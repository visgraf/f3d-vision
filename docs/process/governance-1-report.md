# Governance-1: kernel, shell and state — report

**Status: EXECUTED — REVIEW PENDING.** Claude Code ran contract §7 on the workstation:
C1–C5 pass and C6 fails, as the contract requires. No repair was needed. Acceptance,
and decisions D2 and D3, are Luiz's (contract §8). `main` is not fast-forwarded and no
tag is created.

Contract: [`governance-1-contract.md`](governance-1-contract.md).

Workstation numbers below are **MEASURED** from the commands named with them. ClaudeChat's
earlier numbers are labelled "ClaudeChat sandbox" and quoted from its commit messages.

## 1. Provenance

| item | value |
|---|---|
| branch | `process/governance-1`, from `main` `4fda984` |
| start head | `9a169e93ad7de57881aece898cb3ed3f728183af`, verified equal to `origin/process/governance-1` after `git fetch`, before any command; chain `9a169e9` → `8fe5545` → `4fda984` |
| ClaudeChat commits | `8fe5545` (contract and implementation), `9a169e9` (decision D1 recorded) |
| Claude Code commits | the commit that adds this file; no fix |
| workspace | a dedicated worktree on a local branch tracking `origin/process/governance-1`; the shared checkout was not switched or modified. `.venv` is symlinked from the shared checkout so that C4's `.venv/bin/python` exists; the symlink is untracked and not committed |
| interpreters | `python3` = Python 3.10.20 (C1, C2, C6); `.venv/bin/python` = Python 3.12.3 (C4) |
| executing session | started in the shared checkout, whose local `main` (`e681392`) carries the older `CLAUDE.md`; for this step it followed the contract and the branch's kernel, as Luiz's prompt directed |

## 2. Checks (contract §7)

From the worktree root, at `9a169e9`, in the contract's order. All interactive.

| Id | Command | Expected | Result, verbatim | Verdict |
|---|---|---|---|---|
| C1 | `python3 tools/process/lint.py` | `LINT OK` | `[governance-lint] SUMMARY checked=30 failed=0`, `LINT OK`; exit 0 | PASS |
| C2 | `python3 tools/process/lint.py --self-test` | `undetected=0` | 22 `PASS negative` lines, then `[governance-lint] SELF-TEST negatives=22 undetected=0`; exit 0 | PASS |
| C3 | `git show 4fda984:CLAUDE.md \| cmp - <(sed '1,/^---8<---$/d' docs/repository/CLAUDE-history.md)`, and the same for the handoff | no output, exit 0 | no output; exit 0 and 0 | PASS |
| C4 | `.venv/bin/python tools/repository/check_repository_layout.py` | `failed=0` | `[repository-layout] moves=115 pure=79 repaired=33 active=3 root_tools=16 markdown_links=81 active_links=24 broken_links=0`, `[repository-layout] SUMMARY checked=666 failed=0`; exit 0 | PASS |
| C5 | `git diff --name-only 4fda984 HEAD` | the files of §3 and the report | the 12 paths below | PASS, with the note below |
| C6 | `git worktree add --detach ../gov1-base 4fda984 && python3 tools/process/lint.py --root ../gov1-base; git worktree remove ../gov1-base` | `LINT FAIL` | `[governance-lint] SUMMARY checked=27 failed=16`, `LINT FAIL`; lint exit 1, worktree removed (exit 0) | FAILS, as required |

C5 printed:

    CLAUDE.md
    README.md
    docs/chat-handoff.md
    docs/process/governance-1-contract.md
    docs/process/records/2026-10-12-prevented-main-authority.md
    docs/process/records/2026-10-12-prevented-negative-test-overwrite.md
    docs/process/records/2026-10-12-prevented-stale-handoff.md
    docs/process/shell.md
    docs/repository/CLAUDE-history.md
    docs/repository/chat-handoff-history.md
    tools/process/lint.py
    tools/repository/check_repository_layout.py

Note on C5: eleven of these paths are in §3's table. The twelfth,
`docs/process/governance-1-contract.md`, is the step's own contract, committed with the
implementation in `8fe5545`; the layout checker also lists it as a required Governance-1
file. I read it as part of the step, so no path lies outside it. Read strictly, §3 does
not list it, and C5 shows that one extra file. After this report's commit the list also
contains `docs/process/governance-1-report.md`.

C6's 16 failures, verbatim:

    [governance-lint] FAIL present: docs/process/shell.md
    [governance-lint] FAIL size: CLAUDE.md has at most 150 lines: 1023 lines
    [governance-lint] FAIL size: docs/chat-handoff.md has at most 150 lines: 2557 lines
    [governance-lint] FAIL kernel holds no project state (commit ids, dates, status tokens): ['a437df048b555d5b59f6855b6572eea2665ab0da', '8066a246bf251fb1e2d66b7061899c32df236bf1', '87a3bab0', '4107be8', '2026-10-11']
    [governance-lint] FAIL kernel imports the shell and the handoff for Claude Code: ['@docs/process/shell.md', '@docs/chat-handoff.md']
    [governance-lint] FAIL shell has the Surfaces, Commits and Dials tables
    [governance-lint] FAIL the configuration line names only declared surfaces: []
    [governance-lint] FAIL write access is stated in the shell only, not in CLAUDE.md: ['read-only', 'may push', 'push to']
    [governance-lint] FAIL write access is stated in the shell only, not in docs/chat-handoff.md: ['may push', 'read-only', 'read-only']
    [governance-lint] FAIL surface names are canonical in CLAUDE.md: ['Chat', 'Chat', 'Chat']
    [governance-lint] FAIL surface names are canonical in docs/chat-handoff.md: ['Chat', 'Chat', 'Chat']
    [governance-lint] FAIL every repository path cited by the governance files exists: ['docs/chat-handoff.md: docs/north-star/ns1e-coherent-full-loop-m2-memory-contract.md', 'docs/chat-handoff.md: docs/north-star/ns1c-coherent-first-scene-switch-contract.md', 'docs/chat-handoff.md: tools/dev/']
    [governance-lint] FAIL the shell states the contract path convention
    [governance-lint] FAIL handoff has the Now fields, the next step and the open items: ['Accepted main', 'Active branch', 'Stage']
    [governance-lint] FAIL the branches the handoff names exist (local or origin): []
    [governance-lint] FAIL the accepted main commit exists and is an ancestor of HEAD: none named

