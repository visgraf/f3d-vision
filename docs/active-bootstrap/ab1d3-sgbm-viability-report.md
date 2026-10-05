# Active Bootstrap-1d3 — One-Shot SGBM Viability — report

**Marker.**

    ACTIVE_BOOTSTRAP1D3_SGBM_VIABILITY_COMPLETE

**Status: REVIEW PENDING.** Luiz and Chat make the project decision (ADOPT SGBM, or PERFECT MATCHER → NORTH STAR). No
ACCEPTED marker is written, and the branch is not merged.

> **Question.** On the SAME accepted 4096-spp safe-forward Classroom observations, does the already-tested semi-global
> SGBM mechanism resolve enough of the residual spatial correspondence ambiguity to provide coherent and operationally
> useful local metric geometry?

**Answer (MEASURED, one frozen configuration, one run): SGBM resolves the correspondence ambiguity almost completely
where it answers, but the resulting metric geometry at these ranges is not at the 12–50 mm scale.**

- **Correspondence:** whatever SGBM returns is within 1 pixel-equivalent for 96.7 / 98.4 / 99.9 % of the evaluable
  outputs. The primitive matcher reached 35.9 / 66.6 / 49.2 %. Catastrophic errors (> 10 px) fall from 58 / 27 / 45 % to
  0 / 1 pixel / 0, and the valid output is spatially coherent.
- **Coverage:** SGBM answers for 19.7 / 82.4 / 82.4 % of the full oracle.
  - At gaze 1, 79 % of the oracle lies beyond the frozen z_rect ≤ 4.5 m operating interval.
  - At gazes 2 and 3, the whole oracle is inside it.
- **Metric:** the median 3-D error against the perfect reconstruction is 103 / 66 / 86 mm.
  - The fraction within 12 mm is 6.9 / 11.5 / 8.1 % of the outputs (precision), and 1.4 / 9.4 / 6.6 % of the full
    oracle (effective coverage).
  - At these ranges (4.3–4.6 m) one pixel-equivalent is 0.25–0.30 m of range. The measured 3-D error equals the
    pixel-equivalent error times that conditioning (ratio 0.99–1.01). 12 mm would need about 0.04–0.05 px.
  - Where both matchers are right (≤ 1 px), SGBM's sub-pixel precision is worse than the primitive's (3-D median
    94 / 60 / 78 mm vs 69 / 31 / 44 mm).

My reading is Outcome 2: SGBM strongly reduces the ambiguity, but the result is not operationally sufficient at the
12 / 25 / 50 mm map scales. See "Outcome reading". Luiz and Chat decide.

## Provenance

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (verified by `source` and check 01) |
| AB1d2 acceptance | `f65c6ac8344bfcfb0491888bf8608471d2452f61` (`ACTIVE_BOOTSTRAP1D2_4096SPP_OBSERVATION_QUALITY_ACCEPTED`) |
| base (post-AB1d2 roadmap, `main`) | `56606b8d4a51361f4fb729306ed73bf23b8ffaf3` |
| branch | `active-bootstrap/ab1d3-sgbm-viability`, from `56606b8`; isolated worktree |
| contract | `492232e810b75099708b466a1f3b603f4f1dbba9` (before any SGBM on a Classroom pixel) |
| implementation | `924db53ab6c1ca174abd0220098d7a1d4e1ed318` (every canonical stage ran from it, clean and pushed) |
| report | this commit |

Run `RUN` = `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1d3-sgbm-viability/` (153 MB; manifest `1c542f4c…`).
Visuals `VIS` = `/home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1d3-sgbm-viability/`.

## What ran (MEASURED, `process-log.jsonl`; each stage once, in order, from `924db53`, clean and pushed)

