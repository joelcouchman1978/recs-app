import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

try:
    # tests live under apps/api, so `app` is the package
    from app.main import app
except Exception:
    # fallback import path if needed
    from apps.api.app.main import app  # type: ignore


client = TestClient(app)
SNAP_DIR = Path(__file__).parent / "snapshots"
SNAP_DIR.mkdir(parents=True, exist_ok=True)


def _auth_token() -> str:
    r = client.post("/auth/magic", json={"email": "demo@local.test"})
    r.raise_for_status()
    return r.json()["token"]


def _ids_for(profile: str, *, seed: int = 777, intent: str = "default", explain: bool = False, token: str = ""):
    headers = {"Authorization": f"Bearer {token}"}
    params = {"for": profile, "intent": intent, "seed": seed}
    if explain:
        params["explain"] = True
    r = client.get("/recommendations", params=params, headers=headers)
    r.raise_for_status()
    body = r.json()
    if explain and profile == "family" and isinstance(body, dict):
        items = body.get("items", [])
        fam = body.get("family") or {}
        return [it["id"] for it in items], fam.get("strong_locked_ids") or []
    # default: plain list of items
    return [it["id"] for it in body]


def _snap_path(name: str) -> Path:
    return SNAP_DIR / f"{name}.json"


def _load_snap(name: str):
    p = _snap_path(name)
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _save_snap(name: str, data):
    p = _snap_path(name)
    with p.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


@pytest.mark.parametrize(
    "profile,intent,explain,name",
    [
        ("ross", "default", False, "ross_seed777"),
        ("wife", "default", False, "wife_seed777"),
        ("son", "default", False, "son_seed777"),
        ("family", "family_mix", True, "family_mix_seed777_explain"),
    ],
)
def test_seeded_ids_match_snapshot(profile, intent, explain, name):
    token = _auth_token()

    # 1) Two calls with the same seed must be identical (ordering + contents)
    first = _ids_for(profile, seed=777, intent=intent, explain=explain, token=token)
    second = _ids_for(profile, seed=777, intent=intent, explain=explain, token=token)
    assert first == second, "Seeded recommendations should be deterministic across calls"

    # 2) Compare against committed snapshots (IDs only)
    snap = _load_snap(name)

    # Support opt-in refresh via env var
    should_update = os.getenv("UPDATE_SNAPSHOTS") == "1"

    if explain and profile == "family":
        ids, strong = first
        data = {"ids": ids, "strong_locked_ids": strong}
    else:
        data = {"ids": first}

    if snap is None and should_update:
        _save_snap(name, data)
        pytest.skip(f"Snapshot created: {name}.json (first run with UPDATE_SNAPSHOTS=1)")
    elif snap is None:
        pytest.skip(
            "Snapshot missing. Run with UPDATE_SNAPSHOTS=1 to record, then commit tests/snapshots/*.json"
        )
    else:
        # Exact match required (IDs only)
        assert data == snap

