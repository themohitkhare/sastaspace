FROM python:3.11-slim

# System deps for Playwright/Chromium + curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libx11-xcb1 \
    libxfixes3 \
    fonts-liberation \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager — avoids pip/wheel entirely)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Create non-root user and data directory before installing anything
RUN useradd -m -u 1000 appuser && mkdir -p /data/sites && chown appuser /data/sites

# Copy lockfile and project files (uv uses the frozen lockfile for reproducible builds)
COPY pyproject.toml uv.lock ./
COPY sastaspace/ ./sastaspace/

# Install Python deps using uv with frozen lockfile into a virtualenv
RUN uv sync --frozen --no-dev --no-editable

# Add venv to PATH so all installed entrypoints (uvicorn, playwright) are accessible
ENV PATH="/app/.venv/bin:$PATH"

# Switch to non-root user for Playwright install so browsers land in ~/.cache
USER appuser
ENV HOME=/home/appuser

# Install Playwright + Chromium browser (uses .venv/bin/playwright, installs to ~/.cache)
RUN playwright install chromium

# Persistent sites volume mount point
ENV SASTASPACE_SITES_DIR=/data/sites

EXPOSE 8080

# Copy entrypoint script (must be done before USER switch, then chown)
COPY --chown=appuser:appuser backend/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=15s \
    CMD curl -f http://localhost:8080/ || exit 1

ENTRYPOINT ["./entrypoint.sh"]
