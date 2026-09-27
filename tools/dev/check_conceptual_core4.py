#!/usr/bin/env python3
"""Fail-capable checks for Conceptual Core 4 scene-partition extraction."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fov3d.scene import (
    RegionKind,
    SupportLayer,
    joint_owner,
    label_joint_regions,
    support_depth_from_map,
)


def _layer(iid: int, support: np.ndarray, depth: np.ndarray) -> SupportLayer:
    return SupportLayer(
        instance_id=iid,
        object_name=str(iid),
        support=np.asarray(support, bool),
        depth_m=np.asarray(depth, np.float32),
        point_yx=np.empty((0, 2), np.int32),
        surfel_count=int(np.asarray(support, bool).sum()),
    )


def _imports(path: Path) -> list[tuple[str, tuple[str, ...]]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            out.append((node.module, tuple(a.name for a in node.names)))
    return out


def _imports_experiment(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").startswith("fov3d.experiments"):
                return True
        if isinstance(node, ast.Import):
            if any(a.name.startswith("fov3d.experiments") for a in node.names):
                return True
    return False


def main() -> int:
    checked = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal checked, failed
        checked += 1
        if condition:
            print(f"[conceptual-core4-check] PASS {name}")
        else:
            failed += 1
            print(f"[conceptual-core4-check] FAIL {name}")

    domain = {"yaw": [-2.0, 2.0], "pitch": [-2.0, 2.0]}

    empty = support_depth_from_map(
        np.array([[np.nan, 0.0, -1.0]], np.float64),
        domain, 1.0, instance_id=7, object_name="A",
    )
    check(
        "empty support raster",
        empty.support.shape == (5, 5)
        and empty.support.dtype == np.bool_
        and not empty.support.any()
        and empty.depth_m.dtype == np.float32
        and np.isposinf(empty.depth_m).all()
        and empty.point_yx.dtype == np.int32
        and empty.point_yx.tolist() == [[-1, -1]]
        and empty.surfel_count == 0,
    )

    one = support_depth_from_map(
        np.array([[np.nan, 0.0, -1.0], [0.0, 0.0, -1.0]], np.float64),
        domain, 1.0, instance_id=7, object_name="A",
    )
    check("point_yx original-index alignment",
          one.point_yx.tolist() == [[-1, -1], [2, 2]])
    check(
        "association disk expands beyond point cell",
        int(one.support.sum()) == 5
        and bool(one.support[2, 2])
        and bool(one.support[1, 2])
        and bool(one.support[2, 1])
        and bool(one.support[2, 3])
        and bool(one.support[3, 2]),
    )

    s = np.zeros((2, 2), bool)
    s[0, 0] = True
    d7 = np.full((2, 2), np.inf, np.float32)
    d8 = np.full((2, 2), np.inf, np.float32)
    d7[0, 0] = 2.0
    d8[0, 0] = 1.0
    owner, depth, overlap = joint_owner({
        7: _layer(7, s, d7),
        8: _layer(8, s, d8),
    })
    check("nearest depth wins", int(owner[0, 0]) == 8 and float(depth[0, 0]) == 1.0)
    check("overlap count", overlap.dtype == np.uint16 and int(overlap[0, 0]) == 2)

    d7[0, 0] = 1.0
    owner_tie, _depth_tie, _overlap_tie = joint_owner({
        8: _layer(8, s, d8),
        7: _layer(7, s, d7),
    })
    check("equal-depth tie prefers smaller id", int(owner_tie[0, 0]) == 7)

    mismatch_ok = False
    try:
        joint_owner({
            7: _layer(7, np.zeros((2, 2), bool), np.full((2, 2), np.inf, np.float32)),
            8: _layer(8, np.zeros((3, 3), bool), np.full((3, 3), np.inf, np.float32)),
        })
    except ValueError:
        mismatch_ok = True
    check("shape mismatch fails", mismatch_ok)

    diagonal_object = np.zeros((3, 3), np.int32)
    diagonal_object[0, 0] = 7
    diagonal_object[1, 1] = 7
    obj_depth = np.full((3, 3), np.inf, np.float32)
    obj_depth[diagonal_object == 7] = 2.0
    regions, objects, rc, c2r, r2c = label_joint_regions(
        diagonal_object, obj_depth, {7: "A"}
    )
    obj_regions = [r for r in regions.values() if r.kind is RegionKind.OBJECT_COMPONENT]
    check("foreground uses 8-connectivity", len(obj_regions) == 1)
    check(
        "object ids and membership",
        list(objects) == ["7"]
        and objects["7"].region_ids == ("obj:7:c001",)
        and objects["7"].attributes["identity_source"] == "inherited_from_classroom_oracle1"
        and regions["obj:7:c001"].attributes["source"] == "joint_frontmost_partition",
    )
    check("every cell labeled", np.all(rc > 0) and set(c2r) == set(np.unique(rc)) and set(r2c) == set(regions))

    diagonal_base = np.full((2, 2), 7, np.int32)
    diagonal_base[0, 0] = 0
    diagonal_base[1, 1] = 0
    base_depth = np.ones((2, 2), np.float32)
    base_depth[diagonal_base == 0] = np.inf
    regions2, _objects2, _rc2, _c2r2, _r2c2 = label_joint_regions(
        diagonal_base, base_depth, {7: "A"}
    )
    base_regions = [r for r in regions2.values() if r.kind is RegionKind.BASE]
    check("base uses 4-connectivity", len(base_regions) == 2)

    centered = np.zeros((3, 3), np.int32)
    centered[1, 1] = 7
    centered_depth = np.full((3, 3), np.inf, np.float32)
    centered_depth[1, 1] = 3.0
    regions3, _objects3, _rc3, _c2r3, _r2c3 = label_joint_regions(
        centered, centered_depth, {7: "A"}
    )
    attrs = regions3["obj:7:c001"].attributes
    check(
        "component attributes",
        attrs["cell_count"] == 1
        and attrs["touches_domain_edge"] is False
        and attrs["median_depth_m"] == 3.0
        and attrs["min_depth_m"] == 3.0
        and attrs["max_depth_m"] == 3.0
        and attrs["state_region_code"] == 1,
    )

    from fov3d.experiments.classroom_partition import joint
    check(
        "joint compatibility identities",
        joint.SupportLayer is SupportLayer
        and joint.support_depth_from_map is support_depth_from_map
        and joint.joint_owner is joint_owner
        and joint.label_joint_regions is label_joint_regions,
    )

    direct_ok = True
    for rel in (
        "fov3d/experiments/classroom_partition/relations.py",
        "fov3d/experiments/classroom_partition/incidental.py",
        "fov3d/experiments/classroom_partition/integration.py",
        "fov3d/experiments/classroom_partition/challenge_suite.py",
    ):
        imports = _imports(ROOT / rel)
        direct_ok &= any(
            module == "fov3d.scene" and "support_depth_from_map" in names
            for module, names in imports
        )
        direct_ok &= not any(
            module == "fov3d.experiments.classroom_partition.joint"
            and "support_depth_from_map" in names
            for module, names in imports
        )
    check("production consumers import support rasterization from scene", direct_ok)

    check(
        "scene partition has no experiment dependency",
        not _imports_experiment(ROOT / "fov3d" / "scene" / "partition.py"),
    )

    check("negative larger-id tie convention rejected", int(owner_tie[0, 0]) != 8)
    check("negative foreground-4-connectivity convention rejected", len(obj_regions) != 2)
    check("negative base-8-connectivity convention rejected", len(base_regions) != 1)
    check("negative point-only support convention rejected", int(one.support.sum()) != 1)

    print(f"[conceptual-core4-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
