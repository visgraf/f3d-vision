# Controller-01B: one post-watchdog continuation look — report

**Result.**

    CONTROLLER01B_ONE_LOOK_REPROBE_ACTIONABLE

This result is **MEASURED** by one executed observation. It awaits review by Luiz and Chat. The branch
is not merged, Controller-01's acceptance is unchanged, and **no stopping-policy claim** is made.

**Question** (contract `docs/controller/controller-01b-single-continuation-contract.md`). Starting from
the final causal state of Controller-01, what happens if object 210 (`wall.008`) executes exactly the
one observation still requested by the unchanged accepted local policy?

**Answer (MEASURED).**

Look 25 at the requested gaze [7.6, 18.2] measured 26,950 valid points of 210. It added **0 new surfels**
to the active map, which stayed at 163,944: every point associated with an existing surfel within the
12 mm radius. The global head evidence gained **0 new depth cells** and the observation footprint
**0 new cells**. The effective geometry grew by the look's 26,950 duplicate measurements,
1,938,913 → 1,965,863.

After the look, the unchanged local policy re-probed 210:
- **FSG6f** returned `no_frontier`: in its new window the frontier had 313 raw / **0 OPEN** / 37
  map-resolved / 276 boundary-resolved points, and **0 candidates**.
- The **Cyclopean handoff** then proposed [−17.6, 18.9] from 151 eligible never-observed exterior
  shoreline cells.
- 210 therefore remains **ACTIONABLE**, now through the Cyclopean handoff. That proposal was not
  executed.

A derived attribution with the accepted frontier functions shows the following:
- In the new window, the frontier counts are the same without look 25's geometry, without its binocular
  evidence, and without both. The FSG6f change is attributable to its frontier window moving with the
  current gaze.
- The previous window's frontier, the one FSG6f had been pursuing, is still 350 / 52 OPEN / 28 / 270
  after look 25.

## Provenance

| item | value |
|---|---|
| branch | `controller/controller-01b-single-continuation`, from `main` @ `a60d448` (Policy 1 accepted), isolated worktree |
| contract | `bccd0cb` *Specify Controller-01B single post-watchdog continuation* |
| implementation | `8e8af5a` *Implement Controller-01B single continuation (run, check, visual)* (the run was executed at this commit); `ebbd93f` *Add the derived frontier attribution to the Controller-01B visual* (visual mode only) |
| source run | `/home/lvelho/rd/f3d-vision/previews/controller-01-full` (accepted Controller-01, report `e3bf5e0`): `manifest.json` `d293a98fd6bb285e882186af8fbeadba29ab1d1d62efea23f3ed0ff5c62c0e91`, `actions.json` `12cdbe4d760cce6c494075e4368f9424805b51b997b8b21724bf87f71cc55afd`. All 1,678 files were byte-identical before and after the run, the check, the visual and the mutation work |
| source audit | `/home/lvelho/rd/f3d-vision/previews/controller-01a-terminal-audit/audit.json` (accepted Controller-01A, `CONTROLLER01A_FINAL_REPROBE_ACTIONABLE`) |
| output run | `/home/lvelho/rd/f3d-vision/previews/controller-01b-single-continuation`: `continuation.json` `32be01745912180bd3ab13076a5ae59a371c2e18bdc40789ec5fd2ec298685f3`, look-25 patch `12dd9367…`, post map `f9b4438a…` |
| report | the commit that adds this file |

## Commands

    # the one real observation (batch: 74.8 s wall; reconstruction 57.5 s, one render 4.5 s)
    .venv/bin/python tools/controller/controller01b.py run \
        --source /home/lvelho/rd/f3d-vision/previews/controller-01-full \
        --audit  /home/lvelho/rd/f3d-vision/previews/controller-01a-terminal-audit/audit.json \
        --out    /home/lvelho/rd/f3d-vision/previews/controller-01b-single-continuation

    # the fail-capable check (batch: 69.5 s)
    .venv/bin/python tools/controller/controller01b.py check  --source … --audit … --out …

    # the Level-A visual (batch: about 95 s); deterministic over two runs at ebbd93f
    .venv/bin/python tools/controller/controller01b.py visual --source … --audit … --out … \
        --visuals /home/lvelho/rd/f3d-vision/visuals/controller-01b

The `--source`, `--audit` and `--out` values of `check` and `visual` are those of the run command.

Exactly **one** new OBSERVE was executed. The earlier, pre-run plumbing test (below) rendered nothing.

## Pre-action reproduction (all MEASURED pass)

