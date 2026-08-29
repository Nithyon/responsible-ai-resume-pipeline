from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase


def neo4j_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list) and all(item is None or isinstance(item, (str, int, float, bool)) for item in value):
        return value
    return json.dumps(value, ensure_ascii=False)


def safe_properties(properties: dict[str, Any]) -> dict[str, Any]:
    return {key: neo4j_value(value) for key, value in properties.items()}


def load_graph(path: Path, reset: bool = False) -> tuple[int, int]:
    load_dotenv()
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "resume-password")
    graph = json.loads(path.read_text(encoding="utf-8"))
    node_ids = [node["id"] for node in graph["nodes"]]
    if len(node_ids) != len(set(node_ids)):
        raise ValueError("graph.json contains duplicate node IDs")
    node_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rel_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in graph["nodes"]:
        node_groups[node["label"]].append({"id": node["id"], "properties": safe_properties(node["properties"])})
    for relationship in graph["relationships"]:
        raw = json.dumps(relationship, sort_keys=True, ensure_ascii=False)
        rel_groups[relationship["type"]].append({
            "from": relationship["from"],
            "to": relationship["to"],
            "rel_id": f"rel_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}",
            "properties": safe_properties(relationship["properties"]),
        })

    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver:
        driver.verify_connectivity()
        with driver.session() as session:
            session.run("DROP CONSTRAINT graph_node_id IF EXISTS").consume()
            if reset:
                session.run("MATCH (n) DETACH DELETE n").consume()
            for label, rows in node_groups.items():
                constraint_name = f"graph_id_{''.join(character.casefold() if character.isalnum() else '_' for character in label).strip('_')}"
                session.run(
                    f"CREATE CONSTRAINT {constraint_name} IF NOT EXISTS "
                    f"FOR (n:`{label}`) REQUIRE n.graph_id IS UNIQUE"
                ).consume()
                query = f"""
                UNWIND $rows AS row
                MERGE (n:`{label}` {{graph_id: row.id}})
                REMOVE n:GraphNode
                SET n += row.properties
                """
                session.run(query, rows=rows).consume()
                print(f"Loaded {len(rows)} {label} nodes")
            for relationship_type, rows in rel_groups.items():
                query = f"""
                UNWIND $rows AS row
                MATCH (a {{graph_id: row.from}})
                MATCH (b {{graph_id: row.to}})
                MERGE (a)-[r:`{relationship_type}` {{graph_id: row.rel_id}}]->(b)
                SET r += row.properties
                """
                session.run(query, rows=rows).consume()
                print(f"Loaded {len(rows)} {relationship_type} relationships")
            result = session.run("MATCH (n) OPTIONAL MATCH (n)-[r]->() RETURN count(DISTINCT n) AS nodes, count(r) AS relationships").single()
    return result["nodes"], result["relationships"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Load the schema-validated graph JSON into Neo4j.")
    parser.add_argument("--input", type=Path, default=Path("data/graph.json"))
    parser.add_argument("--reset", action="store_true", help="Delete all existing Neo4j data before loading this graph.")
    args = parser.parse_args()
    nodes, relationships = load_graph(args.input, args.reset)
    print(f"Neo4j graph load complete: {nodes} nodes, {relationships} relationships")


if __name__ == "__main__":
    main()
