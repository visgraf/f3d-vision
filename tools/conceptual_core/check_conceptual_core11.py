#!/usr/bin/env python3
"""Fail-capable checks for Conceptual Core 11 epistemic-partition extraction."""
from __future__ import annotations

import ast
import builtins
import dis
import importlib
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
    CANDIDATE_KINDS,
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

CONSTANTS = ("REGION_KIND", "REGION_KIND_BY_CODE", "CANDIDATE_KINDS")
FUNCTIONS = ("_component_labels", "_distance_to_target", "_touches_edge", "_centroid_angles",
             "_angular_distance_deg", "_region_interfaces", "build_epistemic_partition")
MOVED = CONSTANTS + FUNCTIONS
ACCEPTED_CORE10 = "85c09381584e30c3643bd55be23183f1cdbd2af7"
BENCHMARK = "fov3d/experiments/classroom_partition/benchmark.py"
PARTITION = "fov3d/epistemic/partition.py"
CONSUMERS = {
    "prefix_benchmark": {"CANDIDATE_KINDS", "REGION_KIND", "REGION_KIND_BY_CODE", "build_epistemic_partition"},
    "integration": {"build_epistemic_partition"},
    "challenge_suite": {"REGION_KIND", "_region_interfaces", "build_epistemic_partition"},
}
# OpenCV DIST_L2 / 5x5 chamfer steps in cells: orthogonal 1, diagonal 1.4, knight 2.1969.
DIAG, KNIGHT = 1.4, 2.1969


def _git_show(path: str) -> str:
    proc = subprocess.run(["git", "show", f"{ACCEPTED_CORE10}:{path}"], cwd=ROOT, capture_output=True, text=True)
    return proc.stdout if proc.returncode == 0 else ""


def _top(src: str) -> dict[str, ast.stmt]:
    out: dict[str, ast.stmt] = {}
    for n in ast.parse(src).body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            out[n.name] = n
        elif isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            out[n.targets[0].id] = n
    return out


def _rest(src: str) -> list[str]:
    """Source of every top-level non-import statement that does not define a moved name."""
    out = []
    for n in ast.parse(src).body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(n, ast.FunctionDef) and n.name in MOVED:
            continue
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in MOVED for t in n.targets):
            continue
        out.append(ast.get_source_segment(src, n))
    return out


