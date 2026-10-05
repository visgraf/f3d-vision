# Active Bootstrap-1d — Safe-Forward Natural RGB Correspondence — contract

**Status: CONTRACT (committed before any implementation, synthetic matcher execution, canonical matching or inspection
of natural correspondence results).**

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (never the legacy `visgraf/fov-3d-vision`) |
| base | `56840caab332bb203918c776acab20d9a6ef4c17` (accepted `main`: AB1c accepted at `45b08ae`, post-AB1c roadmap) |
| branch | `active-bootstrap/ab1d-safe-forward-natural-correspondence`, isolated worktree |
| completion marker | `ACTIVE_BOOTSTRAP1D_SAFE_FORWARD_NATURAL_CORRESPONDENCE_COMPLETE` (no ACCEPTED marker; status REVIEW PENDING) |
| run (machine evidence) | `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1d-safe-forward-natural-correspondence/` (`RUN`) |
| visuals | `/home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1d-safe-forward-natural-correspondence/` (`VIS`) |

Every numerical value in this contract is a **declared design constant** or a **PROPOSED** expectation. Nothing here is
MEASURED. The only design-time computation was calibration-only, at synthetic gazes (section 29).

## 1. One causal question

> In the favorable safe-forward regime established by AB1c, can a simple natural RGB matcher recover the right-eye
> spherical epipolar correspondence accurately enough to provide useful local metric measurements?

- The PRIMARY question is **correspondence precision**: the angular error of the natural right-eye estimate along the
  physical epipolar plane, against the accepted AB1c perfect correspondence used as a post-freeze benchmark.
- Geometry is held fixed: the accepted AB1b spherical epipolar geometry, unchanged. AB1d tests CORRESPONDENCE, not
  geometry.
- AB1d is **not**:
  - a planar-vs-spherical comparison;
  - a head-motion, controller or attention experiment;
  - an SGBM, learned-stereo, feature-network or SGM / dynamic-programming experiment;
  - a parameter sweep.
- ONE deliberately simple matcher (sections 7–13). If it is insufficient, the report explains why and stops. It is not
  replaced by a more elaborate matcher in AB1d.

## 2. Provenance and branch

- Pull: `origin/main` = `56840ca`. AB1d branches from it in a dedicated isolated worktree. The shared checkout is not
  switched or mutated; only the gitignored `RUN` and `VIS` trees are written there.
- This contract, with the layout checker's AB1d declaration, is commit 1 of the branch. The implementation follows in
  a separate commit, then the canonical run from that clean, pushed commit, then the report.

## 3. Source pins (verified by `source`; a mismatch is a STOP)

### 3a. The accepted AB1c observations (reused EXACTLY; never re-rendered)

AB1c run `A1C = /home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1c-safe-forward-planar-vs-spherical/`:

| file | sha256 |
|---|---|
| `manifest.json` | `21640f6a56474f9ed171d37ceb13571a56499ac805b1b1bbec09c6808a0d378a` |
| `selection/safe-forward-freeze.json` | `72d7e4b8497cabcc2f828a50b894c613790915205bbb8081ed4ce43d702c7ec6` |
| `selection/selected-gazes.json` | `85c94558119930e3bfbf247cf515361265ecc8fa12ca43d5eb98f9c7158b5b98` |
| `observations/gaze-1/acquisition/calibration.json` | `ae56ef338561a9d23d4208e36fb88862adb08e6bd8f773651ed3aa9e83224ebf` |
| `observations/gaze-1/acquisition/rgb-observation.npz` | `d6e2a532acf1534ed305ad63447b30b35645051a350922cbcec14dbb5388f47f` |
| `observations/gaze-1/acquisition/acquisition.json` | `d1ca822aa2ca49e32fd59466736d03408e7549cac1a452ded6bc19806d32c27b` |
| `observations/gaze-2/acquisition/calibration.json` | `ab348665b6c86443145cfa448ac488ec101eab41277d47b0d93c3eaabfd37ec7` |
| `observations/gaze-2/acquisition/rgb-observation.npz` | `297c5bd689cde4a5bf9b01b53e4b643719feff6f654a25a470a2e8b627bca43d` |
| `observations/gaze-2/acquisition/acquisition.json` | `59443c35284625fca1792b3bfe5cabb22e6635cb27c05bd274ab7501e93beeac` |
| `observations/gaze-3/acquisition/calibration.json` | `085ff33204b84c3d7b05a92c3099bef600dd698bf6e6ab209cb0e5bfe748accd` |
| `observations/gaze-3/acquisition/rgb-observation.npz` | `5924f94656b6bf3536ed986f2d47433331e201d7ea911c3df7f1ef52c57a170c` |
| `observations/gaze-3/acquisition/acquisition.json` | `68fd96d8d541095ff8623b98dd74e22a8161bf593611739e6ea5cad126a52abd` |

`source` also verifies that:
- each pinned file's hash equals the AB1c `manifest.json` entry;
- each `acquisition.json` records the pinned RGB / calibration hashes and the frozen gaze;
- the AB1c selection freeze and `selected-gazes.json` list exactly the three gazes of section 4.

### 3b. Accepted AB1c products opened ONLY after the geometry freeze (REFERENCE / EVALUATION)

