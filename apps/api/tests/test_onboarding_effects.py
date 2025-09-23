from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def _get_profiles(token):
    r = client.get("/me/profiles", headers={"Authorization": f"Bearer {token}"})
    return r.json()


def _ross_id(token):
    for p in _get_profiles(token):
        if p["name"] == "Ross":
            return p["id"]
    return None


def test_constraints_show_evidence_chips():
    token = _auth()
    pid = _ross_id(token)
    assert pid is not None
    # Set very tight constraints to trigger hints
    client.post(
        "/onboarding",
        json={
            "profile_id": pid,
            "loves": [],
            "dislikes": [],
            "creators_like": [],
            "creators_dislike": [],
            "mood": {"tone":2, "pacing":2, "complexity":2, "humor":2, "optimism":2},
            "constraints": {"ep_length_max": 20, "seasons_max": 1, "avoid_dnf": True},
            "boundaries": {},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    r = client.get(
        "/recommendations?for=ross&intent=default",
        headers={"Authorization": f"Bearer {token}"},
    )
    arr = r.json()
    # Expect at least one evidence chip about constraints
    found = False
    for it in arr:
        for b in (it.get("similar_because") or []):
            if "Longer than preferred" in b or "More seasons than preferred" in b:
                found = True
                break
        if found:
            break
    assert found


def test_pacing_mood_shifts_episode_lengths():
    token = _auth()
    pid = _ross_id(token)
    assert pid is not None
    # Slow pacing (1): should lean longer
    client.post(
        "/onboarding",
        json={
            "profile_id": pid,
            "loves": [],
            "dislikes": [],
            "creators_like": [],
            "creators_dislike": [],
            "mood": {"tone":2, "pacing":1, "complexity":2, "humor":2, "optimism":2},
            "constraints": {},
            "boundaries": {},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    a = client.get(
        "/recommendations?for=ross&intent=default",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    # Fast pacing (3): should lean shorter
    client.post(
        "/onboarding",
        json={
            "profile_id": pid,
            "loves": [],
            "dislikes": [],
            "creators_like": [],
            "creators_dislike": [],
            "mood": {"tone":2, "pacing":3, "complexity":2, "humor":2, "optimism":2},
            "constraints": {},
            "boundaries": {},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    b = client.get(
        "/recommendations?for=ross&intent=default",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    def _avg_ep(recs):
        if not recs:
            return 0
        total = 0
        cnt = 0
        for it in recs[:3]:
            sd = client.get(f"/shows/{it['id']}").json()
            el = int((sd.get('metadata') or {}).get('episode_length') or 0)
            if el:
                total += el
                cnt += 1
        return (total / cnt) if cnt else 0

    avg_slow = _avg_ep(a)
    avg_fast = _avg_ep(b)
    # Assert trend: slow pacing average >= fast pacing average
    assert avg_slow >= avg_fast

