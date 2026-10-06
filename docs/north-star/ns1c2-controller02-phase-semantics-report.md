# North Star-1c2 — Correct Controller-02 NORMAL / RESIDUE Semantics — report

**Marker.**

    NORTH_STAR1C2_CONTROLLER02_PHASE_SEMANTICS_COMPLETE

**Status: REVIEW PENDING.** No ACCEPTED marker is written. Neither NS1c2 nor NS1c is merged.

> **Question.** Starting from the accepted NS1b North-Star state, does the first scene-level attention switch occur under
> the ACTUAL ACCEPTED Controller-02 NORMAL / RESIDUE semantics?

**Answer (MEASURED, one canonical run): yes. My reading is Outcome 1 — a natural quiet switch.**

- **The only change from NS1c: `final_look_gate_v1` runs in RESIDUE only.** Every NORMAL probe ran ungated: 0 final-gate
  calls in NORMAL in every stage, and 0 calls of the gate's predicted calibration (P3) in every NORMAL probe.
- **All ten coherent seeds are NORMAL ACTIONABLE at the start**: 172 and 123 through FSG6f, the other eight through
  Cyclopean. NS1c had labelled those eight QUIET.
- **NS1c's four FSG6f actions on 172 were replayed read-only.** The corrected NORMAL decisions selected exactly the same
  four actions. Nothing was re-rendered. Fusion, controller state, evidence and probes are all equal to NS1c's.
- **The first true divergence is 172 after step 3** (6 own looks, 45,267 surfels):
  - FSG6f `no_frontier`;
  - Cyclopean proposal local (+6.2°, −1.2°) → H0 (−163.040°, +31.040°).

  NS1c gated that proposal (REJECT → QUIET → switch to 123). NS1c2 did not call the gate: 172 stayed ACTIONABLE and
  `schedule_normal` retained it.
- **172 continued for 3 new 4096-spp NORMAL actions**: Cyclopean, then FSG6f (a new frontier appeared), then Cyclopean.
  Its map grew 45,267 → 47,892 surfels.
- **After step 6, 172's ProbeResult carried no action**: FSG6f `no_frontier` and Cyclopean `attention_complete`
  (0 eligible cells). So 172 became **QUIET** with 9 own looks, well below the ordinary budget of 24.
- **The accepted `schedule_normal` switched 172 → 202** (global step 7). 202 is the lowest NORMAL-serviceable id above
  172.
- **One NORMAL Cyclopean action on 202**: local (−5.9°, +5.5°) → H0 (−151.282°, +22.052°). 17,447 PERFECT target points;
  202's map grew 217 → 17,371 surfels (293 matched, median 3.24 mm; 17,154 new).
- **NS1c2 stopped there.** The read-only post-action probe of 202 is ACTIONABLE with an FSG6f proposal; it was NOT
  executed.
- **No deferral, no RESIDUE, no gate call in the scene loop.**

The physical head never moved. Every chart is a POLICY COORDINATE CHART only, and all persistent geometry is in canonical
H0. Truth labels:
- CORRESPONDENCE: PERFECT / ORACLE.
- IDENTITY: ORACLE SEGMENTATION AID.
- GEOMETRY: DERIVED spherical geometry.
- CONTROLLER OBSERVATION STATE: the accepted Classroom controller-time oracle matcher.

## 1. Provenance

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (verified by `source` and check 01) |
| base (`main`, NS1c review decision) | `e2a7bb65434a0a2ec4d862a4c70918e00a472416` |
| branch | `north-star/ns1c2-controller02-phase-semantics`, isolated worktree |
| contract | `fa1da52f03366cb1a781b0ad6bd710e235b478f2` (before any implementation, probe, replay or render; unchanged since, check 01) |
| implementation | `0c83bb01eb6b6e1aa775ac7cf75a047183e28095` (every canonical stage ran from it, clean and pushed) |
| report | this commit |
| NS1b acceptance / NS1a acceptance | `2553551` / `37c7e02` |
| NS1c diagnostic source (NOT accepted, NOT merged) | implementation `f339598`, report head `4107be8`; run manifest `90e2dd4b…` (252 files; every NS1c file read equals its entry) |

- Run `RUN` = `/home/lvelho/rd/f3d-vision/previews/north-star/ns1c2-controller02-phase-semantics/`: 662 MB, 279 files;
  `manifest.json` `0ec6228d…`; `check-summary.json` `dae0671d…`.
- Visuals `VIS` = `/home/lvelho/rd/f3d-vision/visuals/north-star/ns1c2-controller02-phase-semantics/`.

### What ran (MEASURED, `process-log.jsonl`; 71 entries, all `ok`, all from `0c83bb0`, clean and pushed)

