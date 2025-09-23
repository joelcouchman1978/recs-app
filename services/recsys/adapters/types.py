from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

OfferType = Literal["stream", "rent", "buy"]


@dataclass
class Offer:
    title_ref: str
    provider: str
    offer_type: OfferType
    price: float | None
    currency: str | None
    region: str
    last_checked_ts: datetime
    raw: dict[str, Any] | None = None
    season: int | None = None


@dataclass
class HistoryItem:
    profile_ref: str
    title_ref: str | None
    tmdb_id: int | None
    season: int | None
    episode: int | None
    status: str  # watched|watching|dropped
    rating: int | None
    last_seen_ts: datetime
    raw: dict[str, Any] | None = None
