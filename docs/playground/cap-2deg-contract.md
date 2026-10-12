# Playground-3 — the 2° cap lattice: contract

**Status: CONTRACT (PROPOSED).** Authorized by Luiz on 2026-10-12 ("promotion first, then the 2° cap"). ClaudeChat
wrote and pushed it; workstation execution is Claude Code's.

| item | value |
|---|---|
| branch | `playground/cap-2deg`, from `main` `9bf936d` (the Engineering-2 acceptance: tag `greedy-foveal-playground-baseline-2`) |
| official baseline | the sparse covering lattice. MEASURED (`previews/greedy-foveal-official-baseline-2/`, Engineering-2 report): 356 fixations, 0 UNSEEN cells, 315 local / 40 global, tail 0, 98.82 % of the Breadth-1 solid angle within 12 mm, 413 s. Near-axis DEPTH (cells within 15° of the baseline axis): 93.31 % of solid angle (Playground-2 report §5; the official run is bitwise equal). |
| changed files | `tools/greedy_foveal/explorer.py` (two lattice constants) and `tools/greedy_foveal/check_lattice.py` (its known answers) |

## 1. Question

The official lattice keeps every gaze at least 6° from the eye baseline axis. That envelope was chosen to keep
near-axis stereo out of Playground-2, and its stated reason was withdrawn: v0 fixated 0.71° from the axis without
harm (Playground-2 report, F1).

**Does a cap ring 2° from the axis keep zero holes and the reconstruction quality with 10 fewer fixations (346
against 356), now that near-axis viewing is in the experiment on purpose?**

## 2. The single change: the cap and spacing of the baseline rings

`LATTICE_CAP_DEG` changes from 6.0 to 2.0, and `LATTICE_AXIS_STEP_DEG` from 10.5 to 11.0. The rings move to θ = 2°,
13°, 24°, …, 90°, …, 178° (8 · 11° = 88°, so a ring still lands on θ = 90°). Everything else is unchanged: the
construction (`build_baseline_lattice`, φ = 0 phase, the fewest gazes per band), the policy, the thresholds and
`run.py`.

Chat-sandbox, PROPOSED for the workstation:

- **346 gazes**, with per-ring counts 4, 9, 15, 20, 24, 27, 29, 30, 30, 30, 29, 27, 24, 20, 15, 9, 4;
- they cover 64,800 / 64,800 cells, and no gaze is redundant;
- the minimum gaze pair is 2.83° (the four gazes of each cap ring);
- the start gaze (0°, 0°) is on the lattice.

**Why 2° is the floor.** A 1° cap (step 89/8°) gives 342 gazes, but two are redundant and its cap-ring pair is
1.73°, below `run.py checks`' 2° no-duplicate rule. N2 below keeps that as a negative control.

## 3. What deliberately does not change

- `run.py`, `render_server.py`, `visuals.py`, `demo.py` and `check_equivalence.py`;
- rendering, correspondence, reconstruction, fusion, coverage, evaluation and the Breadth-1 firewall;
- the policy and its constants (`LATTICE_NEIGHBOUR_DEG` 16°, `LATTICE_VISIT_DEG` 0.5°, `GAIN_MIN` 0.0, `EDGE_MIN`
  0.25, `SEEN_STOP` 2.0);
- the official baseline. It stays the comparison and is not re-run.

`check_equivalence.py source` is expected to FAIL on this branch, since `explorer.py` differs from
`playground-2-sparse-lattice` by design. It is not part of this step.

## 4. Known answers and fail-capable checks (host-side, no Blender)

`tools/greedy_foveal/check_lattice.py` checks the lattice that `lattice()` returns, and exits 1 on any failure.

| # | check | must |
|---|---|---|
| K1 | the lattice footprints contain every 1° cell centre | 64,800 / 64,800 |
| K2 | every gaze has a valid frame; every pair ≥ `VISIT_TOL_DEG` (2°) apart | pass (2.83°) |
| K3 | v0's first-step gains, diagonal and side (unchanged known answer) | 0.825, 0.58 |
| K4 | coverage-only replay through `decide`: stops `none`, 0 UNSEEN cells, ≤ one fixation per lattice gaze, no repeated gaze | pass |
| K5 | a mid-replay state re-decided twice equals the live decision | pass |
| K6 | the lattice has 346 gazes; the official 6° lattice still has 356; the Playground-1 pitch lattice still has 496 | 346, 356, 496 |
| K7 | no gaze is redundant; every gaze is ≥ 2° from the baseline axis; the start gaze is on the lattice | pass |
| N1 | negative control: removing the start gaze breaks the cover | FAIL |
| N2 | negative control: the 1° cap design breaks K2's 2° minimum pair | FAIL |

