"""Small local web interface for searching and reviewing discovered YouTube videos."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from html import escape

from .community import record_promotion
from .db import connect, initialize


def search_candidates(
    db_path: Path, *, song: str = "", author: str = "", voice: str = "all",
    limit: int = 100,
) -> list[dict]:
    """Filter locally discovered candidates; blank text filters are ignored."""
    initialize(db_path)
    song, author, voice = song.strip().casefold(), author.strip().casefold(), voice.strip().casefold()
    allowed_voices = {"all", "soprano", "alto", "tenor", "bass"}
    if voice not in allowed_voices:
        raise ValueError("voice must be all, soprano, alto, tenor or bass")
    limit = max(1, min(int(limit), 200))
    with connect(db_path) as db:
        rows = db.execute(
            """SELECT c.video_id, c.work_id, c.title AS candidate_title, c.url,
                      c.payload_json, w.title AS work_title, w.payload_json AS work_payload
               FROM candidates c LEFT JOIN works w ON w.work_id=c.work_id
               ORDER BY c.title COLLATE NOCASE, c.video_id"""
        ).fetchall()
    results = []
    for row in rows:
        candidate = json.loads(row["payload_json"])
        work = json.loads(row["work_payload"]) if row["work_payload"] else {}
        title = str(work.get("title") or row["work_title"] or "")
        authors = work.get("composers") or candidate.get("composers") or []
        if isinstance(authors, str):
            authors = [authors]
        author_text = " ".join(str(a) for a in authors)
        candidate_voice = str(candidate.get("voice_guess") or "unknown").casefold()
        if song and song not in (title + " " + str(row["candidate_title"] or "")).casefold():
            continue
        if author and author not in author_text.casefold():
            continue
        if voice != "all" and candidate_voice not in {voice, "all"}:
            continue
        results.append({
            "work_id": row["work_id"] or "",
            "work_title": title or "Obra sin título",
            "author": author_text,
            "video_id": row["video_id"],
            "video_title": row["candidate_title"] or candidate.get("title") or "Vídeo sin título",
            "url": row["url"],
            "channel": candidate.get("channel_title") or "",
            "voice": candidate_voice,
            "material_type": str(candidate.get("material_type") or "unknown"),
        })
        if len(results) >= limit:
            break
    return results


def _page(title: str, content: str, script: str = "") -> bytes:
    return ("""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>""" + escape(title) + """ · ai_recogeYouTube</title>
