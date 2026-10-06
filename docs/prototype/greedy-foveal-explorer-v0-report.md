# Greedy Foveal Explorer v0 — prototype report

**This is a prototype. It is not a scientific milestone.** It was built under Luiz's fast reset: no contract, a
disposable branch, and no plan to merge as-is. All numbers below are **MEASURED** from the one full run named here,
unless a line says **ESTIMATED**.

## Provenance

| item | value |
|---|---|
| branch | `prototype/greedy-foveal-explorer-v0` (isolated worktree) |
| base | NS1e head `4a86fc9b808d36837159ebae4b93be4b9987a9ea` (`origin/main` = `5aa2231` was verified and left untouched; NS1e was not accepted or merged) |
| implementation (frozen before the full run) | `a437df048b555d5b59f6855b6572eea2665ab0da`; the run recorded this HEAD with a clean tracked tree |
| after the run | `visuals.py` only (global saccades now drawn dashed; presentation only), committed with this report |
| code | `tools/greedy_foveal/{run.py, explorer.py, render_server.py, visuals.py}` |
| scene / renderer | Classroom `classroom_eye.blend` (sha256 `dca66a32…`), Blender 5.2.1, Cycles OPTIX, **64 spp** (also confirmed by the EXR header `cycles.interior.samples = 64`) |
| head | fixed H0 = the accepted AB1a calibration head pose (`…/ab1a-first-natural-stereo-look/acquisition/calibration.json`, sha256 `9960c86e…`, checked by `ns1a_render.eye_pose(strict=True)`) |

Commands, run in order from the worktree:

    .venv/bin/python tools/greedy_foveal/run.py explore   --run <scratch>/smoke1 --max-fix 8 --keep-raw   # smoke
    .venv/bin/python tools/greedy_foveal/run.py evaluate  --run <scratch>/smoke1
    .venv/bin/python tools/greedy_foveal/run.py checks    --run <scratch>/smoke1
    .venv/bin/python tools/greedy_foveal/run.py visualize --run <scratch>/smoke1 --vis <scratch>/smoke1-vis
    # dev runs (scratchpad only): 40 fixations; and 10 fixations with GAIN_MIN monkeypatched to 0.9 to force the global path
    git commit (a437df0) && git push
    .venv/bin/python tools/greedy_foveal/run.py explore   --run previews/greedy-foveal-explorer-v0 --max-fix 200
    .venv/bin/python tools/greedy_foveal/run.py evaluate  --run previews/greedy-foveal-explorer-v0
    .venv/bin/python tools/greedy_foveal/run.py checks    --run previews/greedy-foveal-explorer-v0
    .venv/bin/python tools/greedy_foveal/run.py visualize --run previews/greedy-foveal-explorer-v0 \
        --vis visuals/greedy-foveal-explorer-v0

`previews/` and `visuals/` are the shared checkout's gitignored trees (`/home/lvelho/rd/f3d-vision/…`).

## Algorithm (as run)

    g = (yaw 0, pitch 0) in H0; the map M, S_seen and S_depth start empty
    loop:
      render the binocular foveal pair at g (persistent Blender server; only the eyes rotate)
      correspondence = accepted AB1b compute_oracle (Object Index > 0, unchanged)
                     + an Object Index 0 extension: project the left Position into the right camera and keep the pair
                       if the nearest right pixel is a hit with index 0 within 5 mm + 1 % of range
      xyz = accepted AB1b compute_epipolar (spherical epipolar triangulation) -> valid H0 points, any instance
      M  <- fuse(M, xyz)    FSG3 12-mm rule: nearest surfel strictly within 12 mm over the 27 neighbouring 12-mm cells,
                            points that land on one surfel are averaged into it (weighted by support), the rest become
                            new surfels. No instance filter, so one global map.
      S_seen  <- 1-deg cells whose centres lie inside g's nominal 12-deg square core (cyclopean, baseline-projected frame)
      S_depth <- the cells of S_seen that hold a valid reconstructed point (its direction from the H0 origin)
      stop if SEEN >= 99 % of 4 pi, or 200 fixations, or no candidate
      LOCAL: 8 neighbours at a 7.2-deg tangent-plane offset (E W N S and the 4 diagonals) in g's local frame
             EDGE_SUPPORT = valid fraction of the outer 64-px band (or corner block) of the core toward the neighbour
             UNSEEN_GAIN  = UNSEEN solid-angle fraction of the neighbour's footprint
             eligible if edge >= 0.25, gain >= 0.25 and no visited fixation within 2 deg; take the max edge*gain
      else GLOBAL: 4-connected UNSEEN components (longitude wrap, across-pole links); in the largest by solid angle,
             take the cell farthest (in angle) from the seen boundary, skipping visited fixations
      else stop

No object identity enters gaze, fusion, local/global switching or stopping. The Object Index rides along on each
surfel only for the ORACLE / VISUALIZATION-ONLY PLY.

## Parameters (chosen once, before any run; none changed afterwards)