`tools/repository/check_repository_layout.py` stays at 0 failures. This contract is required; its report is
allowed.

## 5. Commands and cost classes

These run from an isolated worktree at the head named in the handoff, with the `.venv` and `scenes/classroom`
symlinks. `RUNS=/home/lvelho/rd/f3d-vision/previews`; the run tool is `.venv/bin/python tools/greedy_foveal/run.py`.

| # | command | cost class |
|---|---|---|
| C1 | `.venv/bin/python tools/greedy_foveal/check_lattice.py` | Batch |
| C2 | `.venv/bin/python tools/repository/check_repository_layout.py` | Batch |
| C3 | `run.py explore --run $RUNS/playground-cap-2deg-smoke --max-fix 75` | Batch (about 1.5 min) |
| C4 | `run.py checks --run $RUNS/playground-cap-2deg-smoke` | Batch |
| C5 | `run.py explore --run $RUNS/playground-cap-2deg --max-fix 600 --spp 64` | about 7 min (ESTIMATED: 346 × 1.17 s); authorized by Luiz as this step's acceptance run |
| C6 | `run.py evaluate --run $RUNS/playground-cap-2deg` | Interactive / Batch |
| C7 | `run.py checks --run $RUNS/playground-cap-2deg` | Batch |
| C8 | `run.py visualize --run $RUNS/playground-cap-2deg --vis /home/lvelho/rd/f3d-vision/visuals/playground-cap-2deg --title "Playground-3 2° cap lattice — FIXATE → RECONSTRUCT → SACCADE (Classroom, fixed head H0)"` | Interactive / Batch |

Run C1–C2 before C3, and C3–C4 before C5. Commit before C3.

## 6. Acceptance gate

These criteria are declared before any workstation run and judged on C5–C7 only. The comparison is the official
baseline (`previews/greedy-foveal-official-baseline-2/`).

| # | criterion | official baseline (MEASURED) |
|---|---|---|
| A1 | stops by itself with `no valid unseen fixation`; `coverage.npz` holds 0 UNSEEN cells | 0 |
| A2 | fixations ≤ 346 | 356 |
| A3 | global saccades ≤ 60; all-global tail ≤ 25 | 40; 0 |
| A4 | `run.py checks` passes every check (including no duplicate fixation ≥ 2°) | pass |
| A5 | Breadth-1 12-mm solid angle ≥ 98.80 % | 98.82 % |
| A6 | DEPTH fraction of the solid angle within 15° of the baseline axis (θ_c ≤ 15° or ≥ 165°) ≥ 92.81 % | 93.31 % |

**Why A5 and A6.** The change saves only 10 fixations (2.8 %), so it is worth keeping only if the reconstruction does
not get worse.

- A5 allows 0.02 points of 12-mm solid angle (about one cell in 5,000) for a different set of views.
- A6 allows 0.5 points of near-axis DEPTH, the region where the change acts. A larger loss there would mean
  near-axis stereo costs depth.

PROPOSED (Chat-sandbox replay, full edge support): 346 fixations, 311 local / 34 global, tail 0, 99 % SEEN at #336.

## 7. Stop conditions

Stop and report, without changing the lattice, the thresholds or the gate:

- C1 or C2 fails;
- `explore` raises (for example at a near-axis gaze), or reaches the 600 cap;
- any `run.py checks` item fails;
- an acceptance criterion fails. Report it as measured; the decision returns to Luiz and Chat.

## 8. Permitted fixes

Only implementation defects in `check_lattice.py` needed to realize §4 as written. No change to `explorer.py`
beyond §2, to the thresholds or to the gate. No parameter is tuned after any run has been seen.

## 9. Results to record

Claude Code commits `docs/playground/cap-2deg-report.md` with:

- the branch, the commit `explore` recorded, the commands run, and the C1, C4 and C7 lines verbatim;
- a comparison with the official baseline run:
  - fixations, to 99 % and final;
  - local / global split and the all-global tail;
  - SEEN / DEPTH;
  - UNSEEN cells and holes;
  - Breadth-1 12-mm cells and solid angle;
  - surfels;
  - wall time and its breakdown;
- the near-axis analysis:
  - DEPTH fraction within 15° of the axis (cells and solid angle);
  - the same within 5°;
  - the points per fixation and the diagnostic error (median / p95) at the eight cap-ring gazes (θ = 2° and 178°),
    against the run's median fixation;
- whether every lattice gaze was fixated;
- `visuals/playground-cap-2deg/overview.png`;
- A1–A6 with pass / fail, the deviations from this contract, and any repairs.
