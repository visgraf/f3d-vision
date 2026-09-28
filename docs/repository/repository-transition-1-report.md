# Repository Transition 1: repository-stage transition report

## Result

    REPOSITORY_STAGE_TRANSITION_1_PRESERVES_SCIENTIFIC_BEHAVIOR

This was a **structural repository change**. `docs/` and `tools/` are reorganized by
stage/topic, `README.md` is replaced, and `CLAUDE.md` is updated for the Integrated Foveal
Controller stage. **Scientific behavior is unchanged**, and every item below is MEASURED at
`2402b61` unless marked otherwise:
- `fov3d/` differs from the base by 0 bytes;
- the 16 sealed `tools/` root modules differ by 0 bytes;
- `tests/` and `scenes/` differ by 0 bytes;
- Conceptual Cores 1–10 and 14 pass, and Partition-Graph checkers 1–8b pass;
- the facade check is 16/16, the Classroom-Oracle check 12/12, and `verify_baseline.sh`
  9/9;
- golden reports `MISMATCHES 0`;
- the 13 accepted reference trees are byte-identical to the Core-14 final snapshot.

    historical baseline BYTE/PATH identity   ≠   current repository layout
    sealed scientific behavior               remains preserved

The accepted scientific milestone is still Conceptual Core 14 (`296001e`). This transition
is **proposed**, not accepted. It stops here for Luiz and Chat to review. Nothing was merged
into `main` and no controller work was started.

## Identity and execution

| item | value |
|---|---|
| base | `origin/main = 330577f176e507c3d36c5f2606692fc735bc6def`, verified after `git fetch`; Core 14 `296001e` is its parent |
| shared checkout | `/home/lvelho/rd/f3d-vision`, `main` at `e681392` (an ancestor of `origin/main`, 49 behind), clean, no stash, no unpushed work; **not switched and not mutated** |
| branch | `stage/repository-transition-1`, created at the base with `--no-track`, pushed with its own upstream |
| worktree | `<scratchpad>/rt1/wt` (a dedicated isolated worktree) |
| data links | `.venv` → the shared checkout's `.venv`; the ignored `scenes/classroom/` payload → the shared checkout's; `previews` → `/home/lvelho/temp/previews-2026.09.28` (see *Environment observation*) |
| guard | before and after the base gate and the final gate: branch, expected HEAD and a clean tracked tree (`git status --porcelain --untracked-files=no`); it never tripped |
| base reference | the inventory was re-run in a temporary detached worktree at `330577f` (0 tracked changes), which was then removed |

Commits on `stage/repository-transition-1`:

| commit | content |
|---|---|
| `827b5c7` | Specify repository stage transition: the contract only, **before any path change** |
| `3e1fc9c` | Clarify the `tools/` root set from the dependency inventory: a separate commit; `827b5c7` is not amended |
| `ae80e3a` | Reorganize documentation hierarchy: `git mv` of 60 docs, link repairs, the layout-JSON default path |
| `b1bc417` | Reorganize tools hierarchy: `git mv` of 55 tools, declared mechanical repairs, stable scripts, the relocation-aware baseline step, the move map |
| `2402b61` | Update project entry documents: README, CLAUDE.md, active architecture documents, handoff note, layout checker |
| (this commit) | this report |

The read-only dependency inventory (§4 of the brief) began before `827b5c7` was committed.
No path changed before the contract and its clarification were both committed and pushed.

## Decision during execution: the `tools/` root set

The brief's provisional root set held 10 modules, and its map moved
`tools/classroom_oracle1_{epistemic,eval,matcher,public,render,run}.py` into
`tools/classroom_oracle/`. The inventory found that these six modules belong to the sealed
compatibility closure:
- they are `fov3d` facade targets (`reexport_legacy(globals(), 'tools.classroom_oracle1_*')`
  in six immutable `fov3d/experiments/classroom_oracle/*.py` files: the 6 COMPATIBILITY API
  references below);
- `check_fov3d_facade.py` fails any sealed module whose file is not directly under `tools/`;
- they are in the golden runtime closure of `check_runtime_environment.py`;
- the runner launches Blender on `tools/classroom_oracle1_render.py`.

Execution stopped before moving them. **Luiz decided** that the root set is exactly the 16
legacy modules of `docs/consolidation/consolidation-3-layout.json`. This was recorded as the
contract's *Inventory-resolved clarification* (`3e1fc9c`). Only
`check_classroom_assets.py`, `place_eye.py` and `check_classroom_oracle1.py` move to
`tools/classroom_oracle/`. The approved map has 115 moves: 60 docs and 55 tools.

## Retained `tools/` root (16, byte-identical to the base)

    bl_common.py            classroom_oracle1_epistemic.py
    exr_lite.py             classroom_oracle1_eval.py
    fsg3_surface_map.py     classroom_oracle1_matcher.py
    fsg6f_frontier.py       classroom_oracle1_public.py
    fsg6f_public.py         classroom_oracle1_render.py
    fsg_geometry.py         classroom_oracle1_run.py
    fsg_stereo.py
    multiobject2c_policy.py
    render_foveated.py
    warp.py

These are exactly the `mappings[].legacy` of the Consolidation-3 layout. The layout checker
derives the set from that file and requires equality, both in the index and on disk. No
`__init__.py` was added: `tools` stays a namespace directory, the stage directories need no
package semantics, and every moved script is run by path.

