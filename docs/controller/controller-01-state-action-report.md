# Integrated Foveal Controller 01 — state/action report

**Markers.**

    CONTROLLER01_IMPLEMENTATION_CHECKS_PASS

`CONTROLLER01_GLOBAL_QUIESCENCE_REACHED` is **not** emitted: the full run did not reach the
scientific condition (see *Scientific outcome*).

Everything below is **MEASURED** from the identified commands and runs unless it is marked
PROPOSED or ASSUMED. It awaits review by Luiz and Chat. Nothing is merged into `main`, and
`docs/chat-handoff.md` is unchanged.

**Causal question** (from the contract,
`docs/controller/controller-01-state-action-contract.md`). Can a fixed-head, static-scene observer
close the scene-level loop over all bootstrap-localized known objects? The ingredients are the
accepted bootstrap seed oracle, persistent causal scene/object memory, the accepted object-local
FSG6f → Cyclopean policy and a deterministic retain/switch/stop scheduler. A locally quiet object
must be only "quiet now", able to become actionable again after memory changes, and global STOP
may occur only when no localized initialized object can act.

**Answer (MEASURED): not in this run.** The loop closed over all 25 localized objects:
- every object was seeded and initialized;
- 24 ended QUIET;
- two quiet objects were **naturally reactivated** by other objects' observations, with no
  reactivation mechanism, and both were serviced again and became quiet.

The run nevertheless ended `INCOMPLETE(localized_objects_blocked)`. Object 210 (`wall.008`) reached
the inherited 24-look watchdog while its accepted local policy still proposed an FSG6f action
(58 OPEN frontier surfels, one candidate). It was therefore `BLOCKED:watchdog`, not QUIET, and
global quiescence was not claimed. This is the measured scientific result. The controller was not
tuned and the run was not repeated.

## Provenance

| item | value |
|---|---|
| branch | `controller/controller-01` (new; created from the base in an isolated worktree; forward-only; not merged) |
| base | `origin/main` @ `c5f6be63d050d89026b3658a2d033e7c2439caf1`, verified after `git fetch origin` |
| contract | `4233a55f55a98c70cb8a825b6ebc5794992f0ad0` *Specify Integrated Foveal Controller 01*, committed before any production change |
| layout-checker handoff repair | `baf3fed2356f0a5f2bb34326423f878532013c3a` *Align layout checker with the accepted RT1 Chat Handoff* |
| implementation and checks | `c78e8cef5110a13679cea05745787de1f63f876d` *Implement Integrated Foveal Controller 01 with fail-capable checks* |
| repair (Core-14 gate) | `e3bc0693b07386ae9c196825514b2f69bd251f24` *Respect Core-14 gaze-field ownership in the intrinsic-view guard* |
| visual fix | `aea11bec36207f4e0effbc70838ea0b3f5aa191e` *Draw controller visual legend keys as shapes* |
| check addition | `5b66e5938652f31d832cfc06b21bb33347088656` *Test the real probe-cache key; bound the toy control loops* |
| runs measured at | smoke 1 at `e3bc069`; smoke 2 and the full run at `5b66e59`. The tracked tree was clean before each run |
| report | the commit that adds this file |

Execution environment:
- **Worktree.** Everything ran in `<scratchpad>/c01/wt`, where `<scratchpad>` is
  `/home/lvelho/tmp/claude-2002/-home-lvelho-rd-f3d-vision/7ce1753b-200c-46b9-8b38-02221d827353/scratchpad`.
- **Shared checkout.** `/home/lvelho/rd/f3d-vision` was neither switched nor mutated; it stayed on
  `main` @ `e681392`, clean.
- **Data links.** `.venv/` and the ignored `scenes/classroom/*` payload are symlinked from the shared
  checkout. `previews/` is a real directory holding one symlink per accepted reference tree in
  `/home/lvelho/temp/previews-2026.09.28`.
- **New runs.** They were written into the worktree's own `previews/`; the accepted archive was
  not written.
- **Hardware and software.** Blender 5.2.1 LTS, RTX 4090, OptiX.

Changed files, `c5f6be6..5b66e59` (plus this report):

    A  docs/controller/controller-01-state-action-contract.md
    A  fov3d/control/integrated.py
    A  fov3d/experiments/classroom_oracle/controller01.py
    A  tools/controller/check_controller01.py
    A  tools/controller/plot_controller01.py
    M  tools/repository/check_repository_layout.py

No sealed `tools/` root module, no pre-existing `fov3d/` file, and no test fixture, scene manifest
or accepted reference tree changed.

## What was built

**`fov3d/control/integrated.py`** holds the reusable concepts. It imports only `numpy`, the standard
library, `fov3d.epistemic.partition` and `fov3d.scene.partition`. It has no Blender, evaluator,
historical candidate/run/gaze policy, local fixation policy or `tools.*` import.
- **Service states** (`UNLOCATED`, `SEEDABLE`, `ACTIONABLE`, `QUIET`, `BLOCKED` with a
  `blocked_reason`), and `ObjectSummary(instance_id, state, blocked_reason)`, which is all the
  scheduler sees.
