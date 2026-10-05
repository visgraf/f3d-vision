# North Star-1a — RGB Bootstrap → Perfect Local Measurement → Persistent Entity Seeds — contract

**Status: CONTRACT (committed before any NS1a implementation commit and before any NS1a Classroom render).** Completion
marker (written only by the report): `NORTH_STAR1A_PERFECT_BOOTSTRAP_ROUND_COMPLETE`. No ACCEPTED marker is written by
Claude Code.

Decision context (recorded on `main` at `dfe1626`, "Return to the North Star after AB1d3"): natural stereo is DEFERRED;
the North-Star concept demonstration uses the validated PERFECT / ORACLE correspondence service. NS1a is the first
North-Star integration step.

## 1. One causal question

> Starting from the already accepted six RGB-only candidate gazes, can one complete foveal bootstrap round, using the
> selected PERFECT / ORACLE correspondence service, create a useful persistent set of locally discovered Classroom
> entity seeds WITHOUT using the global Blender object catalog as bootstrap initialization?

The chain, and nothing beyond it:

    coarse spherical RGB attention          (accepted NB1c; read, not recomputed)
      -> frozen foveation locations         (the six NB1c gazes, frozen order)
      -> local binocular observation        (one 4096-spp pair per gaze)
      -> PERFECT correspondence             (accepted AB1b oracle semantics)
      -> accepted spherical metric geometry (accepted AB1b geometry, truth-free)
      -> local oracle segmentation aid      (local Object Index at the measured pixels)
      -> persistent entity seed maps        (accepted fsg3 surface map, accepted parameters)

STOP THERE. NS1a runs no controller, no FSG6f, no Cyclopean policy, no seventh gaze, no post-seed fixation, no residue
closure, no SGBM, no natural matcher, no head motion, no background model.

## 2. Provenance and branch

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (the legacy `fov-3d-vision` is never used) |
| base (accepted `main`: AB1d3 accepted + return to the North Star) | `dfe16269eb4fcf71ee6a97bab0e8e6126970f1b0` |
| AB1d3 acceptance | `9e0bae487012164921343925b04569111bdc9296` (`ACTIVE_BOOTSTRAP1D3_SGBM_VIABILITY_ACCEPTED`) |
| branch | `north-star/ns1a-perfect-bootstrap-round`, from the base, in an isolated worktree |
| run (`RUN`, machine evidence) | `/home/lvelho/rd/f3d-vision/previews/north-star/ns1a-perfect-bootstrap-round/` |
| visuals (`VIS`, persistent) | `/home/lvelho/rd/f3d-vision/visuals/north-star/ns1a-perfect-bootstrap-round/` |

The implementation commit writes this contract's commit SHA into `ns1a_spec.CONTRACT_COMMIT` and the checker's literal;
the checker requires this file to be unchanged from that commit to the checked tree.

## 3. Pre-contract development (disclosed)

Before this commit only accepted code and reports were read, and one calibration-only computation was made (no scene
data, no render): with the accepted `fsg_geometry.make_calibration` and the head pose of the accepted AB1a
`acquisition/calibration.json` (`9960c86e…`), the rank-1 calibration re-serialized with the accepted `write_json` is
**byte-identical** to the AB1a calibration, and the raw-core closest approach to the baseline pole is 9.11° / 83.84° /
23.03° / 66.17° / 82.96° / 64.15° for ranks 1–6 (leverage sin θ median 0.267 / 0.999 / 0.488 / 0.952 / 0.999 / 0.941).
Rank 1 is the known near-baseline gaze of AB1a / AB1b. These facts are recorded, not acted on: no gaze is filtered.

## 4. Sources (verified by `source`; a mismatch is a STOP)

### 4a. The accepted NB1c freeze (the ONLY action source)

