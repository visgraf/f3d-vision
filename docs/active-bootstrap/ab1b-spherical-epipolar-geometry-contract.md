# Active Bootstrap-1b — Gaze-Centered Spherical Epipolar Geometry — contract

**Status: CONTRACT (committed before implementation and before any execution).**

Branch `active-bootstrap/ab1b-spherical-epipolar-geometry`, created from the accepted `main`
`cbdc4eb4d5cf005805ab26ad5a1863a825ad48a5` (*Pivot active bootstrap to spherical epipolar geometry*; AB1a accepted at
`c27edb2`). Report: `docs/active-bootstrap/ab1b-spherical-epipolar-geometry-report.md` (written after execution;
status REVIEW PENDING; marker `ACTIVE_BOOTSTRAP1B_SPHERICAL_EPIPOLAR_GEOMETRY_COMPLETE` on successful execution; no
ACCEPTED marker, no merge).

Every number in this contract is **PROPOSED** (designed or analytically predicted) or **ASSUMED**, unless it is a pinned
hash or a measured value quoted from an accepted report, which is said where it occurs.

## 1. Question

> **Can direct gaze-centered spherical epipolar ray geometry preserve the intended foveal region and recover correct
> metric 3-D from the exact gaze-#1 binocular observation when correspondence is assumed perfect?**

Equivalently: if correspondence is no longer the problem, does the spherical epipolar representation itself work at the
gaze where conventional planar rectification failed (AB1a, accepted negative experiment)?

AB1b tests **REPRESENTATION** only:
- REPRESENTATION: how binocular rays are parameterized (tested here);
- CORRESPONDENCE: how matching left / right rays are found (held perfect here, by an explicit oracle);
- CONTROL: where the eye looks next (not involved: no gaze is chosen or executed).

AB1b is **not**: a matcher benchmark; an SGBM experiment; a global spherical warp; equirectangular whole-scene stereo;
dense correspondence search over a spherical panorama; a controller experiment. It is: ONE already-selected local
fixation; its original raw 12° foveal support; physical rays expressed in baseline-polar epipolar coordinates; perfect
correspondence supplied externally; direct metric triangulation from angles. The report and the figures say this
explicitly.

Historical rationale (from the accepted post-AB1a pivot, `docs/chat-handoff.md`): an early global spherical warp + SGBM
experiment was unsuccessful; that motivated local foveal tangent-plane stereo; tangent-plane SGBM worked on simple,
richly textured synthetic geometry; Classroom was less satisfactory but matcher and controller failure were confounded;
the controller was validated with a perfect local matcher; AB1a then exposed a representation failure **before**
correspondence. AB1b separates binocular representation geometry from correspondence estimation by returning to
perfect / oracle correspondence on purpose.

## 2. Absolutely no new observation

AB1b re-analyses the exact accepted AB1a observation. There is no Blender process, no render or re-render, no new gaze,
no second fixation and no controller.

Source run (read-only): `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1a-first-natural-stereo-look/`
(`AB1A`). Pinned identities, resolved from the accepted AB1a manifest and run (full sha256; verified by `source` and by
the checker):

| AB1a file | sha256 | role in AB1b |
|---|---|---|
| `manifest.json` | `74eba4d6112f2de69fd797f9f41ff987e128ce1ecbcb5d48f05f597e9a2731fe` | pins every file below |
| `process-log.jsonl` | `4ff1056857455329386fb639e79271d0b2678ef9c3d7c29590e10508b58f7ae7` | proves the one acquisition (unchanged) |
| `acquisition/calibration.json` | `9960c86e0fda1c002ae67e702d34ea3399bff3180d61bf71ac535563f8fc3913` | calibration (oracle and geometry) |
| `acquisition/rgb-observation.npz` | `eb84831aee9676e011651821197812c81e7d51d76ab2cecfea609d3a8dd4268d` | the same RGB pair; visualization only |
| `evaluation_only/reference-observation.npz` | `f23a7a53cdb7816ee4161337551d90825026a4a25fd8a57ba4981abaa99cdb08` | Position / Object Index: ORACLE INPUT, later REFERENCE |
| `source/nb1c-action-manifest.json` | `9fc65ef731601f44c67c141467f613a90c2d742007c79fc8090e9b530f0afe15` | the frozen gaze #1 |
| `measurement/measurement-freeze.json` | `53dc5ff2985cfda4ed0ef0ed13f10be12a33e1c7693942dcf9101a2d1448243e` | AB1a measurement identity |
| `evaluation_only/instance-catalog.json` | `3924b5b4bde3e694d99e3c86b351be0b7f23d447ae6eda917619462b92732c1c` | post-freeze names only |
| `measurement/stereo-summary.json` | `166955c0e01f0f3e86f221e7e842e33f0162432949d3e05e42370e09bd7dbaf0` | post-freeze comparison only |
| `evaluation/evaluation-summary.json` | `5ed406369a4df597d943a01c8be9c393ef44ec60061bbae461b460643bab8e23` | post-freeze comparison only |
| `prelook/prelook-geometry.json` | `e65a85b433eb74e5d0592cc6236ccede43335966916026d6bc882b80eb783b8a` | post-freeze comparison only |

