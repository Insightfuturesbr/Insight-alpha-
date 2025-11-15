# syntax=docker/dockerfile:1

# Production image for Insight Futures (Flask + Gunicorn)
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ENV=production \
    FLASK_ENV=production \
    PORT=8000 \
    WORKERS=2 \
    THREADS=2 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/app/.cache/mpl

WORKDIR /app

# System deps (minimal); install build tools only when needed
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better layer caching
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy application code
COPY . .

# Ensure runtime directories exist (and are owned by the runtime user if added)
RUN mkdir -p /app/uploads /app/outputs /app/.cache/mpl

# Optional: drop privileges (uncomment if desired)
# RUN useradd -u 10001 -ms /bin/bash appuser \
#     && chown -R appuser:appuser /app
# USER appuser

EXPOSE 8000

# Default command: run Gunicorn with app factory
# Use shell form to allow env var expansion (required on platforms like Render)
# PORT is provided by platform; fallback defaults included
CMD ["/bin/sh", "-c", \
     "exec gunicorn -b 0.0.0.0:${PORT:-8000} -w ${WORKERS:-2} -k gthread --threads ${THREADS:-2} --timeout 120 --access-logfile - --error-logfile - wsgi:app" ]
