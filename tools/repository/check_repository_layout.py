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
as accepted for Integrated Foveal Controller 01 (INCOMPLETE; no global-quiescence claim).
Controller-01A declares its audit contract (required) and report (allowed); the handoff records
Controller-01A accepted. Preview/visual lifecycle Policy 1 declares
docs/methodology/preview-visual-policy.md (required); the handoff records Policy 1 accepted. The
Controller-01 visual retrofit declares its contract (required), report and generator (allowed); the
handoff records the visual package accepted. Controller-01B declares its contract (required), report
and tool (allowed); the handoff records Controller-01B accepted. Controller-01C declares its audit
contract (required), report and tool (allowed); the handoff records Controller-01C accepted. Foveal
Controller Stage Charter 1 declares docs/methodology/foveal-controller-stage-charter-1.md (required); the
handoff records the charter accepted. Controller-02 declares its contract (required), report and tools
(allowed), and its two fov3d modules as allowed additions (every pre-existing fov3d file stays identical);
the handoff records Controller-02 accepted (SCENE_CLOSED, not global quiescence). Visual Language 1
declares its contract (required), its methodology document, report and tools/visual_language/ tools (allowed).
Breadth-1 declares its contract (required), report and five tools/classroom_oracle/breadth1_* / check tools
(allowed). Natural Bootstrap-1a adds the docs/natural-bootstrap/ and tools/natural_bootstrap/ directories and
declares its contract (required), report and six tools (allowed); the handoff records NB1a accepted.
Natural Bootstrap-1b declares its contract (required), report and five tools/natural_bootstrap/ nb1b tools (allowed);
the handoff records NB1b accepted and the post-NB1b pivot to NB1c. Natural Bootstrap-1c declares its contract
(required), report and five tools/natural_bootstrap/ nb1c tools (allowed); the handoff records NB1c accepted and
the start of Active Bootstrap (AB1a executes RGB gaze #1 exactly once). Active Bootstrap-1a adds the
docs/active-bootstrap/ and tools/active_bootstrap/ directories and declares its contract (required), report and six
tools/active_bootstrap/ ab1a tools (allowed); the handoff records AB1a accepted and the post-AB1a pivot to
spherical epipolar geometry (AB1b tests representation only, with perfect correspondence). Active Bootstrap-1b
declares its contract (required), report and six tools/active_bootstrap/ ab1b tools (allowed); the handoff records
AB1b accepted and the post-AB1b operating strategy (AB1c compares planar and spherical geometry in a favorable
safe-forward regime, with perfect correspondence). Active Bootstrap-1c declares its contract (required), report and eight
tools/active_bootstrap/ ab1c tools (allowed); the handoff records AB1c accepted and the post-AB1c step (AB1d tests
natural RGB correspondence in the safe-forward regime, with the accepted spherical geometry held fixed). Active
Bootstrap-1d declares its contract (required), report and six tools/active_bootstrap/ ab1d tools (allowed); the handoff
records AB1d accepted as a negative experiment and the post-AB1d step (AB1d2 tests whether substantially reducing Monte
Carlo rendering noise improves the same frozen matcher; it changes observation quality only). Active Bootstrap-1d2
declares its contract (required), report and six tools/active_bootstrap/ ab1d2 tools (allowed); the handoff records
AB1d2 accepted and the post-AB1d2 decision (the SGBM bet: AB1d3 is one bounded natural-stereo attempt with one frozen
SGBM configuration; otherwise natural stereo is deferred and the North Star uses PERFECT correspondence). Active
Bootstrap-1d3 declares its contract (required), report and seven tools/active_bootstrap/ ab1d3 tools (allowed); the
handoff records AB1d3 accepted (Outcome 2; SGBM not adopted) and the return to the North Star (natural stereo deferred;
the North Star uses PERFECT / oracle correspondence; North Star-1a is next). North Star-1a adds the docs/north-star/
directory and declares its contract (required), report and eight tools/north_star/ ns1a tools (allowed); its
implementation adds the tools/north_star/ directory. The handoff records NS1a accepted (Outcome 1 with Outcome-2
elements; 13 initialized seeds) and the post-NS1a decision (North Star-1b: a recentered local-controller handoff with
one action, through a temporary policy coordinate chart, not physical head motion). North Star-1b declares its contract
(required), report and ten tools/north_star/ ns1b tools (allowed). The handoff records NS1b accepted (Outcome 1; the
bootstrap-to-controller bridge established) and the post-NS1b decision (North Star-1c: coherent multi-entity control,
first scene switch, continuing from the accepted NS1b state; multi-part oracle identities deferred).
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

DOCS_DIRS = {"active-bootstrap", "architecture", "baseline", "classroom-oracle", "consolidation", "conceptual-core",
             "controller", "methodology", "natural-bootstrap", "north-star", "partition-graph", "repository"}
TOOLS_DIRS = {"active_bootstrap", "baseline", "classroom_oracle", "conceptual_core", "consolidation", "controller",
              "natural_bootstrap", "north_star", "partition_graph", "repository", "visual_language"}
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
CONTROLLER02_FOV3D = {"fov3d/control/controller02.py", "fov3d/experiments/classroom_oracle/controller02.py"}
CONTROLLER02_REQUIRED = {"docs/controller/controller-02-residual-closure-contract.md"}
CONTROLLER02_ALLOWED = CONTROLLER02_REQUIRED | {"docs/controller/controller-02-residual-closure-report.md",
                                                "tools/controller/check_controller02.py",
                                                "tools/controller/visualize_controller02.py"}
CONTROLLER01A_REQUIRED = {"docs/controller/controller-01a-terminal-audit-contract.md"}
CONTROLLER01A_ALLOWED = CONTROLLER01A_REQUIRED | {"docs/controller/controller-01a-terminal-audit-report.md"}
POLICY1_REQUIRED = {"docs/methodology/preview-visual-policy.md"}
CHARTER1_REQUIRED = {"docs/methodology/foveal-controller-stage-charter-1.md"}
C01_VISUALS_REQUIRED = {"docs/controller/controller-01-visuals-contract.md"}
C01_VISUALS_ALLOWED = C01_VISUALS_REQUIRED | {"docs/controller/controller-01-visuals-report.md",
                                              "tools/controller/visualize_controller01.py"}
CONTROLLER01B_REQUIRED = {"docs/controller/controller-01b-single-continuation-contract.md"}
CONTROLLER01B_ALLOWED = CONTROLLER01B_REQUIRED | {"docs/controller/controller-01b-single-continuation-report.md",
                                                  "tools/controller/controller01b.py"}
CONTROLLER01C_REQUIRED = {"docs/controller/controller-01c-frontier-action-correspondence-contract.md"}
CONTROLLER01C_ALLOWED = CONTROLLER01C_REQUIRED | {"docs/controller/controller-01c-frontier-action-correspondence-report.md",
                                                  "tools/controller/controller01c.py"}
VL1_REQUIRED = {"docs/methodology/visual-language-1-contract.md"}
VL1_TOOLS = {f"tools/visual_language/{n}" for n in ("style.py", "vl1_data.py", "vl1_draw.py", "generate_visual_language1.py",
                                                      "render_reference_view.py", "check_visual_language1.py")}
VL1_ALLOWED = VL1_REQUIRED | VL1_TOOLS | {"docs/methodology/visual-language-1.md",
                                         "docs/methodology/visual-language-1-report.md"}
BREADTH1_REQUIRED = {"docs/classroom-oracle/breadth-1-spherical-glance-contract.md"}
BREADTH1_TOOLS = {f"tools/classroom_oracle/{n}" for n in ("breadth1_spec.py", "breadth1_render.py", "breadth1_glance.py",
                                                            "breadth1_visuals.py", "check_breadth1.py")}
BREADTH1_ALLOWED = BREADTH1_REQUIRED | BREADTH1_TOOLS | {"docs/classroom-oracle/breadth-1-spherical-glance-report.md"}
NB1A_REQUIRED = {"docs/natural-bootstrap/nb1a-range-connectivity-contract.md"}
NB1A_TOOLS = {f"tools/natural_bootstrap/{n}" for n in ("nb1a_spec.py", "nb1a_guard.py", "nb1a_discovery.py",
                                                         "nb1a_run.py", "nb1a_visuals.py", "check_nb1a.py")}
NB1A_ALLOWED = NB1A_REQUIRED | NB1A_TOOLS | {"docs/natural-bootstrap/nb1a-range-connectivity-report.md"}
NB1B_REQUIRED = {"docs/natural-bootstrap/nb1b-foveal-serviceability-contract.md"}
NB1B_TOOLS = {f"tools/natural_bootstrap/{n}" for n in ("nb1b_spec.py", "nb1b_serviceability.py", "nb1b_run.py",
                                                         "nb1b_visuals.py", "check_nb1b.py")}
NB1B_ALLOWED = NB1B_REQUIRED | NB1B_TOOLS | {"docs/natural-bootstrap/nb1b-foveal-serviceability-report.md"}
NB1C_REQUIRED = {"docs/natural-bootstrap/nb1c-rgb-candidate-gaze-contract.md"}
NB1C_TOOLS = {f"tools/natural_bootstrap/{n}" for n in ("nb1c_spec.py", "nb1c_attention.py", "nb1c_run.py",
                                                         "nb1c_visuals.py", "check_nb1c.py")}
NB1C_ALLOWED = NB1C_REQUIRED | NB1C_TOOLS | {"docs/natural-bootstrap/nb1c-rgb-candidate-gaze-report.md"}
AB1A_REQUIRED = {"docs/active-bootstrap/ab1a-first-natural-stereo-look-contract.md"}
AB1A_TOOLS = {f"tools/active_bootstrap/{n}" for n in ("ab1a_spec.py", "ab1a_render.py", "ab1a_stereo.py", "ab1a_run.py",
                                                      "ab1a_visuals.py", "check_ab1a.py")}
AB1A_ALLOWED = AB1A_REQUIRED | AB1A_TOOLS | {"docs/active-bootstrap/ab1a-first-natural-stereo-look-report.md"}
AB1B_REQUIRED = {"docs/active-bootstrap/ab1b-spherical-epipolar-geometry-contract.md"}
AB1B_TOOLS = {f"tools/active_bootstrap/{n}" for n in ("ab1b_spec.py", "ab1b_oracle.py", "ab1b_geometry.py", "ab1b_run.py",
                                                      "ab1b_visuals.py", "check_ab1b.py")}
AB1B_ALLOWED = AB1B_REQUIRED | AB1B_TOOLS | {"docs/active-bootstrap/ab1b-spherical-epipolar-geometry-report.md"}
AB1C_REQUIRED = {"docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-contract.md"}
AB1C_TOOLS = {f"tools/active_bootstrap/{n}" for n in ("ab1c_spec.py", "ab1c_select.py", "ab1c_planar.py", "ab1c_render.py",
                                                      "ab1c_run.py", "ab1c_synthetic.py", "ab1c_visuals.py",
                                                      "check_ab1c.py")}
AB1C_ALLOWED = AB1C_REQUIRED | AB1C_TOOLS | {"docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-report.md"}
AB1D_REQUIRED = {"docs/active-bootstrap/ab1d-safe-forward-natural-correspondence-contract.md"}
AB1D_TOOLS = {f"tools/active_bootstrap/{n}" for n in ("ab1d_spec.py", "ab1d_match.py", "ab1d_run.py",
                                                      "ab1d_synthetic.py", "ab1d_visuals.py", "check_ab1d.py")}
AB1D_ALLOWED = AB1D_REQUIRED | AB1D_TOOLS | {"docs/active-bootstrap/ab1d-safe-forward-natural-correspondence-report.md"}
AB1D2_REQUIRED = {"docs/active-bootstrap/ab1d2-4096spp-observation-quality-contract.md"}
AB1D2_TOOLS = {f"tools/active_bootstrap/{n}" for n in ("ab1d2_spec.py", "ab1d2_render.py", "ab1d2_run.py",
                                                       "ab1d2_preflight.py", "ab1d2_visuals.py", "check_ab1d2.py")}
AB1D2_ALLOWED = AB1D2_REQUIRED | AB1D2_TOOLS | {"docs/active-bootstrap/ab1d2-4096spp-observation-quality-report.md"}
AB1D3_REQUIRED = {"docs/active-bootstrap/ab1d3-sgbm-viability-contract.md"}
AB1D3_TOOLS = {f"tools/active_bootstrap/{n}" for n in ("ab1d3_spec.py", "ab1d3_sgbm.py", "ab1d3_run.py",
                                                       "ab1d3_synthetic.py", "ab1d3_visuals.py", "check_ab1d3.py",
                                                       "check_ab1d3_core.py")}
AB1D3_ALLOWED = AB1D3_REQUIRED | AB1D3_TOOLS | {"docs/active-bootstrap/ab1d3-sgbm-viability-report.md"}
NS1A_REQUIRED = {"docs/north-star/ns1a-perfect-bootstrap-round-contract.md"}
NS1A_TOOLS = {f"tools/north_star/{n}" for n in ("ns1a_spec.py", "ns1a_render.py", "ns1a_core.py", "ns1a_run.py",
                                                "ns1a_synthetic.py", "ns1a_visuals.py", "check_ns1a.py",
                                                "check_ns1a_corruptions.py")}
NS1A_ALLOWED = NS1A_REQUIRED | NS1A_TOOLS | {"docs/north-star/ns1a-perfect-bootstrap-round-report.md"}
NS1B_REQUIRED = {"docs/north-star/ns1b-recentered-controller-handoff-contract.md"}
NS1B_TOOLS = {f"tools/north_star/{n}" for n in ("ns1b_spec.py", "ns1b_chart.py", "ns1b_core.py", "ns1b_render.py",
                                                "ns1b_run.py", "ns1b_synthetic.py", "ns1b_fixtures.py",
                                                "ns1b_visuals.py", "check_ns1b.py", "check_ns1b_corruptions.py")}
NS1B_ALLOWED = NS1B_REQUIRED | NS1B_TOOLS | {"docs/north-star/ns1b-recentered-controller-handoff-report.md"}
ADDED_ALLOWED = (ADDED_REQUIRED | {"docs/repository/repository-transition-1-report.md"} | CONTROLLER01_ALLOWED
                 | CONTROLLER01A_ALLOWED | POLICY1_REQUIRED | C01_VISUALS_ALLOWED | CONTROLLER01B_ALLOWED
                 | CONTROLLER01C_ALLOWED | CHARTER1_REQUIRED | CONTROLLER02_ALLOWED | VL1_ALLOWED | BREADTH1_ALLOWED
                 | NB1A_ALLOWED | NB1B_ALLOWED | NB1C_ALLOWED | AB1A_ALLOWED | AB1B_ALLOWED
                 | AB1C_ALLOWED | AB1D_ALLOWED | AB1D2_ALLOWED | AB1D3_ALLOWED | NS1A_ALLOWED | NS1B_ALLOWED)
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
    "An executed scientific/behavioral step must produce:",
    "- its run evidence under `./previews`;",
    "- at least one human-inspectable scientific visual under `./visuals`;",
    "- fail-capable checks;",
    "- a short Git-tracked report recording the result, the visual paths and the regeneration command.",
    "Diagnostic plots alone need not satisfy the visual requirement",
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
    missing_c01a = sorted(CONTROLLER01A_REQUIRED - set(index))
    check("the declared Controller-01A audit contract is tracked", not missing_c01a, str(missing_c01a))
    missing_p1 = sorted(POLICY1_REQUIRED - set(index))
    check("the preview/visual lifecycle policy document is tracked", not missing_p1, str(missing_p1))
    missing_ch1 = sorted(CHARTER1_REQUIRED - set(index))
    check("the Foveal Controller Stage Charter 1 document is tracked", not missing_ch1, str(missing_ch1))
    missing_v1 = sorted(C01_VISUALS_REQUIRED - set(index))
    check("the Controller-01 visuals contract is tracked", not missing_v1, str(missing_v1))
    missing_b = sorted(CONTROLLER01B_REQUIRED - set(index))
    check("the Controller-01B contract is tracked", not missing_b, str(missing_b))
    missing_c = sorted(CONTROLLER01C_REQUIRED - set(index))
    check("the Controller-01C audit contract is tracked", not missing_c, str(missing_c))
    missing_02 = sorted(CONTROLLER02_REQUIRED - set(index))
    check("the Controller-02 contract is tracked", not missing_02, str(missing_02))
    missing_vl1 = sorted(VL1_REQUIRED - set(index))
    check("the Visual Language 1 contract is tracked", not missing_vl1, str(missing_vl1))
    missing_b1 = sorted(BREADTH1_REQUIRED - set(index))
    check("the Breadth-1 contract is tracked", not missing_b1, str(missing_b1))
    missing_nb1a = sorted(NB1A_REQUIRED - set(index))
    check("the NB1a contract is tracked", not missing_nb1a, str(missing_nb1a))
    missing_nb1b = sorted(NB1B_REQUIRED - set(index))
    check("the NB1b contract is tracked", not missing_nb1b, str(missing_nb1b))
    missing_nb1c = sorted(NB1C_REQUIRED - set(index))
    check("the NB1c contract is tracked", not missing_nb1c, str(missing_nb1c))
    missing_ab1a = sorted(AB1A_REQUIRED - set(index))
    check("the AB1a contract is tracked", not missing_ab1a, str(missing_ab1a))
    missing_ab1b = sorted(AB1B_REQUIRED - set(index))
    check("the AB1b contract is tracked", not missing_ab1b, str(missing_ab1b))
    missing_ab1c = sorted(AB1C_REQUIRED - set(index))
    check("the AB1c contract is tracked", not missing_ab1c, str(missing_ab1c))
    missing_ab1d = sorted(AB1D_REQUIRED - set(index))
    check("the AB1d contract is tracked", not missing_ab1d, str(missing_ab1d))
    missing_ab1d2 = sorted(AB1D2_REQUIRED - set(index))
    check("the AB1d2 contract is tracked", not missing_ab1d2, str(missing_ab1d2))
    missing_ab1d3 = sorted(AB1D3_REQUIRED - set(index))
    check("the AB1d3 contract is tracked", not missing_ab1d3, str(missing_ab1d3))
    missing_ns1a = sorted(NS1A_REQUIRED - set(index))
    check("the NS1a contract is tracked", not missing_ns1a, str(missing_ns1a))
    missing_ns1b = sorted(NS1B_REQUIRED - set(index))
    check("the NS1b contract is tracked", not missing_ns1b, str(missing_ns1b))
    for d in ("docs", "tools", "scripts"):
        stray = [p for p in untracked(d) if "__pycache__" not in p]
        check(f"no untracked files under {d}/", not stray, str(stray[:5]))

    # ---- immutable fov3d/, tests/, scenes/
    for d in ("fov3d", "tests", "scenes"):
        if d == "fov3d":
            declared = CONTROLLER01_FOV3D | CONTROLLER02_FOV3D
            diff = git("diff", BASE, "--", d, *[f":(exclude){f}" for f in sorted(declared)])
            check("fov3d/ differs from the base only by the declared Controller-01/02 additions", len(diff) == 0,
                  f"{len(diff)} diff bytes")
            at_base = set(git("ls-tree", "-r", "--name-only", BASE, "--", d).decode().split())
            new_fov3d = sorted({f for f in index if f.startswith("fov3d/")} - at_base)
            check("the only new fov3d/ files are the declared Controller-01/02 modules, absent at the base",
                  set(new_fov3d) <= declared and not (declared & at_base), str(new_fov3d))
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
    check("chat handoff records accepted main at NS1b, with NS1a, AB1d3, AB1d2, AB1d, AB1c, AB1b, AB1a, NB1c, NB1b, "
          "NB1a, Breadth-1, Visual Language 1, Controller-02, Stage Charter 1, Controller-01C, Controller-01B, the "
          "Controller-01 visual package, Policy 1, Controller-01A, Controller-01, RT1 and Core 14 recorded",
          "main @ 255355108863022f931574dae4b2df8cdd2a772e" in handoff
          and "NORTH_STAR1B_RECENTERED_CONTROLLER_HANDOFF_ACCEPTED" in handoff
          and "NORTH_STAR1B_RECENTERED_CONTROLLER_HANDOFF_COMPLETE" in handoff
          and "NS1b is complete. The bootstrap-to-controller bridge is ESTABLISHED; North Star-1c, coherent "
              "multi-entity control with a first scene switch, is next." in squash(handoff)
          and "The multi-part oracle identities 10, 110 and 178 remain **DEFERRED** for this experiment."
          in squash(handoff)
          and "NORTH_STAR1A_PERFECT_BOOTSTRAP_ROUND_ACCEPTED" in handoff
          and "NORTH_STAR1A_PERFECT_BOOTSTRAP_ROUND_COMPLETE" in handoff
          and "NS1a is complete. The frozen NS1a seed set is the North-Star seed handoff; North Star-1b, a recentered "
              "local-controller handoff with ONE action, is next." in squash(handoff)
          and "NS1b uses a **TEMPORARY POLICY COORDINATE CHART**. It is **NOT physical head motion**." in squash(handoff)
          and "ACTIVE_BOOTSTRAP1D3_SGBM_VIABILITY_ACCEPTED" in handoff
          and "ACTIVE_BOOTSTRAP1D3_SGBM_VIABILITY_COMPLETE" in handoff
          and "AB1d3 is complete. NATURAL STEREO IS DEFERRED. The North-Star concept demonstration uses the validated "
              "PERFECT / ORACLE correspondence service; North Star-1a is next." in squash(handoff)
          and "ACTIVE_BOOTSTRAP1D2_4096SPP_OBSERVATION_QUALITY_ACCEPTED" in handoff
          and "ACTIVE_BOOTSTRAP1D2_4096SPP_OBSERVATION_QUALITY_COMPLETE" in handoff
          and "AB1d2 is complete. Natural stereo receives ONE additional bounded attempt: AB1d3, one-shot SGBM viability, "
              "on the accepted 4096-spp observations with one frozen pre-existing SGBM configuration and no parameter "
              "tuning or sweep." in squash(handoff)
          and "ACTIVE_BOOTSTRAP1D_SAFE_FORWARD_NATURAL_CORRESPONDENCE_ACCEPTED" in handoff
          and "ACTIVE_BOOTSTRAP1D_SAFE_FORWARD_NATURAL_CORRESPONDENCE_COMPLETE" in handoff
          and "AB1d is complete. The next experiment tests whether substantially reducing Monte Carlo rendering noise "
              "materially improves the SAME frozen primitive natural correspondence matcher. AB1d2 changes observation "
              "quality only; it does not redesign the matcher." in squash(handoff)
          and "ACTIVE_BOOTSTRAP1C_SAFE_FORWARD_PLANAR_SPHERICAL_ACCEPTED" in handoff
          and "ACTIVE_BOOTSTRAP1C_SAFE_FORWARD_PLANAR_SPHERICAL_COMPLETE" in handoff
          and "AB1c is complete. The next experiment tests natural RGB correspondence in the safe-forward regime, with "
              "the accepted spherical geometry held fixed." in squash(handoff)
          and "ACTIVE_BOOTSTRAP1B_SPHERICAL_EPIPOLAR_GEOMETRY_ACCEPTED" in handoff
          and "ACTIVE_BOOTSTRAP1B_SPHERICAL_EPIPOLAR_GEOMETRY_COMPLETE" in handoff
          and "AB1b is complete. The next experiment compares planar and spherical geometry in a favorable safe-forward "
              "regime, with perfect correspondence." in squash(handoff)
          and "ACTIVE_BOOTSTRAP1A_FIRST_NATURAL_STEREO_LOOK_ACCEPTED" in handoff
          and "ACTIVE_BOOTSTRAP1A_FIRST_NATURAL_STEREO_LOOK_COMPLETE" in handoff
          and "AB1a is complete. The next experiment tests binocular REPRESENTATION only, with perfect correspondence."
          in handoff
          and "NATURAL_BOOTSTRAP1C_RGB_CANDIDATE_GAZE_ACCEPTED" in handoff
          and "NATURAL_BOOTSTRAP1C_RGB_CANDIDATE_GAZE_COMPLETE" in handoff
          and "NB1c is complete. The next experiment executes RGB gaze #1 exactly once." in handoff
          and "NATURAL_BOOTSTRAP1B_FOVEAL_SERVICEABILITY_ACCEPTED" in handoff
          and "NATURAL_BOOTSTRAP1B_FOVEAL_SERVICEABILITY_COMPLETE" in handoff
          and "INITIAL BOOTSTRAP SHOULD NOT REQUIRE DEPTH." in handoff
          and "NATURAL_BOOTSTRAP1A_RANGE_CONNECTIVITY_ACCEPTED" in handoff
          and "NATURAL_BOOTSTRAP1A_RANGE_CONNECTIVITY_COMPLETE" in handoff
          and "BREADTH1_CLASSROOM234_SPHERICAL_GLANCE_ACCEPTED" in handoff
          and "BREADTH1_CLASSROOM234_SPHERICAL_GLANCE_COMPLETE" in handoff
          and "VISUAL_LANGUAGE_1_ACCEPTED" in handoff
          and "VISUAL_LANGUAGE_1_CANONICAL_DEMO_COMPLETE" in handoff
          and "CONTROLLER02_RESIDUAL_CLOSURE_ACCEPTED" in handoff
          and "CONTROLLER02_IMPLEMENTATION_CHECKS_PASS" in handoff
          and "CONTROLLER02_CLASSROOM_SCENE_CLOSED" in handoff
          and "FOVEAL_CONTROLLER_STAGE_CHARTER_1_ACCEPTED" in handoff
          and "CONTROLLER01C_FRONTIER_ACTION_AUDIT_ACCEPTED" in handoff
          and "CONTROLLER01C_FRONTIER_ACTION_CORRESPONDENCE_AUDIT_COMPLETE" in handoff
          and "CONTROLLER01B_SINGLE_CONTINUATION_ACCEPTED" in handoff
          and "CONTROLLER01B_ONE_LOOK_REPROBE_ACTIONABLE" in handoff
          and "CONTROLLER01_VISUAL_PACKAGE_ACCEPTED" in handoff
          and "PREVIEW_VISUAL_LIFECYCLE_POLICY_1_ACCEPTED" in handoff
          and "CONTROLLER01A_TERMINAL_AUDIT_ACCEPTED" in handoff
          and "INTEGRATED_FOVEAL_CONTROLLER01_ACCEPTED" in handoff
          and "REPOSITORY_STAGE_TRANSITION_1_PRESERVES_SCIENTIFIC_BEHAVIOR" in handoff
          and "`296001e8683ba0b1ad62642811d3dea0e84b6566`" in handoff)
    check("chat handoff does not claim Controller-01 global quiescence (the measured outcome is INCOMPLETE)",
          "CONTROLLER01_GLOBAL_QUIESCENCE_REACHED" not in handoff)
    check("chat handoff does not claim Controller-02 closure as global quiescence or record it NOT_CLOSED",
          "CONTROLLER02_GLOBAL_QUIESCENCE" not in handoff and "CONTROLLER02_CLASSROOM_NOT_CLOSED" not in handoff)
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
