#!/usr/bin/env python3
"""Fail-capable checks for Conceptual Core 13: reconstruction status as historical run context.

The reference is accepted Conceptual Core 12 (read from Git). Core 13 supersedes the Core-12
structural checker: the intrinsic partition no longer takes the experiment's target schedule
(``all_target_ids``) nor emits ``reconstruction_status``; the experiment-side run-context layer
re-creates it, and the candidate policy composes on top of that layer.
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
from fov3d.experiments.classroom_partition import candidate_policy, run_context
from fov3d.experiments.classroom_partition.candidate_policy import CANDIDATE_KINDS, build_candidate_partition
from fov3d.experiments.classroom_partition.run_context import (
    annotate_reconstruction_status,
    build_run_context_partition,
)

ACCEPTED_CORE12 = "872ac45405c796a0e8b0cd4455bd17c12c7542db"
PARTITION = "fov3d/epistemic/partition.py"
CP = "fov3d/experiments/classroom_partition/"
HELPERS = ("_component_labels", "_distance_to_target", "_touches_edge", "_centroid_angles",
           "_angular_distance_deg", "_region_interfaces")
PURE_NAMES = ("REGION_KIND", "REGION_KIND_BY_CODE") + HELPERS + ("build_epistemic_partition",)
REMOVED_PARAM = "all_target_ids: set[int],"
REMOVED_STATUS = ('row["reconstruction_status"] = (', '"mapped_now" if mapped_n',
                  'else "targeted_later" if int(instance_id) in all_target_ids', 'else "never_targeted"', ")")
STATUS_WORDS = ("reconstruction_status", "mapped_now", "targeted_later", "never_targeted")
PRODUCERS = {"benchmark": 1, "prefix_benchmark": 1, "integration": 2, "challenge_suite": 1}
KINDS = ("TARGET_SUPPORT", "OTHER_SURFACE", "UNKNOWN", "AMBIGUOUS_BOUNDARY", "TARGET_EVIDENCE_UNMAPPED")
SOURCE_IF = "kind == 'OTHER_SURFACE' and instance_id is not None"
# OpenCV DIST_L2 / 5x5 chamfer steps in cells: orthogonal 1, diagonal 1.4, knight 2.1969.
DIAG, KNIGHT = 1.4, 2.1969


def _git_show(path: str) -> str:
    proc = subprocess.run(["git", "show", f"{ACCEPTED_CORE12}:{path}"], cwd=ROOT, capture_output=True, text=True)
    return proc.stdout if proc.returncode == 0 else ""


def _top(src: str) -> dict[str, ast.stmt]:
    out: dict[str, ast.stmt] = {}
    for n in ast.parse(src).body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            out[n.name] = n
        elif isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            out[n.targets[0].id] = n
    return out


def _text(src: str, node: ast.AST) -> str:
    """Whole source lines of a node (unlike get_source_segment, this keeps trailing comments)."""
    return "\n".join(src.splitlines()[node.lineno - 1:node.end_lineno])


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


class _DropRunContext(ast.NodeTransformer):
    """Core-12 builder AST minus the all_target_ids parameter and the reconstruction_status assignment."""

    def __init__(self) -> None:
        self.args = 0
        self.assigns = 0

    def visit_arguments(self, node: ast.arguments) -> ast.arguments:
        keep = [(a, d) for a, d in zip(node.kwonlyargs, node.kw_defaults) if a.arg != "all_target_ids"]
        self.args += len(node.kwonlyargs) - len(keep)
        node.kwonlyargs, node.kw_defaults = [a for a, _ in keep], [d for _, d in keep]
        return node

    def visit_Assign(self, node: ast.Assign):
        t = node.targets[0] if len(node.targets) == 1 else None
        if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) and t.slice.value == "reconstruction_status":
            self.assigns += 1
            return None
        return self.generic_visit(node)


def _strip_docstrings(node: ast.AST) -> ast.AST:
    node = copy.deepcopy(node)
    for n in ast.walk(node):
        if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.Module)) and n.body and isinstance(n.body[0], ast.Expr) \
                and isinstance(n.body[0].value, ast.Constant) and isinstance(n.body[0].value.value, str):
            n.body = n.body[1:] or [ast.Pass()]
    return node


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                ids.add(id(first.value))
    return ids


def _source_if(tree: ast.AST):
    found = [n for n in ast.walk(tree) if isinstance(n, ast.If) and ast.unparse(n.test) == SOURCE_IF]
    return found[0] if len(found) == 1 else None


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


def _drop(rows, *keys):
    return [{k: v for k, v in r.items() if k not in keys} for r in rows]


def _with_after(d, anchor, key, value):
    out = {}
    for k, v in d.items():
        out[k] = v
        if k == anchor:
            out[key] = value
    return out


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
              domain={"yaw": [-(w - 1) * g / 2, (w - 1) * g / 2], "pitch": [-(h - 1) * g / 2, (h - 1) * g / 2]},
              grid_deg=g,
              gazes_deg=[(float(rng.uniform(-60, 60)), float(rng.uniform(-40, 40)))
                         for _ in range(int(rng.integers(0, 4)))])
    targets = {int(x) for x in rng.choice(ids[1:], int(rng.integers(0, 5)), replace=False)}
    return state, kw, targets


def main() -> int:
    checked = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal checked, failed
        checked += 1
        if condition:
            print(f"[conceptual-core13-check] PASS {name}")
        else:
            failed += 1
            print(f"[conceptual-core13-check] FAIL {name}")

    # ---- reference: accepted Core-12 partition and candidate policy, bound together
    core12_part = _git_show(PARTITION)
    core12_pol = _git_show(f"{CP}candidate_policy.py")
    ref_p = ref_c = None
    pure_import = "from fov3d.epistemic.partition import build_epistemic_partition\n"
    if core12_part and core12_pol.count(pure_import) == 1:
        try:
            ref_p = types.ModuleType("_core12_partition_reference")
            sys.modules[ref_p.__name__] = ref_p
            exec(compile(core12_part, "core12_partition.py", "exec"), ref_p.__dict__)
            ref_c = types.ModuleType("_core12_candidate_policy_reference")
            ref_c.__dict__["build_epistemic_partition"] = ref_p.build_epistemic_partition
            sys.modules[ref_c.__name__] = ref_c
            exec(compile(core12_pol.replace(pure_import, ""), "core12_candidate_policy.py", "exec"), ref_c.__dict__)
        except Exception:  # noqa: BLE001
            ref_p = ref_c = None
    check("reference: accepted Core-12 partition and candidate policy execute from git show 872ac45",
          ref_p is not None and ref_c is not None)
    old_intr = ref_p.build_epistemic_partition if ref_p is not None else None
    old_hist = ref_c.build_candidate_partition if ref_c is not None else None

    # ---- A. intrinsic-module structure against accepted Core 12
    part_src = (ROOT / PARTITION).read_text(encoding="utf-8")
    part_tree = ast.parse(part_src)
    old_defs, new_defs = (_top(core12_part) if core12_part else {}), _top(part_src)
    check("A: REGION_KIND and REGION_KIND_BY_CODE assignments and values are identical to Core 12",
          bool(old_defs) and all(n in old_defs and n in new_defs
                                 and _text(core12_part, old_defs[n]) == _text(part_src, new_defs[n])
                                 for n in ("REGION_KIND", "REGION_KIND_BY_CODE"))
          and _same(REGION_KIND, {"TARGET_SUPPORT": 1, "OTHER_SURFACE": 2, "UNKNOWN": 3,
                                  "AMBIGUOUS_BOUNDARY": 4, "TARGET_EVIDENCE_UNMAPPED": 5})
          and _same(REGION_KIND_BY_CODE, {1: "TARGET_SUPPORT", 2: "OTHER_SURFACE", 3: "UNKNOWN",
                                          4: "AMBIGUOUS_BOUNDARY", 5: "TARGET_EVIDENCE_UNMAPPED"}))
    check("A: the six helpers are source- and AST-identical to Core 12",
          bool(old_defs) and all(n in old_defs and n in new_defs
                                 and _text(core12_part, old_defs[n]) == _text(part_src, new_defs[n])
                                 and ast.dump(old_defs[n]) == ast.dump(new_defs[n]) for n in HELPERS))
    sig_ok = False
    if old_intr is not None:
        old_sig = inspect.signature(old_intr)
        expected_sig = old_sig.replace(parameters=[p for p in old_sig.parameters.values() if p.name != "all_target_ids"])
        sig_ok = ("all_target_ids" in old_sig.parameters
                  and str(inspect.signature(build_epistemic_partition)) == str(expected_sig))
    check("A: the intrinsic signature is Core 12's minus only all_target_ids", sig_ok)
    old_seg = _text(core12_part, old_defs["build_epistemic_partition"]) if "build_epistemic_partition" in old_defs else ""
    new_seg = _text(part_src, new_defs["build_epistemic_partition"]) if "build_epistemic_partition" in new_defs else None
    lines = old_seg.splitlines()
    starts = [i for i in range(len(lines) - 4) if tuple(ln.strip() for ln in lines[i:i + 5]) == REMOVED_STATUS]
    params = [i for i, ln in enumerate(lines) if ln.strip() == REMOVED_PARAM]
    expected_seg = None
    if len(starts) == 1 and len(params) == 1:
        drop = set(range(starts[0], starts[0] + 5)) | {params[0]}
        expected_seg = "\n".join(ln for i, ln in enumerate(lines) if i not in drop)
    check("A: the builder source is Core 12 minus exactly the parameter line and the five status lines",
          expected_seg is not None and expected_seg == new_seg)
    dropper = _DropRunContext()
    old_ast = dropper.visit(copy.deepcopy(old_defs["build_epistemic_partition"])) if "build_epistemic_partition" in old_defs else None
    check("A: the builder AST is Core 12 minus exactly the all_target_ids argument and the status assignment",
          old_ast is not None and dropper.args == 1 and dropper.assigns == 1 and "build_epistemic_partition" in new_defs
          and ast.dump(old_ast) == ast.dump(new_defs["build_epistemic_partition"]))
    docs = _docstring_ids(part_tree)
    check("A: no all_target_ids and no operational reconstruction status anywhere in epistemic.partition",
          not any((isinstance(n, ast.Name) and n.id == "all_target_ids") or (isinstance(n, ast.arg) and n.arg == "all_target_ids")
                  for n in ast.walk(part_tree))
          and not any(isinstance(n, ast.Constant) and id(n) not in docs and n.value in STATUS_WORDS for n in ast.walk(part_tree)))
    old_if, new_if = (_source_if(ast.parse(core12_part)) if core12_part else None), _source_if(part_tree)
    if_ok = old_if is not None and new_if is not None
    if if_ok:
        d2 = _DropRunContext()
        old_if_ast = d2.visit(copy.deepcopy(old_if))
        old_if_src = _text(core12_part, old_if).splitlines()
        k = [i for i in range(len(old_if_src) - 4) if tuple(x.strip() for x in old_if_src[i:i + 5]) == REMOVED_STATUS]
        if_ok = (d2.assigns == 1 and ast.dump(old_if_ast) == ast.dump(new_if) and len(k) == 1
                 and "\n".join(old_if_src[:k[0]] + old_if_src[k[0] + 5:]) == _text(part_src, new_if))
    counts = [ln.strip() for ln in (new_seg or "").splitlines() if ln.strip().startswith(("mapped_n =", "incidental_n ="))]
    check("A: surface_source construction and the mapped/incidental counts are source- and AST-identical to Core 12",
          if_ok and counts == ["mapped_n = int((mapped_other & m).sum())", "incidental_n = int((incidental_other & m).sum())"]
          and '"mapped_cells": mapped_n,' in (new_seg or "") and '"incidental_cells": incidental_n,' in (new_seg or ""))
    check("A: epistemic.partition defines exactly the Core-12 names, in order", list(new_defs) == list(PURE_NAMES))
    check("A: import statements identical to Core 12; no experiment, run_context or candidate_policy import anywhere",
          bool(core12_part)
          and [ast.dump(n) for n in ast.parse(core12_part).body if isinstance(n, (ast.Import, ast.ImportFrom))]
          == [ast.dump(n) for n in part_tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
          and not any(m.startswith("fov3d.experiments") or "run_context" in m or "candidate_policy" in m
                      for m in _all_import_modules(part_src)))
    bindings_ok = ref_p is not None
    for name in HELPERS + ("build_epistemic_partition",):
        if ref_p is None:
            break
        fn_new, fn_old = getattr(epistemic_partition, name), getattr(ref_p, name)
        gn = _global_names(fn_new)
        bindings_ok &= gn == _global_names(fn_old) and fn_new.__globals__ is vars(epistemic_partition)
        for g in gn:
            if g in PURE_NAMES:
                bindings_ok &= g in vars(epistemic_partition)
                continue
            a = vars(epistemic_partition).get(g, getattr(builtins, g, None))
            b = ref_p.__dict__.get(g, getattr(builtins, g, None))
            bindings_ok &= a is not None and a is b
    check("A: global bindings of the intrinsic functions are equivalent to Core 12", bindings_ok)

    # ---- B. intrinsic behavior: helper known answers (subsumed), fixtures, projection equivalence
    blobs = np.array([[1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 0, 0], [1, 1, 0, 1]], bool)
    c4, c8 = _outcome(_component_labels, blobs, 4), _outcome(_component_labels, blobs, 8)
    check("B: _component_labels 4/8-connectivity counts and raster-order int32 labels",
          c4[0] == "ok" and type(c4[1][0]) is int and c4[1][0] == 6
          and _raster(c4[1][1], [[1, 0, 0, 2], [0, 3, 0, 2], [0, 0, 0, 0], [4, 4, 0, 5]], np.int32)
          and c8[0] == "ok" and c8[1][0] == 5
          and _raster(c8[1][1], [[1, 0, 0, 2], [0, 1, 0, 2], [0, 0, 0, 0], [3, 3, 0, 4]], np.int32))
    none = _outcome(_distance_to_target, np.zeros((2, 3), bool), 0.5)
    corner = np.zeros((3, 4), np.int64)
    corner[0, 0] = 1
    dt = _outcome(_distance_to_target, corner, 0.5)
    expected_cells = np.array([[0.0, 1.0, 2.0, 3.0], [1.0, DIAG, KNIGHT, KNIGHT + 1.0],
                               [2.0, KNIGHT, 2 * DIAG, KNIGHT + DIAG]])
    check("B: _distance_to_target: +inf without target; OpenCV L2/5x5 chamfer x grid_deg, float32",
          none[0] == "ok" and none[1].dtype == np.float32 and bool(np.isposinf(none[1]).all())
          and dt[0] == "ok" and dt[1].dtype == np.float32 and bool(np.allclose(dt[1], expected_cells * 0.5, rtol=0.0, atol=1e-4)))
    grid = np.zeros((5, 5), bool)

    def edge(*cells):
        m = grid.copy()
        for c in cells:
            m[c] = True
        return _outcome(_touches_edge, m)

    check("B: _touches_edge: empty/interior/next-to-border False; each border True (Python bool)",
          edge() == ("ok", False) and edge((2, 2)) == ("ok", False) and edge((1, 1), (1, 3), (3, 1), (3, 3)) == ("ok", False)
          and edge((0, 2)) == ("ok", True) and edge((4, 2)) == ("ok", True) and edge((2, 0)) == ("ok", True)
          and edge((2, 4)) == ("ok", True) and type(edge((0, 2))[1]) is bool)
    cm = np.zeros((5, 11), bool)
    cm[0, 1] = cm[0, 4] = cm[2, 4] = True
    cdom = {"yaw": [-10.0, 10.0], "pitch": [-4.0, 4.0]}
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
          and _same(ang((-20.0, 0.0), (30.0, 0.0)), ("ok", 50.0), 1e-9)
          and _same(ang((0.0, -10.0), (0.0, 30.0)), ("ok", 40.0), 1e-9)
          and _same(ang((0.0, 30.0), (0.0, -10.0)), ("ok", 40.0), 1e-9)
          and _same(ang((0.0, 60.0), (30.0, 60.0)), ("ok", _great_circle((0.0, 60.0), (30.0, 60.0))), 1e-9))
    ifc = _outcome(_region_interfaces, np.array([[9, 9, 10, 0], [2, 2, 10, 10], [2, 12, 12, 10]], np.int64))
    wide = _outcome(_region_interfaces, np.array([[300, 44], [300, 44]]))
    check("B: _region_interfaces: H+V accumulation, background ignored, numeric order, symmetric int adjacency, >8-bit codes",
          ifc[0] == "ok" and _same(ifc[1][0], [
              {"region_code_a": 2, "region_code_b": 9, "interface_edge_count": 2},
              {"region_code_a": 2, "region_code_b": 10, "interface_edge_count": 1},
              {"region_code_a": 2, "region_code_b": 12, "interface_edge_count": 2},
              {"region_code_a": 9, "region_code_b": 10, "interface_edge_count": 1},
              {"region_code_a": 10, "region_code_b": 12, "interface_edge_count": 2}])
          and {k: dict(v) for k, v in ifc[1][1].items()} == {
              9: {10: 1, 2: 2}, 2: {10: 1, 12: 2, 9: 2}, 10: {9: 1, 2: 1, 12: 2}, 12: {2: 2, 10: 2}}
          and wide[0] == "ok" and _same(wide[1][0], [{"region_code_a": 44, "region_code_b": 300, "interface_edge_count": 2}]))

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
    kw1 = dict(target_id=7, target_name="fixture-target", domain={"yaw": [-10.0, 10.0], "pitch": [-6.0, 6.0]},
               grid_deg=4.0, gazes_deg=gazes)
    # H2 (2x6) diagonal checkerboards:  T U O X E U / U T X O U E   (O = other surface 5)
    h2 = {
        "target_support": np.array([[1, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0]], bool),
        "owner_instance": np.array([[7, 0, 5, 0, 0, 0], [0, 7, 0, 5, 0, 0]]),
        "nearest_instance": np.array([[7, 0, 5, 0, 7, 0], [0, 7, 0, 5, 0, 7]]),
        "ambiguous_instance": np.array([[0, 0, 0, 1, 0, 0], [0, 0, 1, 0, 0, 0]], bool),
        "depth_seen": np.ones((2, 6), bool), "seen_any": np.ones((2, 6), bool),
    }
    kw2 = dict(target_id=7, target_name="t", domain={"yaw": [-10.0, 10.0], "pitch": [-2.0, 2.0]}, grid_deg=4.0, gazes_deg=[])
    # H3 (2x3) no target support and no gazes:  U O U / E U U   (O = incidental 9)
    h3 = {
        "target_support": np.zeros((2, 3), bool), "owner_instance": np.zeros((2, 3), np.int32),
        "nearest_instance": np.array([[0, 9, 0], [7, 0, 0]]), "ambiguous_instance": np.zeros((2, 3), bool),
        "depth_seen": np.array([[0, 1, 0], [1, 0, 0]], bool), "seen_any": np.array([[1, 1, 1], [0, 0, 0]], bool),
    }
    kw3 = dict(target_id=7, target_name="t", domain={"yaw": [-4.0, 4.0], "pitch": [-2.0, 2.0]}, grid_deg=4.0, gazes_deg=[])
    fixtures = {"H1": (h1, kw1, {7, 25, 90}), "H2": (h2, kw2, {7}), "H3": (h3, kw3, {7})}
    old_i = {k: (_outcome(old_intr, s, all_target_ids=t, **kw) if old_intr else ("no-reference", "")) for k, (s, kw, t) in fixtures.items()}
    new_i = {k: _outcome(build_epistemic_partition, s, **kw) for k, (s, kw, t) in fixtures.items()}
    old_h = {k: (_outcome(old_hist, s, all_target_ids=t, **kw) if old_hist else ("no-reference", "")) for k, (s, kw, t) in fixtures.items()}
    new_h = {k: _outcome(build_candidate_partition, s, all_target_ids=t, **kw) for k, (s, kw, t) in fixtures.items()}
    rc_p = {k: _outcome(build_run_context_partition, s, all_target_ids=t, **kw) for k, (s, kw, t) in fixtures.items()}
    old_rows = [r for k in fixtures if old_i[k][0] == "ok" for r in old_i[k][1][1]]
    check("B: fixtures witness all kinds, every surface_source and reconstruction_status, edge flags, 4/8 connectivity, "
          "target-free and no-gaze cases",
          {r["kind"] for r in old_rows} == set(KINDS)
          and {r.get("surface_source") for r in old_rows} >= {"mapped_and_incidental", "mapped", "incidental"}
          and {r.get("reconstruction_status") for r in old_rows} >= {"mapped_now", "targeted_later", "never_targeted"}
          and {r["touches_domain_edge"] for r in old_rows} == {True, False}
          and old_i["H2"][0] == "ok" and len(old_i["H2"][1][1]) == 9
          and old_i["H3"][0] == "ok" and not any(r["kind"] == "TARGET_SUPPORT" for r in old_i["H3"][1][1]))
    for k in fixtures:
        o, n = old_i[k], new_i[k]
        both = o[0] == "ok" and n[0] == "ok" and isinstance(n[1], tuple) and len(n[1]) == 4
        check(f"B: {k} intrinsic arrays, edges and diag are identical to Core 12 (keys, order, dtype, shape, values)",
              both and _same(n[1][0], o[1][0]) and _same(n[1][2], o[1][2]) and _same(n[1][3], o[1][3]))
        check(f"B: {k} intrinsic rows = Core-12 rows minus only 'reconstruction_status' (order, keys, values, types)",
              both and _same(n[1][1], _drop(o[1][1], "reconstruction_status")))
    bad = dict(h3, seen_any=np.zeros((3, 2), bool))
    check("B: malformed shapes raise the accepted ValueError in the Core-13 and Core-12 builders",
          _outcome(build_epistemic_partition, bad, **kw3)
          == ("ValueError", "Phase-5 state rasters do not share one chart shape")
          == (_outcome(old_intr, bad, all_target_ids=set(), **kw3) if old_intr else None))

    arrays1, rows1, edges1, diag1 = new_i["H1"][1] if new_i["H1"][0] == "ok" else ({}, [], [], {})
    check("B: H1 hand-derived class, surface, mask and region rasters",
          _raster(arrays1.get("class_code"), [[1, 1, 2, 2, 2, 3], [1, 4, 2, 2, 2, 3], [5, 4, 3, 2, 2, 3], [5, 3, 3, 2, 2, 3]], np.uint8)
          and _raster(arrays1.get("surface_instance"), [[0, 0, 3, 3, 12, 0], [0, 60, 3, 12, 12, 0], [0, 0, 0, 25, 40, 0], [0, 0, 0, 25, 40, 0]], np.int32)
          and _raster(arrays1.get("mapped_other"), [[0, 0, 1, 0, 1, 0], [0, 1, 1, 1, 1, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]], np.bool_)
          and _raster(arrays1.get("incidental_other"), [[0, 0, 0, 1, 0, 0], [0, 0, 0, 0, 0, 0], [0, 0, 0, 1, 1, 0], [0, 0, 0, 1, 1, 0]], np.bool_)
          and _raster(arrays1.get("region_code"), [[1, 1, 2, 2, 3, 6], [1, 8, 2, 3, 3, 6], [9, 8, 7, 4, 5, 6], [9, 7, 7, 4, 5, 6]], np.int32))
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
    expected_diag = {
        "target_id": 7, "target_name": "fixture-target", "chart_shape_hw": [4, 6], "region_count": 9,
        "kind_region_counts": {"AMBIGUOUS_BOUNDARY": 1, "OTHER_SURFACE": 4, "TARGET_EVIDENCE_UNMAPPED": 1,
                               "TARGET_SUPPORT": 1, "UNKNOWN": 2},
        "kind_cell_counts": {"TARGET_SUPPORT": 3, "OTHER_SURFACE": 10, "UNKNOWN": 7,
                             "AMBIGUOUS_BOUNDARY": 2, "TARGET_EVIDENCE_UNMAPPED": 2},
        "target_evidence_unmapped_cells": 2, "ambiguous_boundary_cells": 2, "head_depth_cells": 14,
        "eye_ray_seen_cells": 12, "truth_used": False}
    check("B: H1 hand-derived intrinsic rows: every field, key order and type, without candidate or status",
          _same(rows1, _drop(expected_view, "candidate", "reconstruction_status"), 1e-3))
    check("B: H1 hand-derived edge rows and intrinsic diag",
          _same(edges1, [{"region_code_a": a, "region_code_b": b, "interface_edge_count": c}
                         for a in sorted(adjacency) for b, c in sorted(adjacency[a].items()) if a < b])
          and _same(diag1, expected_diag))
    rows3 = new_i["H3"][1][1] if new_i["H3"][0] == "ok" else []
    check("B: H2 hand-derived connectivity and H3 target-free/no-gaze rows",
          new_i["H2"][0] == "ok" and _raster(new_i["H2"][1][0]["region_code"], [[1, 3, 2, 7, 9, 4], [5, 1, 8, 2, 6, 9]], np.int32)
          and len(rows3) == 4 and _raster(new_i["H3"][1][0]["region_code"], [[2, 1, 3], [4, 3, 3]], np.int32)
          and all(r["min_distance_to_target_deg"] is None and r["min_distance_to_historical_gaze_deg"] is None for r in rows3))

    # ---- C. surface_source remains intrinsic evidence provenance
    os_rows = [r for r in rows1 if r["kind"] == "OTHER_SURFACE"]
    check("C: intrinsic OTHER_SURFACE rows carry surface_source mapped_and_incidental/mapped/incidental/incidental "
          "with mapped/incidental counts 2/1, 3/0, 0/2, 0/2",
          [(r.get("surface_source"), r.get("mapped_cells"), r.get("incidental_cells")) for r in os_rows]
          == [("mapped_and_incidental", 2, 1), ("mapped", 3, 0), ("incidental", 0, 2), ("incidental", 0, 2)]
          and all(type(r["surface_source"]) is str for r in os_rows))
    check("C: no intrinsic row carries reconstruction_status; non-OTHER_SURFACE rows carry no surface_source; "
          "H3 incidental surface is intrinsic",
          len(rows1) == 9 and not any("reconstruction_status" in r for k in fixtures if new_i[k][0] == "ok" for r in new_i[k][1][1])
          and not any("surface_source" in r for r in rows1 if r["kind"] != "OTHER_SURFACE")
          and len(rows3) == 4 and rows3[0].get("surface_source") == "incidental")
    sched_a = _outcome(build_run_context_partition, h1, all_target_ids=set(), **kw1)
    sched_b = _outcome(build_run_context_partition, h1, all_target_ids={3, 12, 25, 40}, **kw1)
    check("C: surface_source does not depend on the schedule while reconstruction_status does (live control)",
          sched_a[0] == "ok" and sched_b[0] == "ok"
          and [r.get("surface_source") for r in sched_a[1][1]] == [r.get("surface_source") for r in sched_b[1][1]]
          == [r.get("surface_source") for r in rows1]
          and [r.get("reconstruction_status") for r in sched_a[1][1]][1:5] == ["mapped_now", "mapped_now", "never_targeted", "never_targeted"]
          and [r.get("reconstruction_status") for r in sched_b[1][1]][1:5] == ["mapped_now", "mapped_now", "targeted_later", "targeted_later"])

    # ---- D. reconstruction-status annotation
    def os_row(code, iid, mapped, inc, source):
        return {"region_code": code, "kind": "OTHER_SURFACE", "instance_id": iid, "mapped_cells": mapped,
                "incidental_cells": inc, "surface_source": source, "adjacent_regions": [], "adjacent_to_target_support": False}

    synthetic = [
        os_row(1, 3, 2, 0, "mapped"),                       # mapped, scheduled
        os_row(2, 99, 1, 4, "mapped_and_incidental"),       # mapped, never scheduled
        os_row(3, 25, 0, 3, "incidental"),                  # scheduled later
        os_row(4, 40, 0, 1, "incidental"),                  # never scheduled
        {"region_code": 5, "kind": "TARGET_SUPPORT", "instance_id": 25, "mapped_cells": 0, "incidental_cells": 0},
        {"region_code": 6, "kind": "UNKNOWN", "instance_id": None, "mapped_cells": 0, "incidental_cells": 0},
        {"region_code": 7, "kind": "TARGET_EVIDENCE_UNMAPPED", "instance_id": 25, "mapped_cells": 0, "incidental_cells": 0},
    ]
    snap = copy.deepcopy(synthetic)
    ann = _outcome(annotate_reconstruction_status, synthetic, all_target_ids={3, 25, 7})
    want = [_with_after(r, "surface_source", "reconstruction_status", s) if s else dict(r)
            for r, s in zip(snap, ["mapped_now", "mapped_now", "targeted_later", "never_targeted", None, None, None])]
    check("D: the accepted rule: mapped -> mapped_now; unmapped scheduled -> targeted_later; unmapped unscheduled -> "
          "never_targeted; only OTHER_SURFACE rows (Python str, right after surface_source)",
          ann[0] == "ok" and _same(ann[1], want))
    check("D: the rule reads mapped_cells (the accepted mapped_n), not surface_source",
          _same(_outcome(annotate_reconstruction_status, [os_row(1, 40, 2, 0, "incidental"), os_row(2, 3, 0, 1, "mapped")],
                         all_target_ids=set()),
                ("ok", [_with_after(os_row(1, 40, 2, 0, "incidental"), "surface_source", "reconstruction_status", "mapped_now"),
                        _with_after(os_row(2, 3, 0, 1, "mapped"), "surface_source", "reconstruction_status", "never_targeted")])))
    check("D: annotation does not mutate its inputs, returns new dicts in order, and keeps every value object",
          ann[0] == "ok" and _same(synthetic, snap) and len(ann[1]) == len(synthetic)
          and all(a is not s and all(a[k] is s[k] for k in s) for a, s in zip(ann[1], synthetic)) and ann[1] is not synthetic)
    real = _outcome(annotate_reconstruction_status, rows1, all_target_ids={7, 25, 90})
    check("D: on the intrinsic H1 rows only OTHER_SURFACE rows receive the status, immediately after surface_source",
          real[0] == "ok" and all(
              (list(a) == list(_with_after(p, "surface_source", "reconstruction_status", None)) and type(a["reconstruction_status"]) is str)
              if p["kind"] == "OTHER_SURFACE" else list(a) == list(p) for a, p in zip(real[1], rows1)))
    check("D: missing anchor and double annotation fail loudly; an empty partition stays empty",
          _outcome(annotate_reconstruction_status, [{"region_code": 1, "kind": "OTHER_SURFACE", "instance_id": 3,
                                                     "mapped_cells": 0}], all_target_ids=set())[0] == "KeyError"
          and (real[0] == "ok" and _outcome(annotate_reconstruction_status, real[1], all_target_ids=set())[0] == "ValueError")
          and _outcome(annotate_reconstruction_status, [], all_target_ids={1}) == ("ok", []))

    # ---- E. recontextualization identity
    check("E: annotate_reconstruction_status(NEW_INTRINSIC rows) == Core-12 intrinsic rows on every fixture",
          all(old_i[k][0] == "ok" and new_i[k][0] == "ok"
              and _same(_outcome(annotate_reconstruction_status, new_i[k][1][1], all_target_ids=t), ("ok", old_i[k][1][1]))
              for k, (s, kw, t) in fixtures.items()))
    check("E: build_run_context_partition == Core-12 build_epistemic_partition on every fixture",
          all(old_i[k][0] == "ok" and rc_p[k][0] == "ok" and _same(rc_p[k][1], old_i[k][1]) for k in fixtures))
    calls: dict[str, list] = {"intr": [], "ann": []}
    real_intr, real_ann = run_context.build_epistemic_partition, run_context.annotate_reconstruction_status

    def spy_intr(*a, **kw):
        out = real_intr(*a, **kw)
        calls["intr"].append((kw, out))
        return out

    def spy_ann(*a, **kw):
        calls["ann"].append(kw)
        return real_ann(*a, **kw)

    run_context.build_epistemic_partition, run_context.annotate_reconstruction_status = spy_intr, spy_ann
    try:
        w = _outcome(build_run_context_partition, h1, all_target_ids={7, 25, 90}, **kw1)
    finally:
        run_context.build_epistemic_partition, run_context.annotate_reconstruction_status = real_intr, real_ann
    check("E: the run-context wrapper builds the intrinsic partition once (without all_target_ids), annotates once, "
          "and passes arrays, edges and diag through as the same objects",
          real_intr is build_epistemic_partition and len(calls["intr"]) == 1 and len(calls["ann"]) == 1
          and "all_target_ids" not in calls["intr"][0][0] and calls["ann"][0] == {"all_target_ids": {7, 25, 90}}
          and w[0] == "ok" and w[1][0] is calls["intr"][0][1][0] and w[1][2] is calls["intr"][0][1][2]
          and w[1][3] is calls["intr"][0][1][3])
    check("E: build_run_context_partition keeps the historical Core-12 signature (with all_target_ids)",
          old_intr is not None and str(inspect.signature(build_run_context_partition)) == str(inspect.signature(old_intr)))

    # ---- F. candidate composition
    for k in fixtures:
        check(f"F: {k} build_candidate_partition == accepted Core-12 build_candidate_partition (type/order/value)",
              old_h[k][0] == "ok" and new_h[k][0] == "ok" and _same(new_h[k][1], old_h[k][1]))
    cnt = {"intr": 0, "ann": 0, "wrap": 0, "cand": 0}
    saved = (run_context.build_epistemic_partition, run_context.annotate_reconstruction_status,
             candidate_policy.build_run_context_partition, candidate_policy.annotate_candidate_partition)

    def counting(key, fn):
        def inner(*a, **kw):
            cnt[key] += 1
            return fn(*a, **kw)
        return inner

    run_context.build_epistemic_partition = counting("intr", saved[0])
    run_context.annotate_reconstruction_status = counting("ann", saved[1])
    candidate_policy.build_run_context_partition = counting("wrap", saved[2])
    candidate_policy.annotate_candidate_partition = counting("cand", saved[3])
    try:
        comp = _outcome(build_candidate_partition, h1, all_target_ids={7, 25, 90}, **kw1)
    finally:
        (run_context.build_epistemic_partition, run_context.annotate_reconstruction_status,
         candidate_policy.build_run_context_partition, candidate_policy.annotate_candidate_partition) = saved
    check("F: one build_candidate_partition call = one intrinsic build, one status annotation, one run-context "
          "wrapper call and one candidate annotation",
          comp[0] == "ok" and cnt == {"intr": 1, "ann": 1, "wrap": 1, "cand": 1}
          and saved[2] is build_run_context_partition and old_h["H1"][0] == "ok" and _same(comp[1], old_h["H1"][1]))
    pol_src = (ROOT / CP / "candidate_policy.py").read_text(encoding="utf-8")
    pol_old, pol_new = (_top(core12_pol) if core12_pol else {}), _top(pol_src)

    def norm(node):
        dumped = ast.dump(_strip_docstrings(node))
        return dumped.replace("build_run_context_partition", "build_epistemic_partition")

    check("F: CANDIDATE_KINDS, _insert_after and annotate_candidate_partition are unchanged from Core 12; "
          "build_candidate_partition differs only in the called builder",
          type(CANDIDATE_KINDS) is set and CANDIDATE_KINDS == {"OTHER_SURFACE", "UNKNOWN"}
          and bool(pol_old) and all(n in pol_old and n in pol_new
                                    and _text(core12_pol, pol_old[n]) == _text(pol_src, pol_new[n])
                                    for n in ("CANDIDATE_KINDS", "_insert_after", "annotate_candidate_partition"))
          and "build_candidate_partition" in pol_new and norm(pol_old["build_candidate_partition"]) == norm(pol_new["build_candidate_partition"])
          and list(pol_new) == list(pol_old)
          and old_hist is not None and str(inspect.signature(build_candidate_partition)) == str(inspect.signature(old_hist)))
    check("F: candidate_policy imports build_run_context_partition, not the intrinsic builder",
          _imports(pol_src).get("build_run_context_partition") == "fov3d.experiments.classroom_partition.run_context.build_run_context_partition"
          and "build_epistemic_partition" not in _imports(pol_src)
          and not hasattr(candidate_policy, "build_epistemic_partition"))

    # ---- G. historical compatibility and wiring
    from fov3d.experiments.classroom_partition import benchmark
    via_bench = _outcome(getattr(benchmark, "build_epistemic_partition", lambda *a, **k: None), h1,
                         all_target_ids={7, 25, 90}, **kw1)
    check("G: benchmark.build_epistemic_partition is the candidate wrapper and returns the accepted Core-12 view; "
          "benchmark.CANDIDATE_KINDS is the policy constant",
          getattr(benchmark, "build_epistemic_partition", None) is build_candidate_partition
          and getattr(benchmark, "CANDIDATE_KINDS", None) is candidate_policy.CANDIDATE_KINDS
          and old_h["H1"][0] == "ok" and via_bench[0] == "ok" and _same(via_bench[1], old_h["H1"][1]))
    unchanged = all((ROOT / CP / f"{m}.py").read_text(encoding="utf-8") == _git_show(f"{CP}{m}.py") != ""
                    for m in list(PRODUCERS) + ["incidental"])
    check("G: the four historical producers and the Phase-5 incidental module are byte-identical to Core 12", unchanged)
    wiring_ok = True
    for mod, n_calls in PRODUCERS.items():
        src = (ROOT / CP / f"{mod}.py").read_text(encoding="utf-8")
        called = [c.func.id for c in ast.walk(ast.parse(src)) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)]
        m = importlib.import_module(f"fov3d.experiments.classroom_partition.{mod}")
        wiring_ok &= called.count("build_candidate_partition") == n_calls
        wiring_ok &= "build_epistemic_partition" not in called and "build_run_context_partition" not in called
        wiring_ok &= getattr(m, "build_candidate_partition", None) is build_candidate_partition
        wiring_ok &= not hasattr(m, "build_run_context_partition")
    check("G: producers call build_candidate_partition (1/1/2/1 sites), never the run-context wrapper or the intrinsic builder",
          wiring_ok)
    status_modules, intr_importers, rc_importers = set(), set(), set()
    for path in sorted((ROOT / "fov3d").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docs_p = _docstring_ids(tree)
        if any(isinstance(n, ast.Constant) and id(n) not in docs_p and n.value in ("targeted_later", "never_targeted")
               for n in ast.walk(tree)):
            status_modules.add(path.name)
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.module == "fov3d.epistemic.partition" and any(a.name == "build_epistemic_partition" for a in n.names):
                intr_importers.add(path.name)
            if isinstance(n, ast.ImportFrom) and (n.module or "").endswith("run_context"):
                rc_importers.add(path.name)
    check("G: no duplicate status implementation: status strings only in run_context and the unchanged Phase-5 "
          "incidental; only run_context imports the intrinsic builder; only candidate_policy imports run_context",
          status_modules == {"run_context.py", "incidental.py"} and intr_importers == {"run_context.py"}
          and rc_importers == {"candidate_policy.py"})

    # ---- H. Phase-8b propagation
    from fov3d.experiments.classroom_partition import challenge_suite
    kw01 = dict(kw1, domain={"yaw": [-0.25, 0.25], "pitch": [-0.15, 0.15]}, grid_deg=0.1)
    nh01 = _outcome(build_candidate_partition, h1, all_target_ids={7, 25, 90}, **kw01)
    oh01 = _outcome(old_hist, h1, all_target_ids={7, 25, 90}, **kw01) if old_hist else ("no-reference", "")
    ref_new = _outcome(challenge_suite.refine_integrated_partition, nh01[1][0], nh01[1][1], grid_deg=0.1) if nh01[0] == "ok" else nh01
    ref_old = _outcome(challenge_suite.refine_integrated_partition, oh01[1][0], oh01[1][1], grid_deg=0.1) if oh01[0] == "ok" else oh01
    base_os = [r for r in (nh01[1][1] if nh01[0] == "ok" else []) if r["kind"] == "OTHER_SURFACE"]
    check("H: Phase-8b base historical rows carry reconstruction_status (all three values)",
          [r.get("reconstruction_status") for r in base_os] == ["mapped_now", "mapped_now", "targeted_later", "never_targeted"])
    by_code = {r["region_code"]: r for r in (nh01[1][1] if nh01[0] == "ok" else [])}
    refined_os = [r for r in (ref_new[1][1] if ref_new[0] == "ok" else []) if r["kind"] == "OTHER_SURFACE"]
    check("H: refine_integrated_partition on the Core-13 view equals that on the Core-12 view; refined OTHER_SURFACE "
          "rows carry their origin's surface_source and reconstruction_status",
          ref_new[0] == "ok" and ref_old[0] == "ok" and _same(ref_new[1], ref_old[1]) and len(refined_os) == 4
          and all(r.get("reconstruction_status", "<missing>") == by_code.get(r.get("origin_region_code"), {}).get("reconstruction_status")
                  and r.get("surface_source", "<missing>") == by_code.get(r.get("origin_region_code"), {}).get("surface_source")
                  for r in refined_os))
    cs_old = _top(_git_show(f"{CP}challenge_suite.py")) if core12_part else {}
    cs_new = _top((ROOT / CP / "challenge_suite.py").read_text(encoding="utf-8"))
    check("H: _component_rows and refine_integrated_partition are AST-identical to Core 12",
          all(n in cs_old and n in cs_new and ast.dump(cs_old[n]) == ast.dump(cs_new[n])
              for n in ("_component_rows", "refine_integrated_partition")))

    def rows8b(kind: str, cells: int, original_row=None):
        mask = np.zeros((6, 6), bool)
        mask.flat[:cells] = True
        res = _outcome(challenge_suite._component_rows, mask, connectivity=4, kind=kind, original_code=None,
                       shell_index=None, next_code=1, refined_code=np.zeros((6, 6), np.int32), original_row=original_row)
        return [(r["candidate_raw"], r["eligible_candidate"], r.get("reconstruction_status")) for r in res[1][1]] if res[0] == "ok" else res

    origin = {"instance_id": 3, "surface_source": "mapped", "reconstruction_status": "mapped_now", "mapped_cells": 5,
              "incidental_cells": 0, "touches_domain_edge": False, "seen_any_fraction": 1.0, "head_depth_fraction": 1.0}
    cases = [("UNKNOWN", 30, None), ("UNKNOWN", 3, None), ("OTHER_SURFACE", 30, None), ("OTHER_SURFACE", 24, None),
             ("OTHER_SURFACE", 30, origin), ("OTHER_SURFACE", 24, dict(origin, reconstruction_status="never_targeted")),
             ("TARGET_SUPPORT", 30, None), ("AMBIGUOUS_BOUNDARY", 30, None), ("TARGET_EVIDENCE_UNMAPPED", 30, None)]
    before = [rows8b(*c) for c in cases]
    kinds_saved = candidate_policy.CANDIDATE_KINDS
    candidate_policy.CANDIDATE_KINDS = set()
    run_context.annotate_reconstruction_status = lambda rows, *, all_target_ids: [dict(r) for r in rows]
    try:
        during = [rows8b(*c) for c in cases]
        control = _outcome(build_candidate_partition, h1, all_target_ids={7, 25, 90}, **kw1)
    finally:
        candidate_policy.CANDIDATE_KINDS = kinds_saved
        run_context.annotate_reconstruction_status = saved[1]
    check("H: Phase-8b candidate_raw/eligible_candidate known answers (MIN_ELIGIBLE_CELLS 25) and status propagation",
          before == [[(True, True, None)], [(True, False, None)], [(True, True, None)], [(True, False, None)],
                     [(True, True, "mapped_now")], [(True, False, "never_targeted")],
                     [(False, False, None)], [(False, False, None)], [(False, False, None)]])
    check("H: Phase-8b interpretation is independent of candidate_policy and run_context (live control)",
          during == before and control[0] == "ok"
          and not any(r.get("candidate", True) or "reconstruction_status" in r for r in control[1][1])
          and new_h["H1"][0] == "ok" and any(r.get("candidate", False) for r in new_h["H1"][1][1]))

    # ---- I. package footprints (fresh processes) and dependencies
    check("I: fov3d/epistemic/__init__.py is unchanged from accepted Core 12",
          bool(core12_part) and (ROOT / "fov3d" / "epistemic" / "__init__.py").read_text(encoding="utf-8")
          == _git_show("fov3d/epistemic/__init__.py"))
    rcm, pol = "fov3d.experiments.classroom_partition.run_context", "fov3d.experiments.classroom_partition.candidate_policy"
    probe = ("mods = sorted(sys.modules)\n"
             "print(json.dumps({'cv2': 'cv2' in sys.modules, 'bpy': 'bpy' in sys.modules,\n"
             f"  'run_context': {rcm!r} in sys.modules, 'policy': {pol!r} in sys.modules,\n"
             "  'fov3d': [m for m in mods if m.startswith('fov3d')]}))\n")
    pkg = ["fov3d", "fov3d.epistemic", "fov3d.epistemic.partition", "fov3d.experiments",
           "fov3d.experiments.classroom_partition", "fov3d.experiments.classroom_partition.lift", rcm,
           "fov3d.geometry", "fov3d.geometry.head_chart", "fov3d.reconstruction", "fov3d.reconstruction.association",
           "fov3d.scene", "fov3d.scene.model", "fov3d.scene.sphere"]
    check("I: fresh bare import fov3d.epistemic stays lightweight",
          _fresh("import fov3d.epistemic\n" + probe) == {"cv2": False, "bpy": False, "run_context": False, "policy": False,
                                                        "fov3d": ["fov3d", "fov3d.epistemic"]})
    check("I: fresh import fov3d.epistemic.partition: no experiment, run_context or candidate_policy",
          _fresh("import fov3d.epistemic.partition\n" + probe) == {
              "cv2": True, "bpy": False, "run_context": False, "policy": False,
              "fov3d": ["fov3d", "fov3d.epistemic", "fov3d.epistemic.partition", "fov3d.geometry", "fov3d.geometry.head_chart"]})
    check("I: fresh import run_context: the experiment-package footprint plus the intrinsic partition only "
          "(no candidate_policy, benchmark/evaluator, stereo, renderer or bpy)",
          _fresh(f"import {rcm}\n" + probe) == {"cv2": True, "bpy": False, "run_context": True, "policy": False,
                                               "fov3d": sorted(pkg)})
    check("I: fresh import candidate_policy: run_context and the intrinsic partition, no benchmark/evaluator/stereo/renderer",
          _fresh(f"import {pol}\n" + probe) == {"cv2": True, "bpy": False, "run_context": True, "policy": True,
                                               "fov3d": sorted(pkg + [pol])})
    rc_src = (ROOT / CP / "run_context.py").read_text(encoding="utf-8")
    orders = [
        _fresh(f"import {rcm} as r\nimport {pol} as c\nimport fov3d.experiments.classroom_partition.benchmark as b\n"
               "print(json.dumps(b.build_epistemic_partition is c.build_candidate_partition and c.build_run_context_partition is r.build_run_context_partition))\n"),
        _fresh(f"import fov3d.experiments.classroom_partition.benchmark as b\nimport {pol} as c\nimport {rcm} as r\n"
               "print(json.dumps(c.build_run_context_partition is r.build_run_context_partition))\n"),
    ]
    check("I: static imports: run_context -> typing, numpy, epistemic.partition; candidate_policy -> typing, numpy, "
          "run_context; no import cycle in either order",
          _all_import_modules(rc_src) == {"__future__", "typing", "numpy", "fov3d.epistemic.partition"}
          and _all_import_modules(pol_src) == {"__future__", "typing", "numpy", rcm}
          and orders == [True, True])

    # ---- J. seeded random differential against accepted Core 12
    rng = np.random.default_rng(20260929)
    n_states = 300
    agree = 0
    statuses = {"mapped_now": 0, "targeted_later": 0, "never_targeted": 0}
    ctl = {"position": 0, "swap": 0, "schedule": 0}
    ctl_expected = {"position": 0, "swap": 0, "schedule": 0}
    for _ in range(n_states):
        state, kw, targets = _random_state(rng)
        oi = _outcome(old_intr, state, all_target_ids=targets, **kw) if old_intr else ("no-reference", "")
        ni = _outcome(build_epistemic_partition, state, **kw)
        oh = _outcome(old_hist, state, all_target_ids=targets, **kw) if old_hist else ("no-reference", "")
        nh = _outcome(build_candidate_partition, state, all_target_ids=targets, **kw)
        if not (oi[0] == ni[0] == oh[0] == nh[0] == "ok"):
            continue
        rc = _outcome(annotate_reconstruction_status, ni[1][1], all_target_ids=targets)
        agree += (_same(ni[1][0], oi[1][0]) and _same(ni[1][2], oi[1][2]) and _same(ni[1][3], oi[1][3])
                  and _same(ni[1][1], _drop(oi[1][1], "reconstruction_status"))
                  and rc[0] == "ok" and _same(rc[1], oi[1][1]) and _same(nh[1], oh[1]))
        present = [r["reconstruction_status"] for r in oi[1][1] if "reconstruction_status" in r]
        for s in present:
            statuses[s] += 1
        # non-equivalent controls must be detected by the same comparator
        moved = [dict([(k, v) for k, v in r.items() if k != "reconstruction_status"] + [("reconstruction_status", r["reconstruction_status"])])
                 if "reconstruction_status" in r else r for r in oi[1][1]]
        ctl_expected["position"] += bool(present)
        ctl["position"] += bool(present) and not _same(moved, oi[1][1])
        swap = {"targeted_later": "never_targeted", "never_targeted": "targeted_later"}
        swapped = [dict(r, reconstruction_status=swap.get(r["reconstruction_status"], r["reconstruction_status"]))
                   if "reconstruction_status" in r else r for r in oi[1][1]]
        has_unmapped = any(s != "mapped_now" for s in present)
        ctl_expected["swap"] += has_unmapped
        ctl["swap"] += has_unmapped and not _same(swapped, oi[1][1])
        no_sched = [dict(r, reconstruction_status="never_targeted") if r.get("reconstruction_status") == "targeted_later" else r
                    for r in oi[1][1]]
        has_later = "targeted_later" in present
        ctl_expected["schedule"] += has_later
        ctl["schedule"] += has_later and not _same(no_sched, oi[1][1])
    check(f"J: {n_states} random states: NEW_INTRINSIC == project(OLD_INTRINSIC), RECONTEXTUALIZED == OLD_INTRINSIC "
          "and NEW_HISTORICAL == OLD_HISTORICAL (type-strict)", agree == n_states)
    check("J: all three statuses occur repeatedly (>= 50 each)", min(statuses.values()) >= 50)
    check("J: controls are detected wherever they apply: status moved to the end, targeted/never swapped, schedule ignored",
          ctl == ctl_expected and min(ctl_expected.values()) > 0)

    print(f"[conceptual-core13-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
