# Controller-02: residual closure — report

**Markers.**

    CONTROLLER02_IMPLEMENTATION_CHECKS_PASS
    CONTROLLER02_CLASSROOM_SCENE_CLOSED

**Answer to the question: yes.** The accepted Classroom perceptual behavior terminated as
`SCENE_CLOSED`:
- 24 objects are QUIET, and 210 `wall.008` is an explicit residual object (local state ACTIONABLE,
  `FINALIZED: final_probe_rejected`);
- the known-unserviceable final look was not executed (0 final residue observations);
- the accepted local policy was not changed.

Labels used below:
- **MEASURED**: produced by the commands listed;
- **DERIVED**: computed from measured or controller-time data by the stated accepted functions;
- **PROPOSED**: the contract's expectation before the run.

No global-quiescence marker was emitted. `SCENE_CLOSED` is not global quiescence, and 210 is not
complete.

## Branch and provenance

| item | value |
|---|---|
| branch | `controller/controller-02-residual-closure`, from `main` @ `6306458` (Stage Charter 1 accepted), isolated worktree; not merged |
| contract | `620f776` *Specify Controller-02 residual closure* |
| implementation | `e027d84` *Implement Controller-02 residual closure*; `8758790` *Add replay-guard controls to the Controller-02 checks* (checks only) |
| source run | `/home/lvelho/rd/f3d-vision/previews/controller-01-full`; accepted Controller-01. `manifest.json` `d293a98f…`, `actions.json` `12cdbe4d…`, checked live and recorded |
| output | `/home/lvelho/rd/f3d-vision/previews/controller-02-classroom-replay/`: `manifest.json`, `actions.json`, `events.json`, `final-residue.json`, `result.json` (524 KB). No acquisition, EXR or map is copied |
| visual | `/home/lvelho/rd/f3d-vision/visuals/controller-02/overview.png` (+ `overview.json`) |
| frozen files | `fov3d/control/integrated.py` and `fov3d/experiments/classroom_oracle/controller01.py` are byte-identical to `main` (checked by `git diff` and by check 13) |

## Commands

Run from the repository root, at `e027d84` with a clean tracked tree; the checks were re-run at
`8758790`.

    S=/home/lvelho/rd/f3d-vision/previews
    .venv/bin/python -m fov3d.experiments.classroom_oracle.controller02 --repo . \
        --source $S/controller-01-full --out $S/controller-02-classroom-replay
    .venv/bin/python tools/controller/check_controller02.py --run $S/controller-02-classroom-replay \
        --source $S/controller-01-full --audit01a $S/controller-01a-terminal-audit/audit.json \
        --c01b $S/controller-01b-single-continuation \
        --c01c $S/controller-01c-frontier-action-correspondence/audit.json
    .venv/bin/python tools/controller/visualize_controller02.py --run $S/controller-02-classroom-replay \
        --source $S/controller-01-full --visuals /home/lvelho/rd/f3d-vision/visuals/controller-02

**Output of the three commands:**
- **Replay:** 575.6 s wall time (probes 389 s). It printed `ordinary observations 141 (verified 141);
  final residue observations 0; terminal SCENE_CLOSED` and `RESULT CONTROLLER02_CLASSROOM_SCENE_CLOSED`.
- **Checks:** `SUMMARY checked=77 failed=0` and `CONTROLLER02_IMPLEMENTATION_CHECKS_PASS`.
- **Visual:** 0.7 s. It was generated twice, with identical sha256 `a0c07201…`.

The replay's duration exceeds the batch class. The contract justified it as this step's single
scientific run.

## Controller-02 definitions (implemented)

**The generic concepts** live in `fov3d/control/controller02.py`, with no Blender, no file I/O and no
local fixation policy.
- **Local state:** Controller-01's UNLOCATED / SEEDABLE / ACTIONABLE / QUIET, always recomputed from
  memory. BLOCKED is refused by `ObjectStatus`.
- **Disposition:**
  - `NORMAL`;
  - `DEFERRED` (reason `ordinary_budget`);
  - `FINALIZED`, with reasons `seed_uninitializable`, `quiet_before_final_probe`,
    `final_probe_rejected` or `final_probe_executed`.
