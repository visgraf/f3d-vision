# North Star-1b — Recentered Local-Controller Handoff — One Action — report

**Markers.**

    NORTH_STAR1B_RECENTERED_CONTROLLER_HANDOFF_COMPLETE
    NORTH_STAR1B_RECENTERED_CONTROLLER_HANDOFF_ACCEPTED

**Status: ACCEPTED.** Luiz and Chat accepted NS1b as **Outcome 1** after scientific review, independent GitHub
implementation review, checker / corruption review and qualitative visual inspection of the three figures (see
"Acceptance record" at the end). The bootstrap-to-controller bridge is established; North Star-1c (coherent multi-entity
control, first scene switch) is next. The sections below are the report as completed at `8155c2d`, unchanged.

> **Question.** Can one persistent entity seed produced by the global 360° RGB bootstrap be handed to the accepted local
> FSG6f -> Cyclopean / Controller-02 control semantics through a temporary recentered POLICY COORDINATE CHART, such that
> the controller selects a valid new world fixation and exactly one PERFECT local measurement is fused back into the
> canonical H0 map?

**Answer (MEASURED, one canonical run): yes. My reading is Outcome 1.**
- The frozen rule selected **entity 172**, initialized at NS1a gaze rank 6. It derived this from the frozen data; 172 was
  not forced.
- In the temporary chart C, the unchanged accepted FSG6f proposed **local (0°, −5°)**. That is H0 world gaze
  **(−155.008°, +33.636°)**, 5.00° from the seed gaze.
- The adapted Controller-02 gate **admitted** it: 12 novel serviceable support elements.
- **One** fixed-head 4096-spp binocular observation was rendered there.
- The PERFECT / spherical measurement gave 18,525 target points.
- These were fused into the canonical-H0 map with the accepted 12-mm rule:
  - **9,354 points matched existing surfels** (8,601 surfels affected). This is the first genuine North-Star 12-mm
    overlap.
  - **9,171 points became new surfels.**
  - The map grew from 12,072 to 21,243 surfels.
- The one read-only post-action probe is still ACTIONABLE: FSG6f proposes local (−5°, −10°). It was not executed.

The chart was necessary: run without it, the accepted FSG6f refuses this seed (`too few map points for frontier`). None
of its 12,072 surfels lies in the H0 forward hemisphere that the accepted code requires.

The physical head did not move. Chart C is a POLICY COORDINATE CHART only. Every eye centre, calibration, projection,
observability test and acquisition stayed in canonical H0, and the fusion ran in H0.

Truth labels:
- CORRESPONDENCE: PERFECT / ORACLE.
- IDENTITY: ORACLE SEGMENTATION AID.
- GEOMETRY: DERIVED spherical geometry.
- CONTROLLER OBSERVATION STATE: the accepted Classroom matcher (the Controller-01 controller-time oracle).

## 1. Provenance

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (verified by `source` and check 01) |
| NS1a acceptance | `37c7e026f2ab514be392cd845d390fab2a2d86fc` (`NORTH_STAR1A_PERFECT_BOOTSTRAP_ROUND_ACCEPTED`) |
| base (post-NS1a roadmap, `main`) | `889373d9c174c1c63ebc8d2f79847dbec281f2e8` |
| branch | `north-star/ns1b-recentered-controller-handoff`, from the base, isolated worktree |
| contract | `1e641e66eac46be551b425d2f14a06e9607d533f` (before any implementation, probe or render; unchanged since, check 01) |
| implementation | `40eaf7e6d107472db201c8a25bde55190780fca0` (every canonical stage ran from it, clean and pushed) |
| post-run checker fix | `16cfcb678ba96666aa8cb586f36788b764addaa3` (check 21 frame-tag literal; see "Incidents") |
| report | this commit |

- Run `RUN` = `/home/lvelho/rd/f3d-vision/previews/north-star/ns1b-recentered-controller-handoff/`: 164 MB;
  `manifest.json` `e859fa61…`; `check-summary.json` `146438bd…`.
- Visuals `VIS` = `/home/lvelho/rd/f3d-vision/visuals/north-star/ns1b-recentered-controller-handoff/`.

### What ran (MEASURED, `process-log.jsonl`; each canonical stage once, in contract order, from `40eaf7e`)

| # | command (`tools/north_star/ns1b_run.py`) | result | seconds |
|---|---|---|---|
| 1 | `source` | 42 source pins, 7 NS1a handoff pins, accepted constants | 0.1 |
| 2 | `synthetic` | `NS1B_SYNTHETIC_PASS` 23/23 | 5.7 |
| 3 | `select` | entity 172, rank 6 | 0.03 |
| 4 | `chart` | R_HC, all chart requirements met | 0.03 |
| 5 | `covariance` | `NS1B_COVARIANCE_PASS` 12/12 parts | 63.4 |
| 6 | `context` | one completed own look; 12,072-surfel H0 map | 0.3 |
| 7 | `probe` | Case B: FSG6f (0, −5), gate admissible | 0.7 |
| 8 | `preflight` (Blender, NO render) | identities exact | 0.7 |
| 9 | `acquire` (Blender, the one render) | one pair, 4096 spp | 39.1 |
| 10–15 | `freeze-observation`, `perfect-correspondence`, `freeze-correspondence`, `spherical-geometry`, `freeze-geometry`, `local-oracle-segmentation` | 64,437 correspondences, all triangulated | ≤ 0.7 each |
| 16 | `fuse` | FUSED: matched 9,354, new 9,171 | 1.4 |
| 17 | `post-probe` | ACTIONABLE (not executed) | 0.5 |
| 18 | `visualize` | 3 figures | 0.9 |
| 19 | `check_ns1b.py --corruptions --write-summary` (at `16cfcb6`) | 26/26; null probe clean; corruptions 45/45 | 178 (batch) |

