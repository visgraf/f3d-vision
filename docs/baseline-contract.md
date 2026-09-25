# Baseline contract — Classroom-Oracle-1 full

This is the acceptance contract every later change to this repository is measured
against. It was established in Consolidation 1 (staging commit `44bf786`, report
`a980e59`) and re-run from this repository in Consolidation 2. The imported
baseline is tagged `baseline-classroom-oracle1-2026-09-25` (→ `a980e59`). The
legacy source is `legacy-classroom-oracle3b-2026-09-25` (→ `48a3139`) in
`visgraf/fov-3d-vision`.

## Configuration

| | |
|---|---|
| experiment | Classroom-Oracle-1, spec `Classroom-Oracle-1-v1`, public digest `de19e51eb72aefec58675408bcc86d8d58c220a35aa6046b0a6fbf7dabe11b88` |
| scene | `scenes/classroom/classroom_eye.blend`, sha256 `dca66a3257b909aef00b0331652c55f62a93a8dff0665d070fba7efa436953cc`, plus the linked payload in `scenes/classroom/ASSET_MANIFEST.json` |
| domain | yaw −25..25°, pitch −20..20° (the original FSG6f domain, not Oracle-2's widened one) |
| profile / device / spp | `full` / `OPTIX` / 256 (the runner's defaults) |
| command | `scripts/run_golden.sh OUT_DIR` (runner, then evaluator) |
| environment | `scripts/verify_baseline.sh` must pass; `tools/check_runtime_environment.py` defines the required runtime |

## Behavioral acceptance: exact

A run reproduces the baseline only if all of the following hold, compared by content
against the accepted record (not by archive bytes):

- **Targets:** 25 target instances, in the same order (107 … 234), each with the same seed gaze (`bootstrap/seeds.json`: instances, domain, head pose).
- **Dense reference:** `bootstrap/evaluation_only/reachable_samples.npz` is array-identical.
- **Per look (104):** same gaze, action source, target points, oracle-valid points, map size before/after, new surfels, matcher and fusion metadata, and FSG6f and Cyclopean decisions.
- **Per object (25):** same fixation count, termination, final map surfels and incidental instance IDs.
- **Totals:**
  - 104 fixations;
  - action sources 25 `oracle_seed`, 53 `fsg6f`, 26 `cyclopean_epistemic`;
  - terminations 25 `attention_complete`, 0 `watchdog_24`, 0 anything else.
- **Truth isolation:** `dense_evaluation_truth_opened_during_control: false`; `foreground_background_decomposition: false`; `control_complete: true`.
- **Controller-relevant arrays exactly equal:**
  - every per-look map snapshot's `xyz_h`, `instance_id`, `support_count`, `provenance_mask`;
  - every oracle patch;
  - every final map;
  - the Object Index and Position arrays of every `oracle_observation.npz`.
- **Evaluation:**
  - 29,288 reachable samples;
  - 25,618 covered;
  - coverage `0.8746927069106801` at full stored precision;
  - 4 zero-new-surfel looks;
  - the per-object evaluation table equal at stored precision.

Any mismatch in the list above is a failure of the baseline. It is not fixed by
retuning the controller or by adding a tolerance.

## Not required bit-exact: RGB

The Cycles Combined (RGB) pass rendered with OptiX differs from run to run, with the same
seeds and the same spp. The legacy repository's own two smoke runs already differed.
Measured over the three full runs (legacy, Consolidation 1, Consolidation 2), pairwise:

| pair | observation RGB max abs diff | median per-image max | pixels not bit-identical | map RGB max abs diff |
|---|---:|---:|---:|---:|
| legacy vs C1 | 5.3e-3 | 7.4e-5 | 67.3% | 1.4e-4 |
| legacy vs C2 | 6.1e-3 | 8.0e-5 | 67.3% | 4.2e-4 |
| C1 vs C2 | 6.1e-3 | 8.6e-5 | 67.4% | 4.2e-4 |

RGB feeds only the stored surfel colour and the benchmark PNGs. The controller reads
Position and Object Index only; in all three pairs, all 416 of those observation arrays
are bit-exact. RGB is reported as a maximum absolute difference and is never part of
acceptance. A future run whose RGB differs by the same order is consistent with the
baseline. Differences in any exact item above are not.

## Structural acceptance

`scripts/verify_baseline.sh` must pass. It checks:

- all tracked Python compiles;
- `check_classroom_oracle1` 12/12, the tangent-frame check, and the module self-tests;
- the Classroom asset hashes;
- the required runtime;
- every file tracked at the baseline tag is byte-identical;
- `git diff --check` is clean.

## What changes the contract

Only a deliberate, recorded decision. A refactor that claims to preserve behavior has to
reproduce every exact item above.
