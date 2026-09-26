# Partition-Graph Phase 8 — causal target-evidence integration report (2026-09-25)

The contract is `docs/partition-graph-8.md`. This phase is a representation and integration
benchmark only.

- **No gaze policy, score or candidate ranking was designed, implemented, tuned or
  evaluated.**
- **The historical SurfaceMap and all sealed baseline behaviour are untouched.** Integration
  is a shadow union evaluated retrospectively.
- **Integrated coverage is a counterfactual architecture measurement**, using geometry the
  historical system had already measured causally. It is not a controller achievement.

Earlier reports are preserved unchanged.

## Provenance

| | |
|---|---|
| branch | `architecture/partition-graph-8`, tracking `origin/architecture/partition-graph-8` |
| `6d67edb` Add causal target-evidence integration benchmark | package commit (applied by `PARTITION_GRAPH8_APPLY.sh`, author Luiz Velho) on `59d0572` (Phase-7 report); package sha256 `236bab2d…8a85055`, as the apply script expected |
| package content | adds exactly `fov3d/experiments/classroom_partition/integration.py`, `tools/partition_graph8_{integrate,evaluate,demo}.py`, `tools/dev/check_partition_graph8.py` and `docs/partition-graph-8.md`; all byte-identical to the zip; modifies no existing file |
| `ffdc026` Fix Phase-8 demo region colours, key and overview | presentation-only demo fix |
| this commit, Report Partition Graph Phase 8 | this report |

`git diff 59d0572..6d67edb --stat` shows 6 files and 1,263 insertions. No
`PARTITION_GRAPH8_CODE_PROMPT.md` was present in the repository root, so nothing untracked
needed excluding. The zip's `__pycache__/*.pyc` files are gitignored.

## Deviations and repairs

- **No mechanical repair and no package defect.** Integrator and evaluator ran unchanged,
  and every hard gate passed on the first run.
- **Runtime.** The integrator took 653 s (max RSS 0.55 GB). Its per-state 12 mm novelty
  checks run over up to 1.23 M measured target points per state. This is noted only as a
  runtime observation.
- **Demo presentation fix (`ffdc026`).** No measurement changed.
  - The package coloured UNKNOWN components with arbitrary saturated colours, including
    purple, green and red. These collided with the semantic key: in sol's frames an
    UNKNOWN region looked like TARGET_EVIDENCE_UNMAPPED "that should disappear", although
    sol has no such evidence. UNKNOWN is now pale-tinted with dark region edges.
  - The key named the target-evidence colour "purple" (it renders magenta) and omitted
    AMBIGUOUS_BOUNDARY.
  - The keyed gray "historical miss" layer can never be visible: every historical miss is
    exactly one of gain (cyan) or residual (red). This was verified at every state.
  - The overview showed consecutive states of two targets. It now shows one frame per
    target for eight targets.
  - The package demo is kept at `previews/partition-graph-8-evaluation/demo-package-original/`.
- **Supplementary read-only analysis (untracked).** `previews/partition-graph-8-analysis.{py,json}`
  reads only Phase-8/Phase-7 JSON outputs.

## Gates

```text
py_compile (5 Phase-8 files) -> OK
[partition-graph1-check] SUMMARY checked=13 failed=0
[partition-graph2-check] SUMMARY checked=16 failed=0
[partition-graph3-check] SUMMARY checked=20 failed=0
[partition-graph4-check] SUMMARY checked=14 failed=0
[partition-graph5-check] SUMMARY checked=12 failed=0
[partition-graph6-check] SUMMARY checked=12 failed=0
[partition-graph7-check] SUMMARY checked=12 failed=0
[partition-graph8-check] SUMMARY checked=10 failed=0
[consolidation3-facade-check] SUMMARY checked=16 failed=0
[verify] compiled 90 tracked .py files in memory, errors=0
[verify] 31 files tracked at baseline-classroom-oracle1-2026-09-25 are byte-identical in the working tree
[verify] SUMMARY passed=9 failed=0
compare_golden.sh previews/partition-graph-2-source-full   -> [compare-golden] MISMATCHES 0
compare_golden.sh --smoke previews/partition-graph-8-golden-smoke -> [compare-golden] MISMATCHES 0
git diff --check -> clean
```

**Phase-5/7 inputs**, present and unchanged:

