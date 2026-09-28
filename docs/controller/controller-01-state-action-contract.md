# Integrated Foveal Controller 01: state/action contract

## Status

This is the first **Integrated Foveal Controller** step. It is a scientific/behavioral step
with one causal question. It is **not** Conceptual Core 15, not a migration and not a cleanup.

    base                          origin/main @ c5f6be63d050d89026b3658a2d033e7c2439caf1
                                  (Update Chat Handoff for accepted Repository Stage Transition 1)
    accepted structural milestone b12bdef0593a043c5e7593b38d78735875c007fd
                                  REPOSITORY_STAGE_TRANSITION_1_PRESERVES_SCIENTIFIC_BEHAVIOR
    accepted scientific milestone 296001e8683ba0b1ad62642811d3dea0e84b6566
                                  CONCEPTUAL_CORE14_GAZE_CONTEXT_SEPARATION_PRESERVES_BEHAVIOR
    branch                        controller/controller-01, created from the base
    execution                     one dedicated isolated git worktree; the shared checkout
                                  /home/lvelho/rd/f3d-vision is neither switched nor mutated
    markers                       CONTROLLER01_IMPLEMENTATION_CHECKS_PASS
                                  CONTROLLER01_GLOBAL_QUIESCENCE_REACHED   (only if measured)

Design provenance: Luiz and Chat designed the architecture below. Luiz authorized the
implementation, its fail-capable checks, one smoke integration run and one full closed-loop
scientific run. Claude Code commits this contract **before** any production change, then
implements, runs and reports. Nothing is merged into `main`, and `docs/chat-handoff.md` is not
updated until Luiz accepts the step.

Every statement about behavior in this document is **PROPOSED** unless it is marked otherwise.
The few quantities marked **MEASURED (scratch)** were measured read-only on the accepted
reference run `previews/partition-graph-2-source-full`. They informed cost planning only and
are not acceptance evidence.

## Causal question

Can a fixed-head, static-scene observer close the scene-level loop over all
bootstrap-localized known objects using

- the accepted bootstrap seed oracle,
- persistent causal scene/object memory,
- the accepted object-local FSG6f → Cyclopean policy, and
- a deterministic retain/switch/stop scheduler,

such that a locally quiet object is only "quiet now", can become actionable again after
persistent memory changes, and global STOP occurs only when no localized initialized object can
act?

This step does not design a better fixation policy. The accepted local controller is reused
deliberately, so that the new causal question is scene-level integration. No
reconstruction-quality threshold is a scientific PASS/FAIL criterion.

## What changes and what does not

New (all additions; no existing file changes behavior):

| path | role |
|---|---|
| `fov3d/control/integrated.py` | reusable controller concepts: service states, the object summary, OBSERVE/STOP/INCOMPLETE types, the service-probe result, the deterministic cyclic scheduler, the generic closed control loop, the target-relative intrinsic-view construction, the truth firewall. No Blender, no evaluator, no historical candidate/run/gaze policy, no `tools.*` import. |
| `fov3d/experiments/classroom_oracle/controller01.py` | the Classroom experiment adapter and executable (bootstrap subprocess, rendering, oracle matcher for the current tangent pair, active-target SurfaceMap initialize/fuse, global causal memory, the per-object accepted local-policy context and probe, artifacts, manifest). |
| `tools/controller/check_controller01.py` | fail-capable unit, architecture and run-artifact checks. |
| `tools/controller/plot_controller01.py` | the inspectable visuals, from controller-time artifacts only. |
| `docs/controller/controller-01-state-action-contract.md` | this contract. |
| `docs/controller/controller-01-state-action-report.md` | the executed report. |

Minimal accommodation (see *Repository layout checker*): `tools/repository/check_repository_layout.py`.

Not changed:
- the 16 sealed `tools/` root modules, and every existing `fov3d/` file (byte-identical);
- FSG6f constants and behavior, the 12 mm association/fusion rule, the matcher, the Blender
  truth scope, the bootstrap seed algorithm (`SEED_SCAN_STEP_DEG`, scan geometry, instance-id
  assignment, seed selection), the evaluation metric, the Core-14 epistemic precedence, the
  rendering scene, object ids, the 24-look watchdog value;
