# Active Bootstrap-1c — Safe-Forward Planar vs Spherical Geometry — report

**Markers.**

    ACTIVE_BOOTSTRAP1C_SAFE_FORWARD_PLANAR_SPHERICAL_COMPLETE
    ACTIVE_BOOTSTRAP1C_SAFE_FORWARD_PLANAR_SPHERICAL_ACCEPTED

**Status: ACCEPTED.** Luiz and Chat accepted AB1c after scientific, quantitative, independent code, checker / corruption
and qualitative visual review (see "Acceptance record" at the end). Within the predeclared safe-forward regime, at three
independently selected RGB-attention gazes, planar and gaze-centered spherical epipolar geometry recover the same local
metric structure under shared perfect correspondence. The accepted conclusion concerns **metric geometry**. The **image-
support parameterization** is not identical (see the acceptance record); the "interchangeable" wording under "What is
established" is read in that narrower sense. The sections below are the report as completed at `eecdbc3`, unchanged.

> **Question.** Under favorable, well-conditioned head-relative viewing geometry, do conventional planar tangent stereo
> geometry and gaze-centered spherical epipolar geometry recover the same local metric scene structure from the SAME
> binocular observations when correspondence is held perfect?

**Answer at the three frozen safe-forward gazes, with correspondence held perfect (MEASURED): yes.**
- Both representations are valid on **every** shared perfect correspondence at every gaze: common valid
  53,750 / 63,293 / 65,493 (planar-only 0, spherical-only 0).
- Direct disagreement ‖P_planar − P_spherical‖ (truth-free): median **2.95 / 1.05 / 3.57 µm**, max **8.8 / 3.6 / 11.6 µm**,
  at 4.1–5.0 m; relative median 2.4e-7 – 7.9e-7.
- The disagreement is entirely the oracle's own sub-millipixel epipolar skew. A truth-free consistency-restored control
  (the same pairs made exactly consistent) collapses it to **≤ 2.1e-12 m**.
- Post-freeze, both match Blender Position equally well: 3-D error median **0.157 / 0.125 / 0.140 mm** (planar and spherical
  equal to ≤ 0.3 µm in the median), max ≤ 0.223 mm. 100 % of pairs are within 1 mm.
- The conventional planar support is benign here: the fixed central rectified core lies 0.46–1.33° from the gaze, is
  finite and two-dimensional, and is sourced 87–100 % from the nominal raw core. At AB1a's near-baseline gaze it was a
  0.09 × 4.8 px sliver, 0 % from the nominal core.
