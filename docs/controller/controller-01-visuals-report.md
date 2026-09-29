# Controller-01 visual retrofit — report

**Marker.**

    CONTROLLER01_VISUAL_PACKAGE_COMPLETE

This is a Level-B visual package of the **accepted** Controller-01 measurements, under preview/visual
lifecycle Policy 1. It is visualization only: no new experiment, no behavior change, no change to
any accepted artifact or result. The package was generated and checked (**MEASURED**, below). The
branch awaits Luiz's inspection of the images and Chat's review of the generator and this report,
and is not merged.

## Sources and provenance

| item | value |
|---|---|
| branch | `visuals/controller-01-retrofit`, from `main` @ `a60d448` (Policy 1 accepted), isolated worktree |
| contract | `75f4aec` *Specify the Controller-01 visual retrofit* (`docs/controller/controller-01-visuals-contract.md`) |
| generator | `94ff223` *Add the Controller-01 visual package generator* (`tools/controller/visualize_controller01.py`) |
| source run | `/home/lvelho/rd/f3d-vision/previews/controller-01-full`; accepted Controller-01, report commit `e3bf5e0`. `manifest.json` `d293a98f…` and `actions.json` `12cdbe4d…` are checked by the generator |
| source audit | `/home/lvelho/rd/f3d-vision/previews/controller-01a-terminal-audit/audit.json`; accepted Controller-01A, `CONTROLLER01A_FINAL_REPROBE_ACTIONABLE` |
| truth used | controller-time and derived only. **No reference/evaluation truth.** The truth firewall was active for the whole generation: 0 violations, 240 controller-time files opened |
| output | `/home/lvelho/rd/f3d-vision/visuals/controller-01/` (gitignored; 29 MB) |

Regeneration command, from the repository root, 28.7 s wall, deterministic:

    .venv/bin/python tools/controller/visualize_controller01.py \
        --run   /home/lvelho/rd/f3d-vision/previews/controller-01-full \
        --audit /home/lvelho/rd/f3d-vision/previews/controller-01a-terminal-audit/audit.json \
        --out   /home/lvelho/rd/f3d-vision/visuals/controller-01

It was run three times: twice before the generator commit, and once at `94ff223` with a clean tracked
tree. All 11 output files hashed identically each time.

## The package

| file | what it shows | truth labels |
|---|---|---|
| `overview.png` | **The primary Level-B visual.** Left: the final active fused maps, with 109, 178 and 210 marked and the headline numbers. Right: three event cards. **109** and **178**: the Cyclopean state and the effective geometry, before → after. **210**: the FSG6f frontier and the effective geometry, watchdog → terminal | CONTROLLER-TIME + DERIVED |
| `events/reactivation-0109.png` | The four-panel causal story (next section) | CONTROLLER-TIME (1, 2, 4), DERIVED (3) |
| `events/reactivation-0178.png` | The same story for 178 | CONTROLLER-TIME (1, 2, 4), DERIVED (3) |
| `events/watchdog-0210.png` | The watchdog block and the 01A terminal re-probe (below) | CONTROLLER-TIME (1, 2, 4), DERIVED (3) |
| `scene-final.png` | Four separately labelled panels, never mixed (details below) | CONTROLLER-TIME (maps, memory), DERIVED (range, oblique) |
| `diagnostics/attention-timeline.png`, `diagnostics/gaze-chart.png` | The existing Controller-01 diagnostics, copied unchanged from the run. **Supplementary**, not the main scientific visual | derived bookkeeping |
| `pointclouds/scene-active-maps.ply`, `object-0109/0178/0210-active-map.ply` | Active fused maps, head frame (x right, y up, −z forward; metres), binary PLY with surfel RGB (gamma-encoded): 1,059,349 / 2,829 / 133,989 / 163,944 points (final maps) | CONTROLLER-TIME |
| `visuals-manifest.json` | Sources, the 22 checks, statistics and file hashes | — |

The `scene-final.png` panels are:
- ACTIVE FUSED MAPS, 25 objects, 1,059,349 surfels, surfel RGB;
- MEASUREMENT MEMORY, all 141 looks, 7,843,577 points in 33 instances, each point colored by its
  own look's rectified left RGB;