- the fixed-head and static-scene assumptions;
- `docs/chat-handoff.md`, historical contracts and reports, the accepted reference trees.

Not added: a learned policy, semantic attention, a moving head, recency weighting, inhibition of
return, an object-ranking score, information-gain or budget optimization, a vergence policy, a
focus policy, a foreground/background special object.

## State

    S_t = (M_t, H_t, C_t)

**M_t, persistent causal perceptual memory** (all causal; nothing from evaluation truth):

| component | concrete object | updated by |
|---|---|---|
| known object catalog | `bootstrap/instance_catalog.json` | bootstrap only |
| bootstrap localization | `bootstrap/seeds.json`: one seed direction per controller-domain-visible instance | bootstrap only |
| per-object active-target SurfaceMap | `fov3d.reconstruction.surface_map` `initialize`/`fuse`, 12 mm, only from that object's own target-directed looks, exactly as the accepted runner | the object's own looks |
| global instance measurement memory | one `fov3d.reconstruction.measurement_memory.InstanceMeasurementMemory`, keyed by **observed** instance id, with source global action index and source active target id | every completed look |
| global target-neutral head evidence | one `fov3d.epistemic.head_memory.HeadEvidence` accumulated with `add_head_patch` over every look. Only `depth_seen`, `nearest_instance`, `nearest_range_m`, `ambiguous_instance` and `sample_count` are read. `target_depth_seen`/`other_depth_seen` are never read (they would mix active targets). | every completed look |
| global observation footprint `seen_any` | one accepted Cyclopean evidence chart (`fov3d.experiments.classroom_oracle.epistemic`, 0.10°) accumulated over every look with `add_observation`. Only its target-neutral `seen_any` field is read. | every completed look |
| per-object local-policy context | the accepted local controller's own-target inputs: last own gaze, calibration and binocular state; the own-target visited list and FSG6f history entries; the own-target Cyclopean evidence chart (see *Local policy*) | the object's own looks |
| derived scene support/ownership | `fov3d.scene.partition.support_depth_from_map` per measured instance, then `joint_owner` | derived on demand |
| target-relative epistemic view E_t(i) | `fov3d.epistemic.partition.build_epistemic_partition` | derived on demand |

**H_t, the global executed action history**: the ordered list of executed OBSERVE actions with
their annotations (`actions.json`). The accepted local controller's target-local visited list
and history are a derived local-policy adapter, not the definition of H_t.

**C_t, the attentional context**: the current attended object id (or none before the first
action) and the attention-bout counter.

Not in the controller state: candidate ranking, a future experiment schedule, evaluation
truth, inhibition of return, recency weighting, semantic state, budget optimization.

## Object service states

Every catalog object has exactly one service state:

| state | meaning |
|---|---|
| `UNLOCATED` | known catalog object with no bootstrap seed in the fixed-head controller domain; never attended; outside the localized-quiescence claim; never counted as QUIET |
| `SEEDABLE` | localized; the seed look has not yet been executed |
| `ACTIONABLE` | localized and initialized; the service probe returns one admissible post-seed OBSERVE from the **current** causal memory |
| `QUIET` | localized and initialized; the service probe currently returns no observation. QUIET means "quiet now", never "complete" |
| `BLOCKED` | localized; an execution failure, with `blocked_reason` `seed_uninitializable` or `watchdog`; never QUIET |

The scheduler receives one `ObjectSummary(instance_id, state, blocked_reason)` per object and
nothing else: no candidate score, UNKNOWN count, reconstruction percentage, expected gain,
gaze-distance penalty, recency, fixation count, salience or information gain.

**BLOCKED is sticky.** Once blocked, an object stays blocked for the rest of the run and is not
probed again. This is the conservative choice: a blocked object can never be converted into a
scientific success by later memory changes.

## Local policy (authoritative in Controller 01)

No new policy over the five Core-14 epistemic classes is introduced. The accepted local
sequence is wrapped through the conceptual namespaces:

    fov3d.control.object_policy.choose_next(...)                   (FSG6f through the adapter)
        ↓ only if it returns stop
    fov3d.experiments.classroom_oracle.epistemic.choose_next(...)  (Cyclopean handoff)

