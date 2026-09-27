#!/usr/bin/env python3
"""Fail-capable checks for Conceptual Core 10 corridor relation-origin extraction."""
from __future__ import annotations

import ast
import builtins
import dis
import json
import subprocess
import sys
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fov3d.scene.corridors as scene_corridors
from fov3d.scene.corridors import _joint_region_own_component, _own_labels, _region_code, relation_origin
from fov3d.scene.model import PartitionRegion, RegionKind, ScenePartitionGraph

MOVED = ("_region_code", "_own_labels", "_joint_region_own_component", "relation_origin")
CORRIDOR_EXISTING = ("_component_boundary", "_line_cells", "gap_corridor", "corridors_for_object")
ADAPTER_UNTOUCHED = ("own_support_labels", "component_lineage")
ACCEPTED_CORE9 = "518ff6ce4686238301f5ac946a5ea049e27ed9da"
ADAPTER = "fov3d/experiments/classroom_partition/relations.py"
CORRIDORS = "fov3d/scene/corridors.py"


def _git_show(path: str) -> str:
    proc = subprocess.run(["git", "show", f"{ACCEPTED_CORE9}:{path}"], cwd=ROOT, capture_output=True, text=True)
    return proc.stdout if proc.returncode == 0 else ""


def _defs(src: str) -> dict[str, tuple[str, str]]:
    tree = ast.parse(src)
    return {n.name: (ast.get_source_segment(src, n), ast.dump(n)) for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.ClassDef))}


def _imports(src: str) -> list[str]:
    return [ast.dump(n) for n in ast.parse(src).body if isinstance(n, (ast.Import, ast.ImportFrom))]


def _global_names(fn) -> set[str]:
    names: set[str] = set()
    stack = [fn.__code__]
    while stack:
        code = stack.pop()
        names.update(i.argval for i in dis.get_instructions(code) if i.opname in ("LOAD_GLOBAL", "LOAD_NAME"))
        stack.extend(c for c in code.co_consts if isinstance(c, types.CodeType))
    return names


def _outcome(fn, *args):
    try:
        return ("ok", fn(*args))
    except Exception as exc:  # noqa: BLE001 - the exception is the observation
        return (type(exc).__name__, str(exc))


