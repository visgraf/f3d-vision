# Migration Conceptual Core 5 — report (2026-09-27)

Executed by Claude Code on the Ubuntu workstation against the committed contract
`docs/migration-conceptual-core-5.md`. Every number below is **MEASURED** from the
command shown, unless it is marked otherwise.

## Provenance

| item | value |
|---|---|
| branch | `migration/conceptual-core-5` |
| parent accepted milestone | `main` @ `9b28722971622332ab121096521f72f268344387` (merge base verified; `origin/main` is the same commit) |
| scientific parent | Conceptual Core 4 @ `643d21a` |
| proposal head | `72502e5ff102534f07bfbdff11e3db8a9c6c6315`, verified as the pulled head: 5 Chat-authored commits `015ea64`…`72502e5` |
| Code commits | `a96655e` Core-5 checker strengthened · `de972df` map row made precise · the commit that adds this report |
| gates measured at | Gate A at `72502e5` (proposal checker, 29 checks), then the whole of Gate A again at `de972df` (final checker, 38 checks); Gates B–F at `a96655e` |
| final head | the commit that adds this report |

`fov3d/` is byte-identical at `72502e5`, `a96655e` and `de972df`. Code changed only the
dev checker and one map row, so every gate ran against the proposed production code.

## Files changed (main...final head)

| file | change |
|---|---|
| `fov3d/scene/boundaries.py` | new (proposal): `_interface_edges`, `_trace_edge_components`, `extract_boundaries` |
| `fov3d/experiments/classroom_partition/joint.py` | three definitions removed; imports them from `fov3d.scene.boundaries`; the imports of `defaultdict`, `BoundaryChain` and `PartitionRegion` it no longer uses are dropped (proposal) |
| `tools/dev/check_conceptual_core5.py` | new (proposal); strengthened by Code (`a96655e`) |
| `docs/migration-conceptual-core-5.md` | contract (proposal) |
| `docs/conceptual-core-map.md` | Core-5 status, row and order (proposal); `joint.py` row made precise by Code (`de972df`) |
| `docs/migration-conceptual-core-5-report.md` | this report |

The following are untouched (`git diff 9b28722..HEAD` is empty for each):
- `fov3d/scene/__init__.py`, `model.py`, `partition.py`, `sphere.py` and `synthetic.py`;
- `lift.py`, which holds the Phase-2 boundary construction;
- `relations.py` (gap and relation logic, `FineEvidence`), `incidental.py`,
  `integration.py`, `challenge_suite.py`, `benchmark.py` and `prefix_benchmark.py`;
- `fov3d/epistemic`, `fov3d/geometry` and `fov3d/reconstruction`;
- every existing phase checker, every producer, evaluator and demo under `tools/`, and
  `scripts/`;
- `tests/`, including the golden signatures;
- `CLAUDE.md`, `docs/chat-handoff.md`, and sealed runtime files (`verify_baseline.sh`
  31/31);
- the 13 accepted preview trees, by sha256 manifests before and after.

## Final boundary API and dependency direction

    fov3d.geometry.head_chart   chart_grid, head_unit_from_angles
    fov3d.scene.model           BoundaryChain, BoundaryKind, PartitionRegion, RegionKind
    numpy, collections
            -> fov3d.scene.boundaries      (explicit import; NOT in fov3d.scene.__all__)
                   _interface_edges(region_code) -> {(code_lo, code_hi): [edge dict, ...]}
                   _trace_edge_components(edges) -> [(doubled points, used edge indices), ...]
                   extract_boundaries(region_code, code_to_rid, regions, owner_depth, domain, grid_deg)
                       -> ({"jbNNNNN": BoundaryChain}, diagnostics)
            -> fov3d.experiments.classroom_partition.joint
                   build_joint_graph (Phase-3 composer; Phases 3 and 8b)

Fresh-process import footprints (`python -I`):
- `import fov3d.scene` loads exactly `fov3d`, `fov3d.scene`, `fov3d.scene.model` and
  `fov3d.scene.sphere`, with no `cv2`. This is identical to accepted Core 4
  (`git archive 9b28722`, same probe).
