# Playground-2 — sparse covering lattice: contract

**Status: CONTRACT (PROPOSED).** Luiz named this step on 2026-10-11 as the experiment after the slide presentation, and
authorized it on 2026-10-12. ClaudeChat wrote and pushed it; workstation execution is Claude Code's.

| item | value |
|---|---|
| branch | `playground/sparse-lattice`, from `46a2649` (head of `playground/gaze-lattice`, which contains tag `playground-1-gaze-lattice` → `3c64c1f`) |
| previous experiment | Playground-1 gaze lattice: 496 gazes on pitch rings; MEASURED 496 fixations, 0 UNSEEN cells, 35 global saccades, tail 8, Breadth-1 12 mm 98.82 % (`gaze-lattice-report.md`) |
| official baseline | `tools/greedy_foveal/` at tag `greedy-foveal-playground-baseline`; MEASURED 542 fixations, 640 UNSEEN cells, 219 global saccades, 12 mm 98.32 % |
| changed files | `tools/greedy_foveal/explorer.py` (the lattice) and `tools/greedy_foveal/check_lattice.py` (its known answers) |

## 1. Question

In Playground-1 every one of the 496 lattice gazes was fixated, and each one still added unseen area. So the
fixation count is the lattice size. The ring lattice is wasteful for a measurable reason.

Each footprint is a square in its gaze's tangent plane, and its x axis is the eye baseline (head +X) projected into
that plane (`fsg_geometry.camera_rotation_h`). The squares are therefore aligned with circles about the baseline
axis, not with yaw and pitch. Near yaw ±90°, a pitch ring meets the squares as diamonds and needs 40 gazes where the
equator ring needs 30. Per-ring counts, MEASURED by `check_lattice.py` C1 at `85fb962`:
`[1, 9, 17, 24, 29, 34, 39, 40, 40, 30, 40, 40, 39, 34, 29, 24, 17, 9, 1]`.

**Does a lattice of rings about the baseline axis, on which every square sits square-on to its ring, keep zero holes
with far fewer fixations?**

## 2. The single change: the lattice construction

Everything else is Playground-1 unchanged: the 16° local neighbourhood, `EDGE_SUPPORT × UNSEEN_GAIN` with `> 0`
eligibility, the max-gain global move, the `none` stop and the visited test.

**Baseline-ring lattice.** A gaze is written in baseline coordinates (θ, φ). θ is the angle from head +X; φ is the
rotation about X, with φ = 0 forward (head −Z). Its direction is (cos θ, sin θ sin φ, −sin θ cos φ), the epipolar
convention of `CLAUDE.md`.

- **Rings.** 17 rings, θ = 6°, 16.5°, 27°, …, 90°, …, 174°, i.e. θ = 6° + 10.5° · i for i = 0 … 16.
- **Gazes per ring.** Ring i has n_i gazes at φ = j · 360°/n_i, j = 0 … n_i − 1. Every ring starts at φ = 0, so the
  fixed start gaze (0°, 0°) is a lattice gaze, on the θ = 90° ring.
- **Choosing n_i.** n_i is the smallest n ≥ 1 whose nominal footprints (`footprint`) contain the centre of every 1°
  cell with θ_c in the ring's band.
  - The bands are [θ_i − 5.25°, θ_i + 5.25°].
  - The two cap rings (θ = 6° and 174°) extend their bands to the pole (θ_c ≤ 11.25° and θ_c ≥ 168.75°).
- **Envelope constraint: every gaze stays ≥ 6° from the baseline axis.** No v0 or Playground-1 fixation came closer
  than 6°. Chat-sandbox searches show that a 2° cap ring would save 10 more gazes (346). The 6° cap was chosen
  deliberately to keep near-axis stereo out of this experiment. It is a later, separate question.

Chat-sandbox, PROPOSED for the workstation:

- **356 gazes**, covering 64,800 / 64,800 cells;
- no gaze is redundant: each covers a cell that no other gaze covers;
- the minimum gaze pair is 5.99°.

`LATTICE_KIND` selects the construction: `"baseline"` (this step) or `"pitch"` (Playground-1, kept for comparison
and for check K6).

## 3. What deliberately does not change

- `run.py`, `render_server.py`, `visuals.py`, `demo.py`, `check_equivalence.py`.
- Rendering, correspondence, reconstruction, fusion, the coverage grid, evaluation and the Breadth-1 firewall.
- `local_candidates`, `global_target` and `decide`, together with `LATTICE_NEIGHBOUR_DEG` 16°, `LATTICE_VISIT_DEG`
  0.5°, `GAIN_MIN` 0.0, `EDGE_MIN` 0.25 and `SEEN_STOP` 2.0.
- The official baseline and the Playground-1 tag. They stay the comparisons and are not re-run.

## 4. Known answers and fail-capable checks (host-side, no Blender)

`tools/greedy_foveal/check_lattice.py` checks the lattice that `lattice()` returns. It exits 1 on any failure.