- `partition-graph-5-full`: 104 states, 0 head-depth violations.
- `partition-graph-7-proposals`: truth-free, 104 states; its tree still matches the Phase-7
  hash `5aa71f39…`.
- `partition-graph-7-evaluation`: `state_count` **104**, historical prefix state-misses
  **101,824**, final **29,288 / 25,618 / 3,670**.

## Truth-free integrator

```text
[partition-graph8-integrate] COMPLETE {"candidate_regions": 16825, "phase7_global_parity": 104, "states": 104, "target_evidence_unmapped_cells": 0, "targets": 25, "truth_used": false}
```

- **Hard requirements, all met.** 104 states, 25 targets, `truth_used: false`,
  `phase7_global_parity_checks` = **104**, `historical_map_modified: false`,
  `gaze_policy_defined` / `candidate_ranking_defined` false, `object_identity_inherited: true`.
- **TARGET_EVIDENCE_UNMAPPED eliminated.** Integrated cells total **0**, and states with
  unmapped cells **0**.
- **Declared source reads.** `manifest.json` 1, `bootstrap/seeds.json` 1, 104
  `patches/fix_XX.npz` and 104 `maps/fix_XX.npz`; `forbidden_read_paths: []`.
- **Evidence causality, checked independently** from each target's
  `causal-target-evidence.npz`:
  - every cross-target sample (`source_active_target_id ≠ target`) has
    `source_global_index` < the target's first state;
  - every own-target sample lies within the target's own run;
  - no sample is later than the target-final state;
  - **0 violations over 25 targets**, and `all_sources_causal: true` for all 25.

- **OS-level trace.** The integrator was rerun under `strace -f -e openat,open,execve`,
  writing a separate output `previews/partition-graph-8-proposals-strace` and the log
  `previews/partition-graph-8-propose.strace`. The run completed with the same COMPLETE line.
  - Source-run opens are exactly `manifest.json` 1, `bootstrap/seeds.json` 1, 104
    `patches/fix_XX.npz` and 104 `maps/fix_XX.npz`: 210 distinct files, **0** write-mode
    opens, so the historical maps were only read.
  - Other reads are only the Phase-5 tree (105 opens) and the Phase-7 proposal tree (313
    opens). The only writes go to the traced output tree (468 files).
  - **0** opens of `evaluation_only`, `reachable_samples.npz`, `evaluation.json`,
    `oracle_observation.npz`, EXR, benchmark RGB or Blender. A filename pattern match on
    `benchmark` hit only `fov3d/experiments/classroom_partition/__pycache__/benchmark.cpython-312.pyc`,
    the Phase-6 partition module.
  - One `execve` (the venv Python). Repository modules loaded were only the CLI and `fov3d`:
    the package init, the `classroom_partition` modules `benchmark`, `incidental`,
    `integration`, `joint`, `lift` and `prefix_benchmark`, and `fov3d.scene`'s `model` and
    `sphere`. There was no sealed `tools/*` engine, no controller, matcher, fusion or
    renderer, and no `bpy`.
- **Determinism.** The traced rerun's 468 files are **byte-identical** to the official
  proposal (339 JSON and 129 NPZ files; same file list). The official proposal was not
  overwritten.

## Proposal-tree immutability

```text
468 files, deterministic manifest (find -print0 | sort -z | sha256sum)
sha256(previews/partition-graph-8-proposals.before.sha256) = 110fc50d507f5dfd38234efe33fb34c089eff1bcfe0bf8874d2c170416700d34
sha256(previews/partition-graph-8-proposals.after.sha256)  = 110fc50d507f5dfd38234efe33fb34c089eff1bcfe0bf8874d2c170416700d34
diff -u before after -> empty
```

The traced evaluation shows **0** write-mode opens under the proposal tree. The tree was
re-verified unchanged after the analysis, both demo generations and the traced rerun.

## Offline truth evaluator

```text
[partition-graph8-evaluate] COMPLETE {"cross_target_gain": 61538, "final_integrated_covered": 27948, "final_integrated_residual": 1340, "historical_state_misses": 101824, "integration_gain": 61557, "own_target_retention_gain": 19, "residual_candidate_recall": 0.955472222912062, "residual_state_misses": 40267, "states": 104}
```

