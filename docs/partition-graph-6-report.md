# Partition-Graph Phase 6 — causal epistemic regions and truth-only benchmark report (2026-09-25)

The contract is `docs/partition-graph-6.md`. This phase is benchmark construction only. **No
gaze policy was designed, implemented, tuned or evaluated, and no controller, matcher,
fusion, renderer, termination, golden signature, script or scene asset changed.** Earlier
reports are preserved unchanged.

Terms used throughout:

- **proposer**: the truth-free stage. It sees only controller-time products.
- **evaluator**: the offline stage. It is the only stage that opens dense truth.
- **"causal-final"**: a target's last historical fixation.
- **Evaluator-only quantities** (truth-positive, recall, missed samples) characterize the
  benchmark. They are not features a controller could know.

## Provenance

| | |
|---|---|
| branch | `architecture/partition-graph-6`, tracking `origin/architecture/partition-graph-6` |
| parent | `11d61f8ae60597adf4517605864d30c51223903c` (Phase-5 report), as the apply script required |
| `0b8b075` Add causal epistemic-region benchmark | package commit; adds `fov3d/experiments/classroom_partition/benchmark.py`, `tools/partition_graph6_{propose,evaluate,demo}.py`, `tools/dev/check_partition_graph6.py` and `docs/partition-graph-6.md`; modifies no existing file; byte-identical to `~/Downloads/partition-graph-6.zip` (sha256 `13b2700d…c64c6a`; the apply script deleted the zip's `README_PACKAGE.txt` as intended) |
| `7ded59b` Fix Phase-6 demo region and truth panels | presentation-only demo fix (see Deviations) |
| this commit, Report Partition Graph Phase 6 | this report |

Reused artifacts, all present and not regenerated:

- `previews/partition-graph-2-source-full` (accepted full run);
- `previews/partition-graph-4-lift`;
- `previews/partition-graph-5-full`.

`PARTITION_GRAPH5_CODE_PROMPT.md` stays untracked in the repository root, as the apply
script intends.

## Deviations

- **No mechanical repair.** Proposer and evaluator ran unchanged.
- **No package defect changed a reported quantity.** One latent weakness was checked and
  found not to apply on this run:
  - `_miss_components` maps each 0.25° lattice key to a single sample, so duplicate keys
    would create spurious singleton components.
  - On this run all 29,288 truth samples lie exactly on the 0.25° lattice with unique keys.
  - Recomputing the components from independently recomputed misses gives the same 103.
- **Demo presentation fix (`7ded59b`).** Nothing was measured differently.
  - *Region panel.* All `UNKNOWN` regions shared one colour, so a localized `UNKNOWN`
    region was indistinguishable from the target's giant complement. `OTHER_SURFACE` used
    arbitrary instance colours, and the mapped blackBoard rendered green, the colour panel 1
    reserves for `TARGET_EVIDENCE_UNMAPPED`.
  - *Truth panel.* It painted **all** reachable target truth red, covered and missed alike.
  - *Now:* each `UNKNOWN` region has its own tint, region edges are drawn, and surfaces are
    gray-blue. Missed samples are red and covered ones cyan; coverage is recomputed with the
    evaluator's own `_covered` and asserted equal to the evaluator's per-target missed counts.
  - The package demo is kept at `previews/partition-graph-6-evaluation/demo-package-original/`.
- **Supplementary analyses (untracked, evaluation-side).** They live in
  `previews/partition-graph-6-audit/`: `analyze_pg6.py`, `ablate_incidental.py`, their
  JSON, the `strace` logs and the proposal-tree hash manifests. They write only there, and
  the proposal tree was re-hashed after each.

## Gates (exact output)

```text
[partition-graph1-check] SUMMARY checked=13 failed=0
[partition-graph2-check] SUMMARY checked=16 failed=0
[partition-graph3-check] SUMMARY checked=20 failed=0
[partition-graph4-check] SUMMARY checked=14 failed=0
[partition-graph5-check] SUMMARY checked=12 failed=0
[partition-graph6-check] SUMMARY checked=12 failed=0
[consolidation3-facade-check] SUMMARY checked=16 failed=0
[verify] compiled 80 tracked .py files in memory, errors=0
[verify] 31 files tracked at baseline-classroom-oracle1-2026-09-25 are byte-identical in the working tree
[verify] SUMMARY passed=9 failed=0
compare_golden.sh previews/partition-graph-2-source-full   -> [compare-golden] MISMATCHES 0   (reachable 29288, covered 25618, 25 targets, 104 fixations)
run_golden.sh --smoke previews/partition-graph-6-golden-smoke
compare_golden.sh --smoke previews/partition-graph-6-golden-smoke -> [compare-golden] MISMATCHES 0
git diff --check -> clean
[partition-graph6-propose] COMPLETE {"candidate_kinds": {"OTHER_SURFACE": 1384, "UNKNOWN": 288}, "candidate_regions": 1672, "targets": 25, "truth_used": false}
[partition-graph6-evaluate] COMPLETE {"candidate_recall": 0.9604904632152589, "covered": 25618, "miss_components": 103, "missed": 3670, "reachable": 29288, "truth_positive_candidate_regions": 30}
```

The hard acceptance totals are reproduced exactly: **reachable 29,288, covered 25,618,
missed 3,670.** An independent recomputation in the supplementary analysis gives the same
three numbers and the same per-target captured, missed and by-class counts.

## Proposer truth-isolation proof

The proposer ran under `strace -f -e openat,open,execve`.

- **Source run:** only `manifest.json` and `bootstrap/seeds.json`.
- **Other inputs:** `partition-graph-4-lift/summary.json`, `partition-graph-5-full/summary.json`,
  and the 25 causal-final `partition-graph-5-full/states/global_XXX/head-evidence.npz`.
  Those are controller-time products, audited truth-free in Phase 5.
- **Forbidden opens: 0** — no `evaluation_only`, `reachable_samples.npz`,
  `evaluation.json`, `oracle_observation.npz`, EXR, benchmark RGB or Blender file anywhere.
- **Processes and modules:** one `execve` (the venv Python). It loaded only `fov3d` scene
  and partition modules — no sealed `tools/*` engine module, and no controller, matcher,
  fusion, renderer or `bpy`.
- **Summary:** `truth_used: false`, `controller_executed: false`,
  `gaze_policy_defined: false`, `object_identity_inherited: true`, `target_count: 25`,
  `forbidden_read_paths: []`.

The evaluator (traced too) read `manifest.json`, `seeds.json`,
`bootstrap/evaluation_only/reachable_samples.npz` and the 25 `final_map.npz` files, and no
EXR, oracle observation or Blender file. Its missed samples are placed with the truth's own
`yaw_pitch_deg`. These equal the head-origin angles recomputed from `xyz_h` to within
2 × 10⁻⁵°, the partition chart's convention.

## Proposal-tree immutability proof

The proposal tree `previews/partition-graph-6-proposals` has 102 files. Its sha256 manifest
hashes to **`30e88f61da7ef1d43bc9bb530418f2d03c1403347b26f22a0d9a1c211309bbad`**:

- before evaluation;
- after evaluation (byte-identical, and the evaluator's trace shows **0** write-mode opens
  under the proposal tree);
- after the supplementary analyses;
- after both demo generations.

## Results

### Q1. Causal candidate regions

There are **1,672 candidate regions** over 25 targets (27–157 per target, median 64). The
candidate regions cover **4,824,959 of 5,022,525 chart cells (96.1 %)** — everything except
target support and ambiguous boundaries.

| | UNKNOWN | OTHER_SURFACE |
|---|---|---|
| regions | 288 | 1,384 (mapped 910, incidental 455, mixed 19) |
| reconstruction status | — | mapped_now 929, targeted_later 455, **never_targeted 0** |
| touching domain edge / interior | 69 / 219 | 201 / 1,183 |
| adjacent to target support / not | 44 / 244 | 174 / 1,210 |
| cells: median / P90 / max | 3 / 7,807 / **196,883 (98 % of chart)** | 21 / 2,118 / 29,928 |
| single-cell regions / ≤ 10 cells | 104 / 186 | 177 / 505 |

Each target's largest `UNKNOWN` region is its unexplored complement. For 22 of the 25
targets it covers **37–98 % of the chart**; for woodBase, woodBaseboard and worldMap it
covers 7–9 %.

### Q2. Where the 3,670 missed target samples fall

| class | missed samples | share |
|---|---|---|
| UNKNOWN | 3,198 | 87.1 % |
| OTHER_SURFACE | 327 | 8.9 % |
| TARGET_SUPPORT | 145 | 4.0 % |
| AMBIGUOUS_BOUNDARY | 0 | 0 |
| TARGET_EVIDENCE_UNMAPPED | 0 | 0 |
| outside the chart | 0 | 0 |

The 145 support misses lie inside the target's own angular support but beyond 12 mm of any
surfel, so no region candidate can reach them by construction. They come from coat 1 (all
50 of its misses), wall.008 (54), sol (7), wall (all 7) and a few others.

### Q3. Candidate recall

**Micro recall (UNKNOWN + OTHER_SURFACE) = 3,525 / 3,670 = 0.9605.** Per target:

| recall | targets |
|---|---|
| **1.0** | alphabet 55/55, verticalPipe 17/17 |
| 0.99+ | plank 0.996, lettersPlank 0.995, sol 0.993, woodBaseboard 0.992 |
| 0.93–0.99 | boardFrame 0.988, ceilingMoulding 0.984, blackBoardLamp 0.967, blackBoard_upPart 0.947, blackboardLamp 0.935 |
| < 0.9 | wall.008 0.866, woodBase 0.333 (1/3) |
| **0.0** | coat 1 (0/50), wall (0/7) |
| no misses | the other 10 targets |

Because candidates cover 96 % of the chart, a high recall mainly restates area coverage. It
is not evidence of localization.

### Q4. Truth-positive candidate regions

**30 of 1,672 candidate regions (1.8 %) contain any missed target sample** (13 UNKNOWN, 17
OTHER_SURFACE), across 13 targets (1–6 per target; woodBaseboard 6, wall.008 4). A few giant
regions dominate:

- the top region, sol's complement, holds **29.4 %** of captured misses;
- the top 5 hold 66.1 %;
- 11 regions hold 90 %.

Captured misses by the chart area of the region containing them:

| region size (fraction of chart) | captured misses | share of 3,525 |
|---|---|---|
| > 50 % | **1,996** (all UNKNOWN complements) | 56.6 % |
| 15–50 % | 308 (wall.008's complement, 37 %) | 8.7 % |
| 5–15 % | 736 (UNKNOWN 564, OTHER_SURFACE 172) | 20.9 % |
| ≤ 5 % | 485 (UNKNOWN 330, OTHER_SURFACE 155) | 13.8 % |

Misses are therefore mostly **not** localized. About two thirds sit in each target's giant
complement. The genuinely localized third comes from three sources:

- lettersPlank's 377 misses in a 5.5 %-of-chart UNKNOWN region;
- woodBaseboard's 517 misses in two UNKNOWN regions of 3.9 % and 7.4 %;
- 327 misses in 17 mapped OTHER_SURFACE regions.

### Q5. Truth-positive OTHER_SURFACE regions

| | count |
|---|---|
| regions | 17 |
| missed samples | 327 |
| surface source | **all mapped** (0 incidental, 0 mixed) |
| status of the intervening instance | **all mapped_now** (0 targeted_later, 0 never_targeted) |
| touching domain edge | 8 of 17 |
| adjacent to target support | 9 of 17 |

| target ← mapped surface | missed | region cells |
|---|---|---|
| boardFrame ← blackBoard | 94 | 28,834 |
| woodBaseboard ← woodBase | 57 and 21 | 19,600 and 13,880 |
| blackBoard_upPart ← blackBoardLamp | 22 | 1,384 |
| woodBaseboard ← sol | 22 and 12 | 1,776 and 8,751 |
| wall.008 ← wall | 21 | 6,475 |
| blackboardLamp ← blackBoardLamp | 20 | 1,610 |
| ceilingMoulding ← ceiling | 19 | 288 |
| wall.008 ← plank | 15 | 1,220 |
| other 7 regions | 1–6 each | |

Incidental 3-D (Phase 5's gain) produces **no** truth-positive surface region.

### Q6. Truth-positive UNKNOWN regions

All 13 touch the domain edge, and 12 are adjacent to target support (minimum distance
0.1°). All have head-depth fraction 0 by definition and historical `seen_any` fractions of
0.3–8.4 %. The region-centroid distance to the nearest historical gaze runs 3.8–22.0°, but
for a region covering most of the chart the centroid is not a meaningful location.

| target | missed | cells | deg² | chart | median dist. to support | centroid–gaze |
|---|---|---|---|---|---|---|
| sol | 1,036 | 119,827 | 1,198 | 59.6 % | 17.2° | 14.5° |
| lettersPlank | 377 | 11,134 | 111 | **5.5 %** | 6.2° | 10.8° |
| woodBaseboard | 330 | 7,807 | 78 | **3.9 %** | 10.4° | 15.5° |
| wall.008 | 308 | 75,170 | 752 | 37.4 % | 12.2° | 5.4° |
| ceilingMoulding | 279 | 156,191 | 1,562 | 77.8 % | 25.7° | 22.0° |
| plank | 252 | 135,741 | 1,357 | 67.6 % | 14.4° | 3.8° |
| boardFrame | 244 | 152,218 | 1,522 | 75.8 % | 13.2° | 9.2° |
| woodBaseboard | 187 | 14,773 | 148 | **7.4 %** | 9.2° | 13.5° |
| blackBoardLamp, alphabet, blackBoard_upPart, verticalPipe, blackboardLamp | 59 / 55 / 50 / 12 / 9 | — | — | 54–93 % | — | — |

No policy score is derived from these descriptors.

**Does incidental 3-D subdivide the complement usefully?** This is a counterfactual,
evaluation-side test: fold incidental-only surface cells back into UNKNOWN and re-label.

- **lettersPlank:** its localized region exists only because of incidental evidence. Without
  it, the same 377 misses fall in a 76 %-of-chart complement.
- **woodBaseboard:** its localization comes from mapped surfaces and survives the ablation.
- **All other targets:** incidental evidence only trims the complement, for example sol
  68.8 % → 59.6 %.

Misses in UNKNOWN regions of at most 15 % of the chart total 894 with incidental evidence and
517 without it.

### Q7. Missed-target components on the 0.25° truth lattice (8-connected)

| | Phase 6 (all 3,670 misses) | Oracle-3b (3,479 detached misses) |
|---|---|---|
| components | **103** | 62 |
| size: 1 / 2–9 / 10–99 / ≥ 100 | 36 / 44 / 14 / **9** | — / — / — / **9** |
| samples in components ≥ 100 | **2,809 (76.5 %)** | 2,748 (79.0 %) |
| largest | sol 951, woodBaseboard 400, lettersPlank 382, wall.008 257, ceilingMoulding 204, boardFrame 176 / 164, plank 173, ceilingMoulding 102 | sol 935, woodBaseboard 393, lettersPlank 378, wall.008 236, ceilingMoulding 199, boardFrame 174 / 164, plank 167, ceilingMoulding 102 |

The same nine large components reappear, slightly larger because Phase 6 also counts the
191 shoreline-adjacent misses Oracle-3b excluded. The extra small components are mostly
support misses and alphabet's 30 tiny ones.

Proposal regions per component:

- 82 of 103 components lie in a **single** region; 14 touch 2, 5 touch 3 and 2 touch 4.
- By kind: UNKNOWN only 40, TARGET_SUPPORT only 39, OTHER_SURFACE only 3, mixtures 21.

The large Oracle-3b "near tip, far body" strips mostly span TARGET_SUPPORT (the tip) plus
one UNKNOWN region (the body), and that UNKNOWN region is usually the giant complement.
The strips are "localized" to one candidate, but that candidate is typically most of the
chart.

### Q8. Clearest examples (measured quantities only)

- **lettersPlank — the best localization.** 377 of 382 misses fall in one 11,134-cell
  (5.5 %) UNKNOWN region that incidental 3-D separates from a 60 % complement. Recall 0.995;
  one 382-sample component.
- **woodBaseboard — the richest structure.** 634 misses spread over 6 positive regions:
  UNKNOWN 330 and 187 (3.9 %, 7.4 %), mapped woodBase 57 and 21, mapped sol 22 and 12, plus
  5 in support.
- **sol — the saturated case.** 1,036 of 1,043 misses sit in one UNKNOWN complement covering
  59.6 % of the chart, as the 951-sample strip reaching the chart corner (yaw 13.75–25°,
  pitch −20 to −14.5°).
- **boardFrame — both kinds.** 94 misses in the mapped blackBoard region (14.4 %) and 244 in
  a 75.8 % complement.
- **coat 1 — the unproposable case.** All 50 misses lie inside its own support, so recall is
  0.

### Q9. Is this benchmark rich enough for graph-level region selection?

**No, not in this form.**

1. **The candidate set is saturated in area.** It covers 96 % of the chart, so 96 % recall is
   nearly automatic.
2. **Positives are dominated by one trivial answer.** 56.6 % of captured misses lie in regions
   larger than half the chart, the target's unexplored complement. Choosing "the complement"
   is not region selection.
3. **The decision is degenerate.** Only 30 of 1,672 candidates are positive (1.8 %), in 13
   targets. The negatives are overwhelmingly tiny fragments (691 regions of at most 10 cells).
4. **Genuine localization is limited to about a third of misses** (1,221 in regions of at
   most 15 % of the chart) and concentrated in three targets (lettersPlank, woodBaseboard,
   boardFrame) plus a few mapped surfaces.
5. **Incidental 3-D helps in exactly one case.** lettersPlank.
6. **The dominant Oracle-3b "far bodies" remain inside giant complements.** The partition
   has no evidence to split never-observed territory.

### Recommended next benchmark (not implemented; no policy designed)

1. **Prefix-level benchmark on the same accepted run.**
   - Apply the same truth-free partition at all 104 historical prefixes rather than only the
     25 causal-final states; Phase-5 head evidence already exists for every prefix.
   - Evaluate offline against coverage of each prefix map (`maps/fix_k.npz`).
   - This multiplies the decision points, varies difficulty, and gives each prefix a natural
     reference: whether the historical next fixation landed in a truth-positive region.
2. **Cross-target causal memory.**
   - Accumulate head-centred 3-D from all earlier targets' looks, not just the current
     target's, before partitioning.
   - This is controller-time information at global state *g*, and it is the one mechanism
     measured here that splits a complement (lettersPlank).
   - Test it first with the same evaluation-side ablation used above.
3. **Only if the giant complement persists, a fixed truth-free subdivision of UNKNOWN.**
   Examples are geodesic shells from target support or fixed angular tiles. The candidate
   granularity then becomes a benchmark parameter rather than an accident of evidence
   sparsity.
4. **If 1–3 still leave the decision degenerate, a new challenge setting.** Examples are
   another scene, other seeds, or a budget-limited Oracle-1 configuration run as a separate
   experiment. The sealed golden baseline and its signatures stay untouched.

## Demo inspection

`previews/partition-graph-6-evaluation/demo/`:

- 25 frames, one per target, 1280 × 1040;
- `partition-graph-6-demo.mp4` (25 frames at 2 fps; decodes fully);
- `overview.png` (1600 × 1300);
- `Demo.md`.

Inspected lettersPlank (frame 12), sol (17), woodBaseboard (23) and coat 1 (11, the
all-support edge case):

- **Orientation:** positive pitch is up (the floor `sol` is at the bottom).
- **Panel 1:** its colours match the key.
- **Panel 2:** now shows localized UNKNOWN regions distinctly (lettersPlank's maroon region;
  woodBaseboard's two regions) against the dark complement, with region edges.
- **Panel 3:** labelled "EVALUATION ONLY"; it shows missed samples (red) inside those regions
  and inside coat 1's own support. Its per-target missed counts are asserted equal to the
  evaluator's.
- **`Demo.md`:** states that truth never enters the proposal tree and is not a controller
  feature.

## Immutability and behaviour

Relative to `11d61f8` the changes are the package commit (6 new files), the demo
presentation fix and this report. Every file tracked at `6c8a80f` is untouched, including
the sealed `tools/*` engine, `fov3d` facade wrappers, `tests/golden/`, `scripts/` and scene
manifests. The baseline verifier, checkers 1–6, the smoke comparator and `git diff --check`
were re-run after the report was written. `previews/` stays untracked.

**No gaze, controller, matcher, fusion, rendering or termination behaviour changed, and no
policy, score or candidate ranking was introduced.**

PARTITION_GRAPH6_EPISTEMIC_BENCHMARK_COMPLETE
