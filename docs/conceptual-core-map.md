# Conceptual core migration map

Status: Conceptual Cores 1-13 were verified and accepted. Conceptual Core 14, the third
intentional redesign Core, is now proposed (measured) on `migration/conceptual-core-14`; its
measured acceptance status belongs in `docs/migration-conceptual-core-14-report.md`.

The purpose of this map is to distinguish stable system concepts from the
Classroom/Partition-Graph experiment lineage. It is intentionally architectural, not
chronological.

Classification vocabulary (from the contract): **G** reusable scene/geometry
representation, **M** persistent measurement/reconstruction memory, **P** spherical
partition construction, **T** topology / relations, **E** epistemic / observation state,
**B** benchmark construction, **V** evaluation-only logic, **C** Classroom-specific
saved-run adaptation, **H** historical phase scaffolding.

| module | class | present role | eventually reusable | should remain experiment-specific | current coupling signal |
|---|---|---|---|---|---|
| `__init__.py` | C | re-exports `lift_run` for the Phase-2 tools/checker | none by itself | package identity | package remains the home of experiment adapters/benchmarks |
| `lift.py` | G, P, C | lifts saved Classroom prefixes into spherical scene/observation structures | observation footprint construction, visibility overlay mechanics (the chart transforms moved to `fov3d.geometry.head_chart` in Core 2) | saved-run paths, manifest/calibration replay, Classroom prefix traversal | since Core 2 it keeps only compatibility aliases (`_grid`, `_cells`, `_head_angles_from_unit`, `_head_unit_from_angles`, `FUSION_RADIUS_M`) that no in-repo production code or existing tool imports; `ReadLog` is imported by `joint`, `relations` and `incidental`, and private `_camera_polygon` by `joint` |
| `joint.py` | P, T, C | Phase-3 composition of reusable scene partition + boundary extraction with controller `seen_any` replay, corridors and lineage | after Core 6, support/ownership/regions live in `fov3d.scene.partition`, cell-side boundary enumeration/tracing in `fov3d.scene.boundaries`, the local gap-corridor measurement (`_component_boundary`, `_line_cells`, `gap_corridor`, `corridors_for_object`) in `fov3d.scene.corridors`, target-component lineage (`_lineage`, `_target_component_raster`) in `fov3d.scene.lineage` (Core 7), and the graph/raster state-code consistency check `attach_state_region_codes` in `fov3d.scene.state_validation` (Core 8; the historically misleading name — it validates and attaches nothing — is deliberately preserved during the behavior migration, and a rename is deferred) | reconstruction of a particular saved Classroom prefix; controller `seen_any` replay (lazy `fov3d.stereo.core` import); `lift_joint_run` keeps `previous_target_labels` and calls the scene lineage functions, and passes the replayed evidence to the corridor measurement as an explicit `seen_any` argument | keeps compatibility imports for the extracted scene APIs: the Core-4 partition names are used by its own `build_joint_graph`/`lift_joint_run` and by the unmodified `tools/dev/check_partition_graph{3,4,5,8}.py`; of the Core-5 boundary names only `extract_boundaries` is used (by `build_joint_graph`), while `_interface_edges`/`_trace_edge_components` are contract-mandated aliases with no in-repo consumer besides the Core-5 identity check; the Core-6 corridor names are used by `lift_joint_run` (`corridors_for_object`) and checkers 3 and 4, while `gap_corridor`, `_line_cells` and `_component_boundary` are contract-mandated aliases with no in-repo consumer besides the Core-6 identity check; the Core-7 lineage names are used by `lift_joint_run` (both) and by checker 4 (`_lineage`); `joint.py` keeps only a compatibility import of `attach_state_region_codes`, used by `lift_joint_run` and by the unmodified checker 3; still imports `ReadLog` and private `_camera_polygon` from lift; `build_joint_graph` remains experiment-side and used by Phase 8b |
| `relations.py` | T, E, H | derives ownership cuts, own-support gaps and relation descriptors; Phase-4 left-eye evidence replay (`FineEvidence`) | topological/geometric relation extraction between scene regions/components | Phase-specific diagnostics and report fields; left-eye `FineEvidence`, superseded by head-centred `HeadEvidence` in Phase 5 | imports private `joint` helpers (`_default_stereo_ops`, `_rectified_core_directions_h`) and, since Core 4, `support_depth_from_map` from `fov3d.scene`; since Core 9 the generic boundary depth-order primitive (`boundary_depth_order` with `_region_object`, `_weighted_quantile`) lives in the NumPy-only `fov3d.scene.relations`, and since Core 10 the corridor relation-origin cluster (`relation_origin` with `_region_code`, `_own_labels`, `_joint_region_own_component`) lives in the OpenCV-dependent `fov3d.scene.corridors` beside the gap-corridor geometry; both are imported back as identity names used by `annotate_corridor` (ownership margins, evidence classification, `FineEvidence`, `annotate_corridor`, `component_lineage` and `own_support_labels` stay here); no later module imports it, and Phase 5 consumes its output only as saved `relations.json` |
| `incidental.py` | E, H | Phase-5 head-evidence analysis and relation annotation | none after Core 3; `HeadEvidence` / `add_head_patch` move to `fov3d.epistemic.head_memory` | Phase-5 report classifications and saved-prefix analysis | Core 3 keeps compatibility names by importing the conceptual definitions; they are used by its own `analyze_phase5`/`annotate_head_relation` and by the unmodified `tools/dev/check_partition_graph{5,7,8}.py`; Phases 7, 8 and 8b import the conceptual module directly; still imports `ReadLog` from lift, and since Core 4 takes `support_depth_from_map` from `fov3d.scene`; it is the only production reader of the target-relative fields `target_depth_seen`/`other_depth_seen` |
| `benchmark.py` | B, V, C | Phase-6 proposal orchestration over the explicit historical candidate view, truth firewall and Phase-6 evaluation | none left after Core 11: the epistemic-region vocabulary (`REGION_KIND`, `REGION_KIND_BY_CODE`) and the partition constructor (`build_epistemic_partition` with `_component_labels`, `_distance_to_target`, `_touches_edge`, `_centroid_angles`, `_angular_distance_deg`, `_region_interfaces`) live in `fov3d.epistemic.partition`; since Core 12 the candidate rule `CANDIDATE_KINDS` lives in `candidate_policy` | saved-run paths and the truth firewall (`_guard_source_path`), `propose_phase6`/`evaluate_phase6`, `_covered`, `_miss_components`, JSON I/O | since Core 12 keeps the historical API: the eight representation names are identity imports from `fov3d.epistemic.partition`, `CANDIDATE_KINDS` and `build_candidate_partition` come from `candidate_policy`, and `build_epistemic_partition` is a compatibility alias of `build_candidate_partition` (the accepted candidate view) for the unmodified `tools/dev/check_partition_graph{6,7,8}.py`; `propose_phase6` calls `build_candidate_partition` explicitly; `tools/dev/check_partition_graph8b.py` and `tools/partition_graph{6,7,8b}_demo.py` still import `REGION_KIND`/`REGION_KIND_BY_CODE` through it; `CANDIDATE_KINDS` and the six helper names have no in-repo consumer through `benchmark` besides the Core-11/12 checks; keeps Core-2 aliases `_cells`/`_grid` (still used by `tools/partition_graph6_demo.py`) and `FUSION_RADIUS_M` (no remaining importer); its 12-mm `_covered` query is used by the Phase-8 proposer's novelty metric as well as by evaluators; the measured orphans `cv2`, `math` and `defaultdict` were dropped |
| `candidate_policy.py` | B, H | Core 12: the historical Phase-6/7/8 candidate interpretation of the epistemic partition (`CANDIDATE_KINDS = {OTHER_SURFACE, UNKNOWN}`, `annotate_candidate_partition`, `build_candidate_partition`) | the explicit representation/policy boundary may become a pattern for later policies; the rule itself is **not** an accepted universal attention policy | the historical candidate rule and the accepted Core-11 key positions of `candidate` (after `kind`) and `candidate_region_count` (after `region_count`) | since Core 13 composes on `run_context` (unchanged in Core 14), so the full historical stack is intrinsic partition → `gaze_context` → `run_context` → candidate annotation; imports only `run_context`; used by `benchmark`, `prefix_benchmark`, `integration` and `challenge_suite`; importing it loads the experiment package (`lift`), `run_context`, `gaze_context` and the intrinsic partition but no benchmark, evaluator, stereo or renderer module |
| `run_context.py` | C, H | Core 13: the historical run context of the partition — `annotate_reconstruction_status` adds `reconstruction_status` (`mapped_now` / `targeted_later` / `never_targeted`) right after `surface_source` from `mapped_cells` and the experiment's target schedule `all_target_ids`; `build_run_context_partition` keeps the historical builder signature | none as such: knowing which objects a prerecorded experiment will target later is not an epistemic quantity | the Classroom target schedule and the accepted status rule | since Core 14 composes on `gaze_context` (imports only `gaze_context`); used only by `candidate_policy`; the Phase-5 `incidental.reconstruction_status` helper is a separate, deferred duplicate |
| `gaze_context.py` | C, H | Core 14: the historical action-history context of the partition — `annotate_gaze_context` adds `min_distance_to_historical_gaze_deg` (smallest great-circle angle from the region centroid to the supplied gazes, `None` without gazes) right after `median_distance_to_target_deg`; `build_gaze_context_partition` keeps the historical Core-13 intrinsic signature (with `gazes_deg`) | the idea of relating regions to past fixations may later inspire a reusable observer-history mechanism, but the accepted semantics are target-local and are **not** a controller abstraction | the historical target-local gaze lists chosen by the producers (Phase 6 all target gazes, Phase 7/8 the current-target prefix, Phase 8b the retained prefix) | imports only `fov3d.epistemic.partition` (`build_epistemic_partition` and the generic helper `_angular_distance_deg`, which stays intrinsic); used only by `run_context` |
| `prefix_benchmark.py` | B, V, H | builds Phase-7 prefix benchmark views and metrics | small representation helpers may survive after audit | prefix scenarios, candidate capture metrics, evaluation/report aggregation | since Core 12 takes `REGION_KIND` and `REGION_KIND_BY_CODE` (both unused inside it) from `fov3d.epistemic.partition`, `build_candidate_partition` from `candidate_policy` and only `_covered` from `benchmark`; its orphan `CANDIDATE_KINDS` import was removed in Core 12; Phase 8 imports six names from it, five private (`_memory_state`, `_partition_signature`, `_region_lookup`, `_angles_to_codes`, `_candidate_capture_metrics`) |
| `integration.py` | B, V, H | Phase-8 causal instance-keyed integration proposer/evaluator | none left beyond `cross_target_novelty`; the measured-geometry memory and effective-geometry composition moved to `fov3d.reconstruction.measurement_memory` in Core 1 | Phase-7 parity, Phase-8 proposal tree, novelty metrics, evaluator | imports five private names from `prefix_benchmark`; since Core 12 takes `build_candidate_partition` from `candidate_policy` (both partition sites) and only `_covered` from `benchmark`; `tools/dev/check_partition_graph8.py` still imports `effective_target_geometry` through this module (a re-export) |
| `challenge_suite.py` | B, V | Phase-8b budget replay, UNKNOWN shells, eligibility floor and evaluation | no new core extraction in this step beyond using shared measurement memory | budgets, shells, eligibility, scenario construction, evaluation | since Core 1 it no longer duplicates routing or imports from `integration`; since Core 12 takes `REGION_KIND` and `_region_interfaces` from `fov3d.epistemic.partition`, the base integrated partition from `candidate_policy.build_candidate_partition` (its FULL parity against Phase 8 includes `candidate`) and only the private `_covered` from `benchmark`; it keeps its own, distinct `candidate_raw`/`eligible_candidate` interpretation (independent literal `{"UNKNOWN", "OTHER_SURFACE"}`, `MIN_ELIGIBLE_CELLS`, UNKNOWN shells), evidence that several candidate interpretations can exist over one epistemic representation; still imports `build_joint_graph` from `joint`; `HeadEvidence`/`add_head_patch` come from `fov3d.epistemic.head_memory` (Core 3) and `support_depth_from_map` from `fov3d.scene` (Core 4); chart and radius come from the conceptual modules since Core 2 |

