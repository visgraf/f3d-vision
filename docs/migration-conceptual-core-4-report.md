# Migration Conceptual Core 4 — report (2026-09-27)

Executed by Claude Code on the Ubuntu workstation against the committed contract
`docs/migration-conceptual-core-4.md`. Every number below is **MEASURED** from the
command shown, unless it is marked otherwise.

## Provenance

| item | value |
|---|---|
| branch | `migration/conceptual-core-4` |
| parent accepted milestone | `main` @ `989127cafa784bf9e95cf9b3880fb6085ea283e6` (merge base verified; `origin/main` is the same commit) |
| scientific parent | Conceptual Core 3 @ `502439f` |
| proposal head | `03ff33810c83b8efda19f963acb31e708448ff64`, verified as the pulled head: 14 Chat-authored commits `4639503`…`03ff338` |
| Code commits | `44269cb` Core-4 checker strengthened · `e49f58b` stale map rows corrected · the commit that adds this report |
| gates measured at | Gate A at `03ff338` (proposal checker, 19 checks), then the whole of Gate A again at `e49f58b` (final checker, 25 checks); Gates B–H and supplementary replays at `44269cb` |
| final head | the commit that adds this report |

`fov3d/` is byte-identical at `03ff338`, `44269cb` and `e49f58b`. Code changed only the
dev checker and the map, so every gate ran against the proposed production code.

## Files changed (main...final head)

| file | change |
|---|---|
| `fov3d/scene/partition.py` | new (proposal): `SupportLayer`, `_disk`, `support_depth_from_map`, `joint_owner`, `_component_attrs`, `label_joint_regions` |
| `fov3d/scene/__init__.py` | exports the four public names (proposal) |
| `fov3d/experiments/classroom_partition/joint.py` | six definitions removed; imports the four public names from `fov3d.scene`; `SURFACE_ASSOCIATION_RADIUS_M` import dropped (proposal) |
| `fov3d/experiments/classroom_partition/{relations,incidental,integration,challenge_suite}.py` | `support_depth_from_map` imported from `fov3d.scene` instead of `joint` (proposal) |
| `tools/dev/check_conceptual_core4.py` | new (proposal); strengthened by Code (`44269cb`) |
| `docs/migration-conceptual-core-4.md` | contract (proposal) |
| `docs/conceptual-core-map.md` | Core-4 status and rows (proposal); four stale rows corrected by Code (`e49f58b`) |
| `docs/migration-conceptual-core-4-report.md` | this report |

The following are untouched (`git diff 989127c..HEAD` is empty for each):
- `fov3d/scene/model.py` and `sphere.py` (`ObservationFootprint`, `ObservationOverlay`,
  `BoundaryChain`);
- `fov3d/epistemic`, `fov3d/geometry` and `fov3d/reconstruction`;
- every existing phase checker, every producer, evaluator and demo under `tools/`, and
  `scripts/`;
- `tests/`, including the golden signatures;
- `CLAUDE.md` and sealed runtime files (`verify_baseline.sh` 31/31);
- the 13 accepted preview trees read by the gates, by sha256 manifests before and after.

`docs/chat-handoff.md` was not changed, because Core 4 is not yet accepted.

## Final scene-partition API and dependency direction

    fov3d.geometry.head_chart            chart_grid, chart_cells, head_angles_from_unit
    fov3d.reconstruction.association     SURFACE_ASSOCIATION_RADIUS_M
    fov3d.scene.model                    ObjectHypothesis, PartitionRegion, RegionKind
    cv2, numpy
            -> fov3d.scene.partition
                   SupportLayer                          frozen dataclass
                   support_depth_from_map(xyz_h, domain, grid_deg, *, instance_id, object_name) -> SupportLayer
                   joint_owner(layers) -> (owner int32, depth float32, overlap uint16)
                   label_joint_regions(owner, owner_depth, object_names)
                       -> (regions, objects, region_code int32, code_to_rid, rid_to_code)
            -> fov3d.scene (re-export of the four public names)
            -> fov3d.experiments.classroom_partition
                   joint (Phase-3 composition), relations (4), incidental (5),
                   integration (8), challenge_suite (8b)

