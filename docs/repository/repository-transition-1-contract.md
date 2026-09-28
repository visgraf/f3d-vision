# Repository Transition 1: repository-stage transition contract

## Status

This is a **repository-stage transition**. It is **not** Conceptual Core 15 and **not** a
scientific or behavioral experiment. It reorganizes the repository structurally, preparing
it for the next project stage, the **Integrated Foveal Controller**. No controller is
designed or implemented here.

    base                         origin/main @ 330577f176e507c3d36c5f2606692fc735bc6def
                                 (Update Chat Handoff for accepted Core 14)
    accepted scientific milestone Conceptual Core 14 @ 296001e8683ba0b1ad62642811d3dea0e84b6566
                                 (a parent of the base)
    branch                       stage/repository-transition-1, created from the base
    execution                    one dedicated isolated git worktree; the shared checkout
                                 /home/lvelho/rd/f3d-vision is neither switched nor mutated
    marker                       REPOSITORY_STAGE_TRANSITION_1_PRESERVES_SCIENTIFIC_BEHAVIOR

Design provenance: Luiz and Chat. Luiz approved the direction. Claude Code commits this
contract in the transition worktree **before** any production or path change, runs the
transition, and reports. Nothing is merged or fast-forwarded to `main`. The branch stops for
Luiz and Chat to review.

## Purpose

1. **Documentation.** Reorganize the flat `docs/` directory by stage and topic.
2. **Tools.** Reorganize the historical, orchestration and checking code under `tools/` by
   stage and topic. Deliberately leave the small sealed compatibility/runtime surface at the
   `tools/` root, and eliminate `tools/dev/`.
3. **Project entry documents.** Replace `README.md` and update `CLAUDE.md` for the new
   project stage and the current Chat ↔ Claude Code workflow.

Scientific behavior does not change. The reusable implementation under `fov3d/` stays
byte-identical to the base.

## What is changed and what is not

Changed:
- file locations under `docs/` and `tools/`, using `git mv` so history follows each file;
- the minimal mechanical path, import and link repairs that the moves require;
- the three stable wrappers in `scripts/`, where they name a moved path;
- the one path-identity step of `scripts/verify_baseline.sh` (see *Baseline verification*);
- `README.md` (replaced), `CLAUDE.md` (workflow and stage update);
- the active architecture documents (paths, and the stale Core-14 status);
- new: this contract, the report, a machine-readable move map, and a fail-capable layout
  checker.

Not changed:
- `fov3d/` (zero bytes, against the base);
- the scientific content of any retained root compatibility/runtime tool;
- `tests/` fixtures, `scenes/` manifests, the accepted reference trees under `previews/`;
- the historical baseline tag `baseline-classroom-oracle1-2026-09-25` and every other tag;
- historical contracts and reports, beyond `git mv` and link-target repairs;
- the names of historical documents and tools (renaming is not part of this transition);
- the accepted Chat Handoff, which is not replaced until Luiz accepts this transition.

## Target `docs/` hierarchy

One deliberate top-level exception, `docs/chat-handoff.md`, stays as the fixed recovery entry
point. Everything else moves into a stage/topic directory:

    docs/
    ├── chat-handoff.md
    ├── architecture/
    ├── baseline/
    ├── classroom-oracle/
    ├── consolidation/
    ├── conceptual-core/
    ├── methodology/
    ├── partition-graph/
    └── repository/

No empty controller directory is created to reserve a name. It appears with the first
controller contract. `docs/repository/` holds this transition's own files:

    docs/repository/repository-transition-1-contract.md
    docs/repository/repository-transition-1-report.md
    docs/repository/repository-transition-1-moves.json     machine-readable move map

## Naming convention for new work

Historical documents keep their existing filenames: the names are part of the record. For
new substantial work the convention is:

    docs/<stage>/<phase>-contract.md
    docs/<stage>/<phase>-report.md

For example, for the coming controller stage (not created here):

    docs/controller/controller-01-state-action-contract.md
    docs/controller/controller-01-state-action-report.md

## Target `tools/` hierarchy

`tools/dev/` is eliminated. Its contents move to their actual conceptual stage. Directory
names use Python-friendly underscores:

    tools/
    ├── baseline/
    ├── classroom_oracle/
    ├── conceptual_core/
    ├── consolidation/
    ├── partition_graph/
    ├── repository/
    └── <small sealed compatibility/runtime root surface>

