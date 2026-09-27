# Chat Handoff

## Accepted main

    main @ 41a365c49cbec52a350139238753b087b8f29da0

Accepted milestone: Conceptual Core 6.

## Accepted scientific / architectural state

The sealed scientific behavior is unchanged through Conceptual Cores 1–6.

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

Conceptual Core 6 was accepted with:

    CONCEPTUAL_CORE6_GAP_CORRIDORS_PRESERVE_BEHAVIOR

Measured acceptance evidence from docs/migration-conceptual-core-6-report.md includes:
- Core-6 checker 35/35; Core-5 38/38; Core-4 32/32; Core-3 27/27; Core-2 20/20; Core-1 13/13;
- all Partition-Graph checkers pass, sealed baseline 31/31, golden MISMATCHES 0;
- Phase 3/4/5/8b producer scopes and the Phase-8b evaluator scope are byte-identical;
- 41/41 non-equivalent behavioral mutants and 8/8 static/package mutants are caught;
- 570 corridor records and accepted aggregates are reproduced exactly;
- bare import fov3d.scene remains lightweight and OpenCV-free.

The Phase-2 boundary lineage, Phase-4 relation classification, FineEvidence, lineage,
controller-evidence replay, benchmark/evaluator policy, and target-relative HeadEvidence
placement remain outside Core 6.

## Active next step

Conceptual Core 7: target-component lineage.

Bounded target:

    _lineage
    _target_component_raster

Move these two NumPy/ScenePartitionGraph helpers out of
`fov3d/experiments/classroom_partition/joint.py` into a scene-level lineage module,
preserving exact behavior.

Before extraction, explicitly retire the historical one-shot tool
`tools/dev/apply_partition_graph4_lineage_fix.py`, whose sole purpose was to patch the
pre-fix `_lineage` source in joint.py. It is no longer an active repair mechanism once the
accepted fixed implementation becomes conceptual code.

## Decision-critical open items

1. Core 7 is structural only: do not change lineage semantics, component-label encoding,
   region ordering, partition construction, relation classification, controller replay,
   benchmark/evaluator policy, or runtime scientific behavior.
2. Retire the historical Phase-4 lineage patch tool explicitly rather than leaving a
   source-replacement utility that points at a function no longer owned by joint.py.
3. Keep controller seen_any replay, corridors, boundaries, partition construction and
   lift/report traversal in their current layers.
4. Preserve bare fov3d.scene import behavior; do not eagerly export a new lineage module.
5. Preserve the accepted Phase-3 reference lineage: previews/partition-graph-4-lift.
6. Earlier compatibility aliases and target-relative HeadEvidence placement remain
   deferred unless Core 7 directly requires them.
