# ai_recogeYouTube

Sistema para descubrir, clasificar y verificar grabaciones de YouTube asociadas a obras musicales, con prioridad para pistas de ensayo de soprano, alto, tenor y bajo (SATB) del catálogo OSAP.

## Objetivo

Encontrar enlaces útiles por obra y por voz, registrar evidencias y medir la calidad antes de publicar los resultados en OSAP.

**No se requiere convertir las partituras PDF a MusicXML.** La comparación musical se diseñará para poder trabajar, cuando sea necesario, con fragmentos de la imagen de la partitura original.

## Principios

- Python, herramientas gratuitas y módulos reemplazables.
- API oficial de YouTube Data API para búsqueda y metadatos; claves solo mediante variables de entorno.
- No descargar audio ni extraer medios automáticamente en la primera fase. Para análisis acústico se usarán archivos de prueba autorizados/locales o fuentes con permisos adecuados.
- Ninguna coincidencia de texto se considera verificación musical.
- No escribir en la base de datos de producción de OSAP durante el piloto.
- Resultados reproducibles, idempotentes, con procedencia, estado y evidencia.
- Las puntuaciones son señales de confianza, no garantías.

## Flujo propuesto

1. **Entrada de catálogo**: importar una exportación CSV/JSON de obras OSAP (ID estable, títulos alternativos, compositor, catálogo, idioma y formación cuando existan).
2. **Generación de consultas**: títulos y variantes + soprano/alto/tenor/bass, SATB, practice, rehearsal, part, learning track y equivalentes en otros idiomas.
3. **Descubrimiento**: vídeos, canales y listas de reproducción mediante YouTube Data API.
4. **Normalización y deduplicación**: guardar ID de vídeo/lista, URL canónica, título, canal, fecha, duración si está disponible y consulta de origen.
5. **Clasificación**: posible obra, voz probable y tipo de material (pista aislada, ensayo por voces, interpretación completa, acompañamiento, desconocido).
6. **Verificación**: reglas y evidencias; más adelante análisis de audio y comparación con la partitura.
7. **Revisión**: candidatos pendientes, confirmados o descartados.
8. **Exportación**: CSV/JSON para revisión e integración futura con OSAP, sin escrituras automáticas en producción.

## Fases

### Fase 0 — base verificable
- CLI y configuración.
- Modelos de candidatos y catálogo.
- Persistencia local SQLite.
- Importación de catálogo CSV.
- Pruebas automatizadas con datos ficticios.
- Modo de simulación sin credenciales.

### Fase 1 — descubrimiento YouTube
- Adaptador de YouTube Data API.
- Búsquedas por obra y voz con cuotas controladas.
- Descubrimiento de listas de reproducción y sus elementos.
- Caché, límites, reintentos y deduplicación.
- Exportación y resumen de cobertura.

### Fase 2 — evaluación de resultados
- Etiquetado de una muestra real: útil/no útil, voz, tipo.
- Métricas de precisión por consulta y voz.
- Mejora del generador de consultas y clasificación.

### Fase 3 — análisis acústico opcional
- Analizar archivos locales autorizados o aportados por el usuario.
- Estimar altura fundamental, contorno melódico, tempo y presencia de varias fuentes.
- Distinguir explícitamente pistas monofónicas de mezclas corales.
- No afirmar que una voz es soprano/alto/tenor/bajo solo por la tesitura estimada.

### Fase 4 — comparación con PDF original
- Seleccionar regiones de pentagramas directamente de la página PDF o imagen.
- Registrar manualmente o semi-automáticamente unas pocas notas de referencia por fragmento, sin reconstruir la partitura completa.
- Comparar contorno de alturas, intervalos y ritmo con el audio.
- Evaluar falsos positivos antes de automatizar reconocimiento visual.

### Fase 5 — integración OSAP
- Exportación estable y revisable.
- Diseñar el contrato de integración cuando el piloto esté validado.
- Sin escrituras de producción por defecto.

## Configuración

1. Instalar Python 3.11 o posterior.
2. Crear entorno virtual e instalar el proyecto.
3. Copiar `.env.example` a `.env` y configurar la clave de YouTube si se desea usar la API.
4. Ejecutar `ai-youtube doctor` y `ai-youtube init-db`.
5. Ejecutar primero en modo simulación.

Consulta `docs/ARCHITECTURE.md` y `docs/ROADMAP.md`.

## Límites de la primera versión

- La API de YouTube tiene cuotas y puede no devolver todos los vídeos relevantes.
- Los títulos, descripciones y listas son indicios, no prueba de qué se oye.
- El sistema guarda metadatos y enlaces; no descarga audios.
- El análisis acústico y la comparación con partituras se incorporan después de validar el descubrimiento.


## Modelo local de validación comunitaria

El piloto incluye un modelo SQLite independiente documentado en [`docs/DATA_MODEL_COMMUNITY.md`](docs/DATA_MODEL_COMMUNITY.md). Separa:

- `youtube_videos`: metadatos únicos por ID de YouTube.
- `work_videos`: relación obra/vídeo/voz.
- `users`: identidades locales de prueba.
- `promotions`: una decisión por usuario, obra, vídeo y voz.
- `work_video_scores`: vista con contadores calculados desde las decisiones, sin duplicar votos.

Después de descubrir candidatos, se pueden sincronizar con las tablas de revisión:

```powershell
ai-youtube sync-review --work-id ID_DE_OBRA
ai-youtube rank-videos ID_DE_OBRA --voice soprano

# Confirmar o descartar una asociación tras revisión humana
ai-youtube review-video --work-id ID_DE_OBRA --video-id ID_YOUTUBE --voice soprano --status confirmed
ai-youtube review-video --work-id ID_DE_OBRA --video-id ID_YOUTUBE --voice soprano --status rejected
```

Para probar una aprobación manual en la base local:

```powershell
ai-youtube promote-video --work-id ID_DE_OBRA --video-id ID_YOUTUBE --url "https://www.youtube.com/watch?v=ID_YOUTUBE" --title "Título del vídeo" --user-id prueba-1 --voice soprano --decision approved
ai-youtube rank-videos ID_DE_OBRA --voice soprano
```

Los IDs de usuario de estos comandos son únicamente etiquetas locales de prueba; no equivalen a usuarios autenticados. La API futura debe obtener la identidad desde el servidor. Todo el modelo comunitario es experimental y no escribe en OSAP.


El estado editorial se gestiona por separado de los votos de la comunidad:
- `pending`: candidato aún no verificado.
- `confirmed`: asociación obra/vídeo/voz revisada y aceptada; se prioriza en el ranking.
- `rejected`: asociación revisada y descartada; queda detrás de pendientes.

`review-video` requiere que la asociación ya exista en las tablas de revisión, normalmente tras ejecutar `sync-review`. Los votos comunitarios no cambian por modificar el estado editorial, y el estado editorial no suma votos.
