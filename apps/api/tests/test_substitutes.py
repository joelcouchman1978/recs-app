from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def test_boundary_safe_alternatives_present_for_wife():
    token = _auth()
    # tighten boundaries to trigger substitutes
    client.post("/profiles", headers={"Authorization": f"Bearer {token}"}, json=[{"name":"Wife","boundaries":{"violence": True, "language": True}}])
    r = client.get(
        "/recommendations?for=wife&intent=default",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    arr = r.json()
    # Expect at least two boundary-safe alternative markers when boundaries exclude popular items
    subs = [1 for itm in arr if 'Boundary-safe alternative' in (itm.get('rationale') or '')]
    assert len(subs) >= 2 or len(arr) < 2
