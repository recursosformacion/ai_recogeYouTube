# Modelo de datos: vídeos, obras y promoción comunitaria

## Alcance

Este diseño pertenece al piloto independiente `ai_recogeYouTube`. Usa SQLite local y no lee ni modifica bases de datos, servicios o ficheros de OSAP. La integración futura será una adaptación explícita, después de validar el comportamiento.

## Entidades

- **`youtube_videos`**: una fila por ID de vídeo de YouTube. Guarda URL canónica y metadatos; el vídeo no se duplica si se relaciona con varias obras.
- **`work_videos`**: relación entre obra, vídeo y voz. La clave compuesta `(work_id, video_id, voice)` permite que el mismo vídeo sirva para distintas obras o voces. `review_status` es el estado de revisión del vínculo, no una conclusión derivada únicamente de la búsqueda.
- **`users`**: identificadores locales para pruebas. No representa autenticación real.
- **`promotions`**: decisión de un usuario para una combinación concreta de obra, vídeo y voz. La clave compuesta impide que un mismo usuario incremente repetidamente el contador con clics duplicados. Una nueva decisión actualiza la anterior.
- **Vista `work_video_scores`**: calcula `approval_count` y `rejection_count` desde las decisiones individuales. No mantiene un contador redundante que pueda quedar desincronizado.

## Voces y tipos

Voces iniciales: `soprano`, `alto`, `tenor`, `bass`, `all` y `unknown`. `all` indica una interpretación completa o un recurso común; no significa que el vídeo haya sido validado para cada voz individual.

Tipos de material iniciales: `individual_part`, `sectional_rehearsal`, `full_performance`, `accompaniment`, `unknown`. Se pueden ampliar según los resultados del piloto.

## Reglas de integridad

1. Las coincidencias encontradas por búsqueda comienzan como candidatas; no se consideran verificadas.
2. La aprobación de un usuario queda registrada individualmente y se cuenta una sola vez por obra/vídeo/voz.
3. La puntuación de comunidad no sustituye la revisión. Los vínculos confirmados se priorizan y, dentro de cada estado, se ordenan por aprobaciones, con los rechazos como señal secundaria.
4. En la integración futura, el identificador del usuario deberá obtenerse de la sesión autenticada del servidor. Nunca se confiará en un ID de usuario enviado sin validar por el navegador.
5. No se descargan ni extraen medios de YouTube; el piloto guarda enlaces y metadatos.

## Prueba manual futura

Tras importar una obra de prueba, registrar una promoción con `record_promotion(...)`, volver a registrarla con el mismo usuario y comprobar que `approval_count` sigue siendo 1. Registrar una aprobación de un segundo usuario y comprobar que el contador pasa a 2. Repetir para otra voz y verificar que los contadores quedan separados.

## Límite del piloto

Los identificadores y nombres de usuarios son locales de prueba. No hay registro público, autenticación, moderación ni garantías de que quien vota sea una persona distinta. Antes de publicar resultados, habrá que definir autenticación, abuso, retirada de votos, auditoría y política de moderación.
