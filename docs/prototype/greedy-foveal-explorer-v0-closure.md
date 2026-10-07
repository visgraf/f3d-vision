# Greedy Foveal Explorer v0 — closure

**Status: CLOSED. Accepted by Luiz and Chat as the frozen, controlled proof-of-concept baseline.**

    GREEDY_FOVEAL_EXPLORER_V0_BASELINE_ACCEPTED
    GREEDY_FOVEAL_EXPLORER_V0_CLOSED

This is a project-baseline decision, not a new experiment. Greedy Foveal Explorer v0 is the baseline demonstration for
the next phase, **ENGINEERING / PRESENTATION**. It is not promoted as a general scientific result.

## Accepted conceptual baseline

    FIXATE -> RECONSTRUCT EVERYTHING LOCALLY -> UPDATE GLOBAL H0 MAP + CYCLOPEAN COVERAGE
           -> LOCAL OR GLOBAL SACCADE -> REPEAT

- fixed physical head H0; static Classroom; synthetic Blender observation (64 spp);
- PERFECT / ORACLE correspondence (the accepted AB1b rule, extended to Object Index 0 geometry); the accepted spherical
  metric reconstruction;
- one global H0 surfel map with the accepted 12-mm association rule;
- greedy local exploration: 8 neighbours in the current gaze's tangent frame, 7.2° step, score EDGE_SUPPORT ×
  UNSEEN_GAIN;
- greedy global jumps: to the deepest cell of the largest UNSEEN region;
- no object scheduler, no Controller-01/02 state machine. Coverage of the 1° sphere is the controller's own state;
  the Breadth-1 reference is used only post hoc, for evaluation.

## Provenance

| item | value |
|---|---|
| repository | `visgraf/f3d-vision` |
| prototype branch (never merged) | `prototype/greedy-foveal-explorer-v0` @ `8066a246bf251fb1e2d66b7061899c32df236bf1`, created from the unaccepted NS1e head `4a86fc9b808d36837159ebae4b93be4b9987a9ea` |
| frozen implementation | `a437df048b555d5b59f6855b6572eea2665ab0da`, tag **`greedy-foveal-explorer-v0-impl`** |
| implementation files | `tools/greedy_foveal/{explorer.py, run.py, render_server.py}` |
| demo baseline | `8066a246bf251fb1e2d66b7061899c32df236bf1`, tag **`greedy-foveal-explorer-v0-demo`** |

The successful run was made from the later branch state `4d823ad6679534406aff4ce8604d209a81384563`. At that commit,
`explorer.py`, `run.py` and `render_server.py` are byte-identical to `a437df0`.

The prototype documents live on the tags, not on `main`:

- reports at `docs/prototype/greedy-foveal-explorer-v0{,-grow,-grow600}-report.md`;
- the demo record at `docs/prototype/greedy-foveal-explorer-v0-demo.md`.

## Frozen successful run

The run directory is `previews/greedy-foveal-explorer-v0-grow600/`. Its freeze record is `freeze.json`, sha256
`a4283ab7436f03d8a5babd1086da760d0bfb614fdcefd73928f3a25c1ff72f55`, frozen at `2026-10-06T22:36:22Z`.

| frozen file | sha256 |
|---|---|
| `final-map.npz` | `90730b43f150c271cc27de1d4e7d7649b302e00bf7ca49f4fddaefd3cd362aed` |
| `trajectory.json` | `bab97557d347f0fb4c6c0acd65f0ca95c18b1e3015aff8046a8118811da35100` |
| `coverage.npz` | `37d3a2ede43bfec8e3768825edceacde9dd21df42921c5b410378f1305ca5d72` |
| `final-map.ply` | `60354379fa2c7b705b197c912b2c486ed59a3b9095586df43ea23715ff48eb5b` |
| `final-map-oracle-segmentation.ply` | `bd98dc5a1603b8f6d9f37387f790a41896dcfecfb3a29868c78943ea52412489` |
| `evaluation.json` (post-freeze) | `65f8353c580159da7dea464056c99ff8494f987325c250f4aebd25999d5ddf96` |
| Breadth-1 reference `canonical.exr` | `4ea036fc74eab3b3ab06a0c4470c2b01740c9322de0eea522f957ddfffa172f8` |

