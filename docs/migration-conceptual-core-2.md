# Migration Conceptual Core 2 — head-centered spherical chart extraction

## Status

Structural refactor only.

Parent accepted milestone:

    main @ 485f696ad8f19bed9f63bda70e3a294a3b2dfc7b

Active branch:

    migration/conceptual-core-2

This step introduces no new scientific hypothesis, coordinate convention, chart resolution,
association radius, observation semantics, partition semantics, benchmark parameter, gaze
policy, controller behavior, matcher behavior, fusion behavior, renderer behavior, scene
asset, or evaluation meaning.

Its purpose is to continue migration Step 5 by promoting two de-facto shared concepts out
of the historical Classroom/Partition-Graph lineage:

1. the fixed-head yaw/pitch chart convention used throughout Phases 2-8b;
2. the frozen 12 mm metric surface-association radius currently duplicated in experiment
   modules.

## Why this step

The current Classroom package defines the project-wide head chart privately inside
`fov3d/experiments/classroom_partition/lift.py`:

    _head_angles_from_unit
    _head_unit_from_angles
    _grid
    _cells

Those helpers are imported directly or indirectly by later Phase modules. The implementation
has therefore become architecture while still being owned by historical experiment code.

The current repository also has two independent definitions of:

    FUSION_RADIUS_M = 0.012

in `lift.py` and `benchmark.py`, with downstream imports through those historical modules.

Both are migration Step-5 problems: stable concepts are hidden behind phase lineage.

## Important coordinate-system distinction

Do **not** fold this convention into `fov3d.scene.sphere`.

`fov3d.scene.sphere` intentionally exposes a generic lon/lat convention. Conceptual Core 2
extracts the project's fixed head-frame convention:

    +X = head right
    +Y = head up
    -Z = forward

with:

    yaw   = atan2(x, -z)
    pitch = atan2(y, hypot(x, z))

and inverse:

    x = sin(yaw) * cos(pitch)
    y = sin(pitch)
    z = -cos(yaw) * cos(pitch)

Angles remain degrees.

No semantic unification of these two spherical conventions is attempted here.

## New conceptual modules

Create:

    fov3d/geometry/head_chart.py
    fov3d/reconstruction/association.py

### `fov3d.geometry.head_chart`

The public surface should be small and functional:

    head_angles_from_unit(...)
    head_unit_from_angles(...)
    chart_grid(...)
    chart_cells(...)

The implementation must preserve the current numerical behavior exactly, including:

- float64 calculations;
- row normalization behavior used by the old helper;
- NumPy broadcasting behavior of the inverse mapping;
- `np.rint` cell rounding;
- inclusive grid sizing:
      round((max-min)/grid_deg) + 1
- returned array shapes and ordering;
- current handling of non-finite angles in the in-chart mask.

Do not introduce a chart class, seam abstraction, alternate projection, validation policy,
or changed boundary convention in this step.

### `fov3d.reconstruction.association`

Create one canonical constant:

    SURFACE_ASSOCIATION_RADIUS_M = 0.012

This is the frozen metric radius used by historical map support and 12-mm coverage queries.

The conceptual module must not add any new fusion algorithm or support calculation.

Where backward compatibility requires the historical name:

    FUSION_RADIUS_M

an experiment module may retain a simple alias to the canonical constant. There must be no
second numeric definition of 0.012 for this concept.

## Required dependency cleanup

At minimum inspect and refactor:

    fov3d/experiments/classroom_partition/lift.py
    fov3d/experiments/classroom_partition/joint.py
    fov3d/experiments/classroom_partition/relations.py
    fov3d/experiments/classroom_partition/incidental.py
    fov3d/experiments/classroom_partition/benchmark.py
    fov3d/experiments/classroom_partition/prefix_benchmark.py
    fov3d/experiments/classroom_partition/integration.py
    fov3d/experiments/classroom_partition/challenge_suite.py

Required outcomes:

- production code no longer imports `_grid`, `_cells`, `_head_angles_from_unit`, or
  `_head_unit_from_angles` from `lift.py`;
- Phase 7/8/8b code no longer obtains chart helpers indirectly through `benchmark.py`;
- production code uses the new public head-chart API directly;
- production code that needs the 12-mm constant uses the canonical association module
  directly;
- `lift.py` and `benchmark.py` may retain compatibility aliases only if existing
  public/checker behavior requires them;
- no new cross-phase import is introduced.

