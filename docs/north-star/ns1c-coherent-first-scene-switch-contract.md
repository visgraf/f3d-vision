# North Star-1c — Coherent Multi-Entity Control — First Scene Switch — contract

**Status: CONTRACT (committed before any NS1c implementation commit, before any NS1c controller probe and before any
NS1c render).** Completion marker (written only by the report): `NORTH_STAR1C_COHERENT_FIRST_SCENE_SWITCH_COMPLETE`.
No ACCEPTED marker is written by Claude Code.

Decision context (recorded on `main` at `2815bf1`, "North Star after NS1b"): NS1b is accepted as Outcome 1
(`NORTH_STAR1B_RECENTERED_CONTROLLER_HANDOFF_ACCEPTED`, acceptance `2553551`); the bootstrap-to-controller bridge is
established. POLICY CHART C IS NOT PHYSICAL HEAD MOTION. NS1c continues from the ACTUAL accepted NS1b state. The
multi-part oracle identities 10, 110 and 178 remain DEFERRED.

## 1. One causal question

> Starting from the accepted NS1b state, can the accepted deterministic scene scheduler and per-entity recentered local
> controllers continue servicing the current entity and then AUTONOMOUSLY SWITCH to another coherent RGB-bootstrap seed
> and execute one valid controller-selected observation there?

It tests LOCAL ACTIVE CONTROL + SCENE-LEVEL ATTENTION SWITCHING. It does not test full Classroom closure, every entity,
multi-part identity repair, a background representation, natural stereo, head motion or semantic reasoning. The chain,
and nothing beyond it:

    accepted NS1b post-action state of entity 172     (imported exactly; section 9)
    + frozen NS1a seed set                             (read, never recomputed)
      -> COHERENT_SEED_SET, derived by rule            (section 5)
      -> one FIXED policy chart per coherent entity    (section 7; the accepted NS1b construction)
      -> initial controller contexts, no rerender      (section 9)
      -> ONE initial probe of every coherent entity, before any render; 172 reproduces NS1b   (section 11)
      -> loop over global steps k = 0, 1, ...          (sections 12-17)
           service summaries -> accepted integrated.schedule -> the selected entity's frozen admissible proposal
           -> local C_i -> H0 -> ONE fixed-head 4096-spp observation -> PERFECT correspondence -> spherical geometry
           -> local oracle id -> target-only 12-mm H0 fusion -> context update -> re-probe
      -> canonical STOP after the FIRST successful action whose target != 172   (section 18)

## 2. Provenance and branch

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (the legacy `fov-3d-vision` is never used) |
| base (accepted `main`: NS1b accepted + post-NS1b roadmap) | `2815bf166689d68cec421fb119635cafaa718d9a` |
| NS1b acceptance | `255355108863022f931574dae4b2df8cdd2a772e` (`NORTH_STAR1B_RECENTERED_CONTROLLER_HANDOFF_ACCEPTED`) |
| NS1a acceptance | `37c7e026f2ab514be392cd845d390fab2a2d86fc` (`NORTH_STAR1A_PERFECT_BOOTSTRAP_ROUND_ACCEPTED`) |
| branch | `north-star/ns1c-coherent-first-scene-switch`, from the base, in an isolated worktree |
| run (`RUN`, machine evidence) | `/home/lvelho/rd/f3d-vision/previews/north-star/ns1c-coherent-first-scene-switch/` |
| visuals (`VIS`, persistent) | `/home/lvelho/rd/f3d-vision/visuals/north-star/ns1c-coherent-first-scene-switch/` |

The implementation commit writes this contract's commit SHA into `ns1c_spec.CONTRACT_COMMIT` and the checker's literal;
the checker requires this file to be unchanged from that commit to the checked tree.

Frozen inputs (sha256; a mismatch is a STOP):
- NS1a run (`previews/north-star/ns1a-perfect-bootstrap-round/`): the freezes and seed handoff pinned by NS1b (observation
  freeze `46f0a22e…`, geometry freeze `7b0ae64d…`, seed-set freeze `4ee36a1a…`, `seeds/seed-set.json` `e2ff1ba3…`,
  `seeds/entity-maps.npz` `621d8902…`, `source/nb1c-gaze-list.json` `785d02a7…`, catalog seal `a0849b21…`).
