# Migration Conceptual Core 5 — boundary extraction

## Status

Structural refactor only.

Parent accepted milestone:

    main @ 9b28722971622332ab121096521f72f268344387

Scientific parent milestone:

    Conceptual Core 4 @ 643d21a729e1e80c238aa08649715c5dfc1c18dd

Active branch:

    migration/conceptual-core-5

This step introduces no new scientific hypothesis, interface definition, connectivity
rule, edge-ordering rule, chain-tracing rule, boundary kind, depth-jump rule, front/back
interpretation, topology policy, relation interpretation, partition construction rule,
benchmark parameter, candidate policy, gaze policy, controller behavior, matcher
behavior, fusion behavior, renderer behavior, scene asset, termination rule, or
evaluation meaning.

Its purpose is to continue migration Step 5 by promoting the reusable boundary-extraction
mechanics out of the historical Classroom/Partition-Graph Phase-3 adapter.

The governing migration rule remains:

    migrate behavior first; redesign structure second

## Why this step

Conceptual Core 4 established reusable spherical scene-partition construction under:

    fov3d.scene.partition

The next stable block in the historical Phase-3 module is:

    _interface_edges(...)
    _trace_edge_components(...)
    extract_boundaries(...)

These functions transform an already-constructed region raster into embedded
BoundaryChain objects. Their inputs are generic scene representation data:

    region_code
    code_to_rid
    regions
    owner_depth
    controller-domain chart geometry
    grid_deg

They do not depend on saved-run traversal, controller replay, target-local gap analysis,
lineage, calibration, matcher/fusion/controller execution, or benchmark/evaluator policy.

Their sole production consumer is:

    build_joint_graph(...)

which remains the historical Phase-3 adapter/composer.

## Conceptual boundary

Create:

    fov3d/scene/boundaries.py

Move, as a literal behavior-preserving extraction:

    _interface_edges(...)
    _trace_edge_components(...)
    extract_boundaries(...)

Preserve all existing docstrings, explanatory comments, type annotations, ordering rules,
diagnostics, attribute names, and error behavior where practical.

Do not add these names to fov3d.scene.__all__ in Core 5.

The conceptual import is explicit:

    from fov3d.scene.boundaries import ...

This avoids any change to the accepted Core-4 bare-package import footprint and avoids
creating a new package-initialization gate merely for convenience.

## Exact behavior to preserve

### Interface enumeration

_interface_edges(region_code) must preserve exactly:

- region_code coercion to int32;
- 4-neighbour cell-side interfaces only;
- left/right interfaces enumerated before top/bottom interfaces;
- canonical region-code pair ordering:
      (min(code_a, code_b), max(code_a, code_b))
- doubled endpoint coordinates:
      cell centres at even coordinates;
      cell corners at odd coordinates;
- exact p0/p1 orientation and cell_a/cell_b/code_a/code_b metadata;
- defaultdict(list) grouping semantics;
- deterministic numpy nonzero row-major enumeration.

No diagonal interface is introduced.

### Deterministic chain tracing

_trace_edge_components(edges) must preserve exactly:

- endpoint-to-edge adjacency;
- an unused edge-index set;
- recomputed degrees over unused edges at each component start;
- lexicographically smallest degree-1 endpoint when an open endpoint exists;
- otherwise the lexicographically smallest endpoint over unused edges;
- sorted candidate edge indices at each step;
- first available candidate selection;
- exact closed-loop break condition;
- walk output as:
      (ordered doubled-coordinate points, ordered used edge indices)
- no geometry simplification, resampling, merging, splitting heuristic, or alternate
  graph traversal.

The deterministic ordering is part of accepted serialized output because boundary ids are
assigned in trace order.

### Boundary construction

extract_boundaries(...) must preserve exactly:

- sorted iteration over canonical region-code pairs;
- branch-vertex diagnostic as degree > 2 count per pair;
- chart mapping through fov3d.geometry.head_chart:
      chart_grid
      head_unit_from_angles
- conversion of doubled endpoints to half-cell chart coordinates;
- canonical region ordering from code_to_rid;
- boundary kind:
      OBJECT_OBJECT iff both incident regions are OBJECT_COMPONENT;
      otherwise OBJECT_BASE;
- exact attributes:
      source = "four_neighbour_cell_side_interface"
      interface_edge_count
      region_pair
- OBJECT_OBJECT depth diagnostics only when finite depth exists:
      depth_jump_median_m
      depth_jump_min_m
      depth_jump_max_m
      nearer_region_a_votes
      nearer_region_b_votes
