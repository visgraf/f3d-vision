# Migration Conceptual Core 12 — candidate policy separated from the epistemic partition

## Status

This is the **first intentional redesign Core**. Cores 1–11 moved accepted behavior
without changing structure beyond ownership. Core 12 changes one concept, the
representation/policy boundary. Every accepted observable product must be reproduced
exactly.

Accepted scientific milestone (parent):

    Conceptual Core 11 @ d324e098c859a3b7ea1e91c7526f5cda854bcaf7
    CONCEPTUAL_CORE11_EPISTEMIC_PARTITION_PRESERVES_BEHAVIOR

Administrative provenance:
- The remote state was verified before acceptance: `origin/main = a312959`,
  `origin/migration/conceptual-core-11 = d324e09`. `d324e09` descends from `a312959`, being
  6 ahead and 0 behind, and `CLAUDE.md` was unchanged.
- `origin/main` was fast-forwarded `a312959 → d324e09` (Core 11 accepted by Luiz) with a
  plain, non-forced push.
- The Chat Handoff was then updated on main as `9eb9d9936cd2198fe63b7b9f076455f2114da70d`
  (parent `d324e09`), from a detached administrative worktree that was removed afterwards.
- `migration/conceptual-core-12` was created from the new `origin/main` (`9eb9d99`).

Design provenance: Luiz and Chat. Claude Code committed this contract in the dedicated
isolated Core-12 worktree **before** any production change. Luiz is the scientific and
acceptance authority. Chat is the architecture and review surface and does not mutate the
repository. Claude Code is the execution and mutation surface.

Governing rules:

    simplest falsifiable change;
    preserve accepted observable behavior;
    separate one concept at a time.

## Causal question

Can candidate status be removed from the intrinsic epistemic partition and expressed
instead as a separate historical candidate interpretation, while reproducing every
accepted Phase-6/7/8/8b observable product exactly?

    accepted Core-11 partition  =  pure epistemic partition  +  historical candidate annotation

This is the only conceptual question in Core 12.

## Scientific / architectural claim

Core 11 conflates a region's **epistemic state** (its `kind`) with a historical benchmark's
decision to **call** that region a candidate
(`CANDIDATE_KINDS = {"OTHER_SURFACE", "UNKNOWN"}` → `region["candidate"]` and
`diag["candidate_region_count"]`). Phase 8b already computes a different interpretation
of the same epistemic structure: `candidate_raw = kind in {"UNKNOWN", "OTHER_SURFACE"}`
and `eligible_candidate = candidate_raw and cells >= MIN_ELIGIBLE_CELLS`, over refined
regions and UNKNOWN shells. So candidate status is an interpretation, not intrinsic
identity:

    region.kind  ≠  region.candidate          candidate = interpretation(region)

Target architecture after Core 12:

    causal evidence
        → fov3d.epistemic.partition                      (pure epistemic representation)
        → regions / topology / evidence descriptors
        → classroom_partition.candidate_policy           (historical candidate interpretation)
        → candidate-annotated compatibility view
        → Phase 6 / 7 / 8 / 8b historical pipeline

## Pure epistemic partition — exact boundary

`fov3d/epistemic/partition.py` keeps owning `REGION_KIND`, `REGION_KIND_BY_CODE`,
`_component_labels`, `_distance_to_target`, `_touches_edge`, `_centroid_angles`,
`_angular_distance_deg`, `_region_interfaces` and `build_epistemic_partition`.

It **stops** owning exactly three things, each removed as one line of the accepted Core-11
source:

| removed | Core-11 source line |
|---|---|
| the constant | `CANDIDATE_KINDS = {"OTHER_SURFACE", "UNKNOWN"}` |
| the row entry | `"candidate": bool(kind in CANDIDATE_KINDS),` |
| the diag entry | `"candidate_region_count": sum(bool(r["candidate"]) for r in region_rows),` |

The module docstring is updated to describe the pure representation. **Everything else is
unchanged**:
- the class vocabulary and its precedence;
- `surface_instance` and the mapped/incidental semantics;
- region construction, connectivity, region order and region codes;
- interfaces and adjacency;
- the target-distance descriptors and the gaze-history descriptor;
- `reconstruction_status` and `surface_source`;
- `seen_any_fraction` and `head_depth_fraction`;
- `arrays` and all other diag fields;
- the function arguments and signature, the helper functions, the constants and the
  imports.

