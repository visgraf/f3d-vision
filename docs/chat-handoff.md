# Chat Handoff

## Accepted main

    main @ 3877857c3a355851413cdfaa55c5dd05ad8bdab4

Accepted milestone: Conceptual Core 8.

## Working arrangement

Chat reads, designs and reviews only; it does not mutate GitHub or the workstation
checkout. Claude Code performs every repository mutation and every measured execution in
dedicated isolated git worktrees, never by switching branches in the shared
`/home/lvelho/rd/f3d-vision` checkout. Each measurement runs under a guard that
invalidates it if the branch, HEAD or tracked tree changes. GitHub is the source of truth.

## Accepted scientific / architectural state

The sealed scientific behavior is unchanged through Conceptual Cores 1–8.

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
  - `attach_state_region_codes`, which keeps its compatibility name. It validates the
    graph/raster state-code sets and attaches nothing; a rename is deferred.

`fov3d.scene` lazily re-exports the four scene-partition names, so a bare
`import fov3d.scene` stays OpenCV-free. The modules `boundaries`, `corridors`, `lineage`
and `state_validation` are imported explicitly and are not in `fov3d.scene.__all__`.
`boundaries`, `lineage` and `state_validation` are NumPy-only; `corridors` needs `cv2`.

Conceptual Core 8 was accepted at `3877857c3a355851413cdfaa55c5dd05ad8bdab4` with:

    CONCEPTUAL_CORE8_STATE_VALIDATION_PRESERVES_BEHAVIOR

The measured acceptance evidence, from `docs/migration-conceptual-core-8-report.md`,
includes:
- `attach_state_region_codes` is source-text and AST identical to its previous
  implementation, with identical global bindings;
- the checkers pass: Core-8 20/20 and Core-7 to Core-1, plus the unmodified
  Partition-Graph checkers 1–8b;
- the sealed baseline is 31/31 and the golden comparison reports `MISMATCHES 0`;
- the Phase 3, 4 and 8b producer scopes and the Phase-8b evaluator scope are
  byte-identical;
- the validator ran on all 104 map-present Phase-3 states (instrumented);
- the mutation checks caught 26/26 non-equivalent behavioral mutants and 6/6
  static/package mutants;
- the accepted duplicate-graph-code set semantics are locked;
- the import audit showed that Phases 5, 2, 6, 7 and 8 are not reached, so they were not
  run.

## Active next step

Conceptual Core 9: generic boundary depth-order relation primitive
(`docs/migration-conceptual-core-9.md`).

Bounded target, moved literally from `fov3d/experiments/classroom_partition/relations.py`
to `fov3d/scene/relations.py`:

    _region_object
    _weighted_quantile
    boundary_depth_order

The rest of `relations.py` stays experiment-side, including `FineEvidence`, the stereo
replay, `add_patch_observation`, evidence classification, `relation_origin`,
`ownership_margin_descriptor`, `annotate_corridor` and `component_lineage`.

## Decision-critical open items

1. Core 9 is structural only. Do not rename, re-annotate, validate or redesign; keep the
   quantile and relation semantics exactly.
2. Do not modify `fov3d/scene/__init__.py`. The new module must stay NumPy/scene-model
   only.
3. Later phases are replayed only if the import audit shows the Core-9 diff reaches them.
4. The following remain deferred:
   - the `attach_state_region_codes` rename;
   - the consumerless compatibility aliases (Cores 2, 5 and 6);
   - the separate Phase-2 and Phase-3 boundary lineages;
   - the target-relative `HeadEvidence` placement;
   - whether stricter one-region-per-code validation is scientifically wanted.
