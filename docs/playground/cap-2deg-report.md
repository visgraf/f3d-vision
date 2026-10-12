# Playground-3 — the 2° cap lattice: report

**Status: ACCEPTED** by Luiz on 2026-10-12, as a playground result; **not promoted** (section 11). Claude Code
executed this step on the workstation under the contract below; ClaudeChat reviewed it.

    PLAYGROUND3_CAP_2DEG_ACCEPTED

**Acceptance gate (contract §6): all of A1–A6 PASS.** A2 passes exactly at its bound: 346 fixations against ≤ 346.

Contract: [`cap-2deg-contract.md`](cap-2deg-contract.md).
Official baseline: [Engineering-2 report](../engineering/sparse-lattice-baseline-report.md).
Playground-2 report: [`sparse-lattice-report.md`](sparse-lattice-report.md).

All numbers are **MEASURED** from the run or command named with them, unless marked PROPOSED. There are two runs in
this report:

- **P3**: `previews/playground-cap-2deg/` (C5–C7);
- **official**: `previews/greedy-foveal-official-baseline-2/` (Engineering-2, code `a5f1aae`, bitwise equal to the
  Playground-2 run). It was read, not re-run.

## 1. Result in one paragraph

On the 2° cap lattice, 346 gazes on 17 baseline rings at θ = 2°, 13°, …, 178°, the explorer **stopped by itself at
fixation 346** with `no valid unseen fixation`. `coverage.npz` holds **0 UNSEEN cells (100.00 % SEEN, 99.20 %
DEPTH)**. The split is **309 local / 36 global** saccades, with an all-global tail of **4**. It reached 99 % SEEN at
**fixation 340**.

Post freeze, Breadth-1 coverage within 12 mm is **98.93 % of first-hit cells (253,031 / 255,758)** and **98.83 % of
solid angle**, against the official 98.82 % (+0.006 points, +8 cells).

**Near the baseline axis nothing changed.** The coverage state of every cell within 15° of the axis is identical,
cell for cell, to the official run's: DEPTH 93.31 % of that solid angle in both. The cap-ring fixations add no near-axis
depth that the 6° lattice lacked.

The run took 10 fewer fixations and 14 s less wall time (399 s against 413 s). Overall DEPTH fell by 0.06 points,
41 cells, all farther than 15° from the axis. `run.py checks` passes 8 / 8. Every one of the 346 lattice gazes was
fixated once.

No repair was needed, and no parameter was changed after any run. One contract command, C8, could not run as written
(section 8, D1).

## 2. Provenance

| item | value |
|---|---|
| official-baseline tag | `greedy-foveal-playground-baseline-2` → `9bf936d95540ea2f5d7121c20c187ae7c814b5c5` (annotated tag object `2450f115cf7f809e6d3fd01844c80970aac78320`), created and pushed by Claude Code at the start of this step on Luiz's instruction, after verifying that `9bf936d` is `origin/main` and changes only docs relative to the Engineering-2 run's code `a5f1aae`. |
| branch | `playground/cap-2deg`, from `main` `9bf936d` |
| start head | `1fe6bd2fe1b179ede2ffea0d9299ff9dbec225ac`, verified equal to `origin/playground/cap-2deg` before starting |
| contract commit | `97528ef` (ClaudeChat) |
| implementation commit | `1fe6bd2` (ClaudeChat): two `explorer.py` constants and `check_lattice.py` |
| commit `explore` recorded | `1fe6bd2fe1b179ede2ffea0d9299ff9dbec225ac`, branch `playground/cap-2deg`, `tracked_dirty: []` (C3 and C5) |
| report commit | the commit that adds this file |
| workspace | an isolated worktree on a local branch tracking `origin/playground/cap-2deg`; `.venv` and `scenes/classroom/*` symlinked from the shared checkout |

No code changed on the workstation: `1fe6bd2` is the code that ran.

## 3. Commands actually run

