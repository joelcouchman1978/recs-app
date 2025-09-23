from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.db import get_session


client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def test_admin_freshness_endpoint():
    token = _auth()
    # pre-insert minimal rows
    with next(get_session()) as s:
        s.exec(text("INSERT INTO justwatch_offers (title_ref, provider, offer_type, region, last_checked_ts) VALUES ('t1','netflix','stream','AU', now())"))
        s.exec(text("INSERT INTO serializd_history (profile_ref, status, last_seen_ts) VALUES ('ross','watched', now())"))
        s.commit()
    r = client.get("/admin/freshness", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["offers_rows"] >= 1
    assert body["serializd_rows"] >= 1
    assert body["offers_last_checked"] is not None
    assert body["serializd_last_seen"] is not None


def test_upsert_sets_freshness_ts():
    with next(get_session()) as s:
        s.exec(text("""
            INSERT INTO justwatch_offers (title_ref, provider, offer_type, region, last_checked_ts)
            VALUES ('t2','stan','stream','AU', now())
            ON CONFLICT (title_ref, provider, offer_type)
            DO UPDATE SET last_checked_ts = now()
        """))
        s.commit()
        ts = s.exec(text("SELECT last_checked_ts FROM justwatch_offers WHERE title_ref='t2'"))
        assert ts.first()[0] is not None

