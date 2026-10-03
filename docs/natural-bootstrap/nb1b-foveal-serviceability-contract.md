# Natural Bootstrap-1b — Foveal Serviceability — contract

**Status: PROPOSED.** This contract is committed before implementation and before any serviceability
classification of the Classroom NB1a hypotheses. Branch `natural-bootstrap/nb1b-foveal-serviceability`, from
`main` @ `9c01b8a62813d097940ad5e6e3e95c5d3e3ead83` (NB1a accepted at `dcd294f`).

## 1. Question

> Which frozen NB1a natural hypotheses have an existing deep-interior seed that can safely accommodate the
> current foveal measurement footprint?

NB1b is a **read-only** experiment on the accepted NB1a products. It does **not**:
- create a new scene observation, run Blender, or run Controller-01 or Controller-02;
- change the NB1a segmentation or the NB1a seeds;
- use RGB or Blender identity to select candidates;
- add semantic classification;
- split or merge hypotheses, or optimize seed locations;
- perform Natural Bootstrap-2 identity persistence.

**The claim is modest.** NB1b is a sampled spherical serviceability test of the nominal angular measurement
core. It does not claim actual binocular matching, visibility, stereo success or objectness. There are no
target class counts: every outcome is valid and answers the question.

## 2. Frozen input (pinned before implementation)

The accepted NB1a run is `/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1a-range-connectivity/`
(branch `natural-bootstrap/nb1a-range-connectivity`, discovery frozen at `6b63cdc`, report `a0c98be`,
accepted at `dcd294f`). Its freeze record is the source identity.

**Selection inputs** (exactly these five files; every hash is checked before use):

| file | role | sha256 |
|---|---|---|
| `discovery/bootstrap-freeze.json` | the NB1a freeze identity (records the hashes of all frozen NB1a products) | `c0236d0424a7724bfe57bf0a19bdf56899b7eadf5e059c9537e785f3a08b826a` |
| `discovery/hypothesis-raster.npz` | `labels` (0 = no geometry; H = 1…453), plus `boundary` and `clearance_rad` | `513a15e0077fc1f5d84847ff020386687ce7ec28477b71ddc349378fb00bae88` |
| `discovery/hypotheses.json` | the hypothesis table: id, label, cells, support, range, clearance, seed | `eecf180faecd7765e15c162b76ae1427dc12212026f439d608f21b9c4357009b` |
| `discovery/seeds.json` | the frozen NB1a representative seeds | `c0362d9c898303869117bdd3bb303dadaf15c2d19b94733467fe2ade7c1fb556` |
| `discovery/discovery-summary.json` | the NB1a discovery summary (hypothesis count, validity accounting) | `fac0adb39331d9ff2a3305791b2aff3f0edbd2a43503d3d3572437a74cf2e4ec` |

The other inputs are not files:
- the spherical grid geometry: the accepted `tools/natural_bootstrap/nb1a_spec.py` (read-only), giving the
  720 × 360, 0.5° cell centres and the canonical folded support;
- the sensor constant (section 3).

**Validity.** A cell has valid NB1a range iff its label is > 0. NB1a checks 16–17 established that every
valid cell carries a hypothesis label and no invalid cell does. Selection therefore does not open
`input/range-sensory.npz`; the checker verifies label > 0 ⇔ `valid_mask` independently.

**Selection must not read:**
- RGB (`input/rgb-sensory.npz`);
- the canonical EXR, Object Index or the authored catalog;
- NB1a evaluation products (`evaluation/`);
- Breadth-1 or controller outputs.

Selection runs under the accepted allowlist file-open guard `nb1a_guard.OpenGuard` (read-only reuse). Every
open is recorded in `selection/selection-opened-files.json`, and violations must be 0.

**Evaluation-only inputs**, opened only after the serviceability freeze verifies (section 12):

| file (NB1a run) | sha256 |
|---|---|
| `input/rgb-sensory.npz` (8-bit sRGB proxy) | `cd2600e678fe7f33471e50bee5443128dd5470cc2b380eb7b34a22d3e4ad2c3e` |
| `evaluation/overlap-summary.json` (reference names and per-hypothesis composition) | `1ad980a4a84af7e0e63b6f81360c85c77e3863d7baa324bf45bcdedfe65691cb` |
| `evaluation/overlap-matrix.npz` (sparse H × O cells and sr) | `e4f4bde03d2bfb82cc8a44ab6cbc3b74afec624677051da6fc882c96e502462d` |
| `evaluation/reference-cells.npz` (Object Index, O_0 mask) | `54a58d28eab4ade81c7e945fefb379ce6d13f5a149797324bdbb23f1f84f9f76` |