`previews/natural-bootstrap-1c-rgb-candidate-gaze/selection/rgb-gaze-freeze.json`
`87a3bab01f55051316ac1eb45b48f394211f4c7a3a317fd0e61c0e52c36f9b37`; `candidate-gazes.json` `8041b954…`; NB1c manifest
`524f8fad…`. Grid convention (from the freeze): yaw = −180 + 0.5 (col + 0.5), pitch = 90 − 0.5 (row + 0.5).

| rank | row, col | yaw, pitch (°) |
|---|---|---|
| 1 | 164, 513 | +76.75, +7.75 |
| 2 | 28, 354 | −2.75, +75.75 |
| 3 | 231, 510 | +75.25, −25.75 |
| 4 | 303, 436 | +38.25, −61.75 |
| 5 | 110, 719 | +179.75, +34.75 |
| 6 | 122, 47 | −156.25, +28.75 |

Consumed EXACTLY, in this order: no reselection, no safe-forward filtering, no leverage rejection, no cherry-picking, no
replacement, no seventh gaze. A gaze producing little useful geometry is a result.

### 4b. The head frame (fixed head)

The head pose (`head_R_wh`, `head_origin_w_m`) is taken from the accepted AB1a `acquisition/calibration.json`
(`9960c86e0fda1c002ae67e702d34ea3399bff3180d61bf71ac535563f8fc3913`). The Blender `EYE` pose must equal it
(≤ 1e-6, the accepted tolerance). **Deliberate deviation from the accepted AB1a helper:** `ab1a_render.eye_pose` reads
the Controller-01 `bootstrap/seeds.json`, which holds the old seed list and object names; NS1a never opens that file
before the seed freeze (§7).

### 4c. Accepted code reused read-only (pinned by sha256 at the base; a change is a STOP)

`ab1b_oracle.py`, `ab1b_geometry.py`, `ab1b_spec.py` (oracle and geometry); `fsg_geometry.py`; `nb1a_guard.py`
(allowlist guard); `fsg3_surface_map.py` and the `fov3d.reconstruction.surface_map` facade; `classroom_oracle1_public.py`
(`MIN_INITIAL_TARGET_POINTS`, `FUSION`); `ab1a_render.py`, `ab1a_spec.py`, `classroom_oracle1_render.py`,
`render_foveated.py`, `bl_common.py`, `exr_lite.py` (render path); `visual_language/style.py`. None is modified.

## 5. Observation (the one canonical acquisition)

Six gazes × two eyes = 12 eye images, accepted Classroom scene (`classroom_eye.blend`, `dca66a32…`), fixed head, static
scene, one Blender process, ranks in frozen order, exactly one binocular acquisition per gaze, never re-rendered.

| item | value |
|---|---|
| calibration | `make_calibration("full", yaw, pitch, 2.10, ipd 0.063, head pose §4b, tangent_frame "baseline_projected")` |
| raw raster / nominal raw core / core FOV | 640 × 640 / 256 × 256 (raw x, y = 192..447) / 12° |
| IPD / vergence | 0.063 m / 2.10 m |
| device / spp | OPTIX / **4096** (the accepted synthetic natural-stereo reference observation quality) |
| seeds | L 2111, R 2112 |
| denoising / adaptive sampling / filter | OFF / OFF / BOX width 1.0 |
| camera / passes | the accepted `classroom_oracle1_render._prepare_perspective_pair` + `ab1a_render.configure` (Combined, Position, Object Index; inherited view-layer passes recorded) |

Pre-registered identities (STOP before any render if violated, checked by `preflight`): rank-1 calibration
byte-identical to the AB1a calibration; every calibration within 1e-9 of the host-planned one; settings readback equal
to the accepted AB1d2 4096-spp readback (`observations/gaze-1/acquisition/acquisition.json` `7c023b1f…`); rank-1
camera matrices equal to the AB1a record (`acquisition.json` `ba316b11…`, ≤ 1e-6).

**Cost.** PROPOSED from AB1d2 (≈ 17–18 s per eye at 4096 spp): ≈ 4–5 min for 12 eyes (batch). After each eye render the
driver projects the total; a projection above 1800 s is a STOP (the spp is never lowered without Luiz / Chat).

