#!/usr/bin/env python3
"""Fail-capable checks for Conceptual Core 14: historical gaze context separated from the epistemic partition.

The reference is accepted Conceptual Core 13 (read from Git). Core 14 supersedes the Core-13
structural checker: the intrinsic partition no longer takes the observer's action history
(``gazes_deg``) nor emits ``min_distance_to_historical_gaze_deg``; the experiment-side
gaze-context layer re-creates it, and run context and candidate policy compose on top.
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
from fov3d.experiments.classroom_partition import candidate_policy, gaze_context, run_context
from fov3d.experiments.classroom_partition.candidate_policy import build_candidate_partition
from fov3d.experiments.classroom_partition.gaze_context import annotate_gaze_context, build_gaze_context_partition
from fov3d.experiments.classroom_partition.run_context import build_run_context_partition

ACCEPTED_CORE13 = "3b7091ed7a8f58cfc84c552431bfe60dc694aad3"
PARTITION = "fov3d/epistemic/partition.py"
CP = "fov3d/experiments/classroom_partition/"
HELPERS = ("_component_labels", "_distance_to_target", "_touches_edge", "_centroid_angles",
           "_angular_distance_deg", "_region_interfaces")
PURE_NAMES = ("REGION_KIND", "REGION_KIND_BY_CODE") + HELPERS + ("build_epistemic_partition",)
GAZE_FIELD = "min_distance_to_historical_gaze_deg"
REMOVED_PARAM = "gazes_deg: list[tuple[float, float]],"
REMOVED_BLOCK = ("gaze_dist = [", "_angular_distance_deg((cyaw, cpitch), (float(y), float(p)))",
                 "for y, p in gazes_deg", "] if gazes_deg and np.isfinite(cyaw) and np.isfinite(cpitch) else []")
REMOVED_ENTRY = '"min_distance_to_historical_gaze_deg": None if not gaze_dist else float(min(gaze_dist)),'
PRODUCERS = ("benchmark", "prefix_benchmark", "integration", "challenge_suite")
# producer: (gazes_deg keyword value, its list-comprehension iterable, number of partition calls)
GAZE_SOURCES = {
    "benchmark": ("gazes", "obj.get('trajectory', [])", 1),
    "prefix_benchmark": ("current_target_gazes", "trajectory[:local_step + 1]", 1),
    "integration": ("current_gazes", "trajectory[:local_step + 1]", 2),
    "challenge_suite": ("current_gazes", "list(obj.get('trajectory', []))[:keep]", 1),
}
KINDS = ("TARGET_SUPPORT", "OTHER_SURFACE", "UNKNOWN", "AMBIGUOUS_BOUNDARY", "TARGET_EVIDENCE_UNMAPPED")
# OpenCV DIST_L2 / 5x5 chamfer steps in cells: orthogonal 1, diagonal 1.4, knight 2.1969.
DIAG, KNIGHT = 1.4, 2.1969


def _git_show(path: str) -> str:
    proc = subprocess.run(["git", "show", f"{ACCEPTED_CORE13}:{path}"], cwd=ROOT, capture_output=True, text=True)
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


class _DropGaze(ast.NodeTransformer):
    """Core-13 builder AST minus the gazes_deg argument, the gaze_dist assignment and the gaze row entry."""

    def __init__(self) -> None:
        self.args = self.assigns = self.entries = 0

    def visit_arguments(self, node: ast.arguments) -> ast.arguments:
        keep = [(a, d) for a, d in zip(node.kwonlyargs, node.kw_defaults) if a.arg != "gazes_deg"]
        self.args += len(node.kwonlyargs) - len(keep)
        node.kwonlyargs, node.kw_defaults = [a for a, _ in keep], [d for _, d in keep]
        return node

    def visit_Assign(self, node: ast.Assign):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "gaze_dist":
            self.assigns += 1
            return None
        return self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> ast.Dict:
        self.generic_visit(node)
        keep = [(k, v) for k, v in zip(node.keys, node.values) if not (isinstance(k, ast.Constant) and k.value == GAZE_FIELD)]
        self.entries += len(node.keys) - len(keep)
        node.keys, node.values = [k for k, _ in keep], [v for _, v in keep]
        return node


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


def _gv(row) -> object:
    """The gaze-distance value of a row, or a marker when the field is missing (never raises)."""
    return row.get(GAZE_FIELD, "<missing>") if isinstance(row, dict) else "<missing>"


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
    kw = dict(target_id=int(rng.choice([7, 3])), target_name="random",
              domain={"yaw": [-(w - 1) * g / 2, (w - 1) * g / 2], "pitch": [-(h - 1) * g / 2, (h - 1) * g / 2]},
              grid_deg=g)
    targets = {int(x) for x in rng.choice(ids[1:], int(rng.integers(0, 5)), replace=False)}
    gazes = [(float(rng.uniform(-60, 60)), float(rng.uniform(-40, 40))) for _ in range(int(rng.choice([0, 0, 1, 1, 2, 3, 5])))]
    return state, kw, targets, gazes


def main() -> int:
    checked = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal checked, failed
        checked += 1
        if condition:
            print(f"[conceptual-core14-check] PASS {name}")
        else:
            failed += 1
            print(f"[conceptual-core14-check] FAIL {name}")

    # ---- reference: accepted Core-13 partition, run context and candidate policy, bound together
    core13_part, core13_rc, core13_pol = _git_show(PARTITION), _git_show(f"{CP}run_context.py"), _git_show(f"{CP}candidate_policy.py")
    rc_import = "from fov3d.epistemic.partition import build_epistemic_partition\n"
    pol_import = "from fov3d.experiments.classroom_partition.run_context import build_run_context_partition\n"
    ref_p = ref_r = ref_c = None
    if core13_part and core13_rc.count(rc_import) == 1 and core13_pol.count(pol_import) == 1:
        try:
            ref_p = types.ModuleType("_core13_partition_reference")
            sys.modules[ref_p.__name__] = ref_p
            exec(compile(core13_part, "core13_partition.py", "exec"), ref_p.__dict__)
            ref_r = types.ModuleType("_core13_run_context_reference")
            ref_r.__dict__["build_epistemic_partition"] = ref_p.build_epistemic_partition
            sys.modules[ref_r.__name__] = ref_r
            exec(compile(core13_rc.replace(rc_import, ""), "core13_run_context.py", "exec"), ref_r.__dict__)
            ref_c = types.ModuleType("_core13_candidate_policy_reference")
            ref_c.__dict__["build_run_context_partition"] = ref_r.build_run_context_partition
            sys.modules[ref_c.__name__] = ref_c
            exec(compile(core13_pol.replace(pol_import, ""), "core13_candidate_policy.py", "exec"), ref_c.__dict__)
        except Exception:  # noqa: BLE001
            ref_p = ref_r = ref_c = None
    check("reference: accepted Core-13 partition, run context and candidate policy execute from git show 3b7091e",
          None not in (ref_p, ref_r, ref_c))
    old_intr = ref_p.build_epistemic_partition if ref_p is not None else None
    old_rc = ref_r.build_run_context_partition if ref_r is not None else None
    old_hist = ref_c.build_candidate_partition if ref_c is not None else None

    # ---- A. intrinsic-module structure against accepted Core 13
    part_src = (ROOT / PARTITION).read_text(encoding="utf-8")
    part_tree = ast.parse(part_src)
    old_defs, new_defs = (_top(core13_part) if core13_part else {}), _top(part_src)
    check("A: REGION_KIND and REGION_KIND_BY_CODE assignments and values are identical to Core 13",
          bool(old_defs) and all(n in old_defs and n in new_defs and _text(core13_part, old_defs[n]) == _text(part_src, new_defs[n])
                                 for n in ("REGION_KIND", "REGION_KIND_BY_CODE"))
          and _same(REGION_KIND, {"TARGET_SUPPORT": 1, "OTHER_SURFACE": 2, "UNKNOWN": 3,
                                  "AMBIGUOUS_BOUNDARY": 4, "TARGET_EVIDENCE_UNMAPPED": 5})
          and _same(REGION_KIND_BY_CODE, {1: "TARGET_SUPPORT", 2: "OTHER_SURFACE", 3: "UNKNOWN",
                                          4: "AMBIGUOUS_BOUNDARY", 5: "TARGET_EVIDENCE_UNMAPPED"}))
    check("A: the six helpers, including _angular_distance_deg, are source- and AST-identical to Core 13",
          bool(old_defs) and all(n in old_defs and n in new_defs and _text(core13_part, old_defs[n]) == _text(part_src, new_defs[n])
                                 and ast.dump(old_defs[n]) == ast.dump(new_defs[n]) for n in HELPERS))
    sig_ok = False
    if old_intr is not None:
        old_sig = inspect.signature(old_intr)
        want = old_sig.replace(parameters=[p for p in old_sig.parameters.values() if p.name != "gazes_deg"])
        sig_ok = "gazes_deg" in old_sig.parameters and str(inspect.signature(build_epistemic_partition)) == str(want)
    check("A: the intrinsic signature is Core 13's minus only gazes_deg", sig_ok)
    old_seg = _text(core13_part, old_defs["build_epistemic_partition"]) if "build_epistemic_partition" in old_defs else ""
    new_seg = _text(part_src, new_defs["build_epistemic_partition"]) if "build_epistemic_partition" in new_defs else None
    lines = old_seg.splitlines()
    blocks = [i for i in range(len(lines) - 3) if tuple(ln.strip() for ln in lines[i:i + 4]) == REMOVED_BLOCK]
    params = [i for i, ln in enumerate(lines) if ln.strip() == REMOVED_PARAM]
    entries = [i for i, ln in enumerate(lines) if ln.strip() == REMOVED_ENTRY]
    expected_seg = None
    if len(blocks) == len(params) == len(entries) == 1:
        drop = set(range(blocks[0], blocks[0] + 4)) | {params[0], entries[0]}
        expected_seg = "\n".join(ln for i, ln in enumerate(lines) if i not in drop)
    check("A: the builder source is Core 13 minus exactly the parameter line, the four gaze_dist lines and the gaze row entry",
          expected_seg is not None and expected_seg == new_seg)
    dropper = _DropGaze()
    old_ast = dropper.visit(copy.deepcopy(old_defs["build_epistemic_partition"])) if "build_epistemic_partition" in old_defs else None
    check("A: the builder AST is Core 13 minus exactly the gazes_deg argument, the gaze_dist assignment and the gaze entry",
          old_ast is not None and (dropper.args, dropper.assigns, dropper.entries) == (1, 1, 1)
          and "build_epistemic_partition" in new_defs and ast.dump(old_ast) == ast.dump(new_defs["build_epistemic_partition"]))
    docs = _docstring_ids(part_tree)
    check("A: no gazes_deg, gaze_dist or gaze-distance field anywhere in epistemic.partition (docstrings aside)",
          not any((isinstance(n, ast.Name) and n.id in ("gazes_deg", "gaze_dist"))
                  or (isinstance(n, ast.arg) and n.arg == "gazes_deg") for n in ast.walk(part_tree))
          and not any(isinstance(n, ast.Constant) and id(n) not in docs and n.value == GAZE_FIELD for n in ast.walk(part_tree)))

    def row_dict(src):
        dicts = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Dict)
                 and any(isinstance(k, ast.Constant) and k.value == "seen_any_fraction" for k in n.keys)]
        return [(k.value, ast.unparse(v)) for k, v in zip(dicts[0].keys, dicts[0].values)] if len(dicts) == 1 else None

    old_row, new_row = (row_dict(core13_part) if core13_part else None), row_dict(part_src)
    check("A: every other row field (identity, geometry, target distances, evidence history) is identical, in order",
          old_row is not None and new_row is not None and new_row == [e for e in old_row if e[0] != GAZE_FIELD]
          and [k for k, _ in new_row] == ["region_code", "region_id", "kind", "instance_id", "cell_count",
                                          "touches_domain_edge", "centroid_yaw_deg", "centroid_pitch_deg",
                                          "min_distance_to_target_deg", "median_distance_to_target_deg",
                                          "seen_any_fraction", "head_depth_fraction", "mapped_cells", "incidental_cells"])
    check("A: epistemic.partition defines exactly the Core-13 names, in order", list(new_defs) == list(PURE_NAMES))
    check("A: import statements identical to Core 13; no experiment, gaze_context, run_context or candidate_policy import",
          bool(core13_part)
          and [ast.dump(n) for n in ast.parse(core13_part).body if isinstance(n, (ast.Import, ast.ImportFrom))]
          == [ast.dump(n) for n in part_tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
          and not any(m.startswith("fov3d.experiments") or any(w in m for w in ("gaze_context", "run_context", "candidate_policy"))
                      for m in _all_import_modules(part_src)))
    bindings_ok = ref_p is not None
    for name in HELPERS + ("build_epistemic_partition",):
        if ref_p is None:
            break
        fn_new, fn_old = getattr(epistemic_partition, name), getattr(ref_p, name)
        gn, go = _global_names(fn_new), _global_names(fn_old)
        droppable = {"_angular_distance_deg", "min"} if name == "build_epistemic_partition" else set()
        bindings_ok &= gn <= go and (go - gn) <= droppable and "_angular_distance_deg" not in (gn if droppable else set())
        bindings_ok &= fn_new.__globals__ is vars(epistemic_partition)
        for g in gn:
            if g in PURE_NAMES:
                bindings_ok &= g in vars(epistemic_partition)
                continue
            a = vars(epistemic_partition).get(g, getattr(builtins, g, None))
            b = ref_p.__dict__.get(g, getattr(builtins, g, None))
            bindings_ok &= a is not None and a is b
    check("A: global bindings equivalent to Core 13; the builder no longer calls _angular_distance_deg", bindings_ok)

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
    expected_cells = np.array([[0.0, 1.0, 2.0, 3.0], [1.0, DIAG, KNIGHT, KNIGHT + 1.0], [2.0, KNIGHT, 2 * DIAG, KNIGHT + DIAG]])
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
    check("B: _region_interfaces: H+V accumulation, background ignored, numeric order, symmetric adjacency, >8-bit codes",
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
    kw1 = dict(target_id=7, target_name="fixture-target", domain={"yaw": [-10.0, 10.0], "pitch": [-6.0, 6.0]}, grid_deg=4.0)
    # H2 (2x6) diagonal checkerboards:  T U O X E U / U T X O U E   (O = other surface 5)
    h2 = {
        "target_support": np.array([[1, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0]], bool),
        "owner_instance": np.array([[7, 0, 5, 0, 0, 0], [0, 7, 0, 5, 0, 0]]),
        "nearest_instance": np.array([[7, 0, 5, 0, 7, 0], [0, 7, 0, 5, 0, 7]]),
        "ambiguous_instance": np.array([[0, 0, 0, 1, 0, 0], [0, 0, 1, 0, 0, 0]], bool),
        "depth_seen": np.ones((2, 6), bool), "seen_any": np.ones((2, 6), bool),
    }
    kw2 = dict(target_id=7, target_name="t", domain={"yaw": [-10.0, 10.0], "pitch": [-2.0, 2.0]}, grid_deg=4.0)
    # H3 (2x3) no target support:  U O U / E U U   (O = incidental 9)
    h3 = {
        "target_support": np.zeros((2, 3), bool), "owner_instance": np.zeros((2, 3), np.int32),
        "nearest_instance": np.array([[0, 9, 0], [7, 0, 0]]), "ambiguous_instance": np.zeros((2, 3), bool),
        "depth_seen": np.array([[0, 1, 0], [1, 0, 0]], bool), "seen_any": np.array([[1, 1, 1], [0, 0, 0]], bool),
    }
    kw3 = dict(target_id=7, target_name="t", domain={"yaw": [-4.0, 4.0], "pitch": [-2.0, 2.0]}, grid_deg=4.0)
    multi = [(-8.0, -4.0), (6.0, 4.0)]
    fixtures = {  # name: (state, kw without gazes, all_target_ids, gazes)
        "H1-multi": (h1, kw1, {7, 25, 90}, multi),
        "H1-one": (h1, kw1, {7, 25, 90}, [(6.0, 4.0)]),
        "H1-none": (h1, kw1, {7, 25, 90}, []),
        "H2-one": (h2, kw2, {7}, [(0.0, 0.0)]),
        "H3-none": (h3, kw3, {7}, []),
        "H3-multi": (h3, kw3, {7}, [(1.0, 1.0), (-3.0, 0.5), (10.0, -2.0)]),
    }
    old_i = {k: (_outcome(old_intr, s, gazes_deg=g, **kw) if old_intr else ("no-reference", "")) for k, (s, kw, t, g) in fixtures.items()}
    new_i = {k: _outcome(build_epistemic_partition, s, **kw) for k, (s, kw, t, g) in fixtures.items()}
    old_r = {k: (_outcome(old_rc, s, all_target_ids=t, gazes_deg=g, **kw) if old_rc else ("no-reference", "")) for k, (s, kw, t, g) in fixtures.items()}
    new_r = {k: _outcome(build_run_context_partition, s, all_target_ids=t, gazes_deg=g, **kw) for k, (s, kw, t, g) in fixtures.items()}
    old_h = {k: (_outcome(old_hist, s, all_target_ids=t, gazes_deg=g, **kw) if old_hist else ("no-reference", "")) for k, (s, kw, t, g) in fixtures.items()}
    new_h = {k: _outcome(build_candidate_partition, s, all_target_ids=t, gazes_deg=g, **kw) for k, (s, kw, t, g) in fixtures.items()}
    gz_p = {k: _outcome(build_gaze_context_partition, s, gazes_deg=g, **kw) for k, (s, kw, t, g) in fixtures.items()}
    old_rows = [r for k in fixtures if old_i[k][0] == "ok" for r in old_i[k][1][1]]
    gaze_vals = {k: [r.get(GAZE_FIELD) for r in old_i[k][1][1]] for k in fixtures if old_i[k][0] == "ok"}
    check("B: fixtures witness all kinds, all surface sources, edge flags, 4/8 connectivity, target-free, and no-gaze, "
          "one-gaze and multi-gaze histories with finite great-circle distances",
          {r["kind"] for r in old_rows} == set(KINDS)
          and {r.get("surface_source") for r in old_rows} >= {"mapped_and_incidental", "mapped", "incidental"}
          and {r["touches_domain_edge"] for r in old_rows} == {True, False}
          and old_i["H2-one"][0] == "ok" and len(old_i["H2-one"][1][1]) == 9
          and old_i["H3-none"][0] == "ok" and not any(r["kind"] == "TARGET_SUPPORT" for r in old_i["H3-none"][1][1])
          and all(v is None for k in ("H1-none", "H3-none") for v in gaze_vals.get(k, [0]))
          and all(type(v) is float for k in ("H1-multi", "H1-one", "H2-one", "H3-multi") for v in gaze_vals.get(k, [None]))
          and any(v > 1.0 for v in gaze_vals.get("H1-multi", [0.0])))
    for k in fixtures:
        o, n = old_i[k], new_i[k]
        both = o[0] == "ok" and n[0] == "ok" and isinstance(n[1], tuple) and len(n[1]) == 4
        check(f"B: {k} intrinsic arrays/edges/diag exact and rows = Core-13 rows minus only the gaze-distance field",
              both and _same(n[1][0], o[1][0]) and _same(n[1][2], o[1][2]) and _same(n[1][3], o[1][3])
              and _same(n[1][1], _drop(o[1][1], GAZE_FIELD)))
    bad = dict(h3, seen_any=np.zeros((3, 2), bool))
    check("B: malformed shapes raise the accepted ValueError in the Core-14 and Core-13 builders",
          _outcome(build_epistemic_partition, bad, **kw3)
          == ("ValueError", "Phase-5 state rasters do not share one chart shape")
          == (_outcome(old_intr, bad, gazes_deg=[], **kw3) if old_intr else None))
    arrays1, rows1, edges1, diag1 = new_i["H1-multi"][1] if new_i["H1-multi"][0] == "ok" else ({}, [], [], {})
    ids = {1: "target_support:0001", 2: "other_surface:0002", 3: "other_surface:0003", 4: "other_surface:0004",
           5: "other_surface:0005", 6: "unknown:0006", 7: "unknown:0007", 8: "ambiguous_boundary:0008",
           9: "target_evidence_unmapped:0009"}
    adjacency = {1: {2: 1, 8: 2, 9: 1}, 2: {1: 1, 3: 3, 7: 1, 8: 1}, 3: {2: 3, 4: 1, 5: 1, 6: 2},
                 4: {3: 1, 5: 2, 7: 2}, 5: {3: 1, 4: 2, 6: 2}, 6: {3: 2, 5: 2},
                 7: {2: 1, 4: 2, 8: 2, 9: 1}, 8: {1: 2, 2: 1, 7: 2, 9: 1}, 9: {1: 1, 7: 1, 8: 1}}
    spec = [  # code, kind, instance, cells, edge, centroid, min/median target distance (cells),
        #       seen_any, head depth, mapped, incidental, surface_source
        (1, "TARGET_SUPPORT", 7, 3, True, (-26 / 3, -14 / 3), 0.0, 0.0, 2 / 3, 1.0, 0, 0, None),
        (2, "OTHER_SURFACE", 3, 3, True, (-2 / 3, -14 / 3), 1.0, DIAG, 1 / 3, 2 / 3, 2, 1, "mapped_and_incidental"),
        (3, "OTHER_SURFACE", 12, 3, True, (14 / 3, -10 / 3), KNIGHT, 3.0, 1.0, 1.0, 3, 0, "mapped"),
        (4, "OTHER_SURFACE", 25, 2, True, (2.0, 4.0), 2 * DIAG, (2 * DIAG + KNIGHT + DIAG) / 2, 0.0, 0.5, 0, 2, "incidental"),
        (5, "OTHER_SURFACE", 40, 2, True, (6.0, 4.0), KNIGHT + DIAG, (KNIGHT + DIAG + 3 * DIAG) / 2, 1.0, 0.0, 0, 2, "incidental"),
        (6, "UNKNOWN", None, 4, True, (10.0, 0.0), 4.0, (KNIGHT + 2.0 + 2 * KNIGHT) / 2, 0.25, 0.0, 0, 0, None),
        (7, "UNKNOWN", None, 3, True, (-10 / 3, 14 / 3), KNIGHT, KNIGHT, 1 / 3, 2 / 3, 0, 0, None),
        (8, "AMBIGUOUS_BOUNDARY", None, 2, False, (-6.0, 0.0), 1.0, (1.0 + DIAG) / 2, 0.5, 1.0, 1, 0, None),
        (9, "TARGET_EVIDENCE_UNMAPPED", 7, 2, True, (-10.0, 4.0), 1.0, 1.5, 0.5, 0.5, 0, 0, None),
    ]
    expected_intr = []
    for code, kind, iid, cells, touches, cen, dmin, dmed, seen, depth, mapped, inc, source in spec:
        row = {"region_code": code, "region_id": ids[code], "kind": kind, "instance_id": iid, "cell_count": cells,
               "touches_domain_edge": touches, "centroid_yaw_deg": cen[0], "centroid_pitch_deg": cen[1],
               "min_distance_to_target_deg": dmin * 4.0, "median_distance_to_target_deg": dmed * 4.0,
               "seen_any_fraction": seen, "head_depth_fraction": depth, "mapped_cells": mapped, "incidental_cells": inc}
        if source:
            row["surface_source"] = source
        row["adjacent_regions"] = [{"region_code": n, "region_id": ids[n], "interface_edge_count": c}
                                   for n, c in sorted(adjacency[code].items())]
        row["adjacent_to_target_support"] = 1 in adjacency[code]
        expected_intr.append(row)
    check("B: H1 hand-derived intrinsic rows (no candidate, status or gaze field), edges and diag",
          _same(rows1, expected_intr, 1e-3)
          and _same(edges1, [{"region_code_a": a, "region_code_b": b, "interface_edge_count": c}
                             for a in sorted(adjacency) for b, c in sorted(adjacency[a].items()) if a < b])
          and _same(diag1, {"target_id": 7, "target_name": "fixture-target", "chart_shape_hw": [4, 6], "region_count": 9,
                            "kind_region_counts": {"AMBIGUOUS_BOUNDARY": 1, "OTHER_SURFACE": 4, "TARGET_EVIDENCE_UNMAPPED": 1,
                                                   "TARGET_SUPPORT": 1, "UNKNOWN": 2},
                            "kind_cell_counts": {"TARGET_SUPPORT": 3, "OTHER_SURFACE": 10, "UNKNOWN": 7,
                                                 "AMBIGUOUS_BOUNDARY": 2, "TARGET_EVIDENCE_UNMAPPED": 2},
                            "target_evidence_unmapped_cells": 2, "ambiguous_boundary_cells": 2, "head_depth_cells": 14,
                            "eye_ray_seen_cells": 12, "truth_used": False}))
    rows3 = new_i["H3-none"][1][1] if new_i["H3-none"][0] == "ok" else []
    check("B: H2 hand-derived connectivity and H3 target-free rows",
          new_i["H2-one"][0] == "ok" and _raster(new_i["H2-one"][1][0]["region_code"], [[1, 3, 2, 7, 9, 4], [5, 1, 8, 2, 6, 9]], np.int32)
          and len(rows3) == 4 and _raster(new_i["H3-none"][1][0]["region_code"], [[2, 1, 3], [4, 3, 3]], np.int32)
          and all(r["min_distance_to_target_deg"] is None and GAZE_FIELD not in r for r in rows3))

    # ---- C. intrinsic independence from action history
    builds = [_outcome(build_epistemic_partition, h1, **kw1) for _ in range(3)]
    views = [_outcome(annotate_gaze_context, rows1, gazes_deg=g) for g in ([], [(6.0, 4.0)], multi)]
    check("C: the intrinsic builder accepts no gaze history (a gazes_deg keyword is rejected)",
          _outcome(build_epistemic_partition, h1, gazes_deg=multi, **kw1)[0] == "TypeError")
    check("C: the same state gives identical intrinsic arrays, rows, edges and diag, with no gaze field, whatever history "
          "is applied afterwards",
          all(b[0] == "ok" and _same(b[1], new_i["H1-multi"][1]) for b in builds)
          and all(v[0] == "ok" for v in views) and _same(rows1, expected_intr, 1e-3)
          and not any(GAZE_FIELD in r for r in rows1))
    check("C: the gaze-context annotation does change with the history (live control): None / one gaze / two gazes",
          all(v[0] == "ok" for v in views)
          and [_gv(r) for r in views[0][1]] == [None] * 9
          and all(type(_gv(r)) is float for r in views[1][1] + views[2][1])
          and [_gv(r) for r in views[1][1]] != [_gv(r) for r in views[2][1]]
          and len(views[2][1]) == 9 and _same(_gv(views[2][1][4]), 0.0, 1e-5))   # the gaze on region 5's centroid (acos roundoff ~1.5e-6)

    # ---- D. gaze-context rule
    def row(code, kind, cen, extra=None):
        r = {"region_code": code, "kind": kind, "centroid_yaw_deg": cen[0], "centroid_pitch_deg": cen[1],
             "min_distance_to_target_deg": 1.0, "median_distance_to_target_deg": 2.0, "seen_any_fraction": 0.5}
        r.update(extra or {})
        return r

    gz = [(0.0, 25.0), (30.0, 0.0), (0.0, 0.0)]     # distances from (20, 10): ~24.6, ~14.1 (min, in the middle), ~22.3
    synth = [row(1, "UNKNOWN", (20.0, 10.0)), row(2, "TARGET_SUPPORT", (20.0, 10.0)), row(3, "OTHER_SURFACE", (math.nan, 10.0)),
             row(4, "AMBIGUOUS_BOUNDARY", (-5.0, -5.0)), row(5, "TARGET_EVIDENCE_UNMAPPED", (0.0, 0.0))]
    snap = copy.deepcopy(synth)
    ann = _outcome(annotate_gaze_context, synth, gazes_deg=gz)
    want_vals = [min(_great_circle((r["centroid_yaw_deg"], r["centroid_pitch_deg"]), g) for g in gz)
                 if not math.isnan(r["centroid_yaw_deg"]) else None for r in snap]
    want = [_with_after(r, "median_distance_to_target_deg", GAZE_FIELD, v) for r, v in zip(snap, want_vals)]
    check("D: the accepted rule: minimum great-circle distance from the centroid over all gazes, for every kind; "
          "a non-finite centroid gives None (Python float/None, right after median_distance_to_target_deg)",
          ann[0] == "ok" and _same(ann[1], want, 1e-9) and abs(want_vals[0] - _great_circle((20.0, 10.0), (30.0, 0.0))) < 1e-12)
    check("D: the minimum is the middle gaze (not first, last, mean, median or max); yaw/pitch order is respected",
          ann[0] == "ok" and type(_gv(ann[1][0])) is float and all(abs(_gv(ann[1][0]) - x) > 1.0 for x in (
              _great_circle((20.0, 10.0), gz[0]), _great_circle((20.0, 10.0), gz[2]),
              sum(_great_circle((20.0, 10.0), g) for g in gz) / 3, max(_great_circle((20.0, 10.0), g) for g in gz),
              min(_great_circle((20.0, 10.0), (p, y)) for y, p in gz), min(_great_circle((10.0, 20.0), g) for g in gz))))
    check("D: an empty history gives None for every row; integer gaze components are accepted",
          _same(_outcome(annotate_gaze_context, synth, gazes_deg=[]),
                ("ok", [_with_after(r, "median_distance_to_target_deg", GAZE_FIELD, None) for r in snap]))
          and _same(_outcome(annotate_gaze_context, [synth[0]], gazes_deg=[(30, 0)]),
                    ("ok", [_with_after(snap[0], "median_distance_to_target_deg", GAZE_FIELD,
                                        _great_circle((20.0, 10.0), (30.0, 0.0)))]), 1e-9))
    check("D: annotation does not mutate its inputs, returns new dicts in order, and keeps every value object",
          ann[0] == "ok" and _same(synth, snap) and len(ann[1]) == len(synth) and ann[1] is not synth
          and all(a is not s and all(a[k] is s[k] for k in s) for a, s in zip(ann[1], synth)))
    real = views[2]
    check("D: on the intrinsic H1 rows every region receives the field right after median_distance_to_target_deg",
          real[0] == "ok" and all(list(a) == list(_with_after(p, "median_distance_to_target_deg", GAZE_FIELD, None))
                                  for a, p in zip(real[1], rows1)) and len(real[1]) == 9)
    check("D: missing anchor and double annotation fail loudly; an empty partition stays empty",
          _outcome(annotate_gaze_context, [{"centroid_yaw_deg": 0.0, "centroid_pitch_deg": 0.0}], gazes_deg=[])[0] == "KeyError"
          and _outcome(annotate_gaze_context, real[1], gazes_deg=[])[0] == "ValueError"
          and _outcome(annotate_gaze_context, [], gazes_deg=gz) == ("ok", []))

    # ---- E. regazing identity
    check("E: annotate_gaze_context(NEW_INTRINSIC rows) == Core-13 intrinsic rows for every fixture and history",
          all(old_i[k][0] == "ok" and new_i[k][0] == "ok"
              and _same(_outcome(annotate_gaze_context, new_i[k][1][1], gazes_deg=g), ("ok", old_i[k][1][1]))
              for k, (s, kw, t, g) in fixtures.items()))
    check("E: build_gaze_context_partition == Core-13 build_epistemic_partition for every fixture and history",
          all(old_i[k][0] == "ok" and gz_p[k][0] == "ok" and _same(gz_p[k][1], old_i[k][1]) for k in fixtures))
    calls: dict[str, list] = {"intr": [], "ann": []}
    real_intr, real_ann = gaze_context.build_epistemic_partition, gaze_context.annotate_gaze_context

    def spy_intr(*a, **kw):
        out = real_intr(*a, **kw)
        calls["intr"].append((kw, out))
        return out

    def spy_ann(*a, **kw):
        calls["ann"].append(kw)
        return real_ann(*a, **kw)

    gaze_context.build_epistemic_partition, gaze_context.annotate_gaze_context = spy_intr, spy_ann
    try:
        w = _outcome(build_gaze_context_partition, h1, gazes_deg=multi, **kw1)
    finally:
        gaze_context.build_epistemic_partition, gaze_context.annotate_gaze_context = real_intr, real_ann
    check("E: the gaze-context wrapper builds the intrinsic partition once (without gazes), annotates once, and passes "
          "arrays, edges and diag through as the same objects",
          real_intr is build_epistemic_partition and len(calls["intr"]) == 1 and len(calls["ann"]) == 1
          and "gazes_deg" not in calls["intr"][0][0] and calls["ann"][0] == {"gazes_deg": multi}
          and w[0] == "ok" and w[1][0] is calls["intr"][0][1][0] and w[1][2] is calls["intr"][0][1][2]
          and w[1][3] is calls["intr"][0][1][3])
    check("E: build_gaze_context_partition keeps the historical Core-13 intrinsic signature (with gazes_deg)",
          old_intr is not None and str(inspect.signature(build_gaze_context_partition)) == str(inspect.signature(old_intr)))

    # ---- F. run-context composition
    check("F: build_run_context_partition == accepted Core-13 build_run_context_partition for every fixture and history",
          all(old_r[k][0] == "ok" and new_r[k][0] == "ok" and _same(new_r[k][1], old_r[k][1]) for k in fixtures))
    cnt = {"intr": 0, "gaze": 0, "gwrap": 0, "status": 0, "rcw": 0, "cand": 0}
    saved = (gaze_context.build_epistemic_partition, gaze_context.annotate_gaze_context,
             run_context.build_gaze_context_partition, run_context.annotate_reconstruction_status,
             candidate_policy.build_run_context_partition, candidate_policy.annotate_candidate_partition)

    def counting(key, fn):
        def inner(*a, **kw):
            cnt[key] += 1
            return fn(*a, **kw)
        return inner

    def install():
        (gaze_context.build_epistemic_partition, gaze_context.annotate_gaze_context,
         run_context.build_gaze_context_partition, run_context.annotate_reconstruction_status,
         candidate_policy.build_run_context_partition, candidate_policy.annotate_candidate_partition) = (
            counting("intr", saved[0]), counting("gaze", saved[1]), counting("gwrap", saved[2]),
            counting("status", saved[3]), counting("rcw", saved[4]), counting("cand", saved[5]))

    def restore():
        (gaze_context.build_epistemic_partition, gaze_context.annotate_gaze_context,
         run_context.build_gaze_context_partition, run_context.annotate_reconstruction_status,
         candidate_policy.build_run_context_partition, candidate_policy.annotate_candidate_partition) = saved

    install()
    try:
        one_rc = _outcome(build_run_context_partition, h1, all_target_ids={7, 25, 90}, gazes_deg=multi, **kw1)
    finally:
        restore()
    check("F: one run-context call = one intrinsic build, one gaze annotation, one gaze-context call, one status annotation",
          one_rc[0] == "ok" and cnt == {"intr": 1, "gaze": 1, "gwrap": 1, "status": 1, "rcw": 0, "cand": 0}
          and saved[2] is build_gaze_context_partition)
    rc_src = (ROOT / CP / "run_context.py").read_text(encoding="utf-8")
    rc_old, rc_new = (_top(core13_rc) if core13_rc else {}), _top(rc_src)

    def norm(node, old, new):
        return ast.dump(_strip_docstrings(node)).replace(new, old)

    check("F: run_context imports gaze_context (not the intrinsic builder); _insert_after and annotate_reconstruction_status "
          "are unchanged from Core 13; build_run_context_partition differs only in the called builder; same signature",
          _imports(rc_src).get("build_gaze_context_partition") == "fov3d.experiments.classroom_partition.gaze_context.build_gaze_context_partition"
          and "build_epistemic_partition" not in _imports(rc_src) and not hasattr(run_context, "build_epistemic_partition")
          and bool(rc_old) and all(n in rc_old and n in rc_new and _text(core13_rc, rc_old[n]) == _text(rc_src, rc_new[n])
                                   for n in ("_insert_after", "annotate_reconstruction_status"))
          and list(rc_new) == list(rc_old) and "build_run_context_partition" in rc_new
          and norm(rc_old["build_run_context_partition"], "build_epistemic_partition", "build_epistemic_partition")
          == norm(rc_new["build_run_context_partition"], "build_epistemic_partition", "build_gaze_context_partition")
          and old_rc is not None and str(inspect.signature(build_run_context_partition)) == str(inspect.signature(old_rc)))

    # ---- G. candidate composition
    check("G: candidate_policy.py is byte-identical to accepted Core 13",
          bool(core13_pol) and (ROOT / CP / "candidate_policy.py").read_text(encoding="utf-8") == core13_pol)
    check("G: build_candidate_partition == accepted Core-13 build_candidate_partition for every fixture and history",
          all(old_h[k][0] == "ok" and new_h[k][0] == "ok" and _same(new_h[k][1], old_h[k][1]) for k in fixtures))
    for key in cnt:
        cnt[key] = 0
    install()
    try:
        one_h = _outcome(build_candidate_partition, h1, all_target_ids={7, 25, 90}, gazes_deg=multi, **kw1)
    finally:
        restore()
    check("G: one candidate call = one intrinsic build, gaze annotation, gaze-context call, status annotation, run-context "
          "call and candidate annotation",
          one_h[0] == "ok" and cnt == {"intr": 1, "gaze": 1, "gwrap": 1, "status": 1, "rcw": 1, "cand": 1}
          and old_h["H1-multi"][0] == "ok" and _same(one_h[1], old_h["H1-multi"][1]))

    # ---- H. historical gaze provenance and producer wiring
    from fov3d.experiments.classroom_partition import benchmark
    via_bench = _outcome(getattr(benchmark, "build_epistemic_partition", lambda *a, **k: None), h1,
                         all_target_ids={7, 25, 90}, gazes_deg=multi, **kw1)
    check("H: benchmark.build_epistemic_partition is the candidate wrapper and returns the accepted Core-13 view",
          getattr(benchmark, "build_epistemic_partition", None) is build_candidate_partition
          and getattr(benchmark, "CANDIDATE_KINDS", None) is candidate_policy.CANDIDATE_KINDS
          and old_h["H1-multi"][0] == "ok" and via_bench[0] == "ok" and _same(via_bench[1], old_h["H1-multi"][1]))
    check("H: the four historical producers and the Phase-5 incidental module are byte-identical to Core 13",
          all((ROOT / CP / f"{m}.py").read_text(encoding="utf-8") == _git_show(f"{CP}{m}.py") != ""
              for m in PRODUCERS + ("incidental",)))
    prov_ok = True
    for mod, (name, iterable, n_calls) in GAZE_SOURCES.items():
        tree = ast.parse((ROOT / CP / f"{mod}.py").read_text(encoding="utf-8"))
        kws = [ast.unparse(k.value) for c in ast.walk(tree) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
               and c.func.id == "build_candidate_partition" for k in c.keywords if k.arg == "gazes_deg"]
        comps = [a.value for a in ast.walk(tree) if isinstance(a, ast.Assign) and len(a.targets) == 1
                 and isinstance(a.targets[0], ast.Name) and a.targets[0].id == name and isinstance(a.value, ast.ListComp)]
        prov_ok &= kws == [name] * n_calls and len(comps) == 1
        prov_ok &= bool(comps) and ast.unparse(comps[0].generators[0].iter) == iterable
        prov_ok &= bool(comps) and ast.unparse(comps[0].elt) == "tuple(map(float, r['gaze_deg']))"
        prov_ok &= bool(comps) and [ast.unparse(i) for i in comps[0].generators[0].ifs] == ["'gaze_deg' in r"]
        m = importlib.import_module(f"fov3d.experiments.classroom_partition.{mod}")
        prov_ok &= getattr(m, "build_candidate_partition", None) is build_candidate_partition
        prov_ok &= not any(ast.unparse(k.value) == "global_gazes" for c in ast.walk(tree) if isinstance(c, ast.Call) for k in c.keywords)
    check("H: target-local gaze provenance: Phase 6 the trajectory gazes, Phase 7 current_target_gazes (both arms), "
          "Phase 8 the current prefix (both sites), Phase 8b the retained prefix; global_gazes is never passed", prov_ok)
    metric_mods, gaze_field_mods = set(), set()
    for path in sorted((ROOT / "fov3d").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docs_p = _docstring_ids(tree)
        if any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "_angular_distance_deg" for c in ast.walk(tree)):
            metric_mods.add(path.name)
        if any(isinstance(n, ast.Constant) and id(n) not in docs_p and n.value == GAZE_FIELD for n in ast.walk(tree)):
            gaze_field_mods.add(path.name)
    check("H: no duplicate gaze metric: only gaze_context calls _angular_distance_deg and names the gaze field",
          metric_mods == {"gaze_context.py"} and gaze_field_mods == {"gaze_context.py"})

    # ---- I. Phase 8b
    from fov3d.experiments.classroom_partition import challenge_suite
    kw01 = dict(kw1, domain={"yaw": [-0.25, 0.25], "pitch": [-0.15, 0.15]}, grid_deg=0.1)
    nh01 = _outcome(build_candidate_partition, h1, all_target_ids={7, 25, 90}, gazes_deg=[(0.1, 0.05)], **kw01)
    oh01 = _outcome(old_hist, h1, all_target_ids={7, 25, 90}, gazes_deg=[(0.1, 0.05)], **kw01) if old_hist else ("no-reference", "")
    ref_new = _outcome(challenge_suite.refine_integrated_partition, nh01[1][0], nh01[1][1], grid_deg=0.1) if nh01[0] == "ok" else nh01
    ref_old = _outcome(challenge_suite.refine_integrated_partition, oh01[1][0], oh01[1][1], grid_deg=0.1) if oh01[0] == "ok" else oh01
    base = nh01[1][1] if nh01[0] == "ok" else []
    check("I: the Phase-8b base historical rows carry the gaze-distance field (all rows, finite)",
          len(base) == 9 and all(type(r.get(GAZE_FIELD)) is float for r in base))
    by_code = {r["region_code"]: r for r in base}
    refined = ref_new[1][1] if ref_new[0] == "ok" else []
    refined_os = [r for r in refined if r["kind"] == "OTHER_SURFACE"]
    check("I: refinement on the Core-14 view equals that on the Core-13 view; refined rows do NOT carry the gaze field, "
          "while surface_source and reconstruction_status still propagate",
          ref_new[0] == "ok" and ref_old[0] == "ok" and _same(ref_new[1], ref_old[1]) and len(refined) > 0
          and not any(GAZE_FIELD in r for r in refined) and len(refined_os) == 4
          and all(r.get("reconstruction_status", "<missing>") == by_code.get(r.get("origin_region_code"), {}).get("reconstruction_status")
                  and r.get("surface_source", "<missing>") == by_code.get(r.get("origin_region_code"), {}).get("surface_source")
                  for r in refined_os))
    cs_old = _top(_git_show(f"{CP}challenge_suite.py")) if core13_part else {}
    cs_new = _top((ROOT / CP / "challenge_suite.py").read_text(encoding="utf-8"))
    check("I: _component_rows and refine_integrated_partition are AST-identical to Core 13",
          all(n in cs_old and n in cs_new and ast.dump(cs_old[n]) == ast.dump(cs_new[n])
              for n in ("_component_rows", "refine_integrated_partition")))

    def rows8b(kind: str, cells: int, original_row=None):
        mask = np.zeros((6, 6), bool)
        mask.flat[:cells] = True
        res = _outcome(challenge_suite._component_rows, mask, connectivity=4, kind=kind, original_code=None,
                       shell_index=None, next_code=1, refined_code=np.zeros((6, 6), np.int32), original_row=original_row)
        return [(r["candidate_raw"], r["eligible_candidate"], r.get("reconstruction_status"), GAZE_FIELD in r)
                for r in res[1][1]] if res[0] == "ok" else res

    origin = {"instance_id": 3, "surface_source": "mapped", "reconstruction_status": "mapped_now", "mapped_cells": 5,
              "incidental_cells": 0, "touches_domain_edge": False, "seen_any_fraction": 1.0, "head_depth_fraction": 1.0,
              GAZE_FIELD: 0.5}
    cases = [("UNKNOWN", 30, None), ("UNKNOWN", 3, None), ("OTHER_SURFACE", 30, origin),
             ("OTHER_SURFACE", 24, dict(origin, **{GAZE_FIELD: 99.0})), ("TARGET_SUPPORT", 30, None),
             ("AMBIGUOUS_BOUNDARY", 30, None), ("TARGET_EVIDENCE_UNMAPPED", 30, None)]
    before = [rows8b(*c) for c in cases]
    gz_saved = gaze_context.annotate_gaze_context
    gaze_context.annotate_gaze_context = lambda rows, *, gazes_deg: [
        _with_after(r, "median_distance_to_target_deg", GAZE_FIELD, 0.0) for r in rows]
    try:
        during = [rows8b(*c) for c in cases]
        control = _outcome(build_candidate_partition, h1, all_target_ids={7, 25, 90}, gazes_deg=multi, **kw1)
    finally:
        gaze_context.annotate_gaze_context = gz_saved
    check("I: Phase-8b candidate_raw/eligible_candidate known answers (MIN_ELIGIBLE_CELLS 25), status propagation, and "
          "no gaze-field propagation from the origin row",
          before == [[(True, True, None, False)], [(True, False, None, False)], [(True, True, "mapped_now", False)],
                     [(True, False, "mapped_now", False)], [(False, False, None, False)], [(False, False, None, False)],
                     [(False, False, None, False)]])
    check("I: Phase-8b interpretation is independent of the gaze context (live control: the historical view changes)",
          during == before and control[0] == "ok" and new_h["H1-multi"][0] == "ok"
          and all(r.get(GAZE_FIELD) == 0.0 for r in control[1][1])
          and any(r.get(GAZE_FIELD) != 0.0 for r in new_h["H1-multi"][1][1]))

    # ---- J. package footprints (fresh processes) and dependencies
    check("J: fov3d/epistemic/__init__.py is unchanged from accepted Core 13",
          bool(core13_part) and (ROOT / "fov3d" / "epistemic" / "__init__.py").read_text(encoding="utf-8")
          == _git_show("fov3d/epistemic/__init__.py"))
    gzm = "fov3d.experiments.classroom_partition.gaze_context"
    rcm = "fov3d.experiments.classroom_partition.run_context"
    pol = "fov3d.experiments.classroom_partition.candidate_policy"
    probe = ("mods = sorted(sys.modules)\n"
             "print(json.dumps({'cv2': 'cv2' in sys.modules, 'bpy': 'bpy' in sys.modules,\n"
             "  'fov3d': [m for m in mods if m.startswith('fov3d')]}))\n")
    pkg = ["fov3d", "fov3d.epistemic", "fov3d.epistemic.partition", "fov3d.experiments",
           "fov3d.experiments.classroom_partition", "fov3d.experiments.classroom_partition.lift",
           "fov3d.geometry", "fov3d.geometry.head_chart", "fov3d.reconstruction", "fov3d.reconstruction.association",
           "fov3d.scene", "fov3d.scene.model", "fov3d.scene.sphere"]
    check("J: fresh bare import fov3d.epistemic stays lightweight",
          _fresh("import fov3d.epistemic\n" + probe) == {"cv2": False, "bpy": False, "fov3d": ["fov3d", "fov3d.epistemic"]})
    check("J: fresh import fov3d.epistemic.partition: no experiment, gaze_context, run_context or candidate_policy",
          _fresh("import fov3d.epistemic.partition\n" + probe) == {
              "cv2": True, "bpy": False,
              "fov3d": ["fov3d", "fov3d.epistemic", "fov3d.epistemic.partition", "fov3d.geometry", "fov3d.geometry.head_chart"]})
    check("J: fresh import gaze_context: the intrinsic partition only (no run_context, candidate_policy, benchmark, "
          "evaluator, stereo, renderer or bpy)",
          _fresh(f"import {gzm}\n" + probe) == {"cv2": True, "bpy": False, "fov3d": sorted(pkg + [gzm])})
    check("J: fresh import run_context adds gaze_context; candidate_policy adds run_context; neither loads a benchmark",
          _fresh(f"import {rcm}\n" + probe) == {"cv2": True, "bpy": False, "fov3d": sorted(pkg + [gzm, rcm])}
          and _fresh(f"import {pol}\n" + probe) == {"cv2": True, "bpy": False, "fov3d": sorted(pkg + [gzm, rcm, pol])})
    gz_src = (ROOT / CP / "gaze_context.py").read_text(encoding="utf-8")
    orders = [
        _fresh(f"import {gzm} as g\nimport {rcm} as r\nimport {pol} as c\nimport fov3d.experiments.classroom_partition.benchmark as b\n"
               "print(json.dumps(b.build_epistemic_partition is c.build_candidate_partition and r.build_gaze_context_partition is g.build_gaze_context_partition))\n"),
        _fresh(f"import fov3d.experiments.classroom_partition.benchmark as b\nimport {pol} as c\nimport {rcm} as r\nimport {gzm} as g\n"
               "print(json.dumps(r.build_gaze_context_partition is g.build_gaze_context_partition and c.build_run_context_partition is r.build_run_context_partition))\n"),
    ]
    check("J: static imports: gaze_context -> typing, numpy, epistemic.partition; run_context -> typing, numpy, gaze_context; "
          "candidate_policy -> typing, numpy, run_context; no import cycle in either order",
          _all_import_modules(gz_src) == {"__future__", "typing", "numpy", "fov3d.epistemic.partition"}
          and _imports(gz_src).get("_angular_distance_deg") == "fov3d.epistemic.partition._angular_distance_deg"
          and _all_import_modules(rc_src) == {"__future__", "typing", "numpy", gzm}
          and _all_import_modules((ROOT / CP / "candidate_policy.py").read_text(encoding="utf-8")) == {"__future__", "typing", "numpy", rcm}
          and orders == [True, True])

    # ---- K. seeded random differential against accepted Core 13
    rng = np.random.default_rng(20261001)
    n_states = 300
    agree = 0
    hist = {"empty": 0, "one": 0, "multi": 0}
    finite_rows = 0
    ctl = {"position": 0, "max": 0, "zero": 0}
    ctl_expected = {"position": 0, "max": 0, "zero": 0}
    for _ in range(n_states):
        state, kw, targets, gazes = _random_state(rng)
        oi = _outcome(old_intr, state, gazes_deg=gazes, **kw) if old_intr else ("no-reference", "")
        ni = _outcome(build_epistemic_partition, state, **kw)
        orc = _outcome(old_rc, state, all_target_ids=targets, gazes_deg=gazes, **kw) if old_rc else ("no-reference", "")
        nrc = _outcome(build_run_context_partition, state, all_target_ids=targets, gazes_deg=gazes, **kw)
        oh = _outcome(old_hist, state, all_target_ids=targets, gazes_deg=gazes, **kw) if old_hist else ("no-reference", "")
        nh = _outcome(build_candidate_partition, state, all_target_ids=targets, gazes_deg=gazes, **kw)
        gp = _outcome(build_gaze_context_partition, state, gazes_deg=gazes, **kw)
        if not all(x[0] == "ok" for x in (oi, ni, orc, nrc, oh, nh, gp)):
            continue
        rg = _outcome(annotate_gaze_context, ni[1][1], gazes_deg=gazes)
        agree += (_same(ni[1][0], oi[1][0]) and _same(ni[1][2], oi[1][2]) and _same(ni[1][3], oi[1][3])
                  and _same(ni[1][1], _drop(oi[1][1], GAZE_FIELD)) and rg[0] == "ok" and _same(rg[1], oi[1][1])
                  and _same(gp[1], oi[1]) and _same(nrc[1], orc[1]) and _same(nh[1], oh[1]))
        hist["empty" if not gazes else "one" if len(gazes) == 1 else "multi"] += 1
        finite_rows += sum(r[GAZE_FIELD] is not None for r in oi[1][1])
        # non-equivalent controls must be detected by the same comparator
        moved = [dict([(k, v) for k, v in r.items() if k != GAZE_FIELD] + [(GAZE_FIELD, r[GAZE_FIELD])]) for r in oi[1][1]]
        ctl_expected["position"] += bool(oi[1][1])
        ctl["position"] += bool(oi[1][1]) and not _same(moved, oi[1][1])
        maxed = [dict(r, **{GAZE_FIELD: float(max(_angular_distance_deg((r["centroid_yaw_deg"], r["centroid_pitch_deg"]), g) for g in gazes))})
                 if r[GAZE_FIELD] is not None else r for r in oi[1][1]]
        differs = len(gazes) > 1 and any(abs(a[GAZE_FIELD] - b[GAZE_FIELD]) > 0 for a, b in zip(maxed, oi[1][1]) if b[GAZE_FIELD] is not None)
        ctl_expected["max"] += differs
        ctl["max"] += differs and not _same(maxed, oi[1][1])
        zeroed = [dict(r, **{GAZE_FIELD: 0.0}) if r[GAZE_FIELD] is None else r for r in oi[1][1]]
        ctl_expected["zero"] += not gazes and bool(oi[1][1])
        ctl["zero"] += (not gazes and bool(oi[1][1])) and not _same(zeroed, oi[1][1])
    check(f"K: {n_states} random states: all eight invariants hold (intrinsic projection, regazing, gaze-context, "
          "run-context and historical identity; type-strict)", agree == n_states)
    check("K: empty, one-gaze and multi-gaze histories occur repeatedly (>= 30 each), with >= 500 finite gaze distances",
          min(hist.values()) >= 30 and finite_rows >= 500)
    check("K: controls are detected wherever they apply: field moved to the end, max instead of min, 0.0 instead of None",
          ctl == ctl_expected and min(ctl_expected.values()) > 0)

    print(f"[conceptual-core14-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
