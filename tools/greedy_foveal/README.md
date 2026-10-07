# Greedy Foveal Explorer — official baseline

## What is this?

A small **active-foveal playground**. A fixed binocular head sits in a static synthetic scene (Blender Classroom).
Its eyes explore the scene one fixation at a time:

    FIXATE -> RECONSTRUCT EVERYTHING LOCALLY -> UPDATE GLOBAL H0 MAP + CYCLOPEAN COVERAGE
           -> LOCAL OR GLOBAL SACCADE -> REPEAT

At each fixation the explorer renders a stereo pair with a 12° fovea and reconstructs every foveal point it can match
between the eyes. It fuses those points into one persistent 3-D surfel map and marks the viewed part of a 1° sphere as
seen. Then it picks the next gaze. That is a **local** saccade to a neighbouring view when the fovea's edge still shows
geometry and the neighbour is unexplored; otherwise it is a **global** jump into the largest unexplored region.

The code is the accepted Greedy Foveal Explorer v0, promoted unchanged in behavior (tags
`greedy-foveal-explorer-v0-impl` and `greedy-foveal-explorer-v0-demo`).

## What does it demonstrate?

On the frozen baseline run (fixed head, PERFECT / ORACLE correspondence, 64 spp), the explorer stops by itself at
**fixation 542** with **99.00 %** of the sphere seen. Post hoc, **98.32 %** of the first-hit 360° scene (solid angle) is
reconstructed within 12 mm. It does this with no object scheduler and no controller state machine. These numbers are
MEASURED; see the closure record [`greedy-foveal-explorer-v0-closure.md`](../../docs/prototype/greedy-foveal-explorer-v0-closure.md).

## The five source files

| file | interpreter | role |
|---|---|---|
| [`explorer.py`](explorer.py) | host | the core: sphere grid, one fixation's reconstruction, the global surfel map, coverage, the greedy policy |
| [`run.py`](run.py) | host | the driver: `explore` (control loop, freeze), `evaluate` (post-hoc), `checks`, `visualize` |
| [`render_server.py`](render_server.py) | Blender | a persistent render server: Classroom loaded once, only the eye cameras move |
| [`visuals.py`](visuals.py) | host | the one-page overview figure, plus the display colours used for the PLY exports |
| [`demo.py`](demo.py) | host | the presentation video: an offline replay of the frozen grow600 run |

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
        --baseline $RUNS/greedy-foveal-explorer-v0-grow600 --prefix

Fixations 1–75 must equal the first 75 fixations of the frozen run, bitwise (fixation 69 is the first global jump).
`explore` refuses an existing run directory.

## Full baseline (about 12 min)

    .venv/bin/python tools/greedy_foveal/run.py explore  --run $RUNS/my-baseline --max-fix 600 --spp 64

Expected: `stop: seen >= 99 % of 4 pi` at fixation 542; 322 local and 219 global saccades.

## Evaluate (post hoc, about 30 s)

    .venv/bin/python tools/greedy_foveal/run.py evaluate --run $RUNS/my-baseline
    .venv/bin/python tools/greedy_foveal/run.py checks   --run $RUNS/my-baseline
    .venv/bin/python tools/greedy_foveal/check_equivalence.py run --run $RUNS/my-baseline \
        --baseline $RUNS/greedy-foveal-explorer-v0-grow600 --known-answer
    .venv/bin/python tools/greedy_foveal/run.py visualize --run $RUNS/my-baseline --vis visuals/my-baseline

`evaluate` refuses to run unless the control products still match `freeze.json`. Only after that check does it open
the Breadth-1 reference.

## Demo

    .venv/bin/python tools/greedy_foveal/demo.py rerender   # once: display RGB of every fixation (about 7 min)
    .venv/bin/python tools/greedy_foveal/demo.py build      # video + stills (about 1.5 min)
    .venv/bin/python tools/greedy_foveal/demo.py check

The demo replays the frozen grow600 run; its paths are fixed in `demo.py`. Outputs go to
`visuals/greedy-foveal-explorer-v0-demo/`.

## Architecture

[`docs/architecture/greedy-foveal-playground.md`](../../docs/architecture/greedy-foveal-playground.md): the
coordinate systems, data products, dependency map, truth boundaries and extension points.

## Starting a new experiment

Branch from the official baseline and **change one component**. Each extension point (renderer, matcher, map, fusion,
coverage, local or global policy, stop rule, …) is listed in the architecture document, section 16, with its current
code location and interface. Run the same commands into a new run directory. Compare your result with
`greedy-foveal-explorer-v0-grow600` or the official reproduction, using `evaluate` and `visualize`.
`check_equivalence.py` is for refactors that claim **no** behavior change; a real experiment is expected to diverge.
