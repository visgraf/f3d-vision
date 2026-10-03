# Chat Handoff

## Accepted main

    main @ 40a1cb11b99324da125ed2464078d3ec19aca947

`origin/main` is fast-forwarded to the docs-only handoff commit that adds this entry, whose parent is
`40a1cb1` (the Breadth-1 acceptance commit on branch `classroom-oracle/breadth-1-spherical-glance`).

Accepted milestones:
- **Breadth-1: Classroom-234 Spherical Glance**, accepted by Luiz and Chat (the measured scientific result,
  the final figures and the post-run seed-tie clarification):

      BREADTH1_CLASSROOM234_SPHERICAL_GLANCE_ACCEPTED

  The accepted completion marker is `BREADTH1_CLASSROOM234_SPHERICAL_GLANCE_COMPLETE`.
- **Visual Language 1 + the full canonical Classroom demo**, accepted by Luiz and Chat as committed (a
  methodological / visualization milestone that changed no scientific behavior):

      VISUAL_LANGUAGE_1_ACCEPTED

  The accepted implementation marker is `VISUAL_LANGUAGE_1_CANONICAL_DEMO_COMPLETE`.
- **Revised roadmap** (an explicit later decision by Luiz): Breadth-1 comes before Natural Bootstrap-1.
  The signed Stage Charter 1 is not rewritten.
- **Controller-02 residual closure**, accepted by Luiz and Chat (implementation and measured scientific
  result; its overview was inspected and accepted as satisfying the Level-A scientific-visual
  requirement):

      CONTROLLER02_RESIDUAL_CLOSURE_ACCEPTED

  The accepted markers are `CONTROLLER02_IMPLEMENTATION_CHECKS_PASS` and
  `CONTROLLER02_CLASSROOM_SCENE_CLOSED`: the scene terminated honestly as `SCENE_CLOSED`, which is not
  global quiescence.
- **Foveal Controller Stage Charter 1**, signed by Luiz and Chat (an architectural / scientific-direction
  decision, not an experiment):

      FOVEAL_CONTROLLER_STAGE_CHARTER_1_ACCEPTED

- **Controller-01 frozen** as the good-enough integrated-controller baseline (Charter 1, section 1).
- **Controller-01C**, a valid read-only scientific audit of look 25's frontier/action correspondence:

      CONTROLLER01C_FRONTIER_ACTION_AUDIT_ACCEPTED

  The accepted result marker is `CONTROLLER01C_FRONTIER_ACTION_CORRESPONDENCE_AUDIT_COMPLETE`: the FSG6f
  fixation did **not** service the frontier that requested it.
- **Controller-01B**, one post-watchdog continuation look for object 210 (a bounded scientific step,
  exactly one new OBSERVE):

      CONTROLLER01B_SINGLE_CONTINUATION_ACCEPTED

  The accepted measured result is `CONTROLLER01B_ONE_LOOK_REPROBE_ACTIONABLE`.
- **Controller-01 visual package**, the first Level-B application of Policy 1 (visualization of
  accepted measurements, not a new experiment):

      CONTROLLER01_VISUAL_PACKAGE_ACCEPTED

- **Preview/visual lifecycle Policy 1**, a project policy accepted by Luiz and Chat (not a
  scientific step):

      PREVIEW_VISUAL_LIFECYCLE_POLICY_1_ACCEPTED

- **Controller-01A** is accepted at `657388c` (acceptance commit `bb6a3f3`).
  It is a valid read-only audit:

      CONTROLLER01A_TERMINAL_AUDIT_ACCEPTED

  The accepted result is `CONTROLLER01A_FINAL_REPROBE_ACTIONABLE`.
- **Integrated Foveal Controller 01**, accepted at `e3bf5e0` (implementation and measured
  scientific result):

      INTEGRATED_FOVEAL_CONTROLLER01_ACCEPTED

  The implementation marker `CONTROLLER01_IMPLEMENTATION_CHECKS_PASS` is accepted. Global
  quiescence was **not** reached, and the global-quiescence marker was not emitted. The
  accepted scientific outcome is `INCOMPLETE`. That is a measured scientific result, not an
  implementation failure.
- **Repository Stage Transition 1**, accepted at `b12bdef`. It is structural only and
  changes no scientific behavior:

      REPOSITORY_STAGE_TRANSITION_1_PRESERVES_SCIENTIFIC_BEHAVIOR

- **Conceptual Core 14** remains the accepted **scientific** milestone:
  `296001e8683ba0b1ad62642811d3dea0e84b6566`. The conceptual-core migration **pauses** here.

## Working arrangement

- Luiz is the scientific and acceptance authority.
- Chat is the architecture, specification and review surface. **Its GitHub connection is
  read-only**: it inspects, searches and reviews, and it does not push commits, branches,
  updates or pull requests. For each substantial handoff it prepares a self-contained
  Claude Code prompt, which Luiz gives to Claude Code.
- Claude Code is the **repository-mutation and execution surface**. It commits the durable
  contract before substantial execution. It performs every repository mutation and every
  measured execution in dedicated isolated git worktrees, under the branch/HEAD/clean-tree
  guard, never by switching branches in the shared `/home/lvelho/rd/f3d-vision` checkout.
