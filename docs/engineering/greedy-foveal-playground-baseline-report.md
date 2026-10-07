# Engineering-1: Official Greedy Foveal Playground Baseline — report

**Status: ACCEPTED by Luiz and Chat.** The official Greedy Foveal Playground baseline is established. `main` is
fast-forwarded to the acceptance commit, which carries the annotated tag `greedy-foveal-playground-baseline`.

    GREEDY_FOVEAL_PLAYGROUND_BASELINE_ACCEPTED
    GREEDY_FOVEAL_PLAYGROUND_BASELINE_OFFICIAL

The step was executed and reported as ENGINEERING REVIEW PENDING (`db14029`). Before acceptance, the root README
became the playground front door (`4baca8b`; section 12).

**Acceptance gate (contract §8): all of A1–A7 PASS.** The official reproduction is bitwise equivalent to the frozen
Greedy v0 grow600 run in every control-path product.

Contract: [`greedy-foveal-playground-baseline-contract.md`](greedy-foveal-playground-baseline-contract.md).
Architecture: [`docs/architecture/greedy-foveal-playground.md`](../architecture/greedy-foveal-playground.md).
Quick start: [`tools/greedy_foveal/README.md`](../../tools/greedy_foveal/README.md).

All numbers below are **MEASURED** from the runs and commands named with them, unless marked otherwise.

## 1. Result in one paragraph

The accepted Greedy Foveal Explorer v0 is now an official baseline on clean `main` ancestry. Five files were
extracted from the frozen tags with docstring-only edits (all 5 are AST-equal to their tags once docstrings are
removed). The branch adds a README, the architecture document and an equivalence checker. A clean reproduction from
this branch (`b77b1d9`, 64 spp, cap 600) **stopped at fixation 542** with `seen >= 99 % of 4 pi`: **99.00 % SEEN**,
**98.28 % DEPTH**, **322 local / 219 global** saccades, 16,517,811 surfels, 733 s. Post freeze, Breadth-1 coverage
within 12 mm is **98.52 % of first-hit cells (251,966 / 255,758)** and **98.32 % of first-hit solid angle**.
**Strong equivalence with the frozen grow600 run: PASS (23/23).** Every control-path product is bitwise identical
over all 542 fixations: gazes, decisions, points, oracle ids, fusion, coverage, the final map and the evaluation. Only
the presentation-only RGB differs, as expected. No deviation affected behavior.

## 2. Provenance

