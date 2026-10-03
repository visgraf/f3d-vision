# Natural Bootstrap-1a — Spherical Range Connectivity — report

**Marker.**

    NATURAL_BOOTSTRAP1A_RANGE_CONNECTIVITY_COMPLETE

**Status: REVIEW PENDING.** Luiz and Chat review coherence, seedability and plausibility for later active
interrogation. No ACCEPTED marker is written, and the branch is not merged.

> **Question.** Can local 3-D range continuity alone turn the accepted broad spherical glance into a useful
> set of connected perceptual hypotheses and representative seed directions, without using Blender object
> identity?

**The claim is modest.** NB1a removes Blender **object identity** from bootstrap discovery. Range is a
**controlled sensory proxy**, derived from the Blender Position pass of the accepted Breadth-1 observation.
It is not natural stereo depth sensing.

Every check passed (33/33), and every corruption was caught from a passing baseline (29/29).

Contract: `docs/natural-bootstrap/nb1a-range-connectivity-contract.md`. MEASURED means produced by the runs
below; PROPOSED means the contract's untested estimates.

## Branch and commits

| item | value |
|---|---|
| branch | `natural-bootstrap/nb1a-range-connectivity`, from `main` @ `0fe83af` (Breadth-1 accepted); isolated worktree |
| contract | `f4fa2c3` *Contract NB1a spherical range connectivity* |
| implementation (frozen before the canonical discovery) | `6b63cdc` *Implement NB1a spherical range connectivity* |
| canonical run | synthetic, prepare-input, discover, freeze and evaluate, all at `6b63cdc` (clean, pushed; `process-log.jsonl`) |
| presentation fix after the discovery | `8cc368d` *NB1a figures: presentation fixes after the canonical discovery* (figures only; regenerated and checked at `8cc368d`) |
| report | this commit |

`fov3d/` is byte-identical to `0fe83af`. The changed tracked files are only the declared NB1a files and the
layout checker (checks 30–31).

## Source and truth boundary

**Scene source:**
- the accepted Breadth-1 canonical EXR
  `/home/lvelho/rd/f3d-vision/previews/breadth-1-classroom-234-spherical-glance/render/canonical.exr`,
  sha256 `4ea036fc74eab3b3ab06a0c4470c2b01740c9322de0eea522f957ddfffa172f8`, which is unchanged;
- the head origin from `seeds.json` `6ef83319…`. Only `head_origin_w_m` is read.

**No Blender process ran** (check 2): no Blender command is in the process log, and the Breadth-1 render
directory is unchanged. There is still exactly **one** Classroom observation.

The three separated paths each ran under an allowlist file-open guard (`nb1a_guard.OpenGuard`, an audit
hook). Every open is recorded.

| path | data reads | writes | violations |
|---|---|---|---|
| sensory-proxy preparation | `canonical.exr`, `seeds.json` | `input/` (2 files) | 0 |
| **discovery** | **`input/range-sensory.npz` only** | `discovery/` (6 files) | **0** |
| evaluation | the frozen products, verified first, then the EXR (Object Index), catalog, Breadth-1 summary and `rgb-sensory.npz` | `evaluation/` | 0 |

**The stripped sensory input:**
- `range-sensory.npz` holds exactly `range_m` and `valid_mask`;
- `rgb-sensory.npz` holds exactly `srgb8`;
- the manifest carries no identity, catalog, seed or label data (check 5).

Validity is Position ≠ 0: 255,758 valid cells and 3,442 without geometry. Discovery did not open RGB, the
EXR, the Object Index, the catalog, Breadth-1 products, controller files or evaluation outputs (checks 6–8).
The discovery code imports only `numpy`, `math`, `heapq` and `nb1a_spec`.

Truth classes (Visual Language 1; nothing is CONTROLLER-TIME):

| class | products |
|---|---|
| ORACLE INPUT | the RGB / range proxy |
| DERIVED | continuity graph, hypotheses, boundaries, clearance, seeds; RGB edge diagnostics |
| REFERENCE / EVALUATION | Object Index, catalog, overlap |

