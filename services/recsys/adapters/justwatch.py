from __future__ import annotations

import os
from typing import Any, Dict, List

import requests
from .util import with_backoff
from .types import Offer
from datetime import datetime, timezone


class JustWatchAdapter:
    def __init__(self, region: str = "AU"):
        self.region = region
        self.enabled = os.getenv("USE_REAL_JUSTWATCH", "false").lower() == "true"
        # Minimal AU provider ID → name map (placeholder; adjust with real IDs)
        self.provider_map = {
            8: "Netflix",
            24: "Prime Video",
            179: "Disney+",
            37: "Stan",
            387: "Binge",
            350: "Apple TV+",
            85: "SBS On Demand",
            84: "ABC iView",
            382: "BritBox",
            337: "Paramount+",
            119: "YouTube",
            3: "Google Play",
            10: "Apple iTunes",
            167: "Foxtel Now",
            308: "Kayo Sports",
            56: "Microsoft Store",
            35: "Fetch",
            146: "Rakuten TV",
        }
        # Allow override/extension via env JUSTWATCH_PROVIDER_MAP={"id":"Name",...}
        try:
            import json
            raw = os.getenv("JUSTWATCH_PROVIDER_MAP")
            if raw:
                override = json.loads(raw)
                for k, v in override.items():
                    try:
                        self.provider_map[int(k)] = str(v)
                    except Exception:
                        continue
        except Exception:
            pass
        # simple in-memory caches (per-process)
        self._title_cache: dict[tuple[str, int | None], dict | None] = {}
        self._offers_cache: dict[int, list[dict]] = {}

    def _locale(self) -> str:
        return "en_AU" if self.region.upper() == "AU" else "en_US"

    def search_title(self, title: str, year: int | None = None) -> dict | None:
        if not self.enabled:
            return None
        # Note: Official API is private; many use public web endpoints. This is a placeholder.
        # In real usage, adapt to a maintained wrapper or partner API.
        key = (title, year)
        if key in self._title_cache:
            return self._title_cache[key]
        try:
            r = with_backoff(lambda: requests.get(
                "https://apis.justwatch.com/content/titles/", timeout=10,
                params={"language": self._locale(), "q": title},
            ))
            if isinstance(r, requests.Response):
                r.raise_for_status()
                data = r.json()
            else:
                data = r
            items = data.get("items", [])
            if year:
                items = [i for i in items if i.get("original_release_year") == year]
            item = items[0] if items else None
            self._title_cache[key] = item
            return item
        except Exception:
            try:
                from apps.api.app.metrics import ADAPTER_ERRORS  # type: ignore
                ADAPTER_ERRORS.labels(adapter="justwatch").inc()
            except Exception:
                pass
            self._title_cache[key] = None
            return None

    def availability(self, jw_id: int | None = None, title: str | None = None, year: int | None = None) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        try:
            if not jw_id:
                item = self.search_title(title or "", year)
                jw_id = item.get("id") if item else None
            if not jw_id:
                return []
            if jw_id in self._offers_cache:
                offers = self._offers_cache[jw_id]
            else:
                r = with_backoff(lambda: requests.get(
                    f"https://apis.justwatch.com/content/titles/show/{jw_id}/locale/{self._locale()}",
                    timeout=10,
                ))
                if isinstance(r, requests.Response):
                    r.raise_for_status()
                    offers = (r.json() or {}).get("offers", [])
                else:
                    offers = (r or {}).get("offers", [])
                self._offers_cache[jw_id] = offers
            out = []
            for o in offers:
                if o.get("monetization_type") not in ("flatrate", "rent", "buy"):
                    continue
                pid = o.get("provider_id")
                platform = self.provider_map.get(pid, f"provider_{pid}")
                mtype = o.get("monetization_type")
                offer_type = "stream" if mtype == "flatrate" else ("rent" if mtype == "rent" else ("buy" if mtype == "buy" else None))
                pres = (o.get("presentation_type") or "").upper()
                quality = "4K" if "4K" in pres else ("HD" if "HD" in pres else ("SD" if pres else None))
                out.append({
                    "platform": platform,
                    "offer_type": offer_type,
                    "quality": quality,
                    "leaving_at": None,  # calculate from end dates if exposed
                })
            return out
        except Exception:
            try:
                from apps.api.app.metrics import ADAPTER_ERRORS  # type: ignore
                ADAPTER_ERRORS.labels(adapter="justwatch").inc()
            except Exception:
                pass
            return []

    def fetch_offers(self, title_ref: str, region: str = "AU") -> list[Offer]:
        """Normalize offers for a given title_ref (using existing availability flow as source).
        title_ref may be a known jw_id or resolvable via title/year before calling.
        """
        now = datetime.now(timezone.utc)
        offers = []
        try:
            # Try interpret title_ref as int jw_id first
            jw_id = None
            try:
                jw_id = int(title_ref)
            except Exception:
                jw_id = None
            raw = self.availability(jw_id=jw_id, title=title_ref if jw_id is None else None)
            for o in raw:
                offers.append(Offer(
                    title_ref=title_ref,
                    provider=o.get("platform", "unknown"),
                    offer_type=o.get("offer_type", "stream"),
                    price=None,
                    currency=None,
                    region=region,
                    last_checked_ts=now,
                    raw=o,
                ))
        except Exception:
            try:
                from apps.api.app.metrics import ADAPTER_ERRORS  # type: ignore
                ADAPTER_ERRORS.labels(adapter="justwatch").inc()
            except Exception:
                pass
            return []
        return offers

    def map_show_identifiers(self, meta: dict | None) -> dict:
        """Return best-effort mapping payload for a Show row's metadata
        that can help locate the title (e.g., tmdb_id/imdb_id), if available.
        Currently returns noop; extend when a stable endpoint is available.
        """
        meta = meta or {}
        return {
            "tmdb_id": meta.get("tmdb_id"),
            "imdb_id": meta.get("imdb_id"),
        }
