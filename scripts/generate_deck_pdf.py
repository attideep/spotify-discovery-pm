#!/usr/bin/env python3
"""Generate NL Spotify.pdf deck (10 slides, min 14pt)."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent.parent / "deck" / "NL Spotify.pdf"

SLIDES = [
    ("Repeat listening is Spotify's hidden retention risk", [
        "Spotify Growth PM — AI Discovery Engine + MVP",
        "Millions of users. World-class recsys. Yet comfort loops dominate.",
    ]),
    ("Strategic goal: meaningful discovery, not more of the same", [
        "Growth mandate: increase novel listening without hurting continuity",
        "Collaborative filtering reinforces taste clusters → repeat playlists",
        "Opportunity: AI-native experiences that explain the path to new music",
    ]),
    ("How we mined 1,000+ voices at scale", [
        "Ingest → Normalize → Classify (LLM) → Embed → RAG Q&A",
        "Sources: App Store, Play Store, Reddit, Hacker News (553+ indexed)",
        "Workflow: Review Discovery Engine UI + /docs API",
    ]),
    ("Users don't hate discovery — they hate opaque jumps", [
        '"I just replay my 2019 playlists because at least I know what I\'m getting."',
        "Comfort loop, discovery fatigue, irrelevant recs, algorithm anxiety",
        "Explainability is the #1 unmet need across segments",
    ]),
    ("Six segments, one acute pain: Comfort Loop Curators", [
        "Comfort Loop Curator ★ — high cost to leave safe playlists",
        "Algorithm Skeptic, Context Switcher, Social Discoverer",
        "Time-Poor Commuter, Genre Explorer Burned",
    ]),
    ("What 6 archetype interviews confirmed", [
        "Method: corpus triangulation + synthesized public user voice",
        "70%+ listening from Liked Songs for target segment",
        "#1 unmet need: Tell me WHY this next track",
    ]),
    ("Root cause: no bridge between familiar and novel", [
        "Recsys optimizes retention → reinforces clusters",
        "Discovery is batch-oriented, not moment-aware",
        "Familiar → novel jump too abrupt → skip → comfort retreat",
    ]),
    ("Bridge Sessions: AI that explains the path, not just the playlist", [
        "8-track journey from anchor → novel artist",
        "Intent-aware: Like Khruangbin but more energetic for a run",
        "Spotify deep links — demo + live OAuth",
    ]),
    ("Why LLMs succeed where collaborative filtering plateaus", [
        "CF: play probability | Bridge: understood novelty",
        "CF: black-box | Bridge: explainable transitions",
        "CF: weekly batch | Bridge: real-time, mood-aware",
    ]),
    ("Success metrics, rollout, and test links", [
        "Metrics: bridge completion >40%, save rate >15%",
        "Review Engine: https://spotify-discovery-pm.vercel.app",
        "Bridge Sessions: https://spotify-discovery-pm.vercel.app/bridge.html",
        "Research: interviews/, quote_bank.md",
    ]),
]

W, H = landscape((13.333 * inch, 7.5 * inch))  # 16:9


def draw_slide(c: canvas.Canvas, title: str, bullets: list[str]) -> None:
    c.setFillColor(colors.HexColor("#121212"))
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#1DB954"))
    c.setFont("Helvetica-Bold", 28)
    c.drawString(0.6 * inch, H - 1.1 * inch, title[:90])
    c.setFillColor(colors.HexColor("#B3B3B3"))
    c.setFont("Helvetica", 16)
    y = H - 1.8 * inch
    for b in bullets:
        for line in _wrap(b, 85):
            c.drawString(0.8 * inch, y, line)
            y -= 0.32 * inch
        y -= 0.12 * inch


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines or [""]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=(W, H))
    for title, bullets in SLIDES:
        draw_slide(c, title, bullets)
        c.showPage()
    c.save()
    print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
