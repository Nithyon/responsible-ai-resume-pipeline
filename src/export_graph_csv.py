from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def safe_name(value: str) -> str:
    return "".join(character.casefold() if character.isalnum() else "_" for character in value).strip("_")


def write_rows(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)


def export(graph_path: Path, output_dir: Path, cypher_path: Path) -> tuple[int, int]:
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    node_ids = [node["id"] for node in graph["nodes"]]
    if len(node_ids) != len(set(node_ids)):
        raise ValueError("graph.json contains duplicate node IDs")
    output_dir.mkdir(parents=True, exist_ok=True)
    nodes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    relationships: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in graph["nodes"]:
        nodes[node["label"]].append(node)
    for relationship in graph["relationships"]:
        relationships[relationship["type"]].append(relationship)

    clauses = ["DROP CONSTRAINT graph_node_id IF EXISTS", "MATCH (n) DETACH DELETE n"]
    count_names: list[str] = []
    for label, values in sorted(nodes.items()):
        clauses.append(
            f"CREATE CONSTRAINT graph_id_{safe_name(label)} IF NOT EXISTS "
            f"FOR (n:`{label}`) REQUIRE n.graph_id IS UNIQUE"
        )
        property_names = sorted({key for value in values for key in value["properties"]})
        filename = f"graph_nodes_{safe_name(label)}.csv"
        rows = [
            {"graph_id": value["id"], **{key: csv_value(value["properties"].get(key)) for key in property_names}}
            for value in values
        ]
        write_rows(output_dir / filename, rows, ["graph_id", *property_names])
        count_name = f"n_{safe_name(label)}"
        count_names.append(count_name)
        setters = ", ".join(f"n.`{key}` = row.`{key}`" for key in property_names)
        clauses.append(
            "CALL () {\n"
            f"  LOAD CSV WITH HEADERS FROM 'file:///{filename}' AS row\n"
            f"  MERGE (n:`{label}` {{graph_id: row.graph_id}})\n"
            + (f"  SET {setters}\n" if setters else "")
            + f"  RETURN count(*) AS {count_name}\n"
            "}"
        )

    for relationship_type, values in sorted(relationships.items()):
        property_names = sorted({key for value in values for key in value["properties"]})
        filename = f"graph_rels_{safe_name(relationship_type)}.csv"
        rows = []
        for value in values:
            raw = json.dumps(value, sort_keys=True, ensure_ascii=False)
            rows.append({
                "from_id": value["from"],
                "to_id": value["to"],
                "rel_id": f"rel_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}",
                **{key: csv_value(value["properties"].get(key)) for key in property_names},
            })
        write_rows(output_dir / filename, rows, ["from_id", "to_id", "rel_id", *property_names])
        count_name = f"r_{safe_name(relationship_type)}"
        count_names.append(count_name)
        setters = ", ".join(f"r.`{key}` = row.`{key}`" for key in property_names)
        clauses.append(
            "CALL () {\n"
            f"  LOAD CSV WITH HEADERS FROM 'file:///{filename}' AS row\n"
            "  MATCH (a {graph_id: row.from_id})\n"
            "  MATCH (b {graph_id: row.to_id})\n"
            f"  MERGE (a)-[r:`{relationship_type}` {{graph_id: row.rel_id}}]->(b)\n"
            + (f"  SET {setters}\n" if setters else "")
            + f"  RETURN count(*) AS {count_name}\n"
            "}"
        )
    clauses.append("RETURN " + ", ".join(count_names))
    cypher_path.parent.mkdir(parents=True, exist_ok=True)
    cypher_path.write_text(";\n".join(clauses) + ";\n", encoding="utf-8")
    return len(graph["nodes"]), len(graph["relationships"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Export graph.json as Neo4j LOAD CSV files plus one Cypher script.")
    parser.add_argument("--input", type=Path, default=Path("data/graph.json"))
    parser.add_argument("--output", type=Path, default=Path("data/neo4j_structured_import"))
    parser.add_argument("--cypher", type=Path, default=Path("config/neo4j_structured_import.cypher"))
    args = parser.parse_args()
    nodes, relationships = export(args.input, args.output, args.cypher)
    print(f"Exported {nodes} nodes and {relationships} relationships to {args.output}")
    print(f"Cypher import script: {args.cypher}")


if __name__ == "__main__":
    main()
