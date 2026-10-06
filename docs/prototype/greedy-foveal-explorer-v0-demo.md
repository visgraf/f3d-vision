# Greedy Foveal Explorer v0 — presentation demo

**Presentation only.** This is an offline replay of the frozen grow600 run. It makes no new scientific claim. The
exploration was not rerun, and `explorer.py`, `run.py` and `render_server.py` were not modified (no diff against
`a437df0`).

## Source

| item | value |
|---|---|
| branch | `prototype/greedy-foveal-explorer-v0`, built from HEAD `429de10` |
| run | `previews/greedy-foveal-explorer-v0-grow600/` (code `4d823ad`; explorer byte-identical to `a437df0`) |
| run freeze | `freeze.json` sha256 `a4283ab7436f03d8…`. Every frozen file is re-verified before any read. |
| final map used | `final-map.npz` sha256 `90730b43f150c271…`, equal to the frozen hash |
| evaluation | the run's own `evaluation.json` and `evaluation.npz` (Breadth-1 EXR sha256 `4ea036fc…`) |
| demo code | `tools/greedy_foveal/demo.py` (presentation only) |

Commands:

    .venv/bin/python tools/greedy_foveal/demo.py rerender   # once; cached
    .venv/bin/python tools/greedy_foveal/demo.py build      # about 95 s
    .venv/bin/python tools/greedy_foveal/demo.py check

## Post-hoc re-render (display RGB only)

The full run deleted its raw EXRs. To display the eye images, `rerender` drove the unchanged render server
(`run.Server` / `render_server.py`) once more at each fixation's saved gaze. Settings matched the run: Blender 5.2.1,
OPTIX, 64 spp, seeds L 2111 / R 2112. Rendering all 542 fixations took 421 s.

- **Calibration.** All 542 calibrations written by the server were byte-identical to the saved ones.
- **Same-view check.** At each saved reconstructed point's left pixel, the re-rendered left Position matches the point
  to a median of 0.045 mm across fixations (worst fixation median 0.84 mm).
- **What was kept.** Only the 256 × 256 left and right foveal RGB crops, display-tone-mapped, in
  `previews/greedy-foveal-explorer-v0-demo-cache/eyes/` (160 MB including the manifest). The EXRs were deleted.
- No run product was touched. The depth patch shown in panel B comes from the run's saved `points.npz`, not from the
  re-render and not from Breadth-1.

## Video

| | |
|---|---|
| file | `demo.mp4` |
| format | 1920 × 1080, H.264 (yuv420p, CRF 18), 30 fps, no audio |
| length | 1,873 frames = 62.4 s |
| sha256 | `655c4757…` |

Timeline:

| time | segment | frames |
|---|---|---|
| 0–4 s | title and concept, with a key to the four panels | 120 |
| 4–47.4 s | the replay: all 542 fixations in order, 2 frames each plus 1 extra when the next saccade is global | 1,303 |
| 47.4–49.4 s | freeze: 99.00 % SEEN · 98.28 % DEPTH | 60 |
| 49.4–54.4 s | orbit around the persistent 3-D map | 150 |
| 54.4–62.4 s | the final board | 240 |

No measurement is interpolated between fixations. The MP4 `comment` metadata carries the run values.

Replay panels:

- **Status strip:** fixation, next saccade (LOCAL blue / GLOBAL vermilion, with a strip flash on global frames),
  SEEN / DEPTH / surfels taken from `trajectory.json`.
- **A:** the Breadth-1 RGB panorama, with the current footprint, a fading trail of the trajectory so far, and the next
  saccade (global dashed).
- **B:** left and right foveal RGB and the DERIVED metric depth patch.
- **C:** the observer's UNSEEN / SEEN / DEPTH state, from the saved per-fixation states. DEPTH territory shows the
  observer's own RGB tinted blue.
- **D:** the persistent map growing. The display uses 1.5 cm voxels of the frozen map, ordered by first-fixation
  provenance; the ceiling is removed; new voxels are shown in yellow.

## Stills and panoramas (`visuals/greedy-foveal-explorer-v0-demo/`)

| file | content |
|---|---|
| `demo-poster.png` | 2560 × 1440. Title; fixation #179 (both eyes and depth; chosen only for legibility); the observer's state at #50 / #200 / #450 / #542; the full 3-D map; the reconstructed RGB-D panorama; the four headline numbers |
| `demo-final.png` | 1920 × 1080. Headline numbers; ACTIVE RECONSTRUCTION and BLENDER REFERENCE panoramas (RGB / depth / instance); the Breadth-1 12-mm coverage map; the full final 3-D map (all 8,736,525 surfels below the ceiling cut) |
| `final-{rgb,depth,instance}-panorama.png` | 1440 × 720 (0.25°), projected from the final map, nearest H0 range per pixel; unreconstructed pixels stippled grey |
| `reference-{rgb,depth,instance}-panorama.png` | 720 × 360, Breadth-1, for comparison only |
| `demo-manifest.json`, `demo-checks.json` | provenance, the per-stage open audit, the panel registry, ffprobe output |

The depth images share one single-hue scale: 0.5–5.5 m of range from the head.

## Truth labels (Visual Language 1 cues)

- **REFERENCE / PRESENTATION · NOT AVAILABLE TO CONTROLLER** (hatched brown): replay panel A only.
- **REFERENCE / EVALUATION · NOT AVAILABLE DURING CONTROL**: the BLENDER REFERENCE row, the coverage map, and the
  98.32 % headline on the board and the poster.
- **CONTROLLER-TIME** (filled blue): the status values and panel C.
- **DERIVED** (dashed): the depth patch, the 3-D map, and the reconstructed panoramas. "DISPLAY DOWNSAMPLE" marks the
  voxel views.
- **PERFECT / ORACLE CORRESPONDENCE** (double outline): panel B.
- **ORACLE SEGMENTATION · VISUALIZATION ONLY**: both instance panoramas.

`build` keeps the truth domains in separate audited stages:

| stage | reads |
|---|---|
| derived | final map and per-fixation run products only; no reference file |
| reference | the Breadth-1 EXR and `evaluation.npz` |
| compose | of the reference products, only `b1-rgb.png` (for panel A) |

## Checks (`demo.py check`: all pass)

- The replay shows fixations 1…542 in exact order.
- The MP4 metadata gives SEEN 99.00 % and DEPTH 98.28 %, equal to the run.
- The final map used is the frozen one (sha256 equal).
- No reference file was opened in the derived stage.
- Reference data appears only in panels that carry a REFERENCE label.
- The headline values equal `evaluation.json` and `trajectory.json` (542; 99.00 %; 98.28 %; 98.32 % / 98.52 %;
  16,517,811).
- The MP4 decodes as H.264, 1920 × 1080, 30 fps, 1,873 frames.
- `git diff --check` is clean.

The first build failed the labelling check. The panel registry had merged the two instance panoramas into one entry,
and the board's 98.32 % tile carried no reference tag. The registry now lists each drawn panel, and the tile carries
REFERENCE / EVALUATION. The check itself was not changed.
