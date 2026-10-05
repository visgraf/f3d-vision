# Active Bootstrap-1d — Safe-Forward Natural RGB Correspondence — report

**Marker.**

    ACTIVE_BOOTSTRAP1D_SAFE_FORWARD_NATURAL_CORRESPONDENCE_COMPLETE

**Status: REVIEW PENDING.** Luiz and Chat decide what the measured result means. No ACCEPTED marker is written, and
the branch is not merged.

> **Question.** In the favorable safe-forward regime established by AB1c, can a simple natural RGB matcher recover the
> right-eye spherical epipolar correspondence accurately enough to provide useful local metric measurements?

**Answer at the three accepted AB1c observations (MEASURED): no, not for most pixels.**

The frozen primitive matcher (direct raw epipolar search, 5 × 5 angular patch, ZNCC, one parabola) returns an estimate
for every left core pixel (coverage 100 %), but:
- it places the right correspondence within 1 pixel-equivalent of the AB1c perfect correspondence for only
  **9.2 % / 16.8 % / 9.2 %** of the evaluable pixels;
- the true location is the best photometric peak for **9.9 % / 17.7 % / 9.8 %**;
- the median error is **93 / 57 / 129 pixel-equivalents**, almost all toward nearer range;
- the median natural 3-D error is **4.2 / 3.6 / 4.0 m**; **0.9 % / 2.9 % / 1.3 %** of points lie within 12 mm of the
  perfect reconstruction.

The geometry is verified correct:
- averaged over all evaluable pixels, the frozen score peaks exactly at the oracle location and falls off symmetrically
  at ±0.5 and ±1 px;
- an independent re-implementation of the matcher agrees record for record;
- when the true peak does win, the refined estimate is accurate: median 0.19–0.24 px, 93–95 % within 1 px.

What fails is the photometric decision. At the true location the 5 × 5 gray ZNCC is low (median **0.42 / 0.48 / 0.29**),
while competing peaks along the long full-range segment score higher (median best **0.66 / 0.66 / 0.61**; median peak
margin ≈ 0.03).

This supports **Outcome 4 (photometric-model limited)**, with **Outcome 3 (ambiguity)** as the mechanism of the failures
(section "Scientific outcome").

This is a correspondence experiment on fixed, accepted geometry: one deliberately simple matcher, the same three AB1c
observations, no render, no head motion, no controller. AB1d does not propose a better matcher.

## Provenance

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (`origin` verified by `source` and check 01) |
| AB1c acceptance | `45b08ae81b09365c0744d204276038fe6046b4f9` (`ACTIVE_BOOTSTRAP1C_SAFE_FORWARD_PLANAR_SPHERICAL_ACCEPTED`) |
| base (post-AB1c roadmap, `main`) | `56840caab332bb203918c776acab20d9a6ef4c17` |
| branch | `active-bootstrap/ab1d-safe-forward-natural-correspondence`, from `56840ca`; isolated worktree |
| contract | `850724dd866352c7dd18b36fce5f4ee7400ed4cc` (before any implementation, synthetic matching or canonical matching) |
| implementation + contract section 33 (pre-canonical) | `3c7853ebbe4dcbeb4b773352d596eb2dc0ee71f5` |
| canonical run, figures, checks | all at `3c7853e`, clean and pushed |
| report | this commit |

Run: `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1d-safe-forward-natural-correspondence/` (`RUN`).
Visuals: `/home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1d-safe-forward-natural-correspondence/` (`VIS`).

## What ran (MEASURED, `process-log.jsonl`; each once, in order, from `3c7853e`, clean and pushed)

| # | command | result | seconds |
|---|---|---|---|
| 1 | `ab1d_run.py source` | 11 code pins, 11 AB1c observation pins, 14 benchmark pins (manifest only) | 0.08 |
| 2 | `ab1d_run.py synthetic` | `AB1D_SYNTHETIC_PASS` 24/24 | 25.1 |
| 3 | `ab1d_run.py match` | 3 × 65,536 left pixels; Position / Object Index / oracle / evaluation reads 0 | 57.0 |
| 4 | `ab1d_run.py freeze-correspondence` | 12 files hashed (`match/correspondence-freeze.json` `006c9116…`) | 0.08 |
| 5 | `ab1d_run.py spherical` | 65,536 / 65,536 triangulated per gaze; truth reads 0 | 1.6 |
| 6 | `ab1d_run.py freeze-geometry` | 15 files hashed (`freeze/geometry-freeze.json` `0c2d7b0a…`) | 0.10 |
| 7 | `ab1d_run.py evaluate` | post-freeze benchmark (`evaluation/evaluation-summary.json` `692f49d7…`) | 4.2 |
| 8 | `ab1d_run.py visualize` | 5 figures + manifest | 2.2 |
| 9 | `check_ab1d.py --corruptions --write-summary` | 38/38; corruptions 40/40; null probe clean | 178 (batch) |

