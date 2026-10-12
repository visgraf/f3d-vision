# Chat Handoff

Where the project is now. A recovery index: the files it points to are authoritative.
Rewritten, not appended, at each accepted milestone. Earlier versions are in git;
the version before Governance-1 is kept in `docs/repository/chat-handoff-history.md`.

## Now

| Field             | Value |
|-------------------|-------|
| Accepted main     | `11bfbf6`, tag `governance-1`: Governance-1 accepted; then a docs-only follow-up record |
| Active branch     | `main` |
| Stage             | ENGINEERING / PRESENTATION, complete (Luiz, 2026-10-12). Luiz decides the next phase |
| Official baseline | `tools/greedy_foveal/` = the Playground-2 sparse covering lattice, tag `greedy-foveal-playground-baseline-2`; any change must keep `tools/greedy_foveal/check_equivalence.py` passing |

## Active next step

None authorized in this repository. Later playground experiments change one component
at a time against the official baseline, each explicitly authorized. No policy redesign
and no new research experiment is open. Outside it, ClaudeChat updates the N-Surface
technical note with Governance-1.

## Accepted results, newest first

The report holds the numbers; the line names the claim and where it lives.

- **Governance-1.** The working agreement is three layers: kernel `CLAUDE.md`, shell
  `docs/process/shell.md`, state in this file; `tools/process/lint.py` keeps them
  coherent; process records in `docs/process/records/`. Tag `governance-1`;
  `docs/process/governance-1-report.md`.
- **Official baseline's demo.** `demo.py --profile sparse` replays the frozen
  Playground-2 run. `docs/presentation/official-baseline-demo-report.md`.
- **Playground-3, the 2° cap lattice.** Accepted as a playground result, NOT promoted
  (346 vs 356 fixations). Tag `playground-3-cap-2deg`; `docs/playground/cap-2deg-report.md`.
- **Engineering-2.** The sparse covering lattice is the official baseline, reproduced
  bitwise (23 / 23 checks). Tag `greedy-foveal-playground-baseline-2`;
  `docs/engineering/sparse-lattice-baseline-report.md`.
- **Playground-2, the sparse covering lattice.** 356 fixations, 0 UNSEEN cells, 98.82 %
  within 12 mm. Tag `playground-2-sparse-lattice`; `docs/playground/sparse-lattice-report.md`.
- **Slide presentation** "Active Foveal 3-D Vision".
  `docs/presentation/active-foveal-3d-vision-slides.pdf`.
- **Playground-1, the gaze lattice, and its visualization package.** Not promoted. Tag
  `playground-1-gaze-lattice`; `docs/playground/gaze-lattice-report.md`,
  `docs/playground/gaze-lattice-visuals-report.md`.
- **Working agreement: ClaudeChat replaces ChatGPT in the specification and review
  station** (`55ba7ba`).
- **Technical report** "Active Foveal 3-D Vision". Tag
  `active-foveal-3d-vision-tech-report`; `docs/technical-report/active-foveal-3d-vision.pdf`.
- **Engineering-1.** The official Greedy Foveal Playground baseline (v0 behavior,
  23 / 23 checks). Tag `greedy-foveal-playground-baseline`;
  `docs/engineering/greedy-foveal-playground-baseline-report.md`;
  architecture `docs/architecture/greedy-foveal-playground.md`.
- **Greedy Foveal Explorer v0**, accepted and CLOSED: stops at fixation 542 with
  98.32 % within 12 mm. Tags `greedy-foveal-explorer-v0-impl`,
  `greedy-foveal-explorer-v0-demo`; `docs/prototype/greedy-foveal-explorer-v0-closure.md`.

Earlier stages, all accepted; details in each report and in the history file:

- Controller line: Controller-01 with audits 01A, 01B, 01C and its visual package,
  Stage Charter 1, Controller-02 (`docs/controller/`, `docs/methodology/`).
- North Star: NS1a, NS1b, NS1c2, NS1d (`docs/north-star/`).
- Natural Bootstrap NB1a–NB1c (`docs/natural-bootstrap/`); Active Bootstrap AB1a–AB1d3
  (`docs/active-bootstrap/`). After AB1d3 natural stereo is DEFERRED; the North Star
  uses PERFECT / ORACLE correspondence.
- Breadth-1 (`docs/classroom-oracle/`); Visual Language 1 and Policy 1
  (`docs/methodology/`).
- Conceptual Cores 1–14 (`docs/conceptual-core/`); Repository Stage Transition 1
  (`docs/repository/`).

## Not accepted, frozen, paused, deferred

- **NS1e.** NS1e is REVIEW PENDING, NOT ACCEPTED and NOT MERGED. Its branch is
  `north-star/ns1e-coherent-full-loop-m2-memory`. The branch
  `prototype/greedy-foveal-explorer-v0` descends from it and is never merged into
  `main`.
- **NS1c.** NS1c is REVIEWED, NOT ACCEPTED and NOT MERGED
  (`docs/north-star/ns1c-review-decision.md`); NS1c2 replaced it.
- **Frozen** unless Luiz reopens them: Controller-01, Controller-02, NB1c, Visual
  Language 1, Greedy v0.
- **Paused:** the Conceptual Core migration after Core 14. Do not start Core 15 or
  another cleanup automatically.
- **Deferred:** natural stereo, until the full Classroom demonstration.

## Decision-critical open items

1. Greedy playground: the map and storage cost (16.5 M surfels, 1 GB
   `final-map.npz`); the "PROTOTYPE" labels left in `tools/greedy_foveal/run.py` and
   `tools/greedy_foveal/visuals.py`; the absolute workstation paths in `run.py` and
   `demo.py`; the gaze policy does not read the 3-D map; `run.py visualize` has no
   `--title`.
2. Controller line (historical, off the critical path): its open questions,
   design gaps, deferred cleanups and the Repository Stage Transition 1 items are
   items 1–5 of "Decision-critical open items" in the history file.
3. Breadth-1 evaluation universe: how geometry rendered outside the 234-object
   catalog enters future evaluation. Intentionally open.
