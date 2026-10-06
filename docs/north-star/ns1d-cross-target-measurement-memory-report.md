# North Star-1d — Controller-Phase Cross-Target Measurement Memory — report

**Markers.**

    NORTH_STAR1D_CROSS_TARGET_MEASUREMENT_MEMORY_COMPLETE
    NORTH_STAR1D_CROSS_TARGET_MEASUREMENT_MEMORY_ACCEPTED

**Status: ACCEPTED.** Luiz and Chat accepted NS1d as **Outcome 2** after scientific review, independent GitHub review,
checker / corruption review and visual review of `overview.png`, `memory-causal-timeline.png` and
`effective-geometry-before-after.png` (see "Acceptance record" at the end). The sections below are the report as
completed at `1d2ea2d`, unchanged.

> **Question.** If the accepted instance-keyed measurement-memory mechanism is restored using the already measured
> North-Star controller-phase observations, does cross-target metric evidence alter any entity's effective geometry,
> revision, local service probe or next controller decision relative to the accepted NS1c2 target-only trace?

**Answer (MEASURED, one canonical no-new-render replay): the memory bridge works, and it changes effective geometry,
revisions and the probes of non-selected entities, but no next controller action through accepted NS1c2 step 7. My
reading is Outcome 2.**

- **The accepted memory class runs unchanged on North-Star data.** The nine unique controller-phase observations (the
  NS1b action on 172 and NS1c2 steps 0–7) were each appended once as one sparse 256 × 256 spherical H0 patch, routed by
  the observed local oracle id. The memory holds 581,882 samples in 11 observed ids.
- **Cross-target evidence reached three coherent entities:**
  - 212: +22,399 samples at event 6 (172 active), then +15,798 at event 8 (202 active);
  - 129: +777 at event 6 (172 active);
  - 123: +5,779 at event 8 (202 active).

  Their M2 revisions changed, their cached probes were invalidated, and each was re-probed. Their persistent maps and
  own-look contexts did not change.
- **Two non-selected proposals changed:**
  - 129's Cyclopean proposal: (+5.1°, +4.5°) → (+7.1°, +5.5°); eligible cells 78 → 174;
  - 123's FSG6f proposal: (−5°, +5°) → (0°, +5°).

  212 kept its proposal, while its eligible cells grew 158 → 438 → 510.
- **No action divergence.** At all 8 decision points, M0 (accepted), M1 (own memory) and M2 (full memory) chose the
  accepted NS1c2 action: target, retain / switch, source, local gaze and H0 gaze. Within the trace:
  - the cross-target changes reached only entities that the scheduler was not about to serve;
  - 172's own raw memory changed only its frontier counts.
- **Maps unchanged.** Every persistent map equals the accepted one. The target-only re-fusions were reproduced
  bitwise, and no memory sample was fused.
- **No reactivation; no new acquisition.** No natural reactivation occurred. There were 0 renders, 0 Blender processes
  and 0 acquisitions.
- **The historical mechanism was reproduced from the accepted Controller-01 saved patches:**
  - 7,843,577 points, 70.7 % cross-target;
  - per-look additions 141 / 141;
  - the 109 natural reactivation by 110's look, reproduced exactly.

Truth labels:
- CORRESPONDENCE: PERFECT / ORACLE (frozen products).
- IDENTITY: ORACLE SEGMENTATION AID (frozen attachment).
- GEOMETRY: DERIVED spherical H0.
- The historical numbers are ACCEPTED HISTORICAL REFERENCE.

## 1. Provenance

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (verified by `source` and check 01) |
| base (`main`, post-NS1c2 roadmap) | `3720d745558bcbadb1c9edb3ffad5aaf0d86b3bb` |
| branch | `north-star/ns1d-cross-target-measurement-memory`, isolated worktree |
| contract | `93f51d3abea379c0bf05720261dda039dca073d0` (before any implementation, memory patch, probe or replay; unchanged since, check 01) |
| implementation | `723b3ac4f2191317aebb2ef1a913a1c6dfbcf93d` (every canonical stage ran from it, clean and pushed) |
| report | this commit |
| NS1c2 acceptance / NS1b acceptance / NS1a acceptance | `5fe0684` / `2553551` / `37c7e02` |
| upstream run manifests (pinned) | NS1c2 `0ec6228d…` (279 files), NS1c `90e2dd4b…`, NS1b `e859fa61…`; NS1c2 `check-summary.json` `dae0671d…`, scene freeze `ea5d0465…` |
| accepted memory class | `fov3d/reconstruction/measurement_memory.py` `27471ebf…`, unchanged; `fov3d/` unchanged since the base |

- **Run.** `RUN` = `/home/lvelho/rd/f3d-vision/previews/north-star/ns1d-cross-target-measurement-memory/`.
  - 7.2 MB, 105 manifest files;
  - `manifest.json` `2b5bd172…`;
  - `check-summary.json` `9320a3d6…`;
  - `freeze/event-list-freeze.json` `c39390b7…`;
  - `freeze/replay-freeze.json` `95c5106e…`.
