#!/usr/bin/env python3
"""Structural/unit checks for Partition-Graph Phase 7."""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from fov3d.experiments.classroom_partition.benchmark import build_epistemic_partition
from fov3d.experiments.classroom_partition.incidental import HeadEvidence
from fov3d.experiments.classroom_partition.prefix_benchmark import (
    _angles_to_codes,
    _candidate_capture_metrics,
    _memory_state,
    _partition_signature,
)


def main() -> int:
    checked = failed = 0
    def check(name: str, cond: bool) -> None:
        nonlocal checked, failed
        checked += 1; failed += int(not cond)
        print(f"[partition-graph7-check] {'PASS' if cond else 'FAIL'} {name}")

    shape = (9, 9)
    domain = {"yaw": [-0.4, 0.4], "pitch": [-0.4, 0.4]}
    target = np.zeros(shape, bool); target[3:6, 1:3] = True; target[3:6, 6:8] = True
    local = {
        "target_support": target,
        "owner_instance": np.where(target, 7, 0).astype(np.int32),
        "nearest_instance": np.where(target, 7, 0).astype(np.int32),
        "nearest_range_m": np.where(target, 3.0, np.inf).astype(np.float32),
        "ambiguous_instance": np.zeros(shape, bool),
        "depth_seen": target.copy(),
        "sample_count": target.astype(np.uint16),
        "seen_any": np.ones(shape, bool),
    }
    mem = HeadEvidence.empty(shape)
    mem.depth_seen[:] = local["depth_seen"]
    mem.nearest_instance[:] = local["nearest_instance"]
    mem.nearest_range_m[:] = local["nearest_range_m"]
    mem.sample_count[:] = local["sample_count"]
    # Earlier-target memory splits the large unknown and also contains one direct
    # target sample that the current target map has not persisted.
    mem.depth_seen[4, 4] = True; mem.nearest_instance[4, 4] = 8; mem.nearest_range_m[4, 4] = 2.0
    mem.depth_seen[1, 4] = True; mem.nearest_instance[1, 4] = 7; mem.nearest_range_m[1, 4] = 3.0
    global_state = _memory_state(local, mem)
    check("local-depth-subset-global", not np.any(local["depth_seen"] & ~global_state["depth_seen"]))

    common = dict(target_id=7, target_name="A", all_target_ids={7,8}, domain=domain, grid_deg=0.1, gazes_deg=[(0,0)])
    la, lr, le, _ = build_epistemic_partition(local, **common)
    ga, gr, ge, _ = build_epistemic_partition(global_state, **common)
    ls = _partition_signature(la, lr, le); gs = _partition_signature(ga, gr, ge)
    check("global-other-surface-created", any(r["kind"] == "OTHER_SURFACE" and r.get("instance_id") == 8 for r in gr))
    check("global-target-evidence-unmapped-created", any(r["kind"] == "TARGET_EVIDENCE_UNMAPPED" for r in gr))
    check("global-unknown-not-larger", gs["largest_unknown_cells"] <= ls["largest_unknown_cells"])
    check("target-evidence-is-not-candidate", all(not r["candidate"] for r in gr if r["kind"] == "TARGET_EVIDENCE_UNMAPPED"))
    check("other-surface-remains-candidate", all(r["candidate"] for r in gr if r["kind"] == "OTHER_SURFACE"))

    # Region lookup / truth-evaluation helpers are deterministic and chart aligned.
    codes, ok = _angles_to_codes(np.array([[0.0, 0.0], [0.4, 0.4]], float), ga["region_code"], domain, 0.1)
    check("angle-code-mapping", bool(ok.all()) and np.all(codes > 0))
    met, miss_by = _candidate_capture_metrics(codes, gr, shape[0] * shape[1])
    check("candidate-metrics-account-codes", sum(miss_by.values()) == 2)
    check("candidate-positive-count-bounded", 0 <= met["truth_positive_candidate_regions"] <= gs["candidate_count"])
    check("partition-all-cells-classified", np.all(la["region_code"] > 0) and np.all(ga["region_code"] > 0))
    check("global-memory-can-change-topology", not np.array_equal(la["region_code"], ga["region_code"]))
    check("candidate-kinds-preserved", all(r["kind"] in {"UNKNOWN", "OTHER_SURFACE"} for r in gr if r["candidate"]))

    print(f"[partition-graph7-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
