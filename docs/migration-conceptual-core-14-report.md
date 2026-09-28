# Migration Conceptual Core 14 — report

**Result.**

    CONCEPTUAL_CORE14_GAZE_CONTEXT_SEPARATION_PRESERVES_BEHAVIOR

This result is MEASURED and awaits review by Luiz and Chat. Core 14 is **not** merged into
`main`. No controller logic was implemented.

**Causal question.** Can action-history-derived gaze context (`gazes_deg` and
`min_distance_to_historical_gaze_deg`) be removed from the intrinsic epistemic partition and
reconstructed as a separate historical gaze-context annotation, while reproducing every
accepted Core-13 historical product exactly?

**Answer (measured): yes.**

    accepted Core-13 intrinsic partition = Core-14 intrinsic partition
                                         + historical gaze-context annotation

The evidence:
- **The intrinsic partition.** `fov3d.epistemic.partition.build_epistemic_partition` no
  longer accepts `gazes_deg` or emits the gaze-distance field. Its source is accepted Core 13
  minus exactly six lines, the docstring aside.
- **What stays.** Every evidence-history field and the generic `_angular_distance_deg` are
  unchanged.
- **The gaze-context layer.** The new experiment-side
  `fov3d/experiments/classroom_partition/gaze_context.py` re-creates the accepted rows
  exactly.
- **The composition.** `run_context` composes on it, while `candidate_policy` and the four
  historical producers are byte-identical to Core 13.
- **The eight-part invariant against accepted Core 13 (`3b7091e`)** holds on every fixture,
  on 300 seeded states inside the checker, and on 10,000 random states outside it, across
  empty, one-gaze and multi-gaze histories.
- **The checker.** The Core-14 checker passes 64/64. It caught all 48 non-equivalent dynamic
  mutants and all 22 static mutants.
- **Existing checkers.** The accepted Core-13 checker passes 65/65 at `3b7091e`. The Core-1
  to Core-10 checkers and the Partition-Graph checkers 1–8b pass **unmodified**.
- **Replays.** All 8 reached Phase-6/7/8/8b products are **byte-identical**, and the seven
  composition stages are one-to-one in every producer.
- **Accepted trees, baseline and golden.** The 13 accepted trees are unchanged, the baseline
  is 31/31, and golden reports `MISMATCHES 0`.

## Evidence history versus action history

| quantity | derived from | history | Core 14 |
|---|---|---|---|
| `seen_any_fraction`, `head_depth_fraction` | accumulated state masks `seen_any`, `depth_seen` | evidence | **intrinsic**, unchanged |
| `mapped_cells`, `incidental_cells`, `surface_source` | identity evidence in the state | evidence | **intrinsic**, unchanged |
| `min_distance_to_historical_gaze_deg` | region centroid **and previous fixation directions** | the observer's **action** history | **moved** to `gaze_context` |

The checker's **action-history independence witness** covers two points:
- the same state, built without any gaze argument, gives identical arrays, rows, edges and
  diag, whatever history is applied afterwards;
- the gaze-context annotation does change: `None` everywhere with no gaze, one set of floats
  with one gaze, another with two.

The intrinsic builder now rejects a `gazes_deg` keyword with a `TypeError`.

## Provenance: Core-13 acceptance administration and branch

| step | result |
|---|---|
| pre-check (fetch) | `origin/main = 8279cb2f160f0b0b00c69f4c888e9e0de61a5a23` and `origin/migration/conceptual-core-13 = 3b7091ed7a8f58cfc84c552431bfe60dc694aad3`, both verified. `3b7091e` descends from `8279cb2`; Core 13 is 5 ahead and 0 behind. `CLAUDE.md` is unchanged, and the shared checkout was untouched (`main` at `e681392`, clean) |
| **Core 13 accepted** (Luiz) | `origin/main` fast-forwarded `8279cb2..3b7091e` by a plain, non-forced push of the exact commit |
| handoff | in a detached administrative worktree at `3b7091e`, only `docs/chat-handoff.md` was changed: commit `fe187679935466674c8ea4ce016554557b94114a` (parent `3b7091e`), pushed as a fast-forward to `main`. The administrative worktree was then removed |
| branch | `migration/conceptual-core-14` created at `fe18767` from the new `origin/main` with `--no-track`, pushed with its own remote upstream |
| Core-14 commits | `dbf2b37` contract, **committed before any production change** · `5fcff20` production change · `cea5234` checker · `02e1d11` conceptual map · the commit that adds this report |
| gates measured at | the mechanical audit at `5fcff20`; the mutation tests and the 10,000-state differential before `cea5234`; Gate A, the import audit, the replays, the instrumentation and both snapshots at `cea5234`; Gate A again at `02e1d11`. `fov3d/` and `tools/` are identical at `cea5234` and `02e1d11` |

The handoff records:
- Core 13 accepted at `3b7091e`;
- the intrinsic partition independent of `all_target_ids`;
- `reconstruction_status` in `run_context`, with `surface_source` intrinsic;
- the candidate composition;
- the Core-13 evidence: 65/65, 50/50 and 20/20 mutants, the 10,000/10,000 differential, 8/8
  byte-identical, baseline 31/31, `MISMATCHES 0`, 13 trees unchanged;
