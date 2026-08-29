from __future__ import annotations

import argparse
import json
from pathlib import Path

from .export_neo4j_csv import write_csv


def export(input_dir: Path, output_dir: Path) -> dict[str, int]:
    resumes = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(input_dir.glob("*.json"))]
    if not resumes:
        raise RuntimeError("No processed JSON files found. Run domain extraction first.")

    candidates: list[dict] = []
    skills: list[dict] = []
    experiences: list[dict] = []
    education: list[dict] = []
    projects: list[dict] = []
    technologies: list[dict] = []
    certifications: list[dict] = []

    for resume in resumes:
        candidate = resume["candidate"]
        candidate_name = str(candidate.get("name") or "").strip()
        if not candidate_name:
            continue

        candidates.append(
            {
                "name": candidate_name,
                "email": candidate.get("email", ""),
                "phone": candidate.get("phone", ""),
                "location": candidate.get("location", ""),
                "linkedin": candidate.get("linkedin", ""),
                "source_file": resume["source_document"].get("source_file", ""),
            }
        )

        sections = resume["sections"]
        skills.extend(
            {"candidate_name": candidate_name, "name": item.get("name", ""), "category": item.get("category", "")}
            for item in sections["skills"]
            if str(item.get("name") or "").strip()
        )
        experiences.extend(
            {
                "candidate_name": candidate_name,
                "job_title": item.get("job_title", ""),
                "company": item.get("company", ""),
                "location": item.get("location", ""),
                "start_date": item.get("start_date", ""),
                "end_date": item.get("end_date", ""),
                "description": item.get("description", ""),
            }
            for item in sections["experience"]
            if str(item.get("job_title") or "").strip() and str(item.get("company") or "").strip()
        )
        education.extend(
            {
                "candidate_name": candidate_name,
                "institution": item.get("institution", ""),
                "degree": item.get("degree", ""),
                "location": item.get("location", ""),
                "date": item.get("graduation_year", ""),
            }
            for item in sections["education"]
            if str(item.get("institution") or "").strip()
        )
        for item in sections["projects"]:
            project_name = str(item.get("name") or "").strip()
            if not project_name:
                continue
            projects.append(
                {
                    "candidate_name": candidate_name,
                    "name": project_name,
                    "description": item.get("description", ""),
                    "url": item.get("url", ""),
                }
            )
            technologies.extend(
                {"project_name": project_name, "name": technology}
                for technology in item.get("technologies", [])
                if str(technology or "").strip()
            )
        certifications.extend(
            {
                "candidate_name": candidate_name,
                "name": item.get("name", ""),
                "issuer": item.get("issuer", ""),
                "date": item.get("year", ""),
            }
            for item in sections["certifications"]
            if str(item.get("name") or "").strip()
        )

    return {
        "demo_candidates.csv": write_csv(
            output_dir / "demo_candidates.csv",
            ["name", "email", "phone", "location", "linkedin", "source_file"],
            candidates,
        ),
        "demo_skills.csv": write_csv(
            output_dir / "demo_skills.csv", ["candidate_name", "name", "category"], skills
        ),
        "demo_experience.csv": write_csv(
            output_dir / "demo_experience.csv",
            ["candidate_name", "job_title", "company", "location", "start_date", "end_date", "description"],
            experiences,
        ),
        "demo_education.csv": write_csv(
            output_dir / "demo_education.csv", ["candidate_name", "institution", "degree", "location", "date"], education
        ),
        "demo_projects.csv": write_csv(
            output_dir / "demo_projects.csv", ["candidate_name", "name", "description", "url"], projects
        ),
        "demo_technologies.csv": write_csv(
            output_dir / "demo_technologies.csv", ["project_name", "name"], technologies
        ),
        "demo_certifications.csv": write_csv(
            output_dir / "demo_certifications.csv", ["candidate_name", "name", "issuer", "date"], certifications
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a compact, domain-only Neo4j presentation graph.")
    parser.add_argument("--input", type=Path, default=Path("data/processed"))
    parser.add_argument("--output", type=Path, default=Path("data/neo4j_demo_import"))
    args = parser.parse_args()
    for filename, count in export(args.input, args.output).items():
        print(f"{filename}: {count} rows")


if __name__ == "__main__":
    main()
