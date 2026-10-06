# North Star-1e — Full Coherent Multi-Entity Loop with Cross-Target Measurement Memory — report

**Marker.**

    NORTH_STAR1E_COHERENT_FULL_LOOP_M2_MEMORY_COMPLETE

**Status: REVIEW PENDING.** No ACCEPTED marker is written. NS1e is not merged.

> **Question.** Starting from the accepted NS1d M2-enriched post-NS1c2 state, can the accepted Controller-02 scene
> machine autonomously service the entire coherent ten-entity North-Star scheduler universe to its honest terminal state,
> without controller retuning?

**Answer (MEASURED, one canonical run): yes — Control Outcome 1R.** The accepted machine ran unattended from the exact
accepted start state to an honest Controller-02 `scene_closed`, reported scientifically as **`COHERENT_SUBSET_CLOSED`**,
after **165 new physical actions** (global steps 8–172; 174 controller actions including the 9 accepted controller-phase
prefix observations), well before the derived cap (231 / absolute step 239).

- **Five entities ended locally QUIET in NORMAL:** 123, 129, 172, 202, 212.
- **Five rank-1 entities (9, 12, 204, 230, 231) were serviced to the 24-look ordinary budget** with Cyclopean actions
  only, became `DEFERRED:ordinary_budget`, and in RESIDUE their unchanged Cyclopean proposals were rejected by
  `final_look_gate_v1` as `untraceable_final_support` → `FINALIZED:final_probe_rejected`. No final residue observation
  was executed. Closure is therefore not global quiescence (1R, not 1Q).
- **Cross-target memory was live throughout:** 7,700,338 new memory samples (own 2,714,847; coherent cross-target
  3,474,568; non-scheduler 1,510,923); 402 cross-target re-probes; 27 of them re-probed QUIET entities (172, 202, 212),
  which all stayed QUIET. **No natural reactivation occurred.**
- **NORMAL final-gate calls: 0.** 8 switches, all `schedule_normal`; 10 attention bouts; 0 hard-cap events; 0 failed,
  refused or repeated stages; no restart.
- **Post-control evaluation** (final persistent maps only, 12 mm, accepted Breadth-1 0.5° whole-sphere first-hit
  reference): **6,155 / 21,254 cells = 28.96 %**; solid-angle weighted **30.10 %**. Diagnostic effective geometry (map +
  memory): 29.58 % / 30.73 %. Controller-01's 98.34 % is **not numerically comparable**.

Truth labels: CORRESPONDENCE = PERFECT / ORACLE; IDENTITY = ORACLE SEGMENTATION AID; GEOMETRY = DERIVED spherical H0;
reference = REFERENCE / EVALUATION (opened only after the control freeze); historical numbers = ACCEPTED HISTORICAL
REFERENCE.

## 1. Provenance

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (verified by `source` and check 01; the legacy `fov-3d-vision` never used) |
| base (`main`, post-NS1d roadmap) | `5aa223109ec829d41945f19b4c5223928fd0dde9` |
| NS1d acceptance | `25bb929b4d39e1e73cabf0df582bc3c5d3e45e06` (`NORTH_STAR1D_CROSS_TARGET_MEASUREMENT_MEMORY_ACCEPTED`) |
| branch | `north-star/ns1e-coherent-full-loop-m2-memory`, isolated worktree |
| contract | `3e36b8a409c577e5b619387e8eb276501080c4ce`; pre-implementation amendment (section 36) `0728857de498e2b560def4e7233fefce2c222dfe` = `CONTRACT_COMMIT`; unchanged since (check 01) |
| implementation | `a6a600cbebba7004b7bbed1f846c409e2110ae1f` — every control and evaluation stage ran from it, clean and pushed (2,153 stage runs; the two `visualize` runs came from `d02d94c` and `459682a`) |
| presentation-only figure commits (contract 32 b) | `d02d94c`, `ff706c6`; the final `visualize` ran from `459682a` (the checker commit, whose tree contains both) |
| checker / corruption suite | `459682a` (written outside the run worktree during the run, committed after it) |
| report | this commit |
| upstream pins | NS1d manifest `2b5bd172…`, state after event 8 `7f0c7ce5…`, final next decision `6dcf21a8…`; NS1c2 manifest `0ec6228d…`, state after step 7 `7e50ecf5…`, charts `058a9253…`; NS1a seed set `e2ff1ba3…`, gaze list `785d02a7…`; Breadth-1 EXR `4ea036fc…` |

- **Run.** `RUN` = `/home/lvelho/rd/f3d-vision/previews/north-star/ns1e-coherent-full-loop-m2-memory/` (26 GB; 165 step
  directories plus the terminal decision directory; `manifest.json` `a707ade2…`; `freeze/handoff-freeze.json`
  `35a3b636…`; `scene/terminal.json` `6f86e9ba…`; `control/control-manifest.json` `bd41663b…`; `freeze/control-freeze.json`
  `fa07a712…` (8,678 control files); `evaluation/evaluation.json` `e30da722…`; `check-summary.json` `e7bd4aff…`).
- **Visuals.** `VIS` = `/home/lvelho/rd/f3d-vision/visuals/north-star/ns1e-coherent-full-loop-m2-memory/`.

### What ran (MEASURED, `process-log.jsonl`; every entry `ok`)

| command (`tools/north_star/ns1e_run.py`) | result | seconds |
|---|---|---|
| `source` | 56 accepted-code pins; NS1d ACCEPTED on the base; NS1c not accepted; NS1a / NS1c2 / NS1d pins | 0.2 |
| `synthetic` | `NS1E_SYNTHETIC_PASS` 20/20 | 0.2 |
| `handoff` | start state and next decision reproduced exactly; cap 231 / 239 (section 4) | 3.2 |
| `gate-harness` | M2 gate wiring: 202 FSG6f admitted (traced, real H0 sensor); 9 Cyclopean rejected `untraceable_final_support` | 0.9 |
| `loop` (14:40:09 → 16:34:57 UTC) | 165 steps × 13 stage processes; terminal `closed` at step 173; `freeze-control` | 6,888 (1 h 54 min) |
| `evaluate` (separate process, after the control freeze) | micro 28.96 %, weighted 30.10 % | 7.6 |
| `visualize` (from `459682a`; presentation-only figure code) | 7 figures + 2 PLYs | 16.3 |
| `check_ns1e.py --corruptions --write-summary` | 27/27 `NORTH_STAR1E_CHECKS_PASS`; corruptions 52/52 caught (1 not applicable), clean null probe | 5,031 (batch) |

Stage totals inside the loop: `acquire` 4,866 s (pure render 4,645 s, mean 28.2 s per two-eye 4096-spp action),
`update` 840 s, `fuse` 327 s, `memory` 183 s, `schedule` 151 s, `preflight` 103 s, `spherical-geometry` 86 s, others
< 25 s each.

## 2. NS1d acceptance

NS1d is ACCEPTED as Outcome 2 (acceptance `25bb929`, fast-forwarded to `main`; post-NS1d roadmap `5aa2231`, the NS1e base).
`source` read the NS1d report at the base and found `NORTH_STAR1D_CROSS_TARGET_MEASUREMENT_MEMORY_ACCEPTED` and
`**Status: ACCEPTED.**` (check 01). The accepted NS1d frozen memory after event 8 and its descriptive next decision are the
NS1e start state (section 4).

## 3. Causal question

> Starting from the accepted NS1d M2-enriched post-NS1c2 state, can the accepted Controller-02 scene machine autonomously
> service the entire coherent ten-entity North-Star scheduler universe to its honest terminal state — fixed physical
> head, fixed recentered policy charts, FSG6f → Cyclopean, PERFECT local correspondence, spherical H0 geometry,
> target-only persistent fusion, instance-keyed cross-target measurement memory, revision-driven natural reactivation,
> NORMAL / DEFERRED / RESIDUE — without controller retuning?

Nothing was tuned. No first-action, first-switch or first-object stop: the run ended only at the machine's terminal (or
would have at the derived cap).

## 4. Exact accepted start state (stage `handoff`; MEASURED; no render)

The live M2 scene was reconstructed independently and verified field by field against the frozen records before any
render (`handoff/handoff.json`, `freeze/handoff-freeze.json`):

- **Records:** the ten entity records of NS1c2 `scene/state-after-step-07.json` (`7e50ecf5…`), references re-scoped to the
  NS1c2 run; context part equal to NS1d's contexts after event 8; maps equal to NS1c2's final maps.
- **Contexts:** `ns1e_core.context_from_record` equals the accepted `ns1c2_core.context_from_record` for all ten
  (evidence, history, visited, gaze, calibration, state).
- **Memory:** nine frozen NS1d patches appended in event order; summary (581,882 samples in 11 ids; per-id provenance;
  snapshot digests) equal to NS1d's after event 8.
- **Probes:** one fresh M2 probe per entity, each equal (policy part, tolerance 0) to the frozen NS1d M2 machine's cached
  probe, with equal revisions.
- **Machine:** a fresh `SceneMachine` resumed with the accepted NS1d resume semantics (`ns1d_core.resume_scene`) equals the
  frozen NS1d M2 machine in every persisted field (order, budget, initialized, dispositions, fixations, statuses, recorded,
  phase, current 202, bout 2, step 8, `quiet_since` {172: 6}, quiet probe, cache revisions and policy parts); no event was
  re-emitted.
- **Next decision** (copy of the machine), equal to NS1d's frozen M2 decision at full precision: attend, target 202,
  `retain`, `fsg6f`, local (−10.899999999999999, 10.5), H0 (−147.62774503449359, 15.922813864915128); world-gaze round
  trip 3.6e-15°; real fixed-head physical-calibration test passed.

