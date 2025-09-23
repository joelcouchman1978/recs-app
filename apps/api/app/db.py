from __future__ import annotations

from pathlib import Path
from typing import Generator

from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.engine import make_url

try:
    from redis import Redis
except ImportError:  # pragma: no cover - optional dependency
    Redis = None  # type: ignore

from .settings import settings

_engine = None
_initialized = False


def _ensure_sqlite_path(url: str) -> None:
    try:
        parsed = make_url(url)
    except Exception:
        return
    if parsed.get_backend_name() != "sqlite":
        return
    database = parsed.database
    if not database or database == ":memory:":
        return
    path = Path(database)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)


def get_engine():
    global _engine
    if _engine is not None:
        return _engine
    url = settings.resolved_database_url()
    _ensure_sqlite_path(url)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(url, echo=False, pool_pre_ping=not url.startswith("sqlite"), connect_args=connect_args)
    return _engine


def init_db() -> None:
    global _initialized
    if _initialized:
        return
    engine = get_engine()
    if settings.use_sqlite:
        from . import models  # noqa: F401
        SQLModel.metadata.create_all(engine)
    _initialized = True


def get_session() -> Generator[Session, None, None]:
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        yield session


def get_redis() -> Redis | None:
    if Redis is None or settings.disable_redis:
        return None
    url = settings.resolved_redis_url()
    if not url:
        return None
    try:
        return Redis.from_url(url)
    except Exception:
        return None
