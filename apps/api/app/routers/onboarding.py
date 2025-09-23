from __future__ import annotations

from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..models import Profile, Rating, Event, Show
from ..embeddings_util import rebuild_profile_embedding
from .utils import parse_token


class MoodKnobs(BaseModel):
    tone: int = 2
    pacing: int = 2
    complexity: int = 2
    humor: int = 2
    optimism: int = 2


class Constraints(BaseModel):
    ep_length_max: Optional[int] = None
    seasons_max: Optional[int] = None
    avoid_dnf: Optional[bool] = None
    avoid_cliffhangers: Optional[bool] = None


class OnboardingPayload(BaseModel):
    profile_id: int
    loves: List[str] = []       # show ids
    dislikes: List[str] = []    # show ids
    creators_like: List[str] = []
    creators_dislike: List[str] = []
    mood: MoodKnobs = MoodKnobs()
    constraints: Constraints = Constraints()
    boundaries: Dict[str, bool] = {}


router = APIRouter()


@router.post("/onboarding")
def save_onboarding(payload: OnboardingPayload, session: Session = Depends(get_session), authorization: str | None = Header(default=None)):
    email = parse_token(authorization)
    if not email:
        raise HTTPException(status_code=401, detail="Unauthorized")

    prof = session.get(Profile, payload.profile_id)
    if not prof:
        raise HTTPException(status_code=404, detail="Profile not found")

    # apply boundaries
    if payload.boundaries is not None:
        prof.boundaries = payload.boundaries
        session.add(prof)

    # convert loves/dislikes to ratings
    for sid in payload.loves[:5]:
        session.add(Rating(profile_id=prof.id, show_id=sid, primary=2, nuance_tags=["onboarding"], note="seed love"))
    for sid in payload.dislikes[:3]:
        session.add(Rating(profile_id=prof.id, show_id=sid, primary=0, nuance_tags=["onboarding"], note="seed dislike"))
    session.commit()

    # store event with creators and knobs
    session.add(Event(profile_id=prof.id, kind="onboarding", payload={
        "creators_like": payload.creators_like,
        "creators_dislike": payload.creators_dislike,
        "mood": payload.mood.model_dump(),
        "constraints": payload.constraints.model_dump(),
        "boundaries": payload.boundaries,
    }))
    session.commit()

    # rebuild embedding
    try:
        rebuild_profile_embedding(session, prof.id)
    except Exception:
        pass

    return {"ok": True}

