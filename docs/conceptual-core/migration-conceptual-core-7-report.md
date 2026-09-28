# Migration Conceptual Core 7 — report (2026-09-27)

Executed by Claude Code on the Ubuntu workstation against the committed contract
`docs/migration-conceptual-core-7.md`. Every number below is **MEASURED** from the
command shown, unless it is marked otherwise.

## Provenance

| item | value |
|---|---|
| branch | `migration/conceptual-core-7` |
| starting head = `main` | `e681392af8abc7d5fc6b2116a0c5bb534bc0ea7e` (verified; the branch was created at `main`) |
| scientific parent | Conceptual Core 6 @ `41a365c49cbec52a350139238753b087b8f29da0` (an ancestor of `main`; `41a365c..e681392` changes only `docs/chat-handoff.md`) |
| Code commits (on Luiz's Core-7 instruction) | `73366d5` contract, **committed before any production change** · `94d82ac` extraction, tool retirement and stray-note deletion · `a3039b2` Core-7 checker · `fbf3872` conceptual map · the commit that adds this report |
| gates measured at | Gate A and Gates B–F at `a3039b2`; the whole of Gate A again at `fbf3872`. `fov3d/` and `tools/` are identical at both |
| execution location | an isolated `git worktree` of `migration/conceptual-core-7` (see *Concurrent-checkout incident*) |
| final head | the commit that adds this report |

## Concurrent-checkout incident (environment integrity)

At **15:26:49–15:26:53 −0300**, six seconds after `a3039b2` was committed, a process that
was **not** Claude Code operated on the shared working copy `/home/lvelho/rd/f3d-vision`.
Its reflog entries:

    checkout: moving from migration/conceptual-core-7 to main
    pull --ff-only: Fast-forward            (local main a48124e -> e681392)
    checkout: moving from main to chatgpt-write-test-1790533609
    checkout: moving from chatgpt-write-test-1790533609 to main

No `chatgpt-write-test-*` branch remained locally or on `origin`, and no process was still
running afterwards. **No Core-7 work was lost**: the branch still pointed at `a3039b2`,
which at that time was unpushed.

The one Core-7 measurement taken during the switch, an import audit, is **invalid and
discarded**. It reported that the Phase-3 lift does *not* load `fov3d.scene.lineage`,
which is impossible for Core-7 code, so it had executed `main`'s files. Everything
measured before the switch was re-measured afterwards.

**Protection (Luiz's choice).** Execution continued in an isolated worktree,
`git worktree add <scratchpad>/core7/wt migration/conceptual-core-7`:
- the untracked data directories are symlinked in: `previews/`, `.venv/`, and the five
  ignored `scenes/classroom/` asset entries;
- `fov3d` resolves to the worktree's code, and there is no `.pth` redirect;
- producers record input paths through `Path.resolve()`, which follows the symlinks, so
  the recorded paths equal the accepted ones;
- **every** measurement command ran under a guard that checks branch, HEAD and a clean
  tracked tree before and after, and marks the result invalid on any change. The guard
  never tripped.

The shared checkout was left exactly as the other process left it (on `main`, clean).

## Files changed (main...final head)

| file | change |
|---|---|
| `docs/migration-conceptual-core-7.md` | contract (`73366d5`) |
| `fov3d/scene/lineage.py` | new: `_lineage` and `_target_component_raster`, generated from the exact source segments of `main`'s `joint.py` (`94d82ac`) |
| `fov3d/experiments/classroom_partition/joint.py` | two definitions removed; imported from `fov3d.scene.lineage`; no import orphaned (`94d82ac`) |
| `tools/dev/apply_partition_graph4_lineage_fix.py` | replaced by a non-mutating **tombstone** (`94d82ac`) |
| `docs/core6-note.md` | **deleted** (a stray one-line placeholder, `94d82ac`) |
| `tools/dev/check_conceptual_core7.py` | new checker (`a3039b2`) |
| `docs/conceptual-core-map.md` | Core-7 status, row and order (`fbf3872`) |
| `docs/migration-conceptual-core-7-report.md` | this report |

The following are untouched (`git diff e681392..HEAD` is empty for each):
- `fov3d/scene/__init__.py`, `model.py`, `partition.py`, `boundaries.py`, `corridors.py`,
  `sphere.py` and `synthetic.py`;
- `relations.py`, including `component_lineage`;
- `lift.py`, which holds the Phase-2 boundaries;
- `incidental.py`, `integration.py`, `challenge_suite.py`, `benchmark.py` and
  `prefix_benchmark.py`;
- `fov3d/epistemic`, `fov3d/geometry` and `fov3d/reconstruction`;
- every other tool and checker, and `scripts/`;
- `tests/`, `CLAUDE.md` and `docs/chat-handoff.md`;
- sealed runtime files (baseline 31/31);
- the 13 accepted trees.

## Final lineage API and dependency direction

    numpy, typing.Any
    fov3d.scene.model   ScenePartitionGraph
            -> fov3d.scene.lineage      (explicit import; NOT in fov3d.scene.__all__)
                   _lineage(prev_rc, curr_rc) -> {initial, births, merges, splits, deaths, persistent_links}
                   _target_component_raster(graph, region_code, target_id) -> int32 labels 0 | 1..k
            -> fov3d.experiments.classroom_partition.joint
                   lift_joint_run: joint.py:302 current_target_labels = _target_component_raster(...)
                                   joint.py:303 lineage = _lineage(previous_target_labels.get(iid), current_target_labels)
                                   joint.py:304 previous_target_labels[iid] = current_target_labels

`lift_joint_run` still maintains `previous_target_labels` itself.

Fresh-process footprints (`python -I`, in the worktree):
- `import fov3d.scene` loads exactly `fov3d`, `fov3d.scene`, `fov3d.scene.model` and
  `fov3d.scene.sphere`. It does not load `cv2`, `partition`, `boundaries`, `corridors` or
  `lineage`.
- `import fov3d.scene.lineage` adds only `fov3d.scene.lineage`. It loads no `cv2`, so the
  module is NumPy-only.

## Literal source / AST / global-binding audit

1. **Source text.** `ast.get_source_segment` of `_lineage` and `_target_component_raster`
   in `lineage.py` is **byte-for-byte identical** to accepted `main`'s `joint.py`. The
   module was generated from those segments, and the `_lineage` docstring is preserved.
2. **AST.** The ASTs, docstrings included, are identical.
3. **Global bindings.** `np`, `Any` and `ScenePartitionGraph` in `lineage.py` are the same
   objects as in `main`'s `joint.py`. `lift_joint_run` resolves both names from
   `fov3d.scene.lineage`.
4. **The rest of `joint.py` is unchanged.** All 9 remaining top-level definitions are
   source-text identical to main, as are all non-import module statements. That covers
   `StereoOps`, `_default_stereo_ops`, `build_joint_graph`, `_rectified_core_directions_h`,
   `update_controller_seen_any`, `_append_raw_footprints`, `attach_state_region_codes`,
   `_controller_expected_never` and `lift_joint_run`. The extraction orphaned no import,
   because `np`, `Any` and `ScenePartitionGraph` are still used.
5. `relations.py` and therefore `relations.component_lineage` are unchanged.
6. The controller replay, corridors, boundaries, partition and the Phase-2 code are
   unchanged (item 4 and the file table).
7. A `symtable` scan finds 0 unbound globals in `lineage.py`, `joint.py` and the
   tombstone.

## Historical patch tool: explicit retirement

`tools/dev/apply_partition_graph4_lineage_fix.py` (added in `52c9395`) was a one-shot
exact-source-replacement repair for the Phase-3 lineage bug
(`docs/partition-graph-4-report.md`).

- **Before Core 7** (measured on a scratch copy of the tree at `e681392`): it printed
  `[partition-graph4-lineage-fix] already applied`, exited 0 and wrote nothing, because
  the fixed `_lineage` text was present in `joint.py`. After the move that text is gone,
  so the old script would raise `RuntimeError`.
- **Now** it is a tombstone with the same path. Its docstring states that the fix is
  incorporated, that the accepted implementation lives in `fov3d.scene.lineage`, and that
  Git history (`52c9395`) keeps the original script. It imports nothing but
  `__future__.annotations`, and it calls only `print`, `main` and `SystemExit`.
- **Measured in Gate A:** it prints exactly `[partition-graph4-lineage-fix] RETIRED`,
  exits 0, and leaves `git status` and `git diff` unchanged.

It is retired, not accidentally broken. The historical Phase-4 report that describes the
original script is left unchanged as the historical record.

## Checker and mutation evidence

`tools/dev/check_conceptual_core7.py` has **22 checks** and runs in about 0.32 s wall.
Every expectation was derived by hand from the contract.

| contract item | checks |
|---|---|
| 1 | initial: `{True, 2, 0, 0, 0, 0}` for `[-5, 0, 3, 3, 7]`, with exact key order, `initial` a `bool` and every count an `int` |
| 2–6 | stable persistence `(0,0,0,0,1)`; birth; death; merge (two previous → one current); split (one previous → two current) |
| 7 | mixed fixture: C1←{P1,P2} merge, P3→{C2,C3} split, P4 dies, P5→C5 persists, C4 and C6 are born, giving `(births 2, merges 1, splits 1, deaths 1, persistent 3)`. Births ≠ deaths on purpose |
| 8 | `int32` coercion of float **previous and current** labels; zero and negative codes are not components |
| 9 | the exact `ValueError("lineage raster shape mismatch")` for `(2,2)` vs `(2,3)`, and for the *broadcastable* `(1,3)` vs `(2,3)` |
| 10–14 | `_target_component_raster` with `region_ids` stored as `(c002, c010, c001)`, mapping to codes `5, 2, 9`: neither lexical nor code order. A decoy `region_code` attribute is present on every region. Checks: missing object → all-zero `int32` of the right shape; exact labels `1..3` by stored order; non-target cells stay 0; `str(target_id)` lookup |
| 15–17 | `joint` identities; no duplicates; `lineage.py` imports only `__future__`, `typing`, `numpy` and `.model`; no production import through `joint` |
| 18 | a fresh bare `fov3d.scene` loads none of `cv2`, `partition`, `boundaries`, `corridors` or `lineage`; a fresh `fov3d.scene.lineage` is NumPy-only |
| 19 | the retired tool: no write or replacement capability (AST); the exact `RETIRED` stdout; exit 0; the `joint.py` sha256 is unchanged |

**Behavioral mutants.** They are applied to `lineage.py` and executed into `sys.modules`
before `joint` is imported. All 15 required classes are covered, among 31 mutants:

- current codes unsorted (equivalent), current filter `>= 0` or `!= 0`, previous filter
  `>= 0` or `!= 0`;
- no current or previous `int32` coercion;
- initial births counting 0, and `initial` as an int;
- births from previous labels, deaths from current labels;
- merge threshold `>= 1` or `> 2`, split threshold `>= 1` or `> 2`;
- `persistent_links <= 1`, and persistent counted from children;
- overlap as union, containment or majority;
- shape mismatch accepted, and the message changed;
- counts without `int()` (equivalent), and the key order changed;
- target region ids sorted, labels starting at 0, state-global codes as labels, the wrong
  attribute, a missing target not zero, `int64` output, an int key lookup.

The first run caught **28/29** non-equivalent mutants. `no_prev_int32_coercion` survived,
because only float *current* labels were tested; a random probe showed it changes behavior
in 123/600 cases. The coercion check was extended to float previous labels **before** the
checker was committed. The final result is **29/29 caught**.

Two mutants are equivalent, each with 0/600 differing random cases. The probe does detect
controls: births from previous 281/600, sorted `region_ids` 423/600.

| equivalent mutant | reason |
|---|---|
| current codes not sorted | every count is an order-independent sum |
| counts without `int()` | `sum()` of Python bools is already a Python `int` |

**Static, package and tool mutants: 11/11 caught.**

| mutant | caught by |
|---|---|
| a duplicate `_lineage` in `joint.py` | identities and no-duplicates checks |
| the `_target_component_raster` alias missing from `joint` | checker exits nonzero (`AttributeError`) |
| a lazy `fov3d.experiments` import in `lineage.py` | the allowed-imports check |
| `lineage.py` imports `cv2` | allowed imports, and the NumPy-only footprint |
| `fov3d/scene/__init__.py` eagerly imports `lineage` | bare-footprint check |
| `relations.py` takes `_lineage` through `joint` | no-production-import check |
| **tool reverted to the original repair script** | no-write check, and marker/exit check |
| tool prints `RETIRED` but appends to `joint.py` | no-write check, and the `joint.py` hash (the scratch copy's hash changed) |
| tool rewrites `joint.py` with identical bytes | no-write (AST) check |
| tool prints the wrong marker | marker check |
| tool exits nonzero | exit check |

The behavioral and static harnesses were run again from the isolated worktree, under the
guard, with identical results: 29/29, 2 equivalent, and 11/11.

## Dependency/import audit and conditional-gate decision

This audit was measured in the worktree, under the guard, replacing the invalid one.

| entry point | loads `joint` / `scene.lineage` | gate |
|---|---|---|
| Phase-3 lift | yes / yes | B |
| Phase-4 analyzer | yes / yes (through `relations` → `joint`) | C |
| Phase-5 analyzer | no / no | D (contract-required) |
| Phase-8b proposer / evaluator | yes / yes | E / F |
| Phase-2 lift; Phase-6, 7 and 8 proposers/evaluators | **no / no** | not triggered |

An AST scan of every tracked `.py` file found that only `joint.py` and the Core-7 checker
import `fov3d.scene.lineage`. Nested imports of `joint`/`lineage` occur only in checkers,
and the dynamic-import sites are unchanged. `fov3d/scene/__init__.py` is unchanged.

**Decision:** no conditional gate is required. The Phase-8 proposer was **not authorized
and not run**.

## Gate A — interactive

Run in the worktree under the guard at `a3039b2`, then the whole gate again at `fbf3872`,
with identical results:

```text
compile: 4 changed Python files OK
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
retired tool: "[partition-graph4-lineage-fix] RETIRED" exit=0 exact=yes tree_unchanged=yes
[consolidation3-facade-check] SUMMARY checked=16 failed=0
[verify] 31 files tracked at baseline-classroom-oracle1-2026-09-25 are byte-identical in the working tree
[verify] SUMMARY passed=9 failed=0
[compare-golden] compared {"looks": 104, "npz_arrays_compared": 1348, "rgb_arrays_excluded": 337, "targets": 25}
[compare-golden] MISMATCHES 0
git diff --check: clean
import fov3d.scene -> ['fov3d', 'fov3d.scene', 'fov3d.scene.model', 'fov3d.scene.sphere'] | cv2 False
import fov3d.scene.lineage -> ['fov3d', 'fov3d.scene', 'fov3d.scene.lineage', 'fov3d.scene.model', 'fov3d.scene.sphere'] | cv2 False
```

The golden comparison took 9.95 s. The baseline's `classroom-assets` step (48/48 required)
passed through the linked asset entries.

## Replay gates B–F

All commands were run from the worktree root, in order, each to a fresh directory and each
under the guard. `previews/` is the shared tree reached through the symlink.

```text
B .venv/bin/python tools/partition_graph3_lift.py previews/partition-graph-2-source-full previews/conceptual-core-7-phase3-full
C .venv/bin/python tools/partition_graph4_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/conceptual-core-7-phase4-full
D .venv/bin/python tools/partition_graph5_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/partition-graph-4-full previews/conceptual-core-7-phase5-full
E .venv/bin/python tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals previews/conceptual-core-7-phase8b-proposals
F .venv/bin/python tools/partition_graph8b_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8b-proposals previews/partition-graph-8-evaluation previews/conceptual-core-7-phase8b-evaluation
```

```text
B [partition-graph3-lift] COMPLETE {"causal_final_pairs": 86, "evidence_checks": 51, "evidence_mismatches": 0, "scene_final_pairs": 182, "states": 104}
C [partition-graph4-analyze] COMPLETE {"causal_own_support_gap": 44, "causal_ownership_cut": 42, "causal_relations": 86, "states": 104, "target_depth_checks": 51, "target_depth_mismatches": 0}
D [partition-graph5-analyze] COMPLETE {"challenge_relations": 108, "challenge_states": 41, "challenge_targets": 4, "states": 104, "target_gap_violations": 0}
E [partition-graph8b-propose] COMPLETE {"eligible_candidates": 6489, "full_phase8_parity": 25, "raw_candidates": 18469, "scenarios": 5, "states": 125, "targets": 25, "truth_used": false}
F [partition-graph8b-evaluate] COMPLETE {"full_eligible_recall": 0.9335820895522388, "full_integrated_covered": 27948, "full_integrated_residual": 1340, "scenarios": 5, "states": 125}
```

Every required value matches. All five lines are string-identical to lines in earlier
committed reports.

| gate | wall | accepted reference | accepted total | excluded | producer/evaluator files (fresh = accepted scope) | result | scope manifest sha256 |
|---|---|---|---|---|---|---|---|
| B Phase-3 joint lift | 22.90 s | `partition-graph-4-lift` | 419 | — | 419 | byte-identical | `7eed664047384a43f50f51940cc4ad61d602513bb1095e076adc6c083ac3cbe3` |
| C Phase-4 analyzer | 6.91 s | `partition-graph-4-full` | 425 | `demo/` 107, `demo-package-original/` 107 | 211 | byte-identical | `eca1b6ad798117de8d2de321e0ebfe6f92cb3e73a8f0b80e78e494f8a3f3cd8c` |
| D Phase-5 analyzer | 8.37 s | `partition-graph-5-full` | 225 | `demo/` 7, `demo-package-original/` 7 | 211 | byte-identical | `77f5ae3d408900c8b2428553f22a97fae60aeddef34ea1f500a78e39d07c68eb` |
| E Phase-8b proposer | 62.06 s | `partition-graph-8b-proposals` | 503 | — | 503 | byte-identical | `51a93fc464fc8ce00fc7f519ccadc25f539095be06de074788844b12ad6e7b7d` |
| F Phase-8b evaluator | 16.72 s | `partition-graph-8b-evaluation` | 19 | `demo/` 8, `demo-package-original/` 8 | 3 | byte-identical | `243133b66237523147e1a869ee5b1bf97ee28ec9d817c5c059921e9b254c5715` |

All five scope manifests equal the Core-2 through Core-6 values. The comparison method is
the same as in Cores 3–6:
- two-sided set equality after only the demonstrated `demo/` and
  `demo-package-original/` exclusions, with no fresh file under an excluded path;
- `filecmp` with `shallow=False` on every pair;
- equal `LC_ALL=C` manifests.

In every gate, `only_fresh`, `only_accepted`, `fresh_under_excluded` and `byte_diff` were
all 0.

**Accepted trees unchanged.** Per-file sha256 manifests of the 13 accepted trees are
identical before Gate B and after Gate F, and they equal the Core-6 manifests.

## Changed-path → execution-gate coverage

| changed path | kind | exercised by | execution evidence |
|---|---|---|---|
| `fov3d/scene/lineage.py` module (NumPy, `.model`) | new module | A (Core-7; checkers 3, 4, 5 and 8 through `joint`), B, C (load), E, F (load) | import probe; every run byte-identical |
| `_lineage`, `_target_component_raster` | moved | A (Core-7: 22 checks; checker 4 calls `_lineage`), **B** | `lift_joint_run` calls both for every target at every state (`joint.py:302-304`). The fresh Phase-3 `summary.json` holds **104 lineage records: 25 initial, one per target, and 79 non-initial**. `lineage_totals_excluding_initial = {births 10, deaths 1, merges 3, splits 0}`, **exactly** the Phase-4 report's accepted lineage `{births 10, merges 3, splits 0, deaths 1}`, byte-identical |
| `joint.py` import (+ `fov3d.scene.lineage`) | changed module dependency | A, B, C (`relations` imports `joint`), E, F | as above |
| `lift_joint_run`'s lineage bindings | changed dependency binding | B | `__globals__` identity; output byte-identical |
| `tools/dev/apply_partition_graph4_lineage_fix.py` | retired → tombstone | A (executed; Core-7 checks 21–22) | exact marker, exit 0, tree unchanged; 5 tool mutants caught |
| `tools/dev/check_conceptual_core7.py` | new checker | A; mutation harnesses | 22/22; 29/29 behavioral and 11/11 static mutants caught |
| `docs/core6-note.md` deletion | repository cleanup | — | no runtime meaning (no reference in code) |

## Confirmations

- **`relations.component_lineage`** and all of `relations.py` are untouched
  (`git diff` empty).
- **Also untouched:** the controller `seen_any` replay, corridors, boundaries, partition
  and the Phase-2 boundary code. The replay code in `joint.py` is source-text identical;
  the other modules have an empty `git diff`.
- **Package footprint.** `fov3d/scene/__init__.py` is unchanged, and the bare-import
  footprint is unchanged.
- **No scientific/runtime behavior changed.** The evidence:
  - text-identical functions with identical global bindings;
  - byte-identical Phase 3, 4, 5 and 8b producer output, and Phase-8b evaluator output;
  - identical lineage records and totals;
  - golden `MISMATCHES 0`, and baseline 31/31.

## Repairs and deviations

1. **Checker strengthened before commit.** The coercion check now includes float
   previous labels, after mutation testing found the `prev` coercion gap. The checker was
   committed only in its final 22-check form.
2. **Execution moved to an isolated worktree**, with a guard, after the concurrent
   checkout switch; Luiz chose this. The one invalid measurement was discarded and
   re-taken, and every Core-7 measurement quoted here comes from the worktree under the
   guard.
3. **Additional evidence beyond the contract.** It comprises the source-text and
   global-binding identity checks, the pre-change tool behavior, the import probe and AST
   scan, the equivalence probe, and the accepted-tree manifests before and after. It used
   throw-away harnesses in the session scratchpad, which are not committed.

No other deviation. The gate commands, inputs, output directories and references are
exactly the contract's. No conditional gate was triggered.

## Unresolved

1. **Shared-working-copy hazard.** A process running a `chatgpt-write-test` sequence
   checked out branches in the workstation's working copy mid-step. It should be
   determined what performed it, most likely a Chat repository-write test through a local
   agent. Chat writes should use GitHub or a separate clone or worktree, not
   `/home/lvelho/rd/f3d-vision`, which Claude Code uses for measured execution. The shared
   checkout was left on `main`.
2. **Local `main` is stale for other readers.** The other process fast-forwarded local
   `main` to `e681392`. That is harmless and consistent with `origin/main`, but it was
   done outside the loop.
3. **Consumerless aliases.** `joint._target_component_raster` has one consumer,
   `lift_joint_run`, and `joint._lineage` has two, `lift_joint_run` and checker 4. The
   earlier consumerless aliases (Core 2, Core 5, Core 6) remain a single pending policy
   decision.
4. The Core-2 through Core-6 items are carried over unchanged.

## Recommendation (Conceptual Core 8 only)

After Core 7, `joint.py` holds three groups:
- the Phase-3 composition (`build_joint_graph`, `attach_state_region_codes`,
  `lift_joint_run`);
- the controller `seen_any` replay (`StereoOps`, `_default_stereo_ops`,
  `_rectified_core_directions_h`, `update_controller_seen_any`, `_append_raw_footprints`),
  which depends on calibration and stereo ops;
- `_controller_expected_never`.

The next bounded conceptual step is map item 7, **topology/relations**: make the relation
extraction in `relations.py` operate on the generic scene graph. That is larger and
closer to scientific semantics, so it needs a Chat-designed contract. It should start from
a repository audit of which `relations.py` functions are pure scene-graph operations and
which are `FineEvidence`/Phase-4 replay.

A smaller preparatory Core 8 would be `attach_state_region_codes`. Despite its name it
attaches nothing: it is a pure `ScenePartitionGraph` + raster **consistency validator**.
It checks that the set of graph `state_region_code` values equals the raster's codes,
then calls `graph.validate()`. It is used by `lift_joint_run` (`joint.py:290`) and
checker 3. Luiz and Chat should decide whether that is worth a separate step, perhaps
with a clearer name kept behind a compatibility alias, or should fold into the relations
work. The controller `seen_any` replay should stay experiment-side.

## Success marker

    CONCEPTUAL_CORE7_LINEAGE_PRESERVES_BEHAVIOR
