# Migration Conceptual Core 13 — report

**Result.**

    CONCEPTUAL_CORE13_RECONSTRUCTION_STATUS_SEPARATION_PRESERVES_BEHAVIOR

This result is MEASURED and awaits review by Luiz and Chat. Core 13 is **not** merged into
`main`.

**Causal question.** Can `reconstruction_status` and the dependency on `all_target_ids` be
removed from the intrinsic epistemic partition and expressed instead as an experiment-side
run-context annotation, while reproducing every accepted Core-12 historical product exactly?

**Answer (measured): yes.**

    accepted Core-12 intrinsic partition = Core-13 intrinsic partition
                                         + historical reconstruction-status annotation

The evidence:
- **The intrinsic partition.** `fov3d.epistemic.partition.build_epistemic_partition` no
  longer accepts `all_target_ids` or emits `reconstruction_status`. Its source is accepted
  Core 12 minus exactly six lines, the docstring aside.
- **The provenance field.** `surface_source` stays intrinsic and unchanged.
- **The run-context layer.** The new experiment-side
  `fov3d/experiments/classroom_partition/run_context.py` re-creates the accepted Core-12
  intrinsic rows exactly.
- **The composition.** `candidate_policy.build_candidate_partition` composes intrinsic → run
  context → candidate annotation, and re-creates the accepted Core-12 historical output
  exactly.
- **The central invariant against accepted Core 12 (`872ac45`)** holds on every fixture, on
  300 seeded states inside the checker, and on 10,000 random states outside it.
- **The checker.** The Core-13 checker passes 65/65. It caught all 50 non-equivalent dynamic
  mutants and all 20 static mutants.
- **Existing checkers.** The accepted Core-12 checker passes 70/70 at `872ac45`. The Core-1
  to Core-10 checkers and the Partition-Graph checkers 1–8b pass **unmodified** at the
  current head.
- **Replays.** All 8 reached Phase-6/7/8/8b products are **byte-identical**.
- **Instrumentation.** The redesigned stack is one-to-one in every producer.
- **Accepted trees, baseline and golden.** The 13 accepted trees are unchanged, the baseline
  is 31/31, and golden reports `MISMATCHES 0`.

## The semantic distinction

For `OTHER_SURFACE` regions, accepted Core 12 emitted two fields that look alike but mean
different things:

| field | values | determined by | meaning | Core 13 |
|---|---|---|---|---|
| `surface_source` | `mapped`, `incidental`, `mapped_and_incidental` | the current state only (`mapped_cells`, `incidental_cells`) | causal evidence provenance: how is this surface known? | **stays intrinsic, unchanged** |
| `reconstruction_status` | `mapped_now`, `targeted_later`, `never_targeted` | `mapped_cells` **and `all_target_ids`**, the prerecorded experiment's target schedule | historical run context | **moved** to `run_context` |

An autonomous epistemic representation cannot know which objects a prerecorded experiment
will target later. Core 13 separates only that knowledge, and keeps `surface_source`,
`mapped_cells` and `incidental_cells` intrinsic.

The checker includes a **live control**. Re-running the run-context partition of fixture H1
under two different schedules changes the statuses of the two unmapped surfaces
(`never_targeted` versus `targeted_later`), while `surface_source` stays identical and equal
to the intrinsic value.

## Provenance: Core-12 acceptance administration and branch

| step | result |
|---|---|
| pre-check (fetch) | `origin/main = 9eb9d9936cd2198fe63b7b9f076455f2114da70d` and `origin/migration/conceptual-core-12 = 872ac45405c796a0e8b0cd4455bd17c12c7542db`, both verified. `872ac45` descends from `9eb9d99`; Core 12 is 5 ahead and 0 behind. `CLAUDE.md` is unchanged, and the shared checkout was untouched (`main` at `e681392`, clean) |
| **Core 12 accepted** (Luiz) | `origin/main` fast-forwarded `9eb9d99..872ac45` by a plain, non-forced push of the exact commit |
| handoff | in a detached administrative worktree at `872ac45`, only `docs/chat-handoff.md` was changed: commit `8279cb2f160f0b0b00c69f4c888e9e0de61a5a23` (parent `872ac45`), pushed as a fast-forward to `main`. The administrative worktree was then removed |
| branch | `migration/conceptual-core-13` created at `8279cb2` from the **new** `origin/main` with `--no-track`, pushed with its own remote branch as upstream. This avoids the Core-12 upstream deviation from the start |
| Core-13 commits | `8689016` contract, **committed before any production change** · `6394a36` production change · `c14bd6c` checker · `add48c3` conceptual map · the commit that adds this report |
| gates measured at | the mechanical audit at `6394a36`; the checker mutation tests and the 10,000-state differential before `c14bd6c`; Gate A, the import audit, the replays, the instrumentation and both accepted-tree snapshots at `c14bd6c`; Gate A again at `add48c3`. `fov3d/` and `tools/` are identical at `c14bd6c` and `add48c3` |

The handoff records:
- Core 12 accepted at `872ac45`;
- that the intrinsic partition no longer owns candidate semantics;
- `candidate_policy` ownership of the `OTHER_SURFACE`/`UNKNOWN` → candidate rule;
- the Core-12 evidence: invariant, 70/70, 51/51 and 25/25 mutants, the 10,000/10,000
  differential, 8/8 byte-identical replays, baseline 31/31, `MISMATCHES 0`, 13 trees
  unchanged, and Phase-8b independence;
