# Migration Conceptual Core 1 — instance-keyed measurement memory extraction

## Status

Structural refactor only.

Parent accepted milestone:

    main @ c47bc40220b6ea23c54de44b699977db1362d084

Active branch:

    migration/conceptual-core-1

This step introduces no new scientific hypothesis, benchmark parameter, gaze policy,
score, ranking, controller behavior, matcher behavior, fusion rule, renderer behavior,
scene asset, or evaluation meaning.

Its purpose is to begin migration Step 5 in earnest: move code that has become a stable
project concept out of the historical Classroom/Partition-Graph experiment lineage and
into the conceptual `fov3d` core, while preserving all accepted behavior.

## Why this step

Phases 7 and 8 established a durable architectural fact:

> valid measured geometry must be routed by observed instance identity into persistent
> object/scene memory regardless of which object was active when the measurement was made.

That mechanism is no longer merely a Classroom benchmark trick. It is part of the
emerging system architecture.

Today, however, the implementation is still experiment-shaped:

- `integration.py` owns three parallel per-instance pools for XYZ and provenance;
- `challenge_suite.py` has a second geometry-only routing pool;
- `incidental.py` owns the private patch-validation helper used by both;
- Phase 8b imports `effective_target_geometry` from the Phase-8 experiment module.

That creates exactly the migration problem we want to remove: a stable architectural
mechanism is hidden inside historical phase modules and later phases depend on earlier
phase implementation details.

This step extracts only that clear mechanism.

## Architectural boundary for this step

Create one new conceptual module:

    fov3d/reconstruction/measurement_memory.py

It owns the reusable truth-free, instance-keyed memory of already measured 3-D points.

The exact internal class/function organization may be simple, but the public conceptual
surface must provide these semantics:

1. Validate/filter one saved measurement patch:
   - use `xyz_h`, `instance_id`, and `valid`;
   - retain only finite XYZ with `valid == True` and `instance_id > 0`;
   - preserve sample order.

2. Route retained samples by **observed instance id**, not active target id.

3. Retain aligned provenance for every stored point:
   - `source_global_index`;
   - `source_active_target_id`.

4. Allow an immutable/read-only snapshot for one instance containing aligned:
   - `xyz_h`;
   - `source_global_index`;
   - `source_active_target_id`.

5. Preserve duplicates and insertion order.
   This phase must not introduce deduplication, averaging, surfel fusion, confidence
   weighting, or any new object-association logic.

6. Provide the existing "effective target geometry" operation:
   historical finite map XYZ followed by measured instance XYZ, with the same exact
   ordering and dtypes needed to preserve accepted outputs.

Names may differ from the examples below if Code finds a clearly better minimal API,
but the concepts must remain explicit. A reasonable shape would be:

    MeasurementSnapshot
    InstanceMeasurementMemory
    valid_patch_measurements(...)
    effective_target_geometry(...)

Do not generalize beyond the evidence we actually have.

## Required refactor

Update the current experiment code so that this conceptual module owns the mechanism.

At minimum inspect and, where appropriate, refactor:

    fov3d/experiments/classroom_partition/incidental.py
    fov3d/experiments/classroom_partition/integration.py
    fov3d/experiments/classroom_partition/challenge_suite.py

Required outcomes:

- `integration.py` no longer owns the three parallel routing dictionaries and local
  concatenation helpers for instance-keyed measurement memory.
- `challenge_suite.py` no longer owns its own `_route_patch` / geometry-pool mechanism.
- both use the same conceptual memory implementation.
- later experiment code must not import architectural behavior from an earlier phase
  merely because that is where it was first discovered.
- the private patch-validation helper should move behind the conceptual memory API if
  repository-wide search shows no reason for it to remain experiment-owned.

Do not move `HeadEvidence` in this step. It is epistemic/chart state and belongs to a
different architectural question.

Do not move partition construction, graph topology, UNKNOWN shells, benchmark metrics,
or evaluation code in this step.

## Architectural audit deliverable

Create:

    docs/conceptual-core-map.md

This is a concise migration map, not another phase history.

For each module currently under:

    fov3d/experiments/classroom_partition/

classify its main responsibility into one or more of:

- reusable scene/geometry representation;
- persistent measurement/reconstruction memory;
- spherical partition construction;
- topology / relations;
- epistemic / observation state;
- benchmark construction;
- evaluation-only logic;
- Classroom-specific saved-run adaptation;
- historical phase scaffolding.

For each module, identify:

- what should eventually remain experiment-specific;
- what looks reusable enough to migrate later;
- which imports currently reveal cross-phase coupling.

Do **not** perform those later migrations in this step.

The map should end with a short proposed extraction order for the next 2–4 conceptual
refactors, but it must not create or implement those phases.

## New checker

Add:

    tools/dev/check_conceptual_core1.py

It must be pure host-side Python/NumPy and fail-capable.

It must at least test:

1. valid filtering:
   invalid, background/non-positive instance ids, and non-finite XYZ are rejected;

2. multi-instance routing:
   one synthetic patch routes samples into the correct instance memories;

3. provenance alignment:
   XYZ, source global index, and source active target id remain exactly aligned;

4. active-target independence:
   samples are keyed by observed instance, not by the active target;

5. duplicate/order retention:
   repeated measurements remain repeated and in deterministic insertion order;

6. snapshot isolation:
   retrieving one instance cannot expose another instance's samples;

7. effective-geometry parity:
   finite historical map points are followed by measured points exactly as Phase 8
   previously did;

