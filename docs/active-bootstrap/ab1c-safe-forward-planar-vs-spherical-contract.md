# Active Bootstrap-1c — Safe-Forward Planar vs Spherical Geometry — contract

**Status: CONTRACT (committed before implementation, before the canonical gaze selection and before any AB1c
observation).**

Branch `active-bootstrap/ab1c-safe-forward-planar-vs-spherical`, created from the accepted `main`
`c2b8373b8ba7849ad4411e28c55c31257d15f2af` (*Record post-AB1b active-sensing operating strategy*; AB1b accepted at
`32fc9a3`). Report: `docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-report.md` (written after execution;
status REVIEW PENDING; marker `ACTIVE_BOOTSTRAP1C_SAFE_FORWARD_PLANAR_SPHERICAL_COMPLETE` on successful execution; no
ACCEPTED marker, no merge).

Every number in this contract is **PROPOSED** (designed or analytically predicted) or **ASSUMED**, unless it is a pinned
hash or a value quoted from an accepted report, which is said where it occurs. Nothing below was computed on Classroom.

## 1. Question

> **Under favorable, well-conditioned head-relative viewing geometry, do conventional planar tangent stereo geometry and
> gaze-centered spherical epipolar geometry recover the same local metric scene structure from the SAME binocular
> observations when correspondence is held perfect?**

AB1c is an **equivalence / control** experiment. It is **not**:
- a competition to decide which representation "wins";
- another near-baseline rescue experiment;
- a natural-matcher experiment (correspondence is held perfect by an explicit oracle);
- a head-motion experiment (the head stays fixed);
- a controller experiment (no gaze is chosen by a controller; nothing is CONTROLLER-TIME).

Logical role:

| step | gaze | representation | result |
|---|---|---|---|
| AB1a (accepted) | difficult (near-baseline gaze #1) | conventional planar rectification | intended foveal support lost |
| AB1b (accepted) | the same difficult gaze | gaze-centered spherical epipolar | support preserved, geometry correct, physical conditioning poor |
| **AB1c** | **favorable (safe-forward) gazes** | **planar and spherical, on the same data** | **direct comparison in the benign regime** |

Future, **not this experiment**: AB1d (safe-forward natural RGB correspondence, only after AB1c is judged); AB1e (the
same difficult world target, whole-head recentering, local stereo, transform back to the canonical frame).

**Operating regime (why).** AB1c does **not** propose to use spherical coordinates to compensate for poor physical
conditioning in the final active system. The intended architecture (Luiz and Chat, after AB1b) is:

    world target selected
      -> assess whether the local head-relative stereo geometry is favorable
      -> if favorable:   local stereo measurement
         if unfavorable: future head motion recentres / reorients the binocular rig so the target becomes
                         locally forward and the baseline strongly transverse; then local stereo measurement
      -> transform the measurement back to the canonical omnidirectional frame

AB1c tests only the favorable local measurement regime. REPRESENTATION must not destroy a valid local measurement;
CONDITIONING is physical and is controlled by sensor / head pose. No controller or head action is implemented here.

## 2. Pinned sources (read-only; verified by `source` and by the checker)

**Accepted RGB attention (the only selection input).** The frozen NB1c score raster, full sha256 read from the
accepted NB1c freeze and manifest:

| item | value |
|---|---|
| file | `/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1c-rgb-candidate-gaze/selection/attention-score.npz` |
| sha256 | `4bfee30e0a1a24007925c57d338627449484dffa2a9805fd13b72727c04ef552` |
| content | exactly one array, `A`: float64, shape (360, 720), the accepted RGB-only center-surround score of every cell |
| pinned by | NB1c `selection/rgb-gaze-freeze.json` `87a3bab01f55051316ac1eb45b48f394211f4c7a3a317fd0e61c0e52c36f9b37` (key `attention-score.npz`) and NB1c `manifest.json` `524f8fad71ccb8fd9359fa3221f4de6be3af40be8f3e5fa7cddeb482acedd87e` (key `selection/attention-score.npz`) |
| grid identity | the NB1c freeze's `grid.directions_sha256` `d72076612515f1079ffce611e81a5b5e1675804c1f8d600cafc31a28829d0b73` (cell-centre directions of `nb1a_spec.cell_directions_h`) |

**Accepted code reused read-only** (sha256 at the base; a mismatch is a STOP):

| file | sha256 | role |
|---|---|---|
| `tools/fsg_geometry.py` | `ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54` | camera model: `make_calibration`, `rays_h`, `project_h`, `world_to_head`, `reproject_q`, `rect_to_head` |
| `tools/fsg_stereo.py` | `faebf0f1b3acbfde60b08830a57213bf29c708c3aa274e493ade0042eb0545e9` | accepted planar rectification `rectification(c)` |
| `tools/natural_bootstrap/nb1a_guard.py` | `29ebca57be9e977def7a94ea45a7b0cff0f22a8b1d86b40f740f132491ebe99d` | allowlist file-open guard |
| `tools/natural_bootstrap/nb1a_spec.py` | `1c1786aaef264012dfb5dcda840cbcc211719340075e4417f1ebef8901134d80` | spherical grid convention |
| `tools/natural_bootstrap/nb1c_spec.py` | `2e05e597889ea9f662b69f3d2f71bccc1f411dafaa5b63ba2ca297a37c731a91` | `D_MIN_RAD`, `ANGLE_EPS_RAD`, `SCORE_TIE_REL` |
| `tools/natural_bootstrap/nb1c_attention.py` | `b7d38c67f65b5d1518c8cef30826c278b12fd2cd1dfa25c558a47e3a968875ea` | `angular_distance`, the reference `select_gazes` |
| `tools/active_bootstrap/ab1a_spec.py` | `24ab5df947b6aaabc46737d3fd015d43802405f94ff1b01595c650bf5ab24a62` | instrument constants, head-pose pin |
| `tools/active_bootstrap/ab1a_render.py` | `ae96164abae9a5241cee3e496293879be43ac96e77697d44d4e2bc956d51e01b` | accepted Blender acquisition helpers |
| `tools/active_bootstrap/ab1a_stereo.py` | `c0238a7318c4a9c034c4a679104ae46cfd7504bf204935e2af15707b10f07f65` | accepted planar support diagnostic `prelook_geometry` |
| `tools/active_bootstrap/ab1b_spec.py` | `1634e455a61879934545a1fa634a72cbb2b8ca74fd83a6ba3a977412be0e497d` | AB1b constants |
| `tools/active_bootstrap/ab1b_oracle.py` | `51e2ee556a4a3576d00cd99255793212ad5efcb50b1e15ed292740d8c24aa231` | accepted oracle `compute_oracle` |
| `tools/active_bootstrap/ab1b_geometry.py` | `a125dd9cc666120219e0421a09a380353d2304ed0f09681a1655962444572538` | accepted spherical geometry |
| `tools/active_bootstrap/ab1b_visuals.py` | `6dd4a203b1847e9d5f0f984c2a1727859aa035ad00adead79849bd484ca833ee` | figure helpers (display only) |
| `tools/classroom_oracle1_render.py` | `ebeac7363a54a022c604161a3716a220fcf2aa7feea3792a68568699ed28a55a` | Classroom-Oracle-1 render helpers |
| `tools/render_foveated.py` | `6f4d6c20b3fa22a74cbf71552374410545b09aeb07ae0b5867cf95b7a264fedf` | `render_fixation` |
| `tools/bl_common.py` | `aa7a56e8cd4988cbe7fc92a57fde68e62740688b6ccfee718e01a8e52ba10370` | Blender helpers |
| `tools/exr_lite.py` | `77286773ee52d17f45373a9c0a0358b197b18672c4cff4654e00bc69e828ef20` | EXR reading |
| `tools/visual_language/style.py` | `c379a2a31c9112d22bbe8989324d2ff74608c669fe84d58905509b4d62264053` | Visual Language 1 |
| `tools/classroom_oracle/breadth1_visuals.py` | `61683aea17993da09bfddce4ed13d48da47d710d1630e40c6bdcc7a6f6d2144c` | figure helpers (display only) |

**Scene and head pose.** `scenes/classroom/classroom_eye.blend` `dca66a3257b909aef00b0331652c55f62a93a8dff0665d070fba7efa436953cc`;
head pose `previews/controller-01-full/bootstrap/seeds.json` `6ef833196de2462370ba4b2a2a8eed3fbde7f0a61e5aa6cbaf95f66947134c4f`
(the accepted AB1a / Breadth-1 head frame; the file also lists Controller-01 instances, so the **selection never opens
it**, see section 4).

**Accepted runs, unchanged and not re-executed**: AB1a run `manifest.json` `74eba4d6…` and visuals manifest `d38bfdc2…`;
AB1b run `geometry/geometry-freeze.json` `942707a8…` and visuals manifest `a1216d2c…`; NB1a / NB1b / NB1c freezes
(`c0236d04…`, `f99b7cae…`, `87a3bab0…`).

## 3. The binocular instrument (unchanged)

Exactly the accepted AB1a / AB1b instrument: `fsg_geometry.make_calibration("full", yaw, pitch, 2.10, ipd=0.063,
head pose, tangent_frame="baseline_projected")`; raw raster 640 × 640; nominal core 256 × 256 (12°), raw
`x, y = 192..447`; focal 1217.8386501404907 px; IPD 0.063 m; vergence 2.10 m; eye centres at (∓0.0315, 0, 0); OPTIX,
256 spp, BOX filter 1.0, no adaptive sampling, no denoising; render seeds L 2111, R 2112 (the accepted declared
constants, no object identity). Fixed head. A gaze change is an eye / camera gaze change only. No parameter is tuned
per gaze.

## 4. SAFE-FORWARD operating envelope (design eligibility; declared before any AB1c stereo result)

Head frame: +X right (the physical left-to-right baseline), +Y up, −Z forward. `b̂ = (1, 0, 0)`, `f̂ = (0, 0, −1)`.

For any unit ray `d`:

    stereo leverage       L(d)      = sqrt(1 − (b̂ · d)^2)
    transverse baseline   B_perp(d) = B · L(d),          B = 0.063 m

**Candidates.** All 259,200 NB1c grid cells. A cell's direction is the accepted cell-centre convention
`yaw = −180° + 0.5°(col + 0.5)`, `pitch = 90° − 0.5°(row + 0.5)`,
`d_g = (sin yaw cos pitch, sin pitch, −cos yaw cos pitch)`.

A cell is **SAFE-FORWARD eligible** iff both conditions hold:

1. **Center forward cone:** `alpha_forward = acos(clamp(d_g · f̂, −1, 1))` and
   `alpha_forward <= 20° + ANGLE_EPS_RAD` (`ANGLE_EPS_RAD = 1e-12`, the accepted NB1c boundary convention: the boundary
   belongs to the eligible set).
2. **Full foveal support leverage:** instantiate the accepted binocular calibration at the cell's (yaw, pitch)
   (`make_calibration` exactly as section 3, calibration only, no scene data; the head-pose arguments do not enter the
   head-frame eye geometry `K`, `R_hc`, `centre_h_m`, so selection uses the `fsg_geometry` defaults and never opens the
   head-pose record). For **each** eye, compute `d = fsg_geometry.rays_h(eye, uv)` for **every** one of the 65,536
   nominal raw-core pixel centres `uv = (192 + col, 192 + row)`. Require

       min over both eyes and the complete core of L(d)  >=  0.90

   (closed). Every foveal ray then retains at least 90 % of the physical baseline transversally: B_perp ≥ 56.7 mm.

The leverage condition is evaluated for every cell that passes condition 1; for other cells it is recorded as not
evaluated (NaN). These are **design eligibility conditions**, not success thresholds. They are not relaxed, tightened
or re-centred after Classroom is seen. If the mask cannot be computed exactly from the accepted camera geometry
(e.g. `make_calibration` refuses a cone cell): **STOP**. No gaze is approximated or chosen by hand.

PROPOSED (analytic, not measured): with `baseline_projected`, the core's extreme rays lie along image ±u, about 6° plus
the 0.86° vergence toe-in from the eye's gaze, so the leverage condition (≥ 0.90 ⇔ within 25.84° of the head YZ plane)
removes only cells whose gaze lies more than about 19° from the YZ plane; the eligible set is the 20° cone (≈ 5,056
cells) minus a thin horizontal sliver.

## 5. Selection: K = 3, RGB-only, deterministic, no cherry-picking

    candidate set  = SAFE-FORWARD eligible cells (section 4)
    ranking        = the frozen accepted NB1c score A (section 2), read as stored, never recomputed
    tie rule       = the accepted NB1c rule: tie set = { i eligible : A_max − A_i <= SCORE_TIE_REL · max(1, |A_max|) },
                     SCORE_TIE_REL = 1e-12; resolved by the smaller row, then the smaller column
    diversity      = the accepted NB1c spherical NMS rule: after choosing g_k, suppress every eligible q with
                     alpha(q, g_k) + ANGLE_EPS_RAD < D_MIN (g_k itself included); a candidate exactly at D_MIN stays
                     eligible; alpha = atan2(||d_q × d_g||, d_q · d_g)  (nb1c_attention.angular_distance)
    D_MIN          = 2 · atan( sqrt(2) · tan 6° ) = 16.90906721486762°   (nb1c_spec.D_MIN_RAD; quoted as 16.9°)
    K              = 3

Greedy NMS runs **only inside** the predeclared eligible set: the initial eligible set is the SAFE-FORWARD mask (in the
accepted NB1c NMS it is the whole sphere). There is no minimum score threshold. If fewer than three gazes can be
selected: **HARD STOP** (no relaxation of the envelope, no smaller D_MIN, no hand-picked replacement).

The selection reads exactly one data file, the pinned score raster, under the guard (section 13). It does not read
depth, range, Position, Object Index, the instance catalog, segmentation, NB1a / NB1b products, any stereo result, the
head-pose record or any Classroom render. It does not inspect any AB1c render (none exists before the freeze).

Recorded for each selected gaze **before any render** (`selection/selected-gazes.json`, `selection/nms-rounds.json`):
rank; NB1c row / col; yaw / pitch; direction; A; alpha_forward; L_center = L(d_g); B_perp_center; minimum raw-core
leverage, left; minimum raw-core leverage, right; combined minimum; the number eligible before that NMS selection; the
tie-set size; the NMS suppression count (eligible cells newly suppressed, g_k included); the number remaining; the
margin to the best eligible score outside the tie set (a robustness diagnostic only). Also recorded: the number of cells
in the cone, the number eligible, the eligibility boundary margins (the smallest |L_min − 0.90| over cone cells and the
smallest |alpha_forward − 20°| over all cells), and the eligibility mask.

**Freeze.** `freeze-selection` writes `selection/safe-forward-freeze.json` (the hashes of every selection product, the
selection configuration and code, the source pins). From then on the three gazes are frozen. **No replacement** is
allowed later because a gaze has poor scene geometry, weak or no correspondence support, bland RGB, or an inconvenient
result. A selected gaze with little or zero binocular scene geometry is itself a measurement.

**Independent pre-render verification.** Before any Blender process, `check_ab1c.py --stage selection` recomputes the
cone, the full-core leverage (its own `K⁻¹`, its own camera rotations), the mask and the NMS independently and must
pass. If the generator's and the checker's masks differ in any cell, the eligibility decision is numerically ambiguous:
**STOP** before rendering.

`plan` then writes `plan/gaze-k/planned-calibration.json` with the accepted head pose (the only step that opens the
head-pose record) and verifies that its head-frame eye geometry equals the selection's calibration exactly.

## 6. Observation: exactly three binocular pairs

After the selection freeze and its verification, `acquire` renders exactly **one** binocular RGB observation at each of
the three frozen gazes, in rank order, in one Blender process on `classroom_eye.blend`:

    three gazes  ->  three binocular observations  ->  one physical observation per gaze

The Blender side (`tools/active_bootstrap/ab1c_render.py`) is a thin driver around the accepted AB1a acquisition helpers,
imported read-only from `ab1a_render.py` (`eye_pose`, `calibration`, `configure`, `acquire_pair`, `calib_diff`) and
`classroom_oracle1_render._assign_instance_ids`. No accepted renderer is modified. Per gaze it verifies the Blender-built
calibration against the planned one (|Δ| ≤ 1e-9) and the EYE pose against the accepted head pose (≤ 1e-6), and writes:

    observations/gaze-k/acquisition/      calibration.json, rgb-observation.npz (exactly rgb_L, rgb_R), acquisition.json
    observations/gaze-k/evaluation_only/  raw_L.exr, raw_R.exr, reference-observation.npz (instance_*, position_w_*)
    observations/evaluation_only/         instance-catalog.json (written once)

Truth separation (as AB1a): RGB and calibration are the sensory observation; Position / Object Index are evaluation-only
and serve as the ORACLE INPUT and later as REFERENCE / EVALUATION. **Declared up front (from AB1a contract section 23):**
the reused accepted configuration leaves the Classroom view layer's 11 inherited lighting / material passes on; the raw
EXRs therefore hold Combined, Position, Object Index plus exactly the pinned inherited set (Ambient Occlusion, Diffuse
Color / Direct / Indirect, Emission, Glossy Color / Direct / Indirect, Transmission Color / Direct / Indirect); Depth and
Normal are off. These passes stay inside `evaluation_only/raw_*.exr`, are recorded in `acquisition.json`, and are never
copied into the RGB observation or read by any AB1c stage.

`preflight` (Blender, **no render**) runs first: Classroom loaded, the EYE pose and the three Blender-built calibrations
verified. `acquire` refuses to run if any observation directory exists, and is **not retried** on failure: a second
acquisition is a decision for Luiz and Chat. Planar and spherical geometry use the **same saved observation** at each
gaze; nothing is rendered per representation. No natural correspondence algorithm, no head motion, no controller.

## 7. One common perfect-correspondence product per gaze

`oracle` produces, for each gaze, ONE truth-stripped product with the accepted AB1b oracle,
`ab1b_oracle.compute_oracle(calibration_k, reference_k)` (read-only, unchanged semantics; AB1b contract section 5): for
each LEFT RAW CORE pixel centre, left Position finite and nonzero; left Object Index positive; the left Position
transformed to the head frame; projected through the RIGHT raw camera; finite positive right depth (z_R > 1e-9);
continuous projection inside the padded right raster (0 ≤ u_R, v_R ≤ 639); rounding only for the right same-instance
visibility test; the same right instance; the exact continuous `uv_R` retained.

The product `oracle/gaze-k/oracle-correspondences.npz` holds exactly `left_core_row`, `left_core_col`, `uv_L`, `uv_R`
(no Position, XYZ, instance id, depth, semantic field or identity). Each oracle run is guarded (data reads exactly
`calibration.json` and `reference-observation.npz` of that gaze). `freeze-correspondence` then writes
`oracle/correspondence-freeze.json`, hashing the three products, summaries and guard records, the oracle inputs, the
oracle code and configuration, **before either reconstruction runs**. Both geometries reject a product whose key set
differs from the four keys or carries a truth token (`ab1b_geometry.validate_product`, reused).

Note (ASSUMED, from Breadth-1): about 15 % of the Classroom sphere is rendered geometry without a catalog id (Object
Index 0; e.g. collection-instanced desks and chairs). The accepted positive-instance rule excludes it. The count is
recorded per gaze in the attrition; if it removes a material part of a gaze's geometry, this is reported for judgment.
The rule is **not** changed.

## 8. Spherical geometry path (accepted AB1b, unchanged in meaning)

`spherical`, per gaze, under its own guard (data reads exactly `calibration.json` of that gaze and its frozen product;
neither `cv2` nor `fsg_stereo` loaded): the accepted `ab1b_geometry.left_core_rays`, `compute_epipolar` and
`summarize`, read-only:

    raw uv_L / uv_R -> fsg_geometry.rays_h -> theta = atan2(sqrt(dy^2 + dz^2), dx), phi = atan2(dy, −dz)
      -> rho = B / (cot theta_L − cot theta_R); x = −B/2 + rho cot theta_L; y = rho sin phi_bar; z = −rho cos phi_bar
      -> P_spherical (= P_epi)

with the independent ray-ray cross-check (P_ray), the phi residual, delta_theta, gamma, kappa = 1/|sin gamma| and
range_per_px = B sin(theta_L) / sin(delta_theta)^2 / f; all 65,536 left raw-core rays; numerical guards only
(`DEN_EPS = 1e-12`, `POLE_EPS = 1e-12`, `PARALLEL_EPS = 1e-15`). No planar rectification enters this path.
Outputs: `spherical/gaze-k/{left-core-rays.npz, epipolar-result.npz, spherical-summary.json, spherical-opened-files.json}`.

## 9. Planar geometry path (accepted AB1a rectification, correspondence held perfect)

`planar`, per gaze, under its own guard (data reads exactly `calibration.json` of that gaze and its frozen product;
no SGBM, no matcher, no image remap of scene data). The conventional tangent / projective stereo geometry is the
accepted AB1a rectification, used read-only and **not tuned per gaze**:

    r = fsg_stereo.rectification(c)        # cv2.stereoRectify(K_L, 0, K_R, 0, (640, 640), R, T,
                                           #   flags = CALIB_ZERO_DISPARITY, alpha = -1, newImageSize = (640, 640))
                                           # accepted eye order (L first), accepted relative pose fsg_geometry.relative_pose

For the SAME shared continuous coordinates of each pair, per side s ∈ {L, R} with `K_s`, `R_s = R1 / R2`,
`P_s = P1 / P2`:

    h_s           = R_s · K_s⁻¹ · (u_s, v_s, 1)ᵀ               (the raw ray in the rectified camera frame)
    (u'_s, v'_s)  = (P_s[:, :3] · h_s)[:2] / h_s[2]            (rectified coordinates)
    disparity     d = u'_L − u'_R
    X_rect        = fsg_geometry.reproject_q(Q_full, (u'_L, v'_L), d)
    P_planar      = fsg_geometry.rect_to_head(c, R1, X_rect)

Planar validity is **numerical only** (`valid_planar`): `h_L[2] > 1e-12` and `h_R[2] > 1e-12` (the ray lies in front of
the rectified image plane, i.e. it is representable in the planar rectified model), finite rectified coordinates,
`|d| >= 1e-12` px, finite `P_planar`. No depth interval (the `[0.75, 4.5] m` z_rect window is a matcher search bound, not
geometry), no disparity-sign, raster-containment or conditioning threshold.

Recorded per pair: `uvrect_L`, `uvrect_R`, `w_L = h_L[2]`, `w_R = h_R[2]`, `disparity`, the rectified row residual
`v'_R − v'_L` (descriptive; the planar analogue of the phi residual), `X_rect`, `z_rect`, `P_planar`, `valid_planar`,
`range_L_planar`, `range_per_disparity_px = range_L_planar / d` (descriptive first-order sensitivity), and, descriptively
only, whether `(u'_L, v'_L)` lies inside the 640 × 640 rectified raster and inside the fixed central 256 × 256 rectified
core (`[191.5, 447.5]²`), and whether `(u'_R, v'_R)` lies inside the rectified raster. Recorded per gaze: R1, R2, P1, P2,
Q_full, the rectification rotation angles, the rectified principal points and focal, `P2[0, 3]`.
Outputs: `planar/gaze-k/{planar-result.npz, planar-support.json, planar-summary.json, planar-opened-files.json}`.

### 9a. Planar support diagnostic (descriptive; calibration only)

Per gaze, the accepted AB1a pre-look diagnostic `ab1a_stereo.prelook_geometry(c)` (read-only): conventional
rectification; the fixed central 256 × 256 rectified core; its source in each raw raster through the accepted
rectification maps. Recorded: the raw source bounds of the rectified central core; the count and fraction of
rectified-core pixels sourced from the intended nominal raw core; the angle of the rectified-core centre from the
intended gaze and from the physical baseline; the rectified principal point; the rectification rotation. AB1c adds:
whether every map coordinate of the core is finite (`support_finite`); the raw source spans in x and y; and
`support_two_dimensional` = both spans ≥ 1 raw pixel (a declared definitional descriptor, not a success threshold; the
accepted AB1a sliver at gaze #1 spans about 0.09 px in x). No support-overlap threshold is introduced.

## 10. Freeze both geometries before reference evaluation

    freeze correspondence  ->  spherical geometry, planar geometry  ->  freeze-geometry
      ->  (truth-free) direct comparison  ->  ONLY THEN Position / Object Index for REFERENCE / EVALUATION

`freeze-geometry` writes `freeze/geometry-freeze.json` hashing, per gaze, the correspondence freeze, the product, every
spherical and planar output and guard record, the calibration, and the geometry code and configurations; it requires
and records: each geometry stage's data reads are exactly that gaze's calibration and frozen product; Position reads 0;
Object Index reads 0; guard violations 0; the spherical stage loaded neither `cv2` nor `fsg_stereo`; both geometries
recorded the same product hash and calibration hash, equal to the correspondence freeze. It runs under its own guard.

`compare` (truth-free; guarded; reads only frozen geometry products) writes the PRIMARY comparison (section 11) to
`comparison/`. `evaluate` verifies the geometry freeze and the comparison hashes, marks `geometry_freeze_verified` then
`reference_access_begins`, and only then opens `reference-observation.npz` and the instance catalog. It writes only under
`evaluation/` and re-verifies the frozen geometry and comparison afterwards: it cannot alter them.

## 11. Measurements

**PRIMARY (truth-free): direct PLANAR vs SPHERICAL agreement on the common valid set.** Per gaze, over the pairs of the
one shared product with `valid_planar & valid_epi` (the same pair index, hence the same left core pixel and the same
`uv_L`, `uv_R`):
- counts: raw-core size (65,536); perfect correspondences; planar valid; spherical valid; common valid; planar-only;
  spherical-only;
- `||P_planar − P_spherical||`: min, p05, median, p90, p95, p99, max;
- signed radial difference `|P_planar − o_L| − |P_spherical − o_L|`: the same quantiles;
- relative difference `||P_planar − P_spherical|| / |P_spherical − o_L|`: the same quantiles.

The comparison refuses to run unless both geometry results carry identical `left_core_row` / `left_core_col` arrays and
the same product hash; it never compares sets of different pairs.

**Per gaze, also:** selected gaze, forward angle, L_center, minimum full-core leverage, B_perp; the spherical phi
residual and delta_theta distributions and sign counts; gamma, kappa, range_per_px; the planar disparity distribution
and sign counts, the rectified row residual, range_per_disparity_px, the rectified containment counts; the planar
support diagnostic (9a).

**SECONDARY (post-freeze REFERENCE / EVALUATION):** with `P_truth` = the left Position at the saved left-core indices in
the head frame, for both `P_planar` and `P_spherical` over their own valid pairs and over the common set: 3-D error and
signed / absolute radial error quantiles (min, p05, median, p90, p95, p99, max) and fractions within 1, 5, 10, 25 mm;
camera reprojection residuals of both into the raw L / R cameras against `uv_L`, `uv_R`; the truth-range
distribution; the left instance composition (catalog names, descriptive).

**Pooled:** the same primary and secondary distributions over the union of the three gazes' common sets, reported
**in addition to**, never instead of, the per-gaze tables.

A gaze with zero correspondences or zero common pairs is recorded as such; its distributions are then undefined
(`null`), and nothing is replaced.

PROPOSED expectations (analytic, not measured): both reconstructions are exact functions of the same exact rays, so
`||P_planar − P_spherical||` should sit at float64 round-off (well below 1 µm at a few metres); forward conditioning is
benign (at 3 m, gamma ≈ 21 mrad, kappa ≈ 50, range_per_px ≈ 0.12 m); and the truth error should be limited by Blender's
≈7.8e-4 px Position offset (AB1b supporting diagnostic) to roughly 0.1 mm at 2–3 m. These are expectations, not
criteria.

## 12. No scientific success threshold

No data-dependent acceptance threshold is declared (no "agree within X mm", no "Y % of the core overlaps"). The
experiment is descriptive and comparative. The report states which outcome the per-gaze measurements support:

1. **BENIGN EQUIVALENCE**: under all / most safe-forward observations, both representations preserve useful support and
   reconstruct the common perfect correspondences consistently, with direct agreement commensurate with the reference /
   numerical precision (the expected favorable-control result);
2. **PLANAR FAILS IN THE DECLARED SAFE REGIME**: spherical geometry is coherent but planar support or metric
   reconstruction still behaves pathologically (report; do not retune);
3. **SPHERICAL DISAGREES WHILE PLANAR IS COHERENT**: the accepted spherical formulation does not generalize cleanly to the
   benign controls (report; do not repair the definition after seeing data);
4. **BOTH FAIL**: the observation / calibration / experimental assumption is wrong, or the selected gaze has no usable
   binocular scene support (report).

## 13. Truth firewall

Allowlist guards (`nb1a_guard.OpenGuard`, read-only) record every open:

| stage | data reads (exactly) | writes |
|---|---|---|
| `select` | the pinned `attention-score.npz` | `selection/` |
| `oracle` (per gaze) | that gaze's `calibration.json`, `reference-observation.npz` | `oracle/gaze-k/` |
| `spherical` (per gaze) | that gaze's `calibration.json`, `oracle-correspondences.npz` | `spherical/gaze-k/` |
| `planar` (per gaze) | that gaze's `calibration.json`, `oracle-correspondences.npz` | `planar/gaze-k/` |
| `freeze-geometry` | the frozen files and calibrations | `freeze/` |
| `compare` | the frozen geometry products, calibrations, freezes | `comparison/` |
| `evaluate` | frozen files, then (after the marks) the three `reference-observation.npz` and the catalog | `evaluation/` |

Static audits: the selection module names no depth / range / Position / Object Index / catalog / segmentation / stereo
source and imports no cv2; the spherical and planar modules name no truth identifier; nothing names SGBM / `matcher` /
`refine_disparity` / `compute_natural` / a controller / FSG6f / fusion / head motion.

## 14. Synthetic known answers (before any canonical step; analytic data only)

Software / numerical tolerances only (not scientific thresholds). No Classroom data.

1. **Exact forward stereo** (gaze (0, 0)): known points spanning the nominal 12° core (centre, edges and corners of the
   core, at 1, 2.5 and 6 m), projected exactly with `project_h`: both `P_planar` and `P_spherical` reconstruct them within
   1e-8 m, and agree with each other within 1e-8 m.
2. **Safe-forward off-axis gazes** (0, 0), (+12, 0) and (−8, +9) degrees: each satisfies the declared envelope (the
   selector's own functions), and case 1 holds at each.
3. **Correspondence identity:** both paths consume exactly the same pairs; their results carry the product's row / col
   arrays; a comparison of results built from two different products is refused.
4. **Wrong eye order** (uv_L and uv_R swapped): both reconstructions miss the known points by more than 1e-3 m.
5. **Wrong baseline sign:** spherical with B = −0.063 gives exactly −P; planar with the sign of `Q[3, 2]` flipped gives
   a non-physical (z_rect < 0) point; both fail the known answer.
6. **Changed IPD** (B = 0.064 used to triangulate 0.063 data): spherical scales exactly by 64/63 about the head origin;
   planar scales exactly by 64/63 about the left eye centre; both miss the known answer; the two then disagree by
   (1/63)·0.0315 m ≈ 0.5 mm in x (the comparison exposes it).
7. **Spherical phi sign error** (`phi = atan2(−dy, −dz)`): points with y ≠ 0 fail the known answer.
8. **Planar rectification convention change:** (a) R1 transposed; (b) the rectified coordinates reprojected with a Q from
   a rectification without `CALIB_ZERO_DISPARITY` mixed with the accepted P1 / P2: each fails the known answer; and the
   checker's rectification-convention check fails on a saved rectification made with different flags or alpha.
9. **Truth-bearing correspondence field** (`xyz_h`, `position_w`, `instance_id`, `depth_m`): rejected by both
   geometries' input validation.
10. **Geometry opening Position before the freeze:** the planar and the spherical stage each attempting to open a
    reference observation are refused (`PermissionError`) with one recorded violation.
11. **Safe-forward selector:** known directions — (0, 0) eligible; (0, +19.75) eligible; (0, +20.25) outside the cone;
    (0, +25) leverage-fine but outside the cone; (+19.75, 0) inside the cone but failing full-core leverage; (+15, 0)
    eligible — each with the condition that decides it, cross-checked by a direct formula.
12. **NMS:** on synthetic score rasters: with every cell eligible, the AB1c NMS equals the accepted
    `nb1c_attention.select_gazes` exactly (picks and round records); an ineligible cell with the highest score is never
    chosen; exact and near ties (within SCORE_TIE_REL) resolve to the smaller row, then column; a candidate at exactly
    D_MIN stays eligible and one at D_MIN − 1e-9 is suppressed; fewer than K candidates raises (HARD FAIL).
13. **Common-valid-set accounting:** invalidating one planar pair (and, separately, one spherical pair) removes exactly
    that pair from the common set; statistics are computed over exactly the common set; result arrays of unequal pair
    identity are refused.
14. **Planar support diagnostic:** at the AB1a gaze-#1 calibration (calibration only) it reproduces the accepted AB1a
    pre-look values (0 rectified-core pixels from the nominal core; 14.26° from the gaze; 1.05° from the baseline;
    `support_two_dimensional` false); at (0, 0) the support is finite and two-dimensional.
15. **End-to-end analytic planes** at a safe-forward gaze (float32 Position, Blender-like): the guarded oracle → freeze →
    spherical + planar → compare path returns exactly the analytically binocular-visible core pixels; both geometries
    are valid on all of them; median / max error ≤ 1e-4 / 5e-4 m against the analytic truth; planar vs spherical agree
    within 1e-8 m.

All must pass before the canonical selection (`AB1C_SYNTHETIC_PASS`). Then a **Blender rehearsal**
(`rehearse`; the accepted synthetic factory-startup room of `ab1a_render.build_rehearsal_scene`, never Classroom;
64 spp) runs the AB1c Blender driver at the three synthetic gazes of case 2 and the whole host pipeline on its output;
known answers: the EXR passes are exactly Combined / Position / Object Index; Position projects within 0.001 px of the
pixel centre; correspondences exist at every gaze; both geometries valid on all of them; planar vs spherical within
1e-6 m; median truth error ≤ 1e-3 m (`AB1C_REHEARSAL_PASS`).

## 15. Visuals (Visual Language 1; designed with the experiment)

Persistent figures under `/home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1c-safe-forward-planar-vs-spherical/`
(regenerated byte-identically by the checker):

| figure | content | truth badges |
|---|---|---|
| `overview.png` | the primary Level-A figure (below) | ORACLE INPUT, DERIVED, REFERENCE / EVALUATION |
| `safe-forward-selection.png` | the coarse spherical RGB and the NB1c attention field near −Z; the 20° cone; the eligible region; the three frozen gazes with D_MIN rings; −Z forward, +X baseline; per gaze alpha_forward and min-core leverage | ORACLE INPUT, DERIVED |
| `binocular-observations.png` | the three raw L / R pairs, nominal core outlined; one observation per gaze | ORACLE INPUT |
| `planar-support.png` | per gaze, the fixed central rectified core mapped back onto the left raw raster against the nominal core; principal point; rectified-core centre angle | DERIVED |
| `spherical-support.png` | per gaze, all 65,536 raw-core rays in the gaze-centered display chart (display only) | DERIVED |
| `common-correspondences.png` | per gaze, the shared perfect-correspondence support on the left core and the right matches; "the SAME oracle matches feed both" | ORACLE INPUT, DERIVED |
| `planar-vs-spherical-difference.png` | per gaze, ‖P_planar − P_spherical‖ over the core and the difference vectors, magnified by a stated factor | DERIVED |
| `paired-reconstruction.png` | per gaze, P_planar and P_spherical overlaid (top and side views) | DERIVED |
| `truth-error.png` | post-freeze error distributions of both against Position | REFERENCE / EVALUATION, DERIVED |
| `conditioning.png` | per gaze gamma / kappa / range_per_px / delta_theta, and planar disparity | DERIVED |
| `visuals-manifest.json` | hashes, sources | — |

**Overview** asks: *in the favorable regime, do planar and spherical geometry measure the same thing from the same
photons?*
- **A — SAFE-FORWARD SELECTION:** attention context, the safe-forward region, the three frozen gazes, −Z and +X, each
  gaze's forward angle and min-core leverage; stated: "selection = RGB attention + calibration-only geometry; no depth,
  identity or stereo result selected the gazes".
- **B — SAME PHYSICAL OBSERVATIONS:** the three binocular observations with the nominal raw core; "both representations
  use these exact photons".
- **C — PLANAR vs SPHERICAL:** per gaze the planar support and the spherical representation, and the common
  correspondence support; "the comparison uses the SAME oracle matches".
- **D — METRIC COMPARISON:** paired reconstructions, the direct difference statistics, the post-freeze truth errors and
  the conditioning (shown, not hidden).

Truth semantics stay explicit with text badges (never colour alone): ORACLE INPUT (the rendered RGB; Position / Object
Index as the oracle uses them), DERIVED (selection geometry, rays, correspondences, both reconstructions, the
comparison, conditioning), REFERENCE / EVALUATION (Position when scoring). Nothing is CONTROLLER-TIME. The selection
panels additionally carry a text label **EXPERIMENT SELECTION** (dashed outline), explained in the caption as "chosen by
the experiment's predeclared rule, not by a controller"; it is a caption label, not a new Visual Language 1 class.

## 16. Checks (`check_ab1c.py`; fail-capable; the checker keeps its own literal constants and recomputes independently)

1. canonical repository and base; source pins (section 2) and accepted NB1c / AB1a / AB1b products unchanged;
2. the selection input is exactly the pinned NB1c `A` (hash, freeze, manifest, grid identity);
3. the safe-forward cone recomputes (own atan2 route) for every cell; 20° cap;
4. the full-core leverage recomputes independently for every cone cell (own `K⁻¹`, own camera rotations); ≥ 0.90;
5. the eligibility mask equals the independent mask exactly (no ambiguous cell);
6. K = 3, D_MIN = 2 atan(√2 tan 6°), the tie rule (SCORE_TIE_REL = 1e-12, row then column);
7. the greedy NMS recomputes exactly inside the eligible set (picks, order, round records, pairwise separations);
8. the selected-gaze records recompute (row / col / yaw / pitch / A / alpha_forward / L_center / B_perp / min-core leverage);
9. the selection guard read only the score raster; no depth / Position / identity / segmentation / stereo source;
10. the selection freeze verifies and precedes the plan, the preflight and the acquisition (timestamps and process-log
    order); no gaze was replaced (the plan, the observations and every later stage use exactly the frozen three);
11. the planned calibrations recompute and their head-frame eye geometry equals the selection's;
12. exactly three observations, one per frozen gaze, from exactly one `acquire` entry; no other render;
13. each observation's calibration equals its planned calibration; device / spp / seeds as declared;
14. the RGB observation holds exactly `rgb_L`, `rgb_R`, equal to the EXR Combined channels; the EXR pass set is exactly
    the required + pinned inherited set (no Depth / Normal); L / R agree;
15. the oracle recomputes independently per gaze (own world-to-head, projection, nearest pixel, same-instance rule);
16. continuous `uv_R` retained; the padded right raster is used (matches outside the right nominal core are counted);
17. the product holds exactly the four keys (truth-stripped schema);
18. the correspondence freeze verifies and precedes both geometries;
19. both geometry stages read exactly their gaze's calibration and frozen product; Position / Object Index reads 0;
    guard violations 0; the spherical stage loaded neither cv2 nor fsg_stereo;
20. planar and spherical consumed the identical product (hash, row / col identity) and the same calibration;
21. the spherical theta / phi convention recomputes (theta from +X, phi = atan2(dy, −dz));
22. the spherical triangulation recomputes independently (law of sines) and the ray-ray cross-check (Cramer);
23. the conditioning quantities recompute (gamma via atan2, kappa, range_per_px);
24. the accepted planar rectification recomputes (the checker's own `cv2.stereoRectify` call with
    `CALIB_ZERO_DISPARITY`, alpha −1, `newImageSize` (640, 640), its own relative pose): R1, R2, P1, P2, Q equal;
25. the raw→rectified mapping recomputes by an independent route (`cv2.undistortPoints`) with its own in-front test;
26. the planar triangulation recomputes by an independent route (linear DLT with P1, P2, mapped back by R1 and the left
    camera); validity recomputes;
27. the planar support diagnostic recomputes (raw source bounds, nominal-core count, angles, principal point, spans);
28. the common valid set recomputes (identity, counts, planar-only / spherical-only);
29. the direct ‖P_planar − P_spherical‖, signed radial and relative statistics recompute (per gaze and pooled);
30. the geometry freeze verifies and precedes the comparison and the evaluation;
31. the evaluation opened Position / Object Index only after the freeze marks (ordered guard events);
32. evaluation cannot alter frozen products (freeze and comparison verify now; evaluation wrote only under `evaluation/`);
33. P_truth extraction and both truth-error statistics recompute (3-D, radial, fractions, per gaze and pooled);
34. both reprojection residuals recompute;
35. per-gaze geometry summaries recompute from the saved arrays (spherical and planar distributions, counts, signs);
36. the figures regenerate byte-identically and match the visuals manifest;
37. truth-class labels: manifest, products, figure badges (ORACLE INPUT / DERIVED / REFERENCE / EVALUATION; no
    CONTROLLER-TIME);
38. no natural matcher (static audit and process log: no SGBM, `matcher`, `refine_disparity`, `compute_natural`);
39. no controller, FSG6f, fusion or head motion (static audit; process log; one fixed head pose in every calibration);
40. no second acquisition for either representation (one acquisition per gaze; planar and spherical inputs are the
    observation's calibration and the one product);
41. accepted historical code and run products unchanged (code pins; NB1a / NB1b / NB1c / AB1a / AB1b freezes and
    visuals manifests);
42. changed tracked files are only the declared AB1c files and the layout declaration;
43. the synthetic known answers pass (generator report and the checker's own subset) and the Blender rehearsal passed;
44. the oracle attrition is sequential and recomputes per gaze;
45. the run order in the process log is the declared order, each canonical step once.

`--stage selection` runs checks 1–9 (and the selection part of 10) before any render. Marker on success of the full
checker: `ACTIVE_BOOTSTRAP1C_CHECKS_PASS`.

## 17. Corruption / mutation suite (`--corruptions`; counted only from a passing baseline)

Each probe plants one defect (in a throwaway mirror, as a deliberately wrong regeneration, or as an in-process
override) and must fail at least one of its target checks. A probe that cannot fail is not counted. At least:
- **selection:** hand-pick one gaze; a candidate outside the forward cone; a gaze violating the min-core leverage; K
  changed; D_MIN changed; the tie rule changed; the frozen RGB attention ordering altered (a score edited);
- **observation:** one selected gaze changed after the freeze; a second pair rendered for one representation; the
  calibration / IPD altered;
- **correspondence:** different products for planar and spherical; `uv_R` rounded; the right match restricted to the
  nominal right core; same-instance visibility removed; Position / instance / depth added to the product;
- **planar:** eye order altered; the rectification convention altered; the fixed central support diagnostic changed;
  truth injected into the triangulation;
- **spherical:** phi sign flipped; theta measured from −Z instead of +X; the baseline direction flipped; truth injected;
- **freeze / evaluation:** a geometry product edited after its freeze; Position opened before the geometry freeze; one
  direct-comparison statistic altered;
- **visual:** a canonical visual pixel altered; a truth badge altered.

Marker: `ACTIVE_BOOTSTRAP1C_MUTATIONS_CAUGHT`.

## 18. Commands, order and cost classes

    RUN=/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1c-safe-forward-planar-vs-spherical
    VIS=/home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1c-safe-forward-planar-vs-spherical
    .venv/bin/python tools/active_bootstrap/ab1c_run.py synthetic             --run $RUN   # interactive
    .venv/bin/python tools/active_bootstrap/ab1c_run.py rehearse              --run $RUN   # interactive (Blender, synthetic room)
    .venv/bin/python tools/active_bootstrap/ab1c_run.py source                --run $RUN   # interactive
    .venv/bin/python tools/active_bootstrap/ab1c_run.py select                --run $RUN   # batch (~20 s: ~5,000 calibrations)
    .venv/bin/python tools/active_bootstrap/ab1c_run.py freeze-selection      --run $RUN   # interactive
    .venv/bin/python tools/active_bootstrap/check_ab1c.py --stage selection --run $RUN --visuals $VIS   # interactive-batch
    .venv/bin/python tools/active_bootstrap/ab1c_run.py plan                  --run $RUN   # interactive
    .venv/bin/python tools/active_bootstrap/ab1c_run.py preflight             --run $RUN   # interactive (Blender, no render)
    .venv/bin/python tools/active_bootstrap/ab1c_run.py acquire               --run $RUN   # interactive / small batch (three pairs)
    .venv/bin/python tools/active_bootstrap/ab1c_run.py oracle                --run $RUN   # interactive
    .venv/bin/python tools/active_bootstrap/ab1c_run.py freeze-correspondence --run $RUN   # interactive
    .venv/bin/python tools/active_bootstrap/ab1c_run.py spherical             --run $RUN   # interactive
    .venv/bin/python tools/active_bootstrap/ab1c_run.py planar                --run $RUN   # interactive
    .venv/bin/python tools/active_bootstrap/ab1c_run.py freeze-geometry       --run $RUN   # interactive
    .venv/bin/python tools/active_bootstrap/ab1c_run.py compare               --run $RUN   # interactive
    .venv/bin/python tools/active_bootstrap/ab1c_run.py evaluate              --run $RUN   # interactive
    .venv/bin/python tools/active_bootstrap/ab1c_run.py visualize             --run $RUN --visuals $VIS   # interactive
    .venv/bin/python tools/active_bootstrap/check_ab1c.py --run $RUN --visuals $VIS --corruptions --write-summary   # batch

Order: implement → `synthetic` passes → `rehearse` passes → layout, `scripts/verify_baseline.sh`, `git diff --check` →
commit and push the implementation → the canonical sequence once, from that clean pushed commit (`source` … `evaluate`
refuse to run from a dirty or unpushed tree and refuse to rerun once their output exists) → `visualize` → the checker
with corruptions. Every command appends to `process-log.jsonl`. Exactly three new foveal observations; no full-scene
render, no reference panorama, no natural matcher, no controller, no head-motion sweep, no parameter sweep. No overnight
task is justified.

## 19. Run layout (machine evidence)

    RUN/source/source-manifest.json
    RUN/selection/{safe-forward-mask.npz, selected-gazes.json, nms-rounds.json, selection-summary.json,
                   selection-opened-files.json, safe-forward-freeze.json, selection-check.json}
    RUN/plan/gaze-k/planned-calibration.json, RUN/plan/plan-record.json
    RUN/preflight/preflight.json
    RUN/observations/gaze-k/{acquisition/, evaluation_only/}, RUN/observations/evaluation_only/instance-catalog.json
    RUN/oracle/gaze-k/{oracle-correspondences.npz, oracle-summary.json, oracle-opened-files.json},
    RUN/oracle/correspondence-freeze.json
    RUN/spherical/gaze-k/{left-core-rays.npz, epipolar-result.npz, spherical-summary.json, spherical-opened-files.json}
    RUN/planar/gaze-k/{planar-result.npz, planar-support.json, planar-summary.json, planar-opened-files.json}
    RUN/freeze/{geometry-freeze.json, geometry-freeze-opened-files.json}
    RUN/comparison/{comparison-summary.json, comparison-opened-files.json, gaze-k/comparison-result.npz}
    RUN/evaluation/{evaluation-summary.json, evaluation-opened-files.json, gaze-k/evaluation-result.npz}
    RUN/synthetic/{synthetic-report.json, blender-rehearsal/…}, RUN/logs/
    RUN/manifest.json, RUN/check-summary.json, RUN/process-log.jsonl

## 20. Stop conditions

STOP and report to Luiz / Chat (no repair) when:
- a pinned source or accepted product does not verify;
- the safe-forward mask cannot be computed exactly, or the generator's and the checker's masks differ (numerically
  ambiguous eligibility);
- fewer than three gazes can be selected (HARD STOP);
- a synthetic known answer fails and the cause is a definition rather than an implementation defect;
- the Blender acquisition fails (no retry), or an EYE pose / planned-calibration identity fails;
- any guard violation in selection, oracle, geometry, freeze, comparison or evaluation;
- a correspondence or geometry freeze does not verify;
- a scientific definition (sections 4–12) would need to change after canonical selection or observation has begun.

## 21. Scope of permitted fixes

- **Before the canonical selection:** ordinary implementation defects found by the synthetic checks or the rehearsal
  may be fixed and documented (this includes software known-answer tolerances that prove mis-set for float64 round-off,
  recorded as such).
- **After canonical selection / observation begins**, none of these changes: the safe-forward definition, K, the NMS,
  the gaze selection, the planar geometric definition, the spherical geometric definition, the oracle semantics, the
  scientific metrics, the success semantics. A code defect may be repaired only if this contract already determines the
  correct behaviour and the repair does not change the scientific question; each such repair is minimal, documented and
  committed separately. Presentation-only figure fixes are allowed after the geometry freeze. Nothing is changed to make
  the result "look better".

Deliberately **not changed** by AB1c: `fov3d/`, the controllers, the sealed `tools/` root (FSG geometry and stereo,
Classroom-Oracle-1, renderers), the NB1a / NB1b / NB1c / AB1a / AB1b tools, documents, runs and figures, Visual
Language 1, the Classroom scene and catalog.

## 22. Report

`docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-report.md`, status **REVIEW PENDING**, marker
`ACTIVE_BOOTSTRAP1C_SAFE_FORWARD_PLANAR_SPHERICAL_COMPLETE` (no ACCEPTED marker). It records: the canonical repository,
branch, base and head; the contract, implementation and report SHAs; the source pins; the frozen safe-forward selection
algorithm; the three selected gazes (row / col, yaw / pitch, A, alpha_forward, L_center, min-core leverage L / R,
B_perp); one row per gaze (perfect correspondences, planar valid, spherical valid, common valid, P_planar vs P_spherical
quantiles, planar and spherical truth error, conditioning, planar support diagnostic); the pooled summary; the outcome
(section 12) the measurements support; the statements that no natural matcher, no head motion and no controller ran and
that no gaze was replaced after selection; the visual paths, hashes and regeneration command; the checker and
corruption results; every implementation incident and deviation; what is and is not established; the unresolved
decisions for Luiz and Chat. It does not propose AB1d's implementation, and it stops.

## 23. Pre-canonical clarification (implementation, before any canonical step; within section 21)

Added during implementation, **before** the canonical selection, any Classroom observation or any canonical product.
Sections 1–22 above are preserved as committed at `d8a56aa`. Nothing here changes a scientific definition, rule,
envelope, metric or the success semantics; it corrects two **software known-answer tolerances** and one **PROPOSED
expectation**, and adds two pins.

**Finding (synthetic and rehearsal data only).** The two triangulations are exact functions of exactly consistent rays:
with exactly projected correspondences they agree to ≈ 4e-12 m (case 1). The oracle, however, pairs the left **pixel
centre** with the projection of the left **Position** sample, and a Position sample does not lie exactly on the left
pixel-centre ray (float32 storage; Blender's ≈ 7.8e-4 px offset, AB1b supporting diagnostic). The pair is then very
slightly skew (a phi residual / rectified-row residual). The spherical route places the point on the mean epipolar
plane `phi_bar`; the planar route on the left ray's rectified row. They therefore differ by an amount set by the oracle's
own epipolar inconsistency, not by round-off. Measured on non-Classroom data:
- synthetic case 15 (float32 analytic Position): |P_planar − P_spherical| max 2.9e-7 m; the exact-float64 control on the
  same pairs 1.4e-12 m;
- Blender rehearsal (synthetic room, 64 spp; Position ≈ 8e-4 px off the pixel centre): max 0.73–1.47 µm over 65,536
  pairs per gaze; a **consistency-restored control** (the point on the left ray at the spherical range, projected into the
  right camera, re-triangulated by both) ≤ 6.7e-13 m. Truth error median ≈ 0.03 mm for both.

**Changes (software tolerances, synthetic / rehearsal only).**
- Case 15: planar vs spherical within **1e-6 m** for the float32-Position pairs (`SYN_FLOAT32_AGREE_M`), plus an
  exact-data control (left pixel-centre rays cast against the analytic planes in float64) within 1e-8 m.
- Rehearsal: planar vs spherical within **1e-5 m** for the Blender pairs (`REHEARSAL_AGREE_M`, was 1e-6 m), plus the
  consistency-restored control within 1e-8 m. 1e-5 m stays below the rehearsal's own truth error (≈ 3e-5 m median).
- The EXR pass names are parsed with the accepted AB1a rule (`viewlayer.pass.channel`).

**Revised PROPOSED expectation (section 11).** In Classroom, `||P_planar − P_spherical||` is expected at the
**micrometre** level, tracking the oracle's sub-millipixel epipolar inconsistency (it scales with that inconsistency
and the conditioning), well below the truth error, rather than at float64 round-off. This is an expectation, not a
criterion; no threshold is declared. The report will show the consistency-restored decomposition descriptively.

**Pins added** (accepted code reused read-only by the known answers): `tools/active_bootstrap/ab1b_run.py`
`6088ab06ba52aa285bec9835e39e29c706db137a13d7527c9c76d90e46ac810a` (the AB1b analytic test scene `analytic_scene`,
`cast`, `expected_set`).

**Descriptive addition to the comparison (section 11).** Per gaze, the `compare` stage also records the
consistency-restored control (truth-free: the point on the left ray at the spherical range, projected into the right
camera, re-triangulated by both geometries) and the |phi residual| / |row residual| distributions next to the direct
difference, so that the size of the oracle skew and its share of the disagreement are visible. The PRIMARY quantity is
unchanged: the direct difference on the common valid set of the one shared product.