- **Exact Phase-7 historical parity.** `phase7_historical_state_parity` = **104**: covered
  and missed values equal Phase 7 at every state. Historical prefix totals are covered
  247,191 and missed **101,824**, matching Phase 7. Historical final totals are **29,288 /
  25,618 / 3,670**.
- **Monotone coverage.** Historical ⊆ historical + cross-target ⊆ fully integrated coverage
  was asserted at every state. No historically covered truth sample is lost.
- **Reads.** The evaluator (traced) read:
  - `manifest.json`, `seeds.json` and `evaluation_only/reachable_samples.npz`;
  - the 104 prefix maps (183 opens, including the next-prefix pass);
  - the Phase-8 proposal tree;
  - Phase-7 `state-evaluation.json`, for parity.

  It opened no EXR, oracle observation or Blender file, made one `execve`, and wrote only
  under `previews/partition-graph-8-evaluation`.

## A. How much target geometry was already available?

| | all 104 prefixes (summed per state) | 25 target-final prefixes |
|---|---|---|
| historical map points | 7,923,742 | 945,080 |
| causal measured target points | 42,400,447 | 4,184,494 |
| … own-target provenance | 15,642,423 | 2,131,339 |
| … cross-target provenance | 26,758,024 (63 %) | 2,053,155 (49 %) |
| measured evidence already within 12 mm of the historical map | 34,646,883 | 3,897,078 |
| measured evidence novel beyond 12 mm | 7,753,564 | 287,416 |
| … of which cross-target | **7,753,564 (all)** | **287,416 (all)** |
| … of which own-target | **0** | **0** |
| target-support cells: historical → integrated (added) | 1,725,244 → 2,231,904 (+506,660) | 186,026 → 210,666 (+24,640) |

- Cross-target evidence exists at 96 of 104 states and for 22 of 25 targets at their final
  state. Text, Text.001 and sol have none.
- Cross-target evidence at the final state comes from up to 19 source targets: wall.008 has
  795,787 cross-target points from 19 earlier targets.
- **Every novel sample is cross-target.** The target's own measurements always lie within
  12 mm of its historical map, so the historical within-target fusion discarded essentially
  no own geometry. Raw own-target retention adds only 19 state-samples of coverage (§B).

## B. Integration gain

| | all prefixes | 25 target-final prefixes |
|---|---|---|
| historical misses | 101,824 | 3,670 |
| covered by cross-target evidence | **61,538** | **2,328** |
| additional gain only from retaining raw own-target evidence | **19** | **2** |
| total integration gain | **61,557** | **2,330** |
| residual misses | **40,267** | **1,340** |
| historical misses removed without a new look | **60.5 %** | **63.5 %** |
| coverage | — | historical 25,618 / 29,288 (87.47 %) → integrated **27,948 / 29,288 (95.42 %)** |

The measured gain equals the Phase-7 evaluation-side counterfactual exactly (61,557 and
2,330). Per target at the final state (historical misses → residual):

- **fully resolved by integration:** lettersPlank 382 → 0, woodBaseboard 634 → 0,
  ceilingMoulding 306 → 0, blackBoard_upPart 76 → 0;
- **nearly resolved:** boardFrame 342 → 2, blackBoardLamp 61 → 2;
- **largely resolved:** wall.008 404 → 33;
- **largely unaffected:** **sol 1,043 → 1,043**, plank 259 → 173, coat 1 50 → 44,
  alphabet 55 → 33, wall 7 → 7.

## C. Does integration remove the memory problem cleanly?

**Yes.** Integrated TARGET_EVIDENCE_UNMAPPED is 0 cells at all 104 states, the proposer
asserts this at every state, and the evaluator finds 0 residual misses in
TARGET_EVIDENCE_UNMAPPED. The demo shows 0 magenta pixels in all 104 integrated panels.

## D. Residual region benchmark (post-integration residual, 40,267 state-misses)

