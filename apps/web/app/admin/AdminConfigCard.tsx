"use client";
import { useEffect, useState } from "react";

interface ConfigSummary {
  version: string;
  sha: string | null;
  env: string;
  thresholds: {
    family_strong_min_fit: number;
    family_strong_rule: string;
    offers_stale_days: number;
    season_strict: boolean;
    recs_target_p95_ms: number;
  };
}

export function AdminConfigCard() {
  const [cfg, setCfg] = useState<ConfigSummary | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setErr(null);
    try {
      const res = await fetch(`/api/admin/config/summary`);
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      setCfg(data as ConfigSummary);
    } catch (e: any) {
      setErr(e?.message || "failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <div className="border rounded p-4" data-test="admin-config-summary">
      <div className="flex items-center justify-between">
        <div className="font-medium">Config Summary</div>
        <button className="text-sm underline" onClick={load} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      {err && (
        <p className="mt-2 text-sm text-red-700">Unable to load config (is /admin/config/summary implemented?)</p>
      )}
      {cfg && (
        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="rounded-xl bg-gray-50 p-3">
            <div className="text-xs uppercase tracking-wide opacity-70">Build</div>
            <div className="mt-1 text-sm">Version: <span className="font-mono">{cfg.version}</span></div>
            <div className="text-sm">SHA: <span className="font-mono">{cfg.sha ?? "unknown"}</span></div>
            <div className="text-sm">Env: <span className="font-mono">{cfg.env}</span></div>
          </div>
          <div className="rounded-xl bg-gray-50 p-3">
            <div className="text-xs uppercase tracking-wide opacity-70">Thresholds</div>
            <ul className="mt-1 text-sm space-y-1">
              <li>Family strong min fit: <span className="font-mono">{cfg.thresholds.family_strong_min_fit}</span></li>
              <li>Family strong rule: <span className="font-mono">{cfg.thresholds.family_strong_rule}</span></li>
              <li>Offers stale days: <span className="font-mono">{cfg.thresholds.offers_stale_days}</span></li>
              <li>Season strict: <span className="font-mono">{String(cfg.thresholds.season_strict)}</span></li>
              <li>Recs target p95 ms: <span className="font-mono">{cfg.thresholds.recs_target_p95_ms}</span></li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
