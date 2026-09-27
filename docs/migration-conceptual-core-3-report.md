# Migration Conceptual Core 3 — report (2026-09-27)

Executed by Claude Code on the Ubuntu workstation against the committed contract
`docs/migration-conceptual-core-3.md`. Every number below is **MEASURED** from the
command shown, unless it is marked otherwise.

## Provenance

| item | value |
|---|---|
| branch | `migration/conceptual-core-3` |
| parent accepted milestone | `main` @ `a48124e44655c0021bebbff623dbf11de05f478a` (merge base verified; `origin/main` is the same commit) |
| proposal head | `35b7a2e127970c0bb17b4ea28c0dd333dabdaa87`, verified as the pulled head: 10 Chat-authored commits `9745637`…`35b7a2e` |
| Code commits | `ee73f6c` Core-3 checker strengthened · `6c52d7a` map row made precise · the commit that adds this report |
| gates measured at | Gate A at `35b7a2e` (proposal checker, 24 checks), then the whole of Gate A again at `6c52d7a` (final checker, 27 checks); Gates B–I at `ee73f6c` |
| final head | the commit that adds this report |

`fov3d/` is byte-identical at `35b7a2e`, `ee73f6c` and `6c52d7a`. Code changed only the
dev checker and one map row, so every gate ran against the proposed production code.

## Files changed (main...final head)

| file | change |
|---|---|
| `fov3d/epistemic/__init__.py` | new (proposal) |
| `fov3d/epistemic/head_memory.py` | new (proposal): `HeadEvidence`, `add_head_patch` |
| `fov3d/experiments/classroom_partition/incidental.py` | definitions removed; imports them from the conceptual module (proposal) |
| `fov3d/experiments/classroom_partition/{prefix_benchmark,integration,challenge_suite}.py` | one import statement each (proposal) |
| `tools/dev/check_conceptual_core3.py` | new (proposal); strengthened by Code (`ee73f6c`) |
| `docs/migration-conceptual-core-3.md` | contract (proposal) |
| `docs/conceptual-core-map.md` | Core-3 status and section (proposal); `incidental.py` row made precise by Code (`6c52d7a`) |
| `CLAUDE.md` | Chat-Handoff process addition, +15 lines (proposal) |
| `docs/migration-conceptual-core-3-report.md` | this report |

The following are untouched (`git diff a48124e..HEAD` is empty for each):
- `relations.py` (`FineEvidence`, `add_patch_observation`) and `fov3d/scene/`;
- every existing phase checker, every producer, evaluator and demo under `tools/`, and
  `scripts/`;
- `tests/golden/`;
- sealed runtime files (`verify_baseline.sh` 31/31);
- the 12 accepted preview trees read by the gates, by sha256 manifests before and after.

## Final public head-memory API and dependency direction

    fov3d.geometry.head_chart               chart_grid, chart_cells, head_angles_from_unit
    fov3d.reconstruction.measurement_memory valid_patch_measurements
            -> fov3d.epistemic.head_memory
                   HeadEvidence            dataclass, HeadEvidence.empty(shape)
                   add_head_patch(ev, patch, target_id, domain, grid_deg)
                       -> {"valid_points", "new_depth_cells", "depth_cells"}
            -> fov3d.experiments.classroom_partition
                   incidental (Phase 5), prefix_benchmark (7), integration (8),
                   challenge_suite (8b)

A fresh interpreter that imports `fov3d.epistemic.head_memory` loads exactly `fov3d`,
`fov3d.epistemic`, `fov3d.epistemic.head_memory`, `fov3d.geometry`,
`fov3d.geometry.head_chart`, `fov3d.reconstruction` and
`fov3d.reconstruction.measurement_memory`. It loads no experiment module, even
transitively.

### Target-neutral versus target-relative state (unchanged semantics)

