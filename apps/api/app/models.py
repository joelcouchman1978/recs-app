from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import JSON
from sqlmodel import SQLModel, Field, Relationship

from .settings import settings

try:
    from sqlalchemy.dialects.postgresql import JSONB, ARRAY
except ImportError:  # pragma: no cover - optional dependency
    JSONB = None
    ARRAY = None

if settings.use_sqlite:
    JSONType = JSON

    def _array_type(item_type=str):
        return JSON
else:
    JSONType = JSONB if JSONB is not None else JSON

    def _array_type(item_type=str):
        if ARRAY is None:
            return JSON
        return ARRAY(item_type=item_type)


class ProfileName(str, enum.Enum):
    Ross = "Ross"
    Wife = "Wife"
    Son = "Son"


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    profiles: list[Profile] = Relationship(back_populates="user")  # type: ignore


class Profile(SQLModel, table=True):
    __tablename__ = "profiles"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    name: ProfileName
    age_limit: Optional[int] = None
    boundaries: dict = Field(default_factory=dict, sa_column_kwargs={"type_": JSONType})
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional[User] = Relationship(back_populates="profiles")


class Show(SQLModel, table=True):
    __tablename__ = "shows"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    jw_id: Optional[int] = None
    metadata: dict = Field(default_factory=dict, sa_column_kwargs={"type_": JSONType})
    warnings: list = Field(default_factory=list, sa_column_kwargs={"type_": JSONType})
    flags: list = Field(default_factory=list, sa_column_kwargs={"type_": JSONType})
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OfferType(str, enum.Enum):
    stream = "stream"
    rent = "rent"
    buy = "buy"


class Quality(str, enum.Enum):
    SD = "SD"
    HD = "HD"
    _4K = "4K"


class Availability(SQLModel, table=True):
    __tablename__ = "availability"
    id: Optional[int] = Field(default=None, primary_key=True)
    show_id: uuid.UUID = Field(foreign_key="shows.id")
    platform: str
    offer_type: OfferType
    quality: Optional[Quality] = None
    price_cents: Optional[int] = None
    leaving_at: Optional[datetime] = None
    added_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Rating(SQLModel, table=True):
    __tablename__ = "ratings"
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profiles.id")
    show_id: uuid.UUID = Field(foreign_key="shows.id")
    primary: int = Field(ge=0, le=2, description="0=BAD,1=ACCEPTABLE,2=VERY GOOD")
    nuance_tags: Optional[List[str]] = Field(default=None, sa_column_kwargs={"type_": _array_type(item_type=str)})
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EmbeddingShow(SQLModel, table=True):
    __tablename__ = "embeddings_show"
    show_id: uuid.UUID = Field(foreign_key="shows.id", primary_key=True)
    emb: list[float] = Field(sa_column_kwargs={"type_": _array_type(item_type=float)})


class EmbeddingProfile(SQLModel, table=True):
    __tablename__ = "embeddings_profile"
    profile_id: int = Field(foreign_key="profiles.id", primary_key=True)
    emb: list[float] = Field(sa_column_kwargs={"type_": _array_type(item_type=float)})


class Watchlist(SQLModel, table=True):
    __tablename__ = "watchlist"
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="profiles.id")
    show_id: uuid.UUID = Field(foreign_key="shows.id")
    added_at: datetime = Field(default_factory=datetime.utcnow)


class Event(SQLModel, table=True):
    __tablename__ = "events"
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int
    kind: str
    payload: dict = Field(default_factory=dict, sa_column_kwargs={"type_": JSONType})
    created_at: datetime = Field(default_factory=datetime.utcnow)