- `import fov3d.scene.boundaries` adds only `fov3d.geometry`, `fov3d.geometry.head_chart`
  and `fov3d.scene.boundaries`. It loads no `cv2` and no `fov3d.scene.partition`, so the
  module is NumPy-only.

## Compatibility decisions

`joint.py` imports `_interface_edges`, `_trace_edge_components` and `extract_boundaries`
from `fov3d.scene.boundaries` and defines none of them. The Core-5 checker asserts `is`
identity for all three and checks that `joint.py` has no duplicate top-level definitions.
`build_joint_graph.__globals__["extract_boundaries"] is fov3d.scene.boundaries.extract_boundaries`.

Repository-wide consumers:
- `extract_boundaries` is used only by `build_joint_graph` (`joint.py:76`) and the Core-5
  checker.
- `joint._interface_edges` and `joint._trace_edge_components` have **no in-repo consumer**
  besides the Core-5 identity check. They exist because the contract requires the
  historical names to remain valid (see unresolved item 2).
- No production module imports any of the three names through `joint`. The checker now
  enforces this.

## Literal-extraction and dependency audit (pre-execution)

1. **Source text, not just AST.** `ast.get_source_segment` of each moved function in
   `boundaries.py` is **byte-for-byte identical** to `main`'s `joint.py`. That covers all
   5 comments, both docstrings, every annotation, and every ordering rule, diagnostic key
   and serialized string. The ASTs, including docstrings, are equal too. This is the first
   Core extraction with no dropped documentation.
2. **The rest of `joint.py` is unchanged.** All 15 remaining top-level definitions,
   including `build_joint_graph`, are source-text identical to main. `joint.py` lost
   exactly the three moved definitions.
3. **Identical global bindings.** Every module-level name the moved functions reference
   resolves in `boundaries.py` to the same object as in `main`'s `joint.py`: `Counter`,
   `defaultdict`, `np`, `chart_grid`, `head_unit_from_angles`, `BoundaryChain`,
   `BoundaryKind`, `PartitionRegion`, `RegionKind` and `Any`. With identical text, this
   makes the functions behaviorally identical by construction.
4. **No unbound names.** A `symtable` scan of `boundaries.py`, `joint.py` and the checker
   finds 0 references to names that are neither bound at module level nor builtins.
   `joint.py` has no residual use of `defaultdict`, `BoundaryChain` or `PartitionRegion`.
5. **No experiment dependency** from any `fov3d/scene/*.py` module. The checker scans
   `boundaries.py`; the Core-4 checker scans the whole package.

## Conditional-gate decision

The Core-5 diff changes only `joint.py`'s imports and adds `boundaries.py`. For each of the
12 Partition-Graph producer/evaluator entry points, a fresh process performed the tool's
own `fov3d` imports and recorded `sys.modules`:

| entry point | loads `joint` / `scene.boundaries` | gate |
|---|---|---|
| Phase-3 lift | yes / yes | B |
| Phase-4 analyzer | yes / yes (through `relations` → `joint`) | C |
| Phase-5 analyzer | no / no | D (contract-required) |
| Phase-8b proposer / evaluator | yes / yes | E / F |
| Phase-2 lift; Phase-6 proposer/evaluator; Phase-7 proposer/evaluator; Phase-8 proposer/evaluator | **no / no** | not triggered |

The probe sees only module-level imports, so an AST scan of every tracked `.py` file
covered the rest. It found:
- the importers of `joint`: `relations`, `challenge_suite`, `tools/partition_graph{3,4}_lift.py`
  and the checkers;
- the dynamic imports: `fov3d/_compat.py` (the legacy facade re-export),
  `check_fov3d_facade.py`, and checker 3's `__import__("fov3d.scene")`.

None reaches `joint` or `boundaries` from Phases 2, 6, 7 or 8. `fov3d/scene/__init__.py` is
unchanged. **Decision:** the Core-5 diff does not reach Phases 2, 6, 7 or 8, so those gates
are not required. Under the contract, the Phase-8 proposer was **not authorized and not
run**. `tools/partition_graph4_lift.py` calls the same `lift_joint_run` as Gate B, which is
how `partition-graph-4-lift` was produced.

