"""Consistency between a scene-partition graph and its state region-code raster.

Conceptual Core 8 lifts the accepted Phase-3 graph/raster state-code check into the scene
layer without changing behavior. The historical name ``attach_state_region_codes`` is kept
unchanged: the function validates and attaches nothing. A rename is deferred to a later
compatibility cleanup.
"""
from __future__ import annotations

import numpy as np

from .model import ScenePartitionGraph


def attach_state_region_codes(graph: ScenePartitionGraph, region_code: np.ndarray) -> ScenePartitionGraph:
    """Validate the construction-time raster code carried by every region."""
    codes = {int(c) for c in np.unique(region_code)}
    graph_codes = {int(r.attributes.get("state_region_code", -1)) for r in graph.regions.values()}
    if -1 in graph_codes or graph_codes != codes:
        raise RuntimeError(f"graph/raster region-code mismatch: graph={sorted(graph_codes)} raster={sorted(codes)}")
    graph.validate()
    return graph
