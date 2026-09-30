# Visual Language 1 + full canonical Classroom demo — contract

**Status: PROPOSED** (committed before implementation). Branch
`methodology/visual-language-1-canonical-demo`, from `main` @ `1e0584b` (Controller-02 accepted).

This is a methodological / visualization milestone. It changes no scientific behavior: no `fov3d/` file,
no controller, no policy, threshold, matcher, fusion or renderer changes, no controller rerun, and no new
sensory observation.

## 1. Proof question

> Can a technically literate viewer understand what the system sees, knows, chooses, changes, defers
> and finally leaves unresolved, without reading the implementation?

The package is **REVIEW PENDING** until Luiz and Chat inspect it. Machine checks are necessary, not
sufficient. When generation and checks are complete, the report records
`VISUAL_LANGUAGE_1_CANONICAL_DEMO_COMPLETE`. No ACCEPTED marker is written on this branch.

## 2. Sources

Controller-time sources (the only inputs of the controller-time path):

| source | identity |
|---|---|
| `/home/lvelho/rd/f3d-vision/previews/controller-01-full` | accepted Controller-01 run; `manifest.json` `d293a98f…`, `actions.json` `12cdbe4d…`; 1,678 files |
| `/home/lvelho/rd/f3d-vision/previews/controller-02-classroom-replay` | accepted Controller-02 replay; `result.json` `a6dc4879…` with marker `CONTROLLER02_CLASSROOM_SCENE_CLOSED`; `actions.json` `7fb86aba…`, `events.json` `fae7e648…`, `final-residue.json` `a315714f…`, `manifest.json` `ad49e835…` |

The accepted persistent visuals (`visuals/controller-01/`, `visuals/controller-02/`) are consulted by the
humans designing the language; the generator regenerates from causal source data and does not reuse their
rasters. The Controller-01A/01B/01C outputs are not inputs.

## 3. Truth boundary

The demo states near its beginning: **CONTROLLED PROOF OF CONCEPT**, and the current oracle boundary:
- the Blender scene graph supplies the initial object catalog and one seed per localized object;
- the current-pair Blender Position / Object Index passes support the accepted controlled stereo /
  instance measurement path;
- dense evaluation truth does **not** participate in controller decisions.

Provenance classes (truth badges): `CONTROLLER-TIME`, `DERIVED`, `ORACLE INPUT`,
`REFERENCE / EVALUATION`. `ORACLE INPUT` may coexist with `CONTROLLER-TIME` (the current-pair oracle
measurement is part of the controller-time experiment).

Three separated paths:
1. **Controller-time extraction** (`extract`): reads only the two controller-time sources and writes the
   derived cache. It runs under `fov3d.control.integrated.TruthFirewall` with a predicate that refuses
   evaluation truth (`controller01.is_evaluation_truth`: `evaluation.json`, `bootstrap/evaluation_only/*`),
   every reference path of this step, and the 01A/01B/01C preview directories. Every opened file is
   recorded.
2. **Controller-time rendering** (`render`): frames, events, overview, legend, panoramas, point clouds and
   video stages from the cache and the controller-time sources, under the same firewall.
3. **Reference path** (optional, separate command and process): may read reference/evaluation assets and
   writes only `REFERENCE / EVALUATION`-tagged products (`reference/`, the intro/outro reference panels).
   It never writes cache data consumed by paths 1–2, and never produces controller-time state, action,
   measurement, support or annotation.

At most **one** static Blender reference view is rendered, because no wide RGB scene reference exists
(searched: the controller runs, `scenes/classroom`, the OLD-PREVIEWS archive). It is a head-centred
wide perspective view from the fixed head pose in `bootstrap/seeds.json`, with Combined, Position and
Object Index passes, resampled on the host into the controller's head-centred yaw/pitch chart. It is not
an observation, is not fed to the controller, and is not part of any measurement. Its alignment is
checked against the existing evaluation-only dense samples (`reachable_samples.npz`, instance agreement);
if the check fails, the reference products are omitted and the reason recorded (no tuning).
`reference/depth-reference.png` and `reference/instance-reference.png` come from that same render.

## 4. Derivations (all through accepted `fov3d.*` functions; no controller rerun)

For every global step t (0..140), in action order, the extraction replays the causal state from saved
per-step artifacts and records compact per-step products. Every quantity with a controller-time record
is compared exactly with that record; any mismatch **stops** the extraction.

