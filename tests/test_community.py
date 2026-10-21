from pathlib import Path

import pytest

from ai_recogeyoutube.community import (
    initialize_community_schema,
    ranked_videos,
    record_promotion,
    sync_discovered_candidates,
)
from ai_recogeyoutube.db import initialize, upsert_candidate, upsert_work
from ai_recogeyoutube.models import WorkRecord, YouTubeCandidate


def setup_work(db_path: Path) -> None:
    initialize(db_path)
    upsert_work(db_path, WorkRecord(work_id="w1", title="Ave verum corpus"))
    initialize_community_schema(db_path)


def promote(db_path: Path, user: str, *, decision: str = "approved", voice: str = "soprano") -> None:
    record_promotion(
        db_path, user_id=user, display_name=user, work_id="w1",
        video_id="video-1", url="https://www.youtube.com/watch?v=video-1",
        title="Soprano rehearsal", channel_title="Choir channel",
        voice=voice, material_type="individual_part", decision=decision,
    )


def test_approvals_count_once_per_user_and_can_change_decision(tmp_path: Path) -> None:
    db_path = tmp_path / "pilot.db"
    setup_work(db_path)
    promote(db_path, "u1")
    promote(db_path, "u1")
    results = ranked_videos(db_path, "w1", "soprano")
    assert results[0]["approval_count"] == 1

    promote(db_path, "u2")
    results = ranked_videos(db_path, "w1", "soprano")
    assert results[0]["approval_count"] == 2

    promote(db_path, "u1", decision="rejected")
    results = ranked_videos(db_path, "w1", "soprano")
    assert results[0]["approval_count"] == 1
    assert results[0]["rejection_count"] == 1


def test_same_video_can_link_to_different_works_and_voices(tmp_path: Path) -> None:
    db_path = tmp_path / "pilot.db"
    setup_work(db_path)
    upsert_work(db_path, WorkRecord(work_id="w2", title="Another work"))
    promote(db_path, "u1", voice="soprano")
    record_promotion(
        db_path, user_id="u1", display_name="u1", work_id="w2",
        video_id="video-1", url="https://www.youtube.com/watch?v=video-1",
        title="Same video", voice="alto", decision="approved",
    )
    assert len(ranked_videos(db_path, "w1", "soprano")) == 1
    assert len(ranked_videos(db_path, "w2", "alto")) == 1


def test_unknown_work_is_rejected(tmp_path: Path) -> None:
    db_path = tmp_path / "pilot.db"
    initialize_community_schema(db_path)
    with pytest.raises(ValueError, match="Unknown work_id"):
        record_promotion(
            db_path, user_id="u1", display_name="u1", work_id="missing",
            video_id="v1", url="https://www.youtube.com/watch?v=v1", title="Video",
        )



def test_discovered_candidates_can_be_synced_into_review_model(tmp_path: Path) -> None:
    db_path = tmp_path / "pilot.db"
    setup_work(db_path)
    upsert_candidate(
        db_path,
        YouTubeCandidate(
            video_id="found-video",
            url="https://www.youtube.com/watch?v=found-video",
            title="Ave verum corpus soprano rehearsal",
            channel_title="Choir channel",
            work_id="w1",
            voice_guess="soprano",
            material_type="individual_part",
        ),
    )
    assert sync_discovered_candidates(db_path, "w1") == 1
    rows = ranked_videos(db_path, "w1", "soprano")
    assert len(rows) == 1
    assert rows[0]["approval_count"] == 0
    assert rows[0]["review_status"] == "pending"
    assert rows[0]["title"] == "Ave verum corpus soprano rehearsal"



def test_sync_keeps_same_video_linked_to_multiple_works(tmp_path: Path) -> None:
    db_path = tmp_path / "pilot.db"
    setup_work(db_path)
    upsert_work(db_path, WorkRecord(work_id="w2", title="Another work"))
    upsert_candidate(
        db_path,
        YouTubeCandidate(
            video_id="shared-video",
            url="https://www.youtube.com/watch?v=shared-video",
            title="Shared recording",
            work_id="w1",
            voice_guess="soprano",
        ),
    )
    upsert_candidate(
        db_path,
        YouTubeCandidate(
            video_id="shared-video",
            url="https://www.youtube.com/watch?v=shared-video",
            title="Shared recording",
            work_id="w2",
            voice_guess="alto",
        ),
    )

    assert sync_discovered_candidates(db_path) == 2
    assert len(ranked_videos(db_path, "w1", "soprano")) == 1
    assert len(ranked_videos(db_path, "w2", "alto")) == 1
