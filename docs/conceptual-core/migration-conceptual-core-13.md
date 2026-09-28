# Migration Conceptual Core 13 — reconstruction status as historical run context

## Status

This is the **second intentional redesign Core**. Core 12 separated candidate status from
the intrinsic epistemic partition. Core 13 separates one more concept: the historical
experiment's **run context**. Every accepted historical observable must be reproduced
exactly.

Accepted scientific milestone (parent):

    Conceptual Core 12 @ 872ac45405c796a0e8b0cd4455bd17c12c7542db
    CONCEPTUAL_CORE12_CANDIDATE_POLICY_SEPARATION_PRESERVES_BEHAVIOR

Administrative provenance:
- The remote state was verified before acceptance: `origin/main = 9eb9d99`,
  `origin/migration/conceptual-core-12 = 872ac45`. `872ac45` descends from `9eb9d99`, being
  5 ahead and 0 behind; `CLAUDE.md` was unchanged and the shared checkout untouched.
- `origin/main` was fast-forwarded `9eb9d99 → 872ac45` (Core 12 accepted by Luiz) with a
  plain, non-forced push.
- The Chat Handoff was then updated on main as `8279cb2f160f0b0b00c69f4c888e9e0de61a5a23`
  (parent `872ac45`), from a detached administrative worktree that was removed afterwards.
- `migration/conceptual-core-13` was created from the new `origin/main` (`8279cb2`),
  without tracking `main`, and pushed with its own remote branch as upstream.

Design provenance: Luiz and Chat. Claude Code committed this contract in the dedicated
isolated Core-13 worktree **before** any production change. Luiz is the scientific and
acceptance authority. Chat is the architecture and review surface. Claude Code is the
execution and mutation surface.

Governing principle:

    simplest falsifiable redesign  +  preserve every accepted historical observable

## Causal question

Can `reconstruction_status` and the dependency on `all_target_ids` be removed from the
intrinsic epistemic partition and expressed instead as an experiment-side run-context
annotation, while reproducing every accepted Core-12 historical product exactly?

    accepted Core-12 intrinsic partition  =  Core-13 intrinsic partition
                                          +  historical reconstruction-status annotation

This is the only conceptual question in Core 13.

## The semantic distinction

For `OTHER_SURFACE` regions, the accepted Core-12 intrinsic partition emits two fields
that look alike but mean different things:

| field | values | determined by | meaning | Core 13 |
|---|---|---|---|---|
| `surface_source` | `mapped`, `incidental`, `mapped_and_incidental` | the current state only (`mapped_cells`, `incidental_cells`) | **causal evidence provenance**: how is this surface known? | **stays intrinsic**, unchanged |
| `reconstruction_status` | `mapped_now`, `targeted_later`, `never_targeted` | `mapped_cells` **and `all_target_ids`**, the prerecorded experiment's target schedule | **historical run context**: what the experiment will do with this object | **moves** to the experiment-side run-context layer |

An autonomous epistemic representation should not need to know which objects a
prerecorded experiment will target later. Core 13 therefore separates only
`reconstruction_status` and the `all_target_ids` dependency. `surface_source`,
`mapped_cells` and `incidental_cells` stay intrinsic.

Target architecture after Core 13:

    causal evidence
        → fov3d.epistemic.partition           (kinds, identity, geometry, topology,
                                                evidence statistics, surface_source)
        → classroom_partition.run_context     (historical schedule → reconstruction_status)
        → classroom_partition.candidate_policy (historical candidate interpretation)
        → candidate-annotated historical view
        → Phase 6 / 7 / 8 / 8b

No general controller package is introduced.

## Exact intrinsic change

`fov3d/epistemic/partition.py`. The signature becomes:

    build_epistemic_partition(state, *, target_id, target_name, domain, grid_deg, gazes_deg)

That is, the accepted Core-12 signature minus exactly the `all_target_ids` keyword-only
parameter.

Exactly six lines of the accepted Core-12 source are removed:

```text
-    all_target_ids: set[int],
-                row["reconstruction_status"] = (
-                    "mapped_now" if mapped_n
-                    else "targeted_later" if int(instance_id) in all_target_ids
-                    else "never_targeted"
-                )
```