## 6. Saved observation products (two explicitly separated domains per gaze)

    observations/rank-0k/acquisition/      INFERENCE / SENSORY
        calibration.json
        rgb-observation.npz                exactly rgb_L, rgb_R (linear float32)
        acquisition.json                   the accepted AB1a acquisition record (+ NS1a fields)
    observations/rank-0k/oracle_aid/       ORACLE AID (ORACLE INPUT)
        raw_L.exr, raw_R.exr
        reference-observation.npz          exactly instance_L, instance_R, position_w_L, position_w_R
    observations/evaluation_only/instance-catalog.json
                                           REFERENCE / EVALUATION; SEALED until the seed freeze

The Blender process necessarily assigns pass indices to every renderable object (this IS the Object Index oracle
mechanism, `_assign_instance_ids`, unchanged). The id → name catalog it writes is sealed: Blender records its sha256 in
`observations/acquisition-run.json`; no NS1a stage opens it before the seed freeze; `evaluate` verifies it against that
seal and against the accepted Controller-01 catalog.

## 7. No global Blender catalog before the seed freeze

Before `freeze-seed-set`, no NS1a stage opens: the instance catalog (sealed or accepted), Controller-01's
`bootstrap/seeds.json` or object list, NB1a / NB1b hypotheses, Breadth-1 products, any object name, or any prior
full-scene object ordering. Every stage runs under the accepted `nb1a_guard.OpenGuard` allowlist; the checker scans every
guard record and the stage code. The six foveations are driven ONLY by the frozen NB1c list.

    GLOBAL OBJECT CATALOG INITIALIZATION:     FORBIDDEN
    LOCAL ORACLE SEGMENTATION AT A FOVEATION: ALLOWED for the concept demo, labelled ORACLE INPUT / ORACLE AID

This is an intentional Blender aid, not claimed natural. Natural Bootstrap-2 will eventually remove persistent oracle
identity.

## 8. PERFECT correspondence (accepted AB1b semantics, read-only)

Per gaze, under a guard whose data reads are exactly `calibration.json` + `reference-observation.npz`, the accepted
`ab1b_oracle.compute_oracle`: for every left RAW nominal-core pixel centre — finite geometric hit; positive local Object
Index; left Position → head frame → projected into the RIGHT RAW camera; finite, z_R > 1e-9; anywhere inside the full
padded 640 × 640 right raster; nearest-pixel right Object Index used ONLY for same-instance binocular visibility; the
exact CONTINUOUS right projection retained. Product (truth-stripped, the accepted schema, passes
`ab1b_geometry.validate_product`): `left_core_row`, `left_core_col`, `uv_L`, `uv_R`. No Position, XYZ, depth, Object
Index, name or label in the product. No SGBM, no natural matcher, no rectification, no depth-search interval.

The stage also writes (ORACLE AID, never read by geometry) a per-core-pixel class map: no hit / hit with instance 0 /
positive not right-visible / correspondence. Recorded per gaze: 65,536 raw-core pixels; finite-hit; positive-instance;
right-projectable; padded-raster; same-instance binocular-visible; final correspondences; **excluded because Object
Index == 0** (UNASSIGNED / NON-CATALOG ORACLE GEOMETRY, reported, never hidden).

`freeze-correspondence` then freezes the six products and records.

## 9. Truth-free spherical metric geometry (accepted AB1b, read-only)

Per gaze, under a guard whose data reads are exactly `calibration.json` + the frozen product (no cv2, no `fsg_stereo`,
no `ab1b_oracle` loaded): baseline pole +X; θ = atan2(√(d_y² + d_z²), d_x); φ = atan2(d_y, −d_z); direct spherical
epipolar triangulation (`ab1b_geometry.compute_epipolar`) plus the independent ray-ray cross-check. Stored:
`P_epi`, `P_ray`, `valid_epi`, `valid_ray`, conditioning (γ, κ, range per px), ray gap, correspondence indices. All
geometry is in the canonical fixed-head H0 frame (no head motion). `freeze-geometry` freezes all six before any identity
is attached.

