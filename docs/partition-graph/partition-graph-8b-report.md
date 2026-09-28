# Partition-Graph Phase 8b — budgeted integrated residual challenge suite report (2026-09-25)

The contract is `docs/partition-graph-8b.md`. This phase constructs a benchmark only.

- **No attention score, ranking, gaze policy, controller, matcher, fusion, rendering or scene
  change was designed, implemented, tuned or evaluated.**
- The frozen parameters were used unchanged:
  - budgets 1, 2, 4, 8 and FULL looks per target;
  - 5° UNKNOWN shells;
  - a 25-cell (0.25 deg²) eligibility floor;
  - the 0.10° chart.
- Nothing was tuned after truth results were seen.
- The budget scenarios are retrospective replays of the saved accepted trajectory. They are
  not new acquisitions and not controller results.

Earlier reports are preserved unchanged.

## Provenance

| | |
|---|---|
| branch | `architecture/partition-graph-8b`, tracking `origin/architecture/partition-graph-8b` |
| `e0feb8d` Add budgeted integrated residual challenge suite | package commit (by `PARTITION_GRAPH8B_APPLY.sh`, author Luiz Velho) on the required parent `dcc2719f9c11480f69d4bfa885837cece6fa7986`; zip sha256 `0071c607…e913e1`, as the apply script expected |
| package content | adds exactly `fov3d/experiments/classroom_partition/challenge_suite.py`, `tools/partition_graph8b_{propose,evaluate,demo}.py`, `tools/dev/check_partition_graph8b.py` and `docs/partition-graph-8b.md` (943 insertions); all byte-identical to the zip; modifies no existing file |
| `3bf35fc` Repair Phase-8b demo launch: add repository root to sys.path | mechanical launch repair (see below) |
| `4480197` Fix Phase-8b demo keys, colours and evaluation panel | presentation-only demo fix |
| this commit, Report Partition Graph Phase 8b | this report |

No `PARTITION_GRAPH8B_CODE_PROMPT.md` was present in the repository root.

## Deviations and repairs

- **No package defect affected a reported quantity.** The proposer and evaluator ran
  unchanged, and every hard gate passed on the first run.
- **Demo launch repair (`3bf35fc`).** The prescribed command
  `./.venv/bin/python tools/partition_graph8b_demo.py …` failed with
  `ModuleNotFoundError: No module named 'fov3d'`. Unlike the package's proposer and
  evaluator CLIs, the demo had no repository-root `sys.path` bootstrap. The repair adds
  that three-line bootstrap and nothing else.
- **Demo presentation fix (`4480197`).** No measurement or frame selection changed.
  - Titles contained an em dash, which OpenCV's Hershey font renders as `???`.
  - The middle-panel key said "pale orange" for candidates below the floor, but the BGR
    values rendered pale blue and were invisible at fragment size. These candidates are now
    a visible orange, and region edges no longer cover them.
  - The left panel had no key, and AMBIGUOUS_BOUNDARY was pink on the left but gray in the
    middle. It is now pink in both.
  - The evaluation panel was blank apart from a 16-digit recall in the footer. It now
    lists the evaluator's counts as text; no truth locations are drawn.
  - The package demo, with only the launch repair applied, is kept at
    `previews/partition-graph-8b-evaluation/demo-package-original/`.
- **Supplementary offline analysis (untracked).** This is
  `previews/partition-graph-8b-analysis.{py,json}`.
  - The package evaluator stores only per-state aggregates. To answer the shell,
    multi-region and duplicate questions, this script re-derives each state's residual on
    the evaluation side. It reads dense reachable truth read-only, exactly as the evaluator
    does, and writes only its JSON.
  - It first reproduces the evaluator's raw and eligible metrics and residual for all 125
    states: **0 mismatches**.
  - It then measures the same states in the **pre-shell (base) view**, using the stored
    `original_region_code`, and traces each eligible positive to its base component.
  - The proposal tree was re-hashed unchanged after it.

## Gates