- Core 13 as the active question.

## Isolated worktrees and guard

- **Where it ran.** Every Core-13 edit and measurement ran in `<scratchpad>/core13/wt` on
  `migration/conceptual-core-13`.
- **Data links.** `previews/`, `.venv/` and the ignored `scenes/classroom/` entries are
  symlinked in.
- **Guard.** It requires, before and after every measurement, the branch, the expected HEAD
  and a clean tracked tree. It never tripped.
- **Core-12 reference.** The accepted Core-12 checker ran in a separate read-only
  **detached** worktree at `872ac45` (`<scratchpad>/core13/ref12wt`), which had 0 tracked
  changes.
- **Shared checkout.** `/home/lvelho/rd/f3d-vision` was not mutated and its branch was not
  switched.

## Exact production diff

**`fov3d/epistemic/partition.py`.** The complete non-docstring diff against Core 12, as
measured:

```text
-    all_target_ids: set[int],
-                row["reconstruction_status"] = (
-                    "mapped_now" if mapped_n
-                    else "targeted_later" if int(instance_id) in all_target_ids
-                    else "never_targeted"
-                )
```

The module docstring now says that Core 13 removed the reconstruction status and the target
schedule, and that `surface_source` stays. Nothing else changed:
- `REGION_KIND` and `REGION_KIND_BY_CODE`;
- the helpers and the imports;
- the `surface_source` block and the `mapped_n`/`incidental_n` counts;
- the gaze descriptor and `gazes_deg`;
- the diagnostics and the exceptions.

`fov3d/epistemic/__init__.py` is unchanged.

**New `fov3d/experiments/classroom_partition/run_context.py`** (81 lines). It contains:
- `_insert_after(mapping, anchor, key, value)`, a private copy of the Core-12 helper, so
  that `run_context` does not import `candidate_policy`. It raises `ValueError` on a present
  key and `KeyError` on a missing anchor.
- `annotate_reconstruction_status(region_rows, *, all_target_ids)`. It is non-mutating and
  returns new dicts, in order, sharing the same value objects. For
  `kind == "OTHER_SURFACE"` rows with an instance id, it inserts, immediately after
  `surface_source`:

      "mapped_now" if row["mapped_cells"] else "targeted_later" if int(row["instance_id"]) in all_target_ids else "never_targeted"

- `build_run_context_partition(state, *, target_id, target_name, all_target_ids, domain,
  grid_deg, gazes_deg)`, with the historical signature. It builds the intrinsic partition
  without the schedule, annotates the rows, and passes `arrays`, `edges` and `diag`
  through.

**`fov3d/experiments/classroom_partition/candidate_policy.py`.** The complete non-docstring
diff, as measured:

```text
- from fov3d.epistemic.partition import build_epistemic_partition
+ from fov3d.experiments.classroom_partition.run_context import build_run_context_partition
-     arrays, region_rows, edge_rows, diag = build_epistemic_partition(
+     arrays, region_rows, edge_rows, diag = build_run_context_partition(
```

Its module and function docstrings were updated too. `CANDIDATE_KINDS`, `_insert_after`
and `annotate_candidate_partition` are unchanged, and the `build_candidate_partition`
signature, including `all_target_ids`, is unchanged.

**Not modified:**
- `benchmark.py`, `prefix_benchmark.py`, `integration.py` and `challenge_suite.py`, which
  are byte-identical to Core 12; no mechanical change was needed;
- the Phase-5 `incidental.py` and every historical tool or checker.

## Changed files (main 8279cb2...final head)

| file | change |
|---|---|
| `docs/migration-conceptual-core-13.md` | contract (`8689016`) |
| `fov3d/epistemic/partition.py` | six lines removed; module docstring (`6394a36`) |
| `fov3d/experiments/classroom_partition/run_context.py` | **new** historical run-context layer (`6394a36`) |
| `fov3d/experiments/classroom_partition/candidate_policy.py` | one import, one called name, docstrings (`6394a36`) |
| `tools/dev/check_conceptual_core13.py` | new checker, 65 checks (`c14bd6c`) |
| `docs/conceptual-core-map.md` | Cores 1–12 accepted, Core 13 proposed (measured); a `run_context.py` row; the `candidate_policy` composition; a Core-13 section; the next question (`add48c3`) |
| `docs/migration-conceptual-core-13-report.md` | this report |

## Central Core-13 invariant

The five outputs compared are:
- `OLD_INTRINSIC` = accepted Core-12 `build_epistemic_partition(..., all_target_ids)`;
- `NEW_INTRINSIC` = the Core-13 intrinsic builder, without `all_target_ids`;
- `RECONTEXTUALIZED` = `annotate_reconstruction_status(NEW_INTRINSIC.rows, all_target_ids=...)`;
- `OLD_HISTORICAL` = accepted Core-12 `candidate_policy.build_candidate_partition(...)`;
- `NEW_HISTORICAL` = the Core-13 `candidate_policy.build_candidate_partition(...)`.

