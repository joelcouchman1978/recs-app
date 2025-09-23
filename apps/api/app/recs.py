from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from datetime import datetime, timezone, timedelta
import os
import logging
from statistics import mean, pstdev
from typing import Iterable, List, Tuple

from sqlmodel import Session, select
from sqlalchemy import text

from .models import Availability, Profile, Rating, Show
from .settings import settings
from .history_adj import HistoryRecent
from .spoiler_lint import assert_no_spoilers, SpoilerError


@dataclass
class Scored:
    show: Show
    score: float
    why: list[str]
    novelty: float
    vec_sim: float | None = None
    rationale: str | None = None
    evidence: list[str] | None = None
    fits: dict[str, float] | None = None
    factors: "FitFactors | None" = None
    is_family_strong: bool | None = None


@dataclass
class FitFactors:
    base: float
    rating_prior: float = 0.0
    tag_nudge: float = 0.0
    note_nudge: float = 0.0
    history_adj: float = 0.0


def _stable_hash01(item_id: str, seed: int | None) -> float:
    h = blake2b(digest_size=8)
    h.update(item_id.encode())
    if seed is not None:
        h.update(str(seed).encode())
    n = int.from_bytes(h.digest(), "big")
    return (n % 10_000_000) / 10_000_000.0


def _apply_feedback(
    *,
    show: Show,
    base_score: float,
    seed: int | None,
    liked_tags: set[str],
    notes_text: str,
    rating_priors: list[int],
    history_recent: HistoryRecent | None,
    intent: str,
) -> tuple[float, FitFactors]:
    ff = FitFactors(base=base_score)

    # 1) Ratings prior for this item (across selected profiles)
    for pri in rating_priors:
        if pri == 2:
            ff.rating_prior += settings.rating_weight_very_good
        elif pri == 1:
            ff.rating_prior += settings.rating_weight_acceptable
        elif pri == 0:
            ff.rating_prior -= settings.rating_penalty_bad

    # 2) Tags: treat show.flags as lightweight tags
    itags = set(show.flags or [])
    ff.tag_nudge += len(liked_tags & itags) * settings.tag_like_bonus
    # No explicit disliked tags in current model; keep at zero unless added later

    # 3) Notes keywords
    nt = (notes_text or "").lower()
    for k, w in (settings.note_keyword_weights or {}).items():
        if k in nt:
            ff.note_nudge += float(w)
    ff.note_nudge = max(min(ff.note_nudge, 0.25), -0.35)

    # 4) Serializd adjacency (no-op unless provided)
    if history_recent and history_recent.is_adjacent(show):
        ff.history_adj += settings.history_adj_boost
    # If we ever track completion + rewatch intent, we could subtract here
    if intent != "rewatch":
        # nothing to subtract without explicit completion state
        pass

    # Compose multiplicatively
    multiplier = (1.0 + ff.rating_prior) * (1.0 + ff.tag_nudge + ff.note_nudge + ff.history_adj)
    score = max(0.0, base_score * multiplier)
    # Deterministic micro-jitter for stable tiebreaks
    score += 1e-6 * _stable_hash01(str(show.id), seed)
    return score, ff


# Simple mapping to human language (keep short)
_TONE_WORDS = {
    "comedy": "funny",
    "drama": "grounded",
    "thriller": "tense",
    "family": "family-friendly",
}

_DEF_REASON = "Matches your recent picks"


def build_rationale(item: Show, fit_factors: FitFactors | None, profile) -> str:
    """Premise-only, tone, why-you. Avoid plot beyond pilot.
    Example: "A grounded legal drama; you liked similar shows and tags."
    """
    parts: list[str] = []
    meta = item.metadata or {}
    genres = list(meta.get("genres", []) or [])
    tags = list(item.flags or [])
    tone = None
    for t in genres + tags:
        if t in _TONE_WORDS:
            tone = _TONE_WORDS[t]
            break
    primary_genre = genres[0] if genres else "series"
    if tone:
        parts.append(f"A {tone} {primary_genre}")
    else:
        parts.append(f"A {primary_genre}")

    why_bits: list[str] = []
    if fit_factors and getattr(fit_factors, "rating_prior", 0) > 0:
        why_bits.append("you rated similar shows highly")
    if fit_factors and getattr(fit_factors, "tag_nudge", 0) > 0:
        why_bits.append("matches your liked tags")
    if fit_factors and getattr(fit_factors, "history_adj", 0) > 0:
        why_bits.append("near your recent watches")
    if not why_bits:
        why_bits.append(_DEF_REASON)

    text = "; ".join([parts[0], ", ".join(why_bits)])
    text = (text[: settings.rationale_max_chars]).rstrip()
    assert_no_spoilers(text)
    return text


