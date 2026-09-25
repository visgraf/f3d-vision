# Partition-Graph Phase 5 — Unified Head-Centred Evidence and Challenge States

## Why Phase 5 exists

Phase 4 showed that the relation model is now useful, but the eye-ray evidence raster and the head-centred partition were not expressed in the same chart. The most visible symptom was the apparent `TARGET_DEPTH_VALID` signal inside true gaps: every such cell disappeared when the same valid points were projected from saved `xyz_h` at the head origin. Phase 4 also showed that genuinely unresolved causal-final gaps are almost absent in the accepted golden run.

Phase 5 therefore remains **representation and retrospective analysis only**. It does not implement a gaze policy.

Its scientific question is:

> If every binocular-valid local 3-D sample, including non-target instances that the historical controller measured but did not persist as object geometry, is accumulated in the same head-centred spherical chart as the partition, which own-support gaps remain genuinely unresolved at historical prefixes?

This tests whether a future graph controller needs another saccade, or whether the information was already locally available but discarded by the old representation.

## 1. Controller-time incidental 3-D is allowed evidence

The accepted Oracle-1 patch stores `xyz_h`, `valid`, and left `instance_id` immediately after the local perfect matcher and before target-only fusion. `xyz_h` contains valid geometry for **all** binocular-valid same-instance pixels, not just the current target. Phase 5 reads that saved patch; it never re-runs the matcher.

This evidence is controller-time local measurement. It is distinct from dense evaluation truth and from a later object map.

Object identity is still inherited from Oracle-1 and must be stated as such.

## 2. One coordinate system

Every valid patch point is projected by its head-frame direction:

```text
xyz_h -> head-origin unit direction -> 0.1 degree spherical chart
```

No left-eye ray is used for the Phase-5 depth evidence. Therefore the chart shares the same origin as the object-support partition. The Phase-4 left-eye evidence remains historical evidence, but it is not used to claim depth inside a head-centred gap.

Hard invariant for the accepted run:

```text
head-origin valid TARGET depth in true own-support-gap cells == 0
```

A violation is a hard failure.

## 3. Incidental non-target memory

For each target history, Phase 5 accumulates:

- whether a chart cell has any binocular-valid 3-D sample;
- whether it has target or non-target depth;
- the nearest measured instance id and range;
- whether more than one instance identity has occupied the same chart cell over the history;
- number of valid depth samples.

This is a retrospective model of information that *could have been persisted* by the architecture. It does not claim that Oracle-1's historical controller actually persisted or reasoned over it.

## 4. True-gap evidence classes

Only `own_support_gap` relations are candidates for unresolved geometry. For corridor cells outside the target's own support, use the following exclusive descriptive classes:

1. `MAPPED_OTHER`: the causal joint partition is already owned by another reconstructed object;
2. `INCIDENTAL_OTHER_DEPTH`: no mapped other object owns the cell, but a controller-time valid non-target 3-D sample projects there;
3. `AMBIGUOUS_DEPTH_INSTANCE`: valid 3-D samples from different inherited instance identities accumulated at the same head-centred cell;
4. `SEEN_NO_HEAD_DEPTH`: the exact historical `seen_any` says the cell was sampled, but no valid head-centred 3-D sample is retained there;
5. `UNSEEN`: no historical supported-core sample reached the cell.

`TARGET_SUPPORT` is not a true-gap class; true gap cells are defined as the corridor interior outside the target's own support.

Mapped or incidental other-object depth is **not automatically an occlusion verdict**. It is evidence that another measured surface occupies that angular territory.

## 5. Reconstruction status of observed instances

For every non-target instance id measured in a true gap, Phase 5 records whether that instance is:

- `mapped_now`: already present in the causal joint graph;
- `targeted_later`: one of the accepted Oracle-1 targets but not reconstructed yet at this state;
- `never_targeted`: observed locally but absent from the Oracle-1 target list.

This makes explicit a key architectural distinction: **locally measured object evidence can precede object-level reconstruction**.

## 6. Challenge set

Phase 5 does not invent a new scene or perturb the accepted run. It uses the valid historical prefixes already stored in the 104-fixation run.

A challenge relation is an `own_support_gap` with at least one true-gap cell in one of:

```text
AMBIGUOUS_DEPTH_INSTANCE
SEEN_NO_HEAD_DEPTH
UNSEEN
```

This is a categorical unresolved-information definition, not a score or policy threshold.

The output contains:

- `challenge-relations.json`: every unresolved relation across all historical prefixes;
- `challenge-states.json`: the earliest unresolved state per target, a deterministic compact test set.

If the set is empty or scientifically too small, the correct conclusion is that the golden Classroom trajectory is unsuitable for testing graph-level attention. Do not manufacture a policy result.

## 7. Truth-isolation contract

Phase 5 may read from the source run only:

- `manifest.json`;
- `bootstrap/seeds.json`;
- `maps/fix_XX.npz`;
- `patches/fix_XX.npz`.

It may read Phase-4 lift/analysis outputs. It must not open evaluation truth, `oracle_observation.npz`, EXR, benchmark RGB, Blender files, or execute the matcher/controller/fusion/renderer.

## 8. Acceptance

Phase 5 passes only if:

- checkers 1–5 pass;
- baseline verifier and facade checker pass;
- golden smoke remains `MISMATCHES 0`;
- the accepted full source remains `MISMATCHES 0`;
- all 104 historical states are analyzed;
- Phase-4 `seen_any` and target-depth invariants remain clean;
- head-origin target depth in true gaps is exactly zero;
- no forbidden path is read;
- object identity is explicitly inherited;
- no controller/gaze/termination behavior changes;
- the report states whether the resulting challenge set is large/diverse enough for a later attention experiment.

Phase 5 still does **not** choose a gaze.
