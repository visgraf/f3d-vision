# Migration Conceptual Core 8 — graph/raster state-code consistency

## Status

This is a structural migration only. It is intentionally tiny.

Parent accepted milestone:

    main @ 7855ff3b4691781f1f3d8e49f690b26c7ff30fa3   (accepted Core 7 + Chat Handoff update)

Scientific parent milestone:

    Conceptual Core 7 @ 3603266b299236359f0539a778ac98f65cd11887

Active branch:

    migration/conceptual-core-8

Provenance: this contract records the Core-8 design by Luiz and Chat. Claude Code
committed it **before** any production change, in the dedicated isolated worktree of
`migration/conceptual-core-8`. Chat reads, designs and reviews only; Claude Code performs
every mutation and measurement.

The governing rule remains:

    migrate behavior first; redesign structure second

## Bounded target

    attach_state_region_codes(graph: ScenePartitionGraph, region_code: np.ndarray) -> ScenePartitionGraph

- **Current owner:** `fov3d/experiments/classroom_partition/joint.py`
- **Conceptual owner after Core 8:** `fov3d/scene/state_validation.py`

The name is historically misleading, because the function attaches nothing. Do **not**
rename it in Core 8. A future compatibility cleanup may rename it, for example to
`validate_state_region_codes`. This migration preserves the source text, signature,
exception behavior and object identity exactly.

## Exact behavior to preserve

The accepted implementation, moved **literally**:

    def attach_state_region_codes(graph: ScenePartitionGraph, region_code: np.ndarray) -> ScenePartitionGraph:
        """Validate the construction-time raster code carried by every region."""
        codes = {int(c) for c in np.unique(region_code)}
        graph_codes = {int(r.attributes.get("state_region_code", -1)) for r in graph.regions.values()}
        if -1 in graph_codes or graph_codes != codes:
            raise RuntimeError(f"graph/raster region-code mismatch: graph={sorted(graph_codes)} raster={sorted(codes)}")
        graph.validate()
        return graph

It preserves exactly:
1. The raster codes come from `np.unique(region_code)`.
2. Every raster code is converted with Python `int(...)`.
3. The graph codes come from **every** graph region.
4. The attribute lookup is exactly `r.attributes.get("state_region_code", -1)`.
5. Every graph code is converted with Python `int(...)`.
6. A missing `state_region_code` therefore contributes the sentinel `-1`.
7. The failure condition is exactly `-1 in graph_codes or graph_codes != codes`.
8. The comparison is **set** equality.
9. The exception type is exactly `RuntimeError`.
10. The error text is exactly
    `graph/raster region-code mismatch: graph=<sorted graph code list> raster=<sorted raster code list>`.
11. `graph.validate()` runs **only** after the code-set check succeeds.
12. Exceptions from `graph.validate()` propagate unchanged.
13. A successful return is the **same** graph object, not a copy.
14. Neither the graph nor `region_code` is mutated.

Do **not** introduce any of the following:
- multiplicity checking, or one-region-per-code validation;
- shape or dimensionality checking;
- connectivity or ownership checking;
- code-ordering, contiguous-numbering or positive-only requirements;
- region filtering.

**Accepted subtlety.** Because the function compares *sets*, duplicate
`state_region_code` values on distinct regions are **not** rejected by this helper. If
`graph.validate()` otherwise accepts such a graph and the code sets agree, the helper
accepts it. This is part of the accepted implementation. Do not "fix" it in Core 8.

## Module boundary

Create `fov3d/scene/state_validation.py`. It may depend only on `numpy` and
`fov3d.scene.model.ScenePartitionGraph`. It must **not** import `fov3d.experiments`.

Do **not** modify `fov3d/scene/__init__.py`. Callers import explicitly with
`from fov3d.scene.state_validation import attach_state_region_codes`, so the bare
`import fov3d.scene` footprint stays unchanged.

## `joint.py`

- Remove the implementation, and import the exact conceptual function from
  `fov3d.scene.state_validation`.
- Keep the historical compatibility identity:
  `joint.attach_state_region_codes is state_validation.attach_state_region_codes`.
- No duplicate definition may remain.
- Apart from imports, every remaining definition in `joint.py` stays source-text
  identical to accepted Core-7 main. That covers `build_joint_graph`, `StereoOps`,
  `_default_stereo_ops`, `_rectified_core_directions_h`, `update_controller_seen_any`,
  `_append_raw_footprints`, `_controller_expected_never` and `lift_joint_run`.

`lift_joint_run` still executes `graph = attach_state_region_codes(graph, state["region_code"])`
at the same location.

## Out of scope

Do not move or redesign:
- `ScenePartitionGraph.validate()`;
- partition construction, boundary extraction, gap corridors, target-component lineage;
- the controller `seen_any` replay;
- the Phase-4 relations, `FineEvidence` and `HeadEvidence`;
- the Phase-2 boundaries;
- benchmark and evaluator policy;
- observation overlays and saved-run traversal;
- gaze, controller, matcher, fusion, renderer and termination behavior.

Do not rename the function, and do not modify accepted serialized outputs.