## Concept extracted in Conceptual Core 1

The first extraction is deliberately narrow:

    saved measurement patch
        ↓
    valid finite positive-instance XYZ
        ↓
    route by observed instance identity
        ↓
    append-only measured-geometry memory
        + source global index
        + source active target id
        ↓
    instance snapshot
        ↓
    historical map XYZ + measured instance XYZ

This becomes:

    fov3d/reconstruction/measurement_memory.py

No fusion, deduplication, object discovery, semantic identity, confidence model, or
attention behavior is added.

## Proposed Conceptual Core 3 extraction

Core 3 is deliberately narrow:

    valid saved patch
        ↓
    fixed-head chart projection
        ↓
    persistent HeadEvidence
        ↓
    Phase-5 / Phase-7 / Phase-8 / Phase-8b experiment adapters

This becomes:

    fov3d/epistemic/head_memory.py

The target-neutral fields (depth/nearest identity/range/ambiguity/sample count) and the
historical target-relative fields (target_depth_seen/other_depth_seen) are preserved
exactly. FineEvidence remains a Phase-4 replay adapter in relations.py, and
ObservationFootprint/ObservationOverlay remain scene concepts.

## Conceptual Core 11 extraction (accepted)

Core 11 establishes ownership of the accepted epistemic-region representation only:

    HeadEvidence / causal Phase-5 state
        ↓
    fov3d.epistemic.partition
        (vocabulary, precedence, surface identity, per-kind connectivity,
         region rows and descriptors, cell-side interfaces)
        ↓
    Phase-6 / Phase-7 / Phase-8 / Phase-8b experiment adapters
        ↓
    later policy work

