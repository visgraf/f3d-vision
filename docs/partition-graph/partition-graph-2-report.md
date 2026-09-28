# Partition-Graph Phase 2 — retrospective Classroom lift report (2026-09-25)

The contract is `docs/partition-graph-2.md`, committed by the apply script in `9dca271`
"Add retrospective Classroom partition lift" on `f04c75e` (Phase 1). This phase is a
post-hoc representation experiment: the saved Classroom-Oracle-1 trajectory is re-expressed
as one partition/dual graph per fixation. No gaze was selected, no controller, matcher,
fusion, renderer, stereo, scene, signature or script file was changed, and no mechanical
repair was needed.

## Starting state and package

| | |
|---|---|
| branch | `architecture/partition-graph-2`, tracking `origin/architecture/partition-graph-2` |
| package commit | `9dca271` on `f04c75e`; the only commit after Phase 1 |
| package files | all 12 committed files byte-identical to `~/Downloads/partition-graph-2.zip`; the zip's `PARTITION_GRAPH2_CODE_PROMPT.md` was not committed |
| diff `f04c75e..9dca271` | Phase-1 files hardened (`fov3d/scene/{__init__,model,synthetic}.py`, `tools/dev/check_partition_graph1.py`, `tools/partition_graph1_demo.py`) and new Phase-2 files (`fov3d/experiments/classroom_partition/{__init__,lift}.py`, `tools/partition_graph2_{lift,demo}.py`, `tools/dev/check_partition_graph2.py`, `docs/partition-graph-2.md`); nothing else |
| mechanical repair | none; the package ran unchanged against the live API |

## Gates

| gate | result |
|---|---|
| `py_compile` of `fov3d/scene/*.py`, `fov3d/experiments/classroom_partition/*.py` and the three Phase-2 tools | OK |
| `tools/dev/check_partition_graph2.py` | `SUMMARY checked=16 failed=0` |
| `tools/dev/check_partition_graph1.py` (now expects format v2) | `SUMMARY checked=13 failed=0` |
| `scripts/verify_baseline.sh` | `passed=9 failed=0`; 61 tracked `.py` compiled; 31 files at `baseline-classroom-oracle1-2026-09-25` byte-identical |
| `tools/dev/check_fov3d_facade.py` | `SUMMARY checked=16 failed=0` |
| `git diff --check` (worktree and `f04c75e..HEAD`) | clean |
| golden smoke `previews/partition-graph-2-golden-smoke` | 5 looks, 68 NPZ arrays, 4 targets, `truth_opened_during_control: false`, **`MISMATCHES 0`** |

Phase-1 demo regenerated into `previews/partition-graph-2-pg1-demo/` (the Phase-1 evidence
directory was left untouched). The SVG dual panel now contains the `base` node with its two
edges to A₁ and A₂, and `Demo.md` uses `./.venv/bin/python`. Text is **not** fully
unclipped: the monospace `summary:` line still runs past the 1280 px canvas, and the blue
"one object hypothesis A groups disconnected regions" caption touches the footprint box.
Cosmetic; not repaired.

## Source run

`previews/partition-graph-2-source-full` did not exist, so it was generated fresh with
`scripts/run_golden.sh` (17:12:49 → 17:23:37 including evaluation).

| | |
|---|---|
| runner | `COMPLETE {"fixations": 104, "objects": 25, "smoke": false, "terminations": {"attention_complete": 25}}` |
| evaluator | coverage 0.8746927 (25,618 / 29,288) — used only by the comparator, never by the lift |
| comparator | looks 104, NPZ arrays 1,348, RGB excluded 337, targets 25; action sources `oracle_seed` 25, `fsg6f` 53, `cyclopean_epistemic` 26; `watchdog_24` 0; `truth_opened_during_control: false`; **`MISMATCHES 0`** |

## Truth isolation audit

The lift read exactly 210 files from the source run, all through its path logger
(`summary.json` → `read_paths`):

| path pattern | files |
|---|---|
| `manifest.json` | 1 |
| `bootstrap/seeds.json` | 1 |
| `objects/instance_XXXX/acquisitions/fix_XX/calibration.json` | 104 |
| `objects/instance_XXXX/maps/fix_XX.npz` | 104 |

No path contains `evaluation_only`, `reachable_samples.npz` or `evaluation.json`, although
`evaluation.json` and `bootstrap/evaluation_only/{manifest.json,reachable_samples.npz}`
exist in the source run. No `.exr`, `oracle_observation.npz`, `result.json` or trajectory
file was read.

