# Chat Handoff

## Accepted main

    main @ c5f9bf599d2e537e7d4021adacc7e53269bd18c7

`origin/main` is fast-forwarded to the docs-only handoff commit that adds this entry, whose parent is
`c5f9bf5` (the AB1d acceptance commit on branch `active-bootstrap/ab1d-safe-forward-natural-correspondence`).

Accepted milestones:
- **Active Bootstrap-1d: Safe-Forward Natural RGB Correspondence**, accepted by Luiz and Chat as an **accepted negative
  experiment** (the machine result, the negative scientific conclusion, contract section 33 and the two primary
  visuals):

      ACTIVE_BOOTSTRAP1D_SAFE_FORWARD_NATURAL_CORRESPONDENCE_ACCEPTED

  The accepted completion marker is `ACTIVE_BOOTSTRAP1D_SAFE_FORWARD_NATURAL_CORRESPONDENCE_COMPLETE`. **AB1d is
  complete.**
- **Active Bootstrap after AB1d** (a decision by Luiz and Chat, not an experiment): AB1d2, 4096-spp Observation-Quality
  Control, is next. It changes observation quality only and does not redesign the matcher; AB1e remains future. See
  "Active Bootstrap after AB1d".
- **Active Bootstrap-1c: Safe-Forward Planar vs Spherical Geometry**, accepted by Luiz and Chat (the machine result,
  the scientific conclusion, contract section 23 and the two primary visuals):

      ACTIVE_BOOTSTRAP1C_SAFE_FORWARD_PLANAR_SPHERICAL_ACCEPTED

  The accepted completion marker is `ACTIVE_BOOTSTRAP1C_SAFE_FORWARD_PLANAR_SPHERICAL_COMPLETE`. **AB1c is complete.**
- **Active Bootstrap after AB1c** (a decision by Luiz and Chat, not an experiment): geometry is now sufficiently
  settled for the intended favorable operating regime. AB1d is next and tests CORRESPONDENCE, not geometry; AB1e
  remains future. See "Active Bootstrap after AB1c".
- **Active Bootstrap-1b: Gaze-Centered Spherical Epipolar Geometry**, accepted by Luiz and Chat (the machine result,
  the scientific conclusion and the primary visual):

      ACTIVE_BOOTSTRAP1B_SPHERICAL_EPIPOLAR_GEOMETRY_ACCEPTED

  The accepted completion marker is `ACTIVE_BOOTSTRAP1B_SPHERICAL_EPIPOLAR_GEOMETRY_COMPLETE`. **AB1b is complete.**
- **Active Bootstrap operating strategy after AB1b** (a decision by Luiz and Chat, not an experiment): spherical
  geometry is not a way to make poorly conditioned stereo precise; active head pose avoids poorly conditioned
  configurations, and local stereo operates in a favorable head-relative regime. The next bounded sequence is AB1c,
  AB1d, AB1e. See "Active Bootstrap operating strategy after AB1b".
