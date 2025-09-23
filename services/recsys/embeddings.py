from __future__ import annotations

import hashlib
import math
from typing import Iterable, List

from sqlmodel import Session, select


def _tokens_from_metadata(meta: dict | None) -> list[str]:
    if not meta:
        return []
    toks: list[str] = []
    for g in meta.get("genres", []) or []:
        toks.append(f"genre:{g}")
    for c in meta.get("creators", []) or []:
        toks.append(f"creator:{c}")
    pacing = meta.get("episode_length")
    if pacing is not None:
        bucket = 0 if pacing <= 20 else 1 if pacing <= 35 else 2 if pacing <= 45 else 3
        toks.append(f"len:{bucket}")
    region = meta.get("region")
    if region:
        toks.append(f"region:{region}")
    return toks


def _vec_for_token(tok: str, dim: int = 384) -> list[float]:
    h = hashlib.sha256(tok.encode()).digest()
    # generate dim floats deterministically from hash bytes (repeat if needed)
    vals: list[float] = []
    i = 0
    while len(vals) < dim:
        b = h[i % len(h)]
        v = (b / 255.0) * 2.0 - 1.0  # -1..1
        vals.append(v)
        i += 1
    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vals)) or 1.0
    return [x / norm for x in vals]


def _combine(vecs: list[list[float]]) -> list[float]:
    if not vecs:
        return [0.0] * 384
    dim = len(vecs[0])
    out = [0.0] * dim
    for v in vecs:
        for i, x in enumerate(v):
            out[i] += x
    # normalize
    norm = math.sqrt(sum(x * x for x in out)) or 1.0
    return [x / norm for x in out]


def build_show_embeddings(session: Session) -> int:
    from apps.api.app.models import Show  # type: ignore
    n = 0
    shows = session.exec(select(Show)).all()
    for s in shows:
        toks = _tokens_from_metadata(s.metadata)
        vecs = [_vec_for_token(t) for t in toks]
        emb = _combine(vecs)
        # upsert into embeddings_show (emb_v)
        session.exec(
            """
            INSERT INTO embeddings_show (show_id, emb)
            VALUES (:sid, :arr)
            ON CONFLICT (show_id) DO UPDATE SET emb = EXCLUDED.emb
            """,
            {"sid": str(s.id), "arr": emb},
        )
        # Also set emb_v from the array for pgvector usage
        session.exec(
            """
            UPDATE embeddings_show SET emb_v = :vec::vector WHERE show_id = :sid
            """,
            {"sid": str(s.id), "vec": "[" + ",".join(str(x) for x in emb) + "]"},
        )
        n += 1
    session.commit()
    return n


def build_profile_embeddings(session: Session) -> int:
    from apps.api.app.models import Profile, Rating, Show  # type: ignore
    profiles = session.exec(select(Profile)).all()
    built = 0
    for p in profiles:
        ratings = session.exec(select(Rating).where(Rating.profile_id == p.id)).all()
        vecs: list[list[float]] = []
        for r in ratings:
            s = session.exec(select(Show).where(Show.id == r.show_id)).first()
            if not s:
                continue
            toks = _tokens_from_metadata(s.metadata)
            v = _combine([_vec_for_token(t) for t in toks])
            weight = 2.0 if r.primary == 2 else (1.0 if r.primary == 1 else -1.0)
            vecs.append([x * weight for x in v])
        emb = _combine(vecs) if vecs else [0.0] * 384
        session.exec(
            """
            INSERT INTO embeddings_profile (profile_id, emb)
            VALUES (:pid, :arr)
            ON CONFLICT (profile_id) DO UPDATE SET emb = EXCLUDED.emb
            """,
            {"pid": p.id, "arr": emb},
        )
        session.exec(
            """
            UPDATE embeddings_profile SET emb_v = :vec::vector WHERE profile_id = :pid
            """,
            {"pid": p.id, "vec": "[" + ",".join(str(x) for x in emb) + "]"},
        )
        built += 1
    session.commit()
    return built

