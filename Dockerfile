# ─────────────────────────────────────────────────────────────────────────────
# MediSkin AI — Dockerfile for Hugging Face Spaces (Docker SDK)
#
# HF Spaces requirements:
#   - App MUST listen on port 7860
#   - Persistent storage is mounted at /data
#   - Secrets are injected as environment variables via Space settings
#
# Build stages:
#   1. Install Python deps (cached layer)
#   2. Copy source code
#   3. Collect static files at BUILD time (fast startup)
#   4. At RUNTIME: migrate DB + start Gunicorn
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# ── System packages ───────────────────────────────────────────────────────────
# libpq-dev   : PostgreSQL client headers (psycopg2-binary technically doesn't
#               need them but keeps things consistent)
# libgomp1    : OpenMP required by TensorFlow
# gcc / g++   : Compile some Python packages from source if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        libgomp1 \
        gcc \
        g++ \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies (install first — Docker layer cache) ──────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Copy application source ───────────────────────────────────────────────────
COPY . .

# ── Collect static files at build time ────────────────────────────────────────
# This bakes WhiteNoise's compressed/hashed files into the image so startup
# is instant. Uses a dummy SECRET_KEY just for collectstatic.
ENV DJANGO_SETTINGS_MODULE=mediskin.settings_hf
RUN cd backend && \
    SECRET_KEY="build-time-static-collection-key-not-used-at-runtime" \
    ALLOWED_HOSTS="localhost" \
    python manage.py collectstatic --no-input 2>&1 || \
    echo "WARNING: collectstatic had warnings — continuing build"

# ── Make startup script executable ────────────────────────────────────────────
RUN chmod +x /app/hf_startup.sh

# ── Create /data directory structure (overridden by HF persistent volume) ─────
RUN mkdir -p /data/media /data/uploads

# ── Non-root user (HF Spaces security requirement) ────────────────────────────
# HF Spaces runs containers as user ID 1000
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /data
USER appuser

# ── Port (MUST be 7860 for HF Spaces Docker SDK) ─────────────────────────────
EXPOSE 7860

# ── Environment defaults (overridden by HF Space secrets) ─────────────────────
ENV DJANGO_SETTINGS_MODULE=mediskin.settings_hf
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=7860

# ── Startup ───────────────────────────────────────────────────────────────────
# hf_startup.sh: downloads ML model (if HF_MODEL_REPO set), migrates DB,
# then launches Gunicorn on 0.0.0.0:7860
CMD ["/app/hf_startup.sh"]
