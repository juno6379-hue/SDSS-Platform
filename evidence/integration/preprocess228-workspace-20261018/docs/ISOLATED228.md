# Isolated228 review handoff

TESTED_SYNTHETIC; not installed in shared products. Root approval is still required.

- `input-source-manifest.json`: copied code/config/test bytes and initial SHA.
- `baseline-code/`: exact unchanged main code matching input SHA for changed paths.
- `patch228.diff`, `patch228-manifest.json`: only9 modified existing product files +2 new files; no UI225/collector/operating data patch.
- `profile228-freeze-regression.log`: final88 PASS,74.061sec.
- `benchmark228-result.json`, `benchmark228-supervision.json`: single bounded synthetic child, no retry, no actual QA.
- `freeze228.json`: final immutable handoff pins.

CLI (isolated only): `python scripts/prepare_priority_candidate164.py ... --manifest-profile bounded128m-3000-v1`.
Python stage/materialize/QA/comparison functions accept the same explicit `manifest_profile=` keyword. DefaultNone preserves64MiB/v1; explicit128 requires matchingv2 receipts. API reader selection is query `manifest_profile=bounded128m-3000-v1` with the original pinned request body. Actual filesystem/SHA/quality gates remain distinct. Shared service does not implement these options yet.

Known incomplete consumers: sourceJSON64MiB in173/182 and225budget card. Individual raster/header64MiB limits must stay unchanged. Followup229 is separate.
