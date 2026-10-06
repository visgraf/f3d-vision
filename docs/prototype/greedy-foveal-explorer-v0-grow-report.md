# Greedy Foveal Explorer v0 — "grow" run report

**Prototype run; not a scientific milestone.** This is the same v0 explorer with one change: the safety cap went from
200 to **450** fixations. All numbers are **MEASURED** from the run named here unless a line says **ESTIMATED**.
v0 report: `docs/prototype/greedy-foveal-explorer-v0-report.md`.

## Provenance

- Branch `prototype/greedy-foveal-explorer-v0`. HEAD `c611c637351dd6c796f95d902a9c0049488eeb17` was verified, and the run
  recorded it with a clean tracked tree.
- Between `a437df0` (the v0 implementation) and `c611c63`, only the v0 report and a drawing helper in `visuals.py`
  changed. `explorer.py`, `run.py` and `render_server.py` are byte-identical.
- **Zero code changes to the explorer.** No engineering fix was needed: memory, file sizes and counters were fine at
  16.3 M surfels.
- Presentation-only change after the run, committed with this report: `visuals.py` gained `--mark-fix`
  (the dashed "v0 stopped here" line), coarser ticks above 250 fixations, and a shorter wall-time line.
- `main`, NS1e and the v0 run directory are untouched.

Commands:

    .venv/bin/python tools/greedy_foveal/run.py explore  --run previews/greedy-foveal-explorer-v0-grow --max-fix 450
    .venv/bin/python tools/greedy_foveal/run.py evaluate --run previews/greedy-foveal-explorer-v0-grow
    .venv/bin/python tools/greedy_foveal/run.py checks   --run previews/greedy-foveal-explorer-v0-grow
    .venv/bin/python tools/greedy_foveal/visuals.py --run previews/greedy-foveal-explorer-v0-grow \
        --vis visuals/greedy-foveal-explorer-v0-grow --mark-fix 200

## Result

| quantity | at fixation 200 | final (450) |
|---|---|---|
| angular SEEN | 56.06 % | **96.74 %** of 4π |
| angular DEPTH | 55.55 % | **95.96 %** |
| all-geometry 12-mm coverage (Breadth-1, Position ≠ 0) | 52.96 % cells / 58.39 % sr | **97.24 % cells / 96.89 % sr** (248,688 / 255,758) |
| authored (Object Index > 0) | 53.58 % / 59.84 % sr | **97.23 % / 96.75 % sr** (216,112 / 222,267) |
| Object Index 0 only | 48.85 % / 50.61 % sr | 97.27 % / 97.62 % sr |
| saccades | 195 local / 4 global | **322 local / 127 global** |
| surfels | 9,779,195 | **16,263,451** |
| wall time | 219 s (the v0 run) | **579 s** |

- **Stop reason: the 450-fixation cap.** The 99 % SEEN stop was not reached, and the explorer never ran out of
  candidates.
- **Fixations 1–200 reproduce v0 exactly.** Gazes, decisions, fusion counts and the SEEN history are identical.
  Per-fixation XYZ, oracle ids and errors are bitwise equal, and the map size at 200 equals v0's final map. Only the
  display RGB differs (|Δ| ≤ 0.03), which is run-to-run Cycles/OPTIX colour noise and never enters control. So the
  post-hoc numbers at fixation 200 are v0's evaluation of a geometrically identical map.
- Evaluation details: the distance to the nearest surfel over covered cells has median 0.73 mm. The triangulation
  error against Position (diagnostic only) has a median of 0.046 mm over fixations. The worst point was 47 mm, at
  fixation 386 (−89.5°, −2.5°), 2.6° from the −X baseline; that fixation's median was 0.20 mm.
- **All minimal checks pass:**
  - fixed H0;
  - finite XYZ;
  - no duplicate fixation (minimum pair 3.75°);
  - S_seen monotone;
  - map reload;
  - Breadth-1 opened only after the verified freeze (control opened 3,169 files, none under Breadth-1; `freeze.json` sha256 `e2ff97b9…`);
  - policy determinism (449 saved states re-decided identically);
  - the fusion rule bitwise equal to the accepted FSG3 rule;
  - `git diff --check` clean.

## Global saccades after fixation 200

There were **123** global saccades after fixation 200 (4 before it).

| fixations | globals |
|---|---|
| 201–300 | 9 |
| 301–350 | 16 |
| 351–400 | 48 |
| 401–450 | 50 |

From fixation 363 on, every move was global.

- **Early, into large regions.** The first targets after 200 were:
  - #205 (−45.5°, −50.5°), in a 1.85 sr region: the never-visited area left of the start;
  - #219 (+46.5°, +49.5°);
  - #236 (+68.5°, +34.5°);
  - #244 (−79.5°, −18.5°);
  - #260 (+35.5°, +4.5°);
  - #272 (−16.5°, −2.5°), which filled the hole beside the start;
  - #276 (−129.5°, −20.5°);
  - #286 (−171.5°, +24.5°);
  - #298 (+118.5°, +47.5°).