- GitHub is the durable source of truth.
- Result rules (`CLAUDE.md`, Policy 1):
  - an executed scientific/behavioral step must produce a **measurable result**, its **run
    evidence under `./previews`**, at least one **human-inspectable scientific visual under
    `./visuals`**, **fail-capable checks**, and a short Git-tracked **report** recording the
    result, the visual paths and the regeneration command. Diagnostic plots alone need not
    satisfy the visual requirement;
  - pure architectural/design steps may instead produce a **reviewed
    specification/contract** and a **short summary**;
  - structural/refactoring steps need machine-checkable preservation evidence.
- New contracts and reports follow `docs/<stage>/<phase>-contract.md` and
  `docs/<stage>/<phase>-report.md`.
- Migrate behavior first, redesign structure second, and answer one causal question per
  Core. Cores 12, 13 and 14 were the three intentional redesign Cores: the simplest
  falsifiable redesign, preserving every accepted historical observable and separating one
  concept at a time. The migration pauses after Core 14; no Core 15 is started
  automatically.

## Current roadmap (Luiz, after Breadth-1)

    Controller-02                                   ACCEPTED
      -> Visual Language 1                          ACCEPTED
      -> Breadth-1                                  ACCEPTED
      -> Natural Bootstrap-1                        NEXT
      -> Classroom validation
      -> Tabletop transfer
           same controller / bootstrap policy,
           no scene-specific retuning unless execution is impossible
      -> Natural Bootstrap-2

- This roadmap is a later explicit decision. It inserted Breadth-1 before Natural Bootstrap-1. The signed
  `docs/methodology/foveal-controller-stage-charter-1.md` keeps its historical roadmap and is not edited.
- Controller-01 and Controller-02 remain frozen unless Luiz explicitly reopens them.
- Visual Language 1 remains the standing visual semantics.
- **Natural Bootstrap-1** (the next design target; not started) keeps a modest formulation:

      low-resolution sensory observation
        -> perceptual decomposition
        -> temporary object hypotheses
        -> representative seed gaze per hypothesis
        -> active controller

  - It must not use the Blender object list as controller initialization.
  - No semantic classification is required initially.
  - Preferred first cues: RGB continuity, range/depth continuity, depth discontinuities, connectedness /
    region coherence.
  - Over-segmentation is acceptable.
  - Natural Bootstrap-2 (identity persistence) is a separate later problem.
  - Its design is discussed by Luiz and Chat before any branch, contract or implementation.

## Breadth-1: Classroom-234 Spherical Glance (accepted at `40a1cb1`)

Luiz and Chat accept Breadth-1: the measured scientific result, the final overview and
representative-seed panorama, and the post-run seed-tie numerical clarification.

Record (branch `classroom-oracle/breadth-1-spherical-glance`, base `3aa0cc6`):
- contract: `docs/classroom-oracle/breadth-1-spherical-glance-contract.md` (`d5b975b`). Section 11 is the
  post-run seed-tie clarification (`8158809`, Option A: `SEED_TIE_DOT_EPS = 1e-12`, ties to the smaller row,
  then column).
- implementation: `tools/classroom_oracle/breadth1_{spec,render,glance,visuals}.py` and
  `check_breadth1.py`. Frozen at `0106269` before the canonical run; presentation fix `0a78544`; seed-tie
  repair `8158809`.
- report: `docs/classroom-oracle/breadth-1-spherical-glance-report.md` (completion `e2e554e`, acceptance
  `40a1cb1`).
- run: `/home/lvelho/rd/f3d-vision/previews/breadth-1-classroom-234-spherical-glance/`. The single
  canonical EXR is `render/canonical.exr`, sha256
  `4ea036fc74eab3b3ab06a0c4470c2b01740c9322de0eea522f957ddfffa172f8`. Never re-render; re-analysis reads it.
- visuals: `/home/lvelho/rd/f3d-vision/visuals/breadth-1-classroom-234-spherical-glance/`:
  - `overview.png` `705265b0…`;
  - `seed-direction-panorama.png` `02662754…`;
  - the RGB, range, instance, boundary, histogram and scatter figures;
  - `global-point-cloud.ply`.

Accepted measured result:

    BREADTH1_CHECKS_PASS        26 / 26 (at the acceptance commit `40a1cb1`)
    BREADTH1_MUTATIONS_CAUGHT   29 / 29 (from a passing baseline)

Checks 21–22 of `check_breadth1.py` are scoped to the Breadth-1 base `3aa0cc6`. On later commits,
check 21 reports every later accepted change outside the Breadth-1 files as "undeclared". The first such
change is this handoff's `CLAUDE.md` and `docs/chat-handoff.md`. That is the guard's scope, not a
Breadth-1 regression; the frozen-output checks remain valid.

| quantity | value |
|---|---|
| catalog objects | 234 |
| visible at 0.5° / no first hit | 126 / 108 |
| visible fragmented (> 1 component) | 59 |
| authored cells / point-cloud points | 222,267 / 222,267 |
| accepted localized 25 visible | 25 / 25 |
| visible entirely outside the old Controller domain | 102 |
| largest 1 / 5 / 25 objects | 24.7 % / 63.4 % / 78.6 % of the sphere |
| catalog-labelled / noncatalog rendered / no geometry | 82.5 % / 15.4 % / 2.1 % |
| seeds moved by the seed-tie clarification | only 102 `Rectangle018.002` (187, 63) → (187, 62) and 177 `post-it` (193, 463) → (193, 462) |

Accepted interpretation (durable):
1. Breadth-1 was **one shallow 720 × 360, 0.5° full-sphere reference observation** from the fixed
   cyclopean head origin: exactly one canonical Classroom render.
