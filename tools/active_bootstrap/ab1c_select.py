"""Active Bootstrap-1c: the SAFE-FORWARD envelope and the K = 3 RGB-attention gaze selection.

Contract: docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-contract.md, sections 4-5 and 13.  The input is
exactly the frozen accepted NB1c attention raster ``A``; the envelope is calibration-only geometry (the accepted
``fsg_geometry.make_calibration`` / ``rays_h``, no scene data).  The greedy NMS is the accepted NB1c rule (tie rule,
suppression rule, ``angular_distance``) with one difference declared by the contract: the initial eligible set is the
SAFE-FORWARD mask instead of the whole sphere.  This module imports no cv2 and names no depth, range, Position, Object
Index, catalog, segmentation or stereo source; it never opens the head-pose record (the head pose does not enter the
head-frame eye geometry).
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent / "natural_bootstrap"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ab1c_spec as SP  # noqa: E402
import fsg_geometry as FG  # noqa: E402  (accepted sensor geometry, read-only)
import nb1a_spec as NA  # noqa: E402  (accepted spherical grid convention, read-only)
import nb1c_attention as NC  # noqa: E402  (accepted NB1c angular distance and reference NMS, read-only)
from nb1a_guard import OpenGuard  # noqa: E402  (accepted allowlist file-open guard, read-only)


class BudgetError(RuntimeError):
    """The NMS cannot produce K directions inside the eligible set (contract section 5): HARD STOP."""


class EnvelopeError(RuntimeError):
    """The SAFE-FORWARD mask cannot be computed exactly from the accepted camera geometry: STOP."""


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, data) -> None:
    Path(path).write_text(json.dumps(data, indent=1, sort_keys=True, allow_nan=False) + "\n")


# ------------------------------------------------------------------ the envelope (section 4)
def grid() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Cell-centre directions (HEIGHT, WIDTH, 3), yaw (WIDTH,) and pitch (HEIGHT,) in degrees (accepted convention)."""
    return NA.cell_directions_h(), NA.yaw_centers_deg(), NA.pitch_centers_deg()


def leverage(d) -> np.ndarray:
    """L(d) = sqrt(1 - (b . d)^2) with b = +X."""
    bd = np.asarray(d, np.float64) @ np.asarray(SP.BASELINE_AXIS, np.float64)
    return np.sqrt(np.maximum(0.0, 1.0 - bd * bd))


def alpha_forward(d) -> np.ndarray:
    """alpha_forward = acos(clamp(d . f, -1, 1)), f = -Z."""
    fd = np.asarray(d, np.float64) @ np.asarray(SP.FORWARD_AXIS, np.float64)
    return np.arccos(np.clip(fd, -1.0, 1.0))


def in_cone(alpha) -> np.ndarray:
    return np.asarray(alpha) <= SP.FORWARD_CONE_RAD + SP.ANGLE_EPS_RAD


def core_uv() -> np.ndarray:
    """The 65,536 nominal raw-core pixel centres (192 + col, 192 + row), row-major."""
    r, c = np.mgrid[:SP.CORE_SIZE, :SP.CORE_SIZE]
    return np.stack([c.ravel() + SP.CORE_ORIGIN, r.ravel() + SP.CORE_ORIGIN], axis=-1).astype(np.float64)


def selection_calibration(yaw: float, pitch: float) -> dict:
    """The accepted binocular calibration at (yaw, pitch), calibration only.  The head-pose arguments keep the
    ``fsg_geometry`` defaults: they do not enter the head-frame eye geometry (K, R_hc, centre_h_m)."""
    return FG.make_calibration(SP.PROFILE, float(yaw), float(pitch), SP.VERGENCE_M, ipd=SP.IPD_M,
                               tangent_frame=SP.TANGENT_FRAME)


def core_leverage(c: dict, uv: np.ndarray | None = None) -> tuple[float, float]:
    """Minimum L over every nominal raw-core pixel ray of the left and of the right eye."""
    uv = core_uv() if uv is None else uv
    return tuple(float(leverage(FG.rays_h(eye, uv)).min()) for eye in c["eyes"])


def gaze_envelope(yaw: float, pitch: float) -> dict:
    """The envelope decision for one direction (used by the synthetic selector tests and the gaze records)."""
    d = FG.gaze_direction(yaw, pitch)
    a = float(alpha_forward(d))
    rec = {"yaw_deg": float(yaw), "pitch_deg": float(pitch), "alpha_forward_rad": a, "alpha_forward_deg": math.degrees(a),
           "in_cone": bool(in_cone(a)), "L_center": float(leverage(d)), "B_perp_center_m": SP.IPD_M * float(leverage(d))}
    lev_l, lev_r = core_leverage(selection_calibration(yaw, pitch))
    rec.update(min_core_leverage_L=lev_l, min_core_leverage_R=lev_r, min_core_leverage=min(lev_l, lev_r),
               leverage_ok=bool(min(lev_l, lev_r) >= SP.LEVERAGE_MIN))
    rec["eligible"] = rec["in_cone"] and rec["leverage_ok"]
    return rec


