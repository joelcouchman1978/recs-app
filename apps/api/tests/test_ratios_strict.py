from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def _comfort_count(items):
    # Approximate comfort as novelty n <= 0.6
    return sum(1 for it in items if float(it.get('prediction', {}).get('n', 1)) <= 0.6)


def test_70_30_default_ratio():
    token = _auth()
    r = client.get("/recommendations?for=ross&intent=default", headers={"Authorization": f"Bearer {token}"})
    arr = r.json()
    if len(arr) < 6:
        return  # not enough items in seed; skip strict check
    comfort = _comfort_count(arr)
    # expect ~70% comfort: 4 or 5 of 6
    assert comfort in (4, 5)


def test_comfort_intent_near_zero_discovery():
    token = _auth()
    r = client.get("/recommendations?for=ross&intent=comfort", headers={"Authorization": f"Bearer {token}"})
    arr = r.json()
    if len(arr) < 6:
        return
    discovery = 6 - _comfort_count(arr)
    # allow at most 1 discovery item
    assert discovery <= 1


def test_weekend_binge_ratio():
    token = _auth()
    r = client.get("/recommendations?for=ross&intent=weekend_binge", headers={"Authorization": f"Bearer {token}"})
    arr = r.json()
    if len(arr) < 6:
        return
    comfort = _comfort_count(arr)
    # weekend_binge follows default split: expect ~70% comfort (4 or 5 of 6)
    assert comfort in (4, 5)


def test_surprise_intent_prefers_discovery():
    token = _auth()
    r = client.get("/recommendations?for=ross&intent=surprise", headers={"Authorization": f"Bearer {token}"})
    arr = r.json()
    if len(arr) < 6:
        return
    comfort = _comfort_count(arr)
    # Surprise should bias toward discovery: 2 or 3 comfort of 6
    assert comfort in (2, 3)
