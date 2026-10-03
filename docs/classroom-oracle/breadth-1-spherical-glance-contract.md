# Breadth-1: Classroom-234 Spherical Glance — contract

**Status: PROPOSED** (committed before implementation and before any Classroom execution). Branch
`classroom-oracle/breadth-1-spherical-glance`, from `main` @ `3aa0cc6` (Visual Language 1 accepted at
`e596a10`).

Breadth-1 is a closing **reference experiment** of the oracle-bootstrap era. It renders exactly one
low-resolution global Blender observation of the complete authored Classroom from the fixed head, and
describes it. It changes no scientific behavior:
- no `fov3d/` file changes;
- no controller, policy, matcher, fusion or accepted renderer changes;
- no controller run, no gaze, no foveation, no stereo growth.

## 1. Question

> What does the complete authored Classroom scene look like from the fixed head under one
> low-resolution global observation, before active foveation?

Breadth-1 is **not**:
- a Controller-02 benchmark;
- a local-controller refinement;
- a Natural Bootstrap experiment;
- a 234-object growth campaign;
- a claim that Blender authored objects are natural perceptual objects.

The 234 Blender objects are the **accounting universe**. An object with no first-hit cell is a valid
result. Breadth-1 does not call it "occluded": zero support may come from sampling resolution,
containment, viewpoint or other first-hit effects. The step is **descriptive**: no minimum visible count
is required for success.

## 2. Sources (verified by sha256 before rendering)

| source | role | sha256 |
|---|---|---|
| `previews/controller-01-full/bootstrap/seeds.json` | the accepted fixed-head transform `head_R_wh`, `head_origin_w_m`; the accepted seed directions of the 25 | `6ef833196de2462370ba4b2a2a8eed3fbde7f0a61e5aa6cbaf95f66947134c4f` |
| `previews/controller-01-full/bootstrap/instance_catalog.json` | the accepted authored-object catalog (instance id → name) | `be26594254b03fbda7216ac1a942a5c800cf4bdd8f79751a2b8c22d6bfb4c7ae` |
| `previews/controller-02-classroom-replay/result.json` | the accepted localized Controller-02 set of 25 (`final_states` keys) | `a6dc4879f70216f99d098841f9d2c33dda0ceb71f01a4ab76320b0d08212dc55` |
| `scenes/classroom/classroom_eye.blend` | the accepted Classroom scene (`ASSET_MANIFEST.json` `accepted_classroom_eye_blend_sha256`) | `dca66a3257b909aef00b0331652c55f62a93a8dff0665d070fba7efa436953cc` |

All `previews/…` paths are under `/home/lvelho/rd/f3d-vision/`. Every source is read-only. The accepted
set of 25 must be the same in both accepted sources: the `final_states` keys of `result.json` and the
`instances` of `seeds.json`. If either differs, execution stops.

## 3. The frozen canonical observation

| item | value |
|---|---|
| scene / state | accepted Blender Classroom `classroom_eye.blend`, its active scene, static (frame as loaded) |
| head | fixed: `head_R_wh` (head → world rotation) and `head_origin_w_m` exactly as in `seeds.json` |
| viewpoint | the cyclopean head origin `head_origin_w_m` |
| orientation | camera world matrix `[head_R_wh | head_origin_w_m]`: the camera axes are the head axes (+X right, +Y up, −Z forward), as in the accepted Visual Language 1 reference renderer |
| projection | Blender `PANO` camera, `EQUIRECTANGULAR`: longitude `[−π, π]` (360°), latitude `[−π/2, π/2]` (180°) |
| resolution | 720 × 360 cells (0.5° × 0.5° nominal), `resolution_percentage` 100, pixel aspect 1 |
| active gaze / controller / foveation / stereo growth | NONE |
| engine | Cycles, device OPTIX requested; any other backend is a hard failure (no silent fallback) |
| sampling | 512 spp, adaptive sampling OFF, denoising OFF, motion blur OFF, BOX pixel filter width 1.0, seed 0 pinned (`bl_common.pin_seed`), clip 0.01–1000 m |
| passes | Combined, Position, Object Index, in **one** render written to **one** uncompressed multilayer EXR |
| object ids | `classroom_oracle1_render._assign_instance_ids` (accepted, unchanged) |

