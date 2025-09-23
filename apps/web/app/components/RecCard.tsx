import React from 'react'
import type { RecommendationItem } from '../../../packages/shared/src/api-types'

export type Rec = RecommendationItem

import Link from 'next/link'

export function RecCard({ rec, onRate, More, onMoreLike, onWatchlistAdd, onWatchlistRemove, inWatchlist, moreLink }: { rec: Rec; onRate?: (primary: 0|1|2, tags?: string[], note?: string)=>void; More?: React.ReactNode; onMoreLike?: ()=>void; onWatchlistAdd?: ()=>void; onWatchlistRemove?: ()=>void; inWatchlist?: boolean; moreLink?: string }) {
  const [openNote, setOpenNote] = React.useState(false)
  const [note, setNote] = React.useState('')
  const [tags, setTags] = React.useState<string[]>([])
  const [showBadgesMobile, setShowBadgesMobile] = React.useState(false)
  const tagsPool = ['clever dialogue','strong female lead','humane worldview','cozy','optimistic','short episodes']
  return (
    <div className="rounded border bg-white p-4 shadow-sm" data-test="rec-card">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h2 className="font-semibold" data-test="rec-card-title">{rec.title}{rec.year ? ` (${rec.year})` : ''}</h2>
          {inWatchlist && (
            <span className="text-[10px] px-2 py-0.5 rounded bg-amber-100 border border-amber-200 text-amber-900">In watchlist</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button className="sm:hidden text-[10px] px-2 py-0.5 rounded border" onClick={()=>setShowBadgesMobile(v=>!v)}>{showBadgesMobile ? 'Hide badges' : 'Show badges'}</button>
          <div className={`${showBadgesMobile ? 'flex' : 'hidden'} sm:flex flex-wrap items-center gap-2`}>
          <span className="text-[10px] px-2 py-0.5 rounded border bg-gray-100" title="Derived from novelty n; <=0.6 is Comfort, >0.6 is Discovery">
            {rec.prediction.n <= 0.6 ? 'Comfort' : 'Discovery'}
          </span>
          {rec.au_rating && (
            <span className="text-[10px] px-2 py-0.5 rounded border bg-blue-50 border-blue-200 text-blue-900">AU {rec.au_rating}</span>
          )}
          <span className="text-xs px-2 py-1 rounded bg-gray-100" title={`Predicted ${rec.prediction.label}. c=${rec.prediction.c.toFixed(2)} (confidence 0–1), n=${rec.prediction.n.toFixed(2)} (novelty 0–1; lower=comfort)`}>
            {rec.prediction.label}
            <span className="hidden sm:inline"> · c={rec.prediction.c.toFixed(2)} n={rec.prediction.n.toFixed(2)}</span>
          </span>
          </div>
        </div>
      </div>
        <div className="text-sm mt-2">
          <div className="text-gray-800" data-test="rec-rationale"><span className="font-medium">Why this fits you:</span> {rec.rationale}</div>
          {rec.warnings.length > 0 && <div data-testid="warnings" className="text-red-700 mt-1">Heads-up: {rec.warnings.join(', ')}</div>}
          {rec.flags.length > 0 && <div data-testid="flags" className="text-green-700 mt-1">Positive: {rec.flags.join(', ')}</div>}
          <div className="text-gray-600 mt-2">Where: {rec.where_to_watch.map(w => `${w.platform} (${w.offer_type})`).join(', ')}</div>
          {rec.availability && (
            <div className="mt-1 text-xs flex gap-2 items-center" data-test="rec-availability">
              {rec.availability.provider && <span>{rec.availability.provider}</span>}
              {rec.availability.as_of && (
                <span title="Offer freshness">as of {new Date(rec.availability.as_of).toLocaleDateString()}</span>
              )}
              {rec.availability.stale && (
                <span className="rounded px-1 py-0.5 bg-yellow-100 text-yellow-800" title="Offer data may be stale">stale</span>
              )}
              {rec.availability.season_consistent && (
                <span className="rounded px-1 py-0.5 bg-emerald-100 text-emerald-800 border border-emerald-200" title="Offer matches your current season when available." data-test="chip-season-match">Season match</span>
              )}
              {rec.availability.season_consistent === false && (
                <span className="rounded px-1 py-0.5 bg-gray-100 text-gray-800" title="Season may differ from recommendation">season?</span>
              )}
            </div>
          )}
          {(rec.creators || rec.genres) && (
            <div className="mt-2 flex flex-wrap gap-2">
              {(rec.creators || []).slice(0,2).map((c,i)=>(
                <span key={`cr-${i}`} className="text-xs px-2 py-1 rounded bg-gray-100 border">{c}</span>
              ))}
            {(rec.genres || []).slice(0,3).map((g,i)=>(
              <span key={`gn-${i}`} className="text-xs px-2 py-1 rounded bg-gray-100 border">{g}</span>
            ))}
          </div>
        )}
        {rec.similar_because && rec.similar_because.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {rec.similar_because.slice(0,3).map((b, i) => (
              <span key={i} className="text-xs px-2 py-1 rounded bg-gray-100 border">{b}</span>
            ))}
          </div>
        )}
        {Array.isArray((rec as any).fit_by_profile) && (rec as any).fit_by_profile.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {(rec as any).fit_by_profile.slice(0,3).map((fp: any, i: number) => (
              <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-purple-50 border border-purple-200 text-purple-900" title={`Fit score for ${fp.name}`}>{fp.name}: {(Number(fp.score)||0).toFixed(2)}</span>
            ))}
          </div>
        )}
      </div>
      {(onRate || onMoreLike || onWatchlistAdd || onWatchlistRemove) && (
        <div className="mt-3 flex gap-2 text-xs">
          {onRate && (
            <>
              <button onClick={()=>onRate(2, tags, note)} className="px-2 py-1 rounded border">Rate: VERY GOOD</button>
              <button onClick={()=>onRate(1, tags, note)} className="px-2 py-1 rounded border">Rate: ACCEPTABLE</button>
              <button onClick={()=>onRate(0, tags, note)} className="px-2 py-1 rounded border">Rate: BAD</button>
              <button onClick={()=>setOpenNote(v=>!v)} className="px-2 py-1 rounded border">{openNote ? 'Hide' : 'Add note/tags'}</button>
            </>
          )}
          {onMoreLike && (
            <>
              <button onClick={onMoreLike} className="px-2 py-1 rounded border">More like this</button>
              {moreLink && (
                <Link href={moreLink} className="px-2 py-1 rounded border">Open page ↗</Link>
              )}
            </>
          )}
          {onWatchlistAdd && (
            <button onClick={onWatchlistAdd} className="px-2 py-1 rounded border">Add to watchlist</button>
          )}
          {onWatchlistRemove && (
            <button onClick={onWatchlistRemove} className="px-2 py-1 rounded border">Remove</button>
          )}
        </div>
      )}
      {openNote && (
        <div className="mt-3 border rounded p-2 bg-gray-50">
          <div className="text-xs mb-2">Nuance tags</div>
          <div className="flex flex-wrap gap-2 mb-2">
            {tagsPool.map(t => (
              <button key={t} onClick={()=> setTags(prev => prev.includes(t) ? prev.filter(x=>x!==t) : [...prev, t])} className={`text-xs px-2 py-1 rounded border ${tags.includes(t)?'bg-black text-white':'bg-white'}`}>{t}</button>
            ))}
          </div>
          <textarea className="w-full border rounded p-2 text-sm" placeholder="Add a short note (spoiler-safe)" value={note} onChange={e=>setNote(e.target.value)} />
        </div>
      )}
      {More}
    </div>
  )
}
