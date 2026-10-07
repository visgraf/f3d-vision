# Engineering-1: Official Greedy Foveal Playground Baseline — contract

**Status: CONTRACT.** This file is committed before any implementation or execution.

| item | value |
|---|---|
| stage | ENGINEERING / PRESENTATION (`CLAUDE.md`, `docs/chat-handoff.md`) |
| step | Engineering-1: official Greedy Foveal Playground baseline + architecture documentation |
| branch | `engineering/greedy-playground-baseline`, created from `origin/main` |
| base (`origin/main`) | `3f92ac314bbb1f0c0bfac25c9ca6bd55bb129b0f` (Greedy Foveal Explorer v0 closure) |
| frozen implementation | tag `greedy-foveal-explorer-v0-impl` -> `a437df048b555d5b59f6855b6572eea2665ab0da` |
| frozen demo | tag `greedy-foveal-explorer-v0-demo` -> `8066a246bf251fb1e2d66b7061899c32df236bf1` |
| frozen successful run | `previews/greedy-foveal-explorer-v0-grow600/` (`freeze.json` sha256 `a4283ab7…`) |
| closure record | `docs/prototype/greedy-foveal-explorer-v0-closure.md` |

## 1. Purpose

Turn the accepted Greedy Foveal Explorer v0 proof of concept into an **official, reusable code baseline** on clean
`main` ancestry. The baseline is a small active-foveal playground for later work, in this repository or another one.

This is **not** a new scientific experiment, **not** a policy redesign and **not** an optimization pass. The conceptual
baseline stays:

    FIXATE -> RECONSTRUCT EVERYTHING LOCALLY -> UPDATE GLOBAL H0 MAP + CYCLOPEAN COVERAGE
           -> LOCAL OR GLOBAL SACCADE -> REPEAT

## 2. Source of truth

- **The frozen Greedy v0 tags are the source of truth for behavior.** Core behavior comes from
  `greedy-foveal-explorer-v0-impl` (`explorer.py`, `run.py`, `render_server.py`). Presentation comes from
  `greedy-foveal-explorer-v0-demo` (`visuals.py`, `demo.py`).
- **The frozen grow600 run is the behavioral known answer.** It was made at `4d823ad`, where `explorer.py`, `run.py` and
  `render_server.py` are byte-identical to `a437df0`. The two `visuals.py` functions that the run path writes with
  (`display_rgb`, `oracle_colors`) are identical at `a437df0`, `4d823ad` and `8066a24` (MEASURED before this contract,
  AST comparison).
- Behavior must be reproduced **before** any optimization.

## 3. What changes

1. The five Greedy files are promoted onto this branch under `tools/greedy_foveal/` by **ordinary blob extraction**
   from the tags (`git show <tag>:<path>`). No cherry-pick and no merge, so the branch descends only from `main`. The
   prototype branch and NS1e are not merged.
2. **Docstring-only edits.** Module, class and function docstrings may change from "PROTOTYPE" to "official baseline" /
   "active-foveal playground" wording, and obsolete prototype-report references may be removed. Comments may change.
   **No executable statement changes.** This is machine-checked (section 8, A1): each promoted file must be
   AST-equal to its tag blob once docstrings are removed. Consequence, declared here: `run.py`, `render_server.py` and
   `demo.py` print their module docstring as `--help` text, so `--help` changes.
3. New files:
   - `tools/greedy_foveal/README.md`: a short quick start;
   - `tools/greedy_foveal/check_equivalence.py`: the source / run equivalence checker (section 7);
   - `docs/architecture/greedy-foveal-playground.md`: the main architecture reference;
   - `docs/engineering/greedy-foveal-playground-baseline-report.md`: the officialization report.
4. `tools/repository/check_repository_layout.py` declares the new `docs/engineering/` stage directory, the new
   `tools/greedy_foveal/` directory and the files above. This follows the convention of every earlier step: declaration
   only, no check weakened.

## 4. What deliberately does not change

- No policy redesign: the 8-neighbour local rule, EDGE_SUPPORT × UNSEEN_GAIN, the global rule, every threshold and the
  stop rule stay as frozen.
- No natural stereo, no new segmentation, no moving head, no controller-state machinery.
- No optimization: map storage, spatial fusion, the coverage resolution and the render settings stay as they are.
- No class hierarchy, no framework abstraction, no reorganization of the implementation.
- Accepted shared modules (AB1b oracle and geometry, `fsg_geometry`, `fsg3_surface_map`, `exr_lite`, the AB1a / NS1a
  acquisition helpers, Breadth-1 evaluation, Visual Language 1) are reused read-only. They are **not** copied into
  `tools/greedy_foveal/`; the architecture document records the dependency map instead.
- **Executable strings stay as they are**, including the ones that still say "prototype": the trajectory label
  `"PROTOTYPE (not a scientific milestone)"` (`run.py`), the overview subtitle (`visuals.py`) and the demo poster
  footer (`demo.py`). Changing them changes output bytes; a later presentation-only step may do so.
