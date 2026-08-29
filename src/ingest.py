from __future__ import annotations

import argparse
import json
from pathlib import Path

from .qwen_parser import ollama_available, parse_with_qwen
from .resume_parser import parse_resume_file


def ingest_directory(input_dir: Path, output_dir: Path, parser: str, model: str) -> list[Path]:
    input_files = (
        [input_dir]
        if input_dir.is_file()
        else sorted([*input_dir.glob("*.md"), *input_dir.glob("*.txt"), *input_dir.glob("*.pdf")])
    )
    if not input_files:
        raise RuntimeError(f"No .md or .txt resumes found in {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    use_qwen = parser == "qwen" or (parser == "auto" and ollama_available())
    for source in input_files:
        if source.suffix.lower() == ".pdf" and not use_qwen:
            raise RuntimeError("PDF inputs require --parser qwen or --parser auto with Ollama running.")
        result = parse_with_qwen(source, model) if use_qwen else parse_resume_file(source)
        output_path = output_dir / f"{source.stem}.json"
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        written.append(output_path)
        print(f"[{result['source_document']['parser_version']}] {source.name} -> {output_path.name}")
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize resume files into blueprint-aligned JSON.")
    parser.add_argument("--input", type=Path, default=Path("data/input"))
    parser.add_argument("--output", type=Path, default=Path("data/processed"))
    parser.add_argument("--parser", choices=("deterministic", "qwen", "auto"), default="deterministic")
    parser.add_argument("--model", default="qwen2.5:7b")
    args = parser.parse_args()
    files = ingest_directory(args.input, args.output, args.parser, args.model)
    print(f"Ingested {len(files)} resumes.")


if __name__ == "__main__":
    main()
