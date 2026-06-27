from __future__ import annotations

from pathlib import Path

from fastapi import Cookie, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from analysis.classify import classify_batch
from analysis.cluster import compute_insights
from analysis.rag import CANONICAL_QUESTIONS, ask
from analysis.store import ReviewStore
from discovery.config import get_settings
from ingest.normalize import load_corpus
from ingest.seed_corpus import build_seed_corpus
from mvp.auth import (
    client_from_session,
    exchange_callback,
    get_login_redirect,
    refreshed_session_cookie,
)
from mvp.bridge import BridgeError, create_bridge_session, restore_bridge_session, save_bridge_to_playlist
from mvp.chart_catalog import catalog_count, search_tracks as chart_search
from mvp.parse import parse_track_id, resolve_track_query
from mvp.persistence import ensure_schema, log_bridge_event, metrics_summary
from mvp.rate_limit import enforce_rate_limit
from mvp.track_lookup import enrich_track_meta, lookup_track
from mvp.session import (
    COOKIE_OAUTH,
    COOKIE_SESSION,
    clear_cookie,
    oauth_cookie_kwargs,
    session_cookie_kwargs,
)
from mvp.spotify_client import SpotifyAPIError, SpotifyClient, normalize_track

app = FastAPI(
    title="Spotify Discovery Engine",
    description="AI-powered review analysis + Bridge Sessions MVP",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class AskBody(BaseModel):
    question: str


class BridgeBody(BaseModel):
    intent: str
    anchor: str | None = None
    demo: bool = False


class SavePlaylistBody(BaseModel):
    track_ids: list[str]
    anchor_track: str = "Bridge Session"
    intent: str = ""


class RestoreBridgeBody(BaseModel):
    intent: str
    anchor: str | None = None
    track_ids: list[str]


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


def _bridge_error(exc: BridgeError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content={"error": str(exc), "code": exc.code},
    )


def _spotify_error(exc: SpotifyAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status or 502,
        content={"error": str(exc), "code": exc.code},
    )


@app.on_event("startup")
def startup() -> None:
    _ensure_indexed()
    ensure_schema()


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    store = ReviewStore()
    return {
        "status": "ok",
        "reviews_indexed": store.count(),
        "spotify_configured": settings.spotify_configured,
        "catalog_search": settings.spotify_configured or catalog_count() > 0,
        "chart_catalog_tracks": catalog_count(),
        "llm_configured": settings.bridge_planner_configured,
        "allow_demo_mode": settings.allow_demo_mode,
        "persistence_enabled": settings.persistence_enabled,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
    }


@app.get("/api/metrics")
def api_metrics() -> dict:
    settings = get_settings()
    base = {
        "status": "ok",
        "llm_configured": settings.bridge_planner_configured,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
    }
    base.update(metrics_summary())
    return base


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
def api_ask(body: AskBody, request: Request) -> dict:
    enforce_rate_limit(request, scope="ask")
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


# --- Auth ---

@app.get("/api/auth/status")
def auth_status(bridge_session: str | None = Cookie(default=None, alias=COOKIE_SESSION)) -> dict:
    settings = get_settings()
    client = client_from_session(bridge_session)
    if client:
        try:
            me = client.me()
            return {
                "connected": True,
                "display_name": me.get("display_name") or me.get("id"),
                "demo": False,
            }
        except SpotifyAPIError:
            return {"connected": False, "demo": False, "spotify_configured": settings.spotify_configured}
    return {
        "connected": False,
        "demo": settings.allow_demo_mode,
        "spotify_configured": settings.spotify_configured,
    }


@app.get("/mvp/login")
def mvp_login(response: Response) -> RedirectResponse:
    try:
        url, oauth_val = get_login_redirect()
    except SpotifyAPIError as e:
        raise HTTPException(503, str(e)) from e
    resp = RedirectResponse(url)
    resp.set_cookie(**oauth_cookie_kwargs(oauth_val))
    return resp


@app.get("/mvp/callback")
def mvp_callback(
    response: Response,
    code: str,
    state: str = "",
    bridge_oauth: str | None = Cookie(default=None, alias=COOKIE_OAUTH),
) -> RedirectResponse:
    try:
        session_val = exchange_callback(code, state, bridge_oauth)
    except SpotifyAPIError as e:
        return RedirectResponse(f"/#bridge?error={e.code}")
    resp = RedirectResponse("/#bridge")
    resp.set_cookie(**session_cookie_kwargs(session_val))
    resp.set_cookie(**clear_cookie(COOKIE_OAUTH))
    return resp


@app.post("/mvp/logout")
def mvp_logout(response: Response) -> dict:
    resp = JSONResponse({"ok": True})
    resp.set_cookie(**clear_cookie(COOKIE_SESSION))
    return resp


@app.get("/mvp/demo-token")
def mvp_demo_token() -> dict:
    settings = get_settings()
    if not settings.allow_demo_mode:
        raise HTTPException(403, "Demo mode disabled")
    return {"demo_mode": True}


# --- Bridge ---

@app.get("/api/track/{track_ref:path}")
def api_track_lookup(track_ref: str) -> dict:
    tid = parse_track_id(track_ref)
    if not tid:
        raise HTTPException(400, "Invalid Spotify track URL or ID")
    track = lookup_track(tid)
    if not track:
        raise HTTPException(404, "Track not found on Spotify")
    return track


@app.post("/api/track/lookup")
def api_track_lookup_post(
    body: dict,
    bridge_session: str | None = Cookie(default=None, alias=COOKIE_SESSION),
) -> dict:
    raw = body.get("anchor", "").strip()
    tid = resolve_track_query(raw)
    if not tid:
        raise HTTPException(
            400,
            "No match — try a song name (e.g. Blinding Lights) or paste a Spotify track link",
        )

    client = client_from_session(bridge_session)
    track = lookup_track(tid, client)
    if not track:
        raise HTTPException(404, "Track not found on Spotify — check the link")
    return track


@app.get("/api/search/tracks")
def api_search_tracks(q: str) -> dict:
    query = q.strip()
    if not query:
        raise HTTPException(400, "Enter a song or artist to search")

    settings = get_settings()
    if settings.spotify_configured:
        try:
            client = SpotifyClient.from_client_credentials()
            items = [normalize_track(t) for t in client.search_tracks(query, limit=12)]
            return {"tracks": items, "mode": "spotify"}
        except SpotifyAPIError as e:
            raise HTTPException(e.status or 502, str(e)) from e

    hits = [enrich_track_meta(t) for t in chart_search(query, limit=12)]
    n = catalog_count()
    return {
        "tracks": hits,
        "mode": "chart_catalog",
        "hint": "Pick a track to set as your anchor — no login required.",
    }


@app.post("/api/bridge")
def api_bridge(
    body: BridgeBody,
    request: Request,
    bridge_session: str | None = Cookie(default=None, alias=COOKIE_SESSION),
) -> JSONResponse:
    enforce_rate_limit(request, scope="bridge")
    tid = resolve_track_query(body.anchor) if body.anchor else None
    if body.anchor and body.anchor.strip() and not tid:
        raise HTTPException(
            400,
            "Could not find that song — try the track title or a Spotify link",
        )
    client = None if body.demo else client_from_session(bridge_session)

    try:
        session = create_bridge_session(
            intent=body.intent,
            anchor_track_id=tid,
            client=client,
            force_demo=body.demo,
        )
    except BridgeError as e:
        return _bridge_error(e)
    except SpotifyAPIError as e:
        return _spotify_error(e)

    payload = session.model_dump()
    mode = "demo" if body.demo or not client else "live"
    payload["mode"] = mode
    log_bridge_event(
        intent=session.intent,
        anchor_id=session.anchor_id,
        track_ids=[t.track_id for t in session.tracks],
        planner=session.planner,
        mode=mode,
    )
    resp = JSONResponse(payload)
    new_cookie = refreshed_session_cookie(bridge_session)
    if new_cookie:
        resp.set_cookie(**session_cookie_kwargs(new_cookie))
    return resp


@app.post("/api/bridge/restore")
def api_bridge_restore(body: RestoreBridgeBody) -> JSONResponse:
    tid = resolve_track_query(body.anchor) if body.anchor else None
    try:
        session = restore_bridge_session(
            intent=body.intent,
            anchor_track_id=tid,
            track_ids=body.track_ids,
        )
    except BridgeError as e:
        return _bridge_error(e)

    payload = session.model_dump()
    payload["mode"] = "demo"
    return JSONResponse(payload)


@app.post("/api/bridge/save")
def api_bridge_save(
    body: SavePlaylistBody,
    bridge_session: str | None = Cookie(default=None, alias=COOKIE_SESSION),
) -> JSONResponse:
    client = client_from_session(bridge_session)
    if not client:
        return JSONResponse(
            status_code=401,
            content={"error": "Connect Spotify to save playlists.", "code": "auth_required"},
        )
    from discovery.models import BridgeSession, BridgeTrack

    tracks = [
        BridgeTrack(
            position=i + 1,
            track_id=tid,
            name="",
            artist="",
            spotify_url=f"https://open.spotify.com/track/{tid}",
            explanation="",
            novelty_score=0,
        )
        for i, tid in enumerate(body.track_ids)
    ]
    session = BridgeSession(
        anchor_track=body.anchor_track,
        intent=body.intent,
        tracks=tracks,
        session_summary="",
    )
    try:
        result = save_bridge_to_playlist(client, session)
    except SpotifyAPIError as e:
        return _spotify_error(e)

    resp = JSONResponse(result)
    new_cookie = refreshed_session_cookie(bridge_session)
    if new_cookie:
        resp.set_cookie(**session_cookie_kwargs(new_cookie))
    return resp


if WEB_DIR.exists():

    @app.get("/")
    def root() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/bridge.html")
    def bridge_page() -> FileResponse:
        return FileResponse(WEB_DIR / "bridge.html")

    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