- orientation of depth samples into canonical region-code order before nearer votes;
- exact boundary ids:
      jb00000, jb00001, ...
- exact BoundaryChain fields and closed-loop predicate;
- raster/encoded/unencoded edge diagnostics;
- RuntimeError if any raster interface edge is unencoded.

No occlusion classification, continuity inference, front/back labeling, semantic relation
inference, chain smoothing, chart-resolution change, or depth threshold is introduced.

## What remains in joint.py

Keep experiment-side and unchanged except for imports:

    StereoOps
    _default_stereo_ops
    build_joint_graph
    _append_raw_footprints
    controller seen_any replay helpers
    _component_boundary
    _line_cells
    gap_corridor
    corridors_for_object
    attach_state_region_codes
    target-component lineage helpers
    lift_joint_run
    saved-run traversal and Phase-3 report/state bookkeeping

build_joint_graph remains the adapter/composer that calls:

    joint_owner
    label_joint_regions
    extract_boundaries

and constructs ScenePartitionGraph with the accepted Phase-3 graph metadata.

The Phase-2 boundary construction in lift.py is a separate historical lineage and is
explicitly out of scope.

## Compatibility

Historical names through:

    fov3d.experiments.classroom_partition.joint

must remain valid:

    _interface_edges
    _trace_edge_components
    extract_boundaries

joint.py may import/re-export the exact objects from:

    fov3d.scene.boundaries

It must not duplicate their implementations.

No other production module should gain a dependency on joint.py for boundary extraction.

## Package-boundary rule from Core 4

Do not modify:

    fov3d/scene/__init__.py

in the normal Core-5 implementation.

The accepted Core-4 invariant is:

    import fov3d.scene

does not load:

    cv2
    fov3d.scene.partition

Core 5 must preserve that invariant.

The new boundaries module itself should remain NumPy-only apart from existing fov3d
geometry/model dependencies; it does not need OpenCV.

## Deliberately out of scope

Do not move, redesign, or unify:

- Phase-2 boundary construction in lift.py;
- BoundaryChain data model;
- SupportLayer / support_depth_from_map / joint_owner / label_joint_regions;
- gap_corridor or corridors_for_object;
- Phase-4 relation extraction;
- FineEvidence / add_patch_observation;
- HeadEvidence;
- target-component lineage;
- seen_any/controller evidence replay;
- benchmark / evaluator policy;
- target-relative epistemic-state placement;
- accepted reference registry;
- gaze, controller, matcher, fusion, renderer, termination, or scene assets.

Do not rename serialized boundary ids, source strings, diagnostic keys, or graph metadata.

## New checker

Add:

    tools/dev/check_conceptual_core5.py

It must be deterministic, inexpensive, host-side Python/NumPy, and fail-capable.

It must test at least:

1. A tiny region raster with known horizontal and vertical interfaces:
   - exact pair keys;
   - exact edge count;
   - exact doubled endpoints;
   - exact cell/code metadata.

2. No diagonal-only interface is created.

3. Deterministic open-chain tracing:
   - lexicographically smallest endpoint start;
   - exact point order;
   - exact used-edge order.

4. Deterministic closed-loop tracing:
   - stable start point;
   - stable edge order;
   - closed point sequence.

5. A branch fixture:
   - multiple deterministic walks as accepted by the current algorithm;
   - branch diagnostic preserved by extract_boundaries.

6. OBJECT_BASE boundary construction:
   - exact boundary id;
   - exact region order;
   - exact source string;
   - exact interface_edge_count;
   - unit sphere_xyz;
   - exact closed flag.

7. OBJECT_OBJECT boundary construction:
   - exact kind;
   - exact depth-jump median/min/max;
   - exact nearer votes after canonical code orientation.

8. Multiple region-pair ordering and deterministic jbNNNNN boundary id assignment.

9. Exact diagnostics:
      raster_interface_edges
      encoded_interface_edges
      unencoded_interface_edges
      boundary_chains
      branch_vertices

10. A deliberate malformed tracing/mutation harness or equivalent invariant capable of
    exposing dropped/unencoded edges.

11. Compatibility identities:
       joint._interface_edges is boundaries._interface_edges
       joint._trace_edge_components is boundaries._trace_edge_components
       joint.extract_boundaries is boundaries.extract_boundaries

12. joint.py contains no duplicate definitions of the three moved functions.

13. fov3d.scene.boundaries imports no fov3d.experiments module.

14. Bare fov3d.scene import remains Core-4 compatible:
       cv2 not loaded
       fov3d.scene.partition not loaded
       fov3d.scene.boundaries not loaded

