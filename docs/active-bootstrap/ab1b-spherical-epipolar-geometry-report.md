# Active Bootstrap-1b — Gaze-Centered Spherical Epipolar Geometry — report

**Markers.**

    ACTIVE_BOOTSTRAP1B_SPHERICAL_EPIPOLAR_GEOMETRY_COMPLETE
    ACTIVE_BOOTSTRAP1B_SPHERICAL_EPIPOLAR_GEOMETRY_ACCEPTED

**Status: ACCEPTED.** Luiz and Chat accepted AB1b after scientific, quantitative, code and qualitative visual review
(see "Acceptance record" at the end). At the deliberately difficult gaze #1, gaze-centered spherical epipolar geometry
preserves the intended foveal support and yields correct metric geometry when correspondence is supplied perfectly; the
metric precision there remains strongly limited by physical stereo conditioning. The sections below are the report as
completed at `a597c89`, unchanged.

> **Question.** Can direct gaze-centered spherical epipolar ray geometry preserve the intended foveal region and
> recover correct metric 3-D from the exact gaze-#1 binocular observation when correspondence is assumed perfect?

**Answer at gaze #1, with correspondence held perfect (MEASURED): yes.**
- All **65,536** raw-core sensor rays are represented, finite and non-singular. The core's closest approach to the
  baseline pole is **9.115°**.
- **44,769** raw-core pixels (0.6831 of the core) have a perfect binocular correspondence. All 44,769 are triangulated
  from angles alone.
- Epipolar consistency: |φ_R − φ_L| median 1.93e-6 rad, max 3.88e-6 rad. δθ > 0 for every pair.
- 3-D error against Position (post-freeze): median **0.41 mm**, p95 0.70 mm, p99 0.79 mm, max **0.93 mm**; 100 % of
  pairs within 1 mm.
- The error is a small systematic positive radial bias. A post-run scratch diagnostic attributes it entirely to Blender's
  sub-millipixel Position offset, amplified by the conditioning (see "Post-run scratch diagnostic").
- Conditioning is poor, as expected near the baseline: κ = 1/|sin γ| median 262 (192–430). A pixel-equivalent angular
  error of the right ray moves the range by a median **0.94 m** at ≈4.4 m.

AB1a's planar rectified core had 0 / 65,536 reference-valid pixels at the same gaze (accepted, MEASURED in AB1a).

This is **not** a matcher, an SGBM run or a global spherical warp. It is one already-selected fixation; its raw 12°
support; physical rays in baseline-polar coordinates; perfect correspondence supplied by an explicit oracle; direct
metric triangulation from angles. It tests REPRESENTATION only.

Contract: `docs/active-bootstrap/ab1b-spherical-epipolar-geometry-contract.md`. MEASURED means produced by the runs
below. CALIBRATION-ONLY means computed from the calibration with no scene data.

## Branch and commits

| item | value |
|---|---|
| accepted `main` after the AB1a closure | `cbdc4eb4d5cf005805ab26ad5a1863a825ad48a5` *Pivot active bootstrap to spherical epipolar geometry*; parent `c27edb2` *Accept AB1a first natural stereo look*; `origin/main` fast-forwarded `509c341 → cbdc4eb` (plain push, no merge commit) |
| branch | `active-bootstrap/ab1b-spherical-epipolar-geometry`, from `cbdc4eb`; isolated worktree |
| contract | `922dc8e` *Contract AB1b spherical epipolar geometry* (committed before any implementation) |
| implementation (frozen before the canonical analysis) | `53393e3` *Implement AB1b spherical epipolar geometry* |
| canonical run | `synthetic`, `source`, `oracle`, `freeze-correspondence`, `geometry`, `freeze-geometry`, `evaluate`, `visualize`: all at `53393e3`, clean and pushed |
| presentation fix (one caption, after the geometry freeze) | `d0f1a23` *Fix AB1b point-cloud caption (presentation only)*; `visualize` re-run there |
| checks and corruptions | `check_ab1b.py --corruptions --write-summary` at `d0f1a23` |
| report | this commit |

## What ran

Run: `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1b-spherical-epipolar-geometry/` (`RUN`).
Visuals: `/home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1b-spherical-epipolar-geometry/` (`VIS`).
Source (read-only): `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1a-first-natural-stereo-look/` (`AB1A`).

| # | command (`tools/active_bootstrap/ab1b_run.py`) | commit | status | seconds (MEASURED, process log) |
|---|---|---|---|---|
| 1 | `synthetic` | `53393e3` | ok: `AB1B_SYNTHETIC_PASS` 15/15 | 1.42 |
| 2 | `source` | `53393e3` | ok | 0.03 |
| 3 | `oracle` | `53393e3` | ok | 0.09 |
| 4 | `freeze-correspondence` | `53393e3` | ok | 0.04 |
| 5 | `geometry` | `53393e3` | ok | 0.45 |
| 6 | `freeze-geometry` | `53393e3` | ok | 0.04 |
| 7 | `evaluate` | `53393e3` | ok | 0.25 |
| 8 | `visualize` | `53393e3`, then `d0f1a23` | ok, ok | 1.16, 1.18 |
| 9 | `check_ab1b.py --run RUN --visuals VIS --corruptions --write-summary` | `d0f1a23` | 46/46; corruptions 51/51 (+1 N/A) | 94 (batch) |

