# Consolidation 1 — migration report (2026-09-25)

**CONSOLIDATION1_BASELINE_REPRODUCED**

## Freeze

- Legacy repo `visgraf/fov-3d-vision`, branch `classroom-oracle-3b`. HEAD was exactly
  `48a3139020e87bfaf1255df1585390f7e9094ec8`, with no later work.
- Annotated tag `legacy-classroom-oracle3b-2026-09-25` → `48a3139`, pushed to origin.
- The old tree did not change. The aggregate sha256 over the sha256 list of all 598 tracked
  files was `948b2d267a5b6e7f7a6158e924db08e77f1e726b52d31328ee23e82524fa832b` both
  before and after. `git status` stayed clean and HEAD did not move. The only
  filesystem side effect was in `tools/__pycache__/`, which is gitignored.

## Staging

- Path: `/home/lvelho/rd/fov-3d-vision-core-stage`, branch `main`, no remote.
- Commit `44bf786` "Import minimal Classroom Oracle baseline", plus this docs-only commit.
- 25 files byte-identical to the freeze blobs:
  - 16 runtime
  - 2 verification
  - 2 scene
  - 4 environment
  - 1 doc
- 5 new files: README, provenance, manifest (`.md` and `.json`), and `tools/consolidation1_demo.py`.
- 573 files excluded. See [migration-manifest.md](migration-manifest.md).

## Structural checks (staging, `.venv` Python 3.12.3)

- `py_compile` passes on all 19 migrated Python files.
- `check_classroom_oracle1.py`: `SUMMARY passed=12 failed=0`.
- `check_fsg_tangent_frame.py`: `checked=92 failed=0`.
- Module self-tests all PASS: `fsg_geometry`, `warp`, `classroom_oracle1_matcher`,
  `classroom_oracle1_public` (digest `de19e51e…`, identical to the frozen run manifest),
  `fsg3_surface_map`, `fsg6f_frontier`, `classroom_oracle1_epistemic`,
  `classroom_oracle1_run`.
- Import origins: on the host side, 13 local modules all load from staging. On the Blender
  side, 7 local modules all load from staging. No `sys.path` entry points at the old repo,
  `PYTHONPATH` is empty, and there are 0 symlinks.
- Constants: 45 upper-case module constants across 13 modules were compared against the
  frozen tree. All are equal except `HERE`, which is each module's own directory.

## Smoke (`--profile small --device OPTIX --smoke`)

`COMPLETE {"fixations": 5, "objects": 4, "terminations": {"attention_complete": 2, "seed_uninitializable": 1, "smoke_budget": 1}}`

- Gate status: `PASS_CONTROLLER_TRANSITION_EXERCISED`.
- Primary instances [107, 108]. The probe continued to 109 and then 110. On 110 `beams`,
  `fsg6f` selected the second look.
- The comparison with the legacy `classroom-oracle-1-smoke-2` found 0 behavioral mismatches.

## Full golden run (`--profile full --device OPTIX`, 10 min 48 s)

Compared against the legacy `previews/classroom-oracle-1-full` by content, not archive bytes:

| quantity | frozen | staging |
|---|---|---|
| target IDs / order | 25, 107…234 | identical |
| seeds.json (gazes, domain, head pose) | — | identical |
| dense reference `reachable_samples.npz` | — | arrays identical |
| per-look gaze, action source, target points, new surfels, matcher, fusion, FSG6f and Cyclopean decisions | — | identical (104/104) |
| per-object fixations / termination / final surfels / incidentals | — | identical (25/25) |
| map snapshots xyz/ids/support/provenance, oracle patches | — | 104/104 and 104/104 equal |
| total fixations | 104 | 104 |
| action sources | 25 / 53 / 26 | 25 oracle_seed / 53 fsg6f / 26 cyclopean_epistemic |
| terminations | 25 attention_complete | 25 attention_complete, 0 watchdog_24 |
| truth isolation / no decomposition flags | false / false | false / false |
| reachable / covered | 29,288 / 25,618 | 29,288 / 25,618 |
| coverage (stored) | 0.8746927069106801 | 0.8746927069106801 |
| per-object evaluation table | — | equal at stored precision |
| zero-new-surfel looks | 4 | 4 |

**Colour is not bit-reproducible, and this predates the migration.** The Cycles Combined
(RGB) pass differs between runs on OptiX. The legacy repo's own two smoke runs show it
(`smoke` vs `smoke-2`: observation rgb max |Δ| 3.0e-4, map rgb 1.2e-7). Position and Object
Index passes are bit-exact, and these are the only passes the controller uses. The map `rgb`
arrays (129 of them) were therefore compared separately rather than exactly. Max |Δ| is
1.4e-4. No threshold was applied to any behavioral quantity.

## Demo

`previews/classroom-oracle-1-full/demo/` (gitignored), made by `tools/consolidation1_demo.py`:

- 104 four-panel frames:
  - dense reference with target and gaze trail
  - the saved L|R pair
  - the replayed Cyclopean evidence
  - the accumulating cloud
- `classroom-oracle-1-demo.mp4` (mp4v)
- `overview.png`, `last_frame.png`
- `panoramas/` (reference comparison, observed RGB, instance reference)
- PLY files: 25 per-object clouds plus a whole-scene cloud (945,080 surfels)
- `Demo.md` with the reproduction commands

The demo's own check recomputes coverage and requires it to equal `evaluation.json`. It PASSES.

## Disk

- Legacy repo: 598 tracked files, 15,257,664 bytes.
- Staging: 31 tracked files including this report.
- Untracked scene: 54 files, 150 MB.

## Hidden assumptions found

1. `python3` on this workstation's PATH is a conda 3.10 interpreter (`miniconda/envs/world2018`). The legacy
   venv was built from `/usr/bin/python3.12`. A venv built from a plain `python3` gets 3.10,
   so the staging venv was rebuilt from `/usr/bin/python3`. The README says so.
2. `scenes/classroom/` is gitignored, and the blend is not self-contained. It links
   `//assets/*.blend` and relative textures, so the whole 150 MB directory is required.
   Some image paths (`//../../textures/_baseTextures/*`) are missing in the legacy checkout
   as well. The copy reproduces the same state.
3. `classroom_eye.blend` has no md5 in `scenes/manifest.json`. It is rebuilt by
   `place_eye.py` from `classroom.blend`, and the byte-identity of a rebuild is untested.
   The acceptance run used a copy. The sha256 is now recorded in `migration-manifest.json`.
4. Blender 5.2.1 LTS at `/usr/local/bin/blender`, OptiX on an RTX 4090, and `ffmpeg` only from
   conda. The MP4 was written through OpenCV `mp4v`, not ffmpeg.
5. `render_foveated.py` is on the golden path only for `render_fixation()`. Its OSL shader is not needed.