NB1b opens neither the EXR nor the catalog: the authored names come from the NB1a overlap summary.

## 3. Accepted sensor geometry

Source: the sealed sensor implementation `tools/fsg_geometry.py` (one of the 16 sealed `tools/` root modules,
re-exported as `fov3d.geometry.core`), unchanged since the baseline import `44bf786`:

| item | value |
|---|---|
| git blob | `ad47c1eff6db2b9bd29340fdd633d9c09718d070` |
| sha256 | `ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54` |
| declaration | `CORE_FOV_DEG = 12.0` |
| core geometry | `f = core / (2 * math.tan(math.radians(CORE_FOV_DEG) / 2))` over a square core of `core` pixels |

The accepted measurement core is therefore a **square tangent footprint**: its edges are 6° from the optical
axis. NB1b uses only this nominal angular core geometry. It does not simulate rectification margins,
vergence, stereo matching, occlusion or measurement success.

    a              = CORE_FOV_DEG / 2 = 6°
    R_CENTER       = a                                       (radians(6.0))
    R_FULL         = atan( sqrt(2) * tan(R_CENTER) )         (≈ 8.45°; computed, never a rounded constant)
    ANGLE_EPS_RAD  = 1e-12

Interpretation:
- a spherical disk of radius `R_CENTER` is the orientation-independent central disk inscribed in the nominal
  12° square core;
- a spherical disk of radius `R_FULL` circumscribes the full nominal square core (its corners lie at
  `atan(sqrt(2) tan a)` from the axis);
- therefore, if the `R_FULL` disk lies inside one hypothesis, the nominal square core is conservatively
  contained regardless of in-plane roll.

The selection code takes `CORE_FOV_DEG` from `tools/fsg_geometry.py` itself and verifies the file's hash
first.

## 4. The NB1a seed stays fixed

For each hypothesis H, NB1b uses exactly the frozen NB1a representative seed `(row, col)`. Its direction
`d_s` is the NB1a cell-centre direction of that cell (NB1a contract section 4):

    yaw   = −180° + 0.5°(col + 0.5),   pitch = 90° − 0.5°(row + 0.5)
    d     = (sin yaw cos pitch, sin pitch, −cos yaw cos pitch)          (head frame)

No better seed is searched for, and no seed is moved to make a hypothesis serviceable. The causal question is:
*did NB1a already give us a useful place to look?* The checker verifies that every NB1b seed is field-identical
to the accepted NB1a `seeds.json` and `hypotheses.json`.

## 5. Spherical footprint test (DERIVED)

For each seed direction `d_s` and **every** one of the 259,200 grid-cell centres `d_i`:

    alpha_i = atan2( ||d_s × d_i||, d_s · d_i )

This is the true angular distance on the full sphere. It uses direction vectors, so the longitude seam and the
poles need no special case, and there is no bounding-box prefilter.

    CENTER(H) = { i : alpha_i <= R_CENTER + ANGLE_EPS_RAD }
    FULL(H)   = { i : alpha_i <= R_FULL   + ANGLE_EPS_RAD }

The boundary is inclusive. A cell exactly at the radius (for example 12 rows from the seed along a meridian,
exactly 6°) is inside the footprint.

A footprint is **SAFE** for H iff **every** sampled cell in it has valid NB1a range **and** belongs to H. A
no-geometry cell (label 0) counts as outside the hypothesis.

Recorded for each footprint (descriptive; classification never uses a fraction):
- total sampled cells;
- cells belonging to H;
- cells belonging to other hypotheses, and the number of distinct other hypotheses;
- invalid (no-geometry) cells;
- containment fraction = cells of H / total sampled cells;
- boundary-tie cells, `|alpha_i − R| <= ANGLE_EPS_RAD` (included by the rule);
- SAFE (exact all-or-nothing containment).

The footprints themselves are stored as cell lists, with each FULL-footprint cell's `alpha_i`, in
`selection/footprints.npz`.

## 6. Environment / scene-shell role (declared before evaluation)

    ENVIRONMENT_CANDIDATE  iff  support_sr(H) > 2π steradians

`support_sr` is the NB1a canonical folded spherical support. The rule means "more than one hemisphere of
spherical support". It is geometric, not semantic, and it is declared before any classification; it is not
fitted to H0001.

    ENVIRONMENT_CANDIDATE != semantic "background"