| entity | own looks | map surfels | memory own / cross | revision | state | proposal |
|---|---|---|---|---|---|---|
| 9 | 1 | 268 | 0 / 0 | (1, 0) | ACTIONABLE | Cyclopean (−6.0, −2.1) |
| 12 | 1 | 36,126 | 0 / 0 | (1, 0) | ACTIONABLE | Cyclopean (−5.6, −0.6) |
| 123 | 1 | 1,672 | 0 / 5,779 | (1, 5,779) | ACTIONABLE | FSG6f (0.0, +5.0) |
| 129 | 1 | 174 | 0 / 777 | (1, 777) | ACTIONABLE | Cyclopean (+7.1, +5.5) |
| 172 | 9 | 47,892 | 131,695 / 0 | (9, 131,695) | QUIET | — |
| 202 | 2 | 17,371 | 17,447 / 0 | (2, 17,447) | ACTIONABLE | FSG6f (−10.9, +10.5) |
| 204 | 1 | 3,493 | 0 / 0 | (1, 0) | ACTIONABLE | Cyclopean (+5.9, +0.8) |
| 212 | 1 | 2,756 | 0 / 38,197 | (1, 38,197) | ACTIONABLE | Cyclopean (+3.9, +5.2) |
| 230 | 1 | 1,671 | 0 / 0 | (1, 0) | ACTIONABLE | Cyclopean (−5.5, −0.4) |
| 231 | 1 | 2,960 | 0 / 0 | (1, 0) | ACTIONABLE | Cyclopean (+0.6, +0.3) |

**Accepted next action reproduced: YES.** The first executed action (step 8) is exactly that decision.

Gate-wiring harness (stage `gate-harness`; wiring evidence only, on copies): 202's FSG6f proposal through the M2 gate
adapter → admitted (`novel_support_in_predicted_cores`), one P3 call with the real fixed-head H0 sensor at the mapped
world gaze; 9's Cyclopean proposal → rejected (`untraceable_final_support`), no P3 call; the gate refused in NORMAL; the
handoff state unchanged.

## 5. Coherent scheduler universe

Re-derived at run time from the frozen NS1a seed set (`initialized ∧ contributing_patches == 1`, eligibility fields
only): {9, 12, 123, 129, 172, 202, 204, 212, 230, 231} — equal to the expectation. Ids 10 / 110 / 178:
`AMBIGUOUS ORACLE ID — EXCLUDED FROM SCHEDULER`. Other positive observed ids entered the memory only. No object name or
catalog reached control: the checker scanned every run JSON against the 234 names of a sealed catalog (check 05).

## 6. M2 memory semantics

For every scheduler entity i: `effective_geometry_H0(i) = effective_target_geometry(persistent map(i),
memory.snapshot(i).xyz_h)` (accepted, unchanged); `revision(i) = (own looks, measured points of observed id i)`. The
probe cache of the accepted machine is keyed by this revision, so cross-target memory additions invalidate cached probes
and the next refresh re-probes exactly those entities. The checker recomputed every revision from its own memory rebuild
(check 12) and re-drove the machine with them (check 08).

## 7. Fixed charts / fixed physical head

Each entity used its accepted NS1b-construction chart at its ORIGINAL NS1a initialization gaze (recomputed bitwise equal
to NS1c2's); never recentered (every record's chart hash constant; every probe's adapter used its entity's chart; check
06). The physical head stayed in canonical H0: every executed calibration has eye centres (∓0.0315, 0, 0) m, IPD 0.063 m,
the AB1a head pose, the `baseline_projected` tangent frame and the world gaze of the planned local gaze through the fixed
chart; the accepted physical-calibration test passed for every step (real sensor yes, fake local-baseline sensor no;
check 07).

## 8. Derived action cap

From the handoff machine (all ten NORMAL and initialized; fixations within the budget 24):

    MAX_NEW = (24 − 9) + (24 − 2) + 8 · (24 − 1) + 10 = 15 + 22 + 184 + 10 = 231
    ABSOLUTE = 8 + 231 = 239            (passed as decide(action_cap=239))

Equal to the expectation (`handoff/cap.json`; check 21 recomputes it with its own formula).

## 9. Execution / checkpoint architecture

One process per stage, each run once and refusing to rerun, per new global step k (`steps/step-KKK`):
`schedule` (plan freeze, before any render) → `preflight` (Blender, no render) → `acquire` (the one 4096-spp render) →
`freeze-observation` → `perfect-correspondence` → `freeze-correspondence` → `spherical-geometry` → `freeze-geometry` →
`local-oracle-segmentation` → `freeze-identity` → `fuse` (fusion freeze) → `memory` (memory-event freeze) → `update`
(own-look context; `SceneMachine.commit`; refresh; scene checkpoint + checkpoint freeze). Policy stages ran under the
accepted `NoProcessGuard`; measurement / fusion / memory stages under `ns1e_core.ProcessGuard` (the accepted audit events;
amendment 36.2); every stage under `OpenGuard`. The memory ledger was rebuilt from all frozen patches in every process that
needed it and required equal to the previous checkpoint's digest (the read-only replay of completed events). The update
order 8 → 11 is recorded by ordered guard marks in every step (check 18).

## 10. Complete action timeline (MEASURED; `steps/step-KKK/plan/decision.json`, `fusion/fusion.json`, `memory/event.json`)

