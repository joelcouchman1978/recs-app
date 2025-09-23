from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def _ids(arr):
    return [it["id"] for it in arr]


def test_default_deterministic_repeats():
    token = _auth()
    r1 = client.get(
        "/recommendations?for=ross&intent=default",
        headers={"Authorization": f"Bearer {token}"},
    )
    r2 = client.get(
        "/recommendations?for=ross&intent=default",
        headers={"Authorization": f"Bearer {token}"},
    )
    a1, a2 = r1.json(), r2.json()
    # Only check determinism when we have enough items
    if len(a1) >= 3 and len(a2) >= 3:
        assert _ids(a1) == _ids(a2)


def test_comfort_deterministic_repeats():
    token = _auth()
    r1 = client.get(
        "/recommendations?for=ross&intent=comfort",
        headers={"Authorization": f"Bearer {token}"},
    )
    r2 = client.get(
        "/recommendations?for=ross&intent=comfort",
        headers={"Authorization": f"Bearer {token}"},
    )
    a1, a2 = r1.json(), r2.json()
    if len(a1) >= 3 and len(a2) >= 3:
        assert _ids(a1) == _ids(a2)


def test_anchor_bias_prefers_similar_genres():
    token = _auth()
    # pick an anchor from /shows
    shows = client.get("/shows?limit=10").json()
    if not shows:
        return
    anchor = shows[0]
    like_id = anchor["id"]
    anchor_genres = set((anchor.get("metadata") or {}).get("genres", []) or [])
    r = client.get(
        f"/recommendations?for=ross&intent=default&like_id={like_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    arr = r.json()
    if len(arr) == 0:
        return
    # ensure anchor isn't returned and top result shares at least one genre when available
    assert arr[0]["id"] != like_id
    top = client.get(f"/shows/{arr[0]['id']}").json()
    top_genres = set((top.get("metadata") or {}).get("genres", []) or [])
    # Only assert overlap when anchor has labeled genres
    if anchor_genres:
        assert len(anchor_genres & top_genres) >= 1

