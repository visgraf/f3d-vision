"""North Star-1b: the temporary POLICY COORDINATE CHART C and the NORTH-STAR FRAME ADAPTER (host side).

Contract: docs/north-star/ns1b-recentered-controller-handoff-contract.md, sections 6-8 and 11.

Chart C is a policy coordinate chart only.  The physical head never moves: every physical quantity (eye centres,
calibrations, projections, rectification, observability, acquisitions) stays in the canonical fixed-head frame H0.

    R_HC = column_stack(x_C, y_C, z_C)   maps C coordinates into H0;   rows: p_C = p_H0 @ R_HC,  p_H0 = p_C @ R_HC.T

``PolicyChartAdapter`` runs the accepted FSG6f / Cyclopean / Controller-02 code UNCHANGED on chart-C inputs and
substitutes exactly three physical-boundary functions (P1, P2, P3; contract section 7) by their composition with the
chart transform, in every loaded module object compiled from the named file, restoring them on exit.
"""
from __future__ import annotations

import math
from pathlib import Path
import sys
from typing import Any, Callable

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1b_spec as SP  # noqa: E402

B_H0 = np.array(SP.BASELINE_H0, np.float64)


class ChartSingular(RuntimeError):
    """The projected baseline vanishes: HARD STOP (no other axis is invented)."""


# ------------------------------------------------------------------ gaze conventions (accepted fsg_geometry)
def gaze_direction(yaw_deg: float, pitch_deg: float) -> np.ndarray:
    """The accepted ``fsg_geometry.gaze_direction``: (sin y cos p, sin p, -cos y cos p)."""
    import fsg_geometry as FG
    return np.asarray(FG.gaze_direction(float(yaw_deg), float(pitch_deg)), np.float64)


def yaw_pitch(d: np.ndarray) -> tuple[float, float]:
    """yaw = atan2(d_x, -d_z), pitch = atan2(d_y, hypot(d_x, d_z)), in degrees (contract section 11)."""
    d = np.asarray(d, np.float64)
    return (math.degrees(math.atan2(float(d[0]), float(-d[2]))),
            math.degrees(math.atan2(float(d[1]), math.hypot(float(d[0]), float(d[2])))))


def leverage(d_h0: np.ndarray) -> float:
    """Physical stereo leverage L = sqrt(1 - (b . g)^2) with the H0 baseline b = +X."""
    g = np.asarray(d_h0, np.float64)
    g = g / np.linalg.norm(g)
    return float(math.sqrt(max(0.0, 1.0 - float(np.dot(B_H0, g)) ** 2)))


# ------------------------------------------------------------------ section 6: the chart
def chart_basis(g0: np.ndarray) -> dict[str, Any]:
    """The frozen construction: x_C = normalize(b - (b.g0) g0), z_C = -g0, y_C = normalize(z_C x x_C)."""
    g0 = np.asarray(g0, np.float64)
    g0 = g0 / np.linalg.norm(g0)
    perp = B_H0 - float(np.dot(B_H0, g0)) * g0
    n = float(np.linalg.norm(perp))
    if not n >= SP.CHART_SINGULAR_MIN:
        raise ChartSingular(f"HARD STOP the projected baseline is singular: |b - (b.g0) g0| = {n:.3e} "
                            f"< {SP.CHART_SINGULAR_MIN}")
    x = perp / n
    z = -g0
    y = np.cross(z, x)
    y = y / np.linalg.norm(y)
    r = np.column_stack((x, y, z))
    return {"R_HC": r, "x_C_in_H0": x, "y_C_in_H0": y, "z_C_in_H0": z, "projected_baseline_norm": n,
            "b_dot_g0": float(np.dot(B_H0, g0))}


def to_chart(p_h0: np.ndarray, r_hc: np.ndarray) -> np.ndarray:
    return np.asarray(p_h0, np.float64) @ np.asarray(r_hc, np.float64)


def to_h0(p_c: np.ndarray, r_hc: np.ndarray) -> np.ndarray:
    return np.asarray(p_c, np.float64) @ np.asarray(r_hc, np.float64).T


