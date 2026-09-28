# Migration Conceptual Core 2 — report (2026-09-26)

Executed by Claude Code on the Ubuntu workstation against the committed contract
`docs/migration-conceptual-core-2.md`. Every number below is **MEASURED** from the
command shown, unless it is marked otherwise.

## Provenance

| item | value |
|---|---|
| branch | `migration/conceptual-core-2` |
| parent accepted milestone | `main` @ `485f696ad8f19bed9f63bda70e3a294a3b2dfc7b` (merge base verified) |
| proposal head | `ee3ae248d13764b0e00862dfc6e58562b9b64577`: 13 Chat-authored commits `4959991`…`ee3ae24` |
| Code repair commits | `602b3ee` shadowing and name repair · `94d89fd` checker correction (Luiz-approved) · `5fea5db` map rows |
| gates measured at | `94d89fd` (implementation and checker final; later commits are docs only) |
| final head | the commit that adds this report |

## Luiz decisions recorded during execution

1. **Checker oracle correction** (explicit, under `CLAUDE.md`). Replace the ambiguous
   0.10° "half-cell" test with binary-exact halves on a 0.25° grid (0.5, 1.5, 2.5 → 0, 2, 2
   under `np.rint`). Add a separate regression pinning the accepted-grid inputs
   −24.95/−24.85 to main's `[1, 1]`. Keep the shadowing guard and repair. "It is not
   permission to relax any behavioral-equivalence gate."
2. **Gate C reference-lineage correction** (explicit, under `CLAUDE.md`). Use
   `previews/partition-graph-4-lift` as the authoritative reference for current Phase-3
   producer behavior, with exact 419/419 parity. Also record the comparison against
   `partition-graph-3-full`. Gate C passes if Core 2 equals pre-Core-2 main, Core 2 equals
   4-lift byte for byte, and the sole mismatch against 3-full is the known historical
   lineage correction. "It does not authorize any change to scientific behavior,
   acceptance thresholds, or reference outputs."

## Files changed (main...final head)

| file | change |
|---|---|
| `fov3d/geometry/head_chart.py` | new (proposal) |
| `fov3d/reconstruction/association.py` | new (proposal) |
| `fov3d/experiments/classroom_partition/{lift,joint,relations,incidental,benchmark,prefix_benchmark,integration,challenge_suite}.py` | use the conceptual modules (proposal); three modules repaired by Code (`602b3ee`) |
| `tools/dev/check_conceptual_core2.py` | new (proposal); corrected and strengthened by Code (`94d89fd`) |
| `docs/migration-conceptual-core-2.md` | contract (proposal) |
| `docs/conceptual-core-map.md` | status and order (proposal); stale rows corrected by Code (`5fea5db`) |
| `docs/migration-conceptual-core-2-report.md` | this report |

The following are untouched: `fov3d/scene/sphere.py`, existing phase checkers, sealed
runtime files (`verify_baseline.sh` 31/31), golden signatures, scene assets, and every
accepted preview tree (14 snapshots compared before and after).

## Final public chart API (`fov3d.geometry.head_chart`)

Head frame: +X right, +Y up, −Z forward. Angles are in degrees. This convention is
deliberately distinct from `fov3d.scene.sphere` lon/lat.

    head_angles_from_unit(directions_h) -> (yaw, pitch)
        float64; rows normalized by max(norm, 1e-15)
        yaw = atan2(x, -z), pitch = atan2(y, hypot(x, z))
    head_unit_from_angles(yaw_deg, pitch_deg) -> (N, 3)
        broadcast inputs; (sin y cos p, sin p, -cos y cos p)
    chart_grid(domain, grid_deg) -> (y0, y1, p0, p1, h, w)
        inclusive size: round((max - min) / grid_deg) + 1
    chart_cells(yaw, pitch, y0, p0, grid_deg, h, w) -> (row, col, ok)
        np.rint, int64; ok excludes non-finite and out-of-chart samples

All four functions have the same expressions as the historical `lift.py` helpers; only
local variable names changed.

## Canonical association API (`fov3d.reconstruction.association`)

    SURFACE_ASSOCIATION_RADIUS_M = 0.012

Compatibility aliases, all assignments rather than numbers:
`lift.FUSION_RADIUS_M`, `benchmark.FUSION_RADIUS_M`, `lift._grid/_cells/_head_angles_from_unit/_head_unit_from_angles`,
`benchmark._grid/_cells`.