## Allowed changes

    fov3d/scene/state_validation.py
    fov3d/experiments/classroom_partition/joint.py
    tools/dev/check_conceptual_core8.py
    docs/migration-conceptual-core-8.md
    docs/migration-conceptual-core-8-report.md
    docs/conceptual-core-map.md   (only after the implementation and checker are complete)

## Core-8 checker

Add `tools/dev/check_conceptual_core8.py`. It must be deterministic, inexpensive, run
host-side, and be able to fail. It covers at least:

1. **Valid match.** The raster code set equals the graph code set; the call returns, and
   the returned object **is** the graph passed in.
2. **Graph extra code.** A code is present in the graph but absent from the raster:
   `RuntimeError` with the exact sorted diagnostic.
3. **Raster extra code.** A code is present in the raster but absent from the graph:
   `RuntimeError` with the exact sorted diagnostic.
4. **Missing attribute.** One region lacks `state_region_code`, so the graph codes include
   `-1`: the exact `RuntimeError` diagnostic.
5. **Sentinel semantics.** `-1` in the graph codes fails even when the raster also
   contains `-1`.
6. **Python `int` conversion.** Values whose `int(...)` conversion is observable are used
   for both raster values and graph attributes.
7. **Set semantics.** Duplicate raster occurrences do not matter.
8. **Accepted duplicate-graph-code semantics.** Two otherwise valid regions carrying the
   same code are accepted when the sets match. This locks the accepted behavior against
   an accidental "improvement".
9. **Error precedence.** For a code-set mismatch in a graph that would also fail
   `graph.validate()`, the code-set `RuntimeError` comes first.
10. **Graph validation on match.** For matching code sets on a graph that
    `graph.validate()` rejects, the original `validate()` exception propagates.
11. **No mutation** of the graph or `region_code`, after both success and failure.
12. **Raster shape is not validated here.** Only unique values are used; no
    dimensionality contract is imposed.
13. **Empty case.** An empty graph with an empty raster gives exactly the result
    `ScenePartitionGraph.validate()` produces.
14. **Joint compatibility identity.**
15. **No duplicate definition** in `joint.py`.
16. `state_validation` imports no `fov3d.experiments`.
17. A fresh bare `import fov3d.scene` does not load `fov3d.scene.state_validation`, and
    keeps every Core-4/5/6/7 footprint invariant.
18. A fresh direct `import fov3d.scene.state_validation` stays NumPy-only, with no `cv2`.
19. **Existing Phase-3 checker compatibility.** `tools/dev/check_partition_graph3.py` is
    unmodified and still imports `attach_state_region_codes` through `joint.py`.

It prints:

    [conceptual-core8-check] SUMMARY checked=<N> failed=0

and exits nonzero on failure.

## Mutation testing

The following non-equivalent mutants are tested at least:
- `.get(..., -1)` changed to another sentinel, or the explicit `-1` guard removed;
- a subset or superset comparison replacing equality;
- comparison before `int` conversion, or a missing `int` conversion on graph or raster
  values;
- duplicate graph codes newly rejected;
- `graph.validate()` removed, or moved before the code-set check;
- `return None`, or returning a copy or new graph;
- the error type changed, the error text or its order changed, or `sorted(...)` removed
  or changed in the diagnostics;
- region filtering introduced, or a shape/dimensionality restriction introduced;
- a duplicate implementation reintroduced in `joint.py`;
- `state_validation` importing experiment code;
- an eager export through `fov3d/scene/__init__.py`.

Only `check_conceptual_core8.py` may be strengthened, and only if a genuine
non-equivalent mutant survives. Equivalent mutants are recorded separately rather than
forced into artificial tests.

## Mechanical audit before replay

Prove all of the following:
1. The source text of `attach_state_region_codes` is byte-identical between accepted
   Core-7 `joint.py` and the new `state_validation.py`.
2. The AST is identical.
3. The referenced globals `np` and `ScenePartitionGraph` resolve equivalently.
4. Every remaining top-level definition in `joint.py` is source-text identical to
   accepted Core 7.
5. `fov3d/scene/__init__.py` is unchanged.
6. `partition.py`, `boundaries.py`, `corridors.py` and `lineage.py` are unchanged.
7. `relations.py` is unchanged.
8. The controller replay is unchanged.
9. The Phase-2 boundary implementation is unchanged.

## Execution isolation

Every edit and measurement runs in the dedicated `migration/conceptual-core-8`
worktree. Each measurement command is guarded before **and** after: the current branch
must be `migration/conceptual-core-8`, HEAD must be the expected commit, and the tracked
tree must be clean. Any unexpected change **invalidates that measurement and stops the
step**. The shared `/home/lvelho/rd/f3d-vision` checkout is not a measured execution
surface.

## Execution gates

### A. Interactive structural gates

1. Compile every changed Python file.
2. Run the Core-8 through Core-1 checkers.
3. Run the Partition-Graph checkers 1 through 8b, **unmodified**.
4. Run the facade check, `scripts/verify_baseline.sh`,
   `scripts/compare_golden.sh previews/partition-graph-2-source-full` and
   `git diff --check`. Golden must report `[compare-golden] MISMATCHES 0`.