Every command is interactive except the checker with corruptions (batch). `process-log.jsonl` holds exactly the nine
`ab1b_run.py` entries above. Each canonical step ran once; `source` through `evaluate` refuse to rerun.

## No new observation (MEASURED)

- No Blender process, no render, no gaze, no controller. The process log has no Blender, controller, FSG6f or SGBM
  argument (checks 3, 5, 6, 7). The AB1b run tree holds no EXR, RGB observation or `acquisition/` directory (check 4).
- The AB1a run is unchanged:
  - `manifest.json` `74eba4d6112f2de69fd797f9f41ff987e128ce1ecbcb5d48f05f597e9a2731fe`;
  - `process-log.jsonl` `4ff1056857455329386fb639e79271d0b2678ef9c3d7c29590e10508b58f7ae7`, with exactly one `acquire`;
  - all 43 AB1a manifest files verify, as does the AB1a measurement freeze (checks 1, 4).
- Exact same gaze and calibration: frozen NB1c RGB gaze #1, yaw **+76.75°**, pitch **+7.75°** (rank 1, row 164,
  col 513). The oracle, the geometry and the geometry freeze all read the AB1a calibration in place (check 2).

AB1a source identities, pinned in `source/ab1a-source-manifest.json` (full sha256):

| AB1a file | sha256 | read |
|---|---|---|
| `acquisition/calibration.json` | `9960c86e0fda1c002ae67e702d34ea3399bff3180d61bf71ac535563f8fc3913` | oracle, geometry |
| `acquisition/rgb-observation.npz` | `eb84831aee9676e011651821197812c81e7d51d76ab2cecfea609d3a8dd4268d` | figures only (RGB for display) |
| `evaluation_only/reference-observation.npz` | `f23a7a53cdb7816ee4161337551d90825026a4a25fd8a57ba4981abaa99cdb08` | oracle (ORACLE INPUT); evaluation (REFERENCE) |
| `source/nb1c-action-manifest.json` | `9fc65ef731601f44c67c141467f613a90c2d742007c79fc8090e9b530f0afe15` | source |
| `measurement/measurement-freeze.json` | `53dc5ff2985cfda4ed0ef0ed13f10be12a33e1c7693942dcf9101a2d1448243e` | identity only |
| `evaluation_only/instance-catalog.json` | `3924b5b4bde3e694d99e3c86b351be0b7f23d447ae6eda917619462b92732c1c` | post-freeze names |
| `measurement/stereo-summary.json` | `166955c0e01f0f3e86f221e7e842e33f0162432949d3e05e42370e09bd7dbaf0` | post-freeze comparison |
| `evaluation/evaluation-summary.json` | `5ed406369a4df597d943a01c8be9c393ef44ec60061bbae461b460643bab8e23` | post-freeze comparison |
| `prelook/prelook-geometry.json` | `e65a85b433eb74e5d0592cc6236ccede43335966916026d6bc882b80eb783b8a` | post-freeze comparison |

Before the geometry freeze, AB1b hashed only the pre-freeze inputs. It checked the other pins against the AB1a manifest
without opening the AB1a natural result or summaries.

## CALIBRATION-ONLY RAW-CORE GEOMETRY (MEASURED)

`geometry/left-core-rays.npz` holds all 65,536 rays of the raw left core (raw x, y = 192..447 of 640 × 640), from the
calibration alone:

| quantity | value |
|---|---|
| rays / finite / pole-singular | **65,536 / 65,536 / 0** |
| cyclopean gaze θ_g, φ_g | **15.315°**, 30.701° |
| θ min / median / max | 9.115° / 15.481° / 21.854° |
| minimum angular distance of the core from either baseline pole | **9.115°** (the +X pole; along the image +u axis, as the `baseline_projected` frame predicts) |
| φ range | −2.62° … 64.02° |
| display chart u extent | −0.1082 … +0.1141 rad (−6.20° … +6.54°) |
| display chart v extent | −0.1536 … +0.1536 rad (±8.80°) |
| leverage sin θ min / median / max | 0.158 / 0.267 / 0.372 |

So the foveal support stays finite and two-dimensional. Every raw-core sensor direction is represented explicitly, with
no interpolation or resampling. The contract's analytic expectation (≈9° from the pole, nothing singular; PROPOSED) is
confirmed.

## PERFECT / ORACLE CORRESPONDENCE (MEASURED)

The guarded `oracle` stage read exactly the calibration and `reference-observation.npz` (0 violations; `cv2`,
`fsg_stereo` and `ab1a_stereo` not loaded). Position and Object Index were used here, in their ORACLE INPUT role, and only
here. The accepted Classroom-Oracle-1 visibility semantics were applied on the raw rasters:

