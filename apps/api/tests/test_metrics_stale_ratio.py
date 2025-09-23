from fastapi.testclient import TestClient
from apps.api.app.main import app


client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def test_stale_ratio_metrics_present_after_recs_call():
    token = _auth()
    r = client.get(
        "/recommendations",
        params={"for": "ross", "intent": "default", "seed": 42},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    m = client.get("/metrics")
    assert m.status_code == 200
    text = m.text
    assert "recs_stale_ratio_bucket" in text
    assert "recs_items_total" in text
    assert "recs_items_stale_total" in text