## Mutation / fail-capability evidence

**Harness.** Each behavioral mutant is a text substitution on `boundaries.py`, and the
harness asserts the exact number of matches. The mutant is executed into `sys.modules`
and rebound into `fov3d.scene` before `joint` is imported, so `joint`'s aliases re-export
the mutant. Static/package mutants were applied to working-tree copies. The harnesses are
throw-away and not committed.

**Equivalence probe.** Every mutant that survives the checker is run against the original
on 600 random region rasters: noisy checkerboards and T-junctions, 2×2 blobs, and enclosed
interiors, with depth ties and `inf` depths. The probe compares the full `_interface_edges`
output and every `extract_boundaries` field, including exact `sphere_xyz` bytes and the
diagnostics. A mutant is equivalent only with 0/600 differing cases. The probe is
sensitive: control mutants differ in 529/600 (open start) and 363/600 (pair insertion
order).

| mutant (all ten classes you listed plus others) | proposal checker (29) | strengthened (38) |
|---|---|---|
| diagonal interface inclusion | caught | caught |
| reversed canonical pair ordering | caught | caught |
| horizontal edges enumerated before vertical | **survived** (499/600 differ) | caught |
| horizontal `p0`/`p1` swapped | **survived** (514/600) | caught |
| horizontal doubled-endpoint shift | caught | caught |
| vertical doubled-endpoint shift | caught | caught |
| open-chain start = largest degree-1 endpoint | caught | caught |
| closed-chain start = max endpoint | caught | caught |
| start ignores degree-1 endpoints (smallest endpoint) | **survived** (398/600) | caught |
| candidate edge = last instead of first | caught | caught |
| closed walk breaks on first return to start | **survived** (0/600 on rasters; differs on generic edge lists, see below) | caught |
| pair iteration in insertion (raster discovery) order | caught | caught |
| pair iteration reverse-sorted | caught | caught |
| boundary ids from `jb00001` | caught | caught |
| boundary id 4 digits | caught | caught |
| OBJECT_OBJECT when *either* region is an object | caught | caught |
| never OBJECT_OBJECT | caught | caught |
| no canonical depth orientation | caught | caught |
| inverted depth orientation | caught | caught |
| nearer vote with `<=` | **survived** (253/600) | caught |
| nearer votes swapped a/b | caught | caught |
| signed depth jumps | caught | caught |
| finite test `or` instead of `and` | **survived** (297/600) | caught |
| median → mean | **survived** (135/600) | caught |
| min/max swapped | **survived** (247/600) | caught |
| half-cell conversion offset (doubled → chart) | **survived** (537/600) | caught |
| sphere yaw/pitch axes swapped | **survived** (537/600) | caught |
| `region_pair` reversed | caught | caught |
| `region_a`/`region_b` swapped | caught | caught |
| `interface_edge_count` = points | caught | caught |
| source string changed | caught | caught |
| `closed` always False | **survived** (26/600) | caught |
| branch diagnostic `v >= 2` | caught | caught |
| branch diagnostic counts edges | caught | caught |
| walks with one edge dropped, guard on | caught (`RuntimeError`) | caught |
| walks with one edge dropped, guard off (**dropped edge without failure**) | caught | caught |
| lost-edge guard removed | **survived** | caught |

The table counts 37 non-equivalent mutants. The proposal checker caught 25/37 and the
strengthened checker catches **37/37**.

Five surviving mutants are **equivalent**, each with 0/600 differing cases:

| equivalent mutant | reason |
|---|---|
| candidate indices unsorted | `endpoint_to_edges` lists are appended in increasing edge index, so they are already sorted |
| `closed` with `len > 1` instead of `> 2` | two distinct doubled points are never equal, and a closed walk has at least 5 points |
| branch diagnostic `v > 3` instead of `v > 2` | on a 4-neighbour raster a single region pair never has vertex degree 3. If three sides of the 4-cycle around a vertex separate the pair, the cells alternate, so the fourth side does too |
| `unencoded_interface_edges` hard-coded to 0 | the value is 0 whenever the function returns |
| no `int32` coercion of `region_code` | codes are cast with `int()` before use |

