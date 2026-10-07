# Historical README — pre-playground project state

This document preserves the repository root README from the migration / Integrated Foveal Controller phase, as it
stood at `main` `3f92ac314bbb1f0c0bfac25c9ca6bd55bb129b0f` (Greedy Foveal Explorer v0 closure). It is retained as project
history and does not describe the current repository baseline. For the current project entry point, see the root
[`README.md`](../../README.md).

The preserved text below is verbatim; it has not been updated to agree with the present state.

---

# Foveal Stereo Vision

## Migration and Refactoring

This repository has completed a behavior-preserving migration and conceptual
refactoring of the experimental Foveal Stereo Vision system.

The work began from a sealed historical implementation whose behavior had been
established through the Classroom and Partition-Graph experiments. The purpose of
the migration was not to invent a new algorithm, but to recover the reusable
conceptual architecture that had gradually become embedded in experiment-specific
code.

The migration followed two principles:

    migrate behavior first; redesign structure second

and

    one causal question per conceptual step

Conceptual Cores 1–11 established reusable ownership for the principal mechanisms
under `fov3d/`, including persistent instance-keyed 3-D measurement memory, the
fixed-head spherical chart, persistent head-centered epistemic memory, scene
partition/topology, and the intrinsic epistemic partition.

Conceptual Cores 12–14 then separated three concepts that had historically been
mixed into the epistemic representation:

- candidate interpretation;
- prerecorded experiment/run context;
- fixation/action history.

The resulting conceptual stack is:

    measured 3-D geometry
            ↓
    persistent head-centered evidence
            ↓
    scene geometry / topology
            ↓
    intrinsic epistemic partition
            ↓
    optional gaze/action context
            ↓
    optional experiment run context
            ↓
    candidate interpretation

The intrinsic epistemic partition now represents accumulated causal evidence in
the spherical head-centered domain without depending on candidate policy, future
experiment scheduling, or fixation history. It remains intentionally
target-relative: target support, target evidence and distance-to-target are defined
with respect to one designated object.

The migration is accepted through Conceptual Core 14. Its established scientific
behavior was preserved throughout the redesign against the sealed reference
experiments, including the accepted baseline and golden behavioral comparisons.

The conceptual-core migration pauses here.

## Next Stage — Integrated Foveal Controller

The next stage is a fresh architectural design of the Integrated Foveal Controller
built on the representation established by the migration.

The central question is no longer how to recover structure from the historical
experiments, but how an active binocular observer should use that structure to
decide what to do next.

The controller design will begin from explicit definitions of:

    STATE
        persistent scene / object memory
        + intrinsic epistemic representation
        + observer history
        + current attentional context

    ACTION
        retain or switch the attended object
        + choose the next fixation direction
        + choose vergence / focus
        + continue, stop or change attentional mode

The initial design retains the current fixed-head, static-scene setting and follows
the project's principles of Back to Occam and Bounded Boldness: start with the
simplest coherent closed-loop controller that can be tested causally, then increase
complexity only when the evidence requires it.

The immediate architectural question is:

    given what the system currently knows,
    what should the eyes do next?

Current status: Integrated Foveal Controller 01 is accepted and frozen as the
good-enough baseline, with its audits 01A, 01B and 01C. Foveal Controller Stage
Charter 1 (`docs/methodology/foveal-controller-stage-charter-1.md`) sets the next
steps: Controller-02 loop semantics (deferred residue and one strict final look),
Visual Language 1, natural perceptual bootstrap without the Blender object list, and
a Tabletop transfer test with the same controller.
