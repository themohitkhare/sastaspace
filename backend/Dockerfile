FROM python:3.11-slim

# System deps — curl for healthcheck, libmagic1 for python-magic
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Node.js 22 — required for React component pipeline (Vite builds)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI — required for swarm pipeline agent calls
# Download the binary directly (skip the install script's shell integration)
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then PLATFORM="linux-x64"; \
    elif [ "$ARCH" = "arm64" ]; then PLATFORM="linux-arm64"; \
    else echo "Unsupported arch: $ARCH" && exit 1; fi && \
    GCS_BUCKET="https://storage.googleapis.com/claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819/claude-code-releases" && \
    curl -fsSL "$GCS_BUCKET/latest/$PLATFORM/claude" -o /usr/local/bin/claude && \
    chmod +x /usr/local/bin/claude && \
    echo "Claude CLI installed: $(/usr/local/bin/claude --version 2>/dev/null || echo 'version check failed')"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

RUN useradd -m -u 1000 appuser && mkdir -p /data/sites && chown appuser /data/sites

COPY pyproject.toml uv.lock ./
COPY sastaspace/ ./sastaspace/
COPY components/ ./components/
COPY redesign-template/ ./redesign-template/

# Install Python deps
RUN uv sync --frozen --no-dev --no-editable

# Pre-install React template deps (avoids npm install at runtime)
RUN cd redesign-template && npm install --prefer-offline --no-audit --no-fund \
    && chown -R appuser:appuser /app/redesign-template

ENV PATH="/app/.venv/bin:$PATH"

USER appuser
ENV HOME=/home/appuser

ENV SASTASPACE_SITES_DIR=/data/sites

EXPOSE 8080

COPY --chown=appuser:appuser backend/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=15s \
    CMD curl -f http://localhost:8080/ || exit 1

ENTRYPOINT ["./entrypoint.sh"]