Before the render, inside Blender:
- the live id assignment must equal the accepted catalog exactly: **234** entries, the same id → name
  pairs. Otherwise execution stops before any render.
- the `EYE` object's rigid world pose must equal the `seeds.json` transform within 1e-6. This is a
  consistency check of the scene file.

The observation configuration above is frozen by this contract and the implementation commit. It is not
changed after the Classroom result is seen.

### 3.1 Cell convention

Column `i = 0…719`, row `j = 0…359`; row 0 is the top. Cell centres in the head frame:

    yaw_i   = −180° + 0.5° (i + 0.5)        (left → right; positive toward head +X)
    pitch_j =  +90° − 0.5° (j + 0.5)        (top → bottom)
    d_h     = (sin yaw cos pitch, sin pitch, −cos yaw cos pitch)

This is the project's yaw/pitch convention (`yaw = atan2(x, −z)`, `pitch = atan2(y, hypot(x, z))`).
Columns 0 and 719 meet behind the head (the longitude seam).

The mapping from Blender's equirectangular pixel grid to these cells is established by the synthetic
plumbing test (section 5) before the canonical run. It is then verified on every canonical authored cell
by the orientation check (check 2): the direction of the cell's Position sample from the head origin must
fall inside the cell.

### 3.2 First-hit semantics

Cycles is expected to write the Object Index and Position passes from each pixel's first camera sample,
unfiltered, while the Combined pass averages all 512 samples. Each cell's identity and position would then
be one first-hit sample inside that cell. This is PROPOSED until the synthetic test verifies it: integral
Object Index values, and Position on the surface of the object named by the index. If the test shows other
semantics, execution stops before the canonical run. The canonical checker verifies integral indices
again.

## 4. Analysis (all DERIVED; deterministic)

### 4.1 Cell classes

- **Authored cell:** Object Index ≠ 0. The index must be a catalog id. Any nonzero id absent from the
  catalog is a **hard failure**.
- **Index-0 cell:** not one of the 234. It is recorded separately as one of:
  - `INDEX0_NO_GEOMETRY`: the Position sample is exactly (0, 0, 0), i.e. presumed background or world;
  - `INDEX0_NONCATALOG_GEOMETRY`: index 0 with a nonzero Position, i.e. a surface that carries no catalog
    id.

  Their counts and solid angles are reported. Index-0 cells never enter per-object statistics or the
  point cloud.

### 4.2 Spherical weights

For row `j`: `dλ = 2π/720`, `φ_hi = π/2 − jπ/360`, `φ_lo = π/2 − (j+1)π/360`,
`dΩ_j = dλ (sin φ_hi − sin φ_lo)`. Each cell of the row has this weight, and the grid sums to 4π.

A support's solid angle is `Σ_j n_j dΩ_j` in float64, summed in ascending `j`, where `n_j` is its cell
count in row `j`. Raw cell counts are reported, but a cell fraction is never used as a spherical area.

### 4.3 Visibility

- `VISIBLE_AT_0P5_DEG`: the object's id occurs in at least one cell.
- `NO_FIRST_HIT_AT_0P5_DEG`: otherwise. No causal reason is inferred.

### 4.4 Connected components

Each authored object's visible mask is split into **8-connected** components. Longitude wraps (column 0
neighbours column 719, diagonals included); latitude does not wrap. This is authored-object image
fragmentation, not natural segmentation.

Components are ordered by solid angle (descending), then cell count (descending), then their
lexicographically smallest `(row, column)` cell (ascending). The first is the largest component.

### 4.5 Representative DERIVED seed

One seed per visible object. A seed is analysis only and causes no observation.

1. Take the largest component (4.4).
2. Compute the solid-angle-weighted mean of its cell-centre unit directions `d_h`, and normalize it.
3. Choose the component cell with minimum angular distance to the mean: the maximum float64 dot product
   with the unit mean. Ties go to the smaller row, then the smaller column.
4. Report that cell's centre yaw/pitch, row and column.

