#!/usr/bin/env python3
"""Fail-capable checks for Conceptual Core 9 boundary depth-order relation primitive."""
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

import fov3d.scene.relations as scene_relations
from fov3d.scene.model import BoundaryChain, BoundaryKind, PartitionRegion, RegionKind, ScenePartitionGraph
from fov3d.scene.relations import _region_object, _weighted_quantile, boundary_depth_order

MOVED = ("_region_object", "_weighted_quantile", "boundary_depth_order")
ACCEPTED_CORE8 = "3877857c3a355851413cdfaa55c5dd05ad8bdab4"
ADAPTER = "fov3d/experiments/classroom_partition/relations.py"
KEYS = [
    "boundary_chain_count", "interface_edge_count", "target_nearer_votes", "intervener_nearer_votes",
    "intervener_nearer_vote_fraction", "depth_order_confidence_abs_vote_balance",
    "depth_jump_interface_weighted_median_m", "depth_jump_interface_weighted_p90_m",
]


def _segments(src: str) -> dict[str, tuple[str, str]]:
    tree = ast.parse(src)
    return {n.name: (ast.get_source_segment(src, n), ast.dump(n)) for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name in MOVED}


def _global_names(fn) -> set[str]:
    """Names the function (and its nested comprehensions) load as globals or builtins."""
    names: set[str] = set()
    stack = [fn.__code__]
    while stack:
        code = stack.pop()
        names.update(i.argval for i in dis.get_instructions(code) if i.opname in ("LOAD_GLOBAL", "LOAD_NAME"))
        stack.extend(c for c in code.co_consts if isinstance(c, types.CodeType))
    return names


