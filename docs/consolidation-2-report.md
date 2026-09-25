# Consolidation 2 — baseline seal report (2026-09-25)

The contract is `CONSOLIDATION2_BASELINE_SEAL.md`. It was read from
`~/Downloads/consolidation-2-baseline-seal.zip`, since the prompt's path
`~/Downloads/CONSOLIDATION2_BASELINE_SEAL.md` does not exist as a loose file. The zip's
`SHA256SUMS` verified: contract `a75f9f19…`, prompt `f89eb3d7…`, apply script `ea2214c4…`.

## Repositories

| | path | HEAD | remotes |
|---|---|---|---|
| legacy | `/home/lvelho/rd/fov-3d-vision` | `48a3139020e87bfaf1255df1585390f7e9094ec8` = tag `legacy-classroom-oracle3b-2026-09-25` | origin (GitHub), untouched |
| staging | `/home/lvelho/rd/fov-3d-vision-core-stage` | `a980e59dfc453c590190f842c47c4588bc99989d` | none |
| permanent | `/home/lvelho/rd/fov-3d-vision-core` | `a980e59` + the seal commit | **none** |

- **How the permanent repo was created.** It already existed when this step started. It had been made at 08:58:13 by the packaged `CONSOLIDATION2_APPLY.sh`, whose output ends "Next: paste the Code prompt". I verified it is exactly that script's result and did not recreate it:
  - reflog `clone: from …-core-stage`;
  - HEAD `a980e59`;
  - no remote, and no `objects/info/alternates` (an independent object store, cloned with `--no-hardlinks`);
  - clean, with no ignored files yet;
  - annotated tag `baseline-classroom-oracle1-2026-09-25` → `a980e59` (tagger Luiz Velho, "Reproduced minimal Classroom Oracle 1 baseline").
- **Untracked inputs added for the runs:**
  - `scenes/classroom/`, copied from staging; all 54 files are byte-identical to the legacy checkout (list digest `8d06a44d…`);
  - `.venv`, built from `/usr/bin/python3` (3.12.3) with the pinned requirements.

## Files added by the seal (8, all new; no existing file touched)

```
docs/baseline-contract.md
docs/current-architecture-map.md
docs/consolidation-2-report.md
scenes/classroom/ASSET_MANIFEST.json     (added with -f: scenes/classroom/ is gitignored and .gitignore is not edited)
scripts/run_golden.sh
scripts/verify_baseline.sh
tools/check_classroom_assets.py
tools/check_runtime_environment.py
```

## Asset manifest

Built from the actual tree. Blender 5.2.1 opened `classroom_eye.blend` and resolved
every library, every image with a filepath, and every node filepath. Each path was
resolved relative to **its owning library**, and `bpy.utils.blend_paths` was added.

| | count | bytes |
|---|---:|---:|
| files under `scenes/classroom/` | 54 | 156,901,416 |
| required (direct input 1, linked libraries 11, linked textures 36) | 48 | 112,010,409 |
| optional (generator source `classroom.blend` 1, unreferenced payload 5) | 6 | |
| `missing_legacy_reference` | **0** | |
| `nominal_unused` (`blendcache_classroom_eye/`) | 1 | |

- **Accepted `classroom_eye.blend` sha256**, read from the file:
  `dca66a3257b909aef00b0331652c55f62a93a8dff0665d070fba7efa436953cc`.
- **References:** 0 point outside `scenes/classroom/`.
- **Unreferenced payload:**
  - `ReadMe.txt`
  - `assets/__ENV/Garage/Garage.hdr`
  - `assets/officeSupplies/textures/eraser.jpg`
  - `textures/childDrawing/childDrawing_02.jpg`
  - `textures/glass.jpg`
- **`blendcache_classroom_eye/`** is the default point-cache path of `DustParticules`. That object is in scene `dustParticules`, not the rendered `_mainScene`. Its cache is baked into the `.blend` with `use_disk_cache=False`, the directory is absent, and nothing reads it.
- **Correction to the Consolidation 1 report.** Its "`//../../textures/*` is missing in the legacy repo too" was a resolution error. Those paths belong to linked libraries in `assets/<name>/` and resolve to `scenes/classroom/textures/_baseTextures/`, which exist. No legacy-linked texture is missing. The manifest records this correction.

