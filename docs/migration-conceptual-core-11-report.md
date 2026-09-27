# Migration Conceptual Core 11 — report

**Result.**

    CONCEPTUAL_CORE11_EPISTEMIC_PARTITION_PRESERVES_BEHAVIOR

This result is MEASURED and awaits review by Luiz and Chat. Core 11 is **not** merged into
`main`.

**Causal question.** Can the accepted epistemic-region representation and partition
constructor be moved out of the Phase-6 benchmark module into the reusable epistemic layer
without changing any behavior?

**Answer (measured): yes.** The evidence:
- `fov3d.epistemic.partition` now owns the exact cluster:
  - the constants `REGION_KIND`, `REGION_KIND_BY_CODE` and `CANDIDATE_KINDS`;
  - the functions `_component_labels`, `_distance_to_target`, `_touches_edge`,
    `_centroid_angles`, `_angular_distance_deg`, `_region_interfaces` and
    `build_epistemic_partition`.

  Source text and AST are identical to accepted Core 10, and the global bindings are
  equivalent.
- `benchmark.py` keeps all ten names as **identical objects**, through a compatibility
  import.
- Phases 7, 8 and 8b take the moved names from the conceptual module.
- `fov3d/epistemic/__init__.py` is unchanged, and a bare `import fov3d.epistemic` stays
  OpenCV-free.
- The new checker passes 59/59 and is demonstrably fail-capable: every one of 113
  non-equivalent behavioral mutants and 21 static mutants was caught.
- Every Phase-6, 7, 8 and 8b proposer and evaluator reached by the fresh import audit is
  **byte-identical**, including the approximately 11-minute Phase-8 proposer.
- The 13 accepted trees are unchanged, golden reports `MISMATCHES 0`, and the baseline is
  31/31.

The representation was migrated **intact**. Separating it from candidate or attention policy
is explicitly deferred (see the end of this report).

## Provenance: Core-10 acceptance administration and branch

| step | result |
|---|---|
| **Core 10 accepted** (Luiz) | `origin/main` fast-forwarded `b69e0c9..85c0938` (`85c09381584e30c3643bd55be23183f1cdbd2af7`) by a plain, non-forced push of the exact commit |
| handoff | in a detached administrative worktree, only `docs/chat-handoff.md` was changed: commit `a312959ae9a07afca65d0c4781846517d1645344` (parent `85c0938`), pushed as a fast-forward to `main`. The administrative worktree was then removed |
| branch | `migration/conceptual-core-11` created at `a312959` from the **new** `origin/main`, both remote and local |
| Core-11 commits | `a836f59` contract, **committed before any production change** · `6725cb5` extraction · `aa9665b` blank-line separation (see Repairs) · `2a40f0b` checker · `8939784` conceptual map · the commit that adds this report |
| gates measured at | the mechanical audit at `6725cb5`/`aa9665b`; the checker mutation tests before `2a40f0b`; Gate A, the import audit, the replays, the instrumentation and both accepted-tree snapshots at `2a40f0b`; Gate A again at `8939784`. `fov3d/` and `tools/` are identical at `2a40f0b` and `8939784` |
| final head | the commit that adds this report |

The handoff records:
- Core 10 accepted at `85c0938`;
- `fov3d.scene.corridors` ownership, combining the Core-6 geometry with the Core-10
  relation origin;
- that `fov3d.scene.relations` is NumPy-only;
- the Core-10 evidence and the deferred cleanups;
- the working arrangement;
- Core 11 as the active step.

## Isolated worktree and guard

- **Where it ran.** Every Core-11 edit and measurement ran in the dedicated worktree
  `<scratchpad>/core11/wt` on `migration/conceptual-core-11`.
- **Data links.** The untracked data are symlinked in: `previews/`, `.venv/`, and the
  ignored `scenes/classroom/` asset entries. `fov3d` resolves to the worktree's code.
- **Guard.** Every measurement ran under the guard, which requires, before and after,
  branch `migration/conceptual-core-11`, the expected HEAD, and a clean tracked tree. It
  never tripped. One mistyped invocation, missing the `--` separator, ran nothing: it
  tried to execute the commit id as a command (rc 127) and changed nothing.
