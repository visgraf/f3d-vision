# Migration Conceptual Core 9 — generic boundary depth-order relation primitive

## Status

This is a structural migration only.

Parent accepted milestone:

    main @ f90f90af48a385b8b808e69d45629955bb8f4be2   (accepted Core 8 + Chat Handoff update)

Scientific parent milestone:

    Conceptual Core 8 @ 3877857c3a355851413cdfaa55c5dd05ad8bdab4

Active branch:

    migration/conceptual-core-9

Provenance: this contract records the Core-9 design by Luiz and Chat. Claude Code
committed it in the dedicated isolated `migration/conceptual-core-9` worktree **before**
any production change. Chat reads, designs and reviews only; Claude Code performs every
mutation and measurement.

The governing rule remains:

    migrate behavior first; redesign structure second

## The causal question

Can the generic scene-graph boundary depth-order relation primitive be moved out of the
Phase-4 Classroom adapter without changing behavior?

## Bounded target

Move **literally**, as one coherent cluster, from
`fov3d/experiments/classroom_partition/relations.py` to the new
`fov3d/scene/relations.py`:

    _region_object(graph, rid) -> int | None
    _weighted_quantile(values, weights, q) -> float | None
    boundary_depth_order(graph, target_id, interveners) -> dict[str, Any]

The experiment module imports these three names from `fov3d.scene.relations` and keeps
exposing and using them compatibly. The only in-repository consumer of the cluster is
`annotate_corridor`, which calls `boundary_depth_order`. `_region_object` and
`_weighted_quantile` are used only by `boundary_depth_order`.

## Preserve literally

The following are preserved literally:
- function names and signatures, source text, docstrings/comments (there are none), and
  the existing type annotations, even where imperfect;
- `_region_object`: returns `None` unless the region is `OBJECT_COMPONENT` with a
  non-`None` `object_id`; otherwise returns `int(object_id)`;
- `_weighted_quantile`:
  - returns `None` for empty `values`;
  - converts values and weights to `float64` and sorts with `np.argsort(values)`;
  - takes `cumsum` of the weights and returns `None` when the total is `<= 0`;
  - otherwise returns
    `float(v[np.searchsorted(c, q * c[-1], side="left")])`;
- `boundary_depth_order`:
  - iterates over `sorted(int(v) for v in interveners if int(v) != int(target_id))`;
  - considers only `OBJECT_OBJECT` boundaries, in `graph.boundaries` order;
  - matches the pair `{oa, ob} == {target, other}` through `_region_object`;
  - reads `int(...)` votes from `nearer_region_a_votes`/`nearer_region_b_votes`
    (default 0) and orients them by whether `oa == target`;
  - accumulates `interface_edge_count` (default 0) as `int`;
  - collects `depth_jump_median_m` only when present and `nedge > 0`, weighted by `nedge`;
  - counts every matched chain;
  - writes the per-intervener result keyed by `str(other)`, with the exact field names,
    order and types:
    - `boundary_chain_count`, `interface_edge_count`, `target_nearer_votes`,
      `intervener_nearer_votes`;
    - `intervener_nearer_vote_fraction` (`None` when there are 0 votes);
    - `depth_order_confidence_abs_vote_balance` (`None` when there are 0 votes);
    - `depth_jump_interface_weighted_median_m` (q = 0.5);
    - `depth_jump_interface_weighted_p90_m` (q = 0.9).
- All numerical behavior.

## Do not

- Rename anything, fix annotations, or add validation.
- Alter the quantile or relation semantics, or change `BoundaryKind`/`RegionKind`
  behavior.
- Move `FineEvidence`, the stereo replay, `add_patch_observation`, evidence
  classification, `relation_origin`, `ownership_margin_descriptor`, `annotate_corridor` or
  `component_lineage`.
- Change benchmark or evaluation policy, modify `fov3d/scene/__init__.py`, redesign
  relations, or touch accepted historical outputs.

## Dependency target

`fov3d.scene.relations` is a small generic scene module that depends only on what the
three functions need: `numpy`, `typing.Any`, and the scene model types `BoundaryKind`,
`RegionKind` and `ScenePartitionGraph` from `fov3d.scene.model`. It must not acquire
`cv2`, stereo, experiment, reconstruction-replay, saved-run, benchmark, renderer or
evaluation dependencies. It is imported explicitly and is not added to
`fov3d.scene.__all__`.

## Experiment module

- Remove the three definitions from `fov3d/experiments/classroom_partition/relations.py`
  and import them from `fov3d.scene.relations`.
- Compatibility identities: `relations._region_object`, `relations._weighted_quantile` and
  `relations.boundary_depth_order` are the scene objects, and no duplicate definition
  remains.
- Apart from imports, every remaining top-level definition and module statement stays
  source-text identical to accepted Core 8. Only imports genuinely orphaned by the
  extraction may be removed.

## Allowed changes

    fov3d/scene/relations.py
    fov3d/experiments/classroom_partition/relations.py
    tools/dev/check_conceptual_core9.py
    docs/migration-conceptual-core-9.md
    docs/migration-conceptual-core-9-report.md
    docs/conceptual-core-map.md   (after the implementation and checker are complete)

