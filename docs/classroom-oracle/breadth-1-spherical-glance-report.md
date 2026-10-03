# Breadth-1: Classroom-234 Spherical Glance — report

**Markers.**

    BREADTH1_CLASSROOM234_SPHERICAL_GLANCE_COMPLETE
    BREADTH1_CLASSROOM234_SPHERICAL_GLANCE_ACCEPTED

**Status: ACCEPTED.** Luiz and Chat accepted the measured scientific result and the final figures after
qualitative and scientific review (see "Acceptance record" at the end).

The single canonical Classroom observation is valid and fully analyzed. Every required product exists.
Checks pass **26/26** (`BREADTH1_CHECKS_PASS`). The corruption suite, run from that passing baseline, catches
**29/29** (`BREADTH1_MUTATIONS_CAUGHT`).

The first report (`8b347f2`) stopped at 25/26: check 13 exposed an ambiguity of the seed rule at exact
mathematical ties. Luiz/Chat chose **Option A**, a **post-run numerical clarification** of the seed tie
semantics (contract section 11, `8158809`). The seeds were then re-derived from the saved canonical EXR.
**No Blender render was run again.**

> **The 234-object catalog is not an inventory of all rendered Classroom geometry.** The 234 objects are the
> accepted catalog accounting universe. Collection-instanced geometry (school desks, chairs, the teacher's
> desk, lamps, …) is rendered but is not represented in that catalog: it covers 15.4 % of the sphere with
> Object Index 0. Breadth-1 does not resolve that discrepancy (see "Cell accounting").

Contract: `docs/classroom-oracle/breadth-1-spherical-glance-contract.md`. MEASURED means produced by
the identified runs below; PROPOSED means the contract's untested estimate.

## Branch and commits

| item | value |
|---|---|
| branch | `classroom-oracle/breadth-1-spherical-glance`, from `main` @ `3aa0cc6` (Visual Language 1 accepted at `e596a10`); isolated worktree |
| contract | `d5b975b` *Contract Breadth-1 Classroom-234 spherical glance* |
| implementation (frozen before the run) | `0106269` *Implement Breadth-1 spherical glance* |
| canonical run | at `0106269`: synthetic test, preflight, render and analysis (clean and pushed tree; recorded in `process-log.jsonl` and `manifest.json`) |
| presentation fix after the run | `0a78544` *Breadth-1 figures: presentation fixes after the canonical run* (figures only) |
| first report (decision pending) | `8b347f2` *Report Breadth-1 Classroom-234 spherical glance (decision pending)* |
| post-run seed tie clarification and repair (Option A) | `8158809` *Clarify Breadth-1 seed tie semantics (post-run, Option A)*; `analyze`, `visualize` and the checker re-run at `8158809` from the saved EXR |
| completion report | this commit, *Complete Breadth-1 numerical seed tie repair* |

`fov3d/` is byte-identical to `3aa0cc6`. The only changed tracked files are the declared Breadth-1 files
plus the layout checker (check 21).

## Commands (MEASURED times)

From the worktree root, with `RUN=/home/lvelho/rd/f3d-vision/previews/breadth-1-classroom-234-spherical-glance`
and `VIS=/home/lvelho/rd/f3d-vision/visuals/breadth-1-classroom-234-spherical-glance`:

| command | result | time |
|---|---|---|
| `.venv/bin/python tools/classroom_oracle/breadth1_glance.py synthetic --run $RUN` | `BREADTH1_SYNTHETIC_PASS`, 31/31 | 1.0 s |
| `… breadth1_glance.py preflight --run $RUN` | catalog 234 equal; EYE pose 0 / 0; OPTIX; **no render** | 0.6 s |
| `… breadth1_glance.py render --run $RUN` | the one canonical render | 2.8 s wall |
| `… breadth1_glance.py analyze --run $RUN` | 126 visible, 108 no first hit | 0.8 s |
| `… breadth1_glance.py visualize --run $RUN --visuals $VIS` | 8 figures + PLY (run at `0106269`, then again at `0a78544`) | 1.0 s |
| `.venv/bin/python tools/classroom_oracle/check_breadth1.py --run $RUN --visuals $VIS --corruptions --write-summary` | at `0a78544`: 25/26; corruptions 28/28 (not probative: baseline failing) | 20.5 s |
| `… breadth1_glance.py analyze --run $RUN` (re-derivation at `8158809`, from the saved EXR) | 126 visible, 108 no first hit; tie control 3/3 | 0.8 s |
| `… breadth1_glance.py visualize --run $RUN --visuals $VIS` (at `8158809`) | 8 figures + PLY | 1.0 s |
| `… check_breadth1.py --run $RUN --visuals $VIS --corruptions --write-summary` (at `8158809`) | **26/26; corruptions 29/29 from a passing baseline** | 21.7 s |

The re-derivation invoked no Blender process. `process-log.jsonl` still holds exactly the three original
invocations (synthetic, preflight, canonical) and is byte-identical. The canonical EXR is unchanged at
sha256 `4ea036fc…`.

All are interactive class. The contract's PROPOSED "batch (< 5 min)" for the render was conservative.

The canonical command (logged in `process-log.jsonl`) was:

    blender -b /home/lvelho/rd/f3d-vision/scenes/classroom/classroom_eye.blend --python-exit-code 1 \
      -P tools/classroom_oracle/breadth1_render.py -- --mode canonical \
      --seeds /home/lvelho/rd/f3d-vision/previews/controller-01-full/bootstrap/seeds.json \
      --catalog /home/lvelho/rd/f3d-vision/previews/controller-01-full/bootstrap/instance_catalog.json \
      --out $RUN/render

