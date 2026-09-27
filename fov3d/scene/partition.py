"""Reusable scene-partition construction."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from fov3d.geometry.head_chart import chart_cells, chart_grid, head_angles_from_unit
from fov3d.reconstruction.association import SURFACE_ASSOCIATION_RADIUS_M
from .model import ObjectHypothesis, PartitionRegion, RegionKind


@dataclass(frozen=True)
class SupportLayer:
    instance_id: int
    object_name: str
    support: np.ndarray
    depth_m: np.ndarray
    point_yx: np.ndarray
    surfel_count: int


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
    y0, _y1, p0, _p1, h, w = chart_grid(domain, grid_deg)
    xyz = np.asarray(xyz_h, dtype=np.float64).reshape(-1, 3)
    finite = np.isfinite(xyz).all(axis=1)
    ids = np.flatnonzero(finite)
    pts = xyz[finite]
    point_yx = np.full((len(xyz), 2), -1, np.int32)
    depth = np.full((h, w), np.inf, np.float32)
    if len(pts) == 0:
        return SupportLayer(instance_id, object_name, np.zeros((h, w), bool), depth, point_yx, 0)

    yaw, pitch = head_angles_from_unit(pts)
    yy, xx, ok = chart_cells(yaw, pitch, y0, p0, grid_deg, h, w)
    ranges = np.linalg.norm(pts, axis=1)
    rad_deg = np.degrees(np.arctan(SURFACE_ASSOCIATION_RADIUS_M / np.maximum(ranges, 1e-12)))
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
