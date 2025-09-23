import os
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Dict, List


class Settings(BaseSettings):
    use_real_justwatch: bool = Field(default=False, alias="USE_REAL_JUSTWATCH")
    use_real_serializd: bool = Field(default=False, alias="USE_REAL_SERIALIZD")
    region: str = Field(default="AU", alias="REGION")

    serializd_user: str | None = Field(default=None, alias="SERIALIZD_USER")
    serializd_token: str | None = Field(default=None, alias="SERIALIZD_TOKEN")

    family_coverage_min_fit: float = Field(default=0.6, alias="FAMILY_COVERAGE_MIN_FIT")
    # Environment and CORS
    environment: str = Field("dev", alias="ENVIRONMENT")  # dev|prod
    allow_origins: str = Field("http://localhost:3000", alias="ALLOW_ORIGINS")

    use_sqlite: bool = Field(default=True, alias="USE_SQLITE")
    disable_redis: bool = Field(default=True, alias="DISABLE_REDIS")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")

    # --- Feedback loop weights (phase 2) ---
    # Ratings priors
    rating_weight_very_good: float = Field(0.25, alias="RATING_WEIGHT_VERY_GOOD")
    rating_weight_acceptable: float = Field(0.05, alias="RATING_WEIGHT_ACCEPTABLE")
    rating_penalty_bad: float = Field(0.40, alias="RATING_PENALTY_BAD")

    # Tag nudges
    tag_like_bonus: float = Field(0.08, alias="TAG_LIKE_BONUS")
    tag_dislike_penalty: float = Field(0.12, alias="TAG_DISLIKE_PENALTY")

    # Notes keyword weights
    note_keyword_weights: Dict[str, float] = {
        "dnf": -0.25,
        "too dark": -0.18,
        "too slow": -0.12,
        "boring": -0.20,
        "cozy": +0.10,
        "light": +0.08,
    }

    # History adjacency and rewatch
    history_adj_boost: float = Field(0.06, alias="HISTORY_ADJ_BOOST")
    history_rewatch_penalty: float = Field(0.10, alias="HISTORY_REWATCH_PENALTY")

    # --- Rationale & spoiler lint (phase 5) ---
    rationale_max_chars: int = Field(180, alias="RATIONALE_MAX_CHARS")
    # Keep concise; pilot premise only; no season/episode spoilers.
    spoiler_denylist: List[str] = [
        # plot outcomes
        r"\b(dies|death|kills?|murder(er)?|killer|betray(s|ed)|traitor|villain|twist|revealed?)\b",
        r"\b(wedding|pregnan(t|cy)|break[ -]?up|divorce|affair)\b",
        # time/season reveals
        r"\b(season\s*\d+|episode\s*\d+|finale|post[- ]credits?)\b",
        # resurrection/time jump
        r"\b(return(s|ed)?\s+from\s+the\s+dead|time\s+jump)\b",
        # identity/whodunnit
        r"\b(whodunnit|who\s+killed|the\s+killer\s+is)\b",
    ]

    # --- Data freshness & season handling (phase 6) ---
    offers_stale_days: int = Field(7, alias="OFFERS_STALE_DAYS")
    season_strict: bool = Field(True, alias="SEASON_STRICT")

    # --- Family Mix strong-pick guardrail (phase 7) ---
    family_strong_min_fit: float = Field(0.78, alias="FAMILY_STRONG_MIN_FIT")
    family_strong_rule: str = Field("min", alias="FAMILY_STRONG_RULE")  # "min" or "avg"
    family_strong_lock_count: int = Field(1, alias="FAMILY_STRONG_LOCK_COUNT")

    # --- RC hardening ---
    admin_rps: int = Field(10, alias="ADMIN_RPS")
    admin_burst: int = Field(20, alias="ADMIN_BURST")
    recs_target_p95_ms: int = Field(250, alias="RECS_TARGET_P95_MS")

    # --- Build info ---
    app_version: str = Field("0.1.0", alias="APP_VERSION")
    git_sha: str | None = Field(None, alias="GIT_SHA")

    def resolved_database_url(self) -> str:
        if self.use_sqlite:
            return (self.database_url or "sqlite:///./.local/recs.db")
        if self.database_url:
            return self.database_url
        user = os.getenv("POSTGRES_USER", "dev")
        password = os.getenv("POSTGRES_PASSWORD", "dev")
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "recs")
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

    def resolved_redis_url(self) -> str | None:
        if self.disable_redis:
            return None
        return self.redis_url or os.getenv("REDIS_URL")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
