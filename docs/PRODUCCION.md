# Operación del CRM en producción

## Arquitectura recomendada

- PostgreSQL como base de datos.
- Django servido por Gunicorn.
- Nginx para archivos estáticos y proxy interno.
- Un terminador HTTPS externo delante del puerto local `127.0.0.1:8080`.
- Volúmenes persistentes e independientes para PostgreSQL, imágenes y copias.

El archivo `compose.production.yml` no publica PostgreSQL ni Gunicorn. El proxy solo escucha en localhost; el dominio público debe llegar mediante HTTPS desde el proxy principal del servidor.

## Puesta en marcha

1. Copiar `.env.example` a `.env` y sustituir todos los valores de ejemplo.
2. Generar una clave con al menos 50 caracteres.
3. Definir `POSTGRES_PASSWORD` fuera del repositorio.
4. Configurar el dominio y el certificado HTTPS en el proxy frontal.
5. Ejecutar:

```bash
docker compose -f compose.production.yml build
docker compose -f compose.production.yml up -d
docker compose -f compose.production.yml exec web python manage.py createsuperuser
```

Cada arranque aplica migraciones, recopila estáticos y ejecuta `check --deploy`. Si cualquiera de esas operaciones falla, Gunicorn no se inicia.

## Despliegue de una actualización

```bash
docker compose -f compose.production.yml exec web python manage.py backup_crm
docker compose -f compose.production.yml build web
docker compose -f compose.production.yml up -d web proxy
docker compose -f compose.production.yml exec web python manage.py crm_healthcheck
```

No se debe desplegar si la integración continua tiene pruebas fallidas o migraciones sin generar.

## Monitorización

- Disponibilidad básica: `GET /health/live/`.
- Base de datos y almacenamiento: `GET /health/ready/`.
- Comprobación diaria completa: `python manage.py crm_healthcheck`.
- Cada respuesta incluye `X-Request-ID`; la misma referencia aparece en los logs y en los errores 500.
- `SENTRY_DSN` activa Sentry sin enviar información personal por defecto.

Los logs se escriben en salida estándar para que Docker o el proveedor los rote y conserve. Debe configurarse una alerta para errores 500, fallos de inicio de sesión repetidos y healthchecks fallidos.

## Rendimiento

Los listados y paneles disponen de paginación, cargas relacionadas e índices para agente, estado, fechas, dirección y periodos. Antes de aumentar recursos, deben revisarse las consultas lentas de PostgreSQL y el tiempo de respuesta de dashboard, agenda y avisos con un volumen representativo.