2. It ran **no controller, no active foveation and no per-object growth**.
3. The **234 authored catalog objects are the accounting universe**: 126 visible, 108 with no first hit. A
   missing first hit is a sampling outcome, not a claim of occlusion.
4. The **catalog is not an exhaustive inventory of rendered scene geometry**. 15.4 % of the sphere is
   rendered geometry with no catalog id. It is largely associated with collection-instanced scene
   structure: 56 collection instancers, including 20 school desks, chairs and lamps. That association is
   not verified cell by cell.
5. The authored catalog is **oracle / reference information, not natural segmentation ground truth**.
6. This discrepancy is an **input to Natural Bootstrap-1 design**, not something Breadth-1 repairs. No ids
   were assigned to collection instances, and the catalog is unchanged.
7. Controller-01 and Controller-02 remain frozen unless Luiz explicitly reopens them.
8. Visual Language 1 remains the standing visual semantics.

## Visual Language 1 + canonical Classroom demo (accepted at `e596a10`)

Luiz and Chat accept Visual Language 1 and the canonical demo as committed at `578a4f8`.

Record (branch `methodology/visual-language-1-canonical-demo`, base `1e0584b`):
- contract: `docs/methodology/visual-language-1-contract.md` (`095f48a`);
- implementation: `tools/visual_language/` (`300d7c4`; later fixes `89f66ac`, `2320e5b`, `a30d453`);
- the language: `docs/methodology/visual-language-1.md`; the single source of its vocabulary is
  `tools/visual_language/style.py`;
- report: `docs/methodology/visual-language-1-report.md` (`578a4f8`); acceptance record `e596a10`;
- cache: `/home/lvelho/rd/f3d-vision/previews/visual-language-1-classroom/`;
- package: `/home/lvelho/rd/f3d-vision/visuals/visual-language-1/` (`overview.png`,
  `legend/visual-language-1.png`, the 1440p and 1080p demo videos, 141 cockpit frames, events,
  panoramas, PLYs, narration).

Accepted measured result (report):
- the 251.30 s demo shows each of the 141 accepted looks exactly once as a four-panel cockpit frame
  (BEFORE / OBSERVATION / AFTER semantics), with the seven special events slowed down;
- the causal state was reproduced from the saved runs and matched every logged per-step record; no
  controller was rerun and nothing was observed;
- truth firewall 0 violations; `fov3d/` byte-identical; one static Blender REFERENCE hero view only;
- checker 25/25 (`VISUAL_LANGUAGE_1_CHECKS_PASS`); corruptions 33/33 caught.

Accepted interpretation:
- Visual Language 1 is the standing visual semantics for later experiments. Truth/provenance classes
  carry a non-color cue: CONTROLLER-TIME, DERIVED, REFERENCE / EVALUATION, ORACLE INPUT.
- The known cosmetic issues (a clipped defer label, truncated long tile names, a sparse early 3-D view)
  are non-blocking and not repaired.

## Repository Stage Transition 1 (accepted at `b12bdef`)

`origin/main` was fast-forwarded `330577f → b12bdef` with a plain, non-forced push.

Record:
- contract: `docs/repository/repository-transition-1-contract.md`, including its
  inventory-resolved clarification;
- report: `docs/repository/repository-transition-1-report.md`;
- move map: `docs/repository/repository-transition-1-moves.json`.

What changed:
- `docs/` and `tools/` are organized by stage/topic:
  - `docs/{architecture,baseline,classroom-oracle,consolidation,conceptual-core,methodology,partition-graph,repository}/`,
    with `docs/chat-handoff.md` as the fixed top-level entry point;
  - `tools/{baseline,classroom_oracle,conceptual_core,consolidation,partition_graph,repository}/`.
- The `tools/` root is exactly the 16-module sealed compatibility/runtime closure, the
  `mappings[].legacy` set of `docs/consolidation/consolidation-3-layout.json`.
  `tools/dev/` is gone.
- `README.md` now summarizes the migration and the Integrated Foveal Controller stage.
- `CLAUDE.md` now defines Chat's GitHub role as read-only and Claude Code as the
  repository-mutation/execution surface. It states the result rules above and the current
  project stage.
- `scripts/verify_baseline.sh`: the step `baseline-files-accounted`
  (`tools/baseline/check_baseline_files.py`) is relocation-aware. It accounts for the 31
  baseline-tag files as 22 unchanged, 4 pure relocations, 4 declared-repaired relocations
  and 1 declared replacement (README). Historical baseline byte/path identity is not the
  current layout.
- `tools/repository/check_repository_layout.py` checks the layout.
- Historical reports keep their verbatim pre-transition commands and paths; the move map
  translates them.

Evidence (measured; report):
- `fov3d/`, the 16 sealed root modules, `tests/` and `scenes/` were unchanged (0 bytes vs
  `330577f`);
- the applicable Conceptual-Core checks (Cores 1–10 and 14) and Partition-Graph checks
  (1–8b) passed;
- facade 16/16; Classroom-Oracle 12/12; `verify_baseline` 9/9;
- golden `MISMATCHES 0`;
- the 13 accepted reference trees were unchanged;
- the layout checker passed 487/487 and caught 22/22 mutations.

## Integrated Foveal Controller 01 (accepted at `e3bf5e0`)

