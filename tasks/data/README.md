# Catálogo de calles de Arcos de la Frontera

`arcos_streets.json` es una instantánea de los tramos viarios con nombre del
término municipal de Arcos de la Frontera. Se incluye para poder inicializar la
base de datos en entornos sin conexión saliente, como respaldo de la descarga
directa que realiza `import_arcos_streets`.

- Fuente: colaboradores de OpenStreetMap.
- Consulta: Overpass API, instancia `overpass.private.coffee`.
- Descarga: 3 de septiembre de 2026.
- Datos procesados: 1.228 tramos, agrupados por el CRM en 617 calles.
- Licencia: Open Database License (ODbL), consulta los términos y la atribución
  en <https://www.openstreetmap.org/copyright>.

Para importar o actualizar el catálogo desde esta copia:

```bash
python manage.py import_arcos_streets --file tasks/data/arcos_streets.json
```

El comando es idempotente: crea las calles que falten y actualiza nombre,
geometría e identificadores de las que ya existan. No elimina otras calles salvo
que se añada explícitamente `--prune`.

