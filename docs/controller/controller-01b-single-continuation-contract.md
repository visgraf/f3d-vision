# Controller-01B: one post-watchdog continuation look — contract

## Status

This is a bounded **scientific** step with one causal question and **exactly one** new sensory
action. It is not Controller-02, and it changes no threshold, scheduler, watchdog, stopping rule or
local policy.

    base              origin/main @ a60d44856e8bdc3daf7709db53e411581b7bace2 (Policy 1 accepted)
    source run        /home/lvelho/rd/f3d-vision/previews/controller-01-full
                      (accepted Controller-01, report e3bf5e0; manifest d293a98f…, actions 12cdbe4d…)
    source audit      /home/lvelho/rd/f3d-vision/previews/controller-01a-terminal-audit/audit.json
                      (accepted Controller-01A: CONTROLLER01A_FINAL_REPROBE_ACTIONABLE)
    branch            controller/controller-01b-single-continuation (isolated worktree; not merged)
    output run        /home/lvelho/rd/f3d-vision/previews/controller-01b-single-continuation
    visual            /home/lvelho/rd/f3d-vision/visuals/controller-01b/overview.png (Level A)
    tool              tools/controller/controller01b.py  (modes: run | check | visual)
    result marker     exactly one of
                        CONTROLLER01B_ONE_LOOK_REPROBE_QUIET
                        CONTROLLER01B_ONE_LOOK_REPROBE_ACTIONABLE
                      and neither if the reconstruction or the action fails

Everything here is PROPOSED until the run.

## Causal question

Starting from the final causal state of Controller-01, what happens if object 210 (`wall.008`)
executes exactly the one observation still requested by the unchanged accepted local policy?

The observation helps distinguish two cases, and intermediate outcomes are allowed:
- **Case A**: look 25 contributes substantial new geometry and changes or resolves the frontier. That
  suggests 24 was merely an engineering cutoff reached too early.
- **Case B**: look 25 contributes little novelty, and essentially the same local continuation remains.
  That is evidence of a local continuation/frontier-persistence problem.

No threshold for "substantial" is declared. The measurements are reported, and no interpretation is
encoded into the controller.

## Pre-action state (reconstructed from controller-time artifacts only)

The truth firewall (`fov3d.control.integrated.TruthFirewall` with
`controller01.is_evaluation_truth`) is active for the whole run. It opens no `evaluation.json`
and nothing under `bootstrap/evaluation_only/`.

Reconstructed into a `ClassroomController01` instance, the unchanged Controller-01 adapter class:
- **Global memory and head evidence.** The 141 saved patches are replayed in global order into the
  `InstanceMeasurementMemory` and the global `HeadEvidence` (`remember_measurements`). Every replayed
  per-action addition must equal the logged one.
- **Global observation footprint.** `seen_any` is rebuilt by re-matching each of the 141 saved tangent
  pairs with the accepted matcher (`matcher.compute`, then `epistemic.add_observation`). Every
  recreated patch must equal the saved patch.
- **210's own context.** Its 24 looks give the Cyclopean own evidence, the FSG6f history, the visited
  gazes, and the last gaze, calibration and binocular state, exactly as Controller-01 built them.
- **210's active SurfaceMap.** It is rebuilt by replaying the accepted `initialize`/`fuse` (12 mm)
  over its 24 own looks, with the recreated patches (XYZ, left RGB, instance ids and patch ids
  `fix_00…fix_23`). This recovers the exact runtime map. It must equal the saved `final_map.npz`:
  XYZ as float32, RGB, instance id, support count and provenance.

**M_t validation.** The target-relative view E_t(210) rebuilt from the reconstructed memory must
equal the saved Controller-01 terminal view `objects/instance_0210/epistemic/final_terminal.npz`
(`class_code`, `region_code`).

**Required pre-action reproduction** (the stop gate). The unchanged accepted probe
(`probe_local_policy`: FSG6f → Cyclopean) on 210 must reproduce the accepted Controller-01A terminal
probe:
- own looks 24;
- effective geometry 1,938,913; revision [24, 1,774,969];
- FSG6f `continue`, frontier raw/OPEN/map-resolved/boundary-resolved 350/52/28/270;
- candidates 1, consensus-rejected 2;
- proposed gaze [7.6, 18.2].

If it cannot be reproduced, the tool stops before rendering and emits no marker.

## The one action

    OBSERVE(target_id = 210,
            gaze      = the reproduced proposal [7.600000000000001, 18.200000000000003],
            vergence  = the accepted fixed 2.10 m (FSG6f VERGENCE_DISTANCE_M),
            focus     = the accepted depth-of-field-disabled renderer behavior)

