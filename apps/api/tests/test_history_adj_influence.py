from fastapi.testclient import TestClient
from apps.api.app.main import app
from apps.api.app.db import get_session
from sqlalchemy import text


client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def test_history_adj_does_not_error_and_runs():
    # Smoke: insert a recent serializd_history row mapped to some existing title if possible
    with next(get_session()) as s:
        row = s.exec(text("SELECT title FROM shows LIMIT 1")).first()
        if row and row[0]:
            s.exec(text("INSERT INTO serializd_history (profile_ref, title_ref, last_seen_ts) VALUES ('Ross', :t, now())"), {"t": row[0]})
            s.commit()
    token = _auth()
    r1 = client.get("/recommendations", params={"for": "ross", "intent": "default", "seed": 101}, headers={"Authorization": f"Bearer {token}"})
    assert r1.status_code == 200