The representation is migrated intact, including the benchmark-flavoured fields that are
accepted behavior: `CANDIDATE_KINDS` and the `candidate` flag, `surface_source` and
`reconstruction_status` (`mapped_now` / `targeted_later` / `never_targeted`), and the
historical-gaze descriptor. Which of them belong to representation, benchmark annotation,
candidate generation or attention policy is **deferred**. `fov3d/epistemic/__init__.py` is
unchanged, so a bare `import fov3d.epistemic` stays OpenCV-free; the OpenCV-dependent module
is imported explicitly.

## Conceptual Core 12 separation (accepted)

The first intentional redesign Core separates one concept, candidate status, from the
intrinsic epistemic partition:

    accepted Core-11 partition = pure epistemic partition + historical candidate annotation

    causal evidence
        ↓
    fov3d.epistemic.partition            (candidate-free intrinsic representation)
        ↓
    classroom_partition.candidate_policy (historical OTHER_SURFACE / UNKNOWN → candidate)
        ↓
    candidate-annotated compatibility view
        ↓
    Phase 6 / 7 / 8 / 8b historical pipeline

`fov3d.epistemic.partition` no longer owns `CANDIDATE_KINDS`, `region["candidate"]` or
`diag["candidate_region_count"]`; its output is exactly accepted Core 11 minus those two fields,
and `candidate_policy` re-creates the accepted Core-11 view type- and key-order-strictly.
`benchmark.py` keeps the historical API; Phases 6, 7 and 8 use the explicit candidate view;
Phase 8b uses it for its base partition and keeps its distinct `candidate_raw` /
`eligible_candidate` interpretation. The representation/policy separation is now explicit.