## Resulting hierarchy

    docs/                                  tools/
    ├── chat-handoff.md                    ├── <16 sealed modules>
    ├── architecture/        2             ├── baseline/          4  (3 moved + check_baseline_files.py)
    ├── baseline/            3             ├── classroom_oracle/  3
    ├── classroom-oracle/    1             ├── conceptual_core/  14
    ├── consolidation/       5             ├── consolidation/     3
    ├── conceptual-core/    31             ├── partition_graph/  32
    ├── methodology/         1             └── repository/        1  (check_repository_layout.py)
    ├── partition-graph/    17
    └── repository/          3  (contract, move map, this report)

No `docs/controller/` or `tools/controller/` directory was created.

## Complete move tables

Kinds come from `docs/repository/repository-transition-1-moves.json`:
- **pure**: byte-identical to the base blob;
- **repaired (n)**: the base blob with exactly *n* declared literal edits, each occurring
  once;
- **active**: a moved active document, whose content is governed by the active-document
  rules.

Totals: 79 pure, 33 repaired, 3 active.

### `docs/` (60)

#### `docs/architecture/` (2)

| from | kind |
|---|---|
| `docs/current-architecture-map.md` | active |
| `docs/fov3d-api.md` | active |

#### `docs/baseline/` (3)

| from | kind |
|---|---|
| `docs/baseline-contract.md` | pure |
| `docs/legacy-provenance.md` | pure |
| `docs/migration-manifest.md` | repaired (1): Markdown link target |

#### `docs/classroom-oracle/` (1)

| from | kind |
|---|---|
| `docs/classroom-oracle-1.md` | pure |

#### `docs/conceptual-core/` (31)

| from | kind |
|---|---|
| `docs/conceptual-core-map.md` | active |
| `docs/migration-conceptual-core-1-closure-report.md` | pure |
| `docs/migration-conceptual-core-1-closure.md` | pure |
| `docs/migration-conceptual-core-1-report.md` | pure |
| `docs/migration-conceptual-core-1.md` | pure |
| `docs/migration-conceptual-core-10-report.md` | pure |
| `docs/migration-conceptual-core-10.md` | pure |
| `docs/migration-conceptual-core-11-report.md` | pure |
| `docs/migration-conceptual-core-11.md` | pure |
| `docs/migration-conceptual-core-12-report.md` | pure |
| `docs/migration-conceptual-core-12.md` | pure |
| `docs/migration-conceptual-core-13-report.md` | pure |
| `docs/migration-conceptual-core-13.md` | pure |
| `docs/migration-conceptual-core-14-report.md` | pure |
| `docs/migration-conceptual-core-14.md` | pure |
| `docs/migration-conceptual-core-2-report.md` | pure |
| `docs/migration-conceptual-core-2.md` | pure |
| `docs/migration-conceptual-core-3-report.md` | pure |
| `docs/migration-conceptual-core-3.md` | pure |
| `docs/migration-conceptual-core-4-report.md` | pure |
| `docs/migration-conceptual-core-4.md` | pure |
| `docs/migration-conceptual-core-5-report.md` | pure |
| `docs/migration-conceptual-core-5.md` | pure |
| `docs/migration-conceptual-core-6-report.md` | pure |
| `docs/migration-conceptual-core-6.md` | pure |
| `docs/migration-conceptual-core-7-report.md` | pure |
| `docs/migration-conceptual-core-7.md` | pure |
| `docs/migration-conceptual-core-8-report.md` | pure |
| `docs/migration-conceptual-core-8.md` | pure |
| `docs/migration-conceptual-core-9-report.md` | pure |
| `docs/migration-conceptual-core-9.md` | pure |

#### `docs/consolidation/` (5)

| from | kind |
|---|---|
| `docs/consolidation-1-report.md` | repaired (1): Markdown link target |
| `docs/consolidation-2-report.md` | pure |
| `docs/consolidation-3-interface-refactor.md` | pure |
| `docs/consolidation-3-layout.json` | pure |
| `docs/consolidation-3-report.md` | pure |

#### `docs/methodology/` (1)

| from | kind |
|---|---|
| `docs/methodology-test-1-report.md` | pure |

#### `docs/partition-graph/` (17)

| from | kind |
|---|---|
| `docs/partition-graph-1.md` | pure |
| `docs/partition-graph-2-report.md` | pure |
| `docs/partition-graph-2.md` | pure |
| `docs/partition-graph-3-report.md` | pure |
| `docs/partition-graph-3.md` | pure |
| `docs/partition-graph-4-report.md` | pure |
| `docs/partition-graph-4.md` | pure |
| `docs/partition-graph-5-report.md` | pure |
| `docs/partition-graph-5.md` | pure |
| `docs/partition-graph-6-report.md` | pure |
| `docs/partition-graph-6.md` | pure |
| `docs/partition-graph-7-report.md` | pure |
| `docs/partition-graph-7.md` | pure |
| `docs/partition-graph-8-report.md` | pure |
| `docs/partition-graph-8.md` | pure |
| `docs/partition-graph-8b-report.md` | pure |
| `docs/partition-graph-8b.md` | pure |

### `tools/` (55)

#### `tools/baseline/` (3)

| from | kind |
|---|---|
| `tools/check_runtime_environment.py` | repaired (4): usage / emitted command; repo root `parents[1]`→`parents[2]`; doc pointer in comment; acceptance-check path |
| `tools/compare_golden.py` | repaired (5): usage / emitted command; doc pointer in comment; signature meta `generated_by` |
| `tools/dev/check_fsg_tangent_frame.py` | pure |

