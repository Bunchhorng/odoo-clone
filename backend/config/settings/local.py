import os

from .base import *  # noqa: F403

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
PERMISSION_MODE = os.environ.get("PERMISSION_MODE", "log")
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
