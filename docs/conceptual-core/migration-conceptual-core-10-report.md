# Migration Conceptual Core 10 — report (2026-09-27)

Executed by Claude Code on the Ubuntu workstation against the committed contract
`docs/migration-conceptual-core-10.md`. Every number below is **MEASURED** from the
command shown, unless it is marked otherwise.

## Causal question and answer

*Can the generic corridor relation-origin primitive be moved from the Classroom Phase-4
adapter into the generic scene corridor layer without changing any behavior?*

**Yes.** The evidence:
- `_region_code`, `_own_labels`, `_joint_region_own_component` and `relation_origin` now
  live in `fov3d/scene/corridors.py`;
- they are source-text and AST identical to accepted Core 9, with equivalent global
  bindings;
- `corridors.py`'s imports and existing functions are unchanged;
- the Phase-4 relation product is byte-identical, from 484 executions of `relation_origin`;
- every other replay the fresh import audit requires (Phase 3 and Phase 8b) is also
  byte-identical;
- golden reports `MISMATCHES 0` and the baseline is 31/31.

## Provenance: Core-9 acceptance administration and branch

| step | result |
|---|---|
| pre-check (fetch) | `origin/main = f90f90af48a385b8b808e69d45629955bb8f4be2`, `origin/migration/conceptual-core-9 = 518ff6ce4686238301f5ac946a5ea049e27ed9da`, both verified. `518ff6c` descends from `f90f90a`; Core 9 is 5 ahead and 0 behind. `CLAUDE.md` is unchanged; the only worktree was the untouched shared checkout |
| **Core 9 accepted** (Luiz) | `origin/main` fast-forwarded `f90f90a..518ff6c` by a plain, non-forced push of the exact commit |
| handoff | in a detached administrative worktree at `518ff6c`, only `docs/chat-handoff.md` was changed: commit `b69e0c900fa0b063fc8ecd39f689dc6452f29412` (parent `518ff6c`), pushed as a fast-forward to `main`. The administrative worktree was then removed |
| branch | `migration/conceptual-core-10` created at `b69e0c9` from the **new** `origin/main`, both remote and local |
| Core-10 commits | `3c9d7c6` contract, **committed before any production change** · `f8dbede` extraction · `274fdd6` checker · `d291e9a` conceptual map · the commit that adds this report |
| gates measured at | Gate A, the import audit, the replays and the instrumentation at `274fdd6`; the whole of Gate A again at `d291e9a`. `fov3d/` and `tools/` are identical at both |
| final head | the commit that adds this report |

The handoff records:
- Core 9 accepted at `518ff6c`;
- `fov3d.scene.relations` ownership of `_region_object`, `_weighted_quantile` and
  `boundary_depth_order`, with the adapter keeping identity imports;
- the Core-9 evidence: checker 24/24, 38/38 behavioral and 9/9 static mutants, Phase 4
  211/211 byte-identical, 484 executions, baseline 31/31 and golden `MISMATCHES 0`;
- the working arrangement;
- Core 10 as the active step.

## Isolated worktree and guard

- **Where it ran.** Every Core-10 edit and measurement ran in the dedicated worktree
  `<scratchpad>/core10/wt` on `migration/conceptual-core-10`.
- **Data links.** The untracked data are symlinked in: `previews/`, `.venv/`, and the five
  ignored `scenes/classroom/` asset entries. `fov3d` resolves to the worktree's code.
- **Guard.** Every measurement ran under the guard, which requires, before and after,
  branch `migration/conceptual-core-10`, the expected HEAD, and a clean tracked tree. It
  never tripped.
- **Shared checkout.** `/home/lvelho/rd/f3d-vision` was not mutated and its branch was not
  switched. It stays on local `main` at `e681392`, behind `origin/main`.

## Files changed (main b69e0c9...final head)

| file | change |
|---|---|
| `docs/migration-conceptual-core-10.md` | contract (`3c9d7c6`) |
| `fov3d/scene/corridors.py` | **append only**: a two-line provenance comment and the four exact source segments from accepted Core-9 `relations.py`. The first 147 lines (the docstring, all imports, and `_component_boundary`, `_line_cells`, `gap_corridor` and `corridors_for_object`) are byte-identical to Core 9 (`f8dbede`) |
| `fov3d/experiments/classroom_partition/relations.py` | four definitions removed (28 lines); `from fov3d.scene.corridors import _joint_region_own_component, _own_labels, _region_code, relation_origin` added; **no import orphaned**, so `cv2`, `np` and `ScenePartitionGraph` stay (`f8dbede`) |
| `tools/dev/check_conceptual_core10.py` | new checker (`274fdd6`) |
| `docs/conceptual-core-map.md` | Core-10 status, `relations.py` row and topology/relations order (`d291e9a`) |
| `docs/migration-conceptual-core-10-report.md` | this report |