def _import_bindings(src: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for n in ast.parse(src).body:
        if isinstance(n, ast.ImportFrom):
            out.update({a.asname or a.name: f"{n.module}.{a.name}" for a in n.names})
        elif isinstance(n, ast.Import):
            out.update({a.asname or a.name: a.name for a in n.names})
    return out


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


def _fresh(body: str) -> dict:
    code = f"import json, sys\nsys.path.insert(0, {str(ROOT)!r})\n{body}"
    proc = subprocess.run([sys.executable, "-I", "-c", code], cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        return {}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {}


def _same(actual, expected, tol: float = 1e-9) -> bool:
    """Strict structural equality: exact types, dict key order, floats within tol."""
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
            and value.shape == np.asarray(expected).shape and np.array_equal(value, np.asarray(expected)))


def _great_circle(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Closed-form angle between two (yaw, pitch) chart directions, in degrees."""
    ya, pa, yb, pb = map(math.radians, (*a, *b))
    c = math.cos(pa) * math.cos(pb) * math.cos(ya - yb) + math.sin(pa) * math.sin(pb)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def main() -> int:
    checked = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal checked, failed
        checked += 1
        if condition:
            print(f"[conceptual-core11-check] PASS {name}")
        else:
            failed += 1
            print(f"[conceptual-core11-check] FAIL {name}")

    # ---- A. literal structural identity against accepted Core 10 (read from Git)
    core10 = _git_show(BENCHMARK)
    old = _top(core10) if core10 else {}
    part_src = (ROOT / PARTITION).read_text(encoding="utf-8")
    new = _top(part_src)
    check("A: source text of the moved functions and constant assignments is identical to accepted Core 10",
          bool(old) and all(n in old and n in new
                            and ast.get_source_segment(core10, old[n]) == ast.get_source_segment(part_src, new[n])
                            for n in MOVED))
    check("A: AST of the moved functions and constant assignments is identical to accepted Core 10",
          bool(old) and all(n in old and n in new and ast.dump(old[n]) == ast.dump(new[n]) for n in MOVED))
    check("A: fov3d.epistemic.partition defines exactly the moved cluster, in accepted order",
          list(new) == list(MOVED))
    check("A: vocabulary codes, their order and the inverse map are the accepted ones",
          _same(REGION_KIND, {"TARGET_SUPPORT": 1, "OTHER_SURFACE": 2, "UNKNOWN": 3,
                              "AMBIGUOUS_BOUNDARY": 4, "TARGET_EVIDENCE_UNMAPPED": 5})
          and _same(REGION_KIND_BY_CODE, {1: "TARGET_SUPPORT", 2: "OTHER_SURFACE", 3: "UNKNOWN",
                                          4: "AMBIGUOUS_BOUNDARY", 5: "TARGET_EVIDENCE_UNMAPPED"}))
    check("A: CANDIDATE_KINDS is exactly {OTHER_SURFACE, UNKNOWN}",
          type(CANDIDATE_KINDS) is set and CANDIDATE_KINDS == {"OTHER_SURFACE", "UNKNOWN"})
    bindings_ok = bool(core10)
    if core10:
        ref = types.ModuleType("_core10_benchmark_reference")
        sys.modules[ref.__name__] = ref
        exec(compile(core10, "core10_benchmark.py", "exec"), ref.__dict__)
        for name in FUNCTIONS:
            fn = getattr(epistemic_partition, name)
            globals_now = _global_names(fn)
            bindings_ok &= globals_now == _global_names(getattr(ref, name))
            bindings_ok &= fn.__globals__ is vars(epistemic_partition)
            for g in globals_now:
                if g in MOVED:
                    bindings_ok &= g in vars(epistemic_partition)
                    continue
                a = vars(epistemic_partition).get(g, getattr(builtins, g, None))
                b = ref.__dict__.get(g, getattr(builtins, g, None))
                bindings_ok &= a is not None and a is b
    check("A: global bindings are equivalent to accepted Core 10; cluster names resolve inside epistemic.partition",
          bindings_ok)

    from fov3d.experiments.classroom_partition import benchmark
    check("A: benchmark re-exports the ten identical objects",
          all(getattr(benchmark, n, None) is getattr(epistemic_partition, n) for n in MOVED))
    bench_src = (ROOT / BENCHMARK).read_text(encoding="utf-8")
    check("A: benchmark contains no duplicate definition of a moved name", not (set(MOVED) & set(_top(bench_src))))
    check("A: benchmark's remaining definitions and module statements are source-identical to accepted Core 10",
          bool(core10) and _rest(core10) == _rest(bench_src))
    old_imp, new_imp = (_import_bindings(core10) if core10 else {}), _import_bindings(bench_src)
    check("A: benchmark imports are Core 10's minus the measured orphans (cv2, math, defaultdict) plus the compat import",
          bool(old_imp) and set(old_imp) - set(new_imp) == {"cv2", "math", "defaultdict"}
          and {k: v for k, v in new_imp.items() if k not in MOVED} == {k: v for k, v in old_imp.items()
                                                                      if k not in ("cv2", "math", "defaultdict")}
          and all(new_imp.get(n) == f"fov3d.epistemic.partition.{n}" for n in MOVED))
    check("A: propose_phase6 resolves the conceptual build_epistemic_partition",
          benchmark.propose_phase6.__globals__.get("build_epistemic_partition") is build_epistemic_partition)
    consumers_ok = True
    for mod, names in CONSUMERS.items():
        m = importlib.import_module(f"fov3d.experiments.classroom_partition.{mod}")
        consumers_ok &= all(getattr(m, n, None) is getattr(epistemic_partition, n) for n in names)
        consumers_ok &= getattr(m, "_covered", None) is benchmark._covered
    check("A: direct consumers resolve the conceptual objects and keep benchmark._covered", consumers_ok)
    only_imports = bool(core10)
    for mod in CONSUMERS:
        rel = f"fov3d/experiments/classroom_partition/{mod}.py"
        old_c, new_c = _git_show(rel), (ROOT / rel).read_text(encoding="utf-8")
        only_imports &= bool(old_c) and _rest(old_c) == _rest(new_c) and _import_bindings(old_c).keys() == _import_bindings(new_c).keys()
    check("A: direct consumers differ from accepted Core 10 only in the source of their imports", only_imports)

    # ---- B. _component_labels
    blobs = np.array([[1, 0, 0, 1],
                      [0, 1, 0, 1],
                      [0, 0, 0, 0],
                      [1, 1, 0, 1]], bool)
    c4 = _outcome(_component_labels, blobs, 4)
    c8 = _outcome(_component_labels, blobs, 8)
    check("B: 4-connectivity keeps the diagonal pair apart: count 6 (with background), raster-order labels",
          c4[0] == "ok" and type(c4[1][0]) is int and c4[1][0] == 6
          and _raster(c4[1][1], [[1, 0, 0, 2], [0, 3, 0, 2], [0, 0, 0, 0], [4, 4, 0, 5]], np.int32))
    check("B: 8-connectivity joins the diagonal pair: count 5, raster-order labels",
          c8[0] == "ok" and type(c8[1][0]) is int and c8[1][0] == 5
          and _raster(c8[1][1], [[1, 0, 0, 2], [0, 1, 0, 2], [0, 0, 0, 0], [3, 3, 0, 4]], np.int32))
    empty = _outcome(_component_labels, np.zeros((2, 3), bool), 8)
    check("B: empty mask gives count 1 (background only) and an all-zero int32 raster",
          empty[0] == "ok" and empty[1][0] == 1 and _raster(empty[1][1], np.zeros((2, 3)), np.int32))

    # ---- C. _distance_to_target
    none = _outcome(_distance_to_target, np.zeros((2, 3), bool), 0.5)
    check("C: no target gives a float32 +inf raster of the chart shape",
          none[0] == "ok" and isinstance(none[1], np.ndarray) and none[1].dtype == np.float32
          and none[1].shape == (2, 3) and bool(np.isposinf(none[1]).all()))
    corner = np.zeros((3, 4), np.int64)
    corner[0, 0] = 1
    dt = _outcome(_distance_to_target, corner, 0.5)
    expected_cells = np.array([[0.0, 1.0, 2.0, 3.0],
                               [1.0, DIAG, KNIGHT, KNIGHT + 1.0],
                               [2.0, KNIGHT, 2 * DIAG, KNIGHT + DIAG]])
    check("C: OpenCV L2/5x5 chamfer values (0, 1, 1.4, 2, 2.1969, 2.8, ...) scaled by grid_deg, float32",
          dt[0] == "ok" and isinstance(dt[1], np.ndarray) and dt[1].dtype == np.float32 and dt[1].shape == (3, 4)
          and bool(np.allclose(dt[1], expected_cells * 0.5, rtol=0.0, atol=1e-4)))
    check("C: target cells are 0 and distance increases away from the target",
          dt[0] == "ok" and float(dt[1][0, 0]) == 0.0
          and bool(np.all(np.diff(dt[1][0]) > 0)) and bool(np.all(np.diff(dt[1][:, 0]) > 0)))

    # ---- D. _touches_edge
    grid = np.zeros((5, 5), bool)

    def edge(*cells) -> tuple:
        m = grid.copy()
        for c in cells:
            m[c] = True
        return _outcome(_touches_edge, m)

    check("D: empty, interior and next-to-border masks do not touch the edge (Python bool)",
          edge() == ("ok", False) and edge((2, 2)) == ("ok", False)
          and edge((1, 1), (1, 3), (3, 1), (3, 3)) == ("ok", False) and type(edge((2, 2))[1]) is bool)
    check("D: each chart border alone touches the edge",
          edge((0, 2)) == ("ok", True) and edge((4, 2)) == ("ok", True)
          and edge((2, 0)) == ("ok", True) and edge((2, 4)) == ("ok", True)
          and type(edge((0, 2))[1]) is bool)

    # ---- E. _centroid_angles  (yaw = y0 + mean(col) * g, pitch = p0 + mean(row) * g)
    cdom = {"yaw": [-10.0, 10.0], "pitch": [-4.0, 4.0]}          # g=2 -> h=5, w=11
    cm = np.zeros((5, 11), bool)
    cm[0, 1] = cm[0, 4] = cm[2, 4] = True                          # mean col 3, mean row 2/3
    cen = _outcome(_centroid_angles, cm, cdom, 2.0)
    check("E: asymmetric mask maps columns to yaw and rows to pitch in chart degrees",
          cen[0] == "ok" and _same(cen[1], (-4.0, -4.0 + 4.0 / 3.0), 1e-12))
    check("E: empty mask gives (nan, nan) Python floats",
          _same(_outcome(_centroid_angles, np.zeros((5, 11), bool), cdom, 2.0), ("ok", (math.nan, math.nan))))

    # ---- F. _angular_distance_deg
    def ang(a, b):
        return _outcome(_angular_distance_deg, a, b)

    check("F: identical directions give 0 degrees", _same(ang((12.0, -7.0), (12.0, -7.0)), ("ok", 0.0), 1e-6))
    u = np.array([math.sin(math.radians(-60.0)) * math.cos(math.radians(-28.0)), math.sin(math.radians(-28.0)),
                  -math.cos(math.radians(-60.0)) * math.cos(math.radians(-28.0))])
    check("F: rounding above 1 is clipped (live witness: dot=1+eps at (-60, -28))",
          float(np.dot(u, u)) > 1.0 and _same(ang((-60.0, -28.0), (-60.0, -28.0)), ("ok", 0.0)))
    check("F: pure yaw and pure pitch displacements are returned in degrees",
          _same(ang((0.0, 0.0), (30.0, 0.0)), ("ok", 30.0), 1e-9)
          and _same(ang((-20.0, 0.0), (30.0, 0.0)), ("ok", 50.0), 1e-9)
          and _same(ang((0.0, 0.0), (0.0, 25.0)), ("ok", 25.0), 1e-9))
    check("F: pitch sign and argument order are respected",
          _same(ang((0.0, 10.0), (0.0, 30.0)), ("ok", 20.0), 1e-9)
          and _same(ang((0.0, -10.0), (0.0, 30.0)), ("ok", 40.0), 1e-9)
          and _same(ang((0.0, 30.0), (0.0, -10.0)), ("ok", 40.0), 1e-9))
    check("F: non-planar displacement follows the great circle, not the chart",
          _same(ang((0.0, 60.0), (30.0, 60.0)), ("ok", _great_circle((0.0, 60.0), (30.0, 60.0))), 1e-9)
          and abs(_great_circle((0.0, 60.0), (30.0, 60.0)) - 30.0) > 10.0
          and _same(ang((90.0, 0.0), (0.0, 45.0)), ("ok", 90.0), 1e-9)
          and _same(ang((35.0, -20.0), (-50.0, 40.0)),
                    ("ok", _great_circle((35.0, -20.0), (-50.0, 40.0))), 1e-9))

    # ---- G. _region_interfaces
    rc = np.array([[9, 9, 10, 0],
                   [2, 2, 10, 10],
                   [2, 12, 12, 10]], np.int64)
    ifc = _outcome(_region_interfaces, rc)
    edges_ok = ifc[0] == "ok" and _same(ifc[1][0], [
        {"region_code_a": 2, "region_code_b": 9, "interface_edge_count": 2},
        {"region_code_a": 2, "region_code_b": 10, "interface_edge_count": 1},
        {"region_code_a": 2, "region_code_b": 12, "interface_edge_count": 2},
        {"region_code_a": 9, "region_code_b": 10, "interface_edge_count": 1},
        {"region_code_a": 10, "region_code_b": 12, "interface_edge_count": 2},
    ])
    check("G: horizontal+vertical interfaces accumulate; background ignored; numeric pair order; exact keys",
          edges_ok)
    adj = ifc[1][1] if ifc[0] == "ok" else {}
    check("G: adjacency is symmetric with the same counts and no background entry",
          isinstance(adj, dict) and {k: dict(v) for k, v in adj.items()} == {
              9: {10: 1, 2: 2}, 2: {10: 1, 12: 2, 9: 2}, 10: {9: 1, 2: 1, 12: 2}, 12: {2: 2, 10: 2}}
          and all(type(k) is int and all(type(j) is int and type(c) is int for j, c in v.items())
                  for k, v in adj.items()))
    wide = _outcome(_region_interfaces, np.array([[300, 44], [300, 44]]))
    check("G: region codes are kept beyond 8 bits (300 and 44 stay distinct)",
          wide[0] == "ok" and _same(wide[1][0], [{"region_code_a": 44, "region_code_b": 300, "interface_edge_count": 2}]))
    flat = _outcome(_region_interfaces, np.full((2, 2), 3))
    check("G: a single-region raster has no interfaces",
          flat[0] == "ok" and flat[1][0] == [] and dict(flat[1][1]) == {})

    # ---- H. build_epistemic_partition on hand-derived fixtures
    # H1 (4x6, target 7). Classes:   T T A A B U / T X A B B U / E X U C D U / E U U C D U
    # T target support, X ambiguous boundary, E target evidence unmapped, U unknown,
    # A/B/C/D other surfaces 3/12/25/40 (3 mapped+incidental, 12 mapped, 25 targeted later, 40 never).
    h1 = {
        "target_support": np.array([[1, 1, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0],
                                    [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]]),
        "owner_instance": np.array([[7, 12, 3, 0, 12, 0], [7, 60, 3, 12, 12, 0],
                                    [0, 0, 7, 7, 0, 0], [0, 0, 0, 0, 0, 0]]),
        "nearest_instance": np.array([[7, 12, 7, 3, 12, 0], [7, 3, 12, 3, 0, 0],
                                      [7, 7, 0, 25, 40, 0], [7, 0, 0, 25, 40, 0]]),
        "ambiguous_instance": np.array([[0, 1, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0],
                                        [0, 1, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]]),
        "depth_seen": np.array([[1, 1, 1, 0, 1, 0], [1, 1, 1, 1, 1, 0],
                                [0, 1, 1, 1, 0, 0], [1, 1, 0, 0, 0, 0]]),
        "seen_any": np.array([[1, 1, 1, 0, 1, 1], [0, 1, 0, 1, 1, 0],
                              [0, 0, 1, 0, 1, 0], [1, 0, 0, 0, 1, 0]]),
    }
    dom1 = {"yaw": [-10.0, 10.0], "pitch": [-6.0, 6.0]}          # g=4 -> h=4, w=6
    gazes = [(-8.0, -4.0), (6.0, 4.0)]
    r1 = _outcome(build_epistemic_partition, h1, target_id=7, target_name="fixture-target",
                  all_target_ids={7, 25, 90}, domain=dom1, grid_deg=4.0, gazes_deg=gazes)
    ok1 = r1[0] == "ok" and isinstance(r1[1], tuple) and len(r1[1]) == 4
    arrays, rows, edge_rows, diag = r1[1] if ok1 else ({}, [], [], {})
    check("H: builds and returns (arrays, region_rows, edge_rows, diag)", ok1)
    check("H: precedence target > ambiguous > other surface > target-unmapped > unknown (class_code, uint8)",
          _raster(arrays.get("class_code"), [[1, 1, 2, 2, 2, 3], [1, 4, 2, 2, 2, 3],
                                             [5, 4, 3, 2, 2, 3], [5, 3, 3, 2, 2, 3]], np.uint8))
    check("H: surface identity: mapped owner first, incidental nearest, target id never other (int32)",
          _raster(arrays.get("surface_instance"), [[0, 0, 3, 3, 12, 0], [0, 60, 3, 12, 12, 0],
                                                   [0, 0, 0, 25, 40, 0], [0, 0, 0, 25, 40, 0]], np.int32))
    check("H: mapped/incidental/ambiguous masks (ambiguous cells stay mapped; target owner is not other)",
          _raster(arrays.get("mapped_other"), [[0, 0, 1, 0, 1, 0], [0, 1, 1, 1, 1, 0],
                                               [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]], np.bool_)
          and _raster(arrays.get("incidental_other"), [[0, 0, 0, 1, 0, 0], [0, 0, 0, 0, 0, 0],
                                                       [0, 0, 0, 1, 1, 0], [0, 0, 0, 1, 1, 0]], np.bool_)
          and _raster(arrays.get("ambiguous_boundary"), [[0, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0],
                                                         [0, 1, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]], np.bool_))
    check("H: region codes: target, other surfaces by numeric id, unknown, ambiguous, target-unmapped (int32)",
          _raster(arrays.get("region_code"), [[1, 1, 2, 2, 3, 6], [1, 8, 2, 3, 3, 6],
                                              [9, 8, 7, 4, 5, 6], [9, 7, 7, 4, 5, 6]], np.int32))
    check("H: arrays keys/order and bool pass-through of target_support, depth_seen, seen_any",
          list(arrays) == ["class_code", "region_code", "surface_instance", "target_support", "depth_seen",
                           "seen_any", "mapped_other", "incidental_other", "ambiguous_boundary"]
          and all(_raster(arrays[k], np.asarray(h1[k], bool), np.bool_)
                  for k in ("target_support", "depth_seen", "seen_any")))

    ids = {1: "target_support:0001", 2: "other_surface:0002", 3: "other_surface:0003", 4: "other_surface:0004",
           5: "other_surface:0005", 6: "unknown:0006", 7: "unknown:0007", 8: "ambiguous_boundary:0008",
           9: "target_evidence_unmapped:0009"}
    adjacency = {1: {2: 1, 8: 2, 9: 1}, 2: {1: 1, 3: 3, 7: 1, 8: 1}, 3: {2: 3, 4: 1, 5: 1, 6: 2},
                 4: {3: 1, 5: 2, 7: 2}, 5: {3: 1, 4: 2, 6: 2}, 6: {3: 2, 5: 2},
                 7: {2: 1, 4: 2, 8: 2, 9: 1}, 8: {1: 2, 2: 1, 7: 2, 9: 1}, 9: {1: 1, 7: 1, 8: 1}}
    # code, kind, candidate, instance, cells, edge, centroid, min/median target distance (cells),
    # seen_any fraction, head depth fraction, mapped, incidental, (surface_source, reconstruction_status)
    spec = [
        (1, "TARGET_SUPPORT", False, 7, 3, True, (-26 / 3, -14 / 3), 0.0, 0.0, 2 / 3, 1.0, 0, 0, None),
        (2, "OTHER_SURFACE", True, 3, 3, True, (-2 / 3, -14 / 3), 1.0, DIAG, 1 / 3, 2 / 3, 2, 1,
         ("mapped_and_incidental", "mapped_now")),
        (3, "OTHER_SURFACE", True, 12, 3, True, (14 / 3, -10 / 3), KNIGHT, 3.0, 1.0, 1.0, 3, 0,
         ("mapped", "mapped_now")),
        (4, "OTHER_SURFACE", True, 25, 2, True, (2.0, 4.0), 2 * DIAG, (2 * DIAG + KNIGHT + DIAG) / 2, 0.0, 0.5,
         0, 2, ("incidental", "targeted_later")),
        (5, "OTHER_SURFACE", True, 40, 2, True, (6.0, 4.0), KNIGHT + DIAG, (KNIGHT + DIAG + 3 * DIAG) / 2, 1.0,
         0.0, 0, 2, ("incidental", "never_targeted")),
        (6, "UNKNOWN", True, None, 4, True, (10.0, 0.0), 4.0, (KNIGHT + 2.0 + 2 * KNIGHT) / 2, 0.25, 0.0, 0, 0,
         None),
        (7, "UNKNOWN", True, None, 3, True, (-10 / 3, 14 / 3), KNIGHT, KNIGHT, 1 / 3, 2 / 3, 0, 0, None),
        (8, "AMBIGUOUS_BOUNDARY", False, None, 2, False, (-6.0, 0.0), 1.0, (1.0 + DIAG) / 2, 0.5, 1.0, 1, 0,
         None),
        (9, "TARGET_EVIDENCE_UNMAPPED", False, 7, 2, True, (-10.0, 4.0), 1.0, 1.5, 0.5, 0.5, 0, 0, None),
    ]
    expected_rows = []
    for code, kind, cand, iid, cells, touches, cen, dmin, dmed, seen, depth, mapped, inc, surface in spec:
        row = {"region_code": code, "region_id": ids[code], "kind": kind, "candidate": cand, "instance_id": iid,
               "cell_count": cells, "touches_domain_edge": touches,
               "centroid_yaw_deg": cen[0], "centroid_pitch_deg": cen[1],
               "min_distance_to_target_deg": dmin * 4.0, "median_distance_to_target_deg": dmed * 4.0,
               "min_distance_to_historical_gaze_deg": min(_great_circle(cen, g) for g in gazes),
               "seen_any_fraction": seen, "head_depth_fraction": depth,
               "mapped_cells": mapped, "incidental_cells": inc}
        if surface:
            row["surface_source"], row["reconstruction_status"] = surface
        row["adjacent_regions"] = [{"region_code": n, "region_id": ids[n], "interface_edge_count": c}
                                   for n, c in sorted(adjacency[code].items())]
        row["adjacent_to_target_support"] = 1 in adjacency[code]
        expected_rows.append(row)

    def fields(rs, keys):
        return [{k: r.get(k, "<missing>") for k in keys} for r in rs]

    check("H: region kinds, codes, ids, instance ids and candidate = kind in CANDIDATE_KINDS",
          _same(fields(rows, ("region_code", "region_id", "kind", "candidate", "instance_id")),
                fields(expected_rows, ("region_code", "region_id", "kind", "candidate", "instance_id"))))
    check("H: cell counts, domain-edge flags and centroids",
          _same(fields(rows, ("cell_count", "touches_domain_edge", "centroid_yaw_deg", "centroid_pitch_deg")),
                fields(expected_rows, ("cell_count", "touches_domain_edge", "centroid_yaw_deg",
                                       "centroid_pitch_deg")), 1e-9))
    check("H: min/median distance to target support (chamfer degrees)",
          _same(fields(rows, ("min_distance_to_target_deg", "median_distance_to_target_deg")),
                fields(expected_rows, ("min_distance_to_target_deg", "median_distance_to_target_deg")), 1e-3))
    check("H: min great-circle distance to the historical gazes",
          _same(fields(rows, ("min_distance_to_historical_gaze_deg",)),
                fields(expected_rows, ("min_distance_to_historical_gaze_deg",)), 1e-5))
    check("H: seen_any and head-depth fractions; mapped and incidental cell counts",
          _same(fields(rows, ("seen_any_fraction", "head_depth_fraction", "mapped_cells", "incidental_cells")),
                fields(expected_rows, ("seen_any_fraction", "head_depth_fraction", "mapped_cells",
                                       "incidental_cells")), 1e-12))
    check("H: surface_source and reconstruction_status (mapped_now / targeted_later / never_targeted)",
          _same(fields(rows[1:5], ("surface_source", "reconstruction_status")),
                fields(expected_rows[1:5], ("surface_source", "reconstruction_status")))
          and all("surface_source" not in r and "reconstruction_status" not in r for r in rows[:1] + rows[5:]))
    check("H: adjacent regions and adjacent_to_target_support",
          _same(fields(rows, ("adjacent_regions", "adjacent_to_target_support")),
                fields(expected_rows, ("adjacent_regions", "adjacent_to_target_support"))))
    check("H: complete region rows: exact fields, key order and types", _same(rows, expected_rows, 1e-3))
    expected_edges = [{"region_code_a": a, "region_code_b": b, "interface_edge_count": c}
                      for a in sorted(adjacency) for b, c in sorted(adjacency[a].items()) if a < b]
    check("H: edge rows", _same(edge_rows, expected_edges) and len(expected_edges) == 15)
    check("H: diag keys, values and truth_used = False", _same(diag, {
        "target_id": 7, "target_name": "fixture-target", "chart_shape_hw": [4, 6], "region_count": 9,
        "candidate_region_count": 6,
        "kind_region_counts": {"AMBIGUOUS_BOUNDARY": 1, "OTHER_SURFACE": 4, "TARGET_EVIDENCE_UNMAPPED": 1,
                               "TARGET_SUPPORT": 1, "UNKNOWN": 2},
        "kind_cell_counts": {"TARGET_SUPPORT": 3, "OTHER_SURFACE": 10, "UNKNOWN": 7,
                             "AMBIGUOUS_BOUNDARY": 2, "TARGET_EVIDENCE_UNMAPPED": 2},
        "target_evidence_unmapped_cells": 2, "ambiguous_boundary_cells": 2, "head_depth_cells": 14,
        "eye_ray_seen_cells": 12, "truth_used": False}))

    # H2 (2x6): every 2x2 block is a diagonal checkerboard of two kinds.
    #   T U O X E U / U T X O U E   (O = other surface 5)
    h2 = {
        "target_support": np.array([[1, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0]], bool),
        "owner_instance": np.array([[7, 0, 5, 0, 0, 0], [0, 7, 0, 5, 0, 0]]),
        "nearest_instance": np.array([[7, 0, 5, 0, 7, 0], [0, 7, 0, 5, 0, 7]]),
        "ambiguous_instance": np.array([[0, 0, 0, 1, 0, 0], [0, 0, 1, 0, 0, 0]], bool),
        "depth_seen": np.ones((2, 6), bool),
        "seen_any": np.ones((2, 6), bool),
    }
    r2 = _outcome(build_epistemic_partition, h2, target_id=7, target_name="t", all_target_ids={7},
                  domain={"yaw": [-10.0, 10.0], "pitch": [-2.0, 2.0]}, grid_deg=4.0, gazes_deg=[])
    rc2 = r2[1][0].get("region_code") if r2[0] == "ok" else None
    check("H: connectivity: target/other/target-unmapped 8-connected; unknown/ambiguous 4-connected",
          _raster(rc2, [[1, 3, 2, 7, 9, 4], [5, 1, 8, 2, 6, 9]], np.int32)
          and r2[1][3]["kind_region_counts"] == {"AMBIGUOUS_BOUNDARY": 2, "OTHER_SURFACE": 1,
                                                 "TARGET_EVIDENCE_UNMAPPED": 1, "TARGET_SUPPORT": 1,
                                                 "UNKNOWN": 4})

    # H3 (2x3): no target support and no gazes.   U O U / E U U   (O = incidental 9)
    h3 = {
        "target_support": np.zeros((2, 3), bool),
        "owner_instance": np.zeros((2, 3), np.int32),
        "nearest_instance": np.array([[0, 9, 0], [7, 0, 0]]),
        "ambiguous_instance": np.zeros((2, 3), bool),
        "depth_seen": np.array([[0, 1, 0], [1, 0, 0]], bool),
        "seen_any": np.array([[1, 1, 1], [0, 0, 0]], bool),
    }
    r3 = _outcome(build_epistemic_partition, h3, target_id=7, target_name="t", all_target_ids={7},
                  domain={"yaw": [-4.0, 4.0], "pitch": [-2.0, 2.0]}, grid_deg=4.0, gazes_deg=[])
    rows3 = r3[1][1] if r3[0] == "ok" else []
    check("H: without target support or gazes the distance descriptors are None",
          len(rows3) == 4 and all(r["min_distance_to_target_deg"] is None and r["median_distance_to_target_deg"] is None
                                  and r["min_distance_to_historical_gaze_deg"] is None
                                  and r["adjacent_to_target_support"] is False for r in rows3))
    check("H: target-free partition: codes, kinds and never_targeted incidental surface",
          r3[0] == "ok" and _raster(r3[1][0]["region_code"], [[2, 1, 3], [4, 3, 3]], np.int32)
          and [(r["kind"], r["instance_id"]) for r in rows3] == [
              ("OTHER_SURFACE", 9), ("UNKNOWN", None), ("UNKNOWN", None), ("TARGET_EVIDENCE_UNMAPPED", 7)]
          and (rows3[0].get("surface_source"), rows3[0].get("reconstruction_status")) == ("incidental", "never_targeted")
          and _same(r3[1][3], {
              "target_id": 7, "target_name": "t", "chart_shape_hw": [2, 3], "region_count": 4,
              "candidate_region_count": 3,
              "kind_region_counts": {"OTHER_SURFACE": 1, "TARGET_EVIDENCE_UNMAPPED": 1, "UNKNOWN": 2},
              "kind_cell_counts": {"TARGET_SUPPORT": 0, "OTHER_SURFACE": 1, "UNKNOWN": 4,
                                   "AMBIGUOUS_BOUNDARY": 0, "TARGET_EVIDENCE_UNMAPPED": 1},
              "target_evidence_unmapped_cells": 1, "ambiguous_boundary_cells": 0, "head_depth_cells": 2,
              "eye_ray_seen_cells": 3, "truth_used": False}))
    bad = dict(h3, seen_any=np.zeros((3, 2), bool))
    check("H: mismatched raster shapes raise the accepted ValueError",
          _outcome(build_epistemic_partition, bad, target_id=7, target_name="t", all_target_ids=set(),
                   domain={"yaw": [-4.0, 4.0], "pitch": [-2.0, 2.0]}, grid_deg=4.0, gazes_deg=[])
          == ("ValueError", "Phase-5 state rasters do not share one chart shape"))

    # ---- I. package and import footprint
    check("I: fov3d/epistemic/__init__.py is unchanged from accepted Core 10",
          bool(core10) and (ROOT / "fov3d" / "epistemic" / "__init__.py").read_text(encoding="utf-8")
          == _git_show("fov3d/epistemic/__init__.py"))
    part_imports = set()
    for node in ast.walk(ast.parse(part_src)):
        if isinstance(node, ast.ImportFrom):
            part_imports.add(("." * node.level) + (node.module or ""))
        elif isinstance(node, ast.Import):
            part_imports.update(a.name for a in node.names)
    check("I: epistemic.partition imports only collections, typing, math, cv2, numpy and geometry.head_chart",
          part_imports == {"__future__", "collections", "typing", "math", "cv2", "numpy", "fov3d.geometry.head_chart"})
    direct_ok = True
    via_benchmark = []
    for path in sorted((ROOT / "fov3d").rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if rel == BENCHMARK:
            continue
        from_part: set[str] = set()
        from_bench: set[str] = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module == "fov3d.epistemic.partition":
                from_part.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and (node.module or "").endswith("classroom_partition.benchmark"):
                from_bench.update(a.name for a in node.names)
        if from_bench & set(MOVED):
            via_benchmark.append(rel)
        if path.stem in CONSUMERS and path.parent.name == "classroom_partition":
            direct_ok &= from_part == CONSUMERS[path.stem] and from_bench == {"_covered"}
    check("I: direct consumers import the moved names from epistemic.partition and only _covered from benchmark",
          direct_ok)
    check("I: no production module takes a moved name through benchmark", not via_benchmark)
    names = ["cv2", "fov3d.epistemic.partition"]
    bare = _fresh(f"import fov3d.epistemic\nprint(json.dumps({{'loaded': {{k: k in sys.modules for k in {names!r}}},"
                  " 'fov3d': sorted(m for m in sys.modules if m.startswith('fov3d'))}))\n")
    check("I: fresh bare import fov3d.epistemic stays lightweight (no cv2, no partition)",
          bare == {"loaded": {"cv2": False, "fov3d.epistemic.partition": False}, "fov3d": ["fov3d", "fov3d.epistemic"]})
    direct = _fresh(
        "import fov3d.epistemic.partition\n"
        "mods = sorted(sys.modules)\n"
        "print(json.dumps({'cv2': 'cv2' in sys.modules,\n"
        "  'fov3d': [m for m in mods if m.startswith('fov3d')]}))\n"
    )
    check("I: fresh import fov3d.epistemic.partition loads cv2 and only fov3d.geometry.head_chart",
          direct == {"cv2": True, "fov3d": ["fov3d", "fov3d.epistemic", "fov3d.epistemic.partition",
                                            "fov3d.geometry", "fov3d.geometry.head_chart"]})
    orders = [
        _fresh("import fov3d.epistemic.partition as p\n"
               "import fov3d.experiments.classroom_partition.benchmark as b\n"
               "print(json.dumps(b.build_epistemic_partition is p.build_epistemic_partition))\n"),
        _fresh("import fov3d.experiments.classroom_partition.benchmark as b\n"
               "import fov3d.epistemic.partition as p\n"
               "print(json.dumps(b.REGION_KIND is p.REGION_KIND))\n"),
    ]
    check("I: no import cycle: either import order gives the shared identities", orders == [True, True])

    print(f"[conceptual-core11-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
