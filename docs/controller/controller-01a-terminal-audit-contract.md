# Controller-01A: terminal blocked-state audit contract

## Status

This is a **read-only post-run diagnostic** of the accepted Controller-01 run. It is not
Controller-02, and it changes no controller policy, no scientific state and no accepted artifact.

    accepted main          origin/main @ e659ff1053f6fb0702f2d34224a5da2cec7f9ae9
                           (Accept Integrated Foveal Controller 01; docs-only acceptance
                           commit on top of the accepted Controller-01 report commit
                           e3bf5e08f579104024036d94a2d97a9221ca82dd)
    acceptance marker      INTEGRATED_FOVEAL_CONTROLLER01_ACCEPTED
    source run             /home/lvelho/temp/previews-2026.09.28/controller-01-full
                           (manifest.json d293a98f…, actions.json 12cdbe4d…)
    branch                 controller/controller-01a-terminal-audit, created from e659ff1
    execution              one isolated git worktree; the shared checkout is not touched
    result marker          exactly one of
                             CONTROLLER01A_FINAL_REPROBE_QUIET
                             CONTROLLER01A_FINAL_REPROBE_ACTIONABLE
                           or an explicit audit reconstruction failure

Luiz and Chat designed this step. Claude Code commits this contract before implementing the
audit. The branch is not merged, and `docs/chat-handoff.md` is not updated with the result.

Everything in this document is **PROPOSED** until the audit runs.

## Causal question

At the final causal scene state, after the other objects' subsequent observations have been
incorporated, would object 210 (`wall.008`) still be ACTIONABLE if we ignored only the sticky
BLOCKED flag and asked the unchanged accepted local policy again?

The answer discriminates between two readings. One is sticky-BLOCKED semantics: the object might
have become quiet from later memory. The other is genuinely unresolved local continuation.
Neither outcome is a policy decision here; interpretation belongs to Luiz and Chat.

## What is and is not done

The audit only reconstructs causal controller-time state from saved run artifacts. It does not:
- run Blender, render, fixate or measure anything new;
- fuse into any map;
- change any threshold, the watchdog, the scheduler or the local policy (FSG6f → Cyclopean);
- touch `fov3d/` production code;
- use evaluation truth: it opens neither `evaluation.json` nor anything under
  `bootstrap/evaluation_only/`;
- write into the preserved run, which stays byte-identical. Its per-file sha256 manifest is
  compared before and after the audit and the mutation work.

## Implementation (smallest reproducible audit)

A narrowly isolated audit mode of the existing checker:

    .venv/bin/python tools/controller/check_controller01.py \
        --terminal-reprobe /home/lvelho/temp/previews-2026.09.28/controller-01-full \
        --object 210 [--audit-out <json>]

It uses only the accepted conceptual code, unchanged:
- `fov3d.reconstruction.measurement_memory` (`InstanceMeasurementMemory`,
  `effective_target_geometry`);
- `fov3d.experiments.classroom_oracle.matcher.compute`, `….epistemic` and
  `fov3d.control.object_policy.history_entry`;
- `fov3d.experiments.classroom_oracle.controller01.probe_local_policy` and `LocalPolicyContext`;
- the Controller-01 truth firewall (`fov3d.control.integrated.TruthFirewall` with
  `controller01.is_evaluation_truth`), active for the whole audit, recording every run file opened.

The only other change is the repository-layout checker's narrowest exact accommodation: the two
Controller-01A documents become declared `docs/controller/` additions (the contract required, the
report allowed). It is mutation-tested.

## Reconstruction

Inputs, all controller-time:
- `manifest.json`;
- `actions.json`;
- `objects/instance_XXXX/patches/fix_kk.npz` for every action;
- for object 210:
  - `acquisitions/fix_kk/{calibration.json, oracle_observation.npz}`;
  - `maps/fix_23.npz`;
  - `final_map.npz`;
  - `final_effective_geometry.npz`;
  - `result.json`.

1. **Global measurement memory.** Replay the saved patches in global action order into one
   `InstanceMeasurementMemory`, with source global index = the action's `global_step` and source
   active target = the action's `target_id`.
2. **210's own local-policy context.** It is built from 210's own target-directed looks only, local
   steps 0…23, from its saved acquisitions. For each look, the accepted matcher recreates the
   binocular state from the saved tangent pair. Then, in the accepted runner's order:
   - the own-target Cyclopean evidence (`epistemic.add_observation`);
   - the FSG6f history entry (`object_policy.history_entry`);
   - the visited gaze.

   The last gaze, calibration and binocular state are those of local step 23. No observation made
   while another object was the active target enters this context.
