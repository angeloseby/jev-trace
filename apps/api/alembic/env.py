import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.core.config import settings
from app.db.base import Base
from app.db import models  # noqa: F401 ensure models imported

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
# Use sync URL for offline, async URL for online (psycopg2 is sync, asyncpg is async)
try:
    sync_url = settings.sync_database_url
    async_url = settings.database_url
except Exception:
    sync_url = "postgresql://jev:jev@localhost:5432/jevtrace"
    async_url = "postgresql+asyncpg://jev:jev@localhost:5432/jevtrace"
# alembic.ini offline uses sync_url; online async needs async_url
config.set_main_option("sqlalchemy.url", sync_url)
# store async url for online
config.set_main_option("sqlalchemy.async_url", async_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    # Build async engine from async_url explicitly
    from sqlalchemy.ext.asyncio import create_async_engine

    async_url = config.get_main_option("sqlalchemy.async_url")
    connectable = create_async_engine(async_url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
