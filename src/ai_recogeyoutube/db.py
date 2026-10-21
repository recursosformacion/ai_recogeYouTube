"""Local pilot database. No connection to OSAP production databases."""

import json
import sqlite3
from pathlib import Path

from .models import YouTubeCandidate, WorkRecord


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(db_path: Path) -> None:
    with connect(db_path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS works (
                work_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS candidates (
                video_id TEXT PRIMARY KEY,
                work_id TEXT REFERENCES works(work_id),
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                query TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_candidates_work_id ON candidates(work_id);
            CREATE INDEX IF NOT EXISTS idx_candidates_review ON candidates(json_extract(payload_json, '$.review_status'));
            """
        )


def upsert_work(db_path: Path, work: WorkRecord) -> None:
    with connect(db_path) as db:
        db.execute(
            """INSERT INTO works(work_id, title, payload_json) VALUES (?, ?, ?)
            ON CONFLICT(work_id) DO UPDATE SET title=excluded.title,
            payload_json=excluded.payload_json""",
            (work.work_id, work.title, work.model_dump_json()),
        )


def upsert_candidate(db_path: Path, candidate: YouTubeCandidate) -> None:
    payload = candidate.model_dump(mode="json")
    with connect(db_path) as db:
        if candidate.work_id:
            work_exists = db.execute(
                "SELECT 1 FROM works WHERE work_id=?", (candidate.work_id,)
            ).fetchone()
            if not work_exists:
                raise ValueError(f"Unknown work_id: {candidate.work_id}")
        db.execute(
            """INSERT INTO candidates(video_id, work_id, title, url, query, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
              work_id=COALESCE(excluded.work_id, candidates.work_id),
              title=excluded.title, url=excluded.url, query=excluded.query,
              payload_json=excluded.payload_json""",
            (
                candidate.video_id,
                candidate.work_id,
                candidate.title,
                str(candidate.url),
                candidate.query,
                json.dumps(payload, ensure_ascii=False),
            ),
        )