| # | command | result | seconds |
|---|---|---|---|
| 1 | `ab1d3_run.py source` | 18 code pins, 9 AB1d2 observation pins, 9 AB1d2 run pins, AB1c benchmark (manifest only); numDisparities 112 at every gaze; AB1d2 acceptance verified | 0.07 |
| 2 | `ab1d3_run.py preflight` | `AB1D3_PREFLIGHT_PASS` 38/38 | 12.3 |
| 3 | `ab1d3_run.py sgbm` | THE one SGBM execution; reads exactly calibration + 4096 RGB; frozen configuration recorded; truth reads 0 | 2.3 |
| 4 | `ab1d3_run.py raw-core-adapter` | products 18,118 / 54,018 / 53,998; truth reads 0 | 1.0 |
| 5 | `ab1d3_run.py freeze-correspondence` | 24 files hashed (`c3a8abd8…`) | 0.08 |
| 6 | `ab1d3_run.py spherical` | the accepted AB1b geometry; all pairs triangulated; \|φ residual\| max 2.97e-16 rad; no cv2, no matcher | 1.3 |
| 7 | `ab1d3_run.py freeze-geometry` | 15 files hashed (`b6423acd…`); truth reads 0 | 0.08 |
| 8 | `ab1d3_run.py evaluate` | post-freeze, AB1c benchmark + AB1d2 evaluation | 1.9 |
| 9 | `ab1d3_run.py visualize` | 5 figures | 1.8 |
| 10 | `check_ab1d3.py --corruptions --write-summary` | 34/34; null probe clean; corruptions 46/46 | 107 (batch) |

**Runtime (MEASURED, `sgbm/<g>/sgbm-summary.json`):** SGBM computation per gaze 0.194 / 0.188 / 0.166 s (both
directions, refinement and validity on the full 640 × 640 raster); 0.55 s total. The whole canonical pipeline took 20 s,
of which the preflight took 12 s. Interactive class; the contract's PROPOSED cost held. The checker with corruptions took
107 s, against the proposed 3–5 min.

## Proof of exact AB1d2 observation reuse (MEASURED; `source`, checks 03 and 05)

- **Pinned inputs.** The matcher read exactly these `rgb-observation.npz` files, each beside its pinned
  `calibration.json`, from the accepted AB1d2 run:
  - gaze 1: `9d653bd1fa1bb2d1d59847b0a55c1b43603b5628beb3bc70f29975d4e57bf02c`;
  - gaze 2: `3046cc66f67494b5f639380c46f25672c2259684f28511ba5366f872986e4bba`;
  - gaze 3: `fd9ecd4ed94b8c6fdc91a1dd7501840da2934b335387515b10098dc69497ce75`.
- **Agreement with AB1d2's records.** The hashes equal the AB1d2 observation freeze (`7c8ed0a3…`, spp 4096) and the
  AB1d2 manifest (`5ace0ab7…`), and the AB1d2 render control is `ok`.
- **No new observation.** No Blender process ran, there is no render import or non-git subprocess in the AB1d3 code, and
  there is no new RGB or EXR in `RUN`.
- **Matcher inputs re-derived.** The SGBM input arrays (recorded sha256 of the 640 × 640 uint8 gray pair) equal the
  checker's own `linear_to_u8` gray of the remapped 4096 RGB (check 08).

## The frozen SGBM configuration (MEASURED: recorded from the created OpenCV objects, `sgbm/<g>/sgbm-calls.json`)

| parameter | value (identical at the three gazes) |
|---|---|
| matcher / mode | OpenCV `StereoSGBM`, `getMode()` = 2 (`STEREO_SGBM_MODE_SGBM_3WAY`) |
| blockSize / P1 / P2 | 5 / 200 / 800 |
| preFilterCap / uniquenessRatio / disp12MaxDiff | 31 / 10 / −1 |
| speckleWindowSize / speckleRange | 0 / 1 |
| minDisparity / numDisparities | 0 / 112 (left → right); −111 / 112 (right → left, accepted LR logic) |
| matched arrays | full 640 × 640 uint8 gray pair; the right → left call matched the same pair swapped |
| rectification | one `stereoRectify` per gaze, flags 1024 (`CALIB_ZERO_DISPARITY`), alpha −1, newImageSize 640 × 640 |
| z_rect interval / LR / texture | [0.75, 4.5] m / ≤ 1.0 px / ≥ 0.5 u8 |
| refinement | 3 iterations, step ≤ 0.5 px, total ≤ 0.75 px (max \|refined − discrete\| on supported pixels = 0.75 px at every gaze) |
| ROI / support / identity guard | `getValidDisparityROI` / `fsg_stereo.support_mask` / none |
| tripwires (`StereoBM_create`, `filterSpeckles`, `validateDisparity`, `reprojectImageTo3D`) | 0 calls |

The checker re-assembled the whole matcher from its own literals and its own OpenCV calls on the 4096 RGB: own relative
pose and rectification, own SGBM objects, own written-out refinement, and own terms. It reproduced the record exactly:
- discrete disparity bitwise;
- refined disparity difference 0;
- all nine terms and the validity: 0 differing pixels.

No parameter was changed, swept or tuned.