#### `tools/classroom_oracle/` (3)

| from | kind |
|---|---|
| `tools/check_classroom_assets.py` | repaired (2): usage / emitted command; repo root `parents[1]`→`parents[2]` |
| `tools/dev/check_classroom_oracle1.py` | pure |
| `tools/place_eye.py` | repaired (2): usage / emitted command; tools-root import bootstrap |

#### `tools/conceptual_core/` (14)

| from | kind |
|---|---|
| `tools/dev/check_conceptual_core1.py` | pure |
| `tools/dev/check_conceptual_core10.py` | pure |
| `tools/dev/check_conceptual_core11.py` | pure |
| `tools/dev/check_conceptual_core12.py` | pure |
| `tools/dev/check_conceptual_core13.py` | pure |
| `tools/dev/check_conceptual_core14.py` | pure |
| `tools/dev/check_conceptual_core2.py` | pure |
| `tools/dev/check_conceptual_core3.py` | pure |
| `tools/dev/check_conceptual_core4.py` | pure |
| `tools/dev/check_conceptual_core5.py` | pure |
| `tools/dev/check_conceptual_core6.py` | pure |
| `tools/dev/check_conceptual_core7.py` | repaired (1): split path to moved file |
| `tools/dev/check_conceptual_core8.py` | repaired (1): split path to moved file |
| `tools/dev/check_conceptual_core9.py` | pure |

#### `tools/consolidation/` (3)

| from | kind |
|---|---|
| `tools/consolidation1_demo.py` | repaired (2): tools-root import bootstrap; usage / emitted command |
| `tools/dev/build_fov3d_facade.py` | repaired (1): layout JSON path |
| `tools/dev/check_fov3d_facade.py` | repaired (1): layout JSON path |

#### `tools/partition_graph/` (32)

| from | kind |
|---|---|
| `tools/dev/apply_partition_graph4_lineage_fix.py` | repaired (1): doc pointer in comment |
| `tools/dev/check_partition_graph1.py` | pure |
| `tools/dev/check_partition_graph2.py` | pure |
| `tools/dev/check_partition_graph3.py` | pure |
| `tools/dev/check_partition_graph4.py` | pure |
| `tools/dev/check_partition_graph5.py` | pure |
| `tools/dev/check_partition_graph6.py` | pure |
| `tools/dev/check_partition_graph7.py` | pure |
| `tools/dev/check_partition_graph8.py` | pure |
| `tools/dev/check_partition_graph8b.py` | pure |
| `tools/partition_graph1_demo.py` | repaired (2): repo root `parents[1]`→`parents[2]`; emitted regenerate command |
| `tools/partition_graph2_demo.py` | repaired (2): repo root `parents[1]`→`parents[2]`; emitted regenerate command |
| `tools/partition_graph2_lift.py` | repaired (1): repo root `parents[1]`→`parents[2]` |
| `tools/partition_graph3_demo.py` | repaired (2): repo root `parents[1]`→`parents[2]`; emitted regenerate command |
| `tools/partition_graph3_lift.py` | repaired (1): repo root `parents[1]`→`parents[2]` |
| `tools/partition_graph4_analyze.py` | repaired (1): repo root `parents[1]`→`parents[2]` |
| `tools/partition_graph4_demo.py` | repaired (2): repo root `parents[1]`→`parents[2]`; emitted regenerate command |
| `tools/partition_graph4_lift.py` | repaired (1): repo root `parents[1]`→`parents[2]` |
| `tools/partition_graph5_analyze.py` | repaired (1): repo root `parents[1]`→`parents[2]` |
| `tools/partition_graph5_demo.py` | pure |
| `tools/partition_graph6_demo.py` | repaired (2): repo root `parents[1]`→`parents[2]`; emitted regenerate command |
| `tools/partition_graph6_evaluate.py` | repaired (1): repo root `parents[1]`→`parents[2]` |
| `tools/partition_graph6_propose.py` | repaired (1): repo root `parents[1]`→`parents[2]` |
| `tools/partition_graph7_demo.py` | repaired (1): repo root `parents[1]`→`parents[2]` |
| `tools/partition_graph7_evaluate.py` | repaired (1): repo root `parents[1]`→`parents[2]` |
| `tools/partition_graph7_propose.py` | repaired (1): repo root `parents[1]`→`parents[2]` |
| `tools/partition_graph8_demo.py` | repaired (1): repo root `parents[1]`→`parents[2]` |
| `tools/partition_graph8_evaluate.py` | repaired (1): repo root `parents[1]`→`parents[2]` |
| `tools/partition_graph8_integrate.py` | repaired (1): repo root `parents[1]`→`parents[2]` |
| `tools/partition_graph8b_demo.py` | repaired (1): repo root `parents[1]`→`parents[2]` |
| `tools/partition_graph8b_evaluate.py` | repaired (1): repo root `parents[1]`→`parents[2]` |
| `tools/partition_graph8b_propose.py` | repaired (1): repo root `parents[1]`→`parents[2]` |

## Dependency inventory (read-only, at the base)

Tool: `<scratchpad>/rt1/inventory.py`. It uses two detectors over every tracked text file:
- a **path detector** for `tools/…` / `docs/…` strings, with `{a,b}` braces and
  single-segment `*` globs expanded, plus the moved directory `tools/dev/`;
- a **name detector** for a moved file's basename or Python module stem as a whole word:
  imports, split `Path` parts, subprocess lists, prose.

