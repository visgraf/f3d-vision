# Controller-01 visual retrofit contract

## Status

This step **visualizes accepted measurements**. It is not a new scientific experiment. It changes
no controller behavior, no accepted artifact and no accepted result. It applies preview/visual
lifecycle Policy 1 (`docs/methodology/preview-visual-policy.md`) to the accepted Controller-01 run:
a Level-B visual package.

    base               origin/main @ a60d44856e8bdc3daf7709db53e411581b7bace2 (Policy 1 accepted)
    source run         /home/lvelho/rd/f3d-vision/previews/controller-01-full
                       (accepted Controller-01, report commit e3bf5e0; manifest d293a98f…,
                       actions 12cdbe4d…)
    source audit       /home/lvelho/rd/f3d-vision/previews/controller-01a-terminal-audit/audit.json
                       (accepted Controller-01A: CONTROLLER01A_FINAL_REPROBE_ACTIONABLE)
    branch             visuals/controller-01-retrofit (isolated worktree; not merged until Luiz
                       inspects the images and Chat reviews the generator and report)
    generator          tools/controller/visualize_controller01.py (Git-tracked)
    output             /home/lvelho/rd/f3d-vision/visuals/controller-01/ (gitignored)
    marker             CONTROLLER01_VISUAL_PACKAGE_COMPLETE

Everything here is PROPOSED until the generator runs.

## Package

    visuals/controller-01/
        overview.png                  primary Level-B visual: the Controller-01 story
        events/reactivation-0109.png  natural reactivation of 109 alphabet
        events/reactivation-0178.png  natural reactivation of 178 sol
        events/watchdog-0210.png      the object-210 watchdog block and the 01A terminal re-probe
        scene-final.png               the final reconstructed scene
        diagnostics/attention-timeline.png, diagnostics/gaze-chart.png   supplementary
        pointclouds/*.ply             active fused maps: the combined scene and objects 109, 178, 210
        visuals-manifest.json         checks, sources and file hashes

The diagnostic timeline and gaze chart are copied unchanged from the run. They are supplementary,
not the main scientific visual.

## Data and truth semantics

Only controller-time artifacts of the source run are read:
- `manifest.json` and `actions.json`, with their events;
- `bootstrap/seeds.json` and `bootstrap/instance_catalog.json`;
- per object: saved patches, map snapshots, `final_map.npz`, `final_effective_geometry.npz`,
  `result.json` (the probe records), the rectified RGB pairs (`benchmark/`), and the acquisitions
  (`calibration.json`, `oracle_observation.npz`) of the objects whose own context is
  reconstructed.

The 01A `audit.json` is read too. The generator runs under the Controller-01 truth firewall. It
never opens `evaluation.json` or `bootstrap/evaluation_only/`. **No reference/evaluation truth is
used.**

Every panel carries a label:
- **CONTROLLER-TIME**: data the controller had: saved observations, maps, measurement memory, logged
  probe records;
- **DERIVED**: computed afterwards from controller-time data with the accepted, unchanged functions.
  - The Cyclopean eligibility rasters are recomputed with the sealed Cyclopean helpers
    (`_map_support`, `_exterior_and_distance`, `_cells`), reached read-only through the facade's
    `_legacy_impl`.
  - The FSG6f frontier states come from `fov3d.control.frontier.extract_frontier` and
    `classify_frontier_state`.
  - Scene renderings are angular or oblique projections.

Geometry panels state which geometry they show, and do not mix them silently:
- **ACTIVE FUSED MAPS**;
- **EFFECTIVE CAUSAL GEOMETRY**: the active map plus the measurement memory;
- **MEASUREMENT MEMORY** (points added since a given step).

## Reconstruction (derived, validated)

- The global `InstanceMeasurementMemory` is replayed from the saved patches in global order. The
  memory up to step `s` is its append-only prefix with source step ≤ `s`.
- Active maps at a step are the saved own-look map snapshot `maps/fix_kk.npz` at that time.
- Own contexts of 109, 178 and 210 are rebuilt from their own saved acquisitions with the accepted
  matcher, as in Controller-01A.

## Checks (the generator refuses to write the package if any fails)

Every annotated number is recomputed and must equal its controller-time source.

| event | checked against the source |
|---|---|
| 109 | quiet since step 4, reactivated at step 7, trigger 110; 4 cross-target points added since quiet; effective points 6,166 → 6,170; recomputed Cyclopean eligible cells 0 → 28, equal to the logged probe records *and* to the accepted `epistemic.audit` count; serviced at step 134 |
| 178 | quiet since step 67, reactivated at step 114, final trigger 224; 36,748 cross-target points added since quiet (201: 8,506; 224: 28,242); effective 215,125 → 251,873; eligible 0 → 189 (logged and `audit`); serviced at step 136 |
| 210 | 24 own looks; active map 163,944; effective 1,748,902 → 1,938,913; +190,011 later cross-target measurements by source (234, 109, 224); recomputed FSG6f frontier raw / OPEN / map-resolved / boundary-resolved 354/58/26/270 → 350/52/28/270, and the aligned OPEN support of the [7.6, 18.2] candidate 35 → 30, equal to the 01A audit record; proposed gaze [7.6, 18.2] both times |
| scene | active-map surfel totals equal the manifest's `final_map_surfels`; the run's `manifest.json`/`actions.json` hashes equal the accepted ones |

The truth firewall must record 0 violations. The generator is deterministic, and a second run must
reproduce the PNG hashes.

## Visual meaning (no new claim)

- **Reactivation events.** They show the causal story: BEFORE QUIET → another target's
  observation(s) → cross-target geometry added → the accepted probe classifies the target
  ACTIONABLE → it is later serviced.
  - The counts are annotated as descriptive. The **accepted local probe** made the classification.
- **The 210 visual.** It shows that later causal geometry altered the frontier but did not remove
  the local continuation proposal. It draws **no stopping-policy conclusion**.

## Not done

No change to Controller-01 behavior, the run, the 01A audit, thresholds or policies, and no
evaluation truth. The generated visuals stay out of Git. The branch is not merged here.

## Layout checker

Narrow declaration of the new tracked files: this contract (required), the report and the
generator (allowed), mutation-tested.