- **Decision types.** `Observe(target_id, gaze, vergence, focus, source)`; `Stop`, which accepts only
  `global_quiescence`; `Incomplete`; and `CapReached`, for smoke only.
- **`ProbeResult`**, with `can_act` and `choose_action` as two views of its single `action` field.
- **`schedule(current_id, summaries)`**: pure deterministic retain/switch/stop in ascending,
  cyclic id order.
- **`run_control_loop`**: the generic closed loop, shared by the real run and the synthetic
  checks. It recomputes every localized initialized object's service state after each observation.
  It reuses a probe result exactly while the probe's inputs are unchanged (the revision key), keeps
  BLOCKED sticky, and applies the watchdog after the 24th look and after later memory changes. It
  records natural reactivation, quiet and block events. There is no reactivation operation.
- **`target_epistemic_view`**, E_t(i): `support_depth_from_map` per measured instance →
  `joint_owner` → `build_epistemic_partition`, from the target-neutral HeadEvidence fields and the
  global `seen_any`. It asserts the Core-14 intrinsic row/diag schema (a whitelist).
- **`TruthFirewall`**: a `sys.addaudithook` guard on `open`, `os.listdir` and `os.scandir`.

**`fov3d/experiments/classroom_oracle/controller01.py`** is the Classroom adapter and executable. It
is described in the contract. The accepted Blender acquisition is launched with the accepted
runner's script and arguments (`fov3d.ENGINE_DIR/classroom_oracle1_render.py`, a process
boundary, not an import). The probe is the accepted `object_policy.choose_next` → `epistemic.choose_next`
sequence over each object's own-look context and its effective target geometry.

## Commands actually run

| command | at | wall | cost class |
|---|---|---|---|
| `git fetch origin`; `origin/main` = `c5f6be6…` verified; branch absent locally and remotely; `git worktree add -b controller/controller-01 … c5f6be6` | base | — | interactive |
| pre-implementation gates (next section) | `c5f6be6` | 0.4–3.5 s each | interactive |
| read-only cost probes on `previews/partition-graph-2-source-full` (scratch scripts) | — | < 1 min | interactive |
| gate set (next section) | `c78e8ce`, `e3bc069`, `5b66e59` | 0.4–3.6 s each | interactive |
| Core-1…10 and Partition-Graph 1–8b checkers (unmodified) | `c78e8ce` + repair | ≤ 1 min | interactive |
| `.venv/bin/python -m fov3d.experiments.classroom_oracle.controller01 --repo . --out previews/controller-01-smoke --profile small --device OPTIX --smoke` (later renamed `controller-01-smoke-e3bc069`) | `e3bc069` | 21.63 s | batch |
| the same command, fresh `previews/controller-01-smoke` | `5b66e59` | 21.91 s | batch |
| `.venv/bin/python tools/controller/check_controller01.py --run previews/controller-01-smoke` | `5b66e59` | 2 s | interactive |
| `.venv/bin/python tools/controller/plot_controller01.py --run previews/controller-01-smoke` | `5b66e59` | < 2 s | interactive |
| `.venv/bin/python -m fov3d.experiments.classroom_oracle.controller01 --repo . --out previews/controller-01-full --profile full --device OPTIX` | `5b66e59` | **1222.93 s** | overnight class (> 5 min), explicitly authorized |
| `.venv/bin/python tools/controller/check_controller01.py --run previews/controller-01-full` | `5b66e59` | 2.12 s | interactive |
| `.venv/bin/python -m fov3d.experiments.classroom_oracle.eval --run previews/controller-01-full` (after `control_complete: true`) | `5b66e59` | 1.18 s | interactive |
| `.venv/bin/python tools/controller/plot_controller01.py --run previews/controller-01-full` | `5b66e59` | < 3 s | interactive |
| mutation harnesses (scratch): source mutants, run-artifact corruptions, layout mutations | `5b66e59` | minutes | batch |

Exactly one full scientific run was executed.

## Gates

| gate | base `c5f6be6` (before any change) | final `5b66e59` |
|---|---|---|
| `tools/controller/check_controller01.py` | — | `SUMMARY checked=56 failed=0` (0.58 s) |
| `tools/conceptual_core/check_conceptual_core14.py` | 64/0 | `SUMMARY checked=64 failed=0` (3.57 s) |
| `tools/classroom_oracle/check_classroom_oracle1.py` | 12/0 | `SUMMARY passed=12 failed=0` |
| `tools/consolidation/check_fov3d_facade.py` | 16/0 | `SUMMARY checked=16 failed=0` |
| `tools/repository/check_repository_layout.py` | **487/3 (pre-existing)** | `SUMMARY checked=493 failed=0` |
| `scripts/verify_baseline.sh` | 9/0 | `[verify] SUMMARY passed=9 failed=0` (31/31 baseline files accounted) |
| `git diff --check` (worktree, and `c5f6be6..HEAD`) | clean | clean |
| compile every changed/new Python file | — | 5 files, 0 errors |
| the 16 sealed root modules byte-identical to the base | — | 16/16 (checker A7 and `verify_baseline`) |
| Core-1…10 conceptual checkers (unmodified) | — | 13, 20, 27, 32, 38, 35, 22, 20, 24, 29 checked; 0 failed |
| Partition-Graph checkers 1–8b (unmodified) | — | 13, 16, 20, 14, 12, 12, 12, 10, 12 checked; 0 failed |