| # | command (`tools/north_star/ns1c2_run.py`) | result | seconds |
|---|---|---|---|
| 1 | `source` | 46 source pins; NS1a / NS1b handoff; 44 NS1c prefix pins + NS1c manifest; Controller history pins; budget 24 (live); NS1c not accepted | 0.1 |
| 2 | `synthetic` | `NS1C2_SYNTHETIC_PASS` 17/17 | 0.4 |
| 3 | `known-answer` | historical Controller-02 trace PASS; residue-gate harness PASS | 0.5 |
| 4 | `eligibility` | derived {9, 12, 123, 129, 172, 202, 204, 212, 230, 231}; deferred {10, 110, 178} | 0.02 |
| 5 | `charts` | 10 charts; C_172 = NS1b chart | 0.04 |
| 6 | `contexts` | 10 contexts; 172 imported exactly | 1.0 |
| 7 | `initial-probe` | 10 ungated NORMAL probes + 20 rotated probes; all ACTIONABLE | 8.7 |
| 8 | `prefix` | NS1c steps 0–3 replayed (`schedule`, `replay`, `fuse`, `update` each; no Blender) | 18.4 |
| 9 | `divergence` | 172 ACTIONABLE (Cyclopean); retain; cap 19; frozen | 0.08 |
| 10 | `loop` | 4 new steps × 11 stages; the switch at step 7; canonical stop | 174.4 |
| 11 | `visualize` | 5 figures | 1.4 |
| 12 | `check_ns1c2.py --corruptions --write-summary` | 32/32; null probe clean; corruptions 41/41 | 215 (batch) |

New steps took 41.6–47.1 s each; `acquire` took 37.8–38.9 s. The time projection never approached the 1,800 s limit.

## 2. The NS1c review decision (durable, on `main` at `e2a7bb6`)

`docs/north-star/ns1c-review-decision.md` records the decision: NS1c is REVIEWED, NOT ACCEPTED and NOT MERGED; its branch
stays at `4107be8`; its run is diagnostic evidence. The reason: NS1c applied `final_look_gate_v1` in NORMAL service.

Check 03 verifies all of this on the checked tree: there is no NS1c ACCEPTED marker in any tracked document, and the NS1c
report head is an ancestor of neither the checked tree, nor `origin/main`, nor the base.

## 3. Historical known answer (ACCEPTED HISTORICAL REFERENCE; pinned, not an NS1c2 measurement)

Values are pinned literally from the accepted reports.

- **Controller-01 (ideal / oracle matcher):**
  - 25 localized objects;
  - 141 observations (25 seed / 50 FSG6f / 66 Cyclopean);
  - 26 switches (2 by natural reactivation); 27 bouts;
  - 1,059,349 final active-map surfels;
  - 28,801 / 29,288 reachable samples within 12 mm (0.9833720295001366);
  - per-object coverage 1.0 for 16 of 25;
  - terminal: 24 QUIET, 1 watchdog-blocked (210).
- **Controller-02:** replayed 141 / 141 ordinary actions; the gate ran only after NORMAL exhaustion, once (210, rejected).

**NS1c2's adapter reproduces that history (MEASURED, `known-answer`).** It was driven over the accepted Controller-02
record using name-free sources only: the 25 Controller-01 trajectories, Controller-02 `events.json` and
`final-residue.json`. All of the following matched:
- 141 / 141 selected actions (target, source, gaze, local step) and 56 / 56 events;
- 26 switches (2 `natural_reactivation`) and 27 bouts;
- 210 DEFERRED at step 101 with 24 fixations;
- RESIDUE at step 141, with exactly one gate call, in RESIDUE, on 210's unchanged FSG6f proposal (7.6°, 18.2°);
- 210 `FINALIZED:final_probe_rejected`, and 0 gate calls in NORMAL.

## 4. Authoritative semantics and the phase adapter (contract section 6)

**Option A.** `tools/north_star/ns1c2_phase.SceneMachine` is a resumable adapter. It mirrors
`fov3d.control.controller02.run_controller02` statement by statement and uses the accepted types and `schedule_normal`
directly. `fov3d` is unchanged (pinned).

- **NORMAL.** `local = ACTIONABLE if can_act(ProbeResult) else QUIET`, for both sources. An ACTIONABLE NORMAL object at
  24 own fixations becomes `DEFERRED:ordinary_budget`. `schedule_normal` retains or switches. There is no gate.
- **RESIDUE.** Entered only when `schedule_normal` returns None; it was never entered in this run.

**Equivalence proof (MEASURED, `synthetic`).** On six synthetic scenes, the adapter reproduces the accepted
`run_controller02` exactly, both driven from the seeds and resumed from JSON at intermediate steps. The scenes cover:
- FSG6f and Cyclopean proposals;
- natural reactivation;
- deferral, with rejected and admitted final looks;
- a final look that reactivates NORMAL work, and a second residue pass;
- deferred-QUIET finalization;
- seed failure and unlocated objects.

Between them they produce all 7 event kinds and all 3 residue outcomes. Two machine mutants (late deferral; dropped
reactivation reason) break the equivalence.

