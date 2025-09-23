from __future__ import annotations

import json, os
from fastapi import APIRouter, Header, HTTPException
from .utils import parse_token

router = APIRouter()


def _provider_map() -> dict[int, str]:
    base = {
        8: "Netflix", 24: "Prime Video", 179: "Disney+", 37: "Stan", 387: "Binge", 350: "Apple TV+",
        85: "SBS On Demand", 84: "ABC iView", 382: "BritBox", 337: "Paramount+", 119: "YouTube", 3: "Google Play", 10: "Apple iTunes",
        167: "Foxtel Now", 308: "Kayo Sports", 56: "Microsoft Store", 35: "Fetch", 146: "Rakuten TV",
    }
    try:
        raw = os.getenv("JUSTWATCH_PROVIDER_MAP")
        if raw:
            override = json.loads(raw)
            for k, v in override.items():
                try:
                    base[int(k)] = str(v)
                except Exception:
                    continue
    except Exception:
        pass
    return base


@router.get("/admin/providers")
def get_providers(authorization: str | None = Header(default=None)):
    email = parse_token(authorization)
    if not email:
        raise HTTPException(status_code=401, detail="Unauthorized")
    raw = os.getenv("JUSTWATCH_PROVIDER_MAP")
    return {
        "providers": _provider_map(),
        "overrides_active": bool(raw),
        "raw_override": raw or None,
    }
