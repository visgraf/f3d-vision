# Active Bootstrap-1a — First Natural Stereo Look — report

**Marker.**

    ACTIVE_BOOTSTRAP1A_FIRST_NATURAL_STEREO_LOOK_COMPLETE

**Status: REVIEW PENDING.** Luiz and Chat decide what the measured result means. No ACCEPTED marker is written, and
the branch is not merged.

> **Question.** Can the eye, starting from the FIRST frozen RGB candidate gaze and the fixed binocular instrument
> alone, obtain useful local metric geometry from binocular RGB without using depth, Blender identity or scene
> segmentation?

**Answer at gaze #1, with the accepted instrument (MEASURED): no metric geometry was obtained.**
- Natural RGB-only stereo: **0 / 65,536** valid core pixels.
- Post-freeze reference: the accepted local oracle also has **0** valid pixels. The whole rectified core is
  **no geometry**: it looks out through the window into the black, empty world, about 14° from the fixation and about
  1° from the baseline axis.
- The calibration-only pre-look geometry, recorded before the acquisition, had predicted this sampling location.
- The fixated window region itself is in the raw images, but the accepted rectification's core does not sample it.

Contract: `docs/active-bootstrap/ab1a-first-natural-stereo-look-contract.md`. Section 22 is the pre-run synthetic
clarification; section 23 is the post-run EXR-pass clarification, authorized by Luiz and Chat. MEASURED means produced
by the runs below; CALIBRATION-ONLY means computed from the calibration code with no scene data.

## Branch and commits

| item | value |
|---|---|
| accepted `main` after the NB1c closure | `509c341ff60994ff0bf726b081be1f5c5c107b73` *Launch active natural stereo bootstrap*; parent `6b0ba68` *Accept NB1c RGB candidate gaze*; `origin/main` fast-forwarded `7d1c1b9 → 509c341` (plain push, no merge commit) |
| branch | `active-bootstrap/ab1a-first-natural-stereo-look`, from `509c341`; isolated worktree |
| contract | `934c0f9` *Contract AB1a first natural stereo look* |
| implementation (frozen before any Classroom acquisition) | `a3caaef` *Implement AB1a natural stereo look* (with contract section 22) |
| canonical run | `synthetic`, `rehearse`, `prelook`, `preflight`, `acquire`, `measure`, `freeze`, `evaluate`, `visualize`: all at `a3caaef`, clean and pushed |
| presentation fix (figures only, after the freeze) | `b17259a` *Fix AB1a figure presentation for empty results*; `visualize` re-run there |
| checker repairs (after the run) | `8c9d685` *Repair AB1a checker: data-path false positive, pass-set clause split* |
| post-run clarification (Luiz and Chat) | `49869ae` *Clarify AB1a inherited EXR passes; repair check 42* (contract section 23); final checks and corruptions at `49869ae` |
| report | this commit |

## What ran

Run: `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1a-first-natural-stereo-look/` (`RUN`).
Visuals: `/home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1a-first-natural-stereo-look/` (`VIS`).

| # | command (`tools/active_bootstrap/ab1a_run.py`) | commit | status | seconds (MEASURED, process log) |
|---|---|---|---|---|
| 1 | `synthetic` | `a3caaef` | ok: `AB1A_SYNTHETIC_PASS` 12/12 | 4.42 |
| 2 | `rehearse` (synthetic factory-startup room only) | `a3caaef` | ok: `AB1A_REHEARSAL_PASS` | 3.39 |
| 3 | `prelook` | `a3caaef` | ok | 0.03 |
| 4 | `preflight` (Classroom loaded; **no render**) | `a3caaef` | ok | 0.57 |
| 5 | `acquire`: **the one canonical acquisition** | `a3caaef` | ok | 3.46 (Blender 3.40) |
| 6 | `measure` | `a3caaef` | ok | 0.19 |
| 7 | `freeze` | `a3caaef` | ok | 0.02 |
| 8 | `evaluate` | `a3caaef` | ok | 0.19 |
| 9 | `visualize` | `a3caaef`, then `b17259a` | ok, ok | 0.75, 0.76 |
| 10 | `check_ab1a.py --run RUN --visuals VIS --corruptions --write-summary` | `49869ae` | 42/42; corruptions 51/51 | 73 (batch) |

