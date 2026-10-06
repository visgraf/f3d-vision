# North Star-1c2 — Correct Controller-02 NORMAL / RESIDUE Semantics — contract

**Status: CONTRACT (committed before any NS1c2 implementation commit, before any NS1c2 probe, before the prefix replay
and before any NS1c2 render).** Completion marker (written only by the report):
`NORTH_STAR1C2_CONTROLLER02_PHASE_SEMANTICS_COMPLETE`. No ACCEPTED marker is written by Claude Code.

Decision context (recorded on `main` at `e2a7bb6`, `docs/north-star/ns1c-review-decision.md`): NS1c is REVIEWED, NOT
ACCEPTED and NOT MERGED. NS1c applied `final_look_gate_v1` to every ordinary probe; accepted Controller-02 calls it only
in RESIDUE. NS1c's run is retained as diagnostic evidence. NS1c2 is next.

## 1. One causal question

> Starting from the accepted NS1b North-Star state, does the first scene-level attention switch occur under the ACTUAL
> ACCEPTED Controller-02 NORMAL / RESIDUE semantics?

The only independent variable relative to NS1c is **the placement of `final_look_gate_v1`**:

| | NS1c | NS1c2 |
|---|---|---|
| gate placement | applied to every local proposal (NORMAL service) | applied only in Controller-02 RESIDUE |
| NORMAL local state | ACTIONABLE iff the gate admits the proposal | ACTIONABLE iff the ProbeResult carries an action (FSG6f or Cyclopean) |
| at the ordinary budget | BLOCKED:watchdog (Controller-01 loop) | ACTIONABLE / DEFERRED:ordinary_budget (Controller-02) |
| scheduler | `integrated.schedule` | `controller02.schedule_normal` (the same retain / switch order over NORMAL-serviceable objects) |

Everything else stays frozen: the coherent set, the charts, the contexts, FSG6f, Cyclopean, the gate itself, the
24-fixation budget, the observation path, the PERFECT correspondence, the spherical geometry, the oracle segmentation aid,
target-only 12-mm fusion in canonical H0 and the fixed physical head. This is not a controller redesign, a new FSG6f,
a new Cyclopean policy, a new scheduler, a new watchdog, an identity, stereo or head-motion experiment.

The chain:

    accepted NS1b post-action state of 172 + frozen NS1a seed set
      -> the same COHERENT_SEED_SET, charts and contexts as NS1c          (sections 9-11)
      -> known-answer semantic gates, before any Classroom data is used     (section 7)
      -> ONE ungated NORMAL probe of every coherent entity (no render)      (section 12)
      -> the NS1c four-step prefix, replayed READ-ONLY (no Blender)          (section 13)
      -> the first true divergence: 172's post-step-3 Cyclopean proposal   (section 14)
      -> the Controller-02 NORMAL loop from that state, new renders         (sections 15-18)
      -> STOP after the first executed NORMAL action with target != 172    (section 19)

## 2. Provenance and branch

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (the legacy `fov-3d-vision` is never used) |
| base (`main`: NS1c review decision) | `e2a7bb65434a0a2ec4d862a4c70918e00a472416` |
| NS1b acceptance | `255355108863022f931574dae4b2df8cdd2a772e` (`NORTH_STAR1B_RECENTERED_CONTROLLER_HANDOFF_ACCEPTED`) |
| NS1a acceptance | `37c7e026f2ab514be392cd845d390fab2a2d86fc` |
| NS1c diagnostic source (NOT accepted, NOT merged) | implementation `f339598384b73c01bafc23e40013a6ee987142db`, figure fix `416a29c`, report head `4107be86228c970f4b82fb6d5343365c551f36b0`; run `previews/north-star/ns1c-coherent-first-scene-switch/` (read-only) |
| branch | `north-star/ns1c2-controller02-phase-semantics`, from the base, in an isolated worktree |
| run (`RUN`, machine evidence) | `/home/lvelho/rd/f3d-vision/previews/north-star/ns1c2-controller02-phase-semantics/` |
| visuals (`VIS`, persistent) | `/home/lvelho/rd/f3d-vision/visuals/north-star/ns1c2-controller02-phase-semantics/` |

The implementation commit writes this contract's commit SHA into `ns1c2_spec.CONTRACT_COMMIT` and the checker's literal;
the checker requires this file to be unchanged from that commit to the checked tree.

Frozen inputs (sha256; a mismatch is a STOP), every one listed in full in `ns1c2_spec`:
- NS1a run: the freezes and seed handoff pinned by NS1b / NS1c (observation freeze `46f0a22e…`, geometry freeze
  `7b0ae64d…`, seed-set freeze `4ee36a1a…`, `seeds/seed-set.json` `e2ff1ba3…`, `seeds/entity-maps.npz` `621d8902…`,
  gaze list `785d02a7…`, catalog seal `a0849b21…`).
- NS1b run (the accepted canonical run): the 17 files NS1c pinned (`manifest.json` `e859fa61…`, post-action map
  `bf831ad5…`, post-action probe `2918e146…`, …).
