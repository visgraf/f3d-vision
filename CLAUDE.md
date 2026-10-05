# Working agreement

Science-led, engineering-disciplined project.

The project is developed through two human-supervised AI surfaces connected by a
shared GitHub repository:

- Mac Studio / macOS: Luiz + ChatGPT
- PC workstation / Ubuntu 24.04 / RTX 4090: Luiz + Claude Code in VS Code
- Shared persistent state: https://github.com/visgraf/f3d-vision

Luiz is the project lead and decision authority.

ChatGPT is the design, review and specification surface. Its GitHub connection is
read-only.

Claude Code is the workstation implementation, repository-mutation, execution,
diagnosis, and measurement surface.

GitHub is the durable source of truth and the normal handoff medium between the two.

## The loop

    Luiz sets direction
        ↓
    Chat reads the live repository, reasons about the next step,
    develops the architecture / specification / contract / code drafts,
    checks what it can, and prepares a self-contained Claude Code prompt
        ↓
    Luiz gives the prompt to Claude Code
        ↓
    Claude Code creates/uses the authorized branch and isolated worktree,
    commits the durable contract before substantial execution,
    implements, diagnoses, measures, commits, and pushes
        ↓
    Chat reads and reviews the resulting GitHub commits, reports, and diffs
        ↓
    Luiz accepts, redirects, or rejects
        ↓
    repeat

Luiz remains in the loop for decisions. Beyond giving Claude Code the prompt, Luiz does
not act as a mechanical file courier.

## Authority and responsibility

### Luiz

Luiz:

- sets scientific and architectural direction;
- decides when a proposal should be committed;
- decides whether a result is accepted;
- decides when the project moves to the next phase;
- mediates between Chat and Claude Code when judgment or clarification is required.

Neither AI surface makes an undelegated project decision.

### ChatGPT

ChatGPT's GitHub connection is **read-only**.

Chat may inspect, search and review authorized repository content. Chat does **not**
push commits, branches, updates, or pull requests.

Chat:

- reads the current GitHub repository before proposing changes;
- reasons about architecture, experiments, checks, and acceptance criteria;
- drafts architecture, specifications, contracts, code, and documentation;
- prepares the self-contained Claude Code prompt for each substantial handoff;
- runs checks available in its environment;
- clearly states what it could not run;
- reviews Claude Code's committed reports and changes directly from GitHub;
- distinguishes proposed behavior from measured behavior.

In the normal workflow, repository mutation is performed by Claude Code under Luiz's
authority. Luiz remains free to intervene explicitly.

### Claude Code

Claude Code is the execution authority on the Ubuntu workstation and performs the
repository mutations of the normal workflow.

It:

- creates or uses the explicitly authorized branch, and pulls its exact head before
  starting;
- works in a dedicated isolated git worktree, and does not switch or mutate the shared
  checkout;
- reads this working agreement and the step contract;
- commits the durable step contract before substantial implementation or execution;
- runs commands in the prescribed order;
- reads actual console output rather than trusting exit status alone;
- diagnoses a failing check before modifying code;
- makes only fixes within the delegated scope;
- does not weaken checks, change acceptance criteria, or tune against evaluation truth;
- records measured quantities and their source;
- commits and pushes the resulting implementation/report;
- stops when a decision rule requires Luiz or Chat.

GPU, Blender, scene-asset, performance, and full workstation claims become
**measured facts only after workstation execution**.

## GitHub handoff

GitHub is the default transport. The normal handoff is:

1. Chat prepares the design/specification and a self-contained Claude Code prompt.
2. Luiz gives the prompt to Claude Code.
3. Claude Code creates/uses the authorized branch and isolated worktree.
4. For substantial work, Claude Code commits the durable contract **before**
   implementation/execution.
5. Claude Code implements, executes, and measures.
6. Claude Code commits and pushes the implementation/report.
7. Chat reviews the committed result directly from GitHub.
8. Luiz decides whether it is accepted.

