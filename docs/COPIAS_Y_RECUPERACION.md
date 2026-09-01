# Copias de seguridad y recuperación

## Contenido de una copia

`backup_crm` genera un ZIP con:

- Todos los datos de negocio y usuarios en JSON portable.
- Las imágenes del directorio multimedia.
- Las migraciones aplicadas.
- Un manifiesto con tamaño y SHA-256 de cada archivo.

Las sesiones, permisos generados y tipos de contenido se regeneran y no se incluyen.

## Copia manual

```bash
python manage.py backup_crm --keep 30
python manage.py verify_backup /ruta/crm-backup-AAAAMMDDTHHMMSSZ.zip
```

En Windows se puede programar diariamente `scripts/backup_crm.ps1` desde el Programador de tareas. En Linux se recomienda ejecutar dentro del contenedor:

```cron
15 2 * * * docker compose -f /srv/crm/compose.production.yml exec -T web python manage.py backup_crm --keep 30
45 2 * * * docker compose -f /srv/crm/compose.production.yml exec -T web python manage.py crm_healthcheck
```

El volumen de copias debe replicarse cifrado fuera del servidor. Una distribución razonable es conservar 30 copias diarias, 12 mensuales y al menos una copia externa.

## Restauración

La restauración reemplaza la base de datos y las imágenes. Debe realizarse con la aplicación detenida:

```bash
docker compose -f compose.production.yml stop web proxy
docker compose -f compose.production.yml run --rm web \
  python manage.py restore_crm /app/backups/copia.zip --confirm
docker compose -f compose.production.yml up -d web proxy
docker compose -f compose.production.yml exec web python manage.py crm_healthcheck
```

Antes de modificar nada, el comando verifica rutas, JSON, tamaños y checksums. Por defecto también genera una copia del estado previo. `--no-safety-backup` solo debe utilizarse cuando no quede espacio y exista otra copia comprobada.

## Simulacro

Al menos una vez al trimestre se debe restaurar la última copia en un entorno aislado y comprobar:

1. Inicio de sesión.
2. Recuento de contactos, inmuebles, encargos, pedidos, ventas y alquileres.
3. Acceso a varias imágenes.
4. Apertura de agenda y dashboard.
5. Ejecución completa de pruebas y `crm_healthcheck`.