## Raw-core adapter validation

- **Before the canonical run** (preflight; calibration-only on the three accepted calibrations), all MEASURED:
  - raw → rectified → raw round trip ≤ 2.3e-13 px;
  - analytic perfect correspondence (tilted plane) over the full raw core ≤ 6.5e-12 px;
  - the inverse equals OpenCV's own `initUndistortRectifyMap` to ≤ 4.3e-5 px.
- **Adapter mutations that fail as they must:**
  - R2 transposed: ≥ 255 px;
  - the rectified intrinsic used as the raw one: ≥ 153 px;
  - the right focal × 1.001: 0.13 px;
  - the disparity sign flipped: ≥ 65 px;
  - one invalid source pixel rejects exactly the 4 samples whose footprint holds it;
  - uv_L moved by 1e-9 px is rejected by the accepted validator.
- **On the canonical run** (checks 13–16):
  - The checker's independent adapter (own map, own footprint, own bilinear weights, a linear-solve inverse) reproduces
    the product: same valid set, uv_R within 1e-9 px.
  - uv_L is the exact raw centre, every uv_R is inside the raster, and the accepted AB1b validator passes.
  - Every product sample's four footprint pixels are fully SGBM-valid.
  - The attrition is recomputed exactly.
  - Epipolar consistency of the adapted pairs: |φ_R − φ_L| ≤ 3e-16 rad.
  - SECONDARY: SGBM's own planar-Q reconstruction of the same pair agrees with the spherical one to ≤ 2.0e-12 m.

## Attrition per gaze (MEASURED, `correspondence/<g>/adapter-summary.json`; footprint = all four bilinear pixels)

| stage (implementation order) | gaze 1 | gaze 2 | gaze 3 |
|---|---|---|---|
| raw core | 65,536 | 65,536 | 65,536 |
| rectifiable | 65,536 | 65,536 | 65,536 |
| footprint SGBM-left valid | 63,709 | 64,593 | 65,536 |
| + right valid | 63,174 | 64,007 | 65,536 |
| + calibration support | 63,174 | 64,007 | 65,536 |
| + inside raster | 63,174 | 64,007 | 65,536 |
| + LR ≤ 1 px | 53,850 | 55,183 | 55,848 |
| + texture ≥ 0.5 u8 | 51,284 | 54,879 | 54,537 |
| + finite | 51,284 | 54,879 | 54,537 |
| + z_rect ∈ [0.75, 4.5] m | **18,118** | 54,018 | 53,998 |
| + ROI | 18,118 | 54,018 | 53,998 |
| raw right in front / inside the raster | 18,118 | 54,018 | 53,998 |
| **final product** | **18,118** | **54,018** | **53,998** |

The LR check removes 9–15 % of the core at every gaze. At gaze 1 the frozen z_rect interval removes 33,166 more pixels:
the back wall lies beyond 4.5 m (`disparity-validity.png`, blue). On the full rectified raster, SGBM-left is valid for
329,820 / 334,917 / 333,054 of 409,600 pixels, and the full validity holds for 180,991 / 235,977 / 252,732.

## Full oracle vs serviceable oracle accounting (MEASURED, post-freeze)

| gaze | full oracle \|O\| | serviceable \|S\| | S / O | SGBM valid | valid ∩ O (evaluable) | valid ∩ S | full-oracle coverage | serviceable coverage | valid, no oracle |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 53,750 | 11,226 | 0.209 | 18,118 | 10,591 | 7,603 | **0.197** | 0.677 | 7,527 |
| 2 | 63,293 | 63,293 | 1.000 | 54,018 | 52,165 | 52,165 | **0.824** | 0.824 | 1,853 |
| 3 | 65,493 | 65,493 | 1.000 | 53,998 | 53,963 | 53,963 | **0.824** | 0.824 | 35 |

- **What limits serviceability.** Every serviceable term is met by every oracle pair (left and right footprint support,
  ROI, disparity range) except z_rect: 11,226 / 63,293 / 65,493.
- **Gaze 1 is an end-to-end coverage limitation of the frozen operating interval, not wrong SGBM peaks.** 79 % of its
  oracle lies beyond z_rect 4.5 m.
- **The scene sits close to the upper bound.** On the valid raster, the median z_rect is 3.86 / 4.28 / 4.23 m and the
  median refined disparity is 19.9 / 17.9 / 18.1 px, against a 4.5 m bound at 17.05 px.

