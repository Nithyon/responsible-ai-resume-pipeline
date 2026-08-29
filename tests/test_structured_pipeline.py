from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from src.build_graph_json import build_graph, validate_neo4j_schema
from src.document_ingest import ingest_pdf
from src.export_graph_csv import export
from src.provenance import build_provenance
from src.resume_parser import parse_resume_text
from src.structured_chroma import documents_for
from src.validate_documents import structural_errors


PDF_FIXTURE = Path("data/pdf_samples/synthetic_resume.pdf")


DOMAIN_TEXT = """# MIRA SEN
Email: mira.sen@example.test
Phone: +91 90000 00999
Location: Pune, India
Portfolio: https://portfolio.example/mira-sen
Headline: Data Systems Engineer

[SUMMARY]
Data systems engineer focused on reliable pipelines, observable services, and privacy-aware analytics.

[SKILLS]
Python | Programming; SQL | Programming; Apache Spark | Data; Kafka | Data; Airflow | Data; Docker | Infrastructure; AWS | Infrastructure

[EXPERIENCE]
Data Systems Engineer | Northwind Research | Pune, India | 2022-07 | Present | Built batch and streaming pipelines processing twelve million synthetic events per day.

[EDUCATION]
B.Tech Computer Science | Example Institute of Technology | Pune, India | 2022

[PROJECTS]
Traceable Document Index | Python, Neo4j, Chroma | Linked extracted claims to their source page and document block. | https://portfolio.example/mira-sen

[CERTIFICATIONS]
Cloud Data Foundations | Example Learning Institute | 2025

[LANGUAGES]
English | Professional; Hindi | Native
"""


def synthetic_document(tmp_path: Path) -> dict:
    return ingest_pdf(PDF_FIXTURE, tmp_path / "structured_assets")


def synthetic_resume() -> dict:
    return parse_resume_text(DOMAIN_TEXT, PDF_FIXTURE)


def test_structured_pdf_matches_schema_and_internal_links(tmp_path: Path):
    document = synthetic_document(tmp_path)
    schema = json.loads(Path("config/document.schema.json").read_text(encoding="utf-8"))

    assert list(Draft202012Validator(schema).iter_errors(document)) == []
    assert structural_errors(document) == []
    assert document["statistics"]["pages"] == 1
    assert document["statistics"]["images"] == 1
    assert document["statistics"]["tables"] >= 1
    assert document["statistics"]["links"] >= 1


def test_synthetic_profile_keeps_page_position_and_context(tmp_path: Path):
    document = synthetic_document(tmp_path)
    image = document["assets"]["images"][0]

    assert image["page_number"] == 1
    assert len(image["bbox"]) == 4
    assert image["width_px"] == 360
    assert image["height_px"] == 360
    assert image["context_block_ids"]
    assert Path(image["file_path"]).suffix == ".png"


def test_provenance_links_claims_to_valid_document_blocks(tmp_path: Path):
    document = synthetic_document(tmp_path)
    provenance = build_provenance(synthetic_resume(), document)
    block_ids = {block["block_id"] for block in document["blocks"]}
    evidence = [item for claim in provenance["claims"] for item in claim["evidence"]]

    assert provenance["validation"]["grounded_claims"] > 0
    assert all(item["block_id"] in block_ids for item in evidence)


def test_connected_graph_contains_hierarchy_context_and_provenance(tmp_path: Path):
    processed = tmp_path / "processed"
    structured = tmp_path / "structured"
    provenance_dir = tmp_path / "provenance"
    processed.mkdir()
    structured.mkdir()
    provenance_dir.mkdir()

    resume = synthetic_resume()
    document = synthetic_document(tmp_path)
    provenance = build_provenance(resume, document)
    (processed / "synthetic_resume.json").write_text(json.dumps(resume), encoding="utf-8")
    (structured / "synthetic_resume.document.json").write_text(json.dumps(document), encoding="utf-8")
    (provenance_dir / "synthetic_resume.provenance.json").write_text(json.dumps(provenance), encoding="utf-8")

    graph = build_graph(processed, structured, provenance_dir)
    schema = json.loads(Path("config/neo4j_schema.json").read_text(encoding="utf-8"))
    relationship_types = {relationship["type"] for relationship in graph["relationships"]}

    assert validate_neo4j_schema(graph, schema) == []
    assert {"HAS_PAGE", "HAS_SECTION", "HAS_BLOCK", "NEXT_BLOCK", "HAS_CONTEXT", "EXTRACTED_FROM"} <= relationship_types


def test_structured_chroma_metadata_preserves_source_location(tmp_path: Path):
    document = synthetic_document(tmp_path)
    ids, texts, metadata = documents_for(document)
    image_index = next(index for index, row in enumerate(metadata) if row["content_type"] == "image")

    assert ids[image_index].endswith("block_1")
    assert texts[image_index]
    assert metadata[image_index]["page_number"] == 1
    assert metadata[image_index]["section_id"]
    assert metadata[image_index]["bbox"].startswith("[")


def test_neo4j_export_uses_domain_labels_without_generic_graph_node(tmp_path: Path):
    processed = tmp_path / "processed"
    processed.mkdir()
    (processed / "synthetic_resume.json").write_text(json.dumps(synthetic_resume()), encoding="utf-8")
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(build_graph(processed)), encoding="utf-8")
    output_dir = tmp_path / "neo4j"
    cypher_path = tmp_path / "import.cypher"

    export(graph_path, output_dir, cypher_path)
    cypher = cypher_path.read_text(encoding="utf-8")

    assert "CREATE CONSTRAINT graph_id_candidate" in cypher
    assert "MERGE (n:`Candidate`" in cypher
    assert ":GraphNode" not in cypher