```text
py_compile (5 Phase-8b files) -> OK
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
[verify] compiled 95 tracked .py files in memory, errors=0
[verify] 31 files tracked at baseline-classroom-oracle1-2026-09-25 are byte-identical in the working tree
[verify] SUMMARY passed=9 failed=0
compare_golden.sh previews/partition-graph-2-source-full    -> [compare-golden] MISMATCHES 0
run_golden.sh --smoke previews/partition-graph-8b-golden-smoke (fresh)
compare_golden.sh --smoke previews/partition-graph-8b-golden-smoke -> [compare-golden] MISMATCHES 0
git diff --check -> clean
```

These gates were run before the proposer and again after the demo fix and this report.

**Existing inputs**, used as-is and not regenerated:

- `partition-graph-5-full`: 104 states, 0 head-depth violations.
- `partition-graph-8-proposals`: 104 states, `truth_used: false`, TARGET_EVIDENCE_UNMAPPED
  0 cells and 0 states, Phase-7 parity 104. Its tree still matches the Phase-8 hash
  `110fc50d…`.
- `partition-graph-8-evaluation`: final integrated covered / residual **27,948 / 1,340**.

The source manifest has 25 targets and 104 looks. Historical looks per target are eleven
×1, 2, 2, 2, 3, 3, 3, 4, 5, 6, 6, 7, 12, 19 and 19, so the budgets cap 14, 11, 7, 3 and 0
targets.

## Truth-free proposer

```text
[partition-graph8b-propose] COMPLETE {"eligible_candidates": 6489, "full_phase8_parity": 25, "raw_candidates": 18469, "scenarios": 5, "states": 125, "targets": 25, "truth_used": false}
propose wall=61.05s maxrss=532940KB
```

- **Hard requirements, all met.**
  - 5 scenarios × 25 targets = **125 states**, 25 per scenario.
  - `full_phase8_parity_checks` = **25**: FULL arrays, regions and edges are exactly equal
    to the Phase-8 integrated partitions at all 25 target-final states.
  - `truth_used: false`; `gaze_policy_defined` / `candidate_ranking_defined` false.
  - **TARGET_EVIDENCE_UNMAPPED = 0 cells at every one of the 125 states.**
  - The parameters recorded in `summary.json` are exactly the frozen ones.
- **Partition invariants, checked independently on all 125 states: 0 failures.**
  - Every chart cell carries exactly one refined region, and region sizes sum to the chart.
  - Every refined region lies inside a single base region.
  - Every non-UNKNOWN base region is preserved one-to-one.
  - Every UNKNOWN refined region lies in a single 5° shell.
  - The largest raw candidate region in any state is **18.1 %** of the chart.
- **Tables inspected.** These were `benchmark-states.json`, `candidate-regions.json`
  (18,469 raw rows: UNKNOWN 2,864, OTHER_SURFACE 15,605; eligible 6,489), and per-state
  `summary.json`/`regions.json` for alphabet, blackBoard, sol, wall.008 and woodBase in all
  five scenarios.
  - Retained looks, the original global index and head-depth growth follow the budget. For
    example, woodBase is 1/19 → 2 → 4 → 8 → 19/19 looks, at head depth 63.4 → 68.8 → 74.7 →
    82.6 → 89.5 %.
  - UNKNOWN shells 0–8 are present.
- **Memory strata over the 125 states:** 0–25 % 24 states, 25–50 % 50, 50–75 % 37,
  75–100 % 14.
- **OS-level trace.** The proposer was rerun under `strace -f -e openat,open,execve` into
  `previews/partition-graph-8b-proposals-strace`, with log
  `previews/partition-graph-8b-propose.strace`.
  - Source-run opens: `manifest.json` 1, `bootstrap/seeds.json` 1, `patches/fix_XX.npz`
    (304 opens of all 104 patches, which FULL retains), and retained `maps/fix_XX.npz`
    (125 opens of 60 distinct prefix maps). That is 166 distinct files with **0**
    write-mode opens.
  - Other reads are only the Phase-5 tree (125 opens) and the Phase-8 proposal tree (76
    opens: 25 × partition/regions/edges plus its summary). The only writes are to the
    traced output tree.
  - **0** opens of `evaluation_only`, `reachable_samples.npz`, `evaluation.json`,
    `oracle_observation.npz`, EXR, benchmark RGB or Blender. A filename pattern match on
    `benchmark` hit only the `classroom_partition/benchmark` module `.pyc` and the
    proposer's own output `benchmark-states.json`.
  - One `execve` (the venv Python). Repository modules loaded were only the CLI and `fov3d`:
    the package init, the `classroom_partition` modules `benchmark`, `challenge_suite`,
    `incidental`, `integration`, `joint`, `lift` and `prefix_benchmark`, and `fov3d.scene`'s
    `model` and `sphere`. There was no sealed `tools/*` engine, no controller, matcher,
    fusion or renderer, and no `bpy`.
