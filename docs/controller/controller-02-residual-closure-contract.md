# Controller-02: residual closure — contract

## Status

The first Controller-02 implementation and experiment, authorized by Luiz and Chat under Foveal
Controller Stage Charter 1 (`docs/methodology/foveal-controller-stage-charter-1.md`).
- It adds scene-level loop semantics: deferred residue, one strict final-look gate, and honest scene
  closure.
- It is **not** a local-policy redesign. Controller-01 stays frozen.

    base              origin/main @ 6306458cf508712d4d1065b68708ca73f351c65d (Stage Charter 1 accepted)
    branch            controller/controller-02-residual-closure (isolated worktree; not merged)
    source run        /home/lvelho/rd/f3d-vision/previews/controller-01-full
                      (accepted Controller-01; manifest.json d293a98f…, actions.json 12cdbe4d…)
    output            /home/lvelho/rd/f3d-vision/previews/controller-02-classroom-replay (compact)
    visual            /home/lvelho/rd/f3d-vision/visuals/controller-02/overview.png (Level A)
    markers           CONTROLLER02_IMPLEMENTATION_CHECKS_PASS (implementation), and exactly one of
                        CONTROLLER02_CLASSROOM_SCENE_CLOSED
                        CONTROLLER02_CLASSROOM_NOT_CLOSED
                      for the scientific outcome; neither on a reconstruction or implementation failure.
                      No global-quiescence marker is ever emitted.

Everything below is PROPOSED until it runs.

## The one causal question

Can the accepted Classroom perceptual behavior terminate as `SCENE_CLOSED` with an explicit residual
object, without executing the known-unserviceable final look and without altering the accepted local
policy?

The sensory evidence is the accepted Controller-01 full run. Nothing is rendered.

## What changes and what does not

**Changes** (new files only):
- `fov3d/control/controller02.py`: reusable scene-level concepts and the generic Controller-02 loop;
- `fov3d/experiments/classroom_oracle/controller02.py`: the Classroom replay adapter and the strict
  final-look gate v1;
- `tools/controller/check_controller02.py`: fail-capable checks;
- `tools/controller/visualize_controller02.py`: the Level-A visual generator;
- this contract and the report.

**Narrow checker declarations:**
- `tools/repository/check_repository_layout.py` declares the files above. The two new `fov3d/` modules
  become allowed additions; every pre-existing `fov3d/` file stays byte-identical.
- The Controller-01 architecture check A8 (`tools/controller/check_controller01.py`) says "only the two
  Controller-01 modules are new in `fov3d`". It is extended to accept exactly the two declared
  Controller-02 modules, with its intent unchanged: every pre-existing `fov3d` file is unchanged, and no
  undeclared file is new.

**Unchanged:**
- the frozen Controller-01 production files `fov3d/control/integrated.py` and
  `fov3d/experiments/classroom_oracle/controller01.py`, byte-identical to `main`;
- FSG6f, Cyclopean, the matcher, fusion, every threshold, the budget constant (the Controller-01
  watchdog, 24), the Blender renderer and every accepted artifact;
- production code imports accepted functionality only through `fov3d.*`, never from `tools/`.

## Conceptual model

Controller-02 separates the **local perceptual/service state** from the **scene-level service
disposition**.
- **Local state.** It reuses Controller-01's meanings: UNLOCATED, SEEDABLE, ACTIONABLE, QUIET. BLOCKED
  is never used.
- **Disposition:**
  - `NORMAL`: in ordinary service;
  - `DEFERRED` (reason `ordinary_budget`): no more ordinary service; awaiting its one residue decision;
  - `FINALIZED`: the scene spends no more own-target observations on it. Reasons:
    - `seed_uninitializable`;
    - `quiet_before_final_probe`;
    - `final_probe_rejected`;
    - `final_probe_executed`.
- **Scene phase:** `NORMAL` → `RESIDUE` → `CLOSED`. RESIDUE may return to NORMAL.

An object may honestly be `ACTIONABLE` + `FINALIZED`. That means unresolved perceptual residue remains,
but the scene will spend no more own-target observations on it. That is not QUIET and not a global
failure.

`SceneClosed` is the honest successful terminal. It reports separately:
- quiet localized objects;
- residual localized objects (finalized and not QUIET);
- seed-initialization residues;
- unlocated objects;
- final residue observations executed;
- final residue proposals rejected.

