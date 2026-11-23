"""Small shared SQLite store for demonstration purposes."""
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv('DB_PATH', 'data/jobs.db'))


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA busy_timeout=15000')
    db.execute('PRAGMA journal_mode=WAL')
    return db


def init_db():
    with connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            task TEXT NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            result TEXT,
            error TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        )''')


def create_job(job_id, task):
    with connect() as db:
        db.execute('INSERT INTO jobs (id, task, status) VALUES (?, ?, ?)',
                   (job_id, task, 'queued'))


def get_job(job_id):
    with connect() as db:
        row = db.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
        return dict(row) if row else None


def set_status(job_id, status, *, result=None, error=None, increment_attempt=False):
    with connect() as db:
        db.execute('''UPDATE jobs SET status = ?, result = ?, error = ?,
            attempts = attempts + ?,
            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = ?''',
            (status, result, error, int(increment_attempt), job_id))
