from __future__ import annotations

from typing import Any

from .lite_server import _build_recommendations, _render_metrics


def _first_id(payload: Any) -> str | None:
    items = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
    if not isinstance(items, list) or not items:
        return None
    it0 = items[0]
    if not isinstance(it0, dict):
        return None
    v = it0.get("id")
    return v if isinstance(v, str) else None


def main() -> int:
    def ok(msg: str) -> None:
        print(f"✅ {msg}")

    def fail(msg: str) -> int:
        print(f"❌ {msg}")
        return 1

    ok("lite smoke (no sockets)")

    m = _render_metrics()
    required = [
        "recs_build_info",
        "recs_request_latency_ms_bucket",
        "recs_cache_hits_total",
        "recs_cache_misses_total",
        "recs_stale_ratio_bucket",
    ]
    missing = [r for r in required if r not in m]
    if missing:
        return fail(f"metrics missing: {', '.join(missing)}")
    ok("metrics names present")

    a = _build_recommendations(profile="ross", intent="default", seed=99, explain=False)
    b = _build_recommendations(profile="ross", intent="default", seed=99, explain=False)
    aid = _first_id(a)
    bid = _first_id(b)
    if not aid or aid != bid:
        return fail("seeded determinism drift")
    ok("seeded determinism stable")

    fm = _build_recommendations(profile="family", intent="family_mix", seed=99, explain=True)
    if not isinstance(fm, dict) or "family" not in fm:
        return fail("family meta missing")
    fam = fm.get("family") or {}
    locked = fam.get("strong_locked_ids") if isinstance(fam, dict) else None
    if not isinstance(locked, list) or len(locked) == 0:
        return fail("family guardrail missing strong_locked_ids")
    ok("family guardrail meta present")

    ok("all lite smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
