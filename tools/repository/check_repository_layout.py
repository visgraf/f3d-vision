#!/usr/bin/env python3
"""Fail-capable structural check of Repository Transition 1 (repository-stage transition).

    .venv/bin/python tools/repository/check_repository_layout.py      # exit 1 on any failed check

Contract: docs/repository/repository-transition-1-contract.md.  Move map:
docs/repository/repository-transition-1-moves.json.  The check reads the working tree, the
index and git objects of the base commit; it writes nothing.

It checks the stage/topic hierarchy of docs/ and tools/, the absence of tools/dev/, the
sealed tools/ root closure (exactly the Consolidation-3 facade layout's legacy modules),
every move (old path gone; new path pure, or its base blob plus exactly the declared
edits), move-map completeness, fov3d/ and tests/ byte identity with the base, obsolete
paths in current code/scripts/active docs, the README and CLAUDE.md contracts, Markdown
links, and the accepted Core-14 status of the active architecture documents.  Scientific
behavior is checked elsewhere (the Conceptual-Core and Partition-Graph checkers,
scripts/verify_baseline.sh and the golden comparator).

Controller 01 (docs/controller/controller-01-state-action-contract.md) accommodates the
layout narrowly: the controller stage directories, the declared Controller-01 files (the only
new fov3d/ files; every pre-existing fov3d/ file stays byte-identical), and the Chat Handoff
as accepted for Repository Stage Transition 1.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[2]
BASE = "330577f176e507c3d36c5f2606692fc735bc6def"
MOVE_MAP = "docs/repository/repository-transition-1-moves.json"
LAYOUT = "docs/consolidation/consolidation-3-layout.json"
PREFIX = "[repository-layout]"

DOCS_DIRS = {"architecture", "baseline", "classroom-oracle", "consolidation", "conceptual-core",
             "controller", "methodology", "partition-graph", "repository"}
TOOLS_DIRS = {"baseline", "classroom_oracle", "conceptual_core", "consolidation", "controller", "partition_graph",
              "repository"}
DOCS_ROOT_FILES = {"chat-handoff.md"}
ADDED_REQUIRED = {
    "docs/repository/repository-transition-1-contract.md",
    "docs/repository/repository-transition-1-moves.json",
    "tools/baseline/check_baseline_files.py",
    "tools/repository/check_repository_layout.py",
}
CONTROLLER01_FOV3D = {"fov3d/control/integrated.py", "fov3d/experiments/classroom_oracle/controller01.py"}
CONTROLLER01_REQUIRED = CONTROLLER01_FOV3D | {
    "docs/controller/controller-01-state-action-contract.md",
    "tools/controller/check_controller01.py",
    "tools/controller/plot_controller01.py",
}
CONTROLLER01_ALLOWED = CONTROLLER01_REQUIRED | {"docs/controller/controller-01-state-action-report.md"}
ADDED_ALLOWED = ADDED_REQUIRED | {"docs/repository/repository-transition-1-report.md"} | CONTROLLER01_ALLOWED
HANDOFF_REMOVAL_SENTENCE = "`tools/dev/` is gone."
ACTIVE_MOVED = {"docs/architecture/current-architecture-map.md", "docs/architecture/fov3d-api.md",
                "docs/conceptual-core/conceptual-core-map.md"}
ACTIVE_DOCS = {"README.md", "CLAUDE.md", "AGENTS.md", "docs/chat-handoff.md"} | ACTIVE_MOVED
TAGS = {
    "baseline-classroom-oracle1-2026-09-25": "a980e59dfc453c590190f842c47c4588bc99989d",
    "consolidation2-sealed-2026-09-25": "760d2162953ae0d5754704249a3e0f7ae7b60776",
    "f3d-vision-initial-2026-09-25": "6c8a80f5c57cb5c7f697141de6f48abbdd041743",
}
README_TITLE = "Foveal Stereo Vision"
README_SECTIONS = ["Migration and Refactoring", "Next Stage — Integrated Foveal Controller"]
CLAUDE_FORBIDDEN = [
    "Engineering-first", "science-second", "Chat-authored", "Chat commit", "Chat commits",
    "authorizes a repository write", "authorized a repository write", "Chat writes to the repository",
    "cannot writes", "commits the proposed", "tells Claude Code to pull", "docs/<phase>.md",
    "docs/<phase>-report.md", "migration/refactoring period", "Current migration principle",
]
CLAUDE_REQUIRED = [
    "Science-led, engineering-disciplined project.",
    "ChatGPT's GitHub connection is **read-only**.",
    "Chat does **not** push commits, branches, updates, or pull requests.",
    "An executed scientific/behavioral step must produce an inspectable visual and a measurable result, "
    "together with its checks and a short summary.",
    "Pure architectural/design steps may instead produce a reviewed specification or contract, "
    "together with a short summary.",
    "## Current project stage",
    "The Conceptual Core migration/refactoring through Core 14 is accepted and paused.",
    "Do not start another migration or cleanup Core automatically.",
    "migrate behavior first; redesign structure second",
    "A Chat proposal or contract draft may contain expected outputs.",
    "Only workstation execution converts them into measured outputs.",
    "For each substantial handoff, Chat provides Luiz with a self-contained Claude Code prompt ready to paste.",
    "docs/<stage>/<phase>-contract.md",
    "docs/<stage>/<phase>-report.md",
]
PATH_RX = re.compile(r"(?:tools|docs)/[A-Za-z0-9_\-./{},*]+")
LINK_RX = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

checked = 0
failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global checked, failed
    checked += 1
    if not ok:
        failed += 1
        print(f"{PREFIX} FAIL {name}{': ' + detail if detail else ''}")


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, check=True).stdout


def tracked() -> list[str]:
    return git("ls-files", "-z").decode().split("\0")[:-1]


def untracked(path: str) -> list[str]:
    return git("ls-files", "-z", "--others", "--exclude-standard", "--", path).decode().split("\0")[:-1]


def disk(rel: str) -> Path:
    return REPO / rel


def expand_braces(s: str) -> list[str]:
    m = re.search(r"\{([^{}]*)\}", s)
    if not m:
        return [s]
    return [x for alt in m.group(1).split(",") for x in expand_braces(s[:m.start()] + alt + s[m.end():])]


def apply_edits(blob: bytes, edits: list[list[str]]) -> bytes | None:
    text = blob.decode("utf-8")
    for before, after in edits:
        if text.count(before) != 1:
            return None
        text = text.replace(before, after)
    return text.encode("utf-8")


def stale_references(text: str, olds: set[str]) -> list[str]:
    """Old (moved-away) paths named in `text`: literal, brace-expanded, or as split Path parts."""
    found = []
    for raw in PATH_RX.findall(text):
        raw = raw.rstrip(".,")
        for p in expand_braces(raw):
            p = p.rstrip(".,")
            if p in olds or p == "tools/dev" or p.startswith("tools/dev/"):
                found.append(raw)
                break
    for m in re.finditer(r"""["'](tools|docs)["']\s*/\s*["']([^"']+)["']""", text):
        p = f"{m.group(1)}/{m.group(2)}"
        if p in olds or m.group(2) == "dev" or m.group(2).startswith("dev/"):
            found.append(m.group(0))
    return found


def markdown_links(rel: str) -> list[tuple[int, str, bool]]:
    out = []
    for i, line in enumerate(disk(rel).read_text(encoding="utf-8").splitlines(), 1):
        for target in LINK_RX.findall(line):
            if re.match(r"[a-z]+:", target) or target.startswith("#"):
                continue
            dest = os.path.normpath(os.path.join(os.path.dirname(rel), target.split("#")[0]))
            out.append((i, target, disk(dest).exists()))
    return out


def headings(text: str) -> list[tuple[int, str]]:
    out, fenced = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
            continue
        m = re.match(r"(#{1,6})\s+(.*\S)\s*$", line)
        if m and not fenced:
            out.append((len(m.group(1)), m.group(2)))
    return out


def squash(text: str) -> str:
    """Prose with line breaks and Markdown blockquote markers collapsed to single spaces."""
    return re.sub(r"\s+", " ", re.sub(r"(?m)^\s*>\s?", "", text))


def main() -> int:
    index = tracked()
    files = [f for f in index if disk(f).is_file()]  # content is read from these
    gone = sorted(set(index) - set(files))
    check("every tracked file is present on disk", not gone, str(gone[:5]))
    fileset = set(files)
    spec = json.loads(disk(MOVE_MAP).read_text(encoding="utf-8"))
    moves = spec["moves"]
    olds = {m["old"] for m in moves}
    news = {m["new"] for m in moves}
    check("move map records the base commit", spec.get("base") == BASE, str(spec.get("base")))
    check("move map entries are unique", len(olds) == len(moves) == len(news))

    # ---- hierarchy
    for d in sorted(DOCS_DIRS):
        check(f"docs/{d}/ exists with tracked files", disk(f"docs/{d}").is_dir()
              and any(f.startswith(f"docs/{d}/") for f in files))
    for d in sorted(TOOLS_DIRS):
        check(f"tools/{d}/ exists with tracked files", disk(f"tools/{d}").is_dir()
              and any(f.startswith(f"tools/{d}/") for f in files))
    docs_root_tracked = {f.split("/")[1] for f in index if f.startswith("docs/") and f.count("/") == 1}
    docs_dirs_tracked = {f.split("/")[1] for f in index if f.startswith("docs/") and f.count("/") >= 2}
    docs_disk = {p.name for p in disk("docs").iterdir()}
    check("docs/ root holds only chat-handoff.md among files (tracked)", docs_root_tracked == DOCS_ROOT_FILES,
          str(sorted(docs_root_tracked ^ DOCS_ROOT_FILES)))
    check("docs/ directories are exactly the stage/topic set (tracked)", docs_dirs_tracked == DOCS_DIRS,
          str(sorted(docs_dirs_tracked ^ DOCS_DIRS)))
    check("docs/ root on disk holds only chat-handoff.md and the stage/topic directories",
          docs_disk == DOCS_ROOT_FILES | DOCS_DIRS, str(sorted(docs_disk ^ (DOCS_ROOT_FILES | DOCS_DIRS))))

    # ---- tools/dev and the sealed tools/ root closure
    check("tools/dev/ is gone (disk)", not disk("tools/dev").exists())
    check("tools/dev/ is gone (index)", not any(f.startswith("tools/dev/") for f in index))
    layout = json.loads(disk(LAYOUT).read_text(encoding="utf-8"))
    closure = {"tools/" + m["legacy"].split(".", 1)[1] + ".py" for m in layout["mappings"]}
    check("the Consolidation-3 layout names 16 sealed legacy modules", len(closure) == 16, str(len(closure)))
    root_tracked = {f for f in index if f.startswith("tools/") and f.count("/") == 1}
    check("tools/ root (tracked) is exactly the sealed facade closure", root_tracked == closure,
          str(sorted(root_tracked ^ closure)))
    root_disk_files = {f"tools/{p.name}" for p in disk("tools").iterdir() if p.is_file()}
    check("tools/ root (disk) holds no file outside the sealed facade closure", root_disk_files == closure,
          str(sorted(root_disk_files ^ closure)))
    root_disk_dirs = {p.name for p in disk("tools").iterdir() if p.is_dir() and p.name != "__pycache__"}
    check("tools/ subdirectories are exactly the stage/topic set", root_disk_dirs == TOOLS_DIRS,
          str(sorted(root_disk_dirs ^ TOOLS_DIRS)))
    check("no __init__.py under tools/", not any(f.startswith("tools/") and f.endswith("/__init__.py") for f in files))
    check("no move targets the tools/ root", not any(n.startswith("tools/") and n.count("/") == 1 for n in news))
    check("no sealed closure module is moved", not (olds & closure))

    # ---- every move
    kinds = {"pure": 0, "repaired": 0, "active": 0}
    for m in moves:
        old, new, kind = m["old"], m["new"], m["kind"]
        check(f"old path gone: {old}", old not in index and not disk(old).exists())
        present = new in index and disk(new).is_file()
        check(f"new path present: {new}", present)
        if not present:
            continue
        base_blob = git("show", f"{BASE}:{old}")
        current = disk(new).read_bytes()
        if kind == "pure":
            check(f"pure move byte-identical: {new}", current == base_blob)
        elif kind == "repaired":
            expected = apply_edits(base_blob, m.get("edits", []))
            check(f"repaired move equals base + declared edits: {new}", expected is not None and current == expected,
                  "a declared edit does not fit the base blob" if expected is None else "content differs")
        elif kind == "active":
            check(f"active move is a declared active document: {new}", new in ACTIVE_MOVED)
        else:
            check(f"known move kind: {new}", False, kind)
        kinds[kind] = kinds.get(kind, 0) + 1

    # ---- completeness of the move map
    base_files = git("ls-tree", "-r", "-z", "--name-only", BASE, "--", "docs", "tools").decode().split("\0")[:-1]
    retained = closure | {"docs/chat-handoff.md"}
    unaccounted = sorted(set(base_files) - olds - retained)
    check("every base docs/ and tools/ file is moved or deliberately retained", not unaccounted, str(unaccounted))
    check("every move source existed at the base", olds <= set(base_files), str(sorted(olds - set(base_files))))
    staged = {f for f in index if (f.startswith("docs/") or f.startswith("tools/")) and f.count("/") >= 2}
    extra = sorted(staged - news - ADDED_ALLOWED)
    check("every file in the new hierarchy is a move target or a declared addition", not extra, str(extra))
    missing_added = sorted(ADDED_REQUIRED - set(index))
    check("the transition's own files are tracked", not missing_added, str(missing_added))
    missing_c01 = sorted(CONTROLLER01_REQUIRED - set(index))
    check("the declared Controller-01 files are tracked", not missing_c01, str(missing_c01))
    for d in ("docs", "tools", "scripts"):
        stray = [p for p in untracked(d) if "__pycache__" not in p]
        check(f"no untracked files under {d}/", not stray, str(stray[:5]))

    # ---- immutable fov3d/, tests/, scenes/
    for d in ("fov3d", "tests", "scenes"):
        if d == "fov3d":
            diff = git("diff", BASE, "--", d, *[f":(exclude){f}" for f in sorted(CONTROLLER01_FOV3D)])
            check("fov3d/ differs from the base only by the declared Controller-01 additions", len(diff) == 0,
                  f"{len(diff)} diff bytes")
            at_base = set(git("ls-tree", "-r", "--name-only", BASE, "--", d).decode().split())
            new_fov3d = sorted({f for f in index if f.startswith("fov3d/")} - at_base)
            check("the only new fov3d/ files are the declared Controller-01 modules, absent at the base",
                  set(new_fov3d) <= CONTROLLER01_FOV3D and not (CONTROLLER01_FOV3D & at_base), str(new_fov3d))
        else:
            diff = git("diff", BASE, "--", d)
            check(f"{d}/ differs by zero bytes from the base", len(diff) == 0, f"{len(diff)} diff bytes")
        stray = [p for p in untracked(d) if "__pycache__" not in p]
        check(f"no untracked files under {d}/", not stray, str(stray[:5]))
    for tag, commit in TAGS.items():
        got = git("rev-parse", f"{tag}^{{commit}}").decode().strip()
        check(f"tag {tag} unchanged", got == commit, got)

    # ---- no obsolete paths in current code, scripts and active docs
    # This checker is excluded only because it names the obsolete paths it forbids.
    current_code = [f for f in files if (f.startswith("tools/") or f.startswith("scripts/"))
                    and f.endswith((".py", ".sh")) and f != "tools/repository/check_repository_layout.py"]
    for f in current_code + sorted(ACTIVE_DOCS & fileset):
        text = disk(f).read_text(encoding="utf-8")
        if f == "docs/chat-handoff.md" and text.count(HANDOFF_REMOVAL_SENTENCE) == 1:
            text = text.replace(HANDOFF_REMOVAL_SENTENCE, "")  # the accepted record of the removal itself
        stale = stale_references(text, olds)
        check(f"no obsolete moved path in {f}", not stale, str(sorted(set(stale))[:4]))
    for f in [f for f in files if f.startswith("scripts/") and f.endswith(".sh")]:
        missing = sorted({p for p in re.findall(r"tools/[A-Za-z0-9_/]+\.py", disk(f).read_text(encoding="utf-8"))
                          if not disk(p).is_file()})
        check(f"every tools path named by {f} exists", not missing, str(missing))

    # ---- README.md
    readme = disk("README.md").read_text(encoding="utf-8")
    hs = headings(readme)
    check("README has exactly one title", [t for lvl, t in hs if lvl == 1] == [README_TITLE], str(hs[:3]))
    check("README has exactly the two intended top-level sections",
          [t for lvl, t in hs if lvl == 2] == README_SECTIONS, str([t for lvl, t in hs if lvl == 2]))
    check("README has no deeper headings", not [t for lvl, t in hs if lvl > 2], str([t for lvl, t in hs if lvl > 2]))

    # ---- CLAUDE.md
    claude = disk("CLAUDE.md").read_text(encoding="utf-8")
    low, flat = claude.lower(), squash(claude)
    bad = [p for p in CLAUDE_FORBIDDEN if p.lower() in low]
    check("CLAUDE.md has no obsolete Chat-write / stage / convention wording", not bad, str(bad))
    missing = [p for p in CLAUDE_REQUIRED if squash(p) not in flat]
    check("CLAUDE.md states the agreed stage, workflow and rules", not missing, str([m[:60] for m in missing]))

    # ---- Markdown links
    active_links = broken_active = all_links = broken_all = 0
    for f in [f for f in files if f.endswith(".md")]:
        for line, target, ok in markdown_links(f):
            all_links += 1
            broken_all += not ok
            if f in ACTIVE_DOCS or f.startswith("docs/repository/"):
                active_links += 1
                broken_active += not ok
            if not ok:
                check(f"link resolves: {f}:{line} -> {target}", False)
    check("active documentation links resolve", broken_active == 0, f"{broken_active} broken")

    # ---- accepted status in the active architecture documents
    ccmap = disk("docs/conceptual-core/conceptual-core-map.md").read_text(encoding="utf-8")
    check("conceptual-core map marks Core 14 accepted",
          "Conceptual Core 14 separation (accepted)" in ccmap and "**Conceptual Core 14 (accepted)**" in ccmap
          and "Cores 1-14 were verified and accepted" in ccmap)
    check("conceptual-core map has no stale Core-14 proposal status",
          not re.search(r"Core 14[^\n]*\(proposed|proposed \(measured\)|Proposed Conceptual Core 14", ccmap))
    for f in ("docs/architecture/current-architecture-map.md", "docs/architecture/fov3d-api.md"):
        text = squash(disk(f).read_text(encoding="utf-8"))
        check(f"{f} states Core 14 accepted, migration paused, controller next",
              "accepted through Conceptual Core 14" in text and "paused" in text
              and "Integrated Foveal Controller" in text)
    handoff = disk("docs/chat-handoff.md").read_text(encoding="utf-8")
    check("chat handoff records accepted main at Repository Stage Transition 1, Core 14 the scientific milestone",
          "main @ b12bdef0593a043c5e7593b38d78735875c007fd" in handoff
          and "REPOSITORY_STAGE_TRANSITION_1_PRESERVES_SCIENTIFIC_BEHAVIOR" in handoff
          and "`296001e8683ba0b1ad62642811d3dea0e84b6566`" in handoff)
    check("chat handoff records the transition as accepted, not proposed",
          "## Repository Stage Transition 1 (accepted at `b12bdef`)" in handoff
          and "proposed, not accepted" not in handoff)

    print(f"{PREFIX} moves={len(moves)} pure={kinds['pure']} repaired={kinds['repaired']} active={kinds['active']} "
          f"root_tools={len(root_tracked)} markdown_links={all_links} active_links={active_links} "
          f"broken_links={broken_all}")
    print(f"{PREFIX} SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
