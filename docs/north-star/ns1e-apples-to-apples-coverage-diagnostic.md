# NS1e apples-to-apples coverage — diagnostic

**Status: DIAGNOSTIC — REVIEW PENDING.** This is not a controller experiment, not NS1e acceptance and not an
architectural change. No acceptance marker is written. NS1e is not accepted or merged by this work.

> **Question.** Does the final NS1e reconstruction cover the SAME historical Controller-01 reachable surface nearly as
> well as the old Controller-01 reconstruction? In other words, is 98.34 % → 28.96 % (A) a genuine reconstruction
> regression, or (B) mostly a change of evaluation / object-support scope?

**Answer (MEASURED, one canonical run plus an identical second process):**

- On the identical historical samples of the three common ids, Controller-01 covers **99.29 %** and NS1e **0.00 %**
  (Δ −99.29 pp). The deficit is uniform: 0.00 % for every id.
- **It is not a near miss.** The nearest NS1e surfel to any historical sample is **4.75 m** away. The NS1e maps contain
  **0** surfels inside the old Controller domain, and **none** of NS1e's 45 looks at these ids lies there.
- The two reconstructions cover **disjoint parts** of the same large, fragmented oracle objects.
- **Changing only the reference moves the Controller-01 maps themselves from 99.29 % to 5.38 %.** On that same
  Breadth-1 whole-sphere reference, the NS1e maps score **22.96 %**.

Everything below is MEASURED by the identified command unless marked otherwise. Truth labels: reference = REFERENCE /
EVALUATION (oracle first-hit samples, read only after both runs' control had completed); identity = ORACLE (Blender
instance ids); historical numbers = ACCEPTED HISTORICAL REFERENCE.

## 1. Provenance

| item | value |
|---|---|
| repository | `https://github.com/visgraf/f3d-vision` |
| `origin/main` (verified, not modified) | `5aa223109ec829d41945f19b4c5223928fd0dde9` |
| base: NS1e head (verified 7 ahead / 0 behind `origin/main`) | `4a86fc9b808d36837159ebae4b93be4b9987a9ea` |
| branch | `diagnostic/ns1e-apples-to-apples-coverage`, isolated worktree created at the NS1e head |
| tool commit (canonical run made from it, clean tree) | `b65a80233b990edfb2bb22395f71480f0c474cc3` |
| report | the commit that adds this file |
| tool | `tools/north_star/ns1e_apples_to_apples_coverage.py` (read-only; host `.venv`; no Blender, render, stereo or controller) |
| output | `/home/lvelho/rd/f3d-vision/previews/north-star/ns1e-apples-to-apples-coverage/` |

Command (interactive class):

    .venv/bin/python tools/north_star/ns1e_apples_to_apples_coverage.py \
      --c01-run  /home/lvelho/rd/f3d-vision/previews/controller-01-full \
      --ns1e-run /home/lvelho/rd/f3d-vision/previews/north-star/ns1e-coherent-full-loop-m2-memory \
      --out      /home/lvelho/rd/f3d-vision/previews/north-star/ns1e-apples-to-apples-coverage

| artifact | sha256 |
|---|---|
| `comparison.json` | `731ca16a38403fdda997e383dd0beccbdef5e7f2137dd775ea498a9f10d66151` |
| `comparison.png` | `56cebd44cd627bccdb0e0b78a7d8c386fd6796dc75e047d1cf4be40ecd279e44` |
| result digest (both in-process passes and the second process) | `d3af5c296a6a9fbff803b690a8c88cd263037e41d5bcf8eca1c1b399df1541bf` |

### Controller-01 run: identified by hash, not by name

`/home/lvelho/rd/f3d-vision/previews/controller-01-full`. All three accepted hashes match
(`docs/controller/controller-01-state-action-report.md`, "Full run"):

