import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from schemas import ExtractedMemoryGraph

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(timeout=20000),
)

SYSTEM_PROMPT = """
You are an expert software engineering knowledge graph extractor.
Extract structured entities (Developer, Repository, Technology, Issue, Commit) and directed
relationships (CONTRIBUTED_TO, USES_TECH, RESOLVED, AUTHORED, DEPENDS_ON, REPORTED)
from developer logs, commit messages, PR descriptions, and incident notes.

Rules:
1. Normalize entity IDs to lowercase, hyphen-separated canonical slugs (e.g., 'mohankumard18', 'python', 'mysql-8').
2. Ensure every relationship's source_id and target_id strictly match an extracted entity's id.
3. Keep summaries concise, technical, and factual.
"""


def get_candidate_models() -> list[str]:
    candidates = candidates = ["gemini-3.1-flash-lite", "gemini-3.8-flash"]
    try:
        for m in client.models.list():
            name = m.name.replace("models/", "")
            if (
                "gemini" in name
                and "embedding" not in name
                and "imagen" not in name
                and "veo" not in name
                and "tts" not in name
                and "robotics" not in name
                and name not in candidates
            ):
                candidates.append(name)
    except Exception:
        pass
    return candidates


def extract_memory_from_text(raw_text: str) -> ExtractedMemoryGraph:
    models_to_try = get_candidate_models()
    for model_name in models_to_try:
        for attempt in range(2):
            try:
                print(f"Calling {model_name} (attempt {attempt + 1})...", flush=True)
                response = client.models.generate_content(
                    model=model_name,
                    contents=raw_text,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=ExtractedMemoryGraph,
                        temperature=0.1,
                    ),
                )
                return ExtractedMemoryGraph.model_validate_json(response.text)
            except Exception as e:
                print(f"{model_name} failed: {e}", flush=True)
                if "503" in str(e) and attempt == 0:
                    time.sleep(3)
                    continue
                break
    raise RuntimeError("No available Gemini model succeeded.")


if __name__ == "__main__":
    sample_log = """
    Developer mohankumard18 pushed commit commit-a1b2 to repository library-management-system-sql,
    which uses MySQL 8.0 and SQL Triggers. The commit resolved issue-104 (automated overdue fine calculation
    failing on leap-year due dates) and added composite indexing on book_issues.
    """
    graph = extract_memory_from_text(sample_log)
    print(graph.model_dump_json(indent=2), flush=True)