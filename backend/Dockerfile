FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies from pyproject.toml
# uv can read pyproject.toml directly, but for simplicity we install directly
RUN uv pip install --system \
    "fastapi>=0.104.0" \
    "uvicorn[standard]>=0.24.0" \
    "duckdb>=0.9.0" \
    "pydantic>=2.5.0" \
    "pydantic-settings>=2.1.0" \
    "jinja2>=3.1.0" \
    "python-multipart>=0.0.6"

# Copy application code
COPY backend/app ./app

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