- **Determinism.** The traced rerun's 503 files are **byte-identical** to the official
  proposal (378 JSON and 125 NPZ; same file list). The official proposal was not
  overwritten.

## Proposal-tree immutability

```text
503 files, deterministic manifest (find -print0 | sort -z | xargs -0 sha256sum)
sha256(previews/partition-graph-8b-proposals.before.sha256) = 5d8de1e351c5176a6e0f8c07fde4ce3493136a93c522342117b3dc1ba0615b27
sha256(previews/partition-graph-8b-proposals.after.sha256)  = 5d8de1e351c5176a6e0f8c07fde4ce3493136a93c522342117b3dc1ba0615b27
diff -u before after -> empty
```

The traced evaluation shows **0** write-mode opens under the proposal tree. The tree was
re-verified unchanged after the supplementary analysis and both demo generations.

## Offline truth evaluator

```text
[partition-graph8b-evaluate] COMPLETE {"full_eligible_recall": 0.9335820895522388, "full_integrated_covered": 27948, "full_integrated_residual": 1340, "scenarios": 5, "states": 125}
evaluate wall=17.84s maxrss=327176KB
```

- **FULL hard parity.** Integrated covered **27,948 = 27,948** and residual
  **1,340 = 1,340**, reproducing Phase 8.
- **Reads (traced).**
  - `manifest.json`, `seeds.json` and `evaluation_only/reachable_samples.npz`;
  - the same retained patches and maps;
  - the Phase-8b proposal tree;
  - the Phase-8 evaluation summary, for parity.

  It opened no EXR, oracle observation or Blender file, made one `execve`, and wrote only
  the three files under `previews/partition-graph-8b-evaluation`.

## Scenario results

Residual is post-integration and at 12 mm. 29,288 reachable samples in every scenario.

| | budget_1 | budget_2 | budget_4 | budget_8 | full |
|---|---|---|---|---|---|
| looks retained (of 104) / targets capped | 25 / 14 | 39 / 11 | 58 / 7 | 78 / 3 | 104 / 0 |
| integrated covered | 19,912 (68.0 %) | 21,903 (74.8 %) | 23,169 (79.1 %) | 25,657 (87.6 %) | 27,948 (95.4 %) |
| **integrated residual** | **9,376** | **7,385** | **6,119** | **3,631** | **1,340** |
| head-depth coverage at the last target | 68.4 % | 72.2 % | 76.4 % | 84.2 % | 90.1 % |

**Raw candidate view** (all UNKNOWN shell regions and OTHER_SURFACE):

| | budget_1 | budget_2 | budget_4 | budget_8 | full |
|---|---|---|---|---|---|
| candidate recall | 0.9599 | 0.9590 | 0.9590 | 0.9601 | 0.9336 |
| positive / negative candidates | 53 / 3,535 | 47 / 3,550 | 36 / 3,643 | 26 / 3,717 | 13 / 3,849 |
| states with 0 / 1 / ≥ 2 positives | 8 / 5 / 12 | 10 / 3 / 12 | 12 / 5 / 8 | 14 / 3 / 8 | 20 / 1 / 4 |
| states with a > 50 %-of-chart positive region | 0 | 0 | 0 | 0 | 0 |
| captured in ≤ 5 % / (5, 15] % / (15, 50] % / > 50 % regions | 2,911 / 5,909 / 180 / 0 | 3,491 / 3,487 / 104 / 0 | 2,521 / 3,303 / 44 / 0 | 2,415 / 1,071 / 0 / 0 | 1,127 / 124 / 0 / 0 |

