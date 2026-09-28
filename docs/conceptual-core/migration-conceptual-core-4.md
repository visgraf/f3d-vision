# Migration Conceptual Core 4 — scene partition construction

## Status

Structural refactor only.

Parent accepted milestone:

    main @ 989127cafa784bf9e95cf9b3880fb6085ea283e6

Scientific parent milestone:

    Conceptual Core 3 @ 502439f689ca55c9c50aa2be851415f4568037bb

Active branch:

    migration/conceptual-core-4

This step introduces no new scientific hypothesis, support rule, association radius,
depth rule, ownership rule, connectivity convention, region identity, boundary semantics,
topology rule, benchmark parameter, candidate policy, gaze policy, controller behavior,
matcher behavior, fusion behavior, renderer behavior, scene asset, termination rule, or
evaluation meaning.

Its purpose is to continue migration Step 5 by promoting generic scene-partition
construction out of the historical Classroom/Partition-Graph lineage.

The governing migration rule remains:

    migrate behavior first; redesign structure second

## Why this step

The accepted repository already owns the scene graph data model under:

    fov3d.scene

but the reusable construction mechanics still live in:

    fov3d/experiments/classroom_partition/joint.py

Specifically:

    SupportLayer
    support_depth_from_map(...)
    joint_owner(...)
    label_joint_regions(...)

These operations are no longer merely Phase-3 experiment scaffolding:

- support rasterization is used by Phases 3, 4, 5, 8 and 8b;
- frontmost ownership and connected-region construction define the scene partition
  represented by ScenePartitionGraph;
- later modules import support rasterization through the historical joint module.

Conceptual Core 4 moves that stable construction layer behind the scene API while leaving
Phase-3 replay, boundary extraction, lineage, corridors, calibration replay, and
controller-evidence replay experiment-side.

## Conceptual boundary

Create:

    fov3d/scene/partition.py

The conceptual owner should contain, without semantic redesign:

    SupportLayer
    support_depth_from_map(...)
    joint_owner(...)
    label_joint_regions(...)

Private helpers required only by these functions move with them:

    _disk(...)
    _component_attrs(...)

Export the public names through:

    fov3d.scene

### Support rasterization

Preserve exactly:

- fixed-head chart mapping from fov3d.geometry.head_chart;
- the canonical SURFACE_ASSOCIATION_RADIUS_M from
  fov3d.reconstruction.association;
- float64 input conversion and finite-point filtering;
- point_yx shape, dtype, sentinel values, and original-index alignment;
- angular association radius:
      degrees(arctan(radius / max(range, 1e-12)))
- ceil to chart cells and minimum one-cell radius;
- per-radius raster accumulation;
- OpenCV erosion using the same disk and BORDER_CONSTANT +inf behavior;
- minimum depth across association disks;
- support = isfinite(depth);
- float32 depth output;
- surfel_count meaning.

### Frontmost ownership

Preserve exactly:

- at least one layer is required;
- all support layers must have identical shape;
- overlap_count is uint16 and is the sum of layer support masks;
- smaller metric depth wins;
- exact equal-depth ties select the smaller instance id;
- owner is int32;
- owner depth is float32 +inf where unowned;
- deterministic iteration in sorted instance-id order.

The equal-depth tie is a deterministic raster convention, not a scientific claim.

### Connected region construction

Preserve exactly:

- one object face per 8-connected component of each positive owner id;
- BASE/complement uses dual 4-connectivity;
- deterministic instance and component iteration/order;
- exact region ids:
      obj:<iid>:c<NNN>
      base:c<NNN>
- exact sequential state_region_code assignment;
- exact PartitionRegion and ObjectHypothesis attributes and source strings;
- exact component attributes:
      cell_count
      touches_domain_edge
      median_depth_m
      min_depth_m
      max_depth_m
- exact identity_source string:
      inherited_from_classroom_oracle1
- every chart cell must receive a region code.

