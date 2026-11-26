import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from graph_db import DeveloperMemoryGraphDB

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(timeout=20000),
)


class GraphRAGEngine:
    def __init__(self, db: DeveloperMemoryGraphDB):
        self.db = db

    def retrieve_subgraph_context(self, question: str) -> str:
        keywords = [
            word.strip(".,?!'\"()").lower()
            for word in question.split()
            if len(word.strip(".,?!'\"()")) >= 3
        ]

        with self.db.driver.session() as session:
            matched = session.run(
                """
                MATCH (n)
                WHERE any(kw IN $keywords WHERE
                    toLower(n.id) CONTAINS kw OR
                    toLower(coalesce(n.name, '')) CONTAINS kw OR
                    toLower(coalesce(n.summary, '')) CONTAINS kw
                )
                OPTIONAL MATCH (n)-[r]-(neighbor)
                RETURN DISTINCT
                    n.id AS node_id,
                    labels(n)[0] AS node_label,
                    n.summary AS node_summary,
                    type(r) AS rel_type,
                    startNode(r).id AS src_id,
                    endNode(r).id AS tgt_id,
                    r.context AS rel_context
                LIMIT 40
                """,
                keywords=keywords,
            ).data()

            if not matched:
                matched = session.run(
                    """
                    MATCH (n)
                    OPTIONAL MATCH (n)-[r]->(neighbor)
                    RETURN DISTINCT
                        n.id AS node_id,
                        labels(n)[0] AS node_label,
                        n.summary AS node_summary,
                        type(r) AS rel_type,
                        n.id AS src_id,
                        neighbor.id AS tgt_id,
                        r.context AS rel_context
                    LIMIT 50
                    """
                ).data()

        if not matched:
            return "No developer memory records found in the graph."

        lines = ["### RETRIEVED NEO4J GRAPH CONTEXT ###"]
        seen_nodes = set()
        seen_edges = set()

        for row in matched:
            nid = row["node_id"]
            if nid and nid not in seen_nodes:
                seen_nodes.add(nid)
                lines.append(
                    f"- Node [{row['node_label']}] `{nid}`: {row.get('node_summary', '')}"
                )
            if row["rel_type"] and row["src_id"] and row["tgt_id"]:
                edge_key = (row["src_id"], row["rel_type"], row["tgt_id"])
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    lines.append(
                        f"- Edge: (`{row['src_id']}`) -[{row['rel_type']}]-> (`{row['tgt_id']}`) | Context: {row.get('rel_context', '')}"
                    )

        return "\n".join(lines)

    def ask(self, question: str) -> dict:
        context = self.retrieve_subgraph_context(question)
        prompt = f"""
You are the AI Memory Assistant for a software engineering team.
Answer the user's question using ONLY the Neo4j Knowledge Graph context below.
Cite exact entity IDs in backticks (e.g., `mohankumard18`, `commit-a1b2`) so every claim is traceable.
If the graph does not contain the answer, say so clearly.

{context}

User Question: {question}
"""
        for model_name in ["gemini-3.1-flash-lite", "gemini-3.8-flash"]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.2),
                )
                return {
                    "question": question,
                    "answer": response.text,
                    "graph_context": context,
                }
            except Exception as e:
                print(f"{model_name} failed in RAG ({e}), trying fallback...", flush=True)

        raise RuntimeError("All Gemini models temporarily unavailable.")


if __name__ == "__main__":
    db = DeveloperMemoryGraphDB()
    try:
        rag = GraphRAGEngine(db)
        test_q = "What issue did mohankumard18 resolve, in which repository, and what technologies were used?"
        result = rag.ask(test_q)
        print("=== HYBRID GRAPHRAG Q&A ===", flush=True)
        print(f"Q: {result['question']}\n")
        print(f"A: {result['answer']}\n")
    finally:
        db.close()