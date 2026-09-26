# Migration Conceptual Core 1 — evaluator closure report (2026-09-26)

Executed by Claude Code on the Ubuntu workstation against the committed contract
`docs/migration-conceptual-core-1-closure.md`. Every number below is **MEASURED** from the
command shown.

## Provenance

| item | value |
|---|---|
| branch | `migration/conceptual-core-1` |
| starting head | `3150b52f8567eef35b6e55ad55ed7f5527f95d27` ("Define conceptual core 1 evaluator closure") |
| implementation under test | unchanged since `bef2d0c`; last measured report `0b742a6` |
| final head | the commit that adds this report (no other file changes) |

## Luiz decision recorded during execution

Gate 1's evaluator output was byte-identical, but the accepted evaluation tree also holds
demo artifacts that the evaluator never writes. The contract's literal rule ("identical
relative file list", exception only for "harmless serialization metadata") therefore
required a stop before Gate 2. The decision went to Luiz, who gave this **explicit
scoping clarification under `CLAUDE.md`**:

> For evaluator parity, compare the complete set of files produced by the fresh evaluator
> against the corresponding files in the accepted evaluation tree. Files proven not to be
> evaluator outputs are outside this parity comparison. For Phase 8, this explicitly
> excludes `demo/` and `demo-package-original/` and any files beneath those directories.
> Requirements remain strict within evaluator scope: every fresh evaluator file must exist
> at the corresponding path in the accepted tree; every corresponding file must be
> byte-identical; no evaluator-produced accepted file may be silently omitted; record
> counts, exact excluded paths and why each is known not to be evaluator output; do not
> modify either tree. Apply the same principle to Phase 8b. No code or scientific behavior
> change is authorized.

Every comparison below follows that rule. Within scope, the check is two-sided: the fresh
file set must **equal** the accepted set minus the excluded paths.

## Inputs

All accepted inputs were present:

| input | files |
|---|---|
| `previews/partition-graph-2-source-full` | 1122 |
| `previews/partition-graph-7-evaluation` | 321 |
| `previews/partition-graph-8-proposals` | 468 |
| `previews/partition-graph-8-evaluation` | 321 |
| `previews/partition-graph-8b-proposals` | 503 |
| `previews/partition-graph-8b-evaluation` | 19 |

Both evaluators resolve their input paths to absolute paths. The accepted JSON records
`/home/lvelho/rd/f3d-vision/previews/...` and no output path, so running from the
repository root reproduces the recorded strings. Both fresh output directories were
confirmed absent before their runs.

## Gate 1 — Phase-8 evaluator

```text
$ /usr/bin/time -f 'phase8-eval wall=%es maxrss=%MKB' \
  .venv/bin/python tools/partition_graph8_evaluate.py \
    previews/partition-graph-2-source-full \
    previews/partition-graph-8-proposals \
    previews/partition-graph-7-evaluation \
    previews/conceptual-core-1-phase8-evaluation
[partition-graph8-evaluate] COMPLETE {"cross_target_gain": 61538, "final_integrated_covered": 27948, "final_integrated_residual": 1340, "historical_state_misses": 101824, "integration_gain": 61557, "own_target_retention_gain": 19, "residual_candidate_recall": 0.955472222912062, "residual_state_misses": 40267, "states": 104}
phase8-eval wall=122.60s maxrss=599188KB
```

All nine COMPLETE values equal the contract.

| tree comparison | value |
|---|---|
| fresh evaluator files | **107**: 104 state NPZ, plus `state-evaluation.json`, `region-evaluation.json`, `summary.json` |
| accepted tree total | 321 |
| excluded (not evaluator output) | 214: `demo/` 107, `demo-package-original/` 107 |
| accepted evaluator-scope files | **107** |
| relative file lists (evaluator scope) | identical, both ways; no fresh file under an excluded path |
| contents | **byte-identical**: equal per-file sha256 manifests, and `cmp` clean on all 107 pairs |
| evaluator-scope manifest sha256 | `01c8d253f5ea8698e8df290b7090f299d2fb462c6c40a0fdb04bdc7611525f7d` (both trees) |

## Gate 2 — Phase-8b evaluator

Run only after Gate 1 passed under the recorded scope.

