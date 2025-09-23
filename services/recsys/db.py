from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://%s:%s@%s:%s/%s" % (
        os.getenv("POSTGRES_USER", "dev"),
        os.getenv("POSTGRES_PASSWORD", "dev"),
        os.getenv("POSTGRES_HOST", "postgres"),
        os.getenv("POSTGRES_PORT", "5432"),
        os.getenv("POSTGRES_DB", "recs"),
    ),
)

_engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
_Session = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


def get_session():
    """Return a SQLAlchemy session. Use as a context manager: with get_session() as s: ..."""
    return _Session()

