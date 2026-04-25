"""
Hugging Face Spaces settings for MediSkin AI.
Extends base settings.py — designed for Docker SDK on HF Spaces.

KEY DIFFERENCES vs settings_prod.py (Render):
  - SQLite at /data/db.sqlite3  (HF Spaces persistent volume)
  - Media/uploads at /data/media/
  - SECURE_SSL_REDIRECT = False  (HF handles HTTPS termination)
  - Port 7860 (HF Spaces Docker requirement)
  - ALLOWED_HOSTS includes *.hf.space wildcard
  - Optional: model downloaded from HF Hub at startup
"""

from .settings import *
import os
from pathlib import Path

# ─── Core Security ────────────────────────────────────────────────────────────
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

SECRET_KEY = os.environ.get('SECRET_KEY', 'hf-spaces-insecure-default-change-this-in-settings')

# ─── Allowed Hosts ────────────────────────────────────────────────────────────
ALLOWED_HOSTS = [
    '.hf.space',            # All HF Spaces subdomains (wildcard)
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
]
# Also allow anything set in env (for custom domains)
_extra_hosts = os.environ.get('ALLOWED_HOSTS', '')
if _extra_hosts:
    ALLOWED_HOSTS += [h.strip() for h in _extra_hosts.split(',') if h.strip()]

# ─── HTTPS / SSL ──────────────────────────────────────────────────────────────
# HF Spaces terminates SSL at their load balancer — Django must NOT redirect
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False   # cookies work over HTTP within HF container
CSRF_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
# Disable HSTS on HF (they manage it)
SECURE_HSTS_SECONDS = 0

# Use the forwarded-for header from HF's reverse proxy
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ─── CSRF ─────────────────────────────────────────────────────────────────────
CSRF_TRUSTED_ORIGINS = [
    'https://*.hf.space',
    'http://localhost:7860',
]
_extra_csrf = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if _extra_csrf:
    CSRF_TRUSTED_ORIGINS += [o.strip() for o in _extra_csrf.split(',') if o.strip()]

# ─── Database ─────────────────────────────────────────────────────────────────
# Use SQLite stored in HF Spaces persistent volume (/data)
# The /data directory persists across container restarts on HF Spaces.
# Guard mkdir: during `docker build` collectstatic, /data is not mounted yet.
_DATA_DIR = Path('/data')
try:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
except (PermissionError, OSError):
    import tempfile as _tmp
    _DATA_DIR = Path(_tmp.gettempdir()) / 'mediskin_data'
    _DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': _DATA_DIR / 'db.sqlite3',
    }
}

# ─── Media Files (uploads) ────────────────────────────────────────────────────
MEDIA_ROOT = _DATA_DIR / 'media'
try:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
except (PermissionError, OSError):
    pass
MEDIA_URL = '/media/'

# ─── Static Files ─────────────────────────────────────────────────────────────
# BASE_DIR is backend/ from settings.py — collect into backend/staticfiles/
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'
STATICFILES_DIRS = [FRONTEND_DIR / 'static'] if (FRONTEND_DIR / 'static').exists() else []

# WhiteNoise serves static files directly from gunicorn (no Nginx needed)
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ─── CORS ─────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    'https://*.hf.space',
]
_extra_cors = os.environ.get('CORS_ALLOWED_ORIGINS', '')
if _extra_cors:
    CORS_ALLOWED_ORIGINS += [o.strip() for o in _extra_cors.split(',') if o.strip()]
CORS_ALLOW_CREDENTIALS = True

# ─── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', f'MediSkin AI <{EMAIL_HOST_USER}>')

# ─── Google OAuth ─────────────────────────────────────────────────────────────
# Only configure APP credentials when both env vars are present.
# If missing, allauth shows a proper error instead of crashing with 500.
_GOOGLE_CLIENT_ID     = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
_GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()

if _GOOGLE_CLIENT_ID and _GOOGLE_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS = {
        'google': {
            'APP': {
                'client_id': _GOOGLE_CLIENT_ID,
                'secret':    _GOOGLE_CLIENT_SECRET,
                'key':       '',
            },
            'SCOPE':       ['profile', 'email'],
            'AUTH_PARAMS': {'access_type': 'online'},
        }
    }
    print(f"[settings_hf] Google OAuth: configured (client_id={_GOOGLE_CLIENT_ID[:20]}...)")
else:
    SOCIALACCOUNT_PROVIDERS = {
        'google': {
            'SCOPE':       ['profile', 'email'],
            'AUTH_PARAMS': {'access_type': 'online'},
        }
    }
    print("[settings_hf] Google OAuth: GOOGLE_CLIENT_ID/SECRET not set — button will be disabled.")

SITE_ID = int(os.environ.get('SITE_ID', '1'))

# ─── API Base URL ─────────────────────────────────────────────────────────────
# Inject into HTML templates so JS knows the backend URL
API_BASE_URL = os.environ.get('API_BASE_URL', '')

# ─── Google Maps ──────────────────────────────────────────────────────────────
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')

# ─── Logging ──────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}
