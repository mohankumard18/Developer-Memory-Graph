import networkx as nx
from graph_db import DeveloperMemoryGraphDB


class GraphAnalyticsEngine:
    def __init__(self, db: DeveloperMemoryGraphDB):
        self.db = db

    def build_networkx_graph(self) -> nx.DiGraph:
        nodes, edges = self.db.fetch_all_graph()
        G = nx.DiGraph()
        for n in nodes:
            if n.get("id"):
                G.add_node(
                    n["id"],
                    label=n.get("label", "Entity"),
                    name=n.get("name", n["id"]),
                    summary=n.get("summary", ""),
                )
        for e in edges:
            src, tgt = e.get("source"), e.get("target")
            if src and tgt:
                G.add_edge(
                    src,
                    tgt,
                    relation=e.get("relation", "RELATED_TO"),
                    context=e.get("context", ""),
                )
        return G

    def compute_metrics(self) -> dict:
        G = self.build_networkx_graph()
        num_nodes = G.number_of_nodes()
        num_edges = G.number_of_edges()

        if num_nodes == 0:
            return {
                "total_nodes": 0,
                "total_edges": 0,
                "density": 0.0,
                "top_central_nodes": [],
            }

        degree_c = nx.degree_centrality(G)
        betweenness_c = nx.betweenness_centrality(G)
        # Pure-Python power iteration avoids heavy scipy memory spikes on 512MB cloud containers
        pagerank_c = self._pure_python_pagerank(G)

        ranked = []
        for node_id, data in G.nodes(data=True):
            ranked.append(
                {
                    "id": node_id,
                    "label": data.get("label", "Entity"),
                    "degree_centrality": round(degree_c.get(node_id, 0.0), 4),
                    "betweenness_centrality": round(betweenness_c.get(node_id, 0.0), 4),
                    "pagerank": round(pagerank_c.get(node_id, 0.0), 4),
                }
            )

        ranked.sort(key=lambda x: (x["degree_centrality"], x["pagerank"]), reverse=True)
        return {
            "total_nodes": num_nodes,
            "total_edges": num_edges,
            "density": round(nx.density(G), 4),
            "top_central_nodes": ranked[:10],
        }

    def _pure_python_pagerank(self, G: nx.DiGraph, alpha: float = 0.85, max_iter: int = 50) -> dict:
        nodes = list(G.nodes())
        n = len(nodes)
        if n == 0:
            return {}
        rank = {node: 1.0 / n for node in nodes}
        for _ in range(max_iter):
            new_rank = {node: (1.0 - alpha) / n for node in nodes}
            dangling_sum = sum(rank[node] for node in nodes if G.out_degree(node) == 0)
            for node in nodes:
                new_rank[node] += alpha * dangling_sum / n
                out_deg = G.out_degree(node)
                if out_deg > 0:
                    share = alpha * rank[node] / out_deg
                    for nbr in G.successors(node):
                        new_rank[nbr] += share
            rank = new_rank
        return rank