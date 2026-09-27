# Chat Handoff

## Accepted main

    main @ 518ff6ce4686238301f5ac946a5ea049e27ed9da

Accepted milestone: Conceptual Core 9.

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

The sealed scientific behavior is unchanged through Conceptual Cores 1–9.

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
- `fov3d.scene.corridors` (Core 6)
  - `_component_boundary`
  - `_line_cells`
  - `gap_corridor`
  - `corridors_for_object`
- `fov3d.scene.lineage` (Core 7)
  - `_lineage`
  - `_target_component_raster`
- `fov3d.scene.state_validation` (Core 8)
  - `attach_state_region_codes`, which keeps its compatibility name; the rename is
    deferred
- `fov3d.scene.relations` (Core 9)
  - `_region_object`
  - `_weighted_quantile`
  - `boundary_depth_order`

  The Phase-4 adapter `fov3d/experiments/classroom_partition/relations.py` keeps identity
  imports of all three; `annotate_corridor` resolves the scene function.

`fov3d.scene` lazily re-exports the four scene-partition names, so a bare
`import fov3d.scene` stays OpenCV-free. The modules `boundaries`, `corridors`, `lineage`,
`state_validation` and `relations` are imported explicitly and are not in
`fov3d.scene.__all__`. `boundaries`, `lineage`, `state_validation` and `relations` are
NumPy-only; `corridors` needs `cv2`.

Conceptual Core 9 was accepted at `518ff6ce4686238301f5ac946a5ea049e27ed9da` with:

    CONCEPTUAL_CORE9_RELATIONS_PRESERVE_BEHAVIOR

The preservation evidence, from `docs/migration-conceptual-core-9-report.md`, includes:
- the three moved definitions are source-text and AST identical to their previous
  implementation, with equivalent global bindings;
- the Core-9 checker passes 24/24; it caught 38/38 non-equivalent behavioral mutants and
  9/9 static/identity mutants;
- the Phase-4 relation product is 211/211 byte-identical, from 484 executions of
  `boundary_depth_order`;
- the sealed baseline is 31/31 and the golden comparison reports `MISMATCHES 0`;
- the import audit showed that only Phase 4 is reached, so no other phase was replayed.

## Active next step

Conceptual Core 10: the corridor relation-origin primitive
(`docs/migration-conceptual-core-10.md`).

Causal question: can the generic corridor relation-origin primitive be moved from the
Classroom Phase-4 adapter into the generic scene corridor layer without changing any
behavior?

Bounded target, moved literally from `fov3d/experiments/classroom_partition/relations.py`
to **`fov3d.scene.corridors`**, not `fov3d.scene.relations`:

    _region_code
    _own_labels
    _joint_region_own_component
    relation_origin

The reason for that destination is that `_own_labels` uses `cv2.connectedComponents`, and
`fov3d.scene.corridors` already carries the accepted OpenCV dependency. This keeps
`fov3d.scene.relations` NumPy-only. The classification strings `ownership_cut` and
`own_support_gap` are descriptive scene structure, not policy.

## Decision-critical open items

1. Core 10 is structural only. `own_support_labels` is **not** unified with
   `_own_labels`, and `component_lineage` is **not** unified with
   `fov3d.scene.lineage._lineage`; each is a separate future causal question.
2. Do not modify `fov3d/scene/__init__.py`; the bare import must stay OpenCV-free.
3. Replays are decided by a fresh import audit at the Core-10 head. The Phase-8 proposer
   runs only if it is reached.
4. The following remain deferred:
   - the `attach_state_region_codes` rename;
   - the consumerless compatibility aliases;
   - the separate Phase-2 and Phase-3 boundary lineages;
   - the target-relative `HeadEvidence` placement;
   - whether stricter one-region-per-code validation is wanted.
