from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

from .resume_parser import candidate_id_for


CONSTRAINTS = [
    "CREATE CONSTRAINT candidate_id IF NOT EXISTS FOR (n:Candidate) REQUIRE n.candidate_id IS UNIQUE",
    "CREATE CONSTRAINT resume_hash IF NOT EXISTS FOR (n:Resume) REQUIRE n.source_sha256 IS UNIQUE",
    "CREATE CONSTRAINT skill_name IF NOT EXISTS FOR (n:Skill) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT company_name IF NOT EXISTS FOR (n:Company) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT institution_name IF NOT EXISTS FOR (n:Institution) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT project_id IF NOT EXISTS FOR (n:Project) REQUIRE n.project_id IS UNIQUE",
]


def load_one(session, resume: dict) -> None:
    raw_candidate = resume["candidate"]
    c = {**raw_candidate, "candidate_id": candidate_id_for(raw_candidate)}
    source = resume["source_document"]
    session.run(
        """
        MERGE (candidate:Candidate {candidate_id: $candidate_id})
        SET candidate += $candidate
        MERGE (resume:Resume {source_sha256: $source_sha256})
        SET resume += $source
        MERGE (candidate)-[:HAS_RESUME]->(resume)
        """,
        candidate_id=c["candidate_id"], candidate=c,
        source_sha256=source["source_sha256"], source=source,
    )
    for skill in resume["sections"]["skills"]:
        session.run(
            "MERGE (c:Candidate {candidate_id:$id}) MERGE (s:Skill {name:$name}) MERGE (c)-[r:HAS_SKILL]->(s) SET r.category=$category",
            id=c["candidate_id"], name=skill["name"], category=skill.get("category", ""),
        )
    for item in resume["sections"]["experience"]:
        session.run(
            """
            MERGE (c:Candidate {candidate_id:$id})
            MERGE (company:Company {name:$company})
            MERGE (c)-[r:WORKED_AT {experience_id:$experience_id}]->(company)
            SET r.job_title=$job_title, r.location=$location, r.start_date=$start_date,
                r.end_date=$end_date, r.description=$description
            MERGE (role:Role {name:$job_title})
            MERGE (c)-[:HELD_ROLE]->(role)
            """, id=c["candidate_id"], **item,
        )
    for item in resume["sections"]["education"]:
        session.run(
            """
            MERGE (c:Candidate {candidate_id:$id})
            MERGE (i:Institution {name:$institution})
            MERGE (c)-[r:STUDIED_AT {education_id:$education_id}]->(i)
            SET r.graduation_year=$graduation_year, r.location=$location
            MERGE (d:Degree {name:$degree})
            MERGE (c)-[:EARNED_DEGREE]->(d)
            """, id=c["candidate_id"], **item,
        )
    for item in resume["sections"]["projects"]:
        session.run(
            """
            MERGE (c:Candidate {candidate_id:$id})
            MERGE (p:Project {project_id:$project_id})
            SET p.name=$name, p.description=$description, p.url=$url
            MERGE (c)-[:BUILT]->(p)
            """, id=c["candidate_id"], **item,
        )
        for technology in item.get("technologies", []):
            session.run(
                "MERGE (p:Project {project_id:$project_id}) MERGE (s:Skill {name:$technology}) MERGE (p)-[:USES]->(s)",
                project_id=item["project_id"], technology=technology,
            )
    for item in resume["sections"]["certifications"]:
        session.run(
            """
            MERGE (c:Candidate {candidate_id:$id})
            MERGE (x:Certification {name:$name, issuer:$issuer}) SET x.year=$year
            MERGE (c)-[:EARNED_CERTIFICATION]->(x)
            """, id=c["candidate_id"], **item,
        )
    for item in resume["sections"]["languages"]:
        session.run(
            """
            MERGE (c:Candidate {candidate_id:$id})
            MERGE (l:Language {name:$name})
            MERGE (c)-[r:SPEAKS]->(l) SET r.proficiency=$proficiency
            """, id=c["candidate_id"], **item,
        )


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Load normalized resumes into Neo4j.")
    parser.add_argument("--input", type=Path, default=Path("data/processed"))
    parser.add_argument("--reset", action="store_true", help="Delete all current Neo4j nodes before loading.")
    args = parser.parse_args()
    files = sorted(args.input.glob("*.json"))
    if not files:
        raise RuntimeError("No processed JSON files found. Run ingestion first.")
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "resume-password")),
    )
    with driver:
        driver.verify_connectivity()
        with driver.session() as session:
            if args.reset:
                session.run("MATCH (n) DETACH DELETE n").consume()
            for statement in CONSTRAINTS:
                session.run(statement).consume()
            for path in files:
                load_one(session, json.loads(path.read_text(encoding="utf-8")))
                print(f"Loaded {path.name}")
            counts = session.run("MATCH (n) RETURN count(n) AS nodes").single()["nodes"]
    print(f"Neo4j load complete: {len(files)} resumes, {counts} total nodes.")


if __name__ == "__main__":
    main()
