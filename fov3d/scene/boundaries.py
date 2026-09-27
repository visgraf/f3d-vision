"""Reusable extraction of cell-side boundaries from a spherical scene partition.

Conceptual Core 5 lifts the accepted Phase-3 interface enumeration and deterministic
BoundaryChain tracing into the scene layer without changing behavior.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

import numpy as np

from fov3d.geometry.head_chart import chart_grid, head_unit_from_angles
from .model import BoundaryChain, BoundaryKind, PartitionRegion, RegionKind


def _interface_edges(region_code: np.ndarray) -> dict[tuple[int, int], list[dict[str, Any]]]:
    """Enumerate every 4-neighbour cell-side interface exactly once.

    Endpoint coordinates are stored doubled: cell centres are even integer
    coordinates and cell corners are odd coordinates. This avoids floating-key
    ambiguity when connected edge chains are reconstructed.
    """
    rc = np.asarray(region_code, np.int32)
    h, w = rc.shape
    out: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)

    # Left/right cell pairs: vertical interface at x+1/2.
    ys, xs = np.nonzero(rc[:, :-1] != rc[:, 1:])
    for y, x in zip(ys.tolist(), xs.tolist()):
        a, b = int(rc[y, x]), int(rc[y, x + 1])
        pair = (a, b) if a < b else (b, a)
        out[pair].append(
            {
                "p0": (2 * x + 1, 2 * y - 1),
                "p1": (2 * x + 1, 2 * y + 1),
                "cell_a": (y, x),
                "cell_b": (y, x + 1),
                "code_a": a,
                "code_b": b,
            }
        )

    # Top/bottom cell pairs: horizontal interface at y+1/2.
    ys, xs = np.nonzero(rc[:-1, :] != rc[1:, :])
    for y, x in zip(ys.tolist(), xs.tolist()):
        a, b = int(rc[y, x]), int(rc[y + 1, x])
        pair = (a, b) if a < b else (b, a)
        out[pair].append(
            {
                "p0": (2 * x - 1, 2 * y + 1),
                "p1": (2 * x + 1, 2 * y + 1),
                "cell_a": (y, x),
                "cell_b": (y + 1, x),
                "code_a": a,
                "code_b": b,
            }
        )
    return out


def _trace_edge_components(edges: list[dict[str, Any]]) -> list[tuple[list[tuple[int, int]], list[int]]]:
    """Trace interface-edge components into deterministic non-branching walks."""
    endpoint_to_edges: dict[tuple[int, int], list[int]] = defaultdict(list)
    for i, e in enumerate(edges):
        endpoint_to_edges[e["p0"]].append(i)
        endpoint_to_edges[e["p1"]].append(i)
    unused = set(range(len(edges)))
    walks: list[tuple[list[tuple[int, int]], list[int]]] = []
    while unused:
        degrees: Counter[tuple[int, int]] = Counter()
        for i in unused:
            degrees[edges[i]["p0"]] += 1
            degrees[edges[i]["p1"]] += 1
        ends = sorted(p for p, d in degrees.items() if d == 1)
        start = ends[0] if ends else min(min(edges[i]["p0"], edges[i]["p1"]) for i in unused)
        pts = [start]
        used_here: list[int] = []
        cur = start
        while True:
            candidates = sorted(i for i in endpoint_to_edges[cur] if i in unused)
            if not candidates:
                break
            i = candidates[0]
            unused.remove(i)
            used_here.append(i)
            e = edges[i]
            nxt = e["p1"] if e["p0"] == cur else e["p0"]
            pts.append(nxt)
            cur = nxt
            if cur == start and not any(j in unused for j in endpoint_to_edges[cur]):
                break
        if used_here:
            walks.append((pts, used_here))
    return walks


def extract_boundaries(
    region_code: np.ndarray,
    code_to_rid: dict[int, str],
    regions: dict[str, PartitionRegion],
    owner_depth: np.ndarray,
    domain: dict[str, Any],
    grid_deg: float,
) -> tuple[dict[str, BoundaryChain], dict[str, int]]:
    interfaces = _interface_edges(region_code)
    boundaries: dict[str, BoundaryChain] = {}
    y0, _y1, p0, _p1, _h, _w = chart_grid(domain, grid_deg)
    encoded_edges = 0
    branch_vertices = 0
    bid_counter = 0

    for pair in sorted(interfaces):
        edges = interfaces[pair]
        # Branch degree is diagnostic; walks below split such topology rather than
        # pretending one unordered point set is a curve.
        degree: Counter[tuple[int, int]] = Counter()
        for e in edges:
            degree[e["p0"]] += 1
            degree[e["p1"]] += 1
        branch_vertices += sum(int(v > 2) for v in degree.values())

        for pts2, used in _trace_edge_components(edges):
            if len(pts2) < 2:
                continue
            code_a, code_b = pair
            rid_a, rid_b = code_to_rid[code_a], code_to_rid[code_b]
            xa = np.asarray([p[0] for p in pts2], np.float64) / 2.0
            ya = np.asarray([p[1] for p in pts2], np.float64) / 2.0
            sphere = head_unit_from_angles(y0 + xa * grid_deg, p0 + ya * grid_deg)
            ra, rb = regions[rid_a], regions[rid_b]
            kind = (
                BoundaryKind.OBJECT_OBJECT
                if ra.kind is RegionKind.OBJECT_COMPONENT and rb.kind is RegionKind.OBJECT_COMPONENT
                else BoundaryKind.OBJECT_BASE
            )
            attrs: dict[str, Any] = {
                "source": "four_neighbour_cell_side_interface",
                "interface_edge_count": int(len(used)),
                "region_pair": [rid_a, rid_b],
            }
            if kind is BoundaryKind.OBJECT_OBJECT:
                jumps: list[float] = []
                nearer_a = nearer_b = 0
                for i in used:
                    e = edges[i]
                    ya0, xa0 = e["cell_a"]
                    yb0, xb0 = e["cell_b"]
                    da = float(owner_depth[ya0, xa0])
                    db = float(owner_depth[yb0, xb0])
                    # Orient depths into canonical region-code order.
                    if e["code_a"] != code_a:
                        da, db = db, da
                    if np.isfinite(da) and np.isfinite(db):
                        jumps.append(abs(da - db))
                        nearer_a += int(da < db)
                        nearer_b += int(db < da)
                if jumps:
                    attrs.update(
                        depth_jump_median_m=float(np.median(jumps)),
                        depth_jump_min_m=float(np.min(jumps)),
                        depth_jump_max_m=float(np.max(jumps)),
                        nearer_region_a_votes=int(nearer_a),
                        nearer_region_b_votes=int(nearer_b),
                    )
            bid = f"jb{bid_counter:05d}"
            bid_counter += 1
            boundaries[bid] = BoundaryChain(
                boundary_id=bid,
                region_a=rid_a,
                region_b=rid_b,
                sphere_xyz=sphere,
                closed=bool(len(pts2) > 2 and pts2[0] == pts2[-1]),
                kind=kind,
                attributes=attrs,
            )
            encoded_edges += len(used)

    raster_edges = sum(len(v) for v in interfaces.values())
    diag = {
        "raster_interface_edges": int(raster_edges),
        "encoded_interface_edges": int(encoded_edges),
        "unencoded_interface_edges": int(raster_edges - encoded_edges),
        "boundary_chains": int(len(boundaries)),
        "branch_vertices": int(branch_vertices),
    }
    if encoded_edges != raster_edges:
        raise RuntimeError(f"boundary extraction lost interface edges: {diag}")
    return boundaries, diag