`sched` = the accepted `schedule_normal` decision; `Cyc` = Cyclopean (`cyclopean_epistemic`); `E` = memory event (event =
global step + 1); `own / cross-coherent mem` = this observation's memory additions of the target / of other coherent
entities (non-scheduler ids not shown); `after` = the target's state after the refresh; `[...]` = machine events of the
commit. Every action is NORMAL; no final residue observation occurred.

    step  target  sched   source  local          H0 (yaw, pitch)      map before -> after (+new)   event  own / cross-coherent mem  after
       8     202  retain  FSG6f   (-10.9, +10.5)  (-147.628, +15.923)   17,371 ->  22,410 (+ 5,039)  E9    15,151 /   7,291  ACTIONABLE
       9     202  retain  Cyc     (-9.5, +0.0)   (-145.866, +26.387)   22,410 ->  32,490 (+10,080)  E10   20,445 /  11,818  ACTIONABLE
      10     202  retain  FSG6f   (-14.5, +0.0)  (-140.589, +24.848)   32,490 ->  56,947 (+24,457)  E11   41,913 /   6,886  ACTIONABLE
      11     202  retain  FSG6f   (-19.5, -5.0)  (-133.413, +27.779)   56,947 ->  87,932 (+30,985)  E12   52,755 /   1,630  ACTIONABLE
      12     202  retain  FSG6f   (-24.5, -10.0)  (-125.929, +30.387)   87,932 -> 122,980 (+35,048)  E13   56,580 /   6,069  ACTIONABLE
      13     202  retain  FSG6f   (-24.5, -5.0)  (-128.275, +25.835)  122,980 -> 134,376 (+11,396)  E14   64,795 /     132  ACTIONABLE
      14     202  retain  FSG6f   (-24.5, +0.0)  (-130.446, +21.248)  134,376 -> 155,224 (+20,848)  E15   65,536 /       0  ACTIONABLE
      15     202  retain  Cyc     (-13.6, -5.1)  (-139.648, +29.959)  155,224 -> 155,224 (+     0)  E16   24,986 /   8,087  ACTIONABLE
      16     202  retain  FSG6f   (-13.6, -0.1)  (-141.493, +25.234)  155,224 -> 155,224 (+     0)  E17   38,479 /   8,065  ACTIONABLE
      17     202  retain  FSG6f   (-18.6, +4.9)  (-138.199, +18.859)  155,224 -> 168,555 (+13,331)  E18   43,583 /       0  ACTIONABLE
      18     202  retain  FSG6f   (-18.6, +9.9)  (-139.971, +14.156)  168,555 -> 178,909 (+10,354)  E19   31,360 /       0  ACTIONABLE
      19     202  retain  FSG6f   (-13.6, +14.9)  (-146.334, +10.952)  178,909 -> 183,122 (+ 4,213)  E20    9,929 /     627  ACTIONABLE
      20     202  retain  Cyc     (-16.5, +4.9)  (-140.286, +19.564)  183,122 -> 183,122 (+     0)  E21   36,914 /      40  ACTIONABLE
      21     202  retain  Cyc     (-12.7, +5.1)  (-144.177, +20.571)  183,122 -> 183,122 (+     0)  E22   26,667 /   3,500  ACTIONABLE
      22     202  retain  Cyc     (-8.5, +10.7)  (-150.048, +16.369)  183,122 -> 183,122 (+     0)  E23   15,167 /  20,318  ACTIONABLE
      23     202  retain  FSG6f   (-8.5, +15.7)  (-151.380, +11.538)  183,122 -> 183,122 (+     0)  E24   10,833 /  26,957  ACTIONABLE
      24     202  retain  Cyc     (-18.5, -9.6)  (-132.455, +32.411)  183,122 -> 183,122 (+     0)  E25   31,253 /   8,343  ACTIONABLE
      25     202  retain  FSG6f   (-13.5, -9.6)  (-137.943, +34.222)  183,122 -> 183,122 (+     0)  E26    8,172 /   6,692  ACTIONABLE
      26     202  retain  Cyc     (-20.7, +15.9)  (-140.082,  +7.818)  183,122 -> 198,922 (+15,800)  E27   30,633 /       0  ACTIONABLE
      27     202  retain  Cyc     (-21.3, -13.9)  (-127.349, +35.243)  198,922 -> 202,736 (+ 3,814)  E28   28,572 /  11,145  ACTIONABLE
      28     202  retain  FSG6f   (-21.3, -18.9)  (-124.614, +39.749)  202,736 -> 203,194 (+   458)  E29   10,131 /  13,649  ACTIONABLE
      29     202  retain  Cyc     (-21.2, -13.9)  (-127.457, +35.284)  203,194 -> 203,194 (+     0)  E30   28,085 /  11,123  QUIET  [quiet:202]
      30     204  switch  Cyc     (+5.9, +0.8)   ( +82.292,  +5.481)    3,493 ->  14,062 (+10,569)  E31   14,509 /  21,634  ACTIONABLE
      31     204  retain  Cyc     (+6.3, +0.0)   ( +82.232,  +4.589)   14,062 ->  14,144 (+    82)  E32   13,231 /  20,084  ACTIONABLE
      32     204  retain  Cyc     (+6.4, +0.0)   ( +82.318,  +4.538)   14,144 ->  14,150 (+     6)  E33   13,234 /  19,706  ACTIONABLE
      33     204  retain  Cyc     (+6.4, -0.1)   ( +82.268,  +4.452)   14,150 ->  14,150 (+     0)  E34   13,083 /  19,646  ACTIONABLE
      34     204  retain  Cyc     (+6.3, +0.1)   ( +82.283,  +4.675)   14,150 ->  14,150 (+     0)  E35   13,394 /  20,131  ACTIONABLE
      35     204  retain  Cyc     (+6.4, -0.2)   ( +82.217,  +4.365)   14,150 ->  14,155 (+     5)  E36   12,923 /  19,545  ACTIONABLE
      36     204  retain  Cyc     (+6.5, -0.2)   ( +82.303,  +4.315)   14,155 ->  14,161 (+     6)  E37   12,929 /  19,153  ACTIONABLE
      37     204  retain  Cyc     (+6.2, +0.2)   ( +82.247,  +4.812)   14,161 ->  14,161 (+     0)  E38   13,538 /  20,556  ACTIONABLE
      38     204  retain  Cyc     (+6.3, +0.2)   ( +82.333,  +4.761)   14,161 ->  14,162 (+     1)  E39   13,555 /  20,153  ACTIONABLE
      39     204  retain  Cyc     (+6.5, -0.3)   ( +82.253,  +4.229)   14,162 ->  14,163 (+     1)  E40   12,772 /  19,077  ACTIONABLE
      40     204  retain  Cyc     (+6.6, -0.3)   ( +82.339,  +4.178)   14,163 ->  14,176 (+    13)  E41   12,773 /  18,697  ACTIONABLE
      41     204  retain  Cyc     (+6.1, +0.3)   ( +82.211,  +4.949)   14,176 ->  14,176 (+     0)  E42   13,687 /  20,959  ACTIONABLE
      42     204  retain  Cyc     (+6.2, +0.3)   ( +82.298,  +4.898)   14,176 ->  14,176 (+     0)  E43   13,708 /  20,554  ACTIONABLE
      43     204  retain  Cyc     (+6.5, -0.4)   ( +82.202,  +4.142)   14,176 ->  14,177 (+     1)  E44   12,623 /  18,980  ACTIONABLE
      44     204  retain  Cyc     (+6.6, -0.4)   ( +82.288,  +4.092)   14,177 ->  14,180 (+     3)  E45   12,620 /  18,602  ACTIONABLE
      45     204  retain  Cyc     (+6.1, +0.4)   ( +82.262,  +5.035)   14,180 ->  14,180 (+     0)  E46   13,854 /  20,984  ACTIONABLE
      46     204  retain  Cyc     (+6.6, -0.5)   ( +82.238,  +4.006)   14,180 ->  14,183 (+     3)  E47   12,474 /  18,528  ACTIONABLE
      47     204  retain  Cyc     (+6.7, -0.5)   ( +82.324,  +3.955)   14,183 ->  14,189 (+     6)  E48   12,470 /  18,154  ACTIONABLE
      48     204  retain  Cyc     (+6.0, +0.5)   ( +82.226,  +5.172)   14,189 ->  14,189 (+     0)  E49   13,996 /  21,330  ACTIONABLE
      49     204  retain  Cyc     (+6.1, +0.5)   ( +82.313,  +5.121)   14,189 ->  14,189 (+     0)  E50   14,035 /  20,919  ACTIONABLE
      50     204  retain  Cyc     (+6.7, -0.6)   ( +82.273,  +3.869)   14,189 ->  14,191 (+     2)  E51   12,327 /  18,072  ACTIONABLE
      51     204  retain  Cyc     (+5.9, +0.6)   ( +82.190,  +5.309)   14,191 ->  14,192 (+     1)  E52   14,156 /  21,700  ACTIONABLE
      52     204  retain  Cyc     (+6.0, +0.6)   ( +82.277,  +5.258)   14,192 ->  14,192 (+     0)  E53   14,179 /  21,320  ACTIONABLE/DEFERRED:ordinary_budget  [deferred:204]
      53     212  switch  Cyc     (+3.9, +5.2)   (-161.606, +24.359)    2,756 ->  30,657 (+27,901)  E54   30,303 /   8,691  ACTIONABLE
      54     212  retain  FSG6f   (+8.9, +5.2)   (-167.034, +25.054)   30,657 ->  43,076 (+12,419)  E55   29,735 /   8,603  ACTIONABLE
      55     212  retain  FSG6f   (+13.9, +5.2)  (-172.518, +25.510)   43,076 ->  55,230 (+12,154)  E56   30,003 /     523  ACTIONABLE
      56     212  retain  FSG6f   (+18.9, +5.2)  (-178.036, +25.722)   55,230 ->  67,281 (+12,051)  E57   29,952 /       0  ACTIONABLE
      57     212  retain  FSG6f   (+23.9, +5.2)  (+176.438, +25.686)   67,281 ->  79,332 (+12,051)  E58   29,952 /       0  ACTIONABLE
      58     212  retain  FSG6f   (+23.9, +10.2)  (+176.609, +20.689)   79,332 -> 105,853 (+26,521)  E59   57,277 /       0  ACTIONABLE
      59     212  retain  FSG6f   (+18.9, +10.2)  (-178.130, +20.723)  105,853 -> 116,279 (+10,426)  E60   57,300 /       0  ACTIONABLE
      60     212  retain  FSG6f   (+13.9, +10.2)  (-172.876, +20.521)  116,279 -> 126,528 (+10,249)  E61   57,328 /     423  ACTIONABLE
      61     212  retain  FSG6f   (+8.9, +10.2)  (-167.650, +20.086)  126,528 -> 136,779 (+10,251)  E62   56,965 /   2,820  ACTIONABLE
      62     212  retain  FSG6f   (+3.9, +10.2)  (-162.469, +19.424)  136,779 -> 147,568 (+10,789)  E63   57,659 /   2,599  ACTIONABLE
      63     212  retain  FSG6f   (-1.1, +15.2)  (-158.383, +13.640)  147,568 -> 188,119 (+40,551)  E64   64,109 /   1,399  ACTIONABLE
      64     212  retain  FSG6f   (-6.1, +15.2)  (-153.546, +12.593)  188,119 -> 189,946 (+ 1,827)  E65   38,615 /  11,303  ACTIONABLE
      65     212  retain  Cyc     (-4.4, +5.5)   (-152.848, +22.414)  189,946 -> 193,581 (+ 3,635)  E66   19,897 /  19,901  ACTIONABLE
      66     212  retain  Cyc     (+10.3, +16.5)  (-169.749, +13.961)  193,581 -> 223,976 (+30,395)  E67   65,536 /       0  ACTIONABLE
      67     212  retain  Cyc     (+17.2, +16.5)  (-176.558, +14.384)  223,976 -> 242,132 (+18,156)  E68   65,536 /       0  ACTIONABLE
      68     212  retain  FSG6f   (+22.2, +16.5)  (+178.492, +14.427)  242,132 -> 255,013 (+12,881)  E69   65,536 /       0  QUIET  [quiet:212]
      69     230  switch  Cyc     (-5.5, -0.4)   ( +71.701, +10.103)    1,671 ->   5,412 (+ 3,741)  E70    5,480 /  30,715  ACTIONABLE
      70     230  retain  Cyc     (-5.7, +0.0)   ( +71.720, +10.550)    5,412 ->   5,648 (+   236)  E71    5,503 /  30,731  ACTIONABLE
      71     230  retain  Cyc     (-5.6, +0.0)   ( +71.809, +10.501)    5,648 ->   5,653 (+     5)  E72    5,474 /  31,017  ACTIONABLE
      72     230  retain  Cyc     (-5.6, -0.1)   ( +71.760, +10.414)    5,653 ->   5,654 (+     1)  E73    5,481 /  30,886  ACTIONABLE
      73     230  retain  Cyc     (-5.5, -0.1)   ( +71.849, +10.365)    5,654 ->   5,655 (+     1)  E74    5,438 /  31,089  ACTIONABLE
      74     230  retain  Cyc     (-5.7, +0.1)   ( +71.770, +10.637)    5,655 ->   5,655 (+     0)  E75    5,497 /  30,884  ACTIONABLE
      75     230  retain  Cyc     (-5.6, +0.1)   ( +71.859, +10.589)    5,655 ->   5,656 (+     1)  E76    5,452 /  31,152  ACTIONABLE
      76     230  retain  Cyc     (-5.5, -0.2)   ( +71.800, +10.278)    5,656 ->   5,656 (+     0)  E77    5,446 /  30,958  ACTIONABLE
      77     230  retain  Cyc     (-5.8, +0.2)   ( +71.730, +10.773)    5,656 ->   5,703 (+    47)  E78    5,496 /  30,706  ACTIONABLE
      78     230  retain  Cyc     (-5.7, +0.2)   ( +71.819, +10.725)    5,703 ->   5,703 (+     0)  E79    5,471 /  30,978  ACTIONABLE
      79     230  retain  Cyc     (-5.5, -0.3)   ( +71.750, +10.191)    5,703 ->   5,703 (+     0)  E80    5,455 /  30,843  ACTIONABLE
      80     230  retain  Cyc     (-5.4, -0.3)   ( +71.839, +10.142)    5,703 ->   5,704 (+     1)  E81    5,428 /  31,058  ACTIONABLE
      81     230  retain  Cyc     (-5.8, +0.3)   ( +71.780, +10.861)    5,704 ->   5,705 (+     1)  E82    5,464 /  30,846  ACTIONABLE
      82     230  retain  Cyc     (-5.4, -0.4)   ( +71.790, +10.055)    5,705 ->   5,705 (+     0)  E83    5,442 /  30,879  ACTIONABLE
      83     230  retain  Cyc     (-5.3, -0.4)   ( +71.879, +10.006)    5,705 ->   5,705 (+     0)  E84    5,414 /  31,155  ACTIONABLE
      84     230  retain  Cyc     (-5.9, +0.4)   ( +71.740, +10.997)    5,705 ->   5,743 (+    38)  E85    5,453 /  30,732  ACTIONABLE
      85     230  retain  Cyc     (-5.8, +0.4)   ( +71.829, +10.948)    5,743 ->   5,743 (+     0)  E86    5,426 /  30,981  ACTIONABLE
      86     230  retain  Cyc     (-5.3, -0.5)   ( +71.830,  +9.919)    5,743 ->   5,751 (+     8)  E87    5,430 /  30,958  ACTIONABLE
      87     230  retain  Cyc     (-5.9, +0.5)   ( +71.789, +11.084)    5,751 ->   5,751 (+     0)  E88    5,388 /  30,896  ACTIONABLE
      88     230  retain  Cyc     (-5.3, -0.6)   ( +71.780,  +9.831)    5,751 ->   5,779 (+    28)  E89    5,438 /  30,785  ACTIONABLE
      89     230  retain  Cyc     (-5.2, -0.6)   ( +71.869,  +9.783)    5,779 ->   5,779 (+     0)  E90    5,380 /  30,996  ACTIONABLE
      90     230  retain  Cyc     (-6.0, +0.6)   ( +71.750, +11.220)    5,779 ->   5,790 (+    11)  E91    5,383 /  30,777  ACTIONABLE
      91     230  retain  Cyc     (-5.9, +0.6)   ( +71.839, +11.172)    5,790 ->   5,790 (+     0)  E92    5,342 /  30,988  ACTIONABLE/DEFERRED:ordinary_budget  [deferred:230]
      92     231  switch  Cyc     (-0.2, -0.2)   ( +76.475,  +7.676)    2,960 ->   3,041 (+    81)  E93    3,038 /  40,857  ACTIONABLE
      93     231  retain  Cyc     (-0.1, -0.2)   ( +76.562,  +7.626)    3,041 ->   3,041 (+     0)  E94    3,008 /  40,977  ACTIONABLE
      94     231  retain  Cyc     (-0.3, -0.3)   ( +76.337,  +7.639)    3,041 ->   3,051 (+    10)  E95    3,093 /  40,491  ACTIONABLE
      95     231  retain  Cyc     (-0.2, -0.3)   ( +76.425,  +7.589)    3,051 ->   3,051 (+     0)  E96    3,073 /  40,621  ACTIONABLE
      96     231  retain  Cyc     (-0.1, -0.3)   ( +76.512,  +7.539)    3,051 ->   3,051 (+     0)  E97    3,029 /  40,727  ACTIONABLE
      97     231  retain  Cyc     (+0.0, -0.3)   ( +76.600,  +7.490)    3,051 ->   3,051 (+     0)  E98    3,002 /  40,847  ACTIONABLE
      98     231  retain  Cyc     (-0.5, -0.4)   ( +76.112,  +7.651)    3,051 ->   3,118 (+    67)  E99    3,142 /  40,010  ACTIONABLE
      99     231  retain  Cyc     (-0.4, -0.4)   ( +76.199,  +7.601)    3,118 ->   3,118 (+     0)  E100   3,128 /  40,118  ACTIONABLE
     100     231  retain  Cyc     (-0.3, -0.4)   ( +76.287,  +7.552)    3,118 ->   3,118 (+     0)  E101   3,112 /  40,246  ACTIONABLE
     101     231  retain  Cyc     (+0.0, -0.4)   ( +76.550,  +7.403)    3,118 ->   3,118 (+     0)  E102   3,007 /  40,593  ACTIONABLE
     102     231  retain  Cyc     (+0.1, -0.4)   ( +76.637,  +7.353)    3,118 ->   3,121 (+     3)  E103   2,981 /  40,652  ACTIONABLE
     103     231  retain  Cyc     (-0.7, -0.5)   ( +75.886,  +7.663)    3,121 ->   3,168 (+    47)  E104   3,181 /  39,498  ACTIONABLE
     104     231  retain  Cyc     (-0.6, -0.5)   ( +75.974,  +7.614)    3,168 ->   3,169 (+     1)  E105   3,185 /  39,601  ACTIONABLE
     105     231  retain  Cyc     (-0.5, -0.5)   ( +76.062,  +7.564)    3,169 ->   3,169 (+     0)  E106   3,161 /  39,758  ACTIONABLE
     106     231  retain  Cyc     (+0.0, -0.5)   ( +76.499,  +7.316)    3,169 ->   3,169 (+     0)  E107   3,007 /  40,270  ACTIONABLE
     107     231  retain  Cyc     (-0.8, -0.6)   ( +75.749,  +7.626)    3,169 ->   3,194 (+    25)  E108   3,242 /  39,058  ACTIONABLE
     108     231  retain  Cyc     (-0.7, -0.6)   ( +75.836,  +7.576)    3,194 ->   3,194 (+     0)  E109   3,225 /  39,201  ACTIONABLE
     109     231  retain  Cyc     (+0.0, -0.6)   ( +76.449,  +7.229)    3,194 ->   3,195 (+     1)  E110   3,038 /  40,001  ACTIONABLE
     110     231  retain  Cyc     (+0.1, -0.6)   ( +76.537,  +7.180)    3,195 ->   3,195 (+     0)  E111   3,012 /  40,088  ACTIONABLE
     111     231  retain  Cyc     (-1.0, -0.7)   ( +75.523,  +7.638)    3,195 ->   3,251 (+    56)  E112   3,337 /  38,570  ACTIONABLE
     112     231  retain  Cyc     (-0.9, -0.7)   ( +75.611,  +7.588)    3,251 ->   3,252 (+     1)  E113   3,313 /  38,721  ACTIONABLE
     113     231  retain  Cyc     (-0.8, -0.7)   ( +75.699,  +7.539)    3,252 ->   3,252 (+     0)  E114   3,282 /  38,776  ACTIONABLE
     114     231  retain  Cyc     (+0.1, -0.7)   ( +76.487,  +7.093)    3,252 ->   3,253 (+     1)  E115   3,008 /  39,768  ACTIONABLE/DEFERRED:ordinary_budget  [deferred:231]
     115       9  switch  Cyc     (-6.9, +0.0)   ( +70.651, +11.130)      268 ->   7,761 (+ 7,493)  E116   7,776 /  26,181  ACTIONABLE
     116       9  retain  Cyc     (-6.8, +0.0)   ( +70.740, +11.082)    7,761 ->   7,768 (+     7)  E117   7,663 /  26,511  ACTIONABLE
     117       9  retain  Cyc     (-6.8, -0.1)   ( +70.691, +10.994)    7,768 ->   7,818 (+    50)  E118   7,702 /  26,354  ACTIONABLE
     118       9  retain  Cyc     (-6.7, -0.1)   ( +70.780, +10.946)    7,818 ->   7,823 (+     5)  E119   7,573 /  26,679  ACTIONABLE
     119       9  retain  Cyc     (-6.9, +0.1)   ( +70.700, +11.217)    7,823 ->   7,826 (+     3)  E120   7,764 /  26,345  ACTIONABLE
     120       9  retain  Cyc     (-6.7, -0.2)   ( +70.731, +10.858)    7,826 ->   7,871 (+    45)  E121   7,633 /  26,526  ACTIONABLE
     121       9  retain  Cyc     (-6.9, +0.2)   ( +70.749, +11.305)    7,871 ->   7,872 (+     1)  E122   7,652 /  26,476  ACTIONABLE
     122       9  retain  Cyc     (-6.7, -0.3)   ( +70.682, +10.771)    7,872 ->   7,914 (+    42)  E123   7,656 /  26,361  ACTIONABLE
     123       9  retain  Cyc     (-6.6, -0.3)   ( +70.771, +10.722)    7,914 ->   7,918 (+     4)  E124   7,507 /  26,691  ACTIONABLE
     124       9  retain  Cyc     (-7.0, +0.3)   ( +70.709, +11.441)    7,918 ->   7,957 (+    39)  E125   7,741 /  26,250  ACTIONABLE
     125       9  retain  Cyc     (-6.9, +0.3)   ( +70.798, +11.393)    7,957 ->   7,957 (+     0)  E126   7,623 /  26,595  ACTIONABLE
     126       9  retain  Cyc     (-6.6, -0.4)   ( +70.722, +10.635)    7,957 ->   7,997 (+    40)  E127   7,564 /  26,555  ACTIONABLE
     127       9  retain  Cyc     (-6.5, -0.4)   ( +70.811, +10.587)    7,997 ->   8,003 (+     6)  E128   7,448 /  26,873  ACTIONABLE
     128       9  retain  Cyc     (-7.1, +0.4)   ( +70.669, +11.577)    8,003 ->   8,078 (+    75)  E129   7,853 /  26,068  ACTIONABLE
     129       9  retain  Cyc     (-7.0, +0.4)   ( +70.758, +11.529)    8,078 ->   8,078 (+     0)  E130   7,695 /  26,368  ACTIONABLE
     130       9  retain  Cyc     (-6.5, -0.5)   ( +70.762, +10.499)    8,078 ->   8,122 (+    44)  E131   7,475 /  26,693  ACTIONABLE
     131       9  retain  Cyc     (-7.1, +0.5)   ( +70.718, +11.664)    8,122 ->   8,142 (+    20)  E132   7,781 /  26,132  ACTIONABLE
     132       9  retain  Cyc     (-6.5, -0.6)   ( +70.713, +10.411)    8,142 ->   8,181 (+    39)  E133   7,501 /  26,542  ACTIONABLE
     133       9  retain  Cyc     (-6.4, -0.6)   ( +70.802, +10.363)    8,181 ->   8,185 (+     4)  E134   7,366 /  26,904  ACTIONABLE
     134       9  retain  Cyc     (-7.2, +0.6)   ( +70.678, +11.800)    8,185 ->   8,218 (+    33)  E135   7,869 /  25,889  ACTIONABLE
     135       9  retain  Cyc     (-7.1, +0.6)   ( +70.767, +11.752)    8,218 ->   8,218 (+     0)  E136   7,710 /  26,254  ACTIONABLE
     136       9  retain  Cyc     (-6.4, -0.7)   ( +70.753, +10.276)    8,218 ->   8,258 (+    40)  E137   7,363 /  26,777  ACTIONABLE
     137       9  retain  Cyc     (-6.3, -0.7)   ( +70.842, +10.227)    8,258 ->   8,264 (+     6)  E138   7,215 /  27,124  ACTIONABLE/DEFERRED:ordinary_budget  [deferred:9]
     138      12  switch  Cyc     (-5.6, -0.6)   ( +71.514,  +9.977)   36,126 ->  38,045 (+ 1,919)  E139  21,026 /  14,673  ACTIONABLE
     139      12  retain  Cyc     (-5.6, -0.7)   ( +71.465,  +9.889)   38,045 ->  38,046 (+     1)  E140  20,855 /  14,684  ACTIONABLE
     140      12  retain  Cyc     (-5.5, -0.7)   ( +71.554,  +9.841)   38,046 ->  38,047 (+     1)  E141  21,206 /  14,489  ACTIONABLE
     141      12  retain  Cyc     (-5.7, -0.6)   ( +71.425, +10.025)   38,047 ->  38,047 (+     0)  E142  20,683 /  14,814  ACTIONABLE
     142      12  retain  Cyc     (-5.7, -0.5)   ( +71.474, +10.112)   38,047 ->  38,057 (+    10)  E143  20,838 /  14,822  ACTIONABLE
     143      12  retain  Cyc     (-5.7, -0.4)   ( +71.523, +10.200)   38,057 ->  38,093 (+    36)  E144  21,015 /  14,792  ACTIONABLE
     144      12  retain  Cyc     (-5.7, -0.3)   ( +71.573, +10.287)   38,093 ->  38,110 (+    17)  E145  21,170 /  14,731  ACTIONABLE
     145      12  retain  Cyc     (-5.5, -0.8)   ( +71.504,  +9.753)   38,110 ->  38,134 (+    24)  E146  21,032 /  14,467  ACTIONABLE
     146      12  retain  Cyc     (-5.8, -0.3)   ( +71.484, +10.336)   38,134 ->  38,134 (+     0)  E147  20,814 /  14,937  ACTIONABLE
     147      12  retain  Cyc     (-5.8, -0.2)   ( +71.533, +10.423)   38,134 ->  38,157 (+    23)  E148  20,939 /  14,865  ACTIONABLE
     148      12  retain  Cyc     (-5.5, -0.9)   ( +71.455,  +9.666)   38,157 ->  38,160 (+     3)  E149  20,860 /  14,445  ACTIONABLE
     149      12  retain  Cyc     (-5.9, -0.2)   ( +71.444, +10.472)   38,160 ->  38,160 (+     0)  E150  20,598 /  15,048  ACTIONABLE
     150      12  retain  Cyc     (-5.9, -0.1)   ( +71.493, +10.559)   38,160 ->  38,191 (+    31)  E151  20,765 /  14,987  ACTIONABLE
     151      12  retain  Cyc     (-5.9, +0.0)   ( +71.543, +10.647)   38,191 ->  38,203 (+    12)  E152  20,893 /  14,948  ACTIONABLE
     152      12  retain  Cyc     (-5.5, -1.0)   ( +71.406,  +9.578)   38,203 ->  38,220 (+    17)  E153  20,647 /  14,462  ACTIONABLE
     153      12  retain  Cyc     (-5.4, -1.0)   ( +71.495,  +9.530)   38,220 ->  38,221 (+     1)  E154  20,997 /  14,298  ACTIONABLE
     154      12  retain  Cyc     (-6.0, +0.0)   ( +71.453, +10.695)   38,221 ->  38,221 (+     0)  E155  20,558 /  15,145  ACTIONABLE
     155      12  retain  Cyc     (-6.0, +0.1)   ( +71.503, +10.783)   38,221 ->  38,266 (+    45)  E156  20,675 /  15,067  ACTIONABLE
     156      12  retain  Cyc     (-5.4, -1.1)   ( +71.446,  +9.442)   38,266 ->  38,270 (+     4)  E157  20,793 /  14,282  ACTIONABLE
     157      12  retain  Cyc     (-5.3, -1.1)   ( +71.535,  +9.394)   38,270 ->  38,270 (+     0)  E158  21,110 /  14,108  ACTIONABLE
     158      12  retain  Cyc     (-6.1, +0.1)   ( +71.414, +10.831)   38,270 ->  38,270 (+     0)  E159  20,309 /  15,274  ACTIONABLE
     159      12  retain  Cyc     (-6.1, +0.2)   ( +71.463, +10.919)   38,270 ->  38,361 (+    91)  E160  20,468 /  15,193  ACTIONABLE
     160      12  retain  Cyc     (-6.1, +0.3)   ( +71.512, +11.006)   38,361 ->  38,402 (+    41)  E161  20,625 /  15,119  ACTIONABLE/DEFERRED:ordinary_budget  [deferred:12]
     161     123  switch  FSG6f   (+0.0, +5.0)   (-157.381, +23.854)    1,672 ->   1,674 (+     2)  E162   1,639 /  35,872  ACTIONABLE
     162     123  retain  FSG6f   (-5.0, +5.0)   (-152.090, +22.757)    1,674 ->   6,194 (+ 4,520)  E163   6,291 /  31,772  ACTIONABLE
     163     123  retain  Cyc     (-7.4, -0.5)   (-147.969, +27.456)    6,194 ->  10,705 (+ 4,511)  E164  10,762 /  13,826  ACTIONABLE
     164     123  retain  Cyc     (-11.5, -5.6)  (-141.752, +31.115)   10,705 ->  12,189 (+ 1,484)  E165   7,650 /  15,060  ACTIONABLE
     165     123  retain  Cyc     (-16.7, -11.6)  (-133.500, +34.936)   12,189 ->  19,665 (+ 7,476)  E166   8,520 /  14,249  ACTIONABLE
     166     123  retain  Cyc     (-20.0, -15.9)  (-127.716, +37.587)   19,665 ->  25,122 (+ 5,457)  E167  13,167 /  15,594  ACTIONABLE
     167     123  retain  FSG6f   (-15.0, -15.9)  (-133.337, +39.540)   25,122 ->  25,122 (+     0)  E168   4,669 /   1,081  ACTIONABLE
     168     123  retain  Cyc     (-23.5, -19.8)  (-121.680, +39.603)   25,122 ->  30,341 (+ 5,219)  E169  14,218 /  15,672  ACTIONABLE
     169     123  retain  Cyc     (-23.6, -19.9)  (-121.512, +39.647)   30,341 ->  30,341 (+     0)  E170  14,216 /  15,701  ACTIONABLE
     170     123  retain  Cyc     (-23.5, -19.9)  (-121.620, +39.691)   30,341 ->  30,341 (+     0)  E171  14,220 /  15,283  ACTIONABLE
     171     123  retain  Cyc     (-23.6, -20.0)  (-121.451, +39.736)   30,341 ->  30,341 (+     0)  E172  14,224 /  15,312  QUIET  [quiet:123]
     172     129  switch  Cyc     (+7.1, +5.4)   (-165.102, +24.633)      174 ->     747 (+   573)  E173     768 /  38,771  QUIET  [quiet:129]