def _fresh(body: str) -> dict:
    code = f"import json, sys\nsys.path.insert(0, {str(ROOT)!r})\n{body}"
    proc = subprocess.run([sys.executable, "-I", "-c", code], cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        return {}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {}


def _graph(codes: dict[str, object]) -> ScenePartitionGraph:
    return ScenePartitionGraph(regions={
        rid: PartitionRegion(rid, RegionKind.BASE, attributes={} if code is None else {"state_region_code": code})
        for rid, code in codes.items()
    })


def main() -> int:
    checked = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal checked, failed
        checked += 1
        if condition:
            print(f"[conceptual-core10-check] PASS {name}")
        else:
            failed += 1
            print(f"[conceptual-core10-check] FAIL {name}")

    # ---- A. literal migration against accepted Core 9 (read from Git)
    core9_adapter = _git_show(ADAPTER)
    core9_corridors = _git_show(CORRIDORS)
    old = _defs(core9_adapter) if core9_adapter else {}
    new = _defs((ROOT / CORRIDORS).read_text(encoding="utf-8"))
    check("source text of the four definitions is identical to accepted Core 9",
          bool(old) and all(old.get(n, ("", ""))[0] == new.get(n, (None, None))[0] for n in MOVED))
    check("AST of the four definitions is identical to accepted Core 9",
          bool(old) and all(old.get(n, ("", ""))[1] == new.get(n, (None, None))[1] for n in MOVED))
    bindings_ok = bool(core9_adapter)
    if core9_adapter:
        ref = types.ModuleType("_core9_relations_reference")
        sys.modules[ref.__name__] = ref
        exec(compile(core9_adapter, "core9_relations.py", "exec"), ref.__dict__)
        for name in MOVED:
            for g in _global_names(getattr(scene_corridors, name)):
                if g in MOVED:
                    continue
                a = scene_corridors.__dict__.get(g, getattr(builtins, g, None))
                b = ref.__dict__.get(g, getattr(builtins, g, None))
                bindings_ok &= a is not None and a is b
    check("global bindings are equivalent to accepted Core 9", bindings_ok)
    check("relation_origin helpers resolve to scene.corridors",
          relation_origin.__globals__["_own_labels"] is _own_labels
          and relation_origin.__globals__["_joint_region_own_component"] is _joint_region_own_component
          and _joint_region_own_component.__globals__["_region_code"] is _region_code)
    old_corr = _defs(core9_corridors) if core9_corridors else {}
    check("existing corridor functions are source-identical to accepted Core 9",
          bool(old_corr) and all(old_corr.get(n, ("",))[0] == new.get(n, (None,))[0] for n in CORRIDOR_EXISTING))
    check("scene.corridors import statements are unchanged from accepted Core 9",
          bool(core9_corridors) and _imports(core9_corridors) == _imports((ROOT / CORRIDORS).read_text(encoding="utf-8")))

    # ---- B. adapter compatibility
    from fov3d.experiments.classroom_partition import relations as adapter
    check("adapter re-exports the four identical objects",
          all(getattr(adapter, n, None) is getattr(scene_corridors, n) for n in MOVED))
    check("annotate_corridor resolves the scene relation_origin",
          adapter.annotate_corridor.__globals__.get("relation_origin") is relation_origin)
    adapter_now = _defs((ROOT / ADAPTER).read_text(encoding="utf-8"))
    check("adapter contains no duplicate definitions", not (set(MOVED) & set(adapter_now)))
    check("own_support_labels and component_lineage are untouched",
          bool(old) and all(old.get(n, ("",))[0] == adapter_now.get(n, (None,))[0] for n in ADAPTER_UNTOUCHED))

    # ---- C. _region_code
    g = _graph({"r_int": 7, "r_str": "12", "r_float": 3.9, "r_np": np.int64(5), "r_none": None})
    rcs = [_outcome(_region_code, g, r) for r in ("r_int", "r_str", "r_float", "r_np")]
    check("region code: int, str, float and numpy values go through int()",
          rcs == [("ok", 7), ("ok", 12), ("ok", 3), ("ok", 5)] and type(rcs[3][1]) is int)
    check("region code: missing attribute and missing rid raise KeyError",
          _outcome(_region_code, g, "r_none") == ("KeyError", "'state_region_code'")
          and _outcome(_region_code, g, "nope") == ("KeyError", "'nope'"))

    # ---- D. _own_labels
    diag = _own_labels(np.array([[1, 0], [0, 1]], bool))
    check("own labels: 8-connectivity joins diagonal neighbours",
          diag.tolist() == [[1, 0], [0, 1]])
    multi = _own_labels(np.array([[1, 1, 0, 0, 1],
                                  [0, 0, 0, 0, 1],
                                  [1, 0, 0, 0, 0]], np.int64))
    check("own labels: background 0, three components in raster order, exact shape and int32",
          multi.dtype == np.int32 and multi.shape == (3, 5)
          and multi.tolist() == [[1, 1, 0, 0, 2], [0, 0, 0, 0, 2], [3, 0, 0, 0, 0]])
    check("own labels: input goes through np.uint8 (0.6 truncates to background)",
          _own_labels(np.array([[0.6, 2.0, 0.0]])).tolist() == [[0, 1, 0]])

    # ---- E. _joint_region_own_component
    rc = np.array([[1, 1, 5, 5, 2, 2],
                   [3, 3, 5, 5, 2, 0],
                   [1, 3, 3, 4, 4, 4]], np.int64)
    own = np.array([[1, 1, 1, 2, 0, 3],
                    [0, 0, 1, 2, 3, 3],
                    [1, 0, 0, 0, 0, 0]], np.int32)
    gj = _graph({"A": 1, "B": 2, "C": 3, "D": 5})
    state = {"region_code": rc, "owner_instance": np.full(rc.shape, 9, np.int32)}  # decoy key
    a_val = _outcome(_joint_region_own_component, gj, state, "A", own)
    check("joint region: exactly one positive component gives a Python int",
          a_val == ("ok", 1) and type(a_val[1]) is int)
    check("joint region: background label 0 is ignored",
          _outcome(_joint_region_own_component, gj, state, "B", own) == ("ok", 3))
    msg = "joint region {} does not map to exactly one own-support component: {}"
    check("joint region: no positive label raises the exact RuntimeError",
          _outcome(_joint_region_own_component, gj, state, "C", own) == ("RuntimeError", msg.format("C", [])))
    check("joint region: two positive labels raise the exact RuntimeError",
          _outcome(_joint_region_own_component, gj, state, "D", own) == ("RuntimeError", msg.format("D", [1, 2])))
    float_state = {"region_code": np.array([[1.0, 1.7]])}
    check("joint region: state region_code is cast to int32 (1.7 -> 1 joins the region)",
          _outcome(_joint_region_own_component, _graph({"A": 1}), float_state, "A", np.array([[1, 2]], np.int32))
          == ("RuntimeError", msg.format("A", [1, 2])))

    # ---- F. relation_origin
    support = np.array([[1, 0, 0, 0, 0, 1],
                        [0, 1, 0, 0, 0, 1],
                        [0, 0, 0, 1, 0, 0]], bool)          # 8-connected labels: 1, 2, 3
    rc_o = np.array([[1, 9, 9, 9, 9, 4],
                     [9, 2, 9, 9, 9, 4],
                     [9, 9, 9, 3, 9, 9]], np.int32)
    go = _graph({"P": 1, "Q": 2, "R": 3, "S": 4, "Z": 9})
    so = {"region_code": rc_o}

    def ro(a: str, b: str):
        return relation_origin(go, so, {"region_a": a, "region_b": b}, support)

    cut = _outcome(ro, "P", "Q")
    check("same own-support component (diagonal, 8-connected) -> ownership_cut",
          cut == ("ok", ("ownership_cut", 1, 1)) and type(cut[1]) is tuple)
    check("different components -> own_support_gap with region_a/region_b order kept",
          _outcome(ro, "P", "S") == ("ok", ("own_support_gap", 1, 2))
          and _outcome(ro, "S", "R") == ("ok", ("own_support_gap", 2, 3))
          and _outcome(ro, "R", "P") == ("ok", ("own_support_gap", 3, 1)))
    gap = _outcome(ro, "S", "R")
    check("component ids are Python ints",
          gap[0] == "ok" and type(gap[1][1]) is int and type(gap[1][2]) is int)
    check("errors propagate from relation_origin",
          _outcome(ro, "Z", "P")[0] == "RuntimeError" and _outcome(ro, "P", "missing")[0] == "KeyError")

    # ---- G. dependencies and footprints
    corr_imports = set()
    for node in ast.walk(ast.parse((ROOT / CORRIDORS).read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            corr_imports.add(("." * node.level) + (node.module or ""))
        elif isinstance(node, ast.Import):
            corr_imports.update(a.name for a in node.names)
    forbidden = ("fov3d.experiments", "fov3d.stereo", "fov3d.reconstruction", "fov3d.benchmark", "bpy")
    check("scene.corridors has no experiment/stereo/reconstruction/benchmark/renderer import",
          not any(m.startswith(forbidden) for m in corr_imports))
    init_now = (ROOT / "fov3d" / "scene" / "__init__.py").read_text(encoding="utf-8")
    check("fov3d/scene/__init__.py is unchanged from accepted Core 9",
          bool(core9_corridors) and init_now == _git_show("fov3d/scene/__init__.py"))
    via_adapter = []
    for path in sorted((ROOT / "fov3d").rglob("*.py")):
        if path.as_posix().endswith(ADAPTER):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.ImportFrom) and (node.module or "").endswith("classroom_partition.relations")
                    and set(MOVED) & {a.name for a in node.names}):
                via_adapter.append(path.name)
    check("no production module takes the primitive from the experiment adapter", not via_adapter)
    names = ["cv2", "fov3d.scene.partition", "fov3d.scene.boundaries", "fov3d.scene.corridors",
             "fov3d.scene.lineage", "fov3d.scene.state_validation", "fov3d.scene.relations"]
    bare = _fresh(f"import fov3d.scene\nprint(json.dumps({{k: k in sys.modules for k in {names!r}}}))\n")
    check("fresh bare import fov3d.scene stays lightweight and OpenCV-free",
          len(bare) == len(names) and not any(bare.values()))
    direct = _fresh(
        "import fov3d.scene.corridors\n"
        "mods = sorted(sys.modules)\n"
        "print(json.dumps({'cv2': 'cv2' in sys.modules,\n"
        "  'experiments': any(m.startswith('fov3d.experiments') for m in mods),\n"
        "  'stereo': any(m.startswith('fov3d.stereo') for m in mods),\n"
        "  'fov3d': [m for m in mods if m.startswith('fov3d')]}))\n"
    )
    check("fresh import fov3d.scene.corridors keeps its Core-6 footprint",
          direct == {"cv2": True, "experiments": False, "stereo": False,
                     "fov3d": ["fov3d", "fov3d.geometry", "fov3d.geometry.head_chart", "fov3d.scene",
                               "fov3d.scene.corridors", "fov3d.scene.model", "fov3d.scene.sphere"]})

    print(f"[conceptual-core10-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
