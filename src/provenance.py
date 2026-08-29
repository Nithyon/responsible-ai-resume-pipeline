from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def evidence_for(value: Any, blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    if isinstance(value, list):
        value = " ".join(str(part) for part in value)
    value_text = str(value or "").strip()
    target = normalized(value_text)
    if not target:
        return None
    target_tokens = set(target.split())
    best: tuple[float, str, dict[str, Any]] | None = None
    for block in blocks:
        if block.get("type") not in {"heading", "text", "table"}:
            continue
        block_text = str(block.get("text") or "")
        haystack = normalized(block_text)
        if not haystack:
            continue
        if target in haystack:
            score, match_type = 1.0, "exact_normalized"
        else:
            overlap = len(target_tokens & set(haystack.split())) / max(len(target_tokens), 1)
            score, match_type = overlap, "token_overlap"
        candidate = (score, match_type, block)
        if best is None or candidate[0] > best[0]:
            best = candidate
    if best is None or best[0] < 0.45:
        return None
    score, match_type, block = best
    return {
        "block_id": block["block_id"],
        "page_number": block["page_number"],
        "section_id": block["section_id"],
        "bbox": block["bbox"],
        "quote": block.get("text", ""),
        "match_type": match_type,
        "score": round(score, 3),
    }


def add_claim(
    claims: list[dict[str, Any]], blocks: list[dict[str, Any]], section: str, field: str,
    value: Any, graph_ref: dict[str, Any], item_index: int | None = None,
) -> None:
    if not value:
        return
    evidence = evidence_for(value, blocks)
    raw = f"{section}|{item_index}|{field}|{value}"
    claims.append({
        "claim_id": f"claim_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}",
        "section": section,
        "item_index": item_index,
        "field": field,
        "value": value,
        "graph_ref": graph_ref,
        "grounded": evidence is not None,
        "evidence": [evidence] if evidence else [],
    })


def build_provenance(resume: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
    blocks = document["blocks"]
    claims: list[dict[str, Any]] = []
    candidate = resume["candidate"]
    candidate_ref = {"label": "Candidate", "key": [candidate["name"], candidate.get("email", "")]}
    for field, value in candidate.items():
        add_claim(claims, blocks, "candidate", field, value, candidate_ref)

    section_refs = {
        "skills": lambda item: {"label": "Skill", "key": [item.get("name", "")]},
        "experience": lambda item: {"label": "Company", "key": [item.get("company", "")]},
        "education": lambda item: {"label": "Institution", "key": [item.get("institution", "")]},
        "projects": lambda item: {"label": "Project", "node_id": item.get("project_id", "")},
        "certifications": lambda item: {"label": "Certification", "key": [item.get("name", ""), item.get("issuer", "")]},
        "languages": lambda item: {"label": "Language", "key": [item.get("name", "")]},
    }
    for section, items in resume["sections"].items():
        for index, item in enumerate(items):
            base_ref = section_refs[section](item)
            for field, value in item.items():
                if field.endswith("_id"):
                    continue
                graph_ref = base_ref
                if section == "experience" and field == "job_title":
                    graph_ref = {"label": "Role", "key": [value]}
                elif section == "education" and field == "degree":
                    graph_ref = {"label": "Degree", "key": [value]}
                elif section == "skills":
                    graph_ref = {"label": "Skill", "key": [item.get("name", "")]}
                add_claim(claims, blocks, section, field, value, graph_ref, index)

    grounded = sum(claim["grounded"] for claim in claims)
    return {
        "document_id": document["document"]["document_id"],
        "source_file": document["document"]["source_file"],
        "claims": claims,
        "validation": {
            "total_claims": len(claims),
            "grounded_claims": grounded,
            "ungrounded_claims": len(claims) - grounded,
            "coverage": round(grounded / len(claims), 3) if claims else 1.0,
            "meaning": "Grounded means the extracted value was matched back to a page block in the source PDF.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Link Qwen-extracted fields to source PDF blocks.")
    parser.add_argument("--resumes", type=Path, default=Path("data/processed"))
    parser.add_argument("--documents", type=Path, default=Path("data/structured"))
    parser.add_argument("--output", type=Path, default=Path("data/provenance"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for resume_path in sorted(args.resumes.glob("*.json")):
        document_path = args.documents / f"{resume_path.stem}.document.json"
        if not document_path.exists():
            print(f"SKIP {resume_path.name}: no {document_path.name}")
            continue
        resume = json.loads(resume_path.read_text(encoding="utf-8"))
        document = json.loads(document_path.read_text(encoding="utf-8"))
        result = build_provenance(resume, document)
        output_path = args.output / f"{resume_path.stem}.provenance.json"
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        status = result["validation"]
        print(f"{resume_path.name}: {status['grounded_claims']}/{status['total_claims']} claims grounded ({status['coverage']:.1%})")


if __name__ == "__main__":
    main()