12-deg core (accepted sensor; 256-px core in a 640-px raster per eye; IPD 63 mm; vergence 2.1 m;
`baseline_projected`); local step 0.6 × 12 = 7.2 deg; edge band 64 px; EDGE_MIN 0.25; GAIN_MIN 0.25; visit tolerance
2 deg; stop at 99 % SEEN or 200 fixations; association radius = hash cell = 12 mm; 1-deg coverage grid; render seeds
L 2111 / R 2112 (the accepted constants), 64 spp.

## Result (full run)

| quantity | value |
|---|---|
| fixations | **200**, stopped by the **200-fixation cap** |
| saccades | **195 local, 4 global** (globals at fixations 69, 145, 184, 195); crawl lengths 68 / 76 / 39 / 11 / 6 |
| angular SEEN | **56.06 %** of 4π |
| angular DEPTH | **55.55 %** of 4π |
| **all-geometry 12-mm coverage** (Breadth-1, every first-hit cell with Position ≠ 0, including Object Index 0) | **135,451 / 255,758 cells = 52.96 %; solid angle 58.39 %** (7.186 / 12.307 sr) |
| authored-only (Object Index > 0) | 119,091 / 222,267 cells = 53.58 %; solid angle 59.84 % |
| Object Index 0 (non-catalog) only | 16,360 / 33,491 cells = 48.85 %; solid angle 50.61 % |
| distance to the nearest surfel, covered cells | median 0.80 mm, p90 2.65 mm |
| final surfels | **9,779,195** |
| valid reconstructed points | 12,549,102 total (13.3 % Object Index 0); per fixation median 65,232 of 65,536, min 28,912 |
| triangulation vs left Position (diagnostic only, never a control input) | per-fixation median 0.047 mm (median over fixations); worst fixation median 0.64 mm; worst p95 2.2 mm; worst point 7.3 mm (fixation 80 at (95.0°, −5.2°), next to the +X baseline) |

The reference is the accepted Breadth-1 canonical EXR (sha256 `4ea036fc…172f8`); 3,442 of its cells have no first
hit (windows). The orientation check found 0 cells outside their declared cell. Coverage comes from the accepted
`classroom_oracle1_eval._covered`; the vectorized cross-check agreed on every cell. The evaluation opened the EXR only
after it had verified the freeze (`freeze.json` sha256 `5716a9b6…`). During control the host audit hook recorded
1,419 opens and none under Breadth-1.

## Runtime (64 spp, RTX 4090)

| stage | total | per fixation (mean / max) |
|---|---|---|
| render (request → both EXRs written) | 153.5 s | 0.77 / 1.35 s (Cycles 0.38 s per eye) |
| correspondence (EXR load + oracle) | 6.7 s | 0.034 s |
| geometry | 4.7 s | 0.023 s |
| fusion | 43.2 s | 0.22 / 0.97 s (grows with map size and on dense near surfaces) |
| policy | 0.8 s | 0.004 / 0.08 s |
| **wall, explore** | **219 s** | 1.09 s; the Blender server was ready in 0.5 s |
| evaluate | 14.8 s | (accepted `_covered` 10.9 s) |

## Checks (`checks.json`: all pass)

- **fixed head H0:** every one of the 200 calibrations has exactly the accepted head pose.
- **finite XYZ:** the map and every per-fixation point set.
- **no duplicate fixation:** the minimum pairwise angle is 6.15°, against a 2° tolerance.
- **S_seen monotone:** the SEEN series and every cell state are non-decreasing.
- **map save/load:** a reload is bitwise equal, and a nearest-surfel query returns each reloaded surfel at distance 0.
- **Breadth-1 not opened before the freeze:** the audit is empty, and `evaluation.json` carries the hash of the verified freeze.
- **deterministic policy:** all 199 saved decision states were re-decided with identical results, and one state was decided twice.
- **fusion rule:** the vectorized global map is **bitwise equal** to the accepted `fsg3_surface_map.fuse` on its own three-plane self-test.
- **the policy check can fail:** on the forced-global dev run it reported 9 of 9 mismatches, because that run used a threshold the code does not have.
- `git diff --check` is clean for the implementation commit and for the report commit.

## What looked stupid

1. **Diagonal bias.** 183 of the 195 local moves were diagonal (SW 63, SE 54, NE 33, NW 33). Only 12 were
   axis-aligned. A diagonal neighbour overlaps the current core least (about 83 % unseen against about 58 %), so the
   greedy score always prefers it. The result is zig-zag staircase tracks that leave triangular holes (overview, B).
2. **Edge support carried almost no information.** With PERFECT correspondence in a closed room, geometry reaches
   nearly every edge: the 5th percentile of edge support was 0.73. Only 12 of 462 rejected candidates failed on edge
   support (269 failed on gain, 181 were already visited). It never caused a global saccade. In this setting the
   local/global switch was driven by unseen gain alone, and the hoped-for "boundaries remove edge support" mechanism
   did not fire.
3. **Few, late global saccades.** The crawl ran 68 / 76 / 39 / 11 / 6 fixations between jumps. Unseen territory right
   next to the start (yaw −60…0°) was never visited. The deepest-point rule sent the first jump high up, to
   (84.5°, 66.5°).