## Primary correspondence result (MEASURED; the AB1d / AB1d2 definitions; evaluable outputs E = valid ∩ O)

| gaze | \|E\| | median px-equiv | p90 | p95 | p99 | max | ≤ 0.10 | ≤ 0.25 | ≤ 0.50 | ≤ 1.00 | > 10 px | > 100 px |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 10,591 | 0.341 | 0.799 | 0.916 | 5.31 | 6.69 | 0.169 | 0.395 | 0.659 | **0.967** | 0 | 0 |
| 2 | 52,165 | 0.267 | 0.660 | 0.777 | 1.10 | 80.6 | 0.222 | 0.476 | 0.774 | **0.984** | 1 px | 0 |
| 3 | 53,963 | 0.303 | 0.657 | 0.722 | 0.835 | 1.54 | 0.188 | 0.427 | 0.740 | **0.999** | 0 | 0 |

(Fractions are precision over E.)

**Effective coverage over the full oracle** (correct ≤ x px / \|O\|):

| gaze | ≤ 0.10 | ≤ 0.25 | ≤ 0.50 | ≤ 1.00 |
|---|---|---|---|---|
| 1 | 0.033 | 0.078 | 0.130 | 0.191 |
| 2 | 0.183 | 0.392 | 0.638 | 0.811 |
| 3 | 0.155 | 0.352 | 0.610 | 0.823 |

| gaze | \|e_θ\| median / p90 / p95 / p99 / max [mrad] | signed px-equiv p05 / median / p95 |
|---|---|---|
| 1 | 0.278 / 0.653 / 0.747 / 4.32 / 5.46 | −0.457 / **+0.217** / +0.915 |
| 2 | 0.218 / 0.539 / 0.635 / 0.895 / 65.1 | −0.624 / −0.020 / +0.704 |
| 3 | 0.247 / 0.537 / 0.590 / 0.682 / 1.25 | −0.634 / −0.038 / +0.684 |

**SGBM quantities at the product** (bilinear; median / p95 / max):

| gaze | LR residual [px] | raw fixed-point disparity [1/16 px] | refined disparity [px] | refinement Δ [px] |
|---|---|---|---|---|
| 1 | 0.220 / 0.611 / 0.959 | 292.6 / 369.0 / 378.4 | 18.46 / 23.36 / 23.96 | +0.157 / 0.750 / 0.750 |
| 2 | 0.169 / 0.570 / 0.969 | 288.0 / 293.5 / 1616.1 | 17.90 / 18.75 / 100.5 | −0.115 / 0.654 / 0.750 |
| 3 | 0.199 / 0.597 / 0.982 | 288.0 / 289.0 / 301.4 | 17.86 / 18.74 / 19.58 | −0.135 / 0.725 / 0.750 |

## Operational metric result (MEASURED; P_SGBM_spherical vs the accepted AB1c perfect reconstruction)

| gaze | median | p75 | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| 1 | 103.1 mm | 184.4 mm | 239.2 mm | 276.2 mm | 1.19 m | 1.43 m |
| 2 | 65.6 mm | 116.8 mm | 161.9 mm | 189.0 mm | 261.4 mm | 3.56 m |
| 3 | 86.3 mm | 144.9 mm | 184.8 mm | 202.2 mm | 228.4 mm | 397.5 mm |

Against Position the values agree to < 0.2 mm in the median: 103.0 / 65.6 / 86.3 mm. Radial signed medians:
−65.7 / +4.9 / +10.8 mm.

### Precision AND effective coverage at 12 / 25 / 50 / 100 mm

| gaze | 12 mm: precision / effective | 25 mm | 50 mm | 100 mm |
|---|---|---|---|---|
| 1 | 0.069 / **0.014** | 0.141 / 0.028 | 0.272 / 0.054 | 0.488 / 0.096 |
| 2 | 0.115 / **0.094** | 0.226 / 0.186 | 0.405 / 0.334 | 0.678 / 0.559 |
| 3 | 0.081 / **0.066** | 0.166 / 0.137 | 0.313 / 0.258 | 0.565 / 0.466 |
| pooled | 0.095 / 0.061 | 0.190 / 0.122 | 0.350 / 0.224 | 0.609 / 0.389 |

Precision = correct / SGBM evaluable; effective = correct / full oracle. Pooled values are over the 116,719 evaluable
outputs of the 182,536 oracle pairs.

## Direct comparison with the accepted AB1d2 primitive matcher (MEASURED, same oracle pixels, same 4096-spp photons)