def _fresh(body: str) -> dict:
    code = f"import json, sys\nsys.path.insert(0, {str(ROOT)!r})\n{body}"
    proc = subprocess.run([sys.executable, "-I", "-c", code], cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        return {}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {}


def _chain(bid: str, a: str, b: str, kind: BoundaryKind = BoundaryKind.OBJECT_OBJECT, **attrs) -> BoundaryChain:
    return BoundaryChain(bid, a, b, np.zeros((2, 3)), kind=kind, attributes=attrs)


def main() -> int:
    checked = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal checked, failed
        checked += 1
        if condition:
            print(f"[conceptual-core9-check] PASS {name}")
        else:
            failed += 1
            print(f"[conceptual-core9-check] FAIL {name}")

    # ---- 1-2 literal identity against accepted Core 8, and equivalent global bindings
    proc = subprocess.run(["git", "show", f"{ACCEPTED_CORE8}:{ADAPTER}"], cwd=ROOT, capture_output=True, text=True)
    core8_src = proc.stdout if proc.returncode == 0 else ""
    old = _segments(core8_src) if core8_src else {}
    new = _segments((ROOT / "fov3d" / "scene" / "relations.py").read_text(encoding="utf-8"))
    check("source text of the three definitions is identical to accepted Core 8",
          bool(old) and all(old.get(n, ("", ""))[0] == new.get(n, (None, None))[0] for n in MOVED))
    check("AST of the three definitions is identical to accepted Core 8",
          bool(old) and all(old.get(n, ("", ""))[1] == new.get(n, (None, None))[1] for n in MOVED))

    bindings_ok = bool(core8_src)
    if core8_src:
        ref = types.ModuleType("_core8_relations_reference")
        sys.modules[ref.__name__] = ref
        exec(compile(core8_src, "core8_relations.py", "exec"), ref.__dict__)
        for name in MOVED:
            for g in _global_names(getattr(scene_relations, name)):
                if g in MOVED:
                    continue  # the moved helpers themselves: identity covered by source/AST above
                a = scene_relations.__dict__.get(g, getattr(builtins, g, None))
                b = ref.__dict__.get(g, getattr(builtins, g, None))
                bindings_ok &= a is not None and a is b
        bindings_ok &= all(scene_relations.boundary_depth_order.__globals__[h] is getattr(scene_relations, h)
                           for h in ("_region_object", "_weighted_quantile"))
    check("global bindings are equivalent to accepted Core 8", bindings_ok)

    # ---- 3 experiment-side identities, no duplicates
    from fov3d.experiments.classroom_partition import relations as adapter
    check("experiment adapter re-exports the identical objects",
          all(getattr(adapter, n) is getattr(scene_relations, n) for n in MOVED)
          and adapter.annotate_corridor.__globals__["boundary_depth_order"] is boundary_depth_order)
    adapter_defs = {n.name for n in ast.parse((ROOT / ADAPTER).read_text(encoding="utf-8")).body
                    if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    check("experiment adapter contains no duplicate definitions", not (set(MOVED) & adapter_defs))

    # ---- 4 direct behavior: _weighted_quantile
    wq = _weighted_quantile
    check("weighted quantile: empty values and non-positive total give None",
          wq([], [], 0.5) is None and wq([1.0], [0], 0.5) is None and wq([1.0, 2.0], [1, -1], 0.9) is None)
    # Sorted: v [0.1, 0.3, 0.9], w [1, 4, 5], c [1, 5, 10]; q=0.5 -> 5 -> index 1 -> 0.3
    # (the unsorted order would give c [5, 6, 10] -> 0.9).
    check("weighted quantile: sorts values with their weights",
          wq([0.3, 0.1, 0.9], [1, 6, 3], 0.5) == 0.1 and wq([0.3, 0.1, 0.9], [1, 6, 3], 0.9) == 0.9
          and wq([0.9, 0.1, 0.3], [5, 1, 4], 0.5) == 0.3)
    r = wq([0.1, 0.3, 0.9], [1, 4, 5], 0.5)
    check("weighted quantile: searchsorted side='left' on an exact cumulative boundary",
          r == 0.3 and type(r) is float and wq([0.1, 0.3, 0.9], [1, 4, 5], 0.0) == 0.1)

    # ---- 4 direct behavior: _region_object
    regions = {
        "t1": PartitionRegion("t1", RegionKind.OBJECT_COMPONENT, object_id="7"),
        "t2": PartitionRegion("t2", RegionKind.OBJECT_COMPONENT, object_id="7"),
        "o1": PartitionRegion("o1", RegionKind.OBJECT_COMPONENT, object_id="9"),
        "o2": PartitionRegion("o2", RegionKind.OBJECT_COMPONENT, object_id="12"),
        "o3": PartitionRegion("o3", RegionKind.OBJECT_COMPONENT, object_id="40"),
        "b": PartitionRegion("b", RegionKind.BASE),
        "bx": PartitionRegion("bx", RegionKind.BASE, object_id="9"),         # BASE carrying an id
        "n": PartitionRegion("n", RegionKind.OBJECT_COMPONENT, object_id=None),  # object-less component
    }
    g0 = ScenePartitionGraph(regions=regions)
    check("region object: int id for object components; None for BASE (even with an id) and for no id",
          _region_object(g0, "o2") == 12 and type(_region_object(g0, "o2")) is int
          and _region_object(g0, "b") is None and _region_object(g0, "bx") is None
          and _region_object(g0, "n") is None)

    # ---- 4 direct behavior: boundary_depth_order
    big = dict(nearer_region_a_votes=100, nearer_region_b_votes=100, interface_edge_count=100, depth_jump_median_m=9.0)
    chains = [
        _chain("B1", "t1", "o1", nearer_region_a_votes=3, nearer_region_b_votes=1, interface_edge_count=6, depth_jump_median_m=0.1),
        _chain("B2", "o1", "t2", nearer_region_a_votes=2, nearer_region_b_votes=5, interface_edge_count=1, depth_jump_median_m=0.3),
        _chain("B3", "t1", "o1", nearer_region_a_votes=1, nearer_region_b_votes=0, interface_edge_count=3),
        _chain("B4", "t2", "o1", nearer_region_a_votes=0, nearer_region_b_votes=0, interface_edge_count=0, depth_jump_median_m=0.5),
        _chain("B5", "t1", "o1", BoundaryKind.OBJECT_BASE, **big),      # wrong kind: ignored
        _chain("B6", "t1", "b", **big),                                  # BASE region: ignored
        _chain("B7", "t1", "n", **big),                                  # object-less component: ignored
        _chain("B8", "t1", "o2", interface_edge_count=2, depth_jump_median_m=0.2),   # other 12: no votes
        _chain("B9", "o1", "o2", **big),                                 # other-other: ignored
        _chain("B10", "t1", "t2", **big),                                # target-target: ignored
        _chain("B11", "t1", "bx", **big),                                # BASE with id: ignored
        _chain("B12", "o1", "t1", interface_edge_count=3, depth_jump_median_m=0.9),  # no vote keys
        # Intervener 40: jumps 0.1/0.2/0.3/0.4 with edge weights 4/2/3/1 (cumsum 4, 6, 9, 10),
        # plus a matched chain without interface_edge_count (edges +0, jump not collected).
        _chain("C1", "t1", "o3", nearer_region_a_votes=1, nearer_region_b_votes=0, interface_edge_count=4, depth_jump_median_m=0.1),
        _chain("C2", "o3", "t2", nearer_region_a_votes=0, nearer_region_b_votes=0, interface_edge_count=2, depth_jump_median_m=0.2),
        _chain("C3", "t2", "o3", interface_edge_count=3, depth_jump_median_m=0.3),
        _chain("C4", "o3", "t1", interface_edge_count=1, depth_jump_median_m=0.4),
        _chain("C5", "t1", "o3", nearer_region_a_votes=2, depth_jump_median_m=0.35),
    ]
    graph = ScenePartitionGraph(regions=regions, boundaries={c.boundary_id: c for c in chains})
    interveners = {np.int64(12), 7, 9, 30.0, 33, 40}  # raw set iteration is not sorted
    out = boundary_depth_order(graph, np.int64(7), interveners)
    check("intervener filtering: target excluded, int() conversion, numeric sort, str keys",
          list(out) == ["9", "12", "30", "33", "40"])
    check("missing edge count, multi-jump edge-weighted median (0.2) and p90 (0.3)",
          out.get("40") == {
              "boundary_chain_count": 5, "interface_edge_count": 10, "target_nearer_votes": 3,
              "intervener_nearer_votes": 0, "intervener_nearer_vote_fraction": 0.0,
              "depth_order_confidence_abs_vote_balance": 1.0,
              "depth_jump_interface_weighted_median_m": 0.2, "depth_jump_interface_weighted_p90_m": 0.3,
          })
    check("return structure: exact per-intervener key order",
          all(list(v) == KEYS for v in out.values()))
    o9 = out.get("9", {})
    check("chain and edge accumulation over matched OBJECT_OBJECT chains only",
          o9.get("boundary_chain_count") == 5 and o9.get("interface_edge_count") == 13)
    check("vote accumulation with target/intervener orientation on both chain sides",
          o9.get("target_nearer_votes") == 9 and o9.get("intervener_nearer_votes") == 3)
    check("vote fraction and absolute balance",
          o9.get("intervener_nearer_vote_fraction") == 0.25
          and o9.get("depth_order_confidence_abs_vote_balance") == 0.5)
    check("depth jumps: collected only when present and nedge > 0; edge-weighted median and p90",
          o9.get("depth_jump_interface_weighted_median_m") == 0.1
          and o9.get("depth_jump_interface_weighted_p90_m") == 0.9)
    check("zero votes give None fractions; single jump quantiles",
          out.get("12") == {
              "boundary_chain_count": 1, "interface_edge_count": 2, "target_nearer_votes": 0,
              "intervener_nearer_votes": 0, "intervener_nearer_vote_fraction": None,
              "depth_order_confidence_abs_vote_balance": None,
              "depth_jump_interface_weighted_median_m": 0.2, "depth_jump_interface_weighted_p90_m": 0.2,
          })
    empty_entry = {k: (0 if i < 4 else None) for i, k in enumerate(KEYS)}
    check("intervener without chains: zero counts and None fields",
          out.get("30") == empty_entry and out.get("33") == empty_entry)
    check("value types: Python int counts and float fractions/quantiles",
          all(type(o9.get(k)) is int for k in KEYS[:4]) and all(type(o9.get(k)) is float for k in KEYS[4:]))
    check("target not among interveners and empty interveners",
          boundary_depth_order(graph, 7, {7}) == {} and boundary_depth_order(graph, 7, set()) == {})

    # ---- 5-6 footprints and dependency direction
    sr_imports = set()
    for node in ast.walk(ast.parse((ROOT / "fov3d" / "scene" / "relations.py").read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            sr_imports.add(("." * node.level) + (node.module or ""))
        elif isinstance(node, ast.Import):
            sr_imports.update(a.name for a in node.names)
    check("scene.relations imports only numpy, typing and scene.model",
          sr_imports <= {"__future__", "typing", "numpy", ".model", "fov3d.scene.model"})
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
    check("fresh bare import fov3d.scene keeps every footprint invariant (no scene.relations)",
          len(bare) == len(names) and not any(bare.values()))
    direct = _fresh(
        "import fov3d.scene.relations\n"
        "mods = sorted(sys.modules)\n"
        "print(json.dumps({'cv2': 'cv2' in sys.modules,\n"
        "  'experiments': any(m.startswith('fov3d.experiments') for m in mods),\n"
        "  'stereo': any(m.startswith('fov3d.stereo') for m in mods),\n"
        "  'other_scene': [m for m in mods if m.startswith('fov3d.scene.') and m not in\n"
        "      ('fov3d.scene.model', 'fov3d.scene.sphere', 'fov3d.scene.relations')]}))\n"
    )
    check("fresh import fov3d.scene.relations pulls no cv2, experiment, stereo or other scene module",
          direct == {"cv2": False, "experiments": False, "stereo": False, "other_scene": []})

    print(f"[conceptual-core9-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
