# Contrato de integración directa

Este contrato permite que una futura integración desde OSAP invoque las funciones del piloto sin usar la página web. El proyecto sigue siendo independiente y **no escribe en la base de datos de producción de OSAP**.

## 1. Buscar vídeos en YouTube

Función Python: `ai_recogeyoutube.global_search.search_global`

```python
from pathlib import Path
from ai_recogeyoutube.global_search import search_global

results = search_global(
    db_path=Path("data/ai_recogeyoutube.sqlite"),
    song="Ave verum corpus",
    author="Mozart",
    voice="all",
    limit=50,
)
```

Parámetros:
- `db_path`: ruta a la base SQLite local del piloto.
- `song`: título o fragmento del título; opcional si se indica autor.
- `author`: compositor; opcional si se indica título.
- `voice`: `all` (consultas para todas las voces), `song` (canción completa/sin término de voz), `soprano`, `alto`, `tenor` o `bass`.
- `limit`: máximo de resultados, limitado internamente a 50.

Se requiere configurar `YOUTUBE_API_KEY`. La búsqueda utiliza YouTube Data API y consume cuota. Se debe aportar al menos título o autor.

Cada elemento devuelto contiene `work_id`, `work_title`, `video_id`, `video_title`, `url`, `channel`, `voice`, `material_type`, `approval_count`, `rejection_count`, `author_votes` y `last_vote`.

El vínculo a una obra del catálogo local solo se asigna cuando la búsqueda identifica una coincidencia en las obras importadas. Los resultados globales sin coincidencia se devuelven con `work_id` vacío y no deben votarse como asociación confirmada.

## 2. Registrar una decisión

Función Python: `ai_recogeyoutube.community.record_promotion`

```python
from pathlib import Path
from ai_recogeyoutube.community import record_promotion

record_promotion(
    Path("data/ai_recogeyoutube.sqlite"),
    user_id="identificador-proporcionado-por-osap",
    display_name="Usuario",
    work_id="ID_LOCAL_DE_OBRA",
    video_id="ID_DE_YOUTUBE",
    url="https://www.youtube.com/watch?v=ID_DE_YOUTUBE",
    title="Título del vídeo",
    channel_title="Canal de YouTube",
    voice="soprano",
    decision="approved",
    material_type="unknown",
    note="",
)
```

Campos obligatorios de la decisión:
- `user_id`: identificador que proporciona la aplicación llamante. En la web local es texto libre; no se valida ni autentica.
- `work_id`, `video_id`, `url`, `title`, `voice` y `decision`.
- `decision`: `approved` o `rejected`.
- `display_name`, `channel_title`, `material_type` y `note` tienen valores por defecto documentados en la firma.

La decisión es única por usuario, obra, vídeo y voz: si el mismo usuario vuelve a votar esa combinación, su voto se actualiza, no se duplica. La función asegura la existencia de los registros normalizados de vídeo y relación obra/vídeo/voz antes de guardar el voto.

## 3. Reglas de integración

1. OSAP debe pasar el identificador de usuario que ya conoce; este piloto no implementa autenticación.
2. Usar la misma base SQLite del piloto para búsqueda y votos. No conectar esta función directamente a la base de producción de OSAP.
3. Un voto positivo es una señal comunitaria, no una validación editorial. El estado editorial (`pending`, `confirmed`, `rejected`) es independiente.
4. La relevancia del canal se calcula a partir de sus votos positivos registrados en el piloto; no es una identidad verificada del autor musical.
5. Las funciones Python son el contrato inicial. No se promete aún una API HTTP estable; si OSAP se ejecuta en otro proceso/servidor, habrá que definir el mecanismo de llamada o un servicio interno antes de desplegarlo.
6. La llamada a búsqueda puede consumir cuota de YouTube. No lanzar búsquedas amplias repetidamente sin necesidad.

## 4. Errores esperables

La búsqueda puede lanzar `ValueError` si falta título y autor, si la voz no es válida o si falta `YOUTUBE_API_KEY`; también puede propagar errores de configuración, red o API. La integración debe capturar los errores y mostrarlos como un fallo de búsqueda, sin tratarlo como una lista vacía de resultados.

La escritura de votos puede lanzar `ValueError` ante datos no válidos y errores de acceso a la base de datos. Debe ejecutarse solo con una asociación de obra identificada.
