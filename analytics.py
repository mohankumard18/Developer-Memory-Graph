import networkx as nx
from graph_db import DeveloperMemoryGraphDB


class GraphAnalyticsEngine:
    def __init__(self, db: DeveloperMemoryGraphDB):
        self.db = db

    def build_networkx_graph(self) -> nx.DiGraph:
        G = nx.DiGraph()
        with self.db.driver.session() as session:
            nodes_result = session.run(
                """
                MATCH (n)
                RETURN n.id AS id, labels(n)[0] AS label, n.name AS name, n.summary AS summary
                """
            )
            for record in nodes_result:
                G.add_node(
                    record["id"],
                    label=record["label"],
                    name=record["name"],
                    summary=record["summary"],
                )

            edges_result = session.run(
                """
                MATCH (a)-[r]->(b)
                RETURN a.id AS source, b.id AS target, type(r) AS relation, r.context AS context
                """
            )
            for record in edges_result:
                G.add_edge(
                    record["source"],
                    record["target"],
                    relation=record["relation"],
                    context=record["context"],
                )
        return G

    def compute_metrics(self) -> dict:
        G = self.build_networkx_graph()
        if G.number_of_nodes() == 0:
            return {"error": "Graph is empty. Ingest some logs first."}

        degree_centrality = nx.degree_centrality(G)
        betweenness_centrality = nx.betweenness_centrality(G)
        pagerank = nx.pagerank(G, alpha=0.85)

        ranked_nodes = []
        for node_id, data in G.nodes(data=True):
            ranked_nodes.append(
                {
                    "id": node_id,
                    "label": data.get("label", "Unknown"),
                    "name": data.get("name", node_id),
                    "in_degree": G.in_degree(node_id),
                    "out_degree": G.out_degree(node_id),
                    "degree_centrality": round(degree_centrality[node_id], 4),
                    "betweenness_centrality": round(betweenness_centrality[node_id], 4),
                    "pagerank": round(pagerank[node_id], 4),
                }
            )

        ranked_nodes.sort(key=lambda x: x["degree_centrality"], reverse=True)

        tech_nodes = [n for n in ranked_nodes if n["label"] == "Technology"]
        bottlenecks = [n for n in ranked_nodes if n["betweenness_centrality"] > 0]

        return {
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges(),
            "density": round(nx.density(G), 4),
            "top_central_nodes": ranked_nodes[:5],
            "architectural_bottlenecks": bottlenecks,
            "technology_footprint": tech_nodes,
            "all_nodes": ranked_nodes,
        }


if __name__ == "__main__":
    db = DeveloperMemoryGraphDB()
    try:
        engine = GraphAnalyticsEngine(db)
        report = engine.compute_metrics()

        print("=== DEVELOPER MEMORY GRAPH ANALYTICS ===", flush=True)
        print(f"Total Nodes: {report['total_nodes']} | Total Edges: {report['total_edges']} | Density: {report['density']}")

        print("\nTop Central Nodes (Degree & PageRank):")
        for node in report["top_central_nodes"]:
            print(
                f"  - [{node['label']}] {node['id']} | "
                f"Degree: {node['degree_centrality']} | "
                f"Betweenness: {node['betweenness_centrality']} | "
                f"PageRank: {node['pagerank']}"
            )
    finally:
        db.close()