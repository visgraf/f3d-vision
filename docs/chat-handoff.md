# Chat Handoff

## Accepted main

    main @ d324e098c859a3b7ea1e91c7526f5cda854bcaf7

Accepted milestone: Conceptual Core 11.

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
  Core. Core 12 is the first intentional redesign Core: the simplest falsifiable change,
  preserving accepted observable behavior and separating one concept at a time.

## Accepted scientific / architectural state

The sealed scientific behavior is unchanged through Conceptual Cores 1–11.

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
- `fov3d.epistemic.partition` (Core 11)
  - the accepted epistemic partition representation: `REGION_KIND`, `REGION_KIND_BY_CODE`,
    `CANDIDATE_KINDS`, `_component_labels`, `_distance_to_target`, `_touches_edge`,
    `_centroid_angles`, `_angular_distance_deg`, `_region_interfaces`,
    `build_epistemic_partition`
  - imported explicitly and OpenCV-dependent; `fov3d/epistemic/__init__.py` is unchanged,
    so a bare `import fov3d.epistemic` stays OpenCV-free

The Phase-4 adapter `fov3d/experiments/classroom_partition/relations.py` keeps identity
imports of the Core-9 and Core-10 names; `annotate_corridor` resolves the scene functions.
`fov3d/experiments/classroom_partition/benchmark.py` keeps identity imports of the ten
Core-11 names for historical tools; Phases 7, 8 and 8b import `fov3d.epistemic.partition`
directly and take only `_covered` from `benchmark`.

`fov3d.scene` lazily re-exports the four scene-partition names, so a bare
`import fov3d.scene` stays OpenCV-free. The modules `boundaries`, `corridors`, `lineage`,
`state_validation` and `relations` are imported explicitly. `corridors` needs `cv2`; the
others are NumPy-only.

Conceptual Core 11 was accepted at `d324e098c859a3b7ea1e91c7526f5cda854bcaf7` with:

    CONCEPTUAL_CORE11_EPISTEMIC_PARTITION_PRESERVES_BEHAVIOR

The evidence, from `docs/migration-conceptual-core-11-report.md`, includes:
- the ten moved definitions are source-text and AST identical to accepted Core 10, with
  equivalent global bindings;
- the Core-11 checker passes 59/59; it caught 113/113 non-equivalent behavioral mutants
  and 21/21 static mutants;
- all 8 Phase-6/7/8/8b producer/evaluator replays are byte-identical, including the
  approximately 11-minute Phase-8 proposer;
- the sealed baseline is 31/31 and the golden comparison reports `MISMATCHES 0`;
- the 13 accepted reference trees are unchanged.

Core 11 deliberately retained, for compatibility, the benchmark-flavoured annotations inside
the epistemic partition: the candidate annotation (`CANDIDATE_KINDS`, `region["candidate"]`,
`diag["candidate_region_count"]`), the run status (`surface_source`,
`reconstruction_status` with `mapped_now`/`targeted_later`/`never_targeted`) and the
historical-gaze descriptor (`min_distance_to_historical_gaze_deg`).

Earlier accepted Cores (1–10) are summarised in their reports. The cleanup of
`own_support_labels` versus `_own_labels`, and of `component_lineage` versus
`fov3d.scene.lineage._lineage`, remains **deferred**.

## Active next step

Conceptual Core 12, the first redesign step: **epistemic partition ≠ candidate
interpretation** (`docs/migration-conceptual-core-12.md`, branch
`migration/conceptual-core-12`).

Causal question: can candidate status be removed from the intrinsic epistemic partition and
expressed instead as a separate historical candidate interpretation, while reproducing
every accepted Phase-6/7/8/8b observable product exactly?

    accepted Core-11 partition = pure epistemic partition + historical candidate annotation

- `fov3d.epistemic.partition` stops owning `CANDIDATE_KINDS`, `region["candidate"]` and
  `diag["candidate_region_count"]`; every other Core-11 semantic stays unchanged.
- The new experiment-side `fov3d/experiments/classroom_partition/candidate_policy.py` owns
  the historical `OTHER_SURFACE`/`UNKNOWN` → candidate rule and re-creates the accepted
  Core-11 candidate view exactly (values, types and key order).
- `benchmark.py` keeps the historical API; Phases 6, 7, 8 and 8b use the explicit candidate
  view; Phase 8b keeps its own distinct `candidate_raw`/`eligible_candidate`
  interpretation.

## Decision-critical open items

1. The central Core-12 invariant is measured against accepted Core 11 (`d324e09`): the pure
   output is Core 11 minus exactly the two candidate fields, and re-annotation restores
   Core 11 type- and key-order-strictly.
2. The accepted Core-11 checker asserts the old structure. It stays unmodified as historical
   evidence and is verified at `d324e09`; the Core-12 checker supersedes it at the current
   head. Core-1–10 conceptual checkers and Partition-Graph checkers 1–8b stay current-head
   gates, unmodified.
3. Do not modify `fov3d/epistemic/__init__.py`, and do not create a generic attention
   package: the historical rule is not an accepted universal attention policy.
4. Deferred to Core 13 and later:
   - the historical/context annotations `reconstruction_status`
     (`mapped_now`/`targeted_later`/`never_targeted`) and
     `min_distance_to_historical_gaze_deg`;
   - the target-relative `HeadEvidence` placement;
   - the `_own_labels`/`own_support_labels` and `component_lineage`/`_lineage` cleanup;
   - the `attach_state_region_codes` rename;
   - the consumerless aliases;
   - the Phase-2 and Phase-3 boundary lineages.