The terminal decision (global step 173) is in section 17.

## 11. Per-entity trajectories (MEASURED)

| id | initial map | final map | new actions | own looks | FSG6f | Cyclopean | zero-new-surfel looks | own memory | cross memory | effective | final revision | terminal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 9 (rank 1) | 268 | 8,264 | 23 | 24 | 0 | 23 | 3 | 175,130 | 288,717 | 472,111 | (24, 463,847) | ACTIONABLE / FINALIZED: final_probe_rejected |
| 12 (rank 1) | 36,126 | 38,402 | 23 | 24 | 0 | 23 | 6 | 478,876 | 2,142,902 | 2,660,180 | (24, 2,621,778) | ACTIONABLE / FINALIZED: final_probe_rejected |
| 123 | 1,672 | 30,341 | 11 | 12 | 3 | 8 | 4 | 109,576 | 109,241 | 249,158 | (12, 218,817) | QUIET / NORMAL |
| 129 | 174 | 747 | 1 | 2 | 0 | 1 | 0 | 768 | 4,744 | 6,259 | (2, 5,512) | QUIET / NORMAL |
| 172 | 47,892 | 47,892 | 0 | 9 | 0 | 0 | 0 | 131,695 | 32,865 | 212,452 | (9, 164,560) | QUIET / NORMAL |
| 202 | 17,371 | 203,194 | 22 | 24 | 13 | 9 | 9 | 709,386 | 165,081 | 1,077,661 | (24, 874,467) | QUIET / NORMAL |
| 204 (rank 1) | 3,493 | 14,192 | 23 | 24 | 0 | 23 | 9 | 306,070 | 51,008 | 371,270 | (24, 357,078) | ACTIONABLE / FINALIZED: final_probe_rejected |
| 212 | 2,756 | 255,013 | 16 | 17 | 12 | 4 | 0 | 755,703 | 169,650 | 1,180,366 | (17, 925,353) | QUIET / NORMAL |
| 230 (rank 1) | 1,671 | 5,790 | 23 | 24 | 0 | 23 | 10 | 125,181 | 312,496 | 443,467 | (24, 437,677) | ACTIONABLE / FINALIZED: final_probe_rejected |
| 231 (rank 1) | 2,960 | 3,253 | 23 | 24 | 0 | 23 | 12 | 71,604 | 242,617 | 317,474 | (24, 314,221) | ACTIONABLE / FINALIZED: final_probe_rejected |