## The canonical observation (MEASURED)

| item | value |
|---|---|
| render | **exactly one** canonical Blender invocation (`render_invocations` 1; one `canonical` entry in the process log) |
| render time | **2.208 s** (Blender `render()` call); 2.803 s for the whole Blender process |
| device | Cycles **OPTIX** (RTX 4090), Blender 5.2.1 LTS |
| configuration read back from Blender | `PANO` / `EQUIRECTANGULAR`; longitude ±3.1415927 (float32 π), latitude ±1.5707964; 720 × 360 at 100 %; 512 spp; seed 0 (the .blend's seed keyframe removed by `pin_seed`); adaptive sampling, denoising and motion blur off; BOX filter 1.0; clip 0.01–1000 m |
| head transform | `head_R_wh` / `head_origin_w_m` exactly as `seeds.json` (requested); Blender read-back matrix within 4.1e-8; EYE object pose identical (0 / 0) |
| catalog | accepted `instance_catalog.json`, **234** entries; the live `_assign_instance_ids` assignment is identical |
| canonical EXR | `render/canonical.exr`, 46,664,464 bytes, sha256 `4ea036fc74eab3b3ab06a0c4470c2b01740c9322de0eea522f957ddfffa172f8` (recorded by Blender, re-verified by the checker) |
| render metadata | `render/render-metadata.json` `7c05b80d2d0291f8e12c0886008957b2579e27561b78a766e156b29ec2282157` |
| orientation | all 222,267 authored cells' Position directions lie inside their declared cells. The largest pitch deviation is 0.00032° and the largest yaw deviation 0.00082° (below 85° pitch), so the first sample sits at the cell centre |
| Object Index | integral everywhere; every nonzero id is a catalog id |

Accepted sources, all verified by sha256:
- `seeds.json` `6ef83319…`;
- `instance_catalog.json` `be265945…`;
- Controller-02 `result.json` `a6dc4879…`;
- `classroom_eye.blend` `dca66a32…`.

The two accepted-25 sources agree. The Controller-01 and Controller-02 run files are unchanged (check 20).

## Results (MEASURED, DERIVED from the canonical EXR)

### Accounting of the 234 authored objects

| quantity | value |
|---|---|
| catalog total | **234** |
| `VISIBLE_AT_0P5_DEG` | **126** |
| `NO_FIRST_HIT_AT_0P5_DEG` | **108** |
| visible with > 1 connected component | **59** |

The 108 objects with no first-hit cell are a sampling result at 0.5° from this viewpoint. No cause is
inferred.

### Cell accounting (259,200 cells = 4π sr)

| class | cells | solid angle | of 4π |
|---|---|---|---|
| authored (one of the 234) | 222,267 | 10.3682 sr | 82.5 % |
| `INDEX0_NONCATALOG_GEOMETRY` (Object Index 0, Position ≠ 0) | 33,491 | 1.9390 sr | 15.4 % |
| `INDEX0_NO_GEOMETRY` (Object Index 0, Position = 0) | 3,442 | 0.2592 sr | 2.1 % |

The cell weights sum to 4π = 12.566370614359172 sr.

**What the 234-object catalog is, and is not:**
- The 234 objects are the **accepted catalog accounting universe**: the `instance_catalog.json` used by
  Controller-01/02, which is exactly the scene's renderable geometric objects.
- **Collection-instanced geometry is rendered but is not represented in that catalog.** It appears as
  `INDEX0_NONCATALOG_GEOMETRY` (15.4 % of the sphere). See "Observations for the review" for the read-only
  scene query (56 collection instancers, including 20 school desks).
- **Breadth-1 does not resolve that discrepancy.** No ids were assigned retroactively, and no cell-by-cell
  furniture attribution was made.
- The discrepancy is scientifically relevant to Natural Bootstrap-1 and to any future evaluation that uses
  the catalog.
- Authored-object identity remains oracle / reference information, not natural segmentation ground truth.

### Overlap with the accepted localized 25 (reference subset only)

- All **25 / 25** accepted objects are visible at 0.5°. 101 visible objects are outside the 25.
- **24** visible objects have support inside the old Controller domain (±25° × ±20°), and all 24 are
  accepted-25 members.
- `beams` (110), accepted, has no 0.5° cell centre inside that domain, although its accepted 0.25° seed
  lies there. Its support is elsewhere (rank 1, 3.107 sr).
- **102** visible objects lie entirely outside the old domain; 121 have some support outside it.

| id | name | rank | cells | sr | comp. | in old domain | seed yaw, pitch (°) | sep. from accepted seed (°) | median range (m) |
|---|---|---|---|---|---|---|---|---|---|
| 107 | Text | 95 | 9 | 0.0007 | 3 | yes | 13.75, 16.75 | 1.20 | 4.59 |
| 108 | Text.001 | 101 | 7 | 0.0005 | 4 | yes | 27.75, 15.75 | 3.38 | 4.92 |
| 109 | alphabet | 77 | 28 | 0.0021 | 18 | yes | 25.75, 12.25 | 16.86 | 4.63 |
| 110 | beams | 1 | 81,534 | 3.1071 | 131 | **no** | 87.25, 70.25 | 77.45 | 1.98 |
| 111 | blackBoard | 13 | 1,487 | 0.1129 | 1 | yes | 18.25, 1.75 | 3.25 | 4.49 |
| 112 | blackBoardLamp | 56 | 91 | 0.0068 | 1 | yes | 18.25, 10.75 | 4.18 | 4.37 |
| 113 | blackBoard_upPart | 70 | 46 | 0.0034 | 8 | yes | 5.75, 11.75 | 7.59 | 4.46 |
| 114 | blackboardLamp | 82 | 21 | 0.0016 | 4 | yes | 6.25, 10.75 | 6.88 | 4.42 |
| 115 | boardFrame | 26 | 281 | 0.0213 | 1 | yes | 18.25, −5.75 | 14.87 | 4.47 |
| 116 | ceiling | 69 | 53 | 0.0038 | 9 | yes | −17.25, 20.25 | 2.13 | 4.93 |
| 123 | ceilingMoulding | 12 | 1,751 | 0.1133 | 12 | yes | −107.75, 41.25 | 84.10 | 3.17 |
| 140 | coat 1 | 46 | 112 | 0.0085 | 1 | yes | −1.25, 0.25 | 0.25 | 3.87 |
| 166 | lettersPlank | 23 | 433 | 0.0321 | 1 | yes | 15.25, 13.25 | 7.07 | 4.53 |
| 167 | lettersPlank.001 | 71 | 40 | 0.0029 | 1 | yes | 14.75, 16.75 | 0.72 | 4.59 |
| 168 | lettersPlank.002 | 72 | 39 | 0.0029 | 1 | yes | 26.25, 15.25 | 1.76 | 4.91 |
| 172 | pipe | 9 | 2,926 | 0.1402 | 7 | yes | −123.75, 56.25 | 85.24 | 2.02 |
| 174 | plank | 7 | 2,107 | 0.1604 | 9 | yes | −89.25, −2.25 | 77.72 | 2.44 |
| 178 | sol | 2 | 72,215 | 2.5751 | 77 | yes | 71.25, −76.25 | 66.41 | 1.35 |
| 201 | verticalPipe | 34 | 191 | 0.0143 | 3 | yes | −8.75, 4.75 | 0.75 | 4.48 |
| 202 | wall | 4 | 8,370 | 0.5727 | 11 | yes | −93.75, 28.75 | 68.19 | 2.51 |
| 210 | wall.008 | 8 | 2,008 | 0.1485 | 11 | yes | 11.75, 12.25 | 11.97 | 4.62 |
| 216 | wallPlug.001 | 99 | 8 | 0.0006 | 1 | yes | 13.75, −8.75 | 0.35 | 4.44 |
| 224 | woodBase | 3 | 16,034 | 1.1851 | 29 | yes | −89.25, −16.75 | 85.66 | 2.54 |
| 225 | woodBaseboard | 10 | 1,763 | 0.1218 | 28 | yes | −80.25, −31.25 | 76.62 | 2.51 |
| 234 | worldMap | 15 | 663 | 0.0500 | 2 | yes | −15.75, 6.75 | 0.56 | 4.77 |

The separation from the accepted seed is descriptive. The two seeds answer different questions: a
whole-sphere largest component here, versus the first in-domain hits of the accepted seed scan.

### Support distribution (bins declared in the contract)

Visible solid angle per object; NO_FIRST_HIT = 108 is counted separately:

| sr bin | [3.2e-5, 1e-4) | [1e-4, 3.2e-4) | [3.2e-4, 1e-3) | [1e-3, 3.2e-3) | [3.2e-3, 1e-2) | [1e-2, 3.2e-2) | [3.2e-2, 0.1) | [0.1, 0.32) | [0.32, 1) | [1, 3.2) |
|---|---|---|---|---|---|---|---|---|---|---|
| objects | 4 | 12 | 21 | 19 | 28 | 19 | 10 | 7 | 3 | 3 |

All other declared bins are 0, with no underflow or overflow. Visible cells per object, in bins of
`[2^k, 2^(k+1))`, from k = 0 upward:

    4, 6, 16, 13, 12, 8, 25, 13, 10, 5, 5, 2, 3, 2, 0, 0, 2, 0

**Dominance.** The largest K objects cover:

| K | of 4π | of all authored support |
|---|---|---|
| 1 (`beams`) | 24.7 % | 30.0 % |
| 5 | 63.4 % | 76.8 % |
| 10 | 71.9 % | 87.2 % |
| 25 | 78.6 % | 95.3 % |

### Largest-support ranking (top 25)

| rank | id | name | sr | cells |
|---|---|---|---|---|
| 1 | 110 | beams | 3.1071 | 81,534 |
| 2 | 178 | sol | 2.5751 | 72,215 |
| 3 | 224 | woodBase | 1.1851 | 16,034 |
| 4 | 202 | wall | 0.5727 | 8,370 |
| 5 | 212 | wall.010 | 0.5229 | 7,061 |
| 6 | 141 | corkboard | 0.5042 | 6,837 |
| 7 | 174 | plank | 0.1604 | 2,107 |
| 8 | 210 | wall.008 | 0.1485 | 2,008 |
| 9 | 172 | pipe | 0.1402 | 2,926 |
| 10 | 225 | woodBaseboard | 0.1218 | 1,763 |
| 11 | 10 | Cube.006 | 0.1167 | 4,133 |
| 12 | 123 | ceilingMoulding | 0.1133 | 1,751 |
| 13 | 111 | blackBoard | 0.1129 | 1,487 |
| 14 | 207 | wall.005 | 0.0712 | 951 |
| 15 | 234 | worldMap | 0.0500 | 663 |
| 16 | 208 | wall.006 | 0.0495 | 656 |
| 17 | 20 | Cube.016 | 0.0482 | 645 |
| 18 | 119 | ceilingAirVent.002 | 0.0400 | 1,084 |
| 19 | 214 | wall.012 | 0.0394 | 546 |
| 20 | 21 | Cube.017 | 0.0377 | 505 |
| 21 | 12 | Cube.008 | 0.0365 | 488 |
| 22 | 144 | doorFrame.001 | 0.0350 | 473 |
| 23 | 166 | lettersPlank | 0.0321 | 433 |
| 24 | 173 | pipe.001 | 0.0303 | 430 |
| 25 | 213 | wall.011 | 0.0260 | 351 |

The full ranking is in `summary.json` and `object-stats.csv`.

### Components (authored-object image fragmentation, not natural segmentation)

Component counts among the 126 visible objects, as `count: objects`:

    1: 67, 2: 17, 3: 7, 4: 3, 5: 3, 6: 3, 7: 2, 8: 1, 9: 4, 10: 2, 11: 3, 12: 2, 13: 3,
    18: 1, 20: 1, 28: 2, 29: 1, 34: 1, 37: 1, 77: 1, 131: 1

The most fragmented are `beams` (131), `sol` (77), `Cube.002` (37) and `Cube.005` (34). Six objects
have a component that crosses the longitude seam: 10, 110, 174, 178, 212 and 224.

### Radial range over the 222,267 authored cells

| quantile | 0 | 0.01 | 0.05 | 0.25 | 0.5 | 0.75 | 0.95 | 0.99 | 1 |
|---|---|---|---|---|---|---|---|---|---|
| cells (m) | 1.050 | 1.095 | 1.205 | 1.596 | 1.973 | 2.738 | 4.598 | 5.312 | 6.927 |
| solid-angle weighted (m) | 1.050 | 1.206 | 1.301 | 1.899 | 2.348 | 3.641 | 4.836 | 5.442 | 6.927 |

In the declared half-octave bins, cell counts are:

| bin (m) | cells |
|---|---|
| [1, 1.41) | 44,703 |
| [1.41, 2) | 69,512 |
| [2, 2.83) | 55,791 |
| [2.83, 4) | 26,916 |
| [4, 5.66) | 24,763 |
| [5.66, 8) | 582 |

No authored cell is nearer than 1.05 m.

### Representative DERIVED seeds

There are 126 seeds, one per visible object, each on its object's largest component. The declared
fallback was used 0 times. No seed caused an observation.

Under the section-11 tie semantics (`SEED_TIE_DOT_EPS = 1e-12`), 16 objects have two numerically tied
candidates: 4, 7, 11, 19, 26, 30, 31, 102, 114, 131, 177, 209, 216, 217, 218 and 231. Each record carries
`tied_candidates`.

## Visual products (Visual Language 1)

Persistent, under `/home/lvelho/rd/f3d-vision/visuals/breadth-1-classroom-234-spherical-glance/`, drawn at
`8158809`. Only the two figures that draw seeds changed relative to `0a78544` (marked †); every other file
is byte-identical:

| file | truth badges | sha256 |
|---|---|---|
| `overview.png` † | REFERENCE / EVALUATION, ORACLE INPUT, DERIVED | `705265b08fda43f7c532341fee97486d2f3e494fdcf25d85365e010244454f02` |
| `rgb-panorama.png` | REFERENCE / EVALUATION | `789f3d65ad31c7d861a5e1fdf38c14f6478cb8dec7a5fe3e20a7076c1225898b` |
| `range-panorama.png` | REFERENCE / EVALUATION | `f37a35d5ef6abed6c51761e43feee34ec6a89750fc4abea33c23ad8c66f24f4b` |
| `instance-panorama.png` | ORACLE INPUT, DERIVED | `87863c8d2bb2d8588f676839e0f62ac289478bdd1e48ed7abfd779b02c8e1a7a` |
| `object-boundary-overlay.png` | REFERENCE / EVALUATION, DERIVED | `c860ed7ad06918a762447f60666a8e9284595f049ab309ba6e698ff27a95d91c` |
| `seed-direction-panorama.png` † | DERIVED, REFERENCE / EVALUATION | `0266275481fa43fe61355bd87dae84066b39e77ed49005ce154458cc46d6ea0b` |
| `support-size-histogram.png` | DERIVED | `5d05dbbda327f8ddfdd712c58705796e5af6ee0bc99364363132fd63e40c0dcc` |
| `support-vs-range.png` | DERIVED | `980eed2d93df1f9901495f0af1c36251431b452bd53a5a879970af9fb6f43763` |
| `global-point-cloud.ply` | REFERENCE / EVALUATION, ORACLE INPUT | `ee46ffcba92f18c43cddc6d3d0d90cbfd9226280fd4c0affd750976143310ee4` |
| `visuals-manifest.json` † | — | `e9dd2c02bf5fecd66d6336263efb7142b55a8831b24b05beca871595af7698ba` |

The overview has four regions:
- the RGB glance with the old Controller domain;
- the log range;
- the authored Object Index with boundaries, where white is geometry without a catalog id and hatching
  is no geometry;
- the accounting: one square per catalog object (18 × 13 = 234), the key counts, the cell accounting and
  the 126 derived seeds.

Nothing is labelled CONTROLLER-TIME. The Breadth-1 glyphs (contract section 6) are:
- derived seed: an ink diamond;
- accepted 25: a ring;
- old domain: a dashed rectangle.

Regenerate the figures with:

    .venv/bin/python tools/classroom_oracle/breadth1_glance.py visualize --run $RUN --visuals $VIS

## Machine evidence

Under `/home/lvelho/rd/f3d-vision/previews/breadth-1-classroom-234-spherical-glance/` (67 MB), `manifest.json`
is `a0919152cef1b43592b6f055693a833fe3433b50429dc9f966827ee78a284236`. It was rewritten by the re-derivation
at `8158809` (clean, pushed); the first was `f53b3557…` at `0106269`. It records:
- the inputs with sha256;
- the head transform;
- the three logged Blender invocations;
- the orientation residuals;
- the seed tie rule and its control;
- the truth class of every product.

Files marked † changed in the re-derivation, and only through the seed fields of objects 102 and 177 plus
the new `tied_candidates` / `tie_semantics` fields. Every other output is byte-identical to the first
derivation, including all three `.npz` arrays.

| output | sha256 |
|---|---|
| `glance.npz` | `83bb436dbdda44c09da423be66b0b44d062ac80174f994f052f4f79c7bf31aa2` |
| `range.npz` | `6dee7711b4903f901143cff59b6ad990cf890b95b0ceaf06e67618f604d197bb` |
| `components.npz` | `721b0a686c03e4854fea2fb50411b1b80b13b3cc9e774395fc648be7cd09d2d5` |
| `object-stats.json` † | `2f8aa7bee3abf88bd4a93316ad13babd6419f551536d99e71db6b63dce175a02` |
| `object-stats.csv` † | `fb0f9220a2763457f364e647e1cce582a954a3fa59bc4cfd8520dfb48938c2ab` |
| `components.json` | `078757fa5a4d8a887048e6e7c99837453fbe3bd7a86bc2cdedb865b5427d231e` |
| `seed-directions.json` † | `d68af8fd41db8300d651601f0b9ff33827a13130356c7ffb042c1277d1afa4c7` |
| `summary.json` | `b0744571be530599446e48ec0379c429d3e21acc08fdf153930fd82d4842be04` |
| `global-point-cloud.ply` | `ee46ffcb…`: 222,267 points, one per authored cell, with world Position, 8-bit RGB and instance id |

The directory also holds:
- `synthetic/`: the plumbing EXR `571469f8…` and its 31/31 report;
- `preflight.json`;
- `render/` (EXR, metadata, log);
- `process-log.jsonl`;
- `check-summary.json` `8e43150b8ccd0876e25709a4003b34c3e8c9839b3074d5d83d0866ba72344cc4`, from the checker at
  `8158809`: 26/26, with the corruption results and `baseline_passing: true`.

RGB, Position and Object Index come from the one EXR: `glance.npz` equals the EXR's channels exactly
(check 23).

## Checks

`tools/classroom_oracle/check_breadth1.py` at `8158809`: **26/26 pass** (`BREADTH1_CHECKS_PASS`).

| # | check | result |
|---|---|---|
| 01 | resolution 720 × 360 (EXR data window, metadata) | PASS |
| 02 | full-sphere PANO/EQUIRECTANGULAR, frozen settings, per-cell orientation | PASS |
| 03 | fixed-head transform = `seeds.json` (exact request, 4.1e-8 read-back, EYE 0) | PASS |
| 04 | catalog sha, exactly 234, live assignment equal | PASS |
| 05 | nonzero ids ⊂ catalog; Object Index integral | PASS |
| 06 | 234 records exactly once, names match (JSON and CSV) | PASS |
| 07 | VISIBLE + NO_FIRST_HIT = 234; statuses recompute | PASS |
| 08 | weights sum to 4π; independent formula `2 dλ cos φ_c sin(Δφ/2)` | PASS |
| 09 | per-object cells (exact) and solid angles recompute | PASS |
| 10 | seam-aware 8-connected components (independent BFS) recompute | PASS |
| 11 | range raster from Position and origin | PASS |
| 12 | per-object min / median / max range | PASS |
| 13 | seeds on the largest component; frozen rule with the section-11 tie semantics, applied independently; declared epsilon; independent tie controls 3/3 | PASS (126 seeds, 16 with tied candidates; previously FAIL at `0a78544`) |
| 14 | old-domain flags | PASS |
| 15 | accepted-25 flags vs both accepted sources | PASS |
| 16 | rankings and top-K | PASS |
| 17 | PLY count, coordinates, RGB, ids, cells; visuals copy identical | PASS |
| 18 | output, input and visual hashes | PASS |
| 19 | no CONTROLLER-TIME claim; truth classes declared | PASS |
| 20 | only the declared Blender invocations; no controller outputs or imports; sources unchanged | PASS |
| 21 | only declared Breadth-1 files changed vs `3aa0cc6` | PASS |
| 22 | `fov3d/` byte-identical to `3aa0cc6` | PASS |
| 23 | exactly one canonical render; `glance.npz` is that EXR | PASS |
| 24 | index-0 accounting; 259,200 cells | PASS |
| 25 | synthetic test passed at the canonical commit | PASS |
| 26 | figures regenerate byte-identically | PASS |

**Corruption / mutation suite: 29/29 caught from a passing baseline** (`BREADTH1_MUTATIONS_CAUGHT`). That is
the original 28 plus a new probative tie-break corruption. The checker now prints the marker only when the
uncorrupted baseline passes, and records `baseline_passing` in `check-summary.json`. Each targeted check
failed:

| defect | target |
|---|---|
| an object record dropped | 06 |
| live assignment of 233 | 04 |
| illegal instance id 999 | 05 |
| visible cells +1 | 09 |
| one row weight × 1.001 | 08 |
| a duplicated component | 10 |
| components counted without the longitude wrap (6 seam objects) | 10 |
| seed moved to a neighbouring other-object cell | 13 |
| seed moved to the other numerically tied cell (object 4: (171, 476) → (171, 477)) | 13 |
| median range +0.01 m | 12 |
| flipped old-domain flag | 14 |
| flipped accepted-25 flag | 15 |
| PLY one vertex short | 17 |
| `truth: CONTROLLER-TIME` | 19 |
| spp 256 | 02 |
| 640 × 320 | 01 |
| flipped image columns | 02 |
| altered head rotation | 03 |
| swapped ranks | 16 |
| altered manifest hash | 18 |
| controller command in the process log | 20 |
| a changed controller tool | 21 |
| a changed `fov3d` file | 22 |
| a second canonical render | 23 |
| index-0 count +1 | 24 |
| V + N inconsistent | 07 |
| altered range raster | 11 |
| a failed synthetic check | 25 |
| an overview pixel altered | 26 |

**Check-13 negative control, explicitly:**
- uncorrupted baseline: check 13 **PASS**;
- seed moved off support: check 13 **FAIL**;
- seed moved to the other numerically tied cell: check 13 **FAIL**. That cell is on support, on the largest
  component and equally near the mean, so only the declared tie-break rejects it.

In the first report the baseline already failed check 13, so its earlier 28/28 was not probative for 13.

Other gates, at `8158809` and again at this commit:
- layout checker 521/521, with the Breadth-1 declarations, and negative controls: an untracked contract
  fails it, and an undeclared Breadth-1 file fails it;
- `scripts/verify_baseline.sh` 9/9;
- `git diff --check` clean;
- `fov3d/` identical.

## Check-13 seed tie semantics: diagnosis, decision and repair

**Diagnosis (MEASURED).** For objects 102 `Rectangle018.002`, 209 `wall.007` and 218 `wallSwitch`, the
largest component is exactly mirror-symmetric in longitude:

| object | cells | columns |
|---|---|---|
| 102 | 8 | 62–63 |
| 209 | 4 | 485–488 |
| 218 | 24 | 275–280 |

The two central cells of the row nearest the mean are therefore mathematically equidistant from the
weighted mean. Their float64 dot products differ by 0 or 1 ulp (1.1e-16), depending on arithmetic order.

The contract's rule (4.5) is "maximum float64 dot product; ties → smaller row, then column". Its
tie-break applies only to bitwise-equal values, and the contract fixes no summation order. So the
generator, which uses the 4.2 weight formula and row-major sums, and the independent checker, which uses
the cos·sin weights and BFS-order sums, break these ties differently.

- For **102**, the generator's round-off favours column 63, but the declared tie-break (smaller column)
  gives 62.
- For 209 and 218, the generator's values are bitwise ties and its choice is the declared one; the
  checker's arithmetic differs.

**What a round-off tie tolerance would change** (dry run in scratch; frozen outputs untouched).
Candidates within ε = 1e-12 of the maximum dot product are treated as ties, then broken by row and column.
- 16 visible objects have such a tie at the maximum.
- Exactly 2 seeds would move, each by one cell in the same row:

  | object | current seed | seed under ε | yaw change |
  |---|---|---|---|
  | 102 | (187, 63) | (187, 62) | −148.25° → −148.75° |
  | 177 `post-it` | (193, 463) | (193, 462) | 51.75° → 51.25° |

- 177 passes check 13 today only because both arithmetics happen to favour the same cell.
- Under ε, the generator and the independent checker agree on all 126 seeds.
- Nothing else would change: visibility, components, ranks, ranges and accounting do not depend on seeds.

**Options put to Luiz/Chat (first report):**
- **A (recommended).** Declare ε = 1e-12 as a round-off tie tolerance in contract 4.5, then:
  - apply the same three-line change in `breadth1_glance.representative_seed` and in check 13;
  - re-run `analyze`, `visualize` and `check` from the saved canonical EXR. No render and no new
    observation;
  - record the completion marker if all 26 checks pass.

  This keeps the rule's intent, minimum angular distance with ties to the smaller row and column. It
  moves seeds 102 and 177 by 0.5°.
- **B.** Declare the generator's float64 arithmetic canonical: the 4.2 weights and row-major summation.
  Check 13 then replicates that exact arithmetic for the argmax. Current seeds are kept, including 102 and
  177, which do not follow the mathematical tie-break.

**Decision.** Luiz/Chat chose **Option A**, a post-run numerical clarification and not scientific retuning.
It is recorded as contract section 11, dated 2026-10-03; the original 4.5 rule is kept verbatim, with
pointers.

**Repair (`8158809`).** Exact files changed:
- `docs/classroom-oracle/breadth-1-spherical-glance-contract.md`: section 11 added, plus pointers in 4.5 and
  check 13;
- `tools/classroom_oracle/breadth1_spec.py`:
  - `SEED_TIE_DOT_EPS = 1e-12`, with its explanation;
  - three known-answer controls on exactly mirror-symmetric synthetic components;
- `tools/classroom_oracle/breadth1_glance.py`:
  - `representative_seed` takes all cells with `max_dot - dot <= SEED_TIE_DOT_EPS` and resolves them by row,
    then column, recording `tied_candidates`;
  - `analyze` runs the tie control and stops if it fails;
  - the manifest and `seed-directions.json` record the rule;
- `tools/classroom_oracle/check_breadth1.py`:
  - check 13 applies the rule **independently**, with its own cell geometry, spherical-weight expression
    (cos·sin), BFS components and weighted mean, and a literal epsilon. It never calls the generator;
  - it checks the declared epsilon and runs its own three tie controls;
  - a new corruption moves a seed to the other tied cell;
  - corruptions count only from a passing baseline.

**Tie controls** (synthetic, no Blender), in the generator and independently in the checker:

| control | cells | expected = got | tied |
|---|---|---|---|
| two-cell row (exact float64 equality would pick (60, 29)) | (60, 28), (60, 29) | (60, 28) | 2 |
| four-way tie straddling the equator | rows 179–180 × columns 359–360 | (179, 359) | 4 |
| four-way tie across the longitude seam | rows 179–180 × columns 719, 0 | (179, 0) | 4 |

**Re-derivation (MEASURED, from the saved canonical EXR; no render).** Exactly the two predicted seeds moved:

| object | before (row, col) | after (row, col) | yaw before → after | pitch |
|---|---|---|---|---|
| 102 `Rectangle018.002` | (187, 63) | (187, 62) | −148.25° → −148.75° | −3.75° |
| 177 `post-it` | (193, 463) | (193, 462) | 51.75° → 51.25° | −6.75° |

No other seed moved: 124 of 126 are identical. Neither object is in the accepted 25.

**Unchanged** (compared with a pre-repair snapshot):
- `glance.npz`, `range.npz`, `components.npz`, `components.json`, `summary.json`, `global-point-cloud.ply`,
  `process-log.jsonl` and `preflight.json`, byte for byte;
- every non-seed field of all 234 object records (value-identical);
- catalog 234, visible 126, no first hit 108, fragmented visible 59;
- authored cells 222,267 and PLY points 222,267;
- all support, range, component, ranking and accounting quantities. The cell accounting is 82.5 % /
  15.4 % / 2.1 %.

## Incidents and repairs

**Before the freeze** (implementation defects inside the new Breadth-1 tools, found on synthetic and dev
data):
1. The freeze guard's `code_state` ignored untracked files, so a dev run with uncommitted tools looked
   clean. It now treats untracked files under `tools/`, `docs/`, `fov3d/` and `scripts/` as dirty.
2. The OpenEXR Python header is cleared when the file closes, which caused a `KeyError: 'dataWindow'`. The
   checker now reads the data window before closing.
3. Corruption-suite structure: file corruptions are applied first and the context is then rebuilt, so
   stale arrays cannot leak. In-process mutants pass explicit overrides.
4. A no-wrap component mutant was added. The histogram draws an explicit "≥10 sr" overflow bar instead
   of folding it into the last bin. An underflow below 1e-7 sr raises, which is geometrically impossible:
   one pole cell is 3.3e-7 sr.
5. Dev harness (scratch only, not committed): the synthetic EXR posed as a canonical run to exercise
   `analyze`, `visualize` and the checker end to end. At `0106269` it gave 26/26 and 28/28. No Classroom
   pixels were involved.

**The canonical run:** no technical failure, no restart, no repair.

**After valid data** (presentation only, `0a78544`):
- the overview's Object Index caption explains white and hatched;
- the cell accounting was added to the statistics region;
- the histogram axis label no longer overlaps;
- the support-vs-range y limits follow the data decades;
- the visuals manifest records the drawing commit.

That fix left the frozen arrays and statistics unchanged: the `manifest.json` output hashes were still those
written at `0106269`.

**After the decision** (`8158809`): the authorized post-run seed tie clarification, Option A. It is
described in "Check-13 seed tie semantics" above, and it changed two derived seeds and nothing else.

**Observations for the review:**
- **Extra EXR passes.** The Classroom's `interior` view layer already enables AO, diffuse, glossy,
  transmission, emission, normal and Z passes in the .blend, so the EXR has 45 channels. Breadth-1 uses
  only Combined, Position and Object Index. Perspective `Depth.Z` is never used. The accepted renderers
  load the same .blend view layer.
- **Geometry without a catalog id: 15.4 % of the sphere.** 99.6 % of those cells lie below the horizon
  (a report-only description computed from the frozen `range.npz`). A **read-only scene-structure query**
  (no render, not an observation) found this structure:

      blender -b scenes/classroom/classroom_eye.blend --python-expr "<list scene.objects by type; EMPTY
        objects with instance_type == 'COLLECTION'; their collections' geometric objects>"

  It shows:
  - `_mainScene` has 305 objects, of which exactly 234 are renderable geometric objects, and **56
    collection-instancer empties**;
  - among the instanced collections are `schoolDesk` ×20, `leatherChair` ×2, `teacherDesk`,
    `ceilingLamp` ×6, `basicRadiator` ×3, `crinkledPaper` ×13, books, a suitcase and a wall clock;
  - their geometry is (almost entirely) not in `scene.objects`, so `_assign_instance_ids` gives it no id.

  The index-0 geometry is consistent with these instances. That is **not verified cell by cell**.

  This is an accounting-universe fact, not a defect of this step. The accepted 234-object catalog does not
  include the instanced furniture: the desks and chairs that dominate the lower panorama render with Object
  Index 0. It matters for any later use of the catalog as reference or evaluation (Natural Bootstrap-1,
  Classroom validation).
- **Index-0 cells with no geometry** (3,442) lie between pitch −2.75° and 18.25°, where the RGB panorama
  shows the windows.

## Statements

- Exactly **one** canonical Classroom observation was made. No second scientific observation was run:
  no other resolution, no per-object or foveal view, no smoke-test panorama. The synthetic test used a
  factory-startup scene with no Classroom. The preflight and the scene-structure query loaded the
  Classroom without rendering.
- No controller was executed or imported. Controller-01 and Controller-02 code, the FSG code, the
  accepted renderers and Visual Language 1 are unchanged. `fov3d/` is byte-identical.
- No observation configuration, catalog, visibility, component, support, range or ranking rule was changed
  after the result. The only post-result change to a derived quantity is the authorized seed tie
  clarification (contract section 11). It moved two seeds by one cell each and was re-derived from the
  saved EXR without any render.
- There is still exactly one canonical Classroom render. The canonical EXR was not regenerated (sha256
  `4ea036fc74eab3b3ab06a0c4470c2b01740c9322de0eea522f957ddfffa172f8`).

## Interpretation (descriptive)

The glance is dominated by a few large authored surfaces:
- `beams` alone covers 24.7 % of the sphere;
- the largest five cover 63.4 %;
- the largest 25 cover 78.6 %.

Many authored objects are tiny or fragmented at 0.5°:
- 37 visible objects have under 1e-3 sr;
- 59 are split into several image components;
- `beams` and `sol` are split into 131 and 77 image components. No cause is inferred.

108 catalog objects receive no first-hit cell. Meanwhile, the instanced furniture that is perceptually
salient in RGB and range carries no catalog identity at all.

Authored-object identity here is **oracle / reference accounting, not natural segmentation ground
truth**. The tension visible in `object-boundary-overlay.png` is useful input for Natural Bootstrap-1, not a
target to reconcile. Neither "split" nor "merge" follows from it.

The old ±25° × ±20° Controller window contains support from only 24 visible objects (all from the accepted
25); 102 visible objects lie entirely outside it.

## Unresolved decisions

1. ~~Qualitative and scientific review of the glance and its figures (Luiz and Chat).~~ **ACCEPTED** (see
   "Acceptance record").
2. **Open:** whether instanced Classroom geometry (desks, chairs, lamps, …), outside the accepted 234-object
   catalog, should enter later reference or evaluation universes. Breadth-1 leaves the catalog unchanged
   and assigns no retroactive ids.

Natural Bootstrap-1 is not started.

## Acceptance record

Luiz and Chat completed the qualitative and scientific review and **accept Breadth-1** as committed at
`e2e554e`:

    BREADTH1_CLASSROOM234_SPHERICAL_GLANCE_ACCEPTED

- **Measured scientific result accepted.**
  - catalog 234; visible at 0.5° 126; no first hit 108; visible fragmented 59;
  - authored cells 222,267; point-cloud points 222,267;
  - accepted localized 25 visible 25 / 25; visible entirely outside the old Controller domain 102;
  - the largest 1 / 5 / 25 objects cover 24.7 % / 63.4 % / 78.6 % of the sphere;
  - catalog-labelled geometry 82.5 %, noncatalog rendered geometry 15.4 %, no geometry 2.1 %;
  - machine evidence: `BREADTH1_CHECKS_PASS` (26/26), and `BREADTH1_MUTATIONS_CAUGHT` (29/29 from a passing
    baseline);
  - exactly one canonical Classroom render, EXR sha256
    `4ea036fc74eab3b3ab06a0c4470c2b01740c9322de0eea522f957ddfffa172f8`.
- **Final figures accepted qualitatively:**

  | figure | sha256 |
  |---|---|
  | `overview.png` | `705265b08fda43f7c532341fee97486d2f3e494fdcf25d85365e010244454f02` |
  | `seed-direction-panorama.png` | `0266275481fa43fe61355bd87dae84066b39e77ed49005ce154458cc46d6ea0b` |

  - The four regions communicate RGB appearance, range, authored Object Index and boundaries, and the
    derived accounting with the seed directions.
  - Visual Language 1 provenance (REFERENCE / EVALUATION, ORACLE INPUT, DERIVED) is explicit.
  - The old Controller domain appears as historical context, not as the whole perceptual field.
  - The authored-object / noncatalog-geometry tension is visible and scientifically useful.
  - The seed panorama makes clear that seeds are DERIVED analysis only.
  - Minor density and small-text issues are non-blocking and are not repaired.
- **The post-run seed-tie numerical clarification (contract section 11) is accepted.** Only seeds 102
  `Rectangle018.002`, (187, 63) → (187, 62), and 177 `post-it`, (193, 463) → (193, 462), moved. No other
  scientific quantity changed.
- **The 15.4 % of noncatalog rendered geometry is an accepted scientific finding.** It is not repaired in
  Breadth-1.
- **What the catalog is.** The 234-object catalog remains an oracle / reference accounting universe:
  - it is not natural perceptual ground truth;
  - it is not an exhaustive inventory of all rendered geometry.
- **Open by intent.** How collection-instanced geometry should enter future reference or evaluation is
  left for Natural Bootstrap and later evaluation design.
- **This acceptance step** made no new observation, ran no render and did no scientific computation. It
  changed only this status record, and (in the next commit) `CLAUDE.md` and the Chat Handoff.
