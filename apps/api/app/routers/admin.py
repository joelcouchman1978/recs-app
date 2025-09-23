import os
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import engine
from ..models import Event
from ..queue import get_queue
from rq.registry import StartedJobRegistry, FinishedJobRegistry, FailedJobRegistry, DeferredJobRegistry
import requests, json
import os
from sqlalchemy import text
from ..settings import settings
from services.recsys.jobs import job_refresh_offers, job_sync_serializd


class SyncPayload(BaseModel):
    source: str  # 'justwatch' | 'serializd'
    dry_run: bool | None = None


from .utils import parse_token
from ..settings import settings

router = APIRouter()


def _require_admin(authorization: str | None):
    # In prod, deny dev magic tokens; require JWT-based auth via parse_token
    if settings.environment == "prod" and authorization and "devtoken:" in authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")
    email = parse_token(authorization)
    if not email:
        raise HTTPException(status_code=401, detail="Unauthorized")
    allowed = os.getenv("ADMIN_EMAILS") or "demo@local.test"
    allow_list = {e.strip().lower() for e in allowed.split(',') if e.strip()}
    if email.lower() not in allow_list:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/admin/sync")
def trigger_sync(payload: SyncPayload, authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    if payload.source not in ("justwatch", "serializd"):
        raise HTTPException(status_code=400, detail="invalid source")
    kind = f"admin:sync:{payload.source}"
    # Enqueue via RQ for immediate processing if available
    try:
        q = get_queue()
        if q:
            if payload.source == 'justwatch':
                q.enqueue('tasks.sync_justwatch', kwargs={"dry_run": bool(payload.dry_run)})
            elif payload.source == 'serializd':
                q.enqueue('tasks.sync_serializd', kwargs={"dry_run": bool(payload.dry_run)})
    except Exception:
        pass
    with Session(engine) as s:
        s.add(Event(profile_id=0, kind=kind, payload={}))
        s.commit()
    return {"ok": True, "queued": kind}


@router.post("/admin/jobs/daily_refresh")
def trigger_daily_refresh(limit: int | None = None, region: str = "AU", dry_run: bool = True, authorization: str | None = Header(default=None)):
    """Trigger the daily offers refresh. By default runs as dry-run and returns a summary.
    In production, this should be enqueued to RQ.
    """
    _require_admin(authorization)
    # Prefer queue when available
    try:
        q = get_queue()
        if q and not dry_run:
            q.enqueue('tasks.daily_refresh_top_titles', kwargs={"region": region, "limit": limit, "dry_run": False})
            return {"ok": True, "queued": True}
    except Exception:
        pass
    # Fallback: call job directly (dry-run or immediate execution)
    try:
        from services.recsys.jobs import job_daily_refresh_top_titles  # type: ignore
        res = job_daily_refresh_top_titles(region=region, limit=limit, dry_run=dry_run)
        return {"ok": True, **({"summary": res} if dry_run else res)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/queue")
def queue_status(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    q = get_queue()
    if not q:
        return {"ok": False, "error": "queue unavailable"}
    try:
        started = StartedJobRegistry(queue=q)
        finished = FinishedJobRegistry(queue=q)
        failed = FailedJobRegistry(queue=q)
        deferred = DeferredJobRegistry(queue=q)
        return {
            "ok": True,
            "queue": {"name": q.name, "count": q.count},
            "registries": {
                "started": len(started),
                "finished": len(finished),
                "failed": len(failed),
                "deferred": len(deferred),
            },
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/admin/embeddings/rebuild")
def enqueue_rebuild_embeddings(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    q = get_queue()
    if not q:
        raise HTTPException(status_code=503, detail="queue unavailable")
    try:
        q.enqueue('tasks.rebuild_all_embeddings')
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/admin/status")
def get_status(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    out = {"justwatch": None, "serializd": None, "preview": {"justwatch": None, "serializd": None}}
    with Session(engine) as s:
        jw = s.exec(select(Event).where(Event.kind == "admin:status:justwatch").order_by(Event.created_at.desc())).first()
        sz = s.exec(select(Event).where(Event.kind == "admin:status:serializd").order_by(Event.created_at.desc())).first()
        out["justwatch"] = jw.payload if jw else None
        out["serializd"] = sz.payload if sz else None
        pjw = s.exec(select(Event).where(Event.kind == "admin:preview:justwatch").order_by(Event.created_at.desc())).first()
        psz = s.exec(select(Event).where(Event.kind == "admin:preview:serializd").order_by(Event.created_at.desc())).first()
        out["preview"]["justwatch"] = pjw.payload if pjw else None
        out["preview"]["serializd"] = psz.payload if psz else None
    return out


def _provider_map() -> dict[int, str]:
    base = {
        8: "Netflix", 24: "Prime Video", 179: "Disney+", 37: "Stan", 387: "Binge", 350: "Apple TV+",
        85: "SBS On Demand", 84: "ABC iView", 382: "BritBox", 337: "Paramount+", 119: "YouTube", 3: "Google Play", 10: "Apple iTunes",
    }
    try:
        raw = os.getenv("JUSTWATCH_PROVIDER_MAP")
        if raw:
            override = json.loads(raw)
            for k, v in override.items():
                try:
                    base[int(k)] = str(v)
                except Exception:
                    continue
    except Exception:
        pass
    return base


@router.get("/admin/preview/availability")
def preview_availability(title: str, year: int | None = None, authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    if os.getenv("USE_REAL_JUSTWATCH", "false").lower() != "true":
        raise HTTPException(status_code=400, detail="JustWatch disabled")
    try:
        r = requests.get("https://apis.justwatch.com/content/titles/", timeout=10, params={"language": "en_AU", "q": title})
        r.raise_for_status()
        items = (r.json() or {}).get("items", [])
        if year:
            items = [i for i in items if i.get("original_release_year") == year]
        it = items[0] if items else None
        if not it:
            return {"offers": [], "provider_map": _provider_map()}
        jw_id = it.get("id")
        r2 = requests.get(f"https://apis.justwatch.com/content/titles/show/{jw_id}/locale/en_AU", timeout=10)
        r2.raise_for_status()
        offers = (r2.json() or {}).get("offers", [])
        pm = _provider_map()
        out = []
        for o in offers:
            if o.get("monetization_type") not in ("flatrate", "rent", "buy"):
                continue
            pid = o.get("provider_id")
            platform = pm.get(pid, f"provider_{pid}")
            pres = (o.get("presentation_type") or "").upper()
            quality = "4K" if "4K" in pres else ("HD" if "HD" in pres else ("SD" if pres else None))
            mtype = o.get("monetization_type")
            offer_type = "stream" if mtype == "flatrate" else mtype
            out.append({"platform": platform, "offer_type": offer_type, "quality": quality})
        summary = {"offers": out[:10], "count_offers": len(out), "provider_map": pm, "jw_id": jw_id, "timestamp": datetime.utcnow().isoformat()}
        # store preview event
        try:
            with Session(engine) as s:
                s.add(Event(profile_id=0, kind="admin:preview:justwatch", payload=summary))
                s.commit()
        except Exception:
            pass
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/preview/serializd")
def preview_serializd(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    if os.getenv("USE_REAL_SERIALIZD", "false").lower() != "true":
        raise HTTPException(status_code=400, detail="Serializd disabled")
    user = os.getenv("SERIALIZD_USER"); token = os.getenv("SERIALIZD_TOKEN")
    if not (user and token):
        raise HTTPException(status_code=400, detail="Serializd credentials missing")
    try:
        r = requests.get(f"https://api.serializd.com/users/{user}/ratings", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            data = []
        samples = [{"title": (d.get("title") or ""), "year": d.get("year"), "rating": d.get("rating")} for d in data[:10]]
        summary = {"count": len(data), "samples": samples, "timestamp": datetime.utcnow().isoformat()}
        try:
            with Session(engine) as s:
                s.add(Event(profile_id=0, kind="admin:preview:serializd", payload=summary))
                s.commit()
        except Exception:
            pass
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/preview/sample_justwatch")
def preview_sample_justwatch(limit: int = 5, authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    if os.getenv("USE_REAL_JUSTWATCH", "false").lower() != "true":
        raise HTTPException(status_code=400, detail="JustWatch disabled")
    from ..models import Show  # type: ignore
    with Session(engine) as s:
        shows = s.exec(select(Show).limit(max(1, min(limit, 10)))).all()
        out = []
        total_offers = 0
        for show in shows:
            try:
                r = requests.get("https://apis.justwatch.com/content/titles/", timeout=10, params={"language": "en_AU", "q": show.title})
                r.raise_for_status()
                items = (r.json() or {}).get("items", [])
                it = items[0] if items else None
                if not it:
                    out.append({"show_id": str(show.id), "title": show.title, "offers": []}); continue
                jw_id = it.get("id")
                r2 = requests.get(f"https://apis.justwatch.com/content/titles/show/{jw_id}/locale/en_AU", timeout=10)
                r2.raise_for_status()
                offers = (r2.json() or {}).get("offers", [])
                pm = _provider_map()
                mapped = []
                for o in offers[:10]:
                    if o.get("monetization_type") not in ("flatrate", "rent", "buy"):
                        continue
                    pid = o.get("provider_id")
                    platform = pm.get(pid, f"provider_{pid}")
                    pres = (o.get("presentation_type") or "").upper()
                    quality = "4K" if "4K" in pres else ("HD" if "HD" in pres else ("SD" if pres else None))
                    mtype = o.get("monetization_type")
                    offer_type = "stream" if mtype == "flatrate" else mtype
                    mapped.append({"platform": platform, "offer_type": offer_type, "quality": quality})
                total_offers += len(mapped)
                out.append({"show_id": str(show.id), "title": show.title, "offers": mapped})
            except Exception:
                out.append({"show_id": str(show.id), "title": show.title, "offers": []})
        summary = {"count_shows": len(shows), "count_offers": total_offers, "samples": out, "timestamp": datetime.utcnow().isoformat()}
        try:
            with Session(engine) as s:
                s.add(Event(profile_id=0, kind="admin:preview:justwatch", payload=summary))
                s.commit()
        except Exception:
            pass
        return summary


@router.get("/admin/freshness")
def get_freshness(authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    with Session(engine) as s:
        o = s.exec(text("SELECT MAX(last_checked_ts) AS ts, COUNT(*) AS n FROM justwatch_offers")).first()
        h = s.exec(text("SELECT MAX(last_seen_ts) AS ts, COUNT(*) AS n FROM serializd_history")).first()
        return {
            "offers_last_checked": (o[0].isoformat() if o and o[0] else None),
            "offers_rows": int(o[1] or 0) if o else 0,
            "serializd_last_seen": (h[0].isoformat() if h and h[0] else None),
            "serializd_rows": int(h[1] or 0) if h else 0,
        }


@router.post("/admin/sync/justwatch")
def admin_sync_justwatch(region: str = Query("AU"), dry_run: bool = Query(True), authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    return job_refresh_offers(region=region, title_refs=[], dry_run=dry_run)


@router.post("/admin/sync/serializd")
def admin_sync_serializd(dry_run: bool = Query(True), authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    if not (settings.serializd_user and settings.serializd_token):
        return {"error": "SERIALIZD_USER/TOKEN not configured"}
    return job_sync_serializd(user=settings.serializd_user, token=settings.serializd_token, dry_run=dry_run)
