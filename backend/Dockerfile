FROM python:3.11-slim

WORKDIR /app

# Install uv and system dependencies for OCR / OpenCV
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies using uv (reads dependencies from pyproject.toml)
# Install dependencies directly from the dependencies list
RUN uv pip install --system \
    "fastapi>=0.104.0" \
    "uvicorn[standard]>=0.24.0" \
    "motor>=3.3.0" \
    "pydantic>=2.5.0" \
    "pydantic-settings>=2.1.0" \
    "jinja2>=3.1.0" \
    "python-multipart>=0.0.6" \
    "opencv-python>=4.13.0" \
    "pytesseract>=0.3.13"

# Copy application code
COPY app ./app

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
