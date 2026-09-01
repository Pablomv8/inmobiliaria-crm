import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ImproperlyConfigured(f"{name} debe ser un valor booleano.")


def env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Falta la variable obligatoria {name}.")
    return value


def database_from_url(url, base_dir):
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme in {"postgres", "postgresql", "pgsql"}:
        options = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
        config = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed.path.lstrip("/")),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or "5432"),
            "CONN_MAX_AGE": int(options.pop("conn_max_age", "60")),
            "CONN_HEALTH_CHECKS": True,
        }
        sslmode = options.pop("sslmode", "")
        if sslmode:
            config["OPTIONS"] = {"sslmode": sslmode, **options}
        elif options:
            config["OPTIONS"] = options
        return config
    if scheme == "sqlite":
        raw_path = unquote(parsed.path)
        database_path = Path(raw_path)
        if not database_path.is_absolute():
            database_path = Path(base_dir) / raw_path.lstrip("/")
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": database_path,
        }
    raise ImproperlyConfigured(
        "DATABASE_URL debe utilizar postgresql:// o sqlite://."
    )