Two survivors need explanation:
- **`closed walk breaks on first return to start`** is equivalent on raster-derived
  inputs. The lexicographically smallest vertex of a closed raster component can't have
  degree 4, since that needs an edge to a smaller vertex, so a walk never returns to its
  start with unused start edges. `_trace_edge_components` is a moved function over generic
  edge lists, however, and the contract lists its "exact closed-loop break condition". It
  is now tested directly on a figure-eight.
- **The lost-edge guard** is unreachable with correct tracing. It is now exercised by
  running `extract_boundaries` with a deliberately lossy tracer (contract item 10).

**Static/package mutants.** The proposal checker caught 5/7; the strengthened checker
catches 7/7:

| mutant | proposal | strengthened |
|---|---|---|
| duplicate `extract_boundaries` defined in `joint.py` | caught | caught |
| `joint` missing the `_trace_edge_components` alias | caught | caught |
| lazy `fov3d.experiments` import in `boundaries.py` | caught | caught |
| `fov3d/scene/__init__.py` eagerly imports `boundaries` | caught | caught |
| `fov3d/scene/__init__.py` eagerly imports `partition` | caught | caught |
| `boundaries.py` imports `cv2` | **survived** | caught |
| `challenge_suite` imports `extract_boundaries` through `joint` | **survived** | caught |

## Repair: Core-5 checker strengthened (`a96655e`)

This is the delegated "strengthen the Core-5 checker" scope. No existing check was changed
and no acceptance gate was touched. The nine added checks are below. Their expectations
were derived by hand from the contract's stated rules, and they pass unmodified on code
proven text-identical to main.

1. `exact horizontal edge metadata and enumeration order`. It asserts the full 4-edge list
   of the diagonal fixture: left/right edges before top/bottom, with exact doubled
   endpoints, `p0`/`p1`, cells and codes.
2. `open chain starts at smallest degree-1 endpoint, not smallest endpoint`. It uses an L
   chain whose smallest endpoint `(0,0)` is interior.
3. `closed walk continues through start while start edges remain`. It uses a figure eight
   through `(0,0)` and expects one walk over seven edges.
4. `exact sphere geometry from doubled endpoints`. The doubled endpoints
   `(1,-1),(1,1),(1,3)` map to half-cell chart coordinates, giving yaw −0.5° and pitch
   −1.5/−0.5/0.5°. `np.array_equal` compares against `head_unit_from_angles`.
5. `closed object-base loop and diagnostics`. An enclosed object cell gives one closed
   4-edge loop of 5 points, with exact attributes and diagnostics.
6. `depth-jump statistics with ties and non-finite samples`. The jumps are 1, 2, 4 and 0,
   plus one `inf` sample. Median 1.5, min 0 and max 4; votes a = 2, b = 1.
7. `dropped interface edge raises RuntimeError`. A lossy tracer is patched in and restored
   in `finally`.
8. `fresh import fov3d.scene.boundaries loads neither cv2 nor scene.partition`.
9. `no production module takes boundary extraction from joint`.

The checker went from 29 to **38** checks and runs in 0.25 s wall (Interactive class).

## Gate A — interactive

Measured at `72502e5` (proposal checker 29/0), then the whole gate again at `de972df`:

```text
compile: 3 changed Python files OK
[conceptual-core5-check] SUMMARY checked=38 failed=0
[conceptual-core4-check] SUMMARY checked=32 failed=0
[conceptual-core3-check] SUMMARY checked=27 failed=0
[conceptual-core2-check] SUMMARY checked=20 failed=0
[conceptual-core1-check] SUMMARY checked=13 failed=0
[partition-graph1-check] SUMMARY checked=13 failed=0
[partition-graph2-check] SUMMARY checked=16 failed=0
[partition-graph3-check] SUMMARY checked=20 failed=0
[partition-graph4-check] SUMMARY checked=14 failed=0
[partition-graph5-check] SUMMARY checked=12 failed=0
[partition-graph6-check] SUMMARY checked=12 failed=0
[partition-graph7-check] SUMMARY checked=12 failed=0
[partition-graph8-check] SUMMARY checked=10 failed=0
[partition-graph8b-check] SUMMARY checked=12 failed=0
[consolidation3-facade-check] SUMMARY checked=16 failed=0
[verify] 31 files tracked at baseline-classroom-oracle1-2026-09-25 are byte-identical in the working tree
[verify] SUMMARY passed=9 failed=0
[compare-golden] compared {"looks": 104, "npz_arrays_compared": 1348, "rgb_arrays_excluded": 337, "targets": 25}
[compare-golden] MISMATCHES 0
git diff --check: clean
A.5 fresh import fov3d.scene -> ['fov3d', 'fov3d.scene', 'fov3d.scene.model', 'fov3d.scene.sphere'] | cv2 False
```

The golden comparison took 9.92 s at `72502e5` and 10.03 s at `de972df`.

## Replay gates B–F

All commands were run from the repository root, in order, each to a fresh directory:

```text
B .venv/bin/python tools/partition_graph3_lift.py previews/partition-graph-2-source-full previews/conceptual-core-5-phase3-full
C .venv/bin/python tools/partition_graph4_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/conceptual-core-5-phase4-full
D .venv/bin/python tools/partition_graph5_analyze.py previews/partition-graph-2-source-full previews/partition-graph-4-lift previews/partition-graph-4-full previews/conceptual-core-5-phase5-full
E .venv/bin/python tools/partition_graph8b_propose.py previews/partition-graph-2-source-full previews/partition-graph-5-full previews/partition-graph-8-proposals previews/conceptual-core-5-phase8b-proposals
F .venv/bin/python tools/partition_graph8b_evaluate.py previews/partition-graph-2-source-full previews/partition-graph-8b-proposals previews/partition-graph-8-evaluation previews/conceptual-core-5-phase8b-evaluation
```

```text
B [partition-graph3-lift] COMPLETE {"causal_final_pairs": 86, "evidence_checks": 51, "evidence_mismatches": 0, "scene_final_pairs": 182, "states": 104}
C [partition-graph4-analyze] COMPLETE {"causal_own_support_gap": 44, "causal_ownership_cut": 42, "causal_relations": 86, "states": 104, "target_depth_checks": 51, "target_depth_mismatches": 0}
D [partition-graph5-analyze] COMPLETE {"challenge_relations": 108, "challenge_states": 41, "challenge_targets": 4, "states": 104, "target_gap_violations": 0}
E [partition-graph8b-propose] COMPLETE {"eligible_candidates": 6489, "full_phase8_parity": 25, "raw_candidates": 18469, "scenarios": 5, "states": 125, "targets": 25, "truth_used": false}
F [partition-graph8b-evaluate] COMPLETE {"full_eligible_recall": 0.9335820895522388, "full_integrated_covered": 27948, "full_integrated_residual": 1340, "scenarios": 5, "states": 125}
```

Every required COMPLETE value matches (B, D, E, F). All five lines are string-identical to
lines in earlier committed reports.

| gate | wall | accepted reference | accepted total | excluded | producer/evaluator files (fresh = accepted scope) | result | scope manifest sha256 |
|---|---|---|---|---|---|---|---|
| B Phase-3 joint lift | 22.76 s | `partition-graph-4-lift` | 419 | — | 419 | byte-identical | `7eed664047384a43f50f51940cc4ad61d602513bb1095e076adc6c083ac3cbe3` |
| C Phase-4 analyzer | 6.81 s | `partition-graph-4-full` | 425 | `demo/` 107, `demo-package-original/` 107 | 211 | byte-identical | `eca1b6ad798117de8d2de321e0ebfe6f92cb3e73a8f0b80e78e494f8a3f3cd8c` |
| D Phase-5 analyzer | 8.27 s | `partition-graph-5-full` | 225 | `demo/` 7, `demo-package-original/` 7 | 211 | byte-identical | `77f5ae3d408900c8b2428553f22a97fae60aeddef34ea1f500a78e39d07c68eb` |
| E Phase-8b proposer | 61.30 s | `partition-graph-8b-proposals` | 503 | — | 503 | byte-identical | `51a93fc464fc8ce00fc7f519ccadc25f539095be06de074788844b12ad6e7b7d` |
| F Phase-8b evaluator | 16.58 s | `partition-graph-8b-evaluation` | 19 | `demo/` 8, `demo-package-original/` 8 | 3 | byte-identical | `243133b66237523147e1a869ee5b1bf97ee28ec9d817c5c059921e9b254c5715` |

