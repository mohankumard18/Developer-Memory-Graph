import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from schemas import ExtractedMemoryGraph
from extractor import extract_memory_from_text

load_dotenv()


class DeveloperMemoryGraphDB:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "").replace("neo4j+s://", "neo4j+ssc://")
        user = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def verify_connection(self):
        self.driver.verify_connectivity()
        print("Connected to Neo4j AuraDB successfully!", flush=True)

    def ingest_graph(self, graph: ExtractedMemoryGraph):
        with self.driver.session() as session:
            # 1. Upsert all Entity nodes using MERGE so duplicates are never created
            for entity in graph.entities:
                cypher_node = f"""
                MERGE (n:{entity.label} {{id: $id}})
                SET n.name = $name,
                    n.summary = $summary
                """
                session.run(
                    cypher_node,
                    id=entity.id,
                    name=entity.name,
                    summary=entity.summary,
                )

            # 2. Upsert all directed Relationships between existing Entity nodes
            for rel in graph.relationships:
                cypher_rel = f"""
                MATCH (src {{id: $source_id}})
                MATCH (tgt {{id: $target_id}})
                MERGE (src)-[r:{rel.relation_type}]->(tgt)
                SET r.context = $context
                """
                session.run(
                    cypher_rel,
                    source_id=rel.source_id,
                    target_id=rel.target_id,
                    context=rel.context,
                )

        print(
            f"Ingested {len(graph.entities)} nodes and {len(graph.relationships)} relationships into Neo4j!",
            flush=True,
        )

    def fetch_graph_summary(self):
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (a)-[r]->(b)
                RETURN a.id AS source, type(r) AS relationship, b.id AS target
                """
            )
            return [record.data() for record in result]


if __name__ == "__main__":
    sample_log = """
    Developer mohankumard18 pushed commit commit-a1b2 to repository library-management-system-sql,
    which uses MySQL 8.0 and SQL Triggers. The commit resolved issue-104 (automated overdue fine calculation
    failing on leap-year due dates) and added composite indexing on book_issues.
    """

    db = DeveloperMemoryGraphDB()
    try:
        db.verify_connection()
        extracted = extract_memory_from_text(sample_log)
        db.ingest_graph(extracted)

        print("\nLive Graph Edges in Neo4j AuraDB:")
        for edge in db.fetch_graph_summary():
            print(f"  ({edge['source']}) -[{edge['relationship']}]-> ({edge['target']})")
    finally:
        db.close()