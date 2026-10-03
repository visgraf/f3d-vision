# Natural Bootstrap-1b — Foveal Serviceability — report

**Marker.**

    NATURAL_BOOTSTRAP1B_FOVEAL_SERVICEABILITY_COMPLETE

**Status: REVIEW PENDING.** Luiz and Chat review the result. No ACCEPTED marker is written, and the branch is not
merged.

> **Question.** Which frozen NB1a natural hypotheses have an existing deep-interior seed that can safely
> accommodate the current foveal measurement footprint?

**The claim is modest.** NB1b is a sampled spherical support-containment test of the nominal 12° square
measurement core, at the unchanged NB1a seeds. It does not claim stereo success, visibility or objectness.
It is read-only on the accepted NB1a products.

Every check passed (33/33), and every corruption was caught from a passing baseline (30/30).

Contract: `docs/natural-bootstrap/nb1b-foveal-serviceability-contract.md`. MEASURED means produced by the runs
below.

## Branch and commits

| item | value |
|---|---|
| branch | `natural-bootstrap/nb1b-foveal-serviceability`, from `main` @ `9c01b8a` (NB1a accepted at `dcd294f`); isolated worktree |
| contract | `aaeb095` *Contract NB1b foveal serviceability* |
| implementation (frozen before the canonical selection) | `c1e273a` *Implement NB1b foveal serviceability* |
| canonical run | synthetic, select, freeze, evaluate and visualize, all at `c1e273a` (clean, pushed; `process-log.jsonl`) |
| report | this commit |

`fov3d/`, the controllers, `tools/fsg_geometry.py` and every accepted NB1a file are byte-identical to `9c01b8a`.
The changed tracked files are only the declared NB1b files and the layout checker (checks 30–31).

## Source, sensor and truth boundary

**Frozen NB1a input** (`/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1a-range-connectivity/`): the five
selection inputs verified against the pinned hashes:

| file | sha256 |
|---|---|
| `discovery/bootstrap-freeze.json` (the NB1a freeze identity) | `c0236d04…` |
| `discovery/hypothesis-raster.npz` | `513a15e0…` |
| `discovery/hypotheses.json` | `eecf180f…` |
| `discovery/seeds.json` | `c0362d9c…` |
| `discovery/discovery-summary.json` | `fac0adb3…` |

The whole NB1a run tree (22 files) and the NB1a figures are unchanged (check 30).

**Sensor geometry.** The source is `tools/fsg_geometry.py` (blob `ad47c1ef…`, sha256 `ae3779bc…`), which declares
`CORE_FOV_DEG = 12.0`:
- R_CENTER = 6°;
- R_FULL = atan(√2 · tan 6°) = 8.4545°, computed;
- ANGLE_EPS_RAD = 1e-12.

The checker re-derives R_FULL from the corner direction of the square core, to within 1e-15 rad.

**Two guarded paths** (`nb1a_guard.OpenGuard`, reused read-only):

| path | data reads | writes | violations |
|---|---|---|---|
| **selection** | **exactly the five NB1a discovery files above** | `source/` (1 file), `selection/` (8 files) | **0** |
| evaluation | the frozen selection products, verified first (`freeze_verified`, then `reference_access_begins`), then the NB1a `rgb-sensory.npz`, `overlap-summary.json`, `overlap-matrix.npz` and `reference-cells.npz` (hash-verified) | `evaluation/` | 0 |

Selection did not open:
- RGB;
- the EXR, Object Index or catalog;
- NB1a evaluation products;
- Breadth-1 or controller outputs.

The selection code imports only `json`, `math`, `numpy`, `pathlib`, `sys`, `nb1a_spec`, `nb1a_discovery`
(binning helpers), `nb1b_spec` and `fsg_geometry` (check 7). Evaluation opened neither the EXR nor the catalog.

Truth classes (Visual Language 1; nothing is CONTROLLER-TIME):

| class | products |
|---|---|
| DERIVED | footprints, containment, classes, queues, environment candidate |
| ORACLE INPUT | the RGB proxy, shown post-freeze as appearance crops |
| REFERENCE / EVALUATION | the authored / O_0 composition |

## Pure serviceability results (MEASURED; recorded before any reference evaluation)

Selection took 5.98 s. Freeze record: `selection/serviceability-freeze.json` `f99b7cae…`.

