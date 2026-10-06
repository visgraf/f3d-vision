# North Star-1e — Full Coherent Multi-Entity Loop with Cross-Target Measurement Memory — contract

**Status: CONTRACT (committed before any NS1e implementation commit, before any NS1e probe, before the start-state
reconstruction and before any NS1e render).** Completion marker (written only by the report):
`NORTH_STAR1E_COHERENT_FULL_LOOP_M2_MEMORY_COMPLETE`. No ACCEPTED marker is written by Claude Code.

Decision context (recorded on `main` at `5aa2231`): North Star-1d is ACCEPTED as Outcome 2 (acceptance `25bb929`,
`NORTH_STAR1D_CROSS_TARGET_MEASUREMENT_MEMORY_ACCEPTED`). Cross-target causal measurement memory, correct NORMAL scene
switching and policy-chart global transport are established. NS1e releases the coherent ten-entity Controller-02 loop
with full M2 measurement memory, continuing from the accepted post-NS1c2 / NS1d state.

**NS1e is the first North-Star run released to its honest Controller-02 terminal state.** There is no first-action,
first-switch, first-object, first-reactivation or first-deferral stop. The controller runs until (a) the accepted
Controller-02 state machine closes the declared coherent scheduler universe, or (b) the mathematically derived hard action
cap is reached, or (c) an implementation / scientific invariant fails. A strictly post-control evaluation against the
accepted Breadth-1 0.5° reference follows the controller freeze.

## 1. One causal question

> Starting from the accepted NS1d M2-enriched post-NS1c2 state, can the accepted Controller-02 scene machine autonomously
> service the entire coherent ten-entity North-Star scheduler universe to its honest terminal state, using: the fixed
> physical head; the fixed recentered local policy charts; FSG6f -> Cyclopean local control; PERFECT local correspondence;
> spherical H0 metric geometry; target-only persistent fusion; instance-keyed cross-target measurement memory;
> revision-driven natural reactivation; and correct NORMAL / DEFERRED / RESIDUE semantics — without controller retuning?

Nothing is tuned. Every policy, scheduler, budget, gate, chart, sensor, fusion and memory rule is an accepted, unchanged
component. The measured product is the trajectory the assembled system chooses, its terminal state, and the post-freeze
coverage of the resulting persistent maps.

## 2. Provenance and branch

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (the frozen legacy `fov-3d-vision` is never used) |
| base (`main`: post-NS1d roadmap) | `5aa223109ec829d41945f19b4c5223928fd0dde9` |
| NS1d acceptance | `25bb929b4d39e1e73cabf0df582bc3c5d3e45e06` (`NORTH_STAR1D_CROSS_TARGET_MEASUREMENT_MEMORY_ACCEPTED`) |
| NS1d contract / implementation / report | `93f51d3` / `723b3ac` / `1d2ea2d` |
| NS1c2 acceptance / NS1b acceptance / NS1a acceptance | `5fe0684` / `2553551` / `37c7e02` |
| branch | `north-star/ns1e-coherent-full-loop-m2-memory`, from the base, in an isolated worktree |
| run (`RUN`, machine evidence) | `/home/lvelho/rd/f3d-vision/previews/north-star/ns1e-coherent-full-loop-m2-memory/` |
| visuals (`VIS`, persistent) | `/home/lvelho/rd/f3d-vision/visuals/north-star/ns1e-coherent-full-loop-m2-memory/` |

The implementation commit writes this contract's commit SHA into `ns1e_spec.CONTRACT_COMMIT` and the checker's literal;
the checker requires this file to be unchanged from that commit to the checked tree.

Frozen inputs (sha256; a mismatch is a STOP; every one listed in full in `ns1e_spec`; every upstream file NS1e reads must
also equal its upstream manifest entry):
- NS1d run `previews/north-star/ns1d-cross-target-measurement-memory/`: `manifest.json`
  `2b5bd1726e291f8234b5ffc33d13b4afe0d930c4e9955da9aff1bf03e8848c6e`, `check-summary.json` `9320a3d6…`,
  `freeze/replay-freeze.json` `95c5106e…`, `freeze/event-list-freeze.json` `c39390b7…`; consumed:
  `replay/state-after-event-08.json` `7f0c7ce5…` (the M2 machine, contexts and memory summary after memory event 8),
  `replay/final.json` `6dcf21a8…` (the descriptive M2 next decision, NOT EXECUTED), `events/event-list.json` `eea5d6f5…`
  and the nine frozen memory patches `replay/events/event-0{0..8}/memory-patch.npz` with their `event.json` records.
- NS1c2 run `previews/north-star/ns1c2-controller02-phase-semantics/`: `manifest.json` `0ec6228d…` (279 files);
  consumed: `scene/state-after-step-07.json` `7e50ecf5…` (the accepted final persistent maps and own-look contexts),
  `charts/policy-charts.json` `058a9253…`, `contexts/contexts.json` `25b3940b…` (rank-1 initial planar support) and every
  map / evidence / controller-state / calibration file those records name (NS1c / NS1b / NS1a files through the accepted
  references, each equal to its own manifest or pin).
- NS1a run: `seeds/seed-set.json` `e2ff1ba3…` and `source/nb1c-gaze-list.json` `785d02a7…` (eligibility and charts are
  re-derived from them, section 5).
- Breadth-1 reference (evaluation only, section 26): `previews/breadth-1-classroom-234-spherical-glance/render/canonical.exr`
  `4ea036fc74eab3b3ab06a0c4470c2b01740c9322de0eea522f957ddfffa172f8`.
