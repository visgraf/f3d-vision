#!/usr/bin/env python3
"""Fail-capable checks for Conceptual Core 6 gap-corridor extraction."""
from __future__ import annotations

import ast
import inspect
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fov3d.scene.corridors as corridors_module
from fov3d.geometry.head_chart import head_unit_from_angles
from fov3d.scene.corridors import (
    _component_boundary,
    _line_cells,
    corridors_for_object,
    gap_corridor,
)
from fov3d.scene.model import ObjectHypothesis, PartitionRegion, RegionKind, ScenePartitionGraph

MOVED = ("_component_boundary", "_line_cells", "gap_corridor", "corridors_for_object")
SEMANTICS = "closest-boundary straight local bridge; descriptive only, not a policy or continuity claim"
RESULT_KEYS = [
    "object_id", "region_a", "region_b", "closest_endpoint_yx", "endpoint_gap_deg",
    "corridor_cell_count_interior", "base_cells", "same_object_cells", "other_object_cells",
    "other_object_counts", "seen_cells", "unseen_cells", "seen_fraction", "unseen_fraction",
    "corridor_yx", "semantics",
]


def _imports_experiment(path: Path) -> bool:
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("fov3d.experiments"):
            return True
        if isinstance(node, ast.Import) and any(a.name.startswith("fov3d.experiments") for a in node.names):
            return True
    return False