## 10. Local oracle segmentation aid

Only after `freeze-geometry` verifies: per gaze, under a guard whose data reads are the frozen product, the frozen
epipolar result and `reference-observation.npz`, of which ONLY the member `instance_L` is read (recorded). For every
valid correspondence (`valid_epi`), the temporary entity key is the left raw-core Object Index at its exact `uv_L` centre:

    temporary_entity_id = instance_L[v_L, u_L]  (a positive Blender instance id)   ORACLE SEGMENTATION AID

Cross-look identity persistence (the same id at several gazes = the same entity) is ALSO an oracle aid, recorded as
such. No catalog, no seeds, no names.

Instance 0 is never an ordinary entity: it is reported separately per gaze as UNASSIGNED / NON-CATALOG ORACLE GEOMETRY
(finite left hits, positive-id hits, id-0 hits, from §8). No background model is invented. A gaze that mainly
interrogates instance 0 is a valid bootstrap result.

## 11. Persistent entity seed maps (accepted machinery, accepted parameters)

| parameter | value | source (verified by `source`; pinned by the checker) |
|---|---|---|
| initialization / per-patch precondition | ≥ 100 points of the entity in one patch | `classroom_oracle1_public.MIN_INITIAL_TARGET_POINTS = 100` (= the literal `100` in `fsg3_surface_map.initialize` / `fuse`) |
| association radius | 0.012 m | `classroom_oracle1_public.FUSION["association_radius_m"]` (= `fov3d.reconstruction.association.SURFACE_ASSOCIATION_RADIUS_M`) |
| hash cell | 0.012 m | `classroom_oracle1_public.FUSION["hash_cell_m"]` |
| map operations | `initialize`, `fuse` | `fov3d.reconstruction.surface_map` (facade of the sealed `fsg3_surface_map`) |
| patch id | `nb1c_gaze_01` … `nb1c_gaze_06` | the frozen gaze rank |

Process the six gazes in frozen rank order; within a gaze, positive ids in ascending order. Each gaze forms one
`Patch(patch_id, xyz_h = frozen P_epi, rgb = RAW left-core linear RGB at uv_L, instance_id = local oracle id)` over its
valid correspondences; `n(k, r)` is the number of its points with id k. For each positive id k observed at rank r:

1. **No map yet:** `n ≥ 100` → `initialize(patch, k)`; record `initialized_at_rank` and the initial point count.
   Otherwise → `SEEN_BUT_NOT_INITIALIZED`.
2. **Map exists:** `n ≥ 100` → `fuse(map, patch, k, 0.012, 0.012)`, then replay the same patch: the map must be
   unchanged (exact equality; the Controller-01 `allclose` 1e-10 test also recorded). Otherwise → the evidence record
   is retained and no fusion is forced.

No parameter change. Different ids never share a map. Instance 0 never initializes. Controller-01's code path is not
invoked; the same accepted functions and constants are called directly.

## 12. Seed-set freeze and document

`freeze-seed-set` freezes: the entity maps, per-gaze snapshots, per-gaze local entity measurements, initialization and
fusion history, uninitialized records, instance-0 statistics and provenance. The machine-facing `seeds/seed-set.json`
holds, for every locally observed positive entity id: `temporary_entity_id`, `first_seen_rank`, `gaze_ranks_seen`,
per-gaze valid point counts, `initialized`, `initialized_at_rank`, the map size after each contributing gaze, the final
surfel count, the number of contributing patches, support-count statistics and total raw measured points. No object
name appears in any pre-freeze file.

## 13. Post-freeze descriptive evaluation (`evaluate`)

