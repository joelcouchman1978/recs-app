from __future__ import annotations

import os
from typing import List
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlmodel import Session, select

from ..db import get_session
from ..models import Availability, Profile, Show
from .utils import parse_token
from ..recs import _score_show, _boundary_violates, _episode_length  # type: ignore


router = APIRouter()


@router.get("/debug/recommendations")
def debug_recommendations(
    for_: str = Query(alias="for", pattern="^(ross|wife|son|family)$"),
    intent: str = Query(default="default"),
    session: Session = Depends(get_session),
    authorization: str | None = Header(default=None),
):
    if os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="disabled")

    email = parse_token(authorization)
    if not email:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # resolve profile(s)
    prof_names = {"ross": "Ross", "wife": "Wife", "son": "Son"}
    profiles: list[Profile] = []
    if for_ == "family":
        profiles = session.exec(select(Profile)).all()
    else:
        p = session.exec(select(Profile).where(Profile.name == prof_names[for_])).first()
        if p:
            profiles = [p]
    if not profiles:
        return []

    # liked sets per profile (genres/creators)
    from ..models import Rating, Show as ShowModel
    liked_by_profile: dict[int, tuple[set[str], set[str]]] = {}
    for p in profiles:
        gset: set[str] = set()
        cset: set[str] = set()
        ratings = session.exec(select(Rating).where(Rating.profile_id == p.id)).all()
        for r in ratings:
            s = session.get(ShowModel, r.show_id)
            if not s:
                continue
            if r.primary == 2:
                gset |= set((s.metadata or {}).get("genres", []))
                cset |= set((s.metadata or {}).get("creators", []))
        liked_by_profile[p.id] = (gset, cset)

    # Union boundaries
    union_boundaries: dict = {}
    for p in profiles:
        union_boundaries.update({k: v for k, v in (p.boundaries or {}).items() if v})

    def available(s: Show) -> bool:
        av = session.exec(select(Availability).where(Availability.show_id == s.id)).first()
        return av is not None

    all_shows = session.exec(select(Show)).all()
    candidates: list[Show] = []
    for s in all_shows:
        if not available(s):
            continue
        if intent == "short_tonight" and _episode_length(s) > 35:
            continue
        if _boundary_violates(s, union_boundaries):
            continue
        candidates.append(s)

    # compute per-profile scores per candidate
    def per_scores(s: Show) -> list[float]:
        scores: list[float] = []
        for p in profiles:
            gset, cset = liked_by_profile.get(p.id, (set(), set()))
            sc, _, _ = _score_show(s, intent, gset, cset)
            scores.append(float(sc))
        return scores

    items = [{"id": str(s.id), "title": s.title, "scores": per_scores(s)} for s in candidates]

    # Pareto frontier selection
    def dominated(a: list[float], b: list[float]) -> bool:
        ge_all = all(bi >= ai for ai, bi in zip(a, b))
        gt_any = any(bi > ai for ai, bi in zip(a, b))
        return ge_all and gt_any

    frontier = []
    for i, it in enumerate(items):
        a = it["scores"]
        dom = False
        for j, ot in enumerate(items):
            if i == j:
                continue
            if dominated(a, ot["scores"]):
                dom = True
                break
        if not dom:
            frontier.append(it)

    return frontier[:12]

