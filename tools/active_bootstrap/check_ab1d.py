"""Active Bootstrap-1d: fail-capable checker of safe-forward natural RGB correspondence.

Contract: docs/active-bootstrap/ab1d-safe-forward-natural-correspondence-contract.md, sections 26-27.

    .venv/bin/python tools/active_bootstrap/check_ab1d.py --run RUN --visuals VIS [--corruptions] [--write-summary]

The checker keeps its own literal constants and re-implements the matcher independently (a fundamental-matrix epipolar
line, arccos / complex-argument angles, its own projection, bilinear sampling, moments-form ZNCC and per-pixel Python
decision logic) for a deterministic subset of left pixels (core index % 32 == 7) and the figure examples; it recomputes
the evaluation from the frozen products and the AB1c benchmark; it audits guard records, freezes, the run order, the
sources and the figures.  ``--corruptions`` injects genuine defects into mirrors of the run and the visuals, after an
unmodified-mirror null probe passes every check.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "natural_bootstrap"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

PREFIX = "[ab1d-check]"

# ------------------------------------------------------------------ the checker's own literals (contract section 32)
BASE = "56840caab332bb203918c776acab20d9a6ef4c17"
CORE, ORIGIN, RAW = 256, 192, 640
HALF = 2
SPACING = 1.0
MIN_STD = 0.5
TIE = 1e-12
TOPK = 8
SEP = 3.0
BOUND = 0.75
ZEPS = 1e-12
DEN = 1e-12
LUMA = (0.2126, 0.7152, 0.0722)
PEAK_RADIUS = 1.5
OFFSETS = (-1.0, -0.5, 0.0, 0.5, 1.0)
AT_BEST = 1e-9
PX_BINS = (0.10, 0.25, 0.50, 1.00)
METRIC_M = (0.012, 0.025, 0.050)
SUBSET = (32, 7)


# ------------------------------------------------------------------ independent photometry and geometry
def own_u8(rgb: np.ndarray) -> np.ndarray:
    a = np.clip(np.asarray(rgb, np.float64), 0.0, 1.0)
    s = np.where(a <= 0.0031308, 12.92 * a, 1.055 * a ** (1.0 / 2.4) - 0.055)
    return np.rint(255.0 * s)


def own_gray(rgb: np.ndarray) -> np.ndarray:
    u = own_u8(rgb)
    return u[..., 0] * LUMA[0] + u[..., 1] * LUMA[1] + u[..., 2] * LUMA[2]


class OwnCam:
    def __init__(self, eye: dict) -> None:
        k = np.asarray(eye["K"], np.float64)
        if k[0, 1] != 0 or k[1, 0] != 0 or tuple(k[2]) != (0.0, 0.0, 1.0):
            raise ValueError("unexpected intrinsics")
        self.fx, self.fy, self.cx, self.cy = k[0, 0], k[1, 1], k[0, 2], k[1, 2]
        self.R = np.asarray(eye["R_hc"], np.float64)
        self.o = np.asarray(eye["centre_h_m"], np.float64)
        self.K = k

    def ray(self, u, v) -> np.ndarray:
        x = np.stack([(np.asarray(u) - self.cx) / self.fx, (np.asarray(v) - self.cy) / self.fy,
                      np.ones(np.shape(u))], -1)
        d = x @ self.R.T
        return d / np.linalg.norm(d, axis=-1, keepdims=True)

    def proj(self, d) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        xc = np.asarray(d) @ self.R
        with np.errstate(divide="ignore", invalid="ignore"):
            return self.fx * xc[..., 0] / xc[..., 2] + self.cx, self.fy * xc[..., 1] / xc[..., 2] + self.cy, xc[..., 2]


def own_theta(d) -> np.ndarray:
    return np.arccos(np.clip(np.asarray(d)[..., 0], -1.0, 1.0))


def own_phi(d) -> np.ndarray:
    d = np.asarray(d)
    return np.angle(-d[..., 2] + 1j * d[..., 1])


def own_dir(theta, phi) -> np.ndarray:
    theta, phi = np.broadcast_arrays(np.asarray(theta, np.float64), np.asarray(phi, np.float64))
    return np.stack([np.cos(theta), np.sin(theta) * np.sin(phi), -np.sin(theta) * np.cos(phi)], -1)


def fundamental(c: dict) -> np.ndarray:
    """F with q_R^T F q_L = 0, from the relative pose X_R = R X_L + T (independent of the matcher's plane algebra)."""
    el, er = c["eyes"]
    rl, rr = np.asarray(el["R_hc"], np.float64), np.asarray(er["R_hc"], np.float64)
    r = rr.T @ rl
    t = rr.T @ (np.asarray(el["centre_h_m"], np.float64) - np.asarray(er["centre_h_m"], np.float64))
    tx = np.array([[0, -t[2], t[1]], [t[2], 0, -t[0]], [-t[1], t[0], 0]])
    kl, kr = np.asarray(el["K"], np.float64), np.asarray(er["K"], np.float64)
    return np.linalg.inv(kr).T @ tx @ r @ np.linalg.inv(kl)


def own_bilinear(g: np.ndarray, u, v):
    h, w = g.shape
    u, v = np.asarray(u, np.float64), np.asarray(v, np.float64)
    with np.errstate(invalid="ignore"):
        ins = (u >= 0) & (u <= w - 1) & (v >= 0) & (v <= h - 1)
    uu, vv = np.where(ins, u, 0.0), np.where(ins, v, 0.0)
    x0 = np.clip(np.floor(uu).astype(np.int64), 0, w - 2)
    y0 = np.clip(np.floor(vv).astype(np.int64), 0, h - 2)
    a, b = uu - x0, vv - y0
    val = (g[y0, x0] * (1 - a) * (1 - b) + g[y0, x0 + 1] * a * (1 - b) + g[y0 + 1, x0] * (1 - a) * b
           + g[y0 + 1, x0 + 1] * a * b)
    return np.where(ins, val, np.nan), ins


def own_patch(cam: OwnCam, g, theta_c, phi_c, dlt, half=HALF):
    """25 samples (theta-major) of the angular patch; (vals, exists).  theta_c, phi_c: arrays of equal shape."""
    theta_c, phi_c = np.asarray(theta_c, np.float64), np.asarray(phi_c, np.float64)
    off = np.arange(-half, half + 1, dtype=np.float64)
    th = theta_c[..., None, None] + off[:, None] * dlt
    ph = phi_c[..., None, None] + off[None, :] * dlt / np.sin(theta_c)[..., None, None]
    d = own_dir(np.broadcast_to(th, ph.shape[:-2] + (off.size, off.size)), ph)
    u, v, z = cam.proj(d)
    vals, ins = own_bilinear(g, u, v)
    ins &= z > ZEPS
    n = off.size * off.size
    vals, ins = vals.reshape(theta_c.shape + (n,)), ins.reshape(theta_c.shape + (n,))
    ex = ins.all(axis=-1)
    return np.where(ex[..., None], vals, np.nan), ex


def own_zncc(a, b) -> np.ndarray:
    """Moments form: (E[ab] - E[a]E[b]) / (sd(a) sd(b))."""
    a, b = np.asarray(a), np.asarray(b)
    cov = (a * b).mean(axis=-1) - a.mean(axis=-1) * b.mean(axis=-1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return cov / (a.std(axis=-1) * b.std(axis=-1))


def own_decide(S: list[float], sep=SEP, topk=TOPK, bound=BOUND, spacing=SPACING) -> dict:
    """Per-pixel Python decision logic on one score list (None = invalid)."""
    n = len(S)
    valid = [s is not None for s in S]
    if not any(valid):
        return {"has": False}
    smax = max(s for s in S if s is not None)
    best = next(j for j in range(n) if S[j] is not None and S[j] >= smax - TIE)
    local = []
    for j in range(n):
        if S[j] is None:
            continue
        ok = all(not (0 <= q < n and S[q] is not None and S[j] < S[q] - TIE) for q in (j - 1, j + 1))
        if ok:
            local.append(j)
    peaks, rem = [], list(local)
    while rem and len(peaks) < topk:
        m = max(S[j] for j in rem)
        pick = min(j for j in rem if S[j] >= m - TIE)
        peaks.append(pick)
        rem = [j for j in rem if abs(j - pick) * spacing >= sep]
    sm = S[best - 1] if best >= 1 else None
    sp = S[best + 1] if best + 1 < n else None
    curv = (sm - 2.0 * S[best] + sp) if (sm is not None and sp is not None) else None
    refined = curv is not None and curv < 0
    off = max(-bound, min(bound, (sm - sp) / (2.0 * curv))) if refined else 0.0
    return {"has": True, "best": best, "peaks": peaks, "curv": curv, "refined": refined, "offset": off}


_OWN_CACHE: dict = {}


def own_match(c: dict, g_l: np.ndarray, g_r: np.ndarray, idx, half=HALF, spacing=SPACING, min_std=MIN_STD,
              sep=SEP, bound=BOUND, topk=TOPK, cache_key=None) -> dict:
    """The checker's independent matcher for the left core indices ``idx`` (per pixel)."""
    key = None if cache_key is None else (cache_key, tuple(np.asarray(idx).tolist()), half, spacing, min_std, sep,
                                          bound, topk)
    if key is not None and key in _OWN_CACHE:
        return _OWN_CACHE[key]
    cl, cr = OwnCam(c["eyes"][0]), OwnCam(c["eyes"][1])
    dlt = math.atan(1.0 / cl.fx)
    b = float(c["ipd_m"])
    w, h = c["image_size_wh"]
    f = fundamental(c)
    out: dict = {k: [] for k in ("valid", "reason", "cand", "tcand", "k_first", "k_last", "k_best", "best", "second",
                                 "curv", "refined", "offset", "uv_est", "uv_disc", "theta_est", "peak_k", "peak_z",
                                 "std_l", "q_inf", "t", "l", "theta_l", "phi_l")}
    for i in np.asarray(idx, np.int64):
        r, col = divmod(int(i), CORE)
        ul, vl = col + ORIGIN, r + ORIGIN
        d_l = cl.ray(np.float64(ul), np.float64(vl))
        th_l, ph_l = float(own_theta(d_l)), float(own_phi(d_l))
        lv, lex = own_patch(cl, g_l, np.array(th_l), np.array(ph_l), dlt, half)
        std_l = float(np.std(lv)) if lex else float("nan")
        l = f @ np.array([ul, vl, 1.0])
        l = l / np.hypot(l[0], l[1])
        qu, qv, z = cr.proj(d_l)
        q = np.array([float(qu), float(qv)])
        t = np.array([l[1], -l[0]])
        tp = own_theta(cr.ray(q[0] + t[0], q[1] + t[1]))
        tm = own_theta(cr.ray(q[0] - t[0], q[1] - t[1]))
        if tp < tm:
            t = -t
        ks = np.arange(1, 4000) * spacing
        cu, cv = q[0] + ks * t[0], q[1] + ks * t[1]
        inside = (cu >= 0) & (cu <= w - 1) & (cv >= 0) & (cv <= h - 1)
        sel = np.nonzero(inside)[0]
        k_vals = (sel + 1)
        if sel.size:
            lo, hi = sel[0], sel[-1]
            k_vals = np.arange(lo + 1, hi + 2)
            cu, cv = q[0] + k_vals * spacing * t[0], q[1] + k_vals * spacing * t[1]
            cin = (cu >= 0) & (cu <= w - 1) & (cv >= 0) & (cv <= h - 1)
            dk = cr.ray(cu, cv)
            thk, phk = own_theta(dk), own_phi(dk)
            with np.errstate(divide="ignore", invalid="ignore"):
                den = 1.0 / np.tan(th_l) - 1.0 / np.tan(thk)
                rho = b / den
            adm = cin & np.isfinite(dk).all(-1) & (np.cos(phk - ph_l) > 0) & (thk > th_l) & (den >= DEN) & (rho > 0)
            rv, rex = own_patch(cr, g_r, np.where(adm, thk, np.pi / 2), np.full(thk.shape, ph_l), dlt, half)
            adm &= rex
            rstd = np.std(rv, axis=-1)
            tex = adm & (rstd >= min_std)
            z_all = own_zncc(np.broadcast_to(lv, rv.shape), rv)
            S = [float(z_all[j]) if tex[j] else None for j in range(k_vals.size)]
        else:
            adm = tex = np.zeros(0, bool)
            thk = np.zeros(0)
            S = []
        ltex = bool(lex) and std_l >= min_std
        dec = own_decide(S, sep, topk, bound, spacing) if S else {"has": False}
        valid = ltex and dec["has"]
        reason = 4 if not lex else (1 if not ltex else (2 if adm.sum() == 0 else (3 if not dec["has"] else 0)))
        out["valid"].append(valid)
        out["reason"].append(reason)
        out["cand"].append(int(adm.sum()))
        out["tcand"].append(int(tex.sum()))
        out["k_first"].append(int(k_vals[np.argmax(adm)]) if adm.any() else -1)
        out["k_last"].append(int(k_vals[len(adm) - 1 - np.argmax(adm[::-1])]) if adm.any() else -1)
        out["std_l"].append(std_l)
        out["q_inf"].append(q)
        out["t"].append(t)
        out["l"].append(l)
        out["theta_l"].append(th_l)
        out["phi_l"].append(ph_l)
        if valid:
            j = dec["best"]
            kb = int(k_vals[j])
            s_est = kb * spacing + dec["offset"] * spacing
            uv_e = q + s_est * t
            out["k_best"].append(kb)
            out["best"].append(S[j])
            out["second"].append(S[dec["peaks"][1]] if len(dec["peaks"]) > 1 else float("nan"))
            out["curv"].append(dec["curv"] if dec["curv"] is not None else float("nan"))
            out["refined"].append(bool(dec["refined"]))
            out["offset"].append(dec["offset"])
            out["uv_est"].append(uv_e)
            out["uv_disc"].append(q + kb * spacing * t)
            out["theta_est"].append(float(own_theta(cr.ray(uv_e[0], uv_e[1]))))
            pk = [int(k_vals[p]) for p in dec["peaks"]] + [-1] * (topk - len(dec["peaks"]))
            pz = [S[p] for p in dec["peaks"]] + [float("nan")] * (topk - len(dec["peaks"]))
            out["peak_k"].append(pk[:topk])
            out["peak_z"].append(pz[:topk])
        else:
            nan = float("nan")
            out["k_best"].append(-1)
            for kk in ("best", "second", "curv", "offset", "theta_est"):
                out[kk].append(nan)
            out["refined"].append(False)
            out["uv_est"].append(np.array([nan, nan]))
            out["uv_disc"].append(np.array([nan, nan]))
            out["peak_k"].append([-1] * topk)
            out["peak_z"].append([nan] * topk)
    res = {k: np.asarray(v) for k, v in out.items()}
    if key is not None:
        _OWN_CACHE[key] = res
    return res


def compare_records(rec: dict, own: dict, sel: np.ndarray) -> dict:
    """Field-by-field disagreement between stored record rows ``sel`` and the independent recomputation."""
    def close(a, b, tol):
        a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
        same_nan = np.isnan(a) == np.isnan(b)
        diff = np.where(np.isnan(a) | np.isnan(b), 0.0, np.abs(a - b))
        return int((~same_nan.all(axis=tuple(range(1, a.ndim))) if a.ndim > 1 else ~same_nan).sum()
                   + (diff.reshape(diff.shape[0], -1).max(axis=1) > tol).sum())

    r = {k: np.asarray(v)[sel] for k, v in rec.items()}
    pk_rec = np.where(np.isnan(r["peak_s"]), -1, np.rint(r["peak_s"] / SPACING)).astype(np.int64)
    lsign = np.sign(np.sum(r["line_l"][:, :2] * own["l"][:, :2], -1))
    ln = r["line_l"] / np.hypot(r["line_l"][:, 0], r["line_l"][:, 1])[:, None] * lsign[:, None]
    return {
        "valid_match": int((r["valid_match"] != own["valid"]).sum()),
        "reason": int((r["reason"] != own["reason"]).sum()),
        "candidate_count": int((r["candidate_count"] != own["cand"]).sum()),
        "textured_candidate_count": int((r["textured_candidate_count"] != own["tcand"]).sum()),
        "k_first": int((r["k_first"] != own["k_first"]).sum()),
        "k_last": int((r["k_last"] != own["k_last"]).sum()),
        "k_best": int((r["k_best"] != own["k_best"]).sum()),
        "refined": int((r["refined"] != own["refined"]).sum()),
        "peaks": int((pk_rec != own["peak_k"]).any(axis=1).sum()),
        "peak_zncc": close(r["peak_zncc"], own["peak_z"], 1e-9),
        "best_zncc": close(r["best_zncc"], own["best"], 1e-9),
        "second_peak_zncc": close(r["second_peak_zncc"], own["second"], 1e-9),
        "peak_curvature": close(r["peak_curvature"], own["curv"], 1e-8),
        "refinement_offset": close(r["refinement_offset_samples"], own["offset"], 1e-6),
        "uv_R_est": close(r["uv_R_est"], own["uv_est"], 1e-6),
        "uv_R_discrete": close(r["uv_R_discrete"], own["uv_disc"], 1e-8),
        "theta_R_est": close(r["theta_R_est"], own["theta_est"], 1e-9),
        "left_std": close(r["left_patch_std_u8"], own["std_l"], 1e-9),
        "theta_L": close(r["theta_L"], own["theta_l"], 1e-12),
        "phi_L": close(r["phi_L"], own["phi_l"], 1e-12),
        "q_inf": close(r["q_inf"], own["q_inf"], 1e-8),
        "line_dir": close(r["line_dir"], own["t"], 1e-9),
        "line_l": close(ln, own["l"], 1e-9),
    }


# ------------------------------------------------------------------ literal identities (contract section 3)
SHARED = Path("/home/lvelho/rd/f3d-vision")
A1C = SHARED / "previews/active-bootstrap/ab1c-safe-forward-planar-vs-spherical"
A1C_VIS_MANIFEST = (SHARED / "visuals/active-bootstrap/ab1c-safe-forward-planar-vs-spherical/visuals-manifest.json",
                    "a533366986f6027114b694562d92f7c59bfc47fe486ff7bde0773f07f6b45311")
A1C_MANIFEST_SHA = "21640f6a56474f9ed171d37ceb13571a56499ac805b1b1bbec09c6808a0d378a"
GAZES = ("gaze-1", "gaze-2", "gaze-3")
GAZE_TABLE = {"gaze-1": (191, 322, -18.75, -5.75), "gaze-2": (166, 373, 6.75, 6.75), "gaze-3": (190, 397, 18.75, -5.25)}
OBS_TMPL = "observations/{g}/acquisition/{name}"
REF_TMPL = "observations/{g}/evaluation_only/reference-observation.npz"
ORACLE_TMPL = "oracle/{g}/oracle-correspondences.npz"
SPHERICAL_TMPL = "spherical/{g}/epipolar-result.npz"
EVAL_TMPL = "evaluation/{g}/evaluation-result.npz"
OBS_PINS = {
    "observations/gaze-1/acquisition/calibration.json": "ae56ef338561a9d23d4208e36fb88862adb08e6bd8f773651ed3aa9e83224ebf",
    "observations/gaze-1/acquisition/rgb-observation.npz": "d6e2a532acf1534ed305ad63447b30b35645051a350922cbcec14dbb5388f47f",
    "observations/gaze-2/acquisition/calibration.json": "ab348665b6c86443145cfa448ac488ec101eab41277d47b0d93c3eaabfd37ec7",
    "observations/gaze-2/acquisition/rgb-observation.npz": "297c5bd689cde4a5bf9b01b53e4b643719feff6f654a25a470a2e8b627bca43d",
    "observations/gaze-3/acquisition/calibration.json": "085ff33204b84c3d7b05a92c3099bef600dd698bf6e6ab209cb0e5bfe748accd",
    "observations/gaze-3/acquisition/rgb-observation.npz": "5924f94656b6bf3536ed986f2d47433331e201d7ea911c3df7f1ef52c57a170c",
}
BENCH_PINS = {
    "oracle/gaze-1/oracle-correspondences.npz": "e83eaa7b537abaa4def50def64d0d36bf034d270baa3f4e7ce6cfb0a7512b4a6",
    "oracle/gaze-2/oracle-correspondences.npz": "fd4568d59f3b7a40aef6c11442961749e45a8c3b6c1b1fa53c8934dd636b8831",
    "oracle/gaze-3/oracle-correspondences.npz": "67d433311f1f940637573c9135d6947bad8363411cb45e52412f070874c20c73",
    "spherical/gaze-1/epipolar-result.npz": "3e5024f3a75a34819f742c231b3b448ac6b8486a840f17c9c5f780798c52cd98",
    "spherical/gaze-2/epipolar-result.npz": "d2306f9c200a11e749bf59d71b535a2f4c8a32e08850618901b9402412fee4e2",
    "spherical/gaze-3/epipolar-result.npz": "f1de4f1d6be91880067446ad8a104f875dd7e4757c2c5176be2410ed92d0b561",
    "observations/gaze-1/evaluation_only/reference-observation.npz":
        "7c458254960befefbfef160e0904dc8ab9c34bb1d3791d8f59fd55403b323f2e",
    "observations/gaze-2/evaluation_only/reference-observation.npz":
        "c8b1833ef4df720a0252b89c6886ba6788be4d94f877cfd8ba0bc4781b9e47b6",
    "observations/gaze-3/evaluation_only/reference-observation.npz":
        "740d7ad78f9afc7eb867e20df186bf40b964e31a840a5ba2e85dd4bdcd81e5d0",
}
CODE_PINS = {
    "tools/fsg_geometry.py": "ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54",
    "tools/fsg_stereo.py": "faebf0f1b3acbfde60b08830a57213bf29c708c3aa274e493ade0042eb0545e9",
    "tools/natural_bootstrap/nb1a_guard.py": "29ebca57be9e977def7a94ea45a7b0cff0f22a8b1d86b40f740f132491ebe99d",
    "tools/active_bootstrap/ab1b_spec.py": "1634e455a61879934545a1fa634a72cbb2b8ca74fd83a6ba3a977412be0e497d",
    "tools/active_bootstrap/ab1b_geometry.py": "a125dd9cc666120219e0421a09a380353d2304ed0f09681a1655962444572538",
    "tools/active_bootstrap/ab1b_visuals.py": "6dd4a203b1847e9d5f0f984c2a1727859aa035ad00adead79849bd484ca833ee",
    "tools/active_bootstrap/ab1c_visuals.py": "28054811eca774883753c2499d135cdabae37b32f6f014432bf1057dcab71a30",
    "tools/active_bootstrap/ab1c_spec.py": "53d1b7228b30883db715f3fc33a65893aa7708656c2881f2a31eef1a3ac77b1a",
    "tools/active_bootstrap/ab1c_planar.py": "1528ee92af48c5a13b621d300fe0a78dedc57f27181959d40505f2f9b19e6227",
    "tools/visual_language/style.py": "c379a2a31c9112d22bbe8989324d2ff74608c669fe84d58905509b4d62264053",
    "tools/classroom_oracle/breadth1_visuals.py": "61683aea17993da09bfddce4ed13d48da47d710d1630e40c6bdcc7a6f6d2144c",
}
ACCEPTED = {
    "AB1b geometry freeze": (SHARED / "previews/active-bootstrap/ab1b-spherical-epipolar-geometry/geometry/geometry-freeze.json",
                             "942707a858c8b76cb65db503183853d27c55000eb2e59c6de4dfbcf025d21c7a"),
    "AB1b visuals manifest": (SHARED / "visuals/active-bootstrap/ab1b-spherical-epipolar-geometry/visuals-manifest.json",
                              "a1216d2c22095f6353260efeb93b452a7b429f7a3d29b7d760db8d27a056f88c"),
}
AB1D_TOOLS = ("ab1d_spec.py", "ab1d_match.py", "ab1d_run.py", "ab1d_synthetic.py", "ab1d_visuals.py", "check_ab1d.py")
DECLARED = ({"docs/active-bootstrap/ab1d-safe-forward-natural-correspondence-contract.md",
             "docs/active-bootstrap/ab1d-safe-forward-natural-correspondence-report.md",
             "tools/repository/check_repository_layout.py"} | {f"tools/active_bootstrap/{n}" for n in AB1D_TOOLS})
CANONICAL = ("source", "match", "freeze-correspondence", "spherical", "freeze-geometry", "evaluate")
ORDER = ("source", "synthetic", "match", "freeze-correspondence", "spherical", "freeze-geometry", "evaluate", "visualize")
RECORD_KEYS = {"valid_left_patch", "valid_left_texture", "valid_match", "reason", "candidate_count",
               "textured_candidate_count", "k_first", "k_last", "k_best", "uv_R_discrete", "s_est", "uv_R_est",
               "theta_R_discrete", "theta_R_est", "best_zncc", "second_peak_zncc", "peak_margin", "peak_curvature",
               "refined", "refinement_offset_samples", "peak_count", "peak_s", "peak_uv_R", "peak_theta_R", "peak_zncc",
               "left_core_row", "left_core_col", "uv_L", "theta_L", "phi_L", "left_patch_std_u8", "q_inf", "line_dir",
               "line_l"}
PRODUCT_KEYS = {"left_core_row", "left_core_col", "uv_L", "uv_R"}
FORBIDDEN_TOKENS = ("position", "depth", "xyz", "instance", "object", "oracle", "truth", "semantic", "label", "range")
FIGURES = ("overview.png", "correspondence-error.png", "cost-landscapes.png", "natural-reconstruction.png",
           "confidence-diagnostics.png")
ORA_B, DER_B, REF_B = "ORACLE INPUT", "DERIVED", "REFERENCE / EVALUATION"
BADGES = {"overview.png": [ORA_B, DER_B, REF_B], "correspondence-error.png": [DER_B, REF_B],
          "cost-landscapes.png": [ORA_B, DER_B, REF_B], "natural-reconstruction.png": [DER_B, REF_B],
          "confidence-diagnostics.png": [DER_B, REF_B]}
SYN_CASES = 24
QKEYS = {"min": 0.0, "p05": 0.05, "median": 0.5, "p90": 0.90, "p95": 0.95, "p99": 0.99, "max": 1.0}


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


_SHA_CACHE: dict = {}


def sha_cached(path) -> str:
    p = str(Path(path).resolve())
    st = os.stat(p)
    key = (p, st.st_size, st.st_mtime_ns)
    if key not in _SHA_CACHE:
        _SHA_CACHE[key] = sha256(p)
    return _SHA_CACHE[key]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


def npz(path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def jload(path):
    return json.loads(Path(path).read_text())


def a1c(rel: str) -> Path:
    return A1C / rel


def calib_p(g):
    return a1c(OBS_TMPL.format(g=g, name="calibration.json"))


def rgb_p(g):
    return a1c(OBS_TMPL.format(g=g, name="rgb-observation.npz"))


def qd(a) -> dict | None:
    a = np.asarray(a, np.float64)
    a = a[np.isfinite(a)].ravel()
    if a.size == 0:
        return None
    return {k: float(np.quantile(a, v)) for k, v in QKEYS.items()} | {"count": int(a.size)}


def qeq(stored: dict | None, own: dict | None, rel=1e-9, ab=1e-15) -> bool:
    if stored is None or own is None:
        return stored is None and own is None
    return all(abs(stored[k] - own[k]) <= max(ab, rel * abs(own[k])) for k in own)


_CACHE: dict = {}


def cached(key, fn):
    if key not in _CACHE:
        _CACHE[key] = fn()
    return _CACHE[key]


class Ctx:
    """Lazy access to one run (or a corruption mirror) and its visuals."""

    def __init__(self, run: Path, vis: Path, overrides: dict | None = None) -> None:
        self.run, self.vis, self.overrides = run, vis, overrides or {}
        self._m: dict = {}

    def j(self, rel):
        k = ("j", rel)
        if k not in self._m:
            self._m[k] = jload(self.run / rel)
        return self._m[k]

    def n(self, rel):
        k = ("n", rel)
        if k not in self._m:
            self._m[k] = npz(self.run / rel)
        return self._m[k]

    def rec(self, g):
        return self.n(f"match/{g}/matcher-record.npz")

    def prod(self, g):
        return self.n(f"match/{g}/natural-correspondences.npz")

    def geo(self, g):
        return self.n(f"spherical/{g}/epipolar-result.npz")

    def evr(self, g):
        return self.n(f"evaluation/{g}/evaluation-result.npz")

    def rrel(self, p: str) -> str:
        """Run-relative path for paths inside the run (mirrors keep their meaning); absolute otherwise."""
        rp = str(Path(p))
        for root in (str(self.run), str(self.overrides.get("orig_run", self.run))):
            if rp.startswith(root + "/"):
                return "RUN/" + rp[len(root) + 1:]
        return rp

    def src(self, name: str) -> str:
        return self.overrides.get("static_extra", {}).get(name, "") + (HERE / name).read_text()

    @property
    def log(self) -> list[dict]:
        if "log" not in self._m:
            self._m["log"] = [json.loads(x) for x in (self.run / "process-log.jsonl").read_text().splitlines() if x]
        return self._m["log"]


def calib(g):
    return cached(("calib", g), lambda: jload(calib_p(g)))


def gray_pair(g):
    def f():
        z = npz(rgb_p(g))
        return own_gray(z["rgb_L"]), own_gray(z["rgb_R"])
    return cached(("gray", g, sha_cached(rgb_p(g))), f)


def subset_idx(x: Ctx, g) -> np.ndarray:
    base = np.arange(SUBSET[1], CORE * CORE, SUBSET[0])
    ex = []
    try:
        man = jload(x.vis / "visuals-manifest.json")
        ex = [e["core_index"] for e in man["examples"].get(g, [])]
    except (FileNotFoundError, KeyError):
        pass
    return np.unique(np.concatenate([base, np.asarray(ex, np.int64)]))


def own_sub(x: Ctx, g) -> tuple[np.ndarray, dict]:
    idx = subset_idx(x, g)
    gl, gr = gray_pair(g)
    key = (g, sha_cached(calib_p(g)), sha_cached(rgb_p(g)))
    return idx, own_match(calib(g), gl, gr, idx, cache_key=key)


def cmp_sub(x: Ctx, g) -> dict:
    k = ("cmp", g)
    if k not in x._m:
        idx, own = own_sub(x, g)
        x._m[k] = compare_records(x.rec(g), own, idx)
    return x._m[k]


def own_left(g):
    """Own left rays / angles for the full core."""
    def f():
        c = calib(g)
        cl = OwnCam(c["eyes"][0])
        r, cc = np.divmod(np.arange(CORE * CORE), CORE)
        d = cl.ray((cc + ORIGIN).astype(np.float64), (r + ORIGIN).astype(np.float64))
        return d, own_theta(d), own_phi(d)
    return cached(("left", g), f)


# ------------------------------------------------------------------ checks
def c01(x):
    code = {p: sha_cached(REPO / p) == h for p, h in CODE_PINS.items()}
    remote = git("remote", "get-url", "origin").strip().rstrip("/").removesuffix(".git")
    anc = subprocess.run(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=REPO).returncode == 0
    ok = all(code.values()) and remote.endswith("visgraf/f3d-vision") and anc
    return ok, {"code_mismatch": [k for k, v in code.items() if not v], "remote": remote, "base_ancestor": anc}


def c02(x):
    man = cached("a1c_man", lambda: jload(a1c("manifest.json")))["files"]
    files = {k: sha_cached(a1c(k)) == h for k, h in OBS_PINS.items()}
    in_man = all(man.get(k) == h for k, h in OBS_PINS.items()) and all(man.get(k) == h for k, h in BENCH_PINS.items())
    summ = all(x.j(f"match/{g}/match-summary.json")["inputs"]["calibration"]["sha256"]
               == OBS_PINS[OBS_TMPL.format(g=g, name="calibration.json")]
               and x.j(f"match/{g}/match-summary.json")["inputs"]["rgb_observation"]["sha256"]
               == OBS_PINS[OBS_TMPL.format(g=g, name="rgb-observation.npz")] for g in GAZES)
    src = x.j("source/source-manifest.json")
    ok = (all(files.values()) and in_man and summ and sha_cached(a1c("manifest.json")) == A1C_MANIFEST_SHA
          and sha_cached(A1C_VIS_MANIFEST[0]) == A1C_VIS_MANIFEST[1] and all(src["identity"].values()))
    return ok, {"files": files, "in_a1c_manifest": in_man, "summaries": summ}


def c03(x):
    blender = [e for e in x.log if "blender" in e or "render" in e.get("command", "")]
    exr = [str(p) for p in x.run.rglob("*") if p.suffix in (".exr", ".blend")]
    bad = []
    for name in AB1D_TOOLS[:-1]:
        tree = ast.parse(x.src(name))
        for node in ast.walk(tree):
            ids = []
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                ids = [a.name for a in node.names] + ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            elif isinstance(node, ast.Name):
                ids = [node.id]
            elif isinstance(node, ast.Attribute):
                ids = [node.attr]
            for i in ids:
                if any(t in (i or "") for t in ("bpy", "ab1c_render", "ab1a_render", "render_foveated", "bl_common")):
                    bad.append((name, i))
    return not blender and not exr and not bad, {"blender_log": len(blender), "exr_or_blend": exr[:3], "ast": bad}


def c04(x):
    src = x.j("source/source-manifest.json")["gazes"]
    tab = {g: (src[g]["row"], src[g]["col"], src[g]["yaw_deg"], src[g]["pitch_deg"]) for g in src}
    cal = {g: tuple(calib(g)["gaze_yaw_pitch_deg"]) for g in GAZES}
    heads = {json.dumps([calib(g)["head_R_wh"], calib(g)["head_origin_w_m"]]) for g in GAZES}
    ok = (tab == GAZE_TABLE and all(cal[g] == GAZE_TABLE[g][2:] for g in GAZES) and len(heads) == 1
          and tuple(src) == GAZES)
    return ok, {"gazes": tab, "single_head_pose": len(heads) == 1}


def guard_counts(x: Ctx, events) -> dict:
    paths = [e["path"] for e in events if e.get("event") == "open"]
    pos = sum(p.endswith("reference-observation.npz") or p.endswith(".exr") or "/evaluation_only/" in p for p in paths)
    ora = sum("oracle-correspondences" in p or p.startswith(str(A1C) + "/oracle/") for p in paths)
    ev = sum("evaluation-result" in p or "instance-catalog" in p
             or any(p.startswith(str(A1C) + f"/{s}/") for s in ("evaluation", "planar", "comparison", "spherical", "freeze"))
             for p in paths)
    return {"position": pos, "oracle": ora, "evaluation": ev}


def c05(x):
    bad = {}
    for g in GAZES:
        r = x.j(f"match/{g}/match-opened-files.json")
        want = {str(calib_p(g).resolve()), str(rgb_p(g).resolve())}
        own = guard_counts(x, r["events"])
        p = {"reads_exactly_two": set(r["data_reads"]) == want and set(r["allow_read"]) == want,
             "violations_0": not r["violations"] and r["truth_firewall_violations"] == 0,
             "recorded_truth_reads_0": not any(r[k] for k in ("position_reads", "object_index_reads", "oracle_reads",
                                                              "evaluation_reads")),
             "own_truth_reads_0": not any(own.values()),
             "no_sgbm_tripwire": not r["cv2_tripwire_calls"], "no_learned_or_render_module": not any(r["modules_loaded"].values())}
        if not all(p.values()):
            bad[g] = p
    return not bad, bad


def c06(x):
    bad = {}
    for g in GAZES:
        r = x.j(f"spherical/{g}/spherical-opened-files.json")
        want = {str(calib_p(g).resolve()), f"RUN/match/{g}/natural-correspondences.npz"}
        got = {x.rrel(p) for p in r["data_reads"]}
        own = guard_counts(x, r["events"])
        p = {"reads_exactly_two": got == want, "violations_0": not r["violations"], "own_truth_reads_0": not any(own.values()),
             "no_cv2_matcher_planar": not any(r["modules_loaded"].values())}
        if not all(p.values()):
            bad[g] = p
    return not bad, bad


def c07(x):
    bad = []
    r, cc = np.divmod(np.arange(CORE * CORE), CORE)
    for g in GAZES:
        rec = x.rec(g)
        ok = (np.array_equal(rec["left_core_row"], r) and np.array_equal(rec["left_core_col"], cc)
              and np.array_equal(rec["uv_L"], np.stack([cc + ORIGIN, r + ORIGIN], -1).astype(np.float64))
              and set(rec) == RECORD_KEYS and len(rec["valid_match"]) == CORE * CORE)
        if not ok:
            bad.append(g)
    return not bad, {"bad": bad}


def c08(x):
    worst = {}
    for g in GAZES:
        _, th, ph = own_left(g)
        rec = x.rec(g)
        worst[g] = float(max(np.abs(rec["theta_L"] - th).max(), np.abs(rec["phi_L"] - ph).max()))
    return all(v <= 1e-12 for v in worst.values()), worst


def c09(x):
    out = {}
    for g in GAZES:
        c = calib(g)
        rec = x.rec(g)
        f = fundamental(c)
        ql = np.concatenate([rec["uv_L"], np.ones((CORE * CORE, 1))], 1)
        lf = ql @ f.T
        lf = lf / np.hypot(lf[:, 0], lf[:, 1])[:, None]
        ls = rec["line_l"] / np.hypot(rec["line_l"][:, 0], rec["line_l"][:, 1])[:, None]
        ang = np.abs(ls[:, 0] * lf[:, 1] - ls[:, 1] * lf[:, 0])
        d, _, _ = own_left(g)
        cr = OwnCam(c["eyes"][1])
        qu, qv, _ = cr.proj(d)
        dq = np.hypot(rec["q_inf"][:, 0] - qu, rec["q_inf"][:, 1] - qv)
        on = np.abs(np.sum(lf[:, :2] * rec["q_inf"], 1) + lf[:, 2])
        t = rec["line_dir"]
        perp = np.abs(np.sum(t * lf[:, :2], 1))
        unit = np.abs(np.hypot(t[:, 0], t[:, 1]) - 1)
        thp = own_theta(cr.ray(rec["q_inf"][:, 0] + t[:, 0], rec["q_inf"][:, 1] + t[:, 1]))
        thm = own_theta(cr.ray(rec["q_inf"][:, 0] - t[:, 0], rec["q_inf"][:, 1] - t[:, 1]))
        out[g] = {"max_angle": float(ang.max()), "max_qinf_diff_px": float(dq.max()), "max_qinf_off_line_px": float(on.max()),
                  "max_dir_dot_normal": float(perp.max()), "max_unit_err": float(unit.max()),
                  "theta_increases": bool(np.all(thp > thm))}
    ok = all(v["max_angle"] <= 1e-9 and v["max_qinf_diff_px"] <= 1e-8 and v["max_qinf_off_line_px"] <= 1e-8
             and v["max_dir_dot_normal"] <= 1e-9 and v["max_unit_err"] <= 1e-12 and v["theta_increases"]
             for v in out.values())
    return ok, out


def sub_fields(*fields):
    def chk(x):
        out = {g: {f: cmp_sub(x, g)[f] for f in fields} for g in GAZES}
        return all(n == 0 for v in out.values() for n in v.values()), out
    return chk


c10 = sub_fields("candidate_count", "textured_candidate_count", "k_first", "k_last", "q_inf", "line_dir", "line_l")


def c11(x):
    out = {}
    for g in GAZES:
        rec = x.rec(g)
        v = rec["valid_match"]
        q, t = rec["q_inf"][v], rec["line_dir"][v]
        uv = rec["uv_R_est"][v]
        s = np.sum((uv - q) * t, 1)
        perp = np.abs((uv - q)[:, 0] * -t[:, 1] + (uv - q)[:, 1] * t[:, 0])
        kd = rec["k_best"][v].astype(np.float64)
        disc = q + kd[:, None] * SPACING * t
        pk = rec["peak_s"][v]
        out[g] = {"max_perp_px": float(perp.max(initial=0)), "max_s_diff": float(np.abs(s - rec["s_est"][v]).max(initial=0)),
                  "max_disc_diff": float(np.abs(disc - rec["uv_R_discrete"][v]).max(initial=0)),
                  "peaks_on_integer_samples": bool(np.all(np.isnan(pk) | (np.abs(pk / SPACING - np.rint(pk / SPACING)) == 0))),
                  "k_first_ge_1": bool(np.all(rec["k_first"][rec["candidate_count"] > 0] >= 1))}
    ok = all(o["max_perp_px"] <= 1e-8 and o["max_s_diff"] <= 1e-8 and o["max_disc_diff"] <= 1e-9
             and o["peaks_on_integer_samples"] and o["k_first_ge_1"] for o in out.values())
    return ok, out


def c12(x):
    out = {g: {f: cmp_sub(x, g)[f] for f in ("left_std", "reason", "valid_match")} for g in GAZES}
    rule = {}
    for g in GAZES:
        rec = x.rec(g)
        low = rec["left_patch_std_u8"] < MIN_STD
        rule[g] = bool(np.array_equal(low, rec["reason"] == 1) and np.array_equal(~low, rec["valid_left_texture"]))
    return all(n == 0 for v in out.values() for n in v.values()) and all(rule.values()), {"subset": out, "texture_rule": rule}


c13 = sub_fields("best_zncc", "peak_zncc", "second_peak_zncc")
c14 = sub_fields("k_best", "uv_R_discrete")


def c15(x):
    sub = {g: cmp_sub(x, g)["peaks"] for g in GAZES}
    inv = {}
    for g in GAZES:
        rec = x.rec(g)
        v = rec["valid_match"]
        pk, pz = rec["peak_s"][v], rec["peak_zncc"][v]
        n = rec["peak_count"][v]
        filled = np.isfinite(pk)
        sep = True
        for a in range(TOPK):
            for b in range(a + 1, TOPK):
                both = filled[:, a] & filled[:, b]
                sep &= bool(np.all(np.abs(pk[both, a] - pk[both, b]) >= SEP))
        desc = bool(np.all(np.where(filled[:, 1:], pz[:, 1:] <= pz[:, :-1] + TIE, True)))
        first = bool(np.all(pk[:, 0] == rec["k_best"][v] * SPACING))
        sec = np.where(filled[:, 1], pz[:, 1], np.nan)
        marg = bool(np.allclose(rec["second_peak_zncc"][v], sec, equal_nan=True, rtol=0, atol=0)
                    and np.allclose(rec["peak_margin"][v], rec["best_zncc"][v] - sec, equal_nan=True, rtol=0, atol=0))
        inv[g] = {"separation_ge_3": sep, "descending": desc, "first_is_best": first, "count_le_8": bool(n.max(initial=0) <= TOPK),
                  "count_matches": bool(np.array_equal(n, filled.sum(1))), "second_and_margin": marg,
                  "slots": int(pk.shape[1]) if pk.ndim == 2 else -1}
    ok = all(n == 0 for n in sub.values()) and all(all(v for k, v in o.items() if k != "slots") and o["slots"] == TOPK
                                                  for o in inv.values())
    return ok, {"subset_peak_mismatch": sub, "invariants": inv}


def c16(x):
    sub = {g: {f: cmp_sub(x, g)[f] for f in ("refined", "refinement_offset", "peak_curvature", "uv_R_est", "theta_R_est")}
           for g in GAZES}
    inv = {}
    for g in GAZES:
        rec = x.rec(g)
        v = rec["valid_match"]
        off, ref, cur = rec["refinement_offset_samples"][v], rec["refined"][v], rec["peak_curvature"][v]
        inv[g] = {"bound": bool(np.all(np.abs(off) <= BOUND)), "zero_when_unrefined": bool(np.all(off[~ref] == 0)),
                  "refined_needs_negative_curvature": bool(np.all(cur[ref] < 0)),
                  "s_est": bool(np.allclose(rec["s_est"][v], rec["k_best"][v] * SPACING + off * SPACING, rtol=0, atol=1e-12)),
                  "refined_fraction": float(ref.mean()) if ref.size else 0.0}
    ok = (all(n == 0 for o in sub.values() for n in o.values())
          and all(o["bound"] and o["zero_when_unrefined"] and o["refined_needs_negative_curvature"] and o["s_est"]
                  for o in inv.values()))
    return ok, {"subset": sub, "invariants": inv}


def c17(x):
    out = {}
    for g in GAZES:
        rec = x.rec(g)
        expect_valid = rec["valid_left_texture"] & (rec["textured_candidate_count"] > 0)
        out[g] = {"valid_is_texture_and_support_only": bool(np.array_equal(rec["valid_match"], expect_valid)),
                  "reason_0_is_valid": bool(np.array_equal(rec["reason"] == 0, rec["valid_match"])),
                  "min_best_zncc": float(np.nanmin(rec["best_zncc"])) if rec["valid_match"].any() else None,
                  "min_margin": float(np.nanmin(rec["peak_margin"])) if np.isfinite(rec["peak_margin"]).any() else None}
    ok = all(o["valid_is_texture_and_support_only"] and o["reason_0_is_valid"] for o in out.values())
    return ok, out


def c18(x):
    out = {}
    for g in GAZES:
        rec, geo = x.rec(g), x.geo(g)
        v = rec["valid_match"]
        out[g] = {"theta_R_gt_theta_L": bool(np.all(rec["theta_R_est"][v] > rec["theta_L"][v])),
                  "all_triangulated": bool(np.all(geo["valid_epi"])), "rho_positive": bool(np.all(geo["rho"] > 0)),
                  "positive_ranges": bool(np.all(geo["s_L"] > 0) and np.all(geo["s_R"] > 0))}
    return all(all(o.values()) for o in out.values()), out


def c19(x):
    out = {}
    for g in GAZES:
        rec, p = x.rec(g), x.prod(g)
        v = rec["valid_match"]
        keys_ok = set(p) == PRODUCT_KEYS and not [k for k in p for t in FORBIDDEN_TOKENS if t in k.lower()]
        same = keys_ok and (np.array_equal(p["left_core_row"], rec["left_core_row"][v])
                            and np.array_equal(p["left_core_col"], rec["left_core_col"][v])
                            and np.array_equal(p["uv_L"], rec["uv_L"][v]) and np.array_equal(p["uv_R"], rec["uv_R_est"][v])
                            and p["uv_R"].dtype == np.float64 and p["left_core_row"].dtype == np.int32)
        rk = not [k for k in rec for t in FORBIDDEN_TOKENS if t in k.lower()]
        out[g] = {"product_keys": keys_ok, "product_equals_valid_records": bool(same), "record_truth_free": rk}
    return all(all(o.values()) for o in out.values()), out


def c20(x):
    fz = x.j("match/correspondence-freeze.json")
    want = {f"match/{g}/{n}" for g in GAZES for n in ("matcher-record.npz", "natural-correspondences.npz",
                                                       "match-summary.json", "match-opened-files.json")}
    bad = [n for n, h in fz["files"].items() if sha256(x.run / n) != h]
    used = all(x.j(f"spherical/{g}/spherical-summary.json")["inputs"]["correspondences"]["sha256"]
               == fz["files"][f"match/{g}/natural-correspondences.npz"] for g in GAZES)
    return not bad and set(fz["files"]) == want and used, {"mismatch": bad, "spherical_used_frozen_product": used}


def c21(x):
    import ab1b_geometry as BG
    out = {}
    for g in GAZES:
        c = calib(g)
        p, geo = x.prod(g), x.geo(g)
        cl, cr = OwnCam(c["eyes"][0]), OwnCam(c["eyes"][1])
        dl, dr = cl.ray(p["uv_L"][:, 0], p["uv_L"][:, 1]), cr.ray(p["uv_R"][:, 0], p["uv_R"][:, 1])
        tl, tr = own_theta(dl), own_theta(dr)
        b = float(c["ipd_m"])
        rho = b * np.sin(tl) * np.sin(tr) / np.sin(tr - tl)
        pp = cl.o + (rho / np.sin(tl))[:, None] * dl
        summ = x.j(f"spherical/{g}/spherical-summary.json")
        out[g] = {"max_P_diff_m": float(np.abs(pp - geo["P_epi"]).max(initial=0)),
                  "max_phi_residual": float(np.abs(geo["phi_residual"]).max(initial=0)),
                  "config": summ["geometry_config_sha256"] == BG.SP.config_sha256(BG.SP.GEOMETRY),
                  "rows": bool(np.array_equal(geo["left_core_row"], p["left_core_row"]))}
    ok = all(o["max_P_diff_m"] <= 1e-9 and o["max_phi_residual"] <= 1e-12 and o["config"] and o["rows"] for o in out.values())
    return ok, out


def c22(x):
    fz = x.j("freeze/geometry-freeze.json")
    want = {n for g in GAZES for n in [f"match/{g}/natural-correspondences.npz"] + [
        f"spherical/{g}/{m}" for m in ("left-core-rays.npz", "epipolar-result.npz", "spherical-summary.json",
                                       "spherical-opened-files.json")]}
    bad = [n for n, h in fz["files"].items() if sha256(x.run / n) != h]
    ev = x.j("evaluation/evaluation-opened-files.json")["events"]
    labels = [e.get("label") for e in ev if e.get("event") == "mark"]
    pos = {lab: i for i, e in enumerate(ev) for lab in [e.get("label")] if e.get("event") == "mark"}
    bench = {str(a1c(k).resolve()) for k in BENCH_PINS}
    first_bench = min((i for i, e in enumerate(ev) if e.get("event") == "open" and e["path"] in bench), default=None)
    order = (labels == ["freezes_verified", "reference_access_begins"] and first_bench is not None
             and pos["freezes_verified"] < pos["reference_access_begins"] < first_bench)
    return not bad and set(fz["files"]) == want and order, {"mismatch": bad, "order_ok": order, "labels": labels}


def own_eval(x: Ctx, g) -> dict:
    """Own recomputation of the primary error, local scale, ORACLE-ON-CURVE and ranks (all evaluable rows)."""
    k = ("own_eval", g)
    if k in x._m:
        return x._m[k]
    c = calib(g)
    rec = x.rec(g)
    ora = cached(("ora", g), lambda: npz(a1c(ORACLE_TMPL.format(g=g))))
    oi = ora["left_core_row"].astype(np.int64) * CORE + ora["left_core_col"]
    ov = np.zeros(CORE * CORE, bool)
    ov[oi] = True
    nv = rec["valid_match"]
    cls = np.where(ov & nv, 0, np.where(ov, 1, np.where(nv, 2, 3)))
    e_idx = np.nonzero(ov & nv)[0]
    uv = np.full((CORE * CORE, 2), np.nan)
    uv[oi] = ora["uv_R"]
    cr = OwnCam(c["eyes"][1])
    th_or = own_theta(cr.ray(uv[e_idx, 0], uv[e_idx, 1]))
    e_th = rec["theta_R_est"][e_idx] - th_or
    _, _, ph = own_left(g)
    qu, qv, _ = cr.proj(own_dir(th_or, ph[e_idx]))
    q, t = rec["q_inf"][e_idx], rec["line_dir"][e_idx]
    s_oc = (qu - q[:, 0]) * t[:, 0] + (qv - q[:, 1]) * t[:, 1]

    def lt(s):
        return own_theta(cr.ray(q[:, 0] + s * t[:, 0], q[:, 1] + s * t[:, 1]))
    scale = lt(s_oc + 0.5) - lt(s_oc - 0.5)
    within = np.abs(rec["peak_s"][e_idx] - s_oc[:, None]) <= PEAK_RADIUS
    rank = np.where(within.any(1), np.argmax(within, 1) + 1, TOPK + 1)
    out = {"cls": cls, "e_idx": e_idx, "th_or": th_or, "e_th": e_th, "s_oc": s_oc, "scale": scale, "e_px": e_th / scale,
           "rank": rank, "ov": ov}
    x._m[k] = out
    return out


def c23(x):
    out = {}
    for g in GAZES:
        o, e = own_eval(x, g), x.evr(g)
        s = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]
        same_set = np.array_equal(e["core_index"], o["e_idx"]) and np.array_equal(e["class_map"], o["cls"])
        d = float(np.abs(e["e_theta"] - o["e_th"]).max(initial=0)) if same_set else float("inf")
        cnt = s["counts"]
        counts = (cnt["oracle_correspondences"] == int(o["ov"].sum()) and cnt["evaluable"] == o["e_idx"].size
                  and cnt["natural_valid"] == int(x.rec(g)["valid_match"].sum())
                  and cnt["natural_valid_non_oracle"] == int((o["cls"] == 2).sum()))
        out[g] = {"same_evaluable_set": bool(same_set), "max_e_theta_diff": d, "counts": counts,
                  "summary_abs": qeq(s["primary"]["e_theta_abs_rad"], qd(np.abs(o["e_th"])), rel=1e-6, ab=1e-12),
                  "summary_signed": qeq(s["primary"]["e_theta_signed_rad"], qd(o["e_th"]), rel=1e-6, ab=1e-12)}
    ok = all(v["same_evaluable_set"] and v["max_e_theta_diff"] <= 1e-12 and v["counts"] and v["summary_abs"]
             and v["summary_signed"] for v in out.values())
    return ok, out


def c24(x):
    out = {}
    for g in GAZES:
        o, e = own_eval(x, g), x.evr(g)
        s = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["primary"]
        rs = float(np.abs(e["local_scale_rad_per_px"] / o["scale"] - 1).max(initial=0))
        rp = np.abs(e["e_px"] - o["e_px"]) / np.maximum(np.abs(o["e_px"]), 1e-6)
        fr = {f"{b:g}": float((np.abs(o["e_px"]) <= b).mean()) for b in PX_BINS} if o["e_px"].size else None
        frs = s["px_equivalent_fractions"]
        frac_ok = (frs is None and fr is None) or all(abs(frs[k] - fr[k]) <= 1e-12 for k in fr)
        out[g] = {"max_scale_rel": rs, "max_epx_rel": float(rp.max(initial=0)), "fractions": frac_ok,
                  "summary_abs_px": qeq(s["px_equivalent_abs"], qd(np.abs(o["e_px"])), rel=1e-5, ab=1e-9)}
    ok = all(v["max_scale_rel"] <= 1e-6 and v["max_epx_rel"] <= 1e-5 and v["fractions"] and v["summary_abs_px"]
             for v in out.values())
    return ok, out


def c25(x):
    out = {}
    for g in GAZES:
        o, e = own_eval(x, g), x.evr(g)
        s = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["landscape"]
        dso = float(np.abs(e["s_oracle_on_curve"] - o["s_oc"]).max(initial=0))
        rank_ok = bool(np.array_equal(e["oracle_rank"], o["rank"]))
        tops = {f"top{k}": float((o["rank"] <= k).mean()) for k in (1, 3, 5, 8)}
        tops["worse_than_top8"] = float((o["rank"] > TOPK).mean())
        tops_ok = all(abs(s["top_fractions"][k] - v) <= 1e-12 for k, v in tops.items()) if o["rank"].size else True
        # own ZNCC at ORACLE-ON-CURVE (and the offsets) on the subset
        idx = subset_idx(x, g)
        pos = np.nonzero(np.isin(o["e_idx"], idx))[0]
        c = calib(g)
        gl, gr = gray_pair(g)
        cl, cr = OwnCam(c["eyes"][0]), OwnCam(c["eyes"][1])
        dlt = math.atan(1.0 / cl.fx)
        _, thl, phl = own_left(g)
        ii = o["e_idx"][pos]
        lv, _ = own_patch(cl, gl, thl[ii], phl[ii], dlt)
        zs = []
        q, t = x.rec(g)["q_inf"][ii], x.rec(g)["line_dir"][ii]
        for off in OFFSETS:
            ss = o["s_oc"][pos] + off
            th = own_theta(cr.ray(q[:, 0] + ss * t[:, 0], q[:, 1] + ss * t[:, 1]))
            rv, rex = own_patch(cr, gr, th, phl[ii], dlt)
            z = own_zncc(lv, rv)
            zs.append(np.where(rex & (np.std(rv, axis=-1) >= MIN_STD), z, np.nan))
        zs = np.stack(zs, 1)
        rv, rex = own_patch(cr, gr, o["th_or"][pos], phl[ii], dlt)
        zor = np.where(rex & (np.std(rv, axis=-1) >= MIN_STD), own_zncc(lv, rv), np.nan)
        dz = np.nanmax(np.abs(e["zncc_oracle"][pos] - zor), initial=0)
        nanmatch = bool(np.array_equal(np.isnan(e["zncc_oracle"][pos]), np.isnan(zor)))
        doff = np.nanmax(np.abs(e["zncc_offsets"][pos] - zs), initial=0)
        perp = float(np.max(e["oracle_perpendicular_px"], initial=0))
        out[g] = {"max_s_oc_diff_px": dso, "ranks": rank_ok, "top_fractions": tops_ok, "subset_zncc_oracle_diff": float(dz),
                  "unscorable_match": nanmatch, "subset_offsets_diff": float(doff), "max_perpendicular_px": perp}
    ok = all(v["max_s_oc_diff_px"] <= 1e-6 and v["ranks"] and v["top_fractions"] and v["subset_zncc_oracle_diff"] <= 1e-8
             and v["unscorable_match"] and v["subset_offsets_diff"] <= 1e-8 and v["max_perpendicular_px"] <= 1e-9
             for v in out.values())
    return ok, out


def own_metric(x: Ctx, g) -> dict:
    o = own_eval(x, g)
    e_idx = o["e_idx"]
    c = calib(g)
    geo = x.geo(g)
    gi = geo["left_core_row"].astype(np.int64) * CORE + geo["left_core_col"]
    pn = np.full((CORE * CORE, 3), np.nan)
    pn[gi] = geo["P_epi"]
    perf = cached(("perf", g), lambda: npz(a1c(SPHERICAL_TMPL.format(g=g))))
    pi = perf["left_core_row"].astype(np.int64) * CORE + perf["left_core_col"]
    pp = np.full((CORE * CORE, 3), np.nan)
    pp[pi] = perf["P_epi"]
    pos = cached(("pos", g), lambda: npz(a1c(REF_TMPL.format(g=g)))["position_w_L"])
    r, cc = e_idx // CORE + ORIGIN, e_idx % CORE + ORIGIN
    w = np.asarray(pos)[r, cc].astype(np.float64)
    pref = (w - np.asarray(c["head_origin_w_m"])) @ np.asarray(c["head_R_wh"])
    ol = np.asarray(c["eyes"][0]["centre_h_m"])
    out = {"P_nat": pn[e_idx], "P_perf": pp[e_idx], "P_ref": pref}
    for name, pb in (("vs_perfect", pp[e_idx]), ("vs_position", pref)):
        e3 = np.linalg.norm(pn[e_idx] - pb, axis=1)
        rad = np.linalg.norm(pn[e_idx] - ol, axis=1) - np.linalg.norm(pb - ol, axis=1)
        out[name] = (e3, rad)
    return out


def c26(x):
    out = {}
    for g in GAZES:
        m, e = own_metric(x, g), x.evr(g)
        s = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["metric"]
        res = {"P_nat": float(np.abs(e["P_natural"] - m["P_nat"]).max(initial=0)),
               "P_perfect": float(np.abs(e["P_perfect"] - m["P_perf"]).max(initial=0)),
               "P_reference": float(np.abs(e["P_reference"] - m["P_ref"]).max(initial=0))}
        ok = all(v <= 1e-9 for v in res.values())
        for name in ("vs_perfect", "vs_position"):
            e3, rad = m[name]
            ok &= bool(np.allclose(e[f"error_3d_{name}_m"], e3, rtol=0, atol=1e-12))
            ok &= qeq(s[name]["error_3d_m"], qd(e3), rel=1e-9, ab=1e-15) and qeq(s[name]["radial_signed_m"], qd(rad), rel=1e-9,
                                                                                  ab=1e-15)
            fr = {f"{b:g}": float((e3 <= b).mean()) for b in METRIC_M} if e3.size else None
            ok &= (fr is None and s[name]["fraction_3d_within_m"] is None) or all(
                abs(s[name]["fraction_3d_within_m"][k] - v) <= 1e-12 for k, v in fr.items())
        ab1c_eval = a1c(EVAL_TMPL.format(g=g))
        if ab1c_eval.exists():
            ev = cached(("a1c_eval", g), lambda: npz(ab1c_eval))
            ti = ev["left_core_row"].astype(np.int64) * CORE + ev["left_core_col"]
            pt = np.full((CORE * CORE, 3), np.nan)
            pt[ti] = ev["P_truth"]
            res["vs_ab1c_P_truth"] = float(np.abs(pt[own_eval(x, g)["e_idx"]] - m["P_ref"]).max(initial=0))
            ok &= res["vs_ab1c_P_truth"] <= 1e-9
        out[g] = res | {"ok": bool(ok)}
    return all(v["ok"] for v in out.values()), out


def own_strata(values, err, top1):
    fin = np.isfinite(values)
    bins = []
    if fin.sum() >= 4:
        q25, q50, q75 = (float(np.quantile(values[fin], a)) for a in (0.25, 0.5, 0.75))
        ms = [fin & (values <= q25), fin & (values > q25) & (values <= q50), fin & (values > q50) & (values <= q75),
              fin & (values > q75)]
    else:
        ms = []
    ms.append(~fin)
    for m in ms:
        e = np.abs(err[m])
        bins.append((int(m.sum()), float(np.median(e)) if e.size else None, float(top1[m].mean()) if e.size else None))
    return bins


def c27(x):
    out = {}
    for g in GAZES:
        o = own_eval(x, g)
        rec = x.rec(g)
        conf = x.j("evaluation/evaluation-summary.json")["per_gaze"][g]["confidence"]
        top1 = o["rank"] == 1
        ok = True
        for key, vals in (("peak_margin", rec["peak_margin"][o["e_idx"]]),
                          ("left_patch_std_u8", rec["left_patch_std_u8"][o["e_idx"]]),
                          ("best_zncc", rec["best_zncc"][o["e_idx"]]), ("peak_curvature", rec["peak_curvature"][o["e_idx"]]),
                          ("candidate_count", rec["candidate_count"][o["e_idx"]].astype(np.float64))):
            mine = own_strata(vals, o["e_px"], top1)
            st = [(b["count"], b["median_abs_px"], b["oracle_top1"]) for b in conf[key]["bins"]]
            ok &= len(st) == len(mine) and all(a[0] == b[0] and (a[1] is None) == (b[1] is None)
                                               and (a[1] is None or abs(a[1] - b[1]) <= 1e-6 * max(1, abs(b[1])))
                                               and (a[2] is None or abs(a[2] - b[2]) <= 1e-12)
                                               for a, b in zip(st, mine))
        out[g] = bool(ok)
    return all(out.values()), out


def c28(x):
    out = {}
    for g in GAZES:
        rec = x.rec(g)
        s = x.j(f"match/{g}/match-summary.json")
        c = s["counts"]
        ok = (c["left_core"] == CORE * CORE and c["natural_valid"] == int(rec["valid_match"].sum())
              and c["left_textured"] == int(rec["valid_left_texture"].sum())
              and c["product_pairs"] == len(x.prod(g)["left_core_row"]) and c["refined"] == int(rec["refined"].sum())
              and all(c["reasons"][name] == int((rec["reason"] == k).sum())
                      for k, name in enumerate(("VALID", "LOW_TEXTURE", "NO_SEARCH_SUPPORT", "NO_TEXTURED_CANDIDATE",
                                                "LEFT_PATCH_OUTSIDE")))
              and qeq(s["candidates"]["admissible"], qd(rec["candidate_count"]), rel=1e-12, ab=1e-12)
              and qeq(s["distributions"]["best_zncc"], qd(rec["best_zncc"][rec["valid_match"]]), rel=1e-12, ab=1e-15))
        out[g] = bool(ok)
    return all(out.values()), out


def c29(x):
    import ab1d_visuals as V
    figs, _ = V.render_all(x.run)
    diff = [n for n in FIGURES if V.png_bytes(figs[n]) != (x.vis / n).read_bytes()]
    return not diff, {"differ": diff}


def c30(x):
    man = jload(x.vis / "visuals-manifest.json")
    badges = {n: man["figures"][n]["badges"] for n in FIGURES}
    hashes = all(man["figures"][n]["sha256"] == sha256(x.vis / n) for n in FIGURES)
    ctl = any("CONTROLLER" in b for v in badges.values() for b in v)
    # own deterministic example rules
    ex_ok = True
    for g in GAZES:
        e = x.evr(g)
        idx = e["core_index"].astype(np.int64)
        err = np.abs(e["e_px"])
        mar = x.rec(g)["peak_margin"][idx]
        fin = np.isfinite(err)

        def pick(score, mask):
            m = mask & np.isfinite(score)
            return None if not m.any() else int(idx[m][score[m] == score[m].min()].min())
        want = [("median-error", pick(np.abs(err - np.median(err[fin])), fin)),
                ("high-confidence low-error", pick(-mar, fin & (err <= 0.25))),
                ("smallest peak margin", pick(mar, fin)),
                ("large-error percentile", pick(np.abs(err - np.quantile(err[fin], 0.99)), fin))]
        want = [{"rule": n, "core_index": i} for n, i in want if i is not None]
        ex_ok &= man["examples"][g] == want
    return badges == BADGES and hashes and not ctl and ex_ok, {"badges_ok": badges == BADGES, "hashes": hashes,
                                                               "examples": ex_ok}


def c31(x):
    forbid = ("StereoSGBM", "StereoBM", "stereoRectify", "initUndistortRectifyMap", "torch", "tensorflow", "onnx",
              "sklearn", "keras", "controller", "fsg6f", "move_head", "rotate_head", "recenter", "head_pose_update",
              "ab1c_planar", "rectification")
    truthy = ("position", "instance", "oracle", "reference", "Position", "Object")
    bad = []
    for name in AB1D_TOOLS[:-1]:
        tree = ast.parse(x.src(name))
        for node in ast.walk(tree):
            ids = []
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                ids = [a.name for a in node.names] + ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            elif isinstance(node, ast.Name):
                ids = [node.id]
            elif isinstance(node, ast.Attribute):
                ids = [node.attr]
            for i in ids:
                if any(f.lower() in (i or "").lower() for f in forbid) and not (name == "ab1d_visuals.py" and i == "ab1c_planar"):
                    bad.append((name, i))
                if name == "ab1d_match.py" and any(t.lower() in (i or "").lower() for t in truthy):
                    bad.append((name, "truth:" + i))
    return not bad, {"forbidden": bad[:10]}


def c32(x):
    man = cached("a1c_man", lambda: jload(a1c("manifest.json")))["files"]
    bad = [k for k, h in man.items() if sha_cached(a1c(k)) != h]
    acc = {k: sha_cached(p) == h for k, (p, h) in ACCEPTED.items()}
    return not bad and all(acc.values()) and sha_cached(a1c("manifest.json")) == A1C_MANIFEST_SHA, {
        "a1c_files_changed": bad[:5], "accepted": acc, "a1c_files": len(man)}


def c33(x):
    ch = set(git("diff", "--name-only", BASE).split()) | set(git("diff", "--name-only", "--cached", BASE).split())
    extra = sorted(ch - DECLARED)
    return not extra, {"undeclared": extra}


def c34(x):
    cmds = [e["command"] for e in x.log]
    canon = [c for c in cmds if c in CANONICAL]
    unknown = [c for c in cmds if c not in ORDER]
    ok_status = all(e["status"] == "ok" for e in x.log if e["command"] in CANONICAL + ("visualize",))
    commits = {e["code"]["commit"] for e in x.log if e["command"] in CANONICAL}
    clean = all(not e["code"]["dirty"] and e["code"]["pushed"] for e in x.log if e["command"] in CANONICAL)
    first_match = cmds.index("match") if "match" in cmds else -1
    syn_before = any(c == "synthetic" and e["status"] == "ok" for c, e in zip(cmds[:max(first_match, 0)], x.log))
    rep = x.j("synthetic/synthetic-report.json")
    ok = (canon == list(CANONICAL) and not unknown and ok_status and len(commits) == 1 and clean and syn_before
          and rep["code"]["commit"] in commits and cmds.count("visualize") >= 1)
    return ok, {"canonical": canon, "unknown": unknown, "commits": sorted(commits), "clean": clean,
                "synthetic_before_match": syn_before}


def c35(x):
    rep = x.j("synthetic/synthetic-report.json")
    nums = sorted(c["case"] for c in rep["cases"])
    return (rep["passed"] and nums == list(range(1, SYN_CASES + 1)) and all(c["passed"] for c in rep["cases"])
            and not rep["code"]["dirty"]), {"cases": len(nums), "failed": [c["case"] for c in rep["cases"] if not c["passed"]]}


def c36(x):
    man = x.j("manifest.json")
    bad = [f for f, h in man["files"].items() if sha256(x.run / f) != h]
    return not bad and len(man["files"]) > 0, {"mismatch": bad[:5], "files": len(man["files"])}


def c37(x):
    ev = x.j("evaluation/evaluation-opened-files.json")
    allowed = ({str(a1c(k).resolve()) for k in BENCH_PINS} | {str(calib_p(g).resolve()) for g in GAZES}
               | {str(rgb_p(g).resolve()) for g in GAZES})
    reads = set(ev["data_reads"])
    inside = {x.rrel(p) for p in reads if x.rrel(p).startswith("RUN/")}
    outside = {p for p in reads if not x.rrel(p).startswith("RUN/")}
    ok_inside = all(p.split("/", 2)[1] in ("match", "spherical", "freeze") for p in inside)
    return not ev["violations"] and outside <= allowed and ok_inside, {"outside_not_allowed": sorted(outside - allowed)}


def c38(x):
    out = {}
    for g in GAZES:
        e, o = x.evr(g), own_eval(x, g)
        n = o["e_idx"].size
        out[g] = all(np.asarray(e[k]).shape[0] == n for k in ("e_theta", "e_px", "oracle_rank", "zncc_oracle",
                                                                "error_3d_vs_perfect_m")) and bool(np.all(o["cls"][o["e_idx"]] == 0))
    return all(out.values()), out


CHECKS = [
    ("01", "code pins, canonical remote, base ancestry", c01),
    ("02", "exact reuse of the three accepted AB1c observations (pins, AB1c manifest, match inputs)", c02),
    ("03", "no Blender / render / EXR anywhere in AB1d", c03),
    ("04", "no new gaze, one fixed head pose", c04),
    ("05", "matcher guard: reads exactly calibration + RGB; Position / oracle / evaluation reads 0; no SGBM / learned", c05),
    ("06", "spherical guard: calibration + frozen natural product only; no cv2 / matcher / planar", c06),
    ("07", "raw left nominal core, full core order; record schema", c07),
    ("08", "accepted theta / phi convention (own arccos / complex-argument recomputation)", c08),
    ("09", "epipolar line = independent fundamental-matrix line; q_inf; orientation of +theta", c09),
    ("10", "candidate segment and admissibility (independent re-implementation, subset)", c10),
    ("11", "1-px spacing and estimates on the physical locus (all rows)", c11),
    ("12", "photometric conversion and texture rule MIN_LOCAL_STD_U8 = 0.5", c12),
    ("13", "5 x 5 angular patch and ZNCC (independent scores, subset)", c13),
    ("14", "best candidate and deterministic tie rule (subset)", c14),
    ("15", "top-8 distinct peaks, 3-px separation, margin", c15),
    ("16", "quadratic refinement and the +/-0.75 bound", c16),
    ("17", "no hidden ZNCC / uniqueness / left-right rejection", c17),
    ("18", "positive-parallax, positive-intersection filter", c18),
    ("19", "natural product = valid records, truth-free AB1b schema", c19),
    ("20", "natural correspondence freeze verifies and was consumed", c20),
    ("21", "accepted spherical geometry only (own law-of-sines triangulation)", c21),
    ("22", "geometry freeze verifies; benchmark opened only after the freezes", c22),
    ("23", "primary theta error recomputation and benchmark classes", c23),
    ("24", "local pixel-equivalent scale recomputation", c24),
    ("25", "ORACLE-ON-CURVE, top-k ranks and landscape scores (own patches, subset)", c25),
    ("26", "post-freeze metric evaluation (natural vs perfect / Position)", c26),
    ("27", "confidence strata recomputation", c27),
    ("28", "match summary counts recompute", c28),
    ("29", "figures regenerate byte-identically", c29),
    ("30", "truth badges, epistemic labels and deterministic example rules", c30),
    ("31", "sources: no SGBM, planar matcher, learned model, controller or head motion; truth-free matcher code", c31),
    ("32", "accepted AB1c / AB1b products unchanged", c32),
    ("33", "changed tracked files are only the declared ones", c33),
    ("34", "run order: each canonical step once, in order, clean and pushed; synthetic before match", c34),
    ("35", "synthetic known answers pass (24 cases)", c35),
    ("36", "run manifest verifies", c36),
    ("37", "evaluation guard reads only the declared files", c37),
    ("38", "non-oracle natural outputs are not scored", c38),
]


def run_checks(x: Ctx) -> list[dict]:
    res = []
    for num, name, fn in CHECKS:
        try:
            ok, detail = fn(x)
        except Exception as e:  # a crash is a failure, never a pass
            ok, detail = False, {"exception": f"{type(e).__name__}: {e}"}
        res.append({"check": num, "name": name, "ok": bool(ok), "detail": detail})
    return res


# ------------------------------------------------------------------ corruption suite (contract section 27)
def mirror(run: Path, vis: Path, root: Path) -> tuple[Path, Path]:
    r, v = root / "run", root / "vis"
    for src, dst in ((run, r), (vis, v)):
        for p in sorted(src.rglob("*")):
            q = dst / p.relative_to(src)
            if p.is_dir():
                q.mkdir(parents=True, exist_ok=True)
                continue
            q.parent.mkdir(parents=True, exist_ok=True)
            if p.suffix in (".json", ".jsonl"):
                shutil.copyfile(p, q)
            else:
                os.symlink(p, q)
    return r, v


def rewrite_npz(path: Path, fn) -> None:
    d = npz(path)
    fn(d)
    path.unlink()
    np.savez_compressed(path, **d)


def edit_json(path: Path, fn) -> None:
    d = jload(path)
    fn(d)
    path.unlink()
    path.write_text(json.dumps(d, indent=1, sort_keys=True))


def mutated_rows(x: Ctx, g: str, mutate) -> None:
    """Rewrite the checked rows of a mirrored record with the output of a mutated matcher (what a mutated run stores)."""
    import ab1d_match as M
    idx = subset_idx(x, g)
    z = npz(rgb_p(g))
    saved = {k: getattr(M, k) for k in ("theta_phi", "make_cams", "BASELINE", "search_line", "gray", "moments", "zncc",
                                         "decide", "chord")}
    import ab1d_spec as SPm
    saved_delta = SPm.delta
    try:
        params = mutate(M, SPm) or M.FROZEN
        ctx = M.Context(calib(g), M.gray(z["rgb_L"]), M.gray(z["rgb_R"]), params)
        rec = M.match(ctx, idx)
    finally:
        for k, v in saved.items():
            setattr(M, k, v)
        SPm.delta = saved_delta

    def put(d):
        for k, v in rec.items():
            a = np.array(d[k])
            if a.ndim >= 2 and v.ndim >= 2 and a.shape[1] != v.shape[1]:
                vv = np.full((v.shape[0],) + a.shape[1:], np.nan if a.dtype.kind == "f" else -1, a.dtype)
                m = min(a.shape[1], v.shape[1])
                vv[:, :m] = v[:, :m]
                v = vv
            a[idx] = v
            d[k] = a
    rewrite_npz(x.run / f"match/{g}/matcher-record.npz", put)


def corruption_list():
    G = GAZES[0]
    L = []

    def add(name, expect, fn):
        L.append((name, set(expect), fn))

    def obs_changed(x):
        import ab1d_match as M
        orig = M.gray

        def mutate(M_, SP_):
            M_.gray = lambda rgb, p=M_.FROZEN: orig(rgb, p) * 1.03 + np.sin(np.arange(rgb.shape[1]))[None, :] * 3
        mutated_rows(x, G, mutate)
        edit_json(x.run / f"match/{G}/match-summary.json",
                  lambda d: d["inputs"]["rgb_observation"].__setitem__("sha256", "0" * 64))
    add("source: one observation changed", {"02", "10", "12", "13"}, obs_changed)

    def add_open(path, allowed=False):
        def f(x):
            def ed(d):
                ev = {"event": "open", "path": str(path), "kind": "data-read", "allowed": allowed}
                d["events"].insert(3, ev)
                if not allowed:
                    d["violations"].append(ev)
            edit_json(x.run / f"match/{G}/match-opened-files.json", ed)
        return f
    add("firewall: Position read during matching", {"05"}, add_open(a1c(REF_TMPL.format(g=G))))
    add("firewall: AB1c oracle read during matching", {"05"}, add_open(a1c(ORACLE_TMPL.format(g=G))))
    add("firewall: identity / depth added to the natural product", {"19"},
        lambda x: rewrite_npz(x.run / f"match/{G}/natural-correspondences.npz",
                              lambda d: d.__setitem__("instance_id", np.zeros(len(d["left_core_row"]), np.int32))))

    def mut(fn):
        return lambda x: mutated_rows(x, G, fn)

    def m_flip(M, SP_):
        orig = M.search_line

        def sl(*a):
            r = orig(*a)
            r["t"] = -r["t"]
            return r
        M.search_line = sl
    add("geometry: flipped baseline (search toward negative parallax)", {"09", "10"}, mut(m_flip))

    def m_pole(M, SP_):
        orig = M.theta_phi
        M.theta_phi = lambda a, b, c: (np.pi - orig(a, b, c)[0], orig(a, b, c)[1])
    add("geometry: wrong theta pole (-X)", {"08", "10"}, mut(m_pole))

    def m_phi(M, SP_):
        M.theta_phi = lambda a, b, c: (np.arctan2(np.hypot(b, c), a), np.arctan2(-b, -c))
    add("geometry: phi sign", {"08", "10", "13"}, mut(m_phi))

    def m_rt(M, SP_):
        M.make_cams = lambda c: (M.Cam(c["eyes"][0], c["image_size_wh"]),
                                 M.Cam(c["eyes"][1], c["image_size_wh"], np.asarray(c["eyes"][0]["R_hc"])))
    add("geometry: altered right-camera transform (left rotation used)", {"09", "10"}, mut(m_rt))

    def m_off(M, SP_):
        orig = M.search_line

        def sl(*a):
            r = orig(*a)
            nrm = np.stack([-r["t"][:, 1], r["t"][:, 0]], -1)
            r["q_inf"] = r["q_inf"] + 0.7 * nrm
            return r
        M.search_line = sl
    add("geometry: epipolar line offset by 0.7 px", {"09", "10"}, mut(m_off))

    add("patch: 7 x 7 instead of 5 x 5", {"10", "12", "13"}, mut(lambda M, SP_: M.Params(patch_half=3)))

    def m_spacing(M, SP_):
        SP_.delta = lambda f: math.atan(1.5 / f)
    add("patch: angular spacing 1.5 delta", {"12", "13"}, mut(m_spacing))

    def m_raw(M, SP_):
        M.gray = lambda rgb, p=M.FROZEN: 255.0 * (np.clip(rgb, 0, 1) @ np.array(p.luma))
    add("photometry: raw linear values instead of the declared conversion", {"12", "13"}, mut(m_raw))

    def tex_thr(x):
        rec = x.rec(G)
        thr = float(np.quantile(rec["left_patch_std_u8"][subset_idx(x, G)], 0.10))
        mutated_rows(x, G, lambda M, SP_: M.Params(min_std=max(thr, 0.75)))
    add("photometry: texture threshold changed", {"12", "17"}, tex_thr)

    def m_mean(M, SP_):
        M.moments = lambda vals: (np.ascontiguousarray(vals), np.sqrt(np.mean((vals - vals.mean(-1, keepdims=True)) ** 2, -1)))
    add("ZNCC: mean subtraction broken", {"13", "14"}, mut(m_mean))

    def m_norm(M, SP_):
        M.zncc = lambda a, b: np.sum(a * b, -1) / np.sum(a * a, -1)
    add("ZNCC: normalisation broken", {"13", "14"}, mut(m_norm))
    add("search: 0.5 px spacing", {"10", "11", "14"}, mut(lambda M, SP_: M.Params(spacing=0.5)))

    def m_trunc(M, SP_):
        orig = M.chord

        def ch(*a):
            lo, hi = orig(*a)
            return lo, np.minimum(hi, lo + 150)
        M.chord = ch
    add("search: hidden depth-prior truncation", {"10"}, mut(m_trunc))
    add("search: tie rule / ordering (tolerance 0.02)", {"14", "15"}, mut(lambda M, SP_: M.Params(tie_eps=0.02)))
    add("search: peak separation 5 px", {"15"}, mut(lambda M, SP_: M.Params(separation=5.0)))
    add("search: TOP_K = 4", {"15"}, mut(lambda M, SP_: M.Params(top_k=4)))
    add("refinement: disabled", {"16"}, mut(lambda M, SP_: M.Params(bound=0.0)))

    def m_sign(M, SP_):
        orig = M.decide

        def dec(S, p=M.FROZEN):
            r = orig(S, p)
            r["offset"] = -r["offset"]
            return r
        M.decide = dec
    add("refinement: quadratic sign", {"16"}, mut(m_sign))

    def m_bound(M, SP_):
        orig = M.decide

        def dec(S, p=M.FROZEN):
            r = orig(S, p)
            r["offset"] = np.clip(r["offset"] * 2.0, -1.0, 1.0)
            return r
        M.decide = dec
    add("refinement: +/-0.75 bound exceeded", {"16"}, mut(m_bound))

    def nat_after(x):
        def f(d):
            d["uv_R"] = d["uv_R"].copy()
            d["uv_R"][5, 0] += 0.3
        rewrite_npz(x.run / f"match/{G}/natural-correspondences.npz", f)
    add("freeze: natural product modified after its freeze", {"19", "20"}, nat_after)

    def geo_after(x):
        def f(d):
            d["P_epi"] = d["P_epi"].copy()
            d["P_epi"][7] += 0.01
        rewrite_npz(x.run / f"spherical/{G}/epipolar-result.npz", f)
    add("freeze: geometry modified after its freeze", {"21", "22"}, geo_after)

    def truth_early(x):
        def ed(d):
            ev = d["events"]
            bench = str(a1c(ORACLE_TMPL.format(g=G)).resolve())
            ev.insert(0, {"event": "open", "path": bench, "kind": "data-read", "allowed": True})
        edit_json(x.run / "evaluation/evaluation-opened-files.json", ed)
    add("freeze: truth opened before the geometry freeze", {"22"}, truth_early)

    def ev_arr(key, fn):
        def f(x):
            def g_(d):
                a = np.array(d[key])
                fn(a)
                d[key] = a
            rewrite_npz(x.run / f"evaluation/{G}/evaluation-result.npz", g_)
        return f
    add("evaluation: theta error", {"23"}, ev_arr("e_theta", lambda a: a.__setitem__(11, a[11] + 1e-6)))
    add("evaluation: pixel-equivalent scale", {"24"}, ev_arr("local_scale_rad_per_px", lambda a: a.__setitem__(slice(None), a * 1.01)))
    add("evaluation: oracle rank", {"25"}, ev_arr("oracle_rank", lambda a: a.__setitem__(3, 9 if a[3] != 9 else 1)))
    add("evaluation: one metric statistic", {"26"},
        lambda x: edit_json(x.run / "evaluation/evaluation-summary.json",
                            lambda d: d["per_gaze"][G]["metric"]["vs_perfect"]["error_3d_m"].__setitem__(
                                "median", d["per_gaze"][G]["metric"]["vs_perfect"]["error_3d_m"]["median"] * 1.1)))

    def pixel(x):
        p = x.vis / "overview.png"
        from PIL import Image
        im = Image.open(p).convert("RGB")
        a = np.asarray(im).copy()
        a[600, 600] = 255 - a[600, 600]
        p.unlink()
        Image.fromarray(a).save(p)
    add("visual: a canonical pixel", {"29", "30"}, pixel)
    add("visual: a truth badge", {"30"},
        lambda x: edit_json(x.vis / "visuals-manifest.json",
                            lambda d: d["figures"]["overview.png"].__setitem__("badges", [ORA_B, DER_B])))
    add("process: SGBM injected", {"31"}, lambda x: x.overrides.setdefault("static_extra", {}).__setitem__(
        "ab1d_match.py", "import cv2\nm = cv2.StereoSGBM_create(0, 16, 5)\n"))
    add("process: learned matcher injected", {"31"}, lambda x: x.overrides.setdefault("static_extra", {}).__setitem__(
        "ab1d_match.py", "import torch\n"))
    add("process: head-motion command injected", {"31"}, lambda x: x.overrides.setdefault("static_extra", {}).__setitem__(
        "ab1d_run.py", "def head_step(c):\n    return move_head(c, 10.0)\n"))

    def ctl_log(x):
        p = x.run / "process-log.jsonl"
        lines = p.read_text().splitlines()
        e = json.loads(lines[-1])
        e["command"] = "controller-step"
        lines.append(json.dumps(e))
        p.unlink()
        p.write_text("\n".join(lines) + "\n")
    add("process: controller command in the run log", {"34"}, ctl_log)

    def twice(x):
        p = x.run / "process-log.jsonl"
        lines = p.read_text().splitlines()
        k = next(i for i, ln in enumerate(lines) if json.loads(ln)["command"] == "match")
        lines.insert(k + 1, lines[k])
        p.unlink()
        p.write_text("\n".join(lines) + "\n")
    add("process: a canonical step run twice", {"34"}, twice)

    def syn_fail(x):
        edit_json(x.run / "synthetic/synthetic-report.json",
                  lambda d: (d["cases"][3].__setitem__("passed", False), d.__setitem__("passed", False)))
    add("records: a failed synthetic case", {"35"}, syn_fail)
    add("records: depth field added to the matcher record", {"07", "19"},
        lambda x: rewrite_npz(x.run / f"match/{G}/matcher-record.npz",
                              lambda d: d.__setitem__("depth_m", np.zeros(CORE * CORE))))
    add("records: an undeclared stage read in the evaluation guard", {"37"},
        lambda x: edit_json(x.run / "evaluation/evaluation-opened-files.json",
                            lambda d: d["data_reads"].append(str(A1C / "planar/gaze-1/planar-result.npz"))))
    return L


def corruption_suite(run: Path, vis: Path) -> tuple[int, int, list, dict]:
    results = []
    with tempfile.TemporaryDirectory(prefix="ab1d-corrupt-") as tmp:
        root = Path(tmp)
        r, v = mirror(run, vis, root / "null")
        null = run_checks(Ctx(r, v, {"orig_run": run}))
        null_ok = all(c["ok"] for c in null)
        null_fail = [c["check"] for c in null if not c["ok"]]
        for k, (name, expect, fn) in enumerate(corruption_list()):
            r, v = mirror(run, vis, root / f"c{k:02d}")
            x = Ctx(r, v, {"orig_run": run})
            fn(x)
            x._m.clear()          # never check a value cached before the corruption was written
            res = run_checks(x)
            failed = sorted(c["check"] for c in res if not c["ok"])
            caught = bool(set(failed) & expect)
            results.append({"corruption": name, "expected_any_of": sorted(expect), "failed_checks": failed,
                            "caught": caught})
            print(f"{PREFIX} corruption {'CAUGHT' if caught else 'MISSED'} {name}: failed {failed}")
            shutil.rmtree(root / f"c{k:02d}")
    caught = sum(r["caught"] for r in results)
    return caught, len(results), results, {"null_probe_passed": null_ok, "null_probe_failed": null_fail}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--visuals", required=True, type=Path)
    ap.add_argument("--corruptions", action="store_true")
    ap.add_argument("--write-summary", action="store_true")
    a = ap.parse_args(argv)
    run, vis = a.run.resolve(), a.visuals.resolve()
    res = run_checks(Ctx(run, vis))
    for c in res:
        print(f"{PREFIX} {'PASS' if c['ok'] else 'FAIL'} {c['check']} {c['name']}"
              + ("" if c["ok"] else f" -- {json.dumps(c['detail'], default=str)[:400]}"))
    npass = sum(c["ok"] for c in res)
    ok = npass == len(res)
    print(f"{PREFIX} SUMMARY checked={len(res)} failed={len(res) - npass}")
    if ok:
        print(f"{PREFIX} ACTIVE_BOOTSTRAP1D_CHECKS_PASS")
    out = {"schema": "AB1d-check-summary-v1", "checks": res, "passed": ok, "code": git("rev-parse", "HEAD").strip()}
    if a.corruptions:
        caught, total, results, null = corruption_suite(run, vis)
        out["corruptions"] = {"caught": caught, "total": total, "baseline_passing": ok, **null, "results": results}
        probative = ok and null["null_probe_passed"]
        print(f"{PREFIX} NULL PROBE {'PASS' if null['null_probe_passed'] else 'FAIL ' + str(null['null_probe_failed'])}")
        print(f"{PREFIX} CORRUPTIONS caught={caught}/{total}" + ("" if probative else " (NOT PROBATIVE)"))
        if probative and caught == total:
            print(f"{PREFIX} ACTIVE_BOOTSTRAP1D_MUTATIONS_CAUGHT")
        ok = ok and probative and caught == total
    if a.write_summary:
        (run / "check-summary.json").write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