No Blender process, render or rerender ran. No parameter sweep and no overnight task ran.

## Exact reuse of the AB1c observations (MEASURED)

The matcher read exactly these six files, in place in the AB1c run, under an allowlist guard (check 05). Their hashes
equal the contract pins and the accepted AB1c `manifest.json` entries (`21640f6a…`, unchanged; check 02):

| gaze | row, col | yaw, pitch (°) | `calibration.json` | `rgb-observation.npz` |
|---|---|---|---|---|
| gaze-1 | 191, 322 | −18.75, −5.75 | `ae56ef33…` | `d6e2a532…` |
| gaze-2 | 166, 373 | +6.75, +6.75 | `ab348665…` | `297c5bd6…` |
| gaze-3 | 190, 397 | +18.75, −5.25 | `085ff332…` | `5924f946…` |

- Every one of the 138 files in the AB1c run manifest, the AB1c visuals manifest and the AB1b freeze / visuals verify
  unchanged (check 32).
- The acquisition records list the same hashes and gazes (`source`).
- The AB1c renders are 256 spp, OPTIX, **no denoising**, independent seeds L 2111 / R 2112, box filter 1 px (AB1c
  `acquisition.json`).

## The frozen matcher (contract sections 6–13; unchanged after the canonical match started)

- **Photometry:** `fsg_stereo.linear_to_u8`, then G = 0.2126 R + 0.7152 G + 0.0722 B (float64).
- **Search locus:** for each left raw-core pixel the physical epipolar plane is n = b × d_L. The original right raw image
  is searched along l = K_R^-T R_hc_R^T n, from the infinite-range point q_inf in the direction of increasing θ_R.
  Samples are spaced 1 px over the whole physically admissible segment, with no depth interval.
- **Admissibility:** a candidate needs a finite ray, the same half-plane, θ_R > θ_L, a positive finite triangulation,
  and its complete right patch inside the raster.
- **Patch:** 5 × 5 samples at equal local angular spacing (θ ± i δ, φ ± j δ / sin θ, δ = atan(1/f)), bilinear.
- **Score:** ZNCC.
- **Texture:** MIN_LOCAL_STD_U8 = 0.5 (population std of the 25 samples) is the only threshold.
- **Decision:** best = max ZNCC (ties within 1e-12 go to the earliest candidate); top-8 distinct local peaks (≥ 3 px
  apart); one 3-point parabola at the best candidate, clipped to ±0.75 sample.
- **Not used:** no ZNCC, uniqueness or left-right threshold; no SGBM, learned model or planar rectification.

## Runtime per gaze (MEASURED, `match-summary.json`)

17.8 s / 18.4 s / 17.9 s (16 threads; records byte-identical to a 1-thread run, synthetic case 23).

## Full-core matcher counts (MEASURED)

| | gaze-1 | gaze-2 | gaze-3 |
|---|---|---|---|
| left core pixels | 65,536 | 65,536 | 65,536 |
| textured left (std ≥ 0.5 u8) | 65,536 | 65,536 | 65,536 |
| natural valid | 65,536 | 65,536 | 65,536 |
| reasons LOW_TEXTURE / NO_SEARCH_SUPPORT / NO_TEXTURED_CANDIDATE | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| admissible candidates min / median / max | 224 / 352 / 480 | 226 / 354 / 481 | 224 / 352 / 480 |
| refined | 65,032 | 64,795 | 65,235 |
| best ZNCC median | 0.664 | 0.662 | 0.614 |
| peak margin p05 / median / p95 | 0.0017 / 0.029 / 0.146 | 0.0004 / 0.026 / 0.147 | 0.0013 / 0.031 / 0.135 |
| pixels with 8 distinct peaks | 65,536 | 65,536 | 65,536 |
| left patch std median (u8) | 3.44 | 5.26 | 3.67 |