| file | sha256 |
|---|---|
| `manifest.json` | `d293a98fd6bb285e882186af8fbeadba29ab1d1d62efea23f3ed0ff5c62c0e91` |
| `actions.json` | `12cdbe4d760cce6c494075e4368f9424805b51b997b8b21724bf87f71cc55afd` |
| `evaluation.json` | `76cb1e5df88ea401aed6409327bd51fc149fa05b174a1e67b014e671b34512b6` |
| `bootstrap/evaluation_only/reachable_samples.npz` (recorded) | `58f3a2355fc67df4e153f8bbca198a3db1cc042b8e1806ea8706b02c7545b3c6` |
| `bootstrap/seeds.json` (equals the Breadth-1 report's accepted `6ef83319…`) | `6ef833196de2462370ba4b2a2a8eed3fbde7f0a61e5aa6cbaf95f66947134c4f` |

The manifest has `control_complete: true` and is not a smoke run. `objects/instance_XXXX/final_map.npz` exists for all
25 objects.

### NS1e run

`/home/lvelho/rd/f3d-vision/previews/north-star/ns1e-coherent-full-loop-m2-memory/`. All values agree with the NS1e
report, section 1:

| file | sha256 |
|---|---|
| `manifest.json` | `a707ade2ca817740758251231bb7241529dbb347433ec4bfb6ad0dcc0f027dae` |
| `scene/terminal.json` | `6f86e9ba77ce904ca0ece704dd928b4d3dbe85ac0aa79725eb049994547a66df` |
| `control/control-manifest.json` | `bd41663b3a2905396ece5484d79f838c1f3438af35ae77080f06ee9d1ae930f3` |
| `freeze/control-freeze.json` | `fa07a712111e8b41d9bced4521ce533cda1b4bb736077c8562a8603c960775ab` |
| `evaluation/evaluation.json` | `e30da7220239a295ade18d24340a4cc790a737be1ed743878e1376bade235393` |
| `evaluation/coverage.npz` (recorded) | `30c120fe6360af912d332dcbefa4577430fe262e0782adfb8d634e089e917e96` |
| final scene state `scene/state-after-step-172.json` | `39cc2728…`; equals both the control manifest and the control freeze |

Only the **final persistent surface maps** were used. Each map's sha256 was required to equal its frozen record.
Effective geometry, measurement memory and the PLYs were not used.

| id | Controller-01 `final_map.npz` (sha256, surfels) | NS1e final persistent map (path, sha256, surfels) |
|---|---|---|
| 123 | `e1a16f60…`, 32,047 | `run:steps/step-171/fusion/fused-target-map.npz`, `e3e3733c…`, 30,341 |
| 172 | `1d9e20c1…`, 6,094 | `ns1c2:steps/step-06/fusion/fused-target-map.npz`, `8531d554…`, 47,892 (172 took no NS1e action) |
| 202 | `ba790cf9…`, 54,534 | `run:steps/step-029/fusion/fused-target-map.npz`, `3b14aede…`, 203,194 |

**Breadth-1 reference.** The accepted frozen `render/canonical.exr`, sha256 `4ea036fc…` (equal to the NS1e evaluation
record). It was read with the accepted `breadth1_glance.extract_exr`. Nothing was re-rendered.

**Coverage function.** The sealed `tools/classroom_oracle1_eval.py` (sha256 `b9f707e6…`, equal to the NS1e pin),
`_covered(reference, surfels, 0.012)`. The historical reference is read exactly as that module's `main` reads it, and
the Controller-01 maps are loaded with its `_load_map`. The NS1e maps are loaded exactly as NS1e `evaluate` loads them.

## 2. Common object set (derived)

- `OLD_IDS`: the Controller-01 attempted objects, required equal to `localized_object_ids` (25):
  107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 123, 140, 166, 167, 168, 172, 174, 178, 201, 202, 210, 216, 224,
  225, 234.
- `NEW_IDS`: the NS1e final-scene entities, required equal to the ten evaluated entities:
  9, 12, 123, 129, 172, 202, 204, 212, 230, 231.
- **`COMMON_IDS` = {123, 172, 202}**: computed as the intersection, not hard-coded.

The primary reference over the common ids holds **1,400** of the 29,288 historical samples (123: 369; 172: 24;
202: 1,007).

## 3. Coordinate-frame guard (all pass before any coverage is computed)

| # | check | result |
|---|---|---|
| F1 | Controller-01 `seeds.json` head pose == the head pose NS1e's evaluation used (`ns1a:observations/rank-06/acquisition/calibration.json`) | bitwise equal: `head_R_wh` = +90° about X, origin (−0.6, −1.0, 1.2) m |
| F2 | every look that built a common-id map (13 Controller-01 and 45 NS1e calibrations) | same head pose (bitwise), `map_frame` = `H: fixed head; +X right, +Y up, -Z forward; metres`, eye centres (∓0.0315, 0, 0) m |
| F3 | historical reference: XYZ finite and on cyclopean rays from the head origin; stored yaw/pitch equal the Breadth-1 convention; all samples inside the old domain | max ray angle error 1.9e-5°; max yaw/pitch mismatch 1.5e-6°; 0 of 29,288 outside |
| F4 | Breadth-1 orientation test with the Controller-01 head pose | 0 of 222,267 authored cells outside their cell |
| F5 | final maps: (N, 3), finite, surfel counts equal the run records | pass |
| F6 | geometric cross-check: each historical sample → nearest same-id Breadth-1 point in H | median 24 mm, p90 55 mm (bound < 50 mm, declared before the run); negative control, untransformed world Position: median 5.61 m (bound > 0.5 m) |

**Code provenance.** Both sides use the same transform, `p_H = (p_w − o_w) R_wh`:
- Controller-01 reference: `tools/classroom_oracle1_render.py`, seed scan;
- `fsg_geometry.world_to_head`;
- NS1e: `ns1e_core.head_points`.

**No transform was applied or needed.** All four sources are in the one canonical fixed-head H frame.

F6's 202 median (45.7 mm) is close to its 50-mm bound. The 0.5° cells there are about 40 mm apart at about 4.5 m
range, and the surfaces are oblique.

Stronger independent corroboration comes from the measured results below:
- through the same transform, the Controller-01 maps cover **all 318** inside-domain Breadth-1 cells of these ids within
  12 mm;
- the NS1e maps reproduce NS1e's own `coverage.npz` bitwise (K2).

## 4. Primary apples-to-apples result: the exact historical reference (MEASURED)

Both maps against the same `ref_old(i)`, with the same 12-mm `_covered`:

| id | historical reference N | Controller-01 covered | Controller-01 % | NS1e covered | NS1e % | Δ (pp) |
|---|---|---|---|---|---|---|
| 123 | 369 | 369 | 100.00 % | 0 | 0.00 % | −100.00 |
| 172 | 24 | 24 | 100.00 % | 0 | 0.00 % | −100.00 |
| 202 | 1,007 | 997 | 99.01 % | 0 | 0.00 % | −99.01 |
| **micro (common ids)** | **1,400** | **1,390** | **99.29 %** | **0** | **0.00 %** | **−99.29** |

The Controller-01 column reproduces the accepted Controller-01 `evaluation.json` exactly (known answer K1).

**Why 0.00 % (descriptive, same run).** The nearest-distance distribution separates a precision regression from
disjoint support:

| id | historical sample → nearest Controller-01 surfel (min / median / max) | historical sample → nearest NS1e surfel (min / median / max) | NS1e surfels inside the old domain | Controller-01 surfels inside the old domain |
|---|---|---|---|---|
| 123 | 0.3 / 1.9 / 5.8 mm | **4.75** / 5.29 / 6.28 m | 0 / 30,341 | 10,003 / 32,047 |
| 172 | 1.3 / 3.9 / 9.7 mm | **5.33** / 5.42 / 5.50 m | 0 / 47,892 | 531 / 6,094 |
| 202 | 0.07 / 2.8 / 23.0 mm | **4.86** / 5.19 / 5.63 m | 0 / 203,194 | 32,181 / 54,534 |

These distances come from an independent brute-force computation. Its ≤ 12 mm counts equal `_covered` for both maps
(K3).

Where the looks pointed (H yaw / pitch of each executed gaze):

| id | Controller-01 looks (inside old domain) | NS1e looks (inside old domain) |
|---|---|---|
| 123 | 8 (8): yaw −21.7…+19.9°, pitch +18.4…+20.0° | 12 (0): yaw −157.4…−121.5°, pitch +22.8…+39.7° |
| 172 | 1 (1): (−11.5°, +19.75°) | 9 (0): yaw −163.9…−143.5°, pitch +26.1…+48.2° |
| 202 | 4 (4): yaw −23.5…−18.5°, pitch +4.0…+19.5° | 24 (0): yaw −156.3…−124.6°, pitch +7.8…+39.7° |

For all three ids, NS1e's first look is the NS1a bootstrap look (−156.25°, +28.75°).

The map angular supports are disjoint:
- Controller-01 maps: yaw −28.8…+26.5°;
- NS1e maps: yaw −167.1…−111.1°.

## 5. Secondary 2 × 2 scope matrix (MEASURED; fractions within each reference)

A / C are fractions of historical 0.25° samples. B / D are fractions of Breadth-1 0.5° cells, with the solid-angle
weighted value in parentheses. Raw counts of the two references are not comparable.

| id | A: Controller-01 map, old local ref | C: NS1e map, old local ref | B: Controller-01 map, Breadth-1 sphere ref | D: NS1e map, Breadth-1 sphere ref | sphere cells (sr) |
|---|---|---|---|---|---|
| 123 | 100.00 % | 0.00 % | 16.56 % (18.24 %) | 19.13 % (18.63 %) | 1,751 (0.1133) |
| 172 | 100.00 % | 0.00 % | 1.98 % (2.90 %) | 19.86 % (23.89 %) | 2,926 (0.1402) |
| 202 | 99.01 % | 0.00 % | 4.23 % (4.63 %) | 24.85 % (25.42 %) | 8,370 (0.5727) |

Common-id micro:

|  | old local ref (0.25°, 1,400 samples) | Breadth-1 full-sphere ref (0.5°, 13,047 cells, 0.8262 sr) |
|---|---|---|
| Controller-01 final maps | **99.29 %** | **5.38 %** (weighted 6.20 %) |
| NS1e final maps | **0.00 %** | **22.96 %** (weighted 24.23 %) |

D reproduces NS1e `evaluation/coverage.npz` bitwise for every common id: cells and covered flags, 335 / 581 / 2,080
covered (known answer K2).

## 6. Breadth-1 inside / outside the old Controller domain (MEASURED)

The old domain uses the Breadth-1 definition: cell-centre yaw in [−25°, +25°] and pitch in [−20°, +20°], closed, in H.

| scope (common-id micro) | cells | sr | Controller-01 map | NS1e map |
|---|---|---|---|---|
| inside the old domain | 318 | 0.0235 | **100.00 %** (318) | **0.00 %** (0) |
| outside the old domain | 12,729 | 0.8027 | 3.02 % (384) | 23.54 % (2,996) |
| whole sphere | 13,047 | 0.8262 | 5.38 % (702) | 22.96 % (2,996) |

Solid-angle weighted: inside 100.00 % / 0.00 %; outside 3.46 % / 24.94 %; all 6.20 % / 24.23 %.

| id | inside: cells, Controller-01 / NS1e covered | outside: cells, Controller-01 / NS1e covered |
|---|---|---|
| 123 | 83: 83 / 0 | 1,668: 207 / 335 |
| 172 | 4: 4 / 0 | 2,922: 54 / 581 |
| 202 | 231: 231 / 0 | 8,139: 123 / 2,080 |

Only **2.4 %** of the common ids' whole-sphere cells (2.8 % of their solid angle) lie inside the old domain.

## 7. Checks (MEASURED)

| group | result |
|---|---|
| input pins (Controller-01 ×3, NS1e ×5, final scene state, ten map records, Breadth-1 EXR, evaluator module, radius 12 mm on both sides) | all verified; any mismatch is a STOP before coverage |
| common-id derivation | derived; both id sets cross-checked against a second record |
| finite XYZ / dimensions | F3, F5 |
| coordinate-frame provenance and geometry | F1–F6: **6/6** |
| exact 12-mm coverage code | K1 (Controller-01 evaluation reproduced) ×3, K2 (NS1e `coverage.npz` reproduced bitwise) ×3, K3 (independent brute force = `_covered`) ×3: **9/9** |
| determinism | the whole computation run twice in-process gives an identical result digest (**1/1**); a second process gives the same digest and a byte-identical figure |
| read-only | an audit hook refuses any write, create or delete outside `--out`; 0 violations; `--out` must lie outside both runs |
| `git diff --check` | clean (tool commit and report commit) |

**Fail-capability (scratch harness, not committed).** Each negative control was caught:
- a write outside `--out` → refused;
- a wrong Controller-01 pin → STOP;
- a halved Controller-01 map → STOP at F5;
- a same-count 20-mm shift of the Controller-01 maps → K1 fails for all three ids;
- the NS1e head origin moved by 1 m → STOP at F1 / F2.

**Not run, per the speed policy:** Blender, any renderer, either loop, the repository layout suite, `verify_baseline`,
the NS1e checker, the corruption suite, the 577-probe re-drive and the visualization pipeline. NS1e check 25 scans
only the NS1e report and the NS1e run's own JSON files, so this output directory (a sibling of the run) is outside its
scope. The new tool and report are not declared to the layout checker; this branch is not intended for merge.

## 8. Interpretation (for Luiz and Chat; no threshold was declared or tuned)

**By the literal condition: CASE B.** NS1e is far worse than Controller-01 on the identical historical samples
(0.00 % vs 99.29 %), uniformly for all three ids. Because the deficit is uniform, this is not Case C.

**The measured data do not support Case B's causal reading,** a degraded reconstruction of the same surface:
- NS1e never reconstructed that surface. It has 0 surfels inside the old domain, 0 of its 45 looks at these ids lie
  there, and its nearest surfel is ≥ 4.75 m from every historical sample. A precision regression would appear as near
  misses just beyond 12 mm, and there are none.
- Controller-01 never reconstructed most of NS1e's surface. On the Breadth-1 cells outside the old domain it covers
  3.02 %, against NS1e's 23.54 %.
- For the common ids the two maps occupy disjoint angular supports of the same oracle objects (202 `wall`, 123
  `ceilingMoulding`, 172 `pipe`; wide or multi-component objects).

The primary test therefore **cannot measure reconstruction quality** for these ids, because there is no shared support.

**What it does establish is a scope effect, the question's option B.** With the maps held fixed, changing only the
reference takes the Controller-01 maps of these ids from 99.29 % to 5.38 %. On that same whole-sphere reference the
NS1e maps reach 22.96 %. For these ids the coverage collapse comes from the reference and from where each system
looked, not from how well it reconstructed.

**Limits of this diagnostic:**
- Only 3 of the 10 NS1e entities and 3 of the 25 Controller-01 objects are common. The aggregate scalars (98.34 %:
  25 objects at 0.25°; 28.96 %: 10 entities at 0.5°) are not decomposed further here.
- Nothing here measures NS1e's reconstruction quality where NS1e looked against Controller-01's where Controller-01
  looked.
- Spherical vs planar projection is not tested.

## 9. Recommended next experiment (a proposal; the decision belongs to Luiz and Chat)

The Case-B default named in the diagnostic prompt is a planar vs spherical comparison on the same frozen photons. This
evidence does not indicate it as the next causal step for these ids, because NS1e has no support on the reference at
all.

The density-consistent analogue of the Controller-01 metric for NS1e is **coverage of each entity's own reachable
surface**. That is the PROPOSED next diagnostic, again read-only and with no render:

- **Reference.** The Breadth-1 0.5° cells of entity i whose H direction lies inside that entity's fixed NS1e policy
  chart domain. That domain is chart-local yaw ±25° and pitch ±20° about the entity's original NS1a initialization
  gaze, mapped to H through the accepted NS1b chart.
- **Maps and coverage.** The final persistent map, with the same 12-mm `_covered`, for all ten entities.
- **Reading.** If NS1e covers its own chart-domain surface at a level comparable to Controller-01's coverage of its
  controller domain, the 28.96 % is support scope. If specific entities are low there, those entities become the
  bounded fixtures for the planar vs spherical same-photon comparison.

## 10. Runtime (MEASURED)

| item | seconds |
|---|---|
| one full pass (pins, frame guard, coverage, descriptives) | 4.0 (run 1), 3.9 (run 2) |
| canonical command wall time (two passes plus figure and JSON) | **8.0** |
| class | interactive |

## 11. Deviations and notes

- **Output tree.** The visual is under `./previews/` (`comparison.png`), as the diagnostic prompt specifies. No
  `./visuals/` package was produced. CLAUDE.md asks executed scientific steps for a visual under `./visuals/`; this
  diagnostic followed the prompt instead, and Luiz may want it promoted.
- **No separate contract file.** The paste-ready diagnostic prompt served as the specification. Its scope is restated
  in sections 1–6.
- **Additions beyond the prompt.** These are descriptive or protective only; no number in sections 4–6 depends on
  them:
  - nearest-distance and map-support descriptives;
  - look-gaze table;
  - K3;
  - the write guard;
  - the cross-process determinism re-run.
- The shared checkout's local `main` was stale (`e681392`). It was not touched. All work used `origin/main` and the
  NS1e head.

```
DIAGNOSTIC REVIEW PENDING

NO CONTROLLER OR PROJECTION CHANGE AUTHORIZED.
```
