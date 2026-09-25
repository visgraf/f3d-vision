"""Joint retrospective Classroom partition and local gap-corridor analysis.

Partition-Graph Phase 3 remains read-only and post-hoc. It combines the latest
saved map of every object reconstructed so far into one frontmost spherical
partition, replays the old controller's exact ``seen_any`` sampling geometry
from saved calibrations, derives cell-side scene boundaries, and measures a
local straight gap corridor between disconnected components of one object.

No dense evaluation truth, Blender scene, controller execution, fusion, or new
measurement is used here. Object identity is inherited from the Oracle-1 run.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable
import json
import math

import cv2
import numpy as np

from fov3d.scene import (
    BoundaryChain,
    BoundaryKind,
    ObjectHypothesis,
    ObservationFootprint,
    ObservationOverlay,
    PartitionRegion,
    RegionKind,
    ScenePartitionGraph,
)
from fov3d.experiments.classroom_partition.lift import (
    FUSION_RADIUS_M,
    ReadLog,
    _camera_polygon,
    _cells,
    _grid,
    _head_angles_from_unit,
    _head_unit_from_angles,
)


@dataclass(frozen=True)
class SupportLayer:
    instance_id: int
    object_name: str
    support: np.ndarray
    depth_m: np.ndarray
    point_yx: np.ndarray
    surfel_count: int


@dataclass(frozen=True)
class StereoOps:
    rectification: Callable[[dict[str, Any]], dict[str, Any]]
    support_mask: Callable[[dict[str, Any], dict[str, Any], str], np.ndarray]


def _default_stereo_ops() -> StereoOps:
    # Lazy on purpose: structural tests can inject a pure synthetic fixture, while
    # the real lift uses the consolidated public facade to replay the old evidence
    # geometry exactly. This imports no matcher or controller.
    from fov3d.stereo.core import rectification, support_mask
    return StereoOps(rectification=rectification, support_mask=support_mask)


def _disk(radius: int) -> np.ndarray:
    yy, xx = np.mgrid[-radius:radius + 1, -radius:radius + 1]
    return ((xx * xx + yy * yy) <= radius * radius).astype(np.uint8)


def support_depth_from_map(
    xyz_h: np.ndarray,
    domain: dict[str, Any],
    grid_deg: float,
    *,
    instance_id: int,
    object_name: str,
) -> SupportLayer:
    """Rasterize a metric map using the frozen 12 mm association footprint.

    ``depth_m`` is the nearest surfel range whose projected association disk
    covers each chart cell. It is used only to resolve overlap among already
    reconstructed object maps in the joint retrospective partition.
    """
    y0, _y1, p0, _p1, h, w = _grid(domain, grid_deg)
    xyz = np.asarray(xyz_h, dtype=np.float64).reshape(-1, 3)
    finite = np.isfinite(xyz).all(axis=1)
    ids = np.flatnonzero(finite)
    pts = xyz[finite]
    point_yx = np.full((len(xyz), 2), -1, np.int32)
    depth = np.full((h, w), np.inf, np.float32)
    if len(pts) == 0:
        return SupportLayer(instance_id, object_name, np.zeros((h, w), bool), depth, point_yx, 0)

    yaw, pitch = _head_angles_from_unit(pts)
    yy, xx, ok = _cells(yaw, pitch, y0, p0, grid_deg, h, w)
    ranges = np.linalg.norm(pts, axis=1)
    rad_deg = np.degrees(np.arctan(FUSION_RADIUS_M / np.maximum(ranges, 1e-12)))
    rad_cells = np.maximum(1, np.ceil(rad_deg / grid_deg).astype(np.int32))
    point_yx[ids[ok], 0] = yy[ok]
    point_yx[ids[ok], 1] = xx[ok]

    for r in sorted(set(int(v) for v in rad_cells[ok])):
        sel = ok & (rad_cells == r)
        raw = np.full((h, w), np.inf, np.float32)
        np.minimum.at(raw, (yy[sel], xx[sel]), ranges[sel].astype(np.float32))
        expanded = cv2.erode(
            raw,
            _disk(r),
            borderType=cv2.BORDER_CONSTANT,
            borderValue=float("inf"),
        )
        depth = np.minimum(depth, expanded)
    return SupportLayer(
        instance_id=instance_id,
        object_name=object_name,
        support=np.isfinite(depth),
        depth_m=depth,
        point_yx=point_yx,
        surfel_count=int(finite.sum()),
    )


def joint_owner(layers: dict[int, SupportLayer]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return frontmost reconstructed owner, depth, and overlap count per cell."""
    if not layers:
        raise ValueError("joint_owner requires at least one support layer")
    shape = next(iter(layers.values())).support.shape
    owner = np.zeros(shape, np.int32)
    depth = np.full(shape, np.inf, np.float32)
    overlap = np.zeros(shape, np.uint16)
    for iid in sorted(layers):
        layer = layers[iid]
        if layer.support.shape != shape:
            raise ValueError("support-layer shape mismatch")
        overlap += layer.support.astype(np.uint16)
        d = layer.depth_m
        better = d < depth
        # Exact equal-depth ties are only a deterministic raster convention.
        tie = np.isfinite(d) & np.isfinite(depth) & (d == depth) & ((owner == 0) | (iid < owner))
        take = better | tie
        owner[take] = int(iid)
        depth[take] = d[take]
    return owner, depth, overlap


