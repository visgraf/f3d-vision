# North Star-1c — Coherent Multi-Entity Control — First Scene Switch — report

**Marker.**

    NORTH_STAR1C_COHERENT_FIRST_SCENE_SWITCH_COMPLETE

**Status: REVIEW PENDING.** Luiz and Chat decide whether to release the full coherent multi-entity North-Star loop. No
ACCEPTED marker is written, and the branch is not merged.

> **Question.** Starting from the accepted NS1b state, can the accepted deterministic scene scheduler and per-entity
> recentered local controllers continue servicing the current entity and then AUTONOMOUSLY SWITCH to another coherent
> RGB-bootstrap seed and execute one valid controller-selected observation there?

**Answer (MEASURED, one canonical run): yes. My reading is Outcome 1, a natural scene switch.**
- **172 was serviced first.** The unchanged `integrated.schedule` retained entity 172 for four controller-selected
  fixed-head 4096-spp actions. Its H0 map grew from 21,243 to 45,267 surfels.
- **172 then became QUIET** after the 4th action, through the accepted probe and gate:
  - FSG6f found no frontier;
  - the Cyclopean handoff proposed a fixation;
  - the accepted Controller-02 v1 gate rejected it as `untraceable_final_support`.

  The watchdog was not involved: 172 had 6 own looks, and the limit is 24.
- **The scheduler switched by its accepted rule** (global step 4, 172 → 123). No coherent id above 172 was serviceable,
  so the rule wrapped to the lowest serviceable id: **entity 123**, the only other ACTIONABLE coherent seed.
- **One action executed on 123:**
  - controller-selected local (−5°, +5°) → H0 (−152.090°, +22.757°);
  - 6,291 PERFECT spherical target points;
  - its H0 map grew from 1,672 to 6,194 surfels (1,769 matched, median 1.77 mm; 4,522 new).
- **NS1c stopped there.** The one read-only post-action probe of 123 is QUIET; its proposal was NOT executed.

The physical head never moved. Every chart is a POLICY COORDINATE CHART only. Every eye centre, calibration, projection,
observability test, acquisition and fusion stayed in canonical H0. Truth labels:
- CORRESPONDENCE: PERFECT / ORACLE.
- IDENTITY: ORACLE SEGMENTATION AID.
- GEOMETRY: DERIVED spherical geometry.
- CONTROLLER OBSERVATION STATE: the accepted Classroom matcher (the Controller-01 controller-time oracle).

## 1. Provenance

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (verified by `source` and check 01) |
| NS1b acceptance | `255355108863022f931574dae4b2df8cdd2a772e` (`NORTH_STAR1B_RECENTERED_CONTROLLER_HANDOFF_ACCEPTED`) |
| base (post-NS1b roadmap, `main`) | `2815bf166689d68cec421fb119635cafaa718d9a` |
| branch | `north-star/ns1c-coherent-first-scene-switch`, from the base, isolated worktree |
| contract | `cb2217db82980c3efd0dfd51cf0f944a5d4f7aa2` (before any implementation, probe or render; unchanged since, check 01) |
| implementation | `f339598384b73c01bafc23e40013a6ee987142db` (every canonical stage ran from it, clean and pushed) |
| post-run figure fix | `416a29c9f20e7f99646fb728fb1fd889d65d3433` (overview panel D, presentation only; see "Incidents") |
| report | this commit |

- Run `RUN` = `/home/lvelho/rd/f3d-vision/previews/north-star/ns1c-coherent-first-scene-switch/`: 817 MB, 255 files;
  `manifest.json` `90e2dd4b…`; `check-summary.json` `85cb931f…`.
- Visuals `VIS` = `/home/lvelho/rd/f3d-vision/visuals/north-star/ns1c-coherent-first-scene-switch/`.

### What ran (MEASURED, `process-log.jsonl`; 64 entries, all `ok`, each canonical stage once, from `f339598`)

| # | command (`tools/north_star/ns1c_run.py`) | result | seconds |
|---|---|---|---|
| 1 | `source` | 46 source pins, 7 NS1a and 17 NS1b handoff pins; watchdog 24 (live) | 0.1 |
| 2 | `synthetic` | `NS1C_SYNTHETIC_PASS` 20/20 | 0.3 |
| 3 | `eligibility` | derived {9, 12, 123, 129, 172, 202, 204, 212, 230, 231}; deferred {10, 110, 178} | 0.03 |
| 4 | `charts` | 10 charts, all non-singular; C_172 = NS1b chart | 0.04 |
| 5 | `contexts` | 10 contexts; 172 imported exactly | 1.0 |
| 6 | `initial-probe` | 10 probes + 20 rotated probes; 172 reproduces NS1b | 9.0 |
| 7 | `loop` | 5 global steps × 11 stages (the switch at step 4; canonical stop) | 224.3 |
| 8 | `visualize` | 4 figures (`f339598`, then `416a29c` after the figure fix) | 1.7 |
| 9 | `check_ns1c.py --corruptions --write-summary` (at `416a29c`) | 27/27; null probe clean; corruptions 45/45 | 192 (batch) |

