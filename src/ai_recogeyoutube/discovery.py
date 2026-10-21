"""Run generated queries and persist discovered video metadata."""

from pathlib import Path

from .db import upsert_candidate
from .models import Voice, WorkRecord
from .queries import build_queries
from .youtube import YouTubeClient


def discover_work(
    work: WorkRecord,
    voices: list[Voice],
    client: YouTubeClient,
    db_path: Path,
    max_results: int = 25,
) -> dict[str, int]:
    """Search one work. Duplicate video IDs update the existing local candidate."""
    stats = {"queries": 0, "results": 0, "unique_video_ids": 0}
    seen: set[str] = set()
    for voice in voices:
        for query in build_queries(work, voice):
            stats["queries"] += 1
            for candidate in client.search_videos(query, max_results=max_results):
                candidate.work_id = work.work_id
                candidate.voice_guess = voice
                candidate.evidence.append(f"query_voice:{voice.value}")
                upsert_candidate(db_path, candidate)
                stats["results"] += 1
                seen.add(candidate.video_id)
    stats["unique_video_ids"] = len(seen)
    return stats
