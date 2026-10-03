# Natural Bootstrap-1c — RGB Candidate Gaze — report

**Marker.**

    NATURAL_BOOTSTRAP1C_RGB_CANDIDATE_GAZE_COMPLETE

**Status: REVIEW PENDING.** Luiz and Chat review the result. No ACCEPTED marker is written, and the branch is not
merged.

Every check passed (36/36), and every corruption was caught from a passing baseline (38/38). No RGB gaze was
executed.

**Chronology** (the STOP is part of the record):
1. The pure RGB canonical selection ran **once**, at `37c18d8`.
2. The six gazes were frozen (`rgb-gaze-freeze.json` `87a3bab0…`).
3. Evaluation remained closed.
4. Check 27's conservative ambiguity reading flagged NMS round 2 (margin 1.616e-6), and the declared STOP was taken
   (report `800af61`).
5. Luiz and Chat reviewed the pure-RGB numerical evidence: E = 4.3e-14, and identical independent picks.
6. Before evaluation, they clarified numerical ambiguity: contract section 23 and the check-27 repair, committed at
   `c7d04db`.
7. No gaze, no order and no scientific selection rule changed. The freeze was verified intact before and after that
   commit.
8. Evaluation then began, against the existing freeze. `select` was not rerun.

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
| stop resolution (contract section 23, check-27 repair, pre-evaluation record) | `c7d04db` *Clarify NB1c numerical selection robustness* |
| evaluation, figures, checks | `evaluate`, `visualize` at `c7d04db` (clean, pushed). `nb1c_spec.py`, `nb1c_attention.py`, `nb1c_run.py` and `nb1c_visuals.py` are identical to `37c18d8`. Then `check_nb1c.py --corruptions --write-summary`. |
| report | this commit |

## What ran

Run directory: `/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1c-rgb-candidate-gaze/`.

| command | commit | status | seconds |
|---|---|---|---|
| `nb1c_run.py synthetic` | `37c18d8` | ok: `NB1C_SYNTHETIC_PASS`, 13/13 | 6.8 |
| `nb1c_run.py select` | `37c18d8` | ok: the one canonical application to the accepted RGB proxy | 1.4 |
| `nb1c_run.py freeze` | `37c18d8` | ok | 0.05 |
| (STOP; resolution `c7d04db`) | | | |
| `nb1c_run.py evaluate` | `c7d04db` | ok: freeze verified first; frozen products re-verified afterwards | 0.16 |
| `nb1c_run.py visualize` | `c7d04db` | ok: 9 figures | 1.2 |
| `check_nb1c.py --corruptions --write-summary` | `c7d04db` | 36/36; corruptions 38/38 | 139 (batch) |

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

Selection opened no range, Position, validity mask, NB1a hypothesis or seed, NB1b, Object Index or catalog file.

**Evaluation guard:**
- the freeze was verified first (`freeze_verified`), then `reference_access_begins`;
- after that, the ten pinned evaluation inputs were hash-checked and read (NB1a range, label raster, hypotheses,
  reference cells and overlap names; NB1b classes, queues, environment candidate and freeze identity);
- writes went only to `evaluation/`; violations: 0;
- the frozen products were re-verified afterwards.

No evaluation input was opened before the clarification commit `c7d04db` and the freeze verification.

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

## POST-FREEZE REFERENCE / EVALUATION (MEASURED; descriptive; changes no gaze and no order)

These are not ground-truth comparisons: no accuracy, precision, recall or IoU. The footprint rule at the RGB gaze
itself is NB1b's: CENTER 6°, FULL 8.4545°, SAFE iff every cell belongs to the gaze cell's NB1a hypothesis.

| gaze | yaw, pitch (°) | range (m) | NB1a hypothesis | NB1b class | CENTER own / total | FULL own / total | safety at the RGB gaze | reference at the gaze cell | CENTER composition |
|---|---|---|---|---|---|---|---|---|---|
| 1 | +76.75, +7.75 | 4.396 | H0001 | ENVIRONMENT | 332 / 451 (119 no geometry) | 573 / 901 | **unsafe** | authored `Cube.008` | 332 catalog (`Cube.008` 298, `woodWindow.005` 20, `woodWindow.004` 11), 119 no geometry |
| 2 | −2.75, +75.75 | 1.056 | H0009 | SECONDARY | 1867 / 1867 | 3004 / 3817 | **CENTER-only-safe** | authored `Cube.006` | 1867 `Cube.006` |
| 3 | +75.25, −25.75 | 0.934 | H0004 | MARGINAL | 499 / 499 | 818 / 989 | **CENTER-only-safe** | O_0 (noncatalog) | 499 O_0 |
| 4 | +38.25, −61.75 | 1.362 | H0001 | ENVIRONMENT | 959 / 959 | 1911 / 1911 | **FULL-safe** | authored `sol` | 959 `sol` |
| 5 | +179.75, +34.75 | 1.892 | H0023 | MARGINAL | 279 / 549 (270 other) | 279 / 1095 | **unsafe** | authored `Cube.006` | 279 `Cube.006`, 265 `beams`, 5 O_0 |
| 6 | −156.25, +28.75 | 3.523 | H0001 | ENVIRONMENT | 515 / 515 | 1027 / 1027 | **FULL-safe** | authored `beams` | 408 `beams`, 97 `pipe`, 10 `wall.010` |

