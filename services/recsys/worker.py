from __future__ import annotations

import os
import time
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import create_engine
from redis import Redis
from rq import Worker, Queue, Connection

from .jobs import refresh_justwatch_availability, sync_serializd_ratings, process_admin_triggers
from .embeddings import build_show_embeddings, build_profile_embeddings
from sqlmodel import Session


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    user = os.getenv("POSTGRES_USER", "dev")
    password = os.getenv("POSTGRES_PASSWORD", "dev")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "recs")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    create_engine(url)  # ensure DB reachable

    scheduler = BackgroundScheduler()
    # nightly at 03:15 local time
    scheduler.add_job(refresh_justwatch_availability, 'cron', hour=3, minute=15, id='jw_refresh')
    scheduler.add_job(sync_serializd_ratings, 'cron', hour=3, minute=30, id='sz_sync')
    scheduler.start()
    # poll admin triggers every minute
    scheduler.add_job(process_admin_triggers, 'interval', minutes=1, id='admin_triggers')
    # nightly embedding rebuild at 03:45
    def _rebuild_embeddings():
        from sqlmodel import Session as _S
        eng = create_engine(url)
        with _S(eng) as s:
            cs = build_show_embeddings(s)
            cp = build_profile_embeddings(s)
            print(f"Embeddings rebuilt: shows={cs} profiles={cp}")
    scheduler.add_job(_rebuild_embeddings, 'cron', hour=3, minute=45, id='embeddings_rebuild')

    # dev: run once at startup if flags enabled
    try:
        jw = refresh_justwatch_availability()
        sz = sync_serializd_ratings()
        # initial embeddings
        with Session(create_engine(url)) as s:
            cs = build_show_embeddings(s)
            cp = build_profile_embeddings(s)
        print(f"Initial ingest complete: JW={jw}, Serializd={sz}, Emb(shows)={cs}, Emb(profiles)={cp}")
    except Exception as e:
        print(f"Initial ingest error: {e}")

    print("Recsys worker running scheduler…")
    # Start RQ worker alongside scheduler
    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        conn = Redis.from_url(redis_url)
        with Connection(conn):
            w = Worker([Queue('recs')])
            # Run worker loop in foreground; scheduler runs in background
            w.work(with_scheduler=True)
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
