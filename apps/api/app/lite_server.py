from __future__ import annotations

import argparse
import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import blake2b
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse


def _stable_hash01(item_id: str, seed: int | None) -> float:
    h = blake2b(digest_size=8)
    h.update(item_id.encode())
    if seed is not None:
        h.update(str(seed).encode())
    n = int.from_bytes(h.digest(), "big")
    return (n % 10_000_000) / 10_000_000.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_bool(v: str | None) -> bool:
    if v is None:
        return False
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class _Show:
    id: str
    title: str
    year: int
    genres: tuple[str, ...]
    creators: tuple[str, ...]
    au_rating: str
    warnings: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()
    episode_length: int = 45
    seasons: int = 1


_SHOWS: list[_Show] = [
    _Show(
        id="cozy-bakery",
        title="Cozy Bakery",
        year=2021,
        genres=("comedy", "family"),
        creators=("Jo Dough",),
        au_rating="PG",
        flags=("cozy", "optimistic"),
        episode_length=28,
        seasons=2,
    ),
    _Show(
        id="mystery-harbor",
        title="Mystery Harbor",
        year=2019,
        genres=("mystery", "drama"),
        creators=("Alex Shore",),
        au_rating="M",
        warnings=("dark",),
        flags=("tense",),
        episode_length=45,
        seasons=3,
    ),
    _Show(
        id="science-frontier",
        title="Science Frontier",
        year=2020,
        genres=("documentary", "science"),
        creators=("Dr. Lin",),
        au_rating="G",
        flags=("optimistic",),
        episode_length=35,
        seasons=1,
    ),
    _Show(
        id="rebound",
        title="Rebound",
        year=2017,
        genres=("sports", "comedy"),
        creators=("Casey Quick",),
        au_rating="PG",
        flags=("humorous",),
        episode_length=24,
        seasons=4,
    ),
    _Show(
        id="stellar-siblings",
        title="Stellar Siblings",
        year=2022,
        genres=("sci-fi", "family"),
        creators=("Nia Orbit",),
        au_rating="PG",
        warnings=("mild peril",),
        flags=("hopeful",),
        episode_length=38,
        seasons=2,
    ),
    _Show(
        id="noir-notes",
        title="Noir Notes",
        year=2018,
        genres=("thriller", "mystery"),
        creators=("Jamie Keys",),
        au_rating="MA15+",
        warnings=("violence",),
        flags=("stylish",),
        episode_length=50,
        seasons=1,
    ),
    _Show(
        id="tiny-heroes",
        title="Tiny Heroes",
        year=2016,
        genres=("animation", "family"),
        creators=("Studio Kite",),
        au_rating="G",
        flags=("gentle", "short episodes"),
        episode_length=12,
        seasons=5,
    ),
    _Show(
        id="calm-cases",
        title="Calm Cases",
        year=2023,
        genres=("procedural", "cozy"),
        creators=("Mina Vale",),
        au_rating="PG",
        flags=("clever dialogue", "humane worldview"),
        warnings=("mild peril",),
        episode_length=30,
        seasons=1,
    ),
]


_PROFILE_LIKES: dict[str, set[str]] = {
    "ross": {"mystery", "sci-fi", "documentary", "science"},
    "wife": {"drama", "mystery", "cozy", "documentary"},
    "son": {"animation", "family", "comedy", "sci-fi"},
    # "family" is computed as union of members
}


def _score_show(show: _Show, *, profile: str, seed: int | None) -> float:
    liked = _PROFILE_LIKES.get(profile, set())
    if profile == "family":
        liked = set().union(*_PROFILE_LIKES.values())
    overlap = len(liked & set(show.genres))
    base = 0.6 + 0.25 * overlap
    if profile in {"son", "family"} and {"violence", "dark"} & set(show.warnings):
        base -= 0.35
    return max(0.0, base + 1e-6 * _stable_hash01(show.id, seed))


_CACHE_LOCK = threading.Lock()
_CACHE: dict[tuple[str, str, int | None, bool], Any] = {}