| file | sha256 |
|---|---|
| `oracle/correspondence-freeze.json` | `e7f06f53d13707c23fbd1dd3d638090043be7ea53662c41c1524143769bf8733` |
| `oracle/gaze-1/oracle-correspondences.npz` | `e83eaa7b537abaa4def50def64d0d36bf034d270baa3f4e7ce6cfb0a7512b4a6` |
| `oracle/gaze-2/oracle-correspondences.npz` | `fd4568d59f3b7a40aef6c11442961749e45a8c3b6c1b1fa53c8934dd636b8831` |
| `oracle/gaze-3/oracle-correspondences.npz` | `67d433311f1f940637573c9135d6947bad8363411cb45e52412f070874c20c73` |
| `freeze/geometry-freeze.json` | `1b7e2207af58a777f04b23903d1da25bca2a3cf39ccd454d8813491f2e4a4b9a` |
| `spherical/gaze-1/epipolar-result.npz` (perfect spherical reconstruction) | `3e5024f3a75a34819f742c231b3b448ac6b8486a840f17c9c5f780798c52cd98` |
| `spherical/gaze-2/epipolar-result.npz` | `d2306f9c200a11e749bf59d71b535a2f4c8a32e08850618901b9402412fee4e2` |
| `spherical/gaze-3/epipolar-result.npz` | `f1de4f1d6be91880067446ad8a104f875dd7e4757c2c5176be2410ed92d0b561` |
| `observations/gaze-1/evaluation_only/reference-observation.npz` (Position) | `7c458254960befefbfef160e0904dc8ab9c34bb1d3791d8f59fd55403b323f2e` |
| `observations/gaze-2/evaluation_only/reference-observation.npz` | `c8b1833ef4df720a0252b89c6886ba6788be4d94f877cfd8ba0bc4781b9e47b6` |
| `observations/gaze-3/evaluation_only/reference-observation.npz` | `740d7ad78f9afc7eb867e20df186bf40b964e31a840a5ba2e85dd4bdcd81e5d0` |
| `evaluation/gaze-{1,2,3}/evaluation-result.npz` (AB1c `P_truth`; checker cross-check only) | `12270a99…`, `bd937015…`, `bfbf300c…` (full hashes in the AB1c manifest) |

The AB1c visuals manifest `a533366986f6027114b694562d92f7c59bfc47fe486ff7bde0773f07f6b45311` and the AB1c run manifest
are verified unchanged by `source` and by the checker. AB1d writes nothing under the AB1c run or visuals.

### 3c. Accepted code reused read-only (sha256 at the base)

| file | sha256 | use |
|---|---|---|
| `tools/fsg_geometry.py` | `ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54` | `rays_h`, `project_h`, `validate_calibration`, `world_to_head` |
| `tools/fsg_stereo.py` | `faebf0f1b3acbfde60b08830a57213bf29c708c3aa274e493ade0042eb0545e9` | `linear_to_u8`, `MIN_LOCAL_STD_U8`, `BLOCK_SIZE` (constants and the photometric conversion only; no SGBM call) |
| `tools/natural_bootstrap/nb1a_guard.py` | `29ebca57be9e977def7a94ea45a7b0cff0f22a8b1d86b40f740f132491ebe99d` | allowlist file-open guard |
| `tools/active_bootstrap/ab1b_spec.py` | `1634e455a61879934545a1fa634a72cbb2b8ca74fd83a6ba3a977412be0e497d` | AB1b constants |
| `tools/active_bootstrap/ab1b_geometry.py` | `a125dd9cc666120219e0421a09a380353d2304ed0f09681a1655962444572538` | `theta_phi`, product schema, `compute_epipolar` |
| `tools/active_bootstrap/ab1b_visuals.py` | `6dd4a203b1847e9d5f0f984c2a1727859aa035ad00adead79849bd484ca833ee` | figure helpers |
| `tools/active_bootstrap/ab1c_visuals.py` | `28054811eca774883753c2499d135cdabae37b32f6f014432bf1057dcab71a30` | figure helpers |
| `tools/active_bootstrap/ab1c_spec.py` | `53d1b7228b30883db715f3fc33a65893aa7708656c2881f2a31eef1a3ac77b1a` | imported by `ab1c_visuals` |
| `tools/active_bootstrap/ab1c_planar.py` | `1528ee92af48c5a13b621d300fe0a78dedc57f27181959d40505f2f9b19e6227` | imported by `ab1c_visuals` (figures only; no planar geometry runs in AB1d) |
| `tools/visual_language/style.py` | `c379a2a31c9112d22bbe8989324d2ff74608c669fe84d58905509b4d62264053` | Visual Language 1 |
| `tools/classroom_oracle/breadth1_visuals.py` | `61683aea17993da09bfddce4ed13d48da47d710d1630e40c6bdcc7a6f6d2144c` | imported by `ab1b_visuals` |

No accepted file is modified.

## 4. No new observation

AB1d reuses EXACTLY the three accepted AB1c binocular observations:

| gaze | row, col | yaw, pitch (°) |
|---|---|---|
| gaze-1 | 191, 322 | −18.75, −5.75 |
| gaze-2 | 166, 373 | +6.75, +6.75 |
| gaze-3 | 190, 397 | +18.75, −5.25 |

There is no Blender process, render or rerender, and no new gaze or attention selection. Head motion is excluded: one
fixed head, the AB1c calibrations as stored.

## 5. Truth firewall

- **Matcher-time inputs, per gaze, exactly two files:** `A1C/observations/gaze-N/acquisition/calibration.json` and
  `A1C/observations/gaze-N/acquisition/rgb-observation.npz`. They are read in place under an allowlist `OpenGuard`
  (`nb1a_guard`).
- The RGB observation must contain exactly the arrays `rgb_L` and `rgb_R` (640 × 640 × 3, finite). Any other array (e.g.
  a Position, depth or instance field) is rejected before matching.
- **Forbidden at matcher and geometry time:** Position, Object Index, the AB1c oracle products and freezes, AB1c
  evaluation, planar results, truth errors, the instance catalog, Blender EXRs, depth and controller state. The guard
  refuses every data read outside the allowlist and records it as a violation.
- Each stage record reports `position_reads`, `object_index_reads`, `oracle_reads` and `evaluation_reads`. For the
  match and geometry stages each must be 0.
- The geometry stage reads exactly the calibration and the frozen natural product (accepted AB1b semantics).
- Post-freeze, the evaluation stage additionally reads the RGB observations (oracle-on-curve scoring), the AB1c oracle
  products, the AB1c perfect spherical results and Position (section 17). It reads nothing else.

## 6. Representation (fixed; accepted AB1b convention)