- **Shared checkout.** `/home/lvelho/rd/f3d-vision` was not mutated and its branch was not
  switched. It stays on local `main` at `e681392`, behind `origin/main`.

## Files changed (main a312959...final head)

| file | change |
|---|---|
| `docs/migration-conceptual-core-11.md` | contract (`a836f59`) |
| `fov3d/epistemic/partition.py` | **new**, 264 lines: a docstring, the imports `Counter`, `defaultdict`, `Any`, `math`, `cv2`, `numpy as np` and `head_chart.chart_grid`, then the three constant assignments and the seven functions. These are the **exact** `ast.get_source_segment` texts of `85c0938:benchmark.py`, generated mechanically and kept in their original order (`6725cb5`, blank-line separation `aa9665b`) |
| `fov3d/experiments/classroom_partition/benchmark.py` | cluster removed (L30–38 and L73–304 of Core 10). It gains `from fov3d.epistemic.partition import (...)` with the ten names. The measured orphans are dropped: `cv2`, `math`, and `defaultdict` from `collections`. Every remaining definition and non-import statement is source-identical to Core 10, including the aliases comment, `FUSION_RADIUS_M`, `_cells` and `_grid` (`6725cb5`) |
| `.../prefix_benchmark.py` | import block only: `CANDIDATE_KINDS`, `REGION_KIND`, `REGION_KIND_BY_CODE` and `build_epistemic_partition` from `fov3d.epistemic.partition`; `_covered` from `benchmark` |
| `.../integration.py` | import block only: `build_epistemic_partition` from `fov3d.epistemic.partition`; `_covered` from `benchmark` |
| `.../challenge_suite.py` | import block only: `REGION_KIND`, `_region_interfaces` and `build_epistemic_partition` from `fov3d.epistemic.partition`; `_covered` from `benchmark` |
| `tools/dev/check_conceptual_core11.py` | new checker, 59 checks (`2a40f0b`) |
| `docs/conceptual-core-map.md` | Cores 1–10 accepted, Core 11 proposed (measured); changes to the `benchmark`/`prefix_benchmark`/`integration`/`challenge_suite` rows, a Core-11 extraction section, and item 9 of the order (`8939784`) |
| `docs/migration-conceptual-core-11-report.md` | this report |

`fov3d/epistemic/__init__.py` is **not** modified. No other file changed.

## Mechanical audit (before the checker)

This was a throw-away scratchpad audit, run with the repository `.venv` against
`git show 85c0938`, at 162/162 OK. It covered six things.

**1. Literal identity.** For all ten names:
- source text and AST are identical;
- the destination defines exactly the cluster, in the accepted order;
- the constants have identical values, types and dict order;
- the `LOAD_GLOBAL` name sets are identical for every function, with each non-cluster
  global the **same object** as in Core 10.

The external globals are exactly `Counter`, `chart_grid`, `cv2`, `defaultdict`, `math` and
`np`. `Any` is used only in annotations.

**2. `benchmark.py` remainder.**
- The remaining definitions are `_json`, `_write_json`, `_guard_source_path`,
  `propose_phase6`, `_covered`, `_miss_components` and `evaluate_phase6`.
- The 11 remaining non-import statements (the docstring, the three aliases and the seven
  functions) are source- and AST-identical in order, and the
  comments equal the Core-10 comments minus those inside the moved functions.
- Every remaining function has an identical `LOAD_GLOBAL` set with equivalent bindings.
  `propose_phase6` is the only user of a moved name (`build_epistemic_partition`).

**3. Orphans.** An AST name audit **including annotations** measured the Core-10 imports
left unused by the non-moved remainder as exactly `cv2`, `defaultdict` and `math`. The
removed imports equal that set. Every kept import is used, and each is the Core-10 object.
`Any` stays because it is still used in annotations. An earlier prediction based on
`LOAD_GLOBAL` alone had wrongly listed `Any`, because annotation-only names do not appear
in bytecode.

**4. Consumers.**
- Non-import statements are source-identical.
- The bound import names are the same, and only the moved names changed source, from
  `benchmark` to `fov3d.epistemic.partition`.