## 2. NS1a acceptance and source pins

- **NS1a handoff (check 03).** The NS1a observation, geometry and seed-set freezes are pinned: `46f0a22e…`,
  `7b0ae64d…`, `4ee36a1a…`. So are `seeds/seed-set.json` `e2ff1ba3…`, `seeds/entity-maps.npz` `621d8902…`,
  `source/nb1c-gaze-list.json` `785d02a7…` and the NS1a catalog seal `a0849b21…`. The seed freeze carries the seed set
  and the maps.
- **Accepted code reused read-only (check 02).** 42 files are pinned at the base (pins digest `8cdf70df…`) and none is
  modified:
  - FSG6f: `fsg6f_frontier`, `fsg6f_public`, the `multiobject2c_policy` target-label adapter;
  - Cyclopean: `classroom_oracle1_epistemic`;
  - the Classroom matcher and public constants;
  - `fov3d.control.{integrated, controller02, frontier, object_policy, frontier_config}`;
  - `fov3d.experiments.classroom_oracle.{controller01, controller02, epistemic, matcher, config}`;
  - the accepted surface map and measurement memory;
  - AB1b oracle and geometry;
  - the NS1a spec, core, render and checker;
  - the AB1a / Classroom render path;
  - Visual Language 1.
- **Accepted policy constants (check 06),** read live and recorded by the probe:
  - FSG6f `SURFACE_FRONTIER`: yaw ±25°, pitch ±20°, 5° step, and the other 13 values;
  - FUSION 12 mm / 12 mm;
  - Cyclopean grid 0.1°, chart 401 × 501;
  - object label 141;
  - the minimum of 100 points.

## 3. Deterministic target selection (contract section 5; check 04 recomputes it with |b × g|)

Inputs: the frozen NS1a seed set and gaze list; b = +X. Selection set: `initialized` and `contributing_patches == 1`.

| id | init rank | init gaze H0 (°) | b·g | L = √(1 − (b·g)²) | final surfels |
|---|---|---|---|---|---|
| **172** | **6** | **(−156.25, +28.75)** | **−0.3531** | **0.935586** | **12,072** |
| 212 | 6 | (−156.25, +28.75) | −0.3531 | 0.935586 | 2,756 |
| 123 | 6 | ″ | −0.3531 | 0.935586 | 1,672 |
| 202 | 6 | ″ | −0.3531 | 0.935586 | 217 |
| 129 | 6 | ″ | −0.3531 | 0.935586 | 174 |
| 12, 204, 231, 230, 9 | 1 | (+76.75, +7.75) | +0.9645 | 0.264126 | 36,126 … 268 |

- **Excluded.** Multi-patch oracle ids 10, 110 and 178. The 9 entities that were never initialized.
- **Decided by** `final_surfels`. The five rank-6 candidates tie exactly in L (they share the initialization gaze), and
  172 has the most surfels.
- **Matches the mandate's expectation** (entity 172, rank 6), compared only after the rule derived it.
- **Fields read.** The rule read only `temporary_entity_id`, `initialized`, `initialized_at_rank`,
  `contributing_patches` and `final_surfels`.
- **Guard.** The selection guard read exactly the seed set, the seed freeze and the gaze list. No name, catalog,
  Controller-01 result or probe was involved.

## 4. Selected target and initialization gaze

- **Entity 172.** Single patch `nb1c_gaze_06`; 12,072 surfels.
- **Initialization gaze.** H0 (−156.25°, +28.75°), the saved NS1a rank-6 look.
- **Frame position.** 100 % of its surfels have z_H0 > 0, i.e. they lie behind the H0 forward hemisphere. In chart C,
  100 % are forward.
- (Its post-NS1a evaluation name, `pipe`, is from the accepted NS1a report. No NS1b stage opened a name.)

## 5. The policy chart R_HC (contract section 6; check 05 recomputes it by the triple product)

    x_C = ( 0.935586,  0.181530,  0.302863)
    y_C = ( 0.000000, -0.857728,  0.514104)
    z_C = ( 0.353099, -0.480989, -0.802478)          (columns of R_HC, in H0)

Chart properties (MEASURED):
- ‖b − (b·g0) g0‖ = 0.935586 (not singular).
- Orthonormality error 2.2e-16; det − 1 = 2.2e-16.
- The seed maps to local (3.2e-15°, 0°).
- Point and direction round trips: 8.9e-16 m / 2.2e-16. Distance change 1.3e-15 m.
- The physical baseline in C is (0.9356, 0, 0.3531): horizontal in C, tilted 20.7° in depth.