No `tools/controller/` is created. No `__init__.py` is added unless actual import semantics
require it, and then the choice is documented.

### Files retained at the `tools/` root (provisional set, as specified)

    tools/bl_common.py
    tools/exr_lite.py
    tools/fsg3_surface_map.py
    tools/fsg6f_frontier.py
    tools/fsg6f_public.py
    tools/fsg_geometry.py
    tools/fsg_stereo.py
    tools/multiobject2c_policy.py
    tools/render_foveated.py
    tools/warp.py

These form the small sealed compatibility/runtime surface. Several `fov3d` facades resolve
exact `tools.*` module names, and those facades are not modified. **Stop rule:** if the
dependency inventory shows that another root tool belongs to this compatibility closure,
execution stops and documents it **before** that file is moved, and the root set is decided
explicitly.

## Exact move map (as specified)

`docs/` 60 files, `tools/` 61 files; `git mv` only.

#### `docs/baseline/` (3)

| from | to |
|---|---|
| `docs/baseline-contract.md` | `docs/baseline/baseline-contract.md` |
| `docs/legacy-provenance.md` | `docs/baseline/legacy-provenance.md` |
| `docs/migration-manifest.md` | `docs/baseline/migration-manifest.md` |

#### `docs/classroom-oracle/` (1)

| from | to |
|---|---|
| `docs/classroom-oracle-1.md` | `docs/classroom-oracle/classroom-oracle-1.md` |

#### `docs/consolidation/` (5)

| from | to |
|---|---|
| `docs/consolidation-1-report.md` | `docs/consolidation/consolidation-1-report.md` |
| `docs/consolidation-2-report.md` | `docs/consolidation/consolidation-2-report.md` |
| `docs/consolidation-3-interface-refactor.md` | `docs/consolidation/consolidation-3-interface-refactor.md` |
| `docs/consolidation-3-layout.json` | `docs/consolidation/consolidation-3-layout.json` |
| `docs/consolidation-3-report.md` | `docs/consolidation/consolidation-3-report.md` |

#### `docs/partition-graph/` (17)

| from | to |
|---|---|
| `docs/partition-graph-1.md` | `docs/partition-graph/partition-graph-1.md` |
| `docs/partition-graph-2-report.md` | `docs/partition-graph/partition-graph-2-report.md` |
| `docs/partition-graph-2.md` | `docs/partition-graph/partition-graph-2.md` |
| `docs/partition-graph-3-report.md` | `docs/partition-graph/partition-graph-3-report.md` |
| `docs/partition-graph-3.md` | `docs/partition-graph/partition-graph-3.md` |
| `docs/partition-graph-4-report.md` | `docs/partition-graph/partition-graph-4-report.md` |
| `docs/partition-graph-4.md` | `docs/partition-graph/partition-graph-4.md` |
| `docs/partition-graph-5-report.md` | `docs/partition-graph/partition-graph-5-report.md` |
| `docs/partition-graph-5.md` | `docs/partition-graph/partition-graph-5.md` |
| `docs/partition-graph-6-report.md` | `docs/partition-graph/partition-graph-6-report.md` |
| `docs/partition-graph-6.md` | `docs/partition-graph/partition-graph-6.md` |
| `docs/partition-graph-7-report.md` | `docs/partition-graph/partition-graph-7-report.md` |
| `docs/partition-graph-7.md` | `docs/partition-graph/partition-graph-7.md` |
| `docs/partition-graph-8-report.md` | `docs/partition-graph/partition-graph-8-report.md` |
| `docs/partition-graph-8.md` | `docs/partition-graph/partition-graph-8.md` |
| `docs/partition-graph-8b-report.md` | `docs/partition-graph/partition-graph-8b-report.md` |
| `docs/partition-graph-8b.md` | `docs/partition-graph/partition-graph-8b.md` |

#### `docs/conceptual-core/` (31)

