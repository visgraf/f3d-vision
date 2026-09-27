# Migration Conceptual Core 6 — gap-corridor topology

## Status

Structural refactor only.

Parent accepted milestone:

    main @ 6ff0da753acc8f20c84bf83e82c59db4f58de025

Scientific parent milestone:

    Conceptual Core 5 @ 6ff0da753acc8f20c84bf83e82c59db4f58de025

Active branch:

    migration/conceptual-core-6

Provenance of this contract. Chat started the Core-6 proposal: commits `118161a`,
`5e84db0` and `c049c7a` add `fov3d/scene/corridors.py`. Repository writes were then
interrupted before `joint.py`, the checker and the contract existed. On Luiz's explicit
instruction, Claude Code completed the proposal on the workstation: the `joint.py`
wiring, this contract, the checker and the handoff update. The boundary and acceptance
criteria below restate Luiz's Core-6 instruction and are declared **before** any
execution gate runs.

This step introduces no new scientific hypothesis, corridor definition, rasterization
rule, endpoint-selection rule, owner or evidence classification, relation interpretation,
partition construction rule, benchmark parameter, candidate policy, gaze policy,
controller behavior, matcher behavior, fusion behavior, renderer behavior, scene asset,
termination rule, or evaluation meaning.

The governing migration rule remains:

    migrate behavior first; redesign structure second

## Why this step

Conceptual Cores 4 and 5 moved scene-partition construction (`fov3d.scene.partition`)
and cell-side boundary extraction (`fov3d.scene.boundaries`) out of the historical
Phase-3 adapter `fov3d/experiments/classroom_partition/joint.py`.

The next stable block in that adapter is the local gap-corridor measurement:

    _component_boundary(...)
    _line_cells(...)
    gap_corridor(...)
    corridors_for_object(...)

These functions measure a descriptive straight bridge between two disconnected faces of
one object on an already-constructed scene graph and state raster. Their inputs are
generic scene data plus one explicit evidence mask:

    ScenePartitionGraph (regions with state_region_code, objects)
    state["region_code"], state["owner_instance"]
    seen_any (explicit boolean raster argument)
    controller-domain chart geometry, grid_deg

They do not depend on saved-run traversal, controller replay, calibration, lineage,
matcher/fusion/controller execution, or benchmark/evaluator policy.

The Core-5 report audit found:
- the four functions are used in production only inside `joint.py`, by
  `lift_joint_run`;
- they are also imported by the phase checkers 3 and 4;
- `relations.py` does not import them; Phase 4 consumes corridors only through the saved
  lift outputs.

## Conceptual boundary

Create:

    fov3d/scene/corridors.py

Move, as a literal behavior-preserving extraction from accepted main, preserving
docstrings, comments and annotations:

    _component_boundary
    _line_cells
    gap_corridor
    corridors_for_object

The module may depend only on:

    numpy
    cv2
    collections.Counter
    typing.Any
    fov3d.geometry.head_chart (chart_grid, head_unit_from_angles)
    fov3d.scene.model (ScenePartitionGraph)

It must not import `fov3d.experiments`.

Do not add these names to `fov3d.scene.__all__`, and do not modify
`fov3d/scene/__init__.py`. Callers import the module explicitly:

    from fov3d.scene.corridors import ...

## Exact behavior to preserve

### `_component_boundary(mask)`

- conversion to `uint8`;
- `cv2.erode` with a 3×3 all-ones kernel, `BORDER_CONSTANT`, `borderValue=0`;
- result `mask AND NOT eroded`, as a bool array.

### `_line_cells(y0, x0, y1, x1)`

- `n = max(|y1 − y0|, |x1 − x0|) + 1` with `int()` casts;
- `np.linspace` over each axis, then `np.rint`, then `int32`;
- `(y, x)` column order;
- adjacent-duplicate suppression only;
- a one-point line returns the single point unchanged.

### `gap_corridor(graph, state, region_a, region_b, target_id, seen_any, domain, grid_deg)`

