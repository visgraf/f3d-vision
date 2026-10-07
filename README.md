# Foveal Stereo Vision — Active Foveal Playground

This repository is a playground for **active foveal 3-D vision**. A binocular observer reconstructs a scene by
repeatedly looking, measuring locally, remembering globally and deciding where to look next.

    FIXATE
        ↓
    RECONSTRUCT          everything the fovea can match, as metric 3-D points
        ↓
    UPDATE GLOBAL MEMORY one persistent 3-D map + a sphere of where it has looked
        ↓
    SACCADE              to a neighbouring view, or jump to an unexplored region
        ↓
    repeat

The official baseline, the **Greedy Foveal Explorer**, is intentionally simple. It is a reproducible starting point for
future experiments, not a finished vision system.

## Current baseline

This is a controlled synthetic proof of concept and engineering baseline. In the Blender Classroom scene, with a
fixed head and oracle stereo correspondence, the official reproduction gave the following (MEASURED,
[Engineering-1 report](docs/engineering/greedy-foveal-playground-baseline-report.md)):

| | |
|---|---|
| stop | after **542 fixations**: 99 % of the sphere seen |
| 360° sphere SEEN | **99.00 %** |
| with reconstructed DEPTH | **98.28 %** |
| first-hit solid angle reconstructed within 12 mm (post hoc) | **98.32 %** |
| saccades | **322 local / 219 global** |
| persistent map | **16,517,811 surfels** |

The official reproduction is **bitwise equivalent** to the frozen Greedy v0 control path: **23 / 23** equivalence
checks pass. Gazes, decisions, points, fusion, coverage, the final map and the evaluation are identical.

These numbers describe this one setting. They are not a general vision result.

## What the playground does

- a **fixed head** H0 with two eyes that rotate about their own centres;
- **binocular 12° foveal observations**, rendered by Blender (Cycles, 64 spp);
- **PERFECT / ORACLE correspondence**: the renderer's geometry decides which left and right pixels match;
- **spherical metric triangulation** of every matched foveal ray;
- **one persistent global H0 surfel map**, fused at 12 mm;
- a **1° cyclopean sphere** with each cell UNSEEN, SEEN or DEPTH;
- **greedy local saccades** to one of 8 neighbouring views, where the fovea's edge shows surface and the neighbour
  is unexplored;
- **global jumps** to the deepest point of the largest unexplored region;
- **post-hoc first-hit evaluation** against a full-sphere reference, opened only after the run is frozen.

There is no object scheduler and no Controller-01/02 state machine in the active baseline.

> **Important architectural fact.** The current gaze policy does **not** read the accumulated 3-D map. Gaze selection
> uses the cyclopean coverage sphere plus the current fixation's evidence. The global 3-D map is persistent
> reconstruction memory and output. This is intentional baseline behavior, and it is one of the clearest future
> extension points.

## Quick start

The full commands, prerequisites and expected outputs are in
[`tools/greedy_foveal/README.md`](tools/greedy_foveal/README.md). The minimal sequence, from the repository root:

    # smoke (75 fixations, about 1.5 min)
    .venv/bin/python tools/greedy_foveal/run.py explore  --run <run-dir> --max-fix 75

    # full baseline (about 12 min on an RTX 4090)
    .venv/bin/python tools/greedy_foveal/run.py explore  --run <run-dir> --max-fix 600 --spp 64
    .venv/bin/python tools/greedy_foveal/run.py evaluate --run <run-dir>
    .venv/bin/python tools/greedy_foveal/run.py checks   --run <run-dir>

It needs Blender 5.2.1 with an OPTIX GPU, the repository `.venv` and the gitignored Classroom scene. It also needs two
accepted, hash-checked reference files (the head-pose calibration and the post-hoc reference), which `run.py` currently
locates through a fixed project-workstation path. See the architecture document, §15.2.

## Code map