It means only that this connected hypothesis occupies more than half of all viewing directions, so it is
treated separately from localized foreground hypotheses. Hypotheses are disjoint on the sphere, so at most one
can strictly exceed 2π.

Its CENTER and FULL diagnostics are still computed. It is not placed in a foreground look queue, and it is not
deleted.

## 7. Foreground serviceability classes (DERIVED)

Every non-environment hypothesis is classified exactly once. `clearance` is the NB1a seed interior clearance
(`seed.clearance_rad`, equal to `max_interior_clearance_rad`).

| class | rule | interpretation |
|---|---|---|
| `PRIMARY_LOOK` | FULL is SAFE | the complete nominal 12° square core is conservatively support-contained around the existing NB1a seed |
| `SECONDARY_LOOK` | FULL is not SAFE and CENTER is SAFE | the central inscribed disk is support-contained; the square corners may cross the hypothesis boundary |
| `MARGINAL` | CENTER is not SAFE and clearance > 0 | NB1a found a real interior seed, but it is too close to the boundary for even the central 6° disk |
| `EDGE_ONLY` | clearance == 0 | the seed is a boundary cell (or a singleton) |

There are no additional thresholds and no hypothesis deletion. Every accepted NB1a hypothesis appears exactly
once as `ENVIRONMENT_CANDIDATE`, `PRIMARY_LOOK`, `SECONDARY_LOOK`, `MARGINAL` or `EDGE_ONLY`. The total is
exactly the accepted NB1a hypothesis count, 453. No class count is predeclared.

**Partition invariants.** The four rules partition the non-environment hypotheses only if:
1. FULL SAFE ⇒ CENTER SAFE. This always holds, because CENTER ⊆ FULL.
2. clearance == 0 ⇒ CENTER is not SAFE. A zero-clearance seed is a boundary cell or a singleton, so an outside
   8-neighbour lies within about 0.71° < R_CENTER.
3. No clearance is null. NB1a recorded 0 `NO_BOUNDARY_FALLBACK` seeds.

Selection verifies invariants 2 and 3. A violation is a **stop condition** (section 18): the rules would not
partition, and no class is invented.

## 8. What "worth looking at" means in NB1b

The terminology is deliberately conservative:
- `PRIMARY_LOOK` = a robust sensor-qualified candidate;
- `SECONDARY_LOOK` = a plausible candidate with peripheral-boundary risk.

Neither class causes an observation. `MARGINAL` and `EDGE_ONLY` are not ordinary initial active candidates in
this experiment. `ENVIRONMENT_CANDIDATE` is retained separately for future environmental / background
treatment.

**This is not objectness.** A `PRIMARY_LOOK` hypothesis is not asserted to be an object. It is only a natural
range-derived region whose existing seed safely supports the nominal measurement footprint.

## 9. Deterministic queues

Two frozen foreground queues, with no combined, learned or weighted score:
- `selection/primary-look-queue.json`;
- `selection/secondary-look-queue.json`.

Within each queue the order is:
1. descending NB1a interior seed clearance;
2. descending spherical support;
3. ascending temporary hypothesis id.

The environment candidate is recorded separately in `selection/environment-candidate.json`. `MARGINAL` and
`EDGE_ONLY` hypotheses stay in the complete classification table and are not queued. All classifications and
queues are frozen before any reference evaluation.

## 10. Primary measurements (recorded before any reference evaluation)

`selection/selection-summary.json` holds:
- the total hypotheses and the environment, primary, secondary, marginal and edge-only counts;
- per class:
  - total cells and spherical support (`math.fsum` of the NB1a supports);
  - the clearance distribution (NB1a clearance bins, zero counted separately, and quantiles);
  - the range distribution: the per-hypothesis NB1a median range and the seed range, in the NB1a range bins,
    with quantiles;
- for PRIMARY and SECONDARY: the queue order, seed direction (row, column, yaw, pitch, unit vector), seed
  range, and CENTER and FULL containment fractions;
- the failure accounting of the non-environment hypotheses, for CENTER and for FULL:
  - footprints that are not SAFE;
  - footprints containing invalid range (no geometry);
  - footprints containing another hypothesis;
  - footprints failing only through no geometry, only through another hypothesis, or through both.

The environment candidate's own footprint diagnostics are reported separately. The quantiles and bins are
NB1a's declared ones (NB1a contract section 8).

