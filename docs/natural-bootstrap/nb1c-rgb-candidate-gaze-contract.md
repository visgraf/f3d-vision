# Natural Bootstrap-1c — RGB Candidate Gaze — contract

**Status: PROPOSED.** This contract is committed before implementation and before any attention computation on
the Classroom RGB proxy. Branch `natural-bootstrap/nb1c-rgb-candidate-gaze`, from `main` @
`7d1c1b97e1e29be4bd5e45066507f9c12be006bc` (NB1b accepted at `0238f00`; the post-NB1b pivot recorded at
`7d1c1b9`).

It implements the scientific pivot decided by Luiz and Chat after NB1b:

    INITIAL BOOTSTRAP SHOULD NOT REQUIRE DEPTH.

NB1a and NB1b remain accepted studies of what geometry can do. NB1c is the first step of the revised near-term
chain, and it stops after its first arrow:

    coarse spherical RGB
      -> RGB candidate gazes                          (NB1c)
      -> [future step, not run now] local foveation
      -> local stereo depth / surface orientation
      -> active surface growth using geometric continuity

## 1. Question

> Can sensor-scale center-surround contrast in one coarse spherical RGB observation, with no depth and no
> Blender identity, nominate six spatially separated gaze directions that provide useful starting points for
> active foveal scene discovery?

NB1c stops after producing and evaluating the six candidate directions. It does **not**:
- render Blender, acquire new depth, or run stereo;
- run Controller-01 or Controller-02, or execute any of the six gazes;
- grow a surface, or segment the RGB image into objects;
- use NB1a hypotheses, NB1b serviceability, Blender identity or semantics during selection;
- optimize the six gazes against later reference information.

**The claim is modest.** The score is one simple receptive-field-like attention hypothesis. It is not objectness
and not saliency ground truth. There is no target outcome (section 16).

## 2. RGB-only source (pinned before implementation)

| item | value |
|---|---|
| file | `/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1a-range-connectivity/input/rgb-sensory.npz` |
| sha256 | `cd2600e678fe7f33471e50bee5443128dd5470cc2b380eb7b34a22d3e4ad2c3e` |
| content | exactly one array, `srgb8`: `uint8`, shape (360, 720, 3) |
| recorded in | the accepted NB1a `manifest.json` (`69021c636ef735edf425dab82504473d973735ddeb8109d06ca1e6ebb12fe12e`), key `input/rgb-sensory.npz`, and `input/input-manifest.json`, key `rgb-sensory.npz` |
| produced by | NB1a `input` at `6b63cdc` (frozen, accepted at `dcd294f`) |
| definition | "standard sRGB transfer of clip(Combined linear, 0, 1), 8-bit" of the Breadth-1 canonical EXR (`4ea036fc…`) |

The full hash was read from the accepted NB1a manifest. It matches the prefix `cd2600e6…` recorded in the NB1a
report, and the file on disk.

**Truth status.** The RGB proxy is **ORACLE INPUT**: a controlled sensory proxy, because it originates from
Blender. NB1c selection gets RGB **only**.

**Selection must not read:**
- `input/range-sensory.npz`, Position, the EXR, or any depth-validity mask;
- the NB1a hypothesis raster, hypotheses, seeds or evaluation products;
- NB1b selection or serviceability products;
- Object Index, the authored catalog or any reference product;
- controller outputs.

Selection does not secretly mask invalid-depth directions. If RGB proposes a direction with no geometric hit,
that is a legitimate RGB-bootstrap result, discovered later in evaluation.

The pin lives in the selection code. Selection itself does not open the NB1a manifests: the checker verifies the
pin against them (check 1).

## 3. Sensor-derived angular scales

Source: the sealed sensor implementation `tools/fsg_geometry.py`, unchanged since the baseline import:

| item | value |
|---|---|
| git blob | `ad47c1eff6db2b9bd29340fdd633d9c09718d070` |
| sha256 | `ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54` |
| declaration | `CORE_FOV_DEG = 12.0` |