## PRIMARY: correspondence benchmark (MEASURED, post-freeze; AB1c perfect correspondence as benchmark)

| | gaze-1 | gaze-2 | gaze-3 |
|---|---|---|---|
| oracle correspondences | 53,750 | 63,293 | 65,493 |
| natural valid (full core) | 65,536 | 65,536 | 65,536 |
| evaluable (oracle ∧ natural) | 53,750 | 63,293 | 65,493 |
| coverage | 1.000 | 1.000 | 1.000 |
| natural valid, no oracle (not scored) | 11,786 | 2,243 | 43 |
| signed e_θ min / p05 / median / p95 / max (mrad) | −12.3 / −3.2 / +76.1 / +260.2 / +369.4 | −14.4 / −9.2 / +46.9 / +249.7 / +373.0 | −13.3 / −2.0 / +105.5 / +280.6 / +374.4 |
| \|e_θ\| median / p90 / p95 / p99 / max (mrad) | 76.1 / 222.4 / 260.2 / 310.1 / 369.4 | 46.9 / 211.7 / 249.7 / 310.9 / 373.0 | 105.5 / 247.4 / 280.6 / 332.8 / 374.4 |
| \|pixel-equivalent\| median / p90 / p95 / p99 / max | 93.1 / 271.9 / 318.9 / 381.5 / 456.9 | 57.4 / 258.9 / 305.6 / 382.5 / 460.6 | 129.2 / 303.4 / 344.1 / 410.8 / 463.0 |
| ≤ 0.10 / 0.25 / 0.50 / 1.00 px | 0.022 / 0.051 / 0.078 / 0.092 | 0.054 / 0.104 / 0.141 / 0.168 | 0.030 / 0.058 / 0.077 / 0.092 |
| focal approximation f·\|e_θ\| median (labelled) | 92.6 | 57.2 | 128.4 |
| line-coordinate difference \|s_est − s_oc\| median | 93.3 | 57.4 | 129.5 |

Notes on the primary table:
- The local scale dθ/ds is 817.0–817.6 µrad per line pixel (median).
- ORACLE-ON-CURVE lies on the matcher's line to ≤ 2.4e-13 px.
- Pooled over 182,536 evaluable pixels: ≤ 1 px 11.8 %, median 92.3 pixel-equivalents.
- The errors are almost all positive (larger θ_R, nearer range). The truth sits about 17 px from the infinite-range point,
  while the admissible segment runs about 224–481 px toward near range. The wrong peaks are spread along that segment.

## Cost-landscape benchmark (MEASURED, post-freeze REFERENCE / EVALUATION)

| | gaze-1 | gaze-2 | gaze-3 |
|---|---|---|---|
| ZNCC at ORACLE-ON-CURVE, median | 0.420 | 0.484 | 0.288 |
| best natural ZNCC, median | 0.661 | 0.661 | 0.614 |
| oracle − best, median | −0.210 | −0.140 | −0.295 |
| oracle at / above best (≥ best − 1e-9) | 0.091 | 0.129 | 0.069 |
| oracle in top 1 / 3 / 5 / 8 | 0.099 / 0.217 / 0.300 / 0.394 | 0.177 / 0.303 / 0.379 / 0.451 | 0.098 / 0.188 / 0.248 / 0.318 |
| oracle worse than top 8 | 0.606 | 0.549 | 0.682 |
| median peak margin | 0.029 | 0.026 | 0.031 |
| oracle unscorable / outside segment | 0 / 0 | 0 / 0 | 0 / 0 |
| ZNCC at s_oc + (−1, −0.5, 0, +0.5, +1) px, median | 0.213, 0.356, 0.420, 0.363, 0.211 | 0.326, 0.427, 0.484, 0.419, 0.331 | 0.134, 0.241, 0.288, 0.248, 0.142 |
| fraction with S(0) the maximum of the five | 0.373 | 0.340 | 0.323 |

The oracle-centred offsets peak at 0 and fall off symmetrically in every gaze. The frozen score is registered on the
true location; its peak is low.

**Representative landscapes** (`cost-landscapes.png`; deterministic post-freeze rules, contract section 25):
- **median-error examples:**
  - at gazes 1 and 3, noise-like curves with many peaks of 0.4–0.8; the best lies tens of pixels from the oracle, which
    is a minor peak;
  - at gaze 2, a plateau of near-equal peaks (≈ 0.8) along the board frame.