- region codes resolved from `state_region_code` region attributes by scanning
  `np.unique(region_code)` and the graph regions in their existing order;
- `KeyError` when either code cannot be resolved; `RuntimeError` when either component
  boundary is empty;
- `cv2.batchDistance(..., cv2.CV_32F, normType=cv2.NORM_L2, K=1)` from boundary A to
  boundary B;
- the first `argmin` over A, and the returned nearest index into B;
- endpoint order `[A endpoint, B endpoint]`;
- rasterization by `_line_cells`, with the interior `line[1:-1]`, or empty when the line
  has at most 2 cells;
- endpoint angular gap computed with `chart_grid` and `head_unit_from_angles`, with the
  dot product clipped to [−1, 1] and `degrees(arccos(dot))`;
- interior owner counts:
  - `base_cells` for owner 0;
  - `same_object_cells` for owner `target_id`;
  - `other_object_cells`;
  - `other_object_counts` as a dict keyed by owner-id strings in sorted id order;
- interior evidence counts `seen_cells` and `unseen_cells` from the explicit `seen_any`;
- fractions over the interior count, `None` when the interior is empty;
- every returned key, value and type, including `corridor_yx` as a Python int list;
- the exact `semantics` string:
  `closest-boundary straight local bridge; descriptive only, not a policy or continuity claim`.

`seen_any` remains a plain explicit argument. `fov3d.scene.corridors` must not be coupled
to controller replay.

### `corridors_for_object(graph, state, target_id, seen_any, domain, grid_deg)`

- returns `[]` if the object is missing or has fewer than 2 region ids;
- keeps the `ObjectHypothesis.region_ids` order;
- enumerates all pairs `i < j` with the same nested loops;
- calls `gap_corridor` once per pair.

## What remains in `joint.py`

It keeps the following experiment-side and unchanged, except for imports:
- `StereoOps` and `_default_stereo_ops`;
- `build_joint_graph`;
- `_rectified_core_directions_h`, `update_controller_seen_any` and
  `_append_raw_footprints`, the controller `seen_any` replay;
- `attach_state_region_codes`;
- `_lineage` and `_target_component_raster`, the target-component lineage;
- `_controller_expected_never`;
- `lift_joint_run`, which covers saved-run traversal and Phase-3 report and state
  bookkeeping.

Only imports made genuinely unused by the extraction may be removed. Pre-existing unused
imports are left alone.

## Compatibility

The historical names remain importable from
`fov3d.experiments.classroom_partition.joint`:

    _component_boundary
    _line_cells
    gap_corridor
    corridors_for_object

They must be object-identical to the `fov3d.scene.corridors` definitions, and `joint.py`
must not duplicate them.

## Package boundary (Cores 4 and 5)

`fov3d/scene/__init__.py` is not modified. A fresh `import fov3d.scene` must not load any
of:

    cv2
    fov3d.scene.partition
    fov3d.scene.boundaries
    fov3d.scene.corridors

A fresh `import fov3d.scene.corridors` loads `cv2`, which the module legitimately needs,
but not `fov3d.scene.partition`.

## Deliberately out of scope

Do not move, redesign or unify:
- the Phase-4 relation classification, `FineEvidence` and `add_patch_observation`
  (`relations.py`);
- partition construction and boundary extraction;
- the Phase-2 boundary construction in `lift.py`;
- lineage and the controller `seen_any` replay;
- benchmark and evaluator policy;
- the target-relative epistemic-state placement;
- gaze, controller, matcher, fusion, renderer, termination and scene assets.

Do not rename serialized keys, strings or graph metadata.

## New checker

Add `tools/dev/check_conceptual_core6.py`. It must be deterministic, inexpensive, run
host-side, and be able to fail. At minimum it covers:

- `_component_boundary`: a single cell, a solid block, and an edge-touching block;
- `_line_cells`:
  - horizontal, vertical and diagonal lines;
  - shallow and steep slopes;
  - reversed endpoints and a one-point line;
  - the exact int32 `(y, x)` sequence;
