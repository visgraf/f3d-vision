# Partition-Graph Phase 8b — Budgeted Integrated Residual Challenge Suite

## Why Phase 8b exists

Phase 8 removed the dominant representation defect. Causal instance-keyed routing of measured target geometry removed 60.5% of historical prefix misses without another fixation, eliminated `TARGET_EVIDENCE_UNMAPPED`, and raised final 12 mm coverage from 87.47% to 95.42%.

The post-integration residual is still not a clean attention benchmark: 94.2% of residual state-misses belong to three targets; nine early states still contain truth-positive UNKNOWN regions larger than half the chart; and thousands of raw negative candidates are micro fragments.

Phase 8b is the bounded benchmark refinement before Phase 9. **It defines no score, ranking, or gaze policy.** It leaves the sealed baseline and the Phase-8 integration rule untouched.

Its question is:

> If we reduce historical acquisition budgets in a fixed truth-free way, so that every target contributes fewer looks to later cross-target memory, and simultaneously make candidate granularity explicit, does the integrated residual become broad and non-degenerate enough for a first graph-level attention experiment?

## 1. Five deterministic acquisition-budget scenarios

Run five retrospective scenarios over the saved accepted trajectory:

```text
budget_1   : each target contributes its first min(1, N) look
budget_2   : first min(2, N) looks
budget_4   : first min(4, N) looks
budget_8   : first min(8, N) looks
full       : all N historical looks
```

No image is re-rendered. A retained look is exactly the corresponding accepted patch/map prefix. Looks beyond the scenario budget are simply withheld from both that target's benchmark state and the persistent cross-target memory available to later targets.

This is a true **global budget replay** rather than merely selecting prefixes from the full-memory run: reducing an early target's budget also reduces what later targets can inherit from it.

The accepted object order and within-target historical gaze sequence are unchanged. The FULL scenario must reproduce Phase 8 exactly at all 25 target-final states.

## 2. Causal integrated representation in each scenario

For every target state in every scenario:

1. accumulate head-centred valid 3-D from only retained earlier/current patches;
2. build the historical mapped scene from each earlier target's retained-budget map and the current target's retained prefix map;
3. route all retained measured samples by inherited instance identity;
4. integrate current-target evidence exactly as in Phase 8;
5. build the unchanged epistemic partition.

`TARGET_EVIDENCE_UNMAPPED` must remain zero. Object identity is still inherited from Oracle-1.

## 3. Fixed UNKNOWN subdivision

The early giant-complement problem is addressed with a truth-free benchmark subdivision. `UNKNOWN` alone is split by distance from integrated target support in the existing 0.1° chart.

Shell width is **5°**, chosen before evaluation because it is the frozen FSG movement lattice:

```text
[0°,5°), [5°,10°), [10°,15°), ...
```

Within each shell, 4-connectivity defines regions. All non-UNKNOWN Phase-8b base regions are preserved exactly.

This is a benchmark view, not a physical scene label or attention preference.

## 4. Explicit micro-fragment parameter

All raw `UNKNOWN` and `OTHER_SURFACE` candidates remain represented. A separate benchmark eligibility flag is declared before evaluation:

```text
eligible_candidate := raw candidate AND cell_count >= 25
```

At 0.1° resolution this is 0.25 deg² of chart area. Raw and eligible results must both be reported; no fragment is silently deleted from the representation.

## 5. Memory-density strata

Each state is labelled from truth-free global head-depth coverage:

```text
0–25%, 25–50%, 50–75%, 75–100%
```

This separates sparse-memory scenarios from mature-memory scenarios without using evaluation truth.

## 6. Truth firewall

### Proposer

Allowed source reads:

- `manifest.json` and `bootstrap/seeds.json`;
- retained `patches/fix_XX.npz` files;
- retained `maps/fix_XX.npz` files;
- the audited Phase-5 state tree for target-specific `seen_any`;
- the audited Phase-8 truth-free proposal tree for FULL parity checks.

Forbidden:

- `evaluation_only/*`, `reachable_samples.npz`, `evaluation.json`;
- `oracle_observation.npz`, EXR, benchmark RGB, Blender;
- controller, matcher, fusion, renderer execution.

### Evaluator

The evaluator may open dense reachable truth and the same retained patches/maps. It reconstructs each scenario's causal integrated target geometry and measures only the post-integration residual. It writes to a separate tree and never modifies proposals.

## 7. Evaluation

For every scenario and all 25 targets report:

- integrated covered / residual reachable samples;
- raw and eligible candidate recall;
- truth-positive / truth-negative candidate counts;
- states with 0 / 1 / at least 2 positive candidates;
- states with a positive region larger than 50% of the chart;
- captured residual by positive-region area bins (`<=5%`, `(5,15]%`, `(15,50]%`, `>50%`);
- aggregate diversity by target and by memory-density stratum.

The FULL scenario must reproduce Phase 8 exactly:

```text
integrated covered  = 27,948
integrated residual = 1,340
```

The lower-budget scenarios are measurements, not pre-specified outcomes.

## 8. Interpretation boundary

Phase 8b decides whether the **integrated residual benchmark** is now broad enough to support Phase 9. It does not design Phase 9 itself.

If the lower-budget scenarios produce residuals spread across many targets and multiple eligible positive regions without giant complements dominating, Phase 9 may define the first graph-level attention experiment.

If the benchmark remains concentrated or degenerate, the next challenge setting must change information geometry more substantially: different starts/seeds or another scene, with the sealed golden baseline untouched.

## 9. Acceptance

Phase 8b passes only if:

- checkers 1–8 and 8b pass;
- facade checker and baseline verifier pass;
- accepted source and fresh smoke remain `MISMATCHES 0`;
- proposer is truth-free and deterministic;
- five scenarios × 25 targets = 125 benchmark states are emitted;
- FULL reproduces Phase 8 integrated partitions exactly for all 25 targets;
- integrated `TARGET_EVIDENCE_UNMAPPED` is zero in every scenario state;
- 5° shells and the 25-cell floor remain fixed;
- all chart cells are represented exactly once;
- raw and eligible metrics are both reported;
- FULL evaluation reproduces 27,948 / 1,340;
- evaluation does not modify the proposal tree;
- no gaze, controller, matcher, fusion, rendering, scene asset, score, ranking, or golden behavior changes.
