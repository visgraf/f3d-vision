# Migration Conceptual Core 12 — report

**Result.**

    CONCEPTUAL_CORE12_CANDIDATE_POLICY_SEPARATION_PRESERVES_BEHAVIOR

This result is MEASURED and awaits review by Luiz and Chat. Core 12 is **not** merged into
`main`.

**Causal question.** Can candidate status be removed from the intrinsic epistemic partition
and expressed instead as a separate historical candidate interpretation, while reproducing
every accepted Phase-6/7/8/8b observable product exactly?

**Answer (measured): yes.**

    accepted Core-11 partition = pure epistemic partition + historical candidate annotation

The evidence:
- **The pure partition.** `fov3d.epistemic.partition` no longer owns `CANDIDATE_KINDS`,
  `region["candidate"]` or `diag["candidate_region_count"]`. Its source is accepted Core 11
  minus exactly three lines, the docstring aside.
- **The candidate policy.** The new experiment-side
  `fov3d/experiments/classroom_partition/candidate_policy.py` re-creates the accepted Core-11
  view type-, value- and key-order-strictly.
- **The central invariant against accepted Core 11 (`d324e09`)** holds:
  - on every deterministic fixture;
  - on 300 seeded states inside the checker;
  - on 10,000 random states (396,011 region rows) outside it.
- **The checker.** The Core-12 checker passes 70/70. It caught all 51 non-equivalent dynamic
  mutants and all 25 static mutants.
- **Existing checkers.** The accepted Core-11 checker passes 59/59 at `d324e09`. The Core-1
  to Core-10 checkers and the Partition-Graph checkers 1–8b pass **unmodified** at the
  current head.
- **Replays.** All 8 reached Phase-6/7/8/8b proposer/evaluator products are **byte-identical**.
- **Accepted trees, baseline and golden.** The 13 accepted trees are unchanged, the baseline
  is 31/31, and golden reports `MISMATCHES 0`.

## Why this is a redesign Core

Cores 1–11 moved accepted behavior into conceptual owners without changing any structure
except ownership. Core 12 is the **first intentional redesign**. It changes one concept, the
representation/policy boundary: a region's epistemic `kind` is intrinsic, but calling it a
*candidate* is an interpretation.

The accepted system itself already shows this. Phase 8b computes a different candidate
interpretation over the same epistemic structure: `candidate_raw` and `eligible_candidate`
over refined regions and UNKNOWN shells. Core 12 makes the historical Phase-6/7/8
interpretation equally explicit, while reproducing every observable product exactly.

## Provenance: Core-11 acceptance administration and branch

| step | result |
|---|---|
| pre-check (fetch) | `origin/main = a312959ae9a07afca65d0c4781846517d1645344` and `origin/migration/conceptual-core-11 = d324e098c859a3b7ea1e91c7526f5cda854bcaf7`, both verified. `d324e09` descends from `a312959`; Core 11 is 6 ahead and 0 behind. `CLAUDE.md` is unchanged. The shared checkout was untouched |
| **Core 11 accepted** (Luiz) | `origin/main` fast-forwarded `a312959..d324e09` by a plain, non-forced push of the exact commit |
| handoff | in a detached administrative worktree at `d324e09`, only `docs/chat-handoff.md` was changed: commit `9eb9d9936cd2198fe63b7b9f076455f2114da70d` (parent `d324e09`), pushed as a fast-forward to `main`. The administrative worktree was then removed |
| branch | `migration/conceptual-core-12` created at `9eb9d99` from the **new** `origin/main`, both remote and local. The local upstream was set to the Core-12 remote branch, not `main` |
| Core-12 commits | `cf0e3f8` contract, **committed before any production change** · `ce6dc43` production change · `06b9645` checker · `388731a` conceptual map · the commit that adds this report |
| gates measured at | the mechanical audit at `ce6dc43`; the checker mutation tests and the 10,000-state differential before `06b9645`; Gate A, the import audit, the replays, the instrumentation and both accepted-tree snapshots at `06b9645`; Gate A again at `388731a`. `fov3d/` and `tools/` are identical at `06b9645` and `388731a` |

The handoff records:
- Core 11 accepted at `d324e09`;
- `fov3d.epistemic.partition` ownership;
- the Core-11 evidence;
- the retained candidate, run-status and historical-gaze annotations;
- Core 12 as the first redesign step (epistemic partition ≠ candidate interpretation);
- the working arrangement.

## Isolated worktrees and guard

- **Where it ran.** Every Core-12 edit and measurement ran in the dedicated worktree
  `<scratchpad>/core12/wt` on `migration/conceptual-core-12`.
- **Data links.** `previews/`, `.venv/` and the ignored `scenes/classroom/` entries are
  symlinked in.
- **Guard.** It requires, before and after every measurement, branch
  `migration/conceptual-core-12`, the expected HEAD and a clean tracked tree. It never
  tripped.
- **Core-11 reference.** The accepted Core-11 checker was verified in a separate read-only
  **detached** worktree at `d324e09` (`<scratchpad>/core12/ref11wt`), which had 0 tracked
  changes.
