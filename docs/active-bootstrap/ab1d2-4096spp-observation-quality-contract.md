# Active Bootstrap-1d2 — 4096-spp Observation-Quality Control — contract

**Status: CONTRACT (committed before any implementation, any 4096-spp Classroom render, any inspection of a 4096-spp
Classroom image and any 4096-spp matcher result).**

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (never the legacy `visgraf/fov-3d-vision`) |
| base | `22f538f8eb2dad69d45b7fc3183fbcc2ee861d55` (accepted `main`: AB1d accepted at `c5f9bf5`, post-AB1d roadmap) |
| branch | `active-bootstrap/ab1d2-4096spp-observation-quality`, isolated worktree |
| completion marker | `ACTIVE_BOOTSTRAP1D2_4096SPP_OBSERVATION_QUALITY_COMPLETE` (no ACCEPTED marker; status REVIEW PENDING) |
| run (machine evidence) | `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1d2-4096spp-observation-quality/` (`RUN`) |
| visuals | `/home/lvelho/rd/f3d-vision/visuals/active-bootstrap/ab1d2-4096spp-observation-quality/` (`VIS`) |

Every numerical value in this contract is a **declared design constant**, an **accepted measured value quoted from a
committed AB1c / AB1d record**, or a **PROPOSED** expectation, and is labelled as such. Nothing here is a new
measurement.

## 1. One causal question

> Holding scene, gaze, camera geometry, calibration, renderer settings, random-seed convention, matcher, search
> interval, patch, score, refinement, benchmark and evaluation FIXED, does increasing the Cycles sampling from 256 spp
> to 4096 spp materially improve natural spherical epipolar correspondence?

- AB1d2 is an **OBSERVATION-QUALITY CONTROL**. The single independent variable is Cycles samples per pixel:
  AB1c / AB1d **256 spp** → AB1d2 **4096 spp** (16 × as many samples).
- Theoretical context only (PROPOSED, not a prediction to be tested against a threshold): if stochastic rendering
  variance dominates, 16 × the samples would reduce the per-pixel standard deviation by about 4 ×. AB1d2 measures what
  actually happens.
- AB1d (accepted negative) found that the frozen primitive matcher does not recover reliable correspondence at the
  three AB1c observations. Its labelled post-run diagnostic suggested roughly 2–3 u8 per-eye variation attributable to
  render noise under a noise-only interpretation, against a typical 5 × 5 patch std of about 3–5 u8. **The causal role of
  render noise was not established.** AB1d2 tests it.
- AB1d2 is **not**: a matcher redesign, a denoising experiment, a patch-size / colour / aggregation / prior / learned
  experiment, an spp sweep, a head-motion, controller or attention experiment. It does not change the texture threshold.

## 2. Provenance and branch

- Pull: `origin/main` = `22f538f`. AB1d2 branches from it in a dedicated isolated worktree. The shared checkout is not
  switched or mutated; only the gitignored `RUN` and `VIS` trees are written there.
- Commit 1: this contract, with the layout checker's AB1d2 declaration. Commit 2: the implementation (developed only
  on accepted code, calibration-only data, the AB1c 256-spp observations as a null pair, synthetic records and a
  non-Classroom Blender rehearsal; section 21). Then the canonical run from that clean, pushed commit. Then the report.

## 3. Source pins (verified by `source`; a mismatch is a STOP)

### 3a. The accepted AB1c observations and calibrations (the 256-spp condition; read-only)

AB1c run `A1C` = `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1c-safe-forward-planar-vs-spherical/`,
manifest `21640f6a56474f9ed171d37ceb13571a56499ac805b1b1bbec09c6808a0d378a`. The AB1d `OBS_PINS` (accepted
`tools/active_bootstrap/ab1d_spec.py`) pin, per gaze, `observations/<g>/acquisition/{calibration.json,
rgb-observation.npz, acquisition.json}`; AB1d2 imports and verifies exactly those pins. Calibration SHA256 (accepted):

| gaze | AB1c calibration sha256 | AB1c 256-spp rgb-observation sha256 |
|---|---|---|
| gaze-1 | `ae56ef338561a9d23d4208e36fb88862adb08e6bd8f773651ed3aa9e83224ebf` | `d6e2a532acf1534ed305ad63447b30b35645051a350922cbcec14dbb5388f47f` |
| gaze-2 | `ab348665b6c86443145cfa448ac488ec101eab41277d47b0d93c3eaabfd37ec7` | `297c5bd689cde4a5bf9b01b53e4b643719feff6f654a25a470a2e8b627bca43d` |
| gaze-3 | `085ff33204b84c3d7b05a92c3099bef600dd698bf6e6ab209cb0e5bfe748accd` | `5924f94656b6bf3536ed986f2d47433331e201d7ea911c3df7f1ef52c57a170c` |

Also pinned: the AB1c instance catalog `observations/evaluation_only/instance-catalog.json`
(`948dd8d4c1824e5acf6a3a179b7a8a6d4b39134dda041861dbb8193fe3d3df4a`; read only by the render-control comparison of the
scene object list, never by inference or evaluation), the Classroom blend `scenes/classroom/classroom_eye.blend`
(`dca66a3257b909aef00b0331652c55f62a93a8dff0665d070fba7efa436953cc`) and the accepted head-pose record
`previews/controller-01-full/bootstrap/seeds.json` (`6ef833196de2462370ba4b2a2a8eed3fbde7f0a61e5aa6cbaf95f66947134c4f`).