def _component_attrs(mask: np.ndarray, depth: np.ndarray | None = None) -> dict[str, Any]:
    ys, xs = np.nonzero(mask)
    attrs: dict[str, Any] = {
        "cell_count": int(mask.sum()),
        "touches_domain_edge": bool(
            len(ys)
            and (
                np.any(ys == 0)
                or np.any(xs == 0)
                or np.any(ys == mask.shape[0] - 1)
                or np.any(xs == mask.shape[1] - 1)
            )
        ),
    }
    if depth is not None:
        vals = np.asarray(depth)[mask]
        vals = vals[np.isfinite(vals)]
        if len(vals):
            attrs.update(
                median_depth_m=float(np.median(vals)),
                min_depth_m=float(np.min(vals)),
                max_depth_m=float(np.max(vals)),
            )
    return attrs


def label_joint_regions(
    owner: np.ndarray,
    owner_depth: np.ndarray,
    object_names: dict[int, str],
) -> tuple[
    dict[str, PartitionRegion],
    dict[str, ObjectHypothesis],
    np.ndarray,
    dict[int, str],
    dict[str, int],
]:
    """Label object faces with 8-connectivity and BASE with dual 4-connectivity."""
    owner = np.asarray(owner, np.int32)
    h, w = owner.shape
    region_code = np.zeros((h, w), np.int32)
    regions: dict[str, PartitionRegion] = {}
    objects: dict[str, ObjectHypothesis] = {}
    code_to_rid: dict[int, str] = {}
    rid_to_code: dict[str, int] = {}
    next_code = 1

    for iid in sorted(int(v) for v in np.unique(owner) if int(v) > 0):
        n, labs = cv2.connectedComponents((owner == iid).astype(np.uint8), connectivity=8)
        rids: list[str] = []
        for lab in range(1, n):
            mask = labs == lab
            rid = f"obj:{iid}:c{lab:03d}"
            attrs = _component_attrs(mask, owner_depth)
            attrs.update({"source": "joint_frontmost_partition", "instance_id": iid, "state_region_code": int(next_code)})
            regions[rid] = PartitionRegion(
                region_id=rid,
                kind=RegionKind.OBJECT_COMPONENT,
                object_id=str(iid),
                attributes=attrs,
            )
            region_code[mask] = next_code
            code_to_rid[next_code] = rid
            rid_to_code[rid] = next_code
            next_code += 1
            rids.append(rid)
        if rids:
            objects[str(iid)] = ObjectHypothesis(
                object_id=str(iid),
                region_ids=tuple(rids),
                attributes={
                    "object_name": object_names.get(iid, str(iid)),
                    "identity_source": "inherited_from_classroom_oracle1",
                },
            )

    # Digital-topology duality: if foreground uses 8-connectivity, complement uses 4.
    n_base, base_labs = cv2.connectedComponents((owner == 0).astype(np.uint8), connectivity=4)
    for lab in range(1, n_base):
        mask = base_labs == lab
        rid = f"base:c{lab:03d}"
        attrs = _component_attrs(mask)
        attrs.update({"source": "joint_frontmost_complement", "state_region_code": int(next_code)})
        regions[rid] = PartitionRegion(rid, RegionKind.BASE, attributes=attrs)
        region_code[mask] = next_code
        code_to_rid[next_code] = rid
        rid_to_code[rid] = next_code
        next_code += 1

    if np.any(region_code == 0):
        raise RuntimeError("joint region labelling left unlabeled cells")
    return regions, objects, region_code, code_to_rid, rid_to_code


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
    y0, _y1, p0, _p1, _h, _w = _grid(domain, grid_deg)
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
            sphere = _head_unit_from_angles(y0 + xa * grid_deg, p0 + ya * grid_deg)
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


