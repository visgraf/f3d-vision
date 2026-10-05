# North Star-1a — RGB Bootstrap → Perfect Local Measurement → Persistent Entity Seeds — report

**Marker.**

    NORTH_STAR1A_PERFECT_BOOTSTRAP_ROUND_COMPLETE

**Status: REVIEW PENDING.** Luiz and Chat decide whether the seed set is ready for the North Star-1b controller handoff.
No ACCEPTED marker is written, and the branch is not merged. No controller has run.

> **Question.** Starting from the already accepted six RGB-only candidate gazes, can one complete foveal bootstrap round,
> using the selected PERFECT / ORACLE correspondence service, create a useful persistent set of locally discovered
> Classroom entity seeds WITHOUT using the global Blender object catalog as bootstrap initialization?

**Answer (MEASURED, one canonical run): yes, with partial and redundant elements.**
- The six frozen NB1c gazes, executed once each in frozen order, give **22 positive local entities**. **13 initialize a
  persistent entity map** and 9 are seen but never initialized (all < 100 points).
- Five maps are large:
  - entity 10: 88,465 surfels;
  - entity 110: 86,381;
  - entity 178: 66,681;
  - entity 12: 36,126;
  - entity 172: 12,072.
- Gazes 1, 2, 3 and 6 initialize entities. Gazes 4 and 5 add no new entity; they extend entities already seeded.
- Gaze 3 interrogates mostly unassigned geometry: 95.6 % of its core is instance 0 (non-catalog).
- No global catalog, Controller-01 seed or object name was opened before the seed freeze. Every guard record shows it,
  and checks 16, 23, 24 and 26 verify it.
- Post-freeze, the 13 initialized entities touch 13 of the 126 Breadth-1 visible catalog objects (10.3 %), and 5 of the
  25 objects that Controller-01 localized.

My reading is **Outcome 1, with Outcome-2 elements** (see "Outcome reading"). Luiz and Chat decide.

Identity here is the **ORACLE SEGMENTATION AID**: the local Blender Object Index at the measured pixel. It is not
natural identity. Correspondence is the PERFECT / ORACLE service; geometry is the accepted, truth-free AB1b spherical
geometry.

## 1. Provenance

| item | value |
|---|---|
| canonical repository | `https://github.com/visgraf/f3d-vision` (verified by `source` and check 01) |
| AB1d3 acceptance | `9e0bae487012164921343925b04569111bdc9296` (`ACTIVE_BOOTSTRAP1D3_SGBM_VIABILITY_ACCEPTED`) |
| base (post-AB1d3 roadmap, `main`) | `dfe16269eb4fcf71ee6a97bab0e8e6126970f1b0` |
| branch | `north-star/ns1a-perfect-bootstrap-round`, from the base; isolated worktree |
| contract | `748411c01daaef010905104cf40ed82c917e5f3d` (before any implementation and any NS1a Classroom render; unchanged since, check 01) |
| implementation | `aa2ca517b00b2eb5c6d7bba8a9ccf3be3d68035a` (every canonical stage ran from it, clean and pushed) |
| post-run presentation fix | `f1e3b9b51ee878a280f65ac8afbb0bdda6de4a90` (figure labels only; see "Incidents") |
| post-run corruption-suite fixes | `871303e74e3367c6870937bf29578265e5f1ba05`, `997b74b94406f0d258da69e26db1830e806ac469` (suite only) |
| report | this commit |

- Run `RUN` = `/home/lvelho/rd/f3d-vision/previews/north-star/ns1a-perfect-bootstrap-round/`: 978 MB, mostly the 12 EXRs;
  `manifest.json` `4f3a5a57…`.
- Visuals `VIS` = `/home/lvelho/rd/f3d-vision/visuals/north-star/ns1a-perfect-bootstrap-round/`.

### What ran (MEASURED, `process-log.jsonl`; each canonical stage once, in contract order)

