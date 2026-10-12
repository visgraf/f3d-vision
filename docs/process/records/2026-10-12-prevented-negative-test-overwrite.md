# Prevented: a negative test put the old handoff back

- kind: prevented
- date: 2026-10-12
- by: ClaudeChat
- concerns: `docs/chat-handoff.md`, `docs/process/shell.md`, `docs/repository/CLAUDE-history.md` (uncommitted drafts)

To show that the layout checker's new Governance-1 checks can fail, ClaudeChat
mutated three files, ran the checker, and undid each mutation with
`git checkout HEAD -- <file>`. For the handoff, HEAD held the old 2,557-line
version, so the undo replaced the new draft with it; for the two new files the undo
failed silently and the mutations stayed. `git status` showed it before any commit.

Outcome: the new handoff was recovered from the blob staged before the test; the two
mutations were reverted by hand; C1–C4 were re-run clean. Had it gone unnoticed, C1
would have failed on the handoff's size. Negative tests now run on copies, as
`tools/process/lint.py --self-test` does.