Per step (`schedule`, `preflight`, `acquire`, `freeze-observation`, `perfect-correspondence`, `freeze-correspondence`,
`spherical-geometry`, `freeze-geometry`, `local-oracle-segmentation`, `fuse`, `update`):
- 41.0–46.2 s of stage time per step (42.1–47.3 s wall), of which `acquire` took 38.6–39.3 s;
- the budget projection never exceeded about 1,100 s (limit 1,800 s).

## 2. NS1b acceptance and source pins (check 02)

- **Accepted code reused read-only.** 46 files, pins digest `cebea7d4…`, none modified:
  - FSG6f, the target-label adapter, Cyclopean, the Classroom matcher and public constants;
  - `fov3d.control.{integrated, controller02, frontier, object_policy, frontier_config}`;
  - `fov3d.experiments.classroom_oracle.{controller01, controller02, epistemic, matcher, config}`;
  - the surface map, AB1b oracle and geometry, the AB1a / NS1a render path, the NS1a checker, Visual Language 1;
  - the accepted NS1b modules `ns1b_spec`, `ns1b_chart` (the frame adapter, unchanged), `ns1b_core` and
    `ns1b_visuals`.
- **NS1a handoff.** The freezes, seed set, maps, gaze list and catalog seal, exactly as pinned by NS1b.
- **NS1b handoff.** 17 files of the accepted run, including:
  - `manifest.json` `e859fa61…` and `check-summary.json` `146438bd…` (`NORTH_STAR1B_CHECKS_PASS`);
  - the post-action map `bf831ad5…`, evidence `a9679163…`, controller states `ceebc725…` / `337c0705…` and probe
    `2918e146…`;
  - the action calibration `a4b2ae67…`.
- **Accepted constants, live and recorded.** FSG6f `SURFACE_FRONTIER` (±25° / ±20°, 5° step and the rest), fusion 12 mm
  / 12 mm, the Cyclopean grid 0.1° (401 × 501), the minimum of 100 points, and `controller01.WATCHDOG` = 24.

## 3. COHERENT_SEED_SET derivation (contract section 5; check 03 recomputes it)

Rule: `initialized == true AND contributing_patches == 1`. Fields read: `temporary_entity_id`, `initialized`,
`contributing_patches`, plus `initialized_at_rank` and `final_surfels` for the charts and map checks. No name or catalog
was read: the guard read exactly the seed set, the seed freeze and the gaze list.

| set | ids |
|---|---|
| derived COHERENT_SEED_SET | 9, 12, 123, 129, 172, 202, 204, 212, 230, 231 |
| expected (mandate), compared after derivation | identical |
| deferred (initialized, > 1 patch) | 10 (2 patches), 110 (3), 178 (2) |
| outside (never initialized in NS1a) | 47, 48, 49, 53, 54, 55, 56, 57, 58 |

"Coherent" means only single-patch under the NS1a oracle aid. It claims no natural semantic coherence.

## 4. Deferred multi-part identities (check 04)

10, 110 and 178 are recorded `DEFERRED_AMBIGUOUS_ORACLE_IDENTITY` (`in_scheduler: false`). They are never in a service
summary, a scheduler input, a target or an action, and never labelled QUIET / UNLOCATED / BLOCKED. Entity 110 is
nevertheless visible in every 172 observation (41,558–46,220 points) and in the 123 observation (20,733 points). Those
points were measured and never fused.

## 5. Per-entity policy charts (contract section 7; check 05 recomputes them by the triple product)

The 10 charts take two numeric values, because entities that share an NS1a initialization gaze share the chart. Each
entity keeps its own chart id `C_i` and hash; no chart changed in any scene state, and every probe ran under its
entity's own chart.

| chart | entities | seed gaze H0 | ‖b⊥‖ | b·g0 | y_C·Y | R_HC sha |
|---|---|---|---|---|---|---|
| rank 1 | 9, 12, 204, 230, 231 | (+76.75°, +7.75°) | 0.264126 | +0.964488 | +0.860 | `810d3935…` |
| rank 6 | 123, 129, 172, 202, 212 | (−156.25°, +28.75°) | 0.935586 | −0.353099 | −0.858 | `6a647db1…` |

- Rank 6 is bitwise the accepted NS1b chart.
- Both charts: orthonormality error 2.2e-16, |det − 1| ≤ 2.2e-16, seed → local within 4.8e-15°, round trips at the
  1e-12 tolerance.