| field | dtype, initial | class | update rule |
|---|---|---|---|
| `depth_seen` | bool, False | target-neutral | cell of every in-domain valid sample; cumulative |
| `nearest_instance` | int32, 0 | target-neutral | nearest sample per cell by metric range; exact tie → smaller id (within a patch by the `lexsort` key, across patches by the update rule) |
| `nearest_range_m` | float32, +inf | target-neutral | range of that nearest sample |
| `ambiguous_instance` | bool, False | target-neutral, monotone | more than one identity in a cell within one patch, or the stored nearest identity differs from the patch's nearest identity |
| `sample_count` | uint16, 0 | target-neutral | per-cell sample count, saturating at 65535 |
| `target_depth_seen` | bool, False | **target-relative** | cells holding a sample whose id equals the supplied `target_id` |
| `other_depth_seen` | bool, False | **target-relative** | cells holding a sample whose id differs from the supplied `target_id` |

The target-relative fields stay stored in `HeadEvidence` and keep their exact update
rules. The module docstring documents the distinction.

Repository audit of the readers of the two target-relative fields: the only production
reader is Phase 5 (`incidental.py:91` in `annotate_head_relation`, and `incidental.py:230-231`
where they are serialized). Phases 7, 8 and 8b accumulate their global memory with
`target_id` set to each patch's acquiring target, then read only target-neutral fields:
- `_memory_state` copies `depth_seen`, `nearest_instance`, `nearest_range_m`,
  `ambiguous_instance` and `sample_count`;
- `challenge_suite` reads `depth_seen`, `nearest_instance` and `ambiguous_instance`.

## Compatibility and re-export decision

`incidental.py` imports `HeadEvidence` and `add_head_patch` from
`fov3d.epistemic.head_memory` and defines neither. The AST check below confirms this,
and the Core-3 checker asserts `is` identity. The re-export is **required**, not
cosmetic:

- `incidental.analyze_phase5` and `annotate_head_relation` use both names;
- the unmodified `tools/dev/check_partition_graph5.py:11`,
  `check_partition_graph7.py:11` and `check_partition_graph8.py:11` import them through
  `incidental`. The contract forbids editing existing phase checkers to accommodate the
  refactor.

No other tracked file imports these names through `incidental`.

## Pre-execution review (Code)

**1. Literal extraction (AST).** After stripping docstrings, the AST dumps of
`HeadEvidence` and `add_head_patch` in `head_memory.py` equal those in `main`'s
`incidental.py`. No other top-level definition of `incidental.py` changed. The only
textual differences are these:
- the second paragraph of the `add_head_patch` docstring was dropped;
- three inline comments were dropped;
- two statements were re-wrapped.

See unresolved item 3.

**2. Randomized differential test** (throw-away harness, not committed). It compared
`main`@`a48124e` `incidental.add_head_patch` with `head_memory.add_head_patch` over:
- 400 multi-patch histories, 1,423 patches in total;
- grids of 0.25°, 0.5° and 1.0°;
- ranges quantized to five values, so exact ties are frequent;
- ids 0–5, where 0 is invalid;
- 10 % invalid samples and 3 % NaN samples;
- out-of-domain samples in 1,392 patches;
- 16 histories that start near uint16 saturation.

In every history, all 7 fields (dtype, shape and values) and every returned delta were
identical.

**3. Checker fail-capability (mutation testing).** This led to the repair below.

## Repair: Core-3 checker strengthened (`ee73f6c`)

Each mutant is a text substitution on `head_memory.py`, and the harness asserts that it
matches exactly once. The mutant is executed into `sys.modules` before the checker
imports `incidental`. As a result, `incidental` re-exports the mutant and the identity
check cannot produce a false alarm (the harness artifact reported in Core 2). The static
mutants were applied to `git archive` copies of the tree. The harness is throw-away and
not committed.