- `_covered` still comes from `benchmark`, and the runtime objects are the conceptual ones.

**5. Repo-wide references.** Outside the conceptual module and the three consumers, the
moved names are imported only through `benchmark`, and only by:
- `tools/dev/check_partition_graph{6,7,8,8b}.py`;
- `tools/partition_graph{6,7,8b}_demo.py`.

All of these are unmodified, and each resolves to the conceptual objects, which was
measured. A `symtable` scan found that every global use of a moved name is bound at module
level.

**6. Fresh-process footprints**, compared with a `git archive` export of `85c0938`:
- a bare `fov3d.epistemic` is unchanged: only `fov3d` and `fov3d.epistemic`, with no `cv2`;
- `fov3d.epistemic.partition` loads `cv2` plus exactly `fov3d`, `fov3d.epistemic`,
  `fov3d.epistemic.partition`, `fov3d.geometry` and `fov3d.geometry.head_chart`, and no
  experiment, reconstruction, stereo or scene module;
- `benchmark` = Core 10 + {`fov3d.epistemic`, `fov3d.epistemic.partition`};
- `prefix_benchmark`, `integration` and `challenge_suite` = Core 10 +
  {`fov3d.epistemic.partition`}.

The benchmark delta includes the package `fov3d.epistemic` because Core-10 `benchmark` did
not import it at all. Its `__init__` is a docstring. The audit's first expectation had
omitted this; that was an audit-expectation error, which was corrected, and the
implementation was not changed.

## The Core-11 checker

`tools/dev/check_conceptual_core11.py` runs host-side, deterministically, in 0.58 s (measured). It
reads accepted Core 10 with `git show 85c0938…`, prints
`[conceptual-core11-check] SUMMARY checked=59 failed=0`, and exits nonzero on any failure.

| item | checks | what is witnessed |
|---|---|---|
| **A** literal / compatibility | 13 | Checks against Core 10:<br>• source text and AST of the ten definitions;<br>• the destination defines exactly the cluster, in order;<br>• the vocabulary values, order and inverse, and `CANDIDATE_KINDS` exactly `{OTHER_SURFACE, UNKNOWN}`;<br>• global bindings, with cluster names resolving inside `epistemic.partition`;<br>• `benchmark` re-exports the ten identical objects, with no duplicate definition;<br>• `benchmark`'s remaining statements are source-identical;<br>• `benchmark`'s imports are Core 10 minus exactly `cv2`/`math`/`defaultdict` plus the compatibility import;<br>• `propose_phase6` resolves the conceptual constructor;<br>• the consumers resolve the conceptual objects and keep `benchmark._covered`, and differ from Core 10 only in their imports |
| **B** `_component_labels` | 3 | 4- versus 8-connectivity on a hand-derived raster (counts 6/5 with background, raster-order labels, `int32`, Python `int` count), and the empty mask |
| **C** `_distance_to_target` | 3 | No target gives `float32` +inf. OpenCV L2/5×5 chamfer values (0, 1, 1.4, 2, 2.1969, 2.8, …) × `grid_deg` 0.5, `float32`. Target cells are 0 and the values increase away from them |
| **D** `_touches_edge` | 2 | Empty, interior and next-to-border masks give `False`; each border alone gives `True`; the result is a Python `bool` |
| **E** `_centroid_angles` | 2 | An asymmetric mask checks column→yaw and row→pitch (x/y reversal is visible); the empty mask gives `(nan, nan)` |
| **F** `_angular_distance_deg` | 5 | • zero;<br>• a **live clip witness** (identical (-60°, -28°) directions have dot = 1 + ε);<br>• pure yaw and pitch in degrees;<br>• pitch sign and argument order;<br>• non-planar cases against an independent closed-form great-circle formula |
| **G** `_region_interfaces` | 4 | • horizontal + vertical accumulation;<br>• background ignored;<br>• numeric (not string) pair order, with codes 2/9/10/12;<br>• exact edge-row keys;<br>• symmetric adjacency with Python-int keys and values;<br>• codes beyond 8 bits (300 versus 44);<br>• the single-region raster |
| **H** `build_epistemic_partition` | 20 | Three hand-derived fixtures:<br>• **H1** (4×6, target 7, nine regions): precedence, surface identity and ambiguous/mapped overlap; region codes, arrays and pass-through dtypes; every row field (kinds, ids, instance ids and the candidate flag; counts, edge flags and centroids; chamfer min/median target distances; great-circle gaze minima; seen/depth fractions; mapped/incidental counts; `surface_source` and `reconstruction_status` across all of `mapped_and_incidental`/`mapped`/`incidental` and `mapped_now`/`targeted_later`/`never_targeted`; adjacency and `adjacent_to_target_support`); the complete rows with key order and types; 15 edge rows; the full `diag`, including `truth_used = False`<br>• **H2** (2×6 checkerboards): 8-connectivity for target, other and target-unmapped; 4-connectivity for unknown and ambiguous<br>• **H3** (2×3, no target and no gazes): `None` descriptors, codes, `never_targeted` and the full `diag`<br>• the exact `ValueError` for mismatched shapes |
| **I** package / imports | 7 | • `fov3d/epistemic/__init__.py` equal to Core 10;<br>• `epistemic.partition` imports only the allowed modules (full AST walk, so lazy imports are caught);<br>• the direct consumers import exactly their names from `epistemic.partition` and only `_covered` from `benchmark`;<br>• no production module takes a moved name through `benchmark`;<br>• the fresh bare `fov3d.epistemic` footprint;<br>• the fresh `epistemic.partition` footprint (exact module list);<br>• both import orders give shared identities, so there is no cycle |

