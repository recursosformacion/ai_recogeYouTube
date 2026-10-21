"""Global YouTube search used by the local review website."""
import json
from pathlib import Path

from .community import initialize_community_schema
from .config import get_settings
from .db import connect, initialize, upsert_candidate
from .models import Voice
from .youtube import YouTubeClient


def search_global(db_path: Path, *, song: str = "", author: str = "", voice: str = "all", limit: int = 50) -> list[dict]:
    """Search YouTube live. 'all' means all SATB queries; 'song' adds no voice term."""
    song, author, voice = song.strip(), author.strip(), voice.strip().casefold()
    if not song and not author:
        raise ValueError("Escribe al menos el título de la obra o el compositor.")
    if voice not in {"all", "song", "soprano", "alto", "tenor", "bass"}:
        raise ValueError("Tipo de búsqueda no válido.")
    settings = get_settings()
    if not settings.youtube_api_key:
        raise ValueError("Falta YOUTUBE_API_KEY en .env.")
    initialize(db_path)
    limit = max(1, min(int(limit), 50))
    work = None
    if song:
        with connect(db_path) as db:
            rows = db.execute(
                "SELECT work_id,title,payload_json FROM works WHERE title LIKE ? COLLATE NOCASE LIMIT 100",
                (f"%{song}%",),
            ).fetchall()
        for row in rows:
            payload = json.loads(row["payload_json"])
            composers = payload.get("composers") or []
            if isinstance(composers, str):
                composers = [composers]
            if author and author.casefold() not in " ".join(map(str, composers)).casefold():
                continue
            work = {"work_id": row["work_id"], "title": row["title"], "composers": composers}
            break
    base = " ".join(x for x in ((f'"{song}"' if song else ""), (f'"{author}"' if author else "")) if x)
    if voice == "all":
        queries = [f"{base} {v}" for v in ("soprano", "alto", "tenor", "bass")] + [base]
    elif voice == "song":
        queries = [base]
    else:
        queries = [f"{base} {voice}", f"{base} {voice} choir"]
    client = YouTubeClient(settings.youtube_api_key)
    found = {}
    for query_index, query in enumerate(queries):
        if not query.strip():
            continue
        for candidate in client.search_videos(query, max_results=min(15, max(5, limit // len(queries) + 3))):
            if candidate.video_id in found:
                continue
            if work:
                candidate.work_id = work["work_id"]
                if voice in {"soprano", "alto", "tenor", "bass"}:
                    candidate.voice_guess = Voice(voice)
                elif voice == "all" and query_index < 4:
                    candidate.voice_guess = Voice(("soprano", "alto", "tenor", "bass")[query_index])
            upsert_candidate(db_path, candidate)
            found[candidate.video_id] = candidate
            if len(found) >= limit:
                break
        if len(found) >= limit:
            break
    initialize_community_schema(db_path)
    result = []
    with connect(db_path) as db:
        for c in found.values():
            approvals = rejections = author_votes = 0
            last_vote = "Sin votos"
            v = c.voice_guess.value
            if work:
                db.execute(
                    """INSERT INTO youtube_videos(video_id,url,title,channel_title,published_at,metadata_json)
                       VALUES (?,?,?,?,?,?) ON CONFLICT(video_id) DO UPDATE SET
                       title=excluded.title,url=excluded.url,channel_title=excluded.channel_title,
                       last_seen_at=CURRENT_TIMESTAMP""",
                    (c.video_id, str(c.url), c.title, c.channel_title,
                     c.published_at.isoformat() if c.published_at else None, c.model_dump_json()),
                )
                db.execute(
                    """INSERT INTO work_videos(work_id,video_id,voice,material_type)
                       VALUES (?,?,?,?) ON CONFLICT(work_id,video_id,voice) DO NOTHING""",
                    (work["work_id"], c.video_id, v, c.material_type.value),
                )
                score = db.execute(
                    """SELECT SUM(decision='approved') approvals,SUM(decision='rejected') rejections,
                       MAX(updated_at) last_vote FROM promotions
                       WHERE work_id=? AND video_id=? AND voice=?""",
                    (work["work_id"], c.video_id, v),
                ).fetchone()
                approvals, rejections = score["approvals"] or 0, score["rejections"] or 0
                last_vote = score["last_vote"] or "Sin votos"
                author_votes = db.execute(
                    """SELECT COUNT(*) n FROM promotions p JOIN youtube_videos y ON y.video_id=p.video_id
                       WHERE y.channel_title=? AND p.decision='approved'""",
                    (c.channel_title,),
                ).fetchone()["n"]
            result.append({
                "work_id": work["work_id"] if work else "",
                "work_title": work["title"] if work else song or "Búsqueda global",
                "video_id": c.video_id, "video_title": c.title or "Vídeo sin título",
                "url": str(c.url), "channel": c.channel_title or "Canal desconocido",
                "voice": v, "material_type": c.material_type.value,
                "approval_count": approvals, "rejection_count": rejections,
                "author_votes": author_votes, "last_vote": last_vote,
            })
    result.sort(key=lambda x: (-x["approval_count"], -x["author_votes"], x["rejection_count"], x["video_title"].casefold()))
    return result