- **Scene phase:** `NORMAL` → `RESIDUE` → `CLOSED`. RESIDUE may return to NORMAL.
- **`FinalProbeDecision(admissible, reason, detail)`:** the experiment gate's verdict over the unchanged
  proposal.
- **`SceneClosed`:** separate, disjoint groups of quiet objects, residuals `(id, local state, reason)`,
  seed residues and unlocated objects, plus the executed and rejected final looks. Its reason is
  `scene_closed`, which is distinct from `global_quiescence`.

**The loop** (`run_controller02`):
- It is Controller-01's NORMAL loop: the same retain/switch order restricted to NORMAL objects, the same
  probe cache by revision, the same quiet and natural-reactivation events.
- An ACTIONABLE object at the unchanged 24-look budget is DEFERRED instead of blocked. A failed seed is
  finalized.
- When no NORMAL object needs service, each DEFERRED object receives exactly one residue decision, in
  ascending id. A QUIET one is finalized without a look. For an ACTIONABLE one, the gate judges the
  object's current, unchanged `ProbeResult`, and at most that proposal's own action is executed once.
- A final observation may return the phase to NORMAL.
- The scene closes when no NORMAL object needs service and no DEFERRED object remains.

**The Classroom adapter** is `fov3d/experiments/classroom_oracle/controller02.py`:
- `AcceptedReplay` drives the frozen `ClassroomController01`;
- `final_look_gate_v1` is built from small pure functions: `reconstruct_support`,
  `predicted_calibration`, `core_observability`, `prior_binocular_interrogation` and
  `serviceable_support`.

## No-render replay

For every ordinary OBSERVE that Controller-02 selected, the replay did the following (MEASURED):
1. **Identity:** it required the accepted Controller-01 action's target, gaze, source, object-local
   step and global step. The maximum gaze deviation was **0.0°**.
2. **Execution:** it ran the frozen `ClassroomController01.observe` unchanged, in a temporary directory.
   Its Blender call (`controller01._run`) was replaced, only for that call, by a copy of that action's
   saved `calibration.json` and `oracle_observation.npz`. Memory, target context, fusion, HeadEvidence
   and the observation footprint were therefore updated by the accepted code itself.
3. **Verification:** it checked the recomputed patch and fused map against the source run's saved ones,
   and the step's measurement record against the accepted action record. The record fields were
   target-valid and all-instance points, memory additions, map sizes, new surfels, non-new points,
   initialization, empty look, head evidence and vergence.
4. **Cleanup:** it deleted the step's temporary files.

**Result:** **141 / 141 steps verified.**

**Guards:**
- **Process guard:** a process-wide audit hook refused every process launch. There were **0 attempts**,
  so no Blender or other process ran.
- **Truth firewall:** it refused evaluation truth and the Controller-01A/01B/01C preview directories.
  There were **0 violations**; 568 source files were opened, none of them forbidden.

## Classroom result (MEASURED)

### All 141 ordinary actions equal Controller-01's

PROPOSED: identical actions, since before termination the only difference is BLOCKED → DEFERRED.
MEASURED: identical.
- **Actions:** global steps 0..140; target, gaze, source, scheduler decision and reason, local step and
  attention bout all equal Controller-01's. So does every step's measurement record and proposal
  summary (check E).
- **Events:** every NORMAL-object event (25 `seed_initialized`, 26 `quiet`, 2 `natural_reactivation`)
  equals Controller-01's, including the reactivation probes before and after (check F).