def build_joint_graph(
    layers: dict[int, SupportLayer],
    object_names: dict[int, str],
    observations: ObservationOverlay,
    domain: dict[str, Any],
    grid_deg: float,
    *,
    global_index: int,
    current_target: int,
    current_local_step: int,
) -> tuple[ScenePartitionGraph, dict[str, np.ndarray], dict[str, int]]:
    owner, owner_depth, overlap = joint_owner(layers)
    regions, objects, region_code, code_to_rid, rid_to_code = label_joint_regions(owner, owner_depth, object_names)
    boundaries, boundary_diag = extract_boundaries(region_code, code_to_rid, regions, owner_depth, domain, grid_deg)
    graph = ScenePartitionGraph(
        regions=regions,
        objects=objects,
        boundaries=boundaries,
        observations=observations,
        attributes={
            "lift": "Classroom-Oracle-1 joint retrospective controller-time maps",
            "global_fixation_index": int(global_index),
            "current_target_instance_id": int(current_target),
            "current_target_local_step": int(current_local_step),
            "direction_frame": "legacy_head_H",
            "controller_domain_deg": domain,
            "grid_deg": float(grid_deg),
            "object_connectivity": 8,
            "base_connectivity": 4,
            "owner_rule": "nearest reconstructed 12mm-support range; deterministic instance-id tie break",
            "object_identity_source": "inherited_from_classroom_oracle1",
            "truth_used": False,
            "raw_footprints_are_display_only": True,
        },
    )
    graph.validate()
    state = {
        "owner_instance": owner,
        "owner_depth_m": owner_depth,
        "overlap_count": overlap,
        "region_code": region_code,
    }
    return graph, state, boundary_diag


def _rectified_core_directions_h(calibration: dict[str, Any], side: str, r: dict[str, Any]) -> np.ndarray:
    x0, y0, w, h = map(int, r["crop_xywh"])
    vv, uu = np.mgrid[:h, :w]
    uv = np.stack((uu + x0, vv + y0), axis=-1).astype(np.float64)
    k = np.asarray(r["P1" if side == "L" else "P2"], np.float64)[:, :3]
    rr = np.asarray(r["R1" if side == "L" else "R2"], np.float64)
    a = np.concatenate((uv, np.ones((h, w, 1))), axis=-1)
    d_rect = a @ np.linalg.inv(k).T
    d_c = d_rect @ rr
    eye = calibration["eyes"][0 if side == "L" else 1]
    d_h = d_c @ np.asarray(eye["R_hc"], np.float64).T
    d_h /= np.maximum(np.linalg.norm(d_h, axis=-1, keepdims=True), 1e-15)
    return d_h


def update_controller_seen_any(
    seen_any: np.ndarray,
    calibration: dict[str, Any],
    domain: dict[str, Any],
    grid_deg: float,
    *,
    stereo_ops: StereoOps | None = None,
) -> dict[str, int]:
    """Replay exactly the old controller's ``seen_any`` geometry.

    Only calibration and deterministic support masks are used. No image, instance
    id, local oracle observation, matcher output, or evaluation truth is opened.
    """
    ops = stereo_ops or _default_stereo_ops()
    r = ops.rectification(calibration)
    x0, y0, w, h = map(int, r["crop_xywh"])
    y_min, _ymax, p_min, _pmax, gh, gw = _grid(domain, grid_deg)
    before = int(seen_any.sum())
    marked_pixels = 0
    for side in ("L", "R"):
        full = np.asarray(ops.support_mask(calibration, r, side), bool)
        core = full[y0:y0 + h, x0:x0 + w]
        if core.shape != (h, w):
            raise ValueError(f"support-mask core shape mismatch for {side}: {core.shape} != {(h,w)}")
        directions = _rectified_core_directions_h(calibration, side, r)
        d = directions[core]
        marked_pixels += int(len(d))
        if len(d):
            yaw, pitch = _head_angles_from_unit(d)
            yy, xx, ok = _cells(yaw, pitch, y_min, p_min, grid_deg, gh, gw)
            seen_any[yy[ok], xx[ok]] = True
    return {
        "supported_core_pixels_both_eyes": int(marked_pixels),
        "new_seen_cells": int(seen_any.sum()) - before,
        "seen_cells": int(seen_any.sum()),
        "unseen_cells": int(seen_any.size - seen_any.sum()),
    }