## Pre-execution review: two proposal defects (diagnosed, repaired)

**1. Name shadowing broke three evaluators (MEASURED on `ee3ae24`).** The textual rename
`_cells` → `chart_cells` collided with existing local `chart_cells` cell counts. Python
then treats the name as local for the whole function:

| function | failure on `ee3ae24` |
|---|---|
| `prefix_benchmark.evaluate_phase7` (local at 516, calls at 620/624) | `TypeError: 'int' object is not callable` |
| `integration.evaluate_phase8` (local at 523, call at 650) | `TypeError: 'int' object is not callable` |
| `challenge_suite._region_metrics` → `evaluate_phase8b` (call at 494 before local at 502) | `UnboundLocalError` |

All three evaluators exited 1 within about 1 s on the accepted inputs. No contract gate
exercises these functions.

The same substring rename also changed four unrelated private helper names:

| original (main) | on `ee3ae24` |
|---|---|
| `joint._line_cells` | `_linechart_cells` |
| `incidental._relation_true_gap_cells` | `_relation_true_gapchart_cells` |
| `prefix_benchmark._candidate_cells` | `_candidatechart_cells` |
| `prefix_benchmark._largest_kind_cells` | `_largest_kindchart_cells` |

Each rename was consistent within its own file and harmless to output. Serialized keys
such as `"candidate_cells"` were intact.

*Repair (`602b3ee`, delegated mechanical scope):* in `prefix_benchmark.py`,
`integration.py` and `challenge_suite.py`, import `head_chart` and call
`head_chart.chart_cells(...)` qualified at all 5 call sites. The local counts, keyword
arguments and serialized keys are unchanged. The four helper names are restored and now
identical to main. A whole-package AST scan finds 0 remaining shadowed calls.

**2. Checker oracle defect (Luiz decision 1).** `half-cell rint` failed on unchanged code.
In float64 (−24.95+25)/0.10 = 0.5000000000000071 and (−24.85+25)/0.10 = 1.4999999999999858.
Historical `main` `_cells` and `head_chart.chart_cells` both return `[1, 1]`, not the
expected `[0, 2]`.

*Repair (`94d89fd`):*
- an exact-half test on the 0.25° grid (0, 2, 2);
- the accepted-grid regression pinned to `[1, 1]`;
- a static guard, `no shadowed imported chart/association calls`, with a negative invariant.

**Checker fail-capability (MEASURED; throw-away harness, not committed).** The guard
flags exactly the three broken functions in the `ee3ae24` blobs. In-memory mutants are
all caught (exit 1):

| mutant | failing check |
|---|---|
| forward = +Z | `anchor yaw`, `negative frame-sign invariant` |
| `floor` instead of `rint` | exact-half and near-half checks |
| round-half-up | exact-half check |
| radius 0.010 | `association radius` |

The rounding mutants also trip `lift compatibility aliases`. That is a harness artifact,
because patching the checker's reference breaks the identity test.

## Gate A — interactive

