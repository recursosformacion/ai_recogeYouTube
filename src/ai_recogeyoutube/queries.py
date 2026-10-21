"""Conservative query generation for choral practice tracks."""

from .models import Voice, WorkRecord

VOICE_TERMS: dict[Voice, tuple[str, ...]] = {
    Voice.SOPRANO: ("soprano", "soprano practice", "soprano rehearsal", "sopran"),
    Voice.ALTO: ("alto", "alto practice", "alto rehearsal", "contralto"),
    Voice.TENOR: ("tenor", "tenor practice", "tenor rehearsal"),
    Voice.BASS: ("bass", "bass practice", "bass rehearsal", "bajo", "baix"),
    Voice.UNKNOWN: ("SATB", "choir rehearsal", "choral score"),
}

GENERAL_TERMS = (
    "practice track",
    "rehearsal track",
    "part recording",
    "vocal score",
    "pista de ensayo",
    "ensayo por voces",
    "Stimmprobe",
    "piste de répétition",
)


def build_queries(work: WorkRecord, voice: Voice) -> list[str]:
    """Return deduplicated queries; titles are never treated as proof."""
    titles = [work.title, *work.alternate_titles]
    composers = work.composers[:2]
    voice_terms = VOICE_TERMS[voice]
    queries: list[str] = []

    for title in titles:
        for term in voice_terms[:3]:
            queries.append(f'"{title}" {term}')
        for composer in composers:
            queries.append(f'"{title}" "{composer}" {voice.value}')
        if voice is Voice.UNKNOWN:
            queries.append(f'"{title}" SATB')
        for term in GENERAL_TERMS[:2]:
            queries.append(f'"{title}" {term}')

    # Stable de-duplication preserves query priority.
    return list(dict.fromkeys(q.strip() for q in queries if q.strip()))
