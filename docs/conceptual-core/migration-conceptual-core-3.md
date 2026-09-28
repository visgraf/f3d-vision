# Migration Conceptual Core 3 — persistent head-centered epistemic memory

## Status

Structural refactor only.

Parent accepted milestone:

    main @ a48124e44655c0021bebbff623dbf11de05f478a

Active branch:

    migration/conceptual-core-3

This step introduces no new scientific hypothesis, observation rule, chart convention,
chart resolution, instance-association rule, reconstruction rule, benchmark parameter,
candidate policy, gaze policy, controller behavior, matcher behavior, fusion behavior,
renderer behavior, scene asset, termination rule, or evaluation meaning.

Its purpose is to continue migration Step 5 by promoting one de-facto shared persistent
concept out of the historical Classroom/Partition-Graph lineage:

    persistent head-centered epistemic memory

The governing migration rule remains:

    migrate behavior first; redesign structure second

## Why this step

Conceptual Core 1 extracted persistent instance-keyed measured 3-D memory.

Conceptual Core 2 extracted the fixed-head spherical chart and made the 12-mm surface
association radius conceptually explicit.

The remaining head-centered evidence accumulator still lives in the historical Phase-5
module:

    fov3d/experiments/classroom_partition/incidental.py

but it is persistent causal state used beyond Phase 5 by Phases 7, 8, and 8b:

    saved valid patch
        -> fixed-head spherical projection
        -> HeadEvidence
        -> Phase 5
        -> Phase 7 global causal memory
        -> Phase 8
        -> Phase 8b

That implementation has therefore become architecture while still being owned by a
historical experiment module.

## Conceptual boundary

Create:

    fov3d/epistemic/__init__.py
    fov3d/epistemic/head_memory.py

Move, without semantic redesign:

    HeadEvidence
    add_head_patch(...)

from:

    fov3d/experiments/classroom_partition/incidental.py

to:

    fov3d/epistemic/head_memory.py

The implementation should remain as close to a literal extraction as practical.

### Target-neutral accumulated state

These fields are conceptually independent of the active target used when a patch was
acquired:

    depth_seen
    nearest_instance
    nearest_range_m
    ambiguous_instance
    sample_count

### Target-relative accumulated state

These two fields are conditioned on the target id passed to add_head_patch:

    target_depth_seen
    other_depth_seen

This distinction is important, but Conceptual Core 3 must **not** redesign it.

The target-relative fields remain stored in HeadEvidence with exactly the current update
semantics. A future representation may make them a derived or target-conditioned view, but
that is explicitly outside this step.

## Exact behavior to preserve

HeadEvidence.empty(shape) must preserve the current field shapes, dtypes, and initial
values:

- depth_seen: bool False
- target_depth_seen: bool False
- other_depth_seen: bool False
- nearest_instance: int32 zero
- nearest_range_m: float32 +inf
- ambiguous_instance: bool False
- sample_count: uint16 zero

add_head_patch(...) must preserve exactly:

- patch validation/filtering through
  fov3d.reconstruction.measurement_memory.valid_patch_measurements;
- head-frame direction mapping through fov3d.geometry.head_chart;
- accepted chart-cell rounding and domain clipping;
- valid_points counting *after* chart-domain filtering;
- cumulative depth_seen marking;
- target_depth_seen / other_depth_seen marking from the supplied target_id;
- sample_count accumulation with uint16 saturation;
- deterministic nearest sample selection per chart cell:
    distance first, then smaller instance id for exact distance ties;
- nearest_range_m stored as float32;
- ambiguity when more than one valid instance identity occupies a chart cell within one
  patch;
- ambiguity when accumulated history changes the nearest instance identity;
- monotonic ambiguity flags;
- returned delta dictionary and integer meanings:
    valid_points
    new_depth_cells
    depth_cells

No deduplication, fusion, confidence weighting, temporal decay, ownership inference,
semantic association, target remapping, or alternative ambiguity rule is introduced.

## Dependency direction

The conceptual module may depend only on stable lower-level concepts needed by the current
implementation:

    fov3d.geometry.head_chart
    fov3d.reconstruction.measurement_memory
            -> fov3d.epistemic.head_memory

Experiment modules may depend on fov3d.epistemic.head_memory.

The extraction must remove the later-phase dependency on Phase-5 experiment ownership:

    prefix_benchmark.py
    integration.py
    challenge_suite.py

must import HeadEvidence and add_head_patch directly from:

    fov3d.epistemic.head_memory

incidental.py should itself import the new definitions and may thereby retain the historical
names as compatibility re-exports. Do not duplicate their implementation.

