# ─── MediSkin AI — Hugging Face Spaces Dockerfile ─────────────────────────────
# Docker SDK builds this image and runs it on port 7860 (HF Spaces default).

FROM python:3.10-slim

# ── OS dependencies ──────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# ── Create a non-root user (HF Spaces requirement) ──────────────────────────
RUN useradd -m -u 1000 appuser

# ── Working directory ────────────────────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ─────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Copy project source ─────────────────────────────────────────────────────
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# ── Set build-time Django settings ─────────────────────────────────────────
# collectstatic runs at build time with settings_hf.
# SECRET_KEY must be non-empty for Django to start; real value is injected
# at runtime via HF Spaces environment secrets.
ENV DJANGO_SETTINGS_MODULE=mediskin.settings_hf
ENV SECRET_KEY=build-time-placeholder-not-used-in-production

# ── Copy the startup script ─────────────────────────────────────────────────
COPY hf_start.sh .
RUN chmod +x hf_start.sh

# ── Create writable dirs for runtime ────────────────────────────────────────
RUN mkdir -p /app/backend/media /app/backend/temp_uploads /app/backend/staticfiles && \
    chown -R appuser:appuser /app

# ── Switch to non-root user ─────────────────────────────────────────────────
USER appuser

# ── Expose the HF Spaces port ───────────────────────────────────────────────
EXPOSE 7860

# ── Entrypoint ───────────────────────────────────────────────────────────────
CMD ["bash", "hf_start.sh"]