```text
$ /usr/bin/time -f 'phase8b-eval wall=%es maxrss=%MKB' \
  .venv/bin/python tools/partition_graph8b_evaluate.py \
    previews/partition-graph-2-source-full \
    previews/partition-graph-8b-proposals \
    previews/partition-graph-8-evaluation \
    previews/conceptual-core-1-phase8b-evaluation
[partition-graph8b-evaluate] COMPLETE {"full_eligible_recall": 0.9335820895522388, "full_integrated_covered": 27948, "full_integrated_residual": 1340, "scenarios": 5, "states": 125}
phase8b-eval wall=16.47s maxrss=352260KB
```

All five COMPLETE values equal the contract.

| tree comparison | value |
|---|---|
| fresh evaluator files | **3**: `scenario-evaluation.json`, `state-evaluation.json`, `summary.json` |
| accepted tree total | 19 |
| excluded (not evaluator output) | 16: `demo/` 8, `demo-package-original/` 8 |
| accepted evaluator-scope files | **3** |
| relative file lists (evaluator scope) | identical, both ways; no fresh file under an excluded path |
| contents | **byte-identical**: equal per-file sha256 manifests, and `cmp` clean on all 3 pairs |
| evaluator-scope manifest sha256 | `243133b66237523147e1a869ee5b1bf97ee28ec9d817c5c059921e9b254c5715` (both trees) |

## Excluded paths and why they are not evaluator output

| path | evidence |
|---|---|
| `previews/partition-graph-8-evaluation/demo/` | Written by `tools/partition_graph8_demo.py`, whose `out_dir` defaults to `<evaluation_dir>/demo` (`out=Path(a.out_dir or (ev/"demo"))`). The Phase-8 report ("Demo inspection") documents it as the demo output. |
| `previews/partition-graph-8-evaluation/demo-package-original/` | The Phase-8 report says: "The package demo is kept at `previews/partition-graph-8-evaluation/demo-package-original/`". It is a retained copy of the pre-fix package demo. |
| `previews/partition-graph-8b-evaluation/demo/` | Written by `tools/partition_graph8b_demo.py` (explicit `out_dir` argument). The Phase-8b report ("Demo inspection") documents it as the demo output. |
| `previews/partition-graph-8b-evaluation/demo-package-original/` | The Phase-8b report says: "The package demo, with only the launch repair applied, is kept at `previews/partition-graph-8b-evaluation/demo-package-original/`". |

Evaluator source confirms the scope. `evaluate_phase8` writes only its per-state NPZ files
and `state-evaluation.json`, `region-evaluation.json` and `summary.json`.
`evaluate_phase8b` writes only `state-evaluation.json`, `scenario-evaluation.json` and
`summary.json`. Neither creates `demo/` or `demo-package-original/`. Paths were excluded
because they are demo artifacts, never because they differed: no evaluator-scope file
differed.

## Accepted trees untouched

The sha256 manifests of `partition-graph-8-evaluation` (321 files) and
`partition-graph-8b-evaluation` (19 files) were taken before Gate 1. They are identical
after both gates. The fresh trees stay under the untracked `previews/` and were not
modified after their evaluator runs.

## Final structural sanity

```text
$ .venv/bin/python tools/dev/check_conceptual_core1.py
[conceptual-core1-check] SUMMARY checked=13 failed=0
$ git diff --check
(clean)
$ git status --short
(clean before adding this report)
```

## Repairs

None. No code, scientific, evaluator, threshold, reference-data or API change. The only
committed change is this report.

## Measurement status

Both evaluator code paths touched by Conceptual Core 1 are now **MEASURED**:

- `evaluate_phase8`, via `effective_target_geometry` from
  `fov3d.reconstruction.measurement_memory`;
- `evaluate_phase8b`, via `InstanceMeasurementMemory` routing and the mirrored
  `target_start` provenance.

Each reproduces its accepted COMPLETE summary exactly and its accepted evaluator output
byte-for-byte, under the evaluator scope Luiz approved.

## Unresolved

- Accepted evaluation trees mix evaluator output with later demo artifacts. That is why
  this closure needed a scope decision. A future contract could state the evaluator
  scope up front, or demos could be written beside the evaluation tree instead of inside
  it. This is a methodology note, not a defect in this refactor.
- The architectural questions from `docs/migration-conceptual-core-1-report.md` remain
  open: float32 storage in the conceptual snapshot, dependence on the saved-patch schema,
  and the `check_partition_graph8.py` import path.

## Success marker

    CONCEPTUAL_CORE1_EVALUATORS_MEASURED_IDENTICAL

Per the contract, the branch is ready to be accepted by fast-forwarding `main`. That
acceptance is Luiz's decision and was not performed here.
