# Controller-01C: frontier / action correspondence audit — report

**Marker.**

    CONTROLLER01C_FRONTIER_ACTION_CORRESPONDENCE_AUDIT_COMPLETE

A read-only audit of Controller-01B's look 25 of object 210 `wall.008`. It used no Blender, rendered
nothing, executed no new OBSERVE, fused nothing into an accepted artifact and changed no policy. Every
number below is **MEASURED** by the commands listed, unless it is marked otherwise. The marker encodes no
action-targeting or stopping-policy decision. The branch is not merged, and the Cyclopean proposal
[-17.6, 18.9] was not executed.

## Question and answer

**Question.** Did look 25 actually acquire evidence at the specific OPEN frontier support that caused
FSG6f to choose [7.6, 18.2]?

**Measured answer.** No, for every support element:
- none of the 30 OPEN support elements lay inside either look-25 rectified core, the 256 px raster where
  depth is measured;
- none received a look-25 measurement within 12 mm; the nearest was 0.31–0.38 m away;
- all 30 are still OPEN in the same pre-look window, unchanged.

The support was visible to look 25 only in the periphery. All 30 elements, and their look-ahead targets,
project inside both 640 px raw tangent images onto pixels labelled 210, but outside both cores.

## Sources and provenance

| item | value |
|---|---|
| branch | `controller/controller-01c-frontier-action-correspondence`, from `main` @ `1ba2b59` (Controller-01B accepted), isolated worktree |
| contract | `5506aaa` *Specify Controller-01C frontier/action correspondence audit* |
| implementation | `dca972f` *Implement the Controller-01C frontier/action correspondence audit*; `b6ae6ab` rectifies the full-raster labels with look 25's own calibration (see deviations) |
| source run | `/home/lvelho/rd/f3d-vision/previews/controller-01-full`; accepted Controller-01, report `e3bf5e0`; `manifest.json` `d293a98f…`, `actions.json` `12cdbe4d…` |
| source audit | `/home/lvelho/rd/f3d-vision/previews/controller-01a-terminal-audit/audit.json`; accepted Controller-01A, `FINAL_REPROBE_ACTIONABLE` |
| source 01B run | `/home/lvelho/rd/f3d-vision/previews/controller-01b-single-continuation`; accepted Controller-01B, `CONTROLLER01B_ONE_LOOK_REPROBE_ACTIONABLE` |
| output | `/home/lvelho/rd/f3d-vision/previews/controller-01c-frontier-action-correspondence/audit.json` (sha256 `41b8fbae…`) |
| visual | `/home/lvelho/rd/f3d-vision/visuals/controller-01c/frontier-action-correspondence.png` and its sidecar `frontier-action-correspondence.json` |

## Commands (from the repository root, at `b6ae6ab` with a clean tracked tree)

    S=/home/lvelho/rd/f3d-vision/previews
    A="--source $S/controller-01-full --audit $S/controller-01a-terminal-audit/audit.json \
       --c01b $S/controller-01b-single-continuation"
    .venv/bin/python tools/controller/controller01c.py audit  $A --out $S/controller-01c-frontier-action-correspondence
    .venv/bin/python tools/controller/controller01c.py visual $A --out $S/controller-01c-frontier-action-correspondence \
        --visuals /home/lvelho/rd/f3d-vision/visuals/controller-01c
    .venv/bin/python tools/controller/controller01c.py check  $A --out $S/controller-01c-frontier-action-correspondence \
        --visuals /home/lvelho/rd/f3d-vision/visuals/controller-01c

The three commands took 82.8 s, 83.0 s and 82.6 s wall time (batch). The audit printed
`RESULT CONTROLLER01C_FRONTIER_ACTION_CORRESPONDENCE_AUDIT_COMPLETE`; the visual printed
`visual checks 31/31; firewall violations 0`; the check printed `SUMMARY checked=42 failed=0`.

## Reconstruction and reproduction gates (all passed)

**Accepted Controller-01B reconstruction (7 gates).**
- All 141 replayed memory additions and matcher-recreated patches equal the saved ones.
- 210's replayed active map equals its saved `final_map`.
- E_t(210), the head-evidence cells and the `seen_any` cells equal the saved terminal view.
- The pre-action probe reproduces the accepted 01A terminal probe.