## Runtime environment (`tools/check_runtime_environment.py`)

REQUIRED 11/11 pass:

- Python 3.12.3, not conda (`base_prefix=/usr`);
- numpy 2.2.6, opencv-python-headless 4.13.0.92 and pillow 12.3.0, all equal to their pins;
- 16 host modules resolve under the repo's `tools/`;
- the dev check is present;
- no legacy path on `sys.path`;
- Blender 5.2.1 LTS (`/usr/local/bin/blender` → `/opt/blender-5.2/blender`);
- 8 Blender-side modules resolve under the repo's `tools/`;
- Cycles OPTIX device "NVIDIA GeForce RTX 4090".

INFO:

- `.venv` prefix;
- `python3` on PATH is `/home/lvelho/miniconda/envs/world2018/bin/python3.10`;
- `PYTHONPATH` is empty;
- OpenEXR 3.4.15;
- Blender's Python is 3.13.13;
- CUDA device present;
- nvidia-smi reports RTX 4090, driver 595.91.07, 24,564 MiB;
- `ffmpeg` on PATH is conda's 4.2.2, and `/usr/bin/ffmpeg` also exists.

**Negatives (the checker can fail):**

- under the conda `python3`: 5 REQUIRED failures (Python 3.10, conda, numpy 2.0.1, no opencv, pillow 11.1.0), exit 1;
- with `--blender /nonexistent/blender`: 1 REQUIRED failure.

Both checkers are read-only:

- `sys.dont_write_bytecode`, no project module is executed (`find_spec` only), and Blender runs with `--factory-startup`;
- the asset checker's self-test runs in memory;
- a snapshot (path, size, mtime) of the whole repo tree, ignored files included, was identical before and after `verify_baseline.sh`, on both runs.

## Structural verification (`scripts/verify_baseline.sh`, run from `/`)

`[verify] SUMMARY passed=9 failed=0`:

- 22 tracked `.py` compile in memory;
- `check_classroom_oracle1` `passed=12 failed=0`;
- tangent frame `checked=92 failed=0`;
- module self-tests: `fsg_geometry`, `warp`, matcher, public (digest `de19e51e…`), `fsg3_surface_map`, `fsg6f_frontier`, epistemic and run all PASS;
- assets self-test PASS;
- assets `required_ok=48/48`;
- environment `11/11`;
- 31 files at the baseline tag byte-identical;
- `git diff --check` clean.

**Negative:** in a scratch clone with one byte appended to `tools/fsg6f_public.py`,
`baseline-files-unchanged` and `git-diff-check` FAIL and the script exits 1.

## Smoke (`scripts/run_golden.sh --smoke`, small profile)

`COMPLETE {"fixations": 5, "objects": 4, "smoke": true, "terminations": {"attention_complete": 2, "seed_uninitializable": 1, "smoke_budget": 1}}`

- Gate status: `PASS_CONTROLLER_TRANSITION_EXERCISED`, primary instances [107, 108].
- Against the Consolidation 1 smoke: **0 mismatches**. Seeds, dense samples, 5/5 looks, 5/5 map snapshots and 5/5 patches are equal, and all 20 observation instance/position arrays are exact.

## Full golden run (`scripts/run_golden.sh`, full / OPTIX / 256 spp, 10 min 45 s)

```
[classroom-oracle1] COMPLETE {"fixations": 104, "objects": 25, "smoke": false, "terminations": {"attention_complete": 25}}
[classroom-oracle1-eval] COMPLETE {"coverage": 0.8746927069106801, "fixations": 104, "instances": 25, "terminations": {"attention_complete": 25}}
```

Against the accepted Consolidation 1 record (staging `previews/classroom-oracle-1-full`):
**MISMATCHES 0.**

