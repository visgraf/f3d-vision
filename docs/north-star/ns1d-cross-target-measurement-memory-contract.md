# North Star-1d — Controller-Phase Cross-Target Measurement Memory — contract

**Status: CONTRACT (committed before any NS1d implementation commit, before any NS1d memory patch is built, before any
NS1d probe and before the causal replay).** Completion marker (written only by the report):
`NORTH_STAR1D_CROSS_TARGET_MEASUREMENT_MEMORY_COMPLETE`. No ACCEPTED marker is written by Claude Code.

Decision context (recorded on `main` at `3720d74`): North Star-1c2 is ACCEPTED as Outcome 1 — natural quiet switch
(acceptance `5fe0684`, `NORTH_STAR1C2_CONTROLLER02_PHASE_SEMANTICS_ACCEPTED`). Correct multi-entity NORMAL controller
semantics and a genuine natural scene switch are established. NS1d restores the causal measurement-memory mechanism of
the accepted Controller-01 before the full multi-entity North-Star loop is released.

**NS1d is NOT the full multi-entity run. It is a NO-NEW-RENDER causal replay.** No Blender, no GPU render, no new
observation, no new controller action, no SGBM, no image acquisition.

## 1. One causal question

> If the accepted instance-keyed measurement-memory mechanism is restored using the already measured North-Star
> controller-phase observations, does cross-target metric evidence alter any entity's effective geometry, revision, local
> service probe or next controller decision relative to the accepted NS1c2 target-only trace?

The single independent variable relative to accepted NS1c2 is **the policy geometry and revision of each entity**:

| | accepted NS1c2 (M0) | NS1d architecture under test (M2) |
|---|---|---|
| policy geometry of entity i | persistent H0 map of i | `effective_target_geometry(map_xyz(i), memory.snapshot(i).xyz_h)` |
| revision of entity i | (own looks, map surfels) | (own looks, measured points of observed id i) |
| an observation of A that sees B | changes nothing for B | adds B's samples to the memory: B's effective geometry and revision change; B is re-probed |

Everything else stays frozen: the coherent set, the charts, the contexts, FSG6f, Cyclopean, Controller-02 (the accepted
`schedule_normal` and the NS1c2 resumable adapter), `final_look_gate_v1` (RESIDUE only), the 24-look ordinary budget,
target-only persistent fusion, the fixed physical head, the PERFECT correspondence, the spherical geometry and the oracle
segmentation aid. The experiment replays the ALREADY MEASURED NS1b / NS1c2 controller-phase observations in their
accepted order and **stops at the FIRST controller-decision divergence**, or after the complete accepted NS1c2 trace.

The chain:

    accepted NS1c2 initial state (= accepted NS1b post-action scene state)
      -> historical known answer: the accepted Controller-01 memory, rebuilt from its saved patches  (section 9)
      -> synthetic known answers                                                                    (section 10)
      -> the frozen list of UNIQUE controller-phase physical observations                          (section 6)
      -> memory event 0 (the accepted NS1b action on 172) appended; M0 / M1 / M2 initial tables     (section 13)
      -> for each accepted NS1c2 step: compare the M2 next action with the accepted one;
         if equal: replay the step read-only, append its ONE all-instance memory patch,
         re-probe every entity whose revision changed                                              (section 14)
      -> STOP at the first M2 action divergence, or after step 7                                   (section 15)

## 2. Provenance and branch

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (the legacy `fov-3d-vision` is never used) |
| base (`main`: post-NS1c2 roadmap) | `3720d745558bcbadb1c9edb3ffad5aaf0d86b3bb` |
| NS1c2 acceptance | `5fe0684bae6ab4bc8a2080b1a93089fdb2a935af` (`NORTH_STAR1C2_CONTROLLER02_PHASE_SEMANTICS_ACCEPTED`) |
| NS1c2 implementation / report | `0c83bb0` / `ff6ab3c` |
| NS1b acceptance / NS1a acceptance | `255355108863022f931574dae4b2df8cdd2a772e` / `37c7e026f2ab514be392cd845d390fab2a2d86fc` |
| NS1c diagnostic source (NOT accepted, NOT merged) | report head `4107be86228c970f4b82fb6d5343365c551f36b0`; its run is the measured source of NS1c2 steps 0–3 (read-only) |
| branch | `north-star/ns1d-cross-target-measurement-memory`, from the base, in an isolated worktree |
| run (`RUN`, machine evidence) | `/home/lvelho/rd/f3d-vision/previews/north-star/ns1d-cross-target-measurement-memory/` |
| visuals (`VIS`, persistent) | `/home/lvelho/rd/f3d-vision/visuals/north-star/ns1d-cross-target-measurement-memory/` |

