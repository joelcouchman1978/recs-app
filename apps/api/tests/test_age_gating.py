from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def _age(meta):
    try:
        return int((meta or {}).get('age_rating'))
    except Exception:
        return None


def test_son_age_limit_excludes_mature_items():
    token = _auth()
    r = client.get("/recommendations?for=son&intent=default", headers={"Authorization": f"Bearer {token}"})
    arr = r.json()
    # Ensure any age-rated items are <= 13 for Son
    for it in arr:
        sd = client.get(f"/shows/{it['id']}").json()
        meta = sd.get('metadata')
        ar = _age(meta)
        au = (meta or {}).get('au_rating')
        if ar is not None:
            assert ar <= 13
        if au:
            assert str(au).upper() not in ("MA15+", "MA15", "R18", "R18+")
