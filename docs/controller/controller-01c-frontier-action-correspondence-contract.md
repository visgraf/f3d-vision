# Controller-01C: frontier / action correspondence audit — contract

## Status

A bounded, **read-only** audit with one causal question. No Blender, no render, no new OBSERVE, no
fusion into any accepted artifact, and no change to any threshold, scheduler, watchdog, stopping rule,
local policy or accepted artifact. It is not Controller-02.

    base              origin/main @ 1ba2b593510aa18f9203b4d314e32891935a4ce5 (Controller-01B accepted)
    sources           /home/lvelho/rd/f3d-vision/previews/controller-01-full           (accepted Controller-01)
                      /home/lvelho/rd/f3d-vision/previews/controller-01a-terminal-audit/audit.json (accepted 01A)
                      /home/lvelho/rd/f3d-vision/previews/controller-01b-single-continuation  (accepted 01B)
    branch            controller/controller-01c-frontier-action-correspondence (isolated worktree; not merged)
    tool              tools/controller/controller01c.py  (modes: audit | check | visual)
    output            /home/lvelho/rd/f3d-vision/previews/controller-01c-frontier-action-correspondence/audit.json
    visual            /home/lvelho/rd/f3d-vision/visuals/controller-01c/frontier-action-correspondence.png
                      (+ frontier-action-correspondence.json, the annotated numbers)
    result marker     CONTROLLER01C_FRONTIER_ACTION_CORRESPONDENCE_AUDIT_COMPLETE
                      (emitted only if every reproduction gate passes; it encodes no action-targeting
                      or stopping-policy decision)

Everything below is PROPOSED until the audit runs.

## Causal question

Did look 25 (Controller-01B's one OBSERVE of object 210 `wall.008` at [7.6, 18.2]) actually acquire
evidence at the specific OPEN frontier support that caused FSG6f to choose [7.6, 18.2]?

## What an FSG6f frontier element is (read from the accepted code, not reinterpreted)

`fov3d.control.frontier` re-exports the sealed `tools/fsg6f_frontier.py`; `object_policy.choose_next`
(sealed `tools/multiobject2c_policy.py`) only relabels 210 to FSG6f's `OBJECT_ID`.
- `extract_frontier(map, current yaw/pitch, calibration)` voxelizes the map passed to FSG6f — in
  Controller-01 the **effective target geometry** of 210 (active fused map followed by every measured
  210 point in memory, duplicates retained) — into 25 mm voxel centroids. It keeps centroids within
  ±(core/2 + 1°) = ±7° in yaw and pitch of the current gaze. A kept centroid with ≥ 6 neighbouring
  centroids within 65 mm and a tangent asymmetry ≥ 0.18 is a **frontier element**: source point `x_e` (the voxel centroid) and a
  **look-ahead target** `t_e = x_e + 0.12 m · missing tangent direction`.
- `classify_frontier_state` classifies each element by its **look-ahead target**:
  - MAP_RESOLVED: some map point lies strictly within 12 mm of `t_e` (the frozen fusion radius);
  - BOUNDARY_RESOLVED (if not MAP_RESOLVED): in at least one of 210's own looks, `t_e` projected into
    supported patches of **both** rectified cores and the binocular object fraction `max(f_L, f_R)` of
    the patch (radius `max(1, round(256·0.04)//2)` = 5 px) was < 0.15;
  - OPEN: neither.
- For a candidate direction `u` (unit lattice step), an element is **raw aligned support** when the
  angular direction of `t_e − x_e` has cosine ≥ 0.5 with `u`; **OPEN support** is raw aligned support
  that is OPEN.

"Support surfels" in this audit are therefore these frontier elements (voxel centroids of the
effective geometry), not individual active-map surfels. Each is persisted with its identity (below).

## Reconstruction and required reproduction (stop gates)

The pre-action state is rebuilt with the accepted Controller-01B reconstruction
(`tools/controller/controller01b.py`: `reconstruct`, `validate_pre`) under the truth firewall. Look 25
is then **replayed, not rendered**: the unchanged `ClassroomController01.observe` runs in a temporary
directory with its render call replaced by a copy of 01B's saved acquisition (`replay_renderer`), as
01B's accepted check mode does. The replay's in-memory post state is validated against the saved 01B
artifacts; the temporary directory is discarded; nothing is written to any accepted artifact.

The audit STOPS (no marker) unless all of these reproduce:
- pre: 210, 24 own looks, current gaze [2.6, 18.2], effective geometry 1,938,913;
- pre frontier raw/OPEN/map-resolved/boundary-resolved 350/52/28/270; 1 candidate;
- the selected candidate: gaze [7.6, 18.2], OPEN support 30, raw aligned support 43, map-resolved
  support 3, boundary-resolved support 10, equal to 01A's `terminal_probe.fsg6f_selected`;
- look 25: the replayed acquisition is 01B's (calibration gaze [7.6, 18.2]), target-valid 26,950,
  new surfels 0, post active map equal to 01B's saved `maps/fix_24.npz`;
- post: the previous window still 350/52/28/270 (the accepted 01B attribution
  `pre_window_after_look25`), the new window OPEN 0, and the post probe equal to 01B's recorded one
  (ACTIONABLE, Cyclopean [-17.6, 18.9]).

## Candidate support identity

The support mask is recomputed with the accepted formulas of `choose_next` (the same frontier arrays,
`alignment_cos_min`, the OPEN mask). It must reproduce the selected candidate **exactly**:
- the counts 30 / 43 / 3 / 10;
- `frontier_score = Σ strength·alignment` over the 30 elements equal to the in-process
  `choose_next` value (relative 1e-12);
- the candidate's `continuation` evidence re-computed from the mask (per-eye projected-frontier rays,
  object and support pixels) equal to the in-process decision's.

