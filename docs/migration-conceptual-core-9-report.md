# Migration Conceptual Core 9 — report (2026-09-27)

Executed by Claude Code on the Ubuntu workstation against the committed contract
`docs/migration-conceptual-core-9.md`. Every number below is **MEASURED** from the
command shown, unless it is marked otherwise.

## Causal question and answer

*Can the generic scene-graph boundary depth-order relation primitive be moved out of the
Phase-4 Classroom adapter without changing behavior?*

**Yes.** The evidence:
- `_region_object`, `_weighted_quantile` and `boundary_depth_order` now live in
  `fov3d/scene/relations.py`;
- they are source-text and AST identical to accepted Core 8, with equivalent global
  bindings;
- the regenerated Phase-4 relation product is byte-identical to `partition-graph-4-full`,
  from 484 executions of the primitive;
- golden reports `MISMATCHES 0` and the baseline is 31/31.

## Provenance: main, handoff and branch sequence

| step | result |
|---|---|
| pre-check (fetch) | `origin/main = 7855ff3b4691781f1f3d8e49f690b26c7ff30fa3`, `origin/migration/conceptual-core-8 = 3877857c3a355851413cdfaa55c5dd05ad8bdab4`, both verified. `7855ff3` is an ancestor; Core 8 is 5 ahead and 0 behind. `CLAUDE.md` is unchanged |
| **Core 8 accepted** (Luiz and Chat) | `origin/main` fast-forwarded `7855ff3..3877857` by a plain, non-forced push of the exact commit |
| handoff | in a detached administrative worktree at the new main: `docs/chat-handoff.md` commit `f90f90af48a385b8b808e69d45629955bb8f4be2` (parent `3877857`), pushed as a fast-forward to `main`; the administrative worktree was then removed |
| branch | `migration/conceptual-core-9` created at `f90f90a` from the **new** `origin/main`, both remote and local |
| Core-9 commits | `7166db3` contract, **committed before any production change** · `fea06c1` extraction · `70afe24` checker · `86e3e9c` conceptual map · the commit that adds this report |
| gates measured at | Gate A and Gate B at `70afe24`; the whole of Gate A again at `86e3e9c`. `fov3d/` and `tools/` are identical at both |
| accepted Core-8 parent | `3877857` (`CONCEPTUAL_CORE8_STATE_VALIDATION_PRESERVES_BEHAVIOR`) |
| final head | the commit that adds this report |

The handoff records:
- Core 8 accepted at `3877857`;
- `fov3d.scene.state_validation` ownership, with `attach_state_region_codes` keeping its
  compatibility name;
- Conceptual Core 9 as the active step;
- the working arrangement, in which Chat reads, designs and reviews only and Claude Code
  mutates and measures only in isolated worktrees.

## Isolated-worktree execution

- **Where it ran.** Every Core-9 edit and measurement ran in the dedicated worktree
  `<scratchpad>/core9/wt` on `migration/conceptual-core-9`.
- **Data links.** The untracked data are symlinked in: `previews/`, `.venv/`, and the five
  ignored `scenes/classroom/` asset entries. `fov3d` resolves to the worktree's code, with
  no `.pth` redirect.
- **Guard.** Every measurement ran under the guard, which requires, before and after,
  branch `migration/conceptual-core-9`, the expected HEAD, and a clean tracked tree. It
  never tripped.
- **Shared checkout.** `/home/lvelho/rd/f3d-vision` was not used for measured work and its
  branch was not switched. It stayed on local `main` at `e681392`, behind `origin/main`, as
  before.

## Files changed (main f90f90a...final head)

| file | change |
|---|---|
| `docs/migration-conceptual-core-9.md` | contract (`7166db3`) |
| `fov3d/scene/relations.py` | new: `_region_object`, `_weighted_quantile` and `boundary_depth_order`, generated from the exact source segments of accepted Core-8 `relations.py` (`fea06c1`) |
| `fov3d/experiments/classroom_partition/relations.py` | three definitions removed (60 lines). It gains `from fov3d.scene.relations import _region_object, _weighted_quantile, boundary_depth_order`, and `from fov3d.scene import BoundaryKind, RegionKind, ScenePartitionGraph, support_depth_from_map` narrows to `ScenePartitionGraph, support_depth_from_map`, because only those two orphaned names left (`fea06c1`) |
| `tools/dev/check_conceptual_core9.py` | new checker (`70afe24`) |
| `docs/conceptual-core-map.md` | Core-9 status, `relations.py` row and order (`86e3e9c`) |
| `docs/migration-conceptual-core-9-report.md` | this report |

