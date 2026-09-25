# Partition-Graph Phase 4 — typed gap relations and local epistemic evidence report (2026-09-25)

The contract is `docs/partition-graph-4.md`. This phase is retrospective representation and
analysis only. **No gaze policy was implemented, and no controller, matcher, fusion,
renderer, stereo implementation, golden signature, script or scene asset changed.**
Earlier reports are preserved unchanged.

Terms used throughout:

- **causal object-final**: the joint graph at a target's own last fixation, holding only
  objects reconstructed earlier plus that target's own evidence. This is information the
  historical controller could have had.
- **scene-final**: the last joint graph (global state 103). It is retrospective.
- **ownership cut**: a relation whose two joint components lie in one connected component
  of the target's own support.
- **own-support gap**: a relation whose two joint components lie in different components of
  the target's own support.

## Branch, commits and files

| | |
|---|---|
| branch | `architecture/partition-graph-4`, tracking `origin/architecture/partition-graph-4` |
| `52c9395` Add typed gap relations and local epistemic replay | package commit made by `PARTITION_GRAPH4_APPLY.sh` on `0f580d7` (zip sha256 `869068a8…c7610`, as the apply script expected) |
| `d184766` Fix Phase-4 demo evidence colour key | demo display/documentation fix (see Deviations) |
| this commit, Report Partition Graph Phase 4 | this report |

The package **modifies one existing file**, `fov3d/experiments/classroom_partition/joint.py`,
with the narrow `_lineage` repair only:

- one target-local label space for the previous and current rasters;
- a shape check;
- the updated call site.

Running `tools/dev/apply_partition_graph4_lineage_fix.py` on the Phase-3 blob `1b67ea9`
reproduces the committed `joint.py` byte for byte. **New files:**

- `fov3d/experiments/classroom_partition/relations.py`;
- `tools/partition_graph4_{lift,analyze,demo}.py`;
- `tools/dev/check_partition_graph4.py`;
- `tools/dev/apply_partition_graph4_lineage_fix.py`;
- `docs/partition-graph-4.md`.

All match the zip. The zip's `PARTITION_GRAPH4_CODE_PROMPT.md` was not committed.

## Repairs and deviations

- **No mechanical repair.** The package ran unchanged against the live API: lift 28.5 s,
  analysis 14.6 s.
- **Demo display/documentation fix (`d184766`).**
  - The evidence panel's palette is written in BGR, so `LEFT_NONTARGET_ONLY` displays
    **blue** and `LEFT_TARGET_NO_DEPTH` **yellow**, but the footer named them "orange" and
    "cyan", omitted purple `LEFT_MIXED_NO_DEPTH`, and was clipped.
  - `Demo.md` listed the class names without colours or meanings, so the contract item
    "fine evidence key/semantics are stated in Demo.md" failed.
  - The footer now names the displayed colours and shrinks to fit, and `Demo.md` carries the
    full key, precedence, left-eye-subset caveat and chart-convention note.
  - No palette, relation, evidence or measurement changed. The package's own demo is kept at
    `previews/partition-graph-4-full/demo-package-original/`.
- **Supplementary read-only analyses (untracked).** These live in
  `previews/partition-graph-4-audit/`: `analyze_pg4.py`, `analyze_pg4_gapcells.py` and the
  `strace` logs. They read the Phase-4 outputs, plus the source run's `manifest.json`,
  `seeds.json`, `calibration.json` and `patches/fix_XX.npz` through a guard that rejects
  truth, EXR, oracle-observation, benchmark and Blender paths. They add no new policy, and
  their results are labelled *supplementary* below.

## Gates

