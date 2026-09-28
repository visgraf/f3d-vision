# Partition-Graph Phase 3 — Joint Scene Partition and Local Gap Corridors

## Why Phase 3 exists

Phase 2 established that the spherical partition is informative, but also exposed the first representation-level failure modes.

The important measured facts were:

- 9/25 final target maps had more than one spherical component;
- all 30 final disconnected-component pairs shared the same dominant exterior `BASE`, so the shared-BASE query was saturated and non-discriminative;
- the Phase-2 boundary extractor could omit a touching `BASE` region because it assigned one BASE label to a whole contour;
- foreground and complement both used 8-connectivity instead of a digital-topology dual;
- the displayed observation quad was much larger than the controller's actual rectified-core `seen_any` evidence;
- each Phase-2 graph contained only one target, so every other physical object was hidden inside `BASE`.

Phase 3 repairs those limitations **without changing the historical controller**.

Its scientific question is:

> **If all reconstructed objects known at a historical fixation are placed in one spherical partition, and disconnected parts of one object are related by a local bridge measured against the exact historical observation evidence, do the gaps acquire discriminative graph structure that the saturated exterior-BASE relation could not provide?**

This remains a retrospective representation experiment. It does not select a new gaze.

## 1. Causal joint partition

The Classroom Oracle processed objects sequentially. Phase 3 preserves that historical ordering.

At global fixation `g`, the joint state contains:

- the latest persistent map of every object already reconstructed by `g`;
- no map from a future object;
- the current target map at its current local fixation;
- all completed acquisition footprints up to `g`.

Each object's 3-D map is projected to the same 0.1-degree head-centred spherical chart using the unchanged 12 mm association footprint.

Where reconstructed object supports overlap angularly, the joint **frontmost analysis partition** assigns the chart cell to the object with the smallest reconstructed head-frame range. Exact equal-range ties are broken by instance id only for determinism. This is a representation convention over reconstructed geometry; it is not dense Blender truth.

Object identity is still inherited from Oracle-1. Phase 3 does not perform object discovery or semantic inference.

A second, scene-final graph is simply the last causal graph, after all 25 historical target runs have completed. It contains every object map that Oracle-1 reconstructed.

## 2. Digital topology and exact boundaries

Phase 3 uses a standard complementary-connectivity convention:

- object support components: **8-connected**;
- `BASE` complement components: **4-connected**.

This avoids declaring both diagonal foreground and diagonal background connected at the same time.

Boundaries are no longer assigned one BASE label per contour. Instead, every horizontal or vertical cell-side adjacency between two different partition regions is enumerated exactly once. Connected interface edges are then traced into `BoundaryChain` walks.

Therefore the lift records a hard diagnostic:

```text
raster_interface_edges == encoded_interface_edges
unencoded_interface_edges == 0
```

The boundary kind is:

- `OBJECT_BASE` for object/BASE interfaces;
- `OBJECT_OBJECT` for interfaces between reconstructed objects.

Object-object boundaries also record reconstructed range-jump statistics and which side is nearer more often. These are descriptive geometric attributes, not an automatic occlusion label.

## 3. Exact replay of historical `seen_any`

Phase 2 displayed the full tangent-plane quadrilateral. That was useful as acquisition geometry but was not the controller's epistemic raster.

Phase 3 reconstructs the old controller's actual `seen_any` geometry from each saved calibration:

1. call the consolidated `fov3d.stereo.core` facade for the same stereo rectification and support-mask geometry used by Oracle-1;
2. crop the same rectified core;
3. compute the same fixed-head direction for every supported core pixel;
4. round those directions onto the same 0.1-degree Cyclopean chart;
5. accumulate the left and right supported cells exactly as the historical epistemic module did.

No image, EXR, `oracle_observation.npz`, matcher output, instance-id raster, or dense evaluation truth is required for `seen_any`.

The replay is checked against the **saved controller decision record** already contained in `manifest.json`: whenever a historical `cyclopean_decision` stored `NEVER_OBSERVED`, Phase 3 requires

```text
replayed NEVER_OBSERVED == historical NEVER_OBSERVED
```

A mismatch is a hard failure. This check turns the exact-evidence claim into a measured invariant rather than an approximation.

The raw tangent polygons remain in the `ObservationOverlay` only as display/acquisition metadata and are explicitly marked display-only.

## 4. Local gap corridor