- `gap_corridor`:
  - the missing-region-code `KeyError` and the empty-boundary `RuntimeError`;
  - the exact closest endpoint pair, `corridor_yx`, `endpoint_gap_deg` and interior count;
  - the base, same-target and other-object counts, with sorted string-keyed
    `other_object_counts`;
  - the seen/unseen counts and fractions, and `None` fractions for an empty interior;
  - the exact semantics string;
- `corridors_for_object`: `[]` for a missing or single-region object, and the pair count
  and order for 3 or more regions;
- compatibility identity through `joint`, and no duplicate definitions in `joint.py`;
- no experiment import from `fov3d.scene.corridors`;
- fresh-process package footprints, as specified above.

The checker prints:

    [conceptual-core6-check] SUMMARY checked=<N> failed=0

and exits nonzero on failure. It must be mutation-tested at least against these changes:
- erosion kernel or border;
- line rounding;
- x/y reversal;
- endpoint reversal;
- closest-pair selection;
- region-code lookup;
- owner composition and seen composition;
- pair order;
- the semantics string.

It is strengthened if a non-equivalent mutant survives.

## Allowed changes

    fov3d/scene/corridors.py
    fov3d/experiments/classroom_partition/joint.py
    tools/dev/check_conceptual_core6.py
    docs/migration-conceptual-core-6.md
    docs/migration-conceptual-core-6-report.md
    docs/conceptual-core-map.md
    docs/chat-handoff.md

Do not edit:
- `fov3d/scene/__init__.py`;
- `relations.py` and the Phase-2 code in `lift.py`;
- existing phase checkers;
- sealed runtime files;
- golden signatures and scene assets;
- accepted preview/reference outputs;
- acceptance thresholds.

## Mechanical audit (before execution)

The following must be shown, by source text and AST:
- the four moved functions are identical to accepted main except for module ownership;
- every referenced global has the same binding;
- the rest of `joint.py` is unchanged except for its imports;
- `relations.py`, the Phase-2 code in `lift.py`, the controller `seen_any` replay and the
  lineage are unchanged.

## Execution gates

Run in order.

### A. Interactive structural gates

1. Compile the changed Python files.
2. Run:

       .venv/bin/python tools/dev/check_conceptual_core6.py
       .venv/bin/python tools/dev/check_conceptual_core5.py
       .venv/bin/python tools/dev/check_conceptual_core4.py
       .venv/bin/python tools/dev/check_conceptual_core3.py
       .venv/bin/python tools/dev/check_conceptual_core2.py
       .venv/bin/python tools/dev/check_conceptual_core1.py

3. Run the Partition-Graph checkers 1 through 8b.
4. Run:

       .venv/bin/python tools/dev/check_fov3d_facade.py
       scripts/verify_baseline.sh
       scripts/compare_golden.sh previews/partition-graph-2-source-full
       git diff --check

   It requires `[compare-golden] MISMATCHES 0`.

### B. Phase-3 joint lift (primary)

    .venv/bin/python tools/partition_graph3_lift.py previews/partition-graph-2-source-full previews/conceptual-core-6-phase3-full

All 419 files must be byte-identical to `previews/partition-graph-4-lift`. It requires
`states = 104`, `evidence_checks = 51` and `evidence_mismatches = 0`.

### C. Phase-4 analyzer

    .venv/bin/python tools/partition_graph4_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/conceptual-core-6-phase4-full

The 211-file producer scope must be byte-identical to `previews/partition-graph-4-full`,
with the demonstrated `demo/` and `demo-package-original/` exclusions.

### D. Phase-5 analyzer

    .venv/bin/python tools/partition_graph5_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/partition-graph-4-full previews/conceptual-core-6-phase5-full

The 211-file producer scope must be byte-identical to `previews/partition-graph-5-full`,
with the demonstrated exclusions. It requires `states = 104`,
`target_gap_violations = 0`, `challenge_relations = 108`, `challenge_states = 41` and
`challenge_targets = 4`.

