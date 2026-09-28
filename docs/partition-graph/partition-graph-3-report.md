# Partition-Graph Phase 3 — joint partition and local gap corridors report (2026-09-25)

The contract is `docs/partition-graph-3.md`, committed by the apply script in `3fb0f7d`
"Add joint Classroom partition and local gap corridors" on `aaeb440` (Phase 2 report). This
phase is retrospective representation and analysis only. No gaze policy was implemented, no
controller, matcher, fusion, renderer, stereo implementation, golden signature, script or scene
asset was changed, and `docs/partition-graph-2-report.md` is preserved as evidence.

Two terms are used throughout:

- **causal object-final**: the joint graph at the last fixation of a target's own historical
  run. It can contain only objects reconstructed earlier in the Oracle sequence.
- **scene-final**: the last joint graph (global state 103), after all 25 runs. It is
  retrospective and contains objects the historical controller had not yet reconstructed
  when an earlier target terminated.

## Starting state and package

| | |
|---|---|
| branch | `architecture/partition-graph-3`, tracking `origin/architecture/partition-graph-3` |
| package commit | `3fb0f7d` on `aaeb440`; adds exactly `fov3d/experiments/classroom_partition/joint.py`, `tools/partition_graph3_{lift,demo}.py`, `tools/dev/check_partition_graph3.py`, `docs/partition-graph-3.md`; modifies no Phase-1/2 file |
| package files | byte-identical to `~/Downloads/partition-graph-3.zip`; the zip's `PARTITION_GRAPH3_CODE_PROMPT.md` was not committed |

## Gates

| gate | result |
|---|---|
| `py_compile` of the four Phase-3 files | OK |
| `check_partition_graph1.py` / `2` / `3` | 13/13, 16/16, **20/20** (`[partition-graph3-check] SUMMARY checked=20 failed=0`) |
| `scripts/verify_baseline.sh` | `passed=9 failed=0`; 65 tracked `.py` compiled; 31 baseline files byte-identical |
| `check_fov3d_facade.py` | 16/16 |
| `git diff --check` | clean |
| golden smoke, new directory `previews/partition-graph-3-golden-smoke` | 5 looks, 68 NPZ arrays, 4 targets, **`MISMATCHES 0`** |
| reused source `previews/partition-graph-2-source-full` (not regenerated) | re-compared: looks 104, NPZ arrays 1,348, targets 25, **`MISMATCHES 0`**; 25 objects, 104 fixations, `control_complete` |

## Repairs, defects and deviations

**No mechanical repair.** The lift ran unchanged against the live API (28.6 s, 225 MB peak).

**Package defect found, not repaired: topology lineage.** `_lineage` (`joint.py`, called at
lines 846–851) builds `curr_codes` from the state-wide `state_region_code` of the target's
components. It then tests them against `current_target_labels`, a target-only raster labelled
1…k. The two code spaces coincide only by accident, and in all 79 non-initial states the
target codes lie outside 1…k. For example, `beams` keeps one component (code 9) and is logged
as "birth 1, death 1" at every step. Every current component is therefore counted as a birth
and every previous one as a death. The summary field `lineage_totals_excluding_initial =
{births 191, deaths 185, merges 0, splits 0}` and the per-state `lineage` records are
**invalid**.

This is an internal defect rather than a live-API plumbing mismatch, and fixing it would
change a reported scientific quantity, so the package and its output were left as
delivered. The corrected lineage in §4 is recomputed read-only from the saved state rasters
with the contract's overlap definition. The fix for a future package is to pass the
region-code raster, or compare in one code space.

**Demo-only cosmetic repair (committed with this report).** `tools/partition_graph3_demo.py`
had three presentation problems:

1. **Dropped rows.** The chart panel was 620 × 302 px for a 501 × 401 chart. Nearest
   resampling dropped 99 of the 401 chart rows, so 4,516 corridor cells and **18 of 302
   corridor records** never reached the screen, contradicting "every corridor is drawn". The
   chart is now 626 × 502 px (1.25× in both axes): every row and column is shown and the
   vertical squash is gone.
2. **Lineage line.** It fell below the text panel in every package frame and was never
   visible. It is now removed, so the taller panel does not display the invalid lineage
   field.
3. **Overview.** It showed six consecutive near-identical `worldMap` states. It now takes the
   best frame per target and uses area-averaged thumbnails.

No lift file or measurement changed. The package's own demo is kept at
`previews/partition-graph-3-full/demo-package-original/`.

## 1. Integrity

