# Chat Handoff

## Accepted main

    main @ 872ac45405c796a0e8b0cd4455bd17c12c7542db

Accepted milestone: Conceptual Core 12.

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
  Core. Core 12 was the first intentional redesign Core and Core 13 is the second: the
  simplest falsifiable redesign, preserving every accepted historical observable and
  separating one concept at a time.

## Accepted scientific / architectural state

The sealed scientific behavior is unchanged through Conceptual Cores 1–12.

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
  - imported explicitly and OpenCV-dependent; `fov3d/epistemic/__init__.py` is unchanged,
    so a bare `import fov3d.epistemic` stays OpenCV-free
- `fov3d/experiments/classroom_partition/candidate_policy.py` (Core 12, experiment-side)
  - the historical `OTHER_SURFACE`/`UNKNOWN` → candidate interpretation:
    `CANDIDATE_KINDS`, `annotate_candidate_partition`, `build_candidate_partition`, which
    re-creates the accepted candidate view exactly

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

Conceptual Core 12 was accepted at `872ac45405c796a0e8b0cd4455bd17c12c7542db` with:

    CONCEPTUAL_CORE12_CANDIDATE_POLICY_SEPARATION_PRESERVES_BEHAVIOR

The evidence, from `docs/migration-conceptual-core-12-report.md`, includes:
- the central Core-12 invariant succeeded: the intrinsic output is accepted Core 11 minus
  only the two candidate fields, and `candidate_policy` re-creates Core 11 type- and
  key-order-strictly;
- the Core-12 checker passes 70/70; it caught 51/51 dynamic and 25/25 static mutants;
- the random-state differential agreed on 10,000/10,000 states;
- all 8 Phase-6/7/8/8b producer/evaluator replays are byte-identical;
- the sealed baseline is 31/31 and the golden comparison reports `MISMATCHES 0`;
- the 13 accepted reference trees are unchanged;
- Phase 8b's `candidate_raw`/`eligible_candidate` interpretation remains independent.

The intrinsic partition still carries the run status `reconstruction_status`
(`mapped_now`/`targeted_later`/`never_targeted`, which needs the experiment's target
schedule `all_target_ids`) and the historical-gaze descriptor
(`min_distance_to_historical_gaze_deg`). `surface_source` is causal evidence provenance.

Earlier accepted Cores (1–11) are summarised in their reports. The cleanup of
`own_support_labels` versus `_own_labels`, and of `component_lineage` versus
`fov3d.scene.lineage._lineage`, remains **deferred**.

## Active next step

Conceptual Core 13, the second redesign step (`docs/migration-conceptual-core-13.md`, branch
`migration/conceptual-core-13`).

Causal question: can `reconstruction_status` and the dependency on `all_target_ids` be
removed from the intrinsic epistemic partition and expressed instead as an experiment-side
run-context annotation, while reproducing every accepted Core-12 historical product exactly?

    accepted Core-12 intrinsic partition = Core-13 intrinsic partition
                                         + historical reconstruction-status annotation

- `surface_source` is causal evidence provenance and **stays intrinsic**, together with
  `mapped_cells` and `incidental_cells`.
- `reconstruction_status` is historical run context (`targeted_later`/`never_targeted`
  need the prerecorded target schedule) and moves to the new experiment-side
  `fov3d/experiments/classroom_partition/run_context.py`.
- `candidate_policy.build_candidate_partition` keeps its historical signature and composes
  intrinsic partition → run context → candidate annotation.

## Decision-critical open items

1. The central Core-13 invariant is measured against accepted Core 12 (`872ac45`).
2. The accepted Core-12 checker asserts the Core-12 structure. It stays unmodified and is
   verified at `872ac45`; the Core-13 checker supersedes it at the current head.
   Core-1–10 conceptual checkers and Partition-Graph checkers 1–8b stay current-head gates,
   unmodified.
3. Do not modify `fov3d/epistemic/__init__.py`; do not introduce a general controller
   package; do not alter Phase-8b candidate semantics.
4. Deferred to Core 14 and later:
   - `min_distance_to_historical_gaze_deg` and the `gazes_deg` input to the intrinsic
     partition;
   - broader observer/attention-history representation;
   - the target-relative `HeadEvidence` placement;
   - the Phase-5 `reconstruction_status` duplication;
   - the `_own_labels`/`own_support_labels` and `component_lineage`/`_lineage` cleanup;
   - the `attach_state_region_codes` rename;
   - the consumerless aliases;
   - the Phase-2 and Phase-3 boundary lineages.
