from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlmodel import Session, select

from .db import engine
from .models import (
    Availability,
    OfferType,
    Profile,
    ProfileName,
    Show,
    User,
    Quality,
)


def upsert_user_with_profiles(session: Session, email: str):
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        user = User(email=email)
        session.add(user)
        session.commit()
        session.refresh(user)

    for name in [ProfileName.Ross, ProfileName.Wife, ProfileName.Son]:
        prof = session.exec(select(Profile).where(Profile.user_id == user.id, Profile.name == name)).first()
        if not prof:
            boundaries = {}
            age_limit = None
            if name == ProfileName.Wife:
                boundaries = {"violence": True}
            if name == ProfileName.Son:
                age_limit = 13
                boundaries = {"drug_abuse": True}
            prof = Profile(user_id=user.id, name=name, age_limit=age_limit, boundaries=boundaries)
            session.add(prof)
    session.commit()


def seed_shows(session: Session):
    if session.exec(select(Show)).first():
        return

    platforms = [
        "Netflix",
        "Stan",
        "Binge",
        "Prime Video",
        "ABC iView",
        "SBS On Demand",
        "Disney+",
        "Apple TV+",
        "BritBox",
    ]
    creators_sets = [
        ["S. Waller", "K. Ng"],
        ["A. Kaur", "M. Li"],
        ["T. O’Neill"],
        ["R. Fraser", "L. Zhang"],
        ["P. Singh"],
        ["J. Kim", "E. Ritchie"],
    ]
    archetypes = [
        {"genres": ["mystery", "cozy"], "flags": ["clever dialogue", "humane worldview"], "warnings": ["mild peril"], "episode_length": 30, "age_rating": 12, "au_rating": "PG"},
        {"genres": ["procedural", "comedy"], "flags": ["strong ensemble", "cozy"], "warnings": ["language"], "episode_length": 22, "age_rating": 12, "au_rating": "PG"},
        {"genres": ["sci-fi", "optimistic"], "flags": ["hopeful", "inventive"], "warnings": [], "episode_length": 42, "age_rating": 14, "au_rating": "M"},
        {"genres": ["animation", "family"], "flags": ["gentle", "short episodes"], "warnings": [], "episode_length": 12, "age_rating": 8, "au_rating": "G"},
        {"genres": ["drama", "prestige"], "flags": ["award-winning"], "warnings": ["violence"], "episode_length": 58, "age_rating": 16, "au_rating": "MA15+"},
        {"genres": ["doc", "uplifting"], "flags": ["humane worldview"], "warnings": [], "episode_length": 30, "age_rating": 10, "au_rating": "PG"},
    ]

    now = datetime.utcnow()
    year = 2014
    idx = 1
    for i in range(60):
        arch = archetypes[i % len(archetypes)].copy()
        creators = creators_sets[i % len(creators_sets)]
        title = f"Show {idx:02d} - {'/'.join(arch['genres']).title()}"
        meta = {
            "genres": arch["genres"],
            "episode_length": arch["episode_length"],
            "seasons": 1 + (i % 5),
            "region": "AU" if i % 3 == 0 else "US",
            "creators": creators,
            "synopsis": f"Spoiler-safe overview of {title} with tone and premise.",
            "age_rating": arch.get("age_rating"),
            "au_rating": arch.get("au_rating"),
        }
        s = Show(
            id=uuid.uuid4(),
            title=title,
            year_start=year + (i % 10),
            metadata=meta,
            warnings=arch["warnings"],
            flags=arch["flags"],
        )
        session.add(s)
        session.commit()
        plats = [platforms[(i + j) % len(platforms)] for j in range(1 if i % 2 == 0 else 2)]
        for plat in plats:
            a = Availability(
                show_id=s.id,
                platform=plat,
                offer_type=OfferType.stream,
                quality=Quality.HD,
                added_at=now - timedelta(days=(i % 15)),
                leaving_at=(now + timedelta(days=7 + (i % 5))) if plat in ("Netflix", "Stan") and i % 7 == 0 else None,
            )
            session.add(a)
        session.commit()
        idx += 1


def main():
    with Session(engine) as session:
        upsert_user_with_profiles(session, "demo@local.test")
        seed_shows(session)
        # Seed a few preference signals: Ross likes cozy & procedural, Wife likes cozy & family, Son likes animation & sci-fi
        from .models import Rating
        ross = session.exec(select(Profile).where(Profile.name == ProfileName.Ross)).first()
        wife = session.exec(select(Profile).where(Profile.name == ProfileName.Wife)).first()
        son = session.exec(select(Profile).where(Profile.name == ProfileName.Son)).first()
        shows = session.exec(select(Show)).all()
        for s in shows[:10]:
            if ross:
                session.add(Rating(profile_id=ross.id, show_id=s.id, primary=2, nuance_tags=["cozy"]))
        for s in shows[10:15]:
            if ross:
                session.add(Rating(profile_id=ross.id, show_id=s.id, primary=0, nuance_tags=["slow"]))
        for s in shows[5:12]:
            if wife:
                session.add(Rating(profile_id=wife.id, show_id=s.id, primary=2, nuance_tags=["gentle"]))
        for s in shows[20:24]:
            if wife:
                session.add(Rating(profile_id=wife.id, show_id=s.id, primary=0, nuance_tags=["violence"]))
        for s in shows[30:36]:
            if son:
                session.add(Rating(profile_id=son.id, show_id=s.id, primary=2, nuance_tags=["funny"]))
        session.commit()
    print("Seed complete")


if __name__ == "__main__":
    main()