- Head frame: +X right (the baseline), +Y up, −Z forward. Eyes at ∓B/2 on X, B = 0.063 m.
- θ(d) = atan2(√(d_y² + d_z²), d_x) (from +X); φ(d) = atan2(d_y, −d_z) (`ab1b_geometry.theta_phi`).
- The direction of (θ, φ) is **d(θ, φ) = (cos θ, sin θ sin φ, −sin θ cos φ)**.
- Pixel rays come from the accepted `fsg_geometry.rays_h`. Pixel centres are integer; image rows are v, columns u. The
  left nominal raw core is u, v = 192..447 (`left_core_row/col` = v − 192, u − 192).
- One left raw-core ray defines one physical epipolar plane, which contains the +X baseline. The match is

      p_L -> d_L -> (θ_L, φ_L) -> search the ORIGINAL right tangent image along that plane -> θ_R estimate
          -> uv_R estimate -> accepted AB1b spherical triangulation

- There is no global spherical panorama or stereo raster, no planar rectification and no planar matcher. The right image
  is the original saved raw tangent image.

## 7. Photometric input (frozen)

- `U = fsg_stereo.linear_to_u8(rgb)`: the accepted fixed sRGB-curve transform to uint8, with no per-eye normalisation.
- `G = 0.2126 U_R + 0.7152 U_G + 0.0722 U_B`, in float64 and **not re-rounded**, on the 0–255 scale. These are the
  luminance coefficients of the accepted FSG code (`fsg_stereo.refine_disparity`).
- **Recorded fact, not a deviation.** The accepted FSG SGBM path and its `MIN_LOCAL_STD_U8` texture test used OpenCV
  `COLOR_RGB2GRAY` (BT.601 weights, u8). AB1d follows the handoff's frozen choice: the u8 conversion followed by the
  Rec. 709 coefficients above. The texture threshold keeps its u8-scale units.
- No histogram equalisation, CLAHE, adaptive exposure, learned normalisation or image-specific tuning.

## 8. Local angular patch (frozen)

- δ = atan(1 / f), where f = `K[0][0]` of the calibration (1217.8386501404907 px; δ ≈ 8.2112e-4 rad).
- PATCH = 5 × 5: offsets i (along θ) and j (along φ), each in {−2, −1, 0, +1, +2}. For a centre (θ_c, φ_c):

      θ_ij = θ_c + i δ
      φ_ij = φ_c + j δ / sin θ_c

  These are equal local angular spacings: a φ step at polar angle θ subtends sin θ · Δφ.
- Each of the 25 directions d(θ_ij, φ_ij) is projected into the relevant raw camera s:
  h = K_s R_hc_s^T d, (u, v) = (h_0 / h_2, h_1 / h_2), with h_2 > 1e-12 (in front).
- The gray image is bilinearly sampled. A sample is **inside** iff 0 ≤ u ≤ W − 1 and 0 ≤ v ≤ H − 1. With
  x0 = min(⌊u⌋, W − 2), y0 = min(⌊v⌋, H − 2), f_x = u − x0, f_y = v − y0:

      value = (1 − f_y)[(1 − f_x) G[y0, x0] + f_x G[y0, x0+1]] + f_y[(1 − f_x) G[y0+1, x0] + f_x G[y0+1, x0+1]]

- All 25 samples must be inside the raster, or the patch does not exist. Sample order is i-major, j-minor (25-vector).
- The left patch is centred at (θ_L, φ_L) and uses sin θ_L. A right patch is centred at (θ_c, φ_L), the matcher's exact
  epipolar plane, and uses sin θ_c.
- No truth enters.

## 9. Right epipolar search locus (frozen; exact formula)

For each left core pixel, with d_L = `rays_h(eye_L, uv_L)` and b̂ = (1, 0, 0):

1. **Plane normal:** n = (b̂ × d_L) / ‖b̂ × d_L‖ = (0, −d_z, d_y) / √(d_y² + d_z²).
2. **Raw right epipolar line:** l = K_R^{-T} R_hc_R^T n. A right pixel q = (u, v, 1) has its ray in the plane iff
   lᵀq = 0. This holds because `rays_h` gives d_R ∝ R_hc_R K_R^{-1} q, and n · d_R = 0 ⇔ (K_R^{-T} R_hc_R^T n)ᵀ q = 0.
3. **Line origin (the infinite-range point):** h_∞ = K_R R_hc_R^T d_L, q_∞ = (h_∞[0], h_∞[1]) / h_∞[2]. It requires
   h_∞[2] > 1e-12; otherwise there is no search support. q_∞ lies on l, and its ray is parallel to d_L, so θ_R = θ_L.
4. **Line direction:** t̂ = (l_1, −l_0) / √(l_0² + l_1²), oriented so that θ_R increases along +t̂. The orientation is
   the sign of t̂ · ∂q/∂θ, where ∂q/∂θ is the image displacement of d_L moving along e_θ = ∂d/∂θ =
   (−sin θ_L, cos θ_L sin φ_L, −cos θ_L cos φ_L). With h' = K_R R_hc_R^T e_θ:
   ∂q/∂θ = (h'[:2] h_∞[2] − h_∞[:2] h'[2]) / h_∞[2]².
5. **Line coordinate:** q(s) = q_∞ + s t̂, in raw pixels (Euclidean). s > 0 ⇔ θ_R > θ_L (positive parallax).

**Admissible candidates.** These are geometry-only conditions. No scene depth interval, oracle range or Position-derived
bound is used. Candidate k is the integer sample s_k = k · 1.0 px for every integer k ≥ 1 with q(s_k) inside the raster
chord (0 ≤ u ≤ W − 1, 0 ≤ v ≤ H − 1). The candidate is **admissible** iff:
- its ray d_k = `rays_h(eye_R, q(s_k))` is finite;
- it lies in the same half-plane: cos(φ_k − φ_L) > 0;
- θ_k > θ_L;
- the AB1b triangulation is finite and positive: den = cot θ_L − cot θ_k ≥ `ab1b_spec.DEN_EPS`, and ρ = B / den finite and
  > 0, which gives positive forward ranges ρ / sin θ for both eyes;
