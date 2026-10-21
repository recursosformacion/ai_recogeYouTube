from pathlib import Path

from ai_recogeyoutube.db import initialize, upsert_candidate, upsert_work
from ai_recogeyoutube.models import WorkRecord, YouTubeCandidate
from ai_recogeyoutube.review_html import export_review_html


def test_export_review_html_contains_filterable_candidate_and_safe_link(tmp_path: Path) -> None:
    db_path = tmp_path / "pilot.db"
    output = tmp_path / "review.html"
    initialize(db_path)
    upsert_work(db_path, WorkRecord(work_id="w1", title="Ave verum & corpus"))
    upsert_candidate(
        db_path,
        YouTubeCandidate(
            video_id="video-1",
            url="https://www.youtube.com/watch?v=video-1",
            title='Soprano <practice>',
            channel_title="Choir channel",
            work_id="w1",
            voice_guess="soprano",
            material_type="individual_part",
        ),
    )

    count = export_review_html(db_path, output, "w1")
    html = output.read_text(encoding="utf-8")

    assert count == 1
    assert 'data-voice="soprano"' in html
    assert 'data-status="pending"' in html
    assert "Soprano &lt;practice&gt;" in html
    assert "Ave verum &amp; corpus" in html
    assert 'href="https://www.youtube.com/watch?v=video-1"' in html
    assert "aria-live" in html
    assert "No se conecta a OSAP" in html