| from | to |
|---|---|
| `docs/conceptual-core-map.md` | `docs/conceptual-core/conceptual-core-map.md` |
| `docs/migration-conceptual-core-1-closure-report.md` | `docs/conceptual-core/migration-conceptual-core-1-closure-report.md` |
| `docs/migration-conceptual-core-1-closure.md` | `docs/conceptual-core/migration-conceptual-core-1-closure.md` |
| `docs/migration-conceptual-core-1-report.md` | `docs/conceptual-core/migration-conceptual-core-1-report.md` |
| `docs/migration-conceptual-core-1.md` | `docs/conceptual-core/migration-conceptual-core-1.md` |
| `docs/migration-conceptual-core-10-report.md` | `docs/conceptual-core/migration-conceptual-core-10-report.md` |
| `docs/migration-conceptual-core-10.md` | `docs/conceptual-core/migration-conceptual-core-10.md` |
| `docs/migration-conceptual-core-11-report.md` | `docs/conceptual-core/migration-conceptual-core-11-report.md` |
| `docs/migration-conceptual-core-11.md` | `docs/conceptual-core/migration-conceptual-core-11.md` |
| `docs/migration-conceptual-core-12-report.md` | `docs/conceptual-core/migration-conceptual-core-12-report.md` |
| `docs/migration-conceptual-core-12.md` | `docs/conceptual-core/migration-conceptual-core-12.md` |
| `docs/migration-conceptual-core-13-report.md` | `docs/conceptual-core/migration-conceptual-core-13-report.md` |
| `docs/migration-conceptual-core-13.md` | `docs/conceptual-core/migration-conceptual-core-13.md` |
| `docs/migration-conceptual-core-14-report.md` | `docs/conceptual-core/migration-conceptual-core-14-report.md` |
| `docs/migration-conceptual-core-14.md` | `docs/conceptual-core/migration-conceptual-core-14.md` |
| `docs/migration-conceptual-core-2-report.md` | `docs/conceptual-core/migration-conceptual-core-2-report.md` |
| `docs/migration-conceptual-core-2.md` | `docs/conceptual-core/migration-conceptual-core-2.md` |
| `docs/migration-conceptual-core-3-report.md` | `docs/conceptual-core/migration-conceptual-core-3-report.md` |
| `docs/migration-conceptual-core-3.md` | `docs/conceptual-core/migration-conceptual-core-3.md` |
| `docs/migration-conceptual-core-4-report.md` | `docs/conceptual-core/migration-conceptual-core-4-report.md` |
| `docs/migration-conceptual-core-4.md` | `docs/conceptual-core/migration-conceptual-core-4.md` |
| `docs/migration-conceptual-core-5-report.md` | `docs/conceptual-core/migration-conceptual-core-5-report.md` |
| `docs/migration-conceptual-core-5.md` | `docs/conceptual-core/migration-conceptual-core-5.md` |
| `docs/migration-conceptual-core-6-report.md` | `docs/conceptual-core/migration-conceptual-core-6-report.md` |
| `docs/migration-conceptual-core-6.md` | `docs/conceptual-core/migration-conceptual-core-6.md` |
| `docs/migration-conceptual-core-7-report.md` | `docs/conceptual-core/migration-conceptual-core-7-report.md` |
| `docs/migration-conceptual-core-7.md` | `docs/conceptual-core/migration-conceptual-core-7.md` |
| `docs/migration-conceptual-core-8-report.md` | `docs/conceptual-core/migration-conceptual-core-8-report.md` |
| `docs/migration-conceptual-core-8.md` | `docs/conceptual-core/migration-conceptual-core-8.md` |
| `docs/migration-conceptual-core-9-report.md` | `docs/conceptual-core/migration-conceptual-core-9-report.md` |
| `docs/migration-conceptual-core-9.md` | `docs/conceptual-core/migration-conceptual-core-9.md` |

#### `docs/architecture/` (2)

| from | to |
|---|---|
| `docs/current-architecture-map.md` | `docs/architecture/current-architecture-map.md` |
| `docs/fov3d-api.md` | `docs/architecture/fov3d-api.md` |

#### `docs/methodology/` (1)

| from | to |
|---|---|
| `docs/methodology-test-1-report.md` | `docs/methodology/methodology-test-1-report.md` |

#### `tools/classroom_oracle/` (9)

