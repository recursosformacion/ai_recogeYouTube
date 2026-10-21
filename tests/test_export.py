import csv

from ai_recogeyoutube.db import initialize, upsert_candidate, upsert_work
from ai_recogeyoutube.export import export_candidates
from ai_recogeyoutube.models import YouTubeCandidate, WorkRecord


def test_export_candidates_to_reviewable_csv(tmp_path):
    db_path = tmp_path / "pilot.sqlite3"
    csv_path = tmp_path / "out" / "candidates.csv"
    initialize(db_path)
    upsert_work(db_path, WorkRecord(work_id="w1", title="Ave verum corpus"))
    upsert_candidate(db_path, YouTubeCandidate(
        video_id="abc123",
        url="https://www.youtube.com/watch?v=abc123",
        title="Soprano practice",
        channel_title="Example Choir",
        work_id="w1",
        voice_guess="soprano",
        evidence=["query_voice:soprano"],
    ))

    assert export_candidates(db_path, csv_path, "w1") == 1
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["video_id"] == "abc123"
    assert rows[0]["review_status"] == "pending"
    assert rows[0]["voice_guess"] == "soprano"


def test_export_can_filter_by_work(tmp_path):
    db_path = tmp_path / "pilot.sqlite3"
    initialize(db_path)
    upsert_work(db_path, WorkRecord(work_id="w1", title="Work one"))
    upsert_work(db_path, WorkRecord(work_id="w2", title="Work two"))
    for video_id, work_id in [("one", "w1"), ("two", "w2")]:
        upsert_candidate(db_path, YouTubeCandidate(
            video_id=video_id,
            url=f"https://www.youtube.com/watch?v={video_id}",
            title=video_id,
            work_id=work_id,
        ))
    assert export_candidates(db_path, tmp_path / "one.csv", "w1") == 1
    assert export_candidates(db_path, tmp_path / "all.csv") == 2