The implementation commit writes this contract's commit SHA into `ns1d_spec.CONTRACT_COMMIT` and the checker's literal;
the checker requires this file to be unchanged from that commit to the checked tree.

Frozen inputs (sha256; a mismatch is a STOP; every one listed in full in `ns1d_spec`):
- NS1c2 run `previews/north-star/ns1c2-controller02-phase-semantics/`: `manifest.json`
  `0ec6228d96db1bfadc3372c3ce95342ddfa14f7ba2f11d24234c20ed59d2c8c1` (279 run files; every NS1c2 file NS1d reads must
  equal its manifest entry), `check-summary.json` `dae0671d…`, `freeze/scene-freeze.json` `ea5d0465…`.
- NS1c run `previews/north-star/ns1c-coherent-first-scene-switch/`: `manifest.json` `90e2dd4b…` (steps 0–3 products).
- NS1b run `previews/north-star/ns1b-recentered-controller-handoff/`: `manifest.json` `e859fa61…`.
- NS1a run: the pins inherited from NS1c2 (the seed handoff is read only through NS1c2's contexts).
- Accepted code, unchanged (sha256 at the base): `fov3d/reconstruction/measurement_memory.py` `27471ebf…`,
  `fov3d/control/{controller02,integrated}.py`, the Classroom Controller-01 / Controller-02 adapters, FSG6f, Cyclopean,
  `surface_map`, and the accepted NS1a / NS1b / NS1c2 tools NS1d imports (`ns1b_chart`, `ns1b_core`, `ns1b_fixtures`,
  `ns1c2_core`, `ns1c2_phase`, `ns1c2_spec`, `ns1c2_synthetic`, `ns1a_core`).
- Accepted Controller-01 run `previews/controller-01-full/` (ACCEPTED HISTORICAL REFERENCE; name-free files only: the 25
  `trajectory.partial.json`, the 141 saved oracle patches `objects/instance_*/patches/fix_NN.npz`, the 25
  `final_effective_geometry.npz` and `final_map.npz`, and object 109's three own acquisitions for the reactivation replay)
  and accepted Controller-02 `events.json` `fae7e648…`. `actions.json`, `result.json`, `manifest.json`, catalogs, seeds
  and evaluation files carry names or evaluation truth and are never opened.

## 3. Pre-contract activity (disclosed)

Before this commit only accepted code, reports and recorded run products were read; nothing was probed, no memory patch
was built, nothing was replayed or rendered:
- Read: `fov3d.reconstruction.measurement_memory`, `fov3d.control.{controller02, integrated}`, the Classroom
  Controller-01 adapter (its `InstanceMeasurementMemory` use, `geometry`, `revision`, `remember_measurements`), the
  Controller-01 / Controller-02 reports, the NS1b / NS1c2 contracts, reports and tools.
- Read from recorded products (MEASURED by NS1b / NS1c / NS1c2; used here only as expectations): the per-step
  `segmentation/identity-summary.json` of the nine controller-phase observations; the NS1c2 step decisions and scene states;
  Controller-02 `events.json` (object 109: `quiet` at global step 4 with 6,166 effective points and Cyclopean
  `attention_complete` / eligible 0; `natural_reactivation` at step 7, trigger 110, 6,170 effective points, Cyclopean
  `epistemic_fixation` / eligible 28, proposal (−7.0°, 14.1°)).
- Recorded identities in view (expectation, re-derived at run time from the arrays): every look sees 172 or 202 (the
  target) and the multi-part id 110; besides those, coherent ids appear only at NS1c2 step 5 (212: 22,399 points; 129: 777)
  and step 7 (212: 15,798; 123: 5,779); other non-scheduler ids appear (125, 126, 144, 2, 207). Consequently, for every
  coherent entity, M1 and M2 coincide until the memory receives NS1c2 step 5's observation.
- Two `check_ns1c2.py` runs (on the NS1c2 acceptance tree and the post-acceptance roadmap tree) recorded in the NS1c2
  acceptance and roadmap commits.

## 4. NS1c2 acceptance (pointer)

NS1c2 is ACCEPTED (report `docs/north-star/ns1c2-controller02-phase-semantics-report.md`, acceptance record). Its trace
(8 NORMAL actions: 172 retained at steps 0–6, natural QUIET at 9 own looks, `schedule_normal` switch 172 → 202 at step 7)
is the M0 baseline NS1d must reproduce exactly. NS1c remains REVIEWED, NOT ACCEPTED and NOT MERGED.

## 5. The historical mechanism being restored (ACCEPTED HISTORICAL REFERENCE)

Accepted Controller-01 (`fov3d/experiments/classroom_oracle/controller01.py`, unchanged):
- every completed controller observation produces ONE measured patch (`xyz_h`, `valid`, `instance_id` on the 256 × 256
  core);
- `remember_measurements` appends it ONCE to the global `InstanceMeasurementMemory` with `source_global_index = step` and
  `source_active_target_id = target`; every finite valid positive-instance sample is routed by the OBSERVED instance id,
  independently of which entity was active; samples are append-only; duplicates are retained;
- `measured_points[i]` accumulates the additions for observed id i;
- the policy geometry of entity i is `effective_target_geometry(map_xyz(i), memory.snapshot(i).xyz_h)` (map first, then
  measured samples; no deduplication, no weighting, no fusion);
- `revision(i) = (own looks, measured_points[i])`; the scene loop's probe cache is keyed by revision, so a cross-target
  addition invalidates B's cached probe and B is re-probed at the next refresh; a QUIET B that becomes ACTIONABLE emits
  `natural_reactivation` (there is no reactivation operation);
- a cross-target observation is NOT an own-target look: it never enters B's `history`, `visited`, `evidence`, gaze,
  calibration or controller observation state, and never fuses into B's persistent map.

Literal pins (accepted Controller-01 report): 141 looks; the memory holds 7,843,577 points in 33 observed instances; over
the 25 localized objects 2,274,857 own-target and 5,494,429 cross-target points (70.7 %); 8 unlocated instances measured
incidentally (74,291 points); 2 natural reactivations (109 by 110's look at step 7, 4 cross-target points; 178 by 224 at
step 114).

**Memory is not map fusion.** Persistent maps stay exactly as in the accepted North-Star runs (target-only fusion).
Effective controller geometry = persistent map + measured-instance memory. No new deduplication, no confidence weighting,
no cross-id fusion, no map rewrite.

## 6. Controller-phase scope and the source events

**Scope.** NS1d restores memory from the ACTIVE CONTROLLER phase only. The six untargeted NB1c bootstrap gazes (NS1a) were
attention actions, not object-targeted controller actions; several entities were initialized from one gaze; the accepted
memory provenance requires a positive active target. Therefore:

    BOOTSTRAP CROSS-TARGET MEMORY: NOT DECIDED BY NS1d.

The NS1a persistent maps and own-look contexts remain the initial bootstrap state. This is a deliberate scope boundary.
(It is also an asymmetry for 172: its own memory contains its NS1b and NS1c2 looks, not its NS1a bootstrap look; this
is reported.)

**Events.** Stage `events` derives a frozen ordered list of UNIQUE PHYSICAL CONTROLLER OBSERVATIONS from the accepted
records only (JSON records and manifests; no array is opened): the accepted NS1b action, then every executed NS1c2 action
in global-step order, each with its observation source as recorded by NS1c2's fusion record. Expected (verified, never
silently hard-coded):

| memory event | source | NS1c2 global step | active target | H0 gaze (accepted) | observation products |
|---|---|---|---|---|---|
| 0 | NS1b action 1 (`ns1b_action_01`) | — | 172 | (−155.008°, +33.636°) | NS1b run |
| 1–4 | NS1c2 steps 0–3 (NS1c measured, replayed read-only) | 0–3 | 172 | (−147.585, +37.246), (−145.704, +42.032), (−143.516, +46.782), (−150.152, +48.188) | NS1c run steps 0–3 |
| 5–7 | NS1c2 steps 4–6 | 4–6 | 172 | (−163.040, +31.040), (−163.874, +26.094), (−153.654, +39.235) | NS1c2 run steps 4–6 |
| 8 | NS1c2 step 7 | 7 | 202 | (−151.282, +22.052) | NS1c2 run step 7 |

Expected: 9 events. For each event the list pins the active target, the physical H0 gaze, the observation-freeze,
correspondence-freeze and geometry-freeze record hashes, the hashes of the correspondence product, the geometry result
and the local identity attachment (manifest entries), and the accepted target-map result hash. The checker requires 9
distinct observation-freeze records (no physical observation counted twice), targets [172 × 8, 202], and no NS1a
bootstrap gaze.

## 7. The North-Star spherical memory patch

For memory event e, built ONLY when e is consumed (section 14), from already frozen products only:
- the accepted truth-stripped PERFECT correspondence product (`left_core_row`, `left_core_col`, `uv_L`, `uv_R`);
- its accepted spherical H0 geometry (`P_epi`, `valid_epi`; DERIVED SPHERICAL GEOMETRY, canonical fixed-head H0);
- AFTER the geometry freeze, the accepted local ORACLE SEGMENTATION AID identity attached at the left raw-core sample
  (`segmentation/local-identity.npz`: `instance_L` at the exact `uv_L`; −1 where the geometry is invalid).

One sparse 256 × 256 core raster per event:
- `xyz_h[r, c]` = `P_epi` (float32, the accepted memory dtype) at measured left-core cells `(left_core_row,
  left_core_col)`, NaN elsewhere;
- `instance_id[r, c]` = the attached local positive id, 0 elsewhere (−1 and 0 map to 0);
- `valid[r, c]` = geometry exists AND XYZ finite AND attached id > 0.

The cells are unique (one correspondence per left core cell; checked). Required:
`valid.sum() == #{finite positive-id spherical measurements of the event}`. No Position, no planar persistent geometry,
no SGBM, no right-side identity lookup beyond the accepted perfect-correspondence semantics, and no reference
observation (Position / Object Index) is opened by any NS1d replay stage: the identity is the frozen accepted attachment.

## 8. The accepted memory class, unchanged; memory identity vs scheduler identity

`fov3d/reconstruction/measurement_memory.py` is used unchanged (pinned; never edited). One `InstanceMeasurementMemory()`;
for each consumed event e: `memory.append_patch(patch_e, source_global_index=e, source_active_target_id=target_e)`. The
memory's `source_global_index` is the MEMORY EVENT INDEX 0..N−1, never the NS1c2 global step; the map event → (source
run, NS1c2 global step, H0 gaze) is recorded separately. After every append the run records and the checker verifies:
the additions by observed id (= the per-id counts of the patch), the total, snapshot alignment (`xyz_h`,
`source_global_index`, `source_active_target_id` of equal length), provenance values, and append determinism (an
independent rebuild from the saved patches gives identical snapshots).

