# Migration Conceptual Core 11 — epistemic partition ownership

## Status

This is a structural migration only.

Accepted scientific milestone (parent):

    Conceptual Core 10 @ 85c09381584e30c3643bd55be23183f1cdbd2af7

Administrative provenance:
- `origin/main` was fast-forwarded `b69e0c9 → 85c0938` (Core 10 accepted by Luiz) with a
  plain, non-forced push.
- The Chat Handoff was then updated on main as `a312959ae9a07afca65d0c4781846517d1645344`
  (parent `85c0938`), from a detached administrative worktree that was removed
  afterwards.
- `migration/conceptual-core-11` was created from the new `origin/main` (`a312959`).

Design provenance: Luiz and Chat. Claude Code committed this contract in the dedicated
isolated Core-11 worktree **before** any production change. Luiz is the scientific and
acceptance authority. Chat is the architecture and review surface and does not mutate the
repository. Claude Code is the execution and mutation surface.

The governing rules remain:

    behavior migration first; representation/policy redesign second
    one causal question only

## Causal question

Can the accepted epistemic-region representation and partition constructor be moved out
of the Phase-6 benchmark module into the reusable epistemic layer without changing any
behavior?

## Why this boundary

`build_epistemic_partition` is no longer merely a Phase-6 helper. The Phase-6, Phase-7
(`prefix_benchmark`), Phase-8 (`integration`) and Phase-8b (`challenge_suite`) lineage all
share it as its epistemic partition representation. Core 11 establishes ownership only:

    HeadEvidence / causal state → fov3d.epistemic.partition → experiment/benchmark adapters → later policy work

It migrates the **accepted representation intact**. It does not decide which fields
ultimately belong to representation, benchmark annotation, candidate generation or
attention policy. **That separation is explicitly deferred to a later Core.**

## Bounded target and destination

Move, as one dependency-closed cluster, from
`fov3d/experiments/classroom_partition/benchmark.py` to the new
`fov3d/epistemic/partition.py`:

    REGION_KIND
    REGION_KIND_BY_CODE
    CANDIDATE_KINDS

    _component_labels
    _distance_to_target
    _touches_edge
    _centroid_angles
    _angular_distance_deg
    _region_interfaces

    build_epistemic_partition

The pre-contract measurement confirms closure. The seven functions' non-builtin globals
are exactly `Counter`, `defaultdict`, `math`, `cv2`, `np`, `chart_grid` and the cluster's
own names. The remaining `benchmark.py` code uses exactly one cluster name,
`build_epistemic_partition`.

## Semantics preserved literally (reference `85c0938`)

Nothing below is "improved":

- **A. Vocabulary.** `TARGET_SUPPORT` = 1, `OTHER_SURFACE` = 2, `UNKNOWN` = 3,
  `AMBIGUOUS_BOUNDARY` = 4 and `TARGET_EVIDENCE_UNMAPPED` = 5. `REGION_KIND_BY_CODE` is the
  exact inverse, and `CANDIDATE_KINDS = {"OTHER_SURFACE", "UNKNOWN"}`. Moving
  `CANDIDATE_KINDS` is a compatibility migration, **not** a judgment that candidate policy
  belongs in the representation.
- **B. Partition precedence** is exactly as implemented:

      target own support > ambiguous instance boundary > mapped/incidental other surface
        > unmapped target evidence > no head-centred depth (UNKNOWN)

  The boolean expressions and assignment order are preserved.
- **C. Surface identity.** The mapped-other, incidental-other and target-unmapped
  determinations, the ambiguity masking, the `surface_instance` assignment (with the
  mapped owner taking precedence where encoded) and the per-instance `OTHER_SURFACE`
  components are all preserved.
- **D. Connectivity.** `TARGET_SUPPORT`, `OTHER_SURFACE` and `TARGET_EVIDENCE_UNMAPPED`
  are 8-connected; `UNKNOWN` and `AMBIGUOUS_BOUNDARY` are 4-connected. It is not
  standardized.
