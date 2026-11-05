from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.clock import get_today
from app.config import get_settings
from app.db import get_session
from app.main import create_app

TEST_TODAY = date(2026, 11, 30)
ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def _run_migrations(engine: Engine, revision: str, upgrade: bool) -> None:
    """Run Alembic up or down on the given engine instead of the app's configured database."""
    config = Config(str(ALEMBIC_INI))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        if upgrade:
            command.upgrade(config, revision)
        else:
            command.downgrade(config, revision)


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    """Engine for the test database, rebuilt from scratch with migrations once per test run."""
    url = get_settings().test_database_url
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")

    engine = create_engine(url)
    try:
        engine.connect().close()
    except OperationalError:
        pytest.skip("test database is unreachable; start it with `docker compose up -d db`")

    _run_migrations(engine, "base", upgrade=False)
    _run_migrations(engine, "head", upgrade=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    """Session whose changes, including commits, are rolled back after each test."""
    with db_engine.connect() as connection:
        transaction = connection.begin()
        session = Session(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """API client whose requests all use the rolled-back test session."""
    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_today] = lambda: TEST_TODAY
    with TestClient(app) as test_client:
        yield test_client