For each substantial handoff, Chat provides Luiz with a self-contained Claude Code
prompt ready to paste.

The committed contract, normally `docs/<stage>/<phase>-contract.md`, is the durable
specification. The paste-ready prompt supplies the handoff context needed to create and
execute it; it does not replace the committed contract.

No result needs to be pasted between Chat and Code when it is already committed in
the repository.

ZIP + SHA256 remains only a fallback, for when direct repository transfer is
impossible or an external exact package must be transferred.

## Branch policy

Development occurs on the explicitly active project branch.

Do not assume `main`.

Before proposing or changing anything, both Chat and Claude Code must identify the
current active branch and its head.

Normal development is forward-only:

- commit;
- push;
- revert if wrong;
- do not rewrite published history.

No PR gate is required unless Luiz explicitly introduces one.

A phase or architectural branch may be merged or superseded only by an explicit
project decision.

## Proposed versus measured

Every important claim belongs to one of three states:

- **PROPOSED** — designed or predicted, but not run on the workstation;
- **MEASURED** — produced by an identified command/run and recorded in a committed
  report or other durable source;
- **ASSUMED / ESTIMATED** — explicitly identified as such.

Never blur these categories.

A Chat proposal or contract draft may contain expected outputs.

Only workstation execution converts them into measured outputs.

## Two hard rules

1. **Measured, proposed, or assumed — never ambiguous.**

   Every numerical claim is explicitly one of:
   - measured from an identified run — say where;
   - proposed or expected but not yet workstation-validated — say so;
   - assumed or estimated — say so.

2. **Every tool ships a check that can fail.**

   A control, known answer, invariant, negative test, or behavioral comparator must
   be able to expose an incorrect implementation.

   A tool that cannot come out wrong has not been tested.

## Scientific, design and refactoring steps

Scientific work, architectural design, and structural refactoring have different
visible products.

### Scientific / behavioral and design steps

An executed scientific/behavioral step must produce:

- a measurable result;
- its run evidence under `./previews`;
- at least one human-inspectable scientific visual under `./visuals`;
- fail-capable checks;
- a short Git-tracked report recording the result, the visual paths and the
  regeneration command.

Diagnostic plots alone need not satisfy the visual requirement: whenever the
phenomenon has a meaningful spatial or temporal representation, the visual shows
the phenomenon itself. `docs/methodology/preview-visual-policy.md` defines both
trees and the visual levels.

Pure architectural/design steps may instead produce a reviewed specification
or contract, together with a short summary.

### Structural / migration / refactoring step

A visual result is not mandatory.

Instead, the change must provide machine-checkable evidence that preserved behavior
remains preserved.

For the sealed Classroom baseline this normally includes the relevant structural
checks and the committed golden behavioral comparator, with:

    MISMATCHES 0

unless the contract explicitly declares a deliberate behavioral change.

Refactoring must not silently become a scientific change.

## Current project stage

The Conceptual Core migration/refactoring through Core 14 is accepted
and paused.

Do not start another migration or cleanup Core automatically.

The project is in the Integrated Foveal Controller stage, built on the
`fov3d/` substrate and governed by Foveal Controller Stage Charter 1
(`docs/methodology/foveal-controller-stage-charter-1.md`) and by the later
roadmap decision recorded in `docs/chat-handoff.md`:

- Controller-01 and its audits Controller-01A, 01B and 01C are accepted.
- Controller-01 is frozen as the good-enough integrated-controller
  baseline. Do not automatically refine its local policy; its known
  limitations are documented, not repaired.
- Controller-02 (normal scene loop, deferred residue, one strict final
  residue probe, honest scene closure) is accepted. Controller-01 and
  Controller-02 stay frozen unless Luiz explicitly reopens them.
- Visual Language 1 (`docs/methodology/visual-language-1.md`) is accepted
  and is the standing visual semantics for later experiments.