The Phase-2 shared-BASE relation became useless because almost every disconnected pair touched the same enormous exterior region.

Phase 3 replaces that query with a deliberately local relation.

For every pair of disconnected visible regions belonging to the same inherited object hypothesis:

1. find the closest pair of region-boundary cells;
2. draw the direct digital straight bridge between them;
3. inspect only the bridge interior.

The relation records:

- endpoint angular gap in degrees;
- number of interior bridge cells;
- how many bridge cells are `BASE`;
- how many belong to another reconstructed object, with per-object counts;
- whether the bridge crosses another component of the same object;
- how many bridge cells were historically `seen_any` versus unseen for that target.

This is a **measurement**, not a continuation rule. In particular:

- another object in the corridor does not automatically mean physical occlusion;
- unseen BASE does not automatically mean the object continues there;
- observed BASE does not automatically disprove continuation.

The point is to expose a local relation on which a later controller may reason.

## 5. Causal-final versus scene-final context

For each target, Phase 3 reports its corridor relations in two contexts.

### Causal object-final

The joint graph at the last fixation of that target's own historical run. Only objects reconstructed earlier in the Oracle sequence can appear as interveners.

### Scene-final

The final joint graph after all historical object runs. Later reconstructed objects may now explain chart territory that was still `BASE` when the target itself terminated.

Comparing these two contexts is retrospective and must not be presented as information the old controller possessed at the earlier time.

## 6. Topology events are lineage events, not component-count guesses

Phase 2 initially called an increase in component count a `split`; later audit showed all seven such events were actually births of new disconnected support.

Phase 3 tracks overlap of component cells from one local target state to the next and explicitly counts:

- birth: current component has no predecessor;
- merge: current component overlaps two or more predecessors;
- split: one predecessor overlaps two or more current components;
- death: predecessor overlaps no current component.

Initial components are reported but excluded from the aggregate event totals.

## 7. Truth isolation and allowed inputs

The scientific lift may read only the same controller-time run artifacts as Phase 2:

- `manifest.json`;
- `bootstrap/seeds.json`;
- saved `acquisitions/fix_XX/calibration.json` files;
- saved persistent `maps/fix_XX.npz` snapshots.

It must not open:

- `bootstrap/evaluation_only/*`;
- `reachable_samples.npz`;
- `evaluation.json`;
- EXR files;
- `oracle_observation.npz`;
- the Blender scene.

`manifest.json` contains the saved historical action/audit record. Those decision fields are used only to validate the replayed evidence counts, never to construct object support, choose a boundary, define a corridor, or select a gaze.

The only old-engine dependency newly exercised by the Phase-3 lift is the consolidated `fov3d.stereo.core` **geometry facade** for deterministic rectification/support masks. The controller, matcher, fusion, renderer, and Blender are never executed.

## 8. Required full experiment

Reuse the validated Phase-2 source run if present:

```text
previews/partition-graph-2-source-full
```

First re-run the committed comparator and require `MISMATCHES 0`.

Then write a new Phase-3 output tree with one joint graph per global historical fixation, exact controller-evidence state, local corridor records, a scene-final relation file, and a demo.

## 9. Demo contract

The synchronized four-panel demo shows:

1. joint frontmost spherical partition;
2. current target's connected components with **every** local corridor drawn;
3. exact replayed historical `seen_any` (`SEEN`/`UNSEEN` key shown explicitly);
4. joint dual/topology summary.

Chart orientation is conventional: positive pitch is up. The demo must not silently truncate the relation set; complete corridor records remain in JSON even when text is summarized visually.

## 10. Acceptance

Phase 3 passes only if all of the following hold:

- Phase-1, Phase-2 and Phase-3 structural checkers pass;
- baseline verifier passes;
- facade checker passes;
- golden smoke remains `MISMATCHES 0`;
- the reused/generated full source run remains `MISMATCHES 0`;
- 104 causal joint states are produced for the normal full run;
- exact `seen_any` replay has **zero mismatches** at every available historical Cyclopean audit checkpoint;
- every joint state's boundary diagnostic has `unencoded_interface_edges == 0`;
- no dense/evaluation truth path is read;
- object identity is explicitly reported as inherited;
- no controller, matcher, fusion, rendering, gaze, termination, golden signature, or scene asset is changed;
- scientific conclusions distinguish causal object-final from retrospective scene-final information.

Phase 3 is still representation and analysis. **No new gaze policy is to be implemented in this phase.**