Concretely, the pure builder source is the Core-11 source minus exactly those two lines,
and its AST is the Core-11 AST minus exactly those two dict entries.

`fov3d/epistemic/__init__.py` is **not** modified.

## Historical candidate interpretation

New experiment-side module: `fov3d/experiments/classroom_partition/candidate_policy.py`.
It is deliberately experiment-side. **No** generic `fov3d.attention` package is created,
because the historical rule is not an accepted universal attention policy.

Final public names:

    CANDIDATE_KINDS = {"OTHER_SURFACE", "UNKNOWN"}
    annotate_candidate_partition(region_rows, diag) -> (region_rows, diag)
    build_candidate_partition(state, *, target_id, target_name, all_target_ids,
                              domain, grid_deg, gazes_deg) -> (arrays, region_rows, edge_rows, diag)

It also has one private helper, `_insert_after(mapping, anchor, key, value)`. This returns
a copy of `mapping` with `key` inserted immediately after `anchor`. It raises `ValueError`
if `key` is already present and `KeyError` if `anchor` is missing, so double annotation or
a mis-wired input fails loudly.

- **`annotate_candidate_partition`** is non-mutating. It returns new row dicts with
  `"candidate": bool(row["kind"] in CANDIDATE_KINDS)` inserted **immediately after
  `"kind"`**. It returns a new diag with
  `"candidate_region_count": sum(bool(r["candidate"]) for r in rows)`, a Python `int`,
  inserted **immediately after `"region_count"`**. It reproduces the accepted Core-11
  in-memory dictionaries type- and key-order-strictly, not merely their serialization.
  Nested values (for example `adjacent_regions`) are shared, not copied; the pure rows
  are discarded by the wrapper.
- **`build_candidate_partition`** has the same keyword-only signature as the accepted
  builder. It calls `fov3d.epistemic.partition.build_epistemic_partition(...)`, applies
  `annotate_candidate_partition` to its rows and diag, and returns
  `(arrays, annotated_rows, edges, annotated_diag)`. `arrays` and `edges` are returned
  unchanged, as the same objects. It defines no ranking, score, gaze or continuation
  rule.

Dependencies: `typing.Any`, `numpy` (annotations), and
`fov3d.epistemic.partition.build_epistemic_partition`. There is **no** dependency on
`benchmark`, `prefix_benchmark`, `integration`, `challenge_suite`, dense truth,
evaluators, stereo or rendering.

## Historical compatibility (`benchmark.py`)

- `from fov3d.epistemic.partition import (...)` keeps the eight representation names
  `REGION_KIND`, `REGION_KIND_BY_CODE`, `_angular_distance_deg`, `_centroid_angles`,
  `_component_labels`, `_distance_to_target`, `_region_interfaces` and `_touches_edge`.
  `CANDIDATE_KINDS` and `build_epistemic_partition` leave this import.
- A new import brings in `CANDIDATE_KINDS` and `build_candidate_partition` from
  `candidate_policy`, so that `benchmark.CANDIDATE_KINDS is candidate_policy.CANDIDATE_KINDS`.
- The compatibility alias `build_epistemic_partition = build_candidate_partition` is added
  in the existing backward-compatible aliases block, directly after `_grid = chart_grid`.
  So `benchmark.build_epistemic_partition(...)` still returns the exact accepted Core-11
  candidate view that the unmodified Partition-Graph checkers 6, 7 and 8 assert.
- `propose_phase6` calls `build_candidate_partition(...)` explicitly; only the called name
  changes.
- No duplicate partition implementation.

Every other statement of `benchmark.py` is unchanged from Core 11.

## Direct-consumer wiring

The historical producers take the **explicit candidate view**. None consumes the pure
builder while expecting candidate fields.

| module | from `fov3d.epistemic.partition` | from `candidate_policy` | stays from `benchmark` | call sites renamed to `build_candidate_partition` |
|---|---|---|---|---|
| `benchmark.py` | eight representation names | `CANDIDATE_KINDS`, `build_candidate_partition` | — | `propose_phase6` (1) |
| `prefix_benchmark.py` | `REGION_KIND`, `REGION_KIND_BY_CODE` | `build_candidate_partition` | `_covered` | `propose_phase7` (1) |
| `integration.py` | — | `build_candidate_partition` | `_covered` | `propose_phase8` (2) |
| `challenge_suite.py` | `REGION_KIND`, `_region_interfaces` | `build_candidate_partition` | `_covered` | `propose_phase8b` (1): the base integrated partition, whose FULL parity against the saved Phase-8 rows includes `candidate` |