`process-log.jsonl` holds exactly these ten `ab1a_run.py` entries:
- one `acquire`;
- no other gaze;
- no controller, FSG6f or surface-map command.

## PRE-LOOK GEOMETRY (CALIBRATION-ONLY; recorded before the acquisition)

**Action.** Frozen NB1c RGB gaze #1, consumed verbatim:
- rank 1, row 164, col 513;
- yaw **+76.75°**, pitch **+7.75°**, equal to the cell-centre convention.

| pinned source | sha256 |
|---|---|
| NB1c `selection/rgb-gaze-freeze.json` | `87a3bab01f55051316ac1eb45b48f394211f4c7a3a317fd0e61c0e52c36f9b37` (its seven files verify) |
| NB1c `selection/candidate-gazes.json` | `8041b954f7b63d97f060a41aaca5db1ec6e0c2295381523026e98d11f8a5b621` (equal in the accepted NB1c manifest and the freeze) |
| NB1c `manifest.json` | `524f8fad71ccb8fd9359fa3221f4de6be3af40be8f3e5fa7cddeb482acedd87e` |
| head pose (`EYE`; `previews/controller-01-full/bootstrap/seeds.json`) | `6ef833196de2462370ba4b2a2a8eed3fbde7f0a61e5aa6cbaf95f66947134c4f` |

**Instrument** (unchanged; `fsg_geometry.py` `ae3779bc…` and `fsg_stereo.py` `faebf0f1…` pinned):
- profile `full`; `CORE_FOV_DEG` 12.0°;
- core 256 × 256 (raw 640 × 640, 29.44°; focal 1217.84 px);
- IPD 0.063 m; vergence 2.10 m; tangent frame **`baseline_projected`**;
- `z_rect` search [0.75, 4.5] m;
- OPTIX, 256 spp, fixed head.

Calibration identity: `acquisition/calibration.json` `9960c86e…`, byte-identical to the planned
`prelook/planned-calibration.json`.

**Stereo leverage** (`prelook/prelook-geometry.json` `e65a85b4…`):

| quantity | value |
|---|---|
| `b · d` | 0.9644883124 (the gaze is 15.315° from the baseline) |
| **L** = sqrt(1 − (b·d)²) | **0.2641255292** |
| **B⊥** = IPD · L | **0.016639908 m (16.64 mm)**; a forward look has 63 mm |

**What the accepted rectification does at this gaze** (calibration only; left eye, the right agrees):

| quantity | value |
|---|---|
| rectification rotation (L / R) | 74.909° / 74.455° |
| rectified principal point `c_x` | −65,992.36 px (raster width 640) |
| disparity search | 112 levels; `z_rect` ≥ 0.75 m ⇔ disparity ≤ 102.3 px |
| raw source of the whole 256 × 256 rectified core | L x 623.98–624.07, y 317.08–321.92; R x 634.25–634.35, y 317.08–321.92 (about 0.09 × 4.8 raw px) |
| rectified-core pixels sourced from the nominal 12° raw core | **0 / 65,536** |
| direction of the rectified core centre | **14.263° from the gaze, 1.052° from the baseline axis** |
| range the `z_rect` window admits at the core centre | 40.84–245.07 m |

These diagnostics vetoed nothing, moved nothing and tuned nothing. The contract (section 21) recorded the PROPOSED
expectation "little or no usable metric geometry" before the run.

## RGB-ONLY ACQUISITION / MEASUREMENT (MEASURED)

**Preflight** (no render):
- the Classroom `EYE` pose equals the accepted head pose exactly (|Δ| = 0);
- the Blender-built calibration equals the planned calibration exactly (|Δ| = 0);
- OPTIX; lens 68.503 mm (= 1217.84 · 36 / 640); 256 spp; BOX filter 1.0; no adaptive sampling, no denoising.

**Acquisition** (`acquisition/acquisition.json` `ba316b11…`, created 2026-10-03T21:08:35Z):
- one L/R pair at (+76.75°, +7.75°);
- OPTIX, 256 spp, seeds **L 2111, R 2112** (declared, no object identity);
- render time **L 1.357 s, R 0.855 s**; 209,715,200 primary camera samples;
- the RGB observation `acquisition/rgb-observation.npz` holds exactly `rgb_L`, `rgb_R`: float32 linear,
  640 × 640 × 3, `eb84831aee9676e011651821197812c81e7d51d76ab2cecfea609d3a8dd4268d`;
