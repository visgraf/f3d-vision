#!/usr/bin/env python3
"""Structural/unit checks for Partition-Graph Phase 2."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fov3d.scene import (
    BoundaryChain, BoundaryKind, FootprintEye, PartitionRegion, RegionKind, ScenePartitionGraph,
)
from fov3d.scene.synthetic import build_synthetic_occlusion_case
from fov3d.experiments.classroom_partition import lift_run


def _fake_run(root: Path) -> Path:
    run = root / "run"
    (run / "bootstrap").mkdir(parents=True)
    od = run / "objects" / "instance_0007"
    (od / "maps").mkdir(parents=True)
    (od / "acquisitions" / "fix_00").mkdir(parents=True)
    (od / "acquisitions" / "fix_01").mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({
        "control_complete": True,
        "objects": [{"instance_id": 7, "object_name": "fake", "fixation_count": 2, "termination": "attention_complete"}],
    }))
    (run / "bootstrap" / "seeds.json").write_text(json.dumps({
        "controller_domain_deg": {"yaw": [-5.0, 5.0], "pitch": [-4.0, 4.0]},
        "head_origin_w_m": [0.0, 0.0, 0.0], "head_R_wh": np.eye(3).tolist(),
    }))
    calib = {
        "image_size_wh": [64, 48],
        "eyes": [
            {"K": [[55, 0, 31.5], [0, 55, 23.5], [0, 0, 1]], "R_hc": np.eye(3).tolist()},
            {"K": [[55, 0, 31.5], [0, 55, 23.5], [0, 0, 1]], "R_hc": np.eye(3).tolist()},
        ],
    }
    for i in range(2):
        (od / "acquisitions" / f"fix_{i:02d}" / "calibration.json").write_text(json.dumps(calib))
    def pts(yaws):
        y = np.deg2rad(np.asarray(yaws))
        return np.c_[2*np.sin(y), np.zeros_like(y), -2*np.cos(y)].astype(np.float32)
    # Two separated strips at step 0; step 1 bridges them.
    np.savez_compressed(od / "maps" / "fix_00.npz", xyz_h=pts(np.r_[np.linspace(-3,-1.8,20), np.linspace(1.8,3,20)]))
    np.savez_compressed(od / "maps" / "fix_01.npz", xyz_h=pts(np.linspace(-3,3,90)))
    return run


def main() -> int:
    checked = failed = 0
    def check(name, cond):
        nonlocal checked, failed
        checked += 1
        if cond:
            print(f"[partition-graph2-check] PASS {name}")
        else:
            failed += 1
            print(f"[partition-graph2-check] FAIL {name}")

    g = build_synthetic_occlusion_case()
    g.validate()
    check("synthetic-valid", True)
    check("footprint-eye-has-no-unobserved", "unobserved" not in {x.value for x in FootprintEye})
    check("optional-geometry-present", all(
        b.world_xyz is not None and b.normal_a is not None and b.normal_b is not None and b.depth_a is not None and b.depth_b is not None
        for b in g.boundaries.values()
    ))
    with tempfile.TemporaryDirectory(prefix="pg2-model-") as td:
        g.save(td)
        h = ScenePartitionGraph.load(td)
        ok = True
        for bid in g.boundaries:
            a, b = g.boundaries[bid], h.boundaries[bid]
            for field in ("sphere_xyz", "world_xyz", "normal_a", "normal_b", "depth_a", "depth_b"):
                ok &= np.array_equal(getattr(a, field), getattr(b, field))
        check("roundtrip-geometry-bit-exact", ok)
        meta = json.loads((Path(td) / "graph.json").read_text())
        check("format-v2", meta["format"] == "f3d-vision-scene-partition-v2")

    # Invalid non-unit directions must be rejected, not silently normalized.
    b0 = next(iter(g.boundaries.values()))
    try:
        bad = BoundaryChain("bad", b0.region_a, b0.region_b, b0.sphere_xyz * 2.0)
        bad.validate(); ok = False
    except ValueError:
        ok = True
    check("reject-nonunit-sphere", ok)

    # Occlusion attributes must refer to the chain endpoints.
    try:
        bad = BoundaryChain("bad-occ", "A-left", "B", b0.sphere_xyz, kind=BoundaryKind.OCCLUSION,
                            attributes={"front_region": "base", "back_region": "A-left"})
        bad.validate(); ok = False
    except ValueError:
        ok = True
    check("reject-bad-occlusion-endpoints", ok)

    # Same-object adjacent faces are deliberately legal when a real boundary relation exists.
    same = BoundaryChain("self-occ", "A-left", "A-right", b0.sphere_xyz, kind=BoundaryKind.OCCLUSION,
                         attributes={"front_region": "A-left", "back_region": "A-right"})
    try:
        same.validate(); ok = True
    except ValueError:
        ok = False
    check("same-object-boundary-allowed", ok)

    # ndarray-bearing dataclasses must not expose broken value equality/hash semantics.
    try:
        _ = (b0 == b0); eq_ok = True
    except Exception:
        eq_ok = False
    try:
        hash(b0); hash_ok = False
    except TypeError:
        hash_ok = True
    check("safe-dataclass-equality", eq_ok)
    check("array-dataclasses-unhashable", hash_ok)

    with tempfile.TemporaryDirectory(prefix="pg2-lift-") as td:
        root = Path(td)
        run = _fake_run(root)
        out = root / "lift"
        s = lift_run(run, out, grid_deg=0.10)
        check("lift-posthoc", s["posthoc_only"] and not s["controller_executed"] and not s["dense_truth_opened"])
        check("lift-two-graphs", s["aggregate"]["graphs_written"] == 2)
        o = s["objects"][0]
        check("lift-observation-accumulates", o["fixations"][0]["observation_footprints"] == 2 and o["fixations"][1]["observation_footprints"] == 4)
        check("lift-topology-merge", o["fixations"][0]["object_components"] >= 2 and o["fixations"][1]["object_components"] == 1)
        check("lift-no-truth-path", all("evaluation_only" not in p and not p.endswith("evaluation.json") and not p.endswith("reachable_samples.npz") for p in s["read_paths"]))
        g2 = ScenePartitionGraph.load(out / "objects" / "instance_0007" / "fix_01" / "scene-model")
        check("lift-graph-valid", bool(g2.regions) and len(g2.observations.footprints) == 4)

    print(f"[partition-graph2-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
