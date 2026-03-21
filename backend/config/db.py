"""
File: db.py
Owner: BOTH CAN ADD
Created: 2026-03-21
Project: Learnova (eLearning Platform)
Purpose: Provide the shared PostgreSQL connection configuration for the backend.
What it is: A lightweight DB config module that reads DATABASE_URL/DB_* env vars and can open a psycopg connection when the driver is installed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DB_HOST = "localhost"
DEFAULT_DB_PORT = 5432
DEFAULT_DB_NAME = "learnova"
DEFAULT_DB_USER = "postgres"
ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT_DIR / ".env"


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    name: str
    user: str
    password: str
    url: str


def _load_local_env_file() -> None:
    if not ENV_FILE.exists():
        return

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _build_database_url(
    *,
    user: str,
    password: str,
    host: str,
    port: int,
    name: str,
) -> str:
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def get_database_settings() -> DatabaseSettings:
    _load_local_env_file()

    host = os.getenv("DB_HOST", DEFAULT_DB_HOST)
    port = int(os.getenv("DB_PORT", str(DEFAULT_DB_PORT)))
    name = os.getenv("DB_NAME", DEFAULT_DB_NAME)
    user = os.getenv("DB_USER", DEFAULT_DB_USER)
    password = os.getenv("DB_PASSWORD", "")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        database_url = _build_database_url(
            user=user,
            password=password,
            host=host,
            port=port,
            name=name,
        )

    return DatabaseSettings(
        host=host,
        port=port,
        name=name,
        user=user,
        password=password,
        url=database_url,
    )


def get_database_url() -> str:
    return get_database_settings().url


def connect():
    """
    Open a PostgreSQL connection when a psycopg driver is available.

    Supported drivers:
    - psycopg (v3)
    - psycopg2
    """

    settings = get_database_settings()

    try:
        import psycopg  # type: ignore

        return psycopg.connect(settings.url)
    except ImportError:
        try:
            import psycopg2  # type: ignore

            return psycopg2.connect(settings.url)
        except ImportError as exc:
            raise RuntimeError(
                "No PostgreSQL Python driver is installed. "
                "Install `psycopg[binary]` or `psycopg2-binary` to use backend/config/db.py."
            ) from exc


if __name__ == "__main__":
    settings = get_database_settings()
    masked_url = settings.url.replace(settings.password, "******") if settings.password else settings.url
    print(f"Database host: {settings.host}")
    print(f"Database name: {settings.name}")
    print(f"Database user: {settings.user}")
    print(f"Database url: {masked_url}")