- **E. Geometry and descriptors.** The following are preserved:
  - the `cv2.connectedComponents` and `cv2.distanceTransform` behavior;
  - the domain-edge test and the centroid computation;
  - the spherical angular-distance formula;
  - the gaze-distance and distance-to-target descriptors;
  - the mapped and incidental cell counts;
  - `seen_any_fraction` and `head_depth_fraction`.
- **F. `_region_interfaces`.** It keeps 4-neighbour cell-side interfaces, the filtering of
  non-zero regions, sorted pair keys, the exact `interface_edge_count` accumulation and the
  symmetric adjacency dictionary.
- **G. Region rows.** Every field keeps its meaning, type and construction:
  - `region_code`, `region_id`, `kind`, `candidate`, `instance_id`, `cell_count`;
  - `touches_domain_edge`, `centroid_yaw_deg`, `centroid_pitch_deg`;
  - `min_distance_to_target_deg`, `median_distance_to_target_deg`,
    `min_distance_to_historical_gaze_deg`;
  - `seen_any_fraction`, `head_depth_fraction`, `mapped_cells`, `incidental_cells`;
  - for `OTHER_SURFACE`, `surface_source` and `reconstruction_status`
    (`mapped_now`/`targeted_later`/`never_targeted`).

  These benchmark-flavoured fields are accepted behavior being migrated. This is not a
  claim that they belong permanently in the representation.
- **H. Candidate annotation.** `candidate = kind in CANDIDATE_KINDS`, exactly. It is not
  removed, altered, ranked or scored, and no policy is added.
- **I. Outputs.** The exact keys, values, types and ordering of `arrays`, `region_rows`,
  `edge_rows` and `diag` are preserved. That includes `target_evidence_unmapped_cells`,
  `ambiguous_boundary_cells`, `head_depth_cells`, `eye_ray_seen_cells` and
  `truth_used = False`.

No new validation, dataclass, enum, class or schema redesign is introduced. Every moved
function keeps its source text and AST; the constants keep their assignment source and
value.

## Destination dependencies

`fov3d.epistemic.partition` imports only what the cluster needs, using the exact existing
global objects:

    collections.Counter, collections.defaultdict, typing.Any, math, cv2, numpy,
    fov3d.geometry.head_chart.chart_grid

It must **not** depend on:
- `fov3d.experiments`, the filesystem (`pathlib`) or JSON;
- dense truth or benchmark evaluators;
- reconstruction measurement replay;
- Blender or the renderer, the controller or the matcher.

`fov3d/epistemic/__init__.py` is **not** modified. A bare `import fov3d.epistemic` stays
lightweight and does not import OpenCV or `fov3d.epistemic.partition`. The new module is
imported explicitly.

## Compatibility strategy (`benchmark.py`)

`benchmark.py` imports the ten moved names from `fov3d.epistemic.partition` and keeps
exposing them as **identical objects** (`benchmark.REGION_KIND … benchmark.build_epistemic_partition`).
No duplicate definition remains.

Apart from removing the moved cluster, adding the compatibility import, and removing
imports **measured** as orphaned, every remaining definition and non-import module
statement stays source-text identical to Core 10. The pre-contract AST name audit,
which includes annotations, measured the orphans:
- `cv2`, `defaultdict` and `math` become orphaned;
- `Any` stays, because it is still used in the remaining annotations;
- `Counter`, `deque`, `Path`, `json`, `np`, `chart_cells`, `chart_grid` and
  `SURFACE_ASSOCIATION_RADIUS_M` stay.

The final orphan set is re-measured after the extraction.

The compatibility imports remain for historical tools and checkers:
- `check_partition_graph7.py`, `check_partition_graph8.py` and
  `check_partition_graph8b.py`;
- `partition_graph6_demo.py`, `partition_graph7_demo.py` and `partition_graph8b_demo.py`.

These stay unmodified.

## Direct-consumer strategy