**Across the six** (no target was declared):

| quantity | count |
|---|---|
| valid range at the gaze centre | 6 |
| no valid range | 0 |
| distinct NB1a hypotheses hit | 4 (H0001, H0009, H0004, H0023) |
| duplicate gazes into the same hypothesis | 2 (H0001 is hit by gazes 1, 4 and 6) |
| on the environment (H0001) | 3 |
| on NB1b PRIMARY | 0 |
| on NB1b SECONDARY | 1 |
| on MARGINAL | 2 |
| on EDGE_ONLY | 0 |
| FULL-safe at the actual RGB gaze | 2 (gazes 4, 6: both on the environment shell) |
| CENTER-only-safe | 2 (gazes 2, 3) |
| unsafe | 2 (gazes 1, 5) |

**NB1b comparison** (`evaluation/nb1b-comparison.json`). Ranks are in the full unsuppressed raster (1-based, of
259,200).

| NB1b seed | A | RGB rank | nearest RGB gaze | angular distance |
|---|---|---|---|---|
| P1 H0002 | 0.3281 | 84,911 | 4 | 52.19° |
| P2 H0003 | 0.4748 | 36,601 | 6 | 65.43° |
| S1 H0009 | 1.3294 | **157** | **2** | **1.63°** (inside R_FULL of gaze 2) |
| S2 H0006 | 0.1780 | 156,006 | 6 | 74.59° |
| S3 H0007 | 0.2128 | 137,248 | 4 | 59.70° |

Only S1 lies within D_MIN (or R_FULL) of an RGB gaze. Seen from the gazes, the nearest NB1b queued seed is:

| gaze | nearest seed | distance |
|---|---|---|
| 1 | S1 | 79.0° |
| 2 | S1 | 1.6° |
| 3 | P1 | 94.6° |
| 4 | P1 | 52.2° |
| 5 | S1 | 71.0° |
| 6 | P2 | 65.4° |

**3-D separation** (head-frame first-hit points `p = r d`; all six have range). The pairwise Euclidean separation
ranges from **0.942 m** (gazes 3–4) to **6.776 m** (gazes 1–6). The other pairs:
- 1.651 m (2–3);
- 1.815 m (2–5);
- 1.888 m (5–6);
- 2.274 m (2–4);
- 2.446 m (3–5);
- 3.097 m (4–5);
- 3.390 m (2–6);
- 3.653 m (1–3);
- 4.231 m (3–6);
- 4.267 m (1–4);
- 4.337 m (1–2);
- 4.711 m (4–6);
- 4.967 m (1–5).

## Interpretation for the review (descriptive; no decision)

1. **The RGB mechanism nominated high-contrast luminance structures**, as its definition rewards:
   - a bright window (gaze 1);
   - two ceiling light fixtures (gaze 2, with a saturated-white center; gaze 5);
   - a light near-foreground surface against a darker surround (gaze 3);
   - a coherent floor patch (gaze 4);
   - the dark beams / pipe against the ceiling (gaze 6).
2. **Every direction has a geometric hit** (6/6 valid range). No RGB proposal points through empty space at the gaze
   centre. Gaze 1's CENTER does include 119 no-geometry cells: the window.
3. **The six gazes land on four NB1a hypotheses**: three on the environment shell H0001 (window wall, floor, beams),
   and three on smaller pieces (H0009, H0004, H0023).
4. **No gaze lands on the NB1b PRIMARY candidates.** The two robust range-derived foreground surfaces, H0002 and H0003
   (wood, about 0.6–0.7 m), rank 84,911 and 36,601 in the RGB raster. Their coherent centers have little 6° / 12°
   center-surround colour contrast.
5. **The one strong correspondence is the overhead light.** S1 H0009 ranks 157 in the RGB raster, and gaze 2 lies 1.63°
   from its NB1a seed.
6. **Gaze 3 is on H0004**, the MARGINAL near-foreground O_0 hypothesis whose NB1a seed NB1b showed to be unsafe:
   graph-interior clearance is not angular room. At the RGB-chosen point, H0004's CENTER disk is fully contained
   (499/499); FULL is 818/989.
