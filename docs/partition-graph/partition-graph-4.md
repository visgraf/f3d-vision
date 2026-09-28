# Partition-Graph Phase 4 — Typed Gap Relations and Local Epistemic Evidence

## Why Phase 4 exists

Phase 3 established three facts that change the architectural picture.

1. The joint spherical partition is now topologically faithful at the raster level: every cell-side interface is represented, and the old Phase-2 edge-less BASE cases disappear.
2. A local corridor is more discriminative than the shared-BASE query. On the 30 Phase-2-comparable disconnected-component pairs, the causal relation split into 12 pure-BASE, 5 pure-other-object, and 13 mixed cases instead of 30/30 identical shared-BASE cases.
3. `seen_any` is too coarse for the next decision. It is saturated on almost every causal bridge: 29/30 are fully seen. Depth order, however, already separates some qualitatively different cases.

Phase 4 therefore does **not** implement a new gaze policy. It turns the Phase-3 measurements into a first-class relation model and replays a finer, still controller-time epistemic signal from artifacts that already exist in the accepted Oracle-1 run.

The scientific question is:

> **After separating frontmost-ownership cuts from genuine gaps in an object's own reconstructed support, and after adding local target-depth evidence and depth-order descriptors, which disconnected-object relations remain genuinely unresolved by the historical observations?**

The answer should tell us whether Phase 5 is ready to design graph-level attention, or whether one more representation refinement is needed.

## 1. Fix topology lineage first

Phase 3 found a real implementation defect: `_lineage` compared state-wide region codes with a target-only component raster labelled `1..k`. This made stable components appear as simultaneous births and deaths.

Phase 4 fixes `_lineage` so previous and current component rasters are compared in the **same target-local label space**. It becomes a checked invariant.

For the unchanged accepted full Classroom run, the corrected totals must reproduce the independently audited Phase-3 values:

- joint/frontmost target components: births 10, merges 3, splits 0, deaths 1;
- target own-support components: births 7, merges 2, splits 0, deaths 0.

These are regression expectations for the frozen golden source run, not parameters of a new policy.

## 2. Make relation origin first-class

Every local corridor between two disconnected joint components of one object receives exactly one origin label.

### `ownership_cut`

The two joint components belong to the **same connected component of the target's own support**. Their separation exists only because a nearer reconstructed object won some overlapping angular cells in the frontmost joint partition.

This is a partition/ownership phenomenon, not a missing-support gap.

### `own_support_gap`

The two joint components lie in **different connected components of the target's own reconstructed support**. The target map itself is disconnected across this relation.

This distinction is purely retrospective geometry over already reconstructed maps. It does not assert physical occlusion, continuation, or object identity beyond the inherited Oracle-1 identity.

## 3. Ownership margin and depth-order descriptors

Phase 4 adds quantitative descriptors, not a hard occlusion classifier.

### Ownership margin

Where the corridor passes through another object's frontmost cells **and** the target's own 12 mm support also exists there, define

```text
ownership_margin = target_reconstructed_range - frontmost_owner_range
```

A positive margin means the winning owner is reconstructed closer than the target at that angular cell.

Report:

- sample count;
- minimum / median / P90 margin in metres;
- median margin divided by the already-frozen 12 mm fusion radius;
- fraction of samples whose margin exceeds 12 mm.

No new numerical threshold is introduced.

### Boundary depth order

For every intervening reconstructed object that shares an object-object boundary with the target, aggregate the existing Phase-3 boundary attributes:

- total interface-edge votes;
- target-nearer votes;
- intervener-nearer votes;
- intervener-nearer vote fraction;
- absolute vote-balance confidence `abs(a-b)/(a+b)`;
- interface-weighted depth-jump statistics.

These are descriptive confidence measures. Phase 4 must not convert them into an automatic `OCCLUSION` label.

## 4. Finer epistemic replay without opening hidden truth

`seen_any` says only whether either eye geometrically sampled a chart cell. Phase 4 adds a finer cumulative evidence overlay using the already-saved **controller-time local patch** for each completed fixation.

Allowed new source artifact:

```text
objects/instance_XXXX/patches/fix_YY.npz
```

The patch was written by Oracle-1 immediately after the local perfect matcher and before the next gaze was selected. It contains the local record actually available to the controller-time pipeline: left-core instance id, binocular-valid depth mask, and local XYZ/range. It is not dense future scene truth.

Phase 4 must still never open:

- `bootstrap/evaluation_only/*`;
- `reachable_samples.npz`;
- `evaluation.json`;
- `oracle_observation.npz`;
- any EXR;
- the Blender scene.

Using saved calibration plus the deterministic stereo support geometry, replay these cumulative chart masks per target:

- exact two-eye `seen_any` from Phase 3;
- `left_target_seen`;
- `left_nontarget_seen`;
- `target_depth_valid`.

`target_depth_valid` is especially useful because the historical epistemic module generated it from the left target pixels whose local oracle stereo result was valid. Therefore every saved Cyclopean audit checkpoint provides a hard validation:

```text
replayed target_depth_valid cell count
== historical OBSERVED_TARGET_WITH_DEPTH
```

The Phase-3 hard gate remains as well:

```text
replayed NEVER_OBSERVED
== historical NEVER_OBSERVED
```

Both must have zero mismatches.

The left-only target/nontarget masks are explicitly labelled as left-derived subsets; they are **not** claimed to reproduce the historical two-eye `seen_target` / `seen_nontarget` masks.

## 5. Mutually exclusive evidence classes for display and corridor accounting

For each chart cell, use the following precedence solely to create a readable mutually-exclusive diagnostic raster:

1. `TARGET_DEPTH_VALID`
2. `LEFT_MIXED_NO_DEPTH`
3. `LEFT_TARGET_NO_DEPTH`
4. `LEFT_NONTARGET_ONLY`
5. `SEEN_NO_LEFT_ID_EVIDENCE`
6. `UNSEEN`

The underlying boolean masks are preserved separately. A class therefore never erases the underlying evidence history.

Each corridor reports counts and fractions for these six classes.

This is intentionally finer than `seen_any` while remaining within the accepted controller-time artifact scope.

## 6. Phase-4 relation record

Each relation record retains the Phase-3 corridor fields and adds:

```text
relation_origin: ownership_cut | own_support_gap
own_support_component_a
own_support_component_b

evidence_class_counts
evidence_class_fractions

ownership_margin: {...}
boundary_depth_order: {
    intervener_id: {...}
}
```

The record must also preserve:

- causal object-final vs scene-final context;
- target id and endpoint region ids;
- gap angle and corridor cells;
- BASE / same-object / other-object occupancy;
- exact historical seen/unseen composition.

## 7. Analysis levels

Phase 4 reports three complementary sets.

### A. Every historical state

Annotate the current target's Phase-3 joint-component corridors at all 104 historical states. This supports a sequential demo and topology/evidence evolution.

### B. Causal object-final

For each target at its own historical termination, characterize all current relations using only objects reconstructed up to that time and that target's own accumulated evidence.

This is the main controller-time scientific view.

### C. Scene-final

Re-evaluate the same object relations in the final all-object partition. This is retrospective only. It may reveal later-reconstructed interveners and must never be presented as information available to the earlier controller.

## 8. Required scientific summaries

At minimum report:

- counts of `ownership_cut` vs `own_support_gap`;
- for `own_support_gap`, occupancy classes: pure BASE / pure other-object / mixed;
- fine evidence composition of those classes;
- how many causal gaps have target-depth-valid evidence somewhere in the corridor;
- how many are fully seen but have no target-depth-valid evidence;
- how many remain partly or wholly unseen;
- depth-order / ownership-margin distributions by relation origin;
- examples selected by explicit graph/evidence quantities, not visual cherry-picking;
- how many causal relations change interpretation in scene-final context because a later object occupies their corridor.

Do **not** introduce a success score, attention priority, or gaze recommendation in Phase 4.

## 9. Demo contract

Produce a 104-frame sequential demo, positive pitch up, with four synchronized panels:

1. joint frontmost partition;
2. current target components and every corridor, with `ownership_cut` and `own_support_gap` visually distinct;
3. fine epistemic class raster with an explicit key;
4. relation diagnostics for the current state: origin, occupancy, target-depth evidence, and depth-order / margin summaries.

Also produce:

- MP4;
- overview with one representative frame per target;
- `Demo.md` explaining that the visualization is retrospective analysis, not a new controller.

## 10. Truth isolation and read-path contract

The Phase-4 analyzer may read from the accepted source run only:

- `manifest.json`;
- `bootstrap/seeds.json`;
- `acquisitions/fix_XX/calibration.json`;
- `maps/fix_XX.npz`;
- `patches/fix_XX.npz`.

It may also read Phase-4 lift outputs generated from those files.

Any source-run read of `evaluation_only`, `reachable_samples.npz`, `evaluation.json`, `oracle_observation.npz`, EXR, benchmark RGB, or Blender data is a hard failure.

The analyzer must remain post-hoc: no controller, matcher, fusion, renderer, or Blender execution.

## 11. Acceptance gates

Phase 4 passes only if all of the following hold:

- Phase-1/2/3/4 checkers pass;
- baseline verifier passes;
- facade checker passes;
- golden smoke remains `MISMATCHES 0`;
- reused full source run remains `MISMATCHES 0`;
- fixed Phase-3 lift produces 104 states;
- corrected joint lineage is exactly `{births:10, merges:3, splits:0, deaths:1}` on the golden full source;
- own-support lineage is exactly `{births:7, merges:2, splits:0, deaths:0}`;
- `NEVER_OBSERVED` replay has zero mismatches at every saved Cyclopean checkpoint;
- `OBSERVED_TARGET_WITH_DEPTH` replay has zero mismatches at every saved Cyclopean checkpoint;
- every relation has exactly one origin label;
- every `ownership_cut` endpoint pair maps to the same own-support component;
- every `own_support_gap` endpoint pair maps to different own-support components;
- no forbidden source-run path is opened;
- no sealed controller/matcher/fusion/rendering behavior, golden signature, or scene asset changes;
- scientific conclusions distinguish causal object-final from scene-final information.

Phase 4 is the final planned representation/evidence characterization before deciding whether to implement a graph-level attention policy.
