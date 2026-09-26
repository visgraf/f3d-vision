# Partition-Graph Phase 8 — Causal Target-Evidence Integration

## Why Phase 8 exists

Phase 7 produced the clearest architectural result so far. Causal cross-target 3-D memory largely solved the Phase-6 localization problem: the median largest truth-positive region fell from roughly half the chart to about one eighth, and giant positive complements became an early-prefix phenomenon. But the same experiment exposed a more fundamental issue: **51.9% of all state-misses landed in `TARGET_EVIDENCE_UNMAPPED`**. Evaluation-side analysis found that essentially all of those samples were already within the frozen 12 mm coverage radius of target geometry that had been measured causally.

That is not primarily an attention failure. It is an integration failure: the eye measured geometry belonging to the current target while some other object was active, but the historical architecture kept that geometry outside the target's persistent map.

Phase 8 therefore performs the architecture experiment recommended by Phase 7 **before** any gaze policy is designed.

Its scientific question is:

> **If target geometry that was already measured causally is routed into a shadow target-geometry layer regardless of which target was active when it was seen, how much of the historical residual disappears without another fixation, and does the remaining prefix benchmark become a clean, localized attention problem?**

Phase 8 still defines **no score, no ranking and no gaze policy**.

## 1. Shadow integration, not a rewrite of the sealed map

The accepted historical map remains byte-for-byte untouched.

For target `i`, at each historical prefix `g`, Phase 8 defines:

```text
shadow_target_geometry(i, g)
    = historical_map(i, g)
      UNION
      every valid target-i XYZ measured at source states <= g
```

The second term is **causal measured target evidence**. It comes from saved `patches/fix_XX.npz`, immediately downstream of the accepted local matcher. Provenance records whether each sample was measured during an own-target look or during an earlier different-target look. The cross-target subset is the architectural novelty exposed by Phase 7, but retaining all causal target measurements makes the routing rule uniform and also tests whether the historical surfel map itself discarded any usable measured geometry. None of this is dense evaluation truth.

The union is intentionally conservative:

- raw measured XYZ is retained with provenance;
- no new surfel averaging is defined;
- no RGB, support-count or provenance-mask semantics are invented;
- no old `SurfaceMap` is mutated;
- no matcher or fusion code is executed.

The point of the experiment is to test *routing of already measured geometry into object memory* before choosing a permanent fusion design.

## 2. Strict causal provenance

Phase 8 stores, per target:

```text
xyz_h
source_global_index
source_active_target_id
```

At prefix `g`, only samples with `source_global_index <= g` may participate. A future measurement is forbidden. `source_active_target_id` lets the report separate **cross-target** evidence from **own-target** evidence without changing the integration rule. Because targets are processed sequentially, all cross-target measurements available when a target begins necessarily come from earlier target runs.

Instance identity remains the inherited Oracle-1 identity and must be reported as such.

## 3. Historical-global parity first

Before target support is changed at each prefix, Phase 8 reconstructs the Phase-7 `global` partition from the same causal global head memory.

It must reproduce Phase 7 exactly at **all 104 states**:

- partition arrays;
- region table;
- edge table.

This isolates the experiment to one change: replacing historical target support by support of the shadow integrated target geometry.

## 4. Integrated spherical partition

The unchanged Phase-6 `build_epistemic_partition` is then called with:

- the same causal cross-target global head memory;
- the same mapped-object ownership;
- the same target-specific `seen_any`;
- the same target gaze history;
- **integrated target support** generated from the shadow target geometry using the frozen 12 mm association footprint.

Region precedence stays unchanged:

```text
TARGET_SUPPORT
    > AMBIGUOUS_BOUNDARY
    > OTHER_SURFACE
    > TARGET_EVIDENCE_UNMAPPED
    > UNKNOWN
```

For the accepted run, `TARGET_EVIDENCE_UNMAPPED` must become empty at every prefix. If it does not, the shadow-integration model is internally inconsistent and Phase 8 fails.

Only `UNKNOWN` and `OTHER_SURFACE` remain attention candidates. They are emitted without ranking.

## 5. Truth-free integration diagnostics

