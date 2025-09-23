from __future__ import annotations

import os
import json
import time
from typing import Any, Tuple
from collections import OrderedDict

try:
    from redis import Redis
except ImportError:  # pragma: no cover - optional dependency
    Redis = None  # type: ignore

from .settings import settings
from .metrics import CACHE_HITS, CACHE_MISSES


# Simple in-process LRU cache for recommendations
_CACHE: OrderedDict[str, Tuple[float, Any]] = OrderedDict()
_TTL_SECONDS = float(os.getenv("RECS_CACHE_TTL", "60"))
_MAX_ENTRIES = int(os.getenv("RECS_CACHE_MAX", "200"))
_REDIS_URL = settings.resolved_redis_url()
_R: Redis | None = None


def _now() -> float:
    return time.time()


def make_key(email: str, for_: str, intent: str, like_id: str | None, seed: int | None) -> str:
    return f"{email}|{for_}|{intent}|{like_id or '-'}|{seed if seed is not None else '-'}"


def _redis() -> Redis | None:
    global _R
    if _R is not None:
        return _R
    if Redis is None or not _REDIS_URL:
        return None
    try:
        _R = Redis.from_url(_REDIS_URL)
        return _R
    except Exception:
        return None


def get(key: str):
    r = _redis()
    if r is not None:
        try:
            raw = r.get(f"recs:cache:{key}")
            if not raw:
                # miss on redis
                CACHE_MISSES.inc()
                return None
            CACHE_HITS.inc()
            return json.loads(raw)
        except Exception:
            pass
    item = _CACHE.get(key)
    if not item:
        CACHE_MISSES.inc()
        return None
    expires, value = item
    if _now() > expires:
        _CACHE.pop(key, None)
        CACHE_MISSES.inc()
        return None
    # mark as recently used
    _CACHE.move_to_end(key)
    CACHE_HITS.inc()
    return value


def set(key: str, value: Any, ttl: float | None = None):
    r = _redis()
    if r is not None:
        try:
            r.setex(f"recs:cache:{key}", int(ttl or _TTL_SECONDS), json.dumps(value))
            return
        except Exception:
            pass
    _CACHE[key] = (_now() + (ttl or _TTL_SECONDS), value)
    _CACHE.move_to_end(key)
    # evict expired entries first
    for k, (exp, _) in list(_CACHE.items()):
        if _now() > exp:
            _CACHE.pop(k, None)
    # enforce capacity
    while len(_CACHE) > _MAX_ENTRIES:
        _CACHE.popitem(last=False)


def invalidate_for_email(email: str):
    r = _redis()
    if r is not None:
        try:
            # Use SCAN to avoid blocking Redis
            cursor = 0
            pattern = f"recs:cache:{email}|*"
            while True:
                cursor, keys = r.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    r.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            pass
    prefix = f"{email}|"
    dead = [k for k in list(_CACHE.keys()) if k.startswith(prefix)]
    for k in dead:
        _CACHE.pop(k, None)