Importing `fov3d.scene.partition` in a fresh interpreter loads the following modules,
whether `partition`, `fov3d.scene`, `head_chart` or `association` is imported first:
- `fov3d`, `fov3d.geometry`, `fov3d.geometry.head_chart`;
- `fov3d.reconstruction`, `fov3d.reconstruction.association`;
- `fov3d.scene`, `fov3d.scene.model`, `fov3d.scene.partition`, `fov3d.scene.sphere`.

There is no import cycle, and no experiment module is loaded. What stays in `joint.py` is
unchanged, as listed in contract §"What remains in joint.py". That includes boundary
extraction (`_interface_edges`, `_trace_edge_components`, `extract_boundaries`), which
only `build_joint_graph` uses.

## Compatibility and re-export decision

`joint.py` imports `SupportLayer`, `support_depth_from_map`, `joint_owner` and
`label_joint_regions` from `fov3d.scene` and defines none of them. The Core-4 checker
asserts `is` identity for all four, and the AST check below confirms there are no
duplicates. These imports are **required**:

- `build_joint_graph` calls `joint_owner` and `label_joint_regions` (`joint.py:250-251`),
  and `lift_joint_run` calls `support_depth_from_map` (`joint.py:647`);
- the unmodified phase checkers import them through `joint`:
  `check_partition_graph3.py:17` (`label_joint_regions`, `support_depth_from_map`),
  `check_partition_graph4.py:15` (`SupportLayer`),
  `check_partition_graph5.py:14` (`SupportLayer`) and
  `check_partition_graph8.py:16` (`support_depth_from_map`).

No production module other than `joint.py` obtains any of the four names through `joint`.

## Pre-execution mechanical review (Code)

1. **Literal extraction (AST).** After stripping docstrings, the AST dumps of
   `SupportLayer`, `_disk`, `support_depth_from_map`, `joint_owner` and
   `_component_attrs` equal `main`'s `joint.py`. `label_joint_regions` is equal once its
   **return annotation is ignored**. The extraction dropped that annotation, which was
   `tuple[dict[str, PartitionRegion], dict[str, ObjectHypothesis], np.ndarray, dict[int, str], dict[str, int]]`.
   `partition.py` uses `from __future__ import annotations`, so this has no runtime
   effect. The other 18 top-level definitions of `joint.py` are AST-identical to main.
2. **Consumers changed only at imports.** Every function and class definition, and every
   non-import module statement, of `relations.py`, `incidental.py`, `integration.py` and
   `challenge_suite.py` is AST-identical to main.
3. **No unbound names.** A `symtable` scan finds 0 references to names that are neither
   bound at module level nor builtins. It covered all 8 changed Python files; the missing
   `_disk` or radius constant would be exactly this Core-2 defect class. A planted
   `_disk` reference is flagged, so the scan is fail-capable. `joint.py` has no residual
   reference to `_disk`, `_component_attrs` or `SURFACE_ASSOCIATION_RADIUS_M`.
4. **Randomized differential test** (throw-away harness, not committed). It compared
   `main`@`989127c` `joint.py` with `fov3d.scene.partition` over:
   - 300 cases, 753 support layers and 470,168 chart cells;
   - grids of 0.1°, 0.25°, 0.5° and 1.0°;
   - five quantized ranges, giving several radius classes and exact depth ties;
   - 5 % NaN points, and points on the chart border.

   The following were identical in every case:
   - support rasters, `depth_m`, `point_yx` and `surfel_count`;
   - `joint_owner`'s owner, depth and overlap;
   - every labelled region (id, kind, object, attributes) and every object hypothesis;
   - `region_code`, `code_to_rid` and `rid_to_code`.
5. **Blender safety.** No script run under `blender -b -P` imports `fov3d` at all. See
   unresolved item 1 for the new OpenCV dependency of `fov3d.scene`.

## Repair: Core-4 checker strengthened (`44269cb`)

**Harness.** Each mutant is a text substitution on `partition.py`, and the harness
asserts that it matches exactly once. The mutant is executed into `sys.modules` and
rebound into the `fov3d.scene` package before anything imports `joint`. As a result,
`joint` re-exports the mutant and the identity check cannot produce a false alarm.
Static mutants were applied to `git archive` copies of the tree. The harness is
throw-away and not committed.