**Eligible candidate view** (raw candidates of at least 25 cells):

| | budget_1 | budget_2 | budget_4 | budget_8 | full |
|---|---|---|---|---|---|
| candidate recall | 0.9599 | 0.9586 | 0.9588 | 0.9598 | 0.9336 |
| positive / negative candidates | 53 / 1,170 | 46 / 1,158 | 35 / 1,313 | 25 / 1,371 | 13 / 1,305 |
| states with 0 / 1 / ≥ 2 positives | 8 / 5 / 12 | 10 / 3 / 12 | 12 / 5 / 8 | 14 / 3 / 8 | 20 / 1 / 4 |
| states with a > 50 %-of-chart positive region | 0 | 0 | 0 | 0 | 0 |
| captured in ≤ 5 % / (5, 15] % / (15, 50] % / > 50 % regions | 2,911 / 5,909 / 180 / 0 | 3,488 / 3,487 / 104 / 0 | 2,520 / 3,303 / 44 / 0 | 2,414 / 1,071 / 0 / 0 | 1,127 / 124 / 0 / 0 |
| … as a share of the residual | 31.0 / 63.0 / 1.9 / 0 % | 47.2 / 47.2 / 1.4 / 0 % | 41.2 / 54.0 / 0.7 / 0 % | 66.5 / 29.5 / 0 / 0 % | 84.1 / 9.3 / 0 / 0 % |

**Pre-shell (base) view of the same states**, for comparison only:

| | budget_1 | budget_2 | budget_4 | budget_8 | full |
|---|---|---|---|---|---|
| raw positive regions | 27 | 26 | 22 | 17 | 7 |
| states with 0 / 1 / ≥ 2 positives | 8 / 12 / 5 | 10 / 8 / 7 | 12 / 8 / 5 | 14 / 7 / 4 | 20 / 3 / 2 |
| states with a > 50 % positive region | **12** | **7** | **6** | **6** | 1 |
| residual in > 50 % regions | **5,140 (54.8 %)** | 2,135 (28.9 %) | 1,996 (32.6 %) | 1,021 (28.1 %) | 33 (2.5 %) |

Recall is identical in the base and refined views, because the shells only subdivide
UNKNOWN.

## Diversity and degeneracy across the 125 states

Aggregate over the 125 states: residual 27,851; raw recall 0.9582; eligible recall 0.9580.

- **Targets with residual.** 17 of 25 targets have residual in at least one scenario (per
  scenario 17 / 16 / 15 / 14 / 11). Text, Text.001, beams, ceiling, lettersPlank.001,
  lettersPlank.002, pipe and wallPlug.001 never do.
- **Targets with an eligible truth-positive candidate.** 17 overall (per scenario
  17 / 15 / 13 / 11 / 5). 61 states have one (57 distinct proposal states).
- **States with at least two eligible positives.** 44 states (12 / 12 / 8 / 8 / 4) across
  12 targets. However:
  - **only 23 of them** (5 / 7 / 5 / 4 / 2) have positives in **two or more distinct base
    components**;
  - those 23 come from just **7 targets**: blackBoardLamp, sol, verticalPipe, wall.008,
    woodBase, woodBaseboard and worldMap;
  - **76 of the 172 eligible positive regions** are extra shells of a base component that
    is already positive.

  The other 21 multi-positive states are one residual UNKNOWN component cut into adjacent
  shells.
- **Residual concentration by target** (all 125 states):
  - woodBase 7,971 (28.6 %), blackBoard 6,811 (24.5 %) and sol 6,612 (23.7 %): **top-3
    76.8 %**;
  - next come woodBaseboard 4.6 %, boardFrame 3.3 %, plank 3.1 % and wall.008 3.0 %;
  - 4 targets hold 80 % of the residual, and the inverse-Simpson effective number of
    targets is **4.9**;
  - eligible captured residual has a top-3 share of 78.4 %;
  - per scenario the top-3 share is **72.6 / 75.7 / 80.1 / 84.0 / 94.0 %**, and 5 / 4 / 3 /
    3 / 2 targets hold 80 %;
  - **the same three objects lead every reduced budget.**
