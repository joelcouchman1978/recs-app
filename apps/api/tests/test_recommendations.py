from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") in ("ok", "degraded")
    assert "checks" in body and isinstance(body["checks"], dict)


def test_recommendations_requires_auth():
    r = client.get("/recommendations?for=ross")
    assert r.status_code == 401


def test_recommendations_shape(monkeypatch):
    # Dev token for demo
    token = client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]
    r = client.get("/recommendations?for=ross&intent=short_tonight", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    arr = r.json()
    assert isinstance(arr, list)
    assert len(arr) <= 6
    if arr:
      item = arr[0]
      assert {"id","title","where_to_watch","rationale","warnings","flags","prediction"}.issubset(item.keys())
      assert item["prediction"]["label"] in ["BAD","ACCEPTABLE","VERY GOOD"]
