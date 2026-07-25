from pathlib import Path
import unittest


APP_JS = Path(__file__).resolve().parents[1] / "web" / "app.js"


class WebStaticEscapingTests(unittest.TestCase):
    def test_search_results_escape_untrusted_track_fields(self):
        source = APP_JS.read_text()

        self.assertIn('data-url="${escapeHtml(t.spotify_url || "")}"', source)
        self.assertIn('data-id="${escapeHtml(t.id || "")}"', source)
        self.assertIn('src="${escapeHtml(t.album_art)}"', source)
        self.assertIn('<div class="search-result__title">${escapeHtml(t.name || "")}</div>', source)
        self.assertIn('<div class="search-result__artist">${escapeHtml(t.artist || "Spotify")}</div>', source)
        self.assertIn('<div class="search-results__hint">${escapeHtml(hint)}</div>', source)

    def test_insight_rendering_escapes_corpus_strings(self):
        source = APP_JS.read_text()

        self.assertIn('"${escapeHtml(ex.text || "")}"', source)
        self.assertIn('<p class="theme-detail__summary">${escapeHtml(theme.summary || "")}</p>', source)
        self.assertIn('<p class="theme-card__summary">${escapeHtml(t.summary || "")}</p>', source)
        self.assertIn('<p class="media-card__desc">${escapeHtml((t.summary || "").slice(0, 56))}', source)
        self.assertIn('<button class="chip" data-key="${escapeHtml(k)}">', source)


if __name__ == "__main__":
    unittest.main()
