from __future__ import annotations

import os
from datetime import datetime
import logging
from typing import Iterable

from sqlmodel import create_engine, Session, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import text

from .adapters.justwatch import JustWatchAdapter
from .adapters.serializd import SerializdAdapter


def _counted(jobname: str):
    def deco(fn):
        def wrapper(*args, **kwargs):
            try:
                res = fn(*args, **kwargs)
                try:
                    from apps.api.app.metrics import JOB_SUCCESS  # type: ignore
                    JOB_SUCCESS.labels(job=jobname).inc()
                except Exception:
                    pass
                return res
            except Exception:
                try:
                    from apps.api.app.metrics import JOB_FAILURE  # type: ignore
                    JOB_FAILURE.labels(job=jobname).inc()
                except Exception:
                    pass
                raise
        return wrapper
    return deco


def _engine():
    user = os.getenv("POSTGRES_USER", "dev")
    password = os.getenv("POSTGRES_PASSWORD", "dev")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "recs")
    return create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}")


def refresh_justwatch_availability(dry_run: bool = False) -> int:
    """Fetch AU availability for shows and upsert availability rows.
    Returns number of shows updated.
    """
    logger = logging.getLogger("jobs.justwatch")
    if os.getenv("USE_REAL_JUSTWATCH", "false").lower() != "true":
        logger.info("USE_REAL_JUSTWATCH disabled; skipping")
        return 0
    from apps.api.app.models import Show, Availability, OfferType, Quality, Event  # type: ignore
    eng = _engine()
    jw = JustWatchAdapter(region=os.getenv("REGION", "AU"))
    n = 0
    updated_rows = 0
    logger.info("Starting JustWatch availability refresh…")
    with Session(eng) as s:
        shows = s.exec(select(Show)).all()
        for show in shows:
            offers = jw.availability(jw_id=show.jw_id, title=show.title, year=show.year_start)
            if not offers:
                continue
            for o in offers:
                platform = str(o.get("platform"))
                ot = o.get("offer_type")
                offer_type = OfferType.stream if ot == "stream" else (OfferType.rent if ot == "rent" else (OfferType.buy if ot == "buy" else OfferType.stream))
                qv = o.get("quality")
                quality = Quality[qv] if qv in ("SD", "HD", "4K") else None
                leaving_at = o.get("leaving_at")
                if not dry_run:
                    stmt = pg_insert(Availability.__table__).values(
                        show_id=show.id,
                        platform=platform,
                        offer_type=offer_type,
                        quality=quality,
                        leaving_at=leaving_at,
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=[Availability.__table__.c.show_id, Availability.__table__.c.platform, Availability.__table__.c.offer_type],
                        set_={
                            'quality': quality,
                            'leaving_at': leaving_at,
                            'updated_at': datetime.utcnow(),
                        },
                    )
                    s.exec(stmt)
                updated_rows += 1
            if not dry_run:
                s.commit()
            n += 1
        # record status event
        if not dry_run:
            s.add(Event(profile_id=0, kind="admin:status:justwatch", payload={"count_shows": n, "count_rows": updated_rows, "timestamp": datetime.utcnow().isoformat()}))
            s.commit()
    logger.info("JustWatch refresh complete: shows=%s rows=%s", n, updated_rows)
    return n


def sync_serializd_ratings(dry_run: bool = False) -> int:
    """Pull ratings from Serializd and upsert to ratings table for the configured user.
    Returns number of ratings upserted.
    """
    logger = logging.getLogger("jobs.serializd")
    if os.getenv("USE_REAL_SERIALIZD", "false").lower() != "true":
        logger.info("USE_REAL_SERIALIZD disabled; skipping")
        return 0
    from apps.api.app.models import User, Profile, Rating, Show, Event  # type: ignore
    eng = _engine()
    sz = SerializdAdapter()
    data = sz.ratings()
    if not data:
        return 0
    email = os.getenv("SERIALIZD_USER") or ""
    upserted = 0
    logger.info("Starting Serializd ratings sync…")
    with Session(eng) as s:
        user = s.exec(select(User).where(User.email == email)).first()
        if not user:
            logger.warning("Serializd user %s not found in DB; aborting", email)
            return 0
        profile = s.exec(select(Profile).where(Profile.user_id == user.id, Profile.name == "Ross")).first() or s.exec(select(Profile).where(Profile.user_id == user.id)).first()
        if not profile:
            return 0
        for item in data:
            # map serializd record to internal schema
            rec = SerializdAdapter.to_internal_rating(item)
            title = (rec.get("title") or "").strip()
            year = rec.get("year")
            if not title:
                continue
            # try exact title then fallback ilike
            show = s.exec(select(Show).where(Show.title == title)).first() or s.exec(select(Show).where(Show.title.ilike(title))).first()
            if not show:
                continue
            primary = int(rec.get("rating", 1) or 1)
            primary = 2 if primary >= 7 else (1 if primary >= 4 else 0)
            if not dry_run:
                r = Rating(profile_id=profile.id, show_id=show.id, primary=primary)
                s.add(r)
            upserted += 1
        if not dry_run:
            s.commit()
            s.add(Event(profile_id=profile.id, kind="admin:status:serializd", payload={"count_ratings": upserted, "timestamp": datetime.utcnow().isoformat()}))
            s.commit()
    logger.info("Serializd sync complete: ratings=%s", upserted)
    return upserted