| product | accepted functions / source | exact comparison |
|---|---|---|
| measurement memory | `InstanceMeasurementMemory.append_patch` on the saved patch | `measurement_memory_additions` per step |
| head evidence | `fov3d.epistemic.head_memory.add_head_patch` | `head_evidence` per step |
| observation footprint and own-look context | `matcher.compute` on the saved current-pair observation; `epistemic.add_observation`; `object_policy.history_entry` | matcher `valid` / `instance_id` equal the saved patch |
| target-relative epistemic view E_t(i) after step t | `integrated.support_layers` + `integrated.target_epistemic_view` (+ `view_summary`) | equal (`class_code`, `region_code`) to every saved controller-time view: the event views and the 25 final views |
| FSG6f frontier states after step t | `frontier.extract_frontier` + `frontier.classify_frontier_state` | raw / OPEN / map / boundary counts of the probe record after step t |
| Cyclopean eligible cells (when consulted) | the sealed Cyclopean helpers, as in the accepted Controller-01 visual | `eligible_cells` of the probe record |
| new surfels | saved map after t, entries `[before:]` (fusion appends new surfels) | `new_surfels` |
| repeated target measurements | target-valid patch points that did not become new surfels | `nonnew_target_points` |
| cross-target measurements | memory additions of other instances | `measurement_memory_additions` |
| next local proposal / QUIET | the controller-time probe record after step t (not recomputed) | — |
| service states, dispositions, events, final gate | Controller-02 `actions.json`, `events.json`, `final-residue.json`, `result.json` | Controller-02 actions equal Controller-01 actions (target, gaze, source) |

The event numbers are recomputed and compared with the records:
- **109:** QUIET since step 4; step 7 look at 110; 4 cross-target points; Cyclopean eligible 0 → 28;
  ACTIONABLE; serviced at step 134.
- **178:** QUIET since step 67; 36,748 cross-target points since quiet; eligible 0 → 189; ACTIONABLE;
  serviced at step 136.
- **210:** DEFERRED at step 101, local ACTIONABLE, ordinary look count 24.
- **Final gate:** FSG6f [7.6, 18.2]; 30 OPEN support elements; in both predicted cores 0; previously
  interrogated 30; `novel_service_count` 0; REJECT `no_novel_serviceable_support`; no render, no OBSERVE.
- **Closure:** `SCENE_CLOSED`; quiet 24; residual [210 `wall.008`, ACTIONABLE, `FINALIZED:
  final_probe_rejected`]; unlocated 209; final residue observations 0.

Every scientific number shown is either a controller-time record or recomputed and equal to one.

## 5. Visual Language 1

A single tracked style definition, `tools/visual_language/style.py`, declares every semantic role with a
color **and** a non-color cue (shape, outline, hatch, dash or glyph). Required roles:
- **truth / provenance:** CONTROLLER-TIME, DERIVED, REFERENCE / EVALUATION, ORACLE INPUT;
- **attention:** current object, current fixation, proposed fixation, attention switch;
- **epistemic:** target support, other surface, unknown, ambiguous boundary, unresolved support;
- **measurement / geometry:** persistent geometry, new measurement, new surfel, repeated measurement,
  cross-target measurement;