The invariant has six parts:
1. `NEW_INTRINSIC` arrays equal `OLD_INTRINSIC` arrays exactly;
2. `NEW_INTRINSIC` edges equal `OLD_INTRINSIC` edges exactly;
3. `NEW_INTRINSIC` diag equals `OLD_INTRINSIC` diag exactly;
4. `NEW_INTRINSIC` rows equal `OLD_INTRINSIC` rows minus only `reconstruction_status`;
5. `RECONTEXTUALIZED == OLD_INTRINSIC` rows, and `build_run_context_partition == OLD_INTRINSIC`;
6. `NEW_HISTORICAL == OLD_HISTORICAL`.

All of them are type-, value- and key-order-strict.

**Reference mechanism.** The checker and the differential execute accepted Core 12 from
`git show 872ac45` as isolated reference modules:
- `fov3d/epistemic/partition.py`;
- `fov3d/experiments/classroom_partition/candidate_policy.py`, with its one intrinsic-builder
  import (asserted to occur exactly once) replaced by a binding to the reference partition.

So `OLD_HISTORICAL` is the genuine accepted Core-12 composition. The comparison is
structural: exact Python types, dict key order, NumPy dtype, shape and values, and exact
floats.

| scope | result |
|---|---|
| fixtures H1 (4×6: all 5 kinds, all 3 `surface_source` and all 3 status values), H2 (2×6, 4/8 connectivity), H3 (target-free, no gazes), malformed shape | every invariant holds, and the ValueError is identical |
| seeded in-checker differential | 300/300 states. Each status occurred at least 50 times. Three controls were detected wherever they apply: status moved to the end, `targeted_later`/`never_targeted` swapped, schedule ignored |
| out-of-checker differential (`default_rng(20260930`), mechanical audit) | **10,000/10,000** states, 395,965 region rows, plus 400 more states in the throw-away audit. Sizes 1–14 × 1–16, grid 0.1–4°, target ids 7/3/25, 8 instance ids up to 70000, `all_target_ids` of 0–7 ids, varying densities, domains and gazes. Statuses mapped_now 122,222, targeted_later 40,690, never_targeted 40,391; all 5 kinds and all 3 sources |

The out-of-checker run included eight non-equivalent mutant stacks, each of which differed
from Core 12 on the listed number of states:

| control | states that differed |
|---|---|
| targeted/never swapped | 9281 |
| schedule ignored | 7102 |
| mapped threshold > 1 | 9435 |
| status at the end | 9842 |
| rows reordered | 9927 |
| `surface_source` `and`→`or` | 9821 |
| gaze max | 6692 |
| policy drops the schedule | 7102 |

The claimed-equivalent mutant differed on 0 states.

## Checker supersession

The accepted `tools/dev/check_conceptual_core12.py` asserts the Core-12 structure: the
intrinsic signature with `all_target_ids`, `reconstruction_status` from
`epistemic.partition`, and `candidate_policy` composing directly on the intrinsic builder,
which it spies on through `candidate_policy.build_epistemic_partition`. Core 13 intentionally
changes those facts.

- **A.** The Core-12 checker is **unmodified**. At `872ac45`, in the read-only reference
  worktree, it reports `[conceptual-core12-check] SUMMARY checked=70 failed=0`. This was
  measured in both Gate A runs.
- **B.** At the Core-13 head it is **not** a gate. For the record, it fails there (rc 1):
  - 24 named FAILs, from the signature, source/AST and projection checks, which call the
    intrinsic builder with `all_target_ids`;
  - then `AttributeError: module '...candidate_policy' has no attribute
    'build_epistemic_partition'` at its spy.

  This is exactly the intended structural change.
- **C.** The Core-13 checker subsumes every still-valid Core-12 guarantee:
  - the helper known answers and the hand-derived fixtures;
  - the candidate rule and identity;
  - `benchmark` compatibility;
  - Phase-8b independence;
  - the footprints.

  It adds the run-context tests.
- **D.** The Core-1 to Core-10 conceptual checkers pass unmodified at the current head.
- **E.** The Partition-Graph checkers 1–8b pass **unmodified**, through
  `benchmark.build_epistemic_partition` → `build_candidate_partition`.

This is architectural checker supersession, not regression.

## The Core-13 checker

`tools/dev/check_conceptual_core13.py` (859 lines) runs host-side and deterministically in
2.31 s. It prints `[conceptual-core13-check] SUMMARY checked=65 failed=0` and exits nonzero on
any failure. Source identities compare whole line ranges, so trailing comments count.