**Audit gates (23).**
- **Sources:** the accepted hashes, the 01A outcome, and 01B's marker and single OBSERVE.
- **Pre-look state:** 24 own looks; gaze [2.6, 18.2]; effective geometry 1,938,913 = 163,944 active-map
  surfels + 1,774,969 memory points; frontier 350/52/28/270; 1 candidate.
- **Selected candidate:** [7.6, 18.2] with OPEN / raw / map-resolved / boundary-resolved support
  30/43/3/10, equal to 01A.
- **Support identity:** the re-extracted frontier equals the in-process decision. The direction (+1, 0)
  and the counts reproduce. The frontier score over the 30 elements equals the decision's (6.135141348988722;
  relative 1e-12). The candidate's continuation evidence, recomputed from the support mask, equals the
  decision's: per-eye rays 21/18, object pixels 1,854/1,715. Every element's 25 mm voxel reproduces its
  centroid.
- **Look-25 replay** (no render; temporary directory):
  - the post probe equals 01B's (ACTIONABLE, Cyclopean [-17.6, 18.9]);
  - target-valid 26,950 and new surfels 0;
  - the acquisition is 01B's `fix_24` (calibration gaze [7.6, 18.2]);
  - the post map equals 01B's saved `maps/fix_24.npz`;
  - the evidence is exactly the 26,950 instance-210 valid points (= the memory additions, source 141);
  - the full rectified labels cropped to the core equal the matcher's core labels.
- **Fusion:** the re-derived 12 mm assignment touches exactly the 24,956 surfels whose `fix_24`
  provenance bit was set, with support +1 on each.
- **Association:** the 12 mm counts agree with the accepted `_target_mapped_mask` for every element.
- **Windows:**
  - the same (pre-look) window after look 25 is 350/52/28/270, the accepted 01B attribution;
  - the new window has OPEN 0 (313/0/37/276, the 01B post probe).
- **Area:** `_new_box_area` on the reconstructed inputs equals the decision's value.

## What a support element is

In the accepted code (the sealed `tools/fsg6f_frontier.py`, reached through `fov3d.control.frontier`), a
frontier element is a **25 mm voxel centroid** `x_e` of the effective target geometry. It lies within ±7° of
the current gaze and carries a **look-ahead target** `t_e` 0.12 m along its missing-tangent direction. Its
OPEN / MAP_RESOLVED / BOUNDARY_RESOLVED state classifies `t_e`, not `x_e`. The contract states this before
the audit ran. The audit therefore traces both `x_e` and `t_e`.

## Candidate support identity

The candidate +yaw (direction (1, 0)) has **30 OPEN support elements** within **43 raw aligned** elements
(3 MAP_RESOLVED, 10 BOUNDARY_RESOLVED). `audit.json` persists every one of the 43: frontier index, voxel
key, `x_e`, `t_e`, angles, strength, alignment, pre state, and voxel composition.
- **Location.** The 30 OPEN elements lie in a vertical strip at yaw −2.57° to −1.84° and pitch 11.3° to
  20.5°, 4.26–4.54 m from the head. That is inside look 24's core near its left edge. Their look-ahead
  targets lie 0.4°–1.6° further toward +yaw.
- **Voxel composition.** Their voxels hold 4,849 effective-geometry points: 472 active-map surfels and
  4,377 memory points.