- **Composition versus difficulty.**
  - Scene composition: these three objects hold 47.2 % of all reachable truth (woodBase
    22.6 %, blackBoard 15.8 %, sol 8.8 %).
  - Difficulty: at budget_1 their residual rates are sol 0.68, blackBoard 0.52 and woodBase
    0.40. By contrast wall.008 holds 20.1 % of reachable truth but only 3.0 % of residual
    (rate 0.07 at budget_1), because cross-target memory covers it.
- **Where the eligible positives sit.** 73.4 % of eligible captured residual lies in the
  0–5° shell next to integrated target support, 20.2 % in 5–10°, 4.7 % in 10–15°, 1.6 %
  beyond that and 0.1 % in OTHER_SURFACE. 40 of the 61 positive states have an eligible
  positive outside the 0–5° shell. Eligible positive regions are UNKNOWN 157 and
  OTHER_SURFACE 15, with chart fractions of median 2.9 %, P25 1.5 %, P75 5.2 % and max
  18.1 %.
- **Redundancy of the replay.** Scenarios are nested prefixes of one gaze sequence per
  target in one fixed object order.
  - 111 of the 125 proposal states are distinct.
  - Text, Text.001 and alphabet are identical in all five scenarios, and beams in
    budget_4/8/full: 14 reduced-budget states identical to FULL.

### By memory-density stratum (eligible view)

| stratum | states (b1/b2/b4/b8/full) | targets with residual | residual | dominant targets | eligible positives | states with ≥ 2 positives / ≥ 2 distinct components | recall | base view: > 50 % states, residual share |
|---|---|---|---|---|---|---|---|---|
| 0–25 % | 24 (8/4/4/4/4) | 5 | 2,648 | **blackBoard 90.4 %** | 23 | 8 / **1** | 0.966 | 9, 96.5 % |
| 25–50 % | 50 (11/12/12/8/7) | 11 | 8,254 | blackBoard 53.5 %, sol 21.2 % | 49 | 12 / 3 | 0.942 | 23, 94.1 % |
| 50–75 % | 37 (6/9/8/7/7) | 9 | 15,552 | woodBase 43.9 %, sol 31.2 % | 88 | 20 / **16** | 0.967 | 0, 0 % |
| 75–100 % | 14 (0/0/1/6/7) | 6 | 1,397 | **woodBase 81.3 %** | 12 | 4 / 3 | 0.933 | 0, 0 % |

### Did the two declared parameters do their job?

- **5° UNKNOWN shells: yes, for the early giant-complement degeneracy.**
  - In the base view of the same 125 states, 32 states (every sparse-memory state with a
    positive) had a > 50 %-of-chart positive region, holding 10,325 residual misses (37.1 %).
    In both sparse strata, 94–97 % of the residual sat in such regions.
  - With shells there are **0** such states and 0 misses. Residual captured in > 15 %
    regions falls from 18,598 (66.8 %) to 328 (1.2 %), and no candidate exceeds 18.1 % of
    the chart.
  - The cost is the inflated multi-positive count above: raw positive regions rise from
    99 to 175.
- **25-cell eligibility floor: yes, for micro fragments, at negligible cost.**
  - It marks 11,980 of 18,469 raw candidates (64.9 %) ineligible, cutting negatives from
    **18,294 to 6,317 (−65.5 %)**.
  - It loses **3** of 175 positive regions and **5** of 26,687 captured residual misses
    (0.02 %). Recall is 0.9582 → 0.9580.
  - Every sub-floor raw candidate stays represented.

## Decision: is the integrated residual benchmark now broad and non-degenerate enough for Phase 9?

**No.** The contract's criterion (§8) is residual spread across many targets, multiple eligible
positive regions, and no dominating giant complements. Phase 8b meets the third, partly meets
the second, and does not meet the first:

1. **Giant complements: fixed.** No > 50 % positive region in any scenario (from 32 states).
   Micro negatives are down 65.5 % with essentially no recall loss.
2. **Multiple eligible positive regions: only partly.** 44 states have ≥ 2 eligible
   positives, but only 23 have them in distinct components.
   - Those 23 come from 7 targets, and 16 of them fall in one memory stratum (50–75 %).
   - The sparse 0–25 % stratum has one such state.
