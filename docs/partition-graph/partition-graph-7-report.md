# Partition-Graph Phase 7 — prefix benchmark and cross-target causal 3-D memory report (2026-09-25)

The contract is `docs/partition-graph-7.md`. This phase is benchmark and representation work
only. **No gaze policy, score, candidate ranking or controller behaviour was designed,
implemented, tuned or evaluated. No sealed engine file, golden signature, script or scene
asset changed.** Earlier reports are preserved unchanged.

Terms used throughout:

- **local arm**: the per-target Phase-5 head memory.
- **global arm**: causal cross-target head memory, accumulated from every completed patch up
  to the current state.
- **state-misses**: current-target misses summed over all 104 prefixes.
- **Evaluator-only quantities** (misses, positives, gains) characterize the benchmark. They
  are not controller features.

## Provenance

| | |
|---|---|
| starting point found | branch `architecture/partition-graph-6` at `8f2c57e` (Phase-6 report); **the handoff had not been applied**, and no `architecture/partition-graph-7` branch existed locally or on `origin` |
| action taken | ran `~/Downloads/PARTITION_GRAPH7_APPLY.sh` **unmodified**; all its guards passed (package sha256 `efd4675a…5e579` as expected, HEAD = expected parent `8f2c57e`, clean tree, no existing branch). It created the branch, committed and pushed |
| `43b2198` Add prefix cross-target memory benchmark | package commit made by the apply script (its own message); adds exactly `fov3d/experiments/classroom_partition/prefix_benchmark.py`, `tools/partition_graph7_{propose,evaluate,demo}.py`, `tools/dev/check_partition_graph7.py` and `docs/partition-graph-7.md`; all byte-identical to the zip; modifies no existing file |
| `34c18a8` Fix Phase-7 demo gain colour, footer and overview | presentation-only demo fix |
| this commit, Report Partition Graph Phase 7 | this report |

`git diff 8f2c57e..43b2198 --stat` shows 6 files and 1,249 insertions.
`PARTITION_GRAPH7_CODE_PROMPT.md` stays untracked in the repository root and is not
committed.

## Deviations and repairs

- **Handoff application.** See Provenance. The apply script was run exactly as supplied.
- **No mechanical repair and no package defect.** Proposer and evaluator ran unchanged, and
  every hard gate passed on the first run.
- **Demo presentation fix (`34c18a8`).** No measurement changed.
  - Next-prefix gains are by definition a subset of current misses (all 14,273 gain cells are
    miss cells), so the package's "both" colour painted every gain yellow. The keyed cyan
    never appeared: 0 pixels in 104 frames.
  - Gains are now cyan and the remaining misses red. **All 104 frames match the evaluator
    arrays with 0 pixel mismatches.**
  - Footers auto-fit instead of being clipped.
  - The overview shows the best frame per target (8 distinct targets) instead of 8
    consecutive states of two targets.
  - The package demo is kept at `previews/partition-graph-7-evaluation/demo-package-original/`.
- **Supplementary read-only analyses (untracked).** They are
  `previews/partition-graph-7-analysis.{py,json}` (distributions, from Phase-7 JSON only)
  and `previews/partition-graph-7-integration-check.{py,json}` (evaluation-side
  counterfactual, below). Neither writes into the proposal tree, which was re-hashed
  unchanged afterwards.

## Gates