**Declared fallback:** if the mean's norm is below 1e-9, the seed is the component's lexicographically
smallest `(row, column)` cell. The seed record says whether the fallback was used.

For the accepted 25, the angular separation between this seed and the accepted `seed_gaze_deg` is also
reported, as a descriptive DERIVED comparison.

*Post-run clarification:* section 11 defines the numerical tie semantics of step 3. The rule above is kept
as originally frozen.

### 4.6 Range

`range = ‖position_w − head_origin_w_m‖`, in float64, from the float32 Position pass and the seeds
origin. Perspective Z depth is never used. Per object: min, median (numpy median; the mean of the two
middle values for even counts) and max over its authored cells.

### 4.7 Per-object record (all 234 objects, exactly once)

The record holds:
- catalog id and authored name;
- status;
- visible cell count;
- solid angle (sr) and fraction of 4π;
- component count, and each component's cells and solid angle;
- range min / median / max (null when not visible);
- `intersects_old_controller_domain`;
- `outside_old_controller_domain_cells`;
- `in_accepted_localized_25`;
- seed (yaw, pitch, row, column, fallback flag);
- the seed's separation from the accepted seed (accepted 25 only);
- rank.

**Old Controller domain:** yaw ∈ [−25°, 25°] and pitch ∈ [−20°, 20°], closed. An object intersects it when
at least one of its visible cell centres lies inside. Cell centres sit at odd multiples of 0.25°, so no
centre lies on the boundary.

**Rank:** visible objects get ranks 1…V by solid angle (descending), then cell count (descending), then
catalog id (ascending). `NO_FIRST_HIT` objects have rank null.

### 4.8 Global summaries

- catalog total (234), VISIBLE count, NO_FIRST_HIT count, and visible objects with more than one component;
- the index-0 accounting;
- per-object support distributions, in bins declared here before the run:
  - solid angle (sr): edges `10^(k/2)` for k = −14…2, with NO_FIRST_HIT counted separately as 0;
  - cell count: edges `2^k` for k = 0…18;
- global radial range over all authored cells:
  - bins with edges `2^(k/2)` m for k = −6…12, plus `[0, 0.125)` and `[64, ∞)`;
  - cell-count and solid-angle-weighted histograms;
  - quantiles 0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1. Cell quantiles use numpy `linear`. Weighted
    quantiles are the smallest range at which the cumulative weight reaches `q × total`.
- cumulative solid angle of the largest K objects, K = 1, 5, 10, 25, as fractions of 4π and of all
  authored solid angle;
- overlap with the accepted 25: visible and not visible among the 25, and visible objects outside the 25;
- visible objects entirely outside the old domain (no intersection), and visible objects with any support
  outside it;
- ranking by visible support;
- the component-count distribution, as exact integer counts.

No post-hoc qualitative labels (for example "large" or "tiny") and no thresholds chosen after seeing the
data.

## 5. One-run rule and execution order

1. **Synthetic plumbing test** (`synthetic`). It runs with no Classroom: a factory-startup Blender scene,
   rendered through the same camera/pass configuration function at 720 × 360. The scene is an emissive
   box room around the head (one object per face, distinct colours) plus small marker cubes at known
   head-frame directions, one of them straddling the longitude seam. Host checks:
   - orientation: markers forward, right, up, down and behind land at their declared yaw/pitch;
   - RGB channel order;
   - one EXR with all three passes;
   - integral Object Index values, and first-hit Position on the named object's surface;
   - range from Position and origin;
   - the seam component merged to 1, and 2 without wrap;
   - spherical weights summing to 4π.
2. **Preflight** (`preflight`). It loads the Classroom with no render (not an observation): verifies the
   catalog (234, exact), the EYE pose, the device and the camera configuration, then exits before
   `render()`.
3. **Implementation freeze.** The render/extract/analyze/check/visual code is committed and pushed before
   the canonical run, together with the synthetic test, `git diff --check` and the layout checks.
4. **Canonical render** (`render`). It runs exactly once. The command refuses an existing non-empty output
   directory. If it fails technically before producing a valid observation, a minimal plumbing repair and
   restart is allowed and documented.
