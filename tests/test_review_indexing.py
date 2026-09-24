import importlib
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from analysis.store import ReviewStore
from discovery.config import get_settings
from ingest.normalize import normalize, save_corpus


class ReviewIndexingTests(unittest.TestCase):
    def setUp(self) -> None:
        get_settings.cache_clear()

    def tearDown(self) -> None:
        get_settings.cache_clear()

    def test_serverless_embedding_uses_local_hash_even_when_gemini_configured(self):
        with patch.dict(os.environ, {"VERCEL": "1", "GEMINI_API_KEY": "AIza" + "x" * 40}, clear=False):
            get_settings.cache_clear()
            google_module = types.ModuleType("google")
            genai_module = types.ModuleType("google.generativeai")
            genai_module.configure = lambda api_key: None
            genai_module.embed_content = lambda **kwargs: {"embedding": [1.0]}
            google_module.generativeai = genai_module

            with tempfile.TemporaryDirectory() as tmp, patch.dict(
                sys.modules,
                {"google": google_module, "google.generativeai": genai_module},
            ):
                store = ReviewStore(str(Path(tmp) / "reviews.db"))

                self.assertEqual(len(store.embed("hello")), 384)

    def test_ensure_indexed_repairs_partial_review_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus_path = Path(tmp) / "corpus.json"
            records = [
                normalize("seed", "test", "Discovery feels repetitive", rating=2, idx=0),
                normalize("seed", "test", "Friends help me find fresh music", rating=4, idx=1),
            ]
            save_corpus(records, corpus_path)

            env = {
                "DATA_DIR": tmp,
                "CORPUS_PATH": str(corpus_path),
                "MOCK_MODE": "true",
            }
            with patch.dict(os.environ, env, clear=False):
                get_settings.cache_clear()
                store = ReviewStore()
                store.upsert(records[0])
                self.assertEqual(store.count(), 1)

                main = importlib.import_module("api.main")
                main._ensure_indexed()

                repaired = ReviewStore()
                self.assertEqual(repaired.count(), 2)


if __name__ == "__main__":
    unittest.main()
