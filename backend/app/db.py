from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  created_at INTEGER NOT NULL,
  filename TEXT NOT NULL,
  pdf_path TEXT NOT NULL,
  output_pdf_path TEXT,
  page_count INTEGER DEFAULT 0,
  detected_columns INTEGER DEFAULT 1,
  chunk_count INTEGER DEFAULT 0,
  translated_count INTEGER DEFAULT 0,
  current_chunk_id TEXT,
  state TEXT NOT NULL,
  paused INTEGER DEFAULT 0,
  error_message TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
  job_id TEXT NOT NULL,
  chunk_id TEXT NOT NULL,
  reading_order INTEGER NOT NULL,
  page_number INTEGER NOT NULL,
  block_type TEXT NOT NULL,
  x0 REAL NOT NULL,
  y0 REAL NOT NULL,
  x1 REAL NOT NULL,
  y1 REAL NOT NULL,
  source_text TEXT NOT NULL,
  heading_context TEXT NOT NULL,
  vi_text TEXT,
  notes_json TEXT,
  status TEXT NOT NULL,
  PRIMARY KEY (job_id, chunk_id)
);

CREATE INDEX IF NOT EXISTS idx_chunks_job_order ON chunks(job_id, reading_order);
"""


def _db_path() -> Path:
    # Vercel (serverless) chỉ ghi được vào /tmp. Local/dev có thể override bằng APP_DB_PATH.
    default = "/tmp/pdf_translate_app.sqlite" if os.environ.get("VERCEL") else "/workspace/backend/data/app.sqlite"
    p = os.environ.get("APP_DB_PATH", default)
    return Path(p)


def init_db() -> None:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_job(job_id: str) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()