Measured before this contract:
- `prefix_benchmark` imports `CANDIDATE_KINDS` but never uses it (AST name audit including
  annotations), and no module imports it through `prefix_benchmark`. It is a genuine
  orphan, and **only that import is removed**.
- `REGION_KIND`, `REGION_KIND_BY_CODE` and `defaultdict` are also unused inside
  `prefix_benchmark`, but they are **kept**: they are not orphans created by this change.
- `integration`'s pre-existing unused `AREA_BINS` and `defaultdict` are likewise kept.

**Phase 8b keeps its distinct interpretation, unchanged.** That covers `candidate_raw` and
`eligible_candidate`, `MIN_ELIGIBLE_CELLS`, the UNKNOWN shells, and in particular its
independent literal `kind in {"UNKNOWN", "OTHER_SURFACE"}`. That literal is **not**
replaced by `CANDIDATE_KINDS`: the duplication is evidence that several candidate
interpretations can exist over one epistemic representation.

## Central Core-12 invariant

The reference is accepted Core 11 at `d324e098c859a3b7ea1e91c7526f5cda854bcaf7`, executed
from `git show d324e09:fov3d/epistemic/partition.py` as a reference module. For any valid
input state, let:
- `OLD` = accepted Core-11 `build_epistemic_partition(...)`;
- `PURE` = Core-12 `fov3d.epistemic.partition.build_epistemic_partition(...)`;
- `REANNOTATED` = `candidate_policy` applied to `PURE`.

Then:
1. the `PURE` arrays equal the `OLD` arrays exactly (keys, key order, dtypes, shapes,
   values);
2. the `PURE` edges equal the `OLD` edges exactly;
3. the `PURE` region rows equal the `OLD` region rows with **only** `"candidate"` removed,
   preserving row order, the remaining key order, values and types;
4. the `PURE` diag equals the `OLD` diag with **only** `"candidate_region_count"` removed,
   preserving the remaining key order, values and types;
5. `REANNOTATED == OLD`, type- and key-order-strictly.

## Exclusions

Core 12 does not touch:
- the historical/context annotations `reconstruction_status`
  (`mapped_now`/`targeted_later`/`never_targeted`) and `surface_source`;
- `min_distance_to_historical_gaze_deg`;
- Phase-8b candidate refinement;
- `fov3d/epistemic/__init__.py`;
- unrelated functions.

It creates no generic attention package, and there is no Core 13 in this run. It edits no
historical checker or tool.

## Allowed changes

    fov3d/epistemic/partition.py                              (three lines removed; module docstring)
    fov3d/experiments/classroom_partition/candidate_policy.py (new)
    fov3d/experiments/classroom_partition/benchmark.py        (imports; alias; one call name)
    fov3d/experiments/classroom_partition/prefix_benchmark.py (imports incl. orphan CANDIDATE_KINDS; one call name)
    fov3d/experiments/classroom_partition/integration.py      (import; two call names)
    fov3d/experiments/classroom_partition/challenge_suite.py  (imports; one call name)
    tools/dev/check_conceptual_core12.py
    docs/migration-conceptual-core-12.md
    docs/migration-conceptual-core-12-report.md
    docs/conceptual-core-map.md   (after the implementation, checker and gates are complete)

## Historical-checker supersession

The accepted `tools/dev/check_conceptual_core11.py` asserts the **old** structure:
- `CANDIDATE_KINDS` lives in `epistemic.partition`;
- `region["candidate"]` is produced by the intrinsic builder;
- `benchmark.build_epistemic_partition` is the conceptual builder object.

Core 12 intentionally changes those facts. So:
- **A.** The accepted Core-11 checker is **not modified**. It is verified at the accepted
  Core-11 SHA in a read-only detached reference worktree, where it must report 59/59.
- **B.** At the Core-12 head, Core-11 structural identity is **not** a pass gate.
- **C.** The Core-12 checker subsumes every still-relevant Core-11 behavioral guarantee.
  Core 11's hand-derived helper and partition fixtures are carried over, with and without
  candidate. It also explicitly tests the representation/policy split.
- **D.** The Core-1 to Core-10 conceptual checkers stay current-head gates, unmodified.
- **E.** Partition-Graph checkers 1–8b stay current-head gates, **unmodified**, passing
  through the compatibility layer.