| section | checks | what is witnessed |
|---|---|---|
| reference | 1 | accepted Core-12 partition and candidate policy execute from `git show 872ac45`, bound together |
| **A** intrinsic structure | 10 | • `REGION_KIND`/`REGION_KIND_BY_CODE` and the six helpers identical;<br>• the signature is Core 12's minus **only** `all_target_ids`;<br>• the builder source is Core 12 minus exactly the parameter line and the five status lines, and its AST minus exactly the argument and the status assignment;<br>• no `all_target_ids` and no status string outside docstrings;<br>• the **`surface_source` block and the mapped/incidental counts** are source- and AST-identical;<br>• exactly the Core-12 names;<br>• identical imports, with no experiment, `run_context` or `candidate_policy` import;<br>• identical global bindings |
| **B** projection equivalence | 18 | • the helper known answers (subsumed);<br>• fixture coverage;<br>• per fixture, arrays/edges/diag exact, and rows = `project(OLD_INTRINSIC)`;<br>• the malformed shape;<br>• the hand-derived H1 rasters, rows (without candidate or status), edges and diag;<br>• the H2 connectivity and the H3 target-free/no-gaze case |
| **C** `surface_source` intrinsic | 3 | • the hand-derived intrinsic `surface_source` values and counts;<br>• no intrinsic status anywhere, and no `surface_source` on other kinds;<br>• **the schedule live control** |
| **D** status annotation | 5 | • the exact rule on synthetic rows, including mapped-but-unscheduled, and only `OTHER_SURFACE` rows;<br>• the rule reads `mapped_cells` (the accepted `mapped_n`), not `surface_source`;<br>• non-mutation, new dicts, order, and the same value objects;<br>• placement right after `surface_source` on real rows;<br>• the missing-anchor and double-annotation guards, and an empty list |
| **E** recontextualization | 4 | • `annotate(NEW_INTRINSIC) == OLD_INTRINSIC` rows;<br>• `build_run_context_partition == OLD_INTRINSIC`;<br>• one intrinsic build without the schedule and one annotation, with `arrays`/`edges`/`diag` passed through as the same objects;<br>• the historical signature |
| **F** candidate composition | 6 | • per fixture, `NEW_HISTORICAL == OLD_HISTORICAL`;<br>• one build = 1 intrinsic + 1 status annotation + 1 run-context call + 1 candidate annotation;<br>• the Core-12 policy functions unchanged, with `build_candidate_partition` differing only in the called builder;<br>• the policy imports `run_context`, not the intrinsic builder |
| **G** compatibility | 4 | • `benchmark.build_epistemic_partition` is the candidate wrapper and gives the Core-12 view, and `benchmark.CANDIDATE_KINDS` is the policy constant;<br>• the four producers and `incidental.py` are byte-identical to Core 12;<br>• the producers call only `build_candidate_partition` (1/1/2/1);<br>• **no duplicate status implementation**: status strings only in `run_context` and the unchanged Phase-5 `incidental`; only `run_context` imports the intrinsic builder; only `candidate_policy` imports `run_context` |
| **H** Phase 8b | 5 | • the base rows carry all three statuses;<br>• `refine_integrated_partition` on the Core-13 view equals that on the Core-12 view, and refined `OTHER_SURFACE` rows carry their origin's `surface_source` and status;<br>• `_component_rows`/`refine_integrated_partition` are AST-identical to Core 12;<br>• the `candidate_raw`/`eligible_candidate` known answers and status propagation;<br>• **independence** from `candidate_policy` and `run_context` (live control) |
| **I** footprints | 6 | • `__init__` unchanged;<br>• the exact fresh module lists for bare `fov3d.epistemic`, `epistemic.partition`, `run_context` and `candidate_policy`;<br>• the static imports, and no cycle in either order |
| **J** random differential | 3 | • 300 seeded states, invariants 1–6;<br>• each status at least 50 times;<br>• three controls detected wherever they apply |

### Mutation evidence (before the checker was committed)

**Dynamic mutants.** Substitutions with asserted counts were applied to `partition.py`,
`run_context.py` and/or `candidate_policy.py`, and loaded in dependency order as the real
modules before the checker.

| class | non-equivalent caught / total | examples |
|---|---|---|
| 1 future-context leakage (runtime) | 3 / 3 | schedule parameter retained; builder reads the schedule and emits the status; builder emits the status |
| 2 context rule | 12 / 12 | `mapped_now` inverted; `mapped_now` from `surface_source`; threshold > 1; targeted/never swapped; membership inverted; schedule ignored; id as str; all kinds; rows with an instance id; omitted for `OTHER_SURFACE`; misspelling; bytes |
| 3 reconstitution | 17 / 17 | status at the end or before `surface_source`; row dropped; rows reordered; another field; `surface_source` changed; non-`OTHER_SURFACE` row changed or aliased; in-place insert; guards removed (2); arrays dtype; arrays copied; edges reversed; diag changed; annotation skipped; schedule not forwarded |
| 4 intrinsic regression | 15 / 15 | precedence; UNKNOWN 8-connected; mapped owner; mapped count global; incidental count complement; `surface_source` `or`; `surface_source` strings; centroid x/y; mask 3; median→mean; gaze max; no interface accumulation; asymmetric adjacency; region order; vocabulary code |
| 5 wiring (policy side) | 3 / 3 | policy calls the intrinsic builder, losing the status; policy drops the schedule; policy skips the candidate annotation |
| **total** | **50 / 50** (0 survived; none caught only by a crash) | |

**Static mutants: 20/20 caught**, on throw-away `git ls-files | tar` copies; the unmutated
copy passes 65/0.
- **Class 1, future-context leakage (4):**
  - the intrinsic module importing `run_context`, or an experiment module at top level;
  - the schedule parameter restored;
  - an eager `__init__` import.