The following are untouched (`git diff f90f90a..HEAD` is empty for each):
- `fov3d/scene/__init__.py`, `model.py` (so `BoundaryKind` and `RegionKind` are
  unchanged), `partition.py`, `boundaries.py`, `corridors.py`, `lineage.py`,
  `state_validation.py`, `sphere.py` and `synthetic.py`;
- `joint.py`, `lift.py`, `incidental.py`, `integration.py`, `challenge_suite.py`,
  `benchmark.py` and `prefix_benchmark.py`;
- `fov3d/epistemic`, `fov3d/geometry` and `fov3d/reconstruction`;
- every other tool and checker, including the Partition-Graph checkers 1–8b, which are
  unmodified;
- `scripts/`, `tests/`, `CLAUDE.md` and `docs/chat-handoff.md` on the branch;
- sealed runtime files;
- the 13 accepted trees.

## Relation-primitive API and dependency direction

    numpy, typing.Any
    fov3d.scene.model   BoundaryKind, RegionKind, ScenePartitionGraph
            -> fov3d.scene.relations      (explicit import; NOT in fov3d.scene.__all__)
                   _region_object(graph, rid) -> int | None
                   _weighted_quantile(values, weights, q) -> float | None
                   boundary_depth_order(graph, target_id, interveners) -> dict[str, Any]
            -> fov3d.experiments.classroom_partition.relations
                   annotate_corridor  (the only in-repository consumer)
                   <- analyze_phase4 (Phase 4): per-state at relations.py:402, scene-final at :460

Fresh-process footprints (`python -I`, in the worktree):
- `import fov3d.scene` loads exactly `fov3d`, `fov3d.scene`, `fov3d.scene.model` and
  `fov3d.scene.sphere`. It does not load `cv2`, `partition`, `boundaries`, `corridors`,
  `lineage`, `state_validation` or `relations`.
- `import fov3d.scene.relations` adds only `fov3d.scene.relations`. It loads no `cv2`, no
  `fov3d.experiments.*`, no `fov3d.stereo.*` and no other scene module.

## Literal source / AST / global-binding identity

1. **Source text.** The segments of the three functions in `fov3d/scene/relations.py` are
   **byte-identical** to accepted Core-8 `relations.py` (`3877857`). The module was
   generated from those exact segments. Annotations are kept as they were: there were no
   docstrings or comments, and nothing was "fixed".
2. **AST.** The ASTs are identical.
3. **Global bindings.** `np`, `Any`, `BoundaryKind`, `RegionKind` and
   `ScenePartitionGraph` are the same objects as in the Core-8 adapter. The Core-9 checker
   compares every `LOAD_GLOBAL` name of the three functions (`RegionKind`, `BoundaryKind`,
   `np`, the two helpers, and the builtins `int`, `float`, `abs`, `sorted` and `str`)
   against the executed Core-8 adapter. `boundary_depth_order` resolves its helpers in
   `fov3d.scene.relations`, and `annotate_corridor` resolves `boundary_depth_order` to the
   scene function.
4. **The rest of the adapter is unchanged.** All 17 remaining top-level definitions of the
   adapter are source-text identical to Core 8, as are all non-import module statements.
   That includes `FineEvidence`, `add_patch_observation`, the evidence classification,
   `relation_origin`, `ownership_margin_descriptor`, `annotate_corridor`,
   `component_lineage` and `analyze_phase4`.
5. `fov3d/scene/relations.py` imports only `__future__`, `typing`, `numpy` and `.model`. A
   `symtable` scan finds 0 unbound globals in it and in the adapter.

## Compatibility

