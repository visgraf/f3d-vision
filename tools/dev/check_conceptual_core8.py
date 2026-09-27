#!/usr/bin/env python3
"""Fail-capable checks for Conceptual Core 8 graph/raster state-code consistency."""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fov3d.scene.state_validation as state_validation
from fov3d.scene.model import ObjectHypothesis, PartitionRegion, RegionKind, ScenePartitionGraph
from fov3d.scene.state_validation import attach_state_region_codes

PREFIX = "graph/raster region-code mismatch: "


def _graph(codes: dict[str, object], *, base_object_id: str | None = None, missing: tuple[str, ...] = ()) -> ScenePartitionGraph:
    """Regions obj:7:cNNN (object 7) plus one base region; codes keyed by region id."""
    regions: dict[str, PartitionRegion] = {}
    obj_rids: list[str] = []
    for rid, code in codes.items():
        attrs = {} if rid in missing else {"state_region_code": code}
        if rid.startswith("base"):
            regions[rid] = PartitionRegion(rid, RegionKind.BASE, object_id=base_object_id, attributes=attrs)
        else:
            regions[rid] = PartitionRegion(rid, RegionKind.OBJECT_COMPONENT, object_id="7", attributes=attrs)
            obj_rids.append(rid)
    objects = {"7": ObjectHypothesis("7", tuple(obj_rids))} if obj_rids else {}
    return ScenePartitionGraph(regions=regions, objects=objects)


def _snapshot(graph: ScenePartitionGraph, raster: np.ndarray) -> tuple:
    return (
        list(graph.regions),
        [(id(r), r.region_id, r.kind, r.object_id, dict(r.attributes)) for r in graph.regions.values()],
        {k: tuple(v.region_ids) for k, v in graph.objects.items()},
        raster.dtype.str, raster.shape, raster.tobytes(),
    )


