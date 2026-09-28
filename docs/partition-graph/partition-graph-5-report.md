# Partition-Graph Phase 5 — unified head-centred evidence and challenge states report (2026-09-25)

The contract is `docs/partition-graph-5.md`. This phase is a retrospective representation
experiment. **No attention policy was implemented, and no controller, matcher, fusion,
gaze, termination, golden signature, script or scene asset changed.** Earlier reports are
preserved unchanged.

Terms used throughout:

- **causal object-final**: a target's own last historical fixation.
- **all prefixes**: every one of the 104 historical states.
- **scene-final**: retrospective information. It is not used for any causal conclusion
  below.
- **Instance and object identity** is inherited from Oracle-1 throughout.

## Branch, commits and files

| | |
|---|---|
| branch | `architecture/partition-graph-5`, tracking `origin/architecture/partition-graph-5` |
| `02344b9` Add head-centred incidental evidence analysis | package commit by `PARTITION_GRAPH5_APPLY.sh` on `00af6c9`; adds `fov3d/experiments/classroom_partition/incidental.py`, `tools/partition_graph5_{analyze,demo}.py`, `tools/dev/check_partition_graph5.py` and `docs/partition-graph-5.md`; modifies no existing file; all byte-identical to `~/Downloads/partition-graph-5.zip` (sha256 `d1c4470b…d6d9ca40`) |
| `bd90474` Fix Phase-5 demo evidence key and unresolved-cell visibility | presentation-only demo fix (see Deviations) |
| this commit, Report Partition Graph Phase 5 | this report |

The apply script unzipped the whole package into the repository, so
`PARTITION_GRAPH5_CODE_PROMPT.md` sits untracked in the repository root. It was left
untracked and is not committed.

## Deviations

- **No mechanical repair.** The analysis ran unchanged (10.4 s).
- **Demo presentation fix (`bd90474`).** No analysis output changed.
  - The evidence panel's BGR palette displays `SEEN_NO_HEAD_DEPTH` as **blue**, but the key
    said "tan". The mapped-other gray was missing from the key, and the current target's own
    depth cells fell into the "seen / no head depth" colour.
  - The unresolved panel painted **every** true-gap cell of an unresolved relation red, and
    the 1–3 unresolved cells of the challenge states were about 1 px, practically
    invisible.
  - The panel now uses the relation classifier's precedence (target support first) with a
    correct key. Only unresolved cells are red, and each is circled; explained true-gap
    cells are orange. `Demo.md` states the key and semantics.
  - The package demo is kept at `previews/partition-graph-5-full/demo-package-original/`.
- **Supplementary read-only analysis (untracked).** `previews/partition-graph-5-audit/`
  contains `analyze_pg5.py` and `analysis.json`, reading only the Phase-5 and Phase-4
  outputs, plus `analyze.strace`.

## Gates

| gate | result |
|---|---|
| `py_compile` of the 4 new Python files | OK |
| checkers 1 / 2 / 3 / 4 / 5 | 13/13, 16/16, 20/20, 14/14, **12/12** |
| `check_fov3d_facade.py` | 16/16 |
| `scripts/verify_baseline.sh` | `passed=9 failed=0`; 75 tracked `.py`; 31 baseline files byte-identical |
| `git diff --check` | clean |
| golden smoke, new directory `previews/partition-graph-5-golden-smoke` | 5 looks, 68 NPZ arrays, 4 targets, **`MISMATCHES 0`** |
| accepted source `previews/partition-graph-2-source-full` (not regenerated) | 25 objects, 104 fixations, **`MISMATCHES 0`** |
| reused inputs | `previews/partition-graph-4-lift` and `previews/partition-graph-4-full` both record this exact source run, and the Phase-4 analysis records this exact lift; lift `seen_any` 51/0, lineage 10/3/0/1; Phase-4 target-depth 51/0, own lineage 7/2/0/0, no forbidden paths |
| Phase-5 analysis `previews/partition-graph-5-full` | **104 states**; `head_target_depth_true_gap_violations` **0** |
| determinism | a second run to a scratch directory produced the same 211 files; every JSON byte-identical, every NPZ array equal |