Sizes at `9a169e9` (`wc -l`): `CLAUDE.md` 111, `docs/process/shell.md` 103,
`docs/chat-handoff.md` 93 lines, against the 150-line caps of D3. The two history bodies are
the files at `4fda984`: `CLAUDE.md` 1,023 lines / 49,618 bytes, the handoff 2,557 lines /
168,511 bytes.

### Workstation against ClaudeChat sandbox

| check | ClaudeChat sandbox (`8fe5545` message, on that commit's tree) | workstation, MEASURED at `9a169e9` |
|---|---|---|
| C1 | `LINT OK`, checked=30 failed=0 | `LINT OK`, checked=30 failed=0 |
| C2 | negatives=22 undetected=0 | negatives=22 undetected=0 |
| C3 | identical | identical |
| C4 | checked=666 failed=0 | checked=666 failed=0 |
| C5 | not reported | 12 paths, above |
| C6 | `LINT FAIL`, checked=27 failed=16 | `LINT FAIL`, checked=27 failed=16 |

The `9a169e9` message adds, ClaudeChat sandbox, on that tree: lint `LINT OK`; `--self-test`
`undetected=0`; layout checker `failed=0`. The workstation agrees on every count.

## 3. Repairs

None. No check misfired on the workstation. `tools/process/lint.py` and
`tools/repository/check_repository_layout.py` are unchanged, and no governance content was
edited.

## 4. Observation O1

Command, from the worktree root, Claude Code CLI 2.1.268, about 8 s, exit 0:

    claude -p "Answer only from the instructions loaded at startup, without opening any
    file: (a) who commits a step contract; (b) what the active next step is; (c) where
    the cost classes are set. For each answer, name the file it came from."

Answer, verbatim:

```text
**(a) Who commits a step contract** — ClaudeChat. The Commits table lists "contract, host-side code and host-side checks" as committed by ClaudeChat. The one exception is the fallback: if ClaudeChat cannot push, it puts the contract in the prompt and Claude Code commits it before executing. Both from `docs/process/shell.md`.

**(b) The active next step** — None authorized. Later playground experiments change one component at a time against the official baseline, each explicitly authorized; no policy redesign and no new research experiment is open. From `docs/chat-handoff.md`, section "Active next step".

**(c) Where cost classes are set** — `docs/process/shell.md`, the "Cost classes" row of the Dials table (interactive under ~10 s, batch under ~5 min when justified, overnight only when the contract authorizes it).
```

What the session loaded and did comes from its transcript (`~/.claude/projects/<worktree
key>/82233ed9-b325-4163-a47c-ded0bc4e5eec.jsonl`: its `instructions` attachment and its
tool calls), not from the answer:

- **The imports work.** The worktree's `CLAUDE.md`, `docs/process/shell.md` and
  `docs/chat-handoff.md` were all loaded at startup as `Project` instructions, at 6,197,
  8,430 and 5,323 characters. Each is the file without its final newline.
- **No file was opened.** The transcript has no tool calls.
- **The answers are correct and cite the right layer.** (a) ClaudeChat, from the shell's
  Commits table, and the fallback in which Claude Code commits it; (b) none authorized,
  from the handoff's "Active next step"; (c) the shell's "Cost classes" dial.

**A fourth source of state.** The session also loaded a fourth instruction file: Claude
Code's auto-memory index for this repository on the workstation
(`~/.claude/projects/-home-lvelho-rd-f3d-vision/memory/MEMORY.md`, type `AutoMem`, 1,169
characters). Claude Code loads this index in every session in the repository, including
sessions in its git worktrees. It is not in git and the lint cannot see it. Its one status
line was stale at O1: it still listed the official baseline's demo as REVIEW PENDING,
where the handoff records it accepted at `4fda984`. The O1 answers did not draw on it.
Claude Code corrected that line after O1. The file itself is outside Governance-1's scope
and is not governed here (§5, item 3).

## 5. Acceptance and open decisions

1. The workstation part of contract §8 holds: C1–C5 pass and C6 fails, all MEASURED above.
   Acceptance is Luiz's.
2. D1 was decided by Luiz before execution: either surface may fast-forward `main`, only on
   his explicit acceptance. D2 (§5: the layout checker's accepted-state predicates now read
   the history files) and D3 (150-line caps) await Luiz.
3. Open, for Luiz and ClaudeChat: whether the shell should state what Claude Code's
   auto-memory may hold. For example, it could hold workstation lessons, while project
   status comes only from the handoff. O1 shows that the auto-memory loads alongside the
   kernel and is outside the lint.
4. `main` is not fast-forwarded and no tag is created.

## 6. After writing this report

With this file staged, from the worktree root:

| Id | Result, verbatim |
|---|---|
| C1 | `[governance-lint] SUMMARY checked=30 failed=0`, `LINT OK`; exit 0 |
| C4 | `[repository-layout] moves=115 pure=79 repaired=33 active=3 root_tools=16 markdown_links=82 active_links=24 broken_links=0` (one more link: this report's link to the contract), `[repository-layout] SUMMARY checked=666 failed=0`; exit 0 |