- **Natural reactivations preserved:** **109 at step 7** (triggered by 110's look) and **178 at step
  114** (triggered by 224's look).

### The deferral

- One `deferred` event: object **210**, global step **101**, reason `ordinary_budget`, 24 fixations,
  local state ACTIONABLE. This is exactly where Controller-01 recorded `blocked: watchdog`.
- **Local probe at that point:** FSG6f `continue`; 58 OPEN; 1 candidate; proposal [7.6, 18.2]. That is
  the accepted watchdog-prefix state.
- **Afterwards:** no BLOCKED label or event anywhere (check G). 210 received no ordinary service after
  step 101, while the rest of the scene was serviced through step 140. Its local state stayed ACTIONABLE
  throughout; no `local_state_change` was recorded.
- **Probe cost:** Controller-02 re-probed the deferred 210 whenever its memory revision changed, which
  Controller-01 did not do for a blocked object. The totals were 525 probe calls and 1,765 cache hits,
  against Controller-01's 513 and 1,738. This does not affect any action.

### End of the NORMAL phase

After step 140, ordinary work was exhausted:
- **24 objects QUIET**;
- **1 object** in `ACTIONABLE/DEFERRED:ordinary_budget` (210).

Phases: NORMAL from step 0, RESIDUE at step 141 (deferred [210]), CLOSED at step 141.

### The strict final-look gate v1 on 210

**The final proposal** (MEASURED): the unchanged accepted local proposal, source **FSG6f**, gaze
**[7.6, 18.2]**.
- **Probe state:** revision [24, 1,774,969], effective geometry 1,938,913, frontier 350/52/28/270,
  1 candidate.
- **Match with Controller-01A** (check H): this equals the accepted final Controller-01 state, 01A's
  terminal probe, in summary, revision, gaze and source. 01A was used in check mode only.

**Traceable support** (DERIVED with the accepted frontier functions and `choose_next` formulas):
- **30 OPEN support elements** out of 43 raw aligned (3 map-resolved, 10 boundary-resolved), in
  direction (+1, 0);
- identity against the in-process decision: frontier counts, candidate counts, frontier score
  6.135141348988722 (relative 1e-12) and continuation evidence all equal (check J).

**Predicted calibration and cores** (DERIVED, no render):
- **Calibration:** `make_calibration("full", 7.600000000000001, 18.200000000000003, 2.10, head pose
  from bootstrap seeds.json)`.
- **Known answer:** the same construction reproduces **all 141** saved Controller-01 calibrations
  exactly: bit-identical JSON, maximum deviation 0.0 (check I).
- **Core test:** `t_e` is "in both depth cores" when the accepted FSG6f binocular patch test holds in
  the left **and** right cores. The test uses `_project_rectified_core` and the matcher's geometric
  rectification support cropped to the 256 px core.

| quantity (30 OPEN support elements) | value |
|---|---|
| look-ahead target `t_e` in the left predicted core / right predicted core | 0 / 0 |
| in both predicted cores | **0** |
| unresolved (OPEN and not within 12 mm of the current effective geometry) | 30 |
| mapped within 12 mm | 0 |
| previously binocularly interrogated by a prior own look (all support) | **30** |
| previously interrogated among those in both cores | 0 |
| serviceable (unresolved and in both cores) | 0 |
| **novel_service_count** | **0** |

- **Projection:** the predicted core coordinates of `t_e` are u = −72.5 to −34.6 px (left core) and
  −89.5 to −51.4 px (right core). The core spans 0–255 px, so every target lies left of both cores.
- **Decision** (MEASURED): **REJECT**, reason `no_novel_serviceable_support`. No observation was
  executed, and 210 became `FINALIZED: final_probe_rejected`, with local state still ACTIONABLE and 24
  fixations.

**Validation only; not a Controller-02 decision input.** The replay's firewall refused these artifacts
during the run.
- The predicted calibration equals Controller-01B's executed look-25 calibration exactly.
- The 30 support elements and their `t_e` are identical to the Controller-01C audit's.
- The predicted in-both-cores flags (all false) equal 01C's measured flags for the executed look. The
  predicted core coordinates coincide with 01C's measured ranges.

### Scene closure

`SceneClosed` (MEASURED; check L):

| group | value |
|---|---|
| quiet localized objects | 24: 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 123, 140, 166, 167, 168, 172, 174, 178, 201, 202, 216, 224, 225, 234 |
| residual localized objects | **210 `wall.008`**: ACTIONABLE, FINALIZED `final_probe_rejected` |
| seed-initialization residues | 0 |
| unlocated objects | 209 |
| final residue observations executed | **0** |
| final residue proposals rejected | 1 (210) |
| initialized / localized | 25 / 25 |

The terminal is `SCENE_CLOSED`, not global quiescence. PROPOSED: initialized 25, quiet 24,
residual [210], unlocated 209, 0 final looks, final proposal rejected, terminal SCENE_CLOSED. MEASURED:
identical.

## Checks and fail-capability

**Generic, gate and architecture checks.** `check_controller02.py` without `--run` reports
**56/56**. The count includes every rejected negative control. The controls are source-level mutants of
`fov3d/control/controller02.py` or of the gate functions, built in-process.

| test | negative controls rejected |
|---|---|
| 01 ACTIONABLE below budget stays NORMAL | deferral at 1 fixation |
| 02 at the budget → DEFERRED, not BLOCKED | no deferral; budget off by one |
| 03 a DEFERRED object gets no ordinary service | deferred still serviceable; no deferral |
| 04 deferred QUIET finalizes without a look | QUIET sent to the gate |
| 05 inadmissible → 0 looks, residual | gate ignored |
| 06 admissible → exactly 1 look, then finalized | admitted proposal never executed; second final look |
| 07 still ACTIONABLE after the final look → residual, no second look | second final look |
| 08 a final look reactivates a NORMAL object → phase NORMAL | no return to NORMAL |
| 09 residue processing resumes after the reactivated work | second residue pass dropped; no return to NORMAL |
| 10 a seed failure does not block closure | seed failure left in service |
| 11 unlocated separate from residuals | unlocated counted residual |
| 12 closure with ACTIONABLE residuals | closure requires quiet |
| 13 frozen Controller-01 modules byte-identical to `main` | one frozen file edited |
| 14 the gate receives, and the loop executes, the exact unchanged proposal | a copied proposal executed; the gate sees a rebuilt proposal |
| 15 an untraceable final-support source is rejected | source not checked |
| 16 a visited final gaze is rejected | visited not checked |
| 17 support resolved within 12 mm is not counted | 12 mm rule ignored |
| 18 no second residue observation for a finalized object | second final look |
| E0 the NORMAL phase equals Controller-01's `run_control_loop` (60 random scenes) | switch without the forward rule |
| G1 a genuinely serviceable, never-interrogated synthetic proposal is admitted | a gate that always rejects |
| G2 support already binocularly interrogated is not novel | prior interrogation ignored |
| G3 predicted-core known answer (on-axis in both cores; 10° off-axis in neither) | one-eye/any test |
| C the no-process guard refuses and records a launch | no guard |
| D the replay firewall refuses evaluation truth and 01A/01B/01C only | evaluation-only predicate |

**Also:**
- the types refuse BLOCKED and inconsistent dispositions;
- the new `fov3d` modules import accepted functionality only through `fov3d.*`;
- the generic module has no Blender, subprocess, file I/O or local fixation policy.

**Replay checks** (`--run`): **21/21**.
- **A–L:** A, C, D, E (two checks), F, G, H, I (sensor model, plus the 01B validation), J, K (recomputed,
  plus the 01C validation), and L.
- **Replay guards, each with a rejected control:**
  - R1 accepts the accepted action and refuses a gaze +0.05° off;
  - R2 refuses an action beyond the accepted 141, since it has no evidence and rendering is not
    authorized;
  - R3 per-step verification detects a saved patch altered by 1 mm in one point, using a symlinked fake
    source tree that is then removed;
  - R4 the replay firewall refuses reading the 01B look.

**Corruptions of the compact output** (scratch `c02/run_mutants.py`, throwaway copies): **17/17
caught**, each by its named check:
- A: a wrong recorded source hash;
- C: a recorded process attempt;
- D: a recorded violation; an evaluation-only file in the opened list;
- E: an altered gaze; an altered measurement;
- F: the 178 reactivation dropped;
- G: the deferral one step late; a BLOCKED label;
- H: an altered final probe summary;
- I: an altered predicted gaze;
- J: support 29;
- K: an element flagged in both cores; novel count 1;
- L: 210 reported QUIET; marker NOT_CLOSED; 210 left DEFERRED.

**Layout mutation suite** (scratch `c02_layout_mutants.py`): **61/61 caught**, worktree restored.
Beyond the earlier layout and handoff mutants, the new ones are:
- an undeclared new `fov3d` module (caught by the layout checker, and by Controller-01 A8);
- a pre-existing `fov3d` file edited (A8);
- either frozen Controller-01 module edited (Controller-02 check 13);
- a misspelled 02 report;
- the 02 contract untracked.

**Source byte-identity** (check B). The per-file sha256 manifest of the source run (1,678 files) was
identical before and after the canonical run and checks. It is also identical to the manifest taken in
the 01B step.

**Repository gates** (final branch state):

| gate | result |
|---|---|
| layout | 506/506 |
| Controller-01 | 56/56 |
| Controller-01B check mode | 19/19 |
| Controller-01C check mode | 42/42 |
| Core-14 | 64/64 |
| Classroom | 12/12 |
| facade | 16/16 |
| baseline self-test | 12/12 |
| `verify_baseline` | 9/9 |
| `git diff --check` | clean |
| compile of the new and changed Python | OK |

## Visual (Policy 1, Level A)

`/home/lvelho/rd/f3d-vision/visuals/controller-02/overview.png`:
- 2294 × 1823 px, sha256 `a0c0720148601e5796884346b2de5f2f9eef2ac0e0287e69debb576db1a4b901`,
  identical over two generations;
- sidecar `overview.json` (every annotated number);
- regeneration: the `visualize_controller02.py` command above.

The generator recomputes every annotated number from the replay records and refuses to write unless
they agree with `result.json`. It reads controller-time source artifacts under the truth firewall
(0 violations).

1. **Normal loop** (CONTROLLER-TIME). The attention timeline of all 141 looks by source, with quiet
   ticks and the two natural reactivations. 210's row is marked DEFERRED at step 101 (still ACTIONABLE)
   and hatched "no ordinary service" while the rest of the scene continues.
2. **End of the normal phase** (CONTROLLER-TIME). The final active fused maps: 24 QUIET objects in blue,
   210 DEFERRED/ACTIONABLE in orange. These are the source run's maps, which the replay verified step
   by step.
3. **Strict final-look gate** (DERIVED). 210's effective geometry, its 30 OPEN support elements
   (`x_e` → `t_e`; red = not in both cores, purple ring = previously interrogated), the current gaze,
   the proposed gaze and the two predicted depth-core outlines, drawn at the support depth. It is marked
   REJECT: `no_novel_serviceable_support`.
4. **Honest closure** (DERIVED). `SCENE_CLOSED`, with 25 object tiles (24 quiet, 210 residual), the
   closure groups and counts, "residual != failure" and "SCENE_CLOSED != global quiescence".

## Deviations and incidents

1. **Checker declarations.** The layout checker declares the Controller-02 files, as in the contract.
   `check_controller01.py` A8 ("only the two modules are new in `fov3d`") was extended to exactly the two
   declared Controller-02 modules, and it still fails on any pre-existing `fov3d` edit or undeclared new
   file (layout mutants). The layout checker does not pin the frozen Controller-01 files themselves,
   because they postdate its base; Controller-02 check 13 does.
2. **Scenario bugs in the new tests, fixed before the implementation commit.** The first run of the new
   unit checks failed 5 of 56. All five were errors in my synthetic scenarios, not the implementation:
   - a look count that includes the seed;
   - two helper objects whose need exceeded the budget;
   - a step window one step late;
   - a comparison against the probe result recorded after, rather than at, the gate call.

   The implementation was unchanged by these fixes.
3. **Two control mutants corrected.** A "rebuilt proposal" control was initially behaviorally equivalent
   to the real code, because it reused the same action object; it now rebuilds the action. A legacy
   layout mutant collided with the new real file `visualize_controller02.py`; the harness refused it
   rather than delete the file, and its path was renamed.
4. **Plumbing runs** (scratch; discarded):
   - a 5-action replay smoke and a synthetic loop comparison;
   - a full-length trial replay, identical in outcome to the canonical run;
   - trial visuals, which drove three legibility fixes.
5. **Check re-run at `8758790`.** The canonical run script started at a clean `e027d84`. The replay-guard
   checks (R1–R4) were added afterwards, so the canonical checks were re-run at the committed
   `8758790`: 77/77. The replay and visual code are unchanged since `e027d84`.
6. **Extra probing of the deferred object.** See the deferral section; it has no effect on any action.

## What this report does not claim

- The strict final-look predicate is a deliberately conservative v1. It is not claimed optimal.
- Object 210 is not complete. It remains locally ACTIONABLE, as an explicit residual.
- This is not global quiescence, and coverage was not used as an acceptance criterion.
- No local policy, threshold or accepted artifact was changed.
- Visual Language 1, Natural Bootstrap-1 and Tabletop were not started.