An independent OS-level trace (`strace -f -e openat,open,execve` on a rerun of the lift into
a scratch directory) opened the same 210 source files and nothing else under the run. It
made one `execve` (the venv Python), opened no Blender/`bpy` file and loaded no sealed
`tools/*` module. Importing `fov3d.experiments.classroom_partition` loads only `fov3d`,
`fov3d.experiments`, `fov3d.scene.*` and the lift. The rerun's JSON outputs were
byte-identical to the official lift, so the lift is deterministic. Summary flags:
`posthoc_only: true`, `controller_executed: false`, `blender_launched: false`,
`dense_truth_opened: false`. Every map snapshot is target-only: 7,923,742 surfels, 0 with
`instance_id` ≠ target.

## What one lifted graph is

For target *T* at fixation *k* the lift builds a partition of the controller's
yaw/pitch chart (−25…25° × −20…20°, 0.10° grid, 501 × 401 = 200,901 cells). It uses the same
head-frame angles as `classroom_oracle1_epistemic.angular_coordinates`:

- **Target components.** `maps/fix_k.npz` surfels, each dilated by the angular size of the
  12 mm association radius at its own range, then 8-connected components.
- **BASE regions.** 8-connected components of the complement. BASE means "not *this*
  target's support": other Classroom objects lie inside BASE. Each graph is a per-target
  partition, not a joint scene partition.
- **Boundary chains and dual edges.** One chain per OpenCV contour of each component,
  attached to the BASE label holding the majority of that contour's 8-neighbours.
- **Observation overlay.** Left and right footprints of fixations 0…*k* of *T* only. Each
  footprint is the full 320 × 320 raw image quad (29.4° field of view), not the 12°
  rectified core that the controller's `seen_any` evidence uses. The ±31.5 mm eye-centre
  offset is ignored and the polygons are filled with straight edges in the chart. Here
  "binocular" therefore means "inside both acquired tangent-plane footprints", not
  "stereo-matched".
- **Identity.** Components are grouped under *T* because the saved map belongs to *T*. The
  identity is inherited from Oracle-1; Phase 2 discovers none.

The package's merge/split events compare component **counts** between consecutive
fixations. The diagnostics below also track components by cell overlap.

## Results (all 25 objects)

### Graphs written

**104** fixation graphs, one per fixation of the 104-fixation run. All 25 targets have a
map at every fixation.

### Final target component counts

| components at final fixation | 1 | 2 | 3 | 4 | 6 |
|---|---|---|---|---|---|
| targets | 16 | 6 | 1 | 1 | 1 |

**9 of 25 targets end in more than one spherical component.** Six end with 2
(`blackBoard_upPart`, `ceilingMoulding`, `plank`, `sol`, `woodBaseboard`, `worldMap`), one
each with 3 (`woodBase`), 4 (`wall.008`) and 6 (`alphabet`). Over all 104 graphs the counts
are 1: 49, 2: 31, 3: 14, 4: 9, 6: 1, so 55 of 104 graphs are multi-component.

The components are not slivers. The smallest component of any final multi-component target
has 99 cells / 200 surfels (`ceilingMoulding`). The minimum angular gaps between components
range from 0.2° to 14.5°. Several are only 2–5 cells wide, so the counts depend on the
support-dilation rule.

| target | final components: cells / surfels | pairwise minimum gaps (°) |
|---|---|---|
| 109 alphabet | 253/183, 240/167, 218/135, 212/146, 154/117, 109/74 | 0.4, 0.5, 0.5, 0.5, 0.5, 1.9, 2.4, 2.8, 2.9, 4.2, 4.8, 5.2, 6.6, 7.1, 8.6 |
| 113 blackBoard_upPart | 801/1,489; 572/331 | 0.4 |
| 123 ceilingMoulding | 571/1,401 (edge); 99/200 (edge) | 0.8 |
| 174 plank | 1,518/5,381; 1,087/3,490 | 1.0 |
| 178 sol | 9,466/34,754 (edge); 1,776/5,499 | 0.3 |
| 210 wall.008 | 18,110/65,114 (edge); 15,700/61,888 (edge); 5,780/23,698; 650/1,767 | 0.9, 0.9, 1.8, 1.8, 12.4, 14.5 |
| 224 woodBase | 20,695/89,787 (edge); 14,640/66,102 (edge); 9,661/37,805 | 0.2, 0.9, 9.7 |
| 225 woodBaseboard | 1,723/5,678; 1,709/5,103 | 0.4 |
| 234 worldMap | 16,747/76,082; 1,254/3,269 | 0.9 |

