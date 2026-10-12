# Playground-2 — sparse covering lattice: report

**Status: EXECUTED — REVIEW PENDING.** Claude Code executed this step on the workstation under the contract below.
Whether the result is accepted is Luiz's decision.

**Acceptance gate (contract §6): all of A1–A5 PASS.** A2 passes exactly at its bound: 356 fixations against
≤ 356.

Contract: [`sparse-lattice-contract.md`](sparse-lattice-contract.md).
Playground-1 report: [`gaze-lattice-report.md`](gaze-lattice-report.md).

All numbers are **MEASURED** from the run or command named with them, unless marked PROPOSED. There are three runs
in this report:

- **P2**: `previews/playground-sparse-lattice/` (C5–C7);
- **P1**: `previews/playground-gaze-lattice/` (Playground-1, code `85fb962`);
- **baseline**: `previews/greedy-foveal-official-baseline/` (code `b77b1d9`).

P1 and the baseline were read, not re-run.

## 1. Result in one paragraph

On the baseline-ring lattice, 356 gazes on 17 rings about the eye baseline, the explorer **stopped by itself at
fixation 356** with `no valid unseen fixation`. `coverage.npz` holds **0 UNSEEN cells (100.00 % SEEN, 99.26 %
DEPTH)**. The split is **315 local / 40 global** saccades. The last fixation is itself a local saccade, so the
all-global tail is **0**. It reached 99 % SEEN at **fixation 347**.

Post freeze, Breadth-1 coverage within 12 mm is **98.93 % of first-hit cells (253,023 / 255,758)** and **98.82 %
of solid angle**. That is 0.000002 below P1 (0.988228 against 0.988230), and 0.50 points above the official
baseline.

Against P1 the change takes **140 fewer fixations (−28 %)** and **249 s less wall time (416 s against 665 s)**.
`run.py checks` passes 8 / 8. As in P1, every lattice gaze was fixated exactly once (356 / 356). No repair was
needed, and no parameter was changed after any run.

## 2. Provenance

| item | value |
|---|---|
| branch | `playground/sparse-lattice` |
| start head | `70d992ee9cc3843ebefd6ffc81cc2bef81a30bb3`, verified equal to `origin/playground/sparse-lattice` before starting |
| contract commit | `5981d5b` (ClaudeChat) |
| implementation commit | `70d992e` (ClaudeChat; `explorer.py`, `check_lattice.py`) |
| commit `explore` recorded | `70d992ee9cc3843ebefd6ffc81cc2bef81a30bb3`, branch `playground/sparse-lattice`, `tracked_dirty: []` (C3 and C5 `trajectory.json` / `freeze.json`) |
| report commit | the commit that adds this file |
| workspace | an isolated worktree on a local branch tracking `origin/playground/sparse-lattice`; `.venv` and `scenes/classroom/*` symlinked from the shared checkout |

No code changed on the workstation: `70d992e` is the code that ran.

## 3. Commands actually run

From the worktree root, in contract order, with `RUNS=/home/lvelho/rd/f3d-vision/previews`. The run tool is
`.venv/bin/python tools/greedy_foveal/run.py`.

| # | command | wall | exit |
|---|---|---|---|
| C1 | `.venv/bin/python tools/greedy_foveal/check_lattice.py` | 2.6 s | 0 |
| C2 | `.venv/bin/python tools/repository/check_repository_layout.py` | interactive | 0 |
| C3 | `run.py explore --run $RUNS/playground-sparse-lattice-smoke --max-fix 75` | 81 s | 0 |
| C4 | `run.py checks --run $RUNS/playground-sparse-lattice-smoke` | interactive | 0 |
| C5 | `run.py explore --run $RUNS/playground-sparse-lattice --max-fix 600 --spp 64` | 420 s (`wall_seconds` 416.4) | 0 |
| C6 | `run.py evaluate --run $RUNS/playground-sparse-lattice` | 28.2 s | 0 |
| C7 | `run.py checks --run $RUNS/playground-sparse-lattice` | 3.7 s | 0 |
| C8 | `run.py visualize --run $RUNS/playground-sparse-lattice --vis /home/lvelho/rd/f3d-vision/visuals/playground-sparse-lattice` | 7.9 s | 0 |

