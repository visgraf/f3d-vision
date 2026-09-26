# Conceptual core migration map

Status: Conceptual Core 1 was verified and accepted. Conceptual Core 2 is now proposed on
`migration/conceptual-core-2`; its measured acceptance status belongs in
`docs/migration-conceptual-core-2-report.md`.

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
| `lift.py` | G, P, C | lifts saved Classroom prefixes into spherical scene/observation structures | spherical chart transforms (`_grid`, `_cells`, `_head_angles_from_unit`, `_head_unit_from_angles`), observation footprint construction, visibility overlay mechanics | saved-run paths, manifest/calibration replay, Classroom prefix traversal | its *private* chart helpers are imported by `joint`, `relations`, `incidental` and `benchmark`; defines `FUSION_RADIUS_M = 0.012`, which `benchmark.py` defines a second time |
| `joint.py` | P, T, C | combines reconstructed object supports into one frontmost spherical partition; replays the controller's `seen_any` sampling from saved calibrations | support rasterization (`support_depth_from_map`), joint ownership/depth, connected scene regions, object-object boundaries | reconstruction of a particular saved Classroom prefix; controller `seen_any` replay (lazy `fov3d.stereo.core` import) | imports seven lift names (five private); `support_depth_from_map` is consumed by Phases 4, 5, 8 and 8b and `build_joint_graph` by Phase 8b |
| `relations.py` | T, E, H | derives ownership cuts, own-support gaps and relation descriptors; Phase-4 left-eye evidence replay (`FineEvidence`) | topological/geometric relation extraction between scene regions/components | Phase-specific diagnostics and report fields; left-eye `FineEvidence`, superseded by head-centred `HeadEvidence` in Phase 5 | imports private `joint` helpers (`_default_stereo_ops`, `_rectified_core_directions_h`); no later module imports it, and Phase 5 consumes its output only as saved `relations.json` |
| `incidental.py` | E, H | accumulates head-centred observed depth/instance evidence and annotates relations | epistemic measurement state (`HeadEvidence`, `add_head_patch`) | Phase-5 report classifications and saved-prefix analysis | since this step it delegates patch validation to `fov3d.reconstruction.measurement_memory`; `HeadEvidence`/`add_head_patch` are still imported by Phases 7, 8 and 8b (deliberately not moved here) |
| `benchmark.py` | E, P, B, V | constructs the truth-free epistemic partition and performs Phase-6 evaluation support | epistemic region construction and region adjacency may become reusable | candidate definition, truth firewall, Phase-6 benchmark/evaluation statistics | representation and benchmark policy share one module; re-exports lift's `_cells`/`_grid` to Phases 7, 8 and 8b; second `FUSION_RADIUS_M`; its 12-mm `_covered` query is used by the Phase-8 proposer's novelty metric as well as by evaluators |
| `prefix_benchmark.py` | B, V, H | builds Phase-7 prefix benchmark views and metrics | small representation helpers may survive after audit | prefix scenarios, candidate capture metrics, evaluation/report aggregation | imports earlier phase representations; Phase 8 imports six names from it, five private (`_memory_state`, `_partition_signature`, `_region_lookup`, `_angles_to_codes`, `_candidate_capture_metrics`) |
| `integration.py` | B, V, H | Phase-8 causal instance-keyed integration proposer/evaluator | none left beyond `cross_target_novelty`; the measured-geometry memory and effective-geometry composition moved to `fov3d.reconstruction.measurement_memory` in this step | Phase-7 parity, Phase-8 proposal tree, novelty metrics, evaluator | imports five private names from `prefix_benchmark`; `tools/dev/check_partition_graph8.py` still imports `effective_target_geometry` through this module (a re-export) |
| `challenge_suite.py` | B, V | Phase-8b budget replay, UNKNOWN shells, eligibility floor and evaluation | no new core extraction in this step beyond using shared measurement memory | budgets, shells, eligibility, scenario construction, evaluation | since this step it no longer duplicates routing or imports from `integration`; still imports private `benchmark` helpers (`_covered`, `_region_interfaces`, `_cells`, `_grid`) plus `incidental` and `joint` |

## Concept extracted in this step

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

## Proposed later extraction order

Subject to the measured results of this refactor, the likely next conceptual refactors
are:

1. **Head-centered spherical chart + association constant (Conceptual Core 2, proposed)** —
   promote the fixed-head yaw/pitch mapping and chart indexing to
   `fov3d.geometry.head_chart`, and make `fov3d.reconstruction.association` the single
   source of the frozen 12-mm radius. Observation/epistemic state is deliberately deferred.
2. **Observation / epistemic state** — separate reusable observation-state operations from
   historical Phase-4/5 replay without changing chart or partition semantics.
3. **Scene partition construction** — move generic support/ownership/region construction
   out of `joint.py` behind the scene representation API.
4. **Topology / relations** — make relation extraction operate on the generic scene graph
   rather than Phase-numbered state products.
5. **Epistemic partition versus benchmark policy** — separate reusable uncertainty/state
   representation from candidate/evaluation machinery in `benchmark.py` and
   `prefix_benchmark.py`.

The order is a proposal, not permission to perform those migrations in Conceptual Core 1.