The following are untouched (`git diff b69e0c9..HEAD` is empty for each):
- `fov3d/scene/__init__.py`, `model.py`, `partition.py`, `boundaries.py`, `lineage.py`,
  `state_validation.py`, `relations.py`, `sphere.py` and `synthetic.py`;
- `joint.py`, `lift.py`, `incidental.py`, `integration.py`, `challenge_suite.py`,
  `benchmark.py` and `prefix_benchmark.py`;
- `fov3d/epistemic`, `fov3d/geometry` and `fov3d/reconstruction`;
- every other tool and checker, including the Partition-Graph checkers 1–8b, which are
  unmodified;
- `scripts/`, `tests/`, `CLAUDE.md`, the handoff on the branch, and sealed runtime files;
- the 13 accepted trees.

## Literal source / AST / global-binding evidence

1. **Source text.** The segments of all four functions in `fov3d/scene/corridors.py` are
   **byte-identical** to accepted Core-9 `relations.py` (`518ff6c`). They were appended
   from those exact segments.
2. **AST.** The ASTs are identical.
3. **Global bindings.** Every `LOAD_GLOBAL` name of the four functions (`cv2`, `np`, `int`,
   `len`, `RuntimeError` and the in-cluster helpers) resolves in `scene.corridors` to the
   same object as in the executed Core-9 adapter. `cv2`, `np`, `ScenePartitionGraph` and
   `Any` are identical objects in both modules.
4. **Helper resolution.** Inside `scene.corridors`, `relation_origin` resolves
   `_own_labels` and `_joint_region_own_component`, and `_joint_region_own_component`
   resolves `_region_code`.
5. **The rest of the adapter is unchanged.** All 13 remaining top-level definitions of the
   adapter are source-text identical to Core 9, as are all non-import module statements.
   That includes `own_support_labels`, `component_lineage`, `annotate_corridor`,
   `ownership_margin_descriptor`, `FineEvidence` and `analyze_phase4`.
6. **`corridors.py` itself.** Its import statements are AST-identical to Core 9, and its
   four existing functions are source-identical.
7. A `symtable` scan finds 0 unbound globals in `corridors.py` and the adapter.

## Compatibility identities

`relations._region_code`, `._own_labels`, `._joint_region_own_component` and
`.relation_origin` in the experiment adapter **are** the `fov3d.scene.corridors` objects.
`annotate_corridor.__globals__["relation_origin"]` is the scene function. No duplicate
definition remains. `tools/dev/check_partition_graph4.py` (unmodified) still imports
`relation_origin` through the adapter and passes. No production module takes the cluster
through the adapter; the checker enforces this.

## Import footprints

In fresh processes (`python -I`, worktree):

| import | `fov3d` modules | `cv2` |
|---|---|---|
| `import fov3d.scene` | exactly `fov3d`, `fov3d.scene`, `fov3d.scene.model`, `fov3d.scene.sphere` | no |
| `import fov3d.scene.corridors` | adds `fov3d.geometry`, `fov3d.geometry.head_chart`, `fov3d.scene.corridors`, the unchanged Core-6 footprint, with no experiment, stereo or other scene module | yes (accepted) |
| `import fov3d.experiments.classroom_partition.relations` | 19 `fov3d` modules, including all scene modules through `joint` | yes |

## Checker results

`tools/dev/check_conceptual_core10.py` has **29 checks** and runs in about 0.4 s wall. All
of them passed on the first run against code proven text-identical to Core 9.

