# Current architecture map (as migrated, before refactoring)

This maps the 17-file golden runtime closure by responsibility. The files have not been
moved or renamed; every path below is where the file lives today, byte-identical to
legacy `48a3139`. The map is the input to Consolidation 3.

The closure is:

- the 16 runtime modules under `tools/`;
- the acceptance check `tools/dev/check_classroom_oracle1.py`.

Outside the closure, and not mapped here:

- `tools/place_eye.py`, the scene generator;
- `tools/dev/check_fsg_tangent_frame.py`;
- `tools/consolidation1_demo.py`, which is post-hoc only;
- the Consolidation 2 checkers.

"Direct project imports" means imports of other repository modules, including imports
made inside functions (marked *(in function)*). The names in brackets are what the
golden path actually uses from that import.

## Process boundary

Two interpreters. The host `.venv` (Python 3.12) runs orchestration, measurement,
fusion, control and evaluation. Blender 5.2.1 (bundled Python 3.13) runs only
`classroom_oracle1_render.py`, which the runner launches as
`blender -b <scene> -P tools/classroom_oracle1_render.py -- --mode {seeds|fixation}`.
The two sides share only the files each render writes (`seeds.json`,
`calibration.json`, `oracle_observation.npz`, raw EXRs) and the pure-numpy modules
both import (`classroom_oracle1_public`, `fsg_geometry`, `fsg6f_public`, `exr_lite`, `warp`).

## 1. Sensing / rendering (Blender side)

| file | role | direct project imports |
|---|---|---|
| `tools/classroom_oracle1_render.py` | Blender entry point. `seeds` mode: ray-casts the controller domain at 0.25° from the fixed head, assigns instance ids (sorted renderable objects), writes one seed gaze per visible instance plus the evaluation-only dense samples. `fixation` mode: builds the binocular calibration for a gaze, renders the L/R perspective tangent pair with Combined + Position + Object Index, and extracts them into `oracle_observation.npz`. | `classroom_oracle1_public` [SPEC_ID, defaults, SEED_SCAN_STEP_DEG]; `fsg_geometry` [CV_TO_BLENDER, make_calibration]; *(in function)* `fsg6f_public` [SURFACE_FRONTIER, VERGENCE_DISTANCE_M, DEFAULT_SPP], `bl_common` [find_eye, rigid, ensure_cycles, setup_device, pin_seed, configure_multilayer_exr], `render_foveated` [render_fixation], `exr_lite` [read_uncompressed_exr] |
| `tools/bl_common.py` | Blender helpers: EYE lookup, rigid transform, Cycles and device setup, multilayer EXR output, seed pinning (the Classroom `.blend` keyframes `cycles.seed`). | — (bpy, mathutils, addon_utils) |
| `tools/render_foveated.py` | Only `render_fixation()` is on the golden path: it renders at a given spp and seed and asserts the sampling settings held. Its OSL foveated-camera code is not used. | `bl_common`; `warp` [raster_size, s0_of; re-export only] |
| `tools/warp.py` | Foveated warp maths. On the golden path it is only an import dependency of `render_foveated`. | — |
| `tools/exr_lite.py` | numpy-only reader for uncompressed multilayer EXR, since Blender's Python has no OpenEXR. | — |

## 2. Stereo / oracle measurement (host)

| file | role | direct project imports |
|---|---|---|
| `tools/classroom_oracle1_matcher.py` | The perfect local matcher. From one rendered pair it rectifies and crops the core, and accepts a left truth point only if its reprojection lands on supported right-eye data of the same instance. Returns the H-frame patch record and the per-eye id/support state. No SGBM, no range bound. | `fsg_geometry` [make_calibration, pixels, rays_h, head_to_world, world_to_head]; `fsg_stereo` [rectification, remap, support_mask] |
| `tools/fsg_stereo.py` | Inherited FSG1 stereo instrument. On the golden path only its rectification, remap and support-mask functions are used; its SGBM path is not called. | `fsg_geometry` [validate_calibration, relative_pose, pixels, crop_q, reproject_q, rect_to_head, json_write] |

## 3. Geometry / fusion

| file | role | direct project imports |
|---|---|---|
| `tools/fsg_geometry.py` | Frame conventions (fixed head H, OpenCV camera C) and binocular calibration: gaze direction, per-eye rotations, K, projection, head↔world. Pure numpy; imported by both interpreters. | — |
| `tools/fsg3_surface_map.py` | Persistent head-frame surfel map: `Patch`, `initialize`, `fuse` with the 12 mm association radius and hash cell, idempotent replay, provenance mask. | — |

## 4. Local frontier control