`relations._region_object`, `relations._weighted_quantile` and
`relations.boundary_depth_order` in the experiment adapter are the same objects as in
`fov3d.scene.relations`, with no duplicates; the checker asserts this.
`tools/dev/check_partition_graph4.py` (unmodified) reads the `"boundary_depth_order"`
result key produced by `annotate_corridor`. No production module takes the primitive
through the adapter; the checker enforces this.

## Checker and mutation evidence

`tools/dev/check_conceptual_core9.py` has **24 checks** and runs in about 0.3 s wall.

| area | checks |
|---|---|
| identity | source text and AST identical to Core 8 (read with `git show 3877857:...`); equivalent `LOAD_GLOBAL` bindings against the executed Core-8 adapter; adapter identity re-exports; no duplicates |
| `_weighted_quantile` | `None` for empty values and for a total ≤ 0; values sorted with their weights (`[0.9, 0.1, 0.3]/[5, 1, 4]` gives 0.3); `side='left'` on an exact cumulative boundary (`[1, 5, 10]`, target 5, gives 0.3, a Python `float`); q = 0 |
| `_region_object` | an `int` id for object components; `None` for BASE (even when carrying an id) and for an object-less component |
| `boundary_depth_order` | Fixture: target `np.int64(7)`, interveners `{np.int64(12), 7, 9, 30.0, 33, 40}`, whose raw set iteration is `[33, 7, 40, 9, 12, 30]`. Decoy chains must all be ignored: a wrong kind, a BASE region, an object-less component, a BASE region with an id, an other–other pair and a target–target pair. Checks: keys `["9", "12", "30", "33", "40"]`; exact per-intervener key order. Intervener 9: 5 chains, 13 edges, votes 9/3 with both orientations, fraction 0.25, balance 0.5, and edge-weighted median 0.1 and p90 0.9 (weights 6/1/3; the `nedge = 0` jump and the missing jump are skipped). Intervener 12: zero votes give `None` fractions. Intervener 40: a chain without `interface_edge_count`, and jumps 0.1–0.4 with weights 4/2/3/1 (cumulative 4, 6, 9, 10) giving median 0.2 and p90 0.3. Interveners without chains give zero counts and `None`s. Also Python `int`/`float` types, and empty or target-only interveners |
| dependencies and footprints | allowed imports only; no production import through the adapter; fresh bare `fov3d.scene` footprint; fresh `fov3d.scene.relations` loads no `cv2`, experiment, stereo or other scene module |

**Checker development, before the checker was committed.** Two issues surfaced and were
diagnosed before any change:
- The first run failed "global bindings are equivalent". The cause was **in the checker**:
  it collected `code.co_names`, which also contains attribute names (`regions`, `argsort`,
  `get`, …). It was repaired to use `LOAD_GLOBAL` instructions. The production code was
  never the cause.
- The first behavioral mutation run caught 33/38 non-equivalent mutants.
  `edge_default_one`, `weights_squared`, `quantile_unsorted`, `median_q_0_4` and
  `p90_q_0_95` survived. A random probe confirmed that the first four change behavior
  (44, 3, 559 and 2 of 2000 cases). `p90_q_0_95` is non-equivalent by construction; the
  new fixture is an explicit witness where it moves p90 from 0.3 to 0.4. The checker was
  strengthened with the intervener-40 fixture, whose weights were chosen by a small search
  over integer weights so that every such mutant changes (median, p90), and with an
  unsorted-input quantile case.

**Final behavioral mutation result: 38/38 non-equivalent mutants caught.** It was run in
the worktree under the guard. The mutants are applied to `fov3d/scene/relations.py` and
executed into `sys.modules` before the adapter is imported:

| class | mutants (all caught) |
|---|---|
| object-region filtering | region ignores kind; region ignores a `None` id; id not `int`; kind filter removed; pair match by membership only |
| target/intervener orientation | orientation by region b; never swapped |
| vote accumulation | overwrite instead of accumulate; vote default 1 |
| chain and edge accumulation | edges count chains; edge default 1; chains counted only with a jump |
| zero-vote handling | fraction 0.0; balance 0.0 |
| depth-jump collection | presence unchecked (`KeyError`); wrong attribute; jump divided by edges |
| edge weighting | unit weights; squared weights |
| weighted median/p90 | `side='right'`; values unsorted; sorted by weight; total `< 0`; empty gives 0.0; median q 0.4; p90 q 0.95; median and p90 swapped; no `float` cast |
| intervener filtering | target not excluded; unsorted; string-sorted; not `int` |
| return and key structure | key renamed; key order swapped; key not `str`; fraction uses target votes; signed balance; count as `float` |