| from | to |
|---|---|
| `tools/check_classroom_assets.py` | `tools/classroom_oracle/check_classroom_assets.py` |
| `tools/classroom_oracle1_epistemic.py` | `tools/classroom_oracle/classroom_oracle1_epistemic.py` |
| `tools/classroom_oracle1_eval.py` | `tools/classroom_oracle/classroom_oracle1_eval.py` |
| `tools/classroom_oracle1_matcher.py` | `tools/classroom_oracle/classroom_oracle1_matcher.py` |
| `tools/classroom_oracle1_public.py` | `tools/classroom_oracle/classroom_oracle1_public.py` |
| `tools/classroom_oracle1_render.py` | `tools/classroom_oracle/classroom_oracle1_render.py` |
| `tools/classroom_oracle1_run.py` | `tools/classroom_oracle/classroom_oracle1_run.py` |
| `tools/dev/check_classroom_oracle1.py` | `tools/classroom_oracle/check_classroom_oracle1.py` |
| `tools/place_eye.py` | `tools/classroom_oracle/place_eye.py` |

#### `tools/partition_graph/` (32)

| from | to |
|---|---|
| `tools/dev/apply_partition_graph4_lineage_fix.py` | `tools/partition_graph/apply_partition_graph4_lineage_fix.py` |
| `tools/dev/check_partition_graph1.py` | `tools/partition_graph/check_partition_graph1.py` |
| `tools/dev/check_partition_graph2.py` | `tools/partition_graph/check_partition_graph2.py` |
| `tools/dev/check_partition_graph3.py` | `tools/partition_graph/check_partition_graph3.py` |
| `tools/dev/check_partition_graph4.py` | `tools/partition_graph/check_partition_graph4.py` |
| `tools/dev/check_partition_graph5.py` | `tools/partition_graph/check_partition_graph5.py` |
| `tools/dev/check_partition_graph6.py` | `tools/partition_graph/check_partition_graph6.py` |
| `tools/dev/check_partition_graph7.py` | `tools/partition_graph/check_partition_graph7.py` |
| `tools/dev/check_partition_graph8.py` | `tools/partition_graph/check_partition_graph8.py` |
| `tools/dev/check_partition_graph8b.py` | `tools/partition_graph/check_partition_graph8b.py` |
| `tools/partition_graph1_demo.py` | `tools/partition_graph/partition_graph1_demo.py` |
| `tools/partition_graph2_demo.py` | `tools/partition_graph/partition_graph2_demo.py` |
| `tools/partition_graph2_lift.py` | `tools/partition_graph/partition_graph2_lift.py` |
| `tools/partition_graph3_demo.py` | `tools/partition_graph/partition_graph3_demo.py` |
| `tools/partition_graph3_lift.py` | `tools/partition_graph/partition_graph3_lift.py` |
| `tools/partition_graph4_analyze.py` | `tools/partition_graph/partition_graph4_analyze.py` |
| `tools/partition_graph4_demo.py` | `tools/partition_graph/partition_graph4_demo.py` |
| `tools/partition_graph4_lift.py` | `tools/partition_graph/partition_graph4_lift.py` |
| `tools/partition_graph5_analyze.py` | `tools/partition_graph/partition_graph5_analyze.py` |
| `tools/partition_graph5_demo.py` | `tools/partition_graph/partition_graph5_demo.py` |
| `tools/partition_graph6_demo.py` | `tools/partition_graph/partition_graph6_demo.py` |
| `tools/partition_graph6_evaluate.py` | `tools/partition_graph/partition_graph6_evaluate.py` |
| `tools/partition_graph6_propose.py` | `tools/partition_graph/partition_graph6_propose.py` |
| `tools/partition_graph7_demo.py` | `tools/partition_graph/partition_graph7_demo.py` |
| `tools/partition_graph7_evaluate.py` | `tools/partition_graph/partition_graph7_evaluate.py` |
| `tools/partition_graph7_propose.py` | `tools/partition_graph/partition_graph7_propose.py` |
| `tools/partition_graph8_demo.py` | `tools/partition_graph/partition_graph8_demo.py` |
| `tools/partition_graph8_evaluate.py` | `tools/partition_graph/partition_graph8_evaluate.py` |
| `tools/partition_graph8_integrate.py` | `tools/partition_graph/partition_graph8_integrate.py` |
| `tools/partition_graph8b_demo.py` | `tools/partition_graph/partition_graph8b_demo.py` |
| `tools/partition_graph8b_evaluate.py` | `tools/partition_graph/partition_graph8b_evaluate.py` |
| `tools/partition_graph8b_propose.py` | `tools/partition_graph/partition_graph8b_propose.py` |

