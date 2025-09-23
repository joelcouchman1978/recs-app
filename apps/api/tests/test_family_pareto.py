from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def test_family_pareto_nondominance():
    token = _auth()
    r = client.get("/debug/recommendations?for=family&intent=default", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    arr = r.json()
    # assert nondominance on frontier result
    def dominated(a, b):
        ge_all = all(bi >= ai for ai, bi in zip(a, b))
        gt_any = any(bi > ai for ai, bi in zip(a, b))
        return ge_all and gt_any
    for i, a in enumerate(arr):
        for j, b in enumerate(arr):
            if i == j:
                continue
            assert not dominated(a['scores'], b['scores'])