- the RGB equals the EXR Combined channels (check 40);
- truth went only to `evaluation_only/`: `raw_L.exr`, `raw_R.exr`, `reference-observation.npz` (`instance_*`,
  `position_w_*`), `instance-catalog.json` (equal to the accepted 234-object catalog).

**Natural measurement** (`measurement/stereo-result.npz` `f6207e0e…`, `stereo-summary.json` `166955c0…`):
- the guard's data reads are exactly `calibration.json` and `rgb-observation.npz`;
- writes went only to `measurement/`;
- truth-firewall violations: **0**.

| quantity | value |
|---|---|
| natural-valid core pixels | **0 / 65,536 (fraction 0.0)** |
| SGBM-valid core pixels | 65,536 (every one at disparity **0.0**, refined 0.0) |
| validity terms passing alone (of 65,536) | SGBM-left 65,536; right-valid **0**; support 65,536; inside-raster 65,536; LR **0** (residual 112 px everywhere); texture **0** (5 × 5 gray std exactly 0 everywhere); finite XYZ **0**; `z_rect` **0**; ROI 65,536 |
| sequential attrition | 65,536 after SGBM-left → **0** after right-valid |
| disparity / range / `z_rect` on valid pixels | none (no valid pixel) |
| measured point cloud | **0 points**; no extent |
| runtime | 0.134 s |

**Why** (a descriptive scratch inspection of the frozen DERIVED arrays and the inference-visible RGB, after the
freeze and before any truth was opened):
- Both rectified cores are exactly black: linear RGB 0, u8 gray 0 everywhere.
- The raw sliver they resample (L x ≈ 624, y 317–322; R x ≈ 634) is linear 0 in the raw images.
- With zero texture, SGBM returns disparity 0, so the reprojection is at infinity and every downstream gate fails.
- The fixated raw 12° core itself is bright and textured, a window with blinds. Its mean linear RGB is
  (0.514, 0.457, 0.484), and 5.7 % of raw L pixels exceed linear 1.0.
- The accepted rectified core never samples it.

## MEASUREMENT FREEZE

`measurement/measurement-freeze.json` `53dc5ff2985cfda4ed0ef0ed13f10be12a33e1c7693942dcf9101a2d1448243e`
(2026-10-03T21:09:02Z, at `a3caaef`) hashes:
- the action manifest, the pre-look record and the planned calibration;
- the calibration, the RGB observation and the acquisition record;
- the stereo result, the stereo summary and the opened-files record;
- the matcher configuration (`f3c683e0…`);
- the matcher code (`ab1a_stereo.py`, `ab1a_spec.py`, `fsg_stereo.py`, `fsg_geometry.py`, `nb1a_guard.py`).

Truth-firewall violations: 0. The freeze verifies after evaluation and now (check 32). No stereo file changed after
the freeze.

## POST-FREEZE REFERENCE EVALUATION (MEASURED; descriptive)

`evaluate` ran under the guard. Its ordered events are:

    measurement_freeze_verified -> reference_access_begins -> evaluation_only/reference-observation.npz -> instance-catalog

There were 0 violations, and the frozen measurement was re-verified afterwards. The reference is the accepted
`classroom_oracle1_matcher.compute` (unchanged) at the same calibration and gaze.

| quantity | value |
|---|---|
| natural valid / reference valid | **0 / 0** |
| overlap / natural-only / reference-only | **0 / 0 / 0** |
| 3-D error, radial error (median, p90, p95, p99, max) | **undefined** (no overlap pixel) |
| fractions within 1 / 2.5 / 5 cm | **undefined** |
| natural vs left first-hit Position (secondary) | undefined (no natural-valid pixel) |
| natural-valid composition | catalog 0, O_0 0, no geometry 0; distinct instances touched 0 |
| **rectified core in reference terms (left)** | catalog 0, O_0 0, **no geometry 65,536 / 65,536** |
| per-instance errors (≥ 50 overlap px) | none |
| camera model (Blender Position projected through the calibration) | within ±0.5 px everywhere: maximum residual **0.00084 px (L) / 0.00092 px (R)** over 252,644 / 252,934 raw geometry pixels; 0 behind the camera |