7. **Measurement-core safety at the actual gazes:** 2 FULL-safe (both on the environment shell), 2 CENTER-only, 2
   unsafe. The unsafe ones are the window, whose footprint holds no-geometry cells and other pieces, and a light
   fixture smaller than the 6° center.

## Visual products (Visual Language 1)

Persistent, under `/home/lvelho/rd/f3d-vision/visuals/natural-bootstrap-1c-rgb-candidate-gaze/`, drawn at `c7d04db`
and regenerated byte-identically by check 33:

| file | truth badges | sha256 |
|---|---|---|
| `overview.png` | ORACLE INPUT, DERIVED, REFERENCE / EVALUATION | `9b79b362a167517dad2713cf2943e130060d841716975387fb9cdefc1647ec7c` |
| `rgb-input.png` | ORACLE INPUT | `aada1297f698b1cdb5241227e01598e9fa0ee8f4f1746abff2c6fe2ee9c3a61e` |
| `attention-map.png` | DERIVED | `6c3675a0e8555532f09cdc19b6bf1df2cabd0d9e6b1a4580edecc3dfb2fd6588` |
| `candidate-gazes.png` | DERIVED, ORACLE INPUT | `bc98a3284a623d50a1c677f0fc5606beecb853bdbd0614584c32a28f8ffeaf7d` |
| `center-surround-examples.png` | DERIVED, ORACLE INPUT | `f0518c438b7ff1b961d3d48770b46abf8603d2e7afc54e265795f1b45033f99c` |
| `candidate-crops.png` | ORACLE INPUT, DERIVED | `2ca18bd8e35c1e8950ca6f62619e5225b5e63546fb60e1847647e669fc980c31` |
| `candidate-evaluation.png` | REFERENCE / EVALUATION, DERIVED | `1631dd11a6f8850a8f4541ae54fe56302d09b06d6e96a821878bb75b7b1bfb0b` |
| `attention-score-distribution.png` | DERIVED | `eae5842e6ce7dd510c4f8ee7734cdd2bb8886ad076acbb85f6f6b363abc04e7d` |
| `nb1b-reference-comparison.png` | REFERENCE / EVALUATION, DERIVED | `290294d59501de4d903214fddc7174db3d17cda46bbdf531a2adc9ded27d8280` |
| `visuals-manifest.json` | — | `8f20e7873c4f1d90bf26ed674f91daddc9c4350361aa4abb7e7dab0d2bb62d60` |

The overview has four regions:
- A, ORACLE INPUT: the RGB only;
- B, DERIVED: the full A(g) field, colour ∝ (A / p99.5)^0.7;
- C, DERIVED: the six gazes 1–6 with their D_MIN (dashed) and R_FULL (solid) neighbourhoods;
- D, REFERENCE / EVALUATION, muted: the NB1b classes, the NB1b seeds and a one-line evaluation per gaze.

Minor presentation issues, not repaired:
- in region C, gaze 5's rank label falls just past the panorama's right edge (the gaze is at the seam);
- in region D, the S1 label touches gaze 2's crosshair.

Regenerate the figures with:

    .venv/bin/python tools/natural_bootstrap/nb1c_run.py visualize --run $RUN --visuals $VIS

## Machine evidence

Under `/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1c-rgb-candidate-gaze/`. The selection files are
listed under "What ran" and are frozen.

| file | sha256 |
|---|---|
| `evaluation/candidate-evaluation.json` | `f48dbf20…` |
| `evaluation/nb1b-comparison.json` | `65acee34…` |
| `evaluation/evaluation-opened-files.json` | `9517c783…` |
| `manifest.json` | `524f8fad…` |
| `check-summary.json` | `f608f1d8…` |

`process-log.jsonl` holds the five `nb1c_run.py` commands only, all `ok`: three at `37c18d8` and two at `c7d04db`,
clean and pushed.

## Checks (MEASURED)

`tools/natural_bootstrap/check_nb1c.py` at `c7d04db`: **36/36** (`NATURAL_BOOTSTRAP1C_CHECKS_PASS`;
`check-summary.json`). It recomputes independently:
- the sRGB table: bit-identical;
- the grid directions and the weights (Σ − 4π = 0);
- the CENTER and SURROUND cell sets of **every** candidate (brute-force chord membership): the patterns are equal;
- the means (|Δ| ≤ 1e-12), the two-pass variances and D_RGB;
- the whole score raster: max |ΔA| = **4.3e-14** against the tolerance 1e-6 + 1e-9 |A| (check 22, unchanged);
- the greedy NMS and the tie rule;
- every evaluation descriptor, the NB1b ranks and the 3-D separations;
- the figures (byte-identical regeneration).

