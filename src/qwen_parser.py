from __future__ import annotations

import json
import hashlib
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from .resume_parser import candidate_id_for, parse_resume_text


OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
SECTION_DEFAULTS: dict[str, dict[str, Any]] = {
    "skills": {"name": "", "category": ""},
    "experience": {"job_title": "", "company": "", "location": "", "start_date": "", "end_date": "", "description": ""},
    "education": {"degree": "", "institution": "", "location": "", "graduation_year": ""},
    "projects": {"name": "", "technologies": [], "description": "", "url": ""},
    "certifications": {"name": "", "issuer": "", "year": ""},
    "languages": {"name": "", "proficiency": ""},
}


def ollama_available(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=timeout) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def extract_source_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
        if not text:
            raise RuntimeError(f"No extractable text found in {path.name}")
        links = []
        for page in reader.pages:
            for annotation_ref in page.get("/Annots") or []:
                annotation = annotation_ref.get_object()
                uri = annotation.get("/A", {}).get("/URI")
                if uri and uri not in links:
                    links.append(str(uri))
        if links:
            text += "\n\n[EMBEDDED LINKS]\n" + "\n".join(links)
        return text
    return path.read_text(encoding="utf-8")


def parse_with_qwen(path: Path, model: str = "qwen2.5:7b", timeout: float = 180.0) -> dict[str, Any]:
    text = extract_source_text(path)
    baseline = parse_resume_text(text, path)
    schema_example = {
        "candidate": {
            "name": "",
            "email": "",
            "phone": "",
            "location": "",
            "linkedin": "",
            "portfolio": "",
            "headline": "",
            "summary": "",
        },
        "sections": {
            "skills": [{"name": "", "category": ""}],
            "experience": [{"job_title": "", "company": "", "location": "", "start_date": "", "end_date": "", "description": ""}],
            "education": [{"degree": "", "institution": "", "location": "", "graduation_year": ""}],
            "projects": [{"name": "", "technologies": [""], "description": "", "url": ""}],
            "certifications": [{"name": "", "issuer": "", "year": ""}],
            "languages": [{"name": "", "proficiency": ""}],
        },
    }
    prompt = (
        "Extract only facts explicitly present in this resume. Return one valid JSON object with exactly "
        "the shown structure. Use empty strings or empty arrays when absent. Do not infer or add facts. "
        "Preserve the candidate name exactly as printed, including capitalization, spacing, and punctuation. "
        "Inspect the entire resume for technical skills, tools, methods, and named technologies. Return every "
        "skill as its own object; never combine comma-separated skills and never return an empty skill item. "
        "Use mailto and portfolio URLs from EMBEDDED LINKS when visible text omits their target.\n\n"
        f"STRUCTURE:\n{json.dumps(schema_example, indent=2)}\n\nRESUME:\n{text}"
    )
    request_body = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
        "messages": [{"role": "user", "content": prompt}],
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(request_body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        extracted = json.loads(payload["message"]["content"])
    except (OSError, urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Qwen extraction failed for {path.name}: {exc}") from exc

    # Preserve provenance and deterministic stable IDs; the model is used only for semantic fields.
    candidate = extracted.get("candidate", {})
    sections = extracted.get("sections", {})
    for key in baseline["candidate"]:
        if isinstance(candidate.get(key), str):
            baseline["candidate"][key] = candidate[key].strip()
    if baseline["candidate"]["email"].lower().startswith("mailto:"):
        baseline["candidate"]["email"] = baseline["candidate"]["email"][7:]
    for key in baseline["sections"]:
        if isinstance(sections.get(key), list):
            normalized_items = []
            for raw_item in sections[key]:
                if not isinstance(raw_item, dict):
                    continue
                item = {**SECTION_DEFAULTS[key], **raw_item}
                if key == "projects":
                    technologies = item["technologies"]
                    if isinstance(technologies, str):
                        technologies = technologies.split(",")
                    item["technologies"] = [
                        str(value).strip() for value in technologies if str(value).strip()
                    ] if isinstance(technologies, list) else []
                if key == "skills" and isinstance(item["name"], str):
                    names = [value.strip() for value in item["name"].replace(";", ",").replace("|", ",").split(",") if value.strip()]
                    normalized_items.extend({**item, "name": name} for name in names)
                    continue
                identifying_fields = {
                    "experience": ("job_title", "company"),
                    "education": ("degree", "institution"),
                    "projects": ("name",),
                    "certifications": ("name",),
                    "languages": ("name",),
                }
                required_any = identifying_fields.get(key, ("name",))
                if any(str(item.get(field, "")).strip() for field in required_any):
                    normalized_items.append(item)
            baseline["sections"][key] = normalized_items

    name = baseline["candidate"].get("name", "").strip()
    email = baseline["candidate"].get("email", "").strip()
    candidate_id = candidate_id_for(baseline["candidate"])
    for index, item in enumerate(baseline["sections"]["experience"], start=1):
        item["experience_id"] = f"{candidate_id}_exp_{index}"
    for index, item in enumerate(baseline["sections"]["education"], start=1):
        item["education_id"] = f"{candidate_id}_edu_{index}"
    for index, item in enumerate(baseline["sections"]["projects"], start=1):
        item["project_id"] = f"{candidate_id}_proj_{index}"
    baseline["source_document"]["parser_version"] = f"qwen:{model}"
    baseline["source_document"]["source_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return baseline
