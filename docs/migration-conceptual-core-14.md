# Migration Conceptual Core 14 — historical gaze context separated from the epistemic partition

## Status

This is the **third intentional redesign Core**, after Core 12 (candidate interpretation)
and Core 13 (run context). It completes the present representation archaeology far enough
to prepare the design of the integrated foveal controller. **It does not implement that
controller.**

Accepted scientific milestone (parent):

    Conceptual Core 13 @ 3b7091ed7a8f58cfc84c552431bfe60dc694aad3
    CONCEPTUAL_CORE13_RECONSTRUCTION_STATUS_SEPARATION_PRESERVES_BEHAVIOR

Administrative provenance:
- The remote state was verified before acceptance: `origin/main = 8279cb2`,
  `origin/migration/conceptual-core-13 = 3b7091e`. `3b7091e` descends from `8279cb2`, being
  5 ahead and 0 behind; `CLAUDE.md` was unchanged and the shared checkout untouched.
- `origin/main` was fast-forwarded `8279cb2 → 3b7091e` (Core 13 accepted by Luiz) with a
  plain, non-forced push.
- The Chat Handoff was updated on main as `fe187679935466674c8ea4ce016554557b94114a`
  (parent `3b7091e`), from a detached administrative worktree that was removed afterwards.
- `migration/conceptual-core-14` was created from the new `origin/main` (`fe18767`),
  untracked, and pushed with its own remote branch as upstream.

Design provenance: Luiz and Chat. Claude Code committed this contract in the dedicated
isolated Core-14 worktree **before** any production change.

    simplest falsifiable redesign  +  preserve all accepted historical observables

## Causal question

Can action-history-derived gaze context (`gazes_deg` and
`min_distance_to_historical_gaze_deg`) be removed from the intrinsic epistemic partition and
reconstructed as a separate historical gaze-context annotation, while reproducing every
accepted Core-13 historical product exactly?

    accepted Core-13 intrinsic partition  =  Core-14 intrinsic partition
                                          +  historical gaze-context annotation

This is the only causal question in Core 14.

## Evidence history versus action history

| quantity | derived from | kind of history | Core 14 |
|---|---|---|---|
| `seen_any_fraction`, `head_depth_fraction` | the accumulated state masks `seen_any`, `depth_seen` | **evidence** accumulated in the state | **intrinsic**, unchanged |
| `mapped_cells`, `incidental_cells`, `surface_source` | mapped/incidental identity evidence in the state | **evidence** | **intrinsic**, unchanged |
| `min_distance_to_historical_gaze_deg` | the region centroid **and the previous fixation directions** | **action** history of the observer | **moved** to `gaze_context` |

    evidence history                     action history
    seen_any, depth_seen,                gaze directions
    identity evidence                         |
          |                                   v
          v                              gaze context
    epistemic state

## Accepted target-local gaze semantics (preserved exactly)

The historical pipeline does **not** pass every gaze the observer ever made. It passes the
**current target's** historical gaze sequence or prefix. This was measured in the live code
before this contract:

| phase | producer | list passed as `gazes_deg` |
|---|---|---|
| 6 | `benchmark.propose_phase6` | `gazes`: every `gaze_deg` of the target's trajectory (target-final state) |
| 7 | `prefix_benchmark.propose_phase7` | `current_target_gazes`: the target trajectory through the current local step, `trajectory[: local_step + 1]`, passed to **both** the local and global arms. `global_gazes` is kept separately for reporting only |
| 8 | `integration.propose_phase8` | `current_gazes`: `trajectory[: local_step + 1]`, passed to both partition call sites |
| 8b | `challenge_suite.propose_phase8b` | `current_gazes`: the retained prefix under the scenario budget, `trajectory[:keep]` |

Core 14 moves the ownership of the **derived metric**, not the source or provenance of the
gaze list. It does not substitute global gaze history, other targets' gazes, recency
weighting, inhibition of return, fixation density, scoring or ranking.

## Exact intrinsic change

In `fov3d/epistemic/partition.py`, the signature becomes the accepted Core-13 signature
minus exactly `gazes_deg`:

    build_epistemic_partition(state, *, target_id, target_name, domain, grid_deg)

Exactly six lines of the accepted Core-13 source are removed:

```text
-    gazes_deg: list[tuple[float, float]],
-            gaze_dist = [
-                _angular_distance_deg((cyaw, cpitch), (float(y), float(p)))
-                for y, p in gazes_deg
-            ] if gazes_deg and np.isfinite(cyaw) and np.isfinite(cpitch) else []
-                "min_distance_to_historical_gaze_deg": None if not gaze_dist else float(min(gaze_dist)),
```

The module docstring is updated only as needed. **Everything else is unchanged**:
- `REGION_KIND`, `REGION_KIND_BY_CODE`, and all six helpers, **including
  `_angular_distance_deg`**;
- precedence, `class_code` and `surface_instance`;
- connectivity, region order and codes;
- `cell_count`, the edge flag and the centroid;
- the min/median target distances;
- `seen_any_fraction` and `head_depth_fraction`;
- `mapped_cells`, `incidental_cells` and `surface_source`;
- interfaces, adjacency, `arrays`, diagnostics, exceptions and imports.

**`_angular_distance_deg` is deliberately retained** in `epistemic.partition`. It is a
generic geometric helper, and moving or renaming it would open an unrelated ownership
question. After Core 14 the intrinsic builder no longer calls it, and the gaze-context layer
imports it. No helper cleanup is done here. `fov3d/epistemic/__init__.py` is **not**
modified.

## New historical gaze-context layer

New experiment-side module: `fov3d/experiments/classroom_partition/gaze_context.py`. The
metric may later inspire a reusable observer-history mechanism, but the accepted semantics
are target-local and are not promoted to a controller abstraction here. Final names are as
proposed:

    annotate_gaze_context(region_rows, *, gazes_deg) -> region_rows
    build_gaze_context_partition(state, *, target_id, target_name, domain, grid_deg,
                                 gazes_deg) -> (arrays, region_rows, edge_rows, diag)

It also has one private helper, `_insert_after`. This is a small copy of the Core-12/13
helper, so the layer depends only on `epistemic.partition`. It raises `ValueError` for a
present key and `KeyError` for a missing anchor.

**`annotate_gaze_context`** is **non-mutating**. It returns a new list of new row dicts, in
order, with the same value objects. For **every** row it reproduces the accepted rule from
the row's centroid, using the retained `_angular_distance_deg`:

    gaze_dist = [_angular_distance_deg((centroid_yaw_deg, centroid_pitch_deg), (float(y), float(p)))
                 for y, p in gazes_deg] if gazes_deg and np.isfinite(centroid_yaw_deg)
                                           and np.isfinite(centroid_pitch_deg) else []
    min_distance_to_historical_gaze_deg = None if not gaze_dist else float(min(gaze_dist))

The field is inserted **immediately after `median_distance_to_target_deg`**, its accepted
Core-13 position, before `seen_any_fraction`. An empty gaze list gives `None` for every
region, exactly as before.

**`build_gaze_context_partition`** has the historical Core-13 intrinsic signature. It calls
`fov3d.epistemic.partition.build_epistemic_partition(...)` without `gazes_deg`, then
annotates the rows. `arrays`, `edge_rows` and `diag` are passed through unchanged, as the
same objects.

Dependencies: `typing.Any`, `numpy`, and `fov3d.epistemic.partition`
(`build_epistemic_partition`, `_angular_distance_deg`). There is no dependency on
`run_context`, `candidate_policy`, `benchmark`, evaluators, stereo or rendering.

## Composition

**`run_context.py`.** `build_run_context_partition` keeps its historical Core-13 signature,
**including `all_target_ids` and `gazes_deg`**. It now composes:

    intrinsic → gaze context → reconstruction-status annotation

It calls `gaze_context.build_gaze_context_partition(...)`, with the same arguments, instead
of the intrinsic builder. The change is one import, one called name and the docstrings.
`_insert_after`, `annotate_reconstruction_status` and the status rule are unchanged.

**`candidate_policy.py`.** It is **not modified** (byte-identical to Core 13) and still
composes on `build_run_context_partition`. The complete historical stack is:

    intrinsic → gaze_context → run_context → candidate annotation

