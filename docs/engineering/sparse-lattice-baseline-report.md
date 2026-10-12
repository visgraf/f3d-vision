# Engineering-2: promote the sparse covering lattice to the official baseline — report

**Status: ACCEPTED** by Luiz on 2026-10-12 (section 9). The sparse covering lattice is the official baseline on
`main`. Claude Code executed this step on the workstation under the contract below; ClaudeChat reviewed it.

    SPARSE_LATTICE_BASELINE_ACCEPTED
    SPARSE_LATTICE_BASELINE_OFFICIAL

**Acceptance gate (contract §5): all of A1–A6 PASS.** The official reproduction from this branch is **bitwise
equivalent to the accepted Playground-2 run in every control-path product (23 / 23)**, and it meets the known answer
exactly.

Contract: [`sparse-lattice-baseline-contract.md`](sparse-lattice-baseline-contract.md).
Promoted behavior: [Playground-2 report](../playground/sparse-lattice-report.md).
Previous baseline: [Engineering-1 report](greedy-foveal-playground-baseline-report.md).
Quick start: [`tools/greedy_foveal/README.md`](../../tools/greedy_foveal/README.md).

All numbers are **MEASURED** from the runs and commands named with them.

## 1. Result in one paragraph

The branch carries the accepted Playground-2 explorer on clean `main` ancestry:

- `explorer.py` differs from tag `playground-2-sparse-lattice` in docstrings and comments only;
- `run.py`, `render_server.py`, `visuals.py`, `demo.py` and `check_lattice.py` are byte-identical to the tag.

A clean reproduction from `a5f1aae` (64 spp, cap 600) **stopped at fixation 356** with `no valid unseen fixation`:

- **100.00 % SEEN, 99.26 % DEPTH**;
- **315 local / 40 global** saccades;
- 16,943,073 surfels;
- 413 s.

Post freeze, Breadth-1 coverage within 12 mm is **98.93 % of first-hit cells (253,023 / 255,758)** and **98.82 % of
first-hit solid angle**.

The equivalence checker's verdicts:

- against the frozen Playground-2 run: **PASS, 23 / 23**. Gazes, decisions, candidates, calibrations, points,
  policy states, coverage, the final map, the PLYs and the evaluation are bitwise identical over all 356 fixations;
  only the presentation RGB differs, as expected;
- the negative controls fail as required: the full-mode smoke comparison (10 / 20) and the comparison against the
  v0 official run (6 / 22).

No repair was needed, and no executable code was touched.

## 2. Provenance

