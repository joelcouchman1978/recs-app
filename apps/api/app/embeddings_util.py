from __future__ import annotations

import hashlib
import math
from typing import List

from sqlmodel import Session, select


def _tokens_from_metadata(meta: dict | None) -> list[str]:
    if not meta:
        return []
    toks: list[str] = []
    for g in meta.get("genres", []) or []:
        toks.append(f"genre:{g}")
    for c in meta.get("creators", []) or []:
        toks.append(f"creator:{c}")
    el = meta.get("episode_length")
    if el is not None:
        bucket = 0 if el <= 20 else 1 if el <= 35 else 2 if el <= 45 else 3
        toks.append(f"len:{bucket}")
    region = meta.get("region")
    if region:
        toks.append(f"region:{region}")
    return toks


def _vec_for_token(tok: str, dim: int = 384) -> list[float]:
    h = hashlib.sha256(tok.encode()).digest()
    vals: list[float] = []
    i = 0
    while len(vals) < dim:
        b = h[i % len(h)]
        v = (b / 255.0) * 2.0 - 1.0
        vals.append(v)
        i += 1
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
    norm = math.sqrt(sum(x * x for x in out)) or 1.0
    return [x / norm for x in out]


def rebuild_profile_embedding(session: Session, profile_id: int) -> None:
    from .models import Rating, Show  # type: ignore
    ratings = session.exec(select(Rating).where(Rating.profile_id == profile_id)).all()
    vecs: list[list[float]] = []
    for r in ratings:
        s = session.get(Show, r.show_id)
        if not s:
            continue
        toks = _tokens_from_metadata(s.metadata)
        v = _combine([_vec_for_token(t) for t in toks])
        w = 2.0 if r.primary == 2 else (1.0 if r.primary == 1 else -1.0)
        vecs.append([x * w for x in v])
    emb = _combine(vecs) if vecs else [0.0] * 384
    session.exec(
        """
        INSERT INTO embeddings_profile (profile_id, emb)
        VALUES (:pid, :arr)
        ON CONFLICT (profile_id) DO UPDATE SET emb = EXCLUDED.emb
        """,
        {"pid": profile_id, "arr": emb},
    )
    session.exec(
        """
        UPDATE embeddings_profile SET emb_v = :vec::vector WHERE profile_id = :pid
        """,
        {"pid": profile_id, "vec": "[" + ",".join(str(x) for x in emb) + "]"},
    )
    session.commit()