Selection takes `CORE_FOV_DEG` from that file and verifies its hash first. All values are computed from these
formulas, never from rounded constants:

    CORE_FOV    = 12°                                   (CORE_FOV_DEG)
    R_CENTER    = CORE_FOV / 2  = 6°                    the centre of the receptive field
    R_SURROUND  = CORE_FOV      = 12°                   the outer edge of the surround annulus
    R_FULL      = atan( sqrt(2) * tan(R_CENTER) )       ≈ 8.45453360743381°  (the square core's corner radius)
    D_MIN       = 2 * R_FULL                            ≈ 16.90906721486762°  (spatial exclusion distance)

    ANGLE_EPS_RAD = 1e-12
    SCORE_TIE_REL = 1e-12
    VAR_EPS       = 1e-12      (squared linear-RGB units)

`VAR_EPS` is purely a numerical denominator guard. It is not a fitted scientific threshold.

## 4. Fixed attention budget

    K = 6

This is the only deliberately chosen experimental parameter. It is declared before any Classroom computation,
and it is not changed after seeing Classroom. No other K is run in this experiment.

K = 6 does **not** mean six objects, six scene parts, complete coverage or an expected scene complexity. It
means only that the broad RGB system may nominate six initial places worth interrogating.

## 5. Spherical RGB representation

- Resolution: `WIDTH = 720`, `HEIGHT = 360` (0.5° cells).
- **Candidates:** all 259,200 cell centres. There is no range-validity mask.
- **Cell centres:** exactly the accepted Breadth-1 / NB1a convention (`tools/natural_bootstrap/nb1a_spec.py`,
  read-only):

      yaw   = −180° + 0.5°(col + 0.5),   pitch = 90° − 0.5°(row + 0.5)
      d     = (sin yaw cos pitch, sin pitch, −cos yaw cos pitch)          (fixed head frame)

- **Angular distance:** the true spherical distance, from the direction vectors. Longitude wraps naturally, and
  there is no equirectangular pixel-distance approximation:

      alpha(i, g) = atan2( ||d_i × d_g||, d_i · d_g )

- **Solid-angle cell weights**, for row j:

      d_lambda = 2π / WIDTH
      phi_hi   = π/2 − j π / HEIGHT
      phi_lo   = π/2 − (j + 1) π / HEIGHT
      w_j      = d_lambda * (sin(phi_hi) − sin(phi_lo))

  The full grid sums numerically to 4π (checked to 1e-12).

## 6. Standard sRGB → linear RGB

    c_srgb = srgb8 / 255
    c_linear = c_srgb / 12.92                          if c_srgb <= 0.04045
             = ((c_srgb + 0.055) / 1.055) ** 2.4       otherwise

The conversion is evaluated in Python float64 for each of the 256 codes, and applied per channel by table
look-up. The attention calculation is float64. No grayscale, HSV, Lab, learned colour embedding, exposure
normalization or scene-adaptive white balance is used: ordinary linear-RGB vector statistics only.

## 7. Center and surround

For candidate gaze g:

    CENTER   C(g) = { i : alpha(i, g) <= R_CENTER + ANGLE_EPS_RAD }
    SURROUND S(g) = { i : R_CENTER + ANGLE_EPS_RAD < alpha(i, g) <= R_SURROUND + ANGLE_EPS_RAD }

The 6° boundary belongs to CENTER; the 12° boundary belongs to SURROUND. For region R ∈ {C, S}, with solid-angle
weights:

    W_R  = Σ_i w_i
    mu_R = Σ_i w_i rgb_i / W_R                         (a 3-vector, linear RGB)
    V_R  = Σ_i w_i ||rgb_i − mu_R||² / W_R             (scalar squared Euclidean RGB variation)

## 8. One RGB attention score

    D_RGB(g) = || mu_C − mu_S ||_2
    A(g)     = D_RGB(g) / sqrt( V_C + V_S + VAR_EPS )

This is the **only** NB1c attention score:
- numerator: center-surround colour distinctiveness;
- denominator: within-center plus within-surround colour heterogeneity.

The mechanism prefers a center that is visually different from its surroundings **and** relatively internally
coherent. It has no gradient, edge-density, texture, multiscale, semantic, learned, depth, normal or
segmentation term. `D_RGB`, `V_C`, `V_S` and `A` are recorded separately for every candidate.

## 9. Numerical method (implementation; mathematically identical to sections 7–8)

The generator evaluates the definitions exactly, organised so that all 259,200 candidates take seconds:

1. **Row-interval lemma.** For two rows (j0, j), the distance between cells (j0, c0) and (j, c0 + Δc) depends
   only on (j0, j, |Δc|), with |Δc| the circular column offset in [0, 360]. Cell centres never lie on a pole,
   so it is strictly increasing in |Δc|. Therefore the cells of row j inside a disk around (j0, c0) form one
   circular interval |Δc| ≤ k, or none, or the whole row.

   The generator derives k for every (j0, j) and both radii by evaluating the section-5 `alpha` on the actual
   direction vectors at reference column 0. It STOPs unless every derived membership is exactly such an
   interval. The derived membership pattern is stored. The checker recomputes the CENTER and SURROUND cell sets
   of **every** candidate directly (check 17–18).
2. **Sums.** Per row, circular box sums grow by symmetric increments (k → k + 1 adds columns c0 − k − 1 and
   c0 + k + 1). The operation sequence is identical for every column, so the score raster is exactly equivariant
   to longitude rolls.

   Region sums add rows in ascending order. The SURROUND sums are the 12° disk sums minus the CENTER sums: the
   two sets are disjoint and together form the 12° disk.
3. **Shift.** The values are shifted by one constant, `m` = the per-channel median of the 259,200 linear-RGB
   values. A constant shift leaves `mu_C − mu_S` and every `V_R` mathematically unchanged. It makes a uniform
   sphere exactly zero, and it improves conditioning.

   `V_R` is evaluated by the identity `V_R = Σ w ||rgb − m||² / W_R − ||mu_R − m||²`. It is not clamped. In
   exactly uniform neighbourhoods, rounding leaves |V_R| at the 1e-16 level, of either sign, and |A| at the
   1e-9 level. The denominator must stay positive; otherwise STOP.

**Declared agreement tolerances** between the stored values and the checker's independent recomputation. The
checker uses brute-force per-candidate membership by the chord formula and the two-pass variance definition:

| quantity | tolerance |
|---|---|
| CENTER / SURROUND cell sets and counts | exact |
| W_C, W_S | relative 1e-12 |
| mu_C, mu_S, D_RGB | absolute 1e-12 |
| V_C, V_S | absolute 1e-11 |
| A | \|ΔA\| <= 1e-6 + 1e-9 \|A\| |
| sRGB → linear table | exact (bit-identical) |

These are float64 agreement bounds, not scientific thresholds.

On a random synthetic sphere, the prototype of this method (synthetic data only) agreed with brute force:
- counts exactly for every candidate;
- max |ΔA| 1.6e-15.

That is a PROPOSED expectation; the measured agreement is reported.

## 10. Deterministic score ties

At each greedy step, among the currently eligible candidates:

    A_max     = maximum eligible score
    tie set   = { i eligible : A_max − A_i <= SCORE_TIE_REL * max(1, |A_max|) }

The tie set is resolved by the smaller row, then the smaller column. This does not depend on incidental sort
order.

## 11. Six-gaze spherical NMS

Selection is greedy. Initially every one of the 259,200 cells is eligible. For k = 1..6:
1. choose the eligible maximum by section 10;
2. record it as g_k;
3. suppress every remaining candidate q with `alpha(q, g_k) + ANGLE_EPS_RAD < D_MIN`. A candidate exactly at the
   D_MIN boundary remains eligible; g_k itself (alpha = 0) is suppressed.

Exactly K = 6 directions are chosen; if the implementation cannot produce six, HARD FAIL. There is no minimum
score threshold: even a poor sixth proposal is informative, because K is a declared budget. Selected gazes are
never clustered or moved afterwards.

**Why D_MIN = 16.9°.** It is not fitted to Classroom. It is twice the conservative angular radius of the nominal
square measurement core, so the conservative full-core spherical neighbourhoods of two selected gazes do not
overlap. It is a geometric diversity rule, not an object-separation assumption.

**NMS record per round:**
- the selected cell and score;
- the tie-set size;
- the number eligible before selection;
- the number newly suppressed: previously eligible cells within D_MIN of g_k by the rule, g_k included;
- the number remaining (eligible before − newly suppressed);
- the margin to the best eligible score outside the tie set (a robustness diagnostic only).

## 12. Truth firewall

The canonical selection path runs under the accepted allowlist file-open guard `nb1a_guard.OpenGuard`
(read-only reuse):
- **data reads:** exactly `rgb-sensory.npz`;
- **code reads:** its own code and configuration (`tools/natural_bootstrap/nb1c_spec.py`, `nb1c_attention.py`,
  the accepted `nb1a_spec.py` and `nb1a_guard.py`, and the sealed `tools/fsg_geometry.py`).

Every open is recorded in `selection/selection-opened-files.json`, and violations must be **0**.

Static audit:
- the selection modules (`nb1c_spec.py`, `nb1c_attention.py`) import only `math`, `json`, `numpy`, `pathlib`,
  `sys`, `hashlib`, `nb1a_spec` and `fsg_geometry`;
- they, and the `select` routine of `nb1c_run.py`, name no range, Position, validity, hypothesis, seed,
  serviceability, Object Index, catalog, reference or controller source.

The evaluation-only pins live in `nb1c_run.py`, outside the selection modules.

## 13. Freeze

Before any depth, range, hypothesis or reference information is opened, `freeze` writes
`selection/rgb-gaze-freeze.json`. It holds the sha256 of:
- `source/rgb-source-manifest.json`, which records the RGB source hash;
- `selection/attention-score.npz` (`A`);
- `selection/attention-diagnostics.npz`, which holds:
  - `n_C`, `n_S`, `W_C`, `W_S`;
  - `mu_C`, `mu_S`, `V_C`, `V_S`, `D_RGB`;
  - the membership pattern;
  - the sRGB table, the shift and the row weights;
- `selection/candidate-gazes.json`, `nms-rounds.json`, `selection-summary.json` and `selection-opened-files.json`.

It also holds:
- the selection configuration and its hash;
- the selection code hashes;
- the sensor source hash;
- the spherical grid identity: the sha256 of the direction and row-weight arrays.

After the freeze, evaluation may begin:
- `evaluate` verifies the freeze first and records `freeze_verified`, then `reference_access_begins`, before its
  first reference open;
- it writes only under `evaluation/`, and re-verifies the freeze afterwards;
- it never alters the six gaze directions or their order.

After the freeze there is no change to the score, a radius, K, the NMS, a gaze position, or any added cue. Any
scientific-rule change after evaluation requires a STOP and a decision by Luiz and Chat.

## 14. Pure RGB results (PRIMARY measurements; recorded before evaluation)

`selection/selection-summary.json` and `candidate-gazes.json` record:
- the RGB resolution and the total candidate directions (259,200);
- the CENTER and SURROUND sampled-cell distributions, over all candidates and by latitude;
- the attention-score distribution over all candidates (unweighted): min, median, 90th, 95th and 99th
  percentiles (numpy linear interpolation), max;
- for each selected gaze g1..g6:
  - rank, row / col, yaw / pitch, direction;
  - A, D_RGB, V_C, V_S, mu_C and mu_S (linear RGB);
  - the CENTER / SURROUND counts and weights;
- every NMS round (section 11);
- the full 6 × 6 pairwise angular-distance matrix, and the verification that every off-diagonal pair is
  ≥ D_MIN − ANGLE_EPS_RAD (the tolerance the suppression rule allows);
- numerics: the minimum denominator, and the number of candidates with a negative V_R at rounding level.

These are the primary NB1c measurements.

## 15. Reference / evaluation after the freeze (descriptive only)

Evaluation-only inputs. Every hash is checked, and they are opened only after the freeze verifies:

| file | sha256 |
|---|---|
| NB1a `input/range-sensory.npz` (`range_m`, `valid_mask`) | `02bdf22472ab542545102ec5c3c7f092953a1f89ee2f61ebe62225545ed0883b` |
| NB1a `discovery/hypothesis-raster.npz` (`labels`) | `513a15e0077fc1f5d84847ff020386687ce7ec28477b71ddc349378fb00bae88` |
| NB1a `discovery/hypotheses.json` | `eecf180faecd7765e15c162b76ae1427dc12212026f439d608f21b9c4357009b` |
| NB1a `evaluation/reference-cells.npz` (`object_index`, `o0_mask`) | `54a58d28eab4ade81c7e945fefb379ce6d13f5a149797324bdbb23f1f84f9f76` |
| NB1a `evaluation/overlap-summary.json` (reference names) | `1ad980a4a84af7e0e63b6f81360c85c77e3863d7baa324bf45bcdedfe65691cb` |
| NB1b `selection/serviceability.json` (classes) | `2c83d76cd4c61bea3218b24893effe6e83a2965c9aabd300da7843150e53c1b1` |
| NB1b `selection/primary-look-queue.json` | `1cc867b1a3fb69ed6be6487625b42ae8912f61536ae2e15bb7986a126795dc10` |
| NB1b `selection/secondary-look-queue.json` | `5481497c62f9c0f154fc2d9eb774103e70e1dd61d8ceb5c84181522e7b9b5875` |
| NB1b `selection/environment-candidate.json` | `427346e91483fd74caf0afefe518fd2700a3c9cfe5ab27a93aae104dbea59759` |
| NB1b `selection/serviceability-freeze.json` (identity) | `f99b7cae02498feb21ae1d80978b57c877c44984067d55c7fd2bbe189efb6e9a` |

The scene observation is not rerendered or recomputed. No evaluation result may affect selection.

**T. For each frozen gaze** (`evaluation/candidate-evaluation.json`):
1. whether valid range exists at the gaze centre;
2. if so, the radial range at the centre;
3. the frozen NB1a hypothesis containing that exact gaze cell (or none);
4. that hypothesis's frozen NB1b class: `ENVIRONMENT_CANDIDATE`, `PRIMARY_LOOK`, `SECONDARY_LOOK`, `MARGINAL` or
   `EDGE_ONLY`;
5. at the RGB-selected gaze itself, **not** at the NB1a seed, the CENTER (6°) and FULL (≈ 8.45°) support
   containment against the frozen NB1a raster. This uses NB1b's footprint rule: `alpha <= R + ANGLE_EPS_RAD` over
   the full sphere; SAFE iff every cell belongs to the gaze cell's hypothesis; no geometry counts as outside;
6. the resulting safety at the actual gaze:

   | category | meaning |
   |---|---|
   | `GAZE_FULL_SAFE` | the FULL footprint is SAFE |
   | `GAZE_CENTER_ONLY_SAFE` | only the CENTER footprint is SAFE |
   | `GAZE_UNSAFE` | the CENTER footprint is not SAFE |
   | `GAZE_NO_RANGE` | no valid geometric hit at the gaze cell |

7. the reference at the gaze cell: O_0 / noncatalog, an authored id and name, or no geometry. Also the CENTER
   footprint's O_0, catalog and no-geometry cell counts and its largest authored ids;
8. the head-frame first-hit point `p = r d`, if range is valid.

Across all six:
- the number with valid range, and the number of distinct NB1a hypotheses hit;
- landings on environment, PRIMARY, SECONDARY, MARGINAL and EDGE_ONLY;
- the number FULL-safe, CENTER-only-safe, unsafe and with no range;
- the number of duplicate gazes into the same NB1a hypothesis.

No target is declared for any of these.

**U. NB1b comparison** (`evaluation/nb1b-comparison.json`). For each accepted NB1b PRIMARY and SECONDARY seed (P1
H0002, P2 H0003, S1 H0009, S2 H0006, S3 H0007):
- its RGB attention score A;
- its rank in the full unsuppressed raster: 1-based, ordered by A descending, then row, then column;
- the angular distance to the nearest of the six RGB gazes, and which one.

Conversely, each gaze's distance to the nearest NB1b queued seed is recorded. Descriptive only: no gaze is moved
or replaced.

**V. 3-D separation.** For pairs of gazes with valid range: `p_i = r_i d_i` (head frame) and the pairwise
Euclidean separation. Evaluation only.

No accuracy, precision, recall or IoU language is used. Authored identity is reference information, not ground
truth.

## 16. Scientific success semantics

NB1c has **no** target such as "at least N foreground gazes", "at least N PRIMARY hits", "at least N objects" or
"no environment hits". It succeeds scientifically if:
- the fixed RGB-only mechanism produces its deterministic six-gaze answer;
- the truth firewall holds.

All of these are scientifically valid outcomes:
- many gazes on the foreground, or many on the environment shell;
- duplicate gazes on one natural hypothesis;
- gazes on pure appearance / texture changes, or near occlusion boundaries;
- one or more directions with no valid depth;
- strong, or poor, correspondence to the NB1b candidates.

The score is not retuned after evaluation.

## 17. Outputs

**Machine-facing evidence**, `/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1c-rgb-candidate-gaze/`:

| directory | files |
|---|---|
| `source/` | `rgb-source-manifest.json` |
| `selection/` | `attention-score.npz`, `attention-diagnostics.npz`, `candidate-gazes.json`, `nms-rounds.json`, `selection-summary.json`, `selection-opened-files.json`, `rgb-gaze-freeze.json` |
| `evaluation/` | `candidate-evaluation.json`, `nb1b-comparison.json`, `evaluation-opened-files.json` |
| `synthetic/` | `synthetic-report.json` |
| top level | `manifest.json`, `check-summary.json`, `process-log.jsonl` |

**Persistent visuals**, `/home/lvelho/rd/f3d-vision/visuals/natural-bootstrap-1c-rgb-candidate-gaze/`
(Visual Language 1).

Truth classes (nothing is CONTROLLER-TIME; the six gazes have **not** been executed):

| class | products |
|---|---|
| ORACLE INPUT | the accepted coarse RGB sensory proxy |
| DERIVED | the center-surround attention map, candidate scores, NMS, the six gaze directions |
| REFERENCE / EVALUATION | range, NB1a hypotheses, NB1b classes, authored / O_0 information |

- `overview.png`: one strong four-region figure asking *did coarse RGB alone nominate plausible places for the eye
  to spend expensive binocular attention?*
  - A, ORACLE INPUT: the coarse spherical RGB only;
  - B, DERIVED ATTENTION: the complete spherical A(g) field;
  - C, DERIVED GAZES: the six gazes in order 1..6, with their 16.9° exclusion neighbourhoods;
  - D, REFERENCE / EVALUATION: the same six directions revealed against range / NB1a / NB1b context, drawn muted
    so that it does not dominate.
- `rgb-input.png`, `attention-map.png`, `candidate-gazes.png`;
- `center-surround-examples.png`: tangent-plane views of each gaze's 6° center and 6–12° surround, with mu_C,
  mu_S, V_C, V_S, D_RGB and A;
- `candidate-crops.png`: RGB appearance around each gaze;
- `candidate-evaluation.png` (REFERENCE / EVALUATION): the post-freeze descriptors of section 15;
- `attention-score-distribution.png`: the score distribution, its percentiles, the six selected scores and the
  NMS rounds;
- `nb1b-reference-comparison.png` (REFERENCE / EVALUATION, secondary): the NB1b queued seeds against the six
  gazes and their RGB ranks;
- `visuals-manifest.json`.

Glyphs:

| glyph | meaning |
|---|---|
| numbered ink crosshair (1–6) | RGB gaze, in selection order |
| dashed ring, radius D_MIN | exclusion neighbourhood |
| solid ring, radius R_FULL | conservative full-core neighbourhood (disjoint between gazes) |
| dotted ring R_CENTER / thin ring R_SURROUND | receptive-field center / surround edge (tangent-plane views) |
| square outline | nominal 12° measurement core (tangent-plane views) |
| hollow diamond P1, P2, S1–S3 | accepted NB1b queued seeds (reference only) |
| hatched | no range (reference panels only) |

## 18. Checks (`tools/natural_bootstrap/check_nb1c.py`)

The checker keeps literal copies of the constants and recomputes independently, rather than calling the
generator:
- its own grid directions and row weights;
- per-candidate membership of **every** candidate, by the chord formula over a provable superset box: the rows
  within R of the candidate's latitude, and |Δλ| ≤ asin(sin R / cos φ) + 1 column, or the whole row near a pole;
- weighted means and the **two-pass** variance definition;
- D_RGB and A;
- its own greedy NMS with its own tie rule;
- the evaluation descriptors from the pinned reference products.

1. The accepted RGB source's full hash: it equals the pin and the NB1a `manifest.json` and `input-manifest.json`
   records, which are themselves hash-verified.
2. The input contains RGB only: one array, `srgb8`, `uint8`.
3. Exactly 720 × 360 resolution, for the input and every raster.
4. No Blender invocation (process log); the Breadth-1 render directory is unchanged.
5. No controller invocation (process log); no controller module is imported.
6. Selection opened no range, depth or Position.
7. Selection opened no NB1a hypothesis or seed data.
8. Selection opened no NB1b data.
9. Selection opened no Object Index, catalog or reference:
   - its data reads are exactly the RGB file, with 0 violations;
   - the guard self-test blocks a forbidden open;
   - the import and static audit holds (section 12).
10. The sRGB → linear conversion recomputes exactly (all 256 codes), including known values.
11. The spherical cell directions recompute independently.
12. The solid-angle weights recompute, and sum to 4π.
13. R_CENTER = 6°, from the accepted 12° sensor core (hash and `CORE_FOV_DEG` verified).
14. R_SURROUND = 12°.
15. R_FULL independently equals atan(√2 tan 6°), and the corner direction of the square core.
16. D_MIN = 2 R_FULL.
17. The CENTER cell sets recompute for every candidate: the stored pattern equals brute force, with the counts.
18. The SURROUND cell sets recompute for every candidate.
19. The weighted center / surround means (and weights) recompute.
20. V_C / V_S recompute independently (two-pass).
21. D_RGB and A recompute independently.
22. The entire score raster matches, and the attention-score file equals the diagnostics.
23. The numerical score-tie rule is obeyed at every round.
24. The greedy spherical NMS recomputes exactly from the stored raster: picks, order and round records.
25. Exactly K = 6 gazes are selected.
26. All selected pair separations satisfy D_MIN; the stored matrix recomputes.
27. The selected rows, columns, directions and order match the recomputation from the independent raster.
28. The freeze hashes were verified before any evaluation read.
29. Evaluation did not alter the frozen products, and wrote only under `evaluation/`.
30. Reference, range, NB1a and NB1b reads occur only after the freeze verification, and never in selection.
31. Evaluation recomputes: the selected-gaze range, hypothesis, class, footprints, safety, reference, NB1b
    comparison and 3-D separations.
32. No evaluation datum changes the gaze selection or order: the selection products carry no evaluation-derived
    field, and the frozen gazes equal the pure-RGB recomputation.
33. The figures regenerate deterministically (byte-identical).
34. `fov3d/`, the controllers, `tools/fsg_geometry.py`, and the accepted NB1a / NB1b code, run products and
    figures are unchanged.
35. The changed tracked files are only the declared NB1c files and the layout declaration.
36. The synthetic known answers (section 19) pass, in the generator and in the checker's independent
    re-implementation.

Markers: `NATURAL_BOOTSTRAP1C_CHECKS_PASS`, `NATURAL_BOOTSTRAP1C_MUTATIONS_CAUGHT`.

## 19. Synthetic known answers (no Classroom, no Blender)

Synthetic RGB spheres and score rasters:
1. **uniform sphere:** A = 0 exactly everywhere. Deterministic tie-breaking plus NMS still returns six gazes:
   g1 = (0, 0), then the row / column rule.
2. **coherent coloured centre** (a 6° disk of one colour in a uniform surround of another): the designed centre
   is the unique maximum (A ≥ 1e5, since V_C + V_S ≈ 0) and the first gaze.
3. **heterogeneous centre** with the same mean contrast (a checkerboard of two colours averaging the coherent
   colour): V_C is larger and A is lower than in case 2; D_RGB is within 5 % of case 2.
4. **heterogeneous surround:** V_S is larger and A is lower than in case 2.
5. **known sRGB values:**
   - 0 → 0.0;
   - 10 → 10/255/12.92 = 0.003035269835488375;
   - 11 → ((11/255 + 0.055)/1.055)^2.4 = 0.003346535763899161;
   - 128 → 0.21586050011389926;
   - 255 → 1.0.
6. **longitude seam:** a feature translated across the seam. The score raster is the exact column roll
   (bit-identical), the first gaze maps under the roll with the identical score, and every positive-score unique
   pick corresponds.
7. **near-pole:** a candidate in row 0 has every cell of rows 0–11 in its CENTER (all 720 columns, including the
   exact 6° through-pole ties of row 11), in agreement with direct per-cell evaluation. A polar-cap feature
   scores identically across row 0.
8. **solid-angle weighting:** a latitude-split centre at high latitude. mu_C equals the solid-angle-weighted mean
   (direct computation) and differs from the raw cell-count mean by more than 1e-3.
9. **score ties:** an exact tie and a near tie within SCORE_TIE_REL resolve to the smaller row, then column. A
   candidate just outside the tie window does not join.
10. **NMS:** of two high peaks closer than D_MIN, only the higher one survives round 1. A third peak outside
    D_MIN remains available and is chosen.
11. **exact D_MIN boundary:** a candidate at exactly D_MIN remains eligible; one at D_MIN − 1e-9 is suppressed.
12. **decomposition vs. direct definition:** at sampled candidates (poles, seam, equator), the fast evaluation
    agrees with direct per-candidate evaluation of sections 7–8: cell sets exact, A within tolerance.
13. **budget:** an NMS that cannot produce K directions raises (HARD FAIL).

## 20. Corruption / mutation suite (`--corruptions`)

Corruptions are planted in throwaway mirrors or as in-process mutants. They count only from a passing clean
baseline. Each lists its target checks:
- K altered from 6;
- R_CENTER altered; R_SURROUND altered; the R_FULL formula altered; D_MIN altered;
- gamma-space sRGB used directly instead of linear RGB;
- solid-angle weights omitted;
- equirectangular pixel distance used instead of spherical angle;
- one CENTER membership changed; one SURROUND membership changed;
- one center mean altered; one variance altered;
- the variance denominator removed;
- one attention score altered;
- the score tie-break violated;
- one selected gaze moved; two selected gazes reordered;
- two selected gazes closer than D_MIN;
- longitude seam behaviour broken;
- selection made to open:
  - `range-sensory.npz`;
  - NB1a hypothesis data;
  - NB1b serviceability;
  - Object Index / catalog;
- evaluation modifies a gaze;
- evaluation before a valid freeze;
- a Blender command, and a controller command, in the process log;
- a visual pixel altered;
- `fov3d`, controller, NB1a or NB1b accepted code modified; an NB1b run product altered;
- an evaluation descriptor altered;
- a synthetic known-answer case failed.

## 21. Commands, order and cost classes (PROPOSED estimates)

The tools are `tools/natural_bootstrap/nb1c_{spec,attention,run,visuals}.py` and `check_nb1c.py`. The accepted
`nb1a_spec.py` (grid convention) and `nb1a_guard.py` (file-open guard) are reused read-only.

    RUN=/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1c-rgb-candidate-gaze
    VIS=/home/lvelho/rd/f3d-vision/visuals/natural-bootstrap-1c-rgb-candidate-gaze
    .venv/bin/python tools/natural_bootstrap/nb1c_run.py synthetic --run $RUN                  # interactive–batch
    .venv/bin/python tools/natural_bootstrap/nb1c_run.py select    --run $RUN                  # interactive
    .venv/bin/python tools/natural_bootstrap/nb1c_run.py freeze    --run $RUN                  # interactive
    .venv/bin/python tools/natural_bootstrap/nb1c_run.py evaluate  --run $RUN                  # interactive
    .venv/bin/python tools/natural_bootstrap/nb1c_run.py visualize --run $RUN --visuals $VIS   # interactive–batch
    .venv/bin/python tools/natural_bootstrap/check_nb1c.py --run $RUN --visuals $VIS --corruptions --write-summary   # batch

The independent brute-force recomputation took 145 s single-threaded in the synthetic prototype. The checker runs
it once, over a process pool, and caches it across corruptions.

**Order:**
1. Implement the tools.
2. Pass the synthetic known answers, and run the whole pipeline on a scratch synthetic RGB sphere (never the
   Classroom RGB). In that scratch run, evaluation code may be exercised on the accepted NB1a / NB1b products with
   synthetic gaze directions; this is recorded as an incident.
3. Run the layout checker, `scripts/verify_baseline.sh` and `git diff --check`.
4. Commit and push the implementation.
5. Execute exactly **one** canonical application of the frozen RGB algorithm to the accepted RGB proxy. It
   creates no new scene observation.
6. Freeze, evaluate, visualize and check.

`select` refuses to overwrite an existing `selection/`.

## 22. Acceptance, stop conditions and permitted fixes

On successful execution, with all checks passing and the corruptions caught from a passing baseline, the report
`docs/natural-bootstrap/nb1c-rgb-candidate-gaze-report.md` records
`NATURAL_BOOTSTRAP1C_RGB_CANDIDATE_GAZE_COMPLETE` with status **REVIEW PENDING**. It separates PURE RGB SELECTION
from POST-FREEZE REFERENCE / EVALUATION. No ACCEPTED marker is written, and the branch is not merged.

**Stop and return to Luiz/Chat on any of these:**
- an RGB source hash mismatch, an input other than RGB only, or a resolution other than 720 × 360;
- the sensor source changed (hash, or `CORE_FOV_DEG` ≠ 12.0);
- any truth-firewall violation in selection;
- fewer than six gazes;
- a selection decision whose margin lies within the declared numerical agreement tolerance (ambiguous);
- any need to change K, a radius, the score, the tie rule or the NMS, or to add a cue;
- any change to the gazes after the evaluation has been viewed.

**Permitted fixes:**
- Implementation defects inside the new NB1c tools may be repaired before the canonical selection. This includes
  a failure of the row-interval lemma (section 9), which is a defect of the decomposition, not a reason to change
  the definition.
- After the freeze, only these repairs may proceed:
  - presentation and serialization repairs that leave the frozen products unchanged;
  - checker defects in the check, never the criterion, diagnosed and recorded without weakening the check.

Unchanged by this step:
- `fov3d/`, the controllers, the FSG code (including `tools/fsg_geometry.py`) and the accepted renderers;
- the NB1a and NB1b tools, documents, run products and figures;
- the Breadth-1 tools and outputs, and Visual Language 1;
- the 234-object catalog.

No RGB gaze is executed. Controller integration, RGB segmentation, range-based reseeding and Natural Bootstrap-2
are not started.

## 23. Post-stop numerical clarification (authorized by Luiz and Chat before evaluation)

This section is added after the canonical RGB selection and its STOP. Sections 1–22 above are preserved unchanged
as committed at `9a862dc`.

**What happened.**
- The single canonical selection ran at `37c18d8` and was frozen (`selection/rgb-gaze-freeze.json`
  `87a3bab01f55051316ac1eb45b48f394211f4c7a3a317fd0e61c0e52c36f9b37`).
- In NMS round 2, the margin to the next eligible candidate was 1.616e-6.
- Check 27, as implemented, treated twice the section-9 A correctness tolerance (2 × (1e-6 + 1e-9 |A|)) as the
  ambiguity threshold between two competing scores. It flagged the round, and section 22's stop condition applied.
- The STOP was legitimate under that conservative interpretation. It is part of the scientific record
  (report `800af61`).

**Decision (Luiz and Chat), taken before any reference or evaluation input was opened.** The selection is not
numerically ambiguous. Section 9's `|ΔA| <= 1e-6 + 1e-9 |A|` is a deliberately loose pass / fail agreement bound
between a stored value and its independent recomputation. It is not an ambiguity threshold between two competing
scores. The two concepts are now separated:

    E = max over the complete RGB-only raster | A_stored − A_independent |
        (the checker's independent brute-force membership / two-pass implementation)

    for an NMS round with selected score A_max and margin m to the best eligible candidate
    outside the deterministic tie set:

    T = SCORE_TIE_REL * max(1, |A_max|)
    B = 2 E + T

A round is **NUMERICALLY ROBUST** iff:
1. the independent recomputation selects exactly the same candidate for that round; and
2. m > B.

It is **NUMERICALLY AMBIGUOUS** iff either condition fails. Section 22's stop condition "a selection decision whose
margin lies within the declared numerical agreement tolerance (ambiguous)" now means: a round that is numerically
ambiguous by this definition.

Check 27 is repaired to implement this. It:
- recomputes the complete score raster independently;
- computes E;
- recomputes the greedy NMS independently, and requires its six picks and order to equal the frozen six;
- for every round, computes T and B and requires m > B whenever a runner-up exists. This holds for both the margin
  replayed on the stored raster and the margin on the independent raster;
- reports m, E, T, B and m / B for every round.

The checker gains two probative corruptions:
- E is raised until 2 E + T exceeds a round margin;
- the independent recomputation is made to select a different round winner (checker-only, in-process).

The observed winner and margin are not hard-coded.

**Unchanged:**
- the A correctness tolerance (`|ΔA| <= 1e-6 + 1e-9 |A|`; check 22);
- `SCORE_TIE_REL = 1e-12`, every sensor radius, K = 6, the score and the NMS definitions;
- every other check;
- `nb1c_spec.py`, `nb1c_attention.py`, the frozen selection products and the six gaze positions and their order.

This clarification concerns numerical reproducibility only. It does not alter the attention mechanism, and nothing
is reselected.