The module docstring is updated only as needed. **Everything else is unchanged**:
- `REGION_KIND` and `REGION_KIND_BY_CODE`;
- the six helpers and the imports;
- precedence, `class_code` and `surface_instance`;
- connectivity, region order and codes;
- the centroids;
- the target-distance descriptors and the historical-gaze descriptor;
- `seen_any_fraction` and `head_depth_fraction`;
- `mapped_cells` and `incidental_cells`;
- **`surface_source`**, with its `if kind == "OTHER_SURFACE" and instance_id is not None:`
  block and its selection chain;
- topology, interfaces and adjacency;
- `arrays`, the diagnostics and the exceptions.

`min_distance_to_historical_gaze_deg` and `gazes_deg` are **not** touched; they are the
Core-14 question. `fov3d/epistemic/__init__.py` is **not** modified.

## New run-context layer

New experiment-side module: `fov3d/experiments/classroom_partition/run_context.py`. It
owns the historical schedule-dependent interpretation. Final names are as proposed:

    annotate_reconstruction_status(region_rows, *, all_target_ids) -> region_rows
    build_run_context_partition(state, *, target_id, target_name, all_target_ids,
                                domain, grid_deg, gazes_deg) -> (arrays, region_rows, edge_rows, diag)

It also has one private helper, `_insert_after(mapping, anchor, key, value)`. This is a
small copy of the Core-12 helper in `candidate_policy`, so `run_context` does not import
`candidate_policy`. It raises `ValueError` if `key` is already present and `KeyError` if
`anchor` is missing.

**`annotate_reconstruction_status`** is **non-mutating**. It returns a new list of new row
dicts, in the same order and with the same value objects. For every row with
`kind == "OTHER_SURFACE"` and a non-`None` `instance_id`, it inserts
`reconstruction_status` **immediately after `surface_source`**, its accepted Core-12
position. The value reproduces the accepted rule exactly:

    "mapped_now"     if row["mapped_cells"]                       (the accepted `mapped_n`)
    "targeted_later" elif int(row["instance_id"]) in all_target_ids
    "never_targeted" otherwise

Other rows receive no field. An `OTHER_SURFACE` row without `surface_source`, or one already
carrying `reconstruction_status`, fails loudly.

**`build_run_context_partition`** has the historical Core-12 signature. It calls
`fov3d.epistemic.partition.build_epistemic_partition(...)` without `all_target_ids`, then
annotates the rows. `arrays`, `edge_rows` and `diag` are returned unchanged, as the same
objects. There is no candidate interpretation here.

Dependencies: `typing.Any`, `numpy` (annotations) and `fov3d.epistemic.partition`. There
is no dependency on `candidate_policy`, `benchmark`, evaluators, dense truth, stereo or
rendering.

## Candidate-policy composition

In `fov3d/experiments/classroom_partition/candidate_policy.py`, `build_candidate_partition`
keeps its historical Core-12 signature, **including `all_target_ids`**. It composes:

    intrinsic partition → run-context annotation → candidate annotation

That is, it calls `run_context.build_run_context_partition(...)` instead of the intrinsic
builder, then `annotate_candidate_partition(...)`. The change is exactly one import (the
intrinsic builder replaced by `build_run_context_partition`), one called name, and the
docstrings. `CANDIDATE_KINDS`, `_insert_after` and `annotate_candidate_partition` are
unchanged. The historical output stays exactly the accepted Core-12 output.

## Historical pipeline and compatibility

`benchmark.py`, `prefix_benchmark.py`, `integration.py` and `challenge_suite.py` already
call `build_candidate_partition`, and are **not modified**. This is expected; a mechanical
import change is made only if measurement proves one necessary.

`benchmark.build_epistemic_partition` remains the alias of `build_candidate_partition`, and
`benchmark.CANDIDATE_KINDS` the policy constant. The unmodified historical tools and
checkers keep seeing the accepted candidate view.

**Phase 8b.**
- Its base partition still receives `reconstruction_status`, through
  `build_candidate_partition` → `build_run_context_partition`.
- `refine_integrated_partition`/`_component_rows` still propagate `surface_source`,
  `reconstruction_status`, `mapped_cells`, `incidental_cells` and the other copied fields.
- `candidate_raw`, `eligible_candidate`, `MIN_ELIGIBLE_CELLS` and the UNKNOWN shell logic
  are not altered.

