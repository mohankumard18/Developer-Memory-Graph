import os
import json
import urllib.request
from urllib.parse import urlparse
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from extractor import extract_memory_from_text
from graph_db import DeveloperMemoryGraphDB
from analytics import GraphAnalyticsEngine
from rag_engine import GraphRAGEngine

db: DeveloperMemoryGraphDB | None = None
analytics_engine: GraphAnalyticsEngine | None = None
rag_engine: GraphRAGEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, analytics_engine, rag_engine
    db = DeveloperMemoryGraphDB()
    db.verify_connection()
    analytics_engine = GraphAnalyticsEngine(db)
    rag_engine = GraphRAGEngine(db)
    yield
    if db:
        db.close()


app = FastAPI(title="Developer Memory Graph – AI Analytics Platform", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


class IngestRequest(BaseModel):
    log_text: str


class GitHubIngestRequest(BaseModel):
    repo_url: str


class AskRequest(BaseModel):
    question: str


def fetch_github_json(url: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Developer-Memory-Graph-App",
    }
    gh_token = os.getenv("GITHUB_TOKEN")
    if gh_token:
        headers["Authorization"] = f"Bearer {gh_token}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_github_owner_repo(repo_url: str) -> tuple[str, str]:
    parsed = urlparse(repo_url.strip().rstrip("/"))
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise ValueError("Invalid GitHub URL. Expected format: https://github.com/owner/repo")
    return parts[0], parts[1].removesuffix(".git")


def build_github_summary_log(owner: str, repo: str) -> str:
    base_api = f"https://api.github.com/repos/{owner}/{repo}"

    repo_data = fetch_github_json(base_api)
    languages_data = fetch_github_json(f"{base_api}/languages")
    commits_data = fetch_github_json(f"{base_api}/commits?per_page=8")
    issues_data = fetch_github_json(f"{base_api}/issues?state=all&per_page=8")

    langs = ", ".join(languages_data.keys()) or repo_data.get("language") or "Unknown"
    lines = [
        f"Repository: {repo} (owned by developer {owner}).",
        f"Description: {repo_data.get('description') or 'Software repository'}.",
        f"Technologies used: {langs}.",
        "Recent Commits:",
    ]

    for c in commits_data:
        sha = c.get("sha", "")[:7]
        author = (c.get("author") or {}).get("login") or (c.get("commit", {}).get("author", {}).get("name")) or owner
        msg = c.get("commit", {}).get("message", "").splitlines()[0]
        lines.append(f"- Developer {author} authored commit commit-{sha} in repository {repo}: {msg}")

    real_issues = [i for i in issues_data if "pull_request" not in i]
    if real_issues:
        lines.append("Tracked Issues:")
        for issue in real_issues:
            num = issue.get("number")
            title = issue.get("title", "")
            state = issue.get("state", "open")
            reporter = (issue.get("user") or {}).get("login") or owner
            lines.append(f"- Developer {reporter} reported issue-{num} ({title}, status: {state}) in repository {repo}.")

    return "\n".join(lines)


@app.get("/")
def serve_home():
    return FileResponse("static/index.html")


@app.get("/api/graph")
def get_graph_data():
    G = analytics_engine.build_networkx_graph()
    nodes = [
        {
            "id": node_id,
            "label": data.get("label", "Entity"),
            "name": data.get("name", node_id),
            "summary": data.get("summary", ""),
        }
        for node_id, data in G.nodes(data=True)
    ]
    edges = [
        {
            "from": src,
            "to": tgt,
            "label": data.get("relation", ""),
            "title": data.get("context", ""),
        }
        for src, tgt, data in G.edges(data=True)
    ]
    metrics = analytics_engine.compute_metrics()
    return {"nodes": nodes, "edges": edges, "metrics": metrics}


@app.post("/api/ingest")
def ingest_log(req: IngestRequest):
    if not req.log_text.strip():
        raise HTTPException(status_code=400, detail="Log text cannot be empty.")
    extracted = extract_memory_from_text(req.log_text)
    db.ingest_graph(extracted)
    return {
        "status": "success",
        "entities_added": len(extracted.entities),
        "relationships_added": len(extracted.relationships),
        "extracted": extracted.model_dump(),
    }


@app.post("/api/ingest-github")
def ingest_github_repo(req: GitHubIngestRequest):
    if not req.repo_url.strip():
        raise HTTPException(status_code=400, detail="GitHub repository URL cannot be empty.")
    try:
        owner, repo = parse_github_owner_repo(req.repo_url)
        summary_log = build_github_summary_log(owner, repo)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"GitHub fetch failed: {e}")

    existing_owners = db.get_current_owners()
    if not existing_owners or existing_owners != {owner.lower()}:
        db.clear_graph()

    extracted = extract_memory_from_text(summary_log)
    db.ingest_graph(extracted)
    db.set_repo_owner(repo, owner)

    return {
        "status": "success",
        "owner": owner,
        "entities_added": len(extracted.entities),
        "relationships_added": len(extracted.relationships),
        "fetched_log": summary_log,
    }


@app.post("/api/ask")
def ask_memory(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    return rag_engine.ask(req.question)