The seed looks backward, so chart up points toward world down: y_C · Y = −0.858. The chart is rolled about 180° from
world-up, as is the physical `baseline_projected` camera. The left camera's image +X is 0.81° from x_C, and its image up
coincides with y_C. This follows from the mandated +X construction; consequently local −5° pitch is H0 +4.89° pitch.

The frozen domain (local ±25° / ±20°, 5° step) maps into H0 across the ±180° yaw seam. Its corners are:

| local corner (°) | H0 (°) |
|---|---|
| (−25, −20) | (−119.95, +39.12) |
| (+25, −20) | (+173.56, +50.81) |
| (+25, +20) | (+175.86, +10.86) |
| (−25, +20) | (−137.71, +2.53) |

## 6. Proof that the physical head stayed fixed (checks 07, 10, 17, 23)

- **Every physical calibration is the fixed head.** This covers:
  - the NS1a rank-6 initialization look;
  - the gate's predicted calibration, before and after the action;
  - the planned calibration and the executed calibration.

  Each has eye centres exactly (∓0.0315, 0, 0) m, IPD 0.063 m, the AB1a head pose (|ΔR| = |Δo| = 0) and
  `baseline_projected`.
- **The Blender EYE pose** equals the AB1a head (preflight: 0, 0).
- **No fake local calibration.**
  - No calibration equals `make_calibration` at the local gaze.
  - None has eye centres reset onto C's axes.
  - The gate's P3 calibration is the real sensor at the H0 world gaze, local (0, −5) → H0 (−155.008, +33.636).
- **The adapter substitutes exactly P1–P3** in every loaded module copy (`fsg6f_frontier` and
  `tools.fsg6f_frontier`), and restores them; check 07 verifies this live as well.
- **No head-motion code exists:** check 23's code scan.

## 7. Identity / rotation covariance (contract section 8; `covariance`, re-verified by check 08)

All of these ran before the adapter touched NS1a data.

| known answer | result (MEASURED) |
|---|---|
| K1 FSG6f, 8 accepted self-test fixtures, identity chart | bitwise equal (tolerance 0); every accepted known answer ([5, 5], [−5, −5], eye-swap invariance, the down-right regression, the inset stop, background history) |
| K1 frontier-state unit controls (map / boundary / open, eye swap) | identity and rotations equal |
| K1 Cyclopean bay fixation, and an `add_observation` fixture through P2 | identity equal; rotations: evidence arrays and decisions equal |
| K1 Controller-02 gate, analytic state | identity: no differences; rotated chart with the real sensor: no differences; P3 = real world sensor, never the fake local one |
| K2: object 112 after step 18, revision [1, 26285] | the saved accepted `fsg6f_decision` (continue → [9.0, 10.75]) reproduced bitwise |
| K3: object 112 after step 20, revision [3, 32438] | the saved FSG6f `no_frontier` and the Cyclopean fixation [20.6, 9.7] reproduced bitwise |
| K3q: object 112 after step 21, revision [4, 36183] | the saved QUIET summary reproduced bitwise |
| K4: object 210 terminal state, revision [24, 1774969], 1,938,913 effective points | the accepted Controller-02 verdict reproduced exactly; details below |
| rigid rotation about +X, β = +23°, −47°, +131° | K1 8 fixtures and K2 / K3 / K3q: 0 local differences; world proposal = Q × original (≤ 1e-12, 0.0 for the replay states) |
| projection invariance, canonical chart, the real rank-6 calibration and two predicted looks | max \|uv(C→H0) − uv(H0)\| 2.8e-13 px; negative control (a C point projected as if it were H0) ≥ 712 px |
| chart-only parts under two off-axis rotations | frontier, 12-mm map resolution (frame-invariant) and Cyclopean map support all equal |

**K4 detail.** The accepted verdict was `final_probe_rejected` / `no_novel_serviceable_support`: support 30, in both
cores 0, previously interrogated 30, novel 0. NS1b reproduced it exactly, including every element (52 s).

The replay states were rebuilt from 223 name-free accepted files (digest `5527778a…`): per-object
`trajectory.partial.json`, patches, own-look acquisitions and the Controller-02 `final-residue.json`. The Controller-01
`actions.json`, `result.json` and `manifest.json` carry object names and were never opened.

**Comparison rule (implementation-level, disclosed).** "Exact where discrete" was implemented as follows:
- **Candidate lists.** They must contain the same candidates with equal fields. Their order may differ only where the key
  that decided the accepted sort differs by at most 1e-9 (a floating-point tie-break).
- **The frontier voxel count.** It may differ only when it is the sole difference and map points lie on exact 25-mm
  voxel boundaries.

These rules mattered only for the analytic rotation fixtures:
- **At +23°,** fixture z's frontier voxel count was 256 vs 257: 79 points of the accepted self-test patch lie exactly on
  voxel boundaries (coordinate 0).
- **At −47° and +131°,** two candidates swapped order: their new-box areas are both exactly 120 deg² in exact
  arithmetic, and one becomes 119.99999999999999.