All five scope manifests equal the Core-2 through Core-4 values for the same producer or
evaluator.

**Comparison method** (as in Cores 3 and 4). Each comparison is two-sided:
1. The fresh set must **equal** the accepted set minus the declared exclusions.
2. No fresh file may lie under an excluded path.
3. Every pair must be byte-identical (`filecmp`, `shallow=False`).
4. The scope manifests must be equal. Each is computed as
   `cd DIR && LC_ALL=C find . -type f [-not -path './<excl>/*' ...] -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum`.

In every gate, `only_fresh`, `only_accepted`, `fresh_under_excluded` and `byte_diff` were
all 0. The exclusions are only the post-producer `demo/` and `demo-package-original/`
trees demonstrated in the Core-2 report.

**Accepted trees unchanged.** Per-file sha256 manifests of the 13 accepted trees were taken
before Gate B and after Gate F, and they are identical. They also equal the Core-4 closure
manifests.

## Changed-function / dependency → execution-gate coverage

| changed path | kind | exercised by | execution evidence |
|---|---|---|---|
| `fov3d/scene/boundaries.py` module (imports `head_chart`, `.model`, NumPy) | new module | A (Core-5 checker; checkers 3, 4, 5 and 8 through `joint`), B, C (load), E, F (load) | import probe; every run byte-identical |
| `_interface_edges`, `_trace_edge_components`, `extract_boundaries` | moved | A (Core-5: 38 checks; `build_joint_graph` is called by checkers 3, 4 and 5), B, E | B: `lift_joint_run` → `build_joint_graph` → `extract_boundaries` (`joint.py:76`, unconditional) for all 104 states. The Phase-3 `summary.json` records 569,730 raster = 569,730 encoded interface edges (0 unencoded), 12,050 boundary chains and 2,585 branch vertices, and 104 state files carry the 12,050 `four_neighbour_cell_side_interface` records, all byte-identical. E: `propose_phase8b` → `build_joint_graph` (`challenge_suite.py:360`, per-state loop, `states = 125`) |
| `joint.py` imports (+ `fov3d.scene.boundaries`; − `defaultdict`, `BoundaryChain`, `PartitionRegion`) | changed module dependency | A (checkers 3, 4, 5 and 8; Core-5 identity and duplicate checks), B, C (`relations` imports `joint`), E, F | as above |
| `build_joint_graph`'s `extract_boundaries` binding | changed dependency binding | B, E | `__globals__` identity; outputs byte-identical |
| `tools/dev/check_conceptual_core5.py` | new checker | A; mutation harnesses | 38/38; 37/37 behavioral and 7/7 static mutants caught |

Gate D and the Phase-8b evaluator (F) are contract parity gates. Phase 5 does not load the
changed modules, and F only loads them.

## Confirmations

- **Not moved and unchanged:**
  - the Phase-2 boundary construction in `lift.py` (`git diff` empty);
  - gap corridors and relation logic (`gap_corridor`, `corridors_for_object` in
    `joint.py`, which are source-text identical, and `relations.py`, whose `git diff` is
    empty);
  - lineage, `seen_any` replay, partition construction (`partition.py`), and benchmark
    and evaluator modules;
  - `BoundaryChain` (`model.py`).
- **Package footprint:** `fov3d/scene/__init__.py` is unchanged, and bare
  `import fov3d.scene` still loads exactly the Core-4 set (no `cv2`, `partition` or
  `boundaries`). The Core-4 checker (32/32) and Core-5 checker enforce this in fresh
  processes.