Measured before this contract: `fov3d/experiments/classroom_partition/incidental.py` (Phase
5) has its own, separate `reconstruction_status(instance_id, graph, all_target_ids)`
helper. This is the **Phase-5 duplication**, explicitly deferred. It is not modified, and
it is excluded from the no-duplicate check, which verifies instead that it is unchanged
from Core 12.

## Central Core-13 invariant

The reference is accepted Core 12 at `872ac45405c796a0e8b0cd4455bd17c12c7542db`. Its
`partition.py` and `candidate_policy.py` are executed from `git show` as isolated
reference modules, with the reference policy bound to the reference partition. For every
valid input state, let:
- `OLD_INTRINSIC` = Core-12 `fov3d.epistemic.partition.build_epistemic_partition(...)`;
- `NEW_INTRINSIC` = Core-13 `build_epistemic_partition(...)`, without `all_target_ids`;
- `RECONTEXTUALIZED` = `annotate_reconstruction_status(NEW_INTRINSIC.rows, all_target_ids=...)`;
- `OLD_HISTORICAL` = Core-12 `candidate_policy.build_candidate_partition(...)`;
- `NEW_HISTORICAL` = Core-13 `candidate_policy.build_candidate_partition(...)`.

Then:
1. the `NEW_INTRINSIC` arrays equal the `OLD_INTRINSIC` arrays exactly;
2. the `NEW_INTRINSIC` edges equal the `OLD_INTRINSIC` edges exactly;
3. the `NEW_INTRINSIC` diag equals the `OLD_INTRINSIC` diag exactly;
4. the `NEW_INTRINSIC` rows equal the `OLD_INTRINSIC` rows with **only**
   `"reconstruction_status"` removed, preserving row count and order, the remaining key
   order, values and types;
5. the `RECONTEXTUALIZED` rows equal the `OLD_INTRINSIC` rows, type-, value- and
   key-order-strictly;
6. `NEW_HISTORICAL == OLD_HISTORICAL`, type-, value- and key-order-strictly.

## Exclusions

Core 13 does not touch:
- `surface_source`, `mapped_cells` and `incidental_cells`;
- `min_distance_to_historical_gaze_deg` and `gazes_deg`;
- the candidate semantics (`CANDIDATE_KINDS` and the annotation);
- Phase-8b candidate refinement;
- the Phase-5 `incidental.reconstruction_status` helper;
- `fov3d/epistemic/__init__.py`;
- the historical producers, unless mechanically necessary;
- any historical checker or tool.

It introduces no general controller package, and there is no Core 14 in this run.

## Allowed changes

    fov3d/epistemic/partition.py                              (six lines removed; module docstring)
    fov3d/experiments/classroom_partition/run_context.py      (new)
    fov3d/experiments/classroom_partition/candidate_policy.py (one import, one called name, docstrings)
    tools/dev/check_conceptual_core13.py
    docs/migration-conceptual-core-13.md
    docs/migration-conceptual-core-13-report.md
    docs/conceptual-core-map.md   (after the implementation, checker and gates are complete)

## Checker supersession

The accepted `tools/dev/check_conceptual_core12.py` asserts the Core-12 structure:
- `all_target_ids` is in the intrinsic signature;
- `reconstruction_status` is produced by `epistemic.partition`;
- `candidate_policy` composes directly from the intrinsic builder, with a spy on its
  `build_epistemic_partition` binding.

Core 13 intentionally changes those facts. So:
- **A.** The Core-12 checker is **not modified**. It is verified at `872ac45` in a
  read-only detached reference worktree, where it must report
  `[conceptual-core12-check] SUMMARY checked=70 failed=0`.
- **B.** At the Core-13 head, Core-12 structural success is **not** a gate. Its measured
  outcome there is recorded for information.
- **C.** The Core-13 checker subsumes every still-valid Core-12 guarantee (helpers,
  fixtures, candidate rule, compatibility, Phase-8b independence, footprints) and tests the
  run-context separation.
- **D.** The Core-1 to Core-10 conceptual checkers stay current-head gates, unmodified.
- **E.** Partition-Graph checkers 1–8b stay current-head gates, **unmodified**.

This is architectural checker supersession, not regression.

## Core-13 checker

