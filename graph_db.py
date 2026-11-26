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
        nodes_by_label: dict[str, list[dict]] = {}
        for entity in extracted.entities:
            e_data = entity.model_dump() if hasattr(entity, "model_dump") else dict(entity)
            raw_label = e_data.get("label") or e_data.get("type") or "Entity"
            label = raw_label if raw_label in allowed_labels else "Entity"
            ent_id = str(e_data.get("id", "")).lower()
            if not ent_id:
                continue
            nodes_by_label.setdefault(label, []).append(
                {
                    "id": ent_id,
                    "name": e_data.get("name") or ent_id,
                    "summary": e_data.get("summary") or "",
                }
            )

        rels_by_type: dict[str, list[dict]] = {}
        for rel in extracted.relationships:
            r_data = rel.model_dump() if hasattr(rel, "model_dump") else dict(rel)
            raw_rel = (
                r_data.get("relation_type")
                or r_data.get("relation")
                or r_data.get("type")
                or r_data.get("relationship")
                or r_data.get("label")
                or "RELATED_TO"
            )
            rel_type = "".join(
                c if c.isalnum() or c == "_" else "_" for c in str(raw_rel).upper()
            ) or "RELATED_TO"
            src = str(
                r_data.get("source") or r_data.get("source_id") or r_data.get("from_id") or ""
            ).lower()
            tgt = str(
                r_data.get("target_id") or r_data.get("target") or r_data.get("to_id") or ""
            ).lower()
            if not src or not tgt:
                continue
            rels_by_type.setdefault(rel_type, []).append(
                {
                    "source": src,
                    "target": tgt,
                    "context": r_data.get("context") or r_data.get("description") or "",
                }
            )

        with self.driver.session() as session:
            for label, items in nodes_by_label.items():
                session.run(
                    f"""
                    UNWIND $items AS item
                    MERGE (n:{label} {{id: item.id}})
                    SET n.name = item.name,
                        n.summary = item.summary
                    """,
                    items=items,
                )

            for rel_type, items in rels_by_type.items():
                session.run(
                    f"""
                    UNWIND $items AS item
                    MATCH (a {{id: item.source}})
                    MATCH (b {{id: item.target}})
                    MERGE (a)-[r:{rel_type}]->(b)
                    SET r.context = item.context
                    """,
                    items=items,
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