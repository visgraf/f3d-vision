# Migration Conceptual Core 10 — corridor relation-origin primitive

## Status

This is a structural migration only.

Accepted scientific milestone (parent):

    Conceptual Core 9 @ 518ff6ce4686238301f5ac946a5ea049e27ed9da

Administrative provenance:
- `origin/main` was fast-forwarded `f90f90a → 518ff6c` (Core 9 accepted by Luiz) with a
  plain, non-forced push.
- The Chat Handoff was then updated on main as `b69e0c900fa0b063fc8ecd39f689dc6452f29412`
  (parent `518ff6c`), from a detached administrative worktree that was removed
  afterwards.
- `migration/conceptual-core-10` was created from the new `origin/main` (`b69e0c9`).

Design provenance: Luiz and Chat. Claude Code committed this contract in the dedicated
isolated Core-10 worktree **before** any production change. Chat is the architecture and
review surface and does not mutate the repository. Claude Code is the execution and
mutation surface. Luiz is the scientific and acceptance authority.

The governing rules remain:

    migrate behavior first; redesign structure second
    one causal question only

## Causal question

Can the generic corridor relation-origin primitive be moved from the Classroom Phase-4
adapter into the generic scene corridor layer without changing any behavior?

## Bounded target and destination

Move **literally**, as one coherent cluster, from
`fov3d/experiments/classroom_partition/relations.py` to the existing
`fov3d/scene/corridors.py`:

    _region_code
    _own_labels
    _joint_region_own_component
    relation_origin

The destination is `fov3d.scene.corridors`, **not** `fov3d.scene.relations`, because:
- the relation is specifically about a gap corridor, classifying it as `ownership_cut`
  versus `own_support_gap`;
- its component computation uses `cv2.connectedComponents`, and `fov3d.scene.corridors`
  already owns the OpenCV-dependent local corridor geometry, with `cv2` as an accepted
  dependency;
- keeping `fov3d.scene.relations` NumPy/scene-model-only preserves the dependency
  boundary established by Core 9.

The result is descriptive scene structure, not attention or benchmark policy.

## Exact behavior to preserve

The four function bodies are preserved literally from accepted Core 9 (`518ff6c`),
including names, signatures, annotations, source text, exceptions and implementation
details.

**A. `_region_code(graph, rid)`** is `return int(graph.regions[rid].attributes["state_region_code"])`.
The direct `graph.regions` lookup, the exact attribute key, the `int(...)` conversion and
the existing `KeyError` behavior are kept. No validation or defaults are added.

**B. `_own_labels(layer_support)`** is
`cv2.connectedComponents(np.asarray(layer_support, np.uint8), connectivity=8)`. The
component count is ignored and the result is `labs.astype(np.int32)`. It is not
replaced by scipy, skimage, a custom flood fill, or another helper.

**C. `_joint_region_own_component(graph, state, rid, own_labels)`** keeps:
- the region code from `_region_code`;
- `np.asarray(state["region_code"], np.int32)` and the equality mask against that code;
- `np.unique(own_labels[m])`, discarding labels `<= 0`;
- the requirement of exactly one positive own-support component;
- the exact `RuntimeError` and message when `len(vals) != 1`;
- `return int(vals[0])`.

It is not broadened or reinterpreted.

**D. `relation_origin(graph, state, corridor, own_support)`** keeps:

    labs = _own_labels(own_support)
    a = _joint_region_own_component(graph, state, corridor["region_a"], labs)
    b = _joint_region_own_component(graph, state, corridor["region_b"], labs)
    return ("ownership_cut" if a == b else "own_support_gap", a, b)

The meanings stay descriptive. The same own-support component gives `"ownership_cut"`,
and different components give `"own_support_gap"`. These strings are not renamed, and no
policy implication is added.

## Explicit exclusions

Nothing else moves. The following stay experiment-side and unchanged:
- `FineEvidence`, `_mark`, `add_patch_observation`, `evidence_class_raster` and
  `evidence_class_counts`;
- `_stats`, `ownership_margin_descriptor` and `annotate_corridor`;
- `component_lineage` and `own_support_labels`;
- `_expected_depth_valid`, `_forbidden_source_path` and `analyze_phase4`;
- all stereo replay and saved-run logic.

`own_support_labels` is intentionally **not** unified with `_own_labels`, and
`component_lineage` is intentionally **not** unified with `fov3d.scene.lineage._lineage`.
Each is a separate future causal question.

The existing corridor functions `_component_boundary`, `_line_cells`, `gap_corridor` and
`corridors_for_object` are not altered. `fov3d/scene/__init__.py` is not modified.

## Dependency target