All H1–H3 expectations were derived by hand, and the checker passed on its first run
against the implementation. That makes a derivation error that happens to agree with the
implementation unlikely, but the mutation tests below are the actual fail-capability
evidence.

### Mutation testing (before the checker was committed)

**Behavioral (dynamic) mutants.** Each is a text substitution with an asserted match count,
applied to `partition.py`. The result is executed as `fov3d.epistemic.partition` and
rebound onto the package before the checker, and therefore `benchmark` and the consumers,
import it.

| class | non-equivalent caught / total | claimed equivalent |
|---|---|---|
| 1 vocabulary and candidate compatibility | 10 / 10 | — |
| 2 precedence | 8 / 8 | 1 |
| 3 connected components | 6 / 6 | 2 |
| 4 target distance and geometry | 26 / 26 | — |
| 5 interfaces | 12 / 12 | — |
| 6 surface identity | 9 / 9 | 1 |
| 7 region construction | 21 / 21 | 3 |
| 8 metadata | 21 / 21 | — |
| **total** | **113 / 113** (0 survived) | 7 |

Only one non-equivalent mutant was caught by A alone: `v_by_code_not_inverse`.
`REGION_KIND_BY_CODE` is not used inside the cluster, so its value check is its
behavioral check.

**Static mutants: 21/21 caught**, on throw-away `git ls-files | tar` copies of the tree;
the unmutated copy passes 59/0.
- **Class 9, packaging (12):**
  - `benchmark`: a duplicate definition; a missing compatibility import; a compatibility
    name rebound to a copy;
  - consumers: each of `prefix_benchmark`, `integration` and `challenge_suite` taking a
    moved name through `benchmark`; another module taking one through a lazy import;
  - `__init__`: an eager `from . import partition`; a comment-only change;
  - `epistemic.partition`: a lazy experiment import; a top-level experiment import; an
    extra `json` import.
- **Literal and structural drift (9):**
  - `partition.py`: an extra helper; a comment inside a moved function; a behaviorally
    equivalent AST change; constant source reformatting; a `chart_grid` rebound to a
    local wrapper;
  - `benchmark.py`: an orphan restored (`import math`); a kept import dropped; a remaining
    definition edited;
  - a consumer non-import edit.

**Claimed-equivalent mutants (recorded separately; the checker was not weakened):**

