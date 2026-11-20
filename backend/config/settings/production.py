"""Secure runtime settings for Render with a Neon PostgreSQL database."""
import os
from urllib.parse import parse_qsl, unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403


def _required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Set {name} for the production deployment.")
    return value


def _positive_int(name, default):
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} must be an integer.") from exc
    if value < 0:
        raise ImproperlyConfigured(f"{name} cannot be negative.")
    return value


def _origins(name):
    values = []
    for value in _required(name).split(","):
        origin = value.strip().rstrip("/")
        parsed = urlsplit(origin)
        if (parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password
                or parsed.path or parsed.query or parsed.fragment):
            raise ImproperlyConfigured(f"{name} must contain comma-separated HTTPS origins only.")
        if origin not in values:
            values.append(origin)
    return values


def _neon_database():
    database_url = _required("DATABASE_URL")
    try:
        parsed = urlsplit(database_url)
        port = parsed.port or 5432
    except ValueError as exc:
        raise ImproperlyConfigured("DATABASE_URL has an invalid PostgreSQL port.") from exc
    database_name = unquote(parsed.path.lstrip("/"))
    if (parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname
            or not database_name or parsed.fragment):
        raise ImproperlyConfigured("DATABASE_URL must be a PostgreSQL connection string.")
    options = dict(parse_qsl(parsed.query, keep_blank_values=True))
    options.setdefault("sslmode", "require")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": database_name,
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname,
        "PORT": str(port),
        "CONN_MAX_AGE": _positive_int("DATABASE_CONN_MAX_AGE", 60),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": options,
    }


# Render reaches Django through its trusted HTTPS proxy. Do not use these settings
# for a server that lets clients connect directly to Django.
DEBUG = False
DATABASES["default"] = _neon_database()  # noqa: F405

ALLOWED_HOSTS = [host.strip() for host in _required("DJANGO_ALLOWED_HOSTS").split(",") if host.strip()]
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must list explicit API hosts.")

_frontend = urlsplit(FRONTEND_ORIGIN)  # noqa: F405
if _frontend.scheme != "https":
    raise ImproperlyConfigured("FRONTEND_ORIGIN must be an HTTPS origin in production.")

CORS_ALLOWED_ORIGINS = _origins("DJANGO_CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = _origins("DJANGO_CSRF_TRUSTED_ORIGINS")
if FRONTEND_ORIGIN not in CORS_ALLOWED_ORIGINS or FRONTEND_ORIGIN not in CSRF_TRUSTED_ORIGINS:  # noqa: F405
    raise ImproperlyConfigured("Include FRONTEND_ORIGIN in both CORS and CSRF trusted origins.")
CORS_ALLOW_CREDENTIALS = True
CORS_URLS_REGEX = r"^/api/.*$"

_cookie_domain = _required("DJANGO_COOKIE_DOMAIN").lower()
if not _cookie_domain.startswith(".") or _cookie_domain.count(".") < 2:
    raise ImproperlyConfigured("DJANGO_COOKIE_DOMAIN must be a shared parent domain, such as .example.com.")
_cookie_parent = _cookie_domain[1:]
if not _frontend.hostname or not (_frontend.hostname == _cookie_parent or _frontend.hostname.endswith(_cookie_domain)):
    raise ImproperlyConfigured("DJANGO_COOKIE_DOMAIN must cover FRONTEND_ORIGIN.")
if not any(host.lower() == _cookie_parent or host.lower().endswith(_cookie_domain) for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured("DJANGO_COOKIE_DOMAIN must cover an allowed API host.")

SESSION_COOKIE_DOMAIN = _cookie_domain
CSRF_COOKIE_DOMAIN = _cookie_domain
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = _positive_int("DJANGO_SECURE_HSTS_SECONDS", 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