| class | hypotheses | cells | support (sr) | % of 4π |
|---|---|---|---|---|
| `ENVIRONMENT_CANDIDATE` | **1** | 220,221 | 10.3815 | 82.61 |
| `PRIMARY_LOOK` | **2** | 8,961 | 0.4589 | 3.65 |
| `SECONDARY_LOOK` | **3** | 7,191 | 0.2610 | 2.08 |
| `MARGINAL` | **81** | 17,884 | 1.1113 | 8.84 |
| `EDGE_ONLY` | **366** | 1,501 | 0.0945 | 0.75 |
| total | **453** | 255,758 | | |

The total is exactly the accepted NB1a hypothesis count. No hypothesis was filtered, merged or split, and no seed
moved.

**Seed clearance by class** (degrees, quantiles 0 / 50 / 100 %):
- environment: 50.947;
- primary: 8.500 / 10.802 / 13.105;
- secondary: 6.000 / 6.163 / 8.092;
- marginal: 0.270 / 1.280 / 11.841 (95 % 5.000, 99 % 8.440);
- edge-only: 0 for all 366.

The 87 positive NB1a clearances split 1 + 2 + 3 + 81, and the 366 zero-clearance seeds are exactly the edge-only
class.

**Median range by hypothesis** (m, 0 / 50 / 100 %):
- environment: 1.955;
- primary: 0.529 / 0.625 / 0.721;
- secondary: 0.587 / 0.872 / 1.081;
- marginal: 0.714 / 2.244 / 4.871;
- edge-only: 1.078 / 2.719 / 6.927.

Seed ranges follow the same pattern (primary 0.599–0.681 m, secondary 0.609–1.050 m).

**Failure accounting** (452 non-environment hypotheses):

| footprint | not SAFE | containing no geometry | containing another hypothesis | only no geometry | only another hypothesis | both |
|---|---|---|---|---|---|---|
| CENTER | 447 | 62 | 447 | **0** | 385 | 62 |
| FULL | 450 | 81 | 450 | **0** | 369 | 81 |

Every failing footprint contains another hypothesis. Invalid range never fails a footprint on its own here.

**Partition invariants** held:
- no zero-clearance seed has a SAFE CENTER footprint;
- there is no null clearance.

Every one of the 453 CENTER footprints contains exactly two boundary-tie cells (exactly 6° away along the
meridian), included by the inclusive rule; no FULL footprint has a tie cell.

## Environment result (MEASURED)

**H0001** is the only hypothesis above 2π sr (10.3815 sr, 82.6 % of the sphere). It is therefore the
`ENVIRONMENT_CANDIDATE`. It is not queued and not deleted.

Its own footprint diagnostics at its NB1a seed (yaw 178.25°, pitch 45.75°, behind and above, range 2.37 m;
clearance 50.95°):
- CENTER 647 / 647 SAFE;
- FULL 1291 / 1291 SAFE.

Geometrically it would qualify as PRIMARY; the declared role rule set it apart first. Its FULL footprint crosses
the longitude seam (the seed is 1.75° of yaw from it) and recomputes exactly.

## Primary queue (MEASURED; frozen)

Order: clearance desc, support desc, id.

| rank | id | clearance | support (sr) | cells | seed (row, col) | yaw, pitch (°) | seed range (m) | seed direction (head) | CENTER | FULL |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | **H0002** | 13.105° | 0.3157 | 6,672 | (265, 261) | −49.25, −42.75 | 0.599 | (−0.5563, −0.6788, −0.4793) | 613 / 613 = 1.0 | 1229 / 1229 = 1.0 |
| P2 | **H0003** | 8.500° | 0.1432 | 2,289 | (252, 63) | −148.25, −36.25 | 0.681 | (−0.4244, −0.5913, 0.6858) | 555 / 555 = 1.0 | 1115 / 1115 = 1.0 |

For both, the complete nominal 12° square core is conservatively support-contained at any roll around the
existing NB1a seed.

## Secondary queue (MEASURED; frozen)