4. **The cap, not the policy, ended the run.** ESTIMATED: a 12° core covers 0.0438 sr, so 200 fixations can cover at
   most 69.7 % of 4π even with perfect, non-overlapping tiling, and at least about 287 fixations are needed for the
   whole sphere. With 99 % SEEN as the target, this fovea needs a larger cap or a larger footprint. Following the
   prompt, nothing was retuned.
5. **Cell percentages and solid-angle percentages differ.** The Breadth-1 0.5° cells oversample the poles (52.96 % of
   cells against 58.39 % of solid angle). Read the solid-angle figure.
6. **The map is per-pixel dense.** It holds 9.8 M surfels and only 22 % of incoming points matched an existing surfel,
   because the accepted rule appends every unmatched point. That gives a 587 MB `final-map.npz` and 147 MB PLYs.
7. **Near the baseline, conditioning degrades as expected.** Fixation 80 at (95.0°, −5.2°) had a 7.3 mm worst point.
   Fixation 175 at (105.9°, 4.6°) kept only 28,912 correspondences. Everything was still fused.

## What worked

- The whole loop is fast: about **1.1 s per fixation** and 219 s for 200 fixations. Rendering is 70 % of that. One
  persistent Blender process and fusion vectorized with a spatial hash make it interactive-scale.
- 64 spp was enough. The PERFECT path uses only Position and Object Index, and the geometry error is sub-millimetre at
  the median, so spp was never raised.
- The geometry is right and the reconstruction is visible: about 58 % of the room's first-hit solid angle lies within
  12 mm of the map after 200 fixations, consistent with 56 % SEEN. The top view (overview, F) shows desks, chairs and
  walls in their places.
- The Object Index 0 extension recovers non-catalog geometry: 1.67 M points, and 50.6 % solid-angle coverage of the
  non-catalog reference cells.
- The truth firewall is cheap and explicit: explore → freeze → evaluate.

## Deviations and repairs

- **No contract.** CLAUDE.md asks for a committed contract before substantial execution. Luiz's prompt for this fast
  reset said "No contract file", and this report is the only document.
- **PERFECT correspondence extended to Object Index 0.** The accepted AB1b rule needs a positive Object Index on both
  eyes, which would have excluded all non-catalog geometry. The prompt asks for all geometry, so the rule above was
  added for index-0 pixels only. Positive ids use the accepted function unchanged. Since uv_R is the exact projection
  of the left Position, the 5 mm + 1 % tolerance only decides visibility; it cannot bias the geometry.
- **Fusion was re-implemented, not imported.** The accepted `fsg3_surface_map.fuse` is pure Python, rebuilds its hash
  on every call and caps a map at 63 patches. The rule is unchanged (bitwise equal on its self-test). Three things
  differ: there is no instance filter (one global map), provenance bits are replaced by support counts plus the
  creating fixation, and patches under 100 points are fused rather than rejected.
- **Render server.** Classroom is loaded once and only the eye cameras move. The 11 extra Classroom view-layer passes
  (light, colour, AO; plus the cryptomatte-accuracy flag) are switched off so each EXR holds only Combined, Position and Object Index. Combined is
  unaffected.
- **Raw EXRs deleted after each reconstruction** in the full run. Each fixation keeps `calibration.json` and
  `points.npz`, and the pair can be re-rendered deterministically from the calibration.
- **Repairs during development:** none to accepted code. Before the freeze I fixed my own code: the hash AABB margin,
  the global depth measured from boundary cells, and figure layout. After the run, the visuals-only dashed-line fix.
- **Dev runs.** I ran a smoke run, a 40-fixation run and a forced-global run in the scratchpad. The forced-global run
  monkeypatched `GAIN_MIN` in-process only to exercise the global code path. No parameter was changed after any run,
  and Breadth-1 evaluation was never used to choose anything.

## Output files

Run: `/home/lvelho/rd/f3d-vision/previews/greedy-foveal-explorer-v0/` (1.1 GB)

- `trajectory.json`: per-fixation gaze, kind, timings, counts, fusion, coverage, candidates
- `final-map.npz`: xyz_h (float64), rgb, oracle instance id, support, first fixation
- `final-map.ply`: display RGB
- `final-map-oracle-segmentation.ply`: ORACLE / VISUALIZATION ONLY
- `coverage.npz`, `freeze.json`, `evaluation.json` / `.npz`, `checks.json`
- `fixations/fix-NNNN/{calibration.json, points.npz}`, `policy/state-NNNN.npz`, `blender.log`, `queue/`

Visual: `/home/lvelho/rd/f3d-vision/visuals/greedy-foveal-explorer-v0/overview.png` (A trajectory over the
reconstructed sphere, B SEEN/UNSEEN/DEPTH, C coverage vs fixation, D statistics, E post-hoc 12-mm coverage, F the 3-D map
from above in RGB and ORACLE segmentation). Regenerate with the `visualize` command above.

    GREEDY FOVEAL EXPLORER V0 — PROTOTYPE COMPLETE
    REVIEW PENDING