Luiz and Chat accepted the implementation, the measured scientific result (explicitly as
`INCOMPLETE`, not global quiescence) and the layout-checker repair `baf3fed`.

Record (branch `controller/controller-01`, base `c5f6be6`):
- contract: `docs/controller/controller-01-state-action-contract.md` (`4233a55`);
- report: `docs/controller/controller-01-state-action-report.md` (`e3bf5e0`);
- code: `fov3d/control/integrated.py` (reusable state/action concepts, the deterministic
  retain/switch/stop scheduler, the generic closed loop, the target-relative view E_t(i), the
  truth firewall) and `fov3d/experiments/classroom_oracle/controller01.py` (the Classroom
  adapter/executable);
- checks: `tools/controller/check_controller01.py`; visuals: `tools/controller/plot_controller01.py`.

Accepted measured result of the one full run (at `5b66e59`):

| quantity | value |
|---|---|
| localized / initialized | 25 / 25 |
| observations | 141 |
| switches / attention bouts | 26 / 27 |
| natural reactivations | 2 (109 by 110's look; 178 by 224's look; both serviced and quiet again) |
| QUIET at termination | 24 |
| blocked | 210 `wall.008`, `BLOCKED:watchdog`: at the inherited 24-look watchdog its accepted local policy still proposed an FSG6f look |
| terminal | `INCOMPLETE(localized_objects_blocked)` |
| descriptive coverage (after control) | 0.9833720295001366 |

Full run, canonical current-stage location (Policy 1):

    /home/lvelho/rd/f3d-vision/previews/controller-01-full

It was moved there from the earlier archive copy with `rsync -a` and verified before the archive copy
was removed:
- 1,678 files, and the complete per-file sha256 set identical to the accepted preserved manifest;
- the visuals `controller-attention-timeline.png` and `controller-gaze-chart.png` included;
- `manifest.json` `d293a98f…`, `actions.json` `12cdbe4d…` and `evaluation.json` `76cb1e5d…`.

The smoke runs are plumbing artifacts and were not kept as accepted artifacts.

## Controller-01A terminal blocked-state audit (accepted at `657388c`)

Luiz and Chat accept Controller-01A as a **valid read-only audit** of the preserved
Controller-01 run.

Record (branch `controller/controller-01a-terminal-audit`, base `e659ff1`):
- contract: `docs/controller/controller-01a-terminal-audit-contract.md` (`e53c59f`);
- report: `docs/controller/controller-01a-terminal-audit-report.md` (`657388c`);
- tool: `tools/controller/check_controller01.py --terminal-reprobe RUN --object 210`.

Accepted result:

    CONTROLLER01A_FINAL_REPROBE_ACTIONABLE

- **Watchdog, step 101.** The reconstruction reproduced the saved probe exactly: 24 own looks,
  effective geometry 1,748,902, FSG6f `continue`, 58 OPEN, 1 candidate, proposed gaze
  `[7.6, 18.2]`.
- **Terminal scene state.** 190,011 later causal measurements of 210 had arrived, all from other
  targets. Effective geometry was 1,938,913, and the active map was unchanged at 163,944 surfels.
  FSG6f still continued, with 52 OPEN, 1 candidate and the same gaze `[7.6, 18.2]`.
- Truth firewall: 0 violations. Reconstruction exact. 10/10 negative controls caught.

Accepted interpretation:
- later cross-target memory did **not** make 210 quiet;
- therefore sticky BLOCKED semantics are **not** the explanation for Controller-01's failure to
  reach global quiescence;
- the unresolved behavior is genuinely inside the accepted local continuation/stopping behavior;
- this does **not** yet prescribe a new stopping policy.

## Controller-02 residual closure (accepted at `746e908`)

Controller-02 is accepted: the implementation, the measured scientific result and its Level-A visual.

Record (branch `controller/controller-02-residual-closure`, base `6306458`):
- contract: `docs/controller/controller-02-residual-closure-contract.md` (`620f776`);
- implementation: `fov3d/control/controller02.py` (generic Disposition / ScenePhase / FinalProbeDecision /
  SceneClosed and the loop) and `fov3d/experiments/classroom_oracle/controller02.py` (the no-render replay
  adapter and the strict final-look gate v1) (`e027d84`); checks `tools/controller/check_controller02.py`
  (`e027d84`, `8758790`); visual `tools/controller/visualize_controller02.py`;
- report: `docs/controller/controller-02-residual-closure-report.md` (`746e908`);
- output: `/home/lvelho/rd/f3d-vision/previews/controller-02-classroom-replay/`;
- visual: `/home/lvelho/rd/f3d-vision/visuals/controller-02/overview.png` (Level A).

Controller-01 stays frozen: `fov3d/control/integrated.py` and
`fov3d/experiments/classroom_oracle/controller01.py` are byte-identical.

Accepted measured result (a no-render replay of the accepted Controller-01 run):

    CONTROLLER02_IMPLEMENTATION_CHECKS_PASS
    CONTROLLER02_CLASSROOM_SCENE_CLOSED