<style>
:root{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#222b39;background:#f4f6f9}
*{box-sizing:border-box}body{margin:0}main{max-width:1050px;margin:auto;padding:28px 18px}
h1{font-size:clamp(1.6rem,4vw,2.3rem);margin:0 0 8px}p{color:#586273}
.panel,.result,.player{background:white;border:1px solid #dce2ea;border-radius:12px;padding:18px;margin:14px 0}
form{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;align-items:end}
label{display:flex;flex-direction:column;gap:5px;font-size:.92rem;font-weight:650}
input,select{font:inherit;padding:11px;border:1px solid #b9c3d1;border-radius:7px;min-width:0;width:100%;background:white}
button{font:inherit;font-weight:700;padding:11px 16px;border:0;border-radius:8px;cursor:pointer}
.primary{background:#2457a7;color:white}.accept{background:#167448;color:white}.reject{background:#b72f32;color:white}
.results{margin-top:18px}.result{display:flex;gap:14px;align-items:center;justify-content:space-between}
.result h2{font-size:1.05rem;margin:0 0 5px}.meta{font-size:.88rem;color:#626d7c}.result a{color:#2457a7}
.pill{display:inline-block;padding:3px 8px;background:#edf1f6;border-radius:5px;font-size:.8rem}
.actions{display:flex;gap:8px;flex-wrap:wrap}.notice{background:#e9f1fc;padding:12px;border-radius:8px}
iframe{width:100%;aspect-ratio:16/9;border:0;border-radius:9px}small{color:#626d7c}
@media(max-width:620px){.result{align-items:flex-start;flex-direction:column}.result .actions{width:100%}}
</style></head><body><main>""" + content + script + "</main></body></html>").encode("utf-8")


def serve_review_ui(db_path: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    """Run a loopback-only web UI; all decisions are stored in the local SQLite DB."""
    db_path = Path(db_path).resolve()
    initialize(db_path)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            print("[ai-youtube-web] " + (format % args))

        def send_html(self, body: bytes, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Security-Policy", "default-src 'self'; frame-src https://www.youtube-nocookie.com; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self';")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, payload: dict, status: int = 200) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            if parsed.path == "/api/search":
                try:
                    items = search_candidates(
                        db_path,
                        song=params.get("song", [""])[0],
                        author=params.get("author", [""])[0],
                        voice=params.get("voice", ["all"])[0],
                    )
                    self.send_json({"results": items, "count": len(items)})
                except (ValueError, OSError) as exc:
                    self.send_json({"error": str(exc)}, 400)
                return
            if parsed.path == "/review":
                work_id = params.get("work_id", [""])[0]
                video_id = params.get("video_id", [""])[0]
                voice = params.get("voice", ["unknown"])[0]
                title = params.get("title", ["Vídeo de YouTube"])[0]
                if not work_id or not video_id:
                    self.send_html(_page("Error", "<h1>Falta la obra o el vídeo</h1>"), 400)
                    return
                safe_id = escape(video_id, quote=True)
                content = (
                    "<h1>Revisar vídeo</h1><p>" + escape(title) + "</p>"
                    '<div class="player"><iframe src="https://www.youtube-nocookie.com/embed/' +
                    safe_id + '" title="Reproductor de YouTube" allow="accelerometer; autoplay; '
                    'clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
                    'referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div>'
                    '<p class="notice">Acepta si el vídeo corresponde a la obra y la voz seleccionadas. '
                    'Rechaza si no sirve. La decisión se registra en esta base local.</p>'
                    '<div class="actions"><button class="accept" id="accept">Aceptar</button>'
                    '<button class="reject" id="reject">Rechazar</button></div><p id="message" aria-live="polite"></p>'
                )
                script = """<script>
const data=__DATA__;
async function decide(decision){const msg=document.getElementById('message');
document.querySelectorAll('button').forEach(b=>b.disabled=true);
try{const r=await fetch('/api/decision',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...data,decision})});
const d=await r.json();if(!r.ok)throw new Error(d.error||'No se pudo guardar');
msg.textContent=decision==='approved'?'Aceptado y guardado.':'Rechazado y guardado.';
}catch(e){msg.textContent='Error al guardar: '+e.message;document.querySelectorAll('button').forEach(b=>b.disabled=false)}}
document.getElementById('accept').onclick=()=>decide('approved');
document.getElementById('reject').onclick=()=>decide('rejected');
</script>""".replace("__DATA__", json.dumps({
                    "work_id": work_id, "video_id": video_id, "voice": voice,
                    "url": "https://www.youtube.com/watch?v=" + video_id, "title": title,
                }, ensure_ascii=False).replace("</", "<\/"))
                self.send_html(_page("Revisar vídeo", content, script))
                return
            content = """<h1>Buscar vídeos para una obra musical</h1>
<p>Busca candidatos guardados en el catálogo local y revisa cada vídeo antes de aceptarlo.</p>
<div class="notice">Un campo vacío no aplica ese filtro. «Todas las voces» muestra candidatos de cualquier voz.</div>
<div class="panel"><form id="search">
<label>Canción / título<input name="song" placeholder="Título de la obra"></label>
<label>Autor / compositor<input name="author" placeholder="Nombre del compositor"></label>
<label>Voz<select name="voice"><option value="all">Todas las voces</option><option value="soprano">Soprano</option><option value="alto">Alto</option><option value="tenor">Tenor</option><option value="bass">Bajo</option></select></label>
<button class="primary" type="submit">Buscar</button></form></div>
<p id="summary" aria-live="polite">Introduce uno o varios filtros y pulsa Buscar.</p><div id="results" class="results"></div>"""
            script = """<script>
const form=document.getElementById('search'),results=document.getElementById('results'),summary=document.getElementById('summary');
form.addEventListener('submit',async e=>{e.preventDefault();results.replaceChildren();summary.textContent='Buscando…';
const p=new URLSearchParams(new FormData(form));try{const r=await fetch('/api/search?'+p);const d=await r.json();if(!r.ok)throw new Error(d.error||'Error de búsqueda');
summary.textContent=d.count+' candidatos encontrados'+(d.count===100?' (máximo mostrado: 100)':'');
if(!d.results.length){results.textContent='No hay candidatos que coincidan. Ejecuta primero el descubrimiento de vídeos para ampliar el catálogo local.';return}
for(const item of d.results){const card=document.createElement('article');card.className='result';
const info=document.createElement('div'),h=document.createElement('h2'),meta=document.createElement('div'),link=document.createElement('a'),badge=document.createElement('span');
h.textContent=item.work_title;link.href=item.url;link.target='_blank';link.rel='noopener noreferrer';link.textContent=item.video_title;
meta.className='meta';meta.append(link,document.createElement('br'));meta.lastChild.after(document.createTextNode((item.channel||'Canal desconocido')+' · voz: '+item.voice+' · '+item.material_type));
info.append(h,meta);const actions=document.createElement('div');actions.className='actions';const button=document.createElement('button');button.className='primary';button.textContent='Revisar vídeo';
const review=new URL('/review',location.origin);for(const [k,v] of Object.entries({work_id:item.work_id,video_id:item.video_id,voice:item.voice,title:item.video_title}))review.searchParams.set(k,v);
button.onclick=()=>window.open(review,'review_'+item.video_id,'width=1000,height=800,resizable=yes,scrollbars=yes');
actions.append(button);card.append(info,actions);results.append(card)}
}catch(e){summary.textContent='No se pudo buscar: '+e.message}});
</script>"""
            self.send_html(_page("Buscar vídeos", content, script))

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/api/decision":
                self.send_json({"error": "Ruta desconocida"}, 404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 20000:
                    raise ValueError("Solicitud vacía o demasiado grande")
                data = json.loads(self.rfile.read(length))
                decision = data.get("decision")
                if decision not in {"approved", "rejected"}:
                    raise ValueError("La decisión debe ser approved o rejected")
                work_id = str(data.get("work_id", "")).strip()
                video_id = str(data.get("video_id", "")).strip()
                voice = str(data.get("voice", "unknown")).strip()
                if not work_id or not video_id:
                    raise ValueError("Falta el identificador de obra o vídeo")
                with connect(db_path) as db:
                    candidate = db.execute(
                        """SELECT c.url,c.title,c.payload_json FROM candidates c
                           WHERE c.work_id=? AND c.video_id=? ORDER BY c.title LIMIT 1""",
                        (work_id, video_id),
                    ).fetchone()
                if candidate is None:
                    raise ValueError("El candidato ya no existe en el catálogo local")
                payload = json.loads(candidate["payload_json"])
                record_promotion(
                    db_path, user_id="local-reviewer", display_name="Revisor local",
                    work_id=work_id, video_id=video_id, url=candidate["url"],
                    title=candidate["title"], channel_title=payload.get("channel_title", ""),
                    voice=voice, material_type=payload.get("material_type", "unknown"),
                    decision=decision,
                )
                self.send_json({"saved": True, "decision": decision})
            except (ValueError, OSError, json.JSONDecodeError) as exc:
                self.send_json({"error": str(exc)}, 400)

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Interfaz de revisión disponible en http://{host}:{port}")
    print("Solo escucha en la máquina local; Ctrl+C para detener.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
