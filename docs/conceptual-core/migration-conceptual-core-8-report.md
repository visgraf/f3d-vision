# Migration Conceptual Core 8 — report (2026-09-27)

Executed by Claude Code on the Ubuntu workstation against the committed contract
`docs/migration-conceptual-core-8.md`. Every number below is **MEASURED** from the
command shown, unless it is marked otherwise.

## Provenance and main/handoff/branch sequence

| step | result |
|---|---|
| pre-check (fetch) | `origin/main = e681392af8abc7d5fc6b2116a0c5bb534bc0ea7e` and `origin/migration/conceptual-core-7 = 3603266b299236359f0539a778ac98f65cd11887`, both verified; `e681392` is an ancestor of `3603266` |
| **Core 7 accepted** (Luiz and Chat) | `origin/main` fast-forwarded `e681392..3603266` by a plain, non-forced push of the exact commit |
| handoff update | in a *detached* administrative worktree at the new `origin/main`: `docs/chat-handoff.md` commit `7855ff3b4691781f1f3d8e49f690b26c7ff30fa3` (parent `3603266`), pushed as a fast-forward to `main` |
| branch | `migration/conceptual-core-8` created at `7855ff3` (remote and local); the administrative worktree was then removed |
| Code commits on the branch | `bf0a396` contract, **committed before any production change** · `7bade62` extraction · `8ad8921` checker · `9563ed1` conceptual map · the commit that adds this report |
| gates measured at | Gate A and Gates B–E at `8ad8921`; the whole of Gate A again at `9563ed1`. `fov3d/` and `tools/` are identical at both |
| accepted Core-7 parent | `3603266` (`CONCEPTUAL_CORE7_LINEAGE_PRESERVES_BEHAVIOR`) |
| final head | the commit that adds this report |

The handoff update records:
- accepted Core 7 at `3603266`;
- `fov3d.scene.lineage` ownership;
- the retired lineage patch tool;
- Core 8 as the active step;
- the new arrangement, in which Chat is read/design/review only and Claude Code mutates
  and measures in isolated worktrees.

It also adds the accepted Core-6 `fov3d.scene.corridors` ownership entry, which the
previous handoff had omitted.

## Isolated-worktree execution

- **Where it ran.** Every Core-8 edit and measurement ran in the dedicated worktree
  `<scratchpad>/core8/wt` on `migration/conceptual-core-8`.
- **Data links.** The untracked data are symlinked in: `previews/` (accepted and fresh
  trees), `.venv/`, and the five ignored `scenes/classroom/` asset entries. `fov3d`
  resolves to the worktree's code, and there is no `.pth` redirect. Producers record input
  paths with `Path.resolve()`, so the recorded paths equal the accepted ones.
- **Guard.** Every measurement command ran under a guard that requires, before and after,
  branch `migration/conceptual-core-8`, the expected HEAD, and a clean tracked tree. It
  never tripped.
- **Shared checkout.** `/home/lvelho/rd/f3d-vision` was never used for Core-8 edits or
  measurements and its branch was never switched. It stayed on local `main` at `e681392`,
  as left after Core 7. It is therefore *behind* `origin/main` (`7855ff3`), which is
  harmless, and is left for Luiz.

## Files changed (main 7855ff3...final head)

| file | change |
|---|---|
| `docs/migration-conceptual-core-8.md` | contract (`bf0a396`) |
| `fov3d/scene/state_validation.py` | new: `attach_state_region_codes`, generated from the exact source segment of accepted Core-7 `joint.py` (`7bade62`) |
| `fov3d/experiments/classroom_partition/joint.py` | the definition removed (10 lines); `from fov3d.scene.state_validation import attach_state_region_codes` added; no import orphaned (`7bade62`) |
| `tools/dev/check_conceptual_core8.py` | new checker (`8ad8921`) |
| `docs/conceptual-core-map.md` | Core-8 status, row and order (`9563ed1`) |
| `docs/migration-conceptual-core-8-report.md` | this report |

The following are untouched (`git diff 7855ff3..HEAD` is empty for each):
- `fov3d/scene/__init__.py`, `model.py` (including `ScenePartitionGraph.validate()`),
  `partition.py`, `boundaries.py`, `corridors.py`, `lineage.py`, `sphere.py` and
  `synthetic.py`;
