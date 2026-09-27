# Conceptual core migration map

Status: Conceptual Cores 1-3 were verified and accepted. Conceptual Core 4 is now
proposed on `migration/conceptual-core-4`; its measured acceptance status belongs in
`docs/migration-conceptual-core-4-report.md`.

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
| `joint.py` | P, T, C | Phase-3 composition of the reusable scene partition with boundary extraction, controller `seen_any` replay, corridors and lineage | boundary extraction remains a later topology candidate; support rasterization, frontmost ownership/depth and connected scene regions move to `fov3d.scene.partition` in Core 4 | reconstruction of a particular saved Classroom prefix; controller `seen_any` replay (lazy `fov3d.stereo.core` import) | keeps compatibility imports for the extracted scene-partition API, used by its own `build_joint_graph`/`lift_joint_run` and by the unmodified `tools/dev/check_partition_graph{3,4,5,8}.py`; still imports `ReadLog` and private `_camera_polygon` from lift; `build_joint_graph` remains used by Phase 8b |
| `relations.py` | T, E, H | derives ownership cuts, own-support gaps and relation descriptors; Phase-4 left-eye evidence replay (`FineEvidence`) | topological/geometric relation extraction between scene regions/components | Phase-specific diagnostics and report fields; left-eye `FineEvidence`, superseded by head-centred `HeadEvidence` in Phase 5 | imports private `joint` helpers (`_default_stereo_ops`, `_rectified_core_directions_h`) and, since Core 4, `support_depth_from_map` from `fov3d.scene`; no later module imports it, and Phase 5 consumes its output only as saved `relations.json` |
| `incidental.py` | E, H | Phase-5 head-evidence analysis and relation annotation | none after Core 3; `HeadEvidence` / `add_head_patch` move to `fov3d.epistemic.head_memory` | Phase-5 report classifications and saved-prefix analysis | Core 3 keeps compatibility names by importing the conceptual definitions; they are used by its own `analyze_phase5`/`annotate_head_relation` and by the unmodified `tools/dev/check_partition_graph{5,7,8}.py`; Phases 7, 8 and 8b import the conceptual module directly; still imports `ReadLog` from lift, and since Core 4 takes `support_depth_from_map` from `fov3d.scene`; it is the only production reader of the target-relative fields `target_depth_seen`/`other_depth_seen` |
| `benchmark.py` | E, P, B, V | constructs the truth-free epistemic partition and performs Phase-6 evaluation support | epistemic region construction and region adjacency may become reusable | candidate definition, truth firewall, Phase-6 benchmark/evaluation statistics | representation and benchmark policy share one module; keeps Core-2 aliases `_cells`/`_grid` (still used by `tools/partition_graph6_demo.py`) and `FUSION_RADIUS_M` (no remaining importer); its 12-mm `_covered` query is used by the Phase-8 proposer's novelty metric as well as by evaluators |
| `prefix_benchmark.py` | B, V, H | builds Phase-7 prefix benchmark views and metrics | small representation helpers may survive after audit | prefix scenarios, candidate capture metrics, evaluation/report aggregation | imports earlier phase representations; Phase 8 imports six names from it, five private (`_memory_state`, `_partition_signature`, `_region_lookup`, `_angles_to_codes`, `_candidate_capture_metrics`) |
| `integration.py` | B, V, H | Phase-8 causal instance-keyed integration proposer/evaluator | none left beyond `cross_target_novelty`; the measured-geometry memory and effective-geometry composition moved to `fov3d.reconstruction.measurement_memory` in Core 1 | Phase-7 parity, Phase-8 proposal tree, novelty metrics, evaluator | imports five private names from `prefix_benchmark`; `tools/dev/check_partition_graph8.py` still imports `effective_target_geometry` through this module (a re-export) |
| `challenge_suite.py` | B, V | Phase-8b budget replay, UNKNOWN shells, eligibility floor and evaluation | no new core extraction in this step beyond using shared measurement memory | budgets, shells, eligibility, scenario construction, evaluation | since Core 1 it no longer duplicates routing or imports from `integration`; still imports private `benchmark` helpers (`_covered`, `_region_interfaces`) and `build_joint_graph` from `joint`; `HeadEvidence`/`add_head_patch` come from `fov3d.epistemic.head_memory` (Core 3) and `support_depth_from_map` from `fov3d.scene` (Core 4); chart and radius come from the conceptual modules since Core 2 |

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

## Proposed later extraction order

Subject to the measured results of Core 3, the likely next conceptual refactors are:

1. **Head-centered spherical chart + association constant (Conceptual Core 2; accepted)** —
   `fov3d.geometry.head_chart` and `fov3d.reconstruction.association`.
2. **Persistent head-centered epistemic memory (Conceptual Core 3; accepted)** —
   `fov3d.epistemic.head_memory` owns `HeadEvidence` / `add_head_patch`.
3. **Scene partition construction (Conceptual Core 4; proposed)** — move generic
   support/ownership/region construction out of `joint.py` behind `fov3d.scene`.
4. **Topology / relations** — make relation extraction operate on the generic scene graph
   rather than Phase-numbered state products.
5. **Epistemic partition versus benchmark policy** — separate reusable uncertainty/state
   representation from candidate/evaluation machinery in `benchmark.py` and
   `prefix_benchmark.py`.

The later order remains a proposal, not permission to perform those migrations in Core 3.
