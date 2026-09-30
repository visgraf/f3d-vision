# Visual Language 1

**Status: REVIEW PENDING.** Luiz and Chat accept or revise it after inspecting the canonical demo
qualitatively.

This document describes what the generated Controller-02 Classroom demo **actually uses**. The single
source of truth is `tools/visual_language/style.py`: the legend, the frames and the checker all read it,
and check 20 fails if the legend and the style definition disagree.

- Contract: `docs/methodology/visual-language-1-contract.md`.
- Report: `docs/methodology/visual-language-1-report.md`.
- The demo package: `/home/lvelho/rd/f3d-vision/visuals/visual-language-1/`. It holds the legend at
  `legend/visual-language-1.png` and its machine-readable form at `legend/visual-language-1.json`.

## Principles

- Every semantic role has a **color and a non-color cue** (shape, outline, hatch, dash or glyph). Check 15
  fails if a role lacks a non-color cue, if two roles in a group share a cue, or if two swatches in a group
  are not distinguishable in grayscale.
- The palette is **Okabe-Ito based**, on a light surface, and was validated with the dataviz palette
  validator (see [Palette validation](#palette-validation)).
- Text is always ink (dark gray / black), never the series color. The only exception is a short colored
  count label that repeats its mark's color and sits beside the mark.
- **Six distinctions are kept apart** (legend footer; closing frames):
  - measurement ≠ new geometry;
  - visible ≠ depth measured;
  - actionable ≠ worth a final observation;
  - deferred ≠ quiet;
  - residual ≠ failure;
  - `SCENE_CLOSED` ≠ global quiescence.

## Truth / provenance badges

Badges sit on the right of each panel title. Their shape carries the class as well as their color.

| badge | color | non-color cue | used for |
|---|---|---|---|
| `CONTROLLER-TIME` | `#0072b2` (Okabe-Ito blue) | solid filled badge, white text | logged or replayed controller state: the memory raster, the observation, active maps, records, the disposition |
| `DERIVED` | `#464646` | dashed-outline badge, no fill | recomputed by accepted `fov3d` functions and checked against records: E_t(i) views, frontier / eligible layers, the gate geometry |
| `ORACLE INPUT` | `#882255` (wine) | double-outline badge | the Blender catalog and seeds (bootstrap, seed looks); the current-pair Position / Object Index passes (panel 2 of every look) |
| `REFERENCE / EVALUATION` | `#855e14` (brown) | diagonally hatched badge | the single reference render and its products; never a controller input |

`ORACLE INPUT` coexists with `CONTROLLER-TIME` on panel 2: the current-pair oracle measurement is part of
the controller-time experiment. A seed look also tags panel 1 with `ORACLE INPUT`.

## Roles

Colors are sRGB.

| group | role | color | non-color cue |
|---|---|---|---|
| attention | current object (target) | `#141414` | thick dark outline (3–4 px) with a 7 px white halo |
| attention | current fixation | `#141414` | solid ring + four crosshair arms, white halo |
| attention | proposed fixation | `#141414` | dashed ring (10 segments) + dashed arms, white halo |
| attention | attention move (same object) | `#141414` | single-line arrow |
| attention | attention switch (new object) | `#141414` | double-line arrow; the header says SWITCH |
| epistemic | target support | `#56b4e9` (sky) | solid fill inside a dark target outline (`#0a3c6e`) |
| epistemic | other surface | `#cdc9c1` | flat fill, no outline |
| epistemic | unknown | `#f7f6f2` | dot stipple (`#b2afa6`, 8–12 px lattice) |
| epistemic | ambiguous boundary | `#e69f00` (orange) | thin line strokes (cell-wide; widened at zoom) |
| epistemic | unresolved support | `#d55e00` (vermillion) | hollow rings; FSG6f OPEN elements, or Cyclopean eligible cells when the Cyclopean handoff is consulted |
| geometry | persistent geometry | depth-shaded `#c4cbd6` → `#687284` | fine point texture (orthographic splats) |
| geometry | this look's target measurements | `#141414` | dashed footprint outline (legend role; in frames the target outline marks the footprint) |
| geometry | new spatial support: new surfel | `#009e73` (bluish green) | filled pixels / filled squares |
| geometry | repeated measurement | `#cc79a7` (reddish purple) | hollow rings on a screen lattice (and a 45 % purple tint in the eye image) |
| geometry | cross-target measurement | `#56b4e9` (sky) | x marks on a coarser screen lattice |
| service state | QUIET | `#9db4cf` (slate; deliberately reads gray) | filled tile + ✓ glyph |
| service state | ACTIONABLE | `#0072b2` | white tile, 5 px heavy outline + ▶ glyph |
| service state | SEEDABLE | `#828282` | white tile, dashed outline + ○ glyph |
| service state | DEFERRED | `#e69f00` | single diagonal hatch (`#fdf3de` ground) + outline + "II" glyph |
| service state | FINALIZED RESIDUAL | `#d55e00` | cross-hatch (`#fae8dc` ground) + double outline + "R" glyph |
| service state | UNLOCATED | `#828282` | light tile, dotted outline + "?" glyph |
| sensor | actual depth-measuring core | `#007858` | solid rectangle outline |
| sensor | predicted depth-measuring core | `#007858` | dashed rectangle outline (drawn at the support depth) |
| sensor | binocular support | `#007858` | pale wash (`#d6ece2`) inside both dashed core outlines |
| sensor | visible target pixel without valid depth | `#141414` | black diagonal hatch (8 px) |
| sensor | previously interrogated binocularly | `#cc79a7` | dashed ring |

Action sources on the timeline and in the look markers use a color and a shape:
- seed look: `#464646` square;
- FSG6f look: `#0072b2` circle;
- Cyclopean look: `#009e73` diamond.

Timeline events:
- quiet: ✓;
- natural reactivation: yellow `#f0e442` triangle with an ink outline and the object id;
- deferral: orange diamond, then a hatched orange band on the timeline until the end.

Phases: the header badge reads NORMAL (outlined), RESIDUE (orange hatch) or CLOSED (black), and the
timeline repeats them in two phase cells.

### Palette validation

The palette was validated with the dataviz validator (`validate_palette.py --mode light --pairs all`),
set by set:

| set | result |
|---|---|
| panel 3 colors: `#56b4e9`, `#e69f00`, `#d55e00` | PASS: lightness, chroma, CVD (worst ΔE 13.1) and normal-vision floor (15.6). Contrast WARN for sky 2.25 and orange 2.19; the fills carry outlines and strokes |
| panel 4 colors: `#009e73`, `#cc79a7`, `#56b4e9`, `#d55e00` | PASS, with a CVD WARN of 7.6 (purple vs green under deutan). That is legal only with secondary encoding, which is always present: filled squares vs hollow rings |
| QUIET `#9db4cf` | fails the chroma floor, by design: QUIET is a calm neutral, carried by its fill and ✓ glyph |

A darker ochre for the ambiguous boundary (`#b07000`) was tried and rejected: it FAILs CVD separation
against vermillion (ΔE 1.4).

Grayscale distinctness of the rendered swatches (check 15) is the fraction of swatch pixels that differ
by more than 24 gray levels; it must be at least 2 %. The worst pair in each group:

| group | worst pair | visibly different pixels |
|---|---|---|
| truth | DERIVED / ORACLE INPUT | 27.4 % |
| attention | current / proposed fixation | 2.7 % |
| epistemic | other surface / ambiguous boundary | 8.0 % |
| geometry | persistent geometry / repeated measurement | 6.3 % |
| service state | SEEDABLE / UNLOCATED | 9.9 % |
| sensor | actual / predicted core | 14.2 % |

## Temporal semantics of one look (the cockpit)

The main body of the demo holds one logical frame per accepted look t (0..140), laid out as four panels
at 2560 × 1440, plus a roster and a timeline:

| panel | tag | content | source |
|---|---|---|---|
| 1 SCENE / ATTENTION | `BEFORE look t` | measurement memory up to look t−1 in the head chart (look RGB, lightened; never measured = `#eeede9`); the target outlined; all earlier fixations (small dots); current fixation = look t−1 (solid); proposed fixation = look t (dashed); arrow (double if SWITCH); zoom inset; the target's state before, its own-look count, the decision and the proposal's source | CONTROLLER-TIME |
| 2 THE EYES | `OBSERVATION by look t` | left and right rectified depth cores (256 px, shown at 448 px, green solid border = the actual core). Left image: new-surfel pixels green, repeated-measurement pixels purple-tinted with rings, target pixels without valid depth black-hatched, the target outlined. Right image: the target outlined from the right instance channel. The wide 29° left raw view carries the 12° core outline (visible ≠ depth measured), with counts of target-valid points, all valid points, and target pixels without depth | CONTROLLER-TIME + ORACLE INPUT |
| 3 CYCLOPEAN / EPISTEMIC | `AFTER look t` | E_t(i) in the head chart (target support, other surface, unknown, ambiguous boundary); unresolved support rings; current fixation = look t; the next local proposal (dashed) or a QUIET stamp; zoom inset; the local probe's summary. The proposal comes from the controller-time probe record | DERIVED |
| 4 PERSISTENT 3-D MEMORY | `AFTER look t` | every object's active map before look t (depth-shaded); look t's new surfels (green), repeated target measurements (purple rings) and cross-target measurements (sky x); the head and a dashed gaze ray to the measured target; zoom inset; the map size change and the counts | CONTROLLER-TIME |

The roster shows the 25 localized objects' service states after look t, with the target boxed; the last
tile counts the 209 unlocated objects. The timeline shows:
- the action source per look;
- the attention bouts (alternating gray, object id at each bout start, a tick at each switch);
- the events;
- the phase cells;
- a playhead, with future looks faded.

Special events use the same furniture, and are staged (panels revealed one by one; holds in
`demo/logical-frame-manifest.json`).

## Standard views

- **Angular chart.** The controller domain, yaw −25..25° and pitch −20..20°, with yaw = atan2(x, −z)
  and pitch = atan2(y, hypot(x, z)) in the fixed head frame. E_t(i) uses 0.1° cells. The cockpit draws it
  at 12.5 px/deg (625 × 500), with a grid line every 5°. The view never moves; zoom insets instead of
  camera motion.
- **Zoom windows are causal.** A window grows over the current attention bout from its start up to look
  t, and never uses future looks. The main chart shows the inset's locator as a dashed rectangle.
- **Standard head-relative 3-D camera.** Orthographic, from above and behind the head (elevation 38°,
  azimuth −18°). It is framed once on the final active maps (0.5–99.5 %) and the head origin, and is the
  same in every frame. Depth shading runs over the 1–99 % depth range. Zoom insets use the same
  orientation.

## Conventions

- **New vs repeated (measurement ≠ new geometry).** Fusion appends new surfels, so look t's new surfels
  are the saved map's entries past `active_map_size_before`. Repeated measurements are look t's
  target-valid points that did not become new surfels. Both counts equal the controller-time records
  exactly: `new_surfels` and `nonnew_target_points` (checks 14 and extraction).
- **Visible vs depth measured.**
  - Panel 2 hatches target pixels without valid stereo depth and outlines the 12° core inside the 29° view.
  - `panoramas/observed-footprint.png` separates eye-ray-seen cells (200,752) from head-depth cells
    (181,862).
- **Deferred vs quiet.** They use different tiles (single orange hatch + II vs slate + ✓), the orange
  timeline band, and the explicit "DEFERRED ≠ QUIET" frame of the 210 event.
- **Actionable vs worth a final observation.** In the residue gate, 210 keeps its ACTIONABLE tile while the
  final proposal is struck through as "withdrawn: not executed". The unresolved support stays on screen.
- **Residual ≠ failure.** FINALIZED RESIDUAL is a closed state with an explicit residue (cross-hatch, double
  outline, R), not an error color. The closing frames state it in words.
- **SCENE_CLOSED ≠ global quiescence.** The CLOSED phase badge and the closing statement.

## Accessibility rules applied

- Body text is at least 22 px at 1440p (16.5 px at 1080p); titles are 26–30 px, headline numbers 40–64 px.
  DejaVu Sans / Bold (font hashes in the render manifest).
- Text over imagery sits on a white plate or carries a white outline.
- Little text per frame: a headline, one sub-line, panel titles and three or four lines per panel.
- High contrast marks: black crosshairs with white halos, heavy outlines, and no meaning carried by color
  alone (check 15).
- Pacing: 23 frames (0.77 s) per ordinary look and 36 frames (1.2 s) per switch or first look. Special
  events are staged at 3–6 s per stage. The legend is held 10 s and the cockpit guide 7 s.

## Examples (in the package)

- `frames/step_025.png`: a seed look (panel 1 tagged ORACLE INPUT; SWITCH arrow; Cyclopean proposal after).
- `frames/step_101.png`: 210's 24th look; the probe still proposes [7.6, 18.2]; "ordinary budget reached
  → DEFERRED".
- `events/reactivation-0109.png`: the four cross-target pixels, magnified ×22; eligible 0 → 28.
- `events/reactivation-0178.png`: 36,748 cross-target points; eligible 0 → 189.
- `events/defer-0210.png`: ACTIONABLE → DEFERRED; DEFERRED ≠ QUIET; the scene continues.
- `events/final-residue-gate-0210.png`: 30 OPEN support elements, the predicted cores, the ledger,
  REJECT, NO RENDER / NO OBSERVE.
- `frames/closure.png`: SCENE_CLOSED; residual ≠ failure; SCENE_CLOSED ≠ global quiescence.
- `legend/visual-language-1.png` and `overview.png`.
