#!/usr/bin/env python3
"""Coherence lint for the governance files: syntax of the method, not its semantics.

    python3 tools/process/lint.py              # lint the working tree; exit 1 on any failure
    python3 tools/process/lint.py --self-test  # show that every check can fail
    python3 tools/process/lint.py --root DIR   # lint another checkout, e.g. an older commit

Stdlib only; runs with any Python 3.10+ (host side, interactive cost class).

The three governance layers are the kernel (CLAUDE.md), the shell
(docs/process/shell.md) and the state (docs/chat-handoff.md); AGENTS.md points other
agents at the kernel, and docs/process/records/ holds the process records. The lint
checks that each layer holds only its own kind of content, that write access is stated
once and agrees with who commits what, that cited paths, branches and commits exist,
that surface names are used consistently, and that the records are well formed.
Whether the protocol serves its purpose stays a human judgment.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

REPO = Path(__file__).resolve().parents[2]
PREFIX = "[governance-lint]"
KERNEL, SHELL, HANDOFF, AGENTS = "CLAUDE.md", "docs/process/shell.md", "docs/chat-handoff.md", "AGENTS.md"
RECORDS = "docs/process/records"
MAX_LINES = {KERNEL: 150, SHELL: 150, HANDOFF: 150}
IMPORTS = ("@docs/process/shell.md", "@docs/chat-handoff.md")
SURFACE_NAMES = ("Luiz", "ClaudeChat", "Claude Code", "ChatGPT")
NONCANONICAL = re.compile(r"Claude Chat|Claude-Chat|ClaudeCode|Claude-Code|Chat GPT|chatGPT|Chatgpt|chatgpt")
BARE_CHAT = re.compile(r"(?<![A-Za-z])Chat(?![A-Za-z])(?! Handoff)")
WRITE_RX = re.compile(r"read-only|write access|(?:may|can|cannot|does not|do not|never) push|pushes to|push to"
                      r"|\*\*not\*\* push", re.I)
HEX_RX = re.compile(r"(?<![0-9A-Za-z])(?=[0-9a-f]*[0-9])(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}(?![0-9A-Za-z])")
DATE_RX = re.compile(r"\b20\d\d-\d\d-\d\d\b")
STATUS_RX = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b|ACCEPTED|REVIEW PENDING|NOT MERGED|\bCLOSED\b")
PATH_RX = re.compile(r"`((?:docs|tools|fov3d|scripts|tests|scenes)/[^`\s]*|[A-Z][A-Za-z_-]*\.md)`")
CONTRACT_RX = re.compile(r"^docs/[a-z0-9-]+/[a-z0-9.-]+-contract\.md$")
RECORD_RX = re.compile(r"^(\d{4}-\d\d-\d\d)-(review|rejected|prevented)-[a-z0-9-]+\.md$")

Files = dict[str, str]
Git = Callable[..., str | None]


def git(*args: str) -> str | None:
    """Run git in the repository; return stdout, or None on failure."""
    r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def prose(text: str) -> str:
    """The text without fenced code blocks (templates and diagrams are not statements)."""
    return re.sub(r"^```.*?^```[ \t]*$", "", text, flags=re.S | re.M)


def table(text: str, heading: str) -> list[list[str]]:
    """Rows (header excluded) of the first Markdown table under `## heading`."""
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not m:
        return []
    rows = [ln.strip() for ln in m.group(1).splitlines() if ln.strip().startswith("|")]
    cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
    return [c for c in cells[1:] if not all(set(x) <= set("-: ") for x in c)]


def names_in(cell: str) -> list[str]:
    return [n for n in SURFACE_NAMES if n in cell]


def lint(files: Files, record_files: Files, git: Git) -> list[tuple[str, bool, str]]:
    """Every check as (name, ok, detail)."""
    out: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        out.append((name, ok, detail))

    kernel, shell, handoff = files.get(KERNEL, ""), files.get(SHELL, ""), files.get(HANDOFF, "")
    for f in (KERNEL, SHELL, HANDOFF, AGENTS):
        check(f"present: {f}", bool(files.get(f)))
    for f, cap in MAX_LINES.items():
        n = files.get(f, "").count("\n")
        check(f"size: {f} has at most {cap} lines", n <= cap, f"{n} lines")

    # Kernel: rules only. State (commit ids, dates, status tokens) belongs to the handoff.
    k = prose(kernel)
    found = HEX_RX.findall(k) + DATE_RX.findall(k) + STATUS_RX.findall(k)
    check("kernel holds no project state (commit ids, dates, status tokens)", not found, str(found[:5]))
    lines = [ln.strip() for ln in k.splitlines()]
    check("kernel imports the shell and the handoff for Claude Code", all(i in lines for i in IMPORTS),
          str([i for i in IMPORTS if i not in lines]))
    check("AGENTS.md points to CLAUDE.md", "CLAUDE.md" in files.get(AGENTS, ""))

    # Shell: surfaces, commits and dials, each dial with a traceable trigger.
    surfaces = {r[0]: r for r in table(shell, "Surfaces") if len(r) >= 5}
    commits = [r for r in table(shell, "Commits") if len(r) >= 2]
    dials = [r for r in table(shell, "Dials") if len(r) >= 3]
    check("shell has the Surfaces, Commits and Dials tables", bool(surfaces and commits and dials))
    check("shell declares surfaces by their canonical names", set(surfaces) <= set(SURFACE_NAMES),
          str(sorted(set(surfaces) - set(SURFACE_NAMES))))
    untriggered = [r[0] for r in dials if not (DATE_RX.search(r[2]) or "`" in r[2])]
    check("every dial names the trigger that set it (a date or a pointer)", not untriggered, str(untriggered))
    config = re.search(r"^## Configuration\s*\n\s*\n {4}(\S.*)$", shell, re.M)
    chain = re.findall(r"[A-Za-z][A-Za-z ]*[A-Za-z]", config.group(1)) if config else []
    check("the configuration line names only declared surfaces", bool(chain) and set(chain) <= set(surfaces),
          str(chain))

    # Write access: stated once (in the shell), and every committer can write.
    for f in (KERNEL, HANDOFF, AGENTS):
        hits = WRITE_RX.findall(prose(files.get(f, "")))
        check(f"write access is stated in the shell only, not in {f}", not hits, str(hits[:3]))
    bad = []
    for what, who in ((r[0], r[1]) for r in commits):
        for name in names_in(who) or [who]:
            writes = surfaces.get(name, ["", "", "", "none"])[3].lower()
            if name not in surfaces or writes.startswith("none") or ("main" in what and "main" not in writes):
                bad.append(f"{name}: {what[:40]}")
    check("every committer is a declared surface whose write access covers what it commits", not bad, str(bad))

    # Terms: one name per surface; bare "Chat" is ambiguous since ChatGPT and ClaudeChat both held the station.
    for f in (KERNEL, SHELL, HANDOFF):
        text = prose(files.get(f, ""))
        hits = NONCANONICAL.findall(text) + [m.group(0) for m in BARE_CHAT.finditer(text)]
        check(f"surface names are canonical in {f}", not hits, str(hits[:3]))

    # Paths and layout.
    missing = []
    for f in (KERNEL, SHELL, HANDOFF):
        for p in PATH_RX.findall(prose(files.get(f, ""))):
            if not any(c in p for c in "<*{") and not (REPO / p.rstrip("/")).exists():
                missing.append(f"{f}: {p}")
    check("every repository path cited by the governance files exists", not missing, str(missing[:4]))
    contracts = [p for f in (SHELL, HANDOFF) for p in PATH_RX.findall(files.get(f, "")) if p.endswith("-contract.md")]
    misplaced = [p for p in contracts if "<" not in p and not CONTRACT_RX.match(p)]
    check("cited contracts follow docs/<stage>/<phase>-contract.md", not misplaced, str(misplaced))
    check("the shell states the contract path convention", "docs/<stage>/<phase>-contract.md" in shell)

    # State: required fields; the named branches and the accepted commit exist.
    now = {r[0]: r[1] for r in table(handoff, "Now") if len(r) >= 2}
    need = ["Accepted main", "Active branch", "Stage"]
    check("handoff has the Now fields, the next step and the open items",
          all(k in now for k in need) and "## Active next step" in handoff
          and "## Decision-critical open items" in handoff, str([k for k in need if k not in now]))
    branches = [m for k in ("Active branch", "In progress") for m in re.findall(r"`([^`]+)`", now.get(k, ""))[:1]]
    absent = [b for b in branches if not (git("rev-parse", "--verify", "--quiet", f"refs/heads/{b}")
                                          or git("rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{b}"))]
    check("the branches the handoff names exist (local or origin)", bool(branches) and not absent, str(absent))
    sha = (HEX_RX.findall(now.get("Accepted main", "")) or [""])[0]
    resolved = git("rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}") if sha else None
    ancestor = bool(resolved) and git("merge-base", "--is-ancestor", resolved, "HEAD") is not None
    check("the accepted main commit exists and is an ancestor of HEAD", ancestor, sha or "none named")

    # Process records.
    for name, text in sorted(record_files.items()):
        m = RECORD_RX.match(name)
        fields = dict(re.findall(r"^- (kind|date|by): *(.+?)\s*$", text, re.M))
        ok = bool(m) and fields.get("kind") == m.group(2) and fields.get("date") == m.group(1) \
            and bool(names_in(fields.get("by", ""))) and re.search(r"^Outcome:", text, re.M) is not None
        check(f"record well formed: {name}", ok, str(fields))
    return out


def read_tree() -> tuple[Files, Files]:
    files = {f: (REPO / f).read_text(encoding="utf-8") if (REPO / f).is_file() else ""
             for f in (KERNEL, SHELL, HANDOFF, AGENTS)}
    rec = REPO / RECORDS
    records = {p.name: p.read_text(encoding="utf-8") for p in sorted(rec.glob("*.md"))} if rec.is_dir() else {}
    return files, records


def report(results: list[tuple[str, bool, str]]) -> int:
    failed = [(n, d) for n, ok, d in results if not ok]
    for n, d in failed:
        print(f"{PREFIX} FAIL {n}" + (f": {d}" if d else ""))
    print(f"{PREFIX} SUMMARY checked={len(results)} failed={len(failed)}")
    print("LINT OK" if not failed else "LINT FAIL")
    return 0 if not failed else 1


def self_test() -> int:
    """Each mutation of the clean tree must make its named check fail."""
    files, records = read_tree()
    base = lint(files, records, git)
    if not all(ok for _, ok, _ in base):
        print(f"{PREFIX} self-test needs a clean tree; run the lint first")
        return 1

    def sub(f: str, old: str, new: str) -> Callable[[Files, Files], None]:
        def apply(fs: Files, rs: Files) -> None:
            assert old in fs[f], (f, old)
            fs[f] = fs[f].replace(old, new, 1)
        return apply

    def add(f: str, text: str) -> Callable[[Files, Files], None]:
        return lambda fs, rs: fs.__setitem__(f, fs[f] + text)

    def row(f: str, first_cell: str, old: str, new: str) -> Callable[[Files, Files], None]:
        """Replace `old` by `new` in the table row whose first cell is `first_cell`."""
        def apply(fs: Files, rs: Files) -> None:
            rx = re.compile(rf"^(\| {re.escape(first_cell)} +\|.*)$", re.M)
            m = rx.search(fs[f])
            assert m and old in m.group(1), (first_cell, old)
            fs[f] = fs[f][:m.start()] + m.group(1).replace(old, new) + fs[f][m.end():]
        return apply

    first_dial = table(files[SHELL], "Dials")[0]
    mutations: list[tuple[str, str, Callable[[Files, Files], None]]] = [
        ("size: CLAUDE.md", "the kernel grows past its cap", add(KERNEL, "line\n" * 200)),
        ("kernel holds no project state", "a commit id in the kernel", add(KERNEL, "\nAccepted at `4fda984`.\n")),
        ("kernel holds no project state", "a status token in the kernel", add(KERNEL, "\nPHASE_X_ACCEPTED\n")),
        ("kernel imports", "an import hidden in a code span", sub(KERNEL, "\n@docs/process/shell.md", "\n`@docs/process/shell.md`")),
        ("AGENTS.md points", "AGENTS.md loses its pointer", lambda fs, rs: fs.__setitem__(AGENTS, "Agent notes.\n")),
        ("shell has the Surfaces", "the Commits table disappears", sub(SHELL, "## Commits", "## Who commits")),
        ("every dial names the trigger", "a dial without a trigger",
         sub(SHELL, f"| {first_dial[2]} |", "|  |")),
        ("the configuration line", "an undeclared surface in the loop", sub(SHELL, "[ChatGPT >]", "[Codex >]")),
        ("write access is stated in the shell only, not in docs/chat-handoff.md", "the handoff restates write access",
         add(HANDOFF, "\nClaudeChat may push to `main` after review.\n")),
        ("every committer is a declared surface", "a surface without write access commits",
         row(SHELL, "process record", "ClaudeChat, Claude Code", "ChatGPT")),
        ("every committer is a declared surface", "a committer without main access moves main",
         row(SHELL, "Claude Code", "; `main` on Luiz's acceptance", "")),
        ("surface names are canonical in docs/process/shell.md", "a variant spelling", add(SHELL, "\nClaude Chat reviews.\n")),
        ("surface names are canonical in CLAUDE.md", "a bare Chat", add(KERNEL, "\nChat reviews the report.\n")),
        ("every repository path cited", "a dead path in the handoff", add(HANDOFF, "\nSee `docs/nowhere/missing.md`.\n")),
        ("cited contracts follow", "a misplaced contract", add(HANDOFF, "\nSee `docs/process-contract.md`.\n")),
        ("the shell states the contract path", "the convention disappears",
         lambda fs, rs: fs.__setitem__(SHELL, fs[SHELL].replace("docs/<stage>/<phase>-contract.md", "docs/<x>.md"))),
        ("write access is stated in the shell only, not in CLAUDE.md", "the kernel restates write access",
         add(KERNEL, "\nChatGPT is read-only.\n")),
        ("size: docs/chat-handoff.md", "the handoff grows by appending", add(HANDOFF, "- entry\n" * 150)),
        ("handoff has the Now fields", "the next step disappears", sub(HANDOFF, "## Active next step", "## Next")),
        ("the branches the handoff names exist", "a branch that does not exist",
         sub(HANDOFF, "| Active branch     | `main` |", "| Active branch     | `no-such-branch-0` |")),
        ("the accepted main commit exists", "a commit that does not exist",
         lambda fs, rs: fs.__setitem__(HANDOFF, re.sub(r"(\| Accepted main +\| `)[0-9a-f]+", r"\g<1>deadbe7", fs[HANDOFF]))),
        ("record well formed", "a record whose kind contradicts its name",
         lambda fs, rs: rs.__setitem__("2026-01-01-review-x.md", "# X\n\n- kind: prevented\n- date: 2026-01-01\n"
                                       "- by: Luiz\n\nOutcome: none.\n")),
    ]
    failures = 0
    for target, what, mutate in mutations:
        fs, rs = dict(files), dict(records)
        mutate(fs, rs)
        hit = [n for n, ok, _ in lint(fs, rs, git) if not ok and n.startswith(target)]
        print(f"{PREFIX} {'PASS' if hit else 'FAIL'} negative: {what} -> {target}")
        failures += not hit
    print(f"{PREFIX} SELF-TEST negatives={len(mutations)} undetected={failures}")
    return 0 if failures == 0 else 1


def main(argv: list[str]) -> int:
    global REPO
    args = argv[1:]
    if args[:1] == ["--root"] and len(args) >= 2:
        REPO, args = Path(args[1]).resolve(), args[2:]
    if args == ["--self-test"]:
        return self_test()
    if args:
        print(__doc__)
        return 2
    return report(lint(*read_tree(), git))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