| sequential attrition (descriptive; no target count) | remaining |
|---|---|
| left core total | 65,536 |
| finite left geometric hit | 46,832 |
| positive left instance id | 46,832 |
| right projectable (finite, z_R > 1e-9) | 46,832 |
| inside padded right raster (0 … 639) | 46,832 |
| same-instance binocular-visible | 44,769 |
| **final perfect correspondences** | **44,769 (0.6831 of the core)** |

- Excluded:
  - no finite hit 18,704 (the views out through the window panes);
  - instance id 0 with a hit: **0**;
  - not projectable 0;
  - outside the padded raster 0;
  - different right instance (half-occlusion at the blinds and frames) 2,063.
- The padded margin is in use: **1,790** matches lie outside the right nominal 256 core. `u_R` spans 195.52 … 453.90 and
  `v_R` 190.04 … 448.86 (continuous).
- The positive-instance rule removed nothing here: no hit in the raw core carries Object Index 0. The contract's
  instance-0 caveat therefore does not arise at gaze #1.

Product `oracle/oracle-correspondences.npz` `4d26ff328cafb9ff1b9f54e3a1a7309528de87de1e26f41884516d52465e8fc0`:
- it holds exactly `left_core_row`, `left_core_col`, `uv_L` (raw pixel centres) and `uv_R` (exact continuous
  projections; float64, not rounded);
- no XYZ, Position, range, depth, instance, object, normal or label (check 16).

The product was frozen at 23:04:17Z by `oracle/correspondence-freeze.json`
`d160d98faecdd8ba1c44ff532fc91cd94ab89789e9d6a31743a5c25d8ce8ba56`, before the geometry ran at 23:04:18Z (check 17).

## TRUTH-FREE SPHERICAL EPIPOLAR RECONSTRUCTION (MEASURED)

The guarded `geometry` stage:
- data reads were exactly `AB1A/acquisition/calibration.json` and `RUN/oracle/oracle-correspondences.npz`;
- Position reads 0, Object Index reads 0, AB1a natural-result reads 0, guard violations 0;
- `cv2` and `fsg_stereo` were not loaded (checks 8, 18, 19).

Rays come from the accepted `fsg_geometry.rays_h`. Formulas: θ = atan2(√(d_y² + d_z²), d_x); φ = atan2(d_y, −d_z);
ρ = B / (cot θ_L − cot θ_R); x = −B/2 + ρ cot θ_L; y = ρ sin φ̄; z = −ρ cos φ̄; B = 0.063 m.

| quantity (44,769 pairs) | min | p05 | median | p95 | p99 | max |
|---|---|---|---|---|---|---|
| \|φ_R − φ_L\| [rad] | 1.05e-6 | 1.34e-6 | **1.93e-6** | **3.22e-6** | 3.53e-6 | **3.88e-6** |
| δθ = θ_R − θ_L [mrad] | 2.323 | **2.603** | **3.824** | **4.908** | 5.038 | 5.213 |
| ray angle γ [mrad] | 2.323 | 2.603 | 3.824 | 4.908 | 5.038 | 5.213 |
| κ = 1/\|sin γ\| | 191.8 | 203.7 | **261.5** | **384.2** | 411.8 | 430.4 |
| reconstructed left range [m] | 4.271 | 4.300 | 4.433 | 4.565 | 4.590 | 4.636 |
| range per pixel-equivalent angle [m] | 0.708 | 0.754 | **0.939** | 1.344 | 1.441 | 1.519 |
| closest-ray gap [µm] | 1.28 | 1.73 | 2.37 | 2.73 | 2.81 | 3.03 |
| \|P_epi − P_ray\| [m] | 2.5e-8 | 4.0e-8 | **8.1e-8** | 2.1e-7 | 2.4e-7 | **2.9e-7** |

- Triangulated: epipolar **44,769 / 44,769**, ray-ray 44,769 / 44,769. No singular ray.
- δθ > 0 for **44,769**; δθ = 0 for 0; δθ < 0 for 0. The sign is as predicted for scene points beyond the baseline.
- The φ residual is equivalent to about 6e-4 px at the core. There is no epipolar inconsistency (outcome 4 does not
  occur).
- δθ equals γ to the reported digits, as it should when both rays share an epipolar plane.
- The primary epipolar reconstruction and the independent ray-ray reconstruction agree to 0.29 µm.

Files: `geometry/epipolar-result.npz` `886704905a7fed29eb92a2b5da3e13b30bc5d741f77103f93f1fcf63e46008d5`,
`geometry/left-core-rays.npz` `74db5bf8cb98a0677e836086f7de6648885b9e40ca5c8c8307758f646fc00319`,
`geometry/geometry-summary.json` `7e7650d4041fc46bdb91550e18b0893d5050801b9a8c8f29bd6d75c9da42bbe2`,
`geometry/geometry-opened-files.json` `56f820b4fbde8c137f9c13535b8c02710240f36d1bfb21de0b8af907502985fa`.

## GEOMETRY FREEZE (MEASURED)