- NS1c run, read-only replay source: `manifest.json` `90e2dd4b8a2d287a47f22b4553903a06e0c1059105fec1f954c13da09d426638`
  (it lists the sha256 of all 252 run files; every NS1c file NS1c2 reads must equal its manifest entry) and
  `check-summary.json` `85cb931f…` (`NORTH_STAR1C_CHECKS_PASS`). Key prefix files are also pinned literally (decision,
  planned calibration, the three freezes, local identity, fusion record and fused map, controller state, evidence and
  post-action probe of steps 0–3).
- Accepted Controller-02 output `previews/controller-02-classroom-replay/`: `events.json` `fae7e648…`,
  `final-residue.json` `a315714f…`, `result.json` `a6dc4879…`, `manifest.json` `ad49e835…`. Accepted Controller-01
  name-free per-object trajectories `previews/controller-01-full/objects/instance_*/trajectory.partial.json` (25 files,
  pinned by a digest). `actions.json` of either run carries object names and is never opened.

## 3. Pre-contract development (disclosed)

Before this commit only accepted code, reports and records were read; nothing was probed, replayed or rendered:
- Read: `fov3d.control.{controller02, integrated}`, the Classroom Controller-01 / Controller-02 adapters and their
  reports; the NS1a / NS1b reports and tools; the NS1c contract, report, tools and run records (the step decisions, the
  recorded probes and fusions of steps 0–4, the NS1c manifest, which verifies intact); the structure of the accepted
  Controller-02 replay output and of the Controller-01 trajectories (name-free: `events.json`, `final-residue.json`,
  `trajectory.partial.json`; `actions.json` carries names).
- From the NS1c records (MEASURED by NS1c, re-used here only as expectations): steps 0–3 executed 172's FSG6f proposals
  (−5, −10), (−5, −15), (−5, −20), (0, −20), each admitted by the gate; 172's map 21,243 → 28,038 → 36,575 → 45,267 →
  45,267; after step 3, FSG6f `no_frontier` and Cyclopean `epistemic_fixation` local (+6.2°, −1.2°) → H0
  (−163.040°, +31.040°); NS1c's initial probes carry a proposal for all ten coherent entities (FSG6f for 123 and 172,
  Cyclopean for the other eight).

## 4. The NS1c review decision (pointer)

NS1c is not accepted and not merged (`docs/north-star/ns1c-review-decision.md` on `main`). NS1c2 neither modifies nor
merges the NS1c branch; it reads the NS1c run as a measured replay source only. Its 172 → 123 switch is never called an
accepted natural Controller-02 scene switch.

## 5. Historical known answer (ACCEPTED HISTORICAL REFERENCE; pinned, not re-run)

From the accepted reports (literal pins): Controller-01 with the ideal matcher — 25 localized objects, 141 observations
(25 seed / 50 FSG6f / 66 Cyclopean), 26 switches (24 + 2 annotated natural reactivations), 27 bouts, 2 natural
reactivations, 1,059,349 final active-map surfels, 28,801 of 29,288 reachable samples within 12 mm (micro coverage
0.9833720295001366), per-object coverage 1.0 for 16 of 25, terminal 24 QUIET + 1 watchdog-blocked (210). Controller-02 —
141 / 141 ordinary actions replayed, the 2 natural reactivations preserved, one `deferred` event (210, global step 101,
24 fixations, `ordinary_budget`), RESIDUE at step 141 with deferred [210], one gate decision (210, rejected,
`no_novel_serviceable_support`), 210 `FINALIZED:final_probe_rejected`, 0 final residue observations. The 575-s replay is
not re-run. The coverage numbers come from the accepted evaluation and are pinned as literals; evaluation truth is never
opened.

## 6. Authoritative NORMAL / RESIDUE semantics and the phase adapter

The authoritative semantics are `fov3d/control/controller02.py` (accepted, unchanged, pinned). NS1c2 uses **Option A —
a thin resumable adapter** (`tools/north_star/ns1c2_phase.py`), because the accepted `run_controller02` begins from
SEEDABLE seeds, while NS1c2 resumes an already initialized scene and runs one stage per process. The adapter uses
directly: `ObjectStatus`, `Disposition`, `ScenePhase`, `schedule_normal`, `FinalProbeDecision`, the defer / finalize
reason constants, and `integrated.ProbeResult`, `Observe`, `can_act`, `choose_action`. Its state transitions mirror
`run_controller02` statement by statement:

- **NORMAL.** `local = ACTIONABLE if can_act(probe) else QUIET` from the accepted ProbeResult only (sources `fsg6f` and
  `cyclopean_epistemic`). An ACTIONABLE NORMAL object whose own fixations ≥ budget becomes `ACTIONABLE /
  DEFERRED:ordinary_budget` (not BLOCKED, QUIET or FINALIZED). `schedule_normal(current, statuses)` retains / switches over
  NORMAL-serviceable objects. The gate is never called.
