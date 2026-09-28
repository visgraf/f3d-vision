# Consolidation 3 — Conceptual API Refactor

Date: 2026-09-25

## Purpose

Consolidation 1 extracted the minimal living system. Consolidation 2 sealed it and reproduced the Classroom-Oracle-1 golden behavior a second time with zero behavioral mismatches.

Consolidation 3 introduces the **new conceptual software boundary** without changing scientific behavior and without yet implementing the new partition/dual-graph architecture.

The key decision is deliberately conservative:

> **Do not physically move the proven implementation yet. Put a clean `fov3d` API facade in front of it, prove the facade against the sealed golden baseline, and make all future architecture depend on the facade rather than on historical `tools/*` module names.**

The permanent repo is already small. Physical movement of path-sensitive Blender/runtime modules now would create risk without scientific value. The facade makes future code independent of the historical file layout while preserving the sealed engine byte-for-byte.

## Required starting state

Repository:

`/home/lvelho/rd/fov-3d-vision-core`

Required HEAD:

`760d216` — `Seal minimal Classroom Oracle baseline`

Required ancestor tag:

`baseline-classroom-oracle1-2026-09-25`

Before work begins, create an annotated safety tag on `760d216`:

`consolidation2-sealed-2026-09-25`

The legacy and staging repos are read-only references and must remain unchanged.

## Scientific invariant

This step is **structural only**.

Forbidden:

- controller-policy changes;
- threshold changes;
- matcher changes;
- fusion changes;
- domain changes;
- renderer/scientific-setting changes;
- scene changes;
- new partition/graph behavior;
- new object-discovery behavior;
- retuning to make acceptance pass.

The 31 files protected by the sealed baseline tag remain byte-identical throughout this step.

## Phase A — make behavioral acceptance durable

Consolidation 2 identified one remaining refactor risk: the behavioral comparator exists only in `/tmp`, while the reference run lives in gitignored `previews/`.

Before introducing the facade:

1. Promote the proven Consolidation-2 comparator into the repo as `tools/compare_golden.py`.
2. Remove all scratch absolute paths from it.
3. Make it accept an explicit reference run and candidate run.
4. Validate it against the Consolidation-1 and Consolidation-2 full golden records: **0 mismatches**.
5. Generate a compact committed behavioral signature at:

   `tests/golden/classroom-oracle1-signature.json`

   The signature must contain the behavior that the comparator actually checks, not RGB image bytes or archive metadata. At minimum it records:

   - 25 target IDs and ordering;
   - seed gazes;
   - 104 gaze/action-source decisions;
   - target-point and fusion counts used by the accepted comparator;
   - FSG6f and Cyclopean decision fields used by the accepted comparator;
   - per-object fixation counts and terminations;
   - canonical hashes of non-RGB map/patch arrays used by the accepted comparator;
   - 29,288 reachable / 25,618 covered / coverage 0.8746927069106801;
   - action-source histogram 25/53/26;
   - 25 attention-complete / 0 watchdog.

6. Add `scripts/compare_golden.sh` to compare a new run directly against the committed signature.

The signature generator and comparator must explicitly ignore the already documented OptiX RGB nondeterminism while still checking controller-relevant geometry, IDs, support/provenance, decisions and metrics.

## Phase B — introduce the conceptual `fov3d` API

Create a top-level Python package `fov3d/` using the machine-readable mapping in `docs/consolidation-3-layout.json`.

The first version is a **facade**. It re-exports the sealed implementation from the existing minimal `tools/*` modules; it does not copy or modify that implementation.

Conceptual layout:

```text
fov3d/
  __init__.py
  _compat.py

  rendering/
    blender.py
    exr.py
    foveated.py
    warp.py

  geometry/
    core.py

  reconstruction/
    surface_map.py

  stereo/
    core.py

  control/
    frontier.py
    frontier_config.py
    object_policy.py

  experiments/
    classroom_oracle/
      config.py
      matcher.py
      epistemic.py
      render.py
      run.py
      eval.py
```

This package is the boundary future code will import.

### Why a facade first

The sealed report exposed real path/environment assumptions: Blender-side imports, repository-relative paths, a generated/linked Classroom scene, and a runtime split between host Python and Blender Python. Moving the implementation immediately would couple a filesystem refactor to those assumptions.

A facade gives us the conceptual architecture now while keeping the verified engine fixed underneath it.

## Phase C — verify the facade itself

Use `tools/dev/check_fov3d_facade.py` to verify:

- every mapping entry imports from both old and new names;
- the new facade re-exports the old module's public callables/values;
- package imports resolve only inside the permanent repo;
- the old sealed files are unchanged;
- no historical experiment module is reintroduced.

In addition, run a smoke experiment through the **new package entry point**. The package route must exercise a genuine post-seed controller transition and match the sealed smoke.

The existing legacy entry point must continue to work as well.

## Phase D — full golden acceptance through the new API

Run one full Classroom-Oracle-1 experiment through the `fov3d` package entry point, not the historical top-level runner invocation.

Compare it against the committed signature.

Required headline result:

```text
targets                    25
fixations                  104
action sources             25 oracle_seed / 53 fsg6f / 26 cyclopean_epistemic
attention_complete         25
watchdog_24                0
reachable                  29,288
covered                    25,618
coverage                   0.8746927069106801
behavioral mismatches      0
```

Truth must remain closed during control and foreground/background decomposition must remain disabled.

## Phase E — document the stable boundary

Add:

`docs/fov3d-api.md`

It should explain that:

- `fov3d` is the stable conceptual API for future development;
- `tools/*` is the sealed compatibility engine for the legacy controller baseline;
- future partition/segmentation/topology work must import `fov3d`, not legacy `tools` modules directly;
- legacy modules may be moved behind the facade later, one conceptual block at a time, but physical movement is no longer a prerequisite for the new architecture.

Update `docs/current-architecture-map.md` to show the facade boundary but do not rewrite history.

## Acceptance gates

All must hold:

1. `760d216` is tagged with `consolidation2-sealed-2026-09-25`.
2. A git bundle safety backup exists outside the repo.
3. Every sealed pre-existing tracked file is byte-identical.
4. The in-repo golden comparator reproduces 0 mismatches on the two already accepted full runs.
5. The committed compact signature is generated from an accepted full run.
6. `tools/dev/check_fov3d_facade.py` passes.
7. `scripts/verify_baseline.sh` still passes unchanged.
8. Smoke through `fov3d` matches the sealed smoke.
9. Full run through `fov3d` matches the committed golden signature with 0 mismatches.
10. Legacy and staging repos remain unchanged.

## Explicit non-goals

This step does **not**:

- implement the spherical partition;
- implement primal/dual region graphs;
- redesign segmentation;
- alter FSG6f or Cyclopean eligibility;
- physically relocate the sealed implementation;
- solve the Classroom asset-distribution problem;
- create a GitHub remote.

Those are intentionally separated from the API refactor.

## Success token

The final report must end with exactly:

`CONSOLIDATION3_API_REFACTOR_COMPLETE`