`geometry/geometry-freeze.json` `942707a858c8b76cb65db503183853d27c55000eb2e59c6de4dfbcf025d21c7a` (23:04:27Z, at
`53393e3`) hashes:
- the AB1a calibration source, the correspondence freeze and the product;
- the ray table, the result, the summary and the geometry guard record;
- the geometry code (`ab1b_geometry.py`, `ab1b_spec.py`, `fsg_geometry.py`, `nb1a_guard.py`) and the configuration.

Every precondition held:
- the input hashes equal the correspondence freeze;
- the data reads are exactly two;
- Position reads 0, Object Index reads 0, AB1a natural-result reads 0;
- no `cv2` / `fsg_stereo`.

The freeze ran under its own guard (`geometry-freeze-opened-files.json`; it wrote only the freeze). It verifies after
evaluation and now (checks 32, 37).

## POST-FREEZE REFERENCE EVALUATION (MEASURED; descriptive)

`evaluate` ran under the guard. Its ordered events are:

    (frozen-geometry reads) -> geometry_freeze_verified -> reference_access_begins -> reference-observation.npz
      -> instance-catalog.json -> ab1a_comparison_begins -> AB1a summaries

There were 0 violations, and the frozen geometry was re-verified afterwards (checks 33, 37). Position here plays its
second role, REFERENCE / EVALUATION: the original left Position at the exact saved left-core indices, in the head frame.

| vs Position (44,769 pairs) | median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|
| P_epi 3-D error [mm] | **0.408** | 0.634 | **0.696** | **0.788** | **0.929** |
| P_epi signed radial error [mm] | +0.408 | +0.634 | +0.696 | +0.788 | +0.929 (min −0.100) |
| P_epi relative \|radial\| | 9.1e-5 | 1.4e-4 | 1.6e-4 | 1.8e-4 | 2.1e-4 |
| P_ray 3-D error [mm] | 0.408 | 0.634 | 0.695 | 0.788 | 0.929 |
| truth left range [m] | 4.432 | — | 4.565 | 4.590 | 4.636 (min 4.270) |

- Fractions of P_epi within 1 / 5 / 10 / 25 mm: **1.000 / 1.000 / 1.000 / 1.000** (same for P_ray).
- The 3-D error is essentially all radial, and positive: the reconstruction is slightly too far.
- Reprojection of P_epi into the raw cameras:
  - left: median 3.25e-4 px, max 4.19e-4 px;
  - right: median 3.29e-4 px, max 4.26e-4 px.
- Composition of the correspondences (descriptive): 15 instances.
  - Cube.008: 36,126 pairs; 3-D error median 0.42 mm, max 0.91 mm.
  - wall.002: 3,493 pairs; median 0.17 mm.
  - woodWindow.005: 2,960; median 0.43 mm.
  - woodWindow.004: 1,671; median 0.44 mm.
  - Cube.005: 268; median 0.44 mm.
  - Cube.006: 96; median 0.77 mm.
  - Nine Cylinder.0xx instances with fewer than 50 pairs each.

Files: `evaluation/evaluation-summary.json` `dab6948b474d1c28bf43399d10667ed1a5a032c8b22eddd816f70b35963f933a`,
`evaluation/evaluation-result.npz` `a3017c6b34a0bc84c3b4b39598225f13898002f5731e7b67fa19ec15ca3c90ad`,
`evaluation/evaluation-opened-files.json` `200a6f0736a87c7cbd144c8057285a168ecb83d6bbb7c0b9992576f020949019`.

## POST-FREEZE AB1a COMPARISON (descriptive only)

AB1a figures are accepted and MEASURED in AB1a; AB1b figures are MEASURED here.

| | value |
|---|---|
| AB1a planar rectified core: reference-valid | **0 / 65,536** |
| AB1a planar rectified core: natural-valid | 0 / 65,536 |
| AB1a rectified-core pixels sourced from the nominal raw core | 0 |
| AB1a rectified-core raw source (L) | x 623.98–624.07, y 317.08–321.92 px |
| AB1a rectified-core centre | 14.26° from the gaze, 1.05° from the baseline |
| **AB1b raw-core rays represented** | **65,536 / 65,536** |
| **AB1b raw-core perfect correspondences** | **44,769 / 65,536** |
| **AB1b successfully triangulated** | **44,769 / 65,536** |

The comparison was read after the geometry freeze and changed nothing (check 38).

## Post-run scratch diagnostic (not part of the frozen evaluation; changes nothing)

After evaluation, I asked why the error is a systematic positive radial bias. The diagnostic is a scratch computation
over the frozen run files at `d0f1a23`, with no tool committed. It reads `evaluation-result.npz`,
`oracle-correspondences.npz`, `epipolar-result.npz` and the AB1a calibration:
- Projecting the left Position through the left camera gives a near-constant offset from the pixel centre:
  - du = +4.50e-4 px (std 3.1e-5);
  - dv = −6.41e-4 px (std 2.4e-5);
  - |offset| median 7.8e-4 px, max 8.9e-4 px.
  This matches AB1a's camera-model residual (max 0.00084 px L).