def local_to_world_gaze(yaw_c: float, pitch_c: float, r_hc: np.ndarray) -> tuple[float, float, np.ndarray]:
    """d_C = gaze_direction(yaw_C, pitch_C); d_H0 = d_C @ R_HC.T; the accepted H0 yaw / pitch of d_H0."""
    d_h0 = to_h0(gaze_direction(yaw_c, pitch_c), r_hc)
    y, p = yaw_pitch(d_h0)
    return y, p, d_h0


def world_to_local_gaze(yaw_h0: float, pitch_h0: float, r_hc: np.ndarray) -> tuple[float, float]:
    return yaw_pitch(to_chart(gaze_direction(yaw_h0, pitch_h0), r_hc))


def chart_checks(r_hc: np.ndarray, g0: np.ndarray, probe_points: np.ndarray) -> dict[str, Any]:
    """The section-6 requirements on one chart (orthonormality, det, centre, round trips, distances)."""
    r = np.asarray(r_hc, np.float64)
    g0 = np.asarray(g0, np.float64) / np.linalg.norm(g0)
    p = np.asarray(probe_points, np.float64).reshape(-1, 3)
    centre = yaw_pitch(to_chart(g0, r))
    dirs = p / np.linalg.norm(p, axis=1, keepdims=True)
    d_pair = np.linalg.norm(p[:, None, :] - p[None, :, :], axis=-1)
    pc = to_chart(p, r)
    d_pair_c = np.linalg.norm(pc[:, None, :] - pc[None, :, :], axis=-1)
    out = {
        "orthonormality_error": float(np.abs(r.T @ r - np.eye(3)).max()),
        "determinant": float(np.linalg.det(r)),
        "seed_local_yaw_pitch_deg": [float(centre[0]), float(centre[1])],
        "point_roundtrip_error_m": float(np.abs(to_h0(pc, r) - p).max()),
        "direction_roundtrip_error": float(np.abs(to_h0(to_chart(dirs, r), r) - dirs).max()),
        "distance_change_m": float(np.abs(d_pair_c - d_pair).max()),
        "baseline_in_C": to_chart(B_H0, r).tolist(),
    }
    out["ok"] = bool(out["orthonormality_error"] <= SP.ORTHO_TOL and abs(out["determinant"] - 1.0) <= SP.ORTHO_TOL
                     and max(abs(centre[0]), abs(centre[1])) <= SP.CENTRE_TOL_DEG
                     and out["point_roundtrip_error_m"] <= SP.ROUNDTRIP_TOL
                     and out["direction_roundtrip_error"] <= SP.ROUNDTRIP_TOL
                     and out["distance_change_m"] <= SP.ROUNDTRIP_TOL)
    return out


# ------------------------------------------------------------------ rigid rotations (section 8b)
def rot_x(beta_deg: float) -> np.ndarray:
    """Rotation about the physical baseline axis +X: the exact symmetry group of the fixed binocular head."""
    b = math.radians(float(beta_deg))
    c, s = math.cos(b), math.sin(b)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def rot_axis(axis, angle_rad: float) -> np.ndarray:
    a = np.asarray(axis, np.float64)
    a = a / np.linalg.norm(a)
    k = np.array([[0.0, -a[2], a[1]], [a[2], 0.0, -a[0]], [-a[1], a[0], 0.0]])
    return np.eye(3) + math.sin(angle_rad) * k + (1.0 - math.cos(angle_rad)) * (k @ k)


def rotate_calibration(c: dict, q: np.ndarray) -> dict:
    """The same fixed head with every camera rigidly rotated about the baseline axis (Q must fix +X).

    Eye centres stay at (-/+ IPD/2, 0, 0); R_hc -> Q R_hc.  The result is a valid fixed-head calibration accepted by the
    unchanged ``validate_calibration`` / ``rectification``; for ``baseline_projected`` cameras it equals
    ``make_calibration`` at the rotated gaze.
    """
    import copy
    q = np.asarray(q, np.float64)
    if not np.allclose(q @ B_H0, B_H0, atol=1e-15, rtol=0.0):
        raise ValueError("only rotations about the physical baseline axis keep the eyes on +X")
    out = copy.deepcopy(c)
    for eye in out["eyes"]:
        eye["R_hc"] = (q @ np.asarray(eye["R_hc"], np.float64)).tolist()
    y, p = yaw_pitch(q @ gaze_direction(*c["gaze_yaw_pitch_deg"]))
    out["gaze_yaw_pitch_deg"] = [y, p]
    return out