| gaze | matcher | valid | oracle coverage | median px | ≤ 0.25 | ≤ 0.50 | ≤ 1.00 | median 3-D | ≤ 12 mm | ≤ 25 mm | ≤ 50 mm | > 10 px | > 100 px |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | primitive | 65,431 | 0.998 | 26.40 | 0.227 | 0.321 | 0.359 | 3.283 m | 0.042 / 0.042 | 0.086 / 0.086 | 0.162 / 0.162 | 0.577 | 0.306 |
| 1 | **SGBM** | 18,118 | 0.197 | **0.341** | 0.395 | 0.659 | **0.967** | 103.1 mm | 0.069 / 0.014 | 0.141 / 0.028 | 0.272 / 0.054 | **0** | **0** |
| 2 | primitive | 65,484 | 0.999 | 0.258 | 0.493 | 0.626 | 0.666 | 63.8 mm | 0.147 / 0.147 | 0.278 / 0.277 | 0.442 / 0.441 | 0.271 | 0.096 |
| 2 | **SGBM** | 54,018 | 0.824 | 0.267 | 0.476 | 0.774 | **0.984** | 65.6 mm | 0.115 / 0.094 | 0.226 / 0.186 | 0.405 / 0.334 | **0.00002** | **0** |
| 3 | primitive | 65,531 | 1.000 | 1.748 | 0.335 | 0.454 | 0.492 | 482.3 mm | 0.073 / 0.073 | 0.148 / 0.148 | 0.267 / 0.267 | 0.452 | 0.319 |
| 3 | **SGBM** | 53,998 | 0.824 | **0.303** | 0.427 | 0.740 | **0.999** | 86.3 mm | 0.081 / 0.066 | 0.166 / 0.137 | 0.313 / 0.258 | **0** | **0** |

px and catastrophic fractions are precision over each matcher's evaluable output. The metric columns give
"precision / effective coverage".

**≤ 1 px categories on the full oracle** (correct = evaluable and ≤ 1 px; no output = not correct):

| gaze | both correct | primitive only | SGBM only | neither |
|---|---|---|---|---|
| 1 | 3,855 (0.072) | 15,394 (0.286) | 6,388 (0.119) | 28,113 (0.523) |
| 2 | 38,844 (0.614) | 3,257 (0.051) | 12,470 (0.197) | 8,722 (0.138) |
| 3 | 28,356 (0.433) | 3,843 (0.059) | 25,549 (0.390) | 7,745 (0.118) |

**On the common evaluable set**, median |err| goes primitive → SGBM 13.49 → 0.34 px, 0.20 → 0.27 px and 0.57 → 0.30 px.
Within 1 px goes 0.366 → 0.967, 0.747 → 0.984 and 0.526 → 0.999.

**Did spatial aggregation resolve the residual ambiguity? Yes, where SGBM answers.** The along-epipolar false winners
that dominated the primitive matcher (> 100 px for 10–32 % of its outputs) are gone. The "primitive only" pixels (5–29 %)
are where SGBM gives no output: 99.9 / 97.2 / 99.6 % of them (MEASURED post-run from `evaluation-result.npz`), through
the gaze-1 z_rect cut and the LR rejections. They are not SGBM errors.

## Spatial / catastrophic-error analysis (MEASURED, post-freeze)

- **Catastrophic errors.**
  - **> 100 px:** 0 / 0 / 0.
  - **> 10 px:** 0 / 1 / 0. The one gaze-2 pixel (80.6 px) is isolated and adjacent to an invalid output pixel.
  - The p99 of 5.3 px at gaze 1 comes from the z_rect truncation below.
- **Coherence of the valid output** (8-connected components):

  | gaze | components | largest | fraction of the output in components ≥ 50 px |
  |---|---|---|---|
  | 1 | 568 | 7,372 | 0.844 |
  | 2 | 48 | 53,774 | 0.995 |
  | 3 | 11 | 53,980 | 1.000 |

- **Where outputs are missing.** At gazes 2 and 3 the gaps are mostly LR / right-valid and SGBM-left rejections, banded
  along horizontal structures (board frame, rail, wainscot), plus scattered texture rejections (`attrition.png`).
  - 40 % (gaze 2) and 60 % (gaze 3) of the evaluable outputs lie within 2 px of an invalid output pixel.
- **Visual reading.**
  - The error maps (`overview.png` C, `metric-error.png`) show no coherent wrong surfaces.
  - The 3-D error is spatially fine-grained and follows the disparity noise, not region-level mismatches.

