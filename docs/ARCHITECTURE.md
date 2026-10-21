# Arquitectura

## Componentes

- `catalog`: importación de obras desde CSV/JSON exportado por OSAP.
- `queries`: consultas multilingües por obra, voz y tipo de material.
- `youtube`: cliente de YouTube Data API v3, cuota, reintentos y paginación.
- `repository`: persistencia SQLite y deduplicación por ID de vídeo.
- `classification`: clasificación heurística con evidencias explícitas.
- `review/export`: cola de revisión y exportación CSV/JSON.
- `audio` (opcional): análisis de archivos locales autorizados; no obtiene ni descarga medios.
- `score` (experimental): anotación de fragmentos de PDF/imagen y comparación musical.

## Modelo de evidencia

Cada candidato debe conservar:
- consulta que lo descubrió;
- ID estable de YouTube y URL;
- título, canal, descripción y fecha publicados cuando estén disponibles;
- obra asociada y razón de la asociación;
- voz y tipo de material estimados;
- evidencias textuales/acústicas separadas;
- confianza y estado de revisión.

La etiqueta de voz no se considera confirmada solo por encontrar una palabra en el título. Una pista de ensayo puede incluir acompañamiento; una interpretación completa puede contener todas las voces.

## Comparación de audio y partitura sin MusicXML

No se convierte la partitura entera. El flujo experimental es:
1. Elegir una región de la página original y el pentagrama de la voz.
2. Anotar manualmente unas pocas notas/intervalos de referencia, con sus tiempos relativos aproximados.
3. Extraer un contorno de altura del audio local autorizado.
4. Alinear secuencias con tolerancia a tempo variable (por ejemplo, DTW).
5. Comparar intervalos y ritmo; permitir transposición cuando proceda.
6. Registrar puntuación, ventana comparada y limitaciones.

Primero se validará con pistas de voz aislada. La separación automática de soprano/alto/tenor/bajo en un coro completo queda fuera del MVP, porque es considerablemente más difícil y puede inducir falsos positivos.

## Cuotas y uso de YouTube

Usar la YouTube Data API oficial y sus límites documentados. No incrustar claves en código, commits o logs. La primera versión solo almacena metadatos y enlaces. Cualquier análisis posterior usa medios proporcionados localmente o con permiso adecuado, respetando las condiciones de la fuente.
