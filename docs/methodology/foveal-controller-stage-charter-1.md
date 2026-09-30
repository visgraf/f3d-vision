# Foveal Controller Stage Charter 1

**Status.** ACCEPTED by Luiz and Chat (signed 2026-09-29). Marker:

    FOVEAL_CONTROLLER_STAGE_CHARTER_1_ACCEPTED

This is a pure architectural and scientific-direction decision:
- it executes no experiment;
- it changes no code, threshold or scientific behavior;
- it implements none of the steps it describes.

It closes the Controller-01 investigation and governs the next work of the Integrated Foveal Controller
stage. It was recorded from `main` @ `8ed8eef` (Controller-01C accepted). Each future step still needs
its own contract, checks and acceptance.

The signed direction, in one list:

    stop polishing the local controller;
    let the scene loop finish;
    defer residue;
    allow one strict final look;
    discover objects perceptually;
    test another scene;
    use visuals as a scientific language.

## 1. Controller-01 is the good-enough baseline

Controller-01 is accepted and **frozen** as the current **good-enough** integrated-controller baseline.

"Frozen" means:
- no automatic effort to perfect its local policy;
- known limitations are documented rather than immediately repaired;
- it remains available as an accepted baseline for later comparison;
- it may be revisited only by an explicit future scientific decision.

The controller is not claimed optimal or complete. The adequacy criterion is architectural and
scientific:
- it sustains coherent active scene exploration;
- it accumulates useful persistent geometry and evidence;
- cross-object evidence can reactivate objects;
- local unresolved cases are exposed rather than hidden;
- one difficult object should not dominate the whole scene loop;
- the mechanism is suitable as infrastructure for broader perceptual questions.

**Evidence record.** These accepted, measured results are the basis for the freeze. Details are in the
reports under `docs/controller/`.
- **Controller-01** (`e3bf5e0`):
  - 25 localized objects, 141 observations;
  - 2 natural reactivations, each triggered by another object's measurements, and both serviced;
  - 24 objects quiet at termination;
  - object 210 `wall.008` blocked by the inherited 24-look watchdog;
  - terminal outcome `INCOMPLETE`.
- **Controller-01A** (`657388c`): later cross-object evidence did not make 210 quiet. Sticky BLOCKED is not
  the explanation; the unresolved behavior lies inside the accepted local continuation.
- **Controller-01B** (`f90d738`): one continuation look for 210 added 0 new surfels. FSG6f's stop followed
  its frontier window moving with the gaze, and the previous window still held its 52 OPEN points.
- **Controller-01C** (`bbc37b8`): the FSG6f fixation did not service the frontier that requested it.
  - 0 of 30 OPEN support elements were inside either eye's depth-measuring core;
  - 0 of 30 were measured;
  - 30 of 30 remained OPEN.

  FSG6f takes a fixed 5° step toward the support direction rather than aiming the depth core at the
  support.

**Known Controller-01 limitation** (established by Controller-01C): FSG6f action selection does not
guarantee that the unresolved frontier support motivating an action enters the binocular
depth-measuring core. This limitation is known and localized. **This charter does not repair it.**

## 2. General loop policy

The next controller generation adopts this architecture:

    NORMAL SCENE LOOP
        ->
    DEFER difficult local residue
        ->
    continue servicing the rest of the scene
        ->
    ordinary work exhausted
        ->
    FINAL RESIDUE PASS
        ->
    at most one strictly justified final observation per unresolved object
        ->
    SCENE CLOSED

Core semantic principle:

    local unresolved != global failure

A locally difficult object must not permanently prevent the scene loop from terminating.

A state such as `DEFERRED` / `RESIDUAL` is introduced **conceptually, not yet in code**. The exact name
is not fixed by this charter.

The scene may close honestly with residual objects, for example:

    SCENE_CLOSED
        quiet objects: ...
        residual objects: ...

False "complete" labels are not required.

## 3. Final residue probe

The final pass is conservative.
- An unresolved object receives **at most one** final observation.
- After that observation, the scene closes whether or not the object becomes locally quiet.
- The final observation must be **more strictly justified** than ordinary ACTIONABLE status.

The minimum accepted principle, from Controller-01C: the unresolved support that motivates the
observation must actually be placed inside the binocular depth-measuring support/core.