Three mutants are **equivalent**, recorded separately with 0/2000 differing random cases.
The probe does detect controls: `quantile_side_right` 405/2000, `quantile_unsorted`
559/2000, `weights_unit` 9/2000.

| equivalent mutant | reason |
|---|---|
| no `nedge > 0` guard on jump collection | a zero-weight entry never wins a left `searchsorted` at q·total > 0 (q is 0.5 or 0.9), and an all-zero total gives `None` either way |
| `np.asarray` without `float64` | the values are Python floats, and integer weights give an integer `cumsum` with the same `searchsorted` index |
| `argsort(kind="stable")` | tied values return the same value whichever tied element the index lands on |

**Static and identity mutants: 9/9 caught.**

| mutant | caught by |
|---|---|
| a comment added in `boundary_depth_order` (**no behavior change**) | source-text identity |
| a local variable renamed (**no behavior change**) | source-text and AST identity |
| builtin `abs` shadowed at module level | global-binding equivalence, plus behavior |
| a duplicate `boundary_depth_order` defined in the adapter | identity and no-duplicate checks |
| the adapter missing the `_weighted_quantile` identity import | checker exits nonzero (`AttributeError`) |
| a lazy `fov3d.experiments` import in `scene/relations.py` | allowed-imports check |
| `scene/relations.py` imports `cv2` | allowed imports, and the fresh-import footprint |
| an eager `relations` import in `fov3d/scene/__init__.py` | bare-footprint check |
| a production module importing the primitive through the adapter | no-production-import check |

## Gate A — interactive

Run in the worktree under the guard at `70afe24`, then the whole gate again at `86e3e9c`,
with identical results:

```text
compile: 3 changed Python files OK
[conceptual-core9-check] SUMMARY checked=24 failed=0
[conceptual-core8-check] SUMMARY checked=20 failed=0
[conceptual-core7-check] SUMMARY checked=22 failed=0
[conceptual-core6-check] SUMMARY checked=35 failed=0
[conceptual-core5-check] SUMMARY checked=38 failed=0
[conceptual-core4-check] SUMMARY checked=32 failed=0
[conceptual-core3-check] SUMMARY checked=27 failed=0
[conceptual-core2-check] SUMMARY checked=20 failed=0
[conceptual-core1-check] SUMMARY checked=13 failed=0
[partition-graph1-check] SUMMARY checked=13 failed=0
[partition-graph2-check] SUMMARY checked=16 failed=0
[partition-graph3-check] SUMMARY checked=20 failed=0
[partition-graph4-check] SUMMARY checked=14 failed=0
[partition-graph5-check] SUMMARY checked=12 failed=0
[partition-graph6-check] SUMMARY checked=12 failed=0
[partition-graph7-check] SUMMARY checked=12 failed=0
[partition-graph8-check] SUMMARY checked=10 failed=0
[partition-graph8b-check] SUMMARY checked=12 failed=0
[consolidation3-facade-check] SUMMARY checked=16 failed=0
[verify] 31 files tracked at baseline-classroom-oracle1-2026-09-25 are byte-identical in the working tree
[verify] SUMMARY passed=9 failed=0
[compare-golden] compared {"looks": 104, "npz_arrays_compared": 1348, "rgb_arrays_excluded": 337, "targets": 25}
[compare-golden] MISMATCHES 0
git diff --check: clean
import fov3d.scene -> ['fov3d', 'fov3d.scene', 'fov3d.scene.model', 'fov3d.scene.sphere'] | cv2 False
import fov3d.scene.relations -> ['fov3d', 'fov3d.scene', 'fov3d.scene.model', 'fov3d.scene.relations', 'fov3d.scene.sphere'] | cv2 False
partition_graph4_demo.py --help: imports load (exit 0)
```

The golden comparison took 9.97 s. The Partition-Graph checkers 1–8b were run unmodified
(`git diff` against main is empty).

