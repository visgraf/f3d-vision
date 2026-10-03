# Natural Bootstrap-1c — RGB Candidate Gaze — report

**Status: STOP RESOLVED BEFORE EVALUATION — evaluation pending.**

No completion marker is written yet. The pure RGB selection ran once and is frozen. A declared stop condition then
triggered on the NMS round-2 margin (see "The STOP"). Evaluation stayed closed.

Luiz and Chat reviewed the pure-RGB numerical evidence and resolved the STOP before any evaluation input was opened
(see "Stop resolution"). They kept the frozen six gazes and separated numerical ambiguity from the loose A
correctness tolerance (contract section 23). No gaze and no scientific selection rule changed.

> **Question.** Can sensor-scale center-surround contrast in one coarse spherical RGB observation, with no depth and
> no Blender identity, nominate six spatially separated gaze directions that provide useful starting points for
> active foveal scene discovery?

Contract: `docs/natural-bootstrap/nb1c-rgb-candidate-gaze-contract.md`. MEASURED means produced by the runs below.

## Branch and commits

| item | value |
|---|---|
| NB1b acceptance | `0238f007a505f38087c9e40442243003cd3716cc` *Accept NB1b foveal serviceability* |
| post-NB1b pivot (handoff) | `7d1c1b97e1e29be4bd5e45066507f9c12be006bc` *Pivot natural bootstrap to RGB candidate gaze*; `origin/main` fast-forwarded to it |
| branch | `natural-bootstrap/nb1c-rgb-candidate-gaze`, from `main` @ `7d1c1b9`; isolated worktree |
| contract | `9a862dc` *Contract NB1c RGB candidate gaze* |
| implementation (frozen before the canonical selection) | `37c18d8` *Implement NB1c RGB candidate gaze* |
| canonical run | `synthetic`, `select`, `freeze` at `37c18d8` (clean, pushed; `process-log.jsonl`) |
| STOP report | `800af61` *Report NB1c RGB selection; stop before evaluation* |
| stop resolution (contract section 23, check-27 repair) | this commit |

## What ran, and what did not

Run directory: `/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1c-rgb-candidate-gaze/`.

| command | status | seconds |
|---|---|---|
| `nb1c_run.py synthetic` | ok: `NB1C_SYNTHETIC_PASS`, 13/13 | 6.8 |
| `nb1c_run.py select` | ok: one canonical application to the accepted RGB proxy | 1.4 |
| `nb1c_run.py freeze` | ok | 0.05 |
| `nb1c_run.py evaluate` | **not run** (STOP) | — |
| `nb1c_run.py visualize` | **not run** | — |
| `check_nb1c.py --corruptions --write-summary` | **not run**: it requires the evaluation products | — |

The freeze record is `selection/rgb-gaze-freeze.json`
`87a3bab01f55051316ac1eb45b48f394211f4c7a3a317fd0e61c0e52c36f9b37`.

| file | sha256 |
|---|---|
| `source/rgb-source-manifest.json` | `91b51d94…` |
| `selection/attention-score.npz` | `4bfee30e…` |
| `selection/attention-diagnostics.npz` | `5dce74a7…` |
| `selection/candidate-gazes.json` | `8041b954…` |
| `selection/nms-rounds.json` | `19ffb3da…` |
| `selection/selection-summary.json` | `31f3d1d2…` |
| `selection/selection-opened-files.json` | `9b9b1b13…` |
| `synthetic/synthetic-report.json` | `3e8bff9d…` |

## Source, sensor and truth firewall (MEASURED)

**RGB source.** `previews/natural-bootstrap-1a-range-connectivity/input/rgb-sensory.npz`:
- sha256 `cd2600e678fe7f33471e50bee5443128dd5470cc2b380eb7b34a22d3e4ad2c3e`, verified by `select`;
- the full hash was read from the accepted NB1a `manifest.json` and `input-manifest.json`;
- one array, `srgb8`, `uint8`, 360 × 720 × 3.

It is ORACLE INPUT, a controlled sensory proxy from Blender.

**Sensor.** `tools/fsg_geometry.py` (blob `ad47c1ef…`, sha256 `ae3779bc…`) declares `CORE_FOV_DEG = 12.0`:
- R_CENTER = 6°;
- R_SURROUND = 12°;
- R_FULL = atan(√2 tan 6°) = 8.45453360743381°;
- D_MIN = 2 R_FULL = 16.90906721486762°;
- ANGLE_EPS_RAD = SCORE_TIE_REL = VAR_EPS = 1e-12;
- K = 6.