| # | command (`tools/north_star/ns1a_run.py`) | commit | result | seconds |
|---|---|---|---|---|
| 1 | `source` | `aa2ca51` | pins, NB1c freeze, accepted constants, six planned calibrations (rank 1 byte-identical to AB1a) | 0.03 |
| 2 | `synthetic` | `aa2ca51` | `NS1A_SYNTHETIC_PASS` 21/21 | 2.4 |
| 3 | `preflight` (Blender, NO render) | `aa2ca51` | every identity exact (below) | 0.6 |
| 4 | `acquire` (Blender, the one render) | `aa2ca51` | 12 eyes, ranks 1–6 in order | 197.3 |
| 5 | `freeze-observations` | `aa2ca51` | 37 files hashed; the sealed catalog not opened | 0.4 |
| 6 | `perfect-correspondence` | `aa2ca51` | accepted AB1b oracle on the six pairs | 0.5 |
| 7 | `freeze-correspondence` | `aa2ca51` | 24 files | 0.06 |
| 8 | `spherical-geometry` | `aa2ca51` | accepted AB1b geometry; truth-free | 3.0 |
| 9 | `freeze-geometry` | `aa2ca51` | 24 files | 0.08 |
| 10 | `local-oracle-segmentation` | `aa2ca51` | only `instance_L` read | 0.13 |
| 11 | `persistent-seed-construction` | `aa2ca51` | accepted surface map | 2.6 |
| 12 | `freeze-seed-set` | `aa2ca51` | 74 files | 0.09 |
| 13 | `evaluate` | `aa2ca51` | post-freeze, descriptive | 0.4 |
| 14 | `visualize` | `aa2ca51`, then `f1e3b9b` | 3 figures; regenerated once after the label fix | 2.4, 2.4 |
| 15 | `check_ns1a.py --corruptions --write-summary` | `997b74b` | 34/34; null probe clean; corruptions 40/40 | 119 (batch) |

Freezes (MEASURED; sha256 of the freeze records):
- observation `46f0a22e…`;
- correspondence `263da92c…`;
- geometry `7b0ae64d…`;
- seed set `4ee36a1a…`.

## 2. The six frozen NB1c gazes (consumed exactly; no reselection, filtering or replacement)

Source: NB1c freeze `87a3bab01f55051316ac1eb45b48f394211f4c7a3a317fd0e61c0e52c36f9b37` (checks 03, 04). The record is
`source/nb1c-gaze-list.json` `785d02a7…`.

| rank | row, col | yaw, pitch (°) | patch id | raw-core closest approach to the baseline pole |
|---|---|---|---|---|
| 1 | 164, 513 | +76.75, +7.75 | `nb1c_gaze_01` | 9.11° |
| 2 | 28, 354 | −2.75, +75.75 | `nb1c_gaze_02` | 83.84° |
| 3 | 231, 510 | +75.25, −25.75 | `nb1c_gaze_03` | 23.03° |
| 4 | 303, 436 | +38.25, −61.75 | `nb1c_gaze_04` | 66.17° |
| 5 | 110, 719 | +179.75, +34.75 | `nb1c_gaze_05` | 82.96° |
| 6 | 122, 47 | −156.25, +28.75 | `nb1c_gaze_06` | 64.15° |

No seventh gaze and no post-seed fixation exist (checks 04, 30).

## 3. Proof that no global catalog initialized the run

- **The only action source was the frozen NB1c list.**
  - The `source` stage read exactly the NB1c freeze, the candidate record, the NB1c manifest and the AB1a calibration
    (head pose), with 0 violations.
  - The Blender driver re-verifies the list against its own literal table before rendering.
- **The Controller-01 `bootstrap/seeds.json` was never opened before the freeze.** It holds the old seed list and object
  names.
  - This is a deliberate, declared deviation from the accepted AB1a helper `ab1a_render.eye_pose`, which reads that file.
  - The head pose came from the accepted AB1a calibration instead (`9960c86e…`). The Blender `EYE` equals it exactly
    (|ΔR| = 0, |Δo| = 0).
- **The sealed catalog.**
  - Blender necessarily assigns pass indices to every renderable object: that IS the Object Index oracle mechanism
    (`_assign_instance_ids`, unchanged).
  - The id → name map it wrote went to `observations/evaluation_only/instance-catalog.json`. Blender recorded its seal
    (`a0849b21…`, 234 instances).
  - No stage before `evaluate` opened the catalog. Even the observation freeze carried the seal without hashing the file
    (checks 08, 26).
- **Every pre-freeze guard record is clean.** 19 records, all under the accepted `nb1a_guard.OpenGuard`:
  - 0 violations;
  - 0 reads of a catalog, a seeds file, Breadth-1, NB1b, Controller-01 or NB1a discovery data (check 26);
  - no object name in any pre-freeze file, checked against all 234 catalog names (check 23).
- **The evaluation opened the references only after** `seed_freeze_verified` → `reference_access_begins`, and it
  re-verified the seed freeze afterwards (`seed_freeze_reverified`) (checks 25, 28).

## 4. Render / observation details (MEASURED)

| item | value |
|---|---|
| scene / device | `classroom_eye.blend` (`dca66a32…`), Blender 5.2.1 LTS, CYCLES OPTIX |
| instrument | full profile, 640 × 640 raw, 256 × 256 nominal raw core (x, y = 192..447), 12° core, IPD 0.063 m, vergence 2.10 m, `baseline_projected` |
| sampling | 4096 spp in the record, the Blender readback and every EXR header (`cycles.interior.samples` = `4096`, 12/12); seeds L 2111 / R 2112; denoising OFF; adaptive OFF; BOX 1.0 |
| render time per eye L / R (s) | 11.8 / 11.4; 15.2 / 14.7; 17.2 / 16.9; 16.7 / 16.3; 18.1 / 17.6; 18.4 / 17.9 |
| total | 196.6 s render wall (projected after each eye; never above 196 s against the 1800 s STOP); stage 197.3 s |