Every selected gaze was equal. The replay states and this NS1b seed had no inversion and no flip; the seed has 0 map
points on voxel boundaries.

## 8. Imported seed context (contract section 9; check 11 recomputes it)

- **NORTH-STAR METRIC MAP.** The frozen NS1a H0 map of 172, bitwise: 12,072 surfels, patch `nb1c_gaze_06`, all ids 172.
  It is given to the policy as p_C = p_H0 @ R_HC.
- **CONTROLLER OBSERVATION STATE.** The saved NS1a rank-6 look, with hashes equal to the NS1a observation freeze; no
  rerender. It went through the accepted Classroom matcher, which returned:
  - 58,672 valid pixels in its planar rectified core;
  - 4,118 target pixels (4,238 target-labelled left-core pixels).

  It is used only for masks, history and continuation / boundary evidence.
- **Context.** Current local gaze (0, 0); visited [(0, 0)]; one completed own look; history = that look with the real
  rank-6 H0 calibration.
- **Cyclopean evidence,** marked through P2: seen_any 11,513 cells, seen_target 1,709, target_depth_valid 852.

Observation for later design: the accepted Controller-01 observation state lives in the planar rectified core. That core
is centred 1.49° from the rank-6 gaze, and its right match must fall inside the right core. So its target support (4,118)
is smaller than the North-Star raw-core spherical measurement of the same look (12,072).

## 9. Pre-action FSG6f / Cyclopean decision (the ONE probe; check 12 recomputes it bitwise)

- **FSG6f: `continue`.**
  - Frontier: raw 359, open 254, map-resolved 2, boundary-resolved 103.
  - 3 candidates; 0 rejected by consensus.
  - The Cyclopean handoff was not reached.

| local candidate | predicted new area (deg²) | frontier score | OPEN support (raw / map / boundary) |
|---|---|---|---|
| **(0, −5)** | **106.83** | 19.86 | 55 (55 / 0 / 0) |
| (5, −5) | 105.03 | 52.55 | 158 (158 / 0 / 0) |
| (5, 0) | 81.60 | 68.20 | 183 (183 / 0 / 0) |

- **Selected.** (0, −5) by the accepted ranking (largest predicted new angular area first). The probe read no Position,
  Object Index or catalog: its guard data reads are the context artifacts, the chart, the selection and the rank-6
  calibration.
- **Invariance (in the probe; check 13 adds β = −23°).** The same context rigidly rotated about +X gives the identical
  local decision, evidence, gate and summary:

  | β | chart vs Q·R_HC | world proposal error | predicted calibration error |
  |---|---|---|---|
  | +37° | 5.6e-17 | 4.5e-17 | 1.1e-16 |
  | −61° | 5.6e-17 | 2.8e-17 | 2.2e-16 |

- **Euclidean invariance.** The 12-mm map resolution of the 359 frontier targets is identical in C and H0 (2 mapped
  either way).
- **No-chart diagnostic.** Refused: `ValueError: too few map points for frontier`, with 0 of 12,072 points forward in H0.

## 10. Adapted Controller-02 gate (check 14)

`final_look_gate_v1`, unchanged, under the adapter: **ADMISSIBLE**, `novel_support_in_predicted_cores`.

| support | in L core | in R core | in both | previously interrogated (in both) | mapped ≤ 12 mm | serviceable | novel |
|---|---|---|---|---|---|---|---|
| 55 | 15 | 24 | 15 | 3 (3) | 0 | 15 | **12** |

The predicted calibration is the real fixed-head North-Star sensor (`baseline_projected`, AB1a head, IPD 0.063 m) at the
H0 world gaze. It equals the planned calibration.

## 11. Local proposed gaze

**Local (0.0°, −5.0°)** in chart C. Source: `fsg6f`. The proposal sits inside the frozen ±25° / ±20° domain on the 5°
lattice.

## 12. Mapped H0 physical gaze (check 15 recomputes it in column form)

- d_C = `gaze_direction(0, −5)`; d_H0 = d_C @ R_HC.T = (−0.351755, 0.553914, 0.754617).
- **H0 world gaze (−155.008024°, +33.635971°).**
- The H0 → C round trip reproduces the local gaze to 6.4e-15°.
- 5.00° from the seed gaze. Physical stereo leverage 0.9361.
- The decision, the planned calibration, the preflight and the executed calibration all carry this gaze.

## 13. Whether an action executed

**Yes — exactly one** (Case B; `probe/decision.json`, one action, patch id `ns1b_action_01`). No second gaze, no target
switch and no scheduler (checks 16, 22, 23).

## 14. The executed action

**Render (MEASURED).**
- `classroom_eye.blend`; Blender 5.2.1 LTS, CYCLES OPTIX.
- Full profile: 640 × 640 raw, 256 × 256 core, 12° core.
- IPD 0.063 m, vergence 2.10 m, `baseline_projected`.
- 4096 spp in the record, the readback and both EXR headers (`cycles.interior.samples`).
- Seeds L 2111 / R 2112; denoising OFF; adaptive OFF; BOX 1.0.
- The settings equal the accepted AB1d2 4096-spp readback.
- Render times: L 19.10 s, R 18.52 s (38.4 s wall).
- The calibration is byte-identical to the planned one.
- The sealed catalog seal is `a0849b21…`, equal to NS1a's. The Object Index assignment is therefore the same, and no
  host stage opened the catalog.