| | Phase-8 integrated residual | Phase-7 global (all 101,824 misses) |
|---|---|---|
| candidate regions | 16,825 (UNKNOWN 1,368, OTHER_SURFACE 15,457) | 17,202 |
| truth-positive candidate regions | **129** (UNKNOWN 91, OTHER_SURFACE 38), **0.77 %** of candidates | 535 (3.1 %) |
| states with 0 / 1 / ≥ 2 positives | **39 / 25 / 40** | 16 / 20 / 68 |
| candidate recall | **0.955** on the residual (38,474 / 40,267) | 0.435 |
| captured in ≤ 5 % / (5, 15] % / (15, 50] % / > 50 % of chart | 1,855 / **21,361** / 3,686 / **11,572** | 6,429 / 22,448 / 3,790 / 11,603 |
| … as a share of the residual | 4.6 % / **53.0 %** / 9.2 % / **28.7 %** | — |
| misses by kind | UNKNOWN 38,417 (95.4 %), TARGET_SUPPORT **1,793** (4.5 %), OTHER_SURFACE 57; TARGET_EVIDENCE_UNMAPPED 0, AMBIGUOUS 0 | **TARGET_EVIDENCE_UNMAPPED 52,838 (51.9 %)**, AMBIGUOUS 1,796, TARGET_SUPPORT 2,920, candidates 44,270 |
| largest positive-region fraction by state | 65 states: min 0.002, P25 0.113, **median 0.119**, P75 0.209, max 0.884 | 88 states: min 0.0006, P25 0.096, median 0.120, P75 0.163, max 0.884 |
| states whose largest positive region is ≤ 15 % / > 50 % of chart | 45 / 9 | 62 / 9 |
| giant (> 50 %) positive regions | **9**, all at **states 2 (alphabet) and 6–13 (blackBoard)** | 9 (the same early states) |
| negative candidate regions ≤ 10 cells | 9,756 | 9,905 |

Structure of the residual:

- **Concentrated in three targets.** woodBase 16,848 (41.8 %, 19 states), blackBoard 12,990
  (32.3 %, 11 states) and sol 8,095 (20.1 %, 6 states) together hold **94.2 %**. The other 22
  targets share 5.8 %.
- **Multi-positive states also come from only three targets.** All **40** states with at
  least two positive candidates are consecutive states of wall.008 (19), woodBase (16) and
  sol (5). States with any positive span only 8 targets.
- **Some states have nothing to find.** 23 states have no residual, and 16 more have residual
  only inside TARGET_SUPPORT.
- **Final residual (1,340).** UNKNOWN 1,248, TARGET_SUPPORT 89, OTHER_SURFACE 3. **sol
  alone holds 1,043 (78 %).**
- **Positives and negatives differ sharply in size.** Positive regions have a median of 8,107
  cells, negatives a median of 6 cells.
  - This is a descriptive observation, not a parameter chosen here. A 50-cell floor would
    keep 112 of 129 positives (38,424 of 38,474 captured misses) and cut negatives from
    16,696 to 3,886.

## E. Historical-next reference after integration (79 nonterminal prefixes)

| | count |
|---|---|
| next-gaze centre on an integrated candidate | **21** (UNKNOWN 9, OTHER_SURFACE 12) |
| centre on TARGET_SUPPORT (non-candidate) | 57 |
| centre on AMBIGUOUS_BOUNDARY | 1 |
| centre in a current residual truth-positive region | 46 (TARGET_SUPPORT 39, UNKNOWN 7) |
| centre in a region with residual truth gained at the next prefix | 25 (TARGET_SUPPORT 19, UNKNOWN 6) |
| next-prefix gain before crediting integration (Phase 7) | 14,273 |
| next-prefix gain after crediting integration (Phase 8) | **4,882** (**−65.8 %**) |

About two thirds of what the historical next looks appeared to gain was geometry that had
already been measured and only needed routing. The historical controller is a behavioural
reference, not an optimal label.

## F. Architecture interpretation

**1. Does the measured gain justify persistent target-evidence routing as part of the
architecture? Yes.**

- It removes 60.5 % of all prefix misses and 63.5 % of final misses with no new fixation,
  raising 12 mm coverage from 87.5 % to 95.4 %.
- Essentially all of the gain (61,538 of 61,557) comes from routing measured geometry to its
  instance regardless of which target was active. Retaining raw own-target measurements adds
  only 19 samples.
- The design implication is instance-keyed persistent routing of every valid measurement,
  not a change to the historical within-target fusion.
- Caveats:
  - this is a raw union with no averaging, so a production design needs deduplication or
    fusion (at the final state 4.18 M evidence points are held against a 0.95 M-point
    historical map);
  - routing relies on Oracle-1's inherited instance labels, which a non-oracle system would
    have to earn.