- **high-confidence low-error examples:** a single dominant peak (≈ 0.9–1.0) at the oracle, margins 0.32–0.46.
- **smallest-margin examples:**
  - at gazes 1 and 2, the left patch lies on an edge parallel to the epipolar line, so ZNCC ≈ 1 along a long stretch of
    the line (an aperture-type ambiguity);
  - at gaze 3, a noise-like curve.
- **large-error (p99) examples:** the true location is a minor peak near the start of the segment; the winner lies
  380–410 px away, toward near range.

## Confidence diagnostics (MEASURED, descriptive; `confidence-diagnostics.png`)

Error stratified by quartiles (Q1 → Q4) on the evaluable set. Each cell is median \|pixel-equivalent\|, then the fraction
within 1 px:

| signal | gaze-1 Q1 → Q4 | gaze-2 Q1 → Q4 | gaze-3 Q1 → Q4 |
|---|---|---|---|
| left patch texture (std u8) | 148, 0.03 → 46, 0.17 | 125, 0.06 → 12.5, 0.28 | 128, 0.02 → 101, 0.22 |
| best ZNCC | 144, 0.03 → 58, 0.15 | 126, 0.06 → 13.4, 0.24 | 136, 0.02 → 96, 0.22 |
| peak margin | 90, 0.07 → 91, 0.13 | 44, 0.06 → 30, 0.33 | 129, 0.06 → 113, 0.15 |

- Texture and best ZNCC are the strongest descriptive signals; peak margin is weaker on its own.
- The pixels in the top quartile of **both** texture and margin (scratch cross-tabulation; post-run, labelled) are
  1,951 / 2,428 / 2,922 pixels, about 4 % per gaze:
  - median error 5.7 / 0.13 / 0.51 px;
  - within 1 px 0.36 / 0.83 / 0.52;
  - oracle at / above best 0.34 / 0.75 / 0.35.

  Gaze 2's high-contrast board structure gives a small, fairly reliable subset; gazes 1 and 3 do not.
- Nothing is thresholded in AB1d.

## Secondary: metric consequence (MEASURED, post-freeze)

Natural spherical reconstruction (accepted AB1b geometry on the frozen natural product) on the evaluable pixels:

| | gaze-1 | gaze-2 | gaze-3 |
|---|---|---|---|
| vs AB1c perfect spherical: 3-D median / p90 / p95 / p99 / max | 4.16 / 4.60 / 4.65 / 31.7 / 71.5 m | 3.57 / 4.15 / 7.71 / 42.3 / 73.0 m | 4.03 / 4.43 / 4.51 / 14.9 / 71.0 m |
| signed radial p05 / median / p95 | −4.61 / −4.10 / +1.63 m | −4.12 / −3.32 / +7.71 m | −4.46 / −3.99 / +0.80 m |
| relative range error, median | 0.878 | 0.824 | 0.892 |
| within 12 / 25 / 50 mm (vs perfect) | 0.009 / 0.018 / 0.034 | 0.029 / 0.055 / 0.093 | 0.013 / 0.026 / 0.047 |
| vs Blender Position: 3-D median / p95 | 4.16 / 4.65 m | 3.57 / 7.71 m | 4.03 / 4.51 m |
| vs Position within 12 mm | 0.009 | 0.029 | 0.013 |
| natural κ median (mostly false near peaks) | 11.3 | 16.3 | 8.5 |

Notes on the metric table:
- Vs Position equals vs perfect at this scale, because the AB1c perfect reconstruction is within ≈ 0.14 mm of Position.
- The 12 mm fraction is descriptive (the persistent-map support radius), not a threshold.
- The checker cross-checks the Position reference against AB1c `P_truth` to 0.0 m.

## Post-run supporting diagnostic (scratch; REFERENCE / EVALUATION; not a frozen claim)

The question was why the true location scores low. The diagnostic was run after all freezes and is labelled here as
supporting evidence only.
- **Noise level.** At the oracle correspondences, the left-minus-right gray difference has a robust std of
  2.9 / 4.5 / 4.1 u8: about **2.0 / 3.2 / 2.9 u8 per eye** if it were noise only. A left high-pass noise proxy gives
  2.8 / 4.4 / 3.7 u8.
- **Signal vs noise.** The median 5 × 5 patch std is 3.3 / 5.2 / 3.7 u8, so much of the patch content is comparable to
  independent L / R render noise. The renders are 256 spp, undenoised, with different seeds.