No new dependency from a conceptual module into
fov3d.experiments.classroom_partition is allowed.

## Deliberately out of scope

Do **not** move or redesign:

    FineEvidence
    add_patch_observation(...)

They remain in:

    fov3d/experiments/classroom_partition/relations.py

FineEvidence is a historical Phase-4 left-eye rectified-core/controller replay adapter. It
depends on calibration, rectification, left support masks, and
_rectified_core_directions_h. It is not the persistent general epistemic memory.

Also do **not** move or redesign:

    ObservationFootprint
    ObservationOverlay

They already belong in fov3d.scene.

The conceptual distinction remains:

    ObservationOverlay:
        where have the eyes looked?

    HeadEvidence:
        what 3-D / identity evidence has been measured there?

Keep the following experiment-side:

    HEAD_CLASS_NAMES
    HEAD_CLASS_CODE
    reconstruction_status(...)
    annotate_head_relation(...)
    _relation_true_gap_cells(...)
    analyze_phase5(...)
    Phase-7 _memory_state(...)
    Phase-8b memory_stratum(...)
    phase-specific serialization, challenge construction, reports, and evaluation logic

Do not extract benchmark policy, epistemic partition construction, scene partition
construction, topology, relations, or attention policy in Core 3.

Do not begin Phase-9 attention work and do not diversify the scientific benchmark in this
structural refactor.

## Process addition requested by Luiz

Institutionalize one compact conversation-recovery habit in CLAUDE.md:

> At every accepted main milestone, maintain a compact Chat Handoff section or canonical
> handoff file that records the accepted main commit, the accepted scientific/architectural
> state, the active next step, and any decision-critical open items.

This is a process/documentation change only. It must not become a second source of truth:
GitHub code, contracts, and committed reports remain authoritative. The handoff is a compact
recovery index into that durable state.

No broad rewrite of CLAUDE.md is authorized.

## New checker

Add:

    tools/dev/check_conceptual_core3.py

It must be pure host-side Python/NumPy, deterministic, inexpensive, and fail-capable.

It must test at least:

1. HeadEvidence.empty field shapes, dtypes, and initial values.

2. A controlled patch whose samples map to known head-chart cells.

3. depth_seen accumulation and exact new_depth_cells/depth_cells deltas.

4. target_depth_seen and other_depth_seen semantics using a supplied target_id.

5. sample_count accumulation.

6. nearest-instance choice by metric range.

7. exact-distance tie breaking by smaller instance id.

8. ambiguity from two instance identities in one chart cell in one patch.

9. ambiguity accumulated across different patches/history.

10. out-of-domain valid measurements are excluded from valid_points and state updates.

11. compatibility identity:
       incidental.HeadEvidence is epistemic.head_memory.HeadEvidence
       incidental.add_head_patch is epistemic.head_memory.add_head_patch

12. direct imports in prefix_benchmark.py, integration.py, and challenge_suite.py come
    from fov3d.epistemic.head_memory rather than incidental.py.

13. no import from fov3d.epistemic into fov3d.experiments.

14. at least one explicit negative/mutation-style invariant capable of exposing a changed
    nearest-instance or target-relative rule.

The checker prints:

    [conceptual-core3-check] SUMMARY checked=<N> failed=0

and exits nonzero on failure.

## Allowed changes

Normally limited to:

    fov3d/epistemic/__init__.py
    fov3d/epistemic/head_memory.py
    fov3d/experiments/classroom_partition/incidental.py
    fov3d/experiments/classroom_partition/prefix_benchmark.py
    fov3d/experiments/classroom_partition/integration.py
    fov3d/experiments/classroom_partition/challenge_suite.py
    tools/dev/check_conceptual_core3.py
    docs/conceptual-core-map.md
    docs/migration-conceptual-core-3-report.md
    CLAUDE.md

No other production file should change without a concrete execution-discovered need inside
this extraction boundary and explicit documentation in the report.

Do not edit:

- relations.py / FineEvidence unless a real import break requires a purely mechanical fix;
- scene observation classes;
- protected sealed runtime files;
- golden signatures;
- scene assets;
- accepted preview/reference outputs;
- existing acceptance thresholds;
- existing phase checkers merely to accommodate the refactor.

## Execution-gate principle

Conceptual Core 2 established a hard methodology lesson:

    Every changed function or module-level dependency must be mapped to at least one
    execution gate that actually exercises it.

The final report must contain a changed-function/dependency -> gate coverage table.

