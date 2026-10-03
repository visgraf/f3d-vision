# Natural Bootstrap-1a — Spherical Range Connectivity — contract

**Status: PROPOSED** (committed before implementation and before any Classroom discovery). Branch
`natural-bootstrap/nb1a-range-connectivity`, from `main` @ `0fe83af` (Breadth-1 accepted at `40a1cb1`).

## 1. Question

> Can local 3-D range continuity alone turn the accepted broad spherical glance into a useful set of
> connected perceptual hypotheses and representative seed directions, without using Blender object
> identity?

NB1a is **not**:
- full Natural Bootstrap-1 acceptance;
- RGB + depth segmentation;
- semantic segmentation;
- controller integration;
- persistent identity, or Natural Bootstrap-2;
- a benchmark against the 234 Blender objects;
- an attempt to recover the authored scene graph.

**The modest claim:** NB1a removes Blender **object identity** from bootstrap discovery. It does **not**
claim natural stereo depth sensing. Range is a **controlled sensory proxy**: it is derived from the
Blender Position pass of the accepted Breadth-1 observation.

There is no target hypothesis count, no required agreement with 234 and no minimum authored purity. Every
outcome is valid and answers the question:
- many fragments;
- a few giant regions;
- a structural shell with foreground components;
- coherent proto-objects;
- or something less useful.

Qualitative review afterwards considers coherence, seedability and plausibility for later active
interrogation. No numerical pass/fail threshold is encoded for them.

## 2. No new scene observation

No Blender process runs. The only scene evidence is the accepted Breadth-1 canonical EXR:

| source | role | sha256 |
|---|---|---|
| `/home/lvelho/rd/f3d-vision/previews/breadth-1-classroom-234-spherical-glance/render/canonical.exr` | the single accepted Classroom observation: 720 × 360, 0.5°, full sphere, fixed cyclopean head origin, static Classroom | `4ea036fc74eab3b3ab06a0c4470c2b01740c9322de0eea522f957ddfffa172f8` |
| `/home/lvelho/rd/f3d-vision/previews/controller-01-full/bootstrap/seeds.json` | **only** its `head_origin_w_m` and `head_R_wh`, the accepted fixed-head pose, read by input preparation | `6ef833196de2462370ba4b2a2a8eed3fbde7f0a61e5aa6cbaf95f66947134c4f` |

Evaluation alone (section 7) additionally reads:
- the accepted catalog `previews/controller-01-full/bootstrap/instance_catalog.json` (`be265945…`);
- the Breadth-1 `summary.json`, as reference accounting.

Not allowed:
- a new, lower-resolution or smoke-test Classroom render;
- a foveal, stereo or per-hypothesis observation.

Synthetic non-Classroom unit tests are allowed, without Blender. Synthetic known-answer rasters, and a
synthetic EXR written with the `OpenEXR` package, exercise the pipeline.

## 3. Three separated paths and their truth boundaries

| path | may read | writes | guard |
|---|---|---|---|
| **1. sensory-proxy preparation** (`prepare-input`) | the canonical EXR (Combined RGB and Position **only**), `seeds.json` (head pose only) | `input/range-sensory.npz`, `input/rgb-sensory.npz`, `input/input-manifest.json` | file-open guard with an allowlist; opened files recorded |
| **2. natural bootstrap discovery** (`discover`, `freeze`) | `input/range-sensory.npz` only, plus deterministic grid geometry and its declared constants | `discovery/*` | file-open guard (allowlist); every opened file recorded; violations must be 0 |
| **3. reference / evaluation** (`evaluate`) | the frozen discovery products (hash-verified first), then Object Index (canonical EXR), the catalog, Breadth-1 accounting and `input/rgb-sensory.npz` | `evaluation/*` | opened files recorded in order; the freeze is verified before any reference open |

**The stripped sensory input:**
- `range-sensory.npz` contains exactly `range_m` (float64 360 × 720; 0 where invalid) and `valid_mask`
  (bool).
- `rgb-sensory.npz` contains exactly `srgb8` (uint8 360 × 720 × 3).
- The resolution, grid and source hashes are in `input-manifest.json`. Discovery does not read the
  manifest; it derives the grid from the array shape and its constants.

The sensory input never contains:
- Object Index, instance ids or object names;
- the catalog;
- accepted-25 membership;
- Breadth-1 components or seeds;
- Controller bootstrap seeds;
- any oracle segmentation.

