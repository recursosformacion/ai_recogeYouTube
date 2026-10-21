from ai_recogeyoutube.models import Voice, WorkRecord
from ai_recogeyoutube.queries import build_queries


def test_queries_include_work_and_voice_without_duplicates():
    work = WorkRecord(
        work_id="demo-1",
        title="Ave verum corpus",
        composers=["W. A. Mozart"],
        alternate_titles=["Ave Verum"],
    )
    queries = build_queries(work, Voice.SOPRANO)

    assert queries
    assert any("Ave verum corpus" in query for query in queries)
    assert any("soprano" in query for query in queries)
    assert len(queries) == len(set(queries))


def test_unknown_voice_uses_general_coral_terms():
    work = WorkRecord(work_id="demo-2", title="Test work")
    queries = build_queries(work, Voice.UNKNOWN)

    assert any("SATB" in query for query in queries)
    assert any("choir rehearsal" in query for query in queries)
