import json

import pytest

from ai_recogeyoutube.db import initialize, upsert_candidate, upsert_work, connect
from ai_recogeyoutube.models import WorkRecord, YouTubeCandidate


def test_work_and_candidate_are_persisted_idempotently(tmp_path):
    path = tmp_path / "test.sqlite3"
    initialize(path)
    work = WorkRecord(work_id="w1", title="Ave verum corpus")
    upsert_work(path, work)
    candidate = YouTubeCandidate(
        video_id="abc123",
        url="https://www.youtube.com/watch?v=abc123",
        title="Ave verum corpus - soprano practice",
        work_id="w1",
        query='"Ave verum corpus" soprano practice',
        evidence=["voice term in title"],
        confidence=0.4,
    )
    upsert_candidate(path, candidate)
    upsert_candidate(path, candidate)

    with connect(path) as db:
        rows = db.execute("SELECT * FROM candidates").fetchall()
    assert len(rows) == 1
    payload = json.loads(rows[0]["payload_json"])
    assert payload["work_id"] == "w1"


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