"edge" means the component touches the chart border.

### Topology merge/split events

Package, by count: **2 merges and 7 splits** (plus 25 `initial` and 70 `stable`). All nine
events occur in four targets:

| target | components per fixation | count events | overlap events |
|---|---|---|---|
| 178 sol | 1, 2, 1, 2, 2, 2 | split 2, merge 1 | birth 2, merge 1 |
| 210 wall.008 | 2 ×6, 3 ×6, 4 ×7 | split 2 | birth 2 |
| 224 woodBase | 2 ×9, 3, 4, 4, 3 ×7 | split 2, merge 1 | birth 2, merge 1 |
| 234 worldMap | 1, 2 ×6 | split 1 | birth 1 |

By cell overlap between consecutive fixations, **every "split" is a birth**: a new
component that overlaps no previous one, i.e. new geometry acquired at a separate place.
No existing component ever broke apart (0 overlap splits, 0 vanishings). Overlap totals
equal count totals, so no count-stable fixation hides a simultaneous merge and birth.

### Connected BASE regions

| | |
|---|---|
| final graphs, total | 57 BASE regions: 32 exterior (touch the chart border), 25 enclosed |
| final, regions per target | 1: 18 targets; 3: 3; 4: 1; 7: 1; 8: 1; 11: 1 |
| final, exterior per target | 1: 23; 4: 1 (`ceilingMoulding`); 5: 1 (`wall.008`) |
| final, enclosed per target | 0: 19; 2: 4 (`Text`, `alphabet`, `wall.008`, `woodBaseboard`); 7: 1 (`sol`); 10: 1 (`woodBase`) |
| all 104 graphs | 292 BASE regions; regions per graph 1: 59, 2: 2, 3: 14, 4: 4, 5: 9, 6: 5, 7: 1, 8: 6, 9: 1, 10: 1, 11: 2 |

The 25 final enclosed regions each border exactly one target component: they are holes,
never shared between two components. All 2,136 of their cells are binocular in the lift
overlay, meaning they lie inside territory the target's own fixations imaged. 18 of the 25
are 1–3 cells (≤ 0.3°), plausibly raster or dilation pinholes. The seven larger ones are:

- `wall.008`: 1,068 and 881 cells;
- `woodBase`: 117 and 10;
- `sol`: 16;
- `Text`: 12 and 5.

What occupies an enclosed hole — a real hole, a nearer object, a depth-invalid patch or a
dilation gap — cannot be determined here without truth or other targets' maps.

### Same-object disconnected-component pairs and shared BASE neighbours

| | final graphs | all 104 graphs |
|---|---|---|
| same-object component pairs | **30** (alphabet 15, wall.008 6, woodBase 3, six targets with 1) | 142 |
| pairs sharing ≥ 1 BASE neighbour in the dual graph | **30** | 142 |
| … sharing an **enclosed** BASE region | **0** | 0 |
| … sharing only the exterior BASE | 30 | 142 |

A recount from raster adjacency instead of dual edges gives the same 30. The shared
neighbour is always the single dominant exterior BASE region of that target (`base:c001`).
It covers 155,762–200,200 of the 200,901 chart cells, i.e. 77.5–99.7 % of the chart. As
defined, the shared-BASE query is saturated in this run: it holds for every pair and so
does not discriminate between pairs.

### Observation composition of the shared BASE regions

There are 9 unique shared BASE regions, one per multi-component target, all exterior, with
1,679,846 cells in total. Enclosed shared regions: none.

| | unobserved | left-only | right-only | binocular |
|---|---|---|---|---|
| all 9, cells | 917,366 | 28,231 | 17,934 | 716,315 |
| all 9, share | 54.6 % | 1.7 % | 1.1 % | 42.6 % |

