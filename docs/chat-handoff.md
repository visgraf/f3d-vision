# Chat Handoff

## Accepted main

    main @ 3b7091ed7a8f58cfc84c552431bfe60dc694aad3

Accepted milestone: Conceptual Core 13.

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
  Core. Cores 12 and 13 were the first two intentional redesign Cores and Core 14 is the
  third: the simplest falsifiable redesign, preserving every accepted historical observable
  and separating one concept at a time.

## Accepted scientific / architectural state

The sealed scientific behavior is unchanged through Conceptual Cores 1–13.

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
- `fov3d.epistemic.partition` (Core 11; candidate-free since Core 12)
  - the intrinsic epistemic partition: `REGION_KIND`, `REGION_KIND_BY_CODE`,
    `_component_labels`, `_distance_to_target`, `_touches_edge`, `_centroid_angles`,
    `_angular_distance_deg`, `_region_interfaces`, `build_epistemic_partition`
  - since Core 12 it no longer owns candidate semantics (`CANDIDATE_KINDS`,
    `region["candidate"]`, `diag["candidate_region_count"]`)
  - since Core 13 it no longer depends on the experiment's target schedule
    (`all_target_ids`) nor emits `reconstruction_status`; `surface_source` stays intrinsic
    causal evidence provenance
  - imported explicitly and OpenCV-dependent; `fov3d/epistemic/__init__.py` is unchanged,
    so a bare `import fov3d.epistemic` stays OpenCV-free
- `fov3d/experiments/classroom_partition/candidate_policy.py` (Core 12, experiment-side)
  - the historical `OTHER_SURFACE`/`UNKNOWN` → candidate interpretation:
    `CANDIDATE_KINDS`, `annotate_candidate_partition`, `build_candidate_partition`, which
    re-creates the accepted candidate view exactly
  - since Core 13 it composes intrinsic → run context → candidate annotation
- `fov3d/experiments/classroom_partition/run_context.py` (Core 13, experiment-side)
  - the historical run context: `annotate_reconstruction_status`,
    `build_run_context_partition` (`mapped_now`/`targeted_later`/`never_targeted` from
    `mapped_cells` and `all_target_ids`)

The Phase-4 adapter `fov3d/experiments/classroom_partition/relations.py` keeps identity
imports of the Core-9 and Core-10 names; `annotate_corridor` resolves the scene functions.
`fov3d/experiments/classroom_partition/benchmark.py` keeps the historical API:
`benchmark.CANDIDATE_KINDS` is the policy constant and `benchmark.build_epistemic_partition`
is an alias of `build_candidate_partition`. Phases 6, 7, 8 and 8b call
`build_candidate_partition` explicitly; Phase 8b keeps its own, independent
`candidate_raw`/`eligible_candidate` interpretation.

`fov3d.scene` lazily re-exports the four scene-partition names, so a bare
`import fov3d.scene` stays OpenCV-free. The modules `boundaries`, `corridors`, `lineage`,
`state_validation` and `relations` are imported explicitly. `corridors` needs `cv2`; the
others are NumPy-only.

Conceptual Core 13 was accepted at `3b7091ed7a8f58cfc84c552431bfe60dc694aad3` with:

    CONCEPTUAL_CORE13_RECONSTRUCTION_STATUS_SEPARATION_PRESERVES_BEHAVIOR

The evidence, from `docs/migration-conceptual-core-13-report.md`, includes:
- the intrinsic `epistemic.partition` no longer depends on `all_target_ids`;
  `reconstruction_status` belongs to the experiment-side `run_context`, and `surface_source`
  remains intrinsic causal evidence provenance;
- `candidate_policy` composes intrinsic → run context → candidate, re-creating Core 12
  exactly;
- the Core-13 checker passes 65/65; it caught 50/50 dynamic and 20/20 static mutants;
- the random-state differential agreed on 10,000/10,000 states;
- all 8 Phase-6/7/8/8b products are byte-identical;
- the sealed baseline is 31/31 and the golden comparison reports `MISMATCHES 0`;
- the 13 accepted reference trees are unchanged.

The intrinsic partition still takes the action history `gazes_deg` (the current target's
historical gaze prefix) and emits `min_distance_to_historical_gaze_deg`.

Earlier accepted Cores (1–12) are summarised in their reports. The cleanup of
`own_support_labels` versus `_own_labels`, and of `component_lineage` versus
`fov3d.scene.lineage._lineage`, remains **deferred**.

## Active next step

Conceptual Core 14, the third redesign step (`docs/migration-conceptual-core-14.md`, branch
`migration/conceptual-core-14`).

Causal question: can action-history-derived gaze context (`gazes_deg` and
`min_distance_to_historical_gaze_deg`) be removed from the intrinsic epistemic partition and
reconstructed as a separate historical gaze-context annotation, while reproducing every
accepted Core-13 historical product exactly?

    accepted Core-13 intrinsic partition = Core-14 intrinsic partition
                                         + historical gaze-context annotation

- Evidence history stays intrinsic: `seen_any_fraction`, `head_depth_fraction`,
  `mapped_cells`, `incidental_cells`, `surface_source`.
- Action history (the region's distance to previous fixations) moves to the new
  experiment-side `fov3d/experiments/classroom_partition/gaze_context.py`; the accepted
  target-local gaze lists chosen by the historical producers are preserved exactly.
- The stack becomes intrinsic → gaze context → run context → candidate annotation.

**After Core 14, pending acceptance,** the intended next architectural activity is a fresh
design of the integrated foveal controller over the clean representation boundary, not an
automatic continuation of historical cleanup.

## Decision-critical open items

1. The central Core-14 invariant is measured against accepted Core 13 (`3b7091e`).
2. The accepted Core-13 checker stays unmodified and is verified at `3b7091e`; the Core-14
   checker supersedes it at the current head. Core-1–10 conceptual checkers and
   Partition-Graph checkers 1–8b stay current-head gates, unmodified.
3. Do not implement the controller in Core 14: no scoring, ranking, fixation choice,
   inhibition of return or recency model. Do not modify `fov3d/epistemic/__init__.py` or the
   Phase-8b candidate/refinement semantics (refined rows do not propagate the gaze field).
4. Deferred:
   - global versus target-local observer gaze history, inhibition of return, recency/decay;
   - real-controller candidate eligibility, ranking/scoring, fixation selection,
     vergence/focus action, integrated continuation/stopping;
   - the target-relative `HeadEvidence` placement;
   - the Phase-5 `reconstruction_status` duplication;
   - the `_own_labels`/`own_support_labels` and `component_lineage`/`_lineage` cleanup;
   - the `attach_state_region_codes` rename;
   - the consumerless aliases;
   - the Phase-2 and Phase-3 boundary lineages.