## Import/dependency audit and conditional-replay decision

Measured in the worktree under the guard, for all 12 Partition-Graph producer/evaluator
entry points, with fresh-process `sys.modules`:

| entry point | loads the experiment `relations` / `fov3d.scene.relations` |
|---|---|
| **Phase-4 analyzer** | **yes / yes** |
| Phase-2 lift; Phase-3 lift; Phase-5 analyzer; Phase-6, 7, 8 and 8b proposers/evaluators | no / no |

An AST scan of every tracked `.py` file found the importers of either module:
- the adapter itself;
- the Core-9 checker;
- `tools/dev/check_partition_graph4.py`, which is unmodified and passes;
- `tools/partition_graph4_analyze.py`, which is Gate B;
- `tools/partition_graph4_demo.py`, a post-producer demo tool. It imports only
  `EVIDENCE_CLASS_NAMES`, writes into the excluded `demo/` scope, and is not a comparison
  gate. Its import path was smoke-loaded with `--help`.

The dynamic-import sites are unchanged.

**Decision:** only the Phase-4 relation product is reached, so it alone is replayed (Gate
B). Phases 2, 3, 5, 6, 7, 8 and 8b were **not** run, and the Phase-8 proposer was not
authorized.

## Gate B — Phase-4 relation product

```text
.venv/bin/python tools/partition_graph4_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/conceptual-core-9-phase4-full
[partition-graph4-analyze] COMPLETE {"causal_own_support_gap": 44, "causal_ownership_cut": 42, "causal_relations": 86, "states": 104, "target_depth_checks": 51, "target_depth_mismatches": 0}
```

The line is string-identical to the lines in earlier committed reports.

| wall | accepted reference | accepted total | excluded | producer files (fresh = accepted scope) | result | scope manifest sha256 |
|---|---|---|---|---|---|---|
| 6.81 s | `partition-graph-4-full` | 425 | `demo/` 107, `demo-package-original/` 107 | 211 | **byte-identical** | `eca1b6ad798117de8d2de321e0ebfe6f92cb3e73a8f0b80e78e494f8a3f3cd8c` |

The comparison is two-sided:
- the fresh set equals the accepted set minus only the established exclusions, and no
  fresh file lies under an excluded path;
- `filecmp` with `shallow=False` on every pair;
- equal `LC_ALL=C` manifests. The manifest equals the Core-2 through Core-8 value.

`only_fresh`, `only_accepted`, `fresh_under_excluded` and `byte_diff` were all 0.

**Execution count.** Two separate guarded instrumentation runs wrapped the adapter's
`boundary_depth_order` binding and wrote to scratch directories, not `previews/`. Each
produced output byte-identical to `partition-graph-4-full`.
- **484 calls**: 302 per-state (`analyze_phase4:402`) and 182 scene-final
  (`analyze_phase4:460`).
- 640 intervener entries, 628 of them with at least one matched chain.

The serialized product holds 570 `"boundary_depth_order"` blocks: the 484 computed plus
the 86 causal-final records, which reuse per-state annotations. That matches the Phase-4
report's 570 relation records.

**Accepted trees unchanged.** Per-file sha256 manifests of all 13 accepted trees are
identical before and after, and they equal the Core-8 values.

## Changed-path → execution-gate coverage

| changed path | kind | exercised by | execution evidence |
|---|---|---|---|
| `fov3d/scene/relations.py` module (NumPy, `typing`, `.model`) | new module | A (Core-9; checker 4 through the adapter), B | fresh-import probes; Gate B byte-identical |
| `_region_object`, `_weighted_quantile`, `boundary_depth_order` | moved | A (Core-9: 24 checks), **B** | 484 executions of `boundary_depth_order` (instrumented); 211/211 byte-identical |
| the adapter's import changes (+ scene relations; − `BoundaryKind`, `RegionKind`) | changed module dependency | A (checker 4; Core-9 identities), B | as above |
| `annotate_corridor`'s binding | changed dependency binding | B | `__globals__` identity; output byte-identical |
| `tools/dev/check_conceptual_core9.py` | new checker | A; mutation harnesses | 24/24; 38/38 behavioral and 9/9 static mutants caught |

