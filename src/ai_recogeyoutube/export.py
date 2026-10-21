"""Export locally discovered candidates to a reviewable CSV file."""

import csv
import json
from pathlib import Path

from .db import connect


def export_candidates(db_path: Path, output_path: Path, work_id: str | None = None) -> int:
    """Write candidate metadata and review fields; never modifies OSAP."""
    if not db_path.exists():
        raise FileNotFoundError(f"Local database does not exist: {db_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sql = "SELECT payload_json FROM candidates"
    params: tuple[str, ...] = ()
    if work_id:
        sql += " WHERE work_id = ?"
        params = (work_id,)
    sql += " ORDER BY title COLLATE NOCASE, video_id"

    with connect(db_path) as db, output_path.open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        rows = db.execute(sql, params).fetchall()
        fields = [
            "work_id", "video_id", "url", "title", "channel_title",
            "published_at", "duration_seconds", "voice_guess", "material_type",
            "review_status", "confidence", "query", "evidence", "description",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            item = json.loads(row["payload_json"])
            writer.writerow({
                "work_id": item.get("work_id") or "",
                "video_id": item.get("video_id", ""),
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "channel_title": item.get("channel_title", ""),
                "published_at": item.get("published_at") or "",
                "duration_seconds": item.get("duration_seconds") or "",
                "voice_guess": item.get("voice_guess", "unknown"),
                "material_type": item.get("material_type", "unknown"),
                "review_status": item.get("review_status", "pending"),
                "confidence": item.get("confidence", 0.0),
                "query": item.get("query", ""),
                "evidence": " | ".join(item.get("evidence") or []),
                "description": item.get("description", ""),
            })
    return len(rows)
