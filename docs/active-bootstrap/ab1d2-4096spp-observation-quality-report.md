# Active Bootstrap-1d2 — 4096-spp Observation-Quality Control — report

**Markers.**

    ACTIVE_BOOTSTRAP1D2_4096SPP_OBSERVATION_QUALITY_COMPLETE
    ACTIVE_BOOTSTRAP1D2_4096SPP_OBSERVATION_QUALITY_ACCEPTED

**Status: ACCEPTED.** Luiz and Chat accepted AB1d2 after scientific, quantitative, independent GitHub code, checker /
corruption and qualitative visual review (see "Acceptance record" at the end). Observation quality was a major
limitation of AB1d; large residual along-epipolar ambiguities remain. The sections below are the report as completed at
`cb73e56`, unchanged.

> **Question.** Holding scene, gaze, camera geometry, calibration, renderer settings, random-seed convention, matcher,
> search interval, patch, score, refinement, benchmark and evaluation FIXED, does increasing the Cycles sampling from
> 256 spp to 4096 spp materially improve natural spherical epipolar correspondence?

**Answer at the three accepted AB1c / AB1d views (MEASURED): yes, strongly, and at every gaze; but large ambiguous
regions remain.**

Only the sample count changed. Every other load-bearing render setting, the calibration (byte-identical), the camera
matrices, the seeds, the scene and the search geometry (bitwise) were verified identical. The same frozen AB1d matcher
was scored against the same AB1c oracle, pixel by pixel:

| gaze | within 1 px-equiv, 256 → 4096 | median px-equiv error, 256 → 4096 | oracle top-1, 256 → 4096 | oracle ZNCC median, 256 → 4096 | 3-D error median vs perfect, 256 → 4096 |
|---|---|---|---|---|---|
| 1 | 9.2 % → **35.9 %** | 93.1 → **26.4** px | 9.9 % → **36.5 %** | 0.420 → **0.849** | 4.16 → **3.28** m |
| 2 | 16.8 % → **66.6 %** | 57.4 → **0.26** px | 17.7 % → **67.0 %** | 0.484 → **0.924** | 3.57 m → **63.8 mm** |
| 3 | 9.2 % → **49.2 %** | 129.2 → **1.75** px | 9.8 % → **49.8 %** | 0.288 → **0.779** | 4.03 → **0.48** m |

(256 values: the accepted AB1d run, reproduced exactly here. 4096 values: this run, all evaluable pixels.)

- On the pixels evaluable in both conditions, the error shrinks for 66 / 78 / 73 % of pixels.
- 16,024 / 32,339 / 27,281 pixels move from > 1 px to ≤ 1 px, against 1,739 / 882 / 1,080 moving the other way.
- The oracle-on-curve ZNCC rises for 94 / 98 / 96 % of pixels.
- The improvement is broad across the three lower texture quartiles, where AB1d's labelled diagnostic located the
  problem (gaze 2 Q1: 6 % → 68 % within 1 px). It is smallest in the highest-texture quartile.

What remains:
- 64 / 33 / 51 % of pixels are still worse than 1 px, and the oracle is worse than the 8th peak for 27 / 15 / 19 %.
- Gaze 1's median error is still 26 px.
- At gaze 2 the highest-texture quartile barely changes (median 12.5 → 11.6 px).
- Metric precision is still limited: ≤ 12 mm from the perfect reconstruction for 4.2 / 14.7 / 7.3 % of points.

My reading: every Outcome 1 indicator holds at every gaze, so AB1d's negative result was strongly observation-quality
limited. What remains matches Outcome 2's qualifier: large ambiguous regions remain. Both observation quality and
local-patch ambiguity matter. It is not Outcome 3 and not Outcome 4. See "Scientific outcome".

This is an observation-quality control on fixed, accepted geometry and a frozen matcher. AB1d2 does not propose a
matcher.

## Provenance

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (`origin` verified by `source` and check 01) |
| AB1d acceptance | `c5f9bf599d2e537e7d4021adacc7e53269bd18c7` (`ACTIVE_BOOTSTRAP1D_SAFE_FORWARD_NATURAL_CORRESPONDENCE_ACCEPTED`) |
| base (post-AB1d roadmap, `main`) | `22f538f8eb2dad69d45b7fc3183fbcc2ee861d55` |
| branch | `active-bootstrap/ab1d2-4096spp-observation-quality`, from `22f538f`; isolated worktree |
| contract | `6f5b757754230429c89fd3d358316a5180b6d623` (before any implementation and any 4096-spp Classroom render) |
| implementation | `b66d7f76998566bb29754e63252ddf2b6fb9c9ae` (all canonical stages ran from it, clean and pushed) |
| post-run figure layout fix | `e4c60ebbbd1823febdbd47aa3c9705fa8f1f78ce` (presentation only; see "Incidents") |
| report | this commit |

Run: `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1d2-4096spp-observation-quality/` (`RUN`).
Visuals: `/home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1d2-4096spp-observation-quality/` (`VIS`).

### Accepted sources pinned (verified by `source`, checks 02–04)

- **Accepted AB1c observations:** calibrations `ae56ef33…` / `ab348665…` / `085ff332…`; 256-spp RGB `d6e2a532…` /
  `297c5bd6…` / `5924f946…`; acquisition records; AB1c manifest `21640f6a…`; instance catalog `948dd8d4…`.
- **Accepted AB1c benchmark:** the oracle, perfect spherical and Position files of all three gazes (the AB1d
  `BENCH_PINS`), all in the AB1c manifest.
- **Accepted AB1d products:**
  - manifest `3f6a837d…`; correspondence freeze `006c9116…`; geometry freeze `0c2d7b0a…`; evaluation summary `692f49d7…`;
  - per-gaze matcher records, natural products, spherical results and evaluation results;
  - visuals manifest `c7391c7b…` (the twelve example pixels).
