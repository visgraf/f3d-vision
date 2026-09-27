#!/usr/bin/env python3
"""Fail-capable checks for Conceptual Core 7 target-component lineage extraction."""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fov3d.scene.lineage as lineage_module
from fov3d.scene.lineage import _lineage, _target_component_raster
from fov3d.scene.model import ObjectHypothesis, PartitionRegion, RegionKind, ScenePartitionGraph

MOVED = ("_lineage", "_target_component_raster")
KEYS = ["initial", "births", "merges", "splits", "deaths", "persistent_links"]
RETIRED = "[partition-graph4-lineage-fix] RETIRED"
TOOL = ROOT / "tools" / "dev" / "apply_partition_graph4_lineage_fix.py"
JOINT = ROOT / "fov3d" / "experiments" / "classroom_partition" / "joint.py"


def _counts(d: dict) -> tuple:
    return tuple(d[k] for k in KEYS)


def _typed(d: dict) -> bool:
    return list(d) == KEYS and type(d["initial"]) is bool and all(type(d[k]) is int for k in KEYS[1:])


def _row(*codes: int) -> np.ndarray:
    return np.array([codes], np.int32)


def _fresh(body: str) -> dict:
    code = f"import json, sys\nsys.path.insert(0, {str(ROOT)!r})\n{body}"
    proc = subprocess.run([sys.executable, "-I", "-c", code], cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        return {}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {}


def main() -> int:
    checked = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal checked, failed
        checked += 1
        if condition:
            print(f"[conceptual-core7-check] PASS {name}")
        else:
            failed += 1
            print(f"[conceptual-core7-check] FAIL {name}")

    # ---- _lineage
    init = _lineage(None, np.array([[-5, 0, 3, 3, 7]], np.int32))
    check("initial: exact values, key order and Python types",
          init == {"initial": True, "births": 2, "merges": 0, "splits": 0, "deaths": 0, "persistent_links": 0}
          and _typed(init))

    a = np.zeros((5, 5), np.int32)
    a[1:4, 1:4] = 1
    stable = _lineage(a, a.copy())
    check("stable one-component persistence",
          _counts(stable) == (False, 0, 0, 0, 0, 1) and _typed(stable))

    check("birth", _counts(_lineage(_row(1, 1, 0, 0), _row(1, 1, 0, 2))) == (False, 1, 0, 0, 0, 1))
    check("death", _counts(_lineage(_row(1, 1, 0, 2), _row(1, 1, 0, 0))) == (False, 0, 0, 0, 1, 1))
    check("merge: two previous components overlap one current",
          _counts(_lineage(_row(1, 1, 0, 2, 2), _row(1, 1, 1, 1, 1))) == (False, 0, 1, 0, 0, 0))
    check("split: one previous component overlaps two current",
          _counts(_lineage(_row(1, 1, 1, 1, 1), _row(1, 1, 0, 2, 2))) == (False, 0, 0, 1, 0, 2))

    # Mixed: C1 <- {P1, P2} merge; P3 -> {C2, C3} split; P4 dies; P5 -> C5 persists;
    # C4 and C6 are born.  births 2, merges 1, splits 1, deaths 1, persistent 3.
    prev = _row(1, 1, 2, 2, 0, 3, 3, 3, 0, 4, 0, 5, 0, 0)
    curr = _row(1, 1, 1, 1, 0, 2, 0, 3, 0, 0, 0, 5, 6, 4)
    mixed = _lineage(prev, curr)
    check("mixed fixture: births/merges/splits/deaths/persistent_links",
          _counts(mixed) == (False, 2, 1, 1, 1, 3) and _typed(mixed))

    check("int32 coercion of float previous and current labels",
          _counts(_lineage(_row(0, 2, 2), np.array([[0.0, 2.7, 2.2]]))) == (False, 0, 0, 0, 0, 1)
          and _counts(_lineage(np.array([[0.0, 2.7, 2.2]]), _row(0, 2, 2))) == (False, 0, 0, 0, 0, 1))
    check("zero and negative codes are not components",
          _counts(_lineage(_row(-1, 1, 0), _row(-1, 1, 0))) == (False, 0, 0, 0, 0, 1)
          and _counts(_lineage(_row(-1, -1, 0), _row(0, -1, -1))) == (False, 0, 0, 0, 0, 0))

    def _shape_error(p: np.ndarray, c: np.ndarray) -> bool:
        try:
            _lineage(p, c)
        except ValueError as exc:
            return str(exc) == "lineage raster shape mismatch"
        return False

    check("shape mismatch raises the exact ValueError (also when broadcastable)",
          _shape_error(np.ones((2, 2), np.int32), np.ones((2, 3), np.int32))
          and _shape_error(np.ones((1, 3), np.int32), np.ones((2, 3), np.int32)))

    # ---- _target_component_raster
    rc = np.array([[5, 5, 2, 3],
                   [9, 3, 2, 4],
                   [9, 9, 3, 5]], np.int32)

    def _reg(rid: str, code: int, kind: RegionKind = RegionKind.OBJECT_COMPONENT) -> PartitionRegion:
        # A decoy "region_code" attribute must never be read.
        return PartitionRegion(rid, kind, attributes={"state_region_code": code, "region_code": 100 + code})

    graph = ScenePartitionGraph(
        regions={
            "obj:7:c001": _reg("obj:7:c001", 9),
            "obj:7:c002": _reg("obj:7:c002", 5),
            "obj:7:c010": _reg("obj:7:c010", 2),
            "base:c001": _reg("base:c001", 3, RegionKind.BASE),
            "obj:8:c001": _reg("obj:8:c001", 4),
        },
        # Stored order is neither lexical (c001 < c002 < c010) nor by code (2 < 5 < 9).
        objects={"7": ObjectHypothesis("7", ("obj:7:c002", "obj:7:c010", "obj:7:c001")),
                 "8": ObjectHypothesis("8", ("obj:8:c001",))},
    )
    missing = _target_component_raster(graph, rc, 99)
    check("missing object gives an all-zero int32 raster of the right shape",
          missing.dtype == np.int32 and missing.shape == rc.shape and not missing.any())
    labels = _target_component_raster(graph, rc, 7)
    expected = np.array([[1, 1, 2, 0],
                         [3, 0, 2, 0],
                         [3, 3, 0, 1]], np.int32)
    check("stored region_ids order gives local labels 1..k via state_region_code",
          labels.dtype == np.int32 and np.array_equal(labels, expected))
    check("local labels are exactly 1..k and non-target cells stay zero",
          sorted(int(v) for v in np.unique(labels)) == [0, 1, 2, 3]
          and not labels[(rc == 3) | (rc == 4)].any())
    check("string target key lookup", np.array_equal(_target_component_raster(graph, rc, 8), (rc == 4).astype(np.int32)))

    # ---- compatibility, duplication, dependencies, footprints
    from fov3d.experiments.classroom_partition import joint
    check("joint compatibility identities", all(getattr(joint, n) is getattr(lineage_module, n) for n in MOVED))
    joint_defs = {n.name for n in ast.parse(JOINT.read_text(encoding="utf-8")).body
                  if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    check("joint contains no duplicate lineage definitions", not (set(MOVED) & joint_defs))

    lin_tree = ast.parse((ROOT / "fov3d" / "scene" / "lineage.py").read_text(encoding="utf-8"))
    lin_imports = set()
    for node in ast.walk(lin_tree):
        if isinstance(node, ast.ImportFrom):
            lin_imports.add(("." * node.level) + (node.module or ""))
        elif isinstance(node, ast.Import):
            lin_imports.update(a.name for a in node.names)
    check("scene.lineage imports only numpy, typing and scene.model (no fov3d.experiments)",
          lin_imports <= {"__future__", "typing", "numpy", ".model", "fov3d.scene.model"}
          and not any(m.startswith("fov3d.experiments") for m in lin_imports))

    via_joint = []
    for path in sorted((ROOT / "fov3d").rglob("*.py")):
        if path.name == "joint.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.ImportFrom) and (node.module or "").endswith("classroom_partition.joint")
                    and set(MOVED) & {a.name for a in node.names}):
                via_joint.append(path.name)
    check("no production module takes lineage from joint", not via_joint)

    bare = _fresh(
        "import fov3d.scene\n"
        "print(json.dumps({k: k in sys.modules for k in ['cv2', 'fov3d.scene.partition', "
        "'fov3d.scene.boundaries', 'fov3d.scene.corridors', 'fov3d.scene.lineage']}))\n"
    )
    check("fresh bare import fov3d.scene loads none of cv2/partition/boundaries/corridors/lineage",
          len(bare) == 5 and not any(bare.values()))
    direct = _fresh(
        "import fov3d.scene.lineage\n"
        "print(json.dumps({k: k in sys.modules for k in ['cv2', 'fov3d.scene.partition', "
        "'fov3d.scene.boundaries', 'fov3d.scene.corridors']}))\n"
    )
    check("fresh import fov3d.scene.lineage is NumPy-only", len(direct) == 4 and not any(direct.values()))

    # ---- retired historical fix tool
    tool_tree = ast.parse(TOOL.read_text(encoding="utf-8"))
    tool_imports = {a.name for n in ast.walk(tool_tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    tool_calls = {(n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", ""))
                  for n in ast.walk(tool_tree) if isinstance(n, ast.Call)}
    check("retired tool has no write or source-replacement capability",
          tool_imports <= {"annotations"}
          and not tool_calls & {"open", "write", "write_text", "write_bytes", "replace", "unlink",
                                "rename", "remove", "system", "run", "Popen", "exec", "eval"})
    before = hashlib.sha256(JOINT.read_bytes()).hexdigest()
    proc = subprocess.run([sys.executable, str(TOOL)], cwd=ROOT, capture_output=True, text=True)
    after = hashlib.sha256(JOINT.read_bytes()).hexdigest()
    check("retired tool prints the exact RETIRED marker, exits 0 and leaves joint.py unchanged",
          proc.returncode == 0 and proc.stdout == RETIRED + "\n" and before == after)

    print(f"[conceptual-core7-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