A separate structural scan read every `__file__`/`parents[…]`/`sys.path`/`subprocess`/`git
show`/`glob` line in `tools/**`, because runtime path construction is invisible to name
matching.

| classification | brief's map (121 moves) | approved map (115 moves) |
|---|---:|---:|
| HISTORICAL RECORD (contracts/reports) | 634 | 592 |
| HISTORICAL RECORD (json provenance: `migration-manifest.json`, the `scenes/` manifests' `generated_by`/notes, the `tests/golden/*.json` `generated_by`; with the brief's map also the six module names in `consolidation-3-layout.json`) | 267 | 169 |
| COMMENT / DOCUMENTATION (active docs, code comments, docstrings) | 94 | 51 |
| EXECUTABLE / ACTIVE | 63 | 26 |
| COMMENT / DOCUMENTATION in immutable `fov3d/` | 9 | 3 |
| **COMPATIBILITY API** | **6** | **0** |
| LINK | 4 | 4 |
| total (files) | 1077 (91) | 845 (78) |

With the brief's map, the 6 COMPATIBILITY API references are the six
`fov3d/experiments/classroom_oracle/*.py` facades. They are the finding behind the root-set
decision.

The approved map's 26 EXECUTABLE / ACTIVE references break down as follows:
- **9 name-only labels, not paths:** seven `[place_eye]` log prints and two
  `compare_golden:` error messages;
- `scripts/verify_baseline.sh`: 5, the moved checkers;
- `scripts/compare_golden.sh`: 1, the comparator;
- `check_runtime_environment.py`: `DEV_CHECK`;
- `compare_golden.py`: `generated_by`;
- `build_fov3d_facade.py` and `check_fov3d_facade.py`: the default layout-JSON path;
- Core-7 and Core-8 checkers: one split `Path` each;
- five Partition-Graph demos: an emitted "Regenerate with" command each.

The structural scan added 25 runtime path constructions whose meaning changes with depth:
- 21 Partition-Graph root scripts with `ROOT = Path(__file__).resolve().parents[1]`;
- `check_classroom_assets.py` and `check_runtime_environment.py` (`parents[1]`);
- `consolidation1_demo.py` (a `HERE` bootstrap, followed by bare-name imports of the root
  Classroom modules);
- `place_eye.py` (`dirname(__file__)` on `sys.path`, then `from bl_common import …`).

The files moving out of `tools/dev/` keep their depth (`parents[2]` is still the root). Their
`git show` paths all name `fov3d/…`, and every checker `glob` is `fov3d`-scoped.

The LINK class covers 3 README links (replaced later) and 1 historical link
(`consolidation-1-report.md` → `migration-manifest.md`). A separate repo-wide link pass found
7 Markdown links at the base, 0 broken. One more was broken by the move itself:
`migration-manifest.md` → `../migration-manifest.json`, whose *source* moved.

## Mechanical repairs

All repairs are literal edits declared in the move map, and the layout checker verifies each
one as base blob + edits.

| repair | files |
|---|---|
| repository root one level up (`parents[1]` → `parents[2]`) | 21 `tools/partition_graph/partition_graph*.py`, `tools/classroom_oracle/check_classroom_assets.py`, `tools/baseline/check_runtime_environment.py` |
| explicit tools-root bootstrap (`TOOLS_ROOT = Path(__file__).resolve().parents[1]`, or `dirname(dirname(__file__))` in Blender-side code) for scripts that import root modules by bare name | `tools/consolidation/consolidation1_demo.py`, `tools/classroom_oracle/place_eye.py` |
| split `Path` to a moved file | Core-7 checker (the lineage tombstone), Core-8 checker (`check_partition_graph3.py`) |
| default facade-layout path (`docs/consolidation/…`) | `build_fov3d_facade.py`, `check_fov3d_facade.py` (made in `ae80e3a` at their old paths, before they moved) |
| acceptance-check path | `check_runtime_environment.py` `DEV_CHECK` |
| usage docstrings, emitted "Regenerate with"/"Reproduce" commands, pointer comments | the 5 PG demos, `consolidation1_demo.py`, `place_eye.py`, `check_classroom_assets.py`, `check_runtime_environment.py`, `compare_golden.py` (including its signature meta `generated_by`), the lineage tombstone's report pointer |
| Markdown link targets | `docs/baseline/migration-manifest.md`, `docs/consolidation/consolidation-1-report.md` |
| stable scripts | `scripts/compare_golden.sh` (comparator path, comment paths); `scripts/verify_baseline.sh` (5 moved checker paths, the redesigned step); `scripts/run_golden.sh` **unchanged**, because the runner and evaluator stayed at the root |

No scientific import or algorithm changed. `generated_by` is metadata in a signature's `meta`,
and `compare` reads only `behavior`, so golden comparison is unaffected. `tests/golden/`
keeps its historical `"tools/compare_golden.py signature"`.

No moved script needs both of the brief's bootstrap roots: `place_eye.py`, a Blender entry
point, needs only the tools root (for `bl_common`), and `consolidation1_demo.py` needs only
`TOOLS_ROOT`. No moved script imports a sibling in its own stage directory, so no `HERE`
entry was needed. The Classroom-Oracle scripts that bootstrap their own directory
(`classroom_oracle1_run.py`, `classroom_oracle1_eval.py`, `classroom_oracle1_render.py`) are
sealed root modules, and they are unchanged.

## Historical-document policy (as applied)

- The 56 historical Markdown contracts/reports and the Consolidation-3 layout JSON keep their
  filenames and text.
