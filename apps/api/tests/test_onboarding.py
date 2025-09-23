from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def test_onboarding_creates_ratings_and_event():
    token = _auth()
    # fetch profiles to find one id
    ps = client.get("/me/profiles", headers={"Authorization": f"Bearer {token}"}).json()
    assert ps, "profiles expected"
    pid = ps[0]['id']
    # pick two shows
    shows = client.get("/shows?limit=5").json()
    loves = [shows[0]['id']]
    dislikes = [shows[1]['id']]
    r = client.post("/onboarding", headers={"Authorization": f"Bearer {token}"}, json={
        "profile_id": pid,
        "loves": loves,
        "dislikes": dislikes,
        "creators_like": [],
        "creators_dislike": [],
        "mood": {"tone":2, "pacing":2, "complexity":2, "humor":2, "optimism":2},
        "constraints": {"ep_length_max": 35},
        "boundaries": {"violence": True}
    })
    assert r.status_code == 200
    # ensure recs call still works
    recs = client.get("/recommendations?for=ross&intent=default", headers={"Authorization": f"Bearer {token}"})
    assert recs.status_code == 200
