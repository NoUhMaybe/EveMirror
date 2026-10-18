FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/server.lock
COPY pyproject.toml ./
COPY apps/ apps/
COPY packages/ packages/
RUN pip install --no-cache-dir --no-deps . && useradd --uid 10001 --create-home eve
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2)"
CMD ["uvicorn", "apps.server.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--ws-max-size", "24000", "--ws-max-queue", "8", "--no-access-log"]
