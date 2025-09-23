from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlmodel import Session, select

from ..db import get_session
from ..models import Watchlist
from .utils import parse_token

router = APIRouter()


@router.get("/watchlist")
def list_watchlist(
    profile_id: int = Query(..., ge=1),
    session: Session = Depends(get_session),
    authorization: str | None = Header(default=None),
):
    email = parse_token(authorization)
    if not email:
        raise HTTPException(status_code=401, detail="Unauthorized")
    rows = session.exec(select(Watchlist).where(Watchlist.profile_id == profile_id)).all()
    return {"show_ids": [str(r.show_id) for r in rows]}


@router.post("/watchlist")
def add_to_watchlist(
    payload: dict,
    session: Session = Depends(get_session),
    authorization: str | None = Header(default=None),
):
    email = parse_token(authorization)
    if not email:
        raise HTTPException(status_code=401, detail="Unauthorized")
    wl = Watchlist(profile_id=payload["profile_id"], show_id=payload["show_id"])  # type: ignore
    session.add(wl)
    session.commit()
    return {"ok": True}


@router.delete("/watchlist")
def remove_from_watchlist(
    profile_id: int = Query(..., ge=1),
    show_id: str = Query(...),
    session: Session = Depends(get_session),
    authorization: str | None = Header(default=None),
):
    email = parse_token(authorization)
    if not email:
        raise HTTPException(status_code=401, detail="Unauthorized")
    row = session.exec(select(Watchlist).where(Watchlist.profile_id == profile_id, Watchlist.show_id == show_id)).first()
    if not row:
        # No-op if not present
        return {"ok": True}
    session.delete(row)
    session.commit()
    return {"ok": True}