- **Visuals.** `VIS` = `/home/lvelho/rd/f3d-vision/visuals/north-star/ns1d-cross-target-measurement-memory/`.

### What ran (MEASURED, `process-log.jsonl`; every entry `ok`, from `723b3ac`, clean and pushed)

| # | command (`tools/north_star/ns1d_run.py`) | result | seconds |
|---|---|---|---|
| 1 | `source` | 35 source pins; NS1c2 ACCEPTED on the base; NS1c not accepted; upstream manifests and history pinned | 0.14 |
| 2 | `synthetic` | `NS1D_SYNTHETIC_PASS` 20/20 | 0.15 |
| 3 | `known-answer` | memory rebuild, 109 reactivation, scheduler history: all pass | 2.99 |
| 4 | `events` | 9 unique observations, targets [172 × 8, 202]; no array opened | 0.14 |
| 5 | `replay` | event 0 + NS1c2 steps 0–7; no divergence; 0 reactivations | 38.2 |
| 6 | `visualize` | 3 figures (2 not applicable) | 0.93 |
| 7 | `check_ns1d.py --corruptions --write-summary` | 24/24; null probe clean; corruptions 40/40 | 135 (batch) |

## 2. NS1c2 acceptance

NS1c2 is ACCEPTED as Outcome 1 — natural quiet switch. Its acceptance commit `5fe0684` was fast-forwarded to `main`, and
the post-acceptance roadmap `3720d74` named NS1d next. Check 01 reads the NS1c2 report at the base and finds the
ACCEPTED marker and `**Status: ACCEPTED.**`. NS1c remains NOT ACCEPTED and NOT MERGED (check 03). The accepted NS1c2
trace — 8 NORMAL actions, 172 retained through step 6, natural QUIET at 9 own looks, the switch 172 → 202 at step 7 —
is the M0 baseline.

## 3. The historical measurement-memory semantics (ACCEPTED HISTORICAL REFERENCE; contract section 5)

In the accepted Controller-01 (`controller01.py`, unchanged):
- every completed observation produces one patch;
- `remember_measurements` appends it once to `InstanceMeasurementMemory`, with `source_global_index = step` and
  `source_active_target_id = target`;
- samples are routed by the OBSERVED id, append-only, duplicates retained;
- `measured_points[i]` accumulates the additions;
- the policy geometry is `effective_target_geometry(map_xyz(i), memory.snapshot(i).xyz_h)`;
- `revision(i) = (own looks, measured_points[i])`.

**MEASURED re-verification (stage `known-answer`, check 05).**
- **The accepted memory, rebuilt from the 141 saved name-free Controller-01 oracle patches** (global-step order, the
  accepted class):
  - per-look additions equal the logged `measurement_memory_additions`: 141 / 141;
  - 7,843,577 points in 33 observed ids;
  - over the 25 localized objects: own 2,274,857, cross-target 5,494,429 = **70.7 %**;
  - 8 unlocated ids with 74,291 points;
  - for all 25 objects, the snapshot provenance equals the saved `final_effective_geometry.npz`, and
    `effective_target_geometry(final map, snapshot)` equals its saved `xyz_h` exactly (map first, measured second,
    duplicates retained).
- **The 109 reactivation**, replayed with the unchanged `ns1b_fixtures.rebuild` and probed with
  `controller01.probe_local_policy`:
  - revision (3, 4,048) after step 4 → (3, 4,052) after step 7;
  - exactly 4 added samples, all with `source_active_target_id` 110 and `source_global_index` 7;
  - own looks 3 in both states; map unchanged;
  - effective points 6,166 → 6,170;
  - probe QUIET (Cyclopean `attention_complete`, eligible 0) → ACTIONABLE (`epistemic_fixation`, eligible 28, proposal
    (−7.0°, +14.1°)).

  Both summaries equal the accepted Controller-02 `quiet` / `natural_reactivation` event probes at tolerance 0. The
  accepted adapter, driven with this probe / revision pair, behaves as expected:
  - it re-probes 109 once;
  - it emits exactly one `natural_reactivation` (trigger 110);
  - a null commit with an unchanged revision emits nothing.
- **Scheduler.** The accepted Controller-02 history re-drive (`ns1c2_synthetic.historical_trace`, unchanged) passes all
  its checks, and serves 109 at global step 134 with reason `natural_reactivation`; there are 2 natural-reactivation
  switches in total.

## 4. Controller-phase scope; bootstrap cross-target memory deferred

    BOOTSTRAP CROSS-TARGET MEMORY: NOT DECIDED BY NS1d.

The six NB1c bootstrap gazes were untargeted attention actions, so the accepted memory provenance (a positive active
target) does not apply to them. NS1a's persistent maps and own-look contexts are the initial state. As a consequence,
172's own memory holds its NS1b and NS1c2 looks but not its NS1a initialization look. Every other coherent entity starts
with an empty memory.

## 5. Source event list (stage `events`; check 06)