**Historical producers.** `benchmark.py`, `prefix_benchmark.py`, `integration.py` and
`challenge_suite.py` are **not modified**. They keep selecting the accepted target-local
gaze lists and passing them to `build_candidate_partition`. `benchmark`'s compatibility API
is unchanged.

**Phase 8b.**
- Its base partition still receives `min_distance_to_historical_gaze_deg` through the
  historical candidate view.
- Its refinement (`_component_rows`) does **not** copy that field into refined rows. This
  non-propagation is accepted behavior and is preserved.
- The `reconstruction_status`/`surface_source` propagation, `candidate_raw`,
  `eligible_candidate`, `MIN_ELIGIBLE_CELLS` and the UNKNOWN shells are unchanged.

## Central Core-14 invariant

The reference is accepted Core 13 at `3b7091ed7a8f58cfc84c552431bfe60dc694aad3`. The
Core-13 `partition.py`, `run_context.py` and `candidate_policy.py` are executed from
`git show` as isolated reference modules, bound to one another exactly as in Core 13. For
every valid input, let:
- `OLD_INTRINSIC` = Core-13 `build_epistemic_partition(..., gazes_deg)`;
- `NEW_INTRINSIC` = the Core-14 intrinsic builder, without `gazes_deg`;
- `REGAZED` = `annotate_gaze_context(NEW_INTRINSIC.rows, gazes_deg=...)`;
- `OLD_RUN_CONTEXT` and `NEW_RUN_CONTEXT` = the Core-13 and Core-14
  `build_run_context_partition(...)`;
- `OLD_HISTORICAL` and `NEW_HISTORICAL` = the Core-13 and Core-14
  `build_candidate_partition(...)`.

Then:
1. the `NEW_INTRINSIC` arrays equal the `OLD_INTRINSIC` arrays exactly;
2. the `NEW_INTRINSIC` edges equal the `OLD_INTRINSIC` edges exactly;
3. the `NEW_INTRINSIC` diag equals the `OLD_INTRINSIC` diag exactly;
4. the `NEW_INTRINSIC` rows equal the `OLD_INTRINSIC` rows with **only**
   `"min_distance_to_historical_gaze_deg"` removed (row count and order, the remaining key
   order, values, types);
5. the `REGAZED` rows equal the `OLD_INTRINSIC` rows;
6. `build_gaze_context_partition(...) == OLD_INTRINSIC`;
7. `NEW_RUN_CONTEXT == OLD_RUN_CONTEXT`;
8. `NEW_HISTORICAL == OLD_HISTORICAL`.

All of these are type-, value- and key-order-strict.

## Checker supersession

The accepted `tools/dev/check_conceptual_core13.py` asserts the Core-13 structure:
`gazes_deg` in the intrinsic signature, `min_distance_to_historical_gaze_deg` as intrinsic,
and `run_context` building the intrinsic partition directly. Core 14 intentionally changes
those facts.
- **A.** The Core-13 checker is **not modified**. It is verified at `3b7091e` in a
  read-only detached reference worktree, where it must report
  `[conceptual-core13-check] SUMMARY checked=65 failed=0`.
- **B.** At the Core-14 head it is **not** a gate. Its measured outcome there is recorded
  for information.
- **C.** The Core-14 checker subsumes every still-valid Core-13 guarantee and tests the
  gaze-context boundary.
- **D.** The Core-1 to Core-10 conceptual checkers stay current-head gates, unmodified.
- **E.** The Partition-Graph checkers 1–8b stay current-head gates, **unmodified**.

This is explicit architectural-checker supersession, not regression.

## Core-14 checker

Add `tools/dev/check_conceptual_core14.py`. It is deterministic, inexpensive and
fail-capable, and prints `[conceptual-core14-check] SUMMARY checked=<N> failed=0`. Source
identities compare whole line ranges.
- **A. Intrinsic structure against Core 13.**
  - the constants and all helpers unchanged, including `_angular_distance_deg`;
  - the signature minus **only** `gazes_deg`;
  - the builder source and AST minus exactly the six lines (the parameter, the `gaze_dist`
    assignment, the row entry);
  - no `gazes_deg`/`gaze_dist` and no gaze-distance field anywhere (docstrings aside);
  - every other row field source-identical;
  - identical imports, with no `gaze_context`, `run_context`, `candidate_policy` or
    experiment import;
  - equivalent bindings.
