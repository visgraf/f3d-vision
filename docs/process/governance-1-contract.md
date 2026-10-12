# Governance-1: kernel, shell and state — contract

Status: PROPOSED by ClaudeChat, 2026-10-12. Step type: governance (structural). No
scientific or runtime behavior changes.

## 1. Question

Can the working agreement be split into three layers — a short kernel that rarely
changes, a shell of dial settings each with its trigger, and the project state in the
handoff only — with a lint that keeps them coherent and small committed records of the
process, without losing a rule or a historical record and without adding real weight
to the loop?

This implements proposals 1–3 of §8 of the N-Surface technical note ("Three layers,
three files"; "A coherence lint for the protocol"; "Commit the process, not only its
products") and fixes its limitation 3 ("The constitution absorbs state").

## 2. Assumed state

- Branch `process/governance-1`, created from `main` at `4fda984`
  (`4fda984ddb3bcb3974341a495749be1f8cc1e46a`).
- Default configuration, set by Luiz on 2026-10-12:
  `[ChatGPT >] Luiz > ClaudeChat > Luiz > Claude Code`.

## 3. What changes

| File | Change |
|------|--------|
| `CLAUDE.md` | Rewritten as the kernel: authority, the six kernel rules, contracts / reports / repairs, project invariants. No project state. It imports the shell and the handoff for Claude Code. 1,023 → about 110 lines |
| `docs/process/shell.md` | New. The configuration and the two loops, the surfaces with their write access (stated only here), who commits what, the dials with their triggers, fallbacks, the process-record format |
| `docs/chat-handoff.md` | Rewritten as a recovery index of at most 150 lines (was 2,557): now, next step, accepted results with pointers, what is not accepted or frozen, open items |
| `docs/repository/CLAUDE-history.md` | New. The former `CLAUDE.md`, byte-identical below a historical notice |
| `docs/repository/chat-handoff-history.md` | New. The former handoff, byte-identical below a historical notice |
| `docs/process/records/` | New. Three `prevented` records from this step |
| `tools/process/lint.py` | New. The coherence lint, stdlib only, with `--self-test` |
| `tools/repository/check_repository_layout.py` | Declares the Governance-1 files and directories; reads the accepted-state predicates from the history files (see §5) |
| `README.md` | One sentence: the working agreement is the kernel plus the shell |

Where each section of the former `CLAUDE.md` went:

| Former section | New place |
|----------------|-----------|
| Surfaces, The loop, GitHub handoff, ClaudeChat, One writer at a time, Claude Code | shell: Configuration, Surfaces, Commits; dials Transport, Branches, Worktree |
| Luiz; precedence; "Neither AI surface makes an undelegated project decision" | kernel: Authority |
| Branch policy | kernel rules 4 and 5; shell dial Branches |
| Proposed versus measured; Two hard rules | kernel rules 1 and 2; shell dial "Where a number is measured" |
| Scientific, design and refactoring steps | kernel (refactoring is not science); shell dial "Evidence per step type" |
| Current project stage | handoff (current), `docs/repository/CLAUDE-history.md` (verbatim) |
| Repository layout | shell dial Paths |
| Checks and acceptance criteria | kernel: step contract; rule 2 |
| Standing defaults and precedence | kernel: Authority; shell: Commits, dials Fix scope, Paths, Cost classes |
| Workstation fixes | kernel: repair |
| Environment conventions; Two interpreters | kernel: project invariants |
| Cost classes; Generated artifacts | shell dials |
| Repository as source of truth; Chat Handoff | kernel rule 3; shell dial Handoff |
| Reports | kernel: report |
| Final principle | kernel: Final principle |

## 4. What deliberately does not change

`fov3d/`, `tests/`, `scenes/`, `scripts/`, every tool except the two named above, every
contract and report, every tag, `AGENTS.md`. No rule of the former agreement is
dropped, except where it contradicted another (§6, D1). The scientific record is
untouched; only its location in the governance files changes.

## 5. A check whose target changes (needs Luiz's acceptance)

`check_repository_layout.py` required the live `CLAUDE.md` to contain 23 sentences (first written here as 24),
including the stage ("## Current project stage", "NS1d is ACCEPTED as Outcome 2"),
and the live handoff to contain dozens of accepted-state sentences. Each accepted
phase added more. The check could fail, but what it protected was the accretion
itself: it is one reason the constitution absorbed state.

Governance-1 keeps every one of those predicates, string for string, and points them
at the verbatim history files. Two new checks prove those files are byte-identical
to `CLAUDE.md` and the handoff at `4fda984`. On the live files, the checker keeps the
forbidden-wording list (now on the kernel and the shell) and adds two checks: the
kernel, shell and handoff claim no unaccepted result, and the handoff keeps NS1e and
NS1c unaccepted. The structure of the live files is checked by `tools/process/lint.py`.

So the old predicates become history-preservation checks. This is a deliberate
change of what the checker protects, declared here, not a repair.

## 6. Decisions for Luiz

- **D1. Who may fast-forward `main`.** The former agreement said both "ClaudeChat
  does not push to `main`" and "either surface may" fast-forward it on acceptance
  (`docs/process/records/2026-10-12-prevented-main-authority.md`). The shell keeps the
  second, more specific rule: either surface, only on Luiz's explicit acceptance.
  **Decided by Luiz, 2026-10-12, before execution: either surface.**
- **D2. §5**, the retargeting of the layout checker's accepted-state predicates.
- **D3. Size caps.** Kernel, shell and handoff at most 150 lines each (the Claude Code
  documentation advises under 200 per `CLAUDE.md`, and imported files load at launch
  too). They are constants in `tools/process/lint.py`.

## 7. Checks

| Id | Command | Cost | Expected |
|----|---------|------|----------|
| C1 | `python3 tools/process/lint.py` | interactive | `LINT OK`, 0 failed |
| C2 | `python3 tools/process/lint.py --self-test` | interactive | every negative detected (`undetected=0`) |
| C3 | `git show 4fda984:CLAUDE.md \| cmp - <(sed '1,/^---8<---$/d' docs/repository/CLAUDE-history.md)` and the same for `docs/chat-handoff.md` against `docs/repository/chat-handoff-history.md` | interactive | no output, exit 0 |
| C4 | `.venv/bin/python tools/repository/check_repository_layout.py` | interactive | `failed=0` |
| C5 | `git diff --name-only 4fda984 HEAD` | interactive | only the files in §3 and the step's report |
| C6 | `git worktree add --detach ../gov1-base 4fda984 && python3 tools/process/lint.py --root ../gov1-base; git worktree remove ../gov1-base` | interactive | `LINT FAIL` |

C6 is a control: the lint must reject the governance files it replaces. Its failures
are expected and recorded, not repaired.

## 8. Acceptance

Governance-1 is accepted when C1–C5 pass on the workstation, C6 fails there, and Luiz
accepts D2–D3 or changes them (D1 is decided). Measured on the workstation, C1–C6 become MEASURED;
ClaudeChat's sandbox runs are recorded in the report as "ClaudeChat sandbox".

## 9. Stop conditions and fix scope

Stop and report if the branch head differs from the one named in the prompt, if C3
shows any difference, or if C4 fails for a reason outside this step's files. Claude
Code may repair a defect in `tools/process/lint.py` or in this step's edits to the
layout checker that makes a check misfire on the workstation (an environment or
Python-version issue), and must describe it. It may not change governance content
beyond a typo, move a size cap, or weaken any predicate.

## 10. The report records

`docs/process/governance-1-report.md`: branch and head; C1–C6 with their summary
lines verbatim; any repair; and one observation, O1: in a fresh Claude Code session
started in the worktree, whether the shell and the handoff arrive through the
kernel's imports, and whether the session answers from them, without opening other
files: who commits the contract; what the active next step is; where the cost classes
are set.
