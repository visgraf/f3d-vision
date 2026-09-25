# Legacy provenance

## Source

| | |
|---|---|
| legacy repository | https://github.com/visgraf/fov-3d-vision |
| local checkout at extraction | `/home/lvelho/rd/fov-3d-vision` |
| branch | `classroom-oracle-3b` |
| freeze tag (annotated, pushed) | `legacy-classroom-oracle3b-2026-09-25` |
| freeze commit | `48a3139020e87bfaf1255df1585390f7e9094ec8` — "CLASSROOM_ORACLE3B_COMPLETE: the Cyclopean gap is remote and unseen, not a thin halo" |
| golden experiment | Classroom-Oracle-1 full, original domain yaw ±25°, pitch ±20° |
| golden result record | `docs/classroom-oracle-1.md`, section "Result — 2026-09-24, repaired smoke gate and full run"; smoke-gate repair `ee578d5`, four mechanical repairs `f850946`; all contained in the freeze commit |

The freeze commit is HEAD of `classroom-oracle-3b`; there was no later work. Every
migrated file was copied from the git blob at the freeze commit (`git show 48a3139:<path>`),
not from the working tree, and its sha256 is recorded in `migration-manifest.json`.

Oracle-2 (a domain ablation) and Oracle-3 / 3b (read-only diagnostics) are **not** part of
this extraction and their code is not present. Their results remain in the legacy repo.

## Active inherited contracts

These were in force at the freeze and are carried unchanged by the migrated code.

**Classroom-Oracle-1 public contract** (`tools/classroom_oracle1_public.py`, digest
`de19e51eb72aefec58675408bcc86d8d58c220a35aa6046b0a6fbf7dabe11b88`):

- Blender truth replaces only the local stereo matcher for the current tangent pair;
  same-instance binocular rule; half-occlusions stay unmeasured; no SGBM range bound.
- Blender may enumerate controller-domain-visible instances and give **one seed gaze per
  instance**. It never selects a later fixation, declares completion, or fills holes.
- Dense seed-scan truth (`bootstrap/evaluation_only/`) is never opened by the controller;
  the evaluator refuses to run before `control_complete: true`.
- No foreground/background decomposition: every renderable object is an ordinary instance.
- Controller: frozen FSG6f via the `multiobject2c_policy` adapter; on `no_frontier`, the
  Cyclopean `NEVER_OBSERVED + EXTERIOR` shoreline handoff, deepest border distance first.
- Persistent metric memory `fsg3_surface_map`, fixed head frame, **12 mm** association
  radius and hash cell; initialization precondition 100 target points.
- Empty looks are recorded and fuse zero; `seed_uninitializable` objects are kept.
- **24-look** per-object watchdog (engineering only, never a PASS/FAIL gate).
- Every look retains raw L/R multilayer EXR, rectified PNG pair, oracle patch, map snapshot.

**Frozen FSG6f constants** (`tools/fsg6f_public.py`): controller domain yaw −25..25°,
pitch −20..20°; vergence 2.1 m; spp small 64 / full 256; the full frontier and consensus
parameter set in `PUBLIC_SPEC`.

**Working agreement** (legacy `CLAUDE.md`, not copied): metres; fixed head, eyes rotate
about their centres; `EYE` camera local −Z gaze, +Y up; two interpreters (Blender-side
scripts use only bpy/mathutils/numpy; host scripts use `.venv`); `blender -b -P` exits 0 on
failure, so Blender-side tools catch and exit nonzero; measured or assumed, never in
between; every tool ships a check that can fail; regenerable artifacts are not committed;
git forward only.

**Decisions** (legacy `DECISIONS.md`, not copied) most directly embodied by this code:
D2/D3 (fixed warp, fixed head), D12 (two eyes on the EYE rig), D13 (epipolar frame on the
head's X axis), D17 (the active loop lives in the repo), D-FSG3a (single-object frontier
growth), D-FSG6a…6f (3-D surfel frontier, persistent states, candidate consensus),
D-REALITY2b (empty looks), D-CYCLOPEAN1E/1F (epistemic gaze).
