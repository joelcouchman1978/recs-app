from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def _ensure_profiles(token: str) -> dict[str, int]:
    ps = client.get("/me/profiles", headers={"Authorization": f"Bearer {token}"}).json()
    ids = {p["name"]: p["id"] for p in ps}
    if {"Ross", "Wife", "Son"}.issubset(set(ids.keys())):
        return ids
    # create defaults
    r = client.post(
        "/profiles",
        headers={"Authorization": f"Bearer {token}"},
        json=[
            {"name": "Ross", "age_limit": 18, "boundaries": {}},
            {"name": "Wife", "age_limit": 18, "boundaries": {}},
            {"name": "Son", "age_limit": 13, "boundaries": {}},
        ],
    )
    assert r.status_code == 200
    ps = client.get("/me/profiles", headers={"Authorization": f"Bearer {token}"}).json()
    return {p["name"]: p["id"] for p in ps}


def _ids(token: str, seed=None):
    params = {"for": "ross", "intent": "default"}
    if seed is not None:
        params["seed"] = seed
    r = client.get("/recommendations", params=params, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    return [x["id"] for x in r.json()]


def test_rating_changes_topn_with_fixed_seed():
    token = _auth()
    profs = _ensure_profiles(token)
    pid = profs["Ross"]
    seed = 42
    before = _ids(token, seed)
    if not before:
        return
    target = before[0]
    r = client.post(
        "/ratings",
        headers={"Authorization": f"Bearer {token}"},
        json={"profile_id": pid, "show_id": target, "primary": 0},  # BAD
    )
    assert r.status_code == 200
    after = _ids(token, seed)
    if len(after) >= 1:
        assert after[0] != target


def test_cache_invalidation_on_rating_change():
    token = _auth()
    profs = _ensure_profiles(token)
    pid = profs["Ross"]
    seed = 7
    s1 = _ids(token, seed)
    if not s1:
        return
    r = client.post(
        "/ratings",
        headers={"Authorization": f"Bearer {token}"},
        json={"profile_id": pid, "show_id": s1[0], "primary": 0},
    )
    assert r.status_code == 200
    s2 = _ids(token, seed)
    assert s1 != s2

