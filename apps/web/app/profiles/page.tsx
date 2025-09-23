"use client"
import React, { useEffect, useState } from 'react'
import { ApiClient } from '../../../packages/shared/src/client'
import type { ProfileOut, ProfileCreate } from '../../../packages/shared/src/api-types'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type Boundaries = { [k: string]: boolean }

export default function ProfilesPage() {
  const [email, setEmail] = useState('demo@local.test')
  const [token, setToken] = useState<string | null>(null)
  const [profiles, setProfiles] = useState<ProfileOut[]>([])
  const [dirty, setDirty] = useState<Record<number, { boundaries: Boundaries; age_limit?: number|null }>>({})
  const client = new ApiClient({ baseUrl: API })
  const [toast, setToast] = useState<string | null>(null)
  const [toastFade, setToastFade] = useState(false)

  useEffect(() => {
    ;(async () => {
      const { token } = await client.authMagic({ email })
      setToken(token)
      const ps = await client.getProfiles(token)
      setProfiles(ps)
      const init: Record<number, { boundaries: Boundaries; age_limit?: number|null }> = {}
      ps.forEach(p => { init[p.id] = { boundaries: p.boundaries || {}, age_limit: p.age_limit ?? null } })
      setDirty(init)
    })()
  }, [])

  const toggle = (pid: number, key: string) => {
    setDirty(prev => ({ ...prev, [pid]: { ...prev[pid], boundaries: { ...prev[pid].boundaries, [key]: !prev[pid]?.boundaries?.[key] } } }))
  }
  const setAge = (pid: number, v: number) => setDirty(prev => ({ ...prev, [pid]: { ...prev[pid], age_limit: v } }))

  const save = async () => {
    if (!token) return
    const payload: ProfileCreate[] = profiles.map(p => ({ name: p.name, age_limit: dirty[p.id]?.age_limit ?? p.age_limit ?? undefined, boundaries: dirty[p.id]?.boundaries || p.boundaries }))
    await client.postProfiles(payload, token)
    setToast('Saved profile boundaries')
  }

  React.useEffect(() => {
    if (!toast) return
    setToastFade(false)
    const t1 = setTimeout(()=> setToastFade(true), 2500)
    const t2 = setTimeout(()=> { setToast(null); setToastFade(false) }, 3000)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [toast])

  const keys = ['violence','drug_abuse','language']

  const removeBoundary = async (pid: number, key: string) => {
    if (!token) return
    const p = profiles.find(p=>p.id===pid)
    if (!p) return
    const updated = { ...(dirty[pid]?.boundaries || p.boundaries || {}) }
    updated[key] = false
    await client.postProfileBoundaries({ name: p.name, boundaries: updated }, token)
    const ps = await client.getProfiles(token)
    setProfiles(ps)
    setDirty(prev => ({ ...prev, [pid]: { ...(prev[pid]||{}), boundaries: (ps.find(x=>x.id===pid)?.boundaries || {}) } }))
    setToast(`Removed boundary: ${key}`)
  }

  return (
    <main className="max-w-3xl mx-auto py-10 px-4 space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Profiles & Boundaries</h1>
        <a href="/" className="text-sm underline">Home</a>
      </header>

      <div className="text-sm">
        <label className="block text-xs text-gray-600">Email</label>
        <input className="border rounded px-3 py-2" value={email} onChange={e=>setEmail(e.target.value)} />
      </div>

      <div className="grid gap-4">
        {profiles.map(p => (
          <div key={p.id} className="border rounded p-4 bg-white">
            <div className="flex items-center justify-between">
              <div className="font-medium">{p.name}</div>
              <div className="text-sm">Age limit: <input type="number" min={0} max={21} className="w-20 border rounded px-2 py-1" value={dirty[p.id]?.age_limit ?? ''} onChange={e=>setAge(p.id, Number(e.target.value))} /></div>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
              {keys.map(k => (
                <label key={k} className="flex items-center gap-2">
                  <input type="checkbox" checked={!!dirty[p.id]?.boundaries?.[k]} onChange={()=>toggle(p.id, k)} />
                  <span>Avoid {k.replace('_',' ')}</span>
                </label>
              ))}
            </div>
            <div className="mt-3 text-xs text-gray-700">
              <div className="mb-1">Active boundaries:</div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(dirty[p.id]?.boundaries || {}).filter(([_,v])=>!!v).map(([k]) => (
                  <button key={k} onClick={()=>removeBoundary(p.id, k)} className="px-2 py-1 rounded border bg-white">{k} ✕</button>
                ))}
                {Object.values(dirty[p.id]?.boundaries || {}).filter(Boolean).length===0 && (
                  <span className="text-gray-500">None</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <button onClick={save} className="bg-black text-white px-4 py-2 rounded">Save</button>
      {toast && (
        <div className={`fixed bottom-4 right-4 bg-black text-white text-sm px-3 py-2 rounded shadow transition-opacity duration-500 ${toastFade?'opacity-0':'opacity-100'}`}>{toast}</div>
      )}
    </main>
  )
}
