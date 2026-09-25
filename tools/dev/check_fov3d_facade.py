#!/usr/bin/env python3
"""Structural checker for the Consolidation-3 conceptual API facade."""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path


def comparable(v):
    return isinstance(v, (str, bytes, int, float, bool, type(None), tuple, frozenset))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--layout", type=Path, default=None)
    ns = ap.parse_args()
    repo = ns.repo.resolve()
    layout = ns.layout or repo / "docs" / "consolidation-3-layout.json"
    spec = json.loads(layout.read_text(encoding="utf-8"))

    sys.path.insert(0, str(repo))
    failures = []
    checked = 0
    try:
        for row in spec["mappings"]:
            old = importlib.import_module(row["legacy"])
            new = importlib.import_module(row["new"])
            checked += 1
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
    finally:
        try:
            sys.path.remove(str(repo))
        except ValueError:
            pass

    if failures:
        for f in failures:
            print(f"[consolidation3-facade-check] FAIL {f}")
        print(f"[consolidation3-facade-check] SUMMARY checked={checked} failed={len(failures)}")
        return 1
    print(f"[consolidation3-facade-check] SUMMARY checked={checked} failed=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
