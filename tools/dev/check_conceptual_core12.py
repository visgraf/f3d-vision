#!/usr/bin/env python3
"""Fail-capable checks for Conceptual Core 12: candidate policy separated from the epistemic partition.

The reference is accepted Conceptual Core 11 (read from Git). Core 12 supersedes the Core-11
structural checker: the intrinsic partition no longer owns candidate semantics, and the
historical candidate view is re-created by the experiment-side candidate policy.
"""
from __future__ import annotations

import ast
import builtins
import copy
import dis
import importlib
import inspect
import json
import math
import subprocess
import sys
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fov3d.epistemic.partition as epistemic_partition
from fov3d.epistemic.partition import (
    REGION_KIND,
    REGION_KIND_BY_CODE,
    _angular_distance_deg,
    _centroid_angles,
    _component_labels,
    _distance_to_target,
    _region_interfaces,
    _touches_edge,
    build_epistemic_partition,
)
from fov3d.experiments.classroom_partition import candidate_policy
from fov3d.experiments.classroom_partition.candidate_policy import (
    CANDIDATE_KINDS,
    annotate_candidate_partition,
    build_candidate_partition,
)

ACCEPTED_CORE11 = "d324e098c859a3b7ea1e91c7526f5cda854bcaf7"
PARTITION = "fov3d/epistemic/partition.py"
POLICY = "fov3d/experiments/classroom_partition/candidate_policy.py"
CP = "fov3d/experiments/classroom_partition/"
HELPERS = ("_component_labels", "_distance_to_target", "_touches_edge", "_centroid_angles",
           "_angular_distance_deg", "_region_interfaces")
PURE_NAMES = ("REGION_KIND", "REGION_KIND_BY_CODE") + HELPERS + ("build_epistemic_partition",)
REMOVED_ROW = '"candidate": bool(kind in CANDIDATE_KINDS),'
REMOVED_DIAG = '"candidate_region_count": sum(bool(r["candidate"]) for r in region_rows),'
BENCHMARK_REPRESENTATION = {"REGION_KIND", "REGION_KIND_BY_CODE", "_angular_distance_deg", "_centroid_angles",
                            "_component_labels", "_distance_to_target", "_region_interfaces", "_touches_edge"}
# module: (names from fov3d.epistemic.partition, names from candidate_policy, build_candidate_partition calls)
CONSUMERS = {
    "benchmark": (BENCHMARK_REPRESENTATION, {"CANDIDATE_KINDS", "build_candidate_partition"}, 1),
    "prefix_benchmark": ({"REGION_KIND", "REGION_KIND_BY_CODE"}, {"build_candidate_partition"}, 1),
    "integration": (set(), {"build_candidate_partition"}, 2),
    "challenge_suite": ({"REGION_KIND", "_region_interfaces"}, {"build_candidate_partition"}, 1),
}
KINDS = ("TARGET_SUPPORT", "OTHER_SURFACE", "UNKNOWN", "AMBIGUOUS_BOUNDARY", "TARGET_EVIDENCE_UNMAPPED")
# OpenCV DIST_L2 / 5x5 chamfer steps in cells: orthogonal 1, diagonal 1.4, knight 2.1969.
DIAG, KNIGHT = 1.4, 2.1969


def _git_show(path: str) -> str:
    proc = subprocess.run(["git", "show", f"{ACCEPTED_CORE11}:{path}"], cwd=ROOT, capture_output=True, text=True)
    return proc.stdout if proc.returncode == 0 else ""


def _top(src: str) -> dict[str, ast.stmt]:
    out: dict[str, ast.stmt] = {}
    for n in ast.parse(src).body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            out[n.name] = n
        elif isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            out[n.targets[0].id] = n
    return out


def _imports(src: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for n in ast.parse(src).body:
        if isinstance(n, ast.ImportFrom):
            out.update({a.asname or a.name: f"{n.module}.{a.name}" for a in n.names})
        elif isinstance(n, ast.Import):
            out.update({a.asname or a.name: a.name for a in n.names})
    return out


def _all_import_modules(src: str) -> set[str]:
    mods: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.ImportFrom):
            mods.add(("." * node.level) + (node.module or ""))
        elif isinstance(node, ast.Import):
            mods.update(a.name for a in node.names)
    return mods


class _Rename(ast.NodeTransformer):
    def visit_Name(self, node: ast.Name) -> ast.Name:
        if node.id == "build_candidate_partition":
            node.id = "build_epistemic_partition"
        return node


def _normalized_rest(src: str, *, drop_alias: bool = False) -> list[str]:
    """AST of every non-import statement with the wrapper call renamed back to its Core-11 name."""
    out = []
    for n in ast.parse(src).body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            continue
        if drop_alias and isinstance(n, ast.Assign) and ast.unparse(n) == "build_epistemic_partition = build_candidate_partition":
            continue
        out.append(ast.dump(_Rename().visit(copy.deepcopy(n))))
    return out


def _normalized_source(src: str, *, drop_alias: bool = False) -> list[str]:
    """Source text of every non-import statement with the wrapper call renamed back to its Core-11 name."""
    out = []
    for n in ast.parse(src).body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            continue
        seg = ast.get_source_segment(src, n)
        if drop_alias and seg == "build_epistemic_partition = build_candidate_partition":
            continue
        out.append(seg.replace("build_candidate_partition", "build_epistemic_partition"))
    return out


class _DropCandidateEntries(ast.NodeTransformer):
    def __init__(self) -> None:
        self.dropped = 0

    def visit_Dict(self, node: ast.Dict) -> ast.Dict:
        self.generic_visit(node)
        keep = [(k, v) for k, v in zip(node.keys, node.values)
                if not (isinstance(k, ast.Constant) and k.value in ("candidate", "candidate_region_count"))]
        self.dropped += len(node.keys) - len(keep)
        node.keys, node.values = [k for k, _ in keep], [v for _, v in keep]
        return node


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                ids.add(id(first.value))
    return ids


def _global_names(fn) -> set[str]:
    names: set[str] = set()
    stack = [fn.__code__]
    while stack:
        code = stack.pop()
        names.update(i.argval for i in dis.get_instructions(code) if i.opname in ("LOAD_GLOBAL", "LOAD_NAME"))
        stack.extend(c for c in code.co_consts if isinstance(c, types.CodeType))
    return names


def _outcome(fn, *args, **kwargs):
    try:
        return ("ok", fn(*args, **kwargs))
    except Exception as exc:  # noqa: BLE001 - the exception is the observation
        return (type(exc).__name__, str(exc))