| # | check | must |
|---|---|---|
| K1 | the lattice footprints contain every 1° cell centre | 64,800 / 64,800 |
| K2 | every gaze has a valid frame; every pair ≥ `VISIT_TOL_DEG` apart | pass |
| K3 | the baseline's first-step gains, diagonal and side (unchanged known answer) | 0.825, 0.58 |
| K4 | coverage-only replay through `decide`: stops `none`, 0 UNSEEN cells, ≤ one fixation per lattice gaze, no repeated gaze | pass |
| K5 | a mid-replay state re-decided twice equals the live decision | pass |
| K6 | the lattice has 356 gazes, and the Playground-1 pitch lattice (`LATTICE_KIND = "pitch"`) still has 496 | 356, 496 |
| K7 | no gaze is redundant, and every gaze is ≥ 6° from the baseline axis; the start gaze (0°, 0°) is on the lattice | pass |
| N1 | negative control: removing the start gaze breaks the cover | FAIL |
| N2 | negative control: the 2° cap design breaks K7's 6° envelope | FAIL |

`tools/repository/check_repository_layout.py` stays at 0 failures. This contract is required; its report is
allowed.

## 5. Commands and cost classes

These run from an isolated worktree at the head named in the handoff, with the `.venv` and `scenes/classroom`
symlinks. `RUNS=/home/lvelho/rd/f3d-vision/previews`; the run tool is `.venv/bin/python tools/greedy_foveal/run.py`.

| # | command | cost class |
|---|---|---|
| C1 | `.venv/bin/python tools/greedy_foveal/check_lattice.py` | Batch (Chat-sandbox: under a minute) |
| C2 | `.venv/bin/python tools/repository/check_repository_layout.py` | Batch |
| C3 | `run.py explore --run $RUNS/playground-sparse-lattice-smoke --max-fix 75` | Batch (about 1.5 min) |
| C4 | `run.py checks --run $RUNS/playground-sparse-lattice-smoke` | Batch |
| C5 | `run.py explore --run $RUNS/playground-sparse-lattice --max-fix 600 --spp 64` | about 8 min (ESTIMATED: 356 × 1.34 s). Authorized by Luiz as this step's acceptance run. |
| C6 | `run.py evaluate --run $RUNS/playground-sparse-lattice` | Interactive / Batch |
| C7 | `run.py checks --run $RUNS/playground-sparse-lattice` | Batch |
| C8 | `run.py visualize --run $RUNS/playground-sparse-lattice --vis /home/lvelho/rd/f3d-vision/visuals/playground-sparse-lattice` | Interactive / Batch |

Run C1–C2 before C3, and C3–C4 before C5. `explore` records the commit, so commit before C3.

## 6. Acceptance gate

These criteria are declared before any workstation run and judged on C5–C7 only.

| # | criterion | Playground-1 (MEASURED) | official baseline (MEASURED) |
|---|---|---|---|
| A1 | stops by itself with `no valid unseen fixation`; `coverage.npz` holds 0 UNSEEN cells | 0 | 640 |
| A2 | fixations ≤ 356 | 496 | 542 |
| A3 | global saccades ≤ 60; all-global tail ≤ 25 | 35; 8 | 219; 180 |
| A4 | `run.py checks` passes every check | pass | pass |
| A5 | Breadth-1 12-mm solid angle ≥ 98.32 % (the official baseline) | 98.82 % | 98.32 % |

**Reported, not gated.** The change in 12-mm coverage against Playground-1's 98.82 % is recorded but does not decide
acceptance. Fewer, less overlapping views may trade a little 3-D coverage for fixations; whether that trade is worth
it is a decision for Luiz and Chat, not a pass/fail.

PROPOSED (Chat-sandbox replay, full edge support): 356 fixations, 314 local / 41 global, tail 0, 99 % SEEN at #346.
The windows have no geometry, so they will add global jumps in the real run.

## 7. Stop conditions

Stop and report, without changing the lattice, the thresholds or the gate:

- C1 or C2 fails;
- `explore` raises, or reaches the 600 cap;
- any `run.py checks` item fails;
- an acceptance criterion fails. Report it as measured; the decision returns to Luiz and Chat.

## 8. Permitted fixes

Only implementation defects in the baseline-ring construction or in `check_lattice.py` that are needed to realize
§2 and §4 as written.

A fix must not change any of these:

- the ring angles, the cap, the 6° envelope or the φ = 0 phase;
- the neighbourhood, the thresholds or the acceptance gate.

No parameter is tuned after any run has been seen.

## 9. Results to record

Claude Code commits `docs/playground/sparse-lattice-report.md` with:

- the branch, the commit `explore` recorded, the commands run, and the C1, C4 and C7 lines verbatim;
- a three-way comparison with the Playground-1 run and the official baseline:
  - fixations, to 99 % and final;
  - local / global split and the all-global tail;
  - final SEEN / DEPTH;
  - UNSEEN cells and holes;
  - Breadth-1 12-mm cells and solid angle;
  - surfels;
  - wall time and its breakdown;
- the SEEN / DEPTH checkpoints (#100, #200, #300, #346, final) from each run's `coverage.npz`;
- whether every lattice gaze was fixated, and the DEPTH fraction of the cells within 15° of the baseline axis
  (the cap rings' region);
- `visuals/playground-sparse-lattice/overview.png`;
- A1–A5 with pass / fail, the deviations from this contract, and any repairs.