**Selection guard** (`nb1a_guard.OpenGuard`):
- data reads: exactly `rgb-sensory.npz`;
- writes: 6 files, under `source/` and `selection/` only;
- truth-firewall violations: **0**.

No range, Position, validity mask, NB1a hypothesis or seed, NB1b, Object Index or catalog file was opened. After
`select`, no NB1c process opened any evaluation input.

## PURE RGB SELECTION (MEASURED; frozen before any evaluation)

**Grid and numerics:**
- resolution 720 × 360 (0.5°); 259,200 candidate directions;
- Σ weights − 4π = 0.0;
- the per-channel median shift is (0.1356, 0.0908, 0.0561), linear;
- the minimum score denominator over all candidates is 1.21e-4;
- 43 candidates have V_C < 0 at rounding level (minimum −2.2e-15, in saturated-white centers); no V_S is negative.

**Sampled cells per candidate** (min / median / max):

| | CENTER | SURROUND |
|---|---|---|
| all candidates | 441 / 638 / 8,641 | 1,354 / 1,935 / 11,698 |
| \|pitch\| < 30° | 441 / 470 / 517 | 1,354 / 1,399 / 1,568 |
| 30° ≤ \|pitch\| < 60° | 517 / 638 / 889 | 1,572 / 1,935 / 2,760 |
| \|pitch\| ≥ 60° | 913 / 1,769 / 8,641 | 2,796 / 5,955 / 11,698 |

**Attention score A over all candidates** (unweighted):

| min | median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|
| 0.000796 | 0.2278 | 0.5210 | 0.6192 | 0.8678 | 1.4323 |

**The six RGB gazes** (selection order; linear RGB):

| rank | row, col | yaw, pitch (°) | A | D_RGB | V_C | V_S | mu_C | mu_S | cells C / S |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 164, 513 | +76.75, +7.75 | 1.432258 | 0.530476 | 0.025095 | 0.112084 | (0.579, 0.517, 0.549) | (0.263, 0.229, 0.235) | 451 / 1,372 |
| 2 | 28, 354 | −2.75, +75.75 | 1.331223 | 0.951854 | −1.8e-15 | 0.511257 | (1.000, 1.000, 1.000) | (0.490, 0.451, 0.413) | 1,867 / 6,382 |
| 3 | 231, 510 | +75.25, −25.75 | 1.196390 | 0.211278 | 0.003320 | 0.027867 | (0.308, 0.220, 0.182) | (0.160, 0.107, 0.082) | 499 / 1,518 |
| 4 | 303, 436 | +38.25, −61.75 | 1.179161 | 0.063551 | 0.001417 | 0.001488 | (0.108, 0.070, 0.046) | (0.058, 0.038, 0.025) | 959 / 2,940 |
| 5 | 110, 719 | +179.75, +34.75 | 1.142861 | 0.856923 | 0.556536 | 0.005672 | (0.630, 0.602, 0.574) | (0.151, 0.106, 0.066) | 549 / 1,658 |
| 6 | 122, 47 | −156.25, +28.75 | 1.110885 | 0.066079 | 0.000550 | 0.002988 | (0.060, 0.042, 0.025) | (0.108, 0.078, 0.051) | 515 / 1,556 |

Gaze 5 lies in the last column, at the longitude seam.

**NMS rounds:**

| round | score | tie set | eligible before | newly suppressed | remaining | margin to next eligible |
|---|---|---|---|---|---|---|
| 1 | 1.432258 | 1 | 259,200 | 3,639 | 255,561 | 0.03299 |
| 2 | 1.331223 | 1 | 255,561 | 19,245 | 236,316 | **1.616e-6** |
| 3 | 1.196390 | 1 | 236,316 | 4,011 | 232,305 | 0.002277 |
| 4 | 1.179161 | 1 | 232,305 | 7,947 | 224,358 | 0.01049 |
| 5 | 1.142861 | 1 | 224,358 | 4,415 | 219,943 | 0.004749 |
| 6 | 1.110885 | 1 | 219,943 | 3,010 | 216,933 | 0.002862 |

**Pairwise angular distances** (degrees):

