# Chat Handoff

## Accepted main

    main @ 657388c558433df302bcf324db5c798afc08f659

`origin/main` is fast-forwarded to the docs-only acceptance commit that adds this entry, whose
parent is `657388c` (the Controller-01A report commit).

Accepted milestones:
- **Controller-01A terminal blocked-state audit**, accepted at `657388c` (a valid read-only audit):

      CONTROLLER01A_TERMINAL_AUDIT_ACCEPTED

  The accepted result is `CONTROLLER01A_FINAL_REPROBE_ACTIONABLE`.
- **Integrated Foveal Controller 01**, accepted at `e3bf5e0` (implementation and measured
  scientific result):

      INTEGRATED_FOVEAL_CONTROLLER01_ACCEPTED

  The implementation marker `CONTROLLER01_IMPLEMENTATION_CHECKS_PASS` is accepted. Global
  quiescence was **not** reached, and the global-quiescence marker was not emitted. The
  accepted scientific outcome is `INCOMPLETE`. That is a measured scientific result, not an
  implementation failure.
- **Repository Stage Transition 1**, accepted at `b12bdef`. It is structural only and
  changes no scientific behavior:

      REPOSITORY_STAGE_TRANSITION_1_PRESERVES_SCIENTIFIC_BEHAVIOR

- **Conceptual Core 14** remains the accepted **scientific** milestone:
  `296001e8683ba0b1ad62642811d3dea0e84b6566`. The conceptual-core migration **pauses** here.

## Working arrangement

- Luiz is the scientific and acceptance authority.
- Chat is the architecture, specification and review surface. **Its GitHub connection is
  read-only**: it inspects, searches and reviews, and it does not push commits, branches,
  updates or pull requests. For each substantial handoff it prepares a self-contained
  Claude Code prompt, which Luiz gives to Claude Code.
- Claude Code is the **repository-mutation and execution surface**. It commits the durable
  contract before substantial execution. It performs every repository mutation and every
  measured execution in dedicated isolated git worktrees, under the branch/HEAD/clean-tree
  guard, never by switching branches in the shared `/home/lvelho/rd/f3d-vision` checkout.
- GitHub is the durable source of truth.
- Result rules (`CLAUDE.md`):
  - an executed scientific/behavioral step must produce an **inspectable visual** and a
    **measurable result**, together with its **checks** and a **short summary**;
  - pure architectural/design steps may instead produce a **reviewed
    specification/contract** and a **short summary**;
  - structural/refactoring steps need machine-checkable preservation evidence.
- New contracts and reports follow `docs/<stage>/<phase>-contract.md` and
  `docs/<stage>/<phase>-report.md`.
- Migrate behavior first, redesign structure second, and answer one causal question per
  Core. Cores 12, 13 and 14 were the three intentional redesign Cores: the simplest
  falsifiable redesign, preserving every accepted historical observable and separating one
  concept at a time. The migration pauses after Core 14; no Core 15 is started
  automatically.

## Repository Stage Transition 1 (accepted at `b12bdef`)

`origin/main` was fast-forwarded `330577f → b12bdef` with a plain, non-forced push.

Record:
- contract: `docs/repository/repository-transition-1-contract.md`, including its
  inventory-resolved clarification;
- report: `docs/repository/repository-transition-1-report.md`;
- move map: `docs/repository/repository-transition-1-moves.json`.

What changed:
- `docs/` and `tools/` are organized by stage/topic:
  - `docs/{architecture,baseline,classroom-oracle,consolidation,conceptual-core,methodology,partition-graph,repository}/`,
    with `docs/chat-handoff.md` as the fixed top-level entry point;
  - `tools/{baseline,classroom_oracle,conceptual_core,consolidation,partition_graph,repository}/`.
- The `tools/` root is exactly the 16-module sealed compatibility/runtime closure, the
  `mappings[].legacy` set of `docs/consolidation/consolidation-3-layout.json`.
  `tools/dev/` is gone.
- `README.md` now summarizes the migration and the Integrated Foveal Controller stage.
- `CLAUDE.md` now defines Chat's GitHub role as read-only and Claude Code as the
  repository-mutation/execution surface. It states the result rules above and the current
  project stage.
- `scripts/verify_baseline.sh`: the step `baseline-files-accounted`
  (`tools/baseline/check_baseline_files.py`) is relocation-aware. It accounts for the 31
  baseline-tag files as 22 unchanged, 4 pure relocations, 4 declared-repaired relocations
  and 1 declared replacement (README). Historical baseline byte/path identity is not the
  current layout.
