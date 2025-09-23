# Offline / Sandbox Development

Some environments (CI sandboxes, flights without Wi-Fi) restrict installing system packages or downloading dependencies. This guide documents how to prime caches so that the recommender API and web app can still run locally.

## Python API (FastAPI)

On an online machine:

```bash
pip download -r apps/api/requirements.txt -d vendor/wheels
```

Copy the resulting `vendor/wheels` directory into this repository. Then start the API:

```bash
make api-local
```

`scripts/run_api_local.sh` creates a virtualenv under `.venv_api`, installs packages from `vendor/wheels` when available, and runs Uvicorn against SQLite + in-process cache.

## Node / pnpm (Web)

On an online machine:

```bash
cd apps/web
pnpm fetch
```

Archive the generated store (usually `.pnpm-store`) and extract it here into `vendor/pnpm-store`. Once copied, you can install dependencies offline:

```bash
cd apps/web
PNPM_HOME="$(pwd)/../../vendor/pnpm-store"
pnpm install --offline
```

If pnpm is unavailable, you can still run the API-only flows (`make api-local`, `make preflight-local`, API pytest suites) while offline.

## Helpful targets

- `make api-local` – runs FastAPI using SQLite + in-proc cache, no Docker required.
- `make preflight-local` – executes the readiness metrics/determinism checks against the local API.
- `make sandbox-smoke` – convenience task that starts the API and runs preflight (requires the `vendor/wheels` cache when offline).

## Troubleshooting

- **`pip install` fails offline** – ensure the wheel cache is populated as above; the script prints a hint when installation fails.
- **`pnpm install --offline` complains about missing artifacts** – double-check that the `.pnpm-store` contents match the lockfile version. Re-run `pnpm fetch` on a machine with the same lockfile, then re-copy.
- **`make preflight-local` says the API is unreachable** – start the API first (`make api-local`) or rely on `make sandbox-smoke` which launches it for you.