- **Texture dependence.** By texture quartile, the oracle ZNCC rises from 0.12–0.23 (Q1) to 0.83–0.97 (Q4), roughly
  following a signal-plus-independent-noise prediction (an upper bound in the middle quartiles).
- **Ambiguity remains at high texture.** Even in Q4, where the true location correlates well, competing peaks along the
  segment still win for 71–82 % of pixels (oracle top-1 0.18 / 0.29 / 0.23).
- **The texture threshold sits below the noise.** The accepted texture threshold (0.5 u8) is far below this noise level,
  so it does not mark noise-dominated patches. That is why coverage is 100 %.

This is consistent with a photometric limitation caused by render noise. It is not separately established: no
noise-free or denoised observation was rendered, and none should be in AB1d.

## Scientific outcome (contract section 23)

My reading, for Luiz and Chat to judge: **Outcome 4 (PHOTOMETRIC MODEL LIMITED), with Outcome 3 (AMBIGUITY LIMITED) as
its mechanism.**
- The true location is usually **not** the favored photometric peak: at / above best only 7–13 %, top-1 10–18 %, worse
  than top 8 for 55–68 %.
- The score at the truth is low (median 0.29–0.48) even though it is correctly registered (symmetric peak at offset 0).
- Distinct peaks are near-equal (median margin 0.026–0.031), and the false winners are spread along the full-range
  segment. Edge structure parallel to the epipolar line also produces long near-1 plateaus (aperture-type
  ambiguity).
- **Outcome 1 does not occur:** ≤ 1 px for 9–17 %, metric error metres, ≤ 12 mm for 0.9–2.9 %.
- **Outcome 2 does not occur:** when the true peak wins, refinement is good (median 0.19–0.24 px; 93–95 % ≤ 1 px).
  Search and refinement are not the limitation.
- **Outcome 5 does not occur as defined:** coverage is 100 %. That coverage is vacuous, though, because the accepted
  texture threshold lies below the measured noise.
- The pattern is spatially uneven: gaze 2's high-contrast board and frame structure behaves better than the dark wood
  panelling and blackboard interiors of gazes 1 and 3.

## Checks (MEASURED)

`tools/active_bootstrap/check_ab1d.py` at `3c7853e`: **38/38** (`ACTIVE_BOOTSTRAP1D_CHECKS_PASS`; `check-summary.json`
`2ad6d3c6…`).

The checker keeps its own literal constants and an **independent re-implementation of the matcher**:
- its own photometric conversion and pinhole rays;
- θ by arccos and φ by complex argument;
- the epipolar line from a fundamental matrix;
- orientation by finite difference;
- its own projection and bilinear sampling, and moments-form ZNCC;
- per-pixel Python decision logic for ties, peaks and the parabola.

It compares the stored records on 2,048 left pixels per gaze (core index % 32 == 7) plus the figure examples: **zero
mismatches** in every field. All-row invariants cover the line, q_inf and orientation, the locus, spacing, peaks,
refinement bound, validity semantics and the positive-intersection filter.

It also recomputes:
- the natural geometry (law-of-sines triangulation);
- θ errors, local scales, ORACLE-ON-CURVE, ranks and the subset oracle / offset scores;
- metric errors and the Position cross-check against AB1c `P_truth`;
- the confidence strata and summaries;
- the figures, byte for byte, and the example rules.

It audits:
- the guard records (match: exactly calibration + RGB; spherical: calibration + frozen product; no SGBM tripwire call;
  ordered evaluation events);
- both freezes, the run order and the AB1c / AB1b products;
- the AST of the sources: no SGBM, planar matcher, learned model, controller or head motion, and no truth identifier
  in the matcher;
- the changed tracked files.

**Corruption / mutation suite: 40/40 caught** from a passing baseline, after an unmodified-mirror **null probe** passed
all 38 checks (`ACTIVE_BOOTSTRAP1D_MUTATIONS_CAUGHT`). Each corruption names the checks that must catch it, and counts
only if one of those fails (contract section 33). The families:
- **source / firewall:** a changed observation; a Position read; an AB1c oracle read; identity added to the product;
- **epipolar geometry:** flipped baseline (negative parallax); θ from −X; φ sign; altered right-camera transform; line
  offset 0.7 px;
- **patch / photometry:** 7 × 7; 1.5 δ spacing; raw linear values; texture threshold; ZNCC mean subtraction; ZNCC
  normalisation;
