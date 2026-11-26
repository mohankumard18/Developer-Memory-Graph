import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from schemas import ExtractedMemoryGraph

load_dotenv()


class DeveloperMemoryGraphDB:
    def __init__(self):
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def verify_connection(self):
        with self.driver.session() as session:
            result = session.run("RETURN 1 AS ok")
            if result.single()["ok"] == 1:
                print("Connected to Neo4j AuraDB successfully!")

    def close(self):
        if self.driver:
            self.driver.close()

    def clear_graph(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def get_current_owners(self) -> set[str]:
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (r:Repository)
                WHERE r.owner IS NOT NULL
                RETURN DISTINCT toLower(r.owner) AS owner
                """
            )
            return {record["owner"] for record in result if record["owner"]}

    def set_repo_owner(self, repo_name: str, owner: str):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (r:Repository)
                WHERE toLower(r.id) CONTAINS toLower($repo_name)
                   OR toLower(r.name) CONTAINS toLower($repo_name)
                SET r.owner = $owner
                """,
                repo_name=repo_name,
                owner=owner.lower(),
            )

    def ingest_graph(self, extracted: ExtractedMemoryGraph):
        allowed_labels = {"Developer", "Repository", "Commit", "Issue", "Technology"}
        with self.driver.session() as session:
            for entity in extracted.entities:
                label = entity.label if entity.label in allowed_labels else "Entity"
                query = f"""
                MERGE (n:{label} {{id: $id}})
                SET n.name = $name,
                    n.summary = $summary
                """
                session.run(
                    query,
                    id=entity.id.lower(),
                    name=entity.name,
                    summary=entity.summary,
                )

            for rel in extracted.relationships:
                rel_type = "".join(
                    c if c.isalnum() or c == "_" else "_" for c in rel.relation.upper()
                )
                if not rel_type:
                    rel_type = "RELATED_TO"
                query = f"""
                MATCH (a {{id: $source}})
                MATCH (b {{id: $target}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r.context = $context
                """
                session.run(
                    query,
                    source=rel.source.lower(),
                    target=rel.target.lower(),
                    context=rel.context,
                )

    def fetch_all_graph(self):
        with self.driver.session() as session:
            nodes_res = session.run(
                """
                MATCH (n)
                RETURN n.id AS id, labels(n)[0] AS label, n.name AS name, n.summary AS summary
                """
            )
            nodes = [dict(record) for record in nodes_res]

            edges_res = session.run(
                """
                MATCH (a)-[r]->(b)
                RETURN a.id AS source, b.id AS target, type(r) AS relation, r.context AS context
                """
            )
            edges = [dict(record) for record in edges_res]
            return nodes, edges

    def search_subgraph(self, keywords: list[str], limit: int = 35):
        with self.driver.session() as session:
            if keywords:
                result = session.run(
                    """
                    MATCH (n)
                    WHERE any(kw IN $keywords WHERE
                        toLower(n.id) CONTAINS toLower(kw) OR
                        toLower(coalesce(n.name, '')) CONTAINS toLower(kw) OR
                        toLower(coalesce(n.summary, '')) CONTAINS toLower(kw)
                    )
                    OPTIONAL MATCH (n)-[r]-(m)
                    RETURN n.id AS n_id, labels(n)[0] AS n_label, n.summary AS n_summary,
                           type(r) AS rel, r.context AS rel_context,
                           m.id AS m_id, labels(m)[0] AS m_label, m.summary AS m_summary
                    LIMIT $limit
                    """,
                    keywords=keywords,
                    limit=limit,
                )
                rows = [dict(record) for record in result]
                if rows:
                    return rows

            fallback = session.run(
                """
                MATCH (n)
                OPTIONAL MATCH (n)-[r]->(m)
                RETURN n.id AS n_id, labels(n)[0] AS n_label, n.summary AS n_summary,
                       type(r) AS rel, r.context AS rel_context,
                       m.id AS m_id, labels(m)[0] AS m_label, m.summary AS m_summary
                LIMIT $limit
                """,
                limit=limit,
            )
            return [dict(record) for record in fallback]