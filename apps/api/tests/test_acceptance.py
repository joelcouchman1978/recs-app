from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def test_short_tonight_filters_episode_length():
    token = _auth()
    r = client.get(
        "/recommendations?for=ross&intent=short_tonight",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    recs = r.json()
    for itm in recs:
        s = client.get(f"/shows/{itm['id']}")
        assert s.status_code == 200
        meta = s.json()["metadata"]
        assert int(meta.get("episode_length", 60)) <= 35
        # rationale mentions short episodes
        assert 'short' in itm['rationale'].lower()


def test_family_mix_returns_items():
    token = _auth()
    r = client.get(
        "/recommendations?for=family&intent=default",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    arr = r.json()
    assert isinstance(arr, list)
    # may be less than 6 if strict, but should be >= 1
    assert len(arr) >= 1