- The rank-1 chart's local domain maps to H0 corners (+45.8, +0.9), (+87.6, −22.0), (+108.5, +12.3), (+64.1, +37.2).

## 6. Imported initial contexts (contract section 9; check 08 recomputes them)

| entity | source | own looks | visited | map (surfels) | controller-state target support at the init look |
|---|---|---|---|---|---|
| 172 | NS1b post-action context, imported | 2 | (0, 0), (0, −5) | 21,243 (NS1b fused map) | 4,118 (rank 6); NS1b look 15,175 |
| 123, 129, 202, 212 | NS1a rank-6 look + map | 1 | (0, 0) | 1,672 / 174 / 217 / 2,756 | 2,668 / 0 / 270 / 954 |
| 9, 12, 204, 230, 231 | NS1a rank-1 look + map | 1 | (0, 0) | 268 / 36,126 / 3,493 / 1,671 / 2,960 | 0 (all) |

**The 172 import is exact.**
- Its look states equal NS1b's `context/controller-state.npz` and `post/controller-state.npz` bitwise.
- NS1c's own rank-6 matcher state equals NS1b's (one look, one state).
- Its evidence equals NS1b's `post/evidence.npz`. It is also recomputed from the two looks under C_172.
- Its map equals the NS1b fused map.

**The other nine entities reuse the NS1a looks without rerender.** Their look files equal the NS1a observation freeze,
and their maps equal the frozen NS1a maps. Every map is 100 % forward in its chart.

At the rank-1 look the accepted Classroom matcher has 0 valid points in its planar rectified core. This is the known
near-baseline representation pathology (AB1a; NS1b contract section 3). It is recorded, not acted on.

## 7. Exact reproduction of the NS1b post-action probe for 172 (checks 09, 10)

The initial NS1c probe of 172 equals the accepted NS1b post-action probe with **0 differences** at tolerance 0: the
decisions, summary, gate verdict and detail, state, proposal and predicted calibration. In accepted terms:
- ACTIONABLE, source `fsg6f`;
- local (−5°, −10°) → H0 (−147.585°, +37.246°);
- gate admissible, novel serviceable support 22.

## 8. Initial service table (contract section 11; one probe per entity, before any render)

| id | rank | surfels | own looks | local gaze | FSG6f | proposal source → local | proposed H0 | gate | novel | state |
|---|---|---|---|---|---|---|---|---|---|---|
| 9 | 1 | 268 | 1 | (0, 0) | no_frontier | Cyclopean (−6.0, −2.1) | (+70.42, +8.86) | untraceable_final_support | – | QUIET |
| 12 | 1 | 36,126 | 1 | (0, 0) | no_frontier | Cyclopean (−5.6, −0.6) | (+71.51, +9.98) | untraceable_final_support | – | QUIET |
| **123** | 6 | 1,672 | 1 | (0, 0) | **continue** | **FSG6f (−5, +5)** | (−152.09, +22.76) | **admissible** | **37** | **ACTIONABLE** |
| 129 | 6 | 174 | 1 | (0, 0) | no_frontier | Cyclopean (+5.1, +4.5) | (−162.78, +25.24) | untraceable_final_support | – | QUIET |
| **172** | 6 | 21,243 | 2 | (0, −5) | **continue** | **FSG6f (−5, −10)** | (−147.59, +37.25) | **admissible** | **22** | **ACTIONABLE** |
| 202 | 6 | 217 | 1 | (0, 0) | no_frontier | Cyclopean (−5.9, +5.5) | (−151.28, +22.05) | untraceable_final_support | – | QUIET |
| 204 | 1 | 3,493 | 1 | (0, 0) | no_frontier | Cyclopean (+5.9, +0.8) | (+82.29, +5.48) | untraceable_final_support | – | QUIET |
| 212 | 6 | 2,756 | 1 | (0, 0) | no_frontier | Cyclopean (+3.9, +5.2) | (−161.61, +24.36) | untraceable_final_support | – | QUIET |
| 230 | 1 | 1,671 | 1 | (0, 0) | no_frontier | Cyclopean (−5.5, −0.4) | (+71.70, +10.10) | untraceable_final_support | – | QUIET |
| 231 | 1 | 2,960 | 1 | (0, 0) | no_frontier | Cyclopean (+0.6, +0.3) | (+77.43, +7.71) | untraceable_final_support | – | QUIET |

- **Baseline-rotation invariance.** Every entity's probe is identical under β = +37° and −61°, and under the checker's
  own β = −23° (check 09).
- **123's proposal.** It lies 7.07° from its seed, with leverage 0.902. Its gate support is 37, all in both predicted
  cores, and none was previously interrogated.