- Accepted code, unchanged (sha256 at the base): `fov3d/` entirely (in particular `fov3d/control/controller02.py`,
  `fov3d/control/integrated.py`, `fov3d/reconstruction/measurement_memory.py`, the Classroom Controller-01 / Controller-02
  adapters), FSG6f, Cyclopean, the surface map, the AB1b oracle / geometry, the accepted render helpers, and the accepted
  NS1a / NS1b / NS1c2 / NS1d tools NS1e imports (`ns1a_core`, `ns1a_render`, `ns1b_chart`, `ns1b_core`, `ns1c2_core`,
  `ns1c2_phase`, `ns1c2_spec`, `ns1d_core`, `ns1d_spec`), and `tools/classroom_oracle1_eval.py` (the accepted 12-mm
  coverage function).

## 3. Pre-contract activity (disclosed)

Before this commit:
- Part A of the mandate: the NS1d acceptance commit `25bb929` (fast-forwarded to `main`) and the post-NS1d roadmap
  `5aa2231`, with their gates (recorded in their commit messages).
- Reading only: the code, contracts and reports named in the mandate; the recorded JSON products of the NS1c2, NS1d and
  Breadth-1 runs (the frozen NS1d M2 machine after event 8: step 8, bout 2, current 202, fixations 172: 9, 202: 2, others
  1; 172 QUIET with `quiet_since` 6; the descriptive next decision retain 202, FSG6f, local (−10.9°, +10.5°), H0
  (−147.628°, +15.923°)); the NS1c2 per-step process timings (about 40–46 s per new 4096-spp action, of which about 38 s
  is the render).
- One timing measurement: the nine NS1d memory patches were loaded and appended to a fresh accepted
  `InstanceMeasurementMemory` in a scratch process (0.06 s; 581,882 samples), to size the per-stage ledger rebuild. No
  probe, no gate, no scheduler decision, no render and no NS1e output was produced.

## 4. NS1d acceptance (pointer)

NS1d is ACCEPTED (report `docs/north-star/ns1d-cross-target-measurement-memory-report.md`, acceptance record). Its frozen
memory-enriched post-step-7 state is the NS1e start state. Accepted retained limitations carried into NS1e: bootstrap
cross-target memory NOT DEFINED; ten coherent entities only; 10 / 110 / 178 outside scheduling; the rank-1 planar
controller-state zero-support seam; RESIDUE not yet reached naturally in a North-Star scene run; PERFECT correspondence and
identity are oracle aids.

## 5. Scheduler universe, charts and identities

- **Eligibility.** Re-derived at run time from the frozen NS1a seed set with the accepted rule
  (`ns1c2_core.derive_coherent_set`: `initialized == true AND contributing_patches == 1`), reading only the eligibility
  fields; no name, catalog, semantic class or visibility. Expected: {9, 12, 123, 129, 172, 202, 204, 212, 230, 231};
  ambiguous multi-part oracle ids {10, 110, 178}: `AMBIGUOUS ORACLE ID — EXCLUDED FROM SCHEDULER`. A different derived set
  is a STOP (never hard-coded silently).
- **Memory identity ≠ scheduler identity.** The memory stores every positive observed id (coherent, ambiguous or never
  initialized). A memory id never becomes a scheduler input.
- **Charts.** Each coherent entity keeps its accepted NS1b-construction chart centred on its ORIGINAL NS1a initialization
  gaze (`ns1c2_core.chart_record`, recomputed and required bitwise equal to the NS1c2 chart file). Never recentered: not
  on later observations, not on a map centroid, not on the latest gaze. Checks: orthonormal; det +1; seed → local (0, 0);
  local / H0 round trip; projected baseline non-singular. Policy domain yaw ±25°, pitch ±20°, component step 5°; all FSG6f /
  Cyclopean constants unchanged (pinned through `ns1c2_spec` / the accepted constants check).

## 6. Exact start state and the handoff (stage `handoff`; no render, no Blender)

The NS1e start state is the accepted post-NS1c2-step-7 scene enriched by the accepted NS1d M2 memory after memory event 8.
Nothing is re-acquired or re-rendered. Memory events 0..8 are consumed (event 0 = the NS1b action on 172; events 1..8 =
NS1c2 actions 0..7).

`handoff` reconstructs the complete live M2 scene independently and verifies it against the frozen records:
1. **Records.** The ten entity records of NS1c2 `scene/state-after-step-07.json` (persistent maps, looks, visited gazes,
   current gazes, evidence), with their run-relative references re-scoped to the NS1c2 run (`ns1c2:` scheme). Required:
   their context part equals the NS1d `contexts` after event 8; maps equal NS1c2's final maps (sha256).
2. **Memory.** A fresh accepted `InstanceMeasurementMemory` (through `ns1d_core.MemoryLedger`, unchanged) fed the nine
   frozen NS1d memory patches in event order (each patch equal to its NS1d manifest entry and event record; observation
   key = the event list's observation-freeze sha256; `source_global_index` = memory event index; `source_active_target_id`
   = active target). Required: the ledger summary (total 581,882; per-id counts; per-id provenance; snapshot digests)
   equals the NS1d after-event-8 memory summary exactly.
3. **Contexts.** NS1e rebuilds each `LocalPolicyContext` with `ns1e_core.context_from_record`, which is the accepted
   `ns1c2_core.context_from_record` with one change only: the reference resolver also knows the `ns1c2:` and NS1e `run:`
   schemes. Required: for all ten imported records it produces exactly the accepted function's context (evidence arrays,
   history entries, visited, gaze, calibration, state), computed with the accepted function on the original NS1c2 records.
4. **Probes.** One fresh M2 NORMAL probe per entity (section 8). Required: each equals the NS1d frozen M2 machine's cached
   probe for that entity (policy part: action, summary; tolerance 0) and its M2 revision equals the cached revision.
