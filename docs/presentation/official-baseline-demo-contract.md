# The official baseline's demo (the Playground-2 run): contract

**Status: EXECUTED and ACCEPTED** (2026-10-12; see [the report](official-baseline-demo-report.md), section 9; its F1
adds the per-profile poster snapshots §2 missed). Requested by Luiz on 2026-10-12 to complete this phase. Presentation only. ClaudeChat
wrote this contract and the code changes; Claude Code renders, builds and checks on the workstation.

| item | value |
|---|---|
| branch | `presentation/official-baseline-demo`, from `main` `b0567c8` (the official baseline is tag `greedy-foveal-playground-baseline-2` → `9bf936d`) |
| run replayed | the frozen Playground-2 run `previews/playground-sparse-lattice/` (code `70d992e`, `freeze.json` sha256 `3f8bf4bd…4a7d`). Like the v0 demo, which replays the frozen grow600 run rather than its reproduction; the official reproduction is bitwise equal to it in every control-path product (Engineering-2). |
| format | the v0 demo and the accepted Playground-1 package (`docs/playground/gaze-lattice-visuals-report.md`) |

## 1. Deliverables

The deliverables go in `visuals/playground-sparse-lattice-demo/`, in the shared checkout:

- `demo.mp4`: 1920 × 1080, H.264, 30 fps;
- `demo-poster.png` and `demo-final.png`;
- the reference and final panoramas;
- `demo-manifest.json` and `demo-checks.json`;
- `overview.png`, with an official-baseline title.

## 2. What changes (presentation code only)

1. **`demo.py` gains a profile `sparse`** for the Playground-2 run. Its wording is the `lattice` profile's: "step to a
   nearby lattice gaze", "jump to the best lattice gaze", "100 % SEEN · STOP" and the stop rule "no lattice gaze adds
   unseen area". It names the official baseline in its intro and poster footer, and draws the 356 lattice gazes on
   panel C. Its known answers are the frozen run's: 356 fixations, 100.00 % SEEN, 99.26 % DEPTH, 98.82 % of solid
   angle and 98.93 % of cells within 12 mm, and 16,943,073 surfels. Its poster fixation is the one nearest v0
   #179's gaze, the same rule as the `lattice` profile.
2. **Fix: each profile names its own lattice.** Every profile now has a `lattice_kind`: none for `v0`, `"pitch"` for
   `lattice`, `"baseline"` for `sparse`. `Replay` builds that lattice explicitly (`build_lattice()` or
   `build_baseline_lattice()`), instead of using `explorer.lattice()`.
   - **The defect.** Since Engineering-2, `explorer.lattice()` returns the 356-gaze baseline rings. The `lattice`
     profile on `main` would therefore draw the wrong dots over the Playground-1 replay.
   - **Unaffected.** The accepted Playground-1 package was built on its own branch, where `lattice()` was the pitch
     lattice, so it is not affected.
3. **`check_equivalence.py source`** pins `demo.py` to the commit that makes changes 1–2, not to
   `playground-2-sparse-lattice`, since `demo.py` legitimately changes. The other five files stay pinned to
   `playground-2-sparse-lattice`, so the control path is still checked against the promoted behavior. This is
   the same split Engineering-1 made with its separate demo tag.
4. **The READMEs' demo sections** name the new profile.

## 3. What deliberately does not change

- `explorer.py`, `run.py`, `render_server.py`, `visuals.py` and `check_lattice.py`;
- every run product, which each stage verifies against its `freeze.json`;
- the truth-domain firewall: the DERIVED stages never open the Breadth-1 reference;
- the frozen v0 demo, the accepted Playground-1 package and the official baseline.

## 4. Fail-capable checks

