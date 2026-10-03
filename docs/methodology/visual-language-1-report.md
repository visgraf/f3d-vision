# Visual Language 1 + full canonical Classroom demo — report

**Marker.**

    VISUAL_LANGUAGE_1_CANONICAL_DEMO_COMPLETE

**Qualitative status: ACCEPTED** (`VISUAL_LANGUAGE_1_ACCEPTED`; see "Acceptance record" at the end).
When this report was first committed the status was REVIEW PENDING: Luiz and Chat decided after
inspecting the demo, against this question:

> Can a technically literate viewer understand what the system sees, knows, chooses, changes, defers and
> finally leaves unresolved, without reading the implementation?

The package is complete and every machine check passes:
- a 4 min 11 s demo in two resolutions;
- all 141 accepted looks, each as one four-panel cockpit frame;
- the seven special events, slowed down;
- a poster, a legend, panoramas, full point clouds and narration.

No scientific behavior changed:
- `fov3d/` is identical to accepted `main`;
- no controller was rerun;
- no new sensory observation was made.

Claim labels:
- **MEASURED**: produced by the commands below;
- **DERIVED**: recomputed by accepted functions and compared with records;
- **PROPOSED**: the contract's estimates.

## Branch and provenance

| item | value |
|---|---|
| branch | `methodology/visual-language-1-canonical-demo`, from `main` @ `1e0584b` (Controller-02 accepted); isolated worktree; not merged |
| contract | `095f48a` *Specify Visual Language 1 and the full canonical Classroom demo* |
| implementation | `300d7c4` *Implement Visual Language 1 and the canonical Classroom demo generator*; `89f66ac` (language document; check 15 renders from the declared roles); `2320e5b` (distinct final-epistemic panorama; check 12 path); `a30d453` (check 12 probes the binary reference product) |
| canonical generation | `render`, `reference`, `video` at `2320e5b`; checks and corruptions at `a30d453` (a checker-only change) |
| extraction | at `300d7c4`'s code. It first ran before that commit; the re-run at `300d7c4` into a scratch directory reproduced all 456 cache files byte-identically (the manifest was equal except for wall time) |
| Controller-01 source | `/home/lvelho/rd/f3d-vision/previews/controller-01-full`: `manifest.json` `d293a98f…`, `actions.json` `12cdbe4d…`; 1,678 files, byte-identical before and after (check 24) |
| Controller-02 source | `/home/lvelho/rd/f3d-vision/previews/controller-02-classroom-replay`: `result.json` `a6dc4879…` (`CONTROLLER02_CLASSROOM_SCENE_CLOSED`), `actions.json` `7fb86aba…`, `events.json` `fae7e648…`, `final-residue.json` `a315714f…`, `manifest.json` `ad49e835…` |
| cache (machine-facing) | `/home/lvelho/rd/f3d-vision/previews/visual-language-1-classroom/` (203 MB): `extract-manifest.json` `d125ea95…`, `render-manifest.json` `53f286d7…`, `reference/reference-manifest.json` `effa6bcd…`, `check-report.json` |
| package (human-facing) | `/home/lvelho/rd/f3d-vision/visuals/visual-language-1/` (449 MB, 164 files): `visual-language-manifest.json` `fef82479…` |

## Commands