| frontier index | voxel key | `x_e` yaw, pitch (°) | `t_e` yaw, pitch (°) | `x_e` left-core u (px) | nearest look-25 point (m) | `t_e` to geometry (mm) | earlier binocular tests | same-window post |
|---|---|---|---|---|---|---|---|---|
| 34 | (-8, 33, -168) | -2.52, 11.31 | -1.98, 11.36 | -81 | 0.377 | 19 | 2 | OPEN |
| 37 | (-8, 34, -168) | -2.52, 11.62 | -1.96, 11.05 | -81 | 0.371 | 18 | 2 | OPEN |
| 38 | (-8, 35, -172) | -2.41, 11.71 | -2.04, 11.49 | -79 | 0.350 | 117 | 2 | OPEN |
| 41 | (-8, 36, -168) | -2.52, 12.28 | -2.06, 11.97 | -81 | 0.362 | 26 | 4 | OPEN |
| 42 | (-8, 36, -167) | -2.57, 12.38 | -1.01, 12.32 | -82 | 0.375 | 83 | 7 | OPEN |
| 73 | (-8, 48, -168) | -2.52, 16.14 | -2.11, 15.70 | -80 | 0.364 | 28 | 6 | OPEN |
| 74 | (-8, 50, -172) | -2.40, 16.43 | -1.96, 15.88 | -78 | 0.350 | 115 | 5 | OPEN |
| 76 | (-8, 51, -171) | -2.47, 16.79 | -2.05, 16.52 | -79 | 0.354 | 109 | 6 | OPEN |
| 78 | (-8, 51, -168) | -2.51, 17.08 | -2.10, 16.81 | -80 | 0.364 | 28 | 6 | OPEN |
| 79 | (-8, 52, -172) | -2.40, 17.04 | -1.73, 16.57 | -78 | 0.349 | 110 | 5 | OPEN |
| 82 | (-8, 52, -167) | -2.57, 17.51 | -1.07, 17.32 | -81 | 0.377 | 70 | 5 | OPEN |
| 85 | (-8, 53, -168) | -2.52, 17.69 | -1.97, 17.22 | -80 | 0.368 | 19 | 5 | OPEN |
| 86 | (-8, 53, -167) | -2.57, 17.83 | -1.10, 18.06 | -81 | 0.378 | 77 | 5 | OPEN |
| 87 | (-8, 54, -172) | -2.41, 17.65 | -1.79, 17.13 | -78 | 0.351 | 111 | 5 | OPEN |
| 91 | (-8, 54, -168) | -2.52, 17.99 | -2.10, 17.53 | -80 | 0.366 | 28 | 6 | OPEN |
| 92 | (-8, 55, -172) | -2.40, 17.95 | -1.93, 17.99 | -78 | 0.350 | 109 | 5 | OPEN |
| 95 | (-8, 56, -172) | -2.40, 18.25 | -1.97, 17.78 | -78 | 0.350 | 116 | 5 | OPEN |
| 97 | (-8, 56, -168) | -2.52, 18.62 | -2.11, 18.12 | -80 | 0.366 | 27 | 6 | OPEN |
| 98 | (-8, 57, -172) | -2.41, 18.55 | -2.04, 18.20 | -78 | 0.352 | 117 | 6 | OPEN |
| 99 | (-8, 57, -167) | -2.57, 19.06 | -1.11, 18.65 | -81 | 0.380 | 68 | 4 | OPEN |
| 100 | (-8, 58, -172) | -2.41, 18.86 | -1.79, 18.54 | -77 | 0.351 | 111 | 4 | OPEN |
| 103 | (-8, 59, -172) | -2.41, 19.15 | -2.04, 19.02 | -77 | 0.351 | 114 | 5 | OPEN |
| 106 | (-8, 59, -168) | -2.52, 19.55 | -2.08, 19.40 | -79 | 0.366 | 23 | 5 | OPEN |
| 107 | (-8, 60, -172) | -2.40, 19.45 | -2.06, 19.56 | -77 | 0.352 | 108 | 5 | OPEN |
| 111 | (-8, 62, -168) | -2.51, 20.49 | -2.17, 20.16 | -79 | 0.365 | 38 | 5 | OPEN |
| 131 | (-6, 34, -172) | -1.84, 11.39 | -0.28, 11.50 | -67 | 0.314 | 25 | 2 | OPEN |
| 132 | (-6, 35, -172) | -1.84, 11.72 | -0.29, 11.90 | -67 | 0.308 | 24 | 5 | OPEN |
| 137 | (-6, 49, -172) | -1.84, 16.13 | -0.33, 16.49 | -66 | 0.307 | 22 | 6 | OPEN |
| 138 | (-6, 57, -172) | -1.84, 18.56 | -0.28, 18.28 | -66 | 0.310 | 26 | 6 | OPEN |
| 139 | (-6, 60, -172) | -1.84, 19.46 | -0.27, 19.16 | -66 | 0.310 | 16 | 5 | OPEN |

The left core spans u = 0–255 px. "Earlier binocular tests" counts the own looks, among all 25, in which
`t_e` was binocularly observable; all of them came before look 25.

## Trace through look 25 (the 30 OPEN support elements)

| quantity | support point `x_e` | look-ahead target `t_e` |
|---|---|---|
| inside the left / right rectified core (256 px) | 0 / 0 | 0 / 0 |
| inside both cores | 0 | 0 |
| inside the left / right raw tangent image (640 px) | 30 / 30 | 30 / 30 |
| labelled 210 in both full rectified rasters | 30 | 30 |
| binocularly observable (accepted FSG6f patch evidence) | 0 | 0 |
| valid 210 depth in the 5 px left-core patch | 0 | 0 |
| ≥ 1 look-25 target measurement within 12 mm | 0 | 0 |
| total 12 mm associations | 0 | 0 |

