FROM node:22-alpine AS assets
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY static ./static
COPY templates ./templates
RUN npm run build

FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup --system crm && adduser --system --ingroup crm crm
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=crm:crm . .
COPY --from=assets --chown=crm:crm /app/static/css/main.min.css /app/static/css/main.min.css
RUN chmod +x /app/deploy/entrypoint.sh && mkdir -p /app/media /app/staticfiles /app/backups && chown -R crm:crm /app/media /app/staticfiles /app/backups
USER crm
EXPOSE 8000
ENTRYPOINT ["/app/deploy/entrypoint.sh"]