## Conceptual Core 13 separation (accepted)

The second redesign Core separates the prerecorded experiment's run context from the intrinsic
partition:

    accepted Core-12 intrinsic partition = Core-13 intrinsic partition
                                         + historical reconstruction-status annotation

    causal evidence
        ↓
    fov3d.epistemic.partition            (kinds, identity, geometry, topology,
                                          evidence statistics, surface_source)
        ↓
    classroom_partition.run_context      (historical schedule → reconstruction_status)
        ↓
    classroom_partition.candidate_policy (historical candidate interpretation)
        ↓
    Phase 6 / 7 / 8 / 8b historical pipeline

The intrinsic `build_epistemic_partition` no longer takes `all_target_ids` and no longer emits
`reconstruction_status`; its output is exactly accepted Core 12 minus that field.
`surface_source` (`mapped` / `incidental` / `mapped_and_incidental`) stays intrinsic: it is
causal evidence provenance, determined by the current state alone. `run_context` re-creates the
accepted Core-12 rows exactly; `candidate_policy.build_candidate_partition` keeps its historical
signature and composes run context and candidate annotation. The historical producers,
`benchmark`'s compatibility API and Phase 8b's separate `candidate_raw` / `eligible_candidate`
interpretation are unchanged (Phase 8b still propagates `reconstruction_status` to refined rows).

## Proposed Conceptual Core 14 separation

The third redesign Core separates the observer's **action history** from the intrinsic partition:

    accepted Core-13 intrinsic partition = Core-14 intrinsic partition
                                         + historical gaze-context annotation

Evidence history (`seen_any_fraction`, `head_depth_fraction`, `mapped_cells`, `incidental_cells`,
`surface_source`) is accumulated in the state and stays intrinsic. The distance of a region to
previous fixations is derived from the action history and moves to the experiment-side
`gaze_context`. The intrinsic `build_epistemic_partition` no longer accepts `gazes_deg` and no
longer emits `min_distance_to_historical_gaze_deg`; its output is exactly accepted Core 13 minus
that field. `_angular_distance_deg` stays in `fov3d.epistemic.partition` as a generic helper.
`gaze_context` re-creates the accepted rows exactly; `run_context` composes on `gaze_context`;
`candidate_policy` composes on `run_context`. The historical producers keep their target-local
gaze selection and are unchanged; Phase 8b still receives the gaze field in its base partition and
still does not propagate it to refined rows.