- **service state:** QUIET, ACTIONABLE, DEFERRED, FINALIZED RESIDUAL, UNLOCATED (plus SEEDABLE, needed
  before an object's first look);
- **sensor:** actual depth-measuring core, predicted depth-measuring core, binocular support.

The legend is drawn from `style.py`. The language preserves:
- measurement ≠ new geometry;
- visible ≠ depth measured;
- actionable ≠ worth a final observation;
- deferred ≠ quiet;
- residual ≠ failure;
- `SCENE_CLOSED` ≠ global quiescence.

Presentation rules: high contrast; large labels (body text ≥ 22 px at 1440p); little text per frame; text
over busy backgrounds gets an outline or a plate. The frames must stay readable at 1080p and projected.

`docs/methodology/visual-language-1.md` (status REVIEW PENDING) documents what the generated demo
actually uses: exact colors, glyphs, line and hatch styles, badges, temporal semantics, the standard
head-relative 3-D camera, the standard angular chart, fixation/proposal marks, the new-vs-repeated and
residual conventions, accessibility rules, and examples.

## 6. The cockpit and temporal semantics

A stable four-panel layout, 2560 × 1440:
1. **SCENE / ATTENTION — BEFORE action t:** cumulative measurement memory in the fixed head-centred
   yaw/pitch chart (stable view, no camera motion); current target; current fixation (action t−1);
   proposed fixation (action t) and the attention move / switch; the target's service state and
   disposition.
2. **THE EYES — OBSERVATION by action t:** left and right rectified core images; target pixels;
   target-valid and all valid stereo measurements; target pixels without valid depth; the wide raw
   tangent view with the depth-measuring core outlined (visible ≠ depth measured); action source.
3. **CYCLOPEAN / EPISTEMIC — AFTER action t:** E_t(i) in the head-centred chart (target support, other
   surface, unknown, ambiguous boundary), unresolved support (FSG6f OPEN elements or Cyclopean eligible
   cells), current fixation, next local proposal or QUIET.
4. **PERSISTENT 3-D MEMORY — AFTER action t:** active fused maps from a fixed head-relative oblique 3-D
   camera; persistent geometry before t, new surfels, repeated target measurements and cross-target
   measurements of action t, with a zoomed inset instead of camera jumps.

Panels are labelled BEFORE / OBSERVATION / AFTER. A persistent timeline shows the global step, the
current object, the action source (seed / FSG6f / Cyclopean), quiet transitions, natural reactivations,
attention switches, the 210 deferral, NORMAL → RESIDUE and `SCENE_CLOSED`. A roster shows the 25
localized objects' service states.

## 7. Coverage, pacing and special events

Every accepted ordinary action, global steps 0..140, is one logical frame (141/141; no sampling).
Proposed pacing at 30 fps: 23 frames (≈ 0.77 s) per ordinary action and 36 frames (1.2 s) for a switch
or an object's first look; the special events slow down with staged sub-frames:
- **K1 bootstrap** (ORACLE INPUT): catalog 234, 25 localized / initialized, 209 unlocated, one seed per
  localized object, the seed directions in the chart;
- **K2 reactivation 109**, with a required magnified inset for its four points;
- **K3 deferral of 210** at step 101 (DEFERRED ≠ QUIET), then the timeline visibly continues;
- **K4 reactivation 178** (36,748 cross-target points; eligible 0 → 189);
- **K5 end of the normal phase:** 24 QUIET + 210 ACTIONABLE / DEFERRED, then NORMAL → RESIDUE;
- **K6 strict final-look gate** (the climax): the unchanged proposal, the 30 OPEN elements, the predicted
  left/right depth cores, the counts, REJECT `no_novel_serviceable_support`, NO RENDER / NO OBSERVE. The
  proposal is withdrawn while the unresolved support stays visible;
- **K7 honest closure:** the closure counts, `residual != failure`, `SCENE_CLOSED != global quiescence`.

An intro (title, CONTROLLED PROOF OF CONCEPT, the oracle boundary, the legend) and an outro montage (final
active fused scene, causal measurement memory, final object states, the final epistemic/residue state, point
clouds, and the separately labelled REFERENCE / EVALUATION context).

## 8. Outputs

Machine-facing cache: `/home/lvelho/rd/f3d-vision/previews/visual-language-1-classroom/` (per-step
summaries, compact angular rasters, frontier elements, frame metadata, video stage images, the reference
render). The 22 GB Controller-01 run is not duplicated.

Human-facing package: `/home/lvelho/rd/f3d-vision/visuals/visual-language-1/`:

    overview.png
    legend/visual-language-1.png
    demo/controller-02-classroom-full-1440p.mp4
    demo/controller-02-classroom-full-1080p.mp4
    demo/logical-frame-manifest.json
    frames/bootstrap.png, step_000.png … step_140.png, residue.png, closure.png
    events/reactivation-0109.png, reactivation-0178.png, defer-0210.png, final-residue-gate-0210.png
    panoramas/observed-footprint.png, final-epistemic-0210.png
    pointclouds/scene-active-maps.ply, scene-measurement-memory.ply
    narration.md
    visual-language-manifest.json
    reference/scene-reference.png, depth-reference.png, instance-reference.png   (optional)

Videos: master 2560 × 1440, 30 fps, H.264 (ffmpeg `libx264`); derived 1920 × 1080, 30 fps, from the
same stage images. No audio. `narration.md` is a concise voice-over script aligned with intro, bootstrap,
ordinary loop, 109, 210, 178, residue gate, closure and outro.

The logical-frame manifest maps every logical frame to: the global step or special event, target
id/name, action source, gaze, phase, service state / disposition, observation source files, epistemic-
and geometry-state sources, new surfels, repeated target measurements, target-valid points, the truth
classes of its panels, and its video start/end time (frames and seconds).

Point clouds are binary PLY: `scene-active-maps.ply` holds the 25 final active maps (1,059,349 surfels
expected), and `scene-measurement-memory.ply` holds every valid measurement of the 141 looks (7,843,577
points expected) with instance id and source global step. Counts and sha256 are recorded. The full data are
kept unless a documented size reason requires a deterministic sample.

Tracked files:
- `docs/methodology/visual-language-1-contract.md` (this file), `visual-language-1.md`,
  `visual-language-1-report.md`;
- `tools/visual_language/`: `style.py`, `vl1_data.py`, `vl1_draw.py`, `generate_visual_language1.py`,
  `render_reference_view.py` (Blender side) and `check_visual_language1.py`;
- `tools/repository/check_repository_layout.py`, narrowly: the new `tools/visual_language/` directory and
  these declared files.

## 9. Checks (`tools/visual_language/check_visual_language1.py`)

1. accepted Controller-01 source hashes;
2. the accepted Controller-02 replay marker and source identity;
3. 141/141 actions represented exactly once;
4. target / gaze / source of every action equal the accepted runs;
5. every event step and object correct;
6. the 109 reactivation numbers;
7. the 178 reactivation numbers;
8. the 210 deferral step and state;
9. the final-gate numbers;
10. the closure counts;
11. the controller-time paths opened no evaluation truth (recorded opened files, 0 violations, plus a live
    negative control of the firewall predicate);
12. reference / evaluation assets cannot feed controller-time generation (a planted reference read under
    the controller-time firewall is refused; the controller-time code does not import the reference path);
13. truth badges match their data provenance;
14. new-surfel / repeated-measurement annotations equal the source records;
15. no semantic role uses color as its only cue: every declared role has a non-color cue, and the rendered
    legend swatches of each role group stay pairwise distinguishable in grayscale;
16. all required logical frames exist at 2560 × 1440;
17. all required event figures exist;
18. the MP4 logical-frame timing covers the whole manifest, contiguously; decoded frames at each logical
    frame's midpoint match that frame's stage image (and not a neighbor's);
19. both videos decode fully, with the expected dimensions, frame rate and frame count;
20. the legend semantics equal the style definition;
21. the overview annotations equal the manifest and the records;
22. PLY point counts and hashes equal the recorded provenance;
23. overview, legend and event PNGs regenerate byte-identically;
24. the source runs are byte-identical (per-file sha256 before and after);
25. no controller / `fov3d` scientific behavior changed (`fov3d/` identical to `main`).

A corruption / mutation suite (`--corruptions`, on throwaway copies; sources never modified) must show
each check family failing on a deliberate defect.

## 10. Commands and cost classes (PROPOSED estimates)

    S=/home/lvelho/rd/f3d-vision/previews; V=/home/lvelho/rd/f3d-vision/visuals
    G=tools/visual_language/generate_visual_language1.py
    .venv/bin/python $G extract --source $S/controller-01-full --replay $S/controller-02-classroom-replay \
        --cache $S/visual-language-1-classroom                                        # batch, ~5 min
    blender -b scenes/classroom/classroom_eye.blend --python-exit-code 1 \
        -P tools/visual_language/render_reference_view.py -- --seeds $S/controller-01-full/bootstrap/seeds.json \
        --out $S/visual-language-1-classroom/reference-render                           # batch, one render
    .venv/bin/python $G reference --source $S/controller-01-full --cache $S/visual-language-1-classroom \
        --out $V/visual-language-1                                                    # interactive
    .venv/bin/python $G render --source $S/controller-01-full --replay $S/controller-02-classroom-replay \
        --cache $S/visual-language-1-classroom --out $V/visual-language-1              # above batch, ~10–15 min
    .venv/bin/python tools/visual_language/check_visual_language1.py --source $S/controller-01-full \
        --replay $S/controller-02-classroom-replay --cache $S/visual-language-1-classroom \
        --package $V/visual-language-1                                                # batch
    .venv/bin/python tools/visual_language/check_visual_language1.py ... --corruptions  # above batch

The render step exceeds the batch class. It is justified as the single generation of the step's durable
deliverable (141 frames plus two encodes). No overnight command is authorized.

Gates: the Visual Language 1 checker; Controller-02 checks; Controller-01 checks; repository layout;
`scripts/verify_baseline.sh`; `git diff --check`; compilation of all new Python; `fov3d/` identical to
accepted `main`.

## 11. Acceptance, stop conditions and permitted fixes

Machine completion: all checks pass, the corruption suite catches every planted defect, all gates pass,
and every required output exists. Then the report records `VISUAL_LANGUAGE_1_CANONICAL_DEMO_COMPLETE` and
qualitative status REVIEW PENDING.

Stop and report if:
- a source hash differs;
- any per-step derivation differs from its controller-time record (no forcing);
- the firewall records a violation;
- a change to `fov3d/`, a controller or an accepted artifact would be needed.

A failing reference-alignment check omits the reference products and is recorded.

Permitted fixes: defects inside `tools/visual_language/`, this step's documents and the narrow
layout-checker declaration. Nothing else.

Not in this step: merging to `main`; a handoff claim of acceptance; Natural Bootstrap-1; Tabletop.
