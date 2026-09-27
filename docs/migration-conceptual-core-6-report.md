# Migration Conceptual Core 6 — report (2026-09-27)

Executed by Claude Code on the Ubuntu workstation against the committed contract
`docs/migration-conceptual-core-6.md`. Every number below is **MEASURED** from the
command shown, unless it is marked otherwise.

## Provenance

| item | value |
|---|---|
| branch | `migration/conceptual-core-6` |
| parent accepted milestone | `main` @ `6ff0da753acc8f20c84bf83e82c59db4f58de025` (merge base verified; `origin/main` is the same commit) |
| starting head | `c049c7acbdca880f043c2ad7507630591100cfa0`, verified: 3 commits `118161a`, `5e84db0`, `c049c7a`. `fov3d/scene/corridors.py` was complete; `joint.py`, the contract, the checker and the handoff were not written |
| Code commits (on Luiz's instruction to complete the proposal) | `fde3cd6` `joint.py` wiring · `6a4fdd9` contract and Chat Handoff · `39e6a04` Core-6 checker · `71d25c5` conceptual map · the commit that adds this report |
| gates measured at | Gate A at `39e6a04`, then the whole of Gate A again at `71d25c5`; Gates B–F at `39e6a04`. `fov3d/` and `tools/` are identical at both commits |
| final head | the commit that adds this report |

**Authorship note.** Unlike Cores 3–5, the implementation beyond `corridors.py`, and the
contract and checker, were written by Claude Code under Luiz's explicit delegation. Chat
has not yet reviewed them. The contract was committed (`6a4fdd9`) and the checker was
mutation-tested before any replay gate ran.

## Files changed (main...final head)

| file | change |
|---|---|
| `fov3d/scene/corridors.py` | new (Chat, `5e84db0`/`c049c7a`): `_component_boundary`, `_line_cells`, `gap_corridor`, `corridors_for_object` |
| `fov3d/experiments/classroom_partition/joint.py` | four definitions removed; imported from `fov3d.scene.corridors`; the two imports orphaned by the move (`cv2`, `head_unit_from_angles`) dropped (Code, `fde3cd6`) |
| `tools/dev/check_conceptual_core6.py` | new (Code, `39e6a04`) |
| `docs/migration-conceptual-core-6.md` | contract (Code, `6a4fdd9`) |
| `docs/chat-handoff.md` | records accepted Core 5 (`6ff0da7`) and Core 6 as the active step (Code, `6a4fdd9`) |
| `docs/conceptual-core-map.md` | Core-6 status, `joint.py` row and order (Code, `71d25c5`) |
| `docs/core6-note.md` | a placeholder (`# Core 6`) from Chat's interrupted writes (`118161a`). It is left untouched; see unresolved item 1 |
| `docs/migration-conceptual-core-6-report.md` | this report |

The following are untouched (`git diff 6ff0da7..HEAD` is empty for each):
- `fov3d/scene/__init__.py`, `model.py`, `partition.py`, `boundaries.py`, `sphere.py` and
  `synthetic.py`;
- `lift.py` (Phase-2 boundaries), `relations.py`, `incidental.py`, `integration.py`,
  `challenge_suite.py`, `benchmark.py` and `prefix_benchmark.py`;
- `fov3d/epistemic`, `fov3d/geometry` and `fov3d/reconstruction`;
- every existing checker and tool, and `scripts/`;
- `tests/` (golden signatures) and `CLAUDE.md`;
- sealed runtime files (baseline 31/31);
- the 13 accepted preview trees.

## Final corridor API and dependency direction

    numpy, cv2, collections.Counter, typing.Any
    fov3d.geometry.head_chart   chart_grid, head_unit_from_angles
    fov3d.scene.model           ScenePartitionGraph
            -> fov3d.scene.corridors      (explicit import; NOT in fov3d.scene.__all__)
                   _component_boundary(mask) -> bool raster
                   _line_cells(y0, x0, y1, x1) -> int32 (N, 2) (y, x)
                   gap_corridor(graph, state, region_a, region_b, target_id, seen_any, domain, grid_deg) -> dict
                   corridors_for_object(graph, state, target_id, seen_any, domain, grid_deg) -> list[dict]
            -> fov3d.experiments.classroom_partition.joint
                   lift_joint_run (Phase 3): joint.py:352 per state, joint.py:405 final scene

**`seen_any` stays explicit.** It is a required positional-or-keyword parameter of both
functions, with no default; the checker asserts this. `fov3d.scene.corridors` imports
nothing from `fov3d.experiments`; the checker asserts this too, and a mutant that imports
`update_controller_seen_any` is caught. `lift_joint_run` computes the controller evidence
experiment-side and passes it in: `seen` at `joint.py:352` and `evidence[iid]` at
`joint.py:405`.

Fresh-process footprints (`python -I`):
- `import fov3d.scene` loads exactly `fov3d`, `fov3d.scene`, `fov3d.scene.model` and
  `fov3d.scene.sphere`. It does not load `cv2`, `partition`, `boundaries` or `corridors`.
  This is unchanged from Cores 4 and 5.
- `import fov3d.scene.corridors` adds `fov3d.geometry`, `fov3d.geometry.head_chart` and
  `fov3d.scene.corridors`, and loads `cv2`, as the contract allows. It does not load
  `fov3d.scene.partition`.

## Literal-extraction audit

1. **Source text.** `ast.get_source_segment` of each of the four functions in
   `corridors.py` is **byte-for-byte identical** to accepted `main`'s `joint.py`. That
   includes the `gap_corridor` docstring, its 4 comments and every annotation. The ASTs
   are identical too.
2. **Identical global bindings.** Every module-level name the four functions reference
   resolves in `corridors.py` to the same object as in `main`'s `joint.py`: `Counter`,
   `Any`, `cv2`, `np`, `chart_grid`, `head_unit_from_angles` and `ScenePartitionGraph`.
   Within `corridors.py`, `gap_corridor` resolves `_component_boundary` and `_line_cells`
   to the module's own definitions, and `lift_joint_run` resolves `corridors_for_object`
   to `fov3d.scene.corridors`.
3. **The rest of `joint.py` is unchanged.** The four functions were removed by exact AST
   line ranges, each with its trailing blank separators. All 11 remaining top-level
   definitions are source-text identical to main, as are all non-import module
   statements. That covers `build_joint_graph`, `update_controller_seen_any`,
   `_append_raw_footprints`, `_rectified_core_directions_h`, `attach_state_region_codes`,
   `_lineage`, `_target_component_raster` and `lift_joint_run`.
4. **Imports.** Only `cv2` and `head_unit_from_angles` were used before the move and
   unused after it, so only they were dropped. The pre-existing unused imports
   (`Iterable`, `math`, `ObjectHypothesis`) and the Core-5 aliases were left alone.
   Nothing in the repository reaches `cv2` or `head_unit_from_angles` through `joint`.
5. A `symtable` scan finds 0 unbound global references in `corridors.py` and `joint.py`.
6. `relations.py`, the Phase-2 code in `lift.py`, the controller `seen_any` replay and the
   lineage are unchanged, as items 3 and the file table show.

## Compatibility

`joint._component_boundary`, `joint._line_cells`, `joint.gap_corridor` and
`joint.corridors_for_object` are the same objects as in `fov3d.scene.corridors`, with no
duplicate definitions; the checker asserts both. Consumers through `joint`:
- `corridors_for_object` is used by `lift_joint_run` and by the unmodified checkers 3
  (`check_partition_graph3.py:20`) and 4 (`check_partition_graph4.py:20`);
- `gap_corridor`, `_line_cells` and `_component_boundary` have no in-repo consumer
  besides the Core-6 identity check. They are contract-mandated aliases, like the Core-5
  ones.

No production module takes a corridor name through `joint`; the checker enforces this.

## Dependency/import audit and conditional-gate decision

A fresh-process probe of all 12 Partition-Graph producer/evaluator entry points gave:

| entry point | loads `joint` / `scene.corridors` | gate |
|---|---|---|
| Phase-3 lift | yes / yes | B |
| Phase-4 analyzer | yes / yes (through `relations` → `joint`) | C |
| Phase-5 analyzer | no / no | D (contract-required) |
| Phase-8b proposer / evaluator | yes / yes | E / F |
| Phase-2 lift; Phase-6, 7 and 8 proposers/evaluators | **no / no** | not triggered |

An AST scan of every tracked `.py` file found no lazy or dynamic import of `joint` or
`corridors` from a Phase-2, 6, 7 or 8 path. The dynamic-import sites are unchanged since
Core 5. `fov3d/scene/__init__.py` is unchanged.

**Decision:** no conditional gate is required. The Phase-8 proposer was **not authorized
and not run**.

Execution scope: `relations`, `incidental`, `integration` and `challenge_suite` reference
no corridor name, so Gates C, E and F exercise the changed module *loading*. Only Gate B
(and the Gate-A checkers 3, 4 and 6) execute the moved functions.

## Checker and mutation evidence

`tools/dev/check_conceptual_core6.py` has **35 checks** and runs in about 0.33 s wall.
Every expected value was derived by hand from the contract. All of them passed on the
first run against code proven text-identical to main, so none was fitted to output.

| area | checks |
|---|---|
| `_component_boundary` | single cell; solid 3×3 block keeps only the ring; edge-touching 4×4 block (the zero border erodes the frame); plus shape (the all-ones kernel erodes the centre) |
| `_line_cells` | horizontal; vertical; diagonal; shallow slope (`rint(0.5) = 0`, exact int32 and shape); steep slope; reversed endpoints; one point |
| `gap_corridor` | 4×12 fixture. Object 7 has components A (code 1) and B (code 2) and a middle cell; objects 12 and 9 lie between them (numeric order 9 < 12, string order "12" < "9"). The regions dict is out of code order. `seen_any` is also true on endpoints and off-line cells. Checks: key order; closest pair `[[1,2],[1,9]]` on a distance **tie** (first argmin); exact `corridor_yx` as Python ints; exact `endpoint_gap_deg` (yaw from x, pitch from y); 6 interior cells; base/same/other = 2/1/3; `other_object_counts` items `[("9",2),("12",1)]`; seen/unseen 2/4, fractions 2/6 and 4/6; identity fields and the semantics string; a reversed query keeping the query-order endpoints; zero interior (counts 0, fractions `None`); `KeyError`; `RuntimeError` through a patched empty boundary (unreachable with the real boundary function); a Euclidean nearest pair `(0,0)→(3,3)` where L1 would choose `(0,5)` |
| `corridors_for_object` | 3 regions → 3 pairs in `region_ids` order; 2 regions → 1 pair; missing and single-region objects → `[]` |
| contract structure | `seen_any` required and explicit; `joint` identities; no duplicates; no experiment import; no production import through `joint`; fresh bare `fov3d.scene` footprint; fresh `fov3d.scene.corridors` loads `cv2` but not `partition` |

**Mutation harness.** Each mutant is a text substitution on `corridors.py`, and the
harness asserts the exact number of matches. The mutant is executed into `sys.modules`
before `joint` is imported, so `joint` re-exports it. The harness is throw-away and not
committed. It covered 45 behavioral mutants over all ten required classes:

| class | mutants | result |
|---|---|---|
| erosion kernel / border | cross kernel, 5×5 kernel, `borderValue=1`, `BORDER_REPLICATE`, boundary = whole mask | all caught |
| line rounding | round-half-up (y), floor (x), `n + 2`, int64, one-point returns empty | all caught |
| x/y reversal | `(xs, ys)` stacking; gap angle with x/y swapped | all caught |
| endpoint reversal | reported endpoints reversed; line drawn reversed | all caught |
| closest-pair selection | last argmin on a tie, argmax, **L1 norm**, L∞ norm | all caught |
| region-code lookup | wrong attribute key, codes swapped, `ValueError` instead of `KeyError`, missing empty-boundary guard | all caught |
| owner composition | wrong base id, other includes target, distinct instead of sum, string-sorted keys, owners over the full line, interior including an endpoint | all caught |
| seen composition | seen over the full line, inverted seen, unseen = total, zero-interior fraction 0.0, fractions swapped | all caught |
| pair order | outer loop reversed, sorted `region_ids`, pair arguments swapped, **needs 3 regions** | all caught |
| semantics / serialization | semantics string, `object_id` not a string, result key order, gap in radians | all caught |

The first version of the checker (33 checks) let two non-equivalent mutants survive,
`closest_l1_norm` and `pairs_need_three_regions`. A random-fixture probe confirmed both
change behavior, in 8/600 and 172/600 cases. The last two added checks close them. The
final checker catches **41/41** non-equivalent mutants.

Four mutants are equivalent. Each shows **0/600** differing cases on random rasters,
masks, lines and objects; the probe does detect controls (last argmin 395/600, sorted
`region_ids` 282/600):

| equivalent mutant | reason |
|---|---|
| no adjacent-duplicate suppression in `_line_cells` | the major axis advances exactly one cell per sample, so duplicates never occur for integer endpoints |
| region lookup takes the last match | `state_region_code` values are unique per state |
| no clip before `arccos` | unit vectors kept \|dot\| ≤ 1 in every case |
| `corridor_yx` without `.astype(int)` | int32 `.tolist()` already yields Python ints |

**Static/package mutants: 8/8 caught.** They were applied to working-tree copies:

| mutant | caught by |
|---|---|
| duplicate `gap_corridor` defined in `joint.py` | identities and no-duplicates checks |
| `joint` missing the `_line_cells` alias | checker exits nonzero (`AttributeError`) |
| lazy `fov3d.experiments` import in `corridors.py` | experiment-dependency check |
| `corridors.py` couples to `update_controller_seen_any` | experiment-dependency check |
| `fov3d/scene/__init__.py` eagerly imports `corridors` | bare-footprint check |
| `corridors.py` imports `partition` | corridors-footprint check |
| `relations.py` takes `gap_corridor` through `joint` | no-production-import check |
| `seen_any` given a default (and following parameters too) | explicit/required-argument check |

## Gate A — interactive

Measured at `39e6a04`, then the whole gate again at `71d25c5`, with identical results:

```text
compile: 3 changed Python files OK
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
```

The golden comparison took 9.97 s at `39e6a04` and 10.00 s at `71d25c5`.

## Replay gates B–F

All commands were run from the repository root, in order, each to a fresh directory:

```text
B .venv/bin/python tools/partition_graph3_lift.py previews/partition-graph-2-source-full previews/conceptual-core-6-phase3-full
C .venv/bin/python tools/partition_graph4_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/conceptual-core-6-phase4-full
D .venv/bin/python tools/partition_graph5_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/partition-graph-4-full previews/conceptual-core-6-phase5-full
E .venv/bin/python tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals previews/conceptual-core-6-phase8b-proposals
F .venv/bin/python tools/partition_graph8b_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8b-proposals previews/partition-graph-8-evaluation previews/conceptual-core-6-phase8b-evaluation
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
| B Phase-3 joint lift | 23.04 s | `partition-graph-4-lift` | 419 | — | 419 | byte-identical | `7eed664047384a43f50f51940cc4ad61d602513bb1095e076adc6c083ac3cbe3` |
| C Phase-4 analyzer | 6.93 s | `partition-graph-4-full` | 425 | `demo/` 107, `demo-package-original/` 107 | 211 | byte-identical | `eca1b6ad798117de8d2de321e0ebfe6f92cb3e73a8f0b80e78e494f8a3f3cd8c` |
| D Phase-5 analyzer | 8.38 s | `partition-graph-5-full` | 225 | `demo/` 7, `demo-package-original/` 7 | 211 | byte-identical | `77f5ae3d408900c8b2428553f22a97fae60aeddef34ea1f500a78e39d07c68eb` |
| E Phase-8b proposer | 62.71 s | `partition-graph-8b-proposals` | 503 | — | 503 | byte-identical | `51a93fc464fc8ce00fc7f519ccadc25f539095be06de074788844b12ad6e7b7d` |
| F Phase-8b evaluator | 16.86 s | `partition-graph-8b-evaluation` | 19 | `demo/` 8, `demo-package-original/` 8 | 3 | byte-identical | `243133b66237523147e1a869ee5b1bf97ee28ec9d817c5c059921e9b254c5715` |

All five scope manifests equal the Core-2 through Core-5 values.

**Comparison method** (as in Cores 3–5). Each comparison is two-sided:
1. The fresh set must **equal** the accepted set minus the declared exclusions.
2. No fresh file may lie under an excluded path.
3. Every pair must be byte-identical (`filecmp`, `shallow=False`).
4. The scope manifests must be equal. Each is computed as
   `cd DIR && LC_ALL=C find . -type f [-not -path './<excl>/*' ...] -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum`.

In every gate, `only_fresh`, `only_accepted`, `fresh_under_excluded` and `byte_diff` were
all 0.

**Accepted trees unchanged.** Per-file sha256 manifests of the 13 accepted trees were taken
before Gate B and after Gate F, and they are identical. They also equal the Core-5
manifests.

## Changed-path → execution-gate coverage

| changed path | kind | exercised by | execution evidence |
|---|---|---|---|
| `fov3d/scene/corridors.py` module (imports `cv2`, `head_chart`, `.model`) | new module | A (Core-6; checkers 3, 4, 5 and 8 through `joint`), B, C (load), E, F (load) | import probe; every run byte-identical |
| `_component_boundary`, `_line_cells`, `gap_corridor`, `corridors_for_object` | moved | A (Core-6: 35 checks; checkers 3 and 4 call `corridors_for_object`), **B** | `lift_joint_run` → `corridors_for_object` at `joint.py:352` (per state, with `seen`) and `joint.py:405` (final scene, with `evidence[iid]`) → `gap_corridor` → `_component_boundary` / `_line_cells`. The fresh Phase-3 tree holds **570 corridor records in 61 files**, exactly the Phase-4 report's "570 records (302 per-state, 86 causal, 182 scene-final)". `corridor_aggregate` = `{causal_final_pairs 86, scene_final_pairs 182, scene_final_pairs_crossing_other_object 176, scene_final_pairs_with_unseen_cells 0}`. All byte-identical |
| `joint.py` imports (+ `fov3d.scene.corridors`; − `cv2`, `head_unit_from_angles`) | changed module dependency | A (checkers 3, 4, 5 and 8; Core-6 identity), B, C (`relations` imports `joint`), E, F | as above |
| `lift_joint_run`'s `corridors_for_object` binding | changed dependency binding | B | `__globals__` identity; output byte-identical |
| `tools/dev/check_conceptual_core6.py` | new checker | A; mutation harnesses | 35/35; 41/41 behavioral and 8/8 static mutants caught |

## Confirmations

- **`seen_any` is explicit.** It is a required parameter without a default; there is no
  experiment import in `corridors.py`; and the replay evidence is passed in by
  `lift_joint_run`.
- **Unchanged:**
  - `relations.py` (Phase-4 relation classification, `FineEvidence`,
    `add_patch_observation`);
  - the lineage (`_lineage`, `_target_component_raster`) and the controller `seen_any`
    replay (`update_controller_seen_any`, `_rectified_core_directions_h`,
    `_append_raw_footprints`), which are source-text identical;
  - the Phase-2 boundaries (`lift.py`), partition construction, boundary extraction, and
    benchmark and evaluator modules.
- **Package footprint.** `fov3d/scene/__init__.py` is unchanged, and the bare import
  footprint is unchanged.
- **No scientific/runtime behavior changed.** The evidence:
  - text-identical functions with identical global bindings;
  - byte-identical Phase 3, 4, 5 and 8b producer output, and Phase-8b evaluator output;
  - identical corridor records (570) and aggregates;
  - golden `MISMATCHES 0`, and baseline 31/31.

## Repairs and deviations

1. **Proposal completion by Code** (Luiz's instruction). This covers the `joint.py`
   wiring, the contract, the checker, the handoff update and the map update. These are
   Code-authored rather than Chat proposals and are marked as such in the provenance.
   `corridors.py` itself was not modified.
2. **Checker strengthened before commit.** It gained two checks (Euclidean nearest pair;
   two-region object) after mutation testing. The checker was committed only in its
   final 35-check form, and existing checks were not weakened.
3. **Handoff.** `docs/chat-handoff.md` was updated on the branch as instructed. It
   records accepted Core 5 and active Core 6. No scientific claim was altered; the Core-5
   evidence is quoted from its committed report.
4. **Additional evidence beyond the contract.** It comprises the source-text and
   global-binding identity checks, the import probe and AST scan, the equivalence probe,
   and the accepted-tree manifests before and after. It used throw-away harnesses in the
   session scratchpad, which are not committed.

No other deviation. The gate commands, inputs, output directories and references are
exactly the contract's. No conditional gate was triggered.

## Unresolved

1. **`docs/core6-note.md`** is a one-line placeholder (`# Core 6`) left by Chat's
   interrupted writes (`118161a`). Deleting it was not delegated, so it is left in place.
   Suggest removing it at acceptance.
2. **Consumerless aliases now number five:** `joint._interface_edges`,
   `joint._trace_edge_components`, `joint.gap_corridor`, `joint._line_cells` and
   `joint._component_boundary`. Together with the Core-2 aliases, a single decision on
   the alias policy would remove this recurring item.
3. **Unreachable guard.** `gap_corridor`'s empty-boundary `RuntimeError` cannot fire with
   the real `_component_boundary`, because erosion with a zero border always leaves a
   non-empty boundary for a non-empty mask. It is tested only with an injected empty
   boundary, like the Core-5 lost-edge guard.
4. **Chat review pending** of the Code-authored contract, checker and wiring (repair 1).
5. The Core-5, Core-4, Core-3 and Core-2 items are carried over unchanged.

## Recommendation (Conceptual Core 7 only)

The bounded candidate is **target-component lineage**: `_lineage(prev_rc, curr_rc)` and
`_target_component_raster(graph, region_code, target_id)`, moved to a scene-level module
such as `fov3d.scene.lineage`.

Measured audit:
- they use only NumPy and `ScenePartitionGraph`;
- their consumers are `lift_joint_run` (`joint.py:357-358`) and `check_partition_graph4.py`
  (`_lineage`).

**Precondition to decide first:** `tools/dev/apply_partition_graph4_lineage_fix.py`, the
historical one-shot Phase-4 lineage patch tool, locates `_lineage` by matching
`joint.py` source text. Moving `_lineage` invalidates its preconditions. Luiz and Chat
should decide whether that tool is retired or archived before Core 7.

Leave the following untouched:
- the controller `seen_any` replay, which depends on calibration/stereo ops and stays
  experiment-side;
- `build_joint_graph` and `lift_joint_run`;
- relation classification (`relations.py`);
- benchmark policy.

Gates: the Phase-3 lift (lineage is serialized in the Phase-3 summary) against
`partition-graph-4-lift`; the Phase-4 and Phase-5 analyzers; and the Phase-8b proposer and
evaluator as parity. Phases 2, 6, 7 and 8 run only if the import probe shows the diff
reaches them.

## Success marker

    CONCEPTUAL_CORE6_GAP_CORRIDORS_PRESERVE_BEHAVIOR
