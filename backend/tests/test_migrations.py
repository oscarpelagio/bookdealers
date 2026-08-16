"""Tests de migracions Alembic.

Verifiquen que la migració és la font de veritat de l'esquema:
- `alembic upgrade head` sobre una BD buida funciona.
- `alembic revision --autogenerate` no detecta canvis inesperats (sense drift).
- `alembic downgrade base` + `alembic upgrade head` tornen a l'estat inicial.

S'executen contra una base de dades dedicada (`MIGRATION_DB_NAME`) per no
interferir amb la base de dades de tests (`TEST_DATABASE_NAME`).
"""

import os
import subprocess
import sys
from pathlib import Path

import psycopg2
import psycopg2.extensions
import pytest

from app.core.config import settings

BACKEND_DIR = Path(__file__).resolve().parents[1]
MIGRATION_DB_NAME = "bookdealers_migrations_test"

EXPECTED_TABLES = {
    "book_establishment",
    "books",
    "catalogs",
    "email_verification_tokens",
    "establishments",
    "password_reset_tokens",
    "refresh_tokens",
    "roles",
    "search_cache",
    "search_query",
    "user_roles",
    "users",
}


def _connect(dbname: str):
    return psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        dbname=dbname,
        connect_timeout=5,
    )


def _run_alembic(*args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["POSTGRES_DB"] = MIGRATION_DB_NAME
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def _public_tables() -> set[str]:
    conn = _connect(MIGRATION_DB_NAME)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
            return {row[0] for row in cur.fetchall()}
    finally:
        conn.close()


def _newest_revision_file() -> Path:
    versions = BACKEND_DIR / "alembic" / "versions"
    files = [p for p in versions.glob("*.py") if not p.name.startswith("__")]
    return max(files, key=lambda p: p.stat().st_mtime)


@pytest.fixture(scope="module")
def migration_db():
    conn = _connect("postgres")
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP DATABASE IF EXISTS "{MIGRATION_DB_NAME}"')
            cur.execute(f'CREATE DATABASE "{MIGRATION_DB_NAME}"')
    finally:
        conn.close()
    yield
    conn = _connect("postgres")
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP DATABASE IF EXISTS "{MIGRATION_DB_NAME}"')
    finally:
        conn.close()


def test_upgrade_head_creates_full_schema(migration_db) -> None:
    result = _run_alembic("upgrade", "head")
    assert result.returncode == 0, result.stderr

    tables = _public_tables()
    assert EXPECTED_TABLES <= tables, (
        f"Falten taules després d'alembic upgrade head: "
        f"{EXPECTED_TABLES - tables}"
    )
    assert "alembic_version" in tables


def test_no_schema_drift(migration_db) -> None:
    result = _run_alembic("upgrade", "head")
    assert result.returncode == 0, result.stderr

    result = _run_alembic("revision", "--autogenerate", "-m", "drift check")
    assert result.returncode == 0, result.stderr
    generated = _newest_revision_file()
    try:
        content = generated.read_text()
        assert "op." not in content and "    pass" in content, (
            "alembic revision --autogenerate ha detectat canvis inesperats "
            f"(fitxer generat: {generated.name}). Els models i les "
            "migracions no coincideixen: genera una migració nova amb "
            "'make new-migration'."
        )
    finally:
        generated.unlink()


def test_downgrade_base_and_reupgrade(migration_db) -> None:
    result = _run_alembic("upgrade", "head")
    assert result.returncode == 0, result.stderr

    result = _run_alembic("downgrade", "base")
    assert result.returncode == 0, result.stderr
    assert _public_tables() == {"alembic_version"}

    result = _run_alembic("upgrade", "head")
    assert result.returncode == 0, result.stderr
    assert EXPECTED_TABLES <= _public_tables()
