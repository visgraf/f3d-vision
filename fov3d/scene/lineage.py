"""Target-component lineage between consecutive scene-partition states.

Conceptual Core 7 lifts the accepted Phase-3/Phase-4 target-local component labelling and
overlap lineage into the scene layer without changing behavior.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from .model import ScenePartitionGraph


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
