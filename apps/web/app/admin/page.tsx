"use client"
import React, { useEffect, useState } from 'react'
import { ApiClient } from '../../../../packages/shared/src/client'
import { AdminConfigCard } from './AdminConfigCard'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type Status = {
  justwatch: { count_shows?: number; count_rows?: number; timestamp?: string } | null
  serializd: { count_ratings?: number; timestamp?: string } | null
}

export default function AdminPage() {
  const [status, setStatus] = useState<Status | null>(null)
  const [busy, setBusy] = useState(false)
  const [queue, setQueue] = useState<any | null>(null)
  const [health, setHealth] = useState<any | null>(null)
  const [dryRun, setDryRun] = useState(true)
  const [previewTitle, setPreviewTitle] = useState('')
  const [previewYear, setPreviewYear] = useState<string>('')
  const [previewOffers, setPreviewOffers] = useState<Array<{ platform: string; offer_type: string; quality?: string|null }>|null>(null)
  const [providers, setProviders] = useState<Record<string,string>|null>(null)
  const [providersOverrides, setProvidersOverrides] = useState<{ active: boolean, raw?: string }|null>(null)
  const [providerQuery, setProviderQuery] = useState('')
  const [fresh, setFresh] = useState<any | null>(null)
  const [jwSample, setJwSample] = useState<any | null>(null)
  const [szPreview, setSzPreview] = useState<any | null>(null)
  const [email] = useState('demo@local.test')
  const [token, setToken] = useState<string | null>(null)
  const client = new ApiClient({ baseUrl: API })
  const load = async (tok: string) => {
    try { setStatus(await client.getAdminStatus(tok)) } catch {}
    try { setQueue(await client.getAdminQueue(tok)) } catch {}
    try { setHealth(await client.getHealth()) } catch {}
    try {
      const r = await fetch(`${API}/admin/providers`, { headers:{ Authorization: `Bearer ${tok}` } })
      if (r.ok) { const js = await r.json(); setProviders(js.providers || null); setProvidersOverrides({ active: !!js.overrides_active, raw: js.raw_override || undefined }) }
    } catch {}
    try {
      const f = await fetch(`${API}/admin/freshness`, { headers:{ Authorization: `Bearer ${tok}` } })
      if (f.ok) setFresh(await f.json())
    } catch {}
  }
  useEffect(() => {
    ;(async () => {
      let tok: string | null = null
      try {
        const { token } = await client.authLogin({ email })
        tok = token
      } catch {
        const { token } = await client.authMagic({ email })
        tok = token
      }
      setToken(tok!)
      await load(tok!)
    })()
  }, [])

  const trigger = async (source: 'justwatch'|'serializd') => {
    setBusy(true)
    if (!token) return
    await client.postAdminSync(source, token, { dry_run: dryRun })
    // give worker a moment, then reload status
    setTimeout(()=> token && load(token), 1500)
    setBusy(false)
  }

  const rebuildEmbeddings = async () => {
    setBusy(true)
    if (!token) return
    await client.postRebuildEmbeddings(token)
    setBusy(false)
  }

  const preview = async () => {
    if (!token || !previewTitle) return
    const q = new URLSearchParams({ title: previewTitle })
    if (previewYear) q.set('year', previewYear)
    const r = await fetch(`${API}/admin/preview/availability?${q.toString()}`, { headers:{ Authorization: `Bearer ${token}` } })
    if (r.ok) {
      const js = await r.json()
      setPreviewOffers(js.offers || [])
    }
  }

  const previewSerializd = async () => {
    if (!token) return
    const r = await fetch(`${API}/admin/preview/serializd`, { headers:{ Authorization: `Bearer ${token}` } })
    if (r.ok) setSzPreview(await r.json())
  }

  const sampleJW = async () => {
    if (!token) return
    const r = await fetch(`${API}/admin/preview/sample_justwatch?limit=5`, { headers:{ Authorization: `Bearer ${token}` } })
    if (r.ok) setJwSample(await r.json())
  }

  return (
    <main className="max-w-2xl mx-auto py-10 px-4 space-y-6">
      <h1 className="text-2xl font-semibold">Admin</h1>
      <div className="space-y-3">
        {process.env.NODE_ENV !== 'production' && (
          <div className="border rounded p-4">
            <div className="font-medium">Monitoring (dev)</div>
            <div className="mt-2 text-sm flex flex-wrap gap-3">
              <a className="underline" href="http://localhost:9090" target="_blank" rel="noreferrer">Open Prometheus</a>
              <a className="underline" href="http://localhost:3001" target="_blank" rel="noreferrer">Open Grafana</a>
            </div>
          </div>
        )}
        <AdminConfigCard />
        <div className="border rounded p-4">
          <div className="font-medium">Freshness</div>
          <div className="text-sm mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div>
              <div className="text-gray-700">JustWatch offers</div>
              <div className="text-xs text-gray-600">Rows: {fresh?.offers_rows ?? '—'}</div>
              <div className="text-xs text-gray-600">Last checked: {fresh?.offers_last_checked ?? '—'}</div>
            </div>
            <div>
              <div className="text-gray-700">Serializd history</div>
              <div className="text-xs text-gray-600">Rows: {fresh?.serializd_rows ?? '—'}</div>
              <div className="text-xs text-gray-600">Last seen: {fresh?.serializd_last_seen ?? '—'}</div>
            </div>
          </div>
        </div>
        <div className="border rounded p-4">
          <div className="font-medium">Configuration</div>
          <div className="text-sm text-gray-700 mt-1">Family coverage min fit: {typeof (health as any)?.family_coverage_min_fit === 'number' ? (health as any).family_coverage_min_fit.toFixed(2) : '—'}</div>
          <div className="text-xs text-gray-500 mt-1">Set via env FAMILY_COVERAGE_MIN_FIT</div>
          <div className="mt-2 text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={dryRun} onChange={(e)=>setDryRun(e.target.checked)} /> Dry run syncs (log only)
            </label>
          </div>
        </div>

        <div className="border rounded p-4">
          <div className="font-medium">JustWatch Preview (AU)</div>
          <div className="text-sm text-gray-700 mt-2 flex items-center gap-2">
            <input className="border rounded px-2 py-1 text-sm" placeholder="Title" value={previewTitle} onChange={e=>setPreviewTitle(e.target.value)} />
            <input className="border rounded px-2 py-1 text-sm w-24" placeholder="Year" value={previewYear} onChange={e=>setPreviewYear(e.target.value)} />
            <button className="px-3 py-1 rounded border" onClick={preview} disabled={!previewTitle}>Preview</button>
          </div>
          {previewOffers && (
            <div className="mt-2 text-sm">
              {previewOffers.length===0 && <div className="text-gray-600">No offers found.</div>}
              {previewOffers.length>0 && (
                <ul className="list-disc pl-5">
                  {previewOffers.slice(0,10).map((o,i)=> (
                    <li key={i}>{o.platform} — {o.offer_type}{o.quality?` · ${o.quality}`:''}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        <div className="border rounded p-4">
          <div className="font-medium">Dry-run Samples</div>
          <div className="mt-2 flex items-center gap-2 text-sm">
            <button className="px-3 py-1 rounded border" onClick={sampleJW}>Sample JustWatch (5 shows)</button>
            <button className="px-3 py-1 rounded border" onClick={previewSerializd}>Preview Serializd ratings</button>
          </div>
          {jwSample && (
            <div className="mt-2 text-xs text-gray-800">
              <div>Shows sampled: {jwSample.count_shows} · Offers mapped: {jwSample.count_offers}</div>
            </div>
          )}
          {szPreview && (
            <div className="mt-2 text-xs text-gray-800">
              <div>Serializd ratings: {szPreview.count}</div>
            </div>
          )}
        </div>

        <div className="border rounded p-4">
          <div className="font-medium">Provider Map (AU)</div>
          <div className="mt-2 flex items-center gap-2 text-sm">
            <input className="border rounded px-2 py-1 text-sm" placeholder="Search id or name" value={providerQuery} onChange={e=>setProviderQuery(e.target.value)} />
            <span className="text-xs text-gray-600">{providersOverrides?.active ? 'Overrides active' : 'Base map'}</span>
          </div>
          {!providers && <div className="text-sm text-gray-600 mt-2">No mapping loaded.</div>}
          {providers && (
            <div className="text-xs text-gray-800 mt-2 max-h-64 overflow-auto border rounded p-2">
              {Object.entries(providers)
                .filter(([id, name]) => {
                  const q = providerQuery.toLowerCase().trim()
                  if (!q) return true
                  return id.includes(q) || String(name).toLowerCase().includes(q)
                })
                .sort((a,b)=> Number(a[0]) - Number(b[0]))
                .map(([id, name]) => (
                  <div key={id}>{id}: {name}</div>
              ))}
            </div>
          )}
          <div className="mt-2 text-sm flex items-center gap-2">
            <button className="px-3 py-1 rounded border" onClick={() => {
              if (!providers) return
              const blob = new Blob([JSON.stringify(providers, null, 2)], { type: 'application/json' })
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = 'providers_map.json'
              a.click()
              URL.revokeObjectURL(url)
            }}>Download JSON</button>
            {providersOverrides?.raw && (
              <button className="px-3 py-1 rounded border" onClick={() => {
                const blob = new Blob([providersOverrides.raw!], { type: 'application/json' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = 'providers_override.json'
                a.click()
                URL.revokeObjectURL(url)
              }}>Download Overrides</button>
            )}
          </div>
        </div>

        <div className="border rounded p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">JustWatch AU</div>
              <div className="text-sm text-gray-600">Refresh availability (nightly + manual)</div>
            </div>
            <button disabled={busy} onClick={()=>trigger('justwatch')} className="px-3 py-1 rounded border">Sync</button>
          </div>
          <div className="text-sm mt-2">
            Last: {status?.justwatch?.timestamp ? new Date(status.justwatch.timestamp).toLocaleString() : '—'} ·
            Shows: {status?.justwatch?.count_shows ?? '—'} · Rows: {status?.justwatch?.count_rows ?? '—'}
          </div>
        </div>

        <div className="border rounded p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">Serializd</div>
              <div className="text-sm text-gray-600">Sync ratings/history (nightly + manual)</div>
            </div>
            <button disabled={busy} onClick={()=>trigger('serializd')} className="px-3 py-1 rounded border">Sync</button>
          </div>
          <div className="text-sm mt-2">
            Last: {status?.serializd?.timestamp ? new Date(status.serializd.timestamp).toLocaleString() : '—'} ·
            Ratings: {status?.serializd?.count_ratings ?? '—'}
          </div>
        </div>

        <div className="border rounded p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">Background Queue</div>
              <div className="text-sm text-gray-600">RQ status and counts</div>
            </div>
            <button disabled={busy} onClick={load} className="px-3 py-1 rounded border">Refresh</button>
          </div>
          <div className="text-sm mt-2">
            <div>Queue: {queue?.queue?.name || '—'} · size: {queue?.queue?.count ?? '—'}</div>
            <div>Started: {queue?.registries?.started ?? '—'} · Finished: {queue?.registries?.finished ?? '—'} · Failed: {queue?.registries?.failed ?? '—'} · Deferred: {queue?.registries?.deferred ?? '—'}</div>
          </div>
          <div className="mt-2">
            <button disabled={busy} onClick={rebuildEmbeddings} className="px-3 py-1 rounded border">Rebuild Embeddings</button>
          </div>
        </div>
      </div>
    </main>
  )
}