- global action index 141; object-210 local step 24;
- executed through the unchanged `ClassroomController01.observe`:
  - the same Blender acquisition script and arguments (full profile, OptiX, the accepted spp);
  - the render-noise convention `--object-id 210 --step 24`;
  - the accepted matcher on the current pair only;
  - every valid positive-instance measurement appended to the global memory (source index 141,
    active target 210), plus the head evidence and the observation footprint;
  - fusion into 210's active map with the accepted 12 mm rule and the idempotence replay, or the
    accepted empty-look semantics below 100 target points;
  - no incidental point fused into 210's map;
  - the own-target context updated with this one look.

The Controller-01 watchdog would have refused this look. Executing it is the explicitly authorized
experiment, and the control loop, scheduler and watchdog are not used. **No second observation is
made.** The post-look proposal is recorded and **not executed**.

## Measured and recorded

- **Look 25:**
  - target-valid points; all-instance valid points; measured instance ids;
  - memory additions by instance;
  - active-map size before/after; new surfels; non-new target points;
  - the association-distance summary (median, p95 and max of the matched distances);
  - effective geometry before/after;
  - head-evidence additions;
  - gaze and calibration (prescribed vergence);
  - render time.
- **Post-look probe** (unchanged FSG6f → Cyclopean): QUIET or ACTIONABLE; the source and next gaze
  if actionable. For FSG6f, the reason, frontier raw/OPEN/map-resolved/boundary-resolved, the
  candidate count, and the selected candidate's summary (supports, frontier score, predicted new
  angular area). For Cyclopean, if reached, the reason, eligible cells and the proposed gaze.
- E_t(210) views before and after the look, saved in the output run.

## Checks (`controller01b.py check`, fail-capable)

The check mode recomputes the pre-state from the source run. It then applies the saved look-25
artifacts (no render) and compares everything with the recorded run. It must catch:
1. a wrong source run (the accepted hashes);
2. a pre-action probe that differs from the accepted 01A terminal probe;
3. a wrong target;
4. a wrong gaze (the recorded action, the acquisition's calibration);
5. a wrong global or local action index (the record, the patch path, the memory provenance);
6. an altered vergence or focus;
7. an evaluation-truth access (firewall);
8. a failure to append all valid positive-instance measurements (the recomputed additions from the saved
   patch);
9. an accidental fusion of incidental points into 210's active map (post-map instance ids; replayed
   fusion);
10. a wrong 12 mm fusion (the post map equals the replayed accepted fusion);
11. more than one new OBSERVE (exactly one acquisition and one patch in the output run);
12. QUIET/ACTIONABLE reported inconsistently with the actual post-look probe, recomputed from the
    reconstructed post state.

Fail-capability is demonstrated with deliberate corruptions of throwaway copies of the output run,
and code mutants in throwaway repository copies. The source run stays byte-identical, and its
per-file sha256 manifest is compared before and after.

## Visual (Policy 1, Level A)

`/home/lvelho/rd/f3d-vision/visuals/controller-01b/overview.png`, generated by
`tools/controller/controller01b.py visual`, in the canonical active-perception frame:
1. object 210 and the requested fixation;
2. the new left/right binocular observation;
3. the FSG6f frontier state before → after (DERIVED, with the accepted frontier functions; counts
   checked against the recorded probes);
4. the effective geometry before → the look-25 points → after, with the new geometry highlighted.

It annotates:
- target-valid points and new surfels;
- the effective-geometry change;
- OPEN 52 → after, and candidates 1 → after;
- the post-look state, and the next gaze if still actionable.

All panels are CONTROLLER-TIME or DERIVED; no evaluation truth is used.

## Cost and gates

| command | cost class |
|---|---|
| `controller01b.py run` (reconstruction with 141 re-matches and 24 fusion replays, plus one render) | batch (ESTIMATED 2–6 min) |
| `controller01b.py check` | batch |
| `controller01b.py visual` | batch |
| the Controller-01 unit/architecture, layout, Core-14, Classroom and facade checkers; `verify_baseline`; `git diff --check` | interactive |

## Permitted fixes and stop conditions

Permitted: bugs in the new tool, in its checks or visual, and in the narrow layout declaration.

Stop if the pre-action state cannot be reproduced, or if any change to accepted code, threshold,
rule, watchdog, matcher, fusion or truth scope would be needed. The source run is never modified.
