"""Natural Bootstrap-1c: sensor-scale center-surround RGB attention and six-gaze spherical NMS (selection core).

Contract: docs/natural-bootstrap/nb1c-rgb-candidate-gaze-contract.md, sections 5-11 and 14.  The functions
take only the 8-bit RGB proxy and the declared constants.  Numerical method (contract section 9):
- row-interval membership: inside a disk around cell (j0, c0), the cells of row j are exactly the circular
  interval |c - c0| <= k(j0, j), none, or the whole row; k is derived at reference column 0 with the contract's
  atan2 distance, and anything other than an exact interval is a STOP;
- symmetric incremental row box sums (the same operation sequence for every column, so the raster is exactly
  equivariant to longitude rolls); rows added in ascending order; SURROUND = 12-degree disk - CENTER;
- values shifted by the per-channel median m; V_R = sum w ||rgb - m||^2 / W_R - ||mu_R - m||^2.
The keyword variants of ``attention`` and ``select_gazes`` exist only so that the checker's mutation suite can
build deliberately wrong versions.
"""
from __future__ import annotations

import math

import numpy as np

import nb1c_spec as SP

_PATTERNS: dict = {}


class DecompositionError(RuntimeError):
    """A derived membership is not an exact circular row interval (contract section 9): STOP."""


class BudgetError(RuntimeError):
    """The NMS cannot produce K directions (contract section 11): HARD FAIL."""


def angular_distance(d_g: np.ndarray, dirs: np.ndarray) -> np.ndarray:
    """alpha_i = atan2(||d_i x d_g||, d_i . d_g) for every row d_i of ``dirs``."""
    return np.arctan2(np.linalg.norm(np.cross(dirs, d_g), axis=1), dirs @ d_g)


# ------------------------------------------------------------------ membership pattern (section 9.1)
def _circular_offsets() -> np.ndarray:
    c = np.arange(SP.WIDTH)
    return np.minimum(c, SP.WIDTH - c)          # |dc| of column c from reference column 0, in [0, 360]


def membership_pattern(r_center: float = SP.R_CENTER_RAD, r_surround: float = SP.R_SURROUND_RAD,
                       metric: str = "sphere") -> dict:
    """k_center[j0, j] and k_disk[j0, j]: the half-width of the CENTER and 12-degree-disk intervals of row j around
    a candidate in row j0 (-1 = no cell, WIDTH // 2 = the whole row).  ``metric='pixel'`` is a mutant only."""
    key = (r_center, r_surround, metric)
    if key in _PATTERNS:
        return _PATTERNS[key]
    H, W = SP.HEIGHT, SP.WIDTH
    dirs = SP.cell_directions_h()
    pitch = np.radians(SP.pitch_centers_deg())
    cd = _circular_offsets()
    band = r_surround + math.radians(SP.BAND_MARGIN_DEG)
    kc = np.full((H, H), -1, np.int16)
    kd = np.full((H, H), -1, np.int16)
    for j0 in range(H):
        rows = np.flatnonzero(np.abs(pitch - pitch[j0]) <= band)
        if metric == "sphere":
            alpha = angular_distance(dirs[j0, 0], dirs[rows].reshape(-1, 3)).reshape(len(rows), W)
        else:   # equirectangular pixel distance (mutant)
            alpha = np.radians(SP.CELL_DEG) * np.sqrt((rows - j0)[:, None] ** 2.0 + cd[None, :] ** 2.0)
        far = np.abs(pitch[rows] - pitch[j0]) > r_surround + 1e-9    # alpha >= |d pitch|: never a member
        for out, radius in ((kc, r_center), (kd, r_surround)):
            inside = alpha <= radius + SP.ANGLE_EPS_RAD
            if inside[far].any():
                raise DecompositionError(f"a member beyond the latitude bound around row {j0}")
            for t, j in enumerate(rows):
                m = inside[t]
                if not m.any():
                    continue
                k = int(cd[m].max())
                if not np.array_equal(m, cd <= k):
                    raise DecompositionError(f"row {j} around row {j0}: membership is not a circular interval")
                out[j0, j] = k
    pat = {"k_center": kc, "k_disk": kd, "reference_column": 0, "metric": metric,
           "r_center": r_center, "r_surround": r_surround}
    _PATTERNS[key] = pat
    return pat