| | |
|---|---|
| causal joint states written | **104** (all with a map); 25 objects |
| exact `seen_any` replay | **51 checkpoints, 0 mismatches**; every historical `cyclopean_decision` (26 epistemic hand-offs + 25 terminal stops), covering all 25 targets; saved `NEVER_OBSERVED` 95,226–196,880 of 200,901 cells, reproduced exactly |
| cell-side interfaces | 569,730 raster = 569,730 encoded; **`unencoded_interface_edges == 0` in all 104 states** |
| boundary chains / branch vertices | 12,050 / 2,585 over all states |
| dual vs raster | in every state the set of dual region pairs equals the set of 4-adjacent raster region pairs; **0** isolated BASE nodes |
| read paths | 210: `manifest.json` 1, `bootstrap/seeds.json` 1, `acquisitions/fix_XX/calibration.json` 104, `maps/fix_XX.npz` 104; no `evaluation_only`, `reachable_samples.npz`, `evaluation.json`, `oracle_observation.npz` or EXR path |

The replay is exact for a structural reason. The controller's `raw_support_L/R` is
`fsg_stereo.support_mask(c, r, side)` cropped to the rectified core
(`classroom_oracle1_matcher.compute`), which is purely geometric. Its evidence is created
fresh per target (`epistemic.make_evidence()` inside the per-object loop). The replay calls
the same function through `fov3d.stereo.core`.

The official lift was run under `strace -f -e openat,open,execve`. It opened exactly the 210
source files above and nothing else under the run, made one `execve` (the venv Python) and
opened no Blender file. The only sealed modules it loaded were `tools/fsg_stereo` and its
dependency `tools/fsg_geometry`, through the `fov3d.stereo.core` facade. No matcher,
controller, epistemic, frontier, fusion or renderer module was loaded. Summary flags:
`posthoc_only`, `controller_executed: false`, `blender_launched: false`,
`dense_truth_opened: false`, `object_identity_inherited: true`.

## 2. Corrected digital topology

- **BASE under 4-connectivity (scene-final):** 38 regions, 10 touching the chart border,
  32,892 cells (16.4 % of the chart); the largest has 14,773 cells. Over the 104 states the
  count runs 2–40 (median 10).
- **The 32 Phase-2 edge-less BASE cases disappear.** Applying the exact cell-side interface
  enumeration to Phase 2's own 104 per-target rasters, all 292 Phase-2 BASE regions have at
  least one cell-side interface, and 0 have none. The 32 isolated nodes were an artefact of
  assigning one BASE label per contour. Phase 3 has none in any state.
- **Chains (scene-final):** 213 chains over 190 region pairs (23 parallel), 36 branch
  vertices, 9,243 interface edges. Over all states: 12,050 chains over 10,374 region pairs
  (1,676 parallel).
- **Boundary kinds (scene-final):** 139 `OBJECT_OBJECT` and 74 `OBJECT_BASE` chains.

## 3. Joint scene partition (scene-final)

- **Objects and regions:** 25 objects in 71 regions.
- **Regions per object:**

  | regions | 1 | 2 | 3 | 5 | 6 | 9 | 14 |
  |---|---|---|---|---|---|---|---|
  | objects | 13 | 4 | 2 | 3 | 1 | 1 | 1 |

  The multi-region objects are alphabet 14, blackBoard_upPart 9, wall.008 6, Text 5,
  blackBoardLamp 5, ceilingMoulding 5, lettersPlank 3, woodBase 3, and 2 each for plank, sol,
  woodBaseboard and worldMap.
- **Object–object boundaries:** 40 object pairs share one. The 139 chains have a chain-median
  range jump of min 0.001 / median 0.031 / P90 0.175 / max 0.422 m.

| object pair | chains | interface edges | median jump (m) | nearer votes |
|---|---|---|---|---|
| 109 alphabet \| 166 lettersPlank | 24 | 579 | 0.0014 | 303 : 276 |
| 166 lettersPlank \| 210 wall.008 | 2 | 488 | 0.0052 | 413 : 75 |
| 107 Text \| 167 lettersPlank.001 | 11 | 304 | 0.0022 | 157 : 147 |
| 111 blackBoard \| 115 boardFrame | 1 | 279 | 0.0151 | 0 : 279 |
| 210 wall.008 \| 234 worldMap | 3 | 267 | 0.0404 | 122 : 145 |
| 201 verticalPipe \| 234 worldMap | 2 | 252 | 0.1567 | 252 : 0 |
| 112 blackBoardLamp \| 114 blackboardLamp | 5 | 207 | 0.0460 | 120 : 87 |
| 224 woodBase \| 225 woodBaseboard | 3 | 194 | 0.0039 | 41 : 153 |
| 178 sol \| 225 woodBaseboard | 3 | 193 | 0.0139 | 160 : 33 |
| 113 blackBoard_upPart \| 210 wall.008 | 7 | 192 | 0.0483 | 192 : 0 |
| 201 verticalPipe \| 224 woodBase | 2 | 191 | 0.2206 | 102 : 89 |
| 112 blackBoardLamp \| 113 blackBoard_upPart | 12 | 171 | 0.0496 | 171 : 0 |
| 201 verticalPipe \| 210 wall.008 | 4 | 103 | 0.1763 | 103 : 0 |