The list is derived from the accepted NS1b / NS1c2 JSON records and the pinned manifests only. No array was opened
(guard record), and the list was frozen before any patch was built.

| event | source | NS1c2 step | active target | physical H0 gaze | observation products | valid positive-id samples | ids observed |
|---|---|---|---|---|---|---|---|
| 0 | NS1b action 1 | — | 172 | (−155.008, +33.636) | NS1b run | 64,437 | 110, 126, 172 |
| 1 | NS1c2 step 0 (NS1c measured) | 0 | 172 | (−147.585, +37.246) | NS1c step 0 | 64,598 | 110, 125, 126, 172 |
| 2 | NS1c2 step 1 | 1 | 172 | (−145.704, +42.032) | NS1c step 1 | 64,600 | 110, 125, 172 |
| 3 | NS1c2 step 2 | 2 | 172 | (−143.516, +46.782) | NS1c step 2 | 64,565 | 110, 125, 172 |
| 4 | NS1c2 step 3 | 3 | 172 | (−150.152, +48.188) | NS1c step 3 | 64,804 | 110, 125, 172 |
| 5 | NS1c2 step 4 | 4 | 172 | (−163.040, +31.040) | NS1c2 step 4 | 64,780 | 110, 126, 172 |
| 6 | NS1c2 step 5 | 5 | 172 | (−163.874, +26.094) | NS1c2 step 5 | 64,937 | 110, **129**, 172, **212** |
| 7 | NS1c2 step 6 | 6 | 172 | (−153.654, +39.235) | NS1c2 step 6 | 64,393 | 110, 125, 126, 172 |
| 8 | NS1c2 step 7 | 7 | 202 | (−151.282, +22.052) | NS1c2 step 7 | 64,768 | 2, 110, **123**, 144, 202, 207, **212** |

The list was checked against the accepted records:
- 9 distinct observation-freeze and calibration hashes: each physical observation appears once;
- every decision gaze equals its observation's calibration gaze;
- every product pin equals its manifest entry and the frozen correspondence / geometry records.

## 6. Sparse spherical memory-patch construction (contract section 7; checks 07, 08)

Each event's patch is built only when the replay consumes it, from three frozen products:
- the PERFECT correspondence product (`left_core_row`, `left_core_col`);
- the accepted spherical geometry (`P_epi`, `valid_epi`; canonical H0);
- the post-freeze local identity (`instance_L` at the exact `uv_L`).

The raster holds `xyz_h` (float32, NaN elsewhere), `instance_id` (0 elsewhere) and `valid` (geometry ∧ finite ∧ id > 0).
Verified for every event:
- one correspondence per core cell;
- `valid.sum()` = the finite positive-id measurements;
- every correspondence is geometry-valid and positive-id, so instance 0 and −1 do not occur (0 and 0);
- the target cells equal the accepted NS1c2 / NS1b target fusion patch;
- the checker rebuilds every patch bitwise from the pinned products, and re-attaches the identity independently from
  `instance_L` at `uv_L`;
- each identity record shows `geometry_freeze_verified` before `identity_access_begins`.

The replay stage opened no reference observation, EXR or Position (guard record).

## 7. Per-event memory additions by observed id

| event | own (target) | coherent cross-target | non-scheduler ids |
|---|---|---|---|
| 0 | 172: 18,525 | — | 110: 45,090; 126: 822 |
| 1 | 172: 16,229 | — | 110: 46,209; 125: 2,120; 126: 40 |
| 2 | 172: 18,634 | — | 110: 42,846; 125: 3,120 |
| 3 | 172: 19,531 | — | 110: 41,558; 125: 3,476 |
| 4 | 172: 15,508 | — | 110: 46,220; 125: 3,076 |
| 5 | 172: 14,866 | — | 110: 49,596; 126: 318 |
| 6 | 172: 9,760 | **212: 22,399; 129: 777** | 110: 32,001 |
| 7 | 172: 18,642 | — | 110: 42,277; 125: 2,638; 126: 836 |
| 8 | 202: 17,447 | **212: 15,798; 123: 5,779** | 110: 16,094; 144: 5,611; 207: 3,297; 2: 742 |

`source_global_index` is the memory event index (0–8), never the NS1c2 step. Provenance is aligned in every snapshot,
the memory rebuilt twice is identical, and the memory holds every positive observed id (check 09).

## 8. M0 / M1 / M2 (contract section 11)

| mode | geometry(i) | revision(i) | driven by |
|---|---|---|---|
| M0 accepted NS1c2 | persistent H0 map | (own looks, map surfels) | the accepted adapter (`ns1c2_phase.SceneMachine`) |
| M1 own-memory control | `effective_target_geometry(map, own-target samples of i)` | (own looks, own measured points) | stateless `schedule_normal` (diagnostic) |
| M2 full memory | `effective_target_geometry(map, memory.snapshot(i).xyz_h)` | (own looks, measured points of i) | the accepted adapter |

