from fastapi.testclient import TestClient
from apps.api.app.main import app
from apps.api.app.settings import settings
from apps.api.app.spoiler_lint import assert_no_spoilers, SpoilerError


client = TestClient(app)
PROFILE = "ross"
FALLBACK_TEXT = "A well-matched pick based on your tastes."


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def _get_recs(seed=123):
    token = _auth()
    r = client.get(
        "/recommendations",
        params={"for": PROFILE, "intent": "default", "seed": seed},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    return body


def test_rationales_present_capped_and_safe():
    items = _get_recs(seed=321)
    assert len(items) > 0
    for it in items:
        rationale = it.get("rationale", "")
        assert isinstance(rationale, str) and len(rationale) > 0
        assert len(rationale) <= settings.rationale_max_chars
        assert_no_spoilers(rationale)


def test_rationales_stable_for_same_seed_and_inputs():
    a = _get_recs(seed=999)
    b = _get_recs(seed=999)
    map_a = {it["id"]: it.get("rationale") for it in a}
    map_b = {it["id"]: it.get("rationale") for it in b}
    assert set(map_a.keys()) == set(map_b.keys())
    for k in map_a:
        assert map_a[k] == map_b[k]


def test_fallback_when_spoiler_lint_raises(monkeypatch):
    from apps.api.app import recs as recs_mod

    def always_fail(_text: str):
        raise SpoilerError("forced")

    # Force lint failure so the runtime fallback string is used
    monkeypatch.setattr(recs_mod, "assert_no_spoilers", always_fail)
    items = _get_recs(seed=77)
    assert len(items) > 0
    for it in items:
        rationale = it.get("rationale", "")
        assert rationale == FALLBACK_TEXT
        assert len(rationale) <= settings.rationale_max_chars