- **Projection.** In the left core, `x_e` falls at u = −82 to −66 px and `t_e` at u = −73 to −35 px. In the
  right core the ranges are −100 to −83 and −90 to −51 px. `v` spans 82–278 px.
- **Nearest measurement.** The nearest look-25 target measurement to any `x_e` is 0.307 m (median 0.353 m,
  maximum 0.380 m).
- **The 13 other raw aligned elements.** None of the 43 raw aligned elements, at `x_e` or at `t_e`, lies
  inside either core or received a 12 mm association.
- **Support-count and provenance changes.** No active-map surfel in any support voxel was updated by the
  replayed fusion. There were 0 updated surfels, 0 look-25 measurements fused into them, and no `fix_24`
  provenance bit set on them. Elsewhere, look 25's 26,950 points updated 24,956 surfels.

## Same-window post classification

The frontier was re-extracted from the post-look effective geometry in the **original** pre-look window
(gaze [2.6, 18.2]) and classified with all 25 own looks. Elements were matched by their 25 mm voxel key.

| state after look 25 | of the 30 OPEN support | of the 43 raw aligned |
|---|---|---|
| OPEN | 30 | 30 |
| MAP_RESOLVED | 0 | 3 |
| BOUNDARY_RESOLVED | 0 | 10 |
| no longer frontier | 0 | 0 |

Every matched element was bit-identical: `x_e` and `t_e` shifts were 0.0 m. The **fixed-obligation**
classification, which applies the post-look geometry and history to the exact pre-look `t_e`, also gives
30 OPEN. The window totals were 350/52/28/270 before and after look 25.

**What kept each element OPEN.**
- **In look 25:** for all 30, the look-ahead target was outside a look-25 core. It was therefore neither
  mapped by look 25 nor binocularly testable.
- **In the earlier own looks:**
  - every one of the 30 look-ahead targets had been binocularly tested, 145 tests in total;
  - every test found 210 present, with a binocular object fraction of 1.00, never below 0.15;
  - the post-look effective geometry lies 16–117 mm from the targets (median 53 mm), which is more than
    12 mm.

  So these obligations were observed before look 25 and were neither MAP_RESOLVED nor
  BOUNDARY_RESOLVED by those observations. This is recorded as a measurement, not as an interpretation.

## The four-way cross-tab (pre-declared definitions)

"Measured by look 25" means at least one look-25 target measurement of 210 lies strictly within 12 mm of
`x_e`. "Remains OPEN" means the same-window post state is OPEN.

| | remains OPEN | resolved |
|---|---|---|
| **measured by look 25** | 0 | 0 |
| **not measured by look 25** | 30 | 0 |

The same cross-tab taken at the look-ahead target `t_e` is also 0 / 0 / 30 / 0.

**Decomposition (C5), with no threshold applied.**
- **A**, selected OPEN support never sampled by look 25: **30 of 30**.
- **B**, sampled with valid target depth but still OPEN: **0 of 30** for look 25.
- **C**, mixed: not present.

The earlier-look observation above (145 binocular tests with 210 present, no resolution) is reported
separately. It concerns looks other than look 25.

**Descriptive mechanism, read from the code.** FSG6f's candidate gaze is the current gaze plus one
5° lattice step in the aligned direction (`choose_next`). It is not placed on the support. The support lay
4.4°–5.2° left of look 24's gaze and pointed toward +yaw, so the +5° step put look 25's core
(yaw 1.6°–13.6°) entirely to the right of the support. No policy conclusion is drawn.

## `predicted_new_angular_area_deg2 ≈ 45.67 deg²` (code meaning)

**Computation.** `_new_box_area((yaw, pitch), half, ye, pe)` returns `(2·half)² − |B ∩ X|`, where:
- `B` is the candidate's axis-aligned yaw/pitch box `[yaw ± half] × [pitch ± half]`;
- `half` is half the calibration's `nominal_core_fov_deg`, here 6°;
- `X` is the box spanned by the 1 % and 99 % quantiles (`map_extent_quantile = 0.01`) of the yaw and pitch,
  seen from the head origin, of the map passed to FSG6f. That map is 210's effective geometry, all
  1,938,913 points.