| mutant | proposal checker (24) | strengthened (27) |
|---|---|---|
| cross-patch tie → larger id | caught | caught |
| **within-patch tie → larger id** (`lexsort` id key reversed) | **survived** | caught |
| farther sample wins | caught | caught |
| within-patch farthest selected | caught | caught |
| tie keeps old (strict `<` only) | caught | caught |
| **`target_depth_seen` marks every observed cell** | **survived** | caught |
| `other_depth_seen` marks every cell | caught | caught |
| target / other swapped | caught | caught |
| `other_depth_seen` excludes target cells | caught | caught |
| no history ambiguity | caught | caught |
| no same-patch ambiguity | caught | caught |
| ambiguity not monotone | caught | caught |
| `valid_points` counted before domain filter | caught | caught |
| no uint16 saturation | caught | caught |
| count cells instead of samples | caught | caught |
| `nearest_instance` int64 | caught | caught |
| `nearest_range_m` initialized to 0 | caught | caught |
| `depth_seen` not cumulative | caught | caught |
| `new_depth_cells` counts all patch cells | caught | caught |
| static: Phase 7 imports via `incidental` | — | caught (`later phases import conceptual head memory directly`) |
| static: Phase 8 imports via `incidental` | — | caught (same) |
| static: lazy `fov3d.experiments` import inside `head_memory.py` | — | caught (`epistemic package has no experiment dependency`) |
| static: duplicate `add_head_patch` defined in `incidental.py` | — | caught (`incidental compatibility identity`) |

Both survivors change contract-listed semantics (contract items 4 and 7). The repair
adds three checks on a fresh `HeadEvidence`, using one patch:
- an exact range tie listed larger id first;
- a farther sample with a smaller id;
- a target-only cell and a non-target-only cell.

The new checks are `within-patch delta`, `within-patch exact tie prefers smaller instance`
and `target-relative flags are conditioned on target_id`. Existing checks are unchanged.
The unmutated checker gives 27/27, and all 19 behavioral and 4 static mutants are caught.
This is the delegated "strengthen the Core-3 checker" scope; no acceptance gate was
touched.

Note on the proposal's two "negative … mutant rejected" checks: `negative tie-rule mutant
rejected` compares against the literal `max(8, 6)`, and `negative target-rule mutant
rejected` repeats `target-relative fields can both accumulate`. They restate positive
checks, and the second one did not reject `target_depth_seen marks every cell`. Both are
kept unchanged. The fail-capability evidence is the mutation table above.

## Gate A — interactive

Measured at `35b7a2e` (proposal checker 24/0), then the whole gate again at `6c52d7a`:

```text
compile: 7 changed Python files OK
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

The golden comparison took 9.80 s. The phase checkers 5, 7, 8 and 8b load
`fov3d.epistemic.head_memory` (import probe). Checkers 5, 7 and 8 load it through the
`incidental` compatibility names.

## Replay gates B–I

All commands were run from the repository root, in order, each to a fresh directory:

```text
B .venv/bin/python tools/partition_graph4_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/conceptual-core-3-phase4-full
C .venv/bin/python tools/partition_graph5_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/partition-graph-4-full previews/conceptual-core-3-phase5-full
D .venv/bin/python tools/partition_graph7_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-6-proposals previews/conceptual-core-3-phase7-proposals
E .venv/bin/python tools/partition_graph7_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-7-proposals previews/partition-graph-6-evaluation previews/conceptual-core-3-phase7-evaluation
F .venv/bin/python tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals previews/conceptual-core-3-phase8b-proposals
G .venv/bin/python tools/partition_graph8b_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8b-proposals previews/partition-graph-8-evaluation previews/conceptual-core-3-phase8b-evaluation
H .venv/bin/python tools/partition_graph8_integrate.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-7-proposals previews/conceptual-core-3-phase8-proposals
I .venv/bin/python tools/partition_graph8_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8-proposals previews/partition-graph-7-evaluation previews/conceptual-core-3-phase8-evaluation
```

