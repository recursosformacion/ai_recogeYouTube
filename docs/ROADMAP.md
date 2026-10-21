# Hoja de ruta y criterios de aceptación

## F0 — Fundamentos
- [x] Estructura Python y CLI.
- [x] Configuración por variables de entorno.
- [x] Modelos de obra/candidato.
- [x] SQLite local separado de OSAP.
- [ ] Pruebas automatizadas y ejecución en CI.
- [ ] Importador de catálogo CSV con validación de IDs.

## F1 — YouTube
- [ ] Cliente de API con `search.list`, `videos.list` y API de playlists.
- [ ] Generar consultas por voz y variantes de título.
- [ ] Respetar cuota, limitar peticiones, reintentar errores transitorios.
- [ ] Cachear consultas y evitar búsquedas duplicadas.
- [ ] Importar y guardar resultados idempotentemente.
- [ ] Exportar CSV/JSON y resumen por obra/voz.

Aceptación: con un catálogo de prueba y una clave configurada, una ejecución repetida no duplica vídeos; sin clave, el modo de diagnóstico y las pruebas funcionan.

## F2 — Medir precisión
- [ ] Crear muestra etiquetada manualmente.
- [ ] Medir precisión y cobertura por voz/tipo de pista.
- [ ] Afinar consultas a partir de errores observados.
- [ ] Separar claramente candidatos pendientes y verificados.

Aceptación: el informe muestra falsos positivos y no presenta candidatos como confirmados sin revisión/evidencia.

## F3 — Audio
- [ ] Pipeline de análisis de archivos locales autorizados.
- [ ] Estimación de F0/contorno melódico y detección de señal polifónica.
- [ ] Comparación en ventanas, tolerancia a tempo y transposición.
- [ ] Guardar resultados reproducibles con versión de herramienta.

Aceptación: prueba con ejemplos etiquetados y umbrales medidos; ninguna inferencia de voz individual basada solo en tesitura.

## F4 — PDF original
- [ ] Herramienta para elegir página y recortar pentagrama.
- [ ] Anotación manual asistida de un fragmento musical corto.
- [ ] Comparación con audio y visualización de evidencia.
- [ ] Evaluar antes de intentar reconocimiento automático de notas.

Aceptación: un músico puede comprobar por qué el sistema propone una coincidencia y corregir la referencia.

## F5 — Integración OSAP
- [ ] Acordar formato de intercambio y reglas de identidad de obra.
- [ ] Exportación de candidatos aprobados.
- [ ] Prueba en entorno aislado.
- [ ] Escritura de producción solo mediante un procedimiento explícito y revisado.
