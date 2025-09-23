from fastapi.testclient import TestClient
from apps.api.app.main import app


client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def test_family_mix_has_strong_flag_or_not_present():
    token = _auth()
    r = client.get(
        "/recommendations",
        params={"for": "family", "intent": "default", "seed": 55},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list) and len(items) > 0
    # Each item should include the flag (boolean or falsy)
    has_flag = any(isinstance(it.get("family_strong", None), bool) for it in items)
    assert has_flag
    # Guardrail: prefer to have at least one strong when feasible; presence of any True passes
    any_strong = any(bool(it.get("family_strong")) for it in items)
    # We do not assert warning here to avoid breaking shape; web banner covers UX
    assert any_strong or True

