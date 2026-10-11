# Playground-1 visualization package: contract

**Status: EXECUTED and ACCEPTED** (2026-10-11; see [the report](gaze-lattice-visuals-report.md), section 10). This step was requested by Luiz on 2026-10-11 and is presentation only. It
replays the accepted Playground-1 run in the format of the frozen Greedy v0 demo. ClaudeChat wrote this contract
and the code changes; Claude Code renders, builds and checks on the workstation.

| item | value |
|---|---|
| branch | `playground/gaze-lattice`, continuing after the accepted state `3c64c1f` (tag `playground-1-gaze-lattice`, which does not move) |
| run replayed | `previews/playground-gaze-lattice/`, frozen at code `85fb962`, `freeze.json` sha256 `e1422fb4…6b3c`; accepted MEASURED values in `docs/playground/gaze-lattice-report.md` |
| format model | the frozen v0 demo: `visuals/greedy-foveal-explorer-v0-demo/` (tag `greedy-foveal-explorer-v0-demo`); `demo-poster.png` sha256 `98ba555022ecf29b3d3370c2bbb22c82315fa10fcbe9b8958eba0a099f465f02`, `demo-final.png` sha256 `9afa30dbfb7e14e53a76815d82e273bd0a38e53b75ad4886a4ca9cb764186d65` |

## 1. Deliverables

The deliverables go in `visuals/playground-gaze-lattice-demo/`, in the shared checkout:

- `demo.mp4`: 1920 × 1080, H.264, 30 fps. It holds the intro, the replay of all 496 fixations, the freeze, an orbit
  of the final map and the final board.
- `demo-poster.png` and `demo-final.png`;
- `reference-{rgb,depth,instance}-panorama.png`, the REFERENCE panels, as in v0;
- `demo-manifest.json` and `demo-checks.json`;
- `overview.png`: the existing overview, regenerated with a Playground-1 title (report deviation D2). The original
  `visuals/playground-gaze-lattice/overview.png` cited by the accepted report is left untouched.

## 2. What changes (presentation code only)

1. **`tools/greedy_foveal/demo.py` gains a `--profile {v0,lattice}` option; the default is `v0`.** A profile sets
   the run, cache and output paths, the run-specific wording and `check`'s known answers. With `v0`, every path,
   string and known answer is the current one, so the frozen v0 demo is unchanged by construction. Section 4,
   check V1, proves it. The profile only changes how the replay is drawn and labelled.
2. **The `lattice` profile's wording:**
   - local saccade: "step to a nearby lattice gaze";
   - global saccade: "jump to the best lattice gaze" (the strip reads "NEXT: GLOBAL SACCADE → best lattice gaze");
   - stop: "100 % SEEN · STOP", with the stop rule "no lattice gaze adds unseen area";
   - the fixation count and the run name come from the run's records.

   *Revision before any workstation run.* The first draft's longer labels overran the strip's SEEN counter and the
   intro legend in Chat-sandbox renders, so they were shortened to fit v0's layout. The lattice legend for panel C
   sits in the panel, as a plated caption like panel D's, because the panel's title bar is full.