Files:
- `evaluation/evaluation-summary.json` `5ed40636…`;
- `evaluation/oracle-reference.npz` `91cddb24…`;
- `evaluation/evaluation-opened-files.json` `a8a19903…`.

Evaluation-only:
- `reference-observation.npz` `f23a7a53…`;
- `raw_L.exr` `7ee178ac…`;
- `raw_R.exr` `5e63f344…`.

The natural and the reference results agree: there is no measurable geometry in the rectified core. The calibration
matches the rendered geometry to about 0.001 px at this gaze, so the empty result is not a camera-model error.

## Visual products (Visual Language 1)

Persistent, under `VIS`. Drawn at `b17259a` (the presentation fix); check 35 regenerates them byte-identically.

| file | truth badges | sha256 |
|---|---|---|
| `overview.png` | ORACLE INPUT, DERIVED, REFERENCE / EVALUATION | `b8f3452a8efd8aae65150bbe3eda0cfb1f0669886dd7c12c5f8ad449731cb62c` |
| `binocular-pair.png` | ORACLE INPUT, DERIVED | `e2504a774a378d525629418197a3b77735e545d44bc13aa73edc2b51e6c0f0a6` |
| `tangent-geometry.png` | DERIVED | `adbb4250744abb5c4fccdf3a95b2feb5e47a512378c19be17c29877dfbeb982a` |
| `natural-disparity.png` | DERIVED | `54bebc40e6f48de3c378bf86c14f1b086e23a98eafd3b46454159b1f56abd9c4` |
| `natural-validity.png` | DERIVED | `93ee6d9b7f23cc82eda3ddac1cde4478c7f885b3cfc37651f2ec4d7786aba6f8` |
| `natural-range.png` | DERIVED | `f73540e71d0ebaf5cdadadd06dee0a9ae83d0a34a4d850197961fe6477054566` |
| `measured-point-cloud.png` | DERIVED | `b3d759b93d86628a8db38fd3e73d62c095e621a0a2ee60d056a1aff091836d34` |
| `reference-error.png` | REFERENCE / EVALUATION, DERIVED | `477c46181971c3dec0b25d91aef263a83038b040f8cf47f8a478f271cd692941` |
| `reference-composition.png` | REFERENCE / EVALUATION | `cee13883c99051ba6938d2b79138695d3eda665f1c06fc3afb0ac127af987465` |
| `error-distribution.png` | — | omitted, as declared: no overlap and no natural-valid pixel with geometry |
| `visuals-manifest.json` | — | `d38bfdc2b9158739cc635f3cbc5ba4a764e6234c5397ba50ca99780987b22da0` |

The overview has four regions:
- **A**, frozen action / sensor geometry: the coarse spherical RGB with gaze #1, the rectified-core-centre direction
  and the baseline, a magnified inset, and yaw / pitch, frame, IPD, L and B⊥;
- **B**, natural sensor data: raw L / R tangent RGB with calibration markers, and the black rectified L / R cores;
- **C**, derived measurement: disparity, valid mask, range and point cloud, each stated as empty;
- **D**, reference / evaluation: the core's reference composition (no geometry everywhere) and the statistics.

The action source is labelled "frozen NB1c RGB gaze #1".

Minor presentation issue, not repaired: `binocular-pair.png` has empty space below its content.

Regenerate the figures with:

    .venv/bin/python tools/active_bootstrap/ab1a_run.py visualize --run RUN --visuals VIS

## Machine evidence

Under `RUN`:

| file | sha256 |
|---|---|
| `source/nb1c-action-manifest.json` | `9fc65ef7…` |
| `prelook/planned-calibration.json`, `acquisition/calibration.json` | `9960c86e…` |
| `prelook/prelook-geometry.json` | `e65a85b4…` |
| `preflight/preflight.json` | `86f56c98…` |
| `measurement/measurement-opened-files.json` | `1dab5d08…` |
| `evaluation_only/instance-catalog.json` | `3924b5b4…` |
| `synthetic/synthetic-report.json` | `0c078892…` |
| `synthetic/blender-rehearsal/rehearsal-report.json` | `1110aacb…` |
| `manifest.json` | `74eba4d6…` |
| `check-summary.json` | `46aa8a53…` |