## Post-run descriptive diagnostics (MEASURED from the frozen run files; not contract metrics; nothing re-run)

1. **Why metric error lags correspondence: conditioning.**
   - From the spherical result (truth-free): median left range 4.60 / 4.35 / 4.56 m, and median range per
     pixel-equivalent 0.300 / 0.248 / 0.285 m/px.
   - The product |pixel-equivalent error| × range-per-px has a median of 103.2 / 66.0 / 86.9 mm. Against the measured
     3-D error the per-pixel ratio median is 1.008 / 0.993 / 0.991.
   - At this conditioning, 12 mm corresponds to 0.040 / 0.048 / 0.042 px.
2. **Gaze-1 z_rect truncation bias.**
   - The 2,988 evaluable outputs whose oracle lies just beyond 4.5 m (oracle z_rect median 4.56 m) survive only because
     their disparity is overestimated. Their signed error median is +0.72 px, radial −215 mm, 3-D median 215 mm.
   - The 7,603 evaluable outputs inside the serviceable set have a median of 0.23 px (signed +0.06) and 69.6 mm.
   - My interpretation: this is the selection effect of the frozen interval acting on a surface near its bound.
3. **SGBM outputs where the AB1c oracle has no correspondence** (7,527 / 1,853 / 35), against Position:
   - 3-D median 50.6 / 49.7 / 145.0 mm;
   - gaze 1: 226 outputs beyond 0.5 m (max 1.42 m); gaze 2: none beyond 0.5 m (max 0.38 m).

   These outputs are not in any contract metric. They would enter a persistent map.
4. **Sub-pixel precision where both matchers are right** (category "both ≤ 1 px"):
   - 3-D median SGBM 93.6 / 60.4 / 77.8 mm, against the primitive matcher's 69.3 / 30.9 / 43.8 mm.
   - The bounded refinement sits at its ±0.75 px clamp for 9.4 / 7.5 / 9.5 % of the product.

## Outcome reading (contract section 21; for Luiz and Chat to judge)

**My reading: Outcome 2.** SGBM helps substantially, but the result is not operationally sufficient for persistent scene
growth at the declared map scales.

- **Outcome-1 elements, met:**
  - spatial ambiguity is strongly reduced (≤ 1 px for 96.7–99.9 % of outputs, against 36–67 % for the primitive);
  - catastrophic false matches are essentially eliminated (0, 1 and 0 pixels > 10 px);
  - the valid output is spatially coherent (84–100 % in large components);
  - the built-in rejection works as a safety mechanism.
- **Where it falls short operationally:**
  - **Metric precision at map scales.** Within 12 mm: 7–12 % of outputs and 1–9 % of the oracle. Within 50 mm: 27–41 %
    of outputs. The median 3-D error is 66–103 mm.
  - This is set by conditioning at the 4.3–4.6 m ranges of these views (1 px ≈ 0.25–0.30 m), together with SGBM's
    sub-pixel precision (median 0.27–0.34 px). SGBM is no more precise than the primitive matcher where both are right.
  - On the ≤ 12 / 25 / 50 mm effective coverage, SGBM does not exceed the primitive matcher at any gaze.
  - **Coverage.** The full-oracle coverage is 0.20 / 0.82 / 0.82. At gaze 1 the frozen z_rect ≤ 4.5 m interval excludes
    79 % of the oracle and biases the survivors near the bound.
  - **Unevaluated outputs.** 7,527 / 1,853 / 35 outputs where no oracle exists, with medians of 5–15 cm against
    Position and 226 above 0.5 m at gaze 1.
- **Not Outcome 3:** the ambiguity reduction is large and systematic.
- **Not Outcome 4:**
  - every check passes;
  - the adapter is verified independently, by known answers and by OpenCV's own maps;
  - the configuration is recorded and re-derived bitwise.

The decision rule is Luiz and Chat's.

## Checks (MEASURED)

**`check_ab1d3.py` at `924db53`: 34/34** (`ACTIVE_BOOTSTRAP1D3_CHECKS_PASS`; `check-summary.json`
`28f0315d1cd58f68f89e5dc5f496c97ae3ad97636b3bd18a3487d4d51ca0d131`). The checker keeps its own literal pins and
constants (`check_ab1d3_core.py`). Beyond the items above, it covers:
- provenance (contract committed first and unchanged);
- the three guard records (exact reads, no truth reads, no cv2 / matcher in the spherical stage);
- both freezes and their order, and the evaluation's reference-access marks;
- the accepted spherical geometry reproduced bitwise, with the primary metric being the spherical P_epi (not planar Q);
- its own recomputation of the serviceable set (own planar map, support, ROI, Q);
- its own pixel-equivalent error: own rays and own epipolar line, with the local scale equal to AB1d2's recorded scale on
  the common pixels (relative difference 0 or ≤ 1e-12);