Core invariant: `SCENE_CLOSED != GLOBAL_QUIESCENCE`.

## NORMAL phase

It preserves Controller-01:
- the same bootstrap seeds and catalog;
- the same deterministic retain/switch order, restricted to `NORMAL` objects;
- the same accepted local probe, FSG6f → Cyclopean (`controller01.probe_local_policy`, through the
  frozen adapter);
- the same probe cache by memory revision;
- the same causal measurement memory and target-relative geometry;
- the same natural-reactivation semantics: a recomputed probe, with no reactivation operation.

The one semantic change is at the ordinary budget:
- An initialized `NORMAL` object that is ACTIONABLE with fixations ≥ 24 becomes `DEFERRED`. Its local
  state stays ACTIONABLE, and service continues with the other `NORMAL` objects.
- A `deferred` event records the object, the global step, `reason = ordinary_budget`, the fixation count
  and the current local probe.
- The number 24 is unchanged. Its role is now an ordinary-service budget, not a claim of completion.

**Seed failure.** A localized seed that fails to initialize becomes `FINALIZED` with
`residual_reason = seed_uninitializable`. There is no recovery mechanism, and it never blocks the
scene. The Classroom run has no seed failure, so this is unit-tested.

**Local state of non-`NORMAL` objects.** A `DEFERRED` or `FINALIZED` object's local state is still
recomputed from memory, and its changes are recorded as `local_state_change` events. Its disposition
never changes back, so a deferred object never silently returns to ordinary service. `quiet` and
`natural_reactivation` events are emitted only for `NORMAL` objects, as in Controller-01.

## RESIDUE phase and closure

**Entering RESIDUE.** NORMAL → RESIDUE happens when no `NORMAL` object is SEEDABLE or ACTIONABLE. This
is not global quiescence.

**One decision per deferred object.** `DEFERRED` objects are considered one at a time, in ascending id,
and each receives exactly one residue decision:
- **QUIET:** `FINALIZED` (`quiet_before_final_probe`), with no observation.
- **ACTIONABLE:** the unchanged accepted local proposal (the exact `Observe` of its current probe; no
  replacement gaze) goes to the experiment's final-look gate, which returns
  `FinalProbeDecision(admissible, reason, detail)`:
  - **rejected:** no observation; `FINALIZED` (`final_probe_rejected`);
  - **admitted:** exactly that proposal is executed once; memory and every local state are recomputed;
    then `FINALIZED` (`final_probe_executed`), whatever the resulting local state.
- There is never a second final look, and a `FINALIZED` object never receives another own-target
  observation.

**Return to NORMAL.** If a final observation makes a `NORMAL` object SEEDABLE or ACTIONABLE, for example
through reactivation, the phase returns to NORMAL and ordinary service resumes. When ordinary work is
exhausted again, the residue pass continues with the remaining `DEFERRED` objects.

**Closure.** The scene closes when no `NORMAL` object needs service and no `DEFERRED` object remains.
Quiet versus residual is read from each object's local state at closure.

## Strict final-look gate v1 (Classroom)

This is an **admissibility filter over the frozen local proposal**, not a gaze policy.
- **Scope.** The controller-time decision depends only on the current causal state, the local proposal
  and the known sensor geometry.
- **Forbidden inputs.** It does not read Controller-01A, 01B or 01C artifacts. The run's firewall
  refuses them, and evaluation truth.

1. **Traceable support.**
   - Only an FSG6f proposal exposes a traceable unresolved support set in v1. Any other source is
     rejected: `untraceable_final_support`.
   - The selected candidate's exact OPEN support is reconstructed with the accepted frontier functions
     and the `choose_next` formulas. Its identity is checked against the in-process decision: the
     selected gaze, the counts, the frontier score, and the continuation evidence.
   - Each support element contributes its unresolved look-ahead target `t_e`. There are no rectangles
     and no nearby regions.
2. **Predicted binocular depth core, without rendering.**
   - The proposed calibration is `fov3d.geometry.core.make_calibration(profile, yaw, pitch,
     VERGENCE_DISTANCE_M, head_r_wh, head_origin_w)`. The profile and head pose come from the bootstrap
     `seeds.json`, the same construction the renderer uses.
   - `t_e` is **in both depth cores** when the accepted FSG6f binocular patch test
     (`_target_patch_eye_evidence`, observable) holds in the left **and** the right core. The test uses
     `_project_rectified_core` and the matcher's geometric rectification support (`support_mask`,
     cropped to the 256 px core) of the predicted calibration.
   - This is the same observability test that FSG6f's BOUNDARY_RESOLVED rule applies to completed
     looks. It needs no image.