From the worktree root, in contract order, with `RUNS=/home/lvelho/rd/f3d-vision/previews`. The run tool is
`.venv/bin/python tools/greedy_foveal/run.py`.

| # | command | wall | exit |
|---|---|---|---|
| C1 | `.venv/bin/python tools/greedy_foveal/check_lattice.py` | 3.0 s | 0 |
| C2 | `.venv/bin/python tools/repository/check_repository_layout.py` | interactive | 0 |
| C3 | `run.py explore --run $RUNS/playground-cap-2deg-smoke --max-fix 75` | 84 s | 0 |
| C4 | `run.py checks --run $RUNS/playground-cap-2deg-smoke` | interactive | 0 |
| C5 | `run.py explore --run $RUNS/playground-cap-2deg --max-fix 600 --spp 64` | 402 s (`wall_seconds` 398.7) | 0 |
| C6 | `run.py evaluate --run $RUNS/playground-cap-2deg` | 27.5 s | 0 |
| C7 | `run.py checks --run $RUNS/playground-cap-2deg` | interactive | 0 |
| C8 | `run.py visualize --run $RUNS/playground-cap-2deg --vis /home/lvelho/rd/f3d-vision/visuals/playground-cap-2deg --title "Playground-3 2° cap lattice — …"` | 0.1 s | **2**: `run.py: error: unrecognized arguments: --title …` |
| C8′ | `.venv/bin/python tools/greedy_foveal/visuals.py --run $RUNS/playground-cap-2deg --vis /home/lvelho/rd/f3d-vision/visuals/playground-cap-2deg --title "Playground-3 2° cap lattice — FIXATE → RECONSTRUCT → SACCADE (Classroom, fixed head H0)"` (D1) | 7.9 s | 0 |

C5 ran detached (`setsid nohup`) from a script file, so it would not depend on the agent's tool-call lifetime. The
command itself is as listed.

### C1 (verbatim)

    [lattice] lattice (baseline): 346 gazes on 17 rings of 11 deg (0.5 s); per ring [4, 9, 15, 20, 24, 27, 29, 30, 30, 30, 29, 27, 24, 20, 15, 9, 4]
    [lattice] PASS K1 the lattice covers every 1-deg cell: 64800 / 64800 cells
    [lattice] PASS K2 every gaze has a frame; every pair >= VISIT_TOL_DEG apart: frames True, min pair 2.83 deg
    [lattice] PASS K3 baseline first-step gain: diagonals 0.825, sides 0.58 (+-0.005): diagonal [0.825, 0.825, 0.825, 0.825], side [0.583, 0.583, 0.58, 0.58]
    [lattice] PASS K4 replay: stops with none, 0 UNSEEN cells, <= one fixation per gaze, no duplicate: stop none, 346 fixations (311 local / 34 global, tail 0), UNSEEN cells 0, min pair 2.83 deg, 99 % at #336 (1 s)
    [lattice] PASS K5 a mid-replay state re-decides identically: local -> (-82.37, 67.79)
    [lattice] PASS K6 lattice size 346; official 6-deg lattice 356; Playground-1 pitch lattice 496: 346 gazes; official 356; pitch lattice 496
    [lattice] PASS K7 no redundant gaze; every gaze >= 2 deg from the baseline axis; start gaze on the lattice: redundant 0, closest to axis 2.00 deg, start offset 0.00e+00 deg
    [lattice] PASS N1 negative control: removing the start gaze breaks the cover: 120 cells uncovered
    [lattice] PASS N2 negative control: the 1-deg cap design breaks the 2-deg minimum pair: 342 gazes, min pair 1.73 deg, redundant 2
    [lattice] SUMMARY checked=9 failed=0 (3 s)

On the workstation, C1 reproduces the sandbox numbers of contract §2: 346 gazes, the per-ring counts, the 2.83° pair
and the 1° cap's 342 gazes.

### C2

    [repository-layout] SUMMARY checked=656 failed=0