| item | value |
|---|---|
| source `origin/main` | `3f92ac314bbb1f0c0bfac25c9ca6bd55bb129b0f` (Greedy v0 closure), verified before branching |
| source tags | `greedy-foveal-explorer-v0-impl` → `a437df048b555d5b59f6855b6572eea2665ab0da`; `greedy-foveal-explorer-v0-demo` → `8066a246bf251fb1e2d66b7061899c32df236bf1` (both verified; not moved) |
| branch | `engineering/greedy-playground-baseline`, created from `origin/main` in an isolated worktree |
| ancestry | `3f92ac3` → contract → implementation → documentation → checker label fix → report. No merge or cherry-pick from `prototype/greedy-foveal-explorer-v0` or NS1e. |
| contract commit | `202feb282d4812f33e3f2c8f0f3cd1a17e938843` |
| implementation commit | `99a30478c7215ff57d61c6e56903fd128718b748` |
| documentation commit | `b77b1d9cdb9760cc6030d5e9ce7be017329535fc` (README, architecture document, one checker wording fix) |
| checker label fix | `09685be14233f8e3bf3c8d7e1679d551f6a06b2d` (informative label only; section 8) |
| official reproduction made at | `b77b1d9c…`, clean tracked tree (recorded in the run's `trajectory.json` `code`) |
| report commit | `db14029d7f3b1bbeaf53a4df336f7f2f73c56f0d` (status ENGINEERING REVIEW PENDING) |
| README front door | `4baca8b28f3e473bc7a5cc1d426b50d362080c0f` (section 12) |
| acceptance | the commit that records the status above; `main` and the tag `greedy-foveal-playground-baseline` point to it |

## 3. Files promoted

Extracted by `git show <tag>:<path>`. Each copy was verified blob-identical to its tag before any edit.

| file | source tag | tag blob | official blob | change |
|---|---|---|---|---|
| `tools/greedy_foveal/explorer.py` | `…-v0-impl` | `c06c59ed` | `1ea72865` | module docstring only |
| `tools/greedy_foveal/run.py` | `…-v0-impl` | `20364552` | `db11cdea` | module docstring only |
| `tools/greedy_foveal/render_server.py` | `…-v0-impl` | `ced1f8e7` | `eebff99d` | module docstring only |
| `tools/greedy_foveal/visuals.py` | `…-v0-demo` | `51c9cefb` | `b0d25227` | module docstring only |
| `tools/greedy_foveal/demo.py` | `…-v0-demo` | `b0ed7542` | `2a40f5a3` | module docstring only |

Docstring changes:

- "Greedy Foveal Explorer v0 (PROTOTYPE)" became "Greedy Foveal Explorer, official baseline".
- The references to prototype reports (which live only on the tags) became pointers to the architecture document, the
  README and the contract. `demo.py` now names its demo record "on tag `greedy-foveal-explorer-v0-demo`".
- `run.py` gained one sentence listing `checks` / `visualize`.

**Executable equivalence (A1):** `check_equivalence.py source` → **`SOURCE PASS (10/10)`**. All five files are
"docstrings / comments only" against their tag blobs. The host import closure loads, every module in it is tracked,
and none is from the NS1e lineage.

New files:

- `tools/greedy_foveal/check_equivalence.py` (`source` / `run` / `selftest`);
- `tools/greedy_foveal/README.md`;
- `docs/architecture/greedy-foveal-playground.md`;
- this report and the contract.

## 4. Architecture documentation and dependency map

`docs/architecture/greedy-foveal-playground.md` covers the 19 requested sections. It has three Mermaid diagrams
(system context, one fixation, the decision / stop rule), each also explained in prose. Section 15.2 is the dependency
map. Every reused module is classified CORE RUNTIME, SYNTHETIC OBSERVATION, POST-HOC EVALUATION or PRESENTATION, and
the three data dependencies are listed (Classroom `.blend`, the AB1a head-pose calibration, the Breadth-1 EXR). No
dependency was duplicated.

The host import closure was MEASURED by importing the official modules and listing the repository files loaded. It
holds `fsg_geometry`, `exr_lite`, `ab1b_{geometry,oracle,spec}`, `nb1a_guard`, `visual_language/style`, and for
`evaluate` / `checks` also `breadth1_{glance,spec}`, `classroom_oracle1_{eval,public}` and `fsg3_surface_map`. No
module is from the NS1e lineage.

Between `origin/main` and the tags, the NS1e lineage only **added** `tools/north_star/ns1e_*` files. It changed no
shared module (`git diff --stat 3f92ac3 <tag>`).

One architectural fact is documented, not changed. In this baseline the global map is written but never read during
control: coverage and edge evidence come from the current fixation's points (architecture §3).

## 5. Checks

| check | command | result |
|---|---|---|
| whitespace | `git diff --check` (each commit) | clean |
| repository layout | `.venv/bin/python tools/repository/check_repository_layout.py` | `SUMMARY checked=644 failed=0` at `99a3047` and `b77b1d9`; `SUMMARY checked=644 failed=0` at the report commit (`checked=637 failed=0` at the contract commit) |
| syntax | `PYTHONPYCACHEPREFIX=<scratch> .venv/bin/python -m py_compile tools/greedy_foveal/*.py` | OK (6 files) |
| imports / source equivalence | `check_equivalence.py source` | `SOURCE PASS (10/10 checks passed)` |
| comparator self-test | `check_equivalence.py selftest` | `SELFTEST PASS (15/15 checks passed)`. A changed constant, a changed operator, a 1-ULP array change, a dtype change, ±0.0, a 1-ULP SEEN value, a flipped decision kind, a changed fusion count, a 1-ULP gaze and a missing key are all rejected; docstring-, comment- and timing-only changes are accepted. |
| smoke run | `run.py explore --run …/greedy-foveal-official-baseline-smoke --max-fix 75` | see section 6 |
| smoke run checks | `run.py checks --run …-smoke` | `CHECKS PASS` (8/8; 74 decision states re-decided, 0 mismatches) |
| smoke prefix equivalence | `check_equivalence.py run --run …-smoke --baseline …/greedy-foveal-explorer-v0-grow600 --prefix` | `RUN PASS 17/17` |
| negative control | the same, full mode, `--known-answer` | **FAIL as required**: 11 of 21 checks fail (section 6) |
| full reproduction | section 7 | `FROZEN 542 fixations (322 local, 219 global), stop: seen >= 99 % of 4 pi` (section 7) |
| full run checks | `run.py checks --run …/greedy-foveal-official-baseline` | `CHECKS PASS` (8/8; 541 decision states re-decided, 0 mismatches; minimum fixation pair 3.75°) |
| strong equivalence | `check_equivalence.py run --run …/greedy-foveal-official-baseline --baseline …/greedy-foveal-explorer-v0-grow600 --known-answer` | **`RUN PASS (23/23 checks passed)`**, including the literal known answer (section 7) |

No mutation or corruption campaign was run. No Controller-01/02 check and no other experiment was rerun.

## 6. Smoke run

    .venv/bin/python tools/greedy_foveal/run.py explore \
        --run /home/lvelho/rd/f3d-vision/previews/greedy-foveal-official-baseline-smoke --max-fix 75

Run at `99a3047` (clean tree), 2026-10-07 10:06:45Z – 10:08:08Z. Console summary, verbatim:

    [gfe] render server ready in 0.5 s (OPTIX, 64 spp, code 99a30478)
    [gfe] FROZEN 75 fixations (73 local, 1 global), stop: fixation cap 75; seen 21.70% depth 21.54%; 3,875,207 surfels; wall 82 s

Fixation 69 is the first global saccade, at (+84.50°, +66.50°), as in the frozen run. Every fixation 1–75 is bitwise
equal to the first 75 of grow600:

- gazes, kinds and the 74 decisions with all their candidates;
- per-fixation XYZ, oracle ids and diagnostic errors;
- correspondence, fusion and coverage counts;
- calibrations (byte-identical);
- the 74 saved decision states;
- the SEEN and DEPTH histories, and the coverage state after #75 (equal to grow600's saved state at #75).

Prefix record: `previews/greedy-foveal-official-baseline-smoke/equivalence-prefix.json` (`all_pass: true`).

RGB, reported only (presentation; not a control input): 7,068,620 of 14,443,491 per-point RGB values differ from
grow600, max |Δ| 0.00735 (linear).

**Negative control.** The full-mode comparison of the same 75-fixation run against the 542-fixation baseline fails 11
of 21 checks:

- fixation count;
- the summary fields;
- the cap-truncated decision at #75;
- the missing decision states 75–541;
- the coverage arrays;
- the `checks.json` values;
- the final-map arrays;
- both PLYs;
- the missing evaluation;
- the known answer.

The shared prefix (directions, kinds, calibrations, points, states 1–74) still compares equal. Record:
`…-smoke/equivalence-negative-control.json` (`all_pass: false`).

## 7. Official reproduction

    .venv/bin/python tools/greedy_foveal/run.py explore  --run /home/lvelho/rd/f3d-vision/previews/greedy-foveal-official-baseline --max-fix 600 --spp 64
    .venv/bin/python tools/greedy_foveal/run.py evaluate --run /home/lvelho/rd/f3d-vision/previews/greedy-foveal-official-baseline
    .venv/bin/python tools/greedy_foveal/run.py checks   --run /home/lvelho/rd/f3d-vision/previews/greedy-foveal-official-baseline
    .venv/bin/python tools/greedy_foveal/check_equivalence.py run --run /home/lvelho/rd/f3d-vision/previews/greedy-foveal-official-baseline \
        --baseline /home/lvelho/rd/f3d-vision/previews/greedy-foveal-explorer-v0-grow600 --known-answer
    .venv/bin/python tools/greedy_foveal/run.py visualize --run /home/lvelho/rd/f3d-vision/previews/greedy-foveal-official-baseline \
        --vis /home/lvelho/rd/f3d-vision/visuals/greedy-foveal-official-baseline

Run at `b77b1d9cdb9760cc6030d5e9ce7be017329535fc` (clean tracked tree), Blender 5.2.1 LTS, OPTIX on the RTX 4090.
`explore` ran 2026-10-07 10:13:21Z – 10:25:39Z (12 min 17 s process time); the chained post-freeze steps finished at
10:26:31Z. Console summary lines, verbatim:

    [gfe] render server ready in 0.5 s (OPTIX, 64 spp, code b77b1d9c)
    [gfe] FROZEN 542 fixations (322 local, 219 global), stop: seen >= 99 % of 4 pi; seen 99.00% depth 98.28%; 16,517,811 surfels; wall 733 s
    [gfe] EVALUATED all-geometry 251,966/255,758 cells 98.52% (98.32% sr); authored 98.52% (98.25% sr); vectorized agrees True
    [gfe] CHECKS PASS
    [gfe-equiv] RUN PASS (23/23 checks passed)
    [gfe-visuals] wrote /home/lvelho/rd/f3d-vision/visuals/greedy-foveal-official-baseline/overview.png (2000, 3275)

### 7.1 Final metrics (official reproduction vs frozen grow600)

| quantity | official reproduction | frozen grow600 | equal |
|---|---|---|---|
| stop fixation / reason | 542 / `seen >= 99 % of 4 pi` | 542 / same | yes |
| SEEN / DEPTH | 99.00 % / 98.28 % (0.99004936 / 0.98281148) | same | bitwise |
| local / global saccades | 322 / 219 | 322 / 219 | yes |
| final surfels | 16,517,811 | 16,517,811 | bitwise map |
| Breadth-1 12 mm, all geometry | 251,966 / 255,758 cells = 98.52 %; 98.32 % sr | same | exact |
| authored (Object Index > 0) | 98.52 % cells; 98.25 % sr | same | exact |
| Object Index 0, solid angle | 98.69 % | same | exact |
| NN distance over covered cells | median 0.727 mm, p90 2.240 mm | same | exact |
| control opens / Breadth-1 opens | 3,813 / none | 3,813 / none | yes |
| wall time | 733 s | 729 s | (timing) |
| stage sums: render / fusion / correspondence / geometry / policy | 413.5 / 257.8 / 18.2 / 12.6 / 3.3 s | 412.0 / 255.3 / 18.3 / 12.6 / 3.3 s | (timing) |
| evaluation time | 26.3 s | 26.0 s | (timing) |

### 7.2 Strong equivalence

`check_equivalence.py run … --known-answer`, record `previews/greedy-foveal-official-baseline/equivalence.json`
(sha256 `0e040fdc…`, made by the committed checker at `09685be`): **`RUN PASS (23/23 checks passed)`**.

| compared | result |
|---|---|
| fixation count; summary fields (stop reason, counts, final SEEN / DEPTH, surfels, parameters, server settings / seeds / passes) | equal |
| per-fixation records 1..542: gaze, kind, how chosen, full decision, all 8 local candidates, correspondence / fusion / coverage counts, SEEN / DEPTH, diagnostic error | equal |
| LOCAL / GLOBAL sequence and fixation directions in order | equal |
| 542 `calibration.json` | byte-identical |
| 542 `points.npz`: `xyz_h`, `instance_id_oracle`, `err_mm` | bitwise |
| 541 `policy/state-NNNN.npz` | bitwise |
| `coverage.npz` (state, SEEN and DEPTH histories, row weights) | bitwise; the file is even byte-identical (sha256 `37d3a2ed…`, as in the closure record) |
| `final-map.npz` `xyz_h` / `instance_id_oracle` / `support_count` / `first_fixation` / `patch_ids` / `radius_cell_m` | bitwise |
| `final-map-oracle-segmentation.ply` | byte-identical (sha256 `bd98dc5a…`, as in the closure record) |
| `final-map.ply` header and XYZ | bitwise |
| `evaluation.json` blocks, `evaluation.npz` | equal / bitwise |
| `checks.json` | all pass in both; equal values |
| literal known answer | `542 / seen >= 99 % of 4 pi / 99.00 / 98.28 / 322 / 219 / 251,966 / 255,758 / 98.52 / 98.32`: all match |

RGB, reported only (presentation; never a control input):

- per-point RGB: 48,606,369 of 101,545,785 values differ, max |Δ| 0.118 (linear);
- final-map RGB: max |Δ| 0.039, mean |Δ| 1.1e-7;
- display PLY colours: 3,127 of 49,553,433 channel values differ (max 41 / 255).

So `final-map.npz` and `final-map.ply` differ in bytes only through RGB, and `trajectory.json` only through commit and
timings.

### 7.3 Products

- Run: `/home/lvelho/rd/f3d-vision/previews/greedy-foveal-official-baseline/` (2.2 GB; gitignored, Policy 1).
  `freeze.json` sha256 `6bc9b190e4e15d8482865b3b98c0e8e95044912205a744b56591b48ca56e7bf9` (frozen 10:25:38Z);
  `final-map.npz` `f07e3232…`, `trajectory.json` `3422ed30…`, `evaluation.json` `097e2623…`.
- Visual (presentation only): `/home/lvelho/rd/f3d-vision/visuals/greedy-foveal-official-baseline/overview.png`
  (sha256 `67597fec…`). It shows the same trajectory, coverage, statistics and top views as the frozen run's overview.
- The frozen grow600 run is unchanged: `freeze.json` `a4283ab7…`, `final-map.npz` `90730b43…`, `evaluation.json`
  `65f8353c…`, all as in the closure record.

## 8. Deviations and decisions

- **No `tools/greedy_foveal/__init__.py`.** The repository layout checker forbids `__init__.py` under `tools/` ("no
  `__init__.py` under tools/"). The files use the repository's script-style `sys.path` imports. Declared in the
  contract, section 4.
- **The layout checker was extended**, with declarations only: the `engineering` docs directory, the `greedy_foveal`
  tools directory, the contract (required), and this step's report, architecture document and tools (allowed). Every
  earlier step did the same. No check was weakened.
- **A sixth file in `tools/greedy_foveal/`:** `check_equivalence.py`. The README lists the five source files and the
  checker separately.
- **The README went into the documentation commit, not the implementation commit.** Its link to the architecture
  document must resolve (the layout checker checks every Markdown link).
- **Executable "prototype" strings were kept:**
  - the `trajectory.json` label `"PROTOTYPE (not a scientific milestone)"`;
  - the `overview.png` subtitle "PROTOTYPE. …";
  - the demo poster footer naming `prototype/greedy-foveal-explorer-v0`.

  Changing them would change output bytes. A later presentation-only step may change them.
- **`--help` text changed.** `run.py`, `render_server.py` and `demo.py` print their module docstring as the argparse
  description. This was declared in the contract (section 3).
- **`demo.py` still replays the frozen grow600 run.** Its paths are hard-coded; they were not parameterized, because
  that would change executable code.
- **One checker fix, delegated** (contract §10): the `check_equivalence.py` summary line printed "10/21" for a failing
  run, which was ambiguous. It now prints "(10/21 checks passed); 11 failed". No comparison rule changed.
- **Smoke size 75** (contract C6): the smallest round size that includes the first global saccade (#69).
- Environment note: the shared checkout's local `main` is still at `e681392` (behind `origin/main`). This work used
  `origin/main` `3f92ac3` and its `CLAUDE.md` throughout. The worktree uses `.venv` and `scenes/classroom/*` symlinks
  to the shared checkout.

- **A second delegated checker fix** (`09685be`, after the full run): an *informative* label of the freeze-hash
  report claimed that `.npz` archives carry zip timestamps. The reproduction disproved it: `coverage.npz` is
  byte-identical, because numpy writes the fixed 1980 zip date. The label now names RGB and run metadata as the reasons
  hashes differ. No comparison rule changed. The source check, the full and prefix comparisons and the negative control
  were then re-run from the committed `09685be` (same results), so all three records name a clean commit. The
  contract's §7 sentence about zip timestamps was harmless (the payload comparison was declared anyway) but is
  inaccurate; the contract is left as committed and corrected here.
- **The architecture document was updated with the official result** in the report commit: §17 now cites the
  full-run RGB differences and links this report. The edit is documentation only.
- No deviation in behavior. No stop condition fired. No executable change was made to the promoted code.

## 9. Acceptance gate (contract §8)

| gate | result |
|---|---|
| A1 source | PASS: 5 / 5 executable-equal |
| A2 layout | PASS: `checked=644 failed=0` |
| A3 smoke | PASS: checks pass, prefix equivalence PASS, negative control FAILS |
| A4 known answer | PASS: 542; `seen >= 99 % of 4 pi`; 99.00 % / 98.28 %; 322 / 219; 98.52 % (251,966 / 255,758); 98.32 % sr |
| A5 strong equivalence | PASS: `RUN PASS (23/23 checks passed)` against grow600, `--known-answer` |
| A6 run checks | PASS: `CHECKS PASS` (8/8) |
| A7 hygiene / documentation | PASS: `git diff --check` clean on every commit; contract, code, README, architecture document and report committed and pushed |

## 10. Unresolved decisions (for Luiz and Chat)

- ~~Whether to accept the official baseline and merge it into `main`.~~ Accepted. `main` was fast-forwarded and
  tagged.
- Whether a later presentation-only step should replace the remaining executable "PROTOTYPE" labels and parameterize
  the demo paths.
- Which single-component playground experiment comes first (architecture §16).

## 11. Proposed outlines for the next two deliverables (outlines only)

### A. Technical report

1. **Motivation.** Why reconstruct a whole scene through a small fovea and eye movements, instead of a wide-field
   sensor. Active vision and the cost of high resolution everywhere.
2. **Active foveal vision concept.** Fixed head, two foveated eyes, saccades. Measure locally and remember globally.
   The cyclopean sphere as the controller's memory.
3. **System architecture.** The loop FIXATE → RECONSTRUCT → SACCADE; the persistent state (map, coverage, visited
   gazes); the coordinate systems (architecture §2–§6).
4. **Measurement model.** The binocular sensor (63 mm baseline, 2.1 m vergence, 12° core). PERFECT / ORACLE
   correspondence as a replaceable service, and its truth-stripped interface. Spherical epipolar triangulation.
   Precision and conditioning.
5. **Greedy exploration.** Local rule (EDGE_SUPPORT × UNSEEN_GAIN over 8 tangent-frame neighbours); global rule
   (deepest cell of the largest UNSEEN region); stop rule. Determinism.
6. **Global reconstruction.** One H0 surfel map; the 12-mm association / fusion rule; storage behavior.
7. **Implementation.** The persistent Blender render server, the file protocol, the host loop, freeze and firewall,
   the data products, the software and dependency map.
8. **Classroom proof of concept.** Setup: static Classroom, 64 spp, PERFECT correspondence, Breadth-1 first-hit
   reference used only after the freeze.
9. **Results.** 542 fixations to 99 % SEEN (322 local / 219 global); SEEN / DEPTH growth curves; 98.32 % of first-hit
   solid angle within 12 mm; the final map; timing; bitwise reproducibility (Engineering-1).
10. **Limitations.** Oracle correspondence, fixed head, synthetic scene, first-hit evaluation, the greedy tail,
    storage.
11. **Playground / future research.** The extension-point table (architecture §16): natural stereo, map-driven
    frontiers, smarter global ordering, head motion, natural segmentation, other scenes.

### B. Slide presentation

1. **Why foveal active vision?** High resolution only where you look; reconstruct a 360° scene by looking around.
2. **The eye-inspired idea.** Two eyes, a 12° fovea, saccades, a fixed head.
3. **FIXATE → RECONSTRUCT → SACCADE.** The whole loop on one slide.
4. **Architecture.** The system-context diagram: render service → binocular view → reconstruction → map / coverage /
   edge evidence → policy.
5. **One fixation.** Gaze → stereo pair → correspondence → spherical triangulation → about 65 k points in H0 → 12-mm
   fusion → coverage update.
6. **Local vs global saccades.** Edge support × unseen gain; the jump to the deepest unexplored cell; a trajectory
   figure.
7. **Cyclopean memory.** The 1° UNSEEN / SEEN / DEPTH sphere, with solid-angle accounting.
8. **Reconstruction growth.** SEEN / DEPTH vs fixation; the surfel count; the map at #200, #450 and #542.
9. **Demo.** `demo.mp4` (62 s replay).
10. **Final result.** Stop at 542; 99.00 % SEEN; 98.32 % of the first-hit scene within 12 mm; reproducible bitwise.
11. **Limitations.** Oracle stereo, fixed head, synthetic scene, the greedy tail.
12. **Playground / next directions.** One component at a time: natural stereo, map-driven policy, head motion,
    segmentation, other scenes.

## 12. README front door (before acceptance)

As Luiz requested before acceptance, the root `README.md` was rewritten as the concise front door of the Active Foveal
Playground (`4baca8b`). It covers:

- the idea and the loop;
- the Engineering-1 baseline numbers and the 23 / 23 equivalence;
- what the baseline does;
- the note that the gaze policy does not read the 3-D map;
- a minimal quick start with no home-directory paths;
- the code map and the extension points;
- the demo, described as workstation-local and not hosted on GitHub;
- limitations, documentation links and project history.

The former README is preserved verbatim, below a short historical notice, in `docs/repository/README-history.md`.

**Deviation, necessary for the README change:** the layout checker hard-coded the former README's structure (its
title and its two sections). Its README contract now names the new title and section list, still exact, and still
with no deeper headings. It adds one check that the history file ends with `git show 3f92ac3:README.md` verbatim.
Both new checks were exercised with a temporary tamper; each failed as expected, and the files were restored. No other
structural change was made.

Checks at `4baca8b`:

- `git diff --check`: clean;
- the layout checker: `SUMMARY checked=645 failed=0` (36 Markdown links, 0 broken);
- `check_equivalence.py source`: `SOURCE PASS (10/10 checks passed)`.

No Blender, no experiment and no replay was run. Greedy executable code is unchanged since `99a3047`.

---

    GREEDY FOVEAL PLAYGROUND BASELINE — ACCEPTED
    OFFICIAL PLAYGROUND — ESTABLISHED
    NEXT — TECHNICAL REPORT