Only after the seed freeze verifies (guard marks `seed_freeze_verified` → `reference_access_begins`), `evaluate` may
open: the sealed catalog (seal-verified, and required identical in content to the accepted Controller-01 catalog
`be265942…`), object names, Breadth-1 `object-stats.json` (`2f8aa7be…`, the 126 visible objects), Controller-01
`bootstrap/seeds.json` (`6ef83319…`, the 25 localized objects), the AB1b oracle product (`4d26ff32…`) and Position.
Descriptive only; it changes nothing (the seed freeze re-verifies afterwards). Reported: unique positive local entities
observed; initialized; seen but not initialized; first-encountering gaze per entity; gazes producing ≥ 1 initialized
entity; instance-0 / unassigned fractions; the fraction of Breadth-1 visible catalog entities touched; the overlap with
the 25 Controller-01-localized objects; the oracle-consistency of the geometry against Position (P_epi vs Position at
uv_L); the rank-1 reproduction of the accepted AB1b oracle (same calibration, 4096 vs 256 spp; descriptive). Success is
NOT judged by recovering all objects: six gazes are an attention budget, not an object-count estimate.

## 14. Outcome semantics (no arbitrary success threshold)

- **Outcome 1 — useful bootstrap seed set:** one or more stable persistent entity maps with enough geometry to plausibly
  hand to the active controller. Then NS1b should connect the frozen seed set to the accepted active local-growth /
  Controller-02 machinery.
- **Outcome 2 — partial but informative seed set:** some gazes / entities initialize while others are environment,
  unassigned, too small or redundant. If nontrivial, not a bootstrap failure; Luiz and Chat decide whether it suffices.
- **Outcome 3 — no controller-usable seeds:** no persistent entity initializes. Report; do NOT retune NB1c or choose
  other gazes.
- **Outcome 4 — implementation / representation failure:** perfect correspondence, spherical geometry or seed mechanics
  fail unexpectedly. Diagnose only contract-determined defects.

The report gives a reading; Luiz and Chat decide.

## 15. Synthetic / known-answer tests (`synthetic`, before any Classroom render; analytic data only)

Accepted AB1b matcher / geometry checks are reused, not rebuilt. The NEW integration is tested: (1) the frozen gaze
reader reproduces the exact NB1c hash and six-gaze order; (2) an altered order fails; (3) an altered gaze fails;
(4) the perfect-correspondence adapter on an analytic multi-plane scene passes the accepted validator and matches the
analytic correspondence; (5) a Position / Object Index read inside the truth-free geometry stage is refused; (6) ids come
from the exact left raw-core pixels (a one-pixel shift is detected); (7) a global-catalog read before the seed freeze is
refused; (8) an object-name read before the freeze is refused; (9) a known multi-id patch receives the correct ids;
(10) initialization below 100 points does not occur; (11) at 100 points it succeeds; (12) a second overlapping patch
gives matched and new support under the 12-mm rule; (13) a duplicate replay is exactly idempotent; (14) the same id at
two gazes is one persistent entity; (15) different ids never fuse; (16) instance 0 stays unassigned and never
initializes; (17) the catalog opens only in the evaluation stage, after the seed freeze. Plus: the rank-1 calibration
identity (calibration-only), an undersupported later measurement retained but not fused, determinism, and an end-to-end
analytic run (geometry error against the analytic scene ≤ 1e-4 m median with float32 Position). Software tolerances are
declared in `ns1a_spec` (no Classroom-derived tuning).

## 16. Checker (`tools/north_star/check_ns1a.py`)