Totals: 165 new actions = 28 FSG6f + 137 Cyclopean; 53 looks added zero new surfels (all 165 fusions were `FUSED`, ≥ 100
target points; none `RETAINED_NOT_FUSED`).

- **202 (current at the handoff)** — retained steps 8–29 (22 actions: 13 FSG6f, 9 Cyclopean); map 17,371 → 203,194;
  FSG6f `no_frontier` and Cyclopean `attention_complete`: **naturally QUIET exactly at its 24th own look** (step 29), so it
  was QUIET, not DEFERRED. (212, 123 and 129 went QUIET the same way.)
- **212** — 16 actions (12 FSG6f, 4 Cyclopean), map 2,756 → 255,013, naturally QUIET at 17 looks (step 68).
- **123** — 11 actions (3 FSG6f, 8 Cyclopean), map 1,672 → 30,341, naturally QUIET at 12 looks (step 171). Its first
  action was the memory-changed FSG6f proposal (0°, +5°) that NS1d had recorded.
- **129** — one Cyclopean action (+7.1°, +5.4°) (map 174 → 747), then QUIET (step 172). NS1d had recorded its
  memory-changed proposal as (+7.1°, +5.5°); further cross-target memory (4,744 samples by then) moved it by 0.1°.
- **172** — never selected (QUIET at the handoff); re-probed 9 times by cross-target memory; stayed QUIET.
- **Rank-1 9, 12, 204, 230, 231** — 23 Cyclopean actions each (section 14), DEFERRED at 24, finalized in RESIDUE.