- NS1b run (`previews/north-star/ns1b-recentered-controller-handoff/`, the accepted canonical run): `manifest.json`
  `e859fa61…`, `check-summary.json` `146438bd…`, `fusion/fused-target-map.npz` `bf831ad5…`, `post/post-action-probe.json`
  `2918e146…`, `post/evidence.npz` `a9679163…`, `post/controller-state.npz` `337c0705…`, `context/controller-state.npz`
  `ceebc725…`, `observation/acquisition/calibration.json` `a4b2ae67…`, `freeze/observation-freeze.json` `0fbd0e8d…`,
  `chart/policy-chart.json` `8adefe86…`. Every file pinned is listed in full in `ns1c_spec`.

## 3. Pre-contract development (disclosed)

Before this commit only accepted code, reports and records were read, and one calibration-only computation was made
(no scene data, no controller, no probe, no render):

- Read: the NS1a seed-set document (entity ids, `initialized`, `initialized_at_rank`, `contributing_patches`,
  `final_surfels`); the accepted NS1b report and run records (the post-action probe record and the hashes above); the
  accepted `fov3d.control.integrated`, `controller01`, `controller02` and NS1b tools.
- Calibration-only (`ns1b_chart.chart_basis` / `chart_checks`, no scene data): rank-1 gaze (+76.75°, +7.75°):
  b·g0 = +0.964488, ‖b⊥‖ = 0.264126 (not singular), orthonormality 2.2e-16, det − 1 = 0, seed → local (−4.8e-15°, 0°),
  baseline in C (0.2641, 0, −0.9645), y_C·Y = +0.860; rank-6 gaze: identical to the accepted NS1b chart.

No coherent entity was probed, no controller ran on NS1a or NS1b data, nothing was rendered.

## 4. The fixed physical head (load-bearing, unchanged from NS1b)

The physical binocular head DOES NOT MOVE. Canonical H0: +X right, +Y up, −Z forward, metres. Every persistent map stays
in H0; every eye centre is (∓0.0315, 0, 0) m in H0; every acquisition uses the fixed AB1a head pose (`9960c86e…`); every
physical projection uses the real H0 calibration; every predicted Controller-02 observability uses the real physical
sensor at the mapped H0 gaze. A policy chart exists only for controller policy geometry. No calibration with eye
centres on the axes of a chart is ever constructed ("fake local head"); no chart-local binocular head; no head motion.

## 5. COHERENT_SEED_SET — derived, not hard-coded

Input: the frozen NS1a `seeds/seed-set.json` (verified under the seed freeze). Fields read: `temporary_entity_id`,
`initialized`, `contributing_patches` (eligibility) and `initialized_at_rank`, `final_surfels` (chart and map checks). No
object name, catalog, semantic class, NS1b performance or future visibility; any name / catalog field in the input is
refused.

    eligible(i)  iff  initialized == true  AND  contributing_patches == 1          -> COHERENT_SEED_SET
    deferred(i)  iff  initialized == true  AND  contributing_patches  > 1          -> DEFERRED_AMBIGUOUS_ORACLE_IDENTITY
    otherwise   (never initialized in NS1a)                                         -> outside the NS1c scene

Expected (from the mandate, compared only AFTER derivation; a difference is a STOP, the expected ids are never
forced): COHERENT_SEED_SET = {9, 12, 123, 129, 172, 202, 204, 212, 230, 231}; deferred = {10, 110, 178}. "Coherent"
means only single-patch under the NS1a oracle aid; it claims no natural semantic coherence. The deferred identities are
excluded BY THE RULE (no special-case list). They never enter service summaries, scheduler inputs, target selection or
action execution, and are never labelled QUIET, UNLOCATED or BLOCKED. The never-initialized NS1a ids (no map) are
outside the scene set.

## 6. Initial persistent state (a continuation, not a replay)

    NB1c -> NS1a -> NS1b -> NS1c

- Every coherent entity except 172: its exact frozen NS1a H0 map (`entity-maps.npz`).
- Entity 172: the exact accepted NS1b POST-ACTION map (`fusion/fused-target-map.npz`, 21,243 surfels, patch ids
  `nb1c_gaze_06`, `ns1b_action_01`). It is never reverted to its NS1a seed.

All maps stay separate by temporary oracle id; no cross-id fusion.

## 7. One FIXED policy chart per coherent entity

C_i is built with the accepted NS1b rule (`ns1b_chart.chart_basis`), centred on the entity's NS1a INITIALIZATION GAZE
(the NB1c gaze of rank `initialized_at_rank`), never on a map centroid, latest gaze, object centre or catalog direction:

    g0_H = initialization gaze;  b_H = +X
    x_C = normalize(b_H − (b_H·g0_H) g0_H);  z_C = −g0_H;  y_C = normalize(z_C × x_C);  R_HC = column_stack(x_C, y_C, z_C)

