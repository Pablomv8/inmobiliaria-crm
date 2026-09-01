# Mantenimiento preventivo

## Diario

- Ejecutar `backup_crm` y `crm_healthcheck`.
- Revisar errores 500 y fallos reiterados de autenticación.
- Confirmar que `/health/ready/` responde correctamente.

## Semanal

- Revisar espacio de PostgreSQL, imágenes y copias.
- Comprobar tareas fallidas, operaciones atascadas y registros sin responsable.
- Instalar actualizaciones primero en un entorno de pruebas.

## Mensual

- Probar una restauración en un entorno aislado.
- Revisar usuarios activos y permisos.
- Revisar consultas lentas e índices de PostgreSQL.
- Actualizar dependencias con sus avisos de seguridad y ejecutar toda la batería de pruebas.

## Antes de cada despliegue

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --parallel 4
python manage.py check --deploy --settings=config.settings_production
```

Después del despliegue se comprobarán healthchecks, inicio de sesión, dashboard, agenda, creación de un registro no crítico y acceso a una imagen privada.