## The rule (frozen before the Classroom discovery)

    C_ij = ||p_i − p_j|| / (((r_i + r_j)/2) · atan2(||d_i × d_j||, d_i · d_j))
    retain iff C_ij <= C_MAX = sec(MAX_SURFACE_SLANT_DEG = 75.0°) = 3.863703305156273

Details:
- the graph is the seam-aware 8-neighbourhood (longitude wraps, latitude does not);
- hypotheses are the connected components; every component is kept;
- ids follow the canonical folded spherical support;
- the seed is the max-clearance cell: multi-source Dijkstra from boundary cells along retained edges, with
  true angular cost, and ties within 1e-12 rad going to the smaller row, then column.

The 75° parameter was not tuned. No filtering, merging, splitting or seed-rule change happened after the
discovery or the evaluation.

## Pure discovery results (MEASURED; recorded before any reference evaluation)

Discovery took 1.51 s. Freeze record: `discovery/bootstrap-freeze.json` `c0236d04…`.

| quantity | value |
|---|---|
| valid range cells | 255,758 (3,442 invalid) |
| neighbour pairs / candidate pairs | 1,034,640 / 1,017,272 |
| retained / cut continuity edges | 972,192 / 45,080 (4.4 % cut) |
| **hypotheses** | **453** |
| singletons | 137 (30.2 %) |
| hypotheses with > 1 cell | 316 (69.8 %) |
| largest hypothesis H0001 | 220,221 cells, 10.3815 sr = **82.6 % of the sphere** (above the declared top edge, 10 sr: 1 overflow) |
| largest 1 / 5 / 10 / 25 | 82.6 % / 88.0 % / 91.3 % / 94.5 % of 4π |
| zero-clearance seeds | 366: 137 singletons + 229 multi-cell hypotheses whose every cell is a boundary cell |
| no-boundary fallbacks | 0 |
| hypotheses with numerically tied seed candidates | 257 |

**Support distribution** (declared edges `10^(k/2)` sr; empty bins omitted):

| sr bin | [1e-5, 3.2e-5) | [3.2e-5, 1e-4) | [1e-4, 3.2e-4) | [3.2e-4, 1e-3) | [1e-3, 3.2e-3) | [3.2e-3, 1e-2) | [1e-2, 3.2e-2) | [3.2e-2, 0.1) | [0.1, 0.32) | ≥ 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| hypotheses | 44 | 98 | 149 | 58 | 41 | 32 | 18 | 8 | 4 | 1 |

**Cell counts**, in bins `[2^k, 2^(k+1))` from k = 0:

    137, 110, 74, 28, 22, 21, 22, 15, 10, 5, 5, 2, 1, 0, 0, 0, 0, 1

**Seed interior clearance** (degrees):
- the quantiles 0 / 1 / 5 / 25 / 50 / 75 % are all 0;
- 95 % is 1.979, 99 % is 7.831, and the maximum is 50.947 (H0001);
- among the 87 positive clearances, the declared bins from [0.25°, 0.35°) upward hold 4, 7, 17, 3, 18, 16, 5,
  4, 4, 4, 2, 2, then one at [45°, 64°).

**Median range by hypothesis** (m), at the quantiles 0 / 1 / 5 / 25 / 50 / 75 / 95 / 99 / 100 %:

    0.529, 0.828, 1.169, 1.621, 2.661, 3.570, 4.727, 5.482, 6.927

**The largest hypotheses** (DERIVED; no identity):