- `tools/repository/check_repository_layout.py` checks the layout.
- Historical reports keep their verbatim pre-transition commands and paths; the move map
  translates them.

Evidence (measured; report):
- `fov3d/`, the 16 sealed root modules, `tests/` and `scenes/` were unchanged (0 bytes vs
  `330577f`);
- the applicable Conceptual-Core checks (Cores 1–10 and 14) and Partition-Graph checks
  (1–8b) passed;
- facade 16/16; Classroom-Oracle 12/12; `verify_baseline` 9/9;
- golden `MISMATCHES 0`;
- the 13 accepted reference trees were unchanged;
- the layout checker passed 487/487 and caught 22/22 mutations.

## Integrated Foveal Controller 01 (accepted at `e3bf5e0`)

Luiz and Chat accepted the implementation, the measured scientific result (explicitly as
`INCOMPLETE`, not global quiescence) and the layout-checker repair `baf3fed`.

Record (branch `controller/controller-01`, base `c5f6be6`):
- contract: `docs/controller/controller-01-state-action-contract.md` (`4233a55`);
- report: `docs/controller/controller-01-state-action-report.md` (`e3bf5e0`);
- code: `fov3d/control/integrated.py` (reusable state/action concepts, the deterministic
  retain/switch/stop scheduler, the generic closed loop, the target-relative view E_t(i), the
  truth firewall) and `fov3d/experiments/classroom_oracle/controller01.py` (the Classroom
  adapter/executable);
- checks: `tools/controller/check_controller01.py`; visuals: `tools/controller/plot_controller01.py`.

Accepted measured result of the one full run (at `5b66e59`):

| quantity | value |
|---|---|
| localized / initialized | 25 / 25 |
| observations | 141 |
| switches / attention bouts | 26 / 27 |
| natural reactivations | 2 (109 by 110's look; 178 by 224's look; both serviced and quiet again) |
| QUIET at termination | 24 |
| blocked | 210 `wall.008`, `BLOCKED:watchdog`: at the inherited 24-look watchdog its accepted local policy still proposed an FSG6f look |
| terminal | `INCOMPLETE(localized_objects_blocked)` |
| descriptive coverage (after control) | 0.9833720295001366 |

Preserved full run:

    /home/lvelho/temp/previews-2026.09.28/controller-01-full

It was copied with `rsync -a` and verified file by file: 1,678/1,678 sha256 identical to the source,
including `controller-attention-timeline.png` and `controller-gaze-chart.png`. The report-recorded
hashes are `manifest.json` `d293a98f…`, `actions.json` `12cdbe4d…` and `evaluation.json`
`76cb1e5d…`. The smoke runs are plumbing artifacts and were not archived.

## Controller-01A terminal blocked-state audit (accepted at `657388c`)

Luiz and Chat accept Controller-01A as a **valid read-only audit** of the preserved
Controller-01 run.

Record (branch `controller/controller-01a-terminal-audit`, base `e659ff1`):
- contract: `docs/controller/controller-01a-terminal-audit-contract.md` (`e53c59f`);
- report: `docs/controller/controller-01a-terminal-audit-report.md` (`657388c`);
- tool: `tools/controller/check_controller01.py --terminal-reprobe RUN --object 210`.

Accepted result:

    CONTROLLER01A_FINAL_REPROBE_ACTIONABLE

- **Watchdog, step 101.** The reconstruction reproduced the saved probe exactly: 24 own looks,
  effective geometry 1,748,902, FSG6f `continue`, 58 OPEN, 1 candidate, proposed gaze
  `[7.6, 18.2]`.
- **Terminal scene state.** 190,011 later causal measurements of 210 had arrived, all from other
  targets. Effective geometry was 1,938,913, and the active map was unchanged at 163,944 surfels.
  FSG6f still continued, with 52 OPEN, 1 candidate and the same gaze `[7.6, 18.2]`.
- Truth firewall: 0 violations. Reconstruction exact. 10/10 negative controls caught.

Accepted interpretation:
- later cross-target memory did **not** make 210 quiet;
- therefore sticky BLOCKED semantics are **not** the explanation for Controller-01's failure to
  reach global quiescence;
- the unresolved behavior is genuinely inside the accepted local continuation/stopping behavior;
- this does **not** yet prescribe a new stopping policy.

