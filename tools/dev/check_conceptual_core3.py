#!/usr/bin/env python3
"""Fail-capable checks for Conceptual Core 3 head-memory extraction."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fov3d.epistemic.head_memory import HeadEvidence, add_head_patch
from fov3d.geometry.head_chart import chart_grid, head_unit_from_angles


def _patch(yaw, pitch, ranges, ids, valid=None):
    yaw = np.asarray(yaw, np.float64).reshape(-1)
    pitch = np.asarray(pitch, np.float64).reshape(-1)
    ranges = np.asarray(ranges, np.float64).reshape(-1)
    ids = np.asarray(ids, np.int32).reshape(-1)
    if not (len(yaw) == len(pitch) == len(ranges) == len(ids)):
        raise ValueError("patch vector length mismatch")
    xyz = head_unit_from_angles(yaw, pitch) * ranges[:, None]
    if valid is None:
        valid = np.ones(len(ids), bool)
    valid = np.asarray(valid, bool).reshape(-1)
    if len(valid) != len(ids):
        raise ValueError("valid length mismatch")
    return {
        "xyz_h": xyz.reshape(1, -1, 3),
        "instance_id": ids.reshape(1, -1),
        "valid": valid.reshape(1, -1),
    }


def _from_imports(path: Path) -> list[tuple[str, tuple[str, ...]]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            out.append((node.module, tuple(a.name for a in node.names)))
    return out


def _imports_experiment(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").startswith("fov3d.experiments"):
                return True
        elif isinstance(node, ast.Import):
            if any(a.name.startswith("fov3d.experiments") for a in node.names):
                return True
    return False


def main() -> int:
    checked = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal checked, failed
        checked += 1
        if condition:
            print(f"[conceptual-core3-check] PASS {name}")
        else:
            failed += 1
            print(f"[conceptual-core3-check] FAIL {name}")

    shape = (11, 11)
    ev = HeadEvidence.empty(shape)
    check("empty shapes", all(a.shape == shape for a in (
        ev.depth_seen, ev.target_depth_seen, ev.other_depth_seen,
        ev.nearest_instance, ev.nearest_range_m, ev.ambiguous_instance,
        ev.sample_count,
    )))
    check(
        "empty dtypes",
        ev.depth_seen.dtype == np.bool_
        and ev.target_depth_seen.dtype == np.bool_
        and ev.other_depth_seen.dtype == np.bool_
        and ev.nearest_instance.dtype == np.int32
        and ev.nearest_range_m.dtype == np.float32
        and ev.ambiguous_instance.dtype == np.bool_
        and ev.sample_count.dtype == np.uint16,
    )
    check(
        "empty values",
        not ev.depth_seen.any()
        and not ev.target_depth_seen.any()
        and not ev.other_depth_seen.any()
        and not ev.nearest_instance.any()
        and np.isposinf(ev.nearest_range_m).all()
        and not ev.ambiguous_instance.any()
        and not ev.sample_count.any(),
    )

    domain = {"yaw": [-5.0, 5.0], "pitch": [-5.0, 5.0]}
    y0, _y1, p0, _p1, h, w = chart_grid(domain, 1.0)
    check("test chart shape", (h, w) == shape)

    def cell(yaw_deg: float, pitch_deg: float) -> tuple[int, int]:
        return (
            int(np.rint((pitch_deg - p0) / 1.0)),
            int(np.rint((yaw_deg - y0) / 1.0)),
        )

    a = cell(0.0, 0.0)
    b = cell(1.0, 0.0)
    c = cell(2.0, 0.0)

    first = _patch(
        yaw=[0.0, 0.0, 1.0, 10.0],
        pitch=[0.0, 0.0, 0.0, 0.0],
        ranges=[2.0, 1.0, 3.0, 1.0],
        ids=[7, 8, 7, 7],
    )
    d1 = add_head_patch(ev, first, 7, domain, 1.0)
    check("domain filtering and first delta",
          d1 == {"valid_points": 3, "new_depth_cells": 2, "depth_cells": 2})
    check(
        "depth and target-relative flags",
        bool(ev.depth_seen[a]) and bool(ev.depth_seen[b])
        and bool(ev.target_depth_seen[a]) and bool(ev.target_depth_seen[b])
        and bool(ev.other_depth_seen[a]) and not bool(ev.other_depth_seen[b]),
    )
    check("sample counts", int(ev.sample_count[a]) == 2 and int(ev.sample_count[b]) == 1)
    check(
        "nearest by range",
        int(ev.nearest_instance[a]) == 8
        and np.isclose(float(ev.nearest_range_m[a]), 1.0, atol=0.0, rtol=0.0),
    )
    check("same-patch ambiguity", bool(ev.ambiguous_instance[a]))
    check("single-instance cell initially unambiguous", not bool(ev.ambiguous_instance[b]))

    second = _patch(
        yaw=[0.0, 2.0], pitch=[0.0, 0.0],
        ranges=[1.0, 2.0], ids=[6, 99],
    )
    d2 = add_head_patch(ev, second, 99, domain, 1.0)
    check("second delta",
          d2 == {"valid_points": 2, "new_depth_cells": 1, "depth_cells": 3})
    check(
        "tie prefers smaller instance",
        int(ev.nearest_instance[a]) == 6
        and np.isclose(float(ev.nearest_range_m[a]), 1.0, atol=0.0, rtol=0.0),
    )
    check("target-relative state follows supplied target",
          bool(ev.target_depth_seen[c]) and not bool(ev.other_depth_seen[c]))
    check("sample count accumulates", int(ev.sample_count[a]) == 3)

    third = _patch(
        yaw=[1.0, 2.0], pitch=[0.0, 0.0],
        ranges=[4.0, 2.5], ids=[6, 6],
    )
    d3 = add_head_patch(ev, third, 7, domain, 1.0)
    check("third delta no new cells",
          d3 == {"valid_points": 2, "new_depth_cells": 0, "depth_cells": 3})
    check(
        "history ambiguity is monotonic",
        bool(ev.ambiguous_instance[a])
        and bool(ev.ambiguous_instance[b])
        and bool(ev.ambiguous_instance[c]),
    )
    check("target-relative fields can both accumulate",
          bool(ev.target_depth_seen[c]) and bool(ev.other_depth_seen[c]))
    check(
        "farther different identity does not replace nearest",
        int(ev.nearest_instance[b]) == 7
        and np.isclose(float(ev.nearest_range_m[b]), 3.0, atol=0.0, rtol=0.0),
    )

    sat = HeadEvidence.empty(shape)
    sat.sample_count[a] = np.iinfo(np.uint16).max - 1
    add_head_patch(
        sat, _patch([0.0, 0.0], [0.0, 0.0], [1.0, 1.1], [1, 1]),
        1, domain, 1.0,
    )
    check("sample count saturates uint16", int(sat.sample_count[a]) == 65535)

    # One patch: an exact range tie listed larger-id first, a farther smaller id,
    # a target-only cell and a non-target-only cell.
    tie = HeadEvidence.empty(shape)
    d = cell(-1.0, 0.0)
    d_tie = add_head_patch(
        tie,
        _patch(
            yaw=[0.0, 0.0, 0.0, 1.0, -1.0],
            pitch=[0.0, 0.0, 0.0, 0.0, 0.0],
            ranges=[1.0, 1.0, 2.0, 1.0, 1.0],
            ids=[9, 4, 2, 9, 5],
        ),
        9, domain, 1.0,
    )
    check("within-patch delta",
          d_tie == {"valid_points": 5, "new_depth_cells": 3, "depth_cells": 3})
    check(
        "within-patch exact tie prefers smaller instance",
        int(tie.nearest_instance[a]) == 4
        and np.isclose(float(tie.nearest_range_m[a]), 1.0, atol=0.0, rtol=0.0),
    )
    check(
        "target-relative flags are conditioned on target_id",
        bool(tie.depth_seen[d])
        and not bool(tie.target_depth_seen[d]) and bool(tie.other_depth_seen[d])
        and bool(tie.target_depth_seen[b]) and not bool(tie.other_depth_seen[b]),
    )

    from fov3d.experiments.classroom_partition import incidental
    check(
        "incidental compatibility identity",
        incidental.HeadEvidence is HeadEvidence
        and incidental.add_head_patch is add_head_patch,
    )

    expected_module = "fov3d.epistemic.head_memory"
    direct_ok = True
    for rel in (
        "fov3d/experiments/classroom_partition/prefix_benchmark.py",
        "fov3d/experiments/classroom_partition/integration.py",
        "fov3d/experiments/classroom_partition/challenge_suite.py",
    ):
        imports = _from_imports(ROOT / rel)
        direct_ok &= any(
            module == expected_module
            and "HeadEvidence" in names and "add_head_patch" in names
            for module, names in imports
        )
        direct_ok &= not any(
            module == "fov3d.experiments.classroom_partition.incidental"
            and ("HeadEvidence" in names or "add_head_patch" in names)
            for module, names in imports
        )
    check("later phases import conceptual head memory directly", direct_ok)

    epistemic_dir = ROOT / "fov3d" / "epistemic"
    reverse = [p.name for p in epistemic_dir.glob("*.py") if _imports_experiment(p)]
    check("epistemic package has no experiment dependency", not reverse)

    mutant_tie_winner = max(8, 6)
    check(
        "negative tie-rule mutant rejected",
        int(ev.nearest_instance[a]) == 6
        and int(ev.nearest_instance[a]) != mutant_tie_winner,
    )
    check(
        "negative target-rule mutant rejected",
        bool(ev.target_depth_seen[c]) and bool(ev.other_depth_seen[c]),
    )

    print(f"[conceptual-core3-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