**Service probe.** For an initialized object `i`, one pure function returns a `ProbeResult`:
either ACTIONABLE with the exact proposed `OBSERVE` (source `fsg6f` or
`cyclopean_epistemic`), or QUIET (no action). `can_act(result)` and `choose_action(result)` are
two views of the **same** result field, so they cannot disagree. The probe inputs are:

| input | value |
|---|---|
| current gaze, calibration, binocular ids/support | from the object's **last own** target-directed look |
| visited gazes, FSG6f observation history | the object's own target-directed looks, exactly as the accepted runner builds them |
| Cyclopean evidence chart | accumulated from the object's **own** looks only, exactly as the accepted runner (a fresh chart per object) |
| map geometry for both FSG6f and Cyclopean | `effective_target_geometry(active SurfaceMap XYZ, InstanceMeasurementMemory.snapshot(i).xyz_h)`, duplicates retained |

The global memory therefore enters the local probe through the effective target geometry only.
Using a global observation chart for the Cyclopean `NEVER_OBSERVED` test would be a new policy,
and is **not** done here (listed under *Open questions*). No observation is fabricated to ask
whether an object is actionable, and the probe mutates nothing.

**Exact probe memoization.** The probe of `i` is a pure function of its own-look context and its
effective geometry. Both change only when `i` is observed (own-look count) or when a look
measures instance `i` (memory point count for `i`). The loop therefore caches the last probe
result keyed by `revision(i) = (own-look count, measured point count of i)` and re-probes when
the revision changes. This is exact reuse, not a policy. The checker verifies that a run with the
cache equals a run without it, and that a stale-key mutant is detected.
MEASURED (scratch): one FSG6f probe on effective geometries of 0.28–1.5 M points took
0.45–2.24 s, and one Cyclopean probe about 0.25 s.

The accepted runner's safety check is kept: a proposed gaze already in the object's own visited
list is a controller inconsistency and ends the run as a runtime failure.

## Scheduler (deterministic retain / switch / stop)

`schedule(current_id, summaries)` is pure and uses only identity and service state. Ids are
ordered ascending, and "serviceable" means SEEDABLE or ACTIONABLE.

1. No current object: choose the first serviceable object in ascending id order (`initial`).
2. The current object is serviceable: **retain** it (`retain`).
3. The current object is QUIET or BLOCKED: scan cyclically forward in ascending id order from
   the current id and choose the first serviceable object (`switch`).
4. No serviceable object:
   - if any localized object is BLOCKED → `INCOMPLETE(reason="localized_objects_blocked")`;
   - otherwise every localized object is initialized and QUIET → `STOP(reason="global_quiescence")`.

UNLOCATED objects are ignored by rules 1–4 and are reported separately. `STOP` accepts only the
reason `global_quiescence`; every other ending is a distinct non-success type. Retain and switch
are scheduler transitions, not physical eye actions. With zero localized objects rule 4 would
return STOP vacuously; the report states the localized count, and the Classroom bootstrap
localizes 25 objects (MEASURED in the accepted reference run).

A blocked object does not stop the run early: the loop keeps servicing every other serviceable
object and returns INCOMPLETE only when none remains.

## Action

One executed sensory action:

    OBSERVE(target_id, gaze_yaw_pitch_deg, vergence, focus)

- the gaze comes from the bootstrap seed (the first look of an object, source `oracle_seed`) or
  from the service probe (`fsg6f`, `cyclopean_epistemic`);
- vergence stays the accepted fixed value, FSG6f `VERGENCE_DISTANCE_M` = 2.10 m, as written into
  each look's `calibration.json` by the unchanged renderer;
- focus stays the current rendering behavior: depth of field disabled in the unchanged
  renderer;
- both are recorded explicitly in every action record. Neither is optimized.

The only successful terminal action is `STOP(reason="global_quiescence")`.

## Executing one OBSERVE

For the chosen object `i` with own-look index `k` (0 for the seed look):

1. render the binocular pair with the unchanged Blender acquisition, invoked exactly as the
   accepted runner invokes it (same script, arguments, profile, device and spp;
   `--object-id i --step k`, so the physical noise seed of a look is the accepted one);
2. oracle-match the **current** tangent pair only (`fov3d.experiments.classroom_oracle.matcher`);
3. save the patch (`objects/instance_i/patches/fix_kk.npz`, the accepted arrays and dtypes) and
   the rectified RGB pair;
