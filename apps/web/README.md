## Deterministic slates with `?seed=`

The web app forwards `?seed=<number>` from the URL to the API so slates are reproducible for debugging and tests.

- Example: `http://localhost:3000/?seed=777`
- See the root guide: [Deterministic recommendations with `?seed=`](../../README.md#-deterministic-recommendations-with-seed-debugging) for usage, caveats, and troubleshooting.

## Family Mix meta (`explain=true`)
For debugging Family Mix decisions (strong pick vs warning), call the API with `explain=true`.
See the root guide: [Family Mix meta with `explain=true`](../../README.md#-family-mix-meta-with-explaintrue-optional-debug).