def _append_raw_footprints(
    observations: ObservationOverlay,
    calibration: dict[str, Any],
    global_index: int,
    target_id: int,
    local_step: int,
) -> None:
    from fov3d.scene import FootprintEye
    for eye_index, eye in ((0, FootprintEye.LEFT), (1, FootprintEye.RIGHT)):
        poly, gaze = _camera_polygon(calibration, eye_index)
        observations.append(
            ObservationFootprint(
                fixation_id=f"g{global_index:03d}:obj{target_id}:fix{local_step:02d}",
                eye=eye,
                polygon_sphere_xyz=poly,
                gaze_sphere_xyz=gaze,
                sequence_index=global_index,
                attributes={
                    "semantics": "rendered_tangent_footprint_display_only",
                    "controller_seen_any_source": "exact_core_support_is_saved_in_state_npz",
                },
            )
        )


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

    y_min, _ym, p_min, _pm, _h, _w = _grid(domain, grid_deg)
    dirs = _head_unit_from_angles(
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


def attach_state_region_codes(graph: ScenePartitionGraph, region_code: np.ndarray) -> ScenePartitionGraph:
    """Validate the construction-time raster code carried by every region."""
    codes = {int(c) for c in np.unique(region_code)}
    graph_codes = {int(r.attributes.get("state_region_code", -1)) for r in graph.regions.values()}
    if -1 in graph_codes or graph_codes != codes:
        raise RuntimeError(f"graph/raster region-code mismatch: graph={sorted(graph_codes)} raster={sorted(codes)}")
    graph.validate()
    return graph


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


def _lineage(prev_rc: np.ndarray | None, curr_rc: np.ndarray) -> dict[str, Any]:
    """Classify lineage in one target-local component-label code space.

    Both rasters use 0 for background and 1..k for the target's current
    components. Phase 3 accidentally mixed these labels with state-global region
    codes; that made stable components look like a birth plus a death.
    """
    curr = np.asarray(curr_rc, np.int32)
    curr_codes = sorted(int(v) for v in np.unique(curr) if int(v) > 0)
    if prev_rc is None:
        return {
            "initial": True,
            "births": len(curr_codes),
            "merges": 0,
            "splits": 0,
            "deaths": 0,
            "persistent_links": 0,
        }
    prev = np.asarray(prev_rc, np.int32)
    if prev.shape != curr.shape:
        raise ValueError("lineage raster shape mismatch")
    prev_codes = sorted(int(v) for v in np.unique(prev) if int(v) > 0)
    parents: dict[int, set[int]] = {c: set() for c in curr_codes}
    children: dict[int, set[int]] = {c: set() for c in prev_codes}
    for pc in prev_codes:
        pm = prev == pc
        for cc in curr_codes:
            if np.any(pm & (curr == cc)):
                parents[cc].add(pc)
                children[pc].add(cc)
    births = sum(len(parents[c]) == 0 for c in curr_codes)
    merges = sum(len(parents[c]) > 1 for c in curr_codes)
    splits = sum(len(children[c]) > 1 for c in prev_codes)
    deaths = sum(len(children[c]) == 0 for c in prev_codes)
    persistent = sum(len(parents[c]) == 1 for c in curr_codes)
    return {
        "initial": False,
        "births": int(births),
        "merges": int(merges),
        "splits": int(splits),
        "deaths": int(deaths),
        "persistent_links": int(persistent),
    }


def _target_component_raster(graph: ScenePartitionGraph, region_code: np.ndarray, target_id: int) -> np.ndarray:
    out = np.zeros(region_code.shape, np.int32)
    obj = graph.objects.get(str(target_id))
    if obj is None:
        return out
    for k, rid in enumerate(obj.region_ids, start=1):
        code = int(graph.regions[rid].attributes["state_region_code"])
        out[region_code == code] = k
    return out


def _controller_expected_never(row: dict[str, Any]) -> int | None:
    try:
        return int(row["cyclopean_decision"]["audit"]["epistemic_state_counts"]["NEVER_OBSERVED"])
    except (KeyError, TypeError, ValueError):
        return None


def lift_joint_run(
    run_dir: str | Path,
    out_dir: str | Path,
    *,
    grid_deg: float = 0.10,
    stereo_ops: StereoOps | None = None,
    strict_evidence: bool = True,
) -> dict[str, Any]:
    run = Path(run_dir).resolve()
    out = Path(out_dir).resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"lift output must be new or empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    log = ReadLog(run)
    manifest = log.json(run / "manifest.json")
    if not manifest.get("control_complete"):
        raise RuntimeError("source run is not control_complete")
    seeds = log.json(run / "bootstrap" / "seeds.json")
    domain = seeds["controller_domain_deg"]
    if abs(float(grid_deg) - 0.10) > 1e-12:
        raise ValueError("Phase 3 exact controller-evidence replay requires the frozen 0.10 degree chart")
    _y0, _y1, _p0, _p1, h, w = _grid(domain, grid_deg)

    object_names = {int(o["instance_id"]): str(o["object_name"]) for o in manifest["objects"]}
    layers: dict[int, SupportLayer] = {}
    evidence: dict[int, np.ndarray] = {}
    global_observations = ObservationOverlay([])
    state_summaries: list[dict[str, Any]] = []
    final_state_for_object: dict[int, int] = {}
    evidence_checks: list[dict[str, Any]] = []
    lineage_totals = Counter()
    previous_target_labels: dict[int, np.ndarray] = {}
    stereo = stereo_ops or _default_stereo_ops()
    global_index = 0

    for obj in manifest["objects"]:
        iid = int(obj["instance_id"])
        name = str(obj["object_name"])
        odir = run / "objects" / f"instance_{iid:04d}"
        seen = evidence.setdefault(iid, np.zeros((h, w), bool))
        trajectory = list(obj.get("trajectory", []))
        for local_step in range(int(obj["fixation_count"])):
            calib = log.json(odir / "acquisitions" / f"fix_{local_step:02d}" / "calibration.json")
            ev_delta = update_controller_seen_any(seen, calib, domain, grid_deg, stereo_ops=stereo)
            _append_raw_footprints(global_observations, calib, global_index, iid, local_step)

            row = trajectory[local_step] if local_step < len(trajectory) else {}
            expected_never = _controller_expected_never(row)
            if expected_never is not None:
                actual_never = int(seen.size - seen.sum())
                check = {
                    "instance_id": iid,
                    "local_step": local_step,
                    "expected_never_observed": expected_never,
                    "replayed_never_observed": actual_never,
                    "match": bool(expected_never == actual_never),
                }
                evidence_checks.append(check)
                if strict_evidence and not check["match"]:
                    raise RuntimeError(f"controller seen_any replay mismatch: {check}")

            map_path = odir / "maps" / f"fix_{local_step:02d}.npz"
            if not map_path.exists():
                # Full Oracle-1 has initialized maps, but retain explicit behavior.
                state_summaries.append({
                    "global_index": global_index,
                    "instance_id": iid,
                    "object_name": name,
                    "local_step": local_step,
                    "map_present": False,
                    "evidence": ev_delta,
                })
                global_index += 1
                continue
            snap = log.npz(map_path)
            layer = support_depth_from_map(
                snap["xyz_h"], domain, grid_deg,
                instance_id=iid, object_name=name,
            )
            layers[iid] = layer
            graph, state, bdiag = build_joint_graph(
                layers, object_names, global_observations, domain, grid_deg,
                global_index=global_index,
                current_target=iid,
                current_local_step=local_step,
            )
            graph = attach_state_region_codes(graph, state["region_code"])
            state["current_target_seen_any"] = seen.astype(bool)
            state["current_target_support"] = layer.support.astype(bool)
            state_dir = out / "states" / f"global_{global_index:03d}"
            graph.save(state_dir / "scene-model")
            np.savez_compressed(state_dir / "state.npz", **state)

            rels = corridors_for_object(graph, state, iid, seen, domain, grid_deg)
            (state_dir / "corridors.json").write_text(
                json.dumps(rels, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )

            current_target_labels = _target_component_raster(graph, state["region_code"], iid)
            lineage = _lineage(previous_target_labels.get(iid), current_target_labels)
            previous_target_labels[iid] = current_target_labels
            if not lineage["initial"]:
                for key in ("births", "merges", "splits", "deaths"):
                    lineage_totals[key] += int(lineage[key])

            n_obj_regions = sum(r.kind is RegionKind.OBJECT_COMPONENT for r in graph.regions.values())
            n_base = sum(r.kind is RegionKind.BASE for r in graph.regions.values())
            n_oo = sum(b.kind is BoundaryKind.OBJECT_OBJECT for b in graph.boundaries.values())
            n_ob = sum(b.kind is BoundaryKind.OBJECT_BASE for b in graph.boundaries.values())
            current_components = len(graph.objects[str(iid)].region_ids) if str(iid) in graph.objects else 0
            s = {
                "global_index": global_index,
                "instance_id": iid,
                "object_name": name,
                "local_step": local_step,
                "map_present": True,
                "objects_present": len(graph.objects),
                "object_regions": int(n_obj_regions),
                "base_regions": int(n_base),
                "object_object_boundaries": int(n_oo),
                "object_base_boundaries": int(n_ob),
                "current_target_components": int(current_components),
                "current_target_corridors": len(rels),
                "boundary_diagnostics": bdiag,
                "evidence": ev_delta,
                "lineage": lineage,
            }
            state_summaries.append(s)
            final_state_for_object[iid] = global_index
            global_index += 1

    if global_index != int(manifest.get("total_fixations", global_index)):
        raise RuntimeError(f"global fixation count mismatch: built {global_index}, manifest {manifest.get('total_fixations')}")

    # Scene-final relations use the final joint partition but each target's own
    # controller evidence accumulated only during that target's historical run.
    final_valid = next((s for s in reversed(state_summaries) if s.get("map_present")), None)
    final_relations: list[dict[str, Any]] = []
    final_graph_path = None
    if final_valid is not None:
        gi = int(final_valid["global_index"])
        state_dir = out / "states" / f"global_{gi:03d}"
        final_graph = ScenePartitionGraph.load(state_dir / "scene-model")
        with np.load(state_dir / "state.npz", allow_pickle=False) as z:
            final_state = {k: np.array(z[k]) for k in z.files}
        for iid in sorted(evidence):
            for r in corridors_for_object(final_graph, final_state, iid, evidence[iid], domain, grid_deg):
                r["context"] = "scene_final"
                final_relations.append(r)
        (out / "scene-final-corridors.json").write_text(
            json.dumps(final_relations, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        final_graph_path = f"states/global_{gi:03d}/scene-model"

    # Causal-final relations are the relations at the last state of each object's
    # own historical processing, before any future object maps exist.
    causal_final: list[dict[str, Any]] = []
    for iid, gi in sorted(final_state_for_object.items()):
        d = out / "states" / f"global_{gi:03d}"
        if (d / "corridors.json").exists():
            rels = json.loads((d / "corridors.json").read_text(encoding="utf-8"))
            for r in rels:
                r["context"] = "causal_object_final"
                r["global_index"] = int(gi)
                causal_final.append(r)
    (out / "causal-final-corridors.json").write_text(
        json.dumps(causal_final, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    bad_paths = [
        p for p in sorted(set(log.paths))
        if "evaluation_only" in p or Path(p).name in {"reachable_samples.npz", "evaluation.json"}
    ]
    if bad_paths:
        raise RuntimeError(f"truth isolation violation: {bad_paths}")
    evidence_mismatches = sum(not c["match"] for c in evidence_checks)
    summary = {
        "schema": "PartitionGraph3-joint-retrospective-v1",
        "source_run": str(run),
        "posthoc_only": True,
        "controller_executed": False,
        "blender_launched": False,
        "dense_truth_opened": False,
        "object_identity_inherited": True,
        "grid_deg": float(grid_deg),
        "global_states": state_summaries,
        "final_state_for_object": {str(k): int(v) for k, v in sorted(final_state_for_object.items())},
        "final_graph": final_graph_path,
        "controller_seen_any_validation": {
            "checks": len(evidence_checks),
            "mismatches": int(evidence_mismatches),
            "records": evidence_checks,
        },
        "lineage_totals_excluding_initial": {k: int(lineage_totals[k]) for k in ("births", "merges", "splits", "deaths")},
        "corridor_aggregate": {
            "causal_final_pairs": len(causal_final),
            "scene_final_pairs": len(final_relations),
            "scene_final_pairs_crossing_other_object": sum(int(r["other_object_cells"] > 0) for r in final_relations),
            "scene_final_pairs_with_unseen_cells": sum(int(r["unseen_cells"] > 0) for r in final_relations),
        },
        "read_paths": sorted(set(log.paths)),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
