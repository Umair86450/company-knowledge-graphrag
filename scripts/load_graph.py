import logging

from app.services.graph_service import close_driver, load_knowledge_base, run_query

logging.basicConfig(level=logging.INFO)


def main() -> None:
    load_knowledge_base("data/knowledge_base.json")

    nodes = run_query("MATCH (n) RETURN count(n) AS count")[0]["count"]
    rels = run_query("MATCH ()-[r]->() RETURN count(r) AS count")[0]["count"]
    print(f"Graph loaded: {nodes} nodes, {rels} relationships")

    close_driver()


if __name__ == "__main__":
    main()