### C3 (final line)

    [gfe] FROZEN 75 fixations (74 local, 0 global), stop: fixation cap 75; seen 25.42% depth 25.06%; 4,621,297 surfels; wall 82 s

### C4 (verbatim)

    [gfe] check fixed_head_H0: True
    [gfe] check finite_xyz: True
    [gfe] check no_duplicate_fixation: {'pass': True, 'min_pair_deg': 10.295817751202843}
    [gfe] check seen_monotone: True
    [gfe] check map_save_load: True
    [gfe] check breadth1_not_opened_before_freeze: True
    [gfe] check deterministic_policy: {'pass': True, 'states_rechecked': 74, 'mismatches': []}
    [gfe] check fusion_rule_equals_accepted_fsg3: True
    [gfe] CHECKS PASS

### C5 (final line)

    [gfe] FROZEN 346 fixations (309 local, 36 global), stop: no valid unseen fixation; seen 100.00% depth 99.20%; 16,969,119 surfels; wall 399 s

### C6

    [gfe] EVALUATED all-geometry 253,031/255,758 cells 98.93% (98.83% sr); authored 98.97% (98.81% sr); vectorized agrees True

### C7 (verbatim)

    [gfe] check fixed_head_H0: True
    [gfe] check finite_xyz: True
    [gfe] check no_duplicate_fixation: {'pass': True, 'min_pair_deg': 2.8281398674428297}
    [gfe] check seen_monotone: True
    [gfe] check map_save_load: True
    [gfe] check breadth1_not_opened_before_freeze: True
    [gfe] check deterministic_policy: {'pass': True, 'states_rechecked': 345, 'mismatches': []}
    [gfe] check fusion_rule_equals_accepted_fsg3: True
    [gfe] CHECKS PASS

### C8′

    [gfe-visuals] wrote /home/lvelho/rd/f3d-vision/visuals/playground-cap-2deg/overview.png (2000, 3275)

## 4. Comparison with the official baseline run

Sources: each run's `trajectory.json`, `coverage.npz` and `evaluation.json`. Holes are counted with
`explorer.unseen_components`.

| quantity | official (6° cap) | **P3 (2° cap)** |
|---|---|---|
| stop reason | `no valid unseen fixation` | `no valid unseen fixation` |
| lattice size | 356 | 346 |
| fixations, final | 356 | **346** |
| fixations to 99 % SEEN | 347 | **340** |
| local / global saccades (+ 1 initial) | 315 / 40 | **309 / 36** |
| first global saccade | #168 | #81 (to the θ = 2° cap gaze (+88°, 0°)) |
| last local saccade | #356 | #342 |
| all-global tail after the last local saccade | 0 | **4** |
| final SEEN / DEPTH (% of 4π) | 100.00 / 99.26 | **100.00 / 99.20** |
| cells UNSEEN / SEEN-no-depth / DEPTH (of 64,800) | 0 / 428 / 64,372 | **0** / 469 / 64,331 |
| UNSEEN holes | 0 | **0** |
| Breadth-1 12 mm, all geometry: cells | 253,023 / 255,758 = 98.93 % | 253,031 / 255,758 = **98.93 %** |
| Breadth-1 12 mm, all geometry: solid angle | 98.8228 % | **98.8287 %** |
| authored (Index > 0): cells / solid angle | 98.97 % / 98.81 % | 98.97 % / 98.81 % |
| instance 0 (non-catalog): solid angle | 98.91 % | 98.94 % |
| covered cells, NN distance median / p90 | 0.713 / 2.123 mm | 0.711 / 2.123 mm |
| final surfels | 16,943,073 | 16,969,119 |
| wall (`wall_seconds`) | 412.8 s | **398.7 s** |
| wall per fixation | 1.159 s | 1.152 s |
| breakdown (sum over fixations): render | 269.9 s | 264.0 s |
| correspondence (incl. EXR load) | 11.9 s (6.1 s) | 11.5 s (5.8 s) |
| geometry | 8.2 s | 7.9 s |
| fusion | 103.4 s | 96.2 s |
| policy | 1.6 s | 1.5 s |
| sum of per-fixation totals / server start | 411.8 s / 0.45 s | 397.7 s / 0.45 s |
| `evaluate` (Breadth-1 coverage) | 26.8 s | 26.6 s |
| `run.py checks` | pass | pass (8 / 8; min fixation pair 2.83°) |