#### `tools/conceptual_core/` (14)

| from | to |
|---|---|
| `tools/dev/check_conceptual_core1.py` | `tools/conceptual_core/check_conceptual_core1.py` |
| `tools/dev/check_conceptual_core10.py` | `tools/conceptual_core/check_conceptual_core10.py` |
| `tools/dev/check_conceptual_core11.py` | `tools/conceptual_core/check_conceptual_core11.py` |
| `tools/dev/check_conceptual_core12.py` | `tools/conceptual_core/check_conceptual_core12.py` |
| `tools/dev/check_conceptual_core13.py` | `tools/conceptual_core/check_conceptual_core13.py` |
| `tools/dev/check_conceptual_core14.py` | `tools/conceptual_core/check_conceptual_core14.py` |
| `tools/dev/check_conceptual_core2.py` | `tools/conceptual_core/check_conceptual_core2.py` |
| `tools/dev/check_conceptual_core3.py` | `tools/conceptual_core/check_conceptual_core3.py` |
| `tools/dev/check_conceptual_core4.py` | `tools/conceptual_core/check_conceptual_core4.py` |
| `tools/dev/check_conceptual_core5.py` | `tools/conceptual_core/check_conceptual_core5.py` |
| `tools/dev/check_conceptual_core6.py` | `tools/conceptual_core/check_conceptual_core6.py` |
| `tools/dev/check_conceptual_core7.py` | `tools/conceptual_core/check_conceptual_core7.py` |
| `tools/dev/check_conceptual_core8.py` | `tools/conceptual_core/check_conceptual_core8.py` |
| `tools/dev/check_conceptual_core9.py` | `tools/conceptual_core/check_conceptual_core9.py` |

#### `tools/consolidation/` (3)

| from | to |
|---|---|
| `tools/consolidation1_demo.py` | `tools/consolidation/consolidation1_demo.py` |
| `tools/dev/build_fov3d_facade.py` | `tools/consolidation/build_fov3d_facade.py` |
| `tools/dev/check_fov3d_facade.py` | `tools/consolidation/check_fov3d_facade.py` |

#### `tools/baseline/` (3)

| from | to |
|---|---|
| `tools/check_runtime_environment.py` | `tools/baseline/check_runtime_environment.py` |
| `tools/compare_golden.py` | `tools/baseline/compare_golden.py` |
| `tools/dev/check_fsg_tangent_frame.py` | `tools/baseline/check_fsg_tangent_frame.py` |

## Immutable `fov3d/`

    git diff 330577f176e507c3d36c5f2606692fc735bc6def...HEAD -- fov3d     must be EMPTY

The `fov3d` compatibility facades and `fov3d/__init__.py` are not edited, not even their
docstrings. Where an `fov3d` docstring names a moved path, that reference stays as it is,
and the report records it as a documented exception. Any unavoidable non-path change to
scientific code, whether in `fov3d/` or in a retained root tool, is a **stop condition**.

## Historical-record preservation

Historical contracts and reports are evidence. They often contain the exact commands that
were run at the time, for example a Core-7 report recording
`tools/dev/check_conceptual_core7.py`. Those records are **not** modernized.

Allowed changes to a historical document:
- `git mv`;
- repair of an actual Markdown hyperlink target whose destination moved, or which a move
  broke;
- a mechanically necessary navigation correction that does not rewrite what happened.

Filenames of historical documents are not changed.

## Dependency inventory (first execution step, read-only)

Before anything moves, every tracked file is searched for references to every `docs/` and
`tools/` path that moves. The search covers Python imports, `Path(...)` constructions
(including split forms such as `ROOT / "tools" / "dev" / ...`), `sys.path` bootstraps,
`__file__`-relative roots, subprocess commands, shell scripts, tests, manifests, checker
source paths, `git show` paths, Markdown links, README and CLAUDE.md instructions, comments
and docstrings describing current commands, and the `fov3d` compatibility facades. Each
reference is classified as one of:

    EXECUTABLE / ACTIVE
    HISTORICAL RECORD
    LINK
    COMMENT / DOCUMENTATION
    COMPATIBILITY API