C5 ran detached (`setsid nohup`) from a script file, so it would not depend on the agent's tool-call lifetime. The
command itself is as listed.

### C1 (verbatim)

    [lattice] lattice (baseline): 356 gazes on 17 rings of 10.5 deg (0.5 s); per ring [6, 11, 16, 20, 24, 27, 29, 30, 30, 30, 29, 27, 24, 20, 16, 11, 6]
    [lattice] PASS K1 the lattice covers every 1-deg cell: 64800 / 64800 cells
    [lattice] PASS K2 every gaze has a frame; every pair >= VISIT_TOL_DEG apart: frames True, min pair 5.99 deg
    [lattice] PASS K3 baseline first-step gain: diagonals 0.825, sides 0.58 (+-0.005): diagonal [0.825, 0.825, 0.825, 0.825], side [0.583, 0.583, 0.58, 0.58]
    [lattice] PASS K4 replay: stops with none, 0 UNSEEN cells, <= one fixation per gaze, no duplicate: stop none, 356 fixations (314 local / 41 global, tail 0), UNSEEN cells 0, min pair 5.99 deg, 99 % at #346 (1 s)
    [lattice] PASS K5 a mid-replay state re-decides identically: local -> (180.00, 84.00)
    [lattice] PASS K6 lattice size 356; Playground-1 pitch lattice 496: 356 gazes; pitch lattice 496
    [lattice] PASS K7 no redundant gaze; every gaze >= 6 deg from the baseline axis; start gaze on the lattice: redundant 0, closest to axis 6.00 deg, start offset 0.00e+00 deg
    [lattice] PASS N1 negative control: removing the start gaze breaks the cover: 108 cells uncovered
    [lattice] PASS N2 negative control: the 2-deg cap design breaks the 6-deg envelope: 346 gazes, closest to axis 2.00 deg
    [lattice] SUMMARY checked=9 failed=0 (3 s)

On the workstation, C1 reproduces every number the ClaudeChat sandbox recorded in `70d992e`.

### C2

    [repository-layout] SUMMARY checked=652 failed=0

### C3 (final line)

    [gfe] FROZEN 75 fixations (74 local, 0 global), stop: fixation cap 75; seen 24.53% depth 24.17%; 4,293,016 surfels; wall 80 s

### C4 (verbatim)

    [gfe] check fixed_head_H0: True
    [gfe] check finite_xyz: True
    [gfe] check no_duplicate_fixation: {'pass': True, 'min_pair_deg': 10.162593685879866}
    [gfe] check seen_monotone: True
    [gfe] check map_save_load: True
    [gfe] check breadth1_not_opened_before_freeze: True
    [gfe] check deterministic_policy: {'pass': True, 'states_rechecked': 74, 'mismatches': []}
    [gfe] check fusion_rule_equals_accepted_fsg3: True
    [gfe] CHECKS PASS

### C5 (final line)

    [gfe] FROZEN 356 fixations (315 local, 40 global), stop: no valid unseen fixation; seen 100.00% depth 99.26%; 16,943,073 surfels; wall 416 s

### C6

    [gfe] EVALUATED all-geometry 253,023/255,758 cells 98.93% (98.82% sr); authored 98.97% (98.81% sr); vectorized agrees True

### C7 (verbatim)

    [gfe] check fixed_head_H0: True
    [gfe] check finite_xyz: True
    [gfe] check no_duplicate_fixation: {'pass': True, 'min_pair_deg': 5.991769701343847}
    [gfe] check seen_monotone: True
    [gfe] check map_save_load: True
    [gfe] check breadth1_not_opened_before_freeze: True
    [gfe] check deterministic_policy: {'pass': True, 'states_rechecked': 355, 'mismatches': []}
    [gfe] check fusion_rule_equals_accepted_fsg3: True
    [gfe] CHECKS PASS