The chart is fixed for that entity for the whole of NS1c; it is never recentered after a fixation (that would change the
accepted local-policy meaning). Every chart must meet the NS1b requirements independently (`chart_checks`:
orthonormality and det ≤ 1e-12, seed → local (0, 0) ≤ 1e-9°, H0 → C → H0 point / direction round trips ≤ 1e-12,
distances unchanged) and ‖b⊥‖ ≥ 1e-6. A singular or failing chart is a STOP before any execution. Entities sharing an
initialization rank share the same chart numerically; each entity records its own chart id and hash. C_172 must equal
the accepted NS1b chart bitwise.

## 8. The frame adapter (the accepted NS1b adapter, unchanged)

`ns1b_chart.PolicyChartAdapter` (pinned), with exactly the three accepted substitutions P1 (FSG6f rectified-core
projection), P2 (Cyclopean core directions) and P3 (Controller-02 predicted calibration), entered once per policy call
with the chart of the entity being probed, and the North-Star sensor `ns1b_chart.north_star_sensor` (full profile, IPD
0.063 m, vergence 2.10 m, AB1a head, `baseline_projected`) for P3. The accepted FSG6f constants, the 12-mm map
resolution, the Cyclopean 0.1° grid and the Controller-02 v1 gate are unchanged and recorded as used. Persistent fusion
is never done in a chart.

## 9. Initial controller contexts (stage `contexts`; no rerender)

For every coherent entity i an independent accepted `LocalPolicyContext`:

- **Entities other than 172** (exactly as the NS1b context): the saved NS1a observation at the entity's initialization
  rank (calibration, RGB, ORACLE AID reference; hashes equal to the NS1a observation freeze), passed through the accepted
  Classroom matcher (`ns1b_core.matcher_state`, once per rank) for the CONTROLLER OBSERVATION STATE only;
  `ns1b_core.build_context(i, calibration, state, valid, R_i, (0, 0))`: current local gaze (0, 0); visited [(0, 0)];
  own looks 1; Cyclopean evidence marked through P2 under C_i. Map: its NS1a H0 map.
- **Entity 172**: the ACCEPTED NS1b POST-ACTION context, imported exactly:
  history = [history_entry(NS1a rank-6 calibration, NS1b `context/controller-state.npz`), history_entry(NS1b action
  calibration, NS1b `post/controller-state.npz`)]; evidence = NS1b `post/evidence.npz`; visited [(0, 0), (0, −5)];
  current local gaze (0, −5); calibration = the NS1b action calibration; state = the NS1b post-action state; map = the
  NS1b fused map (21,243 surfels); own looks 2. NS1c's own rank-6 matcher state must equal NS1b's
  `context/controller-state.npz` bitwise (one look, one state).

No catalog, name, future visibility or Controller-01 bootstrap seed. No Blender call before step 0.

## 10. Two representations (retained, not redesigned)

- NORTH-STAR PERSISTENT METRIC MAP: PERFECT raw correspondence -> accepted spherical geometry -> H0 SurfaceMap.
- CONTROLLER OBSERVATION STATE: the accepted Classroom controller-time oracle matcher (masks, continuation, boundary
  history, Cyclopean evidence, physical-serviceability gate).

The planar controller-state geometry never substitutes for the North-Star map. For every action, and for every entity's
initialization look, both counts are recorded (North-Star raw-core target metric points; controller-state target
support = matcher-valid target points, and target-labelled left-core pixels). Descriptive only: the controller is not
changed because they differ.

## 11. Initial service probe of the whole coherent set (stage `initial-probe`; once; before any render)

For every coherent entity, in ascending id, exactly once: its H0 map transformed into C_i; the accepted
`controller01.probe_local_policy` (FSG6f, then the Cyclopean handoff if FSG6f stops) and the accepted
`controller02.final_look_gate_v1` under the adapter (`ns1b_core.probe`, unchanged). Recorded per entity (the B8 table):
entity id, initialization rank, map surfels, own looks, current local gaze, FSG6f result, proposal source, proposed local
gaze, proposed H0 gaze, gate result, gate reason, novel serviceable support, service state (section 12).

