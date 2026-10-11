# Playground-1 — gaze lattice: report

**Status: ACCEPTED** by Luiz on 2026-10-11, as a playground result (section 11). Executed on the workstation by
Claude Code under the contract below; reviewed by ClaudeChat.

    PLAYGROUND1_GAZE_LATTICE_ACCEPTED

**Acceptance gate (contract §6): all of A1–A5 PASS.**

Contract: [`gaze-lattice-contract.md`](gaze-lattice-contract.md).
Baseline report: [`greedy-foveal-playground-baseline-report.md`](../engineering/greedy-foveal-playground-baseline-report.md).
Quick start: [`tools/greedy_foveal/README.md`](../../tools/greedy_foveal/README.md).

Every number below is **MEASURED** from the run or command named with it, unless it is marked PROPOSED.

## 1. Result in one paragraph

With gaze candidates restricted to the fixed 496-gaze covering lattice, the explorer **stopped by itself at fixation
496** with `no valid unseen fixation`. `coverage.npz` holds **0 UNSEEN cells (100.00 % SEEN, 99.31 % DEPTH)**. The
split is **460 local / 35 global** saccades, with an **all-global tail of 8 fixations** after the last local saccade
(#488). It reached 99 % SEEN at **fixation 472**. Post freeze, Breadth-1 coverage within 12 mm is **98.94 % of
first-hit cells (253,043 / 255,758)** and **98.82 % of first-hit solid angle**. The official baseline gives 542
fixations, 99.00 % SEEN, 640 UNSEEN cells in 184 holes, 322 / 219 saccades with a 180-fixation all-global tail, and
98.32 % solid angle. `run.py checks` passes 8 / 8. No repair was needed, and no parameter was changed after any run.
In this run the fixation count equals the lattice size: each of the 496 lattice gazes was fixated exactly once
(section 7).

## 2. Provenance

| item | value |
|---|---|
| branch | `playground/gaze-lattice` |
| start head | `85fb962e90571d911ce8aeb24238b9c8c10d45a5`, verified equal to `origin/playground/gaze-lattice` before starting |
| contract commit | `326699c36624b55b4323b19bdec16e505874ce73` (ClaudeChat) |
| implementation commit | `85fb962e90571d911ce8aeb24238b9c8c10d45a5` (ClaudeChat; `explorer.py`, `check_lattice.py`, contract §2.4 revision) |
| commit `explore` recorded | `85fb962e90571d911ce8aeb24238b9c8c10d45a5`, branch `playground/gaze-lattice`, `tracked_dirty: []` (both runs' `trajectory.json` / `freeze.json` `code`) |
| baseline run | `previews/greedy-foveal-official-baseline/` (code `b77b1d9c…`, Engineering-1), read only, not re-run |
| workspace | an isolated worktree on a local branch tracking `origin/playground/gaze-lattice`; `.venv` and `scenes/classroom/*` symlinked from the shared checkout, per the README |
| report commit | the commit that adds this file |

No code changed on the workstation: `85fb962` is the code that ran.

## 3. Commands actually run

From the worktree root, in contract order, with `RUNS=/home/lvelho/rd/f3d-vision/previews`. The run tool is
`.venv/bin/python tools/greedy_foveal/run.py`.

| # | command | wall | exit |
|---|---|---|---|
| C1 | `.venv/bin/python tools/greedy_foveal/check_lattice.py` | 4.2 s | 0 |
| C2 | `.venv/bin/python tools/repository/check_repository_layout.py` | 0.9 s | 0 |
| C3 | `run.py explore --run $RUNS/playground-gaze-lattice-smoke --max-fix 75` | 77.5 s | 0 |
| C4 | `run.py checks --run $RUNS/playground-gaze-lattice-smoke` | 1.7 s | 0 |
| C5 | `run.py explore --run $RUNS/playground-gaze-lattice --max-fix 600 --spp 64` | 669 s (`wall_seconds` 665.3) | 0 |
| C6 | `run.py evaluate --run $RUNS/playground-gaze-lattice` | 27.4 s | 0 |
| C7 | `run.py checks --run $RUNS/playground-gaze-lattice` | 5.1 s | 0 |
| C8 | `run.py visualize --run $RUNS/playground-gaze-lattice --vis /home/lvelho/rd/f3d-vision/visuals/playground-gaze-lattice` | 7.7 s | 0 |

C5 ran detached (`setsid nohup`) from a script file, so it would not depend on the agent's tool-call lifetime. The
command itself is as listed. For C8, see deviation D1.

### C1 (verbatim)

    [lattice] lattice: 496 gazes on 19 rings of 10 deg (0.8 s); per ring [1, 9, 17, 24, 29, 34, 39, 40, 40, 30, 40, 40, 39, 34, 29, 24, 17, 9, 1]
    [lattice] PASS K1 the lattice covers every 1-deg cell: 64800 / 64800 cells
    [lattice] PASS K2 every gaze has a frame; every pair >= VISIT_TOL_DEG apart: frames True, min pair 6.81 deg
    [lattice] PASS K3 baseline first-step gain: diagonals 0.825, sides 0.58 (+-0.005): diagonal [0.825, 0.825, 0.825, 0.825], side [0.583, 0.583, 0.58, 0.58]
    [lattice] PASS K4 replay: stops with none, 0 UNSEEN cells, <= one fixation per gaze, no duplicate: stop none, 496 fixations (469 local / 26 global, tail 1), UNSEEN cells 0, min pair 6.81 deg, 99 % at #470 (1 s)
    [lattice] PASS K5 a mid-replay state re-decides identically: local -> (-111.72, 50.00)
    [lattice] PASS N1 negative control: one equator gaze removed breaks the cover: 96 cells uncovered
    [lattice] PASS N2 negative control: GAIN_MIN 0.25 fails K4 + tail <= 25: 496 fixations (317 local / 178 global, tail 145), UNSEEN cells 0
    [lattice] SUMMARY checked=7 failed=0 (4 s)

On the workstation, C1 reproduces every number the ClaudeChat sandbox recorded in `85fb962`.

### C2

    [repository-layout] SUMMARY checked=650 failed=0

### C3 (final line)

    [gfe] FROZEN 75 fixations (74 local, 0 global), stop: fixation cap 75; seen 24.66% depth 24.33%; 4,389,884 surfels; wall 76 s

### C4 (verbatim)

    [gfe] check fixed_head_H0: True
    [gfe] check finite_xyz: True
    [gfe] check no_duplicate_fixation: {'pass': True, 'min_pair_deg': 7.970259112430748}
    [gfe] check seen_monotone: True
    [gfe] check map_save_load: True
    [gfe] check breadth1_not_opened_before_freeze: True
    [gfe] check deterministic_policy: {'pass': True, 'states_rechecked': 74, 'mismatches': []}
    [gfe] check fusion_rule_equals_accepted_fsg3: True
    [gfe] CHECKS PASS

### C5 (final line)

    [gfe] FROZEN 496 fixations (460 local, 35 global), stop: no valid unseen fixation; seen 100.00% depth 99.31%; 16,702,245 surfels; wall 665 s

### C6

    [gfe] EVALUATED all-geometry 253,043/255,758 cells 98.94% (98.82% sr); authored 98.98% (98.81% sr); vectorized agrees True

### C7 (verbatim)

    [gfe] check fixed_head_H0: True
    [gfe] check finite_xyz: True
    [gfe] check no_duplicate_fixation: {'pass': True, 'min_pair_deg': 6.809734642322106}
    [gfe] check seen_monotone: True
    [gfe] check map_save_load: True
    [gfe] check breadth1_not_opened_before_freeze: True
    [gfe] check deterministic_policy: {'pass': True, 'states_rechecked': 495, 'mismatches': []}
    [gfe] check fusion_rule_equals_accepted_fsg3: True
    [gfe] CHECKS PASS

### C8

    [gfe-visuals] wrote /home/lvelho/rd/f3d-vision/visuals/playground-gaze-lattice/overview.png (2000, 3275)

## 4. Comparison with the official baseline

Sources: each run's `trajectory.json`, `coverage.npz` and `evaluation.json`. Baseline:
`previews/greedy-foveal-official-baseline/`. Lattice: `previews/playground-gaze-lattice/` (C5–C7). UNSEEN cells
and holes come from `coverage.npz` `state`. Holes are counted with `explorer.unseen_components`: 4-connected,
with longitude wrap and across-pole links.

| quantity | baseline | lattice |
|---|---|---|
| stop reason | `seen >= 99 % of 4 pi` | `no valid unseen fixation` |
| fixations, final | 542 | **496** |
| fixations to 99 % SEEN | 542 | **472** |
| fixations to 100 % SEEN | not reached | 496 |
| local / global saccades (+ 1 initial) | 322 / 219 | **460 / 35** |
| last local saccade | #362 | #488 |
| all-global tail after the last local saccade | 180 | **8** |
| global saccades after #450 | 92 | 21 |
| final SEEN / DEPTH (% of 4π) | 99.00 / 98.28 | **100.00 / 99.31** |
| cells UNSEEN / SEEN-no-depth / DEPTH (of 64,800) | 640 / 411 / 63,749 | **0** / 378 / 64,422 |
| UNSEEN holes | 184 (largest 0.00183 sr, total 0.1250 sr) | **0** |
| Breadth-1 12 mm, all geometry: cells | 251,966 / 255,758 = 98.52 % | 253,043 / 255,758 = **98.94 %** |
| Breadth-1 12 mm, all geometry: solid angle | 98.32 % | **98.82 %** |
| Breadth-1 12 mm, authored (Index > 0): cells / solid angle | 98.52 % / 98.25 % | 98.98 % / 98.81 % |
| Breadth-1 12 mm, instance 0 (non-catalog): solid angle | 98.69 % | 98.92 % |
| covered cells, NN distance median / p90 | 0.727 / 2.240 mm | 0.723 / 2.190 mm |
| final surfels | 16,517,811 | 16,702,245 |
| wall (`wall_seconds`) | 733.1 s | **665.3 s** |
| wall per fixation | 1.353 s | 1.341 s |
| breakdown (sum over fixations): render | 413.5 s | 373.0 s |
| correspondence (incl. EXR load) | 18.2 s (9.3 s) | 16.4 s (8.3 s) |
| geometry | 12.6 s | 11.5 s |
| fusion | 257.8 s | 236.6 s |
| policy | 3.3 s | 2.8 s |
| sum of per-fixation totals / server start | 731.9 s / 0.50 s | 664.2 s / 0.45 s |
| `evaluate` (Breadth-1 coverage) | 26.3 s | 26.5 s |
| `run.py checks` | pass | pass (8 / 8) |

The baseline's all-global tail is **180** fixations, larger than the contract's "≥ 92": the baseline's last local
saccade was #362, not #450. The contract's 92 counts only the globals after #450, and that count is reproduced here.
The gaze proposal is the only code difference between the two runs. The 12-mm gain (+0.50 points of solid angle)
therefore comes from where the eyes looked.

### SEEN versus fixation (checkpoint table)

From each run's `coverage.npz` `seen_history` / `depth_history`: SEEN % / DEPTH % of 4π after fixation n.

| fixation | baseline SEEN / DEPTH | lattice SEEN / DEPTH |
|---|---|---|
| #100 | 28.48 / 28.09 | 31.96 / 31.43 |
| #200 | 56.06 / 55.55 | 60.53 / 60.06 |
| #300 | 79.62 / 78.72 | 82.42 / 81.58 |
| #400 | 94.22 / 93.40 | 94.03 / 93.16 |
| #470 | 97.40 / 96.64 | 98.92 / 98.14 |
| #496 | 98.08 / 97.34 | **100.00 / 99.31** (final) |
| final | **99.00 / 98.28** (#542) | **100.00 / 99.31** (#496) |

The lattice leads through #300. The baseline is slightly ahead at #400 (+0.19 points SEEN). The lattice then
finishes its last 6 % in 96 fixations, while the baseline needs 142 fixations to go from 94.22 % to 99.00 %.

### Visual

`visuals/playground-gaze-lattice/overview.png` (2000 × 3275; sha256 `869121e9…6878`), in the shared checkout's
`visuals/`. Panel A is the trajectory: the lattice tour, with the 35 global targets numbered. Panel B is the final
coverage state, 0.0 % UNSEEN. Panel C is SEEN / DEPTH versus fixation, with global saccades ticked. Panel D gives
the statistics and panel E the Breadth-1 cells. Panel F shows the map from above. Regenerate with C8. The baseline
counterpart is `visuals/greedy-foveal-official-baseline/overview.png`.

## 5. Acceptance gate (contract §6)

Judged on C5–C7 only.

| # | criterion | measured | result |
|---|---|---|---|
| A1 | stops by itself with `no valid unseen fixation`; 0 UNSEEN cells (SEEN = 100 %) | `no valid unseen fixation`; 0 UNSEEN cells; SEEN 100.00 % | **PASS** |
| A2 | fixations ≤ 542 | 496 | **PASS** |
| A3 | global saccades ≤ 60; all-global tail ≤ 25 | 35 global; tail 8 | **PASS** |
| A4 | `run.py checks` passes every check | 8 / 8, `CHECKS PASS` | **PASS** |
| A5 | Breadth-1 12-mm solid angle ≥ 98.32 % | 98.82 % | **PASS** |

## 6. Proposed versus measured

| quantity | PROPOSED (contract §6, Chat-sandbox model) | PROPOSED (check K4, coverage-only replay) | MEASURED (C5–C6) |
|---|---|---|---|
| fixations | 496 | 496 | 496 |
| local / global | 472 / 23 | 469 / 26 | 460 / 35 |
| all-global tail | 1 | 1 | 8 |
| 99 % SEEN at | — | #470 | #472 |
| UNSEEN cells at stop | 0 | 0 | 0 |
| Breadth-1 12-mm solid angle | about 99.3 % | — | 98.82 % |
| wall | 11–13 min (ESTIMATED) | — | 11.1 min (665 s) |

The contract anticipated the extra global jumps: the real windows lack geometry, so the edge band fails there. K4
assumes full edge support everywhere.

## 7. Additional measured observations

- **Fixation 1 equals the baseline's fixation 1.** It is at gaze (0°, 0°), which is lattice gaze 247 (the 30-gaze
  equator ring is half-shifted, so yaw 0 is on it). Its `xyz_h`, `instance_id_oracle`, `err_mm`, calibration,
  correspondence counts, fusion and coverage records match the baseline run exactly. Only the presentation RGB
  differs, the known OPTIX run-to-run RGB difference. The first decision already differs, by design: lattice E
  (+12°, 0°) against baseline NE (+7.2°, +7.14°).
- **Smoke prefix is deterministic.** Fixations 1–75 of C5 match C3 in gaze and kind, with bitwise-equal `xyz_h` and
  an equal `seen_history`.
- **Every lattice gaze was fixated exactly once.** All 496 fixations lie on a lattice gaze (largest offset
  1.5 × 10⁻⁶ deg), and they cover all 496 distinct gazes. So when visited, every lattice gaze still added unseen
  area, and the stop came only when the lattice was exhausted. In this run the fixation count (A2) is the lattice
  size, not a policy outcome.
- **The `> 0` eligibility does matter.** Of the 460 local moves, 117 chose a candidate with unseen gain below the
  baseline's 0.25, which the baseline would have rejected. The smallest chosen gain was 0.045 for a local move and
  0.045 for a global one; the median was 0.599 for local moves and 0.235 for global ones. 20 of the 35 global jumps
  targeted a gaze with gain < 0.25.
- The first global jump is fixation 265, decided after #264, when 232 unvisited lattice gazes still had unseen
  gain. When the last global jump (to #496) was decided, 1 such gaze remained.
- The freeze's open audit recorded 3,492 host opens and 0 Breadth-1 opens. The render server exited 0. Coverage
  cells were monotone.

## 8. Deviations and repairs

- **D1. C8 `--vis` path.** The prompt wrote `--vis visuals/playground-gaze-lattice`. Run from the isolated
  worktree, that relative path would have written into the scratch worktree. The command was given the absolute path
  of the shared checkout's `visuals/playground-gaze-lattice`, where preview / visual Policy 1 keeps visuals. Output
  and code are unaffected.
- **D2. Overview title.** The figure's title still reads "Greedy Foveal Explorer v0", because `visuals.py` is
  unchanged by contract §3. The statistics panel reports the lattice run's own numbers and stop reason.
- **D3. Comparison numbers.** As instructed, no tool file was added. The UNSEEN / hole counts, the tails and the
  checkpoints come from a scratch script outside the repository, which reads only the two runs' `trajectory.json`,
  `coverage.npz` and `evaluation.json`. The hole count can be regenerated with:

      .venv/bin/python -c "import sys, numpy as np; sys.path.insert(0, 'tools/greedy_foveal'); import explorer as X; \
      s = np.load('RUN/coverage.npz')['state']; print(int((s == X.UNSEEN).sum()), len(X.unseen_components(s)[1]))"

- **Repairs: none.** No code, threshold, lattice parameter or check changed. The code that ran is `85fb962`.

## 9. Run evidence

| path (shared checkout) | contents |
|---|---|
| `previews/playground-gaze-lattice/` | C5–C7: 496 fixations, `trajectory.json`, `freeze.json` (sha256 `e1422fb4…6b3c`), `coverage.npz` (`1f95519d…d1f3`), `evaluation.json` (`59e7bfb0…ed6f`), `checks.json`, `final-map.npz`, PLYs, policy states; 2.1 GB |
| `previews/playground-gaze-lattice-smoke/` | C3–C4: 75 fixations; 482 MB |
| `visuals/playground-gaze-lattice/overview.png` | C8 (sha256 `869121e9…6878`) |

## 10. Open items for Luiz and Chat

- Acceptance of Playground-1 and what follows from it (merge to `main`, tag, handoff update) is Luiz's decision.
  This branch makes no acceptance claim.
- Fixation count and lattice size are the same in this run (496), and each gaze still added area when visited.
  Fewer fixations would need a different lattice, or a rule that skips gazes. Neither is in this contract's scope,
  and neither was tried.
- Breadth-1 12-mm solid angle is 98.82 %, against the sandbox's "about 99.3 %". The remaining 1.18 % is not
  attributed in this report.

## 11. Acceptance

**Decision (Luiz, 2026-10-11): ACCEPTED as a playground result.** The official baseline stays the official baseline.

- **The lattice code is not merged into `main`.** It lives at the annotated tag **`playground-1-gaze-lattice`**,
  which points to the commit that adds this section on `playground/gaze-lattice`. `main` keeps the official
  `tools/greedy_foveal/` code, which `check_equivalence.py`, the README and the technical report describe. Copies of
  this report and its contract are on `main` in `docs/playground/`, added by a docs-only acceptance commit.
- **Promoting the lattice** to the official baseline would be a separate Engineering step. It is not authorized.

### ClaudeChat review notes

- **Verified from GitHub.** `847be8a` adds only this report, on top of `85fb962`. The runs recorded `85fb962` with a
  clean tree. The layout checker gives 650 checked, 0 failed with the report in place (Chat-sandbox). The counts are
  consistent: 460 + 35 + 1 = 496; 322 + 219 + 1 = 542; 253,043 / 255,758 = 98.94 %.
- **Correction to the contract.** The baseline's all-global tail is 180 (section 4), not the "≥ 92" of contract
  §1 and §6. The gate's margin is therefore larger than the contract stated.
- **Missed prediction.** The contract predicted about 99.3 % for the 12-mm solid angle; 98.82 % was measured
  (+0.50 points, not about +1.0). A likely reason, PROPOSED and untested: the baseline's UNSEEN holes were partly
  reconstructed already, because a fixation reconstructs its whole raw core while SEEN marks only the cells whose
  centres fall inside the nominal footprint. The remaining 1.18 % is probably depth-edge occlusion slivers, which a
  fixed head cannot fill. It stays unattributed (section 10).
- **D1 came from the prompt.** The relative `--vis` path in the prompt was Chat's error. Claude Code's
  absolute path was the right fix.

### Open, not authorized

- Attributing the remaining 1.18 % of the Breadth-1 solid angle.
- A sparser covering lattice. The fixation count here is the lattice size (496), and 12° square footprints allow
  about 290 in principle.
- The overview title (D2), if the lattice is ever promoted.