| id | cells | sr | % of 4π | range min / median / max (m) | clearance | seed yaw, pitch (°) | seed range (m) |
|---|---|---|---|---|---|---|---|
| H0001 | 220,221 | 10.3815 | 82.61 | 0.68 / 1.96 / 6.23 | 50.95° | 178.25, 45.75 | 2.37 |
| H0002 | 6,672 | 0.3157 | 2.51 | 0.45 / 0.53 / 0.85 | 13.10° | −49.25, −42.75 | 0.60 |
| H0003 | 2,289 | 0.1432 | 1.14 | 0.57 / 0.72 / 1.05 | 8.50° | −148.25, −36.25 | 0.68 |
| H0004 | 1,677 | 0.1134 | 0.90 | 0.57 / 0.92 / 1.18 | 11.84° | 115.75, −39.75 | 0.73 |
| H0005 | 1,572 | 0.1082 | 0.86 | 0.72 / 0.88 / 1.47 | 5.30° | −34.25, −28.75 | 0.76 |
| H0006 | 1,764 | 0.0967 | 0.77 | 0.45 / 0.59 / 0.80 | 6.16° | −122.25, −38.75 | 0.61 |
| H0007 | 1,979 | 0.0940 | 0.75 | 0.80 / 0.87 / 0.97 | 6.00° | −93.25, −52.25 | 0.86 |
| H0008 | 1,237 | 0.0894 | 0.71 | 2.58 / 3.94 / 4.87 | 2.08° | 99.75, −21.25 | 3.31 |
| H0009 | 3,448 | 0.0703 | 0.56 | 1.05 / 1.08 / 1.20 | 8.09° | −0.25, 74.25 | 1.05 |
| H0010 | 988 | 0.0633 | 0.50 | 1.90 / 2.22 / 2.71 | 4.57° | 106.75, −33.25 | 2.19 |

**Reading, before any reference.** Range continuity at 75° produced:
- **one structural shell**: H0001, 82.6 % of the sphere, continuous through creases within 75°;
- a set of **near foreground surfaces**: H0002–H0007, all within about 0.45–1.5 m, below the horizon;
- a long tail of small pieces and singletons at depth discontinuities and grazing geometry.

The seeds of the foreground hypotheses sit several degrees inside their regions (5–13°). The tail has
zero clearance by construction.

## Reference / evaluation (MEASURED; after the freeze; descriptive only)

The freeze verified before the first reference open (check 24). The frozen products verified again
afterwards (check 25).

**Accounting:**
- catalog cells 222,267 and O_0 cells 33,491, equal to Breadth-1;
- 600 non-empty (H, O) pairs;
- 126 authored ids touched;
- 279 hypotheses touch O_0.

The overlap is **not** a ground-truth confusion matrix. No precision, recall, accuracy or IoU is reported.

- **One natural → many authored.** H0001 (the shell) intersects **123** authored ids. Its dominant ids are
  `beams` 29.9 %, `sol` 21.2 % and `woodBase` 11.1 %, with O_0 at 5.6 %. Every other hypothesis intersects at
  most 3 authored ids.
- **Natural hypotheses dominated by O_0.** H0002, H0003, H0004, H0005, H0006, H0007, H0011, H0012 and H0015
  lie **100 %** in O_0. So do further hypotheses down the ranking.
  - The largest natural foreground hypotheses are therefore exactly the rendered geometry that carries no
    catalog id. Breadth-1 found this geometry consistent with collection-instanced furniture (desks,
    chairs), though not verified cell by cell.
  - 270 of 453 hypotheses have O_0 as their dominant reference id; 183 have a catalog id.
- **Many natural → one authored:**

  | authored id | hypotheses meeting it | largest share |
  |---|---|---|
  | `sol` (178) | 53 | 85.5 % |
  | `beams` (110) | 48 | 99.9 % |
  | `woodBase` (224) | 18 | 97.3 % |
  | `Box25.002` | 15 | — |
  | `Cube.005` | 14 | — |
  | `Cube.002` | 12 | — |

  111 of the 126 touched authored ids meet exactly one hypothesis. For 109 of them that hypothesis is the
  shell H0001.
- **Single-id hypotheses.** 435 of 453 hypotheses intersect exactly one reference id: one authored id, or
  O_0.

## RGB diagnostic (MEASURED; after the freeze; DERIVED; no effect on discovery)

The contrast is the Euclidean distance of sRGB-decoded linear RGB across each candidate neighbour pair.