- **NS1b reproduction (HARD STOP).** The probe of 172 must reproduce the accepted NS1b post-action probe exactly
  (decisions, summary, gate verdict and detail, state and proposal; tolerance 0): ACTIONABLE, source `fsg6f`, local
  (−5°, −10°), H0 (−147.585°, +37.246°), gate admissible, novel serviceable support 22. Any difference is a HARD STOP
  before any render.
- **Chart covariance per entity.** Each entity's probe is repeated on its context rigidly rotated about the physical
  baseline by β ∈ {+37°, −61°} (the NS1b in-probe invariance, an exact fixed-head symmetry; accepted comparison rules for
  float ties and exact 25-mm voxel boundaries). Any unexplained difference is Outcome 4 (STOP, no render).
- A refusal raised by the accepted code for an entity is Outcome 4 (STOP); no service state is invented for it.

## 12. Service states and the watchdog

    admissible gated proposal                         -> ACTIONABLE
    no proposal, or the v1 gate rejects the proposal  -> QUIET     (incl. Cyclopean proposals: v1 "untraceable")
    ACTIONABLE and own looks >= WATCHDOG              -> BLOCKED:watchdog   (sticky, as in integrated.run_control_loop)

No coherent entity is SEEDABLE (all are initialized); none is UNLOCATED. WATCHDOG is the accepted Controller-01 constant
read live (`controller01.WATCHDOG` = `config.MAX_OBJECT_FIXATIONS`; expected 24; recorded and pinned). Own looks
include the initialization look (172: 2; every other coherent seed: 1). No new per-object watchdog; no widened budget.

## 13. The scene scheduler — the accepted one

`fov3d.control.integrated.schedule(current_id, summaries)`, unchanged (pinned file), is the only scheduler. Its input is
exactly one `ObjectSummary` per coherent entity (never a deferred id). Initial current object: 172. Its accepted
semantics: retain the current object while it is serviceable; otherwise switch to the next serviceable id above it
(wrapping to the lowest); with nothing serviceable, terminal (Stop / Incomplete). Recorded per decision: kind, current,
selected, reason (retain / switch; a switch to an entity that had become QUIET and then non-QUIET is recorded
`natural_reactivation`, as in the accepted loop; there is no reactivation operation), attention bout (bout 1 is 172's
continuing NS1b bout; +1 at each switch), previous target, transition.

Revision and cache (the accepted `run_control_loop` semantics): revision(i) = (own looks, map surfels), the analog of
the accepted Controller-01 (own looks, measured points) for NS1c's effective geometry, which is the entity's H0 map
only (NS1c keeps no cross-target measurement memory). A probe result is reused exactly while the revision is unchanged;
calls and cache hits are recorded.

## 14. One scene-level iteration (global step k)

Each stage below runs once per step, as its own process, under the accepted `nb1a_guard.OpenGuard`:

1. `schedule`: recompute the summaries (section 12) from the latest probes; call `integrated.schedule`; record the
   decision. Terminal -> section 19 (no action). Attend -> the cap check (section 18) -> the selected entity's frozen
   admissible proposal (its latest probe) -> local C_i gaze -> H0 world gaze (`ns1b_chart.local_to_world_gaze`;
   H0 -> C_i round trip ≤ 1e-9°) -> planned calibration `ns1a_core.planned_calibration(H0 gaze, AB1a head)`, which must
   pass `ns1b_core.physical_calibration_test` (the real sensor at the WORLD gaze, never the fake local one).
2. `preflight` (Blender, NO render) and 3. `acquire` (Blender, ONE binocular pair; section 15).
4. `freeze-observation`; 5. `perfect-correspondence` (accepted AB1b `compute_oracle`, truth-stripped product);
   6. `freeze-correspondence`; 7. `spherical-geometry` (accepted AB1b, truth-free guard); 8. `freeze-geometry`;
   9. `local-oracle-segmentation` (ORACLE SEGMENTATION AID; only `instance_L`, after the geometry freeze).
10. `fuse` (section 16).
11. `update`: the accepted Classroom matcher on the new look (controller observation state); `ns1b_core.add_look` under
    C_target (Controller-01 `observe` order: evidence, history, visited, current gaze / calibration / state); the
    target's map <- the fused map; the target's own looks and revision advance. Re-probe: the target (revision changed)
    and every other coherent entity through the cache; watchdog; the scene state record (section 20); the stop test
    (section 18).

A driver `loop` runs these stages in order, step after step, as subprocesses, until the stop, a terminal decision, the
cap or the budget. Only the target's geometry, history, visited gazes, evidence, own looks and revision change in a step.

