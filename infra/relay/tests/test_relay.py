import json
import pytest

from infra.relay.teams_relay import app


@pytest.fixture()
def client(monkeypatch):
    # ensure clean env per test
    for k in ("TEAMS_WEBHOOK_URL", "DISCORD_WEBHOOK_URL"):
        monkeypatch.delenv(k, raising=False)
    return app.test_client()


def sample_alert(summary="RecsP95LatencyHigh", desc="p95 high", severity="warning"):
    return {
        "status": "firing",
        "commonLabels": {"alertname": "RecsP95LatencyHigh"},
        "alerts": [
            {
                "labels": {"severity": severity, "job": "recs-api"},
                "annotations": {"summary": summary, "description": desc},
            }
        ],
    }


def test_teams_missing_env_returns_500(client):
    resp = client.post("/alert", data=json.dumps(sample_alert()), content_type="application/json")
    assert resp.status_code == 500
    body = resp.get_json()
    assert body and body.get("ok") is False


def test_discord_missing_env_returns_500(client):
    resp = client.post("/discord", data=json.dumps(sample_alert()), content_type="application/json")
    assert resp.status_code == 500
    body = resp.get_json()
    assert body and body.get("ok") is False


def test_teams_success(monkeypatch, client):
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://teams.example/webhook")
    calls = {}

    def fake_post(url, json=None, timeout=10):
        calls["url"] = url
        calls["json"] = json
        class R:
            ok = True
            status_code = 200

        return R()

    import requests

    monkeypatch.setattr(requests, "post", fake_post)
    resp = client.post(
        "/alert", data=json.dumps(sample_alert(desc="hello")), content_type="application/json"
    )
    assert resp.status_code == 200
    assert calls["url"].startswith("https://")
    assert "hello" in calls["json"]["text"]


def test_discord_success_with_truncation(monkeypatch, client):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")
    long = "x" * 5000
    called = {}

    def fake_post(url, json=None, timeout=10):
        called["url"] = url
        called["json"] = json
        class R:
            ok = True
            status_code = 204

        return R()

    import requests

    monkeypatch.setattr(requests, "post", fake_post)
    resp = client.post(
        "/discord", data=json.dumps(sample_alert(desc=long)), content_type="application/json"
    )
    assert resp.status_code == 200
    content = called["json"]["content"]
    assert len(content) <= 2000
    assert "**RecsP95LatencyHigh**" in content


def test_downstream_timeout_returns_502(monkeypatch, client):
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://teams.example/webhook")
    import requests

    class Boom(requests.RequestException):
        pass

    def fake_post(url, json=None, timeout=10):
        raise Boom("timeout")

    monkeypatch.setattr(requests, "post", fake_post)
    resp = client.post("/alert", data=json.dumps(sample_alert()), content_type="application/json")
    assert resp.status_code == 502
    assert resp.get_json()["ok"] is False