Production consumers take the moved names from the conceptual owner. Benchmark-only
helpers keep coming from `benchmark.py`.

| module | from `fov3d.epistemic.partition` | stays from `benchmark` |
|---|---|---|
| `prefix_benchmark.py` | `CANDIDATE_KINDS`, `REGION_KIND`, `REGION_KIND_BY_CODE`, `build_epistemic_partition` | `_covered` |
| `integration.py` | `build_epistemic_partition` | `_covered` |
| `challenge_suite.py` | `REGION_KIND`, `_region_interfaces`, `build_epistemic_partition` | `_covered` |

No other import is changed.

## Exclusions

The following stay in `benchmark.py`:
- `_json`, `_write_json` and `_guard_source_path`;
- `propose_phase6` and `evaluate_phase6`;
- `_covered` and `_miss_components`;
- the aliases `FUSION_RADIUS_M`, `_cells` and `_grid`, with their comment;
- all filesystem and path handling, dense-truth evaluation, golden checks, proposal-tree
  orchestration and report construction.

No other module changes except the three consumer import blocks.

## Allowed changes

    fov3d/epistemic/partition.py                          (new)
    fov3d/experiments/classroom_partition/benchmark.py    (remove cluster; compat import; measured orphans)
    fov3d/experiments/classroom_partition/prefix_benchmark.py  (import block only)
    fov3d/experiments/classroom_partition/integration.py       (import block only)
    fov3d/experiments/classroom_partition/challenge_suite.py   (import block only)
    tools/dev/check_conceptual_core11.py
    docs/migration-conceptual-core-11.md
    docs/migration-conceptual-core-11-report.md
    docs/conceptual-core-map.md   (after the implementation, checker and gates are complete)

## Core-11 checker

Add `tools/dev/check_conceptual_core11.py`. It must be deterministic, inexpensive, run
host-side, and be able to fail. It reads accepted Core 10 with
`git show 85c09381584e30c3643bd55be23183f1cdbd2af7`, and covers:

- **A. Literal structural identity.**
  - source-text and AST identity of every moved function;
  - assignment-source and value identity of the three constants;
  - equivalent `LOAD_GLOBAL` bindings;
  - no duplicates in `benchmark.py`, and the benchmark compatibility identities;
  - the direct consumers resolve the conceptual objects.
- **B. `_component_labels`.**
  - 4- versus 8-connectivity, background 0 and multiple components;
  - the returned component count, the label raster and the `int32` type.
- **C. `_distance_to_target`.**
  - no target gives a `+inf` raster, and target cells give 0;
  - distance increases away from the target, scaled by `grid_deg`;
  - the result is `float32`, with the accepted OpenCV distance-transform values.
- **D. `_touches_edge`.** An empty mask, an interior component, and each chart border.
- **E. `_centroid_angles`.** An empty mask gives nan/nan; an asymmetric mask checks the
  exact centroid mapping and catches x/y reversal.
- **F. `_angular_distance_deg`.**
  - identical directions give 0;
  - known yaw and pitch displacements, and a non-planar case;
  - degrees versus radians, and sign and order.
- **G. `_region_interfaces`.**
  - horizontal and vertical interfaces, with repeated edges accumulating;
  - background ignored, and sorted pair ids;
  - symmetric adjacency;
  - the exact edge-row keys, types and order.
- **H. `build_epistemic_partition`.** A compact synthetic raster fixture must
  independently witness each of these, strongly enough to distinguish precedence
  mutations:
  - every precedence level;
  - mapped versus incidental `OTHER_SURFACE`;
  - `AMBIGUOUS_BOUNDARY`, `TARGET_EVIDENCE_UNMAPPED` and `UNKNOWN`;
  - the `mapped_now`/`targeted_later`/`never_targeted` status;
  - distinct `OTHER_SURFACE` identities;
  - the connectivities;
  - candidate flags;
  - the target and gaze distance descriptors, and the seen/depth fractions;
  - adjacency and `adjacent_to_target_support`;
  - the region-code order;
  - the exact `arrays` and `diag` keys and the important values, including
    `truth_used = False`.