- **RESIDUE.** Entered only when `schedule_normal` returns None. DEFERRED objects in ascending id: QUIET →
  `FINALIZED:quiet_before_final_probe` without a gate call; ACTIONABLE → the UNCHANGED current ProbeResult goes to
  `final_look_gate_v1`; rejected → `FINALIZED:final_probe_rejected`; admitted → that exact proposal executed once,
  `FINALIZED:final_probe_executed`; a final observation may return the scene to NORMAL.
- **CLOSED.** Only when no NORMAL object needs service and no DEFERRED object remains (not expected in NS1c2; never
  claimed as a scene result).
- Revision / cache, `quiet`, `natural_reactivation`, `deferred`, `local_state_change`, `finalized` and
  `final_probe_decision` events, bouts and the `natural_reactivation` scheduler reason: exactly as `run_controller02`.
  There is no `reactivate()` operation.

The adapter state (phase, current, bout, step, fixations, dispositions, recorded statuses, probe cache by revision, last
probes, quiet bookkeeping, reactivation set, residue records) is serialized in every scene state. `fov3d/control/
controller02.py` and `fov3d/control/integrated.py` are not edited (pinned); the integration adapts to the accepted
controller.

**Gate guard (load-bearing).** Every NS1c2 stage that runs policy code runs inside a guard that substitutes
`final_look_gate_v1` in every loaded copy of the accepted Classroom Controller-02 module by a wrapper that records each
call with the adapter phase and raises unless the phase is RESIDUE. NS1c2's NORMAL probe calls only
`controller01.probe_local_policy` under the accepted NS1b frame adapter (never `ns1b_core.probe`, which gates). The
adapter's P3 substitution (`predicted_calibration`, used only by the gate) must record 0 calls in every NORMAL probe.

## 7. Known-answer semantic gates (stages `synthetic`, `known-answer`; before any Classroom data is probed)

`synthetic` (analytic only):
- **B4a NORMAL classification.** FSG6f proposal → ACTIONABLE; Cyclopean proposal → ACTIONABLE; no action → QUIET; gate
  calls 0. Mutants that gate a Cyclopean or an FSG6f NORMAL proposal (calling the real accepted gate) are refused by the
  guard and would classify QUIET.
- **B4b scheduler.** The accepted `schedule_normal`: current NORMAL ACTIONABLE → retain; current QUIET + later
  ACTIONABLE → switch forward; wrap to the lowest serviceable id; DEFERRED / FINALIZED not serviceable; none → None.
- **B4c budget.** 23 fixations ACTIONABLE → NORMAL; 24 → `ACTIONABLE/DEFERRED:ordinary_budget` (not BLOCKED / QUIET /
  FINALIZED); QUIET at 24 stays NORMAL QUIET.
- **B4d RESIDUE only.** With any NORMAL-serviceable object the gate is never called; a direct gate call while the phase
  is NORMAL is refused by the guard; one DEFERRED ACTIONABLE object after NORMAL exhaustion → exactly one gate call.
- **Differential equivalence (Option A proof).** On synthetic scenes (FSG6f and Cyclopean proposals, cross-object
  evidence for natural reactivation, deferral, deferred-QUIET finalization, rejected and admitted final looks, a final
  look that reactivates NORMAL work, a second residue pass), the adapter driven from the seeds reproduces the accepted
  `run_controller02` exactly (actions, events, phases, residue decisions, final statuses, fixations, probe calls / cache
  hits, terminal). The adapter resumed from a JSON round trip of its own state at intermediate steps reproduces the same
  suffix.

`known-answer` (accepted saved data):
- **B4e historical Controller-02 trace.** The adapter is driven over the accepted Controller-02 history from name-free
  sources only (the 25 Controller-01 trajectories for the 141 actions; Controller-02 `events.json` for the service-state
  timeline; `final-residue.json` for the gate verdict): the probe stub returns ACTIONABLE with the object's next executed
  action, or QUIET, by the recorded events; the gate stub returns the recorded verdict. Required: the 141 selected
  actions equal the accepted ones (target, source, gaze ≤ 1e-9°, local step); the 56 events equal `events.json`
  (event, object, global step, trigger); 26 switches incl. 2 `natural_reactivation`, 27 bouts; the phases equal
  `final-residue.json`; 0 gate calls in NORMAL (including all 66 Cyclopean and 50 FSG6f actions); 210 DEFERRED at step 101
  with 24 fixations; exactly one gate call, in RESIDUE, on 210's unchanged FSG6f proposal (7.6°, 18.2°); 210
  `FINALIZED:final_probe_rejected`; no final residue observation.
- **Residue-gate wiring known answer.** NS1c2's production residue path (context reconstruction, unchanged-proposal
  check, the accepted gate under the frame adapter with the North-Star sensor) is run in a one-entity harness scene: 172
  at its accepted NS1b post-action state, own fixations set to the budget, so it is DEFERRED, `schedule_normal` returns
  None and the phase is RESIDUE. The verdict must equal the accepted NS1b post-action gate record (admissible,
  `novel_support_in_predicted_cores`, novel serviceable support 22). Nothing is executed. This harness is not part of
  the scene loop and is reported separately from the loop's gate accounting.