Check 27 (repaired, contract section 23) reported:
- E = 4.3e-14;
- the independent picks equal the frozen six in order;
- per round, m / B = 2.17e10, **1.14e6**, 1.78e9, 8.29e9, 3.86e9 and 2.39e9 (round 2: m = 1.616e-6,
  B = 1.42e-12).

**Corruption / mutation suite: 38/38 caught from a passing baseline** (`NATURAL_BOOTSTRAP1C_MUTATIONS_CAUGHT`). A
mutant counts when any of its target checks fails.

| defect | target(s) |
|---|---|
| K = 7 (regenerated) | 25 |
| R_CENTER 5.5° (regenerated) | 13, 17 |
| R_SURROUND 13° (regenerated) | 14, 18 |
| R_FULL = √2 · 6° (regenerated) | 15, 16 |
| D_MIN 15° (regenerated) | 16 |
| gamma-space sRGB (regenerated) | 10, 19 |
| solid-angle weights omitted (regenerated) | 12, 19 |
| equirectangular pixel distance (regenerated) | 17, 18 |
| one CENTER membership changed | 17 |
| one SURROUND membership changed | 18 |
| one center mean altered | 19 |
| one variance altered | 20 |
| variance denominator removed (regenerated) | 21, 22 |
| one attention score altered | 21, 22 |
| score tie-break violated (planted tie at (0, 0)) | 23 |
| a gaze moved; two gazes reordered | 24, 27 |
| two gazes closer than D_MIN | 26 |
| longitude seam broken (regenerated) | 17, 18 |
| selection opened range / NB1a hypothesis / NB1b / Object Index | 06 / 07 / 08 / 09 |
| evaluation modified a gaze | 29 |
| evaluation read range before the freeze verification | 28, 30 |
| Blender command; controller command in the process log | 04; 05 |
| a visual pixel altered | 33 |
| fov3d, controller, NB1a or NB1b code modified; an NB1b run product altered | 34 |
| an evaluation descriptor altered | 31 |
| a synthetic case failed; tie-break reversed (regenerated) | 36 |
| **E raised until 2E + T exceeds a round margin** (δ = 9.7e-7 at the lowest-score cell) | **27** |
| **independent recomputation selects a different round winner** (checker-only, in-process; round 2) | **27** |

The first of the two new mutants failed checks 21, 27, 29, 32 and 33, but **not** check 22. The repaired robustness
rule thus catches a disagreement that the broad A correctness tolerance accepts.

Other gates:
- layout 542/542;
- `scripts/verify_baseline.sh` 9/9;
- `git diff --check` clean.

Cost (MEASURED):
- synthetic 6.8 s; select 1.4 s; freeze, evaluate and visualize under 1.3 s each;
- the checker with corruptions 139 s (batch; process pool of 32).

## Deviation from the contract's numerical expectation

Contract section 9 expected |V_R| "at the 1e-16 level" in exactly uniform neighbourhoods. The measured minimum is
−2.2e-15 V_C, at 43 candidates, all with saturated-white centers. It has no effect: the minimum denominator over all
candidates is 1.21e-4. The independent two-pass V_C at g2 is exactly 0.0.

## Incidents

**After the canonical selection:** the round-2 STOP and its resolution (sections "The STOP" and "Stop resolution").
There was no other failure, and no repeat of `select`.

**Before the canonical selection** (implementation, synthetic data only):

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
   - check run with corruptions: 2 min 15 s;
   - after the check-27 repair, the dev run gave 35/36 and 38/38 again.

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

- **No Blender process ran** (check 4): the Breadth-1 render directory is unchanged.
- **No controller ran** (check 5): only the five `nb1c_run.py` commands, and no controller module is imported.
- **No gaze was executed.** There was no foveation, no stereo and no new depth. Every number about range, NB1a, NB1b
  or reference is post-freeze evaluation of existing accepted products.
- **Selection used RGB only** (checks 6–9): its data reads are exactly the RGB proxy, with 0 violations; the import
  and static audit hold.
- **No evaluation influence** (checks 28–32): evaluation started only after the freeze verified, and after the
  clarification commit. The six gazes and their order are the frozen ones and equal the pure-RGB recomputation.
- The accepted NB1a and NB1b code, run trees and figures, `fov3d/` and the controllers are unchanged (check 34).
- No RGB segmentation, no range-based reseeding and no controller integration were done. Natural Bootstrap-2 is not
  started.

## Unresolved decisions

1. Qualitative and scientific review of NB1c and its figures (Luiz and Chat).
2. Whether and how the six RGB proposals should lead to the next step (local foveation), given that:
   - three land on the environment shell;
   - none lands on the NB1b PRIMARY foreground;
   - one coincides with the NB1b SECONDARY light.

NB1c is not merged. No ACCEPTED marker is written.
