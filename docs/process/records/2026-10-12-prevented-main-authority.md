# Prevented: the working agreement contradicted itself on who moves `main`

- kind: prevented
- date: 2026-10-12
- by: ClaudeChat
- concerns: `CLAUDE.md` at `4fda984` (sections "ClaudeChat" and "Standing defaults"), commit `55ba7ba`

Commit `55ba7ba` wrote two statements into `CLAUDE.md` at once. The ClaudeChat
section said ClaudeChat never pushes to `main` or moves tags. "Standing defaults"
said that on Luiz's explicit acceptance either surface may fast-forward `main` and
create the tag, as Luiz instructs. A session could follow either one. Found while
splitting `CLAUDE.md` for Governance-1; no lint existed to catch it.

Outcome: write access is now stated once, in the shell's Surfaces and Commits
tables, with the more specific rule: either surface, only on Luiz's explicit
acceptance. Luiz confirmed it on 2026-10-12. `tools/process/lint.py` fails if write
access is restated in the kernel, the handoff or `AGENTS.md`.