# --- Availability freshness and season helpers ---
STALE_DELTA = timedelta(days=settings.offers_stale_days)


def is_stale(ts: datetime | None) -> bool:
    if not ts:
        return True
    now = datetime.now(timezone.utc)
    # ensure tz-aware comparisons
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (now - ts) > STALE_DELTA


def pick_season_consistent_offer(offers: list[dict], *, season: int | None) -> dict | None:
    if not offers:
        return None
    def freshness(o: dict) -> datetime:
        ts = o.get("last_checked_ts")
        if isinstance(ts, datetime):
            return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        return datetime.min.replace(tzinfo=timezone.utc)
    if season is None or not settings.season_strict:
        return max(offers, key=freshness)
    season_offers = [o for o in offers if o.get("season") in (None, season)]
    if season_offers:
        return max(season_offers, key=freshness)
    return max(offers, key=freshness)


# --- Family Mix strong-pick helpers ---
def _family_fit_agg(fits_by_profile: dict[str, float]) -> float:
    if not fits_by_profile:
        return 0.0
    if (settings.family_strong_rule or "min").lower() == "avg":
        return sum(fits_by_profile.values()) / max(1, len(fits_by_profile))
    return min(fits_by_profile.values())


def is_strong_for_family(fits_by_profile: dict[str, float]) -> bool:
    try:
        agg = _family_fit_agg(fits_by_profile)
        return agg >= float(settings.family_strong_min_fit)
    except Exception:
        return False


def _genres(s: Show) -> set[str]:
    return set((s.metadata or {}).get("genres", []))


def _creators(s: Show) -> set[str]:
    return set((s.metadata or {}).get("creators", []))


def _episode_length(s: Show) -> int:
    return int((s.metadata or {}).get("episode_length", 60))


def _familiarity(show: Show, liked_genres: set[str], liked_creators: set[str]) -> float:
    g_overlap = len(_genres(show) & liked_genres)
    c_overlap = len(_creators(show) & liked_creators)
    return min(1.0, 0.15 * g_overlap + 0.3 * c_overlap)


def _boundary_violates(show: Show, boundaries: dict) -> bool:
    warns = set(show.warnings or [])
    banned = {k for k, v in (boundaries or {}).items() if v}
    return len(warns & banned) > 0


def _availability(session: Session, show: Show) -> list[Availability]:
    return session.exec(select(Availability).where(Availability.show_id == show.id)).all()


def _age_rating(s: Show) -> int | None:
    meta = (s.metadata or {})
    # Numeric age rating directly
    try:
        if meta.get("age_rating") is not None:
            return int(meta.get("age_rating"))
    except Exception:
        pass
    # AU ratings mapping if present
    au = str(meta.get("au_rating") or "").upper().replace(" ", "")
    if au:
        mapping = {
            "G": 0,
            "PG": 8,
            "M": 15,
            "MA15+": 15,
            "MA15": 15,
            "R18+": 18,
            "R18": 18,
        }
        if au in mapping:
            return mapping[au]
    return None