Nearer votes are listed in the pair's order.

**Angular overlap.** 16,793 cells (8.4 % of the chart) have `overlap_count > 1`: 15,891
two-way, 580 three-way and 322 four-way. **All 16,793 are resolved by a strictly nearer
reconstructed range; the instance-id tie-break never fired (0 exact ties).** Recomputing
every object's final support layer from its last map reproduces the saved owner raster
exactly. The winning margin has median 3.0 cm, P90 21.7 cm and maximum 48.7 cm, but
**4,283 cells (25.5 %) are decided by less than 1 cm**. Margins are strongly
pair-dependent:

| front ← behind | cells | median margin | share < 1 cm |
|---|---|---|---|
| lettersPlank ← wall.008 | 1,757 | 1.2 cm | 40 % |
| boardFrame ← blackBoard | 1,127 | 1.5 cm | 3 % |
| verticalPipe ← worldMap | 1,056 | 17.3 cm | 0 % |
| verticalPipe ← woodBase | 816 | 17.9 cm | 0 % |
| blackBoardLamp ← blackBoard_upPart | 790 | 15.3 cm | 0 % |
| lettersPlank ← alphabet | 730 | **0.22 cm** | **100 %** |
| woodBaseboard ← woodBase | 620 | 0.95 cm | 58 % |
| plank ← woodBase | 511 | 0.78 cm | 73 % |

## 4. True topology lineage (excluding initialization)

| | births | merges | splits | deaths |
|---|---|---|---|---|
| package summary field (**invalid**, see above) | 191 | 0 | 0 | 185 |
| corrected, joint-partition components | **10** | **3** | **0** | **1** |
| corrected, each target's own support components | **7** | **2** | **0** | **0** |

The own-support rasters are bit-identical to Phase 2's supports in 104/104 states. Their
lineage reproduces Phase 2's post-hoc finding exactly: 7 births and 2 merges, and no
split. The "splits" Phase 2 first reported were births. Under the joint partition there are
still no splits. The extra 3 births, 1 merge and 1 death come from the frontmost rule, as
earlier nearer objects cut a target's growing support:

| target | joint components per fixation | corrected joint events | own-support events |
|---|---|---|---|
| 166 lettersPlank | 4, 3, 3, 3 | birth 1, merge 1, death 1 | none (1 own component) |
| 178 sol | 1, 2, 1, 2, 2, 2 | birth 2, merge 1 | birth 2, merge 1 |
| 210 wall.008 | 2 ×4, 3 ×2, 4 ×2, 5 ×4, 6 ×7 | birth 4 | birth 2 |
| 224 woodBase | 2 ×9, 3, 4, 4, 3 ×7 | birth 2, merge 1 | birth 2, merge 1 |
| 234 worldMap | 1, 2 ×6 | birth 1 | birth 1 |

## 5. Local gap corridors

The package emits one corridor per pair of the target's **joint** components. That unit
mixes two things:

- **ownership cuts:** both joint components lie in one connected component of the target's
  own support, which was cut only because a nearer object won the overlap cells;
- **own-support gaps:** the two pieces are separated in the target's own map, as in Phase 2.

A Phase-2-comparable unit is also given: one bridge per pair of own-support components,
taking the closest joint corridor between them. There are 30 such pairs in both contexts,
the same 30 pairs as Phase 2.

### Package unit (all joint-component pairs)