- **B. Intrinsic projection equivalence.** Over deterministic fixtures,
  `NEW_INTRINSIC == project(OLD_INTRINSIC)` exactly (arrays, dtype, shape, edges, diag,
  rows). The fixtures witness:
  - all kinds, the three sources and surface identity;
  - 4/8 connectivity;
  - the target-free case;
  - no-gaze, one-gaze and multi-gaze histories, with nontrivial great-circle distances;
  - target distances, seen/depth fractions, interfaces, adjacency and edge flags;
  - the malformed shape.

  The helper and fixture known answers are subsumed from Core 13.
- **C. Action-history independence.** For the same state, the intrinsic output built
  without a gaze argument (arrays, rows, edges, diag) is identical whatever gaze history is
  later applied (`[]`, one gaze, several gazes), while the annotations do change: a live
  control.
- **D. The gaze-context rule:**
  - the centroid fields and `_angular_distance_deg` are used;
  - `float` conversion of the gaze components, and the minimum (not the max, mean or
    median);
  - no gazes gives `None`, and finite centroids with gazes give a Python `float`;
  - a non-finite centroid gives `None`;
  - every region receives the field, right after `median_distance_to_target_deg`;
  - order, other fields as the same objects, no input mutation, and new dicts;
  - the guards.
- **E. Regazing identity.** Per fixture and gaze history,
  `annotate_gaze_context(NEW_INTRINSIC) == OLD_INTRINSIC` and
  `build_gaze_context_partition == OLD_INTRINSIC`. `arrays`, `edges` and `diag` are passed
  through as the same objects.
- **F. Run-context composition.**
  - `NEW_RUN_CONTEXT == OLD_RUN_CONTEXT`;
  - spies show one intrinsic build, one gaze annotation, one gaze-context wrapper call and
    one status annotation;
  - `run_context` imports `gaze_context`, not the intrinsic builder;
  - the status rule is Core-13-identical, and the signature is unchanged.
- **G. Candidate composition.**
  - `candidate_policy.py` is byte-identical to Core 13;
  - `NEW_HISTORICAL == OLD_HISTORICAL`;
  - one full call path gives one intrinsic build, one gaze annotation, one gaze-context
    wrapper call, one status annotation, one run-context call and one candidate
    annotation.
- **H. Historical gaze provenance.**
  - the four producers are byte-identical to Core 13;
  - the target-local selections are structurally present: Phase 6 the trajectory gazes,
    Phase 7 `current_target_gazes` for both arms with `global_gazes` reporting-only, Phase 8
    the prefix at both sites, Phase 8b the retained prefix;
  - no producer passes `global_gazes`.
- **I. Phase 8b.**
  - the base partition carries the gaze field;
  - refinement on the Core-14 view equals that on the Core-13 view;
  - refined rows do **not** carry the gaze field, while `reconstruction_status` and
    `surface_source` still propagate;
  - the `candidate_raw`/`eligible_candidate` known answers, and independence from the
    gaze context (live control).
- **J. Package footprints (fresh processes).**
  - a bare `fov3d.epistemic` stays lightweight;
  - `epistemic.partition` loads no experiment, `gaze_context`, `run_context` or
    `candidate_policy`;
  - `gaze_context` loads the intrinsic partition but no `run_context`, `candidate_policy`,
    benchmark, evaluator, stereo or renderer module;
  - `run_context` adds `gaze_context`, with no `candidate_policy` or benchmark;
  - `candidate_policy` adds `run_context`, with no benchmark, evaluator, stereo or
    renderer module;
  - exact module lists, static imports, and no cycle.
- **K. Seeded random differential in the checker.** Hundreds of states, varying dimensions,
  support, owner/nearest identities, ambiguity, depth/seen masks, target ids, domain,
  `grid_deg`, gaze-list length and directions (including empty histories) and
  `all_target_ids`. It checks all eight invariants. Empty, one-gaze and multi-gaze histories
  and non-`None` distances occur repeatedly. It includes non-equivalent controls.

  A larger out-of-checker differential (thousands of states, with mutant controls) is
  recorded in the report.

## Mutation classes

