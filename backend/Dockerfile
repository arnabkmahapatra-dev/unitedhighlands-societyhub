# SocietyHub production image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app
COPY frontend ./frontend

# Data directory for the SQLite database (mounted as a volume in production)
RUN mkdir -p /data
ENV DATABASE_URL=sqlite:////data/societyhub.db

EXPOSE 8000

# Bind to Render's $PORT if provided (falls back to 8000 for local Docker).
# Shell form so ${PORT} is expanded at runtime. WEB_CONCURRENCY controls workers.
CMD gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    -w ${WEB_CONCURRENCY:-2} \
    -b 0.0.0.0:${PORT:-8000} \
    --timeout 60
