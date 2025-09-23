from __future__ import annotations

from typing import List, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlmodel import Session, select

from ..db import get_session
from ..models import Availability, Profile, Rating, Show
from ..schemas import RecommendationItem, Prediction
from .utils import parse_token
from ..recs import recommendations_for_profiles, pick_season_consistent_offer, is_stale
from ..cache import make_key, get as cache_get, set as cache_set
from ..metrics import RECS_STALE_RATIO, RECS_ITEMS_TOTAL, RECS_ITEMS_STALE_TOTAL

router = APIRouter()


@router.get("/recommendations", response_model=Any)
def get_recommendations(
    for_: str = Query(alias="for", pattern="^(ross|wife|son|family)$"),
    intent: str = Query(default="default"),
    novelty_target: float = 0.3,
    like_id: str | None = Query(default=None, description="Anchor show id to bias similarity"),
    seed: int | None = Query(default=None, description="Deterministic seed for stable tie-breaks"),
    explain: bool = Query(False),
    session: Session = Depends(get_session),
    authorization: str | None = Header(default=None),
):
    email = parse_token(authorization)
    if not email:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # resolve profile(s)
    prof_names = {
        "ross": "Ross",
        "wife": "Wife",
        "son": "Son",
    }
    profiles: list[Profile] = []
    if for_ == "family":
        profiles = session.exec(select(Profile)).all()
    else:
        p = session.exec(select(Profile).where(Profile.name == prof_names[for_])).first()
        if p:
            profiles = [p]

    cache_key = make_key(email, for_, intent, like_id, seed)
    if not explain:
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

    picked, fam_meta = recommendations_for_profiles(session, profiles, intent=intent, count=6, like_id=like_id, seed=seed)

    out: list[RecommendationItem] = []
    for sc in picked:
        avails = session.exec(select(Availability).where(Availability.show_id == sc.show.id)).all()
        wt = [
            {"platform": a.platform, "offer_type": a.offer_type.value if hasattr(a.offer_type, 'value') else str(a.offer_type)}
            for a in avails
        ]
        # Build availability metadata for badges (freshness + season)
        offers = [
            {
                "provider": a.platform,
                "offer_type": a.offer_type.value if hasattr(a.offer_type, 'value') else str(a.offer_type),
                "last_checked_ts": a.updated_at,
                # Season unknown at per-offer granularity; treat as None
                "season": None,
            }
            for a in avails
        ]
        chosen = pick_season_consistent_offer(offers, season=None)
        availability_meta = None
        if chosen:
            ts = chosen.get("last_checked_ts")
            availability_meta = {
                "provider": chosen.get("provider"),
                "type": chosen.get("offer_type"),
                "as_of": (ts.isoformat() if ts else None),
                "stale": is_stale(ts) if ts else True,
                # Without explicit season information, do not claim a season match
                "season_consistent": False,
            }
        label = "BAD" if sc.score < 0.5 else ("ACCEPTABLE" if sc.score < 1.0 else "VERY GOOD")
        # confidence: squash relative to threshold edges
        margin = min(abs(sc.score - 0.5), abs(sc.score - 1.0)) if label != "BAD" else abs(sc.score - 0.5)
        c = max(0.3, min(0.95, 0.5 + margin))
        meta = sc.show.metadata or {}
        # Base rationale from scorer
        base_rationale = (sc.rationale or ("; ".join(sc.why[:2]) if sc.why else "Tone and pacing align without spoilers"))

        out.append(
            RecommendationItem(
                id=str(sc.show.id),
                title=sc.show.title,
                year=sc.show.year_start,
                where_to_watch=wt,
                rationale=base_rationale,
                warnings=[w for w in (sc.show.warnings or [])],
                flags=[f for f in (sc.show.flags or [])],
                prediction=Prediction(label=label, c=round(float(c), 2), n=round(float(sc.novelty), 2)),
                similar_because=sc.evidence or [],
                genres=[g for g in (sc.show.metadata or {}).get('genres', [])][:3],
                creators=[c for c in (sc.show.metadata or {}).get('creators', [])][:2],
                au_rating=(meta.get('au_rating') if isinstance(meta.get('au_rating'), str) else None),
                age_rating=(int(meta.get('age_rating')) if meta.get('age_rating') is not None else None),
                fit_by_profile=[{"name": k, "score": float(v)} for k, v in (sc.fits or {}).items()],
                availability=availability_meta,
                family_strong=bool(getattr(sc, 'is_family_strong', False)),
            )
        )

    # Metrics: stale ratio and item counters (intent label only)
    try:
        intent_str = intent if isinstance(intent, str) and intent else "default"
        total = len(out)
        stale = 0
        for it in out:
            av = getattr(it, "availability", None)
            if isinstance(av, dict) and bool(av.get("stale", False)):
                stale += 1
        RECS_ITEMS_TOTAL.labels(intent=intent_str).inc(total)
        RECS_ITEMS_STALE_TOTAL.labels(intent=intent_str).inc(stale)
        ratio = (stale / total) if total else 0.0
        RECS_STALE_RATIO.labels(intent=intent_str).observe(ratio)
    except Exception:
        pass

    if explain and len(profiles) > 1:
        payload: dict[str, Any] = {"items": out}
        if fam_meta is not None:
            payload["family"] = {
                "strong_locked_ids": fam_meta.get("strong_locked_ids", []),
                "warning": fam_meta.get("warning"),
                "strong_min_fit": fam_meta.get("strong_min_fit"),
                "strong_rule": fam_meta.get("strong_rule"),
            }
        return payload
    else:
        if not explain:
            cache_set(cache_key, out)
        return out