## Truth isolation

The official analysis ran under `strace -f -e openat,open,execve`. It opened exactly
**210** source-run files: `manifest.json` 1, `bootstrap/seeds.json` 1, `maps/fix_XX.npz` 104
and `patches/fix_XX.npz` 104. That matches the logger's `read_paths` (`forbidden_read_paths:
[]`). Beyond the source run it read only Phase-4 lift and analysis outputs and wrote its own
output.

- **Forbidden paths:** no `evaluation_only`, `reachable_samples.npz`, `evaluation.json`,
  `oracle_observation.npz`, EXR, benchmark RGB or Blender path was opened.
- **Processes:** one `execve` (the venv Python).
- **Modules:** no sealed `tools/*` engine module was loaded at all, since Phase 5 needs no
  stereo geometry. No controller, matcher, fusion or renderer module was loaded.
- **Summary flags:** `controller_executed`, `matcher_executed`, `fusion_executed`,
  `blender_launched` and `dense_truth_opened` are all false;
  `object_identity_inherited: true`.

## Results

### 1. Head-origin target depth in true gaps

`head_target_depth_true_gap_violations = 0` across all 104 states. Projected from the head
origin, no valid target sample ever lands outside the target's own support inside a gap
corridor.

### 2. True-gap cell classes (own-support-gap relations)

| | relations | true-gap cells | MAPPED_OTHER | INCIDENTAL_OTHER_DEPTH | AMBIGUOUS_DEPTH_INSTANCE | SEEN_NO_HEAD_DEPTH | UNSEEN |
|---|---|---|---|---|---|---|---|
| all prefixes | 214 | 6,887 | 4,756 (69.1 %) | 979 (14.2 %) | 83 (1.2 %) | 814 (11.8 %) | 255 (3.7 %) |
| causal object-final | 44 | 842 | 492 (58.4 %) | 223 (26.5 %) | 7 (0.8 %) | 96 (11.4 %) | 24 (2.9 %) |

The causal-final total of 842 true-gap cells equals Phase 4's independent count.

### 3. Relations, challenge relations, states and targets

| | all prefixes | causal object-final |
|---|---|---|
| own-support-gap relations | 214 | 44 |
| challenge (unresolved) relations | **108** | **10** |
| challenge states | **41** | — |
| challenge targets | **4**: sol, wall.008, woodBase, woodBaseboard | 4 |

The 108 challenge relations reduce to only **12 distinct (target, own-component pair)
cases**, repeated across prefixes:

- wall.008 [1,2] 27, [2,4] 14, [2,3] 10, [1,3] 9;
- woodBase [1,2] 19, [2,3] 10, [1,3] 7, and 2 each for [1,4], [2,4], [3,4];
- sol [1,2] 4;
- woodBaseboard [1,2] 2.

### 4. Reconstruction status of non-target depth seen in gaps

Counted over true-gap cells whose nearest head-centred sample is a non-target instance:

| | mapped_now | targeted_later | never_targeted |
|---|---|---|---|
| all prefixes | 4,545 | 817 (worldMap 642, lettersPlank 149, verticalPipe 25, blackboardLamp 1) | **0** |
| causal object-final | 491 | 218 (lettersPlank 149, worldMap 52, verticalPipe 16, blackboardLamp 1) | **0** |

In this run every locally measured instance in a gap was one of the 25 Oracle-1 targets.
In about 15 % (all prefixes) and 31 % (causal-final) of such cells, the instance had been
measured locally **before** it was reconstructed as an object.

### 5. What Phase 4's `LEFT_NONTARGET_ONLY` territory gains

| Phase-4 `LEFT_NONTARGET_ONLY` true-gap cells | total | MAPPED_OTHER | INCIDENTAL | AMBIGUOUS | SEEN_NO_HEAD_DEPTH | head 3-D not in any map |
|---|---|---|---|---|---|---|
| causal object-final | 736 | 469 (63.7 %) | 175 (23.8 %) | 7 | 85 (11.5 %) | **182 (24.7 %)** |
| all prefixes | 5,955 | 4,247 (71.3 %) | 928 (15.6 %) | 83 | 697 (11.7 %) | **1,011 (17.0 %)** |

About 88 % of the left-eye "another instance" territory is therefore backed by 3-D in the
partition's own chart, whether as a mapped object or as incidental head-centred depth. About
a quarter of it (causal-final) is incidental depth that no object map contained. The 76
Phase-4 parallax `TARGET_DEPTH_VALID` true-gap cells become 47 incidental, 19 mapped and 10
seen-without-depth, confirming they were other-instance territory. Phase 4's 24 `UNSEEN`
cells stay `UNSEEN`.

### 6. The deterministic compact challenge set (earliest unresolved state per target)

| target | global state | local fix | causal-final? | gap | true-gap cells | unresolved |
|---|---|---|---|---|---|---|
| 178 sol | 40 | 1 | no | 0.20° | 1 | 1 `SEEN_NO_HEAD_DEPTH` |
| 210 wall.008 | 59 | 3 | no | 1.90° | 18 | 1 `AMBIGUOUS` (17 incidental) |
| 224 woodBase | 76 | 0 | no | 0.20° | 1 | 1 `SEEN_NO_HEAD_DEPTH` |
| 225 woodBaseboard | 95 | 0 | no | 0.39° | 3 | 3 `SEEN_NO_HEAD_DEPTH` |

### 7. Is the challenge set numerous and diverse enough for a graph-attention experiment?

**No.** The measurements do not support it on this trajectory.

- **Size.** 4 targets, 12 distinct cases, and a median of **2** unresolved cells per
  challenge relation. 35 relations have 1 cell, and only 13 have 10 or more.
- **Reasons, all prefixes (108 relations).** Seen-without-head-depth only 72, ambiguous
  only 27, unseen only 3, seen + unseen 6.
- **Reasons, causal-final (10 relations).** Seen-without-head-depth 7, ambiguous 2, seen +
  unseen 1.
- **`AMBIGUOUS_DEPTH_INSTANCE` is boundary quantization here.** All 83 ambiguous true-gap
  cells have at least two different nearest instances in their 3 × 3 neighbourhood: they are
  0.1° cells straddling two other objects.
- **`SEEN_NO_HEAD_DEPTH` is mostly thin bands.** Median distance to the nearest head-depth
  cell is 3 cells, and 644 of 814 (79 %) lie within 4 cells. `seen_any` is the historical
  eye-ray raster while depth is head-origin projected, so these bands mix the two charts.
- **Only two episodes carry substantial unresolved territory, and both were transient.**
  The historical controller's own later fixations removed them:
  - `wall.008`, local fixes 6–8 (15.13° relation): **37 `UNSEEN` cells deep in unseen
    territory**, 10–13 cells from any seen cell. Gone from fix 9.
  - `woodBase`, local fixes 10–11 (7.27° and 15.67° relations): **48–49
    `SEEN_NO_HEAD_DEPTH` cells**, 41–44 of them more than 4 cells from any head depth
    (median 11–12). Gone at fix 12, the merge event.
- **The largest persistent causal case is band-like.** `wall.008` [1,3] (12.33°, fixes
  13–18, causal-final) has 106 unresolved cells. Its 24 `UNSEEN` cells all lie within 1
  cell of seen territory, and its 82 `SEEN_NO_HEAD_DEPTH` cells within 4 cells of head
  depth: a sliver plus bands, not a region nobody looked at.

A graph-attention experiment on this golden trajectory would have two genuine episodes,
both already resolved by the historical policy, plus quantization and band cells. That is
too few and too uniform to evaluate a policy. Per the contract, the correct conclusion is
that **the golden Classroom trajectory is unsuitable for testing graph-level attention as
it stands**.

### 8. Examples (causal object-final unless stated)

- **`alphabet` / `lettersPlank`.** All **149** true-gap cells of alphabet's 15 own-support
  gaps are `INCIDENTAL_OTHER_DEPTH` from `lettersPlank`, which was `targeted_later` at
  alphabet's final state (global 2). The controller had already measured lettersPlank's 3-D
  surface in those gaps, but the old representation kept only target geometry. This is the
  clearest case of **local measurement preceding object reconstruction**. It is not an
  occlusion verdict: Phase 4 found the two surfaces near-coplanar (1.4 mm jump, split
  votes).
- **`worldMap`** (global 103). Its one own-support gap (1.80°) has 9 true-gap cells, all
  `MAPPED_OTHER` by `verticalPipe` (`mapped_now`). Resolved.
- **`blackBoard_upPart`** (global 21). 9 own-support gaps, 42 true-gap cells, all
  `MAPPED_OTHER`: blackBoardLamp 41 cells (`mapped_now`), blackboardLamp 1 (`targeted_later`).
  Resolved.
- **`wall.008`** (global 74). 12 own-support gaps and 5 unresolved; true-gap cells are
  MAPPED 421, INCIDENTAL 58, SEEN_NO_HEAD_DEPTH 87, UNSEEN 24, AMBIGUOUS 7. `worldMap`
  (`targeted_later`) supplies 52 cells of incidental depth. Its [1,3] relation is the band
  case described in §7, and its transient fix 6–8 relation is the only deep-unseen episode
  in the run.

## Interpretation boundary

- `MAPPED_OTHER` and `INCIDENTAL_OTHER_DEPTH` mean another measured surface occupies that
  angular territory. They are **not** occlusion or continuation verdicts.
- The incidental memory models what *could have been persisted*. Oracle-1 did not persist or
  reason over it.
- Instance identities are Oracle-1's inherited labels.
- No scene-final information is used for any causal-time statement above.

## Demo inspection

`previews/partition-graph-5-full/demo/`:

- 4 frames, one per compact challenge state, 1252 × 1120;
- `partition-graph-5-demo.mp4` (4 frames at 2 fps; decodes fully);
- `overview.png` (1251 × 746);
- `Demo.md` with the key.

Positive pitch is up (the floor is at the bottom). The panel-2 colours match the documented
key. In every frame, the red circled cells of panel 3 are exactly the unresolved cells in
`relations.json`, and the orange cells exactly the explained ones (sol 1/0, wall.008 1/17,
woodBase 1/0, woodBaseboard 3/0). The circles make the 1–3-cell unresolved sets visible.

## Immutability

Relative to `00af6c9` the changes are the package commit (5 new files), the demo
presentation fix and this report. No existing file was modified by the package, and every
file tracked at `6c8a80f` is untouched. The following were re-run after the report was
written:

- the baseline verifier;
- checkers 1–5;
- the smoke comparator.

`previews/` stays untracked. **No gaze, controller, termination or golden behaviour
changed.**

## Recommendation (not implemented; no Phase-6 policy designed)

1. **Tighten the unresolved definition before using it.**
   - Treat ambiguity only where it is not boundary quantization, for example conflicting
     instances inside one cell away from instance edges.
   - Express "seen" in the head chart, or mark the eye-ray/head-origin band as
     indeterminate, so `SEEN_NO_HEAD_DEPTH` stops counting chart-mixing bands.
2. **Find or build a setting with substantial unresolved territory before any attention
   experiment.** The two transient episodes show such territory exists mid-trajectory on
   this run, but only rarely. Candidates are other scenes, other seeds, or budget-limited
   replays.
3. **Keep the incidental 3-D memory as architecture.** It is the concrete, measured gain of
   this phase: local non-target depth resolves about a quarter of causal left-eye
   "another instance" gap territory that no object map held.