**For this candidate:**
- `B` = yaw [1.6, 13.6] × pitch [12.2, 24.2];
- `X` = yaw [−21.66, 28.19] × pitch [0.062, 20.394];
- the intersection is 98.33 deg², so the value is 144 − 98.33 = **45.669 deg²**. That is the strip of the
  candidate box above 210's 99 % pitch quantile, pitch 20.39°–24.2°.

**Intended meaning, according to the code.** It measures the candidate box's angular area outside the
map's robust angular bounding box: a map-angular-extent novelty of the view box.
- It uses no sensor model: no projection, occlusion, depth range or image evidence.
- It does not use the frontier elements or their support, nor the observation footprint.
- It is the **first sort key** (descending) among allowed candidates, ahead of `frontier_score`. This
  decision had one allowed candidate, so it did not change the selection. The direction came from the
  frontier support. The support strip (yaw about −2°) lies outside `B` and plays no part in this value.

**Relationship to look 25's evidence:**
- Of look 25's 26,950 target-valid points, 26,497 fall inside `B`. Only 502 fall outside the pre-look `X`,
  that is, in the "predicted new" strip.
- In that strip, look 25's valid measurements were mostly of other instances: 110 `beams` 10,439;
  123 `ceilingMoulding` 5,945; 10 `Cube.006` 561; 210 `wall.008` 502.
- `X` barely changed: pitch 99 % quantile 20.394° → 20.400°. The same box's value after look 25 is
  45.60 deg².
- Look 25 created no new surfel.

## Truth firewall

`TruthFirewall` with `controller01.is_evaluation_truth` was active in every mode:
- **0 violations**;
- the audit opened 454 controller-time source files, none of them `evaluation.json` or under
  `bootstrap/evaluation_only/`.

Two further preservation facts:
- The per-file sha256 manifests of the three source trees were identical before and after the audit,
  visual and check runs: the Controller-01 run (1,678 files, also equal to the manifest taken in the 01B
  step), the 01B run (17 files) and the 01A `audit.json`.
- The preservation hashing reads bytes only. No evaluation file is parsed.

## Fail-capability (checks 1–12)

The check mode recomputes the audit and compares it with the saved `audit.json` and the visual sidecar.
The fail-capability harness (scratch `c01c/mutants.py`) worked on throwaway copies only:
- **data corruptions** act on copies of `audit.json` and the sidecar;
- **code mutants** act on throwaway repository copies.

The unmutated copy passed (rc 0). Every mutant was refused with rc 1, and the named check or gate below
reported it. **Result: 25/25 caught**, and each of the 12 contract checks is shown to fail. The source
trees and the canonical 01C outputs were byte-identical afterwards.

| # | corruption / mutant | caught by |
|---|---|---|
| 1a | wrong source run (a `manifest.json` with other content) | check 1 (stopped) |
| 1b | audit records other run hashes | check 1 (stopped) |
| 2 | recorded raw aligned support 44 | check 2 |
| 2c | (code) wrong candidate direction (dy = +1) | support-count gate (stopped) |
| 3 | recorded selected gaze [7.7, 18.2] | checks 2, 3 |
| 3c | (code) recorded gaze 0.1° off | checks 2, 3 |
| 4 | one OPEN support element dropped | checks 4, 12 |
| 4c | (code) OPEN filter dropped (support = raw aligned, 43) | support-count gate (stopped) |
| 5 | two support identities swapped (`x_e`) | check 5 |
| 5c | (code) support mask permuted, same count 30 | frontier-score identity gate (2.2276 vs 6.1351; stopped) |
| 6 | recorded look-25 patch hash altered | check 6 |
| 6c | (code) look 24's acquisition used as look 25 | acquisition gate (stopped) |
| 7 | a recorded core projection moved 0.5 px | check 7 |
| 7c | (code) projection with look 24's calibration | check 7 (known-answer reprojection), 12 |
| 8 | recorded association radius 24 mm | check 8 |
| 8c | (code) association radius 24 mm | checks 7, 8 (synthetic 11.9/12.1 mm known answer) |
| 9 | recorded target-valid count 26,951 | checks 6, 9 |
| 9c | (code) other instances' measurements counted as 210 evidence | evidence gate (stopped) |
| 10 | same-window record taken from the new window | check 10 |
| 10c | (code) same window evaluated at the executed gaze | same-window gate (313/0/37/276; stopped) |
| 11 | an evaluation-truth access recorded | check 11 |
| 11c | (code) the audit opens `evaluation.json` | firewall `PermissionError` before the open; check error; violation recorded |
| 12a | summary cross-tab altered | check 12 |
| 12b | visual sidecar count altered | check 12 |
| 12c | (code) summary counts "measured" at `t_e` with a wrong predicate | check 12 |

