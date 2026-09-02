FROM node:22-alpine AS assets
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY static ./static
COPY templates ./templates
RUN npm run build \
    && cp node_modules/leaflet/dist/leaflet.css static/leaflet.css \
    && cp node_modules/leaflet/dist/leaflet.js static/leaflet.js \
    && cp node_modules/leaflet/dist/leaflet.js.map static/leaflet.js.map \
    && mkdir -p static/images \
    && cp node_modules/leaflet/dist/images/* static/images/

FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup --system crm && adduser --system --ingroup crm crm
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=crm:crm . .
COPY --from=assets --chown=crm:crm /app/static /app/static
RUN chmod +x /app/deploy/entrypoint.sh \
    && mkdir -p /app/media /app/staticfiles /app/backups /app/data \
    && chown -R crm:crm /app/media /app/staticfiles /app/backups /app/data
USER crm
EXPOSE 8000
ENTRYPOINT ["/app/deploy/entrypoint.sh"]