- Breadth-1: Classroom-234 Spherical Glance is accepted. It is one shallow
  720 × 360 (0.5°) full-sphere reference observation from the fixed head,
  closing the oracle-bootstrap era:
  - 234 catalog objects = 126 visible + 108 with no first hit;
  - the catalog is not an exhaustive inventory of rendered geometry:
    15.4 % of the sphere carries no catalog id.
- Natural Bootstrap-1 proceeds as bounded experiments. NB1a and NB1b
  followed the original formulation:

      low-resolution sensory observation
        -> perceptual decomposition
        -> temporary object hypotheses
        -> representative seed gaze per hypothesis
        -> active controller

  - It must not use the Blender object list as controller initialization.
  - No semantic classification is required initially.
  - Over-segmentation is acceptable.
  - Each step is designed by Luiz and Chat and committed as a contract
    before implementation.
  - NB1a: Spherical Range Connectivity is accepted. Range continuity on the
    accepted Breadth-1 proxy gives 453 temporary hypotheses (not 453
    objects): coherent, seedable near-foreground proto-objects (seed
    graph-interior clearance about 5–13°), one structural shell H0001
    (82.6 % of the sphere, a plausible environment / scene shell rather than
    a segmentation failure) and a long boundary-dominated tail. NB1a does
    not establish that RGB should be added to segmentation.
  - NB1b: Foveal Serviceability is accepted. At the unchanged NB1a seeds,
    the nominal 12° square core classifies the 453 hypotheses as
    1 environment candidate (H0001, the only one above 2π sr), 2 PRIMARY
    (H0002, H0003), 3 SECONDARY (H0009, H0006, H0007), 81 MARGINAL and
    366 EDGE_ONLY.
  - Terminology: NB1a "clearance" means graph-interior clearance (distance
    along retained continuity edges from a label boundary). It is not
    direct angular room around the sensor (NB1b, H0004).
- Scientific pivot after NB1b (Luiz and Chat): **initial bootstrap should not
  require depth.**
  - NB1a and NB1b remain accepted studies of what geometry can do.
  - The project does not proceed next with range-based, sensor-aware
    reseeding.
  - Initial natural bootstrap assumes broad dense depth is not available.
    Coarse RGB proposes a small number of places worth interrogating.
  - Accurate depth and surface orientation are intended to become local
    active measurements, acquired after foveation.
  - Range continuity, depth discontinuity and surface-normal continuity
    remain important principles, but primarily during active local
    exploration / growth, not as prerequisites for initial attention.
  - The initial RGB bootstrap need not discover all objects or segment the
    scene. A few candidate gazes may be enough to bootstrap active
    discovery; their number is an attention budget, not an object-count
    estimate.
  - NB1c: RGB Candidate Gaze is accepted and complete. From one coarse
    spherical RGB observation (no depth, no Blender identity), sensor-scale
    center-surround contrast nominated six frozen gazes, accepted unchanged
    in frozen order (freeze `87a3bab0`); gaze #1 is (+76.75°, +7.75°).
    A candidate gaze is not a successful measurement. Three environment hits
    are not a bootstrap failure. The mechanism is not retuned toward the
    NB1b PRIMARY candidates, and later steps consume the frozen ordering
    (no cherry-picking, e.g. of gaze 3).
- Active Bootstrap began after NB1c.
  - AB1a: First Natural Stereo Look is accepted as a negative experiment.
    Frozen RGB gaze #1 (+76.75°, +7.75°) was executed exactly once:
    natural RGB-only valid 0 / 65,536 and post-freeze perfect-reference
    valid 0 / 65,536. AB1a does not show that gaze #1 is unmeasurable. At
    this near-baseline gaze (15.3° from the baseline) the accepted planar
    rectification plus the fixed central rectified core samples a raw sliver
    14.3° from the fixation and 1.05° from the baseline, which holds no
    geometry; the raw L/R images contain the intended textured fixation.
    The failure belongs to the measurement representation, not to SGBM or
    to the fixation.
