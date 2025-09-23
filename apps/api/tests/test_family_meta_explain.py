from fastapi.testclient import TestClient
from apps.api.app.main import app


client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def test_default_no_family_meta():
    token = _auth()
    r = client.get(
        "/recommendations",
        params={"for": "family", "intent": "default", "seed": 42},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # By default, no top-level family meta is present
    # (since shape is a list, dict key wouldn't exist)


def test_family_meta_present_with_explain_true():
    token = _auth()
    r = client.get(
        "/recommendations",
        params={"for": "family", "intent": "default", "seed": 42, "explain": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert "items" in data
    fam = data.get("family")
    assert isinstance(fam, dict)
    keys = set(fam.keys())
    assert {"strong_locked_ids", "warning", "strong_min_fit", "strong_rule"}.issubset(keys)
    assert isinstance(fam.get("strong_locked_ids"), list)
    warn = fam.get("warning")
    if warn is not None:
        assert warn.get("code") == "no_strong_pick"