- Core 14 as the active question;
- after Core 14, pending acceptance, integrated foveal-controller design rather than further
  historical cleanup.

## Isolated worktrees and guard

- **Where it ran.** Every Core-14 edit and measurement ran in `<scratchpad>/core14/wt` on
  `migration/conceptual-core-14`.
- **Data links.** `previews/`, `.venv/` and the ignored `scenes/classroom/` entries are
  symlinked in.
- **Guard.** It requires, before and after every measurement, the branch, the expected HEAD
  and a clean tracked tree. It never tripped.
- **Core-13 reference.** The accepted Core-13 checker ran in a read-only **detached**
  worktree at `3b7091e`, which had 0 tracked changes.
- **Shared checkout.** It was not mutated and its branch was not switched.

## Exact production diff

**`fov3d/epistemic/partition.py`.** The complete non-docstring diff against Core 13, as
measured:

```text
-    gazes_deg: list[tuple[float, float]],
-            gaze_dist = [
-                _angular_distance_deg((cyaw, cpitch), (float(y), float(p)))
-                for y, p in gazes_deg
-            ] if gazes_deg and np.isfinite(cyaw) and np.isfinite(cpitch) else []
-                "min_distance_to_historical_gaze_deg": None if not gaze_dist else float(min(gaze_dist)),
```

The docstring now says that Core 14 removed the action history, and that
`_angular_distance_deg` stays as a generic helper. The helper is **deliberately retained**,
source- and AST-identical. It is no longer called by the intrinsic builder, and is used by
`gaze_context`. Unchanged:
- the constants and all helpers;
- every other row field, in the same order;
- the arrays, the diagnostics, the exceptions and the imports.

`fov3d/epistemic/__init__.py` is unchanged.

**New `fov3d/experiments/classroom_partition/gaze_context.py`** (79 lines). It imports
`build_epistemic_partition` and `_angular_distance_deg` from the intrinsic module. It
contains:
- `_insert_after`, a private copy of the helper; see the deviations.
- `annotate_gaze_context(region_rows, *, gazes_deg)`. It is non-mutating and returns new
  dicts, in order, with the same value objects. For **every** row it inserts, immediately
  after `median_distance_to_target_deg`:

      None if no gaze distance else float(min(_angular_distance_deg((centroid_yaw_deg, centroid_pitch_deg), (float(y), float(p))) for y, p in gazes_deg))

  The distances are computed only when `gazes_deg` is non-empty and both centroid
  coordinates are finite, exactly as accepted.
- `build_gaze_context_partition(state, *, target_id, target_name, domain, grid_deg,
  gazes_deg)`, with the historical Core-13 intrinsic signature. It passes `arrays`, `edges`
  and `diag` through.

**`fov3d/experiments/classroom_partition/run_context.py`.** The complete non-docstring diff,
as measured:

```text
- from fov3d.epistemic.partition import build_epistemic_partition
+ from fov3d.experiments.classroom_partition.gaze_context import build_gaze_context_partition
-     arrays, region_rows, edge_rows, diag = build_epistemic_partition(
+     arrays, region_rows, edge_rows, diag = build_gaze_context_partition(
```

Its module and function docstrings were updated too. The call arguments, the signature,
`_insert_after`, `annotate_reconstruction_status` and the status rule are unchanged.

**Not modified:**
- `candidate_policy.py`, and `benchmark.py`, `prefix_benchmark.py`, `integration.py` and
  `challenge_suite.py`, which are byte-identical to Core 13; no mechanical change was needed;
- the Phase-5 `incidental.py`, and every historical tool or checker.

## Changed files (main fe18767...final head)

| file | change |
|---|---|
| `docs/migration-conceptual-core-14.md` | contract (`dbf2b37`) |
| `fov3d/epistemic/partition.py` | six lines removed; module docstring (`5fcff20`) |
| `fov3d/experiments/classroom_partition/gaze_context.py` | **new** (`5fcff20`) |
| `fov3d/experiments/classroom_partition/run_context.py` | one import, one called name, docstrings (`5fcff20`) |
| `tools/dev/check_conceptual_core14.py` | new checker, 64 checks (`cea5234`) |
| `docs/conceptual-core-map.md` | Cores 1–13 accepted, Core 14 proposed (measured); a `gaze_context.py` row; the post-Core-14 architecture; the controller as the next activity (`02e1d11`) |
| `docs/migration-conceptual-core-14-report.md` | this report |

## Accepted target-local gaze semantics (unchanged)

These were measured in the live code and are checked structurally (H) and byte-wise (the
four producers are identical to Core 13):

| phase | producer list passed as `gazes_deg` | comprehension iterable |
|---|---|---|
| 6 | `gazes` | `obj.get('trajectory', [])`, every gaze of the target |
| 7 | `current_target_gazes`, passed to **both** the local and global arms; `global_gazes` is reporting-only and never passed | `trajectory[:local_step + 1]` |
| 8 | `current_gazes`, at both partition call sites | `trajectory[:local_step + 1]` |
| 8b | `current_gazes`, the retained prefix under the scenario budget | `list(obj.get('trajectory', []))[:keep]` |

Each comprehension is `tuple(map(float, r['gaze_deg'])) for r in ... if 'gaze_deg' in r`.
Static mutants that replace any of these (global gazes, an off-by-one prefix, the whole
trajectory, an ignored budget) are caught.