Preflight identities, MEASURED before any render:
- calibration vs host plan: max |Δ| 0.0 for all six, byte-identical;
- rank 1 byte-identical to the AB1a calibration;
- settings readback equal to the accepted AB1d2 4096-spp readback (no difference);
- rank-1 camera matrices equal to the AB1a record (max |Δ| 0.0).

Product domains per gaze (checks 08, 09):
- INFERENCE / SENSORY: `acquisition/{calibration.json, rgb-observation.npz (rgb_L, rgb_R), acquisition.json}`;
- ORACLE AID: `oracle_aid/{raw_L.exr, raw_R.exr, reference-observation.npz (instance_L/R, position_w_L/R)}`.

**Descriptive finding (MEASURED).** Rank 1 uses the same calibration and seeds as AB1a.
- Its `reference-observation.npz` is **byte-identical** to the accepted AB1a 256-spp reference
  (`f23a7a53cdb7816ee4161337551d90825026a4a25fd8a57ba4981abaa99cdb08`).
- Its RGB differs (4096 vs 256 spp, as intended).
- In this configuration the Position and Object Index passes do not depend on the sample count.

## 5. Per-gaze perfect-correspondence attrition (MEASURED, `correspondence/<rank>/oracle-summary.json`)

The accepted AB1b `compute_oracle` ran read-only. The checker's own oracle reproduces every product (same pixel set;
uv_R max difference ≤ 1e-9 px) and every count (check 09).

| rank | raw core | finite hit | positive id | right-projectable | inside padded raster | same-instance visible | **final** | **excluded: id 0** | no hit | different right instance | matches outside the right nominal core |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 65,536 | 46,832 | 46,832 | 46,832 | 46,832 | 44,769 | **44,769** | **0** | 18,704 | 2,063 | 1,790 |
| 2 | 65,536 | 65,536 | 65,536 | 65,536 | 65,536 | 64,595 | **64,595** | **0** | 0 | 941 | 7,793 |
| 3 | 65,536 | 65,536 | 2,862 | 2,862 | 2,862 | 1,145 | **1,145** | **62,674** | 0 | 1,717 | 672 |
| 4 | 65,536 | 65,536 | 65,536 | 65,536 | 65,536 | 65,536 | **65,536** | **0** | 0 | 0 | 6,681 |
| 5 | 65,536 | 65,536 | 64,742 | 64,742 | 64,742 | 62,427 | **62,427** | **794** | 0 | 2,315 | 3,075 |
| 6 | 65,536 | 65,536 | 65,536 | 65,536 | 65,536 | 64,715 | **64,715** | **0** | 0 | 821 | 3,171 |

- The products hold exactly `left_core_row`, `left_core_col`, `uv_L` (raw pixel centres) and `uv_R` (continuous). They
  pass the accepted validator and hold no truth field (check 10).
- The padded right raster is in use at every gaze (last column).
- **Rank 1 reproduces the accepted AB1b oracle exactly:** 44,769 pairs, the same pixel set, uv_R difference 0.0 px
  (post-freeze evaluation).

## 6. Spherical-geometry result (MEASURED, `geometry/<rank>/geometry-summary.json`)

The accepted AB1b geometry ran truth-free:
- data reads were exactly the calibration and the frozen product;
- Position, Object Index and catalog reads: 0;
- `cv2`, `fsg_stereo` and `ab1b_oracle` were not loaded (check 13).

The checker re-derives everything with its own rays, its own θ via |b × d| and b · d, its own φ via the complex
argument, and a law-of-sines triangulation. P_epi agrees to ≤ 1e-9 m and θ / φ to ≤ 1e-12 rad (check 14).

| rank | triangulated (epipolar / ray-ray) | δθ > 0 | \|φ_R − φ_L\| max [rad] | \|P_epi − P_ray\| max [m] | κ median | left range median (min–max) [m] | range per px median [m] | P_epi vs Position median / max [mm] (post-freeze) |
|---|---|---|---|---|---|---|---|---|
| 1 | 44,769 / 44,769 | all | 3.9e-6 | 2.9e-7 | 261.5 | 4.43 (4.27–4.64) | 0.939 | 0.408 / 0.929 |
| 2 | 64,595 / 64,595 | all | 6.2e-7 | 2.9e-10 | 17.0 | 1.07 (1.05–1.68) | 0.015 | 0.008 / 0.021 |
| 3 | 1,145 / 1,145 | all | 1.6e-6 | 3.8e-8 | 143.5 | 3.70 (2.17–4.05) | 0.429 | 0.291 / 0.411 |
| 4 | 65,536 / 65,536 | all | 1.1e-6 | 7.3e-10 | 22.6 | 1.37 (1.28–1.50) | 0.025 | 0.016 / 0.038 |
| 5 | 62,427 / 62,427 | all | 7.1e-7 | 4.5e-9 | 36.8 | 2.31 (1.89–3.55) | 0.070 | 0.036 / 0.089 |
| 6 | 64,715 / 64,715 | all | 7.7e-7 | 1.1e-8 | 59.5 | 3.49 (2.80–4.35) | 0.171 | 0.089 / 0.211 |

