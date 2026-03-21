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

# Create non-root user and data directory before installing anything
RUN useradd -m -u 1000 appuser && mkdir -p /data/sites && chown appuser /data/sites

# Copy project files
COPY pyproject.toml ./

# Copy application source (needed for pip install -e or direct install)
COPY sastaspace/ ./sastaspace/

# Install Python deps as root (system-wide, readable by all users)
RUN pip install --no-cache-dir .

# Switch to non-root user for Playwright install so browsers land in ~/.cache
USER appuser
ENV HOME=/home/appuser

# Install Playwright + Chromium browser (installs to /home/appuser/.cache)
RUN playwright install chromium

# Persistent sites volume mount point
ENV SASTASPACE_SITES_DIR=/data/sites

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=15s \
    CMD curl -f http://localhost:8080/ || exit 1

CMD ["uvicorn", "sastaspace.server:app", "--host", "0.0.0.0", "--port", "8080"]