## Central Core-14 invariant

The eight outputs compared are:
- `OLD_INTRINSIC` = accepted Core-13 `build_epistemic_partition(..., gazes_deg)`;
- `NEW_INTRINSIC` = the Core-14 intrinsic builder, without `gazes_deg`;
- `REGAZED` = `annotate_gaze_context(NEW_INTRINSIC.rows, gazes_deg=...)`;
- `OLD_RUN_CONTEXT` and `NEW_RUN_CONTEXT` = the Core-13 and Core-14
  `build_run_context_partition`;
- `OLD_HISTORICAL` and `NEW_HISTORICAL` = the Core-13 and Core-14
  `build_candidate_partition`.

The invariant has eight parts:
1. `NEW_INTRINSIC` arrays equal `OLD_INTRINSIC` arrays;
2. `NEW_INTRINSIC` edges equal `OLD_INTRINSIC` edges;
3. `NEW_INTRINSIC` diag equals `OLD_INTRINSIC` diag;
4. `NEW_INTRINSIC` rows equal `OLD_INTRINSIC` rows minus only the gaze field;
5. `REGAZED == OLD_INTRINSIC` rows;
6. `build_gaze_context_partition == OLD_INTRINSIC`;
7. `NEW_RUN_CONTEXT == OLD_RUN_CONTEXT`;
8. `NEW_HISTORICAL == OLD_HISTORICAL`.

All of them are type-, value- and key-order-strict.

**Reference mechanism.** Accepted Core 13's `partition.py`, `run_context.py` and
`candidate_policy.py` are executed from `git show 3b7091e` as isolated reference modules.
Each one-line intra-stack import is asserted to occur exactly once and replaced by a binding
to the reference module below it, so the Core-13 stack is reproduced exactly.

| scope | result |
|---|---|
| fixtures H1-multi, H1-one, H1-none, H2-one, H3-none, H3-multi, and the malformed shape | all eight invariants hold |
| seeded in-checker differential | 300/300 states. Each of empty, one-gaze and multi-gaze occurred at least 30 times, with at least 500 finite distances. Three controls were detected wherever they apply: field moved to the end, max instead of min, 0.0 instead of `None` |
| out-of-checker differential (`default_rng(20261002)`) | **10,000/10,000** states, 393,998 region rows, plus 400 states in the throw-away audit. Histories: empty 2,528, one 2,515, multi 4,957; 26,055 gaze entries; gaze field `None` 98,229 rows, finite 295,769 rows |

The out-of-checker run included nine non-equivalent mutant stacks, each of which differed
from Core 13 on the listed number of states:

| control | states that differed |
|---|---|
| max | 4957 |
| first gaze only | 4214 |
| centroid swapped | 7472 |
| no-gaze → 0.0 | 2528 |
| field at the end | 10000 |
| rows reordered | 9924 |
| seen = depth | 9866 |
| `run_context` first gaze only | 4214 |
| policy drops the gazes | 7472 |

The claimed-equivalent mutant differed on 0 states.

## Checker supersession

The accepted `tools/dev/check_conceptual_core13.py` asserts the Core-13 structure: `gazes_deg`
accepted by the intrinsic builder, the gaze field as intrinsic, and `run_context` building the
intrinsic partition directly, with a spy on `run_context.build_epistemic_partition`.

- **A.** It is **unmodified**. At `3b7091e`, in the read-only reference worktree, it reports
  `[conceptual-core13-check] SUMMARY checked=65 failed=0` in both Gate A runs.
- **B.** At the Core-14 head it is not a gate. For the record, it fails there (rc 1):
  - 20 named FAILs, from its intrinsic-signature, source/AST and projection checks;
  - then `AttributeError: module '...run_context' has no attribute
    'build_epistemic_partition'` at its spy.

  This is the intended structural change.
- **C.** The Core-14 checker subsumes every still-valid Core-13 guarantee:
  - the helper known answers and the hand-derived fixtures;
  - the reconstruction-status rule, now as Core-13 source identity plus run-context
    identity;
  - the candidate identity and `benchmark` compatibility;
  - the Phase-8b propagation and independence;
  - the footprints.

  It adds the gaze-context tests.
- **D.** The Core-1 to Core-10 conceptual checkers pass unmodified.
- **E.** The Partition-Graph checkers 1–8b pass **unmodified**.

This is explicit architectural-checker supersession, not regression.

## The Core-14 checker

`tools/dev/check_conceptual_core14.py` (891 lines) runs host-side and deterministically in
3.39 s. It prints `[conceptual-core14-check] SUMMARY checked=64 failed=0`, and source
identities use whole line ranges.

