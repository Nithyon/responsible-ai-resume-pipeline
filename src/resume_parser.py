from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PARSER_VERSION = "deterministic-1.0.0"
SECTION_NAMES = (
    "SUMMARY",
    "SKILLS",
    "EXPERIENCE",
    "EDUCATION",
    "PROJECTS",
    "CERTIFICATIONS",
    "LANGUAGES",
)


def _split_sections(text: str) -> tuple[str, dict[str, str]]:
    marker = re.compile(r"^\[([A-Z]+)\]\s*$", re.MULTILINE)
    matches = list(marker.finditer(text))
    header = text[: matches[0].start()] if matches else text
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[match.end() : end].strip()
    return header.strip(), sections


def _header_value(header: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}:\s*(.+)$", header, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _name_from_header(header: str) -> str:
    for line in header.splitlines():
        cleaned = line.strip().lstrip("#").strip()
        if cleaned and ":" not in cleaned:
            return cleaned
    return "Unknown Candidate"


def _rows(section: str) -> list[list[str]]:
    return [
        [column.strip() for column in line.split("|")]
        for line in section.splitlines()
        if line.strip()
    ]


def _semicolon_pairs(section: str, value_key: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for raw in section.replace("\n", ";").split(";"):
        if not raw.strip():
            continue
        columns = [part.strip() for part in raw.split("|", 1)]
        items.append({"name": columns[0], value_key: columns[1] if len(columns) > 1 else ""})
    return items


def _stable_id(prefix: str, *values: str) -> str:
    digest = hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def candidate_id_for(candidate: dict[str, Any]) -> str:
    """Create an internal database key without exposing it in ingestion JSON."""
    return _stable_id(
        "cand",
        str(candidate.get("name", "")).strip().lower(),
        str(candidate.get("email", "")).strip().lower(),
    )


def parse_resume_text(text: str, source_path: Path) -> dict[str, Any]:
    header, sections = _split_sections(text)
    name = _name_from_header(header)
    email = _header_value(header, "Email")
    candidate_id = _stable_id("cand", name.lower(), email.lower())

    skills = _semicolon_pairs(sections.get("SKILLS", ""), "category")
    languages = _semicolon_pairs(sections.get("LANGUAGES", ""), "proficiency")

    experience = []
    for index, columns in enumerate(_rows(sections.get("EXPERIENCE", "")), start=1):
        columns += [""] * (6 - len(columns))
        experience.append(
            {
                "experience_id": f"{candidate_id}_exp_{index}",
                "job_title": columns[0],
                "company": columns[1],
                "location": columns[2],
                "start_date": columns[3],
                "end_date": columns[4],
                "description": " | ".join(columns[5:]),
            }
        )

    education = []
    for index, columns in enumerate(_rows(sections.get("EDUCATION", "")), start=1):
        columns += [""] * (4 - len(columns))
        education.append(
            {
                "education_id": f"{candidate_id}_edu_{index}",
                "degree": columns[0],
                "institution": columns[1],
                "location": columns[2],
                "graduation_year": columns[3],
            }
        )

    projects = []
    for index, columns in enumerate(_rows(sections.get("PROJECTS", "")), start=1):
        columns += [""] * (4 - len(columns))
        projects.append(
            {
                "project_id": f"{candidate_id}_proj_{index}",
                "name": columns[0],
                "technologies": [item.strip() for item in columns[1].split(",") if item.strip()],
                "description": columns[2],
                "url": columns[3],
            }
        )

    certifications = []
    for columns in _rows(sections.get("CERTIFICATIONS", "")):
        columns += [""] * (3 - len(columns))
        certifications.append({"name": columns[0], "issuer": columns[1], "year": columns[2]})

    normalized = {
        "candidate": {
            "name": name,
            "email": email,
            "phone": _header_value(header, "Phone"),
            "location": _header_value(header, "Location"),
            "linkedin": _header_value(header, "LinkedIn"),
            "portfolio": _header_value(header, "Portfolio"),
            "headline": _header_value(header, "Headline"),
            "summary": sections.get("SUMMARY", "").replace("\n", " ").strip(),
        },
        "sections": {
            "skills": skills,
            "experience": experience,
            "education": education,
            "projects": projects,
            "certifications": certifications,
            "languages": languages,
        },
        "source_document": {
            "source_file": source_path.name,
            "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "parser_version": PARSER_VERSION,
        },
        "images": [],
    }
    return normalized


def parse_resume_file(path: Path) -> dict[str, Any]:
    if path.suffix.lower() not in {".txt", ".md"}:
        raise ValueError(f"Unsupported input format: {path.suffix}. Use .txt or .md.")
    return parse_resume_text(path.read_text(encoding="utf-8"), path)