### E. Phase-8b proposer

    .venv/bin/python tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals previews/conceptual-core-6-phase8b-proposals

All 503 files must be byte-identical to `previews/partition-graph-8b-proposals`. It
requires:

    scenarios = 5
    states = 125
    targets = 25
    full_phase8_parity = 25
    raw_candidates = 18469
    eligible_candidates = 6489
    truth_used = false

### F. Phase-8b evaluator

    .venv/bin/python tools/partition_graph8b_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8b-proposals previews/partition-graph-8-evaluation previews/conceptual-core-6-phase8b-evaluation

The 3-file evaluator scope must be byte-identical to `previews/partition-graph-8b-evaluation`,
and it requires `full_eligible_recall = 0.9335820895522388`.

## Conditional gates

Perform an import/dependency audit first. Phases 2, 6, 7 and 8 are required only if
`fov3d/scene/__init__.py` changes, or if their import paths reach `joint` or
`fov3d.scene.corridors`. In that case the affected producer/evaluator path is replayed
exactly as in the accepted Core-4 report. The approximately 11-minute Phase-8 proposer is
authorized only if the audit shows that Core 6 reaches it.

## Comparison rule

The comparison uses the Core-3/4/5 method:
- fresh output directories only, and accepted trees never modified;
- a two-sided file-set equality after excluding only the demonstrated post-producer
  `demo/` and `demo-package-original/` trees;
- byte identity for every file;
- scope manifests computed as
  `LC_ALL=C find -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum`;
- accepted-tree manifests recorded before and after.

## Acceptance

Core 6 passes only if all of the following hold:
- `fov3d.scene.corridors` owns the four functions, with preserved behavior;
- the `joint.py` compatibility names are identities, with no duplicates;
- `seen_any` remains an explicit argument;
- `fov3d/scene/__init__.py` is unchanged and the package footprints hold;
- no `fov3d.scene` module imports `fov3d.experiments`;
- `relations.py`, the lineage, the controller replay, the Phase-2 boundaries, partition
  construction and benchmark policy are unchanged;
- the Core-6 checker passes and is demonstrably able to fail;
- the Core-1 to Core-5 checkers, the Partition-Graph checkers 1 to 8b, the facade check,
  the baseline and `git diff --check` pass;
- golden reports `MISMATCHES 0`;
- Gates B–F are byte-identical;
- the conditional-gate decision is recorded;
- every changed function and module dependency maps to an executed gate;
- no scientific or runtime behavior changes.

If exact parity fails, diagnose before modifying code. Do not change the acceptance
criteria or the accepted outputs.

## Permitted fixes

The following are permitted:
- import, typing and checker repairs;
- literal-extraction corrections;
- compatibility aliases;
- strengthening the Core-6 checker without weakening any gate;
- strictly mechanical corrections needed to execute the gates, each documented
  separately.

The following are not permitted:
- changing corridor semantics, rasterization, endpoint selection, owner or evidence
  counts, returned keys, or the semantics string;
- coupling corridors to controller replay;
- modifying `fov3d/scene/__init__.py`;
- moving or changing the relation logic, lineage, controller replay, Phase-2 boundaries,
  partition construction, benchmark or evaluator policy;
- editing accepted outputs or golden signatures;
- relaxing parity.

If a repair would need any of those, stop and return the decision to Luiz and Chat.

## Report

Commit `docs/migration-conceptual-core-6-report.md`. It covers:
- provenance and the exact files changed;
- the literal-extraction audit and the dependency/import audit;
- checker and mutation evidence;
- all commands, runtimes and COMPLETE summaries;
- file counts, exclusions, manifests and byte parity;
- the changed-path → execution-gate table and the conditional-gate decision;
- repairs and deviations;
- confirmation that `seen_any` stays explicit and that `relations.py`, the lineage, the
  controller replay and the Phase-2 boundaries are unchanged;
- a bounded Core-7 recommendation.

Required success marker:

    CONCEPTUAL_CORE6_GAP_CORRIDORS_PRESERVE_BEHAVIOR