## 12. Scene switches (MEASURED)

| global step | from → to | reason | the new target's first action |
|---|---|---|---|
| 30 | 202 → 204 | switch (202 QUIET) | Cyclopean (+5.9, +0.8) |
| 53 | 204 → 212 | switch (204 DEFERRED) | Cyclopean (+3.9, +5.2) |
| 69 | 212 → 230 | switch (212 QUIET) | Cyclopean (−5.5, −0.4) |
| 92 | 230 → 231 | switch (230 DEFERRED) | Cyclopean (−0.2, −0.2) |
| 115 | 231 → 9 | switch (wrap to the lowest serviceable id) | Cyclopean (−6.9, 0.0) |
| 138 | 9 → 12 | switch | Cyclopean (−5.6, −0.6) |
| 161 | 12 → 123 | switch | FSG6f (0.0, +5.0) |
| 172 | 123 → 129 | switch | Cyclopean (+7.1, +5.4) |

Every switch is `schedule_normal`'s deterministic choice (the next NORMAL-serviceable id above the current one, wrapping
to the lowest), reproduced by the checker's independent re-drive (check 08). No switch carried the
`natural_reactivation` reason. 10 attention bouts in total (bout 2 at the handoff → 10).

## 13. Natural reactivations

    NO NATURAL REACTIVATION MEASURED

The mechanism was exercised but never produced a reactivation:
- 567 revision changes (165 targets + 402 cross-target); 402 cross-target re-probes;
- 27 of those re-probed entities that were QUIET at the time: 172 ×9 (triggered by looks at 212 ×6, 123 ×2, 129 ×1),
  202 ×14 (212 ×3, 123 ×11) and 212 ×4 (123 ×3, 129 ×1). Example: step 53 (212 active) changed 172's revision (9, 131,695) →
  (9, 139,579); 172 was re-probed and stayed QUIET.
- Every re-probed QUIET entity stayed QUIET, so no `natural_reactivation` event, no reactivation switch. The machine has
  no reactivation call (code scan, check 19).

## 14. Rank-1 behavior (MEASURED; `rank1-diagnostic.png`)

The seam was observed, not fixed.

| id | planar support at the handoff | first selected (step) | source / local gaze | M2 effective at selection | NS1e own looks | spherical target points per look | planar controller support per look | terminal |
|---|---|---|---|---|---|---|---|---|
| 9 | 0 | 115 | Cyclopean (−6.9, 0.0) | 145,668 | 23 | 7,215–7,869 (total 175,130) | 0 every look | FINALIZED: final_probe_rejected |
| 12 | 0 | 138 | Cyclopean (−5.6, −0.6) | 2,179,028 | 23 | 20,309–21,206 (total 478,876) | 27,687–32,740 (total 688,604) | FINALIZED: final_probe_rejected |
| 204 | 0 | 30 | Cyclopean (+5.9, +0.8) | 3,493 | 23 | 12,327–14,509 (total 306,070) | 0 every look | FINALIZED: final_probe_rejected |
| 230 | 0 | 69 | Cyclopean (−5.5, −0.4) | 1,671 | 23 | 5,342–5,503 (total 125,181) | 0 every look | FINALIZED: final_probe_rejected |
| 231 | 0 | 92 | Cyclopean (−0.2, −0.2) | 110,290 | 23 | 2,981–3,337 (total 71,604) | 0 every look | FINALIZED: final_probe_rejected |

- The North-Star spherical path measured each rank-1 target at every look (PERFECT correspondence; every look was
  `FUSED`); their persistent maps grew (9: 268 → 8,264; 204: 3,493 → 14,192; 230: 1,671 → 5,790; 231: 2,960 → 3,253; 12:
  36,126 → 38,402).
- For 9, 204, 230 and 231 the inherited planar controller-state matcher gave **zero** target support at every one of
  their 24 looks. For 12 it gave zero at its NS1a look but 27,687–32,740 at each NS1e look.
- All five never received an FSG6f proposal: each ran 23 Cyclopean actions with near-identical local gazes (all 23
  within a box of at most 1.1° in yaw and 1.4° in pitch) until the 24-look budget, then DEFERRED. Many of those looks added few or no new surfels
  (zero-new looks: 9: 3, 12: 6, 204: 9, 230: 10, 231: 12).
- This is a measured result of the seam (repeated Cyclopean actions, deferral, residue), preserved without retuning.
  Whether it is caused by the planar zero support (4 entities) or by another limitation (12 had planar support) is not
  established by NS1e.

## 15. Memory growth and provenance (MEASURED)

| | samples |
|---|---|
| start (NS1d, events 0–8) | 581,882 in 11 ids |
| NS1e additions (events 9–173) | 7,700,338 = own target 2,714,847 + coherent cross-target 3,474,568 + non-scheduler 1,510,923 |
| final | **8,282,220 samples in 40 observed ids** (174 memory events) |
| final coherent own / cross | 2,863,989 / 3,519,321 (55.1 % cross-target of the coherent memory) |
| final non-scheduler ids (30 ids) | 1,898,910 — 110 `AMBIGUOUS ORACLE ID — EXCLUDED`: 1,241,941; 10 (ambiguous): 24,888; 207: 184,844; 144: 145,662; 229: 69,263; others smaller |
| NS1e additions by active target | 202: 1,427,106; 212: 1,043,538; 231: 997,728; 204: 958,620; 230: 849,357; 12: 829,647; 9: 810,400; 123: 718,854; 129: 65,088 |

- Every observation was appended exactly once (unique observation keys), in event order, event = global step + 1,
  `source_active_target_id` = the active target; instance 0 never stored; the ambiguous ids 10 / 110 stored but never
  scheduled (178 never observed). Checks 12, 16.
- The 55.1 % cross-target share is descriptive and not comparable with Controller-01's 70.7 % (different looks, objects
  and scene coverage).
- Example of cross-target flow: entity 12 (rank 1) holds 2,142,902 cross-target samples, from the looks at 231
  (812,106), 230 (505,109), 204 (421,332) and 9 (404,355): the rank-1 entities share one region of the scene (H0 yaw
  about +64° to +91°).

## 16. Persistent map growth (MEASURED)

Ten maps 114,383 → 607,088 surfels (`final-coherent-persistent-points.ply`). All 165 target-only fusions used the accepted
12-mm H0 surface map with an exact replay; matched distances: median of per-step medians 1.71 mm, maximum 11.99999 mm
(≤ the association radius). No map ever held another entity's id or patch; non-target maps were unchanged at every step
(check 15 re-fused every step bitwise).

## 17. NORMAL / DEFERRED / RESIDUE phase history (MEASURED)

    NORMAL   global steps 8–172   165 ordinary actions; NORMAL final-gate calls 0
    deferred (event, step): 204 @52, 230 @91, 231 @114, 9 @137, 12 @160 — each ACTIONABLE at its 24th own look
    QUIET    (event, step): 202 @29, 212 @68, 123 @171, 129 @172   (172 QUIET since the handoff)
    RESIDUE  from global step 173: schedule_normal returned None with deferred [9, 12, 204, 230, 231]
             one residue decision per deferred entity, ascending id (section 18); no final observation
    CLOSED   global step 173

## 18. Final-gate decisions (MEASURED; `scene/terminal.json`, `residue-phase.png`)

| entity | local state | unchanged proposal (local → H0) | M2 effective points | verdict | P3 calls | outcome |
|---|---|---|---|---|---|---|
| 9 | ACTIONABLE | Cyclopean (−6.7, 0.0) → (+70.829, +11.033) | 472,111 | rejected `untraceable_final_support` | 0 | FINALIZED: final_probe_rejected |
| 12 | ACTIONABLE | Cyclopean (−6.1, +0.4) → (+71.562, +11.094) | 2,660,180 | rejected `untraceable_final_support` | 0 | FINALIZED: final_probe_rejected |
| 204 | ACTIONABLE | Cyclopean (+6.7, −0.7) → (+82.223, +3.782) | 371,270 | rejected `untraceable_final_support` | 0 | FINALIZED: final_probe_rejected |
| 230 | ACTIONABLE | Cyclopean (−5.7, +0.3) → (+71.869, +10.812) | 443,467 | rejected `untraceable_final_support` | 0 | FINALIZED: final_probe_rejected |
| 231 | ACTIONABLE | Cyclopean (−5.8, −0.8) → (+71.238, +9.898) | 317,474 | rejected `untraceable_final_support` | 0 | FINALIZED: final_probe_rejected |

Gate calls 5, all in RESIDUE (gate guard), each on the machine's unchanged cached proposal (the M2 adapter recomputed
the probe and found it equal before calling the gate). Admitted 0, rejected 5, final residue observations 0; the scene
did not return to NORMAL. As the contract allows (section 12), the accepted v1 gate rejects Cyclopean residue proposals
before any predicted calibration; no special case was made.

## 19. Terminal Controller-02 state (MEASURED)

Generic terminal: **`scene_closed`** (`SceneClosed`): quiet [123, 129, 172, 202, 212]; residual [(9, ACTIONABLE,
final_probe_rejected), (12, …), (204, …), (230, …), (231, …)]; seed residues none; final observations none; final
rejections [9, 12, 204, 230, 231].

| category (contract section 23) | entities |
|---|---|
| QUIET NORMAL | 123, 129, 172, 202, 212 |
| FINALIZED quiet-before-final-probe | — |
| FINALIZED final-probe-rejected | 9, 12, 204, 230, 231 |
| FINALIZED final-probe-executed but still locally ACTIONABLE | — |
| other residual | — |

Global quiescence is **not** warranted: five entities are still locally ACTIONABLE. `scene_closed` ≠ all objects quiet.

## 20. Scientific scope label

    COHERENT_SUBSET_CLOSED            (Control Outcome 1R)

The scheduler universe is the ten coherent single-patch NS1a entities only. This is not a full-Classroom closure and not
global quiescence.

## 21. Post-freeze 0.5° spherical reference evaluation (stage `evaluate`)

- Opened only after `freeze/control-freeze.json` and the control manifest (`control_complete: true`), in a separate
  process whose guard record orders `control_freeze_verified` → `reference_access_begins` → the EXR open; it wrote only
  under `evaluation/` (check 23).