| quantity | value |
|---|---|
| ordinary observations | 141 / 141 reproduce Controller-01 behavior (each verified against the saved acquisition) |
| deferral | 210 `wall.008` at global step 101: local ACTIONABLE at the 24-look ordinary budget → `DEFERRED` (not BLOCKED) |
| end of the normal phase | 24 QUIET; 210 ACTIONABLE and DEFERRED; phase NORMAL → RESIDUE |
| final proposal | the unchanged FSG6f proposal [7.6, 18.2], put to the strict final-look gate v1 |
| final support | 30 OPEN elements; entering both predicted depth cores 0; previously interrogated 30 |
| novel_service_count | 0 |
| gate | REJECT (`no_novel_serviceable_support`); final residue observations 0 (no render, no OBSERVE) |
| terminal | `SCENE_CLOSED`: 24 QUIET; residual 210 (ACTIONABLE, `FINALIZED: final_probe_rejected`); 209 unlocated |

Evidence: checks 77/77; 17/17 output corruptions caught; truth firewall 0 violations; 0 process
launches; the sensor model reproduces all 141 saved calibrations exactly; the source run is
byte-identical.

Accepted interpretation:
- `SCENE_CLOSED != global quiescence`, and `residual != failure`;
- 210 remains locally ACTIONABLE; it is an explicit residual, not complete;
- the strict gate v1 is a conservative first predicate, not claimed optimal.

## Foveal Controller Stage Charter 1 (accepted)

Charter: `docs/methodology/foveal-controller-stage-charter-1.md` (`9b9e710`). Application: `40426b2`,
which updates `CLAUDE.md`'s current-project-stage section and adds a README status paragraph.

    FOVEAL_CONTROLLER_STAGE_CHARTER_1_ACCEPTED

- **Controller-01 baseline freeze.** Controller-01 is accepted and frozen as the good-enough
  integrated-controller baseline. There is no automatic effort to perfect its local policy; known
  limitations are documented rather than repaired. It stays available for comparison and may be
  revisited only by an explicit future scientific decision. It is not claimed optimal or complete.
  Its known limitation (from 01C) is that FSG6f action selection does not guarantee that the
  unresolved frontier support motivating an action enters the binocular depth-measuring core. That
  limitation is known and localized, and it is not repaired.
- **Loop policy for the next generation.** The loop runs: normal scene loop → defer difficult local
  residue → keep servicing the scene → final residue pass (at most one strictly justified final
  observation per unresolved object) → scene closed, possibly with residual objects.
  - `local unresolved != global failure`.
  - A `DEFERRED` / `RESIDUAL` state exists conceptually; it is not yet in code and not yet named.
  - The final probe's minimum principle is that the unresolved support must actually be placed inside
    the binocular depth-measuring core. The exact predicate is left to Controller-02, which will use
    the simplest defensible version.
- **Blender object list.** It is to be retired as controller input, moving to reference / evaluation.
  It is not removed yet.
- **Natural Bootstrap-1.** Discover perceptual hypotheses and seed gazes from a low-resolution
  observation, with no semantics; over-segmentation is acceptable. **Natural Bootstrap-2**, identity
  persistence without Blender IDs, is a separate later question.
- **Generality.** After Natural Bootstrap-1, transfer to **Tabletop** with the same controller and no
  scene-specific retuning.
- **Visual Language 1.** Stable visual semantics across experiments, keeping four distinctions:
  measurement vs new geometry, visible vs depth measured, actionable vs worth one final look, and
  residual vs failure.

Signed near-term roadmap (directional; one causal question per executed experiment):

    Controller-01C (accepted audit)
      -> FREEZE Controller-01 (good-enough baseline)
      -> Controller-02 (normal loop + deferred residue + one strict final residue probe)
      -> Visual Language 1
      -> Natural Bootstrap-1 (low-resolution perceptual discovery)
      -> Classroom validation
      -> Tabletop transfer (same controller, no scene-specific retuning)
      -> Natural Bootstrap-2 (remove remaining oracle instance identity)

## Controller-01C frontier/action correspondence audit (accepted at `bbc37b8`)

Controller-01C is accepted as a valid read-only scientific audit (no render, no new OBSERVE, no policy
change).

Record (branch `controller/controller-01c-frontier-action-correspondence`, base `1ba2b59`):
- contract: `docs/controller/controller-01c-frontier-action-correspondence-contract.md` (`5506aaa`);
- implementation: `tools/controller/controller01c.py` (`dca972f`, `b6ae6ab`);
- report: `docs/controller/controller-01c-frontier-action-correspondence-report.md` (`bbc37b8`);
- output: `/home/lvelho/rd/f3d-vision/previews/controller-01c-frontier-action-correspondence/audit.json`;
- visual: `/home/lvelho/rd/f3d-vision/visuals/controller-01c/frontier-action-correspondence.png`.

Accepted result: **the FSG6f fixation did not service the frontier that requested it.**

| measured quantity | value |
|---|---|
| selected FSG6f OPEN support | 30 elements |
| inside either eye's look-25 depth-measuring core | 0 / 30 |
| inside both raw tangent images | 30 / 30, all labelled object 210 |
| valid target-depth measurements | 0 / 30 |
| associated under the accepted 12 mm rule | 0 / 30 |
| nearest look-25 target measurement | about 0.31–0.38 m away |
| same original frontier window after the look | OPEN 30, resolved 0 |

Four-way correspondence:

| | remains OPEN | resolved |
|---|---|---|
| measured by look 25 | 0 | 0 |
| not measured by look 25 | 30 | 0 |

Accepted causal explanation: FSG6f selected the next fixation by taking a fixed 5° step toward the
support direction rather than aiming the depth-measuring core at the unresolved support itself. In this
case, the depth core stepped past the frontier strip.

