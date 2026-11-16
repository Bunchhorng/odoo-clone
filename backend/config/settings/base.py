import os
from pathlib import Path
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY or SECRET_KEY.startswith("REPLACE_WITH_"):
    raise ImproperlyConfigured("Set a random DJANGO_SECRET_KEY in the root .env file.")

DEBUG = False
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.accounts.apps.AccountsConfig",
    "apps.companies.apps.CompaniesConfig",
    "apps.core.apps.CoreConfig",
    "apps.business.apps.BusinessConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASE_NAME = os.environ.get("MYSQL_DATABASE", "kerp")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": DATABASE_NAME,
        "USER": os.environ.get("MYSQL_USER", "kerp"),
        "PASSWORD": os.environ.get("MYSQL_PASSWORD", ""),
        "HOST": os.environ.get("MYSQL_HOST", "db"),
        "PORT": os.environ.get("MYSQL_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "TEST": {"NAME": f"test_{DATABASE_NAME}"},
    }
}

AUTH_USER_MODEL = "accounts.User"
CSRF_FAILURE_VIEW = "apps.core.api.csrf_failure"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Bangkok"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Server-owned origin prevents reset-link host-header poisoning.
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5175").rstrip("/")
_frontend = urlsplit(FRONTEND_ORIGIN)
if (_frontend.scheme not in ("http", "https") or not _frontend.netloc or
        _frontend.username or _frontend.password or _frontend.path or _frontend.query or _frontend.fragment):
    raise ImproperlyConfigured("FRONTEND_ORIGIN must be a single http(s) origin without a path or credentials.")
SESSION_COOKIE_AGE = int(os.environ.get("SESSION_COOKIE_AGE", "28800"))
PASSWORD_RESET_TIMEOUT = 1800
AUTH_RATE_WINDOW_SECONDS = int(os.environ.get("AUTH_RATE_WINDOW_SECONDS", "900"))
AUTH_LOGIN_IDENTITY_LIMIT = int(os.environ.get("AUTH_LOGIN_IDENTITY_LIMIT", "10"))
AUTH_LOGIN_IP_LIMIT = int(os.environ.get("AUTH_LOGIN_IP_LIMIT", "100"))
AUTH_REGISTER_IDENTITY_LIMIT = int(os.environ.get("AUTH_REGISTER_IDENTITY_LIMIT", "3"))
AUTH_REGISTER_IP_LIMIT = int(os.environ.get("AUTH_REGISTER_IP_LIMIT", "20"))
AUTH_RESET_IDENTITY_LIMIT = int(os.environ.get("AUTH_RESET_IDENTITY_LIMIT", "3"))
AUTH_RESET_IP_LIMIT = int(os.environ.get("AUTH_RESET_IP_LIMIT", "30"))
AUTH_RESET_QUEUE_TTL = 900
for _setting in ("SESSION_COOKIE_AGE", "AUTH_RATE_WINDOW_SECONDS", "AUTH_LOGIN_IDENTITY_LIMIT",
                 "AUTH_LOGIN_IP_LIMIT", "AUTH_REGISTER_IDENTITY_LIMIT", "AUTH_REGISTER_IP_LIMIT",
                 "AUTH_RESET_IDENTITY_LIMIT", "AUTH_RESET_IP_LIMIT"):
    if globals()[_setting] < 1:
        raise ImproperlyConfigured(f"{_setting} must be positive.")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "KERP <noreply@kerp.local>")
EMAIL_TIMEOUT = 5
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"