3. **Genuinely serviceable, non-redundant support.** A support element counts only if all of these
   hold:
   - it is OPEN under the current classification;
   - it is not within 12 mm of the current effective geometry (the accepted `_target_mapped_mask`);
   - its `t_e` is in both predicted cores;
   - the proposed gaze is not an already visited own-target gaze. If it is, the gate rejects with
     `visited_final_gaze`.

   **Prior interrogation**, diagnostic and also used for redundancy: `t_e` was already binocularly
   interrogated if, in any prior own-target look of the object's FSG6f history, the same accepted patch
   test held in both eyes. `novel_service_count` is the number of in-both-cores, OPEN, unmapped support
   elements not previously interrogated.
4. **Admissible iff** the source is traceable, the gaze is not visited, and `novel_service_count > 0`.
   There is no percentage, score or gain estimate.

**Expected Classroom residue** (PROPOSED only; not hard-coded):
- the deferred object is 210 `wall.008`, with an FSG6f proposal [7.6, 18.2] and 30 OPEN support
  elements;
- Controller-01C measured 0/30 in both cores for the executed look, so the gate is expected to reject.

The gate must compute its decision from the final state and the sensor model.

**If the gate admits a final look** in this Classroom replay, the run STOPS before executing it and
emits no scientific marker. There is no accepted sensory evidence for such a look, and rendering is not
authorized. The one-final-observation semantics are proven by synthetic unit tests.

## Replay, not rerender

**Execution.** The frozen `ClassroomController01` adapter supplies memory, probe and revision.
- For every ordinary OBSERVE that Controller-02 selects, the replay first requires the target, the gaze,
  the action source and the object-local step to equal the corresponding accepted Controller-01 action.
  Any divergence STOPS the run with a named error.
- The frozen `observe` then runs unchanged, in a temporary work directory. Its Blender call
  (`controller01._run`) is replaced, only for that call, by a copy of that action's saved controller-time
  acquisition (`calibration.json`, `oracle_observation.npz`) from the source run.
- Memory, target-local context, fusion, HeadEvidence and the observation footprint are therefore
  updated by the accepted code path itself.

**Per-step verification.** After every step, the replay verifies the step's recomputed patch and fused
map against the source run's saved ones, and the step's measurement record (target points, memory
additions, new surfels, map sizes, head evidence) against the accepted action record. Temporary files
are deleted after each step.

**Guards:**
- A process-wide audit hook refuses any process launch (`subprocess.Popen`, `os.system`, `os.exec*`,
  `os.posix_spawn`) for the whole run, so no Blender or other process can start.
- The truth firewall refuses `evaluation.json`, `bootstrap/evaluation_only/*` and the
  Controller-01A/01B/01C preview directories. It records the opened source files.

**PROPOSED behavior.** Controller-02 chooses the same 141 ordinary observations (global steps 0..140) as
Controller-01, because before termination its only behavioral difference is BLOCKED → DEFERRED at the
budget. After step 140 it enters RESIDUE with 210 deferred.

**Compact output** (`previews/controller-02-classroom-replay/`):
- `manifest.json`;
- `actions.json`;
- `events.json`;
- `final-residue.json`, which holds the gate's full detail, including the predicted calibration and the
  per-element in-core and interrogation flags;
- `result.json`.

The source run is referenced by path and hashes; no raw acquisitions, EXRs or maps are copied.

## Checks (`tools/controller/check_controller02.py`)