# ------------------------------------------------------------------ section 7: the frame adapter
def _module_copies(rel: str) -> list[tuple[str, Any]]:
    """Every loaded module object compiled from REPO/<rel> (the sealed engine is importable under two names)."""
    want = (REPO / rel).resolve()
    out = []
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if f and Path(f).resolve() == want:
            out.append((name, mod))
    return sorted(out, key=lambda t: t[0])


def ensure_policy_modules() -> None:
    """Load every module object the accepted policy uses, so no copy is first imported inside the adapter."""
    import fov3d  # noqa: F401
    import fsg6f_frontier  # noqa: F401  (the copy used by the accepted multiobject2c_policy adapter)
    from fov3d.control import frontier, frontier_config, integrated, object_policy  # noqa: F401
    from fov3d.experiments.classroom_oracle import controller01, controller02, epistemic, matcher  # noqa: F401


def accepted_sensor(profile: str, yaw_h0: float, pitch_h0: float, head_r_wh, head_origin_w) -> dict:
    """The accepted Controller-02 predicted calibration (the Controller-01 renderer's construction)."""
    fn = _ORIGINAL_P3
    if fn is None:
        from fov3d.experiments.classroom_oracle import controller02 as c02x
        fn = c02x.predicted_calibration
    if getattr(fn, "__ns1b_wrapper__", False):
        raise RuntimeError("the accepted sensor must be the unsubstituted predicted_calibration")
    return fn(profile, (float(yaw_h0), float(pitch_h0)), head_r_wh, head_origin_w)


def north_star_sensor(profile: str, yaw_h0: float, pitch_h0: float, head_r_wh, head_origin_w) -> dict:
    """The North-Star observation sensor that executes the look (``ns1a_core.planned_calibration``)."""
    import ns1a_core
    if profile != SP.PROFILE:
        raise ValueError(f"the North-Star sensor is the {SP.PROFILE} profile, not {profile!r}")
    return ns1a_core.planned_calibration(float(yaw_h0), float(pitch_h0), head_r_wh, head_origin_w)


def baseline_projected_sensor(profile: str, yaw_h0: float, pitch_h0: float, head_r_wh, head_origin_w) -> dict:
    """``make_calibration(..., tangent_frame='baseline_projected')`` in any profile (synthetic fixtures)."""
    import fsg_geometry as FG
    return FG.make_calibration(profile, float(yaw_h0), float(pitch_h0), SP.VERGENCE_M, ipd=SP.IPD_M,
                               head_r_wh=np.asarray(head_r_wh, np.float64),
                               head_origin_w=np.asarray(head_origin_w, np.float64), tangent_frame=SP.TANGENT_FRAME)


_ORIGINAL_P3: Callable | None = None


