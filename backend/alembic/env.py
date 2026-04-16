import asyncio
import os

from alembic import context
from geoalchemy2 import alembic_helpers
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.db import Base
from app.models import Station, Reservation  # noqa: F401 – register models

config = context.config

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://mibici:mibici@localhost:5432/mibici",
)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

target_metadata = Base.metadata


EXCLUDE_SCHEMAS = {"tiger", "tiger_data", "topology"}


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and hasattr(object, "schema") and object.schema in EXCLUDE_SCHEMAS:
        return False
    if reflected and type_ == "table" and name not in Base.metadata.tables:
        return False
    return alembic_helpers.include_object(object, name, type_, reflected, compare_to)


def render_item(type_, obj, autogen_context):
    return alembic_helpers.render_item(type_, obj, autogen_context)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        process_revision_directives=alembic_helpers.writer,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        process_revision_directives=alembic_helpers.writer,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