Before final acceptance, run a repository-wide search and record every remaining occurrence
of the four old private chart names and every remaining `FUSION_RADIUS_M` definition/import.
Any remaining use must be either:
- an intentional backward-compatibility alias/check; or
- a documented item requiring a decision.

## Deliberately out of scope

Do not move or redesign:

- `ObservationFootprint` / `ObservationOverlay`;
- `HeadEvidence`;
- `FineEvidence`;
- camera-footprint construction;
- visibility rasterization;
- support-depth rasterization;
- scene partition construction;
- topology / relation extraction;
- epistemic region construction;
- benchmark or evaluator logic.

Do not modify `fov3d.scene.sphere` except for a strictly necessary documentation link, and
no such change is expected.

## New checker

Add:

    tools/dev/check_conceptual_core2.py

It must be pure host-side Python/NumPy and fail-capable.

It must test at least:

1. fixed-head anchor directions:
       [ 0, 0,-1] -> yaw   0, pitch 0
       [+1, 0, 0] -> yaw +90, pitch 0
       [-1, 0, 0] -> yaw -90, pitch 0
       [ 0,+1, 0] -> pitch +90
       [ 0,-1, 0] -> pitch -90

2. angle -> unit -> angle round trips on non-polar samples;

3. unit -> angle -> unit round trips, including non-unit input directions, preserving the
   old normalization semantics;

4. broadcast behavior of `head_unit_from_angles`;

5. exact chart dimensions for the accepted Classroom domain:
       yaw   [-25, +25]
       pitch [-20, +20]
       grid  0.10 deg
       shape 401 x 501;

6. exact cell mapping for chart center, corners, and just-outside points;

7. current `np.rint` rounding behavior at half-cell cases;

8. non-finite yaw/pitch are excluded by the returned `ok` mask;

9. canonical association radius is exactly:
       0.012 m

10. compatibility aliases, if retained, equal the canonical constant and point to the same
    chart behavior;

11. one deliberate negative/mutation check proving that a changed frame sign, cell rounding,
    or association constant would fail.

The checker prints a deterministic summary and exits nonzero on failure.

## Allowed changes

