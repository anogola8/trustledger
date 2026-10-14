"""TrustLedger settings. All secrets come from environment variables."""
import base64
import hashlib
import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(key, default=False):
    return os.environ.get(key, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(key, default=''):
    return [x.strip() for x in os.environ.get(key, default).split(',') if x.strip()]


DEBUG = env_bool('DEBUG', True)
SECRET_KEY = os.environ.get('SECRET_KEY') or ('dev-insecure-key-change-me' if DEBUG else '')
if not SECRET_KEY:
    raise ImproperlyConfigured('SECRET_KEY must be set when DEBUG is false.')

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
RENDER_HOST = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')
if RENDER_HOST:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_HOST}')
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000').rstrip('/')

# Key used to encrypt issuer private keys at rest (Fernet, 32 url-safe base64 bytes).
KEY_ENCRYPTION_KEY = os.environ.get('KEY_ENCRYPTION_KEY') or ''
if not KEY_ENCRYPTION_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('KEY_ENCRYPTION_KEY must be set when DEBUG is false.')
    KEY_ENCRYPTION_KEY = base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode()).digest()).decode()

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'rest_framework.authtoken',
    'core', 'accounts', 'workers', 'employers', 'attestations', 'verification',
    'trustscore', 'disputes', 'notifications', 'audit', 'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.SecurityHeadersMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
        'notifications.context_processors.unread_count',
    ]},
}]

DATABASES = {'default': dj_database_url.config(default=f'sqlite:///{BASE_DIR / "db.sqlite3"}', conn_max_age=60)}

AUTH_USER_MODEL = 'accounts.User'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
import sys

PASSWORD_HASHERS = ['django.contrib.auth.hashers.PBKDF2PasswordHasher']  # salted PBKDF2-SHA256
if 'test' in sys.argv or os.environ.get('FAST_HASHER'):
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']  # tests only: speed
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard:home'
LOGOUT_REDIRECT_URL = 'core:landing'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
MEDIA_URL = 'media/'
MEDIA_ROOT = Path(os.environ.get('MEDIA_ROOT', BASE_DIR / 'media'))
PRIVATE_ROOT = Path(os.environ.get('PRIVATE_ROOT', BASE_DIR / 'private'))
SERVE_MEDIA = env_bool('SERVE_MEDIA', True)
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.AnonRateThrottle', 'rest_framework.throttling.UserRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {'anon': '60/min', 'user': '300/min', 'verify': '60/min', 'auth': '10/min'},
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# Celery: if no broker is configured (e.g. Render free tier has no free worker) tasks run inline.
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', '')
CELERY_TASK_ALWAYS_EAGER = not CELERY_BROKER_URL
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_RESULT_BACKEND = None

CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}

# Security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_REFERRER_POLICY = 'same-origin'

LOGGING = {'version': 1, 'disable_existing_loggers': False,
           'handlers': {'console': {'class': 'logging.StreamHandler'}},
           'root': {'handlers': ['console'], 'level': os.environ.get('LOG_LEVEL', 'INFO')},
           'loggers': {'celery': {'level': 'WARNING'}}}

# ============ EMAIL (dev) ============
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@trustledger.local'

# ============ AUTH BACKENDS ============
AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailOrUsernameBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# ============ PRODUCTION HARDENING ============
# Everything below activates automatically when DEBUG=False
import os as _os

DEBUG = _os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true'

# SECRET_KEY — must come from env in production
if not DEBUG:
    SECRET_KEY = _os.environ.get('DJANGO_SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError('DJANGO_SECRET_KEY environment variable is required in production.')

# ALLOWED_HOSTS — from env, comma-separated
_allowed = _os.environ.get('DJANGO_ALLOWED_HOSTS', '')
if _allowed:
    ALLOWED_HOSTS = [h.strip() for h in _allowed.split(',') if h.strip()]
elif not DEBUG:
    ALLOWED_HOSTS = ['.onrender.com', 'localhost', '127.0.0.1']

# CSRF trusted origins for production
_csrf = _os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '')
if _csrf:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf.split(',') if o.strip()]
elif not DEBUG:
    CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com']

# Database — prefer DATABASE_URL if set
DATABASE_URL = _os.environ.get('DATABASE_URL')
if DATABASE_URL:
    import dj_database_url
    DATABASES['default'] = dj_database_url.parse(DATABASE_URL, conn_max_age=600)

# HTTPS + security headers
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'same-origin'

# Logging to stdout (Render captures this)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {module} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
}