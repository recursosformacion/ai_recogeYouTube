"""Generate a self-contained HTML page for human review of local candidates."""

from html import escape
from pathlib import Path

from .community import initialize_community_schema, sync_discovered_candidates
from .db import connect


def export_review_html(
    db_path: Path, output_path: Path, work_id: str | None = None,
) -> int:
    """Export a standalone, filterable HTML review board from the local pilot DB."""
    if not db_path.exists():
        raise FileNotFoundError(f"Local database does not exist: {db_path}")
    initialize_community_schema(db_path)
    sync_discovered_candidates(db_path, work_id)

    sql = """SELECT s.work_id, w.title AS work_title, s.video_id, s.url, s.title,
                    s.channel_title, s.voice, s.material_type, s.review_status,
                    s.approval_count, s.rejection_count
             FROM work_video_scores s
             JOIN works w ON w.work_id = s.work_id"""
    params: tuple[str, ...] = ()
    if work_id:
        sql += " WHERE s.work_id=?"
        params = (work_id,)
    sql += """ ORDER BY CASE s.review_status
                  WHEN 'confirmed' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END,
                s.approval_count DESC, s.rejection_count ASC, w.title COLLATE NOCASE"""
    with connect(db_path) as db:
        rows = [dict(row) for row in db.execute(sql, params).fetchall()]

    body_rows = []
    for row in rows:
        fields = [
            row["work_title"], row["work_id"], row["title"], row["channel_title"],
            row["voice"], row["review_status"], row["material_type"],
        ]
        searchable = escape(" ".join(str(value or "") for value in fields).lower(), quote=True)
        body_rows.append(
            '<tr data-search="' + searchable + '"'
            ' data-status="' + escape(row["review_status"], quote=True) + '"'
            ' data-voice="' + escape(row["voice"], quote=True) + '">'
            '<td>' + escape(row["work_title"] or "") + '<small>' +
            escape(row["work_id"] or "") + '</small></td>'
            '<td><a target="_blank" rel="noopener noreferrer" href="' +
            escape(row["url"], quote=True) + '">' + escape(row["title"] or "Abrir vídeo") +
            '</a><small>' + escape(row["channel_title"] or "") + '</small></td>'
            '<td>' + escape(row["voice"]) + '</td>'
            '<td><span class="status ' + escape(row["review_status"]) + '">' +
            escape(row["review_status"]) + '</span></td>'
            '<td>' + escape(row["material_type"] or "unknown") + '</td>'
            '<td class="votes">' + str(row["approval_count"]) + ' / ' +
            str(row["rejection_count"]) + '</td></tr>'
        )

    empty_message = (
        '<tr class="empty"><td colspan="6">No hay candidatos todavía. '
        'Importa el catálogo y ejecuta discover-work.</td></tr>' if not rows else ""
    )
    html = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Revisión de vídeos · ai_recogeYouTube</title>
<style>
:root{color-scheme:light;--ink:#252a34;--muted:#626b78;--paper:#fff;--line:#dce1e8;--accent:#2359a8}
*{box-sizing:border-box}body{margin:0;background:#f3f5f8;color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1400px;margin:auto;padding:28px 20px}h1{margin:0 0 6px;font-size:clamp(1.5rem,3vw,2.2rem)}
p{color:var(--muted)}.notice{padding:12px 15px;border-left:4px solid var(--accent);background:#eaf1fc;border-radius:5px}
.filters{display:flex;gap:12px;flex-wrap:wrap;margin:22px 0}.filters label{display:flex;flex-direction:column;gap:4px;font-size:.9rem;font-weight:600}
input,select{font:inherit;padding:9px 10px;border:1px solid #b9c2cf;border-radius:7px;background:white;min-width:180px}
.summary{margin:12px 0;color:var(--muted)}.table-wrap{overflow:auto;background:white;border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;min-width:850px}th,td{text-align:left;padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top}
th{position:sticky;top:0;background:#edf0f5;font-size:.85rem}tr:last-child td{border-bottom:0}
a{color:var(--accent);font-weight:650;text-decoration:none}a:hover{text-decoration:underline}small{display:block;color:var(--muted);font-weight:400;overflow-wrap:anywhere}
.status{display:inline-block;padding:3px 8px;border-radius:5px;background:#edf0f5;font-size:.82rem}
.status.confirmed{background:#d9f3e3;color:#145b34}.status.rejected{background:#fde3e1;color:#8b2520}
.votes{font-variant-numeric:tabular-nums;white-space:nowrap}.hidden{display:none!important}
footer{margin-top:18px;font-size:.88rem;color:var(--muted)}
</style>
</head>
<body><main>
<h1>Revisión de vídeos musicales</h1>
<p>Panel local de candidatos relacionados con obras y voces. Abre cada vídeo para comprobarlo antes de confirmarlo.</p>
<div class="notice"><strong>Importante:</strong> la voz sugerida por una búsqueda no es una verificación musical.
Esta página es una exportación de solo lectura; los cambios editoriales se aplican con el comando
<code>ai-youtube review-video</code>. Los votos no equivalen a confirmación editorial.</div>
<div class="filters">
<label>Buscar obra, vídeo o canal<input id="q" type="search" placeholder="Título, ID, canal…"></label>
<label>Estado editorial<select id="status"><option value="">Todos</option><option value="pending">Pendiente</option><option value="confirmed">Confirmado</option><option value="rejected">Rechazado</option></select></label>
<label>Voz<select id="voice"><option value="">Todas</option><option value="soprano">Soprano</option><option value="alto">Alto</option><option value="tenor">Tenor</option><option value="bass">Bajo</option><option value="all">Todas las voces</option><option value="unknown">Desconocida</option></select></label>
</div>
<div id="summary" class="summary" aria-live="polite"></div>
<div class="table-wrap"><table><thead><tr><th>Obra</th><th>Vídeo de YouTube</th><th>Voz</th><th>Estado</th><th>Tipo de material</th><th>Aprobaciones / rechazos</th></tr></thead>
<tbody id="rows">""" + "".join(body_rows) + empty_message + """</tbody></table></div>
<footer>Datos locales del piloto ai_recogeYouTube. No se conecta a OSAP ni modifica datos de producción.</footer>
</main>
<script>
const q=document.getElementById('q'),status=document.getElementById('status'),voice=document.getElementById('voice');
const rows=[...document.querySelectorAll('#rows tr:not(.empty)')],summary=document.getElementById('summary');
function filter(){let shown=0;for(const row of rows){const ok=row.dataset.search.includes(q.value.trim().toLowerCase())&&(!status.value||row.dataset.status===status.value)&&(!voice.value||row.dataset.voice===voice.value);row.classList.toggle('hidden',!ok);if(ok)shown++}summary.textContent=shown+' de '+rows.length+' asociaciones visibles';}
[q,status,voice].forEach(el=>el.addEventListener('input',filter));filter();
</script></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return len(rows)