- At every gaze, 100 % of P_epi lies within 1 mm of Position.
- Rank 1 reproduces the accepted AB1b numbers: median 0.408 mm, max 0.929 mm, κ median 261.5.
- There is no epipolar inconsistency, so Outcome 4 does not occur.
- All geometry is in the canonical fixed-head H0 frame.

## 7. Local oracle-segmentation semantics (as executed)

After `freeze-geometry` verified (guard marks `geometry_freeze_verified` → `identity_access_begins`, check 15), the
stage read the frozen product, the frozen `valid_epi` and **only the member `instance_L`** of each
`reference-observation.npz` (recorded; check 16). For each valid correspondence:

    temporary_entity_id = instance_L[v_L, u_L]        ORACLE SEGMENTATION AID (a positive Blender instance id)

- The checker reproduces every id at the exact left pixel (check 17).
- Cross-look persistence by the same id is also an oracle aid, recorded in `seed-set.json`.
- No catalog and no names were used.

## 8. Per-gaze positive ids and point counts (MEASURED, `segmentation/<rank>/identity-summary.json`)

| rank | valid correspondences | local positive ids (points) |
|---|---|---|
| 1 | 44,769 | 12 (36,126) · 204 (3,493) · 231 (2,960) · 230 (1,671) · 9 (268) · 10 (96) · 55 (39) · 56 (31) · 54 (24) · 53 (21) · 57 (21) · 58 (8) · 48 (4) · 49 (4) · 47 (3) |
| 2 | 64,595 | 10 (61,828) · 110 (2,767) |
| 3 | 1,145 | 178 (1,145) |
| 4 | 65,536 | 178 (65,536) |
| 5 | 62,427 | 110 (35,790) · 10 (26,637) |
| 6 | 64,715 | 110 (47,824) · 172 (12,072) · 212 (2,756) · 123 (1,672) · 202 (217) · 129 (174) |

## 9. Instance 0 / unassigned (UNASSIGNED / NON-CATALOG ORACLE GEOMETRY; reported, never an entity)

| rank | finite left hits | positive-id hits | id-0 hits | id-0 fraction |
|---|---|---|---|---|
| 1 | 46,832 | 46,832 | 0 | 0.000 |
| 2 | 65,536 | 65,536 | 0 | 0.000 |
| 3 | 65,536 | 2,862 | **62,674** | **0.956** |
| 4 | 65,536 | 65,536 | 0 | 0.000 |
| 5 | 65,536 | 64,742 | 794 | 0.012 |
| 6 | 65,536 | 65,536 | 0 | 0.000 |
| pooled | 374,512 | 311,044 | 63,468 | 0.169 |

- **Gaze 3 mainly interrogates instance 0.** NB1c's post-freeze evaluation had already recorded its centre as `O_0`
  (non-catalog). This is a valid bootstrap result; the gaze was not replaced.
- No background model was introduced.
- Instance 0 never reaches the seed construction, which refuses it explicitly (synthetic case 16; checks 20, 22).

## 10. Persistent seed-set table (MEASURED, `seeds/seed-set.json` `e2ff1ba3…`, frozen)

Parameters (pinned, check 18):
- initialization / per-patch precondition: 100 points. This is `classroom_oracle1_public.MIN_INITIAL_TARGET_POINTS`, and
  equally the literal `100` in `fsg3_surface_map.initialize` / `fuse`.
- association radius 0.012 m; hash cell 0.012 m;
- patch ids `nb1c_gaze_01..06`.

