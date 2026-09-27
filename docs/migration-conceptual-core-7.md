# Migration Conceptual Core 7 — target-component lineage

## Status

This is a structural refactor only.

Parent accepted milestone:

    main @ e681392af8abc7d5fc6b2116a0c5bb534bc0ea7e

Scientific parent milestone:

    Conceptual Core 6 @ 41a365c49cbec52a350139238753b087b8f29da0

Active branch:

    migration/conceptual-core-7

Provenance: this contract records Luiz's Core-7 instruction. Claude Code committed it on
the branch **before** any production change, so its acceptance criteria are declared
before implementation and execution.

This step introduces none of the following:
- a new scientific hypothesis or lineage rule;
- a new overlap definition, component-label encoding or region ordering;
- new partition construction or relation classification;
- a new benchmark parameter or candidate policy;
- new gaze, controller, matcher, fusion or renderer behavior;
- a new scene asset, termination rule or evaluation meaning.

The governing migration rule remains:

    migrate behavior first; redesign structure second

## Conceptual boundary

Move the following literally, preserving behavior, from
`fov3d/experiments/classroom_partition/joint.py` to `fov3d/scene/lineage.py`:

    _lineage(prev_rc, curr_rc)
    _target_component_raster(graph, region_code, target_id)

Docstrings, comments and annotations are preserved.

`fov3d/scene/lineage.py` may depend only on `numpy` and
`fov3d.scene.model.ScenePartitionGraph`, plus the `typing.Any` annotation. It must not
import `fov3d.experiments`.

Do **not** modify `fov3d/scene/__init__.py`. Callers import explicitly with
`from fov3d.scene.lineage import ...`, so the accepted bare `fov3d.scene` import footprint
stays unchanged.

## Exact `_lineage` behavior to preserve

- `curr_rc` is coerced to `np.int32`. The positive current component codes are sorted
  numerically; zero and negative codes are excluded.
- When `prev_rc` is `None`, the result is `initial = True`, `births` = the number of
  positive current codes, and `merges = splits = deaths = persistent_links = 0`.
- Otherwise `prev_rc` is coerced to `np.int32`. A shape mismatch raises exactly
  `ValueError("lineage raster shape mismatch")`.
- The positive previous component codes are sorted numerically.
- Relations:
  - **parent**: previous component `pc` overlaps current component `cc`, meaning at
    least one shared cell;
  - **child**: the inverse relation.
- Counts:
  - **births**: current components with zero parents;
  - **merges**: current components with more than one parent;
  - **splits**: previous components with more than one child;
  - **deaths**: previous components with zero children;
  - **persistent_links**: current components with exactly one parent.
- The dictionary key order and value types are preserved exactly:

      initial, births, merges, splits, deaths, persistent_links

  In the initial branch, `initial` is `True` and every count is a Python `int`. In the
  non-initial branch, `initial` is `False` and every count is `int(...)`.

There is no IoU threshold, centroid matching, nearest-neighbor matching, identity
inference, temporal heuristic, or other redesign.

## Exact `_target_component_raster` behavior to preserve

- The output is an `int32` zero raster with `region_code.shape`.
- It looks up `graph.objects[str(target_id)]`; a missing object gives the all-zero
  raster.
- It enumerates `obj.region_ids` **in stored order**, starting at local label 1.
- For each region id it reads `graph.regions[rid].attributes["state_region_code"]` and
  assigns local label `k` to the cells with that state-local code.
- It does **not** sort `region_ids`, recompute connected components, or keep the
  state-global code as the output label.

The output is 0 for background or non-target cells, and `1..k` for the target-local
components.

## `joint.py`

- Remove the two implementations and import them from `fov3d.scene.lineage`.
- Keep them as compatibility identities:

      joint._lineage is fov3d.scene.lineage._lineage
      joint._target_component_raster is fov3d.scene.lineage._target_component_raster

- No duplicate implementations may remain.
- Everything else stays source-text unchanged, except imports genuinely orphaned by the
  extraction. That covers:
  - `StereoOps`, `_default_stereo_ops` and `build_joint_graph`;
  - the controller `seen_any` replay and observation footprints;
  - `attach_state_region_codes` and the corridor imports;
  - `_controller_expected_never`, `lift_joint_run`, and saved-run traversal and
    reporting.

`lift_joint_run` continues to compute
`current_target_labels = _target_component_raster(...)` and
`lineage = _lineage(previous_target_labels.get(iid), current_target_labels)`, and it keeps
maintaining `previous_target_labels` itself.

## Historical lineage patch tool: retirement

`tools/dev/apply_partition_graph4_lineage_fix.py` is a one-shot source-replacement repair
(commit `52c9395`) for the already accepted historical Phase-3 lineage bug
(`docs/partition-graph-4-report.md`). Once `_lineage` leaves `joint.py`, that patching
mechanism is obsolete. It is replaced by a **non-mutating tombstone** at the same path.
The tombstone explains that:
- the Phase-4 lineage fix is already incorporated;
- the accepted implementation now lives in `fov3d.scene.lineage`;
- Git history contains the original repair script.

