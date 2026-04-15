# ============================================================
# database/connection.py — SQLAlchemy Engine & Session Factory
# ============================================================
# This module is responsible for CONNECTING to our PostgreSQL database.
# It provides two key things:
#   1. An ENGINE — the connection pool to PostgreSQL
#   2. A SESSION FACTORY — a "cookie cutter" that produces database sessions
#
# HOW IT WORKS:
#   - On import, it reads the DATABASE_URL from the .env file
#   - It creates a SQLAlchemy engine (connection pool) pointing at that URL
#   - It creates a sessionmaker (factory) that produces Session objects
#   - Other modules import `SessionLocal` and `engine` to interact with the DB
#
# WHY A SESSION FACTORY (sessionmaker)?
#   Instead of creating sessions manually each time, we configure ONE factory
#   with the right settings (autocommit=False, autoflush=False) and then call
#   `SessionLocal()` whenever we need a session. This ensures consistency.
#   Think of it like a cookie cutter — set the shape once, stamp out as many
#   cookies (sessions) as you need.
# ============================================================

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# python-dotenv loads variables from the .env file into os.environ
# so os.getenv("DATABASE_URL") can find them.
from dotenv import load_dotenv

# Load environment variables from the .env file in the project root.
# This MUST happen before we try to read DATABASE_URL.
# load_dotenv() is smart — it won't overwrite existing env vars by default.
load_dotenv()

# ----------------------------------------------------------
# 1. DATABASE URL
# ----------------------------------------------------------
# This is the connection string that tells SQLAlchemy WHERE the database is
# and HOW to authenticate. Format:
#   postgresql://<user>:<password>@<host>:<port>/<database_name>
#
# In development: read from .env file
# In production: this would be set by the hosting platform (e.g., Railway, AWS)
DATABASE_URL: str = os.getenv("DATABASE_URL")

# Defensive check: if someone forgot to create a .env file or set this
# variable, we fail FAST with a clear error message instead of a cryptic
# "NoneType has no attribute" error deep inside SQLAlchemy.
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is not set! "
        "Create a .env file with: DATABASE_URL=postgresql://user:pass@host:port/db"
    )

# ----------------------------------------------------------
# 2. ENGINE — The Connection Pool
# ----------------------------------------------------------
# create_engine() is SQLAlchemy's way of establishing a connection pool
# to the database. Key parameters:
#
#   - DATABASE_URL: Tells it WHERE to connect
#   - echo=False: If True, SQLAlchemy prints every SQL statement it runs.
#     Useful for debugging but VERY noisy in production.
#   - pool_pre_ping=True: Before using a connection from the pool, SQLAlchemy
#     sends a quick "SELECT 1" to verify it's still alive. This prevents
#     "connection already closed" errors after database restarts.
#   - pool_size=5: Maintain 5 connections in the pool (enough for dev).
engine = create_engine(
    DATABASE_URL,
    echo=False,                # Set to True for SQL query debugging
    pool_pre_ping=True,        # Verify connections before use
    pool_size=5,               # Number of permanent connections to keep open
    max_overflow=10,           # Allow up to 10 extra connections during spikes
)

# ----------------------------------------------------------
# 3. SESSION FACTORY — The "Cookie Cutter"
# ----------------------------------------------------------
# sessionmaker() creates a FACTORY (not a session itself).
# Every time we call SessionLocal(), it produces a new Session object
# configured with these settings:
#
#   - bind=engine: This session uses our connection pool
#   - autocommit=False: We must EXPLICITLY call session.commit() to save changes.
#     This prevents accidental partial saves if an error occurs mid-operation.
#   - autoflush=False: Don't auto-sync Python changes to the DB before queries.
#     Gives us more control over when data is actually sent to PostgreSQL.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# ----------------------------------------------------------
# 4. BASE CLASS — The ORM Foundation
# ----------------------------------------------------------
# declarative_base() creates a base class that ALL our ORM models will inherit from.
# Each class that inherits from Base maps to a TABLE in PostgreSQL.
# Example:
#   class RawArticle(Base):
#       __tablename__ = "raw_articles"
#       id = Column(Integer, primary_key=True)
#       ...
#
# Base.metadata.create_all(engine) will scan all classes that inherit from Base
# and CREATE the corresponding tables in PostgreSQL (if they don't exist yet).
Base = declarative_base()


# ----------------------------------------------------------
# 5. HELPER: Get a Database Session
# ----------------------------------------------------------
# This is a convenience function that other modules can use.
# It yields a session and guarantees it gets closed afterward.
#
# Usage (in other files):
#   from database.connection import get_db_session
#   with get_db_session() as session:
#       session.query(RawArticle).all()
#
# The "with" statement ensures session.close() is called even if an error occurs.
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Provides a database session that automatically closes when done.

    This is a CONTEXT MANAGER — use it with a "with" statement:
        with get_db_session() as session:
            session.query(...)
            session.commit()

    WHY AUTO-CLOSE?
    Database connections are a LIMITED resource. If we open sessions and
    forget to close them, the connection pool gets exhausted and the app
    crashes. This pattern ensures cleanup ALWAYS happens, even on errors.
    """
    session = SessionLocal()
    try:
        yield session
        # The caller will call session.commit() if everything went well.
        # If they don't commit, changes are rolled back when we close.
    except Exception:
        # If ANY error occurs during the session, rollback all uncommitted changes.
        # This prevents partial/corrupt data from being saved to the database.
        session.rollback()
        raise  # Re-raise the exception so the caller knows something went wrong
    finally:
        # ALWAYS close the session, whether we succeeded or failed.
        # This returns the connection to the pool for reuse.
        session.close()