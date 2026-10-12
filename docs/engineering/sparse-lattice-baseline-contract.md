# Engineering-2: promote the sparse covering lattice to the official baseline — contract

**Status: CONTRACT (PROPOSED).** Approved by Luiz on 2026-10-12 ("promotion first, then the 2° cap"). ClaudeChat
wrote this contract, the promotion and the documentation; workstation execution is Claude Code's.

| item | value |
|---|---|
| branch | `engineering/sparse-lattice-baseline`, from `origin/main` `41c7193` (the Playground-2 acceptance) |
| current official baseline | `tools/greedy_foveal/` on `main`, tag `greedy-foveal-playground-baseline` (Greedy Foveal Explorer v0 behavior; Engineering-1) |
| promoted behavior | tag **`playground-2-sparse-lattice`** → `1f50bd6a3f3cf77ccf260375b2cf2fee60c4738f` |
| behavioral known answer | `previews/playground-sparse-lattice/` (code `70d992e`; `freeze.json` sha256 `3f8bf4bd…4a7d`), accepted in `docs/playground/sparse-lattice-report.md` |

## 1. Purpose

Make the accepted Playground-2 explorer the **official baseline** on `main`. Its loop is the same; only the gaze
policy changes, to the sparse covering lattice. MEASURED for the Playground-2 run against the current official
baseline:

- 356 fixations against 542;
- 0 UNSEEN cells against 640;
- 40 global saccades against 219, with no all-global tail;
- 98.82 % of the Breadth-1 solid angle within 12 mm against 98.32 %;
- 416 s against 733 s.

This step is **not** a new experiment and **not** a policy change: the promoted behavior is exactly the accepted
Playground-2 behavior. The Greedy v0 baseline stays reproducible from its tags (`greedy-foveal-playground-baseline`,
`greedy-foveal-explorer-v0-impl`).

## 2. What changes

1. **Promotion by blob extraction.** `explorer.py`, `check_lattice.py`, `demo.py` and `visuals.py` come from
   `playground-2-sparse-lattice` with `git show <tag>:<path>`. There is no merge and no cherry-pick, so the branch
   descends only from `main`. `run.py` and `render_server.py` are already identical to the tag's.