- Reference: the accepted Breadth-1 `render/canonical.exr` (sha256 `4ea036fc…`, re-verified; never re-rendered), read
  with the accepted `exr_lite` (Object Index and Position only; no metadata file, which holds names).
- Frame: the Breadth-1 orientation test with the North-Star head pose: 222,267 authored cells, **0 outside** their
  declared cells (max |Δpitch| 0.00032°, max |Δyaw| below 85° 0.00082°).
- Coverage: covered iff the Euclidean distance to a final persistent surfel ≤ 0.012 m (accepted
  `classroom_oracle1_eval._covered`); exact equirectangular cell weights (Σ = 4π). Check 24 recomputed everything
  independently (own channel extraction, own transform, own weights, brute-force distances).

## 22. Persistent-map coverage (MEASURED; primary)

| id | reference cells | reference sr | covered | uncovered | cell coverage | solid-angle coverage | final surfels | own looks | terminal |
|---|---|---|---|---|---|---|---|---|---|
| 9 | 148 | 0.0110 | 93 | 55 | 62.84 % | 62.91 % | 8,264 | 24 | FINALIZED: final_probe_rejected |
| 12 | 488 | 0.0365 | 373 | 115 | 76.43 % | 76.86 % | 38,402 | 24 | FINALIZED: final_probe_rejected |
| 123 | 1,751 | 0.1133 | 335 | 1,416 | 19.13 % | 18.63 % | 30,341 | 12 | QUIET |
| 129 | 12 | 0.0008 | 12 | 0 | 100.00 % | 100.00 % | 747 | 2 | QUIET |
| 172 | 2,926 | 0.1402 | 581 | 2,345 | 19.86 % | 23.89 % | 47,892 | 9 | QUIET |
| 202 | 8,370 | 0.5727 | 2,080 | 6,290 | 24.85 % | 25.42 % | 203,194 | 24 | QUIET |
| 204 | 241 | 0.0180 | 149 | 92 | 61.83 % | 62.57 % | 14,192 | 24 | FINALIZED: final_probe_rejected |
| 212 | 7,061 | 0.5229 | 2,443 | 4,618 | 34.60 % | 34.03 % | 255,013 | 17 | QUIET |
| 230 | 165 | 0.0124 | 58 | 107 | 35.15 % | 34.88 % | 5,790 | 24 | FINALIZED: final_probe_rejected |
| 231 | 92 | 0.0069 | 31 | 61 | 33.70 % | 33.69 % | 3,253 | 24 | FINALIZED: final_probe_rejected |
| **all ten** | **21,254** | **1.4348** | **6,155** | **15,099** | **28.96 %** | **30.10 %** | 607,088 | | |

No coherent id lacks a 0.5° first-hit reference. Descriptively, the large low-coverage references are the wide /
fragmented objects: 202 (8,370 cells), 212 (7,061), 172 (2,926 cells in 7 components) and 123 (1,751 in 12) span far more
of the sphere than the local ±25° / ±20° policy domain around each fixed chart reaches; the compact entities are 34–100 %
covered.

## 23. Effective-geometry diagnostic coverage

    MEASURED EFFECTIVE GEOMETRY — NOT PERSISTENT RECONSTRUCTION

Final persistent map + final measurement memory of each id: 6,286 / 21,254 cells = **29.58 %**, solid-angle weighted
**30.73 %**. Per id it exceeds the persistent coverage only where cross-target samples reached reference cells outside
the map (231: 33.70 → 55.43 %; 12: 76.43 → 82.38 %; 230: 35.15 → 40.00 %; 9: 62.84 → 64.86 %; 202 / 212: +0.6 / +0.3 pp);
elsewhere it is equal.

## 24. The historical 98.34 % (non-comparable)

Controller-01: 28,801 / 29,288 = 98.34 % within 12 mm (ACCEPTED HISTORICAL REFERENCE) — dense 0.25° cyclopean first-hit
samples inside the old controller angular domain over the 25 localized objects. NS1e: the accepted 0.5° whole-sphere
first-hit reference over the ten coherent entities. Same 12-mm criterion; different reference sampling, object universe
and angular domain. **The two scalars are not numerically comparable; no better / worse claim is made.**

## 25. Checks (MEASURED)

**`check_ns1e.py`: 27/27** (`NORTH_STAR1E_CHECKS_PASS`; `check-summary.json` `e7bd4aff…`; full run with the corruption suite 5,031 s, batch).

| # | check | result |
|---|---|---|
| 01 | provenance: canonical repo, base, NS1d accepted, contract first and unchanged, one clean pushed commit | PASS |
| 02 | accepted code unchanged (fov3d, pins); NS1e process guard = accepted audit events | PASS |
| 03 | synthetic known answers re-run | PASS |
| 04 | handoff: own NS1d memory; frozen M2 machine; next decision; start state | PASS |
| 05 | eligibility: own rule; ten coherent ids; 10 / 110 / 178 excluded; no names | PASS |
| 06 | charts: own construction at the ORIGINAL NS1a gaze; fixed; every probe used its chart | PASS |
| 07 | physical sensor: fixed head, real world sensor at the mapped gaze, no fake local sensor | PASS |
| 08 | controller: independent SceneMachine re-drive reproduces decisions, events, checkpoints, terminal | PASS |
| 09 | every fresh M2 probe recomputed (tolerance 0) | PASS |
| 10 | gate only in RESIDUE; real H0 sensor; harness | PASS |
| 11 | budget 24; deferral rule; never BLOCKED | PASS |
| 12 | revision = (own looks, measured points) everywhere | PASS |
| 13 | observation: plan frozen before one 4096-spp render per step; render standard | PASS |
| 14 | measurement: geometry recomputed; identity re-attached; freeze order; no truth / stereo leakage | PASS |
| 15 | fusion re-fused bitwise; target only; 12 / 12 mm; other maps fixed | PASS |
| 16 | memory: patches rebuilt bitwise; append once; event = step + 1; provenance; all positive ids | PASS |
| 17 | own-look context: only the active target gains a look | PASS |
| 18 | ordering: stage order; update marks; checkpoints | PASS |
| 19 | natural reactivation only through the refresh; no manual edit | PASS |
| 20 | RESIDUE only after NORMAL exhaustion; at most one final residue observation per entity | PASS |
| 21 | hard cap derived (231 / 239), never exceeded or raised | PASS |
| 22 | checkpointing: contiguous, no partial step, no stage twice | PASS |
| 23 | truth firewall: no control-stage truth read; evaluation after the control freeze | PASS |
| 24 | evaluation recomputed independently (12 mm, persistent map primary, effective diagnostic) | PASS |
| 25 | terminology: COHERENT_SUBSET_CLOSED; no full-Classroom / global claims; 98.34 % non-comparable | PASS |
| 26 | figures byte-identical; labels; PLYs | PASS |
| 27 | run manifest and declared changes | PASS |

Recorded details: check 09 recomputed **577** fresh M2 probes (567 step probes + 10 handoff probes) at tolerance 0; check 08 re-drove all 165 steps and the terminal decision; check 15 re-fused all 165 target patches bitwise; check 16 rebuilt all 165 memory patches bitwise; check 23 scanned 1,820 guard records and reports `control_freeze_hashed_sealed_catalogs_as_bytes`: 165 (deviation D1); check 05 scanned every run JSON against the 234 names of a sealed catalog. Synthetic known answers: 20/20 (`NS1E_SYNTHETIC_PASS`, re-run by check 03).

## 26. Corruption suite (MEASURED)

`NORTH_STAR1E_MUTATIONS_CAUGHT`: **52 / 52 caught, 1 not applicable**. The unmodified-mirror null probe passed every check the suite uses; each corruption mutated a fresh mirror (JSON copied, arrays symlinked and unlinked before any write) or substituted an accepted function / the scanned source in-process; RUN and VIS were unchanged by the suite.

| family | corruptions (catching checks) |
|---|---|
| START | drop NS1d memory event 8 (04, 16); change the current target (04, 08); revert 202's map (15); revert 172's own looks (04, 12); change the next action (07, 08) |
| MEMORY | route by active id (16); discard cross-target ids (16); append twice (16); fuse cross-target memory (15); alter revision semantics (12) |
| CONTEXT | incidental gaze in another visited list (17); another entity's evidence altered (17) |
| CONTROLLER | gate Cyclopean in NORMAL (08); gate FSG6f in NORMAL (08); change scheduler order (08); change budget (11); block instead of defer (11); manual reactivation (19) |
| CHART | dynamic recenter (06); map-centroid centre (06); transposed transform (06) |
| SENSOR | move head (07); rotate baseline (07); change IPD (07); fake local calibration (07) |
| RENDER | change spp (13); enable denoise (13); re-render a completed action (13, 22) |
| MEASUREMENT | SGBM (14); planar persistent geometry (14); Position read before the freeze (14) |
| FUSION | change 12 mm (15); cross-id fusion (15); fuse memory points (15) |
| RESIDUE | enter while NORMAL service exists (20); gate outside RESIDUE (10); modify the proposal before the gate (08); two final residue observations for one entity (20) |
| CAP | increase the cap (21); ignore the cap (21) |
| CHECKPOINT | duplicate a completed action (22); reuse a memory-event id (16); continue from a partial action (22) |
| EVALUATION | reference truth opened before the control freeze (23); memory in the primary coverage (24); another radius (24); 98.34 % called comparable (24); 98.34 % compared in text (25) |
| VISUAL | oracle labels hidden (26); memory exported as fused geometry (26); full-Classroom closure claimed (25); a pixel altered (26) |

Not applicable: **include id 0** — the PERFECT correspondence service emits only positive-instance correspondences, so no measured instance-0 cell exists in any NS1e patch; the exclusion is exercised by synthetic test t02 (and check 16 requires id 0 absent).

## 27. Visuals (Visual Language 1) and hashes

`VIS/visuals-manifest.json` `7524de1a910d453ea7876f6065690ee9cb3cf569473ce2d43880877aac96986d` (regenerated byte for byte by
check 26):

