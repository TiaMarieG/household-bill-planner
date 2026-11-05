from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection

from app import models  # noqa: F401
from app.config import get_settings
from app.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit migration SQL to stdout without connecting to a database."""
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_with_connection(connection: Connection) -> None:
    """Run migrations on an already-open connection."""
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a connection passed in by tests, or the configured database."""
    connection = config.attributes.get("connection")
    if connection is not None:
        _run_with_connection(connection)
        return

    engine = create_engine(get_settings().database_url)
    with engine.connect() as connection:
        _run_with_connection(connection)
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