## 15. Action measurement — the unchanged North-Star path

Classroom `classroom_eye.blend` (`dca66a32…`), fixed head, static scene, 640 × 640 raw, 256 × 256 nominal core, 12°
core, IPD 0.063 m, vergence 2.10 m, OPTIX, 4096 spp, seeds L 2111 / R 2112, denoising OFF, adaptive sampling OFF,
BOX 1.0, `baseline_projected`, through the accepted `ab1a_render` / `ns1a_render` helpers (as NS1b section 12): EYE pose
= AB1a head; calibration built in Blender byte-identical to the planned one; settings readback equal to the accepted
AB1d2 4096-spp readback; 4096 in both EXR headers; sealed catalog written and its seal equal to NS1a's before
rendering (never opened by a host stage). No rerender, no natural stereo, no SGBM, no head motion, no renderer change.
A projected render above 600 s is a STOP.

## 16. Target-only persistent fusion

From the frozen spherical measurement keep only `valid_epi` points whose local oracle id equals the selected target:
`Patch("ns1c_step_NN", xyz_h = P_epi (H0), rgb, instance_id)`, fused into ONLY that target's H0 map with the accepted
`surface_map.fuse` (association radius 0.012 m, hash cell 0.012 m; `ns1b_core.fuse_h0`, H0 only) and replayed once
(exact idempotence). The accepted precondition stands: fewer than 100 target points -> retained, not fused (reported).
Incidental ids in view are never fused into their maps; every non-target map is byte-identical before and after.
Recorded per action: target id, local gaze, H0 gaze, map before, target measured points, matched points, affected
existing surfels, matched distance median / p95 / max, new surfels, map after, replay idempotent.

## 17. Reactivation

Because a step changes only the target's sensory history and map, no other entity's revision changes. The accepted
cache semantics apply; any untouched entity whose service state changes is recorded prominently with its cause (no
special rule; no `reactivate()`). The checker re-probes every untouched entity from scratch at the end and requires its
probe to equal its initial probe.

## 18. The stop condition, the cap and the budget

- **Canonical stop — first spread of attention.** After the FIRST successful physical action whose target != 172
  (successful = executed through the fusion stage: FUSED, or retained by the accepted 100-point precondition), its
  `update` performs the one read-only post-action probe of that new target (its proposal is NOT executed), recomputes the
  scene service-state table once (others from the cache), writes the final scene state and freezes it. STOP. Any later
  `schedule` is refused: no second action on the new target, no third entity.
- **Global safety cap.** Maximum new physical actions = WATCHDOG (24). If the scheduler attends an entity after 24 new
  actions have executed, the loop records `CapReached` and STOPS (Outcome 4). A safety cap, not a completion condition.