When executed, it prints exactly:

    [partition-graph4-lineage-fix] RETIRED

and exits 0. It contains no source replacement and performs no repository write.

This retirement is intentional Core-7 cleanup, not a scientific change.

## Repository cleanup

Delete the stray `docs/core6-note.md`. It is a one-line placeholder from the interrupted
Core-6 writes and has no runtime meaning.

## Out of scope

Do not move, redesign or unify `relations.component_lineage`, which is a separate
accepted Phase-4 function.

Also leave untouched:
- `FineEvidence` and the Phase-4 relation classification;
- the controller `seen_any` replay;
- corridors, boundary extraction and scene partition construction;
- the Phase-2 boundary construction;
- benchmarks and evaluators;
- the target-relative `HeadEvidence` placement;
- gaze, controller, matcher, fusion, renderer and termination behavior;
- accepted outputs, golden signatures and thresholds.

## Allowed changes

    fov3d/scene/lineage.py
    fov3d/experiments/classroom_partition/joint.py
    tools/dev/apply_partition_graph4_lineage_fix.py (tombstone)
    tools/dev/check_conceptual_core7.py
    docs/core6-note.md (deletion)
    docs/migration-conceptual-core-7.md
    docs/migration-conceptual-core-7-report.md
    docs/conceptual-core-map.md

## Core-7 checker

Add `tools/dev/check_conceptual_core7.py`. It must be deterministic, inexpensive, run
host-side, and be able to fail. It covers at least:

1. `_lineage(None, curr)`: exact initial values, exact key order, and Python `bool`/`int`
   value types.
2. Stable persistence of one component: births 0, merges 0, splits 0, deaths 0,
   persistent_links 1.
3. A birth.
4. A death.
5. A merge: two previous components overlap one current component.
6. A split: one previous component overlaps two current components.
7. A mixed fixture that exercises several event counts at once.
8. `int32` coercion, and exclusion of zero and negative codes.
9. The exact shape-mismatch `ValueError` and its message.
10. `_target_component_raster` for a missing object: `int32`, the correct shape, all zero.
11. Stored `region_ids` order is preserved; the fixture uses a deliberately non-lexical,
    non-code order.
12. The exact `state_region_code` lookup.
13. Local labels are `1..k`.
14. Non-target cells stay zero.
15. Compatibility identities through `joint`.
16. `joint` contains no duplicate definitions.
17. `fov3d.scene.lineage` imports no `fov3d.experiments`.
18. A fresh bare `import fov3d.scene` does not load `fov3d.scene.lineage`, and keeps every
    Core-4/5/6 footprint invariant (no `cv2`, `partition`, `boundaries` or `corridors`).
19. The retired historical fix tool exits 0, prints the exact `RETIRED` marker, and
    contains no repository mutation or write behavior.

It prints:

    [conceptual-core7-check] SUMMARY checked=<N> failed=0

**Mutation testing** covers at least the following non-equivalent mutants:
- current codes not sorted, or wrong positive filtering;
- births counted from previous labels;
- merge threshold changed; split threshold changed;
- `persistent_links` counting `<= 1` parent instead of `== 1`;
- overlap test changed;
- a shape mismatch silently accepted;
- target `region_ids` sorted instead of stored order;
- the wrong `state_region_code` attribute;
- labels starting at 0;
- state-global codes used instead of target-local `1..k`;
- a missing target not returning the zero raster;
- a duplicate implementation in `joint.py`;
- `fov3d.scene.lineage` importing experiment code;
- the historical fix tool still mutating `joint.py`.

Only the Core-7 checker may be strengthened, and only if a genuine non-equivalent mutant
survives.

## Mechanical audit before replay

Prove all of the following:
1. Both moved functions are source-text identical to accepted main.
2. Their ASTs are identical.
3. Every referenced global binding is identical.
4. All remaining top-level definitions in `joint.py` are source-text identical.
5. `relations.py` is unchanged.
6. `relations.component_lineage` is unchanged.
7. The controller replay is unchanged.
8. Corridors, boundaries and partition are unchanged.
9. The Phase-2 boundary implementation is unchanged.
10. The old patch tool is **retired**, not accidentally broken.

## Execution gates

Run the gates in order.

### A. Interactive structural gates

1. Compile the changed Python files.
2. Run:

       .venv/bin/python tools/dev/check_conceptual_core7.py
       .venv/bin/python tools/dev/check_conceptual_core6.py
       .venv/bin/python tools/dev/check_conceptual_core5.py
       .venv/bin/python tools/dev/check_conceptual_core4.py
       .venv/bin/python tools/dev/check_conceptual_core3.py
       .venv/bin/python tools/dev/check_conceptual_core2.py
       .venv/bin/python tools/dev/check_conceptual_core1.py