class PolicyChartAdapter:
    """Chart C for policy geometry, H0 for physical sensing (contract section 7).

    P1: fsg6f_frontier._project_rectified_core(cal, xyz_C, side) -> accepted(cal, xyz_C @ R_HC.T, side)
    P2: classroom_oracle1_epistemic._rectified_core_directions_h(cal, side) -> accepted(cal, side) @ R_HC
    P3: controller02.predicted_calibration(profile, gaze_C, R_wh, o_w) -> sensor(profile, world gaze of gaze_C, R_wh, o_w)
    """

    _active: "PolicyChartAdapter | None" = None

    def __init__(self, r_hc: np.ndarray, sensor: Callable | None = None, label: str = "") -> None:
        r = np.asarray(r_hc, np.float64)
        if r.shape != (3, 3) or np.abs(r.T @ r - np.eye(3)).max() > SP.ORTHO_TOL or \
                abs(float(np.linalg.det(r)) - 1.0) > SP.ORTHO_TOL:
            raise ValueError("the policy chart must be a proper orthonormal basis")
        self.r = r
        self.sensor = sensor if sensor is not None else accepted_sensor
        self.label = label
        self.calls = {"P1": 0, "P2": 0, "P3": 0}
        self.p3_log: list[dict] = []
        self.saved: list[tuple[str, Any, str, Any]] = []
        self.copies_before: dict[str, list[str]] = {}
        self.restored = False

    # -- the three substitutions
    def _p1(self, original):
        r = self.r

        def project_rectified_core(calibration, xyz_h, side):
            self.calls["P1"] += 1
            pts = np.asarray(xyz_h, float).reshape(-1, 3)
            return original(calibration, pts @ r.T, side)
        return project_rectified_core

    def _p2(self, original):
        r = self.r

        def rectified_core_directions_h(calibration, side):
            self.calls["P2"] += 1
            return original(calibration, side) @ r
        return rectified_core_directions_h

    def _p3(self, original):
        r = self.r

        def predicted_calibration(profile, gaze, head_r_wh, head_origin_w):
            self.calls["P3"] += 1
            y, p, _d = local_to_world_gaze(float(gaze[0]), float(gaze[1]), r)
            cal = self.sensor(profile, y, p, head_r_wh, head_origin_w)
            self.p3_log.append({"local_gaze_deg": [float(gaze[0]), float(gaze[1])], "world_gaze_deg": [y, p],
                                "calibration_gaze_deg": list(map(float, cal["gaze_yaw_pitch_deg"])),
                                "tangent_frame": cal.get("tangent_frame", "legacy_upright")})
            return cal
        return predicted_calibration

    def __enter__(self) -> "PolicyChartAdapter":
        global _ORIGINAL_P3
        if PolicyChartAdapter._active is not None:
            raise RuntimeError("a policy chart adapter is already active (nesting refused)")
        ensure_policy_modules()
        makers = {"P1": self._p1, "P2": self._p2, "P3": self._p3}
        for sid, rel, attr in SP.ADAPTER_SUBSTITUTIONS:
            copies = _module_copies(rel)
            if not copies:
                raise RuntimeError(f"{sid}: no loaded module compiled from {rel}")
            self.copies_before[sid] = [n for n, _ in copies]
            for name, mod in copies:
                original = getattr(mod, attr)
                if getattr(original, "__ns1b_wrapper__", False):
                    raise RuntimeError(f"{sid}: {name}.{attr} is already substituted")
                if sid == "P3":
                    _ORIGINAL_P3 = original
                wrapper = makers[sid](original)
                wrapper.__ns1b_wrapper__ = True
                self.saved.append((name, mod, attr, original))
                setattr(mod, attr, wrapper)
        PolicyChartAdapter._active = self
        return self

    def __exit__(self, *exc) -> None:
        for _name, mod, attr, original in reversed(self.saved):
            setattr(mod, attr, original)
        PolicyChartAdapter._active = None
        after = {sid: [n for n, _ in _module_copies(rel)] for sid, rel, _a in SP.ADAPTER_SUBSTITUTIONS}
        self.restored = all(getattr(mod, attr) is original for _n, mod, attr, original in self.saved)
        self.copies_stable = after == self.copies_before
        if not (self.restored and self.copies_stable):
            raise RuntimeError(f"adapter exit: restored {self.restored}, module copies stable {self.copies_stable}")

    def record(self) -> dict[str, Any]:
        return {"label": self.label, "R_HC": self.r.tolist(),
                "substitutions": [{"id": sid, "file": rel, "function": attr, "modules": self.copies_before.get(sid, [])}
                                  for sid, rel, attr in SP.ADAPTER_SUBSTITUTIONS],
                "calls": dict(self.calls), "p3": list(self.p3_log), "restored": bool(self.restored),
                "module_copies_stable": bool(getattr(self, "copies_stable", False)),
                "sensor": getattr(self.sensor, "__name__", repr(self.sensor))}


def original_functions() -> dict[str, list[tuple[str, Any]]]:
    """The currently installed objects of the three substituted names in every loaded copy (for restore checks)."""
    ensure_policy_modules()
    return {sid: [(n, getattr(m, attr)) for n, m in _module_copies(rel)] for sid, rel, attr in SP.ADAPTER_SUBSTITUTIONS}
