"use client"
import React, { useEffect, useState } from 'react'
import { ApiClient } from '../../../../../packages/shared/src/client'
import type { RecommendationItem, ShowDetail } from '../../../../../packages/shared/src/api-types'
import { RecCard } from '../../../components/RecCard'
import { MoreDrawer } from '../../../components/MoreDrawer'
import { useSearchParams, useRouter, usePathname } from 'next/navigation'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function MoreLikeThisPage({ params }: { params: { id: string } }) {
  const [data, setData] = useState<RecommendationItem[] | null>(null)
  const [email] = useState('demo@local.test')
  const [token, setToken] = useState<string | null>(null)
  const [profile, setProfile] = useState<'ross'|'wife'|'son'|'family'>('ross')
  const [intent, setIntent] = useState<'default'|'short_tonight'|'weekend_binge'|'comfort'|'surprise'>('default')
  const [anchor, setAnchor] = useState<ShowDetail | null>(null)
  const [debugEnabled, setDebugEnabled] = useState(false)
  const [inspect, setInspect] = useState<Array<{ id: string, title: string, scores: number[] }> | null>(null)
  const client = new ApiClient({ baseUrl: API })
  const search = useSearchParams()
  const router = useRouter()
  const pathname = usePathname()
  const isInspect = (search.get('inspect') === '1' || search.get('debug') === '1')

  const load = async (tok: string) => {
    const recs = await client.getRecommendations({ for_: profile, intent, like_id: params.id }, tok)
    setData(recs)
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
      try { setAnchor(await client.getShow(params.id)) } catch {}
      try { const h = await client.getHealth(); setDebugEnabled(!!h.debug) } catch {}
      await load(tok!)
    })()
  }, [])

  useEffect(() => { if (token) load(token) }, [profile, intent, params.id])
  useEffect(() => {
    (async () => {
      if (!token || !debugEnabled) return
      if ((search.get('inspect') || search.get('debug')) === '1') {
        try {
          const rows = await client.getDebugRecommendations({ for_: profile, intent }, token)
          setInspect(rows)
        } catch {}
      } else {
        setInspect(null)
      }
    })()
  }, [token, debugEnabled, profile, intent, search])

  return (
    <main className="max-w-3xl mx-auto py-10 px-4 space-y-4">
      <header className="flex items-center justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold">More like this</h1>
          <div className="mt-1 text-sm text-gray-800 truncate flex items-center gap-2 flex-wrap">
            {anchor ? (
              <>
                <span className="font-medium">{anchor.title}</span>{anchor.year_start ? ` (${anchor.year_start})` : ''}
                {Array.isArray(anchor.metadata?.creators) && anchor.metadata!.creators.length > 0 && (
                  <span className="ml-2 text-gray-600">by {(anchor.metadata!.creators as string[]).slice(0,2).join(', ')}</span>
                )}
                {anchor.metadata?.au_rating && (
                  <span className="text-[10px] px-2 py-0.5 rounded border bg-blue-50 border-blue-200 text-blue-900">AU {String(anchor.metadata.au_rating)}</span>
                )}
              </>
            ) : (
              <span className="text-gray-500">Loading anchor…</span>
            )}
          </div>
          {anchor && Array.isArray(anchor.metadata?.genres) && (anchor.metadata!.genres as string[]).length > 0 && (
            <div className="mt-1 flex flex-wrap gap-2">
              {(anchor.metadata!.genres as string[]).slice(0,3).map((g, i) => (
                <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-gray-100 border">{g}</span>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-4 text-sm">
          <a className="underline" href="/">Home</a>
          <a className="underline" href="/onboarding">Onboarding</a>
          <a className="underline" href="/profiles">Profiles</a>
          <a className="underline" href="/admin">Admin</a>
          {debugEnabled && (
            <>
              <span className="text-[10px] px-2 py-0.5 rounded bg-purple-100 border border-purple-200 text-purple-900">debug</span>
              <button
                onClick={() => {
                  const params = new URLSearchParams(search as any)
                  if (isInspect) {
                    params.delete('inspect')
                    params.delete('debug')
                  } else {
                    params.set('inspect', '1')
                  }
                  const q = params.toString()
                  router.replace(q ? `${pathname}?${q}` : pathname)
                }}
                className={`text-[10px] px-2 py-0.5 rounded border ${isInspect? 'bg-purple-600 text-white border-purple-700': 'bg-white'}`}
                title="Toggle debug inspector"
              >
                {isInspect ? 'Inspector: On' : 'Inspector: Off'}
              </button>
            </>
          )}
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
      </div>

      {!data && <div>Loading…</div>}
      {inspect && (
        <div className="rounded border p-3 bg-purple-50">
          <div className="text-xs font-semibold mb-2">Debug inspector (Pareto frontier per-profile scores)</div>
          <div className="text-[11px] grid grid-cols-1 gap-2">
            {inspect.map((it, idx) => (
              <div key={it.id} className="flex items-center justify-between">
                <div className="truncate">
                  <span className="text-gray-700">{idx+1}.</span> <span className="font-medium">{it.title}</span>
                </div>
                <div className="text-gray-600">[{it.scores.map(s=>s.toFixed(2)).join(' · ')}]</div>
              </div>
            ))}
          </div>
        </div>
      )}
      {data && (
        <div className="space-y-4">
          {data.map((rec) => (
            <div key={rec.id} className="space-y-2">
              <RecCard
                rec={rec as any}
                moreLink={`/more/${rec.id}`}
                More={<MoreDrawer showId={rec.id} apiBase={API} badges={(rec as any).similar_because} />}
              />
            </div>
          ))}
        </div>
      )}
    </main>
  )
}
