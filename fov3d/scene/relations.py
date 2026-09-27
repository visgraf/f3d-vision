"""Generic scene-graph relation primitives.

Conceptual Core 9 lifts the accepted Phase-4 boundary depth-order relation primitive
(``boundary_depth_order`` with its helpers ``_region_object`` and ``_weighted_quantile``)
out of the Classroom relations adapter into the scene layer without changing behavior.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from .model import BoundaryKind, RegionKind, ScenePartitionGraph


def _region_object(graph: ScenePartitionGraph, rid: str) -> int | None:
    r = graph.regions[rid]
    if r.kind is not RegionKind.OBJECT_COMPONENT or r.object_id is None:
        return None
    return int(r.object_id)


def _weighted_quantile(values: list[float], weights: list[int], q: float) -> float | None:
    if not values:
        return None
    v = np.asarray(values, np.float64)
    w = np.asarray(weights, np.float64)
    order = np.argsort(v)
    v, w = v[order], w[order]
    c = np.cumsum(w)
    if c[-1] <= 0:
        return None
    return float(v[np.searchsorted(c, q * c[-1], side="left")])


def boundary_depth_order(graph: ScenePartitionGraph, target_id: int,
                         interveners: set[int]) -> dict[str, Any]:
    by: dict[int, dict[str, Any]] = {}
    for other in sorted(int(v) for v in interveners if int(v) != int(target_id)):
        tv = ov = edges = 0
        jumps: list[float] = []
        weights: list[int] = []
        chains = 0
        for b in graph.boundaries.values():
            if b.kind is not BoundaryKind.OBJECT_OBJECT:
                continue
            oa, ob = _region_object(graph, b.region_a), _region_object(graph, b.region_b)
            if {oa, ob} != {int(target_id), int(other)}:
                continue
            a_votes = int(b.attributes.get("nearer_region_a_votes", 0))
            b_votes = int(b.attributes.get("nearer_region_b_votes", 0))
            if oa == int(target_id):
                tv += a_votes; ov += b_votes
            else:
                tv += b_votes; ov += a_votes
            nedge = int(b.attributes.get("interface_edge_count", 0))
            edges += nedge
            if "depth_jump_median_m" in b.attributes and nedge > 0:
                jumps.append(float(b.attributes["depth_jump_median_m"]))
                weights.append(nedge)
            chains += 1
        den = tv + ov
        by[str(other)] = {
            "boundary_chain_count": int(chains),
            "interface_edge_count": int(edges),
            "target_nearer_votes": int(tv),
            "intervener_nearer_votes": int(ov),
            "intervener_nearer_vote_fraction": None if den == 0 else float(ov / den),
            "depth_order_confidence_abs_vote_balance": None if den == 0 else float(abs(ov - tv) / den),
            "depth_jump_interface_weighted_median_m": _weighted_quantile(jumps, weights, 0.5),
            "depth_jump_interface_weighted_p90_m": _weighted_quantile(jumps, weights, 0.9),
        }
    return by