- All modes use the same accepted NORMAL probe: FSG6f → Cyclopean, under the fixed policy chart and the frame adapter.
  The final-look gate was called 0 times in every mode.
- All modes use the same accepted own-look contexts.
- **M0 reproduces NS1c2 exactly:**
  - its fresh probes equal NS1c2's recorded probes (policy part, tolerance 0) with identical fresh sets;
  - its 8 decisions equal the accepted actions;
  - its only event is NS1c2's `quiet` of 172 at global step 6 (check 10).
- No entity was QUIET at the resume point in either adapter.

## 9. Memory totals (after event 8)

| | samples |
|---|---|
| total | 581,882 in 11 ids (2, 110, 123, 125, 126, 129, 144, 172, 202, 207, 212) |
| coherent own-target | 149,142 (172: 131,695; 202: 17,447) |
| coherent cross-target | 44,753 (212: 38,197; 123: 5,779; 129: 777) = 23.1 % of the coherent memory |
| non-scheduler ids | 387,987 (110 AMBIGUOUS ORACLE ID — EXCLUDED: 361,891; 125: 14,430; 144: 5,611; 207: 3,297; 126: 2,016; 2: 742) |
| by active source target | 172: 517,114 (events 0–7); 202: 64,768 (event 8) |
| rank-1 entities (9, 12, 204, 230, 231) | 0 |

The 23.1 % share is descriptive. It is not comparable with Controller-01's 70.7 %: that figure covers 141 looks over
25 localized objects, while this one covers 9 looks concentrated on one region.

## 10. Revision changes (check 13)

- **172 (own).** M2 = M1 throughout:
  - after event 0: [2, 18,525];
  - then [3, 34,754], [4, 53,388], [5, 72,919], [6, 88,427], [7, 103,293], [8, 113,053], [9, 131,695].

  M0 revisions are [own looks, surfels], ending at [9, 47,892].
- **202 (own).** M2 [1, 0] → [2, 17,447] at event 8.
- **212 (cross only).** M2 [1, 0] → [1, 22,399] (event 6) → [1, 38,197] (event 8). M1 stays [1, 0]; its map stays 2,756
  surfels.
- **129 (cross only).** M2 [1, 0] → [1, 777] (event 6). M1 stays [1, 0]; its map stays 174.
- **123 (cross only).** M2 [1, 0] → [1, 5,779] (event 8). M1 stays [1, 0]; its map stays 1,672.

Fresh probes match exactly the entities whose revision changed:
- M0 and M1: the target only;
- M2: the target plus {129, 212} at event 6, and plus {123, 212} at event 8.

Every other probe was a cache hit. Adapter accounting: M0 18 probe calls / 72 cache hits; M2 22 / 68.

## 11. Effective geometry changes (`effective-geometry-before-after.png`; check 11)

| entity | map (M0) | M2 effective after event 8 | composition |
|---|---|---|---|
| 172 | 47,892 | 179,587 | map + 131,695 own samples (events 0–7) |
| 202 | 17,371 | 34,818 | map + 17,447 own samples (event 8) |
| 212 | 2,756 | 40,953 | map + 38,197 cross-target samples (172 @ E6, 202 @ E8) |
| 123 | 1,672 | 7,451 | map + 5,779 cross-target samples (202 @ E8) |
| 129 | 174 | 951 | map + 777 cross-target samples (172 @ E6) |

The other five coherent entities have no memory (M0 = M1 = M2 geometry). For 212, the NS1a seed map is a thin strip,
while the memory samples from 172's step-5 look and 202's step-7 look cover a much larger part of it (overview panel C).
The samples remain memory: 212's persistent map is still its single NS1a patch.

## 12. Per-event service-state and proposal changes (soft differences; M2 vs M0)

- **172.** The own raw memory changed the frontier counts at every probe; proposals and states were identical.
  - FSG6f OPEN surfels (M0 → M2): 280 → 287 (E0), 154 → 155, 148 → 149, 163 → 168, 58 → 61, 159 → 163, 50 → 35,
    113 → 124 (E7).
  - Cyclopean eligible cells were identical (274 at E4, 43 at E6, 0 at E7).
  - QUIET after event 7 in all modes (FSG6f `no_frontier`, Cyclopean `attention_complete`).
- **129 (event 6).** Cyclopean eligible 78 → 174; proposal (+5.1°, +4.5°) → **(+7.1°, +5.5°)**, H0 (−162.785, +25.239) →
  (−165.116, +24.534). Still ACTIONABLE; not selected.
- **212.** Cyclopean eligible 158 → 438 (event 6) → 510 (event 8), OPEN 73 → 47 (event 8). The proposal (+3.9°, +5.2°)
  is unchanged. Still ACTIONABLE; not selected.
- **123 (event 8).** FSG6f OPEN 44 → 59; proposal (−5.0°, +5.0°) → **(0.0°, +5.0°)**, H0 (−152.090, +22.757) →
  (−157.381, +23.854). Still ACTIONABLE; not selected.