Exact comparisons compare producer/evaluator outputs from the command under test, not
unrelated demo artifacts stored later in the same accepted directory.

Accepted references must follow the current lineage; in particular, the current Phase-3
reference is partition-graph-4-lift rather than the historically stale
partition-graph-3-full.

## Execution gates

Run in this order.

### A. Interactive structural gates

1. Compile every changed Python file.

2. Run:

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

### B. Phase-4 separation replay — interactive

Even though FineEvidence is intentionally untouched, replay Phase 4 to prove Core 3 has not
accidentally coupled the new persistent memory to the historical left-eye adapter:

    .venv/bin/python tools/partition_graph4_analyze.py       previews/partition-graph-2-source-full       previews/partition-graph-4-lift       previews/conceptual-core-3-phase4-full

Compare producer scope byte-for-byte against:

    previews/partition-graph-4-full

Use the same demonstrated exclusions as Conceptual Core 2 for post-producer demo artifacts.

### C. Phase-5 head-evidence replay — interactive/batch

Run:

    .venv/bin/python tools/partition_graph5_analyze.py       previews/partition-graph-2-source-full       previews/partition-graph-4-lift       previews/partition-graph-4-full       previews/conceptual-core-3-phase5-full

Required COMPLETE values:

    states = 104
    target_gap_violations = 0
    challenge_relations = 108
    challenge_states = 41
    challenge_targets = 4

Compare the 211-file producer scope byte-for-byte with:

    previews/partition-graph-5-full

excluding only the previously identified 7-file demo and 7-file demo-package-original
post-producer trees.

### D. Phase-7 proposer replay — batch

Run:

    .venv/bin/python tools/partition_graph7_propose.py       previews/partition-graph-2-source-full       previews/partition-graph-5-full       previews/partition-graph-6-proposals       previews/conceptual-core-3-phase7-proposals

Required COMPLETE values:

    states = 104
    targets = 25
    local_candidates = 8557
    global_candidates = 17202
    phase6_final_local_parity = 25
    truth_used = false

Compare the 835-file producer scope byte-for-byte with:

    previews/partition-graph-7-proposals

### E. Phase-7 evaluator replay — batch

Run the Phase-7 evaluator on accepted inputs to a fresh directory and require its complete
producer scope to be byte-identical to:

    previews/partition-graph-7-evaluation

Use:

    source_run = previews/partition-graph-2-source-full
    proposal_dir = previews/partition-graph-7-proposals
    phase6_evaluation_dir = previews/partition-graph-6-evaluation
    fresh = previews/conceptual-core-3-phase7-evaluation

The expected evaluator producer scope is 107 files after the already demonstrated demo
exclusions.

### F. Phase-8b proposer replay — batch

Run:

    .venv/bin/python tools/partition_graph8b_propose.py       previews/partition-graph-2-source-full       previews/partition-graph-5-full       previews/partition-graph-8-proposals       previews/conceptual-core-3-phase8b-proposals

Required COMPLETE values:

    scenarios = 5
    states = 125
    targets = 25
    full_phase8_parity = 25
    raw_candidates = 18469
    eligible_candidates = 6489
    truth_used = false

Compare the 503-file producer scope byte-for-byte with:

    previews/partition-graph-8b-proposals

### G. Phase-8b evaluator replay — batch

Run with:

    source_run = previews/partition-graph-2-source-full
    proposal_dir = previews/partition-graph-8b-proposals
    phase8_evaluation_dir = previews/partition-graph-8-evaluation
    fresh = previews/conceptual-core-3-phase8b-evaluation

Require the 3-file evaluator producer scope to be byte-identical to:

    previews/partition-graph-8b-evaluation

and preserve the accepted COMPLETE summary, including:

    full_eligible_recall = 0.9335820895522388

### H. Phase-8 proposer replay — explicitly authorized long gate

Core 3 necessarily changes integration.py's dependency on HeadEvidence/add_head_patch.
Therefore the Phase-8 proposer is a changed path and must be executed.

This approximately 11-minute gate is explicitly authorized by this contract despite being
above the normal five-minute Batch class, because it is the direct behavioral replay for a
modified Phase-8 module and Conceptual Core 2 demonstrated that unexecuted changed paths can
hide real defects.

Run:

    .venv/bin/python tools/partition_graph8_integrate.py       previews/partition-graph-2-source-full       previews/partition-graph-5-full       previews/partition-graph-7-proposals       previews/conceptual-core-3-phase8-proposals

Required COMPLETE values:

    states = 104
    targets = 25
    phase7_global_parity = 104
    target_evidence_unmapped_cells = 0
    candidate_regions = 16825
    truth_used = false

