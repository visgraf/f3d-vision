# The official baseline's demo (the Playground-2 run): report

**Status: EXECUTED and ACCEPTED** by Luiz on 2026-10-12 (section 9). This is presentation only. Claude Code built and
checked the package on the workstation, under the contract below.

    OFFICIAL_BASELINE_DEMO_ACCEPTED

**Machine half (contract §6):**

- S1 PASS;
- L1 PASS;
- V1 equal;
- V2 equal;
- N1 FAIL, as required;
- N2 differ, as required;
- C1 clean.

They hold at the final head, after two permitted fixes (section 6).

Contract: [`official-baseline-demo-contract.md`](official-baseline-demo-contract.md).
Run replayed: [Playground-2 report](../playground/sparse-lattice-report.md); official baseline:
[Engineering-2 report](../engineering/sparse-lattice-baseline-report.md).

All numbers are **MEASURED** from the commands named with them.

## 1. Provenance

| item | value |
|---|---|
| step 0: tag | `playground-3-cap-2deg` → `c217b003927a9fde6dbc2b43ec718912956bbfb5` (annotated tag object `798f9e8fbee87d988d89069fedb85b0cb2c0a486`), created with Luiz's message and pushed. It was absent from origin. `c217b00` is the head of `playground/cap-2deg` and differs from the Playground-3 run's code `1fe6bd2` only under `docs/`. The other tags did not move. |
| branch | `presentation/official-baseline-demo`, from `main` `b0567c8` |
| start head | `5ad73f674b516efcc7d41d231c8cf7f287de0d9a`, verified equal to `origin/presentation/official-baseline-demo` before starting |
| ClaudeChat commits | `74e4d76` (contract), `076efe0` (`demo.py` profile `sparse`; each profile names its lattice), `5ad73f6` (`check_equivalence.py` pins `demo.py` to `076efe0`; README demo sections) |
| fixes (Claude Code) | `bead2b0` (F1, `demo.py` poster snapshots), `1ea62a6` (F2, re-pin `demo.py` to `bead2b0`) |
| report commit | the commit that adds this file |
| run replayed | `previews/playground-sparse-lattice/`: code `70d992e`, `freeze.json` sha256 `3f8bf4bd53180e80de73dcaae99d56349460af39a147202ded0bbd035e2a4a7d`, verified unchanged |
| workspaces | an isolated worktree on a local branch tracking `origin/presentation/official-baseline-demo`; a second, detached worktree at `b0567c8` for N2; both with `.venv` and `scenes/classroom/*` symlinked from the shared checkout. `SCRATCH` is a session scratch directory outside the repository. |

## 2. Commands actually run

From the worktree root, with `RUNS=/home/lvelho/rd/f3d-vision/previews`. `demo.py` is
`.venv/bin/python tools/greedy_foveal/demo.py`.

**First pass, at `5ad73f6`:**

| # | command | wall | exit |
|---|---|---|---|
| C1 | layout checker; `py_compile tools/greedy_foveal/*.py` | interactive | 0; 0 |
| C2 | `check_equivalence.py source` (S1) | interactive | 0 |
| C3 | `demo.py build --profile v0 --out $SCRATCH/v0` (V1) | 93 s | 0 |
| C4 | `demo.py build --profile lattice --out $SCRATCH/p1` (V2) | 92 s | 0 |
| C5 | in the `b0567c8` worktree: `demo.py build --profile lattice --out $SCRATCH/p1-unfixed` (N2) | 91 s | 0 |
| C6 | `demo.py rerender --profile sparse` | 276 s | 0 |
| C7 | `demo.py build --profile sparse` | 13 s | **1**: `IndexError` in `poster()` (F1) |
| C8 | `demo.py check --profile sparse` (L1) | interactive | 1: no `demo-manifest.json`, a consequence of C7 (D1) |
| C9 | `demo.py check --profile sparse --out $SCRATCH/p1-accepted-copy` (N1) | interactive | 1, as required |
| C10 | `.venv/bin/python tools/greedy_foveal/visuals.py --run $RUNS/playground-sparse-lattice --vis /home/lvelho/rd/f3d-vision/visuals/playground-sparse-lattice-demo --title "Official baseline: the sparse covering lattice — FIXATE → RECONSTRUCT → SACCADE (Classroom, fixed head H0)" --mark-fix 347 --mark-name "99 % SEEN" --mark-final` | 7.8 s | 0 |

