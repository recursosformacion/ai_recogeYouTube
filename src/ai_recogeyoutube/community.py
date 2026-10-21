"""Local community review ledger for YouTube candidates.

This pilot stores no credentials and does not connect to OSAP. User IDs are local
pseudonymous identifiers; a future OSAP adapter must derive identity from its
authenticated session rather than trusting a client-supplied user ID.
"""
import json
from pathlib import Path

from .db import connect, initialize


def initialize_community_schema(db_path: Path) -> None:
    """Create normalized video, work-link, user and promotion tables."""
    initialize(db_path)
    with connect(db_path) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS youtube_videos (
            video_id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            channel_title TEXT NOT NULL DEFAULT '',
            published_at TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS work_videos (
            work_id TEXT NOT NULL REFERENCES works(work_id) ON DELETE CASCADE,
            video_id TEXT NOT NULL REFERENCES youtube_videos(video_id) ON DELETE CASCADE,
            voice TEXT NOT NULL CHECK (voice IN ('soprano','alto','tenor','bass','all','unknown')),
            material_type TEXT NOT NULL DEFAULT 'unknown',
            review_status TEXT NOT NULL DEFAULT 'pending'
                CHECK (review_status IN ('pending','confirmed','rejected')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (work_id, video_id, voice)
        );
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS promotions (
            user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            work_id TEXT NOT NULL,
            video_id TEXT NOT NULL,
            voice TEXT NOT NULL,
            decision TEXT NOT NULL CHECK (decision IN ('approved','rejected')),
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, work_id, video_id, voice),
            FOREIGN KEY (work_id, video_id, voice)
                REFERENCES work_videos(work_id, video_id, voice) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_work_videos_rank
            ON work_videos(work_id, voice, review_status);
        CREATE INDEX IF NOT EXISTS idx_promotions_link
            ON promotions(work_id, video_id, voice, decision);
        DROP VIEW IF EXISTS work_video_scores;
        CREATE VIEW work_video_scores AS
            SELECT wv.work_id, wv.video_id, wv.voice, wv.material_type,
                   wv.review_status, yv.url, yv.title, yv.channel_title,
                   SUM(CASE WHEN p.decision = 'approved' THEN 1 ELSE 0 END)
                       AS approval_count,
                   SUM(CASE WHEN p.decision = 'rejected' THEN 1 ELSE 0 END)
                       AS rejection_count
            FROM work_videos wv
            JOIN youtube_videos yv ON yv.video_id = wv.video_id
            LEFT JOIN promotions p
              ON p.work_id = wv.work_id AND p.video_id = wv.video_id
             AND p.voice = wv.voice
            GROUP BY wv.work_id, wv.video_id, wv.voice;
        """)


def record_promotion(
    db_path: Path, *, user_id: str, display_name: str, work_id: str,
    video_id: str, url: str, title: str, channel_title: str = "",
    voice: str = "unknown", material_type: str = "unknown",
    decision: str = "approved", note: str = "",
) -> None:
    """Record or update one user's decision for a work/video/voice tuple.

    Repeated submissions by the same user update their existing decision instead
    of inflating the approval count. The work must already exist in the local
    imported catalogue.
    """
    if decision not in {"approved", "rejected"}:
        raise ValueError("decision must be 'approved' or 'rejected'")
    if voice not in {"soprano", "alto", "tenor", "bass", "all", "unknown"}:
        raise ValueError("unsupported voice")
    if not video_id.strip() or not user_id.strip() or not work_id.strip():
        raise ValueError("user_id, work_id and video_id must not be empty")
    initialize_community_schema(db_path)
    with connect(db_path) as db:
        if not db.execute("SELECT 1 FROM works WHERE work_id=?", (work_id,)).fetchone():
            raise ValueError(f"Unknown work_id: {work_id}")
        db.execute(
            """INSERT INTO users(user_id, display_name) VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET display_name=excluded.display_name""",
            (user_id, display_name),
        )
        db.execute(
            """INSERT INTO youtube_videos(video_id,url,title,channel_title)
               VALUES (?,?,?,?)
               ON CONFLICT(video_id) DO UPDATE SET
                 url=excluded.url, title=excluded.title,
                 channel_title=excluded.channel_title,
                 last_seen_at=CURRENT_TIMESTAMP""",
            (video_id, url, title, channel_title),
        )
        db.execute(
            """INSERT INTO work_videos(work_id,video_id,voice,material_type)
               VALUES (?,?,?,?)
               ON CONFLICT(work_id,video_id,voice) DO UPDATE SET
                 material_type=excluded.material_type,
                 updated_at=CURRENT_TIMESTAMP""",
            (work_id, video_id, voice, material_type),
        )
        db.execute(
            """INSERT INTO promotions(user_id,work_id,video_id,voice,decision,note)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(user_id,work_id,video_id,voice) DO UPDATE SET
                 decision=excluded.decision, note=excluded.note,
                 updated_at=CURRENT_TIMESTAMP""",
            (user_id, work_id, video_id, voice, decision, note),
        )



def sync_discovered_candidates(db_path: Path, work_id: str | None = None) -> int:
    """Copy locally discovered candidates into the normalized community tables.

    This keeps discovery and community review separate: imported candidates stay
    pending until a user or moderator makes a decision.
    """
    initialize_community_schema(db_path)
    with connect(db_path) as db:
        sql = """SELECT video_id, work_id, title, url, payload_json
                 FROM candidates WHERE work_id IS NOT NULL"""
        params: tuple = ()
        if work_id:
            sql += " AND work_id=?"
            params = (work_id,)
        rows = db.execute(sql, params).fetchall()
        count = 0
        for row in rows:
            payload = json.loads(row["payload_json"])
            video_id = row["video_id"]
            db.execute(
                """INSERT INTO youtube_videos(video_id,url,title,channel_title,metadata_json)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(video_id) DO UPDATE SET
                     url=excluded.url, title=excluded.title,
                     channel_title=excluded.channel_title,
                     metadata_json=excluded.metadata_json,
                     last_seen_at=CURRENT_TIMESTAMP""",
                (video_id, row["url"], row["title"],
                 payload.get("channel_title", ""),
                 json.dumps(payload, ensure_ascii=False)),
            )
            voice = payload.get("voice_guess", "unknown")
            if voice not in {"soprano", "alto", "tenor", "bass", "all", "unknown"}:
                voice = "unknown"
            material_type = payload.get("material_type", "unknown")
            db.execute(
                """INSERT INTO work_videos(work_id,video_id,voice,material_type)
                   VALUES (?,?,?,?)
                   ON CONFLICT(work_id,video_id,voice) DO UPDATE SET
                     material_type=excluded.material_type,
                     updated_at=CURRENT_TIMESTAMP""",
                (row["work_id"], video_id, voice, material_type),
            )
            count += 1
        return count


def ranked_videos(db_path: Path, work_id: str, voice: str) -> list[dict]:
    """Return candidates for a work/voice, with community approvals first."""
    initialize_community_schema(db_path)
    with connect(db_path) as db:
        rows = db.execute(
            """SELECT * FROM work_video_scores
               WHERE work_id=? AND voice IN (?, 'all')
               ORDER BY CASE review_status WHEN 'confirmed' THEN 0 ELSE 1 END,
                        approval_count DESC, rejection_count ASC, title COLLATE NOCASE""",
            (work_id, voice),
        ).fetchall()
        return [dict(row) for row in rows]