- **Accepted code (22 files, unchanged), in four groups:**
  - AB1d tools: `ab1d_match.py`, `ab1d_spec.py`, `ab1d_run.py`, `check_ab1d.py`, `ab1d_visuals.py`;
  - render path: `ab1a_render.py`, `ab1a_spec.py`, `ab1c_render.py`, `ab1c_spec.py`, `classroom_oracle1_render.py`,
    `render_foveated.py`, `bl_common.py`, `exr_lite.py`;
  - geometry and photometry: `ab1b_geometry.py`, `ab1b_spec.py`, `fsg_geometry.py`, `fsg_stereo.py`, `nb1a_guard.py`;
  - figure helpers: `ab1b_visuals.py`, `ab1c_visuals.py`, `style.py`, `breadth1_visuals.py`.
- **Classroom blend** `dca66a32…`; head pose `6ef83319…`.

## What ran (MEASURED, `process-log.jsonl`; each canonical stage once, in order, from `b66d7f7`, clean and pushed)

| # | command | result | seconds |
|---|---|---|---|
| 1 | `ab1d2_run.py source` | 22 code pins, 9 AB1c observation pins, 16 AB1d pins; matcher constants identical | 0.1 |
| 2 | `ab1d2_run.py preflight-tests` | `AB1D2_PREFLIGHT_PASS` 69/69 | 0.3 |
| 3 | `ab1d2_run.py rehearse` | `AB1D2_REHEARSAL_PASS` (synthetic room; never Classroom) | 11.6 |
| 4 | `ab1d2_run.py preflight` | Classroom loaded, NO render; calibration diff 0.0, byte-identical; set camera matrices diff 0.0; settings identical except samples | 0.6 |
| 5 | `ab1d2_run.py render-4096` | 6 eye renders; render control ok for every gaze | 106.6 |
| 6 | `ab1d2_run.py freeze-observation` | 11 files hashed | 0.2 |
| 7 | `ab1d2_run.py match` | the accepted AB1d matcher; reads exactly calibration + 4096 RGB | 57.1 |
| 8 | `ab1d2_run.py freeze-correspondence` | search geometry bitwise identical to AB1d (12 fields × 3 gazes) | 0.8 |
| 9 | `ab1d2_run.py spherical` | the accepted AB1b geometry; all natural matches triangulated | 1.7 |
| 10 | `ab1d2_run.py freeze-geometry` | 15 files hashed; truth reads 0 | 0.1 |
| 11 | `ab1d2_run.py evaluate-paired` | 256-spp reproduction exact at all three gazes | 8.3 |
| 12 | `ab1d2_run.py visualize` | 6 figures (`b66d7f7`); regenerated once at `e4c60eb` after the layout fix | 4.0 |
| 13 | `check_ab1d2.py --corruptions --write-summary` | 41/41; null probe clean; corruptions 44/44 | ≈ 230 (batch) |

## Proof that only the sample count changed (MEASURED, `observations/render-control.json` `9b982634…`)

| property | 256 spp (accepted AB1c / AB1d) | 4096 spp (AB1d2) |
|---|---|---|
| samples (record, Blender readback, Cycles EXR header) | 256 | **4096** |
| gaze (yaw, pitch °) | (−18.75, −5.75) / (+6.75, +6.75) / (+18.75, −5.25) | same |
| calibration sha256 | `ae56ef33…` / `ab348665…` / `085ff332…` | same (byte-identical file) |
| camera matrices (both eyes) | AB1c record | equal (set-and-readback difference 0.0) |
| resolution | 640 × 640, 100 % | same |
| engine / device | CYCLES / GPU OPTIX | same |
| denoising | OFF | OFF |
| adaptive sampling | OFF | OFF |
| pixel filter | BOX, width 1.0 | same |
| motion blur / film | OFF / opaque | same |
| L seed / R seed | 2111 / 2112 | 2111 / 2112 |
| EXR channels (41, incl. Position / Object Index) | AB1c set | same |
| EXR `Scene` / `Camera` / `Software` | `_mainScene` / `CLASSROOM_ORACLE1`(`.001`, `.002`) / Blender 5.2.1 LTS | same |
| scene objects (instance catalog) | AB1c list | identical |
| primary camera samples per pair | 209,715,200 | 3,355,443,200 (× 16) |

**Every difference, by field class:**
- In each acquisition record, 24 fields are MUST EQUAL and all are equal.
- EXPECTED DIFFERENT: `spp`; `settings.samples`; `primary_camera_samples`; render seconds; the RGB hash (changed);
  `created_utc`.
- LABEL: `experiment`; `action_source`; `observation_quality_control`; `blend` (path text in another worktree, same
  real path, sha256 pinned).
- EXR headers: 16 attributes MUST EQUAL; `cycles.interior.samples` `'256'` → `'4096'`; five timing attributes; `File`
  (same real path).
- No field or attribute fell outside the declared classes.

### Render cost (MEASURED, acquisition records)

| gaze | 256 spp L / R s (AB1c) | 4096 spp L / R s |
|---|---|---|
| 1 | 1.81 / 1.28 | 18.12 / 17.55 |
| 2 | 1.65 / 1.21 | 17.33 / 16.90 |
| 3 | 1.60 / 1.19 | 16.96 / 16.50 |

Six 4096-spp eye renders: 103.4 s of render calls; the Blender process 106.3 s; the stage 106.6 s. This is well inside the
30-minute budget, so no setting was touched.

### 4096-spp observation hashes (MEASURED; frozen in `freeze/observation-freeze.json` `7c8ed0a3…`)

| gaze | `rgb-observation.npz` sha256 |
|---|---|
| 1 | `9d653bd1fa1bb2d1d59847b0a55c1b43603b5628beb3bc70f29975d4e57bf02c` |
| 2 | `3046cc66f67494b5f639380c46f25672c2259684f28511ba5366f872986e4bba` |
| 3 | `fd9ecd4ed94b8c6fdc91a1dd7501840da2934b335387515b10098dc69497ce75` |

## The matcher and geometry: unchanged (MEASURED)

- **The matcher, run unchanged:** the accepted `ab1d_run.run_match_gaze`, under its own allowlist guard and cv2
  tripwires. It ran with the frozen defaults: 5 × 5 angular patch, `linear_to_u8` + Rec.709 gray, MIN_LOCAL_STD_U8 0.5,
  1 px spacing over the full admissible segment, ZNCC, TOP_K 8 with 3 px separation, and one parabola bounded at
  ±0.75.
