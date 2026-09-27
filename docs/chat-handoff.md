# Chat Handoff

## Accepted main

    main @ 6ff0da753acc8f20c84bf83e82c59db4f58de025

Accepted milestone: Conceptual Core 5.

## Accepted scientific / architectural state

The sealed scientific behavior is unchanged through Conceptual Cores 1–5.

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

`fov3d.scene` lazily re-exports the four scene-partition names, so a bare
`import fov3d.scene` stays OpenCV-free. Accessing the construction API loads
`fov3d.scene.partition` on demand. `fov3d.scene.boundaries` is imported explicitly; it is
not in `fov3d.scene.__all__` and is NumPy-only.

Conceptual Core 5 was accepted with:

    CONCEPTUAL_CORE5_BOUNDARY_EXTRACTION_PRESERVES_BEHAVIOR

The measured acceptance evidence, from `docs/migration-conceptual-core-5-report.md`,
includes:
- the three moved boundary functions are source-text identical to their previous
  implementation and have identical global bindings;
- the checkers pass: Core-5 38/38, Core-4 32/32, Core-3 27/27, Core-2 20/20,
  Core-1 13/13, and Partition-Graph 1–8b;
- the sealed baseline is 31/31 and the golden comparison reports `MISMATCHES 0`;
- the Phase-3 lift (vs `partition-graph-4-lift`), the Phase-4 and Phase-5 analyzers, and
  the Phase-8b proposer and evaluator are byte-identical to the accepted references;
- the import audit showed that Core 5 does not reach Phases 2, 6, 7 or 8, so no
  conditional gate was needed;
- the accepted reference trees are unchanged, and the bare `fov3d.scene` import
  footprint is unchanged.

`FineEvidence`, `HeadEvidence`, gap corridors, relation classification, lineage,
controller-evidence replay, the Phase-2 boundary construction, and benchmark/evaluator
policy stayed outside the Core-5 extraction.

## Active next step

Conceptual Core 6: gap-corridor topology (`docs/migration-conceptual-core-6.md`).

Bounded target:

    _component_boundary
    _line_cells
    gap_corridor
    corridors_for_object

The goal is to move the local gap-corridor measurement out of
`fov3d/experiments/classroom_partition/joint.py` into `fov3d.scene.corridors` without
changing behavior. `seen_any` stays an explicit argument, and the corridor module is not
coupled to controller replay.

## Decision-critical open items

1. Core 6 is a structural migration only. Do not change corridor semantics, relation
   classification, partition construction, boundaries, lineage, controller replay,
   benchmark policy, gaze, controller, matcher, fusion, renderer, scene behavior, or
   termination.
2. Keep the package boundary: `fov3d/scene/__init__.py` is not modified, and a bare
   `import fov3d.scene` must not load `cv2`, `fov3d.scene.partition`,
   `fov3d.scene.boundaries` or `fov3d.scene.corridors`.
3. Keep the accepted Phase-3 reference lineage, `previews/partition-graph-4-lift`.
4. The Phase-8 proposer (about 11 minutes) runs only if the import audit shows Core 6
   reaches it.
5. The following remain deferred:
   - the consumerless compatibility aliases (Core 2 and Core 5);
   - the separate Phase-2 and Phase-3 boundary lineages;
   - the Core-3 target-relative `HeadEvidence` placement;
   - the carried Core-2 cleanup items.
