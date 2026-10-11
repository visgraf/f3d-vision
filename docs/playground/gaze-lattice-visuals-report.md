# Playground-1 visualization package: report

**Status: ACCEPTED** by Luiz on 2026-10-11, after viewing the deliverables (contract §6; section 10). This is
presentation only. Claude Code built and checked the package on the workstation, under the contract below.

    PLAYGROUND1_VISUALS_ACCEPTED

**Machine checks (contract §6):**

- L1 PASS;
- V1 equal;
- N1 FAIL, as required;
- C1 at 0 failures.

Each was run before and after the one presentation fix (section 6).

Contract: [`gaze-lattice-visuals-contract.md`](gaze-lattice-visuals-contract.md).
Run report: [`gaze-lattice-report.md`](gaze-lattice-report.md).

All numbers are **MEASURED** from the commands named with them.

## 1. Provenance

| item | value |
|---|---|
| branch | `playground/gaze-lattice` |
| start head | `c7fe47629a7a1302e2ce841778beb15064e87731`, verified equal to `origin/playground/gaze-lattice` before starting |
| contract commit | `bcfc822` (ClaudeChat) |
| code commit | `c7fe476` (ClaudeChat): `demo.py` profiles, `visuals.py --title` |
| presentation fix | `a243f20` (Claude Code; section 6) |
| report commit | the commit that adds this file |
| run replayed | `previews/playground-gaze-lattice/`: code `85fb962`, `freeze.json` sha256 `e1422fb42ff23c54b5ad35abe788f0911cc6668489c080d0b89654c9f6ea6b3c`, unchanged |
| tag | `playground-1-gaze-lattice` → `3c64c1f`, not moved |
| workspace | an isolated worktree on a local branch tracking `origin/playground/gaze-lattice`; `.venv` and `scenes/classroom/*` symlinked from the shared checkout; `SCRATCH` is a session scratch directory outside the repository |

`demo.py` does not record git state, so the deliverables do not carry a commit. The final package was built at
`a243f20`.

## 2. Commands actually run

From the worktree root, with `RUNS=/home/lvelho/rd/f3d-vision/previews`. `demo.py` is
`.venv/bin/python tools/greedy_foveal/demo.py`.

| # | command | wall | exit |
|---|---|---|---|
| C1 | `.venv/bin/python tools/repository/check_repository_layout.py` | < 1 s | 0 |
| C2 | `demo.py build --profile v0 --out $SCRATCH/v0-rebuild`, then V1 | 95 s | 0 |
| C3 | `demo.py rerender --profile lattice` | 382 s | 0 |
| C4 | `demo.py build --profile lattice` | 93 s | 0 |
| C5 | `demo.py check --profile lattice` (L1) | interactive | 0 |
| C6 | `demo.py check --profile lattice --out $SCRATCH/v0-frozen-copy` (N1; see deviation D1) | interactive | 1, as required |
| C7 | `.venv/bin/python tools/greedy_foveal/visuals.py --run $RUNS/playground-gaze-lattice --vis /home/lvelho/rd/f3d-vision/visuals/playground-gaze-lattice-demo --title "Playground-1 gaze lattice — FIXATE → RECONSTRUCT → SACCADE (Classroom, fixed head H0)" --mark-fix 472 --mark-name "99 % SEEN" --mark-final` | 7.6 s | 0 |

After inspection and the fix `a243f20`:

| # | command | wall | exit |
|---|---|---|---|
| C1 | layout checker | < 1 s | 0 |
| C4 | `demo.py build --profile lattice` | 92 s | 0 |
| C5 | `demo.py check --profile lattice` (L1) | interactive | 0 |
| C2 | `demo.py build --profile v0 --out $SCRATCH/v0-rebuild-2`, then V1 | 93 s | 0 |
| C6 | `demo.py check --profile lattice --out $SCRATCH/v0-frozen-copy-2` (N1) | interactive | 1, as required |

