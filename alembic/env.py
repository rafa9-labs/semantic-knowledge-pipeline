# ============================================================
# alembic/env.py — Alembic Migration Environment
# ============================================================
# This file tells Alembic HOW to connect to our database and
# WHERE to find our SQLAlchemy models for autogenerate support.
#
# KEY CONFIGURATION:
#   1. DATABASE_URL is read from .env (same as the rest of our app)
#   2. target_metadata = Base.metadata so Alembic can see ALL our ORM models
#   3. We import database.models so that Base.metadata knows about every table
#
# HOW AUTOGENERATE WORKS:
#   When you run `alembic revision --autogenerate`, Alembic:
#     1. Connects to PostgreSQL and reads the CURRENT schema
#     2. Reads target_metadata to find the DESIRED schema (our models)
#     3. Compares them and generates a migration script with the differences
#
# This means: if you add a new column to a model, Alembic detects it
# and writes the ALTER TABLE statement for you.
# ============================================================

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from dotenv import load_dotenv

load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL not set! Create a .env file with: "
        "DATABASE_URL=postgresql://user:pass@host:port/db"
    )
config.set_main_option("sqlalchemy.url", DATABASE_URL)

from database.connection import Base
import database.models

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Calls to context.execute() emit the given string to the script output.
    Useful for generating SQL scripts without connecting to a database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context.
    This is the normal mode — connects to the actual database.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