2. **Docstring-only edits** to promoted files (for example `explorer.py`'s header, which still says "frozen to tag
   greedy-foveal-explorer-v0-impl"). **No executable statement changes.** This is machine-checked (A1).
3. **`check_equivalence.py`, retargeted:**
   - `source` checks all six files against `playground-2-sparse-lattice` (`check_lattice.py` is added);
   - `--known-answer` asserts the Playground-2 numbers (A4);
   - `selftest` keeps perturbing the v0 `explorer.py` at `a437df0`, since it tests the comparators, not the target;
   - every comparison rule of Engineering-1 §7 is kept unchanged: bitwise control path, RGB reported only.
4. **Documentation.**
   - The root `README.md` "Current baseline" and "What the playground does" sections; the README title and section
     headings stay, as the layout checker requires.
   - `tools/greedy_foveal/README.md`: the expected numbers and commands.
   - `docs/architecture/greedy-foveal-playground.md` §10 (policy), §11 (stop rule), §16 (extension points) and §17
     (reproducibility baseline).
   - The report `docs/engineering/sparse-lattice-baseline-report.md`.
5. **`check_repository_layout.py`** declares this contract (required) and its report (allowed).

## 3. What deliberately does not change

- **Behavior.** The lattice, the policy, every threshold, the stop rule, rendering, correspondence, reconstruction,
  fusion, coverage, evaluation and the Breadth-1 firewall.
- **Executable strings.** Strings that change output bytes stay as they are, for example `run.py`'s trajectory label
  and `visuals.py`'s default overview title. A later presentation-only step may change them.
- **`demo.py`'s profiles** (`v0`, the default, and `lattice`, the Playground-1 run). No demo of the new official run
  is made in this step.
- **The historical record.** The technical report and the slide presentation are accepted documents of the v0
  baseline and are not edited. The frozen tags, the frozen runs and the demo packages are not modified.

## 4. Commands and cost classes

These run from an isolated worktree at the branch head named in the handoff, with a clean tracked tree for the
runs. `RUNS=/home/lvelho/rd/f3d-vision/previews`. `check_equivalence.py` is
`.venv/bin/python tools/greedy_foveal/check_equivalence.py`; the run tool is `.venv/bin/python
tools/greedy_foveal/run.py`.

| # | command | cost class |
|---|---|---|
| C1 | `git diff --check`; `.venv/bin/python tools/repository/check_repository_layout.py` | Interactive |
| C2 | `.venv/bin/python -m py_compile tools/greedy_foveal/*.py` | Interactive |
| C3 | `check_equivalence.py source` | Interactive |
| C4 | `check_equivalence.py selftest` | Interactive |
| C5 | `.venv/bin/python tools/greedy_foveal/check_lattice.py` | Batch |
| C6 | `run.py explore --run $RUNS/greedy-foveal-official-baseline-2-smoke --max-fix 75` | Batch (about 1.5 min) |
| C7 | `run.py checks --run $RUNS/greedy-foveal-official-baseline-2-smoke` | Batch |
| C8 | `check_equivalence.py run --run $RUNS/greedy-foveal-official-baseline-2-smoke --baseline $RUNS/playground-sparse-lattice --prefix` | Batch |
| C9 | the same without `--prefix` (negative control: **must FAIL**) | Batch |
| C10 | `run.py explore --run $RUNS/greedy-foveal-official-baseline-2 --max-fix 600 --spp 64` | about 7 min (Playground-2 MEASURED 416 s); authorized by Luiz as this step's acceptance run |
| C11 | `run.py evaluate --run $RUNS/greedy-foveal-official-baseline-2` | Interactive / Batch |
| C12 | `run.py checks --run $RUNS/greedy-foveal-official-baseline-2` | Batch |
| C13 | `check_equivalence.py run --run $RUNS/greedy-foveal-official-baseline-2 --baseline $RUNS/playground-sparse-lattice --known-answer` | Batch |
| C14 | `check_equivalence.py run --run $RUNS/greedy-foveal-official-baseline-2 --baseline $RUNS/greedy-foveal-official-baseline --out <scratch file>` (negative control against the v0 official run: **must FAIL**) | Batch |
| C15 | `run.py visualize --run $RUNS/greedy-foveal-official-baseline-2 --vis /home/lvelho/rd/f3d-vision/visuals/greedy-foveal-official-baseline-2` | Interactive / Batch |

## 5. Acceptance gate

All of the following must hold:

- **A1 (source):** `check_equivalence.py source` PASSES. All six files are executable-equal to
  `playground-2-sparse-lattice`, and the import closure loads only tracked, non-NS1e modules.
- **A2 (layout, hygiene):** C1 is clean, and `selftest` PASSES.
- **A3 (smoke):** C7 passes. Prefix equivalence with the Playground-2 run (C8) PASSES, and the full-mode comparison
  (C9) FAILS.
- **A4 (known answer, full reproduction):**

      stop at fixation 356, stop reason "no valid unseen fixation"
      100.00 % SEEN, 99.26 % DEPTH (2-decimal percentages)
      315 local saccades, 40 global saccades
      post-freeze Breadth-1 12 mm: 98.93 % of first-hit cells (253,023 / 255,758)
                                   98.82 % of first-hit solid angle

- **A5 (strong equivalence):** C13 PASSES, bitwise in every control-path product. C14 FAILS.
- **A6 (run checks):** C12 passes every check.

## 6. Stop conditions

- **Any divergence in the control path** (gaze, decision, coverage, points, fusion, final map or evaluation): stop,
  diagnose and report. No tuning, and no edit of promoted executable code to make numbers match. The decision
  returns to Luiz and Chat.
- A Blender / GPU / scene-asset difference from the Playground-2 run: diagnose; if real, stop and report.
- The layout checker fails for a reason other than this step's declarations: stop and report.

## 7. Permitted fixes

**Delegated:**

- documentation and docstring wording;
- defects in the retargeted `check_equivalence.py`, without weakening any rule (no tolerance replaces a bitwise
  rule);
- layout declarations of this step's own files;
- worktree set-up.

**Not delegated:** any executable change to promoted files, thresholds, parameters or render settings, and the
frozen runs and tags.

## 8. Results to record

Claude Code commits `docs/engineering/sparse-lattice-baseline-report.md` with:

- the branch and commits, the commands run, and the C3, C4, C8, C9, C13 and C14 summaries verbatim;
- the A4 numbers;
- the official run's `freeze.json` sha256;
- the wall time compared with the Playground-2 run;
- `visuals/greedy-foveal-official-baseline-2/overview.png`;
- A1–A6 with pass / fail, every deviation and every repair.

**After acceptance** (not part of this execution):

- `main` is fast-forwarded to the branch;
- the new official baseline gets the annotated tag `greedy-foveal-playground-baseline-2`;
- the README, `CLAUDE.md` and `docs/chat-handoff.md` cite this step's report.