This is an explicit architectural-checker supersession, not a regression.

## Core-12 checker

Add `tools/dev/check_conceptual_core12.py`. It is deterministic, inexpensive, host-side and
fail-capable. It reads the reference with `git show d324e09…`, prints
`[conceptual-core12-check] SUMMARY checked=<N> failed=0`, and exits nonzero on any failure.

- **A. Pure-module structure.**
  - `REGION_KIND` and `REGION_KIND_BY_CODE` have identical source, value and order;
  - `CANDIDATE_KINDS` is absent from `epistemic.partition`;
  - the six helpers have identical source and AST;
  - `build_epistemic_partition` has an identical signature, and its source and AST equal
    Core 11 minus exactly the two entries;
  - no operational `"candidate"` or `"candidate_region_count"` construction (non-docstring
    string constants), and no `CANDIDATE_KINDS` name;
  - the import statements are identical to Core 11, with no experiment import.
- **B. Pure projection equivalence.** Core-12 `PURE` is compared with Core-11 `OLD`
  projected, over the deterministic fixtures: arrays and dtypes, shapes, rows (count,
  order, key order, values, types), edges, adjacency, diag (key order, values, types).
  The fixtures witness:
  - all five kinds, precedence, and mapped/incidental overlap and identity;
  - all `reconstruction_status` and `surface_source` values;
  - 4/8 connectivity;
  - the target-free and no-gaze cases;
  - distances, adjacency, interfaces and edge touching;
  - the malformed-shape error.

  The hand-derived Core-11 expectations are also checked directly on the pure output
  (without `candidate`).
- **C. Candidate interpretation.**
  - `CANDIDATE_KINDS == {"OTHER_SURFACE", "UNKNOWN"}` (a `set`);
  - the per-kind flags are UNKNOWN/OTHER_SURFACE → `True` and the other three → `False`;
  - every row retained, with no reordering and no other field changed;
  - `candidate` sits immediately after `kind` and is a Python `bool`;
  - the count is correct, a Python `int`, immediately after `region_count`;
  - the inputs are not mutated;
  - double annotation and a missing anchor fail.
- **D. Reconstitution identity.** For every fixture, `build_candidate_partition(...)` is
  type-, order- and value-identical to Core-11 `build_epistemic_partition(...)`. `arrays`
  and `edges` are passed through as the pure objects.
- **E. Historical benchmark compatibility.**
  - `benchmark.CANDIDATE_KINDS is candidate_policy.CANDIDATE_KINDS`;
  - `benchmark.build_epistemic_partition is candidate_policy.build_candidate_partition`,
    and it produces the accepted view;
  - the eight representation names resolve to `epistemic.partition`;
  - no duplicate definition;
  - `propose_phase6` resolves the wrapper;
  - `benchmark`'s imports and statements equal Core 11 apart from the declared changes
    (normalized AST).
- **F. Direct-consumer wiring.**
  - each of `prefix_benchmark`, `integration` and `challenge_suite` resolves and calls
    `build_candidate_partition`;
  - no historical producer module imports or calls the pure builder;
  - `REGION_KIND`/`REGION_KIND_BY_CODE` still come from `epistemic.partition`, and
    `_covered` from `benchmark`;
  - the consumers equal Core 11 apart from the declared import and call-name changes
    (normalized AST);
  - Phase 8b's own `candidate_raw`/`eligible_candidate` logic is unchanged: its source
    keeps the independent literal, and it does not reference `CANDIDATE_KINDS` or
    `candidate_policy` beyond the wrapper import;
  - it behaves independently: its output is unchanged when `candidate_policy.CANDIDATE_KINDS`
    is temporarily replaced, while the wrapper's flags do change, a live control.
- **G. Package footprints (fresh processes).**
  - a bare `fov3d.epistemic` loads no `cv2`, no `partition` and no `candidate_policy`;
  - `fov3d.epistemic.partition` loads `cv2` and the exact Core-11 module list, with no
    experiments and no `candidate_policy`;
  - `candidate_policy` loads exactly the measured experiment-package footprint plus
    `fov3d.epistemic`, `fov3d.epistemic.partition` and `candidate_policy`, with no
    `benchmark`/`prefix_benchmark`/`integration`/`challenge_suite`, no dense truth or
    evaluator, no stereo and no renderer;
  - no dependency cycle.

  The measured package footprint: a bare `import fov3d.experiments.classroom_partition`
  already loads `lift` and 11 `fov3d` modules, plus `cv2`.