### 3b. The accepted AB1c benchmark (REFERENCE / EVALUATION; opened only after the geometry freeze)

Exactly the AB1d `BENCH_PINS` (accepted `ab1d_spec.py`): per gaze, `oracle/<g>/oracle-correspondences.npz` (perfect
correspondence), `spherical/<g>/epipolar-result.npz` (perfect spherical reconstruction) and
`observations/<g>/evaluation_only/reference-observation.npz` (Blender Position), plus the AB1c correspondence and
geometry freezes. **The oracle is not regenerated, and any Position / Object Index pass rendered by AB1d2 is never used
for the benchmark** (section 12).

### 3c. The accepted AB1d products (the paired 256-spp reference; read-only)

AB1d run `A1D` = `/home/lvelho/rd/f3d-vision/previews/active-bootstrap/ab1d-safe-forward-natural-correspondence/`:

| file | sha256 |
|---|---|
| `manifest.json` | `3f6a837d6529b8fc1a6680aeb18446c6c9ecbe0e67e5304a4e4154837161b838` |
| `match/correspondence-freeze.json` | `006c9116b5127b63efb218d179aef4283d8a0466f631d358a5a2082d72d0c5ab` |
| `freeze/geometry-freeze.json` | `0c2d7b0a3e847085451279a96431541b4ba8998b35c03e5f099597729cc84730` |
| `evaluation/evaluation-summary.json` | `692f49d7c6de6b7babec1fd9775102d933a2f3c97f8e545c0fa164029c187345` |
| `match/gaze-{1,2,3}/matcher-record.npz` | `9a474127…` / `541e3a5c…` / `5034fc6f…` (full values in `ab1d2_spec.py`) |
| `match/gaze-{1,2,3}/natural-correspondences.npz` | `bf9382ae…` / `844c60c6…` / `102e5b04…` |
| `spherical/gaze-{1,2,3}/epipolar-result.npz` | `646e4528…` / `2c8940d9…` / `5a490853…` |
| `evaluation/gaze-{1,2,3}/evaluation-result.npz` | `c849e72d…` / `b794127d…` / `e8665c2b…` |

Every one must also appear with the same hash in the pinned AB1d manifest. The AB1d visuals manifest
`visuals/active-bootstrap/ab1d-safe-forward-natural-correspondence/visuals-manifest.json`
(`c7391c7b3516afed4dc728381f8ffaf8fa4fac4697661ff3aa2781c5ac397ecf`) supplies the accepted example pixels (section 20).

### 3d. Accepted code reused read-only (sha256 at the base)

| file | sha256 | role |
|---|---|---|
| `tools/active_bootstrap/ab1d_match.py` | `dd1ac243…ec255ffd` | the frozen matcher |
| `tools/active_bootstrap/ab1d_spec.py` | `fc50a730…aba7b346` | the frozen matcher constants, AB1c pins |
| `tools/active_bootstrap/ab1d_run.py` | `9df2981b…cb482a7292` | `run_match_gaze`, `run_spherical_gaze`, `evaluation_core` |
| `tools/active_bootstrap/check_ab1d.py` | `600106c0…3e12862` | the accepted independent matcher (`own_match`) for the AB1d2 checker |
| `tools/active_bootstrap/ab1d_visuals.py` | `33a8d9b0…d912fdf53` | figure helpers |
| `tools/active_bootstrap/ab1a_render.py` | `ae96164a…6d51e01b` | Blender acquisition (`eye_pose`, `calibration`, `configure`, `readback`, `acquire_pair`, `calib_diff`, `build_rehearsal_scene`) |
| `tools/active_bootstrap/ab1a_spec.py` | `24ab5df9…5ab24a62` | `SEEDS` L 2111 / R 2112, `DEVICE` OPTIX |
| `tools/active_bootstrap/ab1c_render.py`, `ab1c_spec.py` | `a1281a20…`, `53d1b722…` | accepted AB1c driver (not modified, not imported) |
| `tools/classroom_oracle1_render.py`, `render_foveated.py`, `bl_common.py`, `exr_lite.py` | pinned | accepted Classroom pair configuration, `render_fixation`, seed pin, EXR reader |
| `tools/fsg_geometry.py`, `tools/fsg_stereo.py`, `tools/natural_bootstrap/nb1a_guard.py` | pinned | calibration, photometry, open guard |
| `tools/active_bootstrap/ab1b_geometry.py`, `ab1b_spec.py`, `ab1b_visuals.py`, `ab1c_visuals.py`, `tools/visual_language/style.py`, `tools/classroom_oracle/breadth1_visuals.py` | pinned | spherical geometry, figure helpers |

Full hashes live in `ab1d2_spec.py` (and as independent literals in `check_ab1d2.py`). **No accepted file is modified.**
The only changed tracked files on the branch are the AB1d2 contract, report and tools, and the layout checker.

## 4. The one intentional change