The inventory summary is recorded in the report.

## Path and reference repair policy

Only mechanical repairs required by the moves are made. Scientific imports and algorithms
are not changed.

Repaired:
- executable path construction, for example `Path(__file__).resolve().parents[1]` →
  `parents[2]` when a script moves from `tools/` into `tools/<stage>/`, and split path
  constructions naming a moved file;
- `sys.path` bootstraps, made explicit where a moved script needs both its own directory
  and the `tools/` root (`HERE`, `TOOLS_ROOT`, `REPO_ROOT`), in the simplest form consistent
  with the existing style;
- bare-name imports that relied on the moved script's old directory;
- active instructions: usage docstrings, emitted "regenerate/reproduce" commands, and
  comments in current code and scripts that point to a moved path;
- current architecture documentation;
- actual Markdown links whose destination moved.

Not repaired:
- verbatim historical command records;
- the documented `fov3d/` exception above;
- names used only as log labels or messages, which are not paths.

Every moved file is classified in the move map as either a **pure move** (byte-identical to
its base blob) or a **repaired move**. A repaired move lists its exact literal edits, and
the file must equal its base blob with exactly those edits applied.

## Stable `scripts/` entry points

`scripts/` keeps its size and role. The three wrappers keep working as stable top-level
commands:

    scripts/verify_baseline.sh
    scripts/compare_golden.sh
    scripts/run_golden.sh

Each is updated mechanically wherever it names a moved path, for example
`tools/compare_golden.py` → `tools/baseline/compare_golden.py`.

## Baseline verification

At the base, `scripts/verify_baseline.sh` includes the step `baseline-files-unchanged`. It
requires that every path tracked at the historical baseline tag
`baseline-classroom-oracle1-2026-09-25` is byte-identical **at the same path** in the working
tree. A repository reorganization deliberately invalidates path identity, so this one step
is redesigned for the structural transition. It is not deleted or weakened.

The relocation-aware rule:
- the historical baseline tag is immutable, and still resolves to the commit it resolved to
  at the base;
- every path tracked at the tag is accounted for by exactly one of: unchanged at its path
  (byte-identical, as before), a pure relocation recorded in the transition move map
  (byte-identical at the new path), a repaired relocation (the tag blob plus exactly the
  declared literal edits, at the new path), or an explicitly declared replacement
  (`README.md`, by the decision recorded in this contract);
- an unlisted baseline file that changes, or a relocated file that differs from its declared
  content, fails the step;
- sealed scientific behavior is still guarded by the existing fail-capable checks and by the
  committed golden behavioral comparator.

The step's message must not claim that every baseline path is byte-identical in the current
tree once that is no longer true. The report must state explicitly:

    historical baseline BYTE/PATH identity   ≠   current repository layout
    sealed scientific behavior               remains preserved

The new step must be shown to fail for an unapproved content mutation.

## `README.md`: replaced

The root README is replaced entirely by the approved two-section text:

    # Foveal Stereo Vision
    ## Migration and Refactoring
    ## Next Stage — Integrated Foveal Controller

Only trivial wording adjustments are allowed, and only where a measured repository fact
requires them. No Requirements, Scene, Run or Status section remains in the root README.

## `CLAUDE.md`: stage and workflow update

`CLAUDE.md` stays the standing agreement. The following agreed changes are applied
coherently throughout, with no contradictory older wording left elsewhere:

1. Opening: "Science-led, engineering-disciplined project." replaces
   "Engineering-first / science-second project."
2. ChatGPT's GitHub connection is **read-only**. Chat may inspect, search and review
   authorized repository content. It does not push commits, branches, updates or pull
   requests. In the normal workflow, repository mutation is performed by Claude Code under
   Luiz's authority, and Luiz remains free to intervene explicitly. The obsolete draft
   sentence "ChatGPT cannot writes to the repository …" is removed if present.
3. The loop is replaced by the agreed conceptual loop: Luiz sets direction → Chat reads,
   reasons, drafts and prepares a self-contained Claude Code prompt → Luiz gives the prompt
   to Claude Code → Claude Code uses the authorized branch and isolated worktree, commits the
   durable contract before substantial execution, then implements, diagnoses, measures,
   commits and pushes → Chat reviews on GitHub → Luiz accepts, redirects or rejects.