| rank | id | clearance | support (sr) | cells | seed (row, col) | yaw, pitch (°) | seed range (m) | seed direction (head) | CENTER | FULL |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 | **H0009** | 8.092° | 0.0703 | 3,448 | (31, 359) | −0.25, 74.25 | 1.050 | (−0.0012, 0.9625, −0.2714) | 1683 / 1683 = 1.0 | 3260 / 3423 = 0.952 |
| S2 | **H0006** | 6.163° | 0.0967 | 1,764 | (257, 115) | −122.25, −38.75 | 0.609 | (−0.6596, −0.6259, 0.4162) | 579 / 579 = 1.0 | 966 / 1145 = 0.844 |
| S3 | **H0007** | 6.000° | 0.0940 | 1,979 | (284, 173) | −93.25, −52.25 | 0.862 | (−0.6112, −0.7907, 0.0347) | 739 / 739 = 1.0 | 1140 / 1469 = 0.776 |

In each case the central 6° disk is contained, and the FULL disk reaches 1–4 other hypotheses (163, 179 and 329
cells). H0009 sits overhead at pitch 74.25°: its CENTER and FULL footprints span many columns and recompute
exactly.

## Reference / evaluation findings (MEASURED; after the freeze; descriptive only)

The freeze verified before the first reference open (checks 25, 27), and the frozen products verified again
afterwards (check 26). Nothing here changed a class or a rank (check 28). These are not ground-truth
comparisons: no accuracy, precision, recall or IoU.

| candidate | authored ids intersected | O_0 fraction | dominant reference | FULL-footprint cells: O_0 / catalog | mean sRGB in CENTER |
|---|---|---|---|---|---|
| P1 H0002 | 0 | **100 %** | O_0 | 1229 / 0 | (117, 91, 68) |
| P2 H0003 | 0 | **100 %** | O_0 | 1115 / 0 | (111, 86, 63) |
| S1 H0009 | 1 | 0 % | `Cube.006` 100 % | 0 / 3423 (`Cube.006` 3260, `beams` 163) | (255, 255, 255) |
| S2 H0006 | 0 | **100 %** | O_0 | 1065 / 80 (`sol`) | (77, 53, 30) |
| S3 H0007 | 0 | **100 %** | O_0 | 1290 / 179 (`sol`) | (72, 49, 29) |

**Environment H0001:**
- it intersects 123 authored ids; O_0 is 5.6 % of its support, catalog 94.4 %;
- its largest reference ids are `beams` 29.9 %, `sol` 21.2 %, `woodBase` 11.1 %, then `wall` and `wall.010`;
- its FULL footprint lands almost entirely on `beams` (1283 of 1291 cells; 8 O_0).

**Per class** (support-weighted):

| class | O_0 fraction | hypotheses dominated by O_0 | largest authored ids |
|---|---|---|---|
| environment | 5.6 % | 0 / 1 | `beams`, `sol`, `woodBase` |
| primary | 100 % | 2 / 2 | — |
| secondary | 73.1 % | 2 / 3 | `Cube.006` 26.9 % |
| marginal | 57.7 % | 41 / 81 | `sol` 33.0 %, `Cube.006`, `woodBase` |
| edge-only | 72.1 % | 225 / 366 | `sol`, `Box25.001`, `Box25.002`, `Cube.005` |

**Answers to the contract's questions** (descriptive, from the figures and these numbers):
- **Are the robust candidates visually coherent foreground regions?** Yes, on the RGB proxy. Both PRIMARY tiles show
  a single brown, wood-like surface filling the whole core, 0.6–0.7 m away, below the horizon. They are the two
  largest near-foreground hypotheses.
- **Do robust candidates again recover O_0 / noncatalog furniture?** Yes. Both PRIMARY candidates are 100 % O_0
  (the collection-instanced geometry that carries no catalog id), and so are their whole FULL footprints.
- **What falls into SECONDARY?**
  - two more O_0 near-foreground surfaces, H0006 and H0007, whose square corners reach the floor (`sol`) and
    neighbouring pieces;
  - one nearly overhead catalog surface, H0009 (`Cube.006`, about 1.05 m away at pitch 74°, saturated white on
    the RGB proxy).
- **What is MARGINAL or EDGE_ONLY?**
  - MARGINAL: the rest of the positive-clearance pieces. These include the near-foreground H0004 and H0005, the
    fragmented clusters to the right (yaw 60–150°), and floor pieces (`sol` 33 % of marginal support).
  - EDGE_ONLY: the 366 boundary-dominated slivers and singletons (1,501 cells in total): the thin, grazing
    geometry that NB1a already described.
- **Does the > 2π rule isolate the apparent scene shell?** Yes. Exactly one hypothesis exceeds it, H0001, the room
  shell of 123 authored ids (beams, floor, walls). Its seed looks at the ceiling beams.