**Equivalence.** A mutant is classed as equivalent only if a random-input probe finds 0
differing cases out of 300 against the original. The probe does detect non-equivalent
controls: `floor` differs in 297/300 cases and reversed object order in 211/300.

| mutant | proposal checker (19) | strengthened (25) |
|---|---|---|
| support: point-only disk | caught | caught |
| support: `floor` instead of `ceil` | **survived** | caught |
| support: radius 10 mm | **survived** | caught |
| support: radius doubled | caught | caught |
| support: farthest depth across disks | **survived** | caught |
| support: depth float64 | caught | caught |
| support: `surfel_count` counts in-chart points only | **survived** | caught |
| support: `point_yx` zero sentinel | caught | caught |
| support: `point_yx` misaligned to original indices | caught | caught |
| support: square disk | caught | caught |
| owner: equal-depth tie → larger id | caught | caught |
| owner: `<=` instead of `<` | caught | caught |
| owner: farther wins | caught | caught |
| owner: reversed iteration without tie clause | caught | caught |
| owner: overlap saturating (OR) | caught | caught |
| owner: overlap int32 | caught | caught |
| owner: owner int64 | **survived** | caught |
| owner: owner depth float64 | **survived** | caught |
| owner: broadcastable shape mismatch accepted | **survived** | caught |
| owner: empty input not `ValueError` | **survived** | caught |
| label: foreground 4-connectivity | caught | caught |
| label: BASE 8-connectivity | caught | caught |
| label: object id `c{:02d}` | caught | caught |
| label: BASE id format | **survived** | caught |
| label: codes start at 2 | caught | caught |
| label: objects in reverse id order | **survived** | caught |
| label: object `source` string | caught | caught |
| label: BASE `source` string | **survived** | caught |
| label: `identity_source` string | caught | caught |
| label: `object_name` lookup ignored | **survived** | caught |
| label: `instance_id` attribute dropped | **survived** | caught |
| label: `touches_domain_edge` always False | **survived** | caught |
| label: `touches_domain_edge` ignores last row | **survived** | caught |
| label: median → mean | **survived** | caught |
| label: min/max swapped | **survived** | caught |
| label: `cell_count` counts rows | **survived** | caught |
| label: object kind BASE | caught | caught |
| static: `relations` / `incidental` / `integration` / `challenge_suite` import via `joint` (4 mutants) | caught | caught |
| static: lazy `fov3d.experiments` import in `partition.py` | caught | caught |
| static: lazy `fov3d.experiments` import in `fov3d/scene/model.py` | **survived** | caught |
| static: duplicate `support_depth_from_map` in `joint.py` | caught | caught |
| static: compatibility alias missing from `joint.py` | caught | caught |

Summary:
- proposal checker: 19/37 non-equivalent behavioral mutants caught, and 7/8 static;
- strengthened checker: **37/37** behavioral and **8/8** static.

The six surviving mutants are **equivalent**; each shows 0/300 differing cases:

| equivalent mutant | reason |
|---|---|
| `joint_owner` without the tie clause | sorted ascending iteration already lets the earlier (smaller) id win an exact tie; the clause is unreachable |
| `joint_owner` in reverse order | the tie clause makes the result independent of order |
| no minimum-one-cell radius | `atan(0.012/r) > 0` for every finite range, so `ceil ≥ 1` already |
| `BORDER_REPLICATE` instead of `BORDER_CONSTANT +inf` | a replicated border pixel is the clamped in-image pixel, which lies in the same Euclidean disk |
| BASE attributes given `owner_depth` | `owner == 0` exactly where the depth is +inf, and non-finite depths are filtered |
| no unlabeled-cell guard | unreachable, because `joint_owner` never emits negative ids |

**Added checks.** The strengthened checker adds six checks. Existing checks are
unchanged. The expected values were derived by hand from the contract's semantics and
were not fitted to output. They pass unmodified on code proven identical to main.

