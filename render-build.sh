#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Render Build Script — runs from the repository ROOT on every Render deploy
# ──────────────────────────────────────────────────────────────────────────────
set -e  # Exit immediately on any error

echo "========================================================================"
echo "  MediSkin AI — Render Build"
echo "========================================================================"

# ── Step 1: Install Python dependencies ──────────────────────────────────────
# requirements.txt lives at the repo root (one level above backend/)
echo ""
echo "[1/3] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt   # <-- root-level requirements.txt

# ── Step 2: Collect static files ──────────────────────────────────────────────
echo ""
echo "[2/3] Collecting static files..."
cd backend
export DJANGO_SETTINGS_MODULE=mediskin.settings_prod
python manage.py collectstatic --no-input

# ── Step 3: Run database migrations ───────────────────────────────────────────
echo ""
echo "[3/3] Running database migrations..."
python manage.py migrate

echo ""
echo "========================================================================"
echo "  Build complete!"
echo "========================================================================"
