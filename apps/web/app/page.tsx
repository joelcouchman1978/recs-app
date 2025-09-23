"use client"
import React, { useEffect, useState } from 'react'
import { ApiClient } from '../../../packages/shared/src/client'
import type { RecommendationItem } from '../../../packages/shared/src/api-types'
import { RecCard } from '@/components/RecCard'
import { MoreDrawer } from '../components/MoreDrawer'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Page() {
  const [data, setData] = useState<RecommendationItem[] | null>(null)
  const [email, setEmail] = useState('demo@local.test')
  const [token, setToken] = useState<string | null>(null)
  const [profile, setProfile] = useState<'ross'|'wife'|'son'|'family'>('ross')
  const [intent, setIntent] = useState<'default'|'short_tonight'|'weekend_binge'|'comfort'|'surprise'>('default')
  const [likeId, setLikeId] = useState<string | null>(null)
  const [seed, setSeed] = useState<number | undefined>(undefined)
  const [profiles, setProfiles] = useState<{ id: number, name: string, boundaries: Record<string, boolean> }[] | null>(null)
  const [watchlist, setWatchlist] = useState<Set<string>>(new Set())
  const [debugEnabled, setDebugEnabled] = useState(false)
  const [coverageThreshold, setCoverageThreshold] = useState(0.4)
  const [fitInfoOpen, setFitInfoOpen] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [toastFade, setToastFade] = useState(false)
  const [likeTitle, setLikeTitle] = useState<string | null>(null)
  const client = new ApiClient({ baseUrl: API })
  const coverage = React.useMemo(() => {
    if (!data || profile !== 'family') return null as null | { Ross: boolean; Wife: boolean; Son: boolean }
    const cov = { Ross: false, Wife: false, Son: false }
    for (const it of data as any[]) {
      const fb = (it as any).fit_by_profile as Array<{ name: string; score: number }> | undefined
      if (!fb) continue
      for (const fp of fb) {
        if ((fp.name === 'Ross' || fp.name === 'Wife' || fp.name === 'Son') && typeof fp.score === 'number' && fp.score >= 0.4) {
          ;(cov as any)[fp.name] = true
        }
      }
    }
    return cov
  }, [data, profile])

  const coverageMax = React.useMemo(() => {
    if (!data || profile !== 'family') return null as null | { Ross: number; Wife: number; Son: number }
    const max: any = { Ross: 0, Wife: 0, Son: 0 }
    for (const it of data as any[]) {
      const fb = (it as any).fit_by_profile as Array<{ name: string; score: number }> | undefined
      if (!fb) continue
      for (const fp of fb) {
        if ((fp.name === 'Ross' || fp.name === 'Wife' || fp.name === 'Son') && typeof fp.score === 'number') {
          max[fp.name] = Math.max(max[fp.name], fp.score)
        }
      }
    }
    return max as { Ross: number; Wife: number; Son: number }
  }, [data, profile])

  const load = async (tok: string, prof = profile, intentArg = intent, like: string | null = likeId) => {
    const recs = await client.getRecommendations({ for_: prof, intent: intentArg, like_id: like ?? undefined }, tok, { seed })
    setData(recs)
  }

  useEffect(() => {
    ;(async () => {
      // parse seed from URL if present
      try {
        const sp = new URL(window.location.href).searchParams
        const seedParam = sp.get('seed')
        if (seedParam) setSeed(Number(seedParam))
      } catch {}
      let tok: string | null = null
      try {
        const { token } = await client.authLogin({ email })
        tok = token
      } catch {
        const { token } = await client.authMagic({ email })
        tok = token
      }
      setToken(tok!)
      try {
        const ps = await client.getProfiles(tok!)
        setProfiles(ps as any)
      } catch {}
      await load(tok!)
      try {
        const h = await client.getHealth()
        setDebugEnabled(!!h.debug)
        if (typeof (h as any).family_coverage_min_fit === 'number') setCoverageThreshold((h as any).family_coverage_min_fit)
      } catch {}
      // initial watchlist for the active profile (fallback to first profile)
      try {
        const pid = (profiles || []).find(p=>p.name.toLowerCase()===profile)?.id || (profiles?.[0]?.id ?? 1)
        const wl = await client.getWatchlist(pid, tok!)
        setWatchlist(new Set(wl.show_ids))
      } catch {}
    })()
  }, [])

  useEffect(() => {
    if (!toast) return
    setToastFade(false)
    const t1 = setTimeout(()=> setToastFade(true), 2500)
    const t2 = setTimeout(()=> { setToast(null); setToastFade(false) }, 3000)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [toast])

  useEffect(() => { if (token) load(token) }, [profile, intent, likeId, seed])

  // reload watchlist when profile changes or after profiles load
  useEffect(() => {
    (async () => {
      if (!token) return
      try {
        const pid = (profiles || []).find(p=>p.name.toLowerCase()===profile)?.id || (profiles?.[0]?.id ?? 1)
        const wl = await client.getWatchlist(pid, token)
        setWatchlist(new Set(wl.show_ids))
      } catch {}
    })()
  }, [profile, profiles, token])

  const rate = async (showId: string, primary: 0|1|2, tags?: string[], note?: string) => {
    if (!token) return
    const pid = (profiles || []).find(p=>p.name.toLowerCase()===profile)?.id || (profiles?.[0]?.id ?? 1)
    await client.postRating({ profile_id: pid, show_id: showId, primary, nuance_tags: tags && tags.length? tags: undefined, note }, token)
    await load(token)
  }

  const addToWatchlist = async (showId: string) => {
    if (!token) return
    const pid = (profiles || []).find(p=>p.name.toLowerCase()===profile)?.id || (profiles?.[0]?.id ?? 1)
    try {
      await client.postWatchlistAdd({ profile_id: pid, show_id: showId }, token)
      setToast('Added to watchlist')
      setWatchlist(prev => new Set(prev).add(showId))
    } catch (e) {
      setToast('Failed to add to watchlist')
    }
  }

  const removeFromWatchlist = async (showId: string) => {
    if (!token) return
    const pid = (profiles || []).find(p=>p.name.toLowerCase()===profile)?.id || (profiles?.[0]?.id ?? 1)
    try {
      await client.deleteWatchlist({ profile_id: pid, show_id: showId }, token)
      setToast('Removed from watchlist')
      setWatchlist(prev => { const s = new Set(prev); s.delete(showId); return s })
    } catch (e) {
      setToast('Failed to remove from watchlist')
    }
  }

  const banWarning = async (warning: string) => {
    if (!token || !profiles) return
    const map: any = { ross: 'Ross', wife: 'Wife', son: 'Son' }
    const pname = map[profile]
    const p = profiles.find(p => p.name === pname)
    if (!p) return
    const newB = { ...(p.boundaries || {}), [warning]: true }
    await client.postProfileBoundaries({ name: p.name, boundaries: newB }, token)
    // refresh profiles and recs
    try { setProfiles(await client.getProfiles(token) as any) } catch {}
    await load(token)
  }

  return (
    <main className="max-w-3xl mx-auto py-10 px-4 space-y-4">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Personalised TV Recommender</h1>
        <div className="flex items-center gap-4 text-sm">
          <a className="underline" href="/onboarding">Onboarding</a>
          <a className="underline" href="/profiles">Profiles</a>
          <a className="underline" href="/watchlist">Watchlist{watchlist.size>0?` (${watchlist.size})`:''}</a>
          <a className="underline" href="/admin">Admin</a>
          {debugEnabled && <span className="text-[10px] px-2 py-0.5 rounded bg-purple-100 border border-purple-200 text-purple-900">debug</span>}
        </div>
      </header>
      <div className="flex items-center gap-2 text-sm">
        <span className="text-gray-600">Profile:</span>
        {(['ross','wife','son','family'] as const).map(p => (
          <button key={p} onClick={()=>setProfile(p)} className={`px-2 py-1 rounded border ${profile===p?'bg-black text-white':'bg-white'}`}>{p}</button>
        ))}
        <span className="ml-4 text-gray-600">Intent:</span>
        {(['default','short_tonight','weekend_binge','comfort','surprise'] as const).map(i => (
          <button key={i} onClick={()=>setIntent(i)} className={`px-2 py-1 rounded border ${intent===i?'bg-black text-white':'bg-white'}`}>{i.replace('_',' ')}</button>
        ))}
        {likeId && (
          <div className="ml-4 flex items-center gap-2">
            <span className="text-xs">Anchored to: {likeTitle || 'this show'}</span>
            <button onClick={()=>{setLikeId(null); setLikeTitle(null)}} className="px-2 py-1 rounded border text-xs">Clear filter</button>
          </div>
        )}
      </div>

      {!data && <div>Loading recommendations…</div>}
      {data && (
        <div className="space-y-4">
          {profile === 'family' && coverage && (
            <div className="rounded border bg-purple-50 p-3 text-xs text-purple-900">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="font-semibold">Family coverage</span>
                <span className={`mr-2 ${coverage.Ross? '':'opacity-50'}`} title={coverageMax?`Top fit for Ross: ${(coverageMax.Ross||0).toFixed(2)}`:''}>Ross {coverage.Ross? '✓':'—'}</span>
                <span className={`mr-2 ${coverage.Wife? '':'opacity-50'}`} title={coverageMax?`Top fit for Wife: ${(coverageMax.Wife||0).toFixed(2)}`:''}>Wife {coverage.Wife? '✓':'—'}</span>
                <span className={`${coverage.Son? '':'opacity-50'}`} title={coverageMax?`Top fit for Son: ${(coverageMax.Son||0).toFixed(2)}`:''}>Son {coverage.Son? '✓':'—'}</span>
              </div>
              <div className="mt-1 text-[10px] text-purple-800 flex items-center gap-2">
                <span>✓ indicates at least one item with fit ≥ {coverageThreshold.toFixed(2)} for each member</span>
                <button className="underline" onClick={()=>setFitInfoOpen(true)}>What is fit?</button>
                </div>
              {/* Strong pick or warning banner */}
              <div className="mt-2" data-test="family-coverage">
                {Array.isArray(data) && data.some((it:any)=> it.family_strong) ? (
                  <div className="rounded-2xl px-3 py-2 bg-emerald-50 text-emerald-800" data-test="family-strong-banner">
                    Strong family pick locked in.
                  </div>
                ) : (
                  <div className="rounded-2xl px-3 py-2 bg-amber-50 text-amber-900" data-test="family-warning-banner">
                    No single title is a strong fit for everyone — showing best shared options.
                  </div>
                )}
              </div>
            </div>
          )}
          {data.map((rec) => (
            <div key={rec.id} className="space-y-2">
              <RecCard
                rec={rec as any}
                onRate={(p,t,n)=>rate(rec.id, p, t, n)}
                onMoreLike={()=>{setLikeId(rec.id); setLikeTitle(rec.title)}}
                onWatchlistAdd={!watchlist.has(rec.id) ? ()=>addToWatchlist(rec.id) : undefined}
                onWatchlistRemove={watchlist.has(rec.id) ? ()=>removeFromWatchlist(rec.id) : undefined}
                moreLink={`/more/${rec.id}`}
                inWatchlist={watchlist.has(rec.id)}
                More={<MoreDrawer showId={rec.id} apiBase={API} badges={(rec as any).similar_because} />}
              />
              {(rec.warnings && rec.warnings.length>0) && (
                <div className="text-xs text-gray-700 flex items-center gap-2">
                  <span>Hide content with:</span>
                  {rec.warnings.slice(0,3).map((w:string, i:number)=> (
                    <button key={i} onClick={()=>{banWarning(w); setToast(`Hiding content with ${w}`)}} className="px-2 py-1 rounded border bg-white">{w}</button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      {toast && (
        <div className={`fixed bottom-4 right-4 bg-black text-white text-sm px-3 py-2 rounded shadow transition-opacity duration-500 ${toastFade?'opacity-0':'opacity-100'}`}>{toast}</div>
      )}
    </main>
    {fitInfoOpen && (
      <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={()=>setFitInfoOpen(false)}>
        <div className="bg-white rounded shadow p-4 max-w-md mx-4 text-sm" onClick={(e)=>e.stopPropagation()}>
          <div className="font-semibold mb-2">About fit scores</div>
          <p className="text-gray-700 mb-2">Fit is a per-person score computed from the same factors as recommendations (genres/creators overlap, context intent, preferences). In Family Mix, we select items on a Pareto frontier and then balance across members.</p>
          <p className="text-gray-700 mb-2">Coverage ensures each member has at least one item with fit ≥ {coverageThreshold.toFixed(2)} when possible. You can adjust this threshold via the server’s environment variable <code>FAMILY_COVERAGE_MIN_FIT</code>.</p>
          <div className="text-right mt-2">
            <button className="px-3 py-1 rounded border" onClick={()=>setFitInfoOpen(false)}>Close</button>
          </div>
        </div>
      </div>
    )}
  )
}