**PERFECT correspondence** (accepted AB1b `compute_oracle`; check 18 reproduces it with an own oracle, Δ uv_R ≤ 1e-9 px).
- The 65,536 core pixels all have:
  - a finite hit;
  - a positive id;
  - a right projection inside the padded raster.
- 1,099 pixels see a different right instance and are excluded.
- **64,437 correspondences.** The product is truth-stripped (`left_core_row`, `left_core_col`, `uv_L`, `uv_R`), with
  continuous `uv_R`. Instance 0: 0.

**Spherical geometry** (accepted AB1b; truth-free guard: calibration + frozen product only; check 19 reproduces P_epi
with its own law-of-sines triangulation, ≤ 1e-9 m).
- All 64,437 triangulated.
- δθ > 0 everywhere; |φ_R − φ_L| ≤ 6.5e-7 rad; |P_epi − P_ray| ≤ 3.8e-9 m.
- κ median 51.2 (37.8–67.3).
- Left range median 3.02 m (2.30–3.79); range per pixel median 0.128 m.

**Local oracle segmentation aid.** Attached after the geometry freeze; only `instance_L` was read. Positive ids in view:
110 (45,090), **172 (18,525)**, 126 (822). Only 172 is fused (target only).

**H0 fusion** (accepted `surface_map.fuse`, 0.012 m / 0.012 m, canonical H0; check 21 reproduces it bitwise and with its
own brute-force association):

| map before | target points | matched | affected surfels | new | map after | matched distance median / p95 / max |
|---|---|---|---|---|---|---|
| 12,072 | 18,525 | **9,354** | 8,601 | **9,171** | **21,243** | 1.50 / 3.70 / 11.98 mm |

- The replay of the same patch is a duplicate, and the map is unchanged: exact equality and the 1e-10 test.
- The patch is exactly the frozen H0 P_epi of the target points.
- The new look overlaps the seed's core: about half of the target points re-measure surfels that NS1a measured from the
  seed gaze, and they agree within 1.50 mm (median). The other half extend the map along the target, into a bend that
  the seed look did not see (`first-controller-action-3d.png`).

## 15. Post-action read-only probe (exactly once; not executed; check 22 recomputes it)

**Context update** (Controller-01 `observe` order):
- the accepted matcher state of the new look (15,175 target pixels);
- evidence through P2, giving seen_any 16,796 cells;
- history: 2 own looks;
- visited [(0, 0), (0, −5)];
- geometry: the fused 21,243-surfel H0 map, in C.

**State ACTIONABLE.**
- FSG6f `continue`. Frontier: raw 417, open 280, map-resolved 4, boundary-resolved 133.
- 5 candidates; 1 rejected by consensus: (−5, −5), 63 OPEN of 160 raw.
- **Proposal local (−5°, −10°)** → H0 (−147.585°, +37.246°). It is 11.17° from the seed; leverage 0.9044.
- Gate ADMISSIBLE: support 71, in both cores 29, previously interrogated 43 (7 in both), novel 22.

**This proposal was NOT executed.** NS1b ends here.

## 16. Outcome reading (contract section 17)

**My reading: Outcome 1 — handoff + action succeeds.**
- The recentered policy chart produced an admissible controller action.
- C → H0 was coherent (round trips ≤ 6.4e-15°; baseline-rotation invariance exact).
- One real fixed-head observation executed.
- PERFECT spherical geometry was fused into the canonical map, with genuine 12-mm overlap.
- The controller context remains valid after the action: the post-action probe is ACTIONABLE with a new admissible FSG6f
  proposal.

It is not Outcome 2 (the seed was not QUIET), not Outcome 3 (the gate admitted the proposal) and not Outcome 4: every
covariance, projection, round-trip and invariance test passed.

Luiz and Chat decide.

## 17. Checks (MEASURED)

**`check_ns1b.py`: 26/26** (`NORTH_STAR1B_CHECKS_PASS`; `check-summary.json` `146438bd…`, written at `16cfcb6`). The
checker keeps its own literal pins and recomputes independently wherever an independent formula exists:
- **Selection:** own |b × g| leverage.
- **Chart:** own triple-product construction.
- **World gaze:** own column-form rotation.
- **Fixed-head calibrations:** own construction.
- **Oracle and triangulation:** the accepted NS1a checker's own implementations.
- **12-mm association:** own brute-force nearest surfel.

The accepted policy itself has no independent implementation. Its reproduction is established by the covariance known
answers (check 08 re-runs K1–K3 and K4).

The 26 checks cover:
- provenance (01), source pins (02), the NS1a handoff (03);
- selection (04), chart (05), policy constants (06), frame adapter (07), covariance (08), synthetic order (09);
- fixed head (10), context (11), probe (12), invariance (13), gate (14), world gaze (15), case and process (16);
- observation (17), oracle (18), geometry (19), identity (20), fusion (21), post-probe (22);
- process scan (23), truth boundary (24), figures (25), manifest and declared changes (26).