| file | sha256 | size |
|---|---|---|
| `overview.png` | `693fd911861be0a0ff1a4f9c4ba55199493f1deeac92c7a778d1a986887e1aab` | 2400 x 3413 |
| `controller-full-timeline.png` | `4e176ff467a7fc35b5a37b5f78d6c22856871af3a0352ec0352fa25bc7b6a130` | 2400 x 1372 |
| `multi-entity-final-geometry.png` | `313ad8058c32bf09d6cf9f96b782e42757afa87388563b2028da822645ec4b70` | 2400 x 1022 |
| `memory-flow-timeline.png` | `bf97cb11bb1f047b533945018724569b69e59d9997cd3d3375c3fe0d5317ce5a` | 2400 x 832 |
| `coverage-by-entity.png` | `83e6befa83cb9234e6691c59c6b9e5e0fd8596cd749380de572a176ce065e0c4` | 2400 x 1212 |
| `rank1-diagnostic.png` | `3fa19d55c47a724c8729ed986a5325d5eddb22416912e07d63deddb91c6936f1` | 2400 x 1152 |
| `residue-phase.png` | `5d66a14d271150c999371af30c3fa3e7a65a6d6eee0f23510caec0ae7d9f1684` | 2400 x 445 |
| `final-coherent-persistent-points.ply` | `6795e924d703c7cb3da50458b3eda868ae2633774e7539edb77debfcbdce266e` | 607,088 vertices (the ten persistent maps only; `entity_id` vertex attribute) |
| `final-effective-geometry-diagnostic.ply` | `e2204095aae6ec0e6cb438ba53e578e3562bdf2c4c290292b89b5aef6795953a` | 6,990,398 vertices (map + memory per entity; labelled `MEASURED EFFECTIVE GEOMETRY - NOT PERSISTENT RECONSTRUCTION`) |
| `natural-reactivation.png` | not produced | no natural reactivation occurred |

**`overview.png`:**
- **A** — start state: the ten coherent persistent maps in two zoomed canonical-H0 panels (the entities lie in two yaw
  clusters), the next action of 202 (FSG6f (−10.9°, +10.5°) mapped to H0) as a dashed cross-hair, and the accepted start
  table (own looks, maps, NS1d memory own / cross, revisions, states, proposals).
- **B** — the full attention timeline (entity rows × global step): FSG6f filled circles, Cyclopean hollow triangles; Q /
  D / F letters for QUIET / DEFERRED / FINALIZED; switch connectors; the RESIDUE onset and CLOSED rule at step 173.
- **C** — map and memory growth per entity on a log scale (initial map, final fused map, own memory, cross-target memory;
  memory labelled NOT fused).
- **D** — `NO NATURAL REACTIVATION MEASURED`.
- **E** — terminal: Controller-02 `scene_closed` → `COHERENT_SUBSET_CLOSED`, Outcome 1R; ten state tiles (QUIET slate tiles
  with a check, RESIDUAL cross-hatched tiles) with dispositions and own looks; the section 23 breakdown.
- **F** — persistent-map coverage per entity (solid bars) and the effective-geometry diagnostic (hatched), the aggregates,
  and 98.34 % only inside a dashed `NON-COMPARABLE HISTORICAL REFERENCE` box.

**Supporting:** the full controller timeline with the target map after every action; the final persistent maps (two H0
zooms with the initial maps faded, and a top view with the fixed head; no memory sample drawn); the memory flow per event
(own / coherent cross / non-scheduler, ambiguous ids hatched); coverage by entity (covered reference cells green,
uncovered vermilion crosses, terminal dispositions); the rank-1 seam (per own look: spherical target points vs planar
controller-state support); the RESIDUE phase (five gate rejections).

Truth badges, the fixed-head statement, oracle labels and `AMBIGUOUS ORACLE ID - EXCLUDED` (10 / 110 / 178) are carried as
declared in `visuals-manifest.json` (check 26 requires them). Regenerate (presentation-only code at `459682a`):

    .venv/bin/python tools/north_star/ns1e_run.py visualize --run RUN --visuals VIS

## 28. Incidents, resumptions and deviations

- **Canonical run: no incident.** No failed, refused or repeated stage (2,155 `ok` entries); no partial step; no restart;
  no hardware or renderer failure; every EXR at 4096 spp.
- **D1 — the control freeze hashed the sealed catalogs.** After the terminal decision, `freeze-control` hashed every control
  file, including the 165 Blender-written `observation/evaluation_only/instance-catalog.json` (bytes hashed, never parsed;
  no control decision follows). Contract section 25 limits the firewall to stages before `freeze-control`, but section 13
  says the sealed catalog is "never opened", and NS1a deliberately avoided even hashing it. This was found on the
  development rehearsal while the canonical loop was already running from `a6a600c`; changing the code would have broken
  the one-commit rule, so it is disclosed instead. Check 23 reports it explicitly
  (`control_freeze_hashed_sealed_catalogs_as_bytes`: 165) and still fails on any other forbidden read.
- **D2 — `evaluation.json` per-entity `terminal_state` is the last checkpoint label.** It shows the five rank-1 entities as
  `ACTIONABLE/DEFERRED:ordinary_budget` (step 172), not their terminal `ACTIONABLE/FINALIZED:final_probe_rejected` (step 173,
  `scene/terminal.json`). Labeling only; no coverage number is affected. The report tables and the figures use the
  terminal dispositions.
- **D3 — presentation-only figure commits after the run** (contract 32 b): zoomed H0 cluster panels and a data-fitted top
  view (`d02d94c`); the rank-1 bar scale and the terminal labels in the coverage tiles (`ff706c6`). The final `visualize`
  ran from `459682a` (the checker commit, whose tree contains both); no machine or scientific artifact changed. The
  checker allows `visualize` from a later commit that descends from the implementation commit.
- **D4 — contract amendment before implementation** (section 36, `0728857`): the gate-harness P3 rule, the light process
  guard for measurement stages, checkpoint completion.
- **Development (scratch runs only; never the canonical RUN):** the handoff and the gate harness on scratch runs; a
  factory-startup rehearsal room (never Classroom) ran 127 steps to an honest `scene_closed` through DEFERRED and RESIDUE;
  `evaluate` was exercised on that rehearsal run (whose maps were the unchanged NS1c2 start maps). Defects fixed before the
  implementation commit: guard allowlists for re-verified freezes and plan files; the measurement-stage process guard; the
  gate-harness P3 rule; update writing its checkpoint only after every hash; `loop` resuming from checkpoint freezes; a
  scalar index in a figure helper. Checker defects fixed during development: the re-drive mirrors the per-stage
  `from_json` process boundaries and the gate verdict detail; the name scan compares against the sealed catalog's names;
  run-relative write paths in the evaluation guard check.

## 29. What is established

- **The assembled North-Star system governs the coherent ten-entity Classroom subset on its own to an honest
  Controller-02 terminal:** fixed physical head; fixed recentered policy charts; FSG6f → Cyclopean; PERFECT correspondence;
  spherical H0 geometry; target-only 12-mm fusion; instance-keyed cross-target M2 memory as the live controller geometry;
  NORMAL / DEFERRED / RESIDUE. 165 actions, 8 switches, 4 natural quiets, 5 deferrals, one RESIDUE phase with 5 gate
  rejections, `scene_closed` at step 173, without retuning and well inside the derived cap.
- **Accepted NS1d state → live loop is seamless:** the reconstructed start state equals the frozen NS1d M2 machine; the
  first action is exactly NS1d's recorded next decision; when the scan reached 123, it executed exactly NS1d's
  memory-changed FSG6f proposal (0°, +5°).
- **Controller-02 semantics hold over a long North-Star run:** 0 NORMAL gate calls; the gate only in RESIDUE on unchanged
  proposals with M2 geometry and the real H0 sensor; the deferral rule; the residue procedure; an independent re-drive of
  the accepted machine reproduces every decision, event and checkpoint.
- **M2 memory is causally live:** 567 revision changes, 402 cross-target re-probes (27 of QUIET entities), with persistent
  maps strictly target-only.
- **RESIDUE has now been reached naturally in a North-Star scene run** (limitation 5 of NS1d).
- **Post-control coverage of the persistent maps:** 28.96 % of cells / 30.10 % of solid angle of the ten entities' 0.5°
  first-hit reference within 12 mm.

## 30. What is NOT established

- Full-Classroom closure or global quiescence (five residual ACTIONABLE entities; ten coherent ids only).
- A North-Star natural reactivation: none occurred (the mechanism fired 27 QUIET re-probes, all still QUIET).
- Why the rank-1 entities never received an FSG6f proposal and kept repeating Cyclopean actions with low marginal gain:
  4 of 5 had zero planar controller-state support at every look (the inherited seam), but 12 did not. Not diagnosed here.
- That cross-target memory improves coverage or efficiency (no M0 / M1 counterfactual run was made; the effective-geometry
  coverage is a diagnostic).
- Any comparison with Controller-01's 98.34 % (non-comparable definitions).
- Anything about ids 10 / 110 / 178 as scheduled entities, bootstrap cross-target memory, natural correspondence or
  identity, background modelling, head motion or other scenes.

## 31. Final unresolved decision for Luiz / Chat

    IS THE COHERENT NORTH-STAR CONCEPT DEMO
    NOW COMPLETE ENOUGH TO MOVE TO THE
    NEXT CLASSROOM / IDENTITY / BACKGROUND STAGE?

The measured inputs:
- Control Outcome 1R, `COHERENT_SUBSET_CLOSED` at step 173 after 165 new actions (cap 231 not approached).
- 5 QUIET (123, 129, 172, 202, 212); 5 rank-1 entities finalized after rejected Cyclopean residue proposals.
- 0 NORMAL gate calls; 0 natural reactivations; 27 QUIET re-probes by cross-target memory.
- Persistent-map coverage 28.96 % (cells) / 30.10 % (sr) on the accepted 0.5° reference; effective diagnostic 29.58 % /
  30.73 %; the four wide / fragmented objects (202, 212, 172, 123) account for 97 % of the uncovered solid angle.
- Checks 27/27; corruptions 52/52 caught (1 not applicable); synthetic 20/20; deviations D1–D4 disclosed.

This report makes no next-stage design.

## 32. Repository gates on the report tree (MEASURED)

Layout, `scripts/verify_baseline.sh`, `git diff --check` and the checker summary are recorded in the report commit
message.

NS1e REVIEW PENDING · DECISION PENDING: IS THE COHERENT NORTH-STAR CONCEPT DEMO READY FOR ITS NEXT STAGE?