- `relations.py`, `lift.py` (Phase-2 boundaries), `incidental.py`, `integration.py`,
  `challenge_suite.py`, `benchmark.py` and `prefix_benchmark.py`;
- `fov3d/epistemic`, `fov3d/geometry` and `fov3d/reconstruction`;
- every other tool and checker, including the Partition-Graph checkers 1–8b, which are
  unmodified;
- `scripts/`, `tests/`, `CLAUDE.md` and `docs/chat-handoff.md` on the branch;
- sealed runtime files (baseline 31/31);
- the 13 accepted trees.

## State-validation API and dependency direction

    numpy
    fov3d.scene.model   ScenePartitionGraph
            -> fov3d.scene.state_validation      (explicit import; NOT in fov3d.scene.__all__)
                   attach_state_region_codes(graph, region_code) -> the same graph
                       raises RuntimeError on a code-set mismatch or the -1 sentinel;
                       then graph.validate() (its exceptions propagate)
            -> fov3d.experiments.classroom_partition.joint
                   lift_joint_run: joint.py:281  graph = attach_state_region_codes(graph, state["region_code"])

The name is preserved even though the function validates and attaches nothing; the rename
is deferred. The call is in the same statement position inside `lift_joint_run`, which is
source-text identical. Its line number moved from 290 to 281 only because the 10-line
definition above it was removed.

Fresh-process footprints (`python -I`, in the worktree):
- `import fov3d.scene` loads exactly `fov3d`, `fov3d.scene`, `fov3d.scene.model` and
  `fov3d.scene.sphere`. It does not load `cv2`, `partition`, `boundaries`, `corridors`,
  `lineage` or `state_validation`.
- `import fov3d.scene.state_validation` adds only `fov3d.scene.state_validation`, with no
  `cv2`.

## Source / AST / global-binding identity

1. The source text of `attach_state_region_codes` in `state_validation.py` is
   **byte-identical** to accepted Core-7 `joint.py` (`3603266`). The module was generated
   from that exact segment, and the docstring is preserved.
2. The AST is identical.
3. `np` and `ScenePartitionGraph` in `state_validation.py` are the same objects as in
   Core-7 `joint.py`. `lift_joint_run.__globals__["attach_state_region_codes"]` is the
   scene function, and `joint.attach_state_region_codes is state_validation.attach_state_region_codes`.
4. All 8 remaining top-level definitions of `joint.py` are source-text identical to
   Core 7, as are all non-import module statements: `StereoOps`, `_default_stereo_ops`,
   `build_joint_graph`, `_rectified_core_directions_h`, `update_controller_seen_any`,
   `_append_raw_footprints`, `_controller_expected_never` and `lift_joint_run`.
5. `state_validation.py` imports only `__future__`, `numpy` and `.model`. A `symtable`
   scan finds 0 unbound globals in it and in `joint.py`.
6. `fov3d/scene/__init__.py`, `partition.py`, `boundaries.py`, `corridors.py`,
   `lineage.py`, `relations.py`, the controller replay and the Phase-2 code are unchanged
   (items 4 and the file table).

## Checker results

`tools/dev/check_conceptual_core8.py` has **20 checks** and runs in about 0.30 s wall. Every
expectation was derived by hand from the contract, and all passed on the first run
against code proven text-identical to Core 7.

