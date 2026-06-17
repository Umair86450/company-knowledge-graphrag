"""Neo4j connection helpers: a shared driver and parameterized query runner."""

from __future__ import annotations

import json
import logging
import os

from dotenv import load_dotenv
from neo4j import Driver, GraphDatabase

load_dotenv()

logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

ALLOWED_LABELS = {"Person", "Project", "Skill", "Technology", "Company"}
ALLOWED_REL_TYPES = {"KNOWS", "WORKS_ON", "REPORTS_TO", "USES", "WORKS_AT", "MEMBER_OF"}

_driver: Driver | None = None


def get_driver() -> Driver:
    global _driver
    if _driver is None:
        try:
            _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            _driver.verify_connectivity()
            logger.info("Connected to Neo4j at %s", NEO4J_URI)
        except Exception:
            logger.error("Failed to connect to Neo4j at %s", NEO4J_URI)
            raise
    return _driver


def run_query(cypher: str, params: dict | None = None) -> list[dict]:
    with get_driver().session() as session:
        result = session.run(cypher, params or {})
        return [record.data() for record in result]


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
        logger.info("Neo4j driver closed")


def find_entities(question: str) -> list[dict]:
    text = question.lower()
    nodes = run_query("MATCH (n) RETURN n.id AS id, labels(n)[0] AS label")
    return [n for n in nodes if n["id"] and n["id"].lower() in text]


def get_neighborhood(entity_ids: list[str]) -> list[dict]:
    return run_query(
        "MATCH (a)-[r]-(b) WHERE a.id IN $ids "
        "RETURN a.id AS from, type(r) AS rel, b.id AS to, labels(b)[0] AS to_label",
        {"ids": entity_ids},
    )


def retrieve_context(question: str) -> str:
    entities = find_entities(question)
    if not entities:
        return ""

    relationships = get_neighborhood([e["id"] for e in entities])
    lines = []
    for r in relationships:
        line = f"- {r['from']} {r['rel']} {r['to']}"
        if line not in lines:
            lines.append(line)

    return "Facts from the company knowledge graph:\n" + "\n".join(lines)


def load_knowledge_base(json_path: str) -> None:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    for node in data["nodes"]:
        label = node["label"]
        if label not in ALLOWED_LABELS:
            raise ValueError(f"Unknown node label: {label}")
        run_query(
            f"MERGE (n:{label} {{id: $id}}) SET n += $props",
            {"id": node["id"], "props": node["properties"]},
        )

    for rel in data["relationships"]:
        rel_type = rel["type"]
        if rel_type not in ALLOWED_REL_TYPES:
            raise ValueError(f"Unknown relationship type: {rel_type}")
        run_query(
            f"MATCH (a {{id: $from}}), (b {{id: $to}}) MERGE (a)-[:{rel_type}]->(b)",
            {"from": rel["from"], "to": rel["to"]},
        )

    logger.info(
        "Loaded %d nodes and %d relationships from %s",
        len(data["nodes"]),
        len(data["relationships"]),
        json_path,
    )