| item | result |
|---|---|
| target order / seed gazes / head pose / domain | identical, 25 targets 107…234 |
| dense `reachable_samples.npz` | array-identical |
| per-look gaze, action source, counts, matcher, fusion, FSG6f and Cyclopean decisions, calibration | identical, 104/104 |
| map snapshots (`xyz_h`, `instance_id`, `support_count`, `provenance_mask`) / patches / final maps | 104/104, 104/104, 25/25 equal |
| observation Object Index and Position arrays | 416/416 bit-exact |
| per-object fixations / termination / surfels / incidentals | identical, 25/25 |
| fixations | 104 |
| action sources | 25 `oracle_seed` / 53 `fsg6f` / 26 `cyclopean_epistemic` |
| terminations | 25 `attention_complete`, 0 `watchdog_24` |
| truth opened during control / fg-bg decomposition / control complete | false / false / true |
| reachable / covered / coverage | 29,288 / 25,618 / `0.8746927069106801` |
| zero-new looks / per-object evaluation table | 4 / equal at stored precision |

Comparing directly against the legacy frozen record (`legacy/previews/classroom-oracle-1-full`)
also gives **0 mismatches**.

## RGB nondeterminism (not part of acceptance)

| pair | observation RGB max abs diff | median per-image max | pixels not bit-identical | map RGB max abs diff (129 arrays) |
|---|---:|---:|---:|---:|
| C1 vs C2 (smoke) | 1.2e-4 | 6.4e-6 | 45.0% | 8.9e-8 |
| legacy vs C1 (full) | 5.3e-3 | 7.4e-5 | 67.3% | 1.4e-4 |
| legacy vs C2 (full) | 6.1e-3 | 8.0e-5 | 67.3% | 4.2e-4 |
| C1 vs C2 (full) | 6.1e-3 | 8.6e-5 | 67.4% | 4.2e-4 |

The map RGB difference in this run (4.2e-4) is larger than the single Consolidation 1
figure (1.4e-4), but of the same order as the other pairs. It is OptiX Combined-pass
noise with fixed seeds and spp. `docs/baseline-contract.md` records the range rather
than one number.

## Hash proof

| | before | after |
|---|---|---|
| legacy, 598 tracked files | `948b2d267a5b6e7f…` | identical; HEAD `48a3139`, clean |
| staging, 31 tracked files | `55a4b6fa2bbb94c0…` | identical; HEAD `a980e59`, clean |
| staging untracked (1,440 files; path/size/mtime) | `696161f4…` | identical |
| staging non-EXR contents (1,165 files) / `.git` | `47b23a93…` / `0c59a645…` | identical / identical |
| permanent, 31 pre-existing files vs `a980e59` blobs | `55a4b6fa2bbb94c0…` | identical |

## What keeps the repo from being self-contained

1. **The scene payload is outside git.** `scenes/classroom/` (54 files, 150 MB) exists only in the legacy, staging and permanent checkouts on this disk. The source `classroom.zip` is not kept on the workstation, so the provenance of 53 of the 54 files rests on `scenes/manifest.json` and cannot be re-verified offline. Rebuilding `classroom_eye.blend` with `tools/place_eye.py` has never been tested for byte-identity with the accepted digest. A backup of `scenes/classroom/` outside the checkout is the cheap protection.
2. **The behavioral comparator is not in the repo.** The comparison in this report was made by a scratch script (`/tmp/fov3d-consolidation2/compare.py`, extended from Consolidation 1's). The contract fixed the list of files to add, so it was not committed. `docs/baseline-contract.md` states the criteria, but a later refactor cannot run them from the repo alone.
3. **The reference record is outside git too.** The accepted run records live in `previews/`, which is gitignored: legacy, staging, and this repo's own `previews/` (measured: full run 17 GB, smoke 197 MB; staging's `previews/` is also 17 GB).
4. **Environment.** Blender 5.2.1 at `/usr/local/bin/blender`, an OptiX GPU, and a system Python 3.12 are required. The shell's `python3` is a conda 3.10. `scripts/run_golden.sh` falls back to `python3` when `.venv` is missing, which on this machine would fail; `verify_baseline.sh` reports this through the environment check. `.venv` needs PyPI to rebuild, since packages are not vendored.
5. **History.** There is no remote. The history exists only in this repo and in staging on the same disk.

**CONSOLIDATION2_BASELINE_SEALED**
