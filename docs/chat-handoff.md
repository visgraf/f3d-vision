# Chat Handoff

## Accepted main

    main @ 502439f689ca55c9c50aa2be851415f4568037bb

Accepted milestone: Conceptual Core 3.

## Accepted scientific / architectural state

The current sealed scientific behavior remains unchanged through Conceptual Cores 1-3.

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

Conceptual Core 3 is accepted with:

    CONCEPTUAL_CORE3_HEAD_MEMORY_PRESERVES_BEHAVIOR

Measured acceptance evidence includes:

- Core-3 checker 27/27
- Core-2 checker 20/20
- Core-1 checker 13/13
- Partition-Graph checkers 1-8b all pass
- sealed baseline 31/31
- golden comparison MISMATCHES 0
- byte-identical producer scopes for Phases 4, 5, 7, 8, and 8b
- byte-identical evaluator scopes for Phases 7, 8, and 8b
- accepted reference trees unchanged

`FineEvidence` and `add_patch_observation` remain historical Phase-4 adapters in
`relations.py`. `ObservationFootprint` and `ObservationOverlay` remain scene concepts.

## Active next step

Conceptual Core 4: scene partition construction.

The bounded target is to move generic support rasterization and joint
ownership/region construction out of the historical
`fov3d/experiments/classroom_partition/joint.py` lineage and behind the scene
representation API, without changing scientific/runtime behavior.

Likely reusable concepts include:

- `support_depth_from_map`
- frontmost joint ownership/depth construction
- connected scene-region construction

The exact extraction boundary must be determined from the live repository before
implementation.

## Decision-critical open items

1. Core 4 must remain a structural migration: no new partition semantics, topology,
   benchmark policy, gaze policy, matcher/fusion/controller behavior, or scene behavior.
2. Keep `FineEvidence`, topology/relations, benchmark policy, and the unresolved
   target-relative HeadEvidence representation question outside Core 4.
3. Preserve the accepted Phase-3 reference lineage:
   `previews/partition-graph-4-lift`, not the historically stale
   `partition-graph-3-full`.
4. If Core 4 changes a path used by Phase 8, the approximately 11-minute Phase-8 replay
   must be run explicitly.
5. Carried Core-2 cleanup items remain deferred unless Core 4 directly requires them:
   compatibility aliases, the demo-side 0.012 literal, sealed-runtime association twin,
   and accepted-reference registry.