| mutant | reason | probe |
|---|---|---|
| `p_class_code_order` | the five class masks are disjoint | 9000 cases, 0 differ |
| `c_no_astype` | OpenCV already returns `int32` labels | 9000 / 0 |
| `c_count_not_int` | OpenCV already returns a Python `int` count | 9000 / 0; nonetheless **caught by A**, because dropping `int()` changes the `LOAD_GLOBAL` set |
| `s_take_inc_unmasked` | `incidental_other` already excludes `mapped_other` | 9000 / 0 |
| `r_instance_not_int` | every call passes `None`, `int(target_id)` or a Python-int id | 9000 / 0 |
| `r_empty_component_guard_removed` | `connectedComponents` labels 1..n−1 are non-empty | 9000 / 0 |
| `r_unknown_source_string` | an `OTHER_SURFACE` component always has a mapped or incidental cell | 9000 / 0 |

The probe compared full `build_epistemic_partition` outputs (arrays, rows, edges and diag,
type-strict) and `_component_labels` at connectivity 4 and 8 on 3000 random states per
mutant (sizes 2–9 × 2–11, grid 0.5–4°, random ids, ambiguity, target sets and gazes). Six
non-equivalent controls were detected:

| control | cases that differed |
|---|---|
| `p_mapped_incidental_overlap` | 2776 |
| `r_status_targeted_inverted` | 2824 |
| `c_labels_int64` | 6000 |
| `r_unknown_after_ambiguous` | 2416 |
| `m_gaze_first_only` | 1074 |
| `s_identity_string_order` | 2756 |

**Checker strengthening before commit.** Designing the mutant set exposed four gaps. They
were closed by **adding** checks before the first mutation run; no check was weakened:
- the `benchmark` import set, so a restored orphan is caught;
- consumers changed only in their imports;
- codes beyond 8 bits in G, to catch a `uint8` cast;
- the full `diag` in H3. In H1 the target-unmapped and ambiguous cell counts are both 2,
  so only H3 separates them.

## Gate A (structural, under the guard)

Run at `2a40f0b` and again at `8939784`, with identical results.

| step | result |
|---|---|
| compile (changed Python) | ok |
| conceptual checkers | Core-11 59/0, Core-10 29/0, Core-9 24/0, Core-8 20/0, Core-7 22/0, Core-6 35/0, Core-5 38/0, Core-4 32/0, Core-3 27/0, Core-2 20/0, Core-1 13/0 |
| Partition-Graph checkers (unmodified) | 1: 13/0, 2: 16/0, 3: 20/0, 4: 14/0, 5: 12/0, 6: 12/0, 7: 12/0, 8: 10/0, 8b: 12/0 |
| facade | 16/0 |
| `scripts/verify_baseline.sh` | `[verify] SUMMARY passed=9 failed=0` (31/31 byte-identical) |
| `scripts/compare_golden.sh previews/partition-graph-2-source-full` | `[compare-golden] MISMATCHES 0` (9.97 s; 9.88 s at `8939784`) |
| `git diff --check` (worktree, and `a312959..HEAD`) | clean |

Fresh-process footprints:

| module | `fov3d` modules | `cv2` | loads `epistemic.partition` | loads `benchmark` |
|---|---|---|---|---|
| `fov3d.epistemic` | 2 (`fov3d`, `fov3d.epistemic`) | no | no | no |
| `fov3d.epistemic.partition` | 5 (+ `fov3d.epistemic.partition`, `fov3d.geometry`, `fov3d.geometry.head_chart`) | yes | — | no |
| `benchmark` | 14 | yes | yes | — |
| `prefix_benchmark` | 17 | yes | yes | yes |
| `integration` | 19 | yes | yes | yes |
| `challenge_suite` | 23 | yes | yes | yes |

## Import/dependency audit and replay decisions

A fresh audit ran at `2a40f0b` under the guard. Each entry script was loaded in a fresh
`-I` process without running `main`, and `sys.modules` was then recorded.

