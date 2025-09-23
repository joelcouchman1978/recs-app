from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def test_metrics_endpoint_exposes_counters():
    token = _auth()
    # Trigger a recs call to ensure some metrics exist
    r = client.get("/recommendations", params={"for": "ross", "intent": "default", "seed": 11}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    m = client.get("/metrics")
    assert m.status_code == 200
    text = m.text
    assert "recs_request_latency_ms_bucket" in text
    assert ("recs_cache_hits_total" in text) or ("recs_cache_misses_total" in text)

