# North Star-1b — Recentered Local-Controller Handoff — One Action — contract

**Status: CONTRACT (committed before any NS1b implementation commit, before any NS1b controller probe and before any
NS1b render).** Completion marker (written only by the report): `NORTH_STAR1B_RECENTERED_CONTROLLER_HANDOFF_COMPLETE`.
No ACCEPTED marker is written by Claude Code.

Decision context (recorded on `main` at `889373d`, "North Star after NS1a"): NS1a is accepted; the frozen NS1a seed set
(13 initialized persistent entities, 302,936 surfels) is the North-Star seed handoff. NS1b uses a TEMPORARY POLICY
COORDINATE CHART. It is NOT physical head motion. The physical head remains fixed. Persistent scene geometry remains
authoritative in canonical H0. No controller threshold or FSG6f numerical rule is changed.

## 1. One causal question

> Can one persistent entity seed produced by the global 360° RGB bootstrap be handed to the accepted local FSG6f ->
> Cyclopean / Controller-02 control semantics through a temporary recentered POLICY COORDINATE CHART, such that the
> controller selects a valid new world fixation and exactly one PERFECT local measurement is fused back into the
> canonical H0 map?

The chain, and nothing beyond it:

    frozen NS1a seed set                     (accepted; read, never recomputed)
      -> one deterministic target            (rule of section 5, frozen here)
      -> policy chart C                      (section 6: centred on the target's initialization gaze)
      -> frame adapter                       (section 7: chart for policy geometry, H0 for physical sensing)
      -> covariance established              (section 8: identity, rigid rotation, projection, gate)
      -> controller context                  (section 9: the frozen NS1a map + the saved initialization look)
      -> ONE read-only pre-action probe      (section 10: FSG6f -> Cyclopean; adapted Controller-02 gate)
      -> at most ONE fixed-head observation  (sections 11-12: 4096 spp at the mapped H0 gaze)
      -> PERFECT correspondence -> spherical geometry -> local oracle id   (section 13, accepted AB1b / NS1a path)
      -> ONE H0 fusion into the target map   (section 14: 12 mm / 12 mm)
      -> ONE read-only post-action probe     (section 15; never executed)

STOP THERE. NS1b is a coordinate / controller-handoff experiment. It is NOT the full Classroom controller, a 13-object
loop, a scene-level STOP experiment, a new bootstrap, a stereo experiment, a head-motion experiment or a
controller-policy redesign. Exactly ONE target entity; at most ONE new physical fixation.

## 2. Provenance and branch

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (the legacy `fov-3d-vision` is never used) |
| base (accepted `main`: NS1a accepted + post-NS1a roadmap) | `889373d9c174c1c63ebc8d2f79847dbec281f2e8` |
| NS1a acceptance | `37c7e026f2ab514be392cd845d390fab2a2d86fc` (`NORTH_STAR1A_PERFECT_BOOTSTRAP_ROUND_ACCEPTED`) |
| branch | `north-star/ns1b-recentered-controller-handoff`, from the base, in an isolated worktree |
| run (`RUN`, machine evidence) | `/home/lvelho/rd/f3d-vision/previews/north-star/ns1b-recentered-controller-handoff/` |
| visuals (`VIS`, persistent) | `/home/lvelho/rd/f3d-vision/visuals/north-star/ns1b-recentered-controller-handoff/` |

The implementation commit writes this contract's commit SHA into `ns1b_spec.CONTRACT_COMMIT` and the checker's literal;
the checker requires this file to be unchanged from that commit to the checked tree.

## 3. Pre-contract development (disclosed)

Before this commit only accepted code, reports and records were read, and one calibration-only computation was made
(no scene data, no controller, no render):

- Read: the NS1a seed-set document (`seeds/seed-set.json`) and gaze list, to design the handoff; the accepted
  Controller-01 run's `actions.json` and object 112's `result.json`, and the accepted Controller-02 `final-residue.json`,
  to choose the covariance fixtures of section 8.
- Calibration-only (accepted `make_calibration` with the AB1a head pose, `baseline_projected`; accepted
  `fsg_stereo.rectification`), at the frozen rank-6 gaze (−156.25°, +28.75°): the chart of section 6 has
  ‖b_⊥‖ = 0.9356 (b·g = −0.3531), orthonormality error 2.2e-16, det +1; the seed maps to local (−1.6e-15°, 0°); the
  physical baseline expressed in C is (0.9356, 0, 0.3531); local ↔ H0 gaze round trips are exact to 1e-12°; the
  accepted planar rectified core used by the Classroom matcher's observation state is centred 1.49° from the gaze
  (14.26° at rank 1, the known AB1a near-baseline pathology); the left `baseline_projected` camera's image +X is 0.81°
  from x_C and its image up coincides with y_C. Because the rank-6 gaze looks backward (H0 d_z = +0.80), y_C points
  toward world-down: the chart (like the physical `baseline_projected` camera) is rolled about 180° from world-up.
  This follows from the mandated +X construction and is recorded, not acted on.

No NS1a entity was probed, no controller ran on NS1a data, no target selection was executed, and nothing was rendered.

## 4. The fixed physical head (load-bearing)

The physical binocular head DOES NOT MOVE. Canonical H0: +X right, +Y up, −Z forward, metres. All persistent geometry
stays in H0. The head pose is the accepted AB1a calibration's (`9960c86e…`; the same EYE pose as NS1a). The eye centres
are exactly (∓0.0315, 0, 0) m in H0 for every physical calibration NS1b uses (the rank-6 initialization look, the
predicted look of the gate, the planned and the executed look). Chart C is a POLICY COORDINATE CHART ONLY; it is never
called head recentering, physical head rotation or a changed baseline orientation. No calibration with eye centres reset
to ±IPD/2 on the axes of C is ever constructed for physical use ("fake local baseline").

## 5. Target selection — deterministic, before any probe (frozen rule)

Inputs, and nothing else: the frozen NS1a seed set (`seeds/seed-set.json`, verified under the NS1a seed freeze
`4ee36a1a…`), the frozen gaze provenance (`source/nb1c-gaze-list.json`) and the accepted sensor geometry (H0 baseline
b̂ = +X; `fsg_geometry.gaze_direction`). No object name, catalog, Controller-01 result, controller probe, future
visibility or post-selection render.

Selection set: `initialized == true` AND `contributing_patches == 1` (the single-patch restriction keeps the coordinate
bridge separate from the known multi-part oracle-id problem). For each candidate, at its INITIALIZATION gaze:

    g = gaze_direction(yaw, pitch) of the gaze with rank = initialized_at_rank      (unit, H0)
    L = sqrt(1 − (b̂ · g)²)

Order: (1) maximum L; (2) if tied, maximum `final_surfels`; (3) if tied, lowest `temporary_entity_id`. Ties in L are
exact equality of the float64 values computed by this rule (candidates sharing an initialization gaze share L exactly).

Expected (from the mandate): entity 172, initialized at frozen gaze rank 6. The `select` stage derives the result from
the rule and only then compares it with this expectation. A different result is a STOP with the discrepancy reported;
entity 172 is never forced.

## 6. Policy chart C (frozen construction)

    g0 = unit H0 direction of the target's initialization gaze;   b = (1, 0, 0)
    x_C = normalize(b − (b·g0) g0);   z_C = −g0;   y_C = normalize(z_C × x_C)
    R_HC = column_stack(x_C, y_C, z_C)            (maps C coordinates into H0)
    rows:  p_C = p_H0 @ R_HC;   p_H0 = p_C @ R_HC.T

HARD STOP if ‖b − (b·g0) g0‖ < 1e-6 (singular); no other axis is invented. Required (section 16): R_HC orthonormal
(≤ 1e-12), det +1 (≤ 1e-12), g0 → local yaw = pitch = 0 (≤ 1e-9°), H0 → C → H0 point and direction round trips
(≤ 1e-12 m / rad), distances unchanged (≤ 1e-12 m). The current local gaze is then set to exactly (0.0, 0.0) and the
measured residual recorded.

Inside C the accepted FSG6f policy coordinates are retained exactly: yaw −25…+25°, pitch −20…+20°, 5° component step,
and every accepted FSG6f constant (edge band fraction 0.04, edge object fraction 0.15, voxel 0.025 m, neighbour radius
0.065 m, minimum neighbours 6, tangent asymmetry 0.18, look-ahead 0.12 m, current-view margin 1.0°, minimum candidate
frontier support 8, alignment cosine 0.50, map-extent quantile 0.01, strict OPEN-majority consensus), the 12-mm map
resolution, the boundary semantics, the Cyclopean 0.1° grid and the Controller-02 v1 gate. Nothing is widened or tuned.
The point of NS1b is: move the coordinate chart, not the policy.

## 7. The NORTH-STAR FRAME ADAPTER (`ns1b_chart.PolicyChartAdapter`)

The accepted FSG6f / Cyclopean / Controller-02 code assumes its policy coordinates coincide with the physical head
frame. NS1b keeps two domains:

- POLICY GEOMETRY DOMAIN = chart C: angular coordinates, local yaw / pitch, the ±25 / ±20 domain, 5° candidates,
  frontier angular ranking, the Cyclopean chart, the visited gazes, the map / frontier geometry handed to the policy.
- PHYSICAL SENSOR DOMAIN = canonical H0: the eye centres, every calibration, camera projections, rectification /
  support geometry, binocular observability, the completed observation history and the new Blender acquisition.

The adapter is a context manager active only around accepted policy calls. It runs the accepted functions UNCHANGED on
chart-C inputs and substitutes exactly three physical-boundary functions, each by the composition of the accepted
function with the chart transform (in every loaded module object compiled from the named file; restored on exit;
nesting refused; the substitution record is saved):

| id | accepted function (file) | substitution |
|---|---|---|
| P1 | `_project_rectified_core(calibration, xyz, side)` (`tools/fsg6f_frontier.py`) | `accepted(calibration, xyz_C @ R_HC.T, side)`: a C point is transformed to H0 and projected with the REAL H0 calibration |
| P2 | `_rectified_core_directions_h(calibration, side)` (`tools/classroom_oracle1_epistemic.py`) | `accepted(calibration, side) @ R_HC`: the real H0 directions of the real rectified core pixels, expressed in C for the Cyclopean chart |
| P3 | `predicted_calibration(profile, gaze, head_R_wh, head_origin_w)` (`fov3d/experiments/classroom_oracle/controller02.py`) | the local proposed gaze is mapped to the H0 world gaze (section 11) and the REAL fixed-head sensor model is constructed there |

P3's sensor model is a declared parameter. In NS1b it is the North-Star observation sensor that will actually execute
the look (`ns1a_core.planned_calibration`: full profile, IPD 0.063 m, vergence 2.10 m, AB1a head pose,
`baseline_projected`), because the accepted gate predicts "the calibration of a proposed look from the known sensor
model (the renderer's construction)". For the identity reproduction of the accepted gate (section 8) it is the accepted
`predicted_calibration` itself (Controller-01 renderer construction). `make_calibration` is never called with a chart-C
gaze as though C were the physical head frame.

Everything else is accepted code on chart inputs. Purely Euclidean operations (the 12-mm map resolution
`_target_mapped_mask`, the 65-mm neighbour query, the 0.12-m look-ahead, the serviceable-support 12-mm test) are
exact radius queries and frame-invariant; the checker verifies it. The accepted FSG6a 25-mm voxel grid is axis-aligned
in the frame the policy runs in (C here, as H was for Controller-01); it is part of the accepted policy computed in the
policy chart, not a Euclidean-invariant operation, and is not reported as one. Persistent fusion is never done in C.

## 8. Coordinate covariance — established before the adapter touches NS1a data

Run by the `covariance` stage (and re-verified by the checker); any failure is Outcome 4 (STOP, no render).

**8a. Identity-chart reproduction (R_HC = I).** The adapter must reproduce the accepted policy exactly — frontier counts
and states, candidate list and order, consensus rejections, selected gaze, continuation evidence, stop / no_frontier,
the Cyclopean decision when reached, the gate verdict — exact where discrete, ≤ 1e-9 where floating point is
unavoidable (P3's gaze round trip through `atan2`). Fixtures:

- K1 (analytic, the accepted FSG6f / Cyclopean self-test fixtures): the four FSG6f `choose_next` known answers
  ([5, 5], [−5, −5], [5, 5] eye-swap-invariant, stop at the inset boundary), the down-right regression, the
  frontier-state unit controls and the Cyclopean exterior-bay fixation; plus the accepted gate function on the same
  analytic state (adapter vs direct, all fields).
- K2 (accepted Controller-01 replay state): object 112 after global step 18 (revision [1, 26285]): FSG6f `continue`
  to [9.0, 10.75]; the full saved `fsg6f_decision` must be reproduced.
- K3 (accepted Controller-01 replay state): object 112 after global step 20 (revision [3, 32438]): FSG6f `no_frontier`
  -> Cyclopean `epistemic_fixation` to [20.6, 9.7]; both saved decisions reproduced; and after step 21
  (revision [4, 36183]): QUIET (saved summaries reproduced).
- K4 (the accepted Controller-02 gate verdict): object 210's terminal state (all 141 accepted actions replayed into
  memory; 24 own looks): the FSG6f proposal [7.6, 18.2] and the accepted final-residue verdict `final_probe_rejected`,
  `no_novel_serviceable_support`, support 30, in both predicted cores 0, previously interrogated 30, novel 0, with its
  per-element detail.

K2–K4 states are rebuilt from the accepted run's saved acquisitions and patches with the accepted matcher, memory and
surface-map code (own looks only for the policy context; all patches up to the probe step for measurement memory;
geometry = the accepted effective target geometry, as Controller-01 probed). The rebuilt revision must equal the
recorded one before comparison. No catalog, seeds file, object name, evaluation file or later audit artifact is opened.

**8b. Rigid-rotation covariance.** The exact symmetry group of the fixed binocular head is rotation about the physical
baseline axis +X: it keeps the eye centres on X, so a rigidly rotated configuration (scene, map, frontier, gaze, every
camera rotation R_hc → Q R_hc) is again a valid fixed-head configuration accepted by the unchanged `rectification`
(for `baseline_projected` cameras it equals `make_calibration` at the rotated gaze). For Q = R_x(β), β ∈ {+23°, −47°,
+131°}: the rotated fixture's chart is required to undo Q; the adapter's LOCAL decision must equal the unrotated
decision; mapped back to the rotated H0 world it must equal Q applied to the original proposal (≤ 1e-12). For the
analytic fixtures centred at (0, 0) the chart is the section-6 construction for the rotated seed (which must equal Q:
"the rotated seed becomes local forward"); for K2 / K3 it is R_HC = Q. A rotation that moves the eyes off +X changes
the physical binocular configuration relative to the scene; it has no exact known answer and is not claimed. The
chart-only parts (frontier extraction, map resolution, Cyclopean map support) are additionally tested under general
rotations Q (two fixed off-axis rotations) with R_HC = Q.

**8c. Projection invariance.** For physical points: the direct H0 projection into the real rectified core equals
C -> H0 -> the same projection (≤ 1e-9 px), for the rank-6 calibration and two predicted calibrations; the negative
control (a C point projected as if it were H0) must differ. P2 directions are compared the same way.

**8d. Controller-02 final-look semantics.** Identity: K1 and K4 above. Rotated chart: P3's calibration equals
`make_calibration` at the mapped WORLD gaze with the fixed head (≤ 1e-12) and differs from the fake local calibration
(`make_calibration` at the local gaze), which the checker refuses wherever it appears.

## 9. Initial controller context from the NS1a seed (no rerender)

Only the selected entity's frozen NS1a handoff data:

- NORTH-STAR METRIC MAP: the exact frozen H0 SurfaceMap of the target from `seeds/entity-maps.npz` (verified bitwise
  against the seed freeze). It stays authoritative in H0 and is given to the policy as `p_C = p_H0 @ R_HC` (all its
  surfels). Controller-01 probed the effective target geometry (map ∪ instance measurement memory); NS1b has no
  measurement memory beyond the seed map, and for a single-patch entity the NS1a measured points of the entity are
  exactly its map points.
- CONTROLLER OBSERVATION STATE: the saved NS1a observation at the initialization gaze (rank-6 `calibration.json`,
  `rgb-observation.npz` and the ORACLE AID `reference-observation.npz`, verified against the NS1a observation freeze),
  passed through the accepted Classroom perfect local matcher (`classroom_oracle1_matcher.compute`, the accepted
  Controller-01 controller-time oracle) only to obtain its instance masks, rectified support, binocular history entry and
  continuation / boundary evidence. Its planar point record is never used as geometry.

`LocalPolicyContext` (accepted class): `target_id` = the selected temporary id; current gaze (0.0, 0.0); one completed
own look (the initialization gaze); `visited = [(0.0, 0.0)]`; `history = [object_policy.history_entry(rank-6 H0
calibration, matcher state, target)]`; `evidence` = `epistemic.make_evidence()` + `add_observation(...)` of that look
under the adapter (P2); `calibration` = the rank-6 H0 calibration; `state` = the matcher state. No catalog, name, future
visibility, global object ordering or Controller-01 bootstrap seed.

## 10. The read-only pre-action probe (exactly once)

Under the adapter: the accepted `controller01.probe_local_policy(ctx, map_C)` (FSG6f via the accepted target-label
adapter; if `no_frontier`, the accepted Cyclopean handoff), then the accepted `controller02.final_look_gate_v1` on the
resulting proposal with `gaze = (0, 0)`, the rank-6 calibration, state, history, visited, `profile = "full"` and the
fixed head pose (P3 builds the real predicted calibration). Recorded: FSG6f stop / continue; frontier raw / open /
map-resolved / boundary-resolved counts; candidates and consensus rejections; the selected local gaze; the source
(`fsg6f` or `cyclopean_epistemic`); the mapped H0 world gaze; its angular distance from the seed gaze; its physical
stereo leverage; the gate verdict, reason, serviceable support, novel serviceable support and predicted-core
observability. Recorded diagnostics (not decisions): the same accepted policy WITHOUT the chart on the seed (expected to
be refused: the seed lies behind the H0 forward hemisphere that the accepted code requires), and the decision recomputed
for the context rigidly rotated about the baseline by β ∈ {+37°, −61°} (must be identical in C; any difference is
Outcome 4).

## 11. Exactly one possible action; world-gaze mapping

- **CASE A — no proposal** (FSG6f `no_frontier` and Cyclopean `attention_complete`): the seed is locally QUIET. STOP
  NS1b (Outcome 2). No other entity, no rule change, no gaze.
- **Gate rejects the proposal** (including the accepted v1 rule that a Cyclopean proposal has no traceable final
  support): STOP NS1b (Outcome 3), reporting exactly why. No other target.
- **CASE B — one admissible proposal**: execute exactly that action, once.

Mapping: `d_C = gaze_direction(yaw_C, pitch_C)`; `d_H0 = d_C @ R_HC.T`; `yaw_H0 = atan2(d_x, −d_z)`;
`pitch_H0 = atan2(d_y, hypot(d_x, d_z))`. The H0 → C round trip must reproduce the local gaze (≤ 1e-9°). Both
descriptions are recorded; the planned calibration is `ns1a_core.planned_calibration(yaw_H0, pitch_H0, AB1a head)`.
No second proposal, no target switch, no scheduler loop, no second entity.

## 12. One new physical observation (Case B only)

One binocular pair at (yaw_H0, pitch_H0) with the SAME fixed head, exactly the North-Star observation standard of NS1a:
Classroom `classroom_eye.blend` (`dca66a32…`), static scene, 640 × 640 raw, 256 × 256 nominal core, 12° core, IPD 0.063
m, vergence 2.10 m, `baseline_projected`, OPTIX, 4096 spp, seeds L 2111 / R 2112, denoising OFF, adaptive OFF, BOX 1.0,
through the accepted `ab1a_render.acquire_pair` / `configure` and the NS1a render checks (EYE pose = AB1a head ≤ 1e-6;
calibration built in Blender byte-identical to the host-planned one; settings readback equal to the accepted AB1d2
4096-spp readback; 4096 in the EXR headers). Saved domains: `observation/acquisition/` (SENSORY: `calibration.json`,
`rgb-observation.npz`, `acquisition.json`) and `observation/oracle_aid/` (ORACLE AID: `raw_L.exr`, `raw_R.exr`,
`reference-observation.npz` with Position and Object Index). Blender necessarily assigns the Object Index pass indices;
the id -> name catalog it writes goes to `observation/evaluation_only/instance-catalog.json`, SEALED (never opened by
any NS1b stage), serialized exactly as the NS1a sealed document. Blender records its sha256, which must equal NS1a's
recorded catalog seal (`a0849b21…`): a byte identity proving the same id assignment without any host stage reading
names. No rerender; no second fixation. `preflight` (no render) runs first.

**Cost.** PROPOSED from NS1a (≈ 15–19 s per eye at 4096 spp): ≈ 35–40 s. A projected render time above 600 s is a STOP.

## 13. PERFECT correspondence -> spherical geometry -> local oracle segmentation aid (Case B only)

Exactly the accepted North-Star measurement service, as in NS1a sections 8–10, on the one new observation, each step its
own guarded stage with its own freeze: the accepted `ab1b_oracle.compute_oracle` (raw left nominal core, finite hit,
positive Object Index, exact projection into the full padded right raster, same-instance binocular visibility, continuous
`uv_R`; truth-stripped product `left_core_row`, `left_core_col`, `uv_L`, `uv_R`) -> freeze -> the accepted
`ab1b_geometry` spherical epipolar geometry in H0 under a guard reading only the calibration and the frozen product (no
cv2, `fsg_stereo` or `ab1b_oracle` loaded) -> freeze -> the local ORACLE SEGMENTATION AID (only member `instance_L`
read; `temporary_entity_id = instance_L[v_L, u_L]`). No SGBM, no natural correspondence, no rectification, no depth
interval, no Controller-01 planar geometry as measurement. (The Classroom matcher's role is the controller observation
state only, sections 9 and 15.)

## 14. Target patch and H0 fusion (Case B only)

From the frozen spherical measurement keep only `valid_epi` points whose local oracle id equals the target id:
`Patch("ns1b_action_01", xyz_h = P_epi (H0), rgb = raw left-core linear RGB at uv_L, instance_id)`. Fuse into the
target's NS1a map with the accepted `fov3d.reconstruction.surface_map.fuse`, association radius 0.012 m, hash cell
0.012 m, in canonical H0 only (the fusion entry point refuses any patch not declared H0); replay the same patch once:
the map must be unchanged (exact equality and the Controller-01 1e-10 test). The accepted precondition applies: fewer
than 100 target points -> `fuse` refuses and the evidence is retained, not fused (reported, not forced). Reported: map
size before; measured target points; matched existing surfels; new surfels; affected surfels; matched-distance median /
p95 / max; map size after. Overlap is NOT an acceptance threshold; `matched == 0` is reported as such.

## 15. The read-only post-action probe (Case B only; exactly once; never executed)

Update the context exactly as Controller-01's `observe` does: the accepted Classroom matcher on the new observation
(state only), `epistemic.add_observation` under the adapter, history append, `visited.append(local gaze)`, current
gaze / calibration / state; geometry = the updated H0 map (fused, or unchanged if not fused) in C. Then ONE probe and the
gate, recorded (actionable / quiet; proposal and source; frontier / epistemic summary; verdict). The proposal is NOT
executed. NS1b ends there.

## 16. Truth boundary and process

Controller-time oracle aids are exactly the concept-demo aids: PERFECT local correspondence (the AB1b service for the
measurement; the Classroom matcher for the controller observation state) and local Object Index identity. The
controller never sees Position beyond those services, future visibility, global Blender geometry, dense completion
truth, catalog names or full catalog ordering. The temporary target id is part of the accepted NS1a handoff. Every stage
runs under the accepted `nb1a_guard.OpenGuard` allowlist; the checker scans every guard record. No scene scheduler
(`run_control_loop`, `run_controller02`, `schedule*`), no target switch, no SCENE_CLOSED, no global quiescence claim, no
24-look watchdog, no second entity, no second render, no natural stereo, no SGBM, no head motion.

## 17. Outcome semantics (no arbitrary success threshold)

- **Outcome 1 — handoff + action succeeds:** an admissible controller action from chart C; C -> H0 coherent; one real
  fixed-head observation; PERFECT spherical geometry measured and passed to the accepted 12-mm fusion in canonical H0
  (whether the patch meets the 100-point precondition and how much overlaps is reported, not judged); the controller
  context valid after the action. Then NS1c may enable scene-level scheduling over the frozen NS1a seed set.
- **Outcome 2 — handoff succeeds, selected entity QUIET:** covariance and context correct, no proposal. Not a coordinate
  failure.
- **Outcome 3 — proposal rejected by the adapted Controller-02 gate:** reported exactly; no other target.
- **Outcome 4 — coordinate / adapter failure:** identity or rotation covariance, projection invariance, the chart / world
  gaze round trip or an accepted policy semantic fails. STOP; no render.

The report gives a reading; Luiz and Chat decide.

## 18. Synthetic / known-answer tests (`synthetic`, before any NS1a data is touched by the adapter)

(1) chart basis orthonormal, det +1; (2) centre gaze -> local (0, 0); (3) direction round trip H0 -> C -> H0;
(4) point round trip; (5) Euclidean distance invariant; (6) identity-chart FSG6f reproduces the accepted fixtures;
(7) rigid baseline-axis rotation: same local FSG6f result; (8) identity-chart Cyclopean; (9) rotated Cyclopean;
(10) physical projection: direct H0 = C -> H0; (11) a fake-local-baseline calibration is refused by the checker's
calibration test; (12) world / local gaze mapping on exact known directions; (13) a candidate's world calibration keeps
the fixed head and baseline; (14) identity-chart gate reproduces the accepted gate function; (15) rotated-chart gate
evaluates physical observability with the real H0 sensor, not a fake C sensor; (16) the selection rule is deterministic
and order-independent; (17) a name / catalog field or read during selection is refused; (18) H0 SurfaceMap fusion
reproduces the accepted 12-mm behaviour (matched / new, idempotent); (19) a local-frame fusion attempt is refused;
(20) a second physical action is refused by the process contract. Plus: the adapter restores every substituted function,
refuses nesting and patches every loaded module copy; the frame-invariance of the Euclidean queries; the chart
singularity STOP. Software tolerances are declared in `ns1b_spec`; no Classroom-derived tuning.

## 19. Checker (`tools/north_star/check_ns1b.py`) and corruption suite

Own literal pins and constants; every load-bearing rule must be able to fail. Check families: PROVENANCE (repo, base,
NS1a acceptance, contract first and unchanged, accepted controller / FSG6f / Controller-02 / AB1b / surface-map /
NS1a source pins); FROZEN HANDOFF (NS1a seed freeze, seed set, maps, rank-6 observation); TARGET SELECTION (recomputed
independently; derived, not hard-coded; no name / catalog); CHART (recomputed independently; centre, orthonormality,
det, round trips, no singularity, domain unchanged); POLICY CONSTANTS (unchanged and recorded as used); FRAME ADAPTER
(exactly P1–P3, restored, projection invariance on recorded points, no fake local calibration); COVARIANCE (8a–8d
re-verified; K4 recomputed once per checker process); FIXED HEAD (every physical calibration); INITIAL CONTEXT (exact
NS1a look reused, no rerender, matcher state and evidence recomputed, one own look); PRE-ACTION PROBE (exactly once,
recomputed, baseline-rotation invariance, truth-free guard); GATE (recomputed; P3 calibration = the real sensor at the
world gaze); WORLD GAZE (own formula, round trip, leverage, distance; equals planned and executed); ACTION (zero or one;
the exact proposed gaze; 4096 spp; fixed head; no rerender; catalog seal = NS1a); MEASUREMENT (own oracle and own
triangulation reproduce; identity after the geometry freeze; only `instance_L`); FUSION (H0 only; the patch is the
frozen P_epi of the target; 12 / 12; own nearest-surfel association reproduces matched / new; idempotent; target only);
POST-ACTION (at most one probe, recomputed; no second action); PROCESS (each canonical stage once, in order, one clean
pushed commit; no scheduler / target switch / global STOP / natural stereo / head motion); VISUALS (byte-identical
regeneration; frame labels; fixed-head statement; oracle badges).

`check_ns1b_corruptions.py` runs from a passing mirror after an unmodified-mirror null probe; each corruption names the
checks that must catch it; mutated outputs live only in the temporary mirror; the run and visuals are hashed before and
after. Families, at least: TARGET (multi-patch entity included; leverage altered; tie rule changed; object name used;
another id selected); CHART (one basis axis flipped; map centroid instead of the initialization gaze; wrong cross-product
order; non-orthogonal basis; H0 / C transpose error); PHYSICAL SENSOR (physical head rotated; local eye centres reset to
±X; IPD changed; head pose changed; local fake calibration used for observability); POLICY (±25 / ±20 changed; 5° step
changed; frontier threshold changed; consensus changed; 12-mm resolution changed; Cyclopean grid changed); PROJECTION
(C points projected directly with the H0 calibration; wrong C -> H0 transform; wrong world-gaze mapping); SOURCE
(initial seed re-rendered; seed map altered; catalog opened); ACTION (controller-selected gaze changed; a second gaze
executed; target switched); MEASUREMENT (SGBM used; planar metric geometry used; perfect uv_R rounded; Position exposed
to the spherical geometry); FUSION (fused in C coordinates; radius changed; hash cell changed; idempotence disabled);
VISUAL (local / H0 frame label omitted; head motion implied; oracle badge removed; a canonical pixel altered).
Corruptions that do not apply to the executed case (e.g. ACTION / MEASUREMENT / FUSION under Case A or 3) are
recorded NOT APPLICABLE with the reason, never counted as caught.

## 20. Visuals (Visual Language 1; deterministic; regenerated byte-identically by the checker)

`VIS/overview.png`: **A** the global NS1a seed set in H0 with the selected target highlighted (id, initialization gaze,
leverage, single-patch provenance; NS1a FROZEN INPUT · no object name used for selection); **B** policy recentering:
the seed in canonical H0 beside chart C (seed gaze -> local (0, 0), the ±25° / ±20° frozen domain, the physical baseline
expressed in C, PHYSICAL HEAD FIXED · POLICY CHART ONLY), the controller-selected local candidate and the same direction
in H0; **C** the first controller action (the seed observation beside the new one, local and H0 gazes, PERFECT
correspondence count, target points) or, without an action, the policy / gate stop reason; **D** the canonical-H0 target
map before / after, matched vs new surfels, the 12-mm fusion result and the post-action read-only state. Also
`chart-covariance.png` (identity fixture, baseline-rotated fixture, local decisions, mapped world decisions) and, if an
action executes, `first-controller-action-3d.png` (seed map, new measurement, fused map, the fixed head at the same H0
origin and baseline). Truth badges on every figure; non-color cues (glyphs, hatching, dashed outlines) as well as color;
frame labels on every geometric panel (POLICY CHART C vs CANONICAL H0); `visuals-manifest.json`.

## 21. Commands and order (each canonical stage once, from one clean pushed implementation commit)

    RUN=/home/lvelho/rd/f3d-vision/previews/north-star/ns1b-recentered-controller-handoff
    VIS=/home/lvelho/rd/f3d-vision/visuals/north-star/ns1b-recentered-controller-handoff
    .venv/bin/python tools/north_star/ns1b_run.py source                     --run $RUN
    .venv/bin/python tools/north_star/ns1b_run.py synthetic                  --run $RUN
    .venv/bin/python tools/north_star/ns1b_run.py select                     --run $RUN
    .venv/bin/python tools/north_star/ns1b_run.py chart                      --run $RUN
    .venv/bin/python tools/north_star/ns1b_run.py covariance                 --run $RUN   # batch
    .venv/bin/python tools/north_star/ns1b_run.py context                    --run $RUN
    .venv/bin/python tools/north_star/ns1b_run.py probe                      --run $RUN   # decides Case A / 3 / B
    # Case B only:
    .venv/bin/python tools/north_star/ns1b_run.py preflight                  --run $RUN   # Blender, NO render
    .venv/bin/python tools/north_star/ns1b_run.py acquire                    --run $RUN   # Blender, the one render
    .venv/bin/python tools/north_star/ns1b_run.py freeze-observation         --run $RUN
    .venv/bin/python tools/north_star/ns1b_run.py perfect-correspondence     --run $RUN
    .venv/bin/python tools/north_star/ns1b_run.py freeze-correspondence      --run $RUN
    .venv/bin/python tools/north_star/ns1b_run.py spherical-geometry         --run $RUN
    .venv/bin/python tools/north_star/ns1b_run.py freeze-geometry            --run $RUN
    .venv/bin/python tools/north_star/ns1b_run.py local-oracle-segmentation  --run $RUN
    .venv/bin/python tools/north_star/ns1b_run.py fuse                       --run $RUN
    .venv/bin/python tools/north_star/ns1b_run.py post-probe                 --run $RUN
    # always:
    .venv/bin/python tools/north_star/ns1b_run.py visualize                  --run $RUN --visuals $VIS
    .venv/bin/python tools/north_star/check_ns1b.py --run $RUN --visuals $VIS --corruptions --write-summary

Under Case A or Case 3 the Case-B stages refuse (`not applicable`) and are recorded as not run. Cost classes (PROPOSED):
`covariance` batch (the K4 replay, a few minutes); `acquire` interactive-to-batch (≈ 40 s); the checker with corruptions
batch; every other stage interactive. No overnight task, no parameter sweep, no second target.

## 22. Permitted fix scope

- **Before the canonical run:** implementation defects in the NS1b tools, without changing sections 4–15 or a declared
  tolerance. Development uses analytic fixtures, the accepted Controller-01 / 02 replay states, calibration-only data, a
  scratch development run that rehearses `select` … `probe` on a NON-candidate NS1a entity (entity 110: three
  contributing patches, outside the selection set; its own rank-2 chart), a no-render Classroom preflight probe and a
  low-spp synthetic factory-startup render (never a Classroom render). The selected target is never probed in
  development.
- **After the canonical acquisition:** (a) a later stage that fails with an implementation defect BEFORE writing any
  output may be repaired minimally and then run for its first and only time, if sections 4–15 are unchanged (recorded as
  an incident); (b) presentation-only figure fixes; (c) a checker or corruption-suite defect that false-alarms on correct
  data, only if the fix does not weaken the check (recorded).
- Anything else — a re-render, a second probe, a different target, a change to the chart, the adapter, a policy
  constant, the gate, the oracle, the geometry, the identity rule or the fusion parameters — is a STOP for Luiz and
  Chat.

## 23. Stop conditions

STOP and report if: a source / NS1a pin fails; `synthetic` or `covariance` fails (Outcome 4); the selection differs from
entity 172; the chart is singular; the baseline-rotation invariance of the probe fails; `preflight` fails; the projected
render time exceeds 600 s; a guard records a violation in a canonical stage; a canonical stage would run twice; a
canonical check fails for a reason other than a checker defect.

## 24. Report and stop

`docs/north-star/ns1b-recentered-controller-handoff-report.md`, status REVIEW PENDING, marker
`NORTH_STAR1B_RECENTERED_CONTROLLER_HANDOFF_COMPLETE`, no ACCEPTED marker. It records: provenance; NS1a acceptance /
source pins; the deterministic selection calculation; the selected target and initialization gaze; R_HC; proof the
physical head stayed fixed; the identity / rotation covariance tests; the imported seed context; the pre-action FSG6f /
Cyclopean decision; the adapted Controller-02 gate result; the local proposed gaze; the mapped H0 gaze; whether an action
executed; if so the render details, perfect correspondence, spherical geometry, target points, the H0 fusion (matched /
new, before / after); the post-action read-only probe; the Outcome reading; checks; corruptions; visuals and hashes;
incidents; what is and is NOT established; and the unresolved decision for Luiz / Chat: READY TO ENABLE THE
MULTI-ENTITY NORTH-STAR CONTROLLER LOOP? Then STOP: no acceptance, no merge, no second entity, no second action, no
scheduler, no SCENE_CLOSED, no FSG6f or Controller-02 change, no stereo, no head motion.

## 25. What NS1b may and may not establish

May establish: whether one NS1a seed, through a temporary recentered policy chart and a thin frame adapter, is handed to
the unchanged accepted local controller semantics, whether that controller then proposes an admissible fixation, and
what one PERFECT fixed-head measurement at the mapped world gaze contributes to the canonical H0 map.

May NOT establish: that the other 12 seeds are serviceable; scene-level scheduling, closure or quiescence; natural
correspondence or natural identity; that the chart choice is optimal; anything about head motion, real cameras or other
scenes.