Add `tools/dev/check_conceptual_core13.py`. It is deterministic, inexpensive, host-side and
fail-capable. It prints `[conceptual-core13-check] SUMMARY checked=<N> failed=0`.

- **A. Intrinsic structure against Core 12.**
  - `REGION_KIND` and `REGION_KIND_BY_CODE` are unchanged, and the six helpers are
    source- and AST-identical;
  - the signature equals Core 12 minus **only** `all_target_ids`;
  - the builder source and AST equal Core 12 minus exactly the parameter and the
    `reconstruction_status` assignment;
  - no `all_target_ids` anywhere in the module;
  - no operational `reconstruction_status` or status string (docstrings aside);
  - the `surface_source`, `mapped_n` and `incidental_n` statements are source- and
    AST-identical;
  - exactly the Core-12 names, in order;
  - identical imports, with no experiment, `run_context` or `candidate_policy` import;
  - equivalent global bindings.
- **B. Intrinsic projection equivalence.** Over deterministic fixtures,
  `NEW_INTRINSIC == project(OLD_INTRINSIC)`. The comparison covers:
  - arrays, dtype, shape, edges and diag exactly;
  - rows (order, key order after projection, values, types).

  The fixtures witness all kinds; mapped, incidental and mapped-and-incidental surfaces;
  all three statuses; 4/8 connectivity; the target-free and no-gaze cases; distances; the
  gaze descriptor; interfaces; adjacency; and the malformed shape. The helper and fixture
  known answers are subsumed from Core 12.
- **C. `surface_source` stays intrinsic.** The `mapped`, `incidental` and
  `mapped_and_incidental` values are produced by the intrinsic builder, with hand-derived
  values and counts. Non-`OTHER_SURFACE` rows have neither field.
- **D. The reconstruction-status annotation:**
  - the exact rule on synthetic rows (mapped/targeted/never, including mapped with an id
    outside the schedule);
  - only `OTHER_SURFACE` rows with an instance id receive it;
  - exact Python `str` values;
  - no input mutation, and new dicts;
  - order, and every other field the same object;
  - placement immediately after `surface_source`;
  - the guards (a missing anchor or double annotation fails).
- **E. Recontextualization identity.** Per fixture, `annotate(NEW_INTRINSIC) == OLD_INTRINSIC`
  rows, and `build_run_context_partition == OLD_INTRINSIC`. `arrays`, `edges` and `diag` are
  passed through as the same objects.
- **F. Candidate composition.**
  - per fixture, `NEW_HISTORICAL == OLD_HISTORICAL`;
  - spies show one intrinsic build, one status annotation, one run-context wrapper call and
    one candidate annotation per `build_candidate_partition` call;
  - `CANDIDATE_KINDS` is unchanged;
  - `candidate_policy` equals Core 12 apart from the declared import and call name.
- **G. Historical compatibility.**
  - `benchmark.build_epistemic_partition` gives the accepted historical view, and
    `benchmark.CANDIDATE_KINDS` is the policy constant;
  - the four producer modules are byte-identical to Core 12, wired through
    `build_candidate_partition` (1/1/2/1 sites);
  - no producer calls the intrinsic builder or the run-context wrapper directly;
  - `reconstruction_status` status strings appear, among production modules, only in
    `run_context` and the unchanged Phase-5 `incidental.py`.
- **H. Phase-8b propagation.**
  - the base historical rows carry `reconstruction_status`;
  - `refine_integrated_partition` on the Core-13 view equals that on the Core-12 view, and
    refined `OTHER_SURFACE` rows carry their origin's status;
  - `candidate_raw`/`eligible_candidate` have known answers and are independent of the
    policy and run context (live control);
  - `_component_rows` and `refine_integrated_partition` are unchanged from Core 12.
- **I. Package footprints (fresh processes).**
  - a bare `fov3d.epistemic` stays lightweight;
  - `fov3d.epistemic.partition` loads no experiment, `run_context` or `candidate_policy`;
  - `run_context` loads the intrinsic partition but no `candidate_policy`, benchmark,
    evaluator, stereo or renderer module;
  - `candidate_policy` loads `run_context` and the intrinsic partition but no benchmark,
    evaluator, stereo or renderer module;
  - the exact module lists, the static import sets, and no cycle.