| target | unobserved | left-only | right-only | binocular |
|---|---|---|---|---|
| 109 alphabet | 66.8 % | 2.0 % | 1.8 % | 29.5 % |
| 113 blackBoard_upPart | 68.9 % | 0.0 % | 2.0 % | 29.1 % |
| 123 ceilingMoulding | 76.3 % | 1.4 % | 1.5 % | 20.8 % |
| 174 plank | 52.1 % | 2.5 % | 0.0 % | 45.5 % |
| 178 sol | 51.6 % | 2.1 % | 0.1 % | 46.3 % |
| 210 wall.008 | 16.6 % | 1.6 % | 2.3 % | 79.5 % |
| 224 woodBase | 26.9 % | 0.6 % | 0.0 % | 72.4 % |
| 225 woodBaseboard | 64.8 % | 1.8 % | 1.8 % | 31.6 % |
| 234 worldMap | 52.9 % | 3.1 % | 0.0 % | 44.0 % |

Because each shared region is essentially "the chart minus the target", these fractions
measure how much of the 50° × 40° chart the target's own fixations imaged. They say nothing
about the local territory between two components. The long 19-fixation trajectories
(`wall.008`, `woodBase`) imaged the most. Monocular strips stay small (≤ 3.1 %).

### Clearest graph examples (selected from graph quantities only)

| target | why | frame |
|---|---|---|
| 224 woodBase | most final BASE regions (11: 1 exterior + 10 enclosed), most dual edges (15), birth, birth, merge over 19 fixations | `frame_0094.png` (fix 18) |
| 210 wall.008 | monotone growth 2 → 3 → 4 components by two births; exterior complement cut into 5 border regions; 6 pairs | `frame_0074.png` (fix 18) |
| 178 sol | only birth → merge → birth sequence (1, 2, 1, 2, 2, 2); BASE count up to 10 | `frame_0040.png`, `frame_0041.png` (fix 1–2) |
| 109 alphabet | most components in one graph (6) and most pairs (15) from a single fixation; compact components of similar size (109–253 cells) | `frame_0002.png` (fix 0) |
| 234 worldMap | one clean birth (1 → 2 at fix 1), stable for the next five fixations | `frame_0098.png` (fix 1) |

## Representation fidelity diagnostics

These come from the lift output only, via `previews/partition-graph-2-analysis/analyze_lift.py`
(read-only; reproduced bit-exactly):

- **Missing dual edges.** Raster 8-adjacency has 383 unique (component, BASE) pairs; the
  dual graph has 351, with 0 extra and 32 missing. The 32 missing pairs correspond to 32
  BASE regions with **no dual edge at all**, in 19 graphs. All are small exterior border
  regions (1–1,823 cells, median 4) cut off where a target reaches the chart border:
  `ceilingMoulding` fix 0 (3), `sol` fix 3–4 (1 each), `wall.008` fix 3–18 (1–4 each). The
  cause is the one-BASE-label-per-contour assignment. It leaves `wall.008`'s and
  `ceilingMoulding`'s final dual graphs with isolated BASE nodes. The shared-pair counts are
  unaffected (raster recount: 30).
- **Parallel dual edges.** 423 chains over 351 region pairs gives 72 parallel edges (33 to
  exterior BASE, 39 to enclosed). OpenCV traces holes as 4-connected while the lift labels
  BASE as 8-connected, so several contours can land on one BASE region.
- **Connectivity sensitivity.** The target and BASE are both 8-connected, which is not a
  topologically dual pair. Labelling BASE 4-connected would give 364 regions instead of
  292 (+25 %), and the count would differ in 25 of 104 graphs.
- **Overlap events.** 7 births and 2 merges, with no splits or vanishings, as reported
  above.

## Does the partition/dual view reveal what the one-ring shoreline did not?

The old state (`classroom_oracle1_epistemic.audit`) consists of one support raster
(median-range dilation), its complement, and an exterior mask flood-filled from the chart
border. On top of those sit the one-ring `shoreline = complement ∩ dilate3×3(support)`,
the `eligible = shoreline ∩ exterior ∩ never-observed` cells, and scalar counts. Against
that, on this run:

**Newly explicit (yes):**

1. **Target fragmentation.** 9/25 final targets and 55/104 graphs have 2–6 spherical
   components of substantial size. The old state had a single support mask with no
   component count or identity.
2. **Temporal topology.** 7 births of disconnected components and 2 merges, confined to 4
   targets. The old state kept no correspondence between fixations.
3. **Enclosed BASE faces as individual regions** with their own adjacency and observation
   composition: 25 at the final fixation, in 6 targets. The old rule treated them only as
   "not exterior" and so excluded them from eligibility wholesale. They border 397 of the
   13,254 final one-ring shoreline cells (3.0 %); over all graphs, 4,031 of 100,728 (4.0 %).