- **Active Bootstrap-1a: First Natural Stereo Look**, accepted by Luiz and Chat as an **accepted negative
  experiment** (the machine result, the one execution of RGB gaze #1 and the scientific interpretation):

      ACTIVE_BOOTSTRAP1A_FIRST_NATURAL_STEREO_LOOK_ACCEPTED

  The accepted completion marker is `ACTIVE_BOOTSTRAP1A_FIRST_NATURAL_STEREO_LOOK_COMPLETE`. **AB1a is complete.**
- **Active Bootstrap pivot after AB1a** (a decision by Luiz and Chat, not an experiment): binocular
  representation, correspondence and control are separated; the next step tests gaze-centered spherical epipolar
  geometry with perfect correspondence. See "Active Bootstrap pivot after AB1a".
- **Natural Bootstrap-1c: RGB Candidate Gaze**, accepted by Luiz and Chat (the machine result, the six frozen RGB
  gazes unchanged in frozen order, and the qualitative interpretation):

      NATURAL_BOOTSTRAP1C_RGB_CANDIDATE_GAZE_ACCEPTED

  The accepted completion marker is `NATURAL_BOOTSTRAP1C_RGB_CANDIDATE_GAZE_COMPLETE`. **NB1c is complete.**
- **Scientific pivot after NB1b** (a decision by Luiz and Chat, not an experiment): **initial bootstrap should
  not require depth.** See "Current roadmap" for the durable record.
- **Natural Bootstrap-1b: Foveal Serviceability**, accepted by Luiz and Chat as-is (the machine result, the
  measured classification and queues, the qualitative and scientific interpretation and the figures):

      NATURAL_BOOTSTRAP1B_FOVEAL_SERVICEABILITY_ACCEPTED

  The accepted completion marker is `NATURAL_BOOTSTRAP1B_FOVEAL_SERVICEABILITY_COMPLETE`.
- **Natural Bootstrap-1a: Spherical Range Connectivity**, accepted by Luiz and Chat (the machine result, the
  qualitative and scientific interpretation and the final figures):

      NATURAL_BOOTSTRAP1A_RANGE_CONNECTIVITY_ACCEPTED

  The accepted completion marker is `NATURAL_BOOTSTRAP1A_RANGE_CONNECTIVITY_COMPLETE`.
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

## Current roadmap (Luiz and Chat, after AB1d)

    Controller-02                                   ACCEPTED
      -> Visual Language 1                          ACCEPTED
      -> Breadth-1                                  ACCEPTED
      -> Natural Bootstrap-1
           NB1a spherical range connectivity        ACCEPTED
           NB1b foveal serviceability               ACCEPTED
           NB1c RGB candidate gaze                  ACCEPTED
      -> Active Bootstrap
           AB1a first natural stereo look           ACCEPTED (negative: planar representation)
           AB1b gaze-centered spherical epipolar    ACCEPTED (support preserved, geometry correct;
                geometry                                      conditioning poor at gaze #1)
           AB1c safe-forward planar vs spherical    ACCEPTED (metric geometry equivalent in the
                geometry                                      favorable regime; image support not identical)
           AB1d safe-forward natural RGB            ACCEPTED (negative: the frozen primitive matcher does not
                correspondence                                recover reliable correspondence; render-noise
                                                              causal role not established)
           AB1d2 4096-spp observation-quality       NEXT (same three views, calibration, seeds and frozen
                control                                   matcher; 256 -> 4096 spp only)
           AB1e same difficult target, whole-head   future
                recentering
      -> Classroom validation
      -> Tabletop transfer
           same controller / bootstrap policy,
           no scene-specific retuning unless execution is impossible
      -> Natural Bootstrap-2

- This roadmap is a later explicit decision. It inserted Breadth-1 before Natural Bootstrap-1. The signed
  `docs/methodology/foveal-controller-stage-charter-1.md` keeps its historical roadmap and is not edited.
- Controller-01 and Controller-02 remain frozen unless Luiz explicitly reopens them.
- Visual Language 1 remains the standing visual semantics.
- **Natural Bootstrap-1** proceeds as bounded experiments. NB1a and NB1b followed its original, modest
  formulation:

      low-resolution sensory observation
        -> perceptual decomposition
        -> temporary object hypotheses
        -> representative seed gaze per hypothesis
        -> active controller

  - It must not use the Blender object list as controller initialization.
  - No semantic classification is required initially.
  - Over-segmentation is acceptable.
  - Natural Bootstrap-2 (identity persistence) is a separate later problem.
  - Each step is designed by Luiz and Chat and committed as a contract before implementation.
- **NB1a** (accepted; see its section below) answered the decomposition question with range continuity.
- **NB1b** (accepted; see its section below) tested which NB1a seeds can host the nominal 12° foveal
  measurement core.

### Scientific pivot after NB1b (Luiz and Chat)

    INITIAL BOOTSTRAP SHOULD NOT REQUIRE DEPTH.

Decision record (durable):
1. NB1a and NB1b are accepted. They remain accepted scientific studies of what geometry can do; they are not
   discarded.
2. The project will **not** proceed next with range-based, sensor-aware reseeding.
3. Initial natural bootstrap should assume that broad dense depth is **not** available.
4. Coarse RGB is used to propose a small number of places worth interrogating.
5. Accurate depth and surface orientation are intended to become **local active measurements**, acquired after
   foveation.
6. Range continuity, depth discontinuity and surface-normal continuity remain important principles, but
   primarily during active local exploration / growth, rather than as prerequisites for initial attention.
7. The initial RGB bootstrap does **not** need to discover all objects or segment the whole scene.
8. A few candidate gazes may be enough to bootstrap active discovery.
9. The number of initial gazes is an **attention budget**, not an estimate of object count.
10. Natural Bootstrap-1c is the next experiment.

Revised near-term conceptual chain:

    coarse spherical RGB
      -> RGB candidate gazes
      -> [future step, not run now]
         local foveation
      -> local stereo depth / surface orientation
      -> active surface growth using geometric continuity

- **NB1c: RGB Candidate Gaze** (accepted; see its section below) asked whether sensor-scale center-surround
  contrast in one coarse spherical RGB observation (the accepted NB1a RGB proxy), with no depth and no Blender
  identity, can nominate K = 6 spatially separated gaze directions that provide useful starting points for
  active foveal scene discovery. Its angular scales derive from the accepted 12° core (`CORE_FOV_DEG` of the
  sealed `tools/fsg_geometry.py`). It stopped after producing and evaluating the six directions:
  - no Blender, no stereo, no new depth and no controller; no gaze was executed;
  - no RGB segmentation, no semantics, and no NB1a / NB1b / identity data in selection;
  - range, NB1a and NB1b products were read only after the RGB result was frozen, for descriptive evaluation;
  - K = 6 is an attention budget, not an object count.

### Active Bootstrap after NB1c (Luiz and Chat)

Historical record (the launch of AB1a; AB1a is now accepted, see its section below):

**NB1c is complete. The next experiment executes RGB gaze #1 exactly once.**

Near-term chain:

    coarse spherical RGB
      -> RGB candidate gaze
      -> local binocular RGB acquisition
      -> natural local stereo geometry
      -> [future, not yet] geometric active growth / controller

- **AB1a: First Natural Stereo Look** (branch `active-bootstrap/ab1a-first-natural-stereo-look`, contract
  `docs/active-bootstrap/ab1a-first-natural-stereo-look-contract.md`) asks whether the eye, starting from the
  first frozen RGB candidate gaze and the fixed binocular instrument alone, obtains useful local metric geometry
  from binocular RGB without depth, Blender identity or scene segmentation.
  - The action is already frozen: NB1c RGB gaze #1, (+76.75°, +7.75°), consumed as-is (no recomputation, no
    movement, no snapping, no cherry-picking of another gaze).
  - Instrument: the accepted FSG geometry, profile `full`, 12° core, 256 × 256, IPD 0.063 m, vergence 2.10 m,
    `baseline_projected` tangent frame, z_rect search [0.75, 4.5] m, OPTIX, 256 spp, fixed head.
  - One binocular RGB pair; the natural matcher reads only the calibration and the RGB pair (no Object Index,
    no Position, no range); the measurement is frozen before any reference truth is opened; evaluation is
    descriptive.
  - No second gaze, no surface map, no fusion, no FSG6f, no controller. A poor stereo result is the result,
    not a failure.

### Active Bootstrap pivot after AB1a (Luiz and Chat)

Historical record (the launch of AB1b; AB1b is now accepted, see its section below):

**AB1a is complete. The next experiment tests binocular REPRESENTATION only, with perfect correspondence.**

Roadmap:

    spherical RGB attention
      -> gaze-centered binocular geometry
      -> replaceable correspondence engine
      -> active local metric growth

Three concerns are kept separate:
- **REPRESENTATION**: how binocular rays are parameterized;
- **CORRESPONDENCE**: how matching left / right rays are found;
- **CONTROL**: where the eye looks next.

Rationale (durable project history):
- an early global spherical warp + SGBM experiment was unsuccessful;
- that failure helped motivate local foveal tangent-plane stereo;
- tangent-plane SGBM worked reasonably on simple, richly textured synthetic geometry;
- Classroom was much less satisfactory, but at that point matcher failure and controller failure were confounded;
- the controller was therefore validated with a perfect local matcher;
- now that the controller and the RGB bootstrap have been separated and validated, correspondence reality can be
  revisited in stages;
- AB1a exposed a representation failure **before** correspondence: near the eye baseline, conventional planar
  rectification plus a fixed central rectified crop no longer measures the intended fixation.

- **AB1b: Gaze-Centered Spherical Epipolar Geometry** (branch `active-bootstrap/ab1b-spherical-epipolar-geometry`,
  contract `docs/active-bootstrap/ab1b-spherical-epipolar-geometry-contract.md`) asks whether direct gaze-centered
  spherical epipolar ray geometry preserves the intended foveal region and recovers correct metric 3-D from the
  exact gaze-#1 binocular observation when correspondence is assumed perfect.
  - It re-analyses the exact saved AB1a pair: no Blender, no re-render, no new gaze, no second fixation, no
    controller.
  - Measurement domain: the original raw left 256 × 256 core (x, y = 192..447 of the 640 × 640 raster); the right
    match may use the full padded raster. No planar rectification, no `cv2.stereoRectify`, no rectified crop.
  - A dedicated oracle stage may use Position / Object Index and writes a truth-stripped correspondence product
    (continuous `uv_L`, `uv_R` only), frozen before geometry. The spherical geometry stage reads only the
    calibration and that product: baseline-polar `theta` from +X, `phi = atan2(d_y, -d_z)`, direct triangulation
    `rho = B / (cot theta_L - cot theta_R)`, plus an independent ray-ray cross-check. It is frozen before any
    Position truth is reopened for evaluation.
  - It is **not** a matcher benchmark, an SGBM experiment, a global spherical warp or a controller experiment. No
    correspondence fraction, error, disparity or conditioning threshold is declared.
  - A natural matcher is a later, separate experiment, only if AB1b shows the geometry itself is sound.

### Active Bootstrap operating strategy after AB1b (Luiz and Chat)

Historical record (the launch of AB1c; AB1c is now accepted, see its section below):

**AB1b is complete. The next experiment compares planar and spherical geometry in a favorable safe-forward regime,
with perfect correspondence.**

Decision record (durable):
1. AB1b is accepted (see its section below).
2. Spherical epipolar geometry is **not** intended as a way to make intrinsically poorly conditioned stereo physically
   precise.
3. The intended operating strategy is:
   - use active head pose to avoid poorly conditioned binocular configurations;
   - operate local stereo in a favorable head-relative regime;
   - use gaze-centered spherical epipolar geometry there;
   - transform measurements back into the canonical omnidirectional scene frame when head motion is later introduced.
4. Conceptual distinction:
   - **REPRESENTATION** must not destroy an otherwise valid local measurement;
   - **CONDITIONING** is physical and should be controlled by sensor / head pose.

   In particular: *"representation should not destroy a valid measurement, but active sensing should avoid
   intrinsically bad measurements in the first place."*
5. Next bounded sequence:

       AB1c  safe-forward planar vs spherical geometry
             PERFECT correspondence
             fixed head
             favorable configurations only
             PRIMARY question: geometric agreement

       AB1d  safe-forward NATURAL RGB correspondence
             only after AB1c is judged

       AB1e  return to the SAME difficult world target as AB1a / AB1b,
             rotate the whole binocular head to make the target locally
             forward / well-conditioned, use ordinary local stereo, and
             transform the result back to the canonical frame

6. Head motion is not implemented now. A natural matcher is not implemented now.

- **AB1c: Safe-Forward Planar vs Spherical Geometry** (branch
  `active-bootstrap/ab1c-safe-forward-planar-vs-spherical`, contract
  `docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-contract.md`, committed before implementation) asks
  whether, under favorable, well-conditioned head-relative viewing geometry, conventional planar tangent stereo
  geometry and gaze-centered spherical epipolar geometry recover the same local metric scene structure from the same
  binocular observations when correspondence is held perfect. It is an equivalence / control experiment, not a
  competition, not a near-baseline rescue, not a matcher, head-motion or controller experiment.
  - Three frozen gazes, chosen deterministically from the accepted NB1c RGB attention score inside a predeclared
    SAFE-FORWARD envelope (center within 20° of −Z; minimum full-core stereo leverage ≥ 0.90 in both eyes), with the
    accepted NB1c tie rule and spherical NMS (D_MIN = 16.9°); no depth, identity or stereo result in selection.
  - Exactly one binocular observation per gaze, fixed head; planar and spherical geometry consume the same
    observation and the same frozen, truth-stripped perfect-correspondence product; both geometries are frozen before
    Position is reopened for evaluation. No success threshold is declared.

### Active Bootstrap after AB1c (Luiz and Chat)

Historical record (the launch of AB1d; AB1d is now accepted, see its section below):

**AB1c is complete. The next experiment tests natural RGB correspondence in the safe-forward regime, with the accepted
spherical geometry held fixed.**

Decision record (durable):
1. AB1c is accepted (see its section below).
2. Geometry is now sufficiently settled for the intended favorable operating regime: in the safe-forward envelope,
   planar and spherical metric geometry agree under perfect correspondence, and spherical geometry also survives the
   near-baseline case (AB1b) where the planar representation failed (AB1a).
3. **AB1d tests CORRESPONDENCE, not geometry.** Geometry is held fixed to the accepted AB1b spherical epipolar geometry.
4. AB1e (the same difficult world target with whole-head recentering) remains future. Head motion is not implemented.

- **AB1d: Safe-Forward Natural RGB Correspondence** (branch
  `active-bootstrap/ab1d-safe-forward-natural-correspondence`, contract
  `docs/active-bootstrap/ab1d-safe-forward-natural-correspondence-contract.md`, committed before implementation) asks
  whether, in the favorable safe-forward regime established by AB1c, a simple natural RGB matcher can recover the
  right-eye spherical epipolar correspondence accurately enough to provide useful local metric measurements.
  - It reuses exactly the three accepted AB1c binocular observations: no Blender, no render, no new gaze, no new
    attention selection, no head motion.
  - One deliberately simple matcher: direct raw-image epipolar search, a 5 × 5 local angular patch, ZNCC and one
    one-dimensional sub-pixel peak refinement. The matcher reads only the calibration and the RGB observation.
  - Natural correspondence is frozen before geometry; the spherical geometry is frozen before the AB1c oracle or
    Position is opened. The AB1c perfect correspondence is a post-freeze benchmark only.
  - The primary metric is the angular correspondence error θ_R(natural) − θ_R(oracle). Metric error is secondary. No
    acceptance threshold is declared; a poor primitive matcher is the result, not a reason to tune it.

### Active Bootstrap after AB1d (Luiz and Chat)

**AB1d is complete. The next experiment tests whether substantially reducing Monte Carlo rendering noise materially
improves the SAME frozen primitive natural correspondence matcher. AB1d2 changes observation quality only; it does not
redesign the matcher.**

Decision record (durable):
1. AB1d is accepted as a valid negative experiment (see its section below).
2. AB1d does not establish the causal role of Monte Carlo render noise. Its labelled post-run diagnostic (roughly
   2–3 u8 per-eye variation under a noise-only interpretation, against a typical 5 × 5 patch standard deviation of about
   3–5 u8) motivates the next step; it is not a frozen causal claim.
3. The inserted causal question: **does substantially reducing Monte Carlo rendering noise materially improve the SAME
   frozen primitive natural correspondence matcher?**
4. AB1e (the same difficult world target with whole-head recentering) remains future. Head motion is not implemented.

- **AB1d2: 4096-spp Observation-Quality Control** (branch `active-bootstrap/ab1d2-4096spp-observation-quality`,
  contract `docs/active-bootstrap/ab1d2-4096spp-observation-quality-contract.md`, committed before any 4096-spp
  Classroom render).
  - The single intentional change: Cycles samples per pixel 256 -> 4096, at the same three accepted AB1c / AB1d gazes,
    with the same scene, fixed head, calibration, camera matrices, resolution, device, filter, seeds (L 2111, R 2112),
    denoising OFF and adaptive sampling OFF.
  - The accepted AB1d matcher is used read-only and unchanged (including MIN_LOCAL_STD_U8 = 0.5 and the full
    admissible search interval). The benchmark is the accepted AB1c oracle and Position reference, not new truth
    passes.
  - The primary result is a paired, pixel-by-pixel 256 vs 4096 comparison against the same oracle. No success threshold
    is declared. AB1d2 changes observation quality only; it does NOT redesign the matcher.

## Active Bootstrap-1d: Safe-Forward Natural RGB Correspondence (accepted at `c5f9bf5`)

Luiz and Chat accept AB1d as a **valid negative experiment**: the machine result, the negative scientific conclusion,
contract section 33 and the two primary visuals.

Record (branch `active-bootstrap/ab1d-safe-forward-natural-correspondence`, base `56840ca`):
- contract: `docs/active-bootstrap/ab1d-safe-forward-natural-correspondence-contract.md` (`850724d`); section 33 is the
  pre-canonical clarification (in `3c7853e`), accepted: it was written before canonical Classroom matching, corrected
  the synthetic known-answer tolerances and test textures, and did not alter the canonical matcher constants, the
  evaluation metrics or the outcome semantics, nor tune against Classroom truth.
- implementation: `tools/active_bootstrap/ab1d_{spec,match,run,synthetic,visuals}.py` and `check_ab1d.py`, frozen at
  `3c7853e` before the canonical match.
- report: `docs/active-bootstrap/ab1d-safe-forward-natural-correspondence-report.md` (completion `c541b96`, acceptance
  `c5f9bf5`).
- run: `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1d-safe-forward-natural-correspondence/`. It reads the
  three accepted AB1c observations in place (no render). Correspondence freeze `match/correspondence-freeze.json`
  `006c9116…`; geometry freeze `freeze/geometry-freeze.json` `0c2d7b0a…`. The canonical steps refuse to rerun.
- visuals: `/home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1d-safe-forward-natural-correspondence/`
  (`overview.png` `0d7217b5c7c925b0e4595cd0a72e04ed6b225487f4369cadbacb0f583bc85654` and `cost-landscapes.png`
  `0669aa19c7899ea9de45943b42101f1b9d4ef9a26d9468be5343959549cae862`, inspected and accepted; two minor presentation
  caveats accepted: patch tiles are contrast-stretched without a caption saying so, and "natural κ" mostly describes
  wrong natural correspondences).

Accepted measured result:

    ACTIVE_BOOTSTRAP1D_CHECKS_PASS          38 / 38
    ACTIVE_BOOTSTRAP1D_MUTATIONS_CAUGHT     40 / 40 (from a passing baseline; clean null probe)

Check 33 of `check_ab1d.py` is scoped to the AB1d base `56840ca`. On later commits it reports every later accepted
change outside the AB1d files as "undeclared". The first such change is this handoff's `CLAUDE.md` and
`docs/chat-handoff.md` (measured: 37/38, only check 33). That is the guard's scope, not an AB1d regression; the
frozen-product checks remain valid.

| gaze | within 1 px-equiv | median px-equiv error | oracle top-1 | oracle worse than top 8 | metric error median (natural vs perfect) |
|---|---|---|---|---|---|
| 1 | 9.2 % | 93.1 px | 9.9 % | 60.6 % | 4.16 m |
| 2 | 16.8 % | 57.4 px | 17.7 % | 54.9 % | 3.57 m |
| 3 | 9.2 % | 129.2 px | 9.8 % | 68.2 % | 4.03 m |

Accepted interpretation (durable):
1. At the three accepted safe-forward AB1c observations, the frozen primitive natural matcher (direct raw-image
   spherical epipolar search + 5 × 5 angular grayscale patch + ZNCC + one quadratic sub-pixel refinement) does NOT
   recover reliable correspondence over the full physically admissible epipolar interval.
2. The spherical search geometry is correct and the oracle location is correctly registered on the frozen score. When
   the true peak wins, sub-pixel refinement is accurate (about 0.19–0.24 px median, 93–95 % within 1 px). Search
   geometry and refinement are therefore not the main failure.
3. The correct photometric hypothesis usually does not dominate the competing hypotheses along the long search
   interval. Two failure mechanisms are retained: weak / noisy local appearance with many competing peaks, and genuine
   along-epipolar ambiguity (structure approximately parallel to the search direction).
4. Outcome 4 is supported, with Outcome 3 as an important mechanism.
5. **The causal role of Monte Carlo render noise is NOT established by AB1d.** That is the question of AB1d2.

## Active Bootstrap-1c: Safe-Forward Planar vs Spherical Geometry (accepted at `45b08ae`)

Luiz and Chat accept AB1c: the machine result, the scientific conclusion, contract section 23 and the two primary
visuals.

Record (branch `active-bootstrap/ab1c-safe-forward-planar-vs-spherical`, base `c2b8373`):
- contract: `docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-contract.md` (`d8a56aa`); section 23 is the
  pre-canonical clarification (in `03e7efe`), accepted as legitimate: it occurred before the canonical Classroom
  selection and changed only software known-answer tolerances and a PROPOSED numerical expectation, not the envelope,
  selection, planar or spherical definition, oracle semantics, metric or success semantics.
- implementation: `tools/active_bootstrap/ab1c_{spec,select,planar,render,run,synthetic,visuals}.py` and
  `check_ab1c.py`. Frozen at `03e7efe` before the canonical selection.
- report: `docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-report.md` (completion `eecdbc3`, acceptance
  `45b08ae`).
- run: `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1c-safe-forward-planar-vs-spherical/`. The three
  canonical Classroom pairs: selection freeze `selection/safe-forward-freeze.json` `72d7e4b8…`; correspondence freeze
  `oracle/correspondence-freeze.json` `e7f06f53…`; geometry freeze `freeze/geometry-freeze.json` `1b7e2207…`. Never re-render; the canonical steps refuse to rerun.
- visuals: `/home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1c-safe-forward-planar-vs-spherical/`
  (`overview.png` `0b62d77bbf0c8f5cfaf82c541ca5051abd90dd88abd456295873fa67571177c6` and
  `planar-vs-spherical-difference.png` `13a7c1c389a9470d10487a85aae28318fa91c10d16c297975f041a9ce95ab263`, inspected
  and accepted as satisfying the scientific-visual requirement).

Accepted measured result:

    ACTIVE_BOOTSTRAP1C_CHECKS_PASS          45 / 45
    ACTIVE_BOOTSTRAP1C_MUTATIONS_CAUGHT     53 / 53 (from a passing baseline; clean null probe)

Check 42 of `check_ab1c.py` is scoped to the AB1c base `c2b8373`. On later commits it reports every later accepted
change outside the AB1c files as "undeclared". The first such change is this handoff's `CLAUDE.md` and
`docs/chat-handoff.md` (measured: 44/45, only check 42). That is the guard's scope, not an AB1c regression; the
frozen-product checks remain valid.

| gaze | row, col | yaw, pitch (°) | common valid | ‖P_planar − P_spherical‖ median / p95 / max | consistency-restored max | 3-D error vs Position median | κ median |
|---|---|---|---|---|---|---|---|
| 1 | 191, 322 | −18.75, −5.75 | 53,750 | 2.95 / 6.14 / 8.82 µm | 2.1e-12 m | 0.157 mm | 80.2 |
| 2 | 166, 373 | +6.75, +6.75 | 63,293 | 1.05 / 2.22 / 3.63 µm | 1.8e-12 m | 0.125 mm | 69.2 |
| 3 | 190, 397 | +18.75, −5.25 | 65,493 | 3.57 / 8.08 / 11.64 µm | 7.8e-13 m | 0.140 mm | 76.2 |

Accepted interpretation (durable):
1. Within the predeclared safe-forward operating regime, at three independently selected RGB-attention gazes,
   conventional planar and gaze-centered spherical epipolar geometry recover the same local metric structure from the
   same binocular observations under shared perfect correspondence.
2. Their direct disagreement is only micrometric and collapses to numerical precision for exactly consistent
   correspondence: it arises from the two methods resolving the oracle's small epipolar inconsistency differently, not
   from disagreement in their exact metric stereo geometry.
3. Spherical epipolar geometry therefore preserves the benign forward case while avoiding the near-baseline
   representation pathology demonstrated by AB1a.
4. **METRIC GEOMETRY: benign equivalence established. IMAGE-SUPPORT PARAMETERIZATION: not identical.** The planar
   rectified core is sourced 0.871 / 0.968 / 1.000 from the nominal raw core, and only about 81 % / 94 % / 83 % of the
   oracle pairs lie inside it. AB1c does not establish that the whole fixed-crop planar pipeline is interchangeable with
   spherical stereo.
5. Caveats: no natural correspondence; no head motion; the 20° / min-core leverage ≥ 0.90 envelope is a design choice,
   not proven necessary or optimal; non-catalog Object Index 0 geometry was excluded by the inherited oracle; no
   generality beyond these three gazes, Classroom, this instrument and this range regime.

## Active Bootstrap-1b: Gaze-Centered Spherical Epipolar Geometry (accepted at `32fc9a3`)

Luiz and Chat accept AB1b: the machine result, the scientific conclusion and the primary visual.

Record (branch `active-bootstrap/ab1b-spherical-epipolar-geometry`, base `cbdc4eb`):
- contract: `docs/active-bootstrap/ab1b-spherical-epipolar-geometry-contract.md` (`922dc8e`).
- implementation: `tools/active_bootstrap/ab1b_{spec,oracle,geometry,run,visuals}.py` and `check_ab1b.py`. Frozen at
  `53393e3` before the canonical analysis; presentation fix `d0f1a23` (one caption).
- report: `docs/active-bootstrap/ab1b-spherical-epipolar-geometry-report.md` (completion `a597c89`, acceptance
  `32fc9a3`).
- run: `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1b-spherical-epipolar-geometry/`. A re-analysis of the
  saved AB1a pair (no render): correspondence freeze `oracle/correspondence-freeze.json`
  `d160d98faecdd8ba1c44ff532fc91cd94ab89789e9d6a31743a5c25d8ce8ba56`; geometry freeze `geometry/geometry-freeze.json`
  `942707a858c8b76cb65db503183853d27c55000eb2e59c6de4dfbcf025d21c7a`. The canonical steps refuse to rerun.
- visuals: `/home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1b-spherical-epipolar-geometry/` (`overview.png`
  `b1000881b8510ffeaab5af88b6873077982b46f8ed52b14ede3884a5e3277288`, inspected and accepted as satisfying the
  Level-A scientific-visual requirement).

Accepted measured result:

    ACTIVE_BOOTSTRAP1B_CHECKS_PASS          46 / 46
    ACTIVE_BOOTSTRAP1B_MUTATIONS_CAUGHT     51 / 51 (from a passing baseline; one probe not applicable)

| quantity | value |
|---|---|
| raw-core rays represented | 65,536 / 65,536 |
| perfect binocular correspondences / spherical triangulations | 44,769 / 44,769 |
| \|φ_R − φ_L\| median / p95 / max | 1.93e-6 / 3.22e-6 / 3.88e-6 rad |
| δθ | positive for all 44,769 pairs |
| κ median / p95 | about 262 / about 384 |
| epipolar vs ray-ray reconstruction, median / max | about 8.1e-8 m / about 2.9e-7 m |
| post-freeze error vs Blender Position, median / p95 / p99 / max | 0.408 / 0.696 / 0.788 / 0.929 mm |
| AB1a planar rectified reference-valid (accepted, MEASURED in AB1a) | 0 / 65,536 |

Accepted interpretation (durable):
1. At the deliberately difficult gaze #1, gaze-centered spherical epipolar geometry preserves the intended foveal support
   and yields correct metric geometry when correspondence is supplied perfectly.
2. The failure observed in AB1a was therefore a planar-representation failure, not an absence of binocular support.
3. Metric precision at gaze #1 nevertheless remains strongly limited by physical stereo conditioning, because the
   fixation lies near the physical eye baseline (B⊥ ≈ 16.6 mm; about 0.94 m of range per pixel-equivalent angle at
   ≈4.4 m).
4. The ≈7.8e-4 px Blender Position offset is a labelled post-run supporting diagnostic for the ≈0.4 mm systematic
   radial bias; acceptance does not depend on it as a frozen claim.
5. The synthetic case-10 margin (8.4e-10 m against 1e-9 m) stays recorded; it is not a blocker.
6. No natural matcher has been run.

## Active Bootstrap-1a: First Natural Stereo Look (accepted at `c27edb2`)

Luiz and Chat accept AB1a as an accepted negative experiment: the machine result, the one execution of RGB gaze #1
and the scientific interpretation.

Record (branch `active-bootstrap/ab1a-first-natural-stereo-look`, base `509c341`):
- contract: `docs/active-bootstrap/ab1a-first-natural-stereo-look-contract.md` (`934c0f9`); section 22 is the
  pre-run synthetic clarification and section 23 the post-run EXR-pass clarification.
- implementation: `tools/active_bootstrap/ab1a_{spec,render,stereo,run,visuals}.py` and `check_ab1a.py`. Frozen at
  `a3caaef` before the Classroom acquisition; figure fix `b17259a`; checker repairs `8c9d685`, `49869ae`.
- report: `docs/active-bootstrap/ab1a-first-natural-stereo-look-report.md` (completion `753e911`, acceptance
  `c27edb2`).
- run: `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1a-first-natural-stereo-look/`. The ONE canonical
  L / R pair at gaze #1: `acquisition/rgb-observation.npz`
  `eb84831aee9676e011651821197812c81e7d51d76ab2cecfea609d3a8dd4268d`; measurement freeze
  `53dc5ff2985cfda4ed0ef0ed13f10be12a33e1c7693942dcf9101a2d1448243e`. Never re-render; later steps re-analyse the
  saved pair.
- visuals: `/home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1a-first-natural-stereo-look/` (`overview.png`
  `b8f3452a…`).

Accepted measured result:

    ACTIVE_BOOTSTRAP1A_CHECKS_PASS          42 / 42
    ACTIVE_BOOTSTRAP1A_MUTATIONS_CAUGHT     51 / 51 (from a passing baseline)

    natural RGB-only stereo valid           0 / 65,536
    post-freeze perfect-reference valid     0 / 65,536

Accepted interpretation (durable):
1. AB1a does **not** establish that RGB gaze #1 is intrinsically unmeasurable.
2. It establishes that, at this gaze, the accepted conventional planar rectification plus the fixed central
   rectified-core measurement does not measure the intended fixation.
3. Mechanism (calibration-only, recorded before the acquisition): the gaze is 15.315° from the physical baseline;
   L = 0.2641255292; B⊥ = 16.64 mm; the rectification rotates the cameras by about 75°; the rectified principal point
   lies about −66,000 px from a 640-px raster; the 256 × 256 rectified core is sourced from about a 0.09 × 4.8
   raw-pixel sliver, about 14.26° from the fixation and 1.05° from the baseline axis; in Classroom that sliver holds
   no geometry.
4. The raw L / R tangent images contain the intended bright, structured, textured window fixation. The camera model
   is valid at the rendered gaze (about 0.001 px projection residual).
5. Record it as: the existing planar rectification / central-crop measurement representation fails to preserve the
   intended foveal support at this near-baseline gaze. Not as "SGBM failed on the window", nor as "stereo is
   impossible at gaze #1".
6. The resolved inherited-EXR-pass incident (11 Classroom lighting / material passes, contract section 23) stays in
   the record; those passes stayed in `evaluation_only/` and did not contaminate inference.

## Natural Bootstrap-1c: RGB Candidate Gaze (accepted at `6b0ba68`)

Luiz and Chat accept NB1c: the machine result, the six frozen RGB gazes unchanged in frozen order, and the
qualitative interpretation.

Record (branch `natural-bootstrap/nb1c-rgb-candidate-gaze`, base `7d1c1b9`):
- contract: `docs/natural-bootstrap/nb1c-rgb-candidate-gaze-contract.md` (`9a862dc`); section 23 is the
  pre-evaluation numerical-robustness clarification (`c7d04db`).
- implementation: `tools/natural_bootstrap/nb1c_{spec,attention,run,visuals}.py` and `check_nb1c.py`. Frozen at
  `37c18d8` before the canonical selection; check-27 repair `c7d04db`.
- report: `docs/natural-bootstrap/nb1c-rgb-candidate-gaze-report.md` (STOP report `800af61`, completion `8c7cabf`,
  acceptance `6b0ba68`).
- run: `/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1c-rgb-candidate-gaze/`. The selection is frozen:
  `selection/rgb-gaze-freeze.json` `87a3bab01f55051316ac1eb45b48f394211f4c7a3a317fd0e61c0e52c36f9b37`;
  `selection/candidate-gazes.json` `8041b954f7b63d97f060a41aaca5db1ec6e0c2295381523026e98d11f8a5b621`. `select`
  refuses to rerun; later steps read the frozen products.
- visuals: `/home/lvelho/rd/f3d-vision/visuals/natural-bootstrap-1c-rgb-candidate-gaze/` (`overview.png`
  `9b79b362…`, the RGB input, attention map, candidate gazes and crops, evaluation and NB1b comparison figures).

Accepted measured result:

    NATURAL_BOOTSTRAP1C_CHECKS_PASS        36 / 36
    NATURAL_BOOTSTRAP1C_MUTATIONS_CAUGHT   38 / 38 (from a passing baseline)

Check 35 of `check_nb1c.py` is scoped to the NB1c base `7d1c1b9`. On later commits it reports every later
accepted change outside the NB1c files as "undeclared". The first such change is this handoff's `CLAUDE.md` and
`docs/chat-handoff.md` (measured: 35/36, only check 35). That is the guard's scope, not an NB1c regression; the
frozen-product checks remain valid.

| rank | row, col | yaw, pitch (°) | A |
|---|---|---|---|
| 1 | 164, 513 | +76.75, +7.75 | 1.432258 |
| 2 | 28, 354 | −2.75, +75.75 | 1.331223 |
| 3 | 231, 510 | +75.25, −25.75 | 1.196390 |
| 4 | 303, 436 | +38.25, −61.75 | 1.179161 |
| 5 | 110, 719 | +179.75, +34.75 | 1.142861 |
| 6 | 122, 47 | −156.25, +28.75 | 1.110885 |

The round-2 STOP (margin 1.616e-6 against the loose single-value tolerance) was correct under the conservative
interpretation and stays in the record. It was resolved before evaluation by contract section 23 (E = 4.3e-14;
B = 2E + T; every round robust; identical independent picks); no gaze, order or selection rule changed.

Accepted interpretation (durable):
1. The RGB-only center-surround mechanism produces meaningful, spatially diverse visual invitations rather than
   obvious noise extrema.
2. A candidate gaze is not a successful measurement.
3. Three environment hits are not a bootstrap failure: coarse RGB knows visual distinctiveness, not foreground
   identity.
4. The mechanism must not be retuned to recover the NB1b PRIMARY candidates.
5. Gaze 3 independently chooses a much better location on H0004 than the old graph-clearance NB1a seed; this
   must not be used to cherry-pick gaze 3.
6. Execution consumes the already frozen RGB ordering.

## Natural Bootstrap-1b: Foveal Serviceability (accepted at `0238f00`)

Luiz and Chat accept NB1b as-is: the machine result, the measured classification and queues, the qualitative and
scientific interpretation, and the figures.

Record (branch `natural-bootstrap/nb1b-foveal-serviceability`, base `9c01b8a`):
- contract: `docs/natural-bootstrap/nb1b-foveal-serviceability-contract.md` (`aaeb095`).
- implementation: `tools/natural_bootstrap/nb1b_{spec,serviceability,run,visuals}.py` and `check_nb1b.py`.
  Frozen at `c1e273a` before the canonical selection.
- report: `docs/natural-bootstrap/nb1b-foveal-serviceability-report.md` (completion `e6ff9e4`, acceptance
  `0238f00`).
- run: `/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1b-foveal-serviceability/`. The selection is
  frozen: `selection/serviceability-freeze.json`
  `f99b7cae02498feb21ae1d80978b57c877c44984067d55c7fd2bbe189efb6e9a`. `select` refuses to rerun; later steps read
  the frozen products.
- visuals: `/home/lvelho/rd/f3d-vision/visuals/natural-bootstrap-1b-foveal-serviceability/`:
  - `overview.png` `417084b6542c3a474c6f9cef463c65e18b480769da9d5f9aa18624fb70e7abb5`;
  - `serviceability-panorama.png` `f6a25f5da37611a23a2fffa94d60673515372b1629c74bd32a0640cffd602ee1`;
  - `footprint-examples.png` `bab8bb95177e5dc62d9e6d53205e430cb072a87a399b0b5beb1e7b67a02c201b`;
  - the primary / secondary panoramas, the environment candidate and the class counts.

Accepted measured result:

    NATURAL_BOOTSTRAP1B_CHECKS_PASS        33 / 33
    NATURAL_BOOTSTRAP1B_MUTATIONS_CAUGHT   30 / 30 (from a passing baseline)

Checks 30–31 of `check_nb1b.py` are scoped to the NB1b base `9c01b8a`. On later commits, check 31 reports every
later accepted change outside the NB1b files as "undeclared". The first such change is this handoff's `CLAUDE.md`
and `docs/chat-handoff.md` (measured: 32/33, only check 31). That is the guard's scope, not an NB1b regression; the
frozen-product checks remain valid.

| class | hypotheses | queue |
|---|---|---|
| `ENVIRONMENT_CANDIDATE` | 1 | H0001 (the only hypothesis above 2π sr; not queued) |
| `PRIMARY_LOOK` | 2 | P1 H0002, P2 H0003 |
| `SECONDARY_LOOK` | 3 | S1 H0009, S2 H0006, S3 H0007 |
| `MARGINAL` | 81 | — |
| `EDGE_ONLY` | 366 | — |
| total | 453 | |

Accepted interpretation (durable):
1. The sensor-serviceability categories are visually meaningful.
2. P1 and P2 are coherent, robust foreground candidates (about 0.6–0.7 m away, 100 % O_0 in evaluation).
3. The SECONDARY distinction is visibly explained by the full square footprint crossing neighbouring structure.
4. The > 2π rule cleanly isolates the large environment / scene shell.
5. H0004 confirms that NB1a **graph-interior clearance** is not direct angular room around the sensor.
6. The minor presentation issues are non-blocking.

**Terminology.** NB1a "clearance" means graph-interior clearance: multi-source Dijkstra distance along retained
continuity edges from label-boundary cells. Do not describe it as direct angular depth inside a region.


## Natural Bootstrap-1a: Spherical Range Connectivity (accepted at `dcd294f`)

Luiz and Chat accept NB1a: the machine result, the qualitative and scientific interpretation, and the final
figures.

Record (branch `natural-bootstrap/nb1a-range-connectivity`, base `0fe83af`):
- contract: `docs/natural-bootstrap/nb1a-range-connectivity-contract.md` (`f4fa2c3`).
- implementation: `tools/natural_bootstrap/nb1a_{spec,guard,discovery,run,visuals}.py` and `check_nb1a.py`.
  Frozen at `6b63cdc` before the canonical discovery; presentation fix `8cc368d` (figures only).
- report: `docs/natural-bootstrap/nb1a-range-connectivity-report.md` (completion `a0c98be`, acceptance
  `dcd294f`).
- run: `/home/lvelho/rd/f3d-vision/previews/natural-bootstrap-1a-range-connectivity/`. The discovery is
  frozen: `discovery/bootstrap-freeze.json`
  `c0236d0424a7724bfe57bf0a19bdf56899b7eadf5e059c9537e785f3a08b826a`. `discover` refuses to rerun; later
  steps read the frozen products. The only scene evidence is the Breadth-1 canonical EXR (never re-rendered).
- visuals: `/home/lvelho/rd/f3d-vision/visuals/natural-bootstrap-1a-range-connectivity/`:
  - `overview.png` `eb334876…`;
  - `hypothesis-panorama.png` `c0471cf9…`, `seed-panorama.png` `f4b853a9…`;
  - `rgb-edge-contrast.png` `2ed52df4…`;
  - the range, continuity, histogram and overlap figures.

Accepted measured result:

    NATURAL_BOOTSTRAP1A_CHECKS_PASS        33 / 33 (at `8cc368d`)
    NATURAL_BOOTSTRAP1A_MUTATIONS_CAUGHT   29 / 29 (from a passing baseline)

Checks 30–31 of `check_nb1a.py` are scoped to the NB1a base `0fe83af`. On later commits, check 31 reports
every later accepted change outside the NB1a files as "undeclared". The first such change is this handoff's
`CLAUDE.md` and `docs/chat-handoff.md`. That is the guard's scope, not an NB1a regression; the
frozen-product checks remain valid.

| quantity | value |
|---|---|
| continuity rule | retain iff C ≤ sec 75° (the single declared parameter; not tuned) |
| valid / invalid cells | 255,758 / 3,442 |
| retained / cut edges | 972,192 / 45,080 |
| hypotheses / singletons | 453 / 137 |
| largest hypothesis H0001 | 10.3815 sr, 82.6 % of the sphere; 123 authored ids (evaluation) |
| near foreground H0002–H0007 | 0.45–1.5 m; seed graph-interior clearance 5.3–13.1°; 100 % O_0 (evaluation) |
| zero-clearance seeds / no-boundary fallbacks | 366 / 0 |

Accepted interpretation (durable):
1. Range continuity discovers useful foreground proto-objects.
2. The largest near-foreground hypotheses are coherent and seedable; their deep-interior seeds have roughly
   5–13° of clearance (graph-interior clearance; see the NB1b terminology note).
3. A dominant structural shell, H0001, occupies 82.6 % of the sphere.
4. The shell is not automatically a segmentation failure: it is a plausible environment / scene-shell
   representation.
5. The long tail of small pieces and singletons exposes thin, grazing and boundary-dominated geometry.
6. The count of 453 must not be read as "453 objects".
7. The RGB diagnostics show additional appearance structure inside range-derived hypotheses, but NB1a does
   not establish that RGB should immediately be added to segmentation.
8. The next question is sensor-qualified look-worthiness, not further segmentation.
9. Range is a controlled sensory proxy (Blender Position), not stereo; NB1a removed Blender object identity
   from discovery, nothing more.

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
Charter 1, Controller-02, Visual Language 1, Breadth-1, NB1a, NB1b, NB1c, AB1a, AB1b, AB1c and AB1d are accepted. The
Controller-01 investigation is closed. Controller-01 and Controller-02 are frozen unless Luiz explicitly reopens them.

**Current next activity: Active Bootstrap-1d2 — 4096-spp Observation-Quality Control** (see "Active Bootstrap after
AB1d"), on branch `active-bootstrap/ab1d2-4096spp-observation-quality` from this accepted `main`, with its contract at
`docs/active-bootstrap/ab1d2-4096spp-observation-quality-contract.md`. The same three accepted AB1c / AB1d gazes are
re-rendered once each at 4096 spp (instead of 256), with every other render setting, the calibration and the seeds
unchanged. The accepted AB1d matcher runs unchanged on the new pairs, and the result is compared pixel by pixel with
AB1d against the same accepted AB1c benchmark. No success threshold. No matcher change, no denoising, no head motion,
no controller. AB1e is not started. Range-based reseeding, RGB segmentation and Natural Bootstrap-2 are not started.
FSG6f is not repaired.

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
6. `README.md`'s status paragraph predates the Controller-02, Visual Language 1, Breadth-1, NB1a, NB1b, NB1c, AB1a,
   AB1b, AB1c and AB1d acceptances, the revised roadmap, the post-NB1b pivot, the start of Active Bootstrap, the
   post-AB1a pivot and the post-AB1b operating strategy. These handoff updates did not touch it.
7. Breadth-1 evaluation universe (intentionally open): how collection-instanced Classroom geometry (desks,
   chairs, lamps, …), rendered but outside the 234-object catalog, should enter future reference /
   evaluation. It is left for Natural Bootstrap and later evaluation design.