```text
py_compile (5 Phase-7 files) -> OK
[partition-graph1-check] SUMMARY checked=13 failed=0
[partition-graph2-check] SUMMARY checked=16 failed=0
[partition-graph3-check] SUMMARY checked=20 failed=0
[partition-graph4-check] SUMMARY checked=14 failed=0
[partition-graph5-check] SUMMARY checked=12 failed=0
[partition-graph6-check] SUMMARY checked=12 failed=0
[partition-graph7-check] SUMMARY checked=12 failed=0
[consolidation3-facade-check] SUMMARY checked=16 failed=0
[verify] compiled 85 tracked .py files in memory, errors=0
[verify] 31 files tracked at baseline-classroom-oracle1-2026-09-25 are byte-identical in the working tree
[verify] SUMMARY passed=9 failed=0
compare_golden.sh previews/partition-graph-2-source-full   -> [compare-golden] MISMATCHES 0
compare_golden.sh --smoke previews/partition-graph-7-golden-smoke -> [compare-golden] MISMATCHES 0  (5 looks, 68 NPZ arrays, 4 targets)
git diff --check -> clean
```

**Phase-5/6 inputs**, verified present and unchanged:

- `partition-graph-5-full`: 104 states, `head_target_depth_true_gap_violations` 0.
- `partition-graph-6-proposals`: `truth_used: false`, 25 targets, 1,672 candidates; its tree
  still matches the Phase-6 hash `30e88f61…`.
- `partition-graph-6-evaluation`: **reachable 29,288, covered 25,618, missed 3,670**; 3,525
  captured, 30 positive regions.

## Truth-free proposer

```text
[partition-graph7-propose] COMPLETE {"global_candidates": 17202, "local_candidates": 8557, "phase6_final_local_parity": 25, "states": 104, "targets": 25, "truth_used": false}
```

- **Hard requirements, all met.** 104 states, 25 targets, `truth_used: false`,
  `phase6_final_local_parity` = **25**, `local_memory_subset_checks` = **104**,
  `global_head_depth_monotonic: true`, `forbidden_read_paths: []`.
- **Declared source reads.** `manifest.json` 1, `bootstrap/seeds.json` 1 and the 104
  `patches/fix_XX.npz`.
- **OS-level trace.** The proposer was traced with `strace -f -e openat,open,execve`, writing
  a separate output `previews/partition-graph-7-proposals-strace` and the log
  `previews/partition-graph-7-propose.strace`.
  - Source-run opens are exactly `manifest.json`, `bootstrap/seeds.json` and the 104 patches.
  - Other reads are only the Phase-5 states (105 files) and the Phase-6 proposal tree
    (76 files).
  - **0** opens of `evaluation_only`, `reachable_samples.npz`, `evaluation.json`,
    `oracle_observation.npz`, EXR, benchmark RGB or Blender.
  - One `execve` (the venv Python). Only `fov3d` modules were loaded: no sealed engine, no
    controller, matcher, fusion, renderer or `bpy`.
- **Determinism.** The traced rerun's 835 files are content-identical to the official
  proposal (all JSON equal, all NPZ arrays equal). The official proposal was not overwritten.

## Proposal-tree immutability

```text
835 files hashed, deterministic manifest (sort -z | sha256sum)
sha256(previews/partition-graph-7-proposals.before.sha256) = 5aa71f39a5caa2cd97fca0a1e9bdf6dfe9c85b9ec2bed2121930e96479564530
sha256(previews/partition-graph-7-proposals.after.sha256)  = 5aa71f39a5caa2cd97fca0a1e9bdf6dfe9c85b9ec2bed2121930e96479564530
diff -u before after -> empty
```

The traced evaluation shows **0** write-mode opens under the proposal tree. The tree was
re-verified unchanged after the supplementary analyses and after both demo generations.

## Offline truth evaluator

```text
[partition-graph7-evaluate] COMPLETE {"final": {"covered": 25618, "missed": 3670, "reachable": 29288}, "global_2plus_positive_states": 68, "global_recall": 0.4347697988686361, "local_2plus_positive_states": 63, "local_recall": 0.9713230672532999, "states": 104}
```

- **Exact Phase-6 final parity.** Final-prefix totals are 29,288 / 25,618 / 3,670, equal to
  expected. Local final candidate capture is **3,525 = 3,525**, and local final
  truth-positive candidate regions **30 = 30**.