- **Shared checkout.** `/home/lvelho/rd/f3d-vision` was not mutated and its branch was not
  switched. It stays on local `main` at `e681392`.

## The exact pure/policy boundary

**Removed from `fov3d/epistemic/partition.py`** (the complete non-docstring diff against
Core 11, as measured):

```text
- CANDIDATE_KINDS = {"OTHER_SURFACE", "UNKNOWN"}
-                 "candidate": bool(kind in CANDIDATE_KINDS),
-         "candidate_region_count": sum(bool(r["candidate"]) for r in region_rows),
```

The module docstring now describes the pure representation.

Unchanged:
- `REGION_KIND` and `REGION_KIND_BY_CODE`;
- the six helpers;
- the imports;
- the `build_epistemic_partition` signature;
- every other builder semantic.

That includes:
- precedence and `surface_instance`;
- connectivity, region order and codes;
- interfaces and adjacency;
- the distances and the gaze descriptor;
- `reconstruction_status` and `surface_source`;
- `arrays` and all other diag fields.

`fov3d/epistemic/__init__.py` is unchanged.

**New `fov3d/experiments/classroom_partition/candidate_policy.py`** (79 lines):

    CANDIDATE_KINDS = {"OTHER_SURFACE", "UNKNOWN"}
    annotate_candidate_partition(region_rows, diag) -> (region_rows, diag)
    build_candidate_partition(state, *, target_id, target_name, all_target_ids,
                              domain, grid_deg, gazes_deg) -> (arrays, region_rows, edge_rows, diag)

- **`annotate_candidate_partition`** is non-mutating. It returns new dicts with
  `"candidate": bool(kind in CANDIDATE_KINDS)` immediately after `"kind"`, and
  `"candidate_region_count"` (a Python `int`) immediately after `"region_count"`. These are
  the accepted Core-11 positions.
- **`_insert_after`**, the private helper, raises `ValueError` on double annotation and
  `KeyError` on a missing anchor.
- **`build_candidate_partition`** has the accepted builder signature. It calls the pure
  builder once, annotates the rows and diag, and passes `arrays` and `edges` through as the
  same objects. It defines no ranking, score, gaze or continuation rule.

The module is deliberately experiment-side. No `fov3d.attention` package was created.

## Changed files (main 9eb9d99...final head)

| file | change |
|---|---|
| `docs/migration-conceptual-core-12.md` | contract (`cf0e3f8`) |
| `fov3d/epistemic/partition.py` | the three candidate lines removed; module docstring (`ce6dc43`) |
| `fov3d/experiments/classroom_partition/candidate_policy.py` | **new** historical candidate interpretation (`ce6dc43`) |
| `.../benchmark.py` | `CANDIDATE_KINDS` and `build_epistemic_partition` leave the partition import. `from ...candidate_policy import CANDIDATE_KINDS, build_candidate_partition` is added. The alias `build_epistemic_partition = build_candidate_partition` is added after `_grid = chart_grid`. `propose_phase6` calls `build_candidate_partition` (`ce6dc43`) |
| `.../prefix_benchmark.py` | `from fov3d.epistemic.partition import REGION_KIND, REGION_KIND_BY_CODE`, and `build_candidate_partition` from the policy. The measured-orphan `CANDIDATE_KINDS` import is removed. One call site is renamed (`ce6dc43`) |
| `.../integration.py` | `build_candidate_partition` from the policy; both call sites renamed (`ce6dc43`) |
| `.../challenge_suite.py` | `REGION_KIND` and `_region_interfaces` from the partition, and `build_candidate_partition` from the policy. The base-partition call site is renamed. The Phase-8b candidate logic is untouched (`ce6dc43`) |
| `tools/dev/check_conceptual_core12.py` | new checker, 70 checks (`06b9645`) |
| `docs/conceptual-core-map.md` | Cores 1–11 accepted, Core 12 proposed (measured); a new `candidate_policy.py` row; the consumer rows; a Core-12 section; the next question (`388731a`) |
| `docs/migration-conceptual-core-12-report.md` | this report |

No historical checker or tool was modified.

## Central projection / reconstitution invariant

For a valid state, the three outputs compared are:
- `OLD` = the accepted Core-11 `build_epistemic_partition`;
- `PURE` = the Core-12 `fov3d.epistemic.partition.build_epistemic_partition`;
- `REANNOTATED` = `annotate_candidate_partition` applied to `PURE`.

The invariant has five parts:
1. `PURE` arrays equal `OLD` arrays exactly;
2. `PURE` edges equal `OLD` edges exactly;
3. `PURE` rows equal `OLD` rows minus only `"candidate"` (order, remaining key order,
   values and types);
4. `PURE` diag equals `OLD` diag minus only `"candidate_region_count"`;
5. `REANNOTATED == OLD`, type- and key-order-strictly, and
   `build_candidate_partition == OLD` as well.

