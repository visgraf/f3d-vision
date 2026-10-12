# Active Foveal 3-D Vision — slide presentation

**Status: ACCEPTED** by Luiz on 2026-10-12.

    ACTIVE_FOVEAL_3D_VISION_SLIDES_ACCEPTED

The accepted deck is [`active-foveal-3d-vision-slides.pdf`](active-foveal-3d-vision-slides.pdf): 18 pages, 16:9,
sha256 `5c106a60cad9e59d9cc988658d5f0ff83461911ac3c9aea5826e34c0df07dc8c`.

## Provenance

- **Drafted by ClaudeChat** (2026-10-11) as a Claude Slides deck. The outline came from the Engineering-1 report,
  section 11 B ([`greedy-foveal-playground-baseline-report.md`](../engineering/greedy-foveal-playground-baseline-report.md)),
  with a Playground-1 section added.
- **Revised and exported by Luiz** in Keynote (2026-10-12). The PDF is that export.
- The source deck is not in the repository. This PDF is the durable record.

## Contents

| pages | section | numbers from |
|---|---|---|
| 1–4 | the idea, the observer, the loop | [technical report](../technical-report/README.md), sections 4–5 |
| 5–10 | one fixation, cyclopean memory, the Greedy Foveal Explorer v0 and its result | the technical report and its `figures/` (official baseline run) |
| 11–14 | Playground-1: the problem, the cause, the gaze lattice, the result | [`gaze-lattice-report.md`](../playground/gaze-lattice-report.md) |
| 15–16 | demo: posters and coverage panels of both replays | [`gaze-lattice-visuals-report.md`](../playground/gaze-lattice-visuals-report.md) |
| 17–18 | limits; next experiments | — |

Every number on the slides is MEASURED from the run named in the slide's footer.

There are two exceptions:

- page 12's 0.825 / 0.58 gains are the Chat-sandbox known answer K3 of `tools/greedy_foveal/check_lattice.py`;
- page 18's "about 290" is an area bound, not a measurement.

The figures are:

- the technical report's committed figures;
- a lattice map drawn from `explorer.lattice()` at tag `playground-1-gaze-lattice`;
- a SEEN-growth chart drawn from `../technical-report/figures/fig5-growth.csv`;
- the demo posters from `visuals/`.

The demo videos are not committed. They live in the workstation's `visuals/greedy-foveal-explorer-v0-demo/` and
`visuals/playground-gaze-lattice-demo/`.