**Memory identity** = the observed positive local oracle id: the memory stores EVERY positive observed id — coherent
scheduler ids, the ambiguous oracle identities 10 / 110 / 178, and ids never initialized by NS1a. **Scheduler identity**
= the frozen COHERENT_SEED_SET {9, 12, 123, 129, 172, 202, 204, 212, 230, 231} only. A memory id never becomes a
scheduler input; scheduler eligibility is unchanged. No object names, no global catalog.

## 9. Historical known answer (stage `known-answer`; before any North-Star data is used)

A direct replay over the accepted Controller-01 saved name-free products, with the accepted class:
1. **Memory rebuild.** All 141 saved oracle patches, in global-step order, appended with `source_global_index = global
   step` and `source_active_target_id = target`. Required: every append's additions equal the logged
   `measurement_memory_additions` of that look (141 / 141); total 7,843,577 points in 33 observed ids; own / cross over the
   25 localized objects 2,274,857 / 5,494,429 (70.7 %); 8 unlocated ids with 74,291 points; for each of the 25 objects the
   memory snapshot provenance equals its saved `final_effective_geometry.npz` (`measured_source_global_index`,
   `measured_source_active_target_id`), and `effective_target_geometry(final_map, snapshot)` equals its saved `xyz_h`
   (float32, exact) — map first, measured second; duplicates retained.
