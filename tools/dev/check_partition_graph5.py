#!/usr/bin/env python3
"""Structural/unit checks for Partition-Graph Phase 5."""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from fov3d.scene import ObservationOverlay
from fov3d.experiments.classroom_partition.incidental import (
    HeadEvidence, add_head_patch, annotate_head_relation, reconstruction_status,
)
from fov3d.experiments.classroom_partition.joint import SupportLayer, build_joint_graph


def _xyz(yaw_deg: float, pitch_deg: float, r: float) -> np.ndarray:
    y, p = np.deg2rad([yaw_deg, pitch_deg])
    return np.array([r*np.sin(y)*np.cos(p), r*np.sin(p), -r*np.cos(y)*np.cos(p)], np.float32)


def _layer(iid: int, name: str, support: np.ndarray, depth: float) -> SupportLayer:
    d = np.full(support.shape, np.inf, np.float32); d[support] = depth
    return SupportLayer(iid, name, support, d, np.empty((0,2), np.int32), int(support.sum()))


def main() -> int:
    checked = failed = 0
    def check(name: str, cond: bool) -> None:
        nonlocal checked, failed
        checked += 1
        print(f"[partition-graph5-check] {'PASS' if cond else 'FAIL'} {name}")
        failed += int(not cond)

    domain = {"yaw": [-0.4, 0.4], "pitch": [-0.4, 0.4]}
    shape = (9,9)
    ev = HeadEvidence.empty(shape)
    xyz = np.full((3,3,3), np.nan, np.float32)
    ids = np.zeros((3,3), np.int32); valid = np.zeros((3,3), bool)
    xyz[1,1] = _xyz(0.0, 0.0, 2.0); ids[1,1] = 8; valid[1,1] = True
    xyz[1,2] = _xyz(0.1, 0.0, 3.0); ids[1,2] = 7; valid[1,2] = True
    delta = add_head_patch(ev, {"xyz_h":xyz,"instance_id":ids,"valid":valid}, 7, domain, 0.1)
    check("head-patch-valid-points", delta["valid_points"] == 2)
    check("head-patch-target-and-other", ev.target_depth_seen.any() and ev.other_depth_seen.any())
    check("head-patch-nearest-instance", 8 in set(ev.nearest_instance.ravel().tolist()))

    sup = np.zeros(shape, bool); sup[3:6,1:3] = True; sup[3:6,6:8] = True
    la = _layer(7,"A",sup,3.0)
    g, st, _ = build_joint_graph({7:la},{7:"A"},ObservationOverlay([]),domain,0.1,global_index=0,current_target=7,current_local_step=0)
    # Corridor through the middle cell; add incidental B depth there.
    mem = HeadEvidence.empty(shape)
    mem.depth_seen[4,4]=True; mem.other_depth_seen[4,4]=True; mem.nearest_instance[4,4]=8; mem.nearest_range_m[4,4]=2.0
    rel = {"relation_origin":"own_support_gap","region_a":g.objects["7"].region_ids[0],"region_b":g.objects["7"].region_ids[1],
           "corridor_yx":[[4,2],[4,3],[4,4],[4,5],[4,6]],"endpoint_gap_deg":0.4}
    seen = np.ones(shape,bool)
    rr = annotate_head_relation(rel,g,st["owner_instance"],la.support,seen,mem,7,{7,8})
    check("true-gap-detected", rr["true_gap_cell_count"] == 3)
    check("incidental-other-depth-class", rr["head_evidence_class_counts"]["INCIDENTAL_OTHER_DEPTH"] == 1)
    check("remaining-seen-no-depth", rr["head_evidence_class_counts"]["SEEN_NO_HEAD_DEPTH"] == 2)
    check("relation-unresolved", rr["has_unresolved_true_gap"])
    check("target-depth-not-in-gap", rr["head_target_depth_in_true_gap_cells"] == 0)
    check("later-target-status", rr["head_observed_instance_status"].get("targeted_later",{}).get("8",0) == 1)
    check("mapped-status-helper", reconstruction_status(7,g,{7,8}) == "mapped_now")
    check("never-targeted-helper", reconstruction_status(99,g,{7,8}) == "never_targeted")

    # If B is already in the joint partition, its owned gap cell becomes MAPPED_OTHER.
    sb = np.zeros(shape,bool); sb[4,4]=True
    lb = _layer(8,"B",sb,2.0)
    g2, st2, _ = build_joint_graph({7:la,8:lb},{7:"A",8:"B"},ObservationOverlay([]),domain,0.1,global_index=0,current_target=7,current_local_step=0)
    # Reuse A's two joint components.
    ar = g2.objects["7"].region_ids
    rel2 = dict(rel, region_a=ar[0], region_b=ar[1])
    rr2 = annotate_head_relation(rel2,g2,st2["owner_instance"],la.support,seen,mem,7,{7,8})
    check("mapped-other-precedence", rr2["head_evidence_class_counts"]["MAPPED_OTHER"] == 1)

    print(f"[partition-graph5-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