4. append every valid positive-instance measurement of the saved patch to the global
   `InstanceMeasurementMemory`, with the global action index and active target `i`;
5. accumulate the saved patch into the global `HeadEvidence` and the look's binocular evidence
   into the global `seen_any` chart;
6. seed look: `initialize` the active SurfaceMap if the look has at least the inherited
   100 target points (`MIN_INITIAL_TARGET_POINTS`); otherwise `i` becomes
   `BLOCKED(seed_uninitializable)`. Later look: `fuse` at 12 mm with the accepted idempotence
   replay check, or, below 100 target points, the accepted empty-look semantics (the look and
   its binocular evidence are kept; zero geometry is fused). Patch ids stay `fix_kk`;
7. update `i`'s local-policy context (visited, FSG6f history entry, own Cyclopean evidence,
   current gaze/calibration/state);
8. increment `i`'s target-directed fixation count.

Incidental cross-target measurements are never fused into another object's active SurfaceMap;
they live in the measurement memory with their provenance, and reach the object only through its
effective target geometry.

After every completed observation the loop recomputes the service state of every localized,
initialized, non-blocked object from the current memory (through the exact cache).

## Watchdog

The inherited 24-look watchdog remains only an engineering bound. It counts an object's
target-directed fixations across all of its attention bouts, including the seed look. When an
object has 24 fixations and its probe is ACTIONABLE, it becomes `BLOCKED(watchdog)`; this is
checked after its 24th look and after every later memory change. An object with 24 fixations
whose probe is QUIET stays QUIET. The watchdog is not a success criterion.

## Natural reactivation

There is no `reactivate()` operation and no REACTIVATED state, reactivation timeout, staleness or
recency score. The loop only recomputes service states after each observation. When an object
whose recorded state was QUIET is now ACTIONABLE, the loop records a **natural reactivation**
event (`QUIET → ACTIONABLE`), with the triggering action and target. If the reactivated object
has already used 24 fixations, the same event is recorded and the object becomes
`BLOCKED(watchdog)`.

A switch whose target has a natural reactivation since its last attended action is annotated
`scheduler_reason = natural_reactivation`. The pure decision is still `switch`.

Real-scene reactivation is **not** required for an implementation-valid run. Its measured count,
including zero, is descriptive. The synthetic check must show the full chain (A quiet → B
observed → memory changes → A recomputed ACTIONABLE → the scheduler selects A) with no
reactivation mechanism.

## Target-relative intrinsic epistemic view E_t(i)

E_t(i) is derived, never independent mutable state:

    effective target geometry of i         → support_depth_from_map → target_support
    effective geometry of every measured   → support_depth_from_map per instance → joint_owner
      instance (catalog objects with an      → owner_instance
      active map and/or measurement memory)
    global HeadEvidence                    → nearest_instance, ambiguous_instance, depth_seen
    global seen_any chart                  → seen_any

    build_epistemic_partition(state, target_id=i, target_name=..., domain=seeds
                              controller_domain_deg, grid_deg=0.10)

The historical `candidate_policy`, `run_context` and `gaze_context` layers are not used. The
output must stay intrinsic: no `candidate`, `candidate_region_count`, `reconstruction_status` or
`min_distance_to_historical_gaze_deg`. Support layers are cached by the same revision key as the
probe.

E_t(i) is built at diagnostically important transitions only:
- after an object's seed look (initialized or blocked);
- when an object enters QUIET;
- at every natural reactivation (the "before" view is the one saved when the object entered
  QUIET; the "after" view is built at the reactivation);
- for every localized initialized object at termination.

Each saved view (`objects/instance_i/epistemic/global_tttt_<event>.npz` and `.json`) records:
the arrays `class_code` and `region_code`; the diag, including the five kind cell and region
counts (`TARGET_SUPPORT`, `OTHER_SURFACE`, `UNKNOWN`, `AMBIGUOUS_BOUNDARY`,
`TARGET_EVIDENCE_UNMAPPED`); and a topology summary (region and edge counts, UNKNOWN regions
adjacent to target support, UNKNOWN regions touching the domain edge, the largest UNKNOWN region,
and the other-surface instances adjacent to target support). Every reactivation also records the
before/after probe summaries and revisions, and the provenance of the memory added in between.
No evaluator truth labels any region.