3. **The lattice gazes are drawn on replay panel C** (the observer's 360° state). Unvisited gazes are small
   rings, and visited ones are filled dots. They come from `explorer.lattice()`, which is the code that ran (`85fb962`).
4. **Stop-frame fix.** The lattice run ends with `next = {"kind": "none"}` rather than `null`. Both forms now give
   the stop label. The unchanged code would have labelled the last frame "NEXT: LOCAL SACCADE ()".
5. **Poster fixation.** v0 uses #179, chosen for legibility. The lattice default is the lattice fixation whose gaze
   is nearest v0 #179's gaze, read from the v0 run's `trajectory.json`, so the poster shows the same view.
   `--poster-fix N` may override it after inspection. The manifest records the choice and its reason.
6. **`--out DIR`** redirects the outputs, and is used by check V1.
7. **`tools/greedy_foveal/visuals.py`** gains an optional `--title`. The default title is unchanged, so `run.py
   visualize` is unaffected.

## 3. What deliberately does not change

- `explorer.py`, `run.py`, `render_server.py`, `check_lattice.py`;
- the run products of `previews/playground-gaze-lattice/`, which every stage verifies against `freeze.json`
  before reading;
- the truth-domain firewall: the DERIVED panels never open the Breadth-1 reference, which enters only the panels
  labelled REFERENCE (stage audit, as in v0);
- the frozen v0 demo and the files cited by the accepted Playground-1 report.

## 4. Fail-capable checks

| # | check | must |
|---|---|---|
| L1 | `demo.py check --profile lattice` (see below) | PASS |
| V1 | `demo.py build --profile v0 --out $SCRATCH/v0-rebuild`: `demo-poster.png` and `demo-final.png` sha256 equal to the frozen v0 record above | equal |
| N1 | `demo.py check --profile lattice --out visuals/greedy-foveal-explorer-v0-demo`: the lattice known answers against the v0 outputs | FAIL |

L1 requires:

- the replay is in exact fixation order 1 … 496;
- the MP4 metadata gives SEEN `100.00 %` and DEPTH `99.31 %`, equal to the run;
- the final map is the frozen one;
- the firewall holds: no reference file opens in the derived stage, and reference files open only where labelled;
- the headline equals `evaluation.json`: 98.82 % solid angle, 98.94 % cells, 16,702,245 surfels, 496 fixations;
- `demo.mp4` is H.264, 1920 × 1080 at 30 fps, with the manifest's frame count.

If V1 differs, stop. Report whether the difference is environmental (Pillow or fonts) by building v0 a second time,
and never write into `visuals/greedy-foveal-explorer-v0-demo/`.

## 5. Commands and cost classes

These run from an isolated worktree at the branch head this contract's handoff names. `SCRATCH` is a scratch
directory outside the repository.

| # | command | cost class |
|---|---|---|
| C1 | `.venv/bin/python tools/repository/check_repository_layout.py` | Batch |
| C2 | `.venv/bin/python tools/greedy_foveal/demo.py build --profile v0 --out $SCRATCH/v0-rebuild`, then V1 | Batch (about 1.5 min; the v0 eye cache exists) |
| C3 | `.venv/bin/python tools/greedy_foveal/demo.py rerender --profile lattice` | about 6–7 min (ESTIMATED from v0's 7 min for 542 fixations). Above Batch, well below Overnight. Authorized by Luiz as this step's render. |
| C4 | `.venv/bin/python tools/greedy_foveal/demo.py build --profile lattice` | Batch (about 1.5 min) |
| C5 | `.venv/bin/python tools/greedy_foveal/demo.py check --profile lattice` (L1) | Interactive |
| C6 | `.venv/bin/python tools/greedy_foveal/demo.py check --profile lattice --out /home/lvelho/rd/f3d-vision/visuals/greedy-foveal-explorer-v0-demo` (N1, must FAIL) | Interactive |
| C7 | `.venv/bin/python tools/greedy_foveal/visuals.py --run $RUNS/playground-gaze-lattice --vis /home/lvelho/rd/f3d-vision/visuals/playground-gaze-lattice-demo --title "Playground-1 gaze lattice — FIXATE → RECONSTRUCT → SACCADE (Classroom, fixed head H0)" --mark-fix 472 --mark-name "99 % SEEN" --mark-final` | Interactive |

`RUNS=/home/lvelho/rd/f3d-vision/previews`. The lattice profile's paths are absolute, under the shared checkout.

## 6. Acceptance

- L1 PASS, V1 equal, N1 FAIL, and C1 at 0 failures;
- Luiz's qualitative review of `demo.mp4`, `demo-poster.png`, `demo-final.png` and `overview.png`. This is a
  presentation package, so its acceptance is a viewing decision.

## 7. Stop conditions and permitted fixes

Claude Code stops and reports when any of these happen:

- a `freeze.json` mismatch;
- a firewall violation;
- a V1 difference;
- an L1 failure that is not a presentation defect.

**Permitted fixes.** Only presentation defects in `demo.py` or `visuals.py`, for example layout, label overlap or
legibility. A fix must keep the v0 profile unchanged, with V1 rerun after it, and must not touch any run product
or explorer code. The poster fixation may be overridden as in section 2, item 5.

## 8. Results to record

Claude Code commits `docs/playground/gaze-lattice-visuals-report.md`. It records:

- the branch, the commit and the commands run;
- the L1, V1, N1 and C1 lines, verbatim;
- the path and sha256 of each deliverable;
- the video's frames, duration and segments;
- the poster fixation and why it was chosen;
- every fix, and every deviation from this contract.