Own literal pins and constants; every load-bearing rule must be able to fail. At least: PROVENANCE (canonical repo; base
and AB1d3 acceptance ancestors; contract first and unchanged; accepted NB1c / AB1b / surface-map sources pinned);
SELECTION (exact six NB1c gazes, frozen order, no replacement, no seventh); OBSERVATION (six binocular pairs; fixed head;
static scene; 4096 spp in the record, the readback and the EXR header; accepted camera geometry and seeds; one
acquisition, no rerender; the two product domains); PERFECT MATCHER (own independent oracle reproduces each product and
attrition; raw left core; full padded right raster; continuous `uv_R`; same-instance visibility; exact truth-stripped
schema; no rectification / SGBM / depth bound); GEOMETRY (accepted θ / φ convention recomputed independently; truth-free
guard records; ray-ray cross-check; geometry frozen before identity); ORACLE SEGMENTATION AID (only `instance_L` read; no
catalog; ids reproduced at the exact pixels; id 0 never an entity); PERSISTENT MAP (pinned 100 / 0.012 / 0.012; exact
patch ids; the whole construction replayed from the frozen inputs and equal bitwise; idempotent replay; no cross-id
fusion; initialization and undersupported rules); SEED SET (document recomputed); EVALUATION (catalog only after the
seed freeze; evaluation cannot modify the seed set; numbers recomputed); PROCESS (each canonical stage once, in order,
from one clean pushed commit; no controller / FSG6f / Cyclopean / SGBM / natural matcher / head motion / seventh gaze);
VISUALS (byte-identical regeneration; Visual Language 1 badges; oracle-aid labels; gaze order visible).

## 17. Corruption / mutation suite

From a passing mirror after an unmodified-mirror null probe; each corruption names the checks that must catch it.
Families (at least): SELECTION (change one gaze; swap two ranks; drop one gaze; add a seventh); OBSERVATION (spp; head
moved; IPD; vergence; one gaze re-rendered); CORRESPONDENCE (uv_R rounded; right match restricted to the nominal core;
same-instance test removed; instance 0 matched as ordinary; XYZ / depth / identity field added to the product);
GEOMETRY (θ pole; φ sign; Position read; baseline sign); IDENTITY (catalog read before the freeze; id from a wrong pixel;
two ids merged; id 0 promoted); PERSISTENCE (initialization threshold; fusion radius; hash cell; idempotence disabled;
an undersupported patch fused); FREEZE (correspondence, geometry or a seed map altered after its freeze); PROCESS (SGBM,
controller or FSG6f invoked; an extra gaze); VISUAL (oracle-aid badge removed; gaze panels reordered; a pixel altered).
Mutated outputs are computed inside the temporary mirror only, never inspected for performance, and discarded.

## 18. Visuals (Visual Language 1; deterministic; regenerated byte-identically by the checker)

`VIS/overview.png` tells the whole bootstrap story: **A** coarse 360 RGB attention, the six frozen gazes numbered 1–6,
labelled RGB-ONLY SELECTION · no depth · no Blender identity; **B** the six raw-core RGB observations in frozen order with
the perfect-correspondence count and the instance-0 exclusion count; **C** per gaze, the local measured patch with the
labels ORACLE CORRESPONDENCE · DERIVED SPHERICAL GEOMETRY · ORACLE SEGMENTATION AID (identity never presented as natural);
**D** the accumulated canonical-H0 persistent seed set after six gazes, entities distinguished by a non-color cue as well
(glyph + id label), with initialized / seen-but-not-initialized counts, map sizes, contributing ranks and the
unassigned / instance-0 evidence. Also `bootstrap-progression.png` (the seed set after gaze 1 … 6) and
`entity-seeds-3d.png` (all initialized entity geometry in H0), and `visuals-manifest.json`. Truth badges on every figure;
non-correspondence pixels hatched or stippled, never hidden; post-freeze names, if shown, are muted and badged
REFERENCE / EVALUATION.

