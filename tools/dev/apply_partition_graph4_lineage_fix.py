#!/usr/bin/env python3
"""Apply the narrow Phase-4 lineage bug fix to joint.py.

The Phase-3 package accidentally compared target-local component labels with
state-global region codes. This script performs an exact source replacement and
refuses to edit an unexpected file.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "fov3d/experiments/classroom_partition/joint.py"

OLD = '''def _lineage(prev_rc: np.ndarray | None, curr_rc: np.ndarray, graph: ScenePartitionGraph, target_id: int) -> dict[str, Any]:
    """Classify births/merges/splits/deaths by actual component-cell overlap."""
    curr_codes = [
        int(r.attributes["state_region_code"])
        for r in graph.object_components(str(target_id))
    ] if str(target_id) in graph.objects else []
    if prev_rc is None:
        return {
            "initial": True,
            "births": len(curr_codes),
            "merges": 0,
            "splits": 0,
            "deaths": 0,
            "persistent_links": 0,
        }
    prev_codes = sorted(int(v) for v in np.unique(prev_rc) if int(v) > 0)
    # prev_rc passed here is target-only component labels: 0 background, >0 components.
    parents: dict[int, set[int]] = {c: set() for c in curr_codes}
    children: dict[int, set[int]] = {c: set() for c in prev_codes}
    for pc in prev_codes:
        pm = prev_rc == pc
        for cc in curr_codes:
            cm = curr_rc == cc
            if np.any(pm & cm):
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
'''

NEW = '''def _lineage(prev_rc: np.ndarray | None, curr_rc: np.ndarray) -> dict[str, Any]:
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
'''

OLD_CALL = '''            lineage = _lineage(previous_target_labels.get(iid), current_target_labels, graph, iid)
'''
NEW_CALL = '''            lineage = _lineage(previous_target_labels.get(iid), current_target_labels)
'''


def main() -> int:
    text = PATH.read_text(encoding="utf-8")
    if NEW in text and NEW_CALL in text:
        print("[partition-graph4-lineage-fix] already applied")
        return 0
    if OLD not in text:
        raise RuntimeError("expected Phase-3 _lineage source was not found; refusing to edit")
    if OLD_CALL not in text:
        raise RuntimeError("expected Phase-3 _lineage call was not found; refusing to edit")
    text = text.replace(OLD, NEW, 1).replace(OLD_CALL, NEW_CALL, 1)
    PATH.write_text(text, encoding="utf-8")
    print("[partition-graph4-lineage-fix] APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