**Definitions:**
- Range: `r = ‖position_w − head_origin_w_m‖`, in float64.
- Valid: Position ≠ (0, 0, 0). This is the accepted first-hit semantics: no geometry is written as zeros.
- `srgb8`: the standard sRGB transfer function applied to `clip(Combined linear, 0, 1)`, then rounded to
  8 bits. This is an 8-bit camera-like proxy. RGB is retained for visualization and post-freeze
  diagnostics only; discovery never reads it.

**Truth classes** (Visual Language 1; nothing is CONTROLLER-TIME):

| class | products |
|---|---|
| ORACLE INPUT | the RGB / range sensory proxy (from Blender Combined + Position) |
| DERIVED | continuity graph, retained/cut edges, hypotheses, boundaries, interior clearance, seeds; the RGB edge diagnostics |
| REFERENCE / EVALUATION | Blender Object Index, the authored catalog, the hypothesis-vs-authored overlap |

## 4. Spherical graph and the continuity measure (DERIVED)

Width 720, height 360. Cell centres are as in Breadth-1:

    yaw_i   = −180° + 0.5°(i + 0.5)
    pitch_j = 90° − 0.5°(j + 0.5)
    d       = (sin yaw cos pitch, sin pitch, −cos yaw cos pitch)    (head frame)
    p       = r d

Each valid cell is a graph node. The **seam-aware 8-neighbourhood** is enumerated once per unordered pair
with four forward offsets from each cell (j, i):
- (j, i+1);
- (j+1, i−1);
- (j+1, i);
- (j+1, i+1).

Columns are taken modulo 720, so longitude wraps. Rows outside 0…359 do not exist, so latitude does not
wrap. That gives 1,034,640 neighbour pairs in total. A pair is a **candidate** iff both cells are valid.

For a candidate pair:

    δ_ij = atan2(‖d_i × d_j‖, d_i · d_j)          (true angular separation; never a constant pixel spacing)
    g_ij = ‖p_i − p_j‖
    s_ij = ((r_i + r_j) / 2) · δ_ij
    C_ij = g_ij / s_ij                             (the NB1a continuity ratio)

**The single scientific parameter**, declared before any Classroom discovery:

    MAX_SURFACE_SLANT_DEG = 75.0
    C_MAX = 1 / cos(radians(75.0)) = sec 75° ≈ 3.863703305

C_MAX is computed from the declared angle, never as a rounded constant. **Retain** the continuity edge iff
`C_ij <= C_MAX`; otherwise the edge is **cut**.

Assumption: for a locally planar surface whose normal makes an angle θ with the ray, `g ≈ r δ / cos θ`, so
`C ≈ sec θ`:
- a fronto-parallel surface has C ≈ 1 (slightly below 1, chord versus arc);
- C ≤ C_MAX admits a continuous surface up to about 75° of grazing slant;
- first-hit depth discontinuities generally give large C.

The parameter is not tuned after the Classroom result.

## 5. Hypotheses and records (DERIVED)

**Temporary perceptual hypotheses** are the connected components of the valid-cell graph under the retained
edges. That is the whole decomposition. Not used:
- SLIC, k-means or graph cuts;
- learned or semantic models;
- size filtering, deletion or post-hoc merging;
- oracle splitting;
- a target count.

Every component is kept, including singletons.

**Canonical support** (sr), also the ordering key:

    Ω(H) = (2π/720) · fsum_k( m_k · Δs_k )
    k = 0…179;  m_k = n_k + n_(359−k)   (cells of H in mirror rows k and 359−k)
    Δs_k = sin(π/2 − kπ/360) − sin(π/2 − (k+1)π/360)   (Python math.sin)

This is the exact equirectangular solid angle. It folds mirror rows and sums with `math.fsum`, so supports
of equal row histograms are bitwise equal. The fraction of 4π is reported too.

**Ordering and ids.** Hypotheses are sorted by:
1. descending Ω;
2. descending cell count;
3. the smallest row of the component;
4. then the smallest column in that row (the lexicographically smallest cell).

They get the ids `H0001`, `H0002`, …: at least four digits, more if needed. No Blender identity is used.

**The record** of each hypothesis holds:
- id and ordering keys;
- cell count;
- Ω and its fraction of 4π;
- min / median / max range (numpy median);
- boundary cell count;
- maximum interior clearance (rad and degrees);
- the seed's row, column, yaw, pitch and range;
- the fallback flag;
- the tied-candidate count.