| edge class | edges | median | 95 % | 99 % | mean |
|---|---|---|---|---|---|
| retained (inside hypotheses) | 972,192 | 0.0142 | 0.0878 | 0.2425 | 0.0283 |
| cut (range discontinuities) | 45,080 | 0.0480 | 0.5113 | 1.4879 | 0.1259 |

**Headline.** RGB change is clearly larger across range cuts, but substantial colour change also occurs
inside range hypotheses:
- 78.5 % of cut edges exceed the retained median;
- 11.0 % of cut edges exceed the retained 99th percentile;
- 121,302 retained edges (12.5 %) have contrast at or above the cut median.

The intra-hypothesis map (`rgb-edge-contrast.png`) shows strong RGB changes on:
- the pinned papers on the corkboard;
- the blackboard and window frames;
- lamp outlines;
- furniture edges.

That is the evidence a future NB1b would need to test RGB continuity. NB1a itself makes no such decision.

**RGB did not affect segmentation.** No merge, split, seed change or deletion came from RGB. The RGB
diagnostics recorded the frozen hashes, and the frozen products are unchanged (check 28).

## Visual products (Visual Language 1)

Persistent, under `/home/lvelho/rd/f3d-vision/visuals/natural-bootstrap-1a-range-connectivity/`, drawn at
`8cc368d`:

| file | truth badges | sha256 |
|---|---|---|
| `overview.png` | ORACLE INPUT, DERIVED, REFERENCE / EVALUATION | `eb3348767ce0bbb80c6edd623f051bd1e98aac4172eb4d687318a66dc2e19140` |
| `range-input.png` | ORACLE INPUT | `8c066be058a181609746dcce5539dc86159385324c792dd7b04b983507b3e8e9` |
| `continuity-boundaries.png` | DERIVED, ORACLE INPUT | `41cd53bf17bfd0dfb1ef3905d4fb32530cb65254cc8b6fe4b0a6b9572056632a` |
| `hypothesis-panorama.png` | DERIVED | `c0471cf98e02dd3f97c9486a32073c0c3722faaf80f25324456ded1e887f7b28` |
| `seed-panorama.png` | DERIVED | `f4b853a900f0be0f0eefe78d55b71634bdc03c30370886cc10e505cb35492fd7` |
| `hypothesis-support-histogram.png` | DERIVED | `d295006ad83e204cf27f369582c236466faa2b447187078c437bf7cfadc7d0ad` |
| `interior-clearance-histogram.png` | DERIVED | `4e4550441326ec9b22815f19aeca3039be8a4786ad9a7a517c72c16884d37fef` |
| `overlap-matrix.png` | REFERENCE / EVALUATION | `032ca85e3399d44d4c6919c480e3d375cc2317353113a2d09e907c814f6efd93` |
| `rgb-edge-contrast.png` | DERIVED, ORACLE INPUT | `2ed52df43cdf16a14639534b1842e80d657fe22fd8c77e9f70529d8f276c4ecc` |
| `visuals-manifest.json` | — | `78d9d96c6002f571a85f5adac20cf3ed3aabe9270ab068e4541c1ffec78ceecc` |

The overview has four regions:
- A, ORACLE INPUT: RGB and range;
- B, DERIVED: cut edges;
- C, DERIVED: hypotheses and deep-interior seeds;
- D, REFERENCE / EVALUATION, kept secondary: the composition of the 12 largest hypotheses by authored id
  versus O_0.

Regenerate the figures with:

    .venv/bin/python tools/natural_bootstrap/nb1a_run.py visualize --run $RUN --visuals $VIS

## Machine evidence

Under `/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1a-range-connectivity/` (23 MB):

