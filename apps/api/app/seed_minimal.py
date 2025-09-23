from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, select

from .db import init_db, get_engine
from .models import Availability, OfferType, Profile, ProfileName, Show, User

def seed_minimal() -> None:
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == "sandbox@local.test")).first()
        if user is None:
            user = User(email="sandbox@local.test")
            session.add(user)
            session.flush()
        existing_profiles = {
            p.name for p in session.exec(select(Profile).where(Profile.user_id == user.id)).all()
        }
        for pname in ProfileName:
            if pname not in existing_profiles:
                session.add(Profile(user_id=user.id, name=pname, boundaries={}))

        shows = [
            {
                "slug": "cozy-bakery",
                "title": "Cozy Bakery",
                "genres": ["comedy", "family"],
                "creators": ["Jo Dough"],
                "episode_length": 28,
                "seasons": 2,
                "au_rating": "PG",
                "flags": ["cozy", "optimistic"],
                "warnings": [],
            },
            {
                "slug": "mystery-harbor",
                "title": "Mystery Harbor",
                "genres": ["mystery", "drama"],
                "creators": ["Alex Shore"],
                "episode_length": 45,
                "seasons": 3,
                "au_rating": "M",
                "flags": ["tense"],
                "warnings": ["dark"],
            },
            {
                "slug": "science-frontier",
                "title": "Science Frontier",
                "genres": ["documentary", "science"],
                "creators": ["Dr. Lin"],
                "episode_length": 35,
                "seasons": 1,
                "au_rating": "G",
                "flags": ["optimistic"],
                "warnings": [],
            },
            {
                "slug": "rebound",
                "title": "Rebound",
                "genres": ["sports", "comedy"],
                "creators": ["Casey Quick"],
                "episode_length": 24,
                "seasons": 4,
                "au_rating": "PG",
                "flags": ["humorous"],
                "warnings": [],
            },
            {
                "slug": "stellar-siblings",
                "title": "Stellar Siblings",
                "genres": ["sci-fi", "family"],
                "creators": ["Nia Orbit"],
                "episode_length": 38,
                "seasons": 2,
                "au_rating": "PG",
                "flags": ["hopeful"],
                "warnings": ["mild peril"],
            },
            {
                "slug": "noir-notes",
                "title": "Noir Notes",
                "genres": ["thriller", "mystery"],
                "creators": ["Jamie Keys"],
                "episode_length": 50,
                "seasons": 1,
                "au_rating": "MA15+",
                "flags": ["stylish"],
                "warnings": ["violence"],
            },
        ]

        now = datetime.utcnow()
        for spec in shows:
            show = session.exec(select(Show).where(Show.title == spec["title"])).first()
            if show is None:
                show = Show(
                    title=spec["title"],
                    year_start=2021,
                    metadata={
                        "genres": spec["genres"],
                        "creators": spec["creators"],
                        "episode_length": spec["episode_length"],
                        "seasons": spec["seasons"],
                        "au_rating": spec["au_rating"],
                    },
                    warnings=spec["warnings"],
                    flags=spec["flags"],
                )
                session.add(show)
                session.flush()
            has_avail = session.exec(select(Availability).where(Availability.show_id == show.id)).first()
            if has_avail is None:
                session.add(
                    Availability(
                        show_id=show.id,
                        platform="SandboxFlix",
                        offer_type=OfferType.stream,
                        updated_at=now,
                    )
                )
        session.commit()


if __name__ == "__main__":
    seed_minimal()
