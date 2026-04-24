#!/usr/bin/env bash
# ─── MediSkin AI — Hugging Face Spaces Startup Script ─────────────────────────
# Downloads the ML model from HF Hub, runs migrations, collects static files,
# then starts gunicorn on port 7860.

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          MediSkin AI — Hugging Face Spaces Startup          ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# ── 1. Download model from Hugging Face Hub ──────────────────────────────────
MODEL_DIR="/app/backend/ml/models"
MODEL_FILE="$MODEL_DIR/skin_disease_classifier.h5"

if [ ! -f "$MODEL_FILE" ]; then
    echo "[*] Downloading model from Hugging Face Hub..."
    python -c "
from huggingface_hub import hf_hub_download
import os

repo_id = os.environ.get('HF_MODEL_REPO', 'shanmugapriya-mediskin/skin-disease-model')
filename = 'skin_disease_classifier.h5'
local_dir = '/app/backend/ml/models'

print(f'  Repo:  {repo_id}')
print(f'  File:  {filename}')

path = hf_hub_download(
    repo_id=repo_id,
    filename=filename,
    local_dir=local_dir,
    local_dir_use_symlinks=False,
)
print(f'  Saved: {path}')
print('[+] Model download complete!')
"
else
    echo "[*] Model already exists, skipping download."
fi

# ── 2. Django setup ──────────────────────────────────────────────────────────
cd /app/backend

# Use HF-specific settings throughout
export DJANGO_SETTINGS_MODULE="mediskin.settings_hf"

# Ensure /data directory exists for SQLite + media (HF persistent volume)
mkdir -p /data/media

echo "[*] Running migrations..."
python manage.py migrate --noinput 2>&1

echo "[*] Collecting static files..."
python manage.py collectstatic --noinput 2>&1

# ── 3. Create demo superuser (if not exists) ────────────────────────────────
echo "[*] Creating demo user..."
python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mediskin.settings_hf')
django.setup()
from django.contrib.auth.models import User
if not User.objects.filter(username='demo').exists():
    User.objects.create_superuser('demo', 'demo@mediskin.ai', 'demo123')
    print('  Created demo user (demo / demo123)')
else:
    print('  Demo user already exists.')
"

# ── 4. Start Gunicorn ────────────────────────────────────────────────────────
echo ""
echo "[*] Starting Gunicorn on port 7860..."
echo "══════════════════════════════════════════════════════════════"

exec gunicorn mediskin.wsgi:application \
    --bind 0.0.0.0:7860 \
    --workers 2 \
    --timeout 300 \
    --access-logfile - \
    --error-logfile -
