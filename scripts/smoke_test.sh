#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -q -r requirements.txt

export MOCK_MODE=true
export PYTHONPATH=.

python ingest/seed_corpus.py
python -c "
from analysis.store import ReviewStore
from analysis.classify import classify_batch
from ingest.normalize import load_corpus
from discovery.config import get_settings

s = get_settings()
records = classify_batch(load_corpus(s.corpus_path))
store = ReviewStore()
for r in records:
    store.upsert(r)
print(f'Indexed {store.count()} reviews')
"

curl -sf http://localhost:8000/health >/dev/null 2>&1 || {
  uvicorn api.main:app --host 127.0.0.1 --port 8000 &
  PID=$!
  sleep 2
  curl -sf http://localhost:8000/health | python -m json.tool
  curl -sf http://localhost:8000/api/insights | python -c "import sys,json; d=json.load(sys.stdin); print('themes', len(d['themes']), 'reviews', d['total_reviews'])"
  kill $PID 2>/dev/null || true
}

echo "Smoke test OK"
