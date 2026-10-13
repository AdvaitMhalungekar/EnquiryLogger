# ============================================================
# Dockerfile for Render.com (FastAPI + Static Frontend)
# Render injects $PORT at runtime (default: 10000)
# ============================================================

FROM python:3.11-slim

# Create a non-root user for security
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Set ownership
RUN chown -R appuser:appuser /app
USER appuser

# Render dynamically assigns $PORT — expose a default for local runs
EXPOSE 8000

# Shell form so $PORT is expanded at runtime by Render
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