### C8

    [gfe-visuals] wrote /home/lvelho/rd/f3d-vision/visuals/playground-sparse-lattice/overview.png (2000, 3275)

## 4. Three-way comparison

Sources: each run's `trajectory.json`, `coverage.npz` and `evaluation.json`. UNSEEN cells and holes come from
`coverage.npz` `state`. Holes are counted with `explorer.unseen_components`: 4-connected, with longitude wrap and
across-pole links.

| quantity | baseline | P1 (pitch rings) | **P2 (baseline rings)** |
|---|---|---|---|
| stop reason | `seen >= 99 % of 4 pi` | `no valid unseen fixation` | `no valid unseen fixation` |
| lattice size | — | 496 | 356 |
| fixations, final | 542 | 496 | **356** |
| fixations to 99 % SEEN | 542 | 472 | **347** |
| fixations to 100 % SEEN | not reached | 496 | 356 |
| local / global saccades (+ 1 initial) | 322 / 219 | 460 / 35 | **315 / 40** |
| first global saccade | #69 | #265 | #168 |
| last local saccade | #362 | #488 | #356 (the final fixation) |
| all-global tail after the last local saccade | 180 | 8 | **0** |
| final SEEN / DEPTH (% of 4π) | 99.00 / 98.28 | 100.00 / 99.31 | **100.00 / 99.26** |
| cells UNSEEN / SEEN-no-depth / DEPTH (of 64,800) | 640 / 411 / 63,749 | 0 / 378 / 64,422 | **0** / 428 / 64,372 |
| UNSEEN holes | 184 (largest 0.00183 sr) | 0 | **0** |
| Breadth-1 12 mm, all geometry: cells | 251,966 / 255,758 = 98.52 % | 253,043 = 98.94 % | 253,023 = **98.93 %** |
| Breadth-1 12 mm, all geometry: solid angle | 98.32 % (0.983210) | 98.82 % (0.988230) | **98.82 % (0.988228)** |
| authored (Index > 0): cells / solid angle | 98.52 % / 98.25 % | 98.98 % / 98.81 % | 98.97 % / 98.81 % |
| instance 0 (non-catalog): solid angle | 98.69 % | 98.92 % | 98.91 % |
| covered cells, NN distance median / p90 | 0.727 / 2.240 mm | 0.723 / 2.190 mm | 0.713 / 2.123 mm |
| final surfels | 16,517,811 | 16,702,245 | 16,943,073 |
| wall (`wall_seconds`) | 733.1 s | 665.3 s | **416.4 s** |
| wall per fixation | 1.353 s | 1.341 s | 1.170 s |
| breakdown (sum over fixations): render | 413.5 s | 373.0 s | 270.7 s |
| correspondence (incl. EXR load) | 18.2 s (9.3 s) | 16.4 s (8.3 s) | 11.9 s (6.1 s) |
| geometry | 12.6 s | 11.5 s | 8.2 s |
| fusion | 257.8 s | 236.6 s | 105.7 s |
| policy | 3.3 s | 2.8 s | 1.6 s |
| sum of per-fixation totals / server start | 731.9 s / 0.50 s | 664.2 s / 0.45 s | 415.3 s / 0.50 s |
| `evaluate` (Breadth-1 coverage) | 26.3 s | 26.5 s | 27.4 s |
| `run.py checks` | pass | pass | pass (8 / 8) |

Two P2 figures stand out against P1:

- **Fusion time fell further than the fixation count.** Per fixation it dropped from 0.477 s to 0.297 s, while
  render time per fixation is unchanged (0.75–0.76 s).
- **The final map has more surfels with fewer fixations** (+240,828).

Both are consistent with less overlap between views (section 5), but neither is attributed further here.

### SEEN / DEPTH versus fixation (checkpoint table)

From each run's `coverage.npz` `seen_history` / `depth_history`: SEEN % / DEPTH % of 4π after fixation n.

