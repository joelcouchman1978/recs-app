from flask import Flask, request, jsonify
import os, requests
from requests import RequestException

app = Flask(__name__)


@app.post("/alert")
def alert():
    teams_webhook = os.getenv("TEAMS_WEBHOOK_URL", "")
    data = request.get_json(force=True, silent=True) or {}
    alerts = data.get("alerts", [])
    if not teams_webhook:
        return jsonify({"ok": False, "err": "TEAMS_WEBHOOK_URL not set"}), 500

    # Build a very simple text payload summarizing alerts
    lines = []
    status = (data.get("status") or "firing").upper()
    common = data.get("commonLabels", {}) or data.get("labels", {}) or {}
    lines.append(f"*Alertmanager* [{status}] {common.get('alertname','')}")
    for a in alerts:
        labels = a.get("labels", {}) or {}
        annotations = a.get("annotations", {}) or {}
        sev = labels.get("severity", "info")
        summ = annotations.get("summary", labels.get("alertname", ""))
        desc = annotations.get("description", "")
        tgt = labels.get("instance", labels.get("job", ""))
        lines.append(f"- {sev}: {summ} | {tgt}")
        if desc:
            lines.append(f"  {desc}")

    payload = {"text": "\n".join(lines)[:15000]}  # Teams text limit guard
    try:
        r = requests.post(teams_webhook, json=payload, timeout=10)
        return jsonify({"ok": r.ok, "status": r.status_code}), (200 if r.ok else 502)
    except RequestException as e:
        return jsonify({"ok": False, "status": 502, "error": str(e)}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


@app.post("/discord")
def discord():
    data = request.get_json(force=True, silent=True) or {}
    alerts = data.get("alerts", [])
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not discord_webhook:
        return jsonify({"ok": False, "err": "DISCORD_WEBHOOK_URL not set"}), 500

    # Compose a single text message (Discord expects {"content": "..."})
    lines = []
    status = (data.get("status") or "firing").upper()
    common = data.get("commonLabels", {}) or {}
    title = common.get("alertname", "Alertmanager")
    lines.append(f"**{title}** [{status}]")
    for a in alerts:
        lab = a.get("labels", {}) or {}
        ann = a.get("annotations", {}) or {}
        sev = lab.get("severity", "info")
        summ = ann.get("summary", lab.get("alertname", ""))
        desc = ann.get("description", "")
        tgt = lab.get("instance", lab.get("job", ""))
        lines.append(f"- {sev}: {summ} | {tgt}")
        if desc:
            lines.append(f"  {desc}")
    content = "\n".join(lines)[:1900]  # leave headroom under 2k char limit
    try:
        r = requests.post(discord_webhook, json={"content": content}, timeout=10)
        return jsonify({"ok": r.ok, "status": r.status_code}), (200 if r.ok else 502)
    except RequestException as e:
        return jsonify({"ok": False, "status": 502, "error": str(e)}), 502