- **Class 5, wiring (6):**
  - `run_context` importing `candidate_policy`;
  - the policy also importing the intrinsic builder;
  - the `benchmark` alias bypassing the policy (bound to the run-context wrapper);
  - a producer (`integration`) bypassing the candidate view;
  - a duplicate status helper in `benchmark`;
  - the policy duplicating the status rule.
- **Class 6, Phase 8b (4):**
  - the status propagation removed from the refinement copy;
  - `candidate_raw` coupled to the status;
  - `eligible_candidate` `>=`→`>`;
  - `MIN_ELIGIBLE_CELLS` changed.
- **Drift (6):**
  - a helper comment;
  - a trailing comment on the `surface_source` block;
  - an extra import;
  - a trailing comment in `annotate_candidate_partition`;
  - the Phase-5 `incidental.py` touched;
  - a producer touched.

**Expected-pass control.** The status words used as prose in the intrinsic docstring pass
65/0, so the construction scan is not over-broad.

**Claimed-equivalent (recorded separately): `c_id_conversion_removed`.** It drops `int()`
around the instance id. Instance ids are Python ints and `all_target_ids` holds ints, so
this is the identity. It survived the checker, as expected, and differed on 0 of 10,000
differential states.

**One mutant deserves a note: `c_mapped_from_surface_source`.** On builder-generated rows,
`surface_source ∈ {mapped, mapped_and_incidental}` exactly when `mapped_cells > 0`, so
replays and differentials cannot see this mutant. It is caught only by the D check, which
states the declared rule (the status reads `mapped_cells`, the accepted `mapped_n`) on
synthetic rows where the two disagree.

**Checker defects fixed before commit** (no check was weakened):
1. **A crash.** `p8b_status_propagation_removed` was first caught only by an uncaught
   `KeyError` in H; the lookups were made non-raising.
2. **Trailing comments.** `policy_annotation_comment_drift` initially **survived**, because
   `ast.get_source_segment` excludes a trailing comment on a definition's last line. All
   source identities now compare whole line ranges.

The full suites were re-run on the final checker.

## Consumer wiring and compatibility (measured)

- **The producers** are byte-identical to Core 12:
  - `propose_phase6` (`benchmark`), `propose_phase7` (`prefix_benchmark`), `propose_phase8`
    (`integration`, 2 sites) and `propose_phase8b` (`challenge_suite`) all call
    `build_candidate_partition`;
  - none calls `build_run_context_partition` or the intrinsic builder.
- **`benchmark`:**
  - `benchmark.build_epistemic_partition is candidate_policy.build_candidate_partition`,
    returning the accepted Core-12 view;
  - `benchmark.CANDIDATE_KINDS is candidate_policy.CANDIDATE_KINDS`.
- **Module graph:**
  - `run_context` is the only production importer of the intrinsic builder;
  - `candidate_policy` is the only importer of `run_context`;
  - the status strings exist only in `run_context` and the unchanged Phase-5 `incidental.py`,
    whose separate `reconstruction_status()` helper is the deferred Phase-5 duplication.
- **Phase 8b:**
  - its base partition receives `reconstruction_status` through the composition;
  - `refine_integrated_partition` copies it (with `surface_source`, `mapped_cells`, etc.) to
    refined rows;
  - `candidate_raw`, `eligible_candidate`, `MIN_ELIGIBLE_CELLS` and the UNKNOWN shells are
    unchanged and independent (live control).

## Package footprints (fresh processes, Gate A)

| module | `fov3d` modules | `cv2` | `epistemic.partition` | `run_context` | `candidate_policy` | `benchmark` |
|---|---|---|---|---|---|---|
| `fov3d.epistemic` | 2 | no | no | no | no | no |
| `fov3d.epistemic.partition` | 5 (unchanged) | yes | — | no | no | no |
| `run_context` | 14 | yes | yes | — | no | no |
| `candidate_policy` | 15 | yes | yes | yes | — | no |
| `benchmark` | 16 | yes | yes | yes | yes | — |
| `prefix_benchmark` | 19 | yes | yes | yes | yes | yes |
| `integration` | 21 | yes | yes | yes | yes | yes |
| `challenge_suite` | 25 | yes | yes | yes | yes | yes |

- **`run_context`** loads the experiment-package footprint (11, via `lift`) plus
  `fov3d.epistemic`, `fov3d.epistemic.partition` and `run_context`. There is no
  `candidate_policy`, benchmark, evaluator, stereo, rendering or `bpy` module.
- **Deltas against Core 12** (the mechanical audit against a `git archive` of `872ac45`):
  `candidate_policy`, `benchmark`, `prefix_benchmark`, `integration` and `challenge_suite`
  each gain exactly `run_context`; `fov3d.epistemic` and `fov3d.epistemic.partition` are
  unchanged.
- **No import cycle** (both orders).

## Import/dependency audit and replay decisions

A fresh audit ran at `c14bd6c` under the guard:

| entry point | `epistemic.partition` | `run_context` | `candidate_policy` | `benchmark` | decision |
|---|---|---|---|---|---|
| Phase-6 proposer / evaluator | **yes** | **yes** | **yes** | **yes** | replayed |
| Phase-7 proposer / evaluator | **yes** | **yes** | **yes** | **yes** | replayed |
| Phase-8 proposer / evaluator | **yes** | **yes** | **yes** | **yes** | replayed |
| Phase-8b proposer / evaluator | **yes** | **yes** | **yes** | **yes** | replayed |
| Phase-2 lift, Phase-3 lift, Phase-4 analyzer, Phase-5 analyzer, (info) `partition_graph4_lift.py` | no | no | no | no | **not run** |

