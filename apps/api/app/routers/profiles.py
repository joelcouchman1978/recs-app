from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import User, Profile, ProfileName
from ..embeddings_util import rebuild_profile_embedding
from ..schemas import ProfileCreate, ProfileOut
from .utils import parse_token
from ..cache import invalidate_for_email

router = APIRouter()


@router.get("/me/profiles", response_model=list[ProfileOut])
def get_my_profiles(
    session: Session = Depends(get_session),
    authorization: str | None = Header(default=None),
):
    email = parse_token(authorization)
    if not email:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        return []
    profiles = session.exec(select(Profile).where(Profile.user_id == user.id)).all()
    return [
        ProfileOut(id=p.id, name=p.name.value if hasattr(p.name, 'value') else str(p.name), age_limit=p.age_limit, boundaries=p.boundaries)
        for p in profiles
    ]


@router.post("/profiles", response_model=list[ProfileOut])
def create_or_update_profiles(
    payload: list[ProfileCreate],
    session: Session = Depends(get_session),
    authorization: str | None = Header(default=None),
):
    email = parse_token(authorization)
    if not email:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        user = User(email=email)
        session.add(user)
        session.commit()
        session.refresh(user)

    existing = {p.name: p for p in session.exec(select(Profile).where(Profile.user_id == user.id)).all()}
    out: list[ProfileOut] = []
    for item in payload:
        try:
            name_enum = ProfileName(item.name)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid profile name: {item.name}")
        if name_enum in existing:
            prof = existing[name_enum]
            prof.age_limit = item.age_limit
            prof.boundaries = item.boundaries
        else:
            prof = Profile(user_id=user.id, name=name_enum, age_limit=item.age_limit, boundaries=item.boundaries)
            session.add(prof)
        session.commit()
        session.refresh(prof)
        try:
            rebuild_profile_embedding(session, prof.id)
        except Exception:
            pass
        out.append(ProfileOut(id=prof.id, name=prof.name.value, age_limit=prof.age_limit, boundaries=prof.boundaries))
    # invalidate rec cache for this user
    try:
        invalidate_for_email(email)
    except Exception:
        pass
    return out
