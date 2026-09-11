"""
Django settings for the Nagrik Setu platform.
Secrets are pulled from HashiCorp Vault at boot (see core/vault_client.py);
env vars are the local-dev fallback.
"""
import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# --- Vault-backed secrets (falls back to env vars if Vault is unreachable) ---
from core.vault_client import get_secret  # noqa: E402

DEBUG = env.bool("DJANGO_DEBUG", default=False)
# The "*******-local-dev-only" fallback is intentionally obviously-fake so
# it can never be mistaken for a real value; it only applies when DEBUG is
# on. Any non-debug deployment must supply a real key via Vault/.env or
# fail loudly rather than silently run with a guessable secret key.
_SECRET_KEY_FALLBACK = "*******-local-dev-only" if DEBUG else None
SECRET_KEY = get_secret(
    "django_secret_key", default=env("DJANGO_SECRET_KEY", default=_SECRET_KEY_FALLBACK)
)
if not SECRET_KEY:
    raise RuntimeError(
        "DJANGO_SECRET_KEY is not set. Provide it via Vault (django_secret_key) or the "
        "DJANGO_SECRET_KEY env var — refusing to start without one outside DEBUG mode."
    )
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "apps.issues",
    "apps.accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Database: PostgreSQL ---
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": get_secret("postgres_db", default=env("POSTGRES_DB", default="nagrik_setu")),
        "USER": get_secret("postgres_user", default=env("POSTGRES_USER", default="nagrik_setu")),
        "PASSWORD": get_secret("postgres_password", default=env("POSTGRES_PASSWORD", default="")),
        "HOST": env("POSTGRES_HOST", default="postgres"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
    }
}

# --- Cache: Redis ---
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://redis:6379/0"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "300/min",
        # Tighter, separate scope for upvote so a script can't hammer a
        # single issue's vote count even from an authenticated account;
        # combined with the per-IP dedupe cache check in views.py.
        "upvote": "10/min",
    },
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
}

from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:5173"])

# --- AWS ---
AWS_REGION = env("AWS_REGION", default="ap-south-1")
AWS_STORAGE_BUCKET_NAME = env("AWS_S3_BUCKET", default="nagrik-setu-uploads")
AWS_DYNAMODB_TABLE = env("AWS_DYNAMODB_TABLE", default="nagrik-setu-events")

# --- Uploaded-photo verification (see apps/issues/models.py, views.py,
# backend/lambda/upload_validation/) ---
# Off by default so local/demo setups without the Lambda deployed still
# show photos immediately; turn on in any real deployment.
REQUIRE_ATTACHMENT_VERIFICATION = env.bool("REQUIRE_ATTACHMENT_VERIFICATION", default=False)

# Shared secret the upload-validation Lambda presents when calling back to
# /api/v1/internal/mark-attachment-verified/ (core/internal_views.py).
# Sourced from Vault in real deployments, same pattern as every other
# secret in this file.
INTERNAL_SERVICE_TOKEN = get_secret(
    "internal_service_token", default=env("INTERNAL_SERVICE_TOKEN", default="")
)

# --- Agentic AI auto-triage (see core/ai_triage.py) ---
# Off by default: enabling it means calling an external LLM API with
# citizen-submitted text, which a deployer should opt into deliberately
# (cost, data-handling policy, provider choice) rather than get by default.
ENABLE_AI_TRIAGE = env.bool("ENABLE_AI_TRIAGE", default=False)
ANTHROPIC_API_KEY = get_secret(
    "anthropic_api_key", default=env("ANTHROPIC_API_KEY", default="")
)

# --- Security headers ---
# Only enforced when DEBUG is off, so local `docker-compose up` over plain
# HTTP still works without fighting HSTS/redirect loops.
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Custom error handlers (see core/error_views.py + templates/errors/) ---
handler400 = "core.error_views.handler400"
handler403 = "core.error_views.handler403"
handler404 = "core.error_views.handler404"
handler500 = "core.error_views.handler500"