- **AST importers:**
  - the four producers, `candidate_policy` (→ `run_context`) and `run_context`
    (→ intrinsic);
  - checkers 11, 12 and 13, and the nested import in `check_conceptual_core2.py`;
  - Partition-Graph checkers 6, 7, 8 and 8b;
  - the Phase-6 tools;
  - demos 6, 7 and 8b.
- **Dynamic-import sites.** They are unchanged, plus the Core-13 checker's own
  `importlib.import_module`.

## Replays: commands, COMPLETE lines and byte comparisons

The replays ran from the worktree root under the guard at `c14bd6c`, each to a fresh
`previews/conceptual-core-13-*` directory, with the exact accepted Core-12 commands and
scopes.

Seven gates used the plain command:

```text
.venv/bin/python tools/partition_graph6_propose.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/partition-graph-5-full previews/conceptual-core-13-phase6-proposals
.venv/bin/python tools/partition_graph6_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-6-proposals previews/conceptual-core-13-phase6-evaluation
.venv/bin/python tools/partition_graph7_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-6-proposals previews/conceptual-core-13-phase7-proposals
.venv/bin/python tools/partition_graph7_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-7-proposals previews/partition-graph-6-evaluation previews/conceptual-core-13-phase7-evaluation
.venv/bin/python tools/partition_graph8_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8-proposals previews/partition-graph-7-evaluation previews/conceptual-core-13-phase8-evaluation
.venv/bin/python tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals previews/conceptual-core-13-phase8b-proposals
.venv/bin/python tools/partition_graph8b_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8b-proposals previews/partition-graph-8-evaluation previews/conceptual-core-13-phase8b-evaluation
```

The Phase-8 proposer's **required replay was itself instrumented**. The unmodified entry
script ran with its established arguments through the counting wrapper, so it ran once:

```text
.venv/bin/python <scratchpad>/core13/instrument.py tools/partition_graph8_integrate.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-7-proposals previews/conceptual-core-13-phase8-proposals
```

```text
[partition-graph6-propose] COMPLETE {"candidate_kinds": {"OTHER_SURFACE": 1384, "UNKNOWN": 288}, "candidate_regions": 1672, "targets": 25, "truth_used": false}
[partition-graph6-evaluate] COMPLETE {"candidate_recall": 0.9604904632152589, "covered": 25618, "miss_components": 103, "missed": 3670, "reachable": 29288, "truth_positive_candidate_regions": 30}
[partition-graph7-propose] COMPLETE {"global_candidates": 17202, "local_candidates": 8557, "phase6_final_local_parity": 25, "states": 104, "targets": 25, "truth_used": false}
[partition-graph7-evaluate] COMPLETE {"final": {"covered": 25618, "missed": 3670, "reachable": 29288}, "global_2plus_positive_states": 68, "global_recall": 0.4347697988686361, "local_2plus_positive_states": 63, "local_recall": 0.9713230672532999, "states": 104}
[partition-graph8-integrate] COMPLETE {"candidate_regions": 16825, "phase7_global_parity": 104, "states": 104, "target_evidence_unmapped_cells": 0, "targets": 25, "truth_used": false}
[partition-graph8-evaluate] COMPLETE {"cross_target_gain": 61538, "final_integrated_covered": 27948, "final_integrated_residual": 1340, "historical_state_misses": 101824, "integration_gain": 61557, "own_target_retention_gain": 19, "residual_candidate_recall": 0.955472222912062, "residual_state_misses": 40267, "states": 104}
[partition-graph8b-propose] COMPLETE {"eligible_candidates": 6489, "full_phase8_parity": 25, "raw_candidates": 18469, "scenarios": 5, "states": 125, "targets": 25, "truth_used": false}
[partition-graph8b-evaluate] COMPLETE {"full_eligible_recall": 0.9335820895522388, "full_integrated_covered": 27948, "full_integrated_residual": 1340, "scenarios": 5, "states": 125}
```

All eight lines are string-identical to the accepted Core-12 lines.

