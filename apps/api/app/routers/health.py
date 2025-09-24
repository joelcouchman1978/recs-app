from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

import logging
from ..db import get_session, get_redis
from ..settings import settings

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str
    time_utc: str
    checks: dict
    version: str | None = None
    sha: str | None = None


@router.get("/healthz", response_model=Health)
async def healthz():
    logger = logging.getLogger(__name__)
    checks: dict[str, dict] = {}

    # DB check + optional pgvector extension presence
    try:
        with next(get_session()) as s:
            s.exec(text("SELECT 1"))
            vec = None
            if not settings.use_sqlite:
                try:
                    vec = s.exec(text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector')")).scalar()
                except Exception:
                    vec = None
            checks["db"] = {"ok": True, "pgvector": bool(vec) if vec is not None else False}
    except Exception as e:
        checks["db"] = {"ok": False, "error": str(e)}

    # Redis
    if settings.disable_redis:
        checks["redis"] = {"ok": True, "disabled": True}
    else:
        try:
            r = get_redis()
            pong = r.ping() if r else False
            checks["redis"] = {"ok": bool(pong)}
        except Exception as e:
            checks["redis"] = {"ok": False, "error": str(e)}

    # App-level
    checks["app"] = {"ok": True}

    overall = "ok" if all(x.get("ok") for x in checks.values()) else "degraded"
    resp = Health(status=overall, time_utc=datetime.now(timezone.utc).isoformat(), checks=checks, version=settings.app_version, sha=settings.git_sha)
    if resp.status != "ok":
        try:
            logger.warning("healthz degraded", extra={"checks": checks})
        except Exception:
            pass
    return resp