- Counterfactual: using that projection instead of the pixel centre as `uv_L` makes the triangulation error 2e-13 m
  (max 6e-13 m), with |φ residual| ≤ 9e-16 rad. The geometry itself is exact.
- First-order check: the left-ray angle offset θ_L(pixel centre) − θ_L(Position) has median 3.6e-7 rad (4.4e-4 px). Put
  through ∂r_L/∂θ_L = B sin θ_R cos δθ / sin² δθ, it reproduces the measured signed radial error with correlation
  **1.00000** (median 4.0767e-4 m predicted vs 4.0764e-4 m measured; max discrepancy 0.2 µm).

So the 0.41 mm median error is Blender's sub-millipixel Position sample offset, amplified by κ ≈ 200–430. It is not an
error of the representation, the formulas or the camera convention.

## Scientific outcome (contract section 15)

My reading of the measurements, for Luiz and Chat to judge:
- **Outcome 1 holds:** many correct correspondences (44,769 of 65,536 raw-core pixels) and accurate triangulation
  (≤ 0.93 mm everywhere, at ≈4.4 m). Spherical epipolar geometry is viable at gaze #1 given perfect correspondence, and
  it preserves the intended foveal region that planar rectification lost.
- **The outcome-2 conditioning is the decisive caveat for the next step:**
  - κ median 262 (up to 430);
  - a pixel-equivalent angular error of the right ray changes the range by about 0.94 m (median; 0.71–1.52 m);
  - so a natural matcher with 0.1 px error would give about 9 cm range error here, and 1 px about 0.9 m (first order,
    descriptive).
  The physical baseline (B⊥ ≈ 16.6 mm), not the representation, limits metric precision at this gaze.
- **Outcome 3 does not hold:** the raw fixation has ample binocular support. The 18,704 core pixels without a match look
  out through the window into empty space.
- **Outcome 4 does not occur:** φ residuals are ≈ 6e-4 px-equivalent, and δθ > 0 everywhere.

## Visual products (Visual Language 1)

Persistent, under `VIS`. Drawn at `d0f1a23` (the presentation fix); check 39 regenerates them byte-identically.

| file | truth badges | sha256 |
|---|---|---|
| `overview.png` | ORACLE INPUT, DERIVED, REFERENCE / EVALUATION | `b1000881b8510ffeaab5af88b6873077982b46f8ed52b14ede3884a5e3277288` |
| `raw-foveal-core.png` | ORACLE INPUT, DERIVED | `4536f1cb5de3a1b0f5471dff5a95abb98e044bc0859a2378abee4a667ffaf6d8` |
| `spherical-epipolar-core.png` | DERIVED, ORACLE INPUT | `f0a7a4d185f24a6dc10c2a2e0c6696e7648da029ff89c08100fe3ad53356ea16` |
| `perfect-correspondences.png` | ORACLE INPUT, DERIVED | `9bb5a6b2725ef65a00b7d8e891cff59182d9e4b76d777a9d8e4b7cf2e4c02150` |
| `epipolar-residual.png` | DERIVED | `2d23426e9299edc225bfc1496094660d110d25e0f2281749722ef3f8c6121206` |
| `angular-disparity.png` | DERIVED | `24b44653acb408fe3f82be4564c54cbe3971f9aa51bfd4ae9874f9a6fdd57d57` |
| `conditioning.png` | DERIVED | `da8e036e4cefebfe65ea90aabab71da0ecff77bb236df3a994a652053010cf47` |
| `reconstructed-point-cloud.png` | DERIVED | `3528ca1041d09be0f1f5747e77d5d61d6aeb1d2473533156cc8996fd788fdc46` |
| `triangulation-error.png` | REFERENCE / EVALUATION, DERIVED | `1e3092ca55f5b62d9918347e615fbab032c4839694465828609f0bafc2f1c8a3` |
| `planar-vs-spherical.png` | REFERENCE / EVALUATION, DERIVED | `45a8ca2f7bc00cfb5987508e08f2e5c91f972fdae38f0b464a398bc356b84d28` |
| `visuals-manifest.json` | — | `a1216d2c22095f6353260efeb93b452a7b429f7a3d29b7d760db8d27a056f88c` |

The overview asks: *does spherical epipolar geometry preserve and reconstruct the foveal region that planar
rectification lost?* It has four regions:
- **A — SAME OBSERVATION:** the saved raw L / R gaze-1 RGB with the nominal 12° core, the gaze / baseline geometry and
  "no new render".
- **B — SPHERICAL EPIPOLAR REPRESENTATION:** all 65,536 raw-core rays splatted into the gaze-centered display chart
  (RGB for display only), with the +X pole direction and its distance.
- **C — PERFECT CORRESPONDENCE / TRIANGULATION:** 24 representative ray pairs (equal chart v = equal φ; δθ magnified ×4,
  stated), the φ / δθ statistics and the RGB-coloured reconstruction.