| group | checks |
|---|---|
| A. literal migration | source-text and AST identity (from `git show 518ff6c`); `LOAD_GLOBAL` bindings against the executed Core-9 adapter; helper resolution in `scene.corridors`; existing corridor functions source-identical; `corridors.py` imports unchanged |
| B. adapter | four identity re-exports; the `annotate_corridor` binding; no duplicates; `own_support_labels` and `component_lineage` untouched (source-identical to Core 9) |
| C. `_region_code` | `7`, `"12"`, `3.9` and `np.int64(5)` give `7`, `12`, `3` and `5` as Python `int`s; a missing attribute gives `KeyError('state_region_code')`; a missing rid gives `KeyError('nope')` |
| D. `_own_labels` | the diagonal pair `[[1,0],[0,1]]` gives one component under 8-connectivity; a 3×5 mask gives three components in raster order `[[1,1,0,0,2],[0,0,0,0,2],[3,0,0,0,0]]` as `int32` with shape (3, 5); `[[0.6, 2.0, 0.0]]` gives `[[0, 1, 0]]` because `uint8` truncates 0.6 to background |
| E. `_joint_region_own_component` | region A over label {1} gives the Python `int` 1; region B over {0, 3} gives 3 (label 0 ignored); region C over {0} gives `RuntimeError ... component: []`; region D over {1, 2} gives `RuntimeError ... component: [1, 2]`; a float state raster `[[1.0, 1.7]]` joins the 1.7 cell only through the `int32` cast, giving `RuntimeError [1, 2]`; a decoy `owner_instance` key is present |
| F. `relation_origin` | P–Q, joined only diagonally, gives `("ownership_cut", 1, 1)`; P–S gives `("own_support_gap", 1, 2)`, S–R gives `(…, 2, 3)` and R–P gives `(…, 3, 1)`; Python `int` ids; `RuntimeError` and `KeyError` propagate |
| G. dependencies | no experiment, stereo, reconstruction, benchmark or renderer import; `fov3d/scene/__init__.py` byte-identical to Core 9; no production import through the adapter; fresh bare `fov3d.scene` stays OpenCV-free; fresh `fov3d.scene.corridors` has exactly the Core-6 footprint |

**Checker development, before the commit.** The first mutation run caught every
non-equivalent mutant. However, five of them were caught only because the checker
*crashed* on an uncaught exception, not by a named FAIL: `rc_wrong_attribute`,
`jr_no_region_mask`, `jr_include_label_0`, `jr_wrong_state_key` and the static
`adapter_missing_identity_import`. The direct calls were wrapped so that exceptions become
observations, and the identity lookups were made non-raising. This is a robustness
improvement with no check weakened. The committed checker catches every mutant through a
named check.

## Mutation results

The mutants were applied to the final checker **before it was committed**, in the
worktree under the guard.

**Behavioral mutants.** They are applied to `fov3d/scene/corridors.py` and executed into
`sys.modules` before the adapter is imported. **27/27 non-equivalent mutants are caught,
all by named checks**:

| class | mutants (all caught) |
|---|---|
| 1. region-code lookup | wrong attribute name; no `int`; `.get(..., -1)` default instead of `KeyError` |
| 2. own-label generation | connectivity 4; bool coercion instead of `uint8` truncation; `int64` output; foreground inverted; binary labels (`labs > 0`); relabelled output (`labs * 2`) |
| 3. joint-region mapping | no region mask; label 0 included; multiple labels accepted (`len == 0` guard); first label taken silently; `len > 1` condition; wrong state key; no `int32` cast; numpy return instead of `int`; message changed; `ValueError` instead of `RuntimeError` |
| 4. relation classification | equality reversed; strings swapped; always `ownership_cut`; always `own_support_gap`; `region_a`/`region_b` swapped; `region_a` duplicated; wrong tuple order; errors swallowed |

**Equivalent mutant**, recorded separately, not forced: dropping
`.astype(np.int32)` from `_own_labels`. `cv2.connectedComponents` already returns `int32`
(`CV_32S`) labels, and it showed 0/2000 differing outcomes on random masks and relation
queries. The probe does detect controls: connectivity 4 1039/2000, regions swapped
479/2000, label 0 included 1671/2000.

**Static/package mutants: 9/9 caught, all by named checks.**

| mutant | caught by |
|---|---|
| a duplicate `relation_origin` defined in the adapter | identity, `annotate_corridor` binding, and no-duplicate checks |
| the adapter missing the `_own_labels` identity import | identity re-export check |
| a lazy `fov3d.experiments` import in `scene.corridors` | dependency check |
| an eager `corridors` import in `fov3d/scene/__init__.py` | `__init__` unchanged, and the bare footprint |
| a production module importing `relation_origin` through the adapter | no-production-import check |
| an import added to `corridors.py` | imports-unchanged check |
| an existing corridor function edited (comment only) | existing functions source-identical |
| `own_support_labels` touched | untouched check |
| `fov3d/scene/__init__.py` touched (comment only) | `__init__` unchanged |

## Import/dependency audit and replay decisions

A fresh audit was measured at the Core-10 head (`274fdd6`) under the guard, for all 12
Partition-Graph producer/evaluator entry points (fresh-process `sys.modules`):

