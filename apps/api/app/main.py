import os
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time

from .routers import __init__ as rinit  # noqa: F401
from .settings import settings  # noqa: F401
from .logging_setup import configure_logging
from .middleware import RequestIdAndTimingMiddleware
from .metrics import router as metrics_router
from .metrics import RECS_BUILD_INFO
from .routers.health import router as health_router
from .routers.ready import router as ready_router
from .routers.auth import router as auth_router
from .routers.profiles import router as profiles_router
from .routers.shows import router as shows_router
from .routers.ratings import router as ratings_router
from .routers.watchlist import router as watchlist_router
from .routers.recommendations import router as recs_router

from .routers.onboarding import router as onboarding_router
from .routers.debug import router as debug_router
from .routers.providers import router as providers_router
from .db import init_db


configure_logging()
init_db()
app = FastAPI(title="Recs API", version="0.1.0")


if os.getenv('ENABLE_DEBUG_ENDPOINTS', '0') in ('1','true','True'):
    from .routers.admin import router as admin_router
    app.include_router(admin_router)
allow = settings.allow_origins or "http://localhost:3000"
origins = [o.strip().rstrip('/') for o in allow.split(',') if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(RequestIdAndTimingMiddleware)


app.include_router(health_router)
app.include_router(ready_router)
app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(shows_router)
app.include_router(ratings_router)
app.include_router(watchlist_router)
app.include_router(recs_router)
app.include_router(metrics_router)

app.include_router(onboarding_router)
app.include_router(debug_router)
app.include_router(providers_router)


# --- Admin rate limit (prod only) ---
class _AdminRateLimit(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._toks = float(settings.admin_burst)
        self._ts = time.time()

    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/admin") and (settings.environment or "dev").lower() == "prod":
            now = time.time()
            refill = (now - self._ts) * float(settings.admin_rps)
            self._toks = min(float(settings.admin_burst), self._toks + refill)
            self._ts = now
            if self._toks < 1.0:
                return JSONResponse({"error": "rate_limited"}, status_code=429)
            self._toks -= 1.0
        return await call_next(request)


app.add_middleware(_AdminRateLimit)

# Record build info gauge on startup import
try:
    RECS_BUILD_INFO.labels(
        version=settings.app_version,
        sha=(settings.git_sha or "unknown"),
        env=(settings.environment or "dev"),
    ).set(1)
except Exception:
    pass