def _fresh(body: str) -> dict:
    code = f"import json, sys\nsys.path.insert(0, {str(ROOT)!r})\n{body}"
    proc = subprocess.run([sys.executable, "-I", "-c", code], cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        return {}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {}


def _cells(mask: np.ndarray) -> list[list[int]]:
    return np.argwhere(mask).tolist()


def _region(rid: str, code: int, kind: RegionKind = RegionKind.OBJECT_COMPONENT, oid: str | None = None) -> PartitionRegion:
    return PartitionRegion(rid, kind, object_id=oid, attributes={"state_region_code": code})


def main() -> int:
    checked = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal checked, failed
        checked += 1
        if condition:
            print(f"[conceptual-core6-check] PASS {name}")
        else:
            failed += 1
            print(f"[conceptual-core6-check] FAIL {name}")

    # ---- _component_boundary: 3x3 all-ones erosion, zero border.
    single = np.zeros((5, 5), bool)
    single[2, 2] = True
    b_single = _component_boundary(single)
    check("component boundary: single cell", b_single.dtype == np.bool_ and _cells(b_single) == [[2, 2]])

    block = np.zeros((7, 7), bool)
    block[2:5, 2:5] = True
    expected_block = block.copy()
    expected_block[3, 3] = False
    check("component boundary: solid block keeps only the ring",
          np.array_equal(_component_boundary(block), expected_block))

    edge = np.ones((4, 4), bool)
    expected_edge = edge.copy()
    expected_edge[1:3, 1:3] = False
    check("component boundary: edge-touching block (zero border erodes the frame)",
          np.array_equal(_component_boundary(edge), expected_edge))

    plus = np.zeros((5, 5), bool)
    plus[2, 1:4] = True
    plus[1:4, 2] = True
    check("component boundary: plus shape (all-ones kernel erodes the centre)",
          np.array_equal(_component_boundary(plus), plus))

    # ---- _line_cells: n = max(|dy|, |dx|) + 1, linspace, rint (half to even), int32, (y, x).
    def line(*a: int) -> list[list[int]]:
        return _line_cells(*a).tolist()

    check("line: horizontal", line(2, 1, 2, 5) == [[2, 1], [2, 2], [2, 3], [2, 4], [2, 5]])
    check("line: vertical", line(1, 3, 4, 3) == [[1, 3], [2, 3], [3, 3], [4, 3]])
    check("line: diagonal", line(0, 0, 3, 3) == [[0, 0], [1, 1], [2, 2], [3, 3]])
    shallow = _line_cells(0, 0, 1, 4)
    check("line: shallow slope (rint(0.5) = 0)",
          shallow.dtype == np.int32 and shallow.shape == (5, 2)
          and shallow.tolist() == [[0, 0], [0, 1], [0, 2], [1, 3], [1, 4]])
    check("line: steep slope", line(0, 0, 4, 1) == [[0, 0], [1, 0], [2, 0], [3, 1], [4, 1]])
    check("line: reversed endpoints", line(1, 4, 0, 0) == [[1, 4], [1, 3], [0, 2], [0, 1], [0, 0]])
    one = _line_cells(3, 2, 3, 2)
    check("line: one point", one.dtype == np.int32 and one.shape == (1, 2) and one.tolist() == [[3, 2]])

    # ---- gap_corridor fixture (4 x 12).  Object 7: A = code 1 (cols 1-2), B = code 2
    # (cols 9-10), middle cell code 5.  Objects 12 (code 4) and 9 (codes 6, 7) lie between.
    rc = np.full((4, 12), 3, np.int32)
    rc[1:3, 1:3] = 1
    rc[1:3, 9:11] = 2
    rc[1, 3:9] = [3, 4, 6, 5, 7, 3]
    owner = np.zeros((4, 12), np.int32)
    owner[1:3, 1:3] = 7
    owner[1:3, 9:11] = 7
    owner[1, 3:9] = [0, 12, 9, 7, 9, 0]
    regions = {  # deliberately not in code order
        "obj:7:c002": _region("obj:7:c002", 2, oid="7"),
        "base:c001": _region("base:c001", 3, RegionKind.BASE),
        "obj:9:c001": _region("obj:9:c001", 6, oid="9"),
        "obj:7:c001": _region("obj:7:c001", 1, oid="7"),
        "obj:12:c001": _region("obj:12:c001", 4, oid="12"),
        "obj:7:c003": _region("obj:7:c003", 5, oid="7"),
        "obj:9:c002": _region("obj:9:c002", 7, oid="9"),
    }
    objects = {
        "7": ObjectHypothesis("7", ("obj:7:c002", "obj:7:c001", "obj:7:c003")),
        "9": ObjectHypothesis("9", ("obj:9:c001", "obj:9:c002")),
        "12": ObjectHypothesis("12", ("obj:12:c001",)),
    }
    graph = ScenePartitionGraph(regions=regions, objects=objects)
    state = {"region_code": rc, "owner_instance": owner}
    seen = np.zeros((4, 12), bool)
    seen[0, :] = True              # off-line cells: must not count
    seen[1, 2] = seen[1, 9] = True  # endpoints: must not count
    seen[1, 3] = seen[1, 5] = True  # interior: seen at cols 3 and 5
    domain = {"yaw": [-5.0, 5.0], "pitch": [-2.0, 2.0]}

    r = gap_corridor(graph, state, "obj:7:c001", "obj:7:c002", 7, seen, domain, 1.0)
    check("corridor result keys and order", list(r) == RESULT_KEYS)
    # A boundary (1,1),(1,2),(2,1),(2,2); (1,2) and (2,2) tie at distance 7 -> first wins.
    check("corridor closest endpoint pair (first argmin on a tie)",
          r["closest_endpoint_yx"] == [[1, 2], [1, 9]])
    check("corridor_yx exact", r["corridor_yx"] == [[1, c] for c in range(2, 10)]
          and all(type(v) is int for p in r["corridor_yx"] for v in p))
    dirs = head_unit_from_angles(np.array([-3.0, 4.0]), np.array([-1.0, -1.0]))
    expected_gap = float(np.degrees(np.arccos(float(np.clip(np.dot(dirs[0], dirs[1]), -1.0, 1.0)))))
    check("endpoint_gap_deg exact (yaw from x, pitch from y)",
          type(r["endpoint_gap_deg"]) is float and r["endpoint_gap_deg"] == expected_gap
          and 6.9 < r["endpoint_gap_deg"] < 7.0)
    check("interior count excludes endpoints", r["corridor_cell_count_interior"] == 6)
    check("owner composition: base/same/other",
          r["base_cells"] == 2 and r["same_object_cells"] == 1 and r["other_object_cells"] == 3)
    check("other_object_counts string-keyed in numeric id order",
          list(r["other_object_counts"].items()) == [("9", 2), ("12", 1)])
    check("seen composition over interior only",
          r["seen_cells"] == 2 and r["unseen_cells"] == 4
          and r["seen_fraction"] == 2 / 6 and r["unseen_fraction"] == 4 / 6)
    check("identity fields and semantics string",
          r["object_id"] == "7" and r["region_a"] == "obj:7:c001" and r["region_b"] == "obj:7:c002"
          and r["semantics"] == SEMANTICS)

    rev = gap_corridor(graph, state, "obj:7:c002", "obj:7:c001", 7, seen, domain, 1.0)
    check("reversed query keeps query-order endpoints",
          rev["closest_endpoint_yx"] == [[1, 9], [1, 2]]
          and rev["corridor_yx"] == [[1, c] for c in range(9, 1, -1)])

    rc0 = np.array([[1, 2]], np.int32)
    g0 = ScenePartitionGraph(regions={"obj:7:c001": _region("obj:7:c001", 1, oid="7"),
                                      "obj:7:c002": _region("obj:7:c002", 2, oid="7")})
    z = gap_corridor(g0, {"region_code": rc0, "owner_instance": np.array([[7, 7]], np.int32)},
                     "obj:7:c001", "obj:7:c002", 7, np.ones((1, 2), bool), domain, 1.0)
    check("zero interior: counts 0 and None fractions",
          z["corridor_yx"] == [[0, 0], [0, 1]] and z["corridor_cell_count_interior"] == 0
          and z["base_cells"] == 0 and z["same_object_cells"] == 0 and z["other_object_cells"] == 0
          and z["other_object_counts"] == {} and z["seen_cells"] == 0 and z["unseen_cells"] == 0
          and z["seen_fraction"] is None and z["unseen_fraction"] is None)

    try:
        gap_corridor(graph, state, "obj:7:c001", "no-such-region", 7, seen, domain, 1.0)
        key_error = False
    except KeyError:
        key_error = True
    check("unresolvable region code raises KeyError", key_error)

    real_boundary = corridors_module._component_boundary
    corridors_module._component_boundary = lambda mask: np.zeros_like(np.asarray(mask, bool))
    try:
        gap_corridor(graph, state, "obj:7:c001", "obj:7:c002", 7, seen, domain, 1.0)
        runtime_error = False
    except RuntimeError as exc:
        runtime_error = "empty component boundary" in str(exc)
    finally:
        corridors_module._component_boundary = real_boundary
    check("empty component boundary raises RuntimeError", runtime_error)

    # ---- corridors_for_object: region_ids order, all i<j pairs.
    pairs = corridors_for_object(graph, state, 7, seen, domain, 1.0)
    check("corridors_for_object pair count and order",
          [(c["region_a"], c["region_b"]) for c in pairs]
          == [("obj:7:c002", "obj:7:c001"), ("obj:7:c002", "obj:7:c003"), ("obj:7:c001", "obj:7:c003")]
          and pairs[0] == rev)
    check("corridors_for_object: two regions give exactly one pair",
          [(c["region_a"], c["region_b"]) for c in corridors_for_object(graph, state, 9, seen, domain, 1.0)]
          == [("obj:9:c001", "obj:9:c002")])

    # Euclidean nearest: from A (0,0), B cell (3,3) is at sqrt(18) < 5 = |(0,5)|,
    # although (0,5) would win under an L1 metric (5 < 6).
    rc_l2 = np.full((4, 6), 3, np.int32)
    rc_l2[0, 0] = 1
    rc_l2[3, 3] = rc_l2[0, 5] = 2
    g_l2 = ScenePartitionGraph(regions={"obj:7:c001": _region("obj:7:c001", 1, oid="7"),
                                        "obj:7:c002": _region("obj:7:c002", 2, oid="7"),
                                        "base:c001": _region("base:c001", 3, RegionKind.BASE)})
    l2 = gap_corridor(g_l2, {"region_code": rc_l2, "owner_instance": np.zeros((4, 6), np.int32)},
                      "obj:7:c001", "obj:7:c002", 7, np.zeros((4, 6), bool), domain, 1.0)
    check("closest pair uses the Euclidean metric",
          l2["closest_endpoint_yx"] == [[0, 0], [3, 3]]
          and l2["corridor_yx"] == [[0, 0], [1, 1], [2, 2], [3, 3]])

    check("corridors_for_object: missing and single-region objects give []",
          corridors_for_object(graph, state, 99, seen, domain, 1.0) == []
          and corridors_for_object(graph, state, 12, seen, domain, 1.0) == [])

    params = inspect.signature(gap_corridor).parameters
    check("seen_any stays an explicit, required gap_corridor argument",
          list(params) == ["graph", "state", "region_a", "region_b", "target_id", "seen_any", "domain", "grid_deg"]
          and all(p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD and p.default is inspect.Parameter.empty
                  for p in params.values()))

    # ---- compatibility, duplication, dependencies, package footprints.
    from fov3d.experiments.classroom_partition import joint
    check("joint compatibility identities",
          all(getattr(joint, n) is getattr(corridors_module, n) for n in MOVED))
    joint_path = ROOT / "fov3d" / "experiments" / "classroom_partition" / "joint.py"
    joint_defs = {n.name for n in ast.parse(joint_path.read_text(encoding="utf-8")).body
                  if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    check("joint contains no duplicate corridor definitions", not (set(MOVED) & joint_defs))
    check("scene corridors has no experiment dependency",
          not _imports_experiment(ROOT / "fov3d" / "scene" / "corridors.py"))
    via_joint = []
    for path in sorted((ROOT / "fov3d").rglob("*.py")):
        if path.name == "joint.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.ImportFrom) and (node.module or "").endswith("classroom_partition.joint")
                    and set(MOVED) & {a.name for a in node.names}):
                via_joint.append(path.name)
    check("no production module takes corridors from joint", not via_joint)

    bare = _fresh(
        "import fov3d.scene\n"
        "print(json.dumps({k: k in sys.modules for k in "
        "['cv2', 'fov3d.scene.partition', 'fov3d.scene.boundaries', 'fov3d.scene.corridors']}))\n"
    )
    check("fresh bare import fov3d.scene stays lightweight",
          bool(bare) and not any(bare.values()))
    direct = _fresh(
        "import fov3d.scene.corridors\n"
        "print(json.dumps({'cv2': 'cv2' in sys.modules, 'partition': 'fov3d.scene.partition' in sys.modules}))\n"
    )
    check("fresh import fov3d.scene.corridors loads cv2 but not scene.partition",
          direct.get("cv2") is True and direct.get("partition") is False)

    print(f"[conceptual-core6-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
