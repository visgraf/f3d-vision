# Prevented: the handoff told a fresh session things that were no longer true

- kind: prevented
- date: 2026-10-12
- by: ClaudeChat
- concerns: `docs/chat-handoff.md` at `4fda984`

The handoff, the fixed entry point for a new conversation, had grown to 2,557 lines by
appending a section per milestone. Its lower sections were never revised:

- "Working arrangement" said the specification surface's GitHub connection is
  read-only and that it does not push, which stopped being true on 2026-10-11
  (`55ba7ba`);
- "Active next step" and "Decision-critical open items" said the slide presentation
  was next, though it was accepted at `65eca40` and the phase closed at `4fda984`;
- the "Current roadmap" block still marked the slide presentation NEXT.

A session reading past the "Read first" section would have taken stale premises as
current. `CLAUDE.md` repeated part of the same state in its "Current project stage"
section.

Outcome: the handoff is rewritten as a recovery index of at most 150 lines, rewritten
rather than appended at each milestone; the old file is kept verbatim in
`docs/repository/chat-handoff-history.md`. The lint enforces the size cap and keeps
state out of the kernel.
