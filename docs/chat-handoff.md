# Chat Handoff

## Accepted main

    main @ 643d21a729e1e80c238aa08649715c5dfc1c18dd

Accepted milestone: Conceptual Core 4.

## Accepted scientific / architectural state

The current sealed scientific behavior remains unchanged through Conceptual Cores 1-4.

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

The four scene-partition construction names are lazily re-exported through
`fov3d.scene`, so bare `import fov3d.scene` remains OpenCV-free while direct access to
the construction API loads `fov3d.scene.partition` on demand.

Conceptual Core 4 is accepted with:

    CONCEPTUAL_CORE4_SCENE_PARTITION_PRESERVES_BEHAVIOR

Measured acceptance evidence includes:

- Core-4 checker 32/32
- Core-3 checker 27/27
- Core-2 checker 20/20
- Core-1 checker 13/13
- Partition-Graph checkers 1-8b all pass
- sealed baseline 31/31
- golden comparison MISMATCHES 0
- all twelve Partition-Graph producer/evaluator replay scopes from Phase 2 through 8b
  byte-identical to accepted references after the lazy-export closure
- accepted reference trees unchanged

`FineEvidence`, `HeadEvidence`, boundary extraction, gap relations, lineage,
controller-evidence replay, and benchmark/evaluator policy remain outside the Core-4
extraction.

## Active next step

Conceptual Core 5: boundary extraction.

Bounded target:

    _interface_edges
    _trace_edge_components
    extract_boundaries

Move the reusable 4-neighbour interface enumeration and deterministic
`BoundaryChain` tracing out of
`fov3d/experiments/classroom_partition/joint.py` into a scene-level module, while
preserving exact behavior.

The exact Core-5 extraction boundary must be determined from the live repository before
implementation.

## Decision-critical open items

1. Core 5 remains a structural migration only. Do not change boundary semantics,
   topology, relation interpretation, partition construction, benchmark policy, gaze,
   controller, matcher, fusion, renderer, scene behavior, or termination.
2. Leave the distinct Phase-2 boundary construction in `lift.py` untouched; unification
   is a later question.
3. Leave `gap_corridor`, `corridors_for_object`, Phase-4 relation extraction,
   target-component lineage, and `seen_any` replay in the experiment layer.
4. Preserve the Core-4 lazy-export package boundary: any new scene module that depends on
   OpenCV must not make bare `import fov3d.scene` require OpenCV.
5. Preserve the accepted Phase-3 reference lineage:
   `previews/partition-graph-4-lift`.
6. Core-3 target-relative HeadEvidence placement and carried Core-2 cleanup items remain
   deferred unless Core 5 directly requires them.
