# Migration Conceptual Core 1 — report (2026-09-26)

Executed by Claude Code on the Ubuntu workstation against the committed contract
`docs/migration-conceptual-core-1.md`. Every number below is **MEASURED** from the
command shown, unless it is marked otherwise.

## Provenance

| item | value |
|---|---|
| active branch | `migration/conceptual-core-1` |
| parent accepted milestone | `main` @ `c47bc40220b6ea23c54de44b699977db1362d084` (local `main` fast-forwarded and verified equal to `origin/main`) |
| proposal head executed | `bef2d0c4d05c71a268bb7c928c1cb5bfac1f8045` (7 Chat-authored commits `5be1ea7`…`bef2d0c`, author Luiz Velho) |
| Code commits | map corrections, then this report, as two separate commits on top of `bef2d0c` |

Proposal commits: `5be1ea7` contract · `f3ba19f` measurement memory · `f41c57a` checker ·
`e65298f` map · `24de48b` incidental.py patch API · `d4842f2` Phase 8 · `bef2d0c` Phase 8b.

## Files changed (main...final head)

| file | change |
|---|---|
| `fov3d/reconstruction/measurement_memory.py` | new conceptual module (proposal) |
| `fov3d/experiments/classroom_partition/incidental.py` | private patch helper replaced by an import of `valid_patch_measurements` (proposal) |
| `fov3d/experiments/classroom_partition/integration.py` | three routing dicts, `_concat_*` helpers and `effective_target_geometry` removed; uses the memory (proposal) |
| `fov3d/experiments/classroom_partition/challenge_suite.py` | `_route_patch` / `_concat_xyz` removed; proposer and evaluator use the memory; no import from `integration` (proposal) |
| `tools/dev/check_conceptual_core1.py` | new fail-capable checker (proposal) |
| `docs/migration-conceptual-core-1.md` | contract (proposal) |
| `docs/conceptual-core-map.md` | audit map (proposal, **corrected by Code**; see Deviations) |
| `docs/migration-conceptual-core-1-report.md` | this report (Code) |

No implementation file was changed by Code. There are no changes outside the contract's
allowed paths. The protected `tools/*` runtime, golden signatures, scene assets and
baseline contracts are untouched (see `verify_baseline.sh` below).

## Boundary review before execution

The diff was reviewed against the contract before any gate ran. The structure matches:

- one conceptual implementation, `fov3d/reconstruction/measurement_memory.py`, outside the
  Classroom package;
- Phase 8 (`propose_phase8`) and Phase 8b (`propose_phase8b`, `evaluate_phase8b`) use
  it; the old pools are gone;
- `incidental.py` delegates patch filtering, and `HeadEvidence` stays experiment-side;
- no partition, topology, attention, constant or benchmark-semantics change;
- no remaining definition or use of `_valid_patch_samples` / `_route_patch` / `_concat_*`
  outside the new module (repository-wide search). `check_partition_graph8.py` still
  imports `effective_target_geometry` through `integration.py`, where it remains
  importable as a re-export.

## Final conceptual API (`fov3d.reconstruction.measurement_memory`)

    valid_patch_measurements(patch) -> (xyz float64[N,3], ids int32[N], mask bool[H,W])
        finite XYZ, valid == True, instance_id > 0; raster order; raises ValueError on bad shapes

    effective_target_geometry(historical_map_xyz_h, measured_instance_xyz_h) -> float64[M,3]
        finite historical rows, then finite measured rows; duplicates retained

    MeasurementSnapshot(xyz_h float32[N,3], source_global_index int32[N],
                        source_active_target_id int32[N])            # frozen
        copies and makes arrays read-only; raises on length mismatch or non-finite XYZ
        .empty()   .cross_target_mask(target_id)

    InstanceMeasurementMemory()
        .append_patch(patch, *, source_global_index>=0, source_active_target_id>0)
            -> {observed_instance: count}   routes by observed id, append-only
        .instance_ids() -> sorted tuple
        .snapshot(instance_id) -> MeasurementSnapshot  (empty if unseen)

## Architectural classification summary

The full table is in `docs/conceptual-core-map.md`. In short: `lift`, `joint` = chart,
partition and Classroom replay (G/P/C); `relations` = topology plus the superseded Phase-4
left-eye evidence (T/E/H); `incidental` = epistemic head-centred state (E);
`benchmark`, `prefix_benchmark`, `integration`, `challenge_suite` = benchmark/evaluation
(B/V), with `benchmark` also holding epistemic partition construction (E/P). The
instance-keyed measurement memory (M) is now the only concept outside the package.

