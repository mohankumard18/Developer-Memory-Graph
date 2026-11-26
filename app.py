import os
import json
import urllib.request
from urllib.parse import urlparse
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from schemas import ExtractedMemoryGraph
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


def extract_github_graph(owner: str, repo: str) -> ExtractedMemoryGraph:
    base_api = f"https://api.github.com/repos/{owner}/{repo}"

    repo_data = fetch_github_json(base_api)
    languages_data = fetch_github_json(f"{base_api}/languages")
    commits_data = fetch_github_json(f"{base_api}/commits?per_page=8")
    issues_data = fetch_github_json(f"{base_api}/issues?state=all&per_page=8")

    # Introspect field names on Relationship model in schemas.py so validation always matches
    rel_model = ExtractedMemoryGraph.model_fields["relationships"].annotation.__args__[0]
    rel_field_name = "type" if "type" in rel_model.model_fields else (
        "relation" if "relation" in rel_model.model_fields else next(
            k for k in rel_model.model_fields if k not in {"source", "target", "context"}
        )
    )

    def make_rel(src: str, tgt: str, rel_val: str, ctx: str) -> dict:
        payload = {"source": src, "target": tgt, rel_field_name: rel_val}
        if "context" in rel_model.model_fields:
            payload["context"] = ctx
        return payload

    entities: dict[str, dict] = {}
    relationships: list[dict] = []

    repo_id = repo.lower()
    owner_id = owner.lower()
    desc = repo_data.get("description") or f"GitHub repository owned by {owner}"

    entities[repo_id] = {"id": repo_id, "label": "Repository", "name": repo, "summary": desc}
    entities[owner_id] = {"id": owner_id, "label": "Developer", "name": owner, "summary": f"Repository owner {owner}"}
    relationships.append(make_rel(owner_id, repo_id, "CONTRIBUTED_TO", f"{owner} owns {repo}"))

    langs = list(languages_data.keys()) or ([repo_data["language"]] if repo_data.get("language") else [])
    for lang in langs:
        lang_id = lang.lower()
        entities[lang_id] = {
            "id": lang_id,
            "label": "Technology",
            "name": lang,
            "summary": f"Programming language/technology used in {repo}",
        }
        relationships.append(make_rel(repo_id, lang_id, "USES_TECH", f"{repo} uses {lang}"))

    for c in commits_data:
        sha = c.get("sha", "")[:7]
        if not sha:
            continue
        commit_id = f"commit-{sha}"
        author = (c.get("author") or {}).get("login") or (c.get("commit", {}).get("author", {}).get("name")) or owner
        author_id = author.lower()
        msg = c.get("commit", {}).get("message", "").splitlines()[0] or "Repository commit"

        entities.setdefault(
            author_id,
            {"id": author_id, "label": "Developer", "name": author, "summary": f"GitHub contributor {author}"},
        )
        entities[commit_id] = {"id": commit_id, "label": "Commit", "name": commit_id, "summary": msg}

        relationships.append(make_rel(author_id, commit_id, "AUTHORED", msg))
        relationships.append(make_rel(commit_id, repo_id, "CONTRIBUTED_TO", msg))

    for issue in issues_data:
        if "pull_request" in issue:
            continue
        num = issue.get("number")
        if num is None:
            continue
        issue_id = f"issue-{num}"
        title = issue.get("title", "Tracked issue")
        state = issue.get("state", "open")
        reporter = (issue.get("user") or {}).get("login") or owner
        reporter_id = reporter.lower()

        entities.setdefault(
            reporter_id,
            {"id": reporter_id, "label": "Developer", "name": reporter, "summary": f"GitHub contributor {reporter}"},
        )
        entities[issue_id] = {
            "id": issue_id,
            "label": "Issue",
            "name": issue_id,
            "summary": f"{title} (status: {state})",
        }
        relationships.append(make_rel(reporter_id, issue_id, "REPORTED", title))
        if state == "closed":
            relationships.append(make_rel(repo_id, issue_id, "RESOLVED", f"Closed issue: {title}"))

    return ExtractedMemoryGraph.model_validate(
        {"entities": list(entities.values()), "relationships": relationships}
    )


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
    try:
        extracted = extract_memory_from_text(req.log_text)
        db.ingest_graph(extracted)
        return {
            "status": "success",
            "entities_added": len(extracted.entities),
            "relationships_added": len(extracted.relationships),
            "extracted": extracted.model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


@app.post("/api/ingest-github")
def ingest_github_repo(req: GitHubIngestRequest):
    if not req.repo_url.strip():
        raise HTTPException(status_code=400, detail="GitHub repository URL cannot be empty.")
    try:
        owner, repo = parse_github_owner_repo(req.repo_url)
        extracted = extract_github_graph(owner, repo)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"GitHub fetch failed: {e}")

    try:
        existing_owners = db.get_current_owners()
        if not existing_owners or existing_owners != {owner.lower()}:
            db.clear_graph()

        db.ingest_graph(extracted)
        db.set_repo_owner(repo, owner)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neo4j sync failed: {e}")

    return {
        "status": "success",
        "owner": owner,
        "entities_added": len(extracted.entities),
        "relationships_added": len(extracted.relationships),
    }


@app.post("/api/ask")
def ask_memory(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    try:
        return rag_engine.ask(req.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GraphRAG query failed: {e}")