| entry point | loads `fov3d.epistemic.partition` | loads `benchmark` | also loads | decision |
|---|---|---|---|---|
| Phase-6 proposer / evaluator | **yes** | **yes** | — | replayed (primary) |
| Phase-7 proposer / evaluator | **yes** | **yes** | `prefix_benchmark` | replayed |
| Phase-8 proposer / evaluator | **yes** | **yes** | `prefix_benchmark`, `integration` | replayed (the proposer was authorized) |
| Phase-8b proposer / evaluator | **yes** | **yes** | `challenge_suite` | replayed |
| Phase-2 lift, Phase-3 lift, Phase-4 analyzer, Phase-5 analyzer | no | no | — | **not run** |
| (informational) `tools/partition_graph4_lift.py`, a second wrapper of `lift_joint_run` | no | no | — | not run |

This matches the expected topology.

**AST scan.** It covered top-level and nested imports of either module.
- **Production importers:** `benchmark`, `prefix_benchmark`, `integration` and
  `challenge_suite`.
- **Tools:**
  - the Phase-6 proposer and evaluator;
  - checkers 6, 7, 8 and 8b;
  - demos 6, 7 and 8b;
  - a nested import in `check_conceptual_core2.py` (L145);
  - the Core-11 checker.
- **Dynamic-import sites:** unchanged, namely `fov3d/_compat.py:8`,
  `check_fov3d_facade.py:28-29` and `check_partition_graph3.py:144`, plus the Core-11
  checker's own `importlib.import_module` of the three consumers.

**Call sites.** `build_epistemic_partition` is called only in `propose_phase6`,
`propose_phase7`, `propose_phase8` (two sites) and `propose_phase8b`. The evaluators load
the changed modules but do not call it; the zero calls are measured below.

## Replay gates: byte comparisons and manifests

All replays ran from the worktree root under the guard at `2a40f0b`, in order, each to a
fresh `previews/conceptual-core-11-*` directory. The commands are the established ones,
with the same inputs as those recorded in the accepted trees' `summary.json`:

```text
.venv/bin/python tools/partition_graph6_propose.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/partition-graph-5-full previews/conceptual-core-11-phase6-proposals
.venv/bin/python tools/partition_graph6_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-6-proposals previews/conceptual-core-11-phase6-evaluation
.venv/bin/python tools/partition_graph7_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-6-proposals previews/conceptual-core-11-phase7-proposals
.venv/bin/python tools/partition_graph7_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-7-proposals previews/partition-graph-6-evaluation previews/conceptual-core-11-phase7-evaluation
.venv/bin/python tools/partition_graph8_integrate.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-7-proposals previews/conceptual-core-11-phase8-proposals
.venv/bin/python tools/partition_graph8_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8-proposals previews/partition-graph-7-evaluation previews/conceptual-core-11-phase8-evaluation
.venv/bin/python tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals previews/conceptual-core-11-phase8b-proposals
.venv/bin/python tools/partition_graph8b_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8b-proposals previews/partition-graph-8-evaluation previews/conceptual-core-11-phase8b-evaluation
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

All eight lines are string-identical to lines in earlier committed reports.

| gate | wall | accepted reference | accepted total | excluded | fresh = accepted scope | result | scope manifest sha256 |
|---|---|---|---|---|---|---|---|
| **Phase-6 proposer (primary)** | 2.87 s | `partition-graph-6-proposals` | 102 | — | 102 | **byte-identical** | `30e88f61da7ef1d43bc9bb530418f2d03c1403347b26f22a0d9a1c211309bbad` |
| Phase-6 evaluator | 1.45 s | `partition-graph-6-evaluation` | 59 | `demo/` 28, `demo-package-original/` 28 | 3 | byte-identical | `b584139a0186e014627452c74c811ed7b5281f3351255ae2596340ef6ae96fff` |
| Phase-7 proposer | 47.42 s | `partition-graph-7-proposals` | 835 | — | 835 | byte-identical | `3dde52e4cd34228f91c240db3682dc489d9f1adb74a5e85a7021b58bff1673de` |
| Phase-7 evaluator | 19.44 s | `partition-graph-7-evaluation` | 321 | `demo/` 107, `demo-package-original/` 107 | 107 | byte-identical | `05d35ef37a6294c0b0da08a1f943d7c9c8daef93c22819adb9beb8bdb3da0515` |
| Phase-8 proposer | 658.20 s | `partition-graph-8-proposals` | 468 | — | 468 | byte-identical | `69ccbfb748f250e19baebb75789e57c66f4c26443286e43a9a85ca77f474a209` |
| Phase-8 evaluator | 125.01 s | `partition-graph-8-evaluation` | 321 | `demo/` 107, `demo-package-original/` 107 | 107 | byte-identical | `01c8d253f5ea8698e8df290b7090f299d2fb462c6c40a0fdb04bdc7611525f7d` |
| Phase-8b proposer | 61.80 s | `partition-graph-8b-proposals` | 503 | — | 503 | byte-identical | `51a93fc464fc8ce00fc7f519ccadc25f539095be06de074788844b12ad6e7b7d` |
| Phase-8b evaluator | 16.32 s | `partition-graph-8b-evaluation` | 19 | `demo/` 8, `demo-package-original/` 8 | 3 | byte-identical | `243133b66237523147e1a869ee5b1bf97ee28ec9d817c5c059921e9b254c5715` |

Each comparison was two-sided:
- set equality after only the established exclusions, with no fresh file beneath an
  excluded path;
- `filecmp` with `shallow=False` on every pair;
- equal `LC_ALL=C` scope manifests.

`only_fresh`, `only_accepted`, `fresh_under_excluded` and `byte_diff` were 0 in every
gate. Every fresh manifest equals the accepted tree's scope manifest.

## `build_epistemic_partition` execution counts

A separate guarded instrumentation run wrapped the `build_epistemic_partition` binding of
`benchmark`, `prefix_benchmark`, `integration` and `challenge_suite`. Before wrapping,
each binding was asserted to be the conceptual object. The unmodified entry scripts ran
with output to a scratch directory, not `previews/`, and every scratch output was also
byte-identical to its accepted tree.

| run | calls (binding) | reconciliation |
|---|---|---|
| Phase-6 proposer | **25** (`benchmark`) | one per target. The 3452 region rows (`AMBIGUOUS_BOUNDARY` 1739, `OTHER_SURFACE` 1384, `TARGET_SUPPORT` 41, `UNKNOWN` 288) equal, kind by kind, the rows in the 25 saved `targets/*/regions.json`. The candidate rows 1384 + 288 = 1672 equal the COMPLETE `candidate_regions` |
| Phase-7 proposer | **208** (`prefix_benchmark`) | 2 × 104 states. The candidate rows (`OTHER_SURFACE` 22865 + `UNKNOWN` 2894 = 25759) equal `local_candidates` 8557 + `global_candidates` 17202 |
| Phase-8b proposer | **125** (`challenge_suite`) | one per state (5 scenarios × 25 targets). The Phase-8b `raw_candidates` (18469) also count its UNKNOWN shells, so they are not the partition rows. No row reconciliation is claimed |
| Phase-6, 7, 8 and 8b evaluators | **0** | load only |

The Phase-8 proposer (about 11 min) was **not** instrumented, because of its cost. Its
byte-identical replay above executes both `integration` call sites. This is recorded as a
deviation.

## Accepted-tree integrity

Full-tree per-file sha256 manifests of the 13 accepted trees were taken before the first
replay and after the last replay and instrumentation, both under the guard at `2a40f0b`.
They are **identical**. They are also identical to Core 10's final snapshot.

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
| `fov3d/epistemic/partition.py` (the ten moved definitions) | new module, literal move | A (checker 11, all items); Phases 6, 7, 8 and 8b P/E | 25 / 208 / 125 constructor calls in the Phase-6/7/8b proposers; the Phase-8 proposer executes it through `integration`; all outputs byte-identical |
| `benchmark.py` compatibility import and orphan removal | changed module and imports | A; Phases 6–8b | `propose_phase6` resolves the conceptual constructor (25 calls); `evaluate_phase6` and `_covered` load paths byte-identical |
| `prefix_benchmark.py` import block | changed dependency binding | A; Phase-7 P/E (and Phase 8 through `prefix_benchmark`) | 208 calls through its binding; byte-identical |
| `integration.py` import block | changed dependency binding | A; Phase-8 P/E | Phase-8 proposer (both call sites) byte-identical |
| `challenge_suite.py` import block | changed dependency binding | A; Phase-8b P/E | 125 calls through its binding; byte-identical |
| `fov3d/epistemic/__init__.py` | **unchanged** | A/I | file equality with Core 10; fresh bare footprint |
| `tools/dev/check_conceptual_core11.py` | new checker | A; mutation harnesses | 59/59; 113/113 behavioral and 21/21 static mutants caught |

## Repairs and deviations

1. **No production repair was needed.** No check failed against the implementation at any
   point.
2. **Blank-line separation (`aa9665b`).** The literal generator had joined the moved
   segments with three blank lines. A forward commit restored the house two-line
   separation. The segments, AST and bindings were unchanged, and the mechanical audit was
   re-run clean. The branch was unpublished, but no history was rewritten.
3. **Audit expectations corrected (throw-away tooling only).**
   - The venv interpreter path had been resolved through its symlink to the system Python.
   - The reference export needed the sealed `tools/` package.
   - The `benchmark` footprint delta must include the `fov3d.epistemic` package itself.

   None of these affected the implementation or the committed checker.
4. **Checker strengthening before commit.** Four added checks, described above; none was
   weakened.
5. **Phase-8 proposer not instrumented** (cost). Its replay is byte-identical.
6. **Informational audit row.** `tools/partition_graph4_lift.py` was audited in addition to
   the 12 established entry points; it loads neither module.

The replay commands, inputs, references and exclusions are the established ones.

## Deferred (explicitly not part of Core 11)

1. **Separating representation from policy.** The following remain accepted compatibility
   semantics inside `fov3d.epistemic.partition`, and moving them was **not** a judgment
   that they belong there:
   - `CANDIDATE_KINDS` and the `candidate` flag;
   - `surface_source` and `reconstruction_status`, including `targeted_later`, which
     depends on `all_target_ids`;
   - the historical-gaze descriptor.
2. The `_own_labels` (`fov3d.scene.corridors`) versus `own_support_labels` (Phase-4
   relations adapter) duplicate.
3. The `component_lineage` (adapter) versus `fov3d.scene.lineage._lineage` duplicate.
4. The `attach_state_region_codes` rename.
5. The consumerless compatibility aliases, now including Core 11's own: `benchmark`'s
   `CANDIDATE_KINDS` and the six helper names have no in-repo consumer besides the Core-11
   identity check. `REGION_KIND`, `REGION_KIND_BY_CODE` and `build_epistemic_partition`
   remain used through `benchmark` by the historical checkers and demos.
6. The placement of the target-relative `HeadEvidence` fields.
7. The separate historical Phase-2/Phase-3 boundary lineages.

## Unresolved decisions (for Luiz and Chat)

- Whether to accept Core 11 and fast-forward `main` to the final head of this branch.
- The scope of the next Core, in particular whether to begin the representation/policy
  separation (deferred item 1) or one of the compatibility cleanups (items 2–5).

## Acceptance

| criterion | status |
|---|---|
| `fov3d.epistemic.partition` owns the exact cluster (source/AST-preserved functions, preserved constants, equivalent bindings) | MEASURED pass |
| `benchmark` compatibility identities; direct consumers resolve the conceptual implementation | MEASURED pass |
| no duplicate production implementation | MEASURED pass |
| `fov3d/epistemic/__init__.py` unchanged; bare `fov3d.epistemic` lightweight | MEASURED pass |
| no experiment or truth dependency in `epistemic.partition` | MEASURED pass |
| Core-11 checker passes and is demonstrably fail-capable | MEASURED pass (59/59; 113/113 + 21/21 mutants) |
| earlier checkers pass; baseline 31/31; golden `MISMATCHES 0` | MEASURED pass |
| Phase 6 byte-identical; every reached downstream producer and evaluator byte-identical | MEASURED pass (8/8) |
| accepted trees unchanged | MEASURED pass (13/13) |
| every changed production path maps to an executed gate | MEASURED pass |

    CONCEPTUAL_CORE11_EPISTEMIC_PARTITION_PRESERVES_BEHAVIOR