## Gate A — interactive

Changed Python files (5) compiled with `.venv/bin/python -m py_compile`: OK.

```text
$ .venv/bin/python tools/dev/check_conceptual_core1.py
[conceptual-core1-check] PASS valid filtering count
[conceptual-core1-check] PASS valid filtering order
[conceptual-core1-check] PASS valid filtering raster mask
[conceptual-core1-check] PASS multi-instance routing counts
[conceptual-core1-check] PASS instance ids
[conceptual-core1-check] PASS provenance alignment
[conceptual-core1-check] PASS active-target independence
[conceptual-core1-check] PASS duplicate and insertion order
[conceptual-core1-check] PASS snapshot isolation
[conceptual-core1-check] PASS snapshot arrays read-only
[conceptual-core1-check] PASS effective geometry exact order
[conceptual-core1-check] PASS negative provenance invariant
[conceptual-core1-check] PASS negative patch-shape invariant
[conceptual-core1-check] SUMMARY checked=13 failed=0
```

**Fail-capability, measured.** A throw-away mutation harness (not committed) patched
the module in memory and reran the checker. It detected all five mutants, each with
exit 1:

| mutant | checks that failed |
|---|---|
| route by active target instead of observed id | 7 |
| deduplicate samples | 4 |
| measured XYZ before historical | effective geometry exact order |
| keep background / negative instance ids | 3 filtering checks |
| drop the provenance length check | negative provenance invariant, read-only |

Existing checkers (each `rc=0`, all under 0.2 s):

```text
[partition-graph1-check] SUMMARY checked=13 failed=0
[partition-graph2-check] SUMMARY checked=16 failed=0
[partition-graph3-check] SUMMARY checked=20 failed=0
[partition-graph4-check] SUMMARY checked=14 failed=0
[partition-graph5-check] SUMMARY checked=12 failed=0
[partition-graph6-check] SUMMARY checked=12 failed=0
[partition-graph7-check] SUMMARY checked=12 failed=0
[partition-graph8-check] SUMMARY checked=10 failed=0
[partition-graph8b-check] SUMMARY checked=12 failed=0
```

```text
$ .venv/bin/python tools/dev/check_fov3d_facade.py
[consolidation3-facade-check] SUMMARY checked=16 failed=0
$ scripts/verify_baseline.sh
[verify] 31 files tracked at baseline-classroom-oracle1-2026-09-25 are byte-identical in the working tree
[verify] SUMMARY passed=9 failed=0
$ git diff --check            # and git diff --check main...HEAD
(clean)
```

## Gate B — Phase-8b fresh proposer replay (Batch)

```text
$ R=/home/lvelho/rd/f3d-vision/previews
$ /usr/bin/time -f 'propose wall=%es maxrss=%MKB' .venv/bin/python tools/partition_graph8b_propose.py \
    $R/partition-graph-2-source-full $R/partition-graph-5-full $R/partition-graph-8-proposals \
    $R/conceptual-core-1-phase8b-proposals
[partition-graph8b-propose] COMPLETE {"eligible_candidates": 6489, "full_phase8_parity": 25, "raw_candidates": 18469, "scenarios": 5, "states": 125, "targets": 25, "truth_used": false}
propose wall=61.49s maxrss=581996KB
```

The inputs are the absolute paths recorded in the accepted `summary.json`. The summary
matches the contract exactly.

Tree comparison against the accepted `previews/partition-graph-8b-proposals`:

- file list identical: **503 files**;
- `diff -r -q`: no differences, so **byte-identical**;
- manifest hash (`find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum`):
  both `51a93fc464fc8ce00fc7f519ccadc25f539095be06de074788844b12ad6e7b7d`;
- the accepted tree still matches its recorded `partition-graph-8b-proposals.before.sha256`.

## Gate C — Phase-8 fresh integrator replay (authorized long gate)

Run only after Gates A and B passed.

```text
$ /usr/bin/time -f 'integrate wall=%es maxrss=%MKB' .venv/bin/python tools/partition_graph8_integrate.py \
    $R/partition-graph-2-source-full $R/partition-graph-5-full $R/partition-graph-7-proposals \
    $R/conceptual-core-1-phase8-proposals
[partition-graph8-integrate] COMPLETE {"candidate_regions": 16825, "phase7_global_parity": 104, "states": 104, "target_evidence_unmapped_cells": 0, "targets": 25, "truth_used": false}
integrate wall=658.16s maxrss=548752KB
```

Runtime was 658 s, against 653 s in Phase 8. The summary matches the contract exactly.