- **I. Package and import footprint.**
  - `fov3d/epistemic/__init__.py` is unchanged;
  - a bare `fov3d.epistemic` loads neither `cv2` nor `partition`;
  - an explicit `fov3d.epistemic.partition` loads `cv2` but no experiment, benchmark,
    filesystem/replay or stereo machinery;
  - there is no dependency cycle;
  - no rewired consumer takes a moved name through `benchmark`.

It prints:

    [conceptual-core11-check] SUMMARY checked=<N> failed=0

and exits nonzero on any failure.

## Mutation classes

The **final** checker is mutation-tested **before** it is committed. It must catch
meaningful non-equivalent mutants in these classes:

1. **Vocabulary and candidate compatibility:** a wrong code; a missing kind; a wrong
   `CANDIDATE_KINDS` member; the candidate flag inverted.
2. **Precedence:** ambiguous after other surface; target-unmapped before other surface;
   the `UNKNOWN` formula changed; the mapped/incidental overlap precedence changed.
3. **Connected components:** 4/8 changes; the wrong dtype; component-count or label
   errors.
4. **Target distance and geometry:** the wrong distance-transform mask; the wrong grid
   scaling; x/y centroid reversal; the edge test changed; degrees versus radians.
5. **Interfaces:** horizontal only; vertical only; background included; no accumulation;
   asymmetric adjacency; a string/numeric sorting mistake.
6. **Surface identity:** the mapped owner ignored; the incidental nearest ignored; the
   target identity treated as other; different non-target identities merged.
7. **Region construction:** connectivity changed by kind; the code order changed; a wrong
   `instance_id`; wrong mapped/incidental counts; changed source or status strings.
8. **Metadata:** `seen_any_fraction` or `head_depth_fraction` changed; the gaze distance
   omitted or wrong; the target-distance statistics changed;
   `adjacent_to_target_support` changed.
9. **Packaging:**
   - a duplicate benchmark definition, or a missing compatibility import;
   - a downstream module taking a conceptual name through `benchmark`;
   - an eager import from `fov3d/epistemic/__init__.py`;
   - an experiment dependency added to `epistemic.partition`.

Genuinely equivalent mutants are recorded separately. The checker is never weakened for
the score.

## Worktree guard

All measured work runs in the dedicated `migration/conceptual-core-11` worktree. Before
and after every measurement, the branch must be `migration/conceptual-core-11`, HEAD must
be the expected commit, and the tracked tree must be clean. Any unexpected change
invalidates the measurement and stops the step. The shared checkout is not used.

## Execution gates

**Gate A (structural and interactive, under the guard):**
- compile the changed Python files;
- run the Core-11 checker, then the Core-10 through Core-1 checkers;
- run the Partition-Graph checkers 1–8b, **unmodified**, and the facade check;
- run `scripts/verify_baseline.sh` (31/31),
  `scripts/compare_golden.sh previews/partition-graph-2-source-full` (`MISMATCHES 0`) and
  `git diff --check`;
- run fresh import footprints for `fov3d.epistemic`, `fov3d.epistemic.partition`,
  `benchmark`, `prefix_benchmark`, `integration` and `challenge_suite`.

**Fresh import/dependency audit.** Before any replay decision, record in fresh processes
which Partition-Graph producer/evaluator entry points load `fov3d.epistemic.partition` or
`fov3d.experiments.classroom_partition.benchmark`. The expected result is Phases 6, 7, 8
and 8b; this is **measured**. Phases 2–5 run only if they are reached. The approximately
11-minute Phase-8 proposer **is authorized** if the audit reaches it.

