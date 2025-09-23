"use client"
import React, { useEffect, useState } from 'react'
import { ApiClient } from '../../../../../packages/shared/src/client'
import { MoreDrawer } from '../../../components/MoreDrawer'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type Profile = { id: number; name: string }
type Show = { id: string; title: string; year_start?: number|null }

export default function WatchlistPage() {
  const [email] = useState('demo@local.test')
  const [token, setToken] = useState<string | null>(null)
  const [profiles, setProfiles] = useState<Profile[] | null>(null)
  const [profile, setProfile] = useState<'ross'|'wife'|'son'>('ross')
  const [showIds, setShowIds] = useState<string[]>([])
  const [shows, setShows] = useState<Show[]>([])
  const [toast, setToast] = useState<string | null>(null)
  const [toastFade, setToastFade] = useState(false)
  const client = new ApiClient({ baseUrl: API })

  useEffect(() => {
    ;(async () => {
      const { token } = await client.authMagic({ email })
      setToken(token)
      try {
        const ps = await client.getProfiles(token)
        setProfiles(ps as any)
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

  const activeProfileId = (): number | null => {
    if (!profiles) return null
    const pid = (profiles || []).find(p=>p.name.toLowerCase()===profile)?.id || (profiles?.[0]?.id ?? null)
    return pid ?? null
  }

  const loadWatchlist = async () => {
    if (!token) return
    const pid = activeProfileId()
    if (!pid) return
    try {
      const wl = await client.getWatchlist(pid, token)
      setShowIds(wl.show_ids)
      // fetch show summaries
      const arr: Show[] = []
      for (const id of wl.show_ids) {
        try {
          const sd = await client.getShow(id)
          arr.push({ id: sd.id, title: sd.title, year_start: sd.year_start })
        } catch {}
      }
      setShows(arr)
    } catch {}
  }

  useEffect(() => { loadWatchlist() }, [token, profile, profiles])

  const remove = async (id: string) => {
    if (!token) return
    const pid = activeProfileId()
    if (!pid) return
    try {
      await client.deleteWatchlist({ profile_id: pid, show_id: id }, token)
      setShowIds(prev => prev.filter(x=>x!==id))
      setShows(prev => prev.filter(x=>x.id!==id))
      setToast('Removed from watchlist')
    } catch {
      setToast('Failed to remove')
    }
  }

  return (
    <main className="max-w-3xl mx-auto py-10 px-4 space-y-4">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Watchlist</h1>
        <div className="flex items-center gap-4 text-sm">
          <a className="underline" href="/">Home</a>
          <a className="underline" href="/onboarding">Onboarding</a>
          <a className="underline" href="/profiles">Profiles</a>
          <a className="underline" href="/admin">Admin</a>
        </div>
      </header>
      <div className="flex items-center gap-2 text-sm">
        <span className="text-gray-600">Profile:</span>
        {(['ross','wife','son'] as const).map(p => (
          <button key={p} onClick={()=>setProfile(p)} className={`px-2 py-1 rounded border ${profile===p?'bg-black text-white':'bg-white'}`}>{p}</button>
        ))}
      </div>

      {showIds.length === 0 && (
        <div className="text-gray-600">No items yet. Add shows from the recommendations page.</div>
      )}

      <div className="space-y-3">
        {shows.map(s => (
          <div key={s.id} className="rounded border bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-semibold">{s.title}{s.year_start ? ` (${s.year_start})` : ''}</div>
                <div className="text-xs text-gray-500">ID: {s.id}</div>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <button onClick={()=>remove(s.id)} className="px-2 py-1 rounded border">Remove</button>
              </div>
            </div>
            <div className="mt-2">
              <MoreDrawer showId={s.id} apiBase={API} />
            </div>
          </div>
        ))}
      </div>

      {toast && (
        <div className={`fixed bottom-4 right-4 bg-black text-white text-sm px-3 py-2 rounded shadow transition-opacity duration-500 ${toastFade?'opacity-0':'opacity-100'}`}>{toast}</div>
      )}
    </main>
  )}