The other files are listed in the sections above. `logs/` holds the Blender logs.

## Checks (MEASURED)

`tools/active_bootstrap/check_ab1a.py` at `49869ae`: **42/42** (`ACTIVE_BOOTSTRAP1A_CHECKS_PASS`;
`check-summary.json`).

The checker keeps its own literal constants. It independently recomputes:
- the NB1c action;
- the calibration axes, intrinsics, L and B⊥;
- the rectification (its own `cv2.stereoRectify`) and the whole natural pipeline (its own SGBM factory, refinement
  copy, gates and reprojection). Every saved term, mask, disparity and XYZ is equal;
- the truth firewall (guard records, ordered events, a static audit of the matcher);
- the reference: EXRs re-extracted with `exr_lite`, and the accepted oracle re-run;
- the evaluation statistics;
- the figures.

Its own synthetic cases include a differential test: with an uninformative identity, the accepted truth-assisted
`fsg_stereo.compute` returns exactly the natural result. The natural matcher therefore differs from the accepted
instrument only by the removed identity guard.

Checks 1–41 are the contract's list (section 16). Check 42 is the EXR pass-set clause, split out of check 40 and
repaired under section 23.

**Corruption / mutation suite: 51/51 caught from a passing baseline** (`ACTIVE_BOOTSTRAP1A_MUTATIONS_CAUGHT`; no probe
was not-applicable). The probes cover:
- the action: move gaze #1; substitute gaze #3;
- the instrument: `legacy_upright`; IPD; vergence; depth-search range;
- the matcher: block size; uniqueness; LR off and texture off, both with the configuration record scrubbed;
  instance-interior masking; same-instance equality;
- truth access: Object Index or Position opened during measurement; Position replacing the disparity geometry;
- the saved measurement: support mask, one valid pixel, one disparity, one XYZ point, rectification `P2`;
- the freeze: the measurement modified after evaluation; reference access before the freeze;
- the process log: a controller command; FSG6f; a second gaze; a re-render after evaluation;
- code and files: a visual pixel; FSG / controller / NB1a / NB1b / NB1c code; an undeclared file;
- records: an extra RGB array; an identity field; an identity token in the matcher; an object-id seed; the EYE pose;
  an evaluation statistic; the reference geometry; a failed synthetic case; L; one RGB pixel;
- the EXR passes: add Depth; add Normal; remove Position; remove Object Index; add an unknown pass; drop a pinned
  inherited pass; L / R mismatch; alter the recorded inherited set.

Other gates (at `49869ae` and this report):
- tangent-frame regression 92/0 (at `a3caaef`);
- layout 551/551;
- `scripts/verify_baseline.sh` 9/9;
- `git diff --check` clean.

Known answers before the canonical look (MEASURED at `a3caaef`; synthetic data only):
- **Synthetic, 12/12.**
  - Plane at `z_rect` 2 m: valid 0.99995, median disparity error 0.008 px, p95 0.23 px, median `z_rect` error 0.18 %,
    plane residual 3.7 mm.
  - Uniform pair: 0 valid.
  - LR inconsistency: 461 of 12,522 affected pixels stay valid with the LR check, 1,320 without it.
  - Occlusion: both depths recovered, 1.4996 m and 3.0018 m. The half-occluded strip has 6,656 px, of which 161 are
    valid (descriptive).
  - Support border: 0 valid pixels outside the support.
  - Gaze #1 calibration: finite. A synthetic textured plane there gives 0 valid pixels.
  - Look along ±baseline: rejected.
  - Changing the Object Index or Position truth leaves the measurement array-identical.
  - Opening an evaluation-only file: the guard refuses it.
  - An observation with truth: refused.
- **Blender rehearsal** (synthetic factory-startup room, never Classroom):
  - Position projects within 0.001 px of its pixel centre at both gazes;
  - the passes are exactly Combined / Position / Object Index;
  - forward gaze: natural valid 100 %, median |radial error| 3.55 mm against the oracle;
  - gaze-#1 geometry: 0 natural-valid pixels.

