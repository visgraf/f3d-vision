# Partition-Graph Phase 7 — Prefix Benchmark and Cross-Target Causal 3-D Memory

## Why Phase 7 exists

Phase 6 moved from pairwise gaps to whole-field epistemic regions and recovered 3,525 of the 3,670 final misses inside truth-free candidate regions. That 96.05% recall was not a useful selection result, because the candidates covered 96% of the chart and 56.6% of captured misses sat in giant `UNKNOWN` complements larger than half the chart. Only 30 of 1,672 causal-final candidates were truth-positive.

The Phase-6 report recommended two changes *before* introducing an artificial subdivision or a new scene:

1. evaluate every historical prefix, not only the 25 target-final states;
2. accumulate controller-time head-centred 3-D across targets, rather than resetting incidental memory for each target.

Phase 7 implements exactly those two changes. **It still defines no attention score, candidate ranking or gaze policy.**

Its scientific question is:

> **Across all 104 historical decision prefixes, does causal cross-target 3-D memory split the giant complement into substantially more localized truth-free regions, and does that create a non-degenerate benchmark for future region selection?**

## 1. Two truth-free proposal arms

At every global fixation `g`, Phase 7 builds two partitions over the **same** current target map, same joint mapped-object ownership, same target-specific historical `seen_any`, and same 0.1° head-centred chart.

### `local`

The existing Phase-5 head memory for the current target only. This is the Phase-6 representation generalized from 25 final states to all 104 prefixes.

### `global`

One causal head-centred memory accumulated from **every completed saved patch from every target up to and including `g`**.

The global memory contains only local measurements already made by the historical eye:

- valid `xyz_h`;
- inherited instance id;
- nearest measured range per chart cell;
- whether multiple instance identities occupied one chart cell;
- sample count.

No future patch is opened. No evaluation truth is opened.

The global memory does **not** change the persistent target map. This phase measures what a richer architecture could have retained; it does not retroactively fuse incidental samples.

## 2. Region semantics stay unchanged

Both arms call the existing Phase-6 `build_epistemic_partition` unchanged. Precedence remains:

```text
TARGET_SUPPORT
    > AMBIGUOUS_BOUNDARY
    > OTHER_SURFACE (mapped or measured incidental)
    > TARGET_EVIDENCE_UNMAPPED
    > UNKNOWN
```

Only `UNKNOWN` and `OTHER_SURFACE` are attention candidates, exactly as in Phase 6.

`TARGET_EVIDENCE_UNMAPPED` is deliberately **not** an attention candidate. It means the architecture already measured the current target at that direction but the current target map does not contain it. That is a memory/integration issue, not automatically a reason for another gaze.

## 3. Prefix causality

The accepted Oracle-1 run processes targets sequentially. Phase 7 traverses the saved trajectory in exactly that order.

At state `g`:

- the current target map is `maps/fix_k.npz` at the current local fixation `k`;
- mapped-object ownership is the already audited causal joint state from Phase 5;
- local memory is the current target's Phase-5 memory;
- global memory contains patches from global states `0..g`, and nothing later;
- only the current target's gazes up to `k` are passed to the unchanged Phase-6 region descriptor, preserving exact final-state parity with Phase 6.

Hard proposer invariants:

1. exactly 104 states are emitted;
2. local head-depth cells are a subset of global head-depth cells at every state;
3. global head-depth support is monotonic over global time;
4. at each of the 25 target-final states, the **local** Phase-7 partition arrays, region table and edge table are byte/content-identical to the Phase-6 proposal for that target;
5. no dense/evaluation truth path is opened.

## 4. Two-stage truth firewall

### Proposer

Allowed source-run reads:

- `manifest.json`;
- `bootstrap/seeds.json`;
- `patches/fix_XX.npz` for the 104 completed looks.

It may also read the already audited Phase-5 state files and Phase-6 truth-free proposal tree.

Forbidden:

- `evaluation_only/*`;
- `reachable_samples.npz`;
- `evaluation.json`;
- `oracle_observation.npz`;
- EXR / benchmark RGB / Blender;
- any controller, matcher, fusion or renderer execution.