**Reference mechanism.** Both the checker and the differential execute
`git show d324e09:fov3d/epistemic/partition.py` as an isolated reference module. The
comparison is structural:
- exact Python types;
- dict key order;
- NumPy dtype, shape and values;
- floats compared exactly, since the same code path is used, except against the
  hand-derived expectations, which carry tolerances.

**Measured results:**

| scope | result |
|---|---|
| deterministic fixtures H1 (4×6, all 5 kinds, all 3 `reconstruction_status` and `surface_source` values), H2 (2×6, per-kind 4/8 connectivity), H3 (target-free, no gazes), malformed shape | every invariant holds, and the ValueError is identical |
| seeded in-checker differential | 300/300 states |
| out-of-checker differential (`default_rng(20260928)`) | **10,000/10,000** states, 396,011 region rows. Sizes 1–14 × 1–16, grid 0.1–4°, 8 instance ids up to 70000, varying owner/nearest/ambiguity/depth/seen densities, `all_target_ids`, domain offsets and 0–5 gazes. All five kinds, all three statuses and all three surface sources occurred |

The out-of-checker run included seven non-equivalent controls, each of which differed from
Core 11 on the listed number of states:

| control | states that differed |
|---|---|
| candidate at the end | 10000 |
| UNKNOWN removed from the kinds | 9278 |
| count off by one | 10000 |
| rows reordered | 9924 |
| `targeted_later` inverted | 9248 |
| gaze max instead of min | 6678 |
| UNKNOWN 8-connected | 6063 |

The claimed-equivalent mutant differed on 0 states.

## Historical-checker supersession

The accepted `tools/dev/check_conceptual_core11.py` asserts the old structure: that
`CANDIDATE_KINDS` lives in `epistemic.partition`, that the intrinsic builder emits
`candidate`, and that `benchmark.build_epistemic_partition` is the conceptual builder. Core 12
intentionally changes all three facts. Following the contract:

- **A.** The Core-11 checker is **unmodified**. At `d324e09`, in the read-only reference
  worktree, it reports `[conceptual-core11-check] SUMMARY checked=59 failed=0`. This was
  measured in both Gate A runs.
- **B.** At the Core-12 head it is **not** a pass gate. For the record, it stops at import
  (rc 1) with
  `ImportError: cannot import name 'CANDIDATE_KINDS' from 'fov3d.epistemic.partition'`,
  which is exactly the intended structural change.
- **C.** The Core-12 checker subsumes every still-relevant Core-11 behavioral guarantee:
  - all helper known answers;
  - the hand-derived H1/H2/H3 expectations, now asserted on the pure output and on the
    candidate view;
  - the malformed-shape error;
  - package footprints and import boundaries.

  It adds the representation/policy tests.
- **D.** The Core-1 to Core-10 conceptual checkers pass unmodified at the current head.
- **E.** The Partition-Graph checkers 1–8b pass **unmodified**. Checkers 6, 7 and 8 assert
  candidate flags through `benchmark.build_epistemic_partition`, which is now the candidate
  wrapper.

This is an explicit architectural-checker supersession, not a regression.

## The Core-12 checker

`tools/dev/check_conceptual_core12.py` (807 lines) runs host-side and deterministically in
2.06 s (measured on the final checker). It prints `[conceptual-core12-check] SUMMARY checked=70 failed=0` and exits nonzero on
any failure.

