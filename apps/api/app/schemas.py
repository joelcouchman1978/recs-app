from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class MagicLinkRequest(BaseModel):
    email: str


class MagicLinkResponse(BaseModel):
    token: str


class ProfileCreate(BaseModel):
    name: str
    age_limit: Optional[int] = None
    boundaries: dict = Field(default_factory=dict)


class ProfileOut(BaseModel):
    id: int
    name: str
    age_limit: Optional[int]
    boundaries: dict


class RatingCreate(BaseModel):
    profile_id: int
    show_id: str
    primary: int
    nuance_tags: Optional[List[str]] = None
    note: Optional[str] = None


class WhereToWatch(BaseModel):
    platform: str
    offer_type: str


class Prediction(BaseModel):
    label: str
    c: float
    n: float


class RecommendationItem(BaseModel):
    id: str
    title: str
    year: Optional[int] = None
    where_to_watch: List[WhereToWatch]
    rationale: str
    warnings: List[str]
    flags: List[str]
    prediction: Prediction
    similar_because: List[str] = []
    genres: List[str] = []
    creators: List[str] = []
    au_rating: Optional[str] = None
    age_rating: Optional[int] = None
    fit_by_profile: Optional[list[dict]] = None
    availability: Optional[dict] = None
    family_strong: Optional[bool] = None