**After F1 (`bead2b0`) and F2 (`1ea62a6`), at the final code head `1ea62a6`:**

| # | command | wall | exit |
|---|---|---|---|
| C7 | `demo.py build --profile sparse` (first run at `bead2b0`, which F2 does not change for `demo.py`) | 83 s | 0 |
| C1 | layout checker; `py_compile`; `git diff --check 5ad73f6 HEAD` | interactive | 0; 0; 0 |
| C2 | `check_equivalence.py source` (S1) | interactive | 0 |
| C3 | `demo.py build --profile v0 --out $SCRATCH/v0-2` (V1) | 93 s | 0 |
| C4 | `demo.py build --profile lattice --out $SCRATCH/p1-2` (V2) | 91 s | 0 |
| C8 | `demo.py check --profile sparse` (L1) | interactive | 0 |
| C9 | `demo.py check --profile sparse --out $SCRATCH/p1-accepted-copy-2` (N1, a fresh copy) | interactive | 1, as required |

C6 ran detached (`setsid nohup`) from a script file, so it would not depend on the agent's tool-call lifetime. N2 was
not re-run, since its tree `b0567c8` does not contain F1 or F2 (section 3). C10 depends on neither fix: `visuals.py`
is unchanged.

## 3. Check lines (verbatim)

### C1 (both passes)

    [repository-layout] SUMMARY checked=657 failed=0

### S1 (C2 at the final head)

    [gfe-equiv] PASS tag playground-2-sparse-lattice -> 1f50bd6a3f3c  1f50bd6a3f3cf77ccf260375b2cf2fee60c4738f
    [gfe-equiv] PASS tag greedy-foveal-explorer-v0-impl -> a437df048b55  a437df048b555d5b59f6855b6572eea2665ab0da
    [gfe-equiv] PASS demo.py pin bead2b0a84a7 is an ancestor of HEAD  exit 0
    [gfe-equiv] PASS tools/greedy_foveal/explorer.py executable-equal to playground-2-sparse-lattice  docstrings / comments only
    [gfe-equiv] PASS tools/greedy_foveal/run.py executable-equal to playground-2-sparse-lattice  byte-identical
    [gfe-equiv] PASS tools/greedy_foveal/render_server.py executable-equal to playground-2-sparse-lattice  byte-identical
    [gfe-equiv] PASS tools/greedy_foveal/visuals.py executable-equal to playground-2-sparse-lattice  byte-identical
    [gfe-equiv] PASS tools/greedy_foveal/check_lattice.py executable-equal to playground-2-sparse-lattice  byte-identical
    [gfe-equiv] PASS tools/greedy_foveal/demo.py executable-equal to commit bead2b0a84a7  byte-identical
    [gfe-equiv] PASS host import closure loads
    [gfe-equiv] PASS host import closure: every loaded repository module is tracked
    [gfe-equiv] PASS host import closure: no NS1e-lineage module
    [gfe-equiv] SOURCE PASS (12/12 checks passed)

The first pass at `5ad73f6` also gave `SOURCE PASS (12/12 checks passed)`, with the pin `076efe0a1ec9`.

### L1 (C8 at the final head)

    [gfe-demo] check replay_in_exact_order: True
    [gfe-demo] check metadata_seen_depth_equal_run: True
    [gfe-demo] check final_map_from_frozen_run: True
    [gfe-demo] check no_reference_in_derived_stage: True
    [gfe-demo] check reference_only_where_labelled: True
    [gfe-demo] check headline_equals_evaluation: True
    [gfe-demo] check mp4_frames_and_size: True
    [gfe-demo] video 1322 frames, 44.07 s, 1920x1080 @ 30/1
    [gfe-demo] CHECKS PASS