- **H. Random differential (in the checker, seeded).** Hundreds of valid small synthetic
  states vary raster size, target support, owner and nearest identities, ambiguity,
  depth/seen masks, `all_target_ids`, domain, grid scale and gaze lists. On each,
  `REANNOTATED(PURE) == OLD` and `PURE == project(OLD)`, type-strictly. It includes
  non-equivalent controls (a candidate appended at the wrong position, and a different
  kind set) that must be detected.

  A larger out-of-checker run with thousands of states and mutant controls is recorded in
  the report.

## Mutation classes

The **final** checker is mutation-tested **before** it is committed. It must catch:
1. **Pure/policy boundary:**
   - `candidate` still emitted by the pure partition;
   - `CANDIDATE_KINDS` retained in the pure module;
   - `candidate_region_count` retained in the pure diag;
   - the pure builder importing `candidate_policy`;
   - the pure module importing an experiment.
2. **Candidate rule:**
   - UNKNOWN removed or OTHER_SURFACE removed;
   - TARGET_SUPPORT, AMBIGUOUS_BOUNDARY or TARGET_EVIDENCE_UNMAPPED added;
   - the flag inverted;
   - the constant changed.
3. **Reconstitution:**
   - `candidate` or `candidate_region_count` at the wrong position;
   - a wrong count;
   - a row filtered, or rows reordered;
   - another row field or a diag field changed;
   - arrays copied with a dtype change;
   - edges modified.
4. **Pure partition regression**, caught by projection equivalence against accepted
   Core 11: precedence, connectivity, surface identity, distances, interface
   accumulation, adjacency, region ordering, `reconstruction_status`, the gaze
   descriptor.
5. **Wiring:**
   - `benchmark`, `prefix_benchmark`, `integration` or `challenge_suite` using the pure
     builder directly;
   - the compatibility alias removed;
   - a duplicate builder added.
6. **Phase-8b conceptual separation:** replacing or coupling `candidate_raw` or
   `eligible_candidate` to the Core-12 wrapper or constant.

Genuinely equivalent mutants are recorded separately. The checker is never weakened for
the score.

## Worktree guard

All measured work runs in the dedicated `migration/conceptual-core-12` worktree. Before
and after every measurement, the branch, the expected HEAD and a clean tracked tree are
required. Any unexpected change invalidates the measurement and stops the step. The shared
checkout is not used.

## Execution gates

**Gate A (under the guard):**
- compile the changed Python;
- run the Core-12 checker;
- run the Core-10 to Core-1 conceptual checkers, **unmodified**;
- verify the accepted Core-11 checker at `d324e09` in a read-only detached reference
  worktree (59/59);
- run the Partition-Graph checkers 1–8b, **unmodified**, and the facade check;
- run `scripts/verify_baseline.sh` (31/31),
  `scripts/compare_golden.sh previews/partition-graph-2-source-full` (`MISMATCHES 0`) and
  `git diff --check`;
- run fresh import footprints for `fov3d.epistemic`, `fov3d.epistemic.partition`,
  `candidate_policy`, `benchmark`, `prefix_benchmark`, `integration` and
  `challenge_suite`.

**Fresh import/dependency audit.** Before any replay decision, record in fresh processes
which Partition-Graph producer/evaluator entry points load `fov3d.epistemic.partition`,
`candidate_policy` or `benchmark`. The expected result is Phases 6, 7, 8 and 8b; this is
**measured**. Phases 2–5 run only if they are reached.

**Replays.** Every reached producer and evaluator is replayed with the established Core-11
commands, each to a fresh `previews/conceptual-core-12-*` directory:

| gate | command (after `.venv/bin/python`) | accepted reference | scope / exclusions |
|---|---|---|---|
| Phase-6 proposer | `tools/partition_graph6_propose.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/partition-graph-5-full <fresh>` | `partition-graph-6-proposals` | 102 files |
| Phase-6 evaluator | `tools/partition_graph6_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-6-proposals <fresh>` | `partition-graph-6-evaluation` | 3; `demo/` 28, `demo-package-original/` 28 |
| Phase-7 proposer | `tools/partition_graph7_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-6-proposals <fresh>` | `partition-graph-7-proposals` | 835 |
| Phase-7 evaluator | `tools/partition_graph7_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-7-proposals previews/partition-graph-6-evaluation <fresh>` | `partition-graph-7-evaluation` | 107; 107 + 107 |
| Phase-8 proposer | `tools/partition_graph8_integrate.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-7-proposals <fresh>` | `partition-graph-8-proposals` | 468 |
| Phase-8 evaluator | `tools/partition_graph8_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8-proposals previews/partition-graph-7-evaluation <fresh>` | `partition-graph-8-evaluation` | 107; 107 + 107 |
| Phase-8b proposer | `tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals <fresh>` | `partition-graph-8b-proposals` | 503 |
| Phase-8b evaluator | `tools/partition_graph8b_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8b-proposals previews/partition-graph-8-evaluation <fresh>` | `partition-graph-8b-evaluation` | 3; 8 + 8 |

The acceptance target is all reached outputs byte-identical.

Cost classes:
- the checker and Gate A are interactive;
- the replays are batch; the Phase-8 proposer is about 11 min (658 s in Core 11), is
  required by this contract, and runs **once**;
- the out-of-checker differential is batch.

**Instrumentation.** One-to-one counts of pure `build_epistemic_partition`,
`annotate_candidate_partition` and `build_candidate_partition` calls, by binding:
- for the expensive Phase-8 proposer, the **required replay itself** is instrumented (the
  unmodified entry script run through a counting `runpy` wrapper into its fresh
  `previews/` directory), so no second ~11-minute run is made;
- the other phases run with the plain established command as the replay, plus a cheap
  instrumented run into scratch space.

The expected counts, from Core 11, are Phase-6 25, Phase-7 208, Phase-8 208 (**not yet
measured in Core 11**), Phase-8b 125, and evaluators 0. These are expectations, not
assumptions. Candidate counts are reconciled with the accepted products where meaningful.

## Byte-comparison discipline

- Use fresh output directories, and treat accepted trees as read-only.
- Compare file sets in both directions, with the established exclusions only and no fresh
  file beneath an excluded path.
- Byte-compare every in-scope pair.
- Record deterministic `LC_ALL=C` scope manifests and the exact COMPLETE lines.
- Hash all 13 accepted reference trees before the first replay and after the last replay
  and instrumentation. They must be unchanged.

## Acceptance

Core 12 passes only if all of the following hold:
- the intrinsic `epistemic.partition` no longer owns candidate semantics, and its output is
  exactly Core 11 minus only `region["candidate"]` and `diag["candidate_region_count"]`;
- `candidate_policy` reconstructs the accepted Core-11 output exactly;
- `benchmark`'s historical compatibility is intact;
- all unmodified Partition-Graph checkers pass;
- the Core-1 to Core-10 conceptual checkers pass at the current head;
- the accepted Core-11 checker passes at `d324e09`;
- the Core-12 checker is fail-capable;
- the randomized reconstitution differential is clean;
- no experiment dependency enters `epistemic.partition`;
- Phase 8b's separate candidate semantics remain independent;
- the baseline is 31/31 and golden reports `MISMATCHES 0`;
- every reached Phase-6/7/8/8b product is byte-identical;
- the accepted reference trees are unchanged;
- every changed production path maps to an executed gate.

## Permitted fixes

Only minimal mechanical import, wiring or checker defects inside the declared Core-12
scope may be fixed. If preservation would require changing epistemic semantics, the
historical candidate rule, Phase-8b candidate refinement, metadata semantics, accepted
outputs or this contract, **stop and report**.

## Deferred (explicitly not part of Core 12)

1. `reconstruction_status` (`mapped_now` / `targeted_later` / `never_targeted`), which is
   Core-13 design.
2. `min_distance_to_historical_gaze_deg`.
3. Other historical/context annotations, pending Core-13 design.
4. The placement of the target-relative `HeadEvidence` fields.
5. `_own_labels` versus `own_support_labels`.
6. `component_lineage` versus `scene.lineage._lineage`.
7. The `attach_state_region_codes` rename.
8. The consumerless compatibility aliases.
9. The historical Phase-2/Phase-3 boundary lineage cleanup.

Commit and push the completed branch, then stop for review by Luiz and Chat. Core 12 is not
merged without Luiz's explicit acceptance.

Success marker:

    CONCEPTUAL_CORE12_CANDIDATE_POLICY_SEPARATION_PRESERVES_BEHAVIOR
