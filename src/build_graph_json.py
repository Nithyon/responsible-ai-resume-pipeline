from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .resume_parser import candidate_id_for


def entity_id(label: str, *parts: str) -> str:
    value = "|".join(str(part).strip().casefold() for part in parts)
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{label.lower()}_{digest}"


def build_graph(
    input_dir: Path,
    documents_dir: Path | None = None,
    provenance_dir: Path | None = None,
) -> dict[str, list[dict[str, Any]]]:
    nodes: dict[str, dict[str, Any]] = {}
    relationships: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    candidate_by_stem: dict[str, str] = {}
    block_node_ids: dict[str, str] = {}

    def add_node(node_id: str, label: str, properties: dict[str, Any]) -> str:
        if node_id in nodes:
            nodes[node_id]["properties"].update(properties)
        else:
            nodes[node_id] = {"id": node_id, "label": label, "properties": properties}
        return node_id

    def add_relationship(
        source: str,
        relationship_type: str,
        target: str,
        properties: dict[str, Any] | None = None,
        identity: str = "",
    ) -> None:
        key = (source, relationship_type, target, identity)
        relationships[key] = {
            "from": source,
            "type": relationship_type,
            "to": target,
            "properties": properties or {},
        }

    for path in sorted(input_dir.glob("*.json")):
        resume = json.loads(path.read_text(encoding="utf-8"))
        candidate = resume["candidate"]
        sections = resume["sections"]
        source_document = resume["source_document"]

        internal_candidate_id = candidate_id_for(candidate)
        candidate_by_stem[path.stem] = internal_candidate_id
        candidate_id = add_node(
            internal_candidate_id,
            "Candidate",
            {**candidate, "candidate_id": internal_candidate_id},
        )
        resume_id = add_node(
            f"resume_{source_document['source_sha256'][:16]}",
            "Resume",
            source_document,
        )
        add_relationship(candidate_id, "HAS_RESUME", resume_id)

        for item in sections["skills"]:
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            skill_id = add_node(entity_id("Skill", name), "Skill", {"name": name})
            add_relationship(candidate_id, "HAS_SKILL", skill_id, {"category": item.get("category", "")})

        for item in sections["experience"]:
            company = str(item.get("company") or "").strip()
            role = str(item.get("job_title") or "").strip()
            if not role:
                continue
            role_id = add_node(entity_id("Role", role), "Role", {"name": role})
            experience_id = item["experience_id"]
            add_relationship(candidate_id, "HELD_ROLE", role_id)
            if company:
                company_id = add_node(entity_id("Company", company), "Company", {"name": company})
                add_relationship(candidate_id, "WORKED_AT", company_id, item, identity=experience_id)

        for item in sections["education"]:
            institution = str(item.get("institution") or "").strip()
            degree = str(item.get("degree") or "").strip()
            if not institution or not degree:
                continue
            institution_id = add_node(entity_id("Institution", institution), "Institution", {"name": institution})
            degree_id = add_node(entity_id("Degree", degree), "Degree", {"name": degree})
            add_relationship(candidate_id, "STUDIED_AT", institution_id, {
                "education_id": item["education_id"],
                "graduation_year": item.get("graduation_year", ""),
                "location": item.get("location", ""),
            }, identity=item["education_id"])
            add_relationship(candidate_id, "EARNED_DEGREE", degree_id)

        for item in sections["projects"]:
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            project_id = add_node(item["project_id"], "Project", item)
            add_relationship(candidate_id, "BUILT", project_id)
            for technology in item.get("technologies", []):
                technology = str(technology).strip()
                if not technology:
                    continue
                skill_id = add_node(entity_id("Skill", technology), "Skill", {"name": technology})
                add_relationship(project_id, "USES", skill_id)

        for item in sections["certifications"]:
            name = str(item.get("name") or "").strip()
            issuer = str(item.get("issuer") or "").strip()
            if not name or not issuer:
                continue
            certification_id = add_node(entity_id("Certification", name, issuer), "Certification", item)
            add_relationship(candidate_id, "EARNED_CERTIFICATION", certification_id)

        for item in sections["languages"]:
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            language_id = add_node(entity_id("Language", name), "Language", {"name": name})
            add_relationship(candidate_id, "SPEAKS", language_id, {"proficiency": item.get("proficiency", "")})

        for item in resume.get("images", []):
            image_id = add_node(item["image_id"], "Image", item)
            add_relationship(candidate_id, "HAS_IMAGE", image_id)

    if documents_dir is not None:
        for path in sorted(documents_dir.glob("*.document.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            source = document["document"]
            resume_id = add_node(f"resume_{source['source_sha256'][:16]}", "Resume", source)
            section_titles = {
                section["section_id"]: section["title"]
                for section in document["hierarchy"]["sections"]
            }
            for page in document["hierarchy"]["pages"]:
                page_id = add_node(page["page_id"], "Page", {
                    "page_id": page["page_id"],
                    "page_number": page["page_number"],
                    "width": page["width"],
                    "height": page["height"],
                    "raw_text": page["raw_text"],
                })
                add_relationship(resume_id, "HAS_PAGE", page_id)
            for section in document["hierarchy"]["sections"]:
                section_id = add_node(section["section_id"], "Section", {
                    **section,
                    "document_id": source["document_id"],
                })
                add_relationship(resume_id, "HAS_SECTION", section_id)

            ordered_node_ids: list[str] = []
            for block in document["blocks"]:
                if block["type"] == "image":
                    node_id, label = block["image_id"], "Image"
                elif block["type"] == "table":
                    node_id, label = block["block_id"], "Table"
                else:
                    node_id, label = block["block_id"], "TextBlock"
                properties = {
                    **block,
                    "document_id": source["document_id"],
                    "source_file": source["source_file"],
                    "section_title": section_titles[block["section_id"]],
                    "bbox": json.dumps(block["bbox"]),
                    "context_block_ids": json.dumps(block.get("context_block_ids", [])),
                }
                add_node(node_id, label, properties)
                block_node_ids[block["block_id"]] = node_id
                ordered_node_ids.append(node_id)
                add_relationship(block["page_id"], "HAS_BLOCK", node_id)
                add_relationship(block["section_id"], "HAS_BLOCK", node_id)

            for left, right in zip(ordered_node_ids, ordered_node_ids[1:]):
                add_relationship(left, "NEXT_BLOCK", right)
            for block in document["blocks"]:
                if block["type"] not in {"image", "table"}:
                    continue
                source_node = block_node_ids[block["block_id"]]
                for context_id in block.get("context_block_ids", []):
                    target = block_node_ids.get(context_id)
                    if target:
                        add_relationship(source_node, "HAS_CONTEXT", target)

    if provenance_dir is not None:
        for path in sorted(provenance_dir.glob("*.provenance.json")):
            provenance = json.loads(path.read_text(encoding="utf-8"))
            stem = path.name.removesuffix(".provenance.json")
            for claim in provenance["claims"]:
                if not claim["grounded"] or not claim["evidence"]:
                    continue
                graph_ref = claim["graph_ref"]
                if graph_ref["label"] == "Candidate":
                    source_node = candidate_by_stem.get(stem)
                elif graph_ref.get("node_id"):
                    source_node = graph_ref["node_id"]
                else:
                    source_node = entity_id(graph_ref["label"], *graph_ref.get("key", []))
                target_node = block_node_ids.get(claim["evidence"][0]["block_id"])
                if source_node not in nodes or target_node not in nodes:
                    continue
                evidence = claim["evidence"][0]
                add_relationship(source_node, "EXTRACTED_FROM", target_node, {
                    "claim_id": claim["claim_id"],
                    "field": claim["field"],
                    "value": json.dumps(claim["value"], ensure_ascii=False) if isinstance(claim["value"], list) else str(claim["value"]),
                    "page_number": evidence["page_number"],
                    "match_type": evidence["match_type"],
                    "score": evidence["score"],
                }, identity=claim["claim_id"])

    return {"nodes": list(nodes.values()), "relationships": list(relationships.values())}


def validate_neo4j_schema(graph: dict[str, list[dict[str, Any]]], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    node_labels = schema["node_labels"]
    relationship_types = schema["relationship_types"]
    nodes_by_id = {node["id"]: node for node in graph["nodes"]}
    for node in graph["nodes"]:
        if node["label"] not in node_labels:
            errors.append(f"Unknown node label {node['label']} for {node['id']}")
    for index, relationship in enumerate(graph["relationships"]):
        definition = relationship_types.get(relationship["type"])
        source = nodes_by_id.get(relationship["from"])
        target = nodes_by_id.get(relationship["to"])
        if definition is None:
            errors.append(f"Relationship {index} has unknown type {relationship['type']}")
            continue
        if source is None or target is None:
            errors.append(f"Relationship {index} references a missing node")
            continue
        allowed_from = definition["from"] if isinstance(definition["from"], list) else [definition["from"]]
        allowed_to = definition["to"] if isinstance(definition["to"], list) else [definition["to"]]
        if source["label"] not in allowed_from or target["label"] not in allowed_to:
            errors.append(
                f"Relationship {index} {relationship['type']} has invalid labels "
                f"{source['label']} -> {target['label']}"
            )
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Build one Neo4j-ready graph JSON from validated resumes.")
    parser.add_argument("--input", type=Path, default=Path("data/processed"))
    parser.add_argument("--output", type=Path, default=Path("data/graph.json"))
    parser.add_argument("--schema", type=Path, default=Path("config/neo4j_schema.json"))
    parser.add_argument(
        "--documents",
        type=Path,
        help="Optional structure-preserving document JSON directory.",
    )
    parser.add_argument(
        "--provenance",
        type=Path,
        help="Optional claim-to-source provenance directory.",
    )
    args = parser.parse_args()
    graph = build_graph(args.input, args.documents, args.provenance)
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    errors = validate_neo4j_schema(graph, schema)
    if errors:
        print("NEO4J SCHEMA VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"GRAPH JSON CREATED: {len(graph['nodes'])} nodes, {len(graph['relationships'])} relationships -> {args.output}")
    print(f"NEO4J SCHEMA VALIDATION PASSED: {args.schema}")


if __name__ == "__main__":
    main()