Each of the 43 raw aligned elements is persisted with: frontier index, 25 mm voxel key, `x_e`, `t_e`,
yaw/pitch of both, strength, alignment, pre-look state, OPEN-support membership, and its voxel's
composition (number of effective-geometry points; active-map surfel indices in the voxel; number of
memory points).

## Per-element trace through look 25 (for each of the 30 OPEN support elements; also the 43)

Using look 25's calibration and binocular state (the replayed accepted matcher output), for both `x_e`
and `t_e`:
1. inside the left rectified core (the 256 × 256 observation raster used by the matcher and FSG6f),
   via the accepted `_project_rectified_core`; also inside the raw left tangent image (640 × 640) via
   the accepted `fsg_geometry.project_h`;
2. the same for the right eye;
3. **binocular support**: the accepted `_target_patch_eye_evidence` observable in both eyes (inside the
   core and the 5 px patch has supported pixels), with the per-eye object fractions;
4. **valid target-210 depth evidence**: the number of look-25 pixels in the 5 px left-core patch around
   the projection that are matcher-`valid` with instance 210; also the 3-D distance and range
   difference between the element and the measured point at its projected pixel;
5. **12 mm association**: whether ≥ 1 of the 26,950 look-25 target-valid measurements of 210 lies
   strictly within 12 mm (`public.FUSION["association_radius_m"]`) of the point;
6. how many do;
7. whether the active-map surfels in the element's voxel changed in the replayed fusion (support count,
   provenance bit of `fix_24`), and how many look-25 measurements fused into them;
8. **same-window post classification**: re-extract the frontier from the post-look effective geometry
   with the **original pre-look gaze [2.6, 18.2] and calibration**, classify it with the post-look
   history (25 own looks), and match the element by its 25 mm voxel key: OPEN / MAP_RESOLVED /
   BOUNDARY_RESOLVED / no longer frontier. Also the **fixed-obligation** classification: the exact
   pre-look `x_e`, `t_e` classified with the post-look geometry and history;
9. if still OPEN, the condition that kept it OPEN: the nearest post-look effective-geometry distance to
   `t_e` (≥ 12 mm), and for look 25 whether `t_e` was outside a core, in an unsupported patch, or
   binocularly observable with `max(f_L, f_R) ≥ 0.15`; also how many of the 25 own looks tested it
   binocularly.

Only controller-time data are used: the source run's saved patches, acquisitions (calibration and the
oracle observation consumed by the accepted matcher) and maps; the 01A audit; the 01B record,
acquisition, patch and map.

## Reported decomposition (no policy conclusion)

Declared before the audit runs:
- **measured by look 25** := ≥ 1 look-25 target-valid measurement of 210 strictly within 12 mm of the
  support element `x_e`;
- **remains OPEN** := the same-window post classification is OPEN; otherwise **resolved**, broken down
  into MAP_RESOLVED / BOUNDARY_RESOLVED / no longer frontier.

The core cross-tab (over the 30 OPEN support elements):

    measured + remains OPEN | measured + resolved | not measured + remains OPEN | not measured + resolved

