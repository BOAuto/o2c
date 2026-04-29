import logging
import os
import subprocess
from collections.abc import Generator
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

_DEFAULT_TEST_DB = "app_test"

# Ensure tests never run against a "real"/non-disposable DB unless explicitly opted-in.
# We do this before importing `app.core.config.settings`, because settings loads values
# from env_file at import time.
_current_env = os.environ.get("ENVIRONMENT", "local")
if _current_env != "production":
    current_postgres_db = (os.environ.get("POSTGRES_DB") or "").strip()
    if not current_postgres_db.endswith("_test"):
        os.environ["POSTGRES_DB"] = _DEFAULT_TEST_DB

from app.core.config import settings  # noqa: E402
from app.core.db import engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from tests.utils.user import authentication_token_from_email  # noqa: E402
from tests.utils.utils import get_superuser_token_headers  # noqa: E402

logger = logging.getLogger(__name__)


def _pytest_is_using_disposable_db() -> bool:
    """
    The tests currently mutate the DB (e.g. create random users).
    To avoid leaking that data into a "production-like" database, the default
    behavior is to require a disposable DB name ending in ``_test``.
    """
    if settings.ENVIRONMENT == "production":
        return False
    db_name = (settings.POSTGRES_DB or "").strip()
    if db_name.endswith("_test"):
        return True
    # Opt-in escape hatch for local experiments on a disposable DB.
    return os.environ.get("PYTEST_ALLOW_DB_MUTATION") == "1"


def _pytest_ensure_database_exists(db_name: str) -> None:
    """
    Create the disposable test database if it doesn't exist.

    We connect to the admin database (postgres) and create with AUTOCOMMIT, so
    this works even when the target DB is missing.
    """
    # psycopg needs a connection string or params; keep it explicit for clarity.
    with psycopg.connect(
        host=settings.POSTGRES_SERVER,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        dbname="postgres",
    ) as conn:
        conn.autocommit = True
        exists = conn.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_database WHERE datname = %(db)s)",
            {"db": db_name},
        ).fetchone()[0]
        if not exists:
            conn.execute(f'CREATE DATABASE "{db_name}"')


def _pytest_ensure_schema_initialized() -> None:
    """
    If someone points pytest at an empty disposable DB, `init_db()` (used by the
    tests) expects tables to exist. Detect that and run Alembic automatically
    for convenience.
    """
    _pytest_ensure_database_exists((settings.POSTGRES_DB or "").strip())

    backend_dir = Path(__file__).resolve().parents[1]
    # Always upgrade to head for disposable DBs to avoid "app_test" drifting
    # between code changes.
    subprocess.run(["alembic", "upgrade", "head"], cwd=backend_dir, check=True)


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    if not _pytest_is_using_disposable_db():
        db_name = (settings.POSTGRES_DB or "").strip()
        raise RuntimeError(
            "Refusing to run pytest against a non-disposable database.\n\n"
            f"Detected POSTGRES_DB={db_name!r}.\n"
            "Use POSTGRES_DB=..._test (preferred) or set "
            "PYTEST_ALLOW_DB_MUTATION=1 (only for disposable DBs).\n"
            "This prevents dummy test users from leaking into your real DB."
        )

    _pytest_ensure_schema_initialized()
    with Session(engine) as session:
        init_db(session)
        yield session
        # If we got here, we are already on a disposable DB, so cleanup is safe
        # and keeps subsequent test runs tidy.
        session.execute(delete(User))
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
