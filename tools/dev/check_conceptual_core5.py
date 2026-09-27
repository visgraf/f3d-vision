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

import fov3d.scene.boundaries as boundaries_module
from fov3d.geometry.head_chart import head_unit_from_angles
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

    # Full edge list of the diagonal fixture: left/right edges first, then top/bottom,
    # each with its exact doubled endpoints and p0/p1 orientation.
    check(
        "exact horizontal edge metadata and enumeration order",
        diag_edges[(1, 2)] == [
            {"p0": (1, -1), "p1": (1, 1), "cell_a": (0, 0), "cell_b": (0, 1), "code_a": 1, "code_b": 2},
            {"p0": (1, 1), "p1": (1, 3), "cell_a": (1, 0), "cell_b": (1, 1), "code_a": 2, "code_b": 1},
            {"p0": (-1, 1), "p1": (1, 1), "cell_a": (0, 0), "cell_b": (1, 0), "code_a": 1, "code_b": 2},
            {"p0": (1, 1), "p1": (3, 1), "cell_a": (0, 1), "cell_b": (1, 1), "code_a": 2, "code_b": 1},
        ],
    )

    # The smallest endpoint (0, 0) is interior; the walk must start at the smallest
    # degree-1 endpoint (0, 2) instead.
    l_walks = _trace_edge_components([
        {"p0": (0, 0), "p1": (2, 0)},
        {"p0": (0, 0), "p1": (0, 2)},
    ])
    check(
        "open chain starts at smallest degree-1 endpoint, not smallest endpoint",
        l_walks == [([(0, 2), (0, 0), (2, 0)], [1, 0])],
    )

    # Figure eight through (0, 0): returning to the start with unused edges there must
    # continue the same walk.
    eight = _trace_edge_components([
        {"p0": (0, 0), "p1": (1, 0)},
        {"p0": (1, 0), "p1": (1, 1)},
        {"p0": (1, 1), "p1": (0, 1)},
        {"p0": (0, 1), "p1": (0, 0)},
        {"p0": (0, 0), "p1": (1, -1)},
        {"p0": (1, -1), "p1": (2, -1)},
        {"p0": (2, -1), "p1": (0, 0)},
    ])
    check(
        "closed walk continues through start while start edges remain",
        eight == [(
            [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0), (1, -1), (2, -1), (0, 0)],
            [0, 1, 2, 3, 4, 5, 6],
        )],
    )

    # Doubled endpoints (1,-1),(1,1),(1,3) -> half-cell chart (0.5, -0.5..1.5) ->
    # yaw -0.5, pitch -1.5/-0.5/0.5 on the 1-degree grid starting at (-1, -1).
    check(
        "exact sphere geometry from doubled endpoints",
        np.array_equal(
            b0.sphere_xyz,
            head_unit_from_angles([-0.5, -0.5, -0.5], [-1.5, -0.5, 0.5]),
        ),
    )

    # An object cell enclosed by BASE gives one closed four-edge loop.
    enclosed = np.full((3, 3), 2, np.int32)
    enclosed[1, 1] = 1
    b_loop, d_loop = extract_boundaries(
        enclosed,
        {1: "obj", 2: "base"},
        regions_ob,
        np.where(enclosed == 1, 1.0, np.inf).astype(np.float32),
        {"yaw": [-1.0, 1.0], "pitch": [-1.0, 1.0]},
        1.0,
    )
    loop_b = b_loop.get("jb00000")
    check(
        "closed object-base loop and diagnostics",
        list(b_loop) == ["jb00000"]
        and loop_b.closed is True
        and loop_b.kind is BoundaryKind.OBJECT_BASE
        and loop_b.sphere_xyz.shape == (5, 3)
        and loop_b.attributes == {
            "source": "four_neighbour_cell_side_interface",
            "interface_edge_count": 4,
            "region_pair": ["obj", "base"],
        }
        and d_loop == {
            "raster_interface_edges": 4,
            "encoded_interface_edges": 4,
            "unencoded_interface_edges": 0,
            "boundary_chains": 1,
            "branch_vertices": 0,
        },
    )

    # Five left/right edges between objects: jumps 1, 2, 4, 0 (tie) and one non-finite
    # sample -> median 1.5, min 0, max 4; a nearer 2, b nearer 1, the tie votes for neither.
    rc_stats = np.array([[1, 2]] * 5, np.int32)
    depth_stats = np.array(
        [[1.0, 2.0], [3.0, 1.0], [1.0, 5.0], [2.0, 2.0], [np.inf, 1.0]], np.float32
    )
    b_stats, _d_stats = extract_boundaries(
        rc_stats,
        {1: "a", 2: "b"},
        {"a": _region("a", RegionKind.OBJECT_COMPONENT, "1"),
         "b": _region("b", RegionKind.OBJECT_COMPONENT, "2")},
        depth_stats,
        {"yaw": [-1.0, 1.0], "pitch": [-2.0, 2.0]},
        1.0,
    )
    check(
        "depth-jump statistics with ties and non-finite samples",
        list(b_stats) == ["jb00000"]
        and b_stats["jb00000"].attributes == {
            "source": "four_neighbour_cell_side_interface",
            "interface_edge_count": 5,
            "region_pair": ["a", "b"],
            "depth_jump_median_m": 1.5,
            "depth_jump_min_m": 0.0,
            "depth_jump_max_m": 4.0,
            "nearer_region_a_votes": 2,
            "nearer_region_b_votes": 1,
        },
    )

    # Malformed tracing that drops an edge must be rejected by extract_boundaries.
    real_trace = boundaries_module._trace_edge_components

    def _lossy_trace(edges):
        walks = real_trace(edges)
        pts, used = walks[0]
        return [(pts[:-1], used[:-1])] + walks[1:]

    boundaries_module._trace_edge_components = _lossy_trace
    try:
        extract_boundaries(rc, {1: "obj", 2: "base"}, regions_ob, depth_ob, domain, 1.0)
        lossy_rejected = False
    except RuntimeError as exc:
        lossy_rejected = "lost interface edges" in str(exc)
    finally:
        boundaries_module._trace_edge_components = real_trace
    check("dropped interface edge raises RuntimeError", lossy_rejected)

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

    direct = _fresh(
        "import fov3d.scene.boundaries\n"
        "print(json.dumps({'cv2': 'cv2' in sys.modules, "
        "'partition': 'fov3d.scene.partition' in sys.modules}))"
    )
    check(
        "fresh import fov3d.scene.boundaries loads neither cv2 nor scene.partition",
        direct.get("cv2") is False and direct.get("partition") is False,
    )

    moved = {"_interface_edges", "_trace_edge_components", "extract_boundaries"}
    via_joint = []
    for path in sorted((ROOT / "fov3d").rglob("*.py")):
        if path.name == "joint.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.ImportFrom)
                and (node.module or "").endswith("classroom_partition.joint")
                and moved & {a.name for a in node.names}
            ):
                via_joint.append(path.name)
    check("no production module takes boundary extraction from joint", not via_joint)

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
