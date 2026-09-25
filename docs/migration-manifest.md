# Migration manifest — Consolidation 1

Machine-readable form, with every sha256 and the reason for every excluded file:
[`migration-manifest.json`](../migration-manifest.json). Source: legacy freeze commit
`48a3139` (tag `legacy-classroom-oracle3b-2026-09-25`), 598 tracked files.
Migrated: 25 unchanged, plus 5 new. Excluded: 573.

## How the closure was computed

A scratch audit (outside both repositories) parsed every `import` / `from … import`
node, including function-local ones, recursively from the roots:

```
tools/classroom_oracle1_{public,render,matcher,epistemic,run,eval}.py
tools/dev/check_classroom_oracle1.py
docs/classroom-oracle-1.md
```

and resolved each name against tracked files in `tools/` and `tools/dev/`. The
function-local imports matter: `classroom_oracle1_render.py` reaches `bl_common`,
`exr_lite` and `render_foveated` (→ `warp`) only from inside functions, and those
four modules are not in the list of direct imports in the task.

Dynamic references checked by hand: the runner launches
`blender -b <scene> -P tools/classroom_oracle1_render.py`; the scene path is
`classroom_oracle1_public.SCENE`; `tools/foveated_camera.osl` is referenced only by
`render_foveated.main()` / `setup_foveated_camera`, which the golden path does not call
(it uses `render_fixation()` with a perspective camera), so it is excluded.

## Dependency graph (repository-local)

```
classroom_oracle1_run ──┬─ classroom_oracle1_public
                        ├─ classroom_oracle1_matcher ─┬─ fsg_geometry
                        │                             └─ fsg_stereo ── fsg_geometry
                        ├─ classroom_oracle1_epistemic ─ public, fsg6f_public, fsg_stereo
                        ├─ fsg3_surface_map
                        ├─ fsg6f_public
                        └─ multiobject2c_policy ─ fsg6f_frontier ─ fsg6f_public, fsg_geometry, fsg_stereo
   (subprocess, Blender) classroom_oracle1_render ─ public, fsg_geometry, fsg6f_public,
                        bl_common, exr_lite, render_foveated ─ bl_common, warp
classroom_oracle1_eval ── classroom_oracle1_public
```

External: host `.venv` — numpy, opencv (`cv2`), pillow (`PIL`, imported at top of
`fsg_stereo`). Blender-bundled — bpy, mathutils, addon_utils, numpy.

## Migrated (byte-identical to the freeze blob)

| group | files |
|---|---|
| runtime (16) | `tools/` bl_common, classroom_oracle1_epistemic, classroom_oracle1_eval, classroom_oracle1_matcher, classroom_oracle1_public, classroom_oracle1_render, classroom_oracle1_run, exr_lite, fsg3_surface_map, fsg6f_frontier, fsg6f_public, fsg_geometry, fsg_stereo, multiobject2c_policy, render_foveated, warp |
| verification (2) | `tools/dev/check_classroom_oracle1.py`; `tools/dev/check_fsg_tangent_frame.py` (the only other `tools/dev` script whose import closure lies inside the runtime) |
| scene (2) | `scenes/manifest.json`, `tools/place_eye.py` |
| environment (4) | `requirements.txt`, `requirements-fsg.txt`, `.gitignore`, `LICENSE` |
| docs (1) | `docs/classroom-oracle-1.md` |

Module self-tests run in place of checks that would pull in excluded modules:
`fsg3_surface_map.self_test`, `fsg6f_frontier.self_test`, `fsg_geometry --self-test`,
`warp --self-test`, `classroom_oracle1_matcher --self-test`,
`classroom_oracle1_{public,epistemic,run}.self_test`. (`check_fsg3.py` needs `fsg3_scene`,
`fsg3_policy`; `check_fsg6f.py` needs `fsg6f_scene`, `fsg6e_*`, `fsg4_public`.)

## New in staging

| file | purpose |
|---|---|
| `README.md` | fresh staging README |
| `docs/legacy-provenance.md` | freeze tag/commit, golden result, inherited contracts |
| `docs/migration-manifest.md`, `migration-manifest.json` | this manifest |
| `tools/consolidation1_demo.py` | post-hoc migration-baseline demo; **not** in the golden runtime; imports only closure modules; its check (coverage recomputed = `evaluation.json`) exits 1 on mismatch |

## Scene (untracked, generated)

`scenes/classroom/` is gitignored, as in the legacy repo. Rebuild: download
`classroom.zip` (md5 `3adbb7114b514bfc6fc724ce20f86b4e`, CC0) and unzip into
`scenes/classroom/`, then run `tools/place_eye.py` with `--location -0.6 -1.0 1.2 --yaw 0`.
For acceptance the directory was copied byte-identically from the legacy checkout
(54 files, 150 MB; `classroom_eye.blend` sha256
`dca66a3257b909aef00b0331652c55f62a93a8dff0665d070fba7efa436953cc`). The blend links
`//assets/*.blend` and textures relatively, so the whole directory is required, not the
`.blend` alone. `scenes/hdri/workshop/asset.json` is not needed by the Classroom.

## Excluded (573)

| family | files | reason |
|---|---:|---|
| docs history | 167 | experiment notes, log, summaries; stay in the legacy repo |
| tools fsg* | 97 | historical FSG experiments (fsg1–fsg7, validation, audits) outside the closure |
| tools/dev historical checks | 64 | check an excluded module, or import one |
| tools multiobject* | 61 | MultiObject experiments; only `multiobject2c_policy.py` is on the golden path |
| tools cyclopean* | 28 | Cyclopean-1a…1g experiments; the handoff used is `classroom_oracle1_epistemic` |
| tools scene* | 25 | Scene-1 experiments and `scene_render_fix` |
| tools phase A–D infrastructure | 24 | preview, reference, noise, pairs, sequence, stereo instruments, fetch_hdris, make_* |
| docs/reference | 20 | Phase A CPU baseline images |
| tools fullscene_real* / fullscene* | 15 / 12 | full-scene experiments |
| tools reality* | 15 | Reality checks |
| tools classroom_oracle2/3/3b | 12 | Oracle-2 is a domain ablation; Oracle-3/3b are read-only diagnostics |
| tools fsg_bridge* / fsg_blend_bridge* | 7 / 2 | Blender bridge experiments |
| tools demo_classroom* / demo_tabletop* | 5 / 5 | earlier demos, bound to their own experiments |
| root docs | 3 | legacy README, DECISIONS.md, CLAUDE.md; referenced from `legacy-provenance.md` |
| tools classroom_fsg* | 3 | Classroom-FSG-1 (SGBM) |
| tools/dev oracle-2/3/3b checks | 3 | not golden |
| tools/dev stub | 3 | `fake_blender_*` sandbox stubs |
| scenes hdri | 1 | HDRI descriptor for other scenes |
| tools OSL | 1 | `foveated_camera.osl`, not on the golden path |