| file | sha256 |
|---|---|
| `input/range-sensory.npz` | `02bdf224…` |
| `input/rgb-sensory.npz` | `cd2600e6…` |
| `input/input-manifest.json` | `6d254702…` |
| `discovery/continuity-edges.npz` | `149ce63d…` |
| `discovery/hypothesis-raster.npz` | `513a15e0…` |
| `discovery/hypotheses.json` | `eecf180f…` |
| `discovery/hypotheses.csv` | `ca458497…` |
| `discovery/seeds.json` | `c0362d9c…` |
| `discovery/discovery-summary.json` | `fac0adb3…` |
| `discovery/discovery-opened-files.json` | `9de65774…` |
| `discovery/bootstrap-freeze.json` | `c0236d04…` |
| `evaluation/overlap-matrix.npz` | `e4f4bde0…` |
| `evaluation/overlap-summary.json` | `1ad980a4…` |
| `evaluation/reference-cells.npz` | `54a58d28…` |
| `evaluation/rgb-edge-diagnostics.json` | `7ea56745…` |
| `evaluation/rgb-edge-contrast.npz` | `a065901f…` |
| `evaluation/evaluation-opened-files.json` | `92ec6437…` |
| `manifest.json` | `69021c63…` |
| `check-summary.json` | `7eee407a…` |

`process-log.jsonl` holds the NB1a commands only.

## Checks (MEASURED)

`tools/natural_bootstrap/check_nb1a.py` at `8cc368d`: **33/33** (`NATURAL_BOOTSTRAP1A_CHECKS_PASS`). It
recomputes independently:
- it reads the EXR with OpenEXR;
- it enumerates all 8 neighbours and de-duplicates them, giving 1,034,640 pairs;
- it computes chord-formula angular separations;
- it builds BFS components: 453, in exact 1:1 correspondence;
- it computes Bellman-Ford clearance, matching to within 1.8e-15 rad;
- it counts its own overlap: 600 pairs, equal.

Further results:
- edge-state mismatches 0;
- C_MAX equals sec 75°;
- seed rule violations 0 (257 ties, 0 fallbacks);
- O_0 is included, with the Breadth-1 accounting equal;
- the figures regenerate byte-identically;
- the synthetic known answers pass 10/10 in the generator and in the checker's independent re-implementation:
  - fronto-parallel patch: 1;
  - depth step: 2;
  - 73.5° strip connected (C 3.57 / 3.47); 76.5° strip split (C 4.36 / 4.21);
  - seam patch: 1 (2 without wrap);
  - diagonal pair: 1;
  - singleton: seed itself, clearance 0;
  - deep-interior square: centre seed, 5.000°;
  - symmetric four-way tie resolved to (179, 359);
  - no-boundary sphere: fallback.

**Corruption / mutation suite: 29/29 caught from a passing baseline** (`NATURAL_BOOTSTRAP1A_MUTATIONS_CAUGHT`).
The checker marks the suite not probative unless the uncorrupted baseline passes.

| defect | target |
|---|---|
| slant parameter changed to 70° | 13 |
| a retained edge flipped | 14 |
| longitude wrap broken (regenerated) | 10 |
| constant pixel spacing (regenerated) | 11 |
| a hypothesis label altered | 15 |
| a singleton deleted | 16 |
| two components merged | 18 |
| a seed moved off its hypothesis | 22 |
| a seed moved away from max clearance | 22 |
| the seed tie-break violated (H0003) | 23 |
| Object Index added to the sensory input | 05 |
| discovery opened RGB | 07 |
| discovery opened the catalog | 08 |
| a bootstrap output modified after the freeze | 24 |
| evaluation before the freeze verification | 24 |
| an overlap value altered | 26 |
| O_0 omitted | 27 |
| the RGB step modified a hypothesis | 28 |
| a visual pixel altered | 29 |
| `fov3d` modified | 30 |
| controller code modified | 30 |
| a Blender command in the process log | 02 |
| a controller command in the process log | 32 |
| a C value altered | 12 |
| a range value altered | 04 |
| a clearance value altered | 21 |
| a boundary cell flipped | 20 |
| hypothesis ids swapped | 19 |
| a synthetic case failed | 33 |