`fov3d.scene.corridors` already depends legitimately on `cv2`, `numpy`, `collections`,
`typing`, `fov3d.geometry.head_chart` and `fov3d.scene.model`. The four functions need
only `cv2`, `np` and builtins, plus `ScenePartitionGraph` and `Any` for annotations, all
of which the module already imports as the identical objects. **The import statements of
`fov3d/scene/corridors.py` therefore stay unchanged.**

It must not acquire any dependency on:
- `fov3d.experiments` or `fov3d.stereo`;
- reconstruction replay or saved-run adapters;
- benchmark or evaluation policy;
- renderer or Blender code.

A bare `import fov3d.scene` stays unchanged and OpenCV-free.

## Experiment adapter compatibility

- `fov3d.experiments.classroom_partition.relations._region_code`, `._own_labels`,
  `._joint_region_own_component` and `.relation_origin` are the **identical** function
  objects from `fov3d.scene.corridors`.
- No duplicate definitions remain.
- `annotate_corridor` resolves `relation_origin` to the `scene.corridors` object.
- Apart from the four removed definitions and the required import, every remaining
  top-level definition and non-import module statement of the adapter is source-text
  identical to accepted Core 9.
- Imports are removed only if genuinely orphaned. `cv2` stays (it is used by
  `own_support_labels`), as do `numpy` and `ScenePartitionGraph`.

## Allowed changes

    fov3d/scene/corridors.py                          (append the four literal segments)
    fov3d/experiments/classroom_partition/relations.py (remove four definitions; add the import)
    tools/dev/check_conceptual_core10.py
    docs/migration-conceptual-core-10.md
    docs/migration-conceptual-core-10-report.md
    docs/conceptual-core-map.md                        (only after the implementation and checker are complete)

## Core-10 checker

Add `tools/dev/check_conceptual_core10.py`. It must be deterministic, inexpensive, run
host-side, and be able to fail. It references the accepted implementation from Git at
`518ff6ce4686238301f5ac946a5ea049e27ed9da`, and checks at least:

**A. Literal migration**
- source-text and AST identity of the four definitions;
- equivalent `LOAD_GLOBAL` bindings;
- helpers inside `relation_origin` resolve to the `scene.corridors` functions.

**B. Adapter compatibility**
- four identity re-exports;
- `annotate_corridor` resolves the scene `relation_origin`;
- no duplicates remain.

**C. `_region_code`**
- an integer code, and a string or numeric-convertible code, with exact `int`
  conversion;
- a missing `state_region_code` raises `KeyError`;
- a missing rid keeps the existing lookup-failure behavior.

**D. `_own_labels`** (small hand-verifiable masks)
- 8- versus 4-connectivity, using diagonally touching foreground;
- background versus foreground, and multiple components;
- exact shape, `np.int32` dtype, and input conversion through `np.uint8`.

**E. `_joint_region_own_component`**
- exactly one positive component gives the right Python `int`;
- label 0 is ignored, and the region code selects the right cells;
- two positive labels give the exact `RuntimeError`, and so does no positive label;
- the state `region_code` is converted to `np.int32`;
- the exact message semantics.

**F. `relation_origin`**
- the same component gives `("ownership_cut", a, b)`, and different components give
  `("own_support_gap", a, b)`;
- the correct use of `region_a` and `region_b`, with the exact tuple order;
- Python `int` values for `a` and `b`;
- errors propagate rather than being swallowed.

**G. Dependencies and footprints**
- no experiment, stereo, reconstruction or benchmark import in `scene.corridors`;
- its import statements are unchanged from accepted Core 9;
- the bare `fov3d.scene` footprint and `fov3d/scene/__init__.py` are unchanged;
- no production module takes the four functions through the experiment adapter.

It prints:

    [conceptual-core10-check] SUMMARY checked=<N> failed=0

and exits nonzero on failure.

## Mutation classes

The final checker is mutation-tested **before** it is committed. It must catch meaningful
non-equivalent changes in at least these classes:

1. **Region-code lookup:** the wrong attribute name; a missing `int`; a default instead of
   `KeyError`.
2. **Own-label generation:**
   - connectivity 4 instead of 8;
   - the wrong input dtype or coercion, or the wrong output dtype;
   - foreground/background inversion;
   - incorrectly replaced `connectedComponents` semantics.
3. **Joint-region mapping:**
   - no region-code mask, or label 0 included;
   - multiple positive labels accepted, or the first label taken silently;
   - the wrong `len` condition, the wrong state key, or a missing `int32` conversion.
4. **Relation classification:**
   - equality reversed, or the strings swapped;
   - always `ownership_cut`, or always `own_support_gap`;
   - `region_a`/`region_b` swapped or duplicated;
   - the wrong tuple order, or a non-`int` component return.
