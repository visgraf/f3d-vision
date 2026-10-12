# Greedy Foveal Explorer — official baseline

## What is this?

A small **active-foveal playground**. A fixed binocular head sits in a static synthetic scene (Blender Classroom).
Its eyes explore the scene one fixation at a time:

    FIXATE -> RECONSTRUCT EVERYTHING LOCALLY -> UPDATE GLOBAL H0 MAP + CYCLOPEAN COVERAGE
           -> LOCAL OR GLOBAL SACCADE -> REPEAT

At each fixation the explorer renders a stereo pair with a 12° fovea and reconstructs every foveal point it can match
between the eyes. It fuses those points into one persistent 3-D surfel map and marks the viewed part of a 1° sphere as
seen. Then it picks the next gaze from a fixed **gaze lattice** of 356 views on 17 rings about the eye baseline, whose
12° footprints cover every 1° cell. That is a **local** saccade to a neighbouring lattice view that still adds unseen
area, preferring views where the fovea's edge shows geometry; otherwise it is a **global** jump to the unvisited
lattice view that adds the most. It stops when no lattice view adds anything.

The code is the accepted Playground-2 sparse covering lattice, promoted unchanged in behavior (tag
`playground-2-sparse-lattice`; Engineering-2,
[contract](../../docs/engineering/sparse-lattice-baseline-contract.md)). The previous official baseline, Greedy
Foveal Explorer v0, is tag `greedy-foveal-playground-baseline`.

## What does it demonstrate?

On the frozen baseline run (fixed head, PERFECT / ORACLE correspondence, 64 spp), the explorer stops by itself at
**fixation 356** with **100 %** of the sphere seen and no hole left. Post hoc, **98.82 %** of the first-hit 360° scene
(solid angle) is reconstructed within 12 mm. It does this with no object scheduler and no controller state machine.
These numbers are MEASURED; see the [Playground-2 report](../../docs/playground/sparse-lattice-report.md).

## The source files

| file | interpreter | role |
|---|---|---|
| [`explorer.py`](explorer.py) | host | the core: sphere grid, one fixation's reconstruction, the global surfel map, coverage, the greedy policy |
| [`run.py`](run.py) | host | the driver: `explore` (control loop, freeze), `evaluate` (post-hoc), `checks`, `visualize` |
| [`render_server.py`](render_server.py) | Blender | a persistent render server: Classroom loaded once, only the eye cameras move |
| [`visuals.py`](visuals.py) | host | the one-page overview figure, plus the display colours used for the PLY exports |
| [`demo.py`](demo.py) | host | the presentation video: an offline replay of a frozen run (`--profile v0`, the default, or `lattice`, the Playground-1 run) |
| [`check_lattice.py`](check_lattice.py) | host | fail-capable checks of the gaze lattice and a coverage-only replay of the policy |

[`check_equivalence.py`](check_equivalence.py) proves that the code and a run reproduce the frozen baseline.

## Prerequisites

- Blender 5.2.1 on `PATH` (`blender`), with an OPTIX GPU; the repository `.venv`.
- `scenes/classroom/classroom_eye.blend` (gitignored; in a new worktree, symlink `scenes/classroom/*` from the shared
  checkout).
- Two accepted reference files in the shared checkout's `previews/`. `explore` needs the AB1a head-pose calibration;
  `evaluate` needs the Breadth-1 canonical EXR. Both are hash-checked.

Commands run from the repository root. In the examples below, `RUNS=/home/lvelho/rd/f3d-vision/previews`.

## Smoke test (about 1.5 min)

    .venv/bin/python tools/greedy_foveal/run.py explore --run $RUNS/my-smoke --max-fix 75
    .venv/bin/python tools/greedy_foveal/run.py checks  --run $RUNS/my-smoke
    .venv/bin/python tools/greedy_foveal/check_equivalence.py run --run $RUNS/my-smoke \
        --baseline $RUNS/playground-sparse-lattice --prefix

Fixations 1–75 must equal the first 75 fixations of the frozen run, bitwise (fixations 2–75 are local saccades; the
first global jump is at fixation 168). `explore` refuses an existing run directory. Without a renderer,
`.venv/bin/python tools/greedy_foveal/check_lattice.py` checks the lattice and replays the policy on coverage alone.

## Full baseline (about 7 min)

    .venv/bin/python tools/greedy_foveal/run.py explore  --run $RUNS/my-baseline --max-fix 600 --spp 64

Expected: `stop: no valid unseen fixation` at fixation 356; 315 local and 40 global saccades.

## Evaluate (post hoc, about 30 s)

    .venv/bin/python tools/greedy_foveal/run.py evaluate --run $RUNS/my-baseline
    .venv/bin/python tools/greedy_foveal/run.py checks   --run $RUNS/my-baseline
    .venv/bin/python tools/greedy_foveal/check_equivalence.py run --run $RUNS/my-baseline \
        --baseline $RUNS/playground-sparse-lattice --known-answer
    .venv/bin/python tools/greedy_foveal/run.py visualize --run $RUNS/my-baseline --vis visuals/my-baseline

`evaluate` refuses to run unless the control products still match `freeze.json`. Only after that check does it open
the Breadth-1 reference.

## Demo

    .venv/bin/python tools/greedy_foveal/demo.py rerender   # once: display RGB of every fixation (about 7 min)
    .venv/bin/python tools/greedy_foveal/demo.py build      # video + stills (about 1.5 min)
    .venv/bin/python tools/greedy_foveal/demo.py check

By default the demo replays the frozen v0 grow600 run into `visuals/greedy-foveal-explorer-v0-demo/`; `--profile
lattice` replays the Playground-1 run. There is no profile for the new official run yet.

## Architecture

[`docs/architecture/greedy-foveal-playground.md`](../../docs/architecture/greedy-foveal-playground.md): the
coordinate systems, data products, dependency map, truth boundaries and extension points.

## Starting a new experiment

Branch from the official baseline and **change one component**. Each extension point (renderer, matcher, map, fusion,
coverage, local or global policy, stop rule, …) is listed in the architecture document, section 16, with its current
code location and interface. Run the same commands into a new run directory. Compare your result with
`playground-sparse-lattice` or the official reproduction, using `evaluate` and `visualize`.
`check_equivalence.py` is for refactors that claim **no** behavior change; a real experiment is expected to diverge.