## Bootstrap and the truth firewall

The accepted Classroom-Oracle bootstrap runs unchanged (`--mode seeds`,
`--seed-step SEED_SCAN_STEP_DEG`). The controller reads only `bootstrap/instance_catalog.json`
and `bootstrap/seeds.json`: known identities plus one coarse seed direction per visible object.
The first OBSERVE of each object must still earn its local 3-D measurements.

The controller must never open `bootstrap/evaluation_only/…` or `evaluation.json`. This is
enforced, not intended. During control a process-wide audit hook
(`sys.addaudithook`) watches every file `open` and directory listing, and raises
`PermissionError` on any forbidden path. It records every run file opened for reading. The
manifest records `dense_evaluation_truth_opened_during_control` from the hook's measured
violation count, and lists the files the controller opened. The checker rejects any forbidden
path in that list, and tests the hook itself with a forbidden open that must fail.

## Run artifacts

The run directory is a superset of the Classroom-Oracle layout, so the existing offline evaluator
can read the active-target final maps:

    bootstrap/seeds.json, instance_catalog.json, evaluation_only/…  (created by the bootstrap;
                                                                     never opened during control)
    logs/bootstrap.blender.log
    objects/instance_XXXX/
        acquisitions/fix_kk/…, fix_kk.blender.log
        patches/fix_kk.npz
        maps/fix_kk.npz
        benchmark/fix_kk_{L,R}.png
        epistemic/global_tttt_<event>.{npz,json}
        final_map.npz                     active-target fused SurfaceMap geometry
        final_effective_geometry.npz      effective causal target geometry + provenance
        result.json
    actions.json                          the global action history H_t, with events
    manifest.json

Each action record reconstructs: the global step; target id/name; gaze; action source
(`oracle_seed`, `fsg6f`, `cyclopean_epistemic`); the fixed vergence/focus state; the target's
service state before the action; the pure scheduler decision (`initial`, `retain`, `switch`) and
the annotated reason (adding `natural_reactivation`); the attention-bout number and the
current-object transition; the object-local step; target valid points; all-instance valid points;
the active map size before/after; new surfels; measurement-memory additions by observed
instance; the proposing probe summary; the service states of every localized object before and
after; and the events it caused.

The manifest distinguishes: known catalog objects; localized; unlocated; successfully
initialized; blocked at initialization; watchdog-blocked; quiet; actionable at termination; total
actions; switches; attention bouts; quiet episodes; natural reactivations. It records
`control_complete`, the terminal action and reason, the final service state of every localized
object, the cross-target measurement provenance, and
`dense_evaluation_truth_opened_during_control`. For the existing evaluator, `manifest.objects`
lists the attempted localized objects in the accepted row format (`instance_id`,
`object_name`, `fixation_count`, `termination` = final service state, `final_map_surfels`,
`trajectory` with `new_surfels`).

Visuals (regenerable previews, not committed): `controller-attention-timeline.png` (x = global
action, y = object; seeds, FSG6f and Cyclopean actions, switches, attention bouts, reactivations)
and `controller-gaze-chart.png` (the executed gaze sequence in the yaw/pitch controller domain,
labelled by action and object). They are drawn from controller-time artifacts only, with the
pinned OpenCV/Pillow; no package is installed.

## Smoke mode

`--smoke` is plumbing/integration only, with the small profile. It caps the run at
`SMOKE_ACTION_CAP = 8` executed actions, a cost bound and not a policy: reaching it ends the run
as `smoke_cap_reached`, which is not QUIET and not a scientific result. The scheduler and the
local policy are unchanged in smoke mode. The existing evaluator refuses smoke output.

## Checks (`tools/controller/check_controller01.py`)

Blender-free unit and architecture checks. Each behavioral check also runs a deliberate
negative control (a mutant scheduler, probe, memory or firewall) that must be rejected, so every
check is shown to be fail-capable:

1. a current ACTIONABLE object is retained;
2. a current SEEDABLE object is retained;
3. a current QUIET object causes a deterministic cyclic switch to the next serviceable object;
4. all localized initialized objects QUIET → `STOP(global_quiescence)`;
5. a SEEDABLE object prevents STOP;
6. an ACTIONABLE object prevents STOP;
7. a localized BLOCKED object prevents successful `global_quiescence`;
8. UNLOCATED is not silently equivalent to QUIET;
9. the ascending-id/cyclic order is deterministic and independent of input order;
10. the selector uses only service state and identity: `ObjectSummary` has exactly
    `instance_id`, `state`, `blocked_reason`, and decisions are invariant to attached epistemic
    side information (a ranking mutant is caught);
11. `can_act` and `choose_action` cannot disagree, and the probe maps FSG6f continue / FSG6f stop
    + Cyclopean select / both stop to fsg6f / cyclopean / QUIET; the probe is pure;
12. synthetic natural reactivation through the real control loop, with no reactivation mechanism
    (and the probe cache equals a cache-free run; a stale-key cache is caught);
13. the effective target geometry includes causal cross-target XYZ without mutating the active
    SurfaceMap;
14. the target-relative Core-14 view is intrinsic (no candidate, reconstruction status or gaze
    distance) and ignores the target-relative `HeadEvidence` fields;
15. successful global STOP is impossible after a seed initialization failure;
16. watchdog-blocked is not QUIET;
17. the truth firewall rejects controller access to `bootstrap/evaluation_only` and
    `evaluation.json`.

Architecture checks: the imports of `integrated.py` (no `bpy`, `tools`, historical bare module
name, evaluator, `candidate_policy`, `run_context` or `gaze_context`) and of `controller01.py`
(`fov3d` namespaces only); no reactivation/recency/inhibition API; the service-state set is
exactly the five states; the 16 sealed root modules are byte-identical to the base.

Run validation (`--run DIR`): the manifest and truth firewall; contiguous global steps; the seed
as each object's first look and only first look; post-seed sources; fixed vergence/focus;
own-target gazes unique; at most 24 fixations per object; a replay of the pure scheduler over the
logged service states reproduces every decision; bout and switch counts; the measurement memory
rebuilt from the saved patches reproduces the logged additions and the final effective geometry;
the final maps; event consistency (every reactivation was QUIET then ACTIONABLE, triggered by a
different target); and terminal consistency (`global_quiescence` if and only if every localized
object is initialized and QUIET; smoke ends only at the cap or earlier with a terminal
decision).

## Repository layout checker

**Pre-existing failure (MEASURED before this contract).** At the base `c5f6be6`,
`tools/repository/check_repository_layout.py` reports `SUMMARY checked=487 failed=3`. At
`b12bdef` it reported 487/0. The only change between the two commits is the acceptance
administration of `docs/chat-handoff.md`. The checker's three handoff assertions still encode
the pre-acceptance state:
- "keeps accepted main at Core 14";
- "does not claim the transition accepted";
- the handoff sentence "`tools/dev/` is gone." read as an obsolete path.

So this is a stale expectation, not a regression.

The checker also asserts that `fov3d/` is byte-identical to the RT1 base, and that `docs/` and
`tools/` contain exactly the RT1 stage directories and files. The authorized Controller-01
additions therefore cannot pass it unchanged.

**Proposed minimal accommodation**, in this file only, without loosening any existing check:
1. `docs/controller/` and `tools/controller/` join the stage/topic directory sets;
2. the Controller-01 files become declared additions: the contract, the report, the checker, the
   visual tool and the two new `fov3d` modules. Every **pre-existing** `fov3d/` file must stay
   byte-identical to the base, and the only allowed new `fov3d/` files are the two declared
   modules;
3. the handoff assertions are aligned with the accepted state: main @ `b12bdef`, Repository
   Stage Transition 1 accepted, Core 14 the accepted scientific milestone. The removal sentence
   "`tools/dev/` is gone" is allowed verbatim. Any other `tools/dev/…` path still fails.

Evidence to record: the checked-count change, and the RT1 mutation suite re-run with the two
mutations whose premise changed (an empty `docs/controller/`, and a handoff claiming acceptance)
replaced by their counterparts (an undeclared stage directory, and a handoff reverted to the
pre-acceptance claims). New mutations cover an undeclared `fov3d` file, an edited existing
`fov3d` file, an undeclared `docs/controller` file, and a handoff naming a `tools/dev/…` path.
Item 3 repairs a stale check on a file outside the Controller-01 scope. It is recorded as a
separate commit and a report deviation for Luiz and Chat to review.