The AB1a visuals manifest (`visuals/active-bootstrap/ab1a-first-natural-stereo-look/visuals-manifest.json`,
`d38bfdc2b9158739cc635f3cbc5ba4a764e6234c5397ba50ca99780987b22da0`) stays unchanged.

Known identities: gaze #1 yaw **+76.75°**, pitch **+7.75°** (NB1c rank 1, row 164, col 513); profile `full`; raw
640 × 640; nominal core 256 × 256 (12°); focal 1217.8386501404907 px; IPD 0.063 m; vergence 2.10 m; tangent frame
`baseline_projected`.

Before the geometry freeze (section 12), AB1b **hashes** only the pre-freeze inputs (manifest, process log, calibration,
RGB observation, reference observation, action manifest, measurement-freeze record) and checks that the AB1a manifest
lists the other pinned hashes. It does **not** open or hash the AB1a natural stereo result or any AB1a summary before the
geometry freeze. The AB1a results become comparison / evaluation only after the AB1b geometry is frozen (section 14).

## 3. Measurement domain

No rectified image. No `cv2.stereoRectify`. No planar rectified core or crop.

The measurement domain is the **original raw left nominal core**: the raw raster is 640 × 640; the nominal core is the
central 256 × 256 crop, raw `x = 192..447`, `y = 192..447`. Its 65,536 left-eye raw pixel centres
(`uv_L = (192 + col, 192 + row)`, integer pixel-centre convention of `fsg_geometry`) are the intended foveal
measurement support around the executed fixation.

Matching may use the **full padded right raw raster** (640 × 640), mirroring the original purpose of the padding (left
foveal support + right search margin). The right point is **not** required to lie inside the right nominal core; it
must only be physically projectable and visible in the padded right raster under the perfect-matcher rule (section 5).

## 4. Hard architectural split

    ORACLE CORRESPONDENCE STAGE   may use Position / Object Index
    SPHERICAL GEOMETRY STAGE      must NOT use Position / Object Index / truth XYZ

The geometry stage receives only the calibration and matched left / right pixel coordinates. This split is
load-bearing and is enforced three ways: an allowlist file-open guard (the accepted `nb1a_guard.OpenGuard`, read-only)
around each stage, a truth-stripped product schema validated on input, and a static audit of the geometry module.

Position has a **dual role**: ORACLE INPUT for correspondence generation, and later REFERENCE / EVALUATION for
reconstruction error. The geometry stage itself never sees it.

## 5. Oracle correspondence stage (`oracle`)

Reads exactly (guarded): `AB1A/acquisition/calibration.json` and `AB1A/evaluation_only/reference-observation.npz`
(arrays `position_w_L`, `position_w_R`, `instance_L`, `instance_R`; Position is head-world metres, `(0, 0, 0)` where
there is no hit, the accepted AB1a convention). Writes only under `oracle/`.

For each LEFT RAW CORE pixel centre (row-major, core row `r`, col `c`, raw `(v, u) = (192 + r, 192 + c)`):
1. take its left Position `P_w = position_w_L[v, u]`;
2. require a **finite geometric hit**: all components finite and not all zero; and a **positive left instance id**
   `instance_L[v, u] > 0`;
3. transform to the accepted head frame: `P_h = world_to_head(calibration, P_w)` (float64);
4. project the same `P_h` through the RIGHT raw perspective camera (`fsg_geometry.project_h`, right eye);
5. require finite positive right-camera depth (`z_R > 1e-9`, the accepted Classroom-Oracle-1 rule) and the projected
   coordinate inside the padded right raster: `0 <= u_R <= 639` and `0 <= v_R <= 639` (closed, continuous; the accepted
   rule);
6. sample the right raw Object Index at the nearest projected pixel (`np.rint`), following the accepted
   Classroom-Oracle-1 perfect-matcher visibility semantics;
7. require the sampled right instance id to equal the left instance id.

The exact **continuous** projected right coordinate is the correspondence `uv_R`; the rounded right pixel is used only
for the same-instance visibility test. No SGBM, no RGB search, no depth threshold, no `[0.75, 4.5] m` interval, no
planar rectification.

**Product** `oracle/oracle-correspondences.npz` contains exactly four arrays, in left-core raster order:

| key | dtype / shape | meaning |
|---|---|---|
| `left_core_row` | int32 (N,) | core row 0..255 |
| `left_core_col` | int32 (N,) | core col 0..255 |
| `uv_L` | float64 (N, 2) | left raw pixel centre `(192 + col, 192 + row)` |
| `uv_R` | float64 (N, 2) | exact continuous right raw projection |

No `xyz`, Position, range, depth, instance id, object name, normal or semantic label appears in it. The geometry stage
rejects any product whose key set differs from these four, or whose keys carry a forbidden token (`xyz`, `position`,
`range`, `depth`, `instance`, `object`, `normal`, `semantic`, `label`, `truth`, `world`).

Also written: `oracle/oracle-summary.json` (descriptive attrition and the right-margin use; no identity list),
`oracle/oracle-opened-files.json` (the guard record). Attrition is recorded **descriptively**, sequentially:

    left core total                     65,536
    finite left geometric hit
    positive left instance id
    right projectable (finite, z_R > 1e-9)
    inside padded right raster
    same-instance binocular-visible
    final perfect correspondences

plus the count of final correspondences whose `uv_R` lies outside the right nominal core (the padded margin in use).
**No target correspondence count is declared.**

`freeze-correspondence` then writes `oracle/correspondence-freeze.json`, hashing the source manifest, the oracle inputs,
the product, the oracle summary, the oracle guard record, the oracle code (`ab1b_oracle.py`, `ab1b_spec.py`,
`fsg_geometry.py`, `nb1a_guard.py`) and the oracle configuration. The product is frozen **before** the geometry stage
runs.

Note (ASSUMED, from the accepted oracle semantics): the positive-instance rule excludes geometry with Object Index 0
(collection-instanced, non-catalog Classroom geometry; Breadth-1 open item 7). The count is recorded in the attrition.
If this rule removes a material part of the finite left geometry, it is reported as an item for judgment; the rule is
**not** changed.

## 6. Spherical epipolar coordinates

Fixed head frame: +X the physical left-to-right eye baseline, +Y up, −Z forward. Baseline axis `b = (1, 0, 0)`.

For a head-frame unit ray `d = (dx, dy, dz)`:

    theta = atan2( sqrt(dy^2 + dz^2), dx )          theta in [0, pi]   (angle from +X, the baseline axis)
    phi   = atan2( dy, -dz )                         phi in (-pi, pi]   (epipolar plane about X)

Canonical wrap: `wrap(a) = atan2(sin a, cos a)`, in `(-pi, pi]`. Pole singularity (purely numerical): a ray with
`sqrt(dy^2 + dz^2) < 1e-12` lies on the baseline axis; its `phi` is undefined (recorded `NaN`, flagged `singular`),
never silently assigned.

For a true correspondence in ideal binocular geometry `phi_L = phi_R`, and for ordinary scene points beyond the eye
baseline `delta_theta = theta_R - theta_L > 0`. The sign is recorded and validated for the canonical scene; it is not an
acceptance target for arbitrary synthetic cases.

## 7. Geometry stage (`geometry`): rays, triangulation, display chart

Reads exactly (guarded): `AB1A/acquisition/calibration.json` and `oracle/oracle-correspondences.npz`. It must not read
`reference-observation.npz`, raw EXRs, Object Index, Position, the AB1a natural stereo result, or NB1a / NB1b / NB1c
scene products. It refuses to start unless `oracle/correspondence-freeze.json` exists (a file-existence test, not a
read); `freeze-geometry` later verifies that the geometry's recorded input hashes equal the correspondence freeze. It
imports neither `cv2` nor `fsg_stereo`, and records whether either module is loaded.

**Rays.** The accepted `fsg_geometry.rays_h` (read-only, sha256 pinned) turns continuous `uv_L`, `uv_R` into head-frame
unit rays `d_L`, `d_R`. Derived: `theta_L`, `theta_R`, `phi_L`, `phi_R`, `delta_theta = theta_R - theta_L`, the wrapped
residual `phi_residual = wrap(phi_R - phi_L)`.