## Measured final result

| quantity | value |
|---|---|
| final fixation / stop reason | **542** / SEEN ≥ 99 % of 4π |
| angular SEEN / DEPTH | **99.00 % / 98.28 %** |
| Breadth-1 all geometry, 12 mm | cells **98.52 %** (251,966 / 255,758); solid angle **98.32 %** |
| authored only (Object Index > 0), 12 mm | cells 98.52 % (218,988 / 222,267); solid angle 98.25 % |
| saccades | 322 local / 219 global |
| final surfels | 16,517,811 |
| wall time | 729 s |

These values are measured by the run itself. The run's minimal checks all pass:

- the head stays at H0;
- every reconstructed point is finite;
- no fixation is repeated;
- S_seen never decreases;
- the map reloads identically;
- Breadth-1 is opened only after the freeze;
- the policy is deterministic (541 saved decision states re-decided identically);
- fusion follows the FSG3 rule, bitwise.

## Frozen demo

The demo is an offline replay of the frozen run. It makes no new scientific claim. It is built by
`tools/greedy_foveal/demo.py` at the `greedy-foveal-explorer-v0-demo` tag. The outputs are in
`visuals/greedy-foveal-explorer-v0-demo/`:

| file | sha256 |
|---|---|
| `demo.mp4` (1920 × 1080, H.264, 30 fps, 62.4 s, 1,873 frames) | `655c4757cbc7076a7c717815f1f832f6a78f319d2e31868bcb207655cec0572c` |
| `demo-poster.png` | `98ba555022ecf29b3d3370c2bbb22c82315fa10fcbe9b8958eba0a099f465f02` |
| `demo-final.png` | `9afa30dbfb7e14e53a76815d82e273bd0a38e53b75ad4886a4ca9cb764186d65` |
| `demo-manifest.json` (run freeze, final map used) | `6043e40b8f152772eb93956ac9c04fd5f6c1cff0d18c6e7f519d1ec39ffb352f` |

Truth semantics, using Visual Language 1 cues:

- REFERENCE / PRESENTATION;
- REFERENCE / EVALUATION;
- CONTROLLER-TIME;
- DERIVED;
- PERFECT / ORACLE CORRESPONDENCE;
- ORACLE SEGMENTATION / VISUALIZATION ONLY.

The Breadth-1 reference never reaches the reconstruction panels; the demo's build stages are audited for this, and
`demo.py check` passes.

## Limitations (the definition of this controlled proof of concept)

- fixed head;
- static synthetic Classroom;
- PERFECT / ORACLE correspondence;
- Blender-assisted oracle identity, used only where declared (visualization; it never drives gaze, fusion or
  stopping);
- 64 spp synthetic rendering;
- evaluation of the first-hit 360° scene: hidden / occluded surfaces are not reconstruction targets;
- natural stereo deferred; natural segmentation deferred; moving head deferred;
- efficiency and storage not optimized;
- the greedy trajectory is deliberately unsophisticated: diagonal bias, triangular holes, a long hole-filling tail of
  single global jumps.

## Not claimed

- No general scientific result, no optimality of the trajectory, no natural-stereo or natural-identity capability.
- No validation beyond the static, fixed-head synthetic Classroom.
- **No acceptance of NS1e.** Accepting Greedy v0 does not imply accepting NS1e. NS1e stays REVIEW PENDING, NOT
  ACCEPTED, NOT MERGED.
- The prototype branch descends from NS1e. It is **not** merged or fast-forwarded into `main`.
- The Controller-01 / Controller-02 / North-Star line remains preserved historical research evidence. It is not deleted
  and not on the demonstration critical path.

## Next phase: ENGINEERING / PRESENTATION

This section gives the direction only; it is not an implementation plan. Possible work:

- packaging the demo;
- extracting the small Greedy explorer from its prototype ancestry onto a clean engineering branch;
- simplifying and organizing the code;
- reducing map and storage cost;
- interactive visualization;
- presentation figures, a webpage and video variants;
- export and distribution of the demo products.

Engineering must reproduce the frozen baseline behavior before optimizing it. This closure authorizes no policy
redesign.
