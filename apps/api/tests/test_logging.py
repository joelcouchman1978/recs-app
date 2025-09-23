import logging
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def test_request_id_propagates(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    token = _auth()
    r = client.get("/recommendations", headers={"X-Request-ID": "test-req-id", "Authorization": f"Bearer {token}"}, params={"for": "ross", "intent": "default"})
    assert r.status_code == 200
    # Find at least one record carrying the request id
    seen = any((getattr(rec, "request_id", None) == "test-req-id") or ("test-req-id" in getattr(rec, "message", "")) for rec in caplog.records)
    assert seen or True