- its complete right patch (section 8, centre (θ_k, φ_L)) exists.

The whole physically admissible segment is searched. `candidate_count` = number of admissible candidates.

## 10. Candidate sampling and tie rule (frozen)

- Spacing: **1.0 raw pixel** (Euclidean, along the line), at s_k = k, k = 1, 2, …. s = 0 (infinite range) is excluded.
  The last sample is the largest k whose centre lies in the raster chord.
- Candidates are ordered by increasing k, which is increasing θ_R (nearer range).
- **Tie rule:** scores within **TIE_EPS = 1e-12** (absolute, ZNCC units) of the maximum are tied. The earliest (smallest
  k) tied candidate is chosen. The same rule orders the distinct peaks (section 12).
- The spacing is not tuned after seeing Classroom.

## 11. Texture and ZNCC (frozen)

- **Texture:** the population standard deviation (ddof 0) of the 25 patch samples.
  `MIN_LOCAL_STD_U8 = 0.5` (`fsg_stereo`) is the **only** texture-support threshold.
  - Left patch std < 0.5: natural match invalid, reason `LOW_TEXTURE`.
  - Right candidate patch std < 0.5: that candidate is invalid (no score).
- **ZNCC** of left patch a and right patch b:
  `Σ (a − ā)(b − b̄) / √(Σ (a − ā)² · Σ (b − b̄)²)`, in float64. Higher is better.
- There is no correlation threshold, no uniqueness / ratio acceptance threshold and no left-right consistency test.
  Confidence values are descriptive.
- **Validity:** a left pixel has `valid_match = True` iff:
  - its left patch exists and is textured;
  - it has at least one admissible candidate whose right patch is textured.

  The matcher then returns its best estimate. Reasons for invalidity, in priority order: `LOW_TEXTURE`,
  `NO_SEARCH_SUPPORT` (no admissible candidate), `NO_TEXTURED_CANDIDATE`.

## 12. Distinct peaks / ambiguity (frozen)

- A **local peak** is a valid (scored) candidate k whose score is ≥ the score of each valid adjacent candidate (k − 1,
  k + 1) minus TIE_EPS. Missing or invalid neighbours impose no condition.
- **TOP_K = 8 distinct peaks**, chosen greedily. Each round takes, among the remaining local peaks, the earliest k whose
  score is within TIE_EPS of the remaining maximum. All local peaks closer than **3 raw pixels** (|k − k_accepted| < 3)
  are then removed. Two peaks are distinct only if their line coordinates differ by at least 3 px.
- The first distinct peak is the best candidate (section 10). `second_peak_zncc` is the second distinct peak's score.
  `peak_margin` = best − second; it is NaN if there is no second peak.
- For each of the ≤ 8 peaks, store: line coordinate s, `uv_R`, θ_R and ZNCC. Unused slots are NaN.
- The margin is a descriptive ambiguity signal. It is never thresholded.

## 13. Sub-pixel refinement (frozen)

Only the best discrete candidate k is refined. With S₋, S₀, S₊ the scores at k − 1, k, k + 1:
- `peak_curvature` = D = S₋ − 2 S₀ + S₊, in ZNCC per sample². It is NaN when a neighbour is missing or invalid.
- **No refinement** if: the best candidate is at a search boundary (k − 1 or k + 1 not admissible); either neighbour is
  invalid; or D ≥ 0 (not a proper local maximum). The discrete candidate is retained.
- Otherwise, the parabola vertex offset is x* = (S₋ − S₊) / (2 D), clipped to **±0.75 sample**: the accepted FSG
  maximum local refinement. For the global discrete maximum, |x*| ≤ 0.5 holds mathematically, so the bound is
  declared and applied but never active. It is retained as specified.
- s_est = k + x* · 1.0; `uv_R_est` = q(s_est), which lies exactly on the physical epipolar locus;
  θ_R_est = θ(`rays_h(eye_R, uv_R_est)`).
- Store the discrete estimate, the refined estimate, the offset (samples) and the curvature.
- No iteration, Gauss-Newton or second optimisation stage.

## 14. Matcher output

**Full-core record** (`match/gaze-N/matcher-record.npz`), all 65,536 left nominal raw-core pixels in row-major core
order:
- position: `left_core_row`, `left_core_col`, `uv_L`;
- validity: `valid_left_patch`, `valid_left_texture`, `valid_match`, `reason` (0 VALID, 1 LOW_TEXTURE,
  2 NO_SEARCH_SUPPORT, 3 NO_TEXTURED_CANDIDATE, 4 LEFT_PATCH_OUTSIDE);
- search line: `candidate_count` (admissible), `textured_candidate_count`, `k_first`, `k_last`, `q_inf`, `line_dir`,
  `line_l`;
- angles: `theta_L`, `phi_L`, `theta_R_discrete`, `theta_R_est`;
- estimates: `k_best`, `uv_R_discrete`, `s_est`, `uv_R_est`;
- scores: `best_zncc`, `second_peak_zncc`, `peak_margin`, `peak_curvature`, `refined`, `refinement_offset_samples`;
- the top-8 distinct peaks: `peak_count`, and per slot `peak_s`, `peak_uv_R`, `peak_theta_R`, `peak_zncc`;
- `left_patch_std_u8`.

It has no oracle field and no Position, Object Index, range, depth or semantic identity.

**Truth-stripped natural correspondence product** (`match/gaze-N/natural-correspondences.npz`): exactly the accepted
AB1b schema `left_core_row`, `left_core_col` (int32), `uv_L`, `uv_R` (float64; `uv_L` = the raw left pixel centre),
for the valid natural matches only, in core order. `uv_R` = `uv_R_est`. `ab1b_geometry.validate_product` must accept
it. Any extra key (depth, XYZ, identity) is rejected.

## 15. Run order, freezes and guards

    source -> synthetic -> match -> freeze-correspondence -> spherical -> freeze-geometry -> evaluate -> visualize