| contract item(s) | check |
|---|---|
| 1, 11 | valid match (the fixture includes a BASE region) returns **the same** graph; no mutation after success |
| 2, 11 | graph extra code: `RuntimeError`, `graph=[1, 2, 3, 9] raster=[1, 2, 3]`; no mutation after failure |
| 3 | raster extra code: `graph=[1, 2, 3] raster=[1, 2, 3, 4]`. The raster is `int32`; the diagnostic shows Python ints |
| 4 | missing attribute: `graph=[-1, 1, 3] raster=[1, 2, 3]` |
| 5 | `-1` fails even when the raster contains `-1`, for both an explicit `-1` and a missing attribute: `graph=[-1, 2, 3] raster=[-1, 2, 3]` |
| 6 | `int()` on both sides. Raster `2.7`/`3.2` → `{2, 3}`; attributes `"2"`/`3.9` → `{2, 3}` → accepted, and `"2"`/`4.9` → `graph=[2, 4] raster=[2, 3]`. Non-integral values are needed because `np.float64(2.0) == 2` with equal hashes |
| 7 | repeated raster values |
| 8 | **accepted duplicate codes**: `obj:7:c002` and `obj:7:c003` both carry code 2, `graph.validate()` passes, the call is accepted, and the same graph is returned |
| 9 | error precedence: a code-set mismatch *and* a BASE region with an `object_id` gives the code-set `RuntimeError`, not `ValueError` |
| 10 | matching sets with an invalid graph: `ValueError("base region base:c001 cannot carry object_id")` propagates unchanged, the same as calling `graph.validate()` directly |
| 12 | 1-D, 3-D and column rasters are accepted, so there is no dimensionality contract |
| 13 | an empty `ScenePartitionGraph()` with an empty raster is accepted, as `validate()` allows, and the same object is returned |
| 14–16 | `joint` identity; no duplicate definition; `state_validation` imports only `numpy` and `.model` |
| 17–18 | fresh bare `fov3d.scene` loads none of `cv2`, `partition`, `boundaries`, `corridors`, `lineage` or `state_validation`; fresh `fov3d.scene.state_validation` loads none of the first five |
| 19 | `check_partition_graph3.py` (unmodified) still imports and calls `attach_state_region_codes` through `joint` |

## Mutation evidence

**Behavioral mutants.** They are applied to `state_validation.py` and executed into
`sys.modules` before `joint` is imported, in the worktree under the guard. All 19 required
classes are covered, with 28 mutants in all. **26/26 non-equivalent mutants are caught by
the first version of the checker**, so no strengthening was needed.

| class | mutants | result |
|---|---|---|
| sentinel | `.get(..., -2)`; `-2` in both the lookup and the guard; `-1` guard removed | caught |
| comparison | subset instead of equality; superset instead of equality | caught |
| `int` conversion | no `int` on raster values; raster compared before `int` (`tolist`); no `int` on graph values; graph `int` only in the message | caught |
| multiplicity | duplicate graph codes newly rejected | caught |
| `validate()` | removed; moved before the code-set check | caught |
| return | `return None`; `copy.copy(graph)` | caught |
| error | `ValueError` instead; prefix text changed; graph/raster order swapped; unsorted diagnostics; reverse-sorted diagnostics | caught |
| filtering and shape | object regions only; regions with the attribute only; a 2-D shape restriction; positive raster codes only | caught |
| mutation of inputs | region attributes mutated; raster sorted in place on success; raster sorted in place on failure | caught |

**Equivalent mutants.** These are recorded separately, not forced into artificial tests.
Each shows **0/1000** differing outcomes on random fixtures:
- the raster rank is 1–3, including empty shapes, with int or non-integral float values;
- region attributes are int, string or `.5` floats, some missing;
- an invalid BASE region is included sometimes;
- **half the fixtures have matching code sets**, so that 230/1000 reach the success path.

The probe does detect controls: no graph `int` 744/1000, duplicate codes rejected 519/1000,
`validate()` removed 24/1000.

| equivalent mutant | reason |
|---|---|
| distinct values via a Python `set` instead of `np.unique` | the same distinct values reach `int()`, and sets ignore order |
| `codes != graph_codes` instead of `graph_codes != codes` | set inequality is symmetric |

**Static/package mutants: 6/6 caught.**

| mutant | caught by |
|---|---|
| a duplicate definition reintroduced in `joint.py` | identity and no-duplicate checks |
| the `joint` compatibility import removed | checker exits nonzero (`AttributeError`) |
| a lazy `fov3d.experiments` import in `state_validation.py` | allowed-imports check |
| `state_validation.py` imports `cv2` | allowed imports, and the NumPy-only footprint |
| an eager export through `fov3d/scene/__init__.py` | bare-footprint check |
| `check_partition_graph3.py` bypassing `joint` | the Phase-3 compatibility check |

## Accepted duplicate-code subtlety

The helper compares **sets**, so two distinct regions carrying the same
`state_region_code` are **not** rejected by it. `ScenePartitionGraph.validate()` does not
check code uniqueness either. Checker item 8 locks this accepted behavior, and the mutant
that newly rejects duplicates is caught. Core 8 deliberately does not "fix" it.