plus the same cross-tab with "measured" taken at the look-ahead target `t_e`, and the projection and
binocular-support counts. The possible readings (A: the support was never sampled, an
action-targeting/gaze-correspondence observation; B: it was sampled with valid target depth and remains
OPEN, a frontier-resolution/classification observation; C: mixed) are reported as counts. No majority
threshold is used and no policy conclusion is drawn.

## `predicted_new_angular_area_deg2` (code meaning only)

The report states exactly what `_new_box_area` computes for the candidate (its inputs: the candidate
gaze, half the nominal core FOV, and the 1 %/99 % yaw and pitch quantiles of the map passed to FSG6f),
what the code uses it for (the first candidate sort key), and how it relates to look 25's evidence:
the fraction of look 25's target-valid points that fall outside the pre-look quantile box, and the box
before and after look 25. The score is not redesigned.

## Visual (Policy 1, Level A)

`visuals/controller-01c/frontier-action-correspondence.png` (with a sidecar JSON of every annotated
number), four panels answering "Did the action actually service the frontier that requested it?":
1. PRE-ACTION FRONTIER (DERIVED): frontier states in the pre window, the 30 OPEN support elements
   highlighted with their look-ahead arrows, the current and proposed gazes;
2. LOOK-25 BINOCULAR OBSERVATION (CONTROLLER-TIME images, DERIVED projections): the left/right cores
   with 210's valid pixels and the projections of the same elements, coded by
   outside / observable / valid target depth;
3. 3-D CORRESPONDENCE (CONTROLLER-TIME + DERIVED): the support elements and look-25 target
   measurements, marking which elements received 12 mm associated measurements;
4. SAME-WINDOW POST CLASSIFICATION (DERIVED): the same elements after look 25, coded
   OPEN / MAP_RESOLVED / BOUNDARY_RESOLVED / no longer frontier, with the cross-tab.

No evaluation or reference truth.

## Truth firewall

`fov3d.control.integrated.TruthFirewall` with `controller01.is_evaluation_truth` is active in every
mode; `evaluation.json` and `bootstrap/evaluation_only/*` are forbidden. The audit records the opened
source files and the violations (required: none).

## Checks (`controller01c.py check`, fail-capable)

The check mode recomputes the audit and compares it with the saved `audit.json` and the visual sidecar.
It must catch:
1. a wrong source run (accepted hashes of the Controller-01 run; 01A outcome; 01B record/marker);
2. a wrong pre-action candidate (the selected-candidate fields vs 01A and 01B);
3. a wrong selected gaze;
4. a wrong set/count of the 30 OPEN support elements;
5. a permuted or mismatched support identity (score, continuation, persisted identity);
6. a wrong look-25 acquisition (01B's `fix_24`, its calibration gaze, patch hash, 26,950);
7. projection with the wrong calibration/gaze (known answer: look 25's own valid measurements must
   reproject onto their own left-core pixels, and onto the same rectified row in the right core);
8. association not using the accepted 12 mm rule (the recorded radius; a synthetic known-answer control
   at 11.9 / 12.1 mm; agreement with the accepted `_target_mapped_mask`);
9. another object's measurements counted as target-210 evidence (the evidence set is exactly the
   26,950 instance-210 valid points of the saved patch);
10. the same-window classification evaluated in the new post-look window (the window gaze must be the
    pre-look gaze and its counts must equal 350/52/28/270);
11. an evaluation-truth access (firewall);
12. visual or summary counts inconsistent with the per-element records.

Fail-capability is shown with temporary corruptions of throwaway copies of the audit output and code
mutants in throwaway repository copies. The source previews are never modified; the per-file sha256
manifests of the three source trees are compared before and after.

## Cost and gates

| command | cost class |
|---|---|
| `controller01c.py audit` (01B reconstruction: 141 re-matches, 24 fusion replays; one look-25 replay; no render) | batch (ESTIMATED 2–3 min) |
| `controller01c.py check` | batch |
| `controller01c.py visual` | batch |
| the layout, Controller-01, Core-14, Classroom and facade checkers; `verify_baseline`; `git diff --check` | interactive |

## Permitted fixes and stop conditions

Permitted: bugs in the new tool, its checks and visual, and the narrow layout declaration (the layout
checker declares this contract as required, and the report and the tool as allowed).

Stop if any reproduction gate fails, or if answering the question would need a change to accepted code,
thresholds, rules, the matcher, fusion, the truth scope, or a new observation. The source previews are
never modified. The Cyclopean proposal [-17.6, 18.9] is not executed.