Normally limited to:

    fov3d/geometry/head_chart.py
    fov3d/reconstruction/association.py
    fov3d/experiments/classroom_partition/*.py
    tools/dev/check_conceptual_core2.py
    docs/conceptual-core-map.md
    docs/migration-conceptual-core-2-report.md

Do not edit protected sealed runtime files, golden signatures, scene assets, or accepted
preview/reference outputs.

Existing phase checkers should not be weakened or rewritten to accommodate the refactor.
A minimal import-only checker update requires explicit justification in the report.

## Execution gates

Run in this order.

### A. Interactive structural gates

1. Compile all changed Python files.

2. Run:

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

### B. Exact producer replay — Phase 2 lift

Run the Phase-2 lift with accepted source:

    source = previews/partition-graph-2-source-full

to a fresh directory:

    previews/conceptual-core-2-phase2-full

using:

    tools/partition_graph2_lift.py

Require:
- 104 graphs;
- 25 targets/objects represented as in the accepted run;
- truth remains unopened;
- every file produced by the fresh lift exists at the same relative path in
  `previews/partition-graph-2-full`;
- every corresponding producer file is byte-identical.

The accepted Phase-2 tree may contain later demo/analysis artifacts. Comparison scope is
the complete fresh producer output, plus a two-sided check against accepted files that are
demonstrably part of the lift output. Exclude only independently identified post-lift
artifacts and record them.

### C. Exact producer replay — Phase 3 joint lift

Run:

    tools/partition_graph3_lift.py

with:

    source = previews/partition-graph-2-source-full
    fresh  = previews/conceptual-core-2-phase3-full

Compare producer output against:

    previews/partition-graph-3-full

Required headline invariants include:

    states = 104
    evidence_checks = 51
    evidence_mismatches = 0

and byte-identical producer-scope output.

### D. Exact producer replay — Phase 5 head evidence

Run:

    tools/partition_graph5_analyze.py

with accepted inputs:

    source_run = previews/partition-graph-2-source-full
    lift_dir   = previews/partition-graph-4-lift
    phase4_dir = previews/partition-graph-4-full
    fresh      = previews/conceptual-core-2-phase5-full

Required COMPLETE values:

    states = 104
    target_gap_violations = 0
    challenge_relations = 108
    challenge_states = 41
    challenge_targets = 4

Compare producer-scope output byte-for-byte with:

    previews/partition-graph-5-full

### E. Exact producer replay — Phase 7 proposer

Run:

    tools/partition_graph7_propose.py

with:

    source_run          = previews/partition-graph-2-source-full
    phase5_dir          = previews/partition-graph-5-full
    phase6_proposal_dir = previews/partition-graph-6-proposals
    fresh               = previews/conceptual-core-2-phase7-proposals

Required COMPLETE summary:

    states = 104
    targets = 25
    local_candidates = 8557
    global_candidates = 17202
    phase6_final_local_parity = 25
    truth_used = false

Compare producer-scope output byte-for-byte with:

    previews/partition-graph-7-proposals

### F. Exact producer replay — Phase 8b proposer

Run:

    tools/partition_graph8b_propose.py

with:

    source_run          = previews/partition-graph-2-source-full
    phase5_dir          = previews/partition-graph-5-full
    phase8_proposal_dir = previews/partition-graph-8-proposals
    fresh               = previews/conceptual-core-2-phase8b-proposals

Required COMPLETE summary:

    scenarios = 5
    states = 125
    targets = 25
    full_phase8_parity = 25
    raw_candidates = 18469
    eligible_candidates = 6489
    truth_used = false

Compare producer-scope output byte-for-byte with:

    previews/partition-graph-8b-proposals

### G. Conditional Phase-8 long replay

Do **not** run the approximately 11-minute Phase-8 integrator by default.

Run it only if:
- one of Gates B-F fails in a way that may involve the extracted chart/association logic; or
- static dependency review shows a Phase-8-only code path that is not exercised by the other
  gates.

If required, use the exact Conceptual Core 1 Phase-8 parity contract and require the accepted
468-file producer output to match byte-for-byte.

## Producer-scope comparison rule

For all replay gates, compare the files produced by the command under test, not unrelated
demo or supplementary artifacts later stored beneath the same accepted directory.

Strict requirements:

1. every fresh producer file exists in the accepted tree at the same relative path;
2. every corresponding file is byte-identical;
3. no accepted file known to be produced by the command may be silently omitted;
4. excluded accepted paths must be listed with evidence that they are post-producer
   demo/analysis artifacts;
5. neither accepted nor fresh trees may be modified during comparison.

This rule incorporates the evaluator-scope lesson from Conceptual Core 1.

## Acceptance

This step passes only if all of the following hold:

- the new head-chart module is the conceptual owner of the fixed-head yaw/pitch mapping;
- the new association module is the single numeric source of the 12-mm radius;
- no production phase depends on private chart helpers owned by `lift.py`;
- no later phase obtains chart helpers indirectly through `benchmark.py`;
- no second numeric 0.012 definition remains for this concept;
- the new fail-capable checker passes;
- Conceptual Core 1 checker passes;
- existing checkers 1-8b pass;
- facade and baseline verification pass;
- golden comparison remains `MISMATCHES 0`;
- Phase 2, 3, 5, 7 and 8b fresh producer outputs reproduce the accepted producer-scope
  outputs byte-for-byte;
- protected runtime files and accepted outputs remain untouched;
- `git diff --check` is clean;
- no scientific/runtime behavior changes.

If exact parity fails, this is not a successful refactor. Diagnose and repair only inside
the delegated structural scope; do not change acceptance criteria or reference outputs.

## Permitted fixes

Claude Code may make minimal implementation repairs inside the extraction boundary.

It may not:

- alter the head-frame convention;
- alter chart resolution or cell rounding;
- alter the 12-mm radius;
- change support, coverage, partition, topology, epistemic, benchmark, or evaluator semantics;
- edit accepted preview/reference trees;
- edit golden signatures;
- change controller, matcher, fusion, renderer, gaze, termination, or scene behavior;
- expand the step into observation-state or partition extraction.

If parity appears to require any of those, stop and return the decision to Luiz and Chat.

## Report

Commit:

    docs/migration-conceptual-core-2-report.md

Include:

- branch and exact commit provenance;
- files changed;
- final public chart API;
- canonical association API;
- repository-wide dependency audit results;
- checker/facade/baseline/golden summaries;
- exact commands and runtimes for replay Gates B-F;
- producer file counts, exclusions, and byte-parity results;
- any repair or deviation;
- whether Gate G was required and why;
- confirmation that no scientific/runtime behavior changed;
- unresolved architectural questions;
- bounded recommendation for Conceptual Core 3 only.

Required success marker:

    CONCEPTUAL_CORE2_HEAD_CHART_PRESERVES_BEHAVIOR