**Synthetic / known answers: 23/23** (`NS1B_SYNTHETIC_PASS`; analytic, before NS1a data). These are the 20 contract
cases plus:
- the adapter mechanics: substitution, restore, nesting refusal and every module copy;
- the chart-singularity STOP;
- the Euclidean frame invariance.

**Covariance: 12/12 parts** (`NS1B_COVARIANCE_PASS`).

**Repository gates on the report tree (MEASURED):** layout 611/611, `scripts/verify_baseline.sh` 9/9,
`git diff --check` clean, and `check_ns1b.py` (read-only) 26/26.

## 18. Corruption suite (MEASURED): 45/45 caught

`NORTH_STAR1B_MUTATIONS_CAUGHT`:
- It started from a passing baseline, after an unmodified-mirror null probe that passed all 26 checks.
- No corruption was NOT APPLICABLE: this is Case B.
- Each corruption mutated a temporary mirror; the mirror's manifest was then regenerated, so the manifest check is not
  what catches it.
- RUN and VIS were hashed before and after the suite and are unchanged.

| family | corruptions (catching checks) |
|---|---|
| TARGET | multi-patch entity included (04, 05); leverage altered (04); tie rule changed (04, 05); a name / catalog read in the selection (04, 24); another id selected (04, 05) |
| CHART | one basis axis flipped (05); map centroid instead of the initialization gaze (05); wrong cross-product order (05); non-orthogonal basis (05); H0 / C transpose error (05) |
| PHYSICAL SENSOR | head rotated (10); local eye centres reset to ±X of the chart (10); IPD changed (10); head pose changed (10); local fake calibration used for observability (07, 10, 14) |
| POLICY | ±25 / ±20 changed (06); 5° step changed in-process (06, 12); frontier threshold changed (06); consensus changed (12); 12-mm resolution changed (06, 12); Cyclopean grid changed (06) |
| PROJECTION | C points projected directly with the H0 calibration, in-process (08); wrong C → H0 transform, in-process (08); wrong world-gaze mapping (15) |
| SOURCE | initial seed re-rendered (03); seed map altered (11); catalog opened by the probe (12, 24) |
| ACTION | controller-selected gaze changed (15); a second gaze executed (22, 23); target switched (21) |
| MEASUREMENT | SGBM-like correspondence (18); other metric geometry (19); perfect uv_R rounded (18); Position exposed to the spherical geometry (19, 24) |
| FUSION | fused in C coordinates (21); radius changed, regenerated (21); hash cell changed (21); idempotence disabled (21); fusion record claims the chart frame (21) |
| COVARIANCE / DECISION | K4 verdict altered (08); gate verdict flipped in the decision (14) |
| VISUAL | local / H0 frame label omitted (25); head motion implied (25); oracle badge removed (25); a canonical pixel altered (25) |

## 19. Visuals (Visual Language 1) and hashes

`VIS` (`visuals-manifest.json` `a10e5fcf0aa249d0ce4bb72dce9ff012c056eb909cc6517ebc975af737fbeb77`):

| figure | truth badges | sha256 |
|---|---|---|
| `overview.png` | ORACLE INPUT, DERIVED | `5dedb921a1428212daf6d230b5df22e15a23266412389aa2d90f6772de294463` |
| `chart-covariance.png` | ORACLE INPUT, DERIVED | `4419516363733473ac32d68b05c2350976cabadbda94a58a3a3739f4514b6428` |
| `first-controller-action-3d.png` | ORACLE INPUT, DERIVED | `0b299f936f0680b6568ebee633dc85d708681f9ab1e1f34b0363fb95b32c6d5b` |

**`overview.png`** has four panels:
- **A:** the NS1a seed set in H0 yaw / pitch, with target 172 ringed. Beside it the selection table (L, surfels,
  decided by), tagged NS1a FROZEN INPUT · no object name used for selection.
- **B:** canonical H0 around the seed beside chart C. It shows:
  - seed → local (0, 0);
  - the frozen ±25° / ±20° domain, also mapped into H0;
  - the FSG6f candidates;
  - the selected (0, −5) in both frames;
  - the physical baseline in C;
  - R_HC, tagged PHYSICAL HEAD FIXED · POLICY CHART ONLY.
- **C:** the seed look beside the one new look. Also the probe and gate numbers, and the target vs other-id
  correspondence map (no hit stippled, not visible hatched).
- **D:** the H0 map before / after, viewed along the seed gaze. Seed-unmatched surfels are grey squares; matched surfels
  green crosses; new surfels blue squares. Beside it the fusion and post-probe numbers.

**`chart-covariance.png`:** the identity known answers (K1–K4), the baseline-rotation results with the original and
rotated decisions, and projection invariance.

**`first-controller-action-3d.png`:** top / front / side views in H0, with the fixed head at the origin and the baseline
on +X. Also the seed and action gaze lines, and a zoom along the seed gaze with seed / matched / new surfels.

Regenerate:

    .venv/bin/python tools/north_star/ns1b_run.py visualize --run RUN --visuals VIS

## 20. Incidents

1. **Before the contract** (calibration-only; contract section 3): the chart at rank 6; the planar rectified core 1.49°
   off the gaze (14.26° at rank 1); the chart's roll relative to the camera; the local ↔ H0 round trips.
