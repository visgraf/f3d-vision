# Consolidation 3 — conceptual API refactor report (2026-09-25)

The contract is `docs/consolidation-3-interface-refactor.md`, committed by the apply script
in `447347d`. This step was structural only: no controller, renderer, matcher, fusion,
threshold, domain, scene or evaluation change, and no new architecture behavior.

## Starting state (verified, not repaired)

| | |
|---|---|
| repo | `/home/lvelho/rd/fov-3d-vision-core`, branch `consolidation-3-interface-refactor`, no remote |
| parent | `447347d` "Add Consolidation 3 API refactor contract" on `760d216` |
| safety tag | `consolidation2-sealed-2026-09-25` (annotated) → `760d216` |
| safety bundle | `/home/lvelho/rd/fov-3d-vision-core-consolidation2.bundle`, sha256 `86068e35…`, `git bundle verify`: complete history, heads `main` and both tags at `760d216` |
| package files | the 4 committed files and the untracked `CONSOLIDATION3_CODE_PROMPT.md` are byte-identical to `~/Downloads/consolidation-3-interface-refactor.zip`; the prompt file was left untracked, as the apply script left it |

## Commits

| commit | content |
|---|---|
| `2449f90` Add durable golden behavior comparator | `tools/compare_golden.py`, `scripts/compare_golden.sh`, `tests/golden/classroom-oracle1-signature.json`, `tests/golden/classroom-oracle1-smoke-signature.json` |
| this commit, Add fov3d conceptual API facade | `fov3d/` (25 files), `docs/fov3d-api.md`, `docs/consolidation-3-report.md`, the repaired `tools/dev/check_fov3d_facade.py`, and an append to `docs/current-architecture-map.md` |

## Step 1 — durable comparator and signature

`tools/compare_golden.py` is the Consolidation-2 scratch comparator
(`/tmp/fov3d-consolidation2/compare.py`) promoted with the same acceptance semantics. It
has no scratch paths, and uses one extraction and one diff. Either side may be a run
directory or a signature file.

Subcommands:

- `compare REFERENCE CANDIDATE`
- `signature RUN --out FILE`
- `self-test`

Semantics:

- **Arrays** are compared as `dtype[shape]:sha256` over canonical bytes (NaN canonical,
  −0.0 → +0.0). This equals the old `np.array_equal(equal_nan=True)` with dtype and shape.
- **Large dicts** (matcher, fusion, FSG6f and Cyclopean decisions, calibration) are
  compared by canonical-JSON sha256, with a readable summary of their top-level scalars.
- **RGB** (`rgb`, `rgb_L`, `rgb_R`) keeps key, dtype and shape only. That matches the old
  code, which skipped RGB content only when shape and dtype agreed. In run-vs-run mode the
  RGB differences are measured and printed as informational.
- **Stricter than before in two ways:** evaluation is compared whenever the reference has
  one, and list lengths are checked explicitly (the old `zip` truncated).

Validation:

| comparison | mismatches | compared |
|---|---:|---|
| C1 full vs C2 full (run vs run) | **0** | 104 looks, 1,348 controller arrays, 337 RGB arrays excluded; RGB report equal to the Consolidation-2 figures (map 4.19e-4, observation 6.06e-3, 67.4%) |
| C2 full vs committed signature | **0** | same |
| legacy frozen full vs committed signature | **0** | same |
| C2 smoke / legacy smoke-2 vs smoke signature | **0** / **0** | 5 looks, 68 arrays, 17 RGB excluded |
| smoke run vs full signature | 226 | the signatures are not interchangeable |
| mutated signature copies against the C2 run: one gaze, one map hash, coverage last digit, one action source | 1 each | each located exactly |
| `compare_golden.py self-test` | PASS | −0.0 and NaN payload equal; a one-element change, dtype, shape and six record mutations detected |

Signatures:

- **Full** (`tests/golden/classroom-oracle1-signature.json`): 476,509 B (102,514 B gzipped).
- **Smoke:** 27,853 B.
- Both were generated from the accepted Consolidation-1 runs, so checking C2 against
  them is not a tautology.
- Generation is deterministic: a rerun is byte-identical.
- The smoke signature was not required by the prompt. It was added so the
  interactive-class gate is also durable without `previews/`.

## Step 2 — facade

`tools/dev/build_fov3d_facade.py` (no `--force`) generated:

- `fov3d/_compat.py`;
- 16 wrappers of 8 lines (14 with a CLI), each re-exporting exactly its layout target;
- 7 package `__init__.py` files and `fov3d/__init__.py`.

All 16 were reviewed against `docs/consolidation-3-layout.json`. They contain no
implementation code, and a rerun of the generator is idempotent.

Two package-plumbing facts surfaced, both diagnosed before any change:

1. **Five sealed modules cannot be imported alone.** `fsg_stereo`, `fsg6f_frontier`,
   `multiobject2c_policy`, `classroom_oracle1_matcher` and `classroom_oracle1_epistemic`
   import their siblings by bare name and rely on `tools/` being on `sys.path`, which
   every sealed entry point inserts first.
   **Fix:** `fov3d/__init__.py` does the same. The generator writes this file only when
   it is absent, so it never overwrites it. The same file refuses to import unless
   `tools` resolves to this repo; a negative with a foreign `tools` package gives
   `ImportError`.
2. **Two sealed modules import `bpy` at module level** (`bl_common`, `render_foveated`),
   so they load only inside Blender. Four host modules need `cv2`, which Blender lacks.
   So no single interpreter can import all 16. The package's `check_fov3d_facade.py`
   crashed on its first row (`ModuleNotFoundError: bpy`) and could not print
   `checked=16` anywhere.
   **Repair:** the per-row check was factored into `check_row()`, unchanged. A row whose
   sealed module needs `bpy`/`mathutils` runs that same function inside Blender
   (`--factory-startup`). If Blender is missing, the row fails; it is never skipped.
   The checker also imports `fov3d` first (plumbing), and additionally checks that the
   sealed module resolves inside `tools/`.