**Replays.** These use the established commands (from the committed Core-2/Core-4 reports,
with inputs matching those recorded in the accepted trees' `summary.json`), each to a
fresh `previews/conceptual-core-11-*` directory.

| gate | command | accepted reference | scope / exclusions |
|---|---|---|---|
| **Phase-6 proposer (primary)** | `tools/partition_graph6_propose.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/partition-graph-5-full <fresh>` | `partition-graph-6-proposals` | 102 files, none excluded |
| Phase-6 evaluator | `tools/partition_graph6_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-6-proposals <fresh>` | `partition-graph-6-evaluation` | 3 files; `demo/` 28, `demo-package-original/` 28 |
| Phase-7 proposer | `tools/partition_graph7_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-6-proposals <fresh>` | `partition-graph-7-proposals` | 835 files |
| Phase-7 evaluator | `tools/partition_graph7_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-7-proposals previews/partition-graph-6-evaluation <fresh>` | `partition-graph-7-evaluation` | 107 files; 107 + 107 excluded |
| Phase-8 proposer | `tools/partition_graph8_integrate.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-7-proposals <fresh>` | `partition-graph-8-proposals` | 468 files |
| Phase-8 evaluator | `tools/partition_graph8_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8-proposals previews/partition-graph-7-evaluation <fresh>` | `partition-graph-8-evaluation` | 107 files; 107 + 107 excluded |
| Phase-8b proposer | `tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals <fresh>` | `partition-graph-8b-proposals` | 503 files |
| Phase-8b evaluator | `tools/partition_graph8b_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8b-proposals previews/partition-graph-8-evaluation <fresh>` | `partition-graph-8b-evaluation` | 3 files; 8 + 8 excluded |

Only the reached phases run. The exact COMPLETE lines are recorded. Where practical,
`build_epistemic_partition` calls are instrumented on scratch output only.

## Byte-comparison discipline

- Use a fresh output directory, and treat accepted trees as read-only.
- Compare file sets in both directions, with no fresh file beneath an excluded path.
- Byte-compare every in-scope pair.
- Record deterministic `LC_ALL=C` scope manifests.
- Hash every accepted reference tree before the first replay and after the last
  replay/instrumentation. Any change invalidates the run.

## Acceptance

Core 11 passes only if all of the following hold:
- `fov3d.epistemic.partition` owns the exact cluster, with source/AST-preserved functions,
  preserved constants and equivalent global bindings;
- the benchmark compatibility identities hold, and the direct consumers resolve the
  conceptual implementation;
- no duplicate production implementation remains;
- `fov3d/epistemic/__init__.py` is unchanged and a bare `fov3d.epistemic` stays
  lightweight;
- no experiment or truth dependency enters `epistemic.partition`;
- the Core-11 checker passes and is demonstrably able to fail;
- all earlier checkers pass, the baseline is 31/31 and golden reports `MISMATCHES 0`;
- Phase 6 is byte-identical, and so is every downstream producer and evaluator the audit
  reaches;
- the accepted trees are unchanged;
- every changed production path maps to an executed gate.

## Permitted fixes

Only minimal mechanical import, wiring or checker defects inside the declared Core-11
scope may be fixed. If preservation would require changing epistemic region semantics,
candidate meaning, metadata semantics, benchmark or evaluation policy, accepted outputs,
or this contract, **stop and report**.

## Deferred (explicitly not part of Core 11)

1. **Separating representation from policy.** `CANDIDATE_KINDS`, the candidate flag,
   `targeted_later`/`reconstruction_status` and the historical-gaze descriptors remain
   accepted compatibility semantics.
2. The `_own_labels` versus `own_support_labels` cleanup.
3. The `component_lineage` versus `fov3d.scene.lineage._lineage` cleanup.
4. The `attach_state_region_codes` rename.
5. The consumerless compatibility aliases.
6. The target-relative `HeadEvidence` placement.
7. The cleanup of the separate historical Phase-2/Phase-3 boundary lineage.

No Core-12 redesign is made in this run. Commit and push the completed branch, then stop
for review by Luiz and Chat. Core 11 is not merged without Luiz's explicit acceptance.

Success marker:

    CONCEPTUAL_CORE11_EPISTEMIC_PARTITION_PRESERVES_BEHAVIOR