| gate | result |
|---|---|
| source `manifest.json`/`actions.json` are the accepted artifacts; source audit is the accepted 01A result | pass |
| the 141 replayed per-action memory additions equal the logged ones | pass |
| the 141 matcher-recreated patches equal the saved patches | pass |
| 210 has 24 own looks | pass |
| 210's active map, replayed with the accepted 12 mm `initialize`/`fuse`, equals the saved `final_map` (XYZ as float32, RGB, ids, support, provenance, patch ids `fix_00…fix_23`) | pass (163,944 surfels) |
| E_t(210) from the reconstructed memory equals the saved Controller-01 terminal view (`class_code`, `region_code`) | pass |
| global head-depth cells and `seen_any` cells equal the saved terminal view's (181,862 / 200,752) | pass |
| **pre-action probe = accepted 01A terminal probe** | **pass** (next table) |

| field | accepted 01A terminal probe | 01B pre-action probe |
|---|---|---|
| state / source | ACTIONABLE / fsg6f | ACTIONABLE / fsg6f |
| revision (own looks, measured points of 210) | [24, 1,774,969] | [24, 1,774,969] |
| effective geometry | 1,938,913 | 1,938,913 |
| FSG6f reason; raw / OPEN / map / boundary | continue; 350 / 52 / 28 / 270 | continue; 350 / 52 / 28 / 270 |
| candidates / consensus-rejected | 1 / 2 | 1 / 2 |
| proposed gaze | [7.600000000000001, 18.200000000000003] | the same |
| selected candidate: OPEN / raw / map / boundary support | 30 / 43 / 3 / 10 | 30 / 43 / 3 / 10 |
| selected candidate: frontier score; predicted area (deg²) | 6.135140974246827; 45.669258831148255 | 6.135141348988722 (Δ 3.7e-7); 45.669259983589086 (Δ 1.2e-6) |

The two float descriptors differ only at float32-rounding level. 01A evaluated the probe on the saved
float32 `final_map.npz`; 01B uses the exact float64 replay of the accepted fusion, which is the runtime
representation. Every discrete field and the whole probe summary are exact.

## The one action

    OBSERVE(target_id = 210,
            gaze      = [7.600000000000001, 18.200000000000003]   (the reproduced FSG6f proposal),
            vergence  = fixed 2.10 m (FSG6f VERGENCE_DISTANCE_M; calibration prescribed_vergence_distance_m = 2.1),
            focus     = depth of field disabled (unchanged renderer))
    global action index 141 · object-210 local step 24 · source fsg6f
    render: full profile, OptiX, 256 spp, noise seeds L/R 22017306/22017307 (the --object-id 210 --step 24 convention)

It was executed through the unchanged `ClassroomController01.observe`: the same Blender acquisition
script, the matcher on the current pair, the global memory, head evidence and footprint, 12 mm fusion
with the idempotence replay, and the own-context update. The Controller-01 control loop, scheduler and
watchdog were not used; the watchdog would have refused this look.

## Measurements of look 25 (MEASURED)

| quantity | value |
|---|---|
| target-valid points (210) | **26,950** |
| all-instance valid points | 59,524 |
| measured instance ids | 10, 107, 109, 110, 123, 166, 167, 210 (10 is an unlocated catalog instance) |
| memory additions by instance | 210: 26,950 · 166: 11,357 · 110: 11,135 · 123: 6,350 · 167: 2,202 · 109: 784 · 10: 609 · 107: 137 |
| active map 210 before → after | 163,944 → 163,944 |
| **new surfels** | **0** |
| non-new target points | 26,950 (26,950 matched; 24,956 existing surfels updated) |
| association distance of the matched points | median 1.53 mm, p95 2.40 mm, max 6.41 mm (the 12 mm rule) |
| effective geometry 210 before → after | 1,938,913 → 1,965,863 (+26,950) |
| global head evidence | 39,439 valid in-domain points; **0 new depth cells** (181,862 → 181,862) |
| global observation footprint `seen_any` | **0 new cells** (200,752 → 200,752) |
| E_t(210) kind cells before → after | TARGET_SUPPORT 44,655 → 44,655; UNKNOWN 15,160 → 15,160; AMBIGUOUS_BOUNDARY 3,953 → 3,955; OTHER_SURFACE 137,133 → 137,131; TARGET_EVIDENCE_UNMAPPED 0 → 0 |
| gaze / calibration | [7.6, 18.2]; prescribed vergence 2.1 m |
| render time | 4.52 s |

## Post-look probe (MEASURED; the proposal was not executed)