## Failing gates, repairs and incidents (chronological)

1. **Pre-existing layout-checker failure.** At the base `c5f6be6` the layout checker reported
   `checked=487 failed=3`:
   - "chat handoff keeps accepted main at Core 14";
   - "chat handoff does not claim the transition accepted";
   - "no obsolete moved path in docs/chat-handoff.md: ['tools/dev/']".

   **Diagnosis.** In a detached worktree at `b12bdef` it reported 487/0. The only change from
   `b12bdef` to `c5f6be6` is the acceptance administration of `docs/chat-handoff.md`, so the
   checker's handoff assertions still encoded the pre-acceptance state. The third failure is the
   accepted sentence "`tools/dev/` is gone."

   **Repair.** `baf3fed`, a separate commit, declared in the contract before implementation. The two
   status assertions became exact assertions of the accepted state: main @ `b12bdef`, the RT1
   marker, Core 14 as the scientific milestone, and the transition recorded as accepted. The one
   verbatim removal sentence is allowed. On the untouched `c5f6be6` tree this gives 487/3 → 487/0.
   Any other `tools/dev/…` path in the handoff still fails (mutation below).

   **This repair touches a check outside the Controller-01 scope and needs review.**
2. **Layout accommodation for the authorized additions** (in `c78e8ce`, as the contract declared):
   - the controller stage directories;
   - the declared Controller-01 files;
   - `fov3d/` "differs by zero bytes from the base" became "differs from the base only by the declared
     Controller-01 additions", together with "the only new `fov3d/` files are the declared modules,
     absent at the base".

   The count went 487 → 493: two directory checks, "declared Controller-01 files are tracked",
   the new-`fov3d` check, and the stale-path scans of the two new tools.
3. **Core-14 gate failure at `c78e8ce`.** `check_conceptual_core14.py` reported `checked=64
   failed=1`, "H: no duplicate gaze metric: only gaze_context calls _angular_distance_deg and names
   the gaze field".

   **Diagnosis.** `integrated.py` named the historical gaze field literally, in a blacklist of
   fields the intrinsic view must not carry. Core 14 forbids any `fov3d` module other than
   `gaze_context` from naming it. This was a genuine conflict with an accepted invariant.

   **Repair.** `e3bc069`. The blacklist became a positive whitelist of the Core-14 intrinsic row and
   diag keys, which is strictly stronger. The explicit historical field names now appear only in the
   Controller-01 checker, outside `fov3d`. The Core-14 checker is unchanged, and all Core 1–10 and
   Partition-Graph checkers pass.
4. **Visual defect** (smoke 1). Pillow's default font lacks the em-dash, dotted-line, ring and cross
   glyphs, so the legend showed boxes. **Repair** `aea11be`: those keys are drawn as shapes.
