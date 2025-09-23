"use client"
import React, { useEffect, useState } from 'react'

type ShowDetail = {
  id: string
  title: string
  metadata?: any
  warnings?: string[]
  flags?: string[]
  availability: { platform: string; offer_type: string; quality?: string|null; leaving_at?: string|null }[]
}

export function MoreDrawer({ showId, apiBase, badges }: { showId: string; apiBase: string; badges?: string[] }) {
  const [open, setOpen] = useState(false)
  const [detail, setDetail] = useState<ShowDetail | null>(null)

  useEffect(() => {
    if (!open || detail) return
    ;(async () => {
      const r = await fetch(`${apiBase}/shows/${showId}`)
      setDetail(await r.json())
    })()
  }, [open])

  return (
    <div className="mt-3">
      <button onClick={()=>setOpen(v=>!v)} className="text-sm underline">{open ? 'Hide' : 'More'}</button>
      {open && detail && (
        <div className="mt-3 rounded border bg-gray-50 p-3 text-sm">
          <div className="font-medium">Spoiler-safe details</div>
          {detail.metadata?.synopsis && (
            <div className="mt-1 text-gray-800"><span className="font-medium">Synopsis:</span> {detail.metadata.synopsis}</div>
          )}
          {(detail.metadata?.age_rating || detail.metadata?.au_rating) && (
            <div className="mt-1 text-gray-800">Age rating: {detail.metadata?.au_rating ? (`AU ${detail.metadata.au_rating}`) : (detail.metadata?.age_rating)}</div>
          )}
          <div className="mt-1 text-gray-800">Creators: {(detail.metadata?.creators || []).join(', ') || '—'}</div>
          <div className="text-gray-800">Network/Region: {detail.metadata?.region || '—'}</div>
          <div className="text-gray-800">Episode length: {detail.metadata?.episode_length ? `${detail.metadata?.episode_length}m` : '—'} · Seasons: {detail.metadata?.seasons ?? '—'}</div>
          {badges && badges.length>0 && (
            <div className="mt-2">
              <div className="font-medium text-gray-900">Similar-because</div>
              <div className="mt-1 flex flex-wrap gap-2">
                {badges.slice(0,4).map((b,i)=> (
                  <span key={i} className="text-xs px-2 py-1 rounded bg-white border">{b}</span>
                ))}
              </div>
            </div>
          )}
          {(detail.metadata?.imdb_rating || detail.metadata?.rt_score || detail.metadata?.mc_score) && (
            <div className="mt-2">
              <div className="font-medium text-gray-900">External</div>
              <div className="mt-1 flex flex-wrap gap-2">
                {detail.metadata?.imdb_rating && detail.metadata.imdb_rating >= 8.5 && (
                  <span className="text-xs px-2 py-1 rounded bg-yellow-100 border">IMDb {detail.metadata.imdb_rating}</span>
                )}
                {detail.metadata?.rt_score && detail.metadata.rt_score >= 90 && (
                  <span className="text-xs px-2 py-1 rounded bg-red-100 border">RT {detail.metadata.rt_score}%</span>
                )}
                {detail.metadata?.mc_score && detail.metadata.mc_score >= 85 && (
                  <span className="text-xs px-2 py-1 rounded bg-green-100 border">MC {detail.metadata.mc_score}</span>
                )}
              </div>
            </div>
          )}
          <div className="mt-2">
            <div className="font-medium text-gray-900">Availability (AU)</div>
            <ul className="list-disc pl-5">
              {detail.availability.map((a, i) => (
                <li key={i}>{a.platform} — {a.offer_type}{a.quality ? ` · ${a.quality}` : ''}{a.leaving_at ? ` · leaving ${new Date(a.leaving_at).toLocaleDateString()}` : ''}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
