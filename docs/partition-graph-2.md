# Partition-Graph Phase 2 — Retrospective Classroom Lift

## Scientific question

Phase 1 proved that the new representation can express a scene partition, embedded boundary graph, dual region graph, disconnected visible components belonging to one object hypothesis, and a separate observation overlay.

Phase 2 asks a narrower question before any new controller is designed:

> **When the already-completed Classroom-Oracle-1 trajectory is expressed as a partition/dual graph at each fixation, what structure becomes visible that the old shoreline representation did not expose directly?**

This is a retrospective representation experiment. It does not select a gaze.

## Truth isolation

The lift may read only saved controller-time artifacts:

- `manifest.json`;
- `bootstrap/seeds.json` (controller-visible domain and head pose);
- each completed fixation's `calibration.json`;
- the persistent target map snapshots under `maps/fix_XX.npz`.

It deliberately does **not** read:

- `bootstrap/evaluation_only/reachable_samples.npz`;
- any dense evaluation truth;
- `evaluation.json`;
- future fixations while constructing an earlier fixation state;
- Blender or the scene file.

Every read performed by the lift goes through a path logger. The final summary records all input paths and rejects evaluation-truth paths.

## Lifted representation

For each target object and completed map snapshot:

1. Project the persistent 3-D target surfels into the legacy head-centered spherical chart.
2. Give each surfel its existing 12 mm metric association footprint projected to angular support.
3. Compute connected target-support regions.
4. Compute connected components of their complement as `BASE` regions.
5. Extract object/base boundary chains and derive the dual graph from those chains.
6. Group all target components under the already-existing target hypothesis. This **does not infer identity**; the target identity is inherited from the completed Oracle experiment.
7. Reconstruct left and right tangent-plane footprints from each saved calibration and accumulate them as a separate observation overlay.
8. For every disconnected pair of target components, ask whether both are adjacent in the dual graph to the same `BASE` region. If so, record the shared base region and its observation-state composition.

The last query is descriptive, not a controller rule. A shared base neighbor is not automatically an occluder, a continuation, or a hole.

## Representation hardening folded into Phase 2

Before lifting real data, Phase 2 repairs issues found by the Phase-1 audit:

- footprint source (`LEFT`, `RIGHT`, `BINOCULAR`) is separated from derived visibility (`UNOBSERVED`, `LEFT_ONLY`, `RIGHT_ONLY`, `BINOCULAR`);
- non-unit sphere directions and normals are rejected rather than silently normalized on save;
- occlusion front/back attributes must name the boundary's incident regions;
- ndarray-bearing dataclasses no longer expose broken generated value-equality/hash semantics;
- optional 3-D boundary arrays are part of the structural checker and must round-trip bit-exactly;
- same-object adjacent faces are **explicitly allowed** when a real boundary relation separates them (e.g. self-occlusion, crease, depth discontinuity); they are not automatically merged merely because `object_id` matches;
- serialization advances to `f3d-vision-scene-partition-v2` while reading valid v1 files;
- the Phase-1 SVG includes the base node and uses the repository venv in its regeneration command.

## What Phase 2 can and cannot establish

It can establish that the partition/dual view exposes topological facts such as:

- one target hypothesis occupying multiple disconnected spherical regions;
- multiple connected `BASE` components;
- two disconnected target regions sharing a particular base neighbor;
- whether that shared base territory lies mostly outside or inside the accumulated left/right observation footprints;
- merges or splits of target partition components as fixations add geometry.

It cannot establish automatic object identity, semantic segmentation, occlusion direction, or the next fixation. Those belong to later phases.

## Required full experiment

Use a full 25-object Classroom-Oracle-1 run that first passes the committed golden comparator. If no validated full run exists in the active repository, generate a fresh one with `scripts/run_golden.sh` and verify `MISMATCHES 0` before lifting it.

The output is post-hoc under `previews/partition-graph-2-full/` and includes one saved graph/state per fixation, aggregate summaries, and a synchronized four-panel demo.

## Acceptance

- Phase-2 checker: zero failures.
- Baseline verifier: unchanged and passing.
- Golden smoke: `MISMATCHES 0`.
- Source full run: `MISMATCHES 0` against the committed signature.
- No dense truth opened by the lift.
- No controller, matcher, fusion, rendering, gaze, or termination code changed.
- Report all graph-derived measurements without tuning a new policy.