- **search:** 0.5 px spacing; hidden depth truncation; tie rule; 5 px peak separation; TOP_K 4;
- **refinement:** disabled; quadratic sign; bound exceeded;
- **freeze:** product after freeze; geometry after freeze; truth before the freeze;
- **evaluation:** θ error; pixel scale; oracle rank; a metric statistic;
- **visual:** a pixel; a truth badge;
- **process:** SGBM injected; a learned matcher; a head-motion command; a controller command in the log; a step run
  twice; a failed synthetic case; a depth field in the record; an undeclared evaluation read.

Other gates:
- layout 574/574;
- `scripts/verify_baseline.sh` 9/9;
- `git diff --check` clean.

**Synthetic known answers 24/24** (`synthetic/synthetic-report.json` `df45b56d…`; analytic scenes only, contract
sections 24 and 33). They show:
- exact line geometry (≤ 1e-9 px; fundamental-matrix agreement);
- candidates on the epipolar plane (≤ 1e-12 rad);
- analytic-sampler exactness (continuous score maximum at the truth, ZNCC 0.99999);
- integer and sub-pixel bins within the revised tolerances;
- affine photometric invariance; LOW_TEXTURE on a flat block; exposed repeated-texture ambiguity; boundary
  no-refinement;
- known-answer failures for a wrong plane sign, a wrong right transform and a wrong baseline axis;
- detection of altered patch, spacing, threshold, separation and bound by the checker's independent recomputation;
- the guard refusing Position / oracle reads inside the real match stage;
- product schema rejection; AB1b geometry consuming the natural product unchanged; the photometric conversion; ZNCC,
  ties, peaks and parabola units;
- thread invariance; end-to-end through linear RGB.

## Visuals (Visual Language 1)

Persistent, under `VIS`. Drawn at `3c7853e`; check 29 regenerates them byte-identically.

Regenerate:

    .venv/bin/python tools/active_bootstrap/ab1d_run.py visualize --run RUN --visuals VIS

| figure | badges | sha256 |
|---|---|---|
| `overview.png` | ORACLE INPUT, DERIVED, REFERENCE / EVALUATION | `0d7217b5c7c925b0e4595cd0a72e04ed6b225487f4369cadbacb0f583bc85654` |
| `correspondence-error.png` | DERIVED, REFERENCE / EVALUATION | `dbe175126d6eddfbbf24e2847c2d129e5de8fbc7b088f39fb2af46022f86ac41` |
| `cost-landscapes.png` | ORACLE INPUT, DERIVED, REFERENCE / EVALUATION | `0669aa19c7899ea9de45943b42101f1b9d4ef9a26d9468be5343959549cae862` |
| `natural-reconstruction.png` | DERIVED, REFERENCE / EVALUATION | `4cc387321d3c43fccb1626e66914f569cdbb707e7ed213e0815b7d633d79aaa0` |
| `confidence-diagnostics.png` | DERIVED, REFERENCE / EVALUATION | `6f35f1ea02be6714e49e9fc878813232c1c749aed424d0be5180261a69715fee` |
| `visuals-manifest.json` | (sources, examples, badges) | `c7391c7b3516afed4dc728381f8ffaf8fa4fac4697661ff3aa2781c5ac397ecf` |

`overview.png` answers the contract's question in four regions:
- **A:** the same three saved pairs;
- **B:** direct epipolar matching at the median-error example of each gaze (left patch, search locus, natural peaks,
  and ORACLE-ON-CURVE as a dashed post-freeze reference);
- **C:** full-core classes, \|error\| and margin maps;
- **D:** natural vs perfect clouds and error maps.

Two presentation notes (no figure was changed after the canonical run):
- the 5 × 5 patch tiles are contrast-stretched per tile for display, which the caption does not say;
- region D's "natural κ median (conditioning retained)" is the κ of the natural points, which are mostly false near
  peaks here.

Run manifest `manifest.json` `3f6a837d…`.

## Incidents and deviations