| entry point | loads `fov3d.scene.corridors` | loads the experiment `relations` adapter | decision |
|---|---|---|---|
| Phase-3 lift | **yes** (through `joint`) | no | replayed |
| Phase-4 analyzer | **yes** | **yes** | replayed (required; `relation_origin` is called there) |
| Phase-8b proposer / evaluator | **yes** (through `challenge_suite` → `joint`) | no | replayed |
| Phase-2 lift; Phase-5 analyzer; Phase-6, 7 and 8 proposers/evaluators | no | no | **not run** |

This matches the Core-6 topology. The AST scan found the direct importers of either module:
- `joint.py` and the adapter;
- the Core-6, 9 and 10 checkers;
- checker 4;
- `tools/partition_graph4_analyze.py`;
- `tools/partition_graph4_demo.py`, a post-producer demo that uses only
  `EVIDENCE_CLASS_NAMES`.

The dynamic-import sites are unchanged. **The Phase-8 proposer was not authorized and not
run.**

## Replay gates: byte comparisons and manifests

All replays ran from the worktree root under the guard, in order, each to a fresh
directory:

```text
.venv/bin/python tools/partition_graph3_lift.py previews/partition-graph-2-source-full previews/conceptual-core-10-phase3-full
.venv/bin/python tools/partition_graph4_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/conceptual-core-10-phase4-full
.venv/bin/python tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals previews/conceptual-core-10-phase8b-proposals
.venv/bin/python tools/partition_graph8b_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8b-proposals previews/partition-graph-8-evaluation previews/conceptual-core-10-phase8b-evaluation
```

```text
[partition-graph3-lift] COMPLETE {"causal_final_pairs": 86, "evidence_checks": 51, "evidence_mismatches": 0, "scene_final_pairs": 182, "states": 104}
[partition-graph4-analyze] COMPLETE {"causal_own_support_gap": 44, "causal_ownership_cut": 42, "causal_relations": 86, "states": 104, "target_depth_checks": 51, "target_depth_mismatches": 0}
[partition-graph8b-propose] COMPLETE {"eligible_candidates": 6489, "full_phase8_parity": 25, "raw_candidates": 18469, "scenarios": 5, "states": 125, "targets": 25, "truth_used": false}
[partition-graph8b-evaluate] COMPLETE {"full_eligible_recall": 0.9335820895522388, "full_integrated_covered": 27948, "full_integrated_residual": 1340, "scenarios": 5, "states": 125}
```

All four lines are string-identical to lines in earlier committed reports.

| gate | wall | accepted reference | accepted total | excluded | fresh = accepted scope | result | scope manifest sha256 |
|---|---|---|---|---|---|---|---|
| Phase 3 lift | 22.83 s | `partition-graph-4-lift` | 419 | — | 419 | byte-identical | `7eed664047384a43f50f51940cc4ad61d602513bb1095e076adc6c083ac3cbe3` |
| **Phase 4 analyzer** | 6.96 s | `partition-graph-4-full` | 425 | `demo/` 107, `demo-package-original/` 107 | 211 | **byte-identical** | `eca1b6ad798117de8d2de321e0ebfe6f92cb3e73a8f0b80e78e494f8a3f3cd8c` |
| Phase 8b proposer | 61.68 s | `partition-graph-8b-proposals` | 503 | — | 503 | byte-identical | `51a93fc464fc8ce00fc7f519ccadc25f539095be06de074788844b12ad6e7b7d` |
| Phase 8b evaluator | 16.67 s | `partition-graph-8b-evaluation` | 19 | `demo/` 8, `demo-package-original/` 8 | 3 | byte-identical | `243133b66237523147e1a869ee5b1bf97ee28ec9d817c5c059921e9b254c5715` |

Each comparison was two-sided:
- set equality after only the established exclusions, with no fresh file beneath an
  excluded path;
- `filecmp` with `shallow=False` on every pair;
- equal `LC_ALL=C` manifests.

`only_fresh`, `only_accepted`, `fresh_under_excluded` and `byte_diff` were 0 in every
gate. All four manifests equal the values from Cores 2–9.

**Accepted-tree integrity.** Per-file sha256 manifests of all 13 accepted trees were taken
before the first replay and after the instrumentation, and they are identical. They also
equal the Core-9 values.

## `relation_origin` execution count

A separate guarded instrumentation run wrapped the adapter's `relation_origin` binding and
ran `analyze_phase4` to a scratch directory, not `previews/`. Its 211-file output was also
byte-identical to `partition-graph-4-full`.

    relation_origin calls: 484  (ownership_cut 161, own_support_gap 323)