- Active Bootstrap pivots after AB1a to spherical epipolar geometry.
  Roadmap:

        spherical RGB attention
          -> gaze-centered binocular geometry
          -> replaceable correspondence engine
          -> active local metric growth

  Keep three concerns separate:
  - REPRESENTATION: how binocular rays are parameterized;
  - CORRESPONDENCE: how matching left/right rays are found;
  - CONTROL: where the eye looks next.
  - AB1b: Gaze-Centered Spherical Epipolar Geometry is accepted. On the
    saved AB1a pair at the deliberately difficult gaze #1, with perfect
    correspondence, spherical epipolar geometry preserves the intended
    foveal support (65,536 / 65,536 raw-core rays; 44,769 perfect
    correspondences, all triangulated) and yields correct metric geometry
    (error vs Position median 0.41 mm, max 0.93 mm). The AB1a failure was
    a planar-representation failure, not an absence of binocular support.
    Metric precision there remains strongly limited by physical
    conditioning (kappa median about 262), because the fixation lies near
    the eye baseline. No natural matcher has been run.
- Active Bootstrap operating strategy after AB1b (Luiz and Chat).
  Spherical epipolar geometry is not intended as a way to make
  intrinsically poorly conditioned stereo physically precise. Instead:
  use active head pose to avoid poorly conditioned binocular
  configurations; operate local stereo in a favorable head-relative
  regime; use gaze-centered spherical epipolar geometry there; transform
  measurements back into the canonical omnidirectional scene frame when
  head motion is later introduced.
  - REPRESENTATION must not destroy an otherwise valid local measurement.
  - CONDITIONING is physical and should be controlled by sensor / head
    pose: "representation should not destroy a valid measurement, but
    active sensing should avoid intrinsically bad measurements in the
    first place."
  - Next bounded sequence:
    - AB1c: safe-forward planar vs spherical geometry. Perfect
      correspondence, fixed head, favorable configurations only; the
      primary question is geometric agreement.
    - AB1d: safe-forward natural RGB correspondence, only after AB1c is
      judged.
    - AB1e: return to the same difficult world target as AB1a / AB1b,
      rotate the whole binocular head so the target is locally forward and
      well conditioned, use ordinary local stereo, and transform the result
      back to the canonical frame.
  - AB1c: Safe-Forward Planar vs Spherical Geometry is accepted. Within
    the predeclared safe-forward regime (20° cone about −Z, min-core
    leverage ≥ 0.90), at three independently selected RGB-attention gazes,
    planar and gaze-centered spherical epipolar geometry recover the same
    local metric structure from the same binocular observations under
    shared perfect correspondence: direct disagreement median 1–4 µm,
    max ≤ 12 µm, collapsing to about 1e-12 m for exactly consistent
    correspondence. Spherical geometry preserves the benign forward case
    while avoiding the AB1a near-baseline pathology. METRIC GEOMETRY:
    benign equivalence established. IMAGE-SUPPORT PARAMETERIZATION: not
    identical (the planar rectified core holds about 81–94 % of the
    oracle pairs). AB1c does not establish that the whole fixed-crop
    planar pipeline is interchangeable with spherical stereo.
- Active Bootstrap after AB1c (Luiz and Chat). Geometry is now
  sufficiently settled for the intended favorable operating regime.
  - AB1d: safe-forward natural RGB correspondence tests CORRESPONDENCE,
    not geometry: it reuses the three accepted AB1c observations (no
    render, no new gaze, fixed head) with the accepted AB1b spherical
    geometry held fixed.
  - AB1d: Safe-Forward Natural RGB Correspondence is accepted as a
    NEGATIVE experiment. At the three accepted safe-forward AB1c
    observations (256 spp, undenoised), the frozen primitive matcher
    (direct raw-image spherical epipolar search, 5 x 5 angular gray
    patch, ZNCC, one quadratic sub-pixel refinement) does not recover
    reliable correspondence over the full physically admissible epipolar
    interval: within 1 pixel-equivalent 9.2 / 16.8 / 9.2 %; oracle top-1
    photometric peak 9.9 / 17.7 / 9.8 %; median metric error
    4.16 / 3.57 / 4.03 m. Search geometry and refinement are not the main
    failure (when the true peak wins, median 0.19–0.24 px); the correct
    photometric hypothesis usually does not dominate the competing
    hypotheses along the long interval. Outcome 4 is supported, with
    Outcome 3 (along-epipolar ambiguity) as an important mechanism. The
    causal role of Monte Carlo render noise is NOT established by AB1d.