| section | checks | what is witnessed |
|---|---|---|
| reference | 1 | the accepted Core-11 partition executes from `git show d324e09` |
| **A** pure structure | 10 | Pure-module structure:<br>• `REGION_KIND`/`REGION_KIND_BY_CODE` source and values;<br>• `CANDIDATE_KINDS` absent (defined, imported, referenced);<br>• the six helpers source/AST-identical;<br>• the builder signature identical;<br>• the builder **source is Core 11 minus exactly the two candidate lines**, and its **AST is Core 11 minus exactly the two dict entries**;<br>• no operational `"candidate"`/`"candidate_region_count"` constant outside docstrings;<br>• exactly the Core-11 names minus `CANDIDATE_KINDS`, in order;<br>• the import statements identical, with no experiment or policy import (full AST walk);<br>• the global bindings equivalent (only `CANDIDATE_KINDS`/`sum`/`bool` may drop) |
| **B** pure behavior | 25 | • the helper known answers (subsumed from Core 11);<br>• fixture coverage (all kinds, sources, statuses, edge flags, connectivity, target-free and no-gaze cases);<br>• per fixture, arrays + edges, rows and diag each **equal to `project(OLD)`**;<br>• the malformed shape;<br>• the hand-derived H1 rasters, complete pure rows, edge rows and pure diag;<br>• the H2 connectivity;<br>• the H3 target-free/no-gaze case |
| **C** candidate rule | 7 | • `CANDIDATE_KINDS` is exactly the set;<br>• per-kind flags, each kind alone, with Python bool/int types;<br>• rows retained, `candidate` right after `kind`, and every other value the same object;<br>• the count (int) right after `region_count`;<br>• no input mutation and new dicts returned;<br>• double annotation and missing anchors fail;<br>• an empty partition gives count 0 |
| **D** reconstitution | 7 | • per fixture, `build_candidate_partition == OLD`;<br>• `annotate(PURE) == OLD`;<br>• one pure call, with `arrays`/`edges` passed through as the same objects (spy);<br>• the signature;<br>• the hand-derived candidate view |
| **E** benchmark compatibility | 5 | • `benchmark.CANDIDATE_KINDS is candidate_policy.CANDIDATE_KINDS`;<br>• `benchmark.build_epistemic_partition is build_candidate_partition`, and it returns the Core-11 view;<br>• the eight representation identities;<br>• no duplicate (the alias is the only binding);<br>• `propose_phase6` resolves and calls the wrapper |
| **F** wiring and Phase 8b | 6 | • the four modules import exactly the declared names and call the wrapper at 1/1/2/1 sites, never the pure builder;<br>• they equal Core 11 in **source text and AST** apart from the declared import, alias and call-name changes;<br>• among production modules only `candidate_policy` imports the pure builder;<br>• Phase-8b `_component_rows` is AST-identical to Core 11, with its own literal, and never names `CANDIDATE_KINDS` or a row `candidate`;<br>• the Phase-8b `candidate_raw`/`eligible_candidate` known answers (`MIN_ELIGIBLE_CELLS` 25);<br>• **independence with a live control**: the Phase-8b rows are unchanged while `candidate_policy.CANDIDATE_KINDS` is temporarily emptied, and the wrapper's flags do change |
| **G** footprints | 6 | • `__init__` unchanged;<br>• the fresh bare `fov3d.epistemic`, fresh `epistemic.partition` and fresh `candidate_policy` exact module lists;<br>• the policy's own imports;<br>• no import cycle |
| **H** random differential | 3 | • 300 seeded states, all invariants;<br>• coverage of kinds and statuses;<br>• three non-equivalent controls (position, narrowed kinds, count) detected |

### Mutation evidence (before the checker was committed)

**Dynamic mutants.** Substitutions with asserted counts were applied to `partition.py` and/or
`candidate_policy.py`. Both were loaded as the real modules before the checker, and hence
before `benchmark` and the consumers.

| class | non-equivalent caught / total | examples |
|---|---|---|
| 1 pure/policy boundary (runtime) | 3 / 3 | pure emits `candidate`; `CANDIDATE_KINDS` retained; `candidate_region_count` retained |
| 2 candidate rule | 10 / 10 | UNKNOWN or OTHER_SURFACE removed; TARGET_SUPPORT, AMBIGUOUS_BOUNDARY or TARGET_EVIDENCE_UNMAPPED added; flag inverted; int flag; frozenset; lower-case kinds; constant `True` |
| 3 reconstitution | 19 / 19 | candidate at the end or before `kind`; count at the wrong position or the end; `len(rows)`; +1; float; row filtered; rows reversed; another row field; a diag field; in-place append; double-annotation or missing-anchor guard removed; arrays dtype changed; arrays copied; edges reversed or truncated; annotation skipped |
| 4 pure regression | 19 / 19 | precedence; UNKNOWN 8-connected; mapped owner; median→mean; mask 3; no interface accumulation; asymmetric adjacency; region order; `targeted_later` inverted; gaze max; centroid x/y; edge row; no clip; seen/depth; `truth_used`; `region_count`; unsorted kind counts; vocabulary code; always-8 labels |
| **total** | **51 / 51** (0 survived) | |

**Static mutants: 25/25 caught**, on throw-away `git ls-files | tar` copies; the unmutated
copy passes 70/0.
- **Class 1, import boundary (6):**
  - the pure module importing `candidate_policy` lazily, or an experiment module at top level
    or lazily in a helper;
  - the `CANDIDATE_KINDS` source restored;
  - an eager `__init__` import;
  - the policy importing `benchmark`.
- **Class 5, wiring (11):**
  - `benchmark` using the pure builder, or calling the alias name;
  - `prefix_benchmark`, `integration` or `challenge_suite` using the pure builder;
  - the alias removed;
  - a duplicate builder, or a duplicate `CANDIDATE_KINDS`, in `benchmark`;
  - the prefix orphan restored;
  - a representation name taken through `benchmark`;
  - a consumer non-import edit.
- **Class 6, Phase-8b separation (4):**
  - the literal replaced by `CANDIDATE_KINDS`;
  - `candidate_raw` coupled to the row `candidate`;
  - `eligible_candidate` routed through `candidate_policy`;
  - `MIN_ELIGIBLE_CELLS` changed.
- **Pure-module drift (4):** a helper comment; an extra builder statement; an extra helper; an
  extra import.

**Expected-pass control.** Prose mentioning "candidate" in the pure module's docstring passes
70/0, so the construction scan is not over-broad.

**Claimed-equivalent (recorded separately): `r_flag_without_bool`.** It removes the `bool()`
around the membership test, which is already a Python `bool`. It survived the checker, as
expected, and differed on 0 of 10,000 differential states.