| | causal object-final | scene-final |
|---|---|---|
| corridors / targets | 86 / 10 | 182 / 12 |
| ownership cuts / own-support gaps | 42 / 44 | 73 / 109 |
| endpoint gap min / median / P90 / max (°) | 0.19 / 1.99 / 8.58 / 22.95 | 0.19 / 2.05 / 7.45 / 23.12 |
| interior cells (total) | 3,295 | 5,963 |
| interior BASE / same-object / other-object | 27.6 % / 43.1 % / 29.3 % | 1.1 % / 28.9 % / 70.0 % |
| crossing a mapped other object | 47 | 176 |
| pure BASE / pure other-object | 16 / 18 | 5 / 71 |
| crossing another component of the same object | 45 | 105 |
| containing historically unseen cells | **1** (24 cells) | **0** |
| seen share of interior cells | 99.27 % | 100 % |
| with an intervener reconstructed after the target | 0 | 162 |

Corridors per target:

- causal: alphabet 15, blackBoard_upPart 45, ceilingMoulding 1, lettersPlank 3, plank 1,
  sol 1, wall.008 15, woodBase 3, woodBaseboard 1, worldMap 1;
- scene-final: Text 10, alphabet 91, blackBoardLamp 10, blackBoard_upPart 36,
  ceilingMoulding 10, lettersPlank 3, plank 1, sol 1, wall.008 15, woodBase 3,
  woodBaseboard 1, worldMap 1.

Interveners (number of corridors):

- causal: blackBoardLamp 35, verticalPipe 11, lettersPlank 5, alphabet 4, boardFrame 4,
  coat 1 2, blackBoard_upPart 2, blackBoard 1, blackboardLamp 1;
- scene-final: lettersPlank 96, blackBoardLamp 33, wall.008 29, blackboardLamp 19,
  boardFrame 17, verticalPipe 16, lettersPlank.001 10, pipe 9, blackBoard_upPart 5,
  alphabet 4, worldMap 4, coat 1 2, blackBoard 1.

### Phase-2-comparable unit (30 own-support component pairs)

| | causal object-final | scene-final |
|---|---|---|
| pure BASE / pure other-object / mixed | **12 / 5 / 13** | **4 / 14 / 12** |
| bridges containing any BASE cell | 25 | 6 |
| bridges crossing another object | 8 | 26 |
| bridges with unseen cells | 1 | 0 |
| gap min / median / P90 / max (°) | 0.20 / 1.82 / 8.45 / 14.83 | 0.20 / 1.82 / 8.79 / 15.23 |

Class changes from the causal to the scene-final context:

- 8 pure BASE → pure other-object;
- 1 mixed → pure other-object;
- 4 pure BASE and 5 pure other-object unchanged;
- 12 mixed stay mixed: the 10 alphabet pairs change composition (BASE + same-object →
  same-object + lettersPlank), and the 2 woodBase pairs are unchanged.

20 of the 30 pairs gain an intervener that was reconstructed after the target finished.

| target, own pair | causal bridge | scene-final bridge |
|---|---|---|
| 109 alphabet, 15 pairs | 5 pure BASE (0.39–0.49°, 3–4 cells), 10 BASE + same-object (1.85–8.27°) | 5 pure lettersPlank, 10 same-object + lettersPlank |
| 113 blackBoard_upPart [1,2] | 1.33°, 12 cells, all blackBoardLamp | 12 cells: blackBoardLamp 10, blackboardLamp 2 (later) |
| 123 ceilingMoulding [1,2] | 0.76°, 7 cells BASE | 1.60°, 16 cells verticalPipe (later) |
| 174 plank [1,2] | 1.00°, 9 cells BASE | 1.60°, 15 cells verticalPipe (later) |
| 178 sol [1,2] | 0.29°, 2 cells BASE | same |
| 210 wall.008 [1,2] | 1.80°, 17 cells verticalPipe | same |
| 210 wall.008 [1,3] | **12.33°, 122 cells BASE, 24 unseen** | 13.20°, 131 cells worldMap (later), 0 unseen |
| 210 wall.008 [1,4] | 14.83°, 146 cells: verticalPipe 113, lettersPlank 30, BASE 3 | 15.23°, 150 cells: verticalPipe 117, lettersPlank 30, worldMap 3 |
| 210 wall.008 [2,3] | 2.11°, 19 cells: verticalPipe 12, lettersPlank 7 | 2.34°, same interveners |
| 210 wall.008 [2,4] | 1.84°, 17 cells BASE | same |
| 210 wall.008 [3,4] | 1.63°, 16 cells verticalPipe | same |
| 224 woodBase [1,2] | 0.20°, 1 cell BASE | same |
| 224 woodBase [1,3] | 1.50°, 14 cells: verticalPipe 13, BASE 1 | same |
| 224 woodBase [2,3] | 10.02°, 100 cells: same-object 83, verticalPipe 15, BASE 2 | same |
| 225 woodBaseboard [1,2] | 0.39°, 3 cells BASE | same |
| 234 worldMap [1,2] | 1.80°, 17 cells verticalPipe | same |