8. one deliberate negative invariant:
   a malformed or provenance-inconsistent construction must raise/fail, proving the
   checker can detect a broken implementation.

The checker must print a deterministic summary and exit nonzero on failure.

## Allowed changes

This step may modify/add only what is needed for the extraction and its documentation,
normally within:

    fov3d/reconstruction/
    fov3d/experiments/classroom_partition/
    tools/dev/check_conceptual_core1.py
    docs/conceptual-core-map.md
    docs/migration-conceptual-core-1-report.md

A change elsewhere requires a clear mechanical reason in the report.

The sealed compatibility engine remains protected. Do not edit existing protected
`tools/*` runtime files, golden signatures, scene assets, or baseline contracts.

## Execution gates

Run in this order.

### A. Interactive gates

1. Compile all changed Python files.

2. Run:

       .venv/bin/python tools/dev/check_conceptual_core1.py

3. Run existing structural/phase checkers 1 through 8b.

4. Run:

       .venv/bin/python tools/dev/check_fov3d_facade.py
       scripts/verify_baseline.sh
       git diff --check

Any failure is diagnosed before modification.

### B. Batch equivalence — Phase 8b

Using the already accepted source, Phase-5 tree, and accepted Phase-8 proposal tree,
rerun only the Phase-8b proposer to a fresh output directory.

Expected scientific summary must remain exactly:

    scenarios = 5
    states = 125
    targets = 25
    full_phase8_parity = 25
    raw_candidates = 18469
    eligible_candidates = 6489
    truth_used = false

Compare the fresh proposal tree against the accepted
`previews/partition-graph-8b-proposals`.

Because the output directory itself is not part of the serialized proposal, the
proposal files should be byte-identical. If they are not, stop and identify the first
difference before proceeding.

Do not run the Phase-8b evaluator unless needed to diagnose a proposer mismatch.

### C. Authorized long equivalence gate — Phase 8

The full Phase-8 integrator previously took about 653 s, so under this project's cost
classes this is an explicitly authorized **Overnight-class** command even though it is
only on the order of minutes.

Justification: this is the one accepted long-running path whose internal measurement
routing is being structurally changed, and exact replay is the strongest evidence that
the extraction preserved behavior.

After all cheaper gates pass, rerun the Phase-8 integrator to a fresh output directory
using the same accepted source, Phase-5 tree, and Phase-7 proposal tree.

Expected summary remains exactly:

    states = 104
    targets = 25
    phase7_global_parity = 104
    target_evidence_unmapped_cells = 0
    candidate_regions = 16825
    truth_used = false

Compare the fresh proposal tree against the accepted
`previews/partition-graph-8-proposals`.

Require the same file list and byte-identical contents.

If the accepted preview trees required for B or C are missing, do not silently rebuild
upstream phases. Report the missing prerequisite and stop for a decision.

## Golden baseline

This refactor does not touch the sealed runtime path, but the accepted behavioral
baseline remains a guardrail.

After the structural gates, run at least:

    scripts/compare_golden.sh previews/partition-graph-2-source-full

Expected:

    [compare-golden] MISMATCHES 0

A fresh Blender/GPU smoke is not required unless another gate gives reason to suspect
the sealed runtime path changed.

## Acceptance

This step passes only if all of the following hold:

- the architectural audit is committed;
- one conceptual instance-keyed measurement-memory implementation exists outside the
  Classroom experiment package;
- Phase 8 and Phase 8b use that implementation rather than duplicated routing pools;
- no new scientific behavior or parameter is introduced;
- duplicates and insertion order remain preserved;
- instance identity remains inherited from the accepted Oracle run;
- no new deduplication/fusion/object-association semantics appear;
- the new fail-capable checker passes;
- existing checkers 1–8b pass;
- facade and baseline verification pass;
- golden comparison remains `MISMATCHES 0`;
- fresh Phase-8 proposal output is byte-identical to accepted Phase 8;
- fresh Phase-8b proposal output is byte-identical to accepted Phase 8b;
- protected baseline files and scene assets remain untouched;
- `git diff --check` is clean.

If exact Phase-8 or Phase-8b parity fails, this is **not** a refactor success. Diagnose
and repair only within the delegated structural scope; do not change acceptance
criteria, thresholds, or stored reference outputs.

## Permitted fixes

Claude Code may make minimal implementation repairs required to satisfy this contract,
provided they remain inside the extraction boundary above.

It may not:

- alter scientific constants;
- alter evaluation semantics;
- change chart resolution, fusion radius, shells, eligibility threshold, budgets, or
  candidate definitions;
- edit the accepted proposal/evaluation trees;
- edit golden signatures;
- change controller, matcher, renderer, fusion, gaze, termination, or scene behavior;
- expand the refactor into partition/topology/attention work.

If satisfying parity appears to require any of those, stop and return the decision to
Luiz and Chat.

## Report

Commit:

    docs/migration-conceptual-core-1-report.md

It must include:

- branch and exact commit provenance;
- files changed;
- the final conceptual API;
- the architectural classification summary;
- checker summary lines;
- existing checker/facade/baseline/golden results;
- Phase-8 fresh replay command, runtime, summary, and exact-tree comparison;
- Phase-8b fresh replay command, runtime, summary, and exact-tree comparison;
- any deviations or repairs;
- confirmation that no scientific/runtime baseline behavior changed;
- unresolved architectural questions;
- a bounded recommendation for the next refactor only.

Success marker:

    CONCEPTUAL_CORE1_REFACTOR_PRESERVES_BEHAVIOR