Tree comparison against the accepted `previews/partition-graph-8-proposals`:

- file list identical: **468 files**;
- `diff -r -q`: no differences, so **byte-identical**;
- manifest hash: both `69ccbfb748f250e19baebb75789e57c66f4c26443286e43a9a85ca77f474a209`;
- the accepted tree still matches its recorded `partition-graph-8-proposals.before.sha256`.

The fresh trees are under `previews/` (untracked and regenerable). The accepted trees
were only read.

## Golden baseline

```text
$ scripts/compare_golden.sh previews/partition-graph-2-source-full
[compare-golden] compared {"looks": 104, "npz_arrays_compared": 1348, "rgb_arrays_excluded": 337, "targets": 25}
[compare-golden] MISMATCHES 0
```

No other gate gave a reason to suspect the sealed runtime path, so no Blender/GPU smoke
was run.

## Deviations and repairs

- **Implementation repairs: none.** Every gate passed on the proposal as committed.
- **Map corrections (`docs/conceptual-core-map.md`, within contract scope):**
  1. Added the contract's classification column (vocabulary G/M/P/T/E/B/V/C/H). The
     proposed table described roles but did not classify them as the contract requires.
  2. `integration.py` and `challenge_suite.py` rows described the *pre-refactor* coupling
     (inline routing, duplicated pool, import from Phase 8). Rewritten to the live
     post-refactor state.
  3. `__init__.py` is not "none by itself": it re-exports `lift_run` for the Phase-2
     tools and checker.
  4. Added coupling the proposed map missed:
     - `lift.py`'s private chart helpers are imported by four later modules;
     - `FUSION_RADIUS_M = 0.012` is defined twice (`lift.py`, `benchmark.py`);
     - `joint.support_depth_from_map` feeds Phases 4, 5, 8 and 8b;
     - Phase 8 imports five private `prefix_benchmark` names;
     - `challenge_suite` imports four private `benchmark` helpers;
     - `relations.py` is a leaf that no later module imports and also holds the
       superseded Phase-4 left-eye `FineEvidence`.
  5. Extraction-order item 1 now names the private chart helpers and the single 12-mm
     constant source. The order itself is unchanged, and no later migration was
     performed.
- **Extra evidence, not required:** the mutation test above (scratchpad only).

## Scientific / runtime behavior

No scientific constant, chart resolution, 12-mm radius, budget, shell, eligibility
threshold, candidate definition, evaluation semantics, accepted proposal/evaluation tree,
golden signature, or controller/matcher/renderer/fusion/gaze/termination/scene behavior
was changed. Byte-identical Phase-8 and Phase-8b proposer outputs, `MISMATCHES 0` and
`verify_baseline.sh` 9/9 are the measured evidence.

## Unresolved

1. **`evaluate_phase8b` refactor is PROPOSED, not MEASURED.** The proposal also changed the
   Phase-8b evaluator's routing (memory plus a mirrored `target_start` table). No gate
   exercises it, and the contract forbids running the evaluator without a proposer
   mismatch. Static reading: it uses only `snapshot(iid).xyz_h`, which comes from the
   same filter/order/float32 path the proposer uses, and the proposer was measured
   byte-identical. Converting this to MEASURED needs a decision to run
   `tools/partition_graph8b_evaluate.py` (Batch, about 18 s in Phase 8b) and compare
   against `previews/partition-graph-8b-evaluation`.
2. `evaluate_phase8` changed only its import of the (byte-for-byte equivalent)
   `effective_target_geometry`. It is also not replayed.
3. **Architectural questions:**
   - `MeasurementSnapshot` fixes float32 storage, inherited from Phase 8. Is storage
     precision part of the concept or a replay artifact?
   - `valid_patch_measurements` is bound to the saved-patch dict schema
     (`xyz_h` / `instance_id` / `valid`). Should the conceptual layer define its own
     patch type?
   - `check_partition_graph8.py` still reaches `effective_target_geometry` through
     `integration.py`. It was left alone because editing existing checks is outside the
     delegated scope.

## Recommendation (next refactor only)

Map item 1, **spherical chart / observation state**: promote `lift.py`'s private chart
helpers (`_grid`, `_cells`, `_head_angles_from_unit`, `_head_unit_from_angles`) and one
`FUSION_RADIUS_M` source into a conceptual module. Nothing else. Parity gates: checkers
1–8b, the same Phase-8/8b byte-identical replays, plus a Phase-7 proposer replay, because
Phase 7 consumes these helpers directly.

## Success marker

    CONCEPTUAL_CORE1_REFACTOR_PRESERVES_BEHAVIOR