- **Reads.** The evaluator (traced) read `manifest.json`, `seeds.json`,
  `evaluation_only/reachable_samples.npz` and the 104 prefix maps. It opened no EXR, oracle
  observation or Blender file.

## Results

### Prefix benchmark size

| | local | global |
|---|---|---|
| states | 104 | 104 |
| state-misses (all prefixes) | 101,824 | 101,824 |
| states with any miss | 92 | 92 |
| candidate regions | 8,557 (UNKNOWN 1,574, OTHER_SURFACE 6,983) | **17,202** (UNKNOWN 1,320, OTHER_SURFACE 15,882) |
| truth-positive candidate regions | 490 (5.7 % of candidates) | 535 (**3.1 %**) |
| states with 0 / 1 / ≥ 2 positive candidates | 14 / 27 / 63 | 16 / 20 / 68 |
| negative candidate regions ≤ 10 cells | 3,538 | **9,905** |

### Localization (captured state-misses by the chart area of their positive region)

| region area | local: cells | local: share of all state-misses | global: cells | global: share of all state-misses |
|---|---|---|---|---|
| ≤ 5 % | 18,271 | 17.9 % | 6,429 | 6.3 % |
| (5 %, 15 %] | 8,359 | 8.2 % | 22,448 | 22.0 % |
| (15 %, 50 %] | 46,198 | 45.4 % | 3,790 | 3.7 % |
| > 50 % | 26,076 | 25.6 % | 11,603 | 11.4 % |
| not in a candidate | 2,920 (TARGET_SUPPORT) | 2.9 % | **52,838 TARGET_EVIDENCE_UNMAPPED**, 1,796 AMBIGUOUS, 2,920 TARGET_SUPPORT | **51.9 %** + 1.8 % + 2.9 % |
| **candidate recall** | **0.9713** | | **0.4348** | |

Largest positive-region chart fraction by state (states with at least one positive):

| | min | P25 | median | P75 | max | states | states > 50 % | states ≤ 15 % |
|---|---|---|---|---|---|---|---|---|
| local | 0.016 | 0.245 | **0.480** | 0.705 | 0.932 | 90 | 43 | 15 |
| global | 0.0006 | 0.096 | **0.120** | 0.163 | 0.884 | 88 | **9** | **62** |

### Cross-target causal memory

- **Memory growth.** Global head-depth cells cover 4.4 % of the chart at state 0, then
  35.5 % at state 10, 47.3 % at 25, 75.1 % at 50, 81.3 % at 75 and **90.1 % at state 103**.
  Local memory covers a median of 13.4 % of the chart (max 44.9 %). Global/local depth-cell
  ratio: median 4.5×, P75 7.8×, max 32.7×.
- **Local → global miss transitions (state-misses):**

  | transition | count |
  |---|---|
  | UNKNOWN → **TARGET_EVIDENCE_UNMAPPED** | **52,838** |
  | UNKNOWN → UNKNOWN | 39,368 |
  | OTHER_SURFACE → OTHER_SURFACE | 4,775 |
  | TARGET_SUPPORT → TARGET_SUPPORT | 2,920 |
  | UNKNOWN → AMBIGUOUS_BOUNDARY | 1,218 |
  | OTHER_SURFACE → AMBIGUOUS_BOUNDARY | 578 |
  | UNKNOWN → OTHER_SURFACE | **127** |

- **Size of each miss's containing region**, global versus local: **smaller for 97,790**,
  equal for 3,313, larger for 721. The per-state median area change is −0.17 of the chart
  (P25 −0.46).
- **Giant (> 50 %) positive UNKNOWN regions.** 43 in the local arm, holding 26,076 misses,
  reached as late as state 54. In the global arm there are **9**, holding 11,603 misses, and
  **all fall in the first 14 prefixes** (alphabet at state 2, blackBoard at states 6–13),
  when little cross-target memory exists. No giant positive region remains after state 13.
