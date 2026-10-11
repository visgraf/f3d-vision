"""Playground-1 (gaze lattice): fail-capable host-side checks.  No Blender, no rendering, no Breadth-1.

    .venv/bin/python tools/greedy_foveal/check_lattice.py        # exit 1 on any failed check

Contract: docs/playground/gaze-lattice-contract.md, section 4.

K1 the lattice footprints contain every 1-deg cell centre.
K2 every lattice gaze has a valid tangent frame, and every pair is >= VISIT_TOL_DEG apart.
K3 known answer behind the change: the baseline's first-step UNSEEN gain is 0.825 for its diagonal neighbours and 0.58
   for its side neighbours (the diagonal bias).
K4 a coverage-only replay of the run.py control loop (start at gaze (0, 0), full edge support, no reconstructed
   points) through explorer.decide ends with "none", 0 UNSEEN cells, at most one fixation per lattice gaze (plus the
   start), and no two fixations closer than VISIT_TOL_DEG.
K5 a mid-replay state re-decided twice gives the same decision as the live one.
N1 negative control: K1 with one equator gaze removed must FAIL.
N2 negative control: K4 plus "all-global tail <= 25" with the baseline threshold GAIN_MIN = 0.25 must FAIL.

The replay numbers are a Chat-sandbox model of the workstation run, not a measurement of it.
"""
from __future__ import annotations

import math
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import explorer as X  # noqa: E402

PREFIX = "[lattice]"
TAIL_MAX = 25            # the contract's A3 tail bound, used by the negative control N2
checked = failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global checked, failed
    checked += 1
    failed += not ok
    print(f"{PREFIX} {'PASS' if ok else 'FAIL'} {name}{': ' + detail if detail else ''}", flush=True)


def covers_all(footprints: list[np.ndarray]) -> tuple[bool, int]:
    cov = np.zeros(X.H * X.W, bool)
    for f in footprints:
        cov[f] = True
    return bool(cov.all()), int((~cov).sum())


def replay(max_fix: int = 1000) -> dict:
    """The run.py explore loop with the renderer and reconstruction replaced by full edge support and no points."""
    cv = np.ones((X.CORE_SIZE, X.CORE_SIZE), bool)
    state = np.zeros((X.H, X.W), np.int8)
    visited = np.zeros((0, 3))
    yaw, pitch, kind = 0.0, 0.0, "initial"
    kinds, seen_hist, mid, stop = [], [], None, None
    for n in range(1, max_fix + 1):
        X.update_coverage(state, yaw, pitch, np.zeros((0, 3)))
        seen, _ = X.fractions(state)
        seen_hist.append(seen)
        visited = np.vstack([visited, X.direction(yaw, pitch)[None]])
        kinds.append(kind)
        if seen >= X.SEEN_STOP:
            stop = "seen"
            break
        dec = X.decide(state, cv, yaw, pitch, visited)
        if n == 150:
            mid = (state.copy(), cv, yaw, pitch, visited.copy(), dec)
        if dec["kind"] == "none":
            stop = "none"
            break
        yaw, pitch, kind = dec["yaw_deg"], dec["pitch_deg"], dec["kind"]
    last_local = max((i for i, k in enumerate(kinds) if k == "local"), default=-1)
    ang = X.angle_deg(visited, visited) + np.eye(len(visited)) * 999
    sh = np.array(seen_hist)
    return {"stop": stop, "fixations": len(kinds), "local": kinds.count("local"), "global": kinds.count("global"),
            "tail": len(kinds) - 1 - last_local, "unseen_cells": int((state == X.UNSEEN).sum()),
            "min_pair_deg": float(ang.min()), "to_99": int(np.argmax(sh >= 0.99)) + 1 if sh[-1] >= 0.99 else None,
            "seen": float(sh[-1]), "holes": len(X.unseen_components(state)[1]), "mid": mid}


def k4_ok(r: dict, n_lattice: int) -> bool:
    return (r["stop"] == "none" and r["unseen_cells"] == 0 and r["fixations"] <= n_lattice + 1
            and r["min_pair_deg"] >= X.VISIT_TOL_DEG)


