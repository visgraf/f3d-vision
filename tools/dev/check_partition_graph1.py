#!/usr/bin/env python3
"""Deterministic structural/unit check for Partition-Graph Phase 1."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fov3d.scene import RegionKind, ScenePartitionGraph, unit_to_lonlat
from fov3d.scene.synthetic import build_synthetic_occlusion_case


def main() -> int:
    checked = 0
    failed = 0

    def check(name: str, cond: bool) -> None:
        nonlocal checked, failed
        checked += 1
        if cond:
            print(f"[partition-graph1-check] PASS {name}")
        else:
            failed += 1
            print(f"[partition-graph1-check] FAIL {name}")

    g = build_synthetic_occlusion_case()
    g.validate()
    check("synthetic-valid", True)
    check("no-void-region-kind", all(r.kind in (RegionKind.OBJECT_COMPONENT, RegionKind.BASE) for r in g.regions.values()))
    check("two-components-one-object", len(g.object_components("A")) == 2)
    check("dual-from-boundaries", len(g.dual_edges()) == len(g.boundaries) == 4)
    check("observation-overlay-separate", len(g.observations.footprints) == 1)
    check("summary-disconnected", g.summary()["objects_with_multiple_visible_components"] == 1)

    lonlat = unit_to_lonlat(next(iter(g.boundaries.values())).sphere_xyz)
    check("sphere-roundtrip-finite", bool(np.isfinite(lonlat).all()))

    with tempfile.TemporaryDirectory(prefix="pg1-") as td:
        g.save(td)
        check("graph-json-written", (Path(td) / "graph.json").is_file())
        check("arrays-npz-written", (Path(td) / "arrays.npz").is_file())
        h = ScenePartitionGraph.load(td)
        check("roundtrip-summary", h.summary() == g.summary())
        check("roundtrip-dual", h.dual_edges() == g.dual_edges())
        meta = json.loads((Path(td) / "graph.json").read_text())
        check("format-version", meta["format"] == "f3d-vision-scene-partition-v2")

    # Negative invariant: base must not masquerade as an object.
    from fov3d.scene.model import PartitionRegion
    try:
        PartitionRegion("bad", RegionKind.BASE, object_id="X").validate()
        negative_ok = False
    except ValueError:
        negative_ok = True
    check("negative-base-object-id", negative_ok)

    print(f"[partition-graph1-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
