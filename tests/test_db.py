import json
import sqlite3

import pytest

from ai_recogeyoutube.db import initialize, upsert_candidate, upsert_work, connect
from ai_recogeyoutube.models import WorkRecord, YouTubeCandidate


def make_candidate(video_id: str, work_id: str, title: str | None = None) -> YouTubeCandidate:
    return YouTubeCandidate(
        video_id=video_id,
        url=f"https://www.youtube.com/watch?v={video_id}",
        title=title or f"Video for {work_id}",
        work_id=work_id,
        query=f"query {work_id}",
    )


def test_work_and_candidate_are_persisted_idempotently(tmp_path):
    path = tmp_path / "test.sqlite3"
    initialize(path)
    work = WorkRecord(work_id="w1", title="Ave verum corpus")
    upsert_work(path, work)
    candidate = make_candidate("abc123", "w1", "Ave verum corpus - soprano practice")
    upsert_candidate(path, candidate)
    upsert_candidate(path, candidate)

    with connect(path) as db:
        rows = db.execute("SELECT * FROM candidates").fetchall()
    assert len(rows) == 1
    payload = json.loads(rows[0]["payload_json"])
    assert payload["work_id"] == "w1"


def test_same_video_can_be_associated_with_multiple_works(tmp_path):
    path = tmp_path / "test.sqlite3"
    initialize(path)
    upsert_work(path, WorkRecord(work_id="w1", title="Work one"))
    upsert_work(path, WorkRecord(work_id="w2", title="Work two"))

    upsert_candidate(path, make_candidate("shared123", "w1", "First title"))
    upsert_candidate(path, make_candidate("shared123", "w2", "Second title"))
    # Re-discovery for the first work updates that association, not the other one.
    upsert_candidate(path, make_candidate("shared123", "w1", "Updated first title"))

    with connect(path) as db:
        rows = db.execute(
            "SELECT video_id, work_id, title FROM candidates ORDER BY work_id"
        ).fetchall()
    assert [(row["video_id"], row["work_id"], row["title"]) for row in rows] == [
        ("shared123", "w1", "Updated first title"),
        ("shared123", "w2", "Second title"),
    ]


def test_initialize_migrates_legacy_video_primary_key_without_losing_rows(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE works (
                work_id TEXT PRIMARY KEY, title TEXT NOT NULL, payload_json TEXT NOT NULL
            );
            CREATE TABLE candidates (
                video_id TEXT PRIMARY KEY,
                work_id TEXT REFERENCES works(work_id),
                title TEXT NOT NULL, url TEXT NOT NULL,
                query TEXT NOT NULL DEFAULT '', payload_json TEXT NOT NULL
            );
            INSERT INTO works VALUES ('w1', 'Work one', '{}');
            INSERT INTO candidates VALUES (
                'legacy123', 'w1', 'Legacy video',
                'https://www.youtube.com/watch?v=legacy123', 'legacy query', '{"work_id":"w1"}'
            );
        """)

    initialize(path)
    initialize(path)  # Migration and initialization are repeatable.
    with connect(path) as db:
        rows = db.execute("SELECT * FROM candidates").fetchall()
        columns = {row["name"] for row in db.execute("PRAGMA table_info(candidates)")}
    assert "candidate_key" in columns
    assert len(rows) == 1
    assert rows[0]["video_id"] == "legacy123"
    assert rows[0]["work_id"] == "w1"
    assert json.loads(rows[0]["payload_json"])["work_id"] == "w1"


def test_candidate_rejects_unknown_work_id(tmp_path):
    path = tmp_path / "test.sqlite3"
    initialize(path)
    candidate = YouTubeCandidate(
        video_id="abc123",
        url="https://www.youtube.com/watch?v=abc123",
        title="Orphan candidate",
        work_id="missing",
    )
    with pytest.raises(ValueError, match="Unknown work_id"):
        upsert_candidate(path, candidate)
