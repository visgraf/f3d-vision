#!/usr/bin/env python3
"""Structural checker for the Consolidation-3 conceptual API facade.

Each mapping is checked in the interpreter that can load its sealed module: the host
interpreter for most, Blender for the two whose sealed module imports ``bpy`` at module
level (tools.bl_common, tools.render_foveated).  The per-mapping check is the same in
both.  A mapping that needs Blender counts as a failure if Blender is unavailable.
"""
from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path

PREFIX = "[consolidation3-facade-check]"
BLENDER_ONLY_DEPENDENCIES = {"bpy", "mathutils", "bmesh"}


def comparable(v):
    return isinstance(v, (str, bytes, int, float, bool, type(None), tuple, frozenset))


def check_row(row: dict, repo: Path) -> list[str]:
    failures: list[str] = []
    old = importlib.import_module(row["legacy"])
    new = importlib.import_module(row["new"])
    if getattr(new, "__legacy_module__", None) != row["legacy"]:
        failures.append(f"{row['new']}: wrong __legacy_module__")
    public = getattr(old, "__all__", [n for n in dir(old) if not n.startswith("_")])
    for name in public:
        if not hasattr(new, name):
            failures.append(f"{row['new']}: missing public name {name}")
            continue
        a = getattr(old, name)
        b = getattr(new, name)
        if callable(a) or isinstance(a, type):
            if b is not a:
                failures.append(f"{row['new']}.{name}: callable not identical to sealed implementation")
        elif comparable(a) and b != a:
            failures.append(f"{row['new']}.{name}: value differs from sealed implementation")
    new_file = Path(new.__file__).resolve()
    if repo not in new_file.parents:
        failures.append(f"{row['new']}: imported outside permanent repo: {new_file}")
    old_file = Path(old.__file__).resolve()
    if old_file.parent != repo / "tools":
        failures.append(f"{row['legacy']}: sealed module resolved outside {repo / 'tools'}: {old_file}")
    return failures


def check_row_in_blender(row: dict, repo: Path, blender: str) -> list[str]:
    """Run check_row inside Blender's Python on the same repo and return its failures."""
    expr = (
        "import sys, json, importlib.util\n"
        "sys.dont_write_bytecode = True\n"
        f"sys.path.insert(0, {str(repo)!r})\n"
        "import fov3d\n"
        f"spec = importlib.util.spec_from_file_location('facade_check', {str(Path(__file__).resolve())!r})\n"
        "mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)\n"
        f"row = json.loads({json.dumps(row)!r})\n"
        "try:\n"
        f"    fails = mod.check_row(row, __import__('pathlib').Path({str(repo)!r}))\n"
        "except Exception as exc:\n"
        "    fails = [f\"{row['new']}: {type(exc).__name__}: {exc}\"]\n"
        "print('FACADEROW' + json.dumps(fails))\n"
    )
    try:
        p = subprocess.run([blender, "-b", "--factory-startup", "--python-exit-code", "1", "--python-expr", expr],
                           capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f"{row['new']}: needs Blender ({type(exc).__name__}: {exc})"]
    line = next((l for l in p.stdout.splitlines() if l.startswith("FACADEROW")), None)
    if line is None:
        tail = " | ".join((p.stdout + p.stderr).strip().splitlines()[-3:])
        return [f"{row['new']}: Blender check produced no result (exit {p.returncode}): {tail}"]
    return json.loads(line[len("FACADEROW"):])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--layout", type=Path, default=None)
    ap.add_argument("--blender", default="blender")
    ns = ap.parse_args()
    repo = ns.repo.resolve()
    layout = ns.layout or repo / "docs" / "consolidation-3-layout.json"
    spec = json.loads(layout.read_text(encoding="utf-8"))

    sys.path.insert(0, str(repo))
    failures = []
    checked = 0
    try:
        import fov3d  # noqa: F401  (package plumbing: puts the sealed tools/ on sys.path)
        for row in spec["mappings"]:
            try:
                failures += check_row(row, repo)
                where = "host"
            except ModuleNotFoundError as exc:
                if exc.name not in BLENDER_ONLY_DEPENDENCIES:
                    failures.append(f"{row['new']}: {type(exc).__name__}: {exc}")
                    checked += 1
                    continue
                failures += check_row_in_blender(row, repo, ns.blender)
                where = "blender"
            checked += 1
            print(f"{PREFIX} checked {row['new']} -> {row['legacy']} ({where})")
    finally:
        try:
            sys.path.remove(str(repo))
        except ValueError:
            pass

    if failures:
        for f in failures:
            print(f"{PREFIX} FAIL {f}")
        print(f"{PREFIX} SUMMARY checked={checked} failed={len(failures)}")
        return 1
    print(f"{PREFIX} SUMMARY checked={checked} failed=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
