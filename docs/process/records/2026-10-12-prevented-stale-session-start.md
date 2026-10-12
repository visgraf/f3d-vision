# Prevented: workstation sessions started from a September agreement

- kind: prevented
- date: 2026-10-12
- by: Claude Code, ClaudeChat
- concerns: the workstation's shared checkout `/home/lvelho/rd/f3d-vision`; Claude Code's auto-memory; `docs/process/governance-1-report.md` §1 and §4

Governance-1's observation O1 checked what a fresh Claude Code session loads. Two
sources of state turned out to sit outside the repository's view:

- The shared checkout's local `main` was at `e681392` (2026-09-27), 216 commits behind
  `origin/main`. Its `CLAUDE.md` is the first f3d-vision agreement ("Engineering-first /
  science-second", ChatGPT as the design surface). Claude Code works in worktrees and
  never touched the shared checkout, so every session Luiz started there loaded that
  agreement; the current rules reached Code only through prompts and contracts.
- Claude Code's auto-memory for the repository loads in every session, worktrees
  included. One status line in it was stale.

Claude Code found both (report §1, §4) and corrected the memory line. ClaudeChat
counted the distance to `origin/main` and identified the agreement the checkout loads.

Outcome: two shell dials, set by Luiz at acceptance. "Worktree": the shared checkout
stays on `main` and is fast-forwarded after each acceptance. "Assistant memory": both
assistants' memories are caches, never project status.
