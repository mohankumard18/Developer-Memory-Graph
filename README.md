# Developer Memory Graph – AI Analytics Platform

> **Live Demo:** https://developer-memory-graph.onrender.com
> *(Note: Hosted on Render's free tier—allow ~40 seconds on the initial request if the service is waking from sleep.)*

An AI-powered **Engineering Knowledge Graph & GraphRAG Analytics Platform** that transforms unstructured developer logs and live public GitHub repositories into a connected **Neo4j AuraDB** knowledge graph, computes **NetworkX** graph centrality metrics, and answers technical questions using **Hybrid GraphRAG** grounded in live graph traversals.

---

## Key Features

- **1-Click Public GitHub Repository Importer:** Fetches repository metadata, programming languages, commit history, and tracked issues from the GitHub REST API and merges them into a unified multi-repository knowledge graph.
- **Structured AI Knowledge Extraction:** Uses **Google Gemini (`google-genai`)** with **Pydantic** structured schemas to extract canonical `Developer`, `Repository`, `Commit`, `Issue`, and `Technology` nodes alongside typed directional relationships (`AUTHORED`, `CONTRIBUTED_TO`, `RESOLVED`, `USES_TECH`, `REPORTED`).
- **Idempotent Cloud Graph Persistence:** Uses Cypher `MERGE` operations in **Neo4j AuraDB** so shared developers and technologies automatically link separate repositories together without creating duplicate nodes.
- **Real-Time Graph Science Analytics:** Converts the live Neo4j graph into a **NetworkX** directed graph to compute **Degree Centrality**, **Betweenness Centrality**, **PageRank**, and overall **Graph Density**.
- **Hallucination-Free Hybrid GraphRAG Q&A:** Retrieves matching subgraphs directly from Neo4j before synthesizing answers with Gemini, enforcing explicit node citations.

---

## System Architecture

```text
GitHub REST API / Raw Engineering Logs
                 │
                 ▼
   Google Gemini Structured Extraction (Pydantic)
                 │
                 ▼
      Neo4j AuraDB Cloud Graph (Cypher MERGE)
           │                     │
           ▼                     ▼
  NetworkX Analytics     Hybrid GraphRAG Engine
 (PageRank, Centrality)  (Subgraph Traversal + LLM)
           │                     │
           └──────────┬──────────┘
                      ▼
       FastAPI REST Backend + Vis.js UI