| property | AB1c / AB1d (accepted) | AB1d2 |
|---|---|---|
| Cycles samples per pixel | 256 | **4096** |
| scene | Classroom `classroom_eye.blend` (`dca66a32…`) | same |
| gazes (row, col; yaw, pitch °) | gaze-1 (191, 322; −18.75, −5.75), gaze-2 (166, 373; +6.75, +6.75), gaze-3 (190, 397; +18.75, −5.25) | same; no new attention selection |
| head pose, eye centres, IPD, vergence | accepted head pose; IPD 0.063 m; vergence 2.10 m; `baseline_projected` tangent frame | same; no head motion |
| calibration (intrinsics, extrinsics) | AB1c `calibration.json` | **byte-identical copy** (section 5) |
| raster / core | 640 × 640, nominal 256 × 256 raw core | same |
| engine / device | CYCLES / GPU OPTIX | same |
| denoising / adaptive sampling | OFF / OFF | OFF / OFF |
| pixel filter | BOX, width 1.0 | same |
| motion blur, film, colour, EXR | OFF; opaque film; OPEN_EXR_MULTILAYER, codec NONE, 32-bit | same |
| render seeds | L 2111, R 2112 (independent) | **same** (L and R stay independent; seeds are not changed between conditions) |
| render passes | Combined, Position, Object Index (+ the inherited AB1a set), no Z, no Normal | same (truth passes stay `evaluation_only`, unused) |

- The accepted helpers are used read-only. The new Blender driver `ab1d2_render.py` calls `ab1a_render.acquire_pair`
  with `spp = 4096`, exactly as `ab1c_render.canonical` called it with 256. No accepted renderer is modified.
- The accepted `render_fixation` tags the scene for update whenever samples or seed change (the known persistent-data
  pitfall) and asserts `(samples, seed, adaptive, time_limit) = (4096, seed, False, 0.0)` after every render.
- Cycles writes its own sample count into each EXR header (`cycles.interior.samples`; AB1c: `'256'`, read from the
  accepted EXR headers at design time). AB1d2 requires `'4096'` there: an independent record of the samples actually
  rendered.
- **No lower spp is substituted to save time without Luiz / Chat approval** (section 24).

## 5. Calibration identity (no geometric change, even numerically)

For each gaze, before any render:
1. The calibration built in Blender from the Classroom EYE and the gaze (`ab1a_render.calibration`, as in AB1c) must
   equal the accepted AB1c calibration to the accepted tolerance `CALIBRATION_TOL = 1e-9` (`calib_diff`; PROPOSED
   expectation: exactly 0).
2. The calibration actually used is the **accepted AB1c `calibration.json`, loaded and re-serialized**. Its
   serialization by the accepted `write_json` must reproduce the AB1c file **byte for byte**; otherwise STOP before
   rendering. After rendering, the AB1d2 `calibration.json` SHA256 must equal the AB1c pin (section 3a).
3. The camera matrices (`classroom_oracle1_render._eye_matrix` of that calibration, as `mathutils` matrices) must equal
   the matrices recorded in the accepted AB1c `acquisition.json` to the accepted camera-pose tolerance
   `EYE_POSE_TOL = 1e-6` (PROPOSED expectation: exactly equal). Otherwise **STOP BEFORE RENDERING**.

The check runs twice: in the no-render Blender `preflight` (all three gazes) and again inside the canonical process for
all three gazes before the first render.

## 6. Blender driver and render product

