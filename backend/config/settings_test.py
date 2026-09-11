"""Settings used only by the test suite — swaps Postgres for local SQLite
so CI/dev boxes don't need a running Postgres instance just to run tests."""
from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # faster tests

# The test client always talks plain HTTP with no TLS-terminating proxy in
# front of it, so the production-only security headers added in
# settings.py (SECURE_SSL_REDIRECT etc.) must be off here, exactly as they
# would be in local dev behind a real load balancer that already redirects.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
