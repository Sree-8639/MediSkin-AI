"""
Production settings for MediSkin on Render and Vercel.
Extends base settings.py with production overrides.
"""

from .settings import *
import os

# ─── Production Security ──────────────────────────────────────────────────────
DEBUG = False

# Get from environment or fail loudly in production
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required in production!")

# Parse ALLOWED_HOSTS from environment
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ValueError("ALLOWED_HOSTS environment variable is required in production!")

ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS if h.strip()]

# Security headers for HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# ── CSRF Trusted Origins ─────────────────────────────────────────────────────
# Required so POST/PUT/PATCH requests originating from Vercel or any custom
# domain pass Django's CSRF middleware check (Django 4+ requires this for
# cross-origin requests with cookies/credentials).
# Wildcards supported from Django 4.0+
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',   # The backend itself (Render)
    'https://*.vercel.app',     # The frontend (Vercel preview + production)
]
# Append any additional origins from the environment variable
_extra_csrf = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if _extra_csrf:
    CSRF_TRUSTED_ORIGINS += [o.strip() for o in _extra_csrf.split(',') if o.strip()]

# ─── Database Configuration ───────────────────────────────────────────────────
# Use PostgreSQL on Render (DATABASE_URL is set by Render automatically)
if os.environ.get('DATABASE_URL'):
    import dj_database_url
    DATABASES['default'] = dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
else:
    # Fallback to SQLite if DATABASE_URL not set (local testing)
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }

# ─── Static Files & Storage ───────────────────────────────────────────────────
# BASE_DIR is backend/ — so staticfiles/ is created inside backend/staticfiles/
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'
# Only add STATICFILES_DIRS entries that actually exist (avoids collectstatic errors)
STATICFILES_DIRS = [FRONTEND_DIR / 'static'] if (FRONTEND_DIR / 'static').exists() else []

# Use whitenoise for serving static files in production
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ─── CORS Configuration ───────────────────────────────────────────────────────
# Parse from environment: CORS_ALLOWED_ORIGINS=https://example.vercel.app,https://www.example.com
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ALLOWED_ORIGINS if origin.strip()]

# Specific CORS settings
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ─── Logging Configuration ────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
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

# ─── Email Configuration for Production ────────────────────────────────────────
# Uses Gmail SMTP by default. Configure via environment variables.
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', f'MediSkin AI <{EMAIL_HOST_USER}>')

# ─── Google OAuth (allauth) ────────────────────────────────────────────────────
# Configure allowed redirect URIs for Google OAuth
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
    }
}

# ─── Site Framework (allauth) ─────────────────────────────────────────────────
# Update SITE_ID based on environment
# SITE_ID = 1 assumes you've created a Site with domain matching ALLOWED_HOSTS[0]
SITE_ID = int(os.environ.get('SITE_ID', '1'))