_METRICS_LOCK = threading.Lock()
_CACHE_HITS = 0
_CACHE_MISSES = 0
_LAT_BUCKETS_MS = [5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0]
_LAT_CUM_BUCKET_COUNTS = {b: 0 for b in _LAT_BUCKETS_MS}
_LAT_INF = 0
_LAT_SUM_MS = 0.0

_STALE_BUCKETS = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]
_STALE_CUM_BUCKET_COUNTS = {b: 0 for b in _STALE_BUCKETS}
_STALE_INF = 0
_STALE_SUM = 0.0


def _observe_latency_ms(ms: float) -> None:
    global _LAT_INF, _LAT_SUM_MS
    with _METRICS_LOCK:
        for b in _LAT_BUCKETS_MS:
            if ms <= b:
                _LAT_CUM_BUCKET_COUNTS[b] += 1
        _LAT_INF += 1
        _LAT_SUM_MS += float(ms)


def _observe_stale_ratio(ratio: float) -> None:
    global _STALE_INF, _STALE_SUM
    ratio = max(0.0, min(1.0, float(ratio)))
    with _METRICS_LOCK:
        for b in _STALE_BUCKETS:
            if ratio <= b:
                _STALE_CUM_BUCKET_COUNTS[b] += 1
        _STALE_INF += 1
        _STALE_SUM += ratio


def _build_recommendations(
    *,
    profile: str,
    intent: str,
    seed: int | None,
    explain: bool,
) -> Any:
    scored = [(s, _score_show(s, profile=profile, seed=seed)) for s in _SHOWS]
    scored.sort(key=lambda t: (-t[1], t[0].id))
    picked = scored[:6]

    items: list[dict[str, Any]] = []
    now_iso = _now_iso()
    for show, score in picked:
        label = "BAD" if score < 0.5 else ("ACCEPTABLE" if score < 1.0 else "VERY GOOD")
        items.append(
            {
                "id": show.id,
                "title": show.title,
                "year": show.year,
                "rationale": "Matches your recent picks (lite mode, spoiler-safe).",
                "warnings": list(show.warnings),
                "flags": list(show.flags),
                "genres": list(show.genres)[:3],
                "creators": list(show.creators)[:2],
                "au_rating": show.au_rating,
                "prediction": {"label": label, "c": round(min(0.95, 0.55 + 0.15 * score), 2), "n": 0.3},
                "availability": {
                    "provider": "SandboxFlix",
                    "type": "stream",
                    "as_of": now_iso,
                    "stale": False,
                    "season_consistent": True,
                },
                "debug": {"score": round(score, 4), "intent": intent},
            }
        )

    _observe_stale_ratio(0.0)

    if explain and profile == "family" and intent == "family_mix":
        return {
            "items": items,
            "family": {
                "strong_locked_ids": [items[0]["id"]] if items else [],
                "warning": None,
                "strong_min_fit": 0.75,
                "strong_rule": "min",
            },
        }
    return items