15. Mutation-style checks must be capable of exposing at least:
   - diagonal interfaces;
   - reversed pair ordering;
   - nondeterministic/different start endpoint;
   - different candidate-edge order;
   - changed boundary-id order;
   - OBJECT_OBJECT misclassification;
   - changed depth-orientation vote semantics;
   - lost interface edge without RuntimeError.

The checker prints:

    [conceptual-core5-check] SUMMARY checked=<N> failed=0

and exits nonzero on failure.

## Allowed changes

Normally limited to:

    fov3d/scene/boundaries.py
    fov3d/experiments/classroom_partition/joint.py
    tools/dev/check_conceptual_core5.py
    docs/conceptual-core-map.md
    docs/migration-conceptual-core-5-report.md
    docs/chat-handoff.md

Do not modify fov3d/scene/__init__.py unless execution discovers a concrete need and Chat
explicitly approves it.

No other production file should change without an execution-discovered need inside this
extraction boundary and explicit documentation in the report.

Do not edit:

- existing phase checkers merely to accommodate the refactor;
- Phase-2 lift.py boundary construction;
- protected sealed runtime files;
- golden signatures;
- scene assets;
- accepted preview/reference outputs;
- existing acceptance thresholds.

## Execution-gate principle

Every changed function or module-level dependency must map to at least one execution gate
that actually exercises it.

Because Core 5 deliberately does not alter fov3d.scene.__init__, Phases 2, 6, 7 and 8 are
not automatically part of the required replay set. Add them only if import/dependency
analysis shows that the final diff reaches them.

The accepted Phase-3 producer reference is:

    previews/partition-graph-4-lift

not partition-graph-3-full.

## Execution gates

Run in this order.

### A. Interactive structural gates

1. Compile every changed Python file.

2. Run:

       .venv/bin/python tools/dev/check_conceptual_core5.py
       .venv/bin/python tools/dev/check_conceptual_core4.py
       .venv/bin/python tools/dev/check_conceptual_core3.py
       .venv/bin/python tools/dev/check_conceptual_core2.py
       .venv/bin/python tools/dev/check_conceptual_core1.py

3. Run existing Partition-Graph checkers 1 through 8b.

4. Run:

       .venv/bin/python tools/dev/check_fov3d_facade.py
       scripts/verify_baseline.sh
       scripts/compare_golden.sh previews/partition-graph-2-source-full
       git diff --check

Golden requirement:

       [compare-golden] MISMATCHES 0

5. Run fresh-process import probes confirming bare fov3d.scene has the same module
   footprint as accepted Core 4.

### B. Phase-3 joint lift — primary producer replay

Run:

    .venv/bin/python tools/partition_graph3_lift.py       previews/partition-graph-2-source-full       previews/conceptual-core-5-phase3-full

Compare all 419 producer files byte-for-byte against:

    previews/partition-graph-4-lift

Required COMPLETE invariants:

    states = 104
    evidence_checks = 51
    evidence_mismatches = 0

This is the primary execution gate for the moved boundary extraction.

### C. Phase-4 analyzer

Run:

    .venv/bin/python tools/partition_graph4_analyze.py       previews/partition-graph-2-source-full       previews/partition-graph-4-lift       previews/conceptual-core-5-phase4-full

Compare the 211-file producer scope byte-for-byte against:

    previews/partition-graph-4-full

using the accepted demo exclusions.

### D. Phase-5 analyzer

Run:

    .venv/bin/python tools/partition_graph5_analyze.py       previews/partition-graph-2-source-full       previews/partition-graph-4-lift       previews/partition-graph-4-full       previews/conceptual-core-5-phase5-full

Required COMPLETE values:

    states = 104
    target_gap_violations = 0
    challenge_relations = 108
    challenge_states = 41
    challenge_targets = 4

Compare the 211-file producer scope byte-for-byte against:

    previews/partition-graph-5-full

using the accepted demo exclusions.

### E. Phase-8b proposer

Run:

    .venv/bin/python tools/partition_graph8b_propose.py       previews/partition-graph-2-source-full       previews/partition-graph-5-full       previews/partition-graph-8-proposals       previews/conceptual-core-5-phase8b-proposals

Required COMPLETE values:

    scenarios = 5
    states = 125
    targets = 25
    full_phase8_parity = 25
    raw_candidates = 18469
    eligible_candidates = 6489
    truth_used = false

Compare all 503 producer files byte-for-byte against:

    previews/partition-graph-8b-proposals

This gate exercises build_joint_graph and therefore the moved boundary extraction in the
Phase-8b path.

### F. Phase-8b evaluator

Run with accepted inputs to:

    previews/conceptual-core-5-phase8b-evaluation