C3 ran detached (`setsid nohup`) from a script file, so it would not depend on the agent's tool-call lifetime. The
fix touches only the freeze card, so C3 (the eye cache) and C7 (`visuals.py`) were not rerun.

## 3. Check lines (verbatim)

### C1 (both times)

    [repository-layout] SUMMARY checked=651 failed=0

### V1 (both times: C2 at `c7fe476` and at `a243f20`)

    98ba555022ecf29b3d3370c2bbb22c82315fa10fcbe9b8958eba0a099f465f02  .../v0-rebuild/demo-poster.png
    9afa30dbfb7e14e53a76815d82e273bd0a38e53b75ad4886a4ca9cb764186d65  .../v0-rebuild/demo-final.png
    98ba555022ecf29b3d3370c2bbb22c82315fa10fcbe9b8958eba0a099f465f02  .../v0-rebuild-2/demo-poster.png
    9afa30dbfb7e14e53a76815d82e273bd0a38e53b75ad4886a4ca9cb764186d65  .../v0-rebuild-2/demo-final.png

Both equal the frozen record. Beyond V1, both rebuilds are byte-identical to the frozen v0 directory in every
image, with the same 1,873 frames and segments:

- `demo.mp4`, which also covers the v0 freeze card the fix touches;
- all eight PNGs: poster, final, three final and three reference panoramas.

### L1 (C5; identical before and after the fix)

    [gfe-demo] check replay_in_exact_order: True
    [gfe-demo] check metadata_seen_depth_equal_run: True
    [gfe-demo] check final_map_from_frozen_run: True
    [gfe-demo] check no_reference_in_derived_stage: True
    [gfe-demo] check reference_only_where_labelled: True
    [gfe-demo] check headline_equals_evaluation: True
    [gfe-demo] check mp4_frames_and_size: True
    [gfe-demo] video 1597 frames, 53.23 s, 1920x1080 @ 30/1
    [gfe-demo] CHECKS PASS

### N1 (C6; identical before and after the fix)

    [gfe-demo] check replay_in_exact_order: False
    [gfe-demo] check metadata_seen_depth_equal_run: False
    [gfe-demo] check final_map_from_frozen_run: False
    [gfe-demo] check no_reference_in_derived_stage: True
    [gfe-demo] check reference_only_where_labelled: False
    [gfe-demo] check headline_equals_evaluation: False
    [gfe-demo] check mp4_frames_and_size: True
    [gfe-demo] video 1873 frames, 62.43 s, 1920x1080 @ 30/1
    [gfe-demo] CHECKS FAIL

Five of the seven lattice known answers reject the v0 package. The two that pass do not depend on the run: the
derived-stage firewall, and a well-formed H.264 1920 × 1080 file whose frame count matches its own manifest.

### C3 (re-render)

    [gfe-demo] re-render 496 of 496 fixations at 64 spp
    ...
    [gfe-demo] 496/496 (fixation 496) 380 s; same-view median 0.014 mm

All 496 re-render calibrations are byte-identical to the saved ones (`eyes-manifest.json`, `calibration_identical`).
The same-view check (re-rendered left Position against the saved points) gives a median-of-medians of 0.042 mm,
and the largest per-fixation median is 1.165 mm. For context, the v0 cache gives 0.045 / 0.840 mm. That check is
recorded, not gated.

## 4. Deliverables

All are in the shared checkout's `visuals/playground-gaze-lattice-demo/`, 47 MB in total. They are the final build
at `a243f20`, except `overview.png`, which is from C7.