- precision and effective coverage, categories, spatial statistics, pooled values;
- the process: exactly one SGBM execution, from one clean pushed commit, after the preflight;
- scope: AST scan for sweep loops, other matchers, PERFECT-matcher or controller imports, and a hidden variant in the
  canonical call;
- exactly three SGBM records and three products;
- byte-identical figure regeneration, badges and hatching, and the manifest and declared changes.

**Preflight known answers: 38/38** (`preflight/preflight-report.json` `4f387882…`, same commit). They cover adapter
geometry, adapter mutations, SGBM on analytic planes, the full-raster crop equal to the accepted output, determinism,
the recorder, the checker's null probe, semi-global aggregation against a P1 = P2 = 0 control, sub-pixel disparity, wrong
eye order, ten configuration mutations detected, the truth firewall and the evaluation code.

**Repository gates at the report tree:** layout 589/589, `verify_baseline` 9/9, `check_ab1d3.py` (read-only) 34/34,
`git diff --check` clean.

## Corruptions (MEASURED): 46/46 caught

The suite ran from a passing baseline, after an unmodified-mirror **null probe** passed all 34 checks
(`ACTIVE_BOOTSTRAP1D3_MUTATIONS_CAUGHT`). Each corruption names the checks that must catch it and counts only if one of
them fails.

- **SOURCE (5):** an RGB pixel; the calibration; an oracle and a Position read during matching; a Position read in the
  adapter.
- **SGBM (12):** block size 7, P1 400, P2 1600, uniqueness 15, MODE_SGBM, preFilterCap 63, numDisparities 128, z interval
  0.75–8 m, LR 2 px, speckle 100 / 2, texture 2.0 u8, refinement bound 2.0 px.
  - Each is a genuinely mutated SGBM output for gaze 1, computed inside the temporary mirror only. None was inspected for
    performance or reported, and each was discarded.
  - Each is caught by the recorded getters, the summary audit or the literal re-assembly.
- **RECTIFICATION (5):** eye swap, baseline sign, R2ᵀ, central-crop window, a shifted disparity map.
- **ADAPTER (5):** disparity sign, wrong inverse, interpolation across invalid pixels, non-raw uv_L, uv_R outside the
  raster.
- **FREEZE (3):** correspondence and geometry mutated after their freezes; the benchmark opened early.
- **EVALUATION (8):** serviceable count and mask, ≤ 1 px count, 12-mm precision, effective coverage, an error array, the
  category map, planar Q substituted for the primary metric.
- **PROCESS (5):** a second SGBM configuration, a parameter sweep, a PERFECT-matcher import, head motion / controller, a
  hidden variant.
- **VISUAL (3):** a figure pixel, the hatching painted over, a truth badge.

## Visuals (Visual Language 1)

`VIS` (`visuals-manifest.json` `b59d3a428cf0aa10bcd6be7a962d30af86182277c123ba58da5dec8f3989a68d`):

| figure | truth badges | sha256 |
|---|---|---|
| `overview.png` | ORACLE INPUT, DERIVED, REFERENCE / EVALUATION | `91ff08b7c3093e9a42cdd6adbe6b2cfbc6edb8cca5a332f742ce020ddace3361` |
| `sgbm-vs-primitive.png` | DERIVED, REFERENCE / EVALUATION | `adda160a5225d9436dadc7e6f837900a01e69086f0941528b0bffed9886079e9` |
| `disparity-validity.png` | ORACLE INPUT, DERIVED | `11cf4a29085be2cba5892cc620e2fd15359710b82585ec763c4891a45fd80f39` |
| `metric-error.png` | DERIVED, REFERENCE / EVALUATION | `3df8dfe69236a2b9cffe4c777b7538c03f70e9482452894dfdf2be4273f1ad9e` |
| `attrition.png` | DERIVED, REFERENCE / EVALUATION | `0bda508aad7ffeaaf1e71c65c96659cd567842261ac936c4c8e7ed177eb5d975` |