| file | role | direct project imports |
|---|---|---|
| `tools/fsg6f_public.py` | The frozen FSG6f contract and constants: domain yaw ±25°, pitch ±20°, 12 mm fusion, vergence 2.1 m, spp, the frontier and consensus parameters. | — |
| `tools/fsg6f_frontier.py` | Truth-free 3-D surfel-frontier controller. Extracts the raw frontier, classifies it OPEN / MAP_RESOLVED / BOUNDARY_RESOLVED, applies the continuation corridor and the strict-majority candidate consensus, and returns `choose_next` (a gaze, or `no_frontier`). | `fsg6f_public` [SURFACE_FRONTIER, FUSION, VERGENCE_DISTANCE_M, OBJECT_ID, BACKGROUND_ID]; `fsg_geometry` [make_calibration]; `fsg_stereo` [rectification] |
| `tools/multiobject2c_policy.py` | Pure adapter. It relabels the scene's target instance id into FSG6f's fixed `OBJECT_ID` namespace and builds history entries; the geometry and all constants are untouched. | `fsg6f_frontier` [choose_next]; `fsg6f_public` [OBJECT_ID] |

## 5. Cyclopean / epistemic control

| file | role | direct project imports |
|---|---|---|
| `tools/classroom_oracle1_epistemic.py` | A fixed-head angular chart at 0.10° accumulating what the completed looks observed (any, target, non-target, target with depth). After FSG6f returns `no_frontier`, it audits map support and chooses one `NEVER_OBSERVED + EXTERIOR` shoreline cell, deepest border distance first, or `stop`. | `classroom_oracle1_public` [CYCLOPEAN_GRID_DEG, FUSION]; `fsg_stereo` [rectification]; *(in function)* `fsg6f_public` [SURFACE_FRONTIER] |

## 6. Experiment orchestration

| file | role | direct project imports |
|---|---|---|
| `tools/classroom_oracle1_public.py` | The experiment's public contract: spec id, scene path, defaults, 24-look watchdog, 100-point initialization floor, fusion rule, and the oracle / control / benchmark contracts with their digest. | — |
| `tools/classroom_oracle1_run.py` | The control loop. It launches the Blender bootstrap, then for each seed runs: render → match → initialize or fuse (with an idempotence replay) → Cyclopean evidence → FSG6f next gaze → Cyclopean handoff on `no_frontier`. This repeats until `attention_complete`, `seed_uninitializable` or the watchdog. It writes all per-look artifacts, the manifest, and the repaired smoke gate. | `classroom_oracle1_epistemic`, `classroom_oracle1_matcher`, `classroom_oracle1_public`, `fsg3_surface_map` [Patch, initialize, fuse], `fsg6f_public` [FUSION], `multiobject2c_policy` [choose_next, history_entry] |
| `tools/dev/check_classroom_oracle1.py` | The 12 fail-capable acceptance checks: contract self-tests, a source scan (no SGBM, the same-instance rule, the runner never names `evaluation_only`, Blender contains no policy), the inherited constants, benchmark retention, and empty looks. | `classroom_oracle1_epistemic`, `classroom_oracle1_matcher`, `classroom_oracle1_public`, `classroom_oracle1_run`, `fsg6f_public`, `multiobject2c_policy` |

## 7. Evaluation

| file | role | direct project imports |
|---|---|---|
| `tools/classroom_oracle1_eval.py` | Offline only, and only after `control_complete`. It opens the dense evaluation-only samples and counts a sample covered if a final surfel lies within 12 mm (exact, via a spatial hash). Writes per-object and aggregate coverage to `evaluation.json`. | `classroom_oracle1_public` [FUSION, SPEC_ID] |

## Dependency graph

```
classroom_oracle1_run ─┬─ classroom_oracle1_public
                       ├─ classroom_oracle1_matcher ─┬─ fsg_geometry
                       │                             └─ fsg_stereo ─ fsg_geometry
                       ├─ classroom_oracle1_epistemic ─ public, fsg_stereo, (fsg6f_public)
                       ├─ fsg3_surface_map
                       ├─ fsg6f_public
                       └─ multiobject2c_policy ─ fsg6f_frontier ─ fsg6f_public, fsg_geometry, fsg_stereo
   ⇣ subprocess (Blender)
classroom_oracle1_render ─ public, fsg_geometry, (fsg6f_public, bl_common, exr_lite,
                           render_foveated ─ bl_common, warp)
classroom_oracle1_eval ─ classroom_oracle1_public
```

## Observations for Consolidation 3 (not acted on here)

- Frame and calibration code (`fsg_geometry`), rectification (`fsg_stereo`) and
  the frontier controller (`fsg6f_frontier`) carry experiment-lineage names (FSG1, FSG6f)
  that describe history, not role.
- `fsg6f_public` mixes the controller's frozen constants with FSG6f fixture metadata
  (`OBJECT_ID`, `BACKGROUND_ID`, fixtures, seeds). `multiobject2c_policy` exists only to
  map scene ids into that fixture namespace.
- `render_foveated.py` and `warp.py` are on the path only for `render_fixation`. The
  foveated OSL camera, which the project is named for, is not used by the golden run.
- The runner binds inherited APIs by introspection (`_construct_patch`,
  `_history_entry`, `_decision_gaze`). That tolerance to API drift is a refactor target.