def _score_show(
    show: Show,
    intent: str,
    liked_genres: set[str],
    liked_creators: set[str],
    vec_sim: float | None = None,
    pref: dict | None = None,
) -> Tuple[float, list[str], float]:
    g = _genres(show)
    c = _creators(show)
    why: list[str] = []

    sim = 0.0
    g_overlap = len(g & liked_genres)
    c_overlap = len(c & liked_creators)
    sim += 0.2 * g_overlap + 0.5 * c_overlap
    if vec_sim is not None:
        sim += 0.6 * vec_sim  # weight for vector similarity
    if c_overlap:
        why.append("From a creator you’ve enjoyed")
    if g_overlap:
        why.append("Matches your preferred tones/genres")

    context_bonus = 0.0
    if intent == "short_tonight":
        if _episode_length(show) <= 35:
            context_bonus += 0.3
            why.append("Short episodes fit ‘short tonight’")
        else:
            context_bonus -= 0.5  # filtered earlier but keep penalty safeguard
    elif intent == "weekend_binge":
        # favor longer episodes and multiple seasons
        if (show.metadata or {}).get("seasons", 1) >= 2:
            context_bonus += 0.3
        if _episode_length(show) >= 40:
            context_bonus += 0.15
    elif intent == "comfort":
        # comfort slightly rewards familiarity
        context_bonus += min(0.2, 0.5 * (1.0 - _familiarity(show, liked_genres, liked_creators))) * -1
    elif intent == "surprise":
        # surprise slightly rewards novelty
        context_bonus += 0.2

    # Apply onboarding preferences if provided
    if pref:
        el = _episode_length(show)
        seasons = int((show.metadata or {}).get("seasons", 1) or 1)
        cons = pref.get("constraints") or {}
        if cons.get("ep_length_max") is not None:
            maxlen = int(cons.get("ep_length_max"))
            if el <= maxlen:
                context_bonus += 0.1
            else:
                over = max(0, el - maxlen)
                penalty = min(0.3, 0.01 * over)
                context_bonus -= penalty
                why.append("Longer than your preferred episode length")
        if cons.get("seasons_max") is not None:
            smax = int(cons.get("seasons_max"))
            if seasons <= smax:
                context_bonus += 0.05
            else:
                over_s = max(0, seasons - smax)
                penalty = min(0.25, 0.05 * over_s)
                context_bonus -= penalty
                why.append("More seasons than you prefer")
        if cons.get("avoid_cliffhangers") and ("cliffhanger" in (show.flags or []) or "cliffhanger" in (show.warnings or [])):
            context_bonus -= 0.2
        if cons.get("avoid_dnf"):
            if seasons >= 6:
                context_bonus -= 0.1
            if el >= 55:
                context_bonus -= 0.1
            if "slow" in (show.flags or []):
                context_bonus -= 0.08
        # creators like/dislike
        clike = set(pref.get("creators_like") or [])
        cdis = set(pref.get("creators_dislike") or [])
        if _creators(show) & clike:
            context_bonus += 0.2
            why.append("From a creator you like")
        if _creators(show) & cdis:
            context_bonus -= 0.3
        # mood knobs
        mood = pref.get("mood") or {}
        humor = int(mood.get("humor", 2)); optimism = int(mood.get("optimism", 2)); tone = int(mood.get("tone", 2))
        pacing = int(mood.get("pacing", 2)); complexity = int(mood.get("complexity", 2))
        genres = _genres(show); flags = set(show.flags or [])
        if humor >= 3 and ("comedy" in genres or "funny" in flags):
            context_bonus += 0.1
        if humor <= 1 and ("comedy" in genres or "funny" in flags):
            context_bonus -= 0.05
        if optimism >= 3 and ("optimistic" in genres or "optimistic" in flags or "hopeful" in flags):
            context_bonus += 0.1
        if optimism <= 1 and ("optimistic" in genres or "hopeful" in flags):
            context_bonus -= 0.05
        if tone >= 3 and ("cozy" in genres or "warm" in flags):
            context_bonus += 0.08
        # pacing: slow preference favors longer episodes; fast favors shorter
        if pacing <= 1 and el >= 40:
            context_bonus += 0.08
        if pacing >= 3 and el <= 35:
            context_bonus += 0.08
        if complexity >= 3 and ("prestige" in genres or "mystery" in genres):
            context_bonus += 0.06
        if complexity <= 1 and ("prestige" in genres or "mystery" in genres):
            context_bonus -= 0.06

    avail_bonus = 0.1  # AU avail assumed by presence

    fam_h = _familiarity(show, liked_genres, liked_creators)
    if vec_sim is not None:
        novelty = max(0.0, min(1.0, 0.5 * (1.0 - fam_h) + 0.5 * (1.0 - vec_sim)))
    else:
        novelty = 1.0 - fam_h

    score = sim + context_bonus + avail_bonus
    return score, why, novelty


def _label(score: float) -> str:
    if score >= 1.0:
        return "VERY GOOD"
    if score >= 0.5:
        return "ACCEPTABLE"
    return "BAD"


