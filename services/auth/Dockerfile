FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir .

RUN useradd -u 1000 -m authuser
USER authuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

EXPOSE 8080

# In compose, network_mode: host overrides the bind port via $PORT env.
# Healthcheck targets that env so it works in both default + host mode.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8080}/healthz" >/dev/null || exit 1

CMD ["python", "-m", "sastaspace_auth.main"]