- **Reads and match times:**
  - Each gaze read exactly its calibration and its 4096 RGB, with 0 violations and 0 truth reads.
  - Match time 17.8 / 18.5 / 17.9 s.
  - The match summaries carry the accepted matcher config SHA256. The independent re-implementation (check 21) agrees
    with every checked row.
- **Search geometry:** bitwise identical to AB1d over the full core of every gaze for `left_core_row/col`, `uv_L`,
  `theta_L`, `phi_L`, `q_inf`, `line_dir`, `line_l`, `k_first`, `k_last`, `candidate_count` and `valid_left_patch`
  (`match/search-geometry-identity.json`). The full search interval is unchanged (median 351.5 / 353.5 / 351.5
  admissible candidates).
- **Spherical geometry:** the accepted AB1b geometry, via the accepted `run_spherical_gaze`; it read exactly the
  calibration and the frozen natural product.
- **One effect of the unchanged texture threshold.** At 4096 spp, 105 / 52 / 5 left patches fall below 0.5 u8
  (`LOW_TEXTURE`); at 256 spp all 65,536 passed. So the natural-valid counts are 65,431 / 65,484 / 65,531, and 104 / 52 /
  5 oracle pixels drop out of the evaluable set. Likewise 1,934 / 377 / 847 oracle right patches become unscorable at
  4096 (std < 0.5 u8), against 0 at 256. The flatter patches are the expected effect of less noise. The threshold was
  not changed.

## Absolute 4096-spp result (MEASURED; the accepted AB1d evaluation definitions)

| gaze | oracle pairs | natural valid | evaluable | coverage | median px-equiv | p90 | p95 | p99 | max | ≤ 0.10 | ≤ 0.25 | ≤ 0.50 | ≤ 1.00 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 53,750 | 65,431 | 53,646 | 0.998 | 26.40 | 232.5 | 286.6 | 361.6 | 451.8 | 0.106 | 0.227 | 0.321 | 0.359 |
| 2 | 63,293 | 65,484 | 63,241 | 0.999 | 0.258 | 96.8 | 164.1 | 303.4 | 459.7 | 0.273 | 0.493 | 0.627 | 0.666 |
| 3 | 65,493 | 65,531 | 65,488 | 1.000 | 1.748 | 241.4 | 303.4 | 383.2 | 462.1 | 0.165 | 0.335 | 0.454 | 0.492 |

| gaze | signed e_θ median | \|e_θ\| median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| 1 | +21.6 mrad | 21.6 mrad | 190.4 mrad | 234.2 mrad | 295.2 mrad | 364.6 mrad |
| 2 | +0.025 mrad | 0.211 mrad | 78.9 mrad | 134.1 mrad | 247.6 mrad | 371.8 mrad |
| 3 | +0.34 mrad | 1.43 mrad | 197.4 mrad | 247.8 mrad | 312.1 mrad | 373.6 mrad |

| gaze | top 1 | top 3 | top 5 | top 8 | worse than 8 | oracle ZNCC median | best ZNCC median | oracle − best median | peak margin median |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.365 | 0.555 | 0.647 | 0.730 | 0.270 | 0.849 | 0.851 | −0.011 | 0.022 |
| 2 | 0.670 | 0.779 | 0.821 | 0.848 | 0.152 | 0.924 | 0.906 | +0.002 | 0.048 |
| 3 | 0.497 | 0.680 | 0.751 | 0.812 | 0.188 | 0.779 | 0.776 | −0.004 | 0.039 |

The averaged score still peaks exactly at the oracle location (offset medians at −1, −0.5, 0, +0.5, +1 px:
0.449 / 0.707 / **0.849** / 0.718 / 0.454 at gaze 1; 0.687 / 0.841 / **0.924** / 0.834 / 0.692 at gaze 2; 0.383 / 0.645 /
**0.779** / 0.647 / 0.386 at gaze 3).

## PRIMARY: paired 256 → 4096 comparison (MEASURED, `evaluation/<g>/paired-result.npz`)

Common set C = core indices evaluable in both conditions (only-256: 104 / 52 / 5, the new `LOW_TEXTURE` pixels;
only-4096: 0). E = |pixel-equivalent error|, ΔE = E4096 − E256 (negative = improvement); equality tolerance
ε = 1e-9 px, declared in the contract.

| gaze | \|C\| | median E256 | median E4096 | median ΔE | ΔE p10 / p50 / p90 | improved | equal | worsened | improved > 1 px | worsened > 1 px |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 53,646 | 93.00 | 26.40 | −16.80 | −212.7 / −16.8 / +109.0 | 0.662 | 0.001 | 0.338 | 0.583 | 0.273 |
| 2 | 63,241 | 57.37 | 0.258 | −16.14 | −240.5 / −16.1 / +7.4 | 0.779 | 0.003 | 0.219 | 0.652 | 0.140 |
| 3 | 65,488 | 129.21 | 1.748 | −42.65 | −245.9 / −42.6 / +111.9 | 0.727 | 0.000 | 0.273 | 0.659 | 0.229 |

Paired 1-px transitions (a descriptive bin, not an acceptance threshold):

| gaze | bad → good | good → good | good → bad | bad → bad |
|---|---|---|---|---|
| 1 | 16,024 (0.299) | 3,225 (0.060) | 1,739 (0.032) | 32,658 (0.609) |
| 2 | 32,339 (0.511) | 9,762 (0.154) | 882 (0.014) | 20,258 (0.320) |
| 3 | 27,281 (0.417) | 4,918 (0.075) | 1,080 (0.016) | 32,209 (0.492) |

Pooled over the three gazes (182,375 pixels): median E 92.3 → 0.68 px; improved 0.726, worsened 0.273.

## Paired photometric effect (MEASURED)

| gaze | oracle ZNCC median 256 → 4096 | ΔZ median (p10 / p90) | oracle score increased | unscorable 256 / 4096 | oracle − best median 256 → 4096 | best ZNCC median 256 → 4096 |
|---|---|---|---|---|---|---|
| 1 | 0.421 → 0.849 | +0.289 (+0.057 / +0.685) | 0.938 | 0 / 1,934 | −0.209 → −0.011 | 0.661 → 0.851 |
| 2 | 0.485 → 0.924 | +0.358 (+0.010 / +0.752) | 0.977 | 0 / 377 | −0.140 → +0.002 | 0.661 → 0.906 |
| 3 | 0.288 → 0.779 | +0.378 (+0.058 / +0.730) | 0.964 | 0 / 847 | −0.295 → −0.004 | 0.614 → 0.776 |

