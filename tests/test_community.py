from pathlib import Path

import pytest

from ai_recogeyoutube.community import (
    initialize_community_schema,
    ranked_videos,
    record_promotion,
)
from ai_recogeyoutube.db import upsert_work
from ai_recogeyoutube.models import WorkRecord


def setup_work(db_path: Path) -> None:
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