There is no semantic label and no confidence scalar.

## 6. Deep-interior representative seed (DERIVED)

1. **Boundary.** A component cell is a boundary cell iff at least one existing 8-neighbour is invalid, or
   is valid but in another component. Rows beyond the top or bottom do not exist and do not make a
   boundary. Longitude wraps.
2. **Clearance.** Multi-source Dijkstra from all boundary cells (distance 0) along the component's
   **retained continuity edges**, with edge cost δ_ij. This is "paths inside the component": a path never
   leaves the component's graph. `D(x)` is the angular distance to the nearest boundary cell.
3. **Seed.** The cell with maximum D. Every cell with `max_D − D <= CLEARANCE_TIE_EPS_RAD = 1e-12` is
   tied; ties go to the smaller row, then the smaller column.
4. **Degenerate cases:**
   - a singleton is its own seed, with clearance 0;
   - a component with **no boundary** records `NO_BOUNDARY_FALLBACK` and takes its lexicographically
     smallest cell, with clearance null. No other optimization is invented.

Every seed is a cell of its hypothesis. No seed causes an observation.

## 7. Freeze, then reference / evaluation

**Freeze.** `freeze` writes `discovery/bootstrap-freeze.json` with the sha256 of:
- `input/range-sensory.npz`;
- `continuity-edges.npz`, `hypothesis-raster.npz`, `hypotheses.json`, `hypotheses.csv`, `seeds.json`;
- `discovery-summary.json`, `discovery-opened-files.json`;
- the discovery configuration and the discovery code files.

`evaluate` refuses to run unless every frozen hash verifies. It records the verification before its first
reference open. It never writes into `discovery/` or `input/`. After evaluation, the frozen hashes are
verified again.

**Overlap (REFERENCE / EVALUATION).** H_i is a natural hypothesis; O_j is an authored identity (Object Index
j from the canonical EXR); **O_0** is valid rendered geometry carrying Object Index 0.

    A_ij = Ω(H_i ∩ O_j)

It is stored sparse, with cells and sr. It is **not** a ground-truth confusion matrix. No precision,
recall, accuracy, IoU or "error" is reported.

Per H, the record holds:
- the intersected authored ids;
- the dominant id (largest overlap, catalog or 0) and its fraction;
- the fractions of all intersected ids;
- the O_0 fraction.

Per O, the record holds:
- the number of hypotheses intersecting it;
- the support distribution across them.

Examples are chosen by rank, never by threshold:
- the hypotheses with the most intersected authored ids (one H → many O);
- the authored ids intersected by the most hypotheses (many H → one O);
- the hypotheses with the largest O_0 support (H dominated by O_0).

Cross-check: the O_0 and catalog cell counts equal Breadth-1's accounting.

**RGB diagnostics (DERIVED, post-freeze).** For every candidate neighbour pair:
- decode `srgb8 / 255` with the standard sRGB transfer to linear;
- the contrast is `‖rgb_lin_i − rgb_lin_j‖₂`;
- there is no threshold.

Reported are the distributions for **retained** versus **cut** edges, in bins declared below, with
quantiles. A map shows the RGB contrast on retained (intra-hypothesis) edges. RGB never causes a merge,
split, seed change or deletion. Its purpose is to inform whether a future NB1b should test RGB continuity.

## 8. Declared distributions (before any Classroom discovery)

| distribution | bins |
|---|---|
| hypothesis support Ω (sr) | edges `10^(k/2)`, k = −14…2 |
| cell count | edges `2^k`, k = 0…18 |
| interior clearance (degrees) | zero counted separately; edges `2^(k/2)`, k = −6…14 |
| range (m) | Breadth-1 half-octave edges, `[0, 0.125)`, `2^(k/2)` for k = −6…12, `[64, ∞)` |
| RGB contrast | zero counted separately; edges `10^(k/4)`, k = −24…1 |

Quantiles are 0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1. Top-K supports are taken for K = 1, 5, 10 and
25.

The **pure discovery summary**, recorded before evaluation, holds:
- valid cells;
- candidate pairs;
- retained and cut edges;
- hypotheses;
- singletons (count and fraction) and hypotheses with more than one cell;
- the largest support and the top-K supports;
- the support and cell-count distributions;
- the clearance distribution, zero-clearance seeds and no-boundary fallbacks;
- range by hypothesis.

