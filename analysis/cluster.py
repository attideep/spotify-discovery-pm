from __future__ import annotations

from collections import Counter

from discovery.models import ThemeInsight
from analysis.store import ReviewStore


THEME_SUMMARIES = {
    "discovery_fatigue": "Users find discovery cognitively expensive — browsing and evaluating new music feels like work with low payoff.",
    "recommendation_irrelevance": "Recommendations overlap with existing taste clusters; Discover Weekly and Daily Mix feel samey.",
    "comfort_loop": "Repeat playlist listening is rational — familiar content reduces decision fatigue and skip risk.",
    "algorithm_anxiety": "Users distrust opaque algorithms after bad experiences; they manually curate or skip 'recommended' labels.",
    "social_discovery": "Friend shares and social signals outperform algorithmic feeds for trusted novelty.",
    "podcast_drift": "Podcast promotion crowds out music discovery surfaces in the home feed.",
    "ui_friction": "Discovery features are hard to find or buried under non-music content.",
    "positive_discovery": "When discovery works, users describe it as magical — but it's rare enough to not change default behavior.",
}


def compute_insights(store: ReviewStore) -> list[ThemeInsight]:
    records = store.load_all()
    total = max(len(records), 1)
    theme_counter: Counter = Counter()
    theme_examples: dict[str, list] = {t: [] for t in THEME_SUMMARIES}

    for r in records:
        for t in r.themes:
            theme_counter[t] += 1
            if len(theme_examples[t]) < 5:
                theme_examples[t].append(
                    {"id": r.id, "text": r.text[:200], "url": r.url, "source": r.source}
                )

    insights = []
    for theme, count in theme_counter.most_common():
        insights.append(
            ThemeInsight(
                theme=theme,
                count=count,
                pct=round(100 * count / total, 1),
                summary=THEME_SUMMARIES.get(theme, theme),
                exemplars=theme_examples.get(theme, []),
            )
        )
    return insights