- Active Bootstrap after AB1d (Luiz and Chat).
  - AB1d2: 4096-spp Observation-Quality Control asks: does substantially
    reducing Monte Carlo rendering noise materially improve the SAME
    frozen primitive natural correspondence matcher? AB1d2 changes
    observation quality only (Cycles 256 -> 4096 spp at the same three
    gazes, calibration, seeds and render settings). It does NOT redesign
    the matcher.
  - AB1d2 is accepted. At the three accepted safe-forward Classroom
    gazes, 256 -> 4096 spp (everything else fixed) substantially improves
    natural spherical epipolar correspondence: within 1 pixel-equivalent
    9.2 / 16.8 / 9.2 % -> 35.9 / 66.6 / 49.2 %; median error
    93.1 / 57.4 / 129.2 -> 26.4 / 0.258 / 1.748 px. The AB1d failure was
    strongly limited by observation quality, but large residual
    along-epipolar ambiguities remain: cleaner observations alone do not
    make independent 5 x 5 local-patch matching generally sufficient.
    Outcome 1 strongly supported, with the Outcome-2 residual.
  - 4096 spp is the reference observation quality for subsequent
    SYNTHETIC Classroom natural-correspondence experiments. This is a
    project control choice, not a claim of optimality, biological
    plausibility or sensor equivalence.
- Active Bootstrap after AB1d2 (Luiz and Chat): THE SGBM BET.
  - Natural stereo receives ONE additional bounded attempt: AB1d3,
    one-shot SGBM viability. It uses the accepted 4096-spp observations
    and one frozen pre-existing SGBM configuration, with no parameter
    tuning or sweep.
  - If SGBM is judged operationally useful: adopt SGBM as the current
    natural correspondence service, stop improving stereo, and return to
    the active-perception program.
  - Otherwise: stop natural-stereo development, use the already
    validated PERFECT / oracle matcher as the local-correspondence
    service for the North Star concept demo (the full Classroom
    active-perception demonstration), and return immediately to the
    active-perception / full-Classroom roadmap. Natural stereo then
    becomes a DEFERRED RESEARCH TOPIC, revisited only after the full
    Classroom demonstration is achieved.
  - AB1e (head-recentered natural stereo) is no longer an obligatory
    prerequisite for returning to the North Star.
  - AB1d3: One-Shot SGBM Viability is accepted as Outcome 2. On the
    accepted 4096-spp safe-forward Classroom observations the frozen SGBM
    matcher almost eliminates the catastrophic along-epipolar
    ambiguities of the independent local matcher (within 1
    pixel-equivalent 96.7 / 98.4 / 99.9 % of evaluable outputs,
    essentially no catastrophic errors), but at the present baseline,
    range and scene distances its subpixel precision gives median metric
    errors of about 103 / 66 / 86 mm and insufficient effective coverage
    at the 12–50 mm persistent-map scales. Spatial aggregation solves
    most of the gross correspondence ambiguity; SGBM is NOT ADOPTED as
    the operational matcher for the North-Star concept demonstration.