- **D — REFERENCE / COMPARISON:** the error against Position, the conditioning, and AB1a 0 / 65,536 against AB1b
  65,536 / 44,769 / 44,769.

Position appears in two roles: ORACLE INPUT (correspondence generation) and REFERENCE / EVALUATION (scoring). The
geometry never sees it. Nothing is CONTROLLER-TIME. The display chart is labelled "display chart only", and no
natural-matcher raster is drawn.

Regenerate the figures with:

    .venv/bin/python tools/active_bootstrap/ab1b_run.py visualize --run RUN --visuals VIS

## Machine evidence

Under `RUN`:

| file | sha256 |
|---|---|
| `source/ab1a-source-manifest.json` | `85ced3e58ee6ce1ba53d6068a74cb7eb3e79eb02ceb73a6e5aaac8ff2298288c` |
| `oracle/oracle-summary.json` | `1ed55bbfdb0f92e704887e6b430f6988c2ce8260126e421f3828b57929c0b008` |
| `oracle/oracle-opened-files.json` | `8b7d3e5b6cf860bb8d9cb8955438a6c3e43060524afcc33e77f2cca0b8d65978` |
| `geometry/geometry-freeze-opened-files.json` | `b5fa5f2eef145906eb6c8c68f485617ebf582c926b18143008bdbc4df05ca3c0` |
| `synthetic/synthetic-report.json` | `73bad61b054ccdbc79bddf30c033a1e76f5d36db9e886eaddb2b2aed9470ae14` |
| `manifest.json` | `dfbf9d70e22b898bcdc6a137ec25725ed24d6a32b02c8f848d1605e8debce36d` |
| `check-summary.json` | `1530d608a13d1182b7909285a541b2e31799c350e5bee0d30dc300092d555ef4` |

The other files are listed in the sections above.

## Checks (MEASURED)

`tools/active_bootstrap/check_ab1b.py` at `d0f1a23`: **46/46** (`ACTIVE_BOOTSTRAP1B_CHECKS_PASS`; `check-summary.json`).

The checker keeps its own literal constants, and independently recomputes:
- the AB1a identities;
- the raw-core rays (its own K⁻¹, R_hc);
- θ via |b × d| and b · d, φ via the complex argument, the wrap via the complex exponential;
- the display chart;
- the oracle (its own world-to-head, projection, nearest-pixel and same-instance rule);
- the epipolar triangulation by the law of sines;
- the ray-ray triangulation by Cramer's rule with cross products, and the gap by the line-line distance;
- γ via atan2, κ and range-per-pixel;
- P_truth, the errors and the reprojection;
- the AB1a comparison values;
- the figures, byte for byte.

It also audits:
- the generator sources (AST: no SGBM, rectification, `cv2`, `fsg_stereo`, Blender, controller or fusion identifier /
  import; no truth identifier in the geometry module);
- the guard records, the ordered events, the run order and both freezes;
- the changed tracked files.

**Corruption / mutation suite: 51/51 caught from a passing baseline** (`ACTIVE_BOOTSTRAP1B_MUTATIONS_CAUGHT`). One more
probe was **not applicable**: "positive left instance rule dropped" leaves the canonical product unchanged, because no
raw-core hit has Object Index 0. The rule was exercised on the dev run (below). The probes cover:
- representation: the rectified core instead of the raw core; `cv2.stereoRectify`; SGBM;
- action and calibration: the gaze moved; the calibration changed;
- oracle: the right search restricted to the nominal core; same-instance visibility omitted; `uv_R` rounded; Position
  or an instance id put in the product;
- truth access: the geometry opening `reference-observation.npz`; P_epi replaced by Position truth;
- geometry definitions (each regenerated through the generator): θ from −Z; φ sign flipped; φ seam wrapping broken;
  L / R swapped; the baseline direction flipped; the baseline length set to 0.064 m;
- saved values: one `uv_L`, one `uv_R`, one θ, one φ, one δθ, one XYZ, P_ray, κ, the gap, the chart, one ray direction,
  θ_g, a raw-core statistic, a distribution, a truth label, the attrition;
- freezes and order: the product modified after its freeze; the geometry modified after evaluation; the reference read
  before the geometry freeze;
- evaluation: an error statistic, P_truth, a reprojection residual, the AB1a comparison;
- records and files: a Blender, a controller and a second-gaze command; a visual pixel; accepted FSG / AB1a / NB1c
  sources; an undeclared file; a failed synthetic case; an AB1a pin.

Other gates:
- layout 558/558 (at `53393e3`, and with this report);
- `scripts/verify_baseline.sh` 9/9;
- `git diff --check` clean.