3. **Spread across targets: not met.**
   - Budget reduction scales the residual (1,340 → 9,376) but does not move it. The same
     three large surfaces hold 72.6–94.0 % of the residual in every scenario (76.8 %
     overall), and the effective number of targets is 4.9.
   - Each memory stratum is dominated by one or two objects: blackBoard is 90.4 % of the
     sparsest stratum and woodBase 81.3 % of the densest.
   - An attention result on this suite would mostly measure three objects in one
     trajectory.

The reason is structural. All five scenarios replay the same scene, object order and gaze
sequence, so they change how much memory exists but not where the information gaps are. Part
of the concentration is scene composition (47.2 % of reachable truth on three surfaces), and
part is where the trajectory leaves those surfaces unseen.

## Recommendation (bounded; no policy)

1. **Keep the Phase-8b construction frozen as the benchmark view.** This covers
   instance-keyed integration, 5° UNKNOWN shells, the 25-cell eligibility floor, budget
   replay and memory strata. Report raw and eligible results, and when counting multiple
   positives, count distinct base components as well as shell regions.
2. **Change the information geometry next. First step: multiple different start gazes and
   seeds in the same classroom.**
   - These are separate non-golden runs, with the sealed golden baseline and scene assets
     untouched, each processed by the same Phase-5/8/8b pipeline and optionally budget-replayed.
   - Different starts change the object order, which objects inherit cross-target memory, and
     where each trajectory leaves gaps. This addresses the difficulty component and the
     one-trajectory redundancy directly, at the lowest cost.
3. **If sample-weighted residual stays dominated by the same large surfaces across seeds,
   move to another scene.** That domination would mean the composition component (47.2 % of
   reachable truth on three surfaces) persists.
4. **Before running the next setting, predeclare its breadth acceptance criteria.** Examples
   are the top-3 residual share, the number of targets with distinct-component multi-positive
   states, and per-stratum dominance. Phase-9 readiness should not be judged post hoc.

## Demo inspection

`previews/partition-graph-8b-evaluation/demo/` contains:

- 5 frames (1560 × 440), one per scenario;
- `partition-graph-8b-demo.mp4` (5 frames at 1.5 fps; decodes all 5);
- `overview.png` (1560 × 660);
- `Demo.md`.

The frames are the package's evaluation-side display selection, the highest-residual target
per scenario: woodBase at budgets 1, 2, 4 and 8, and sol at FULL.

- **Orientation:** positive pitch is up. The alphabet frieze is at the top and the floor at
  the bottom.
- **Left panel:** integrated partition with key. Green TARGET_SUPPORT visibly grows with
  budget; for woodBase the looks are 1, 2, 4, 8 of 19 and head depth goes 63.4 → 82.6 %.
  **0 magenta TARGET_EVIDENCE_UNMAPPED pixels in all 5 frames.**
- **Middle panel:** 5° UNKNOWN shells, lighter near target support and darker farther, plus
  about 850 visible orange sub-floor candidate pixels per frame along the lettering and
  board edges.
- **Right panel:** labelled **EVALUATION ONLY**. It lists the evaluator's counts for that
  state (retained looks, stratum, covered/residual, raw and eligible candidates, positives,
  recall, largest positive region and area bins) and draws no truth locations.
- **No score, ranking or policy** appears in any panel.

## Immutability and behaviour

Relative to `dcc2719` the changes are:

- the package commit (6 new files);
- the demo launch repair and the demo presentation fix (both only
  `tools/partition_graph8b_demo.py`, a package file);
- this report.

Every file tracked at the sealed baseline is untouched, including the `tools/*` engine,
`fov3d` facade wrappers, `tests/golden/`, `scripts/` and scene assets. The baseline verifier
reports 31/31 byte-identical. The historical maps and patches were only read, and the source
and fresh-smoke comparators report `MISMATCHES 0`. `previews/` stays untracked.

**No gaze, controller, matcher, fusion, rendering, scene-asset, termination or golden
behaviour changed, and no score, ranking or policy was introduced.**

PARTITION_GRAPH8B_CHALLENGE_SUITE_NEEDS_NEW_SETTING