| id | first seen rank | gaze ranks seen | points per gaze (1 / 2 / 3 / 4 / 5 / 6) | initialized | at rank | final surfels | patches | support count | total raw points |
|---|---|---|---|---|---|---|---|---|---|
| 9 | 1 | 1 | 268 / 0 / 0 / 0 / 0 / 0 | yes | 1 | 268 | 1 | all 1 | 268 |
| 10 | 1 | 1, 2, 5 | 96 / 61,828 / 0 / 0 / 26,637 / 0 | yes | 2 | 88,465 | 2 | all 1 | 88,561 |
| 12 | 1 | 1 | 36,126 / 0 / … | yes | 1 | 36,126 | 1 | all 1 | 36,126 |
| 47 | 1 | 1 | 3 | no | — | 0 | 0 | — | 3 |
| 48 | 1 | 1 | 4 | no | — | 0 | 0 | — | 4 |
| 49 | 1 | 1 | 4 | no | — | 0 | 0 | — | 4 |
| 53 | 1 | 1 | 21 | no | — | 0 | 0 | — | 21 |
| 54 | 1 | 1 | 24 | no | — | 0 | 0 | — | 24 |
| 55 | 1 | 1 | 39 | no | — | 0 | 0 | — | 39 |
| 56 | 1 | 1 | 31 | no | — | 0 | 0 | — | 31 |
| 57 | 1 | 1 | 21 | no | — | 0 | 0 | — | 21 |
| 58 | 1 | 1 | 8 | no | — | 0 | 0 | — | 8 |
| 110 | 2 | 2, 5, 6 | 0 / 2,767 / 0 / 0 / 35,790 / 47,824 | yes | 2 | 86,381 | 3 | all 1 | 86,381 |
| 123 | 6 | 6 | 1,672 | yes | 6 | 1,672 | 1 | all 1 | 1,672 |
| 129 | 6 | 6 | 174 | yes | 6 | 174 | 1 | all 1 | 174 |
| 172 | 6 | 6 | 12,072 | yes | 6 | 12,072 | 1 | all 1 | 12,072 |
| 178 | 3 | 3, 4 | 0 / 0 / 1,145 / 65,536 / 0 / 0 | yes | 3 | 66,681 | 2 | all 1 | 66,681 |
| 202 | 6 | 6 | 217 | yes | 6 | 217 | 1 | all 1 | 217 |
| 204 | 1 | 1 | 3,493 | yes | 1 | 3,493 | 1 | all 1 | 3,493 |
| 212 | 6 | 6 | 2,756 | yes | 6 | 2,756 | 1 | all 1 | 2,756 |
| 230 | 1 | 1 | 1,671 | yes | 1 | 1,671 | 1 | all 1 | 1,671 |
| 231 | 1 | 1 | 2,960 | yes | 1 | 2,960 | 1 | all 1 | 2,960 |

Counts:
- 22 observed positive entities;
- **13 initialized**: 9, 10, 12, 110, 123, 129, 172, 178, 202, 204, 212, 230, 231;
- **9 seen but not initialized**: 47, 48, 49, 53, 54, 55, 56, 57, 58, all at rank 1 with 3–39 points;
- gazes with an initialized entity: 1, 2, 3, 6.

Support count is 1 for every surfel, because no surfel was ever matched across gazes (next section). Three maps lie just
above the precondition: 9 (268), 202 (217) and 129 (174).

## 11. Initialization / fusion history in frozen gaze order (MEASURED, `seeds/construction-history.json`)

| rank | events |
|---|---|
| 1 | INITIALIZED 9 (268), 12 (36,126), 204 (3,493), 230 (1,671), 231 (2,960). SEEN_BUT_NOT_INITIALIZED 10 (96 < 100), 47, 48, 49, 53, 54, 55, 56, 57, 58 |
| 2 | INITIALIZED 10 (61,828), 110 (2,767) |
| 3 | INITIALIZED 178 (1,145) |
| 4 | FUSED 178: 1,145 → 66,681 (matched 0, new 65,536) |
| 5 | FUSED 10: 61,828 → 88,465 (matched 0, new 26,637). FUSED 110: 2,767 → 38,557 (matched 0, new 35,790) |
| 6 | FUSED 110: 38,557 → 86,381 (matched 0, new 47,824). INITIALIZED 123 (1,672), 129 (174), 172 (12,072), 202 (217), 212 (2,756) |

- Every fusion was replayed with the same patch: duplicate, and exactly equal (also within the Controller-01
  1e-10 test) (check 21).
- **No fusion matched any surfel within 12 mm.** The six raw cores are angularly disjoint (minimum gaze separation
  21.2°), so every fusion appended a spatially disjoint part of the same entity. On this data the 12-mm association
  radius and hash cell therefore had no effect: their corruptions are caught only through the pinned constants
  (check 18), not through the outputs.
- **Entities fused across gazes are physically multi-part** (post-run descriptive diagnostic, from the frozen maps'
  per-patch provenance):
  - entity 10: parts at gazes 2 and 5, centroids 1.92 m apart, min gap 1.70 m;
  - entity 110: three parts, centroid distances 1.43–3.31 m, min gaps 0.45–2.54 m;
  - entity 178: two parts 2.84 m apart, min gap 1.20 m.

  A Blender instance id can cover several physical pieces, so the oracle identity merges them into one seed.

## 12. Final map sizes (MEASURED, `seeds/entity-maps.npz` `621d8902…`)

