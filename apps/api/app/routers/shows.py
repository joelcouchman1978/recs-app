from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..db import get_session
from ..models import Show, Availability

router = APIRouter()


@router.get("/shows")
def list_shows(limit: int = Query(default=60, ge=1, le=200), session: Session = Depends(get_session)):
    shows = session.exec(select(Show).limit(limit)).all()
    out = []
    for s in shows:
        out.append({
            "id": str(s.id),
            "title": s.title,
            "year_start": s.year_start,
            "metadata": s.metadata,
            "warnings": s.warnings,
            "flags": s.flags,
        })
    return out

@router.get("/shows/{show_id}")
def get_show(show_id: str, session: Session = Depends(get_session)):
    show = session.get(Show, show_id)
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    avails = session.exec(select(Availability).where(Availability.show_id == show.id)).all()
    return {
        "id": str(show.id),
        "title": show.title,
        "year_start": show.year_start,
        "year_end": show.year_end,
        "metadata": show.metadata,
        "warnings": show.warnings,
        "flags": show.flags,
        "availability": [
            {
                "platform": a.platform,
                "offer_type": a.offer_type.value if hasattr(a.offer_type, 'value') else str(a.offer_type),
                "quality": a.quality.value if a.quality and hasattr(a.quality, 'value') else (str(a.quality) if a.quality else None),
                "leaving_at": a.leaving_at.isoformat() if a.leaving_at else None,
            }
            for a in avails
        ],
    }
