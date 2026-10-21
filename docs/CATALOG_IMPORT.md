# Importar el catálogo de obras

La primera versión no se conecta directamente a la base de datos de OSAP. Exporta una muestra o un catálogo completo autorizado a CSV y usa el importador local.

Columnas obligatorias:
- `work_id`: identificador estable de la obra en OSAP.
- `title`: título principal.

Columnas opcionales:
- `composers`
- `alternate_titles`
- `catalog_numbers`
- `languages`
- `formation`

En los campos con varios valores, separa los elementos con `|`. Consulta `examples/catalog.example.csv`.

Mantén el ID de OSAP tal como se exportó; no generes IDs nuevos por título, porque varias obras pueden compartir nombres y una misma obra puede tener títulos alternativos.