## 8. The fixed physical head (load-bearing, unchanged from NS1b / NS1c)

The physical binocular head DOES NOT MOVE. Canonical H0: +X right, +Y up, −Z forward, metres. Every persistent map stays
in H0; every eye centre is (∓0.0315, 0, 0) m in H0; every acquisition uses the fixed AB1a head pose (`9960c86e…`); every
physical projection uses the real H0 calibration. A policy chart exists only for controller policy geometry. No
chart-local binocular head ("fake local head"); no head motion.

## 9. COHERENT_SEED_SET — the same frozen rule

    eligible(i)  iff  initialized == true  AND  contributing_patches == 1          -> COHERENT_SEED_SET
    deferred(i)  iff  initialized == true  AND  contributing_patches  > 1          -> DEFERRED_AMBIGUOUS_ORACLE_IDENTITY

Derived from the frozen NS1a `seeds/seed-set.json` (fields `temporary_entity_id`, `initialized`, `contributing_patches`,
plus `initialized_at_rank`, `final_surfels`); names / catalog refused. Expected, compared only after derivation (a
difference is a STOP): {9, 12, 123, 129, 172, 202, 204, 212, 230, 231}; deferred {10, 110, 178}, which never enter a
status, scheduler input, target or action.

## 10. Charts

One FIXED policy chart per coherent entity, the accepted NS1b construction (`ns1b_chart.chart_basis`) at the entity's
NS1a initialization gaze; never recentered; C_172 bitwise the accepted NS1b chart; the NS1b chart requirements per chart.

## 11. Initial contexts and maps (stage `contexts`; no rerender)

Exactly as NS1c (contract section 9 there): 172 = the accepted NS1b post-action context and map, imported exactly (2 own
looks; visited (0, 0), (0, −5); current local gaze (0, −5); 21,243 surfels); every other coherent entity = its frozen NS1a
map and saved NS1a initialization look through the accepted Classroom matcher (controller observation state only); own
looks 1; visited [(0, 0)]. Own looks include the initialization look. Two representations are retained, not redesigned:
the North-Star persistent metric map (PERFECT → spherical → H0) and the controller observation state (the accepted
Classroom controller-time oracle matcher).

## 12. Initial service table under NORMAL semantics (stage `initial-probe`; once; before any replay or render)

For every coherent entity in ascending id, exactly once: the accepted `controller01.probe_local_policy` (FSG6f, then
Cyclopean if FSG6f stops) under its chart, **no gate**. Recorded (B9): id, map size, own looks, FSG6f status, Cyclopean
status, proposal source, local proposal, H0 proposal, NORMAL local state, disposition. The table is derived, not
hard-coded; the NS1c diagnostic expectation (all ten ACTIONABLE: FSG6f for 123 and 172, Cyclopean for the others) is
compared afterwards and any difference is reported. `untraceable_final_support` has no role: the gate is not invoked.
- **NS1b reproduction (HARD STOP).** 172's probe must reproduce the accepted NS1b post-action probe exactly in its policy
  part (decisions, summary, state, proposal; tolerance 0): ACTIONABLE, `fsg6f`, local (−5°, −10°), H0 (−147.585°,
  +37.246°).
- **Chart covariance.** Each probe is repeated on its context rigidly rotated about the physical baseline by
  β ∈ {+37°, −61°} (the NS1b / NS1c invariance, accepted float-tie and voxel-boundary rules). A difference is a STOP.
- **NS1c policy equality.** Each probe's policy part must equal NS1c's recorded initial probe (tolerance 0).

