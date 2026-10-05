# Active Bootstrap-1d3 — One-Shot SGBM Viability — contract

**Status: CONTRACT (frozen before any canonical SGBM execution).** Committed before the canonical SGBM run, before any
inspection of canonical SGBM disparity, and before any inspection of canonical SGBM geometry. Completion marker (written
only by the report): `ACTIVE_BOOTSTRAP1D3_SGBM_VIABILITY_COMPLETE`. No ACCEPTED marker is written by Claude Code.

Decision context (recorded on `main` at `56606b8`, "Active Bootstrap after AB1d2: the SGBM bet"): natural stereo receives
ONE additional bounded attempt. If SGBM is judged operationally useful, it becomes the current natural correspondence
service and stereo development stops; otherwise natural-stereo development stops, natural stereo becomes a deferred
research topic, and the North Star full Classroom demonstration uses the already validated PERFECT / oracle
correspondence service. This contract does not make that judgment; Luiz and Chat make it from the report.

## 1. One pragmatic question

> On the SAME accepted 4096-spp safe-forward Classroom observations, does the already-tested semi-global SGBM mechanism
> resolve enough of the residual spatial correspondence ambiguity to provide coherent and operationally useful local
> metric geometry?

A VIABILITY test. ONE frozen SGBM configuration, ONE canonical run, ONE result. It is NOT: an SGBM research project, an
SGBM parameter optimization, a comparison of many stereo algorithms, a parameter sweep, a confidence-fusion experiment, a
learned stereo experiment, a head-motion experiment, a new observation or a new attention experiment.

## 2. Provenance and branch

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (the legacy `fov-3d-vision` is never used) |
| base (accepted `main`: AB1d2 accepted + post-AB1d2 roadmap) | `56606b8d4a51361f4fb729306ed73bf23b8ffaf3` |
| AB1d2 acceptance | `f65c6ac8344bfcfb0491888bf8608471d2452f61` (`ACTIVE_BOOTSTRAP1D2_4096SPP_OBSERVATION_QUALITY_ACCEPTED`) |
| branch | `active-bootstrap/ab1d3-sgbm-viability`, from the base, in an isolated worktree |
| run (`RUN`) | `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1d3-sgbm-viability/` |
| visuals (`VIS`) | `/home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1d3-sgbm-viability/` |

The implementation commit writes this contract's commit SHA into `ab1d3_spec.CONTRACT_COMMIT` and the checker's literal
`CONTRACT`; the checker requires the contract file to be unchanged from that commit to the checked tree.

## 3. Pre-contract development (disclosed)

Before this commit, development used ONLY:

- accepted source code and accepted reports;
- calibration-only data of the three accepted gazes (`calibration.json`; rectification, disparity range, raw-core
  footprint in the rectified raster);
- analytic synthetic scenes (the accepted `ab1a_run.render_planes` textured planes) rendered through those calibrations,
  including a scratchpad-only synthetic run (two planes, synthetic oracle) used to exercise the stages, the evaluation and
  the figures.

No SGBM was run on any Classroom pixel. No Classroom SGBM disparity, validity, correspondence or geometry exists or was
inspected. The AB1c oracle, Position and the AB1d2 evaluation arrays were not opened.

Calibration-only facts (identical at the three gazes): `numDisparities` = 112 (|P2[0,3]| = 76.724 px·m); the frozen
z_rect interval [0.75, 4.5] m corresponds to rectified disparity [17.05, 102.30] px; the raw 256 × 256 left core maps to
rectified u ∈ [169, 507], v ∈ [179, 460] (outside the central 256 × 256 crop of the accepted FSG / AB1a output, hence
§6c); rectification rotations 5.8–19.5°.