- the active maps colored by range;
- an oblique orthographic view of the active maps from above and behind the head.

### What the reactivation visuals mean

Each event has four panels, following the canonical active-perception frame.

1. **Scene/attention.** The measurement memory up to the trigger step, in look RGB. The target is
   tinted orange; its own looks are marked ×. The trigger fixation and its 12° core are shown in
   blue, and the later service look in aqua.
2. **Foveated observation.** The trigger look's rectified left/right pair from the controller-time
   benchmark images. The pixels measured as the target, which are cross-target measurements, are in
   orange; the trigger's own target is outlined in blue.
3. **Cyclopean state, before → after** (DERIVED). This is the target's own-look footprint, its effective
   map support, and the eligible never-observed exterior shoreline cells. It is recomputed with the
   sealed Cyclopean helpers, and its count equals the accepted `epistemic.audit` count and the
   logged probe records.
4. **Effective causal geometry, before → after.** The added cross-target points are highlighted.

What each event shows:
- **109 `alphabet`.** QUIET since step 4. At step 7, the look at 110 `beams` (gaze [−12, 20]) measured
  4 pixels of 109 at the very corner of its view. Those 4 cross-target points lie at the far-left part of
  the alphabet strip, which 109's own three looks never observed. The Cyclopean eligible cells went
  from 0 to 28, the accepted probe classified 109 ACTIONABLE (proposal [−7.0, 14.1]), and it was
  serviced at step 134. Effective geometry 6,166 → 6,170; active map unchanged at 2,118 surfels.
- **178 `sol`.** QUIET since step 67. Looks of 201 (step 72; 8,506 points) and of 224 (steps 104, 109,
  112, 114; 28,242 points) added 36,748 cross-target points. The step-114 look at 224 `woodBase` added a
  floor region that 178's own looks had never observed. The eligible cells went from 0 to 189
  (proposal [18.9, −14.7]), and 178 was serviced at step 136. Effective geometry 215,125 → 251,873;
  active map unchanged at 83,028.

The captions state it explicitly: **the accepted local probe (FSG6f → Cyclopean) made the
classification. The counts are descriptive.**

### What the 210 visual means

The four panels:
1. The 24 own looks by source, the last look (step 101, [2.6, 18.2]), and the still-requested
   FSG6f look [7.6, 18.2] with its 12° core.
2. The last own binocular look, with the pixels measured as 210.
3. The FSG6f frontier (DERIVED, with `fov3d.control.frontier.extract_frontier` /
   `classify_frontier_state`), at the watchdog and at the terminal state. OPEN, MAP_RESOLVED and
   BOUNDARY_RESOLVED points are colored by state. The OPEN support of the [7.6, 18.2] candidate is
   ringed, and an arrow shows the candidate direction.
4. The effective geometry at the watchdog and at the terminal state. The +190,011 later
   cross-target measurements are colored by source: 234 `worldMap` 94,431; 109 `alphabet` 76,308;
   224 `woodBase` 19,272.

| | watchdog (step 101) | terminal (step 140) |
|---|---|---|
| own looks | 24 | 24 |
| active map | 163,944 | 163,944 |
| effective geometry | 1,748,902 | 1,938,913 (+190,011 cross-target) |
| frontier raw / OPEN / map-resolved / boundary-resolved | 354 / 58 / 26 / 270 | 350 / 52 / 28 / 270 |
| candidates; OPEN support of the candidate | 1; 35 | 1; 30 |
| proposed gaze | [7.6, 18.2] | [7.6, 18.2] |

Later causal geometry altered the frontier, but it did not remove the local continuation proposal.
The visual draws **no stopping-policy conclusion**.

## Checks (MEASURED)

The generator recomputes every annotated number and refuses to write the package if any check
fails. The last run passed **22/22**:
- the source `manifest.json` and `actions.json` hashes, and the 01A outcome;
- the memory replay of all 141 per-action additions;
- **109**: the event identity; effective geometry 6,166/6,170, equal to the logged probes; 4 cross-target
  points, none own-target; eligible 0/28, equal to the logged probes and the accepted audit; serviced
  at step 134;