| file | bytes | sha256 |
|---|---|---|
| `demo.mp4` | 38,227,293 | `326bddfb72648bd41dc21b5b086ebfd3ef756d5a6f0063a30eb8bf7a77f4994f` |
| `demo-poster.png` | 2,080,655 | `2c26843f8e3e610d5125f3d48dfaeb801a5d8f55dccbe5b23a9068ea26b2c2ab` |
| `demo-final.png` | 990,243 | `16dc1d0395bf865050bc705ec941be267a08fcd5581cbb52b1ba7a762d6c0206` |
| `overview.png` | 4,110,648 | `ef58970c521bcb336b100f87d1f4a51ea99266d5920cdf952c4ec3dddbf81fd8` |
| `reference-rgb-panorama.png` | 465,052 | `7c2e34265888c04ddc683b09bea3687284ab249b99ebe85af16c2a5cfb8e9860` |
| `reference-depth-panorama.png` | 66,031 | `752c2d947a1619143de00c2d98a19b7f73f9f3fd02d59fc1ee030682ff9b0b14` |
| `reference-instance-panorama.png` | 17,048 | `b2faa742be8c09ee3685c28883d0db0395be504327e1154b49c8c6be8935f8bd` |
| `final-rgb-panorama.png` | 2,247,884 | `77e66092ca099fd7e0abc2cbf6d00167724bc99adb091f5352822173646b9735` |
| `final-depth-panorama.png` | 229,252 | `25f64984dd00f709a21f75fefa67f47b9848093a03bb73ae25730b244cf4cd24` |
| `final-instance-panorama.png` | 78,764 | `4fccf7a811fe61f39e3e5dd9b2c23328d8d3bd8f33e5c0fb24d12be6887e64bb` |
| `demo-manifest.json` | 201,077 | `0113f1cc96b2da5e43ba83408b506f0f5df7b349803b4b66de188498601f224f` |
| `demo-checks.json` | 800 | `93fea169f5d6a829eaccf260245c8fa225666274dea040b9ba8b3185f69c8b22` |

The three REFERENCE panoramas are byte-identical to v0's, as they should be: they come from Breadth-1 alone. The
final panoramas are new; contract §1 lists only the reference panoramas, and the final ones are the build's
standard by-products, as in v0.

The eye cache is `previews/playground-gaze-lattice-demo-cache/` (147 MB). It holds 496 eye `.npz` files,
`eyes-manifest.json`, the reference RGB and the render-server work directory `render-20261011-193437`. `build`
regenerates the package from it without rendering.

Both files cited by the accepted run report are unchanged:

- `visuals/playground-gaze-lattice/overview.png` (sha256 `869121e9…6878`);
- the run's `freeze.json` (`e1422fb4…6b3c`).

## 5. The video

| | value |
|---|---|
| format | H.264, 1920 × 1080, 30 fps (ffprobe, L1) |
| frames / duration | 1,597 frames = 53.23 s |
| segments (frames) | intro 120 · replay 1,027 · freeze 60 · orbit 150 · final 240 |
| replay | fixations 1 … 496 in exact order (L1): 461 fixations × 2 frames + 35 × 3 frames (the 35 fixations followed by a global saccade) = 1,027 |
| metadata comment | `fixations=496; seen=100.00 %; depth=99.31 %; coverage_solid_angle=98.82 %; coverage_cells=98.94 %; surfels=16,702,245; run=playground-gaze-lattice; run_freeze_sha256=e1422fb4…6b3c` |
| firewall (manifest `stage_opens`) | derived stage: 4 opens, none reference; Breadth-1 EXR and `evaluation.npz` only in the reference stage; compose reads only the cache's reference RGB from `/reference/` |

The frozen v0 video has 1,873 frames (62.4 s). The lattice video is shorter because it replays 46 fewer fixations.

Frames inspected:

- the intro (frame 60);
- a local saccade (frame 418, #150, "NEXT: LOCAL SACCADE (SE)");
- the first global saccade (frames 648 / 649, #264 → #265, "NEXT: GLOBAL SACCADE → best lattice gaze");
- the stop frame (frame 1146, #496, "100 % SEEN · STOP");
- the freeze card (frame 1177);
- the orbit (frame 1282);
- the final board (frame 1596).

In panel C, the 496 lattice gazes read clearly: rings for not yet fixated, dots for fixated. At the stop frame every
gaze is a dot. The lattice labels fit the strip and the intro legend. The only defect found was the freeze card
(section 6).

## 6. Fixes

**F1 (`a243f20`): freeze-card headline overrun.**

- *Defect.* The card is 1,100 px wide. At 56 pt the lattice line "100.00 % SEEN · 99.31 % DEPTH" measures
  1,096.3 px, so it touched both borders. v0's "99.00 % SEEN · 98.28 % DEPTH" measures 1,057.4 px and leaves about
  21 px on each side.
- *Fix.* The font steps down by 2 pt only while the line is wider than the card minus 40 px. v0 stays at 56 pt
  (1,057.4 ≤ 1,060). The lattice line is drawn at 54 pt (1,057.1 px), with v0's margins.
- *Unchanged by construction.* v0 output: V1 and the byte-identical v0 `demo.mp4` after the fix confirm it. No run
  product, explorer code, check or known answer changed.

## 7. Poster fixation

The default was kept: **fixation #293**, the lattice fixation whose gaze is nearest v0 #179's gaze. In the manifest
this reads "nearest gaze to v0 #179 (129.98, -9.34): 0.83 deg away". I compared it with the frozen v0 poster: it
shows the same layered chair seats and desks at a similar scale, and is equally legible. `--poster-fix` was not
used.

## 8. Deviations from the contract

- **D1. N1 on a copy.** `check` writes `demo-checks.json` into its `--out`. So N1 ran on scratch copies of the
  frozen `visuals/greedy-foveal-explorer-v0-demo/` (`cp -a`, all 12 files verified sha256-identical before the
  run), not on the frozen directory itself, as the handoff prompt instructed. The known answers it judges (the
  manifest and the video) are the frozen files' bytes.
- **D2. The v0 build rewrites a v0 cache file.** `build --profile v0` saves the cache's `reference/b1-rgb.png` on
  each run (`demo.py`, in the reference stage), so C2 rewrote
  `previews/greedy-foveal-explorer-v0-demo-cache/reference/b1-rgb.png` in place. Its modification time changed and
  its bytes did not. A sha256 snapshot of all 2,185 files of `visuals/greedy-foveal-explorer-v0-demo/` and the v0
  cache, taken before C1 and after the last command, is identical. Nothing was written into
  `visuals/greedy-foveal-explorer-v0-demo/`.
- **D3. Reruns.** C1, C2/V1, C4, C5 and C6 were run twice, before and after F1, as section 7 of the contract
  requires after a fix. Section 3 records both.

## 9. For Luiz

Machine checks complete. The viewing decision (contract §6) is open. The deliverables to view are `demo.mp4`,
`demo-poster.png`, `demo-final.png` and `overview.png` in `visuals/playground-gaze-lattice-demo/`.

## 10. Acceptance

**Decision (Luiz, 2026-10-11): ACCEPTED.** Luiz viewed `demo.mp4`, `demo-poster.png`, `demo-final.png` and
`overview.png`, the qualitative half of contract §6. The machine half is L1 PASS, V1 equal, N1 FAIL and C1 at
0 failures.

- **ClaudeChat review.** F1 (`a243f20`) is the only code change after `c7fe476`, and it touches only the freeze-card
  headline size. In the Chat-sandbox, the v0 profile still renders the intro card, freeze card, static chrome and
  local / global / stop strips pixel-identically to the pre-change `demo.py`, which agrees with Claude Code's
  byte-identical v0 rebuild. The layout checker gives 651 checked, 0 failed at `ae28fce`.
- **Code location.** As with Playground-1, the presentation code (`demo.py --profile`, `visuals.py --title`)
  stays on `playground/gaze-lattice`, and `main` receives docs-only copies of this contract and report.