**2. After integration is credited, is the remaining benchmark localized and
non-degenerate enough to justify Phase 9 as the first graph-level attention experiment?
Not yet.** The memory problem is now removed cleanly. What remains is a narrow benchmark,
not a representation defect:

1. **Concentration.** 94 % of residual state-misses belong to three objects (woodBase,
   blackBoard, sol). Every multi-positive state comes from three objects' consecutive,
   strongly correlated states, and 78 % of the final residual is one object (sol). A policy
   evaluated here would effectively be evaluated on about three objects.
2. **Early giant complements.** 28.7 % of the residual lies in nine > 50 %-of-chart
   positive regions, all in prefixes 2–13, while head-centred memory is still sparse. Phase 7
   measured global depth cells at 4.4 % of the chart at state 0 and 35.5 % at state 10.
3. **Candidate granularity.** Positives are 0.77 % of candidates; 9,756 negatives are
   fragments of at most 10 cells, while positives are large.

## Recommendation (bounded; no policy)

1. **Adopt persistent instance-keyed target-evidence routing as part of the representation.**
   The Phase-8 shadow union is the reference, and a proper deduplicating fusion design is
   its own engineering task.
2. **Declare the two missing benchmark parameters explicitly and truth-free**, rather than
   tuning them on outcomes:
   - a minimum candidate-region size, or a fragment-merge rule, for the micro negatives;
   - either a fixed subdivision of early-prefix giant UNKNOWN complements, or stratification
     that reports sparse-memory early prefixes separately.
3. **Broaden the residual before any attention policy.** The golden trajectory's residual is
   too concentrated to support a first graph-attention experiment. Build additional
   challenge settings that yield residual spread across many objects and states: other
   seeds or start gazes, budget-limited replays, or another scene. Run them as separate
   experiments with the sealed golden baseline untouched, and apply the same integrated
   representation to each.
4. **Only then define Phase 9's first graph-level attention experiment**, on that broadened
   integrated residual benchmark.

## Demo inspection

`previews/partition-graph-8-evaluation/demo/`:

- 104 frames, 1252 × 1120;
- `partition-graph-8-demo.mp4` (104 frames at 4 fps; decodes through all 104 frames);
- `overview.png` (1252 × 2240, eight different targets);
- `Demo.md`.

Confirmed on the fixed demo:

- **Orientation:** positive pitch is up.
- **Historical-global vs integrated panels:** they differ visibly exactly where integration
  matters. For example, at wall.008 state 56 the historical panel's large magenta
  TARGET_EVIDENCE_UNMAPPED area (33,247 display pixels) becomes green target support in the
  integrated panel (green 17,528 → 66,300 pixels; magenta 0).
- **TARGET_EVIDENCE_UNMAPPED disappears:** 0 magenta pixels in all 104 integrated panels.
- **Truth panel:** labelled **EVALUATION ONLY**. Cyan integration-gain cells and red residual
  cells match `truth-evaluation.npz` with **0 pixel mismatches** in all 104 frames. Gain and residual are disjoint and together equal the historical misses at every
  state, so no separate gray layer can appear; the key now says so.
- **No policy shown:** no score, ranking or policy is displayed.
- **Overview covers the full range**, one frame per target:
  - woodBase at state 76 and wall.008 at state 56 (large gain);
  - woodBaseboard at state 95 and worldMap at state 97 (no residual left after integration);
  - lettersPlank at state 30 and boardFrame at state 23;
  - blackBoard at state 6 (gain 246, residual 2,394) and sol at state 39 (gain 0, residual
    1,753), residual that integration barely touches.

## Immutability and behaviour

Relative to `59d0572` the changes are the package commit (6 new files), the demo
presentation fix and this report. Every file tracked at `6c8a80f` is untouched, including
the sealed `tools/*` engine, `fov3d` facade wrappers, `tests/golden/`, `scripts/` and scene
manifests. The historical maps were only read, and the source-run comparator still reports
`MISMATCHES 0`. After the report, checkers 1–8, the facade checker, the baseline verifier,
the smoke comparator and `git diff --check` were re-run.

**No gaze, controller, matcher, fusion, rendering or termination behaviour changed, and no
policy, score or candidate ranking was introduced.**

PARTITION_GRAPH8_TARGET_INTEGRATION_COMPLETE
