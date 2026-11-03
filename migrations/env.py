"""Ambiente do Alembic.

As migrations são SQL explícito (`op.execute`), sem modelos do ORM: o schema fica legível e cada
restrição é revisável no próprio arquivo da migration.
"""

import os

from alembic import context
from sqlalchemy import create_engine, pool


def _url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("defina DATABASE_URL (postgresql+psycopg://...)")
    return url


def run_migrations_offline() -> None:
    context.configure(url=_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