## Accepted scientific / architectural state

The sealed scientific behavior is unchanged through Conceptual Cores 1–14 and Repository
Stage Transition 1.

Conceptual ownership established so far:

- `fov3d.reconstruction.measurement_memory`
  - valid patch measurement filtering
  - append-only instance-keyed measured 3-D memory
  - effective target geometry composition
- `fov3d.geometry.head_chart`
  - fixed-head yaw/pitch mapping and chart indexing
- `fov3d.reconstruction.association`
  - canonical 12-mm surface association radius
- `fov3d.epistemic.head_memory`
  - persistent head-centered epistemic memory
  - `HeadEvidence`
  - `add_head_patch`
- `fov3d.scene.partition`
  - `SupportLayer`
  - `support_depth_from_map`
  - `joint_owner`
  - `label_joint_regions`
- `fov3d.scene.boundaries`
  - `_interface_edges`
  - `_trace_edge_components`
  - `extract_boundaries`
- `fov3d.scene.corridors`
  - Core 6, gap-corridor geometry: `_component_boundary`, `_line_cells`, `gap_corridor`,
    `corridors_for_object`
  - Core 10, corridor relation origin: `_region_code`, `_own_labels`,
    `_joint_region_own_component`, `relation_origin`
- `fov3d.scene.lineage` (Core 7)
  - `_lineage`
  - `_target_component_raster`
- `fov3d.scene.state_validation` (Core 8)
  - `attach_state_region_codes`, which keeps its compatibility name; the rename is
    deferred
- `fov3d.scene.relations` (Core 9)
  - the NumPy-only boundary-depth-order module: `_region_object`, `_weighted_quantile`,
    `boundary_depth_order`
- `fov3d.epistemic.partition` (Core 11; candidate-free since Core 12)
  - the intrinsic epistemic partition: `REGION_KIND`, `REGION_KIND_BY_CODE`,
    `_component_labels`, `_distance_to_target`, `_touches_edge`, `_centroid_angles`,
    `_angular_distance_deg`, `_region_interfaces`, `build_epistemic_partition`
  - since Core 12 it no longer owns candidate semantics (`CANDIDATE_KINDS`,
    `region["candidate"]`, `diag["candidate_region_count"]`)
  - since Core 13 it no longer depends on the experiment's target schedule
    (`all_target_ids`) nor emits `reconstruction_status`; `surface_source` stays intrinsic
    causal evidence provenance
  - since Core 14 it no longer takes the fixation/action history (`gazes_deg`) nor emits
    `min_distance_to_historical_gaze_deg`; `_angular_distance_deg` stays as a generic helper
  - it is therefore independent of the candidate interpretation, the experiment's future
    target schedule and the fixation/action history; it depends only on accumulated
    evidence and the chart (it is still relative to one designated target)
  - imported explicitly and OpenCV-dependent; `fov3d/epistemic/__init__.py` is unchanged,
    so a bare `import fov3d.epistemic` stays OpenCV-free
- `fov3d/experiments/classroom_partition/candidate_policy.py` (Core 12, experiment-side)
  - the historical `OTHER_SURFACE`/`UNKNOWN` → candidate interpretation:
    `CANDIDATE_KINDS`, `annotate_candidate_partition`, `build_candidate_partition`, which
    re-creates the accepted candidate view exactly
  - it composes on `run_context`; the full historical stack is
    intrinsic → gaze context → run context → candidate annotation
- `fov3d/experiments/classroom_partition/run_context.py` (Core 13, experiment-side)
  - owns `reconstruction_status`: `annotate_reconstruction_status`,
    `build_run_context_partition` (`mapped_now`/`targeted_later`/`never_targeted` from
    `mapped_cells` and `all_target_ids`); since Core 14 it composes on `gaze_context`