## Visual products (Visual Language 1)

Persistent, under `/home/lvelho/rd/f3d-vision/visuals/natural-bootstrap-1b-foveal-serviceability/`, drawn at
`c1e273a`:

| file | truth badges | sha256 |
|---|---|---|
| `overview.png` | DERIVED, ORACLE INPUT, REFERENCE / EVALUATION | `417084b6542c3a474c6f9cef463c65e18b480769da9d5f9aa18624fb70e7abb5` |
| `serviceability-panorama.png` | DERIVED | `f6a25f5da37611a23a2fffa94d60673515372b1629c74bd32a0640cffd602ee1` |
| `primary-look-panorama.png` | DERIVED, ORACLE INPUT | `56771f2f2868181c9b7fb1c461877cc93c528b91a45a0ad3a31155d455161e65` |
| `secondary-look-panorama.png` | DERIVED, ORACLE INPUT | `f54cc38a6184cff4e89b10c1d9b636fee10aa45c03f8fb08a16a78f40c1477bf` |
| `environment-candidate.png` | DERIVED, REFERENCE / EVALUATION | `30a579380cda014df98b5ca184289055c5878e8ab5f980ae73cf81e6afaaa1fa` |
| `footprint-examples.png` | DERIVED | `bab8bb95177e5dc62d9e6d53205e430cb072a87a399b0b5beb1e7b67a02c201b` |
| `class-counts.png` | DERIVED | `4bf194e6d3da13b53ed4a8deb607f12318892ce4065b87b8b1ffd41032a48c53` |
| `visuals-manifest.json` | — | `1d7e2a7c822e2e57192e4a64ce3e4af5e6a6f4a0ceb5631ed2e1e7a60a53398e` |

The overview has four regions:
- A, DERIVED: the NB1a hypotheses and frozen seeds;
- B, DERIVED: the 12° square core with its 6° inscribed and 8.45° circumscribed disks, plus two tangent-plane
  footprint examples (P1, S1);
- C, DERIVED: the classification, with FULL (solid) and CENTER (dotted) rings at queued seeds;
- D, REFERENCE / EVALUATION, kept secondary: RGB appearance crops and O_0 / catalog bars of the queued
  candidates, and the per-class composition.

`footprint-examples.png` shows, in the tangent plane at each seed, the support around P1, S1, P2, the deepest
marginal (H0004), the largest edge-only and the environment. Examples are chosen by rank only.

Minor presentation issues, not repaired:
- in overview region D, an O_0-dominant label is truncated ("O_0 (index 0, no…");
- in `class-counts.png`, the 1-, 2- and 3-count bars are thin next to 366 (each bar carries its count).

Regenerate the figures with:

    .venv/bin/python tools/natural_bootstrap/nb1b_run.py visualize --run $RUN --visuals $VIS

## Machine evidence

Under `/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1b-foveal-serviceability/` (4.9 MB):

| file | sha256 |
|---|---|
| `source/nb1a-source-manifest.json` | `ef919200…` |
| `selection/serviceability.json` | `2c83d76c…` |
| `selection/serviceability.csv` | `d0086206…` |
| `selection/primary-look-queue.json` | `1cc867b1…` |
| `selection/secondary-look-queue.json` | `5481497c…` |
| `selection/environment-candidate.json` | `427346e9…` |
| `selection/footprint-stats.json` | `ca60a3fa…` |
| `selection/footprints.npz` | `8c00fa5a…` |
| `selection/selection-summary.json` | `da815b9a…` |
| `selection/selection-opened-files.json` | `391890cd…` |
| `selection/serviceability-freeze.json` | `f99b7cae…` |
| `evaluation/candidate-reference-summary.json` | `11e74b9a…` |
| `evaluation/evaluation-opened-files.json` | `20c9d48a…` |
| `synthetic/synthetic-report.json` | `7fd35509…` |
| `manifest.json` | `c7caa630…` |
| `check-summary.json` | `f6516931…` |

`process-log.jsonl` (`8347ff26…`) holds the five NB1b commands only, all `ok`, clean and pushed at `c1e273a`.

## Checks (MEASURED)