| id | 10 | 110 | 178 | 12 | 172 | 204 | 231 | 212 | 123 | 230 | 9 | 202 | 129 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| surfels | 88,465 | 86,381 | 66,681 | 36,126 | 12,072 | 3,493 | 2,960 | 2,756 | 1,672 | 1,671 | 268 | 217 | 174 |

Total: 302,936 surfels in 13 maps. The per-rank snapshots are `seeds/snapshot-after-rank-0k.npz`.

## 13. Post-freeze descriptive evaluation (MEASURED, `evaluation/evaluation.json` `2bac3a38…`)

- **Catalog.** The sealed catalog matches its Blender seal, and its id → name map equals the accepted Controller-01 catalog
  exactly (234 instances).
- **Names of the 13 initialized entities:**
  - 9 `Cube.005`; 10 `Cube.006`; 12 `Cube.008`;
  - 110 `beams`; 123 `ceilingMoulding`; 129 `ceiling_pipeHang.005`; 172 `pipe`; 178 `sol`;
  - 202 `wall`; 204 `wall.002`; 212 `wall.010`; 230 `woodWindow.004`; 231 `woodWindow.005`.

  The 9 uninitialized entities are `Cylinder.015/016/017/021–026` (rank 1).
- **First encounter.** Gaze 1 first saw 15 entities, gaze 2 one (110), gaze 3 one (178) and gaze 6 five (123, 129, 172,
  202, 212). Gazes 4 and 5 first-encountered none.
- **Gazes producing ≥ 1 initialized entity:** 4 of 6 (1, 2, 3, 6).
- **Instance 0.** 63,468 of 374,512 finite left hits (16.9 %). 95.6 % at gaze 3 and 1.2 % at gaze 5.
- **Breadth-1 (126 visible catalog objects at 0.5°).**
  - Observed: 13 / 126 = 0.103. Initialized: 13 / 126 = 0.103. They are the same 13 objects.
  - The 9 cylinders are not Breadth-1-visible at 0.5°.
- **Controller-01 (25 localized objects).**
  - Observed and initialized ∩ localized: 5 — 110 `beams`, 123 `ceilingMoulding`, 172 `pipe`, 178 `sol`, 202 `wall`.
  - The other 8 initialized entities were never localized by Controller-01.
- **Oracle consistency.** P_epi vs Position at the exact uv_L: 100 % within 1 mm at every gaze (§6).

Success is not judged by object recovery: six gazes are an attention budget, not an object count.

## 14. Outcome reading (contract §14; for Luiz and Chat)

**My reading: Outcome 1, with Outcome-2 elements.**
- **Outcome 1 indicators, met.** The six frozen RGB gazes produce 13 stable persistent entity maps without catalog
  initialization. Five are large (12,072–88,465 surfels) and spatially well measured (§6). That is plausibly enough
  geometry to hand to an active controller.
- **Outcome 2 elements, present:**
  - gaze 3 is 95.6 % unassigned (non-catalog) geometry;
  - gazes 4 and 5 are redundant at the entity level: they extend already-seeded entities and initialize nothing new;
  - 9 small entities never reach 100 points;
  - 3 maps sit just above the threshold;
  - the seeds are environment-heavy (walls, floor, ceiling structures, window, light fixtures);
  - entities fused across gazes are physically multi-part.
- **Not Outcome 3:** 13 entities initialize.
- **Not Outcome 4:**
  - the perfect correspondence, the spherical geometry and the seed mechanics behave exactly as contracted (34/34 checks);
  - rank 1 reproduces the accepted AB1b result exactly.

Luiz and Chat decide.

## 15. Checks (MEASURED)

**`check_ns1a.py`: 34/34** (`NORTH_STAR1A_CHECKS_PASS`; `check-summary.json` `39a2cbde…`, written at `997b74b`). The
checker keeps its own literal pins and constants:
- provenance and contract order (01);
- accepted source pins (02);
- the NB1c freeze and frozen order (03, 04);
- calibrations rebuilt and byte-compared, rank 1 against AB1a (05);
- 4096 spp in the record, the readback and the EXR headers, plus seeds, device and filter (06);
- own eye matrices (07);
- the observation freeze and product domains (08);
- its own oracle (09), the schema and semantics (10), the oracle guard and class map (11);
- a code / command scope scan (12);
- the truth-free geometry guards (13) and its own triangulation (14);
- freeze order and identity after the geometry freeze (15);
- the segmentation aid reading only `instance_L` (16) and its own id lookup (17);
- the pinned map constants (18);
- an own construction loop over the accepted surface map reproducing maps, snapshots and history bitwise (19);
- the initialization / undersupport rules (20), replayed idempotence (21) and no cross-id fusion (22);
- the seed-set document recomputed, plus a name-leak scan (23);
- the seed freeze before evaluation (24) and the evaluation access order (25);
- no forbidden pre-freeze read in any guard record (26);
- the evaluation recomputed (27) and unchanged (28);
- the process: once, in order, one clean pushed commit (29);
- no controller / FSG6f / Cyclopean / SGBM / head motion / seventh gaze (30);
- synthetic before the render (31);
- byte-identical figure regeneration (32) and badges / labels / gaze order (33);
- manifest and declared changes (34).