2. **The 109 reactivation.** With the accepted NS1b replay routine (`ns1b_fixtures.rebuild`, unchanged): 109's
   own-target context and effective geometry after global step 4 and after step 7. Required: the measured-point revision
   changes, by exactly 4 samples whose `source_active_target_id` is 110 and `source_global_index` is 7; 109's own looks
   (3) and persistent map are unchanged between the two; the accepted probe (`controller01.probe_local_policy`, the
   Controller-01 chart, no adapter) gives after step 4 a summary equal to the accepted `quiet` event's probe (QUIET;
   6,166 effective points; FSG6f `no_frontier`; Cyclopean `attention_complete`, eligible 0) and after step 7 one equal to
   the accepted `natural_reactivation` event's `probe_after` (ACTIONABLE; 6,170 points; Cyclopean `epistemic_fixation`,
   eligible 28, proposal (−7.0°, 14.1°)), exactly (tolerance 0); the cached quiet probe is invalidated by the revision
   change (an accepted adapter re-drive with this probe / revision pair emits `natural_reactivation`, trigger 110).
3. **Scheduler.** The accepted Controller-02 history re-drive (`ns1c2_synthetic.historical_trace`, unchanged) shows 109's
   later service as a switch with reason `natural_reactivation` (global step 134) and 2 natural reactivations in total.

Nothing is fabricated: if any required saved product is missing, the stage STOPs.

## 10. Synthetic known answers (stage `synthetic`)