def _call(graph: ScenePartitionGraph, raster: np.ndarray):
    try:
        return "ok", attach_state_region_codes(graph, raster)
    except Exception as exc:  # noqa: BLE001 - the exception itself is the observation
        return type(exc).__name__, str(exc)


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
            print(f"[conceptual-core8-check] PASS {name}")
        else:
            failed += 1
            print(f"[conceptual-core8-check] FAIL {name}")

    raster = np.array([[1, 1, 2], [3, 3, 2]], np.int32)

    # 1 valid match (with a base region) -> the same graph object.
    g = _graph({"obj:7:c001": 1, "obj:7:c002": 2, "base:c001": 3})
    before = _snapshot(g, raster)
    status, out = _call(g, raster)
    check("valid match returns the same graph object", status == "ok" and out is g)
    check("no mutation after success", _snapshot(g, raster) == before)

    # 2 graph extra code; 3 raster extra code (int32 raster values are printed as Python ints).
    ge = _graph({"obj:7:c001": 1, "obj:7:c002": 2, "base:c001": 3, "obj:7:c009": 9})
    before_ge = _snapshot(ge, raster)
    check("graph extra code: exact RuntimeError diagnostic",
          _call(ge, raster) == ("RuntimeError", PREFIX + "graph=[1, 2, 3, 9] raster=[1, 2, 3]"))
    check("no mutation after failure", _snapshot(ge, raster) == before_ge)
    raster_extra = np.array([[4, 1, 2], [3, 3, 2]], np.int32)
    check("raster extra code: exact RuntimeError diagnostic",
          _call(g, raster_extra) == ("RuntimeError", PREFIX + "graph=[1, 2, 3] raster=[1, 2, 3, 4]"))

    # 4 missing attribute contributes the -1 sentinel.
    gm = _graph({"obj:7:c001": 1, "obj:7:c002": 2, "base:c001": 3}, missing=("obj:7:c002",))
    check("missing attribute: sentinel -1 in the exact diagnostic",
          _call(gm, raster) == ("RuntimeError", PREFIX + "graph=[-1, 1, 3] raster=[1, 2, 3]"))

    # 5 -1 in graph codes fails even when the raster also contains -1 (explicit and missing).
    raster_neg = np.array([[-1, 2], [3, 3]], np.int32)
    g_explicit = _graph({"obj:7:c001": -1, "obj:7:c002": 2, "base:c001": 3})
    g_missing = _graph({"obj:7:c001": 0, "obj:7:c002": 2, "base:c001": 3}, missing=("obj:7:c001",))
    check("sentinel -1 fails even when the raster contains -1",
          _call(g_explicit, raster_neg) == ("RuntimeError", PREFIX + "graph=[-1, 2, 3] raster=[-1, 2, 3]")
          and _call(g_missing, raster_neg) == ("RuntimeError", PREFIX + "graph=[-1, 2, 3] raster=[-1, 2, 3]"))

    # 6 Python int(...) on both sides: int(2.7) == 2, int(3.2) == 3, int("2") == 2, int(3.9) == 3.
    float_raster = np.array([[2.7, 3.2], [3.2, 2.7]])
    g_int = _graph({"obj:7:c001": "2", "base:c001": 3.9})
    check("int() conversion of raster values and graph attributes",
          _call(g_int, float_raster)[0] == "ok"
          and _call(_graph({"obj:7:c001": "2", "base:c001": 4.9}), float_raster)
          == ("RuntimeError", PREFIX + "graph=[2, 4] raster=[2, 3]"))

    # 7 set semantics: repeated raster occurrences do not matter.
    check("set semantics: repeated raster values",
          _call(g, np.array([1, 1, 1, 2, 2, 3, 3, 3, 3], np.int32))[0] == "ok")

    # 8 accepted duplicate graph codes: two valid regions share code 2.
    g_dup = _graph({"obj:7:c001": 1, "obj:7:c002": 2, "obj:7:c003": 2, "base:c001": 3})
    g_dup.validate()
    status, out = _call(g_dup, raster)
    check("accepted: duplicate graph codes are not rejected when the sets match",
          status == "ok" and out is g_dup)

    # 9 error precedence: code-set mismatch AND an invalid graph -> the code-set error first.
    g_bad_mismatch = _graph({"obj:7:c001": 1, "obj:7:c002": 2, "base:c001": 3, "obj:7:c009": 9},
                            base_object_id="7")
    check("code-set RuntimeError precedes graph.validate()",
          _call(g_bad_mismatch, raster) == ("RuntimeError", PREFIX + "graph=[1, 2, 3, 9] raster=[1, 2, 3]"))

    # 10 matching sets but an invalid graph -> graph.validate()'s own exception propagates.
    g_bad = _graph({"obj:7:c001": 1, "obj:7:c002": 2, "base:c001": 3}, base_object_id="7")
    try:
        g_bad.validate()
        expected_validate = ("ok", None)
    except Exception as exc:  # noqa: BLE001
        expected_validate = (type(exc).__name__, str(exc))
    check("graph.validate() runs on a match and its exception propagates unchanged",
          expected_validate == ("ValueError", "base region base:c001 cannot carry object_id")
          and _call(g_bad, raster) == expected_validate)

    # 12 no shape/dimensionality contract: 1-D, 3-D and column rasters are accepted.
    check("raster shape and dimensionality are not validated",
          all(_call(g, r)[0] == "ok" for r in (
              np.array([3, 2, 1], np.int32),
              np.array([[[1], [2]], [[3], [3]]], np.int32),
              np.array([[1], [2], [3]], np.int64),
          )))

    # 13 empty graph + empty raster: exactly what ScenePartitionGraph.validate() allows.
    g_empty = ScenePartitionGraph()
    g_empty.validate()
    status, out = _call(g_empty, np.zeros((0,), np.int32))
    check("empty graph and empty raster return the same graph", status == "ok" and out is g_empty)

    # ---- compatibility, duplication, dependencies, footprints
    from fov3d.experiments.classroom_partition import joint
    check("joint compatibility identity",
          joint.attach_state_region_codes is state_validation.attach_state_region_codes)
    joint_path = ROOT / "fov3d" / "experiments" / "classroom_partition" / "joint.py"
    joint_defs = {n.name for n in ast.parse(joint_path.read_text(encoding="utf-8")).body
                  if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    check("joint contains no duplicate definition", "attach_state_region_codes" not in joint_defs)

    sv_imports = set()
    for node in ast.walk(ast.parse((ROOT / "fov3d" / "scene" / "state_validation.py").read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            sv_imports.add(("." * node.level) + (node.module or ""))
        elif isinstance(node, ast.Import):
            sv_imports.update(a.name for a in node.names)
    check("state_validation imports only numpy and scene.model (no fov3d.experiments)",
          sv_imports <= {"__future__", "numpy", ".model", "fov3d.scene.model"})

    p3 = ast.parse((ROOT / "tools" / "dev" / "check_partition_graph3.py").read_text(encoding="utf-8"))
    p3_via_joint = any(isinstance(n, ast.ImportFrom) and n.module == "fov3d.experiments.classroom_partition.joint"
                       and "attach_state_region_codes" in {a.name for a in n.names} for n in ast.walk(p3))
    p3_calls = any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "attach_state_region_codes"
                   for n in ast.walk(p3))
    check("Phase-3 checker still imports and calls the function through joint", p3_via_joint and p3_calls)

    names = ["cv2", "fov3d.scene.partition", "fov3d.scene.boundaries", "fov3d.scene.corridors",
             "fov3d.scene.lineage", "fov3d.scene.state_validation"]
    bare = _fresh(f"import fov3d.scene\nprint(json.dumps({{k: k in sys.modules for k in {names!r}}}))\n")
    check("fresh bare import fov3d.scene keeps every footprint invariant (no state_validation)",
          len(bare) == len(names) and not any(bare.values()))
    direct = _fresh(f"import fov3d.scene.state_validation\nprint(json.dumps({{k: k in sys.modules for k in {names[:5]!r}}}))\n")
    check("fresh import fov3d.scene.state_validation is NumPy-only",
          len(direct) == 5 and not any(direct.values()))

    print(f"[conceptual-core8-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