|   | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| 1 | 0 | 79.913 | 33.532 | 75.626 | 96.101 | 117.255 |
| 2 | 79.913 | 0 | 112.023 | 139.983 | 69.488 | 74.154 |
| 3 | 33.532 | 112.023 | 0 | 43.683 | 115.653 | 134.471 |
| 4 | 75.626 | 139.983 | 43.683 | 0 | 143.752 | 145.634 |
| 5 | 96.101 | 69.488 | 115.653 | 143.752 | 0 | 21.213 |
| 6 | 117.255 | 74.154 | 134.471 | 145.634 | 21.213 | 0 |

The minimum pairwise separation is **21.213°** (gazes 5–6). Every pair is ≥ D_MIN.

## The STOP: round-2 margin (diagnosis, MEASURED, pure RGB only)

**Trigger.** In round 2:
- g2 = (28, 354) scores 1.331222512710;
- the best other eligible candidate, (28, 355), scores 1.331220896834;
- the margin is 1.616e-6.

Check 27 of `check_nb1c.py` (committed at `37c18d8`) flags a decision as ambiguous when its margin is ≤ 2 × the declared
A tolerance, 2 × (1e-6 + 1e-9 |A|) = 2.003e-6. This is the error bound on a difference of two scores that are each
within tolerance. The check would therefore fail, and contract section 22 makes such a decision a STOP.

The contract's stop wording, "within the declared numerical agreement tolerance", read literally against the
single-value tolerance (1.0e-6), would not trigger. The checker and the contract wording therefore disagree on this
case. I did not choose the permissive reading.

**Diagnosis.** A scratch command applied the checker's own independent implementation (`check_nb1c.brute` and `nms`)
to the RGB proxy only. No evaluation input was read.
- **Measured agreement:**
  - max |A_stored − A_independent| = **4.3e-14** over all 259,200 candidates (median 3.9e-16; max relative 2.1e-12);
  - CENTER and 12°-disk membership patterns equal for every candidate (brute-force chord membership);
  - 0 non-interval memberships, 0 box-edge hits.
- **The independent NMS selects the identical six gazes in the identical order.** Its round margins match the stored
  ones to the printed precision; round 2 is 1.616e-6 in both.
- **The round-2 margin is 3.7 × 10⁷ times the measured disagreement.** At both cells the stored and independent A
  differ by ≤ 3.6e-15. The decision is numerically robust; only the deliberately loose declared tolerance (1e-6) flags
  it.
- **What the two cells are.** (28, 354) and (28, 355) are adjacent columns, 0.123° apart at pitch 75.75°. For both:
  - the CENTER is entirely saturated white: mu_C = (1, 1, 1), V_C = 0 (stored −1.8e-15);
  - the score is set by a smoothly varying surround (V_S 0.51126 vs 0.51104).

  The next cells, (37, 360) and (28, 356), are lower by 5.4e-6 and 5.7e-6: a smooth plateau maximum, not a tie.
- **Consequence.** If round 2 had taken (28, 355), the greedy sequence would be:

  (164, 513), **(28, 355)**, (231, 510), (303, 436), (110, 719), (122, 47)

  Only g2 moves, by one column (0.123°). The other five gazes and the order are unchanged.

## Stop resolution (Luiz and Chat, before evaluation)

**Decision:** CONTINUE NB1c WITH THE EXISTING FROZEN SIX RGB GAZES.
- No regeneration, no reselection, no gaze moved.
- No change to K, a radius, the score, the tie rule or the NMS.

The STOP was correct under the conservative interpretation, and it stays in the record. The cause was a
checker / contract numerical-semantics mismatch:
- section 9's `|ΔA| <= 1e-6 + 1e-9 |A|` is a loose pass / fail agreement bound for one value;
- check 27 had used twice that bound as the ambiguity threshold between two competing scores.

Contract section 23 now defines:
- E = max |A_stored − A_independent| over the whole RGB-only raster;
- per round, T = 1e-12 · max(1, |A_selected|) and B = 2 E + T;
- a round is robust iff the independent recomputation selects the same candidate and its margin m > B.

Check 27 is repaired accordingly. Only check 27 changed: the A correctness tolerance (check 22) and every other check
are unchanged, and the checker gains two probative corruptions for the repaired rule.

