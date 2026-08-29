from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import chromadb
from dotenv import load_dotenv

from .resume_parser import candidate_id_for


def section_text(resume: dict[str, Any], section: str) -> str:
    candidate = resume["candidate"]
    if section == "summary":
        return f"{candidate['name']} - {candidate['headline']}. {candidate['summary']}"
    values = resume["sections"][section]
    rendered = []
    for item in values:
        parts = []
        for key, value in item.items():
            if key.endswith("_id") or not value:
                continue
            display = ", ".join(value) if isinstance(value, list) else str(value)
            parts.append(f"{key.replace('_', ' ')}: {display}")
        rendered.append("; ".join(parts))
    return f"{candidate['name']} {section}: " + " | ".join(rendered)


def documents_for(resume: dict[str, Any]) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    c = resume["candidate"]
    candidate_id = candidate_id_for(c)
    source = resume["source_document"]
    images = resume.get("images", [])
    image_paths = ", ".join(image["relative_path"] for image in images)
    section_names = ["summary"] + [name for name, values in resume["sections"].items() if values]
    ids, documents, metadata = [], [], []
    for section in section_names:
        ids.append(f"{candidate_id}:{section}")
        documents.append(section_text(resume, section))
        metadata.append(
            {
                "candidate_id": candidate_id,
                "candidate_name": c["name"],
                "section": section,
                "source_file": source["source_file"],
                "headline": c["headline"],
                "location": c["location"],
                "image_count": len(images),
                "image_paths": image_paths,
            }
        )
    return ids, documents, metadata


def get_collection(reset: bool = False):
    load_dotenv()
    client = chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "data/chroma"))
    collection_name = os.getenv("CHROMA_COLLECTION", "resume_sections")
    if reset:
        existing_names = {collection.name for collection in client.list_collections()}
        if collection_name in existing_names:
            client.delete_collection(collection_name)
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "Blueprint-aligned semantic resume sections", "hnsw:space": "cosine"},
    )


def load_resumes(input_dir: Path, reset: bool = False) -> int:
    collection = get_collection(reset=reset)
    total = 0
    for path in sorted(input_dir.glob("*.json")):
        resume = json.loads(path.read_text(encoding="utf-8"))
        ids, documents, metadata = documents_for(resume)
        collection.upsert(ids=ids, documents=documents, metadatas=metadata)
        total += len(ids)
        print(f"Embedded {path.name}: {len(ids)} documents")
    return total


def query(text: str, n_results: int = 5) -> None:
    result = get_collection().query(query_texts=[text], n_results=n_results)
    for rank, (document, metadata, distance) in enumerate(
        zip(result["documents"][0], result["metadatas"][0], result["distances"][0]), start=1
    ):
        print(f"{rank}. {metadata['candidate_name']} [{metadata['section']}] distance={distance:.4f}")
        print(f"   {document}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load or search the Chroma resume collection.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    load_parser = subparsers.add_parser("load")
    load_parser.add_argument("--input", type=Path, default=Path("data/processed"))
    load_parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate only the configured resume collection before loading.",
    )
    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("text")
    query_parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    if args.command == "load":
        total = load_resumes(args.input, reset=args.reset)
        print(f"Chroma load complete: {total} section documents.")
    else:
        query(args.text, args.top_k)


if __name__ == "__main__":
    main()