| # | check | must |
|---|---|---|
| S1 | `check_equivalence.py source`: the five control files are executable-equal to `playground-2-sparse-lattice`, and `demo.py` to its pinned commit | PASS |
| L1 | `demo.py check --profile sparse` (replay order 1…356, metadata, frozen final map, firewall, headline, MP4 format) | PASS |
| V1 | `demo.py build --profile v0 --out $SCRATCH/v0`: `demo.mp4`, `demo-poster.png` and `demo-final.png` sha256 equal to the frozen v0 record: `655c4757cbc7076a7c717815f1f832f6a78f319d2e31868bcb207655cec0572c`, `98ba555022ecf29b3d3370c2bbb22c82315fa10fcbe9b8958eba0a099f465f02`, `9afa30dbfb7e14e53a76815d82e273bd0a38e53b75ad4886a4ca9cb764186d65` | equal |
| V2 | `demo.py build --profile lattice --out $SCRATCH/p1`: the same three files equal to the accepted Playground-1 package: `326bddfb72648bd41dc21b5b086ebfd3ef756d5a6f0063a30eb8bf7a77f4994f`, `2c26843f8e3e610d5125f3d48dfaeb801a5d8f55dccbe5b23a9068ea26b2c2ab`, `16dc1d0395bf865050bc705ec941be267a08fcd5581cbb52b1ba7a762d6c0206` | equal |
| N1 | `demo.py check --profile sparse --out <a copy of the Playground-1 package>`: the sparse known answers against Playground-1's outputs | FAIL |
| N2 | the `lattice` profile built with `main`'s unfixed `demo.py` (`b0567c8`) into `$SCRATCH/p1-unfixed`: its `demo.mp4` sha256 differs from V2's | differ |

- **V2 proves the fix.** It shows the Playground-1 replay is byte-identical again on `main`.
- **N2 shows the defect was real.** If N2's video equals the accepted one, the fix is moot; report that.
- If V1 or V2 differs, stop. Report whether the difference is environmental by building twice. Never write into the
  frozen v0 directory or the accepted Playground-1 directory.

## 5. Commands and cost classes

These run from an isolated worktree at the branch head named in the handoff. `SCRATCH` is a scratch directory outside
the repository, and `RUNS=/home/lvelho/rd/f3d-vision/previews`. `demo.py` is
`.venv/bin/python tools/greedy_foveal/demo.py`.

| # | command | cost class |
|---|---|---|
| C1 | `.venv/bin/python tools/repository/check_repository_layout.py`; `.venv/bin/python -m py_compile tools/greedy_foveal/*.py` | Interactive |
| C2 | `.venv/bin/python tools/greedy_foveal/check_equivalence.py source` (S1) | Interactive |
| C3 | V1 | Batch (about 1.5 min) |
| C4 | V2 (needs `$RUNS/playground-gaze-lattice-demo-cache`) | Batch |
| C5 | N2: in a second worktree at `b0567c8`, `demo.py build --profile lattice --out $SCRATCH/p1-unfixed` | Batch |
| C6 | `demo.py rerender --profile sparse` | about 5 min (ESTIMATED: Playground-1 took 382 s for 496 fixations); authorized by Luiz as this step's render |
| C7 | `demo.py build --profile sparse` | Batch |
| C8 | `demo.py check --profile sparse` (L1) | Interactive |
| C9 | N1, on a scratch copy of `visuals/playground-gaze-lattice-demo/` | Interactive |
| C10 | `.venv/bin/python tools/greedy_foveal/visuals.py --run $RUNS/playground-sparse-lattice --vis /home/lvelho/rd/f3d-vision/visuals/playground-sparse-lattice-demo --title "Official baseline: the sparse covering lattice — FIXATE → RECONSTRUCT → SACCADE (Classroom, fixed head H0)" --mark-fix 347 --mark-name "99 % SEEN" --mark-final` | Interactive |

## 6. Acceptance

- **Machine half:** S1 and L1 PASS, V1 and V2 equal, N1 FAIL, N2 differ, C1 clean.
- **Viewing half:** Luiz's review of `demo.mp4`, `demo-poster.png`, `demo-final.png` and `overview.png`.

## 7. Stop conditions and permitted fixes

**Stop and report** on any of these:

- a `freeze.json` mismatch;
- a firewall violation;
- a V1 or V2 difference;
- an L1 failure that is not a presentation defect.

**Permitted fixes:**

- presentation defects in `demo.py` (layout, label overlap, legibility), provided V1 and V2 are re-run after the fix;
- re-pinning `demo.py` in `check_equivalence.py` to the commit that carries such a fix;
- overriding the poster fixation with `--poster-fix`, recording why.

No run product, control-path code or check rule changes.

## 8. Results to record

Claude Code commits `docs/presentation/official-baseline-demo-report.md` with:

- the branch, the commits and the commands run;
- the S1, L1, V1, V2, N1 and N2 lines, verbatim;
- each deliverable's path and sha256;
- the video's frames, duration and segments;
- the poster fixation;
- every fix and every deviation from this contract.