- RETURN TO THE NORTH STAR (Luiz and Chat, after AB1d3; the second
  mandate).
  - NATURAL STEREO IS DEFERRED. It is a DEFERRED RESEARCH TOPIC, not
    discarded, reopened only after the full Classroom active-perception
    demonstration has been achieved. The accepted stereo record AB1a–AB1d3
    is its head start. Do not open another stereo experiment now.
  - The North-Star concept demonstration uses the validated PERFECT /
    ORACLE correspondence service (the accepted AB1b oracle semantics).
  - Near-term roadmap:
    - Natural Bootstrap: coarse 360 RGB -> six frozen RGB candidate gazes
      (NB1c), accepted.
    - Active Bootstrap / stereo investigation: AB1a through AB1d3,
      complete.
    - North Star-1a: one six-gaze RGB bootstrap round -> perfect local
      measurements -> persistent entity seeds. Accepted (below).
    - North Star-1b: connect the seed set to the accepted local
      controller. Accepted (below).
    - North Star-1c (next): coherent multi-entity control, first scene
      switch (below).
    - Later: the full Classroom active scene loop and the final
      omnidirectional outputs.
  - Controller-01, Controller-02, NB1c and Visual Language 1 stay frozen
    unless explicitly reopened.
  - Head recentering / AB1e is not a prerequisite for the concept demo.
    The first North-Star concept-demo path remains fixed-head /
    static-scene.
  - Head motion is not implemented yet. No natural matcher has been
    adopted.
  - NS1a: Perfect Bootstrap Round is ACCEPTED as Outcome 1, with
    documented Outcome-2 elements. One frozen six-gaze 360° RGB bootstrap
    round, followed by PERFECT / oracle local correspondence, accepted
    spherical metric geometry, local ORACLE SEGMENTATION AID identity and
    the accepted persistent surface-map machinery, creates a substantial
    persistent multi-entity seed set without using the global Blender
    catalog to initialize the bootstrap: 22 positive local entities, 13
    initialized, 9 never initialized; 302,936 surfels; five large maps
    (entities 10, 110, 178, 12, 172); pooled instance-0 16.9 % (gaze 3
    95.6 %); 100 % of measured points within 1 mm of Position. Caveats:
    natural correspondence and natural identity are not established;
    Blender instance identity merges disconnected pieces (10, 110, 178);
    no 12-mm cross-gaze association occurred (the six cores are
    disjoint); the controller has not yet serviced the seeds; none of the
    six NB1c gaze centres lies inside the historical FSG6f yaw ±25°,
    pitch ±20° chart.
- North Star after NS1a (Luiz and Chat).
  - Frozen North-Star seed handoff: the NS1a seed set, 13 initialized
    persistent entities, 302,936 surfels.
  - NS1b: prove a recentered local-controller handoff for one
    deterministically selected NS1a entity; allow the accepted local
    policy to select one post-bootstrap fixation; execute exactly that one
    action using PERFECT correspondence; fuse the new metric result back
    into canonical H0.
  - NS1b uses a TEMPORARY POLICY COORDINATE CHART. It is NOT physical
    head motion. The physical head remains fixed. Persistent scene
    geometry remains authoritative in canonical H0. No controller
    thresholds or FSG6f numerical rules are changed.
  - NS1b: Recentered Controller Handoff is ACCEPTED as Outcome 1. A
    persistent entity seed produced by the global RGB bootstrap can be
    handed to the unchanged accepted FSG6f -> Cyclopean / Controller-02
    semantics through a temporary local POLICY COORDINATE CHART while all
    physical sensing and persistent geometry remain in canonical H0.
    Deterministic target 172 (initialization H0 gaze (−156.25°, +28.75°)):
    local action (0°, −5°) -> H0 (−155.008°, +33.636°), gate admissible
    (novel support 12); one fixed-head 4096-spp observation; 64,437
    PERFECT correspondences, 18,525 target points; the map grew from
    12,072 to 21,243 surfels (9,354 matched, median 1.50 mm; 9,171 new):
    the first genuine North-Star 12-mm overlap. Post-action ACTIONABLE,
    next local proposal (−5°, −10°), NOT executed. POLICY CHART C IS NOT
    PHYSICAL HEAD MOTION. Limitations retained: PERFECT correspondence
    and identity are oracle aids; one entity serviced; the multi-part
    oracle identities 10, 110, 178 are unresolved; the controller
    observation state supports less than the North-Star measurement
    (4,118 vs 12,072 points at the initialization look).