Rank transitions (counts on C):

| gaze | top-1: not → in | in → in | in → not | not → not | top-3: not → in / in → not | top-8: not → in / in → not |
|---|---|---|---|---|---|---|
| 1 | 16,152 | 3,408 | 1,912 | 32,174 | 20,573 / 2,487 | 20,593 / 2,626 |
| 2 | 32,209 | 10,188 | 1,028 | 19,816 | 31,451 / 1,336 | 27,036 / 1,986 |
| 3 | 27,379 | 5,200 | 1,215 | 31,694 | 33,722 / 1,487 | 33,900 / 1,550 |

The best competing peak also rises:
- **Competing peak.** The best recorded distinct peak farther than 1.5 px from ORACLE-ON-CURVE has median ZNCC
  0.655 → 0.811 / 0.647 → 0.809 / 0.609 → 0.703 (median Δ +0.096 / +0.080 / +0.077). It rises by less than the
  oracle's own score (+0.29 / +0.36 / +0.38).
- **Peak margin.** The best-minus-second distinct peak median goes 0.027 → 0.022 / 0.025 → 0.048 / 0.031 → 0.039.

**The true correspondence becomes far more photometrically distinctive. Its distinct competitors still score high,
so the decision remains marginal for many pixels.**

## Metric consequence (MEASURED; the accepted AB1b spherical geometry on the frozen natural correspondence)

| gaze | vs perfect median (256 → 4096) | p90 (4096) | p95 (256 → 4096) | p99 (4096) | max (4096) | vs Position median / p95 (4096) | ≤ 12 mm (256 → 4096) | ≤ 25 mm | ≤ 50 mm |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 4.161 → 3.283 m | 4.570 m | 4.645 → 4.631 m | 33.37 m | 71.6 m | 3.283 / 4.631 m | 0.009 → 0.042 | 0.018 → 0.086 | 0.034 → 0.162 |
| 2 | 3.569 m → 63.8 mm | 3.981 m | 7.710 → 7.656 m | 71.82 m | 73.0 m | 0.0638 / 7.657 m | 0.029 → 0.147 | 0.055 → 0.278 | 0.093 → 0.442 |
| 3 | 4.031 → 0.482 m | 4.341 m | 4.505 → 4.446 m | 13.54 m | 70.7 m | 0.482 / 4.446 m | 0.013 → 0.073 | 0.026 → 0.148 | 0.047 → 0.267 |

- **Paired on C:** the 3-D error vs perfect improves for 0.655 / 0.769 / 0.719 of pixels (median Δ −0.19 / −1.62 /
  −0.65 m).
- **Why metric precision lags correspondence:**
  - At ≈ 4.5 m one pixel-equivalent of θ_R is about 0.25–0.32 m of range (accepted AB1c conditioning).
  - So "within 1 px" and "within 12 mm" are very different bars. The 12 mm fraction stays small (4–15 %) even where most
    correspondences are within 1 px.
  - The far tail (p99 13–72 m) comes from false matches near zero parallax.
- The 12 mm bin remains descriptive only.

## Observation-quality diagnostics (descriptive; no noise variance is claimed)

**Paired gray change.** |G4096 − G256| on the nominal core, median / p90 / p95 [u8]:

| gaze | L eye | R eye | signed mean L / R |
|---|---|---|---|
| 1 | 1.28 / 4.00 / 5.14 | 1.72 / 4.07 / 5.21 | +0.103 / +0.085 |
| 2 | 2.21 / 6.93 / 8.86 | 2.14 / 6.93 / 8.79 | +0.113 / +0.095 |
| 3 | 2.14 / 6.64 / 8.49 | 2.07 / 6.21 / 8.28 | +0.128 / +0.165 |

Over the full raster the median is 2.00 / 2.00 / 2.29 u8 and the signed mean +0.11 to +0.14 u8. This is the change
between two renders, not a noise estimate.

**The small positive signed mean** (4096 slightly brighter, by about 0.1 u8 against a median change of about 2 u8) is
recorded because the contract names a systematic signed mean as a possible sign of a non-sampling difference.
- Every load-bearing setting was verified identical (above).
- ASSUMED / NOT TESTED: this is consistent with averaging through the concave `linear_to_u8` transfer. Under that
  transfer, a noisier image maps to slightly lower u8 values on average.
- I do not treat it as an Outcome 4 inconsistency. Luiz and Chat should judge it.

**Patch texture.**
- The left 5 × 5 patch std over all core pixels, quartiles 25 / 50 / 75 % [u8], falls at 4096: 2.50 / 3.44 / 5.35 →
  1.14 / 2.02 / 4.83 (gaze 1); 3.60 / 5.26 / 13.25 → 1.79 / 3.28 / 12.60 (gaze 2); 2.86 / 3.67 / 6.26 → 1.13 / 1.69 /
  4.58 (gaze 3).
- The oracle right-patch std on C falls likewise: median 2.52 → 1.62, 4.16 → 2.87, 2.64 → 1.38.
- At 256 spp, noise inflated the apparent texture of weak patches.

**PROXY quantities** (labelled PROXY; never a sensor-noise variance):

| gaze | PROXY-LR: oracle L − R robust std, 256 → 4096 [u8] | PROXY-HP: left high-pass robust std / √1.25, 256 → 4096 [u8] |
|---|---|---|
| 1 | 2.87 → 1.12 | 2.79 → 1.33 |
| 2 | 4.54 → 1.30 | 4.43 → 1.73 |
| 3 | 4.08 → 1.28 | 3.69 → 1.42 |

The 256 values reproduce AB1d's labelled post-run diagnostic. The proxies fall 2.6–3.5 × (LR) and 2.1–2.6 × (HP).
They contain non-noise terms (texture, view-dependent shading), so their ratio is not a variance ratio.

**Texture-stratified paired result** (quartiles of the 256-spp left patch std, applied to both conditions):