| gate | result |
|---|---|
| `py_compile` (joint, relations, 3 tools, checker) | OK |
| checkers 1 / 2 / 3 / 4 | 13/13, 16/16, 20/20, **`[partition-graph4-check] SUMMARY checked=14 failed=0`** |
| `check_fov3d_facade.py` | 16/16 |
| `scripts/verify_baseline.sh` | `passed=9 failed=0`; 71 tracked `.py` compiled; 31 baseline files byte-identical |
| `git diff --check` | clean |
| golden smoke, new directory `previews/partition-graph-4-golden-smoke` | 5 looks, 68 NPZ arrays, 4 targets, **`MISMATCHES 0`** |
| reused source `previews/partition-graph-2-source-full` (not regenerated) | looks 104, NPZ arrays 1,348, targets 25, **`MISMATCHES 0`** |
| fresh lift `previews/partition-graph-4-lift` | 104 states; `seen_any` **51 checkpoints, 0 mismatches**; `unencoded_interface_edges == 0` in all 104 states (569,730 / 569,730); lineage **`{births 10, merges 3, splits 0, deaths 1}`** |
| analysis `previews/partition-graph-4-full` | 104 states; joint lineage 10/3/0/1; own-support lineage **7/2/0/0**; `NEVER_OBSERVED` 51/0; **`OBSERVED_TARGET_WITH_DEPTH` 51 checkpoints, 0 mismatches** |
| relation typing, all 570 records (302 per-state, 86 causal, 182 scene-final) | every record has exactly one origin; every `ownership_cut` maps both endpoints to the same own-support component; every `own_support_gap` maps them to different ones; evidence-class counts sum to the corridor interior; `UNSEEN` equals the Phase-3 unseen count |

## Truth isolation

| run | source files opened (logger = `strace`) | forbidden opens | processes | engine modules loaded |
|---|---|---|---|---|
| lift | 210: `manifest.json` 1, `bootstrap/seeds.json` 1, `calibration.json` 104, `maps/fix_XX.npz` 104 | 0 | 1 (`.venv/bin/python`) | `tools/fsg_stereo`, `tools/fsg_geometry` via `fov3d.stereo.core` |
| analysis | 314: the above + `patches/fix_XX.npz` 104 | 0 | 1 | same |

The analysis was traced on the official run itself. Neither run opened `evaluation_only`,
`reachable_samples.npz`, `evaluation.json`, `oracle_observation.npz`, an EXR, benchmark RGB or
Blender data, although several of these exist in the source run. No matcher, controller,
epistemic, frontier, fusion, renderer or `bpy` module was loaded. `summary.json` declares:

- `controller_executed`, `matcher_executed`, `fusion_executed`, `blender_launched`,
  `dense_truth_opened`: all `false`;
- `object_identity_inherited`: `true`;
- `forbidden_read_paths`: `[]`.

## Corrected lineage proof

- The fixed `_lineage` gives joint totals **10 births, 3 merges, 0 splits, 1 death** on the
  unchanged golden source.
- The per-target events are identical to the Phase-3 read-only recomputation:
  - `lettersPlank`: birth 1, merge 1, death 1;
  - `sol`: birth 2, merge 1;
  - `wall.008`: birth 4;
  - `woodBase`: birth 2, merge 1;
  - `worldMap`: birth 1.
- The fix is isolated. All 416 per-state lift files and both corridor files are
  byte-identical to the Phase-3 lift, and the lift summary differs only in the lineage
  fields of the 79 non-initial states and their totals.
- The analysis's independent own-support lineage is **7 births, 2 merges, 0 splits, 0
  deaths**, as audited in Phase 3.

## Exact target-depth-valid replay proof