`predicted_new_angular_area_deg2` (about 45.67 deg²) is **not** a sensor-novelty prediction. It is the
area of the candidate's 12° view box outside the 1–99 % yaw/pitch extent of the target's effective
geometry. It uses no sensor model, no frontier elements and no observation footprint.

Accepted evidence: truth firewall 0 violations; audit checks 42/42; mutants 25/25 caught; layout
502/502; layout mutants 50/50; source previews unchanged.

This limitation of the accepted local policy is **known and localized**: FSG6f action selection does
not guarantee that the unresolved frontier support motivating an action enters the binocular
depth-measuring core. It is documented, not scheduled for repair.

## Controller-01B single post-watchdog continuation (accepted at `f90d738`)

Controller-01B accepted.

Record (branch `controller/controller-01b-single-continuation`, base `a60d448`; merged forward with the
accepted `main` at `b4d115d`):
- contract: `docs/controller/controller-01b-single-continuation-contract.md` (`bccd0cb`);
- implementation: `tools/controller/controller01b.py` (`8e8af5a`; the derived attribution `ebbd93f`);
- report: `docs/controller/controller-01b-single-continuation-report.md` (`f90d738`);
- run: `/home/lvelho/rd/f3d-vision/previews/controller-01b-single-continuation`;
- visual: `/home/lvelho/rd/f3d-vision/visuals/controller-01b/overview.png` (Level A).

Accepted measured result:

    CONTROLLER01B_ONE_LOOK_REPROBE_ACTIONABLE

Key measurements (one OBSERVE only: target 210 `wall.008`, gaze [7.6, 18.2]):

| quantity | value |
|---|---|
| target-valid points | 26,950 |
| new surfels | 0 |
| new head-depth cells | 0 |
| new observation-footprint cells | 0 |
| active map | 163,944 -> 163,944 |
| effective geometry | 1,938,913 -> 1,965,863 |
| pre | FSG6f `continue`; OPEN 52; candidates 1; proposal [7.6, 18.2] |
| post | FSG6f `no_frontier`; OPEN 0; candidates 0; Cyclopean eligible 151; ACTIONABLE; proposal [-17.6, 18.9], **not executed** |

Accepted derived attribution:
- the previous FSG6f window still contains the original 52 OPEN frontier points after look 25;
- the FSG6f transition to `no_frontier` came from the frontier window moving with the executed gaze,
  not from new information resolving that previous frontier.

No new stopping policy is stated.

## Controller-01 visual package (accepted at `ef7bd45`)

Luiz and Chat inspected the generated images and accept the package as the first Level-B
application of Policy 1.

Record (branch `visuals/controller-01-retrofit`, base `a60d448`):
- contract: `docs/controller/controller-01-visuals-contract.md` (`75f4aec`);
- generator: `tools/controller/visualize_controller01.py` (`94ff223`);
- report: `docs/controller/controller-01-visuals-report.md` (`ef7bd45`), with the file hashes and
  the regeneration command;
- output: `/home/lvelho/rd/f3d-vision/visuals/controller-01/` (`overview.png`, the event cards
  `events/reactivation-0109.png`, `events/reactivation-0178.png`, `events/watchdog-0210.png`,
  `scene-final.png`, supplementary diagnostics, active-map PLYs).

Accepted strengths:
- the scientific phenomena are visible, not merely controller bookkeeping;
- the natural reactivations of 109 and 178 are causally inspectable;
- the 210 watchdog / Controller-01A story is inspectable;
- active fused maps and measurement memory are explicitly distinguished;
- controller-time and derived information are labelled;
- no evaluation truth is used (firewall: 0 violations).

Future visual-style guidance (**non-blocking**; the accepted generator and report are not changed
for it):
- microscopic changes, such as 109's four points, benefit from a magnified inset;
- scene views should make the meaning of white/void explicit;
- repeated measurements must not visually imply new spatial support;
- presentation-safe simplified variants may later accompany dense scientific figures.

## Preview/visual lifecycle Policy 1 (accepted)

Specification: `docs/methodology/preview-visual-policy.md` (`7b32d44`). Application: `262e490`.

    PREVIEW_VISUAL_LIFECYCLE_POLICY_1_ACCEPTED

- **`./previews/`, machine-facing experimental memory.** It is gitignored. It holds the current
  stage's run evidence and regenerable intermediates, which may be large. It is kept for the
  current stage, is disposable afterwards, and is never the permanent record. New previews never
  go into external archives.
- **`./visuals/`, human-facing scientific memory.** It is gitignored and persistent for the whole
  project. It is compact and generated by Git-tracked tools. Reports record each visual's path and
  regeneration command.
- **The canonical four-panel active-perception visual**: scene/attention, foveated observation,
  Cyclopean/epistemic, persistent 3-D memory.
- **Visual levels.** Level A (`visuals/<step>/overview.png`) for every executed scientific step;
  Level B for significant experiments; Level C for demonstration milestones.
- **Truth labels.** CONTROLLER-TIME / DERIVED / REFERENCE; reference imagery never feeds back into
  control.
- **Git** holds the durable record: code, contracts, reports, summaries, provenance, hashes,
  regeneration commands and acceptance.
- **Mechanics.** `CLAUDE.md` states the stricter result rule, and `.gitignore` ignores `visuals/`.
  `.gitignore` is a baseline-tag file, so `tools/baseline/check_baseline_files.py` gained an exact
  "edited in place" rule for the one declared edit.

