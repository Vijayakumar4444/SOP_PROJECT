from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]


def load_project_env(root: Path = ROOT) -> bool:
    """Load project-local environment variables without overriding the shell."""
    return load_dotenv(root / ".env", override=False)


def get_database_url() -> str:
    load_project_env()
    return os.getenv("DATABASE_URL", "")


def check_database_health(conninfo: str | None = None, timeout_seconds: int = 15) -> dict[str, Any]:
    load_project_env()
    database_url = conninfo if conninfo is not None else get_database_url()
    if not database_url:
        return {
            "connected": False,
            "status": "not_configured",
            "detail": "DATABASE_URL is not configured.",
        }

    try:
        with psycopg.connect(database_url, connect_timeout=timeout_seconds) as conn:
            with conn.cursor() as cur:
                cur.execute("select current_database(), current_user, version(), now()")
                database, user, version, server_time = cur.fetchone()
    except Exception as exc:
        return {
            "connected": False,
            "status": "error",
            "error_type": exc.__class__.__name__,
            "detail": str(exc),
        }

    return {
        "connected": True,
        "status": "ok",
        "database": database,
        "user": user,
        "server": version.split(",")[0],
        "server_time": server_time.isoformat(),
    }
