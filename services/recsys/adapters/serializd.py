from __future__ import annotations

import os
from typing import Any, Dict, List

import requests
from .util import with_backoff
from .types import HistoryItem
from datetime import datetime, timezone


class SerializdAdapter:
    def __init__(self):
        self.enabled = os.getenv("USE_REAL_SERIALIZD", "false").lower() == "true"
        self.user = os.getenv("SERIALIZD_USER")
        self.token = os.getenv("SERIALIZD_TOKEN")

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def ratings(self) -> List[Dict[str, Any]]:
        if not self.enabled or not (self.user and self.token):
            return []
        try:
            # Placeholder endpoint; replace with Serializd API if available
            r = with_backoff(lambda: requests.get(f"https://api.serializd.com/users/{self.user}/ratings", headers=self._headers(), timeout=10))
            if isinstance(r, requests.Response):
                r.raise_for_status()
                data = r.json()
            else:
                data = r
            return data if isinstance(data, list) else []
        except Exception:
            try:
                from apps.api.app.metrics import ADAPTER_ERRORS  # type: ignore
                ADAPTER_ERRORS.labels(adapter="serializd").inc()
            except Exception:
                pass
            return []

    def fetch_watch_history(self) -> List[HistoryItem]:
        """Normalize ratings into HistoryItems (best-effort)"""
        out: List[HistoryItem] = []
        if not self.enabled or not (self.user and self.token):
            return out
        data = self.ratings()
        now = datetime.now(timezone.utc)
        for item in data:
            title = (item.get("title") or "").strip()
            rating = item.get("rating")
            out.append(HistoryItem(
                profile_ref=self.user or "",
                title_ref=title or None,
                tmdb_id=(item.get("ids") or {}).get("tmdb") if isinstance(item.get("ids"), dict) else None,
                season=None,
                episode=None,
                status="watched",
                rating=int(rating) if isinstance(rating, int) else None,
                last_seen_ts=now,
                raw=item,
            ))
        return out

    @staticmethod
    def to_internal_rating(item: Dict[str, Any]) -> Dict[str, Any]:
        """Map a Serializd rating record to our internal shape.
        Expected fields (best-effort): title, year, rating (0-10), ids: { imdb?, tmdb? }.
        """
        title = (item.get("title") or "").strip()
        year = item.get("year")
        rating = item.get("rating")
        ids = item.get("ids") or {}
        return {
            "title": title,
            "year": year,
            "rating": rating,
            "imdb_id": ids.get("imdb"),
            "tmdb_id": ids.get("tmdb"),
        }