**Generic unit tests** (Blender-free, synthetic callbacks). Each is also run against source-level
mutants of `fov3d/control/controller02.py` that must be rejected:
1. ACTIONABLE below budget stays `NORMAL` and serviceable;
2. ACTIONABLE at the budget becomes `DEFERRED`, not BLOCKED;
3. a `DEFERRED` object receives no ordinary service;
4. a deferred QUIET object finalizes without a look;
5. an inadmissible final proposal executes 0 looks and finalizes a residual;
6. an admissible final proposal executes exactly 1 look, then finalizes;
7. still ACTIONABLE after its final look → residual, and no second final look;
8. a final observation can reactivate a `NORMAL` object and return the phase to NORMAL;
9. after the reactivated normal work, residue processing resumes;
10. a seed-initialization failure does not block closure;
11. unlocated objects stay separate from residuals;
12. the scene may close with ACTIONABLE residuals;
13. the frozen Controller-01 modules are unchanged;
14. the final gate receives the exact unchanged local proposal, and that is what executes;
15. an unsupported/untraceable final-support source is rejected, not guessed;
16. a duplicate visited final gaze is rejected;
17. support already resolved within 12 mm is not counted;
18. no second residue observation is possible for a finalized object.

Also:
- NORMAL-phase equivalence of the generic loop with Controller-01's `run_control_loop` on randomized
  synthetic scenes without budget hits;
- the no-subprocess guard;
- the sensor-model known answer: `make_calibration` from the bootstrap head pose reproduces every one of
  the 141 saved calibrations;
- architecture: no `tools` import in the new `fov3d` modules; the frozen files byte-identical.

**Classroom replay checks** (`--run`):
- A. source hashes accepted;
- B. source run byte-identical (per-file sha256 manifest before and after, recorded by the run
  procedure);
- C. no process launched;
- D. truth firewall: 0 violations, no evaluation file, no 01A/01B/01C artifact opened;
- E. all 141 ordinary actions equal Controller-01's target, gaze, source, scheduler decision and local
  step;
- F. the accepted natural reactivations (109 at step 7, 178 at step 114) and every `NORMAL`-object event
  equal Controller-01's;
- G. 210 becomes `DEFERRED` at the former watchdog point (step 101, 24 fixations); nothing is BLOCKED;
- H. 210's final local probe reproduces the accepted final Controller-01 state (the accepted 01A terminal
  probe; CHECK MODE only);
- I. the predicted calibration for [7.6, 18.2] equals `make_calibration` from the sensor model (not the
  saved 01B look). CHECK MODE also compares it with 01B's saved calibration, **as validation only**;
- J. the final-support reconstruction reproduces the 30 OPEN support elements (identity checked);
- K. the final core-service computation is recomputed from the recorded `t_e` and calibration. CHECK
  MODE also compares the predicted in-core flags with the Controller-01C audit. **01C is validation
  only, not a Controller-02 decision input**;
- L. the terminal record is internally consistent.

**Fail-capability** is shown with:
- the in-process mutants above;
- corruptions of throwaway copies of the compact output;
- code mutants in throwaway repository copies;
- layout mutants.

The source run is never modified.

## Visual (Policy 1, Level A)

`visuals/controller-02/overview.png`, from `tools/controller/visualize_controller02.py`, has four panels
(CONTROLLER-TIME / DERIVED labelled; no evaluation truth):
1. the NORMAL loop: the attention timeline with 210 reaching the budget and becoming DEFERRED, while the
   scene continues;
2. the end of the NORMAL phase: 24 QUIET + 210 DEFERRED/ACTIONABLE on the final scene reconstruction;
3. the strict final-look gate: 210's OPEN support and look-ahead targets, the proposed gaze, the
   predicted binocular depth cores, and serviced vs unserviced vs previously interrogated support, with
   `novel_service_count`;
4. honest closure: `SCENE_CLOSED`, the quiet / residual / unlocated counts, whether the final look was
   executed or rejected, and `residual != failure`.

## Cost and gates

| command | cost class |
|---|---|
| unit checks | interactive |
| the Classroom replay (141 replayed steps with the accepted probes; no render) | ESTIMATED 8–12 min, above batch; justified as the single scientific run of this step |
| `--run` checks (including a 210 reconstruction for H/J/K) | batch |
| visual | batch |
| the Controller-01, 01B and 01C check modes; layout; Core-14; Classroom; facade; `verify_baseline`; `git diff --check`; compile | interactive to batch |

## Permitted fixes and stop conditions

**Permitted:** bugs in the new modules, the checks, the visual and the narrow declarations.

**Stop** if:
- any ordinary action diverges from Controller-01;
- the replay's per-step verification fails;
- the gate admits a final look in this replay;
- any change to frozen code, a threshold, the matcher, fusion, the truth scope or the local policy
  would be needed;
- the prior-interrogation test cannot be defined without new semantics.

The Cyclopean or FSG6f proposal is never replaced by an invented gaze.