def interval_count(k: int) -> int:
    return 0 if k < 0 else (SP.WIDTH if k >= SP.WIDTH // 2 else 2 * k + 1)


# ------------------------------------------------------------------ statistics (sections 7-8, 9.2-9.3)
def _shift(row: np.ndarray, s: int, wrap: bool) -> np.ndarray:
    """out[c] = row[c - s] (columns wrap; without wrap, out-of-range columns contribute zero)."""
    if wrap:
        return np.roll(row, s, axis=0)
    out = np.zeros_like(row)
    if s >= 0:
        out[s:] = row[:SP.WIDTH - s]
    else:
        out[:SP.WIDTH + s] = row[-s:]
    return out


def attention(lin: np.ndarray, pattern: dict, weights: np.ndarray, *, seam_wrap: bool = True,
              denominator: bool = True) -> dict:
    """Center / surround statistics and the score for all 259,200 candidates.

    ``lin``: (HEIGHT, WIDTH, 3) float64 linear RGB; ``weights``: per-row cell solid angle."""
    H, W = SP.HEIGHT, SP.WIDTH
    shift = np.median(lin.reshape(-1, 3), axis=0)
    dv = lin - shift
    vals = np.concatenate([np.ones((H, W, 1)), dv, (dv * dv).sum(-1, keepdims=True)], axis=-1)   # 1, d (3), |d|^2
    acc = {r: np.zeros((H, W, 5)) for r in ("C", "D")}
    cnt = {r: np.zeros((H, W)) for r in ("C", "D")}
    kc, kd = pattern["k_center"], pattern["k_disk"]
    half = W // 2
    for j in range(H):
        need: dict[int, list] = {}
        for r, kk in (("C", kc), ("D", kd)):
            for j0 in np.flatnonzero(kk[:, j] >= 0):
                need.setdefault(int(kk[j0, j]), []).append((r, int(j0)))
        if not need:
            continue
        row = vals[j]
        box = row.copy()
        for k in range(0, max(need) + 1):
            if k > 0:
                if k < half or not seam_wrap:
                    box = box + _shift(row, k, seam_wrap) + _shift(row, -k, seam_wrap)
                else:   # k == 360 with wrapping: the antipodal column, once
                    box = box + _shift(row, half, True)
            for r, j0 in need.get(k, ()):
                acc[r][j0] += weights[j] * box
                cnt[r][j0] += box[:, 0]
    dC, dD = acc["C"], acc["D"]
    dS = dD - dC
    W_C, W_S = dC[..., 0], dS[..., 0]
    n_C, n_S = cnt["C"], cnt["D"] - cnt["C"]
    if (W_C <= 0).any() or (W_S <= 0).any():
        raise DecompositionError("an empty CENTER or SURROUND")
    mC = dC[..., 1:4] / W_C[..., None]          # mu_C - m
    mS = dS[..., 1:4] / W_S[..., None]          # mu_S - m
    V_C = dC[..., 4] / W_C - (mC * mC).sum(-1)
    V_S = dS[..., 4] / W_S - (mS * mS).sum(-1)
    D = np.sqrt(((mC - mS) ** 2).sum(-1))
    den = V_C + V_S + SP.VAR_EPS
    if (den <= 0).any():
        raise DecompositionError("non-positive score denominator")
    A = D / np.sqrt(den) if denominator else D.copy()
    return {"A": A, "D_RGB": D, "V_C": V_C, "V_S": V_S, "mu_C": mC + shift, "mu_S": mS + shift,
            "W_C": W_C, "W_S": W_S, "n_C": np.rint(n_C).astype(np.int32), "n_S": np.rint(n_S).astype(np.int32),
            "shift": shift, "denominator": den}


# ------------------------------------------------------------------ NMS (sections 10-11)
def select_gazes(scores: np.ndarray, dirs: np.ndarray, k_budget: int = SP.K, d_min: float = SP.D_MIN_RAD,
                 tie_rel: float = SP.SCORE_TIE_REL, tie_break: bool = True) -> tuple[list[int], list[dict]]:
    """Greedy spherical NMS over candidates in row-major order (smaller index = smaller row, then column).

    ``tie_break=False`` (pick the last tied index) exists only for a mutant."""
    a = np.asarray(scores, np.float64).reshape(-1)
    dirs = np.asarray(dirs, np.float64).reshape(-1, 3)
    eligible = np.ones(a.size, bool)
    picks, rounds = [], []
    for k in range(1, k_budget + 1):
        idx = np.flatnonzero(eligible)
        if idx.size == 0:
            raise BudgetError(f"only {len(picks)} of {k_budget} directions could be selected")
        amax = float(a[idx].max())
        tied = idx[amax - a[idx] <= tie_rel * max(1.0, abs(amax))]
        g = int(tied.min() if tie_break else tied.max())
        others = np.setdiff1d(idx, tied, assume_unique=True)
        alpha = angular_distance(dirs[g], dirs)
        newly = eligible & (alpha + SP.ANGLE_EPS_RAD < d_min)
        before = int(idx.size)
        eligible &= ~newly
        picks.append(g)
        rounds.append({"round": k, "index": g, "row": g // SP.WIDTH, "col": g % SP.WIDTH, "score": float(a[g]),
                       "score_max": amax, "tie_set_size": int(tied.size), "eligible_before": before,
                       "newly_suppressed": int(newly.sum()), "remaining": int(eligible.sum()),
                       "margin_to_next_eligible": float(a[g] - a[others].max()) if others.size else None})
    return picks, rounds


def pairwise_deg(dirs_sel: np.ndarray) -> np.ndarray:
    d = np.asarray(dirs_sel, np.float64)
    return np.degrees(np.array([angular_distance(x, d) for x in d]))


# ------------------------------------------------------------------ the whole pure-RGB computation
def run(srgb8: np.ndarray, *, k_budget: int = SP.K, r_center: float = SP.R_CENTER_RAD,
        r_surround: float = SP.R_SURROUND_RAD, d_min: float | None = None, r_full: float = SP.R_FULL_RAD,
        linear: bool = True, weighted: bool = True, metric: str = "sphere", seam_wrap: bool = True,
        denominator: bool = True, tie_break: bool = True) -> dict:
    """Score raster, diagnostics and the K gazes for one 8-bit RGB sphere."""
    if srgb8.dtype != np.uint8 or srgb8.shape != (SP.HEIGHT, SP.WIDTH, 3):
        raise ValueError(f"srgb8 must be uint8 {SP.HEIGHT} x {SP.WIDTH} x 3, got {srgb8.dtype} {srgb8.shape}")
    lut = SP.linear_table(linear)
    lin = lut[srgb8]
    weights = SP.row_weights(weighted)
    pat = membership_pattern(r_center, r_surround, metric)
    st = attention(lin, pat, weights, seam_wrap=seam_wrap, denominator=denominator)
    dmin = 2.0 * r_full if d_min is None else d_min
    dirs = SP.cell_directions_h().reshape(-1, 3)
    picks, rounds = select_gazes(st["A"], dirs, k_budget, dmin, tie_break=tie_break)
    return {"stats": st, "pattern": pat, "lut": lut, "weights": weights, "picks": picks, "rounds": rounds,
            "pairwise_deg": pairwise_deg(dirs[picks]), "dirs_sel": dirs[picks],
            "params": {"K": k_budget, "r_center": r_center, "r_surround": r_surround, "r_full": r_full, "d_min": dmin,
                       "linear": linear, "weighted": weighted, "metric": metric, "seam_wrap": seam_wrap,
                       "denominator": denominator, "tie_break": tie_break}}


def gaze_records(res: dict) -> list[dict]:
    st = res["stats"]
    yaw, pitch = SP.yaw_centers_deg(), SP.pitch_centers_deg()
    out = []
    for k, (g, rd) in enumerate(zip(res["picks"], res["rounds"]), start=1):
        r, c = divmod(g, SP.WIDTH)
        out.append({"rank": k, "index": g, "row": r, "col": c, "yaw_deg": float(yaw[c]), "pitch_deg": float(pitch[r]),
                    "direction_h": [float(x) for x in res["dirs_sel"][k - 1]], "A": float(st["A"][r, c]),
                    "D_RGB": float(st["D_RGB"][r, c]), "V_C": float(st["V_C"][r, c]), "V_S": float(st["V_S"][r, c]),
                    "mu_C_linear": [float(x) for x in st["mu_C"][r, c]], "mu_S_linear": [float(x) for x in st["mu_S"][r, c]],
                    "n_C": int(st["n_C"][r, c]), "n_S": int(st["n_S"][r, c]), "W_C_sr": float(st["W_C"][r, c]),
                    "W_S_sr": float(st["W_S"][r, c]), "tie_set_size": rd["tie_set_size"],
                    "margin_to_next_eligible": rd["margin_to_next_eligible"]})
    return out


def _dist(values: np.ndarray) -> dict:
    v = np.asarray(values, np.float64).reshape(-1)
    return {name: float(np.quantile(v, q)) for name, q in SP.QUANTILES.items()}


def summary(res: dict) -> dict:
    st = res["stats"]
    pw = res["pairwise_deg"]
    off = pw[~np.eye(len(pw), dtype=bool)]
    pitch = SP.pitch_centers_deg()
    lat_bands = [(-90, -60), (-60, -30), (-30, 0), (0, 30), (30, 60), (60, 90)]
    by_lat = []
    for lo, hi in lat_bands:
        rows = np.flatnonzero((pitch >= lo) & (pitch < hi))
        by_lat.append({"pitch_deg": [lo, hi], "n_C": _dist(st["n_C"][rows]), "n_S": _dist(st["n_S"][rows])})
    return {
        "schema": "NB1c-selection-summary-v1", "truth": SP.TRUTH_DERIVED,
        "statement": "PURE RGB SELECTION: primary NB1c measurements from the coarse RGB proxy only, recorded before any "
                     "evaluation input is opened; not objectness, not saliency ground truth",
        "resolution": {"width": SP.WIDTH, "height": SP.HEIGHT, "cell_deg": SP.CELL_DEG},
        "candidate_directions": int(st["A"].size), "K": res["params"]["K"], "params_used": res["params"],
        "constants": SP.SENSOR_CONSTANTS,
        "weights_sum_minus_4pi": math.fsum(np.repeat(res["weights"], SP.WIDTH).tolist()) - 4 * math.pi,
        "center_cells": _dist(st["n_C"]), "surround_cells": _dist(st["n_S"]), "cells_by_latitude": by_lat,
        "attention_score": _dist(st["A"]), "D_RGB": _dist(st["D_RGB"]),
        "selected": [{k: g[k] for k in ("rank", "row", "col", "yaw_deg", "pitch_deg", "A", "D_RGB", "V_C", "V_S")}
                     for g in gaze_records(res)],
        "pairwise_angular_distance_deg": pw.tolist(),
        "min_pairwise_deg": float(off.min()) if off.size else None,
        "all_pairs_at_least_D_MIN": bool((np.radians(off) >= res["params"]["d_min"] - SP.ANGLE_EPS_RAD).all()),
        "numerics": {"min_denominator": float(st["denominator"].min()),
                     "negative_V_C": int((st["V_C"] < 0).sum()), "negative_V_S": int((st["V_S"] < 0).sum()),
                     "min_V_C": float(st["V_C"].min()), "min_V_S": float(st["V_S"].min()),
                     "shift_median_linear": [float(x) for x in st["shift"]]},
    }
