"use client"
import React, { useEffect, useMemo, useState } from 'react'
import { ApiClient } from '../../../../packages/shared/src/client'
import type { ShowSummary } from '../../../../packages/shared/src/api-types'

export default function OnboardingPage() {
  const [email, setEmail] = useState('demo@local.test')
  const [token, setToken] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [toastFade, setToastFade] = useState(false)
  const [shows, setShows] = useState<ShowSummary[]>([])
  const [liked, setLiked] = useState<Record<string, boolean>>({})
  const [disliked, setDisliked] = useState<Record<string, boolean>>({})
  const [boundaries, setBoundaries] = useState<{ violence?: boolean; drug_abuse?: boolean; language?: boolean }>({})
  const [mood, setMood] = useState({ tone:2, pacing:2, complexity:2, humor:2, optimism:2 })
  const [constraints, setConstraints] = useState<{ ep_length_max?: number|null; seasons_max?: number|null; avoid_dnf?: boolean; avoid_cliffhangers?: boolean }>({ ep_length_max: 35, seasons_max: 5 })
  const [step, setStep] = useState<number>(1)
  const [profileId, setProfileId] = useState<number | null>(null)
  const [creatorsLike, setCreatorsLike] = useState<string[]>([])
  const [creatorsDislike, setCreatorsDislike] = useState<string[]>([])
  const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const client = new ApiClient({ baseUrl: base })

  useEffect(() => {
    ;(async () => {
      const { token } = await client.authMagic({ email })
      setToken(token)
      const js = await client.getShows(60)
      setShows(js)
      try {
        const ps = await client.getProfiles(token)
        setProfileId(ps?.[0]?.id || null)
      } catch {}
    })()
  }, [])

  const submit = async () => {
    if (!token) return
    const loves = Object.keys(liked).filter(id => liked[id])
    const dislikes = Object.keys(disliked).filter(id => disliked[id])
    const creators_like = creatorsLike
    const creators_dislike = creatorsDislike
    await client.postOnboarding({
      profile_id: profileId || 1,
      loves,
      dislikes,
      creators_like,
      creators_dislike,
      mood,
      constraints,
      boundaries,
    }, token)
    setToast('Saved. Head back to Home for recommendations.')
  }

  React.useEffect(() => {
    if (!toast) return
    setToastFade(false)
    const t1 = setTimeout(()=> setToastFade(true), 2500)
    const t2 = setTimeout(()=> { setToast(null); setToastFade(false) }, 3000)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [toast])

  return (
    <main className="max-w-3xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Onboarding</h1>
      <div className="space-y-2">
        <label className="block text-sm font-medium">Email</label>
        <input className="border rounded px-3 py-2 w-full" value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com" />
        <p className="text-xs text-gray-600">Magic login stub will use this email.</p>
      </div>

      {step === 1 && (
        <section>
          <h2 className="font-medium mb-2">Pick a few you like / dislike</h2>
          <div className="grid grid-cols-1 gap-2">
            {shows.slice(0, 20).map(s => (
              <div key={s.id} className="border rounded p-3 flex items-center justify-between">
                <div>
                  <div className="font-medium">{s.title}</div>
                  <div className="text-xs text-gray-600">{(s.metadata?.genres || []).join(', ')}</div>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <label className="flex items-center gap-1"><input type="checkbox" checked={!!liked[s.id]} onChange={e=> setLiked(prev=>({ ...prev, [s.id]: e.target.checked }))}/> Like</label>
                  <label className="flex items-center gap-1"><input type="checkbox" checked={!!disliked[s.id]} onChange={e=> setDisliked(prev=>({ ...prev, [s.id]: e.target.checked }))}/> Dislike</label>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {step === 2 && (
        <section>
          <h2 className="font-medium mb-2">Mood knobs</h2>
          {Object.entries(mood).map(([k,v]) => (
            <div key={k} className="mb-3">
              <label className="block text-sm font-medium mb-1">{k}</label>
              <input type="range" min={0} max={4} value={v} onChange={e=> setMood(prev=>({ ...prev, [k]: Number(e.target.value) }))} className="w-full" />
            </div>
          ))}
          <div className="mt-4">
            <div className="text-sm font-medium mb-2">Creators you like</div>
            <div className="flex flex-wrap gap-2">
              {Array.from(new Set(shows.flatMap(s => (s.metadata as any)?.creators || []))).slice(0,12).map((c:any)=> (
                <button key={c} onClick={()=> setCreatorsLike(prev => prev.includes(c) ? prev.filter(x=>x!==c) : [...prev, c])} className={`text-xs px-2 py-1 rounded border ${creatorsLike.includes(c)?'bg-black text-white':'bg-white'}`}>{c}</button>
              ))}
            </div>
            <div className="text-sm font-medium mt-3 mb-2">Creators to avoid</div>
            <div className="flex flex-wrap gap-2">
              {Array.from(new Set(shows.flatMap(s => (s.metadata as any)?.creators || []))).slice(0,12).map((c:any)=> (
                <button key={c} onClick={()=> setCreatorsDislike(prev => prev.includes(c) ? prev.filter(x=>x!==c) : [...prev, c])} className={`text-xs px-2 py-1 rounded border ${creatorsDislike.includes(c)?'bg-black text-white':'bg-white'}`}>{c}</button>
              ))}
            </div>
          </div>
        </section>
      )}

      {step === 3 && (
        <section>
          <h2 className="font-medium mb-2">Practical constraints</h2>
          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm">Max episode length (min)
              <input type="number" className="block border rounded px-2 py-1 mt-1" value={constraints.ep_length_max ?? ''} onChange={e=> setConstraints(prev=>({ ...prev, ep_length_max: Number(e.target.value) }))} />
            </label>
            <label className="text-sm">Max seasons
              <input type="number" className="block border rounded px-2 py-1 mt-1" value={constraints.seasons_max ?? ''} onChange={e=> setConstraints(prev=>({ ...prev, seasons_max: Number(e.target.value) }))} />
            </label>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
            {['avoid_dnf','avoid_cliffhangers'].map(k => (
              <label key={k} className="flex items-center gap-2">
                <input type="checkbox" checked={Boolean((constraints as any)[k])} onChange={e=> setConstraints(prev=>({ ...prev, [k]: e.target.checked }))} />
                <span>{k.replace('_',' ')}</span>
              </label>
            ))}
          </div>
        </section>
      )}

      {step === 4 && (
        <section>
          <h2 className="font-medium mb-2">Content boundaries</h2>
          <div className="grid grid-cols-2 gap-2">
            {['violence','drug_abuse','language'].map(k => (
              <label key={k} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={!!(boundaries as any)[k]} onChange={e=> setBoundaries(prev=>({ ...prev, [k]: e.target.checked }))} />
                <span>Avoid {k.replace('_',' ')}</span>
              </label>
            ))}
          </div>
        </section>
      )}

      <div className="flex items-center justify-between">
        <button disabled={step<=1} onClick={()=>setStep(s=>Math.max(1, s-1))} className="px-3 py-1 rounded border">Back</button>
        {step<4 ? (
          <button onClick={()=>setStep(s=>s+1)} className="px-3 py-1 rounded border">Next</button>
        ) : (
          <button onClick={submit} className="bg-black text-white px-4 py-2 rounded">Save</button>
        )}
      </div>

      <section>
        <h2 className="font-medium mb-2">Pick a few you like / dislike</h2>
        <div className="grid grid-cols-1 gap-2">
          {shows.slice(0, 20).map(s => (
            <div key={s.id} className="border rounded p-3 flex items-center justify-between">
              <div>
                <div className="font-medium">{s.title}</div>
                <div className="text-xs text-gray-600">{(s.metadata?.genres || []).join(', ')}</div>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <label className="flex items-center gap-1"><input type="checkbox" checked={!!liked[s.id]} onChange={e=> setLiked(prev=>({ ...prev, [s.id]: e.target.checked, ...(e.target.checked? { [s.id]: true } : {}) }))}/> Like</label>
                <label className="flex items-center gap-1"><input type="checkbox" checked={!!disliked[s.id]} onChange={e=> setDisliked(prev=>({ ...prev, [s.id]: e.target.checked }))}/> Dislike</label>
              </div>
            </div>
          ))}
        </div>
      </section>

      <button onClick={submit} className="bg-black text-white px-4 py-2 rounded">Save</button>
      {toast && (
        <div className={`fixed bottom-4 right-4 bg-black text-white text-sm px-3 py-2 rounded shadow transition-opacity duration-500 ${toastFade?'opacity-0':'opacity-100'}`}>{toast}</div>
      )}
    </main>
  )
}
