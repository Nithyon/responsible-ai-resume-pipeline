from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

DEFAULT_SCHEMA = Path("config/resume.schema.json")


def validate(input_dir: Path, expected_count: int = 10, schema_path: Path = DEFAULT_SCHEMA) -> list[str]:
    errors: list[str] = []
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    files = sorted(input_dir.glob("*.json"))
    if len(files) != expected_count:
        errors.append(f"Expected {expected_count} JSON files; found {len(files)}")
    source_hashes: set[str] = set()
    for path in files:
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}: invalid JSON ({exc})")
            continue
        for validation_error in sorted(validator.iter_errors(item), key=lambda error: list(error.absolute_path)):
            location = ".".join(str(part) for part in validation_error.absolute_path) or "root"
            errors.append(f"{path.name}: schema error at {location}: {validation_error.message}")
        source_hash = item.get("source_document", {}).get("source_sha256")
        if source_hash in source_hashes:
            errors.append(f"{path.name}: duplicate source document hash {source_hash}")
        source_hashes.add(source_hash)
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate normalized resume JSON files.")
    parser.add_argument("--input", type=Path, default=Path("data/processed"))
    parser.add_argument("--expected", type=int, default=10)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    args = parser.parse_args()
    errors = validate(args.input, args.expected, args.schema)
    if errors:
        print("VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"SCHEMA VALIDATION PASSED: {args.expected} resume files match {args.schema}.")


if __name__ == "__main__":
    main()
