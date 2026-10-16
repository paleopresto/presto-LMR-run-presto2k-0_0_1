# PReSto LMR run, 2026-10-08b pool

This repository runs the PReSto LMR reconstruction on a pinned LiPDverse data
pool. Everything that defines the run is committed here:

- `query_params.json` (`mode: bundle`): the pool bundle's URL and sha256,
  and its TSids. Pool, criteria and deduplication:
  [paleopresto/presto-recipes](https://github.com/paleopresto/presto-recipes/tree/pools/pools),
  release [pools-2026-10-08b-r8](https://github.com/paleopresto/presto-recipes/releases/tag/pools-2026-10-08b-r8) (r4 with missing-value codes set to NaN).
- The algorithm's config, from presto-recipes `runs/presto-LMR/2026-10-08b/`
  (or the template default where that directory has none).
- The workflow and container code, from the template's `pool-bundles` branch
  until that is merged upstream.

Committing `query_params.json` triggers the reconstruction workflow.