- **J. Seeded random differential in the checker.** Hundreds of states, varying raster
  size, target support, owner/nearest identities, ambiguity, depth/seen masks, target ids,
  `all_target_ids` membership, domain, `grid_deg` and gaze histories. It checks invariants
  4–6 (and 1–3), with all three statuses occurring repeatedly, and includes non-equivalent
  controls.

  A larger out-of-checker differential (thousands of states, with mutant controls) is
  recorded in the report.

## Mutation classes

The **final** checker is mutation-tested before it is committed. It must catch:
1. **Future-context leakage:**
   - `all_target_ids` still in the intrinsic signature;
   - the intrinsic builder reading `all_target_ids`;
   - the intrinsic builder still emitting `reconstruction_status`;
   - the intrinsic module importing `run_context` or an experiment module.
2. **Context rule:**
   - the `mapped_now` condition inverted, or based on `surface_source`;
   - `targeted_later` and `never_targeted` swapped;
   - the membership test inverted;
   - the instance-id conversion changed;
   - the annotation applied to all kinds, or omitted for `OTHER_SURFACE`;
   - a wrong string spelling or type.
3. **Reconstitution:**
   - the wrong key position;
   - a row dropped, or rows reordered;
   - another field changed, or `surface_source` changed;
   - arrays copied or their dtype changed;
   - edges or diag changed;
   - in-place mutation.
4. **Intrinsic regression:** precedence, connectivity, surface identity, mapped/incidental
   counts, `surface_source`, centroid, distance, gaze descriptor, adjacency/interfaces,
   region ordering.
5. **Wiring:**
   - `candidate_policy` bypassing `run_context`, or calling the pure builder and losing
     the status;
   - `run_context` importing `candidate_policy`;
   - `benchmark` bypassing `candidate_policy`;
   - a producer bypassing the candidate view;
   - a duplicate status implementation.
6. **Phase 8b:**
   - the `reconstruction_status` propagation removed;
   - `candidate_raw` coupled to the run-context logic;
   - `eligible_candidate` changed.

Genuinely equivalent mutants are recorded separately. The checker is never weakened for
the score.

## Worktree guard

All measured work runs in the dedicated `migration/conceptual-core-13` worktree. Before and
after every measurement, the branch, the expected HEAD and a clean tracked tree are
required. The shared checkout is not used.

## Execution gates

**Gate A (under the guard):**
- compile the changed Python;
- run the Core-13 checker and the Core-10 to Core-1 conceptual checkers (unmodified);
- verify the accepted Core-12 checker at `872ac45` in a read-only detached reference
  worktree (70/70);
- run the Partition-Graph checkers 1–8b (**unmodified**) and the facade check;
- run `scripts/verify_baseline.sh` (31/31),
  `scripts/compare_golden.sh previews/partition-graph-2-source-full` (`MISMATCHES 0`) and
  `git diff --check`;
- run the fresh package footprints.

**Import/dependency audit.** Measure all Partition-Graph producer/evaluator entry points in
fresh processes for `fov3d.epistemic.partition`, `run_context`, `candidate_policy` and
`benchmark`. The expected result is Phases 6–8b; this is **measured**. Earlier phases run
only if reached.

**Replays.** Every reached producer and evaluator is replayed with the exact accepted Core-12
commands and scopes, each to a fresh `previews/conceptual-core-13-*` directory:

| gate | command (after `.venv/bin/python`) | accepted reference | scope / exclusions |
|---|---|---|---|
| Phase-6 proposer | `tools/partition_graph6_propose.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/partition-graph-5-full <fresh>` | `partition-graph-6-proposals` | 102 |
| Phase-6 evaluator | `tools/partition_graph6_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-6-proposals <fresh>` | `partition-graph-6-evaluation` | 3; 28 + 28 |
| Phase-7 proposer | `tools/partition_graph7_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-6-proposals <fresh>` | `partition-graph-7-proposals` | 835 |
| Phase-7 evaluator | `tools/partition_graph7_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-7-proposals previews/partition-graph-6-evaluation <fresh>` | `partition-graph-7-evaluation` | 107; 107 + 107 |
| Phase-8 proposer | `tools/partition_graph8_integrate.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-7-proposals <fresh>` | `partition-graph-8-proposals` | 468 |
| Phase-8 evaluator | `tools/partition_graph8_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8-proposals previews/partition-graph-7-evaluation <fresh>` | `partition-graph-8-evaluation` | 107; 107 + 107 |
| Phase-8b proposer | `tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals <fresh>` | `partition-graph-8b-proposals` | 503 |
| Phase-8b evaluator | `tools/partition_graph8b_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8b-proposals previews/partition-graph-8-evaluation <fresh>` | `partition-graph-8b-evaluation` | 3; 8 + 8 |