**Where the DEPTH difference lies.** The official run has 110 cells with DEPTH that P3 sees without depth, and P3 has
69 cells with DEPTH that the official run sees without depth. That is net −41 cells: −0.0192 sr lost, +0.0120 sr
gained. Every one of these cells is 15.6°–79.6° from the baseline axis: they come from the different view set
elsewhere on the sphere, not from the cap.

### SEEN / DEPTH versus fixation

From each run's `coverage.npz`: SEEN % / DEPTH % of 4π after fixation n.

| fixation | official | P3 |
|---|---|---|
| #100 | 32.41 / 31.95 | 33.54 / 33.06 |
| #200 | 62.89 / 62.25 | 64.28 / 63.55 |
| #300 | 89.29 / 88.60 | 90.66 / 89.93 |
| #336 | 96.83 / 96.14 | 98.62 / 97.82 |
| #346 | 98.90 / 98.18 | **100.00 / 99.20** (final) |
| final | 100.00 / 99.26 (#356) | 100.00 / 99.20 (#346) |

P3 leads in SEEN at every checkpoint.

### Visual

`visuals/playground-cap-2deg/overview.png` (2000 × 3275; sha256 `eb37a444…f226d`), in the shared checkout's
`visuals/`, with the Playground-3 title. It shows:

- panel A: the trajectory, with the 36 global targets numbered. Local saccades along the θ = 90° ring draw the
  vertical lines at yaw 0° and ±180°;
- panel B: the final coverage state, 0.0 % UNSEEN, 0.8 % SEEN without depth;
- panel C: SEEN / DEPTH versus fixation;
- panels D–F: the statistics, the Breadth-1 cells and the map from above.

In panel A, the label of global target #139 is partly hidden under the "end #346" label. This is a `visuals.py`
label placement, outside this step's permitted fixes.

## 5. Near-axis analysis

Cells are counted by the angle θ_c of the cell centre from the baseline axis (+X); "within d" means θ_c ≤ d or
≥ 180° − d. Solid angle is weighted with `explorer.CELL_W`.

| region | cells | official: DEPTH cells / cells % / solid angle % | P3: DEPTH cells / cells % / solid angle % |
|---|---|---|---|
| within 15° | 1,432 | 1,337 / 93.37 % / **93.31 %** | 1,337 / 93.37 % / **93.31 %** |
| within 5° | 160 | 114 / 71.25 % / 71.24 % | 114 / 71.25 % / 71.24 % |

- **The two runs' coverage states are identical within 15° of the axis, cell for cell** (`np.array_equal` on the
  masked `state`). Neither has an UNSEEN cell there.
- The SEEN-without-depth cells near the axis are the same in both runs. In P3: 10 of the 24 cells within 2°,
  23 / 64 within 3°, 36 / 104 within 4°, 46 / 160 within 5°.
- So the 2° cap ring fixates these cells, and they remain without depth. Whether that is near-epipole triangulation
  failure, missing geometry or the 12-mm map is not diagnosed here.

### The eight cap-ring fixations (θ = 2° and 178°)

Points are the fixation's valid PERFECT correspondences. The error is the diagnostic error against the left-eye
Position, as median / p95. For comparison, the run's median fixation has 65,179 points, with a median error of
0.048 mm and a p95 of 0.075 mm (medians over all 346 fixations).