- **Time budget.** PROPOSED cost ≈ 50 s per step (render ≈ 38 s); worst case 24 actions ≈ 20 min. After each step the
  driver projects elapsed + (cap − executed) × mean step seconds; above 1800 s it STOPS before the next step and reports
  (no parameter is changed; continuation only by Luiz's decision).

## 19. Outcome semantics

- **Outcome 1 — natural scene switch.** 172 is serviced until its summary is QUIET; the unchanged scheduler switches to
  another ACTIONABLE coherent seed; one controller-selected observation executes for it and updates its H0 map.
  Establishes multi-entity scene-level North-Star control.
- **Outcome 2 — watchdog-driven switch.** 172 remains ACTIONABLE until BLOCKED:watchdog; the scheduler switches and one
  action executes on another coherent seed. Multi-entity mechanics, not natural completion of 172 (partial success).
- **Outcome 3 — no serviceable second entity.** The scheduler is terminal before any second-entity action: Stop
  (global_quiescence of the coherent subset) is recorded `COHERENT_SUBSET_QUIESCENT`; Incomplete (172 blocked, nothing
  else serviceable) is recorded `COHERENT_SUBSET_INCOMPLETE`. Never `SCENE_CLOSED`: the full Classroom is not closed.
- **Outcome 4 — cap or integration failure.** The cap; NS1b post-probe not reproduced; scheduler semantics diverge; chart
  covariance fails; physical-head invariance fails; a refusal of the accepted code; the measurement / fusion pipeline
  fails; the budget stop. STOP; no tuning.

If the second-entity action is retained (fewer than 100 target points), the switch is reported with that fact; the
reading is left to Luiz and Chat. The report gives a reading; Luiz and Chat decide.

## 20. Scene state record

After the initial probe and after every step, `scene/state-NN.json` records, for every coherent entity:
temporary_entity_id, initialization rank, chart id / hash, current local gaze, own looks, map surfels, service state,
proposal source / local gaze / H0 gaze (if actionable), gate reason, novel support, revision, probe provenance (fresh or
cached); and globally: global step, current target, scheduler decision and reason, attention bout, previous target,
target transition, accumulated physical observations, the deferred identities (listed separately), the watchdog and the
cap. The action trace must let Chat reconstruct why 172 was retained, when it ceased to be retained, and why the new
target was selected.

## 21. Truth boundary and process

Controller-time oracle aids are exactly the concept-demo aids: PERFECT local correspondence (AB1b service for the
measurement; the Classroom matcher for the controller observation state) and local Object Index identity. The controller
never sees Position beyond those services, future visibility, global Blender geometry, catalog names or full catalog
ordering. Every stage runs under `OpenGuard`; the checker scans every guard record. Truth (Position / Object Index) is
read only by `contexts` (matcher state), `perfect-correspondence`, `freeze-observation`, `local-oracle-segmentation`
(`instance_L` only) and `update` (matcher state). The spherical geometry is truth-free. No `run_control_loop`,
`run_controller02`, `catalog_summaries`, SCENE_CLOSED marker, natural stereo, SGBM or head motion in the production
code; `integrated.schedule` is the only scheduler.

## 22. Known-answer / preflight tests

Analytic (`synthetic`, before any NS1a / NS1b data is touched): charts orthonormal / det +1 / seed -> (0, 0) on every
NB1c gaze; local -> H0 -> local round trips; scheduler synthetic (current ACTIONABLE -> retain; current QUIET ->
deterministic switch, forward then wrap; nothing serviceable -> Stop / global_quiescence; blocked -> Incomplete;
watchdog -> BLOCKED); the eligibility rule on synthetic seed documents (multi-part excluded by rule; names refused);
a deferred id inserted into the summaries is refused; a fixed-H0 calibration accepted, a chart-local fake head refused;
the first world action's calibration equals the real sensor at the mapped H0 gaze; target-only fusion (incidental maps
unchanged); the 12-mm H0 fusion known answer; the second-target stop refuses another action; the global cap; the
SCENE_CLOSED marker refused.

On the frozen data, each a STOP in its stage: the coherent set derived = the expected ten (`eligibility`); 10 / 110 /
178 excluded by rule (`eligibility`); one chart per coherent id meeting section 7 (`charts`); the 172 import: map hash,
21,243 surfels, 2 own looks, visited (0, 0) and (0, −5) (`contexts`); every other entity's NS1a initialization look
reused without rerender (`contexts`); the NS1b post-probe reproduction (`initial-probe`).

## 23. Checker (`tools/north_star/check_ns1c.py`)