```text
B [partition-graph4-analyze] COMPLETE {"causal_own_support_gap": 44, "causal_ownership_cut": 42, "causal_relations": 86, "states": 104, "target_depth_checks": 51, "target_depth_mismatches": 0}
C [partition-graph5-analyze] COMPLETE {"challenge_relations": 108, "challenge_states": 41, "challenge_targets": 4, "states": 104, "target_gap_violations": 0}
D [partition-graph7-propose] COMPLETE {"global_candidates": 17202, "local_candidates": 8557, "phase6_final_local_parity": 25, "states": 104, "targets": 25, "truth_used": false}
E [partition-graph7-evaluate] COMPLETE {"final": {"covered": 25618, "missed": 3670, "reachable": 29288}, "global_2plus_positive_states": 68, "global_recall": 0.4347697988686361, "local_2plus_positive_states": 63, "local_recall": 0.9713230672532999, "states": 104}
F [partition-graph8b-propose] COMPLETE {"eligible_candidates": 6489, "full_phase8_parity": 25, "raw_candidates": 18469, "scenarios": 5, "states": 125, "targets": 25, "truth_used": false}
G [partition-graph8b-evaluate] COMPLETE {"full_eligible_recall": 0.9335820895522388, "full_integrated_covered": 27948, "full_integrated_residual": 1340, "scenarios": 5, "states": 125}
H [partition-graph8-integrate] COMPLETE {"candidate_regions": 16825, "phase7_global_parity": 104, "states": 104, "target_evidence_unmapped_cells": 0, "targets": 25, "truth_used": false}
I [partition-graph8-evaluate] COMPLETE {"cross_target_gain": 61538, "final_integrated_covered": 27948, "final_integrated_residual": 1340, "historical_state_misses": 101824, "integration_gain": 61557, "own_target_retention_gain": 19, "residual_candidate_recall": 0.955472222912062, "residual_state_misses": 40267, "states": 104}
```

Every required COMPLETE value in the contract matches (C, D, F, G, H, I). The following
lines are string-identical to accepted or prior report lines:
- E, G and I, to the accepted evaluator lines;
- C, D, F and H, to the Core-1/Core-2 and phase reports.

B is not quoted verbatim in any report. Its values agree with
`docs/partition-graph-4-report.md`: 104 states, 86 causal relations = 42 `ownership_cut`
+ 44 `own_support_gap`, and 51 checkpoints with 0 mismatches.

| gate | wall | accepted reference | accepted total | excluded | producer/evaluator files (fresh = accepted scope) | result | scope manifest sha256 |
|---|---|---|---|---|---|---|---|
| B Phase-4 analyzer | 6.87 s | `partition-graph-4-full` | 425 | `demo/` 107, `demo-package-original/` 107 | 211 | byte-identical | `eca1b6ad798117de8d2de321e0ebfe6f92cb3e73a8f0b80e78e494f8a3f3cd8c` |
| C Phase-5 analyzer | 8.38 s | `partition-graph-5-full` | 225 | `demo/` 7, `demo-package-original/` 7 | 211 | byte-identical | `77f5ae3d408900c8b2428553f22a97fae60aeddef34ea1f500a78e39d07c68eb` |
| D Phase-7 proposer | 47.93 s | `partition-graph-7-proposals` | 835 | — | 835 | byte-identical | `3dde52e4cd34228f91c240db3682dc489d9f1adb74a5e85a7021b58bff1673de` |
| E Phase-7 evaluator | 19.67 s | `partition-graph-7-evaluation` | 321 | `demo/` 107, `demo-package-original/` 107 | 107 | byte-identical | `05d35ef37a6294c0b0da08a1f943d7c9c8daef93c22819adb9beb8bdb3da0515` |
| F Phase-8b proposer | 62.48 s | `partition-graph-8b-proposals` | 503 | — | 503 | byte-identical | `51a93fc464fc8ce00fc7f519ccadc25f539095be06de074788844b12ad6e7b7d` |
| G Phase-8b evaluator | 16.74 s | `partition-graph-8b-evaluation` | 19 | `demo/` 8, `demo-package-original/` 8 | 3 | byte-identical | `243133b66237523147e1a869ee5b1bf97ee28ec9d817c5c059921e9b254c5715` |
| H Phase-8 proposer | 658.89 s | `partition-graph-8-proposals` | 468 | — | 468 | byte-identical | `69ccbfb748f250e19baebb75789e57c66f4c26443286e43a9a85ca77f474a209` |
| I Phase-8 evaluator | 126.06 s | `partition-graph-8-evaluation` | 321 | `demo/` 107, `demo-package-original/` 107 | 107 | byte-identical | `01c8d253f5ea8698e8df290b7090f299d2fb462c6c40a0fdb04bdc7611525f7d` |