- `demo.py` keeps its hard-coded paths. It stays the replay of the frozen grow600 run.
- **No `tools/greedy_foveal/__init__.py`.** The repository layout checker forbids `__init__.py` under `tools/`, and
  the files use the repository's script-style `sys.path` imports.
- The frozen tags, the frozen grow600 run, the demo package, `CLAUDE.md` and `docs/chat-handoff.md` are not modified.

## 5. Deliverables

| file | role |
|---|---|
| `docs/engineering/greedy-foveal-playground-baseline-contract.md` | this contract |
| `tools/greedy_foveal/{explorer,run,render_server,visuals,demo}.py` | the official code (from the tags) |
| `tools/greedy_foveal/README.md` | the quick start |
| `tools/greedy_foveal/check_equivalence.py` | the equivalence checker |
| `docs/architecture/greedy-foveal-playground.md` | the architecture reference, including the dependency map and the extension points |
| `docs/engineering/greedy-foveal-playground-baseline-report.md` | the report, status ENGINEERING REVIEW PENDING |

Run evidence (gitignored, Policy 1) goes to `previews/greedy-foveal-official-baseline-smoke/` and
`previews/greedy-foveal-official-baseline/`. A presentation-only overview figure of the official run may be written to
`visuals/greedy-foveal-official-baseline/overview.png` with the unchanged `run.py visualize`.

## 6. Commands and cost classes

Run from the branch worktree, with a clean tracked tree for the runs. `RUNS=/home/lvelho/rd/f3d-vision/previews`.

| # | command | cost class |
|---|---|---|
| C1 | `git diff --check` | Interactive |
| C2 | `.venv/bin/python tools/repository/check_repository_layout.py` | Interactive |
| C3 | `.venv/bin/python -m py_compile tools/greedy_foveal/*.py` and host import of `explorer`, `run`, `visuals`, `demo`, `check_equivalence` | Interactive |
| C4 | `.venv/bin/python tools/greedy_foveal/check_equivalence.py source` | Interactive |
| C5 | `.venv/bin/python tools/greedy_foveal/check_equivalence.py selftest` | Interactive |
| C6 | `run.py explore --run $RUNS/greedy-foveal-official-baseline-smoke --max-fix 75` (smoke) | Batch (ESTIMATED about 1.5–2 min: fixations 1–75 of grow600 took 84 s) |
| C7 | `run.py checks --run $RUNS/greedy-foveal-official-baseline-smoke` | Interactive / Batch |
| C8 | `check_equivalence.py run --run …-smoke --baseline $RUNS/greedy-foveal-explorer-v0-grow600 --prefix` | Batch |
| C9 | the same without `--prefix` (negative control: **must FAIL**) | Batch |
| C10 | `run.py explore --run $RUNS/greedy-foveal-official-baseline --max-fix 600 --spp 64` (full) | about 12–13 min (grow600 MEASURED 729 s). Above Batch, well below Overnight; explicitly authorized by the Engineering-1 step prompt as the acceptance gate. |
| C11 | `run.py evaluate --run $RUNS/greedy-foveal-official-baseline` | Interactive / Batch (grow600: 26 s) |
| C12 | `run.py checks --run $RUNS/greedy-foveal-official-baseline` | Batch |
| C13 | `check_equivalence.py run --run $RUNS/greedy-foveal-official-baseline --baseline $RUNS/greedy-foveal-explorer-v0-grow600 --known-answer` | Batch |
| C14 (optional) | `run.py visualize --run $RUNS/greedy-foveal-official-baseline --vis visuals/greedy-foveal-official-baseline` | Interactive / Batch |

No other experiment is rerun. No Controller-01/02 check is run beyond the repository layout checker.

## 7. Equivalence checker

`tools/greedy_foveal/check_equivalence.py` has three modes.

**`source`.** Each promoted file is compared with its tag blob, with module, class and function docstrings removed
from both ASTs. Comments are not in the AST. Any executable difference fails.

**`run --run R --baseline B [--prefix] [--known-answer]`.** It compares the **scientific payload**, not file bytes.
NumPy `.npz` archives carry zip timestamps, and the JSON records carry branch, commit and time metadata.

