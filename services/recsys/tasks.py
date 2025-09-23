from __future__ import annotations

from sqlmodel import create_engine, Session

from .jobs import refresh_justwatch_availability, sync_serializd_ratings, job_daily_refresh_top_titles
from .embeddings import build_show_embeddings, build_profile_embeddings


def _engine_url() -> str:
    import os
    user = os.getenv("POSTGRES_USER", "dev")
    password = os.getenv("POSTGRES_PASSWORD", "dev")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "recs")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def rebuild_profile_embedding(profile_id: int) -> dict:
    from apps.api.app.embeddings_util import rebuild_profile_embedding as _rebuild  # type: ignore
    eng = create_engine(_engine_url())
    with Session(eng) as s:
        _rebuild(s, profile_id)
    return {"ok": True, "profile_id": profile_id}


def rebuild_all_embeddings() -> dict:
    eng = create_engine(_engine_url())
    with Session(eng) as s:
        cs = build_show_embeddings(s)
        cp = build_profile_embeddings(s)
    return {"ok": True, "shows": cs, "profiles": cp}


def sync_justwatch(*, dry_run: bool = False) -> dict:
    n = refresh_justwatch_availability(dry_run=dry_run)
    return {"ok": True, "shows_updated": n}


def sync_serializd(*, dry_run: bool = False) -> dict:
    n = sync_serializd_ratings(dry_run=dry_run)
    return {"ok": True, "ratings_upserted": n}


def daily_refresh_top_titles(*, region: str = "AU", limit: int | None = None, dry_run: bool = False) -> dict:
    return job_daily_refresh_top_titles(region=region, limit=limit, dry_run=dry_run)