### Evaluator

The evaluator is separate. It may open dense truth and the current target map at each prefix.

For current target `i` and local fixation `k` it defines current misses exactly as the sealed evaluator does:

```text
reachable target truth sample is missed
iff it is farther than 12 mm from every surfel in maps/fix_k.npz
```

At the 25 target-final prefixes, the totals must reproduce Phase 6 exactly:

```text
reachable 29,288
covered   25,618
missed     3,670
```

The local-arm final candidate capture and truth-positive candidate-region count must also reproduce the Phase-6 evaluator exactly.

## 5. What the evaluator measures

For each of the 104 prefixes and for both arms it reports:

- current reachable / covered / missed target samples;
- missed samples by region kind;
- attention-candidate recall;
- truth-positive and truth-negative candidate-region counts;
- size of every positive region as a fraction of the chart;
- missed samples captured in disjoint region-size bins:
  - `<=5%` of chart;
  - `(5%,15%]`;
  - `(15%,50%]`;
  - `>50%`;
- missed samples landing in `TARGET_EVIDENCE_UNMAPPED` (memory/integration opportunity rather than gaze candidate);
- missed samples still inside `TARGET_SUPPORT`.

No one of these quantities becomes a controller score.

## 6. Cross-target-memory ablation

Because `local` and `global` share the same target map and mapped-object state, their difference isolates cross-target causal memory.

For each currently missed truth sample, the evaluator records the local-to-global region-kind transition, for example:

```text
UNKNOWN -> OTHER_SURFACE
UNKNOWN -> TARGET_EVIDENCE_UNMAPPED
UNKNOWN -> UNKNOWN
```

It also compares the chart area of the containing region. Per state it reports how many misses move to a smaller, equal, or larger region and the median change in containing-region area.

The central descriptive questions are:

- Does global memory reduce misses assigned to giant `UNKNOWN` regions?
- Does it increase the number of localized positive regions without simply exploding negative fragments?
- Does it expose already-measured target geometry (`TARGET_EVIDENCE_UNMAPPED`) that should be integrated rather than re-observed?
- How many states have 0, 1, or at least 2 truth-positive candidates?

## 7. Historical-next-fixation reference

For nonterminal prefixes only, Phase 7 records the **historical next gaze center** as a reference. It asks:

- which current region contains that gaze center;
- whether that region is a candidate;
- whether that region contains any current miss;
- whether it contains any truth sample newly covered by the next historical prefix.

This is descriptive. The historical controller is not treated as ground-truth optimal behavior, and its next gaze is never used to build or rank Phase-7 regions.

## 8. No fixed UNKNOWN subdivision yet

Phase 6 proposed fixed geodesic/tile subdivision only if prefix-level analysis and cross-target memory fail to make the benchmark useful.

Phase 7 therefore **does not** subdivide `UNKNOWN` artificially. Keeping this mechanism out preserves a clean causal ablation:

```text
Phase-6/7 local memory  ->  Phase-7 global cross-target memory
```

If giant positive complements remain dominant after this test, a later phase may add a fixed truth-free subdivision as an explicit benchmark parameter, or move to a new scene/seed/budget challenge.

## 9. Acceptance

Phase 7 passes only if:

- checkers 1–7 pass;
- facade checker and baseline verifier pass;
- golden smoke remains `MISMATCHES 0`;
- the accepted full source remains `MISMATCHES 0`;
- proposer emits 104 states and uses no truth;
- local-memory depth is a subset of global memory at all 104 states;
- global head-depth support is monotonic;
- the 25 local final states reproduce Phase-6 proposals exactly;
- evaluator reproduces the Phase-6 final totals and local final proposal metrics exactly;
- evaluation does not modify the proposal tree;
- no controller, matcher, fusion, gaze, termination, golden signature or scene asset changes;
- no score, ranking or new gaze policy is introduced.

The report must decide only whether this **benchmark representation** is rich enough to justify a later attention experiment. If not, it must recommend the next benchmark refinement rather than manufacture a policy result.