def process_admin_triggers() -> dict:
    """Poll the events table for admin sync triggers and process them.
    Deletes processed events. Returns a summary dict with counts.
    """
    from apps.api.app.models import Event  # type: ignore
    eng = _engine()
    summary = {"justwatch": 0, "serializd": 0}
    with Session(eng) as s:
        events = s.exec(select(Event).where(Event.kind.like("admin:sync:%"))).all()
        for ev in events:
            kind = ev.kind or ""
            try:
                if kind == "admin:sync:justwatch":
                    summary["justwatch"] += refresh_justwatch_availability()
                elif kind == "admin:sync:serializd":
                    summary["serializd"] += sync_serializd_ratings()
            finally:
                # delete event regardless to avoid reprocessing
                s.delete(ev)
                s.commit()
    return summary


@_counted("refresh_offers")
def job_refresh_offers(region: str = "AU", title_refs: list[str] | None = None, dry_run: bool = False) -> dict:
    """Fetch and upsert normalized offers into justwatch_offers.
    title_refs: list of title references (jw_id or internal ref).
    """
    logger = logging.getLogger("jobs.offers")
    eng = _engine()
    jw = JustWatchAdapter(region=os.getenv("REGION", region))
    total = 0
    updated = 0
    with Session(eng) as s:
        refs = title_refs or []
        if not refs:
            # Default to using existing show titles
            try:
                from apps.api.app.models import Show  # type: ignore
                shows = s.exec(select(Show.title)).all()
                refs = [t for (t,) in shows] if shows and isinstance(shows[0], tuple) else [getattr(x, 'title', None) for x in shows]
                refs = [r for r in refs if r]
            except Exception:
                refs = []
        for ref in refs[:200]:  # cap batch
            offs = jw.fetch_offers(str(ref), region)
            total += len(offs)
            if not offs or dry_run:
                continue
            for o in offs:
                s.exec(text(
                    """
                    INSERT INTO justwatch_offers (title_ref, provider, offer_type, price, currency, region, last_checked_ts, raw)
                    VALUES (:title_ref, :provider, :offer_type, :price, :currency, :region, :last_checked_ts, :raw)
                    ON CONFLICT (title_ref, provider, offer_type)
                    DO UPDATE SET price = EXCLUDED.price,
                                  currency = EXCLUDED.currency,
                                  region = EXCLUDED.region,
                                  last_checked_ts = EXCLUDED.last_checked_ts,
                                  raw = EXCLUDED.raw
                    """
                ), {
                    "title_ref": o.title_ref,
                    "provider": o.provider,
                    "offer_type": o.offer_type,
                    "price": o.price,
                    "currency": o.currency,
                    "region": o.region,
                    "last_checked_ts": o.last_checked_ts,
                    "raw": o.raw,
                })
                updated += 1
            s.commit()
    logger.info("offers refresh: total_offers=%s updated_rows=%s", total, updated)
    return {"count": total, "updated": updated, "dry_run": dry_run}


@_counted("sync_serializd")
def job_sync_serializd(user: str | None = None, token: str | None = None, dry_run: bool = False) -> dict:
    """Fetch ratings/history from Serializd and insert into serializd_history."""
    logger = logging.getLogger("jobs.serializd_history")
    eng = _engine()
    sz = SerializdAdapter()
    if user:
        sz.user = user
    if token:
        sz.token = token
    items = sz.fetch_watch_history()
    total = len(items)
    inserted = 0
    if not items or dry_run:
        return {"count": total, "inserted": 0, "dry_run": dry_run}
    with Session(eng) as s:
        for it in items:
            s.exec(text(
                """
                INSERT INTO serializd_history (profile_ref, title_ref, tmdb_id, season, episode, status, rating, last_seen_ts, raw)
                VALUES (:profile_ref, :title_ref, :tmdb_id, :season, :episode, :status, :rating, :last_seen_ts, :raw)
                """
            ), {
                "profile_ref": it.profile_ref,
                "title_ref": it.title_ref,
                "tmdb_id": it.tmdb_id,
                "season": it.season,
                "episode": it.episode,
                "status": it.status,
                "rating": it.rating,
                "last_seen_ts": it.last_seen_ts,
                "raw": it.raw,
            })
            inserted += 1
        s.commit()
    logger.info("serializd sync: total=%s inserted=%s", total, inserted)
    return {"count": total, "inserted": inserted, "dry_run": dry_run}


def job_daily_refresh_top_titles(region: str = "AU", limit: int | None = None, dry_run: bool = True) -> dict:
    """Refresh a capped set of the stalest title_refs in justwatch_offers for a region.
    Selects by oldest MAX(last_checked_ts) first. When dry_run, returns a sample only.
    """
    from datetime import datetime, timedelta, timezone
    OFFERS_STALE_DAYS = int(os.getenv("OFFERS_STALE_DAYS", "14"))
    DAILY_REFRESH_LIMIT = int(os.getenv("DAILY_REFRESH_LIMIT", "200"))
    lim = int(limit or DAILY_REFRESH_LIMIT)
    cutoff = datetime.now(timezone.utc) - timedelta(days=OFFERS_STALE_DAYS)
    eng = _engine()
    title_refs: list[str] = []
    with Session(eng) as s:
        rows = s.exec(text(
            """
            SELECT title_ref
            FROM justwatch_offers
            WHERE region = :region
            GROUP BY title_ref
            HAVING COALESCE(MAX(last_checked_ts), TIMESTAMP 'epoch') < :cutoff
            ORDER BY COALESCE(MAX(last_checked_ts), TIMESTAMP 'epoch') ASC
            LIMIT :lim
            """
        ), {"region": region, "cutoff": cutoff, "lim": lim}).all()
        for r in rows or []:
            try:
                title_refs.append(r[0] if isinstance(r, (tuple, list)) else getattr(r, "title_ref"))
            except Exception:
                continue
    if dry_run:
        return {"region": region, "count": len(title_refs), "title_refs_sample": title_refs[:10]}
    return job_refresh_offers(region=region, title_refs=title_refs, dry_run=False)
