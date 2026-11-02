"""Development settings for WorkFlow Enterprise."""

from .base import *  # noqa: F403

DEBUG = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# For local development convenience
ALLOWED_HOSTS = ["*"]

