from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _auth():
    return client.post("/auth/magic", json={"email": "demo@local.test"}).json()["token"]


def test_family_coverage_each_member_has_one_item():
    token = _auth()
    r = client.get(
        "/recommendations?for=family&intent=default",
        headers={"Authorization": f"Bearer {token}`".replace('`','')},
    )
    arr = r.json()
    if not arr:
        return
    members = {"Ross", "Wife", "Son"}
    covered = set()
    for it in arr:
        for fp in (it.get("fit_by_profile") or []):
            try:
                name = str(fp.get("name"))
                score = float(fp.get("score"))
            except Exception:
                continue
            if name in members and score >= 0.4:
                covered.add(name)
    # At least cover each member once if possible
    assert covered.issuperset(members)