Other gates:
- layout 530/530;
- `scripts/verify_baseline.sh` 9/9;
- `git diff --check` clean;
- `fov3d/` identical.

## Incidents and repairs

**Before the freeze** (implementation defects inside the new NB1a tools, found on synthetic and dev data):
1. **Native file opens bypass Python audit hooks.** OpenEXR opens files in C++, so the guards did not record
   the EXR reads. Preparation and evaluation now read the EXR with the accepted pure-Python `exr_lite`,
   whose opens the guard sees; the checker uses OpenEXR independently. An audit-hook guard records and
   blocks Python-level opens; it is not an OS sandbox. The static import audit of the discovery code
   (check 8) complements it.
2. Evaluation hashed the reference sources before verifying the freeze. Those hash reads now happen inside
   the guard, after the freeze verification.
3. Checker repairs:
   - checks 6 and 25 now validate the guard records for internal consistency instead of against a mirror
     path, so they no longer failed in every corruption mirror;
   - check 2 uses a fixed path for the Breadth-1 render directory;
   - mirrors keep the original directory names;
   - an overview placeholder for the O_0 panel was replaced by a post-freeze reference raster,
     `evaluation/reference-cells.npz`, an extra REFERENCE / EVALUATION product not listed in the contract.
4. A scratch dev harness, not committed, ran the whole pipeline on Breadth-1's synthetic (non-Classroom)
   EXR: 33/33 checks and 28/28 corruptions. The singleton case was N/A there.

**The canonical discovery:** no failure, no repeat.

**After the freeze** (presentation only, `8cc368d`):
- the first `visualize` crashed in PIL on a sub-2-pixel bar, logged as `failed` in `process-log.jsonl`; bars
  now keep a minimum height;
- the overview panel D caption is wrapped;
- the RGB and overlap figures have shorter titles and trimmed canvases.

Two intermediate `visualize` runs during these fixes are logged with `dirty: true`. The persistent figures
are the final run's, at `8cc368d` (clean). The frozen products and evaluation outputs are unchanged.

## Statements

- **Blender identity did not affect discovery.** The discovery guard shows exactly one data read, the
  stripped range file, with 0 violations. Ordering, seeds and ids use no identity.
- **RGB did not affect segmentation**, nor any seed or hypothesis.
- **No controller ran**, and no controller module is imported (check 32).
- No Blender render, and no new, lower-resolution, foveal, stereo or per-hypothesis observation.
- The 75° parameter, the region rule, the absence of filtering and the seed rule are unchanged since the
  implementation commit.

## Interpretation for the review (descriptive; no decision)

On this proxy, simple range continuity:

1. **Separates foreground proto-objects from the room.** The largest near-foreground hypotheses come out as
   coherent, seedable regions with seeds 5–13° deep; in the RGB they look like desks and chairs. In the
   reference they lie entirely in the noncatalog O_0 geometry, so NB1a recovers salient structure that the
   authored catalog does not list.
2. **Merges the room into one shell.** Walls, floor, ceiling, beams, mouldings, boards and pipes are joined
   through creases within 75°: 82.6 % of the sphere spans 123 authored ids. That is too merged for
   interrogating structural parts.
3. **Leaves a fragmented tail.** It consists of 137 singletons and 229 all-boundary pieces, all with zero
   clearance. Visually they sit at thin or grazing geometry, such as furniture legs, window mullions and desk
   edges.

The evaluated relationship to authored identity is reference information, not ground truth. The O_0
correspondence again underlines that the 234-object catalog is not an inventory of rendered geometry.

Possible next questions, for Luiz and Chat only:
- RGB continuity (NB1b) for the shell's internal structure and the high-contrast intra-hypothesis edges;
- an orientation or crease cue;
- controller-integration design using the foreground seeds.

## Unresolved decisions

1. Qualitative and scientific review: coherence, seedability, plausibility for later active interrogation.
2. The next cue, if any (RGB continuity, orientation / crease), or controller integration. Not started.

NB1b, Controller-02 integration and Natural Bootstrap-2 are not started.