- **The QUIET entities.** All eight hold a Cyclopean proposal that the v1 gate rejects. They are QUIET under the
  mandated conversion (contract section 12), not because they have nothing to propose (see section 20).

## 9–11. Scheduler action trace, every retain / switch reason, every local and H0 gaze

| step | scheduler (accepted `integrated.schedule`) | target | bout | local gaze (C_i) | H0 gaze | why |
|---|---|---|---|---|---|---|
| 0 | retain | 172 | 1 | (−5, −10) | (−147.585, +37.246) | current 172 ACTIONABLE (its imported NS1b proposal) |
| 1 | retain | 172 | 1 | (−5, −15) | (−145.704, +42.032) | current 172 ACTIONABLE after step 0 (gate novel 15) |
| 2 | retain | 172 | 1 | (−5, −20) | (−143.516, +46.782) | current 172 ACTIONABLE after step 1 (gate novel 22) |
| 3 | retain | 172 | 1 | (0, −20) | (−150.152, +48.188) | current 172 ACTIONABLE after step 2 (gate novel 75) |
| **4** | **switch** | **123** | **2** | **(−5, +5)** | **(−152.090, +22.757)** | 172 QUIET; serviceable = {123}; no id above 172 serviceable → wrap to the lowest, 123 |

- **Recorded summaries.** At steps 0–3 the scheduler saw {123: ACTIONABLE, 172: ACTIONABLE, the rest QUIET}. At step 4
  it saw {123: ACTIONABLE, the rest QUIET, including 172}.
- **Check 12** recomputed every decision with the accepted scheduler on its own summaries: equal.
- **Gaze mapping.** Every local → H0 mapping was recomputed in column form; round trips ≤ 1e-9° (check 13).

## 12. Every physical acquisition (check 15)

Five binocular pairs, one per step:
- Classroom `classroom_eye.blend`, fixed AB1a head, OPTIX, 4096 spp (record, readback and both EXR headers);
- seeds L 2111 / R 2112, denoising OFF, adaptive OFF, BOX 1.0, `baseline_projected`;
- settings equal to the accepted AB1d2 4096-spp readback;
- each calibration byte-identical to the host-planned real sensor at the mapped H0 gaze, never the fake local one;
- catalog seal `a0849b21…` (= NS1a) every time, and never opened.

Render times: L 18.81–19.20 s, R 18.26–18.66 s per pair. No re-render.

## 13. Per-action PERFECT correspondence and spherical geometry (checks 16–18)

| step | PERFECT correspondences | triangulated | κ median (min–max) | left range median | entities in view (points) |
|---|---|---|---|---|---|
| 0 | 64,598 | 64,598 | 45.9 (39.6–63.3) | 2.56 m | 172: 16,229 · 110: 46,209 · 125: 2,120 · 126: 40 |
| 1 | 64,600 | 64,600 | 42.4 (37.2–50.7) | 2.43 m | 172: 18,634 · 110: 42,846 · 125: 3,120 |
| 2 | 64,565 | 64,565 | 39.8 (34.7–49.4) | 2.29 m | 172: 19,531 · 110: 41,558 · 125: 3,476 |
| 3 | 64,804 | 64,804 | 38.1 (33.4–45.8) | 2.25 m | 172: 15,508 · 110: 46,220 · 125: 3,076 |
| 4 | 65,013 | 65,013 | 70.0 (52.6–84.8) | 3.98 m | **123: 6,291** · 212: 16,661 · 202: 15,111 · 110: 20,733 · 144: 4,489 · 207: 1,224 · 2: 504 |

- **Correspondence.** The accepted AB1b oracle produced the truth-stripped product (`left_core_row`, `left_core_col`,
  `uv_L`, `uv_R`). The checker's own oracle reproduced it, with Δ uv_R ≤ 1e-9 px.
- **Geometry.** The accepted AB1b spherical geometry ran under a truth-free guard (calibration + frozen product only).
  The checker's own triangulation reproduced it to ≤ 1e-9 m.
- **Identity.** It was attached only after the geometry freeze, from `instance_L` alone.

## 14. Per-action target fusion (contract section 16; check 19)

| step | target | patch | map before | target points | matched | affected surfels | matched distance median / p95 / max | new | map after | replay |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 172 | `ns1c_step_00` | 21,243 | 16,229 | 9,434 | 8,578 | 1.05 / 3.21 / 11.99 mm | 6,795 | 28,038 | exact |
| 1 | 172 | `ns1c_step_01` | 28,038 | 18,634 | 10,097 | 8,977 | 1.00 / 3.46 / 12.00 mm | 8,537 | 36,575 | exact |
| 2 | 172 | `ns1c_step_02` | 36,575 | 19,531 | 10,839 | 9,675 | 0.98 / 3.45 / 12.00 mm | 8,692 | 45,267 | exact |
| 3 | 172 | `ns1c_step_03` | 45,267 | 15,508 | 15,508 | 14,230 | 1.01 / 2.27 / 7.25 mm | 0 | 45,267 | exact |
| 4 | **123** | `ns1c_step_04` | 1,672 | 6,291 | 1,769 | 1,585 | 1.77 / 5.03 / 11.93 mm | 4,522 | **6,194** | exact |