## Gate A — interactive

Run in the worktree under the guard at `8ad8921`, then the whole gate again at `9563ed1`,
with identical results:

```text
compile: 3 changed Python files OK
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
import fov3d.scene.state_validation -> ['fov3d', 'fov3d.scene', 'fov3d.scene.model', 'fov3d.scene.sphere', 'fov3d.scene.state_validation'] | cv2 False
```

The golden comparison took 9.99 s. The Partition-Graph checkers 1–8b were run unmodified
(`git diff` against main is empty).

## Import/dependency audit and conditional-gate decision

Measured in the worktree, under the guard, before replay.

| entry point | loads `joint` / `scene.state_validation` |
|---|---|
| Phase-3 lift | yes / yes |
| Phase-4 analyzer | yes / yes (through `relations` → `joint`) |
| Phase-8b proposer / evaluator | yes / yes (through `challenge_suite` → `joint`) |
| **Phase-5 analyzer** | **no / no** |
| Phase-2 lift; Phase-6, 7 and 8 proposers/evaluators | no / no |

An AST scan of every tracked `.py` file found that only `joint.py` and the Core-8 checker
import `fov3d.scene.state_validation`. Nested imports of `joint`/`state_validation` occur
only in checkers, and the dynamic-import sites are unchanged (`fov3d/_compat.py`, the
facade checker, and checker 3's `__import__("fov3d.scene")`).

**Decision (the contract's tighter rule):**
- **Phase 5 was not run.** The final Core-8 diff does not reach its executable or import
  path, and it consumes only the accepted `partition-graph-4-lift` tree.
- Phases 2, 6, 7 and 8 were not run.
- **The Phase-8 proposer was not authorized and not run.**

## Replay gates B–E

All commands were run from the worktree root, in order, each to a fresh directory and each
under the guard:

```text
B .venv/bin/python tools/partition_graph3_lift.py previews/partition-graph-2-source-full previews/conceptual-core-8-phase3-full
C .venv/bin/python tools/partition_graph4_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/conceptual-core-8-phase4-full
D .venv/bin/python tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals previews/conceptual-core-8-phase8b-proposals
E .venv/bin/python tools/partition_graph8b_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8b-proposals previews/partition-graph-8-evaluation previews/conceptual-core-8-phase8b-evaluation
```

```text
B [partition-graph3-lift] COMPLETE {"causal_final_pairs": 86, "evidence_checks": 51, "evidence_mismatches": 0, "scene_final_pairs": 182, "states": 104}
C [partition-graph4-analyze] COMPLETE {"causal_own_support_gap": 44, "causal_ownership_cut": 42, "causal_relations": 86, "states": 104, "target_depth_checks": 51, "target_depth_mismatches": 0}
D [partition-graph8b-propose] COMPLETE {"eligible_candidates": 6489, "full_phase8_parity": 25, "raw_candidates": 18469, "scenarios": 5, "states": 125, "targets": 25, "truth_used": false}
E [partition-graph8b-evaluate] COMPLETE {"full_eligible_recall": 0.9335820895522388, "full_integrated_covered": 27948, "full_integrated_residual": 1340, "scenarios": 5, "states": 125}
```

Every required value matches. All four lines are string-identical to lines in earlier
committed reports.

| gate | wall | accepted reference | accepted total | excluded | producer/evaluator files (fresh = accepted scope) | result | scope manifest sha256 |
|---|---|---|---|---|---|---|---|
| B Phase-3 joint lift | 22.92 s | `partition-graph-4-lift` | 419 | — | 419 | byte-identical | `7eed664047384a43f50f51940cc4ad61d602513bb1095e076adc6c083ac3cbe3` |
| C Phase-4 analyzer | 7.13 s | `partition-graph-4-full` | 425 | `demo/` 107, `demo-package-original/` 107 | 211 | byte-identical | `eca1b6ad798117de8d2de321e0ebfe6f92cb3e73a8f0b80e78e494f8a3f3cd8c` |
| D Phase-8b proposer | 61.97 s | `partition-graph-8b-proposals` | 503 | — | 503 | byte-identical | `51a93fc464fc8ce00fc7f519ccadc25f539095be06de074788844b12ad6e7b7d` |
| E Phase-8b evaluator | 16.78 s | `partition-graph-8b-evaluation` | 19 | `demo/` 8, `demo-package-original/` 8 | 3 | byte-identical | `243133b66237523147e1a869ee5b1bf97ee28ec9d817c5c059921e9b254c5715` |

In every gate, `only_fresh`, `only_accepted`, `fresh_under_excluded` and `byte_diff` were
all 0. The method is the same as in Cores 3–7:
- two-sided set equality after only the demonstrated `demo/` and `demo-package-original/`
  exclusions;
- `filecmp` with `shallow=False` on every pair;
- `LC_ALL=C` manifests.

All four scope manifests equal the Core-2 through Core-7 values.

**Accepted-tree manifests before and after.** The per-file sha256 manifests of all 13
accepted trees are identical before Gate B and after Gate E, and they equal the Core-7
values:

| tree | files | full-tree manifest sha256 |
|---|---|---|
| `partition-graph-2-source-full` | 1122 | `9c4def894e2573c22722336cf200d794e30d566f88108cdde3ee3722da7ff53d` |
| `partition-graph-2-full` | 524 | `9589e4a335ff9490a2f0aaf7c034c14abfc2559095d36d143115349accadb509` |
| `partition-graph-4-lift` | 419 | `7eed664047384a43f50f51940cc4ad61d602513bb1095e076adc6c083ac3cbe3` |
| `partition-graph-4-full` | 425 | `223c7ea9bd226aba24f96fa97c9e5119ae0a6e27a62e21d0abb048e821650d95` |
| `partition-graph-5-full` | 225 | `41640332e411582b31ab6cafc9675034d955d4884bf77e3b06cfb19ad2677517` |
| `partition-graph-6-proposals` | 102 | `30e88f61da7ef1d43bc9bb530418f2d03c1403347b26f22a0d9a1c211309bbad` |
| `partition-graph-6-evaluation` | 59 | `06caf55212f68604cdd8e2414028358085dec702e612ee862750d1bd9f7ccfe4` |
| `partition-graph-7-proposals` | 835 | `3dde52e4cd34228f91c240db3682dc489d9f1adb74a5e85a7021b58bff1673de` |
| `partition-graph-7-evaluation` | 321 | `08a74a0f25245ca1c63b8203f7228ee3b44c0863e9ee66b1cc7a01676f6a12d2` |
| `partition-graph-8-proposals` | 468 | `69ccbfb748f250e19baebb75789e57c66f4c26443286e43a9a85ca77f474a209` |
| `partition-graph-8-evaluation` | 321 | `f08d5dbae6519b607e651caaa74b14f0d141374629b6945bd0b95567ebfaeea2` |
| `partition-graph-8b-proposals` | 503 | `51a93fc464fc8ce00fc7f519ccadc25f539095be06de074788844b12ad6e7b7d` |
| `partition-graph-8b-evaluation` | 19 | `c08677826edf589e75de1b921cf354bfbe5d4dd9158d12ae4d1dac42bad96bb9` |

**Execution count in Gate B.** A separate guarded instrumentation run wrapped
`joint.attach_state_region_codes` with a counter and ran `lift_joint_run` to a scratch
directory, not `previews/`. It made **104 calls for 104 global states**, none of them
map-absent. All 104 returned the identical graph object, and 0 raised. Its 419-file
output was also byte-identical to `partition-graph-4-lift`, so the wrapper did not alter
behavior, and Gate B wrote 104 `states/global_*` directories. So the validator ran on
every map-present Phase-3 state, before `graph.save`.

Phase 8b does **not** call the function: `challenge_suite` has 0 references. Gates D and E
cover the changed module-load path only, as the contract states.

## Changed-path → execution-gate coverage

| changed path | kind | exercised by | execution evidence |
|---|---|---|---|
| `fov3d/scene/state_validation.py` module (NumPy, `.model`) | new module | A (Core-8; checkers 3, 4, 5 and 8 through `joint`), B, C (load), D, E (load) | import probe; every run byte-identical |
| `attach_state_region_codes` | moved | A (Core-8: 20 checks; checker 3 calls it), **B** | 104/104 map-present states (instrumented), same object returned; 419/419 byte-identical |
| `joint.py` import (+ `fov3d.scene.state_validation`) | changed module dependency | A, B, C (`relations` → `joint`), D, E (`challenge_suite` → `joint`) | as above |
| `lift_joint_run`'s binding | changed dependency binding | B | `__globals__` identity; output byte-identical |
| `tools/dev/check_conceptual_core8.py` | new checker | A; mutation harnesses | 20/20; 26/26 behavioral and 6/6 static mutants caught |

## Repairs and deviations

1. **No repairs were needed.** The extraction, checker and gates passed as designed, and
   the checker was not strengthened: its first version caught every non-equivalent
   mutant.
2. **Handoff correction.** The previous handoff omitted the accepted Core-6
   `fov3d.scene.corridors` ownership entry, and the handoff commit `7855ff3` added it.
   This is a factual correction; no scientific claim changed.
3. **Additional evidence beyond the contract.** It comprises the instrumented call count,
   the equivalence probe, and the `symtable` scan. It used throw-away harnesses in the
   session scratchpad, which are not committed.

No other deviation. The gate commands, inputs, output directories and references are
exactly the contract's.

## Confirmations

- `ScenePartitionGraph.validate()`, partition construction, boundary extraction, gap
  corridors, target-component lineage, the controller `seen_any` replay, the Phase-4
  relations (`relations.py`), `FineEvidence`, `HeadEvidence`, the Phase-2 boundaries,
  benchmark and evaluator policy, observation overlays and saved-run traversal are
  **unchanged**, by `git diff` and source-text identity.
- The function was **not renamed**, and no serialized output changed.
- `fov3d/scene/__init__.py` is unchanged, and the bare-import footprint is unchanged.
- **No scientific/runtime behavior changed.** The evidence:
  - text-identical code with identical global bindings;
  - byte-identical Phase 3, 4 and 8b producer output, and Phase-8b evaluator output;
  - golden `MISMATCHES 0`, and baseline 31/31.

## Unresolved

1. **Deferred rename.** A future compatibility cleanup could rename the function to, for
   example, `validate_state_region_codes`, keeping `attach_state_region_codes` as a
   compatibility alias.
2. **Alias policy.** Consumerless compatibility aliases from Cores 2, 5 and 6 remain one
   pending decision. `joint.attach_state_region_codes` is *not* consumerless: it is used
   by `lift_joint_run` and checker 3.
3. **Duplicate-code acceptance** is locked as accepted behavior. Whether a stricter
   one-region-per-code validation is scientifically desirable is a separate decision for
   Luiz and Chat.
4. **Stale shared `main`.** The shared checkout's local `main` (`e681392`) is behind
   `origin/main` (`7855ff3`). It was deliberately not touched.

## Recommendation (Conceptual Core 9 only)

Topology/relations is the next larger boundary, and it is close to scientific semantics.
The recommended Core 9 is therefore a **Chat-designed contract, informed by a measured
audit of `relations.py`**, before any move. An AST inventory at this head suggests three
groups.

**Candidate pure scene-graph operations.** They use only `ScenePartitionGraph`,
`RegionKind`/`BoundaryKind` and NumPy:
- `_region_code`, `_own_labels`, `_joint_region_own_component`, `relation_origin`;
- `_region_object`, `_weighted_quantile`, `boundary_depth_order`;
- `component_lineage`, `own_support_labels`.

**Evidence-coupled and must stay experiment-side:** `FineEvidence`, `_mark`,
`add_patch_observation`, `evidence_class_raster` and `evidence_class_counts`. They use
chart marking and the stereo/rectification replay.

**Mixed composers or drivers:** `annotate_corridor`, `ownership_margin_descriptor` (it
uses the 12-mm association radius) and `analyze_phase4`.

A bounded first extraction could be the depth-order descriptor group
(`boundary_depth_order` with `_region_object` and `_weighted_quantile`) or the
relation-origin group. Chat should decide which, because "depth order" and "relation
origin" carry interpretive meaning. Their gates would be the Phase-4 analyzer against
`partition-graph-4-full` as the primary gate, plus Phase 5 if the audit shows it is
reached. The rename and alias cleanup (items 1–2) could be a separate small compatibility
step.

## Success marker

    CONCEPTUAL_CORE8_STATE_VALIDATION_PRESERVES_BEHAVIOR
