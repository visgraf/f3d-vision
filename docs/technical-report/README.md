# Active Foveal 3-D Vision — technical report

**Status: ACCEPTED** by Luiz and Chat (October 2026). Tag `active-foveal-3d-vision-tech-report`.

    ACTIVE_FOVEAL_3D_VISION_TECH_REPORT_ACCEPTED

Accepted PDF: `active-foveal-3d-vision.pdf`, sha256 `43f165247a18b50ce3b7f46c2cebf179c5f31952a0c646791232e2d4775669b5` (20 A4 pages). The review draft was `6a59d23`; acceptance
changed only the status lines, the PDF metadata and two cosmetic layout details. No content changed.

*Active Foveal 3-D Vision: A Fixate–Reconstruct–Saccade Playground for 360-Degree Scene Reconstruction* documents the
accepted official Greedy Foveal Playground baseline (tag `greedy-foveal-playground-baseline`). It presents the system
as a controlled proof of concept and reproducible computational baseline, from the present-day viewpoint. It is not a
history of the project.

| file | what |
|---|---|
| [`active-foveal-3d-vision.tex`](active-foveal-3d-vision.tex) | the canonical source (LaTeX, 11 pt, A4) |
| [`references.bib`](references.bib) | the four historical references |
| [`active-foveal-3d-vision.pdf`](active-foveal-3d-vision.pdf) | the compiled report |
| [`make_figures.py`](make_figures.py) | regenerates the raster figures and growth-curve data in `figures/` |
| `figures/` | report figures, the growth-curve CSVs and `figure-sources.json` (provenance) |

The canonical technical description remains
[`docs/architecture/greedy-foveal-playground.md`](../architecture/greedy-foveal-playground.md). The canonical measured
evidence is [`docs/engineering/greedy-foveal-playground-baseline-report.md`](../engineering/greedy-foveal-playground-baseline-report.md).
This report presents those sources and does not replace them.

## Compile

No experiment, render or replay is needed. From this directory:

    mkdir -p build
    pdflatex -output-directory=build active-foveal-3d-vision.tex
    bibtex   build/active-foveal-3d-vision
    pdflatex -output-directory=build active-foveal-3d-vision.tex
    pdflatex -output-directory=build active-foveal-3d-vision.tex
    pdflatex -output-directory=build active-foveal-3d-vision.tex    # floats settle on the third pass after bibtex
    cp build/active-foveal-3d-vision.pdf .

Where `latexmk` is installed, `latexmk -pdf -outdir=build active-foveal-3d-vision.tex` does the same. `build/` is
gitignored.

The build uses only standard TeX Live packages: geometry, lmodern, microtype, amsmath, graphicx, booktabs, tabularx,
xcolor, enumitem, caption, subcaption, TikZ / pgfplots, natbib, fancyhdr and hyperref. Figures 1 and 7 (the
architecture diagrams) and Figure 5 (the growth curve) are drawn by LaTeX itself.

## Where the figures come from

`make_figures.py` writes every raster figure and the Figure 5 data. It reads only existing products and renders
nothing:

- **The official Engineering-1 reproduction run**, `previews/greedy-foveal-official-baseline/`, in the workstation's
  shared checkout. The script reads the trajectory, the coverage history, the saved decision states, the #179 point
  patch and calibration, and the post-hoc evaluation. It verifies the run's freeze before reading anything.
- **The accepted frozen demo** (tag `greedy-foveal-explorer-v0-demo`):
  - the final and reference panoramas in `visuals/greedy-foveal-explorer-v0-demo/`;
  - the 3-D map view, cropped from `demo-final.png` (hash-checked against the closure record);
  - the #179 eye crops in `previews/greedy-foveal-explorer-v0-demo-cache/`.

It never opens the Breadth-1 reference EXR. `figures/figure-sources.json` records the sha256 of every input and
output, plus every derived number that the text quotes (points per fixation, fusion timings, exploration phases,
remaining holes, and so on).

To regenerate, from the repository root (about 2 s; presentation only):

    .venv/bin/python docs/technical-report/make_figures.py

## Measured source

All MEASURED numbers come from the official reproduction run (`freeze.json` sha256 `6bc9b190…`, made at `b77b1d9`).
That run is bitwise equivalent to the frozen grow600 run in every control-path product (23 / 23 equivalence checks).
Headline values: 542 fixations; 99.00 % SEEN; 98.28 % DEPTH; 322 local / 219 global saccades; 16,517,811 surfels;
98.32 % of the first-hit reference solid angle within 12 mm (98.52 % of cells); 733 s.