**The gate guard.** It substitutes the accepted Classroom `final_look_gate_v1` in every loaded module copy and refuses
any call outside RESIDUE. Production NORMAL probes call only `controller01.probe_local_policy` under the accepted NS1b
frame adapter; the gating `ns1b_core.probe` is never used (code scan, check 28).

## 5. Known-answer semantic gates (B4a–B4e; MEASURED)

| gate | result |
|---|---|
| B4a NORMAL classification | FSG6f → ACTIONABLE; Cyclopean → ACTIONABLE; none → QUIET; 0 gate calls. Gating mutants (FSG6f, Cyclopean) calling the real accepted gate are refused by the guard in NORMAL, and would have classified QUIET (NS1c's error). |
| B4b `schedule_normal` | retain; switch forward (212); wrap (12); DEFERRED skipped (204); finalized-only → None; nothing → None |
| B4c budget | 23 → ACTIONABLE; 24 → `ACTIONABLE/DEFERRED:ordinary_budget` (FSG6f and Cyclopean); QUIET at 24 → QUIET; never BLOCKED / FINALIZED |
| B4d RESIDUE only | a direct gate call in NORMAL is refused; a scene with NORMAL work has 0 gate calls; one deferred ACTIONABLE object after NORMAL exhaustion gets exactly one gate call, in RESIDUE |
| B4e historical trace | section 3 |
| residue-gate wiring harness | 172 at its accepted NS1b post-action state with own fixations set to 24 → `ACTIONABLE/DEFERRED:ordinary_budget` → `schedule_normal` None → RESIDUE → the production residue path. The verdict equals the accepted NS1b gate record: admissible, `novel_support_in_predicted_cores`, novel serviceable support 22, gate detail equal at tolerance 0. Not executed. This is a one-entity harness, reported separately from the scene loop. |

## 6. Eligible set and deferred identities (checks 04, 05)

The rule is `initialized AND contributing_patches == 1`, the same as NS1c, derived from the frozen NS1a seed set with no
name or catalog.
- Coherent: {9, 12, 123, 129, 172, 202, 204, 212, 230, 231}, equal to the expectation after derivation.
- Deferred: 10, 110, 178. They appear in no status, scheduler input, adapter order, table or target.
- Charts: two numeric values (rank 1 and rank 6; C_172 = NS1b's chart bitwise). They are fixed for the whole run.

## 7. Initial state (check 08)

- **172**: the accepted NS1b post-action context and map, imported exactly. 21,243 surfels; 2 own looks; visited (0, 0)
  and (0, −5); current local gaze (0, −5). Its evidence is recomputed from the two looks.
- **The other nine**: their frozen NS1a maps and saved initialization looks, with no rerender; 1 own look each.

## 8. Prefix replay — NS1c steps 0–3, read-only (checks 16, 21–25)

| step | target | `schedule_normal` | source | local | H0 | decision = NS1c | replay verified | fusion = NS1c (bitwise) | update = NS1c | map |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 172 | retain | fsg6f | (−5.0, −10.0) | (−147.585, +37.246) | yes | yes (21 files) | yes | yes | 21,243 → 28,038 |
| 1 | 172 | retain | fsg6f | (−5.0, −15.0) | (−145.704, +42.032) | yes | yes | yes | yes | 28,038 → 36,575 |
| 2 | 172 | retain | fsg6f | (−5.0, −20.0) | (−143.516, +46.782) | yes | yes | yes | yes | 36,575 → 45,267 |
| 3 | 172 | retain | fsg6f | (+0.0, −20.0) | (−150.152, +48.188) | yes | yes | yes | yes | 45,267 → 45,267 |

At every prefix step all of the following held:
- **Selection.** Target 172, scheduler `retain`, source `fsg6f`; local gaze, H0 gaze and planned-calibration bytes equal
  to NS1c's.
- **No process.** Every prefix stage ran under the accepted `NoProcessGuard`, with 0 attempts. No `preflight` or
  `acquire` ran, and no observation product was written in a prefix step.
- **Measurement equal.** Observation, PERFECT correspondence, spherical geometry and identity were verified in place
  against NS1c's freezes and manifest. The checker's own oracle and triangulation reproduce them.
- **Persistence equal.** The fused map equals NS1c's bitwise (NS1c's patch ids `ns1c_step_00..03`). The controller
  observation state, evidence, history, visited gazes, own looks and revision equal NS1c's.
- **Probe equal.** The policy part of the ungated re-probe equals NS1c's recorded probe at tolerance 0. NS1c's gate
  verdicts are ignored: they admitted these FSG6f proposals.

## 9. The first true divergence (stage `divergence`; frozen before any render; check 17)

Post-step-3 state of 172: 6 own looks, 45,267 surfels, revision [6, 45267], chart C_172.
- FSG6f `no_frontier`: frontier raw 194, open 58, map-resolved 10, boundary-resolved 126; 0 candidates.
- Cyclopean `epistemic_fixation`: 274 eligible cells; local (+6.2°, −1.2°) → H0 (−163.040°, +31.040°); leverage 0.968.
- NORMAL local state ACTIONABLE, disposition NORMAL.
- `schedule_normal` retains 172 with exactly this proposal.

The derived cap is (24 − 6) + 1 = **19**, equal to the expectation; it was frozen and never changed. The divergence
freeze precedes every step-4 stage in the process log.

## 10. NS1c vs NS1c2 at the same state (headline; `ns1c-vs-ns1c2-divergence.png`)

| | NS1c (NOT ACCEPTED) | NS1c2 |
|---|---|---|
| FSG6f | `no_frontier` | `no_frontier` (identical) |
| Cyclopean | proposal (+6.2°, −1.2°) | the same proposal (policy part equal at tolerance 0) |
| final gate | CALLED in NORMAL → REJECT `untraceable_final_support` | NOT CALLED (0 calls) |
| service state | QUIET | **ACTIONABLE** |
| scheduler | SWITCH → 123 | **RETAIN → 172** |

## 11. Corrected initial service table (all ten, ungated; B9; checks 09, 11)

| id | rank | surfels | own looks | FSG6f | Cyclopean | source | local proposal | H0 proposal | NORMAL state | = NS1c policy |
|---|---|---|---|---|---|---|---|---|---|---|
| 9 | 1 | 268 | 1 | no_frontier | epistemic_fixation | Cyclopean | (−6.0, −2.1) | (+70.42, +8.86) | ACTIONABLE | yes |
| 12 | 1 | 36,126 | 1 | no_frontier | epistemic_fixation | Cyclopean | (−5.6, −0.6) | (+71.51, +9.98) | ACTIONABLE | yes |
| 123 | 6 | 1,672 | 1 | continue | – | FSG6f | (−5.0, +5.0) | (−152.09, +22.76) | ACTIONABLE | yes |
| 129 | 6 | 174 | 1 | no_frontier | epistemic_fixation | Cyclopean | (+5.1, +4.5) | (−162.78, +25.24) | ACTIONABLE | yes |
| **172** | 6 | 21,243 | 2 | continue | – | FSG6f | (−5.0, −10.0) | (−147.59, +37.25) | ACTIONABLE | yes |
| 202 | 6 | 217 | 1 | no_frontier | epistemic_fixation | Cyclopean | (−5.9, +5.5) | (−151.28, +22.05) | ACTIONABLE | yes |
| 204 | 1 | 3,493 | 1 | no_frontier | epistemic_fixation | Cyclopean | (+5.9, +0.8) | (+82.29, +5.48) | ACTIONABLE | yes |
| 212 | 6 | 2,756 | 1 | no_frontier | epistemic_fixation | Cyclopean | (+3.9, +5.2) | (−161.61, +24.36) | ACTIONABLE | yes |
| 230 | 1 | 1,671 | 1 | no_frontier | epistemic_fixation | Cyclopean | (−5.5, −0.4) | (+71.70, +10.10) | ACTIONABLE | yes |
| 231 | 1 | 2,960 | 1 | no_frontier | epistemic_fixation | Cyclopean | (+0.6, +0.3) | (+77.43, +7.71) | ACTIONABLE | yes |

- The NS1c diagnostic expectation (all ten ACTIONABLE; FSG6f for 123 and 172) holds.
- 172 reproduces the accepted NS1b post-action probe exactly in its policy part.
- Every probe passes the baseline-rotation invariance (β = +37°, −61°; the checker's own β = −23°).
- `untraceable_final_support` plays no role: the gate was never invoked.

## 12. Action trace (every proposal source; checks 12, 13, 18, 19)

| step | phase | target | scheduler | source | local | H0 | map before | target points | matched (median) | new | map after | own looks | after |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 (NS1c) | NORMAL | 172 | retain | FSG6f | (−5.0, −10.0) | (−147.585, +37.246) | 21,243 | 16,229 | 9,434 (1.05 mm) | 6,795 | 28,038 | 3 | ACTIONABLE |
| 1 (NS1c) | NORMAL | 172 | retain | FSG6f | (−5.0, −15.0) | (−145.704, +42.032) | 28,038 | 18,634 | 10,097 (1.00 mm) | 8,537 | 36,575 | 4 | ACTIONABLE |
| 2 (NS1c) | NORMAL | 172 | retain | FSG6f | (−5.0, −20.0) | (−143.516, +46.782) | 36,575 | 19,531 | 10,839 (0.98 mm) | 8,692 | 45,267 | 5 | ACTIONABLE |
| 3 (NS1c) | NORMAL | 172 | retain | FSG6f | (+0.0, −20.0) | (−150.152, +48.188) | 45,267 | 15,508 | 15,508 (1.01 mm) | 0 | 45,267 | 6 | ACTIONABLE |
| **4** | NORMAL | 172 | retain | **Cyclopean** | (+6.2, −1.2) | (−163.040, +31.040) | 45,267 | 14,866 | 13,213 (1.64 mm) | 1,653 | 46,920 | 7 | ACTIONABLE |
| 5 | NORMAL | 172 | retain | FSG6f | (+6.2, +3.8) | (−163.874, +26.094) | 46,920 | 9,760 | 8,788 (1.79 mm) | 972 | 47,892 | 8 | ACTIONABLE |
| 6 | NORMAL | 172 | retain | Cyclopean | (+0.2, −10.7) | (−153.654, +39.235) | 47,892 | 18,642 | 18,642 (1.09 mm) | 0 | 47,892 | 9 | **QUIET** |
| **7** | NORMAL | **202** | **switch** | Cyclopean | (−5.9, +5.5) | (−151.282, +22.052) | 217 | 17,447 | 293 (3.24 mm) | 17,154 | 17,371 | 2 | ACTIONABLE |

Every decision equals the accepted `schedule_normal` on the checker's own statuses (check 12). An independent re-drive of
the adapter over the recorded probes reproduces every decision, event, phase, current object, bout and status (check 13).

172's post-action probes:
- after step 4: FSG6f `continue` (frontier open 159, 1 candidate) → (+6.2, +3.8);
- after step 5: FSG6f `no_frontier`, Cyclopean `epistemic_fixation` (43 eligible cells) → (+0.2, −10.7);
- after step 6: FSG6f `no_frontier` and Cyclopean `attention_complete` (0 eligible cells) → no action → QUIET (the
  `quiet` event at global step 6; 9 own looks).

## 13. Phase and gate accounting (checks 14, 15)

| quantity | value |
|---|---|
| NORMAL actions | 8 (4 replayed NS1c + 4 new) |
| **final-gate calls in NORMAL** | **0** (every stage's guard record; every NORMAL probe: `gate_called` false, P3 = 0) |
| DEFERRED objects / events | 0 (172 left NORMAL service by natural QUIET at 9 own looks) |
| RESIDUE entered | no |
| residue gate calls / final residue observations | 0 / 0 |
| events | 1 (`quiet`, 172, step 6); no natural reactivation |
| probe calls / cache hits (adapter) | 18 / 72 |

14. **The DEFERRED event:** none occurred (the budget was not reached).
15. **RESIDUE:** not reached. The RESIDUE machinery is implemented and was exercised by the differential, the historical
    trace and the residue-gate harness (sections 4–5).

## 16–17. The first accepted scene switch and the second-target action (checks 12, 27)

- **When.** Global step 7, attention bout 2, transition 172 → 202.
- **Why.** 172 was NORMAL QUIET, a natural quiet: its ProbeResult had no action, far below the budget. `schedule_normal`
  saw ACTIONABLE 9, 12, 123, 129, 202, 204, 212, 230, 231 and QUIET 172, and took the lowest serviceable id above 172:
  **202**. This is not a reactivation.
- **The action.** 202's unchanged Cyclopean proposal: local (−5.9°, +5.5°) → H0 (−151.282°, +22.052°), 15.1° from its seed.
  - One fixed-head 4096-spp pair: 64,768 PERFECT correspondences, all triangulated.
  - 17,447 target points, FUSED into 202's H0 map only: 217 → 17,371 (293 matched, 211 surfels affected, median
    3.24 mm, p95 10.4 mm; 17,154 new). The replay was exact.
- **The read-only post-action probe of 202** (`steps/step-07/update/probes/e00202.json`): ACTIONABLE.
  - FSG6f `continue` (frontier open 180, 2 candidates) → local (−10.9°, +10.5°) → H0 (−147.628°, +15.923°).
  - **NOT EXECUTED.**

## 18. Per-action H0 fusion (check 24)

- **Fusion rule.** Target only, canonical H0, 12 mm / 12 mm, the accepted `surface_map.fuse` with one exact replay.
- **Checker reproduction.** Every fusion is reproduced bitwise and by the checker's own brute-force association.
- **Incidental entities in view were never fused** (target-only persistence, frozen):
  - step 5: 212 (22,399 points) and 129 (777);
  - step 7: 212 (15,798) and 123 (5,779);
  - 110 in every look.

  Every non-target map is unchanged at every step.
- **Patch ids.** `ns1c_step_00..03` (NS1c's measurements) and `ns1c2_step_04..07`.

## 19. Controller-state support vs North-Star measurement (descriptive; `controller-vs-northstar-support.png`)

| look | controller-state target support | North-Star raw-core target points |
|---|---|---|
| init, rank 1 (9 / 12 / 204 / 230 / 231) | 0 / 0 / 0 / 0 / 0 | 268 / 36,126 / 3,493 / 1,671 / 2,960 |
| init, rank 6 (123 / 129 / 172 / 202 / 212) | 2,668 / 0 / 4,118 / 270 / 954 | 1,672 / 174 / 12,072 / 217 / 2,756 |
| steps 0–3 (172) | 6,151 / 12,634 / 21,529 / 17,318 | 16,229 / 18,634 / 19,531 / 15,508 |
| steps 4–6 (172) | 16,241 / 10,329 / 21,304 | 14,866 / 9,760 / 18,642 |
| step 7 (202) | 24,466 | 17,447 |

- **Rank-1 zero support is retained and was not fixed.** No rank-1 entity was selected, so it caused no failure here.
- **Rank-1 entities are still ACTIONABLE.** All five are NORMAL ACTIONABLE through Cyclopean, despite 0 controller-state
  support.

## 20. Final frozen state (`scene/final-scene-state.json`, `freeze/scene-freeze.json` `ea5d0465…`)

| id | NORMAL state | own looks | surfels | revision | proposal | probe |
|---|---|---|---|---|---|---|
| 9 | ACTIONABLE | 1 | 268 | [1, 268] | Cyclopean (−6.0, −2.1) | cached |
| 12 | ACTIONABLE | 1 | 36,126 | [1, 36126] | Cyclopean (−5.6, −0.6) | cached |
| 123 | ACTIONABLE | 1 | 1,672 | [1, 1672] | FSG6f (−5.0, +5.0) | cached |
| 129 | ACTIONABLE | 1 | 174 | [1, 174] | Cyclopean (+5.1, +4.5) | cached |
| **172** | QUIET | 9 | 47,892 | [9, 47892] | – | cached |
| **202** | ACTIONABLE | 2 | 17,371 | [2, 17371] | FSG6f (−10.9, +10.5), NOT EXECUTED | fresh |
| 204 | ACTIONABLE | 1 | 3,493 | [1, 3493] | Cyclopean (+5.9, +0.8) | cached |
| 212 | ACTIONABLE | 1 | 2,756 | [1, 2756] | Cyclopean (+3.9, +5.2) | cached |
| 230 | ACTIONABLE | 1 | 1,671 | [1, 1671] | Cyclopean (−5.5, −0.4) | cached |
| 231 | ACTIONABLE | 1 | 2,960 | [1, 2960] | Cyclopean (+0.6, +0.3) | cached |

- The scene phase is NORMAL. There were 8 accumulated physical observations: 4 replayed and 4 new.
- The checker re-probed the eight untouched entities from scratch; each equals its initial probe (check 26).
- The scheduler was not called after the stop. No coherent-subset closure and no scene closure is claimed.

## 21. Outcome reading

**My reading: Outcome 1 — a natural quiet switch.** Under the accepted NORMAL semantics:
- 172 kept servicing (Cyclopean and FSG6f proposals both counted) until its own ProbeResult carried no action;
- 172 became QUIET at 9 own looks, before the ordinary budget;
- the accepted `schedule_normal` switched to the next NORMAL-serviceable entity (202);
- one ordinary controller-selected PERFECT observation executed there and was fused into 202's canonical-H0 map.

Why not the other outcomes:
- Not Outcome 2: there was no deferral.
- Not Outcome 3: NORMAL work never exhausted; nine entities stayed serviceable.
- Not Outcome 4: the prefix reproduced, the gate was never called in NORMAL, `schedule_normal` behaved as recomputed,
  every invariant held, and the cap was not reached (4 of 19).

Observations for Luiz and Chat (descriptive, not decisions):
1. **The corrected semantics changed the trajectory and the second target.** 172 received three more looks (one
   Cyclopean look exposed a new FSG6f frontier that the next look serviced), and attention moved forward to 202, not by
   wrap-around to 123. Under NS1c, 202 had been wrongly QUIET.
2. **172's quiet is now a genuine local quiet.** Neither FSG6f nor Cyclopean proposes anything. It is not a gate artifact.
3. **Target-only fusion left in-view coherent entities unfused** (212, 129, 123). In this run, untouched revisions never
   changed and no reactivation could occur. This frozen simplification is distinct from the Controller-01 measurement
   memory, which accumulated cross-target evidence.

## 22. Checks (MEASURED)

**`check_ns1c2.py`: 32/32** (`NORTH_STAR1C2_CHECKS_PASS`; `check-summary.json` `dae0671d…`).

The checker keeps its own literal pins and recomputes independently where an independent formula exists:
- the coherent set; the charts (triple product); the world gazes (column form); the fixed-head calibrations;
- the oracle and the triangulation (the accepted NS1a checker's implementations), for every step including the
  replayed prefix;
- the 12-mm association (brute force);
- the NORMAL classification and deferral;
- every `schedule_normal` decision.

It also re-runs:
- the synthetic known answers and the differential;
- the historical Controller-02 trace;
- the residue-gate harness;
- an adapter re-drive over the recorded probes;
- every recorded probe, from its reconstructed context.

The 32 checks:
- 01 provenance; 02 pins; 03 NS1c decision; 04 eligibility; 05 charts; 06 constants / budget / cap; 07 fixed head;
- 08 initial state; 09 initial probes; 10 known answers; 11 NORMAL classification; 12 scheduler; 13 adapter re-drive;
- 14 gate accounting; 15 budget / defer; 16 prefix replay; 17 divergence; 18 world gazes; 19 own looks / cap;
- 20 observations; 21 PERFECT correspondence; 22 geometry; 23 identity; 24 fusion; 25 update; 26 untouched;
- 27 stop; 28 process / code scan; 29 truth boundary; 30 terminology; 31 figures; 32 manifest and declared changes.

Synthetic: 17/17 (`NS1C2_SYNTHETIC_PASS`). Repository gates on the report tree: section 29.

## 23. Corruption suite (MEASURED): 41/41 caught, 0 not applicable

`NORTH_STAR1C2_MUTATIONS_CAUGHT`:
- The null probe on an unmodified mirror passed all 32 checks.
- Each corruption mutated a temporary mirror, or the code in-process, and the mirror manifest was regenerated.
- RUN and VIS were unchanged by the suite.

| family | corruptions (catching checks) |
|---|---|
| SEMANTICS | gate a Cyclopean NORMAL proposal (NS1c's rule, in-process) (09, 17, 26); gate an FSG6f NORMAL proposal (09, 14); a gate call while NORMAL (14); guard disabled (10); a Cyclopean proposal classified QUIET (11); a switch while 172 is NORMAL ACTIONABLE (12, 13) |
| BUDGET | budget 24 → 30 (06); BLOCKED instead of DEFERRED (11, 15); gated at the budget while NORMAL work remains (15) |
| RESIDUE (adapter source mutants) | RESIDUE while NORMAL work exists; deferred order changed; proposal altered before the gate; two final looks for one object (10 each) |
| PREFIX | one NS1c action altered (12, 16); one observation hash altered (16); Blender during the prefix (16, 28); only three prefix steps (16); NS1c's wrong QUIET state imported (11, 13) |
| TARGET SET | include 10 / 110 / 178 (04 each); names / catalog (04, 29) |
| CHART / SENSOR | dynamic recenter (05); fake local baseline (07, 18); head moved (07, 18) |
| MEASUREMENT | SGBM-like correspondence (21); planar persistent geometry (22); Position leak (22, 29) |
| FUSION | cross-target fusion; radius changed; fused in the chart (24 each) |
| STOP | a second action on 202; a third entity (27 each); a scene-closure claim (30) |
| PROBE | NS1b reproduction altered (09); an untouched entity changed silently (11, 26); truth read by the initial probe (09, 29) |
| VISUAL | phase hidden; a gate marker in NORMAL; oracle label removed; a canonical pixel altered (31 each) |

## 24. Visuals (Visual Language 1) and hashes

`VIS/visuals-manifest.json` `40662e9f9807dbb4e34530f3f38693f26d102f2f6e79e4ed1139f0160ee4eecb`:

| figure | sha256 |
|---|---|
| `overview.png` | `39f19feddb7508c547deb333d92ca19d57aec65985c35423673ef20e006ec830` |
| `ns1c-vs-ns1c2-divergence.png` | `d8a3e7bd8f12f6bad03f3f768a31811ddf61566e0efd15dec1db4e27aa0b3e69` |
| `controller-phase-timeline.png` | `9c189b3fb8163e730e73938139f7eda795c1774865d4c6002da64b59cf3ebd17` |
| `multi-entity-growth-3d.png` | `1a072adcaf365025f399390ad6cd76a3577d273ce82f7d79b74f442648f4d170` |
| `controller-vs-northstar-support.png` | `d9a18b90c232b17db5f3a698a81bd523f9f37b1bbf88d6b932437e128ea0f6a7` |

**`overview.png`:**
- **A:** the historical known answer, labelled ACCEPTED HISTORICAL REFERENCE, with the adapter's re-drive strip of the
  141 accepted actions (deferral at 101; the gate diamond inside RESIDUE).
- **B:** the semantic bug, side by side at the divergence state.
- **C:** the 172 continuation (dashed cards for the replayed NS1c prefix; red cards for the new steps).
- **D:** the first valid switch, 172 → 202.
- **E:** the phase state: NORMAL throughout; final-gate markers only inside RESIDUE (none occurred).

**Supporting figures:**
- the divergence figure (both flows, and the H0 sky with NS1c's switch target vs NS1c2's retained fixation);
- the phase timeline (rows entities; the deferred identities hatched; a source glyph per action);
- the growth of 172 (seven actions) and 202;
- support (descriptive).

Regenerate:

    .venv/bin/python tools/north_star/ns1c2_run.py visualize --run RUN --visuals VIS

## 25. Incidents and deviations

1. **Before the contract:** reading only (contract section 3).
2. **Development before the implementation commit** (scratch runs only):
   - **Rehearsal setup.** Scene {172, 10, 110, 178}; 16-spp factory-startup rehearsal renders; one no-render Classroom
     preflight on a throwaway copy of a rehearsal step's plan.
   - **Rehearsal results.** The NS1c prefix of 172 replayed with every equality. The divergence reproduced. The
     rehearsal loop stopped at the first switch (172 QUIET → 178). The corruption suite caught 27/27 of the applicable
     corruptions.
   - **Defects found and fixed inside the implementation commit:**
     - the NS1c-decision scan flagged the `main` layout checker, which names the NS1c ACCEPTED marker only to forbid
       it; the scan is now restricted to tracked Markdown documents;
     - the prefix `fuse` re-verified NS1c's whole correspondence freeze, and would have read raw EXRs (truth); it now
       hashes only the files it consumes, and `replay` keeps the full verification;
     - a key collision in the known-answer record (`sources`);
     - a synthetic scene that did not produce a deferred-QUIET object was redesigned;
     - figure layout.
   - **Not explicit in the contract.** The no-render Classroom preflight is not listed in contract section 28. NS1c's
     contract allowed it; it is disclosed here.
3. **Deviation from contract section 2.** Controller-02 `result.json` and `manifest.json` carry object names, so they
   were neither pinned nor opened. Only the name-free `events.json` and `final-residue.json` (and the 25 Controller-01
   trajectories) are read; the coverage numbers are literals from the accepted reports.
4. **Correction.** The implementation commit message says "42 corruptions"; the suite has 41.
5. **Canonical run: no incident.** Every canonical stage ran once, in order, from `0c83bb0`, clean and pushed. Nothing
   was re-rendered, and no stage failed or was refused.

## 26. What is established

- **The corrected placement produces the first valid North-Star scene switch.** With `final_look_gate_v1` in RESIDUE only
  and everything else frozen, the accepted Controller-02 NORMAL semantics did the following:
  - transported from the ideal-matcher Classroom controller to the RGB-bootstrap North-Star scene through fixed policy
    charts and canonical H0;
  - continued servicing 172 until it was genuinely locally QUIET (no FSG6f and no Cyclopean proposal; 9 own looks);
  - switched autonomously through the accepted `schedule_normal` to the next NORMAL-serviceable coherent seed (202);
  - executed one controller-selected PERFECT fixed-head observation there, fused into 202's canonical-H0 map
    (217 → 17,371 surfels).
- **NS1c's gate placement was the sole cause of the divergence.** Its first four actions are reproduced exactly; at the
  same post-step-3 state the identical probe yields ACTIONABLE and retain instead of QUIET and switch.
- **The phase adapter is equivalent to the accepted Controller-02 loop.** This rests on the synthetic differential, the
  JSON resumes, and the exact re-drive of the accepted Controller-02 Classroom history.
- **The physical head stayed fixed.** Fusion was target only in canonical H0.

## 27. What is NOT established

- Full Classroom closure, coherent-subset quiescence, or behavior beyond the first switch. 202 is still ACTIONABLE; the
  other eight seeds were never serviced.
- Whether the ordinary-budget DEFERRED / RESIDUE path behaves correctly on North-Star data. It was not reached; it is
  proven only by the synthetic differential, the historical trace and the one-entity harness.
- That target-only fusion is adequate. In-view coherent entities (212, 129, 123) were measured but not fused, and no
  reactivation was possible.
- That the rank-1 controller observation state is adequate. It has 0 support; no rank-1 entity was selected.
- Anything about 10 / 110 / 178; natural correspondence or natural identity (both are oracle aids); head motion, real
  cameras or other scenes.

## 28. Unresolved decision for Luiz / Chat

    READY TO RELEASE THE CORRECT MULTI-ENTITY NORTH-STAR LOOP?

The measured inputs:
- Outcome 1, with a natural quiet switch 172 → 202 under the exact Controller-02 NORMAL semantics.
- Final-gate calls in NORMAL: 0. No deferral; RESIDUE not reached.
- 8 actions, all FUSED: 4 replayed from NS1c and equal; 4 new.
  - 172: 21,243 → 47,892 surfels.
  - 202: 217 → 17,371 surfels.
- Checks 32/32; corruptions 41/41.
- Open simplifications: target-only fusion, rank-1 zero controller support, the multi-part identities.

This report makes no loop design.

## 29. Repository gates on the report tree (MEASURED)

Layout, `scripts/verify_baseline.sh`, `git diff --check` and a read-only `check_ns1c2.py` rerun are recorded in the report
commit message.

NS1c2 REVIEW PENDING · DECISION PENDING: READY TO RELEASE THE CORRECT MULTI-ENTITY NORTH-STAR LOOP?