- **Genuinely unobserved residual (global UNKNOWN misses, 39,368; 38.7 %).** By region
  area: ≤ 5 % 5.2 %, (5 %, 15 %] **55.7 %**, (15 %, 50 %] 9.6 %, > 50 % 29.5 % (the early
  prefixes above).
- **Misses in TARGET_EVIDENCE_UNMAPPED.**

  | scope | misses in class | share |
  |---|---|---|
  | all prefixes | **52,838** | 51.9 % |
  | 25 final states | 1,799 of 3,670 | 49.0 % |
  | wall.008, all prefixes | 28,268 of 33,812 | 84 % |
  | woodBase, all prefixes | 18,065 of 36,812 | 49 % |
  | woodBaseboard, final | 506 of 634 | 80 % |
  | lettersPlank, final | 336 of 382 | 88 % |
  | ceilingMoulding, final | 264 of 306 | 86 % |
  | boardFrame, final | 231 of 342 | 68 % |
  | sol, all 6 prefixes | **0** | 0 % |

  These are measurement or integration opportunities, not attention candidates, per the
  contract.

**Evaluation-side integration counterfactual (supplementary, not a policy).** At each prefix,
for each current miss: does a valid patch sample of the current target exist from any look
at global states 0..g (causal) within the sealed 12 mm?

| miss class (global arm) | within 12 mm of a causally measured target sample |
|---|---|
| TARGET_EVIDENCE_UNMAPPED | **52,749 / 52,838 (99.8 %)** |
| OTHER_SURFACE | 4,828 / 4,902 (98.5 %) |
| AMBIGUOUS_BOUNDARY | 1,789 / 1,796 (99.6 %) |
| TARGET_SUPPORT | 1,570 / 2,920 (54 %) |
| UNKNOWN | **621 / 39,368 (1.6 %)** |
| **all state-misses** | **61,557 / 101,824 (60.5 %)** |
| 25 final states | 2,330 / 3,670 (63.5 %) |

At the final states, integrating already-measured target geometry would take the 12 mm
coverage from 25,618 to about **27,948 of 29,288 (95.4 %) without a single new look**. This
is an upper bound; it assumes the integrated samples are fused as measured.

### Historical-next reference (79 nonterminal prefixes; descriptive only)

The historical controller is not treated as optimal.

| | local | global |
|---|---|---|
| next-gaze centre on a candidate region | 47 (UNKNOWN 29, OTHER_SURFACE 18) | 33 (UNKNOWN 12, OTHER_SURFACE 21) |
| centre in a currently truth-positive region | 62 (of which TARGET_SUPPORT 29) | 57 (TARGET_SUPPORT 29, **TARGET_EVIDENCE_UNMAPPED 12**, UNKNOWN 9, OTHER_SURFACE 6, AMBIGUOUS 1) |
| centre in a region containing next-prefix gains | 56 | 50 (TARGET_EVIDENCE_UNMAPPED 12) |

In **12 of 79** steps the historical next fixation was centred in territory where the target
had already been measured by earlier looks, and its gain landed there: re-observation of
geometry that was measured but never integrated.

### Benchmark-readiness conclusion

> Does prefix-level sampling plus causal cross-target memory create a sufficiently
> localized and non-degenerate region-selection benchmark to justify a later graph-attention
> experiment?

**Not yet**, but for a different reason than in Phase 6.

1. **The localization problem is largely solved.** Cross-target memory moves 96 % of state-
   misses into smaller regions. It removes the giant-complement degeneracy from 90 of 104
   prefixes (giant positive regions: 43 → 9, all early). The median largest positive region
   per state falls from 48 % to 12 % of the chart, and the genuinely unobserved residual is
   mostly in 5–15 % regions. Prefix sampling gives 68 states with at least 2 positive
   candidates.
