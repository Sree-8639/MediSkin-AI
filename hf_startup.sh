#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# HF Spaces Startup Script
# Runs EVERY TIME the container starts (not just build time).
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo "========================================================"
echo "  MediSkin AI — Hugging Face Spaces Startup"
echo "========================================================"

# ── Ensure /data dirs exist (persistent volume) ──────────────────────────────
mkdir -p /data/media    # uploaded profile pictures & reports
mkdir -p /data/uploads  # temporary prediction uploads

# ── Download ML model if not already present ─────────────────────────────────
MODEL_PATH="/app/backend/ml/models/skin_disease_classifier.keras"
if [ ! -f "$MODEL_PATH" ]; then
    echo "[model] Model not found at $MODEL_PATH"
    if [ -n "$HF_MODEL_REPO" ]; then
        echo "[model] Downloading from HF Hub: $HF_MODEL_REPO ..."
        python -c "
from huggingface_hub import hf_hub_download
import os, shutil
repo_id = os.environ['HF_MODEL_REPO']
token   = os.environ.get('HF_TOKEN', None)
path    = hf_hub_download(repo_id=repo_id,
                           filename='skin_disease_classifier.keras',
                           token=token,
                           local_dir='/tmp/model')
dest = '/app/backend/ml/models/skin_disease_classifier.keras'
os.makedirs(os.path.dirname(dest), exist_ok=True)
shutil.copy(path, dest)
print(f'[model] Downloaded and placed at {dest}')
"
    else
        echo "[model] WARNING: HF_MODEL_REPO not set — ML diagnostics will be disabled."
        echo "[model] Set HF_MODEL_REPO=username/repo-name in Space secrets to enable AI."
    fi
else
    echo "[model] Model found at $MODEL_PATH — skipping download."
fi

# ── Apply database migrations ─────────────────────────────────────────────────
echo ""
echo "[db] Running migrations..."
cd /app/backend
python manage.py migrate --noinput

echo ""
echo "[startup] Starting Gunicorn on port 7860..."
echo "========================================================"

# ── Start Gunicorn on port 7860 (required by HF Spaces) ──────────────────────
exec gunicorn mediskin.wsgi:application \
    --bind 0.0.0.0:7860 \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