`tools/natural_bootstrap/check_nb1b.py` at `c1e273a`: **33/33** (`NATURAL_BOOTSTRAP1B_CHECKS_PASS`;
`check-summary.json`). It recomputes independently:
- its own grid directions;
- chord-formula angular distances: the stored α of every FULL-footprint cell agrees to within 1e-14 rad;
- every CENTER and FULL footprint as an exact cell set, with its statistics;
- the classes as "exactly one rule holds": all 453 hypotheses match exactly one rule;
- the queue order;
- the reference composition from the NB1a overlap matrix.

It also confirms:
- R_FULL from atan(√2 tan 6°) and from the square-core corner direction;
- the synthetic known answers: 17/17 in the generator, and the checker's own 17 independent cases.

The synthetic cases cover:
- PRIMARY, SECONDARY, MARGINAL, EDGE_ONLY;
- a hemisphere plus one row (environment) and minus one row (not);
- an invalid cell and an other-hypothesis cell inside the footprint;
- the seam footprint as the yaw-shift of the interior one, and a no-geometry cell across the seam;
- a pole-crossing footprint and a small polar cap;
- the exact 6° meridian tie (unsafe) and the same cell at 6.5° (safe);
- tight R_FULL and R_CENTER disks;
- the partition-invariant STOP.

**Corruption / mutation suite: 30/30 caught from a passing baseline** (`NATURAL_BOOTSTRAP1B_MUTATIONS_CAUGHT`).

| defect | target(s) |
|---|---|
| `CORE_FOV_DEG` changed in the sensor source | 08 |
| R_CENTER 5.5° (regenerated) | 09, 12 |
| R_CENTER 6.5° (regenerated) | 09, 12 |
| R_FULL = √2 · 6° (regenerated) | 10, 13 |
| invalid cells omitted from failure (regenerated) | 14, 32 |
| seam handling broken (regenerated) | 12, 13 |
| > 2π replaced by a fitted 0.3 sr threshold (regenerated) | 15 |
| an NB1a seed moved (H0002) | 05 |
| a PRIMARY reclassified as SECONDARY (H0002) | 18 |
| a MARGINAL relabelled EDGE_ONLY (H0004) | 20, 21 |
| the environment candidate placed in the primary queue | 24 |
| an EDGE_ONLY hypothesis deleted (H0453) | 22 |
| a queue reordered | 23 |
| RGB altered a category (H0004) | 28 |
| selection read Object Index | 07 |
| selection opened RGB | 06 |
| evaluation read a reference product before the freeze verification | 27 |
| a frozen output modified after evaluation | 26 |
| a Blender command in the process log | 02 |
| a controller command in the process log | 03 |
| a visual pixel altered | 29 |
| `fov3d` modified | 30 |
| controller code modified | 30 |
| NB1a code modified | 30 |
| an NB1a frozen product altered | 01 |
| a footprint statistic altered | 12 |
| a stored angular distance altered | 11 |
| a FULL footprint cell dropped | 13 |
| a reference composition value altered | 33 |
| a synthetic case failed | 32 |

"Regenerated" mutants rebuild the selection and the synthetic report with the wrong variant. A mutant counts as
caught when any of its listed target checks fails. The invalid-cells mutant changes no canonical output, because no
canonical footprint fails through no geometry alone. It is caught by the synthetic known answers (check 32), as
intended.

Other gates:
- `check_nb1b.py` re-run with this report staged: 33/33 (no corruptions, no summary write);
- layout 536/536;
- `scripts/verify_baseline.sh` 9/9;
- `git diff --check` clean.

Cost (MEASURED):
- synthetic 0.6 s, select 6.0 s, freeze, evaluate and visualize under 1 s each;
- the checker with corruptions 51 s (batch).

## Incidents

**Before the canonical selection** (implementation, on synthetic data only):
1. Two tight-radius synthetic cases were added (a disk of exactly R_FULL, and one of exactly R_CENTER), so that
   the generator's known answers themselves reject R_FULL = √2 · 6° and R_CENTER = 6.5°.
2. `regenerate` in the checker tolerates a mutant whose selection would STOP on the partition invariant.
3. Figure layout fixes on the scratch dev run:
   - overlapping tile captions;
   - the radius-label collision;
   - the region-D title;
   - the clearance axis range.
4. A scratch dev harness, not committed, ran the whole pipeline on synthetic NB1a-like products. It built an
   analytic room with spheres and processed it with the accepted NB1a discovery code; no Classroom data was
   read. Results: 33/33 checks, 30/30 corruptions, all five classes exercised.
