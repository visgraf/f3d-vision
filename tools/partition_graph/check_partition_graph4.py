#!/usr/bin/env python3
"""Structural/unit checks for Partition-Graph Phase 4."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fov3d.scene import ObservationOverlay
from fov3d.experiments.classroom_partition.joint import (
    SupportLayer,
    StereoOps,
    _lineage,
    build_joint_graph,
    corridors_for_object,
)
from fov3d.experiments.classroom_partition.relations import (
    EVIDENCE_CLASS_NAMES,
    FineEvidence,
    add_patch_observation,
    annotate_corridor,
    component_lineage,
    evidence_class_counts,
    evidence_class_raster,
    relation_origin,
)


def _layer(iid: int, name: str, support: np.ndarray, depth: float) -> SupportLayer:
    dep = np.full(support.shape, np.inf, np.float32)
    dep[np.asarray(support, bool)] = float(depth)
    return SupportLayer(iid, name, np.asarray(support, bool), dep, np.empty((0, 2), np.int32), int(np.sum(support)))


def _calib() -> dict:
    return {
        "image_size_wh": [9, 9],
        "eyes": [
            {"K": [[50, 0, 4], [0, 50, 4], [0, 0, 1]], "R_hc": np.diag([-1.0, 1.0, -1.0]).tolist()},
            {"K": [[50, 0, 4], [0, 50, 4], [0, 0, 1]], "R_hc": np.diag([-1.0, 1.0, -1.0]).tolist()},
        ],
    }


def _stub_ops() -> StereoOps:
    def rectification(c):
        k = np.asarray(c["eyes"][0]["K"], float)
        return {"crop_xywh": [0, 0, 9, 9], "P1": np.c_[k, np.zeros(3)], "P2": np.c_[k, np.zeros(3)], "R1": np.eye(3), "R2": np.eye(3)}
    def support_mask(c, r, side):
        return np.ones((9, 9), bool)
    return StereoOps(rectification=rectification, support_mask=support_mask)


def main() -> int:
    checked = failed = 0
    def check(name: str, cond: bool) -> None:
        nonlocal checked, failed
        checked += 1
        if cond:
            print(f"[partition-graph4-check] PASS {name}")
        else:
            failed += 1
            print(f"[partition-graph4-check] FAIL {name}")

    # The exact Phase-3 bug: stable target-local component labels must remain persistent
    # even when a graph-global code would have been something else.
    a = np.zeros((5, 5), np.int32); a[1:4, 1:4] = 1
    lin = _lineage(a, a.copy())
    check("lineage-stable-no-birth-death", lin["births"] == 0 and lin["deaths"] == 0 and lin["persistent_links"] == 1)

    b = np.zeros((5, 5), np.int32); b[1:4, 1] = 1; b[1:4, 3] = 2
    birth = component_lineage(a, b)
    check("lineage-explicit-change-detected", birth["births"] + birth["splits"] + birth["deaths"] > 0)

    # Fine evidence: saved left instance ids + valid mask produce target/nontarget/depth masks.
    ev = FineEvidence.empty((11, 11))
    ids = np.full((9, 9), 7, np.int32); ids[:, :2] = 8
    valid = np.zeros((9, 9), bool); valid[3:6, 3:6] = True
    patch = {"instance_id": ids, "valid": valid}
    delta = add_patch_observation(ev, _calib(), patch, 7, {"yaw": [-5, 5], "pitch": [-5, 5]}, 1.0, stereo_ops=_stub_ops())
    check("fine-evidence-left-target", delta["left_target_cells"] > 0)
    check("fine-evidence-left-nontarget", delta["left_nontarget_cells"] > 0)
    check("fine-evidence-target-depth", 0 < delta["target_depth_valid_cells"] <= delta["left_target_cells"])
    seen = np.ones((11, 11), bool)
    cls = evidence_class_raster(seen, ev)
    counts = evidence_class_counts(cls)
    check("evidence-classes-partition-chart", sum(counts.values()) == cls.size and set(counts) == set(EVIDENCE_CLASS_NAMES))
    check("evidence-class-depth-present", counts["TARGET_DEPTH_VALID"] > 0)

    # Synthetic ownership cut: target own support is connected, but a nearer B column
    # wins the middle and splits A in the frontmost joint partition.
    shape = (9, 9)
    sup_a = np.zeros(shape, bool); sup_a[3:6, 1:8] = True
    sup_b = np.zeros(shape, bool); sup_b[3:6, 4] = True
    la = _layer(7, "A", sup_a, 3.0); lb = _layer(8, "B", sup_b, 2.0)
    domain = {"yaw": [-0.4, 0.4], "pitch": [-0.4, 0.4]}
    g, st, _ = build_joint_graph({7: la, 8: lb}, {7: "A", 8: "B"}, ObservationOverlay([]), domain, 0.1,
                                  global_index=0, current_target=7, current_local_step=0)
    rels = corridors_for_object(g, st, 7, np.ones(shape, bool), domain, 0.1)
    check("ownership-cut-fixture-has-relation", len(rels) >= 1)
    if rels:
        origin, ca, cb = relation_origin(g, st, rels[0], la.support)
        check("ownership-cut-typed", origin == "ownership_cut" and ca == cb)
        fine = FineEvidence.empty(shape)
        ann = annotate_corridor(g, st, rels[0], la, 7, np.ones(shape, bool), fine)
        check("ownership-cut-margin-positive", ann["ownership_margin"]["count"] > 0 and ann["ownership_margin"]["median_m"] > 0)
        check("ownership-cut-depth-order-present", "8" in ann["boundary_depth_order"])
    else:
        check("ownership-cut-typed", False); check("ownership-cut-margin-positive", False); check("ownership-cut-depth-order-present", False)

    # Synthetic own-support gap: two A islands, no ownership cut.
    sup2 = np.zeros(shape, bool); sup2[3:6, 1:3] = True; sup2[3:6, 6:8] = True
    l2 = _layer(7, "A", sup2, 3.0)
    g2, st2, _ = build_joint_graph({7: l2}, {7: "A"}, ObservationOverlay([]), domain, 0.1,
                                    global_index=0, current_target=7, current_local_step=0)
    rel2 = corridors_for_object(g2, st2, 7, np.ones(shape, bool), domain, 0.1)
    check("own-support-gap-fixture-has-relation", len(rel2) == 1)
    if rel2:
        origin2, ca2, cb2 = relation_origin(g2, st2, rel2[0], l2.support)
        check("own-support-gap-typed", origin2 == "own_support_gap" and ca2 != cb2)
    else:
        check("own-support-gap-typed", False)

    # Explicit invariants on type semantics.
    check("relation-origin-domain", all(x in {"ownership_cut", "own_support_gap"} for x in [origin if rels else "ownership_cut", origin2 if rel2 else "own_support_gap"]))

    print(f"[partition-graph4-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