| gate | wall | accepted reference | accepted total | excluded | fresh = accepted scope | result | scope manifest sha256 |
|---|---|---|---|---|---|---|---|
| Phase-6 proposer | 2.87 s | `partition-graph-6-proposals` | 102 | — | 102 | byte-identical | `30e88f61da7ef1d43bc9bb530418f2d03c1403347b26f22a0d9a1c211309bbad` |
| Phase-6 evaluator | 1.46 s | `partition-graph-6-evaluation` | 59 | `demo/` 28, `demo-package-original/` 28 | 3 | byte-identical | `b584139a0186e014627452c74c811ed7b5281f3351255ae2596340ef6ae96fff` |
| Phase-7 proposer | 47.55 s | `partition-graph-7-proposals` | 835 | — | 835 | byte-identical | `3dde52e4cd34228f91c240db3682dc489d9f1adb74a5e85a7021b58bff1673de` |
| Phase-7 evaluator | 19.36 s | `partition-graph-7-evaluation` | 321 | `demo/` 107, `demo-package-original/` 107 | 107 | byte-identical | `05d35ef37a6294c0b0da08a1f943d7c9c8daef93c22819adb9beb8bdb3da0515` |
| **Phase-8 proposer** (instrumented) | 660.15 s | `partition-graph-8-proposals` | 468 | — | 468 | **byte-identical** | `69ccbfb748f250e19baebb75789e57c66f4c26443286e43a9a85ca77f474a209` |
| Phase-8 evaluator | 125.57 s | `partition-graph-8-evaluation` | 321 | `demo/` 107, `demo-package-original/` 107 | 107 | byte-identical | `01c8d253f5ea8698e8df290b7090f299d2fb462c6c40a0fdb04bdc7611525f7d` |
| Phase-8b proposer | 61.93 s | `partition-graph-8b-proposals` | 503 | — | 503 | byte-identical | `51a93fc464fc8ce00fc7f519ccadc25f539095be06de074788844b12ad6e7b7d` |
| Phase-8b evaluator | 16.74 s | `partition-graph-8b-evaluation` | 19 | `demo/` 8, `demo-package-original/` 8 | 3 | byte-identical | `243133b66237523147e1a869ee5b1bf97ee28ec9d817c5c059921e9b254c5715` |

Each comparison was two-sided:
- set equality after only the established exclusions, with no fresh file beneath an
  excluded path;
- `filecmp` with `shallow=False` on every pair;
- equal `LC_ALL=C` manifests.

`only_fresh`, `only_accepted`, `fresh_under_excluded` and `byte_diff` were 0 everywhere.

## Instrumentation counts and status counts

The instrumentation wrapped every stage, each delegating to the real object:
- `run_context`'s intrinsic-builder binding and `annotate_reconstruction_status`;
- `candidate_policy`'s `build_run_context_partition` binding and
  `annotate_candidate_partition`;
- the four producers' `build_candidate_partition` bindings;
- `benchmark`'s alias.

The Phase-8 count comes from its required replay. The other phases were instrumented in
separate scratch runs, whose outputs were also byte-identical to the accepted trees.

| run | intrinsic builds | status annotations | run-context calls | candidate annotations | candidate wrapper (binding) | alias | mapped_now | targeted_later | never_targeted |
|---|---|---|---|---|---|---|---|---|---|
| Phase-6 proposer | **25** | 25 | 25 | 25 | 25 (`benchmark`) | 0 | 929 | 455 | 0 |
| Phase-7 proposer | **208** | 208 | 208 | 208 | 208 (`prefix_benchmark`) | 0 | 15908 | 6957 | 0 |
| Phase-8 proposer | **208** | 208 | 208 | 208 | 208 (`integration`) | 0 | 20700 | 10639 | 0 |
| Phase-8b proposer | **125** | 125 | 125 | 125 | 125 (`challenge_suite`) | 0 | 8705 | 6900 | 0 |
| Phase-6, 7, 8 and 8b evaluators | **0** | 0 | 0 | 0 | 0 | 0 | — | — | — |

The composition is one-to-one in every producer, and the counts equal the Core-12
construction counts.

**Status reconciliation:**
- **Status counts against the `OTHER_SURFACE` rows.** In every producer, the statuses sum to
  the `OTHER_SURFACE` rows measured in Core 12: 929 + 455 = 1384; 15908 + 6957 = 22865;
  20700 + 10639 = 31339; 8705 + 6900 = 15605.
- **Phase 6 against the saved rows.** The accepted `partition-graph-6-proposals` rows,
  counted read-only, hold exactly 929 `mapped_now` and 455 `targeted_later`.
  - `surface_source` there is mapped 910, mapped_and_incidental 19 and incidental 455.
  - The 929 mapped surfaces are exactly the `mapped_now` ones, and the 455 incidental ones
    are exactly the `targeted_later` ones.
- **`never_targeted`** does not occur in the accepted Classroom products: every unmapped
  surface instance is in the manifest's target list. It is exercised by the fixtures and by
  40,391 differential rows.
- **Total rows and candidate rows** (3452/1672, 69228/25759, 104134/34027 and 54473/16547)
  equal Core 12's.

## Gate A

Gate A was run at `c14bd6c` and again at `add48c3`, with identical results:

| step | result |
|---|---|
| compile (changed Python) | ok |
| conceptual checkers | Core-13 65/0; Core-10 29/0, Core-9 24/0, Core-8 20/0, Core-7 22/0, Core-6 35/0, Core-5 38/0, Core-4 32/0, Core-3 27/0, Core-2 20/0, Core-1 13/0 (unmodified) |
| accepted Core-12 checker at `872ac45` (read-only detached worktree, 0 tracked changes) | 70/0 |
| Partition-Graph checkers (unmodified) | 1: 13/0, 2: 16/0, 3: 20/0, 4: 14/0, 5: 12/0, 6: 12/0, 7: 12/0, 8: 10/0, 8b: 12/0 |
| facade | 16/0 |
| `scripts/verify_baseline.sh` | `[verify] SUMMARY passed=9 failed=0` (31/31) |
| `scripts/compare_golden.sh previews/partition-graph-2-source-full` | `[compare-golden] MISMATCHES 0` (9.80 s; 9.90 s) |
| `git diff --check` (worktree, and `8279cb2..HEAD`) | clean |
| fresh footprints | as tabulated above |