## 11. Freeze

`freeze` writes `selection/serviceability-freeze.json` with the sha256 of:
- `source/nb1a-source-manifest.json` (the NB1a freeze identity and the five verified input hashes);
- `serviceability.json`, `serviceability.csv`, `primary-look-queue.json`, `secondary-look-queue.json`,
  `environment-candidate.json`, `footprint-stats.json`, `footprints.npz`, `selection-summary.json` and
  `selection-opened-files.json`;
- the sensor geometry constants and the `tools/fsg_geometry.py` hash;
- the selection configuration (and its hash) and the selection code files.

Once frozen:
- reference evaluation may begin;
- evaluation may not alter serviceability outputs: `evaluate` refuses to run unless every frozen hash
  verifies, records that verification before its first reference open, never writes into `source/` or
  `selection/`, and re-verifies the freeze afterwards.

Any scientific-rule change after the reference evaluation requires a STOP and a decision by Luiz and Chat.

## 12. Reference / evaluation after the freeze (descriptive only)

Only after the serviceability freeze verifies, `evaluate` reads the evaluation-only inputs of section 2.

For each PRIMARY and SECONDARY candidate it reports:
- the authored ids intersected;
- the O_0 (noncatalog geometry) fraction and the catalog fraction;
- the reference composition (dominant ids by support);
- an RGB appearance descriptor: the mean sRGB over the CENTER footprint. The appearance crop itself is a
  figure (section 13).

For the environment candidate it reports the authored ids intersected, the O_0 fraction and its support
fraction of the sphere. Per class it reports the support-weighted O_0 and catalog fractions, the hypotheses
dominated by O_0, and the most-supported authored ids.

None of this changes a category or a rank. The questions it informs:
- Are the robust candidates visually coherent foreground regions?
- Do robust candidates again recover O_0 / noncatalog furniture?
- What kinds of hypotheses fall into SECONDARY?
- What visual structures are MARGINAL or EDGE_ONLY?
- Does the > 2π rule isolate the apparent scene shell?

The relation to authored identity is reference information, not ground truth. No benchmark, accuracy,
precision, recall or IoU language is used.

## 13. Outputs

Machine-facing evidence, `/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1b-foveal-serviceability/`:

| directory | files |
|---|---|
| `source/` | `nb1a-source-manifest.json` |
| `selection/` | `serviceability.json`, `serviceability.csv`, `primary-look-queue.json`, `secondary-look-queue.json`, `environment-candidate.json`, `footprint-stats.json`, `footprints.npz`, `selection-summary.json`, `selection-opened-files.json`, `serviceability-freeze.json` |
| `evaluation/` | `candidate-reference-summary.json`, `evaluation-opened-files.json` |
| `synthetic/` | `synthetic-report.json` |
| top level | `manifest.json`, `check-summary.json`, `process-log.jsonl` |

Persistent visuals, `/home/lvelho/rd/f3d-vision/visuals/natural-bootstrap-1b-foveal-serviceability/`
(Visual Language 1):
- `overview.png`, with four regions:
  - A, DERIVED (NB1a source): the accepted natural hypotheses and frozen deep-interior seeds;
  - B, SENSOR GEOMETRY / DERIVED: the 12° square core, the 6° central disk and the ≈ 8.45° conservative disk,
    with example footprints;
  - C, DERIVED: the serviceability classification (environment, primary, secondary, marginal, edge-only);
  - D, REFERENCE / EVALUATION, kept secondary: appearance and authored-reference composition of the selected
    candidates;
- `serviceability-panorama.png`: every hypothesis by class, with the seeds;
- `primary-look-panorama.png` and `secondary-look-panorama.png`: the queued candidates, their FULL / CENTER
  footprints and queue ranks, with RGB appearance crops (post-freeze);
- `environment-candidate.png`: the environment candidate, its seed and footprints;
- `footprint-examples.png`: tangent-plane (gnomonic) views of the square core, the two disks and the
  hypothesis support around example seeds chosen by rank;
- `class-counts.png`: class counts and seed clearance by class against R_CENTER and R_FULL;
- `visuals-manifest.json`.

The natural hypotheses and the sensor-fit result are primary; authored identity stays secondary.

Glyphs:

| glyph | meaning |
|---|---|
| ink diamond | NB1a seed (as NB1a) |
| solid ring | FULL footprint boundary (R_FULL disk) |
| thin dotted ring | CENTER footprint boundary (R_CENTER disk) |
| square outline | nominal 12° measurement core (tangent-plane views) |
| class fill + glyph | serviceability class; every class also has a non-colour cue |
| stipple | environment candidate |
| hatched | no geometry |
| brown | authored reference (evaluation panels only) |

## 14. Checks (`tools/natural_bootstrap/check_nb1b.py`)

The checker keeps literal copies of the constants. It recomputes independently:
- its own grid directions;
- angular distance via the chord formula `2 asin(||d_s − d_i|| / 2)`;
- the footprints, the containment and the classes from the frozen NB1a labels, seeds, clearances and
  supports;
- the queue order;
- the reference composition.

1. The accepted NB1a source: the freeze record hash, every NB1a frozen product against it, the NB1a discovery
   code hashes, and the acceptance commit `dcd294f` as an ancestor of HEAD.
2. No Blender invocation: no Blender process in the process log; the Breadth-1 render directory is unchanged.
3. No controller invocation: the process log holds only NB1b commands; no controller module is imported.
4. All 453 accepted NB1a hypotheses are preserved, with their ids, labels, cells and supports.
5. The NB1a seeds are field-identical (no reseeding), and each seed direction is its NB1a cell-centre
   direction.
6. The selection path opened no RGB.
7. The selection path opened no Object Index, catalog, EXR or evaluation file. Its data reads are exactly the
   five pinned inputs, with 0 violations; the guard self-test blocks a forbidden open; the selection code
   imports only declared modules.
8. The accepted sensor source still declares `CORE_FOV_DEG = 12.0` and has the pinned hash; the run used that
   value.
9. R_CENTER = 6°.
10. R_FULL recomputes independently from `atan(sqrt(2) tan 6°)` and from the corner direction of the square
    core.
11. Spherical angular distance recomputes independently (stored FULL-footprint `alpha_i`).
12. The CENTER footprints recompute exactly (cell sets and counts).
13. The FULL footprints recompute exactly.
14. Invalid cells count as unsafe.
15. The environment criterion is exactly `support_sr > 2π`.
16. There is at most one environment candidate.
17. Every hypothesis gets exactly one category.
18. PRIMARY iff non-environment and FULL SAFE.
19. SECONDARY iff non-environment, FULL not SAFE and CENTER SAFE.
20. MARGINAL iff non-environment, CENTER not SAFE and clearance > 0.
21. EDGE_ONLY iff non-environment and clearance == 0.
22. No hypothesis was filtered, deleted, merged or split; the NB1a label raster is unchanged.
23. The queue ordering recomputes.
24. The environment candidate is excluded from the foreground queues, which hold exactly the PRIMARY and
    SECONDARY hypotheses.
25. The freeze hashes matched before evaluation.
26. Evaluation did not modify the frozen outputs, and wrote only under `evaluation/`.
27. RGB and reference data were opened only after the freeze verification, and never by selection.
28. No evaluation datum affects classification or rank: the frozen classes and queues equal the pure-geometry
    recomputation, and the selection products carry no evaluation-derived field.
29. The figures regenerate deterministically (byte-identical).
30. `fov3d/`, the controllers, `tools/fsg_geometry.py` and the accepted NB1a files and run products are
    unchanged.
31. The changed tracked files are only the declared NB1b files and the layout declaration.
32. The synthetic known answers (section 15) pass in the generator and in the checker's independent
    re-implementation.
33. The reference evaluation recomputes from the pinned NB1a reference products.

## 15. Synthetic known answers (no Blender, no Classroom)

Synthetic label rasters, hypothesis records and seeds exercise the classification:
- a component with a FULL-safe seed → `PRIMARY_LOOK`;
- a disk of radius 7° (CENTER safe, FULL not) → `SECONDARY_LOOK`;
- a disk of radius 3° with positive clearance → `MARGINAL`;
- a zero-clearance strip → `EDGE_ONLY`;
- a component of more than 2π (a hemisphere plus one row) → `ENVIRONMENT_CANDIDATE`, and a hemisphere minus
  one row → not environment;
- an invalid cell inside the footprint → unsafe;
- an other-hypothesis cell inside the footprint → unsafe;
- a footprint across the longitude seam: its cell set is the yaw-shift of the same footprint away from the
  seam, and a no-geometry cell across the seam makes it unsafe;
- a near-pole footprint (crossing the pole);
- an exact radius-boundary tie: a no-geometry cell exactly 6° away along the meridian makes CENTER unsafe; the
  same cell 6.5° away does not.

