from fastapi.testclient import TestClient
from apps.api.app.main import app


client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def _first(seed=42):
    token = _auth()
    r = client.get(
        "/recommendations",
        params={"for": "ross", "intent": "default", "seed": seed},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list) and len(items) > 0
    return items[0]


def test_availability_payload_has_freshness_and_consistency_fields():
    item = _first()
    av = item.get("availability", {}) or {}
    assert {"as_of", "stale", "season_consistent"}.issubset(set(av.keys()))

