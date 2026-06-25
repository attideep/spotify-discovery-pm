from __future__ import annotations

import json
import re

from discovery.config import get_settings
from discovery.models import AskResponse
from analysis.store import ReviewStore

_ANSWER_FOOTER_RE = re.compile(
    r"\n+(?:Note|Notes|Additionally|In summary|Overall|To summarize|"
    r"Based on the (?:above|evidence|reviews)|"
    r"It(?:'s| is) (?:worth|important) noting)[:\s].*$",
    re.I | re.S,
)


def _clean_answer(text: str) -> str:
    """Strip trailing meta-commentary and filler the model sometimes adds."""
    if not text:
        return text
    cleaned = _ANSWER_FOOTER_RE.sub("", text.strip()).strip()
    cleaned = re.sub(r"\s*\[(?:id\d+|r\d+)\]\s*$", "", cleaned, flags=re.I)
    return cleaned


CANONICAL_QUESTIONS = {
    "why_struggle": "Why do users struggle to discover new music?",
    "rec_frustrations": "What are the most common frustrations with recommendations?",
    "listening_behaviors": "What listening behaviors are users trying to achieve?",
    "repeat_causes": "What causes users to repeatedly listen to the same content?",
    "segment_challenges": "Which user segments experience different discovery challenges?",
    "unmet_needs": "What unmet needs emerge consistently across reviews?",
}


def _mock_answer(question: str, hits: list) -> AskResponse:
    ctx = "\n".join(f"- [{h[0].id}] {h[0].text[:180]}" for h in hits[:6])
    answers = {
        "why_struggle": (
            "Discovery has high cognitive cost and low trust ROI. Users describe evaluating "
            "new music as 'work' and retreat to known playlists when suggestions feel samey or opaque."
        ),
        "rec_frustrations": (
            "Top frustrations: Discover Weekly staleness, overlap with Daily Mix, autoplay loops, "
            "podcast-heavy home feed, and no explanation for why a track was suggested."
        ),
        "listening_behaviors": (
            "Users want context-fit listening (commute, focus, gym), low-effort novelty, "
            "gradual expansion from anchors, and social trust paths — not random jumps."
        ),
        "repeat_causes": (
            "Comfort loops persist because familiar playlists minimize skip risk, save time, "
            "and algorithms reinforce existing clusters instead of bridging to novel artists."
        ),
        "segment_challenges": (
            "Comfort Loop Curators need gradual bridges; Algorithm Skeptics need explainability; "
            "Time-Poor Commuters need moment-aware sessions; Genre Explorers Burned need diversity controls."
        ),
        "unmet_needs": (
            "Explainable transitions, moment-aware discovery, controlled novelty distance, "
            "social trust signals, and discovery that meets users in existing routines."
        ),
    }
    key = next((k for k, v in CANONICAL_QUESTIONS.items() if v.lower() in question.lower() or question.lower() in v.lower()), "why_struggle")
    if question.startswith("q:"):
        key = question[2:]
    answer = answers.get(key, answers["why_struggle"])
    citations = [
        {"id": h[0].id, "text": h[0].text[:160], "url": h[0].url, "score": round(h[1], 3)}
        for h in hits[:5]
    ]
    return AskResponse(question=CANONICAL_QUESTIONS.get(key, question), answer=answer, citations=citations)


def ask(question: str, store: ReviewStore | None = None) -> AskResponse:
    store = store or ReviewStore()
    hits = store.search(question, k=8)
    settings = get_settings()

    if settings.mock_mode or not settings.anthropic_api_key:
        q = question
        for k, v in CANONICAL_QUESTIONS.items():
            if k in question or v.lower() in question.lower():
                q = f"q:{k}"
                break
        return _mock_answer(q, hits)

    import anthropic

    context = "\n".join(
        f"[{r.id}] ({r.source}) {r.text}" for r, _ in hits
    )
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = f"""You are a Spotify Growth PM analyst. Answer using ONLY the review evidence below.

Rules:
- Write 2-4 direct sentences answering the question. No preamble ("Based on the reviews…").
- No disclaimers, follow-up offers, or notes after the answer.
- Do not repeat the question. Do not add sections titled Note/Additionally/Summary.
- Cite review IDs inline in brackets only where needed (e.g. [r42]).

Question: {question}

Reviews:
{context}

Return JSON only: {{"answer": "...", "cited_ids": ["id1", "id2"]}}"""
    msg = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text
    try:
        data = json.loads(re.search(r"\{.*\}", raw, re.S).group())
        cited = data.get("cited_ids", [])
        citations = [
            {"id": h[0].id, "text": h[0].text[:160], "url": h[0].url}
            for h in hits
            if h[0].id in cited
        ] or [{"id": h[0].id, "text": h[0].text[:160], "url": h[0].url} for h in hits[:3]]
        return AskResponse(
            question=question,
            answer=_clean_answer(data.get("answer", "")),
            citations=citations,
        )
    except Exception:
        return _mock_answer(question, hits)
