# Event-Driven Job Processor

Python/FastAPI producer + RabbitMQ durable queue + manual-ACK Python worker + SQLite status store + HTML polling dashboard.

## Windows PowerShell quick start

```powershell
docker compose up -d
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Open two PowerShell terminals **in this project folder**, activate the virtual environment in both (`.\.venv\Scripts\Activate.ps1`), and run:

- Terminal A: `python -m uvicorn app:app --reload`
- Terminal B: `python worker.py`

Visit http://127.0.0.1:8000 for the dashboard, http://127.0.0.1:8000/docs for API docs, and http://localhost:15672 for RabbitMQ (guest / guest; local demo only).

Test `retry: demo` for two NACKs followed by success; `fail: demo` for terminal failure after three attempts.

## API requests (PowerShell)

```powershell
$job = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/jobs -ContentType 'application/json' -Body '{"task":"Generate report"}'
$job
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/jobs/$($job.job_id)"
```

## Architecture notes

- API returns 202 only after publisher confirmation from RabbitMQ (not after job completion).
- Durable queue + persistent message + a Docker named volume persist queued jobs through normal broker restarts.
- Worker uses `basic_ack` only after recording completed or terminal failed, and `basic_nack(requeue=True)` for retryable failures.
- `prefetch_count=1` keeps a worker processing at most one unacknowledged message at a time.
- SQLite is a **local demo** store; the API and worker must share the same project directory and DB path.
- This is an at-least-once design, not exactly-once. Crash windows and lost publisher confirms can create duplicates or status discrepancies. A production version should use an outbox/inbox pattern, idempotent side effects, PostgreSQL, controlled retry delays and a dead-letter queue. The demo deliberately requeues immediately for easy observation.
- Do not expose `guest` credentials or RabbitMQ management interface publicly.

To stop the broker without deleting queued messages: `docker compose down`. Do not use `docker compose down -v` unless you want to delete broker data.