All eight scope manifests equal the Conceptual Core 2 values for the same producers and
evaluators. During Gate H, Code ran a few seconds of static analysis (`git grep`, AST
scripts); its wall time compares with 667.27 s in Core 2.

**Comparison method.** Each comparison is two-sided:
1. The fresh file set must **equal** the accepted set minus the declared exclusions.
2. No fresh file may lie under an excluded path.
3. Every pair must be byte-identical (`filecmp` with `shallow=False`).
4. The scope manifests must be equal. Each is computed as
   `cd DIR && LC_ALL=C find . -type f [-not -path './demo/*' -not -path './demo-package-original/*'] -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum`,
   the formula of the Core-1/Core-2 reports; it reproduces their recorded values.

In every gate, `only_fresh`, `only_accepted`, `fresh_under_excluded` and `byte_diff` were
all 0.

**Exclusions** are exactly the post-producer demo trees demonstrated in the Core-2
report: `demo/` is the default output of the phase demo tools, and
`demo-package-original/` is the retained package demo documented in each phase report.
No producer or evaluator writes either, and no fresh tree contains one.

**Accepted trees unchanged.** Per-file sha256 manifests of all 12 accepted trees read by
the gates were taken before Gate B and after Gate I, and they are identical:

| tree | files | full-tree manifest sha256 (before = after) |
|---|---|---|
| `partition-graph-2-source-full` | 1122 | `9c4def894e2573c22722336cf200d794e30d566f88108cdde3ee3722da7ff53d` |
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
| `fov3d/epistemic/__init__.py` | new package | A, C–I (every import of `head_memory`) | the entry modules of C–I import `head_memory` at module level; import probes of B's entry (does not load it) and of checkers 5, 7, 8 and 8b (load it) |
| `head_memory` module imports (`chart_grid`, `chart_cells`, `head_angles_from_unit`, `valid_patch_measurements`) | new module dependencies | A, C, D, F, H | executed on every `add_head_patch` call below |
| `head_memory.HeadEvidence` / `.empty` | moved | A (Core-3 27 checks; checkers 5, 7 and 8), C, D, F, H | C writes 104 `states/global_*/head-evidence.npz`, each with all 7 fields, byte-identical |
| `head_memory.add_head_patch` | moved | A (Core-3; checker 5), C, D, F, H | same 104 npz files (C); 104 `global_head_memory_delta` records in Phase-7 `summary.json` (D); `full_phase8_parity 25` (F); `phase7_global_parity 104` (H) |
| `incidental.py` module imports (4 names removed; epistemic import added; compatibility re-export) | changed module dependency | A (checker 5; Core-3 identity), C | `analyze_phase5` calls `HeadEvidence.empty` (`:189`) and `add_head_patch` (`:192`); `annotate_head_relation` (`:205`) reads `target_depth_seen` (`:91`) |
| `incidental.analyze_phase5`, `annotate_head_relation` | names now resolve to the conceptual module | C | byte-identical 211-file Phase-5 scope |
| `prefix_benchmark.py` import | changed module dependency | A (checkers 7 and 8), D, E (module load), H (`_memory_state`) | `propose_phase7` `:178`, `:198`, `_memory_state` `:217`; Phase 8 calls `_memory_state` at `integration.py:239` |
| `integration.py` import | changed module dependency | A (checker 8), H, I (module load) | `propose_phase8` `:190`, `:220` |
| `challenge_suite.py` import | changed module dependency | A (checker 8b), F, G (module load) | `propose_phase8b` `:324`, `:340` |
| `tools/dev/check_conceptual_core3.py` | new checker | A; mutation harness | 27/27; 19/19 and 4/4 mutants caught |

