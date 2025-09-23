from __future__ import annotations

import time
from typing import Callable, TypeVar

import requests

T = TypeVar("T")


def with_backoff(func: Callable[[], T], *, retries: int = 3, base_delay: float = 0.5) -> T:
    """Run a function with simple exponential backoff on network errors and 429/5xx.
    The callable should raise or return a requests.Response or data; if a Response is returned,
    we consider status codes to decide on retry.
    """
    last_exc: Exception | None = None
    delay = base_delay
    for attempt in range(retries):
        try:
            out = func()
            if isinstance(out, requests.Response):
                if out.status_code in (429, 500, 502, 503, 504):
                    # retryable HTTP
                    last_exc = RuntimeError(f"HTTP {out.status_code}")
                else:
                    return out  # type: ignore
            else:
                return out
        except Exception as e:
            last_exc = e
        time.sleep(delay)
        delay *= 2
    if last_exc:
        raise last_exc
    raise RuntimeError("with_backoff exhausted without exception")

