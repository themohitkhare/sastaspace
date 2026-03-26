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
# Install via npm (claude-code is published as @anthropic-ai/claude-code)
RUN npm install -g @anthropic-ai/claude-code && \
    echo "Claude CLI installed: $(claude --version 2>/dev/null || echo 'version check skipped')"

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