The evaluators (`evaluate_phase7`, `evaluate_phase8` and `evaluate_phase8b`) do not
reference `HeadEvidence` or `add_head_patch`. Gates E, G and I therefore cover only the
changed import of their module, and they confirm unchanged evaluator output.

**Gate B separation.** An import probe of `fov3d.experiments.classroom_partition.relations`
(the Phase-4 entry point) loads neither `fov3d.epistemic.head_memory` nor any changed
module. Its output is byte-identical (211 files). Core 3 did not couple the persistent
memory to `FineEvidence`.

## Dependency audit (repository-wide, tracked files)

AST import-graph diff between `main` and the final head, over `fov3d/` and `tools/`:

- **9 removed edges:**
  - 6 cross-phase edges: Phases 7, 8 and 8b (`prefix_benchmark`, `integration` and
    `challenge_suite`) no longer import `HeadEvidence` or `add_head_patch` from
    `incidental`;
  - 3 edges from `incidental` itself, which drops `chart_cells`, `head_angles_from_unit`
    and `valid_patch_measurements`.
- **Added edges:** those same four modules now import from `fov3d.epistemic.head_memory`.
  `head_memory` imports from `head_chart` and `measurement_memory`. The Core-3 checker
  imports as well.
- **New edges into `fov3d.experiments`:** 1. It is the Core-3 dev checker importing
  `incidental` for the identity check, which is intentional and not production code.
- **Conceptual (non-experiment) `fov3d` modules that import `fov3d.experiments`:** none.

Every tracked occurrence of `HeadEvidence`, `add_head_patch` or `head_memory` outside
`docs/`:

| occurrence | classification |
|---|---|
| `fov3d/epistemic/head_memory.py` | conceptual owner |
| `prefix_benchmark.py:34`, `integration.py:40-43`, `challenge_suite.py:49-52` | direct conceptual imports (required) |
| `incidental.py:28` | conceptual import and compatibility re-export (required, see above) |
| `tools/dev/check_partition_graph5.py:11`, `check_partition_graph7.py:11`, `check_partition_graph8.py:11` | existing phase checkers using the compatibility names (unmodified by contract) |
| `tools/dev/check_conceptual_core3.py` | Core-3 checker |

`FineEvidence` (`relations.py:43`) and `add_patch_observation` (`relations.py:70`) have
not moved and are unchanged. `ObservationFootprint` (`fov3d/scene/model.py:195`) and
`ObservationOverlay` (`:216`) have not moved and are unchanged.

## Scientific / runtime behavior

None of the following changed:
- chart mapping, resolution or rounding, and valid-patch filtering;
- nearest, tie, ambiguity or sample-count rules, and target-relative versus
  target-neutral semantics;
- `FineEvidence` and observation-overlay semantics;
- partition, benchmark, evaluator or candidate semantics, and gaze, controller, matcher,
  fusion, renderer, scene or termination behavior;
- thresholds, accepted trees and golden signatures.

The evidence:
- a literal AST-identical extraction, and a randomized differential test identical in
  1,423 patches;
- byte-identical producer output for Phases 4, 5, 7, 8 and 8b;
- byte-identical evaluator output for Phases 7, 8 and 8b;
- golden `MISMATCHES 0`, and baseline 31/31.

## CLAUDE.md process addition