4. The GitHub handoff section is replaced by the eight-step handoff, in which Chat does not
   author commits. ZIP + SHA256 stays only as a fallback.
5. All "Chat-authored commit" language is removed and replaced by: *A Chat proposal or
   contract draft may contain expected outputs. Only workstation execution converts them into
   measured outputs.* and *For each substantial handoff, Chat provides Luiz with a
   self-contained Claude Code prompt ready to paste.*
6. The scientific/behavioral result rule becomes, exactly: *An executed
   scientific/behavioral step must produce an inspectable visual and a measurable result,
   together with its checks and a short summary. Pure architectural/design steps may instead
   produce a reviewed specification or contract, together with a short summary.*
   Structural/refactoring steps still require machine-checkable preservation evidence.
7. "Current migration principle" is replaced by "Current project stage": the migration
   through Core 14 is accepted and paused, `fov3d/` is the substrate for the Integrated
   Foveal Controller, no further migration or cleanup Core starts automatically, and future
   behavior-preserving refactoring still follows *migrate behavior first; redesign structure
   second*.
8. One documentation convention throughout: `docs/<stage>/<phase>-contract.md` and
   `docs/<stage>/<phase>-report.md`.
9. Every valuable standing rule is preserved, subject only to path updates: Luiz's
   authority; proposed / measured / assumed; fail-capable checks; workstation execution
   authority; branch policy and forward-only published history; explicit acceptance criteria;
   no threshold or evaluation tuning to force success; the delegated-fix scope; the fixed-head
   geometry conventions; Blender Python versus host Python; cost classes; the repository as
   source of truth; the Chat Handoff recovery index; report requirements; the generated-artifact
   policy.

## Active architecture documents

`docs/architecture/current-architecture-map.md`, `docs/architecture/fov3d-api.md` and
`docs/conceptual-core/conceptual-core-map.md` are active, not purely historical. They are
updated only as needed to reflect:
- Core 14 **accepted** (the conceptual-core map still calls it "proposed (measured)", which
  is stale administrative status);
- the conceptual-core migration paused;
- Integrated Foveal Controller design as the next activity;
- the new repository paths.

Their scientific content is not redesigned.

## `docs/chat-handoff.md`

The accepted scientific milestone stays Core 14. The handoff does not claim that this
transition is accepted. A very small current-work note, saying that the repository layout
transition is proposed and in progress on `stage/repository-transition-1`, may be added.
Paths that the move would otherwise leave stale may be repaired. The handoff is not
replaced until Luiz accepts the transition.

## Checks

| id | check | cost class |
|---|---|---|
| A | `.venv/bin/python tools/repository/check_repository_layout.py` | interactive |
| B | compile every tracked Python source (in memory) | interactive |
| C | self-tests and baseline checks through their **new** paths | interactive |
| D | Conceptual Cores 1–10 and 14 at current head (`tools/conceptual_core/`) | interactive |
| E | Partition-Graph checkers 1–8b (`tools/partition_graph/`) | interactive |
| F | facade checker (`tools/consolidation/check_fov3d_facade.py`) | interactive (Blender for two rows) |
| G | Classroom-Oracle baseline checker (new `tools/classroom_oracle/` path) | interactive |
| H | updated `scripts/verify_baseline.sh` | interactive |
| I | golden comparator against the same accepted existing artifact used by the current migration gates (`previews/partition-graph-2-source-full`); no new Blender rendering | interactive (~10 s) |
| J | `scripts/run_golden.sh --help`, `scripts/compare_golden.sh --help`, and the moved tools' `--help`/self-test entry points | interactive |
| K | Markdown/current-link check of the active documentation | interactive |
| L | `git diff --check` | interactive |
| M | `fov3d/` unchanged; `tests/` unchanged; accepted reference trees unchanged; nothing written into accepted reference directories | interactive / batch (tree hashing) |

Superseded Core-11, Core-12 and Core-13 current-head structural failures are **not**
regressions: Cores 12–14 intentionally redesigned what those checkers inspect. Their accepted
checkers remain evidence at their accepted SHAs. They are run for information only, and
their failure mode must be the same before and after the transition.