5. **Analysis and visuals** (`analyze`, `visualize`) run from the saved EXR only. Once valid data exist,
   only presentation or serialization repairs that leave the frozen arrays and statistics unchanged may
   proceed. Anything else stops and returns to Luiz/Chat.

Not rendered:
- per-object views;
- foveal views;
- another resolution;
- a second Classroom panorama;
- Controller-02 observations;
- a lower-resolution Classroom "smoke test".

## 6. Provenance (Visual Language 1)

| product | truth class |
|---|---|
| RGB panorama, range panorama, Position-derived range data | REFERENCE / EVALUATION |
| Object Index raster, authored catalog identity | ORACLE INPUT |
| visibility, components, boundaries, seeds, rankings, statistics, plots, overview annotations | DERIVED |

Nothing in Breadth-1 is `CONTROLLER-TIME`, and no product, manifest field or figure may claim it.

The figures use Visual Language 1 (`tools/visual_language/style.py`, read-only) and its badges and their
non-colour cues:
- REFERENCE / EVALUATION: a hatched badge;
- ORACLE INPUT: a double-outline badge;
- DERIVED: a dashed-outline badge.

Breadth-1 adds three glyphs that do not reuse a Visual Language 1 glyph with another meaning:
- **derived seed direction:** a small ink diamond with a white halo. It is not a crosshair, because a
  crosshair means a fixation;
- **accepted-25 membership:** a solid ring around the diamond;
- **old Controller domain:** a dashed ink rectangle.

Authored boundaries are thin ink lines.

## 7. Outputs

Machine-facing evidence, `/home/lvelho/rd/f3d-vision/previews/breadth-1-classroom-234-spherical-glance/`:
- `synthetic/`: the synthetic test EXR, metadata and report;
- `preflight.json`;
- `render/canonical.exr`: the single canonical render, kept uncompressed as the raw evidence;
- `render/render-metadata.json`: written by Blender with the configuration read back from Blender, the
  device, timings, the catalog, the poses and the EXR sha256;
- `render/blender.log`;
- `glance.npz`: the aligned RGB float32, instance int32 and Position float32 arrays, extracted from the
  EXR;
- `range.npz`: range float64 and the cell weights;
- `object-stats.json`, `object-stats.csv`, `components.json`, `seed-directions.json`, `summary.json`;
- `global-point-cloud.ply`;
- `check-summary.json`;
- `manifest.json`: inputs with sha256, code commit, the logged subprocess commands, and outputs with
  sha256.

Persistent human-facing products, `/home/lvelho/rd/f3d-vision/visuals/breadth-1-classroom-234-spherical-glance/`:
- `overview.png`: four regions:
  - RGB spherical glance;
  - range;
  - authored Object Index and boundaries;
  - statistics, with the 234-object accounting (one cell per catalog object) and the seed directions.
- `rgb-panorama.png`, `range-panorama.png`, `instance-panorama.png`, `object-boundary-overlay.png`,
  `seed-direction-panorama.png`, `support-size-histogram.png`, `support-vs-range.png`;
- `global-point-cloud.ply`: binary little-endian, one vertex per authored cell, holding the world-frame
  Position, 8-bit RGB (`clip(linear)^(1/2.2)`, the Visual Language 1 gamma) and the instance id;
- `visuals-manifest.json`: each figure's truth badges, sources and sha256.

## 8. Checks (`tools/classroom_oracle/check_breadth1.py`)

The checker recomputes everything from the canonical EXR (read with the independent `OpenEXR` package)
and the accepted sources. It uses its own literal copy of the frozen configuration, and independent
implementations of the weights (`2 dλ cos φ_c sin(Δφ/2)`) and of the components (explicit seam-aware
union-find).

1. Canonical resolution is exactly 720 × 360 (EXR data window and metadata).
2. Full-sphere camera configuration:
   - the read-back `PANO` / `EQUIRECTANGULAR` camera and longitude/latitude ranges;
   - **orientation**: every authored cell's Position direction lies inside its declared cell (±0.25° in
     pitch and yaw; yaw wraps). An angular tolerance of 1e-3° applies, converted to yaw by `1/cos(pitch)`
     so that it stays an angle near the poles.