| fixation | kind | gaze (yaw, pitch) | θ | points | error median / p95 (mm) | new surfels |
|---|---|---|---|---|---|---|
| #52 | local | (−88°, 0°) | 178° | 65,270 | 0.213 / 0.737 | 65,095 |
| #81 | global | (+88°, 0°) | 2° | 34,577 | 1.774 / 3.365 | 34,577 |
| #258 | local | (+92°, 0°) | 2° | 25,279 | 1.272 / 2.898 | 4,480 |
| #260 | local | (+90°, −2°) | 2° | 34,754 | 1.058 / 2.445 | 1,287 |
| #311 | local | (+90°, +2°) | 2° | 20,749 | 1.169 / 2.519 | 461 |
| #338 | local | (−90°, −2°) | 178° | 65,280 | 0.227 / 0.793 | 9,858 |
| #340 | local | (−92°, 0°) | 178° | 65,271 | 0.222 / 0.749 | 1,534 |
| #342 | local | (−90°, +2°) | 178° | 65,536 | 0.253 / 0.926 | 1,158 |

- **The θ = 178° side (−X)** keeps a full point count. Its error is about 4–5 × the run median, 0.21–0.25 mm.
- **The θ = 2° side (+X)** gives 20,749–34,754 points, 32–53 % of the median. Its error is 1.06–1.77 mm, about
  20–40 × the median.
- **The official 6° cap ring shows the same asymmetry,** for context: θ = 6° gives 16,730–51,716 points at
  0.61–1.43 mm, and θ = 174° gives 65,250–65,506 points at 0.08–0.19 mm. The +X side of the head faces the windows
  in this scene; the asymmetry is not attributed further here.

## 6. Lattice use

- **Every lattice gaze was fixated, exactly once.** All 346 fixations lie on a lattice gaze (largest offset
  1.5 × 10⁻⁶ deg) and cover all 346 distinct gazes. As in Playground-1 and Playground-2, the fixation count is the
  lattice size. The closest fixation to the axis is 2.00°.
- **The smoke prefix is deterministic.** Fixations 1–75 of C5 equal C3 in gaze, kind and bitwise `xyz_h`.
- Fixation 1 is the shared start gaze (0°, 0°). The runs diverge at the first decision: P3 goes S to (0°, −12°),
  the official run NE to (+10.73°, +11.80°).
- The freeze audit recorded 2,442 host opens and 0 Breadth-1 opens. The render server exited 0. Coverage cells were
  monotone.

## 7. Acceptance gate (contract §6)

Judged on C5–C7 only.

| # | criterion | measured | result |
|---|---|---|---|
| A1 | stops by itself with `no valid unseen fixation`; 0 UNSEEN cells | `no valid unseen fixation`; 0 UNSEEN cells | **PASS** |
| A2 | fixations ≤ 346 | 346 | **PASS** (at the bound) |
| A3 | global saccades ≤ 60; all-global tail ≤ 25 | 36 global; tail 4 | **PASS** |
| A4 | `run.py checks` passes every check (no duplicate fixation ≥ 2°) | 8 / 8; min pair 2.83° | **PASS** |
| A5 | Breadth-1 12-mm solid angle ≥ 98.80 % | 98.83 % (0.988287) | **PASS** |
| A6 | DEPTH fraction of the solid angle within 15° of the axis ≥ 92.81 % | 93.31 % (identical to the official run) | **PASS** |

### Proposed versus measured

| quantity | PROPOSED (contract §6 / check K4, coverage-only replay) | MEASURED (C5–C6) |
|---|---|---|
| fixations | 346 | 346 |
| local / global | 311 / 34 | 309 / 36 |
| all-global tail | 0 | 4 |
| 99 % SEEN at | #336 | #340 |
| wall | about 7 min (ESTIMATED, 346 × 1.17 s) | 6.6 min (399 s) |

## 8. Deviations, findings and repairs

