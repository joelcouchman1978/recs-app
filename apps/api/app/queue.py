from __future__ import annotations

import os
from typing import Optional

try:
    from redis import Redis
except ImportError:  # pragma: no cover - optional dependency
    Redis = None  # type: ignore

from rq import Queue

from .settings import settings

_queue: Optional[Queue] = None


def get_queue() -> Optional[Queue]:
    global _queue
    if _queue is not None:
        return _queue
    if settings.disable_redis or Redis is None:
        return None
    url = os.getenv('REDIS_URL') if not settings.redis_url else settings.redis_url
    if not url:
        url = settings.resolved_redis_url()
    if not url:
        return None
    try:
        conn = Redis.from_url(url)
        _queue = Queue('recs', connection=conn)
        return _queue
    except Exception:
        return None

