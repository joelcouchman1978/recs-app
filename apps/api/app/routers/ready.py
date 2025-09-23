from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, timezone
from sqlalchemy import text

from ..db import get_session, get_redis


router = APIRouter()


class Ready(BaseModel):
    status: str
    time_utc: str
    checks: dict


@router.get("/readyz", response_model=Ready)
async def readyz():
    checks: dict[str, dict] = {}

    try:
        with next(get_session()) as s:
            s.exec(text("SELECT 1"))
            try:
                vec = s.exec(text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector')")).scalar()
            except Exception:
                vec = None
            checks["db"] = {"ok": True, "pgvector": bool(vec) if vec is not None else False}
    except Exception as e:
        checks["db"] = {"ok": False, "error": str(e)}

    try:
        r = get_redis()
        pong = r.ping() if r else False
        checks["redis"] = {"ok": bool(pong)}
    except Exception as e:
        checks["redis"] = {"ok": False, "error": str(e)}

    checks["app"] = {"ok": True}

    overall = "ok" if all(x.get("ok") for x in checks.values()) else "degraded"
    return Ready(status=overall, time_utc=datetime.now(timezone.utc).isoformat(), checks=checks)

