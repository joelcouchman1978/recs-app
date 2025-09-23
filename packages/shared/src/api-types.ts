// Generated-lite types approximating the OpenAPI schema (handwritten for bootstrap)
export interface MagicLinkRequest { email: string }
export interface MagicLinkResponse { token: string }

export interface ProfileCreate { name: 'Ross'|'Wife'|'Son'|string; age_limit?: number|null; boundaries?: Record<string, boolean> }
export interface ProfileOut { id: number; name: string; age_limit?: number|null; boundaries: Record<string, boolean> }

export interface WhereToWatch { platform: string; offer_type: string }
export interface Prediction { label: 'BAD'|'ACCEPTABLE'|'VERY GOOD'; c: number; n: number }
export interface RecommendationItem {
  id: string;
  title: string;
  year?: number|null;
  where_to_watch: WhereToWatch[];
  rationale: string;
  warnings: string[];
  flags: string[];
  prediction: Prediction;
  similar_because?: string[];
  genres?: string[];
  creators?: string[];
  au_rating?: string;
  age_rating?: number;
  fit_by_profile?: Array<{ name: string; score: number }>;
  availability?: { provider?: string|null; type?: string|null; as_of?: string|null; stale?: boolean; season_consistent?: boolean };
  family_strong?: boolean;
}

export interface ShowSummary { id: string; title: string; year_start?: number|null; metadata?: any; warnings?: string[]; flags?: string[] }
export interface ShowDetail extends ShowSummary { availability: Array<{ platform: string; offer_type: string; quality?: string|null; leaving_at?: string|null }> }

export interface WatchlistArgs { profile_id: number; show_id: string }
export interface WatchlistOut { show_ids: string[] }

export interface HealthOut { ok: boolean; debug?: boolean; family_coverage_min_fit?: number }