- **Late, into tiny holes.** The size of the unseen region chosen fell monotonically: 1.85 sr at #205, 0.1 sr by #335,
  0.01 sr by #392, 0.004 sr at #450.
- The late targets are spread over the whole sphere, all pitches and all yaws (the numbered dashed arcs in the
  overview, A). Every target is listed in `trajectory.json`.

## Does the unseen region keep shrinking, or does the explorer get trapped?

**It keeps shrinking. It is not trapped, but its efficiency drops sharply as it nears full coverage.**

| fixation | 25 | 100 | 200 | 250 | 300 | 350 | 375 | 400 | 425 | 449 |
|---|---|---|---|---|---|---|---|---|---|---|
| UNSEEN % | 92.6 | 71.5 | 43.9 | 31.4 | 20.4 | 11.0 | 7.8 | 5.8 | 4.3 | 3.3 |
| unseen components | 1 | 36 | 99 | 148 | 207 | 311 | 340 | 335 | 318 | 291 |
| largest component (sr) | 11.6 | 8.26 | 1.85 | 1.08 | 0.32 | 0.043 | 0.015 | 0.009 | 0.006 | 0.004 |

Mean SEEN gain per fixation:

| fixations | gain |
|---|---|
| 1–100 | 0.285 % |
| 101–200 | 0.276 % |
| 201–300 | 0.236 % |
| 301–400 | 0.146 % |
| 401–450 | 0.050 % |

No fixation gained zero; the minimum was 0.030 %.

- **Where the unseen territory stands at the end.** 289 holes remain, 3.26 % of the sphere in total, and every one is
  under 0.01 sr (≤ 0.004 sr, about 3.6° × 3.6° or less). There is **no large structured hole left**. The holes form a
  near-regular lattice of corner gaps between overlapping 12° square footprints (overview, B).
- **Seen without depth (0.78 %).** These cells are the windows at yaw +60…+130°, pitch 0…+30°, where Breadth-1
  also has no first hit.
- **Why it slows down.** Once only corner gaps remain, no local neighbour reaches GAIN_MIN = 0.25. So every move becomes
  a global jump to the largest remaining gap, one gap per fixation. A 12° fixation covers 0.044 sr but now gains only
  about 0.004–0.006 sr. The unseen component count has been falling since about fixation 375 (from 340 to 291).
- **Projection to 99 % SEEN (ESTIMATED).** About 0.29 sr (2.3 points) must still be cleared, in holes of at most
  0.004 sr each. That is at least about 72 more fixations, and plausibly about 100 at the current rate.
- **Post-hoc coverage tracks angular coverage.** 96.89 % of the first-hit solid angle lies within 12 mm of the map.
  Panel F shows the remaining 3-D gaps are mostly floor and wall regions occluded by chairs and desks from the single
  fixed head; looking more from H0 cannot reach those.

**Outcome B, close to A.** Left to run, the dumb greedy explorer heads toward a complete 360° reconstruction:
96.7 % SEEN and 96.9 % first-hit solid angle within 12 mm in 450 fixations. It leaves no large structured hole, only a
fine lattice of corner gaps that it is still clearing, one global jump each.

## Runtime

| | 1–200 | 201–450 |
|---|---|---|
| wall per fixation, mean | 1.09 s | 1.44 s |
| wall per fixation, max | 1.88 s | 3.74 s |
| fusion, mean / max | 0.21 / 0.98 s | 0.56 / 2.90 s |

Totals: render 344 s, fusion 183 s, correspondence 15 s, geometry 10 s, policy 3 s; evaluation 25 s. Fusion grows with
the map size because the hash box scans the whole map each time. The run slowed but nothing became pathological.

## Output files

Run: `/home/lvelho/rd/f3d-vision/previews/greedy-foveal-explorer-v0-grow/` (2.0 GB)

- `trajectory.json`
- `final-map.npz` (976 MB)
- `final-map.ply` and `final-map-oracle-segmentation.ply` (ORACLE / VISUALIZATION ONLY; 244 MB each)
- `coverage.npz`, `freeze.json`, `evaluation.json` / `.npz`, `checks.json`
- `fixations/`, `policy/`

Visual: `/home/lvelho/rd/f3d-vision/visuals/greedy-foveal-explorer-v0-grow/overview.png`. Panel C marks where v0
stopped (#200, SEEN 56.1 %). Global saccades are drawn dashed.

    GREEDY FOVEAL EXPLORER V0 (GROW, 450) — PROTOTYPE RUN COMPLETE
    REVIEW PENDING