The names and strings above are preserved because accepted serialized outputs depend on
them. Their historical wording is not redesigned in Core 4.

## What remains in joint.py

Keep experiment-side:

    StereoOps
    _default_stereo_ops
    rectified/controller-evidence replay helpers
    _interface_edges
    _trace_edge_components
    extract_boundaries
    build_joint_graph
    gap_corridor
    corridors_for_object
    attach_state_region_codes
    target-component lineage helpers
    lift_joint_run
    saved-run traversal, report production, and Phase-3 state bookkeeping

Boundary extraction is deliberately **not** moved in Core 4. It is topology/relations work
and remains the candidate for a later conceptual migration.

build_joint_graph remains the Phase-3 adapter/composer. It should call the conceptual
scene-partition functions but retain its existing boundary extraction and exact graph
metadata.

## Compatibility

Historical imports through:

    fov3d.experiments.classroom_partition.joint

must remain valid for existing phase checkers and any accepted tool behavior.

Therefore joint.py may retain direct aliases/imported names for:

    SupportLayer
    support_depth_from_map
    joint_owner
    label_joint_regions

They must be the same objects as the fov3d.scene public API, not duplicate
implementations.

Production consumers outside joint.py should import support_depth_from_map directly from
fov3d.scene rather than through the historical experiment module.

At minimum inspect and update:

    fov3d/experiments/classroom_partition/relations.py
    fov3d/experiments/classroom_partition/incidental.py
    fov3d/experiments/classroom_partition/integration.py
    fov3d/experiments/classroom_partition/challenge_suite.py

Do not introduce a new cross-phase dependency.

## Deliberately out of scope

Do not move or redesign:

- extract_boundaries or BoundaryChain construction;
- gap corridors or relation extraction;
- FineEvidence / add_patch_observation;
- HeadEvidence;
- ObservationFootprint / ObservationOverlay;
- build_joint_graph metadata or Phase-3 saved-run adaptation;
- controller seen_any replay;
- target-component lineage;
- benchmark / evaluator policy;
- target-relative epistemic-state placement;
- accepted reference registry;
- gaze, controller, matcher, fusion, renderer, termination, or scene assets.

Do not rename serialized schema keys or accepted source strings.

## New checker

Add:

    tools/dev/check_conceptual_core4.py

It must be pure host-side Python/NumPy/OpenCV, deterministic, inexpensive, and
fail-capable.

It must test at least:

1. SupportLayer public availability from fov3d.scene and compatibility identity through
   classroom_partition.joint.

2. Empty/finite support raster behavior, including exact dtypes/shapes and point_yx
   original-index alignment.

3. A controlled support-radius fixture that distinguishes the accepted disk-expansion
   behavior from a point-only raster.

4. joint_owner nearest-depth selection.

5. joint_owner exact equal-depth tie -> smaller instance id.

6. joint_owner overlap_count dtype and values.

7. shape mismatch fails.

8. object foreground uses 8-connectivity: a diagonal two-cell object forms one region.

9. BASE uses 4-connectivity: a diagonal-only BASE connection remains two regions.

10. exact region ids, state_region_code ordering, object membership, source strings, and
    identity_source.

11. touches_domain_edge and depth summary attributes on a controlled fixture.

12. every cell is labeled.

13. joint compatibility identities:
       joint.SupportLayer is scene.SupportLayer
       joint.support_depth_from_map is scene.support_depth_from_map
       joint.joint_owner is scene.joint_owner
       joint.label_joint_regions is scene.label_joint_regions

14. relations.py, incidental.py, integration.py, and challenge_suite.py import
    support_depth_from_map from fov3d.scene, not from joint.py.

15. fov3d.scene.partition has no import from fov3d.experiments.

16. deliberate negative/mutation-style invariants capable of exposing:
    - larger-id equal-depth tie selection;
    - foreground 4-connectivity replacing 8;
    - BASE 8-connectivity replacing 4;
    - association radius collapsing to point-only support.