| fixation | baseline | P1 | P2 |
|---|---|---|---|
| #100 | 28.48 / 28.09 | 31.96 / 31.43 | 32.41 / 31.95 |
| #200 | 56.06 / 55.55 | 60.53 / 60.06 | 62.89 / 62.25 |
| #300 | 79.62 / 78.72 | 82.42 / 81.58 | 89.29 / 88.60 |
| #346 | 88.37 / 87.51 | 89.52 / 88.55 | 98.90 / 98.18 |
| final | 99.00 / 98.28 (#542) | 100.00 / 99.31 (#496) | **100.00 / 99.26 (#356)** |

P2 leads at every checkpoint. Panel C of its overview shows a nearly straight SEEN curve up to the stop.

### Visual

`visuals/playground-sparse-lattice/overview.png` (2000 × 3275; sha256 `6690f37f…45f9`), in the shared checkout's
`visuals/`.

- Panel A: the trajectory, with the 40 global targets numbered.
- Panel B: the final coverage state, 0.0 % UNSEEN. The fixation centres trace the baseline rings.
- Panel C: SEEN / DEPTH versus fixation.
- Panels D–F: the statistics, the Breadth-1 cells and the map from above.

Regenerate with C8. The comparisons are `visuals/playground-gaze-lattice/overview.png` (P1) and
`visuals/greedy-foveal-official-baseline/overview.png`.

## 5. Lattice use and the near-axis region

- **Every lattice gaze was fixated, exactly once.** All 356 fixations lie on a lattice gaze (largest offset
  1.2 × 10⁻⁶ deg), and they cover all 356 distinct gazes. So when visited, each gaze still added unseen area, and
  the stop came when the lattice was exhausted. As in P1 (496 / 496), the fixation count is the lattice size.
- **Overlap at decision time.** The unseen gain of the chosen gaze is much higher than in P1:

  | | local moves: median | local moves: below 0.25 | global moves: median | global moves: below 0.25 |
  |---|---|---|---|---|
  | P1 | 0.599 | 117 / 460 | 0.235 | 20 / 35 |
  | P2 | 0.847 | 4 / 315 | 0.713 | 0 / 40 |

  In P2 the smallest chosen gain is 0.111 for a local move and 0.278 for a global one.
- **Near the baseline axis.** This is the cap rings' region: cells whose centre lies within 15° of the axis
  (θ_c ≤ 15° or ≥ 165°), 1,432 cells.

  | | DEPTH cells | DEPTH fraction: cells / solid angle | SEEN-no-depth | UNSEEN |
  |---|---|---|---|---|
  | baseline | 1,319 | 92.11 % / 92.06 % | 94 | 19 |
  | P1 | 1,334 | 93.16 % / 93.10 % | 98 | 0 |
  | P2 | **1,337** | **93.37 % / 93.31 %** | 95 | 0 |

  The closest P2 fixation to the axis is 6.00°, the envelope of §2.
- **Fixation 1 equals the baseline's.** It is at gaze (0°, 0°), which is on the θ = 90° ring. Its `xyz_h`,
  `instance_id_oracle` and `err_mm` match the baseline's fixation 1 exactly. Only the presentation RGB differs.
  The first decision is lattice gaze 134, NE (+10.73°, +11.80°).
- **The smoke prefix is deterministic.** Fixations 1–75 of C5 equal C3 in gaze and kind, with bitwise-equal
  `xyz_h` and an equal `seen_history`.
- The first global jump is fixation 168, decided when 189 unvisited lattice gazes still had unseen gain. The freeze
  audit recorded 2,512 host opens and 0 Breadth-1 opens. The render server exited 0. Coverage cells were monotone.

## 6. Acceptance gate (contract §6)

Judged on C5–C7 only.

| # | criterion | measured | result |
|---|---|---|---|
| A1 | stops by itself with `no valid unseen fixation`; 0 UNSEEN cells | `no valid unseen fixation`; 0 UNSEEN cells | **PASS** |
| A2 | fixations ≤ 356 | 356 | **PASS** (at the bound) |
| A3 | global saccades ≤ 60; all-global tail ≤ 25 | 40 global; tail 0 | **PASS** |
| A4 | `run.py checks` passes every check | 8 / 8, `CHECKS PASS` | **PASS** |
| A5 | Breadth-1 12-mm solid angle ≥ 98.32 % | 98.82 % | **PASS** |

**Reported, not gated:** the 12-mm solid angle against P1 changed by −0.0002 percentage points (0.988228 against
0.988230). By cells, it is 20 fewer of 255,758.

## 7. Proposed versus measured

| quantity | PROPOSED (contract §6 / check K4, coverage-only replay) | MEASURED (C5–C6) |
|---|---|---|
| fixations | 356 | 356 |
| local / global | 314 / 41 | 315 / 40 |
| all-global tail | 0 | 0 |
| 99 % SEEN at | #346 | #347 |
| UNSEEN cells at stop | 0 | 0 |
| wall | about 8 min (ESTIMATED, 356 × 1.34 s) | 6.9 min (416 s) |

The contract expected the windows to add global jumps in the real run. Here the real run has one global saccade
fewer than the replay.

## 8. Deviations, findings and repairs

- **Repairs: none.** No code, lattice parameter, threshold, check or gate changed. The code that ran is `70d992e`.
- **D1. Overview title.** The overview still reads "Greedy Foveal Explorer v0 — …", the default title. The contract's
  C8 passes no `--title`, and `visuals.py` is unchanged by §3. Panel D carries this run's own numbers and stop
  reason.
- **D2. Comparison numbers.** As instructed, no tool file was added. The three-way figures, checkpoints, lattice
  use, chosen gains and near-axis fractions come from a scratch script outside the repository. It reads only the
  three runs' `trajectory.json`, `coverage.npz` and `evaluation.json`, and uses `explorer.unseen_components`,
  `explorer.lattice` (`LATTICE_KIND` `"baseline"` for P2, `"pitch"` for P1) and `explorer.CELL_DIR` / `CELL_W`.
- **F1. A premise of contract §2 is not borne out for v0.** §2 says: "No v0 or Playground-1 fixation came closer
  than 6°" to the baseline axis. MEASURED from the official baseline's `trajectory.json`, which is bitwise equal to
  v0 grow600 in every gaze: two v0 fixations came closer than 6°.
  - #416, global, (+89.5°, +0.5°): 0.71° from the axis;
  - #386, global, (−89.5°, −2.5°): 2.55° from the axis.

  Playground-1's closest fixation is 6.00°. This does not affect the run, the checks or the gate. It only bears on
  the stated motivation for the 6° envelope, which stays a design choice for Luiz and Chat.

## 9. Run evidence

| path (shared checkout) | contents |
|---|---|
| `previews/playground-sparse-lattice/` | C5–C7: 356 fixations. `freeze.json` (sha256 `3f8bf4bd…4a7d`), `coverage.npz` (`88f0fa44…c937`), `trajectory.json` (`9668a5d6…c3bd7`), `evaluation.json` (`5ecc4828…ac42`), `checks.json` (`e72dba6b…44e4`), the map, PLYs and policy states. 2.0 GB. |
| `previews/playground-sparse-lattice-smoke/` | C3–C4: 75 fixations. 472 MB. |
| `visuals/playground-sparse-lattice/overview.png` | C8 (sha256 `6690f37f…45f9`) |

## 10. Open items for Luiz and Chat

- Acceptance of Playground-2, and whatever follows from it, is Luiz's decision. This branch makes no acceptance
  claim.
- The fixation count is again the lattice size, and every gaze still added area when visited. Going below 356
  would need a smaller lattice: for example the 2° cap (346 gazes; C1 N2 on the workstation) or a different
  ring spacing. Either is a new decision, and the 2° cap also brings in near-axis stereo.
- F1: the 6° envelope's stated motivation does not hold for v0. Whether this changes the envelope decision is open.