- **Repairs: none.** No code, lattice constant, threshold, check or gate changed. The code that ran is `1fe6bd2`.
- **D1. C8 cannot run as written.** `run.py visualize` has no `--title` option: `run.py` exits 2 with
  "unrecognized arguments". Only `visuals.py`'s own command line takes `--title`. `run.py` is unchanged by contract
  §3, and no code fix is delegated. The overview was therefore made with `visuals.py` (C8′), which calls the same
  `overview()` function that `run.py visualize` calls. This is the route the accepted Playground-1 visualization
  package used. The arguments are the contract's: the same run, `--vis` and `--title`, and no marks. The output is
  `overview.png` with the Playground-3 title.
- **D2. Comparison numbers.** As instructed, no tool file was added. The comparison, checkpoints, near-axis
  fractions, cap-ring rows and lattice use come from a scratch script outside the repository. It reads only the two
  runs' `trajectory.json`, `coverage.npz` and `evaluation.json`, using `explorer.unseen_components`,
  `explorer.build_baseline_lattice`, `explorer.CELL_DIR` and `explorer.CELL_W`.
- **F1. The near-axis region did not change.** Contract §6 calls the near-axis region "where the change acts". In
  coverage terms it did not act: the near-axis state is identical in both runs. A6 passes because nothing there got
  worse, not because anything got better.

## 9. Run evidence

| path (shared checkout) | contents |
|---|---|
| `previews/playground-cap-2deg/` | C5–C7: 346 fixations. `freeze.json` (sha256 `3580e239…21dc`), `coverage.npz` (`8ecf4623…1f3e`), `trajectory.json` (`f0d6ee2b…1cfb`), `evaluation.json` (`f0553acf…2798`), `checks.json` (`b0bca5d8…f9ec`), the map, PLYs and policy states. 1.9 GB. |
| `previews/playground-cap-2deg-smoke/` | C3–C4: 75 fixations. 502 MB. |
| `visuals/playground-cap-2deg/overview.png` | C8′ (sha256 `eb37a444…f226d`) |

## 10. Open items for Luiz and Chat

- Acceptance of Playground-3, and whatever follows from it, is Luiz's decision.
- The fixation count is again the lattice size. The 10-fixation saving is all the cap gives: 12-mm coverage +0.006
  points, near-axis DEPTH unchanged, overall DEPTH −0.06 points.
- The near-axis SEEN-without-depth cells, 46 within 5° in both runs, are not reached by moving the cap. If they
  matter, the cause (near-epipole geometry, scene content or the map) is a separate question.
- `run.py visualize` lacks `--title` (D1). A future contract either uses `visuals.py` or adds the option in an
  authorized step.

## 11. Acceptance

**Decision (Luiz, 2026-10-12): ACCEPTED as a playground result, and NOT promoted.** The gain, 10 fixations (2.8 %)
and 14 s, is too small for an Engineering step. The official baseline stays the 6° lattice (tag
`greedy-foveal-playground-baseline-2`). The 2° cap code is preserved at the annotated tag **`playground-3-cap-2deg`**,
which points to the commit that adds this section.

- **The near-axis SEEN-without-depth cells** (46 within 5° of the axis, identical in both runs) were checked visually
  by Luiz: they are mostly the windows, which have no first-hit geometry. They are not diagnosed further.
- **ClaudeChat review.** `e53851d` adds only this report, on top of `1fe6bd2`, the code `explore` recorded with a
  clean tree. The layout checker gives 656 checked, 0 failed (Chat-sandbox). The counts are consistent:
  309 + 36 + 1 = 346; 253,031 / 255,758 = 98.93 %.
- **F1 confirms the contract's own geometry.** The cap changes which gazes cover the near-axis region, not how well
  its points triangulate. The near-axis coverage state is identical cell for cell.
- **The cap-ring views are poor even with oracle correspondence.** The +X ring kept 32–53 % of the points, at 1.1–1.8
  mm median error (section 5), consistent with the 1/sin γ conditioning: 28.7× at 2°, 9.6× at 6°.
- **D1 was the contract's error.** `run.py visualize` has no `--title`; Claude Code's use of `visuals.py` was the
  right route.