- `fov3d/experiments/classroom_partition/gaze_context.py` (Core 14, experiment-side)
  - owns the historical target-local gaze descriptor: `annotate_gaze_context`,
    `build_gaze_context_partition` (`min_distance_to_historical_gaze_deg` from the region
    centroid and the producers' target-local gaze list)

The Phase-4 adapter `fov3d/experiments/classroom_partition/relations.py` keeps identity
imports of the Core-9 and Core-10 names; `annotate_corridor` resolves the scene functions.
`fov3d/experiments/classroom_partition/benchmark.py` keeps the historical API:
`benchmark.CANDIDATE_KINDS` is the policy constant and `benchmark.build_epistemic_partition`
is an alias of `build_candidate_partition`. Phases 6, 7, 8 and 8b call
`build_candidate_partition` explicitly; Phase 8b keeps its own, independent
`candidate_raw`/`eligible_candidate` interpretation.

`fov3d.scene` lazily re-exports the four scene-partition names, so a bare
`import fov3d.scene` stays OpenCV-free. The modules `boundaries`, `corridors`, `lineage`,
`state_validation` and `relations` are imported explicitly. `corridors` needs `cv2`; the
others are NumPy-only.

Conceptual Core 14 was accepted at `296001e8683ba0b1ad62642811d3dea0e84b6566` with:

    CONCEPTUAL_CORE14_GAZE_CONTEXT_SEPARATION_PRESERVES_BEHAVIOR

The evidence, from `docs/conceptual-core/migration-conceptual-core-14-report.md`, includes:
- the intrinsic output is accepted Core 13 minus only the gaze-distance field; `gaze_context`,
  `run_context` and `candidate_policy` re-create the accepted outputs exactly, and the
  historical producers (with their target-local gaze selection) are unchanged;
- the Core-14 checker passes 64/64; it caught 48/48 dynamic and 22/22 static mutants;
- the random-state differential agreed on 10,000/10,000 states;
- all 8 Phase-6/7/8/8b products are byte-identical;
- the sealed baseline is 31/31 and the golden comparison reports `MISMATCHES 0`;
- the 13 accepted reference trees are unchanged.

The Core-14 report ends with a read-only **Controller-readiness boundary** (intrinsic
information available, separated historical layers, what is not implemented, and the
observation that the intrinsic partition is still target-relative).

Earlier accepted Cores (1–13) are summarised in their reports. The cleanup of
`own_support_labels` versus `_own_labels`, and of `component_lineage` versus
`fov3d.scene.lineage._lineage`, remains **deferred**.

## Active next step

**The conceptual-core migration remains paused after Core 14.** Do not create Core 15
automatically and do not create a new migration branch.

Controller-01A is accepted. The next activities are:
- the official preview/visual lifecycle policy;
- a visual retrofit of Controller-01 (visualization of accepted measurements);
- **Controller-01B**, one bounded scientific step: exactly **one** post-watchdog continuation
  look for object 210, the observation still requested by the unchanged accepted local policy.
  It changes no threshold, scheduler, watchdog or stopping rule, and it is **not** Controller-02.

## Decision-critical open items

1. Controller design is led by Luiz with Chat. Controller-01 reuses the accepted local policy
   unchanged. Open questions from its report:
   - the adequacy of the 24-look watchdog under effective geometry;
   - target-local versus global observation evidence for the Cyclopean handoff (both natural
     reactivations came through it);
   - the service latency of reactivated objects under the cyclic order;
   - sticky BLOCKED;
   - the metric scope (active fused map versus effective geometry);
   - measured-but-unlocated instances;
   - a target-neutral scene-level epistemic formulation.
2. Still not designed or implemented: candidate ranking/scoring, a new fixation policy,
   vergence/focus action, inhibition of return, gaze recency/decay, the budget/quality
   trade-off, a moving head, semantic decisions.
3. Representation observation for the design: the intrinsic partition is still relative to one
   designated target (`target_id`, `target_support`, the target kinds and target distances).
4. Deferred historical cleanups (not to be started automatically):
   - the target-relative `HeadEvidence` placement;
   - the Phase-5 `reconstruction_status` duplication;
   - the `_own_labels`/`own_support_labels` and `component_lineage`/`_lineage` cleanup;
   - the `attach_state_region_codes` rename;
   - the consumerless aliases;
   - the three private `_insert_after` copies;
   - the Phase-2 and Phase-3 boundary lineages.
5. Open items from Repository Stage Transition 1 (see its report):
   - `fov3d/__init__.py`'s docstring still names pre-transition paths. Fixing it is a
     text-only `fov3d/` change and needs an explicit decision.
   - `docs/conceptual-core/conceptual-core-map.md` keeps the stale headings "Proposed
     Conceptual Core 3 extraction" and "Proposed later extraction order".
   - Reference-tree location: the shared checkout's `previews/` is empty. The accepted trees,
     now including `controller-01-full`, are at `/home/lvelho/temp/previews-2026.09.28`, and
     gates that name `previews/…` need that location linked.