The **final** checker is mutation-tested before it is committed. It must catch:
1. **Action-history leakage:**
   - `gazes_deg` retained in the intrinsic signature;
   - the intrinsic builder reading the gaze history, or emitting the gaze-distance field;
   - the intrinsic module importing `gaze_context` or an experiment module.
2. **Gaze annotation:**
   - min → max or mean; first gaze only; last gaze only;
   - yaw/pitch swapped; the centroid fields swapped;
   - `float` conversion removed or changed (where non-equivalent);
   - no gazes giving 0 instead of `None`;
   - the field only on candidates, or omitted for one kind;
   - a wrong key spelling or type.
3. **Reconstitution:**
   - the field at the end, or before the median target distance;
   - a row dropped, or rows reordered;
   - another field changed;
   - in-place mutation;
   - arrays copied or their dtype changed;
   - edges or diag changed;
   - the annotation skipped.
4. **Intrinsic regression:** precedence, connectivity, surface identity, target distance,
   centroid, mapped/incidental counts, `surface_source`, `seen_any_fraction`,
   `head_depth_fraction`, adjacency/interfaces, region ordering.
5. **Wiring:**
   - `run_context` importing the intrinsic builder directly, skipping the gaze context, or
     duplicating the gaze computation;
   - `candidate_policy` bypassing `run_context`;
   - a producer changing its target-local selection or using `global_gazes`;
   - a duplicate gaze-metric implementation elsewhere.
6. **Phase 8b:**
   - the gaze field propagated to refined rows, or lost from the base rows;
   - `candidate_raw` coupled to the gaze distance;
   - `eligible_candidate` changed;
   - the status propagation changed.

Genuinely equivalent mutants are recorded separately. The checker is never weakened.

## Execution gates

**Gate A (under the guard):**
- compile the changed Python;
- run the Core-14 checker and the Core-10 to Core-1 conceptual checkers (unmodified);
- verify the accepted Core-13 checker at `3b7091e` in a read-only detached reference
  worktree (65/65);
- run the Partition-Graph checkers 1–8b (**unmodified**) and the facade check;
- run `scripts/verify_baseline.sh` (31/31),
  `scripts/compare_golden.sh previews/partition-graph-2-source-full` (`MISMATCHES 0`) and
  `git diff --check`;
- run the fresh package footprints.

**Import/dependency audit.** Measure, in fresh processes, every Partition-Graph
proposer/evaluator entry point for `fov3d.epistemic.partition`, `gaze_context`,
`run_context`, `candidate_policy` and `benchmark`. Replay every reached phase; Phases 2–5
run only if reached.

**Replays.** The exact accepted Core-13 commands, inputs and scopes are used, each to a fresh
`previews/conceptual-core-14-*` directory:
- the Phase-6 proposer and evaluator, `partition_graph6_propose.py` and
  `partition_graph6_evaluate.py` (102; 3 with 28 + 28 excluded);
- the Phase-7 proposer and evaluator (835; 107 with 107 + 107 excluded);
- the Phase-8 proposer (`partition_graph8_integrate.py`, 468) and evaluator (107 with
  107 + 107 excluded);
- the Phase-8b proposer (503) and evaluator (3 with 8 + 8 excluded).

The inputs are those recorded in the Core-12/13 reports. The target is all 8
byte-identical, with exact COMPLETE lines, two-sided set equality, the established
exclusions only, byte comparison, and `LC_ALL=C` manifests. The Phase-8 proposer (about
11 min) runs **once**.

**Instrumentation.** Per producer, one-to-one counts of:
- intrinsic builds;
- gaze annotations;
- gaze-context wrapper calls;
- status annotations;
- run-context calls;
- candidate annotations;
- candidate wrapper calls.

Descriptively, it also records:
- the gaze entries supplied;
- the partitions with an empty, a single or several gazes;
- the rows with a `None` or a finite gaze distance.

The Phase-8 proposer's **required replay is itself instrumented**. The other phases use the
plain established commands, plus cheap instrumented scratch runs. The expected counts, from
Core 13, are Phase-6 25, Phase-7 208, Phase-8 208 and Phase-8b 125, with evaluators 0;
these are measured.

**Accepted-tree integrity.** Full per-file sha256 manifests of the 13 accepted trees are
taken before the first replay and after the last replay and instrumentation, and must be
unchanged. Outputs go to fresh or scratch destinations only.

