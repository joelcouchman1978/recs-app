from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session

from ..db import get_session
from ..models import Rating
from ..embeddings_util import rebuild_profile_embedding
from ..queue import get_queue
from ..schemas import RatingCreate
from .utils import parse_token
from ..cache import invalidate_for_email

router = APIRouter()


@router.post("/ratings")
def post_rating(
    payload: RatingCreate,
    session: Session = Depends(get_session),
    authorization: str | None = Header(default=None),
):
    email = parse_token(authorization)
    if not email:
        raise HTTPException(status_code=401, detail="Unauthorized")
    r = Rating(
        profile_id=payload.profile_id,
        show_id=payload.show_id,  # type: ignore
        primary=payload.primary,
        nuance_tags=payload.nuance_tags,
        note=payload.note,
    )
    session.add(r)
    session.commit()
    # rebuild profile embedding to adapt recommendations quickly
    try:
        rebuild_profile_embedding(session, payload.profile_id)
    except Exception:
        pass
    # enqueue async rebuild as well
    try:
        q = get_queue()
        if q:
            q.enqueue('tasks.rebuild_profile_embedding', kwargs={"profile_id": payload.profile_id})
    except Exception:
        pass
    # invalidate rec cache for this user
    email = parse_token(authorization)
    if email:
        try:
            invalidate_for_email(email)
        except Exception:
            pass
    return {"ok": True}