- **Fusion rule.** Target only, canonical H0, association radius 0.012 m, hash cell 0.012 m, through the accepted
  `surface_map.fuse` with one exact replay.
- **Checker reproduction.** The checker reproduced every fusion bitwise and with its own brute-force association.
- **Incidental entities.** The incidental ids in view, including the coherent 202 and 212 at step 4, were never fused.
  Every non-target map is byte-identical before and after each step, and the patch ids are unique.
- **Step 3.** All 15,508 target points re-measured existing surfels within 12 mm; no new surfel was added.

## 15. Controller-state support vs North-Star measurement (descriptive; `controller-vs-northstar-support.png`)

| look | controller-state target support (matcher-valid) | North-Star raw-core target points |
|---|---|---|
| init looks, rank 1 (9 / 12 / 204 / 230 / 231) | 0 / 0 / 0 / 0 / 0 | 268 / 36,126 / 3,493 / 1,671 / 2,960 |
| init looks, rank 6 (123 / 129 / 172 / 202 / 212) | 2,668 / 0 / 4,118 / 270 / 954 | 1,672 / 174 / 12,072 / 217 / 2,756 |
| 172, NS1b action | 15,175 | 18,525 |
| step 0 / 1 / 2 / 3 (172) | 6,151 / 12,634 / 21,529 / 17,318 | 16,229 / 18,634 / 19,531 / 15,508 |
| step 4 (123) | 7,761 | 6,291 |

The two representations differ in both directions:
- At the rank-1 initialization gaze the controller observation state has no target support.
- At steps 2–4 the controller state counts more target points than the North-Star raw core.

These figures are descriptive only. Nothing was changed because of them.

## 16. The exact event that ended 172's service

After step 3 (global step 3, own looks 6), the target re-probe of 172 is:
- **FSG6f `no_frontier`.** Frontier raw 194, open 58, map-resolved 10, boundary-resolved 126. No candidate survived; 2
  were consensus-rejected.
- **The Cyclopean handoff: `epistemic_fixation`.** Local (+6.2°, −1.2°), 274 eligible cells.
- **The Controller-02 v1 gate: REJECTED,** `untraceable_final_support` (v1 exposes traceable support only for FSG6f
  proposals).

So the gated state was **QUIET**: the event `quiet` for object 172 at global step 3. The watchdog was not reached (6 own
looks < 24), and the cap was not reached (4 < 24 new actions). The end of 172's service is therefore **natural quiet
under the accepted probe / gate**, not the watchdog or the cap.

## 17. First selected second entity

**Entity 123**, selected at global step 4 by the accepted scheduler's switch rule:
- the current entity 172 was not serviceable;
- of the serviceable ids, {123}, none was above 172;
- so the rule took the lowest serviceable id.

This is not a natural reactivation: 123 had been ACTIONABLE since the initial probe, and its probe was reused from the
cache at every step (its revision never changed). The attention bout became 2.

## 18. The first second-entity action

- **Fixation.** Local (−5°, +5°) in C_123, the frozen admissible FSG6f proposal of 123's initial probe (gate: novel
  serviceable support 37). That maps to H0 (−152.090°, +22.757°), 7.07° from 123's seed gaze.
- **Measurement.** One fixed-head 4096-spp pair, 65,013 PERFECT correspondences, all triangulated. 6,291 target points.
- **Fusion.** FUSED into 123's H0 map only: 1,672 → 6,194 surfels, with 1,769 matched (1,585 surfels affected; median
  1.77 mm) and 4,522 new. The replay was exact.
- **The one read-only post-action probe** (`steps/step-04/update/probes/e00123.json`):
  - FSG6f `no_frontier` (frontier raw 231, open 40, map-resolved 0, boundary-resolved 191);
  - Cyclopean `epistemic_fixation` local (−7.7°, −0.5°) → H0 (−147.644°, +27.374°);
  - gate `untraceable_final_support`, so QUIET.

  **This proposal was NOT executed.**

## 19. Frozen scene state after the stop

The stop came at global step 4 (`scene/final-scene-state.json`, `freeze/scene-freeze.json`). The table below is the
state after it:

| id | state | own looks | surfels | revision | probe |
|---|---|---|---|---|---|
| 9 | QUIET | 1 | 268 | [1, 268] | cached (initial) |
| 12 | QUIET | 1 | 36,126 | [1, 36126] | cached |
| **123** | QUIET | 2 | 6,194 | [2, 6194] | fresh (step 4; the post-action probe) |
| 129 | QUIET | 1 | 174 | [1, 174] | cached |
| **172** | QUIET | 6 | 45,267 | [6, 45267] | cached (step 3) |
| 202 | QUIET | 1 | 217 | [1, 217] | cached |
| 204 | QUIET | 1 | 3,493 | [1, 3493] | cached |
| 212 | QUIET | 1 | 2,756 | [1, 2756] | cached |
| 230 | QUIET | 1 | 1,671 | [1, 1671] | cached |
| 231 | QUIET | 1 | 2,960 | [1, 2960] | cached |

- **Accounting.** Accumulated physical observations: 5. Probe calls: 15 (10 initial + 5 fresh). Cache hits: 45. No
  untouched entity changed state, and no natural reactivation occurred.
- **Recomputed from scratch.** The checker re-probed the eight untouched entities from scratch: each is identical to its
  initial probe (check 21).
- **No further scheduler call.** Every coherent entity is QUIET in this frozen state, but the scheduler was **not**
  called again: the canonical stop precedes it. No coherent-subset quiescence and no scene closure is claimed.

## 20. Outcome reading (contract section 19)

**My reading: Outcome 1 — natural scene switch.**
- 172 was serviced until its gated probe was QUIET (section 16).
- The unchanged scheduler then switched to another ACTIONABLE coherent seed (123).
- One controller-selected physical observation executed for 123 and updated its persistent H0 map (FUSED, +4,522
  surfels, genuine 12-mm overlap with its seed).

It is not Outcome 2: no watchdog was involved. It is not Outcome 3: the scheduler was never terminal. It is not Outcome
4: the NS1b reproduction, chart covariance, the fixed head, the scheduler recomputation and the pipeline all held, and
the cap was not reached.