### V1 (C3; identical in both passes)

    655c4757cbc7076a7c717815f1f832f6a78f319d2e31868bcb207655cec0572c  demo.mp4
    98ba555022ecf29b3d3370c2bbb22c82315fa10fcbe9b8958eba0a099f465f02  demo-poster.png
    9afa30dbfb7e14e53a76815d82e273bd0a38e53b75ad4886a4ca9cb764186d65  demo-final.png

All three equal the frozen v0 record; the video has 1,873 frames.

### V2 (C4; identical in both passes)

    326bddfb72648bd41dc21b5b086ebfd3ef756d5a6f0063a30eb8bf7a77f4994f  demo.mp4
    2c26843f8e3e610d5125f3d48dfaeb801a5d8f55dccbe5b23a9068ea26b2c2ab  demo-poster.png
    16dc1d0395bf865050bc705ec941be267a08fcd5581cbb52b1ba7a762d6c0206  demo-final.png

All three equal the accepted Playground-1 package; the video has 1,597 frames. So the Playground-1 replay is
byte-identical again with the fixed `demo.py`.

### N1 (C9; identical in both passes)

    [gfe-demo] check replay_in_exact_order: False
    [gfe-demo] check metadata_seen_depth_equal_run: False
    [gfe-demo] check final_map_from_frozen_run: False
    [gfe-demo] check no_reference_in_derived_stage: True
    [gfe-demo] check reference_only_where_labelled: False
    [gfe-demo] check headline_equals_evaluation: False
    [gfe-demo] check mp4_frames_and_size: True
    [gfe-demo] video 1597 frames, 53.23 s, 1920x1080 @ 30/1
    [gfe-demo] CHECKS FAIL

Five of the seven sparse known answers reject the Playground-1 package. The two that pass do not depend on the run:
the derived-stage firewall, and a well-formed H.264 file whose frame count matches its own manifest.

### N2 (C5, `main`'s unfixed `demo.py` at `b0567c8`)

    499c8ed92f018416ec59b040ed0d060646ca5dc3b89d027860e700dc554b0cc2  demo.mp4          (V2: 326bddfb…994f — differs)
    2c26843f8e3e610d5125f3d48dfaeb801a5d8f55dccbe5b23a9068ea26b2c2ab  demo-poster.png   (equal to V2)
    16dc1d0395bf865050bc705ec941be267a08fcd5581cbb52b1ba7a762d6c0206  demo-final.png    (equal to V2)

**The video differs, so the defect was real.** At `b0567c8` the `lattice` profile draws `explorer.lattice()`, which
is now the 356-gaze baseline lattice. I extracted panel C of the stop frame (frame 1146) from both builds:

- the fixed build shows "gaze lattice: 496 views" with every gaze a fixated dot;
- the unfixed build shows "gaze lattice: 356 views" with nearly every ring still unfixated.

The stills are equal, because only the video's panel C draws the lattice.

### C6 (re-render)

    [gfe-demo] re-render 356 of 356 fixations at 64 spp
    ...
    [gfe-demo] 356/356 (fixation 356) 274 s; same-view median 0.765 mm

All 356 re-render calibrations are byte-identical to the saved ones. The same-view check (recorded, not gated)
gives a median-of-medians of 0.048 mm and a largest per-fixation median of 1.426 mm.

## 4. Deliverables

All are in the shared checkout's `visuals/playground-sparse-lattice-demo/`, 40 MB in total. The package is built at
`bead2b0`, whose `demo.py` is the final one. `overview.png` comes from C10.