2. **Between the contract and the canonical run** (scratch run only):
   - **What was rehearsed.** `select` … `post-probe` on entity 110, a NON-candidate (three patches, rank-2 chart). The
     rehearsal included a no-render Classroom preflight and a 16-spp factory-startup render; there was never a
     Classroom render. The selected target was never probed.
   - **Defects found and fixed inside the implementation commit:**
     - the comparison rule for float-tie candidate inversions and exact-voxel-boundary flips (section 7);
     - a name-key screen that matched the descriptive key "… (unassigned / non-catalog)" in the NS1a seed set (now
       exact name / catalog key forms);
     - a directory listing inside a guard (fixture files are now listed before the guard);
     - output directories created before their guards;
     - checker defects found on the rehearsal run: a byte comparison of two float paths, a proposal comparison missing
       two appended keys, and the observation freeze's hash read not allowed by the truth-boundary check.
3. **Canonical run:** no incident.
   - Every canonical stage ran once, in order, from `40eaf7e`, clean and pushed.
   - The one render took 38.4 s.
   - No re-render, second probe or second action.
4. **After the canonical run** (contract section 22(c), checker only, `16cfcb6`):
   - **The defect.** The first canonical checker run failed check 21 alone. The fusion record carries frame `"H0"`:
     the stage merges the H0-only `fuse_h0` result after its display label, and `fuse_h0` writes its machine tag `"H0"`.
     The check expected the label `"CANONICAL H0"`.
   - **The data were correct.** Every substantive condition held: patch = frozen H0 P_epi; accepted fuse reproduced
     bitwise; own association 9,354 / 9,171 / 8,601; exact replay; 12 mm / 12 mm.
   - **Why it was missed earlier.** The rehearsal's fusion was RETAINED_NOT_FUSED, so it never wrote the tag.
   - **The fix.** The check now requires the exact tag of each path. Probes that set `"C"`, or the label on a FUSED
     record, fail it. One corruption was added ("fusion record claims the chart frame").
   - **Consequence.** No stage, artifact or figure changed. The suite then caught 45/45.
5. **Cosmetic.** The accepted NS1a `Budget` helper prints its own `[ns1a-render]` prefix in the NS1b Blender log.
6. **Nothing in the contract was left unrun.**

## 21. What is established

- **The handoff works.** A persistent seed from the global 360° RGB bootstrap (NS1a entity 172) is handed to the
  accepted local FSG6f → Cyclopean / Controller-02 semantics, unchanged, through a temporary recentered POLICY
  COORDINATE CHART and a thin frame adapter. Every physical quantity stays in the fixed-head H0 frame.
- **The chart is necessary for this seed.** Without it, the accepted FSG6f refuses the seed: no surfel lies in the H0
  forward hemisphere.
- **Covariance is established on accepted known answers:**
  - identity reproduction on accepted FSG6f / Cyclopean fixtures, on accepted Controller-01 replay states (bitwise), and
    on the accepted Controller-02 verdict;
  - exact covariance under rigid rotations about the physical baseline;
  - projection invariance.
- **The action executes.** The controller proposed an admissible fixation, local (0, −5) → H0 (−155.008°, +33.636°).
  One PERFECT fixed-head 4096-spp measurement there gave 18,525 target points.
- **The first genuine 12-mm North-Star fusion occurred.** 9,354 points matched existing surfels (matched-distance median
  1.50 mm), 9,171 were new, and the H0 map grew from 12,072 to 21,243 surfels.
- **The controller context remains valid after the action.** The read-only post-action probe is ACTIONABLE, with a new
  admissible FSG6f proposal.

## 22. What is NOT established

- That the other 12 seeds are serviceable through the same handoff. Four of them (212, 123, 202, 129) share this
  rank-6 chart, and the multi-part oracle ids (10, 110, 178) were deliberately excluded.
- Anything about scene-level scheduling, target switching, closure, the 24-look budget or global quiescence. None was
  run.
- Natural correspondence or natural identity: both are oracle aids here.
- That the chart construction is optimal. Rotations off the baseline axis have no exact physical known answer and were
  tested only for the chart-only parts.
- Head motion, real cameras or other scenes.
- **One design observation, for later.** The accepted controller observation state (planar rectified core, right match
  inside the right core) supports less of the target than the North-Star raw-core spherical measurement of the same look
  (4,118 vs 12,072 at rank 6).

## 23. Unresolved decision for Luiz / Chat

~~READY TO ENABLE THE MULTI-ENTITY NORTH-STAR CONTROLLER LOOP?~~

**Decided:** NS1b is accepted (Outcome 1), and the bootstrap-to-controller bridge is established. The next step is
North Star-1c, coherent multi-entity control with a first scene switch, continuing from the accepted NS1b state (see
"Acceptance record").

The measured inputs:
- Outcome 1 on one deterministic seed (172).
- Covariance: identity and rotation known answers all pass, including the accepted Controller-02 verdict.
- One executed action with genuine 12-mm overlap (9,354 matched; median 1.50 mm).
- An ACTIONABLE post-action state.
- The chart is necessary for at least this seed.
- The 5 rank-6 seeds share one chart. Three multi-part seeds await the oracle-identity question.

