"""Minimal spherical-coordinate utilities for the partition representation.

Angles are in degrees.  The canonical frame is x-forward, y-left, z-up only in
so far as lon/lat are defined by atan2(y, x) and asin(z).  The representation
stores unit 3-vectors so it is not tied to a particular 2-D chart or seam.
"""

from __future__ import annotations

import numpy as np


def normalize_rows(x: np.ndarray, *, eps: float = 1e-12) -> np.ndarray:
    a = np.asarray(x, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != 3:
        raise ValueError(f"expected shape (N,3), got {a.shape}")
    n = np.linalg.norm(a, axis=1, keepdims=True)
    if np.any(n <= eps):
        raise ValueError("cannot normalize a zero-length direction")
    return a / n


def lonlat_to_unit(lon_deg: np.ndarray, lat_deg: np.ndarray) -> np.ndarray:
    lon = np.deg2rad(np.asarray(lon_deg, dtype=np.float64))
    lat = np.deg2rad(np.asarray(lat_deg, dtype=np.float64))
    lon, lat = np.broadcast_arrays(lon, lat)
    cl = np.cos(lat)
    out = np.stack((cl * np.cos(lon), cl * np.sin(lon), np.sin(lat)), axis=-1)
    return out.reshape((-1, 3))


def unit_to_lonlat(unit: np.ndarray) -> np.ndarray:
    u = normalize_rows(unit)
    lon = np.rad2deg(np.arctan2(u[:, 1], u[:, 0]))
    lat = np.rad2deg(np.arcsin(np.clip(u[:, 2], -1.0, 1.0)))
    return np.stack((lon, lat), axis=1)