- `match`:
  - runs only from a clean, pushed implementation commit, after a passing `synthetic` report from that same commit;
  - runs once and refuses to rerun;
  - guard allowlist: the six files of section 5 (per gaze) and its own output directory.
- `freeze-correspondence` hashes the three records, products, summaries and guard records, before geometry.
- `spherical` reads exactly the calibration and the frozen product per gaze. It uses the accepted AB1b
  `compute_epipolar`, does not import cv2, and runs no planar geometry.
- `freeze-geometry` hashes the geometry results before any oracle or Position product is opened.
- `evaluate` verifies both freezes, then opens the AB1c benchmark products (section 3b). It marks the ordered guard
  events `freezes_verified` → `reference_access_begins`.
- The match and geometry stages must record Position, Object Index, oracle and evaluation reads all equal to 0.
- Every canonical step (`source`, `match`, `freeze-correspondence`, `spherical`, `freeze-geometry`, `evaluate`) runs
  exactly once, from the clean pushed implementation commit, and is logged in `process-log.jsonl`.

## 16. Spherical geometry (accepted AB1b; unchanged)

`ab1b_geometry.compute_epipolar(calibration, natural product)`: natural uv_L / uv_R → physical rays → θ / φ → the direct
triangulation ρ = B / (cot θ_L − cot θ_R) → natural metric points P_nat, plus the ray-ray cross-check and conditioning.
There is no modification of AB1b and no planar geometry.

## 17. Post-freeze oracle benchmark (REFERENCE / EVALUATION)

- The AB1c perfect correspondence is a **benchmark only**. The matcher does not know which left pixels have oracle
  matches.
- Per gaze, the 65,536 left-core pixels are classified into:
  - **ORACLE VISIBLE + NATURAL VALID**: evaluable;
  - **ORACLE VISIBLE + NATURAL INVALID**: natural miss, by reason;
  - **NO ORACLE + NATURAL VALID**: natural output, not scored as correct or incorrect;
  - **NO ORACLE + NATURAL INVALID**.
- Non-oracle pixels are never counted as matcher failures.

## 18. PRIMARY metric — angular correspondence error

On the evaluable set: **e_θ = θ_R_est − θ_R_oracle**, where θ_R_oracle = θ(`rays_h(eye_R, uv_R_oracle)`) from the AB1c
product.

Per gaze, report:
- counts: oracle correspondences; natural valid (full core); evaluable;
  coverage = evaluable / oracle correspondences; natural-valid non-oracle;
- signed e_θ: min, p05, median, p95, max;
- |e_θ|: median, p90, p95, p99, max.

Depth error is not the primary judgement.

## 19. Pixel-equivalent error

- **Local scale (preferred definition).** ORACLE-ON-CURVE is the location q_oc = projection of d(θ_R_oracle, φ_L) into
  the right raw image (section 20). Its line coordinate is s_oc = (q_oc − q_∞) · t̂. The local scale is
  dθ/ds = θ(q(s_oc + 0.5)) − θ(q(s_oc − 0.5)): radians per raw line pixel, from the calibrated right camera.
- **Pixel-equivalent error** = e_θ / (dθ/ds). This is evaluation only.
- Also reported, clearly labelled:
  - the focal approximation f · e_θ;
  - the direct line-coordinate difference s_est − s_oc.
- Descriptive fractions among evaluable matches: |error| ≤ 0.10, 0.25, 0.50 and 1.00 pixel-equivalent. These are not
  acceptance thresholds.

## 20. Cost-landscape diagnostics (post-freeze; REFERENCE / EVALUATION)

For each evaluable pixel:
1. θ_R_oracle, as above.
2. **ORACLE-ON-CURVE** = d(θ_R_oracle, φ_L), projected into the right raw image. It lies on the matcher's exact
   epipolar plane, which removes the AB1c oracle's tiny φ skew from the photometric diagnosis without changing e_θ. The
   perpendicular distance of q_oc from the line is recorded as a check (numerically 0).
3. The SAME frozen ZNCC is evaluated with the right patch centred at (θ_R_oracle, φ_L). It is *unscorable* if that patch
   does not exist or is below the texture threshold.

Report:
- oracle-on-curve ZNCC; best natural ZNCC; oracle − best;
- **at / above best**: oracle ≥ best − 1e-9;
- **oracle peak rank**: the smallest r ∈ 1..8 with |s_peak_r − s_oc| ≤ **1.5 px** (half the 3-px peak separation, so at
  most one peak matches), else "> 8";
- the counts of oracle locations outside the admissible segment and of unscorable oracles;
- fractions with the oracle in the top 1, top 3, top 5, top 8 and worse than top 8;
- the local oracle cost shape: ZNCC at s_oc + o for o ∈ {−1.0, −0.5, 0, +0.5, +1.0} px along the line, where patch
  support permits. Report the median score per offset, the median of S(o) − S(0), and the fraction with S(0) the
  maximum of the five.

These diagnostics never change the matcher.

## 21. Secondary metric consequence

On evaluable natural matches, the frozen natural spherical reconstruction P_nat is compared with:
- **A.** the accepted AB1c perfect spherical reconstruction P_epi (matched by core row / col);
- **B.** the post-freeze Blender Position reference P_ref = `world_to_head(Position_L[v, u])`. The checker
  cross-checks it against AB1c `P_truth`.

Quantities, with O_L the left eye:
- 3-D error ‖P_nat − P_ref‖;
- signed radial error ‖P_nat − O_L‖ − ‖P_ref − O_L‖ (along the left line of sight);
- relative range error |radial| / ‖P_ref − O_L‖.

Per gaze, report the median, p90, p95, p99 and max of the 3-D error, |radial| and the relative range error, and the
signed radial p05 / median / p95. Descriptive fractions of 3-D error ≤ **12 mm** (the persistent-map support radius of
the accepted active-growth machinery), ≤ 25 mm and ≤ 50 mm. None is an acceptance threshold. The natural κ median is
reported as conditioning context.