- Verbatim command records naming `tools/dev/…`, `tools/partition_graph*.py`, flat `docs/…`
  and so on are **not** modernized. The remaining matches are listed under *Path search*.
- Changes to historical documents: two link targets only (`migration-manifest.md`,
  `consolidation-1-report.md`).
- `migration-manifest.json`, the `scenes/` manifests (their `generated_by`/notes name
  `tools/place_eye.py`) and `tests/golden/*.json` are unchanged provenance records.
  `scenes/` and `tests/` are frozen by the contract.

## README result

`README.md` is exactly the approved text. It has one title (`Foveal Stereo Vision`) and two
sections, *Migration and Refactoring* and *Next Stage — Integrated Foveal Controller*, with
no deeper headings and no Requirements/Scene/Run/Status sections. No wording was adjusted:
the repository facts it states match the accepted record (Cores 1–11 ownership, Cores 12–14
separations, acceptance through Core 14).

## CLAUDE.md workflow changes

| brief item | applied |
|---|---|
| 20.1 opening | "Science-led, engineering-disciplined project." |
| 20.2 Chat GitHub rule | "ChatGPT's GitHub connection is **read-only**." Chat may inspect/search/review, and "does **not** push commits, branches, updates, or pull requests". Repository mutation is by Claude Code under Luiz's authority, and Luiz may intervene explicitly. The sentence "ChatGPT cannot writes to the repository …" **was not present** at the base, so there was nothing to remove; the checker asserts its absence. |
| 20.3 loop | replaced by the agreed loop, verbatim |
| 20.4 handoff | replaced by the eight-step handoff; ZIP + SHA256 only as a fallback |
| 20.5 Chat-commit language | removed everywhere, replaced by the two agreed sentences |
| 20.6 result rule | the exact two-sentence principle; the structural/refactoring subsection (machine-checkable preservation evidence, `MISMATCHES 0`) is kept |
| 20.7 stage | "Current migration principle" replaced by "Current project stage", verbatim |
| 20.8 convention | one convention: `docs/<stage>/<phase>-contract.md` / `-report.md` (the handoff section and the standing defaults) |
| 20.9 standing rules | all kept. Path-level updates: Claude Code works in a dedicated isolated worktree and commits the contract first; the Chat Handoff is named `docs/chat-handoff.md` |
| addition | a short **Repository layout** section: `fov3d/`; the 16-module sealed `tools/` root; `tools/<stage>/`; `docs/<stage>/`; the fixed handoff entry point; `scripts/`. It keeps the previous rule "new architecture is organized around stable `fov3d` concepts; `tools/` is a compatibility baseline where contracts say it is sealed". *Flagged for review: the brief did not list this section.* |

## Active architecture documents and handoff

- `docs/conceptual-core/conceptual-core-map.md`:
  - status "Cores 1-14 verified and accepted";
  - Core 14 accepted at `296001e`;
  - the migration paused and Integrated Foveal Controller design next;
  - "Proposed Conceptual Core 14 separation" → "Conceptual Core 14 separation (accepted)";
    "Core 14 (proposed)" → "(accepted)";
  - 7 tool paths updated.
- `docs/architecture/current-architecture-map.md`:
  - a status note (accepted through Core 14, paused, controller next; the 16 modules stay at
    the root and only the acceptance check was relocated, byte-identical);
  - path updates for the acceptance check, the ancillary tools, the layout JSON and the API
    document.
- `docs/architecture/fov3d-api.md`:
  - a status note;
  - rule 2 and the verification table now describe the relocation-aware baseline step;
  - facade builder, checker and layout paths;
  - the signature-provenance sentence now says the comparator was "then at the `tools/`
    root, now `tools/baseline/compare_golden.py`".
- Scientific content is not redesigned.
- `docs/chat-handoff.md`: accepted `main` stays `296001e` (Core 14). There is a small
  "Current work (**proposed, not accepted**)" note and one path repair (the Core-14 report).
  The handoff is **not** replaced.

## Baseline verification redesign

Before: the `verify_baseline.sh` step `baseline-files-unchanged` ran `git diff --quiet TAG --`
over every tag path, so path identity was part of the check.

After: the `baseline-files-accounted` step runs `tools/baseline/check_baseline_files.py
--self-test` and then `tools/baseline/check_baseline_files.py`. The tool:
- requires `baseline-classroom-oracle1-2026-09-25` to still resolve to `a980e59`, to be
  recorded as such in the move map, and to be an ancestor of HEAD;
- accounts for every one of the 31 tag paths by exactly one rule:

  | rule | count at `2402b61` | files |
  |---|---:|---|
  | unchanged at its path | 22 | the 16 sealed modules, `.gitignore`, `LICENSE`, `migration-manifest.json`, the 2 requirements files, `scenes/manifest.json` |
  | pure relocation | 4 | `classroom-oracle-1.md`, `legacy-provenance.md`, `check_classroom_oracle1.py`, `check_fsg_tangent_frame.py` |
  | repaired relocation (tag blob + declared edits) | 4 | `migration-manifest.md`, `consolidation-1-report.md` (link), `place_eye.py`, `consolidation1_demo.py` (bootstrap + usage text) |
  | declared replaced | 1 | `README.md` |

- fails when a relocated file's old path reappears, when a relocated file is missing, when a
  declared edit does not fit the tag blob, or when any unlisted file changes;
- prints, verbatim: `historical baseline byte/path identity is not the current layout; every
  baseline file is accounted for by the relocation rule above`.