5. Run fresh-process import probes for `fov3d.scene` and
   `fov3d.scene.state_validation`.

### B. Phase-3 joint lift (primary execution)

    .venv/bin/python tools/partition_graph3_lift.py previews/partition-graph-2-source-full previews/conceptual-core-8-phase3-full

All 419 producer files must be byte-identical to `previews/partition-graph-4-lift`. It
requires `states = 104`, `evidence_checks = 51` and `evidence_mismatches = 0`.
`attach_state_region_codes` must execute on every map-present Phase-3 state before the
graph is serialized. The number of calls and states exercised is recorded where
practical.

### C. Phase-4 analyzer

    .venv/bin/python tools/partition_graph4_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/conceptual-core-8-phase4-full

The 211-file producer scope must be byte-identical to `previews/partition-graph-4-full`,
with only the established demo exclusions. This gate also loads `joint.py` through
`relations.py`.

### D and E. Phase 8b

`challenge_suite` imports `build_joint_graph` from `joint.py`, so Core 8 changes the
module dependency path Phase 8b loads.

    .venv/bin/python tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals previews/conceptual-core-8-phase8b-proposals
    .venv/bin/python tools/partition_graph8b_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8b-proposals previews/partition-graph-8-evaluation previews/conceptual-core-8-phase8b-evaluation

All 503 proposer files and the 3-file evaluator scope must be byte-identical. The
accepted COMPLETE values must hold, including `full_eligible_recall = 0.9335820895522388`.

## Conditional gates (tighter than earlier contracts)

Phase 5 normally imports neither `joint.py` nor `state_validation`. It is **not** run by
habit. First perform the repository-wide import/dependency audit. Phase 5 runs only if
the final Core-8 diff actually reaches its executable or import path. Phases 2, 6, 7 and 8
are likewise conditional only. The approximately 11-minute Phase-8 proposer is authorized
**only** if the audit shows that the final Core-8 diff reaches it.

## Comparison discipline

- Use only fresh Core-8 output directories, and never modify accepted trees.
- Require two-sided file-set equality, with only the established demo/package
  exclusions and zero fresh files beneath excluded paths.
- Compare every file byte for byte.
- Record deterministic scope manifests
  (`LC_ALL=C find -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum`).
- Record accepted-tree manifests before and after.

## Conceptual map

Update `docs/conceptual-core-map.md` only after the implementation and checker are
complete. It records:
- Cores 1–7 as accepted, and Core 8 as proposed or measured;
- `fov3d.scene.state_validation` as the owner of `attach_state_region_codes`, with
  `joint.py` keeping only the compatibility import;
- that the misleading historical name is preserved during the behavior migration and the
  rename is deferred;
- that topology/relations remains the next larger conceptual boundary.

## Acceptance

Core 8 passes only if all of the following hold:
- `fov3d.scene.state_validation` owns the function, with literal preserved behavior;
- the `joint.py` identity holds and no duplicate remains;
- `fov3d/scene/__init__.py` is unchanged and the footprints hold;
- no `fov3d.scene` module imports `fov3d.experiments`;
- the out-of-scope code is unchanged;
- the Core-8 checker passes and is demonstrably able to fail;
- the Core-1 to Core-7 checkers, the unmodified Partition-Graph checkers 1 to 8b, the
  facade check, the baseline and `git diff --check` pass;
- golden reports `MISMATCHES 0`;
- Gates B–E are byte-identical;
- the conditional-gate decision is recorded;
- every changed path maps to an executed gate;
- every measurement ran isolated and guarded;
- no scientific or runtime behavior changes.

If exact parity fails, diagnose before modifying code. Do not change the acceptance
criteria or the accepted outputs.

## Permitted fixes

The following are permitted:
- import and checker repairs;
- literal-extraction corrections;
- the compatibility alias;
- strengthening the Core-8 checker;
- strictly mechanical corrections needed to run the gates, each documented separately.

Anything that changes validation semantics, the name, the signature, the exceptions, the
out-of-scope code, accepted outputs, golden signatures or thresholds requires stopping and
returning the decision to Luiz and Chat.

## Report

Commit `docs/migration-conceptual-core-8-report.md`. It covers:
- provenance, the accepted Core-7 parent, and the exact main/handoff/branch sequence;
- the isolated-worktree execution details and the exact files changed;
- source, AST and global-binding identity, and the state-validation API and dependency
  direction;
- checker results, mutation evidence, and the accepted duplicate-code subtlety;
- Gate-A summaries, replay commands, runtimes and COMPLETE lines;
- file counts, exclusions, manifests, byte parity, and the accepted-tree manifests before
  and after;
- the import audit and the conditional-gate decision;
- changed-path → gate coverage;
- repairs and deviations;
- confirmation that no other scene, topology, controller or relation behavior changed;
- unresolved items;
- a bounded Core-9 recommendation.

Required success marker:

    CONCEPTUAL_CORE8_STATE_VALIDATION_PRESERVES_BEHAVIOR

Commit and push `migration/conceptual-core-8`. Do **not** merge Core 8 into main. Stop and
report to Luiz and Chat for review.