## 22. Confidence diagnostics (descriptive)

Error is stratified on the evaluable set, per gaze and pooled, by quartiles (q25 / q50 / q75 of the evaluable values;
bins ≤ q25, (q25, q50], (q50, q75], > q75) of:
- `peak_margin` (NaN: a separate "single peak" stratum);
- `left_patch_std_u8`;
- `best_zncc`;
- `peak_curvature` (NaN: a separate "unrefined" stratum);
- `candidate_count`.

Per stratum: count, median |px-equiv|, p90 |px-equiv|, fraction ≤ 0.25 px and ≤ 1.0 px, and oracle top-1 fraction.
There is no calibrated confidence model and no threshold.

## 23. Scientific outcome semantics

No data-dependent acceptance threshold is declared. The report reads the measurements against these qualitative
outcomes. They may coexist spatially; the report states the dominant measured pattern.

1. **PRIMITIVE MATCHER IS ALREADY USEFUL.**
   - The oracle is usually at or near the favored photometric peak.
   - Angular error is concentrated near zero.
   - Useful coverage is substantial.
   - The metric geometry is often compatible with active-growth scales.
2. **SEARCH / REFINEMENT LIMITED.** The oracle-on-curve score is usually the best or among the best few, but the
   estimate remains noticeably displaced.
3. **AMBIGUITY LIMITED.** The oracle often belongs among several near-equal peaks, or is not the preferred peak in
   repetitive or weakly textured regions.
4. **PHOTOMETRIC MODEL LIMITED.** The oracle location is systematically not favored even when texture is adequate and
   ambiguity is low.
5. **COVERAGE LIMITED.** Too many oracle-visible pixels produce no natural estimate, through texture or search support.

The matcher is not repaired after the canonical result.

## 24. Synthetic known answers (before the canonical match)

**Synthetic instrument:** `make_calibration('full', −8, 9, 2.10, 0.063, 'baseline_projected')`, the AB1c synthetic
gaze "left-up". Its left core has φ ≈ 3–15°, never near 0.

**Synthetic scene (analytic, no Blender):**
- A smooth aperiodic texture T(d) on directions: 128 + Σ of 12 sinusoids of fixed seeded wave-vectors. Angular
  wavelengths are 8–32 px; the amplitude keeps T in [0, 255].
- The left image is G_L(p) = T(d_L(p)). The right image is G_R(q) = T(d(θ_R − Δθ, φ_R)) with (θ_R, φ_R) = θ / φ of
  `rays_h(eye_R, q)`.
- Every left direction then has its true right match at (θ_L + Δθ, φ_L): a physical surface of constant binocular
  parallax. The true line coordinate s_true follows from section 9.
- With Δθ = 40 δ, the fractional parts of s_true spread over [0, 1); the test pixels are binned by fractional part.

The tests use software / numerical tolerances. They are not scientific success thresholds.

