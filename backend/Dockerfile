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

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files first (cache layer)
COPY pyproject.toml uv.lock ./

# Install Python deps (no dev deps)
RUN uv sync --no-dev --frozen

# Install Playwright + Chromium browser
RUN uv run playwright install chromium

# Copy application source
COPY sastaspace/ ./sastaspace/

# Persistent sites volume mount point
ENV SASTASPACE_SITES_DIR=/data/sites

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=15s \
    CMD curl -f http://localhost:8080/ || exit 1

CMD ["uv", "run", "uvicorn", "sastaspace.server:app", "--host", "0.0.0.0", "--port", "8080"]