| gaze | stratum | median E 256 → 4096 [px] | ≤ 1 px 256 → 4096 | top-1 256 → 4096 | oracle ZNCC 256 → 4096 |
|---|---|---|---|---|---|
| 1 | Q1 (≤ 2.46) | 147.9 → 67.5 | 0.030 → 0.333 | 0.036 → 0.338 | 0.153 → 0.645 |
| 1 | Q2 | 116.9 → 23.5 | 0.050 → 0.393 | 0.059 → 0.401 | 0.229 → 0.755 |
| 1 | Q3 | 86.5 → 14.4 | 0.117 → 0.405 | 0.123 → 0.409 | 0.579 → 0.904 |
| 1 | Q4 (> 4.91) | 46.0 → 16.1 | 0.174 → 0.305 | 0.178 → 0.310 | 0.844 → 0.965 |
| 2 | Q1 (≤ 3.58) | 124.5 → 0.32 | 0.062 → 0.677 | 0.070 → 0.680 | 0.226 → 0.778 |
| 2 | Q2 | 85.5 → 0.18 | 0.096 → 0.784 | 0.103 → 0.787 | 0.333 → 0.896 |
| 2 | Q3 | 35.0 → 0.13 | 0.239 → 0.837 | 0.248 → 0.842 | 0.559 → 0.942 |
| 2 | Q4 (> 12.49) | 12.5 → 11.6 | 0.277 → 0.366 | 0.289 → 0.372 | 0.972 → 0.993 |
| 3 | Q1 (≤ 2.86) | 128.0 → 8.47 | 0.024 → 0.439 | 0.030 → 0.447 | 0.123 → 0.614 |
| 3 | Q2 | 143.3 → 4.73 | 0.040 → 0.473 | 0.045 → 0.476 | 0.154 → 0.658 |
| 3 | Q3 | 134.0 → 0.49 | 0.085 → 0.540 | 0.091 → 0.543 | 0.313 → 0.816 |
| 3 | Q4 (> 6.25) | 100.7 → 0.63 | 0.218 → 0.515 | 0.226 → 0.523 | 0.829 → 0.971 |

- **The gains are broad across Q1–Q3.** The lowest quartile's oracle ZNCC rises 3.4–5 ×. Q4 gains least.
- **The highest-texture quartile can stay ambiguous.**
  - At gaze 2 the true location already correlated at 0.97 in Q4. It goes to 0.99, yet the median error is unchanged
    (≈ 12 px), because near-equal peaks along the line remain.
  - My interpretation, not separately measured: this is the high-contrast board and frame structure, i.e. the
    along-epipolar (aperture-type) ambiguity that AB1d retained as its second failure mechanism. Sampling noise would
    not remove it.

## Scientific outcome (contract section 19)

My reading, for Luiz and Chat to judge: **all four Outcome 1 indicators hold at every gaze, so the AB1d negative
result was strongly observation-quality limited. The residual matches Outcome 2's qualifier (large ambiguous regions
remain). Both Monte Carlo observation quality and local-patch ambiguity matter.**

- **Outcome 1 indicators, each met at all three gazes:**
  - **Oracle scores increase:** for 94–98 % of pixels; median +0.29 to +0.38.
  - **Oracle ranks improve:** top-1 × 3.7 / × 3.8 / × 5.1; top-1 gains outnumber losses 8–31 to 1.
  - **Correspondence errors shrink:** improved for 66–78 %; 16k–32k pixels cross into ≤ 1 px against 0.9k–1.7k
    leaving.
  - **Metric reconstruction improves:** median 3-D error 4.16 → 3.28 m, 3.57 m → 64 mm, 4.03 → 0.48 m; ≤ 12 mm × 4.6
    to × 5.6.
- **The frozen matcher becomes substantially more useful with no change.** Gaze 2 reaches a median of 0.26 px with
  67 % within 1 px; gaze 3 reaches 1.75 px and 49 %.
- **Outcome 2 qualifier: large ambiguous regions remain.**
  - Gaze 1 keeps a 26 px median and 64 % of its pixels beyond 1 px.
  - 15–27 % of oracles stay worse than the 8th peak.
  - Distinct competitors rise with the oracle (median competing ZNCC 0.70–0.81), and peak margins stay near 0.02–0.05.
  - The highest-texture quartile at gaze 2 does not improve.
  - Metric precision (≤ 12 mm for 4–15 %) is not generally useful.
- **Not Outcome 3:** the improvement is large, broad and systematic.
- **Not Outcome 4:**
  - geometry is bitwise identical;
  - settings differ only in spp;
  - the 256 reproduction is exact;
  - nothing systematically worsens.

  Worsened pixels are a minority (34 / 22 / 27 %; MEASURED post-run from `paired-result.npz`). Of them, 83 / 69 / 84 %
  were already worse than 1 px at 256 spp and stay so; at 4096 the oracle is not the top peak for 93 / 76 / 90 % of
  them. Good → bad is 3.2 / 1.4 / 1.6 % of all pixels.

  The small signed brightness shift is recorded above with its interpretation labelled.

## Checks (MEASURED)

`tools/active_bootstrap/check_ab1d2.py` at `e4c60eb`: **41/41** (`ACTIVE_BOOTSTRAP1D2_CHECKS_PASS`; `check-summary.json`
`a139683bab6a3b95fa68cb0f1ad6fe61cd93b8d9369412511ec5f13243c0231b`).

The checker keeps its own literal pins and constants:
- **Render control.**
  - It re-implements the section-7 classification and reads the EXR headers itself.
  - It recomputes the camera matrices from the calibration.
  - It confirms 4096 in the record, the readback and both EXR headers of every gaze, against 256 in the accepted headers.
- **Search geometry.** It recomputes the identity over the full core.
- **Independent matcher.** It runs the accepted AB1d checker's independent matcher on the 4096 RGB for core index
  % 32 == 7 plus the twelve example pixels: 0 mismatches.
- **Evaluation.**
  - It recomputes the 4096 θ errors, local pixel scale, ORACLE-ON-CURVE, ranks and subset oracle ZNCC with its own
    primitives.
  - It verifies that the paired 256 side equals the accepted AB1d arrays and summary.
  - It recomputes the paired ΔE, ε-fractions, transitions, ΔZ, rank transitions, competing peaks, metric consequence and
    diagnostics (including the PROXY labels).