## Accepted-tree integrity

Full-tree per-file sha256 manifests of the 13 accepted trees were taken under the guard at
`c14bd6c`, before the first replay and after the last replay and instrumentation. They are
**identical**, and also identical to Core 12's final snapshot. The per-tree manifest values
are those recorded in `docs/migration-conceptual-core-12-report.md`, for example
`partition-graph-8-proposals` 468 files `69ccbfb7…` and `partition-graph-2-source-full` 1122
files `9c4def89…`.

## Changed-path → executed-gate coverage

| changed path | kind | exercised by | execution evidence |
|---|---|---|---|
| `fov3d/epistemic/partition.py` (six lines removed) | intrinsic redesign | A/B/C/J checker; the 10,000-state differential; Phases 6–8b | 25 / 208 / 208 / 125 intrinsic builds; all products byte-identical |
| `run_context.py` (new) | historical run context | C/D/E/G/H/I/J checker; the differential; Phases 6–8b | status annotations and run-context calls one-to-one with the intrinsic builds; the status counts reconcile with the saved Phase-6 rows; byte-identical |
| `candidate_policy.py` (import and call) | composition | F/G/I checker; unmodified Partition-Graph checkers 6/7/8 (through the alias); Phases 6–8b | candidate annotations and wrapper calls one-to-one; byte-identical |
| `fov3d/epistemic/__init__.py`, the four producers, `incidental.py` | **unchanged** | G/I | byte equality with Core 12; footprints |
| `tools/dev/check_conceptual_core13.py` | new checker | Gate A; mutation harnesses | 65/65; 50/50 dynamic and 20/20 static mutants caught |

## Repairs and deviations

1. **No production repair was needed.** No gate failed against the implementation, and no
   producer needed a mechanical change.
2. **Checker strengthening before commit.** Two defects were found while designing the
   mutants: a crash-only catch, and trailing-comment drift that survived. Both were fixed,
   the first with non-raising lookups and the second by **adding** whole-line source
   identity. No check was weakened, and the full suites were re-run on the final checker.
3. **Replay/instrumentation arrangement** (as the contract allows):
   - the Phase-8 proposer's required replay was run **once**, through the counting wrapper;
   - the seven other gates used the plain established commands, plus cheap instrumented
     scratch runs.
4. **`_insert_after` duplication.** `run_context` has its own small private copy of the
   Core-12 helper, so it does not depend on `candidate_policy`, which would invert the
   composition. This is recorded, not a behavioral duplicate.

No other deviation.

## Deferred (explicitly not part of Core 13)

1. `min_distance_to_historical_gaze_deg`, the Core-14 question.
2. The `gazes_deg` input to the intrinsic partition.
3. Broader observer/attention-history representation.
4. The placement of the target-relative `HeadEvidence` fields.
5. The Phase-5 `reconstruction_status` duplication (`incidental.reconstruction_status`,
   unchanged).
6. `_own_labels` versus `own_support_labels`.
7. `component_lineage` versus `scene.lineage._lineage`.
8. The `attach_state_region_codes` rename.
9. The consumerless compatibility aliases.
10. The historical Phase-2/Phase-3 boundary lineage cleanup.

No Core 14 in this run.

## Unresolved decisions (for Luiz and Chat)

- Whether to accept Core 13 and fast-forward `main` to the final head of this branch.
- The Core-14 design for the historical gaze context (`min_distance_to_historical_gaze_deg`,
  `gazes_deg`).

## Acceptance

| criterion | status |
|---|---|
| intrinsic `build_epistemic_partition` no longer accepts `all_target_ids` | MEASURED pass |
| intrinsic rows no longer contain `reconstruction_status`; output = Core 12 minus **only** that field | MEASURED pass (fixtures, 300 + 10,000 random states) |
| `surface_source` stays intrinsic and unchanged | MEASURED pass (source/AST identity, hand-derived values, schedule live control) |
| `run_context` reconstitutes the accepted Core-12 intrinsic rows exactly | MEASURED pass |
| `candidate_policy` reconstitutes the accepted Core-12 historical output exactly | MEASURED pass |
| no experiment/run-context dependency in `epistemic.partition` | MEASURED pass |
| historical compatibility intact | MEASURED pass |
| Phase-8b propagation exact | MEASURED pass |
| Core-13 checker fail-capable; random differential clean | MEASURED pass (50/50 + 20/20; 10,000/10,000) |
| Core-1 to Core-10 checkers pass at the current head | MEASURED pass |
| accepted Core-12 checker passes at `872ac45` | MEASURED pass (70/70) |
| all Partition-Graph checkers pass unmodified | MEASURED pass (1–8b) |
| baseline 31/31; golden `MISMATCHES 0` | MEASURED pass |
| every reached Phase-6/7/8/8b product byte-identical | MEASURED pass (8/8) |
| 13 accepted reference trees unchanged | MEASURED pass |
| all changed production paths covered by executed gates | MEASURED pass |

    CONCEPTUAL_CORE13_RECONSTRUCTION_STATUS_SEPARATION_PRESERVES_BEHAVIOR