Current-stage data:
- `previews/controller-01-full` is the canonical Controller-01 run.
- `visuals/controller-01/` is the accepted Controller-01 Level-B visual package.
- `previews/controller-01b-single-continuation` and `visuals/controller-01b/overview.png` are the
  accepted Controller-01B run and visual.
- `previews/controller-01c-frontier-action-correspondence/audit.json` and
  `visuals/controller-01c/frontier-action-correspondence.png` are the accepted Controller-01C audit and
  visual.
- `previews/controller-01a-terminal-audit/audit.json` was re-established by re-running the
  accepted audit against it. The scientific fields are identical, and so is the result:
  `CONTROLLER01A_FINAL_REPROBE_ACTIONABLE`, prefix 58 OPEN / 1 candidate / `[7.6, 18.2]`,
  terminal 52 OPEN / 1 candidate / the same gaze, 190,011 post-watchdog measurements, effective
  geometry 1,748,902 → 1,938,913.
- **OLD-PREVIEWS**, `/home/lvelho/temp/previews-2026.09.28`, keeps the earlier stages' reference
  trees; its `controller-01-full` copy was removed after the verified move. No new experiment writes
  there, and current `./previews` does not symlink into it. Its remaining trees may be deleted only
  after a separate dependency audit.

## Accepted scientific / architectural state

The sealed scientific behavior is unchanged through Conceptual Cores 1–14 and Repository
Stage Transition 1.

Conceptual ownership established so far:

- `fov3d.reconstruction.measurement_memory`
  - valid patch measurement filtering
  - append-only instance-keyed measured 3-D memory
  - effective target geometry composition
- `fov3d.geometry.head_chart`
  - fixed-head yaw/pitch mapping and chart indexing
- `fov3d.reconstruction.association`
  - canonical 12-mm surface association radius
- `fov3d.epistemic.head_memory`
  - persistent head-centered epistemic memory
  - `HeadEvidence`
  - `add_head_patch`
- `fov3d.scene.partition`
  - `SupportLayer`
  - `support_depth_from_map`
  - `joint_owner`
  - `label_joint_regions`
- `fov3d.scene.boundaries`
  - `_interface_edges`
  - `_trace_edge_components`
  - `extract_boundaries`
- `fov3d.scene.corridors`
  - Core 6, gap-corridor geometry: `_component_boundary`, `_line_cells`, `gap_corridor`,
    `corridors_for_object`
  - Core 10, corridor relation origin: `_region_code`, `_own_labels`,
    `_joint_region_own_component`, `relation_origin`
- `fov3d.scene.lineage` (Core 7)
  - `_lineage`
  - `_target_component_raster`
- `fov3d.scene.state_validation` (Core 8)
  - `attach_state_region_codes`, which keeps its compatibility name; the rename is
    deferred
- `fov3d.scene.relations` (Core 9)
  - the NumPy-only boundary-depth-order module: `_region_object`, `_weighted_quantile`,
    `boundary_depth_order`
- `fov3d.epistemic.partition` (Core 11; candidate-free since Core 12)
  - the intrinsic epistemic partition: `REGION_KIND`, `REGION_KIND_BY_CODE`,
    `_component_labels`, `_distance_to_target`, `_touches_edge`, `_centroid_angles`,
    `_angular_distance_deg`, `_region_interfaces`, `build_epistemic_partition`
  - since Core 12 it no longer owns candidate semantics (`CANDIDATE_KINDS`,
    `region["candidate"]`, `diag["candidate_region_count"]`)
  - since Core 13 it no longer depends on the experiment's target schedule
    (`all_target_ids`) nor emits `reconstruction_status`; `surface_source` stays intrinsic
    causal evidence provenance
  - since Core 14 it no longer takes the fixation/action history (`gazes_deg`) nor emits
    `min_distance_to_historical_gaze_deg`; `_angular_distance_deg` stays as a generic helper
  - it is therefore independent of the candidate interpretation, the experiment's future
    target schedule and the fixation/action history; it depends only on accumulated
    evidence and the chart (it is still relative to one designated target)
  - imported explicitly and OpenCV-dependent; `fov3d/epistemic/__init__.py` is unchanged,
    so a bare `import fov3d.epistemic` stays OpenCV-free
- `fov3d/experiments/classroom_partition/candidate_policy.py` (Core 12, experiment-side)
  - the historical `OTHER_SURFACE`/`UNKNOWN` → candidate interpretation:
    `CANDIDATE_KINDS`, `annotate_candidate_partition`, `build_candidate_partition`, which
    re-creates the accepted candidate view exactly
  - it composes on `run_context`; the full historical stack is
    intrinsic → gaze context → run context → candidate annotation
- `fov3d/experiments/classroom_partition/run_context.py` (Core 13, experiment-side)
  - owns `reconstruction_status`: `annotate_reconstruction_status`,
    `build_run_context_partition` (`mapped_now`/`targeted_later`/`never_targeted` from
    `mapped_cells` and `all_target_ids`); since Core 14 it composes on `gaze_context`