| field | before look 25 | after look 25 |
|---|---|---|
| state | ACTIONABLE (fsg6f) | **ACTIONABLE (cyclopean_epistemic)** |
| revision | [24, 1,774,969] | [25, 1,801,919] |
| FSG6f reason | continue | **no_frontier** |
| FSG6f raw / OPEN / map-resolved / boundary-resolved | 350 / 52 / 28 / 270 | 313 / **0** / 37 / 276 |
| FSG6f candidates | 1 | **0** |
| FSG6f selected candidate | [7.6, 18.2]: support 30 (OPEN) / 43 (raw); score 6.135; predicted new area 45.67 deg² | none |
| Cyclopean | not reached | `epistemic_fixation`: **151 eligible cells** (map support 44,655; shoreline 3,370; never-observed 88,724) |
| next proposed gaze | [7.6, 18.2] | **[−17.6, 18.9]** (Cyclopean; not executed) |

## Derived frontier attribution (DERIVED; not a policy)

This uses the accepted `frontier.extract_frontier` / `classify_frontier_state`, reproduced by the
visual mode (`visuals/controller-01b/frontier-attribution.json`). FSG6f extracts its frontier around the
**current gaze**.

| window / ingredients | raw / OPEN / map / boundary |
|---|---|
| new window, look-25 geometry + evidence (actual) | 313 / 0 / 37 / 276 |
| new window, without look-25 binocular evidence | 313 / 0 / 37 / 276 |
| new window, without look-25 geometry | 313 / 0 / 37 / 276 |
| new window, gaze move only (neither) | 313 / 0 / 37 / 276 |
| previous window before look 25 (recorded pre) | 350 / 52 / 28 / 270 |
| previous window after look 25 | 350 / 52 / 28 / 270 |

## Relation to the contract's cases (measurements only)

| contract description | measured |
|---|---|
| Case A: look 25 contributes substantial new geometry and changes/resolves the frontier | new surfels 0; new head-depth cells 0; new footprint cells 0; the previous window's OPEN frontier is unchanged (52). The FSG6f proposal disappeared only because its window moved with the gaze (attribution) |
| Case B: little novelty; essentially the same local continuation remains | novelty 0 on all three measures. A local continuation remains, but the source changed: FSG6f stopped and the Cyclopean handoff proposes [−17.6, 18.9] |

No threshold for "substantial" was declared. Classifying the outcome is left to Luiz and Chat.

## Truth firewall (MEASURED)

The run, the check and the visual each ran under the Controller-01 truth firewall. **0 violations.**
The run opened 454 source files, all controller-time: manifest, actions, seeds and catalog (4);
141 patches; 282 acquisition files; 25 final maps; 2 terminal-view files. It opened no `evaluation.json` and nothing under
`bootstrap/evaluation_only/`.

## Checks and fail-capability

`controller01b.py check` on the real output reports `SUMMARY checked=19 failed=0`. That is the
7 reconstruction/pre-action gates plus the **12 contract checks**:
1. source run;
2. pre-action probe;
3. target;
4. gaze;
5. global/local index and memory provenance;
6. vergence/focus;
7. firewall;
8. all valid positive-instance measurements appended;
9. no incidental surfel in 210's map;
10. the post map equals the re-executed 12 mm fusion;
11. exactly one OBSERVE;
12. the recorded state and marker equal the re-executed post-look probe.

The check re-executes the unchanged `observe()` with its render call replaced by the saved acquisition.

**Fail-capability** (scratch harnesses `mutants.py` and `mutants2.py`). Data corruptions act on
throwaway copies of the output run; code mutants act on throwaway repository copies. The unmutated copy
passes, and the source run was byte-identical afterwards.

| # | corruption / mutant | caught by |
|---|---|---|
| 1a | wrong source run (a different `manifest.json`) | check 1 (stopped) |
| 1b | record claims other source hashes | check 1 (stopped) |
| 2 | recorded pre-action probe differs (OPEN 51) | check 2 |
| 3 | wrong target (211) | check 3 |
| 4 | wrong gaze ([7.7, 18.2]) | check 4 |
| 5 | wrong global index (142) | check 5 |
| 6 | altered vergence (2.0 m) | check 6 |
| 7a | an evaluation-truth access recorded in the run | check 7 |
| 7b | (code) check mode opens `evaluation.json` | firewall `PermissionError`; named check error; violation recorded |
| 8a | recorded additions miss one point of 210 | check 8 |
| 8b | (code) `observe` appends only the target's measurements | check 8 |
| 9 | an incidental instance id on a surfel of 210's post map | check 9 |
| 10b | (code) fusion radius 1 mm instead of 12 mm | checks 10 and 12 |
| 10c | (code) fusion radius 6 mm | checks 10 and 12 |
| 11 | a second OBSERVE (`fix_25` acquisition and patch) | checks 3, 5 and 11 |
| 12 | QUIET reported although the probe is ACTIONABLE | check 12 |