**Checker defects fixed before commit** (no check was weakened):
1. **A crash.** `k_annotation_skipped` was first caught only by an uncaught `KeyError` in the
   F control. The lookups were made non-raising, so it now fails as 7 named checks.
2. **Comment drift.** `consumer_non_import_edit` initially **survived**, because the F
   comparison normalized ASTs, which ignore comments. A source-text comparison under the same
   declared renaming was **added**, and it is now caught.

The full dynamic and static suites were re-run on the final checker.

## Compatibility API and direct-consumer wiring (measured)

- **`benchmark`:**
  - `benchmark.CANDIDATE_KINDS is candidate_policy.CANDIDATE_KINDS`;
  - `benchmark.build_epistemic_partition is candidate_policy.build_candidate_partition`,
    returning the exact Core-11 view;
  - `REGION_KIND`, `REGION_KIND_BY_CODE` and the six helpers are the `epistemic.partition`
    objects;
  - no duplicate implementation.
- **Consumers:**
  - `propose_phase6`, `propose_phase7`, `propose_phase8` (2 sites) and `propose_phase8b`
    call `build_candidate_partition`;
  - none of the four modules calls the pure builder;
  - `candidate_policy` is the only production importer of the pure builder.
- **Orphans.** Measured: `prefix_benchmark`'s `CANDIDATE_KINDS` import was unused, and
  nothing imported it through `prefix_benchmark`. Only that import was removed.
  `REGION_KIND`, `REGION_KIND_BY_CODE` and `defaultdict` (unused in `prefix_benchmark`), and
  `AREA_BINS` and `defaultdict` (unused in `integration`), are pre-existing and were kept.
- **Phase 8b.**
  - The base integrated partition uses the candidate view, because its FULL parity check
    compares against the saved Phase-8 `regions.json`, which includes `candidate`.
  - Its own interpretation is unchanged: `candidate_raw = kind in {"UNKNOWN", "OTHER_SURFACE"}`,
    and `eligible_candidate = candidate_raw and cells >= MIN_ELIGIBLE_CELLS`, over refined
    regions and UNKNOWN shells.
  - It is independent of `candidate_policy`: this was checked structurally, and behaviorally
    with a live control.

## Package footprints (fresh processes, Gate A)

| module | `fov3d` modules | `cv2` | `epistemic.partition` | `candidate_policy` | `benchmark` |
|---|---|---|---|---|---|
| `fov3d.epistemic` | 2 (`fov3d`, `fov3d.epistemic`) | no | no | no | no |
| `fov3d.epistemic.partition` | 5 (unchanged from Core 11) | yes | — | no | no |
| `candidate_policy` | 14 | yes | yes | — | no |
| `benchmark` | 15 | yes | yes | yes | — |
| `prefix_benchmark` | 18 | yes | yes | yes | yes |
| `integration` | 20 | yes | yes | yes | yes |
| `challenge_suite` | 24 | yes | yes | yes | yes |

- **`candidate_policy`.** Its 14 modules are the measured experiment-package footprint (11,
  via the package `__init__` → `lift`) plus `fov3d.epistemic`, `fov3d.epistemic.partition`
  and `candidate_policy`. There is no benchmark, evaluator, dense-truth, stereo, rendering
  or `bpy` module.
- **Deltas against Core 11** (the mechanical audit against a `git archive` of `d324e09`):
  - each of `benchmark`, `prefix_benchmark`, `integration` and `challenge_suite` gains
    exactly `candidate_policy`;
  - `fov3d.epistemic` and `fov3d.epistemic.partition` are unchanged.
- **No import cycle** (both orders).

## Import/dependency audit and replay decisions

A fresh audit ran at `06b9645` under the guard, with `sys.modules` recorded after loading
each entry script without running `main`:

| entry point | `epistemic.partition` | `candidate_policy` | `benchmark` | also | decision |
|---|---|---|---|---|---|
| Phase-6 proposer / evaluator | **yes** | **yes** | **yes** | — | replayed |
| Phase-7 proposer / evaluator | **yes** | **yes** | **yes** | `prefix_benchmark` | replayed |
| Phase-8 proposer / evaluator | **yes** | **yes** | **yes** | `prefix_benchmark`, `integration` | replayed |
| Phase-8b proposer / evaluator | **yes** | **yes** | **yes** | `challenge_suite` | replayed |
| Phase-2 lift, Phase-3 lift, Phase-4 analyzer, Phase-5 analyzer, (info) `partition_graph4_lift.py` | no | no | no | — | **not run** |

- **AST importers of the three modules:**
  - the four historical modules;
  - `candidate_policy` (pure only);
  - checkers 11 and 12, and the nested import in `check_conceptual_core2.py` L145;
  - Partition-Graph checkers 6, 7, 8 and 8b;
  - the Phase-6 tools;
  - demos 6, 7 and 8b.
- **Dynamic-import sites.** They are unchanged, plus the Core-12 checker's own
  `importlib.import_module` of the consumers.

## Replays: commands, COMPLETE lines and byte comparisons

