# Shell: current dial settings

Everything outside the kernel that has moved at least once. Each dial has one current
setting and the trigger that set it. When a platform capability, the project stage,
an execution cost or Luiz's bandwidth changes, edit the row that moved, record the
trigger, and leave `CLAUDE.md` alone. The previous setting stays in git history.

Write access is stated in this file and nowhere else.

## Configuration

    [ChatGPT >] Luiz > ClaudeChat > Luiz > Claude Code

Steps, the inner loop:

    Luiz sets direction
      > ClaudeChat reads the repository, writes the contract and any host-side code,
        checks what its sandbox can run, pushes to the work branch, and writes one
        self-contained prompt naming the branch and its head
      > Luiz gives the prompt to Claude Code
      > Claude Code pulls that head into its worktree, implements what remains,
        executes, measures, reports, pushes
      > ClaudeChat reviews the committed report and diff
      > Luiz accepts, redirects or rejects

Phases, the outer loop (optional, at a phase end):

    the repository > ChatGPT reviews the phase, read-only
      > Luiz brings the review to ClaudeChat
      > ClaudeChat records it in a `review` record, with what it adopts and why
      > Luiz opens the next phase

## Surfaces

| Surface     | Station                                              | Sees                                  | Writes                                              | Runs                                          |
|-------------|------------------------------------------------------|---------------------------------------|-----------------------------------------------------|-----------------------------------------------|
| Luiz        | decides, routes                                      | everything                            | anything                                            | anything                                      |
| ClaudeChat  | plans and specifies steps; reviews results            | the live repository, cloned in its sandbox | work branches Luiz names; `main` on Luiz's acceptance | host-side Python; no Blender, GPU or scene assets |
| Claude Code | executes, measures, diagnoses; reports                | the working tree on the workstation   | work branches Luiz names; `main` on Luiz's acceptance | everything: Blender, GPU, scene assets        |
| ChatGPT     | reviews phases (optional)                            | the public repository                 | none                                                | its own sandbox                               |

ClaudeChat runs in claude.ai on the Mac Studio. Claude Code runs in VS Code on the
Ubuntu 24.04 / RTX 4090 workstation.

## Commits

| What                                                          | Committed by            |
|---------------------------------------------------------------|-------------------------|
| contract, host-side code and host-side checks                 | ClaudeChat              |
| workstation code, delegated fixes, report                     | Claude Code             |
| acceptance commit and handoff update                          | ClaudeChat              |
| `main` fast-forward and tags, only on Luiz's explicit acceptance | ClaudeChat, Claude Code |
| process record                                                | ClaudeChat, Claude Code |

## Dials

| Dial | Setting | Trigger |
|------|---------|---------|
| Configuration | ClaudeChat plans steps, Claude Code executes them, ChatGPT optionally reviews phases | Luiz, 2026-10-12: the scheme proven in fov-3d-vision and here since 2026-10-11 |
| Stance | Science-led, engineering-disciplined | carried from the working agreement at `4fda984` |
| Transport | git. The work branch carries contract, code, report and records. Luiz carries one prompt per step and, at a phase end, one review. ZIP + SHA256 only when git transfer is impossible | 2026-10-11 (`55ba7ba`): ClaudeChat can push |
| Branches | Do not assume `main`; each step names its work branch. One writer at a time: pull the exact head before starting, push before handing over, name branch and head in the prompt; a writer that finds another remote head stops and reports | 2026-10-11 (`55ba7ba`): two surfaces can push |
| Worktree | Claude Code works in a dedicated git worktree and never switches or mutates the shared checkout `/home/lvelho/rd/f3d-vision` | carried from the handoff at `4fda984` |
| Where a number is measured | GPU, Blender, scene-asset, performance and full-run numbers: Claude Code on the workstation. A ClaudeChat sandbox command is MEASURED only for what it computes, labelled "ClaudeChat sandbox" with command and commit; a sandbox model of a workstation run stays PROPOSED for that quantity | 2026-10-11 (`55ba7ba`) |
| Evidence per step type | Scientific or behavioral: a measurable result, run evidence in `previews/`, at least one visual in `visuals/` showing the phenomenon itself, fail-capable checks, a short report with the regeneration command. Design: a reviewed contract and a short summary. Structural: `MISMATCHES 0` from the golden comparator for the sealed Classroom baseline; `tools/greedy_foveal/check_equivalence.py` for the official baseline. Governance: `LINT OK` | stage changes; Policy 1 (`docs/methodology/preview-visual-policy.md`); Engineering-1 |
| Cost classes | Interactive, under about 10 s: the development loop. Batch, under about 5 min: when justified. Overnight: only when the contract authorizes it with a one-line justification; the result is kept. Develop on the cheapest configuration that preserves the behavior; run the full one once, for the number that is reported | execution cost: 35-minute reference renders in fov-3d-vision; carried from `4fda984` |
| Fix scope | None unless the contract delegates a class of repair: diagnose, report, stop | carried from the working agreement at `4fda984` |
| Generated artifacts | Gitignored: `previews/` (machine-facing run evidence, kept for the stage) and `visuals/` (human-facing, persistent, regenerated by tracked tools). Git holds code, contracts, reports, numerical summaries, hashes and regeneration commands. Expensive reference assets are identified by provenance and checksum | Policy 1 (`docs/methodology/preview-visual-policy.md`) |
| Paths | Contracts `docs/<stage>/<phase>-contract.md`, reports `docs/<stage>/<phase>-report.md`; historical documents keep their names. Records `docs/process/records/`. Reusable code `fov3d/`. Sealed compatibility engine: the 16 modules at the `tools/` root (`docs/consolidation/consolidation-3-layout.json`). Other tools `tools/<stage>/`. Entry points `scripts/` | Repository Stage Transition 1 (`docs/repository/repository-transition-1-report.md`) |
| Phase review | Optional. At a phase end ChatGPT reviews the phase from the repository; the review is committed as a `review` record | Luiz, 2026-10-12: the cross-vendor phase review worked in fov-3d-vision and left no record |
| Process records | On. Kinds `review`, `rejected`, `prevented`; format below | Luiz, 2026-10-12: the cheapest saves were the least visible |
| Governance lint | `python3 tools/process/lint.py` must print `LINT OK` before any push that changes `CLAUDE.md`, `AGENTS.md`, this file or the handoff | Luiz, 2026-10-12 |
| Handoff | Rewritten, not appended, at each accepted milestone; at most 150 lines; earlier versions live in git | 2026-10-12: the handoff had grown to 2,557 lines |

## Fallbacks

- ClaudeChat cannot push: it puts the contract in the prompt, and Claude Code commits
  it before executing. This was the setting until 2026-10-10, with ChatGPT in
  ClaudeChat's station and no repository write.
- ChatGPT unavailable at a phase end: the phase closes without a cross-vendor review;
  the acceptance commit says so.

## Process records

One small file per event, `docs/process/records/YYYY-MM-DD-<kind>-<slug>.md`,
committed by the surface that saw it, in its next push:

- `review`: a phase or step review, with what was adopted and why;
- `rejected`: a contract rejected before execution, with the premise that failed;
- `prevented`: an error caught before it became a premise for later work.

```
# <Kind>: <one line>

- kind: review | rejected | prevented
- date: YYYY-MM-DD
- by: <surface or Luiz>
- concerns: <files or commits>

<What happened, in a few lines.>

Outcome: <what changed, or "none">.
```