Require the 3-file evaluator scope to be byte-identical to:

    previews/partition-graph-8b-evaluation

and preserve:

    full_eligible_recall = 0.9335820895522388

This evaluator is a downstream serialization/parity gate; it need not call the moved
functions directly.

## Conditional gates

Before expensive replay, perform a repository-wide import/dependency audit.

If the final diff changes fov3d.scene.__init__ or reaches Phase 2, 6, 7, or 8 producer
imports, replay those affected producer/evaluator paths exactly as in the accepted Core-4
report.

In particular, the approximately 11-minute Phase-8 proposer is required only if the final
Core-5 diff reaches its executable/import path.

## Comparison rule

For Gates B-F:

1. write only to fresh Core-5 output directories;
2. never modify accepted references;
3. identify the producer/evaluator file set from the fresh command output;
4. require every fresh file to exist at the accepted relative path;
5. require every corresponding file to be byte-identical;
6. require the accepted producer/evaluator scope to have no silently omitted file;
7. exclude only previously demonstrated post-producer demo/package artifacts and record
   every exclusion;
8. record file counts and deterministic manifests/checksums in the report.

## Acceptance

Conceptual Core 5 passes only if all of the following hold:

- fov3d.scene.boundaries is the conceptual owner of _interface_edges,
  _trace_edge_components, and extract_boundaries;
- the three moved functions preserve accepted behavior exactly;
- joint.py contains no duplicate implementations;
- compatibility identities through joint.py are preserved;
- build_joint_graph remains experiment-side and unchanged except for dependency binding;
- fov3d.scene.__init__ remains unchanged unless separately approved;
- bare fov3d.scene import preserves the Core-4 lightweight/OpenCV-free footprint;
- no conceptual scene module imports fov3d.experiments;
- Phase-2 boundary construction, gap corridors, relation logic, lineage, controller replay,
  partition construction, and benchmark policy remain unchanged;
- the Core-5 checker passes and is demonstrably fail-capable;
- Core-1 through Core-4 checkers pass;
- existing Partition-Graph checkers 1-8b pass;
- facade, baseline, golden, and diff checks pass;
- golden comparison remains MISMATCHES 0;
- Gates B-F reproduce accepted producer/evaluator scopes byte-for-byte;
- all conditionally affected paths are replayed if dependency audit requires them;
- every changed function/module dependency is covered by at least one actual execution
  gate and the mapping is recorded;
- protected runtime/reference files remain untouched;
- no scientific/runtime behavior changes.

If exact parity fails, diagnose before modifying code. Do not change acceptance criteria or
accepted outputs.

## Permitted fixes

Claude Code may make minimal implementation repairs inside the extraction boundary.

It may:

- repair imports, typing, checker defects, or literal extraction mistakes;
- preserve compatibility aliases needed by existing callers;
- strengthen the Core-5 checker without weakening any acceptance gate;
- make a strictly mechanical correction required to execute the declared gates,
  documenting it separately.

It may not:

- change interface enumeration;
- change deterministic walk ordering;
- change boundary ids, region ordering, source strings, diagnostics, or depth-vote
  semantics;
- change boundary classification;
- modify fov3d.scene.__init__ without Chat approval;
- unify Phase-2 and Phase-3 boundary implementations;
- move or change gap/relation logic;
- change partition, benchmark, evaluator, attention, gaze, controller, matcher, fusion,
  renderer, scene, or termination semantics;
- edit accepted preview/reference trees;
- edit golden signatures;
- relax parity requirements.

If a repair would require any of those, stop and return the decision to Luiz and Chat.

## Report

Commit:

    docs/migration-conceptual-core-5-report.md

Include:

- branch and exact commit provenance;
- files changed;
- final boundary API and dependency direction;
- compatibility decisions;
- literal-extraction / dependency audit;
- Core-5 through Core-1 checker summaries;
- phase-checker/facade/baseline/golden summaries;
- exact commands, runtimes, file counts, exclusions, and byte-parity results for Gates B-F;
- conditional-gate decision and evidence;
- changed-function/dependency -> execution-gate table;
- mutation/fail-capability evidence;
- every repair or deviation;
- confirmation that Phase-2 boundary construction and relation/gap logic were untouched;
- confirmation that fov3d.scene package import footprint stayed lightweight;
- confirmation that no scientific/runtime behavior changed;
- unresolved architectural questions;
- bounded recommendation for Conceptual Core 6 only.

Required success marker:

    CONCEPTUAL_CORE5_BOUNDARY_EXTRACTION_PRESERVES_BEHAVIOR