The replays ran from the worktree root under the guard at `06b9645`, each to a fresh
`previews/conceptual-core-12-*` directory, with the established Core-11 commands and inputs.

Seven gates used the plain command:

```text
.venv/bin/python tools/partition_graph6_propose.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/partition-graph-5-full previews/conceptual-core-12-phase6-proposals
.venv/bin/python tools/partition_graph6_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-6-proposals previews/conceptual-core-12-phase6-evaluation
.venv/bin/python tools/partition_graph7_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-6-proposals previews/conceptual-core-12-phase7-proposals
.venv/bin/python tools/partition_graph7_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-7-proposals previews/partition-graph-6-evaluation previews/conceptual-core-12-phase7-evaluation
.venv/bin/python tools/partition_graph8_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8-proposals previews/partition-graph-7-evaluation previews/conceptual-core-12-phase8-evaluation
.venv/bin/python tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals previews/conceptual-core-12-phase8b-proposals
.venv/bin/python tools/partition_graph8b_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8b-proposals previews/partition-graph-8-evaluation previews/conceptual-core-12-phase8b-evaluation
```

The Phase-8 proposer's **required replay was itself instrumented**. The unmodified entry
script, with its established arguments, ran through the counting wrapper (`runpy` under
`__main__`), so no second ~11-minute run was needed:

```text
.venv/bin/python <scratchpad>/core12/instrument.py tools/partition_graph8_integrate.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-7-proposals previews/conceptual-core-12-phase8-proposals
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

All eight lines are string-identical to the accepted Core-11 lines.

| gate | wall | accepted reference | accepted total | excluded | fresh = accepted scope | result | scope manifest sha256 |
|---|---|---|---|---|---|---|---|
| Phase-6 proposer | 2.85 s | `partition-graph-6-proposals` | 102 | — | 102 | byte-identical | `30e88f61da7ef1d43bc9bb530418f2d03c1403347b26f22a0d9a1c211309bbad` |
| Phase-6 evaluator | 1.45 s | `partition-graph-6-evaluation` | 59 | `demo/` 28, `demo-package-original/` 28 | 3 | byte-identical | `b584139a0186e014627452c74c811ed7b5281f3351255ae2596340ef6ae96fff` |
| Phase-7 proposer | 47.90 s | `partition-graph-7-proposals` | 835 | — | 835 | byte-identical | `3dde52e4cd34228f91c240db3682dc489d9f1adb74a5e85a7021b58bff1673de` |
| Phase-7 evaluator | 19.56 s | `partition-graph-7-evaluation` | 321 | `demo/` 107, `demo-package-original/` 107 | 107 | byte-identical | `05d35ef37a6294c0b0da08a1f943d7c9c8daef93c22819adb9beb8bdb3da0515` |
| **Phase-8 proposer** (instrumented) | 662.18 s | `partition-graph-8-proposals` | 468 | — | 468 | **byte-identical** | `69ccbfb748f250e19baebb75789e57c66f4c26443286e43a9a85ca77f474a209` |
| Phase-8 evaluator | 125.91 s | `partition-graph-8-evaluation` | 321 | `demo/` 107, `demo-package-original/` 107 | 107 | byte-identical | `01c8d253f5ea8698e8df290b7090f299d2fb462c6c40a0fdb04bdc7611525f7d` |
| Phase-8b proposer | 62.66 s | `partition-graph-8b-proposals` | 503 | — | 503 | byte-identical | `51a93fc464fc8ce00fc7f519ccadc25f539095be06de074788844b12ad6e7b7d` |
| Phase-8b evaluator | 16.55 s | `partition-graph-8b-evaluation` | 19 | `demo/` 8, `demo-package-original/` 8 | 3 | byte-identical | `243133b66237523147e1a869ee5b1bf97ee28ec9d817c5c059921e9b254c5715` |

Each comparison was two-sided:
- set equality after only the established exclusions, with no fresh file beneath an
  excluded path;
- `filecmp` with `shallow=False` on every pair;
- equal `LC_ALL=C` manifests.

`only_fresh`, `only_accepted`, `fresh_under_excluded` and `byte_diff` were 0 everywhere.

## Instrumentation counts

The instrumentation wrapped four bindings, each delegating to the real object:
- `candidate_policy`'s binding of the pure builder;
- `candidate_policy`'s `annotate_candidate_partition`;
- the `build_candidate_partition` binding of each of the four historical modules;
- `benchmark`'s compatibility alias.

The Phase-8 proposer count comes from its required replay. The other phases were instrumented
in separate scratch runs, whose outputs were also byte-identical to the accepted trees.

| run | pure builds | annotations | wrapper calls (binding) | alias | annotated rows | candidate rows | reconciliation |
|---|---|---|---|---|---|---|---|
| Phase-6 proposer | **25** | 25 | 25 (`benchmark`) | 0 | 3452 | 1672 (OTHER_SURFACE 1384, UNKNOWN 288) | equal to the COMPLETE `candidate_regions`/`candidate_kinds`. The rows equal the Core-11 measurement (3452, one partition per target) |
| Phase-7 proposer | **208** | 208 | 208 (`prefix_benchmark`) | 0 | 69228 | 25759 (22865 + 2894) | 2 × 104 states. 25759 = `local_candidates` 8557 + `global_candidates` 17202, the same candidate rows as the Core-11 report |
| Phase-8 proposer | **208** | 208 | 208 (`integration`) | 0 | 104134 | 34027 (31339 + 2688) | 2 × 104 states (the historical and integrated sites). 34027 = the historical Phase-7-global recomputation 17202 + the integrated `candidate_regions` 16825. **First measurement of this count; Core 11 did not instrument the Phase-8 proposer** |
| Phase-8b proposer | **125** | 125 | 125 (`challenge_suite`) | 0 | 54473 | 16547 (15605 + 942) | one base partition per state (5 scenarios × 25). The committed Core-11 report records only the Phase-8b call count (125), not these rows. Phase 8b's own `raw_candidates` (18469) also count its UNKNOWN shells and are not these rows |
| Phase-6, 7, 8 and 8b evaluators | **0** | 0 | 0 | 0 | — | — | load only |

The pure builds, annotations and wrapper calls are one-to-one in every run. The
compatibility alias is never called by production.

## Baseline, golden and Gate A

Gate A was run at `06b9645` and again at `388731a`, with identical results:

| step | result |
|---|---|
| compile (changed Python) | ok |
| conceptual checkers | Core-12 70/0; Core-10 29/0, Core-9 24/0, Core-8 20/0, Core-7 22/0, Core-6 35/0, Core-5 38/0, Core-4 32/0, Core-3 27/0, Core-2 20/0, Core-1 13/0 (unmodified) |
| accepted Core-11 checker at `d324e09` (read-only detached worktree, 0 tracked changes) | 59/0 |
| Partition-Graph checkers (unmodified) | 1: 13/0, 2: 16/0, 3: 20/0, 4: 14/0, 5: 12/0, 6: 12/0, 7: 12/0, 8: 10/0, 8b: 12/0 |
| facade | 16/0 |
| `scripts/verify_baseline.sh` | `[verify] SUMMARY passed=9 failed=0` (31/31) |
| `scripts/compare_golden.sh previews/partition-graph-2-source-full` | `[compare-golden] MISMATCHES 0` (10.05 s; 9.79 s) |
| `git diff --check` (worktree, and `9eb9d99..HEAD`) | clean |
| fresh footprints | as tabulated above |

## Accepted-tree integrity

Full-tree per-file sha256 manifests of the 13 accepted trees were taken under the guard at
`06b9645`, before the first replay and after the last replay and instrumentation. They are
**identical**, and also identical to Core 11's final snapshot:

| tree | files | manifest sha256 |
|---|---|---|
| `partition-graph-2-source-full` | 1122 | `9c4def894e2573c22722336cf200d794e30d566f88108cdde3ee3722da7ff53d` |
| `partition-graph-2-full` | 524 | `9589e4a335ff9490a2f0aaf7c034c14abfc2559095d36d143115349accadb509` |
| `partition-graph-4-lift` | 419 | `7eed664047384a43f50f51940cc4ad61d602513bb1095e076adc6c083ac3cbe3` |
| `partition-graph-4-full` | 425 | `223c7ea9bd226aba24f96fa97c9e5119ae0a6e27a62e21d0abb048e821650d95` |
| `partition-graph-5-full` | 225 | `41640332e411582b31ab6cafc9675034d955d4884bf77e3b06cfb19ad2677517` |
| `partition-graph-6-proposals` | 102 | `30e88f61da7ef1d43bc9bb530418f2d03c1403347b26f22a0d9a1c211309bbad` |
| `partition-graph-6-evaluation` | 59 | `06caf55212f68604cdd8e2414028358085dec702e612ee862750d1bd9f7ccfe4` |
| `partition-graph-7-proposals` | 835 | `3dde52e4cd34228f91c240db3682dc489d9f1adb74a5e85a7021b58bff1673de` |
| `partition-graph-7-evaluation` | 321 | `08a74a0f25245ca1c63b8203f7228ee3b44c0863e9ee66b1cc7a01676f6a12d2` |
| `partition-graph-8-proposals` | 468 | `69ccbfb748f250e19baebb75789e57c66f4c26443286e43a9a85ca77f474a209` |
| `partition-graph-8-evaluation` | 321 | `f08d5dbae6519b607e651caaa74b14f0d141374629b6945bd0b95567ebfaeea2` |
| `partition-graph-8b-proposals` | 503 | `51a93fc464fc8ce00fc7f519ccadc25f539095be06de074788844b12ad6e7b7d` |
| `partition-graph-8b-evaluation` | 19 | `c08677826edf589e75de1b921cf354bfbe5d4dd9158d12ae4d1dac42bad96bb9` |

## Changed-path → executed-gate coverage

| changed path | kind | exercised by | execution evidence |
|---|---|---|---|
| `fov3d/epistemic/partition.py` (three lines removed) | pure representation redesign | A/B/D/H checker; the 10,000-state differential; Phases 6–8b | 25 / 208 / 208 / 125 pure builds in the Phase-6/7/8/8b proposers; all products byte-identical |
| `candidate_policy.py` (new) | historical interpretation | C/D/F/G/H checker; the differential; Phases 6–8b | annotations and wrapper calls one-to-one with the pure builds; byte-identical |
| `benchmark.py` imports, alias and `propose_phase6` call | compatibility plus wiring | E/F checker; unmodified checkers 6/7/8 (through the alias); Phase-6 P/E | 25 wrapper calls; alias 0 calls in production; byte-identical |
| `prefix_benchmark.py` imports and call | wiring plus orphan removal | F; Phase-7 P/E (and Phase 8 through it) | 208 wrapper calls; byte-identical |
| `integration.py` import and two calls | wiring | F; Phase-8 P/E | 208 wrapper calls (the instrumented required replay); byte-identical |
| `challenge_suite.py` imports and base call | wiring (8b logic untouched) | F (including independence); Phase-8b P/E | 125 wrapper calls; FULL parity 25; byte-identical |
| `fov3d/epistemic/__init__.py` | **unchanged** | G | file equality with Core 11; fresh bare footprint |
| `tools/dev/check_conceptual_core12.py` | new checker | Gate A; mutation harnesses | 70/70; 51/51 dynamic and 25/25 static mutants caught |

## Repairs and deviations

1. **No production repair was needed.** No gate failed against the implementation.
2. **Checker strengthening before commit.** Two defects were found while designing the
   mutants: a crash-only catch, and comment drift that survived. Both were fixed by making
   lookups non-raising and **adding** a source-text comparison. No check was weakened, and
   the full mutation suites were re-run on the final checker.
3. **Replay/instrumentation arrangement.** The contract allowed two approaches; both are
   recorded:
   - The Phase-8 proposer's required replay was run **once**, through the counting wrapper
     with its established arguments, into its fresh `previews/` directory.
   - The seven other gates were replayed with the plain established commands, plus cheap
     instrumented scratch runs.
4. **Upstream of the local Core-12 branch.** Because the branch was created from
   `origin/main`, it initially tracked `origin/main`. Its upstream was set to
   `origin/migration/conceptual-core-12` before any push, so that no accidental push to
   `main` was possible.

No other deviation. The replay commands, inputs, references and exclusions are the
established ones.

## Deferred (explicitly not part of Core 12)

1. `reconstruction_status` (`mapped_now` / `targeted_later` / `never_targeted`, which depends
   on `all_target_ids`).
2. `min_distance_to_historical_gaze_deg`.
3. Other historical/context annotations (for example `surface_source`), pending the Core-13
   design.
4. The placement of the target-relative `HeadEvidence` fields.
5. `_own_labels` versus `own_support_labels`.
6. `component_lineage` versus `scene.lineage._lineage`.
7. The `attach_state_region_codes` rename.
8. The consumerless compatibility aliases. These now include `benchmark.CANDIDATE_KINDS` and
   the six helper names, which have no in-repo consumer besides the Core-11/12 checks.
   `benchmark.build_epistemic_partition` stays used by the unmodified Partition-Graph
   checkers 6, 7 and 8.
9. The historical Phase-2/Phase-3 boundary lineage cleanup.

No Core 13 in this run.

## Unresolved decisions (for Luiz and Chat)

- Whether to accept Core 12 and fast-forward `main` to the final head of this branch.
- The Core-13 design for the historical/context annotations still inside the representation.

## Acceptance

| criterion | status |
|---|---|
| intrinsic `epistemic.partition` no longer owns candidate semantics | MEASURED pass |
| its output is exactly Core 11 minus only `region["candidate"]` and `diag["candidate_region_count"]` | MEASURED pass (fixtures, 300 + 10,000 random states) |
| `candidate_policy` reconstructs the accepted Core-11 output exactly | MEASURED pass |
| `benchmark`'s historical compatibility intact | MEASURED pass |
| all unmodified Partition-Graph checkers pass | MEASURED pass (1–8b) |
| Core-1 to Core-10 conceptual checkers pass at the current head | MEASURED pass |
| accepted Core-11 checker passes at `d324e09` | MEASURED pass (59/59) |
| Core-12 checker fail-capable | MEASURED pass (51/51 + 25/25) |
| randomized reconstitution differential clean | MEASURED pass (10,000/10,000; 7 controls detected) |
| no experiment dependency in `epistemic.partition` | MEASURED pass |
| Phase 8b's separate candidate semantics independent | MEASURED pass (structural and live control) |
| baseline 31/31; golden `MISMATCHES 0` | MEASURED pass |
| every reached Phase-6/7/8/8b product byte-identical | MEASURED pass (8/8) |
| accepted reference trees unchanged | MEASURED pass (13/13) |
| every changed production path maps to an executed gate | MEASURED pass |

    CONCEPTUAL_CORE12_CANDIDATE_POLICY_SEPARATION_PRESERVES_BEHAVIOR