The checker prints:

    [conceptual-core4-check] SUMMARY checked=<N> failed=0

and exits nonzero on failure.

## Allowed changes

Normally limited to:

    fov3d/scene/partition.py
    fov3d/scene/__init__.py
    fov3d/experiments/classroom_partition/joint.py
    fov3d/experiments/classroom_partition/relations.py
    fov3d/experiments/classroom_partition/incidental.py
    fov3d/experiments/classroom_partition/integration.py
    fov3d/experiments/classroom_partition/challenge_suite.py
    tools/dev/check_conceptual_core4.py
    docs/conceptual-core-map.md
    docs/migration-conceptual-core-4-report.md
    docs/chat-handoff.md

No other production file should change without an execution-discovered need inside this
extraction boundary and explicit documentation in the report.

Do not edit:

- existing phase checkers merely to accommodate the refactor;
- protected sealed runtime files;
- golden signatures;
- scene assets;
- accepted preview/reference outputs;
- existing acceptance thresholds.

## Execution-gate principle

Every changed function or module-level dependency must map to at least one execution gate
that actually exercises it.

Exact comparisons compare producer/evaluator outputs from the command under test, not
unrelated demo artifacts stored later in the same accepted directory.

The accepted Phase-3 producer reference is:

    previews/partition-graph-4-lift

not the historically stale partition-graph-3-full tree.

## Execution gates

Run in this order.

### A. Interactive structural gates

1. Compile every changed Python file.

2. Run:

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

### B. Phase-3 joint lift — primary producer replay

Run:

    .venv/bin/python tools/partition_graph3_lift.py       previews/partition-graph-2-source-full       previews/conceptual-core-4-phase3-full

Compare the complete 419-file producer scope byte-for-byte against:

    previews/partition-graph-4-lift

Required COMPLETE invariants:

    states = 104
    evidence_checks = 51
    evidence_mismatches = 0

This gate directly exercises support_depth_from_map, joint_owner,
label_joint_regions, and build_joint_graph through the accepted Phase-3 path.

### C. Phase-4 analyzer

Run:

    .venv/bin/python tools/partition_graph4_analyze.py       previews/partition-graph-2-source-full       previews/partition-graph-4-lift       previews/conceptual-core-4-phase4-full

Compare the 211-file producer scope byte-for-byte against:

    previews/partition-graph-4-full

using the previously demonstrated demo exclusions.

### D. Phase-5 analyzer

Run:

    .venv/bin/python tools/partition_graph5_analyze.py       previews/partition-graph-2-source-full       previews/partition-graph-4-lift       previews/partition-graph-4-full       previews/conceptual-core-4-phase5-full

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

    .venv/bin/python tools/partition_graph8b_propose.py       previews/partition-graph-2-source-full       previews/partition-graph-5-full       previews/partition-graph-8-proposals       previews/conceptual-core-4-phase8b-proposals

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

### F. Phase-8b evaluator

Run with accepted inputs to:

    previews/conceptual-core-4-phase8b-evaluation

Require the 3-file evaluator scope to be byte-identical to:

    previews/partition-graph-8b-evaluation

and preserve:

    full_eligible_recall = 0.9335820895522388

This gate covers module loading after the challenge_suite import change.

### G. Phase-8 proposer — explicitly authorized long gate

integration.py changes its support_depth_from_map dependency, so the approximately
11-minute Phase-8 proposer is a changed executable path and must be run.

Run:

    .venv/bin/python tools/partition_graph8_integrate.py       previews/partition-graph-2-source-full       previews/partition-graph-5-full       previews/partition-graph-7-proposals       previews/conceptual-core-4-phase8-proposals

Required COMPLETE values:

    states = 104
    targets = 25
    phase7_global_parity = 104
    target_evidence_unmapped_cells = 0
    candidate_regions = 16825
    truth_used = false

Compare all 468 producer files byte-for-byte against:

    previews/partition-graph-8-proposals

