from __future__ import annotations

import json
from pathlib import Path

from src.build_graph_json import build_graph, validate_neo4j_schema
from src.chroma_store import documents_for
from src.export_demo_graph import export
from src.ingest import ingest_directory
from src.resume_parser import candidate_id_for, parse_resume_file
from src.validate import validate


INPUT_DIR = Path("data/input")
FIXTURE = INPUT_DIR / "resume_01_data_engineer.md"


def test_ten_synthetic_resumes_ingest_and_validate(tmp_path: Path):
    output_dir = tmp_path / "processed"
    written = ingest_directory(INPUT_DIR, output_dir, "deterministic", "qwen2.5:7b")

    assert len(written) == 10
    assert validate(output_dir, expected_count=10) == []


def test_parser_preserves_candidate_name_and_missing_values():
    resume = parse_resume_file(FIXTURE)

    assert resume["candidate"]["name"] == "Aanya Rao"
    assert resume["candidate"]["email"] == "aanya.rao@example.test"
    assert "candidate_id" not in resume["candidate"]
    assert len(resume["sections"]["experience"]) == 2
    assert any(skill["name"] == "Apache Spark" for skill in resume["sections"]["skills"])


def test_vector_documents_follow_id_and_metadata_schema():
    resume = parse_resume_file(FIXTURE)
    ids, documents, metadata = documents_for(resume)

    assert len(ids) == len(documents) == len(metadata) == 7
    assert ids[0].endswith(":summary")
    assert all(row["candidate_id"] == candidate_id_for(resume["candidate"]) for row in metadata)
    assert all(row["source_file"] == FIXTURE.name for row in metadata)


def test_synthetic_graph_matches_formal_neo4j_schema(tmp_path: Path):
    processed = tmp_path / "processed"
    ingest_directory(INPUT_DIR, processed, "deterministic", "qwen2.5:7b")
    graph = build_graph(processed)
    schema = json.loads(Path("config/neo4j_schema.json").read_text(encoding="utf-8"))

    assert validate_neo4j_schema(graph, schema) == []
    labels = {node["label"] for node in graph["nodes"]}
    relationships = {relationship["type"] for relationship in graph["relationships"]}
    assert {"Candidate", "Skill", "Company", "Institution", "Project"} <= labels
    assert {"HAS_SKILL", "WORKED_AT", "STUDIED_AT", "BUILT", "USES"} <= relationships


def test_demo_export_contains_only_public_presentation_columns(tmp_path: Path):
    processed = tmp_path / "processed"
    output = tmp_path / "neo4j_demo_import"
    ingest_directory(INPUT_DIR, processed, "deterministic", "qwen2.5:7b")

    counts = export(processed, output)

    assert counts["demo_candidates.csv"] == 10
    assert {path.name for path in output.glob("*.csv")} == set(counts)
    candidate_header = (output / "demo_candidates.csv").read_text(encoding="utf-8").splitlines()[0]
    assert candidate_header == "name,email,phone,location,linkedin,source_file"
