# Greedy Foveal Explorer v0 — "grow600" run report

**Prototype run; not a scientific milestone.** This is the same v0 explorer with one change: the cap went from 450 to
**600** fixations. The 99 % SEEN stop was kept. All numbers are **MEASURED** from the run named here.
Earlier reports: `greedy-foveal-explorer-v0-report.md` (200 cap) and `greedy-foveal-explorer-v0-grow-report.md` (450 cap).

## Provenance

- Branch `prototype/greedy-foveal-explorer-v0`. HEAD `4d823ad6679534406aff4ce8604d209a81384563` was verified, and the
  run recorded it with a clean tracked tree.
- `explorer.py`, `run.py` and `render_server.py` have **no diff** against `a437df0`. The explorer code was not changed.
- **No resume.** `explore` always starts at fixation 1 and refuses an existing run directory, and no resume machinery
  was added. The run started cleanly from fixation 1.
- **Fixations 1–450 reproduce the 450-cap run exactly.** Decisions, gazes, fusion counts, per-fixation XYZ, oracle ids,
  errors and the SEEN history are bitwise equal. So that run's post-hoc evaluation is this run's value at #450.
- Presentation-only change, committed with this report: `visuals.py --mark-fix` now takes several values, plus
  `--mark-name` and `--mark-final`. The old single-value call still renders as before.

Commands:

    .venv/bin/python tools/greedy_foveal/run.py explore  --run previews/greedy-foveal-explorer-v0-grow600 --max-fix 600
    .venv/bin/python tools/greedy_foveal/run.py evaluate --run previews/greedy-foveal-explorer-v0-grow600
    .venv/bin/python tools/greedy_foveal/run.py checks   --run previews/greedy-foveal-explorer-v0-grow600
    .venv/bin/python tools/greedy_foveal/visuals.py --run previews/greedy-foveal-explorer-v0-grow600 \
        --vis visuals/greedy-foveal-explorer-v0-grow600 --mark-fix 200 450 --mark-name "v0 stop" "450-run stop" --mark-final

## Result

| | fixation 200 | fixation 450 | **final: fixation 542** |
|---|---|---|---|
| SEEN | 56.06 % | 96.74 % | **99.00 %** |
| DEPTH | 55.55 % | 95.96 % | **98.28 %** |
| all-geometry 12-mm, cells | 52.96 % | 97.24 % (248,688) | **98.52 % (251,966 / 255,758)** |
| all-geometry 12-mm, solid angle | 58.39 % | 96.89 % | **98.32 %** |
| authored (Object Index > 0), cells / solid angle | 53.58 % / 59.84 % | 97.23 % / 96.75 % | **98.52 % / 98.25 %** (218,988 / 222,267) |
| local / global saccades | 195 / 4 | 322 / 127 | **322 / 219** |
| surfels | 9,779,195 | 16,263,451 | **16,517,811** |
| wall time | 219 s (the v0 run) | 579 s (the 450 run) | **729 s** |

- **Stop reason:** SEEN ≥ 99 % of 4π, reached at **fixation 542**. The 600 cap was not used.
- After fixation 450, all 92 moves were global jumps, each into one small hole. The mean SEEN gain was 0.025 % per
  fixation (minimum 0.015 %).
- Mean wall time per fixation was 1.65 s for fixations 451–542. Fusion averaged 0.78 s per fixation, with a maximum of
  2.9 s.
- **What remains.** 1.0 % of the sphere is UNSEEN, in 184 holes each ≤ 0.0018 sr. Another 0.72 % is SEEN without
  depth: the windows, which have no first hit in Breadth-1 either.
- Evaluation details: the distance to the nearest surfel over covered cells has median 0.73 mm. Object Index 0
  coverage is 98.69 % of solid angle. The vectorized cross-check agreed with the accepted `_covered` on every cell.
- **All minimal checks pass:**
  - fixed H0;
  - finite XYZ;
  - no duplicate fixation (minimum pair 3.75°);
  - S_seen monotone;
  - map reload;
  - Breadth-1 opened only after the verified freeze (control opened 3,813 files, none under Breadth-1; `freeze.json` sha256 `a4283ab7…`);
  - policy determinism (541 saved states re-decided identically);
  - the fusion rule bitwise equal to the accepted FSG3 rule;
  - `git diff --check` clean.

## Answers

- **Did it reach 99 % SEEN?** **Yes.**
- **At which fixation?** **#542.** That is 92 fixations after the 450 cap and 342 after the original 200 cap.
- **What reconstruction coverage did that produce?** **98.32 % of the Breadth-1 first-hit solid angle within 12 mm**
  (98.52 % of cells). Authored objects alone: 98.25 % of solid angle.
- **Does the unchanged dumb explorer finish the job if we let it keep walking?** **Yes, within this setup:** fixed head,
  static Classroom, PERFECT correspondence, 12° fovea. It never stalled. The cost is a long tail of single-hole global
  jumps:

  | fixations | SEEN covered |
  |---|---|
  | first 200 | 56 % |
  | next 250 (to 450) | to 96.7 % |
  | last 92 (to 542) | the final 2.3 points |

The uncovered 1.7 % of the reference solid angle is two things (overview, E):

- the remaining UNSEEN holes (1.0 % of the sphere);
- thin slivers at depth edges, where the reference ray from the head origin lands on a surface that the binocular
  correspondence did not reach.

The windows have no first hit, so they are not in the reference at all. The white areas in the top view (overview, F)
are occlusion shadows behind chairs and desks; the first-hit reference does not contain them either.

## Output files

- Run: `/home/lvelho/rd/f3d-vision/previews/greedy-foveal-explorer-v0-grow600/` (2.2 GB; same layout as the earlier runs)
- Visual: `/home/lvelho/rd/f3d-vision/visuals/greedy-foveal-explorer-v0-grow600/overview.png`. Panel C has markers at
  #200, #450 and the final #542; global saccades are drawn dashed.

    GREEDY FOVEAL EXPLORER V0 (GROW600) — REACHED 99 % SEEN AT FIXATION 542
    REVIEW PENDING