## Incidents and deviations

1. **Synthetic case 5 (before the Classroom acquisition; contract section 22).**
   - The declared "0 valid at `z_rect` 0.5 m" was wrong for the accepted instrument.
   - When the true disparity (153.4 px) exceeds the 112-level search, 4,151 in-range false matches (6.3 %) survive
     every inherited gate.
   - The case now asserts that the true geometry is never admitted and records the false-match count. The 8 m plane
     is rejected entirely.
   - No instrument or matcher rule changed.
2. **Check 07 false positive (after the run; `8c9d685`).**
   - The argv scan for "controller" matched the declared head-pose data path `previews/controller-01-full/...`.
   - Declared accepted data paths are now masked. Controller commands are still caught.
3. **Inherited EXR passes (after the run; an implementation / acquisition-format incident; contract section 23).**
   - The raw EXRs also hold 11 lighting / material passes enabled in the Classroom `.blend` view layer `interior`:
     AO, Diffuse / Glossy / Transmission Color / Direct / Indirect, and Emission.
   - The reused accepted configuration leaves them on. The accepted Controller-01 EXRs carry the same passes, plus
     Depth and Normal.
   - Depth and Normal were absent, as declared.
   - The extra passes stayed in `evaluation_only/`. They were never copied into the RGB observation and never opened
     by the matcher (0 violations).
   - Check 42 (split from check 40) first failed on this. I took the failure to Luiz, who decided AMEND + RECORD.
   - Section 23 pins the exact inherited set, and check 42 was repaired with eight new probes.
   - There was no re-render, re-measurement, re-freeze or re-evaluation.
   - Correction: commit `8c9d685` and my question to Luiz said 13 extra passes. The exact count is **11** (14 in
     total).
4. **Probe strength (checker, after the run).** The "Position replaces disparity geometry" probe was a no-op on this
   data (the core has no geometry). It now also records the Position read that such a matcher must make.
5. **Presentation fix (`b17259a`, figures only).** Empty results are drawn as explicit statements, and region D shows
   the core's reference composition.
6. **Worktrees.** NB1c was accepted from an isolated detached worktree and pushed to its branch ref, because the
   branch was checked out in an older session's worktree. AB1a used its own worktree. Both have `.venv` and the
   `scenes/classroom` asset links. Development used scratch dev runs built from the synthetic rehearsal only; they
   were not committed.

## Statements

- **Exactly one gaze was executed:** frozen NB1c RGB gaze #1, once, one binocular pair. No other gaze (2, 3 or any)
  was executed, re-centred or redirected, and gaze #1 was not re-rendered.
- **No controller** ran: no Controller-01 / 02, no FSG6f, no `fsg3_surface_map`, no fusion or persistent map, no
  controller query (checks 7, 36).
- **Natural inference used binocular RGB only:** the calibration and `rgb_L` / `rgb_R`. It used no depth, Object
  Index, Position, NB1a range or hypotheses, NB1b classes, semantics or target id (checks 18–21, 24).
- The measurement was frozen before any truth was opened (check 31). Evaluation was descriptive and changed nothing
  (check 32).
- Accepted code is unchanged: `fov3d/`, the controllers, NB1a / NB1b / NB1c, the FSG and Classroom-Oracle-1
  sources. The NB1a / NB1b / NB1c run trees and NB1c visuals are unchanged too (checks 9, 37).

## Unresolved decisions (Luiz and Chat)

1. Qualitative and scientific review of AB1a and its figures.
2. The measured result is "no metric geometry at gaze #1 with the accepted instrument". The pre-look geometry shows
   the mechanism: with `baseline_projected` at 15° from the baseline, the accepted planar rectification
   (`CALIB_ZERO_DISPARITY`, `alpha = -1`, a central crop) samples a sliver about 1° from the epipole, about 14° from
   the fixation. Here that sliver had no geometry. Whether and how the instrument should be adapted for
   large-eccentricity looks is a design question; nothing was changed here.
   - Options include a rectification core centred on the fixation, a different crop, or a look restricted by
     leverage.
   - The saved raw L / R pair contains the fixated window region, and a later step could re-analyse it without
     re-rendering.
3. What, if anything, AB1a implies for the next action. It executed no second gaze and asked no controller.
