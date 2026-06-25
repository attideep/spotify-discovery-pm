# Review Discovery Workflow (Cursor Automation — optional)

Scheduled automation to refresh Reddit/HN signals and post theme summary.

## Trigger
- Webhook (manual) or weekly cron

## Actions
1. Run ingest scrapers on latest Reddit RSS
2. Re-classify and update vector index
3. Post top 5 themes to Slack/email

## Manual test (no automation required)
```bash
curl -X POST http://localhost:8000/api/ingest
curl http://localhost:8000/api/insights
```

Primary workflow demo: **Review Discovery Engine UI** at `/`
