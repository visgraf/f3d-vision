# Migration Conceptual Core 1 — evaluator closure

## Status

Measurement-only closure of the already implemented Conceptual Core 1 refactor.

Active branch:

    migration/conceptual-core-1

Current measured implementation/report head before this closure:

    0b742a6d339363c8b58e4f01b0ff7efaebbaeb53

Parent accepted milestone remains:

    main @ c47bc40220b6ea23c54de44b699977db1362d084

The implementation is already strongly validated: the new checker, existing checkers,
facade, baseline verification, golden comparator, and fresh Phase-8 / Phase-8b proposer
replays all passed, with both proposer trees byte-identical to their accepted references.

One gap remains: the refactor also changed code paths reached by the Phase-8 and Phase-8b
**evaluators**, but the Conceptual Core 1 contract deliberately did not execute those
evaluators after proposer parity succeeded.

This closure converts those evaluator paths from PROPOSED to MEASURED before the branch
is accepted into `main`.

## Scientific boundary

No new implementation, scientific hypothesis, metric, threshold, benchmark setting, or
architecture is introduced here.

Do not modify:

- measurement-memory semantics;
- evaluation semantics;
- accepted proposal/evaluation trees;
- chart resolution or 12 mm radius;
- Phase-8b budgets, UNKNOWN shells, or candidate eligibility;
- golden signatures;
- controller, matcher, fusion, renderer, gaze, termination, or scene behavior.

The normal expected outcome is **zero code changes**.

## Inputs

Use the accepted proposal/evaluation inputs, not the fresh Conceptual-Core-1 proposer
trees. This isolates the evaluator code path and also preserves the path strings recorded
inside the accepted JSON outputs.

Expected accepted inputs under `previews/`:

    partition-graph-2-source-full
    partition-graph-7-evaluation
    partition-graph-8-proposals
    partition-graph-8-evaluation
    partition-graph-8b-proposals
    partition-graph-8b-evaluation

If any required accepted input is missing, stop and report it. Do not silently rebuild an
upstream phase.

## Gate 1 — Phase-8 evaluator

Run to a fresh output directory:

    previews/conceptual-core-1-phase8-evaluation

using:

    tools/partition_graph8_evaluate.py

with accepted inputs:

    source_run           = previews/partition-graph-2-source-full
    proposal_dir         = previews/partition-graph-8-proposals
    phase7_evaluation    = previews/partition-graph-7-evaluation

The COMPLETE summary must be exactly:

    states = 104
    historical_state_misses = 101824
    cross_target_gain = 61538
    own_target_retention_gain = 19
    integration_gain = 61557
    residual_state_misses = 40267
    final_integrated_covered = 27948
    final_integrated_residual = 1340
    residual_candidate_recall = 0.955472222912062

Then compare the fresh output tree with:

    previews/partition-graph-8-evaluation

Require:

- identical relative file list;
- byte-identical contents.

If not identical, identify the first differing file and stop before Phase 8b unless the
difference is proven to be harmless serialization metadata outside the contract. Do not
change the reference tree.

## Gate 2 — Phase-8b evaluator

Only after Gate 1 passes, run to:

    previews/conceptual-core-1-phase8b-evaluation

using:

    tools/partition_graph8b_evaluate.py

with accepted inputs:

    source_run          = previews/partition-graph-2-source-full
    proposal_dir        = previews/partition-graph-8b-proposals
    phase8_evaluation   = previews/partition-graph-8-evaluation

The COMPLETE summary must be exactly:

    scenarios = 5
    states = 125
    full_integrated_covered = 27948
    full_integrated_residual = 1340
    full_eligible_recall = 0.9335820895522388

Then compare the fresh output tree with:

    previews/partition-graph-8b-evaluation

Require:

- identical relative file list;
- byte-identical contents.

## Final structural sanity

After both evaluators pass:

    .venv/bin/python tools/dev/check_conceptual_core1.py
    git diff --check
    git status --short

No Blender/GPU run is required. No new golden run is required because the sealed runtime
was already verified in the main Conceptual Core 1 report and this closure changes no
runtime code.

## Repairs

Default: no fix.

If an evaluator fails or differs:

1. diagnose;
2. record the first concrete discrepancy;
3. do not alter accepted outputs or acceptance criteria;
4. make no code change unless the cause is clearly a mechanical defect inside the
   already delegated Conceptual Core 1 extraction boundary.

Any change to science, evaluator semantics, thresholds, reference data, or the conceptual
API requires a decision from Luiz and Chat.

## Report

Commit:

    docs/migration-conceptual-core-1-closure-report.md

Include:

- branch and starting/final commit ids;
- exact evaluator commands;
- runtimes;
- COMPLETE summary lines;
- file counts for fresh and accepted trees;
- exact-tree comparison result;
- final checker and worktree status;
- repairs, if any;
- whether both evaluator paths are now MEASURED.

Required success marker:

    CONCEPTUAL_CORE1_EVALUATORS_MEASURED_IDENTICAL

If that marker is justified, the branch is ready to be accepted by fast-forwarding
`main`.
