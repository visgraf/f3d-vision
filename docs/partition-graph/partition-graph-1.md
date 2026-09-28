# Partition-Graph Phase 1 — Representation Kernel

## Purpose

This phase begins the post-consolidation architecture.  It changes **representation only**.
It does not change the sealed Classroom-Oracle controller, FSG6f, Cyclopean eligibility,
stereo, fusion, rendering, gaze selection, or termination.

The architectural premise is that the Cyclopean domain should be treated as a partition of
the viewing sphere rather than primarily as a shoreline map.

Two partitions must remain distinct:

1. **Scene partition.** Connected faces corresponding to visible object components and the
   residual `BASE` complement.
2. **Observation overlay.** Spherical footprints of left/right/binocular fixations, carrying
   what territory was sampled.

`VOID` is intentionally **not** a physical scene-region type. A hole may be unobserved,
monocular, missing depth, occluded, or still assigned to base. Those are visibility or
knowledge states.

## Core representation

The representation is a coupled structure:

```text
3-D attributed geometry
        ↕
spherical partition faces
        ↕
embedded boundary chains  = primal boundary graph
        ↕
region adjacency          = dual graph
        ↕
object hypotheses grouping one or more disconnected faces

plus a separate observation/visibility overlay
```

A connected partition face is **not** synonymous with a physical object.  Multiple visible
faces may carry the same `object_id`.  This directly represents an object that disappears
behind an occluder and reappears elsewhere.

A `BoundaryChain` is stored primarily as chart-independent unit directions on the sphere.
It may additionally carry 3-D points, normals on both sides, depths on both sides, a relation
kind, and arbitrary attributes.  This is the bridge between topology and geometry.

The dual graph is derived from the boundary table rather than separately maintained: each
region is a dual node; each boundary creates one adjacency edge between its two incident
regions.

## Scope of Phase 1

Included:

- spherical coordinate utilities;
- partition-region and object-hypothesis data types;
- attributed 3-D/2-D boundary chains;
- derived dual adjacency;
- left/right/binocular observation footprints;
- strict invariants and portable JSON + NPZ serialization;
- synthetic occlusion/reappearance fixture;
- structural tests and a small representation demo.

Explicitly excluded:

- automatic segmentation;
- automatic object discovery;
- controller policy;
- graph scoring/ranking;
- completion rules;
- inference that two components are the same object;
- inference of occlusion direction from image data;
- use of Blender dense truth;
- modification of the sealed engine.

The synthetic fixture labels its relations by construction.  It is a software test, not a
scientific result.

## Acceptance contract

1. `scripts/verify_baseline.sh` passes before and after this phase.
2. `tools/dev/check_partition_graph1.py` reports zero failures.
3. The existing golden smoke still compares with `MISMATCHES 0`.
4. No file under the sealed implementation is edited to make Phase 1 work.
5. New architecture code lives under `fov3d/scene/` and imports no historical experiment
   module.
6. No controller behavior is added in this phase.

## Next phase

Phase 2 should be a **retrospective Classroom lift**: construct this representation from a
saved Classroom-Oracle run using only information that was available to the controller at the
corresponding time. Dense Blender truth, if used at all, belongs strictly to a later evaluator.
That experiment should answer whether the partition/dual-graph view exposes relationships that
were invisible to the old shoreline representation before any new gaze policy is designed.
