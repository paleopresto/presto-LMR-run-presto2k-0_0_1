# PReSto LMR run on PReSto2k 0_0_1

This repository runs the PReSto LMR reconstruction on the [PReSto2k 0_0_1](https://lipdverse.org/PReSto2k/0_0_1/) compilation: 1036 records.

- Membership comes only from the published compilation, read from the
  LiPDverse whole-database export
  [2026-10-15b](https://lipdverse.org/dev/export/database-2026-10-15b/)
  (`compilations` table) by presto-recipes `pools/compilation_pool.R`.
- `query_params.json` (`mode: bundle`) pins the bundle by URL and sha256:
  presto-recipes release
  [pools-2026-10-15b-r2](https://github.com/paleopresto/presto-recipes/releases/tag/pools-2026-10-15b-r2).
  Its files are the compilation's LiPD files, checked against the export's
  md5 values and trimmed to the member records.
- The code and algorithm config are those of
  [presto-LMR-run-2026-10-08b](https://github.com/paleopresto/presto-LMR-run-2026-10-08b),
  unchanged, so this run differs from that one only in where its data come
  from.

- r2 (this run) reads age axes held in years AD as calendar years; in r1
  five records (Buentgen 2011, Hessl 2018, Stahle 2009, Yang 2014, Lapointe 2023)
  were assimilated reversed in time. See the release notes.

Committing `query_params.json` triggers the reconstruction workflow.