| section | checks | what is witnessed |
|---|---|---|
| reference | 1 | accepted Core-13 partition, run context and candidate policy execute from `git show 3b7091e`, bound together |
| **A** intrinsic structure | 10 | • the constants, and the six helpers **including `_angular_distance_deg`**, identical;<br>• the signature minus **only** `gazes_deg`;<br>• the builder source minus exactly the parameter, the four `gaze_dist` lines and the gaze entry;<br>• the AST minus exactly the argument, the assignment and the entry;<br>• no `gazes_deg`/`gaze_dist` and no gaze field;<br>• **every other row field identical, in order**;<br>• the same names and imports, with no experiment, `gaze_context`, `run_context` or `candidate_policy`;<br>• equivalent bindings, with the builder no longer calling `_angular_distance_deg` |
| **B** projection equivalence | 16 | • the helper known answers (subsumed);<br>• fixture coverage: all kinds and sources, edge flags, 4/8 connectivity, target-free, and no/one/multi-gaze with finite distances;<br>• per fixture, arrays/edges/diag exact, and rows = `project(OLD_INTRINSIC)`;<br>• the malformed shape;<br>• the hand-derived H1 intrinsic rows, edges and diag;<br>• the H2 connectivity and the H3 target-free case |
| **C** action-history independence | 3 | • a `gazes_deg` keyword is rejected;<br>• the same state gives an identical intrinsic output whatever history is applied;<br>• **a live control**: the annotation changes (`None`, one gaze, two gazes, and a gaze on region 5's centroid giving ≈0) |
| **D** gaze rule | 6 | • the exact rule on synthetic rows of every kind, with a non-finite centroid giving `None`;<br>• the minimum is the **middle** gaze, so first, last, mean, max, yaw/pitch-swapped and centroid-swapped are all distinguishable;<br>• an empty history gives `None`, and integer gaze components are accepted;<br>• non-mutation, order and the same value objects;<br>• placement right after `median_distance_to_target_deg` on real rows;<br>• the guards |
| **E** regazing identity | 4 | • `annotate(NEW_INTRINSIC) == OLD_INTRINSIC` and `build_gaze_context_partition == OLD_INTRINSIC`, for every fixture and history;<br>• one intrinsic build without gazes, one annotation, and pass-through of arrays/edges/diag;<br>• the historical signature |
| **F** run-context composition | 3 | • `NEW_RUN_CONTEXT == OLD_RUN_CONTEXT`;<br>• one call = 1 intrinsic + 1 gaze annotation + 1 gaze-context call + 1 status annotation;<br>• `run_context` imports `gaze_context`, with the status functions unchanged, the builder differing only in the called name, and the same signature |
| **G** candidate composition | 3 | • `candidate_policy.py` byte-identical to Core 13;<br>• `NEW_HISTORICAL == OLD_HISTORICAL`;<br>• the full call path is one-to-one across the six stages |
| **H** provenance and wiring | 4 | • `benchmark` compatibility;<br>• the four producers and `incidental.py` byte-identical;<br>• **the target-local gaze provenance** (the table above), with `global_gazes` never passed;<br>• no duplicate gaze metric: only `gaze_context` calls `_angular_distance_deg` or names the field |
| **I** Phase 8b | 5 | • the base rows carry the gaze field;<br>• refinement on the Core-14 view equals that on the Core-13 view;<br>• **refined rows do not carry the gaze field**, while `surface_source`/`reconstruction_status` propagate;<br>• `_component_rows`/`refine_integrated_partition` AST-identical;<br>• the `candidate_raw`/`eligible_candidate` known answers, and **independence from the gaze context** (live control) |
| **J** footprints | 6 | • `__init__` unchanged;<br>• the exact fresh module lists for `fov3d.epistemic`, `epistemic.partition`, `gaze_context`, and `run_context` + `candidate_policy`;<br>• the static imports, and no cycle |
| **K** random differential | 3 | • 300 seeded states, all eight invariants;<br>• the history mix;<br>• three controls detected wherever they apply |

### Mutation evidence (before the checker was committed)

**Dynamic mutants.** Substitutions with asserted counts were applied to `partition.py`,
`gaze_context.py`, `run_context.py` and/or `candidate_policy.py`, and loaded in dependency
order as the real modules before the checker.

| class | non-equivalent caught / total | examples |
|---|---|---|
| 1 action-history leakage (runtime) | 3 / 3 | `gazes_deg` retained (with a default); builder reads gazes and emits the field; builder emits the field |
| 2 gaze annotation | 13 / 13 | max; mean; first only; last only; gaze yaw/pitch swapped; centroid swapped; gaze truncated to int; no-gaze → 0.0; `isfinite` guard dropped; only candidate kinds; omitted for ambiguous; key misspelled; `np.float64` type |
| 3 reconstitution | 14 / 14 | field at the end or before the target median; row dropped; rows reordered; another field changed; in-place insert; guards removed (2); arrays dtype; arrays copied; edges reversed; diag changed; annotation skipped; gazes not forwarded |
| 4 intrinsic regression | 13 / 13 | precedence; UNKNOWN 8-connected; mapped owner; median→mean; centroid x/y; mapped count; `surface_source` `or`; seen = depth; depth sum; asymmetric adjacency; no interface accumulation; region order; `_angular_distance_deg` without clip |
| 5 wiring (runtime) | 5 / 5 | `run_context` calls the intrinsic builder; `run_context` drops the gazes; `run_context` first gaze only; `run_context` skips the status; policy drops the gazes |
| **total** | **48 / 48** (0 survived; none caught only by a crash) | |

**Static mutants: 22/22 caught**, on throw-away `git ls-files | tar` copies; the unmutated
copy passes 64/0.
- **Class 1, action-history leakage (4):**
  - the intrinsic module importing `gaze_context`, or an experiment module at top level;
  - the gaze parameter restored;
  - an eager `__init__` import.
- **Class 5, wiring (9):**
  - `gaze_context` importing `run_context`;
  - `run_context` also importing the intrinsic builder;
  - `run_context` duplicating the gaze metric;
  - `candidate_policy` importing `gaze_context`;
  - Phase 7 passing `global_gazes`;
  - a Phase-7 prefix off by one;
  - Phase 8 using the whole trajectory;
  - Phase 8b ignoring the budget;
  - a duplicate gaze metric in `benchmark`.
- **Class 6, Phase 8b (4):**
  - the gaze field propagated to refined rows;
  - the status propagation removed;
  - `candidate_raw` coupled to the gaze distance;
  - `eligible_candidate` `>=`→`>`.
- **Drift (5):**
  - a trailing comment on `_angular_distance_deg`, or on the intrinsic median row entry;
  - a trailing comment in the `run_context` status function;
  - `candidate_policy` touched;
  - `incidental.py` touched.

**Expected-pass control.** The gaze-field name in the intrinsic docstring's prose passes
64/0.

**Claimed-equivalent (recorded separately): `g_float_removed`.** It drops `float()` around
the gaze components. The producers already pass floats, and `math.radians` accepts ints and
floats alike. It survived, as expected, and differed on 0 of 10,000 differential states.

**Checker defects fixed before commit** (no check was weakened):
1. **A tolerance.** The C live control first expected the distance from a gaze placed on
   region 5's centroid to be 0 within 1e-6. It is 1.48e-6°, from `acos` roundoff. The
   tolerance was set to 1e-5, the value the accepted Core-11 checker uses for gaze
   distances. This was an expectation error in the new checker, not an implementation
   difference.
2. **Crash-only catches.** Three mutants (`g_only_candidate_kinds`,
   `g_omitted_for_ambiguous`, `g_key_spelling`) were first caught only by a `KeyError` in the
   C and D checks. The lookups were made non-raising, and each is now caught by 12–13 named
   FAILs.

The full dynamic suite was re-run on the final checker.

## Consumer wiring and package footprints

- **The call path** is:
  - the producers → `build_candidate_partition` (`candidate_policy`, unchanged);
  - → `build_run_context_partition` (`run_context`);
  - → `build_gaze_context_partition` (`gaze_context`);
  - → `build_epistemic_partition` (intrinsic).
- **Importers:**
  - `gaze_context` is the only production importer of the intrinsic builder;
  - `run_context` is the only importer of `gaze_context`;
  - `candidate_policy` is the only importer of `run_context`.
- **`benchmark`:** `benchmark.build_epistemic_partition` is `build_candidate_partition`, and
  `benchmark` still re-exports `_angular_distance_deg` as a compatibility name, uncalled.

| module (fresh process) | `fov3d` modules | `epistemic.partition` | `gaze_context` | `run_context` | `candidate_policy` | `benchmark` |
|---|---|---|---|---|---|---|
| `fov3d.epistemic` | 2 | no | no | no | no | no |
| `fov3d.epistemic.partition` | 5 (unchanged) | — | no | no | no | no |
| `gaze_context` | 14 | yes | — | no | no | no |
| `run_context` | 15 | yes | yes | — | no | no |
| `candidate_policy` | 16 | yes | yes | yes | — | no |
| `benchmark` / `prefix_benchmark` / `integration` / `challenge_suite` | 17 / 20 / 22 / 26 | yes | yes | yes | yes | — / yes / yes / yes |

Against Core 13 (the mechanical audit on a `git archive` of `3b7091e`), each of `run_context`,
`candidate_policy` and the four producers gains exactly `gaze_context`. `fov3d.epistemic` and
`fov3d.epistemic.partition` are unchanged. There is no stereo, rendering, evaluator or `bpy`
module in the context layers, and no cycle.

## Import/dependency audit and replay decisions

A fresh audit ran at `cea5234` under the guard:

| entry point | `epistemic.partition` | `gaze_context` | `run_context` | `candidate_policy` | `benchmark` | decision |
|---|---|---|---|---|---|---|
| Phase-6/7/8/8b proposers and evaluators | **yes** | **yes** | **yes** | **yes** | **yes** | replayed (8) |
| Phase-2 lift, Phase-3 lift, Phase-4 analyzer, Phase-5 analyzer, (info) `partition_graph4_lift.py` | no | no | no | no | no | **not run** |

The dynamic-import sites are unchanged, plus the Core-14 checker's own
`importlib.import_module`.

## Replays: commands, COMPLETE lines and byte comparisons

The replays ran under the guard at `cea5234`, each to a fresh `previews/conceptual-core-14-*`
directory, with the exact accepted Core-13 commands, inputs and scopes. Seven used the plain
command:

```text
.venv/bin/python tools/partition_graph6_propose.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/partition-graph-5-full previews/conceptual-core-14-phase6-proposals
.venv/bin/python tools/partition_graph6_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-6-proposals previews/conceptual-core-14-phase6-evaluation
.venv/bin/python tools/partition_graph7_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-6-proposals previews/conceptual-core-14-phase7-proposals
.venv/bin/python tools/partition_graph7_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-7-proposals previews/partition-graph-6-evaluation previews/conceptual-core-14-phase7-evaluation
.venv/bin/python tools/partition_graph8_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8-proposals previews/partition-graph-7-evaluation previews/conceptual-core-14-phase8-evaluation
.venv/bin/python tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals previews/conceptual-core-14-phase8b-proposals
.venv/bin/python tools/partition_graph8b_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8b-proposals previews/partition-graph-8-evaluation previews/conceptual-core-14-phase8b-evaluation
```

The Phase-8 proposer's **required replay was itself instrumented**, so it ran once:

```text
.venv/bin/python <scratchpad>/core14/instrument.py tools/partition_graph8_integrate.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-7-proposals previews/conceptual-core-14-phase8-proposals
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

All eight lines are string-identical to the accepted Core-13 lines. `full_phase8_parity: 25`
confirms that Phase 8b's FULL parity against the saved Phase-8 rows, including the gaze field,
remains exact.

| gate | wall | accepted reference | accepted total | excluded | fresh = accepted scope | result | scope manifest sha256 |
|---|---|---|---|---|---|---|---|
| Phase-6 proposer | 2.87 s | `partition-graph-6-proposals` | 102 | — | 102 | byte-identical | `30e88f61da7ef1d43bc9bb530418f2d03c1403347b26f22a0d9a1c211309bbad` |
| Phase-6 evaluator | 1.41 s | `partition-graph-6-evaluation` | 59 | `demo/` 28, `demo-package-original/` 28 | 3 | byte-identical | `b584139a0186e014627452c74c811ed7b5281f3351255ae2596340ef6ae96fff` |
| Phase-7 proposer | 47.10 s | `partition-graph-7-proposals` | 835 | — | 835 | byte-identical | `3dde52e4cd34228f91c240db3682dc489d9f1adb74a5e85a7021b58bff1673de` |
| Phase-7 evaluator | 19.34 s | `partition-graph-7-evaluation` | 321 | `demo/` 107, `demo-package-original/` 107 | 107 | byte-identical | `05d35ef37a6294c0b0da08a1f943d7c9c8daef93c22819adb9beb8bdb3da0515` |
| **Phase-8 proposer** (instrumented) | 657.59 s | `partition-graph-8-proposals` | 468 | — | 468 | **byte-identical** | `69ccbfb748f250e19baebb75789e57c66f4c26443286e43a9a85ca77f474a209` |
| Phase-8 evaluator | 125.28 s | `partition-graph-8-evaluation` | 321 | `demo/` 107, `demo-package-original/` 107 | 107 | byte-identical | `01c8d253f5ea8698e8df290b7090f299d2fb462c6c40a0fdb04bdc7611525f7d` |
| Phase-8b proposer | 61.53 s | `partition-graph-8b-proposals` | 503 | — | 503 | byte-identical | `51a93fc464fc8ce00fc7f519ccadc25f539095be06de074788844b12ad6e7b7d` |
| Phase-8b evaluator | 16.61 s | `partition-graph-8b-evaluation` | 19 | `demo/` 8, `demo-package-original/` 8 | 3 | byte-identical | `243133b66237523147e1a869ee5b1bf97ee28ec9d817c5c059921e9b254c5715` |

Each comparison was two-sided:
- set equality after only the established exclusions, with no fresh file beneath an excluded
  path;
- `filecmp` with `shallow=False` on every pair;
- equal `LC_ALL=C` manifests.

`only_fresh`, `only_accepted`, `fresh_under_excluded` and `byte_diff` were 0 everywhere.

## Instrumentation

The wrappers delegated to the real objects at every stage:
- the intrinsic build and the gaze annotation (the `gaze_context` bindings);
- the gaze-context wrapper and the status annotation (the `run_context` bindings);
- the run-context wrapper and the candidate annotation (the `candidate_policy` bindings);
- the candidate wrapper (the four producer bindings);
- the `benchmark` alias.

The Phase-8 count comes from its required replay. The others come from separate scratch runs,
whose outputs were also byte-identical.

| run | intrinsic | gaze annot. | gaze-context | status annot. | run-context | candidate annot. | candidate wrapper (binding) | alias |
|---|---|---|---|---|---|---|---|---|
| Phase-6 proposer | **25** | 25 | 25 | 25 | 25 | 25 | 25 (`benchmark`) | 0 |
| Phase-7 proposer | **208** | 208 | 208 | 208 | 208 | 208 | 208 (`prefix_benchmark`) | 0 |
| Phase-8 proposer | **208** | 208 | 208 | 208 | 208 | 208 | 208 (`integration`) | 0 |
| Phase-8b proposer | **125** | 125 | 125 | 125 | 125 | 125 | 125 (`challenge_suite`) | 0 |
| Phase-6, 7, 8 and 8b evaluators | **0** | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

The composition is one-to-one at all seven stages, and the counts equal the Core-13 counts.

**Descriptive gaze measurements** (not acceptance criteria):

| producer | gaze entries supplied | partitions with 0 / 1 / ≥2 gazes | rows with `None` / finite gaze distance |
|---|---|---|---|
| Phase 6 | 104 | 0 / 11 / 14 | 0 / 3452 |
| Phase 7 | 1182 | 0 / 50 / 158 | 0 / 69228 |
| Phase 8 | 1182 | 0 / 50 / 158 | 0 / 104134 |
| Phase 8b | 304 | 0 / 69 / 56 | 0 / 54473 |

- **Phase 6** reconciles exactly with the accepted products:
  - the 25 targets' saved `fixation_count` values in `partition-graph-6-proposals/summary.json`
    sum to 104, with 11 one-fixation and 14 multi-fixation targets;
  - all 3,452 saved `regions.json` rows carry a finite gaze distance.
- **Phases 7 and 8** supply identical gaze lists: both use the current-target prefix
  `trajectory[:local_step + 1]`, for two partitions per state.
- **No accepted Classroom partition has an empty gaze history,** so the `None` branch is
  exercised only by the fixtures and the differential (98,229 `None` rows).

## Gate A

Gate A was run at `cea5234` and again at `02e1d11`, with identical results:

| step | result |
|---|---|
| compile (changed Python) | ok |
| conceptual checkers | Core-14 64/0; Core-10 29/0, Core-9 24/0, Core-8 20/0, Core-7 22/0, Core-6 35/0, Core-5 38/0, Core-4 32/0, Core-3 27/0, Core-2 20/0, Core-1 13/0 (unmodified) |
| accepted Core-13 checker at `3b7091e` (read-only detached worktree, 0 tracked changes) | 65/0 |
| Partition-Graph checkers (unmodified) | 1: 13/0, 2: 16/0, 3: 20/0, 4: 14/0, 5: 12/0, 6: 12/0, 7: 12/0, 8: 10/0, 8b: 12/0 |
| facade | 16/0 |
| `scripts/verify_baseline.sh` | `[verify] SUMMARY passed=9 failed=0` (31/31) |
| `scripts/compare_golden.sh previews/partition-graph-2-source-full` | `[compare-golden] MISMATCHES 0` (9.93 s; 9.93 s) |
| `git diff --check` (worktree, and `fe18767..HEAD`) | clean |
| fresh footprints | as tabulated above |

## Accepted-tree integrity

Full per-file sha256 manifests of the 13 accepted trees were taken under the guard at
`cea5234`, before the first replay and after the last replay and instrumentation. They are
**identical**, and also identical to Core 13's final snapshot. The per-tree values are those
recorded in `docs/migration-conceptual-core-12-report.md`.

## Changed-path → executed-gate coverage

| changed path | kind | exercised by | execution evidence |
|---|---|---|---|
| `fov3d/epistemic/partition.py` (six lines removed) | intrinsic redesign | A/B/C/K checker; the 10,000-state differential; Phases 6–8b | 25 / 208 / 208 / 125 intrinsic builds; byte-identical |
| `gaze_context.py` (new) | historical action context | C/D/E/H/I/J/K checker; the differential; Phases 6–8b | gaze annotations and wrapper calls one-to-one; the Phase-6 gaze entries and rows reconcile with the saved products; byte-identical |
| `run_context.py` (import and call) | composition | F/G/J checker; unmodified Partition-Graph checkers 6/7/8 (through the alias); Phases 6–8b | status annotations and run-context calls one-to-one; byte-identical |
| `candidate_policy.py`, the four producers, `incidental.py`, `fov3d/epistemic/__init__.py` | **unchanged** | G/H/J | byte equality with Core 13; footprints |
| `tools/dev/check_conceptual_core14.py` | new checker | Gate A; mutation harnesses | 64/64; 48/48 dynamic and 22/22 static mutants caught |

## Repairs and deviations

1. **No production repair was needed.** No gate failed against the implementation, and no
   producer or policy module needed a change.
2. **Checker fixes before commit.** The live-control tolerance was aligned with Core 11's
   1e-5 gaze tolerance, and three crash-only catches were made named FAILs. No check was
   weakened, and the suites were re-run on the final checker.
3. **Replay/instrumentation arrangement** (as the contract allows): the Phase-8 required replay
   was run **once**, instrumented; the other seven used the plain commands plus scratch
   instrumentation.
4. **`_insert_after` now exists in three private copies**, in `candidate_policy` (Core 12),
   `run_context` (Core 13) and `gaze_context` (Core 14). Each context layer then depends only
   on the layer below it. A shared helper would be a separate small ownership question, which
   is not addressed here.

No other deviation.

## Controller-readiness boundary

This section is a **read-only** analysis of the live code after Core 14. No production code
was changed for it, and **no controller is implemented**.

### A. Intrinsic information available to a future controller

`fov3d.epistemic.partition.build_epistemic_partition(state, *, target_id, target_name,
domain, grid_deg)` returns four things, measured from the live code.

**Per-region rows**, in this key order:
- `region_code`, `region_id`, `kind`, `instance_id`;
- `cell_count`, `touches_domain_edge`, `centroid_yaw_deg`, `centroid_pitch_deg`;
- `min_distance_to_target_deg`, `median_distance_to_target_deg`;
- `seen_any_fraction`, `head_depth_fraction`, `mapped_cells`, `incidental_cells`;
- (`OTHER_SURFACE`) `surface_source`;
- `adjacent_regions`, `adjacent_to_target_support`.

**`arrays`**: `class_code`, `region_code`, `surface_instance`, `target_support`, `depth_seen`,
`seen_any`, `mapped_other`, `incidental_other`, `ambiguous_boundary`.

**`edges`**: `region_code_a`, `region_code_b`, `interface_edge_count`.

**`diag`**: `target_id`, `target_name`, `chart_shape_hw`, `region_count`,
`kind_region_counts`, `kind_cell_counts`, `target_evidence_unmapped_cells`,
`ambiguous_boundary_cells`, `head_depth_cells`, `eye_ray_seen_cells`, `truth_used`.

In controller terms that is:
- the epistemic kind: target support, other surface, unknown, ambiguous boundary, unmapped
  target evidence;
- region geometry: cell count, domain-edge contact, centroid;
- target-distance descriptors (min and median);
- topology: interfaces, adjacency, adjacency to target support;
- instance identity;
- evidence history: `seen_any_fraction`, `head_depth_fraction`, mapped/incidental cell
  counts, `surface_source`.

**Observation for controller design (not changed here).** The intrinsic partition is still
**target-relative**. It takes a designated `target_id` and `target_support`. Two kinds
(`TARGET_SUPPORT`, `TARGET_EVIDENCE_UNMAPPED`) and the target-distance descriptors are defined
relative to that target, and the historical producers build one per-target state for
each call (for example the per-target Phase-5 states in Phase 6). A controller reasoning over several objects at once would call it per target or
need a target-neutral formulation. This connects to the deferred target-relative
`HeadEvidence` placement.

### B. Separated historical/contextual layers

| layer | module | extra input | adds | semantics |
|---|---|---|---|---|
| gaze context | `classroom_partition.gaze_context` | `gazes_deg`, the producer's target-local gaze list | `min_distance_to_historical_gaze_deg` | historical, target-local fixation-distance descriptor |
| run context | `classroom_partition.run_context` | `all_target_ids`, the prerecorded target schedule | `reconstruction_status` | historical experiment schedule |
| candidate policy | `classroom_partition.candidate_policy` | none (`CANDIDATE_KINDS`) | `candidate`, `candidate_region_count` | historical `OTHER_SURFACE`/`UNKNOWN` → candidate rule |
| Phase 8b | `classroom_partition.challenge_suite` | refined regions, UNKNOWN shells | `candidate_raw`, `eligible_candidate` | an independent, second candidate interpretation (`MIN_ELIGIBLE_CELLS` 25) |

Each layer is optional and composes on the one below; none feeds back into the intrinsic
partition.

### C. Explicitly not yet implemented

- general controller candidate eligibility;
- scoring or ranking;
- fixation choice;
- vergence/focus choice;
- inhibition of return;
- a recency model;
- the design of global versus target-local gaze memory;
- continuation/stopping integration;
- the budget/quality trade-off;
- a moving head;
- semantic decisions.

The historical pipeline still declares `gaze_policy_defined: False` and, in Phase 8b,
`candidate_ranking_defined: False`.

### D. Architectural consequence

After Core 14 the intrinsic partition is independent of:

    the experiment's future target schedule     (Core 13)
    the candidate interpretation                (Core 12)
    the fixation / action history               (Core 14)

It depends only on accumulated evidence and the chart. It therefore gives a clean basis on
which to design the integrated foveal controller:

    intrinsic epistemic representation
        → optional gaze/action context
        → optional experiment run context
        → candidate interpretation
        → future attention/controller policy

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

No Core 15 migration in this run.

## Unresolved decisions (for Luiz and Chat)

- Whether to accept Core 14 and fast-forward `main` to the final head of this branch.
- If it is accepted, the scope of the fresh integrated foveal-controller design. The
  controller-readiness boundary above, including the target-relative observation, is offered
  as input, and no automatic Core-15 cleanup is proposed.

## Acceptance

| criterion | status |
|---|---|
| intrinsic builder no longer accepts `gazes_deg` | MEASURED pass |
| intrinsic rows no longer contain `min_distance_to_historical_gaze_deg`; output = Core 13 minus **only** that field | MEASURED pass (fixtures, 300 + 10,000 random states) |
| all evidence-history fields unchanged; `_angular_distance_deg` unchanged | MEASURED pass |
| `gaze_context` / `run_context` / `candidate_policy` reconstruct the Core-13 intrinsic, run-context and historical outputs exactly | MEASURED pass |
| target-local gaze provenance unchanged; producers unchanged | MEASURED pass (byte identity and structural provenance) |
| Phase-8b base and refined behavior exact | MEASURED pass |
| no experiment or action-history dependency in `epistemic.partition` | MEASURED pass |
| Core-14 checker fail-capable; random differential clean | MEASURED pass (48/48 + 22/22; 10,000/10,000) |
| Core-1 to Core-10 checkers pass at the current head | MEASURED pass |
| accepted Core-13 checker passes at `3b7091e` | MEASURED pass (65/65) |
| all Partition-Graph checkers pass unmodified | MEASURED pass (1–8b) |
| baseline 31/31; golden `MISMATCHES 0` | MEASURED pass |
| every reached Phase-6/7/8/8b product byte-identical | MEASURED pass (8/8) |
| 13 accepted reference trees unchanged | MEASURED pass |
| every changed production path maps to an executed gate | MEASURED pass |

    CONCEPTUAL_CORE14_GAZE_CONTEXT_SEPARATION_PRESERVES_BEHAVIOR