def main() -> None:
    t0 = time.perf_counter()
    L = X.lattice()
    n = len(L["dir"])
    rings = {float(p): int((L["pitch_deg"] == p).sum()) for p in np.unique(L["pitch_deg"])}
    print(f"{PREFIX} lattice: {n} gazes on {len(rings)} rings of {L['ring_deg']:g} deg "
          f"({time.perf_counter() - t0:.1f} s); per ring {list(rings.values())}", flush=True)

    ok, missing = covers_all(L["footprints"])
    check("K1 the lattice covers every 1-deg cell", ok, f"{X.H * X.W - missing} / {X.H * X.W} cells")

    frames_ok = True
    for y, p in zip(L["yaw_deg"], L["pitch_deg"]):
        try:
            X.frame(float(y), float(p))
        except ValueError:
            frames_ok = False
    ang = X.angle_deg(L["dir"], L["dir"]) + np.eye(n) * 999
    check("K2 every gaze has a frame; every pair >= VISIT_TOL_DEG apart",
          frames_ok and float(ang.min()) >= X.VISIT_TOL_DEG, f"frames {frames_ok}, min pair {ang.min():.2f} deg")

    st = np.zeros((X.H, X.W), np.int8)
    X.update_coverage(st, 0.0, 0.0, np.zeros((0, 3)))
    r = X.frame(0.0, 0.0)
    t = math.tan(math.radians(X.LOCAL_STEP_DEG))
    gains = {}
    for name, a, b in X.NEIGHBOURS:
        d = r[:, 2] + t * (a * r[:, 0] + b * r[:, 1])
        y2, p2 = (float(v) for v in X.yaw_pitch(d / np.linalg.norm(d)))
        gains[name] = X.unseen_gain(st, y2, p2)
    diag = [gains[k] for k in ("NE", "NW", "SE", "SW")]
    side = [gains[k] for k in ("E", "W", "N", "S")]
    check("K3 baseline first-step gain: diagonals 0.825, sides 0.58 (+-0.005)",
          all(abs(g - 0.825) <= 0.005 for g in diag) and all(abs(g - 0.58) <= 0.005 for g in side),
          f"diagonal {[round(g, 3) for g in diag]}, side {[round(g, 3) for g in side]}")

    t1 = time.perf_counter()
    rep = replay()
    check("K4 replay: stops with none, 0 UNSEEN cells, <= one fixation per gaze, no duplicate",
          k4_ok(rep, n), f"stop {rep['stop']}, {rep['fixations']} fixations ({rep['local']} local / {rep['global']} "
          f"global, tail {rep['tail']}), UNSEEN cells {rep['unseen_cells']}, min pair {rep['min_pair_deg']:.2f} deg, "
          f"99 % at #{rep['to_99']} ({time.perf_counter() - t1:.0f} s)")

    st_, cv_, y_, p_, vis_, live = rep["mid"]
    d1, d2 = X.decide(st_, cv_, y_, p_, vis_), X.decide(st_, cv_, y_, p_, vis_)
    check("K5 a mid-replay state re-decides identically", d1 == d2 == live, f"{live['kind']} -> "
          f"({live.get('yaw_deg', float('nan')):.2f}, {live.get('pitch_deg', float('nan')):.2f})")

    eq = int(np.flatnonzero(L["pitch_deg"] == 0.0)[0])
    ok_n1, miss_n1 = covers_all(L["footprints"][:eq] + L["footprints"][eq + 1:])
    check("N1 negative control: one equator gaze removed breaks the cover", not ok_n1, f"{miss_n1} cells uncovered")

    saved = X.GAIN_MIN
    X.GAIN_MIN = 0.25
    try:
        neg = replay()
    finally:
        X.GAIN_MIN = saved
    check(f"N2 negative control: GAIN_MIN 0.25 fails K4 + tail <= {TAIL_MAX}",
          not (k4_ok(neg, n) and neg["tail"] <= TAIL_MAX),
          f"{neg['fixations']} fixations ({neg['local']} local / {neg['global']} global, tail {neg['tail']}), "
          f"UNSEEN cells {neg['unseen_cells']}")

    print(f"{PREFIX} SUMMARY checked={checked} failed={failed} ({time.perf_counter() - t0:.0f} s)", flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
