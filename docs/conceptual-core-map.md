# Conceptual core migration map

Status: proposed by Chat for Migration Conceptual Core 1. Claude Code must verify this
classification against the live code while executing
`docs/migration-conceptual-core-1.md` and record corrections in the phase report.

The purpose of this map is to distinguish stable system concepts from the
Classroom/Partition-Graph experiment lineage. It is intentionally architectural, not
chronological.

| module | present role | eventually reusable | should remain experiment-specific | current coupling signal |
|---|---|---|---|---|
| `lift.py` | lifts saved Classroom prefixes into spherical scene/observation structures | spherical chart transforms, observation footprint construction, visibility overlay mechanics | saved-run paths, manifest/calibration replay, Classroom prefix traversal | reusable geometry is mixed with file-layout assumptions |
| `joint.py` | combines reconstructed object supports into one frontmost spherical partition | support rasterization, joint ownership/depth, connected scene regions, object-object boundaries | reconstruction of a particular saved Classroom prefix | imports lift/chart helpers and carries run-state metadata |
| `relations.py` | derives ownership cuts, own-support gaps and relation descriptors | topological/geometric relation extraction between scene regions/components | Phase-specific diagnostics and report fields | relation semantics are embedded in the Classroom analysis package |
| `incidental.py` | accumulates head-centred observed depth/instance evidence and annotates relations | epistemic measurement state; valid-patch measurement extraction | Phase-5 report classifications and saved-prefix analysis | patch parsing was a private helper reused by later phases |
| `benchmark.py` | constructs the truth-free epistemic partition and performs Phase-6 evaluation support | epistemic region construction and region adjacency may become reusable | candidate definition, truth firewall, Phase-6 benchmark/evaluation statistics | representation and benchmark policy share one module |
| `prefix_benchmark.py` | builds Phase-7 prefix benchmark views and metrics | small representation helpers may survive after audit | prefix scenarios, candidate capture metrics, evaluation/report aggregation | mostly benchmark-oriented and imports earlier phase representations |
| `integration.py` | Phase-8 causal instance-keyed integration proposer/evaluator | **instance-keyed measured-geometry memory and effective geometry composition** | Phase-7 parity, Phase-8 proposal tree, novelty metrics, evaluator | stable routing mechanism is implemented inline with Phase-8 experiment logic |
| `challenge_suite.py` | Phase-8b budget replay, UNKNOWN shells, eligibility floor and evaluation | no new core extraction in this step beyond using shared measurement memory | budgets, shells, eligibility, scenario construction, evaluation | duplicates the routing pool and imports effective geometry from Phase 8 |
| `__init__.py` | marks retrospective Classroom partition package | none by itself | package identity | package remains the home of experiment adapters/benchmarks |

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

1. **Spherical chart / observation state** — separate generic chart and observation
   operations from saved Classroom replay in `lift.py` and `incidental.py`.
2. **Scene partition construction** — move generic support/ownership/region construction
   out of `joint.py` behind the scene representation API.
3. **Topology / relations** — make relation extraction operate on the generic scene graph
   rather than Phase-numbered state products.
4. **Epistemic partition versus benchmark policy** — separate reusable uncertainty/state
   representation from candidate/evaluation machinery in `benchmark.py` and
   `prefix_benchmark.py`.

The order is a proposal, not permission to perform those migrations in Conceptual Core 1.