## 19. Commands and order (each canonical stage runs once, from one clean pushed implementation commit)

    RUN=/home/lvelho/rd/f3d-vision/previews/north-star/ns1a-perfect-bootstrap-round
    VIS=/home/lvelho/rd/f3d-vision/visuals/north-star/ns1a-perfect-bootstrap-round
    .venv/bin/python tools/north_star/ns1a_run.py source                        --run $RUN
    .venv/bin/python tools/north_star/ns1a_run.py synthetic                     --run $RUN
    .venv/bin/python tools/north_star/ns1a_run.py preflight                     --run $RUN   # Blender, NO render
    .venv/bin/python tools/north_star/ns1a_run.py acquire                       --run $RUN   # Blender, the one render
    .venv/bin/python tools/north_star/ns1a_run.py freeze-observations           --run $RUN
    .venv/bin/python tools/north_star/ns1a_run.py perfect-correspondence        --run $RUN
    .venv/bin/python tools/north_star/ns1a_run.py freeze-correspondence         --run $RUN
    .venv/bin/python tools/north_star/ns1a_run.py spherical-geometry            --run $RUN
    .venv/bin/python tools/north_star/ns1a_run.py freeze-geometry               --run $RUN
    .venv/bin/python tools/north_star/ns1a_run.py local-oracle-segmentation     --run $RUN
    .venv/bin/python tools/north_star/ns1a_run.py persistent-seed-construction  --run $RUN
    .venv/bin/python tools/north_star/ns1a_run.py freeze-seed-set               --run $RUN
    .venv/bin/python tools/north_star/ns1a_run.py evaluate                      --run $RUN
    .venv/bin/python tools/north_star/ns1a_run.py visualize                     --run $RUN --visuals $VIS
    .venv/bin/python tools/north_star/check_ns1a.py --run $RUN --visuals $VIS --corruptions --write-summary

Cost classes (PROPOSED): `acquire` batch (≈ 4–5 min); every other stage interactive; the checker with corruptions batch.
No overnight task.

## 20. Permitted fix scope

- **Before the canonical acquisition:** implementation defects in the NS1a tools, without changing §5–§13 or a declared
  tolerance. Development uses analytic synthetic data, calibration-only data, a no-render Classroom configuration probe
  and a synthetic factory-startup Blender rehearsal (never a Classroom render).
- **After the canonical acquisition:** (a) a later stage that fails with an implementation defect BEFORE writing any
  output may be repaired minimally and then run for its first and only time, if §5–§13 are unchanged (recorded as an
  incident); (b) presentation-only figure fixes; (c) a checker defect that false-alarms on correct data, only if the fix
  does not weaken the check (recorded).
- Anything else — a re-render, a gaze change, a change to the oracle, geometry, identity rule, initialization or fusion
  parameters, or the evaluation definitions — is a STOP for Luiz and Chat.

## 21. Stop conditions

STOP and report if: a source / NB1c / head-pose pin fails; `synthetic` or `preflight` fails; the projected render time
exceeds 1800 s; a guard records a violation in a canonical stage; a canonical stage would run twice; the perfect
geometry is inconsistent with its own correspondence (Outcome 4); a canonical check fails for a reason other than a
checker defect.

## 22. Report and stop

`docs/north-star/ns1a-perfect-bootstrap-round-report.md`, status REVIEW PENDING, marker
`NORTH_STAR1A_PERFECT_BOOTSTRAP_ROUND_COMPLETE`, no ACCEPTED marker. It records: provenance; the exact six gazes; proof
that no global catalog initialized the run; render / observation details; per-gaze perfect-correspondence attrition; the
spherical-geometry result; the local oracle-segmentation semantics; per-gaze positive ids and point counts; instance-0 /
unassigned counts; the persistent seed-set table; the initialization / fusion history in frozen order; final map sizes;
the post-freeze descriptive evaluation; an Outcome reading; checks; corruptions; visuals and hashes; incidents; what is
and is NOT established; and the unresolved decision for Luiz / Chat: IS THIS SEED SET READY FOR NORTH STAR-1b
CONTROLLER HANDOFF? Then STOP: no acceptance, no merge, no controller, no FSG6f, no further gaze, no natural stereo, no
head motion, no NB1c change, no background model.

## 23. What NS1a may and may not establish

May establish: what persistent entity seed set one six-gaze RGB bootstrap round produces in the Classroom with perfect
local correspondence, accepted spherical geometry, local oracle segmentation and the accepted persistent-map machinery,
without global catalog initialization.

May NOT establish: natural correspondence or natural identity (both are oracle aids here); that six gazes suffice for the
scene or that another gaze set would do better (none is run); how the active controller will use the seeds (NS1b);
anything about head motion, real cameras or other scenes.