def safe_forward_mask() -> dict:
    """The SAFE-FORWARD mask over all 259,200 cells: the cone for every cell, the full-core leverage for every cone cell."""
    dirs, yaw, pitch = grid()
    alpha = alpha_forward(dirs)
    cone = in_cone(alpha)
    lev_l = np.full(cone.shape, np.nan)
    lev_r = np.full(cone.shape, np.nan)
    uv = core_uv()
    for r, c in zip(*np.nonzero(cone)):      # row-major order
        try:
            cal = selection_calibration(yaw[c], pitch[r])
        except ValueError as exc:
            raise EnvelopeError(f"make_calibration refuses cone cell ({r}, {c}): {exc}") from exc
        lev_l[r, c], lev_r[r, c] = core_leverage(cal, uv)
    lev = np.fmin(lev_l, lev_r)
    with np.errstate(invalid="ignore"):
        eligible = cone & (lev >= SP.LEVERAGE_MIN)
    if not np.isfinite(lev[cone]).all():
        raise EnvelopeError("non-finite leverage in the cone")
    margins = {"min_abs_leverage_minus_0p90": float(np.abs(lev[cone] - SP.LEVERAGE_MIN).min()),
               "min_abs_alpha_forward_minus_20deg_rad": float(np.abs(alpha - SP.FORWARD_CONE_RAD).min())}
    return {"alpha_forward_rad": alpha, "cone": cone, "min_core_leverage_L": lev_l, "min_core_leverage_R": lev_r,
            "min_core_leverage": lev, "eligible": eligible, "margins": margins}


# ------------------------------------------------------------------ the NMS (section 5): the accepted NB1c rule
def select_gazes(scores: np.ndarray, dirs: np.ndarray, eligible0: np.ndarray, k_budget: int = SP.K,
                 d_min: float = SP.D_MIN_RAD, tie_rel: float = SP.SCORE_TIE_REL) -> tuple[list[int], list[dict]]:
    """Greedy spherical NMS in row-major order, starting from ``eligible0`` (the SAFE-FORWARD mask)."""
    a = np.asarray(scores, np.float64).reshape(-1)
    dirs = np.asarray(dirs, np.float64).reshape(-1, 3)
    eligible = np.asarray(eligible0, bool).reshape(-1).copy()
    if a.size != eligible.size or dirs.shape[0] != a.size:
        raise ValueError("scores, directions and eligibility must cover the same cells")
    picks, rounds = [], []
    for k in range(1, k_budget + 1):
        idx = np.flatnonzero(eligible)
        if idx.size == 0:
            raise BudgetError(f"only {len(picks)} of {k_budget} directions could be selected inside the eligible set")
        amax = float(a[idx].max())
        tied = idx[amax - a[idx] <= tie_rel * max(1.0, abs(amax))]
        g = int(tied.min())
        others = np.setdiff1d(idx, tied, assume_unique=True)
        alpha = NC.angular_distance(dirs[g], dirs)
        newly = eligible & (alpha + SP.ANGLE_EPS_RAD < d_min)
        before = int(idx.size)
        eligible &= ~newly
        picks.append(g)
        rounds.append({"round": k, "index": g, "row": g // SP.WIDTH, "col": g % SP.WIDTH, "score": float(a[g]),
                       "score_max": amax, "tie_set_size": int(tied.size), "eligible_before": before,
                       "newly_suppressed": int(newly.sum()), "remaining": int(eligible.sum()),
                       "margin_to_next_eligible": float(a[g] - a[others].max()) if others.size else None})
    return picks, rounds


def gaze_records(picks, rounds, scores, mask) -> list[dict]:
    dirs, yaw, pitch = grid()
    out = []
    for k, (g, rd) in enumerate(zip(picks, rounds), start=1):
        r, c = divmod(g, SP.WIDTH)
        d = dirs[r, c]
        lev_l, lev_r = float(mask["min_core_leverage_L"][r, c]), float(mask["min_core_leverage_R"][r, c])
        lc = float(leverage(d))
        out.append({"rank": k, "index": int(g), "row": int(r), "col": int(c), "yaw_deg": float(yaw[c]),
                    "pitch_deg": float(pitch[r]), "direction_h": [float(x) for x in d], "A": float(scores[r, c]),
                    "alpha_forward_rad": float(mask["alpha_forward_rad"][r, c]),
                    "alpha_forward_deg": math.degrees(float(mask["alpha_forward_rad"][r, c])),
                    "L_center": lc, "B_perp_center_m": SP.IPD_M * lc,
                    "min_core_leverage_L": lev_l, "min_core_leverage_R": lev_r,
                    "min_core_leverage": min(lev_l, lev_r), "B_perp_min_core_m": SP.IPD_M * min(lev_l, lev_r),
                    "eligible_before": rd["eligible_before"], "tie_set_size": rd["tie_set_size"],
                    "nms_suppressed": rd["newly_suppressed"], "remaining_after": rd["remaining"],
                    "margin_to_next_eligible": rd["margin_to_next_eligible"]})
    return out


