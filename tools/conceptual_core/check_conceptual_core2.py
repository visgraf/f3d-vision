#!/usr/bin/env python3
"""Fail-capable checks for Conceptual Core 2 head-chart extraction."""
from __future__ import annotations

from pathlib import Path
import ast
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fov3d.geometry.head_chart import (
    chart_cells,
    chart_grid,
    head_angles_from_unit,
    head_unit_from_angles,
)
from fov3d.reconstruction.association import SURFACE_ASSOCIATION_RADIUS_M


def _shadowed_imported_calls(source: str) -> list[str]:
    """Return `function:name` where a function calls an imported name it also assigns.

    Python then treats the name as local in the whole function, so the call reaches the
    local value (e.g. an int cell count) instead of the imported chart function.
    """
    tree = ast.parse(source)
    imported = {
        a.asname or a.name
        for n in tree.body
        if isinstance(n, ast.ImportFrom)
        for a in n.names
    }
    found: list[str] = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        stores = {
            n.id for n in ast.walk(fn)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
        }
        calls = {
            n.func.id for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        }
        found += [f"{fn.name}:{name}" for name in sorted(stores & calls & imported)]
    return found


def main() -> int:
    checked = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal checked, failed
        checked += 1
        if condition:
            print(f"[conceptual-core2-check] PASS {name}")
        else:
            failed += 1
            print(f"[conceptual-core2-check] FAIL {name}")

    anchors = np.asarray(
        [
            [0.0, 0.0, -1.0],
            [1.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, -1.0, 0.0],
        ],
        np.float64,
    )
    yaw, pitch = head_angles_from_unit(anchors)
    check("anchor yaw", np.array_equal(yaw[:3], np.array([0.0, 90.0, -90.0])))
    check("anchor pitch", np.array_equal(pitch, np.array([0.0, 0.0, 0.0, 90.0, -90.0])))

    sample_yaw = np.array([-63.0, -17.5, 0.0, 28.25, 71.0], np.float64)
    sample_pitch = np.array([-30.0, 12.5, 0.0, -19.25, 35.0], np.float64)
    dirs = head_unit_from_angles(sample_yaw, sample_pitch)
    yyaw, ppitch = head_angles_from_unit(dirs)
    check("angle-unit-angle yaw", np.allclose(yyaw, sample_yaw, atol=1e-12, rtol=0.0))
    check("angle-unit-angle pitch", np.allclose(ppitch, sample_pitch, atol=1e-12, rtol=0.0))

    scaled = dirs * np.array([[2.0], [0.5], [3.0], [4.0], [1.25]])
    syaw, spitch = head_angles_from_unit(scaled)
    rebuilt = head_unit_from_angles(syaw, spitch)
    check("non-unit normalization", np.allclose(rebuilt, dirs, atol=1e-12, rtol=0.0))

    broadcast = head_unit_from_angles(np.array([-10.0, 0.0, 10.0]), np.array([[0.0], [5.0]]))
    check("broadcast shape", broadcast.shape == (6, 3))

    domain = {"yaw": [-25.0, 25.0], "pitch": [-20.0, 20.0]}
    y0, y1, p0, p1, h, w = chart_grid(domain, 0.10)
    check("accepted chart bounds", (y0, y1, p0, p1) == (-25.0, 25.0, -20.0, 20.0))
    check("accepted chart shape", (h, w) == (401, 501))

    cy, cx, ok = chart_cells(
        np.array([0.0, -25.0, 25.0, -25.11, 25.11]),
        np.array([0.0, -20.0, 20.0, 0.0, 0.0]),
        y0, p0, 0.10, h, w,
    )
    check("center and corners", cy[:3].tolist() == [200, 0, 400] and cx[:3].tolist() == [250, 0, 500] and ok[:3].all())
    check("outside rejected", ok[3:].tolist() == [False, False])

    # Exact half cells need binary-exact inputs: on a 0.25-degree grid the normalized
    # coordinates 0.5, 1.5, 2.5 are exact, and np.rint rounds half to even -> 0, 2, 2.
    q0, _q1, r0, _r1, qh, qw = chart_grid(domain, 0.25)
    halves = np.array([0.5, 1.5, 2.5])
    hy, hx, hok = chart_cells(
        q0 + halves * 0.25,
        r0 + halves * 0.25,
        q0, r0, 0.25, qh, qw,
    )
    check(
        "exact half-cell rint (half to even)",
        hx.tolist() == [0, 2, 2] and hy.tolist() == [0, 2, 2] and hok.all(),
    )

    # On the accepted 0.10-degree chart these nominal half cells are not exact in
    # float64 ((-24.95 + 25) / 0.10 = 0.5000000000000071); historical main gives [1, 1].
    ry, rx, rok = chart_cells(
        np.array([-24.95, -24.85]),
        np.array([-19.95, -19.85]),
        y0, p0, 0.10, h, w,
    )
    check(
        "accepted-grid near-half regression",
        rx.tolist() == [1, 1] and ry.tolist() == [1, 1] and rok.all(),
    )

    with np.errstate(invalid="ignore"):
        _ny, _nx, nok = chart_cells(
            np.array([np.nan, np.inf, 0.0]),
            np.array([0.0, 0.0, np.nan]),
            y0, p0, 0.10, h, w,
        )
    check("nonfinite rejected", nok.tolist() == [False, False, False])

    check("association radius", SURFACE_ASSOCIATION_RADIUS_M == 0.012)

    from fov3d.experiments.classroom_partition import lift
    from fov3d.experiments.classroom_partition import benchmark

    check(
        "lift compatibility aliases",
        lift._grid is chart_grid
        and lift._cells is chart_cells
        and lift._head_angles_from_unit is head_angles_from_unit
        and lift._head_unit_from_angles is head_unit_from_angles,
    )
    check(
        "association compatibility aliases",
        lift.FUSION_RADIUS_M == SURFACE_ASSOCIATION_RADIUS_M
        and benchmark.FUSION_RADIUS_M == SURFACE_ASSOCIATION_RADIUS_M,
    )

    package = ROOT / "fov3d" / "experiments" / "classroom_partition"
    shadowed = [
        f"{p.name}:{s}"
        for p in sorted(package.glob("*.py"))
        for s in _shadowed_imported_calls(p.read_text(encoding="utf-8"))
    ]
    check("no shadowed imported chart/association calls", not shadowed)
    for s in shadowed:
        print(f"[conceptual-core2-check]   shadowed {s}")

    wrong_forward_yaw, _ = head_angles_from_unit(np.array([[0.0, 0.0, 1.0]]))
    check("negative frame-sign invariant", float(wrong_forward_yaw[0]) != 0.0)
    check("negative association invariant", SURFACE_ASSOCIATION_RADIUS_M != 0.010)
    check(
        "negative shadowing invariant",
        _shadowed_imported_calls("from m import f\ndef g():\n    y = f(1)\n    f = 2\n") == ["g:f"],
    )

    print(f"[conceptual-core2-check] SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