Conceptually:

    unresolved support
        AND
    proposed gaze geometrically services that support
        AND
    support is not already geometrically resolved
        AND
    observation is not effectively redundant

The exact predicate is deliberately **not** optimized in this charter. Controller-02 will implement the
simplest defensible version (Back to Occam).

## 4. The Blender object list is to be retired as controller input

The current Blender instance catalog was a useful controlled bootstrap device. But a Blender scene
graph is an authoring representation, and it must not be assumed to equal natural perceptual
segmentation.

The project will therefore move toward:

    low-resolution sensory observation
        ->
    perceptual decomposition
        ->
    temporary object hypotheses
        ->
    seed gaze per hypothesis
        ->
    active foveal controller

Blender object identity should eventually move to **REFERENCE / EVALUATION** rather than controller
initialization. It is **not** removed by this charter.

## 5. Natural Bootstrap-1

The first natural-bootstrap experiment asks:

    Can a broad low-resolution observation discover a useful initial set
    of perceptual regions and seed fixations?

The first version stays deliberately modest.
- **No semantic classification is required.**
- It prefers simple perceptual evidence: coarse RGB continuity, coarse depth continuity, depth
  discontinuities, and connectedness / region coherence.
- Its output hypotheses need only provide, approximately: a temporary perceptual identity, angular
  support, coarse depth, a representative seed gaze, and an optional confidence.
- Over-segmentation is acceptable.

The bootstrap produces **hypotheses, not ground-truth objects**.

## 6. Natural Bootstrap-2 is a separate future question

Discovery and identity persistence are **not** silently combined:
- **Natural Bootstrap-1** discovers the initial perceptual hypotheses without Blender's object list.
- **Natural Bootstrap-2** maintains and revises perceptual identities through later foveated
  observations, without relying on Blender instance IDs.

This separation is deliberate. Persistent causal evidence remains primary; object interpretation may
eventually become revisable. Possible future phenomena include split, merge, newly discovered entity,
occluded continuation, part versus whole, and background. **None is implemented now.**

## 7. Generality test: leave Classroom

After Natural Bootstrap-1 works well enough to run the integrated loop, another scene is tested. The
signed next scene is **Tabletop**. Classroom and Tabletop should exercise different conditions.

**Do not retune the controller between Classroom and Tabletop.** Use the same controller parameters and
policy, unless a failure prevents execution entirely.

The purpose is generality, not benchmark optimization. A Tabletop failure is an informative scientific
result.

## 8. Visual Language 1

Visual Language 1 is a near-term methodological activity. It is **not** a graphic-design exercise. Its
purpose is to keep visual semantics stable across experiments and scenes.

The visual language should eventually distinguish, consistently:
- current attention;
- current fixation;
- unresolved support;
- new measurement, new spatial support and repeated measurement;
- persistent geometry;
- residual object;
- controller-time data, derived visualization, and reference / evaluation.

It must preserve these scientific distinctions visually:

    measurement != new geometry
    visible != depth measured
    actionable != worth one final observation
    residual != failure

No large visual redesign is implemented by this charter. The non-blocking style guidance recorded with
the Controller-01 visual package is an input.

## 9. Signed near-term roadmap

    Controller-01C
        accepted frontier/action correspondence audit
            ->
    FREEZE Controller-01
        good-enough baseline
            ->
    Controller-02
        normal loop
        + deferred residue
        + one strict final residue probe
            ->
    Visual Language 1
            ->
    Natural Bootstrap-1
        low-resolution perceptual discovery
            ->
    Classroom validation
            ->
    Tabletop transfer
        same controller, no scene-specific retuning
            ->
    Natural Bootstrap-2
        remove remaining oracle instance identity

This roadmap is directional. Each scientific step still follows **Bounded Boldness**: one causal
question per executed experiment.

## What this charter does not do

- It does not implement Controller-02.
- It does not repair FSG6f or change any accepted local policy, threshold, scheduler, watchdog or
  stopping rule.
- It does not implement Natural Bootstrap-1 or -2, and it does not remove the Blender instance catalog.
- It executes no new scientific observation.
- It does not redesign the visuals.

The next activity is the architectural design and contract of Controller-02.