Cost classes: the checker and Gate A are interactive; the replays and the out-of-checker
differential are batch; the Phase-8 proposer is one required ~11-minute run.

## Controller-readiness boundary

The report includes a **read-only** architectural section, "Controller-readiness boundary".
It summarizes, from the live code after Core 14:
- the intrinsic information available to a future controller;
- the separated historical and contextual layers;
- what is explicitly **not** implemented.

After Core 14 the intrinsic partition is independent of the experiment's target schedule,
the candidate interpretation and the fixation history. That section changes no production
code. **No controller** (candidate eligibility, scoring/ranking, fixation choice, vergence,
inhibition of return, recency, continuation/stopping) is implemented in Core 14.

## Exclusions

Core 14 does not touch:
- the evidence-history fields and `_angular_distance_deg`;
- `candidate_policy.py`, the four historical producers, and the Phase-8b
  candidate/refinement semantics;
- `fov3d/epistemic/__init__.py`;
- the Phase-5 `incidental.py`;
- any historical tool or checker.

It introduces no controller logic, and there is no Core 15 in this run.

## Allowed changes

    fov3d/epistemic/partition.py                          (six lines removed; module docstring)
    fov3d/experiments/classroom_partition/gaze_context.py (new)
    fov3d/experiments/classroom_partition/run_context.py  (one import, one called name, docstrings)
    tools/dev/check_conceptual_core14.py
    docs/migration-conceptual-core-14.md
    docs/migration-conceptual-core-14-report.md
    docs/conceptual-core-map.md   (after the implementation, checker and gates are complete)

## Acceptance

Core 14 passes only if all of the following hold:
- the intrinsic builder no longer accepts `gazes_deg`, and its rows no longer contain
  `min_distance_to_historical_gaze_deg`;
- the intrinsic output equals accepted Core 13 minus **only** that field;
- every evidence-history field and `_angular_distance_deg` is unchanged;
- `gaze_context`, `run_context` and `candidate_policy` reconstruct the accepted Core-13
  intrinsic, run-context and historical outputs exactly;
- the target-local gaze provenance is unchanged, and the producers are unchanged;
- the Phase-8b base and refined behavior is exact;
- no experiment or action-history dependency enters `epistemic.partition`;
- the Core-14 checker is fail-capable, and the random differential is clean;
- the Core-1 to Core-10 checkers pass at the current head;
- the accepted Core-13 checker passes at `3b7091e`;
- all Partition-Graph checkers pass unmodified;
- the baseline is 31/31 and golden reports `MISMATCHES 0`;
- every reached Phase-6/7/8/8b product is byte-identical;
- the 13 accepted trees are unchanged;
- every changed production path maps to an executed gate.

## Permitted repairs

Only minimal mechanical import, wiring or checker defects inside the declared Core-14 scope
may be repaired. If preservation would require changing intrinsic or evidence semantics, the
target-local gaze selection, the gaze rule, the run-context or candidate semantics, Phase-8b
behavior, accepted outputs or this contract, **stop and report**.

## Deferred (explicitly not part of Core 14)

1. The design of global versus target-local observer gaze history.
2. Inhibition of return.
3. Gaze recency or decay.
4. Candidate eligibility for the real controller.
5. Candidate ranking or scoring.
6. Fixation selection.
7. Vergence/focus action.
8. Integrated continuation/stopping logic.
9. The placement of the target-relative `HeadEvidence` fields.
10. The Phase-5 `reconstruction_status` duplication.
11. `_own_labels` versus `own_support_labels`.
12. `component_lineage` versus `scene.lineage._lineage`.
13. The `attach_state_region_codes` rename.
14. The consumerless compatibility aliases.
15. The historical Phase-2/Phase-3 boundary lineage cleanup.

Commit and push the completed branch, then stop for review by Luiz and Chat. Core 14 is not
merged without Luiz's explicit acceptance. If it is accepted, the next activity is a fresh
architectural design of the integrated foveal controller over the clean representation
boundary, not an automatic Core-15 cleanup migration.

Success marker:

    CONCEPTUAL_CORE14_GAZE_CONTEXT_SEPARATION_PRESERVES_BEHAVIOR
