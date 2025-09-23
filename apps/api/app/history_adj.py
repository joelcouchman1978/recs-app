from __future__ import annotations

from typing import Iterable
from sqlmodel import Session, select
from sqlalchemy import text
from .models import Show


class HistoryRecent:
    """Minimal structure extracted from recent Serializd rows to test adjacency.

    In this codebase, we do not yet persist creators/genres in the serializd table,
    so callers should pre-join/shape rows to include these fields when available.
    Passing an empty set is safe and results in no adjacency boost.
    """

    def __init__(self, rows: Iterable[dict] | None):
        self.creators = set()
        self.genres = set()
        for r in rows or []:
            self.creators.update(r.get("creators", []) or [])
            self.genres.update(r.get("genres", []) or [])

    def is_adjacent(self, item) -> bool:
        ic = set(getattr(item, "metadata", {}).get("creators", []) or [])
        ig = set(getattr(item, "metadata", {}).get("genres", []) or [])
        return bool(self.creators & ic or self.genres & ig)


def recent_for_profiles(session: Session, profiles: list) -> "HistoryRecent":
    """Fetch recent Serializd rows for given profiles and map to creators/genres via title match.
    Best-effort: joins by exact Show.title; if no matches, returns empty sets.
    """
    names = []
    try:
        # Use profile names as refs when available (e.g., Ross/Wife/Son)
        for p in profiles:
            nm = getattr(p, "name", None)
            if hasattr(nm, 'value'):
                names.append(nm.value)
            elif isinstance(nm, str):
                names.append(nm)
    except Exception:
        names = []
    rows: list[dict] = []
    try:
        # Recent 50 entries overall (filter by profile_ref if names set)
        if names:
            q = text("""
                SELECT sh.title_ref, sh.last_seen_ts
                FROM serializd_history sh
                WHERE sh.profile_ref = ANY(:names)
                ORDER BY sh.last_seen_ts DESC
                LIMIT 50
            """)
            res = session.exec(q, {"names": names}).all()
        else:
            q = text("SELECT title_ref, last_seen_ts FROM serializd_history ORDER BY last_seen_ts DESC LIMIT 50")
            res = session.exec(q).all()
        title_refs = [r[0] for r in res if r and r[0]]
        if not title_refs:
            return HistoryRecent([])
        # Map titles to creators/genres
        for t in title_refs:
            s = session.exec(select(Show).where(Show.title == t)).first()
            if s:
                rows.append({
                    "creators": (s.metadata or {}).get("creators", []) or [],
                    "genres": (s.metadata or {}).get("genres", []) or [],
                })
    except Exception:
        pass
    return HistoryRecent(rows)