_INDEX_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Recs (Lite)</title>
    <style>
      :root { color-scheme: light dark; }
      body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; line-height: 1.35; }
      .row { display: flex; gap: 12px; flex-wrap: wrap; align-items: end; }
      label { display: grid; gap: 6px; font-size: 12px; opacity: 0.9; }
      input, select, button { font: inherit; padding: 8px 10px; border-radius: 10px; border: 1px solid rgba(127,127,127,0.35); }
      button { cursor: pointer; }
      .card { margin-top: 18px; padding: 14px; border-radius: 14px; border: 1px solid rgba(127,127,127,0.25); }
      .muted { opacity: 0.8; font-size: 12px; }
      ol { margin: 10px 0 0 18px; }
      .pill { display: inline-block; padding: 2px 8px; border-radius: 999px; border: 1px solid rgba(127,127,127,0.35); font-size: 12px; margin-left: 8px; }
      code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 12px; }
    </style>
  </head>
  <body>
    <h1>Recs <span class="pill">Lite mode</span></h1>
    <p class="muted">
      Running without FastAPI/Next.js dependencies. Endpoints: <code>/readyz</code>, <code>/metrics</code>, <code>/recommendations</code>.
    </p>
    <div class="row">
      <label>
        Profile
        <select id="profile">
          <option value="ross">ross</option>
          <option value="wife">wife</option>
          <option value="son">son</option>
          <option value="family">family</option>
        </select>
      </label>
      <label>
        Intent
        <select id="intent">
          <option value="default">default</option>
          <option value="family_mix">family_mix</option>
        </select>
      </label>
      <label>
        Seed
        <input id="seed" inputmode="numeric" pattern="[0-9]*" value="99" />
      </label>
      <label>
        Explain
        <select id="explain">
          <option value="false">false</option>
          <option value="true">true</option>
        </select>
      </label>
      <button id="go">Get recommendations</button>
    </div>

    <div class="card" id="out">
      <div class="muted">Click “Get recommendations”.</div>
    </div>

    <script>
      const out = document.getElementById("out");
      const $ = (id) => document.getElementById(id);
      const render = (payload) => {
        const items = Array.isArray(payload) ? payload : (payload.items || []);
        const family = (!Array.isArray(payload) && payload.family) ? payload.family : null;
        const parts = [];
        if (family) {
          const locked = (family.strong_locked_ids || []).length;
          parts.push(`<div class="muted">Family meta: strong_locked_ids=${locked}</div>`);
        }
        parts.push("<ol>");
        for (const it of items) {
          parts.push(`<li><strong>${it.title}</strong> <span class="muted">(${it.id})</span><div class="muted">${it.rationale || ""}</div></li>`);
        }
        parts.push("</ol>");
        out.innerHTML = parts.join("");
      };

      document.getElementById("go").addEventListener("click", async () => {
        out.innerHTML = `<div class="muted">Loading…</div>`;
        const profile = $("profile").value;
        const intent = $("intent").value;
        const seed = $("seed").value.trim();
        const explain = $("explain").value;
        const qp = new URLSearchParams();
        qp.set("for", profile);
        qp.set("intent", intent);
        if (seed) qp.set("seed", seed);
        qp.set("explain", explain);
        const r = await fetch(`/recommendations?${qp.toString()}`);
        const j = await r.json();
        render(j);
      });
    </script>
  </body>