3. Run the Partition-Graph checkers 1 through 8b.
4. Run:

       .venv/bin/python tools/dev/apply_partition_graph4_lineage_fix.py

   It must print exactly `[partition-graph4-lineage-fix] RETIRED`, and running it must
   leave the working tree unchanged.
5. Run:

       .venv/bin/python tools/dev/check_fov3d_facade.py
       scripts/verify_baseline.sh
       scripts/compare_golden.sh previews/partition-graph-2-source-full
       git diff --check

   It requires `[compare-golden] MISMATCHES 0`.
6. Run the fresh-process import probes.

### B. Phase-3 joint lift (primary lineage replay)

    .venv/bin/python tools/partition_graph3_lift.py previews/partition-graph-2-source-full previews/conceptual-core-7-phase3-full

All 419 producer files must be byte-identical to `previews/partition-graph-4-lift`. It
requires `states = 104`, `evidence_checks = 51` and `evidence_mismatches = 0`. This gate
directly executes both moved lineage functions across the accepted run.

### C. Phase-4 analyzer

    .venv/bin/python tools/partition_graph4_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/conceptual-core-7-phase4-full

The 211-file producer scope must be byte-identical to `previews/partition-graph-4-full`,
with the established demo exclusions.

### D. Phase-5 analyzer

    .venv/bin/python tools/partition_graph5_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/partition-graph-4-full previews/conceptual-core-7-phase5-full

The 211-file producer scope must be byte-identical to `previews/partition-graph-5-full`.

### E and F. Phase 8b

    .venv/bin/python tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals previews/conceptual-core-7-phase8b-proposals
    .venv/bin/python tools/partition_graph8b_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8b-proposals previews/partition-graph-8-evaluation previews/conceptual-core-7-phase8b-evaluation

All 503 proposer files and the 3-file evaluator scope must be byte-identical. It requires
`full_eligible_recall = 0.9335820895522388`.

## Conditional gates

First perform a repository-wide import/dependency audit. Phases 2, 6, 7 and 8 are not
automatically required. If the final Core-7 diff reaches an executable or import path of
any of them, replay the affected producer/evaluator. The approximately 11-minute Phase-8
proposer is authorized **only** if it is reached.

## Comparison discipline

- Use fresh outputs only, and never modify accepted references.
- Use two-sided file-set equality, with only the established `demo/` and
  `demo-package-original/` exclusions.
- Compare every file byte for byte.
- Record deterministic scope manifests
  (`LC_ALL=C find -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum`).
- Record the accepted-tree manifests before and after.

## Acceptance

Core 7 passes only if all of the following hold:
- `fov3d.scene.lineage` owns both functions, with preserved behavior;
- the `joint.py` compatibility identities hold and no duplicate remains;
- `fov3d/scene/__init__.py` is unchanged and the bare-import footprint holds;
- no `fov3d.scene` module imports `fov3d.experiments`;
- the historical patch tool is retired as specified;
- `docs/core6-note.md` is removed;
- `relations.py` (including `component_lineage`), the controller replay, corridors,
  boundaries, partition and the Phase-2 code are unchanged;
- the Core-7 checker passes and is demonstrably able to fail;
- the Core-1 to Core-6 checkers, the Partition-Graph checkers 1 to 8b, the facade check,
  the baseline and `git diff --check` pass;
- golden reports `MISMATCHES 0`;
- Gates B–F are byte-identical;
- the conditional-gate decision is recorded;
- every changed path maps to an executed gate;
- no scientific or runtime behavior changes.

If exact parity fails, diagnose before modifying code. Do not change the acceptance
criteria or the accepted outputs.

## Permitted fixes

The following are permitted:
- import, typing and checker repairs;
- literal-extraction corrections;
- compatibility aliases;
- strengthening the Core-7 checker;
- strictly mechanical corrections needed to run the gates, each documented separately.

Anything that changes lineage semantics, the label encoding, region ordering,
`relations.component_lineage`, the controller replay, corridors, boundaries, partition,
the Phase-2 code, benchmarks, evaluators, accepted outputs, golden signatures or
thresholds requires stopping and returning the decision to Luiz and Chat.

## Report

Commit `docs/migration-conceptual-core-7-report.md`. It covers:
- exact provenance and the files changed;
- the lineage API and dependency direction;
- the literal source, AST and global-binding audit;
- the explicit retirement of the patch tool;
- checker and mutation evidence;
- commands, runtimes and COMPLETE summaries;
- file counts, exclusions and manifests, and byte parity;
- changed-path → gate coverage and the conditional-gate decision;
- repairs and deviations;
- confirmation that `relations.component_lineage` is untouched;
- confirmation that the controller, corridor, boundary, partition and Phase-2 code is
  untouched;
- unresolved items;
- a bounded Core-8 recommendation.

Required success marker:

    CONCEPTUAL_CORE7_LINEAGE_PRESERVES_BEHAVIOR