- **No scientific/runtime behavior changed.** The evidence:
  - text-identical functions with identical global bindings;
  - byte-identical Phase 3, 4, 5 and 8b producer output, and Phase-8b evaluator output;
  - identical boundary diagnostics across all 104 Phase-3 states;
  - golden `MISMATCHES 0`, and baseline 31/31.

## Repairs and deviations

1. **Checker strengthened** (`a96655e`, delegated scope). It closes 12 behavioral and 2
   static surviving mutants, as described above.
2. **Map row made precise** (`de972df`, docs only, allowed path). The proposal's
   `joint.py` row dropped the consumer detail recorded in Core 4. The row now
   distinguishes the Core-4 partition names from the Core-5 boundary names, and states
   that `_interface_edges`/`_trace_edge_components` have no in-repo consumer.
3. **Additional evidence beyond the contract.** It comprises the source-text and
   global-binding identity checks, the entry-point import probe and AST import scan, the
   equivalence probe, and the accepted-tree manifests before and after. It used throw-away
   harnesses in the session scratchpad, which are not committed.
4. Gate A was run twice, at the proposal and at the final code commit.

No other deviation. The commands, inputs, output directories and references are exactly
the contract's. No conditional gate was triggered. Code changed no production code.

## Unresolved

1. **Two boundary lineages.** Phase 2 (`lift.py`) and Phase 3 (`fov3d.scene.boundaries`)
   still build `BoundaryChain`s independently. Unifying them is a scientific/structural
   question outside Core 5, as the contract states.
2. **Consumerless aliases.** `joint._interface_edges` and `joint._trace_edge_components`
   are kept only by the contract's compatibility rule. Nothing in the repository reads
   them except the Core-5 identity check. This parallels the Core-2 alias item, and
   keeping or removing them is Luiz and Chat's call.
3. **Private names as conceptual API.** `fov3d.scene.boundaries` exports two
   underscore-prefixed names (`_interface_edges`, `_trace_edge_components`) that the
   checker, and potentially future relation code, calls directly. A later API step could
   give them public names; that would be a deliberate rename, not part of this literal
   extraction.
4. **Raster-only invariants.** The equivalence probe showed that two tracing rules (the
   closed-walk break condition and the `v > 2` branch threshold) cannot be distinguished
   on 4-neighbour rasters. They matter only for generic edge lists. This is worth
   recording if `_trace_edge_components` is ever reused beyond raster interfaces.
5. The Core-4 items (the `joint.py` import `ObjectHypothesis` is now unused, dropped
   Core-3/Core-4 docstrings) and the Core-3/Core-2 items are carried over unchanged.

## Recommendation (Conceptual Core 6 only)

Map item 5, bounded to **gap-corridor topology**. Move `gap_corridor` and
`corridors_for_object`, with their only helpers `_component_boundary` and `_line_cells`,
out of `joint.py` into a scene-level relation module, for example `fov3d.scene.corridors`.

Measured repository audit:
- the four functions are used only inside `joint.py`, by `lift_joint_run` (`joint.py:489`,
  `joint.py:542`), and by checkers 3 and 4;
- `relations.py` does not import them; Phase 4 consumes corridors only through the saved
  lift outputs.

They operate on the scene graph and state rasters plus an explicit `seen` evidence mask.
That mask must stay a parameter and not become a coupling to controller replay.

Leave the following untouched:
- Phase-4 ownership-cut/own-support-gap classification and `FineEvidence` (`relations.py`);
- lineage and `seen_any` replay;
- Phase-2 boundaries;
- benchmark policy.

Gates:
- the Phase-3 lift against `partition-graph-4-lift`;
- the Phase-4 and Phase-5 analyzers;
- the Phase-8b proposer and evaluator;
- Phases 2, 6, 7 and 8 only if the import probe shows the diff reaches them.

Keep the text-level literal-extraction audit, the import probe and the mutation plus
equivalence harness as standard practice.

## Success marker

    CONCEPTUAL_CORE5_BOUNDARY_EXTRACTION_PRESERVES_BEHAVIOR