1. **Contract section 33 (pre-canonical clarification).**
   - **Diagnosis.** The synthetic diagnosis showed the frozen chain is exact (analytic sampling). The declared
     known-answer tolerances were too tight for the parabola's inherent ≈ 0.05 px bias, and the declared 8–32 px
     synthetic texture was ambiguous for a 5 × 5 patch.
   - **Revisions.**
     - texture 3–8 px;
     - revised software tolerances, with a recorded half-sample phase penalty (0.50 bin correct-discrete 0.886);
     - a φ-ramp scene for the φ-sign case;
     - exact-integer comparison only for u8 values;
     - corruption attribution by expected checks.
   - **Unchanged.** No matcher constant, metric or outcome rule changed. Please review section 33.
2. **Implementation defects found on development data and fixed before the implementation commit:**
   - **Read classifier.** The truth-read classifier matched the substring "planar" in the AB1c run's own directory name,
     so every calibration read would have counted as an evaluation read. It stopped the spherical stage in the dev run;
     replaced by exact AB1c sub-directory prefixes. Check 05 independently flagged the stale dev record.
   - **Naming crash.** A constant-name typo (`LANDSCAPE_OFFSETS`) crashed the evaluation.
   - **Synthetic report crashes.** Two synthetic helper calls crashed the report.
   - **Corruption suite:**
     - a hard-coded gaze name;
     - a stale cache after writing a corruption (a missed texture-threshold catch);
     - a right-camera "transpose" that is a no-op for a mathematically symmetric rotation at the dev forward gaze,
       replaced by using the left rotation.
   - **Layout.** Figure layout fixes.
3. **Development data.**
   - The evaluation, figures and checker were developed on the **AB1c Blender-rehearsal synthetic room** (procedural
     texture, 64 spp), not on Classroom. There the frozen matcher reached median ≈ 0.08 px and top-1 ≥ 99.6 %.
   - This is a dev-only observation, not a result. It is consistent with the matcher working when patch texture far
     exceeds the noise.
   - No Classroom natural correspondence was computed or inspected before the canonical `match`.
4. **Canonical run:** no incident. Every step ran once, in order, from the clean pushed `3c7853e`. No fix was made
   after the canonical match started.
5. **Checker console:** written to the session scratchpad, not into the run.
6. **Nothing in the contract was left unrun.**

## What is established

- **The negative result.** At the three accepted safe-forward Classroom observations (256 spp, undenoised), the frozen
  primitive natural matcher fails for most pixels:
  - direct raw spherical epipolar search with a 5 × 5 angular ZNCC and one parabola, over the full admissible range;
  - ≤ 1 pixel-equivalent for 9–17 %; true peak first for 10–18 %;
  - median natural metric error 3.6–4.2 m; ≤ 12 mm for 0.9–2.9 %.
- **The failure is correspondence, not geometry.**
  - The score is registered on the true location (symmetric peak at offset 0).
  - An independent re-implementation agrees exactly.
  - Synthetic and analytic known answers are exact.
  - When the true peak wins, sub-pixel accuracy is about 0.2 px.
- **The measured failure mode is photometric with ambiguity.** The true location scores low (median ZNCC 0.29–0.48)
  while many near-equal competing peaks score higher along the full-range segment. Error falls steeply with patch
  texture.
- **The texture threshold does not see noise.** The accepted texture threshold (0.5 u8) does not discriminate
  noise-dominated patches in these observations.

## What is NOT established

- That the render noise **causes** the photometric failure. The noise estimate is a labelled post-run diagnostic, and
  no denoised or higher-sample observation was made.
- Anything about other matchers (larger patches, colour, regularisation, priors, learned features). None was run or
  proposed.
- Anything about head motion, recentering or the controller (AB1e; not started).
- Generality beyond these three gazes, Classroom, this instrument and its render settings.
- Whether the small high-texture, high-margin subset (gaze 2) is useful to the active loop. This is descriptive only.
- The meaning of the natural κ, which here mostly reflects false near peaks.

## Unresolved decisions (Luiz and Chat)

1. Scientific, quantitative, code and visual review of AB1d, including the outcome reading (4 with 3).
2. Review of contract section 33 (the pre-canonical synthetic clarification).
3. Whether the AB1c observation noise (256 spp, no denoising, independent L / R seeds; about 2–3 u8 per eye by the
   labelled diagnostic) is the intended sensor model for natural correspondence experiments.
4. How texture adequacy should relate to sensor noise. The accepted MIN_LOCAL_STD_U8 = 0.5 is below the measured noise
   here. This is recorded, not changed.
5. The shortest route after AB1d — back toward the active loop or one narrowly justified correspondence improvement —
   is Luiz and Chat's decision. This report does not propose a matcher.
