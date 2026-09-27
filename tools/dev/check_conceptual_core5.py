#!/usr/bin/env python3
"""Fail-capable checks for Conceptual Core 5 boundary extraction."""
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

from fov3d.scene.boundaries import (
    _interface_edges,
    _trace_edge_components,
    extract_boundaries,
)
from fov3d.scene.model import BoundaryKind, PartitionRegion, RegionKind


def _region(rid: str, kind: RegionKind, object_id: str | None = None) -> PartitionRegion:
    return PartitionRegion(rid, kind, object_id=object_id)


def _imports_experiment(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").startswith("fov3d.experiments"):
                return True
        elif isinstance(node, ast.Import):
            if any(a.name.startswith("fov3d.experiments") for a in node.names):
                return True
    return False


def _top_level_defs(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


def _fresh(code: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-I", "-c", f"import sys, json; sys.path.insert(0, {str(ROOT)!r}); {code}"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return {"_failed": True, "stderr": proc.stderr, "returncode": proc.returncode}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        return {"_failed": True, "stdout": proc.stdout, "stderr": proc.stderr}


def main() -> int:
    checked = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal checked, failed
        checked += 1
        if condition:
            print(f"[conceptual-core5-check] PASS {name}")
        else:
            failed += 1
            print(f"[conceptual-core5-check] FAIL {name}")

    # One vertical interface, two chart-cell sides in one deterministic open chain.
    rc = np.array([[1, 2], [1, 2]], np.int32)
    interfaces = _interface_edges(rc)
    check("interface pair keys", list(interfaces) == [(1, 2)])
    edges = interfaces[(1, 2)]
    check("interface edge count", len(edges) == 2)
    check(
        "exact first vertical edge metadata",
        edges[0] == {
            "p0": (1, -1),
            "p1": (1, 1),
            "cell_a": (0, 0),
            "cell_b": (0, 1),
            "code_a": 1,
            "code_b": 2,
        },
    )
    check(
        "exact second vertical edge metadata",
        edges[1] == {
            "p0": (1, 1),
            "p1": (1, 3),
            "cell_a": (1, 0),
            "cell_b": (1, 1),
            "code_a": 1,
            "code_b": 2,
        },
    )

    diagonal = np.array([[1, 2], [2, 1]], np.int32)
    diag_edges = _interface_edges(diagonal)
    check(
        "diagonal adjacency creates only four-neighbour sides",
        len(diag_edges[(1, 2)]) == 4,
    )

    walks = _trace_edge_components(edges)
    check(
        "deterministic open-chain tracing",
        walks == [([(1, -1), (1, 1), (1, 3)], [0, 1])],
    )

    loop_edges = [
        {"p0": (0, 0), "p1": (1, 0)},
        {"p0": (1, 0), "p1": (1, 1)},
        {"p0": (1, 1), "p1": (0, 1)},
        {"p0": (0, 1), "p1": (0, 0)},
    ]
    loop = _trace_edge_components(loop_edges)
    check(
        "deterministic closed-loop tracing",
        loop == [([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)], [0, 1, 2, 3])],
    )

    branch_edges = [
        {"p0": (0, 0), "p1": (1, 0)},
        {"p0": (1, 0), "p1": (2, 0)},
        {"p0": (1, 0), "p1": (1, 1)},
    ]
    branch_walks = _trace_edge_components(branch_edges)
    check(
        "deterministic branch walks",
        branch_walks
        == [
            ([(0, 0), (1, 0), (2, 0)], [0, 1]),
            ([(1, 0), (1, 1)], [2]),
        ],
    )

    domain = {"yaw": [-1.0, 1.0], "pitch": [-1.0, 1.0]}
    regions_ob = {
        "obj": _region("obj", RegionKind.OBJECT_COMPONENT, "1"),
        "base": _region("base", RegionKind.BASE),
    }
    depth_ob = np.array([[1.0, np.inf], [1.0, np.inf]], np.float32)
    boundaries, diag = extract_boundaries(
        rc,
        {1: "obj", 2: "base"},
        regions_ob,
        depth_ob,
        domain,
        1.0,
    )
    b0 = boundaries["jb00000"]
    check(
        "object-base boundary exact metadata",
        len(boundaries) == 1
        and b0.boundary_id == "jb00000"
        and b0.region_a == "obj"
        and b0.region_b == "base"
        and b0.kind is BoundaryKind.OBJECT_BASE
        and b0.closed is False
        and b0.attributes == {
            "source": "four_neighbour_cell_side_interface",
            "interface_edge_count": 2,
            "region_pair": ["obj", "base"],
        },
    )
    check(
        "boundary sphere directions are unit",
        b0.sphere_xyz.shape == (3, 3)
        and np.allclose(np.linalg.norm(b0.sphere_xyz, axis=1), 1.0),
    )
    check(
        "exact simple diagnostics",
        diag == {
            "raster_interface_edges": 2,
            "encoded_interface_edges": 2,
            "unencoded_interface_edges": 0,
            "boundary_chains": 1,
            "branch_vertices": 0,
        },
    )

    # Canonical pair is (1,2), but each raster edge is encountered as code_a=2,
    # code_b=1. Depths must therefore be swapped before nearer-region voting.
    rc_oo = np.array([[2, 1], [2, 1]], np.int32)
    regions_oo = {
        "near": _region("near", RegionKind.OBJECT_COMPONENT, "10"),
        "far": _region("far", RegionKind.OBJECT_COMPONENT, "20"),
    }
    depth_oo = np.array([[3.0, 1.0], [4.0, 2.0]], np.float32)
    boo, doo = extract_boundaries(
        rc_oo,
        {1: "near", 2: "far"},
        regions_oo,
        depth_oo,
        domain,
        1.0,
    )
    bo = boo["jb00000"]
    check("object-object kind", bo.kind is BoundaryKind.OBJECT_OBJECT)
    check(
        "depth jumps and canonical nearer votes",
        bo.attributes["depth_jump_median_m"] == 2.0
        and bo.attributes["depth_jump_min_m"] == 2.0
        and bo.attributes["depth_jump_max_m"] == 2.0
        and bo.attributes["nearer_region_a_votes"] == 2
        and bo.attributes["nearer_region_b_votes"] == 0,
    )
    check("object-object diagnostics complete", doo["unencoded_interface_edges"] == 0)

    # Pair iteration, not raster discovery order, controls jbNNNNN ids.
    rc_pairs = np.array([[3, 1, 2]], np.int32)
    regions_pairs = {
        "r1": _region("r1", RegionKind.OBJECT_COMPONENT, "1"),
        "r2": _region("r2", RegionKind.BASE),
        "r3": _region("r3", RegionKind.BASE),
    }
    bp, dp = extract_boundaries(
        rc_pairs,
        {1: "r1", 2: "r2", 3: "r3"},
        regions_pairs,
        np.array([[3.0, 1.0, np.inf]], np.float32),
        {"yaw": [-1.0, 1.0], "pitch": [0.0, 0.0]},
        1.0,
    )
    check(
        "sorted region pairs control boundary ids",
        list(bp) == ["jb00000", "jb00001"]
        and bp["jb00000"].attributes["region_pair"] == ["r1", "r2"]
        and bp["jb00001"].attributes["region_pair"] == ["r1", "r3"],
    )
    check(
        "multiple-pair diagnostics",
        dp["raster_interface_edges"] == 2
        and dp["encoded_interface_edges"] == 2
        and dp["unencoded_interface_edges"] == 0
        and dp["boundary_chains"] == 2,
    )

    branch_regions = {
        "a": _region("a", RegionKind.OBJECT_COMPONENT, "1"),
        "b": _region("b", RegionKind.OBJECT_COMPONENT, "2"),
    }
    branch_boundaries, branch_diag = extract_boundaries(
        diagonal,
        {1: "a", 2: "b"},
        branch_regions,
        np.array([[1.0, 2.0], [2.0, 1.0]], np.float32),
        domain,
        1.0,
    )
    check("branch diagnostic", branch_diag["branch_vertices"] == 1)
    check(
        "branch extraction encodes every interface",
        branch_diag["raster_interface_edges"] == 4
        and branch_diag["encoded_interface_edges"] == 4
        and branch_diag["unencoded_interface_edges"] == 0
        and sum(int(b.attributes["interface_edge_count"]) for b in branch_boundaries.values()) == 4,
    )

    from fov3d.experiments.classroom_partition import joint
    check(
        "joint compatibility identities",
        joint._interface_edges is _interface_edges
        and joint._trace_edge_components is _trace_edge_components
        and joint.extract_boundaries is extract_boundaries,
    )

    defs = _top_level_defs(ROOT / "fov3d" / "experiments" / "classroom_partition" / "joint.py")
    check(
        "joint contains no duplicate boundary definitions",
        not ({"_interface_edges", "_trace_edge_components", "extract_boundaries"} & defs),
    )
    check(
        "scene boundaries has no experiment dependency",
        not _imports_experiment(ROOT / "fov3d" / "scene" / "boundaries.py"),
    )

    bare = _fresh(
        "import fov3d.scene\n"
        "print(json.dumps({'cv2': 'cv2' in sys.modules, "
        "'partition': 'fov3d.scene.partition' in sys.modules, "
        "'boundaries': 'fov3d.scene.boundaries' in sys.modules}))"
    )
    check(
        "bare fov3d.scene import footprint unchanged",
        bare.get("cv2") is False
        and bare.get("partition") is False
        and bare.get("boundaries") is False,
    )

    # Explicit negative/mutation-style invariants.
    check("negative reversed pair ordering rejected", list(interfaces) != [(2, 1)])
    check("negative different open-chain start rejected", walks[0][0][0] == (1, -1))
    check("negative different candidate order rejected", branch_walks[0][1] == [0, 1])
    check("negative boundary-id discovery order rejected", bp["jb00000"].attributes["region_pair"] == ["r1", "r2"])
    check("negative OBJECT_OBJECT misclassification rejected", bo.kind is not BoundaryKind.OBJECT_BASE)
    check("negative depth orientation rejected", bo.attributes["nearer_region_a_votes"] != 0)
    check("negative lost-edge invariant rejected", branch_diag["unencoded_interface_edges"] == 0)

    print(f"[conceptual-core5-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