The proposer may compare causal measured target evidence, and its cross-target subset, against the historical target map using the frozen 12 mm geometry rule. That comparison is still truth-free because both sets are controller-time products.

For every prefix it records:

- historical map point count;
- all causal target-evidence point count, split into own-target and cross-target provenance;
- causal target evidence already represented within 12 mm;
- causal target evidence novel beyond 12 mm;
- the same novelty statistics for the cross-target subset;
- historical target-support cells;
- integrated target-support cells;
- added support cells;
- candidate-region structure before and after integration.

These are representation diagnostics, not attention scores.

## 6. Separate offline evaluator

The evaluator is the only Phase-8 stage allowed to open dense reachable truth.

For every prefix it computes both:

```text
historical coverage = within 12 mm of historical map
integrated coverage = within 12 mm of historical map UNION all causal measured target evidence
```

Therefore:

```text
integration gain = historically missed AND integrated covered
residual miss    = not integrated covered
```

The historical arm must reproduce Phase 7 exactly at all 104 states and reproduce the sealed final totals:

```text
reachable = 29,288
covered   = 25,618
missed    = 3,670
```

The integrated result is measured, not pre-specified.

## 7. Rebuild the prefix region benchmark on residual misses

The evaluator places only the **post-integration residual misses** into the truth-free integrated regions and reports:

- residual candidate recall;
- truth-positive and truth-negative candidate-region counts;
- states with 0 / 1 / at least 2 truth-positive candidates;
- positive-region area distribution:
  - `<= 5%` chart;
  - `(5%, 15%]`;
  - `(15%, 50%]`;
  - `> 50%`;
- residual misses in `TARGET_SUPPORT`;
- residual misses in `TARGET_EVIDENCE_UNMAPPED` (required to be zero);
- final integrated coverage and residual misses.

This is the benchmark that decides whether a later graph-level attention experiment is finally well-posed.

## 8. Historical-next-fixation reference after integration

For each nonterminal prefix, the evaluator also asks where the historical next gaze center falls in the integrated partition and how many residual truth samples become covered at the next historical prefix **after shadow integration is already credited**.

This separates two effects that Phase 7 mixed:

1. gain that another look really provided;
2. geometry that had already been measured earlier and only needed integration.

The old controller is still only a behavioral reference, not an optimal label.

## 9. Truth firewall

### Proposer allowed source-run reads

- `manifest.json`;
- `bootstrap/seeds.json`;
- 104 `patches/fix_XX.npz` files;
- 104 `maps/fix_XX.npz` files.

It may also read the audited Phase-5 and Phase-7 truth-free outputs.

Forbidden to proposer:

- `evaluation_only/*`;
- `reachable_samples.npz`;
- `evaluation.json`;
- `oracle_observation.npz`;
- EXR / benchmark RGB / Blender;
- controller, matcher, fusion or renderer execution.

### Evaluator

Dense truth is allowed only here and must never be copied into or used to modify the proposal tree.

## 10. Acceptance

Phase 8 passes only if:

- checkers 1–8 pass;
- facade checker and baseline verifier pass;
- accepted full source and a fresh smoke both remain `MISMATCHES 0`;
- proposer emits 104 states and 25 targets;
- Phase-7 global parity is exact at all 104 states;
- every cross-target evidence sample is strictly causal and comes from a different active target;
- integrated `TARGET_EVIDENCE_UNMAPPED` is zero at all 104 states;
- no dense truth path is opened by the proposer;
- evaluator reproduces Phase-7 historical prefix coverage/miss counts state by state;
- historical final totals remain exactly `29,288 / 25,618 / 3,670`;
- integrated coverage never loses a historically covered truth sample;
- evaluation does not modify the proposal tree;
- no controller, matcher, fusion, rendering, gaze, termination, golden signature or scene asset changes;
- no score, candidate ranking or new gaze policy is introduced.

The report must decide whether **the residual after integration** is finally a suitable graph-attention benchmark. If yes, Phase 9 may define the first graph-level attention experiment. If no, the report must identify the remaining representation/benchmark defect before any policy is introduced.