3. The fixed-head transform equals `seeds.json` exactly (requested), within 1e-6 (Blender read-back), and
   agrees with the EYE pose.
4. The catalog sha256 is the accepted one; its count is exactly 234; Blender's live assignment equals it.
5. Rendered nonzero instance ids are a subset of the catalog, and the raw Object Index is integral.
6. Every one of the 234 catalog objects appears exactly once, with matching names.
7. VISIBLE + NO_FIRST_HIT = 234, and each status recomputes.
8. Spherical cell weights sum to 4π, and the stored weights equal the independent formula.
9. Every per-object cell count (exact) and solid angle recompute from the instance raster.
10. Connected components recompute with the seam-aware rule (count, cells and solid angle of each, order).
11. Range values recompute from Position and the cyclopean origin.
12. Per-object min / median / max range recompute.
13. Every seed lies on its object's largest component and reproduces the frozen selection rule, with the
    numerical tie semantics of section 11.
14. The old Controller-domain flags recompute.
15. The accepted-25 membership flags reproduce the accepted sources (both must agree).
16. The rankings reproduce the raw supports.
17. The PLY point count, coordinates and instance ids match the canonical data.
18. Output hashes and manifest identities match.
19. No product, manifest or figure record claims CONTROLLER-TIME; every truth class is declared.
20. No controller was executed:
    - the logged subprocesses are only the declared Blender invocations;
    - there are no controller outputs;
    - the Breadth-1 tools import no controller module;
    - the accepted source runs are unchanged.
21. Accepted controller/FSG/renderer/Visual Language code is unchanged: every changed tracked file
    relative to the base is a declared Breadth-1 file.
22. `fov3d/` is byte-identical to the branch base `3aa0cc6`.
23. Exactly one canonical render: the process log and the render metadata show one canonical invocation.
    `glance.npz` reproduces exactly from the single EXR, whose sha256 Blender recorded.
24. The index-0 accounting recomputes, and authored + index-0 cells = 259,200.
25. The synthetic plumbing test passed with this code commit.
26. The visual products regenerate byte-identically from the saved data.

**Corruption / mutation suite** (`--corruptions`). It plants defects on throwaway mirrors or in-process
mutants; the canonical outputs are never modified. Each defect must make its targeted check fail:

| defect | targeted check |
|---|---|
| wrong catalog count | 4 / 6 |
| illegal instance id | 5 |
| altered visible-support count | 9 |
| wrong spherical row weight | 8 |
| broken seam / component count | 10 |
| seed moved off support | 13 |
| altered range statistic | 12 |
| flipped old-domain flag | 14 |
| flipped accepted-25 flag | 15 |
| wrong PLY point count | 17 |
| false provenance class | 19 |
| changed canonical render configuration | 1 / 2 |
| flipped image columns (orientation) | 2 |
| altered head transform | 3 |
| swapped ranks | 16 |
| altered manifest hash | 18 |
| a controller command in the process log | 20 |
| a changed accepted tool or `fov3d` file | 21 / 22 |
| a second canonical render | 23 |
| altered index-0 count | 24 |

Terminal markers: `BREADTH1_CHECKS_PASS` and `BREADTH1_MUTATIONS_CAUGHT`.

## 9. Commands and cost classes (PROPOSED estimates)

From the worktree root, with `RUN=/home/lvelho/rd/f3d-vision/previews/breadth-1-classroom-234-spherical-glance`
and `VIS=/home/lvelho/rd/f3d-vision/visuals/breadth-1-classroom-234-spherical-glance`:

| command | cost class |
|---|---|
| `.venv/bin/python tools/classroom_oracle/breadth1_glance.py synthetic --run $RUN` | interactive–batch (< 1 min) |
| `.venv/bin/python tools/classroom_oracle/breadth1_glance.py preflight --run $RUN` | interactive–batch (scene load) |
| `.venv/bin/python tools/classroom_oracle/breadth1_glance.py render --run $RUN` | batch (one render; < 5 min expected) |
| `.venv/bin/python tools/classroom_oracle/breadth1_glance.py analyze --run $RUN` | batch |
| `.venv/bin/python tools/classroom_oracle/breadth1_glance.py visualize --run $RUN --visuals $VIS` | batch |
| `.venv/bin/python tools/classroom_oracle/check_breadth1.py --run $RUN --visuals $VIS [--corruptions]` | batch |

