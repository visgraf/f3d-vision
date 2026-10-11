# Playground-1 — gaze lattice: contract

**Status: EXECUTED and ACCEPTED** (2026-10-11; see [the report](gaze-lattice-report.md), section 11). Authorized by Luiz on 2026-10-11 as the first playground experiment against the
official Greedy Foveal Playground baseline (tag `greedy-foveal-playground-baseline`). Written and pushed by ClaudeChat
under the working agreement of `55ba7ba`; workstation execution is Claude Code's.

| item | value |
|---|---|
| branch | `playground/gaze-lattice`, from `55ba7ba` (the ClaudeChat working agreement, whose parent is `main` `9fdf043`) |
| baseline code | `tools/greedy_foveal/` at tag `greedy-foveal-playground-baseline`; `explorer.py` is unchanged from it at `55ba7ba` |
| baseline run | `previews/greedy-foveal-official-baseline/` (MEASURED: 542 fixations, 99.00 % SEEN, 322 local / 219 global, 98.32 % Breadth-1 solid angle within 12 mm, 733 s) |
| changed file | `tools/greedy_foveal/explorer.py` only (plus the new host-side check `tools/greedy_foveal/check_lattice.py`) |

## 1. Question

The baseline leaves residual UNSEEN holes and ends in a long tail of single-hole global jumps. The official run
stopped at 99.00 % SEEN with 184 holes, each ≤ 0.0018 sr; all 92 fixations after #450 of grow600 were single-hole
global jumps. The proposed cause is that gaze candidates live in a continuous tangent frame that drifts with pitch,
plus a diagonal bias. A diagonal neighbour's unseen gain is 0.83, against 0.58 for a side neighbour (Chat-sandbox
known answer, below). Diagonal staircases leave slivers far below `GAIN_MIN = 0.25` of a footprint, and only global
jumps can reach them, one hole per jump.

**Does restricting every gaze to a fixed covering lattice, and filling any lattice neighbour that still adds unseen
area, remove the holes and the tail without costing more fixations than the baseline?**

## 2. The single change: where gaze candidates come from

The lattice replaces the gaze proposal set, which is shared by three rows of the architecture map
(`docs/architecture/greedy-foveal-playground.md` §16): the local policy, the global policy and the stopping rule.
They change together because the lattice defines all three. Nothing else changes.

1. **Gaze lattice** (deterministic, built once, lazily, from the existing `footprint()`):
   - pitch rings every 10° from −90° to +90° (19 rings), with one gaze `(yaw 0, pitch ±90°)` at each pole;
   - on every other ring at pitch `p`, `n` equally spaced yaws `−180° + (i + ½)·360°/n`, shifted by a further half
     step when `n mod 4 = 2` (this keeps yaw ±90° out, where pitch 0 is degenerate with the stereo baseline);
   - `n` is the smallest value ≥ 4 whose nominal footprints contain the centre of every 1° cell whose centre pitch
     lies in `[p − 5°, p + 5°]`.

   PROPOSED (Chat-sandbox model): 496 gazes, covering every one of the 64,800 cells.
2. **Local move:** candidates are the unvisited lattice gazes within 16° of the current gaze. The score is
   `EDGE_SUPPORT × UNSEEN_GAIN`, as in the baseline. The edge band is the baseline band of the octant (E, SE, S, SW,
   W, NW, N, NE) that holds the candidate's offset in the current tangent frame. A candidate is eligible when
   `EDGE_SUPPORT ≥ EDGE_MIN` (0.25, unchanged) and `UNSEEN_GAIN > 0`; the baseline requires `≥ 0.25`. Highest score
   wins; ties go to the lower lattice index.
3. **Global move:** jump to the unvisited lattice gaze with the largest `UNSEEN_GAIN`; ties go to the lower index.
   This replaces the UNSEEN-component BFS and the "deepest cell" rule.
4. **Stop:** `decide` returns `none` when no unvisited lattice gaze has `UNSEEN_GAIN > 0`. The run then stops with
   `no valid unseen fixation`. Under the lattice, that means every cell is SEEN. `SEEN_STOP = 2.0` is unreachable on
   purpose, so `run.py`'s SEEN branch never fires.

   *Revision before any workstation run.* This contract first said `SEEN_STOP = 1.0`. The Chat-sandbox check K4 then
   showed that `run.py`'s SEEN branch fires first, at exactly 100 %, and records its fixed text "seen >= 99 % of
   4 pi". The coverage outcome is the same; only the recorded stop reason was wrong.

A lattice gaze counts as visited when a fixation direction lies within 0.5° of it. So `decide(state, core_valid, yaw,
pitch, visited)` keeps its signature and its inputs, and `run.py` and its saved decision states are untouched.

## 3. What deliberately does not change

- `run.py`, `render_server.py`, `visuals.py`, `demo.py`, `check_equivalence.py`;
- rendering (Classroom, 64 spp, fixed head H0), the PERFECT / ORACLE correspondence and the spherical reconstruction;
- the global map, the FSG3 12-mm fusion rule and the coverage grid (1°, `footprint`, `update_coverage`);
- `edge_support`, `unseen_gain`, `EDGE_BAND_PX`, `EDGE_MIN`, `VISIT_TOL_DEG` (still used by `run.py checks`);
- post-hoc evaluation and the Breadth-1 firewall: Breadth-1 is opened only after the freeze;
- the official baseline itself. It stays the comparison and is not re-run; `check_equivalence.py` is expected to
  report this branch as different, by design.

