# Slim image. Agno + httpx + ollama-py — no native compilation needed.
FROM python:3.13-slim

WORKDIR /app

# Install only runtime deps. Build deps and dev deps stay out.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir .

# Runs as non-root.
RUN useradd -u 1000 -m moderator
USER moderator

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD curl -fsS "${OLLAMA_HOST:-http://host.docker.internal:11434}/" >/dev/null || exit 1

CMD ["python", "-m", "sastaspace_moderator.main"]