- North Star after NS1b (Luiz and Chat).
  - Bootstrap-to-controller bridge: ESTABLISHED.
  - NS1c (next): coherent multi-entity control, first scene switch. It
    continues from the ACTUAL accepted NS1b state (current target 172;
    map 21,243 surfels; 2 own looks; visited local gazes (0, 0),
    (0, −5); next accepted proposal (−5, −10)). The accepted scheduler
    and per-entity recentered local controllers service the current
    entity, then switch autonomously to another coherent seed and
    execute one controller-selected observation there; the experiment
    stops after the first action on a target other than 172.
  - The scene-level experiment operates only on entities that were
    single-patch persistent seeds in the frozen NS1a handoff. The
    multi-part oracle identities 10, 110, 178 remain DEFERRED.
  - Physical head fixed; one fixed policy chart per entity; no threshold,
    scheduler or watchdog change; no SCENE_CLOSED claim.
- Classroom validation, Tabletop transfer and Natural Bootstrap-2 follow.
  - Tabletop transfer uses the same controller and bootstrap policy, with no
    scene-specific retuning unless execution is impossible.
  - Natural Bootstrap-2 (identity persistence) is a separate later problem.

For future behavior-preserving refactoring, the standing rule remains:

    migrate behavior first; redesign structure second

## Repository layout

- `fov3d/` is the reusable conceptual implementation. New architecture is organized
  around its stable concepts, not around historical experiment lineage.
- The `tools/` root holds only the sealed compatibility engine: the 16 modules that
  `fov3d` re-exports (`docs/consolidation/consolidation-3-layout.json`). It is a
  compatibility baseline where the current contracts say it is sealed.
- Other tools live in stage/topic directories: `tools/<stage>/`.
- Documentation lives in `docs/<stage>/`. `docs/chat-handoff.md` is the fixed recovery
  entry point.
- `scripts/` holds the stable top-level entry points.

## Checks and acceptance criteria

A step contract should state:

- what is being changed;
- what is deliberately not being changed;
- commands to run;
- cost class of each command;
- expected checks;
- acceptance criteria;
- stop conditions;
- scope of permitted fixes;
- exactly which results must be recorded.

Acceptance criteria are declared before evaluation whenever tuning against the result
would compromise the experiment.

Checks must not be modified merely to make a failing implementation pass.

If the implementation and the check disagree, diagnose the cause first.

## Standing defaults and precedence

Unless a step contract explicitly says otherwise:

- Claude Code has standing permission to commit and push step results and delegated
  fixes to the active branch. Work outside that scope requires Luiz.
- If the contract does not state a scope of permitted fixes, the default is **no
  fixes**: diagnose, report, and stop.
- Contracts and reports follow the convention `docs/<stage>/<phase>-contract.md` and
  `docs/<stage>/<phase>-report.md`. Historical documents keep their existing names.
- If the active branch is not named by the instruction or contract, ask rather than
  infer it from the current checkout.
- An overnight command runs only when the step contract explicitly authorizes it and
  gives its justification; otherwise ask Luiz first.

`CLAUDE.md` supplies the standing project rules. A step contract may specialize
those rules but may not contradict them. Only an explicit decision by Luiz may
override `CLAUDE.md`. If a conflict exists, stop and report it.

## Workstation fixes

Claude Code may repair an implementation defect when the step contract clearly
delegates that class of repair.

A repair must:

- be minimal;
- stay outside the acceptance criterion itself;
- be described explicitly;
- preserve the scientific intent;
- be committed;
- be distinguishable from the original proposed change when that distinction matters.

If the required repair changes architecture, scientific assumptions, thresholds,
evaluation semantics, or experiment design, stop and return the decision to Luiz and
Chat.

## Environment conventions

- Metres.
- The head is fixed; eyes rotate about their own centres.
- `EYE` is a Blender camera object: local -Z is gaze, local +Y is head up.
- Equirect `(u,v)` to EYE-frame direction:

      lon = (u - 0.5) * 2*pi
      lat = (0.5 - v) * pi

  with `v = 0` at the top row.

