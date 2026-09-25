#!/usr/bin/env python3
"""Structural/unit checks for Partition-Graph Phase 3."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fov3d.scene import BoundaryKind, RegionKind, ScenePartitionGraph
from fov3d.experiments.classroom_partition.joint import (
    StereoOps,
    build_joint_graph,
    corridors_for_object,
    label_joint_regions,
    lift_joint_run,
    support_depth_from_map,
    update_controller_seen_any,
)


def _pts(yaws: np.ndarray, rng: float) -> np.ndarray:
    y = np.deg2rad(np.asarray(yaws, np.float64))
    return np.c_[rng * np.sin(y), np.zeros_like(y), -rng * np.cos(y)].astype(np.float32)


def _stub_ops() -> StereoOps:
    def rectification(c):
        w, h = map(int, c["image_size_wh"])
        eye = c["eyes"][0]
        k = np.asarray(eye["K"], float)
        return {
            "crop_xywh": [0, 0, w, h],
            "P1": np.c_[k, np.zeros(3)],
            "P2": np.c_[k, np.zeros(3)],
            "R1": np.eye(3),
            "R2": np.eye(3),
        }

    def support_mask(c, r, side):
        w, h = map(int, c["image_size_wh"])
        m = np.ones((h, w), bool)
        # Distinct unsupported corners exercise the support mask rather than a raw quad.
        m[:3, :4] = False
        m[-3:, -4:] = False
        return m

    return StereoOps(rectification=rectification, support_mask=support_mask)


def _calib() -> dict:
    return {
        "image_size_wh": [48, 32],
        "eyes": [
            {"K": [[220, 0, 23.5], [0, 220, 15.5], [0, 0, 1]], "R_hc": np.diag([-1.0, 1.0, -1.0]).tolist()},
            {"K": [[220, 0, 23.5], [0, 220, 15.5], [0, 0, 1]], "R_hc": np.diag([-1.0, 1.0, -1.0]).tolist()},
        ],
    }


def _fake_run(root: Path) -> Path:
    run = root / "run"
    (run / "bootstrap").mkdir(parents=True)
    objects = []
    for iid, name, xyz in (
        (7, "A", _pts(np.r_[np.linspace(-3.0, -1.5, 30), np.linspace(1.5, 3.0, 30)], 3.0)),
        (8, "B", _pts(np.linspace(-1.7, 1.7, 60), 2.0)),
    ):
        od = run / "objects" / f"instance_{iid:04d}"
        (od / "maps").mkdir(parents=True)
        (od / "acquisitions" / "fix_00").mkdir(parents=True)
        (od / "acquisitions" / "fix_00" / "calibration.json").write_text(json.dumps(_calib()))
        np.savez_compressed(od / "maps" / "fix_00.npz", xyz_h=xyz)
        seen = np.zeros((41, 101), bool)
        update_controller_seen_any(
            seen, _calib(), {"yaw": [-5.0, 5.0], "pitch": [-2.0, 2.0]}, 0.10,
            stereo_ops=_stub_ops(),
        )
        expected_never = int(seen.size - seen.sum())
        objects.append({
            "instance_id": iid,
            "object_name": name,
            "fixation_count": 1,
            "termination": "attention_complete",
            "trajectory": [{
                "step": 0,
                "cyclopean_decision": {
                    "audit": {"epistemic_state_counts": {"NEVER_OBSERVED": expected_never}}
                },
            }],
        })
    (run / "manifest.json").write_text(json.dumps({
        "control_complete": True,
        "total_fixations": 2,
        "objects": objects,
    }))
    (run / "bootstrap" / "seeds.json").write_text(json.dumps({
        "controller_domain_deg": {"yaw": [-5.0, 5.0], "pitch": [-2.0, 2.0]},
        "head_origin_w_m": [0, 0, 0],
        "head_R_wh": np.eye(3).tolist(),
    }))
    return run


def main() -> int:
    checked = failed = 0

    def check(name: str, cond: bool) -> None:
        nonlocal checked, failed
        checked += 1
        if cond:
            print(f"[partition-graph3-check] PASS {name}")
        else:
            failed += 1
            print(f"[partition-graph3-check] FAIL {name}")

    domain = {"yaw": [-5.0, 5.0], "pitch": [-2.0, 2.0]}
    a = support_depth_from_map(
        _pts(np.r_[np.linspace(-3.0, -1.5, 30), np.linspace(1.5, 3.0, 30)], 3.0),
        domain, 0.10, instance_id=7, object_name="A",
    )
    b = support_depth_from_map(
        _pts(np.linspace(-1.7, 1.7, 60), 2.0),
        domain, 0.10, instance_id=8, object_name="B",
    )
    check("support-layer-nonempty", bool(a.support.any() and b.support.any()))
    check("nearer-layer-depth", float(np.nanmin(b.depth_m)) < float(np.nanmin(a.depth_m)))

    # Explicit dual 8/4 digital topology: diagonal foreground connects, diagonal BASE does not.
    owner = np.array([[7, 0], [0, 7]], np.int32)
    depth = np.where(owner > 0, 3.0, np.inf).astype(np.float32)
    regions, objects, rc, _c2r, _r2c = label_joint_regions(owner, depth, {7: "A"})
    obj_regs = sum(r.kind is RegionKind.OBJECT_COMPONENT for r in regions.values())
    base_regs = sum(r.kind is RegionKind.BASE for r in regions.values())
    check("dual-connectivity-object-8", obj_regs == 1)
    check("dual-connectivity-base-4", base_regs == 2)

    obs = __import__("fov3d.scene", fromlist=["ObservationOverlay"]).ObservationOverlay([])
    g, st, diag = build_joint_graph(
        {7: a, 8: b}, {7: "A", 8: "B"}, obs, domain, 0.10,
        global_index=1, current_target=8, current_local_step=0,
    )
    from fov3d.experiments.classroom_partition.joint import attach_state_region_codes
    g = attach_state_region_codes(g, st["region_code"])
    check("joint-graph-valid", (g.validate() is None))
    check("boundary-interface-complete", diag["unencoded_interface_edges"] == 0 and diag["raster_interface_edges"] > 0)
    check("object-object-boundary-present", any(x.kind is BoundaryKind.OBJECT_OBJECT for x in g.boundaries.values()))
    check("base-not-other-objects", 0 < sum(r.kind is RegionKind.BASE for r in g.regions.values()) < len(g.regions))

    seen = np.zeros(st["owner_instance"].shape, bool)
    # Directly make the central chart observed for corridor composition.
    seen[:, st["owner_instance"].shape[1] // 3: 2 * st["owner_instance"].shape[1] // 3] = True
    rels = corridors_for_object(g, st, 7, seen, domain, 0.10)
    check("same-object-disconnected-pair", len(rels) >= 1)
    check("local-corridor-crosses-B", any(r["other_object_counts"].get("8", 0) > 0 for r in rels))
    check("local-corridor-has-evidence-composition", all(r["seen_cells"] + r["unseen_cells"] == r["corridor_cell_count_interior"] for r in rels))

    # Replay uses the rectified support mask, not the raw image quad.
    seen2 = np.zeros((41, 101), bool)
    ev = update_controller_seen_any(seen2, _calib(), domain, 0.10, stereo_ops=_stub_ops())
    check("controller-seen-any-replay-nonempty", 0 < ev["seen_cells"] < seen2.size)
    check("controller-seen-any-count-consistent", ev["unseen_cells"] == seen2.size - ev["seen_cells"])

    with tempfile.TemporaryDirectory(prefix="pg3-lift-") as td:
        root = Path(td)
        run = _fake_run(root)
        out = root / "lift"
        s = lift_joint_run(run, out, stereo_ops=_stub_ops())
        check("lift-two-global-states", len(s["global_states"]) == 2)
        check("lift-strict-evidence-match", s["controller_seen_any_validation"]["checks"] == 2 and s["controller_seen_any_validation"]["mismatches"] == 0)
        check("lift-posthoc-no-truth", s["posthoc_only"] and not s["controller_executed"] and not s["dense_truth_opened"])
        check("lift-read-path-isolation", all("evaluation_only" not in p and not p.endswith("evaluation.json") and not p.endswith("reachable_samples.npz") for p in s["read_paths"]))
        check("lift-scene-final-corridor", s["corridor_aggregate"]["scene_final_pairs"] >= 1 and s["corridor_aggregate"]["scene_final_pairs_crossing_other_object"] >= 1)
        check("lift-boundaries-complete", all((not x.get("map_present")) or x["boundary_diagnostics"]["unencoded_interface_edges"] == 0 for x in s["global_states"]))
        final = max(x["global_index"] for x in s["global_states"] if x.get("map_present"))
        gg = ScenePartitionGraph.load(out / "states" / f"global_{final:03d}" / "scene-model")
        check("lift-final-graph-valid", gg.validate() is None and len(gg.objects) == 2)

    print(f"[partition-graph3-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