## 6. Does the local relation discriminate?

**Partly.** Discrimination depends on the axis and on the context.

- **Object versus BASE, causal context: yes.** Phase 2's shared-BASE relation held for 30/30
  pairs through one exterior region covering 77–99.7 % of the chart. The local bridge splits
  the same 30 pairs into 12 pure BASE, 5 pure other-object and 13 mixed. Bridge lengths vary
  from 1 to 146 interior cells and gaps from 0.20° to 14.8°. The package unit shows the same
  spread (47 of 86 cross another object, 16 pure BASE, 18 pure other-object).
- **Epistemic axis (seen versus unseen): no, saturated.** 29/30 causal bridges (85/86
  corridors) lie entirely in historically SEEN territory, and none contains unseen cells in
  the scene-final context. The bridges join nearby parts of a target's own map, and the
  supported rectified cores of that target's own fixations cover its neighbourhood. In this
  run the fragments are therefore almost never separated by territory the controller did not
  look at. They are separated by looked-at territory where no target surfel was fused. The
  one exception is `wall.008` [1,3] (24 of 122 cells unseen).
- **Scene-final context: drifts toward saturation on "other object".** 26/30 bridges (176/182
  corridors) cross another object, and BASE falls to 1.1 % of corridor cells. There are two
  mechanisms:
  1. objects reconstructed later fill gap territory (20/30 pairs gain a later intervener);
  2. the frontmost owner rule creates components by itself (73/182 scene-final and 42/86
     causal corridors are ownership cuts). The corridor then crosses the winning object
     largely by construction.
- **Depth-order attributes separate cases that occupancy alone does not.** Bridges occupied
  by `verticalPipe` sit on object–object boundaries with 16–22 cm median jumps and almost
  one-sided nearer votes. For example, 252:0 against `worldMap` and 103:0 against
  `wall.008`, though 102:89 against `woodBase`. Bridges occupied by `lettersPlank` against
  `alphabet` sit on a boundary with a 1.4 mm median jump and 303:276 votes, where overlap
  ownership was decided by a median 2.2 mm margin. The reconstruction does not order these
  two surfaces.

## 7. Examples (selected from Phase-3 graph quantities only)

- **`wall.008` [1,3].** The longest causal pure-BASE bridge (12.33°, 122 cells) and the only
  bridge with unseen cells (24). In the scene-final context the same pair is bridged entirely
  by `worldMap` (131 cells). That is retrospective information: `worldMap` was reconstructed
  after `wall.008` terminated. The `wall.008 | worldMap` boundary has a 4.0 cm median jump
  with split votes (122:145).
- **`worldMap` [1,2], `wall.008` [1,2] and [3,4].** 16–17-cell bridges occupied entirely by
  `verticalPipe`, an earlier object, so this holds in both contexts. The target–pipe
  boundaries have 15.7–17.6 cm median jumps and 100 % nearer votes for the pipe. This is the
  cleanest "nearer mapped object in the gap" configuration in the run.
- **`blackBoard_upPart`.** 2 own components become 10 joint components (45 corridors, 36 of
  them ownership cuts by `blackBoardLamp`). The own-pair bridge is 12 cells of
  `blackBoardLamp`, on a boundary with a 5.0 cm median jump and 171:0 votes.
- **`alphabet`.** In the causal context, all 15 bridges are BASE or pass through other
  `alphabet` components. In the scene-final context, all 15 involve `lettersPlank` (later)
  through a near-coplanar ownership decision (see §6), so `alphabet` grows to 14 joint
  regions.
- **The four scene-final pure-BASE bridges:** `sol` (0.29°, 2 cells), `woodBase` [1,2]
  (0.20°, 1 cell), `woodBaseboard` (0.39°, 3 cells) and `wall.008` [2,4] (1.84°, 17 cells).
  Each is seen, yet no reconstructed object claims it.

## 8. Interpretation boundary

- Other-object occupancy of a corridor is not an occlusion proof. The owner is the nearest
  *reconstructed* 12 mm support, and 25.5 % of overlap cells are decided by less than 1 cm.
- Unseen BASE is not object continuation, and seen BASE does not rule continuation out.
  BASE here means "no reconstructed object claims this cell".
- Scene-final interveners may be objects the historical target controller had not yet
  reconstructed (162/182 corridors, 20/30 own pairs). Only the causal context is information
  the controller could have had.