This report makes no scheduler design.

~~NS1b REVIEW PENDING · DECISION PENDING: READY TO ENABLE MULTI-ENTITY NORTH-STAR CONTROL?~~

NS1b ACCEPTED · BOOTSTRAP-TO-CONTROLLER BRIDGE ESTABLISHED · NS1c NEXT

## Acceptance record

Luiz and Chat completed the scientific review, an independent GitHub implementation review, the checker / corruption
review and a qualitative visual inspection of the three figures, and **accept NS1b** as committed at `8155c2d`:

    NORTH_STAR1B_RECENTERED_CONTROLLER_HANDOFF_ACCEPTED

- **Machine result accepted:**
  - `NORTH_STAR1B_RECENTERED_CONTROLLER_HANDOFF_COMPLETE`;
  - `NORTH_STAR1B_CHECKS_PASS` 26/26;
  - `NORTH_STAR1B_MUTATIONS_CAUGHT` 45/45 from a passing baseline, with a clean unmodified-mirror null probe;
  - `NS1B_SYNTHETIC_PASS` 23/23;
  - `NS1B_COVARIANCE_PASS` 12/12 parts.
- **Outcome 1 accepted** (contract section 17).
- **Accepted scientific conclusion** (stated without strengthening):

      A persistent entity seed produced by the global RGB bootstrap can be handed to the unchanged accepted FSG6f ->
      Cyclopean / Controller-02 semantics through a temporary local POLICY COORDINATE CHART while all physical sensing
      and persistent geometry remain in canonical H0.

- **Accepted measured result** (MEASURED, the one canonical run; sections 3–15). For deterministic target 172:

  | quantity | value |
  |---|---|
  | initialization H0 gaze | (−156.25°, +28.75°) |
  | local selected action | (0°, −5°) |
  | mapped H0 action | (−155.008°, +33.636°) |
  | Controller-02 gate | admissible |
  | novel serviceable support | 12 |
  | fixed-head 4096-spp observation | executed exactly once |
  | PERFECT correspondences | 64,437 |
  | target metric points | 18,525 |
  | map before | 12,072 surfels |
  | matched target points | 9,354 |
  | affected existing surfels | 8,601 |
  | median matched distance | 1.50 mm |
  | new surfels | 9,171 |
  | map after | 21,243 surfels |

  The experiment establishes the first genuine North-Star 12-mm overlap and active persistent-map extension.

  Post-action: the controller remained ACTIONABLE; the next local proposal, (−5°, −10°), was **NOT executed**.
- **Accepted coordinate conclusion.**

      POLICY CHART C IS NOT PHYSICAL HEAD MOTION.

  The physical head remained fixed. Persistent geometry remained in canonical H0. The chart only transformed policy
  geometry. The accepted covariance evidence includes:
  - identity FSG6f reproduction;
  - rotated FSG6f covariance;
  - identity / rotated Cyclopean covariance;
  - physical projection invariance;
  - Controller-02 real-sensor gate reproduction.

  The chart is therefore accepted as the North-Star bridge between global 360° persistent scene geometry and the frozen
  local ±25° / ±20° controller.
- **Retained limitations** (part of the acceptance):
  1. PERFECT correspondence remains an oracle aid.
  2. Object identity remains an ORACLE SEGMENTATION AID.
  3. Only one entity was actively serviced in NS1b.
  4. The known NS1a multi-part oracle identities remain unresolved: 10, 110, 178.
  5. The controller observation state still has narrower support than the North-Star spherical measurement. At the NS1b
     initialization look: North-Star target map 12,072 points; accepted Controller-01 planar controller-state target
     support 4,118 points. This representation is NOT redesigned in NS1c; the discrepancy is measured where useful.
- **Visuals accepted.** Luiz and Chat inspected the three figures:
  - `visuals/north-star/ns1b-recentered-controller-handoff/overview.png`
    (`5dedb921a1428212daf6d230b5df22e15a23266412389aa2d90f6772de294463`);
  - `visuals/north-star/ns1b-recentered-controller-handoff/chart-covariance.png`
    (`4419516363733473ac32d68b05c2350976cabadbda94a58a3a3739f4514b6428`);
  - `visuals/north-star/ns1b-recentered-controller-handoff/first-controller-action-3d.png`
    (`0b299f936f0680b6568ebee633dc85d708681f9ab1e1f34b0363fb95b32c6d5b`).

  Accepted visual reading: deterministic target selection; fixed physical head; policy-only recentering; covariance;
  controller-selected action; genuine overlap; persistent H0 map growth.
- **Accepted NS1b post-action state** (the NS1c starting point): current target 172; H0 map 21,243 surfels; 2 own looks;
  visited local gazes (0, 0), (0, −5); next accepted post-action proposal local (−5, −10), not executed.
- **This acceptance step** made no new observation and did no scientific computation. It changed only this status
  record, and (in the next commit) `CLAUDE.md`, the Chat Handoff and the layout checker's handoff assertion. The NS1b
  code, canonical run, controller action, maps, figures and contract are unchanged.