</html>
"""


class _Handler(BaseHTTPRequestHandler):
    server_version = "RecsLite/0.1"

    def _send_json(self, payload: Any, *, status: int = 200) -> None:
        data = json.dumps(payload, separators=(",", ":"), default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization,Content-Type")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_text(self, text: str, *, status: int = 200, content_type: str = "text/plain; charset=utf-8") -> None:
        data = text.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization,Content-Type")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization,Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        started = time.time()
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        try:
            if path == "/":
                return self._send_text(_INDEX_HTML, content_type="text/html; charset=utf-8")

            if path in {"/readyz", "/healthz"}:
                return self._send_json({"status": "ok", "mode": "lite"})

            if path == "/admin/config/summary":
                allow = os.getenv("ALLOW_ORIGINS", "http://localhost:3000")
                return self._send_json(
                    {
                        "mode": "lite",
                        "environment": os.getenv("ENVIRONMENT", "dev"),
                        "allow_origins": [o.strip() for o in allow.split(",") if o.strip()],
                        "notes": "Lite server runs without FastAPI/DB/Redis.",
                    }
                )

            if path == "/recommendations":
                qs = parse_qs(parsed.query)
                profile = (qs.get("for") or ["ross"])[0]
                intent = (qs.get("intent") or ["default"])[0]
                seed_raw = (qs.get("seed") or [None])[0]
                seed = int(seed_raw) if isinstance(seed_raw, str) and seed_raw.strip().isdigit() else None
                explain = _as_bool((qs.get("explain") or ["false"])[0])

                cache_key = (profile, intent, seed, explain)
                with _CACHE_LOCK:
                    cached = _CACHE.get(cache_key)
                if cached is not None:
                    global _CACHE_HITS
                    with _METRICS_LOCK:
                        _CACHE_HITS += 1
                    return self._send_json(cached)

                payload = _build_recommendations(profile=profile, intent=intent, seed=seed, explain=explain)
                with _CACHE_LOCK:
                    _CACHE[cache_key] = payload
                global _CACHE_MISSES
                with _METRICS_LOCK:
                    _CACHE_MISSES += 1
                return self._send_json(payload)

            if path == "/metrics":
                return self._send_text(_render_metrics())

            self._send_json({"error": "not_found", "path": path}, status=HTTPStatus.NOT_FOUND)
        finally:
            _observe_latency_ms((time.time() - started) * 1000.0)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/admin/jobs/daily_refresh":
            qs = parse_qs(parsed.query)
            dry = _as_bool((qs.get("dry_run") or ["false"])[0])
            return self._send_json({"status": "ok", "mode": "lite", "dry_run": dry, "refreshed": 0})
        return self._send_json({"error": "not_found", "path": path}, status=HTTPStatus.NOT_FOUND)


def _render_metrics() -> str:
    version = os.getenv("APP_VERSION", "0.1.0")
    sha = os.getenv("GIT_SHA", "lite")
    env = os.getenv("ENVIRONMENT", "dev")

    with _METRICS_LOCK:
        hits = int(_CACHE_HITS)
        misses = int(_CACHE_MISSES)
        lat_counts = dict(_LAT_CUM_BUCKET_COUNTS)
        lat_inf = int(_LAT_INF)
        lat_sum = float(_LAT_SUM_MS)
        stale_counts = dict(_STALE_CUM_BUCKET_COUNTS)
        stale_inf = int(_STALE_INF)
        stale_sum = float(_STALE_SUM)

    lines: list[str] = []
    lines += [
        "# HELP recs_build_info Build info (lite).",
        "# TYPE recs_build_info gauge",
        f'recs_build_info{{version="{version}",sha="{sha}",env="{env}",mode="lite"}} 1',
        "",
        "# HELP recs_cache_hits_total Recommendation cache hits.",
        "# TYPE recs_cache_hits_total counter",
        f"recs_cache_hits_total {hits}",
        "# HELP recs_cache_misses_total Recommendation cache misses.",
        "# TYPE recs_cache_misses_total counter",
        f"recs_cache_misses_total {misses}",
        "",
        "# HELP recs_request_latency_ms Request latency in milliseconds.",
        "# TYPE recs_request_latency_ms histogram",
    ]
    for b in _LAT_BUCKETS_MS:
        lines.append(f'recs_request_latency_ms_bucket{{le="{b}"}} {lat_counts[b]}')
    lines.append(f'recs_request_latency_ms_bucket{{le="+Inf"}} {lat_inf}')
    lines.append(f"recs_request_latency_ms_sum {lat_sum}")
    lines.append(f"recs_request_latency_ms_count {lat_inf}")
    lines.append("")

    lines += [
        "# HELP recs_stale_ratio Ratio of stale availability on the slate.",
        "# TYPE recs_stale_ratio histogram",
    ]
    for b in _STALE_BUCKETS:
        lines.append(f'recs_stale_ratio_bucket{{le="{b}"}} {stale_counts[b]}')
    lines.append(f'recs_stale_ratio_bucket{{le="+Inf"}} {stale_inf}')
    lines.append(f"recs_stale_ratio_sum {stale_sum}")
    lines.append(f"recs_stale_ratio_count {stale_inf}")
    lines.append("")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Dependency-free lite API (offline/sandbox friendly).")
    p.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    args = p.parse_args(argv)

    httpd = ThreadingHTTPServer((args.host, args.port), _Handler)
    print(f"Recs lite API listening on http://{args.host}:{args.port} (pid={os.getpid()})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
