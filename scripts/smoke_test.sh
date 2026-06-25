#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -q -r requirements.txt

export MOCK_MODE=false
export ALLOW_DEMO_MODE=true
export PYTHONPATH=.

python scripts/verify_demo_tracks.py

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

# Bridge demo (no Spotify keys)
python -c "
from mvp.bridge import create_bridge_session
from mvp.oembed import lookup_track_oembed
assert lookup_track_oembed('35KiiILklye1JRRctaLUb4')['name'] == 'Holocene'
s = create_bridge_session('Like Khruangbin but more energetic', force_demo=True)
assert len(s.tracks) == 8
s2 = create_bridge_session('warm indie', anchor_track_id='35KiiILklye1JRRctaLUb4', force_demo=True)
assert 'Holocene' in s2.anchor_track
print('Bridge demo OK:', s.tracks[0].name)
"

uvicorn api.main:app --host 127.0.0.1 --port 8765 &
PID=$!
sleep 2
curl -sf http://127.0.0.1:8765/health | python3 -m json.tool
curl -sf -X POST http://127.0.0.1:8765/api/bridge \
  -H 'Content-Type: application/json' \
  -d '{"intent":"indie folk focus","demo":true}' | python3 -c "
import sys,json
d=json.load(sys.stdin)
assert d['mode']=='demo'
assert len(d['tracks'])==8
print('API bridge OK', d['tracks'][0]['spotify_url'])
"
kill $PID 2>/dev/null || true
echo "Smoke test OK"
