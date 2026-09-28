#!/usr/bin/env python3
"""Fail-capable checks for Conceptual Core 1 measurement-memory extraction."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fov3d.reconstruction.measurement_memory import (
    InstanceMeasurementMemory,
    MeasurementSnapshot,
    effective_target_geometry,
    valid_patch_measurements,
)


def _patch(xyz, ids, valid):
    return {
        "xyz_h": np.asarray(xyz, np.float64),
        "instance_id": np.asarray(ids, np.int32),
        "valid": np.asarray(valid, bool),
    }


def main() -> int:
    checked = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal checked, failed
        checked += 1
        if condition:
            print(f"[conceptual-core1-check] PASS {name}")
        else:
            failed += 1
            print(f"[conceptual-core1-check] FAIL {name}")

    p = _patch(
        [
            [[1, 0, 0], [2, 0, 0], [np.nan, 0, 0]],
            [[3, 0, 0], [4, 0, 0], [5, 0, 0]],
        ],
        [[7, 0, 7], [8, 7, -1]],
        [[1, 1, 1], [1, 0, 1]],
    )
    xyz, ids, mask = valid_patch_measurements(p)
    check("valid filtering count", len(xyz) == 2)
    check("valid filtering order", ids.tolist() == [7, 8])
    check("valid filtering raster mask", int(mask.sum()) == 2)

    mem = InstanceMeasurementMemory()
    routed = mem.append_patch(
        p, source_global_index=3, source_active_target_id=99
    )
    check("multi-instance routing counts", routed == {7: 1, 8: 1})
    check("instance ids", mem.instance_ids() == (7, 8))

    p2 = _patch(
        [[[6, 0, 0], [6, 0, 0], [7, 0, 0]]],
        [[7, 7, 9]],
        [[1, 1, 1]],
    )
    mem.append_patch(p2, source_global_index=4, source_active_target_id=7)
    s7 = mem.snapshot(7)
    check(
        "provenance alignment",
        s7.source_global_index.tolist() == [3, 4, 4]
        and s7.source_active_target_id.tolist() == [99, 7, 7],
    )
    check(
        "active-target independence",
        s7.cross_target_mask(7).tolist() == [True, False, False],
    )
    check(
        "duplicate and insertion order",
        s7.xyz_h.tolist()
        == [[1.0, 0.0, 0.0], [6.0, 0.0, 0.0], [6.0, 0.0, 0.0]],
    )
    s8 = mem.snapshot(8)
    check(
        "snapshot isolation",
        len(s8.xyz_h) == 1
        and s8.xyz_h.tolist() == [[3.0, 0.0, 0.0]]
        and s8.source_active_target_id.tolist() == [99],
    )
    check(
        "snapshot arrays read-only",
        not s7.xyz_h.flags.writeable
        and not s7.source_global_index.flags.writeable
        and not s7.source_active_target_id.flags.writeable,
    )

    historical = np.array(
        [[10, 0, 0], [np.nan, 0, 0], [11, 0, 0]], np.float64
    )
    effective = effective_target_geometry(historical, s7.xyz_h)
    check(
        "effective geometry exact order",
        effective.tolist()
        == [
            [10.0, 0.0, 0.0],
            [11.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [6.0, 0.0, 0.0],
            [6.0, 0.0, 0.0],
        ],
    )

    negative_ok = False
    try:
        MeasurementSnapshot(
            xyz_h=np.zeros((2, 3), np.float32),
            source_global_index=np.zeros((1,), np.int32),
            source_active_target_id=np.zeros((2,), np.int32),
        )
    except ValueError:
        negative_ok = True
    check("negative provenance invariant", negative_ok)

    malformed_ok = False
    try:
        valid_patch_measurements(
            {
                "xyz_h": np.zeros((2, 3), np.float64),
                "instance_id": np.zeros((2, 3), np.int32),
                "valid": np.ones((2, 3), bool),
            }
        )
    except ValueError:
        malformed_ok = True
    check("negative patch-shape invariant", malformed_ok)

    print(
        f"[conceptual-core1-check] SUMMARY checked={checked} failed={failed}"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
