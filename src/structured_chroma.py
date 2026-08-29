from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import chromadb
from dotenv import load_dotenv


COLLECTION_NAME = "document_blocks"


def block_document(block: dict[str, Any]) -> str:
    if block["type"] in {"heading", "text", "table"}:
        return str(block.get("text") or "")
    return " | ".join(part for part in [block.get("caption", ""), block.get("nearby_text", "")] if part)


def documents_for(document: dict[str, Any]) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    source = document["document"]
    sections = {item["section_id"]: item for item in document["hierarchy"]["sections"]}
    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict[str, Any]] = []
    for block in document["blocks"]:
        text = block_document(block).strip()
        if not text:
            continue
        section = sections[block["section_id"]]
        ids.append(block["block_id"])
        texts.append(text)
        metadatas.append({
            "document_id": source["document_id"],
            "source_file": source["source_file"],
            "page_number": block["page_number"],
            "page_id": block["page_id"],
            "section_id": block["section_id"],
            "section_title": section["title"],
            "block_id": block["block_id"],
            "content_type": block["type"],
            "bbox": json.dumps(block["bbox"]),
            "asset_path": block.get("file_path", ""),
        })
    return ids, texts, metadatas


def get_collection(reset: bool = False):
    load_dotenv()
    client = chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "data/chroma"))
    if reset and COLLECTION_NAME in {collection.name for collection in client.list_collections()}:
        client.delete_collection(COLLECTION_NAME)
    return client.get_or_create_collection(
        COLLECTION_NAME,
        metadata={"description": "PDF blocks with page, section, bbox, image/table context and provenance", "hnsw:space": "cosine"},
    )


def load_documents(input_dir: Path, reset: bool = False) -> int:
    collection = get_collection(reset)
    total = 0
    for path in sorted(input_dir.glob("*.document.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        ids, texts, metadatas = documents_for(document)
        if ids:
            collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
        total += len(ids)
        print(f"Embedded {path.name}: {len(ids)} provenance-rich blocks")
    return total


def query(text: str, top_k: int) -> None:
    results = get_collection().query(query_texts=[text], n_results=top_k)
    for rank, (document, metadata, distance) in enumerate(zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ), start=1):
        print(f"{rank}. {metadata['source_file']} page {metadata['page_number']} [{metadata['section_title']}] distance={distance:.4f}")
        print(f"   block={metadata['block_id']} bbox={metadata['bbox']}")
        print(f"   {document}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load/search layout-preserving PDF blocks in Chroma.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    load_parser = subparsers.add_parser("load")
    load_parser.add_argument("--input", type=Path, default=Path("data/structured"))
    load_parser.add_argument("--reset", action="store_true")
    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("text")
    query_parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    if args.command == "load":
        print(f"Chroma structured load complete: {load_documents(args.input, args.reset)} blocks")
    else:
        query(args.text, args.top_k)


if __name__ == "__main__":
    main()