def recommendations_for_profiles(
    session: Session,
    profiles: list[Profile],
    intent: str,
    count: int = 6,
    like_id: str | None = None,
    seed: int | None = None,
) -> tuple[list[Scored], dict | None]:
    # Collect liked/disliked signals per profile
    liked_by_profile: dict[int, tuple[set[str], set[str]]] = {}
    liked_tags_by_profile: dict[int, set[str]] = {}
    last_note_by_profile: dict[int, str] = {}
    rating_map_by_profile: dict[int, dict[str, int]] = {}
    union_boundaries: dict = {}
    for p in profiles:
        union_boundaries.update({k: v for k, v in (p.boundaries or {}).items() if v})
        gset: set[str] = set()
        cset: set[str] = set()
        ratings = session.exec(select(Rating).where(Rating.profile_id == p.id)).all()
        for r in ratings:
            s = session.get(Show, r.show_id)
            if not s:
                continue
            if r.primary == 2:
                gset |= _genres(s)
                cset |= _creators(s)
            if r.nuance_tags:
                liked_tags_by_profile.setdefault(p.id, set()).update([t for t in r.nuance_tags if t])
            # capture notes and per-show prior
            if r.note:
                last_note_by_profile[p.id] = r.note
            rating_map_by_profile.setdefault(p.id, {})[str(r.show_id)] = int(r.primary)
        liked_by_profile[p.id] = (gset, cset)

    # Candidate pool (safe) and also track boundary violators for substitution
    all_shows = session.exec(select(Show)).all()
    safe_candidates: list[Show] = []
    violators: list[Show] = []
    # Effective age limit: strictest across selected profiles
    eff_age_limit = None
    ages = [p.age_limit for p in profiles if getattr(p, 'age_limit', None) is not None]
    if ages:
        eff_age_limit = min(int(a) for a in ages if a is not None)
    # If SQL vector is enabled and we have a profile, pre-order candidates by ANN
    neighbor_ids: list[str] = []
    # Auto-enable SQL ANN when we have enough data, or via flag
    use_sql_vec_flag = os.getenv("USE_SQL_VECTOR", "false").lower() == "true"
    use_sql_vec_auto = False
    if profiles:
        try:
            # require: >100 shows with vectors and profile vector present
            show_vec_count = session.exec(text("SELECT COUNT(*) FROM embeddings_show WHERE emb_v IS NOT NULL")).first()[0]
            pid = profiles[0].id
            prof_vec_ok = session.exec(text("SELECT 1 FROM embeddings_profile WHERE profile_id = :pid AND emb_v IS NOT NULL"), {"pid": pid}).first()
            use_sql_vec_auto = (show_vec_count or 0) >= 100 and prof_vec_ok is not None
        except Exception:
            use_sql_vec_auto = False
    use_sql_vec = (use_sql_vec_flag or use_sql_vec_auto) and bool(profiles)
    if use_sql_vec:
        try:
            pid = profiles[0].id
            rows = session.exec(text(
                """
                SELECT es.show_id
                FROM embeddings_show es, embeddings_profile ep
                WHERE ep.profile_id = :pid AND es.emb_v IS NOT NULL AND ep.emb_v IS NOT NULL
                ORDER BY es.emb_v <-> ep.emb_v
                LIMIT 400
                """
            ), {"pid": pid}).all()
            neighbor_ids = [str(r[0]) for r in rows]
        except Exception:
            neighbor_ids = []
    # Deterministic candidate ordering with vector-neighbor priority then ID tiebreaker
    if neighbor_ids:
        ordered = sorted(
            all_shows,
            key=lambda s: (
                (neighbor_ids.index(str(s.id)) if str(s.id) in neighbor_ids else 10**9),
                str(s.id),
            ),
        )
    else:
        ordered = sorted(all_shows, key=lambda s: str(s.id))

    for s in ordered:
        if len(_availability(session, s)) == 0:
            continue
        if intent == "short_tonight" and _episode_length(s) > 35:
            # still track as violator of context to allow short substitutes
            continue
        # Age/content gating: exclude items above effective age limit
        if eff_age_limit is not None:
            ar = _age_rating(s)
            if ar is not None and ar > eff_age_limit:
                continue
        if _boundary_violates(s, union_boundaries):
            violators.append(s)
            continue
        safe_candidates.append(s)

    # Score all candidates first
    scored_all: list[Scored] = []
    # For initial split, approximate using aggregate likes
    agg_g = set().union(*[gc[0] for gc in liked_by_profile.values()]) if liked_by_profile else set()
    agg_c = set().union(*[gc[1] for gc in liked_by_profile.values()]) if liked_by_profile else set()

    # Optional: pull profile vector (first profile) and show vectors
    profile_vec: list[float] | None = None
    show_vecs: dict[str, list[float]] = {}
    try:
        if profiles:
            pid = profiles[0].id
            row = session.exec(text("SELECT emb FROM embeddings_profile WHERE profile_id = :pid"), {"pid": pid}).first()
            if row and row[0]:
                profile_vec = row[0]
        rows = session.exec(text("SELECT show_id, emb FROM embeddings_show")).all()
        for r in rows:
            if r[1]:
                show_vecs[str(r[0])] = r[1]
    except Exception:
        profile_vec = None
        show_vecs = {}

    # Fallback: compute ephemeral vectors if missing
    def _tokens_from_meta(meta: dict | None) -> list[str]:
        if not meta:
            return []
        toks: list[str] = []
        for g in meta.get("genres", []) or []:
            toks.append(f"genre:{g}")
        for c in meta.get("creators", []) or []:
            toks.append(f"creator:{c}")
        el = meta.get("episode_length")
        if el is not None:
            bucket = 0 if el <= 20 else 1 if el <= 35 else 2 if el <= 45 else 3
            toks.append(f"len:{bucket}")
        region = meta.get("region")
        if region:
            toks.append(f"region:{region}")
        return toks

    def _vec(toklist: list[str]) -> list[float]:
        import hashlib, math
        dim = 384
        out = [0.0] * dim
        for t in toklist:
            h = hashlib.sha256(t.encode()).digest()
            for i in range(dim):
                out[i] += ((h[i % len(h)] / 255.0) * 2.0 - 1.0)
        norm = math.sqrt(sum(x * x for x in out)) or 1.0
        return [x / norm for x in out]

    def _cos(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        num = sum(x*y for x, y in zip(a, b))
        da = sum(x*x for x in a) ** 0.5
        db = sum(x*x for x in b) ** 0.5
        if da == 0 or db == 0:
            return 0.0
        return max(-1.0, min(1.0, num / (da * db)))

    # Anchor show (like_id) bias
    anchor_show = None
    anchor_vec: list[float] | None = None
    try:
        from uuid import UUID
        if like_id:
            anchor_show = session.get(Show, like_id)
            if anchor_show:
                sv = show_vecs.get(str(anchor_show.id))
                if sv:
                    anchor_vec = sv
    except Exception:
        anchor_show = None
        anchor_vec = None
    # Load onboarding prefs per profile and aggregate
    from .models import Event as EventModel  # type: ignore
    prefs_per_profile: dict[int, dict] = {}
    for p in profiles:
        try:
            row = session.exec(text("SELECT payload FROM events WHERE profile_id=:pid AND kind='onboarding' ORDER BY created_at DESC LIMIT 1"), {"pid": p.id}).first()
            if row and row[0]:
                prefs_per_profile[p.id] = row[0]
        except Exception:
            continue
    agg_pref: dict | None = None
    if prefs_per_profile:
        likes = set(); dislikes = set()
        mood_keys = ["tone","pacing","complexity","humor","optimism"]
        mood_sums = {k: 0 for k in mood_keys}; mood_count = 0
        ep_max = []; seasons_max = []; avoid_cliff = False; avoid_dnf = False
        for pd in prefs_per_profile.values():
            likes |= set(pd.get("creators_like") or [])
            dislikes |= set(pd.get("creators_dislike") or [])
            md = pd.get("mood") or {}
            for k in mood_keys:
                if k in md:
                    mood_sums[k] += int(md.get(k, 2))
            mood_count += 1
            cons = pd.get("constraints") or {}
            if cons.get("ep_length_max") is not None:
                ep_max.append(int(cons.get("ep_length_max")))
            if cons.get("seasons_max") is not None:
                seasons_max.append(int(cons.get("seasons_max")))
            avoid_cliff = avoid_cliff or bool(cons.get("avoid_cliffhangers"))
            avoid_dnf = avoid_dnf or bool(cons.get("avoid_dnf"))
        mood_avg = {k: (mood_sums[k] // mood_count) for k in mood_keys} if mood_count else {}
        cons_obj = {}
        if ep_max:
            cons_obj["ep_length_max"] = min(ep_max)
        if seasons_max:
            cons_obj["seasons_max"] = min(seasons_max)
        if avoid_cliff:
            cons_obj["avoid_cliffhangers"] = True
        if avoid_dnf:
            cons_obj["avoid_dnf"] = True
        agg_pref = {"creators_like": list(likes), "creators_dislike": list(dislikes), "mood": mood_avg, "constraints": cons_obj}
    for s in safe_candidates:
        vec_sim = None
        if profile_vec is not None:
            sv = show_vecs.get(str(s.id))
            if sv:
                vec_sim = (1.0 + _cos(profile_vec, sv)) / 2.0  # scale -1..1 to 0..1
        elif profiles:
            # compute ephemeral vectors
            # profile: aggregate liked ratings for first profile
            p0 = profiles[0]
            prates = session.exec(select(Rating).where(Rating.profile_id == p0.id)).all()
            ptoks: list[str] = []
            for r in prates:
                sh = session.get(Show, r.show_id)
                if not sh:
                    continue
                w = 2 if r.primary == 2 else (1 if r.primary == 1 else -1)
                ptoks.extend(_tokens_from_meta(sh.metadata) * max(1, abs(w)))
            pvec = _vec(ptoks) if ptoks else None
            if pvec:
                svec = _vec(_tokens_from_meta(s.metadata))
                vec_sim = (1.0 + _cos(pvec, svec)) / 2.0
        sc, why, nov = _score_show(s, intent, agg_g, agg_c, vec_sim, pref=agg_pref)
        # Apply feedback nudges + deterministic micro-jitter
        # Aggregate liked tags, notes, and priors across the selected profiles
        agg_tags = set().union(*liked_tags_by_profile.values()) if liked_tags_by_profile else set()
        notes_text = "\n".join([last_note_by_profile.get(pid, "") for pid in last_note_by_profile.keys()])
        priors = []
        for pid in rating_map_by_profile.keys():
            pri = rating_map_by_profile[pid].get(str(s.id))
            if pri is not None:
                priors.append(int(pri))
        # Build recent history adjacency once per request (first iteration triggers; reuse closure variable)
        try:
            history_recent_obj
        except NameError:
            try:
                from .history_adj import recent_for_profiles as _recent
                history_recent_obj = _recent(session, profiles)
            except Exception:
                history_recent_obj = None

        sc, _ff = _apply_feedback(
            show=s,
            base_score=sc,
            seed=seed,
            liked_tags=agg_tags,
            notes_text=notes_text,
            rating_priors=priors,
            history_recent=history_recent_obj,
            intent=intent,
        )
        
        # Anchor similarity bonus
        if anchor_show and anchor_show.id != s.id:
            bonus = 0.0
            if anchor_vec is not None and str(s.id) in show_vecs:
                sim = (1.0 + _cos(anchor_vec, show_vecs[str(s.id)])) / 2.0
                bonus += 0.25 * sim
            else:
                # heuristic: genres overlap and episode length proximity
                g = len(_genres(s) & _genres(anchor_show))
                dl = abs(_episode_length(s) - _episode_length(anchor_show))
                bonus += max(0.0, min(0.25, 0.05 * g - 0.005 * dl))
            sc += bonus
            why = ([f"Similar to {anchor_show.title}"] + why)[:3]
        scored_all.append(Scored(show=s, score=sc, why=why, novelty=nov, vec_sim=vec_sim, factors=_ff))

    # Comfort vs Discovery split by novelty threshold (lower novelty => comfort)
    novelty_threshold = 0.6 if intent != "surprise" else 0.4
    comfort = [x for x in scored_all if x.novelty <= novelty_threshold]
    discovery = [x for x in scored_all if x.novelty > novelty_threshold]
    # Deterministic sort with explicit tiebreakers
    comfort.sort(key=lambda x: (-x.score, x.novelty, str(x.show.id)))
    discovery.sort(key=lambda x: (-x.score, -x.novelty, str(x.show.id)))

    # Targets per intent
    picked: list[Scored] = []
    if intent == "comfort":
        # Aim for all comfort; cap discovery padding at <=10% of total
        d_cap = max(0, int(count * 0.1))
        picked = comfort[:count]
        if len(picked) < count and discovery:
            need = count - len(picked)
            picked += discovery[: min(d_cap, need)]
    else:
        # Default deterministic split: ~70/30; Surprise: ~40/60
        if intent == "surprise":
            c_target = max(0, round(count * 0.4))
        else:
            c_target = max(0, round(count * 0.7))
        d_target = max(0, count - c_target)
        c_take = min(c_target, len(comfort))
        d_take = min(d_target, len(discovery))
        picked = comfort[:c_take] + discovery[:d_take]

    # Family Mix: if multiple profiles, compute Pareto frontier across members and rank by mean - lam*stdev
    family_meta: dict | None = None
    if len(profiles) > 1:
        # Build per-profile liked sets once
        per_profile_gc = {p.id: liked_by_profile.get(p.id, (set(), set())) for p in profiles}

        # Per-candidate per-profile score map
        per_scores_map: dict[str, list[float]] = {}
        for sc in scored_all:
            scores: list[float] = []
            for p in profiles:
                gset, cset = per_profile_gc.get(p.id, (set(), set()))
                ps, _, _ = _score_show(sc.show, intent, gset, cset)
                scores.append(ps)
            per_scores_map[str(sc.show.id)] = scores

        # Pareto frontier: keep items not dominated by any other
        def dominated(a: list[float], b: list[float]) -> bool:
            # a is dominated by b if b >= a for all dims and b > a for at least one
            ge_all = all(bi >= ai for ai, bi in zip(a, b))
            gt_any = any(bi > ai for ai, bi in zip(a, b))
            return ge_all and gt_any

        frontier: list[Scored] = []
        for sc in scored_all:
            a = per_scores_map[str(sc.show.id)]
            dom = False
            for other in scored_all:
                if other.show.id == sc.show.id:
                    continue
                b = per_scores_map[str(other.show.id)]
                if dominated(a, b):
                    dom = True
                    break
            if not dom:
                frontier.append(sc)

        # rank frontier by mean - lam*stdev and filter extreme low fits
        lam = 0.5
        rescored: list[Scored] = []
        prof_names = [ (p.id, (p.name.value if hasattr(p.name, 'value') else str(p.name))) for p in profiles ]
        for sc in frontier:
            scores = per_scores_map[str(sc.show.id)]
            if any(s < 0.2 for s in scores):
                continue
            m = mean(scores)
            sdev = pstdev(scores) if len(scores) > 1 else 0.0
            fits = { name: float(scores[idx]) for idx, (pid, name) in enumerate(prof_names) }
            rescored.append(Scored(show=sc.show, score=m - lam * sdev, why=sc.why, novelty=sc.novelty, vec_sim=sc.vec_sim, fits=fits))
        # Mark strong-for-family on rescored items
        for i, sc in enumerate(rescored):
            rescored[i].is_family_strong = is_strong_for_family(sc.fits or {})

        rescored.sort(key=lambda x: x.score, reverse=True)
        # Pre-lock strong candidates (up to configured count)
        strong_cands = [sc for sc in rescored if sc.is_family_strong]
        strong_cands.sort(key=lambda x: (_family_fit_agg(x.fits or {}), x.score), reverse=True)
        lock_n = max(0, min(int(settings.family_strong_lock_count or 0), count))
        locked: list[Scored] = strong_cands[:lock_n] if lock_n else []
        # Build initial picked slate: locked first, then fill from rescored
        picked = []
        seen_ids = set()
        for sc in locked:
            if sc.show.id not in seen_ids and len(picked) < count:
                picked.append(sc)
                seen_ids.add(sc.show.id)
        for sc in rescored:
            if sc.show.id in seen_ids:
                continue
            if len(picked) < count:
                picked.append(sc)
                seen_ids.add(sc.show.id)

        # Fairness coverage: try to ensure each profile has at least one item with reasonable fit
        # Threshold is configurable via FAMILY_COVERAGE_MIN_FIT (default 0.4)
        try:
            coverage_threshold = float(os.getenv("FAMILY_COVERAGE_MIN_FIT", "0.4"))
        except Exception:
            coverage_threshold = 0.4
        logger = logging.getLogger("recs.family")
        for idx_p, (pid, name) in enumerate(prof_names):
            has_cover = any((sc.fits or {}).get(name, 0.0) >= coverage_threshold for sc in picked)
            if not has_cover:
                # find best candidate for this profile not already picked
                best_for_p = None
                best_score = -1e9
                for sc in rescored:
                    if sc in picked:
                        continue
                    s_for_p = (sc.fits or {}).get(name)
                    if s_for_p is None:
                        continue
                    # prefer items meeting threshold; otherwise take highest
                    key = (1 if s_for_p >= coverage_threshold else 0, s_for_p, sc.score)
                    if key > (1 if best_score >= coverage_threshold else 0, best_score, -1e9):
                        best_for_p = sc
                        best_score = s_for_p
                if best_for_p is not None:
                    if len(picked) < count:
                        picked.append(best_for_p)
                        try:
                            logger.info(
                                "family_coverage_add",
                                extra={
                                    "member": name,
                                    "threshold": coverage_threshold,
                                    "show_id": str(best_for_p.show.id),
                                    "score": float(best_for_p.score),
                                    "fit": float((best_for_p.fits or {}).get(name, 0.0)),
                                },
                            )
                        except Exception:
                            pass
                    else:
                        # replace the tail item with lowest fit for this profile
                        worst_idx = None
                        worst_fit = 1e9
                        for i, sc in enumerate(picked):
                            s_for_p = (sc.fits or {}).get(name, 0.0)
                            if s_for_p < worst_fit:
                                worst_fit = s_for_p
                                worst_idx = i
                        if worst_idx is not None:
                            try:
                                logger.info(
                                    "family_coverage_swap",
                                    extra={
                                        "member": name,
                                        "threshold": coverage_threshold,
                                        "out_show_id": str(picked[worst_idx].show.id),
                                        "out_fit": float((picked[worst_idx].fits or {}).get(name, 0.0)),
                                        "in_show_id": str(best_for_p.show.id),
                                        "in_fit": float((best_for_p.fits or {}).get(name, 0.0)),
                                    },
                                )
                            except Exception:
                                pass
                            picked[worst_idx] = best_for_p
        # Re-sort by combined score deterministically after adjustments
        picked.sort(key=lambda x: (-x.score, str(x.show.id)))

        # Family meta for explain=true
        try:
            family_meta = {
                "strong_locked_ids": [str(c.show.id) for c in locked],
                "warning": None if locked else {
                    "code": "no_strong_pick",
                    "message": "No single title clears the strong-fit bar for everyone; showing best shared options.",
                },
                "strong_min_fit": float(settings.family_strong_min_fit),
                "strong_rule": str(settings.family_strong_rule),
            }
        except Exception:
            family_meta = None

    # If we are short, pad with more discovery (or comfort) as available
    if len(picked) < count:
        remaining = count - len(picked)
        # Fill from whichever pool still has items, deterministically
        extra_c = [x for x in comfort if x not in picked]
        extra_d = [x for x in discovery if x not in picked]
        # For non-comfort intents, prefer discovery first to maintain variety
        if intent != "comfort" and extra_d:
            take = min(remaining, len(extra_d))
            picked += extra_d[:take]
            remaining -= take
        if remaining > 0 and extra_c:
            take = min(remaining, len(extra_c))
            picked += extra_c[:take]
            remaining -= take
        # For comfort intent, we already applied discovery cap above, so only fill with comfort here

    # Boundary substitutes: find top-scoring violators (scored ignoring boundaries)
    # and prepare up to two similar boundary-safe alternatives to include in final set
    substitutes: list[Scored] = []
    if violators:
        scored_violators: list[Tuple[Show, float]] = []
        for v in violators:
            sv, _, _ = _score_show(v, intent, agg_g, agg_c)
            scored_violators.append((v, sv))
        scored_violators.sort(key=lambda t: t[1], reverse=True)

        def sim(a: Show, b: Show) -> float:
            g = len(_genres(a) & _genres(b))
            dl = abs(_episode_length(a) - _episode_length(b))
            return g - 0.02 * dl

        for v, _ in scored_violators[:2]:
            cands = sorted(
                [s for s in safe_candidates if s not in [sc.show for sc in picked] and s not in [sub.show for sub in substitutes]],
                key=lambda s: sim(v, s),
                reverse=True,
            )
            for s in cands[:1]:  # one alt per violator
                scv, why, nov = _score_show(s, intent, agg_g, agg_c)
                substitutes.append(Scored(show=s, score=scv + 0.05, why=["Boundary-safe alternative"] + why, novelty=nov, vec_sim=None))

    # Ensure up to 2 substitutes are present by replacing from the tail
    if substitutes:
        # unique by show id
        seen = set()
        uniq_subs = []
        for sub in substitutes:
            if sub.show.id not in seen:
                uniq_subs.append(sub)
                seen.add(sub.show.id)
        for i, sub in enumerate(uniq_subs[:2]):
            if len(picked) < count:
                picked.append(sub)
            else:
                picked[-(i+1)] = sub

    # Final: limit to count
    picked = picked[:count]

    # Build rationale text with explicit evidence
    def _rationale_for(sc: Scored) -> tuple[str, list[str]]:
        # New standardized rationale builder; fallback to safe generic on lint error
        try:
            txt = build_rationale(sc.show, sc.factors, profiles[0] if profiles else None)
        except SpoilerError:
            txt = "A well-matched pick based on your tastes."
        # Append season/provider hint when safe and applicable
        try:
            avails = _availability(session, sc.show)
            offers = [
                {
                    "provider": a.platform,
                    "offer_type": a.offer_type.value if hasattr(a.offer_type, 'value') else str(a.offer_type),
                    "last_checked_ts": a.updated_at,
                    # Season unknown at per-offer granularity in current model
                    "season": None,
                }
                for a in avails
            ]
            chosen = pick_season_consistent_offer(offers, season=None)
            prov = chosen.get("provider") if chosen else None
            season = chosen.get("season") if chosen else None
            if prov and isinstance(season, int):
                txt = f"{txt} (showing S{season} on {prov})"
            # If we don't know season, avoid adding a hint to prevent spoilers/noise
        except Exception:
            pass
        # Evidence chips remain as before, trimmed
        bits: list[str] = []
        agg_g = set().union(*[v[0] for v in liked_by_profile.values()]) if liked_by_profile else set()
        agg_c = set().union(*[v[1] for v in liked_by_profile.values()]) if liked_by_profile else set()
        creators = list(_creators(sc.show) & agg_c)
        if creators:
            bits.append(f"From creator(s) {', '.join(creators[:2])}")
        gmatch = list(_genres(sc.show) & agg_g)
        if gmatch:
            bits.append(f"Shares your taste for {', '.join(gmatch[:2])}")
        return txt, bits

    for i, sc in enumerate(picked):
        rationale, bits = _rationale_for(sc)
        picked[i].rationale = rationale
        picked[i].evidence = bits[:3]

    return picked, family_meta