Run from the worktree root:

    S=/home/lvelho/rd/f3d-vision/previews; V=/home/lvelho/rd/f3d-vision/visuals/visual-language-1
    G=tools/visual_language/generate_visual_language1.py
    .venv/bin/python $G extract --source $S/controller-01-full --replay $S/controller-02-classroom-replay \
        --cache $S/visual-language-1-classroom
    blender -b /home/lvelho/rd/f3d-vision/scenes/classroom/classroom_eye.blend --python-exit-code 1 \
        -P tools/visual_language/render_reference_view.py -- --seeds $S/controller-01-full/bootstrap/seeds.json \
        --out $S/visual-language-1-classroom/reference-render
    .venv/bin/python $G render --source $S/controller-01-full --replay $S/controller-02-classroom-replay \
        --cache $S/visual-language-1-classroom --out $V
    .venv/bin/python $G reference --source $S/controller-01-full --cache $S/visual-language-1-classroom --out $V
    .venv/bin/python $G video --cache $S/visual-language-1-classroom --out $V
    .venv/bin/python tools/visual_language/check_visual_language1.py --source $S/controller-01-full \
        --replay $S/controller-02-classroom-replay --cache $S/visual-language-1-classroom --package $V \
        --corruptions --report $S/visual-language-1-classroom/check-report.json