## Core-9 checker

Add `tools/dev/check_conceptual_core9.py`. It must be deterministic, inexpensive, run
host-side, and be able to fail. It establishes at least:

1. The source-text and AST identity of the three moved definitions against accepted
   Core 8 (`3877857`), read from Git.
2. Equivalent global bindings.
3. The experiment-side identity imports, and no duplicate definitions.
4. Direct `boundary_depth_order` behavior on the important cases:
   - object-region filtering, including `BASE` and object-less regions;
   - target/intervener orientation on both chain sides;
   - vote accumulation over several chains;
   - edge accumulation and chain counts;
   - zero-vote `None` fields;
   - depth-jump collection, skipped when absent or when `nedge` is 0;
   - edge weighting, and the weighted median/p90 including the searchsorted boundary;
   - intervener filtering (the target excluded, int conversion, sorted order);
   - non-`OBJECT_OBJECT` boundaries ignored;
   - the exact return keys and their order.
5. The bare `import fov3d.scene` footprint is unchanged and OpenCV-free, and
   `fov3d.scene.relations` is not loaded.
6. An explicit `import fov3d.scene.relations` pulls in no experiment, stereo or `cv2`
   machinery.

It prints:

    [conceptual-core9-check] SUMMARY checked=<N> failed=0

and exits nonzero on failure.

**Mutation evidence** must show that the checker detects meaningful changes in:
- object-region filtering;
- target/intervener orientation;
- vote accumulation;
- chain and edge accumulation;
- zero-vote handling;
- depth-jump collection;
- edge weighting;
- weighted median and p90 behavior;
- intervener filtering;
- the return and key structure.

Equivalent mutants are recorded separately. Only the Core-9 checker may be strengthened.

## Execution isolation

Every edit and measurement runs in the dedicated `migration/conceptual-core-9` worktree
under the standard guard. Before and after each measured command, the branch must be
`migration/conceptual-core-9`, HEAD must be the expected commit, and the tracked tree must
be clean. Any unexpected change invalidates the measurement and stops the step.

## Execution gates

### A. Interactive structural gates

1. Compile the changed Python files.
2. Run the Core-9 through Core-1 checkers.
3. Run the Partition-Graph checkers 1 through 8b, **unmodified**.
4. Run `tools/dev/check_fov3d_facade.py`, `scripts/verify_baseline.sh` (sealed baseline
   31/31), `scripts/compare_golden.sh previews/partition-graph-2-source-full` (which must
   end with `[compare-golden] MISMATCHES 0`), and `git diff --check`.
5. Run fresh-process import probes for `fov3d.scene` and `fov3d.scene.relations`.

### B. Phase-4 relation product (primary)

Regenerate the accepted Phase-4 relation product through the normal accepted path:

    .venv/bin/python tools/partition_graph4_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/conceptual-core-9-phase4-full

The 211-file producer scope must be byte-identical to `previews/partition-graph-4-full`,
with only the established `demo/` and `demo-package-original/` exclusions. The accepted
COMPLETE values must be reproduced. The number of `boundary_depth_order` executions is
recorded where practical.

### Conditional replays

Use the repository-wide import/dependency audit to determine which later phases the final
Core-9 diff actually reaches. Replay a producer or evaluator path only if it is reached;
do not run unrelated phases merely for reassurance. The approximately 11-minute Phase-8
proposer is authorized only if it is reached.

## Comparison discipline

- Use fresh Core-9 output directories only, and never modify accepted trees.
- Require two-sided file-set equality, with only the established exclusions and no fresh
  file beneath an excluded path.
- Compare every file byte for byte.
- Record deterministic `LC_ALL=C` scope manifests, and accepted-tree manifests before and
  after.

## Acceptance

Core 9 passes only if all of the following hold:
- `fov3d.scene.relations` owns the three functions, literally preserved;
- the experiment-side identities hold and no duplicate remains;
- `fov3d/scene/__init__.py` is unchanged and the footprints hold;
- no scene module imports `fov3d.experiments`, `cv2` or stereo machinery;
- the out-of-scope code is unchanged;
- the Core-9 checker passes and is demonstrably able to fail;
- the Core-1 to Core-8 checkers, the unmodified Partition-Graph checkers 1 to 8b, the
  facade check, the baseline (31/31) and `git diff --check` pass;
- golden reports `MISMATCHES 0`;
- Gate B is byte-identical;
- the conditional replays are decided by the audit and recorded;
- every changed path maps to an executed gate;
- all work ran isolated and guarded.

## Permitted fixes

Only minimal mechanical import or wiring defects inside the declared Core-9 scope may be
fixed. If preservation would require changing relation behavior, architecture, accepted
outputs, evaluation semantics or this contract, **stop and report**.

## Report

Commit `docs/migration-conceptual-core-9-report.md`, recording:
- the exact commands and commits;
- the checks and mutation results;
- the comparisons and the conditional-replay decision;
- the coverage table;
- any deviations.

Then commit and push, and stop for review by Luiz and Chat.

Success marker:

    CONCEPTUAL_CORE9_RELATIONS_PRESERVE_BEHAVIOR