This reconciles exactly with the serialized product:
- 570 `relation_origin` values (203 `ownership_cut`, 367 `own_support_gap`);
- the computed 484 plus the 86 causal-final records, which reuse per-state annotations
  (42 `ownership_cut` and 44 `own_support_gap`, matching the COMPLETE line);
- the scene-final subset, 73 `ownership_cut` and 109 `own_support_gap` (n = 182), matches
  `docs/partition-graph-4-report.md`;
- the call split of 302 per-state and 182 scene-final was measured in Core 9.

`relation_origin` is **not** called in Phases 3 or 8b. Those gates cover the changed
`scene.corridors` module load only.

## Baseline and golden

The sealed baseline is 31/31 byte-identical (`[verify] SUMMARY passed=9 failed=0`). Golden
reports `[compare-golden] MISMATCHES 0`, taking 9.97 s. Both were run at `274fdd6` and
again at `d291e9a`. Gate A also covered:
- all conceptual checkers: Core-10 29/0, Core-9 24/0, Core-8 20/0, Core-7 22/0,
  Core-6 35/0, Core-5 38/0, Core-4 32/0, Core-3 27/0, Core-2 20/0, Core-1 13/0;
- the Partition-Graph checkers 1–8b, all passing and unmodified;
- the facade check at 16/0;
- `git diff --check`, which was clean.

## Changed-path → executed-gate coverage

| changed path | kind | exercised by | execution evidence |
|---|---|---|---|
| `fov3d/scene/corridors.py`, appended cluster | moved functions | A (Core-10: 29 checks; checker 4 calls `relation_origin`), **Phase 4** | 484 `relation_origin` executions (instrumented); 211/211 byte-identical |
| `fov3d/scene/corridors.py` module, with its imports and existing functions unchanged | changed module (append) | A, Phase 3, Phase 4, Phase 8b P/E | import audit; all byte-identical (Phase 3 executes the unchanged corridor functions, as measured in Core 6) |
| adapter import (+ `fov3d.scene.corridors`) | changed module dependency | A (checker 4; Core-10 identities), Phase 4 | as above |
| `annotate_corridor`'s `relation_origin` binding | changed dependency binding | Phase 4 | `__globals__` identity; output byte-identical |
| `tools/dev/check_conceptual_core10.py` | new checker | A; mutation harnesses | 29/29; 27/27 behavioral and 9/9 static mutants caught |

## Repairs and deviations

1. **No production repair was needed.** The extraction was a pure append plus removal,
   and no import was orphaned.
2. **Provenance comment.** Two comment lines precede the appended block in
   `corridors.py`. They name its origin and the descriptive meaning of `ownership_cut`
   versus `own_support_gap`. They are outside every function segment and every import
   statement, so identity checks are unaffected.
3. **Checker robustness, before the commit.** Exceptions from direct calls now become
   named observations, and the identity lookups are non-raising. The committed checker is
   the final form, and no check was weakened.
4. **Additional evidence.** It comprises the instrumented `relation_origin` count and its
   reconciliation, the equivalence probe, the `symtable` scan, and the informational
   `_own_labels`/`own_support_labels` differential below. It used throw-away harnesses in
   the session scratchpad, which are not committed.

No other deviation. The replay commands, inputs, references and exclusions are the
established ones.

## Unresolved / deferred (explicitly not fixed)

1. **`relations.component_lineage` versus `fov3d.scene.lineage._lineage`** appear
   behaviorally duplicative: Core 9 measured 0/3000 differing outcomes. They remain
   separate.
2. **`relations._own_labels` versus `relations.own_support_labels`** are implementation
   duplicates. Their bodies are identical except for the parameter name (`layer_support`
   versus `support`), and they give 0/3000 differing outputs on bool and float masks. After
   Core 10, `_own_labels` lives in `scene.corridors` while `own_support_labels` stays in
   the adapter. They are **not** unified in Core 10.
3. The **`attach_state_region_codes` rename** remains deferred.
4. The **consumerless compatibility aliases** (Cores 2, 5 and 6) remain deferred.
5. The **target-relative `HeadEvidence` placement** remains deferred.

Also carried over: the separate Phase-2 and Phase-3 boundary lineages, the question of
stricter one-region-per-code validation, and the shared checkout's stale local `main`.
None of these was touched. No Core-11 migration was made in this run.

## Success marker

    CONCEPTUAL_CORE10_RELATION_ORIGIN_PRESERVES_BEHAVIOR