Mutants 8c and 7c also moved the recorded known answers, so check 7 fired for 8c as well. The
association results themselves could not reveal a 24 mm radius here, because every support element's
nearest look-25 measurement is at least 0.31 m away. The synthetic 11.9/12.1 mm control is what catches
it.

## Visual (Policy 1, Level A)

`/home/lvelho/rd/f3d-vision/visuals/controller-01c/frontier-action-correspondence.png` (2122 × 1829):
- sha256 `534a97c724e6d5c20b5b7f8c03cc5c5b21bd70c561479b192d112bc2dab9f7df`, identical across two
  generations at `b6ae6ab`;
- sidecar `frontier-action-correspondence.json`, sha256 `80950093…`, holding the annotated numbers,
  which check 12 compares.

Regeneration: the `visual` command above.

The four panels answer "Did the action actually service the frontier that requested it?":
1. **Pre-action frontier** (DERIVED). The pre-window frontier states, the 30 OPEN support elements with
   their look-ahead arrows, the look-24 and look-25 cores, and the frontier window.
2. **Look-25 binocular observation** (CONTROLLER-TIME images and labels; DERIVED projections). The full
   rectified left/right rasters, with the 256 px cores outlined, 210's label outline, and the matcher-valid
   depth. The same 30 elements are marked at their projections (o = `x_e`, × = `t_e`), all outside the
   cores.
3. **3-D correspondence** (CONTROLLER-TIME points; DERIVED positions). Front and top orthographic views in
   a local frame. They show the support elements, the pre-look geometry, look 25's 26,950 measurements,
   and the nearest-measurement distance (0.31 m).
4. **Same-window post classification** (DERIVED). The same pre-look window after look 25, with the same 30
   elements coloured by post state (all OPEN), the cross-tab and the kept-open conditions.

No evaluation or reference truth is used.

## Deviations and incidents

1. **Trace extended with full-raster labels.** The contract asked for raw-tangent inclusion. The trace
   additionally records each element's pixel label and 5 px label fraction in look 25's full rectified
   rasters. The labels are the matcher's own rectified oracle labels, before it crops the core, and a gate
   checks that they equal the core labels inside the core. This quantifies that the support was seen
   peripherally as 210 (30/30). The addition is purely additive.
2. **Plumbing runs.** Three trial audits and visuals were written to scratch before the canonical run and
   discarded. They drove the visual's legibility fixes and the additions above. No number changed between
   trials.
3. **Canonical run restarted.** The first canonical attempt, at `dca972f`, was stopped before it wrote
   anything. `b6ae6ab` then made the full-raster rectification use look 25's calibration directly instead
   of the trace calibration. The values are identical, since the trace calibration is look 25's. The change
   lets a wrong-calibration mutant reach the named projection check 7 rather than an earlier gate.
   Everything reported comes from the run at `b6ae6ab`.
4. **Transient layout message.** A layout-checker run before `git add` of the new tool reported the
   then-untracked file. The committed state passes 502/502.
5. **Terminology.** The contract's "support surfels" are FSG6f frontier elements (voxel centroids of the
   effective geometry). Their voxels' active-map surfels were traced separately, for the support-count and
   provenance question.

## Layout checker and repository gates

At `b6ae6ab`:
- **Layout checker:** declares the contract (required), this report and the tool (allowed);
  `SUMMARY checked=502 failed=0`.
- **Other checkers:** Controller-01 56/56; Core-14 64/64; Classroom 12/12; facade 16/16; baseline
  accounting 31/31 (self-test 12/12); `verify_baseline` 9/9; `git diff --check` clean.
- **`fov3d/`:** unchanged; 0 diff lines vs `1ba2b59`.

The layout mutation suite (scratch `c01c_layout_mutants.py`) caught **50/50**, including:
- an undeclared tracked `tools/controller` tool;
- a misspelled, undeclared 01C report;
- the 01C contract untracked;
- the handoff reverted to before the 01B acceptance, or stripped of the 01B markers.

The worktree was restored.

## Unresolved (for Luiz and Chat)

- The interpretation of the counts: A = 30/30 for look 25, together with the earlier-look observation
  that the same obligations stayed OPEN despite 145 binocular observations of 210. Any consequence for
  action targeting, frontier resolution semantics or stopping behavior. This report draws none.