Own literal pins; independent recomputation wherever an independent formula exists (eligibility, charts by the triple
product, world gazes by the column form, fixed-head calibrations, PERFECT correspondence and triangulation by the
accepted NS1a checker's own implementations, the 12-mm association by an own brute-force nearest surfel); the accepted
policy is re-run (it has no independent implementation): every recorded probe is recomputed from the reconstructed
context. Families: PROVENANCE (repo, base, NS1b / NS1a acceptance, contract first and unchanged, pins); ELIGIBLE SET
(derived, rule, expected ten, no names, deferred ids absent from every scheduler input); INITIAL STATE (172 = NS1b
post-action context and map; others = NS1a; exact histories); CHARTS (construction, fixed per entity, no recentering,
non-singular, round trips); PHYSICAL SENSOR (head fixed, eye centres fixed, no fake chart sensor, mapped world gazes);
INITIAL PROBES (each coherent entity exactly once before any render; 172 reproduces NS1b; rotation invariance);
SCHEDULER (exact `integrated.schedule` recomputed on every recorded summary set; current starts at 172; retain / switch
exact); WATCHDOG (accepted constant; own-look counts; no widened budget); ACTION PROCESS (each step's stages once, in
order; no rerender; 4096 spp; PERFECT; spherical H0; identity only after geometry); FUSION (selected target only; H0;
12 / 12; idempotent; no cross-id modification; unique patch ids); STOP (canonical stop right after the first successful
action with target != 172; at most one post-action probe of it; no third entity; cap); TERMINOLOGY (no SCENE_CLOSED);
REACTIVATION (untouched probes recomputed from scratch equal); TRUTH BOUNDARY (guard records); VISUALS (byte-identical
regeneration, oracle badges, local vs H0 labels, fixed-head statement, deferred identities shown, scheduler transition
shown); MANIFEST and declared changes. Every load-bearing rule must be able to fail.

## 24. Corruption suite (`tools/north_star/check_ns1c_corruptions.py`)

From a passing baseline, after an unmodified-mirror null probe; each corruption mutates a temporary mirror (large arrays
symlinked and unlinked before any write), regenerates the mirror's manifest, names the checks that must catch it; RUN
and VIS are hashed before and after. At least: ELIGIBILITY (include 10; include 110; include 178; drop a valid coherent
seed; use names); INITIAL STATE (revert 172 to its NS1a map; remove the NS1b action from its history; alter 172's
visited gaze; re-render another seed's initialization look); CHART (recenter a chart after an action; map centroid;
flip an axis; transpose); SCHEDULER (start with current = None; choose the target manually; change the ordering; switch
while the current entity is still actionable; mark deferred ids QUIET); WATCHDOG (change the limit; reset 172's own-look
count); PHYSICAL ACTION (local gaze used as H0 gaze; head moved; IPD changed; spp changed; rerender); MEASUREMENT (SGBM;
planar persistent geometry; Position leak into the spherical stage); FUSION (fuse an incidental entity; fuse all visible
ids; radius changed; fuse in C; cross-id fusion); STOP (a second action on the new target; a third entity; SCENE_CLOSED
emitted); VISUAL (deferred identities hidden; scheduler reason hidden; fixed-head statement omitted; oracle label
removed). Corruptions that do not apply to the executed trajectory are recorded NOT APPLICABLE with the reason, never
counted as caught.

## 25. Scientific visuals (Visual Language 1; deterministic; regenerated byte-identically by the checker)

`VIS/overview.png`: **A** North-Star scene state (coarse Classroom 360° view in H0; the ten coherent seed maps; 172
highlighted as current; 10 / 110 / 178 shown separately as DEFERRED AMBIGUOUS ORACLE IDENTITY); **B** initial service
map (per coherent entity: ACTIONABLE / QUIET, map size, chart centre, proposed local gaze where applicable); **C**
attention timeline (every NS1c action in order: global step, target, retain / switch, local gaze, H0 gaze, map growth;
the first target switch prominent); **D** first cross-entity action (old target 172 -> new target j: scheduler reason,
the new entity's seed map, the selected fixation, the new observation, the target measurement, the fused map); **E**
scene state after the switch (all coherent maps in canonical H0; the service-state table; the new target's next
proposal, explicitly NOT EXECUTED). Supporting: `scene-scheduler-timeline.png` (rows entities, columns global actions;
service states, current target, scheduler transitions); `multi-entity-growth-3d.png` (canonical-H0 geometry of 172 and
the second entity before / after their NS1c actions; 172's growth sequence if several); `controller-vs-northstar-support.png`
(descriptive: per action, controller-state target support vs North-Star raw-core target measurement). Truth badges on
every figure; frame labels (POLICY CHART vs CANONICAL H0); PHYSICAL HEAD FIXED - POLICY CHART ONLY; non-color cues;
`visuals-manifest.json`. Without a switch (Outcome 3 / 4), panels D / E and the growth figure show what exists and state
that no cross-entity action occurred.

## 26. Commands and order

    RUN=/home/lvelho/rd/f3d-vision/previews/north-star/ns1c-coherent-first-scene-switch
    VIS=/home/lvelho/rd/f3d-vision/visuals/north-star/ns1c-coherent-first-scene-switch
    .venv/bin/python tools/north_star/ns1c_run.py source         --run $RUN
    .venv/bin/python tools/north_star/ns1c_run.py synthetic      --run $RUN
    .venv/bin/python tools/north_star/ns1c_run.py eligibility    --run $RUN
    .venv/bin/python tools/north_star/ns1c_run.py charts         --run $RUN
    .venv/bin/python tools/north_star/ns1c_run.py contexts       --run $RUN
    .venv/bin/python tools/north_star/ns1c_run.py initial-probe  --run $RUN   # every coherent entity once; no render
    .venv/bin/python tools/north_star/ns1c_run.py loop           --run $RUN   # per step: schedule, preflight, acquire,
        # freeze-observation, perfect-correspondence, freeze-correspondence, spherical-geometry, freeze-geometry,
        # local-oracle-segmentation, fuse, update -- until the stop, a terminal decision, the cap or the budget
    .venv/bin/python tools/north_star/ns1c_run.py visualize      --run $RUN --visuals $VIS
    .venv/bin/python tools/north_star/check_ns1c.py --run $RUN --visuals $VIS --corruptions --write-summary

Every canonical stage runs once (per step for the step stages) from one clean pushed implementation commit. Cost classes
(PROPOSED): `initial-probe` interactive-to-batch (ten probes plus twenty rotated probes); `loop` batch per step
(≈ 50 s), normally a few steps, worst case ≈ 20 min (section 18 budget); the checker with corruptions batch; every other
stage interactive. No overnight task, no parameter sweep.

## 27. Permitted fix scope

- **Before the canonical run:** implementation defects in the NS1c tools, without changing sections 4–20 or a declared
  tolerance. Development uses analytic fixtures; the 172 NS1b import and post-probe reproduction (an accepted known
  answer); the controller observation state of the NS1a looks (entity-independent, no policy); and a scratch
  development run (never the canonical RUN) whose scene is the rehearsal set {172 (NS1b import), 10, 110, 178} — the
  deferred multi-part ids act as non-coherent rehearsal entities, as entity 110 did for NS1b — with a no-render
  Classroom preflight and low-spp factory-startup rehearsal renders (never a Classroom render). No coherent entity other
  than 172 is probed in development; 172 is probed only for the NS1b reproduction and after rehearsal looks.
- **After the canonical run starts:** (a) a stage that fails with an implementation defect BEFORE writing any output may
  be repaired minimally and then run for its first and only time, if sections 4–20 are unchanged (recorded as an
  incident); (b) presentation-only figure fixes; (c) a checker or corruption-suite defect that false-alarms on correct
  data, only if the fix does not weaken the check (recorded).
- Anything else — a re-render, a re-probe outside the rules, a different target, a chart change, an adapter, policy,
  gate, scheduler, watchdog, oracle, geometry, identity or fusion change — is a STOP for Luiz and Chat.

## 28. Stop conditions

STOP and report if: a source / NS1a / NS1b pin fails; `synthetic` fails; the derived coherent set differs from the
expected ten; a chart is singular or fails section 7; the 172 import is not exact; the NS1b post-probe is not reproduced
(HARD STOP); a per-entity rotation invariance fails; the accepted code refuses an entity; `preflight` fails; a render
projects above 600 s; the budget projection exceeds 1800 s; a guard records a violation in a canonical stage; a stage
would run twice; the cap is reached; a canonical check fails for a reason other than a checker defect.

## 29. Report and stop

`docs/north-star/ns1c-coherent-first-scene-switch-report.md`, status REVIEW PENDING, marker
`NORTH_STAR1C_COHERENT_FIRST_SCENE_SWITCH_COMPLETE`, no ACCEPTED marker. It records: provenance; NS1b acceptance /
source pins; the coherent-set derivation; the deferred identities; the per-entity charts; the imported initial
contexts; the exact NS1b post-probe reproduction; the initial service table; the scheduler action trace with every
retain / switch reason; every local and H0 gaze; every physical acquisition; per-action PERFECT correspondence /
spherical geometry and target fusion; controller-state vs North-Star support; the exact event that ended 172's service;
the first selected second entity and its first action; the frozen scene state after the stop; the Outcome reading;
checks; corruptions; visuals and hashes; incidents; what is and is NOT established; and the unresolved decision for Luiz
/ Chat: READY TO RELEASE THE FULL COHERENT MULTI-ENTITY NORTH-STAR LOOP? Then STOP: no acceptance, no merge, no second
action on the new target, no third entity, no 10 / 110 / 178, no identity decomposition, no background model, no
SCENE_CLOSED, no natural stereo, no head motion.

## 30. What NS1c may and may not establish

May establish: whether, from the accepted NS1b state, the accepted scheduler and the per-entity recentered local
controllers (fixed charts, unchanged policy and gate, fixed head) continue servicing 172 and then switch autonomously to
another coherent seed and execute one valid controller-selected PERFECT observation there, fused into that entity's
canonical H0 map.

May NOT establish: full Classroom closure or scene-level quiescence; the serviceability of every coherent entity beyond
its probe; anything about the multi-part identities; natural correspondence or natural identity; that the charts are
optimal; head motion, real cameras or other scenes.
