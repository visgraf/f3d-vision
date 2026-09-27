"""Gap-corridor geometry extracted from the accepted Classroom Phase-3 adapter."""
from __future__ import annotations

from collections import Counter
from typing import Any

import cv2
import numpy as np

from fov3d.geometry.head_chart import chart_grid, head_unit_from_angles
from .model import ScenePartitionGraph


def _component_boundary(mask: np.ndarray) -> np.ndarray:
    m = np.asarray(mask, np.uint8)
    er = cv2.erode(m, np.ones((3, 3), np.uint8), borderType=cv2.BORDER_CONSTANT, borderValue=0)
    return (m.astype(bool) & ~er.astype(bool))


def _line_cells(y0: int, x0: int, y1: int, x1: int) -> np.ndarray:
    n = max(abs(int(y1) - int(y0)), abs(int(x1) - int(x0))) + 1
    ys = np.rint(np.linspace(y0, y1, n)).astype(np.int32)
    xs = np.rint(np.linspace(x0, x1, n)).astype(np.int32)
    pts = np.stack((ys, xs), axis=1)
    if len(pts) <= 1:
        return pts
    keep = np.ones(len(pts), bool)
    keep[1:] = np.any(pts[1:] != pts[:-1], axis=1)
    return pts[keep]


def gap_corridor(
    graph: ScenePartitionGraph,
    state: dict[str, np.ndarray],
    region_a: str,
    region_b: str,
    target_id: int,
    seen_any: np.ndarray,
    domain: dict[str, Any],
    grid_deg: float,
) -> dict[str, Any]:
    """Measure the direct local bridge between two disconnected target faces.

    The bridge is the digital straight segment joining the closest boundary-cell
    pair. It is intentionally local and does not route around the dominant
    exterior BASE region. It is a measurement, not a continuation hypothesis.
    """
    rc = np.asarray(state["region_code"], np.int32)
    owner = np.asarray(state["owner_instance"], np.int32)
    rid_to_code = {rid: i for i, rid in enumerate([])}
    # Recover codes from the raster by one representative cell per graph region.
    # Region ids encode object/component labels but codes themselves are state-local.
    code_a = code_b = None
    for code in np.unique(rc):
        code = int(code)
        ys, xs = np.nonzero(rc == code)
        if not len(ys):
            continue
        # Build the same id from graph membership by cell owner + component order is
        # not safe, so callers attach state-local code in region attributes below.
        rid = None
        for candidate, reg in graph.regions.items():
            if int(reg.attributes.get("state_region_code", -1)) == code:
                rid = candidate
                break
        if rid == region_a:
            code_a = code
        if rid == region_b:
            code_b = code
    if code_a is None or code_b is None:
        raise KeyError(f"could not resolve region codes for corridor {region_a}, {region_b}")

    ma = rc == code_a
    mb = rc == code_b
    ba = np.argwhere(_component_boundary(ma))
    bb = np.argwhere(_component_boundary(mb))
    if not len(ba) or not len(bb):
        raise RuntimeError("empty component boundary in corridor query")
    dist, idx = cv2.batchDistance(
        ba.astype(np.float32), bb.astype(np.float32), cv2.CV_32F,
        normType=cv2.NORM_L2, K=1,
    )
    i = int(np.argmin(dist[:, 0]))
    j = int(idx[i, 0])
    y0c, x0c = map(int, ba[i])
    y1c, x1c = map(int, bb[j])
    line = _line_cells(y0c, x0c, y1c, x1c)
    interior = line[1:-1] if len(line) > 2 else np.empty((0, 2), np.int32)

    y_min, _ym, p_min, _pm, _h, _w = chart_grid(domain, grid_deg)
    dirs = head_unit_from_angles(
        y_min + np.array([x0c, x1c], np.float64) * grid_deg,
        p_min + np.array([y0c, y1c], np.float64) * grid_deg,
    )
    dot = float(np.clip(np.dot(dirs[0], dirs[1]), -1.0, 1.0))
    gap_deg = float(np.degrees(np.arccos(dot)))

    owner_counts: Counter[int] = Counter()
    seen_count = unseen_count = 0
    if len(interior):
        vals = owner[interior[:, 0], interior[:, 1]]
        owner_counts.update(int(v) for v in vals.tolist())
        se = np.asarray(seen_any, bool)[interior[:, 0], interior[:, 1]]
        seen_count = int(se.sum())
        unseen_count = int(len(se) - se.sum())
    base_cells = int(owner_counts.get(0, 0))
    same_cells = int(owner_counts.get(int(target_id), 0))
    other_counts = {str(k): int(v) for k, v in sorted(owner_counts.items()) if k not in (0, int(target_id))}
    nint = int(len(interior))
    return {
        "object_id": str(target_id),
        "region_a": region_a,
        "region_b": region_b,
        "closest_endpoint_yx": [[y0c, x0c], [y1c, x1c]],
        "endpoint_gap_deg": gap_deg,
        "corridor_cell_count_interior": nint,
        "base_cells": base_cells,
        "same_object_cells": same_cells,
        "other_object_cells": int(sum(other_counts.values())),
        "other_object_counts": other_counts,
        "seen_cells": seen_count,
        "unseen_cells": unseen_count,
        "seen_fraction": None if nint == 0 else float(seen_count / nint),
        "unseen_fraction": None if nint == 0 else float(unseen_count / nint),
        "corridor_yx": line.astype(int).tolist(),
        "semantics": "closest-boundary straight local bridge; descriptive only, not a policy or continuity claim",
    }


def corridors_for_object(
    graph: ScenePartitionGraph,
    state: dict[str, np.ndarray],
    target_id: int,
    seen_any: np.ndarray,
    domain: dict[str, Any],
    grid_deg: float,
) -> list[dict[str, Any]]:
    oid = str(target_id)
    obj = graph.objects.get(oid)
    if obj is None or len(obj.region_ids) < 2:
        return []
    out: list[dict[str, Any]] = []
    rids = list(obj.region_ids)
    for i in range(len(rids)):
        for j in range(i + 1, len(rids)):
            out.append(gap_corridor(graph, state, rids[i], rids[j], target_id, seen_any, domain, grid_deg))
    return out


# Relation origin of a gap corridor (Conceptual Core 10): moved literally from the
# Phase-4 Classroom relations adapter; ownership_cut vs own_support_gap is descriptive.

def _region_code(graph: ScenePartitionGraph, rid: str) -> int:
    return int(graph.regions[rid].attributes["state_region_code"])


def _own_labels(layer_support: np.ndarray) -> np.ndarray:
    _n, labs = cv2.connectedComponents(np.asarray(layer_support, np.uint8), connectivity=8)
    return labs.astype(np.int32)


def _joint_region_own_component(graph: ScenePartitionGraph, state: dict[str, np.ndarray], rid: str,
                                own_labels: np.ndarray) -> int:
    code = _region_code(graph, rid)
    m = np.asarray(state["region_code"], np.int32) == code
    vals = np.unique(own_labels[m])
    vals = vals[vals > 0]
    if len(vals) != 1:
        raise RuntimeError(f"joint region {rid} does not map to exactly one own-support component: {vals.tolist()}")
    return int(vals[0])


def relation_origin(graph: ScenePartitionGraph, state: dict[str, np.ndarray], corridor: dict[str, Any],
                    own_support: np.ndarray) -> tuple[str, int, int]:
    labs = _own_labels(own_support)
    a = _joint_region_own_component(graph, state, corridor["region_a"], labs)
    b = _joint_region_own_component(graph, state, corridor["region_b"], labs)
    return ("ownership_cut" if a == b else "own_support_gap", a, b)