The target is all 8 byte-identical, with exact COMPLETE lines. The Phase-8 proposer (about
11 min; 662 s in Core 12) is required by this contract and runs **once**.

**Instrumentation.** Per producer, one-to-one counts of:
- intrinsic builds;
- reconstruction-status annotations;
- run-context wrapper calls;
- candidate annotations;
- candidate wrapper calls (by binding);
- the `benchmark` alias;
- the `mapped_now`/`targeted_later`/`never_targeted` counts.

The Phase-8 proposer's **required replay is itself instrumented**. The other phases run the
plain established commands, plus cheap instrumented runs into scratch space. The expected
counts, from the Core-12 measurements, are Phase-6 25, Phase-7 208, Phase-8 208 and
Phase-8b 125, with evaluators 0. These are expectations, and they are measured.

Cost classes:
- the checker and Gate A are interactive;
- the replays and the out-of-checker differential are batch;
- the Phase-8 proposer is one required ~11-minute run.

## Byte-comparison discipline and accepted-tree integrity

- Use fresh output directories, and treat accepted trees as read-only.
- Compare file sets in both directions, with the established exclusions only and no fresh
  file beneath an excluded path.
- Byte-compare every in-scope pair.
- Record `LC_ALL=C` scope manifests and the exact COMPLETE lines.
- Take full per-file sha256 manifests of the 13 accepted reference trees before the first
  replay and after the last replay and instrumentation. They must be unchanged.

## Acceptance

Core 13 passes only if all of the following hold:
- the intrinsic `build_epistemic_partition` no longer accepts `all_target_ids`;
- the intrinsic rows no longer contain `reconstruction_status`, and the intrinsic output
  equals accepted Core 12 minus **only** `reconstruction_status`;
- `surface_source` stays intrinsic and unchanged;
- `run_context` reconstitutes the accepted Core-12 intrinsic rows exactly;
- `candidate_policy` reconstitutes the accepted Core-12 historical output exactly;
- no experiment or run-context dependency enters `epistemic.partition`;
- historical compatibility is intact;
- Phase-8b propagation is exact;
- the Core-13 checker is fail-capable, and the random differential is clean;
- the Core-1 to Core-10 checkers pass at the current head;
- the accepted Core-12 checker passes at `872ac45`;
- all Partition-Graph checkers pass unmodified;
- the baseline is 31/31 and golden reports `MISMATCHES 0`;
- every reached Phase-6/7/8/8b product is byte-identical;
- the 13 accepted reference trees are unchanged;
- every changed production path is covered by executed gates.

## Permitted repairs

Only minimal mechanical import, wiring or checker defects inside the declared Core-13
scope may be repaired. If preservation would require changing intrinsic semantics,
`surface_source`, the historical status rule, candidate semantics, Phase-8b refinement,
accepted outputs or this contract, **stop and report**.

## Deferred (explicitly not part of Core 13)

1. `min_distance_to_historical_gaze_deg`, the Core-14 question.
2. The `gazes_deg` input to the intrinsic partition.
3. Broader observer/attention-history representation.
4. The placement of the target-relative `HeadEvidence` fields.
5. The Phase-5 `reconstruction_status` duplication (`incidental.reconstruction_status`).
6. `_own_labels` versus `own_support_labels`.
7. `component_lineage` versus `scene.lineage._lineage`.
8. The `attach_state_region_codes` rename.
9. The consumerless compatibility aliases.
10. The historical Phase-2/Phase-3 boundary lineage cleanup.

Commit and push the completed branch, then stop for review by Luiz and Chat. Core 13 is not
merged without Luiz's explicit acceptance.

Success marker:

    CONCEPTUAL_CORE13_RECONSTRUCTION_STATUS_SEPARATION_PRESERVES_BEHAVIOR
