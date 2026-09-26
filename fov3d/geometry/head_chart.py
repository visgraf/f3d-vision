"""Fixed-head spherical yaw/pitch chart utilities.

This module owns the head-frame chart convention used by the retrospective
Classroom partition experiments:

    +X = head right
    +Y = head up
    -Z = forward

Angles are in degrees. This convention is intentionally distinct from the
generic lon/lat utilities in fov3d.scene.sphere.
"""
from __future__ import annotations

from typing import Any

import numpy as np


def head_angles_from_unit(directions_h: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return fixed-head yaw and pitch in degrees.

    Input rows are normalized before conversion, matching the historical helper.
    """
    u = np.asarray(directions_h, dtype=np.float64).reshape(-1, 3)
    n = np.linalg.norm(u, axis=1, keepdims=True)
    u = u / np.maximum(n, 1e-15)
    yaw = np.degrees(np.arctan2(u[:, 0], -u[:, 2]))
    pitch = np.degrees(np.arctan2(u[:, 1], np.hypot(u[:, 0], u[:, 2])))
    return yaw, pitch


def head_unit_from_angles(
    yaw_deg: np.ndarray,
    pitch_deg: np.ndarray,
) -> np.ndarray:
    """Return fixed-head unit directions for broadcast yaw/pitch inputs."""
    yaw = np.deg2rad(np.asarray(yaw_deg, dtype=np.float64))
    pitch = np.deg2rad(np.asarray(pitch_deg, dtype=np.float64))
    yaw, pitch = np.broadcast_arrays(yaw, pitch)
    out = np.stack(
        (
            np.sin(yaw) * np.cos(pitch),
            np.sin(pitch),
            -np.cos(yaw) * np.cos(pitch),
        ),
        axis=-1,
    )
    return out.reshape(-1, 3)


def chart_grid(
    domain: dict[str, Any],
    grid_deg: float,
) -> tuple[float, float, float, float, int, int]:
    """Return yaw/pitch bounds and inclusive chart shape (h, w)."""
    y0, y1 = map(float, domain["yaw"])
    p0, p1 = map(float, domain["pitch"])
    w = int(round((y1 - y0) / grid_deg)) + 1
    h = int(round((p1 - p0) / grid_deg)) + 1
    return y0, y1, p0, p1, h, w


def chart_cells(
    yaw: np.ndarray,
    pitch: np.ndarray,
    y0: float,
    p0: float,
    grid_deg: float,
    h: int,
    w: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Map angles to nearest inclusive chart cells using historical np.rint."""
    x = np.rint((np.asarray(yaw) - y0) / grid_deg).astype(np.int64)
    y = np.rint((np.asarray(pitch) - p0) / grid_deg).astype(np.int64)
    ok = (
        np.isfinite(yaw)
        & np.isfinite(pitch)
        & (x >= 0)
        & (x < w)
        & (y >= 0)
        & (y < h)
    )
    return y, x, ok
