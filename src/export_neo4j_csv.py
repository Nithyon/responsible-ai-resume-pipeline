from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable

from .resume_parser import candidate_id_for


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict]) -> int:
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(materialized)
    return len(materialized)


def export(input_dir: Path, output_dir: Path) -> dict[str, int]:
    resumes = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(input_dir.glob("*.json"))]
    if not resumes:
        raise RuntimeError("No processed JSON files found. Run ingestion first.")

    candidates = []
    skills = []
    experiences = []
    education = []
    projects = []
    project_skills = []
    certifications = []
    languages = []
    for resume in resumes:
        c = resume["candidate"]
        candidate_id = candidate_id_for(c)
        candidates.append({"candidate_id": candidate_id, **c, **resume["source_document"]})
        skills.extend(
            {"candidate_id": candidate_id, **item}
            for item in resume["sections"]["skills"]
            if str(item.get("name") or "").strip()
        )
        experiences.extend(
            {"candidate_id": candidate_id, **item}
            for item in resume["sections"]["experience"]
            if str(item.get("job_title") or "").strip() and str(item.get("company") or "").strip()
        )
        education.extend(
            {"candidate_id": candidate_id, **item}
            for item in resume["sections"]["education"]
            if str(item.get("degree") or "").strip() and str(item.get("institution") or "").strip()
        )
        for item in resume["sections"]["projects"]:
            if not str(item.get("name") or "").strip():
                continue
            projects.append({"candidate_id": candidate_id, **item, "technologies": ", ".join(item["technologies"])})
            project_skills.extend(
                {"project_id": item["project_id"], "technology": value}
                for value in item["technologies"]
                if str(value or "").strip()
            )
        certifications.extend(
            {"candidate_id": candidate_id, **item}
            for item in resume["sections"]["certifications"]
            if str(item.get("name") or "").strip() and str(item.get("issuer") or "").strip()
        )
        languages.extend(
            {"candidate_id": candidate_id, **item}
            for item in resume["sections"]["languages"]
            if str(item.get("name") or "").strip()
        )

    counts = {
        "resume_candidates.csv": write_csv(output_dir / "resume_candidates.csv", [
            "candidate_id", "name", "email", "phone", "location", "linkedin", "portfolio", "headline", "summary",
            "source_file", "source_sha256", "ingested_at", "parser_version",
        ], candidates),
        "resume_skills.csv": write_csv(output_dir / "resume_skills.csv", ["candidate_id", "name", "category"], skills),
        "resume_experience.csv": write_csv(output_dir / "resume_experience.csv", [
            "candidate_id", "experience_id", "job_title", "company", "location", "start_date", "end_date", "description",
        ], experiences),
        "resume_education.csv": write_csv(output_dir / "resume_education.csv", [
            "candidate_id", "education_id", "degree", "institution", "location", "graduation_year",
        ], education),
        "resume_projects.csv": write_csv(output_dir / "resume_projects.csv", [
            "candidate_id", "project_id", "name", "technologies", "description", "url",
        ], projects),
        "resume_project_skills.csv": write_csv(output_dir / "resume_project_skills.csv", ["project_id", "technology"], project_skills),
        "resume_certifications.csv": write_csv(output_dir / "resume_certifications.csv", ["candidate_id", "name", "issuer", "year"], certifications),
        "resume_languages.csv": write_csv(output_dir / "resume_languages.csv", ["candidate_id", "name", "proficiency"], languages),
    }
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Export normalized resume JSON to Neo4j LOAD CSV files.")
    parser.add_argument("--input", type=Path, default=Path("data/processed"))
    parser.add_argument("--output", type=Path, default=Path("data/neo4j_import"))
    args = parser.parse_args()
    for filename, count in export(args.input, args.output).items():
        print(f"{filename}: {count} rows")


if __name__ == "__main__":
    main()