`CLAUDE.md` gains one 15-line subsection, "Chat Handoff at accepted main milestones",
under "Repository as source of truth". At every accepted `main` milestone it requires a
compact handoff section or file. The handoff records:
- the accepted `main` commit;
- the accepted state;
- the active next step;
- decision-critical open items.

It is explicitly a recovery index, not a competing source of truth. No other line of
`CLAUDE.md` changed (`git diff` shows +15 and −0). Code did not change this text.

## Repairs and deviations

1. **Checker strengthened** (`ee73f6c`, delegated scope). Two surviving mutants were
   closed, as described above. No existing check was modified.
2. **Map row made precise** (`6c52d7a`, docs only, allowed path). The `incidental.py`
   row now names the compatibility consumers, its remaining `lift`/`joint` imports, and
   that it is the only production reader of the target-relative fields.
3. **Additional evidence beyond the contract gates.** It comprises the AST extraction
   check, the randomized differential test, the mutation harness, the import probes and
   the accepted-tree manifests before and after. It used throw-away harnesses in the
   session scratchpad, which are not committed.
4. Gate A was run twice, at the proposal and at the final code commit.

No other deviation. The commands, inputs, output directories and references are exactly
the contract's. Code changed no production code.

## Unresolved

1. **Target-relative state placement.** `target_depth_seen`/`other_depth_seen` are read
   only by Phase 5. In the cross-target global memory of Phases 7, 8 and 8b they are
   accumulated against each patch's acquiring target and never read. Whether they should
   become a Phase-5 target-conditioned view is a representation decision the contract
   defers.
2. **Compatibility names.** They remain only because the unmodified phase checkers 5, 7
   and 8 (and Phase 5 itself) use them. Retargeting those checkers to
   `fov3d.epistemic.head_memory` would need a contract that permits editing existing
   phase checkers.
3. **Dropped explanatory text.** The extraction dropped:
   - the docstring paragraph explaining that `xyz_h` is already head-frame, so no left-eye
     ray projection or parallax compensation applies;
   - three inline comments, including "Ties prefer the smaller instance id only for
     determinism".

   This does not affect behavior, but the tie comment records that the tie rule is a
   determinism device, not a scientific claim. Restoring it is comment-only. It was not
   done here, so that the gated code bytes remain the final ones.
4. **Checker naming.** The two proposal checks named "negative … mutant rejected" restate
   positive checks (see above). Chat may prefer to rename or replace them. Their
   fail-capability is recorded in the mutation table.
5. **Chat Handoff location.** `CLAUDE.md` now requires a handoff section or canonical
   file at every accepted `main` milestone, but none exists yet, for `a48124e` or for
   Core 3 if it is accepted. Luiz and Chat should decide between section and file, and
   who writes it at acceptance.
6. The Core-2 items are carried over unchanged: the alias decision, the `0.012` in
   `partition_graph6_demo.py`, the twin of the sealed-runtime radius, and the reference
   registry.

## Recommendation (Conceptual Core 4 only)

Map item 3, **scene partition construction**. Move generic support rasterization and
joint ownership/region construction out of `joint.py` behind the scene representation
API. `support_depth_from_map` is consumed by Phases 4, 5, 8 and 8b, and `incidental.py`
still imports it from `joint`. Leave the following untouched:
- `FineEvidence`;
- topology/relations and benchmark policy;
- the target-relative question (unresolved item 1), a representation decision rather
  than a structural move.

Gates:
- the Phase-3 joint lift against `partition-graph-4-lift`;
- producers 4, 5, 7, 8b and 8. The approximately 11-minute Phase-8 gate is needed if
  `integration.py` or its imports change;
- evaluators 7, 8 and 8b, plus the Phase-6 evaluator if `benchmark.py` is touched;
- the coverage table with import probes, and a checker with a mutation harness.

## Success marker

    CONCEPTUAL_CORE3_HEAD_MEMORY_PRESERVES_BEHAVIOR