- **202 (event 8).** The own memory leaves its post-action FSG6f proposal unchanged: (−10.9°, +10.5°).
- **Rank-1 entities and 204 / 230 / 231 / 9 / 12.** No change.

No ACTIONABLE / QUIET state changed in any mode other than 172's accepted quiet. **No natural reactivation** occurred:
no QUIET entity received memory after becoming QUIET.

## 13. First action divergence

**None through accepted step 7 (check 17).**

| step | accepted | M0 | M1 | M2 |
|---|---|---|---|---|
| 0 | 172 retain FSG6f (−5, −10) | = | = | = |
| 1 | 172 retain FSG6f (−5, −15) | = | = | = |
| 2 | 172 retain FSG6f (−5, −20) | = | = | = |
| 3 | 172 retain FSG6f (0, −20) | = | = | = |
| 4 | 172 retain Cyclopean (+6.2, −1.2) | = | = | = |
| 5 | 172 retain FSG6f (+6.2, +3.8) | = | = | = |
| 6 | 172 retain Cyclopean (+0.2, −10.7) | = | = | = |
| 7 | 172 → 202 switch Cyclopean (−5.9, +5.5) | = | = | = |

Equality was exact in target, decision, source, local gaze and H0 gaze. The checker recomputed every decision with the
accepted `schedule_normal` on its own statuses (check 16). M1 never diverged either.

**Causal reading.**
- The cross-target evidence (events 6 and 8) changed only entities the scheduler did not serve within the trace:
  - while 172 stayed ACTIONABLE, it was retained;
  - at the switch, `schedule_normal` took the lowest NORMAL-serviceable id above 172, which was 202;
  - 202 received no memory before step 7.
- 172's own raw memory did not change any of its decisions.

**After step 7 (descriptive, NOT EXECUTED).** The next decision is the same in all three modes: retain 202, FSG6f
(−10.9°, +10.5°) → H0 (−147.628, +15.923). The memory-enriched post-step-7 state is frozen (`replay/final.json`,
`replay/state-after-event-08.json`).

## 14. Natural reactivations

None. Only 172 was ever QUIET, after event 7, and no later observation measured it before the trace ended. The mechanism
itself is validated by the historical 109 replay (section 3) and synthetic test 11. Neither adapter has a manual
reactivation call (code scan, check 18).

## 15. Persistent maps unchanged (check 15)

- **Accepted fusions reproduced.** For every consumed event, the accepted target-only fusion was reproduced bitwise
  from the accepted target patch with the accepted 12-mm H0 fusion:
  - NS1b 12,072 → 21,243;
  - 172 21,243 → 28,038 → 36,575 → 45,267 → 45,267 → 46,920 → 47,892 → 47,892;
  - 202 217 → 17,371.
- **No other map touched.** All other maps equal their initial NS1a maps.
- **No foreign data in any map.** Every map holds only its own id and its own patch ids. Cross-target samples were never
  fused.
- **Contexts.** Own-look contexts change only for the active target and equal the accepted NS1c2 records (check 14).

**MAP INVARIANT: PASS.**

## 16. Rank-1 effects (descriptive)

None of the nine controller-phase observations saw a rank-1 entity (9, 12, 204, 230, 231). Their memory is empty; their
M0, M1 and M2 geometry, revision ([1, 0] in M1 / M2), probe and proposal are identical. Their zero planar controller
support is unchanged and was not addressed.

## 17. Outcome reading

**My reading: Outcome 2 — memory bridge works, no action divergence in the trace.**
- The memory accumulates the all-instance controller-phase measurements faithfully: 9 events, 581,882 samples, exact
  provenance.
- Persistent maps are unchanged.
- Revisions propagate cross-target evidence, and cache invalidation re-probes exactly the affected entities.
- Some non-selected probes changed: two proposals (129, 123) and the eligible cells of 212.
- Every next physical action through accepted step 7 is unchanged.

Not Outcome 1 or 3: no M2 action divergence, and M1 never diverged. Not Outcome 4: every integration check passed.

Observations for Luiz and Chat (descriptive, not decisions):
1. **The changed proposals carry forward.** The memory-enriched state differs from target-only NS1c2 in two proposals
   that a released loop would use when the scan reaches 123 or 129: 123 FSG6f (0°, +5°) instead of (−5°, +5°); 129
   Cyclopean (+7.1°, +5.5°) instead of (+5.1°, +4.5°).
2. **172's own raw memory roughly quadruples its effective geometry** (47,892 → 179,587) without changing any of its
   decisions in this trace. The duplicates the accepted semantics retain did not perturb FSG6f's proposals here.
3. **The ambiguous id 110 dominates the memory** (361,891 samples) but never enters scheduling. Six other non-scheduler
   ids are stored.

## 18. Checks (MEASURED)

**`check_ns1d.py`: 24/24** (`NORTH_STAR1D_CHECKS_PASS`; `check-summary.json` `9320a3d6…`).