**Primary reconstruction: direct epipolar triangulation.** `B = IPD = 0.063 m`; eye origins `x_L = -B/2`,
`x_R = +B/2` on X (checked against the calibration's eye centres). For each pair:

    den     = cot(theta_L) - cot(theta_R)
    rho     = B / den
    x       = -B/2 + rho * cot(theta_L)
    phi_bar = atan2( sin(phi_L) + sin(phi_R), cos(phi_L) + cos(phi_R) )
    y       =  rho * sin(phi_bar)
    z       = -rho * cos(phi_bar)
    P_epi   = (x, y, z)

Purely numerical guard: a pair is triangulated (`valid_epi`) unless either ray is pole-singular, `|den| < 1e-12`, or
the result is non-finite. No range, disparity, sign or conditioning threshold is applied. No Position truth enters this
computation.

**Independent ray-ray triangulation (descriptive cross-check).** Closest points of `o_L + s_L d_L` and
`o_R + s_R d_R` by the ordinary least-squares construction; `P_ray` is their midpoint; `valid_ray` unless
`1 - (d_L . d_R)^2 < 1e-15` or non-finite. Recorded: the closest-ray gap and `|P_epi - P_ray|`. The checker implements
both triangulations independently of the generator (law-of-sines and linear least squares).

**Gaze-centered display chart (display / diagnostic only; not the AB1c matcher raster).** For the frozen cyclopean gaze
direction `d_g` (from the calibration's `gaze_yaw_pitch_deg`, `fsg_geometry.gaze_direction`), `theta_g`, `phi_g` as
above, and for any ray:

    chart_u = theta - theta_g
    chart_v = sin(theta_g) * wrap(phi - phi_g)          (radians)

The cyclopean gaze is exactly `(0, 0)`. No interpolation, resampling or raster for a natural matcher is defined here.

## 8. The entire raw foveal core (calibration only)

Independently of correspondence truth, the geometry stage writes `geometry/left-core-rays.npz` for **all 65,536** left
raw-core pixel rays: `row`, `col` (core indices), `uv` (raw pixel centres), `direction_h`, `theta`, `phi`, `chart_u`,
`chart_v`, `leverage = sin(theta)`. This shows the distinction from AB1a: the AB1a planar rectified core sampled a
~0.09 × 4.8 raw-pixel sliver; in the spherical-ray representation every one of the 65,536 raw-core sensor directions
remains explicitly represented. No interpolation is needed for this claim.

Recorded (calibration-only): `theta` min / median / max; the minimum angular distance of the nominal core from either
baseline pole (`min(theta, pi - theta)`); `chart_u` and `chart_v` extents; leverage `sin(theta)` min / median / max;
the count of finite and of pole-singular rays.

PROPOSED (analytic, not measured): `theta_g` ≈ 15.3°; with the `baseline_projected` tangent frame the +X pole lies
along the left image's +u axis, so the nominal core's closest approach to the pole is ≈ 15.3° − 6.0° ≈ 9°; no core ray
is singular.

## 9. Conditioning measurements

For every perfect correspondence: `delta_theta` (angular binocular disparity); ray intersection angle
`gamma = acos(clamp(d_L . d_R, -1, 1))`; conditioning proxy `kappa = 1 / |sin(gamma)|` (**no threshold**); and a
descriptive first-order range sensitivity `range_per_px = B * sin(theta_L) / sin(delta_theta)^2 / f` (metres of left
range per pixel-equivalent angle `1/f` of right-ray error along its epipolar curve; from the law of sines
`r_L = B sin(theta_R) / sin(delta_theta)`).

Distributions (min, p05, median, p90, p95, p99, max, count) of: `|phi_residual|`, `delta_theta`, `gamma`, `kappa`, the
closest-ray gap, `|P_epi - P_ray|`, the reconstructed left range `|P_epi - o_L|`, and `range_per_px`; and the sign
counts of `delta_theta`. These say how poorly conditioned gaze #1 is; conditioning never rejects anything.

PROPOSED (analytic): at gaze #1 B⊥ ≈ 16.6 mm, so a point at 3 m has `gamma` ≈ 5.5 mrad, `kappa` ≈ 180 and
`range_per_px` ≈ 0.44 m.

## 10. What the geometry outputs hold

`geometry/epipolar-result.npz` (per correspondence, same order as the product): `left_core_row`, `left_core_col`,
`d_L`, `d_R`, `theta_L`, `theta_R`, `phi_L`, `phi_R`, `delta_theta`, `phi_residual`, `phi_bar`, `singular_L`,
`singular_R`, `rho`, `P_epi`, `valid_epi`, `s_L`, `s_R`, `P_ray`, `ray_gap`, `valid_ray`, `epi_ray_diff`, `gamma`,
`kappa`, `range_L`, `range_per_px`, `chart_u_L`, `chart_v_L`, `chart_u_R`, `chart_v_R`.

`geometry/geometry-summary.json`: counts (correspondences, triangulated, singular), the section 8 and 9 statistics,
`theta_g` / `phi_g`, the configuration and its hash, the input hashes, the loaded-module record.
`geometry/geometry-opened-files.json`: the guard record with `position_reads`, `object_index_reads`,
`ab1a_natural_result_reads` (all must be 0) and the data reads (exactly the two inputs).

## 11. Synthetic known answers (`synthetic`; analytic data only, before any canonical step)

No Classroom RGB, Position or Object Index is used during implementation or tuning. The calibrations are built
analytically with `fsg_geometry.make_calibration`. Cases (declared tolerances are known-answer tolerances on synthetic
data, not scientific thresholds):

1. **Forward point** (0.10, 0.05, −2.0) m: `|phi_L - phi_R| <= 1e-12`; `delta_theta > 0`; `|P_epi - P| <= 1e-9 m`.
2. **Several epipolar planes**: points at `phi` ∈ {−150°, −60°, 0°, 45°, 120°, 179°} and ranges 0.5–6 m: `phi`
   correct to 1e-12 rad and XYZ to 1e-9 m.
3. **Near +X, not singular**: P = (5.0, 0.01, −0.02) m: finite `theta`, `phi`, reconstruction within 1e-6 m.
4. **Exact ±X ray**: `d = (±1, 0, 0)`: flagged pole-singular, `phi` NaN, no finite reconstruction.
5. **phi seam**: rays with `phi_L = pi - 1e-6`, `phi_R = -pi + 1e-6`: wrapped residual `2e-6` (not ≈ 2π); the
   circular mean lies at ±π (not 0).
6. **Swapped eyes**: the left / right rays of a forward point exchanged: `delta_theta < 0` (the invariant exposes it)
   and the reconstruction becomes exactly `-P` (error `2|P|`, to 1e-9 m).
7. **Baseline sign flipped** (`B = -0.063`): the reconstruction becomes exactly `-P` (error `2|P|`; detected).
8. **Baseline magnitude altered** (`B = 0.064`): the reconstruction is the true one scaled by `0.064 / 0.063`
   (to 1e-9 relative) and misses the truth by more than the 1e-9 m known-answer tolerance (detected).
9. **Perturbed `theta_R`** by 1e-7 rad: the left-range change matches `-B sin(theta_L) / sin(delta_theta)^2 × 1e-7` to
   1 % (expected depth sensitivity).
10. **Ray-ray vs epipolar**: 200 seeded points (0.5–8 m, all directions with `theta` in [5°, 175°]): `|P_epi - P_ray|`
    ≤ 1e-9 m, gap ≤ 1e-9 m; with the right rays perturbed off-plane by 1e-4 rad both stay finite, gap > 0.
11. **Gaze-#1 calibration**: all 65,536 nominal left-core rays have finite `theta` / `phi`, none singular; neither `cv2`
    nor `fsg_stereo` is imported by the geometry stage (no planar rectification required).
12. **Truth in the product**: a product carrying `xyz_h`, `position_w` or `instance_id` (each case) is rejected by the
    geometry input schema.
13. **Guard**: the geometry stage attempting to open a reference observation is refused (`PermissionError`) and the
    violation is recorded.
14. **End-to-end at gaze #1 (analytic planes)**: analytic Position / Object Index (float32, Blender-like) of a plane
    normal to the gaze at 4 m (id 1) behind a finite patch at 2 m (id 2), through the file-level, guarded
    oracle → freeze → geometry path: the correspondences are exactly the analytically binocular-visible core pixels
    (left hit whose right projection's nearest right pixel carries the same id, recomputed by direct ray casting);
    some `uv_R` lie outside the right nominal core; median `|P_epi - P_truth|` ≤ 1e-4 m and max ≤ 5e-4 m;
    `delta_theta > 0` everywhere; `|phi_residual|` ≤ 1e-6 rad.
15. **Same-instance rule**: the case 14 data with a right-eye-only region of a different instance (a right-only
    occluder): exactly the correspondences whose nearest right pixel falls in it are rejected; with the rule omitted
    they are accepted (the rule is load-bearing).

All 15 must pass before the canonical analysis (`AB1B_SYNTHETIC_PASS`). The checker re-runs its own independent subset.

## 12. Geometry freeze (`freeze-geometry`)

Before any reconstruction accuracy is evaluated against Position truth, `geometry/geometry-freeze.json` hashes:
the AB1a calibration source; the correspondence freeze; the correspondence product; `left-core-rays.npz`;
`epipolar-result.npz`; `geometry-summary.json`; `geometry-opened-files.json`; the geometry code (`ab1b_geometry.py`,
`ab1b_spec.py`, `fsg_geometry.py`, `nb1a_guard.py`) and the geometry configuration. It requires and records:
Position reads 0; Object Index reads 0; AB1a natural-stereo-result reads 0; guard violations 0; the geometry's recorded
input hashes equal the correspondence freeze. It runs under its own guard (no truth readable).

## 13. Post-freeze evaluation (`evaluate`; REFERENCE / EVALUATION, descriptive)

Only after the geometry freeze verifies may evaluation reopen `reference-observation.npz` (ordered guard events:
`geometry_freeze_verified` → `reference_access_begins` → reads). It uses the original left Position at the exact saved
left-core indices of the oracle matches (`position_w_L[192 + row, 192 + col]`), transformed to the head frame
(`P_truth`), and compares both `P_epi` and `P_ray` against it, over their triangulated pairs:
- Euclidean 3-D error; radial error (`|P - o_L| - |P_truth - o_L|`), signed and absolute; relative radial error;
- median, p90, p95, p99, maximum (plus min, p05);
- fractions with 3-D error ≤ 1, 5, 10, 25 mm.

These are descriptive, not tuning targets. Also: `P_epi` reprojected into both accepted raw cameras
(`fsg_geometry.project_h`), with pixel residual distributions against `uv_L` and `uv_R`; the truth range distribution;
and, descriptively, the left instance composition of the correspondences (catalog names; per-instance error
quantiles for instances with ≥ 50 correspondences). The frozen geometry is re-verified after evaluation; evaluation
writes only under `evaluation/` (`evaluation-summary.json`, `evaluation-result.npz` with `P_truth` and the per-pair
errors, `evaluation-opened-files.json`).

## 14. Post-freeze AB1a comparison (descriptive only)

After the reference evaluation (guard mark `ab1a_comparison_begins`), `evaluate` reads the accepted AB1a summaries
(`measurement/stereo-summary.json`, `evaluation/evaluation-summary.json`, `prelook/prelook-geometry.json`, each hash
verified) and records side by side:
- AB1a planar-rectified natural valid and reference valid (accepted: **0 / 65,536** each, MEASURED in AB1a);
- the AB1a rectified-core raw source and its angle from the gaze and the baseline (AB1a pre-look);
- AB1b raw-core rays represented, AB1b raw-core perfect correspondences, AB1b triangulated correspondences.

This comparison never alters AB1b geometry (the geometry is frozen and re-verified).

## 15. Scientific success semantics (no thresholds)

No correspondence fraction, reconstruction error, disparity magnitude or conditioning threshold is declared. The
meaningful outcomes are:
1. many correct correspondences and accurate triangulation: spherical epipolar geometry is viable at gaze #1;
2. correspondences exist but triangulation is badly conditioned: the representation preserves the fixation, and the
   physical baseline is the limiting factor;
3. few / no binocular-visible correspondences: the raw fixation itself lacks useful binocular support;
4. unexpected epipolar inconsistency (e.g. large `phi` residuals, `delta_theta <= 0`, systematic triangulation error):
   the proposed geometry or a camera convention is wrong.

The report states which outcome the measurements support. PROPOSED expectation: because the oracle `uv_R` is the exact
projection of the left Position, and Blender Position lies within ~0.001 px of the left pixel centre (AB1a, MEASURED),
triangulation should be accurate to roughly sub-millimetre to millimetre level, limited by that offset amplified by
`kappa`; the informative quantities are support preservation, epipolar consistency and conditioning. **Do not repair the
result after seeing Classroom.**

## 16. What AB1b must not do

No `cv2.stereoRectify` for the AB1b geometry; no planar rectified image; no SGBM; no learned stereo; no Blender; no
re-render; no other gaze; no NB1a range; no NB1b classes; no Controller-01 / 02; no FSG6f; no fusion; no surface growth;
no design or tuning of the final natural-matcher raster. Stop after spherical geometry + evaluation.

## 17. Commands and cost classes

    .venv/bin/python tools/active_bootstrap/ab1b_run.py synthetic             --run RUN   # interactive
    .venv/bin/python tools/active_bootstrap/ab1b_run.py source                --run RUN   # interactive
    .venv/bin/python tools/active_bootstrap/ab1b_run.py oracle                --run RUN   # interactive
    .venv/bin/python tools/active_bootstrap/ab1b_run.py freeze-correspondence --run RUN   # interactive
    .venv/bin/python tools/active_bootstrap/ab1b_run.py geometry              --run RUN   # interactive
    .venv/bin/python tools/active_bootstrap/ab1b_run.py freeze-geometry       --run RUN   # interactive
    .venv/bin/python tools/active_bootstrap/ab1b_run.py evaluate              --run RUN   # interactive
    .venv/bin/python tools/active_bootstrap/ab1b_run.py visualize             --run RUN --visuals VIS   # interactive
    .venv/bin/python tools/active_bootstrap/check_ab1b.py --run RUN --visuals VIS --corruptions --write-summary  # batch

`RUN = /home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1b-spherical-epipolar-geometry`,
`VIS = /home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1b-spherical-epipolar-geometry`.

Order: implement → `synthetic` passes → layout → `scripts/verify_baseline.sh` → `git diff --check` → commit and push
the implementation → the canonical reanalysis **once** (`source`, `oracle`, `freeze-correspondence`, `geometry`,
`freeze-geometry`, `evaluate`, `visualize`) → `check_ab1b.py --corruptions`. `source` through `evaluate` run only from a
clean, pushed commit and refuse to rerun once their output exists. Every command appends to `process-log.jsonl`. No
renderer appears anywhere.

## 18. Run layout (machine evidence) and visuals

    RUN/source/ab1a-source-manifest.json
    RUN/oracle/{oracle-correspondences.npz, oracle-summary.json, oracle-opened-files.json, correspondence-freeze.json}
    RUN/geometry/{left-core-rays.npz, epipolar-result.npz, geometry-summary.json, geometry-opened-files.json,
                  geometry-freeze.json, geometry-freeze-opened-files.json}
    RUN/evaluation/{evaluation-summary.json, evaluation-result.npz, evaluation-opened-files.json}
    RUN/synthetic/synthetic-report.json
    RUN/manifest.json, RUN/check-summary.json, RUN/process-log.jsonl

Visuals (persistent, Visual Language 1, deterministic PNGs regenerated byte-identically by the checker), under `VIS`:
`overview.png`, `raw-foveal-core.png`, `spherical-epipolar-core.png`, `perfect-correspondences.png`,
`epipolar-residual.png`, `angular-disparity.png`, `conditioning.png`, `reconstructed-point-cloud.png`,
`triangulation-error.png`, `planar-vs-spherical.png`, `visuals-manifest.json`. No natural-matcher chart is drawn.

Truth classes (Visual Language 1): ORACLE INPUT — the saved raw RGB pair; Position / Object Index used by the oracle.
DERIVED — raw-core ray directions, `theta` / `phi`, the display chart, the truth-stripped correspondence UVs, epipolar
disparity, `P_epi`, ray-ray triangulation, conditioning. REFERENCE / EVALUATION — Position truth when scoring
`P_epi` / `P_ray`; the accepted AB1a planar result. Nothing is CONTROLLER-TIME.

The **primary overview** has four regions and asks: *does spherical epipolar geometry preserve and reconstruct the
foveal region that planar rectification lost?*
- **A — SAME OBSERVATION**: the saved AB1a raw L / R gaze-1 RGB; the nominal raw 12° core; gaze / baseline geometry;
  "no new render".
- **B — SPHERICAL EPIPOLAR REPRESENTATION**: all 65,536 left-core rays in the display chart (RGB for visualization
  only); the baseline-pole direction and distance; the support is finite and two-dimensional.
- **C — PERFECT CORRESPONDENCE / TRIANGULATION**: representative matched ray pairs; `phi` agreement; `delta_theta`;
  the reconstructed RGB-coloured point cloud.
- **D — REFERENCE / COMPARISON**: metric error versus Position; compact conditioning statistics; AB1a planar
  rectified 0 / 65,536 against AB1b raw-core perfect-correspondence / reconstructed counts.

## 19. Checks (`check_ab1b.py`; fail-capable; the checker keeps its own literal constants)

1. accepted AB1a source identities and hashes (pins, AB1a manifest, AB1a measurement freeze, source manifest);
2. exact gaze #1 and the AB1a calibration reused (path, hash, gaze);
3. no Blender command (process log, static audit);
4. no new acquisition (AB1a run tree and process log unchanged; no render products in the AB1b run);
5. no second gaze (declared commands only; no gaze argument; one calibration);
6. no controller / FSG6f / fusion;
7. no SGBM invocation (static audit, process log, `cv2` not loaded in oracle / geometry);
8. no `cv2.stereoRectify` in the AB1b geometry path (static audit, loaded-module records, no rectified arrays);
9. the raw measurement core is exactly the central 256 × 256 of the 640 × 640 LEFT raw raster;
10. all 65,536 raw-core pixel rays independently recompute;
11. right matching uses the padded 640 × 640 raster (the product equals the independent padded-raster set, including
    matches outside the right nominal core);
12. the oracle left finite-geometry rule recomputes;
13. the right projection independently recomputes;
14. same-instance right visibility independently recomputes;
15. the exact continuous `uv_R` is retained (not rounded);
16. the correspondence product contains no XYZ / Position / range / instance (exact key set, schema);
17. the correspondence freeze verifies and precedes the geometry;
18. the geometry opens only the calibration and the frozen correspondence product;
19. the geometry opens no Position / Object Index / AB1a natural result (guard record, freeze record, static audit);
20. the baseline axis is +X (calibration eye centres, configuration, the triangulation origins);
21. the `theta` formula independently recomputes;
22. the `phi` formula independently recomputes;
23. `phi` wrapping independently recomputes (seam vectors through the generator's wrap; saved ranges; circular mean);
24. `theta_g` / `phi_g` recompute;
25. display `chart_u` / `chart_v` recompute;
26. `delta_theta` recomputes;
27. the `phi` residual recomputes;
28. the epipolar triangulation independently recomputes (law of sines);
29. the generic ray-ray triangulation independently recomputes (linear least squares);
30. the closest-ray gap recomputes (line-line distance);
31. the conditioning quantities recompute (`gamma` by atan2, `kappa`, `range_per_px`);
32. the geometry freeze verifies and precedes the evaluation;
33. evaluation reopens truth only after the geometry freeze (ordered guard events);
34. `P_truth` extraction independently recomputes;
35. 3-D / radial error statistics recompute (both reconstructions);
36. camera reprojection residuals recompute;
37. evaluation cannot change the frozen geometry (the freeze verifies now; evaluation writes only under
    `evaluation/`);
38. the post-freeze AB1a comparison is descriptive only and equals the AB1a files;
39. the figures regenerate deterministically (byte-identical) and match the visuals manifest;
40. accepted AB1a / NB1c / controller / FSG code and run products are unchanged;
41. changed tracked files are only the declared AB1b / layout / handoff files;
42. the synthetic known answers pass (generator report and the checker's own subset);
43. the calibration-only raw-core statistics recompute;
44. the oracle attrition is sequential, consistent and equals the checker's own counts;
45. the geometry-summary distributions recompute from the saved arrays;
46. truth-class labels: the run manifest, the product and the figures carry the declared classes.

Marker on success: `ACTIVE_BOOTSTRAP1B_CHECKS_PASS`.

## 20. Corruption / mutation suite (`--corruptions`)

Counted only from a passing clean baseline; each probe plants one defect in a throwaway mirror (or as an in-process
override) and must fail at least one of its target checks. At least: use the rectified core instead of the raw core;
invoke `cv2.stereoRectify`; invoke SGBM; move the gaze; change the calibration; use only the right nominal 256 core
instead of the padded support; omit same-instance visibility; round `uv_R` before the geometry stage; put Position into
the product; put an instance id into the product; let the geometry open `reference-observation.npz`; define `theta`
from −Z instead of +X; flip the sign of `phi`; break `phi` seam wrapping; swap L / R; flip the baseline direction;
alter the baseline length; alter one `uv_L`; alter one `uv_R`; alter one `theta`; alter one `phi`; alter
`delta_theta`; alter one reconstructed XYZ point; replace `P_epi` by Position truth; alter the ray-ray triangulation;
alter the geometry after evaluation; evaluate before the geometry freeze; alter one error statistic; add a Blender
command; add a controller command; execute a second gaze; alter a visual pixel; modify accepted FSG / AB1a / NB1c
sources. Further probes may be added (e.g. the oracle positive-instance rule, conditioning, the gap, the AB1a
comparison, the synthetic report, the attrition, an undeclared file). Marker: `ACTIVE_BOOTSTRAP1B_MUTATIONS_CAUGHT`.

## 21. Stop conditions

STOP and report to Luiz / Chat (no repair) when:
- an AB1a source identity does not verify;
- a synthetic known answer fails and the cause is a definition rather than an implementation defect;
- any guard violation occurs in the oracle, geometry, freeze or evaluation stage;
- a correspondence or geometry freeze does not verify;
- a scientific geometric definition (sections 5–9) would need to change after Classroom has been viewed;
- the canonical result shows outcome 4 (epipolar inconsistency): recorded and reported, not repaired.

## 22. Scope of permitted fixes

Implementation defects that leave every definition, rule, tolerance and evaluation semantic unchanged (crashes, I/O,
bookkeeping, checker false positives with a demonstrated cause), each minimal, described and committed separately.
After the geometry freeze, presentation-only figure fixes are allowed. Nothing in sections 3–15 changes without Luiz and
Chat.

## 23. Report

`docs/active-bootstrap/ab1b-spherical-epipolar-geometry-report.md`, status REVIEW PENDING, distinguishing:
CALIBRATION-ONLY RAW-CORE GEOMETRY; PERFECT / ORACLE CORRESPONDENCE; TRUTH-FREE SPHERICAL EPIPOLAR RECONSTRUCTION;
GEOMETRY FREEZE; POST-FREEZE REFERENCE EVALUATION. It records: the accepted main after the AB1a closure; the AB1b
branch and commits; the exact AB1a source hashes; the same gaze and calibration; the proof of no Blender / no new
observation; raw-core `theta` / `phi` / chart extents; the minimum core distance from the baseline pole; the raw-core
leverage distribution; the perfect-correspondence count / fraction and attrition; the `|phi_L - phi_R|` distribution;
the `delta_theta` distribution; the `gamma` / `kappa` distribution; the triangulation count; the reconstructed range
distribution; the ray-ray gap; the epipolar-vs-ray difference; the post-freeze 3-D / radial errors; the reprojection
errors; the accepted AB1a planar 0 / 65,536 comparison; the visual paths and hashes; checks and corruptions;
incidents. It ends with the measured outcome (section 15) and stops: no natural matcher is started.
