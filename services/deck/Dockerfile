FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src

# Default install is the lightweight path (no audiocraft/torch). Builders that
# want real MusicGen output can rebuild with `pip install .[musicgen]` after
# COPY, or override the CMD to a different image.
RUN pip install --no-cache-dir .

RUN useradd -u 1000 -m deckuser
USER deckuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8081

EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8081}/healthz" >/dev/null || exit 1

CMD ["python", "-m", "sastaspace_deck.main"]
