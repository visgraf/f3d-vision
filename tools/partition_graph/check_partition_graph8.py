#!/usr/bin/env python3
"""Structural/unit checks for Partition-Graph Phase 8."""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from fov3d.experiments.classroom_partition.benchmark import build_epistemic_partition
from fov3d.experiments.classroom_partition.incidental import HeadEvidence
from fov3d.experiments.classroom_partition.integration import (
    cross_target_novelty,
    effective_target_geometry,
)
from fov3d.experiments.classroom_partition.joint import support_depth_from_map
from fov3d.experiments.classroom_partition.prefix_benchmark import _memory_state


def _xyz(yaw_deg: float, pitch_deg: float, r: float) -> np.ndarray:
    y, p = np.deg2rad([yaw_deg, pitch_deg])
    return np.array([r*np.sin(y)*np.cos(p), r*np.sin(p), -r*np.cos(y)*np.cos(p)], np.float32)


def main() -> int:
    checked = failed = 0
    def check(name: str, cond: bool) -> None:
        nonlocal checked, failed
        checked += 1; failed += int(not cond)
        print(f"[partition-graph8-check] {'PASS' if cond else 'FAIL'} {name}")

    domain = {"yaw": [-0.5, 0.5], "pitch": [-0.3, 0.3]}
    # Historical target A has two samples; an earlier look at B measured a third A sample.
    hist = np.vstack((_xyz(-0.3, 0, 3.0), _xyz(-0.2, 0, 3.0)))
    cross = np.vstack((_xyz(0.25, 0, 3.0),))
    eff = effective_target_geometry(hist, cross)
    check("effective-union-count", len(eff) == 3)
    check("inputs-not-mutated", len(hist) == 2 and len(cross) == 1)
    nov = cross_target_novelty(hist, cross)
    check("cross-target-novel-beyond-12mm", nov["novel_beyond_12mm"] == 1)

    near = hist[0:1] + np.array([[0.001, 0, 0]], np.float32)
    nov2 = cross_target_novelty(hist, near)
    check("cross-target-redundant-within-12mm", nov2["represented_within_12mm"] == 1)

    layer_hist = support_depth_from_map(hist, domain, 0.1, instance_id=7, object_name="A")
    layer_eff = support_depth_from_map(eff, domain, 0.1, instance_id=7, object_name="A")
    check("integration-expands-support", int(layer_eff.support.sum()) > int(layer_hist.support.sum()))

    shape = layer_eff.support.shape
    local_state = {
        "target_support": layer_hist.support.copy(),
        "owner_instance": np.where(layer_hist.support, 7, 0).astype(np.int32),
        "nearest_instance": np.where(layer_hist.support, 7, 0).astype(np.int32),
        "nearest_range_m": np.where(layer_hist.support, 3.0, np.inf).astype(np.float32),
        "ambiguous_instance": np.zeros(shape, bool),
        "depth_seen": layer_hist.support.copy(),
        "sample_count": layer_hist.support.astype(np.uint16),
        "seen_any": np.ones(shape, bool),
    }
    mem = HeadEvidence.empty(shape)
    mem.depth_seen[:] = local_state["depth_seen"]
    mem.nearest_instance[:] = local_state["nearest_instance"]
    mem.nearest_range_m[:] = local_state["nearest_range_m"]
    mem.sample_count[:] = local_state["sample_count"]
    # Put earlier cross-target A evidence in the global memory at its chart cell.
    yaw = 0.25; pitch = 0.0
    x = int(round((yaw - domain["yaw"][0]) / 0.1))
    y = int(round((pitch - domain["pitch"][0]) / 0.1))
    mem.depth_seen[y, x] = True
    mem.nearest_instance[y, x] = 7
    mem.nearest_range_m[y, x] = 3.0
    mem.sample_count[y, x] = 1
    gs = _memory_state(local_state, mem)
    _, _r0, _e0, d0 = build_epistemic_partition(gs, target_id=7, target_name="A", all_target_ids={7,8}, domain=domain, grid_deg=.1, gazes_deg=[(0,0)])
    check("historical-global-has-unmapped-target-evidence", d0["target_evidence_unmapped_cells"] > 0)
    gs2 = dict(gs); gs2["target_support"] = layer_eff.support
    _a1, r1, _e1, d1 = build_epistemic_partition(gs2, target_id=7, target_name="A", all_target_ids={7,8}, domain=domain, grid_deg=.1, gazes_deg=[(0,0)])
    check("integrated-removes-unmapped-target-evidence", d1["target_evidence_unmapped_cells"] == 0)
    check("integrated-still-classifies-all-cells", sum(int(r["cell_count"]) for r in r1) == int(np.prod(shape)))
    check("no-new-policy-field", all("score" not in r and "priority" not in r for r in r1))
    check("candidate-domain-unchanged", all(r["kind"] in {"UNKNOWN","OTHER_SURFACE"} for r in r1 if r["candidate"]))

    print(f"[partition-graph8-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