`tools/active_bootstrap/ab1d2_render.py` (Blender's Python; failures exit nonzero, `--python-exit-code 1`):
- `preflight` (Classroom, **no render**): section 5 for every gaze; `configure(c, 4096)` and `readback`; the settings must
  equal the AB1c record's except `samples` (= 4096). Writes `preflight/preflight.json` (`"rendered": false`).
- `canonical` (Classroom): replicates the AB1c canonical call sequence exactly (so the Blender object state and the
  per-gaze camera names `CLASSROOM_ORACLE1`, `.001`, `.002` are the same): section 5 for all gazes (no scene change);
  `_assign_instance_ids` and the evaluation-only instance catalog; then for gaze-1, gaze-2, gaze-3 in order one
  `acquire_pair(c, acq, ev, 4096, extras)` each. Exactly **3 gazes × 2 eyes = 6 images**, one binocular pair per gaze.
- `rehearsal` (factory-startup synthetic room of AB1a; **never Classroom**): section 21.

Per gaze the product is the AB1c schema: `observations/<g>/acquisition/{calibration.json, rgb-observation.npz
(exactly rgb_L, rgb_R), acquisition.json}` and `observations/<g>/evaluation_only/{raw_L.exr, raw_R.exr,
reference-observation.npz}`, with `observations/evaluation_only/instance-catalog.json`. The new truth passes exist only
because the accepted acquisition helper writes them; **AB1d2 never opens them** (section 12).

No rerender for any reason (noisy appearance, poor matching, anything else). `render-4096` refuses to run if any
observation exists. A failed canonical acquisition is not retried: a second acquisition is a decision for Luiz and
Chat.

## 7. Render-setting equivalence (after the render, before any matching)

`render-4096` compares, per gaze, the new `acquisition.json` and both EXR headers with the accepted AB1c ones
(EXR **header metadata only**: the first 64 KiB of each file are parsed; no pixel data is decoded). Every field falls
into exactly one class; a field outside the classes, or any class violation, is a **HARD STOP** (no freeze).

**acquisition.json**
- MUST EQUAL (load-bearing): `schema`, `truth`, `statement`, `blender`, `gaze_yaw_pitch_deg`, `profile`,
  `tangent_frame`, `ipd_m`, `vergence_distance_m`, `device`, `render_seeds_lr` (exactly `{L: 2111, R: 2112}`),
  `seed_rule`, `exr_channels_lr`, `settings` (every key except `samples`: engine, device, resolution, percentage,
  adaptive, denoising, pixel filter, filter width, motion blur, film, file format, codec, depth, passes, camera type /
  lens / sensor / shift / clip / dof), `camera_matrix_world_lr` (≤ 1e-6), `calibration_sha256`,
  `rgb_observation_arrays`, `evaluation_only`, `complete`, `canonical`, `ab1c_gaze`, `ab1c_rank`, `eye_pose`,
  `calibration_max_abs_diff_from_planned` (here: vs the AB1c calibration).
- EXPECTED DIFFERENT (exactly as declared): `spp` 256 → 4096; `settings.samples` 256 → 4096; `primary_camera_samples`
  209,715,200 → 3,355,443,200 (2 · 640 · 640 · spp); `render_seconds_lr`; `rgb_observation_sha256`; `created_utc`.
- LABEL (declared provenance text; verified separately): `experiment`, `action_source`, `blend` (path text; its real
  path must equal the AB1c record's real path and the file SHA256 the pin), `observation_quality_control` (AB1d2 only).

**EXR header (each eye)**
- MUST EQUAL: `BlenderMultiChannel`, `Camera`, `Scene`, `Software`, `Frame`, `Time`, `channels`, `colorInteropID`,
  `compression`, `dataWindow`, `displayWindow`, `lineOrder`, `pixelAspectRatio`, `screenWindowCenter`,
  `screenWindowWidth`, `xDensity`.
- EXPECTED DIFFERENT: `cycles.interior.samples` `'256'` → `'4096'`; timing (`Date`, `RenderTime`,
  `cycles.interior.render_time`, `cycles.interior.synchronization_time`, `cycles.interior.total_time`).
- LABEL: `File` (blend path text; real path equal).

**Scene object list**: the instances of the AB1d2 instance catalog equal those of the AB1c catalog.

The result is `observations/render-control.json`, listing every field with its class, both values, and verdict.

## 8. Observation freeze

`freeze-observation` writes `freeze/observation-freeze.json` before any matching: the SHA256 of every
`acquisition/` file, of `render-control.json`, `preflight/preflight.json` and the instance catalog; the
`evaluation_only` EXR / reference files (**hashed only, never decoded**); the renderer-source pins; the blend SHA256;
the seeds; `spp = 4096`; the AB1c calibration pins (equal). After this point nothing is rerendered.

## 9. The frozen AB1d matcher, unchanged

The accepted AB1d matcher runs **unchanged** through the accepted `ab1d_run.run_match_gaze(calibration, rgb, out)`:
direct raw-image spherical epipolar search over the full physically admissible segment, 1.0 px spacing from the
infinite-range point, no depth prior; 5 × 5 angular patch; `linear_to_u8` + (0.2126, 0.7152, 0.0722) gray;
`MIN_LOCAL_STD_U8 = 0.5` (the only threshold; **not changed**, section 18); ZNCC; ties within 1e-12 →
smallest k; TOP_K = 8 distinct peaks ≥ 3 px apart; one 3-point parabola bounded at ±0.75 sample. AB1d2 passes no
parameters (the matcher's `FROZEN` defaults), never assigns to the matcher or spec modules, and calls no other matcher.
No SGBM / SGM / dynamic programming / aggregation / smoothness / depth prior / learned feature / denoising / confidence
rejection.

- **Inference reads only** `RUN/observations/<g>/acquisition/calibration.json` (byte-identical to AB1c) and
  `rgb-observation.npz` (`rgb_L`, `rgb_R`), under the accepted allowlist `OpenGuard` and the accepted cv2 tripwires.
  AB1d2 adds its own audit: no read under any `evaluation_only/`, the AB1c run, or the AB1d run; `bpy`, `ab1d2_render`,
  torch / tensorflow / onnxruntime not loaded.
- The output schema is AB1d's (same function): `match/<g>/{matcher-record.npz, natural-correspondences.npz,
  match-summary.json, match-opened-files.json}`.
- `match` requires the observation freeze and a passing `preflight-tests` report from the same clean commit.

## 10. Search-geometry identity (256 vs 4096; hard stop)

The calibration-derived matcher fields must be **exactly equal** (bitwise, NaN = NaN) between the accepted AB1d
256-spp record and the AB1d2 4096-spp record, for every one of the 65,536 core pixels of each gaze:
`left_core_row`, `left_core_col`, `uv_L`, `theta_L`, `phi_L`, `q_inf`, `line_dir`, `line_l`, `k_first`, `k_last`,
`candidate_count` (admissible candidates, i.e. the candidate uv locations before texture / photometric rejection, which
are `q_inf + k · line_dir` for k in [`k_first`, `k_last`]) and `valid_left_patch`.

`freeze-correspondence` performs this comparison before freezing; **any difference is a HARD STOP (the experiment is
confounded)**. The only intended differences come from RGB → patch values → texture → ZNCC landscapes → chosen
correspondences.

## 11. Spherical geometry and freezes (accepted AB1b; unchanged)

- `freeze-correspondence`: `match/correspondence-freeze.json` (records, products, guard records, matcher code hashes,
  matcher config SHA256, matcher inputs, the observation-freeze SHA256, the section-10 identity result).
- `spherical`: the accepted `ab1d_run.run_spherical_gaze` (accepted AB1b `compute_epipolar`) on the calibration and the
  frozen natural product only; no cv2, no matcher, no truth.
- `freeze-geometry`: `freeze/geometry-freeze.json`, before any benchmark or Position access.

## 12. Benchmark reuse and truth firewall

After both freezes, `evaluate-paired` opens, under an allowlist `OpenGuard` with ordered marks
`freezes_verified` → `reference_access_begins`, exactly: the AB1d2 frozen files and observations; the accepted AB1c
256-spp observations (for the 256-spp scores and diagnostics); the accepted AB1d products (section 3c); and the
accepted AB1c benchmark (section 3b), whose hashes must equal the AB1c pins. **Any read of an AB1d2 `evaluation_only`
file is a violation** (new 4096 truth passes are not a benchmark). For every evaluable left-core index the 256-spp and
the 4096-spp estimates are scored against the **same** AB1c oracle θ_R: the experiment is paired.

## 13. Absolute 4096-spp result (exact AB1d definitions)

The accepted `ab1d_run.evaluation_core` (AB1d contract sections 17–22) on the 4096 records, geometry and RGB, with the
AB1c oracle, perfect reconstruction and Position. Per gaze: oracle pairs, natural valid, evaluable, coverage; signed
e_θ and |e_θ| (median, p90, p95, p99, max); local pixel-equivalent error (same quantiles); fractions ≤ 0.10 / 0.25 /
0.50 / 1.00 px; oracle peak rank top 1 / 3 / 5 / 8 / worse than 8 (ORACLE-ON-CURVE within 1.5 px); ZNCC (oracle-on-curve
median, best-score median, oracle − best, peak margin). Written as `evaluation/<g>/evaluation-result.npz` (AB1d schema).

**256-spp reproduction control**: the same function on the accepted AB1d records, geometry and AB1c RGB must reproduce
the accepted AB1d `evaluation-result.npz` arrays exactly (NaN-aware equality) and the accepted per-gaze summary exactly.
Otherwise HARD STOP (Outcome 4). The paired comparison uses these 256-spp values.

## 14. PRIMARY causal comparison — paired 256 vs 4096

Common set **C** = core indices evaluable in both runs (oracle ∧ natural valid at 256 and at 4096). Counts of C and of
the indices evaluable in only one run are reported. On C, with E = |pixel-equivalent error| (AB1d contract section 19):

- E256, E4096, ΔE = E4096 − E256 (negative = improvement);
- median E256, median E4096; median ΔE; p10 / p50 / p90 ΔE;
- fractions E4096 < E256 − ε, |E4096 − E256| ≤ ε, E4096 > E256 + ε, with the numerical equality tolerance
  **ε = 1e-9 px** (declared here, before any result);
- 1-px transitions (descriptive bin "good" = E ≤ 1.0 px; **not** an acceptance threshold): bad → good, good → good,
  good → bad, bad → bad (counts and fractions of |C|).

## 15. Paired photometric effect

On C, with the AB1d definitions:
- oracle-on-curve ZNCC Z256, Z4096; ΔZ median, p10, p90; fraction ΔZ > 1e-12 (increased), with unscorable (NaN)
  counts reported separately;
- top-1 transitions (not top1 → top1, top1 → top1, top1 → not top1, not top1 → not top1); the same 2 × 2 for top 3 and
  top 8;
- **competing peak score** (declared here; uses only AB1d record fields and the AB1d oracle radius): the maximum
  `peak_zncc` over the recorded distinct peaks whose line coordinate lies farther than `ORACLE_PEAK_RADIUS_PX = 1.5`
  from ORACLE-ON-CURVE (NaN if none); paired median and Δ;
- peak margin (`peak_margin`, best minus second distinct peak) and oracle − best: paired medians and Δ.

## 16. Metric consequence

The accepted spherical geometry on the frozen 4096 natural correspondences; per gaze: natural 4096 vs perfect spherical
(median, p90, p95, p99, max), natural 4096 vs Position (median, p95), fractions within 12 / 25 / 50 mm (descriptive).
Side by side with the accepted AB1d 256-spp values, and paired on C: 3-D error vs perfect at 256 and 4096, Δ (median,
p10, p90) and the fraction improved by more than 1e-12 m.

## 17. Observation-quality diagnostics (descriptive; no variance claim)

No second 4096 render is made to estimate variance; **no physical noise variance is claimed**.
1. **Paired gray change** (the matcher's gray, `ab1d_match.gray`), per gaze and eye: |G4096 − G256| median, p90, p95, and
   the signed mean, over the full 640 × 640 raster and over the nominal core. This is the change between two renders, not
   a noise estimate. A systematic signed mean would indicate a non-sampling difference (section 19, Outcome 4).
2. **Patch texture** at 256 vs 4096: left 5 × 5 patch std (`left_patch_std_u8`, all valid left patches) and the
   oracle right patch std (on C): median and quartiles.
3. **Oracle-on-curve ZNCC** at 256 vs 4096 (section 15).
4. **PROXY** quantities (labelled PROXY wherever reported; never converted into a sensor-noise variance):
   - PROXY-LR: robust std (1.4826 · MAD) of G_L at the oracle left pixel minus bilinear G_R at the oracle right point,
     over the oracle pairs, at 256 and at 4096 (REFERENCE / EVALUATION: uses the oracle);
   - PROXY-HP: robust std of the left-core high-pass residual (pixel minus the mean of its 4 neighbours) divided by
     √1.25, at 256 and at 4096.

   These replicate the AB1d labelled post-run diagnostic so the conditions can be compared.
5. **Texture-stratified paired result**: on C, strata by the quartiles of the **256-spp** left patch std (edges fixed
   from the 256 condition, applied to both): median E256 / E4096, top-1 at 256 / 4096, median Z256 / Z4096.

## 18. Texture threshold control

`MIN_LOCAL_STD_U8 = 0.5` is kept exactly. If 4096 spp shows a cleaner separation between useful and useless texture, it
is reported (section 17.5); it is not thresholded.

## 19. Outcome semantics (no data-dependent success threshold)

- **OUTCOME 1 — observation quality was a major limit**: a broad, coherent improvement (oracle scores increase, ranks
  improve, correspondence errors shrink, metric reconstruction improves); the frozen matcher becomes substantially more
  useful without any matcher change.
- **OUTCOME 2 — observation quality helps but ambiguity remains dominant**: correct correspondence improves meaningfully,
  particularly in weak / noisy areas, but large ambiguous regions remain and the matcher is still not generally useful.
- **OUTCOME 3 — little or no improvement**: little systematic improvement in oracle rank, angular correspondence or
  metric result; independent 5 × 5 local matching over the full interval is intrinsically inadequate for this scene /
  regime.
- **OUTCOME 4 — unexpected regression or inconsistency**: geometry differs, render settings differ beyond spp, the
  256-spp reproduction fails, or the 4096 observation systematically worsens for unexplained reasons. STOP and diagnose
  the experimental control.

The report reads the paired result against these descriptions; Luiz and Chat decide. AB1d2 does not build the next
matcher.

## 20. Visuals (Visual Language 1)

`VIS` = `visuals/active-bootstrap/ab1d2-4096spp-observation-quality/`; text truth badges; deterministic (the checker
regenerates every PNG byte-identically); `visuals-manifest.json` records hashes, badges, sources, display transforms
and the example pixels.
- `overview.png` (ORACLE INPUT, DERIVED, REFERENCE / EVALUATION): **A** same view, one changed variable — for each gaze
  the 256-spp and the 4096-spp left image with an identical display transform (`linear_to_u8`, no stretch), and a zoomed
  crop pair; the statement "same scene · same gaze · same calibration · same seeds · same matcher · 256 → 4096 spp ONLY"
  drawn on the figure. Any contrast-stretched crop uses identical limits for both conditions and carries a visible
  "CONTRAST-STRETCHED" label (limits recorded in the manifest). **B** same pixels, paired cost landscapes (one accepted
  example per gaze). **C** correspondence change per gaze (256 error map, 4096 error map, paired change map: improved /
  unchanged / worsened). **D** metric consequence with paired numbers.
- `paired-cost-landscapes.png` (ORACLE INPUT, DERIVED, REFERENCE / EVALUATION): **all twelve accepted AB1d example
  pixels**, read from the pinned AB1d visuals manifest in its order (median-error, high-confidence low-error, smallest
  peak margin, large-error percentile per gaze). **No example is chosen after seeing 4096 results.** Each panel overlays
  the 256 and 4096 ZNCC curves over the full chord, ORACLE-ON-CURVE, and both selected natural peaks.
- `correspondence-improvement.png` (DERIVED, REFERENCE / EVALUATION): error maps, ΔE maps, transition tables.
- `observation-comparison.png` (ORACLE INPUT, DERIVED, REFERENCE / EVALUATION): image pairs, |ΔG| maps, texture and
  oracle-ZNCC distributions, PROXY values labelled PROXY.
- `metric-comparison.png` (DERIVED, REFERENCE / EVALUATION): 3-D error maps and distributions at 256 and 4096.
- `confidence-change.png` (DERIVED, REFERENCE / EVALUATION): section 17.5 strata at 256 and 4096.

No figure shows only improved examples.

## 21. Preflight known answers and rehearsal (before the canonical render)

The matcher is accepted and frozen; it is **not** re-researched. Only what is new in AB1d2 is tested, on accepted code,
the accepted AB1c 256-spp records, synthetic records and a non-Classroom rehearsal. No Classroom render other than
the canonical one is made; no 4096-spp Classroom image is used in development.

`preflight-tests` (host; `preflight/preflight-tests.json`, marker `AB1D2_PREFLIGHT_PASS`):
1. the driver selects exactly spp = 4096 (declared constant; the canonical call passes it; static check);
2. a record with spp 256 / 2048 / 8192 fails the setting comparison;
3. denoising enabled fails; 4. adaptive sampling enabled fails;
5. L seed changed fails; R seed changed fails; 6. the same seed for both eyes fails;
7. pixel filter type changed fails; filter width changed fails; 8. resolution changed fails;
9. camera matrix changed fails; gaze changed fails; 10. calibration hash changed fails;
11. a matcher source change (in a mirror) fails the source verification; a changed matcher constant fails the
    constant identity;
12. a changed benchmark file (in a mirror) fails the benchmark verification;
- plus: the unmodified expected record (AB1c record with exactly the declared expected differences) passes; an
  unknown extra field fails; an EXR header with a denoising pass, a different `Scene` or a missing samples attribute
  fails; the search-geometry identity passes on the accepted record against itself and fails on a perturbed `q_inf` /
  `k_last` / `candidate_count`; the paired statistics give ΔE ≡ 0 and a diagonal transition table on a record paired
  with itself.

`rehearse` (Blender, factory-startup synthetic room of AB1a, **never Classroom**; `synthetic/rehearsal/`):
13. the AB1c gaze-1 direction rendered at 256 and at 4096 spp (one pair each, seeds 2111 / 2112) through the same
    `acquire_pair`: calibrations byte-identical, camera matrices identical, settings identical except samples, EXR
    `cycles.interior.samples` 256 / 4096, the setting comparison 256 → 4096 passes with exactly the declared expected
    differences, RGB differs (max |Δ| > 0); the comparison of the rehearsal 4096 record against the accepted AB1c record
    **fails** (different scene: a negative control on real Blender output).

The canonical `render-4096` requires passing `preflight-tests` and `rehearse` reports from its own clean commit and the
no-render Classroom `preflight` record.

## 22. Checker (`tools/active_bootstrap/check_ab1d2.py`)

Own literal constants and pins; fail-capable; `ACTIVE_BOOTSTRAP1D2_CHECKS_PASS`. Coverage:
- **Provenance**: canonical remote; branch / base ancestry; contract commit; accepted AB1d source pins; AB1c observation,
  calibration and benchmark pins; AB1d product pins; AB1d visuals manifest; only declared files changed since the base.
- **Render control**: exactly 3 gazes and 6 eye renders; spp 4096 in the record, the readback and both EXR headers;
  same gaze, calibration (byte-identical), camera matrices (own recomputation from the calibration and the accepted
  record), resolution, scene (blend SHA256, real path, EXR `Scene`, object list), engine / device, seeds 2111 / 2112,
  denoising OFF, adaptive OFF, filter, passes; own re-implementation of the section-7 classification; no rerender.
- **Matcher**: accepted matcher source and constants (own literals); match summaries carry the accepted matcher config
  SHA256; no override / no other matcher (static scan of the AB1d2 tools); guard records; an independent
  re-implementation of the matcher (the accepted AB1d checker's `own_match`) on the 4096 RGB for core index % 32 == 7
  and the example pixels agrees with the stored record; no shortened search.
- **Geometry**: section-10 identity recomputed over the full core; accepted AB1b spherical geometry only (config SHA256,
  reads, modules).
- **Freeze / truth**: observation freeze before matching; correspondence freeze before spherical; geometry freeze
  before evaluation (process order, freeze contents, guard mark order); no AB1d2 `evaluation_only` read anywhere;
  benchmark hashes equal the AB1c pins.
- **Paired evaluation**: same oracle pixels; independently recomputed θ errors, local pixel scale, ORACLE-ON-CURVE and
  ranks for the 4096 run; the 256 reproduction equals the accepted AB1d arrays; paired ΔE, ε-fractions, 1-px
  transitions, ΔZ, rank transitions, competing peak and margin; metric consequence; diagnostics (PROXY labels present).
- **Visuals**: deterministic regeneration; the twelve accepted example indices reused in order; truth badges; display
  transforms recorded, identical across conditions, stretched panels labelled.
- **Process**: each canonical stage once, in order, from one clean pushed commit; preflight-tests and rehearsal before
  the render; no matcher redesign, AB1e, controller or head-motion command or module.

## 23. Corruption / mutation suite

An unmodified-mirror **null probe** first must pass every check. Then genuine defects in mirrors of `RUN` / `VIS`; each
names the checks that must catch it and counts only if one of them fails. Families:
- **render**: spp ≠ 4096 (record, readback, EXR header); denoising on; adaptive on; L seed changed; R seed changed; L = R
  seed; pixel filter changed; camera pose changed; one gaze changed; calibration changed; resolution changed;
- **source**: accepted 256 observation altered; accepted AB1d matcher source altered; accepted benchmark altered;
- **matcher**: patch size, texture threshold, spacing, hidden depth truncation, ZNCC, refinement changed (injected into
  the checker's view of the match record / constants);
- **geometry**: candidate line changed; baseline sign changed;
- **freeze**: 4096 RGB modified after the observation freeze; correspondence modified after its freeze; geometry
  modified after its freeze;
- **evaluation**: new 4096 Position used instead of the AB1c benchmark; paired error corrupted; top-1 transition count
  corrupted; metric comparison corrupted;
- **visual**: a different example pixel chosen; a canonical figure pixel altered; a truth badge altered;
- **process**: a gaze rendered twice; match run twice; a denoising pass inserted; a head-motion action inserted; a
  controller action inserted.

## 24. Permitted fix scope

- Before the canonical 4096 Classroom render: ordinary implementation bugs in the new driver, checker, orchestration
  or visualization may be corrected and documented.
- After the first canonical render starts, **nothing below changes**: spp = 4096, render seeds, render settings, gazes,
  calibration, matcher, texture threshold, search range, patch, score, refinement, benchmark, scientific metrics, outcome
  semantics. A disappointing result is the result. A code defect may be fixed only when this contract already determines
  the correct behaviour; every incident is documented.

## 25. Cost (PROPOSED)

- Accepted AB1c 256-spp render calls took 1.2–1.8 s per eye (MEASURED in the AB1c `acquisition.json`; Cycles render
  time about 1.1 s plus about 0.5 s synchronization in the EXR header). PROPOSED: about 16 × the render time at 4096 spp,
  roughly 15–25 s per eye, about 2–3 minutes for six eyes plus scene loading: **batch**.
- Matching about 1 minute (AB1d MEASURED 57 s for three gazes); evaluation and figures under a minute; checker with
  corruptions a few minutes. No overnight task.
- If the canonical render appears likely to exceed about **30 minutes**: STOP before changing any setting and report.
  spp is never lowered without Luiz / Chat approval.

## 26. Commands and run order

    .venv/bin/python tools/active_bootstrap/ab1d2_run.py source                --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py preflight-tests       --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py rehearse              --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py preflight             --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py render-4096           --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py freeze-observation    --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py match                 --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py freeze-correspondence --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py spherical             --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py freeze-geometry       --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py evaluate-paired       --run RUN
    .venv/bin/python tools/active_bootstrap/ab1d2_run.py visualize             --run RUN --visuals VIS
    .venv/bin/python tools/active_bootstrap/check_ab1d2.py --run RUN --visuals VIS --corruptions --write-summary

- Canonical stages (each exactly once, from one clean pushed implementation commit, refusing to rerun): `source`,
  `preflight`, `render-4096`, `freeze-observation`, `match`, `freeze-correspondence`, `spherical`, `freeze-geometry`,
  `evaluate-paired`. `preflight-tests` and `rehearse` run once in `RUN` from the same commit before `render-4096`.
  `visualize` is deterministic and may be regenerated.
- Run layout: `source/`, `preflight/`, `synthetic/rehearsal/`, `observations/`, `freeze/`, `match/`, `spherical/`,
  `evaluation/`, `logs/`, `process-log.jsonl`, `manifest.json`, `check-summary.json`.
- Tools: `ab1d2_spec.py`, `ab1d2_render.py`, `ab1d2_run.py`, `ab1d2_preflight.py`, `ab1d2_visuals.py`,
  `check_ab1d2.py` (all under `tools/active_bootstrap/`).

## 27. Report and stop

`docs/active-bootstrap/ab1d2-4096spp-observation-quality-report.md`, status **REVIEW PENDING**, marker
`ACTIVE_BOOTSTRAP1D2_4096SPP_OBSERVATION_QUALITY_COMPLETE`, no ACCEPTED marker. Contents: provenance (repo, base,
branch, contract / implementation / report SHAs); exact AB1d and AB1c source pins; proof that only spp changed; render
times; 4096 RGB hashes; the absolute 4096 result; the paired result; paired ZNCC / rank changes; metric consequence;
observation diagnostics; outcome reading; checks; mutations; visuals and hashes; incidents and fixes; what is
established; what is not; unresolved decisions.

Then **STOP**: AB1d2 is not accepted or merged by Code; no matcher change, no 8192 spp, no denoising, no larger patch,
no SGM / continuity, no learned features, no AB1e, no controller.

## 28. What AB1d2 may and may not establish

- MAY establish: whether increasing the path-tracing sample count substantially changes natural correspondence for the
  frozen matcher; whether the true correspondence becomes more photometrically distinctive at 4096 spp; whether the
  AB1d negative result was strongly observation-quality limited; whether ambiguity remains after substantially cleaner
  sampling.
- Does NOT establish: the optimal spp; a biological sensor-noise model; real-camera performance; the effect of
  denoising, larger patches, spatial aggregation or learned features; an optimal confidence threshold; arbitrary-gaze
  stereo; head-motion behaviour; controller performance.

## 29. Declared constants (summary)

| constant | value |
|---|---|
| `SPP` / accepted | 4096 / 256 |
| seeds | L 2111, R 2112 |
| device | OPTIX |
| `CALIBRATION_TOL` / `EYE_POSE_TOL` (accepted) | 1e-9 / 1e-6 |
| `EQUAL_TOL_PX` (ε) | 1e-9 px |
| `ZNCC_EQUAL_TOL` | 1e-12 |
| `METRIC_EQUAL_TOL_M` | 1e-12 m |
| `GOOD_PX` (descriptive bin) | 1.0 px |
| `ORACLE_PEAK_RADIUS_PX` (AB1d) | 1.5 px |
| PROXY scale factors | 1.4826 (MAD), √1.25 (4-neighbour high-pass) |
| EXR header read | first 65,536 bytes (header only) |
| render budget STOP | about 30 minutes |
| matcher constants | AB1d (unchanged): PATCH 5, LUMA (0.2126, 0.7152, 0.0722), MIN_LOCAL_STD_U8 0.5, SPACING 1.0, TIE 1e-12, TOP_K 8, separation 3 px, refinement bound 0.75 |