The old message, "N files tracked at TAG are byte-identical in the working tree", is gone.

Fail-capability: `--self-test` catches 9/9 in-memory mutations. Four on-disk unapproved
mutations were also caught (see the next table). The step count stays 9, and the other eight
steps only follow the new paths. A future relocation of baseline files must add its own move
map to this accounting.

## Layout checker and fail-capable tests

`tools/repository/check_repository_layout.py` runs 487 checks at `2402b61`. They cover:
- the hierarchy and the exact `docs/` root;
- `tools/dev/` absent from both disk and index;
- the root set equal to the layout's legacy set;
- the stage directories;
- no `__init__.py`;
- each move (old path gone, new path present, pure/repaired content);
- move-map completeness (every base `docs/`/`tools/` file is moved or retained; every new
  hierarchy file is a move target or a declared addition);
- no untracked files;
- `fov3d/`, `tests/` and `scenes/` at 0 diff bytes from the base;
- the three tags unchanged;
- no obsolete path in current code, scripts or active docs (literal, brace-expanded and
  split-`Path` forms), with every `tools/…py` named by `scripts/*.sh` existing;
- the README heading contract;
- the CLAUDE.md forbidden and required wording;
- all Markdown links resolving;
- the Core-14 accepted status and the handoff's non-acceptance.

The checker excludes only its own source from the stale-path scan, because that source names
the paths it forbids.

Mutation harness `<scratchpad>/rt1/mutants.py`, run against the staged commit-4 tree. Each
mutation was applied on disk, checked and restored. The tracked state and `git status` were
identical afterwards, and the unmutated checker reported 487/0 before and after.

| # | mutation (on disk, temporary) | caught by |
|---|---|---|
| 1 | moved file returned to its obsolete path (`tools/compare_golden.py`) | old path gone; root set (disk) |
| 2 | expected new path missing (`check_partition_graph5.py`) | tracked file present; new path present |
| 3 | unexpected extra root tools file | root set (disk) |
| 4 | `tools/dev/` recreated | `tools/dev/` gone (disk) |
| 5 | active script pointing to an old path (`verify_baseline.sh` → `tools/dev/…`) | no obsolete moved path in `scripts/verify_baseline.sh` |
| 6 | one `fov3d/` byte flipped | `fov3d/` differs by zero bytes |
| 7 | "A Chat-authored commit is a **proposal**…" restored in CLAUDE.md | obsolete Chat-write wording |
| 8 | README third section (`## Status`) | exactly the two intended sections |
| 9 | broken active Markdown link in the handoff | link resolves; active links resolve |
| 10 | pure move content changed | pure move byte-identical |
| 11 | repaired move beyond its declared edits (`parents[3]`) | repaired move equals base + declared edits |
| 12 | `tests/` fixture byte flipped | `tests/` differs by zero bytes |
| 13 | extra file in the `docs/` root | `docs/` root on disk |
| 14 | empty `docs/controller/` reserved | `docs/` root on disk |
| 15 | CLAUDE.md "visual **and** measurable" weakened to "or" | agreed stage/workflow/rules wording |
| 16 | Core 14 reverted to "Proposed" in the map | Core 14 accepted; no stale proposal status |
| 17 | handoff claims the transition accepted | handoff does not claim acceptance |
| 18 | obsolete `tools/dev/…` path in an active architecture doc | no obsolete moved path |
| 19 | `check_baseline_files`: unapproved edit to `place_eye.py` (repaired relocation) | differs from tag blob + declared edits |
| 20 | `check_baseline_files`: byte flip in `classroom-oracle-1.md` (pure relocation) | differs from tag blob |
| 21 | `check_baseline_files`: byte flip in `tools/warp.py` (sealed root) | not byte-identical at its baseline path |
| 22 | `check_baseline_files`: relocated file's old path reappears | old path still exists |

Result: **22/22 caught** (rc=1 with the expected FAIL line). Two defects were found and fixed
before the checker was committed:
- the checker crashed on a missing tracked file (mutation 2 still exited 1, but without a
  summary line), so absent tracked files are now reported as a failed check;
- blockquote markers split phrases in the active-doc status check.

Neither fix loosened a check.

## Gates: base layout versus new layout

Base gate: `<scratchpad>/rt1/gate_old.sh`, old paths, at `330577f` under the guard. New gate:
`<scratchpad>/rt1/gate_new.sh`, new paths, at `2402b61` under the guard, with the tracked tree
clean before and after. All values are MEASURED.