Exact, fail-capable fixtures (each with a negative control) for: (1) one multi-id patch → exact per-id counts; (2) aligned
snapshot XYZ / global index / active target; (3) a duplicate append retains duplicates; (4) `effective_target_geometry`
order: map first, measured second; (5) a cross-target point changes the M2 revision of the observed entity; (6) it does
not change that entity's persistent map; (7) it does not enter that entity's own-look context; (8) M1 ignores
cross-target additions; (9) M2 includes them; (10) the revision change invalidates the cached probe in the accepted
adapter (re-probe count); (11) no manual reactivation: the reactivation arises only through the adapter's refresh;
(12) the historical 109 fixture (section 9); (13) the sparse spherical raster: valid count equality; (14) instance 0 and −1
excluded; (15) every positive observed id retained, even outside the scheduler; (16) ambiguous ids stored in memory but
never scheduler inputs; (17) one physical observation appended exactly once (a double append is detected); (18) source
provenance carries the active target; (19) process guard: a Blender invocation is refused; (20) action divergence: the
replay driver stops immediately and never consumes a later observation.

## 11. Three read-only geometry modes

| mode | role | geometry(i) | revision(i) |
|---|---|---|---|
| **M0** | ACCEPTED NS1c2 BASELINE | persistent H0 map only | (own looks, map surfels) — the accepted NS1c2 revision |
| **M1** | OWN-MEASUREMENT MEMORY CONTROL (diagnostic only) | `effective_target_geometry(map, snapshot(i).xyz_h[source_active_target_id == i])` | (own looks, own-target measured points of i) |
| **M2** | FULL ACCEPTED MEMORY SEMANTICS (architecture under test) | `effective_target_geometry(map, snapshot(i).xyz_h)` | (own looks, measured_points[i]) |