The historical epistemic module marked `target_depth_valid` from
`raw_support_L & (ids_left == target) & valid_L` along the rectified left-core directions,
accumulated per target (`make_evidence()` inside each object's run). The saved patch
contains exactly `ids_left` (`instance_id`) and `valid`, and `raw_support_L` is the
geometric `fsg_stereo.support_mask`. The replay recomputes the same mask with the same
geometry. At all 51 saved Cyclopean checkpoints (25 targets, 4 to 41,633 cells),
`replayed target_depth_valid == historical OBSERVED_TARGET_WITH_DEPTH`. The Phase-3
`NEVER_OBSERVED` replay also still matches at all 51.

## Results

### Relation origin

| | relations | ownership_cut | own_support_gap |
|---|---|---|---|
| causal object-final | 86 | **42** (3 targets: blackBoard_upPart 36, lettersPlank 3, wall.008 3) | **44** (9 targets: alphabet 15, wall.008 12, blackBoard_upPart 9, woodBase 3, and 1 each for ceilingMoulding, plank, sol, woodBaseboard, worldMap) |
| scene-final (retrospective) | 182 | 73 (7 targets) | 109 (9 targets; alphabet 78) |

### Causal own-support gaps: occupancy

The package's occupancy classes look only at BASE and other-object cells:

| class | pure BASE | pure other-object | mixed |
|---|---|---|---|
| gaps | 23 | 16 | 5 |

17 of the 44 corridors also pass through the target's own other components. On the
Phase-2-comparable unit (the closest bridge per pair of own-support components, 30 pairs)
the causal classes are 22 / 5 / 3. Phase 3's 12 / 5 / 13 counted BASE + same-object as
"mixed". The pairs are the same; only the class definition differs.

### Causal own-support gaps: fine evidence (package flags)

| gaps (44) | count |
|---|---|
| any `TARGET_DEPTH_VALID` cell | **40** |
| fully seen, no `TARGET_DEPTH_VALID` | **3** |
| any `UNSEEN` cell | **1** |

Interior share: `LEFT_NONTARGET_ONLY` 58.7 %, `TARGET_DEPTH_VALID` 38.4 %,
`LEFT_MIXED_NO_DEPTH` 1.5 %, `UNSEEN` 1.3 %, `LEFT_TARGET_NO_DEPTH` 0.05 %,
`SEEN_NO_LEFT_ID_EVIDENCE` 0.

**The "40/44 with target depth" flag does not mean target depth was measured inside the
gaps.** A supplementary decomposition of the 1,893 interior cells of these 44 corridors
shows:

- 785 cells (41.5 %) are the target's own other components;
- 266 (14.1 %) are the target's own support, won by a nearer object;
- 842 (44.5 %) are **true gap cells** outside the target's own support.

Of the 727 `TARGET_DEPTH_VALID` corridor cells, 517 lie on the target's own components, 134
on its own support owned by a nearer object, and only 76 in true gap cells. **All 76 lie in
the left-eye parallax band.** Evidence is marked along left-eye rays, as the historical
module did, while the partition projects maps from the head origin. The 31.5 mm eye offset
displaces the evidence by a predicted 3.6–4.7 cells in yaw (median 4.0) at the targets'
ranges. The best aligning shift of `target_depth_valid` onto the head-centred support is
median +3 cells (12 of 25 targets at exactly 3).

Eye-ray depth-valid cells outside the support fall from a median of 3.7 % (max 40 %) to at
most 4.2 % after that shift. When the same valid target points are projected from the head
origin (patch `xyz_h`), **0 % fall outside the target's support for every target**. In the
partition's own chart, no gap ever held valid target depth. That follows from how the maps
were built: there were no empty-fusion looks in this run.

**True gap cells (842), by evidence class** (supplementary):

| class | cells | share | note |
|---|---|---|---|
| `LEFT_NONTARGET_ONLY` | 736 | 87.4 % | |
| `TARGET_DEPTH_VALID` | 76 | 9.0 % | all in the parallax band |
| `UNSEEN` | 24 | 2.9 % | all in `wall.008` [1,3] |
| `LEFT_MIXED_NO_DEPTH` | 6 | 0.7 % | |
| `LEFT_TARGET_NO_DEPTH` | 0 | 0 | |

Per relation:

- 38 of the 44 true gaps are entirely `LEFT_NONTARGET_ONLY` or parallax cells;
- 1 has unseen cells;
- 5 have mixed or target-no-depth cells.

**Which instance the left eye saw in the true gap cells** (supplementary, from the patch
`instance_id`; these are Oracle-1's inherited oracle labels):

| instance seen | cells |
|---|---|
| a target reconstructed **earlier** | 436 |
| a target reconstructed **later** | 324 |
| both | 16 |
| id 0 | 15 |
| no non-target id | 51 |
| an instance **never targeted** | 0 |

Per relation, 22 corridors saw an earlier-reconstructed instance in the gap and 25 a
later-reconstructed one. At causal time the controller's own observation had therefore
already labelled most gap territory as "another instance", even where that instance's map
did not yet exist.

### Scene-final (retrospective)

- **Occupancy of the 109 own-support gaps:** pure other-object 100, pure BASE 5, mixed 4.
- **Evidence flags:** any `TARGET_DEPTH_VALID` 94; fully seen without it 15; any `UNSEEN` 0.
- **Ownership cuts:** 73; 67 of them have a later-reconstructed object in the corridor.

On the own-pair unit, the causal classes 22 / 5 / 3 become 4 / 24 / 2. **20 of the 30 own
pairs gain an intervener reconstructed after the target finished.** Counted per relation,
28 of the 44 causal own-support-gap relations belong to an own pair whose scene-final
bridge has a later intervener. None of this was available to the historical controller when
the target terminated.

### Ownership margin (target range − frontmost owner range, where both exist)

| relations with samples | median of per-relation medians | P90 | max | all samples > 12 mm | median < 12 mm |
|---|---|---|---|---|---|
| causal ownership_cut (26/42) | 44.8 mm (3.7 × 12 mm) | 50.6 mm | 221.6 mm | 23 | 3 |
| causal own_support_gap (21/44) | 151.8 mm (12.7 ×) | 198.0 mm | 244.8 mm | 18 | 0 |
| scene ownership_cut (67/73) | **7.6 mm (0.64 ×)** | 46.9 mm | 221.6 mm | 19 | **38** |
| scene own_support_gap (102/109) | **2.3 mm (0.19 ×)** | 154.7 mm | 208.5 mm | 20 | **76** |

In the causal context almost every relation involving a nearer object has a clear margin.
For example, the 21 `blackBoard_upPart` cuts by `blackBoardLamp` have medians of 38–52 mm.
The scene-final context is dominated by sub-fusion-radius margins: all 86 `alphabet`
relations with samples have medians ≤ 5.5 mm against `lettersPlank`, a later object.

### Boundary depth order (target ← intervener, aggregated object–object boundary votes)

Causal context: 13 target/intervener pairs.

- **9 are one-sided with the intervener nearer.** Vote-balance confidence is 1.0 and the
  interface-weighted median jumps range 0.9–34.6 cm. The 0.9 cm case is `wall.008` ←
  `alphabet`, with only 7 interface edges. The best-supported pairs are:
  - `worldMap` ← `verticalPipe`: 252:0, 16.7 cm;
  - `blackBoard_upPart` ← `blackBoardLamp`: 206:0, 12.6 cm;
  - `wall.008` ← `coat 1`: 122:0, 34.6 cm;
  - `wall.008` ← `verticalPipe`: 116:0, 19.4 cm;
  - `wall.008` ← `blackBoardLamp`: 143:0, 21.1 cm.
- **1 is mostly one-sided:** `wall.008` ← `lettersPlank`, 75:413, confidence 0.69, 7.9 mm.
- **2 are ambiguous**, and they are of two kinds:
  - near-coplanar: `lettersPlank` ← `alphabet`, 276:303, confidence 0.047, 1.4 mm jump;
  - a large jump with split votes: `woodBase` ← `verticalPipe`, 89:102, confidence 0.068,
    26.9 cm, where the order flips along the boundary.
- **1 has no shared boundary:** `wall.008` ← `blackBoard`.

The scene-final context adds 12 retrospective pairs. Examples:

- `Text` ← `lettersPlank.001`: 157:147, confidence 0.033, 2.3 mm;
- `plank` ← `verticalPipe`: 21:20, confidence 0.024, 26.4 cm;
- `wall.008` ← `worldMap`: 122:145, confidence 0.086.
- `blackBoard_upPart` ← `wall.008`: 192:0 with the **target** nearer. The object occupying
  its 27 ownership-cut corridors is *behind* the target.

### Examples (selected by the measured quantities above)

- **Strongest one-sided intervener on an own-support gap: `worldMap` [1,2].** 1.80°, 17
  cells, all `verticalPipe` (earlier). 8 cells are own support won by the pipe (margin 138
  mm, 100 % > 12 mm) and 9 are true gap cells, all observed as earlier-reconstructed
  instances (`verticalPipe` in 8, `wall.008` in 2). The boundary has 252:0 votes and a
  16.7 cm jump.
- **The only relation with an epistemic deficit: `wall.008` [1,3].** 12.33°, 122 true gap
  cells: 98 `LEFT_NONTARGET_ONLY`, observed as `worldMap` (later), and 24 `UNSEEN`. In the
  scene-final context it is bridged entirely by `worldMap`.
- **Largest ownership-cut family: `blackBoard_upPart`.** 36 causal cuts by the earlier
  `blackBoardLamp` (206:0, 12.6 cm, margins 38–52 mm). Its 9 own-support gaps each have 4–5
  true gap cells, all observed as `blackBoardLamp`.
- **Ambiguous, near-coplanar: `alphabet` / `lettersPlank`.** Causally, the 15 `alphabet`
  gaps are BASE plus its own components. Their true gap cells were already observed as
  `lettersPlank`, which was reconstructed only later. In the scene-final context, 91
  relations cross `lettersPlank` with ≤ 5.5 mm margins and 303:276 votes.
- **Large jump, unordered: `woodBase` / `plank` ← `verticalPipe`.** 26–27 cm jumps with
  split votes.

## Is the finer evidence discriminative enough for a Phase-5 attention experiment?

**Not yet**, on this run and in this form.

1. **Relation origin is the most useful new distinction.** It separates 42 causal ownership
   cuts, which frontmost ownership manufactures, from 44 real own-support gaps. Ownership
   margins and depth-order confidence then separate clear nearer interveners from
   near-coplanar or order-flipping ones.
2. **The six evidence classes, used as corridor flags, do not discriminate gaps.**
   - `TARGET_DEPTH_VALID` inside gaps comes from the target's own components and from the
     eye-ray / head-origin parallax band, never from true gap cells.
   - `UNSEEN` touches 1 of 44 causal gaps.
   - True gap cells are 87 % `LEFT_NONTARGET_ONLY`: the historical left eye saw another
     instance in almost every gap.
3. **Genuinely unresolved gaps are rare here.** Only `wall.008` [1,3] (24 unseen cells) and
   5 relations with a few mixed or target-no-depth cells carry any epistemic deficit. An
   attention experiment on this golden run would have almost nothing to act on.
4. **The discriminating content is which instance was seen in the gap.** That means
   whether it is already reconstructed, earlier or later, and its depth order against the
   target. That content comes from Oracle-1's inherited instance labels; a non-oracle system
   would have to earn it.

## Recommendation for the next phase (not implemented)

Do one more representation refinement before designing attention:

1. **Put evidence and partition in one chart.** Either project depth-bearing evidence from
   the head origin using the patch `xyz_h`, as the supplementary check did, or carry an
   explicit parallax band so the eye-ray classes no longer bleed into gaps.
2. **Record the observed intervening instance per gap** (from patch ids) with its
   reconstruction status (earlier, later, never) and its boundary depth-order confidence.
   Label the inherited-oracle dependence explicitly.
3. **Choose a Phase-5 test setting that has real unresolved gaps.** In this golden run,
   causal gaps are almost all already observed as another instance. Candidates are a scene
   or run with unseen or target-without-depth gap territory, or a setting without oracle
   instance labels.

Only then should a graph-level attention rule be designed. No success score, priority or
gaze recommendation is introduced here.

## Demo inspection

`previews/partition-graph-4-full/demo/`:

- 104 PNG frames, 1252 × 1120;
- `partition-graph-4-demo.mp4` (mpeg4, 104 frames at 4 fps; all frames decode and match the
  PNGs within codec error, mean absolute difference 2.7–3.3 / 255);
- `overview.png` (1565 × 1400, a 5 × 5 grid with one representative frame per target);
- `Demo.md`.

Confirmed:

- **Orientation:** positive pitch is up (the floor `sol` is drawn at the bottom).
- **Corridors:** every corridor cell of all 302 per-state relations (16,792 cells) is drawn.
  Ownership cuts are magenta and own-support gaps red; 194 cells are over-painted where
  corridors of different origin overlap.
- **Evidence key:** the displayed class colours match the corrected key.
- **Text panel:** values are generated from each state's `relations.json`. Spot-checked
  frame 74 (`wall.008`: 15 relations, 3 cuts, 12 gaps; the [1,3] line reads gap 12.33°,
  B/O 122/0, depth 0) and frame 94 (`woodBase`: gaps 10.02°, 1.50° and 0.20° with B/O 2/15,
  1/13, 1/0).
- **Display-only fields:** the text panel's `depth=` counts `TARGET_DEPTH_VALID` over the
  whole corridor interior, which is subject to the same-object and parallax caveats above.
  No display issue changes a measured result.

## Immutability

Relative to `0f580d7`, the changes are the package commit (the narrow `joint.py` lineage fix
plus 7 new files), the demo display fix and this report. No sealed `tools/*` engine module,
`fov3d` facade wrapper, `tests/golden/` signature, script or scene asset changed, and every
file tracked at `6c8a80f` is untouched. The following were re-run after the report was
written:

- the baseline verifier;
- the Phase-1 to Phase-4 checkers;
- the smoke comparator.

`previews/` stays untracked. **No gaze, controller, termination or golden behaviour
changed.**
