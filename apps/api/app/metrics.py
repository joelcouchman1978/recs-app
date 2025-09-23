from prometheus_client import Counter, Histogram, Gauge, CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response
from fastapi import APIRouter


REQUEST_LATENCY_MS = Histogram(
    "recs_request_latency_ms",
    "Latency of /recommendations in milliseconds",
    buckets=(5, 10, 25, 50, 100, 200, 400, 800, 1600, 3200),
)
CACHE_HITS = Counter("recs_cache_hits_total", "Recommendation cache hits")
CACHE_MISSES = Counter("recs_cache_misses_total", "Recommendation cache misses")
JOB_SUCCESS = Counter("jobs_success_total", "Successful background jobs", ["job"])
JOB_FAILURE = Counter("jobs_failure_total", "Failed background jobs", ["job"])
ADAPTER_ERRORS = Counter("adapter_errors_total", "Adapter error count", ["adapter"])

# Per-slate distribution of stale items ratio (0..1) with coarse buckets
RECS_STALE_RATIO = Histogram(
    "recs_stale_ratio",
    "Per-slate ratio of stale items in recommendations (0..1)",
    buckets=(0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0),
    labelnames=["intent"],
)

# Running totals so ratio = stale/total can be computed too
RECS_ITEMS_TOTAL = Counter(
    "recs_items_total",
    "Total recommendation items returned",
    ["intent"],
)
RECS_ITEMS_STALE_TOTAL = Counter(
    "recs_items_stale_total",
    "Total stale recommendation items returned",
    ["intent"],
)

# Build info gauge (set once at startup)
RECS_BUILD_INFO = Gauge(
    "recs_build_info",
    "Build info tagged with version, sha, env",
    labelnames=["version", "sha", "env"],
)

# Total API errors (incremented on 5xx)
RECS_REQUEST_ERRORS = Counter(
    "recs_request_errors_total",
    "Total API errors",
    ["route"],
)


router = APIRouter()


@router.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