5. **Machine.** A fresh `ns1c2_phase.SceneMachine` (unchanged) over the coherent ids with the live budget, resumed with
   the accepted NS1d resume semantics (`ns1d_core.resume_scene`: `resume_initialized` + the quiet bookkeeping of every
   entity already QUIET) at current = 202, bout = 2, global step = 8, fixations = the records' own looks and
   `quiet_since` = the frozen record's value for each QUIET entity (172: 6). Required equal to the frozen NS1d M2 machine:
   order, budget, initialized, dispositions (all NORMAL), fixations, statuses, recorded statuses, phase, current, bout,
   step, `quiet_since`, the quiet probes (policy part), `reactivated_since_attended`, cache revisions, terminal (none). No
   historical event is re-emitted (the fresh machine's event list is empty).
6. **Next decision.** `decide()` on a copy of the machine must reproduce the frozen NS1d M2 next decision exactly
   (`replay/final.json`): kind attend, target 202, `schedule_normal` decision retain, reason retain, source `fsg6f`, local
   gaze (−10.899999999999999, 10.5), mapped H0 gaze (−147.62774503449359, 15.922813864915128) — full precision — with the
   world-gaze round trip and the real fixed-head physical-calibration test passing.
7. **Expected (derived, compared, never forced):** current target 202; own looks 172: 9, 202: 2, every other coherent
   entity 1; 172 QUIET; 202 ACTIONABLE; M2 memory 581,882 samples in 11 observed ids; revisions 172 (9, 131,695),
   202 (2, 17,447), 212 (1, 38,197), 123 (1, 5,779), 129 (1, 777), others (1, 0).

Any difference in target, source, local gaze, H0 gaze, scheduler reason, revision, map, memory or own-look context is a
**HARD STOP** before any render (Control Outcome 3). The handoff writes the NS1e initial scene state
(`scene/state-initial.json`), the derived cap (section 20) and `freeze/handoff-freeze.json`.

## 7. The resumable scene machine

The accepted resumable Controller-02 implementation `tools/north_star/ns1c2_phase.SceneMachine` drives the loop
unchanged: `decide(final_gate, action_cap)` (NORMAL `schedule_normal`; the phase return to NORMAL; cap; bout; the
natural-reactivation reason; the RESIDUE procedure) and `commit(plan, outcome, probe, revision)` (fixations; finalization
of an executed final look; the refresh with its deferral rule, quiet / natural-reactivation / deferred / local-state-change
events; the action record). `fov3d/control/controller02.py` and `fov3d/control/integrated.py` are not modified. The
machine persists as its own JSON (`to_json` / `from_json`) in every scene checkpoint. There is no manual reactivation
operation anywhere in NS1e (code scan).

## 8. M2 is the live controller geometry

For every scheduler entity i, with the ledger rebuilt in each process from all frozen memory events (section 23):

    map_xyz(i)              = persistent H0 SurfaceMap(i)
    memory_xyz(i)           = InstanceMeasurementMemory.snapshot(i).xyz_h
    effective_geometry_H0(i) = effective_target_geometry(map_xyz(i), memory_xyz(i))      (accepted, unchanged)
    revision(i)             = (own_look_count(i), measured_points(i))                    (measured points of observed id i)

The NORMAL probe of i is the accepted `ns1c2_core.probe_normal_ctx` (the accepted `controller01.probe_local_policy`, FSG6f
→ Cyclopean, under the accepted NS1b frame adapter `ns1b_chart.PolicyChartAdapter` with the entity's fixed chart; NO gate)
on `to_chart(effective_geometry_H0(i), R_HC(i))`. The map-surfel count is never a revision component. The adapter's probe
cache is keyed by this revision, so a cross-target memory addition invalidates i's cached probe and i is re-probed at the
next refresh.

## 9. Physical sensor: fixed

The physical head stays in canonical H0 for the entire run: no head rotation, no translation; eye centres
(∓0.0315, 0, 0) m; IPD 0.063 m. Every physical action maps its local policy gaze through the fixed chart C_i to an H0
direction and is executed by the real fixed-head sensor at that world gaze (`ns1a_core.planned_calibration`; the accepted
`ns1b_core.physical_calibration_test` must pass: real world sensor yes, fake local-baseline sensor no, fixed head yes).
Persistent geometry and measurement memory stay in H0. No camera is ever built with a baseline rotated into C_i.

## 10. NORMAL semantics

Accepted Controller-02 NORMAL semantics exactly: a ProbeResult with an action (`fsg6f` or `cyclopean_epistemic`) is
ACTIONABLE; without one, QUIET. `final_look_gate_v1` is never called in NORMAL. Every policy-running stage runs under the
accepted `ns1c2_phase.GateGuard`, which records every gate call with the scene phase and raises unless the phase is
RESIDUE. Required for the whole run: **NORMAL final-gate calls == 0**. Scheduler: the accepted `controller02.schedule_normal`
(retain the current ACTIONABLE; otherwise switch deterministically to the next NORMAL-serviceable id above the current,
wrapping to the lowest). Natural reactivation only through the revision / cache mechanism.

## 11. Ordinary budget

The accepted ordinary budget, read live (`classroom_oracle.controller02.BUDGET` = `controller01.WATCHDOG`), expected 24 own
looks. An ACTIONABLE NORMAL entity at 24 own looks becomes `DEFERRED:ordinary_budget` (not BLOCKED, not QUIET, not
FINALIZED) and leaves NORMAL service pending RESIDUE. The budget is not changed.

## 12. RESIDUE semantics

When `schedule_normal` returns None and DEFERRED entities remain, the machine enters RESIDUE and processes them in ascending
id order: a DEFERRED entity whose current probe is QUIET is `FINALIZED:quiet_before_final_probe` with no gate call; one
whose current probe is ACTIONABLE passes its UNCHANGED cached ProbeResult to `final_look_gate_v1` — exactly here and
nowhere else — through the NS1e M2 gate adapter `ns1e_core.residue_gate_m2`, which mirrors the accepted
`ns1c2_core.residue_gate` with the M2 effective geometry in place of the map:
- the context is rebuilt from the record; the M2 effective geometry (same revision as the cached probe) is put in chart
  C_i; the probe is recomputed and must equal the cached probe exactly (else STOP);
- the accepted gate receives the cached ProbeResult, the recomputed FSG6f decision and the chart geometry, under the
  accepted NS1b adapter with the real fixed-head North-Star sensor (`ns1b_chart.north_star_sensor`) for its predicted
  observability (P3: local gaze → world gaze → real H0 sensor); never a fake local sensor.

A Cyclopean residue proposal may be rejected as `untraceable_final_support` by the accepted v1 semantics; no special case.
A rejected proposal is `FINALIZED:final_probe_rejected`. An admitted one executes at most one final residue observation
(`FINALIZED:final_probe_executed`). A final observation may change other entities' revisions and return the scene to
NORMAL; this is preserved.

**Gate-wiring harness (stage `gate-harness`, before the loop; no render).** On the frozen handoff state, the M2 gate
adapter is driven once for 202 (FSG6f proposal) and once for one Cyclopean-proposing entity (the lowest-id ACTIONABLE
Cyclopean entity at the handoff), in RESIDUE phase under the gate guard, on copies only. Required: recomputed probe equal
to the cached one; P3 called with the real H0 sensor at the mapped world gaze; the gate-guard record shows only RESIDUE
calls; NORMAL calls 0; the handoff state unchanged. The verdicts are recorded as wiring evidence only (no action is taken
and nothing enters the scene).

## 13. Live physical observation

For each genuinely new action, stage `schedule` freezes the controller plan BEFORE any render (`plan/decision.json` and
`freeze/plan-freeze.json` with the plan digest): global step, phase, scheduler decision and reason, target, proposal
source, local gaze, mapped H0 gaze, target revision, all service states, the map digest (sha256 of every entity map) and the
memory-ledger digest. `preflight` and `acquire` verify the plan freeze before Blender starts. Then exactly one binocular
observation (stage `acquire`, `tools/north_star/ns1e_render.py`, a thin driver over the accepted `ab1a_render` /
`ns1a_render` helpers exactly as `ns1c2_render`, accepting the plan kinds `attend` and `final_residue`):

    Classroom, static scene, fixed physical head; 640 x 640 per eye, nominal core 256 x 256, 12° core; IPD 0.063 m;
    vergence 2.10 m; OPTIX; 4096 spp; seeds L 2111 / R 2112; denoising OFF; adaptive sampling OFF; BOX filter 1.0;
    baseline_projected tangent convention.

The calibration built in Blender must be byte-identical to the planned one; the sealed instance catalog is written and
sealed (its seal must equal NS1a's) and never opened. A completed action is never re-rendered.

## 14. Local measurement path

    raw binocular observation -> accepted PERFECT / ORACLE correspondence (AB1b compute_oracle) -> freeze (truth-stripped
    product: left_core_row, left_core_col, uv_L, uv_R) -> accepted spherical epipolar metric geometry in H0 (AB1b
    compute_epipolar) -> freeze -> local ORACLE SEGMENTATION AID (instance_L at the exact uv_L; ns1a_core.attach_identity;
    only the instance_L member is read) -> freeze-identity

Position and Object Index are read by the PERFECT correspondence service only; the geometry stage reads only the
calibration and the frozen product; identity reads only `instance_L` after the geometry freeze. No SGBM, no natural
matcher, no planar persistent geometry, no broad oracle depth, no future visibility.

## 15. Active-target persistent fusion

For active target T: the frozen spherical measurements whose attached id == T, with their left-core RGB, as one target
patch (patch id `ns1e_step_KKK`, frame H0) fused ONLY into persistent map(T) with the accepted `ns1b_core.fuse_h0`
(accepted surface map; association radius 0.012 m; hash cell 0.012 m; accepted 100-point precondition; one exact replay —
idempotence required). Recorded: target measured points, map before, matched measurements, affected surfels, matched
distance median / p95 / max, new surfels, map after. No other entity's persistent map changes because of the observation.

## 16. All-instance measurement memory

From the same frozen spherical measurement, the accepted sparse 256 × 256 memory patch (`ns1d_core.memory_patch`, unchanged:
`xyz_h` the spherical H0 point, `valid` = finite geometry ∧ attached id > 0, `instance_id` the attached positive id) is
appended EXACTLY ONCE (`ns1d_core.MemoryLedger`, append-once by observation key, strictly in event order) with
`source_active_target_id` = T. Memory event indexing: accepted prior events 0..8; the first new NS1e observation is
memory event 9, then 10, 11, …; the mapping memory event ↔ NS1e global step is recorded separately (event e is global step
e − 1 in this run; the two are never confused). Every positive observed id is stored; instance 0 is excluded; ambiguous
ids may enter memory but never scheduler eligibility.

## 17. Own-look context update

Only the active target T receives an own-look context update (controller observation state, current gaze, calibration,
visited gaze, history, evidence), with the accepted inherited Classroom controller-time oracle matcher on the step's own
observation (`ns1b_core.matcher_state`, `ns1b_core.add_look` under the chart adapter), exactly as NS1c2. This controller
observation state is not part of the persistent geometry or memory path. No incidental observation enters another entity's
visited list, gaze, calibration, history or evidence; cross-target information reaches other entities only through memory
→ revision → re-probe.

## 18. Update order per physical action (frozen; checker-enforced)

    1 observation complete (acquire, freeze-observation)  2 correspondence frozen  3 spherical geometry frozen
    4 identity attached and frozen  5 active-target SurfaceMap fused (fusion freeze)  6 all-instance memory patch appended
    once (memory-event freeze)  7 measured-point counters updated (in the memory-event record)
    8 active-target own-look context updated  9 SceneMachine.commit  10 refresh of every service state under the new
    revisions  11 quiet / natural reactivation / deferral / local-state-change detection (the machine's events)

Stages 1–7 are separate processes that each refuse to run before their predecessor's freeze; `update` performs 8–11 in
that order, with ordered guard marks (`fusion_freeze_verified`, `memory_event_verified`, `context_updated`,
`commit_begins`, `refresh_complete`), and writes the scene checkpoint.

## 19. Natural reactivation and the rank-1 seam (observed, not forced, not fixed)

- **Natural reactivation.** When the accepted refresh emits `natural_reactivation` for B, NS1e records: B; the triggering
  target A; the memory event; the cross-target points of B added by that event; revision before / after; effective-geometry
  size before / after; probe before / after; the next proposal; and, later, whether and when B is serviced (scheduler reason
  `natural_reactivation`). No reactivation is forced; none is required.
- **Rank-1 seam.** The five rank-1 entities (9, 12, 204, 230, 231) have valid spherical maps but zero target support in
  their inherited planar controller initialization state. Not fixed. When each is first selected NS1e records: id, current
  own planar support, current M2 effective-geometry size, proposal source, selected local / H0 gaze. For every own look it
  records the North-Star spherical target measurement count and the controller-state target support count. Empty looks,
  premature quiet, repeated Cyclopean actions, deferral or residue caused by the seam are measured results.
- **Bootstrap cross-target memory: NOT PART OF NS1e.** The six untargeted NS1a bootstrap observations are not routed into
  memory.

## 20. Hard action cap — derived, not tuned

From the handoff machine (all ten NORMAL, initialized, fixations f_i ≤ budget B):

    MAX_NEW_PHYSICAL_ACTIONS = Σ_i (B − f_i) + |coherent|          (NORMAL looks up to B each; at most one final residue
                                                                    observation per entity, after which it is FINALIZED)
    expected: (24 − 9) + (24 − 2) + 8 · (24 − 1) + 10 = 15 + 22 + 184 + 10 = 231
    ABSOLUTE_ACTION_CAP = handoff global step + MAX_NEW = 8 + 231 = 239   (passed as decide(action_cap=239))

A reactivated entity does not invalidate the bound: its NORMAL looks are already counted up to B (an ACTIONABLE entity at B
is DEFERRED) and it has at most one final observation. Derived from the frozen state and the live budget; compared with
the expectation; a difference is a STOP. Reaching the cap before closure is INCOMPLETE (Control Outcome 2) and is never
permission to raise it.

## 21. Execution, checkpointing and resumability

Per new global step k (≥ 8), one directory `steps/step-KKK` (three digits) and one process per stage, each run once and
refusing to rerun: `schedule` (plan freeze) | `preflight` (Blender, no render) | `acquire` (Blender, the one render) |
`freeze-observation` | `perfect-correspondence` | `freeze-correspondence` | `spherical-geometry` | `freeze-geometry` |
`local-oracle-segmentation` | `freeze-identity` | `fuse` (fusion freeze) | `memory` (memory-event freeze) | `update` (scene
checkpoint `scene/state-after-step-KKK.json` and `freeze/checkpoint-step-KKK.json`). Host stages other than `preflight` /
`acquire` run under the accepted `NoProcessGuard` (no process, hence no Blender) and every stage under `OpenGuard`
allowlists. If `schedule` returns `closed` or `cap`, it writes `scene/terminal.json`; then `freeze-control` writes
`control/control-manifest.json` (`control_complete: true` or `control_incomplete_cap: true`) and `freeze/control-freeze.json`.

`loop` drives the steps from the last checkpoint. A restart (re)builds the accepted initial state, replays the completed
NS1e memory events read-only (the ledger is always rebuilt from all frozen patches and must equal the last checkpoint's
memory digest), restores the last frozen scene checkpoint and continues with the next action. It never re-renders a
completed action, re-appends a memory event or re-fuses a completed patch. If the next step directory exists without its
checkpoint (a partial or ambiguous action), `loop` STOPs and reports the completed stages; it never guesses.

## 22. Authorized cost

Luiz authorized this single canonical run up to its derived 231-new-action bound. Measured NS1c2 cost is about 40–46 s per
4096-spp action (PROPOSED for NS1e: about 1 min per action including stage processes and M2 probes; worst case about
4 h). The run is not stopped for exceeding the earlier interactive guideline. No spp reduction, denoising, renderer,
policy or budget change to save time. On a hardware / renderer failure: checkpoint, STOP, report.

## 23. Terminal semantics

The accepted machine may terminate with its generic `scene_closed` over its declared input universe. NS1e reports it
scientifically as **`COHERENT_SUBSET_CLOSED`** (the universe is the ten coherent entities only), never as a full-Classroom
closure, and never as global quiescence unless every final local state warrants it. At closure the report separates: QUIET
NORMAL entities; `FINALIZED:quiet_before_final_probe`; `FINALIZED:final_probe_rejected`; `FINALIZED:final_probe_executed`
but still locally ACTIONABLE; any other residual. Controller-02 `scene_closed` ≠ all objects quiet.

## 24. Control outcomes

- **Outcome 1 — honest coherent-subset closure** before the cap. **1Q:** all ten locally QUIET at terminal. **1R:** the
  honest closure contains one or more finalized residual ACTIONABLE entities. Both are valid; 1R is never retuned into 1Q.
- **Outcome 2 — hard cap** reached before closure: an incomplete coherent loop.
- **Outcome 3 — integration failure:** the handoff cannot be reproduced; a chart / sensor invariant fails; a duplicate memory
  append; the map / memory boundary violated; a renderer failure that prevents continuation; Controller-02 semantics
  diverge. STOP without tuning.

## 25. Truth firewall

During all controller operation (every stage before `freeze-control`) no stage may open: dense evaluation truth; the
Breadth-1 reference; any catalog or object name; future visibility; evaluation-only geometry. Enforced by the `OpenGuard`
allowlists and recorded guard events (the checker scans every control-stage record). Only after the terminal / cap state
is frozen and the control manifest says `control_complete: true` or `control_incomplete_cap: true` may the separate
`evaluate` process open reference truth. `evaluate` writes only under `evaluation/`; no control stage reads `evaluation/`;
control stages refuse to run after the control freeze.

## 26. Post-freeze full-sphere reference evaluation (stage `evaluate`)

Reference: the ACCEPTED Breadth-1 spherical glance `render/canonical.exr` (sha256 pinned; never re-rendered), read with the
accepted pure-Python `tools/exr_lite.py` (channels `Object Index.X` and `Position.XYZ` only; no metadata file, which holds
names, is opened): 720 × 360, 0.5° cell centres, fixed head, full-sphere first hit. Frame: the Breadth-1 pano was rendered
at the accepted head pose, which equals the North-Star calibration head pose exactly; `evaluate` re-verifies the frame by
the Breadth-1 orientation test (every authored cell's Position direction, mapped to H0 with the North-Star head pose
`p_H0 = (p_w − o_w) R_wh`, lies inside its declared 0.5° cell, Breadth-1 tolerance) before any coverage. Identity: the
Breadth-1 Object Index and the North-Star local oracle ids are the same accepted `_assign_instance_ids` assignment (NS1a's
post-freeze evaluation found its sealed catalog equal to the accepted Controller-01 catalog, which Breadth-1 used).

Only the ten coherent ids are evaluated. For id i: reference samples = cells with Object Index == i and finite, nonzero
Position. **Primary reconstruction: the final persistent SurfaceMap only.** A reference point is covered iff its
Euclidean distance to some final persistent surfel of i is ≤ 0.012 m (the accepted exact spatial-hash test
`classroom_oracle1_eval._covered`). Cell solid angles are the exact equirectangular weights (Breadth-1 `row_weights`,
Σ = 4π). Per id: reference cells, reference solid angle, covered / uncovered cells, cell-count and solid-angle-weighted
coverage fractions, final persistent surfels, own looks, terminal state. An id with zero 0.5° reference samples is
`NO_0P5_DEG_FIRST_HIT_REFERENCE` (never zero coverage). Aggregates: micro cell coverage and solid-angle-weighted micro
coverage over the ten. **Diagnostic (clearly labelled `MEASURED EFFECTIVE GEOMETRY — NOT PERSISTENT RECONSTRUCTION`):** the
same test against final persistent map + final measurement memory of i.

## 27. The historical 98.34 % (do not overclaim)

Controller-01's evaluation measured 28,801 / 29,288 = 98.34 % within 12 mm (ACCEPTED HISTORICAL REFERENCE): dense 0.25°
cyclopean first-hit samples inside the old controller angular domain over the 25 localized objects. NS1e's primary
definition is the accepted 0.5° whole-sphere first-hit reference over the ten coherent North-Star entities. Same 12-mm
criterion; different angular sampling, object universe and angular domain. The two scalars are **NOT numerically
comparable**; no better / worse claim is made; 98.34 % appears only as architectural context.

## 28. Scientific visuals (Visual Language 1)

`VIS/overview.png`: **A** start state (ten coherent entities in canonical H0; current 202; the accepted NS1d M2 memory; the
next action 202 FSG6f (−10.9°, +10.5°) mapped to H0); **B** the full attention timeline (target vs global action; retain,
switch, natural reactivation, QUIET, DEFERRED, RESIDUE, FINALIZED; FSG6f vs Cyclopean by non-colour glyphs); **C** map +
memory growth per entity (persistent map, own memory, cross-target memory, effective geometry); **D** reactivations, or
`NO NATURAL REACTIVATION MEASURED`; **E** terminal state (generic Controller-02 terminal; scientific label
`COHERENT_SUBSET_CLOSED` or `INCOMPLETE_CAP`; ten per-entity rows); **F** post-freeze coverage (persistent map; effective
geometry separately; 98.34 % only as `NON-COMPARABLE HISTORICAL REFERENCE`). Supporting: `controller-full-timeline.png`,
`multi-entity-final-geometry.png`, `memory-flow-timeline.png`, `coverage-by-entity.png`, `rank1-diagnostic.png`;
`natural-reactivation.png` if a reactivation occurs; `residue-phase.png` if RESIDUE occurs. Exports:
`final-coherent-persistent-points.ply` (the ten persistent maps only, with an entity-id vertex attribute, deterministic
order; no memory sample) and the explicitly labelled `final-effective-geometry-diagnostic.ply`. Truth badges, frame labels,
the fixed-head statement, oracle labels and `visuals-manifest.json`; ids 10 / 110 / 178 labelled `AMBIGUOUS ORACLE ID —
EXCLUDED`; memory is never drawn as fused geometry. Figures regenerate byte-identically.

## 29. Checker (`tools/north_star/check_ns1e.py`) and synthetic known answers

Own literal pins; independent recomputation wherever an independent formula exists. Families (mandate B30): PROVENANCE;
HANDOFF (independent ledger rebuild; machine fields; next decision); ELIGIBILITY; CHARTS (recomputed; every probe's adapter
used the fixed chart); PHYSICAL SENSOR (every calibration: fixed head, real world sensor, not fake); CONTROLLER (an
independent re-drive of the accepted SceneMachine from the handoff with the recorded probe results and independently
recomputed revisions reproduces every decision, event and checkpoint machine; NORMAL gate calls 0; budget 24; no manual
reactivation); PROBES (fresh probes recomputed from context and M2 geometry, tolerance 0); OBSERVATION (one plan freeze
before each render; one render per step; spp, seeds, device, filter, denoise, adaptive); MEASUREMENT (freeze order;
geometry recomputed; identity re-attached; no Position in geometry / identity / fusion / memory); FUSION (re-fused
bitwise; target only; 12 / 12 mm; idempotent; maps hold only their own id and own patch ids); MEMORY (patches rebuilt from
products bitwise; append once; provenance; event ↔ step mapping; all positive ids; no id 0; never fused); CONTEXT (only the
target gains a look); ORDERING (process order and guard marks); REACTIVATION (adapter events only); RESIDUE (only after
NORMAL exhaustion; gate only in RESIDUE; unchanged proposal; real H0 sensor; ≤ 1 final observation per entity); CAP;
CHECKPOINTING; TRUTH FIREWALL; EVALUATION (after the control freeze; Breadth-1 hash; persistent map primary; memory only in
the diagnostic; exact 12 mm recomputed independently); TERMINOLOGY (`COHERENT_SUBSET_CLOSED`, never full-Classroom
closure; 98.34 % never comparable; no ACCEPTED marker); VISUALS; MANIFEST and declared changes. `ns1e_synthetic.py`
provides fail-capable synthetic known answers (each with a negative control) for the ledger, the revision, the cap bound,
resume equivalence, revision-only reactivation, gate-only-in-RESIDUE, the residue procedure, partial-step refusal, the
coverage function, the solid-angle weights, the world → H0 transform and the PLY export.

## 30. Corruption suite (`tools/north_star/check_ns1e_corruptions.py`)

From a passing baseline after an unmodified-mirror null probe; mirrors with large arrays symlinked and unlinked before any
write; RUN and VIS hashed before and after. At least the mandate's B31 families: START STATE (drop memory event 8; change
the current target; revert 202's map; revert 172's own looks; change the next action); MEMORY (route by active id; discard
cross-target ids; append twice; include id 0; fuse cross-target memory; alter revision semantics); CONTEXT (incidental gaze
in another visited list; another entity's evidence altered); CONTROLLER (gate Cyclopean in NORMAL; gate FSG6f in NORMAL;
change scheduler order; change budget; block instead of defer; manual reactivation); CHART (dynamic recenter; map-centroid
centre; transposed transform); PHYSICAL SENSOR (move head; rotate baseline; change IPD; fake local calibration); RENDER
(change spp; enable denoise; re-render a completed action); MEASUREMENT (SGBM; planar persistent geometry; Position read
before the freeze); FUSION (change 12 mm; cross-id fusion; fuse memory points); RESIDUE (enter while NORMAL service exists;
gate outside RESIDUE; modify the proposal before the gate; two final observations for one entity); CAP (increase; ignore);
CHECKPOINT (duplicate a completed action; reuse a memory-event id; continue from a partial action); EVALUATION (reference
truth opened before the control freeze; memory in the primary coverage; another radius; 98.34 % called comparable);
VISUAL (oracle labels hidden; memory called fused geometry; full-Classroom closure claimed). A corruption that cannot apply
to the executed trace (e.g. a RESIDUE corruption when RESIDUE never occurred) is recorded NOT APPLICABLE with the reason,
never counted as caught, and is exercised on the synthetic residue fixtures instead.

## 31. Commands, order and cost

    RUN=/home/lvelho/rd/f3d-vision/previews/north-star/ns1e-coherent-full-loop-m2-memory
    VIS=/home/lvelho/rd/f3d-vision/visuals/north-star/ns1e-coherent-full-loop-m2-memory
    .venv/bin/python tools/north_star/ns1e_run.py source        --run $RUN   # interactive
    .venv/bin/python tools/north_star/ns1e_run.py synthetic     --run $RUN   # interactive
    .venv/bin/python tools/north_star/ns1e_run.py handoff       --run $RUN   # interactive; HARD STOP point; no render
    .venv/bin/python tools/north_star/ns1e_run.py gate-harness  --run $RUN   # interactive; no render
    .venv/bin/python tools/north_star/ns1e_run.py loop          --run $RUN   # authorized batch (hours); to terminal / cap
    .venv/bin/python tools/north_star/ns1e_run.py freeze-control --run $RUN  # (called by loop at the terminal)
    .venv/bin/python tools/north_star/ns1e_run.py evaluate      --run $RUN   # batch; post-control, separate process
    .venv/bin/python tools/north_star/ns1e_run.py visualize     --run $RUN --visuals $VIS
    .venv/bin/python tools/north_star/check_ns1e.py --run $RUN --visuals $VIS --corruptions --write-summary   # batch

Every canonical stage runs once, from one clean pushed implementation commit, and refuses to rerun. No parameter sweep, no
alternate controller, no retry with tuned thresholds, no second canonical run.

## 32. Permitted fix scope

- **Before the canonical run** (`handoff` onwards on the canonical RUN): implementation defects in the NS1e tools, without
  changing sections 5–27 or a declared tolerance. Development uses the synthetic fixtures, scratch development runs (never
  the canonical RUN), the handoff on a scratch run, and the factory-startup rehearsal scene for render plumbing (never a
  Classroom render outside the canonical run). No development result is reported as measured.
- **After the canonical run starts:** (a) a host-side stage that fails from an implementation defect before writing any
  scientific output may be repaired minimally, its failed attempt's records preserved under `incidents/`, and run for its
  first scientific time (recorded as an incident; never a render stage after Blender began rendering); (b) presentation-only
  figure fixes; (c) a checker or corruption-suite defect that false-alarms on correct data, only if the fix does not weaken
  the check (recorded).
- Anything else — a re-render, a different policy / scheduler / budget / gate / chart / sensor / fusion / memory rule, an
  edit of `fov3d/` or of an accepted tool, bootstrap memory, ambiguous ids in scheduling, a rank-1 fix, foreground /
  background modelling, head motion, natural stereo — is a STOP for Luiz and Chat.

## 33. Stop conditions

STOP and report if: a provenance or pin check fails; `synthetic` fails; the derived eligibility, charts or cap differ from
their expectations; the handoff does not reproduce the accepted state or next decision exactly; a guard records a
violation or an unexpected process; a stage would run twice; a step directory is partial or ambiguous; a NORMAL gate call
occurs; a persistent map other than the target's changes; a memory event is duplicated or skipped; a renderer / hardware
failure prevents continuation; a canonical check fails for a reason other than a checker defect. Reaching the terminal or
the cap is not a failure: freeze and evaluate.

## 34. Report and stop

`docs/north-star/ns1e-coherent-full-loop-m2-memory-report.md`, status REVIEW PENDING, marker
`NORTH_STAR1E_COHERENT_FULL_LOOP_M2_MEMORY_COMPLETE`, no ACCEPTED marker, with the 31 sections of the mandate's B33 and the
final unresolved decision: IS THE COHERENT NORTH-STAR CONCEPT DEMO NOW COMPLETE ENOUGH TO MOVE TO THE NEXT CLASSROOM /
IDENTITY / BACKGROUND STAGE? Then STOP: no acceptance, no merge, no other scene, no ambiguous ids, no bootstrap memory, no
rank-1 repair, no foreground / background modelling, no change to FSG6f, Cyclopean, Controller-02, the scheduler, the
budget or the gate, no natural stereo, no head motion.

## 35. What NS1e may and may not establish

May establish: how the assembled North-Star system (fixed head, fixed charts, accepted local control, PERFECT
correspondence, spherical H0 geometry, target-only fusion, M2 cross-target memory, Controller-02 phases) governs the
coherent ten-entity Classroom subset on its own to an honest terminal; its trajectory, reactivations, deferrals, residue
decisions, terminal composition and the post-freeze 12-mm coverage of its persistent maps on the accepted 0.5° reference.

May NOT establish: full-Classroom closure or global quiescence; anything about ids 10 / 110 / 178, bootstrap cross-target
memory, natural correspondence or natural identity, background modelling, head motion, other scenes; a numerical
comparison with Controller-01's 98.34 %.

## 36. Amendment before implementation (development findings; committed before the implementation commit)

Two clarifications found while developing on scratch runs (synthetic fixtures, the handoff and the gate-wiring harness on
copies of the frozen state, and the factory-startup rehearsal room). Neither changes a scientific rule of sections 5–27;
where they differ, the sentences below supersede the corresponding sentences of sections 12 and 21.

1. **Gate-wiring harness, P3 requirement (section 12).** The accepted `final_look_gate_v1` traces an FSG6f proposal and
   predicts its observability (P3), but rejects a Cyclopean proposal as `untraceable_final_support` before any predicted
   calibration. The harness therefore requires: every P3 call the gate makes uses the real fixed-head H0 sensor at the
   mapped world gaze (never the fake local-baseline sensor); the FSG6f proposal is traced (at least one P3 call); the
   Cyclopean proposal makes no P3 call and is rejected `untraceable_final_support`. Development measurement on copies of
   the handoff state: 202 FSG6f (−10.9°, +10.5°) admitted (`novel_support_in_predicted_cores`, one real-sensor P3 call);
   9 Cyclopean (−6.0°, −2.1°) rejected (`untraceable_final_support`, no P3 call). These are wiring evidence only.
2. **Process guards (section 21).** The accepted `NoProcessGuard` lives in the Classroom Controller-02 module, whose import
   loads the controller stack (cv2, `fsg_stereo`, FSG6f). The measurement stages must show that no such module is loaded
   (the accepted NS1c2 freeze checks). Therefore the policy stages (`source`, `handoff`, `gate-harness`, `schedule`,
   `update`, `freeze-control`, `evaluate`) run under the accepted `NoProcessGuard`, and the measurement, fusion and
   memory stages (`freeze-observation` through `memory`) run under `ns1e_core.ProcessGuard`, the same audit-hook
   mechanism with exactly the accepted guard's audit events (checker-verified), which imports no controller module.
3. **Checkpoint completion (section 21).** A step is complete only when its checkpoint freeze
   `freeze/checkpoint-step-KKK.json` exists; `update` computes every hash it records before it writes any output, and
   `loop` resumes after the last checkpoint freeze. The planar controller-state target support of each entity's last own
   look at the handoff is carried from the accepted NS1c2 records (`contexts/contexts.json` diagnostics or the step's
   `update/update.json`), pinned through the NS1c2 manifest.