## Repairs and deviations

1. **Orphaned imports removed.** `BoundaryKind` and `RegionKind` were used in the adapter
   only by the moved functions and nothing takes them through the adapter, so they were
   dropped from its `fov3d.scene` import. The contract allows removing genuinely orphaned
   imports.
2. **Checker development fixes.** The binding-check defect was fixed and the fixtures were
   strengthened, both **before** the checker was committed. The committed checker is the
   final 24-check form. No production code needed repair.
3. **Additional evidence.** It comprises the instrumented call counts, the random
   equivalence probe, the `symtable` scan, and the informational lineage differential
   below. It used throw-away harnesses in the session scratchpad, which are not
   committed. One throw-away command briefly wrote a temporary file under `/tmp`, which
   was deleted at once; it had no effect on any measurement.

There were no other deviations. The gate command, inputs, output directory and reference
are exactly the contract's.

## Confirmations

- **Unchanged** (by `git diff` and source-text identity):
  - `FineEvidence`, the stereo replay, `add_patch_observation` and the evidence
    classification;
  - `relation_origin`, `ownership_margin_descriptor`, `annotate_corridor` and
    `component_lineage`;
  - `BoundaryKind`/`RegionKind` behavior, partition construction, boundaries, corridors,
    lineage and state validation;
  - the controller replay, the Phase-2 boundaries, and benchmark and evaluation policy.
- Nothing was renamed, and no annotation was altered or validation added.
- `fov3d/scene/__init__.py` is unchanged, and the bare-import footprint is unchanged.
- **No scientific/runtime behavior changed.** The evidence:
  - text-identical code with equivalent bindings;
  - a byte-identical Phase-4 relation product from 484 executions;
  - golden `MISMATCHES 0`, and baseline 31/31.

## Unresolved

1. **Two lineage implementations.** `fov3d.scene.lineage._lineage` (Core 7) and the
   adapter's `relations.component_lineage` differ in text (names, annotations,
   formatting), but a random differential gave 0/3000 differing outcomes, including
   `None`, shape-mismatch errors and float labels. They are probably behavioral
   duplicates. Unifying them was explicitly out of scope and is a decision for Luiz and
   Chat.
2. **Carried items.** The deferred `attach_state_region_codes` rename, the consumerless
   aliases (Cores 2, 5 and 6), the separate Phase-2 and Phase-3 boundary lineages, the
   target-relative `HeadEvidence` placement, and the question of stricter
   one-region-per-code validation are all carried over unchanged.
3. **Stale shared `main`.** The shared checkout's local `main` (`e681392`) is behind
   `origin/main` (`f90f90a`). It was deliberately not touched.

## Recommendation (Conceptual Core 10 only)

Continue the topology/relations boundary with the next coherent cluster in the adapter,
the relation-origin group: `_region_code`, `_own_labels`, `_joint_region_own_component`
and `relation_origin`. `annotate_corridor` consumes it just as it consumes
`boundary_depth_order`, so the same single primary gate (the Phase-4 relation product) and
the same audit-driven conditional-replay rule apply.

**Measured dependency, a correction.** The globals were read with `LOAD_GLOBAL` at this
head:
- `_own_labels` uses **`cv2.connectedComponents`**, and so does `own_support_labels`.
- `relation_origin` therefore depends on OpenCV transitively. The other two functions use
  only `np` and builtins.

The Core-8 report's AST inventory, which considered only `from`-imports, listed
`_own_labels` and `own_support_labels` among the "NumPy-only" candidates. That was wrong.

Moving this cluster into `fov3d.scene.relations` would make that module require OpenCV. It
is NumPy-only today, although the bare `fov3d.scene` import would stay unaffected. The
Core-10 contract should therefore decide the placement explicitly, for example a separate
cv2-dependent module like `fov3d.scene.corridors`.

"Relation origin" (`ownership_cut` versus `own_support_gap`) also carries interpretive
meaning, so Chat should confirm that the cluster is generic. The lineage-duplication
question (unresolved item 1) could be settled in the same review rather than silently.

## Success marker

    CONCEPTUAL_CORE9_RELATIONS_PRESERVE_BEHAVIOR