**Pre-evaluation record** (MEASURED with the repaired `check_nb1c.nms_robustness`, on the RGB proxy and the frozen
score raster only, before any evaluation input was opened):

    E = max |A_stored - A_independent| = 4.296563105299356e-14   (all 259,200 candidates)

| round | frozen gaze | independent pick | runner-up | margin m | T | B = 2E + T | m / B | robust |
|---|---|---|---|---|---|---|---|---|
| 1 | (164, 513) | same | (164, 514) | 0.0329911 | 1.432e-12 | 1.518e-12 | 2.17e10 | yes |
| **2** | **(28, 354)** | **same** | **(28, 355)** | **1.61588e-6** | **1.331e-12** | **1.417e-12** | **1.14e6** | **yes** |
| 3 | (231, 510) | same | (231, 509) | 0.00227688 | 1.196e-12 | 1.282e-12 | 1.78e9 | yes |
| 4 | (303, 436) | same | (303, 435) | 0.0104902 | 1.179e-12 | 1.265e-12 | 8.29e9 | yes |
| 5 | (110, 719) | same | (111, 719) | 0.00474903 | 1.143e-12 | 1.229e-12 | 3.86e9 | yes |
| 6 | (122, 47) | same | (122, 48) | 0.00286217 | 1.111e-12 | 1.197e-12 | 2.39e9 | yes |

The margins replayed on the stored raster and computed on the independent raster agree to the printed precision.
Every round is numerically robust, and the independent six picks equal the frozen six in order.

The frozen selection was re-verified before the clarification. All 7 frozen files are byte-identical to
`rgb-gaze-freeze.json` `87a3bab0…`.

## Deviation from the contract's numerical expectation

Contract section 9 expected |V_R| "at the 1e-16 level" in exactly uniform neighbourhoods. The measured minimum is
−2.2e-15 V_C, at 43 candidates, all with saturated-white centers. It has no effect: the minimum denominator over all
candidates is 1.21e-4. The independent two-pass V_C at g2 is exactly 0.0.

## Implementation incidents (before the canonical selection; synthetic data only)

1. **Synthetic NMS case.** The hand-placed "just beyond D_MIN" peak (169, 392) measured 16.899°, inside D_MIN; I had
   ignored the cos-latitude compression. It was replaced by (155, 383), at 16.927° by search. It lies inside the
   window (D_MIN, 2·√2·6°), so it also separates the R_FULL-formula mutant.
2. **Static audit.** Check 9's token audit flagged the word "hypothesis" in a statement string of
   `nb1c_attention.summary`. The string was rephrased; the audit was not weakened.
3. **Figure fixes** on the scratch dev run:
   - panorama title and badge collisions; header lines wrapped to the canvas;
   - D_MIN rings drawn solid: `style.dashed_line` restarts its pattern per segment, so NB1c dashes by arc length;
   - the evaluation-count layout, staggered percentile labels and colorbar labels.
4. **Scratch dev harness, not committed.** It ran the whole pipeline on a synthetic room-like RGB sphere, never the
   Classroom RGB, with the RGB pin patched:
   - checks 35/36; check 1 fails by design, since the dev RGB is not the pinned file;
   - 36/36 corruptions caught by their target checks;
   - check run with corruptions: 2 min 15 s.

   As the contract allows, that dev run exercised the evaluation code on the accepted NB1a / NB1b products with
   synthetic gaze directions. It said nothing about Classroom RGB attention.
5. **Prototype** (before the contract, synthetic data): the fast decomposition against brute force gave exact counts
   for every candidate and max |ΔA| 1.6e-15; brute force alone took 145 s single-threaded.
6. **Worktree setup:** `.venv` and the `scenes/classroom` asset links, as for NB1b.

Gates before the implementation commit:
- layout 542/542;
- `scripts/verify_baseline.sh` 9/9;
- `git diff --check` clean.

Before the contract commit, layout 537/537.

## Statements

- No Blender process ran, and no controller ran (process log: three `nb1c_run.py` commands, all `ok`, clean and
  pushed at `37c18d8`).
- No RGB gaze was executed. There was no foveation and no stereo.
- Selection opened the RGB proxy only. No evaluation input has been opened by any NB1c command.
- No RGB segmentation, no range-based reseeding, no controller integration; Natural Bootstrap-2 is not started.
- NB1c is not merged, and no ACCEPTED or COMPLETE marker is written.