- Epipolar `(theta, phi)` of a head-frame direction:
  `theta` is measured from +X (the baseline);
  `phi = atan2(d_y, -d_z)` about X.
  Corresponding directions share `phi`;
  parallax `theta_R - theta_L > 0`.

- Python should remain plain and typed where useful. Avoid framework machinery unless
  it solves a demonstrated problem.

## Two interpreters

The two Python environments are not interchangeable.

Scripts run by:

    blender -b -P

use Blender's bundled Python and may assume only packages actually available there.

Host-side scripts use the repository `.venv`.

Do not infer that an import is valid in Blender because it works in the host
environment, or vice versa.

`blender -b -P` may exit successfully even when a Python script reports a failure.
Any Blender-side tool producing an artifact must make its own failure observable and
must cause a nonzero process result when appropriate.

## Cost classes

Commands belong to one of three cost classes:

- **Interactive** — under roughly 10 seconds.
  Normal development loop: checks, single fixations, small deterministic tests.

- **Batch** — under roughly 5 minutes.
  Run when scientifically or structurally justified.

- **Overnight** — longer work.
  Must be explicitly justified before execution and its durable result retained.

Develop and debug on the cheapest configuration that preserves the relevant behavior.
Run expensive/full configurations only when they produce a result that will actually
be reported or used.

## Repository as source of truth

A new Chat conversation should reconstruct the project from the repository and the
committed phase reports, not rely solely on conversational memory.

Conversation summaries are useful handoffs but are secondary sources.

### Chat Handoff at accepted main milestones

At every accepted `main` milestone, maintain the compact **Chat Handoff**,
`docs/chat-handoff.md`. It should be short enough to scan at the start of a fresh
conversation and record at least:

- the accepted `main` commit;
- the accepted scientific/architectural state;
- the active next step;
- decision-critical open items.

The Chat Handoff is a recovery index, not a competing source of truth. Repository code,
contracts, committed reports, and measured artifacts remain authoritative; the handoff
points a new conversation to that durable state.

Important scientific or architectural information learned only in chat should be
promoted into an appropriate committed document when it becomes part of the project
state.

Each completed phase should leave enough committed evidence that another session can
recover:

- the question;
- the contract;
- the implementation;
- the checks;
- the measured result;
- the conclusion;
- the next open question.

## Reports

Claude Code should commit a report for every substantial executed phase.

The report should include:

- exact branch and relevant commit ids;
- commands actually run;
- summary lines verbatim where useful;
- every failing gate that affected the work;
- measured numbers and the files/runs they came from;
- implementation repairs and why they were required;
- deviations from the original proposal;
- whether the acceptance condition passed;
- unresolved decisions.

Chat should review the committed report and relevant diff rather than rely on a
second-hand paraphrase when GitHub access is available.

## Generated artifacts

Regenerable renders, previews, `.blend` outputs, caches, and similar products should
not be committed unless a specific contract declares them durable reference assets.

Two gitignored trees hold generated artifacts (`docs/methodology/preview-visual-policy.md`):

- `./previews/`: machine-facing experimental memory. It holds the current stage's run evidence,
  is kept for the life of that stage, and is disposable afterwards. New previews go here, never
  into an external archive.
- `./visuals/`: human-facing scientific memory, persistent for the whole project and
  generated by Git-tracked tools.

Git holds the durable record: code, contracts, reports, numerical summaries,
provenance, hashes, regeneration commands and acceptance decisions.

If a command cheaply regenerates an artifact, the command and source data are the
durable record.

Large or expensive reference assets must be identified by provenance and checksum,
and stored according to the scene/asset policy of the repository.

## Final principle

The working process should optimize for:

    clear scientific decisions
    + reproducible behavior
    + cheap recovery
    + explicit authority
    + minimal human file shuffling

GitHub carries state.

Claude Code mutates the repository and measures on the workstation.

Chat designs and reviews.

Luiz decides.