Synthetic finding recorded before the canonical run (§10, case "periodic band"): on a periodic stripe band embedded in
unique texture, the frozen SGBM does NOT recover the band — it rejects it (0–0.2 % valid in the band), while a
P1 = P2 = 0 control returns 9–17 % valid matches in the band, all wrong; outside the band the frozen configuration is
correct for 99.9 % vs 97.0–97.5 % for the control. On a purely periodic plane the frozen SGBM can lock coherently onto a
wrong period. These are properties of the frozen mechanism, stated before the Classroom result.

## 4. Sources (verified by `source`; a mismatch is a STOP)

### 4a. The accepted AB1d2 4096-spp observations (ORACLE INPUT; read in place, never re-rendered)

`A1D2 = previews/active-bootstrap/ab1d2-4096spp-observation-quality`

| gaze | row, col | yaw, pitch (°) | `calibration.json` sha256 | `rgb-observation.npz` sha256 |
|---|---|---|---|---|
| 1 | 191, 322 | −18.75, −5.75 | `ae56ef33…` | `9d653bd1fa1bb2d1d59847b0a55c1b43603b5628beb3bc70f29975d4e57bf02c` |
| 2 | 166, 373 | +6.75, +6.75 | `ab348665…` | `3046cc66f67494b5f639380c46f25672c2259684f28511ba5366f872986e4bba` |
| 3 | 190, 397 | +18.75, −5.25 | `085ff332…` | `fd9ecd4ed94b8c6fdc91a1dd7501840da2934b335387515b10098dc69497ce75` |

Also pinned: the AB1d2 observation freeze `7c8ed0a3…`, render-control record `9b982634…` (`ok`), the acquisition records,
the AB1d2 run manifest `5ace0ab7…`, the AB1d2 correspondence and geometry freezes (`ae98de44…`, `9447019d…`), the AB1d2
visuals manifest `3041febc…`, the AB1d2 acceptance commit (an ancestor of HEAD) and the ACCEPTED status in its report.

### 4b. The accepted AB1c benchmark (REFERENCE / EVALUATION; opened only after the geometry freeze)

The same benchmark as AB1d / AB1d2 (`ab1d_spec.BENCH_PINS`): the AB1c oracle correspondences, the AB1c perfect spherical
reconstruction and the evaluation-only Position of each gaze, verified at `source` only through the AB1c manifest
`21640f6a…`. No new oracle.

### 4c. The accepted AB1d2 primitive evaluation (REFERENCE / EVALUATION; opened only after the geometry freeze)

`A1D2/evaluation/gaze-{1,2,3}/evaluation-result.npz` (`ee844c5a…`, `8ac6781a…`, `995fc07e…`), verified at `source` only
through the AB1d2 manifest.

### 4d. Accepted code reused read-only (sha256 at the base)

`fsg_stereo.py`, `fsg_geometry.py`, `ab1a_stereo.py`, `ab1a_spec.py`, `ab1a_run.py` (synthetic plane renderer),
`ab1b_geometry.py`, `ab1b_spec.py`, `ab1c_planar.py`, `ab1c_spec.py`, `ab1d_match.py` (evaluation line geometry only),
`ab1d_spec.py`, `ab1d_run.py` (`run_spherical_gaze`), `ab1d2_spec.py`, `ab1b_visuals.py`, `ab1c_visuals.py`,
`nb1a_guard.py`, `visual_language/style.py`, `classroom_oracle/breadth1_visuals.py` (pins in `ab1d3_spec.SOURCE_PINS`).
None is modified.

## 5. No new observation

No Blender, no render, no new gaze, no new seeds, no denoising, no head motion. The matcher reads `calibration.json` and
`rgb-observation.npz` (exactly `rgb_L`, `rgb_R`) of each gaze — nothing else. No Position, no Object Index, no oracle, no
evaluation, no PERFECT matcher at inference.

## 6. The ONE frozen SGBM configuration

### 6a. Configuration (the accepted FSG / AB1a natural RGB-only matcher; not invented, not tuned)

| parameter | value |
|---|---|
| matcher | OpenCV `StereoSGBM` |
| mode | `STEREO_SGBM_MODE_SGBM_3WAY` (OpenCV value 2) |
| blockSize | 5 |
| P1 / P2 | 8 · 5² = 200 / 32 · 5² = 800 |
| preFilterCap | 31 |
| uniquenessRatio | 10 |
| disp12MaxDiff | −1 (inside OpenCV) |
| speckleWindowSize / speckleRange | 0 / 1 (no speckle filtering) |
| minDisparity | 0 (left → right); right → left: −(minDisparity + numDisparities − 1) = −111 (accepted LR logic) |
| numDisparities | ceil((ceil(\|P2[0,3]\| / z_rect_min) + 4) / 16) · 16 = 112 at the three calibrations |
| z_rect operating interval | [0.75, 4.5] m — the previously accepted, fixed, NON-oracle interval; not recomputed, not expanded |
| left-right consistency | ≤ 1.0 px |
| minimum local std | 0.5 u8 (5 × 5 box on the rectified gray) |
| bounded photometric refinement | 3 Gauss-Newton iterations, each update ≤ 0.5 px, total ≤ 0.75 px (`fsg_stereo.refine_disparity`) |
| disparity ROI | `cv2.getValidDisparityROI(roi_L, roi_R, minDisparity, numDisparities, blockSize)` |
| calibration support | `fsg_stereo.support_mask` (calibration-derived) |
| identity / instance guard | NONE |

### 6b. Photometric / rectification path (accepted, unchanged)

For each gaze: raw linear RGB → `fsg_stereo.rectification` (`cv2.stereoRectify`, `CALIB_ZERO_DISPARITY`, `alpha = −1`,
`newImageSize` 640 × 640; `cv2.initUndistortRectifyMap` `CV_32FC1`) → `cv2.remap` `INTER_LINEAR` → `linear_to_u8` →
`cv2.cvtColor(RGB2GRAY)` → full 640 × 640 SGBM, left → right and right → left. No crop before SGBM.

### 6c. The output window

The matcher IS the accepted `ab1a_stereo.compute_natural`, called unchanged. It computes every array on the full
640 × 640 rectified raster and, at return, crops them to `rectification(c)["crop_xywh"]` (the central 256 × 256).
`ab1d3_sgbm.full_raster_view` reports that window as the full raster for the duration of one call. R1, R2, P1, P2, Q, the
maps, the ROI, the disparity range and every computed value are untouched. Known answer (§10): the central crop of the
full-raster output equals the accepted `compute_natural` output bitwise.

### 6d. Validity (frozen; the accepted AB1a RGB-only terms, in implementation order)

`term_sgbm_left` (SGBM left valid), `term_right_valid` (right disparity valid and right-supported at the matched point),
`term_support_left` (calibration support), `term_inside_raster` (0 ≤ u_R < W − 1), `term_lr` (LR ≤ 1 px),
`term_texture` (std ≥ 0.5 u8), `term_finite` (finite reconstruction), `term_z_range` (z_rect ∈ [0.75, 4.5] m),
`term_roi` (valid-disparity ROI). Full validity is their AND. No semantic mask, Object Index, oracle occlusion test, new
confidence threshold, speckle filter or uniqueness threshold is added. The built-in rejection is part of the matcher
under test.

### 6e. Runtime proof of the configuration

`ab1d3_sgbm.Recorder` wraps the OpenCV entry points during the SGBM call and records: every `StereoSGBM_create` (its
keyword arguments and the created object's own getters: mode, blockSize, P1, P2, preFilterCap, uniquenessRatio,
disp12MaxDiff, speckleWindowSize, speckleRange, minDisparity, numDisparities), the shape, dtype and sha256 of every array
pair SGBM matches, every `stereoRectify` call (flags, alpha, newImageSize), the map and ROI calls. Tripwires (must never
be called): `StereoBM_create`, `filterSpeckles`, `validateDisparity`, `reprojectImageTo3D`.

## 7. Why planar rectification is allowed here

AB1c established that, in the SAFE-FORWARD regime, planar and spherical metric geometry are benignly equivalent. SGBM may
therefore use conventional planar rectification internally. This does not reverse the decision to keep spherical
geometry as the common downstream representation: SGBM, the PERFECT matcher and any future matcher supply the SAME
truth-free raw correspondence product, and the controller / persistent map does not depend on SGBM.

## 8. The raw-core correspondence adapter (frozen)

The canonical output is the accepted AB1b truth-free product: `left_core_row`, `left_core_col`, `uv_L` (EXACTLY the raw
left pixel centre (col + 192, row + 192)), `uv_R`. For each of the 65,536 raw left-core pixels, in core order:

1. **Left rectified coordinate:** `ab1c_planar.to_rectified(K_L, R1, P1, uv_L)` (accepted AB1c geometry; continuous).
2. **Rectifiable:** finite, rectified-camera depth `w_L > 1e-12`, and the 2 × 2 bilinear footprint
   {x0, x0 + 1} × {y0, y0 + 1} (x0 = floor(u), y0 = floor(v)) inside the 640 × 640 raster.
3. **Sampling (frozen):** bilinear interpolation of the full REFINED SGBM disparity. Valid ONLY if all FOUR footprint
   pixels satisfy the full SGBM validity (every §6d term), whatever their bilinear weights. No interpolation across an
   invalid SGBM pixel.
4. `u_rect_R = u_rect_L − d`, `v_rect_R = v_rect_L`.
5. **Rectified → raw right:** column form `d_raw_R ∝ R2ᵀ K_rect⁻¹ (u_rect_R, v_rect_R, 1)ᵀ` with `K_rect = P2[:, :3]`,
   `uv_R = project(K_R d_raw_R)`; in the repository's row-vector form `d_raw = (q K_rect⁻ᵀ) R2`. The convention is
   verified independently (§10: round trip, analytic perfect correspondence, OpenCV's own maps).
6. **Raw validity:** finite, raw-camera z > 1e-12, 0 ≤ u_R ≤ W − 1, 0 ≤ v_R ≤ H − 1.
7. The product (valid rows only, core order) must pass `ab1b_geometry.validate_product` unchanged. No truth field.

The adapter recomputes the accepted rectification from the calibration and requires it to equal the SGBM record bitwise.
SGBM's own planar Q reconstruction of the same adapted pair is stored in the adapter record as a SECONDARY diagnostic
only.

## 9. Freeze before truth

Canonical order: `source` → `preflight` (known answers) → `sgbm` → `raw-core-adapter` → `freeze-correspondence` →
`spherical` → `freeze-geometry` → `evaluate` → `visualize`. Before the correspondence freeze and before the geometry
freeze: oracle reads 0, Position reads 0, Object Index reads 0 (allowlist guards `nb1a_guard.OpenGuard`; every open is
recorded and classified). The SGBM stage reads exactly calibration + RGB; the adapter exactly calibration + its own SGBM
record; the spherical stage exactly calibration + the frozen product (no cv2, no matcher module loaded). The evaluation
records a `freezes_verified` mark and a `reference_access_begins` mark; no reference file is opened before the latter.

## 10. Preflight known answers (before any canonical SGBM; synthetic and calibration-only data)

`ab1d3_run.py preflight` (`ab1d3_synthetic.run_preflight`) must pass from the same clean commit as the canonical stages.
Software tolerances are declared in `ab1d3_spec` (no Classroom-derived tuning). Cases:

- **Adapter (the three accepted calibrations):** raw → rectified → raw round trip (≤ 1e-9 px); analytic perfect
  correspondence on a tilted plane (its rectified disparity is affine in (u, v), so bilinear sampling is exact) over the
  full raw core (≤ 1e-6 px); the inverse equals OpenCV's own `initUndistortRectifyMap` (≤ 2e-3 px, float32 maps).
- **Adapter mutations that must fail:** R2 transposed; the rectified intrinsic K_rect used as the raw right intrinsic;
  the right focal scaled by 1.001 (the eyes share K in these calibrations, so a swapped eye intrinsic is a no-op);
  disparity sign flipped. One invalid SGBM source pixel rejects exactly the raw-core samples whose footprint holds it
  (the sampling-across-invalid mutation would accept them). uv_L moved by 1e-9 px or 0.5 px is rejected by the accepted
  validator. The checker's independent adapter agrees (≤ 1e-9 px) and detects R2ᵀ and sign mutations.
- **SGBM (analytic textured planes):** a fronto-parallel plane at z_rect 2 m (forward calibration) and the same plane
  through the three accepted calibrations: valid ≥ 0.90 of the raw core, |median disparity error| ≤ 0.05 px, p95 ≤ 0.5 px
  (the accepted AB1a thresholds), spherical 3-D median ≤ 5 mm, φ residual ≤ 1e-9 rad; the full-raster window's crop equals
  the accepted output bitwise; determinism (bitwise); the recorder sees exactly §6a; the checker's audit is silent on the
  unmutated run (null probe).
- **Semi-global aggregation is active** (periodic band in unique texture vs a P1 = P2 = 0 control, three calibrations):
  the output differs from the control; correct-and-valid outside the band gains ≥ 0.02; wrong-and-valid inside the band
  ≤ 0.05 and ≤ the control's. Recovery of the band itself is recorded, not required (§3).
- **Known sub-pixel disparity 40.3 px:** median refined error ≤ 0.05 px; |refined − discrete| ≤ 0.75 px; refinement
  active; unsupported pixels unchanged.
- **Must fail:** wrong eye order; adapter disparity sign; adapter R2ᵀ (on the SGBM scene).
- **The checker detects** (calls audit, summary audit and the literal re-assembly): block size 7; uniquenessRatio 15;
  P1 / P2 400 / 1600; MODE_SGBM; numDisparities 128; z interval 0.5–6 m; LR disabled; texture threshold 2.0 u8; speckle
  filtering 100 / 2; refinement 5 iterations / 2.0 px.
- **Truth firewall:** a truth-bearing matcher input (Position / Object Index keys) is refused; the guarded SGBM stage reads
  exactly calibration + RGB (positive control); a Position read and an oracle read inside the SGBM stage, and an oracle
  read inside the adapter, are refused and counted; the spherical geometry refuses an unfrozen product.
- **Evaluation code** (synthetic two-plane scene with a synthetic oracle; a near plane in range, a far plane at z_rect
  6 m beyond the frozen interval): far-plane oracle points are never serviceable; SGBM output on them ≤ 1 %; median
  |pixel-equivalent error| ≤ 0.2 px; pixel-equivalent ≈ focal approximation (ratio 0.95–1.05); the four categories
  partition the oracle; effective coverage ≤ precision; the secondary planar-Q diagnostic ≤ 1e-9 m; a +2 px shift of uv_R
  shows as 1.8–2.2 px.

## 11. Spherical geometry downstream (accepted AB1b; unchanged)

The truth-stripped SGBM product is fed to the accepted AB1b spherical geometry (`ab1d_run.run_spherical_gaze`):
P_SGBM_spherical from raw uv_L, uv_R. SGBM's planar Q reconstruction never defines the primary metric result.

## 12. Post-freeze reference sets (evaluation only)

- **A. Full oracle set O:** every accepted AB1c perfect correspondence in the raw left core.
- **B. SGBM-serviceable oracle set S ⊆ O:** the oracle pair, through the accepted planar geometry, lies inside the frozen
  SGBM operating domain: the bilinear footprint of `to_rectified(uv_L)` inside the raster with all four pixels in the
  left calibration support and inside the valid-disparity ROI; the footprint of `to_rectified(uv_R_oracle)` inside the
  raster with all four pixels in the right calibration support; 0 ≤ d = u_rect_L − u_rect_R ≤ numDisparities − 1; Q
  reprojection finite with z_rect ∈ [0.75, 4.5] m. An oracle outside S is NOT a wrong SGBM peak; it IS reported as an
  end-to-end coverage limitation.
- **C. SGBM valid ∩ oracle E:** the accuracy-evaluable outputs.

## 13. Primary correspondence measurements (the AB1d / AB1d2 definitions)

`e_θ = θ_R(SGBM) − θ_R(oracle)`; pixel-equivalent error `e_θ / s`, where `s` is the θ_R change over one pixel of the
AB1d matcher's calibration-only raw right epipolar line at ORACLE-ON-CURVE (θ_R oracle at φ_L) — computed with the
accepted `ab1d_match` geometry; the checker requires it to equal AB1d2's recorded local scale on common pixels. Per gaze:
|O|, |S|, SGBM valid, |E|, |E ∩ S|, serviceable coverage |E ∩ S| / |S|, full-oracle coverage |E| / |O|; |e_θ| and
|pixel-equivalent| median / p90 / p95 / p99 / max; fractions within 0.10 / 0.25 / 0.50 / 1.00 px (precision over E and
effective coverage over O); the signed distributions; the LR residual, the raw fixed-point disparity, the refined
disparity and the refinement delta.

## 14. Operational metric measurements

P_SGBM_spherical against the accepted AB1c perfect spherical reconstruction and against post-freeze Position. Per gaze:
3-D error median / p75 / p90 / p95 / p99 / max; for 12 / 25 / 50 / 100 mm BOTH:

1. **PRECISION** = correct_within_threshold / |E|;
2. **EFFECTIVE ORACLE COVERAGE** = correct_within_threshold / |O| (and, descriptively, / |S|).

## 15. Direct comparison with the accepted AB1d2 primitive matcher

On the SAME raw-core oracle pixels (AB1d2 arrays, post-freeze): natural valid count, oracle coverage, median px error,
≤ 0.25 / 0.50 / 1.00 px, median 3-D error, ≤ 12 / 25 / 50 mm, catastrophic fractions > 10 px and > 100 px. Categories on
the full oracle (correct = evaluable and |e| ≤ 1 px; no output = not correct): both correct, primitive only, SGBM only,
neither — mapped spatially. Plus the common-evaluable medians. Not a matcher bake-off.

## 16. Attrition and spatial analysis

For the 65,536 raw left-core pixels per gaze: raw core → rectifiable → the footprint passing each §6d term cumulatively
in implementation order → raw right in front → raw right inside = product. No post-hoc filter. Spatial: 8-connected
components of the valid output and of the > 10 px / > 100 px catastrophic errors (count, largest, fraction in components
≥ 50 px), and the fraction of catastrophic pixels within 2 px of an invalid output pixel.

## 17. Visuals (Visual Language 1)

`VIS`: `overview.png` (A same 4096-spp observations; B SGBM spatial matching, planar internally, with the raw-core outline;
C raw-core correspondence quality: primitive and SGBM error maps on the same scale and the category map; D metric
consequence: 3-D error map and precision / effective-coverage curves with 12 / 25 / 50 / 100 mm marks),
`sgbm-vs-primitive.png`, `disparity-validity.png`, `metric-error.png`, `attrition.png`, and `visuals-manifest.json`. Truth
badges on every figure; invalid / unevaluable pixels hatched, never hidden; fixed display ramps identical for both
matchers; no cherry-picking. Deterministic; the checker regenerates every PNG byte-identically.

## 18. No parameter tuning (absolute)

After canonical SGBM output exists, NOTHING in §6, §8, §12–§16 changes: block size, uniquenessRatio, P1, P2,
preFilterCap, mode, disparity range, z range, LR tolerance, texture threshold, speckle settings, refinement and its bound,
rectification, interpolation, adapter validity, evaluation metrics. If SGBM performs badly, THAT IS THE RESULT. No second
configuration, no "one small change".

## 19. Checker (`tools/active_bootstrap/check_ab1d3.py` + `check_ab1d3_core.py`)

Own literal pins and constants. 34 checks: provenance (canonical repo, base, AB1d2 acceptance, contract committed first
and unchanged); pinned sources; the exact 4096-spp observations; benchmark / AB1d2 pins; no new observation (no render
imports, no non-git subprocess, no new RGB / EXR); the recorded OpenCV calls; the accepted summary and the spec's
configuration; the whole matcher re-assembled from literals (own rectification, own SGBM objects, own refinement, own
terms) on the 4096 RGB equal to the record (discrete bitwise; inputs hash-identical); the three guard records;
rectification (accepted convention, full window, 112 disparities, support, ROI); an independent adapter (own map, own
footprint, own bilinear, linear-solve inverse) reproducing the product (≤ 1e-9 px), exact uv_L, uv_R inside, accepted
validator; strict interpolation validity; attrition; epipolar consistency (φ residual ≤ 1e-9 rad) and the secondary
planar-Q (≤ 1e-6 m); both freezes and their order; the evaluation's reference-access order; the accepted spherical
geometry reproduced and the primary metric equal to the spherical P_epi; own recomputation of S, errors (own rays and own
epipolar line; scale equal to AB1d2's), precision / effective coverage, categories, spatial statistics and pooled
values; process (canonical once, in order, one clean pushed commit, exactly one SGBM execution, preflight first); scope
(no sweep loop, no other matcher, no PERFECT matcher, no controller / head motion, no hidden variant in the canonical
call); exactly three SGBM records and products; the preflight report; figures; badges and hatching; manifest and declared
changes.

## 20. Corruption / mutation suite

From a passing baseline, after an unmodified-mirror null probe passes every check; each corruption names the checks
that must catch it. Families: SOURCE (an RGB pixel; the calibration; an oracle / Position read during matching or in the
adapter); SGBM (block size, P1, P2, uniqueness, mode, preFilterCap, numDisparities, z interval, LR tolerance, speckle,
texture threshold, refinement bound — each a genuinely mutated stage output computed for one gaze inside the temporary
mirror only; never inspected for performance, never reported, discarded); RECTIFICATION (eye swap, baseline sign, R2ᵀ,
crop window, a shifted disparity map); ADAPTER (disparity sign, wrong inverse, interpolation across invalid pixels,
non-raw uv_L, uv_R outside the raster); FREEZE (correspondence or geometry mutated after its freeze; benchmark opened
early); EVALUATION (serviceable count and mask, ≤ 1 px count, 12-mm precision, effective coverage, an error array, the
category map, planar-Q substituted for the primary metric); PROCESS (a second SGBM configuration, a parameter sweep, a
PERFECT matcher import, head motion / controller, a hidden variant); VISUAL (a figure pixel, hatching painted over, a
truth badge).

## 21. Outcome semantics (no automatic accept / reject threshold)

- **Outcome 1 — SGBM is operationally useful:** spatial ambiguity strongly reduced; the valid output spatially coherent;
  catastrophic false matches sufficiently suppressed; residual error compatible enough with active surface growth.
  Decision after review: adopt SGBM; stop stereo development; return to active perception.
- **Outcome 2 — helps but not operationally sufficient:** do NOT tune SGBM; stop natural stereo; PERFECT correspondence
  for the North Star; defer stereo research.
- **Outcome 3 — does not materially help:** stop natural stereo immediately; PERFECT correspondence for the North Star.
- **Outcome 4 — experimental / adapter failure:** fix only a contract-determined implementation defect; rerun only if the
  scientific definition is unchanged.

Luiz and Chat judge from precision, coverage, catastrophic-error rate, spatial coherence, compatibility with the
12 / 25 / 50 mm active-map scales and the visuals. The report gives a reading, not a decision.

## 22. Permitted fix scope

- Before the canonical SGBM: implementation defects in the AB1d3 tools, without changing §6, §8, §12–§16 or a declared
  tolerance.
- After the canonical SGBM: presentation-only figure fixes (layout, labels; no data, statistic or transform change); a
  checker defect that false-alarms on correct data, only if the fix does not weaken the check (recorded in the report).
- Anything else — a change to the configuration, the adapter rule, the reference sets, the metrics, or a rerun of SGBM —
  is a STOP for Luiz and Chat.

## 23. Stop conditions

STOP and report if: a source / observation / benchmark pin fails; the preflight fails; a guard records a truth read or a
violation at inference; the recorded configuration differs from §6a; the adapter's recomputed rectification differs from
the SGBM record; a canonical stage would run twice; the SGBM stage takes unexpectedly long (PROPOSED < 1 min; > 5 min is a
STOP, and the algorithm is not simplified to save time); a canonical check fails for a reason other than a checker
defect.

## 24. Cost (PROPOSED, from synthetic development; MEASURED values go in the report)

SGBM ≈ 0.2 s per gaze (interactive); adapter ≈ 0.03 s per gaze; preflight ≈ 12 s; spherical, freezes and evaluation
interactive; figures ≈ 5 s; read-only checker ≈ 30 s; checker with corruptions ≈ 3–5 min (batch). No overnight task.

## 25. Commands

    RUN=/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1d3-sgbm-viability
    VIS=/home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1d3-sgbm-viability
    .venv/bin/python tools/active_bootstrap/ab1d3_run.py source                --run $RUN
    .venv/bin/python tools/active_bootstrap/ab1d3_run.py preflight             --run $RUN
    .venv/bin/python tools/active_bootstrap/ab1d3_run.py sgbm                  --run $RUN
    .venv/bin/python tools/active_bootstrap/ab1d3_run.py raw-core-adapter      --run $RUN
    .venv/bin/python tools/active_bootstrap/ab1d3_run.py freeze-correspondence --run $RUN
    .venv/bin/python tools/active_bootstrap/ab1d3_run.py spherical             --run $RUN
    .venv/bin/python tools/active_bootstrap/ab1d3_run.py freeze-geometry       --run $RUN
    .venv/bin/python tools/active_bootstrap/ab1d3_run.py evaluate              --run $RUN
    .venv/bin/python tools/active_bootstrap/ab1d3_run.py visualize             --run $RUN --visuals $VIS
    .venv/bin/python tools/active_bootstrap/check_ab1d3.py --run $RUN --visuals $VIS --corruptions --write-summary

Every canonical stage refuses to run from a dirty or unpushed commit and refuses to rerun.

## 26. Report and stop

`docs/active-bootstrap/ab1d3-sgbm-viability-report.md`, status REVIEW PENDING, marker
`ACTIVE_BOOTSTRAP1D3_SGBM_VIABILITY_COMPLETE`, no ACCEPTED marker; the items required by the step handoff (provenance,
observation reuse, configuration, runtime, adapter validation, attrition, oracle / serviceable accounting, primary and
metric results, precision AND effective coverage at 12 / 25 / 50 / 100 mm, the AB1d2 comparison, catastrophic-error
analysis, an Outcome reading, checks, corruptions, visuals with hashes, incidents, what is and is NOT established, and the
unresolved decision ADOPT SGBM vs PERFECT MATCHER → NORTH STAR). No SGBM parameter recommendation; no next matcher design.
Then STOP: no acceptance, no merge, no tuning, no other configuration, no AB1e, no PERFECT fallback, no controller.

## 27. What AB1d3 may and may not establish

May establish: how the one frozen SGBM configuration performs as a correspondence service on these three accepted
4096-spp observations, end to end through the common raw product and the accepted spherical geometry, against the same
benchmark as AB1d / AB1d2, and how it compares with the accepted primitive matcher on the same pixels.

May NOT establish: that SGBM is optimal or that another configuration would or would not do better (none is run); that
4096 spp is a sensor model; anything about real cameras, other scenes, arbitrary gazes, head motion or the controller;
that the frozen z_rect interval is appropriate for the scene (its effect is reported as coverage, not judged).