The adapter is then resumed: phase NORMAL; current 172; attention bout 1 (172's continuing NS1b bout); global step 0;
fixations = own looks; every entity initialized; dispositions NORMAL; recorded statuses = this table.

## 13. The NS1c prefix — read-only measured replay (command `prefix`; global steps 0–3; NO Blender)

NS1c's first four post-NS1b actions on 172 were accepted ordinary FSG6f proposals selected before the semantic difference
could matter. They are reused, not re-rendered. For each prefix step k = 0, 1, 2, 3, as separate stages
(`schedule`, `replay`, `fuse`, `update`), each under the accepted `NoProcessGuard` (no process can start inside them):

1. `schedule`: the adapter's corrected NORMAL decision must select exactly NS1c step k: target 172, scheduler `retain`,
   source `fsg6f`, the same local gaze and H0 gaze, and planned-calibration bytes equal to NS1c's
   `plan/planned-calibration.json`.
2. `replay`: NS1c step k's observation, PERFECT correspondence, spherical geometry and local identity are verified in
   place against NS1c's own freezes, NS1c's manifest and NS1c2's literal pins (hashes, 4096 spp, seeds, settings,
   catalog seal, calibration bytes equal to NS1c2's planned calibration). Nothing is copied or re-rendered.
3. `fuse`: NS1c2 recomputes the target-only 12-mm H0 fusion from NS1c's frozen geometry and identity into its own map
   (patch id `ns1c_step_0k`, NS1c's measurement); the fusion record and the fused map must equal NS1c's bitwise.
4. `update`: NS1c2 recomputes the controller observation state (accepted matcher on NS1c's saved look), the context
   update (Controller-01 `observe` order) and the ungated re-probe of 172; controller state, evidence, history / visited
   / own looks / revision and the probe's policy part must equal NS1c's step-k records; then the adapter refresh (cache
   by revision for the untouched entities).

Any difference in any prefix step is a STOP (Outcome 4): the saved prefix is not used further, and the semantic
correction is not assumed to be late. The prefix stages never run `preflight` / `acquire` and never write an
`observation/` tree.

## 14. The first true divergence (stage `divergence`; frozen BEFORE any new render)

From the reconstructed post-step-3 state (expected: 172 with 6 own looks and 45,267 surfels), the record freezes: 172's
ungated post-step-3 probe (FSG6f result; Cyclopean proposal source, local gaze, mapped H0 gaze), map, revision, own
looks, chart, NORMAL local state, disposition, the gate-call count (0) and the `schedule_normal` result. Expected:
FSG6f `no_frontier`, Cyclopean `epistemic_fixation` → **ACTIONABLE**, schedule `retain 172`. It records the NS1c
comparison at the same state (NS1c: gate REJECT `untraceable_final_support` → QUIET → switch → 123; NS1c2: gate NOT
CALLED → ACTIONABLE → retain 172). The FSG6f result and the Cyclopean proposal must equal NS1c's recorded step-3 probe.

STOP (no render) if the probe carries no action, if the scheduler would switch before executing it, or if the probe
differs from NS1c's.

The derived safety cap, frozen here and never increased after results:

    MAX_NEW_POST_DIVERGENCE_ACTIONS = (ordinary_budget − own_looks_172) + 1      expected (24 − 6) + 1 = 19

A different derived number is a STOP.

## 15. The NORMAL loop (command `loop`; global steps k ≥ 4)

Per step, as separate stages (each once, under the accepted `OpenGuard`): `schedule` (the adapter's decision:
`schedule_normal` over the current statuses; DEFERRED objects excluded; if None, the RESIDUE procedure of section 17),
`preflight`, `acquire`, `freeze-observation`, `perfect-correspondence`, `freeze-correspondence`, `spherical-geometry`,
`freeze-geometry`, `local-oracle-segmentation`, `fuse`, `update` (target context update, fresh probe of every entity whose
revision changed, cache for the rest, the adapter refresh with its deferral rule). A retain or switch executes the
selected entity's UNCHANGED current proposal. NORMAL final-gate calls must be exactly 0.

## 16. The ordinary budget

`fov3d.experiments.classroom_oracle.controller02.BUDGET` (= `controller01.WATCHDOG`, live, expected 24; pinned). It is
an ordinary-service budget, not a watchdog. 172 may receive at most 24 − 6 = 18 further ordinary looks; at 24 own
fixations an ACTIONABLE 172 becomes `ACTIONABLE/DEFERRED:ordinary_budget`, leaves NORMAL service, is not gated while
NORMAL work remains, and `schedule_normal` switches to another NORMAL-serviceable entity.

## 17. RESIDUE (implemented, even if not reached)

Entered only when `schedule_normal` returns None. For every DEFERRED entity in ascending id, the current ProbeResult
(revision cache): QUIET → `FINALIZED:quiet_before_final_probe` (no gate call); ACTIONABLE → the residue gate: the entity's
context is rebuilt, the probe is recomputed and must equal the cached one exactly, and the accepted
`final_look_gate_v1` receives the UNCHANGED cached proposal (frame adapter, North-Star sensor for P3). Rejected →
`FINALIZED:final_probe_rejected`; admitted → that exact proposal is executed once as the step's action
(`FINALIZED:final_probe_executed`). One decision per deferred entity; the guard makes a gate call outside RESIDUE
impossible.

## 18. Measurement, fusion and frozen simplifications

Each new action: one fixed-head 4096-spp binocular pair at the mapped H0 gaze (Classroom `classroom_eye.blend`
`dca66a32…`, 640 × 640 raw, 256 × 256 nominal core, 12° core, IPD 0.063 m, vergence 2.10 m, OPTIX, seeds L 2111 /
R 2112, denoising OFF, adaptive OFF, BOX 1.0, `baseline_projected`; calibration byte-identical to the planned one;
settings equal to the accepted AB1d2 4096-spp readback; 4096 in both EXR headers; sealed catalog seal = NS1a's, never
opened); PERFECT / oracle raw correspondence (accepted AB1b) → freeze → accepted spherical geometry in H0 (truth-free)
→ freeze → local ORACLE SEGMENTATION AID (`instance_L` only) → target-only fusion (`ns1b_core.fuse_h0`, 12 mm / 12 mm,
one exact replay; fewer than 100 target points → retained, not fused) → the controller observation state (accepted
Classroom matcher). Patch ids: `ns1c2_step_NN` for new steps. A render projected above 600 s is a STOP.

Frozen simplifications, recorded and not redesigned: **target-only persistent fusion** (untouched entities keep their
revision; reactivation remains possible in the machinery but is not expected); **rank-1 controller-state zero support**
(the planar controller-state matcher has 0 target support at the rank-1 initialization gaze for 9, 12, 204, 230, 231;
their Cyclopean ProbeResults may still make them ACTIONABLE; for every executed action both the North-Star raw-core
target metric support and the controller-state target support are recorded; a failure caused by it is reported, not
fixed).

## 19. Stop, cap and time budget

- **Canonical stop.** Immediately after the FIRST successfully executed NORMAL observation whose target != 172 (through
  the fusion stage: FUSED or retained by the 100-point precondition): its `update` performs the one read-only post-action
  probe of the new target (not executed), recomputes the scene status table once, writes the final scene state and
  freezes it. STOP. Any later `schedule` is refused: no second action on the new target, no third entity, no coherent-set
  closure.
- **Cap.** At most 19 new post-divergence physical actions (section 14). Attending beyond the cap is `CapReached`
  (Outcome 4, STOP).
- **Time.** PROPOSED ≈ 45 s per new step (NS1c measured 41–46 s); worst case 19 steps ≈ 15 min. After each step the
  driver projects elapsed + (cap − executed) × mean step seconds; above 1800 s it STOPS before the next step (no
  quality or policy change).

## 20. Outcome semantics

- **Outcome 1 — natural quiet switch.** Under NORMAL semantics 172's ProbeResult carries no action before the budget →
  QUIET → `schedule_normal` switches to another NORMAL-serviceable entity; one ordinary action executes there.
- **Outcome 2 — ordinary-budget switch.** 172 stays ACTIONABLE to 24 fixations → `DEFERRED:ordinary_budget` (no gate
  yet) → another NORMAL ACTIONABLE entity is selected and one ordinary action executes there.
- **Outcome 3 — NORMAL scene does not spread.** No other NORMAL-serviceable entity when 172 leaves NORMAL, or the
  corrected probes do not yield the expected actionable set, or ordinary work exhausts first; RESIDUE is entered and
  characterized correctly if required; no scene-spreading claim.
- **Outcome 4 — semantic / replay failure.** The prefix does not reproduce; a gate call in NORMAL; `schedule_normal`
  behavior differs; a phase invariant fails; a physical / coordinate / measurement invariant fails; the cap; the time
  budget. STOP, no tuning.

## 21. NS1c comparative diagnostic (headline)

At the exact post-step-3 state: NS1c — FSG6f `no_frontier`; Cyclopean proposal; final gate REJECT
`untraceable_final_support`; QUIET; SWITCH → 123. NS1c2 — FSG6f the same; Cyclopean the same; final gate NOT CALLED;
ACTIONABLE; RETAIN → 172. This is a headline table in the report and a headline figure.

## 22. Scene state record

`scene/state-initial.json` and `scene/state-after-step-NN.json` record, per coherent entity: id, rank, chart id / hash,
looks, visited, current local gaze, own looks, map (path, hash, surfels), evidence, probe record (path, hash, revision,
fresh / cached), NORMAL local state, disposition / reason, label, proposal (source, local, H0); and globally: phase,
current, previous, attention bout, step, scheduler decision and reason, executed actions (prefix + new), new actions,
budget, cap, gate-guard calls by phase, events, the serialized adapter state, the deferred identities (separately),
stop.

## 23. Truth boundary and process

Controller-time oracle aids are exactly the concept-demo aids (PERFECT correspondence for the measurement; the Classroom
matcher for the controller observation state; local Object Index identity). No Position beyond those services, no future
visibility, no global geometry, no catalog or names. Every canonical stage runs once (per step for step stages) from one
clean pushed implementation commit, under `OpenGuard`; truth is read only by `contexts`, `known-answer` (the NS1b looks for
the harness context), `perfect-correspondence`, `freeze-observation`, `local-oracle-segmentation` (`instance_L`),
`update` and the prefix `update` / `replay` (NS1c's saved looks). Production code never uses `integrated.schedule`,
`run_control_loop`, `ns1b_core.probe`, natural stereo, SGBM or head motion; `final_look_gate_v1` is referenced only by the
residue gate; `schedule_normal` is the only scheduler; no scene-closure marker is emitted.

## 24. Checker (`tools/north_star/check_ns1c2.py`)

Own literal pins; independent recomputation wherever an independent formula exists; every load-bearing rule fail-capable.
Families: PROVENANCE (repo, base, NS1b / NS1a acceptance, NS1c diagnostic pins, Controller-01 / 02 pins, contract first
and unchanged); NS1c DECISION (no NS1c ACCEPTED marker in the tree; the NS1c report head is not an ancestor of `main` or
of the checked tree); ELIGIBILITY (own rule; 10 / 110 / 178 absent everywhere); CHARTS / SENSOR (own construction; fixed
head; no fake local sensor; P3 = real sensor); INITIAL PROBES (once, ungated, recomputed, own rotation, NS1b
reproduction, NS1c policy equality); NORMAL PHASE (own classification from the probe alone; Cyclopean counts; the
accepted `schedule_normal` recomputed on every decision; an independent re-drive of the adapter over the recorded probes
reproducing every decision, event and disposition); GATE ACCOUNTING (guard records of every stage: NORMAL calls 0; P3 0 in
every NORMAL probe; residue calls only with phase RESIDUE); BUDGET / DEFER (own fixations; deferral exactly at 24; never
BLOCKED; not gated while NORMAL work remains); RESIDUE (the synthetic differential and the historical Controller-02
trace re-run by the checker; the residue harness verdict); PREFIX (exactly four replayed steps; no Blender; NS1c hashes;
decisions, maps, states, evidence, probes equal NS1c's); DIVERGENCE (the record, frozen before the first acquire; equal
to NS1c's policy result; ACTIONABLE; retain; cap 19); ACTIONS (world gazes, planned = executed calibration bytes, one
4096-spp pair per new step, no re-render); MEASUREMENT (own oracle, own triangulation, identity after the geometry freeze);
FUSION (selected target only, H0, 12 / 12, own association, idempotent, untouched maps unchanged); UPDATE / REACTIVATION
(controller state, evidence, re-probes recomputed; untouched entities re-probed from scratch equal); STOP (exactly the
first executed target != 172; one post-action probe; nothing after); PROCESS (stage order, one commit, code scan);
TRUTH BOUNDARY; TERMINOLOGY (no scene-closure claim; NS1c never called accepted; its switch never called natural
Controller-02 evidence); VISUALS (byte-identical regeneration; NORMAL / RESIDUE explicit; gate markers only in RESIDUE;
the divergence shown); MANIFEST and declared changes.

## 25. Corruption suite (`tools/north_star/check_ns1c2_corruptions.py`)

From a passing baseline after an unmodified-mirror null probe; mirrors with large arrays symlinked and unlinked before
writing; the mirror manifest regenerated; RUN and VIS hashed before and after. At least: SEMANTICS (gate a Cyclopean
NORMAL proposal; gate an FSG6f NORMAL proposal; a gate call while NORMAL; a Cyclopean proposal classified QUIET; a switch
while the current entity is NORMAL ACTIONABLE); BUDGET (budget changed; BLOCKED instead of DEFERRED; gated immediately at
the budget while NORMAL work remains); RESIDUE (residue while a NORMAL-serviceable object exists; deferred order changed;
proposal altered; two final looks for one object); PREFIX (one NS1c action altered; one observation hash altered; Blender
during the prefix; only three prefix steps; NS1c's wrong QUIET state imported); TARGET SET (10 / 110 / 178 included;
names used); CHART / SENSOR (dynamic recenter; fake local baseline; head moved); MEASUREMENT (SGBM-like correspondence;
planar persistent geometry; Position leak); FUSION (cross-target fusion; radius changed; fused in the chart); STOP (a
second action on the new target; a third entity; a scene-closure claim); VISUAL (phase hidden; a gate marker in NORMAL;
an oracle label removed). Corruptions that do not apply to the executed trajectory are recorded NOT APPLICABLE with the
reason, never counted as caught.

## 26. Scientific visuals (Visual Language 1; deterministic; regenerated byte-identically by the checker)

`VIS/overview.png`: **A** historical known answer (ACCEPTED HISTORICAL REFERENCE, not an NS1c2 measurement); **B** the
semantic bug, side by side at the divergence state (NS1c: gate wrongly in NORMAL → rejected → QUIET → switch; NS1c2: no
gate in NORMAL → ACTIONABLE → retain); **C** the corrected 172 continuation (local gaze, H0 gaze, source, map growth per
action); **D** the first valid scene switch (172 → scheduler reason → second target; source, local / H0 gaze; before /
after map), or what happened instead; **E** phase state (NORMAL, DEFERRED if encountered, RESIDUE only if encountered;
gate markers only inside RESIDUE). Supporting: `ns1c-vs-ns1c2-divergence.png`; `controller-phase-timeline.png` (rows
entities, columns actions; NORMAL ACTIONABLE / NORMAL QUIET / DEFERRED / FINALIZED; current target; retain / switch;
action source); `multi-entity-growth-3d.png` (if a switch occurs); `controller-vs-northstar-support.png` (descriptive).
Truth badges, frame labels (POLICY CHART vs CANONICAL H0), the fixed-head statement, non-color cues,
`visuals-manifest.json`.

## 27. Commands, order and cost

    RUN=/home/lvelho/rd/f3d-vision/previews/north-star/ns1c2-controller02-phase-semantics
    VIS=/home/lvelho/rd/f3d-vision/visuals/north-star/ns1c2-controller02-phase-semantics
    .venv/bin/python tools/north_star/ns1c2_run.py source         --run $RUN
    .venv/bin/python tools/north_star/ns1c2_run.py synthetic      --run $RUN
    .venv/bin/python tools/north_star/ns1c2_run.py known-answer   --run $RUN
    .venv/bin/python tools/north_star/ns1c2_run.py eligibility    --run $RUN
    .venv/bin/python tools/north_star/ns1c2_run.py charts         --run $RUN
    .venv/bin/python tools/north_star/ns1c2_run.py contexts       --run $RUN
    .venv/bin/python tools/north_star/ns1c2_run.py initial-probe  --run $RUN   # ungated; no render
    .venv/bin/python tools/north_star/ns1c2_run.py prefix         --run $RUN   # steps 0-3: schedule, replay, fuse, update
    .venv/bin/python tools/north_star/ns1c2_run.py divergence     --run $RUN   # frozen before any render
    .venv/bin/python tools/north_star/ns1c2_run.py loop           --run $RUN   # steps >= 4, until the stop / cap / budget
    .venv/bin/python tools/north_star/ns1c2_run.py visualize      --run $RUN --visuals $VIS
    .venv/bin/python tools/north_star/check_ns1c2.py --run $RUN --visuals $VIS --corruptions --write-summary

Cost classes (PROPOSED): `initial-probe` interactive-to-batch; `prefix` batch (four replayed steps, no render);
`loop` batch, worst case ≈ 15 min (section 19); the checker with corruptions batch; every other stage interactive. No
overnight task, no parameter sweep.

## 28. Permitted fix scope

- **Before the canonical run:** implementation defects in the NS1c2 tools, without changing sections 5–21 or a declared
  tolerance. Development uses analytic fixtures, the accepted known answers (section 7) and scratch development runs
  (never the canonical RUN) whose scene is the rehearsal set {172 (NS1b import), 10, 110, 178}, the deferred multi-part ids
  acting as non-coherent rehearsal entities (NS1c's accepted practice); the rehearsal replays the NS1c prefix of 172 (a
  reproduction of NS1c's measured records) and renders only low-spp factory-startup rehearsal scenes, never Classroom.
  No coherent entity other than 172 is probed in development.
- **After the canonical run starts:** (a) a stage that fails with an implementation defect BEFORE writing any output may
  be repaired minimally and then run for its first and only time, if sections 5–21 are unchanged (recorded as an
  incident); (b) presentation-only figure fixes; (c) a checker or corruption-suite defect that false-alarms on correct
  data, only if the fix does not weaken the check (recorded).
- Anything else — a re-render, a re-probe outside the rules, a different target, a chart change, an adapter, policy,
  gate, scheduler, budget, oracle, geometry, identity or fusion change, an edit of `fov3d/` — is a STOP for Luiz and
  Chat.

## 29. Stop conditions

STOP and report if: a source / NS1a / NS1b / NS1c / Controller pin fails; `synthetic` or `known-answer` fails; the derived
coherent set differs; a chart fails; the 172 import is not exact; the NS1b policy reproduction fails (HARD STOP); a
rotation invariance fails; the accepted code refuses an entity; any prefix step differs from NS1c; the divergence probe
carries no action or the scheduler would switch first; the derived cap differs from 19; the gate is called in NORMAL;
`preflight` fails; a render projects above 600 s; the time projection exceeds 1800 s; a guard records a violation in a
canonical stage; a stage would run twice; the cap is reached; a canonical check fails for a reason other than a checker
defect.

## 30. Report and stop

`docs/north-star/ns1c2-controller02-phase-semantics-report.md`, status REVIEW PENDING, marker
`NORTH_STAR1C2_CONTROLLER02_PHASE_SEMANTICS_COMPLETE`, no ACCEPTED marker. It records the 28 items of the mandate's B25
(provenance; the NS1c review decision; the historical known answer; the authoritative semantics; the eligible set; the
initial state; the prefix replay proof; the divergence state; the NS1c vs NS1c2 comparison; the corrected initial service
table; the action trace with every proposal source; NORMAL gate calls = 0; DEFERRED / RESIDUE events if any; the first
switch and second-target action; per-action H0 fusion; controller-state vs North-Star support; the final frozen state;
the Outcome reading; checks; corruptions; visuals and hashes; incidents; what is and is NOT established) and ends with the
unresolved decision: READY TO RELEASE THE CORRECT MULTI-ENTITY NORTH-STAR LOOP? Then STOP: no acceptance, no merge of
NS1c2 or NS1c, no release of the full loop, no second action on the new target, no third target; FSG6f, Cyclopean, the
scheduler, the budget, the gate, rank-1 support, fusion scope, identities, background, stereo and the head unchanged.

## 31. What NS1c2 may and may not establish

May establish: whether, from the accepted NS1b state, the accepted Controller-02 NORMAL / RESIDUE semantics (gate in
RESIDUE only) with the unchanged policy, charts, budget and fixed head produce a first scene-level switch to another
coherent seed and one valid controller-selected PERFECT observation there, and by which mechanism (natural quiet or
ordinary-budget deferral).

May NOT establish: full Classroom closure or coherent-subset quiescence; anything about 10 / 110 / 178; natural
correspondence or identity; that cross-target fusion is unnecessary; that the rank-1 controller observation state is
adequate; head motion, real cameras or other scenes.
