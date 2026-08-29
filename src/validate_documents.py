from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


def structural_errors(document: dict) -> list[str]:
    errors: list[str] = []
    pages = document["hierarchy"]["pages"]
    sections = document["hierarchy"]["sections"]
    blocks = document["blocks"]
    block_ids = [block["block_id"] for block in blocks]
    page_ids = {page["page_id"] for page in pages}
    section_ids = {section["section_id"] for section in sections}

    if len(block_ids) != len(set(block_ids)):
        errors.append("block_id values are not unique")
    if document["document"]["page_count"] != len(pages):
        errors.append("document.page_count does not match hierarchy.pages")
    for block in blocks:
        if block["page_id"] not in page_ids:
            errors.append(f"{block['block_id']} references a missing page")
        if block["section_id"] not in section_ids:
            errors.append(f"{block['block_id']} references a missing section")
        x0, top, x1, bottom = block["bbox"]
        if x1 < x0 or bottom < top:
            errors.append(f"{block['block_id']} has an invalid bbox")
        for context_id in block.get("context_block_ids", []):
            if context_id not in set(block_ids):
                errors.append(f"{block['block_id']} references missing context block {context_id}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate structure-preserving PDF ingestion JSON files.")
    parser.add_argument("--input", type=Path, default=Path("data/structured"))
    parser.add_argument("--schema", type=Path, default=Path("config/document.schema.json"))
    args = parser.parse_args()

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    failed = 0
    files = sorted(args.input.glob("*.document.json"))
    for path in files:
        document = json.loads(path.read_text(encoding="utf-8"))
        errors = [error.message for error in validator.iter_errors(document)] + structural_errors(document)
        if errors:
            failed += 1
            print(f"FAIL {path.name}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {path.name}")
    if failed:
        raise SystemExit(f"DOCUMENT VALIDATION FAILED: {failed}/{len(files)} files")
    print(f"DOCUMENT VALIDATION PASSED: {len(files)} files against {args.schema}")


if __name__ == "__main__":
    main()