## 4. Known answers and fail-capable checks (host-side, no Blender)

`tools/greedy_foveal/check_lattice.py` exits 1 on any failure. It checks:

- **K1 cover:** the lattice footprints contain every 1° cell centre (64,800 / 64,800).
- **K2 well-formed:** every gaze has a valid tangent frame (no degenerate gaze), and every pair is ≥ `VISIT_TOL_DEG`
  apart, so `run.py checks`' no-duplicate test can pass.
- **K3 baseline bias:** the baseline's first-step unseen gain is 0.825 for every diagonal neighbour and 0.58 for every
  side neighbour. This is the known answer behind §1.
- **K4 replay:** a coverage-only replay through `explorer.decide`, with full edge support and no rendering, ends with
  `none`, 0 UNSEEN cells, at most one fixation per lattice gaze, and no repeated gaze.
- **K5 determinism:** a mid-replay state re-decided twice gives the same decision.
- **Negative controls, which must fail:**
  - N1: K1 with one ring gaze removed;
  - N2: K4 with the eligibility threshold set back to the baseline `GAIN_MIN = 0.25`, while still demanding a tail of
    at most 25 global fixations.

`tools/repository/check_repository_layout.py` must stay at 0 failures, with this contract required and the report and
check tool allowed.

## 5. Commands and cost classes

`RUNS=/home/lvelho/rd/f3d-vision/previews`; all from the repository root, in an isolated worktree with the `.venv`
and `scenes/classroom` symlinks (`README.md` of `tools/greedy_foveal/`).

| # | command | cost class |
|---|---|---|
| C1 | `.venv/bin/python tools/greedy_foveal/check_lattice.py` | Batch (Chat-sandbox: under a minute) |
| C2 | `.venv/bin/python tools/repository/check_repository_layout.py` | Batch |
| C3 | `run.py explore --run $RUNS/playground-gaze-lattice-smoke --max-fix 75` | Batch (about 1.5 min) |
| C4 | `run.py checks --run $RUNS/playground-gaze-lattice-smoke` | Batch |
| C5 | `run.py explore --run $RUNS/playground-gaze-lattice --max-fix 600 --spp 64` | about 11–13 min (ESTIMATED from the baseline's 1.35 s per fixation). Above Batch, well below Overnight. Authorized by Luiz as this step's acceptance run, as C10 was for Engineering-1. |
| C6 | `run.py evaluate --run $RUNS/playground-gaze-lattice` | Interactive / Batch |
| C7 | `run.py checks --run $RUNS/playground-gaze-lattice` | Batch |
| C8 | `run.py visualize --run $RUNS/playground-gaze-lattice --vis visuals/playground-gaze-lattice` | Interactive / Batch |

The `run.py` commands are `.venv/bin/python tools/greedy_foveal/run.py …`. Run C1–C2 before C3, and C3–C4 before C5.
Commit before C3: `explore` records the commit and whether the tree is clean.

## 6. Acceptance gate

These criteria are declared before any workstation run. They are judged on C5–C7 only:

| # | criterion | baseline (MEASURED) |
|---|---|---|
| A1 | the run stops by itself with `no valid unseen fixation`, and `coverage.npz` holds **0 UNSEEN cells** (SEEN = 100 %) | 99.00 %, 184 holes |
| A2 | fixations **≤ 542** | 542 |
| A3 | global saccades **≤ 60**, and the all-global tail after the last local saccade is **≤ 25** fixations | 219 global; tail ≥ 92 |
| A4 | `run.py checks` passes every check | pass |
| A5 | Breadth-1 within 12 mm, solid angle **≥ 98.32 %** | 98.32 % |

PROPOSED (Chat-sandbox model, full edge support): 496 fixations to 100 % SEEN, 472 local / 23 global, a one-fixation
tail; 12-mm coverage about 99.3 %. The windows have no geometry, so they will add some global jumps in the real run.
These numbers are predictions, not criteria.

## 7. Stop conditions

Stop and report, without changing thresholds or the lattice:

- C1 or C2 fails;
- `explore` raises (for example a degenerate gaze), or reaches the 600 cap;
- any `run.py checks` item fails;
- an acceptance criterion fails. Report it as measured; the decision returns to Luiz and Chat.

## 8. Permitted fixes

Only implementation defects in the lattice construction, the visited test or `decide` that are needed to realize §2
as written. A fix must not change the lattice rule, the 16° neighbourhood, `EDGE_MIN`, the `> 0` eligibility or the
acceptance gate. No parameter is tuned after any smoke or full run has been seen. A needed change of that kind is a
new decision for Luiz and Chat.

## 9. Results to record

Claude Code commits `docs/playground/gaze-lattice-report.md` with:

- the branch, the commit `explore` recorded and the commands actually run;
- C1 and C4 / C7 summary lines verbatim;
- a comparison with the official baseline run:
  - fixations, to 99 % and final;
  - local / global split and the all-global tail;
  - final SEEN / DEPTH;
  - UNSEEN cells and holes;
  - Breadth-1 12-mm cells and solid angle;
  - surfels;
  - wall time and its breakdown;
- the SEEN-versus-fixation curve of both runs from `coverage.npz`, and the overview visual
  `visuals/playground-gaze-lattice/overview.png`;
- A1–A5 with pass / fail, the deviations from this contract, and any repairs.