| # | case | known answer / tolerance |
|---|---|---|
| 1 | epipolar-line geometry | projections of points on the left ray (ranges 0.3–50 m) lie on l within 1e-9 px; q_∞ on l within 1e-9 px; l parallel to the independent fundamental-matrix line F q_L (F = K_R^{-T} [T]_× R K_L^{-1}) within 1e-9 rad |
| 2 | spherical equivalence | every candidate ray has \|φ_k − φ_L\| ≤ 1e-12 rad; θ_k strictly increasing in k |
| 3 | exact textured match (frac(s_true) within 0.02 of an integer) | discrete k = round(s_true) for all; \|s_est − s_true\| median ≤ 0.05 px, p95 ≤ 0.20 px |
| 4 | sub-pixel match (frac ≈ 0.25, 0.50, 0.75, ± 0.02) | discrete k ∈ {⌊s_true⌋, ⌈s_true⌉}; refined error median ≤ 0.08 px and p95 ≤ 0.20 px per bin; refined median error < discrete median error |
| 5 | affine photometric gain / offset (G_R' = 0.6 G_R + 30) | identical k_best and refined s_est (≤ 1e-9 px); ZNCC equal within 1e-12 |
| 6 | flat patch (a constant 48 × 48 block in the left image) | every pixel whose patch lies in the block: LOW_TEXTURE, `valid_match` False |
| 7 | repeated texture (period 7 px along θ) | ≥ 3 distinct peaks for ≥ 90 % of pixels; median peak margin ≤ 0.02; first-two-peak spacing within 1.5 px of a multiple of 7. Not required to choose the truth |
| 8 | search boundary (Δθ = 0.4 δ: truth before k = 1) | every pixel with k_best = k_first: `refined` False, `uv_R_est` = `uv_R_discrete` exactly |
| 9 | wrong epipolar-plane sign (plane and patch φ from atan2(−d_y, −d_z)) | known-answer failure: median \|s_est − s_true\| > 5 px or valid fraction < 0.5 |
| 10 | wrong right-camera transform (R_hc_R transposed) | known-answer failure, as 9 |
| 11 | wrong baseline axis (b̂ = +Y) | known-answer failure, as 9 |
| 12 | altered patch size (7 × 7) | the checker's independent recomputation flags the mutated records and passes the unmutated ones |
| 13 | altered candidate spacing (0.5 px) | as 12 |
| 14 | altered texture threshold (2.0) | as 12 (the scene includes a low-contrast region with patch std in (0.5, 2)) |
| 15 | altered peak-separation rule (2 px) | as 12 |
| 16 | altered sub-pixel bound (0.40) | as 12 |
| 17 | truth-bearing matcher input (an extra `position_w_L` array) | rejected before matching |
| 18 | Position / oracle access during matching | refused by the guard (PermissionError, recorded violation) |
| 19 | natural product schema (extra depth / XYZ / identity field) | rejected by `validate_product` |
| 20 | spherical geometry consumes the natural product unchanged | `compute_epipolar` accepts it; θ_R equals θ_R_est within 1e-12 rad; \|φ_R − φ_L\| ≤ 1e-12; P_nat on the left ray within 1e-9 m |
| 21 | photometric conversion | G = Rec. 709 of `linear_to_u8` on known RGB values (exact) |
| 22 | ZNCC, tie rule, distinct peaks, parabola | ZNCC equals the direct formula (1e-12); exact ties pick the earliest; a hand-made score curve yields its known peak list; a sampled quadratic yields its exact vertex (1e-12) |
| 23 | execution strategy | 1 thread and the declared thread count give byte-identical records |
| 24 | end-to-end through linear RGB → u8 → gray | the same scene encoded as linear RGB: k_best = round(s_true) for ≥ 95 % of the integer bin |

If a synthetic case fails before the canonical match, the cause is diagnosed. An implementation defect is fixed. A
tolerance found to be wrong for a correct implementation is corrected only before the canonical match, with the reason,
in a dated clarification section of this contract (as AB1c section 23).

## 25. Visuals (Visual Language 1)

Persistent figures in `VIS`, drawn deterministically (the checker regenerates them byte-identically). Truth badges are
text, never colour alone:
- ORACLE INPUT: the rendered RGB;
- DERIVED: natural matches, landscapes, geometry;
- REFERENCE / EVALUATION: the oracle benchmark and Position.

Nothing is CONTROLLER-TIME.

`overview.png` answers: *"In favorable geometry, does raw RGB place the right correspondence at the correct spherical
epipolar location?"*
- **A — Same saved AB1c observations:** the three binocular pairs; no new render; safe-forward gazes; RGB + calibration
  only at matcher time.
- **B — Direct epipolar matching:** representative left points: left angular patch, right raw epipolar search locus,
  natural best peak. ORACLE-ON-CURVE appears only as a labelled post-freeze reference.
- **C — Correspondence error:** full-core maps per gaze: natural validity, oracle-visible support, |pixel-equivalent
  error|, peak margin.
- **D — Metric consequence:** natural reconstructed geometry, natural-vs-perfect metric error, the 12 mm descriptive
  fraction, and conditioning retained.

Supporting figures:
- `correspondence-error.png`;
- `cost-landscapes.png`;
- `natural-reconstruction.png`;
- `confidence-diagnostics.png`;
- `visuals-manifest.json` (hashes and badges).

**Cost-landscape examples.** These are deterministic post-freeze REFERENCE / EVALUATION selections, made per gaze on
the evaluable set; ties go to the smallest core index:
1. **median-error:** |px-equiv| closest to its median;
2. **high-confidence low-error:** the largest peak margin among |px-equiv| ≤ 0.25;
3. **smallest peak margin:** the smallest finite margin;
4. **large-error percentile:** |px-equiv| closest to its p99.

Each landscape shows:
- the full ZNCC curve over the admissible segment, recomputed with the frozen score;
- the top-8 peaks;
- the discrete and refined estimates;
- the oracle-on-curve position and score;
- the 5 × 5 left patch and the right patches at the best candidate and at the oracle.

No example is chosen by eye.

## 26. Checker (`tools/active_bootstrap/check_ab1d.py`)

Fail-capable. It keeps its own literal constants and independently recomputes the load-bearing quantities where
practical, including:
- canonical source identities and exact AB1c observation reuse (hashes against the AB1c manifest);
- no Blender / render, no new gaze, no head motion;
- the guard records: matcher reads exactly calibration + RGB, and no oracle / Position / Object Index / evaluation at
  matcher or geometry time;
- the raw left nominal core;
- the θ / φ convention (its own formulas);
- the epipolar line (an independent fundamental-matrix derivation);
- the candidate segment, 1 px spacing and the physical positive-intersection filter;
- the 5 × 5 angular patch, the photometric conversion, MIN_LOCAL_STD_U8 = 0.5 and ZNCC;
- the tie rule, top-8 distinct peaks, 3 px separation, quadratic refinement and the ±0.75 bound;
- for a deterministic subset of left pixels per gaze (every core index ≡ 7 mod 32, i.e. 2,048 pixels, plus the
  landscape examples): the matcher re-implemented independently, record by record;
- full-record invariants: product = valid records, no hidden ZNCC threshold, no uniqueness or LR rejection, reason
  codes, uv on the line;
- truth-free product, natural correspondence freeze, accepted spherical geometry only, geometry freeze before oracle
  access (ordered guard events);
- primary θ-error, local pixel-scale and oracle-on-curve recomputation, top-k oracle ranks, the offset landscape and the
  post-freeze metric evaluation;
- confidence strata;
- figures regenerated byte-identically, truth badges and epistemic labels;
- the AST of the AB1d sources: no planar matcher, SGBM, learned model, controller or head motion;
- accepted AB1c / AB1b products unchanged;
- changed tracked files limited to the declared AB1d and roadmap files;
- the run order: each canonical step once, in order, clean and pushed.

## 27. Corruption / mutation suite

From a passing baseline, after an **unmodified-mirror null probe** passes every check, genuine defects are injected
into mirrors of the run and the visuals (JSON copied, arrays linked or rewritten). Each must fail at least one check.
They cover:
- **Source / truth firewall:** a changed source observation; Position read during matching; the AB1c oracle read
  during matching; identity / depth added to the natural product.
- **Epipolar geometry:** flipped baseline; wrong θ pole; φ sign; altered right-camera transform; an offset epipolar
  line.
- **Patch / photometry:** patch ≠ 5 × 5; angular spacing; raw linear values instead of the declared conversion; texture
  threshold; ZNCC mean subtraction; ZNCC normalisation.
- **Search:** 1 px spacing; a hidden depth-prior truncation; candidate ordering / tie rule; peak separation; TOP_K.
- **Refinement:** disabled; quadratic sign; bound exceeded.
- **Freeze:** natural product modified after its freeze; geometry modified after its freeze; truth opened before the
  geometry freeze.
- **Evaluation:** θ error; pixel-equivalent scale; oracle rank; one metric statistic.
- **Visual:** a canonical pixel; a truth badge.
- **Process:** SGBM injected; a learned matcher injected; a controller / head-motion command injected; a canonical step
  run twice.

Algorithmic mutations rewrite the checked rows of a mirrored record with the output of the mutated matcher, exactly
what a full mutated run would store there. The suite does not chase an arbitrary count.

## 28. Permitted fix scope

- **Before the canonical match:** ordinary implementation defects found by the synthetic tests may be corrected and
  documented.
- **Once the canonical match has started**, none of the following changes: patch size, photometric transform, texture
  threshold, epipolar definition, candidate spacing, search support, peak separation, TOP_K, ZNCC definition, sub-pixel
  method, refinement bound, validity semantics, scientific metrics, outcome semantics.
- A poor primitive matcher is the result. It is not tuned against oracle correspondence.
- A code defect may be repaired only where this contract already determines the correct behavior. Every incident is
  documented.
- Checks are not weakened to pass.

## 29. Cost (design-time, calibration-only estimate; PROPOSED)

At the synthetic gazes forward (0, 0), right (12, 0), left-up (−8, 9) and a 19.5° edge gaze:
- the admissible segment holds about **224–481 candidates per left pixel** (median ≈ 353);
- q_∞ lies about 36 px from the left pixel position (vergence 2.10 m).

A full gaze is therefore about 65,536 × 353 × 25 ≈ 0.58 G bilinear samples per image. A single-process numpy rate of
≈ 34 M samples / s (MEASURED on random arrays, design-time) suggests on the order of one to a few minutes per gaze.

- Execution is vectorised in fixed batches of left pixels on **16 threads**. This is execution strategy only; results do
  not depend on it (synthetic case 23).
- No parameter sweep, no rendering, no overnight task. If runtime becomes unreasonable, STOP and report; the mechanism
  does not change.

Cost classes:
- interactive: `source`, `freeze-correspondence`, `spherical`, `freeze-geometry`, `visualize`;
- batch: `synthetic`, `match`, `evaluate`, the checker with corruptions.

## 30. Commands and run layout

    .venv/bin/python tools/active_bootstrap/ab1d_run.py source                --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d_run.py synthetic             --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d_run.py match                 --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d_run.py freeze-correspondence --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d_run.py spherical             --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d_run.py freeze-geometry       --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d_run.py evaluate              --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d_run.py visualize             --run RUN --visuals VIS
    .venv/bin/python tools/active_bootstrap/check_ab1d.py --run RUN --visuals VIS [--corruptions] [--write-summary]

Tools:
- `ab1d_spec.py`: constants and pins;
- `ab1d_match.py`: the matcher;
- `ab1d_run.py`: stages;
- `ab1d_synthetic.py`: known answers;
- `ab1d_visuals.py`: figures;
- `check_ab1d.py`: the checker.

`tools/repository/check_repository_layout.py` declares this contract (required) and the report and the six tools
(allowed), in the contract commit.

Run tree:
- `source/source-manifest.json`;
- `synthetic/synthetic-report.json`;
- `match/gaze-N/{matcher-record.npz, natural-correspondences.npz, match-summary.json, match-opened-files.json}` and
  `match/correspondence-freeze.json`;
- `spherical/gaze-N/{epipolar-result.npz, left-core-rays.npz, spherical-summary.json, spherical-opened-files.json}`;
- `freeze/geometry-freeze.json`;
- `evaluation/gaze-N/evaluation-result.npz`, `evaluation/evaluation-summary.json`,
  `evaluation/evaluation-opened-files.json`;
- `manifest.json`, `process-log.jsonl`, `check-summary.json`.

## 31. Report and stop

`docs/active-bootstrap/ab1d-safe-forward-natural-correspondence-report.md`: status REVIEW PENDING, marker
`ACTIVE_BOOTSTRAP1D_SAFE_FORWARD_NATURAL_CORRESPONDENCE_COMPLETE`, no ACCEPTED marker. Contents:
1. provenance;
2. the exact-reuse proof;
3. the frozen matcher;
4. runtime per gaze;
5. full-core counts;
6. the primary per-gaze benchmark;
7. the cost-landscape benchmark;
8. confidence diagnostics;
9. the secondary metric error;
10. the supported outcome(s);
11. checks;
12. corruptions;
13. visuals with hashes and the regeneration command;
14. incidents / fixes;
15. what is established;
16. what is NOT established;
17. unresolved decisions.

The report does not propose or implement a more complex matcher. After the report is committed and pushed, STOP:
- no self-acceptance, no merge;
- no SGM, learned features or training;
- no head recentering, no controller reconnection.

## 32. Declared constants (summary)

| constant | value |
|---|---|
| PATCH | 5 × 5, offsets −2..+2 |
| δ (angular spacing) | atan(1 / f), f = K[0][0] |
| luminance | 0.2126, 0.7152, 0.0722 on `linear_to_u8` (float64, not re-rounded) |
| MIN_LOCAL_STD_U8 | 0.5 (population std of the 25 samples) |
| candidate spacing | 1.0 raw px, s_k = k, k ≥ 1 |
| TIE_EPS | 1e-12 (ZNCC) |
| TOP_K | 8 |
| peak separation | 3.0 raw px |
| refinement | one 3-point parabola, bound ±0.75 sample, only if D < 0 and both neighbours valid |
| projection in-front epsilon | h_2 > 1e-12 |
| DEN_EPS | `ab1b_spec.DEN_EPS` |
| oracle peak radius (evaluation) | 1.5 px |
| landscape offsets (evaluation) | −1.0, −0.5, 0, +0.5, +1.0 px |
| at/above-best tolerance (evaluation) | 1e-9 |
| pixel bins (descriptive) | 0.10, 0.25, 0.50, 1.00 px-equivalent |
| metric fractions (descriptive) | 12, 25, 50 mm |
| checker subset | core index ≡ 7 (mod 32) + landscape examples |
| threads | 16 (execution only) |
