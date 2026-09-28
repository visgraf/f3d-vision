"""Historical gaze context of the Classroom epistemic partition.

Conceptual Core 14 separates the observer's action history from the intrinsic epistemic
partition. ``fov3d.epistemic.partition`` describes the evidence accumulated in the state
(what was seen, with depth, from which identities). This module relates each region to
where the historical run looked: ``min_distance_to_historical_gaze_deg`` is the smallest
great-circle angle between the region centroid and the gaze directions supplied.

The supplied list is the historical producers' choice (the current target's gaze prefix);
this module does not select, weight or rank gazes. It is experiment-side on purpose: the
accepted semantics are target-local, not a general observer-history mechanism.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from fov3d.epistemic.partition import _angular_distance_deg, build_epistemic_partition


def _insert_after(mapping: dict[str, Any], anchor: str, key: str, value: Any) -> dict[str, Any]:
    """Copy ``mapping`` with ``key`` inserted immediately after ``anchor``."""
    if key in mapping:
        raise ValueError(f"{key!r} is already present")
    if anchor not in mapping:
        raise KeyError(anchor)
    out: dict[str, Any] = {}
    for k, v in mapping.items():
        out[k] = v
        if k == anchor:
            out[key] = value
    return out


def annotate_gaze_context(
    region_rows: list[dict[str, Any]],
    *,
    gazes_deg: list[tuple[float, float]],
) -> list[dict[str, Any]]:
    """Return the region rows with the historical ``min_distance_to_historical_gaze_deg``.

    New dictionaries are returned in the same order and the inputs are not modified. The
    field follows ``median_distance_to_target_deg``, as in the accepted Core-13 partition
    output, and is ``None`` when there are no gazes.
    """
    out = []
    for r in region_rows:
        cyaw, cpitch = r["centroid_yaw_deg"], r["centroid_pitch_deg"]
        gaze_dist = [
            _angular_distance_deg((cyaw, cpitch), (float(y), float(p)))
            for y, p in gazes_deg
        ] if gazes_deg and np.isfinite(cyaw) and np.isfinite(cpitch) else []
        out.append(_insert_after(
            r, "median_distance_to_target_deg", "min_distance_to_historical_gaze_deg",
            None if not gaze_dist else float(min(gaze_dist)),
        ))
    return out


def build_gaze_context_partition(
    state: dict[str, np.ndarray],
    *,
    target_id: int,
    target_name: str,
    domain: dict[str, Any],
    grid_deg: float,
    gazes_deg: list[tuple[float, float]],
) -> tuple[dict[str, np.ndarray], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Build the intrinsic epistemic partition and apply the historical gaze context."""
    arrays, region_rows, edge_rows, diag = build_epistemic_partition(
        state,
        target_id=target_id,
        target_name=target_name,
        domain=domain,
        grid_deg=grid_deg,
    )
    region_rows = annotate_gaze_context(region_rows, gazes_deg=gazes_deg)
    return arrays, region_rows, edge_rows, diag
