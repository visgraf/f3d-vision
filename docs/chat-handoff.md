# Chat Handoff

## Accepted main

    main @ 85c09381584e30c3643bd55be23183f1cdbd2af7

Accepted milestone: Conceptual Core 10.

## Working arrangement

- Luiz is the scientific and acceptance authority.
- Chat is the architecture and review surface. It reads, designs and reviews only, and it
  does not mutate GitHub or the workstation checkout.
- Claude Code is the execution and mutation surface. It performs every repository
  mutation and every measured execution in dedicated isolated git worktrees, under the
  branch/HEAD/clean-tree guard, never by switching branches in the shared
  `/home/lvelho/rd/f3d-vision` checkout.
- GitHub is the durable source of truth.
- Migrate behavior first, redesign structure second, and answer one causal question per
  Core.

## Accepted scientific / architectural state

The sealed scientific behavior is unchanged through Conceptual Cores 1–10.

Conceptual ownership established so far:

- `fov3d.reconstruction.measurement_memory`
  - valid patch measurement filtering
  - append-only instance-keyed measured 3-D memory
  - effective target geometry composition
- `fov3d.geometry.head_chart`
  - fixed-head yaw/pitch mapping and chart indexing
- `fov3d.reconstruction.association`
  - canonical 12-mm surface association radius
- `fov3d.epistemic.head_memory`
  - persistent head-centered epistemic memory
  - `HeadEvidence`
  - `add_head_patch`
- `fov3d.scene.partition`
  - `SupportLayer`
  - `support_depth_from_map`
  - `joint_owner`
  - `label_joint_regions`
- `fov3d.scene.boundaries`
  - `_interface_edges`
  - `_trace_edge_components`
  - `extract_boundaries`
- `fov3d.scene.corridors`
  - Core 6, gap-corridor geometry: `_component_boundary`, `_line_cells`, `gap_corridor`,
    `corridors_for_object`
  - Core 10, corridor relation origin: `_region_code`, `_own_labels`,
    `_joint_region_own_component`, `relation_origin`
- `fov3d.scene.lineage` (Core 7)
  - `_lineage`
  - `_target_component_raster`
- `fov3d.scene.state_validation` (Core 8)
  - `attach_state_region_codes`, which keeps its compatibility name; the rename is
    deferred
- `fov3d.scene.relations` (Core 9)
  - the NumPy-only boundary-depth-order module: `_region_object`, `_weighted_quantile`,
    `boundary_depth_order`

The Phase-4 adapter `fov3d/experiments/classroom_partition/relations.py` keeps identity
imports of the Core-9 and Core-10 names; `annotate_corridor` resolves the scene functions.

`fov3d.scene` lazily re-exports the four scene-partition names, so a bare
`import fov3d.scene` stays OpenCV-free. The modules `boundaries`, `corridors`, `lineage`,
`state_validation` and `relations` are imported explicitly. `corridors` needs `cv2`; the
others are NumPy-only.

Conceptual Core 10 was accepted at `85c09381584e30c3643bd55be23183f1cdbd2af7` with:

    CONCEPTUAL_CORE10_RELATION_ORIGIN_PRESERVES_BEHAVIOR

The evidence, from `docs/migration-conceptual-core-10-report.md`, includes:
- the four moved definitions are source-text and AST identical to their previous
  implementation, with equivalent global bindings;
- the move into `corridors.py` was a pure append, leaving its imports and existing
  functions unchanged;
- the Core-10 checker passes 29/29; it caught 27/27 non-equivalent behavioral mutants
  and 9/9 static/package mutants;
- the Phase-4 relation product is 211/211 byte-identical, from 484 executions of
  `relation_origin`;
- the replays the import audit required (Phase 3 and the Phase-8b proposer/evaluator) are
  byte-identical;
- the sealed baseline is 31/31 and the golden comparison reports `MISMATCHES 0`.

The cleanup of `own_support_labels` versus `_own_labels`, and of `component_lineage`
versus `fov3d.scene.lineage._lineage`, remains **deferred**. Each pair is a measured
behavioral duplicate, but unifying them is a separate causal question.

## Active next step

Conceptual Core 11: the epistemic partition (`docs/migration-conceptual-core-11.md`).

Causal question: can the accepted epistemic-region representation and partition
constructor be moved out of the Phase-6 benchmark module into the reusable epistemic layer
without changing any behavior?

Bounded target, moved intact from `fov3d/experiments/classroom_partition/benchmark.py` to
`fov3d/epistemic/partition.py`:

    REGION_KIND, REGION_KIND_BY_CODE, CANDIDATE_KINDS
    _component_labels, _distance_to_target, _touches_edge, _centroid_angles,
    _angular_distance_deg, _region_interfaces
    build_epistemic_partition

`benchmark.py` keeps compatibility identities, the Phase-6 orchestration and the
dense-truth evaluation. Phases 7, 8 and 8b import the conceptual partition directly.
Core 11 migrates the accepted representation intact, including `CANDIDATE_KINDS`, the
candidate flag and `reconstruction_status`. Separating representation from candidate,
benchmark and attention policy is deferred to a later Core.

## Decision-critical open items

1. Core 11 is structural only: no representation or policy redesign, and no dataclasses,
   enums or new validation.
2. Do not modify `fov3d/epistemic/__init__.py`. A bare `import fov3d.epistemic` must stay
   lightweight, with no OpenCV and no `partition`.
3. Replays are decided by a fresh import audit. The Phase-8 proposer is authorized if the
   audit reaches it.
4. The following remain deferred:
   - separating representation from policy;
   - the `_own_labels`/`own_support_labels` and `component_lineage`/`_lineage` cleanup;
   - the `attach_state_region_codes` rename;
   - the consumerless aliases;
   - the target-relative `HeadEvidence` placement;
   - the Phase-2 and Phase-3 boundary lineages.