## 9. Outputs

Machine-facing evidence, `/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1a-range-connectivity/`:

| directory | files |
|---|---|
| `input/` | `range-sensory.npz`, `rgb-sensory.npz`, `input-manifest.json`, `input-opened-files.json` |
| `discovery/` | `continuity-edges.npz`, `hypothesis-raster.npz`, `hypotheses.json`, `hypotheses.csv`, `seeds.json`, `discovery-summary.json`, `discovery-opened-files.json`, `bootstrap-freeze.json` |
| `evaluation/` | `overlap-matrix.npz`, `overlap-summary.json`, `rgb-edge-diagnostics.json`, `rgb-edge-contrast.npz`, `evaluation-opened-files.json` |
| `synthetic/` | the known-answer report |
| top level | `process-log.jsonl`, `manifest.json`, `check-summary.json` |

Persistent visuals, `/home/lvelho/rd/f3d-vision/visuals/natural-bootstrap-1a-range-connectivity/`:
- `overview.png`, with four regions:
  - A, ORACLE INPUT: RGB + range;
  - B, DERIVED: range-continuity boundaries;
  - C, DERIVED: hypotheses + deep-interior seeds;
  - D, REFERENCE / EVALUATION: the relation to authored identity, catalog versus noncatalog. It is kept
    deliberately secondary.
- `range-input.png`, `continuity-boundaries.png`, `hypothesis-panorama.png`, `seed-panorama.png`;
- `hypothesis-support-histogram.png`, `interior-clearance-histogram.png`, `overlap-matrix.png`,
  `rgb-edge-contrast.png`;
- `visuals-manifest.json`.

Glyphs:

| glyph | meaning |
|---|---|
| ink diamond | derived seed (as Breadth-1); diamonds grow with interior clearance, singletons are small dots |
| thin solid ink line | natural boundary (a cut edge, or a valid/invalid border) |
| hatched | no geometry |
| dashed brown line | authored reference boundary, in evaluation figures only |

## 10. Checks (`tools/natural_bootstrap/check_nb1a.py`)

The checker recomputes independently:
- its own EXR reader (`exr_lite`);
- its own grid and directions;
- angular separation via the chord formula `2 asin(‖d_i − d_j‖ / 2)`, compared within tolerance; edge
  states are compared exactly;
- its own BFS components;
- its own clearance by vectorized Bellman-Ford relaxation;
- its own overlap counting.

It keeps literal copies of the constants.

1. The source canonical EXR hash is exactly the accepted one.
2. No Blender invocation occurred: no Blender process in the log; the Breadth-1 render directory and the EXR
   are unchanged.
3. The sensory input is exactly 720 × 360.
4. Range and validity recompute from the EXR Position and the accepted head origin.
5. The stripped range input contains only `range_m` and `valid_mask`; there is no Object Index, instance or
   catalog data in the inputs or the manifest.
6. Discovery opened only allowed files, with 0 violations; the guard self-test blocks a forbidden open.
7. Discovery did not open RGB.
8. Discovery did not open Object Index, the catalog, the EXR or evaluation files. The discovery code imports
   no oracle, controller or RGB path.
9. Spherical cell directions recompute.
10. The seam-aware 8-neighbour enumeration recomputes (count and pairs).
11. True angular separations recompute.
12. C_ij recomputes independently.
13. C_MAX equals sec 75°, and the configuration declares 75.0.
14. Retained/cut edge states recompute exactly.
15. Connected components recompute independently.
16. Every valid cell belongs to exactly one hypothesis.
17. No invalid cell belongs to a hypothesis.
18. No component was filtered, merged or deleted: the hypothesis count equals the independent component
    count, with a 1:1 partition.
19. Deterministic ordering and ids recompute.
20. Boundary cells recompute.
21. Interior clearance recomputes independently.
22. Every seed lies in its hypothesis and attains the maximum clearance (within ε).
23. Seed tie, singleton and fallback behaviour is correct.
24. The freeze hashes matched before evaluation, and the reference was opened only after verification.
25. Evaluation did not alter the bootstrap products.
26. The overlap matrix recomputes from the frozen H and the reference O.
27. O_0 noncatalog valid geometry is included, and the accounting matches Breadth-1.
28. RGB diagnostics are post-freeze, recompute, and did not alter discovery.
29. The visual products regenerate deterministically.
30. `fov3d/` and the accepted controllers are unchanged.
31. Changed tracked files are only declared NB1a files and the layout declaration.
32. No controller was executed: the process log holds only NB1a commands, and no controller module is
    imported.