```text
compile: 11 changed Python files OK
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

## Replay gates B–G (producer scope)

All commands were run from the repository root with the contract's relative paths. The
producers resolve inputs to the absolute paths recorded in the accepted JSON. Comparisons
are two-sided: the fresh file set must **equal** the accepted set minus the listed
exclusions, every file must be `cmp`-identical, and no fresh file may sit under an
excluded path.

```text
B .venv/bin/python tools/partition_graph2_lift.py previews/partition-graph-2-source-full previews/conceptual-core-2-phase2-full
C .venv/bin/python tools/partition_graph3_lift.py previews/partition-graph-2-source-full previews/conceptual-core-2-phase3-full
D .venv/bin/python tools/partition_graph5_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/partition-graph-4-full previews/conceptual-core-2-phase5-full
E .venv/bin/python tools/partition_graph7_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-6-proposals previews/conceptual-core-2-phase7-proposals
F .venv/bin/python tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals previews/conceptual-core-2-phase8b-proposals
G .venv/bin/python tools/partition_graph8_integrate.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-7-proposals previews/conceptual-core-2-phase8-proposals
```

```text
[partition-graph2-lift] COMPLETE {"final_multi_component_objects": 9, "final_pairs_with_shared_base_neighbor": 30, "graphs_written": 104, "objects": 25, "topology_merges": 2, "topology_splits": 7}
[partition-graph3-lift] COMPLETE {"causal_final_pairs": 86, "evidence_checks": 51, "evidence_mismatches": 0, "scene_final_pairs": 182, "states": 104}
[partition-graph5-analyze] COMPLETE {"challenge_relations": 108, "challenge_states": 41, "challenge_targets": 4, "states": 104, "target_gap_violations": 0}
[partition-graph7-propose] COMPLETE {"global_candidates": 17202, "local_candidates": 8557, "phase6_final_local_parity": 25, "states": 104, "targets": 25, "truth_used": false}
[partition-graph8b-propose] COMPLETE {"eligible_candidates": 6489, "full_phase8_parity": 25, "raw_candidates": 18469, "scenarios": 5, "states": 125, "targets": 25, "truth_used": false}
[partition-graph8-integrate] COMPLETE {"candidate_regions": 16825, "phase7_global_parity": 104, "states": 104, "target_evidence_unmapped_cells": 0, "targets": 25, "truth_used": false}
```

Every required headline value matches the contract.

| gate | wall | reference | accepted total | excluded | producer files (fresh = accepted scope) | result | scope manifest sha256 |
|---|---|---|---|---|---|---|---|
| B Phase 2 | 6.14 s | `partition-graph-2-full` | 524 | `demo/` 107 | 417 | byte-identical | `8d3c87923bcba8cec41ca8b9033123e3b06c78c1ae36a6e97f25e1a29eb529e9` |
| C Phase 3 | 23.01 s | `partition-graph-4-lift` (decision 2) | 419 | — | 419 | byte-identical | `7eed664047384a43f50f51940cc4ad61d602513bb1095e076adc6c083ac3cbe3` |
| D Phase 5 | 8.31 s | `partition-graph-5-full` | 225 | `demo/` 7, `demo-package-original/` 7 | 211 | byte-identical | `77f5ae3d408900c8b2428553f22a97fae60aeddef34ea1f500a78e39d07c68eb` |
| E Phase 7 | 47.83 s | `partition-graph-7-proposals` | 835 | — | 835 | byte-identical | `3dde52e4cd34228f91c240db3682dc489d9f1adb74a5e85a7021b58bff1673de` |
| F Phase 8b | 62.89 s | `partition-graph-8b-proposals` | 503 | — | 503 | byte-identical | `51a93fc464fc8ce00fc7f519ccadc25f539095be06de074788844b12ad6e7b7d` |
| G Phase 8 | 667.27 s | `partition-graph-8-proposals` | 468 | — | 468 | byte-identical | `69ccbfb748f250e19baebb75789e57c66f4c26443286e43a9a85ca77f474a209` |

The Phase-8b and Phase-8 manifests equal the Conceptual Core 1 values.

**Gate C details (decision 2).** Against the contract's `partition-graph-3-full`, the
result is 418/419 byte-identical (`demo/` 107 and `demo-package-original/` 107 excluded).
The sole differing file is `summary.json`. A structural JSON diff finds 242 differing
leaves and no key or length differences. Every differing leaf is `births`, `deaths`,
`merges` or `persistent_links`, under `global_states[*].lineage` or
`lineage_totals_excluding_initial`. The totals are stale Phase-3 `{births 191, deaths 185,
merges 0}` against corrected `{births 10, deaths 1, merges 3}`. This is the Phase-4
`_lineage` repair (`docs/partition-graph-4.md` §1; the Phase-4 report says the fixed lift
is "byte-identical to the Phase-3 lift, and the lift summary differs only in the
lineage"). **Pre-Core-2 `main` @ `485f696`** was exported with `git archive` (no
`head_chart` module) and its Phase-3 lift was run (25.17 s). It gives 419 files
byte-identical to both the Core-2 output and `partition-graph-4-lift`. All three
conditions of decision 2 hold, so **Gate C passes**.

**Gate G was required.** The contract's second trigger applies: `propose_phase8` (its
`chart_grid` call and a harmless local `chart_cells` shadow) and `cross_target_novelty`
(the radius) are changed Phase-8-only paths that no gate B–F exercises. The shadowing
defect also sat in Phase-8 code.

## Additional measured coverage (beyond the contract's gates)

The contract gates leave some changed functions unexercised. The shadowing defect lived in
exactly such functions, so every changed function was mapped to a run that exercises it,
and the gaps were replayed. Each run used accepted inputs, went to a fresh directory and
was compared at producer scope.

| run | wall | accepted reference | producer files | excluded | result | manifest sha256 |
|---|---|---|---|---|---|---|
| Phase-7 evaluator | 19.29 s | `partition-graph-7-evaluation` | 107 | `demo/` 107, `demo-package-original/` 107 | byte-identical | `05d35ef37a6294c0b0da08a1f943d7c9c8daef93c22819adb9beb8bdb3da0515` |
| Phase-8 evaluator | 124.14 s | `partition-graph-8-evaluation` | 107 | 107 + 107 | byte-identical | `01c8d253f5ea8698e8df290b7090f299d2fb462c6c40a0fdb04bdc7611525f7d` |
| Phase-8b evaluator | 16.32 s | `partition-graph-8b-evaluation` | 3 | 8 + 8 | byte-identical | `243133b66237523147e1a869ee5b1bf97ee28ec9d817c5c059921e9b254c5715` |
| Phase-4 analyzer | 6.92 s | `partition-graph-4-full` | 211 | 107 + 107 | byte-identical | `eca1b6ad798117de8d2de321e0ebfe6f92cb3e73a8f0b80e78e494f8a3f3cd8c` |
| Phase-6 evaluator | 1.49 s | `partition-graph-6-evaluation` | 3 | 28 + 28 | byte-identical | `b584139a0186e014627452c74c811ed7b5281f3351255ae2596340ef6ae96fff` |

The three repaired evaluators reproduce their accepted COMPLETE summaries. For example,
Phase 8: `historical_state_misses 101824`, `integration_gain 61557`,
`residual_candidate_recall 0.955472222912062`. Phase 8b: `full_eligible_recall
0.9335820895522388`. The Phase-8 and 8b manifests equal the Core-1 closure values.

Changed-function coverage:

| module | changed functions | measured by |
|---|---|---|
| `lift` | `_build_graph`, `_fill_polygon`, `_support_from_map`, `_visibility_raster` | B |
| `joint` | `extract_boundaries`, `gap_corridor`, `lift_joint_run`, `support_depth_from_map`, `update_controller_seen_any` | C (and D–G) |
| `relations` | `_mark`, `analyze_phase4`, `ownership_margin_descriptor` | Phase-4 analyzer |
| `incidental` | `add_head_patch`, `analyze_phase5` | D (and E–G) |
| `benchmark` | `_centroid_angles`, `evaluate_phase6` | E/F (via `build_epistemic_partition`), Phase-6 evaluator |
| `prefix_benchmark` | `propose_phase7`, `evaluate_phase7`, `_angles_to_codes` | E, Phase-7 evaluator |
| `integration` | `propose_phase8`, `cross_target_novelty`, `evaluate_phase8` | G, Phase-8 evaluator |
| `challenge_suite` | `propose_phase8b`, `evaluate_phase8b`, `_region_metrics` | F, Phase-8b evaluator |

**Exclusion evidence.** Each `demo/` directory is the default output of that phase's demo
tool:
- `tools/partition_graph{2,3,4,5,6,7,8}_demo.py` default to `<dir>/demo`;
- `partition_graph8b_demo.py` takes an explicit `out_dir`.

Each `demo-package-original/` is documented in its phase report as the retained package
demo (Phases 3, 4, 5, 6, 7, 8, 8b). No producer or evaluator writes either directory, and
no fresh tree contains one.

All 14 accepted trees read by the gates are unchanged, by sha256 manifests before and
after: 2-source-full, 2-full, 3-full, 4-lift, 4-full, 5-full, 6-proposals, 6-evaluation,
7-proposals, 7-evaluation, 8-proposals, 8-evaluation, 8b-proposals, 8b-evaluation.

## Dependency audit (repository-wide, tracked files)

Import-graph diff (AST) between main and final head, `classroom_partition` package:
- **0** new edges into the experiment package;
- **23** removed cross-phase edges: chart helpers and `FUSION_RADIUS_M` from `lift` and
  `benchmark`;
- all added edges target `fov3d.geometry.head_chart` or `fov3d.reconstruction.association`.

Required results:

- no production module imports a private chart helper from `lift.py`;
- no Phase 7/8/8b module obtains chart helpers through `benchmark.py`;
- inside `fov3d/`, `association.py` holds the only `0.012`.

Every remaining occurrence:

| occurrence | classification |
|---|---|
| `lift.py:35-39` aliases `FUSION_RADIUS_M`, `_cells`, `_grid`, `_head_angles_from_unit`, `_head_unit_from_angles` | compatibility aliases. **Decision item:** no in-repo consumer except the Core-2 alias check |
| `benchmark.py:42-44` aliases `FUSION_RADIUS_M`, `_cells`, `_grid` | `_cells`/`_grid` are required by `tools/partition_graph6_demo.py`. `FUSION_RADIUS_M` has no consumer (**decision item**) |
| `tools/partition_graph6_demo.py:12,78,105` | older demo using benchmark compatibility aliases (intentional compatibility) |
| `tools/partition_graph6_demo.py:99` `_covered(..., 0.012)` | **Decision item:** second numeric literal for the 12-mm coverage concept, in a demo outside the contract's allowed paths |
| `tools/classroom_oracle1_epistemic.py:63…253` `_cells(ev, …)` | unrelated homonym: the sealed runtime's own evidence-grid helper with a different signature. Protected |
| `tools/classroom_oracle1_public.py:26,27,85`, `tools/fsg6f_public.py:37,38`, `tools/classroom_oracle1_run.py:475,477`, `tools/dev/check_classroom_oracle1.py:96-99` | sealed runtime frozen `FUSION` parameters (`association_radius_m`, `hash_cell_m`) and their assertions. Protected baseline files |
| `tests/golden/*.json` `frontier_state_radius_m: 0.012` | recorded golden data. Protected |
| `tools/dev/check_conceptual_core2.py` | intentional constant and alias assertions |
| `docs/*.md` | contract, report and map text |

## Scientific / runtime behavior

No change to the head-frame convention, angle formulas, chart resolution, `np.rint`
rounding, 12-mm radius, support, partition, topology, epistemic, benchmark or evaluator
semantics, accepted trees, golden signatures, or controller, matcher, fusion, renderer,
gaze, scene or termination behavior. The evidence:

- byte-identical producer output for Phases 2, 3 (per decision 2), 4, 5, 7, 8 and 8b;
- byte-identical evaluator output for Phases 6, 7, 8 and 8b;
- golden `MISMATCHES 0`;
- baseline 31/31.

## Unresolved

1. **Alias decision.** The `lift.py` aliases and `benchmark.FUSION_RADIUS_M` have no
   in-repo consumer. The contract allows aliases "only if existing public/checker behavior
   requires them". They were kept, because they are harmless and asserted identical, but
   keeping or removing them is Luiz/Chat's call.
2. `tools/partition_graph6_demo.py:99` hard-codes `0.012` for 12-mm coverage. The fix is
   outside this contract's allowed paths.
3. The sealed runtime keeps its own frozen `FUSION.association_radius_m = 0.012`.
   Architectural question: should `association.py` document itself as the conceptual twin
   of that protected parameter?
4. **Reference registry.** `partition-graph-3-full` is stale for current code since
   Phase 4. Future contracts should name `partition-graph-4-lift` for the joint-lift
   producer. A small accepted-reference registry would prevent this.
5. **Methodology.** The contract's gates did not cover the evaluators, Phase 4 or Phase 6,
   and the only real defect was in such a path. Future structural contracts could require
   a changed-function → gate coverage table and evaluator replays. The static shadowing
   guard now covers this defect class.

## Recommendation (Conceptual Core 3 only)

Map item 2, **observation / epistemic state**: extract `HeadEvidence` + `add_head_patch`
(consumed by Phases 5, 7, 8 and 8b) behind a conceptual module on top of
`fov3d.geometry.head_chart`. Leave the Phase-4 `FineEvidence`, partition, topology and
benchmark code untouched. Gates:
- producers 4, 5, 7, 8b, plus Phase 8 if touched;
- the Phase-7/8/8b evaluators;
- a changed-function coverage table, with references taken from the accepted-reference
  lineage (4-lift, not 3-full).

## Success marker

    CONCEPTUAL_CORE2_HEAD_CHART_PRESERVES_BEHAVIOR
