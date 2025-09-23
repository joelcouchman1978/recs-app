import os
import time
from datetime import datetime, timedelta

from rq import Queue
from redis import Redis

from services.recsys.jobs import job_daily_refresh_top_titles

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REGION = os.getenv("REGION", "AU")
LIMIT = int(os.getenv("DAILY_REFRESH_LIMIT", "200"))
RUN_AT_HOUR = int(os.getenv("DAILY_REFRESH_HOUR", "3"))  # 03:00 local


def next_run(now: datetime) -> datetime:
    target = now.replace(hour=RUN_AT_HOUR, minute=0, second=0, microsecond=0)
    if now >= target:
        target = target + timedelta(days=1)
    return target


def main():
    r = Redis.from_url(REDIS_URL)
    q = Queue("recs", connection=r)
    while True:
        now = datetime.now()
        nr = next_run(now)
        sleep_s = max(1, int((nr - now).total_seconds()))
        time.sleep(sleep_s)
        # enqueue job (non-dry-run)
        try:
            q.enqueue(job_daily_refresh_top_titles, region=REGION, limit=LIMIT, dry_run=False)
        except Exception:
            # In case enqueue fails, try direct call to avoid missing a day
            try:
                job_daily_refresh_top_titles(region=REGION, limit=LIMIT, dry_run=False)
            except Exception:
                pass


if __name__ == "__main__":
    main()

