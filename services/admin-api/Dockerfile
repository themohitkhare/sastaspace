FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir .

RUN useradd -u 1000 -m adminapiuser
USER adminapiuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=3170

EXPOSE 3170

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD curl -fsS "http://127.0.0.1:${PORT:-3170}/healthz" >/dev/null || exit 1

CMD ["python", "-m", "sastaspace_admin_api.main"]
