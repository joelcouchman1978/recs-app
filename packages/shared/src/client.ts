import type {
  MagicLinkRequest,
  MagicLinkResponse,
  RecommendationItem,
  ShowSummary,
  ShowDetail,
  ProfileCreate,
} from './api-types'

export type Config = { baseUrl: string }

export class ApiClient {
  constructor(private cfg: Config) {}

  private url(p: string) { return `${this.cfg.baseUrl}${p}` }

  async authMagic(body: MagicLinkRequest): Promise<MagicLinkResponse> {
    const r = await fetch(this.url('/auth/magic'), { method:'POST', headers:{ 'Content-Type':'application/json' }, body: JSON.stringify(body) })
    if (!r.ok) throw new Error('auth/magic failed')
    return r.json()
  }

  async authLogin(body: MagicLinkRequest): Promise<MagicLinkResponse> {
    const r = await fetch(this.url('/auth/login'), { method:'POST', headers:{ 'Content-Type':'application/json' }, body: JSON.stringify(body) })
    if (!r.ok) throw new Error('auth/login failed')
    return r.json()
  }

  async getHealth(): Promise<import('./api-types').HealthOut> {
    const r = await fetch(this.url('/healthz'))
    if (!r.ok) throw new Error('health failed')
    return r.json()
  }

  async getShows(limit = 60): Promise<ShowSummary[]> {
    const r = await fetch(this.url(`/shows?limit=${limit}`))
    if (!r.ok) throw new Error('get shows failed')
    return r.json()
  }

  async getShow(id: string): Promise<ShowDetail> {
    const r = await fetch(this.url(`/shows/${id}`))
    if (!r.ok) throw new Error('get show failed')
    return r.json()
  }

  async getProfiles(token: string): Promise<import('./api-types').ProfileOut[]> {
    const r = await fetch(this.url('/me/profiles'), { headers: { Authorization: `Bearer ${token}` } })
    if (!r.ok) throw new Error('get profiles failed')
    return r.json()
  }

  async getRecommendations(params: { for_: 'ross'|'wife'|'son'|'family', intent?: string, like_id?: string }, token: string, opts?: { seed?: number }): Promise<RecommendationItem[]> {
    const q = new URLSearchParams({ 'for': params.for_, intent: params.intent ?? 'default' })
    if (params.like_id) q.set('like_id', params.like_id)
    if (opts && typeof opts.seed === 'number') q.set('seed', String(opts.seed))
    const r = await fetch(this.url(`/recommendations?${q.toString()}`), { headers: { Authorization: `Bearer ${token}` } })
    if (!r.ok) throw new Error('get recommendations failed')
    return r.json()
  }

  async getDebugRecommendations(params: { for_: 'ross'|'wife'|'son'|'family', intent?: string }, token: string): Promise<Array<{ id: string, title: string, scores: number[] }>> {
    const q = new URLSearchParams({ 'for': params.for_, intent: params.intent ?? 'default' })
    const r = await fetch(this.url(`/debug/recommendations?${q.toString()}`), { headers: { Authorization: `Bearer ${token}` } })
    if (!r.ok) throw new Error('debug recs failed')
    return r.json()
  }

  async postProfiles(profiles: ProfileCreate[], token: string): Promise<unknown> {
    const r = await fetch(this.url('/profiles'), { method:'POST', headers:{ 'Content-Type':'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify(profiles) })
    if (!r.ok) throw new Error('post profiles failed')
    return r.json()
  }

  async postRating(args: { profile_id: number, show_id: string, primary: 0|1|2, nuance_tags?: string[], note?: string }, token: string): Promise<void> {
    const r = await fetch(this.url('/ratings'), { method:'POST', headers:{ 'Content-Type':'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify(args) })
    if (!r.ok) throw new Error('post rating failed')
  }

  async postOnboarding(payload: {
    profile_id: number;
    loves: string[];
    dislikes: string[];
    creators_like: string[];
    creators_dislike: string[];
    mood: { tone:number; pacing:number; complexity:number; humor:number; optimism:number };
    constraints: { ep_length_max?: number|null; seasons_max?: number|null; avoid_dnf?: boolean; avoid_cliffhangers?: boolean };
    boundaries: Record<string, boolean>;
  }, token: string): Promise<void> {
    const r = await fetch(this.url('/onboarding'), { method:'POST', headers:{ 'Content-Type':'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) })
    if (!r.ok) throw new Error('post onboarding failed')
  }

  async postProfileBoundaries(update: { name: 'Ross'|'Wife'|'Son'|string; age_limit?: number|null; boundaries: Record<string, boolean> }, token: string): Promise<unknown> {
    const r = await fetch(this.url('/profiles'), { method:'POST', headers:{ 'Content-Type':'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify([update]) })
    if (!r.ok) throw new Error('post profiles failed')
    return r.json()
  }

  async postWatchlistAdd(args: import('./api-types').WatchlistArgs, token: string): Promise<void> {
    const r = await fetch(this.url('/watchlist'), { method:'POST', headers:{ 'Content-Type':'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify(args) })
    if (!r.ok) throw new Error('post watchlist failed')
  }

  async deleteWatchlist(args: import('./api-types').WatchlistArgs, token: string): Promise<void> {
    const q = new URLSearchParams({ profile_id: String(args.profile_id), show_id: args.show_id })
    const r = await fetch(this.url(`/watchlist?${q.toString()}`), { method:'DELETE', headers:{ Authorization: `Bearer ${token}` } })
    if (!r.ok) throw new Error('delete watchlist failed')
  }

  async getWatchlist(profile_id: number, token: string): Promise<import('./api-types').WatchlistOut> {
    const q = new URLSearchParams({ profile_id: String(profile_id) })
    const r = await fetch(this.url(`/watchlist?${q.toString()}`), { headers:{ Authorization: `Bearer ${token}` } })
    if (!r.ok) throw new Error('get watchlist failed')
    return r.json()
  }

  // Admin endpoints (require admin email configured on server)
  async getAdminStatus(token: string): Promise<any> {
    const r = await fetch(this.url('/admin/status'), { headers:{ Authorization: `Bearer ${token}` } })
    if (!r.ok) throw new Error('admin status failed')
    return r.json()
  }
  async getAdminQueue(token: string): Promise<any> {
    const r = await fetch(this.url('/admin/queue'), { headers:{ Authorization: `Bearer ${token}` } })
    if (!r.ok) throw new Error('admin queue failed')
    return r.json()
  }
  async postAdminSync(source: 'justwatch'|'serializd', token: string, opts?: { dry_run?: boolean }): Promise<any> {
    const r = await fetch(this.url('/admin/sync'), { method:'POST', headers:{ 'Content-Type':'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ source, dry_run: opts?.dry_run ?? false }) })
    if (!r.ok) throw new Error('admin sync failed')
    return r.json()
  }
  async postRebuildEmbeddings(token: string): Promise<any> {
    const r = await fetch(this.url('/admin/embeddings/rebuild'), { method:'POST', headers:{ Authorization: `Bearer ${token}` } })
    if (!r.ok) throw new Error('embeddings rebuild failed')
    return r.json()
  }
}