3. **Active map.** The saved active SurfaceMap geometry of 210 (`final_map.npz`), which must equal
   `maps/fix_23.npz`, because 210 had no own look after step 101. No incidental point is fused into
   it.
4. **Effective target geometry.** `effective_target_geometry(active map XYZ,
   memory.snapshot(210).xyz_h)`, exactly as in Controller-01.

## Validation gates (all must pass before any result is reported)

| gate | requirement |
|---|---|
| action order | `actions.json` global steps are contiguous and ascending; 210's own actions have local steps 0…23 in ascending global order; their count equals the manifest's 24 fixations |
| memory replay | every replayed per-action addition equals the logged `measurement_memory_additions` |
| own-look identity | each acquisition's `calibration.json` gaze equals the logged gaze of that local step; the matcher-recreated patch (XYZ, validity, instance id) equals the saved patch `fix_kk.npz` |
| active map | `final_map.npz` equals `maps/fix_23.npz`; its size equals the logged map size after 210's last look |
| terminal geometry | the terminal effective geometry, XYZ and per-point provenance, equals the saved `final_effective_geometry.npz` |
| truth firewall | zero violations; no opened file is evaluation truth |

**Watchdog-prefix reproduction (the stop gate).** Memory is replayed through global step 101, the
step of 210's 24th look. The unchanged local probe is called with the 24-look own context, and the
watchdog decision itself is ignored. The probe must reproduce the saved Controller-01 probe record
(`result.json`, the probe after step 101):
- revision `[24, 1584958]` and effective points 1,748,902;
- ACTIONABLE, source `fsg6f`, FSG6f `continue`;
- `frontier_open_count` 58, `frontier_raw_count` 354, map-resolved 26, boundary-resolved 270;
- candidates 1, consensus-rejected 3;
- proposed gaze `[7.6, 18.2]` (within 1e-9 degrees).

If any item differs, the audit **stops** and reports a reconstruction failure. It performs no
terminal probe.

## Terminal re-probe

Replay the remaining saved observations, steps 102…140. Object 210's own context is **unchanged**:
it received no further own-target observation. Call the same accepted local probe on the terminal
effective geometry, ignoring only the sticky BLOCKED state. No FSG6f or Cyclopean rule is altered.

- Both FSG6f and Cyclopean stop → `FINAL_REPROBE_QUIET`.
- Either proposes a gaze → `FINAL_REPROBE_ACTIONABLE`.

Measured and reported:
- 210's measured point count at the watchdog and at the terminal state;
- the number of causal measurements of 210 added after the watchdog, with their source targets and
  source global steps;
- the active-map size (unchanged);
- the effective-geometry size at the watchdog and at the terminal state;
- the watchdog-prefix probe and the terminal probe: source, proposed gaze, FSG6f frontier counts
  and candidates, and the Cyclopean eligible cells if reached;
- the files opened, and the firewall result.

## Fail-capable evidence (deliberate temporary corruptions or mutants)

Each must make the audit report a failure. Data corruptions act only on throwaway copies of the
needed run files; code mutants act only on throwaway copies of the repository.
1. corrupted global action ordering;
2. a missing saved patch;
3. a patch attributed to the wrong active target;
4. a changed own-target gaze/history ordering for 210;
5. another target's gaze included in 210's local history;
6. the active map alone used instead of the effective geometry;
7. an attempted access to evaluation truth;
8. a reconstruction that does not reproduce the step-101 watchdog-prefix result (58 OPEN,
   1 candidate).

The preserved run's per-file sha256 manifest (1,678 files) is compared before and after.

## Gates and cost

| command | cost class |
|---|---|
| the audit command above | interactive to batch (ESTIMATED < 1 min: 141 patch loads, 24 matcher calls, two probes on ~1.7–1.9 M points) |
| `tools/controller/check_controller01.py` (unit/architecture), `check_repository_layout.py`, `check_conceptual_core14.py`, `check_classroom_oracle1.py`, `check_fov3d_facade.py`, `scripts/verify_baseline.sh`, `git diff --check` | interactive |
| the mutation harnesses | batch |

## Acceptance of this step

The audit is valid when all validation gates and the watchdog-prefix reproduction pass, the
firewall records no violation, every corruption/mutant is caught, the preserved run is unchanged,
and the existing gates pass. The report then carries exactly one result marker. Without a valid
reconstruction there is no marker and the failure is reported.

## Permitted fixes and stop conditions

Permitted: bugs in the new audit code, the checker, or the narrow layout accommodation.

Stop and report if reproducing the watchdog prefix would require changing any accepted code,
threshold, rule or artifact, or reading evaluation truth. The same applies if the saved artifacts
cannot reconstruct the state.