The checker keeps its own literal pins. It recomputes the following independently:
- the event list;
- every memory patch (bitwise);
- the identity re-attachment;
- the memory (accepted class, rebuilt twice);
- the M0 / M1 / M2 geometry sizes and revisions;
- the cache sets;
- the map re-fusions;
- every scheduler decision;
- the first divergence.

It also:
- re-runs the synthetic and historical known answers;
- recomputes every fresh M1 / M2 probe from its context and own geometry (40 probes, tolerance 0);
- regenerates the figures byte for byte.

The 24 checks:
- 01 provenance; 02 accepted code / pins; 03 NS1c decision; 04 synthetic; 05 historical; 06 event list;
- 07 memory patches; 08 identity / truth; 09 memory; 10 M0 = NS1c2; 11 geometry / revision; 12 probes;
- 13 revision / cache; 14 contexts; 15 maps; 16 scheduler; 17 divergence; 18 reactivation; 19 outcome; 20 process;
- 21 truth boundary; 22 terminology; 23 figures; 24 manifest / freeze / declared changes.

## 19. Corruption suite (MEASURED): 40/40 caught, 0 not applicable

`NORTH_STAR1D_MUTATIONS_CAUGHT`:
- The null probe on an unmodified mirror passed all 24 checks.
- Each corruption mutated a fresh mirror (re-signing its replay freeze and manifest) or the code in-process.
- RUN and VIS were unchanged by the suite.

| family | corruptions (catching checks) |
|---|---|
| MEMORY ROUTING | route by active target (07, 09); discard cross-target ids (07, 09); include instance 0 (07); same observation twice (06); provenance target changed (09); the accepted class routing by active target, in-process (09) |
| GEOMETRY | planar-like range-scaled geometry (07); Position read by the replay (08, 21); rounded geometry (07) |
| MAP | cross-target samples fused into a map (11, 14, 15); a frozen map altered (14, 15); memory deduplicated against the map (11) |
| REVISION | map surfels as M2 revision (11, 13); no M2 increment on cross-target evidence (11, 13); M1 incremented by cross-target evidence (11, 13) |
| CONTEXT | cross-target gaze in visited; another entity's evidence altered; a cross-target look counted as own (14 each) |
| SCHEDULER | ineligible id 110 in the scheduler (16); an object name (16); order changed (16, 17) |
| CAUSAL REPLAY | continue past a divergence; consume a counterfactual observation; skip a memory event (17 each) |
| PROCESS | Blender launched; a re-render (20 each) |
| VISUAL | memory drawn as fused surfels; source target hidden; divergence panel omitted; a pixel altered (23 each) |
| OTHER | M0 probe altered (10); synthetic report altered (04); historical value altered (05); event order swapped (06); manual reactivation (18); wrong outcome (19); ACCEPTED marker in the report, in-process (22); a decision claimed executed (22); an M2 probe altered (12); a catalog read (21) |

Synthetic known answers: 20/20 (`NS1D_SYNTHETIC_PASS`), each with a negative control.

## 20. Visuals (Visual Language 1) and hashes

`VIS/visuals-manifest.json` `04eb5c6cf0709155fdbd70e540ff89822faa61baecddf01c3d52cbd9dd99ba2c`:

| figure | sha256 |
|---|---|
| `overview.png` | `6f2f77092d1e3da15e9297a794941aa02f67b942d64cd365d08b3e70bd2dcb84` |
| `memory-causal-timeline.png` | `71ffb93492615ca0c5e47db21241f1940ea6d9960e3f8c10c6861ebb0d6cb401` |
| `effective-geometry-before-after.png` | `b883e7bae2d60386a5d220149d4d6c666718ab57cb159b1badcc7285c0735109` |
| `decision-divergence.png` | not produced: no action divergence occurred |
| `reactivation.png` | not produced: no natural reactivation occurred |

**`overview.png`:**
- **A:** the accepted historical mechanism (ACCEPTED HISTORICAL REFERENCE), with the MEASURED reproduction of
  Controller-01's 141-patch memory and the 109 reactivation.
- **B:** the real memory patch of event 6 (active target 172; ids 212, 129, 172, 110), with the additions by id and
  their revision effects. 110 is hatched and labelled AMBIGUOUS ORACLE ID — EXCLUDED.
- **C:** 212 in its policy chart: the persistent map (2,756 surfels), the memory samples (38,197; glyph = source active
  target) and the effective geometry, with the M0 and M2 proposals. Memory samples are drawn as samples, never as
  surfels.
- **D:** the causal timeline — own looks, cross-target additions, re-probes, and the decision at each step.
- **E:** NO ACTION DIVERGENCE THROUGH STEP 7, with the memory-enriched final scene table and the descriptive next
  decision (NOT EXECUTED).

**Supporting figures:** the full observed-id × event timeline; and the before / after effective geometry of 123, 129,
172, 202 and 212.

Regenerate:

    .venv/bin/python tools/north_star/ns1d_run.py visualize --run RUN --visuals VIS

## 21. Incidents and deviations