Known answers before the canonical analysis (MEASURED at `53393e3`; analytic data only, no Classroom data): **synthetic
15/15**.
- Forward point: φ residual 0, error 8.9e-15 m.
- Six epipolar planes × three ranges: errors ≤ 6.8e-14 m.
- Near +X (θ_L = 0.0044 rad): error 9.9e-14 m.
- Exact ±X: flagged singular, φ NaN, no reconstruction.
- φ seam: wrapped residual 2.0e-6 rad; φ̄ = π.
- Swapped eyes and a flipped baseline sign: both reconstruct −P (error 4.006 m).
- B = 0.064: the reconstruction scales by 64/63.
- θ_R perturbed by 1e-7 rad: the first-order sensitivity matches to 3.2e-6 relative.
- 200 random points: |P_epi − P_ray| ≤ 8.4e-10 m (declared tolerance 1e-9 m).
- Gaze-#1 calibration: 65,536 finite rays, θ 9.115–21.854°, no `cv2`.
- Truth fields in the product: rejected.
- Guard: the geometry opening a reference observation is refused, with 1 violation recorded.
- End-to-end analytic planes at gaze #1 (float32 Position): 64,169 correspondences equal the analytic set; 2,846 outside
  the right nominal core; error median 5.3e-6 m, max 4.8e-5 m.
- Same-instance rule: a right-only occluder rejects exactly its 1,560 pairs; with the rule omitted, they are accepted.

## Incidents and deviations

1. **Development before the canonical analysis.** Dev runs used a scratch analytic AB1a-like source tree: planes, a
   gapped far plane, an instance-0 patch and procedural RGB, with no Classroom data. They were not committed.
   - On it: checks 46/46 and corruptions 52/52 (all applicable).
   - Two defects found there were fixed inside the implementation commit `53393e3`, before any canonical step:
     - check 33 first assumed the freeze mark is the first ordered event, but verifying the freeze legitimately reads
       the frozen files first. The rule became "no read other than the frozen geometry before the mark";
     - a mutation patch was wrapped twice.
2. **Presentation fix (`d0f1a23`, text only, after the geometry freeze; contract section 22).** The right panel of
   `reconstructed-point-cloud.png` is a projection onto head (−Z, Y), seen along the baseline. It was captioned
   "side view (along −Z)".
3. **One corruption probe not applicable** (positive-instance rule), because the canonical raw core has no Object
   Index 0 hit. This is recorded, not counted.
4. **Synthetic case 10 margin.** |P_epi − P_ray| reached 8.4e-10 m against the declared 1e-9 m. It is deterministic
   (seeded), and comes from the ray-ray least-squares cancellation for near-parallel rays near the pole. The checker's
   own ray-ray recomputation on the canonical data uses its own tolerance, 1e-7 m. Canonical |P_epi − P_ray| is
   ≤ 2.9e-7 m. P_ray agrees with the checker's Cramer route to 5.7e-10 m, and P_epi with the law-of-sines route to
   2.7e-13 m (check-summary).
5. **Extra recorded fields, beyond the contract's lists:**
   - `left-core-rays.npz` also holds `singular`;
   - the geometry and oracle guard records add `modules_loaded`;
   - the freeze step writes `geometry/geometry-freeze-opened-files.json` (declared in section 18).
6. **Correspondence-freeze ordering, as contracted.** The `geometry` command tests only that the correspondence freeze
   exists, which is not a read. `freeze-geometry` then verifies that the geometry's input hashes equal the freeze. This
   keeps the geometry's data reads to exactly two.
7. **Worktrees.** AB1a was accepted from a detached worktree and pushed to its branch ref, because the branch is
   checked out in an older session's worktree. AB1b used its own worktree, with `.venv` and `scenes/classroom` links.

## Statements

- No Blender, no render, no new gaze, no second fixation, no controller, no FSG6f, no fusion, no surface growth (checks
  3–7).
- No `cv2.stereoRectify`, no planar rectified image or crop, no SGBM, no learned stereo (checks 7, 8).
- The spherical geometry read only the calibration and the frozen, truth-stripped correspondence product. Position and
  Object Index entered only the oracle (ORACLE INPUT) and the post-freeze evaluation (REFERENCE / EVALUATION).
- The geometry was frozen before Position was reopened. Evaluation and the AB1a comparison changed nothing.
- Accepted code and products are unchanged: `fov3d/`, the controllers, NB1a / NB1b / NB1c, the FSG sources, the AB1a
  tools; the NB1a / NB1b / NB1c / AB1a run trees and visuals (checks 4, 40).
- No natural matcher was started.

## Unresolved decisions (Luiz and Chat)

1. ~~Scientific and qualitative review of AB1b and its figures.~~ **ACCEPTED** (see "Acceptance record").
2. ~~Whether the measured result establishes that "the geometry itself is sound", the stated precondition for a natural
   matcher experiment.~~

   **Decided:** the accepted conclusion is stated in the acceptance record and is not strengthened beyond it. A natural
   matcher does not follow directly. The next experiment, Active Bootstrap-1c, compares planar and spherical geometry with
   perfect correspondence in a favorable (safe-forward) head-relative regime. Natural RGB correspondence (AB1d) comes
   only after AB1c is judged.