Post-Core-14 architecture:

    intrinsic epistemic representation          fov3d.epistemic.partition
        → optional gaze / action context        classroom_partition.gaze_context
        → optional experiment run context       classroom_partition.run_context
        → candidate interpretation              classroom_partition.candidate_policy
        → future attention / controller policy  (not yet designed)

The intrinsic partition is now independent of the experiment's future target schedule, of the
candidate interpretation and of the fixation/action history. The next architectural activity,
pending acceptance, is the design of the integrated foveal controller over this boundary, not a
further historical cleanup migration.

## Proposed later extraction order

Subject to the measured results of Core 3, the likely next conceptual refactors are:

1. **Head-centered spherical chart + association constant (Conceptual Core 2; accepted)** —
   `fov3d.geometry.head_chart` and `fov3d.reconstruction.association`.
2. **Persistent head-centered epistemic memory (Conceptual Core 3; accepted)** —
   `fov3d.epistemic.head_memory` owns `HeadEvidence` / `add_head_patch`.
3. **Scene partition construction (Conceptual Core 4; accepted)** —
   `fov3d.scene.partition` owns support rasterization, frontmost ownership/depth and
   connected scene regions.
4. **Boundary extraction (Conceptual Core 5; accepted)** — move the accepted 4-neighbour
   interface enumeration and deterministic `BoundaryChain` tracing from `joint.py` to
   `fov3d.scene.boundaries`, without unifying the separate Phase-2 boundary lineage.
5. **Gap-corridor topology (Conceptual Core 6; accepted)** — move the local straight
   gap-corridor measurement from `joint.py` to `fov3d.scene.corridors`, keeping `seen_any`
   an explicit argument and leaving Phase-4 relation classification in `relations.py`.
6. **Target-component lineage (Conceptual Core 7; accepted)** — move `_lineage` and
   `_target_component_raster` from `joint.py` to `fov3d.scene.lineage`, retiring the
   historical Phase-4 lineage patch tool; `relations.component_lineage` stays separate.
7. **Graph/raster state-code consistency (Conceptual Core 8; accepted)** — move
   `attach_state_region_codes` literally from `joint.py` to `fov3d.scene.state_validation`,
   keeping its name, set semantics and `graph.validate()` ordering; a rename is deferred.
8. **Topology / relations** — the next larger conceptual boundary: make relation extraction
   operate on the generic scene graph rather than Phase-numbered state products. First step,
   **Conceptual Core 9 (accepted)**: the generic boundary depth-order primitive
   (`boundary_depth_order`, `_region_object`, `_weighted_quantile`) moved literally to the
   NumPy-only `fov3d.scene.relations`. Second step, **Conceptual Core 10 (accepted)**: the
   corridor relation-origin cluster (`relation_origin`, `_region_code`, `_own_labels`,
   `_joint_region_own_component`) moves literally to `fov3d.scene.corridors`, which already
   owns the OpenCV-dependent gap-corridor geometry, so `fov3d.scene.relations` stays
   NumPy-only. The rest of the Phase-4 relations adapter stays experiment-side.
9. **Epistemic partition versus benchmark policy** — separate reusable uncertainty/state
   representation from candidate/evaluation machinery in `benchmark.py` and
   `prefix_benchmark.py`. First step, **Conceptual Core 11 (accepted)**: the accepted
   epistemic-region vocabulary and partition constructor moved intact from `benchmark.py`
   to `fov3d.epistemic.partition`, with `benchmark.py` keeping identity compatibility names
   and Phases 7, 8 and 8b importing the conceptual module directly. Second step,
   **Conceptual Core 12 (accepted)**: candidate status leaves the intrinsic partition and
   becomes the experiment-side historical interpretation `candidate_policy`, which the
   historical pipeline uses explicitly. Third step, **Conceptual Core 13 (accepted)**:
   `reconstruction_status` and the `all_target_ids` dependency leave the intrinsic partition
   and become the experiment-side run context `run_context`, while `surface_source` stays
   intrinsic. Fourth step, **Conceptual Core 14 (proposed)**: the action-history gaze context
   (`gazes_deg`, `min_distance_to_historical_gaze_deg`) leaves the intrinsic partition and
   becomes the experiment-side `gaze_context`. Next: integrated foveal-controller design over
   the clean representation boundary.

The later order remains a proposal, not permission to perform those migrations in Core 3.