1. **Before the contract:** reading only (contract section 3).
2. **Development** (scratch runs only, never the canonical RUN), defects found and fixed before the implementation
   commit:
   - the `events` stage hashed array products, which its own guard refused; array pins now come from the pinned
     manifests, and their bytes are verified when the replay consumes them;
   - a synthetic negative control (test 16) called `schedule_normal` with an id outside its scene;
   - the checker's process check treated `cv2` / `fsg_stereo` (accepted policy dependencies) as render modules; it now
     names only the render / SGBM / natural-stereo modules;
   - the checker's identity-order check had exempted event 0; it now covers all events;
   - figure layout.
3. **Implementation addition, not named in the contract.** `ns1d_core.resume_scene` wraps the accepted
   `SceneMachine.resume_initialized` and adds `run_controller02`'s quiet bookkeeping (`quiet_probe`, `quiet_since`) for
   any entity already QUIET at a resume point. Without it, a later reactivation of such an entity would fail. It was
   used in the historical 109 re-drive. In the canonical replay no entity was QUIET at the resume point, so it was a
   no-op there.
4. **Process-guard self-test.** Synthetic test 19 deliberately attempts a `blender` launch under the active
   `NoProcessGuard`, and the guard refuses it before any process starts. The synthetic stage's guard record therefore
   lists one refused attempt. All other guarded stages record 0 attempts. **New renders: 0. Blender processes started:
   0. Acquisitions: 0.**
5. **Labels.** The figures use the ASCII hyphen in "AMBIGUOUS ORACLE ID - EXCLUDED" (the label from the NS1c2
   acceptance note).
6. **Canonical run: no incident.** Every canonical stage ran once, in order, from `723b3ac`, clean and pushed. Nothing
   was refused or failed.

## 22. What is established

- **The accepted instance-keyed memory inserts cleanly into the North-Star architecture** from already measured
  spherical controller-phase observations. The class (`InstanceMeasurementMemory`, `effective_target_geometry`) is
  unchanged. Each observation enters once as a sparse H0 patch built from the frozen PERFECT correspondence, the
  accepted geometry and the post-freeze identity.
- **Every invariant held:**
  - per-id routing by observed id, with exact provenance;
  - persistent maps unchanged (target-only fusion reproduced bitwise);
  - own-look contexts unchanged;
  - scheduler eligibility unchanged.
- **Cross-target evidence propagates causally** (M2 revision → cache invalidation → re-probe). It changed the effective
  geometry and the probes of 212, 129 and 123, and two of their proposals.
- **Through the accepted NS1c2 trace, the restored memory changes no next controller action.** The decision is the same
  in all three modes (Outcome 2). The memory-enriched post-step-7 state is frozen.
- **The historical Controller-01 memory and its 109 natural reactivation are reproduced exactly** from the accepted
  saved patches.

## 23. What is NOT established

- How the full multi-entity loop behaves with memory. The changed proposals of 123 and 129 were not exercised.
- That cross-target memory improves coverage or efficiency.
- That a North-Star natural reactivation occurs. None arose in this short trace.
- Bootstrap cross-target memory (NOT DECIDED BY NS1d).
- Whether FULL historical memory (own raw duplicates included) or a cross-target-only variant is preferable. In this
  trace M1 = M2 for every decision, and the own duplicates changed no decision.
- Anything about natural correspondence or identity (both oracle aids); 10 / 110 / 178 as scheduled entities; RESIDUE
  on North-Star data; the rank-1 controller-state support; head motion; other scenes.

## 24. Final unresolved decision for Luiz / Chat

~~READY TO RELEASE THE MULTI-ENTITY NORTH-STAR LOOP WITH CROSS-TARGET MEMORY?~~

**Decided:** NS1d is accepted (Outcome 2). Cross-target causal measurement memory is established. North Star-1e releases
the coherent ten-entity Controller-02 loop with full M2 measurement memory, continuing from the accepted post-NS1c2 /
NS1d state (see "Acceptance record").

The measured inputs:
- Outcome 2.
- Memory bridge: 9 events; 581,882 samples; maps and contexts invariant.
- Cross-target re-probes: 212, 129 (event 6); 123, 212 (event 8).
- 2 proposal changes on non-selected entities.
- 0 action divergences; 0 reactivations.
- Checks 24/24; corruptions 40/40; synthetic 20/20; historical known answer exact.
- The frozen post-step-7 state is `replay/state-after-event-08.json`.

This report makes no loop design.

## 25. Repository gates on the report tree (MEASURED)

Layout, `scripts/verify_baseline.sh`, `git diff --check` and a read-only `check_ns1d.py` rerun are recorded in the report
commit message.

~~NS1d REVIEW PENDING · DECISION PENDING: READY TO RELEASE THE MULTI-ENTITY NORTH-STAR LOOP WITH CROSS-TARGET MEMORY?~~

NS1d ACCEPTED · OUTCOME 2 · NS1e NEXT

## Acceptance record