| item | value |
|---|---|
| promoted tag | `playground-2-sparse-lattice` → `1f50bd6a3f3cf77ccf260375b2cf2fee60c4738f`. Annotated tag object `b76f7ba26546d0ba5004f74df19793da8daad812`, created and pushed by Claude Code in this step on Luiz's instruction (section 7, D1). |
| branch | `engineering/sparse-lattice-baseline`, from `origin/main` `41c7193` (the Playground-2 acceptance) |
| start head | `a5f1aae0ee2ccffff87cb0a9d8101023cd7ea8f5`, verified equal to `origin/engineering/sparse-lattice-baseline` before starting |
| contract commit | `cb1217b` (ClaudeChat) |
| code and documentation commit | `a5f1aae` (ClaudeChat): the promotion, the retargeted `check_equivalence.py`, README, tools README and architecture document |
| official reproduction made at | `a5f1aae0…`, branch `engineering/sparse-lattice-baseline`, `tracked_dirty: []` (the run's `trajectory.json` / `freeze.json` `code`) |
| behavioral known answer | `previews/playground-sparse-lattice/`: code `70d992e`; `freeze.json` sha256 `3f8bf4bd…4a7d` |
| report commit | the commit that adds this file |
| workspace | an isolated worktree on a local branch tracking `origin/engineering/sparse-lattice-baseline`; `.venv` and `scenes/classroom/*` symlinked from the shared checkout |

## 3. Commands actually run

From the worktree root, in contract order, with `RUNS=/home/lvelho/rd/f3d-vision/previews`:

- `check_equivalence.py` is `.venv/bin/python tools/greedy_foveal/check_equivalence.py`;
- the run tool is `.venv/bin/python tools/greedy_foveal/run.py`.

| # | command | wall | exit |
|---|---|---|---|
| C1 | `git diff --check` (and `git diff --check 41c7193 HEAD`; D2); `.venv/bin/python tools/repository/check_repository_layout.py` | interactive | 0, 0; 0 |
| C2 | `.venv/bin/python -m py_compile tools/greedy_foveal/*.py` | interactive | 0 |
| C3 | `check_equivalence.py source` | interactive | 0 |
| C4 | `check_equivalence.py selftest` | interactive | 0 |
| C5 | `.venv/bin/python tools/greedy_foveal/check_lattice.py` | 2 s | 0 |
| C6 | `run.py explore --run $RUNS/greedy-foveal-official-baseline-2-smoke --max-fix 75` | 77 s | 0 |
| C7 | `run.py checks --run $RUNS/greedy-foveal-official-baseline-2-smoke` | interactive | 0 |
| C8 | `check_equivalence.py run --run $RUNS/greedy-foveal-official-baseline-2-smoke --baseline $RUNS/playground-sparse-lattice --prefix` | interactive | 0 |
| C9 | the same without `--prefix` | interactive | 1, as required |
| C10 | `run.py explore --run $RUNS/greedy-foveal-official-baseline-2 --max-fix 600 --spp 64` | 417 s (`wall_seconds` 412.8) | 0 |
| C11 | `run.py evaluate --run $RUNS/greedy-foveal-official-baseline-2` | 27.7 s | 0 |
| C12 | `run.py checks --run $RUNS/greedy-foveal-official-baseline-2` | interactive | 0 |
| C13 | `check_equivalence.py run --run $RUNS/greedy-foveal-official-baseline-2 --baseline $RUNS/playground-sparse-lattice --known-answer` | 8.6 s | 0 |
| C14 | `check_equivalence.py run --run $RUNS/greedy-foveal-official-baseline-2 --baseline $RUNS/greedy-foveal-official-baseline --out <session scratch>/C14-equivalence-vs-v0.json` | 7.7 s | 1, as required |
| C15 | `run.py visualize --run $RUNS/greedy-foveal-official-baseline-2 --vis /home/lvelho/rd/f3d-vision/visuals/greedy-foveal-official-baseline-2` | 7.7 s | 0 |

C10 ran detached (`setsid nohup`) from a script file, so it would not depend on the agent's tool-call lifetime. The
command itself is as listed.

### C1, C2, C5, C7, C12

    (git diff --check: no output, exit 0; git diff --check 41c7193 HEAD: no output, exit 0)
    [repository-layout] SUMMARY checked=655 failed=0
    (py_compile: exit 0)
    [lattice] SUMMARY checked=9 failed=0 (2 s)
    C7:  [gfe] CHECKS PASS   (8 / 8; no_duplicate min pair 10.16 deg, deterministic_policy 74 states rechecked)
    C12: [gfe] CHECKS PASS   (8 / 8; no_duplicate min pair 5.99 deg, deterministic_policy 355 states rechecked)

### C3 (verbatim)

    [gfe-equiv] PASS tag playground-2-sparse-lattice -> 1f50bd6a3f3c  1f50bd6a3f3cf77ccf260375b2cf2fee60c4738f
    [gfe-equiv] PASS tag greedy-foveal-explorer-v0-impl -> a437df048b55  a437df048b555d5b59f6855b6572eea2665ab0da
    [gfe-equiv] PASS tools/greedy_foveal/explorer.py executable-equal to playground-2-sparse-lattice  docstrings / comments only
    [gfe-equiv] PASS tools/greedy_foveal/run.py executable-equal to playground-2-sparse-lattice  byte-identical
    [gfe-equiv] PASS tools/greedy_foveal/render_server.py executable-equal to playground-2-sparse-lattice  byte-identical
    [gfe-equiv] PASS tools/greedy_foveal/visuals.py executable-equal to playground-2-sparse-lattice  byte-identical
    [gfe-equiv] PASS tools/greedy_foveal/demo.py executable-equal to playground-2-sparse-lattice  byte-identical
    [gfe-equiv] PASS tools/greedy_foveal/check_lattice.py executable-equal to playground-2-sparse-lattice  byte-identical
    [gfe-equiv] PASS host import closure loads
    [gfe-equiv] PASS host import closure: every loaded repository module is tracked
    [gfe-equiv] PASS host import closure: no NS1e-lineage module
    [gfe-equiv] SOURCE PASS (11/11 checks passed)

### C4

    [gfe-equiv] SELFTEST PASS (15/15 checks passed)

The 15 controls: source ×5 (identical text, docstring-only and comment-only changes accepted; a changed constant and
a changed operator rejected); bitwise ×4 (identical accepted; one-ULP, dtype and −0.0 vs +0.0 rejected); SEEN history
one-ULP ×1; entry ×5 (timing-only accepted; flipped decision kind, changed fusion count, one-ULP gaze and a missing
key rejected).

### C8

    [gfe-equiv] RUN PASS (17/17 checks passed)

The 17 checks cover fixations 1–75 against the first 75 of the Playground-2 run: per-fixation records, the LOCAL /
GLOBAL sequence, directions, calibrations byte-identical, points bitwise, policy states 1–74 bitwise, row weights,
the SEEN / DEPTH histories and the coverage state after #75 bitwise, the freeze, the Breadth-1 firewall and the run
checks. Its record is the smoke run's `equivalence-prefix.json`.

### C9 (negative control)

    [gfe-equiv] RUN FAIL (10/20 checks passed); 10 failed: ['fixation count', 'trajectory summary fields (all control fields)', 'per-fixation records 1..75 (gaze, kind, decision, candidates, correspondence, fusion, coverage, SEEN / DEPTH, diagnostic error)', 'policy decision states present in both 1..75', 'coverage.npz state / SEEN history / DEPTH history / row weights bitwise', 'run.py checks: equal check values', 'final-map.npz xyz_h / instance_id_oracle / support_count / first_fixation / patch_ids / radius_cell_m bitwise', 'final-map-oracle-segmentation.ply byte-identical', 'final-map.ply header and XYZ bitwise', 'post-hoc evaluation present in both runs']

The 75-fixation smoke run is rejected as a full reproduction: the count, the stop and the final products differ.
The per-fixation gazes, calibrations and points of 1–75 still pass, as they should. Fixation 75 fails only on its
`next` / `local_candidates` (the smoke run's cap stops it there).

### C13 (verbatim)

    [gfe-equiv] PASS fixation count  356 vs 356
    [gfe-equiv] PASS trajectory summary fields (all control fields)
    [gfe-equiv] PASS per-fixation records 1..356 (gaze, kind, decision, candidates, correspondence, fusion, coverage, SEEN / DEPTH, diagnostic error)
    [gfe-equiv] PASS LOCAL / GLOBAL sequence 1..356
    [gfe-equiv] PASS fixation directions in order 1..356
    [gfe-equiv] PASS per-fixation files present 1..356
    [gfe-equiv] PASS calibration.json byte-identical 1..356
    [gfe-equiv] PASS points.npz xyz_h/instance_id_oracle/err_mm bitwise 1..356
    [gfe-equiv] PASS policy decision states present in both 1..356
    [gfe-equiv] PASS policy decision states bitwise 1..356
    [gfe-equiv] PASS coverage.npz state / SEEN history / DEPTH history / row weights bitwise
    [gfe-equiv] PASS run products unchanged since its freeze
    [gfe-equiv] PASS control process opened no Breadth-1 path (run)
    [gfe-equiv] PASS run.py checks: all pass (run)
    [gfe-equiv] PASS run.py checks: equal check values
    [gfe-equiv] PASS final-map.npz keys
    [gfe-equiv] PASS final-map.npz xyz_h / instance_id_oracle / support_count / first_fixation / patch_ids / radius_cell_m bitwise
    [gfe-equiv] PASS final-map-oracle-segmentation.ply byte-identical
    [gfe-equiv] PASS final-map.ply header and XYZ bitwise
    [gfe-equiv] PASS evaluation.json coverage blocks, NN distances, reference and cross-check
    [gfe-equiv] PASS evaluation freeze link: evaluation names the run's own freeze
    [gfe-equiv] PASS evaluation.npz cells / covered / instance bitwise
    [gfe-equiv] PASS known answer: 356 / no valid unseen fixation / 100.00 % / 99.26 % / 315 local / 40 global / 98.93 % cells (253,023 / 255,758) / 98.82 % sr
    [gfe-equiv] RUN PASS (23/23 checks passed)

The checker also reports, without comparing:

- **RGB:** 31,763,457 of 66,248,853 per-point values differ, max |Δ| 0.038. In the final map 26,537,157 of
  50,829,219 values differ. Only 360 of the 50.8 M 8-bit PLY display colours differ.
- **Freeze-file bytes:** `coverage.npz` and `final-map-oracle-segmentation.ply` are byte-identical to Playground-2's;
  `trajectory.json`, `final-map.npz` and `final-map.ply` differ in RGB and metadata only.
- **Open audit:** 2,512 host opens in both runs.

Its record is the official run's `equivalence.json`.

### C14 (negative control against the v0 official run)

    [gfe-equiv] RUN FAIL (6/22 checks passed); 16 failed: ['fixation count', 'trajectory summary fields (all control fields)', 'per-fixation records 1..356 (gaze, kind, decision, candidates, correspondence, fusion, coverage, SEEN / DEPTH, diagnostic error)', 'LOCAL / GLOBAL sequence 1..356', 'fixation directions in order 1..356', 'calibration.json byte-identical 1..356', 'points.npz xyz_h/instance_id_oracle/err_mm bitwise 1..356', 'policy decision states present in both 1..356', 'policy decision states bitwise 1..356', 'coverage.npz state / SEEN history / DEPTH history / row weights bitwise', 'run.py checks: equal check values', 'final-map.npz xyz_h / instance_id_oracle / support_count / first_fixation / patch_ids / radius_cell_m bitwise', 'final-map-oracle-segmentation.ply byte-identical', 'final-map.ply header and XYZ bitwise', 'evaluation.json coverage blocks, NN distances, reference and cross-check', 'evaluation.npz cells / covered / instance bitwise']

The two runs agree at fixation 1, at gaze (0°, 0°). They diverge from its decision on: calibrations and points from
#2 on. The six checks that pass are ones that do not compare the two runs' control paths:

- files present;
- the run unchanged since its freeze;
- no Breadth-1 open in the run;
- the run's own checks pass;
- the map keys;
- the evaluation's link to its own freeze.

The record went to a session scratch file, not to either run directory (`--out`). The v0 official run's own
`equivalence.json` was verified sha256-unchanged after C14.

### C10, C11, C15

    [gfe] FROZEN 356 fixations (315 local, 40 global), stop: no valid unseen fixation; seen 100.00% depth 99.26%; 16,943,073 surfels; wall 413 s
    [gfe] EVALUATED all-geometry 253,023/255,758 cells 98.93% (98.82% sr); authored 98.97% (98.81% sr); vectorized agrees True
    [gfe-visuals] wrote /home/lvelho/rd/f3d-vision/visuals/greedy-foveal-official-baseline-2/overview.png (2000, 3275)

## 4. The A4 numbers and the official run

| quantity | official run (C10–C11) | known answer (Playground-2 run) |
|---|---|---|
| stop | fixation 356, `no valid unseen fixation` | 356, `no valid unseen fixation` |
| SEEN / DEPTH | 100.00 % / 99.26 % | 100.00 % / 99.26 % |
| local / global saccades | 315 / 40 | 315 / 40 |
| Breadth-1 12 mm, cells | 253,023 / 255,758 = 98.93 % | 253,023 / 255,758 = 98.93 % |
| Breadth-1 12 mm, solid angle | 98.82 % (0.9882278408816154) | 98.82 % (0.9882278408816154) |
| final surfels | 16,943,073 | 16,943,073 |

**Official run `freeze.json` sha256: `e090d629408ee1106ad35cb129d32720533f068a3d48bbbaf3c82dc20b800559`.** It differs
from Playground-2's `3f8bf4bd…`, because the freeze records the code, the time and the hashes of the RGB-carrying
files.

Other hashes:

| file | sha256 |
|---|---|
| `coverage.npz` | `88f0fa44693f4b2b9c0b22a2ed2d85d5a76bed0683ec259b3c7cdcf8e9b9c937` (equal to Playground-2's) |
| `checks.json` | `e72dba6b…44e4` (equal to Playground-2's) |
| `trajectory.json` | `3b2f578d…9b0d` |
| `evaluation.json` | `ddf4cc6e…4a9e` |
| `equivalence.json` (C13) | `c5c21b5b…3251` |

**Wall time, compared with the Playground-2 run** (`wall_seconds`; sums over fixations):

| | official run | Playground-2 |
|---|---|---|
| wall | 412.8 s | 416.4 s |
| render | 269.9 s | 270.7 s |
| correspondence (incl. EXR load) | 11.9 s (6.1 s) | 11.9 s (6.1 s) |
| geometry | 8.2 s | 8.2 s |
| fusion | 103.4 s | 105.7 s |
| policy | 1.6 s | 1.6 s |
| server start | 0.45 s | 0.50 s |

So the run is 3.6 s (0.9 %) faster; the difference is not attributed. The v0 official baseline took 733.1 s.

### Visual

`visuals/greedy-foveal-official-baseline-2/overview.png` (2000 × 3275; sha256 `0bdf8786…2eba`), in the shared
checkout's `visuals/`. It shows the same content as `visuals/playground-sparse-lattice/overview.png`. Its bytes
differ, because it embeds display RGB and the wall time (413 s against 416 s).

## 5. Acceptance gate (contract §5)

| # | criterion | measured | result |
|---|---|---|---|
| A1 | `source` PASSES: six files executable-equal to `playground-2-sparse-lattice`; clean import closure | 11 / 11 | **PASS** |
| A2 | C1 clean; `selftest` PASSES | diff-check clean, layout 655 / 0, py_compile ok; selftest 15 / 15 | **PASS** |
| A3 | C7 passes; C8 PASSES; C9 FAILS | C7 8 / 8; C8 17 / 17; C9 FAIL 10 / 20 | **PASS** |
| A4 | 356, `no valid unseen fixation`, 100.00 % / 99.26 %, 315 / 40, 98.93 % cells (253,023 / 255,758), 98.82 % sr | exactly these (section 4) | **PASS** |
| A5 | C13 PASSES bitwise; C14 FAILS | C13 23 / 23; C14 FAIL 6 / 22 | **PASS** |
| A6 | C12 passes every check | 8 / 8 | **PASS** |

## 6. Run evidence

| path (shared checkout) | contents |
|---|---|
| `previews/greedy-foveal-official-baseline-2/` | C10–C13: 356 fixations; `freeze.json`, `trajectory.json`, `coverage.npz`, `final-map.npz`, PLYs, policy states, `evaluation.json` / `.npz`, `checks.json`, `equivalence.json` (C13 PASS); 2.0 GB |
| `previews/greedy-foveal-official-baseline-2-smoke/` | C6–C9: 75 fixations; `equivalence-prefix.json` (C8 PASS, sha256 `8c9e20a3…3099`) and `equivalence.json` (C9's FAIL record, `9c19b141…12b6`; D3); 472 MB |
| `visuals/greedy-foveal-official-baseline-2/overview.png` | C15 |

## 7. Deviations and repairs

- **Repairs: none.** No executable code, documentation, check or layout declaration was changed on the
  workstation. The code that ran is `a5f1aae`.
- **D1. The tag `playground-2-sparse-lattice` was created in this step.** It did not exist on origin. On Luiz's
  instruction, Claude Code created it at `1f50bd6` with the given message, after verifying that `1f50bd6` is the
  head of `playground/sparse-lattice` and differs from the run's code `70d992e` only under `docs/`.
  - The first `git push` of the tag failed with a truncated error.
  - The immediate retry succeeded as `[new tag]`, so no other writer had created it.
  - Origin's tag object `b76f7ba…` equals the local one and resolves to `1f50bd6`.
  - The tags `playground-1-gaze-lattice` and `greedy-foveal-playground-baseline` did not move.
- **D2. C1's `git diff --check`.** On a clean tree, `git diff --check` compares the working tree with the index and is
  trivially empty. It was also run over the branch's own changes (`git diff --check 41c7193 HEAD`), also clean.
- **D3. C9's record lands in the smoke run directory.** C9, as the contract writes it (no `--out`), wrote its FAIL
  record to `previews/greedy-foveal-official-baseline-2-smoke/equivalence.json`, next to C8's PASS record
  `equivalence-prefix.json`. It is the honest record of the negative control. A reader should take the smoke run's
  verdict from `equivalence-prefix.json`.
- **D4. Overview title.** The overview still reads "Greedy Foveal Explorer v0 — …", `visuals.py`'s default.
  Contract §3 keeps executable strings unchanged in this step.

## 8. After acceptance (contract §8; not executed)

These are Luiz's decisions:

- fast-forward `main` to this branch;
- tag the new official baseline `greedy-foveal-playground-baseline-2`;
- update the README, `CLAUDE.md` and `docs/chat-handoff.md` to cite this report.

## 9. Acceptance

**Decision (Luiz, 2026-10-12): ACCEPTED.** `main` is fast-forwarded to this branch. The new official baseline gets
the annotated tag **`greedy-foveal-playground-baseline-2`** at the acceptance commit. The previous official baseline
(v0 behavior) stays at `greedy-foveal-playground-baseline`.

### ClaudeChat review notes

- **Verified from GitHub.** `f108e5e` adds only this report, on top of `a5f1aae`, the code the official run recorded
  with a clean tree. The Chat-sandbox source check, selftest and lattice checks reproduce C3, C4 and C5.
- **The gate holds as declared.** The reproduction is bitwise equal to the Playground-2 run (23 / 23) and meets the
  known answer exactly. Both negative controls fail.
- **D3 is the contract's omission.** C9 had no `--out`, so its FAIL record sits in the smoke run directory. The smoke
  run's verdict is `equivalence-prefix.json`.
- **D4.** The default overview title still says v0. It is an executable string, kept by contract §3; a later
  presentation step may change it.