- **Audits.** Guard records, freeze contents and order, the process log, the manifest, the declared changed files, and
  a static scan for overrides, other matchers, head motion or controller.
- **Figures.** It regenerates every figure byte-identically.

**Corruption / mutation suite: 44/44 caught** from a passing baseline, after an unmodified-mirror **null probe**
passed all 41 checks (`ACTIVE_BOOTSTRAP1D2_MUTATIONS_CAUGHT`). Each corruption names the checks that must catch it and
counts only if one of them fails. The families:
- **Render:** spp 2048 in the record; 2048 in the EXR header (the attribute rewritten in a mirrored EXR); denoising;
  adaptive; L seed; R seed; L = R seed; pixel filter; resolution; camera pose; one gaze; calibration.
- **Source:** the accepted 256 observation altered; the accepted AB1d matcher source altered; the accepted benchmark
  altered (the last two through overrides of the accepted inputs).
- **Matcher** (a mutated matcher's output stored for the checked rows): 7 × 7 patch; texture threshold 4.0; spacing
  0.5; hidden depth truncation (k ≤ 100); SAD instead of ZNCC; refinement bound 0.3; a changed texture constant; a
  hidden `Params` override in the run code.
- **Geometry:** candidate line shifted; baseline sign flipped.
- **Freeze:** 4096 RGB, correspondence or geometry modified after its freeze.
- **Evaluation:** the new 4096 Position read instead of the AB1c benchmark; paired error corrupted; a top-1
  transition count corrupted; the metric comparison corrupted; a hidden 256 reproduction failure.
- **Visual:** a different example pixel; a figure pixel altered; a truth badge altered; an unlabelled contrast stretch.
- **Process:** a second render; match twice; a denoising pass in the record; head motion; a controller action; a
  Position read during matching; a render-control record claiming ok over a failed gaze check.

Before the layout fix, the same checker code on the original figures also gave 41/41 and 44/44 (console kept in the
session scratchpad, not in the run).

**Preflight known answers 69/69** (`preflight/preflight-tests.json` `296e82e1…`):
- **The driver:** it passes exactly `SP.SPP` = 4096 (AST check).
- **Record mutations that must fail:** spp 256 / 2048 / 8192; denoising; adaptive; each seed; L = R; filter type /
  width; resolution; camera; gaze; calibration; device; Blender version; a denoising EXR channel; head motion; an
  unknown field; an unchanged RGB; a different blend.
- **Matching EXR-header cases.**
- **Calibration:** a byte-identical re-serialization passes and a changed calibration is detected.
- **Search-geometry identity:** passes against itself; fails on q_inf + 1e-12, k_last + 1, candidate_count + 1, one ulp
  of θ_L, and a negated line.
- **Matcher source and constants:** an altered mirror fails, and each changed constant or `FROZEN` parameter fails.
- **Benchmark:** an altered mirror fails.
- **Paired statistics:** a null pair gives ΔE ≡ 0 with diagonal transitions; ÷ 4 gives the known transition counts;
  disjoint sets give the intersection; the competing peak excludes oracle-adjacent peaks.

**Rehearsal** (`synthetic/rehearsal/rehearsal-report.json` `644bd6bf…`): the AB1a synthetic room (factory startup, never
Classroom), at the gaze-1 direction, at 256 and 4096 spp, through the same `acquire_pair`.
- **Positive control:** calibrations byte-identical, camera matrices identical, readback samples 256 / 4096, and the
  EXR `cycles.ViewLayer.samples` attribute 256 / 4096.
- **The section-7 comparison 256 → 4096 passes** with exactly the declared differences.
- **RGB changed:** max |Δ| ≈ 6e-4 linear on this emission-only scene.
- **Negative control:** comparing the rehearsal record against the accepted AB1c record **fails** on the scene identity
  (EXR channels / `Scene` / blend).

**Repository gates** at the report tree: layout 581/581, `verify_baseline` 9/9, `check_ab1d2.py` (read-only) 41/41,
`git diff --check` clean.

## Visuals (Visual Language 1)

`VIS`, regenerated from `e4c60eb` (`visuals-manifest.json` `3041febc5fb1727d385d4e4ad063477fc9100cad1859bd8a1d778a97836363be`):

| figure | truth badges | sha256 |
|---|---|---|
| `overview.png` | ORACLE INPUT, DERIVED, REFERENCE / EVALUATION | `232467c8403d78cba932a73e8ea5cb95787ea96de5ca0552b8b3d395d055bfa8` |
| `paired-cost-landscapes.png` | ORACLE INPUT, DERIVED, REFERENCE / EVALUATION | `3aee6c8c38a61044543f3d249dfaa60347eab03b88fc0ec1757b3667dfcb14dc` |
| `correspondence-improvement.png` | DERIVED, REFERENCE / EVALUATION | `bb23eba4fdcc912aa721caffb78b94ebd41d79827e59d420496a8b5fbb14c257` |
| `observation-comparison.png` | ORACLE INPUT, DERIVED, REFERENCE / EVALUATION | `ac3d57a5da8e50aebdc6b79f48db7d99c0897fabed3f4495929f30f16c9671e4` |
| `metric-comparison.png` | DERIVED, REFERENCE / EVALUATION | `6526b56e9409e878cecdd45ae33f4a82e80c181e9c5b4b3b553ad956a76974a1` |
| `confidence-change.png` | DERIVED, REFERENCE / EVALUATION | `00007554c9a08e53d7941f3aea24cd4c4255024812c877a32cf3d9b52ec54724` |

- **`overview.png`** has four panels.
  - **A** shows the 256 and 4096 left image per gaze, with the same `linear_to_u8` transform and no stretch. A 48 × 48
    zoom at the core centre carries one contrast stretch per gaze; its limits come from the 256 crop, it is applied
    unchanged to the 4096 crop, and a yellow "CONTRAST-STRETCHED" label is drawn on the figure.
  - **B** shows the paired cost landscape of the accepted AB1d median-error example of each gaze. All three become
    sharp, dominant peaks at ORACLE-ON-CURVE (|err| 93.13 → 0.16, 57.42 → 0.12, 129.21 → 0.13 px).
  - **C** shows |err| at 256 and 4096 on the same log scale, plus the 1-px transition map.
  - **D** shows the 3-D error maps and CDFs.
- **`paired-cost-landscapes.png`** shows all twelve accepted AB1d example pixels, read from the pinned AB1d visuals
  manifest in its order; none was chosen after seeing 4096. Not only improvements appear:
  - gaze 1 "smallest peak margin" stays on a long ZNCC ≈ 1 plateau (|err| 38.6 → 15.0 px, rank > 8 → > 8);
  - gaze 3 "smallest peak margin" worsens (104 → 358 px; its oracle patch becomes unscorable at 4096).
- **`observation-comparison.png`** shows the image pairs, the |ΔG| maps, the ΔG histograms, the texture and oracle-ZNCC
  distributions, and the PROXY values.
- **`correspondence-improvement.png`** shows the error and ΔE maps, the ΔE and error histograms, and the transitions.
- **`metric-comparison.png`** shows the 3-D error maps and CDFs with the 12 / 25 / 50 mm marks.
- **`confidence-change.png`** shows the section 17.5 strata.

Regenerate: `.venv/bin/python tools/active_bootstrap/ab1d2_run.py visualize --run RUN --visuals VIS`.

## Incidents and deviations

1. **Before the canonical render (implementation commit `b66d7f7`; no Classroom render had been made):**
   - **EXR attribute names.** The rehearsal showed that Cycles names its per-layer EXR attributes `cycles.<view
     layer>.*` (`ViewLayer` in the synthetic room, `interior` in Classroom). The contract names the Classroom
     attributes (`cycles.interior.samples`, timing). The comparison now reads the view layer from each header's channel
     list. For Classroom the classes are exactly as declared.
   - **The instance catalog** sits under `observations/evaluation_only/`. It is hashed in the observation freeze with
     the other evaluation-only files (hashed, never decoded), so the guarded evaluation never opens it.
   - **The Blender preflight** writes into the existing `preflight/` directory (the preflight-tests report is there
     first).
   - **The checker's EXR corruption** parses the attribute rather than searching for the value.
   - **The canonical Blender call** has the 30-minute budget as a subprocess timeout (section 25's stop). It was not
     reached: 106 s.
2. **Development data:**
   - Development used the accepted code, calibration-only data, synthetic records, the non-Classroom rehearsal and the
     no-render Classroom preflight.
   - It also used a **null pair**: the accepted AB1c 256-spp observation standing in for the 4096 one.
     - On it, the matcher, the search geometry and the 256 evaluation reproduced AB1d exactly, and the paired ΔE was 0.
     - The checker failed only the stand-in-specific checks.
     - 38 of 44 corruptions were caught through baseline-passing checks; the other six target exactly those
       stand-in-failing checks, and all are caught on the canonical run.
   - No 4096-spp Classroom image was rendered or inspected before the canonical render.
3. **Canonical run:** no incident. Every canonical stage ran once, in order, from the clean pushed `b66d7f7`. Nothing
   was rerendered. No matcher, threshold, setting, metric or benchmark was changed.
4. **After the run: figure layout (presentation only), commit `e4c60eb`.**
   - **The defects.** Three overlaps introduced by the last pre-run layout edit:
     - the overview panel-D footer caption and colour bar overlapped the new CDF plots;
     - the correspondence-improvement colour bars overlapped the gaze-3 label;
     - one observation-comparison histogram label overflowed its panel.
   - **The fix:** positions and label text only. No data, example pixel, display transform or statistic changed, and
     no canonical stage was rerun.
   - **Regeneration.** The figures were regenerated (`visualize` is deterministic and regenerable, contract section 26)
     and the checker with corruptions was rerun (41/41, 44/44). Three figures changed hash (overview,
     correspondence-improvement, observation-comparison); three are byte-identical.
5. **The contract's PROPOSED cost held:** render ≈ 17 s per eye, the stage 107 s; the checker with corruptions ≈ 4 min,
   in the batch class.
6. **Nothing in the contract was left unrun.**

## What is established

- **Rendering noise was a major limit of AB1d.** With nothing changed but 256 → 4096 spp, verified, the same frozen
  matcher improves broadly and coherently at all three gazes. The improvement shows in oracle score, oracle rank,
  angular and pixel-equivalent error, and metric error.
- **The true correspondence becomes far more photometrically distinctive.** Median oracle ZNCC rises 0.42 / 0.48 / 0.29 →
  0.85 / 0.92 / 0.78. The median oracle − best gap closes from −0.21 / −0.14 / −0.30 to −0.011 / +0.002 / −0.004.
- **The gain is broad where the 256-spp patches were weak.** Gains span the three lower texture quartiles; the oracle ZNCC
  of the lowest quartile rises 3.4–5 ×.
- **Ambiguity remains after substantially cleaner sampling.**
  - Gaze 1 keeps a 26 px median error, and 15–27 % of oracles stay worse than the 8th peak.
  - Distinct competing peaks also rise.
  - The highest-texture quartile at gaze 2 does not improve.
- **Metric usefulness stays limited at this range:** ≤ 12 mm for 4–15 %.
- **The experimental control held:**
  - settings differ only in spp;
  - the calibration is byte-identical;
  - the search geometry is bitwise identical;
  - the 256-spp evaluation reproduces AB1d exactly.

## What is NOT established

- A physical noise variance or noise model. The gray change and the PROXY values are descriptive; no second 4096 render
  was made.
- That 4096 spp is optimal or sufficient; no other spp was run.
- The effect of denoising, larger patches, colour, spatial aggregation, priors or learned features. None was run or
  proposed.
- That the small positive brightness shift (+0.1 u8) is a pure transfer-curve averaging effect. That is an untested
  interpretation.
- Anything about real cameras, other scenes, arbitrary gazes, head motion or the controller.
- That the 0.5 u8 texture threshold is appropriate at 4096 spp. Its few new exclusions are reported, not judged.

## Unresolved decisions (Luiz and Chat)

1. ~~Scientific, quantitative, code and visual review of AB1d2, including the outcome reading (all Outcome 1 indicators
   met, with an Outcome 2 residual).~~ **ACCEPTED** (see "Acceptance record").
2. ~~Whether the small positive gray shift (+0.08 to +0.17 u8 mean) needs any follow-up, or is accepted as consistent with
   sampling alone.~~

   **Decided:** recorded as a nonblocking caveat. Its exact explanation is not established, and no further experiment is
   launched for it.
3. ~~Which observation quality is the reference for later natural-correspondence experiments: 256 spp, 4096 spp, or
   something else.~~

   **Decided:** 4096 spp is the reference observation quality for subsequent synthetic Classroom
   natural-correspondence experiments. This is a project control choice (see "Acceptance record").
4. ~~What, if anything, addresses the residual along-line ambiguity. AB1d2 does not propose or build a matcher.~~

   **Decided:** natural stereo receives one additional bounded attempt, AB1d3 (one-shot SGBM viability). The roadmap
   commit that follows this acceptance records the decision.
5. ~~The shortest route after AB1d2, back toward AB1e and the active loop or one narrowly justified correspondence step,
   is Luiz and Chat's decision.~~

   **Decided:** after AB1d3, either SGBM is adopted as the current natural correspondence service, or natural-stereo
   development stops and the North Star proceeds with the validated PERFECT / oracle correspondence service. AB1e is no
   longer an obligatory prerequisite for returning to the North Star. The roadmap commit records the decision.

## Acceptance record

Luiz and Chat completed the scientific review, the quantitative review, an independent GitHub code review, the checker /
corruption review and the visual inspection of the two primary figures, and **accept AB1d2** as committed at `cb73e56`:

    ACTIVE_BOOTSTRAP1D2_4096SPP_OBSERVATION_QUALITY_ACCEPTED

- **Machine result accepted:**
  - `ACTIVE_BOOTSTRAP1D2_4096SPP_OBSERVATION_QUALITY_COMPLETE`;
  - `ACTIVE_BOOTSTRAP1D2_CHECKS_PASS` 41/41;
  - `ACTIVE_BOOTSTRAP1D2_MUTATIONS_CAUGHT` 44/44 from a passing baseline, with a clean unmodified-mirror null probe;
  - `AB1D2_PREFLIGHT_PASS` 69/69 and `AB1D2_REHEARSAL_PASS`.
- **Scientific conclusion accepted** (stated without strengthening):
  - At the three accepted safe-forward Classroom gazes, increasing Cycles sampling from 256 spp to 4096 spp — while
    holding scene, gaze, calibration, seeds, stereo geometry, matcher and evaluation fixed — substantially improves
    natural spherical epipolar correspondence.
  - Therefore the AB1d failure was strongly limited by observation quality.
  - However, large residual along-epipolar ambiguities remain. Cleaner observations alone do not make independent
    5 × 5 local-patch matching generally sufficient.
- **Accepted key measurements** (MEASURED in the sections above; unchanged; 256 → 4096 spp):

  | quantity | gaze 1 | gaze 2 | gaze 3 |
  |---|---|---|---|
  | within 1 pixel-equivalent | 9.2 % → 35.9 % | 16.8 % → 66.6 % | 9.2 % → 49.2 % |
  | median pixel-equivalent error | 93.1 → 26.4 px | 57.4 → 0.258 px | 129.2 → 1.748 px |
  | oracle top-1 | 9.9 % → 36.5 % | 17.7 % → 67.0 % | 9.8 % → 49.7 % |
  | median oracle ZNCC | 0.421 → 0.849 | 0.485 → 0.924 | 0.288 → 0.779 |
  | median 3-D error vs perfect | 4.161 → 3.283 m | 3.569 m → 63.8 mm | 4.031 → 0.482 m |
  | within the existing 12-mm persistent-map support | 0.9 % → 4.2 % | 2.9 % → 14.7 % | 1.3 % → 7.3 % |

- **Accepted interpretation:** Outcome 1 strongly supported, with the Outcome-2 residual. Observation quality was a
  MAJOR limitation, but residual local-patch ambiguity remains.
- **Not claimed:**
  - that 4096 spp is optimal;
  - that this measures a physical sensor-noise variance;
  - that local matching is now generally sufficient;
  - that real cameras behave like this experiment.
- **Figures accepted.** Luiz and Chat inspected the two primary figures:
  - `visuals/active-bootstrap/ab1d2-4096spp-observation-quality/overview.png`
    (`232467c8403d78cba932a73e8ea5cb95787ea96de5ca0552b8b3d395d055bfa8`);
  - `visuals/active-bootstrap/ab1d2-4096spp-observation-quality/paired-cost-landscapes.png`
    (`3aee6c8c38a61044543f3d249dfaa60347eab03b88fc0ec1757b3667dfcb14dc`).

  Accepted qualitative reading:
  - same scene / gaze / calibration / seeds / matcher; 256 → 4096 spp is the only intended change;
  - formerly catastrophic median-error examples move onto the true correspondence at 4096;
  - previously good examples remain good;
  - some flat / repetitive cost landscapes remain ambiguous;
  - one example even worsens / becomes unscorable;
  - the improvement is broad rather than cherry-picked;
  - metric error remains substantial in important regions.
- **4096 spp becomes the synthetic natural-stereo reference.** For subsequent SYNTHETIC Classroom
  natural-correspondence experiments, 4096 spp is the reference observation quality. This is a PROJECT CONTROL CHOICE.
  It does NOT assert optimality of 4096 spp, biological plausibility or equivalence to a real sensor. Reason: 256 spp has
  now been causally shown to contaminate evaluation of the correspondence mechanism substantially, and 4096 spp is
  inexpensive enough for the bounded synthetic experiments.
- **Small brightness shift: a nonblocking caveat.** The measured +0.08 to +0.17 u8 mean gray shift is recorded. Every
  load-bearing rendering setting was verified identical. Its exact explanation is NOT established; the nonlinear
  transfer explanation stays an untested interpretation, not a measured fact. No further experiment is launched for it.
- **AB1d2 is complete.** Its run is the accepted record. Later steps read its frozen 4096-spp observations; nothing is
  re-rendered.
- **This acceptance step** made no new observation, ran no render, did not rerun the matcher and did no scientific
  computation. It changed only this status record, and (in the next commit) `CLAUDE.md`, the Chat Handoff and the layout
  checker's handoff assertion. The AB1d2 code, data, measurements, figures and contract definitions are unchanged.