3. ~~How to treat the conditioning at near-baseline gazes such as gaze #1 (κ ≈ 260; ≈0.94 m range per pixel-equivalent
   angle at ≈4.4 m) when correspondence becomes natural.~~

   **Decided (architectural):** conditioning is physical and is to be controlled by sensor / head pose, not compensated
   by the representation. Spherical epipolar geometry is not intended to make intrinsically poorly conditioned stereo
   physically precise. Active head pose should avoid poorly conditioned binocular configurations; local stereo operates
   in a favorable head-relative regime. A later experiment (AB1e) returns to this same difficult world target with
   whole-head recentering. The roadmap commit that follows this acceptance records the decision.
4. The ≈7.8e-4 px offset of Blender Position from the pixel centre (scratch diagnostic) bounds oracle-based metric
   checks at this conditioning to about 1 mm. It may matter for future oracle comparisons at large κ.

   **Recorded, not decided:** it stays a labelled post-run supporting diagnostic. AB1b acceptance does not depend on it.

## Acceptance record

Luiz and Chat completed the scientific, quantitative, code and qualitative visual review and **accept AB1b** as committed
at `a597c89`:

    ACTIVE_BOOTSTRAP1B_SPHERICAL_EPIPOLAR_GEOMETRY_ACCEPTED

- **Machine result accepted:**
  - `ACTIVE_BOOTSTRAP1B_SPHERICAL_EPIPOLAR_GEOMETRY_COMPLETE`;
  - `ACTIVE_BOOTSTRAP1B_CHECKS_PASS` 46/46;
  - `ACTIVE_BOOTSTRAP1B_MUTATIONS_CAUGHT` 51/51 from a passing baseline (one probe not applicable, recorded);
  - `AB1B_SYNTHETIC_PASS` 15/15.
- **Accepted scientific conclusion:**
  - At the deliberately difficult gaze #1, gaze-centered spherical epipolar geometry preserves the intended foveal
    support and yields correct metric geometry when correspondence is supplied perfectly.
  - Therefore the failure observed in AB1a was a planar-representation failure, not an absence of binocular support.
  - Metric precision at gaze #1 nevertheless remains strongly limited by physical stereo conditioning, because the
    fixation lies near the physical eye baseline.
- **Accepted measured facts** (MEASURED in the sections above; unchanged):

  | quantity | value |
  |---|---|
  | raw-core rays represented | 65,536 / 65,536 |
  | perfect binocular correspondences | 44,769 / 65,536 |
  | spherical triangulations | 44,769 / 65,536 |
  | \|φ_R − φ_L\| median / p95 / max | 1.93e-6 / 3.22e-6 / 3.88e-6 rad |
  | δθ | positive for all 44,769 pairs |
  | κ median / p95 | about 262 / about 384 |
  | epipolar vs independent ray-ray reconstruction, median / max | about 8.1e-8 m / about 2.9e-7 m |
  | post-freeze error against Blender Position, median / p95 / p99 / max | 0.408 / 0.696 / 0.788 / 0.929 mm |
  | AB1a planar rectified reference-valid (accepted, MEASURED in AB1a) | 0 / 65,536 |

- **Post-run supporting diagnostic (labelled; not a frozen scientific claim).** The ≈7.8e-4 px offset of Blender Position
  from the pixel centre ("Post-run scratch diagnostic") is useful supporting evidence for the ≈0.4 mm systematic radial
  bias. AB1b acceptance does **not** depend on making that diagnostic a stronger frozen claim.
- **Synthetic case 10 margin stays recorded** (incident 4): |P_epi − P_ray| reached 8.4e-10 m against its declared 1e-9 m
  known-answer tolerance. It is deterministic, not a blocker, and does not reopen the experiment.
- **Visual review accepted.** Luiz and Chat inspected the primary scientific visual
  `visuals/active-bootstrap/ab1b-spherical-epipolar-geometry/overview.png`
  (`b1000881b8510ffeaab5af88b6873077982b46f8ed52b14ede3884a5e3277288`). Accepted qualitative interpretation:
  - **A:** the same saved physical observation, no new render;
  - **B:** the spherical representation preserves the finite two-dimensional foveal support;
  - **C:** the perfect correspondences satisfy the epipolar organization and triangulate into coherent geometry;
  - **D:** the AB1a planar support failure and the AB1b spherical recovery are shown side by side, while the poor
    conditioning remains explicit.

  The figure satisfies the project's Level-A scientific-visual requirement.
- **Conditioning caveat retained.** κ median 262 (up to 430) and a median 0.94 m of range per pixel-equivalent angle at
  ≈4.4 m: the physical baseline (B⊥ ≈ 16.6 mm), not the representation, limits metric precision at gaze #1.
- **No natural matcher has yet been run.** AB1b used perfect / oracle correspondence only.
- **AB1b is complete.** Its run is the accepted record. Later steps read its frozen products; nothing is re-rendered or
  recomputed.
- **This acceptance step** made no new observation, ran no render and did no scientific computation. It changed only
  this status record, and (in the next commit) `CLAUDE.md`, the Chat Handoff and the layout checker's handoff assertion.
  The AB1b code, contract, canonical run, figures and measured numbers are unchanged.