| check | base `330577f` | new `2402b61` |
|---|---|---|
| A layout checker | — | `SUMMARY checked=487 failed=0` |
| B compile tracked `.py` (in memory) | 124, errors 0 | 126, errors 0 (+2 new checkers) |
| C `compare_golden.py self-test` | PASS | PASS |
| C `check_baseline_files.py --self-test` | — | PASS (9 mutations) |
| C classroom assets self-test | PASS (inside `verify_baseline`) | PASS |
| C tangent frame | PASS (inside `verify_baseline`) | `SUMMARY checked=92 failed=0` |
| C runtime environment | PASS (inside `verify_baseline`) | `required_passed=11/11` |
| D Cores 1–10 | 13, 20, 27, 32, 38, 35, 22, 20, 24, 29 checked; 0 failed | identical |
| D Core 14 | `checked=64 failed=0` | `checked=64 failed=0` |
| D Cores 11/12/13 (informational, superseded) | rc=1 at import: `ImportError … CANDIDATE_KINDS` / `AttributeError … candidate_policy.build_epistemic_partition` / `… run_context.build_epistemic_partition` | the same three failure modes |
| E Partition-Graph 1–8b | 13, 16, 20, 14, 12, 12, 12, 10, 12 checked; 0 failed | identical |
| F facade | `checked=16 failed=0` | `checked=16 failed=0` |
| G `check_classroom_oracle1` | `passed=12 failed=0` | `passed=12 failed=0` |
| H `scripts/verify_baseline.sh` | `passed=9 failed=0` (31 files byte-identical) | `passed=9 failed=0` (31 accounted: 22/4/4/1) |
| I golden `scripts/compare_golden.sh previews/partition-graph-2-source-full` | `MISMATCHES 0` (9.97 s) | `MISMATCHES 0` (9.83 s) |
| J `scripts/run_golden.sh --help`, `scripts/compare_golden.sh --help` | — | rc 0, rc 0 |
| J moved-tool entry points | — | rc 0 for all: `--help` of `compare_golden`, `check_baseline_files`, `check_runtime_environment`, `check_classroom_assets`, the facade checker and builder, `consolidation1_demo` and all 22 `partition_graph*.py` (module-level bootstraps and imports execute); a module-level probe (`runpy`, no `__main__`) of the 25 repaired host scripts confirmed 24/24 root constants (21 `ROOT`, 2 `REPO` = repository, 1 `TOOLS_ROOT` = `tools/`; `partition_graph5_demo.py` has none); the tombstone prints `RETIRED`; `place_eye.py --help` inside Blender 5.2.1 (proves the new `bl_common` bootstrap in Blender's Python) |
| L `git diff --check` | clean | clean (worktree, and `330577f..2402b61`) |

The golden comparator reused the accepted existing artifact. **No Blender rendering was
performed.** The only Blender invocations were the facade checker's two `bpy` rows, the
runtime probe and the `place_eye --help` import.

## Path search after the move

Literal searches over all tracked files at `2402b61` (`<scratchpad>/rt1/logs/path_search_2402b61.txt`):

| pattern | active docs | active code/scripts | historical contracts/reports | historical json | this transition's record | `fov3d/` (exception) |
|---|---:|---:|---:|---:|---:|---:|
| `tools/dev/` | 0 | 0 (the layout checker names it 5×, as the forbidden path) | 153 in 43 files | 78 | 64 | 1 |
| `tools/partition_graph<N>` (old root scripts) | 0 | 0 | 178 in 36 files | 0 | 49 | 0 |
| `tools/consolidation1_demo.py` | 0 | 0 | 3 | 1 | 3 | 0 |
| `tools/compare_golden.py` | 0 | 0 | 3 | 2 (`tests/golden` meta) | 7 | 0 |
| `tools/check_runtime_environment.py` | 0 | 0 | 3 | 0 | 4 | 0 |
| `tools/check_classroom_assets.py`, `tools/place_eye.py` | 0 | 0 | 1, 3 | 0, 6 | 5, 6 | 0 |
| the 60 old flat `docs/…` paths | 0 | 0 | 154 in 44 files | 8 | 124 | 2 |
| `tools/classroom_oracle1_` (**not moved**, sealed root) | 9 (valid) | 9 (valid) | 11 | 90 | 20 | 0 |

- Every remaining obsolete match is historical evidence, a historical JSON record, this
  transition's own record, or the documented `fov3d/` exception.
- **The documented `fov3d/` exception:** `fov3d/__init__.py`'s docstring still says it was
  "generated by tools/dev/build_fov3d_facade.py from docs/consolidation-3-layout.json" and
  cites `docs/fov3d-api.md`.
- `fov3d/` is immutable in this transition, so the docstring is unchanged. The references are
  prose, not code.

## Links

| scope | links | broken |
|---|---:|---:|
| all tracked Markdown at `2402b61` | 3 | 0 |
| active documentation (README, CLAUDE.md, AGENTS.md, handoff, architecture docs, conceptual-core map, `docs/repository/`) | 1 (`AGENTS.md` → `CLAUDE.md`) | **0** |

The base had 7 links. The 4 README links left with the replaced README, the 2 historical links
that moves broke were repaired, and `AGENTS.md` → `CLAUDE.md` is unchanged.

## Integrity

| item | result (MEASURED at `2402b61`) |
|---|---|
| `git diff 330577f...HEAD -- fov3d` | **0 bytes** (and 0 in the working tree; no untracked files) |
| 16 sealed root modules vs base | 0 bytes |
| `tests/`, `scenes/` vs base | 0 bytes, 0 bytes |
| tags | `baseline-classroom-oracle1-2026-09-25` → `a980e59`, `consolidation2-sealed-2026-09-25` → `760d216`, `f3d-vision-initial-2026-09-25` → `6c8a80f` (unchanged) |
| the 13 accepted reference trees | per-file sha256 manifests at `2402b61` are **identical to Core 14's final snapshot**, 13/13 (`<scratchpad>/rt1/logs/snapshot_2402b61.log`) |
| writes into accepted reference directories | none: `find … -newermt "2026-09-28 11:31"` over the previews root returned 0 entries |
| branch diff `330577f..2402b61` | 124 paths: 115 renames, 5 modified (`README.md`, `CLAUDE.md`, `docs/chat-handoff.md`, `scripts/compare_golden.sh`, `scripts/verify_baseline.sh`), 4 added (contract, move map, `check_baseline_files.py`, `check_repository_layout.py`) |

## Environment observation (not a transition change)

When this session began, the shared checkout's ignored `previews/` directory was **empty**
(recreated 2026-09-28 11:29). The accepted reference trees, 25 GB, are at
`/home/lvelho/temp/previews-2026.09.28`: 139 entries, the latest dated 2026-09-27 22:45. The
worktree linked `previews` to that location. The gates name `previews/partition-graph-2-source-full`
relative to the repository, so running them in the shared checkout needs the same link, or the
trees back in place.

## Commands executed (principal)

```bash
git fetch origin; git rev-parse origin/main                       # 330577f…
git merge-base --is-ancestor 296001e… origin/main                 # Core 14 in lineage
git branch --no-track stage/repository-transition-1 330577f…
git worktree add <scratchpad>/rt1/wt stage/repository-transition-1
ln -s …/.venv .venv; ln -s /home/lvelho/temp/previews-2026.09.28 previews; ln -s … scenes/classroom/*
<scratchpad>/rt1/guard.sh 330577f… -- <scratchpad>/rt1/gate_old.sh              # base gate
python3 <scratchpad>/rt1/inventory.py brief|moves_approved.json OUT.tsv          # inventory
git commit (contract) ; git push -u origin stage/repository-transition-1        # 827b5c7
git commit (clarification) ; git push                                            # 3e1fc9c
git mv docs/<60 files> docs/<stage>/…                                            # scripted loop
python3 <scratchpad>/rt1/repairs.py apply|apply-at-old …                         # declared edits
git mv tools/<55 files> tools/<stage>/… ; rmdir tools/dev
python3 <scratchpad>/rt1/repairs.py movemap docs/repository/repository-transition-1-moves.json
.venv/bin/python tools/baseline/check_baseline_files.py --self-test; … check_baseline_files.py
bash scripts/verify_baseline.sh
.venv/bin/python tools/repository/check_repository_layout.py
python3 <scratchpad>/rt1/mutants.py                                              # 22/22 caught
<scratchpad>/rt1/guard.sh 2402b61… -- <scratchpad>/rt1/gate_new.sh               # new gate, PASS
<scratchpad>/rt1/snapshot.sh rt1-at-2402b61                                      # 13/13 identical
git diff 330577f...HEAD -- fov3d | wc -c                                         # 0
git diff --check 330577f HEAD
```

## Deviations from the brief

1. **Root set: 16, not 10.** This was an inventory finding, decided by Luiz and recorded in
   `3e1fc9c`. The six `classroom_oracle1_*` modules stay at the root. As a result:
   - the brief's `run_golden.sh` examples (§16) do not apply, and `run_golden.sh` is
     unchanged;
   - `check_classroom_oracle1.py` is a pure move.
2. **CLAUDE.md, §20.2:** the sentence "ChatGPT cannot writes to the repository …" did not
   exist at the base, so nothing was removed.
3. **CLAUDE.md, addition:** a short *Repository layout* section, flagged for review.
4. **A second new tool:** `tools/baseline/check_baseline_files.py` implements the redesigned
   baseline step. The step was renamed `baseline-files-unchanged` → `baseline-files-accounted`.
5. **Emitted text in moved tools was repaired:** "Regenerate with"/"Reproduce" commands, and
   `compare_golden.py`'s `meta.generated_by`. Future demo READMEs, and a future `signature`
   regeneration, will name the new paths. No gate compares these texts.
6. **README links were repaired in `ae80e3a`**, before the README was replaced in `2402b61`,
   so each intermediate commit has resolving links.
7. **The read-only inventory began before the contract commit.** No path change preceded the
   contract.

## Unresolved questions

1. `fov3d/__init__.py`'s docstring names the pre-transition paths (`tools/dev/build_fov3d_facade.py`,
   `docs/consolidation-3-layout.json`, `docs/fov3d-api.md`). Correcting it is a text-only
   `fov3d/` change, and it needs an explicit decision.