Compare the 468-file producer scope byte-for-byte with:

    previews/partition-graph-8-proposals

### I. Phase-8 evaluator replay — batch

Run with:

    source_run = previews/partition-graph-2-source-full
    proposal_dir = previews/partition-graph-8-proposals
    phase7_evaluation_dir = previews/partition-graph-7-evaluation
    fresh = previews/conceptual-core-3-phase8-evaluation

Require the 107-file evaluator producer scope to be byte-identical to:

    previews/partition-graph-8-evaluation

and preserve the accepted COMPLETE headline values, including:

    historical_state_misses = 101824
    integration_gain = 61557
    residual_candidate_recall = 0.955472222912062

## Comparison rule

For Gates B-I:

1. write only to fresh Core-3 output directories;
2. never modify accepted references;
3. identify the producer/evaluator file set from the fresh command output;
4. require every fresh file to exist at the accepted relative path;
5. require every corresponding file to be byte-identical;
6. require the accepted producer/evaluator scope to have no silently omitted file;
7. exclude only previously demonstrated post-producer demo/package artifacts and record
   every exclusion;
8. record file counts and a deterministic manifest/checksum in the report.

## Acceptance

Conceptual Core 3 passes only if all of the following hold:

- fov3d.epistemic.head_memory is the conceptual owner of HeadEvidence and add_head_patch;
- the implementation preserves all current field/update semantics exactly;
- target-relative fields remain unchanged and explicitly documented as such;
- FineEvidence and add_patch_observation remain experiment-side and unchanged;
- ObservationFootprint/ObservationOverlay remain in fov3d.scene;
- Phase 7/8/8b production code imports the persistent head memory directly from the
  conceptual module, not through incidental.py;
- incidental.py contains no duplicate HeadEvidence/add_head_patch implementation;
- no conceptual module imports the experiment package;
- the Core-3 checker passes and is demonstrably fail-capable;
- Core-1 and Core-2 checkers pass;
- existing Partition-Graph checkers 1-8b pass;
- facade, baseline verification, and golden comparison pass;
- golden comparison remains MISMATCHES 0;
- Gates B-I reproduce accepted producer/evaluator scopes byte-for-byte;
- every changed function/module dependency is covered by at least one actual execution
  gate and the mapping is recorded;
- protected runtime/reference files remain untouched;
- git diff --check is clean;
- no scientific/runtime behavior changes;
- CLAUDE.md contains only the bounded Chat-Handoff process addition requested by Luiz.

If exact parity fails, this is not a successful refactor. Diagnose before changing code.
Do not change acceptance criteria or accepted outputs.

## Permitted fixes

Claude Code may make minimal implementation repairs inside the extraction boundary.

It may:

- repair imports, typing, package initialization, checker defects, or mechanical extraction
  mistakes;
- add a compatibility re-export in incidental.py if needed;
- strengthen the Core-3 checker without weakening any acceptance gate;
- make a strictly mechanical correction required to execute the declared gates, documenting
  it separately.

It may not:

- redesign HeadEvidence;
- change target-relative versus target-neutral semantics;
- change chart mapping, chart resolution, or rounding;
- change valid-patch filtering;
- change nearest/ambiguity/sample-count behavior;
- change Phase-4 FineEvidence;
- change partition, benchmark, evaluator, candidate, attention, gaze, controller, matcher,
  fusion, renderer, scene, or termination semantics;
- edit accepted preview/reference trees;
- edit golden signatures;
- relax parity requirements.

If a repair would require any of those, stop and return the decision to Luiz and Chat.

## Report

Commit:

    docs/migration-conceptual-core-3-report.md

Include:

- branch and exact commit provenance;
- files changed;
- final public head-memory API and dependency direction;
- explicit documentation of target-neutral versus target-relative fields;
- compatibility/re-export decisions;
- repository-wide dependency audit;
- Core-3/Core-2/Core-1 checker summaries;
- phase-checker/facade/baseline/golden summaries;
- exact commands, runtimes, file counts, exclusions, and byte-parity results for Gates B-I;
- changed-function/dependency -> execution-gate table;
- every repair or deviation;
- confirmation that FineEvidence and observation overlay classes were not moved;
- confirmation that no scientific/runtime behavior changed;
- the bounded CLAUDE.md Chat-Handoff process addition;
- unresolved architectural questions;
- bounded recommendation for Conceptual Core 4 only.

Required success marker:

    CONCEPTUAL_CORE3_HEAD_MEMORY_PRESERVES_BEHAVIOR