Observations for Luiz and Chat (descriptive, not decisions):
1. **Eight of the ten coherent seeds were QUIET at the start, and stayed QUIET.** Each holds a Cyclopean proposal that
   the v1 gate rejects. In NS1c every probe is gated (contract section 12, from the mandate's B8). In the accepted
   Controller-02 scene loop, by contrast, the v1 gate applies only to the final residue probe, and the normal loop
   counts any FSG6f or Cyclopean proposal as ACTIONABLE.
2. **All five rank-1 seeds have 0 controller-state target support at their initialization look.** This is the planar
   rectified-core pathology at the near-baseline rank-1 gaze. Their FSG6f probes found no frontier.
3. **172's and 123's own post-action probes ended in the same way:** FSG6f `no_frontier` → Cyclopean proposal → gate
   rejection.

## 21. Checks (MEASURED)

**`check_ns1c.py`: 27/27** (`NORTH_STAR1C_CHECKS_PASS`; `check-summary.json` `85cb931f…`, written at `416a29c`). The
checker keeps its own literal pins. It recomputes independently wherever an independent formula exists:
- the coherent set (own rule);
- the charts (own triple product);
- the world gazes (own column form);
- the fixed-head calibrations;
- the oracle and the triangulation (the accepted NS1a checker's own implementations);
- the 12-mm association (own brute force);
- the service states (own gate / watchdog rule);
- the scheduler decisions (the accepted scheduler on own summaries).

Every recorded probe is recomputed from its reconstructed context. The 172 probe is compared with the accepted NS1b
record.

The 27 checks cover:
- provenance (01); pins (02); eligibility (03); deferred absent (04); charts fixed (05); constants and watchdog (06);
- fixed head (07); initial state (08); initial probes once + own rotation (09); NS1b reproduction (10);
- service states (11); scheduler (12); world gaze (13); own looks / cap (14); observations (15); oracle (16);
- geometry (17); identity (18); target-only fusion (19); update + cache (20); reactivation / untouched (21);
- the stop (22); process + code scan (23); truth boundary (24); terminology (25); figures (26); manifest and declared
  changes (27).

**Synthetic: 20/20** (`NS1C_SYNTHETIC_PASS`; analytic, before any NS1a / NS1b data):
- charts on all six NB1c gazes and the singular-chart refusal;
- local ↔ H0 round trips;
- the eligibility rule and the name / catalog refusal;
- the scheduler cases: retain, forward switch, wrap, Stop → `COHERENT_SUBSET_QUIESCENT`, Incomplete →
  `COHERENT_SUBSET_INCOMPLETE`;
- the watchdog and sticky BLOCKED;
- a deferred id in the summaries refused;
- the fixed head and the fake chart-local head refused;
- the first world action is the real sensor;
- target-only fusion and the 12-mm H0 known answer;
- unique patch ids;
- the post-stop refusal and the global cap;
- the scene-closure marker refused;
- the revision / refresh events and the adapter restore.

**Repository gates on the report tree (MEASURED):** layout 620/620, `scripts/verify_baseline.sh` 9/9,
`git diff --check` clean, `check_ns1c.py` (read-only) 27/27.

## 22. Corruption suite (MEASURED): 45/45 caught, 1 not applicable

`NORTH_STAR1C_MUTATIONS_CAUGHT`:
- It started from a passing baseline, after an unmodified-mirror null probe that passed all 27 checks.
- Each corruption mutated a temporary mirror (large arrays symlinked and unlinked before writing). The mirror's
  manifest was then regenerated, so the manifest check is not what catches it.
- RUN and VIS were hashed before and after the suite and are unchanged.

| family | corruptions (catching checks) |
|---|---|
| ELIGIBILITY | include 10 / 110 / 178 (03, 04, 12 each); drop a coherent seed (03, 04); names / catalog read (03, 24) |
| INITIAL STATE | 172 reverted to its NS1a map (08); NS1b action removed from 172's history (08, 14); 172 visited gaze altered (08); another seed's look re-rendered (08) |
| CHART | recentered after an action (05); map centroid (05); axis flipped (05); transposed (05) |
| SCHEDULER | current = None (12); target chosen manually (12); switch while 172 still actionable (11, 12); deferred ids marked QUIET (04) |
| WATCHDOG | limit changed (02, 14); 172 own-look count reset (14); watchdog changed in-process (06) |
| PHYSICAL ACTION | local gaze as H0 gaze (07, 13); head moved (07, 13); IPD changed (07, 13); spp changed (15); re-render (15, 23) |
| MEASUREMENT | SGBM-like correspondence (16); other persistent geometry (17); Position leak into the spherical stage (17, 24) |
| FUSION | an incidental entity fused (19); all visible ids fused (19); radius changed, regenerated (19); fused in C (19); cross-id fusion (19) |
| STOP | a second action on the new target (22); a third entity (22); scene-closure marker emitted (25) |
| PROBE | NS1b reproduction altered (09, 10); policy constant in the record (06); an untouched entity changed silently (20, 21); truth read by the initial probe (09, 24) |
| VISUAL | deferred identities hidden (26); scheduler reason hidden (26); fixed-head statement omitted (26); oracle label removed (26); a canonical pixel altered (26) |

NOT APPLICABLE: "scheduler ordering changed". At the switch, 123 was the only serviceable entity other than 172, so a
different ordering could not select a different target.

## 23. Visuals (Visual Language 1) and hashes

`VIS` (`visuals-manifest.json` `914e4eec1796598700f3c89cdee1bf6657af7d189ad10d7e736808f1211b1c50`):

| figure | truth badges | sha256 |
|---|---|---|
| `overview.png` | ORACLE INPUT, DERIVED | `bc4d0b6f5746de2a1bac9a24593f582c32766e668aaa6b47cd4f81a53b440a7a` |
| `scene-scheduler-timeline.png` | DERIVED | `0752e18ef697d070f8606b5c90335c5d7f56748c4e03fcf09487fa954864a3ba` |
| `multi-entity-growth-3d.png` | ORACLE INPUT, DERIVED | `beb3fd98aa0ada11644507b10d2a3374567f912de56cdb91abb4f52cd2625588` |
| `controller-vs-northstar-support.png` | ORACLE INPUT, DERIVED | `604f5a702e7df5307fbb28acf1681e20270efe9ee6f7f3d03c16dd662bee1f62` |

**`overview.png`:**
- **A:** the coarse 360° RGB backdrop (RGB-only NB1a sensory input, `cd2600e6…`), with the ten coherent seed maps in H0,
  172 ringed as current, the two chart centres, and 10 / 110 / 178 drawn apart as DEFERRED.
- **B:** the initial service map: VL1 state tiles and the per-entity numbers, the deferred tiles, and the NS1b
  reproduction line.
- **C:** the attention timeline. Five action cards, retain (single arrow) and switch (double arrow); the FIRST TARGET
  SWITCH is bold.
- **D:** 172 → 123, with the scheduler reason, 123's seed map (grey) and new surfels (blue), the executed fixation and
  its raw core, the new observation and the target-vs-other-id correspondence map.
- **E:** all coherent maps in a top view of canonical H0, the frozen service-state table, and 123's next proposal marked
  NOT EXECUTED.

**`scene-scheduler-timeline.png`:** rows are entities (the deferred rows hatched and never scheduled); columns are the
initial state and the state after each step. The current target is framed, and the switch arrow runs 172 → 123.

**`multi-entity-growth-3d.png`:** the canonical-H0 growth of 172 over its four actions, coloured by step, and of 123
before / after. Each has a top view and a view along its chart centre, with the fixed head and the gaze line.

**`controller-vs-northstar-support.png`:** section 15.

Regenerate:

    .venv/bin/python tools/north_star/ns1c_run.py visualize --run RUN --visuals VIS

## 24. Incidents

1. **Before the contract (calibration-only).** The rank-1 and rank-6 charts (contract section 3).
2. **Between the contract and the canonical run** (development, contract section 27; scratch runs only):
   - **Rehearsals.** Low-spp factory-startup renders, never Classroom:
     - scene {172, 10, 110, 178}: retain → switch to 10 (wrap) → stop;
     - scene {172, 178}: retain → terminal Stop → `COHERENT_SUBSET_QUIESCENT`.

     The 172 import reproduced the NS1b post-probe with 0 differences. No coherent entity other than 172 was probed.
   - **An entity-independent check** of the rank-1 controller observation state found 0 valid matcher points.
   - **Defects found and fixed inside the implementation commit:**
     - `schedule`'s next-step guard (it tested generator objects);
     - the cached-entity record copy in `update`;
     - the context map check, which assumed a single patch for rehearsal entities;
     - `loop` now refuses once the run has stopped;
     - the figure layout;
     - checker defects found on the rehearsal runs: check 10 skips the two keys the NS1b probe stage appended;
       check 24 admits the source stage's hash-only reads of exactly the pinned files; check 25's terminal-record read;
     - the corruption suite's choice of an untouched entity.
3. **Canonical run: no incident.**
   - Every canonical stage ran once, in order, from `f339598`, clean and pushed.
   - Five renders took 38.6–39.3 s each. Nothing was re-rendered, and no stage failed or was refused.
4. **After the canonical run** (contract section 27(b), presentation only, `416a29c`):
   - **The defect.** Overview panel D drew 123's ~3° × 3° seed map in the same blue as the fixation cross-hair, inside a
     44° × 36° window, so the map was hidden.
   - **The fix.** The tile now zooms on the fixation and separates the seed map, the new surfels and the cross-hair.
   - **Consequence.** `visualize` was re-run, and the run manifest was rewritten by it. No stage, run artifact or
     recorded number changed.
5. **Nothing in the contract was left unrun.**

## 25. What is established

- **The scene loop ran end to end with every accepted component unchanged.** The accepted deterministic scene scheduler
  (`fov3d.control.integrated.schedule`), driving per-entity fixed recentered policy charts and the accepted FSG6f →
  Cyclopean probe with the Controller-02 v1 gate, did the following on the accepted NS1b state:
  - continued servicing entity 172 for four PERFECT fixed-head actions, growing its H0 map from 21,243 to 45,267
    surfels;
  - observed 172 become QUIET naturally;
  - autonomously switched to another coherent RGB-bootstrap seed (123);
  - executed one controller-selected observation there, fused into 123's H0 map (1,672 → 6,194; 1,769 matched at
    median 1.77 mm).
- **Active attention spread from one entity to another**, through accepted service semantics and not a manual choice.
- **The physical head stayed fixed throughout.** All persistent geometry stayed in canonical H0, and fusion was target
  only.
- **Two per-entity charts.** The rank-6 chart (shared by five seeds) and the new rank-1 chart (five seeds) both met the
  NS1b chart requirements and passed the baseline-rotation covariance on every entity.

## 26. What is NOT established

- Full Classroom closure, or the quiescence of the coherent subset. The scheduler was not called after the stop.
- The serviceability of the eight entities that were QUIET from the start, beyond their gated probes. In particular,
  whether they would be serviceable under the ungated normal-loop semantics of the accepted Controller-02 loop.
- Anything about the multi-part oracle identities 10, 110, 178.
- Natural correspondence or natural identity: both are oracle aids.
- That the charts are optimal. That the near-baseline rank-1 controller observation state (0 matcher points) is
  adequate.
- Head motion, real cameras or other scenes.

## 27. Unresolved decision for Luiz / Chat

    READY TO RELEASE THE FULL COHERENT MULTI-ENTITY NORTH-STAR LOOP?

The measured inputs:
- Outcome 1: a natural switch 172 → 123 under the unchanged scheduler.
- 5 actions, all FUSED; 172 21,243 → 45,267; 123 1,672 → 6,194.
- The NS1b post-probe reproduced exactly; checks 27/27; corruptions 45/45.
- 8 of 10 coherent seeds QUIET under gated probes (Cyclopean proposals rejected by v1). The 5 rank-1 seeds have 0
  controller-state support.
- In the frozen final table every coherent entity is QUIET (not a scheduler decision).

This report makes no loop design.

NS1c REVIEW PENDING · DECISION PENDING: READY TO RELEASE THE FULL COHERENT MULTI-ENTITY NORTH-STAR LOOP?