### H. Phase-8 evaluator

Run with accepted inputs to:

    previews/conceptual-core-4-phase8-evaluation

Require the 107-file evaluator scope to be byte-identical to:

    previews/partition-graph-8-evaluation

and preserve:

    historical_state_misses = 101824
    integration_gain = 61557
    residual_candidate_recall = 0.955472222912062

This gate covers module loading after the integration import change.

## Comparison rule

For Gates B-H:

1. write only to fresh Core-4 output directories;
2. never modify accepted references;
3. identify the producer/evaluator file set from the fresh command output;
4. require every fresh file to exist at the accepted relative path;
5. require every corresponding file to be byte-identical;
6. require the accepted producer/evaluator scope to have no silently omitted file;
7. exclude only previously demonstrated post-producer demo/package artifacts and record
   every exclusion;
8. record file counts and deterministic manifests/checksums in the report.

## Acceptance

Conceptual Core 4 passes only if all of the following hold:

- fov3d.scene is the conceptual owner of SupportLayer, support_depth_from_map,
  joint_owner, and label_joint_regions;
- those functions preserve accepted semantics exactly;
- joint.py contains no duplicate implementations of the extracted concepts;
- historical imports through joint.py remain compatibility identities;
- production consumers use the scene API directly for support_depth_from_map;
- no conceptual scene module imports fov3d.experiments;
- boundary extraction, FineEvidence, HeadEvidence, topology/relations policy, benchmark
  policy, and scientific runtime behavior remain unchanged;
- the Core-4 checker passes and is demonstrably fail-capable;
- Core-1 through Core-3 checkers pass;
- existing Partition-Graph checkers 1-8b pass;
- facade, baseline, golden, and diff checks pass;
- golden comparison remains MISMATCHES 0;
- Gates B-H reproduce accepted producer/evaluator scopes byte-for-byte;
- every changed function/module dependency is covered by at least one actual execution
  gate and the mapping is recorded;
- protected runtime/reference files remain untouched;
- no scientific/runtime behavior changes.

If exact parity fails, diagnose before modifying code. Do not change acceptance criteria
or accepted outputs.

## Permitted fixes

Claude Code may make minimal implementation repairs inside the extraction boundary.

It may:

- repair imports, typing, package exports, checker defects, or mechanical extraction
  mistakes;
- preserve compatibility aliases needed by existing checkers;
- strengthen the Core-4 checker without weakening any acceptance gate;
- make a strictly mechanical correction required to execute the declared gates,
  documenting it separately.

It may not:

- change the 12-mm association rule;
- change depth or tie semantics;
- change foreground/background connectivity;
- change region ids, code order, source strings, graph metadata, or serialized schemas;
- move boundary extraction or relation logic;
- change benchmark, evaluator, attention, gaze, controller, matcher, fusion, renderer,
  scene, or termination semantics;
- edit accepted preview/reference trees;
- edit golden signatures;
- relax parity requirements.

If a repair would require any of those, stop and return the decision to Luiz and Chat.

## Report

Commit:

    docs/migration-conceptual-core-4-report.md

Include:

- branch and exact commit provenance;
- files changed;
- final scene-partition API and dependency direction;
- compatibility/re-export decisions;
- repository-wide dependency audit;
- Core-4/Core-3/Core-2/Core-1 checker summaries;
- phase-checker/facade/baseline/golden summaries;
- exact commands, runtimes, file counts, exclusions, and byte-parity results for Gates B-H;
- changed-function/dependency -> execution-gate table;
- mutation/fail-capability evidence;
- every repair or deviation;
- confirmation that boundary extraction and relation logic were not moved;
- confirmation that no scientific/runtime behavior changed;
- unresolved architectural questions;
- bounded recommendation for Conceptual Core 5 only.

Required success marker:

    CONCEPTUAL_CORE4_SCENE_PARTITION_PRESERVES_BEHAVIOR