A pre-transition run of the same gate at the base layout is recorded, so that every
post-transition result has a measured comparator.

## Fail-capable layout checker

`tools/repository/check_repository_layout.py` verifies this transition. At minimum:
- the expected hierarchy exists;
- the `docs/` root contains only `chat-handoff.md` plus the expected directories;
- `tools/dev/` no longer exists;
- the old paths are absent and the new paths exist;
- the `tools/` root set is exactly the approved compatibility/runtime set;
- `fov3d/` differs by zero bytes from the base;
- `tests/` is unchanged;
- the move map is complete, and each move is a pure move or exactly its declared repair;
- active scripts reference new tool paths only;
- `CLAUDE.md` contains no obsolete Chat-write workflow language;
- `README.md` has exactly the two intended top-level substantive sections;
- active current documentation links resolve.

Before the final checker is committed, deliberate temporary mutations must show that it
catches at least: a moved file returned to its obsolete path; an expected new path missing;
an unexpected extra root tools file; `tools/dev/` recreated; an active script still pointing
to an old path; one `fov3d/` byte changed; obsolete Chat-write language restored in
`CLAUDE.md`; a third substantive top-level README section; a broken active Markdown link. The
checker is not weakened to make the final tree pass.

## Acceptance criteria

The transition is ready for Luiz and Chat review only if:
- `docs/` is organized by stage/topic, and `tools/` is organized by stage/topic;
- `tools/dev/` is gone;
- the `tools/` root contains only the deliberate compatibility/runtime surface;
- historical evidence has not been rewritten;
- active paths all resolve, and the stable scripts work with the new paths;
- `README.md` contains only *Migration and Refactoring* and
  *Next Stage — Integrated Foveal Controller*;
- `CLAUDE.md` accurately states Chat's read-only GitHub role, contains the agreed visual +
  measurable + checks + summary rule, states that the migration is accepted and paused with
  controller design next, and has one unambiguous documentation convention;
- Core 14 is marked accepted in current architecture documentation;
- `fov3d/` is byte-identical to the base;
- the fail-capable layout checker passes;
- all applicable Conceptual-Core and Partition-Graph checks pass;
- baseline verification passes under the explicitly updated relocation-aware rule;
- golden behavior is unchanged (`MISMATCHES 0`);
- accepted reference assets are unchanged;
- `git diff --check` is clean.

## Stop conditions

- The base is not `330577f`, the shared checkout is dirty, or project work would be lost.
- The inventory finds another root tool in the compatibility closure (stop before moving it).
- A non-path change to scientific code, in `fov3d/` or in a retained root tool, turns out to
  be unavoidable.
- A check can pass only by weakening it, or by changing a threshold or an acceptance
  criterion.
- Proving a structural move would require a new expensive Blender rendering.
- Any conflict with `CLAUDE.md` that this contract does not resolve.

## Scope of permitted fixes

Mechanical path, import, bootstrap, link and instruction repairs required by the moves, as
defined above. Nothing else. Any fix beyond that returns to Luiz and Chat.

## Results to record

In `docs/repository/repository-transition-1-report.md`: the starting SHA; the branch and
worktree; the complete `docs/` and `tools/` move tables; the retained `tools/` root set; the
dependency inventory summary; the mechanical repairs; the historical-document policy; the
README result; the CLAUDE.md workflow changes; the baseline-verification redesign; the layout
checker and its fail-capable tests; every executed command; checker summaries; path-search
results; the active broken-link count; the `fov3d/` byte-identity result; `tests/` and
reference-tree integrity; deviations; unresolved questions; and a concise transition summary
that separates structural repository change from scientific behavior.

## Commit sequence

1. Specify repository stage transition (this contract only).
2. Reorganize documentation hierarchy (`git mv`, link repairs only).
3. Reorganize tools hierarchy (`git mv`, mechanical import/path repairs, stable scripts).
4. Update project entry documents (README, CLAUDE.md, active architecture status, layout
   checker).
5. Report repository stage transition.

Commits stay reviewable and are not squashed. The branch is pushed. Then execution stops:
no merge to `main`, no Core 15, no controller code, no controller architecture work.
