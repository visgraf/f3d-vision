"""Epistemic-region partition of a head-centred evidence state.

The partition assigns every chart cell one epistemic kind (target support, other surface,
unknown, ambiguous boundary or unmapped target evidence) and describes each connected
region: identity, geometry, evidence fractions, distances and interfaces.

Conceptual Core 11 moved the accepted representation here from the Classroom Phase-6
benchmark module. Conceptual Core 12 removed the candidate annotation (``candidate`` and
``candidate_region_count``): calling a region a candidate is an interpretation of this
representation, not part of it, and the historical rule lives with the Classroom
experiment adapters. Conceptual Core 13 removed the reconstruction status and with it the
experiment's target schedule (``all_target_ids``): whether a surface will be targeted later
is historical run context, not evidence. The evidence provenance ``surface_source`` stays
here. Conceptual Core 14 removed the observer's action history (``gazes_deg`` and the
region's distance to previous fixations): the partition depends only on accumulated evidence,
and ``_angular_distance_deg`` stays here as a generic geometric helper.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any
import math

import cv2
import numpy as np

from fov3d.geometry.head_chart import chart_grid


REGION_KIND = {
    "TARGET_SUPPORT": 1,
    "OTHER_SURFACE": 2,
    "UNKNOWN": 3,
    "AMBIGUOUS_BOUNDARY": 4,
    "TARGET_EVIDENCE_UNMAPPED": 5,
}
REGION_KIND_BY_CODE = {v: k for k, v in REGION_KIND.items()}


def _component_labels(mask: np.ndarray, connectivity: int) -> tuple[int, np.ndarray]:
    m = np.asarray(mask, np.uint8)
    n, labs = cv2.connectedComponents(m, connectivity=connectivity)
    return int(n), labs.astype(np.int32)


def _distance_to_target(target_support: np.ndarray, grid_deg: float) -> np.ndarray:
    target = np.asarray(target_support, bool)
    if not target.any():
        return np.full(target.shape, np.inf, np.float32)
    # cv2.distanceTransform measures non-zero pixels to the nearest zero pixel.
    d = cv2.distanceTransform((~target).astype(np.uint8), cv2.DIST_L2, 5)
    return (d * float(grid_deg)).astype(np.float32)


def _touches_edge(mask: np.ndarray) -> bool:
    m = np.asarray(mask, bool)
    if not m.any():
        return False
    return bool(m[0].any() or m[-1].any() or m[:, 0].any() or m[:, -1].any())


def _centroid_angles(mask: np.ndarray, domain: dict[str, Any], grid_deg: float) -> tuple[float, float]:
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return float("nan"), float("nan")
    y0, _y1, p0, _p1, _h, _w = chart_grid(domain, grid_deg)
    return float(y0 + xs.mean() * grid_deg), float(p0 + ys.mean() * grid_deg)


def _angular_distance_deg(a: tuple[float, float], b: tuple[float, float]) -> float:
    ay, ap = map(math.radians, a)
    by, bp = map(math.radians, b)
    ua = np.array([math.sin(ay) * math.cos(ap), math.sin(ap), -math.cos(ay) * math.cos(ap)])
    ub = np.array([math.sin(by) * math.cos(bp), math.sin(bp), -math.cos(by) * math.cos(bp)])
    return float(math.degrees(math.acos(float(np.clip(np.dot(ua, ub), -1.0, 1.0)))))


def _region_interfaces(region_code: np.ndarray) -> tuple[list[dict[str, Any]], dict[int, dict[int, int]]]:
    rc = np.asarray(region_code, np.int32)
    pairs: Counter[tuple[int, int]] = Counter()
    left = rc[:, :-1]
    right = rc[:, 1:]
    ys, xs = np.nonzero(left != right)
    for y, x in zip(ys.tolist(), xs.tolist()):
        a, b = int(left[y, x]), int(right[y, x])
        if a and b:
            pairs[tuple(sorted((a, b)))] += 1
    top = rc[:-1, :]
    bottom = rc[1:, :]
    ys, xs = np.nonzero(top != bottom)
    for y, x in zip(ys.tolist(), xs.tolist()):
        a, b = int(top[y, x]), int(bottom[y, x])
        if a and b:
            pairs[tuple(sorted((a, b)))] += 1
    edges = [
        {"region_code_a": int(a), "region_code_b": int(b), "interface_edge_count": int(n)}
        for (a, b), n in sorted(pairs.items())
    ]
    adjacency: dict[int, dict[int, int]] = defaultdict(dict)
    for (a, b), n in pairs.items():
        adjacency[a][b] = int(n)
        adjacency[b][a] = int(n)
    return edges, adjacency


def build_epistemic_partition(
    state: dict[str, np.ndarray],
    *,
    target_id: int,
    target_name: str,
    domain: dict[str, Any],
    grid_deg: float,
) -> tuple[dict[str, np.ndarray], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Build a truth-free causal evidence partition for one target-final state.

    Precedence is intentionally representation-first:
      target own support > ambiguous instance boundary > mapped/incidental other
      surface > unmapped target evidence > no head-centred depth.

    Unknown territory is therefore defined in the same head-origin chart as the
    persistent object support.  Historical eye-ray ``seen_any`` is retained only
    as an attribute; it does not define region identity.
    """
    target_support = np.asarray(state["target_support"], bool)
    owner = np.asarray(state["owner_instance"], np.int32)
    nearest = np.asarray(state["nearest_instance"], np.int32)
    ambiguous = np.asarray(state["ambiguous_instance"], bool)
    depth_seen = np.asarray(state["depth_seen"], bool)
    seen_any = np.asarray(state["seen_any"], bool)
    if not (target_support.shape == owner.shape == nearest.shape == ambiguous.shape == depth_seen.shape == seen_any.shape):
        raise ValueError("Phase-5 state rasters do not share one chart shape")

    mapped_other = (~target_support) & (owner > 0) & (owner != int(target_id))
    incidental_other = (~target_support) & (~mapped_other) & (nearest > 0) & (nearest != int(target_id))
    target_unmapped = (~target_support) & (nearest == int(target_id))
    ambiguous_boundary = (~target_support) & ambiguous
    other_surface = (~ambiguous_boundary) & (mapped_other | incidental_other)
    target_unmapped &= ~ambiguous_boundary & ~other_surface
    unknown = ~(target_support | ambiguous_boundary | other_surface | target_unmapped)

    class_code = np.zeros(target_support.shape, np.uint8)
    class_code[target_support] = REGION_KIND["TARGET_SUPPORT"]
    class_code[other_surface] = REGION_KIND["OTHER_SURFACE"]
    class_code[unknown] = REGION_KIND["UNKNOWN"]
    class_code[ambiguous_boundary] = REGION_KIND["AMBIGUOUS_BOUNDARY"]
    class_code[target_unmapped] = REGION_KIND["TARGET_EVIDENCE_UNMAPPED"]
    if np.any(class_code == 0):
        raise RuntimeError("epistemic partition left unclassified cells")

    surface_instance = np.zeros(owner.shape, np.int32)
    surface_instance[mapped_other] = owner[mapped_other]
    take_inc = incidental_other & ~mapped_other
    surface_instance[take_inc] = nearest[take_inc]

    region_code = np.zeros(owner.shape, np.int32)
    region_rows: list[dict[str, Any]] = []
    next_code = 1
    distance_deg = _distance_to_target(target_support, grid_deg)

    def add_components(kind: str, mask: np.ndarray, connectivity: int, instance_id: int | None = None) -> None:
        nonlocal next_code
        n, labs = _component_labels(mask, connectivity)
        for lab in range(1, n):
            m = labs == lab
            if not m.any():
                continue
            code = next_code
            next_code += 1
            region_code[m] = code
            cyaw, cpitch = _centroid_angles(m, domain, grid_deg)
            dvals = distance_deg[m]
            finite_d = dvals[np.isfinite(dvals)]
            mapped_n = int((mapped_other & m).sum())
            incidental_n = int((incidental_other & m).sum())
            row: dict[str, Any] = {
                "region_code": int(code),
                "region_id": f"{kind.lower()}:{code:04d}",
                "kind": kind,
                "instance_id": None if instance_id is None else int(instance_id),
                "cell_count": int(m.sum()),
                "touches_domain_edge": _touches_edge(m),
                "centroid_yaw_deg": cyaw,
                "centroid_pitch_deg": cpitch,
                "min_distance_to_target_deg": None if not len(finite_d) else float(np.min(finite_d)),
                "median_distance_to_target_deg": None if not len(finite_d) else float(np.median(finite_d)),
                "seen_any_fraction": float(seen_any[m].mean()),
                "head_depth_fraction": float(depth_seen[m].mean()),
                "mapped_cells": mapped_n,
                "incidental_cells": incidental_n,
            }
            if kind == "OTHER_SURFACE" and instance_id is not None:
                if mapped_n and incidental_n:
                    source = "mapped_and_incidental"
                elif mapped_n:
                    source = "mapped"
                elif incidental_n:
                    source = "incidental"
                else:
                    source = "unknown"
                row["surface_source"] = source
            region_rows.append(row)

    # Target support remains its own-support topology (8-connected).
    add_components("TARGET_SUPPORT", target_support, 8, int(target_id))

    # Keep distinct non-target identities separate, including incidental-only ones.
    for iid in sorted(int(v) for v in np.unique(surface_instance) if int(v) > 0):
        add_components("OTHER_SURFACE", other_surface & (surface_instance == iid), 8, iid)

    # Complement-like classes use 4-connectivity as digital duals to 8-connected surfaces.
    add_components("UNKNOWN", unknown, 4, None)
    add_components("AMBIGUOUS_BOUNDARY", ambiguous_boundary, 4, None)
    add_components("TARGET_EVIDENCE_UNMAPPED", target_unmapped, 8, int(target_id))

    if np.any(region_code == 0):
        raise RuntimeError("epistemic region labelling left cells without region codes")

    edge_rows, adjacency = _region_interfaces(region_code)
    by_code = {int(r["region_code"]): r for r in region_rows}
    for code, row in by_code.items():
        row["adjacent_regions"] = [
            {"region_code": int(n), "region_id": by_code[n]["region_id"], "interface_edge_count": int(c)}
            for n, c in sorted(adjacency.get(code, {}).items())
        ]
        row["adjacent_to_target_support"] = any(
            by_code[n]["kind"] == "TARGET_SUPPORT" for n in adjacency.get(code, {})
        )

    diag = {
        "target_id": int(target_id),
        "target_name": str(target_name),
        "chart_shape_hw": [int(v) for v in target_support.shape],
        "region_count": len(region_rows),
        "kind_region_counts": dict(sorted(Counter(r["kind"] for r in region_rows).items())),
        "kind_cell_counts": {
            name: int((class_code == code).sum()) for name, code in REGION_KIND.items()
        },
        "target_evidence_unmapped_cells": int(target_unmapped.sum()),
        "ambiguous_boundary_cells": int(ambiguous_boundary.sum()),
        "head_depth_cells": int(depth_seen.sum()),
        "eye_ray_seen_cells": int(seen_any.sum()),
        "truth_used": False,
    }
    arrays = {
        "class_code": class_code,
        "region_code": region_code,
        "surface_instance": surface_instance,
        "target_support": target_support,
        "depth_seen": depth_seen,
        "seen_any": seen_any,
        "mapped_other": mapped_other,
        "incidental_other": incidental_other,
        "ambiguous_boundary": ambiguous_boundary,
    }
    return arrays, region_rows, edge_rows, diag
