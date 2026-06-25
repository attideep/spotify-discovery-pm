from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from analysis.classify import classify_batch
from analysis.cluster import compute_insights
from analysis.rag import CANONICAL_QUESTIONS, ask
from analysis.store import ReviewStore
from discovery.config import get_settings
from ingest.normalize import load_corpus
from ingest.seed_corpus import build_seed_corpus
from mvp.bridge import create_bridge_session, get_auth_url, handle_callback

app = FastAPI(
    title="Spotify Discovery Engine",
    description="AI-powered review analysis + Bridge Sessions MVP",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class AskBody(BaseModel):
    question: str


class BridgeBody(BaseModel):
    intent: str
    anchor_track_id: str | None = None
    access_token: str | None = None


def _ensure_indexed() -> ReviewStore:
    store = ReviewStore()
    if store.count() == 0:
        settings = get_settings()
        corpus_path = Path(settings.corpus_path)
        if not corpus_path.exists():
            build_seed_corpus(str(corpus_path))
        records = load_corpus(corpus_path)
        classified = classify_batch(records)
        for r in classified:
            store.upsert(r)
    return store


@app.on_event("startup")
def startup() -> None:
    _ensure_indexed()


@app.get("/health")
def health() -> dict:
    store = ReviewStore()
    return {"status": "ok", "reviews_indexed": store.count(), "mock_mode": get_settings().mock_mode}


@app.post("/api/ingest")
def api_ingest() -> dict:
    settings = get_settings()
    if settings.mock_mode:
        path = build_seed_corpus(settings.corpus_path)
    else:
        from ingest.scrapers import run_ingest

        path = run_ingest(settings.corpus_path)
    records = load_corpus(path)
    store = ReviewStore()
    for r in classify_batch(records):
        store.upsert(r)
    return {"indexed": store.count(), "corpus": path}


@app.get("/api/insights")
def api_insights() -> dict:
    store = _ensure_indexed()
    insights = compute_insights(store)
    records = store.load_all()
    segments: dict[str, int] = {}
    for r in records:
        segments[r.segment] = segments.get(r.segment, 0) + 1
    return {
        "total_reviews": len(records),
        "themes": [i.model_dump() for i in insights],
        "segments": segments,
        "canonical_questions": CANONICAL_QUESTIONS,
    }


@app.post("/api/ask")
def api_ask(body: AskBody) -> dict:
    store = _ensure_indexed()
    resp = ask(body.question, store)
    return resp.model_dump()


@app.get("/api/ask/{question_key}")
def api_ask_canonical(question_key: str) -> dict:
    if question_key not in CANONICAL_QUESTIONS:
        raise HTTPException(404, "Unknown question key")
    store = _ensure_indexed()
    resp = ask(f"q:{question_key}", store)
    return resp.model_dump()


# --- Bridge Sessions MVP ---

@app.get("/mvp/login")
def mvp_login() -> RedirectResponse:
    return RedirectResponse(get_auth_url())


@app.get("/mvp/callback")
def mvp_callback(code: str, state: str = "") -> RedirectResponse:
    token = handle_callback(code)
    return RedirectResponse(f"/?token={token['access_token']}#bridge")


@app.get("/mvp/demo-token")
def mvp_demo_token() -> dict:
    return {"access_token": "demo", "demo_mode": True}


@app.post("/api/bridge")
def api_bridge(body: BridgeBody) -> dict:
    session = create_bridge_session(
        intent=body.intent,
        anchor_track_id=body.anchor_track_id,
        access_token=body.access_token or "demo",
    )
    return session.model_dump()


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

    @app.get("/")
    def root() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/bridge.html")
    def bridge_page() -> FileResponse:
        return FileResponse(WEB_DIR / "bridge.html")
