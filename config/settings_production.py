import os

from django.core.exceptions import ImproperlyConfigured

from .environment import database_from_url, env_bool, env_list, required_env
from .settings import *  # noqa: F403


DEBUG = False
SECRET_KEY = required_env("DJANGO_SECRET_KEY")
if SECRET_KEY.startswith("development-") or len(SECRET_KEY) < 50:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY debe ser una clave de producción aleatoria de al menos 50 caracteres."
    )

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS es obligatorio en producción.")

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
DATABASE_URL = required_env("DATABASE_URL")
DATABASES = {"default": database_from_url(DATABASE_URL, BASE_DIR)}  # noqa: F405

SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_HSTS_INCLUDE_SUBDOMAINS", True)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD", True)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_AGE = int(os.getenv("DJANGO_SESSION_COOKIE_AGE", "28800"))
SESSION_EXPIRE_AT_BROWSER_CLOSE = env_bool("DJANGO_SESSION_EXPIRE_AT_BROWSER_CLOSE", True)
SESSION_SAVE_EVERY_REQUEST = True

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}

SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()
if SENTRY_DSN:
    try:
        import sentry_sdk
    except ImportError as exc:
        raise ImproperlyConfigured(
            "Instala sentry-sdk para utilizar SENTRY_DSN."
        ) from exc
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        send_default_pii=False,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        release=os.getenv("APP_RELEASE") or None,
    )