- **178**: the same checks, with 215,125/251,873, 36,748 points, eligible 0/189 and step 136;
- **210**: 24 own looks; map, effective geometry and later additions by source, equal to 01A; the
  recomputed frontier counts 354/58/26/270 → 350/52/28/270, equal to 01A; the candidate support
  35 → 30, equal to 01A; the proposed gaze;
- **scene**: the active-map surfel counts equal the manifest's;
- the truth firewall: 0 violations.

**Negative controls** (scratch `gen_mutants.py`, throwaway repository copies, scratch output). All
**5/5** were refused with rc 1, and no package was written:
- an expected 109 eligible count of 27;
- an expected 210 OPEN count of 57;
- a wrong accepted manifest hash;
- a generator that opens `evaluation.json` (the firewall raised `PermissionError` before the open);
- an expected 178 cross-target count of 36,747.

## File hashes (sha256, generated at `94ff223`)

| file | sha256 |
|---|---|
| `overview.png` | `09e2b5d8e47c701becaed6bb02f881aa86c395dc9d60df2d177fd3145e34ad95` |
| `events/reactivation-0109.png` | `1fa9a3f567f186d41fc154a2380abfe81dbcd3ba82a8ba21e9a7b9eca549630c` |
| `events/reactivation-0178.png` | `f55d854a7375f61321475831845bbc8c26f71a8904e8e721ebe126e01eddce12` |
| `events/watchdog-0210.png` | `497d6bffc41e7c6d0a1baf0c5a3ab21f57dc2e5522ceceae5e46e1bcc55d5c33` |
| `scene-final.png` | `6b4c8b9394dcf97d61954ae8b0ed717817ed26b999ca6f33f3401e09a905de37` |
| `diagnostics/attention-timeline.png` | `38d1aaac0107ecbf08731af38488ac38cb09f94cd8d2596c26a4edbc10b3c108` |
| `diagnostics/gaze-chart.png` | `08bbe83c7c68e466e5b1b25a4d5dc59b010eb1ae45fdd1ca0b5d41b529df072c` |
| `pointclouds/scene-active-maps.ply` | `8755077cc3eb12b1626df40003ae09eab11f7d21c2d9c5af84cf8f541a8caf72` |
| `pointclouds/object-0109-active-map.ply` | `640d7bc08e4c9a80ed6130db144d4275aa8b62dabcbd6a46d86d22265af9f45f` |
| `pointclouds/object-0178-active-map.ply` | `02e2bd02f4d4aeca74e9012960d55c99b4f03d1a3739cc808105602437ba86b7` |
| `pointclouds/object-0210-active-map.ply` | `d4a2ac1923d9d7a88c6125c37c556a1b6946b71ba7eb2e352f243810a6273dce` |

## Notes and deviations

1. **Visual iteration (scratch, before the generator commit).** The first trial renders had four
   problems: 109's scene window did not include the trigger fixation; the trigger target's tint hid
   the 4 cross-target pixels; mark labels were unreadable on photographic backgrounds; and the
   overview lacked event headers. The trial also exposed a caption that attributed all additions
   since quiet to the trigger look. All were fixed before `94ff223`, and no number changed.
2. **Sealed helpers.** The Cyclopean eligibility layers use the sealed Cyclopean helpers, reached
   read-only through the facade's `_legacy_impl`. The recomputed count is cross-checked against the
   accepted public `epistemic.audit`.
3. **Shared checkout.** Its local `main` is still `e681392`, whose `.gitignore` predates `visuals/`.
   Until that checkout is updated to the accepted `main`, `visuals/` appears there as untracked. No
   tracked file of the shared checkout was modified.
4. **Layout checker.** It declares this report and the generator (allowed) and the contract
   (required): `SUMMARY checked=498 failed=0`. The layout mutation suite caught **42/42**, including
   an undeclared tracked `tools/controller` generator, a misspelled undeclared visuals report and the
   visuals contract untracked.
