FROM node:24-bookworm-slim AS dashboard
WORKDIR /build/apps/dashboard
COPY apps/dashboard/package*.json ./
RUN npm ci
COPY packages/application/ /build/packages/application/
COPY apps/dashboard/ ./
RUN npm run contracts:check && npm run typecheck && npm run build

FROM python:3.12-slim
ARG EVE_INSTALL_SPEECH=0
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 EVE_SERVER_BROWSER__STATIC_ROOT=/app/dashboard
WORKDIR /app
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/server.lock
RUN if [ "$EVE_INSTALL_SPEECH" = "1" ]; then pip install --no-cache-dir -r requirements/voice-server.lock; fi
COPY pyproject.toml ./
COPY apps/__init__.py apps/config.py apps/
COPY apps/edge/ apps/edge/
COPY apps/server/ apps/server/
COPY packages/ packages/
COPY --from=dashboard /build/apps/dashboard/dist/ dashboard/
RUN pip install --no-cache-dir --no-deps . && useradd --uid 10001 --create-home eve \
    && mkdir -p /var/lib/eve && chown 10001:10001 /var/lib/eve
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2)"
CMD ["uvicorn", "apps.server.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--ws-max-size", "24000", "--ws-max-queue", "8", "--no-access-log"]