All geometries are formed in canonical H0 and passed to the accepted NORMAL probe (`ns1c2_core.probe_normal_ctx`: the
accepted `controller01.probe_local_policy` under the accepted NS1b frame adapter and the entity's fixed chart; no gate).
The context of an entity is its accepted NS1c2 own-look record, identical in all three modes. No physical acquisition in
any mode.
- M0 must reproduce the accepted NS1c2 probes (policy part, tolerance 0) and every accepted NS1c2 decision exactly;
  otherwise Outcome 4.
- M0 and M2 are driven by the accepted resumable Controller-02 adapter (`ns1c2_phase.SceneMachine`, unchanged), resumed
  as NS1c2 resumed it (current 172, bout 1, own fixations, all initialized), with their own probe and revision callbacks
  (the adapter's probe cache keyed by the mode's revision). M1 is a stateless diagnostic: its statuses come from its own
  probes (cached by M1 revision) and its decision is the accepted `schedule_normal` over them, with the accepted current
  object.
- The ordinary budget (24) is not reachable in this trace (at most 9 own looks); the deferral rule is evaluated anyway.

## 12. Map / memory / context separation (load-bearing)

- Persistent maps: only the active target's accepted target-only patch is fused, reproducing the accepted NS1c2 fused
  map bitwise (re-fused with the accepted `ns1b_core.fuse_h0` from the accepted target patch, whose XYZ must equal the
  target subset of the event's memory patch). Every other map is unchanged at every event; a map never holds another id
  or another target's patch id.
- Own-look context: only the active target gains a look, taken from the accepted NS1c2 entity record after that step;
  every other entity's looks, visited gazes, evidence, current gaze and calibration are unchanged.
- Cross-target information enters B only through its M2 effective geometry and its M2 revision (cache invalidation).

## 13. Initial memory state (stage `replay`, first part; B11)

From the accepted NS1c2 initial scene state (10 coherent contexts; 172 map 21,243 surfels; the other nine their NS1a seed
maps), append memory event 0 only. For every coherent id record: M0 / M1 / M2 geometry size; memory points own / cross;
revision M0 / M1 / M2; probe M0 / M1 / M2 (state, source, local / H0 proposal, FSG6f and Cyclopean summaries). Then
compute the next scene decision in each mode and compare it with the accepted NS1c2 step-0 action. If M2 changes it: this
is the FIRST CAUSAL DIVERGENCE — freeze and STOP; no later observation is consumed.

## 14. Sequential causal replay (stage `replay`; B12)

For accepted NS1c2 steps k = 0..7, with memory holding events 0..k:
1. require the M2 next action to equal the accepted step-k action (target, `schedule_normal` retain / switch, proposal
   source, local gaze, mapped H0 gaze; section 15);
2. consume event k+1 (step k's observation) read-only: verify its products against their pins;
3. reproduce the accepted target-only map update exactly (section 12);
4. append its ONE all-instance memory patch;
5. recompute measured points;
6. update revisions for every observed eligible entity;
7. commit the step in the M0 and M2 adapters (fixations, refresh: a fresh probe exactly where the mode's revision changed,
   the cache elsewhere; events);
8. compute the M0 / M1 / M2 service tables;
9. compute the accepted `schedule_normal` decision in each mode;
10. compare the next M2 action with the accepted NS1c2 trace.

The instant the next M2 action differs: freeze the FIRST CAUSAL DIVERGENCE and STOP. Observations after a causal
divergence are counterfactual and are never consumed (the stage opens an event's arrays only when it consumes the event;
its guard record proves it). After step 7 (event 8) the memory-enriched post-step-7 state is frozen with a descriptive M2
service table and the M2 `schedule_normal` result, NOT EXECUTED and not compared (there is no accepted step 8).

## 15. What counts as a divergence

Load-bearing (a divergence; STOP): the M2 next action differs from the accepted one in the current / selected target, the
`schedule_normal` decision (retain / switch / initial), the ACTIONABLE / QUIET state of the target that determines
scheduling, the proposal source (`fsg6f` vs `cyclopean_epistemic`), the local proposed gaze or the mapped H0 gaze (exact
equality: the proposals are the accepted policy's grid values), or M2 has no action where the accepted trace has one.
Soft (recorded, no stop): frontier / candidate counts, Cyclopean eligible cells, effective-geometry sizes, revisions,
service-state or proposal changes of non-selected entities that leave the decision unchanged, and the scheduler's
`natural_reactivation` reason annotation on an otherwise identical switch.

At the divergence the record holds the M0 (accepted) action, the M1 action, the M2 action, the memory state (per-id
counts and snapshot digests), every M2 probe, and the causal attribution (section 17).

## 16. Reactivation (B14)

If an entity is QUIET under M2 and a later observation of another active target adds measurements to it, its revision
changes, its cached quiet probe is invalidated and it is re-probed by the adapter's refresh; if it becomes ACTIONABLE the
accepted adapter emits `natural_reactivation`, recorded with: the triggering active target, the source memory event, the
cross-target points added, the revision before / after, the probe before / after and the effective geometry size before /
after. There is no manual reactivation call (code scan). No reactivation in this short trace is not a failure.

## 17. Outcome semantics

- **Outcome 1 — memory bridge works, action divergence found.** M2 accumulates the all-instance controller-phase
  measurements faithfully; persistent maps unchanged; revisions propagate cross-target evidence; the next physical action
  first differs from accepted NS1c2 at a specific event, and M1 does NOT already produce that change (the difference
  needs cross-target evidence).
- **Outcome 2 — memory bridge works, no action divergence in the trace.** Memory, revisions and effective geometry change
  correctly (possibly some non-selected probes change), but every next action through accepted step 7 is unchanged. The
  memory-enriched post-step-7 state is frozen; the next experiment may release the controller from there.
- **Outcome 3 — own-memory effect dominates.** At (or before) the first M2 divergence, M1 already changes the action
  (restoring the FULL historical effective-geometry semantics changes policy because the historical controller used raw
  own measurements in addition to fused maps). Reported separately; never called cross-target reactivation. Because no
  coherent cross-target sample exists before event 6, any divergence at decisions before NS1c2 steps 0–5 is necessarily
  Outcome 3. Luiz and Chat decide whether FULL historical memory or a cross-target-only variant is the North-Star
  architecture.
- **Outcome 4 — integration failure.** E.g. a patch cannot be built without truth leakage; a patch count mismatch;
  corrupted provenance; a persistent map changes; revision semantics incorrect; the accepted target-only replay (M0) not
  reproduced; a process guard violation. STOP; no tuning.

## 18. Rank-1 planar controller support (descriptive only)

Not fixed. The run reports whether cross-target spherical memory changes the effective geometry, proposal or state of
the five rank-1 entities (9, 12, 204, 230, 231); their planar controller observation support may remain zero.

## 19. Process guard and truth boundary

The canonical stages `source`, `synthetic`, `known-answer`, `events` and `replay` run under the accepted
`NoProcessGuard` (no process can start, hence no Blender) and under `OpenGuard` read allowlists. Zero new renders, zero
Blender attempts, zero acquisitions. Truth reads: only `known-answer` reads the accepted Controller-01 oracle
observations of object 109's three own looks (the accepted controller-time oracle matcher input, through the unchanged
`ns1b_fixtures.rebuild`). No NS1d stage reads a North-Star reference observation, EXR, Position or catalog. If a required
all-instance spherical / identity product is absent: STOP (never regenerated from Position, never re-rendered).

## 20. Checker (`tools/north_star/check_ns1d.py`)

Own literal pins; independent recomputation wherever an independent formula exists; every load-bearing rule
fail-capable. Families: PROVENANCE (canonical repo; base; contract first and unchanged; NS1c2 ACCEPTED on the base; NS1c
not accepted / not merged; accepted `measurement_memory.py` and the accepted code unchanged; upstream manifests and
every read file equal to its manifest entry); OBSERVATION EVENTS (own derivation; 9 unique physical observations;
targets; gazes; hashes); MEMORY PATCH (own construction from the pinned products; accepted correspondence and geometry
only; identity attached post-freeze — the checker re-attaches it independently from `instance_L` at `uv_L`; no Position;
exact valid count; instance 0 / −1 excluded); MEMORY (own rebuild with the accepted class: additions, totals, provenance,
append once, determinism; all positive ids); MAP / MEMORY SEPARATION (own re-fusion bitwise; cross ids never fused;
untouched maps unchanged); M0 / M1 / M2 (own geometry sizes and revisions; M0 = accepted; probes re-run from reconstructed
contexts and geometry and equal at tolerance 0); REVISION / CACHE (cross additions change exactly the M2 revisions of the
observed eligible ids, never M1, never maps; fresh probes exactly where the revision changed); OWN-LOOK CONTEXT (untouched
by cross-target memory); SCHEDULER (`schedule_normal` recomputed on own statuses; eligibility unchanged; memory-only ids
absent); DIVERGENCE (first load-bearing difference correctly located; replay stopped there; later observations not
opened); REACTIVATION (adapter events only); PROCESS (zero renders / Blender / acquisition; stage order; one clean pushed
commit; code scan); TRUTH BOUNDARY; TERMINOLOGY (memory ≠ persistent map; cross-target measured ≠ fused; reactivation ≠
manual; observed id ≠ scheduler eligibility; no ACCEPTED marker); VISUALS (byte-identical regeneration; labels); MANIFEST
and declared changes. The historical and synthetic known answers are re-run by the checker.

## 21. Corruption suite (`tools/north_star/check_ns1d_corruptions.py`)

From a passing baseline after an unmodified-mirror null probe; mirrors with large arrays symlinked and unlinked before
writing; RUN and VIS hashed before and after. At least: MEMORY ROUTING (route by active target instead of observed id;
discard cross-target ids; include instance 0; append the same observation twice; change the provenance target); GEOMETRY
(planar controller geometry instead of spherical H0; Position directly; rounded correspondence); MAP (fuse cross-target
samples; alter a frozen map; deduplicate memory against the map); REVISION (map surfels in M2; no increment on
cross-target evidence; M1 incremented by cross-target evidence); CONTEXT (a cross-target gaze appended to visited;
another entity's evidence / history altered); SCHEDULER (an observed but ineligible id added; an object name used; order
changed); CAUSAL REPLAY (continue past the first divergence; consume a counterfactual later observation; skip a memory
event); PROCESS (launch Blender; rerender); VISUAL (memory drawn as fused surfels; the source active target hidden; the
divergence point omitted). A corruption that cannot apply to the executed trace is recorded NOT APPLICABLE with the
reason, never counted as caught.

## 22. Scientific visuals (Visual Language 1; deterministic; regenerated byte-identically by the checker)

`VIS/overview.png`: **A** the accepted historical mechanism (one active observation → several instance ids → memory →
per-id revision / effective geometry; 70.7 % cross-target; two natural reactivations), labelled ACCEPTED HISTORICAL
REFERENCE; **B** one real North-Star memory patch (active target, all positive observed ids, spherical derived points,
additions by id); **C** map vs memory for one useful observed entity (persistent SurfaceMap, cross-target memory samples,
effective geometry; "memory points are NOT fused surfels"); **D** the causal replay timeline (events, revisions, affected
entities); **E** the first divergence (M0 / M1 / M2 next action, the exact causal difference) or "NO ACTION DIVERGENCE
THROUGH STEP 7" with the memory-enriched final scene. Supporting: `memory-causal-timeline.png`,
`effective-geometry-before-after.png`, `decision-divergence.png` (if a divergence occurs), `reactivation.png` (if a
natural reactivation occurs). Truth badges, frame labels, the fixed-head statement, the source active target on every
memory sample, non-color cues, `visuals-manifest.json`. Future-figure wording: the ids 10 / 110 / 178 are labelled
`AMBIGUOUS ORACLE ID — EXCLUDED` (from scheduling), never "deferred id".

## 23. Commands, order and cost

    RUN=/home/lvelho/rd/f3d-vision/previews/north-star/ns1d-cross-target-measurement-memory
    VIS=/home/lvelho/rd/f3d-vision/visuals/north-star/ns1d-cross-target-measurement-memory
    .venv/bin/python tools/north_star/ns1d_run.py source        --run $RUN
    .venv/bin/python tools/north_star/ns1d_run.py synthetic     --run $RUN
    .venv/bin/python tools/north_star/ns1d_run.py known-answer  --run $RUN
    .venv/bin/python tools/north_star/ns1d_run.py events        --run $RUN
    .venv/bin/python tools/north_star/ns1d_run.py replay        --run $RUN   # event 0 + steps 0..7, stops at divergence
    .venv/bin/python tools/north_star/ns1d_run.py visualize     --run $RUN --visuals $VIS
    .venv/bin/python tools/north_star/check_ns1d.py --run $RUN --visuals $VIS --corruptions --write-summary

Cost classes (PROPOSED): `known-answer` and `replay` batch (minutes; no render); the checker with corruptions batch;
every other stage interactive. No overnight task, no parameter sweep. Every canonical stage runs once, from one clean
pushed implementation commit, and refuses to rerun.

## 24. Permitted fix scope

- **Before the canonical run:** implementation defects in the NS1d tools, without changing sections 5–17 or a declared
  tolerance. Development uses the synthetic fixtures, the historical known answer and scratch development runs (never the
  canonical RUN). Development may build the event list and run the replay on a scratch run; no development result is
  reported as the measured result, and the canonical replay runs once from the implementation commit.
- **After the canonical run starts:** (a) a stage that fails with an implementation defect BEFORE writing any output may
  be repaired minimally and then run for its first and only time, if sections 5–17 are unchanged (recorded as an
  incident); (b) presentation-only figure fixes; (c) a checker or corruption-suite defect that false-alarms on correct
  data, only if the fix does not weaken the check (recorded).
- Anything else — a render, a different event order or scope, a memory routing / revision / geometry change, an edit of
  `fov3d/` or of the accepted memory class, a policy, scheduler, budget or gate change, bootstrap memory, cross-target
  fusion, a rank-1 fix — is a STOP for Luiz and Chat.

## 25. Stop conditions

STOP and report if: a provenance or pin check fails; `synthetic` or `known-answer` fails; the derived event list differs
from section 6 in count, order, targets or uniqueness; a memory patch count or provenance check fails; a required product
is absent; M0 does not reproduce the accepted NS1c2 probes and decisions; a persistent map or a non-target context
changes; a guard records a violation or a process attempt; a stage would run twice; a canonical check fails for a reason
other than a checker defect. The first M2 action divergence is a scientific stop (freeze; Outcome 1 or 3), not a failure.

## 26. Report and stop

`docs/north-star/ns1d-cross-target-measurement-memory-report.md`, status REVIEW PENDING, marker
`NORTH_STAR1D_CROSS_TARGET_MEASUREMENT_MEMORY_COMPLETE`, no ACCEPTED marker. It records the 24 items of the mandate's B26
(provenance; NS1c2 acceptance; the historical semantics; the scope and why bootstrap memory is deferred; the event list;
the patch construction; per-event additions by observed id; M0 / M1 / M2; memory totals own / cross / by id / by active
source; revision changes; effective-geometry changes; per-event service-state / proposal changes; the first action
divergence, if any; natural reactivations, if any; proof that persistent maps are unchanged; rank-1 effects; the Outcome
reading; checks; corruptions; visuals and hashes; incidents; what is and is NOT established) and ends with the unresolved
decision: READY TO RELEASE THE MULTI-ENTITY NORTH-STAR LOOP WITH CROSS-TARGET MEMORY? Then STOP: no acceptance, no merge,
no execution of a divergent next action, no release of the full loop, no bootstrap memory, no change to FSG6f, Cyclopean,
Controller-02, the scheduler, the budget, rank-1 support, map fusion scope, identities in scheduling, stereo or the head.

## 27. What NS1d may and may not establish

May establish: whether the accepted instance-keyed memory mechanism can be inserted into the North-Star architecture from
already measured spherical controller-phase observations with maps, contexts and scheduler eligibility intact, and whether
and where the restored effective geometry (own and cross-target) changes the next controller decision relative to the
accepted target-only NS1c2 trace.

May NOT establish: the behaviour of the full multi-entity loop with memory; bootstrap cross-target memory; that
cross-target memory improves coverage; anything about natural correspondence or identity, 10 / 110 / 178 as scheduled
entities, head motion, real cameras or other scenes.