33. The synthetic known-answer shapes pass in the generator and in the independent checker:
    - a continuous fronto-parallel patch: 1 component;
    - a clean depth step that splits: 2;
    - near threshold: a 74° slanted strip stays connected, a 76° strip splits;
    - longitude seam connectivity;
    - diagonal connectivity;
    - a singleton;
    - a deep-interior seed at the centre of a square;
    - a symmetric four-way seed tie resolved to the smaller row and column;
    - a no-boundary full sphere.

**Corruption / mutation suite** (`--corruptions`). Corruptions are planted in throwaway mirrors or as
in-process mutants. They count only when the uncorrupted baseline passes all checks. The list:
- MAX_SURFACE_SLANT_DEG changed;
- one retained edge flipped;
- longitude wrapping broken;
- constant pixel spacing used instead of the true δ;
- one hypothesis label altered;
- a singleton deleted;
- two components merged;
- a seed moved off support;
- a seed moved away from the maximum-clearance cell;
- the seed tie-break violated;
- Object Index added to the sensory input;
- discovery opening RGB;
- discovery opening the catalog or Object Index;
- a bootstrap output modified after the freeze;
- evaluation before a valid freeze;
- one overlap value altered;
- O_0 omitted;
- RGB modifying a hypothesis;
- a visual pixel altered;
- `fov3d`/controller code modified;
- a Blender or controller command in the process log.

Markers: `NATURAL_BOOTSTRAP1A_CHECKS_PASS`, `NATURAL_BOOTSTRAP1A_MUTATIONS_CAUGHT`.

## 11. Commands, order and cost classes (PROPOSED estimates)

    RUN=/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1a-range-connectivity
    VIS=/home/lvelho/rd/f3d-vision/visuals/natural-bootstrap-1a-range-connectivity
    .venv/bin/python tools/natural_bootstrap/nb1a_run.py synthetic     --run $RUN   # interactive–batch
    .venv/bin/python tools/natural_bootstrap/nb1a_run.py prepare-input --run $RUN   # interactive
    .venv/bin/python tools/natural_bootstrap/nb1a_run.py discover      --run $RUN   # batch
    .venv/bin/python tools/natural_bootstrap/nb1a_run.py freeze        --run $RUN   # interactive
    .venv/bin/python tools/natural_bootstrap/nb1a_run.py evaluate      --run $RUN   # batch
    .venv/bin/python tools/natural_bootstrap/nb1a_run.py visualize     --run $RUN --visuals $VIS
    .venv/bin/python tools/natural_bootstrap/check_nb1a.py --run $RUN --visuals $VIS --corruptions --write-summary

**Order:**
1. Implement the steps above.
2. Run the synthetic tests and a scratch end-to-end run on a synthetic EXR.
3. Run the layout checker and `git diff --check`.
4. Commit and push the implementation.
5. Make **one** canonical discovery, which means one application of the frozen algorithm and configuration
   to the accepted range proxy.
6. Freeze, evaluate, visualize and check.

`discover` refuses to overwrite an existing `discovery/`.

## 12. Acceptance, stop conditions and permitted fixes

On successful execution, with all checks passing and the corruptions caught from a passing baseline, the
report records `NATURAL_BOOTSTRAP1A_RANGE_CONNECTIVITY_COMPLETE` with status **REVIEW PENDING**. No ACCEPTED
marker is written.

**Stop and return to Luiz/Chat on any of these:**
- a source hash mismatch;
- any truth-firewall violation in discovery;
- the need to change the 75° parameter, the region rule, filtering or the seed rule;
- any discovery change after the reference evaluation has been viewed.

Implementation defects inside the new NB1a tools may be repaired before the canonical discovery. After the
freeze, only presentation and serialization repairs that leave the frozen products unchanged may proceed.

Unchanged by this step:
- `fov3d/`;
- the controllers, FSG code and accepted renderers;
- Visual Language 1;
- the Breadth-1 tools and outputs;
- the 234-object catalog.

No controller runs. NB1b, controller integration and Natural Bootstrap-2 are not started.