5. **Package/static behavior:**
   - a duplicate adapter definition, or a missing identity import;
   - an experiment import from `scene.corridors`;
   - an eager `scene.corridors` import from `fov3d/scene/__init__.py`;
   - production code taking the primitive through the adapter.

Genuinely equivalent mutants are recorded separately. Checks are never weakened to
improve the mutation numbers.

## Isolation guard

All measured work runs in the dedicated `migration/conceptual-core-10` worktree. Before
and after every measurement, the branch must be `migration/conceptual-core-10`, HEAD must
be the expected commit, and the tracked tree must be clean. Any unexpected change
invalidates the measurement and stops the step. The shared checkout is not used.

## Execution gates

**A. Structural and interactive gates**, run under the guard:
- compile the changed Python files;
- run the Core-10 checker, then the Core-9 through Core-1 checkers;
- run the Partition-Graph checkers 1 through 8b, **unmodified**;
- run the facade check, `scripts/verify_baseline.sh` (sealed baseline 31/31),
  `scripts/compare_golden.sh previews/partition-graph-2-source-full` (`MISMATCHES 0`) and
  `git diff --check`;
- run fresh-process import footprints for `fov3d.scene`, `fov3d.scene.corridors` and the
  experiment relations adapter.

**Import/dependency audit.** Before any replay decision, record in fresh processes which
Partition-Graph producer/evaluator entry points load `fov3d.scene.corridors` or
`fov3d.experiments.classroom_partition.relations`. The expected result is Phase 3,
Phase 4 and Phase 8b, but it is *measured* at the Core-10 head. Phases 5, 2, 6, 7 and 8
are replayed only if the audit reaches them, and the Phase-8 proposer only if it is
reached.

**Replays:**
- **Phase 3**, if reached:

      .venv/bin/python tools/partition_graph3_lift.py previews/partition-graph-2-source-full previews/conceptual-core-10-phase3-full

  compared with `previews/partition-graph-4-lift`.
- **Phase 4**, required (`relation_origin` is actually called there):

      .venv/bin/python tools/partition_graph4_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/conceptual-core-10-phase4-full

  The 211-file producer scope is compared with `previews/partition-graph-4-full`, with
  only the `demo/` and `demo-package-original/` exclusions. The COMPLETE line is recorded,
  and the `relation_origin` execution count is instrumented on scratch output only.
- **Phase 8b** proposer and evaluator, if reached, with the accepted commands, references
  and exclusions (`partition-graph-8b-proposals`, `partition-graph-8b-evaluation`).

No unrelated phase is run for reassurance.

## Comparison discipline

- Use a fresh output directory, and treat accepted trees as read-only.
- Compare file sets in **both** directions, with no fresh files under excluded paths.
- Byte-compare every in-scope pair.
- Record deterministic `LC_ALL=C` manifests, and accepted-tree manifests before and after
  the replay sequence.
- Any unexpected mutation of an accepted tree invalidates the run.

## Acceptance

Core 10 passes only if all of the following hold:
- the four functions live in `fov3d.scene.corridors`, literally preserved from accepted
  Core 9 in source and AST, with equivalent global bindings;
- the experiment-side identities hold and `annotate_corridor` resolves the scene function;
- no duplicate implementation remains;
- the existing corridor functions, `own_support_labels`, `component_lineage` and
  `fov3d/scene/__init__.py` are unchanged;
- no new forbidden dependency enters `scene.corridors`;
- the Core-10 checker passes and is demonstrably able to fail;
- all earlier conceptual checkers and the Partition-Graph checkers pass;
- the baseline is 31/31 and golden reports `MISMATCHES 0`;
- the Phase-4 producer output and every audit-required replay are byte-identical;
- the accepted trees are unchanged;
- every changed production path maps to an executed gate.

## Permitted fixes

Only minimal mechanical import, wiring or checker defects inside the declared Core-10
scope may be fixed. If preserving behavior would require changing relation semantics,
corridor semantics, scene architecture outside the bounded target, accepted outputs,
benchmark or evaluation policy, or this contract, **stop and report**.

## Report and review

Commit `docs/migration-conceptual-core-10-report.md`. It records the following as
**unresolved/deferred**, not fixed:
- the `component_lineage` versus `_lineage` duplication;
- the `_own_labels` versus `own_support_labels` duplication;
- the `attach_state_region_codes` rename;
- the consumerless aliases;
- the target-relative `HeadEvidence` placement.

Then push, and stop for review by Luiz and Chat. Core 10 is not merged without Luiz's
explicit acceptance, and no Core-11 migration is made in this run.

Success marker:

    CONCEPTUAL_CORE10_RELATION_ORIGIN_PRESERVES_BEHAVIOR