1. `support radius classes, overlap minimum and surfel count` on a 1° grid:
   - a 0.3 m point: atan(0.04) = 2.29° → 3 cells, 29 cells;
   - an overlapping 1.0 m point: 1 cell, adding 3 cells, for 32 in total;
   - depth checked as the minimum across disks;
   - a finite point outside the chart, and a NaN point.
2. `owner dtypes and unowned depth`.
3. `broadcastable shape mismatch and empty input raise ValueError`. A (2,2) layer with a
   (1,2) layer is needed, because numpy already raises for (2,2) with (3,3).
4. `multi-object region ids, codes and order`: objects 3 and 5, only one of them named,
   and one BASE component.
5. `exact component attributes`: full attribute dicts, including an object that touches
   only the last row.
6. `fov3d.scene package has no experiment dependency`: all of `fov3d/scene/*.py`, per the
   acceptance wording.

This is the delegated "strengthen the Core-4 checker" scope. No acceptance gate was
touched.

## Gate A — interactive

Measured at `03ff338` (proposal checker 19/0), then the whole gate again at `e49f58b`:

```text
compile: 8 changed Python files OK
[conceptual-core4-check] SUMMARY checked=25 failed=0
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

The golden comparison took 9.79 s at `03ff338` and 10.00 s at `e49f58b`.

## Replay gates B–H

All commands were run from the repository root, in order, each to a fresh directory:

```text
B .venv/bin/python tools/partition_graph3_lift.py previews/partition-graph-2-source-full previews/conceptual-core-4-phase3-full
C .venv/bin/python tools/partition_graph4_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/conceptual-core-4-phase4-full
D .venv/bin/python tools/partition_graph5_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/partition-graph-4-full previews/conceptual-core-4-phase5-full
E .venv/bin/python tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals previews/conceptual-core-4-phase8b-proposals
F .venv/bin/python tools/partition_graph8b_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8b-proposals previews/partition-graph-8-evaluation previews/conceptual-core-4-phase8b-evaluation
G .venv/bin/python tools/partition_graph8_integrate.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-7-proposals previews/conceptual-core-4-phase8-proposals
H .venv/bin/python tools/partition_graph8_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8-proposals previews/partition-graph-7-evaluation previews/conceptual-core-4-phase8-evaluation
```

```text
B [partition-graph3-lift] COMPLETE {"causal_final_pairs": 86, "evidence_checks": 51, "evidence_mismatches": 0, "scene_final_pairs": 182, "states": 104}
C [partition-graph4-analyze] COMPLETE {"causal_own_support_gap": 44, "causal_ownership_cut": 42, "causal_relations": 86, "states": 104, "target_depth_checks": 51, "target_depth_mismatches": 0}
D [partition-graph5-analyze] COMPLETE {"challenge_relations": 108, "challenge_states": 41, "challenge_targets": 4, "states": 104, "target_gap_violations": 0}
E [partition-graph8b-propose] COMPLETE {"eligible_candidates": 6489, "full_phase8_parity": 25, "raw_candidates": 18469, "scenarios": 5, "states": 125, "targets": 25, "truth_used": false}
F [partition-graph8b-evaluate] COMPLETE {"full_eligible_recall": 0.9335820895522388, "full_integrated_covered": 27948, "full_integrated_residual": 1340, "scenarios": 5, "states": 125}
G [partition-graph8-integrate] COMPLETE {"candidate_regions": 16825, "phase7_global_parity": 104, "states": 104, "target_evidence_unmapped_cells": 0, "targets": 25, "truth_used": false}
H [partition-graph8-evaluate] COMPLETE {"cross_target_gain": 61538, "final_integrated_covered": 27948, "final_integrated_residual": 1340, "historical_state_misses": 101824, "integration_gain": 61557, "own_target_retention_gain": 19, "residual_candidate_recall": 0.955472222912062, "residual_state_misses": 40267, "states": 104}
```

Every required COMPLETE value in the contract matches (B, D, E, F, G, H). All seven lines
are string-identical to lines in earlier committed reports (Core 1, Core-1 closure,
Core 2 and Core 3).

| gate | wall | accepted reference | accepted total | excluded | producer/evaluator files (fresh = accepted scope) | result | scope manifest sha256 |
|---|---|---|---|---|---|---|---|
| B Phase-3 joint lift | 23.06 s | `partition-graph-4-lift` | 419 | — | 419 | byte-identical | `7eed664047384a43f50f51940cc4ad61d602513bb1095e076adc6c083ac3cbe3` |
| C Phase-4 analyzer | 6.83 s | `partition-graph-4-full` | 425 | `demo/` 107, `demo-package-original/` 107 | 211 | byte-identical | `eca1b6ad798117de8d2de321e0ebfe6f92cb3e73a8f0b80e78e494f8a3f3cd8c` |
| D Phase-5 analyzer | 8.38 s | `partition-graph-5-full` | 225 | `demo/` 7, `demo-package-original/` 7 | 211 | byte-identical | `77f5ae3d408900c8b2428553f22a97fae60aeddef34ea1f500a78e39d07c68eb` |
| E Phase-8b proposer | 61.96 s | `partition-graph-8b-proposals` | 503 | — | 503 | byte-identical | `51a93fc464fc8ce00fc7f519ccadc25f539095be06de074788844b12ad6e7b7d` |
| F Phase-8b evaluator | 16.68 s | `partition-graph-8b-evaluation` | 19 | `demo/` 8, `demo-package-original/` 8 | 3 | byte-identical | `243133b66237523147e1a869ee5b1bf97ee28ec9d817c5c059921e9b254c5715` |
| G Phase-8 proposer | 661.99 s | `partition-graph-8-proposals` | 468 | — | 468 | byte-identical | `69ccbfb748f250e19baebb75789e57c66f4c26443286e43a9a85ca77f474a209` |
| H Phase-8 evaluator | 126.41 s | `partition-graph-8-evaluation` | 321 | `demo/` 107, `demo-package-original/` 107 | 107 | byte-identical | `01c8d253f5ea8698e8df290b7090f299d2fb462c6c40a0fdb04bdc7611525f7d` |

Every scope manifest equals the Core-2/Core-3 value for the same producer or evaluator.

### Supplementary replays (beyond the contract)

`fov3d/scene/__init__.py` now imports `.partition` eagerly. An import probe shows that
**all 12 Partition-Graph producer/evaluator entry points load `fov3d.scene.partition`**,
Phases 2 through 8b. That includes Phases 2, 6 and 7, which have no contract gate. Each of
those was replayed with accepted inputs to a fresh `conceptual-core-4-extra-*` directory.
Phase 6 used the inputs recorded in the accepted `partition-graph-6-proposals/summary.json`.

```text
.venv/bin/python tools/partition_graph2_lift.py previews/partition-graph-2-source-full previews/conceptual-core-4-extra-phase2-full
.venv/bin/python tools/partition_graph6_propose.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/partition-graph-5-full previews/conceptual-core-4-extra-phase6-proposals
.venv/bin/python tools/partition_graph6_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-6-proposals previews/conceptual-core-4-extra-phase6-evaluation
.venv/bin/python tools/partition_graph7_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-6-proposals previews/conceptual-core-4-extra-phase7-proposals
.venv/bin/python tools/partition_graph7_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-7-proposals previews/partition-graph-6-evaluation previews/conceptual-core-4-extra-phase7-evaluation
```

| run | wall | accepted reference | total | excluded | scope | result | scope manifest sha256 |
|---|---|---|---|---|---|---|---|
| Phase-2 lift | 6.08 s | `partition-graph-2-full` | 524 | `demo/` 107 | 417 | byte-identical | `8d3c87923bcba8cec41ca8b9033123e3b06c78c1ae36a6e97f25e1a29eb529e9` |
| Phase-6 proposer | 3.03 s | `partition-graph-6-proposals` | 102 | — | 102 | byte-identical | `30e88f61da7ef1d43bc9bb530418f2d03c1403347b26f22a0d9a1c211309bbad` |
| Phase-6 evaluator | 1.47 s | `partition-graph-6-evaluation` | 59 | `demo/` 28, `demo-package-original/` 28 | 3 | byte-identical | `b584139a0186e014627452c74c811ed7b5281f3351255ae2596340ef6ae96fff` |
| Phase-7 proposer | 47.21 s | `partition-graph-7-proposals` | 835 | — | 835 | byte-identical | `3dde52e4cd34228f91c240db3682dc489d9f1adb74a5e85a7021b58bff1673de` |
| Phase-7 evaluator | 19.52 s | `partition-graph-7-evaluation` | 321 | `demo/` 107, `demo-package-original/` 107 | 107 | byte-identical | `05d35ef37a6294c0b0da08a1f943d7c9c8daef93c22819adb9beb8bdb3da0515` |

All five COMPLETE lines are string-identical to earlier committed report lines. With these
runs, every Partition-Graph producer and evaluator from Phase 2 through 8b reproduces its
accepted scope byte for byte.

**Comparison method** (as in Core 3). Each comparison is two-sided:
1. The fresh set must **equal** the accepted set minus the declared exclusions.
2. No fresh file may lie under an excluded path.
3. Every pair must be byte-identical (`filecmp`, `shallow=False`).
4. The scope manifests must be equal. Each is computed as
   `cd DIR && LC_ALL=C find . -type f [-not -path './<excl>/*' ...] -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum`.

In every run, `only_fresh`, `only_accepted`, `fresh_under_excluded` and `byte_diff` were
all 0. The exclusions are only the post-producer `demo/` and `demo-package-original/`
trees demonstrated in the Core-2 report. No fresh tree contains one.

**Accepted trees unchanged.** Per-file sha256 manifests of the 13 trees read by the runs
were taken before Gate B and after the last supplementary replay, and they are identical.
The 12 trees shared with Core 3 still have their Core-3 manifests.

| tree | files | full-tree manifest sha256 (before = after) |
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

## Changed-function / dependency → execution-gate coverage

Line numbers refer to the final head.

| changed path | kind | exercised by | execution evidence |
|---|---|---|---|
| `fov3d/scene/__init__.py`, eager `.partition` import and 4 exports | changed package init; `import fov3d.scene` now also loads `partition`, `cv2`, `head_chart` and `association` | A (every checker importing `fov3d.scene`), B–H, supplementary 2, 6P, 6E, 7P and 7E | import probe: all 12 entry points load `fov3d.scene.partition`; every run byte-identical |
| `fov3d/scene/partition.py` module imports | new module dependencies | same as above | same |
| `SupportLayer`, `_disk`, `support_depth_from_map` | moved | A (Core-4; checkers 3 and 8), B, C, D, E, G | B: `lift_joint_run` → `joint.py:647`; C: `analyze_phase4` → `relations.py:451`; D: `analyze_phase5` → `incidental.py:193`; E: `propose_phase8b` → `challenge_suite.py:354`, `:367`; G: `propose_phase8` → `integration.py:264` |
| `joint_owner`, `_component_attrs`, `label_joint_regions` | moved | A (Core-4; checker 3 calls `label_joint_regions`), B, E | through `build_joint_graph` (`joint.py:250-251`). B: from `lift_joint_run` (`joint.py:652`); its 104 graphs hold 4,834 object-region and 1,548 BASE-region records, byte-identical. E: from `propose_phase8b` (`challenge_suite.py:360`), called unconditionally in the per-state loop, `states = 125` |
| `joint.py` module imports (4 names from `fov3d.scene`; association import removed) | changed module dependency | A (checkers 3, 4, 5 and 8; Core-4 identity), B, C (`relations` imports `joint`), E | as above |
| `relations.py` import | changed dependency | C | `analyze_phase4` |
| `incidental.py` import | changed dependency | D | `analyze_phase5` |
| `integration.py` import | changed dependency | G, H (module load) | `propose_phase8` |
| `challenge_suite.py` import | changed dependency | E, F (module load) | `propose_phase8b` |
| `tools/dev/check_conceptual_core4.py` | new checker | A; mutation harness | 25/25; 37/37 and 8/8 mutants caught |

The evaluators (Gates F and H, and the supplementary Phase-6/7 evaluators) do not call the
moved functions. They cover the changed module loading and confirm unchanged evaluator
output.

## Dependency audit (repository-wide, tracked files)

AST import-graph diff (absolute imports) between `main` and the final head, over `fov3d/`
and `tools/`:

- **5 removed edges:**
  - 4 cross-phase edges: `relations`, `incidental`, `integration` and `challenge_suite`
    no longer import `support_depth_from_map` from `joint`;
  - `joint`'s import of `SURFACE_ASSOCIATION_RADIUS_M`.
- **Added edges:**
  - those four modules and `joint` import from `fov3d.scene`;
  - `partition` imports `chart_cells`, `chart_grid` and `head_angles_from_unit` from
    `head_chart`, and `SURFACE_ASSOCIATION_RADIUS_M` from `association`;
  - the Core-4 checker imports as well.

  The relative edges `fov3d/scene/__init__ → .partition → .model` are new; the AST diff
  lists absolute imports only.
- **New edges into `fov3d.experiments`:** 1. It is the Core-4 dev checker importing
  `joint` for the identity check, which is intentional and not production code.
- **Non-experiment `fov3d` modules that import `fov3d.experiments`:** none. The checker
  now enforces this for all of `fov3d/scene/*.py`.

Every tracked occurrence of the four public names outside `docs/`:

| occurrence | classification |
|---|---|
| `fov3d/scene/partition.py`, `fov3d/scene/__init__.py` | conceptual owner and public export |
| `relations.py:19`, `incidental.py:26`, `integration.py:44`, `challenge_suite.py:38` | direct scene imports (required) |
| `joint.py:33-36` | conceptual import, internal use and compatibility re-export (required, see above) |
| `tools/dev/check_partition_graph{3,4,5,8}.py` | existing phase checkers using the compatibility names (unmodified by contract) |
| `tools/dev/check_conceptual_core4.py` | Core-4 checker |

**Not moved, and unchanged** (AST-identical to main, or `git diff` empty):
- boundary extraction (`_interface_edges`, `_trace_edge_components`,
  `extract_boundaries`) and `build_joint_graph` metadata;
- `gap_corridor`, `corridors_for_object`, `attach_state_region_codes`, and the lineage and
  `seen_any` replay helpers;
- `FineEvidence` and `add_patch_observation` (`relations.py`);
- `HeadEvidence` (`fov3d/epistemic`);
- `ObservationFootprint`, `ObservationOverlay` and `BoundaryChain` (`fov3d/scene/model.py`);
- benchmark and evaluator modules.

## Scientific / runtime behavior

None of the following changed:
- the 12-mm association rule and the radius/`ceil`/minimum-one-cell rasterization;
- nearest-depth and equal-depth tie behavior;
- foreground 8-connectivity and BASE 4-connectivity;
- region ids and code order, serialized strings and graph metadata;
- boundary extraction, and topology/relation semantics;
- benchmark and evaluator behavior;
- gaze, controller, matcher, fusion, renderer, scene and termination behavior;
- thresholds, accepted trees and golden signatures.

The evidence:
- a literal AST-identical extraction (annotation aside), and a randomized differential
  test identical in 300 cases;
- byte-identical producer output for Phases 2, 3, 4, 5, 6, 7, 8 and 8b;
- byte-identical evaluator output for Phases 6, 7, 8 and 8b;
- golden `MISMATCHES 0`, and baseline 31/31.

## Repairs and deviations

1. **Checker strengthened** (`44269cb`, delegated scope). It closes 18 behavioral and 1
   static surviving mutant, as described above. No existing check was modified.
2. **Stale map rows corrected** (`e49f58b`, docs only, allowed path):
   - `incidental.py`: `support_depth_from_map` now comes from `fov3d.scene`. The text was
     Code's own Core-3 row;
   - `challenge_suite.py`: it has not imported `incidental` since Core 3, which the
     Core-3 map commit missed; it now takes only `build_joint_graph` from `joint`;
   - `relations.py`: its scene import;
   - `joint.py`: the consumers of its compatibility imports.
3. **Supplementary replays** of Phases 2, 6 and 7 (producers and evaluators), beyond the
   contract gates. They are justified because the package init change reaches those
   phases. All are byte-identical.
4. **Additional evidence beyond the contract.** It comprises the AST and `symtable`
   checks, the randomized differential test, the mutation and equivalence harnesses, the
   import probes and the accepted-tree manifests before and after. It used throw-away
   harnesses in the session scratchpad, which are not committed.
5. Gate A was run twice, at the proposal and at the final code commit.

No other deviation. The contract gates' commands, inputs, output directories and
references are exactly the contract's. Code changed no production code.

## Unresolved

1. **`fov3d.scene` now requires OpenCV at import.** On `main`, `import fov3d.scene` loaded
   only `model`, `sphere` and NumPy (probe on a `git archive` of `989127c`). The eager
   export of `partition` the contract asks for now also loads `cv2`, `head_chart` and
   `association`, which makes the whole scene data model host-only. Blender's Python has
   no OpenCV (`docs/fov3d-api.md:53-54`).

   No Blender-side script imports `fov3d` today, so nothing breaks. The decision is
   whether this is acceptable, or whether the partition API should be exported lazily or
   kept as `fov3d.scene.partition` only. Relatedly, the `fov3d/__init__.py` docstring's
   list of OpenCV-dependent modules does not mention `fov3d.scene`. That file is outside
   Core-4 scope.
2. **Dropped documentation** (the same pattern as Core-3 unresolved item 3). The
   extraction dropped:
   - the docstrings of `support_depth_from_map` (the frozen 12-mm footprint; `depth_m` is
     used only to resolve overlap) and `label_joint_regions` (8-connectivity versus dual
     4-connectivity);
   - the `joint_owner` comment "Exact equal-depth ties are only a deterministic raster
     convention";
   - the "Digital-topology duality" comment;
   - the return annotation of `label_joint_regions`.

   These record semantics that the contract itself states. Restoring them is
   comment/annotation-only. It was not done here, so that the gated bytes remain final.
   Future Chat extractions could preserve docstrings and comments verbatim.
3. **Unreachable tie clause.** In `joint_owner`, the tie clause is redundant with sorted
   iteration (it is an equivalent mutant). The documented semantics hold either way; no
   action is needed, but no checker can distinguish the two mechanisms.
4. **Cosmetic.** `joint.py` imports `ObjectHypothesis`, which the move left unused.
   `Iterable` and `math` were already unused on `main`.
5. **Compatibility names** in `joint.py` stay alive through its own composition code and
   checkers 3, 4, 5 and 8. Retargeting those checkers needs a contract that permits
   editing phase checkers, as in Core-3 item 2.
6. **Gate-selection methodology.** The contract gates omitted Phases 2, 6 and 7, although
   a package `__init__` change reaches them. Future contracts could treat an `__init__`
   export change as touching every importer, or require the import probe.
7. **Chat Handoff.** `docs/chat-handoff.md` should be updated if Core 4 is accepted, with
   the new main commit and `fov3d.scene.partition` ownership.
8. The Core-3 unresolved items (target-relative placement, `incidental` compatibility
   names, dropped `head_memory` comments, checker naming) and the Core-2 items are carried
   over unchanged.

## Recommendation (Conceptual Core 5 only)

Map item 4, bounded to **boundary extraction**. Move `_interface_edges`,
`_trace_edge_components` and `extract_boundaries` (4-neighbour interface enumeration and
`BoundaryChain` tracing) out of `joint.py` into a scene module (for example
`fov3d.scene.boundaries`). They operate only on `region_code` and the region maps, and
their sole consumer is `build_joint_graph`, used by Phases 3 and 8b.

Leave the following untouched:
- the Phase-2 boundary construction in `lift.py`, a separate lineage whose unification
  is a later question;
- `gap_corridor` and relation extraction (`relations.py`), lineage, and `seen_any` replay;
- benchmark policy.

Settle unresolved item 1 first, because it decides whether a new scene module may be
re-exported eagerly.

Gates:
- the Phase-3 joint lift against `partition-graph-4-lift`;
- the Phase-4 and Phase-5 analyzers;
- the Phase-8b proposer and evaluator;
- Phases 2, 6 and 7 if the `fov3d.scene` exports change;
- Phase 8 only if an `integration.py` path changes;
- a checker with a mutation harness covering interface enumeration, chain ordering and
  boundary ids.

## Success marker

    CONCEPTUAL_CORE4_SCENE_PARTITION_PRESERVES_BEHAVIOR
