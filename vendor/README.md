# Offline mirrors

- Place Python wheels in `vendor/wheels` (generate with `pip download -r apps/api/requirements.txt -d vendor/wheels` on a connected machine).
- Place the pnpm store in `vendor/pnpm-store` (run `pnpm fetch` on a connected machine, archive the resulting store, and extract it here). After copying, run `pnpm install --offline` in `apps/web`.

Scripts such as `scripts/run_api_local.sh` will prefer these caches automatically when present.