Luiz and Chat completed the scientific review, an independent GitHub review, the checker / corruption review and a
visual review of `overview.png`, `memory-causal-timeline.png` and `effective-geometry-before-after.png`, and **accept
NS1d** as committed at `1d2ea2d`:

    NORTH_STAR1D_CROSS_TARGET_MEASUREMENT_MEMORY_ACCEPTED

- **Outcome accepted:** OUTCOME 2.
- **Machine result accepted:**
  - `NORTH_STAR1D_CROSS_TARGET_MEASUREMENT_MEMORY_COMPLETE`;
  - `NORTH_STAR1D_CHECKS_PASS` 24/24;
  - `NORTH_STAR1D_MUTATIONS_CAUGHT` 40/40, with a clean unmodified-mirror null probe;
  - `NS1D_SYNTHETIC_PASS` 20/20.
- **Accepted scientific conclusion** (stated without strengthening):

      The accepted Controller-01 instance-keyed measurement-memory mechanism runs unchanged on frozen North-Star
      spherical measurements.

  - Nine unique controller-phase observations were replayed: the accepted NS1b action plus accepted NS1c2 steps 0–7.
  - Measured memory:

    | | samples |
    |---|---|
    | total | 581,882 |
    | observed ids | 11 |
    | scheduler-entity own-target | 149,142 |
    | scheduler-entity cross-target | 44,753 |
    | cross-target, entity 212 | 38,197 |
    | cross-target, entity 123 | 5,779 |
    | cross-target, entity 129 | 777 |
    | non-scheduler id 110 | 361,891 |

  - Memory changed revisions, effective controller geometry, probe-cache validity and some local proposals, without
    changing the persistent SurfaceMaps, the own-look histories, or any accepted NS1c2 next action through step 7.
    Examples:
    - entity 129: Cyclopean proposal (+5.1°, +4.5°) → (+7.1°, +5.5°);
    - entity 123: FSG6f proposal (−5°, +5°) → (0°, +5°).
  - No action divergence occurred. No natural reactivation occurred inside this short North-Star trace.
- **Historical known answer** (ACCEPTED HISTORICAL REFERENCE, retained prominently). The accepted Controller-01 memory,
  rebuilt from 141 saved patches:
  - 7,843,577 measured samples;
  - localized-object own: 2,274,857;
  - localized-object cross-target: 5,494,429;
  - cross-target fraction: 70.7 %.

  The historical object-109 natural reactivation was reproduced exactly:

      109 QUIET
        -> later observation with active target 110
        -> +4 measurements of 109
        -> revision changes
        -> Cyclopean eligible cells 0 -> 28
        -> 109 ACTIONABLE
        -> proposal (-7.0, +14.1)

  Thus `cross-target memory -> revision invalidation -> re-probe -> natural reactivation` is an accepted known
  mechanism.
- **Architectural distinction accepted:**

      PERSISTENT MAP  !=  MEASUREMENT MEMORY

  For entity i, the persistent SurfaceMap(i) contains only its accepted target-active fusion. Its controller geometry is
  `effective_target_geometry(persistent_map(i), measurement_memory(i))`. Cross-target measurements DO change effective
  geometry and revision; they DO NOT fuse into another entity's persistent map, DO NOT become another entity's own look,
  and DO NOT enter another entity's visited-gaze list.
- **Visuals accepted** (the reported hashes):
  - `visuals/north-star/ns1d-cross-target-measurement-memory/overview.png`
    (`6f2f77092d1e3da15e9297a794941aa02f67b942d64cd365d08b3e70bd2dcb84`);
  - `visuals/north-star/ns1d-cross-target-measurement-memory/memory-causal-timeline.png`
    (`71ffb93492615ca0c5e47db21241f1940ea6d9960e3f8c10c6861ebb0d6cb401`);
  - `visuals/north-star/ns1d-cross-target-measurement-memory/effective-geometry-before-after.png`
    (`b883e7bae2d60386a5d220149d4d6c666718ab57cb159b1badcc7285c0735109`).

  Accepted visual reading:
  - measured memory is visibly distinct from fused map geometry;
  - cross-target evidence reaches non-active entities;
  - revisions / proposals change without map mutation;
  - the scheduler trajectory remains identical through NS1c2 step 7.
- **Retained limitations** (part of the acceptance):
  1. BOOTSTRAP cross-target memory is still NOT DEFINED.
  2. The scheduler universe remains only the ten coherent single-patch NS1a entities.
  3. Ambiguous oracle identities 10 / 110 / 178 remain outside scheduling.
  4. Rank-1 seeds still have the inherited planar controller-state zero-support seam.
  5. Controller-02 RESIDUE has still not been reached naturally in a North-Star scene run.
  6. PERFECT correspondence remains an oracle aid.
  7. Identity remains an ORACLE SEGMENTATION AID.
- **Unchanged by this acceptance:** the canonical replay, the memory products, the figures, the implementation and the
  contract.
- **Next (Luiz and Chat):** North Star-1e — release the coherent ten-entity Controller-02 loop with full M2 measurement
  memory, continuing from the accepted post-NS1c2 / NS1d state (not restarting from bootstrap).