| file | role |
|---|---|
| [`tools/greedy_foveal/explorer.py`](tools/greedy_foveal/explorer.py) | geometry, coverage, the map, the greedy policy |
| [`tools/greedy_foveal/run.py`](tools/greedy_foveal/run.py) | the active loop, freeze, evaluation, checks |
| [`tools/greedy_foveal/render_server.py`](tools/greedy_foveal/render_server.py) | the persistent Blender observation service |
| [`tools/greedy_foveal/visuals.py`](tools/greedy_foveal/visuals.py) | the overview visualization |
| [`tools/greedy_foveal/demo.py`](tools/greedy_foveal/demo.py) | the offline presentation replay |
| [`tools/greedy_foveal/check_equivalence.py`](tools/greedy_foveal/check_equivalence.py) | the baseline equivalence checks |

The baseline reuses accepted project modules for sensor geometry, the oracle correspondence, triangulation, Blender
acquisition and evaluation. The architecture document maps each dependency.

## Architecture and playground extensions

**[`docs/architecture/greedy-foveal-playground.md`](docs/architecture/greedy-foveal-playground.md)** is the canonical
architecture reference. It covers the loop, the coordinate systems, the persistent state, the measurement service, the
map and fusion rule, coverage, the policy, the truth / oracle boundaries and the data products.

It also identifies the replaceable components, with each one's current implementation and interface:

- renderer; stereo matcher; local metric measurement;
- map representation; fusion; cyclopean coverage;
- local gaze policy; global gaze policy; stopping rule;
- segmentation / semantics; head motion; visualization.

The intended development style is to **change one component at a time and compare against the official baseline**.

## Demo

The accepted, frozen demo (tag `greedy-foveal-explorer-v0-demo`) is an offline replay of the baseline run. Its
products are:

- `demo.mp4` (1920 × 1080, 62.4 s);
- `demo-poster.png`;
- `demo-final.png`.

They are generated, workstation-local files (gitignored `visuals/greedy-foveal-explorer-v0-demo/`), so GitHub does
not host them. Their sha256 hashes are in the
[closure record](docs/prototype/greedy-foveal-explorer-v0-closure.md). `tools/greedy_foveal/demo.py` regenerates
them from the frozen run.

## Limitations

- synthetic, static Classroom scene; 64-spp rendering;
- fixed head; no moving head yet;
- PERFECT / ORACLE correspondence; no natural stereo yet;
- oracle object identity used only for declared visualization; no natural segmentation yet;
- first-hit evaluation: surfaces hidden from the head origin are not targets;
- a deliberately unsophisticated greedy trajectory, with a long tail of single global jumps;
- map and storage efficiency not optimized (about 1 GB map, 2.2 GB per run).

## Documentation

| document | what |
|---|---|
| [`docs/architecture/greedy-foveal-playground.md`](docs/architecture/greedy-foveal-playground.md) | the canonical architecture reference |
| [`tools/greedy_foveal/README.md`](tools/greedy_foveal/README.md) | quick start and commands |
| [`docs/engineering/greedy-foveal-playground-baseline-report.md`](docs/engineering/greedy-foveal-playground-baseline-report.md) | the official reproduction and equivalence evidence |
| [`docs/prototype/greedy-foveal-explorer-v0-closure.md`](docs/prototype/greedy-foveal-explorer-v0-closure.md) | the proof-of-concept closure and provenance |
| [`docs/repository/README-history.md`](docs/repository/README-history.md) | the historical, pre-playground README |
| [`docs/chat-handoff.md`](docs/chat-handoff.md) | the project's working state and AI-collaboration handoff (not user documentation) |

The working agreement for contributors and coding assistants is [`CLAUDE.md`](CLAUDE.md).

## Project history

The repository contains a substantial earlier research line on object-centric controllers, epistemic state, scene
partitioning and Controller-01/02. It also holds the natural-bootstrap and stereo studies that led to the playground.
That work is preserved as historical research evidence, with its contracts, reports and code under `docs/` and
`tools/`. It is not the current playground baseline.

The former repository README is preserved at
[`docs/repository/README-history.md`](docs/repository/README-history.md).