Standing gates:
- `tools/repository/check_repository_layout.py`, which declares the Breadth-1 files narrowly;
- `scripts/verify_baseline.sh`;
- `git diff --check`.

## 10. Acceptance, stop conditions and permitted fixes

Implementation success requires:
- the exact configuration;
- exactly one valid canonical Classroom observation;
- all 234 objects accounted;
- aligned RGB / Position / Object Index evidence;
- the complete deterministic analysis and the required visuals;
- checks passing and the corruption suite caught;
- no controller run, no foveation, no per-object observation, no post-result retuning.

The scientific result is whatever the glance reveals. On completion the report records
`BREADTH1_CLASSROOM234_SPHERICAL_GLANCE_COMPLETE` with status **REVIEW PENDING**. No ACCEPTED marker is
written.

Stop and return to Luiz/Chat on any of these:
- a source hash mismatch;
- a catalog other than exactly 234, or a live assignment that differs;
- disagreement between the two accepted-25 sources;
- an EYE pose mismatch;
- a non-OPTIX device;
- a nonzero rendered id outside the catalog;
- an orientation check failure on canonical data;
- any repair that would change sampling, camera geometry, catalog or visibility semantics, or metrics
  after valid data exist.

Permitted fixes:
- before the canonical run: implementation defects inside the new Breadth-1 tools;
- after valid data: presentation and serialization only, with the frozen arrays and statistics unchanged.

The accepted Visual Language 1 renderer, `fov3d/`, the controllers and the accepted helpers are not
modified.

## 11. Post-run numerical clarification: representative-seed ties (2026-10-03)

**Authorized by Luiz/Chat on 2026-10-03, after the valid canonical observation** (Option A of the Breadth-1
report's check-13 decision). This is a numerical clarification of section 4.5 step 3, not a new
observation and not scientific retuning.

**Why.** The frozen rule picks the maximum float64 dot product, with ties to the smaller row, then the
smaller column. Its tie-break applies only to bitwise-equal values, and no summation order is fixed. For
mathematically mirror-symmetric components, two cells are exactly equidistant from the mean, but their
dot products differ by about 1 ulp, so the outcome depended on arithmetic order. The independent checker
and the generator disagreed on 3 of 126 canonical seeds.

**Rule.**

    SEED_TIE_DOT_EPS = 1e-12

After computing the dot products of the support cells to the normalized solid-angle-weighted mean, every
cell with `max_dot - dot <= SEED_TIE_DOT_EPS` is numerically tied. The tied set is resolved by the smaller
row, then the smaller column. The fallback (norm below 1e-9) is unchanged. The constant lives in
`tools/classroom_oracle/breadth1_spec.py`, and the checker keeps an independent literal copy.

**Scope.**
- It repairs floating-point ambiguity in mathematically symmetric cases.
- It may change only the DERIVED representative seed.
- It changes nothing else:
  - the observation;
  - visibility;
  - components;
  - support;
  - range;
  - rank;
  - catalog accounting;
  - the renderer configuration.
- **No new Blender render is authorized.** The seeds are re-derived from the saved canonical EXR (sha256
  `4ea036fc74eab3b3ab06a0c4470c2b01740c9322de0eea522f957ddfffa172f8`) by `analyze`, `visualize` and the
  checker only.

**Checks.**
- Check 13 applies this rule independently. It keeps its own cell geometry, spherical-weight expression,
  BFS components and weighted mean, and shares only the epsilon.
- Known-answer controls on exactly mirror-symmetric synthetic components (no Blender) exercise the rule
  in both the generator and the checker:
  - a two-cell row where exact float64 equality would pick the larger column;
  - a four-way tie straddling the equator;
  - a four-way tie across the longitude seam.
- The corruption suite adds a seed moved to another numerically tied cell, which only the tie-break can
  reject.
- Corruptions count as demonstrated only from a passing uncorrupted baseline.