- **`overview.png`** has four panels:
  - **A:** the same 4096-spp raw cores;
  - **B:** the planar rectified raster with the raw-core outline, the refined disparity and the first failing validity
    term;
  - **C:** the primitive and SGBM error maps on one log scale, and the category map;
  - **D:** the SGBM 3-D error map and the precision / effective-coverage curves for SGBM and the primitive matcher, with
    the 12 / 25 / 50 / 100 mm marks.
- **Invalid and unevaluable pixels are hatched everywhere.** No example was selected.

Regenerate: `.venv/bin/python tools/active_bootstrap/ab1d3_run.py visualize --run RUN --visuals VIS`.

## Incidents and deviations

1. **Before the contract** (development on calibration-only and synthetic data; no Classroom SGBM existed):
   - The spec first listed the 3WAY mode value as 1. Checking against OpenCV (`STEREO_SGBM_MODE_SGBM_3WAY` = 2) corrected
     it before any use.
   - A purely periodic synthetic texture showed coherent wrong locking. The "aggregation is active" known answer was
     therefore designed as a periodic band in unique texture (contract §3, §10).
   - Figure layout defects (dashed curves, label overlaps, the sign of the error-ratio map) were fixed on the synthetic
     run.
2. **Between the contract and the canonical run** (implementation commit `924db53`): a checker AST-scan false positive
   (a chained `.stdout.strip()` read as a subprocess call) was fixed. The contract is unchanged since `492232e`
   (check 01).
3. **Canonical run:** no incident. Every stage ran once, in order, from the clean pushed `924db53`. No SGBM rerun, no
   configuration change, no post-run fix to code, figures or checker.
4. **Post-run analysis:** the "Post-run descriptive diagnostics" are computed from the frozen run files and labelled as
   such. They change no contract metric.
5. **Nothing in the contract was left unrun.**

## What is established

- **On these three accepted 4096-spp views, the one frozen SGBM configuration, used as a correspondence service through
  the common raw product and the accepted spherical geometry:**
  - returns 18,118 / 54,018 / 53,998 raw-core correspondences;
  - 96.7 / 98.4 / 99.9 % of its evaluable outputs are within 1 pixel-equivalent of the oracle;
  - it has essentially no catastrophic errors;
  - its output is spatially coherent.
- **Semi-global aggregation plus SGBM's built-in rejection removes the along-epipolar false winners** that dominated the
  accepted primitive matcher on the same photons.
- **The metric error of the returned geometry is 66–103 mm (median)** at these 4.3–4.6 m ranges. It is quantitatively
  explained by the binocular conditioning (1 px ≈ 0.25–0.30 m) and SGBM's ≈ 0.3 px sub-pixel error. 7–12 % of the
  outputs are within 12 mm.
- **The frozen z_rect ≤ 4.5 m interval** removes most of gaze 1's oracle and biases its survivors near the bound.
- **The raw-core adapter is correct.** It is verified independently, by known answers and against OpenCV's maps.

## What is NOT established

- That SGBM is optimal. Equally, that another configuration, block size, uniqueness, P1 / P2, smoothing or refinement
  would or would not do better: none was run (contract §18).
- That the frozen z_rect interval suits this scene. Its effect is reported as coverage, not judged.
- The correctness of the non-oracle outputs beyond the post-run Position comparison.
- Anything about real cameras, other scenes, other gazes or ranges, head motion or the controller.
- Whether a different baseline, range or active head pose would change the metric picture. AB1d3 has no such
  manipulation.

## Unresolved decision for Luiz and Chat

    ADOPT SGBM
    or
    PERFECT MATCHER -> NORTH STAR

The measured inputs to that decision are above:
- **Correspondence:** precision ≤ 1 px 96.7 / 98.4 / 99.9 %; catastrophic 0 / 1 px / 0.
- **Coverage:** 0.197 / 0.824 / 0.824 of the full oracle.
- **Metric:**
  - ≤ 12 mm: precision 0.069 / 0.115 / 0.081, effective 0.014 / 0.094 / 0.066;
  - ≤ 25 mm: precision 0.141 / 0.226 / 0.166, effective 0.028 / 0.186 / 0.137;
  - ≤ 50 mm: precision 0.272 / 0.405 / 0.313, effective 0.054 / 0.334 / 0.258.
- **Spatial coherence:** high.
- **Unevaluated outputs:** 7,527 / 1,853 / 35, against Position medians of 5–15 cm.

This report makes no SGBM parameter recommendation and does not design a next matcher.