**Synthetic / known answers: 21/21** (`NS1A_SYNTHETIC_PASS`, `synthetic/synthetic-report.json` `6e56c808…`; analytic
scenes only, before any Classroom render). They cover all 17 contract cases, plus:
- the rank-1 calibration identity;
- an undersupported later measurement retained, not fused;
- determinism and frozen rank order;
- the seed-set document fields with no names;
- end-to-end analytic geometry (median and max error within 1e-4 / 5e-4 m with float32 Position).

**Repository gates on the report tree (MEASURED):** layout 600/600, `scripts/verify_baseline.sh` 9/9, `git diff --check`
clean, and `check_ns1a.py` (read-only) 34/34.

## 16. Corruption suite (MEASURED): 40/40 caught

`NORTH_STAR1A_MUTATIONS_CAUGHT`, from a passing baseline after an unmodified-mirror null probe passed all 34 checks.
Every corruption mutated a temporary mirror only. The suite hashed all 139 run and visual files before and after: they
are unchanged.

| family | corruptions (catching checks) |
|---|---|
| SELECTION | gaze-list gaze changed (03); executed gaze changed (04, 05); two ranks swapped (04, 05); one gaze dropped (04, 08); a seventh gaze added (04, 30) |
| OBSERVATION | spp 2048 (06); head moved (05, 30); IPD 0.064 (05); vergence 2.2 (05); one gaze re-rendered (04, 29) |
| CORRESPONDENCE | uv_R rounded (09, 10); right match restricted to the nominal core, regenerated (09); same-instance test removed, regenerated (09, 10); instance 0 as an ordinary match, regenerated (09, 10); an XYZ field added (10) |
| GEOMETRY | θ pole changed, regenerated (14); φ sign flipped (14); Position read in the geometry stage (13); baseline sign flipped (14) |
| IDENTITY | catalog read before the freeze (16, 26); id from a wrong pixel, seeds regenerated (17); two ids merged, seeds regenerated (17); instance 0 promoted to an entity (19, 20) |
| PERSISTENCE | threshold 50, regenerated with a mutated copy of the sealed map (18, 19, 20); radius 24 mm (18); hash cell 24 mm (18); idempotence disabled (18, 19, 21); an undersupported patch fused (19, 20) |
| FREEZE | correspondence (15), geometry (15) or a seed map (15, 19, 28) altered after its freeze |
| PROCESS | SGBM invoked (12, 29); a controller invoked (29, 30); FSG6f loaded (30); an extra gaze executed (04, 29) |
| VISUAL | oracle-input badge removed (33); gaze panels reordered (32, 33); a pixel altered (32) |
| EVALUATION | catalog opened before the reference-access mark (25); an evaluation number altered (27) |

## 17. Visuals (Visual Language 1) and hashes

`VIS` (`visuals-manifest.json` `dc63cf311a5dff7723f96d2443666fb7b16f3c43f3c7fe9f5ec004d6e1f0c3db`):

| figure | truth badges | sha256 |
|---|---|---|
| `overview.png` | ORACLE INPUT, DERIVED, REFERENCE / EVALUATION | `3580fe603545cc673fc22f9182bb9f9deb6d9e6f82cdc452e8a4561a6399e109` |
| `bootstrap-progression.png` | ORACLE INPUT, DERIVED | `adb472a2b0b77df65a50ded43ee02c1c79e6bc1f40ae4dbc5296da3ad6e41743` |
| `entity-seeds-3d.png` | ORACLE INPUT, DERIVED | `778c9862a9c73156f0ee2be0138055544626f9d4e931b28ff456e70d5bb5fe3b` |

- **`overview.png`** has four panels:
  - **A:** the coarse 360 RGB with the six executed fixations 1–6 and their 12° raw-core outlines, tagged RGB-ONLY
    SELECTION · no depth · no Blender identity;
  - **B:** the six raw-core RGB observations in frozen order, with the correspondence, instance-0 and exclusion counts;
  - **C:** per gaze, every perfect correspondence coloured by its oracle id (glyph + id label), shaded by range, tagged
    ORACLE CORRESPONDENCE · DERIVED SPHERICAL GEOMETRY · ORACLE SEGMENTATION AID. No hit is stippled, instance 0
    cross-hatched (UNASSIGNED) and not-right-visible hatched; nothing is hidden;
  - **D:** the persistent seed set in the H0 top view, with the entity table. Post-freeze names appear only in the muted
    REFERENCE / EVALUATION column.