5. **Coverage gap** (after smoke 1). The real probe-cache key `ClassroomController01.revision` was not
   tested; only the loop's cache logic was, in the toy world. **Repair** `5b66e59`:
   - the memory bookkeeping of `observe` was factored into `remember_measurements`, with the same
     behavior (smoke 2 is identical to smoke 1 on every controller field);
   - check 12c was added.

   In the same commit the toy loops got a 500-action safety cap. A source mutant ("cache ignores the
   revision") had been caught by check 12, but then hung a negative-control loop. Now a
   non-terminating mutant ends in a named failure.
6. **Harness incident, no committed state affected.** The first run of the adapted layout-mutation
   harness still contained the RT1 mutation "empty `docs/controller/` reserved". Its `makedirs`
   failed because the directory now exists, and the harness's cleanup then removed
   `docs/controller/`, deleting the committed contract file **from disk**. The file was restored with
   `git checkout --` and the tracked tree verified clean. The harness now refuses any mutation whose
   "created" path already exists.

7. **Checker defect found while verifying this report.** The negative control of check 12c (an
   own-look-only revision key) was rejected only by a crash (`KeyError` on a catalog-only id), not by
   its named assertion. The mutant was corrected, so it now fails with "revision of 7 unchanged after
   a look measured instance 7". The fix is committed with this report. All 26 controls were
   re-verified to fail on named assertions, and the unit suite, the three `--run` validations and the
   source-mutation suite were re-run.

No production behavior was repaired after a measured run. No threshold, constant, matcher, fusion,
scheduler rule, watchdog value or success criterion was changed.

## Deviations from the contract

1. **The intrinsic-view guard is a whitelist**, not a named blacklist (repair 3). The contract's
   requirement — no `candidate`, `candidate_region_count`, `reconstruction_status` or gaze-distance
   field — is enforced more strictly.
2. **More checks than the 17.** They add 11b (probe purity with the real FSG6f/Cyclopean), 12b (cache
   equals cache-free), 12c (real revision key), 16b (quiet at 24; reactivation at 24) and the A5b
   visual-tool truth check.
3. **Two smoke runs**, one at `e3bc069` and one at the final implementation commit `5b66e59`. Both
   are recorded.
4. **The layout-checker handoff repair** `baf3fed` was declared in the contract, but it modifies a
   check beyond the narrow docs/tools accommodation that the handoff prompt anticipated.

## Fail-capability evidence

| suite | result |
|---|---|
| `check_controller01.py` unit and architecture | 56 checks = 21 behavioral + **26 negative controls rejected** + 9 architecture. Every control was verified to fail on a named behavioral assertion, not a crash |
| source mutants on `integrated.py`/`controller01.py` (scratch `src_mutants.py`, throwaway copies) | **23/23 caught** by named FAILs; the unmutated copy passes 47/0 (unit part) |
| run-artifact corruptions of a smoke copy (scratch `run_mutants.py`) | **14/14 caught**; the unmutated copy passes 13/0 |
| layout mutations (scratch `layout_mutants.py`, the RT1 suite adapted) | **29/29 caught**; worktree restored; 493/0 before and after |

Negative controls inside the checker include:
- mutant schedulers: never-retain, retain-anything, restart-scan, input-order, seedable-ignored,
  actionable-ignored, blocked-as-quiet, unlocated-as-seedable, and a ranking selector using
  epistemic side information;
- an unlocated-as-quiet classification;
- a `can_act` from a separate flag, and a probe skipping the Cyclopean handoff;
- an input-mutating probe;
- stale-key and own-look-only caches;
- a map-only geometry, and a geometry fusing cross-target points into the map;
- a target-relative head view, and a candidate-annotated view;
- a watchdog reported as quiet;
- a permissive firewall predicate.

Source mutants (23):
- seedable not retained; switch restarting from the first id; blocked ignored at termination;
  input order;
- watchdog one look late; watchdog reported QUIET;
- reactivation event not emitted; reason not annotated;
- seed failure treated as initialized;
- cache ignoring the revision;
- ProbeResult state inverted; `can_act` from the detail;
- `seen_any` replaced by `depth_seen`; intrinsic guard disabled;
- firewall not raising;
- unlocated objects QUIET; STOP accepting any reason;
- empty target support in the view;
- probe skipping the Cyclopean handoff; effective geometry ignoring memory;
- `evaluation.json` not forbidden; revision ignoring measured points;
- probe mutating the visited list.

Run corruptions (14):
- a retain logged as a switch; the target of a retained action changed;
- the dense-truth flag set true; truth in the opened-file list;
- a memory addition off by one; a patch replaced by another look's;
- an effective-geometry row dropped;
- the reactivation event removed;
- a false `global_quiescence` terminal;
- vergence changed on one action;
- a post-seed action labelled `oracle_seed`;
- a view summary carrying `candidate`;
- the switch count off by one;
- the service states after a step altered.

Layout mutations: the 22 RT1 mutations, with two whose premise changed replaced by their
counterparts:
- "empty `docs/controller`" became "empty `docs/controller2`";
- "handoff claims acceptance" became "handoff reverted to main at Core 14" and "handoff reverted to
  the transition proposed".

The seven new mutations are:
- a handoff naming a `tools/dev/…` path;
- an undeclared tracked `fov3d` file;
- an edited existing `fov3d` file (the Core-14 partition);
- an undeclared tracked `docs/controller` file;
- an undeclared tools stage directory;
- a missing declared Controller-01 file;
- the second handoff reversion above.

## Smoke runs (plumbing only; not scientific)

| | smoke 1 (`e3bc069`) | smoke 2 (`5b66e59`) |
|---|---|---|
| directory | `previews/controller-01-smoke-e3bc069` | `previews/controller-01-smoke` |
| wall | 21.63 s | 21.91 s |
| terminal | `CAP smoke_cap_reached` (8 actions) | identical |
| `--run` validation | 13/0 (final checker) | 13/0 run checks (69/0 with the unit suite) |

Smoke 2 is identical to smoke 1 on every controller field: targets, gazes, sources, scheduler
decisions and reasons, valid points, memory additions, service states and events.

Observed in the small profile:
- 107 `Text` got 65 target points (< 100), so it is `BLOCKED:seed_uninitializable` (the full profile
  gives 403);
- 108 was quiet after its seed;
- 109 took two Cyclopean looks, then went quiet;
- 110 took two FSG6f looks, and its last look added 2 cross-target points of 109, which **naturally
  reactivated 109**: Cyclopean eligible cells 0 → 26;
- the cap was then reached.

## Full run: control result

Run directory: `<scratchpad>/c01/wt/previews/controller-01-full` (22 GB, 1,678 files).

| artifact | sha256 |
|---|---|
| `manifest.json` | `d293a98fd6bb285e882186af8fbeadba29ab1d1d62efea23f3ed0ff5c62c0e91` |
| `actions.json` | `12cdbe4d760cce6c494075e4368f9424805b51b997b8b21724bf87f71cc55afd` |
| `evaluation.json` | `76cb1e5df88ea401aed6409327bd51fc149fa05b174a1e67b014e671b34512b6` |

Controller-time console line:

    [controller01] COMPLETE {"actions": 141, "bouts": 27, "localized": 25, "reactivations": 2, "smoke": false, "switches": 26, "terminal": {"blocked": [[210, "watchdog"]], "reason": "localized_objects_blocked", "type": "INCOMPLETE"}}

`--run` validation: all 13 run checks pass (`SUMMARY checked=69 failed=0` with the unit suite). They
cover:
- a replay of the pure scheduler over the logged service states, reproducing all 141 decisions and
  the terminal;
- the measurement memory rebuilt from the 141 saved patches, reproducing every logged addition and
  every final effective geometry;
- the firewall.

**Bootstrap is unchanged, as measured.** `bootstrap/seeds.json`, `bootstrap/instance_catalog.json`
and `bootstrap/evaluation_only/manifest.json` are byte-identical to the accepted run
`partition-graph-2-source-full`. All **25/25 seed-look oracle patches** are byte-identical to that
run's `fix_00` patches (same gaze, same render noise seeds). The post-seed trajectories diverge
for most objects; the effective geometry is the intended cause.

| quantity | value |
|---|---|
| known catalog objects | 234 |
| localized (bootstrap seed) | 25 |
| unlocated (reported separately; outside the claim) | 209 |
| successfully initialized | 25 |
| blocked at initialization | 0 |
| watchdog-blocked | **1** (210 `wall.008`) |
| QUIET at termination | 24 |
| ACTIONABLE / SEEDABLE at termination | 0 / 0 |
| total global observations | **141** (25 `oracle_seed`, 50 `fsg6f`, 66 `cyclopean_epistemic`) |
| switches | **26** (24 `switch` + 2 annotated `natural_reactivation`) |
| attention bouts | 27 |
| quiet episodes | 26 (24 objects once; 109 and 178 twice) |
| natural reactivations | **2** |
| watchdog hits / initialization failures | 1 / 0 |
| zero-new-surfel looks / empty looks | 3 / 0 |
| probe calls / exact cache reuses | 513 / 1,738 |
| terminal | `INCOMPLETE(reason="localized_objects_blocked", blocked=[(210, "watchdog")])` |
| `dense_evaluation_truth_opened_during_control` | `false`; firewall violations 0; 284 run files opened for reading, all `json`/`npz`, none under `bootstrap/evaluation_only` and no `evaluation.json` |
| fixed vergence / focus on every action | 2.10 m (FSG6f `VERGENCE_DISTANCE_M`, also read back from every `calibration.json`) / depth of field disabled |
| wall | 1222.93 s. bootstrap 3.3 s; control 1198.8 s, of which render 626.6 s (4.44 s per look), probes 358.3 s and E_t views 48.4 s |

Attention bouts (object, first global step, looks):

    107@0×1, 108@1×1, 109@2×3, 110@5×3, 111@8×10, 112@18×4, 113@22×3, 114@25×4, 115@29×8,
    116@37×1, 123@38×8, 140@46×2, 166@48×6, 167@54×1, 168@55×1, 172@56×1, 174@57×5, 178@62×6,
    201@68×6, 202@74×4, 210@78×24, 216@102×1, 224@103×17, 225@120×7, 234@127×7,
    109@134×2 (natural reactivation), 178@136×5 (natural reactivation)

### Final service state of every localized object

| id | name | final state | looks | seed / FSG6f / Cyclopean | bouts | quiet episodes | reactivations | final map | effective geometry | own / cross-target measured points |
|---|---|---|---|---|---|---|---|---|---|---|
| 107 | Text | QUIET | 1 | 1/0/0 | 1 | 1 | 0 | 403 | 4,190 | 403 / 3,384 |
| 108 | Text.001 | QUIET | 1 | 1/0/0 | 1 | 1 | 0 | 485 | 2,495 | 485 / 1,525 |
| 109 | alphabet | QUIET | 5 | 1/0/4 | 2 | 2 | 1 | 2,829 | 36,314 | 3,592 / 29,893 |
| 110 | beams | QUIET | 3 | 1/2/0 | 1 | 1 | 0 | 36,317 | 346,150 | 38,131 / 271,702 |
| 111 | blackBoard | QUIET | 10 | 1/5/4 | 1 | 1 | 0 | 160,048 | 1,231,455 | 364,945 / 706,462 |
| 112 | blackBoardLamp | QUIET | 4 | 1/2/1 | 1 | 1 | 0 | 8,449 | 112,892 | 13,597 / 90,846 |
| 113 | blackBoard_upPart | QUIET | 3 | 1/0/2 | 1 | 1 | 0 | 4,198 | 63,259 | 4,768 / 54,293 |
| 114 | blackboardLamp | QUIET | 4 | 1/1/2 | 1 | 1 | 0 | 1,729 | 19,615 | 2,725 / 15,161 |
| 115 | boardFrame | QUIET | 8 | 1/0/7 | 1 | 1 | 0 | 25,264 | 242,919 | 37,180 / 180,475 |
| 116 | ceiling | QUIET | 1 | 1/0/0 | 1 | 1 | 0 | 1,783 | 21,271 | 1,783 / 17,705 |
| 123 | ceilingMoulding | QUIET | 8 | 1/4/3 | 1 | 1 | 0 | 32,047 | 222,310 | 52,654 / 137,609 |
| 140 | coat 1 | QUIET | 2 | 1/0/1 | 1 | 1 | 0 | 12,480 | 107,226 | 17,605 / 77,141 |
| 166 | lettersPlank | QUIET | 6 | 1/2/3 | 1 | 1 | 0 | 37,202 | 549,865 | 62,570 / 450,093 |
| 167 | lettersPlank.001 | QUIET | 1 | 1/0/0 | 1 | 1 | 0 | 5,071 | 58,608 | 5,071 / 48,466 |
| 168 | lettersPlank.002 | QUIET | 1 | 1/0/0 | 1 | 1 | 0 | 5,601 | 30,516 | 5,601 / 19,314 |
| 172 | pipe | QUIET | 1 | 1/0/0 | 1 | 1 | 0 | 6,094 | 34,694 | 6,094 / 22,506 |
| 174 | plank | QUIET | 5 | 1/2/2 | 1 | 1 | 0 | 18,825 | 160,648 | 28,928 / 112,895 |
| 178 | sol | QUIET | 11 | 1/7/3 | 2 | 2 | 1 | 133,989 | 530,549 | 212,765 / 183,795 |
| 201 | verticalPipe | QUIET | 6 | 1/0/5 | 1 | 1 | 0 | 18,106 | 163,948 | 33,131 / 112,711 |
| 202 | wall | QUIET | 4 | 1/2/1 | 1 | 1 | 0 | 54,534 | 388,737 | 88,484 / 245,719 |
| 210 | wall.008 | **BLOCKED:watchdog** | 24 | 1/13/10 | 1 | 0 | 0 | 163,944 | 1,938,913 | 502,605 / 1,272,364 |
| 216 | wallPlug.001 | QUIET | 1 | 1/0/0 | 1 | 1 | 0 | 1,110 | 12,326 | 1,110 / 10,106 |
| 224 | woodBase | QUIET | 17 | 1/8/8 | 1 | 1 | 0 | 214,387 | 1,670,559 | 545,562 / 910,610 |
| 225 | woodBaseboard | QUIET | 7 | 1/0/6 | 1 | 1 | 0 | 35,530 | 214,720 | 46,736 / 132,454 |
| 234 | worldMap | QUIET | 7 | 1/2/4 | 1 | 1 | 0 | 78,924 | 664,456 | 198,332 / 387,200 |

For reference only, the accepted Classroom-Oracle-1 run `partition-graph-2-source-full` used
104 looks, and all 25 objects ended `attention_complete`. Controller 01 changed the look count of 14
of the 25 objects. For example:
- 123: 1 → 8;
- 115: 3 → 8;
- 225: 2 → 7;
- 210: 19 → 24 (watchdog);
- 224: 19 → 17.

This comparison is descriptive: the local policy now reads effective geometry, as designed.

### The watchdog block

Object 210 was attended in bout 21, steps 78–101. It took 24 looks: 1 seed, 13 FSG6f and
10 Cyclopean. Its new surfels per look were:

    44250, 16565, 4804, 14151, 9800, 19301, 277, 4482, 1763, 1060, 2187, 2093, 461, 10086,
    1160, 12220, 2311, 3134, 4658, 6047, 2979, 54, 55, 46

After the 24th look, the probe (revision `[24, 1584958]`) was still ACTIONABLE:
- FSG6f `continue`, 58 OPEN frontier surfels, one candidate;
- so the loop recorded `blocked` (reason `watchdog`, previous state ACTIONABLE, 24 fixations).

The loop then serviced every remaining object and both reactivated objects, and returned INCOMPLETE
only when no serviceable object remained.

### Natural reactivations (both are real-scene measurements)

| object | quiet since | reactivated after | trigger (the observed target) | memory added to the object since quiet | FSG6f before → after | Cyclopean eligible cells before → after | serviced at |
|---|---|---|---|---|---|---|---|
| 109 `alphabet` | step 4 | step 7 | 110 `beams` | 4 cross-target points (from 110's look at step 7) | `no_frontier` → `no_frontier` | **0 → 28** (map-support cells 2,173 → 2,191; shoreline 897 → 925) | step 134 (2 Cyclopean looks, then QUIET at step 135) |
| 178 `sol` | step 67 | step 114 | 224 `woodBase` | 36,748 cross-target points (201: 8,506; 224: 28,242; steps 72, 104, 109, 112, 114) | `no_frontier` → `no_frontier` | **0 → 189** (map support 11,318 → 13,129; shoreline 814 → 981) | step 136 (5 looks, then QUIET) |

Observations:
- **Both reactivations came through the Cyclopean handoff.** Cross-target geometry extended the
  object's effective support, and its new shoreline lay in chart cells that the object's **own** looks
  had never observed.
- **Memory changes do not by themselves reactivate.** Object 178 received cross-target points at
  steps 72, 104, 109 and 112 and stayed QUIET; it became ACTIONABLE only at step 114.
- **Service waits for the cyclic scan.** The scheduler reached 109 127 steps after its reactivation:
  deterministic cyclic order serves reactivated objects only when the forward scan wraps, and there
  is no ranking. When 109 was finally serviced, the probe had been recomputed from the newer memory.
  Its action (`[1.8, 13.2]`) is not the gaze proposed at reactivation (`[-7.0, 14.1]`).

Intrinsic E_t(i) at the reactivations: kind cell counts (`TARGET_SUPPORT`, `OTHER_SURFACE`,
`UNKNOWN`, `AMBIGUOUS_BOUNDARY`, `TARGET_EVIDENCE_UNMAPPED`), and the UNKNOWN cells adjacent to
target support:

| object | before (entry into QUIET) | after (reactivation) | UNKNOWN cells adjacent to target support |
|---|---|---|---|
| 109 | 2,173 / 23,806 / 173,448 / 1,474 / 0 (`global_0004_quiet`) | 2,191 / 39,925 / 156,952 / 1,833 / 0 (`global_0007_natural_reactivation`) | 172,387 → 155,891 |
| 178 | 11,318 / 149,823 / 34,100 / 5,660 / 0 (`global_0067_quiet`) | 13,129 / 158,461 / 22,856 / 6,455 / 0 (`global_0114_natural_reactivation`) | 26,279 → 20,515 |

The views are in `objects/instance_XXXX/epistemic/*.npz|json`. The before/after probe summaries,
revisions and memory provenance are in the events of `actions.json`.

### Target-relative intrinsic views at important transitions

54 views were saved at transitions:
- 25 seed initializations;
- 26 quiet entries;
- 2 reactivations;
- 1 watchdog block.

25 terminal views were also saved, one per initialized object. None uses evaluator truth, and every
saved summary has `truth_used: false`.

In the terminal views:
- `TARGET_EVIDENCE_UNMAPPED` is 0 for all 25 targets;
- UNKNOWN is 15,160 cells in 21 regions for every target (largest 12,636);
- UNKNOWN regions adjacent to target support remain for 140 (3 regions, 1,452 cells), 174 (1, 864),
  178 (9, 13,238), 201 (1, 12,636), 210 (2, 1,909), 224 (9, 13,231) and 225 (6, 13,229).

These are descriptive. The accepted local policy, not the partition, decides actions in
Controller 01.

### Cross-target measurement provenance

The global `InstanceMeasurementMemory` holds 7,843,577 measured points from 141 looks, in
33 observed instances. Each look measured 6.21 instances on average (at most 11). For the 25
localized objects:
- own-target points: 2,274,857;
- cross-target points: 5,494,429 (70.7 %);
- final active maps: 1,059,349 surfels in total;
- effective geometries: 8,828,635 points = maps + own + cross.

Eight **unlocated** catalog instances were measured incidentally: 1, 3, 10, 117, 130, 143, 145 and
213, with 74,291 points in total. They remain UNLOCATED and outside the quiescence claim. Per-object
sources are in `manifest.cross_target_provenance`, and per-point provenance in each
`final_effective_geometry.npz`.

## Evaluation (descriptive only; opened only after `control_complete`)

The existing evaluator read the integrated run unchanged, so no separate evaluator was needed:

    [classroom-oracle1-eval] COMPLETE {"coverage": 0.9833720295001366, "fixations": 141, "instances": 25, "terminations": {"BLOCKED:watchdog": 1, "QUIET": 24}}

| quantity | Controller 01 | accepted Classroom-Oracle-1 (reference) |
|---|---|---|
| reachable samples | 29,288 | 29,288 |
| covered samples (12 mm, active-target final maps) | **28,801** | 25,618 |
| coverage (micro) | **0.9834** | 0.8747 |
| fixations | 141 | 104 |
| zero-new-surfel looks | 3 | 4 |

Per-object coverage is 1.0000 for 16 objects. The other 9 are:

| object | coverage |
|---|---|
| 112 | 0.9925 |
| 113 | 0.9859 |
| 114 | 0.8491 |
| 115 | 0.9922 |
| 140 | 0.8765 |
| 178 | 0.9884 |
| 202 | 0.9901 |
| 210 | 0.9364 |
| 224 | 0.9994 |

The full table is in `evaluation.json`. The evaluator measures the **active-target fused maps**
(the accepted metric), not the effective causal geometry. Coverage is not a Controller-01 success
criterion, and nothing from the evaluation fed back into the controller.

## Inspectable visuals

These are regenerable previews and are not committed. Regenerate them with
`.venv/bin/python tools/controller/plot_controller01.py --run previews/controller-01-full`:
- `previews/controller-01-full/controller-attention-timeline.png`: x = global action, y = object.
  It shows the seed, FSG6f and Cyclopean markers, the attention bouts, the switches, the quiet
  entries, the two reactivation rings ("reactivated by 110 @ 7" and "by 224 @ 114") and the
  watchdog cross at 210.
- `previews/controller-01-full/controller-gaze-chart.png`: the 141 executed gazes in the
  ±25° × ±20° controller domain. Each gaze is labelled by global action, each object id sits at
  its seed, and the first looks after a reactivation (134, 136) are ringed.
- The same two files exist for `previews/controller-01-smoke`.

## Acceptance

**Implementation acceptance: PASS.**

| criterion | status |
|---|---|
| contract committed before implementation | MEASURED pass (`4233a55` precedes `c78e8ce`) |
| conceptual API boundaries | MEASURED pass (A1–A5; fresh-import footprints) |
| no sealed runtime module changed | MEASURED pass (16/16 byte-identical; `verify_baseline` 9/9) |
| truth firewall holds | MEASURED pass (tests 17; full run: 0 violations, 284 files opened, none truth) |
| scheduler tests | MEASURED pass (01–10 with controls) |
| synthetic natural reactivation | MEASURED pass (12, 12b, 12c) |
| service-probe consistency | MEASURED pass (11, 11b) |
| Core-14 intrinsic partition intact | MEASURED pass (Core-14 checker 64/0; A8; every pre-existing `fov3d` file unchanged) |
| baseline, facade, Classroom and layout gates | MEASURED pass (layout after the declared accommodation and the `baf3fed` handoff repair, which awaits review) |
| smoke run structurally valid | MEASURED pass (13/13 run checks) |
| full run structurally valid | MEASURED pass (13/13 run checks) |
| inspectable visual | MEASURED pass |
| report | this document |

    CONTROLLER01_IMPLEMENTATION_CHECKS_PASS

**Scientific outcome: global quiescence NOT reached (MEASURED).**

| condition | full run |
|---|---|
| every bootstrap-localized, successfully initialized object is QUIET | no: 24/25 QUIET; 210 BLOCKED |
| no SEEDABLE object remains | yes (0) |
| no ACTIONABLE object remains | yes (0) |
| no localized object BLOCKED (initialization or watchdog) | **no**: 210 `BLOCKED:watchdog` |

The terminal is `INCOMPLETE(localized_objects_blocked)`. The 209 UNLOCATED catalog objects are
excluded from the claim. `CONTROLLER01_GLOBAL_QUIESCENCE_REACHED` is not emitted.

What the run does establish (MEASURED):
- the closed scene-level loop runs causally end to end over the 25 localized objects;
- the retain/switch schedule is deterministic and reproduces exactly under replay;
- quiet objects are recomputed from memory, and quiet is "quiet now": two real natural reactivations
  occurred, were serviced and returned to quiet;
- STOP was correctly withheld because of the blocked object.

## Unresolved questions (for Luiz and Chat)

1. **Acceptance.** Whether to accept the implementation, the measured scientific outcome and the
   layout-checker handoff repair `baf3fed`.
2. **The 210 block.** At the watchdog the accepted local policy still proposed an FSG6f look, with
   the last three looks adding 54, 55 and 46 surfels. Possible directions:
   - accept the 24-look engineering bound;
   - revisit the local continuation/stopping behavior under effective geometry, which is a policy
     change;
   - treat diminishing returns explicitly, which is a new policy.

   None of this is decided here.
3. **Target-local Cyclopean evidence.** Both reactivations came from the Cyclopean
   `NEVER_OBSERVED` test using only the object's own looks: shoreline cells already observed by
   other objects' looks still count as never observed. Whether a global observation footprint should
   be used is contract open question 1.
4. **Service latency of reactivated objects.** The deterministic cyclic order serves them only when
   the scan wraps (109: 127 steps). Any other order would be a new scheduling policy.
5. **Sticky BLOCKED**: contract open question 2.
6. **Metric scope.** The evaluator measures the active fused maps. The coverage of the effective
   causal geometry, which is what the probe reads, was not measured.
7. **Unlocated but measured instances.** Eight catalog instances have causal measurements and no seed.
   Whether measured-but-unlocated objects should become serviceable is a future question.
8. **Retaining the run.** The full run (22 GB) and the smokes live in the session scratchpad
   worktree above. Relocating them, for example beside the accepted trees, needs a decision.
9. A target-neutral scene-level epistemic formulation remains open (contract open question 3; the
   deferred `HeadEvidence` placement).