4. **Exterior fragmentation.** `ceilingMoulding` and `wall.008` cut the exterior complement
   into 4 and 5 border regions. The old exterior mask was one union.

**Not revealed (no):**

5. **The pairwise shared-BASE relation carries no information here.** All 30 final pairs
   (142 over the trajectory) share only the dominant exterior BASE. No pair shares an
   enclosed region; each enclosed region borders exactly one component. In a per-target
   partition, any two components reached from the exterior share that region by
   construction.
6. **Nothing here explains why components are disconnected.** Occlusion by a nearer
   object, physically separate parts of one mesh instance, or reconstruction gaps are all
   possible; distinguishing them needs information the lift does not have.

This comparison is structural. The lift's support uses a per-surfel radius, not the
controller's single median-range radius, so it is not a replay of the controller's own
shoreline audit.

## Interpretation limits

- Object identity is inherited from Oracle-1. Phase 2 does not infer that two components
  belong together.
- BASE is the complement of **one** target's support. Other objects are inside BASE, so a
  BASE region is not background and a shared BASE neighbour is not an occluder, a
  continuation or a hole.
- Observation footprints are acquired tangent planes: full raw 29.4° quads of that
  target's fixations only. They are separate from scene identity and from the controller's
  core-only `seen_any` evidence.
- Component counts are sensitive to narrow gaps (0.2–0.5°), the dilation rule and the 8/8
  connectivity choice.
- This is one deterministic golden run and a post-hoc description. It tunes and implies no
  policy.

## Demo inventory

Lift output `previews/partition-graph-2-full/` (117 MB):

- `summary.json`;
- per fixation, `objects/instance_XXXX/fix_XX/`: `scene-model/graph.json` (format v2),
  `scene-model/arrays.npz`, `state.npz` and `relations.json` (104 of each);
- `demo/`:
  - `frame_0000.png` … `frame_0103.png` (104 frames, 1240 × 720, four panels);
  - `partition-graph-2-demo.mp4` (mpeg4/mp4v, 104 frames at 4 fps = 26.0 s; decodes fully and matches the PNG frames within codec error, mean absolute difference 2.5–3.6 / 255);
  - `overview.png` (1280 × 1200; final frames of 109, 210, 224, 178, 123, 225);
  - `Demo.md`.

Supplementary diagnostics are in `previews/partition-graph-2-analysis/`: `analyze_lift.py`,
`analysis.json`, `analysis.txt` and `lift-rerun.strace`.

Inspected: `overview.png` and frames 0002 (alphabet), 0041 (sol merge) and 0094 (woodBase
final). The panels agree with the numbers above. Presentation issues, not repaired:

- rasters are drawn with pitch increasing downward, so the scene appears upside down
  (floor `sol` and `woodBase` at the top, `ceilingMoulding` at the bottom);
- the overlay panel has no colour key (left-only is blue, right-only orange; with converged
  eyes the right eye's frustum reaches furthest left);
- the relations panel lists at most 7 pairs (alphabet has 15).

## Immutability

The only change after `9dca271` is this report. Since the consolidated baseline `6c8a80f`
every changed path is an **addition** (14 files: the Phase-1 and Phase-2 representation,
experiment, checker, demo and doc files), and not one file tracked at `6c8a80f` was
modified. The sealed `tools/*` engine, `fov3d` facade wrappers, `tests/golden/`,
`scripts/`, `.gitignore` and scene manifests are byte-identical. `scripts/verify_baseline.sh`
passes and the smoke comparator remains `MISMATCHES 0`. `previews/` stays untracked.

## Recommendation for Phase 3 (not implemented)

1. **Fix the extraction before drawing conclusions from the dual graph:**
   - assign BASE labels per contour segment rather than per contour, so no raster-adjacent
     BASE region is left isolated;
   - adopt a topologically dual connectivity (8-connected target, 4-connected BASE) or
     report both.
2. **Replace the shared-BASE query with a local relation.** For example, the complement
   corridor between two components within their gap distance, and that corridor's
   composition taken from the controller's own evidence rasters (seen target / non-target /
   depth-valid) rather than full-quad footprints.
3. **Lift all targets into one joint partition per time step.** BASE would then exclude
   other targets, and object–object boundaries (occlusion candidates) could be expressed.
4. **Demo:** flip the raster rows so up is up, and add a colour key.