| file | bytes | sha256 |
|---|---|---|
| `demo.mp4` | 30,716,147 | `42b161618628031ac4ae653462dfaac9312d52e9b425f9d6fcfef28f13fa64f7` |
| `demo-poster.png` | 2,081,939 | `104fd01188b450033b3688fd8a65e1e3f509f3b255e51b889318791675d2fe76` |
| `demo-final.png` | 988,969 | `3d282f5cac17a27667fdc84b63af56a9e66e4f677fc8158c36091210a15767a8` |
| `overview.png` | 4,273,549 | `2fe769de0e6ab8f12f29ebb20be5aed365273824535c9fdbfb3bbb18d534b55d` |
| `reference-rgb-panorama.png` | 465,052 | `7c2e34265888c04ddc683b09bea3687284ab249b99ebe85af16c2a5cfb8e9860` |
| `reference-depth-panorama.png` | 66,031 | `752c2d947a1619143de00c2d98a19b7f73f9f3fd02d59fc1ee030682ff9b0b14` |
| `reference-instance-panorama.png` | 17,048 | `b2faa742be8c09ee3685c28883d0db0395be504327e1154b49c8c6be8935f8bd` |
| `final-rgb-panorama.png` | 2,302,311 | `a2456c709cd3e0b074d704aac129fdd7ef571f3521c53131265d73053ed41607` |
| `final-depth-panorama.png` | 220,408 | `f53d6fb805599197fcd25a4fb970a9dd941c02a2b51bf01543d2dbafb2dde224` |
| `final-instance-panorama.png` | 73,734 | `bb58360feec7a1378a1207ea439c9c36072258af69026be8a2c814f578452bab` |
| `demo-manifest.json` | 148,703 | `e31eacf352a1eb4c275113f4f9189775c58c7f96a6ef7de496d98b8fada71497` |
| `demo-checks.json` | 802 | `0307a39d74929f9448196095c6b7b824375987eab4e54db973ae08c9acfafc5b` |

The three REFERENCE panoramas are byte-identical to the v0 and Playground-1 packages' (Breadth-1 alone).

The eye cache is `previews/playground-sparse-lattice-demo-cache/` (105 MB). It holds 356 eye `.npz` files,
`eyes-manifest.json`, the reference RGB and the render-server work directory. `build` regenerates the package from it
without rendering.

## 5. The video and the poster

| | value |
|---|---|
| format | H.264, 1920 × 1080, 30 fps (ffprobe, L1) |
| frames / duration | 1,322 frames = 44.07 s |
| segments (frames) | intro 120 · replay 752 · freeze 60 · orbit 150 · final 240 |
| replay | fixations 1 … 356 in exact order (L1): 316 fixations × 2 frames + 40 × 3 frames (those followed by a global saccade) |
| metadata comment | `fixations=356; seen=100.00 %; depth=99.26 %; coverage_solid_angle=98.82 %; coverage_cells=98.93 %; surfels=16,943,073; run=playground-sparse-lattice; run_freeze_sha256=3f8bf4bd…4a7d` |
| firewall (manifest `stage_opens`) | derived stage: 4 opens, none reference; the Breadth-1 EXR and `evaluation.npz` open only in the reference stage; compose reads only the cache's reference RGB |
| final map | the frozen one (sha256 used = frozen) |

**Poster fixation: #169, the profile's default.** It is the lattice fixation nearest v0 #179's gaze: the manifest
records "nearest gaze to v0 #179 (129.98, -9.34): 4.09 deg away". The sparse lattice is coarser than Playground-1's,
so the nearest gaze is 4.09° away, against 0.83° there. I compared it with the frozen v0 poster: it shows layered
chair seats and desks at a similar scale and is equally legible, so `--poster-fix` was not used.

Frames inspected:

- the intro (frame 60): the footer "official baseline: a sparse covering lattice of 356 views" fits;
- the first global saccade (frame 454, #167 → #168, "NEXT: GLOBAL SACCADE → best lattice gaze");
- the stop frame (frame 871, "100 % SEEN · STOP");
- the freeze card (frame 902): "100.00 % SEEN · 99.26 % DEPTH" fits inside the card;
- the final board (frame 1321).

In panel C, the 356 lattice gazes read as rings, then dots as they are fixated. Apart from F1, no presentation defect
was found. In the overview, the long official-baseline title fits the 2,000-px width, and the "99 % SEEN (#347)" and
"final (#356)" marks are legible.

## 6. Fixes (contract §7)

- **F1 (`bead2b0`): the poster's snapshot fixations.**
  - *Defect.* `poster()` hard-coded its four "after fixation k" panels as (50, 200, 450, final). With 356
    fixations, C7 raised `IndexError` at `T[449]`. Had it got past that line, the #450 panel would silently have
    shown the final state, since `state-0450.npz` does not exist.
  - *Fix.* Each profile now names its three snapshots: `v0` and `lattice` keep (50, 200, 450), so their outputs are
    unchanged by construction; `sparse` uses (50, 200, 300). 300 / 356 = 84 % of the run, close to v0's
    450 / 542 = 83 %.
  - *Unchanged.* V1 and V2 are equal after the fix. No run product, control-path code or check rule changed.
- **F2 (`1ea62a6`): re-pin `demo.py`.** `check_equivalence.py`'s `DEMO_COMMIT` now names `bead2b0`, so S1 checks the
  fixed `demo.py`. The other five files stay pinned to `playground-2-sparse-lattice`.

## 7. Deviations

- **D1. Commands after the C7 failure.** C7, C8, C9 and C10 ran as one batch, so C8–C10 ran before C7's failure had
  been diagnosed.
  - C8 failed only because C7 had written no manifest.
  - C9 (N1) and C10 depend on neither C7 nor F1. C10's `overview.png` is the delivered one, and N1 was re-run on a
    fresh copy at the final head with the same result.
  - The failed C7 had already written `demo-final.png` and the panoramas. The successful C7 overwrote all of them.
- **D2. Builds re-save a cache file.** Every `build`, including V1, V2 and N2, re-saves its cache's
  `reference/b1-rgb.png` (`demo.py`'s reference stage). A sha256 snapshot of all 4,186 files was taken before C1 and
  again after the last command, and the two are identical. The snapshot covers:
  - `visuals/greedy-foveal-explorer-v0-demo/`;
  - `visuals/playground-gaze-lattice-demo/`;
  - `previews/greedy-foveal-explorer-v0-demo-cache/`;
  - `previews/playground-gaze-lattice-demo-cache/`.

  Nothing was written into either frozen package directory. N1 used scratch copies, verified identical before the
  run.
- **D3. N2 was not re-run after the fixes.** It tests `main`'s unfixed code at `b0567c8`, which the fixes do not
  touch. Its reference, V2's `demo.mp4`, is the same before and after.
- **D4. An extra C1 check.** C1 also ran `git diff --check 5ad73f6 HEAD` over the fixes; it was clean.

## 8. For Luiz

The machine half is complete; the viewing half (contract §6) is open. The deliverables to view are `demo.mp4`,
`demo-poster.png`, `demo-final.png` and `overview.png`, in `visuals/playground-sparse-lattice-demo/`. `main` was not
touched.

## 9. Acceptance

**Luiz's decision (2026-10-12): ACCEPTED** ("It's done and accepted"), after viewing the deliverables of section 4.
With it, the phase that began with Playground-1 is complete.

**ClaudeChat review**, from GitHub at `cb21ae2`:

- **The machine half holds at the final head.** S1 passes 12 / 12 with `demo.py` pinned to `bead2b0`. V1 and V2 are
  byte-equal to the frozen v0 record and the accepted Playground-1 package, N1 fails and N2 differs, as required.
- **F1 was a defect in ClaudeChat's code.** `poster()` hard-coded its snapshots at fixations 50, 200 and 450, and the
  `sparse` profile did not override them. The Chat-sandbox test rendered the intro, strips, freeze card and panel C,
  but not the poster, which needs the derived assets. Claude Code's fix is within contract §7, leaves `v0` and
  `lattice` unchanged by construction, and V1 / V2 confirm it.
- **N2 confirms the lattice defect on `b0567c8`.** Only the video differs (panel C draws 356 baseline rings over the
  Playground-1 run). The stills do not draw the lattice. The accepted Playground-1 package was never affected.
- D1–D4 are recorded deviations with no effect on the deliverables. D2's before / after snapshot of both frozen
  packages and their caches is identical.

**On `main`:** this branch is fast-forwarded into `main` with this acceptance. `tools/greedy_foveal/demo.py` on `main`
is then `bead2b0`'s, and `check_equivalence.py source` pins it there. The deliverables stay workstation-local
(gitignored); their sha256 hashes are section 4's.