def pairwise_deg(dirs_sel) -> list[list[float]]:
    d = np.asarray(dirs_sel, np.float64)
    return np.degrees(np.array([NC.angular_distance(x, d) for x in d])).tolist()


def load_scores(path: Path) -> np.ndarray:
    with np.load(path, allow_pickle=False) as z:
        if z.files != ["A"]:
            raise ValueError(f"the attention raster must hold exactly A, not {z.files}")
        a = np.asarray(z["A"])
    if a.shape != (SP.HEIGHT, SP.WIDTH) or a.dtype != np.float64 or not np.isfinite(a).all():
        raise ValueError(f"attention raster {a.dtype} {a.shape}")
    return a


def compute_selection(scores: np.ndarray) -> dict:
    mask = safe_forward_mask()
    dirs, _yaw, _pitch = grid()
    picks, rounds = select_gazes(scores, dirs, mask["eligible"])
    gz = gaze_records(picks, rounds, scores, mask)
    return {"mask": mask, "picks": picks, "rounds": rounds, "gazes": gz,
            "pairwise_deg": pairwise_deg([g["direction_h"] for g in gz])}


# ------------------------------------------------------------------ the guarded stage
def run_select(score_path: Path, out_dir: Path) -> dict:
    """Read exactly the frozen attention raster; write the mask, the gazes, the rounds and the records."""
    out_dir.mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ab1c-select", [score_path], [out_dir])
    try:
        with g:
            inp = {"path": str(score_path), "sha256": sha256(score_path)}
            if inp["sha256"] != SP.ATTENTION[1]:
                raise RuntimeError(f"attention raster hash {inp['sha256']}")
            scores = load_scores(score_path)
            sel = compute_selection(scores)
            m = sel["mask"]
            np.savez_compressed(out_dir / "safe-forward-mask.npz", alpha_forward_rad=m["alpha_forward_rad"],
                                cone=m["cone"], min_core_leverage_L=m["min_core_leverage_L"],
                                min_core_leverage_R=m["min_core_leverage_R"], eligible=m["eligible"])
            write_json(out_dir / "selected-gazes.json", {
                "schema": "AB1c-selected-gazes-v1", "truth": SP.TRUTH_DERIVED, "label": SP.SELECTION_LABEL,
                "statement": "the three SAFE-FORWARD gazes chosen by the predeclared rule from the frozen NB1c RGB "
                             "attention and calibration-only geometry; recorded before any render; frozen next",
                "gazes": sel["gazes"]})
            write_json(out_dir / "nms-rounds.json", {"schema": "AB1c-nms-rounds-v1", "truth": SP.TRUTH_DERIVED,
                                                     "rounds": sel["rounds"]})
            summary = {
                "schema": "AB1c-selection-summary-v1", "truth": SP.TRUTH_DERIVED, "label": SP.SELECTION_LABEL,
                "statement": "SAFE-FORWARD selection: RGB attention + calibration-only geometry; no depth, identity, "
                             "segmentation or stereo result", "selection": SP.SELECTION,
                "selection_config_sha256": SP.config_sha256(SP.SELECTION), "input": inp,
                "cells": int(m["cone"].size), "cells_in_cone": int(m["cone"].sum()),
                "cells_eligible": int(m["eligible"].sum()),
                "cone_cells_failing_leverage": int((m["cone"] & ~m["eligible"]).sum()),
                "leverage_in_cone": {"min": float(np.nanmin(m["min_core_leverage"])),
                                     "max": float(np.nanmax(m["min_core_leverage"]))},
                "boundary_margins": m["margins"], "K": SP.K, "D_MIN_RAD": SP.D_MIN_RAD, "D_MIN_DEG": SP.D_MIN_DEG,
                "selected": [{k: x[k] for k in ("rank", "row", "col", "yaw_deg", "pitch_deg", "A")} for x in sel["gazes"]],
                "pairwise_angular_distance_deg": sel["pairwise_deg"],
                "mask_sha256": hashlib.sha256(np.packbits(m["eligible"]).tobytes()).hexdigest()}
            write_json(out_dir / "selection-summary.json", summary)
    finally:
        rec = g.record()
        rec["modules_loaded"] = {mm: mm in sys.modules for mm in ("cv2", "fsg_stereo", "ab1a_stereo", "ab1c_planar")}
        rec["truth_firewall_violations"] = len(rec["violations"])
        write_json(out_dir / "selection-opened-files.json", rec)
    return summary