2. `docs/conceptual-core/conceptual-core-map.md` still has the headings "Proposed Conceptual
   Core 3 extraction" and "Proposed later extraction order". They are stale in the same way as
   Core 14 was, but the brief scoped the status correction to Core 14.
3. Where the accepted reference trees live from now on: see *Environment observation*.
4. When this transition is accepted, the handoff note should be replaced by the accepted
   state (a new accepted `main`), in an administrative commit.
5. A future relocation of any baseline-tag file must add a move map to
   `check_baseline_files.py`, which currently reads one.

## Transition summary

- **Structural repository change:**
  - 60 docs are in 7 stage/topic directories, plus `docs/repository/`, with the handoff
    fixed at the top;
  - 55 tools are in 5 stage/topic directories, plus `tools/repository/`, and `tools/dev/` is
    gone;
  - the `tools/` root is exactly the 16-module sealed facade closure;
  - 79 pure moves and 33 declared mechanical repairs;
  - README replaced, and CLAUDE.md updated for the Integrated Foveal Controller stage and the
    read-only-Chat workflow;
  - one relocation-aware baseline step;
  - a fail-capable layout checker (22/22 mutations caught).
- **Scientific behavior: unchanged.**
  - `fov3d/`, the sealed root modules, `tests/` and `scenes/` are all at 0 bytes of difference;
  - every applicable checker passes with the same counts as at the base;
  - golden reports `MISMATCHES 0`;
  - the 13 accepted reference trees are identical.
- **Next:** Luiz and Chat review `stage/repository-transition-1`. Nothing was merged into
  `main`. No Core 15 and no controller work was started.