2. **The dominant residual is not a looking problem.** 52 % of state-misses lie in
   TARGET_EVIDENCE_UNMAPPED, and 60.5 % of all state-misses are within 12 mm of target
   geometry the system had already measured. That includes 98.5 % of the OTHER_SURFACE and
   99.6 % of the AMBIGUOUS misses. A region-selection experiment on this benchmark would
   score attention on misses that attention cannot, and need not, fix.
3. **The global candidate set is noisy.** 17,202 candidates, of which 9,905 are negative
   fragments of at most 10 cells, and only 3.1 % are positive.

### Recommendation (next benchmark operation; no policy)

1. **Direct integration of measured target evidence deserves its own architecture
   experiment, and it should come first.** Integrate each target's causally measured
   geometry from other targets' looks (TARGET_EVIDENCE_UNMAPPED and the integrable
   OTHER_SURFACE, AMBIGUOUS and support cases) into its map at each prefix, truth-free.
   Evaluate the coverage gain offline; the counterfactual upper bound is 87.5 % → 95.4 %
   final coverage with no new fixations.
2. **Then rebuild this prefix benchmark on the integrated representation.** Its residual is
   essentially the genuinely unobserved UNKNOWN territory: about 39 k state-misses and about
   1,340 final misses, already localized under global memory in 90 of 104 prefixes.
3. **Choosing between the contract's two options.**
   - A fixed truth-free subdivision of residual UNKNOWN is needed only for the early-prefix
     giant complements (states 2–13, 11,603 state-misses). Adopt it there as an explicit,
     declared benchmark parameter, or stratify those prefixes. Declare a minimum-fragment
     parameter for the tiny negative OTHER_SURFACE fragments in the same way.
   - A separate scene, seed or budget challenge is not yet indicated. Reconsider it only if
     the post-integration residual proves too small or too uniform.

## Demo inspection

`previews/partition-graph-7-evaluation/demo/`:

- 104 frames, 1252 × 1120;
- `partition-graph-7-demo.mp4` (mpeg4, 104 frames at 4 fps; decodes through all 104 frames);
- `overview.png` (1252 × 2240, 8 distinct targets);
- `Demo.md`.

Confirmed on the fixed demo:

- **Orientation:** positive pitch is up (floor and chairs at the bottom).
- **Arms visually distinct:** the global partition shows orange TARGET_EVIDENCE_UNMAPPED
  regions and the split complement, while the local arm shows one large tinted UNKNOWN
  region. At sol's final state (frame 44), local puts 1,036 misses in a > 50 % region and
  global puts 0.
- **Truth panel:** labelled **EVALUATION ONLY**. Red = current misses not gained next;
  cyan = misses newly covered at the next historical prefix. The 87,551 red and 14,273 cyan
  cells match `truth-evaluation.npz` exactly (0 pixel mismatches) and sum to the 101,824
  state-misses.
- **No policy shown:** no panel presents a score, ranking or policy; the text panel states
  so.
- **Overview:** 8 distinct targets. It covers the woodBase and wall.008 TARGET_EVIDENCE_UNMAPPED
  cases, blackBoard at state 6 (the early giant complement that persists), and the sol,
  lettersPlank, woodBaseboard, boardFrame and worldMap localization differences.

## Immutability and behaviour

Relative to `8f2c57e` the changes are the package commit (6 new files), the demo
presentation fix and this report. Every file tracked at `6c8a80f` is untouched, including
the sealed `tools/*` engine, `fov3d` facade wrappers, `tests/golden/`, `scripts/` and scene
manifests. The Phase-5 and Phase-6 artifacts were read, not regenerated. After the report,
checkers 1–7, the facade checker, the baseline verifier, the smoke comparator and
`git diff --check` were re-run.

**No gaze, controller, matcher, fusion, rendering or termination behaviour changed, and no
policy, score or candidate ranking was introduced.**

PARTITION_GRAPH7_PREFIX_MEMORY_BENCHMARK_COMPLETE
