# Developer Memory Graph – AI Analytics Platform

An AI-powered engineering knowledge graph platform that extracts structured software entities and relationships from public GitHub repositories and raw engineering logs, persists them in **Neo4j AuraDB**, computes **NetworkX** centrality/PageRank metrics, and answers natural-language engineering queries via **Hybrid GraphRAG**.

## Tech Stack
- **Backend:** FastAPI, Uvicorn, Python
- **AI Extraction & GraphRAG:** Google Gemini API (`google-genai`) with Pydantic Structured Outputs
- **Graph Database:** Neo4j AuraDB (Cloud)
- **Graph Analytics:** NetworkX (Degree Centrality, Betweenness Centrality, PageRank)
- **Frontend:** HTML5, CSS3, JavaScript, Vis.js Network Visualization

## Local Setup
1. Clone the repository and create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt