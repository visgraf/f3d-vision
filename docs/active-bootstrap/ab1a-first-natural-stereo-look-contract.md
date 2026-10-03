# Active Bootstrap-1a — First Natural Stereo Look — contract

**Status: CONTRACT** (committed before implementation and before any acquisition). Designed by Luiz and Chat;
written down and executed by Claude Code on the workstation. Luiz and Chat decide what the measured result means.

| item | value |
|---|---|
| branch | `active-bootstrap/ab1a-first-natural-stereo-look` (isolated worktree) |
| base | accepted `main` @ `509c341ff60994ff0bf726b081be1f5c5c107b73` (NB1c accepted at `6b0ba68`; handoff `509c341`) |
| run evidence | `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1a-first-natural-stereo-look/` (`RUN`) |
| visuals | `/home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1a-first-natural-stereo-look/` (`VIS`) |
| report | `docs/active-bootstrap/ab1a-first-natural-stereo-look-report.md` |
| completion marker | `ACTIVE_BOOTSTRAP1A_FIRST_NATURAL_STEREO_LOOK_COMPLETE` (status REVIEW PENDING; never ACCEPTED here) |

Every number below is one of: **MEASURED** (from an identified run), **CALIBRATION-ONLY** (computed from the accepted
calibration code with no scene data; the canonical `prelook` command recomputes and records it), or **PROPOSED /
EXPECTED** (not yet run).

## 1. The single causal question

> Can the eye, starting from the FIRST frozen RGB candidate gaze and the fixed binocular instrument alone, obtain
> useful local metric geometry from binocular RGB without using depth, Blender identity or scene segmentation?

Scientific transition:

    coarse RGB
      -> frozen RGB candidate gaze
      -> ACTUAL binocular fixation
      -> RGB-only local stereo measurement
      -> measured local metric geometry

**Exactly one gaze is executed: one physical fixation, one binocular pair.** The experiment stops after measuring
and evaluating that fixation. No controller follows it; no second gaze; no surface growth.

## 2. What changes and what does not

Changes (new, declared files only):
- `docs/active-bootstrap/ab1a-first-natural-stereo-look-contract.md` (this file) and `-report.md`;
- `tools/active_bootstrap/ab1a_spec.py`, `ab1a_render.py`, `ab1a_stereo.py`, `ab1a_run.py`, `ab1a_visuals.py`,
  `check_ab1a.py`;
- `tools/repository/check_repository_layout.py`: the new stage directories `docs/active-bootstrap/` and
  `tools/active_bootstrap/`, the AB1a contract (required) and report / tools (allowed).

**The scientific change being tested:** the natural matcher removes the oracle part of the accepted FSG stereo
matcher — no `mask_interior`, no instance ids, no same-instance equality, no Position. Its support is
calibration-derived only.

Not changed (byte-identical; checked): `fov3d/`; the 16 sealed `tools/` root modules, in particular
`tools/fsg_geometry.py`, `tools/fsg_stereo.py`, `tools/classroom_oracle1_render.py`,
`tools/classroom_oracle1_matcher.py`, `tools/render_foveated.py`, `tools/bl_common.py`, `tools/exr_lite.py`;
`tools/controller/`, Controller-01 / Controller-02; `tools/natural_bootstrap/` (NB1a, NB1b, NB1c); the accepted NB1a,
NB1b, NB1c run trees and visuals; the Classroom scene. Nothing is retuned: not the NB1c attention mechanism, not the
instrument, not the matcher constants.

Not done: no gaze 2 or gaze 3 (gaze 3's known promise is not used); no Controller-01 / 02; no FSG6f call; no
`fsg3_surface_map`; no fusion or persistent map; no re-centred look; no NB1a range, NB1a hypotheses or NB1b classes
as measurement input; no Object Index or Blender Position during stereo inference; no semantics; no target object id.

## 3. The frozen action

Source: the accepted NB1c run `previews/natural-bootstrap-1c-rgb-candidate-gaze/` (absolute paths under the shared
checkout `/home/lvelho/rd/f3d-vision`).

| pinned item | sha256 |
|---|---|
| `selection/rgb-gaze-freeze.json` | `87a3bab01f55051316ac1eb45b48f394211f4c7a3a317fd0e61c0e52c36f9b37` |
| `selection/candidate-gazes.json` (from the accepted NB1c `manifest.json` and the freeze record) | `8041b954f7b63d97f060a41aaca5db1ec6e0c2295381523026e98d11f8a5b621` |
| `manifest.json` (accepted NB1c manifest) | `524f8fad71ccb8fd9359fa3221f4de6be3af40be8f3e5fa7cddeb482acedd87e` |

Before execution the run verifies (STOP on any mismatch) that the freeze record lists `candidate-gazes.json` with
that hash, that its seven frozen files verify, and that rank 1 is exactly:

    rank 1   row 164   col 513   yaw +76.75 deg   pitch +7.75 deg

The gaze is consumed verbatim from `candidate-gazes.json` (`yaw_deg`, `pitch_deg`); the checker also recomputes the
NB1c cell-centre convention `yaw = -180 + 0.5 (col + 0.5)`, `pitch = 90 - 0.5 (row + 0.5)`. **Action source:
frozen NB1c RGB gaze #1.** No RGB attention is recomputed, NB1c is not rerun, and the gaze is not moved or snapped.

Head frame: the gaze is a head-frame direction `d = (sin yaw cos pitch, sin pitch, -cos yaw cos pitch)` (the NB1c /
Breadth-1 / FSG convention). The head pose is the Classroom `EYE` object; the accepted record of it is
`previews/controller-01-full/bootstrap/seeds.json` (`6ef83319…`; `head_R_wh`, `head_origin_w_m`), the pose
Breadth-1 rendered the coarse RGB from. The acquisition reads the `EYE` pose in Blender and must equal that record
(|Δ| ≤ 1e-6).

## 4. The binocular instrument (inherited unchanged)

`tools/fsg_geometry.py` (sha256 `ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54`, blob `ad47c1ef`)
and `tools/fsg_stereo.py` (sha256 `faebf0f1b3acbfde60b08830a57213bf29c708c3aa274e493ade0042eb0545e9`, blob
`b9601ecf`) are pinned.

| parameter | value | source |
|---|---|---|
| profile | `full` | |
| `CORE_FOV_DEG` | 12.0° | `fsg_geometry` |
| core size | 256 × 256 (raw padded raster 640 × 640, raw FOV 29.44°) | `fsg_geometry.CORE_SIZE["full"]` |
| IPD | 0.063 m | `fsg_geometry.DEFAULT_IPD` |
| vergence distance | 2.10 m | `fsg6f_public.VERGENCE_DISTANCE_M`, as in the accepted Classroom-Oracle-1 renderer |
| tangent frame | `baseline_projected` | `make_calibration(..., tangent_frame="baseline_projected")` |
| depth search `z_rect` | [0.75, 4.5] m | `fsg_geometry` |
| device / spp | OPTIX / 256 | `fsg6f_public.DEFAULT_SPP["full"]` |
| head | fixed | |

The calibration is exactly `make_calibration("full", 76.75, 7.75, 2.10, ipd=0.063, head_r_wh, head_origin_w,
tangent_frame="baseline_projected")`. The 2.10 m vergence distance and the `z_rect` interval are fixed instrument
parameters inherited from the existing stereo instrument. **They are not measurements of this scene and are not
changed** (in particular not from the known NB1c post-freeze range evaluation). Nothing is tuned for gaze 1.

**Why `baseline_projected`** (not `legacy_upright`): the local tangent +X follows the physical left–right eye
baseline projected into the tangent plane, so the tangent frame is measurement-centric rather than
appearance-centric. The exact look-along-baseline singularity stays rejected by the accepted geometry; gaze #1 is not
singular and is attempted as frozen.

## 5. PRE-LOOK GEOMETRY (recorded before acquisition; a diagnostic only)

For the cyclopean gaze unit direction `d` and the head baseline `b = (1, 0, 0)`:

    stereo leverage   L(d)   = sqrt(1 - (b . d)^2)
    transverse base   B_perp = IPD * L(d)

CALIBRATION-ONLY values at gaze #1 (computed at contract time; `prelook` recomputes them):

| quantity | value |
|---|---|
| `d` | (0.964488, 0.134851, −0.227107) |
| `b · d` | 0.9644883124 (gaze 15.315° from the baseline) |
| `L` | **0.2641255292** |
| `B_perp` | **0.0166399 m** (16.64 mm) |

The pre-look record also states the calibration-only consequences of the accepted rectification at this gaze
(`cv2.stereoRectify`, `CALIB_ZERO_DISPARITY`, `alpha = -1`, central 256 × 256 crop of the rectified raster), all
computed from `make_calibration` + the accepted `fsg_stereo.rectification` with no scene data:

| quantity (left eye; the right eye agrees) | CALIBRATION-ONLY value |
|---|---|
| rectification rotation of the left / right camera | 74.909° / 74.455° |
| rectified principal point `c_x` (both eyes, zero disparity) | −65,992.36 px (raster width 640) |
| rectified baseline / focal length / `P2[0,3]` | 0.063 m / 1217.84 px / −76.724 |
| disparity search | 112 levels (from `z_rect` ≥ 0.75 m: maximum 102.3 px + 4, rounded up to 16) |
| raw-raster source of the rectified 256 × 256 core | L: x ∈ [623.98, 624.07], y ∈ [317.08, 321.92]; R: x ∈ [634.25, 634.35], y ∈ [317.08, 321.92] |
| rectified-core pixels sourced from the nominal raw 12° core | 0 / 65,536 |
| calibration support inside the rectified core (L / R) | 65,536 / 65,536 |
| direction of the rectified core centre | 14.263° from the gaze, 1.052° from the baseline axis |
| range admitted at the core centre by `z_rect` ∈ [0.75, 4.5] m | [40.84, 245.07] m |

In words (calibration-only): at this gaze the accepted planar rectification turns each camera by about 75° to make
the rows parallel to the baseline; the central crop of the rectified raster then samples a sliver about 0.09 × 4.8
raw pixels wide near the raw image's epipole side, about 14° from the fixation and about 1° from the baseline axis,
where the fixed `z_rect` window admits only ranges of tens to hundreds of metres.

These diagnostics **must not** veto the gaze, move it, trigger another RGB candidate, modify vergence or modify any
matcher parameter. They are recorded so that the result can be read against them. The instrument is applied as
accepted.

## 6. One canonical binocular acquisition

A **new** Blender-side tool, `tools/active_bootstrap/ab1a_render.py`, renders exactly one L/R padded tangent pair at
gaze #1. It reuses, read-only, the accepted low-level utilities: `classroom_oracle1_render._head_pose`,
`_assign_instance_ids`, `_prepare_perspective_pair`, `_eye_matrix`, `_extract_exr`;
`render_foveated.render_fixation`; `bl_common`; `exr_lite`. The accepted files stay byte-identical.

- Blender 5.2.1, `blender -b scenes/classroom/classroom_eye.blend --python-exit-code 1 -P ab1a_render.py -- ...`;
  the script exits nonzero on any failure.
- Render settings as the accepted Classroom-Oracle-1 fixation: Cycles, OPTIX (no fallback: any other backend is a
  STOP), 256 spp, no adaptive sampling, no denoising, BOX filter width 1.0, perspective camera with
  `lens = K[0][0] · 36 / 640`, sensor 36 mm, horizontal fit, clip 0.01–1000 m.
- Passes: Combined, Position, Object Index only (the Z and Normal passes that `_prepare_perspective_pair` enables
  are switched off again). Multilayer EXR, uncompressed, one part.
- Render seeds, declared and independent of any object identity: **L 2111, R 2112.** No object id is used for
  anything in acquisition except writing the evaluation-only Object Index pass.

Immediate separation into two truth domains (inside the Blender process, before it exits):

| path | domain | contents |
|---|---|---|
| `RUN/acquisition/calibration.json` | inference-visible | the calibration |
| `RUN/acquisition/rgb-observation.npz` | inference-visible (ORACLE INPUT) | exactly `rgb_L`, `rgb_R` (float32 linear, 640 × 640 × 3) — nothing else scene-derived |
| `RUN/acquisition/acquisition.json` | manifest | gaze, profile, tangent frame, IPD, vergence, spp, device, seeds, render seconds, EYE pose, calibration identity (sha256), RGB observation sha256, EXR channel list |
| `RUN/evaluation_only/raw_L.exr`, `raw_R.exr` | REFERENCE / EVALUATION | the raw multilayer EXRs (they hold truth passes) |
| `RUN/evaluation_only/reference-observation.npz` | REFERENCE / EVALUATION | exactly `instance_L`, `instance_R`, `position_w_L`, `position_w_R` |
| `RUN/evaluation_only/instance-catalog.json` | REFERENCE / EVALUATION | the pass-index → object-name map |

The natural matcher never opens anything below `evaluation_only/`. `acquire` refuses to run if
`RUN/acquisition/` or `RUN/evaluation_only/` exists and is non-empty: **the gaze is rendered once.**

## 7. The natural stereo matcher (`tools/active_bootstrap/ab1a_stereo.py`)

`tools/fsg_stereo.py` is not modified, and its truth-assisted `compute()` is never called. The AB1a matcher reuses its
accepted primitives (`rectification`, `remap`, `support_mask`, `matcher`, `refine_disparity`, `linear_to_u8`) and
its constants, which must equal the AB1a literals (STOP otherwise):

    BLOCK_SIZE 5    LR_TOLERANCE_PX 1.0    UNIQUENESS_RATIO 10    MIN_LOCAL_STD_U8 0.5
    SGBM_3WAY, P1 = 8 B^2, P2 = 32 B^2, disp12MaxDiff -1, preFilterCap 31, speckleWindowSize 0, speckleRange 1
    refinement: 3 Gauss-Newton iterations, each <= 0.5 px, total <= 0.75 px

Input: **exactly** `acquisition/calibration.json` and `acquisition/rgb-observation.npz`, whose arrays must be exactly
`{rgb_L, rgb_R}` (anything else is refused). No instance arrays, no Position, no range.

Mechanics (the accepted ones): rectification (calibration-derived; disparity search from the calibration exactly as
the accepted instrument) → linear-to-u8 gray → SGBM 3WAY left and right → bounded local photometric refinement on
`SGBM-valid ∧ support` → left–right consistency → calibration support → texture gate → fixed `z_rect` interval → 3-D
reprojection (`Q_full`, `rect_to_head`).

Natural support is calibration-derived only: `support[side] = support_mask(calibration, rectification, side)`.

Natural validity (full rectified raster, then the central core crop):

    valid = term_sgbm_left        (SGBM left disparity valid)
          & term_right_valid      (remapped right disparity valid and right-supported; bilinear > 0.999)
          & term_support_left     (calibration support, left)
          & term_inside_raster    (0 <= u_R < w - 1)
          & term_lr               (|d_L + d_R(u_R)| <= 1.0 px)
          & term_texture          (5 x 5 left gray std >= 0.5)
          & term_finite           (finite reprojected XYZ)
          & term_z_range          (0.75 <= z_rect <= 4.5 m)
          & term_roi              (cv2.getValidDisparityROI)

**There is no identity boundary guard.** This is the scientific change being tested.

Outputs (`RUN/measurement/`):
- `stereo-result.npz`: `disparity_px`, `disparity_sgbm_px`, `valid`, `xyz_h` (NaN where invalid), `range_left_m`,
  `z_rect_m`, `lr_error_px`, `left_gray_std`, `rgb_left`, `rgb_right`, `raw_support_L`, the nine `term_*` masks, and
  the rectification matrices (`R1`, `R2`, `P1`, `P2`, `Q_full`, `Q_core`, `crop_xywh`, `roi_L`, `roi_R`,
  `min_disparity`, `num_disparities`). There is **no** instance / object id, truth depth, truth normal or
  Position-derived field.
- `stereo-summary.json` (descriptive, pre-evaluation): `valid_count`, `core_pixels`, `valid_fraction_core`, the
  finite / SGBM-valid disparity counts, the per-term pass counts and the sequential attrition, disparity / range /
  `z_rect` distributions on valid pixels (min, median, p90, p95, max), the LR residual and local-texture
  distributions, the measured XYZ bounding box, the runtime and the exact matcher configuration. Empty sets give
  `null` statistics: **a zero result is recorded honestly and is not a scientific failure.**
- `measurement-opened-files.json`: the `nb1a_guard.OpenGuard` record (accepted, read-only) for the measurement.
  Allowed reads: the two inputs (plus code); writes only under `measurement/`. Expected violations: **0**.

**Optional normals (M):** omitted. AB1a's causal question is metric stereo geometry, not surface orientation.

## 8. Measurement freeze

Before any file below `evaluation_only/` is opened by any host process, `freeze` writes
`measurement/measurement-freeze.json` with the sha256 of: the NB1c action source (`source/nb1c-action-manifest.json`,
`candidate-gazes.json`, `rgb-gaze-freeze.json`); the pre-look record; `calibration.json`; `rgb-observation.npz`;
`acquisition.json`; the matcher configuration (canonical JSON and its sha256); the matcher code (`ab1a_stereo.py`,
`ab1a_spec.py`, `fsg_stereo.py`, `fsg_geometry.py`, `nb1a_guard.py`); `stereo-result.npz`; `stereo-summary.json`;
`measurement-opened-files.json`. The truth firewall must show 0 violations. **After the freeze the stereo result is
immutable:** no threshold, validity rule, disparity range or gaze changes after reference truth has been viewed.

## 9. POST-FREEZE REFERENCE / EVALUATION (descriptive)

`evaluate` runs under the guard. It verifies the measurement freeze first (`measurement_freeze_verified`), then marks
`reference_access_begins`, then opens `evaluation_only/reference-observation.npz` (and the catalog), and writes only
under `evaluation/`. It re-verifies the freeze afterwards. It never modifies the natural output.

**Reference geometry:** the accepted Classroom-Oracle-1 local oracle, `classroom_oracle1_matcher.compute` (read-only,
unchanged), at the SAME calibration and gaze: left Blender Position at the rectified left core pixel (nearest
sample) + right supported same-instance reprojection. It uses Position, Object Index and same-instance right-eye
visibility because this is explicitly REFERENCE / EVALUATION. Note: it counts only catalog geometry (index > 0).

Declared definitions (all on the 256 × 256 rectified left core):
- `N` = natural valid, `R` = reference valid; overlap `N ∧ R`; natural-only `N ∧ ¬R`; reference-only `R ∧ ¬N`.
- On the overlap: 3-D error `||xyz_N − xyz_R||`; radial error `r_N − r_R` (signed) and `|r_N − r_R|`, with
  `r = ||xyz − c_L||` from the left eye centre. Quantiles median, p90, p95, p99, max (`numpy.quantile`, linear);
  descriptive fractions with 3-D error ≤ 0.010, 0.025, 0.050 m (the established FSG metric scales). **No pass /
  fail.** Empty sets give `null`.
- Composition of natural-valid pixels by the left Object Index at that rectified pixel (nearest) and the left
  Position: catalog instance (index > 0, with names), `O_0` (index 0 with geometry: noncatalog rendered geometry) and
  no geometry (Position = (0, 0, 0)). Distinct catalog instances touched.
- Reasons for natural-only pixels: no geometry; `O_0`; right reprojection outside the core; right pixel unsupported;
  different right instance.
- Secondary descriptive comparison (declared now): for every natural-valid pixel with left geometry (any index), the
  3-D and radial error against the left first-hit Position at the same rectified pixel (no binocular-visibility
  rule).
- Error statistics per reference instance with at least 50 overlap pixels.
- Camera-model diagnostic (REFERENCE): every raw pixel with geometry has its Blender Position projected through the
  calibration (`project_h`); the residual to the pixel centre must lie within ±0.5 px (Cycles writes Position from
  the first sample, inside the BOX-filtered pixel footprint). The maximum residual is reported.

Identity information stays evaluation-only.

## 10. Scientific success semantics

There is **no** required scientific target (no minimum valid fraction, point count, maximum error or surface
initialization). Dense accurate geometry, sparse geometry, a central patch with boundary failures, poor depth from weak
leverage, window mismatches, or essentially no usable metric geometry are all valid results. **A poor stereo result
is not a stop condition: it is the result.**

AB1a succeeds **operationally** iff the frozen RGB gaze is executed exactly once; natural inference uses binocular RGB
only; the measurement is frozen before truth; evaluation is descriptive; and the checks pass with every corruption
caught from a passing baseline.

## 11. No controller

After the measurement and its evaluation: STOP. No `fsg3_surface_map`, no surfel fusion, no FSG6f, no other RGB
gaze, no redirect or re-centred look, no gaze 2 / 3, no controller query.

## 12. Visuals (Visual Language 1)

Truth classes: ORACLE INPUT (rendered binocular RGB; the coarse spherical RGB proxy), DERIVED (baseline-projected
geometry diagnostic, rectification, disparity, natural validity, natural range, measured point cloud), REFERENCE /
EVALUATION (Position truth, Object Index, oracle-valid geometry, error maps, identity composition). Nothing is
CONTROLLER-TIME. The action source is labelled **frozen NB1c RGB gaze #1**.

`VIS/`:
- `overview.png` — four regions: **A** frozen action / sensor geometry (coarse spherical RGB with gaze #1,
  yaw / pitch, baseline-projected frame, IPD, L, B_perp, and the calibration-derived direction of the rectified core
  centre); **B** natural sensor data (raw L / R tangent RGB with calibration-only markers, rectified L / R core; no
  truth overlays); **C** derived natural measurement (disparity, valid mask, range, RGB point cloud); **D**
  reference / evaluation (oracle support, error map, compact statistics).
- `binocular-pair.png`, `tangent-geometry.png`, `natural-disparity.png`, `natural-validity.png`,
  `natural-range.png`, `measured-point-cloud.png`, `reference-error.png`; optionally `error-distribution.png`,
  `reference-composition.png`; `visuals-manifest.json`.
- Deterministic: the checker regenerates every PNG byte-identically. Empty results are drawn explicitly ("0 valid
  pixels"), never as blank panels.

## 13. Machine evidence (`RUN/`)

    source/nb1c-action-manifest.json
    prelook/planned-calibration.json, prelook/prelook-geometry.json
    preflight/preflight.json, preflight/blender.log
    acquisition/calibration.json, rgb-observation.npz, acquisition.json, blender.log
    evaluation_only/raw_L.exr, raw_R.exr, reference-observation.npz, instance-catalog.json
    measurement/stereo-result.npz, stereo-summary.json, measurement-opened-files.json, measurement-freeze.json
    evaluation/oracle-reference.npz, evaluation-summary.json, evaluation-opened-files.json
    synthetic/synthetic-report.json, synthetic/blender-rehearsal/...
    manifest.json, check-summary.json, process-log.jsonl

## 14. Commands, order and cost classes

    .venv/bin/python tools/active_bootstrap/ab1a_run.py <command> --run RUN [--visuals VIS]

| # | command | what | cost |
|---|---|---|---|
| 1 | `synthetic` | host-side known answers (section 15); no Blender, no Classroom | interactive |
| 2 | `rehearse` | Blender on a synthetic factory-startup scene only (section 15) | batch (< 1 min) |
| 3 | `prelook` | verify the NB1c action; write the action manifest, the planned calibration and the pre-look geometry | interactive |
| 4 | `preflight` | Blender on Classroom: pose, camera, passes and settings read back; **no render** | interactive–batch |
| 5 | `acquire` | **the one canonical Blender acquisition** (gaze #1, one pair) | batch |
| 6 | `measure` | the natural matcher under the guard | interactive |
| 7 | `freeze` | the measurement freeze | interactive |
| 8 | `evaluate` | post-freeze reference evaluation | interactive |
| 9 | `visualize` | figures and `manifest.json` | interactive |
| 10 | `check_ab1a.py --run RUN --visuals VIS --corruptions --write-summary` | checks + corruption suite | batch |

Order (contract section Z of the handoff): implement → synthetic known answers pass → the tangent-frame regression
(`tools/baseline/check_fsg_tangent_frame.py`) passes → layout → `scripts/verify_baseline.sh` → `git diff --check` →
commit and push the implementation → only then `prelook`, `preflight`, `acquire` (once), `measure`, `freeze`,
`evaluate`, `visualize`, checks with corruptions. `rehearse` and `synthetic` may run during implementation; their
final versions run at the implementation commit. There is no low-spp Classroom preview and no Classroom rehearsal at
any other gaze. **The first Classroom binocular pair is the experiment.**

## 15. Known answers before the canonical look

**Host-side synthetic (`synthetic`; the natural matcher without Classroom truth).** Analytic L / R tangent images of
procedurally textured planes, rendered by ray–plane intersection through the calibration (no Blender). Cases:
1. textured plane perpendicular to the rectified axis at `z_rect` = 2.0 m (forward gaze): recovered disparity /
   geometry correct — valid fraction ≥ 0.90, |median(d − d_true)| ≤ 0.05 px, p95 |d − d_true| ≤ 0.50 px,
   median |z_rect − Z| / Z ≤ 0.005, median distance of `xyz_h` from the plane ≤ 0.005 m;
2. low-texture (uniform) pair: the texture gate rejects it (0 valid; the texture term false everywhere);
3. explicit left / right inconsistency (a region of the right image replaced): LR consistency rejects the affected
   pixels (no valid pixel there has LR error > 1 px; disabling the LR term admits many of them);
4. occlusion (a near plane in front of a far plane): no identity mask exists; the result has no identity field; the
   two depths are recovered; the half-occluded strip's validity is recorded (descriptive);
5. disparity outside the fixed search / depth interval (planes at `z_rect` 0.5 m and 8 m): rejected (0 valid);
6. calibration support border (a synthetic calibration with vergence 0.15 m, whose rectified core is only partly
   supported: 47,360 / 65,536 left): no valid pixel outside the support, valid pixels inside it;
7. baseline-projected gaze #1: the calibration and rectification are accepted and finite, and the pre-look values
   recompute;
8. exact gaze along ±baseline (yaw ±90°, pitch 0): rejected as the known physical tangent-frame degeneracy;
9. synthetic Object Index truth changed while the RGB stays byte-identical: the natural measurement stays
   array-identical (the summary identical except runtime);
10. the same with Position truth;
11. an attempt to open an evaluation-only file during measurement: the truth guard fails (PermissionError, one
    recorded violation);
12. an observation carrying anything besides `rgb_L` / `rgb_R` is refused.

**Blender rehearsal (`rehearse`; a synthetic factory-startup scene, never Classroom).** An `EYE` at the accepted head
pose inside a closed, procedurally textured emission room with a textured plane 2 m ahead. The AB1a render path
acquires a pair at the forward gaze (0°, 0°) and at the gaze-#1 calibration (64 spp; seeds 2111 / 2112), with the
same truth-domain split. Known answers: every geometry pixel's Position projects within ±(0.5 + 1e-3) px of its own
pixel centre (camera model, both gazes, both eyes); the EXR channel set and settings read back as declared; at the
forward gaze the natural matcher's valid fraction is ≥ 0.50 and its median |radial error| against the reference oracle
is ≤ 0.010 m. The gaze-#1 rehearsal result is recorded only. No Classroom RGB is used in implementation or tuning.

The synthetic thresholds are implementation checks on synthetic data, frozen at the implementation commit.

## 16. Checks (`tools/active_bootstrap/check_ab1a.py`)

The checker keeps its own literal constants and recomputes independently (its own `cv2.stereoRectify` call and maps,
its own SGBM factory, refinement, validity and reprojection). Checks:

1. accepted NB1c freeze identity (`87a3bab0…`; its seven files verify);
2. `candidate-gazes.json` full hash (`8041b954…`), equal in the accepted NB1c manifest and the freeze;
3. exactly the rank-1 gaze is consumed (row 164, col 513);
4. yaw / pitch are exactly +76.75 / +7.75 (action manifest, planned and acquired calibration, acquisition);
5. no gaze movement or snapping (equal to the frozen record and to the cell-centre recomputation);
6. exactly one canonical acquisition (process log: one `acquire`, ok, after the implementation commit; two EXRs;
   nothing re-rendered after `freeze` or `evaluate`);
7. no controller command (process log, imports);
8. no second gaze (every logged / recorded gaze is gaze #1);
9. accepted `fsg_geometry.py`, `fsg_stereo.py`, Classroom-Oracle-1 renderer / matcher, `render_foveated.py`,
   `bl_common.py`, `exr_lite.py` unchanged (sha256);
10. `CORE_FOV` = 12°;
11. full core = 256;
12. IPD = 0.063 m;
13. vergence = 2.10 m;
14. tangent frame = `baseline_projected` (recorded);
15. depth-search bounds [0.75, 4.5] m;
16. the baseline-projected local +X of each eye recomputes (`unit(b − (b·z) z)`);
17. `L` and `B_perp` recompute; the pre-look record recomputes from the calibration and precedes `acquire`;
18. `rgb-observation.npz` contains exactly `rgb_L` / `rgb_R` (float32, 640 × 640 × 3, finite);
19. the natural matcher's data reads are exactly `calibration.json` and `rgb-observation.npz`;
20. the natural matcher opened nothing below `evaluation_only/` (0 violations);
21. the natural result holds no instance / Position / truth-geometry field;
22. rectification recomputes independently;
23. SGBM / refinement / gate constants equal the frozen instrument;
24. the natural matcher has no instance-equality guard (static audit of `ab1a_stereo.py`; no truth-assisted
    `compute()` call);
25. support is calibration-only (the saved support term equals the independent calibration support);
26. LR-consistency validity recomputes;
27. texture validity recomputes;
28. fixed depth-search validity recomputes;
29. the saved valid mask equals the AND of the saved terms and the independent full recomputation;
30. saved XYZ / range / `z_rect` recompute from disparity and calibration;
31. the measurement freeze verified before any reference access (the guard's ordered events; no `evaluation_only`
    read before `measurement_freeze_verified`);
32. evaluation did not alter the frozen measurement (the freeze verifies now);
33. the reference geometry recomputes from evaluation-only truth (the reference observation re-extracts from the raw
    EXRs; the accepted oracle recomputes `oracle-reference.npz`);
34. the evaluation statistics recompute;
35. the figures regenerate byte-identically;
36. no surface map / fusion / FSG6f invocation (process log, imports, no such outputs);
37. accepted NB1a / NB1b / NB1c / controller / `fov3d` / FSG files and the NB1c run tree unchanged;
38. changed tracked files are only the declared AB1a / layout / handoff files;
39. synthetic known answers pass (the generator's report and the checker's own independent cases);
40. the acquisition: OPTIX, 256 spp, seeds 2111 / 2112, the declared EXR channels, the `EYE` pose equal to the accepted
    head pose, and the RGB observation equal to the raw EXR Combined pass;
41. the Blender rehearsal passed its known answers (camera model, channels, forward-gaze stereo).

The total need not stay at 41 if a further meaningful check is useful.

## 17. Corruption / mutation suite

Corruptions count only from a passing baseline. Each targets named checks and counts as caught when any target fails.
At least: move gaze #1; substitute gaze #3; `legacy_upright`; alter IPD; alter vergence; alter the depth-search range;
alter the SGBM block size (regenerated); alter the uniqueness ratio (regenerated); disable the LR check
(regenerated); disable the texture check (regenerated); add instance-interior masking; add same-instance equality;
open Object Index during measurement; open Position during measurement; replace disparity geometry with Position
truth; alter the support mask; alter one valid pixel; alter one disparity; alter one XYZ point; modify the frozen
measurement after evaluation; reference access before the measurement freeze; run a controller command; run FSG6f;
execute a second gaze; re-render gaze 1 after evaluation; alter a visual pixel; modify accepted FSG / controller /
NB1a / NB1b / NB1c code. Plus: an extra array in the RGB observation; an identity field in the natural result; the
render seed taken from an object id; an altered evaluation statistic; altered reference geometry; a failed synthetic
case; an altered `L`.

## 18. Stop conditions

STOP and return to Luiz / Chat if:
- the accepted NB1c action identity does not match;
- gaze #1 cannot be represented by `baseline_projected` geometry (`make_calibration` or the accepted rectification
  raises);
- sensor constants differ from the accepted instrument (including the `fsg_geometry` / `fsg_stereo` pins);
- a truth / reference file is opened before the measurement freeze;
- the natural matcher appears to require identity or Position truth;
- a scientific matcher threshold / rule would need changing after canonical RGB is seen;
- the canonical gaze would need to be moved;
- a second acquisition seems necessary (including an OPTIX failure after the render started);
- a controller action appears necessary to complete AB1a;
- measurement files are modified after truth evaluation.

**A poor stereo result is NOT a stop condition. It is the result.** The calibration-only facts of section 5 are
recorded, not acted on.

## 19. Permitted fixes

- Before the implementation commit: any implementation fix, on synthetic data only.
- After acquisition: an implementation defect that prevents execution may be debugged against the SAME saved RGB
  pair, provided no scientific matcher rule changes and no truth has been opened. The gaze is never re-rendered.
- After the freeze: presentation-only figure fixes, and checker defects whose repair does not weaken any check.
- Every repair is minimal, described in the report and committed separately when the distinction matters. A repair
  that would change the instrument, the matcher's validity semantics, the evaluation definitions or the experiment
  design is a STOP.

## 20. The report records

The accepted main SHA after NB1c closure; the AB1a branch and commits; the exact NB1c action source hashes and gaze;
the sensor / calibration constants and tangent frame; `L`, `B_perp` and the pre-look rectification facts; render
time; the natural valid count / fraction; disparity / range statistics; the point-cloud extent; the reference valid /
overlap / natural-only / reference-only counts; the 3-D and radial error statistics; the 1 / 2.5 / 5 cm fractions;
the reference composition; the visuals with paths, hashes and the regeneration command; checks and corruptions;
incidents; and the explicit statement that no second gaze and no controller were executed. Sections: PRE-LOOK
GEOMETRY; RGB-ONLY ACQUISITION / MEASUREMENT; MEASUREMENT FREEZE; POST-FREEZE REFERENCE EVALUATION. Status REVIEW
PENDING; no ACCEPTED marker; no merge.

## 21. Expectations (PROPOSED; not measured)

Given only the calibration-only facts of section 5: the rectified core is expected to show a strongly magnified,
nearly one-dimensional raw sliver near the epipole; the texture gate, uniqueness and the `z_rect` window are expected
to reject most or all of it; any surviving natural-valid pixel would lie 40–245 m away along the core-centre direction
and is unlikely to coincide with reference geometry, whose same-instance reprojection needs the true (large) disparity
inside the right core. The expected scientific outcome is therefore little or no usable metric geometry at gaze #1
with this instrument. This expectation is stated so that it cannot be confused with the measurement; it changes
nothing in the procedure.

## 22. Implementation-time clarification (before any Classroom acquisition; synthetic data only)

**Synthetic case 5 (section 15).** The declared expectation "planes at `z_rect` 0.5 m and 8 m: rejected (0 valid)"
was wrong for the accepted instrument at 0.5 m. MEASURED on the analytic textured plane (forward gaze): the true
disparity, 153.4 px, lies beyond the 112-level search, and **4,151 in-range false matches (6.3 % of the core) survive
every inherited gate** (uniqueness, LR, texture, `z_rect`), with `z_rect` 0.75–4.50 m (median 1.65 m). The 8 m plane
is rejected entirely (0 valid). The instrument and the matcher are not changed. Case 5 now asserts what the
inherited bound guarantees: at 0.5 m the true geometry is never admitted (0 valid pixels within 20 % of 0.5 m; true
disparity > search), the false-match count is recorded, and at 8 m nothing is valid. This bears on reading the
canonical result: wherever the true disparity exceeds the search (section 5 places the rectified core centre there at
gaze #1), any natural-valid pixel is necessarily such an in-range false match.

**Corruption semantics (section 17).** The probes that disable the LR or texture gate regenerate the measurement and
also scrub the variant from the recorded configuration, so only the independent recomputation can expose them; they
are reported as not applicable when that gate already passes on every core pixel (disabling it then changes
nothing). The checker's own synthetic cases (check 39) include a differential test: with an uninformative
(constant, everywhere-interior) identity, the accepted truth-assisted `fsg_stereo.compute` returns exactly the AB1a
natural valid mask, disparity and XYZ, so the natural matcher differs from the accepted instrument only by the
identity guard.

## 23. Post-run clarification: inherited Classroom EXR passes (authorized by Luiz and Chat)

**Chronology.** After the canonical acquisition, measurement, freeze and evaluation, the checker found that the
evaluation-only raw EXRs (`evaluation_only/raw_L.exr`, `raw_R.exr`) do not hold only the passes section 6 named. The
Classroom `.blend` view layer (`interior`) has further lighting / material passes enabled, and the reused accepted
`classroom_oracle1_render._prepare_perspective_pair` leaves them on (the accepted Controller-01 EXRs carry the same
passes, plus Depth and Normal). AB1a switched Depth and Normal off as declared. MEASURED from the canonical EXR
headers (identical for L and R; recorded in `acquisition/acquisition.json` `exr_channels_lr`): 14 passes, i.e. the
3 required ones plus 11 inherited ones:

    Ambient Occlusion, Diffuse Color, Diffuse Direct, Diffuse Indirect, Emission,
    Glossy Color, Glossy Direct, Glossy Indirect,
    Transmission Color, Transmission Direct, Transmission Indirect

These channels stayed exclusively inside `evaluation_only/raw_*.exr`. The natural measurement consumed exactly
`calibration.json` and `rgb-observation.npz` (exactly `rgb_L`, `rgb_R`, equal to the EXR Combined channels) with 0
truth-firewall violations. Luiz and Chat authorized this narrow clarification. It is not a scientific-rule change and
authorizes no re-render, re-measurement, re-freeze or re-evaluation: the canonical acquisition, RGB observation,
natural measurement, measurement freeze and evaluation stay exactly as they are.

**Clarified acquisition contract** (the section 6 wording above is kept as the original record):
- required EXR passes: Combined, Position, Object Index;
- forbidden EXR passes: Depth, Normal;
- additional inherited Classroom lighting / material passes are permitted **only** inside `evaluation_only/raw_*.exr`,
  provided that (1) their exact names are recorded in `acquisition.json` and the report; (2) the L and R pass sets
  agree; (3) none is copied into `rgb-observation.npz`; (4) none is opened by the natural matcher; (5) none influences
  the frozen natural measurement.

**Check 42** (split out of check 40's pass clause, then repaired here, not deleted) requires: the required passes
present with their channels; Depth and Normal absent; the additional pass set equal to the exact inherited set
pinned above; no pass outside required + pinned inherited; L / R consistency; and the recorded channel lists equal to
the EXR headers. Conditions (3)-(5) remain covered by checks 18-20, 29-30 and 40. New probes: add Depth; add Normal;
remove Position; remove Object Index; add an unknown, unrecorded pass; drop a pinned inherited pass; L / R pass sets
differ; alter the recorded inherited-pass set.

Correction: the commit message of `8c9d685` and the question put to Luiz described these as 13 extra passes; the
exact count is 11 (14 in total).
