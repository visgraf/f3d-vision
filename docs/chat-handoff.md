# Chat Handoff

## Accepted main

    main @ 3603266b299236359f0539a778ac98f65cd11887

Accepted milestone: Conceptual Core 7.

## Working arrangement

Chat reads, designs and reviews only; it no longer mutates GitHub or the workstation
checkout. Claude Code performs every repository mutation and every measured execution in
dedicated isolated git worktrees, never by switching branches in the shared
`/home/lvelho/rd/f3d-vision` checkout. Each measurement runs under a guard that
invalidates it if the branch, HEAD or tracked tree changes. GitHub is the source of truth.

## Accepted scientific / architectural state

The sealed scientific behavior is unchanged through Conceptual Cores 1–7.

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

`fov3d.scene` lazily re-exports the four scene-partition names, so a bare
`import fov3d.scene` stays OpenCV-free. Accessing the construction API loads
`fov3d.scene.partition` on demand. `fov3d.scene.boundaries`, `fov3d.scene.corridors` and
`fov3d.scene.lineage` are imported explicitly and are not in `fov3d.scene.__all__`.
`boundaries` and `lineage` are NumPy-only; `corridors` needs `cv2`.

Conceptual Core 7 was accepted at `3603266b299236359f0539a778ac98f65cd11887` with:

    CONCEPTUAL_CORE7_LINEAGE_PRESERVES_BEHAVIOR

The measured acceptance evidence, from `docs/migration-conceptual-core-7-report.md`,
includes:
- `_lineage` and `_target_component_raster` are source-text identical to their previous
  implementation, with identical global bindings;
- the checkers pass: Core-7 22/22, Core-6 35/35, Core-5 38/38, Core-4 32/32, Core-3 27/27,
  Core-2 20/20, Core-1 13/13, and Partition-Graph 1–8b;
- the sealed baseline is 31/31 and the golden comparison reports `MISMATCHES 0`;
- the Phase 3, 4, 5 and 8b producer scopes and the Phase-8b evaluator scope are
  byte-identical;
- the 104 Phase-3 lineage records and the accepted totals
  `{births 10, merges 3, splits 0, deaths 1}` are reproduced exactly;
- the mutation checks caught 29/29 non-equivalent behavioral mutants and 11/11
  static/package/tool mutants;
- a bare `import fov3d.scene` stays lightweight and OpenCV-free.

The historical one-shot tool `tools/dev/apply_partition_graph4_lineage_fix.py` is
**retired**. It is now a non-mutating tombstone that prints
`[partition-graph4-lineage-fix] RETIRED` and exits 0. The original repair script remains
in Git history (`52c9395`).

The following stay outside Core 7:
- `relations.component_lineage` and the Phase-4 relation classification;
- `FineEvidence`;
- the controller `seen_any` replay;
- benchmark and evaluator policy;
- the target-relative `HeadEvidence` placement.

## Active next step

Conceptual Core 8: graph/raster state-code consistency (`docs/migration-conceptual-core-8.md`).

Bounded target:

    attach_state_region_codes(graph, region_code) -> ScenePartitionGraph

The function moves literally from `fov3d/experiments/classroom_partition/joint.py` to
`fov3d/scene/state_validation.py`. The historical name is misleading, because the
function validates rather than attaches, but it is kept unchanged in Core 8; a rename is
deferred to a later compatibility cleanup.

## Decision-critical open items

1. Core 8 is structural only. Keep the exact set semantics, the `-1` sentinel, the error
   text, the ordering of the `graph.validate()` call and identity return. Duplicate
   graph codes stay accepted when the code sets match; do not "fix" that in Core 8.
2. Do not modify `fov3d/scene/__init__.py`; keep the bare `fov3d.scene` import
   lightweight.
3. Phase 5 and Phases 2, 6, 7 and 8 are conditional only, and run only if the import
   audit shows that the final Core-8 diff reaches them.
4. Topology/relations remains the next larger conceptual boundary and needs a
   Chat-designed contract.
5. The following remain deferred:
   - the consumerless compatibility aliases (Cores 2, 5 and 6);
   - the separate Phase-2 and Phase-3 boundary lineages;
   - the target-relative `HeadEvidence` placement;
   - the carried Core-2 cleanup items.