Measured durations (the contract's estimates were PROPOSED):

| command | measured | cost class |
|---|---|---|
| extract | 266.1 s (289.8 s for the verification re-run) | batch |
| reference render (one Blender process) | 29.1 s on OPTIX, 33.5 s wall | interactive / batch |
| render (16 workers) | 98.3 s | batch (the contract expected above batch) |
| reference | about 3 s | interactive |
| video (two encodes) | about 80 s | batch |
| checks | 53–55 s | batch |
| checks + 33 corruptions | 4 min 28 s | batch |

The Blender command uses the shared checkout's scene path, exactly as the accepted Controller-01 run did,
because the new worktree had no scene-asset links; the asset is only read.

## Output tree

    overview.png, overview.json
    legend/visual-language-1.png, legend/visual-language-1.json
    demo/controller-02-classroom-full-1440p.mp4, demo/controller-02-classroom-full-1080p.mp4,
        demo/logical-frame-manifest.json
    frames/bootstrap.png, frames/step_000.png … frames/step_140.png, frames/residue.png, frames/closure.png
    events/reactivation-0109.png, reactivation-0178.png, defer-0210.png, final-residue-gate-0210.png
    panoramas/observed-footprint.png, final-epistemic-0210.png
    pointclouds/scene-active-maps.ply, scene-measurement-memory.ply
    reference/scene-reference.png, depth-reference.png, instance-reference.png
    narration.md
    visual-language-manifest.json

## Videos (MEASURED; ffprobe with frame counting)

| file | size | fps | frames | duration | sha256 |
|---|---|---|---|---|---|
| `demo/controller-02-classroom-full-1440p.mp4` | 2560 × 1440 | 30 | 7,539 | 251.30 s | `8820622b77097d826f31a20c22b5c38eeb48b3ba7b3453c4bec92ba931437c11` |
| `demo/controller-02-classroom-full-1080p.mp4` | 1920 × 1080 | 30 | 7,539 | 251.30 s | `688de43bef42cea3a096644f2482c2d92e6613961e79c9596fe1dcc1c654e685` |

Both are H.264 (libx264, CRF 18, yuv420p) without audio. They were encoded by ffmpeg 4.2.2 from the same
stage images, the 1080p one with Lanczos scaling. Both encodes produced byte-identical files when their
stage images were unchanged; determinism of the MP4s is still not claimed.

## Coverage

There are **154 logical frames**. **Action coverage is 141/141**: `step_000` … `step_140` each appear
exactly once, in order, each with its own cockpit frame. Holds are 23 frames per look and 36 for the 27
switches and first looks.

| logical frame | time (s) | stages | truth |
|---|---|---|---|
| intro | 0.0–5.0 | 1 | CONTROLLER-TIME (text only) |
| intro_reference | 5.0–10.0 | 1 | REFERENCE / EVALUATION |
| legend | 10.0–20.0 | 1 | — |
| guide (how to read the cockpit) | 20.0–27.0 | 1 | as a step frame |
| bootstrap | 27.0–35.0 | 2 | ORACLE INPUT |
| event_reactivation_0109 (after step 7) | 42.87–56.87 | 4 | CONTROLLER-TIME, DERIVED, ORACLE INPUT |
| event_defer_0210 (after step 101) | 136.30–150.30 | 4 | CONTROLLER-TIME, DERIVED |
| event_reactivation_0178 (after step 114) | 161.13–175.13 | 4 | CONTROLLER-TIME, DERIVED, ORACLE INPUT |
| residue (NORMAL → RESIDUE, after step 140) | 196.8–203.8 | 2 | CONTROLLER-TIME |
| event_final_residue_gate_0210 | 203.8–225.3 | 6 | CONTROLLER-TIME, DERIVED |
| closure | 225.3–235.3 | 2 | CONTROLLER-TIME |
| outro | 235.3–245.3 | 2 | CONTROLLER-TIME |
| outro_reference | 245.3–251.3 | 1 | REFERENCE / EVALUATION + CONTROLLER-TIME |

**Event numbers.** All are recomputed and equal to the records (checks 5–10).

- **Bootstrap:**
  - 234 catalog objects;
  - 25 localized, each with one seed;
  - 209 unlocated.
- **109:**
  - QUIET at look 4;
  - look 7 at 110 measures 4 cross-target points (magnified ×22);
  - Cyclopean eligible 0 → 28;
  - ACTIONABLE, serviced at look 134.
- **210:**
  - DEFERRED at look 101;
  - local ACTIONABLE, ordinary look count 24;
  - 39 more looks go to other objects.
- **178:**
  - QUIET at look 67;
  - 36,748 cross-target points (8,506 from 201, 28,242 from 224; looks 72, 104, 109, 112, 114);
  - eligible 0 → 189;
  - serviced at look 136.
- **End of the normal phase:** 24 QUIET; 210 ACTIONABLE + DEFERRED.
- **Gate:**
  - unchanged FSG6f proposal [7.6, 18.2];
  - 30 OPEN support elements: 0 enter both predicted cores, 30 were previously interrogated;
  - `novel_service_count` 0;
  - REJECT `no_novel_serviceable_support`; NO RENDER, NO OBSERVE.
- **Closure:**
  - `SCENE_CLOSED`;
  - quiet 24;
  - residual 210 `wall.008` (ACTIONABLE, `FINALIZED: final_probe_rejected`);
  - unlocated 209;
  - final residue observations 0.

**Other counts** (MEASURED from the records):
- sources: 25 seed, 50 FSG6f and 66 Cyclopean looks;
- 26 attention switches;
- new surfels 1,059,349 (equal to the final active-map total) and repeated measurements 1,215,508.

## Truth boundary (implemented)

- **Controller-time extraction.** It runs under `fov3d.control.integrated.TruthFirewall` with
  `vl1_data.forbidden_controller_time`, which refuses:
  - evaluation truth (`controller01.is_evaluation_truth`);
  - this step's reference products (`reference-render/`, `reference/`, `reachable_samples.npz`);
  - the 01A/01B/01C previews.

  It opened 678 source files, with 0 violations. The per-file sha256 fingerprints were taken outside the
  firewall (hashing only).
- **Controller-time rendering.** Same firewall, in the parent process and in each of the 16 workers.
  Opened 888 files, 0 violations.
- **Reference path.** A separate process with a recording firewall that forbids nothing. It opened 31
  files, including `bootstrap/evaluation_only/reachable_samples.npz` for the alignment check. It writes
  only `reference/` products and REFERENCE-tagged stages.
- **Video / composition.** Its firewall refuses evaluation truth. It opened the two manifests; 0
  violations.
- **Check 11** re-verifies the recorded opened files and live-tests the predicate: `evaluation.json`,
  `reachable_samples.npz` and the 01C audit are refused.
- **Check 12** live-tests that the controller-time firewall refuses the reference product. It also checks
  that no controller-time special uses a reference stage, and that reference imagery appears only in
  REFERENCE-tagged logical frames.

**Every per-step derivation matched its controller-time record exactly** (MEASURED; the extraction stops on
any mismatch):
- memory additions, head evidence, matcher recomputation, map sizes;
- new surfels (the map's appended entries);
- repeated measurements (`nonnew_target_points`);
- frontier counts against the probe record after each look;
- Cyclopean eligible cells;
- effective-geometry sizes.

**79 recomputed epistemic views equal the saved controller-time views**: the 54 event views and the 25
final terminal views. At the final state:
- 210's recomputed effective geometry equals the saved one (1,938,913 points);
- its frontier counts equal the Controller-02 gate record (350 / 52 / 28 / 270).

## Optional reference assets and provenance

No wide RGB scene reference existed; I searched the controller runs, `scenes/classroom` and the
OLD-PREVIEWS archive. **Exactly one** static Blender reference view was rendered:
- a 2400 × 2048 perspective view from the fixed head origin and orientation of `bootstrap/seeds.json`;
- 512 spp, OPTIX, 29.1 s;
- Combined, Position and Object Index passes, with object indices assigned by the accepted renderer's
  `_assign_instance_ids`.

It was resampled on the host into the head chart (yaw ±25°, pitch ±20°, 40 px/deg).

Alignment against the existing evaluation-only dense samples, all 29,288 (MEASURED):

| test | result |
|---|---|
| instance agreement | 0.9963 |
| range within 2 cm | 0.9951 |
| id → name map | equal to the controller's catalog |
| verdict | ALIGNED (threshold 0.97 / 0.95) |

Products:

| file | sha256 |
|---|---|
| `reference/scene-reference.png` | `9d0a8d3d…` |
| `reference/depth-reference.png` | `7ead8fce…` |
| `reference/instance-reference.png` | `059c140a…` |

All three come from that single render. It is not an observation, it is not fed to the controller, and it
is shown only in the `intro_reference` and `outro_reference` frames, which carry the badge.

## Palette and glyph semantics

These are in `docs/methodology/visual-language-1.md` (REVIEW PENDING), with exact colors, cues,
badges, temporal semantics, standard views, conventions and validator results. Summary:
- Okabe-Ito based, on a light surface;
- every role has a non-color cue;
- four truth badges distinguished by shape (solid, dashed outline, double outline, hatched);
- service-state tiles by fill, hatch and glyph;
- new surfels are filled green and repeated measurements hollow purple rings;
- unresolved support is vermillion rings;
- predicted cores are dashed.

## Checks (MEASURED)

`tools/visual_language/check_visual_language1.py` passed **25/25** (`VISUAL_LANGUAGE_1_CHECKS_PASS`),
checks 1–25 as numbered in the contract.

**Corruption / mutation suite: 33/33 caught.** Each corruption is applied to a throwaway mirror, whose
JSON files are copies and whose other files are links, or is an in-process mutant; every one failed its
targeted check:

| check | corruptions |
|---|---|
| 01 | a wrong accepted hash constant |
| 02 | Controller-02 marker NOT_CLOSED |
| 03 | a missing step; a duplicated step |
| 04 | an altered gaze; an altered target |
| 05 | the deferral misplaced |
| 06 | 109's cross-target points 4 → 5 |
| 07 | 178's eligible 189 → 190 |
| 08 | the deferral step 101 → 100 |
| 09 | in both cores 0 → 1 |
| 10 | quiet 24 → 25 |
| 11 | evaluation truth in the opened files; a predicate that no longer refuses evaluation truth |
| 12 | a predicate that no longer refuses reference products; a reference stage in a controller-time special |
| 13 | panel 2 without ORACLE INPUT; a REFERENCE badge on a step |
| 14 | an altered new-surfel count |
| 15 | a role without a non-color cue; DEFERRED drawn like QUIET |
| 16 | a missing frame |
| 17 | a missing event figure |
| 18 | a shifted logical frame; two frame images swapped |
| 19 | a truncated 1080p video |
| 20 | an altered legend label |
| 21 | an altered overview number |
| 22 | a wrong recorded PLY count; a flipped PLY byte |
| 23 | an altered legend pixel |
| 24 | an altered recorded fingerprint |
| 25 | an edited `fov3d` file (worktree, restored) |

**Other gates** (MEASURED on this branch):

| gate | result |
|---|---|
| Controller-02 checks | 56/56 (`CONTROLLER02_IMPLEMENTATION_CHECKS_PASS`) |
| Controller-01 checks | 56/56 |
| repository layout | 515/515 |
| layout mutants | 72/72 caught, including 6 new Visual Language 1 mutants |
| `scripts/verify_baseline.sh` | 9/9 |
| `git diff --check` | clean |
| new Python | all 6 modules compile |
| `fov3d/` | identical to accepted `main` `1e0584b` |

## Determinism and output hashes (MEASURED)

**Determinism:**
- check 23 regenerates the overview, the legend and the four event PNGs byte-identically;
- the extraction reproduced all 456 cache files byte-identically.

| file | sha256 |
|---|---|
| `overview.png` | `95eb65243ad4233c45de422980750f315ed55cccc4005054f157195dad19718b` |
| `legend/visual-language-1.png` | `d24a0c58915b725a9fb0fa52e75f608b76aa271148af90e3cf9c9980b68d1944` |
| `events/reactivation-0109.png` | `b2095f26c8e7bad6d43a6c3da2a0aee47e62ba42ea02dc26d19fae306668c263` |
| `events/reactivation-0178.png` | `ecfaedc12bb2c05419a79e612a7de543c3306a19c1b00b8382e0a17b50433f07` |
| `events/defer-0210.png` | `2000854d04bba057e08762f884eacce43d4c5f25dd122922dbeaa8ff6654ea74` |
| `events/final-residue-gate-0210.png` | `2f2564dcab2ea2905a342d3d3de3146a12eb2f8d0e055f0657b8f5550c6dfff6` |
| `frames/bootstrap.png` | `50c5e6ee566d1788452a09bd3766bdbb4ae0c831e1c873ed1c3f56cbbe89d5c5` |
| `frames/residue.png` | `556a91934b811bc49fdec29e1f16fd0955bb2341654215e50f8ae181981e51bf` |
| `frames/closure.png` | `ca51ac508a8be6e3ab0ff9a5de8d0326fd6e5719382a0379152b6c7b1bdb987b` |
| `panoramas/observed-footprint.png` | `79011fa5efcca9f5d86e3da5795491d93bb84b7276158c03f337dcc8d2374b37` |
| `panoramas/final-epistemic-0210.png` | `108a1580fedd5f5d890a8b450a9a0a7fb0c60d9969b8c933d85a481548c6bb78` |
| `demo/logical-frame-manifest.json` | `b219d6d50a84d9d6760fb4880b11caa72a0465a4f92708123b73b4400c0eb076` |
| `narration.md` | `ba81f6e8bb351405d898f928e216726de41aa23a5ddf0e40253edf4dc31b764c` |

`visual-language-manifest.json` lists the sha256 and size of every package file.

## Point clouds (MEASURED; full data, binary little-endian PLY)

| file | points | sha256 | content |
|---|---|---|---|
| `pointclouds/scene-active-maps.ply` | 1,059,349 | `34e5fc416bf081563cc9657f51afc5ea1ba8133610a7a40e488825977c95f470` | the 25 final active maps; x y z, surfel RGB, instance |
| `pointclouds/scene-measurement-memory.ply` | 7,843,577 | `c4db37f6e8919908d259c906b6f90c5c28db124143737d8f2f48c049c4c285ff` | every valid measurement of the 141 looks; x y z, look RGB, instance, source step |

The counts equal the manifest's `final_map_surfels` and the sum of all memory additions (check 22). No
sampling was needed; the files total 177 MB.

## Incidents and deviations

1. **Check 15's metric changed.** The first package check failed check 15 on two grayscale pairs: current
   vs proposed fixation, and other surface vs ambiguous boundary.
   - Diagnosis: the mean gray difference over a swatch is dominated by empty background. It would pass two
     near-identical large fills and fail a clearly different small glyph.
   - Fix: the metric is now the fraction of swatch pixels differing by more than 24 gray levels, which must
     be at least 2 %. The fixation swatches are drawn larger so their dash pattern shows.
   - A darker ochre for the ambiguous boundary was tried and rejected, because it failed CVD separation
     against vermillion.
   - The worst pair now passes at 2.7 % (current vs proposed fixation).
   - Both changes preceded the implementation commit.
2. **Check 15 read a cached copy.** While designing the corruption suite I saw that check 15 rendered
   swatches from the import-time `ROLE` copy, so a mutant that redraws a role could slip through. It now
   renders from `style.ROLES` (`89f66ac`).
3. **Check 12 in mirrors.** In the first corruption run, check 12 failed in every mirror, masking whether
   its targeted mutants were genuinely caught. The live control's reference file was a copied JSON inside
   the mirror. It now opens the resolved binary product (`2320e5b`, `a30d453`). In the final suite check 12
   fails only for its own corruptions and one related badge corruption.
4. **Duplicate panorama.** `panoramas/final-epistemic-0210.png` first duplicated the gate event figure.
   It became its own whole-domain panorama (`2320e5b`), and the package was regenerated.
5. **Development defects fixed before the canonical run**, all inside `tools/visual_language/`:
   - Pillow's `MaxFilter(1)` crashes the process (SIGFPE): avoided;
   - an empty splat;
   - the ffmpeg concat demuxer's trailing entry added one frame: `-frames:v` now pins the exact manifest
     length;
   - black padding in the large panels;
   - two helper edits of my own damaged a function; repaired before any commit.
6. **Scene-asset links.** `verify_baseline` first failed its `classroom-assets` step in the new worktree:
   the gitignored Classroom asset links that earlier worktrees carry were missing. After adding the same
   links it passed 9/9. The reference render read the scene from the shared checkout.
7. **Contract estimates.** The render was faster than the contract's PROPOSED "above batch, ~10–15 min":
   98 s. No command exceeded the batch class.

## Known cosmetic issues for the review

- In `events/defer-0210.png` panel 3, the label "24 looks = budget" is partly covered by the DEFERRED tile.
- Tiles for long object names truncate their last letters ("178 sol", "109 alphabet").
- Panel 4's whole-scene 3-D view is sparse in the first looks (by design the camera never moves); the zoom
  inset carries the detail.

## Unresolved decisions

- Qualitative acceptance of Visual Language 1 and the canonical demo (Luiz and Chat).
- Whether to keep the reference hero view and the reference comparison in the intro and outro.
- Any revision of roles, pacing or layout requested in the review.

This branch is not merged, `docs/chat-handoff.md` is unchanged, and Natural Bootstrap-1 is not started.

## Acceptance record

Luiz and Chat inspected the canonical demo and accept Visual Language 1 and the canonical Classroom demo
**as committed** at `578a4f8`:

    VISUAL_LANGUAGE_1_ACCEPTED

- The package under `/home/lvelho/rd/f3d-vision/visuals/visual-language-1/` is accepted as-is. Every
  measured statement and hash above is unchanged.
- The known cosmetic issues listed above are **non-blocking**. They are not repaired.
- The acceptance step performed no regeneration, no rerender, no controller execution and no scientific
  observation. It changed only this status record, the status line of
  `docs/methodology/visual-language-1.md`, and (in the next commit) the stage description and the Chat
  Handoff.
- The earlier "REVIEW PENDING" mentions and "Unresolved decisions" above are the status at report time;
  this record resolves the acceptance question. Accepting the demo as committed keeps the reference hero
  view in the intro and outro.