- Conditioning is benign compared with AB1b: κ median 69–80 (AB1b gaze #1: 262), and 0.25–0.32 m of range per
  pixel-equivalent angle at ≈4.5 m (AB1b: 0.94 m).

This supports **outcome 1, BENIGN EQUIVALENCE** (section "Scientific outcome").

This is an **equivalence / control** experiment: perfect correspondence, fixed head, favorable configurations only. It
is not a competition between the representations, not a near-baseline rescue, not a natural-matcher, head-motion or
controller experiment.

**Why this is the operating regime.** AB1c does **not** propose to use spherical coordinates to compensate for poor
physical conditioning in the final active system. The intended architecture (Luiz and Chat, after AB1b) is:

    world target selected
      -> assess whether the local head-relative stereo geometry is favorable
      -> if favorable:   local stereo measurement
         if unfavorable: future head motion recentres / reorients the binocular rig so the target becomes locally
                         forward and the baseline strongly transverse; then local stereo measurement
      -> transform the measurement back to the canonical omnidirectional frame

AB1c tests only the favorable local measurement regime. AB1e will test the head-recentering consequence on the same
difficult world target as AB1a / AB1b. No controller or head action was implemented here.

Contract: `docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-contract.md` (section 23 is the pre-canonical
clarification). MEASURED means produced by the runs below. CALIBRATION-ONLY means computed from the calibration with no
scene data. PROPOSED means designed or predicted, not measured.

## Branch and commits

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (`origin` verified by `source` and check 01) |
| AB1b acceptance | `32fc9a31041ff78fbf2e4cc9b40cf7040fe19323` *Accept AB1b spherical epipolar geometry* (on `active-bootstrap/ab1b-spherical-epipolar-geometry`; `origin/main` fast-forwarded `cbdc4eb → 32fc9a3`, plain push) |
| post-AB1b roadmap = base | `c2b8373b8ba7849ad4411e28c55c31257d15f2af` *Record post-AB1b active-sensing operating strategy* (`main`) |
| branch | `active-bootstrap/ab1c-safe-forward-planar-vs-spherical`, from `c2b8373`; isolated worktree |
| contract | `d8a56aa9bad02937848a09a3bf4a2cad481bd415` *Contract AB1c safe-forward planar vs spherical geometry* (before any implementation, selection or observation) |
| implementation + contract section 23 (frozen before the canonical selection) | `03e7efe07f88cd9ce9883a5115c8a4003da3312f` *Implement AB1c safe-forward planar vs spherical geometry* |
| canonical run, figures, checks | all at `03e7efe`, clean and pushed |
| report | this commit |

## What ran

Run: `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1c-safe-forward-planar-vs-spherical/` (`RUN`).
Visuals: `/home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1c-safe-forward-planar-vs-spherical/` (`VIS`).

| # | command | status | seconds (MEASURED, process log) |
|---|---|---|---|
| 1 | `ab1c_run.py synthetic` | ok: `AB1C_SYNTHETIC_PASS` 15/15 | 1.57 |
| 2 | `ab1c_run.py rehearse` (synthetic factory-startup room only) | ok: `AB1C_REHEARSAL_PASS` 3/3 | 7.16 (Blender 3.29) |
| 3 | `ab1c_run.py source` | ok | 0.06 |
| 4 | `ab1c_run.py select` | ok | 14.95 |
| 5 | `ab1c_run.py freeze-selection` | ok | 0.03 |
| 6 | `check_ab1c.py --stage selection --write-summary` | `ACTIVE_BOOTSTRAP1C_SELECTION_CHECKS_PASS` 10/10 | (interactive) |
| 7 | `ab1c_run.py plan` | ok | 0.02 |
| 8 | `ab1c_run.py preflight` (Classroom loaded; **no render**) | ok | 0.61 |
| 9 | `ab1c_run.py acquire`: **the one canonical acquisition, three pairs** | ok | 11.79 (Blender 11.71) |
| 10 | `ab1c_run.py oracle` | ok | 0.26 |
| 11 | `ab1c_run.py freeze-correspondence` | ok | 0.03 |
| 12 | `ab1c_run.py spherical` | ok | 1.78 |
| 13 | `ab1c_run.py planar` | ok | 0.80 |
| 14 | `ab1c_run.py freeze-geometry` | ok | 0.07 |
| 15 | `ab1c_run.py compare` | ok | 0.89 |
| 16 | `ab1c_run.py evaluate` | ok | 1.19 |
| 17 | `ab1c_run.py visualize` | ok | 2.84 |
| 18 | `check_ab1c.py --corruptions --write-summary` | 45/45; corruptions 53/53; null probe clean | 196 (batch) |

`process-log.jsonl` holds exactly the 16 `ab1c_run.py` entries, each once, in the declared order, from the clean pushed
`03e7efe` (check 45). The selection check (row 6) is recorded in `selection/selection-check.json`. `plan` refuses to run
unless that check passed on the exact selection freeze. Every command is interactive except `select` and the checker with
corruptions (batch). No overnight task ran.

## Source pins

Verified by `source` and check 01 / 02 (full sha256 in the contract, section 2, and `source/source-manifest.json`
`240d80d8…`):
- **the only selection input**: NB1c `selection/attention-score.npz`
  `4bfee30e0a1a24007925c57d338627449484dffa2a9805fd13b72727c04ef552` (array `A`, float64 360 × 720). It is pinned by the
  NB1c freeze `87a3bab0…` and manifest `524f8fad…`; grid identity `d7207661…`.
- **accepted code reused read-only** (20 pins): `fsg_geometry.py` `ae3779bc…`, `fsg_stereo.py` `faebf0f1…`,
  `nb1a_guard.py`, `nb1a_spec.py`, `nb1c_spec.py`, `nb1c_attention.py`, `ab1a_spec.py`, `ab1a_render.py` `ae96164a…`,
  `ab1a_stereo.py` `c0238a73…`, `ab1b_spec.py`, `ab1b_oracle.py` `51e2ee55…`, `ab1b_geometry.py` `a125dd9c…`,
  `ab1b_visuals.py`, `ab1b_run.py` `6088ab06…` (added in section 23), `classroom_oracle1_render.py`, `render_foveated.py`,
  `bl_common.py`, `exr_lite.py`, `visual_language/style.py`, `breadth1_visuals.py`.
- **scene and head pose**: `classroom_eye.blend` `dca66a32…`; head pose `controller-01-full/bootstrap/seeds.json`
  `6ef83319…`. Only `plan` opens it, after the selection freeze.
- **accepted runs unchanged** (check 41): AB1a manifest `74eba4d6…` and visuals `d38bfdc2…`; AB1b geometry freeze
  `942707a8…` and visuals `a1216d2c…`; NB1a / NB1b / NB1c freezes.

## SAFE-FORWARD SELECTION (frozen before any render; MEASURED)

**Algorithm (contract sections 4–5).** Candidates are the 259,200 NB1c cell centres. A cell is eligible iff:
1. its centre lies within the **20° cone** about −Z (`alpha_forward = acos(d_g · f̂) ≤ 20° + 1e-12`); **and**
2. the **minimum stereo leverage** `L = sqrt(1 − d_x²)` over every one of the 65,536 nominal raw-core pixel rays of
   **both** eyes is **≥ 0.90**. These rays come from the accepted `make_calibration` (full, 2.10 m vergence, IPD 0.063,
   `baseline_projected`), calibration only.

Ranking uses the frozen NB1c score `A`, read as stored. The accepted NB1c tie rule (`1e-12` relative; smaller row, then
column) and spherical NMS (suppress `alpha + 1e-12 < D_MIN`, `D_MIN = 2 atan(√2 tan 6°) = 16.909°`) run greedily
**inside** the eligible set. K = 3. No score threshold.

| quantity | value |
|---|---|
| cells in the cone / eligible / removed by the leverage condition | 5,056 / **4,988** / 68 |
| min-core leverage over cone cells | 0.8947 … 0.9924 |
| eligibility boundary margins | \|L_min − 0.90\| ≥ 8.28e-4; \|alpha − 20°\| ≥ 8.87e-5 rad |
| independent mask (check 05, own K⁻¹ and rotations) | identical, 0 differing cells (no ambiguous cell) |
| pairwise separations of the three gazes | 28.35°, 37.32°, 16.954° (D_MIN 16.909°) |

**The three frozen gazes** (`selection/selected-gazes.json` `85c94558…`; freeze `selection/safe-forward-freeze.json`
`72d7e4b8…`):

| rank | row, col | yaw, pitch (°) | A | alpha_forward | L_center | min-core L (L / R) | B⊥ center / min-core | eligible before | ties | NMS suppressed |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 191, 322 | −18.75, −5.75 | 0.751812 | 19.582° | 0.9475 | 0.9149 / 0.9030 | 59.7 / 56.9 mm | 4,988 | 1 | 1,501 |
| 2 | 166, 373 | +6.75, +6.75 | 0.621786 | 9.535° | 0.9932 | 0.9722 / 0.9788 | 62.6 / 61.3 mm | 3,487 | 1 | 2,555 |
| 3 | 190, 397 | +18.75, −5.25 | 0.432344 | 19.446° | 0.9474 | 0.9029 / 0.9148 | 59.7 / 56.9 mm | 932 | 1 | 378 |

Margins to the best eligible score outside the tie set are 1.95e-3, 1.41e-3 and 3.26e-2, far above the 1e-12 tie
window. The selection guard read exactly the attention raster (0 violations; cv2 not loaded). No gaze was replaced after
selection. Gazes 1 and 3 lie near the cone rim, symmetric about the head midline. Gaze 2 is near forward.

## OBSERVATIONS (MEASURED)

**Preflight** (no render): EYE pose |Δ| = 0 (R and origin); the three Blender-built calibrations equal the planned ones
(|Δ| = 0); OPTIX, 256 spp, Depth and Normal off.

**One acquisition, three binocular pairs** (2026-10-05T00:32:43–50Z, one Blender process; seeds L 2111, R 2112):

| gaze | render seconds L / R | `rgb-observation.npz` | `calibration.json` |
|---|---|---|---|
| 1 | 1.81 / 1.28 | `d6e2a532acf1534ed305ad63447b30b35645051a350922cbcec14dbb5388f47f` | `ae56ef33…` |
| 2 | 1.65 / 1.21 | `297c5bd689cde4a5bf9b01b53e4b643719feff6f654a25a470a2e8b627bca43d` | `ab348665…` |
| 3 | 1.60 / 1.19 | `5924f94656b6bf3536ed986f2d47433331e201d7ea911c3df7f1ef52c57a170c` | `085ff332…` |

Each RGB observation holds exactly `rgb_L`, `rgb_R`, equal to the EXR Combined channels (check 14). As declared up front
(contract section 6), the raw EXRs hold Combined, Position and Object Index plus the 11 pinned inherited Classroom passes.
They stay in `evaluation_only/`. Planar and spherical geometry used these same saved observations. Nothing was rendered
per representation.

Scene content (display; see `binocular-observations.png`):
- gaze 1: a wall panel corner with a chair and a desk edge;
- gaze 2: the lettered strip above the blackboard and the board's upper left;
- gaze 3: the blackboard's lower part and the wainscot.

## PERFECT / ORACLE CORRESPONDENCE — one shared product per gaze (MEASURED)

The accepted AB1b oracle (`ab1b_oracle.compute_oracle`, unchanged), guarded per gaze. Data reads were exactly that
gaze's `calibration.json` and `reference-observation.npz`.

| sequential attrition | gaze 1 | gaze 2 | gaze 3 |
|---|---|---|---|
| left core total | 65,536 | 65,536 | 65,536 |
| finite left geometric hit | 65,536 | 65,536 | 65,536 |
| positive left instance id | **55,002** | 63,898 | 65,536 |
| right projectable / inside padded right raster | 55,002 / 55,002 | 63,898 / 63,898 | 65,536 / 65,536 |
| same-instance binocular-visible = **final** | **53,750 (0.820)** | **63,293 (0.966)** | **65,493 (0.999)** |
| matches outside the right nominal core (padded margin in use) | 3,009 | 5,439 | 5,634 |

- The **positive-instance rule removed 10,534 left hits (16.1 % of the core) at gaze 1** and 1,638 (2.5 %) at gaze 2.
  These are Object Index 0, non-catalog geometry: the hatched chair and desk in `common-correspondences.png`. The contract
  (section 7) anticipated this. It is reported for judgment; the rule is unchanged.
- The products hold exactly `left_core_row`, `left_core_col`, `uv_L`, `uv_R` (continuous):
  - gaze 1 `e83eaa7b…`;
  - gaze 2 `fd4568d5…`;
  - gaze 3 `67d43331…`.
- All three were frozen by `oracle/correspondence-freeze.json` `e7f06f53…` before either geometry ran.

## TRUTH-FREE SPHERICAL EPIPOLAR RECONSTRUCTION (MEASURED; accepted AB1b geometry)

Guarded per gaze: data reads exactly the calibration and the frozen product; Position / Object Index reads 0; cv2,
`fsg_stereo`, `ab1a_stereo` and `ab1c_planar` not loaded.

| quantity | gaze 1 | gaze 2 | gaze 3 |
|---|---|---|---|
| raw-core rays represented / pole-singular | 65,536 / 0 | 65,536 / 0 | 65,536 / 0 |
| triangulated (epipolar / ray-ray) | 53,750 / 53,750 | 63,293 / 63,293 | 65,493 / 65,493 |
| θ_g (from +X) | 108.65° | 83.30° | 71.33° |
| raw-core leverage sin θ min / median | 0.915 / 0.952 | 0.972 / 0.991 | 0.903 / 0.943 |
| \|φ_R − φ_L\| median / max [rad] | 4.46e-7 / 5.52e-7 | 4.03e-7 / 5.03e-7 | 6.00e-7 / 6.82e-7 |
| δθ median [mrad]; δθ > 0 | 12.47; all | 14.44; all | 13.12; all |
| κ median (p95) | 80.2 (84.0) | 69.2 (71.6) | 76.2 (82.2) |
| range per pixel-equivalent angle, median | 0.316 m | 0.246 m | 0.283 m |
| reconstructed left range | 4.44–5.00 m | 4.13–4.51 m | 4.32–4.82 m |
| \|P_epi − P_ray\| max | 9.5e-9 m | 5.7e-9 m | 1.3e-8 m |

## TRUTH-FREE PLANAR RECONSTRUCTION (MEASURED; accepted AB1a rectification)

`fsg_stereo.rectification` (cv2.stereoRectify, `CALIB_ZERO_DISPARITY`, alpha −1, 640 × 640), not tuned per gaze. Raw →
rectified by the accepted matrices. Q reprojection and `rect_to_head`. Guarded per gaze: data reads exactly the
calibration and the frozen product; Position / Object Index reads 0; no SGBM, no matcher.

| quantity | gaze 1 | gaze 2 | gaze 3 |
|---|---|---|---|
| valid planar / correspondences | 53,750 / 53,750 | 63,293 / 63,293 | 65,493 / 65,493 |
| in front of both rectified image planes | all | all | all |
| rectification rotation L / R | 17.83° / 19.46° | 7.56° / 5.85° | 19.48° / 17.85° |
| rectified principal point x (raster 640) | 762.4 px | 166.4 px | −123.8 px |
| disparity median (range) | 16.83 px (16.54–18.93) | 17.91 px (17.59–18.64) | 17.95 px (17.71–18.26) |
| \|rectified row residual\| median / max | 5.4e-4 / 6.8e-4 px | 4.9e-4 / 6.2e-4 px | 7.3e-4 / 8.4e-4 px |
| range per disparity pixel, median | 0.285 m | 0.242 m | 0.254 m |
| pairs inside the fixed central rectified core (descriptive) | 43,497 (80.9 %) | 59,718 (94.4 %) | 54,634 (83.4 %) |

**Planar support diagnostic (CALIBRATION-ONLY; accepted `ab1a_stereo.prelook_geometry`; descriptive, no threshold):**

| left eye | gaze 1 | gaze 2 | gaze 3 | AB1a gaze #1 (accepted) |
|---|---|---|---|---|
| rectified-core pixels from the nominal raw core | 57,088 (0.871) | 63,466 (0.968) | 65,536 (1.000) | 0 |
| raw source of the rectified core, x / y [px] | 164.3–390.1 / 195.9–443.1 | 184.0–435.1 / 191.2–447.8 | 214.2–439.6 / 195.6–443.4 | 623.98–624.07 / 317.1–321.9 |
| rectified-core centre from gaze / from baseline | 1.33° / 70.0° | 0.46° / 82.8° | 1.33° / 70.0° | 14.26° / 1.05° |
| finite / two-dimensional | yes / yes | yes / yes | yes / yes | — / no (0.09 × 4.8 px) |

The right eye is the mirror image: 65,536 / 58,880 / 57,088 rectified-core pixels from its nominal core. In the declared
favorable regime the conventional planar rectification behaves benignly. It does **not** repeat AB1a's catastrophic
support displacement.

## GEOMETRY FREEZE (MEASURED)

`freeze/geometry-freeze.json` `1b7e2207…` hashes, for all three gazes:
- the product, every spherical and planar output and guard record, and the calibrations;
- the code and the configurations.

Recorded preconditions: both geometries read exactly the calibration and the same frozen product (equal hashes); Position
/ Object Index reads 0; violations 0; spherical without cv2.

## PRIMARY: DIRECT PLANAR vs SPHERICAL AGREEMENT (MEASURED; truth-free)

`compare` ran after the geometry freeze and before any Position was reopened. Its guard opened no truth file.
It works over the common valid set of the one shared product per gaze (`comparison/comparison-summary.json` `ed36bd57…`).

| gaze | perfect corr. | planar valid | spherical valid | common | ‖ΔP‖ min / median / p90 / p95 / p99 / max | signed radial median (p05 … p95) | relative median |
|---|---|---|---|---|---|---|---|
| 1 | 53,750 | 53,750 | 53,750 | 53,750 | 0.86 / **2.95** / 5.40 / 6.14 / 7.30 / **8.82** µm | −0.88 µm (−5.4 … +5.1) | 6.2e-7 |
| 2 | 63,293 | 63,293 | 63,293 | 63,293 | 0.71 / **1.05** / 1.91 / 2.22 / 2.73 / **3.63** µm | +0.02 µm (−1.7 … +1.7) | 2.4e-7 |
| 3 | 65,493 | 65,493 | 65,493 | 65,493 | 1.17 / **3.57** / 7.06 / 8.08 / 9.57 / **11.64** µm | +0.02 µm (−7.1 … +6.8) | 7.9e-7 |
| pooled | 182,536 | — | — | 182,536 | 0.71 / 2.09 / — / 6.74 / 8.73 / 11.64 µm | −0.06 µm | 4.6e-7 |

**Decomposition (truth-free; contract section 23).** The oracle pairs the left pixel centre with the projection of the
Position sample, which lies ≈ 5–7e-4 px off that ray. Measured skew:
- \|φ residual\| median 4.0–6.0e-7 rad;
- \|row residual\| median 4.9–7.3e-4 px.

The spherical route places the point on the mean epipolar plane. The planar route places it on the left ray's
rectified row. The **consistency-restored control** (the left-ray point at the spherical range, projected into the right
camera, re-triangulated by both) gives ‖ΔP‖ max **2.09e-12 / 1.75e-12 / 7.8e-13 m**. So the two geometries are the same
function of consistent rays; the µm-level disagreement is the oracle's skew, resolved differently.

The reprojection residuals show the same split. P_planar reprojects to the left pixel centre exactly (median ≈ 1e-13 px)
and carries the skew on the right (median 5–7e-4 px). P_spherical splits it (≈ 2.4–3.5e-4 px on each side).

## SECONDARY: POST-FREEZE REFERENCE / EVALUATION (MEASURED; descriptive)

`evaluate` ran after the freeze and comparison verified. Ordered guard events:

    (frozen reads) -> geometry_freeze_verified -> reference_access_begins -> reference-observation.npz ×3 -> catalog

There were 0 violations. The frozen geometry and the comparison were re-verified afterwards. P_truth is the left Position
at the saved left-core indices, in the head frame.

| gaze | method | pairs | 3-D error min / median / p90 / p95 / p99 / max [mm] | signed radial median | within 1 mm |
|---|---|---|---|---|---|
| 1 | planar | 53,750 | 0.107 / **0.157** / 0.178 / 0.183 / 0.193 / 0.216 | +0.157 mm | 1.000 |
| 1 | spherical | 53,750 | 0.107 / **0.157** / 0.178 / 0.184 / 0.193 / 0.218 | +0.157 mm | 1.000 |
| 2 | planar | 63,293 | 0.090 / **0.125** / 0.133 / 0.136 / 0.142 / 0.160 | +0.125 mm | 1.000 |
| 2 | spherical | 63,293 | 0.089 / **0.125** / 0.133 / 0.136 / 0.142 / 0.157 | +0.125 mm | 1.000 |
| 3 | planar | 65,493 | 0.095 / **0.140** / 0.158 / 0.164 / 0.174 / 0.215 | +0.140 mm | 1.000 |
| 3 | spherical | 65,493 | 0.095 / **0.140** / 0.159 / 0.166 / 0.178 / 0.223 | +0.140 mm | 1.000 |
| pooled | planar / spherical | 182,536 | median 0.137 / 0.137; p95 0.173 / 0.174; max 0.216 / 0.223 | | 1.000 / 1.000 |

The error is a small positive radial bias, essentially identical for both representations. It is consistent with the
AB1b post-run supporting diagnostic (Blender Position ≈ 7.8e-4 px off the pixel centre, amplified by the conditioning).
At ≈ 3.5× better conditioning than AB1b's gaze #1 (range per pixel 0.25–0.32 m against 0.94 m), the error is ≈ 3× smaller
(0.13–0.16 mm against 0.41 mm). This is an interpretation; it was not separately diagnosed here.

Composition (catalog names, descriptive):
- gaze 1: woodBase 44,210, plank 7,424, wall.008 1,601, wall 515;
- gaze 2: blackBoard 30,329, wall.008 18,651, boardFrame 7,045, blackBoardLamp 3,516, …;
- gaze 3: blackBoard 34,304, woodBase 26,021, boardFrame 4,101, wallPlug.001 1,067.

## Scientific outcome (contract section 12)

My reading, for Luiz and Chat to judge: **Outcome 1, BENIGN EQUIVALENCE.** At all three predeclared safe-forward
observations:
- both representations preserve the useful foveal support;
- both are valid on every shared perfect correspondence;
- they reconstruct it consistently. The direct agreement (median 1–4 µm, max ≤ 12 µm at ≈4.5 m) is about 40× below the
  reference precision (≈ 0.14 mm). The consistency-restored control shows it is entirely accounted for by the oracle's
  sub-millipixel skew.

Outcomes 2, 3 and 4 do not occur:
- planar support is benign and planar metric reconstruction is coherent;
- spherical geometry is coherent;
- every gaze has substantial binocular support (82–100 % of the core).

## Statements

- **No natural matcher ran** (no SGBM, matcher, refinement or `compute_natural`; check 38).
- **No head motion ran.** One fixed head pose in every calibration, equal to the accepted head pose (check 39).
- **No controller ran** (no Controller-01 / 02, FSG6f, fusion or surface growth; check 39).
- **No gaze was replaced after selection.** The three frozen gazes are exactly the planned, observed and analysed ones
  (checks 10, 13).
- Exactly three new foveal observations, one per gaze, from one acquisition. No second pair for either representation, no
  full-scene render, no panorama, no sweep (checks 12, 40).
- Selection used only the frozen NB1c attention and calibration-only geometry.
- Both geometries read only calibration and the shared frozen product. Position / Object Index entered only the oracle
  (ORACLE INPUT) and the post-freeze evaluation (REFERENCE / EVALUATION).
- Accepted code and products are unchanged (checks 01, 41).

## Visual products (Visual Language 1)

Persistent, under `VIS`. Drawn at `03e7efe`. Check 36 regenerates them byte-identically.

| file | truth badges | sha256 |
|---|---|---|
| `overview.png` | ORACLE INPUT, DERIVED, REFERENCE / EVALUATION | `0b62d77bbf0c8f5cfaf82c541ca5051abd90dd88abd456295873fa67571177c6` |
| `safe-forward-selection.png` | ORACLE INPUT, DERIVED | `bd9a18d9ad4d4e91f6870057e8ed4037c26eda974c6a82ecc0fad7d563676d51` |
| `binocular-observations.png` | ORACLE INPUT | `6198d8863b2781039dcef37b220f833e03fef12a55bf377a26101a4e8b34ea79` |
| `planar-support.png` | DERIVED | `6f2f0b5b85357c48891658f838fc5a87953cb3a23f6e27dce0d3982ea888af1a` |
| `spherical-support.png` | DERIVED | `feb130a7b9b09a79bd3a89bf5ce539be0e87506121e28297e6bc5f8e8c2792da` |
| `common-correspondences.png` | ORACLE INPUT, DERIVED | `53a880be2172b454905b1f1efa0ae6402573a03e9f860aeac69c7cacccefce84` |
| `planar-vs-spherical-difference.png` | DERIVED | `13a7c1c389a9470d10487a85aae28318fa91c10d16c297975f041a9ce95ab263` |
| `paired-reconstruction.png` | DERIVED | `28562ec6bf71bc0818ba7a2e1778e776afd7d7149d3ffd08df445e180a07ec87` |
| `truth-error.png` | REFERENCE / EVALUATION, DERIVED | `0f6335aca73bdb1d3d73fab94b803d2874db3ac0fdab0a6a8325b0fe6842d563` |
| `conditioning.png` | DERIVED | `e6d48e99c236bc4b902fd95484190face2d498c7d27c1ceebe54fc23c47808a3` |
| `visuals-manifest.json` | — | `a533366986f6027114b694562d92f7c59bfc47fe486ff7bde0773f07f6b45311` |

The overview asks: *in the favorable regime, do planar and spherical geometry measure the same thing from the same
photons?* It has four regions:
- **A — SAFE-FORWARD SELECTION:** the frozen NB1c attention near −Z, the 20° cone, the hatched ineligible region, the
  three numbered gazes with D_MIN rings, and −Z / +X. It carries the caption label EXPERIMENT SELECTION (dashed outline),
  explained as the predeclared rule, not a controller and not a new Visual Language 1 class.
- **B — SAME PHYSICAL OBSERVATIONS:** the three raw L / R pairs with the nominal core.
- **C — PLANAR vs SPHERICAL:** per gaze, the raw source of the planar rectified core (orange) against the nominal core,
  and the shared correspondence support (green; hatched = no perfect correspondence).
- **D — METRIC COMPARISON:** the overlaid reconstructions, the ‖ΔP‖ map over the core, the direct and control
  statistics, the post-freeze truth errors and the conditioning.

`planar-vs-spherical-difference.png` shows the difference vectors magnified ×1e4 (stated on the panel). Nothing is
CONTROLLER-TIME.

Regenerate the figures with:

    .venv/bin/python tools/active_bootstrap/ab1c_run.py visualize --run RUN --visuals VIS

## Machine evidence

Under `RUN` (the other files are listed above and in `manifest.json` `21640f6a…`):

| file | sha256 |
|---|---|
| `selection/safe-forward-mask.npz` | `519fd9db8f3f51eef2f83c6f4305bda16fcf4c7225ebc958062566ce5d7ee2cf` |
| `selection/nms-rounds.json` | `d5c1b8dcce04480dcc3f673a059b796bb85bebf56192dbaad152afd85819be04` |
| `selection/selection-summary.json` | `26bd19f52904aed0ab366d2c37d21deb474789ea52faf2679ada5d9daf57fbed` |
| `selection/selection-check.json` | `1effe0752bd4ddde7053f0cd25bcfe6a6a0ff13e4c07c74fd14c66589bd66630` |
| `plan/plan-record.json` | `3d5e798fca945c204005e924d633dffcc8b086300bb1db7445791e6cff9d6f1b` |
| `preflight/preflight.json` | `ec1942b99910fb45a04c1e508995ec830612f1bc0f234ea22edbed665c02da27` |
| `observations/evaluation_only/instance-catalog.json` | `948dd8d4c1824e5acf6a3a179b7a8a6d4b39134dda041861dbb8193fe3d3df4a` |
| `evaluation/evaluation-summary.json` | `80c1cab10c83558d81d313d05560dc6f1ecae0bee34deb0c24305f9436a04f2c` |
| `synthetic/synthetic-report.json` | `df7f19d44368bec31e100a82a54d859e2233c12ae8345e668f1af6cba4885ff9` |
| `synthetic/blender-rehearsal/rehearsal-report.json` | `fcc4ebf9923ef3b4bfeebbb91e2c90725f5a3228c7c1edce354f0642acdbbc0c` |
| `check-summary.json` | `95715b44d5d5859c25ff2b205d35a06a0a42e015891a47b04b66117e96661a49` |

## Checks (MEASURED)

`tools/active_bootstrap/check_ab1c.py` at `03e7efe`: **45/45** (`ACTIVE_BOOTSTRAP1C_CHECKS_PASS`; `check-summary.json`).
The pre-render `--stage selection` run passed 10/10 (`ACTIVE_BOOTSTRAP1C_SELECTION_CHECKS_PASS`) before any Blender
process.

The checker keeps its own literal constants and independently recomputes:
- the cone (atan2) for every cell;
- the full-core leverage for every cone cell (its own K⁻¹ and camera rotations, vectorised);
- the mask, its own NMS and the gaze records;
- the planned calibrations;
- the oracle per gaze;
- θ (|b × d|) and φ (complex argument), the law-of-sines triangulation, Cramer's ray-ray rule and γ (atan2);
- its own `cv2.stereoRectify` call, `cv2.undistortPoints`, an in-front test and a Z = f′B/d reconstruction;
- the support diagnostic (its own rectification maps and angles);
- the common set and the direct statistics, P_truth, the errors, the reprojection and the summaries;
- the figures, byte for byte.

It also audits:
- the guard records, the ordered events, the freezes and the run order;
- the generator sources (AST: no truth identifier in the selection or geometry paths, no matcher, controller or
  head-motion identifier);
- the EXR pass set, the head pose and the changed tracked files.

**Corruption / mutation suite: 53/53 caught from a passing baseline** (`ACTIVE_BOOTSTRAP1C_MUTATIONS_CAUGHT`; none not
applicable). A **null probe** (an unmodified mirror) passed all 45 checks first, so every catch is probative. The probes
cover:
- **selection:** a hand-picked gaze; a gaze outside the cone; a gaze violating the leverage; K; D_MIN (regenerated); the
  tie rule (regenerated); an altered attention ordering; a mask value; the selection reading the head-pose record;
- **observation:** a gaze changed after the freeze; a second pair for one representation; IPD; head moved; a planned
  calibration; a Depth pass;
- **correspondence:** different products for planar and spherical; `uv_R` rounded; right match restricted to the nominal
  core; same-instance removed; Position / instance / depth in the product; the product modified after its freeze;
- **planar:** eye order; rectification flags / alpha; R1 transposed; the support diagnostic; truth injected;
- **spherical:** φ sign; θ from −Z; baseline flipped; truth injected; Position opened;
- **freeze / evaluation:** geometry edited after the freeze; Position before the freeze; a comparison statistic; P_truth;
  a truth-error statistic; a reprojection statistic; a summary distribution; κ; the common mask;
- **visual:** a pixel; a truth badge;
- **records:** a natural matcher in a generator; a controller command; accepted FSG / AB1b sources; an undeclared file; a
  failed synthetic case; the attrition; the run order; a step run twice.

Other gates:
- layout 567/567 (at `03e7efe` and with this report);
- `scripts/verify_baseline.sh` 9/9;
- `git diff --check` clean.

**Known answers before the canonical selection** (MEASURED at `03e7efe`; synthetic data and the synthetic room only):

Synthetic 15/15:
- exact stereo across the 12° core: planar ≤ 4.3e-12 m, spherical ≤ 6.8e-14 m, mutual ≤ 4.3e-12 m;
- the three safe-forward synthetic gazes satisfy the envelope and are exact;
- correspondence identity; wrong eye order (spherical exactly −P);
- wrong baseline sign (spherical −P; planar behind the camera);
- changed IPD (the exact 64/63 scale laws, and the 0.5 mm planar − spherical gap);
- φ sign error; planar convention changes (R1 transposed; non-zero-disparity Q);
- truth fields rejected by both;
- both geometries refused when they open Position;
- the selector's six known directions; NMS = the accepted NB1c rule, eligibility, ties, the exact D_MIN boundary, the
  budget error;
- common-set accounting;
- the support diagnostic reproduces the accepted AB1a gaze-#1 values (0; 14.26°; 1.05°; not 2-D);
- end-to-end analytic planes: exact set; error median ≈ 1e-6 m; float32 pairs within 2.9e-7 m; exact control 1.4e-12 m.

**Blender rehearsal 3/3** (synthetic room, 64 spp):
- passes exactly Combined / Position / Object Index;
- Position ≤ 8.7e-4 px from the pixel centre;
- 65,536 common pairs per gaze;
- planar vs spherical ≤ 1.47 µm, consistency-restored ≤ 6.7e-13 m;
- truth median ≈ 0.03 mm.

## Incidents and deviations

1. **Pre-canonical clarification (contract section 23, in `03e7efe`, before the canonical selection; within section
   21).**
   - Synthetic case 15 first failed: planar vs spherical was 2.9e-7 m against the declared 1e-8 m.
   - Diagnosis: the two triangulations are exact for consistent rays (case 1: 4e-12 m). Float32 Position (and Blender's
     ≈ 8e-4 px offset in the rehearsal) makes the oracle pairs slightly skew. The two routes resolve that skew differently.
   - The two software known-answer tolerances were corrected:
     - case 15: 1e-6 m for float32 data, plus an exact control at 1e-8 m;
     - rehearsal: 1e-5 m (was 1e-6 m), plus a consistency-restored control at 1e-8 m.
   - The PROPOSED expectation "float64 round-off" was revised to "micrometre-level". The measured Classroom result is
     micrometre-level.
   - No scientific definition, rule, envelope or metric changed. The consistency-restored control was added to the
     truth-free comparison as a descriptive field.
2. **Pin added:** `tools/active_bootstrap/ab1b_run.py` (the accepted AB1b analytic test scene, reused by the known
   answers).
3. **EXR pass-name parsing.** The first rehearsal parsed `ViewLayer.Combined` as a pass name. It now uses the accepted
   AB1a rule (`viewlayer.pass.channel`). Fixed before the implementation commit.
4. **Checker defects found on development data and fixed before the implementation commit:**
   - check 37 matched "CONTROLLER-TIME" inside the manifest's own explanatory sentence; it now inspects the badges;
   - checks 18, 19, 32 and 40 compared absolute paths, so in a corruption mirror they failed by construction, making
     their catches non-probative. They now compare run-relative paths, and a null probe guards the suite.
5. **Development runs** (scratch, not committed; no Classroom data, no Classroom render):
   - a synthetic attention raster drove the full stage sequence;
   - the canonical Blender mode ran inside the accepted synthetic room;
   - there the checker gave 45/45 and the corruptions 52/52 (+1 not applicable: no occlusion in the room).
   - The calibration-only eligibility counts (5,056 cone cells, 4,988 eligible) are independent of the attention raster.
     They were therefore seen in development. No canonical gaze was computed or seen before the canonical `select`.
6. **Positive-instance rule at gaze 1:** 10,534 hits (16.1 %) removed (non-catalog chair / desk geometry), as anticipated
   by contract section 7. Recorded, not changed.
7. **Inherited EXR passes:** 14 passes, as declared in contract section 6. Evaluation-only; never read by any AB1c stage.
8. **Process-log scope:** the `--stage selection` checker run is not an `ab1c_run.py` command. Its result is
   `selection/selection-check.json`, which `plan` verified against the exact freeze.
9. **Stray console file:** my checker console redirect wrote `previews/active-bootstrap/ab1c-check-console.txt` next to
   the run. It was moved to the session scratchpad at once; it is not part of the run.
10. **Minor presentation issue, not repaired:** the overview's region D has empty space at its bottom.
11. **Worktrees:** AB1b was accepted from a detached worktree of `a597c89` and pushed to its branch ref and to `main`.
    AB1c used its own worktree on its branch. Both have `.venv` and `scenes/classroom` links. The shared checkout was not
    switched or mutated; only gitignored run and visual trees were written there.

## What is established

- In the declared safe-forward envelope, at the three predeclared RGB-attention gazes, the accepted planar rectification
  geometry and the accepted gaze-centered spherical epipolar geometry recover the same local metric structure from the
  same observations under perfect correspondence:
  - 100 % common validity;
  - median 1–4 µm and max ≤ 12 µm direct difference at ≈ 4.5 m;
  - the difference is fully accounted for by the oracle's sub-millipixel skew.
- In that envelope the conventional planar support is benign: finite, two-dimensional, centred within 1.4° of the gaze,
  and sourced 87–100 % from the nominal raw core.
- Conditioning in that envelope is benign compared with AB1b's near-baseline gaze: κ 69–80 against 262, and 0.25–0.32 m
  against 0.94 m per pixel-equivalent angle. The truth error (0.13–0.16 mm) is correspondingly about 3× smaller.
- Together with AB1a / AB1b, this supports the architectural reading that **representation matters at near-baseline
  gazes, and the two representations are interchangeable in the favorable regime.**

## What is NOT established

- Anything about **natural** correspondence (sub-pixel accuracy, texture, occlusion handling). AB1d is future and is not
  proposed here.
- Anything about **head motion** or recentering, or about transforming measurements back to the canonical frame (AB1e).
- That the envelope (20° cone, min-core L ≥ 0.90) is necessary, sufficient or optimal. It is a design choice; only its
  interior was sampled, at three gazes.
- Generality beyond these three gazes, this scene, this instrument (12° core, 63 mm IPD, 2.10 m vergence) and ranges of
  4.1–5.0 m.
- Measurements of non-catalog (Object Index 0) geometry. The accepted oracle excludes it; the chair and desk at gaze 1
  were not compared.
- That the truth-error bias is caused by the Blender Position offset. That is an interpretation consistent with AB1b's
  supporting diagnostic, not a separate diagnosis here.
- That the planar fixed central rectified core would host all foveal correspondences in a planar natural matcher: 81–94 %
  of the pairs fall inside it, descriptively.

## Unresolved decisions (Luiz and Chat)

1. ~~Scientific, quantitative, code and qualitative visual review of AB1c and its figures.~~ **ACCEPTED** (see
   "Acceptance record").
2. ~~Review of the pre-canonical clarification (contract section 23): two corrected synthetic / rehearsal tolerances, the
   revised PROPOSED expectation and the added consistency-restored control.~~

   **Decided:** contract section 23 is accepted as legitimate and is not reopened (see "Acceptance record").
3. ~~Whether outcome 1 settles the favorable-regime equivalence well enough for the roadmap's next step.~~

   **Decided:** geometry is now sufficiently settled for the intended favorable operating regime. The next experiment is
   Active Bootstrap-1d, safe-forward natural RGB correspondence. It tests CORRESPONDENCE, not geometry. AB1e remains
   future. The roadmap commit that follows this acceptance records the decision.
4. The oracle's positive-instance rule excluded 16 % of gaze 1's core (non-catalog furniture). Should future oracle /
   evaluation include Object Index 0 geometry (cf. Breadth-1 open item 7)?

   **Recorded, not decided.** The exclusion stays an explicit caveat of AB1c.
5. The oracle's sub-millipixel skew (Blender Position offset) now appears as the limiting term both of oracle-vs-truth
   metric checks and of planar-vs-spherical agreement. Should future perfect-correspondence experiments use an exactly
   consistent oracle (e.g. the left-ray point at the reference range)?

   **Recorded, not decided.**

## Acceptance record

Luiz and Chat completed the scientific review, the quantitative review, an independent GitHub code review, the checker /
corruption review and the qualitative inspection of the two primary figures, and **accept AB1c** as committed at
`eecdbc3`:

    ACTIVE_BOOTSTRAP1C_SAFE_FORWARD_PLANAR_SPHERICAL_ACCEPTED

- **Machine result accepted:**
  - `ACTIVE_BOOTSTRAP1C_SAFE_FORWARD_PLANAR_SPHERICAL_COMPLETE`;
  - `ACTIVE_BOOTSTRAP1C_CHECKS_PASS` 45/45;
  - `ACTIVE_BOOTSTRAP1C_MUTATIONS_CAUGHT` 53/53 from a passing baseline, with a clean unmodified-mirror null probe;
  - `ACTIVE_BOOTSTRAP1C_SELECTION_CHECKS_PASS` 10/10 before any Blender process;
  - `AB1C_SYNTHETIC_PASS` 15/15; `AB1C_REHEARSAL_PASS` 3/3.
- **Accepted scientific conclusion** (stated without strengthening):
  - Within the predeclared safe-forward operating regime, at three independently selected RGB-attention gazes,
    conventional planar and gaze-centered spherical epipolar geometry recover the same local metric structure from the
    same binocular observations under shared perfect correspondence.
  - Their direct disagreement is only micrometric and collapses to numerical precision for exactly consistent
    correspondence.
  - Therefore spherical epipolar geometry preserves the benign forward case while avoiding the near-baseline
    representation pathology demonstrated by AB1a.
- **Interpretation of the micrometre residual.** When correspondence is made geometrically consistent, the
  planar-spherical difference collapses to numerical precision. Therefore the observed micrometre disagreement arises from
  the two methods resolving the oracle's small epipolar inconsistency differently, rather than from disagreement in their
  exact metric stereo geometry.
- **Accepted measured facts** (MEASURED in the sections above; unchanged):

  | quantity | gaze 1 | gaze 2 | gaze 3 |
  |---|---|---|---|
  | correspondences = common valid (planar-only 0, spherical-only 0) | 53,750 | 63,293 | 65,493 |
  | ‖P_planar − P_spherical‖ median / p95 / max | 2.95 / 6.14 / 8.82 µm | 1.05 / 2.22 / 3.63 µm | 3.57 / 8.08 / 11.64 µm |
  | consistency-restored control, max | 2.09e-12 m | 1.75e-12 m | 7.8e-13 m |
  | 3-D error vs Blender Position median, planar / spherical | 0.157 / 0.157 mm | 0.125 / 0.125 mm | 0.140 / 0.140 mm |
  | κ median | 80.2 | 69.2 | 76.2 |
  | planar rectified core sourced from the nominal raw core | 0.871 | 0.968 | 1.000 |
  | oracle pairs inside the fixed central planar rectified core (descriptive) | 80.9 % | 94.4 % | 83.4 % |

- **Two distinct statements are preserved:**
  - **METRIC GEOMETRY: benign equivalence established.** Both geometries reconstruct the same points from the same shared
    correspondence, to micrometres, and to numerical precision for exactly consistent correspondence.
  - **IMAGE-SUPPORT PARAMETERIZATION: not identical.** The conventional planar support is benign in the safe-forward
    regime (finite, two-dimensional, within 1.4° of the gaze), but it is not the nominal raw support: its fixed central
    rectified core is sourced 0.871 / 0.968 / 1.000 from the nominal raw core, and only about 81 % / 94 % / 83 % of the
    oracle pairs lie inside it.

  AB1c does **not** establish that the whole fixed-crop planar stereo pipeline is interchangeable with spherical stereo.
- **Contract section 23 accepted as legitimate; not reopened.** The pre-canonical clarification occurred before the
  canonical Classroom selection. It changed software known-answer tolerances (synthetic case 15, the Blender rehearsal)
  and a PROPOSED numerical expectation only. It did not change the safe-forward envelope, the gaze selection, the planar
  definition, the spherical definition, the oracle semantics, the scientific metric or the success semantics. The
  exact-consistency controls remain at numerical precision.
- **Visual review accepted.** Luiz and Chat inspected the two primary figures; they satisfy the scientific-visual
  requirement:
  - `visuals/active-bootstrap/ab1c-safe-forward-planar-vs-spherical/overview.png`
    (`0b62d77bbf0c8f5cfaf82c541ca5051abd90dd88abd456295873fa67571177c6`);
  - `visuals/active-bootstrap/ab1c-safe-forward-planar-vs-spherical/planar-vs-spherical-difference.png`
    (`13a7c1c389a9470d10487a85aae28318fa91c10d16c297975f041a9ce95ab263`).
- **Caveats retained:**
  - no natural correspondence was established;
  - no head motion was tested;
  - the 20° / min-core leverage ≥ 0.90 envelope is a design choice, not proven necessary or optimal;
  - non-catalog Object Index 0 geometry was excluded by the inherited oracle;
  - AB1c does not establish generality beyond these three gazes, Classroom, this instrument and this range regime.
- **AB1c is complete.** Its run is the accepted record. Later steps read its frozen products; nothing is re-rendered or
  recomputed.
- **This acceptance step** made no new observation, ran no render and did no scientific computation. It changed only
  this status record, and (in the next commit) `CLAUDE.md`, the Chat Handoff and the layout checker's handoff assertion.
  The AB1c code, contract, canonical run, figures and measured numbers are unchanged.