- **`bootstrap-progression.png`:** the seed set after gaze 1 … 6, at the same scale.
- **`entity-seeds-3d.png`:** top, front and side orthographic views of all 13 initialized maps.

Regenerate:

    .venv/bin/python tools/north_star/ns1a_run.py visualize --run RUN --visuals VIS

## 18. Incidents

1. **Before the contract** (calibration-only): the rank-1 byte identity with AB1a and the per-gaze pole distances (contract
   §3).
2. **Between the contract and the canonical render** (scratchpad only; a no-render Classroom preflight probe and a 16-spp
   factory-startup rehearsal through every stage — never a Classroom render). Defects found and fixed inside the
   implementation commit:
   - a synthetic guard probe whose write directory contained the probed file;
   - lazy imports inside guards that tried to write `.pyc` files (now `dont_write_bytecode`, and imports before guards);
   - the check-12 word scan (now an AST identifier scan) and the check-30 module rule (`ab1b_oracle` is legitimate in the
     oracle stage only);
   - three figure overlaps;
   - **corruption helpers that wrote through the mirror's symlinks into the (scratch) run.** They now unlink before
     writing, and the suite verifies the run's hashes before and after. That scratch run was rebuilt; no canonical data
     existed then.
3. **Canonical run:** no incident.
   - Every canonical stage ran once, in order, from `aa2ca51`, clean and pushed.
   - The render took 196.6 s.
   - No re-render, no gaze change, no rerun of any stage.
4. **After the canonical run** (contract §20):
   - **(b) presentation only (`f1e3b9b`):** label clutter where many ids cluster at rank 1. A deterministic label placer
     with leader lines (glyphs stay at their data positions); no labels on hollow glyphs in the small progression panels;
     panel-C labels and lines kept in their tile. `visualize` was re-run; no data, statistic or transform changed.
   - **Corruption-suite only (`871303e`, `997b74b`):** the first canonical suite run reported two corruptions NOT
     APPLICABLE, because both targeted the gaze with the most correspondences (rank 4: one floor entity).
     - Same-instance removal now targets the gaze with the most different-instance exclusions.
     - The wrong-pixel shift now targets the gaze with the most ids, moving only to positive neighbour ids.
     - Targeted at rank 1, the unrestricted shift had reached instance-0 neighbours, and the seed construction refused
       them, as designed.

     The checker, the stages and the run are unchanged; the suite then caught 40/40.
5. **Nothing in the contract was left unrun.**

## 19. What is established

- One six-gaze RGB bootstrap round, from the frozen NB1c list, with PERFECT / oracle correspondence, the accepted
  spherical geometry, local oracle segmentation and the accepted persistent-map machinery, produces **13 initialized
  persistent entity seed maps** (302,936 surfels) without any global-catalog initialization. 9 further local entities
  stay below the 100-point precondition.
- The PERFECT matcher and the AB1b geometry carry over to all six gazes:
  - 100 % of the measured points lie within 1 mm of the Position oracle;
  - rank 1 reproduces the accepted AB1b oracle and geometry exactly.
- Gaze 3 is dominated by non-catalog geometry (95.6 % instance 0). Gazes 4 and 5 extend entities rather than
  discovering new ones.
- On this round the 12-mm association never fires: the six cores are angularly disjoint, and multi-gaze entities are
  unions of disjoint parts.

## 20. What is NOT established

- **Natural correspondence or natural identity.** Both are oracle aids here. Blender instance identity merges physically
  separate pieces (entities 10, 110, 178).
- That these seeds will be serviceable by the accepted controller (NS1b). In particular, the accepted
  Controller-01 / Classroom-Oracle-1 controller domain is yaw ±25°, pitch ±20° (Breadth-1 records it), and **none of the
  six NB1c gazes lies inside it.** This is a fact for the design, not a test.
- That six gazes suffice for the scene, or that another gaze set would do better. None was run.
- Anything about instance-0 geometry, which has no seed by construction; about head motion, real cameras or other
  scenes.

## 21. Unresolved decision for Luiz / Chat

    IS THIS SEED SET READY FOR NORTH STAR-1b CONTROLLER HANDOFF?

The measured inputs:
- 13 initialized seeds, 5 large (≥ 12k surfels), 3 near the threshold;
- 9 small uninitialized entities;
- instance 0 dominating gaze 3;
- two redundant gazes;
- multi-part oracle entities;
- seeds spread over the whole sphere, outside the accepted ±25° / ±20° controller domain;
- the seed freeze `4ee36a1a…` and `seeds/seed-set.json` as the machine-facing handoff document.

This report makes no controller design.

NS1a REVIEW PENDING · NO CONTROLLER RUN YET · DECISION PENDING: READY FOR NS1b CONTROLLER HANDOFF?
