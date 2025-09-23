import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from .metrics import REQUEST_LATENCY_MS, RECS_REQUEST_ERRORS
from .logging_setup import set_request_id
from .settings import settings
from prometheus_client import Counter as _Counter

RECS_SLOW_REQUESTS = _Counter('recs_slow_requests_total', 'Recommendations exceeding SLO target')


class RequestIdAndTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(req_id)
        start = time.perf_counter()
        status_code = None
        route_label = request.url.path.rsplit("/", 1)[-1] or request.url.path
        try:
            response = await call_next(request)
            try:
                status_code = int(getattr(response, "status_code", 200))
            except Exception:
                status_code = None
            return response
        except Exception:
            # Count unhandled exceptions as 5xx
            try:
                RECS_REQUEST_ERRORS.labels(route=route_label).inc()
            except Exception:
                pass
            raise
        finally:
            dur_ms = 1000.0 * (time.perf_counter() - start)
            if request.url.path.endswith("/recommendations"):
                REQUEST_LATENCY_MS.observe(dur_ms)
                try:
                    if dur_ms > float(settings.recs_target_p95_ms):
                        from logging import getLogger
                        getLogger(__name__).warning("recs_slow", extra={"lat_ms": round(dur_ms,2), "path": request.url.path, "query": str(request.url.query)})
                        RECS_SLOW_REQUESTS.inc()
                except Exception:
                    pass
            # Count returned 5xx responses
            try:
                if status_code and status_code >= 500:
                    RECS_REQUEST_ERRORS.labels(route=route_label).inc()
            except Exception:
                pass
            set_request_id(None)