5. Worktree setup: the first `verify_baseline` failed `classroom-assets` because the new worktree lacked the
   gitignored `scenes/classroom/textures` and `ReadMe.txt` links. Adding the links gave 9/9. No tracked change.

**The canonical selection:** no failure, no repeat. No change after the freeze.

**Finding that needs judgment (not an NB1b defect): NB1a clearance is a graph distance, not an angular guarantee.**

Three MARGINAL hypotheses have NB1a seed clearance ≥ 6° yet an unsafe CENTER footprint: H0004 (11.84°), H0042
(7.59°) and H0013 (6.25°). H0004 is the clearest case. It is one of the "largest near-foreground hypotheses
(seeds 5–13° deep)" in the NB1a acceptance record:
- its CENTER disk is only 97 / 585 own cells (16.6 %);
- a cell of another hypothesis lies 0.77° from its seed.

Post-freeze diagnostic of the frozen NB1a raster and continuity edges (no RGB, no reference):
- the seed (259, 591) sits in a 4-column strip of H0004, flanked by H0025 and H0001;
- **7 of its 8 continuity edges are cut** (C up to 21.8, against C_MAX 3.86), and only the edge straight up is
  retained;
- range steps 0.79 → 0.73 → 0.63 m across adjacent columns: a grazing strip.

NB1a defines clearance as multi-source Dijkstra along *retained* edges from *label* boundary cells. The seed's
clearance (10.3 → 11.8° down column 591) is therefore the length of a long vertical retained path, while a label
boundary lies 0.4° away.

This is NB1a's declared semantics, verified by its checker. NB1b's direct footprint test is what exposes it. NB1b
did not move the seed or change the class rules, as the contract requires. Whether later work should prefer an
angular clearance, or treat such seeds differently, is a decision for Luiz and Chat.

## Statements

- **No Blender render** (check 2): no Blender process; the Breadth-1 render directory is unchanged.
- **No controller** (check 3): only NB1b commands ran, and no controller module is imported.
- **No RGB influence on selection** (checks 6, 27, 28): selection opened no RGB. RGB was read only after the
  freeze, for appearance crops and descriptors.
- **No Blender identity influence on selection** (checks 7, 27, 28): selection opened no Object Index, catalog or
  evaluation product. The reference composition was computed only after the freeze.
- **No seed moved** (check 5): every seed is field-identical to the accepted NB1a `seeds.json` and
  `hypotheses.json`.
- **No hypothesis modified** (checks 4, 22): all 453 hypotheses are preserved, with identical ids, labels, cells
  and supports; the NB1a label raster is unchanged.
- No PRIMARY or SECONDARY look was executed. Nothing caused an observation.

## Interpretation for the review (descriptive; no decision)

1. **The sensor-qualified set is small.** Of 453 temporary hypotheses:
   - 2 can host the full nominal 12° square core at their existing NB1a seed;
   - 3 more can host its central 6° disk;
   - one connected scene shell is set apart by the > 2π rule.
2. **The robust candidates are near-foreground noncatalog surfaces.** H0002 and H0003 are about 0.6–0.7 m away,
   wood-like on the RGB proxy and 100 % O_0. The NB1a observation that range continuity recovers furniture
   absent from the authored catalog carries over to sensor-qualified look-worthiness.
3. **The square corners matter.** The three SECONDARY hypotheses contain the 6° disk but not the 8.45° disk. Their
   corners reach the floor or neighbouring pieces (FULL containment 0.78–0.95).
4. **The shell is cleanly isolated.** H0001 alone exceeds 2π sr. At its own seed it is fully serviceable (the
   ceiling beams), so the role rule, not the footprint, keeps it out of the foreground queues.
5. **The NB1a clearance overstates angular room for grazing strips** (H0004; see "Incidents"). The footprint test,
   not the NB1a clearance, decides serviceability.

## Unresolved decisions

1. Qualitative and scientific review of NB1b and its figures (Luiz and Chat).
2. Whether seed selection should later use an angular (footprint-based) clearance, given the H0004 / H0042 /
   H0013 finding. NB1a seeds were kept fixed here by contract.
3. What, if anything, follows for the 81 MARGINAL hypotheses and the environment candidate. They are out of scope
   for NB1b.

NB1b is not merged. No PRIMARY or SECONDARY look was executed. Controller-02 integration, RGB segmentation and
Natural Bootstrap-2 are not started.