## 16. Corruption / mutation suite (`--corruptions`)

Corruptions are planted in throwaway mirrors or as in-process mutants. They count only when the uncorrupted
baseline passes every check. The list:
- `CORE_FOV_DEG` changed in the sensor source;
- R_CENTER of 5.5° or 6.5° instead of 6°;
- R_FULL as `sqrt(2) · 6°` instead of the tangent / corner geometry;
- invalid cells omitted from footprint failure;
- seam handling broken (cells across the seam dropped);
- an NB1a seed moved;
- one PRIMARY reclassified as SECONDARY;
- the environment candidate placed in the primary queue;
- the > 2π rule changed to a fitted threshold;
- an EDGE_ONLY hypothesis deleted;
- a queue reordered;
- RGB altering a category;
- Object Index read before the freeze;
- a frozen output modified after evaluation;
- a Blender command and a controller command in the process log;
- a visual pixel altered;
- `fov3d`, controller or NB1a code modified;
- a footprint statistic altered, and a reference composition value altered.

Markers: `NATURAL_BOOTSTRAP1B_CHECKS_PASS`, `NATURAL_BOOTSTRAP1B_MUTATIONS_CAUGHT`.

## 17. Commands, order and cost classes (PROPOSED estimates)

The tools are `tools/natural_bootstrap/nb1b_{spec,serviceability,run,visuals}.py` and `check_nb1b.py`.
The accepted `nb1a_spec.py` (grid geometry) and `nb1a_guard.py` (file-open guard) are reused read-only.

    RUN=/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1b-foveal-serviceability
    VIS=/home/lvelho/rd/f3d-vision/visuals/natural-bootstrap-1b-foveal-serviceability
    .venv/bin/python tools/natural_bootstrap/nb1b_run.py synthetic --run $RUN                  # interactive
    .venv/bin/python tools/natural_bootstrap/nb1b_run.py select    --run $RUN                  # interactive
    .venv/bin/python tools/natural_bootstrap/nb1b_run.py freeze    --run $RUN                  # interactive
    .venv/bin/python tools/natural_bootstrap/nb1b_run.py evaluate  --run $RUN                  # interactive
    .venv/bin/python tools/natural_bootstrap/nb1b_run.py visualize --run $RUN --visuals $VIS   # interactive–batch
    .venv/bin/python tools/natural_bootstrap/check_nb1b.py --run $RUN --visuals $VIS --corruptions --write-summary   # batch

**Order:**
1. Implement the tools.
2. Pass the synthetic known answers, and run the whole pipeline on a scratch copy of synthetic NB1a-like
   products.
3. Run the layout checker and `git diff --check`.
4. Commit and push the implementation.
5. Run exactly **one** canonical selection on the accepted frozen NB1a result. There is no scene observation
   in NB1b.
6. Freeze, evaluate, visualize and check.

`select` refuses to overwrite an existing `selection/`. After the freeze, the serviceability rules are not
changed on the basis of the evaluation.

## 18. Acceptance, stop conditions and permitted fixes

On successful execution, with all checks passing and the corruptions caught from a passing baseline, the report
`docs/natural-bootstrap/nb1b-foveal-serviceability-report.md` records
`NATURAL_BOOTSTRAP1B_FOVEAL_SERVICEABILITY_COMPLETE` with status **REVIEW PENDING**. No ACCEPTED marker is
written, and the branch is not merged.

**Stop and return to Luiz/Chat on any of these:**
- an NB1a source hash mismatch, or a hypothesis count other than 453;
- the sensor source changed (hash, or `CORE_FOV_DEG` ≠ 12.0);
- any truth-firewall violation in selection;
- a partition invariant violated (section 7);
- the need to change the footprint radii, the containment rule, the environment rule, the class rules or the
  queue order;
- any serviceability change after the reference evaluation has been viewed.

Implementation defects inside the new NB1b tools may be repaired before the canonical selection. After the
freeze, only presentation and serialization repairs that leave the frozen products unchanged may proceed.

Unchanged by this step:
- `fov3d/`, the controllers, the FSG code (including `tools/fsg_geometry.py`) and the accepted renderers;
- the NB1a tools, documents and run products;
- the Breadth-1 tools and outputs, and Visual Language 1;
- the 234-object catalog.

No PRIMARY or SECONDARY look is executed. Controller-02 integration, RGB segmentation and Natural Bootstrap-2 are
not started.