Facade checker results:

- `SUMMARY checked=16 failed=0` (14 host, 2 Blender).
- **Negatives:**
  - a wrong host mapping fails;
  - a wrong Blender mapping fails from inside Blender;
  - `--blender /nonexistent` fails both Blender rows (`failed=2`).

## Step 3 — package route

- **Host:** 14 of the 16 facade modules import alone in a fresh host process.
- **Blender:** `fov3d.rendering.blender` and `.foveated` import in Blender.
- **Both interpreters:** exr, warp, geometry, surface_map, frontier, frontier_config,
  object_policy, config, render and eval. Measured per module; the table is in
  `docs/fov3d-api.md`.
- **Entry points:** `python -m fov3d.experiments.classroom_oracle.run` and `….eval` call
  the sealed `main()` and nothing else. They work from the repo root, and from elsewhere
  with `PYTHONPATH`.
- **Legacy entry point** still works: `tools/classroom_oracle1_run.py --smoke` gives 0
  mismatches against the smoke signature.

## Step 4 — smoke through `fov3d`

`python -m fov3d.experiments.classroom_oracle.run --repo . --out previews/fov3d-classroom-oracle-1-smoke --profile small --device OPTIX --smoke`:

- `COMPLETE {"fixations": 5, "objects": 4, "smoke": true, "terminations": {"attention_complete": 2, "seed_uninitializable": 1, "smoke_budget": 1}}`
- gate `PASS_CONTROLLER_TRANSITION_EXERCISED`, primary instances [107, 108];
- genuine post-seed transition on 110 `beams`: `oracle_seed` (−22, 20) → `fsg6f` (−17, 15);
- **0 mismatches** against the sealed C2 smoke (run vs run) and against the smoke signature.

## Step 5 — full golden through `fov3d`

`python -m fov3d.experiments.classroom_oracle.run --repo . --out previews/fov3d-classroom-oracle-1-full --profile full --device OPTIX`,
then `python -m fov3d.experiments.classroom_oracle.eval --run …` (10 min 54 s in total):

```
[classroom-oracle1] COMPLETE {"fixations": 104, "objects": 25, "smoke": false, "terminations": {"attention_complete": 25}}
[classroom-oracle1-eval] COMPLETE {"coverage": 0.8746927069106801, "fixations": 104, "instances": 25, "terminations": {"attention_complete": 25}}
```

`scripts/compare_golden.sh previews/fov3d-classroom-oracle-1-full` gives **MISMATCHES 0**
(104 looks, 1,348 controller arrays; 337 RGB arrays excluded). Against the sealed C2 full
run it also gives **0**.

| headline | value |
|---|---|
| targets | 25 |
| fixations | 104 |
| action sources | 25 `oracle_seed` / 53 `fsg6f` / 26 `cyclopean_epistemic` |
| attention_complete / watchdog_24 | 25 / 0 |
| reachable / covered | 29,288 / 25,618 |
| coverage | 0.8746927069106801 |
| zero-new-surfel looks | 4 |
| truth opened during control / fg-bg decomposition | false / false |

RGB (C2 vs this run; informational):

- observation max |Δ| 7.7e-3;
- median per-image max 6.9e-5;
- 67.3% of pixels not bit-identical;
- map max |Δ| 4.2e-4.

This is the same order as every earlier pair.

## Step 6 — boundary documented

- **`docs/fov3d-api.md`** covers:
  - the stable API and the sealed engine;
  - the import rule for future work;
  - that moving code is optional;
  - the measured interpreter map;
  - the entry points and the plumbing;
  - the known properties: two module objects per sealed file (facade `tools.X` against the engine's bare `X`), the broad public surface (no `__all__`), and the interpreter split.
- **`docs/current-architecture-map.md`:** a section was appended. The first 9,393 bytes
  are the sealed text (sha256 `65a75a46…`), with 37 insertions and 0 deletions.

## Invariants

- **Sealed files:**
  - the 31 files at `baseline-classroom-oracle1-2026-09-25` are byte-identical;
  - of the 8 Consolidation-2 seal files, 7 are byte-identical and 1 (`current-architecture-map.md`) is append-only, as the contract asks.
- **`scripts/verify_baseline.sh`:** `SUMMARY passed=9 failed=0`. It is unchanged and was run after all changes.
- **Legacy** `/home/lvelho/rd/fov-3d-vision`: 598 tracked files identical (`948b2d26…`), HEAD `48a3139`, clean.
- **Staging** `/home/lvelho/rd/fov-3d-vision-core-stage`: tracked files, all 1,440 untracked files by path/size/mtime, and `.git` are identical; HEAD `a980e59`, clean.

## Still not self-contained

1. **The scene payload** (`scenes/classroom/`, 150 MB, gitignored). There is no local
   source zip, and `place_eye.py` regeneration has not been tested for byte-identity.
   Unchanged from Consolidation 2.
2. **The environment:** Blender 5.2.1, an OptiX GPU, system Python 3.12, and PyPI to
   rebuild `.venv`.
3. **No remote.** The history exists in this repo, in staging, and in the safety bundle
   on the same disk.

Resolved by this step: the behavioral comparator and the golden reference no longer live
outside git. `tests/golden/` replaces the 17 GB `previews/` tree for acceptance. The run
directories are still needed for RGB measurement and diagnosis.

## Not implemented

No spherical partition, dual graph, segmentation, object discovery, or any other new
architecture behavior. No sealed implementation was moved, copied or edited.

**CONSOLIDATION3_API_REFACTOR_COMPLETE**