Result: **16/16 caught**. Every one of the 12 contract checks is shown to fail.

Two mutants were not caught, and neither indicates a defect in a check.
- **24 mm radius: a data-equivalent mutant.** Every one of look 25's 26,950 target points had an existing
  surfel within 6.41 mm. Fusion assigns each point to its nearest surfel within the radius, so any radius
  ≥ 6.42 mm yields the byte-identical map; this observation cannot distinguish 12 from 24 mm. The 6 mm
  and 1 mm mutants, which this data does exercise, are caught.
- **7b, first form: refused, but not by a named check.** It placed the read before the check's error
  handling, so the process ended with an uncaught firewall `PermissionError` (rc 1) and no named check.
  It was re-run inside the check's flow as 7b above.

The visual mode's own checks passed **11/11**. They cover the recomputed pre/post frontier counts, the
re-executed post-look probe, and the attribution reproducing the recorded counts.

## Visual (Policy 1, Level A)

`/home/lvelho/rd/f3d-vision/visuals/controller-01b/overview.png`

- sha256 `bb5b812694a772c8ff818416f0b26548f4d318f4bb5036f2b6620d02117b309a`, identical over two
  generations at `ebbd93f`;
- generator: `tools/controller/controller01b.py visual` (the command above);
- attribution data: `frontier-attribution.json` (sha256
  `1b42a40ef163ffb4c57fcd69c61069968b8fab8616b8489d7b8dee69cd6b8cb2`).

The four canonical panels:
1. object 210, its 24 earlier looks, look 25 with its 12° core, and the not-executed next proposal
   (CONTROLLER-TIME);
2. the new rectified left/right pair, with 210's valid points (CONTROLLER-TIME);
3. the FSG6f frontier before → after, colored by state, with the candidate support ringed and the
   attribution line (DERIVED);
4. the effective geometry before → after, with look 25's measurements highlighted (CONTROLLER-TIME).

It annotates:
- target-valid points 26,950 and new surfels 0;
- effective geometry 1,938,913 → 1,965,863;
- OPEN 52 → 0, and candidates 1 → 0;
- ACTIONABLE, with the next gaze [−17.6, 18.9] marked not executed.

No evaluation truth is used.

## Deviations and incidents

1. **Plumbing test before the real run (scratch; no render).** To guarantee the single authorized
   observation, the whole pipeline was first exercised with the render replaced by a stand-in copy of
   210's saved look-24 acquisition, written to a discarded scratch directory. Nothing was rendered and
   nothing was kept. It exposed the next two items, which were fixed before the real run.
2. **M_t validation needs the other objects' maps.** E_t(210)'s ownership raster uses every object's
   effective geometry. The reconstruction therefore also installs the other 24 objects' saved final
   active maps, used only as scene support layers. None of those objects is probed or observed. With
   them, E_t(210) equals the saved terminal view exactly.
3. **Pre-action gate calibration.** The first gate also required exact equality of the selected
   candidate's two float descriptors, which is stricter than the contract, and it failed at the 1e-7
   level. The cause is the float32 (01A) versus float64 (runtime replay) map. Discrete fields and the
   summary stay exact; the two floats get a 1e-5 relative tolerance, and the deltas are recorded.
4. **Derived attribution added after the run** (`ebbd93f`, visual mode only). It re-uses the accepted
   frontier functions; the run and its record are unaffected.
5. **Helper duplication.** The small drawing helpers duplicate those of the separate, unmerged
   `visuals/controller-01-retrofit` branch; consolidation is left for a later decision.
6. **Layout checker.** It declares the contract (required), this report and the tool (allowed):
   `SUMMARY checked=498 failed=0`. The layout mutation suite caught **42/42**, including an undeclared
   tracked `tools/controller` file, a misspelled undeclared 01B report and the contract untracked.
7. **Shared checkout.** Its local `main` is `e681392`, whose `.gitignore` predates `visuals/`.
   `visuals/` appears there as untracked until that checkout is updated. No tracked file there was
   modified.

## Unresolved (for Luiz and Chat)

- The interpretation of the measurements against Cases A and B, and any consequence for the stopping
  behavior. This report draws none.