| compared | rule |
|---|---|
| fixation count, stop reason, local / global counts, final SEEN / DEPTH, final surfels, parameters, render-server settings / seeds / passes | exactly equal |
| per fixation, in order: gaze (yaw, pitch), kind (initial / local / global) and how it was chosen, the full decision record `next` and every local candidate, correspondence counts, fusion counts and match distances, coverage counts, SEEN / DEPTH, the diagnostic error vs Position | exactly equal (JSON values) |
| per fixation `calibration.json` | byte-identical |
| per fixation `points.npz`: `xyz_h`, `instance_id_oracle`, `err_mm` | bitwise equal (dtype, shape, values) |
| per decision `policy/state-NNNN.npz`: `state`, `core_valid`, `gaze`, `visited` | bitwise equal |
| `coverage.npz`: `state`, `seen_history`, `depth_history`, `row_weights` | bitwise equal |
| `final-map.npz`: `xyz_h`, `instance_id_oracle`, `support_count`, `first_fixation`, `patch_ids`, `radius_cell_m` | bitwise equal |
| `final-map-oracle-segmentation.ply` | byte-identical (no RGB enters it) |
| `evaluation.json` (coverage blocks, NN distances, reference, cross-check) and `evaluation.npz` | exactly / bitwise equal |
| `checks.json` | all pass in both runs, equal check values |
| RGB: `points.npz` `rgb`, `final-map.npz` `rgb`, `final-map.ply` colours | **reported, not a failure.** Cycles OPTIX RGB is not bitwise reproducible run to run; RGB never enters gaze, fusion association, coverage or stopping. Shapes must match. |
| metadata: `code`, wall and stage timings, `render_seconds_lr`, `freeze_sha256`, `frozen_utc`, open-audit counts | not compared (reported where useful); `breadth1_opens` must be empty in both runs |

With `--prefix`, a shorter run R (for example the smoke run, stopped by its cap) is compared with the first N fixations
of B. Gazes and all per-fixation products are compared for 1..N. Decisions are compared for 1..N−1. R's final coverage
state is compared with B's saved decision state at N. Run-level final products (final map, evaluation) are skipped.

`--known-answer` also asserts the literal frozen values of section 8, independently of B's files.

**`selftest`** (Interactive) proves that the comparators can fail, using in-memory controls only: a changed
executable constant must fail `source`; a docstring-only change must pass; a single-ULP change in an `xyz_h` array, a
flipped decision kind and a changed SEEN history value must each fail the run comparators.

## 8. Acceptance gate

All of the following must hold:

- **A1 (source):** `check_equivalence.py source`: 5 / 5 files executable-equal to their tag blobs.
- **A2 (layout):** the repository layout checker reports `failed=0`.
- **A3 (smoke):** the smoke run passes `run.py checks`. Prefix equivalence with grow600 PASSES. The full-mode
  comparison (negative control) FAILS.
- **A4 (known answer, full reproduction):**

      stop at fixation 542
      stop reason "seen >= 99 % of 4 pi"
      99.00 % SEEN, 98.28 % DEPTH (2-decimal percentages)
      322 local saccades, 219 global saccades
      post-freeze Breadth-1 12 mm: 98.52 % of first-hit cells (251,966 / 255,758)
                                   98.32 % of first-hit solid angle

- **A5 (strong equivalence):** `check_equivalence.py run … --known-answer` against
  `previews/greedy-foveal-explorer-v0-grow600/` PASSES.
- **A6 (run checks):** `run.py checks` on the official run: all checks pass.
- **A7:** `git diff --check` is clean, and the architecture document, README and report are committed.

## 9. Stop conditions

- **Any divergence in the control path** (gaze, decision, coverage, per-fixation XYZ, oracle ids, fusion, the final
  map or evaluation): STOP. Diagnose and report. **No tuning, no policy change and no edit of the promoted executable
  code to make the numbers match.** The decision returns to Luiz and Chat.
- The render server cannot start, or Blender / GPU / scene assets differ from the frozen run (Blender version, device,
  settings): diagnose the environment. If the difference is real, stop and report.
- The layout checker fails for a reason other than a missing declaration of this step's files: stop and report.
- A conflict with `CLAUDE.md`: stop and report.

## 10. Permitted fixes

Delegated:

- documentation, the README, the report and docstring wording;
- defects in the new `check_equivalence.py`. The rules of section 7 must not be weakened. A tolerance may not replace
  a bitwise rule, except for the RGB rule already declared;
- layout-checker declarations of this step's own files and directories;
- worktree environment set-up: `.venv` and `scenes/classroom` symlinks to the shared checkout.

Not delegated:

- any executable change to the five promoted files;
- thresholds, parameters and render settings;
- the frozen run, the tags and the demo package.

## 11. Results to record

The report records:

- the source main SHA, the tags, the branch, the contract / implementation / documentation / report commits;
- the exact files promoted, with their tag blob ids and new blob ids;
- the docstring-only diff summary and the A1 result;
- the dependency map (in the architecture document) and the layout result;
- the smoke and full commands as run, their console summary lines verbatim, and the runtimes;
- the equivalence results: full, prefix, negative control and self-test;
- the final metrics;
- the RGB differences as reported;
- any deviation, with the reason;
- the proposed outlines of the later technical report and slide presentation (outlines only).

**Report status:** `ENGINEERING REVIEW PENDING`. No accepted marker is added, and nothing is merged to `main`. The next
decision belongs to Luiz and Chat.