def _fresh(body: str):
    code = f"import json, sys\nsys.path.insert(0, {str(ROOT)!r})\n{body}"
    proc = subprocess.run([sys.executable, "-I", "-c", code], cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        return {}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {}


def _same(actual, expected, tol: float = 0.0) -> bool:
    """Strict structural equality: exact types, dict key order, arrays by dtype/shape/value."""
    if isinstance(expected, np.ndarray):
        return (isinstance(actual, np.ndarray) and actual.dtype == expected.dtype
                and actual.shape == expected.shape and bool(np.array_equal(actual, expected)))
    if isinstance(expected, float):
        return type(actual) is float and (
            (math.isnan(expected) and math.isnan(actual)) or abs(actual - expected) <= tol)
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return list(actual) == list(expected) and all(_same(actual[k], expected[k], tol) for k in expected)
    if isinstance(expected, (list, tuple)):
        return len(actual) == len(expected) and all(_same(a, e, tol) for a, e in zip(actual, expected))
    return actual == expected


def _raster(value, expected, dtype) -> bool:
    return (isinstance(value, np.ndarray) and value.dtype == dtype
            and value.shape == np.asarray(expected).shape and bool(np.array_equal(value, np.asarray(expected))))


def _great_circle(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Closed-form angle between two (yaw, pitch) chart directions, in degrees."""
    ya, pa, yb, pb = map(math.radians, (*a, *b))
    c = math.cos(pa) * math.cos(pb) * math.cos(ya - yb) + math.sin(pa) * math.sin(pb)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def _project(result):
    """Accepted Core-11 output minus exactly the two candidate fields."""
    arrays, rows, edges, diag = result
    return (arrays, [{k: v for k, v in r.items() if k != "candidate"} for r in rows], edges,
            {k: v for k, v in diag.items() if k != "candidate_region_count"})


def _random_state(rng: np.random.Generator):
    h, w = int(rng.integers(2, 10)), int(rng.integers(2, 12))
    ids = np.array([0, 7, 3, 12, 25, 40, 300])
    ts = rng.random((h, w)) < rng.uniform(0.0, 0.4)
    owner = np.where(rng.random((h, w)) < 0.5, 0, rng.choice(ids, (h, w)))
    owner = np.where(ts & (rng.random((h, w)) < 0.8), 7, owner)
    state = {
        "target_support": ts, "owner_instance": owner,
        "nearest_instance": np.where(rng.random((h, w)) < 0.35, 0, rng.choice(ids, (h, w))),
        "ambiguous_instance": rng.random((h, w)) < rng.uniform(0.0, 0.3),
        "depth_seen": rng.random((h, w)) < 0.6, "seen_any": rng.random((h, w)) < 0.6,
    }
    g = float(rng.choice([0.5, 1.0, 2.0, 4.0]))
    kw = dict(target_id=7, target_name="random",
              all_target_ids={int(x) for x in rng.choice(ids[1:], int(rng.integers(0, 4)), replace=False)},
              domain={"yaw": [-(w - 1) * g / 2, (w - 1) * g / 2], "pitch": [-(h - 1) * g / 2, (h - 1) * g / 2]},
              grid_deg=g,
              gazes_deg=[(float(rng.uniform(-60, 60)), float(rng.uniform(-40, 40)))
                         for _ in range(int(rng.integers(0, 4)))])
    return state, kw


def main() -> int:
    checked = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal checked, failed
        checked += 1
        if condition:
            print(f"[conceptual-core12-check] PASS {name}")
        else:
            failed += 1
            print(f"[conceptual-core12-check] FAIL {name}")

    core11_src = _git_show(PARTITION)
    ref = None
    if core11_src:
        ref = types.ModuleType("_core11_partition_reference")
        sys.modules[ref.__name__] = ref
        try:
            exec(compile(core11_src, "core11_partition.py", "exec"), ref.__dict__)
        except Exception:  # noqa: BLE001
            ref = None
    check("reference: accepted Core-11 partition executes from git show d324e09", ref is not None)
    old_build = ref.build_epistemic_partition if ref is not None else None

    # ---- A. pure-module structure against accepted Core 11
    part_src = (ROOT / PARTITION).read_text(encoding="utf-8")
    old_defs, new_defs = (_top(core11_src) if core11_src else {}), _top(part_src)
    check("A: REGION_KIND and REGION_KIND_BY_CODE assignments and values are identical to Core 11",
          bool(old_defs) and all(n in old_defs and n in new_defs
                                 and ast.get_source_segment(core11_src, old_defs[n]) == ast.get_source_segment(part_src, new_defs[n])
                                 for n in ("REGION_KIND", "REGION_KIND_BY_CODE"))
          and _same(REGION_KIND, {"TARGET_SUPPORT": 1, "OTHER_SURFACE": 2, "UNKNOWN": 3,
                                  "AMBIGUOUS_BOUNDARY": 4, "TARGET_EVIDENCE_UNMAPPED": 5})
          and _same(REGION_KIND_BY_CODE, {1: "TARGET_SUPPORT", 2: "OTHER_SURFACE", 3: "UNKNOWN",
                                          4: "AMBIGUOUS_BOUNDARY", 5: "TARGET_EVIDENCE_UNMAPPED"}))
    part_tree = ast.parse(part_src)
    check("A: CANDIDATE_KINDS is not defined, imported or referenced by epistemic.partition",
          not hasattr(epistemic_partition, "CANDIDATE_KINDS")
          and not any(isinstance(n, ast.Name) and n.id == "CANDIDATE_KINDS" for n in ast.walk(part_tree))
          and "CANDIDATE_KINDS" not in _imports(part_src))
    check("A: the six helpers are source- and AST-identical to Core 11",
          bool(old_defs) and all(n in old_defs and n in new_defs
                                 and ast.get_source_segment(core11_src, old_defs[n]) == ast.get_source_segment(part_src, new_defs[n])
                                 and ast.dump(old_defs[n]) == ast.dump(new_defs[n]) for n in HELPERS))
    check("A: build_epistemic_partition keeps the accepted Core-11 signature",
          old_build is not None and str(inspect.signature(build_epistemic_partition)) == str(inspect.signature(old_build)))
    old_seg = ast.get_source_segment(core11_src, old_defs["build_epistemic_partition"]) if "build_epistemic_partition" in old_defs else ""
    new_seg = ast.get_source_segment(part_src, new_defs["build_epistemic_partition"]) if "build_epistemic_partition" in new_defs else None
    kept = [ln for ln in old_seg.splitlines() if ln.strip() not in (REMOVED_ROW, REMOVED_DIAG)]
    check("A: build_epistemic_partition source is Core 11 minus exactly the two candidate lines",
          bool(old_seg) and len(old_seg.splitlines()) - len(kept) == 2 and "\n".join(kept) == new_seg)
    dropper = _DropCandidateEntries()
    old_ast = dropper.visit(copy.deepcopy(old_defs["build_epistemic_partition"])) if "build_epistemic_partition" in old_defs else None
    check("A: build_epistemic_partition AST is Core 11 minus exactly the two candidate dict entries",
          old_ast is not None and dropper.dropped == 2 and "build_epistemic_partition" in new_defs
          and ast.dump(old_ast) == ast.dump(new_defs["build_epistemic_partition"]))
    docs = _docstring_ids(part_tree)
    operational = [n.value for n in ast.walk(part_tree) if isinstance(n, ast.Constant) and id(n) not in docs
                   and n.value in ("candidate", "candidate_region_count")]
    check("A: no operational 'candidate' or 'candidate_region_count' construction remains (docstrings aside)",
          not operational)
    check("A: epistemic.partition defines exactly the Core-11 names minus CANDIDATE_KINDS, in order",
          list(new_defs) == list(PURE_NAMES))
    check("A: import statements are identical to Core 11; no experiment or candidate_policy import anywhere",
          bool(core11_src)
          and [ast.dump(n) for n in ast.parse(core11_src).body if isinstance(n, (ast.Import, ast.ImportFrom))]
          == [ast.dump(n) for n in part_tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
          and not any(m.startswith(("fov3d.experiments", "fov3d.attention")) or "candidate_policy" in m
                      for m in _all_import_modules(part_src)))
    bindings_ok = ref is not None
    for name in HELPERS + ("build_epistemic_partition",):
        if ref is None:
            break
        fn_new, fn_old = getattr(epistemic_partition, name), getattr(ref, name)
        gn, go = _global_names(fn_new), _global_names(fn_old)
        droppable = {"CANDIDATE_KINDS", "sum", "bool"} if name == "build_epistemic_partition" else set()
        bindings_ok &= gn <= go and (go - gn) <= droppable and "CANDIDATE_KINDS" not in gn
        bindings_ok &= fn_new.__globals__ is vars(epistemic_partition)
        for g in gn:
            if g in PURE_NAMES:
                bindings_ok &= g in vars(epistemic_partition)
                continue
            a = vars(epistemic_partition).get(g, getattr(builtins, g, None))
            b = ref.__dict__.get(g, getattr(builtins, g, None))
            bindings_ok &= a is not None and a is b
    check("A: global bindings of the pure functions are equivalent to Core 11 (candidate names dropped only)",
          bindings_ok)

    # ---- B. pure behavior: Core-11 helper known answers (subsumed), fixtures, projection equivalence
    blobs = np.array([[1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 0, 0], [1, 1, 0, 1]], bool)
    c4, c8 = _outcome(_component_labels, blobs, 4), _outcome(_component_labels, blobs, 8)
    check("B: _component_labels 4-connectivity: count 6, raster-order int32 labels",
          c4[0] == "ok" and type(c4[1][0]) is int and c4[1][0] == 6
          and _raster(c4[1][1], [[1, 0, 0, 2], [0, 3, 0, 2], [0, 0, 0, 0], [4, 4, 0, 5]], np.int32))
    check("B: _component_labels 8-connectivity joins the diagonal pair: count 5",
          c8[0] == "ok" and type(c8[1][0]) is int and c8[1][0] == 5
          and _raster(c8[1][1], [[1, 0, 0, 2], [0, 1, 0, 2], [0, 0, 0, 0], [3, 3, 0, 4]], np.int32))
    none = _outcome(_distance_to_target, np.zeros((2, 3), bool), 0.5)
    corner = np.zeros((3, 4), np.int64)
    corner[0, 0] = 1
    dt = _outcome(_distance_to_target, corner, 0.5)
    expected_cells = np.array([[0.0, 1.0, 2.0, 3.0], [1.0, DIAG, KNIGHT, KNIGHT + 1.0],
                               [2.0, KNIGHT, 2 * DIAG, KNIGHT + DIAG]])
    check("B: _distance_to_target: +inf without target; OpenCV L2/5x5 chamfer x grid_deg, float32",
          none[0] == "ok" and none[1].dtype == np.float32 and none[1].shape == (2, 3) and bool(np.isposinf(none[1]).all())
          and dt[0] == "ok" and dt[1].dtype == np.float32 and dt[1].shape == (3, 4)
          and bool(np.allclose(dt[1], expected_cells * 0.5, rtol=0.0, atol=1e-4)))
    grid = np.zeros((5, 5), bool)

    def edge(*cells):
        m = grid.copy()
        for c in cells:
            m[c] = True
        return _outcome(_touches_edge, m)

    check("B: _touches_edge: empty/interior/next-to-border False; each border True (Python bool)",
          edge() == ("ok", False) and edge((2, 2)) == ("ok", False) and edge((1, 1), (1, 3), (3, 1), (3, 3)) == ("ok", False)
          and edge((0, 2)) == ("ok", True) and edge((4, 2)) == ("ok", True) and edge((2, 0)) == ("ok", True)
          and edge((2, 4)) == ("ok", True) and type(edge((0, 2))[1]) is bool and type(edge((2, 2))[1]) is bool)
    cdom = {"yaw": [-10.0, 10.0], "pitch": [-4.0, 4.0]}
    cm = np.zeros((5, 11), bool)
    cm[0, 1] = cm[0, 4] = cm[2, 4] = True
    check("B: _centroid_angles: columns->yaw, rows->pitch; empty mask gives (nan, nan)",
          _same(_outcome(_centroid_angles, cm, cdom, 2.0), ("ok", (-4.0, -4.0 + 4.0 / 3.0)), 1e-12)
          and _same(_outcome(_centroid_angles, np.zeros((5, 11), bool), cdom, 2.0), ("ok", (math.nan, math.nan))))

    def ang(a, b):
        return _outcome(_angular_distance_deg, a, b)

    u = np.array([math.sin(math.radians(-60.0)) * math.cos(math.radians(-28.0)), math.sin(math.radians(-28.0)),
                  -math.cos(math.radians(-60.0)) * math.cos(math.radians(-28.0))])
    check("B: _angular_distance_deg: zero, live clip witness, degrees, pitch sign/order, great circle",
          _same(ang((12.0, -7.0), (12.0, -7.0)), ("ok", 0.0), 1e-6)
          and float(np.dot(u, u)) > 1.0 and _same(ang((-60.0, -28.0), (-60.0, -28.0)), ("ok", 0.0))
          and _same(ang((0.0, 0.0), (30.0, 0.0)), ("ok", 30.0), 1e-9)
          and _same(ang((-20.0, 0.0), (30.0, 0.0)), ("ok", 50.0), 1e-9)
          and _same(ang((0.0, 0.0), (0.0, 25.0)), ("ok", 25.0), 1e-9)
          and _same(ang((0.0, -10.0), (0.0, 30.0)), ("ok", 40.0), 1e-9)
          and _same(ang((0.0, 30.0), (0.0, -10.0)), ("ok", 40.0), 1e-9)
          and _same(ang((0.0, 60.0), (30.0, 60.0)), ("ok", _great_circle((0.0, 60.0), (30.0, 60.0))), 1e-9)
          and _same(ang((35.0, -20.0), (-50.0, 40.0)), ("ok", _great_circle((35.0, -20.0), (-50.0, 40.0))), 1e-9))
    ifc = _outcome(_region_interfaces, np.array([[9, 9, 10, 0], [2, 2, 10, 10], [2, 12, 12, 10]], np.int64))
    check("B: _region_interfaces: H+V accumulation, background ignored, numeric order, symmetric int adjacency",
          ifc[0] == "ok" and _same(ifc[1][0], [
              {"region_code_a": 2, "region_code_b": 9, "interface_edge_count": 2},
              {"region_code_a": 2, "region_code_b": 10, "interface_edge_count": 1},
              {"region_code_a": 2, "region_code_b": 12, "interface_edge_count": 2},
              {"region_code_a": 9, "region_code_b": 10, "interface_edge_count": 1},
              {"region_code_a": 10, "region_code_b": 12, "interface_edge_count": 2}])
          and {k: dict(v) for k, v in ifc[1][1].items()} == {
              9: {10: 1, 2: 2}, 2: {10: 1, 12: 2, 9: 2}, 10: {9: 1, 2: 1, 12: 2}, 12: {2: 2, 10: 2}}
          and all(type(k) is int and all(type(j) is int and type(c) is int for j, c in v.items())
                  for k, v in ifc[1][1].items()))
    wide = _outcome(_region_interfaces, np.array([[300, 44], [300, 44]]))
    check("B: _region_interfaces keeps codes beyond 8 bits",
          wide[0] == "ok" and _same(wide[1][0], [{"region_code_a": 44, "region_code_b": 300, "interface_edge_count": 2}]))

    # H1 (4x6, target 7):  T T A A B U / T X A B B U / E X U C D U / E U U C D U
    # A/B/C/D other surfaces 3/12/25/40 (3 mapped+incidental, 12 mapped, 25 targeted later, 40 never).
    h1 = {
        "target_support": np.array([[1, 1, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]]),
        "owner_instance": np.array([[7, 12, 3, 0, 12, 0], [7, 60, 3, 12, 12, 0], [0, 0, 7, 7, 0, 0], [0, 0, 0, 0, 0, 0]]),
        "nearest_instance": np.array([[7, 12, 7, 3, 12, 0], [7, 3, 12, 3, 0, 0], [7, 7, 0, 25, 40, 0], [7, 0, 0, 25, 40, 0]]),
        "ambiguous_instance": np.array([[0, 1, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]]),
        "depth_seen": np.array([[1, 1, 1, 0, 1, 0], [1, 1, 1, 1, 1, 0], [0, 1, 1, 1, 0, 0], [1, 1, 0, 0, 0, 0]]),
        "seen_any": np.array([[1, 1, 1, 0, 1, 1], [0, 1, 0, 1, 1, 0], [0, 0, 1, 0, 1, 0], [1, 0, 0, 0, 1, 0]]),
    }
    gazes = [(-8.0, -4.0), (6.0, 4.0)]
    kw1 = dict(target_id=7, target_name="fixture-target", all_target_ids={7, 25, 90},
               domain={"yaw": [-10.0, 10.0], "pitch": [-6.0, 6.0]}, grid_deg=4.0, gazes_deg=gazes)
    # H2 (2x6) diagonal checkerboards:  T U O X E U / U T X O U E   (O = other surface 5)
    h2 = {
        "target_support": np.array([[1, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0]], bool),
        "owner_instance": np.array([[7, 0, 5, 0, 0, 0], [0, 7, 0, 5, 0, 0]]),
        "nearest_instance": np.array([[7, 0, 5, 0, 7, 0], [0, 7, 0, 5, 0, 7]]),
        "ambiguous_instance": np.array([[0, 0, 0, 1, 0, 0], [0, 0, 1, 0, 0, 0]], bool),
        "depth_seen": np.ones((2, 6), bool), "seen_any": np.ones((2, 6), bool),
    }
    kw2 = dict(target_id=7, target_name="t", all_target_ids={7},
               domain={"yaw": [-10.0, 10.0], "pitch": [-2.0, 2.0]}, grid_deg=4.0, gazes_deg=[])
    # H3 (2x3) no target support and no gazes:  U O U / E U U   (O = incidental 9)
    h3 = {
        "target_support": np.zeros((2, 3), bool), "owner_instance": np.zeros((2, 3), np.int32),
        "nearest_instance": np.array([[0, 9, 0], [7, 0, 0]]), "ambiguous_instance": np.zeros((2, 3), bool),
        "depth_seen": np.array([[0, 1, 0], [1, 0, 0]], bool), "seen_any": np.array([[1, 1, 1], [0, 0, 0]], bool),
    }
    kw3 = dict(target_id=7, target_name="t", all_target_ids={7},
               domain={"yaw": [-4.0, 4.0], "pitch": [-2.0, 2.0]}, grid_deg=4.0, gazes_deg=[])
    fixtures = {"H1": (h1, kw1), "H2": (h2, kw2), "H3": (h3, kw3)}
    old = {k: (_outcome(old_build, s, **kw) if old_build else ("no-reference", "")) for k, (s, kw) in fixtures.items()}
    pure = {k: _outcome(build_epistemic_partition, s, **kw) for k, (s, kw) in fixtures.items()}
    wrap = {k: _outcome(build_candidate_partition, s, **kw) for k, (s, kw) in fixtures.items()}
    old_rows = [r for k in fixtures if old[k][0] == "ok" for r in old[k][1][1]]
    check("B: fixtures witness all five kinds, every surface_source/reconstruction_status, edge flags, "
          "4/8 connectivity, target-free and no-gaze cases",
          {r["kind"] for r in old_rows} == set(KINDS)
          and {r.get("surface_source") for r in old_rows} >= {"mapped_and_incidental", "mapped", "incidental"}
          and {r.get("reconstruction_status") for r in old_rows} >= {"mapped_now", "targeted_later", "never_targeted"}
          and {r["touches_domain_edge"] for r in old_rows} == {True, False}
          and old["H2"][0] == "ok" and len(old["H2"][1][1]) == 9
          and old["H3"][0] == "ok" and not any(r["kind"] == "TARGET_SUPPORT" for r in old["H3"][1][1]))
    for k in fixtures:
        o, p = old[k], pure[k]
        both = o[0] == "ok" and p[0] == "ok" and isinstance(p[1], tuple) and len(p[1]) == 4
        proj = _project(o[1]) if both else None
        check(f"B: {k} pure arrays and edges are identical to Core 11 (keys, order, dtype, shape, values)",
              both and _same(p[1][0], proj[0]) and _same(p[1][2], proj[2]))
        check(f"B: {k} pure rows = Core-11 rows minus only 'candidate' (order, keys, values, types)",
              both and all("candidate" in r for r in o[1][1]) and _same(p[1][1], proj[1]))
        check(f"B: {k} pure diag = Core-11 diag minus only 'candidate_region_count'",
              both and "candidate_region_count" in o[1][3] and _same(p[1][3], proj[3]))
    bad = dict(h3, seen_any=np.zeros((3, 2), bool))
    check("B: malformed shapes raise the accepted ValueError in the pure and Core-11 builders",
          _outcome(build_epistemic_partition, bad, **kw3)
          == ("ValueError", "Phase-5 state rasters do not share one chart shape")
          == (_outcome(old_build, bad, **kw3) if old_build else None))

    arrays1, rows1, edges1, diag1 = pure["H1"][1] if pure["H1"][0] == "ok" else ({}, [], [], {})
    check("B: H1 hand-derived class, surface, mask and region rasters",
          _raster(arrays1.get("class_code"), [[1, 1, 2, 2, 2, 3], [1, 4, 2, 2, 2, 3], [5, 4, 3, 2, 2, 3], [5, 3, 3, 2, 2, 3]], np.uint8)
          and _raster(arrays1.get("surface_instance"), [[0, 0, 3, 3, 12, 0], [0, 60, 3, 12, 12, 0], [0, 0, 0, 25, 40, 0], [0, 0, 0, 25, 40, 0]], np.int32)
          and _raster(arrays1.get("mapped_other"), [[0, 0, 1, 0, 1, 0], [0, 1, 1, 1, 1, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]], np.bool_)
          and _raster(arrays1.get("incidental_other"), [[0, 0, 0, 1, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 0], [0, 0, 0, 1, 1, 0]], np.bool_)
          and _raster(arrays1.get("ambiguous_boundary"), [[0, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]], np.bool_)
          and _raster(arrays1.get("region_code"), [[1, 1, 2, 2, 3, 6], [1, 8, 2, 3, 3, 6], [9, 8, 7, 4, 5, 6], [9, 7, 7, 4, 5, 6]], np.int32)
          and list(arrays1) == ["class_code", "region_code", "surface_instance", "target_support", "depth_seen",
                                "seen_any", "mapped_other", "incidental_other", "ambiguous_boundary"])
    ids = {1: "target_support:0001", 2: "other_surface:0002", 3: "other_surface:0003", 4: "other_surface:0004",
           5: "other_surface:0005", 6: "unknown:0006", 7: "unknown:0007", 8: "ambiguous_boundary:0008",
           9: "target_evidence_unmapped:0009"}
    adjacency = {1: {2: 1, 8: 2, 9: 1}, 2: {1: 1, 3: 3, 7: 1, 8: 1}, 3: {2: 3, 4: 1, 5: 1, 6: 2},
                 4: {3: 1, 5: 2, 7: 2}, 5: {3: 1, 4: 2, 6: 2}, 6: {3: 2, 5: 2},
                 7: {2: 1, 4: 2, 8: 2, 9: 1}, 8: {1: 2, 2: 1, 7: 2, 9: 1}, 9: {1: 1, 7: 1, 8: 1}}
    spec = [  # code, kind, candidate, instance, cells, edge, centroid, min/median target distance (cells),
        #       seen_any, head depth, mapped, incidental, (surface_source, reconstruction_status)
        (1, "TARGET_SUPPORT", False, 7, 3, True, (-26 / 3, -14 / 3), 0.0, 0.0, 2 / 3, 1.0, 0, 0, None),
        (2, "OTHER_SURFACE", True, 3, 3, True, (-2 / 3, -14 / 3), 1.0, DIAG, 1 / 3, 2 / 3, 2, 1, ("mapped_and_incidental", "mapped_now")),
        (3, "OTHER_SURFACE", True, 12, 3, True, (14 / 3, -10 / 3), KNIGHT, 3.0, 1.0, 1.0, 3, 0, ("mapped", "mapped_now")),
        (4, "OTHER_SURFACE", True, 25, 2, True, (2.0, 4.0), 2 * DIAG, (2 * DIAG + KNIGHT + DIAG) / 2, 0.0, 0.5, 0, 2, ("incidental", "targeted_later")),
        (5, "OTHER_SURFACE", True, 40, 2, True, (6.0, 4.0), KNIGHT + DIAG, (KNIGHT + DIAG + 3 * DIAG) / 2, 1.0, 0.0, 0, 2, ("incidental", "never_targeted")),
        (6, "UNKNOWN", True, None, 4, True, (10.0, 0.0), 4.0, (KNIGHT + 2.0 + 2 * KNIGHT) / 2, 0.25, 0.0, 0, 0, None),
        (7, "UNKNOWN", True, None, 3, True, (-10 / 3, 14 / 3), KNIGHT, KNIGHT, 1 / 3, 2 / 3, 0, 0, None),
        (8, "AMBIGUOUS_BOUNDARY", False, None, 2, False, (-6.0, 0.0), 1.0, (1.0 + DIAG) / 2, 0.5, 1.0, 1, 0, None),
        (9, "TARGET_EVIDENCE_UNMAPPED", False, 7, 2, True, (-10.0, 4.0), 1.0, 1.5, 0.5, 0.5, 0, 0, None),
    ]
    expected_view = []
    for code, kind, cand, iid, cells, touches, cen, dmin, dmed, seen, depth, mapped, inc, surface in spec:
        row = {"region_code": code, "region_id": ids[code], "kind": kind, "candidate": cand, "instance_id": iid,
               "cell_count": cells, "touches_domain_edge": touches, "centroid_yaw_deg": cen[0], "centroid_pitch_deg": cen[1],
               "min_distance_to_target_deg": dmin * 4.0, "median_distance_to_target_deg": dmed * 4.0,
               "min_distance_to_historical_gaze_deg": min(_great_circle(cen, g) for g in gazes),
               "seen_any_fraction": seen, "head_depth_fraction": depth, "mapped_cells": mapped, "incidental_cells": inc}
        if surface:
            row["surface_source"], row["reconstruction_status"] = surface
        row["adjacent_regions"] = [{"region_code": n, "region_id": ids[n], "interface_edge_count": c}
                                   for n, c in sorted(adjacency[code].items())]
        row["adjacent_to_target_support"] = 1 in adjacency[code]
        expected_view.append(row)
    expected_diag_view = {
        "target_id": 7, "target_name": "fixture-target", "chart_shape_hw": [4, 6], "region_count": 9,
        "candidate_region_count": 6,
        "kind_region_counts": {"AMBIGUOUS_BOUNDARY": 1, "OTHER_SURFACE": 4, "TARGET_EVIDENCE_UNMAPPED": 1,
                               "TARGET_SUPPORT": 1, "UNKNOWN": 2},
        "kind_cell_counts": {"TARGET_SUPPORT": 3, "OTHER_SURFACE": 10, "UNKNOWN": 7,
                             "AMBIGUOUS_BOUNDARY": 2, "TARGET_EVIDENCE_UNMAPPED": 2},
        "target_evidence_unmapped_cells": 2, "ambiguous_boundary_cells": 2, "head_depth_cells": 14,
        "eye_ray_seen_cells": 12, "truth_used": False}
    expected_pure = _project(({}, expected_view, [], expected_diag_view))
    check("B: H1 hand-derived pure rows: every field, key order and type, without 'candidate'",
          _same(rows1, expected_pure[1], 1e-3))
    check("B: H1 hand-derived edge rows",
          _same(edges1, [{"region_code_a": a, "region_code_b": b, "interface_edge_count": c}
                         for a in sorted(adjacency) for b, c in sorted(adjacency[a].items()) if a < b]))
    check("B: H1 hand-derived pure diag without 'candidate_region_count', truth_used = False",
          _same(diag1, expected_pure[3]))
    check("B: H2 hand-derived connectivity: target/other/target-unmapped 8-, unknown/ambiguous 4-connected",
          pure["H2"][0] == "ok" and _raster(pure["H2"][1][0]["region_code"], [[1, 3, 2, 7, 9, 4], [5, 1, 8, 2, 6, 9]], np.int32))
    rows3 = pure["H3"][1][1] if pure["H3"][0] == "ok" else []
    check("B: H3 hand-derived target-free/no-gaze rows and diag",
          len(rows3) == 4 and _raster(pure["H3"][1][0]["region_code"], [[2, 1, 3], [4, 3, 3]], np.int32)
          and all(r["min_distance_to_target_deg"] is None and r["median_distance_to_target_deg"] is None
                  and r["min_distance_to_historical_gaze_deg"] is None and r["adjacent_to_target_support"] is False
                  for r in rows3)
          and [(r["kind"], r["instance_id"]) for r in rows3] == [
              ("OTHER_SURFACE", 9), ("UNKNOWN", None), ("UNKNOWN", None), ("TARGET_EVIDENCE_UNMAPPED", 7)]
          and (rows3[0].get("surface_source"), rows3[0].get("reconstruction_status")) == ("incidental", "never_targeted")
          and _same(pure["H3"][1][3], {
              "target_id": 7, "target_name": "t", "chart_shape_hw": [2, 3], "region_count": 4,
              "kind_region_counts": {"OTHER_SURFACE": 1, "TARGET_EVIDENCE_UNMAPPED": 1, "UNKNOWN": 2},
              "kind_cell_counts": {"TARGET_SUPPORT": 0, "OTHER_SURFACE": 1, "UNKNOWN": 4,
                                   "AMBIGUOUS_BOUNDARY": 0, "TARGET_EVIDENCE_UNMAPPED": 1},
              "target_evidence_unmapped_cells": 1, "ambiguous_boundary_cells": 0, "head_depth_cells": 2,
              "eye_ray_seen_cells": 3, "truth_used": False}))

    # ---- C. historical candidate interpretation
    check("C: CANDIDATE_KINDS is exactly the set {OTHER_SURFACE, UNKNOWN}",
          type(CANDIDATE_KINDS) is set and CANDIDATE_KINDS == {"OTHER_SURFACE", "UNKNOWN"})
    flags = {}
    for kind in KINDS:
        res = _outcome(annotate_candidate_partition, [{"region_code": 1, "kind": kind, "cell_count": 4}],
                       {"target_id": 7, "region_count": 1, "truth_used": False})
        flags[kind] = res
    check("C: per kind: UNKNOWN and OTHER_SURFACE are candidates; TARGET_SUPPORT, AMBIGUOUS_BOUNDARY and "
          "TARGET_EVIDENCE_UNMAPPED are not (Python bool; count 1/0)",
          all(flags[k] == ("ok", ([{"region_code": 1, "kind": k, "candidate": k in ("OTHER_SURFACE", "UNKNOWN"),
                                    "cell_count": 4}],
                                  {"target_id": 7, "region_count": 1,
                                   "candidate_region_count": int(k in ("OTHER_SURFACE", "UNKNOWN")), "truth_used": False}))
              and type(flags[k][1][0][0]["candidate"]) is bool and type(flags[k][1][1]["candidate_region_count"]) is int
              for k in KINDS))
    snap_rows, snap_diag = copy.deepcopy(rows1), copy.deepcopy(diag1)
    ann = _outcome(annotate_candidate_partition, rows1, diag1)
    a_rows, a_diag = ann[1] if ann[0] == "ok" else ([], {})

    def with_after(d, anchor, key, value):
        out = {}
        for k2, v2 in d.items():
            out[k2] = v2
            if k2 == anchor:
                out[key] = value
        return out

    check("C: rows retained in order; 'candidate' inserted immediately after 'kind'; other fields are the pure values",
          len(a_rows) == len(rows1) == 9
          and all(list(a) == list(with_after(p, "kind", "candidate", None)) and all(a[k2] is p[k2] for k2 in p)
                  and type(a["candidate"]) is bool and a["candidate"] == (p["kind"] in ("OTHER_SURFACE", "UNKNOWN"))
                  for a, p in zip(a_rows, rows1)))
    check("C: candidate_region_count (Python int) immediately after region_count; other diag fields untouched",
          bool(a_diag) and list(a_diag) == list(with_after(diag1, "region_count", "candidate_region_count", None))
          and type(a_diag["candidate_region_count"]) is int and a_diag["candidate_region_count"] == 6
          and all(a_diag[k2] is diag1[k2] for k2 in diag1))
    check("C: annotation does not mutate its inputs and returns new dictionaries",
          ann[0] == "ok" and _same(rows1, snap_rows) and _same(diag1, snap_diag)
          and all(a is not p for a, p in zip(a_rows, rows1)) and a_diag is not diag1 and a_rows is not rows1)
    check("C: double annotation and missing anchors fail loudly",
          _outcome(annotate_candidate_partition, a_rows, a_diag)[0] == "ValueError"
          and _outcome(annotate_candidate_partition, [{"region_code": 1}], {"region_count": 1})[0] == "KeyError"
          and _outcome(annotate_candidate_partition, [], {"target_id": 7})[0] == "KeyError")
    check("C: an empty partition annotates to count 0",
          _same(_outcome(annotate_candidate_partition, [], {"region_count": 0, "truth_used": False}),
                ("ok", ([], {"region_count": 0, "candidate_region_count": 0, "truth_used": False}))))

    # ---- D. reconstitution identity against accepted Core 11
    for k in fixtures:
        check(f"D: {k} build_candidate_partition is type/order/value-identical to Core-11 build_epistemic_partition",
              old[k][0] == "ok" and wrap[k][0] == "ok" and _same(wrap[k][1], old[k][1]))
    reann = {}
    for k in fixtures:
        if pure[k][0] == "ok":
            r = _outcome(annotate_candidate_partition, pure[k][1][1], pure[k][1][3])
            reann[k] = (pure[k][1][0], r[1][0], pure[k][1][2], r[1][1]) if r[0] == "ok" else None
    check("D: annotate_candidate_partition(PURE) re-creates Core 11 on every fixture",
          all(old[k][0] == "ok" and reann.get(k) is not None and _same(reann[k], old[k][1]) for k in fixtures))
    spy_calls = []
    real = candidate_policy.build_epistemic_partition

    def spy(*a, **kw):
        out = real(*a, **kw)
        spy_calls.append(out)
        return out

    candidate_policy.build_epistemic_partition = spy
    try:
        w = _outcome(build_candidate_partition, h1, **kw1)
    finally:
        candidate_policy.build_epistemic_partition = real
    check("D: the wrapper calls the pure builder once and passes arrays and edges through as the same objects",
          real is build_epistemic_partition and len(spy_calls) == 1 and w[0] == "ok"
          and w[1][0] is spy_calls[0][0] and w[1][2] is spy_calls[0][2])
    check("D: build_candidate_partition has the accepted Core-11 builder signature",
          old_build is not None and str(inspect.signature(build_candidate_partition)) == str(inspect.signature(old_build)))
    check("D: H1 hand-derived candidate view (flags, candidate_region_count 6); H3 count 3",
          wrap["H1"][0] == "ok" and _same(wrap["H1"][1][1], expected_view, 1e-3)
          and _same(wrap["H1"][1][3], expected_diag_view)
          and wrap["H3"][0] == "ok" and wrap["H3"][1][3].get("candidate_region_count") == 3)

    # ---- E. historical benchmark compatibility
    from fov3d.experiments.classroom_partition import benchmark
    check("E: benchmark.CANDIDATE_KINDS is candidate_policy.CANDIDATE_KINDS",
          getattr(benchmark, "CANDIDATE_KINDS", None) is candidate_policy.CANDIDATE_KINDS)
    via_bench = _outcome(getattr(benchmark, "build_epistemic_partition", lambda *a, **k: None), h1, **kw1)
    check("E: benchmark.build_epistemic_partition is the candidate wrapper and returns the accepted Core-11 view",
          getattr(benchmark, "build_epistemic_partition", None) is build_candidate_partition
          and old["H1"][0] == "ok" and via_bench[0] == "ok" and _same(via_bench[1], old["H1"][1]))
    check("E: benchmark's eight representation names are the epistemic.partition objects",
          all(getattr(benchmark, n, None) is getattr(epistemic_partition, n) for n in BENCHMARK_REPRESENTATION))
    bench_src = (ROOT / CP / "benchmark.py").read_text(encoding="utf-8")
    bench_tree = ast.parse(bench_src)
    bench_fns = {n.name for n in bench_tree.body if isinstance(n, ast.FunctionDef)}
    bench_assigns = [n for n in bench_tree.body if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id in set(PURE_NAMES) | {"CANDIDATE_KINDS", "build_candidate_partition"}
                             for t in n.targets)]
    check("E: benchmark has no duplicate: no partition/candidate definition; build_epistemic_partition only as the alias",
          not (bench_fns & (set(PURE_NAMES) | {"build_candidate_partition", "annotate_candidate_partition", "_insert_after"}))
          and [ast.unparse(n) for n in bench_assigns] == ["build_epistemic_partition = build_candidate_partition"])
    p6 = [n for n in bench_tree.body if isinstance(n, ast.FunctionDef) and n.name == "propose_phase6"]
    p6_calls = [c.func.id for c in ast.walk(p6[0]) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)] if p6 else []
    check("E: propose_phase6 resolves and calls build_candidate_partition, not the pure builder",
          benchmark.propose_phase6.__globals__.get("build_candidate_partition") is build_candidate_partition
          and p6_calls.count("build_candidate_partition") == 1 and "build_epistemic_partition" not in p6_calls)

    # ---- F. direct-consumer wiring and Phase-8b independence
    wiring_ok = True
    norm_ok = bool(core11_src)
    for mod, (from_part, from_pol, n_calls) in CONSUMERS.items():
        src = (ROOT / CP / f"{mod}.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        got_part = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == "fov3d.epistemic.partition" for a in n.names}
        got_pol = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                   and n.module == "fov3d.experiments.classroom_partition.candidate_policy" for a in n.names}
        calls = [c.func.id for c in ast.walk(tree) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)]
        m = importlib.import_module(f"fov3d.experiments.classroom_partition.{mod}")
        wiring_ok &= got_part == from_part and got_pol == from_pol
        wiring_ok &= calls.count("build_candidate_partition") == n_calls and "build_epistemic_partition" not in calls
        wiring_ok &= getattr(m, "build_candidate_partition", None) is build_candidate_partition
        if mod != "benchmark":
            wiring_ok &= not hasattr(m, "build_epistemic_partition")
            wiring_ok &= getattr(m, "_covered", None) is benchmark._covered
        wiring_ok &= all(getattr(m, n, None) is getattr(epistemic_partition, n) for n in from_part)
        old_src = _git_show(f"{CP}{mod}.py")
        old_imp, new_imp = _imports(old_src) if old_src else {}, _imports(src)
        expected_imp = {k: v for k, v in old_imp.items() if k not in ("build_epistemic_partition", "CANDIDATE_KINDS")}
        expected_imp.update({n: f"fov3d.experiments.classroom_partition.candidate_policy.{n}" for n in from_pol})
        norm_ok &= bool(old_src) and new_imp == expected_imp
        norm_ok &= _normalized_rest(old_src) == _normalized_rest(src, drop_alias=(mod == "benchmark"))
        norm_ok &= _normalized_source(old_src) == _normalized_source(src, drop_alias=(mod == "benchmark"))
    check("F: benchmark, prefix_benchmark, integration and challenge_suite import the declared names and call "
          "build_candidate_partition (1/1/2/1 sites), never the pure builder", wiring_ok)
    check("F: the four modules equal Core 11 (source text and AST) apart from the declared import, alias and "
          "call-name changes (prefix_benchmark's orphan CANDIDATE_KINDS removed)", norm_ok)
    pure_importers, policy_importers = set(), set()
    for path in sorted((ROOT / "fov3d").rglob("*.py")):
        for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(n, ast.ImportFrom) and n.module == "fov3d.epistemic.partition" and any(a.name == "build_epistemic_partition" for a in n.names):
                pure_importers.add(path.name)
            if isinstance(n, ast.ImportFrom) and (n.module or "").endswith("candidate_policy"):
                policy_importers.add(path.name)
    check("F: among production modules only candidate_policy imports the pure builder; the four historical modules "
          "import the policy", pure_importers == {"candidate_policy.py"}
          and policy_importers == {"benchmark.py", "prefix_benchmark.py", "integration.py", "challenge_suite.py"})
    cs_src = (ROOT / CP / "challenge_suite.py").read_text(encoding="utf-8")
    cs_tree = ast.parse(cs_src)
    cs_old = _top(_git_show(f"{CP}challenge_suite.py")) if core11_src else {}
    cr_new = [n for n in cs_tree.body if isinstance(n, ast.FunctionDef) and n.name == "_component_rows"]
    literal = [n for n in ast.walk(cr_new[0]) if isinstance(n, ast.Set)
               and {e.value for e in n.elts if isinstance(e, ast.Constant)} == {"UNKNOWN", "OTHER_SURFACE"}] if cr_new else []
    check("F: Phase-8b _component_rows is unchanged from Core 11 and keeps its own literal "
          "{'UNKNOWN', 'OTHER_SURFACE'}; challenge_suite never names CANDIDATE_KINDS or a row 'candidate'",
          "_component_rows" in cs_old and bool(cr_new) and ast.dump(cs_old["_component_rows"]) == ast.dump(cr_new[0])
          and len(literal) == 1
          and not any(isinstance(n, ast.Name) and n.id in ("CANDIDATE_KINDS", "candidate_policy") for n in ast.walk(cs_tree))
          and not any(isinstance(n, ast.Constant) and n.value == "candidate" for n in ast.walk(cs_tree)))
    from fov3d.experiments.classroom_partition import challenge_suite

    def rows8b(kind: str, cells: int):
        mask = np.zeros((6, 6), bool)
        mask.flat[:cells] = True
        res = _outcome(challenge_suite._component_rows, mask, connectivity=4, kind=kind, original_code=None,
                       shell_index=None, next_code=1, refined_code=np.zeros((6, 6), np.int32), original_row=None)
        return [(r["candidate_raw"], r["eligible_candidate"]) for r in res[1][1]] if res[0] == "ok" else res

    cases = [("UNKNOWN", 30), ("UNKNOWN", 3), ("OTHER_SURFACE", 30), ("OTHER_SURFACE", 24),
             ("TARGET_SUPPORT", 30), ("AMBIGUOUS_BOUNDARY", 30), ("TARGET_EVIDENCE_UNMAPPED", 30)]
    before = [rows8b(k, c) for k, c in cases]
    saved = candidate_policy.CANDIDATE_KINDS
    candidate_policy.CANDIDATE_KINDS = set()
    try:
        during = [rows8b(k, c) for k, c in cases]
        control = _outcome(build_candidate_partition, h1, **kw1)
    finally:
        candidate_policy.CANDIDATE_KINDS = saved
    check("F: Phase-8b candidate_raw/eligible_candidate known answers (MIN_ELIGIBLE_CELLS 25)",
          before == [[(True, True)], [(True, False)], [(True, True)], [(True, False)],
                     [(False, False)], [(False, False)], [(False, False)]])
    check("F: Phase-8b interpretation is independent of candidate_policy (live control: the wrapper's flags change)",
          during == before and control[0] == "ok" and not any(r.get("candidate", True) for r in control[1][1])
          and wrap["H1"][0] == "ok" and any(r.get("candidate", False) for r in wrap["H1"][1][1]))

    # ---- G. package footprints (fresh processes) and dependencies
    check("G: fov3d/epistemic/__init__.py is unchanged from accepted Core 11",
          bool(core11_src) and (ROOT / "fov3d" / "epistemic" / "__init__.py").read_text(encoding="utf-8")
          == _git_show("fov3d/epistemic/__init__.py"))
    pol = "fov3d.experiments.classroom_partition.candidate_policy"
    probe = ("mods = sorted(sys.modules)\n"
             "print(json.dumps({'cv2': 'cv2' in sys.modules, 'bpy': 'bpy' in sys.modules,\n"
             f"  'partition': 'fov3d.epistemic.partition' in sys.modules, 'policy': {pol!r} in sys.modules,\n"
             "  'fov3d': [m for m in mods if m.startswith('fov3d')]}))\n")
    check("G: fresh bare import fov3d.epistemic: no cv2, no partition, no candidate policy",
          _fresh("import fov3d.epistemic\n" + probe) == {"cv2": False, "bpy": False, "partition": False, "policy": False,
                                                        "fov3d": ["fov3d", "fov3d.epistemic"]})
    check("G: fresh import fov3d.epistemic.partition: cv2 and only geometry.head_chart; no experiments, no policy",
          _fresh("import fov3d.epistemic.partition\n" + probe) == {
              "cv2": True, "bpy": False, "partition": True, "policy": False,
              "fov3d": ["fov3d", "fov3d.epistemic", "fov3d.epistemic.partition", "fov3d.geometry",
                        "fov3d.geometry.head_chart"]})
    check("G: fresh import candidate_policy: the experiment-package footprint plus epistemic.partition only "
          "(no benchmark/evaluators, dense truth, stereo, renderer or bpy)",
          _fresh(f"import {pol}\n" + probe) == {
              "cv2": True, "bpy": False, "partition": True, "policy": True,
              "fov3d": ["fov3d", "fov3d.epistemic", "fov3d.epistemic.partition", "fov3d.experiments",
                        "fov3d.experiments.classroom_partition", pol,
                        "fov3d.experiments.classroom_partition.lift", "fov3d.geometry", "fov3d.geometry.head_chart",
                        "fov3d.reconstruction", "fov3d.reconstruction.association", "fov3d.scene", "fov3d.scene.model",
                        "fov3d.scene.sphere"]})
    pol_src = (ROOT / POLICY).read_text(encoding="utf-8")
    check("G: candidate_policy imports only typing, numpy and fov3d.epistemic.partition",
          _all_import_modules(pol_src) == {"__future__", "typing", "numpy", "fov3d.epistemic.partition"})
    orders = [
        _fresh(f"import {pol} as c\nimport fov3d.experiments.classroom_partition.benchmark as b\n"
               "print(json.dumps(b.build_epistemic_partition is c.build_candidate_partition))\n"),
        _fresh(f"import fov3d.experiments.classroom_partition.benchmark as b\nimport {pol} as c\n"
               "print(json.dumps(b.CANDIDATE_KINDS is c.CANDIDATE_KINDS))\n"),
    ]
    check("G: no import cycle: either import order gives the shared identities", orders == [True, True])

    # ---- H. seeded random differential against accepted Core 11
    rng = np.random.default_rng(20260927)
    n_states = 300
    agree = 0
    ctl_position = ctl_kinds = ctl_count = 0
    ctl_kinds_expected = 0
    kinds_seen, status_seen = set(), set()
    for _ in range(n_states):
        state, kw = _random_state(rng)
        o = _outcome(old_build, state, **kw) if old_build else ("no-reference", "")
        p = _outcome(build_epistemic_partition, state, **kw)
        w = _outcome(build_candidate_partition, state, **kw)
        if o[0] != "ok" or p[0] != "ok" or w[0] != "ok":
            continue
        r = _outcome(annotate_candidate_partition, p[1][1], p[1][3])
        if r[0] != "ok":
            continue
        agree += (_same(p[1], _project(o[1])) and _same((p[1][0], r[1][0], p[1][2], r[1][1]), o[1])
                  and _same(w[1], o[1]))
        kinds_seen |= {row["kind"] for row in o[1][1]}
        status_seen |= {row.get("reconstruction_status") for row in o[1][1]} - {None}
        # non-equivalent controls must be detected by the same comparator
        moved = [dict(list({k2: v for k2, v in row.items() if k2 != "candidate"}.items()) + [("candidate", row["candidate"])])
                 for row in o[1][1]]
        ctl_position += not _same(moved, o[1][1])
        narrow = [with_after({k2: v for k2, v in row.items() if k2 != "candidate"}, "kind", "candidate", row["kind"] == "UNKNOWN")
                  for row in o[1][1]]
        has_other = any(row["kind"] == "OTHER_SURFACE" for row in o[1][1])
        ctl_kinds_expected += has_other
        ctl_kinds += (not _same(narrow, o[1][1])) and has_other
        bumped = dict(o[1][3], candidate_region_count=o[1][3]["candidate_region_count"] + 1)
        ctl_count += not _same(bumped, o[1][3])
    check(f"H: {n_states} random states: PURE == project(OLD), annotate(PURE) == OLD and wrapper == OLD (type-strict)",
          agree == n_states)
    check("H: random states cover all five kinds and all reconstruction statuses",
          kinds_seen == set(KINDS) and status_seen == {"mapped_now", "targeted_later", "never_targeted"})
    check("H: controls are detected: candidate moved to the end, kind set narrowed to UNKNOWN, count off by one",
          ctl_position == n_states and ctl_count == n_states and ctl_kinds == ctl_kinds_expected > 0)

    print(f"[conceptual-core12-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