- Object identity is inherited from Oracle-1. Phase 3 groups components by the saved target
  maps and discovers no identity.
- `seen_any` is per-target evidence, replayed exactly. It says a supported rectified core
  pixel looked there, not that target depth was valid there.

## Answer to the core question

Joint local topology plus exact epistemic evidence gives a vocabulary that Phase 2 lacked.
Each gap between fragments of one object now has:

- a length;
- occupancy by BASE, an earlier mapped object, a later mapped object or the object's own
  other pieces;
- a depth order and jump across the object–object boundary it crosses;
- a seen/unseen composition.

In the causal context that vocabulary separates the 30 fragment pairs into several distinct
configurations. Three qualifications must be settled before it drives attention:

1. The ownership-cut versus own-support-gap distinction has to be first-class. Otherwise
   the frontmost rule manufactures "other object in the gap" relations.
2. Depth-order confidence is needed. Near-coplanar ownership, as between `lettersPlank` and
   `alphabet`, should not count as an intervening object.
3. In this run `seen_any` is almost always SEEN inside corridors, so it cannot tell gaps
   apart.

## Demo inventory and inspection

Lift output `previews/partition-graph-3-full/` (99 MB):

- `summary.json`, `causal-final-corridors.json`, `scene-final-corridors.json`;
- `states/global_000…103/`: `scene-model/{graph.json, arrays.npz}`, `state.npz` (owner,
  owner depth, overlap count, region codes, the target's `seen_any` and its own support) and
  `corridors.json`;
- `demo/`:
  - 104 four-panel frames, 1252 × 1120;
  - `partition-graph-3-demo.mp4` (mpeg4, 104 frames at 4 fps, 26 s; all frames decode and
    match the PNGs within codec error, mean absolute difference 2.6–3.4 / 255);
  - `overview.png` (1252 × 1680);
  - `Demo.md`;
- `demo-package-original/`: the unrepaired package demo.

Inspected: frames 2 (`alphabet`, 6 components, 15 corridors), 21 (`blackBoard_upPart`, 10
components, first frame with object–object boundaries), 52 (`wall`, middle, 1 component),
74 (`wall.008` final, 6 components, 1 corridor with unseen cells) and 103 (final state), plus
`overview.png` and the MP4. Confirmed:

- positive pitch is up (`sol` at the bottom, `ceilingMoulding` at the top);
- the `seen_any` panel carries an explicit `dark=UNSEEN | green=SEEN` key;
- the text panel values match `summary.json`;
- programmatically, every one of the 16,792 corridor cells across all 302 corridor records
  is drawn red in the repaired frames.

Supplementary read-only analysis is in `previews/partition-graph-3-analysis/`
(`analyze_pg3.py`, `analysis.json`, `lift.strace`). It reads only the Phase-3 and Phase-2
lift outputs, plus the source run's controller-time `maps/fix_XX.npz` for the overlap
recomputation, through a guard that rejects truth, EXR and oracle-observation paths. It
computes:

- the corrected lineage (the contract's overlap definition applied to the target
  component rasters rebuilt from `region_code`);
- the own-support connectivity of each corridor's two regions (8-connected components of
  the saved `current_target_support`, or of the recomputed final layer for scene-final);
- the Phase-2 exact-interface re-check;
- the overlap margins.

## Immutability

After this commit the only changes relative to `3fb0f7d` are this report and the demo-only
repair of `tools/partition_graph3_demo.py`. Relative to the consolidated baseline `6c8a80f`,
every other changed path is a Phase-1/2/3 addition. The sealed `tools/*` engine, `fov3d`
facade wrappers, `tests/golden/`, `scripts/` and scene manifests are byte-identical. The
baseline verifier, the three partition checkers and the smoke comparator were re-run after
the report was written. `previews/` stays untracked.

## Recommendation for Phase 4 (not implemented)

1. Fix `_lineage` so it compares in one code space, and make lineage a checked invariant: a
   stable single component must give 0 events.
2. Make each same-object pair carry an explicit `ownership_cut` versus `own_support_gap`
   label, derived from the target's own support.
3. Attach a depth-order confidence to object–object boundaries (jump magnitude and vote
   balance) and to overlap ownership margins. Treat sub-centimetre, split-vote cases as
   unordered.
4. Look for an epistemic signal finer than `seen_any` that can be replayed exactly within
   the truth-isolation contract. In this run `seen_any` does not discriminate inside
   corridors. Only then design an attention rule over the vocabulary.
