"""Persistent head-centered epistemic memory.

This module owns the reusable head-chart evidence accumulator established by the
Classroom Partition-Graph Phase 5 experiments and reused causally by later phases.

The representation intentionally preserves two kinds of accumulated state:

- target-neutral measured evidence: depth_seen, nearest_instance, nearest_range_m,
  ambiguous_instance, and sample_count;
- historical target-relative evidence: target_depth_seen and other_depth_seen,
  conditioned on the target_id supplied when each patch is accumulated.

Conceptual Core 3 preserves that distinction exactly. A future representation may
derive the target-relative view instead of storing it, but no such redesign belongs
here.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np

from fov3d.geometry.head_chart import chart_cells, chart_grid, head_angles_from_unit
from fov3d.reconstruction.measurement_memory import (
    valid_patch_measurements as _valid_patch_samples,
)


@dataclass
class HeadEvidence:
    """Cumulative head-centred depth evidence available from saved local patches."""

    depth_seen: np.ndarray
    target_depth_seen: np.ndarray
    other_depth_seen: np.ndarray
    nearest_instance: np.ndarray
    nearest_range_m: np.ndarray
    ambiguous_instance: np.ndarray
    sample_count: np.ndarray

    @classmethod
    def empty(cls, shape: tuple[int, int]) -> "HeadEvidence":
        return cls(
            depth_seen=np.zeros(shape, bool),
            target_depth_seen=np.zeros(shape, bool),
            other_depth_seen=np.zeros(shape, bool),
            nearest_instance=np.zeros(shape, np.int32),
            nearest_range_m=np.full(shape, np.inf, np.float32),
            ambiguous_instance=np.zeros(shape, bool),
            sample_count=np.zeros(shape, np.uint16),
        )


def add_head_patch(
    ev: HeadEvidence,
    patch: dict[str, np.ndarray],
    target_id: int,
    domain: dict[str, Any],
    grid_deg: float,
) -> dict[str, int]:
    """Accumulate all valid patch geometry in the head-origin spherical chart."""
    pts, ids, _m = _valid_patch_samples(patch)
    before = int(ev.depth_seen.sum())
    if len(pts) == 0:
        return {"valid_points": 0, "new_depth_cells": 0, "depth_cells": before}

    yaw, pitch = head_angles_from_unit(pts)
    y0, _y1, p0, _p1, h, w = chart_grid(domain, grid_deg)
    yy, xx, ok = chart_cells(yaw, pitch, y0, p0, grid_deg, h, w)
    pts = pts[ok]
    ids = ids[ok]
    yy = yy[ok].astype(np.int64)
    xx = xx[ok].astype(np.int64)
    if len(pts) == 0:
        return {"valid_points": 0, "new_depth_cells": 0, "depth_cells": before}
    rng = np.linalg.norm(pts, axis=1).astype(np.float64)

    flat = yy * w + xx
    uniq, counts = np.unique(flat, return_counts=True)
    cy, cx = np.divmod(uniq, w)
    ev.depth_seen[cy, cx] = True
    tgt_flat = np.unique(flat[ids == int(target_id)])
    if len(tgt_flat):
        ty, tx = np.divmod(tgt_flat, w)
        ev.target_depth_seen[ty, tx] = True
    oth_flat = np.unique(flat[ids != int(target_id)])
    if len(oth_flat):
        oy, ox = np.divmod(oth_flat, w)
        ev.other_depth_seen[oy, ox] = True
    old = ev.sample_count[cy, cx].astype(np.uint32)
    ev.sample_count[cy, cx] = np.minimum(
        old + counts.astype(np.uint32), np.iinfo(np.uint16).max
    ).astype(np.uint16)

    order = np.lexsort((ids, rng, flat))
    f = flat[order]
    first = np.r_[True, f[1:] != f[:-1]]
    sel = order[first]
    sy, sx = yy[sel], xx[sel]
    sr, si = rng[sel], ids[sel]

    by_cell: dict[int, set[int]] = defaultdict(set)
    for ff, iid in zip(flat.tolist(), ids.tolist()):
        by_cell[int(ff)].add(int(iid))
    for ff, vals in by_cell.items():
        if len(vals) > 1:
            ay, ax = divmod(ff, w)
            ev.ambiguous_instance[ay, ax] = True

    for y, x, r, iid in zip(sy.tolist(), sx.tolist(), sr.tolist(), si.tolist()):
        old_i = int(ev.nearest_instance[y, x])
        if old_i not in (0, int(iid)):
            ev.ambiguous_instance[y, x] = True
        old_r = float(ev.nearest_range_m[y, x])
        if (r < old_r) or (r == old_r and (old_i == 0 or int(iid) < old_i)):
            ev.nearest_range_m[y, x] = np.float32(r)
            ev.nearest_instance[y, x] = int(iid)

    after = int(ev.depth_seen.sum())
    return {
        "valid_points": int(len(pts)),
        "new_depth_cells": after - before,
        "depth_cells": after,
    }
