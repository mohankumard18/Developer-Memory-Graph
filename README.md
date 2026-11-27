# Developer Memory Graph – AI Analytics Platform

> **Live Demo:** https://developer-memory-graph.onrender.com#
>🧠 Developer Memory Graph – AI Analytics Platform

> Turn scattered developer activity (repositories, commits, issues, technologies) into a living **knowledge graph** you can explore in 3D, rank with graph analytics, and question in plain English.

> **Live Demo:** [https://developer-memory-graph.onrender.com](https://developer-memory-graph.onrender.com)
> *(Note: Hosted on Render's free tier. Allow ~40 seconds on the initial request if the service is waking from sleep.)*

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Neo4j](https://img.shields.io/badge/Neo4j-008CC1?style=for-the-badge&logo=neo4j&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)

<img width="1848" height="1138" alt="devgraphDASHBOARD1 png" src="https://github.com/user-attachments/assets/ccd27f8f-91f2-4d1a-aa4b-c4c0ac8a3538" />

## 💡 The Problem

Developer knowledge is scattered. Decisions live in commit messages, bugs live in issues, and context lives in people's heads. Weeks later, nobody remembers **who fixed what, why a technology was chosen, or which parts of a project matter most.**

## ✅ The Solution

Developer Memory Graph automatically extracts **entities and relationships** from developer activity, stores them in a **Neo4j graph database**, and gives you three ways to understand them:

1. **See it:** an interactive 3D graph explorer
2. **Measure it:** network analytics (Degree, Betweenness, PageRank)
3. **Ask it:** an AI question-answering engine grounded in the graph (RAG)

---

## 📸 Screenshots

### Interactive 3D Graph Explorer
Developers, repositories, technologies, issues and commits shown as connected spherical nodes with orbital animation. Filter by entity type or relation, search nodes, go fullscreen, or download the view.

![3D Graph Explorer](assets/graph-explorer.png)

### Network Analytics
Every entity is scored with **Degree**, **Betweenness** and **PageRank** to reveal the most influential repositories, developers and commits.

![Network Analytics](assets/analytics.png)

<!-- Uncomment after adding the screenshot
### Ask the Graph (RAG)
Ask questions in plain English and get answers grounded in your own graph data.

![RAG Query](assets/rag-query.png)
-->

---

## ✨ Features

| Feature | What it does |
|---|---|
| 📥 **Repository Import** | Paste a GitHub repository URL and import its developers, commits, issues and tech stack as graph nodes and links |
| 📝 **Activity Processing** | Type activity in plain language (e.g. *"Developer X fixed issue-15 using FastAPI"*) and the extractor turns it into nodes and relationships |
| 🌐 **3D Graph Explorer** | Interactive visualization with spherical nodes, orbital animation, zoom/pan controls, search, filters and export |
| 📊 **Network Analytics** | Degree, Betweenness and PageRank scores for every entity, plus Top Developers, Top Repositories and Most Connected Entities panels |
| 🤖 **RAG Question Answering** | Ask about repositories, commits or technologies and get answers grounded in the knowledge graph |
| 🏷️ **Typed Relationships** | Relations such as `CONTRIBUTED_TO` link commits, developers, repositories, issues and technologies |

---

## 🏗️ Architecture

```
GitHub repo / activity text
          │
          ▼
   ┌─────────────┐     entities + relationships
   │ extractor.py│ ───────────────────────────────┐
   └─────────────┘                                │
                                                  ▼
 ┌────────────┐   Cypher (batched UNWIND)   ┌──────────────┐
 │  app.py    │ ◄─────────────────────────► │  graph_db.py │ ──► Neo4j
 │  (FastAPI) │                             └──────────────┘
 └────┬───────┘
      │
      ├──► analytics.py   → Degree · Betweenness · PageRank
      ├──► rag_engine.py  → graph context + LLM → grounded answers
      └──► static/        → 3D Graph Explorer UI
```

---

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI
- **Graph Database:** Neo4j (batched `UNWIND` writes for fast inserts)
- **Graph Analytics:** Degree, Betweenness Centrality, PageRank
- **AI:** Retrieval-Augmented Generation (RAG) over the knowledge graph
- **Frontend:** HTML, CSS, JavaScript (3D graph visualization)
- **Deployment:** Render

---

## 📁 Project Structure

```
Developer-Memory-Graph/
├── app.py            # FastAPI application and API routes
├── extractor.py      # Entity & relationship extraction
├── graph_db.py       # Neo4j connection and batched graph writes
├── analytics.py      # PageRank, Degree and Betweenness analytics
├── rag_engine.py     # RAG question-answering over the graph
├── schemas.py        # Request/response data models
├── static/           # Frontend: 3D Graph Explorer
├── assets/           # README screenshots
└── requirements.txt  # Python dependencies
```

---

## 🚀 Run Locally

**1. Clone the repository**
```bash
git clone https://github.com/mohankumard18/Developer-Memory-Graph.git
cd Developer-Memory-Graph
```

**2. Create a virtual environment and install dependencies**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
```

**3. Configure environment variables** (create a `.env` file)
```env
NEO4J_URI=your_neo4j_uri
NEO4J_USER=your_neo4j_username
NEO4J_PASSWORD=your_neo4j_password
```
Add the API key for your AI model provider here as well.

**4. Start the server**
```bash
uvicorn app:app --reload
```

**5. Open** `http://127.0.0.1:8000`

---

## 🧩 Challenges I Solved

- **Edges pointing to the wrong nodes:** fixed the `target_id` and `relation_type` mapping in `graph_db.py` so relationships link the right entities.
- **Slow graph writes:** replaced one-by-one inserts with **batched Neo4j `UNWIND` writes**.
- **PageRank performance and reliability:** replaced the `scipy` PageRank implementation in `analytics.py`.

---

## 🔮 Roadmap

- [ ] Support for more data sources (pull requests, code reviews, docs)
- [ ] Timeline view to see how the graph evolves over time
- [ ] Multi-repository comparison
- [ ] User authentication and saved graphs

---

## 👤 Author

**Duppada Mohan Kumar**
Final-year B.Tech CSE (Data Science) student

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/mohankumarduppada)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/mohankumard18)

⭐ If you found this project interesting, consider giving it a star!
       FastAPI REST Backend + Vis.js UI
