FROM python:3.11-slim-bullseye AS builder

WORKDIR /app
COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential rustc cargo && \
    python -m venv /venv && \
    /venv/bin/pip install --no-cache-dir --upgrade pip && \
    /venv/bin/pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove build-essential rustc cargo && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

FROM python:3.11-slim-bullseye AS runner
WORKDIR /app

# Copy venv from builder stage
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"

# Copy app code
COPY . .

# Create non-root user
RUN useradd -m appuser && \
    chown -R appuser:appuser /app
USER appuser

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production 

# Default port that can be overridden at runtime
ARG PORT=5001
ENV PORT=$PORT
EXPOSE $PORT

# Use gunicorn for production with proper env var expansion
CMD gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 0 wsgi:application