- `fov3d/experiments/classroom_partition/gaze_context.py` (Core 14, experiment-side)
  - owns the historical target-local gaze descriptor: `annotate_gaze_context`,
    `build_gaze_context_partition` (`min_distance_to_historical_gaze_deg` from the region
    centroid and the producers' target-local gaze list)

The Phase-4 adapter `fov3d/experiments/classroom_partition/relations.py` keeps identity
imports of the Core-9 and Core-10 names; `annotate_corridor` resolves the scene functions.
`fov3d/experiments/classroom_partition/benchmark.py` keeps the historical API:
`benchmark.CANDIDATE_KINDS` is the policy constant and `benchmark.build_epistemic_partition`
is an alias of `build_candidate_partition`. Phases 6, 7, 8 and 8b call
`build_candidate_partition` explicitly; Phase 8b keeps its own, independent
`candidate_raw`/`eligible_candidate` interpretation.

`fov3d.scene` lazily re-exports the four scene-partition names, so a bare
`import fov3d.scene` stays OpenCV-free. The modules `boundaries`, `corridors`, `lineage`,
`state_validation` and `relations` are imported explicitly. `corridors` needs `cv2`; the
others are NumPy-only.

Conceptual Core 14 was accepted at `296001e8683ba0b1ad62642811d3dea0e84b6566` with:

    CONCEPTUAL_CORE14_GAZE_CONTEXT_SEPARATION_PRESERVES_BEHAVIOR

The evidence, from `docs/conceptual-core/migration-conceptual-core-14-report.md`, includes:
- the intrinsic output is accepted Core 13 minus only the gaze-distance field; `gaze_context`,
  `run_context` and `candidate_policy` re-create the accepted outputs exactly, and the
  historical producers (with their target-local gaze selection) are unchanged;
- the Core-14 checker passes 64/64; it caught 48/48 dynamic and 22/22 static mutants;
- the random-state differential agreed on 10,000/10,000 states;
- all 8 Phase-6/7/8/8b products are byte-identical;
- the sealed baseline is 31/31 and the golden comparison reports `MISMATCHES 0`;
- the 13 accepted reference trees are unchanged.

The Core-14 report ends with a read-only **Controller-readiness boundary** (intrinsic
information available, separated historical layers, what is not implemented, and the
observation that the intrinsic partition is still target-relative).

Earlier accepted Cores (1–13) are summarised in their reports. The cleanup of
`own_support_labels` versus `_own_labels`, and of `component_lineage` versus
`fov3d.scene.lineage._lineage`, remains **deferred**.

## Active next step

**The conceptual-core migration remains paused after Core 14.** Do not create Core 15
automatically and do not create a new migration branch.

Controller-01, 01A, 01B and 01C, Policy 1, the Controller-01 visual package, Foveal Controller Stage
Charter 1, Controller-02, Visual Language 1 and Breadth-1 are accepted. The Controller-01 investigation is
closed. Controller-01 and Controller-02 are frozen unless Luiz explicitly reopens them.

**Next scientific design target: Natural Bootstrap-1** (see "Current roadmap"). It begins only after Luiz
and Chat discuss its design: no branch, contract or implementation exists yet. FSG6f is not repaired.

## Decision-critical open items

1. Controller design is led by Luiz with Chat, under Stage Charter 1. Controller-02 settled the
   deferred/residual semantics and honest scene closure with a strict final-look gate v1 (not claimed
   optimal; residual objects are not claimed complete). Controller-01 (frozen) keeps the accepted local
   policy unchanged. Open questions from its report:
   - the adequacy of the 24-look watchdog under effective geometry;
   - target-local versus global observation evidence for the Cyclopean handoff (both natural
     reactivations came through it);
   - the service latency of reactivated objects under the cyclic order;
   - sticky BLOCKED;
   - the metric scope (active fused map versus effective geometry);
   - measured-but-unlocated instances;
   - a target-neutral scene-level epistemic formulation.
2. Still not designed or implemented: candidate ranking/scoring, a new fixation policy,
   vergence/focus action, inhibition of return, gaze recency/decay, the budget/quality
   trade-off, a moving head, semantic decisions.
3. Representation observation for the design: the intrinsic partition is still relative to one
   designated target (`target_id`, `target_support`, the target kinds and target distances).
4. Deferred historical cleanups (not to be started automatically):
   - the target-relative `HeadEvidence` placement;
   - the Phase-5 `reconstruction_status` duplication;
   - the `_own_labels`/`own_support_labels` and `component_lineage`/`_lineage` cleanup;
   - the `attach_state_region_codes` rename;
   - the consumerless aliases;
   - the three private `_insert_after` copies;
   - the Phase-2 and Phase-3 boundary lineages.
5. Open items from Repository Stage Transition 1 (see its report):
   - `fov3d/__init__.py`'s docstring still names pre-transition paths. Fixing it is a
     text-only `fov3d/` change and needs an explicit decision.
   - `docs/conceptual-core/conceptual-core-map.md` keeps the stale headings "Proposed
     Conceptual Core 3 extraction" and "Proposed later extraction order".
   - Reference-tree location: current-stage previews live in the shared checkout's `previews/`
     (Policy 1). The earlier stages' reference trees stay in OLD-PREVIEWS,
     `/home/lvelho/temp/previews-2026.09.28`. Historical gates that name those `previews/…` trees
     need them linked until a dependency audit retires them.
6. `README.md`'s status paragraph predates the Controller-02, Visual Language 1 and Breadth-1 acceptances
   and the revised roadmap. These handoff updates did not touch it.
7. Breadth-1 evaluation universe (intentionally open): how collection-instanced Classroom geometry (desks,
   chairs, lamps, …), rendered but outside the 234-object catalog, should enter future reference /
   evaluation. It is left for Natural Bootstrap and later evaluation design.