## Gates and commands

| command | cost class |
|---|---|
| `.venv/bin/python tools/controller/check_controller01.py` | interactive |
| `.venv/bin/python tools/conceptual_core/check_conceptual_core14.py` | interactive |
| `.venv/bin/python tools/classroom_oracle/check_classroom_oracle1.py` | interactive |
| `.venv/bin/python tools/consolidation/check_fov3d_facade.py` | interactive |
| `.venv/bin/python tools/repository/check_repository_layout.py` | interactive |
| `scripts/verify_baseline.sh` | interactive |
| `git diff --check`; compile every changed/new Python file; sealed-module byte identity | interactive |
| `.venv/bin/python -m fov3d.experiments.classroom_oracle.controller01 --repo . --out previews/controller-01-smoke --profile small --device OPTIX --smoke` | batch |
| `.venv/bin/python tools/controller/check_controller01.py --run previews/controller-01-smoke` and the visual | interactive |
| `.venv/bin/python -m fov3d.experiments.classroom_oracle.controller01 --repo . --out previews/controller-01-full --profile full --device OPTIX` | overnight (ESTIMATED 0.5–2 h; explicitly authorized by Luiz as the first Controller-01 scientific experiment) |
| `.venv/bin/python tools/controller/check_controller01.py --run previews/controller-01-full` | interactive |
| `.venv/bin/python -m fov3d.experiments.classroom_oracle.eval --run previews/controller-01-full` (only after `control_complete`) | batch |
| `.venv/bin/python tools/controller/plot_controller01.py --run previews/controller-01-full` | interactive |

Exactly one full scientific run. It is rerun only if a clearly diagnosed implementation/runtime
defect invalidates it; the invalid run and the repair are recorded. No sweep, and no rerun
because of disappointing coverage or behavior. No evaluation output feeds back into the
controller.

## Acceptance

**Implementation acceptance** (`CONTROLLER01_IMPLEMENTATION_CHECKS_PASS`) requires:
- this contract committed before any production change;
- the conceptual API boundaries respected, and no sealed runtime module changed;
- the truth firewall holding;
- the scheduler checks, the synthetic natural-reactivation check and the probe-consistency check
  passing;
- the Core-14 intrinsic partition semantics intact;
- the baseline, facade, Classroom, Core-14 and layout gates passing;
- the smoke run and the full run structurally valid (`--run` validation);
- the inspectable visual present, and the report complete.

**Scientific outcome.** The Controller-01 question passes **only** if the full run terminates with
`STOP(global_quiescence)`: every bootstrap-localized, successfully initialized object is QUIET;
no SEEDABLE and no ACTIONABLE object remains; and no localized object is BLOCKED. UNLOCATED
catalog objects are reported separately and excluded from the claim. Any other ending (seed
initialization failure, watchdog block, controller inconsistency, runtime failure) is the
MEASURED scientific result and is recorded without tuning.
`CONTROLLER01_GLOBAL_QUIESCENCE_REACHED` is emitted only in the passing case.

Descriptive only: reachable samples, covered samples, coverage fraction, per-object coverage,
zero-new looks, the natural-reactivation count, the switch and bout counts.

## Stop conditions and permitted fixes

Permitted, minimal and recorded: new-controller bugs, new-runner artifact/serialization bugs,
new-checker bugs, the layout-checker accommodation above, and mechanical facade-invocation issues
that do not alter sealed behavior.

Stop and return the decision to Luiz and Chat if a fix would change: the architecture; bootstrap,
matcher or fusion semantics; FSG6f behavior/constants; the Cyclopean gaze rule; the Core-14
intrinsic partition; the object-selection policy; the scientific success criterion; the
evaluation metric; truth availability; the vergence/focus policy; the scene content; or the
watchdog value.

## Open questions (recorded, not decided here)

1. Whether the Cyclopean `NEVER_OBSERVED` test should later read a global observation footprint
   instead of the object's own looks (global versus target-local observation memory).
2. Whether BLOCKED should remain sticky once memory changes could make a blocked object quiet.
3. A target-neutral formulation of the epistemic view for scene-level decisions (the deferred
   target-relative `HeadEvidence` placement).
