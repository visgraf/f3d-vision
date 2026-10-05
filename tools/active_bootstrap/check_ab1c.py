"""Active Bootstrap-1c: fail-capable checks of safe-forward planar vs spherical geometry.

    .venv/bin/python tools/active_bootstrap/check_ab1c.py --run RUN --visuals VIS [--stage selection]
                                                          [--corruptions] [--write-summary]

Contract: docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-contract.md, sections 16-17 (checks 1-45).  The
checker keeps its own literal constants and recomputes independently of the generator:
- the forward cone (atan2 of |d x f| and d . f on its own grid) and the full-core leverage of every cone cell (its own
  K^-1 and camera rotations, vectorised), the eligibility mask, its own greedy NMS with its own tie rule;
- the oracle per gaze (its own world-to-head, projection, nearest pixel, same-instance rule);
- the spherical geometry (theta via |b x d|, phi via the complex argument, the law of sines, Cramer's ray-ray rule,
  gamma via atan2);
- the planar geometry (its own cv2.stereoRectify call and relative pose, cv2.undistortPoints for raw -> rectified, its
  own in-front test, its own Z = f' B / d reconstruction), the support diagnostic (its own rectification maps and angles);
- the common set, the direct comparison, the post-freeze evaluation (P_truth, errors, reprojection);
- the truth firewall (guard records, ordered events, static audits), the freezes, the run order, the figures (bytes).

``--stage selection`` runs the selection checks (1-9 and the selection freeze) before any render; with
``--write-summary`` it writes only ``selection/selection-check.json``.  ``--corruptions`` plants defects in throwaway
mirrors (JSON copied, other files linked; edited arrays rewritten), as regenerations with a deliberately wrong generator,
or as in-process overrides; they count only when the uncorrupted baseline passes.  ``--write-summary`` (full) writes only
``check-summary.json``.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
from functools import cached_property
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TOOLS = REPO / "tools"
PREFIX = "[ab1c-check]"

# ---- literal copies (contract sections 2-14); deliberately not imported from ab1c_spec
SHARED = Path("/home/lvelho/rd/f3d-vision")
BASE = "c2b8373b8ba7849ad4411e28c55c31257d15f2af"
REMOTE = "visgraf/f3d-vision"
ATTENTION = (SHARED / "previews/natural-bootstrap-1c-rgb-candidate-gaze/selection/attention-score.npz",
             "4bfee30e0a1a24007925c57d338627449484dffa2a9805fd13b72727c04ef552")
NB1C_FREEZE = (SHARED / "previews/natural-bootstrap-1c-rgb-candidate-gaze/selection/rgb-gaze-freeze.json",
               "87a3bab01f55051316ac1eb45b48f394211f4c7a3a317fd0e61c0e52c36f9b37")
NB1C_MANIFEST = (SHARED / "previews/natural-bootstrap-1c-rgb-candidate-gaze/manifest.json",
                 "524f8fad71ccb8fd9359fa3221f4de6be3af40be8f3e5fa7cddeb482acedd87e")
GRID_SHA = "d72076612515f1079ffce611e81a5b5e1675804c1f8d600cafc31a28829d0b73"
HEAD_POSE = (SHARED / "previews/controller-01-full/bootstrap/seeds.json",
             "6ef833196de2462370ba4b2a2a8eed3fbde7f0a61e5aa6cbaf95f66947134c4f")
BLEND_SHA = "dca66a3257b909aef00b0331652c55f62a93a8dff0665d070fba7efa436953cc"
CODE_PINS = {
    "tools/fsg_geometry.py": "ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54",
    "tools/fsg_stereo.py": "faebf0f1b3acbfde60b08830a57213bf29c708c3aa274e493ade0042eb0545e9",
    "tools/natural_bootstrap/nb1a_guard.py": "29ebca57be9e977def7a94ea45a7b0cff0f22a8b1d86b40f740f132491ebe99d",
    "tools/natural_bootstrap/nb1a_spec.py": "1c1786aaef264012dfb5dcda840cbcc211719340075e4417f1ebef8901134d80",
    "tools/natural_bootstrap/nb1c_spec.py": "2e05e597889ea9f662b69f3d2f71bccc1f411dafaa5b63ba2ca297a37c731a91",
    "tools/natural_bootstrap/nb1c_attention.py": "b7d38c67f65b5d1518c8cef30826c278b12fd2cd1dfa25c558a47e3a968875ea",
    "tools/active_bootstrap/ab1a_spec.py": "24ab5df947b6aaabc46737d3fd015d43802405f94ff1b01595c650bf5ab24a62",
    "tools/active_bootstrap/ab1a_render.py": "ae96164abae9a5241cee3e496293879be43ac96e77697d44d4e2bc956d51e01b",
    "tools/active_bootstrap/ab1a_stereo.py": "c0238a7318c4a9c034c4a679104ae46cfd7504bf204935e2af15707b10f07f65",
    "tools/active_bootstrap/ab1b_spec.py": "1634e455a61879934545a1fa634a72cbb2b8ca74fd83a6ba3a977412be0e497d",
    "tools/active_bootstrap/ab1b_oracle.py": "51e2ee556a4a3576d00cd99255793212ad5efcb50b1e15ed292740d8c24aa231",
    "tools/active_bootstrap/ab1b_geometry.py": "a125dd9cc666120219e0421a09a380353d2304ed0f09681a1655962444572538",
    "tools/active_bootstrap/ab1b_visuals.py": "6dd4a203b1847e9d5f0f984c2a1727859aa035ad00adead79849bd484ca833ee",
    "tools/active_bootstrap/ab1b_run.py": "6088ab06ba52aa285bec9835e39e29c706db137a13d7527c9c76d90e46ac810a",
    "tools/classroom_oracle1_render.py": "ebeac7363a54a022c604161a3716a220fcf2aa7feea3792a68568699ed28a55a",
    "tools/render_foveated.py": "6f4d6c20b3fa22a74cbf71552374410545b09aeb07ae0b5867cf95b7a264fedf",
    "tools/bl_common.py": "aa7a56e8cd4988cbe7fc92a57fde68e62740688b6ccfee718e01a8e52ba10370",
    "tools/exr_lite.py": "77286773ee52d17f45373a9c0a0358b197b18672c4cff4654e00bc69e828ef20",
    "tools/visual_language/style.py": "c379a2a31c9112d22bbe8989324d2ff74608c669fe84d58905509b4d62264053",
    "tools/classroom_oracle/breadth1_visuals.py": "61683aea17993da09bfddce4ed13d48da47d710d1630e40c6bdcc7a6f6d2144c",
}
ACCEPTED = {
    "AB1a manifest": (SHARED / "previews/active-bootstrap/ab1a-first-natural-stereo-look/manifest.json",
                      "74eba4d6112f2de69fd797f9f41ff987e128ce1ecbcb5d48f05f597e9a2731fe"),
    "AB1a visuals": (SHARED / "visuals/active-bootstrap/ab1a-first-natural-stereo-look/visuals-manifest.json",
                     "d38bfdc2b9158739cc635f3cbc5ba4a764e6234c5397ba50ca99780987b22da0"),
    "AB1b geometry freeze": (SHARED / "previews/active-bootstrap/ab1b-spherical-epipolar-geometry/geometry/geometry-freeze.json",
                             "942707a858c8b76cb65db503183853d27c55000eb2e59c6de4dfbcf025d21c7a"),
    "AB1b visuals": (SHARED / "visuals/active-bootstrap/ab1b-spherical-epipolar-geometry/visuals-manifest.json",
                     "a1216d2c22095f6353260efeb93b452a7b429f7a3d29b7d760db8d27a056f88c"),
    "NB1a freeze": (SHARED / "previews/natural-bootstrap-1a-range-connectivity/discovery/bootstrap-freeze.json",
                    "c0236d0424a7724bfe57bf0a19bdf56899b7eadf5e059c9537e785f3a08b826a"),
    "NB1b freeze": (SHARED / "previews/natural-bootstrap-1b-foveal-serviceability/selection/serviceability-freeze.json",
                    "f99b7cae02498feb21ae1d80978b57c877c44984067d55c7fd2bbe189efb6e9a"),
    "NB1c freeze": NB1C_FREEZE,
}
RAW, CORE, ORIGIN = 640, 256, 192
IPD, FOCAL, VERGENCE = 0.063, 1217.8386501404907, 2.10
DEVICE, SPP, SEEDS = "OPTIX", 256, {"L": 2111, "R": 2112}
W_GRID, H_GRID = 720, 360
CONE_RAD, LEV_MIN, EPS, K_GAZES, TIE = math.radians(20.0), 0.90, 1e-12, 3, 1e-12
D_MIN = 2.0 * math.atan(math.sqrt(2.0) * math.tan(math.radians(6.0)))
Z_MIN = 1e-9
REQUIRED_PASSES = {"Combined", "Position", "Object Index"}
INHERITED = {"Ambient Occlusion", "Diffuse Color", "Diffuse Direct", "Diffuse Indirect", "Emission", "Glossy Color",
             "Glossy Direct", "Glossy Indirect", "Transmission Color", "Transmission Direct", "Transmission Indirect"}
GAZES = ("gaze-1", "gaze-2", "gaze-3")
PRODUCT_KEYS = {"left_core_row", "left_core_col", "uv_L", "uv_R"}
FORBIDDEN_KEY_TOKENS = ("xyz", "position", "range", "depth", "instance", "object", "normal", "semantic", "label", "truth",
                        "world")
QUANT = {"min": 0.0, "p05": 0.05, "median": 0.5, "p90": 0.90, "p95": 0.95, "p99": 0.99, "max": 1.0}
FRACTIONS = (0.001, 0.005, 0.010, 0.025)
TOL_ANG, TOL_UV, TOL_XYZ, TOL_RAY, TOL_LEV, TOL_REL = 1e-11, 1e-9, 1e-9, 1e-7, 1e-12, 1e-9
GENERATOR = ["ab1c_spec.py", "ab1c_select.py", "ab1c_planar.py", "ab1c_render.py", "ab1c_run.py", "ab1c_synthetic.py",
             "ab1c_visuals.py"]
AB1C_FILES = {f"tools/active_bootstrap/{n}" for n in GENERATOR + ["check_ab1c.py"]} | {
    "docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-contract.md",
    "docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-report.md"}
DECLARED = AB1C_FILES | {"tools/repository/check_repository_layout.py"}
COMMANDS = {"synthetic", "rehearse", "source", "select", "freeze-selection", "plan", "preflight", "acquire", "oracle",
            "freeze-correspondence", "spherical", "planar", "freeze-geometry", "compare", "evaluate", "visualize"}
ORDER = ["source", "select", "freeze-selection", "plan", "preflight", "acquire", "oracle", "freeze-correspondence",
         "spherical", "planar", "freeze-geometry", "compare", "evaluate"]
FIGURES = ["overview.png", "safe-forward-selection.png", "binocular-observations.png", "planar-support.png",
           "spherical-support.png", "common-correspondences.png", "planar-vs-spherical-difference.png",
           "paired-reconstruction.png", "truth-error.png", "conditioning.png"]
ORA, DER, REF = "ORACLE INPUT", "DERIVED", "REFERENCE / EVALUATION"
BADGES = {"overview.png": [ORA, DER, REF], "safe-forward-selection.png": [ORA, DER],
          "binocular-observations.png": [ORA], "planar-support.png": [DER], "spherical-support.png": [DER],
          "common-correspondences.png": [ORA, DER], "planar-vs-spherical-difference.png": [DER],
          "paired-reconstruction.png": [DER], "truth-error.png": [REF, DER], "conditioning.png": [DER]}
SELECTION_FORBIDDEN = ("position", "instance", "catalog", "depth", "segment", "reference", "seeds", "head_pose",
                       "stereo", "cv2", "sgbm", "oracle", "evaluation")
GEOMETRY_TRUTH = ("load_reference", "reference", "position", "instance", "catalog", "compute_oracle", "evaluation")
MATCHER_IDS = ("sgbm", "matcher", "refine_disparity", "compute_natural", "measure_dir")
CONTROL_IDS = ("controller", "fsg6f", "fsg3", "surface_map", "fusion", "multiobject", "fov3d", "head_motion",
               "recenter")


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


# ------------------------------------------------------------------ independent geometry
def unit(v):
    v = np.asarray(v, np.float64)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def own_gaze(yaw, pitch):
    y, p = np.radians(yaw), np.radians(pitch)
    return np.stack([np.sin(y) * np.cos(p), np.sin(p), -np.cos(y) * np.cos(p)], -1)


def own_grid():
    yaw = -180.0 + 0.5 * (np.arange(W_GRID) + 0.5)
    pitch = 90.0 - 0.5 * (np.arange(H_GRID) + 0.5)
    yy, pp = np.meshgrid(yaw, pitch)
    return own_gaze(yy, pp), yaw, pitch


def own_eye_rotations(yaw, pitch) -> tuple[np.ndarray, np.ndarray]:
    """R_hc of the left and right eyes (camera +X = the baseline projected into the tangent plane)."""
    tgt = own_gaze(yaw, pitch) * VERGENCE
    out = []
    for cx in (-IPD / 2, IPD / 2):
        z = unit(tgt - np.array([cx, 0.0, 0.0]))
        x = unit(np.array([1.0, 0.0, 0.0]) - z[0] * z)
        out.append(np.column_stack([x, np.cross(z, x), z]))
    return out[0], out[1]


def own_core_dirs_cam() -> np.ndarray:
    r, c = np.mgrid[:CORE, :CORE]
    cpp = (RAW - 1) / 2
    a = np.stack([(c.ravel() + ORIGIN - cpp) / FOCAL, (r.ravel() + ORIGIN - cpp) / FOCAL, np.ones(CORE * CORE)], -1)
    return unit(a)


_MASK_CACHE: dict = {}


def own_mask() -> dict:
    """Cone (atan2 route) for every cell; full-core leverage (own rotations, vectorised) for every cone cell."""
    if "m" in _MASK_CACHE:
        return _MASK_CACHE["m"]
    dirs, yaw, pitch = own_grid()
    f = np.array([0.0, 0.0, -1.0])
    alpha = np.arctan2(np.linalg.norm(np.cross(dirs, f), axis=-1), dirs @ f)
    cone = alpha <= CONE_RAD + EPS
    a = own_core_dirs_cam()
    rr, cc = np.nonzero(cone)
    rows_l, rows_r = [], []
    for r, c in zip(rr, cc):
        rl, rrr = own_eye_rotations(yaw[c], pitch[r])
        rows_l.append(rl[0])
        rows_r.append(rrr[0])
    rows = np.concatenate([np.asarray(rows_l), np.asarray(rows_r)]).T     # 3 x 2N
    mx = np.empty(rows.shape[1])
    for s in range(0, rows.shape[1], 256):
        dx = a @ rows[:, s:s + 256]
        mx[s:s + 256] = np.max(np.abs(dx), axis=0)
    lev = np.sqrt(np.maximum(0.0, 1.0 - mx * mx))
    n = len(rr)
    lev_l, lev_r = np.full(cone.shape, np.nan), np.full(cone.shape, np.nan)
    lev_l[rr, cc], lev_r[rr, cc] = lev[:n], lev[n:]
    with np.errstate(invalid="ignore"):
        elig = cone & (np.fmin(lev_l, lev_r) >= LEV_MIN)
    _MASK_CACHE["m"] = {"alpha": alpha, "cone": cone, "lev_L": lev_l, "lev_R": lev_r, "eligible": elig, "dirs": dirs,
                        "yaw": yaw, "pitch": pitch}
    return _MASK_CACHE["m"]


def own_nms(a: np.ndarray, dirs: np.ndarray, elig0: np.ndarray, k=K_GAZES, d_min=D_MIN, tie=TIE) -> list[dict]:
    a, d, e = a.reshape(-1), dirs.reshape(-1, 3), elig0.reshape(-1).copy()
    out = []
    for kk in range(k):
        idx = np.nonzero(e)[0]
        if not idx.size:
            break
        amax = a[idx].max()
        ties = idx[amax - a[idx] <= tie * max(1.0, abs(amax))]
        g = int(np.min(ties))
        ang = np.arctan2(np.linalg.norm(np.cross(d, d[g]), axis=-1), d @ d[g])
        sup = e & (ang + EPS < d_min)
        out.append({"index": g, "row": g // W_GRID, "col": g % W_GRID, "score": float(a[g]), "tie_set_size": int(ties.size),
                    "eligible_before": int(idx.size), "newly_suppressed": int(sup.sum())})
        e &= ~sup
    return out


def own_rays(eye: dict, uv) -> np.ndarray:
    k, r = np.asarray(eye["K"], np.float64), np.asarray(eye["R_hc"], np.float64)
    uv = np.asarray(uv, np.float64)
    dc = np.stack([(uv[..., 0] - k[0, 2]) / k[0, 0], (uv[..., 1] - k[1, 2]) / k[1, 1], np.ones(uv.shape[:-1])], -1)
    return unit(np.einsum("ij,...j->...i", r, dc))


def own_project(eye: dict, p_h) -> tuple[np.ndarray, np.ndarray]:
    k, r = np.asarray(eye["K"], np.float64), np.asarray(eye["R_hc"], np.float64)
    xc = np.einsum("ji,...j->...i", r, np.asarray(p_h, np.float64) - np.asarray(eye["centre_h_m"], np.float64))
    with np.errstate(divide="ignore", invalid="ignore"):
        u = k[0, 0] * xc[..., 0] / xc[..., 2] + k[0, 2]
        v = k[1, 1] * xc[..., 1] / xc[..., 2] + k[1, 2]
    return np.stack([u, v], -1), xc[..., 2]


def own_w2h(c: dict, p_w) -> np.ndarray:
    r = np.asarray(c["head_R_wh"], np.float64)
    return np.einsum("ji,...j->...i", r, np.asarray(p_w, np.float64) - np.asarray(c["head_origin_w_m"], np.float64))


def own_theta(d):
    d = np.asarray(d, np.float64)
    return np.arctan2(np.linalg.norm(np.cross(np.array([1.0, 0.0, 0.0]), d), axis=-1), d[..., 0])


def own_phi(d):
    d = np.asarray(d, np.float64)
    return np.angle(-d[..., 2] + 1j * d[..., 1])


def own_epipolar(th_l, th_r, ph_l, ph_r, b=IPD):
    with np.errstate(divide="ignore", invalid="ignore"):
        r_l = b * np.sin(th_r) / np.sin(th_r - th_l)
    pb = np.angle(np.exp(1j * ph_l) + np.exp(1j * ph_r))
    return np.stack([-b / 2 + r_l * np.cos(th_l), r_l * np.sin(th_l) * np.sin(pb), -r_l * np.sin(th_l) * np.cos(pb)], -1)


def own_ray_ray(o_l, d_l, o_r, d_r):
    n = np.cross(d_l, d_r)
    nn = np.sum(n * n, -1)
    w = o_r - o_l
    s = np.sum(np.cross(w, d_r) * n, -1) / nn
    t = np.sum(np.cross(w, d_l) * n, -1) / nn
    return (o_l + s[..., None] * d_l + o_r + t[..., None] * d_r) / 2, np.abs(np.sum(w * n, -1)) / np.sqrt(nn)


def own_rectify(c: dict) -> dict:
    import cv2
    kl, kr = (np.asarray(e["K"], np.float64) for e in c["eyes"])
    rl, rr = (np.asarray(e["R_hc"], np.float64) for e in c["eyes"])
    ol, orr = (np.asarray(e["centre_h_m"], np.float64) for e in c["eyes"])
    r, t = rr.T @ rl, rr.T @ (ol - orr)
    w, h = c["image_size_wh"]
    r1, r2, p1, p2, q, _a, _b = cv2.stereoRectify(kl, np.zeros(5), kr, np.zeros(5), (w, h), r, t,
                                                   flags=cv2.CALIB_ZERO_DISPARITY, alpha=-1, newImageSize=(w, h))
    return {"R1": r1, "R2": r2, "P1": p1, "P2": p2, "Q_full": q}


def own_planar(c: dict, rect: dict, prod: dict) -> dict:
    import cv2
    out = {}
    for side, k, rr, pp, uv in (("L", 0, rect["R1"], rect["P1"], prod["uv_L"]), ("R", 1, rect["R2"], rect["P2"], prod["uv_R"])):
        kk = np.asarray(c["eyes"][k]["K"], np.float64)
        uv = np.asarray(uv, np.float64).reshape(-1, 1, 2)
        und = cv2.undistortPoints(uv, kk, None, R=np.asarray(rr, np.float64), P=np.asarray(pp, np.float64)).reshape(-1, 2) \
            if len(uv) else np.zeros((0, 2))
        a = np.concatenate([uv.reshape(-1, 2), np.ones((len(uv), 1))], -1)
        hz = (np.asarray(rr, np.float64) @ np.linalg.solve(kk, a.T))[2] if len(uv) else np.zeros(0)
        out[side] = (und, hz)
    (ul, wl), (ur, wr) = out["L"], out["R"]
    p1 = np.asarray(rect["P1"], np.float64)
    f, cx, cy = p1[0, 0], p1[0, 2], p1[1, 2]
    b = -np.asarray(rect["P2"], np.float64)[0, 3] / np.asarray(rect["P2"], np.float64)[0, 0]
    d = ul[:, 0] - ur[:, 0]
    with np.errstate(divide="ignore", invalid="ignore"):
        z = f * b / d
        xr = np.stack([(ul[:, 0] - cx) * z / f, (ul[:, 1] - cy) * z / f, z], -1)
    r_hc = np.asarray(c["eyes"][0]["R_hc"], np.float64)
    p = np.einsum("ij,nj->ni", r_hc @ np.asarray(rect["R1"], np.float64).T, xr) + np.asarray(c["eyes"][0]["centre_h_m"])
    valid = (wl > 1e-12) & (wr > 1e-12) & np.isfinite(ul).all(-1) & np.isfinite(ur).all(-1) & (np.abs(d) >= 1e-12) \
        & np.isfinite(p).all(-1)
    return {"uvrect_L": ul, "uvrect_R": ur, "w_L": wl, "w_R": wr, "disparity": d, "P_planar": np.where(valid[:, None], p, np.nan),
            "valid_planar": valid, "row_residual": ur[:, 1] - ul[:, 1]}


def quant(a) -> dict | None:
    a = np.asarray(a, np.float64).ravel()
    a = a[np.isfinite(a)]
    if a.size == 0:
        return None
    return {k: float(np.quantile(a, q)) for k, q in QUANT.items()} | {"count": int(a.size)}


def qeq(a: dict | None, b: dict | None, rel=TOL_REL, absol=0.0) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return set(a) == set(b) and all(abs(a[k] - b[k]) <= rel * max(1.0, abs(b[k])) + absol for k in a)


def ast_ids(src: str) -> set:
    t = ast.parse(src)
    out = set()
    for n in ast.walk(t):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
        elif isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, ast.alias):
            out.add(n.name)
            if n.asname:
                out.add(n.asname)
        elif isinstance(n, ast.arg):
            out.add(n.arg)
    return {x.lower() for x in out}


def func_src(src: str, names) -> str:
    t = ast.parse(src)
    return "\n".join(ast.get_source_segment(src, n) for n in t.body if isinstance(n, ast.FunctionDef) and n.name in names)


def _generator(name):
    for p in (HERE, TOOLS, TOOLS / "natural_bootstrap", TOOLS / "classroom_oracle", TOOLS / "visual_language"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    return __import__(name)


# ------------------------------------------------------------------ context
class Ctx:
    def __init__(self, run: Path, vis: Path):
        self.run, self.vis = run, vis
        self.overrides: dict = {}
        self._c: dict = {}

    def j(self, rel):
        return json.loads((self.run / rel).read_text())

    def npz(self, rel):
        with np.load(self.run / rel, allow_pickle=False) as z:
            return {k: np.asarray(z[k]) for k in z.files}

    def per(self, kind: str, g: str):
        key = (kind, g)
        if key not in self._c:
            rel = {"calib": f"observations/{g}/acquisition/calibration.json",
                   "acq": f"observations/{g}/acquisition/acquisition.json",
                   "plan": f"plan/{g}/planned-calibration.json",
                   "prod": f"oracle/{g}/oracle-correspondences.npz", "osum": f"oracle/{g}/oracle-summary.json",
                   "oopen": f"oracle/{g}/oracle-opened-files.json", "rays": f"spherical/{g}/left-core-rays.npz",
                   "sph": f"spherical/{g}/epipolar-result.npz", "ssum": f"spherical/{g}/spherical-summary.json",
                   "sopen": f"spherical/{g}/spherical-opened-files.json", "pla": f"planar/{g}/planar-result.npz",
                   "psum": f"planar/{g}/planar-summary.json", "psup": f"planar/{g}/planar-support.json",
                   "popen": f"planar/{g}/planar-opened-files.json", "cmp": f"comparison/{g}/comparison-result.npz",
                   "evr": f"evaluation/{g}/evaluation-result.npz",
                   "ref": f"observations/{g}/evaluation_only/reference-observation.npz",
                   "rgb": f"observations/{g}/acquisition/rgb-observation.npz"}[kind]
            self._c[key] = self.npz(rel) if rel.endswith(".npz") else self.j(rel)
        return self._c[key]

    @cached_property
    def sel(self):
        return self.j("selection/selected-gazes.json")["gazes"]

    @cached_property
    def rounds(self):
        return self.j("selection/nms-rounds.json")["rounds"]

    @cached_property
    def ssum(self):
        return self.j("selection/selection-summary.json")

    @cached_property
    def smask(self):
        return self.npz("selection/safe-forward-mask.npz")

    @cached_property
    def sopen(self):
        return self.j("selection/selection-opened-files.json")

    @cached_property
    def sfz(self):
        return self.j("selection/safe-forward-freeze.json")

    @cached_property
    def attention_path(self):
        return Path(self.overrides.get("attention_path", ATTENTION[0]))

    @cached_property
    def A(self):
        with np.load(self.attention_path, allow_pickle=False) as z:
            return np.asarray(z["A"])

    @cached_property
    def log(self):
        return [json.loads(x) for x in (self.run / "process-log.jsonl").read_text().splitlines() if x.strip()]

    @cached_property
    def cfz(self):
        return self.j("oracle/correspondence-freeze.json")

    @cached_property
    def gfz(self):
        return self.j("freeze/geometry-freeze.json")

    @cached_property
    def csum(self):
        return self.j("comparison/comparison-summary.json")

    @cached_property
    def copen(self):
        return self.j("comparison/comparison-opened-files.json")

    @cached_property
    def ev(self):
        return self.j("evaluation/evaluation-summary.json")

    @cached_property
    def evopen(self):
        return self.j("evaluation/evaluation-opened-files.json")

    @cached_property
    def changed_files(self):
        ch = set(git("diff", "--name-only", BASE).split()) | set(git("diff", "--name-only", "--cached", BASE).split())
        return sorted(ch)

    def src(self, name: str) -> str:
        return self.overrides.get("static_extra", {}).get(name, "") + (HERE / name).read_text()

    # ---- the checker's own per-gaze computations
    def own_oracle(self, g):
        key = ("own_oracle", g)
        if key not in self._c:
            c, ref = self.per("calib", g), self.per("ref", g)
            r, cc = np.mgrid[:CORE, :CORE]
            r, cc = r.ravel(), cc.ravel()
            pos = ref["position_w_L"][r + ORIGIN, cc + ORIGIN].astype(np.float64)
            ids = ref["instance_L"][r + ORIGIN, cc + ORIGIN].astype(np.int64)
            hit = np.isfinite(pos).all(-1) & (np.abs(pos).sum(-1) > 0)
            cat = hit & (ids > 0)
            uv, z = own_project(c["eyes"][1], own_w2h(c, np.where(hit[:, None], pos, 0.0)))
            proj = cat & np.isfinite(uv).all(-1) & np.isfinite(z) & (z > Z_MIN)
            with np.errstate(invalid="ignore"):
                inside = proj & (uv[:, 0] >= 0) & (uv[:, 0] <= RAW - 1) & (uv[:, 1] >= 0) & (uv[:, 1] <= RAW - 1)
            ui = np.rint(np.clip(np.nan_to_num(uv[:, 0]), 0, RAW - 1)).astype(int)
            vi = np.rint(np.clip(np.nan_to_num(uv[:, 1]), 0, RAW - 1)).astype(int)
            vis = inside & (ref["instance_R"][vi, ui] == ids)
            self._c[key] = {"rows": r[vis], "cols": cc[vis], "uv_R": uv[vis],
                            "attrition": [CORE * CORE, int(hit.sum()), int(cat.sum()), int(proj.sum()), int(inside.sum()),
                                          int(vis.sum()), int(vis.sum())]}
        return self._c[key]

    def own_sph(self, g):
        key = ("own_sph", g)
        if key not in self._c:
            c, prod = self.per("calib", g), self.per("prod", g)
            dl, dr = own_rays(c["eyes"][0], prod["uv_L"]), own_rays(c["eyes"][1], prod["uv_R"])
            th_l, th_r, ph_l, ph_r = own_theta(dl), own_theta(dr), own_phi(dl), own_phi(dr)
            o_l, o_r = np.array([-IPD / 2, 0, 0.0]), np.array([IPD / 2, 0, 0.0])
            pray, gap = own_ray_ray(o_l, dl, o_r, dr) if len(dl) else (np.zeros((0, 3)), np.zeros(0))
            gamma = np.arctan2(np.linalg.norm(np.cross(dl, dr), axis=-1), np.sum(dl * dr, -1))
            self._c[key] = {"d_L": dl, "d_R": dr, "theta_L": th_l, "theta_R": th_r, "phi_L": ph_l, "phi_R": ph_r,
                            "P_epi": own_epipolar(th_l, th_r, ph_l, ph_r), "P_ray": pray, "gap": gap, "gamma": gamma}
        return self._c[key]

    def own_rect(self, g):
        key = ("own_rect", g)
        if key not in self._c:
            self._c[key] = own_rectify(self.per("calib", g))
        return self._c[key]

    def own_pla(self, g):
        key = ("own_pla", g)
        if key not in self._c:
            self._c[key] = own_planar(self.per("calib", g), self.own_rect(g), self.per("prod", g))
        return self._c[key]

    def ptruth(self, g):
        key = ("ptruth", g)
        if key not in self._c:
            prod, ref, c = self.per("prod", g), self.per("ref", g), self.per("calib", g)
            pos = ref["position_w_L"][prod["left_core_row"].astype(int) + ORIGIN,
                                      prod["left_core_col"].astype(int) + ORIGIN].astype(np.float64)
            self._c[key] = own_w2h(c, pos)
        return self._c[key]


def rrel(x, p) -> str:
    """A recorded absolute path relative to the run root (the run directory keeps its name in a mirror)."""
    s, key = str(p), "/" + x.run.name + "/"
    return s.split(key, 1)[1] if key in s else s


def hit_tokens(ids: set, tokens) -> list:
    return sorted(i for i in ids if any(t in i for t in tokens))


# ------------------------------------------------------------------ checks
def c01(x):
    remote = git("remote", "get-url", "origin").strip().rstrip("/")
    remote = remote[:-4] if remote.endswith(".git") else remote
    code = {p: sha256(REPO / p) == h for p, h in CODE_PINS.items()}
    acc = {k: sha256(p) == h for k, (p, h) in ACCEPTED.items()}
    nb = json.loads(NB1C_FREEZE[0].read_text())
    nb1c_files = all(sha256(NB1C_FREEZE[0].parent / n) == h for n, h in nb["files"].items())
    src = x.j("source/source-manifest.json")
    ok = (remote.endswith(REMOTE) and all(code.values()) and all(acc.values()) and nb1c_files
          and src["attention"]["sha256"] == ATTENTION[1] and src["base_commit"] == BASE
          and src["head_pose_source"]["sha256"] == HEAD_POSE[1] and src["blend"]["sha256"] == BLEND_SHA
          and git("merge-base", "--is-ancestor", BASE, "HEAD") == "")
    return ok, {"remote": remote, "code": {k: v for k, v in code.items() if not v},
                "accepted": {k: v for k, v in acc.items() if not v}, "nb1c_files": nb1c_files}


def c02(x):
    nb, man = json.loads(NB1C_FREEZE[0].read_text()), json.loads(NB1C_MANIFEST[0].read_text())
    d, _y, _p = own_grid()
    grid = hashlib.sha256(np.ascontiguousarray(d, np.float64).tobytes()).hexdigest()
    with np.load(x.attention_path, allow_pickle=False) as z:
        files = list(z.files)
    a = x.A
    ok = (sha256(x.attention_path) == ATTENTION[1] and sha256(NB1C_FREEZE[0]) == NB1C_FREEZE[1]
          and sha256(NB1C_MANIFEST[0]) == NB1C_MANIFEST[1] and nb["files"]["attention-score.npz"] == ATTENTION[1]
          and man["files"]["selection/attention-score.npz"] == ATTENTION[1] and nb["grid"]["directions_sha256"] == GRID_SHA
          and grid == GRID_SHA and files == ["A"] and a.shape == (H_GRID, W_GRID) and a.dtype == np.float64
          and x.ssum["input"]["sha256"] == ATTENTION[1] and x.sfz["attention"]["sha256"] == ATTENTION[1])
    return ok, {"attention": sha256(x.attention_path)[:12], "grid": grid[:12]}


def c03(x):
    m = own_mask()
    bad_alpha = float(np.max(np.abs(x.smask["alpha_forward_rad"] - m["alpha"])))
    ok = bad_alpha <= TOL_ANG and np.array_equal(x.smask["cone"], m["cone"]) and int(m["cone"].sum()) == x.ssum["cells_in_cone"]
    gz_ok = all(math.radians(20.0) + EPS >= np.arctan2(np.linalg.norm(np.cross(own_gaze(g["yaw_deg"], g["pitch_deg"]),
                                                                                [0, 0, -1.0])),
                                                         own_gaze(g["yaw_deg"], g["pitch_deg"]) @ [0, 0, -1.0]) for g in x.sel)
    return ok and gz_ok, {"max_alpha_diff": bad_alpha, "cone": int(m["cone"].sum()), "selected_in_cone": gz_ok}


def c04(x):
    m = own_mask()
    cone = m["cone"]
    dl = np.abs(x.smask["min_core_leverage_L"][cone] - m["lev_L"][cone])
    dr = np.abs(x.smask["min_core_leverage_R"][cone] - m["lev_R"][cone])
    outside_nan = bool(np.isnan(x.smask["min_core_leverage_L"][~cone]).all())
    sel_ok = all(min(m["lev_L"][g["row"], g["col"]], m["lev_R"][g["row"], g["col"]]) >= LEV_MIN for g in x.sel)
    ok = float(max(dl.max(), dr.max())) <= TOL_LEV and outside_nan and sel_ok
    return ok, {"max_leverage_diff": float(max(dl.max(), dr.max())), "selected_leverage_ok": sel_ok}


def c05(x):
    m = own_mask()
    lev = np.fmin(m["lev_L"], m["lev_R"])
    margin = float(np.nanmin(np.abs(lev[m["cone"]] - LEV_MIN)))
    ok = (np.array_equal(x.smask["eligible"], m["eligible"]) and int(m["eligible"].sum()) == x.ssum["cells_eligible"]
          and hashlib.sha256(np.packbits(m["eligible"]).tobytes()).hexdigest() == x.ssum["mask_sha256"])
    return ok, {"eligible": int(m["eligible"].sum()), "differing": int((x.smask["eligible"] != m["eligible"]).sum()),
                "leverage_margin": margin}


def c06(x):
    s = x.ssum
    ok = (len(x.sel) == K_GAZES == s["K"] and abs(s["D_MIN_RAD"] - D_MIN) <= 1e-15
          and s["selection"]["SCORE_TIE_REL"] == TIE and s["selection"]["ANGLE_EPS_RAD"] == EPS
          and s["selection"]["FORWARD_CONE_DEG"] == 20.0 and s["selection"]["LEVERAGE_MIN"] == LEV_MIN
          and s["selection"]["score_threshold"] is None and len(x.rounds) == K_GAZES)
    return ok, {"K": len(x.sel), "D_MIN_RAD": s["D_MIN_RAD"]}


def c07(x):
    m = own_mask()
    own = own_nms(x.A, m["dirs"], m["eligible"])
    keys = ("index", "row", "col", "score", "tie_set_size", "eligible_before", "newly_suppressed")
    same = len(own) == len(x.rounds) and all(o[k] == r[k] for o, r in zip(own, x.rounds) for k in keys)
    picks = [(g["row"], g["col"]) for g in x.sel] == [(o["row"], o["col"]) for o in own]
    d = np.array([own_gaze(g["yaw_deg"], g["pitch_deg"]) for g in x.sel])
    sep = [float(np.arctan2(np.linalg.norm(np.cross(d[i], d[k])), d[i] @ d[k])) for i in range(len(d)) for k in range(i)]
    ok = same and picks and all(s + EPS >= D_MIN for s in sep)
    return ok, {"own_picks": [(o["row"], o["col"]) for o in own], "min_separation_deg": math.degrees(min(sep)) if sep else None}


def c08(x):
    m = own_mask()
    bad = []
    for k, g in enumerate(x.sel, start=1):
        r, c = g["row"], g["col"]
        yaw, pitch = -180.0 + 0.5 * (c + 0.5), 90.0 - 0.5 * (r + 0.5)
        d = own_gaze(yaw, pitch)
        lc = math.sqrt(max(0.0, 1 - d[0] ** 2))
        want = {"rank": k, "yaw_deg": yaw, "pitch_deg": pitch, "A": float(x.A[r, c]), "L_center": lc,
                "B_perp_center_m": IPD * lc, "min_core_leverage_L": float(m["lev_L"][r, c]),
                "min_core_leverage_R": float(m["lev_R"][r, c]), "alpha_forward_rad": float(m["alpha"][r, c]),
                "index": r * W_GRID + c}
        for key, v in want.items():
            if abs(float(g[key]) - float(v)) > 1e-11 * max(1.0, abs(float(v))):
                bad.append((k, key, g[key], v))
        if g["min_core_leverage"] != min(g["min_core_leverage_L"], g["min_core_leverage_R"]):
            bad.append((k, "min_core_leverage"))
        rd = x.rounds[k - 1]
        if (g["eligible_before"], g["tie_set_size"], g["nms_suppressed"]) != (rd["eligible_before"], rd["tie_set_size"],
                                                                           rd["newly_suppressed"]):
            bad.append((k, "round record"))
    return not bad, {"mismatch": bad[:6]}


def c09(x):
    o = x.sopen
    ids = ast_ids(x.src("ab1c_select.py"))
    hits = hit_tokens(ids, SELECTION_FORBIDDEN)
    imports = {n.names[0].name.split(".")[0] for n in ast.walk(ast.parse(x.src("ab1c_select.py")))
               if isinstance(n, (ast.Import, ast.ImportFrom)) and getattr(n, "names", None)} | {
        n.module.split(".")[0] for n in ast.walk(ast.parse(x.src("ab1c_select.py"))) if isinstance(n, ast.ImportFrom) and n.module}
    ok = (o["data_reads"] == [str(ATTENTION[0])] and not o["violations"] and not any(o["modules_loaded"].values())
          and not hits and "cv2" not in imports)
    return ok, {"data_reads": o["data_reads"], "violations": len(o["violations"]), "identifier_hits": hits}


def c10(x, stage="full"):
    fz = x.sfz
    files_ok = all(sha256(x.run / n) == h for n, h in fz["files"].items()) and set(fz["files"]) == {
        "selection/safe-forward-mask.npz", "selection/selected-gazes.json", "selection/nms-rounds.json",
        "selection/selection-summary.json", "selection/selection-opened-files.json"}
    gz = [(g["rank"], g["row"], g["col"], g["yaw_deg"], g["pitch_deg"]) for g in x.sel]
    fzg = [(g["rank"], g["row"], g["col"], g["yaw_deg"], g["pitch_deg"]) for g in fz["gazes"]]
    ok = files_ok and gz == fzg
    det = {"freeze_files_verify": files_ok, "gazes_equal_freeze": gz == fzg}
    if stage == "selection":
        return ok, det
    cmds = [e["command"] for e in x.log if e["status"] == "ok"]
    order_ok = all(cmds.index(a) < cmds.index(b) for a, b in (("freeze-selection", "plan"), ("plan", "preflight"),
                                                             ("preflight", "acquire")) if a in cmds and b in cmds)
    chk = x.j("selection/selection-check.json")
    plan = x.j("plan/plan-record.json")
    same = all(x.per("calib", g)["gaze_yaw_pitch_deg"] == [s["yaw_deg"], s["pitch_deg"]]
               == x.per("plan", g)["gaze_yaw_pitch_deg"] for g, s in zip(GAZES, fz["gazes"]))
    acq_ok = all(x.per("acq", g)["ab1c_rank"] == k for k, g in enumerate(GAZES, start=1))
    ok = (ok and order_ok and chk["passed"] and chk["selection_freeze_sha256"] == sha256(x.run / "selection/safe-forward-freeze.json")
          and plan["selection_check_sha256"] == sha256(x.run / "selection/selection-check.json")
          and plan["selection_freeze_sha256"] == sha256(x.run / "selection/safe-forward-freeze.json") and same and acq_ok
          and sorted(p.name for p in (x.run / "observations").iterdir() if p.name != "evaluation_only") == list(GAZES))
    return ok, det | {"order": order_ok, "independent_check_passed": chk.get("passed"), "observed_gazes_are_frozen": same}


def c11(x):
    pose = json.loads(HEAD_POSE[0].read_text())
    bad = []
    for g, s in zip(GAZES, x.sfz["gazes"]):
        p = x.per("plan", g)
        rl, rr = own_eye_rotations(s["yaw_deg"], s["pitch_deg"])
        k = np.array([[FOCAL, 0, (RAW - 1) / 2], [0, FOCAL, (RAW - 1) / 2], [0, 0, 1.0]])
        ok = (np.allclose(p["eyes"][0]["R_hc"], rl, atol=1e-12) and np.allclose(p["eyes"][1]["R_hc"], rr, atol=1e-12)
              and all(np.allclose(e["K"], k, atol=1e-9) for e in p["eyes"])
              and p["eyes"][0]["centre_h_m"] == [-IPD / 2, 0.0, 0.0] and p["eyes"][1]["centre_h_m"] == [IPD / 2, 0.0, 0.0]
              and np.allclose(p["head_R_wh"], pose["head_R_wh"], atol=0) and np.allclose(p["head_origin_w_m"],
                                                                                         pose["head_origin_w_m"], atol=0)
              and p["image_size_wh"] == [RAW, RAW] and p["core_size"] == CORE and p["ipd_m"] == IPD
              and p["prescribed_vergence_distance_m"] == VERGENCE and p.get("tangent_frame") == "baseline_projected"
              and sha256(x.run / "plan" / g / "planned-calibration.json") == x.j("plan/plan-record.json")["gazes"][
                  GAZES.index(g)]["planned_calibration_sha256"])
        if not ok:
            bad.append(g)
    return not bad, {"bad": bad}


def c12(x):
    acq = [e for e in x.log if e["command"] == "acquire"]
    renders = [e for e in x.log if e.get("blender") and e["command"] not in ("acquire", "preflight", "rehearse")]
    obs = sorted(p.name for p in (x.run / "observations").iterdir())
    pre = [e for e in x.log if e["command"] == "preflight"]
    ok = (len(acq) == 1 and acq[0]["status"] == "ok" and acq[0]["blender"]["mode"] == "canonical"
          and "classroom_eye.blend" in " ".join(acq[0]["blender"]["argv"]) and not renders
          and obs == sorted(list(GAZES) + ["evaluation_only"]) and len(pre) == 1
          and all(len(list((x.run / "observations" / g / "acquisition").iterdir())) == 3 for g in GAZES)
          and x.j("preflight/preflight.json")["rendered"] is False)
    return ok, {"acquire_entries": len(acq), "observation_dirs": obs}


def calib_diff(a, b) -> float:
    if isinstance(a, dict) and isinstance(b, dict):
        return max([calib_diff(a[k], b[k]) for k in a] or [0.0]) if set(a) == set(b) else math.inf
    if isinstance(a, list) and isinstance(b, list):
        return max([calib_diff(p, q) for p, q in zip(a, b)] or [0.0]) if len(a) == len(b) else math.inf
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return abs(float(a) - float(b))
    return 0.0 if a == b else math.inf


def c13(x):
    bad = {}
    for g in GAZES:
        a = x.per("acq", g)
        diff = calib_diff(x.per("plan", g), x.per("calib", g))
        if not (diff <= 1e-9 and a["device"] == DEVICE and a["spp"] == SPP and a["render_seeds_lr"] == SEEDS
                and a["calibration_sha256"] == sha256(x.run / f"observations/{g}/acquisition/calibration.json")):
            bad[g] = diff
    return not bad, {"bad": bad}


def exr_pass_names(channels) -> set:
    return {".".join(ch.split(".")[1:-1]) for ch in channels}


def c14(x):
    _generator("exr_lite")
    from exr_lite import read_header, read_uncompressed_exr
    bad = {}
    for g in GAZES:
        a = x.per("acq", g)
        rgb = x.per("rgb", g)
        if sorted(rgb) != ["rgb_L", "rgb_R"] or a["rgb_observation_sha256"] != sha256(
                x.run / f"observations/{g}/acquisition/rgb-observation.npz"):
            bad[g] = "rgb arrays / hash"
            continue
        for side in ("L", "R"):
            p = x.run / f"observations/{g}/evaluation_only/raw_{side}.exr"
            hdr = [ch[0] for ch in read_header(p.read_bytes())[0]["channels"]]
            passes = exr_pass_names(a["exr_channels_lr"][side])
            ch = read_uncompressed_exr(str(p))
            names = set(ch)
            cr = [n for n in names if n.endswith("Combined.R")][0]
            cg = [n for n in names if n.endswith("Combined.G")][0]
            cb = [n for n in names if n.endswith("Combined.B")][0]
            comb = np.stack([np.asarray(ch[cr]), np.asarray(ch[cg]), np.asarray(ch[cb])], -1).astype(np.float32)
            if (sorted(hdr) != sorted(a["exr_channels_lr"][side]) or passes != REQUIRED_PASSES | INHERITED
                    or exr_pass_names(a["exr_channels_lr"]["L"]) != exr_pass_names(a["exr_channels_lr"]["R"])
                    or comb.shape != rgb[f"rgb_{side}"].shape
                    or not np.array_equal(comb.reshape(rgb[f"rgb_{side}"].shape), rgb[f"rgb_{side}"])):
                bad[f"{g}:{side}"] = sorted(passes ^ (REQUIRED_PASSES | INHERITED))
    return not bad, {"bad": bad}


def c15(x):
    bad = {}
    for g in GAZES:
        o, prod = x.own_oracle(g), x.per("prod", g)
        if not (np.array_equal(o["rows"], prod["left_core_row"]) and np.array_equal(o["cols"], prod["left_core_col"])
                and (np.max(np.abs(o["uv_R"] - prod["uv_R"])) if len(o["uv_R"]) else 0.0) <= TOL_UV):
            bad[g] = (len(o["rows"]), len(prod["left_core_row"]))
    return not bad, {"bad": bad}


def c16(x):
    det, ok = {}, True
    for g in GAZES:
        prod = x.per("prod", g)
        uv = prod["uv_R"]
        frac = float(np.mean(np.abs(uv - np.rint(uv)) > 1e-6)) if len(uv) else 1.0
        outside = int(((uv < ORIGIN) | (uv > ORIGIN + CORE - 1)).any(-1).sum()) if len(uv) else 0
        rec = x.per("osum", g)["right_margin"]["outside_right_nominal_core"]
        det[g] = {"non_integer_fraction": frac, "outside_right_nominal_core": outside}
        ok &= (len(uv) == 0 or frac > 0.5) and outside == rec and uv.dtype == np.float64
    return ok, det


def c17(x):
    bad = {}
    for g in GAZES:
        with np.load(x.run / f"oracle/{g}/oracle-correspondences.npz", allow_pickle=False) as z:
            keys = set(z.files)
        prod = x.per("prod", g)
        uv_l = np.stack([prod["left_core_col"] + ORIGIN, prod["left_core_row"] + ORIGIN], -1).astype(np.float64) \
            if len(prod["left_core_row"]) else np.zeros((0, 2))
        if (keys != PRODUCT_KEYS or any(t in k.lower() for k in keys for t in FORBIDDEN_KEY_TOKENS)
                or not np.array_equal(prod["uv_L"], uv_l)):
            bad[g] = sorted(keys)
    return not bad, {"bad": bad}


def c18(x):
    fz = x.cfz
    files_ok = all(sha256(x.run / n) == h for n, h in fz["files"].items())
    want = {f"oracle/{g}/{n}" for g in GAZES for n in ("oracle-correspondences.npz", "oracle-summary.json",
                                                       "oracle-opened-files.json")}
    cmds = [e["command"] for e in x.log if e["status"] == "ok"]
    order = all(cmds.index("freeze-correspondence") < cmds.index(s) for s in ("spherical", "planar") if s in cmds)
    reads = all({rrel(x, p) for p in x.per("oopen", g)["data_reads"]} == {f"observations/{g}/acquisition/calibration.json",
                                                                         f"observations/{g}/evaluation_only/reference-observation.npz"}
                and not x.per("oopen", g)["violations"] for g in GAZES)
    return files_ok and set(fz["files"]) == want and order and reads, {"files": files_ok, "order": order, "oracle_reads": reads}


def c19(x):
    bad = {}
    for g in GAZES:
        want = {f"observations/{g}/acquisition/calibration.json", f"oracle/{g}/oracle-correspondences.npz"}
        for kind in ("sopen", "popen"):
            o = x.per(kind, g)
            opened = [e["path"] for e in o["events"] if e.get("event") == "open"]
            truthy = [p for p in opened if p.endswith("reference-observation.npz") or p.endswith(".exr")
                      or "evaluation_only" in p]
            if {rrel(x, p) for p in o["data_reads"]} != want or o["violations"] or truthy or o["position_reads"] or o["object_index_reads"]:
                bad[f"{g}:{kind}"] = {"reads": o["data_reads"], "truth": truthy}
        if any(x.per("sopen", g)["modules_loaded"].values()):
            bad[f"{g}:spherical modules"] = x.per("sopen", g)["modules_loaded"]
    planar_ids = ast_ids(x.src("ab1c_planar.py"))
    run_src = x.src("ab1c_run.py")
    sph_ids = ast_ids(func_src(run_src, ("run_spherical_gaze", "compare_core", "consistency_control")))
    hits = hit_tokens(planar_ids, GEOMETRY_TRUTH) + hit_tokens(sph_ids, GEOMETRY_TRUTH)
    return not bad and not hits, {"bad": bad, "identifier_hits": hits}


def c20(x):
    bad = []
    for g in GAZES:
        ps = x.cfz["files"][f"oracle/{g}/oracle-correspondences.npz"]
        cs = sha256(x.run / f"observations/{g}/acquisition/calibration.json")
        ss, pp = x.per("ssum", g), x.per("psum", g)
        sph, pla, prod = x.per("sph", g), x.per("pla", g), x.per("prod", g)
        if not (ss["inputs"]["correspondences"]["sha256"] == pp["inputs"]["correspondences"]["sha256"] == ps
                and ss["inputs"]["calibration"]["sha256"] == pp["inputs"]["calibration"]["sha256"] == cs
                and all(np.array_equal(r[k], prod[k]) for r in (sph, pla) for k in ("left_core_row", "left_core_col"))):
            bad.append(g)
    return not bad, {"bad": bad}


def c21(x):
    worst = 0.0
    for g in GAZES:
        o, s = x.own_sph(g), x.per("sph", g)
        if len(o["d_L"]):
            worst = max(worst, float(np.max(np.abs(o["theta_L"] - s["theta_L"]))), float(np.max(np.abs(o["theta_R"] - s["theta_R"]))),
                        float(np.max(np.abs(np.angle(np.exp(1j * (o["phi_L"] - s["phi_L"])))))),
                        float(np.max(np.abs(np.angle(np.exp(1j * (o["phi_R"] - s["phi_R"])))))),
                        float(np.max(np.abs(o["d_L"] - s["d_L"]))))
        rays = x.per("rays", g)
        cal = x.per("calib", g)
        d = own_rays(cal["eyes"][0], rays["uv"].reshape(-1, 2))
        worst = max(worst, float(np.max(np.abs(own_theta(d) - rays["theta"].ravel()))))
    return worst <= TOL_ANG, {"max_angle_diff": worst}


def c22(x):
    worst, wray = 0.0, 0.0
    for g in GAZES:
        o, s = x.own_sph(g), x.per("sph", g)
        if not len(o["d_L"]):
            continue
        v = s["valid_epi"].astype(bool)
        worst = max(worst, float(np.nanmax(np.abs(o["P_epi"][v] - s["P_epi"][v]))) if v.any() else 0.0)
        wray = max(wray, float(np.nanmax(np.abs(o["P_ray"] - s["P_ray"]))))
        if not np.array_equal(v, np.isfinite(o["P_epi"]).all(-1)):
            return False, {"validity": g}
    return worst <= TOL_XYZ and wray <= TOL_RAY, {"max_epi_diff_m": worst, "max_ray_diff_m": wray}


def c23(x):
    worst = 0.0
    for g in GAZES:
        o, s = x.own_sph(g), x.per("sph", g)
        if not len(o["d_L"]):
            continue
        dth = o["theta_R"] - o["theta_L"]
        with np.errstate(divide="ignore", invalid="ignore"):
            kap = 1 / np.abs(np.sin(o["gamma"]))
            rpp = IPD * np.sin(o["theta_L"]) / np.sin(dth) ** 2 / FOCAL
        worst = max(worst, float(np.max(np.abs(o["gamma"] - s["gamma"]))),
                    float(np.max(np.abs(kap - s["kappa"]) / kap)), float(np.max(np.abs(rpp - s["range_per_px"]) / np.abs(rpp))))
    return worst <= 1e-8, {"max_rel_diff": worst}


def c24(x):
    bad = {}
    for g in GAZES:
        own, pla = x.own_rect(g), x.per("pla", g)
        for k in ("R1", "R2", "P1", "P2", "Q_full"):
            if not np.allclose(own[k], pla[k], rtol=0, atol=1e-9 * max(1.0, float(np.max(np.abs(own[k]))))):
                bad[f"{g}:{k}"] = float(np.max(np.abs(own[k] - pla[k])))
        if not np.array_equal(pla["crop_xywh"], [ORIGIN, ORIGIN, CORE, CORE]):
            bad[f"{g}:crop"] = pla["crop_xywh"].tolist()
    return not bad, {"bad": bad}


def c25(x):
    worst, bad = 0.0, []
    for g in GAZES:
        o, p = x.own_pla(g), x.per("pla", g)
        if not len(o["disparity"]):
            continue
        worst = max(worst, float(np.max(np.abs(o["uvrect_L"] - p["uvrect_L"]))), float(np.max(np.abs(o["uvrect_R"] - p["uvrect_R"]))))
        if not (np.array_equal(o["w_L"] > 1e-12, p["w_L"] > 1e-12) and np.array_equal(o["w_R"] > 1e-12, p["w_R"] > 1e-12)):
            bad.append(g)
    return worst <= TOL_UV and not bad, {"max_uv_diff_px": worst, "in_front_mismatch": bad}


def c26(x):
    worst, bad = 0.0, []
    for g in GAZES:
        o, p = x.own_pla(g), x.per("pla", g)
        if not len(o["disparity"]):
            continue
        if not np.array_equal(o["valid_planar"], p["valid_planar"].astype(bool)):
            bad.append(g)
            continue
        v = o["valid_planar"]
        if v.any():
            worst = max(worst, float(np.max(np.abs(o["P_planar"][v] - p["P_planar"][v]))),
                        float(np.max(np.abs(o["disparity"] - p["disparity"]))))
    return worst <= TOL_XYZ and not bad, {"max_diff": worst, "validity_mismatch": bad}


def c27(x):
    import cv2
    bad = {}
    for g in GAZES:
        c, own = x.per("calib", g), x.own_rect(g)
        sup = x.per("psup", g)["eyes"]
        dg = own_gaze(*c["gaze_yaw_pitch_deg"])
        for i, side, rk, pk in ((0, "L", "R1", "P1"), (1, "R", "R2", "P2")):
            kk = np.asarray(c["eyes"][i]["K"], np.float64)
            mx, my = cv2.initUndistortRectifyMap(kk, np.zeros(5), own[rk], own[pk][:, :3], (RAW, RAW), cv2.CV_32FC1)
            mx, my = mx[ORIGIN:ORIGIN + CORE, ORIGIN:ORIGIN + CORE], my[ORIGIN:ORIGIN + CORE, ORIGIN:ORIGIN + CORE]
            inn = ((mx >= ORIGIN - 0.5) & (mx <= ORIGIN + CORE - 0.5) & (my >= ORIGIN - 0.5) & (my <= ORIGIN + CORE - 0.5))
            p = own[pk]
            u0 = ORIGIN + (CORE - 1) / 2
            ray = np.array([(u0 - p[0, 2]) / p[0, 0], (u0 - p[1, 2]) / p[1, 1], 1.0])
            rh = unit(np.asarray(c["eyes"][i]["R_hc"], np.float64) @ (own[rk].T @ ray))
            e = sup[side]
            want = {"rectified_core_pixels_from_nominal_raw_core": int(inn.sum()),
                    "rectified_core_centre_from_gaze_deg": math.degrees(math.atan2(np.linalg.norm(np.cross(rh, dg)), rh @ dg)),
                    "rectified_core_centre_from_baseline_deg": math.degrees(math.atan2(np.hypot(rh[1], rh[2]), abs(rh[0])))}
            spans = {"x": float(mx.max() - mx.min()), "y": float(my.max() - my.min())}
            ok = (e["rectified_core_pixels_from_nominal_raw_core"] == want["rectified_core_pixels_from_nominal_raw_core"]
                  and abs(e["rectified_core_centre_from_gaze_deg"] - want["rectified_core_centre_from_gaze_deg"]) <= 1e-7
                  and abs(e["rectified_core_centre_from_baseline_deg"] - want["rectified_core_centre_from_baseline_deg"]) <= 1e-7
                  and abs(e["raw_source_of_rectified_core_px"]["x"][0] - float(mx.min())) <= 1e-6
                  and abs(e["raw_source_of_rectified_core_px"]["y"][1] - float(my.max())) <= 1e-6
                  and abs(e["raw_source_span_px"]["x"] - spans["x"]) <= 1e-6
                  and e["support_finite"] == bool(np.isfinite(mx).all() and np.isfinite(my).all())
                  and e["support_two_dimensional"] == (spans["x"] >= 1.0 and spans["y"] >= 1.0)
                  and abs(e["rectified_principal_point_px"][0] - float(p[0, 2])) <= 1e-9
                  and abs(e["rectified_core_fraction_from_nominal_raw_core"] - int(inn.sum()) / CORE ** 2) <= 1e-15)
            if not ok:
                bad[f"{g}:{side}"] = want
    return not bad, {"bad": bad}


def own_compare(x, g):
    c, s, p = x.per("calib", g), x.per("sph", g), x.per("pla", g)
    common = s["valid_epi"].astype(bool) & p["valid_planar"].astype(bool)
    o_l = np.asarray(c["eyes"][0]["centre_h_m"], np.float64)
    d = np.linalg.norm(p["P_planar"][common] - s["P_epi"][common], axis=-1)
    rs = np.linalg.norm(s["P_epi"][common] - o_l, axis=-1)
    rad = np.linalg.norm(p["P_planar"][common] - o_l, axis=-1) - rs
    return common, d, rad, d / rs


def c28(x):
    bad = {}
    for g in GAZES:
        common, _d, _r, _rel = own_compare(x, g)
        s, p = x.per("sph", g).get("valid_epi").astype(bool), x.per("pla", g)["valid_planar"].astype(bool)
        k = x.csum["per_gaze"][g]["counts"]
        want = {"raw_core_pixels": CORE * CORE, "correspondences": int(common.size), "planar_valid": int(p.sum()),
                "spherical_valid": int(s.sum()), "common_valid": int(common.sum()), "planar_only": int((p & ~s).sum()),
                "spherical_only": int((s & ~p).sum())}
        cm = x.per("cmp", g)
        if k != want or not np.array_equal(cm["common"].astype(bool), common) or not all(
                np.array_equal(cm[kk], x.per("prod", g)[kk]) for kk in ("left_core_row", "left_core_col")):
            bad[g] = {"recorded": k, "own": want}
    return not bad, {"bad": bad}


def c29(x):
    bad = []
    pool = {"d": [], "rad": [], "rel": []}
    for g in GAZES:
        common, d, rad, rel = own_compare(x, g)
        pg = x.csum["per_gaze"][g]
        cm = x.per("cmp", g)
        if not (qeq(pg["planar_minus_spherical_m"], quant(d)) and qeq(pg["radial_signed_planar_minus_spherical_m"], quant(rad), absol=1e-15)
                and qeq(pg["relative_difference"], quant(rel))
                and np.allclose(cm["difference_m"][common], d, rtol=0, atol=1e-15)):
            bad.append(g)
        pool["d"].append(d)
        pool["rad"].append(rad)
        pool["rel"].append(rel)
    po = x.csum["pooled"]
    pooled = (qeq(po["planar_minus_spherical_m"], quant(np.concatenate(pool["d"])))
              and qeq(po["radial_signed_planar_minus_spherical_m"], quant(np.concatenate(pool["rad"])), absol=1e-15)
              and po["common_valid"] == int(sum(len(a) for a in pool["d"])))
    return not bad and pooled, {"bad": bad, "pooled": pooled}


def c30(x):
    fz = x.gfz
    files_ok = all(sha256(x.run / n) == h for n, h in fz["files"].items()) and all(
        sha256(v["path"]) == v["sha256"] for v in fz["calibrations"].values())
    cmds = [e["command"] for e in x.log if e["status"] == "ok"]
    order = all(cmds.index("freeze-geometry") < cmds.index(s) for s in ("compare", "evaluate") if s in cmds) and all(
        cmds.index(s) < cmds.index("freeze-geometry") for s in ("spherical", "planar"))
    pre = all(all(v.values()) for v in fz["preconditions"].values())
    hashes = (x.csum["geometry_freeze_sha256"] == sha256(x.run / "freeze/geometry-freeze.json")
              == x.ev["geometry_freeze_sha256"])
    return files_ok and order and pre and hashes, {"files": files_ok, "order": order, "preconditions": pre, "hashes": hashes}


def c31(x):
    ev = [str(e) for e in x.evopen["ordered_data_events"]]
    try:
        i_fz, i_ref = ev.index("geometry_freeze_verified"), ev.index("reference_access_begins")
    except ValueError:
        return False, {"events": ev[:6]}
    refs = [k for k, p in enumerate(ev) if p.endswith("reference-observation.npz") or "evaluation_only" in p]
    copen = [e["path"] for e in x.copen["events"] if e.get("event") == "open"]
    truth_in_compare = [p for p in copen if p.endswith("reference-observation.npz") or "evaluation_only" in p]
    ok = i_fz < i_ref and refs and min(refs) > i_ref and not x.evopen["violations"] and not truth_in_compare
    return ok, {"freeze_mark": i_fz, "reference_mark": i_ref, "first_reference": min(refs) if refs else None,
                "truth_in_compare": truth_in_compare}


def c32(x):
    fz_ok = all(sha256(x.run / n) == h for n, h in x.gfz["files"].items())
    cmp_ok = all(sha256(x.run / n) == h for n, h in x.ev["comparison_sha256"].items())
    writes = [w for w in x.evopen["writes"] if not rrel(x, w).startswith("evaluation/")]
    return fz_ok and cmp_ok and not writes and x.ev["frozen_geometry_sha256"] == x.gfz["files"], {
        "freeze": fz_ok, "comparison": cmp_ok, "writes_outside": writes}


def c33(x):
    bad = []
    pool = {"planar": [], "spherical": []}
    for g in GAZES:
        c, ev, evr = x.per("calib", g), x.ev["per_gaze"][g], x.per("evr", g)
        pt = x.ptruth(g)
        o_l = np.asarray(c["eyes"][0]["centre_h_m"], np.float64)
        if len(pt) and float(np.max(np.abs(evr["P_truth"] - pt))) > 1e-12:
            bad.append((g, "P_truth"))
        for name, p, v in (("planar", x.per("pla", g)["P_planar"], x.per("pla", g)["valid_planar"].astype(bool)),
                           ("spherical", x.per("sph", g)["P_epi"], x.per("sph", g)["valid_epi"].astype(bool))):
            e3 = np.linalg.norm(p[v] - pt[v], axis=-1)
            rad = np.linalg.norm(p[v] - o_l, axis=-1) - np.linalg.norm(pt[v] - o_l, axis=-1)
            rec = ev[f"{name}_vs_truth"]
            fr = {f"{s:.3f}": float((e3 <= s).mean()) for s in FRACTIONS} if e3.size else None
            if not (qeq(rec["error_3d_m"], quant(e3)) and qeq(rec["radial_signed_m"], quant(rad), absol=1e-15)
                    and rec["pairs"] == int(v.sum()) and rec["fraction_3d_within_m"] == fr):
                bad.append((g, name))
            pool[name].append(e3)
    for name in pool:
        if not qeq(x.ev["pooled"][f"{name}_vs_truth"]["error_3d_m"], quant(np.concatenate(pool[name]))):
            bad.append(("pooled", name))
    return not bad, {"bad": bad}


def c34(x):
    bad = []
    for g in GAZES:
        c, prod, ev = x.per("calib", g), x.per("prod", g), x.ev["per_gaze"][g]
        for name, p, v in (("planar", x.per("pla", g)["P_planar"], x.per("pla", g)["valid_planar"].astype(bool)),
                           ("spherical", x.per("sph", g)["P_epi"], x.per("sph", g)["valid_epi"].astype(bool))):
            ul, _ = own_project(c["eyes"][0], p)
            ur, _ = own_project(c["eyes"][1], p)
            rl, rr = np.linalg.norm(ul - prod["uv_L"], axis=-1), np.linalg.norm(ur - prod["uv_R"], axis=-1)
            rec = ev[f"{name}_reprojection_px"]
            if not (qeq(rec["left"], quant(rl[v]), rel=1e-6, absol=1e-9) and qeq(rec["right"], quant(rr[v]), rel=1e-6, absol=1e-9)):
                bad.append((g, name))
    return not bad, {"bad": bad}


def c35(x):
    bad = []
    for g in GAZES:
        s, ss, p, ps = x.per("sph", g), x.per("ssum", g), x.per("pla", g), x.per("psum", g)
        ve, vp = s["valid_epi"].astype(bool), p["valid_planar"].astype(bool)
        dd, pd = ss["distributions"], ps["distributions"]
        dth = s["delta_theta"]
        ok = (qeq(dd["kappa"], quant(s["kappa"])) and qeq(dd["abs_phi_residual_rad"], quant(np.abs(s["phi_residual"])))
              and qeq(dd["delta_theta_rad"], quant(dth)) and ss["counts"]["triangulated_epipolar"] == int(ve.sum())
              and ss["counts"]["delta_theta_positive"] == int((dth > 0).sum())
              and qeq(pd["disparity_px"], quant(p["disparity"][vp])) and qeq(pd["z_rect_m"], quant(p["z_rect"][vp]))
              and ps["counts"]["valid_planar"] == int(vp.sum())
              and ps["counts"]["disparity_positive"] == int((p["disparity"] > 0).sum())
              and ps["counts"]["rect_L_in_central_core"] == int(p["rect_L_in_central_core"].sum()))
        if not ok:
            bad.append(g)
    return not bad, {"bad": bad}


_FIG_CACHE: dict = {}


def c36(x):
    V = _generator("ab1c_visuals")
    man = json.loads((x.vis / "visuals-manifest.json").read_text())
    key = tuple(sorted((k, sha256(Path(k) if k.startswith("/") else x.run / k)) for k in man["sources"]))
    if key not in _FIG_CACHE:
        figs, _d = V.render_all(x.run)
        _FIG_CACHE.clear()
        _FIG_CACHE[key] = {n: V.png_bytes(f) for n, f in figs.items()}
    figs = _FIG_CACHE[key]
    bad = [n for n in FIGURES if n not in figs or not (x.vis / n).is_file() or (x.vis / n).read_bytes() != figs[n]
           or man["figures"][n]["sha256"] != sha256(x.vis / n)]
    return not bad and sorted(figs) == sorted(FIGURES), {"mismatch": bad}


def c37(x):
    man = json.loads((x.vis / "visuals-manifest.json").read_text())
    badge = {n: man["figures"][n]["badges"] for n in FIGURES}
    ok = (badge == BADGES and x.ssum["truth"] == DER and x.csum["truth"] == DER and x.ev["truth"] == REF
          and all(x.per("ssum", g)["truth"] == DER and x.per("psum", g)["truth"] == DER and x.per("osum", g)["truth"] == DER
                  for g in GAZES)
          and not any("CONTROLLER-TIME" in b for bs in badge.values() for b in bs)
          and x.ssum.get("label") == "EXPERIMENT SELECTION")
    return ok, {"badges_equal": badge == BADGES}


def c38(x):
    hits = {}
    for n in GENERATOR:
        h = hit_tokens(ast_ids(x.src(n)), MATCHER_IDS)
        if h:
            hits[n] = h
    logs = [e["command"] for e in x.log if any(t in json.dumps(e).lower() for t in ("sgbm", "\"matcher\""))]
    return not hits and not logs, {"identifier_hits": hits, "log": logs}


def c39(x):
    hits = {}
    for n in GENERATOR:
        h = hit_tokens(ast_ids(x.src(n)), CONTROL_IDS)
        if h:
            hits[n] = h
    data_paths = (str(HEAD_POSE[0]),)
    bad_log = [e["command"] for e in x.log if e["command"] not in COMMANDS or any(
        t in " ".join(str(a) for a in e.get("argv", []) if str(a) not in data_paths).lower() for t in ("controller", "fsg6f"))]
    pose = json.loads(HEAD_POSE[0].read_text())
    one = all(np.allclose(x.per("calib", g)["head_R_wh"], pose["head_R_wh"], rtol=0, atol=1e-9)
              and np.allclose(x.per("calib", g)["head_origin_w_m"], pose["head_origin_w_m"], rtol=0, atol=1e-9) for g in GAZES)
    return not hits and not bad_log and one, {"identifier_hits": hits, "log": bad_log, "one_fixed_head_pose": one}


def c40(x):
    ok = True
    for g in GAZES:
        cs = sha256(x.run / f"observations/{g}/acquisition/calibration.json")
        for kind in ("ssum", "psum"):
            ok &= rrel(x, x.per(kind, g)["inputs"]["calibration"]["path"]) == f"observations/{g}/acquisition/calibration.json" \
                and x.per(kind, g)["inputs"]["calibration"]["sha256"] == cs
    acq = [e for e in x.log if e["command"] == "acquire"]
    n_acq_json = len(list((x.run / "observations").glob("*/acquisition/acquisition.json")))
    return ok and len(acq) == 1 and n_acq_json == 3, {"inputs_are_the_observation": ok, "acquisitions": n_acq_json}


def c41(x):
    ch = x.changed_files
    acc = [f for f in ch if f.startswith(("fov3d/", "tools/controller/", "tools/natural_bootstrap/", "tools/classroom_oracle/",
                                          "tools/visual_language/", "tools/baseline/", "scenes/"))
           or (f.startswith("tools/") and f.count("/") == 1)
           or (f.startswith("tools/active_bootstrap/ab1a_") or f.startswith("tools/active_bootstrap/ab1b_")
               or f in ("tools/active_bootstrap/check_ab1a.py", "tools/active_bootstrap/check_ab1b.py"))]
    code = {p: sha256(REPO / p) == h for p, h in CODE_PINS.items()}
    acc_p = {k: sha256(p) == h for k, (p, h) in ACCEPTED.items()}
    return not acc and all(code.values()) and all(acc_p.values()), {"accepted_files_changed": acc,
                                                                    "code": {k: v for k, v in code.items() if not v},
                                                                    "products": {k: v for k, v in acc_p.items() if not v}}


def c42(x):
    extra = [f for f in x.changed_files if f not in DECLARED]
    return not extra, {"undeclared": extra[:8]}


def c43(x):
    rep = x.j("synthetic/synthetic-report.json")
    reh = x.j("synthetic/blender-rehearsal/rehearsal-report.json")
    own = indep_synthetic()
    ok = (rep["passed"] and all(c["ok"] for c in rep["cases"]) and len(rep["cases"]) == 15 and reh["passed"]
          and len(reh["cases"]) == 3 and all(c["ok"] for c in reh["cases"]) and all(own.values()))
    return ok, {"synthetic": sum(c["ok"] for c in rep["cases"]), "rehearsal": reh["passed"], "own": own}


def indep_synthetic() -> dict:
    """The checker's own subset: exact forward pairs, both generators against an analytic answer and each other; the
    generator NMS against the accepted NB1c NMS."""
    SEL, PL, BG = _generator("ab1c_select"), _generator("ab1c_planar"), _generator("ab1b_geometry")
    NC = _generator("nb1c_attention")
    c = SEL.selection_calibration(5.0, -3.0)
    o_l = np.array([-IPD / 2, 0, 0.0])
    rows, cols = np.array([0, 100, 255], np.int32), np.array([255, 30, 128], np.int32)
    uvl = np.stack([cols + ORIGIN, rows + ORIGIN], -1).astype(np.float64)
    p = o_l + np.array([1.5, 3.0, 5.0])[:, None] * own_rays(c["eyes"][0], uvl)
    uvr, _ = own_project(c["eyes"][1], p)
    prod = {"left_core_row": rows, "left_core_col": cols, "uv_L": uvl, "uv_R": uvr}
    s = BG.compute_epipolar(c, prod)
    pl = PL.triangulate(c, PL.rectify(c), prod)
    rng = np.random.default_rng(3)
    a = rng.normal(size=(H_GRID, W_GRID))
    d, _y, _p = own_grid()
    p1, _ = SEL.select_gazes(a, d, np.ones(a.shape, bool), 4)
    p2, _ = NC.select_gazes(a, d, 4)
    own = [o["index"] for o in own_nms(a, d, np.ones(a.shape, bool), 4)]
    return {"spherical_exact": float(np.max(np.abs(s["P_epi"] - p))) <= 1e-9,
            "planar_exact": float(np.max(np.abs(pl["P_planar"] - p))) <= 1e-9, "nms_equal": p1 == p2 == own}


def c44(x):
    bad = {}
    for g in GAZES:
        o, s = x.own_oracle(g), x.per("osum", g)
        rec = [a["remaining"] for a in s["attrition"]]
        if rec != o["attrition"] or any(a < b for a, b in zip(rec, rec[1:])) or s["correspondences"] != o["attrition"][-1]:
            bad[g] = {"recorded": rec, "own": o["attrition"]}
    return not bad, {"bad": bad}


def c45(x):
    ok_cmds = [e["command"] for e in x.log if e["status"] == "ok"]
    canon = [cmd for cmd in ok_cmds if cmd in ORDER]
    failed_canon = [e["command"] for e in x.log if e["command"] in ORDER and e["status"] != "ok"]
    pre = [cmd for cmd in ok_cmds[:ok_cmds.index("source")]] if "source" in ok_cmds else []
    canon_ok = all(e["code"]["dirty"] is False and e["code"]["pushed"] is True for e in x.log if e["command"] in ORDER)
    ok = (canon == ORDER and not failed_canon and "synthetic" in pre and "rehearse" in pre and canon_ok
          and ok_cmds.index("visualize") > ok_cmds.index("evaluate"))
    return ok, {"canonical_order": canon, "failed_canonical": failed_canon, "clean_pushed": canon_ok}


CHECKS = [(f"{i:02d}", name, fn) for i, (name, fn) in enumerate([
    ("canonical repository, base and source pins; accepted products unchanged", c01),
    ("the selection input is exactly the pinned NB1c attention A", c02),
    ("the 20-degree forward cone recomputes for every cell", c03),
    ("the full-core leverage recomputes for every cone cell (>= 0.90)", c04),
    ("the eligibility mask equals the independent mask", c05),
    ("K = 3, D_MIN = 2 atan(sqrt2 tan 6 deg), tie rule, no score threshold", c06),
    ("the greedy NMS recomputes inside the eligible set", c07),
    ("the selected-gaze records recompute", c08),
    ("the selection read only the attention raster (guard, static audit)", c09),
    ("the selection freeze verifies and precedes plan / preflight / acquisition; no replacement", c10),
    ("the planned calibrations recompute (head-frame eyes, accepted head pose)", c11),
    ("exactly three observations from exactly one acquisition; no other render", c12),
    ("each observation's calibration equals its plan; device / spp / seeds", c13),
    ("RGB observation = EXR Combined; EXR passes = required + pinned inherited", c14),
    ("the oracle recomputes per gaze", c15),
    ("continuous uv_R retained; the padded right raster is used", c16),
    ("the product holds exactly the four truth-free keys", c17),
    ("the correspondence freeze verifies and precedes both geometries", c18),
    ("both geometries read exactly calibration + product; no truth", c19),
    ("planar and spherical consumed the identical product and calibration", c20),
    ("spherical theta / phi convention recomputes", c21),
    ("spherical triangulation (law of sines) and ray-ray (Cramer) recompute", c22),
    ("conditioning recomputes (gamma, kappa, range_per_px)", c23),
    ("the accepted planar rectification recomputes (own stereoRectify)", c24),
    ("raw -> rectified recomputes (cv2.undistortPoints; in-front test)", c25),
    ("the planar triangulation recomputes (own Z = f' B / d route)", c26),
    ("the planar support diagnostic recomputes", c27),
    ("the common valid set recomputes", c28),
    ("the direct planar vs spherical statistics recompute (per gaze and pooled)", c29),
    ("the geometry freeze verifies and precedes comparison and evaluation", c30),
    ("Position / Object Index opened only after the freeze marks", c31),
    ("evaluation cannot alter frozen products", c32),
    ("P_truth and both truth-error statistics recompute", c33),
    ("both reprojection residuals recompute", c34),
    ("per-gaze geometry summaries recompute", c35),
    ("figures regenerate deterministically", c36),
    ("truth-class labels", c37),
    ("no natural matcher", c38),
    ("no controller / FSG6f / fusion / head motion; one fixed head pose", c39),
    ("no second acquisition for either representation", c40),
    ("accepted historical code and run products unchanged", c41),
    ("changed tracked files are only the declared ones", c42),
    ("synthetic known answers and the Blender rehearsal pass (and the checker's own subset)", c43),
    ("oracle attrition is sequential and recomputes", c44),
    ("run order: each canonical step once, in order, clean and pushed", c45)], start=1)]
SELECTION_STAGE = ("01", "02", "03", "04", "05", "06", "07", "08", "09", "10")


def run_checks(ctx, quiet=False, stage="full") -> list[dict]:
    res = []
    for num, name, fn in CHECKS:
        if stage == "selection" and num not in SELECTION_STAGE:
            continue
        try:
            ok, detail = fn(ctx, "selection") if (stage == "selection" and num == "10") else fn(ctx)
        except Exception as exc:
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        res.append({"check": num, "name": name, "ok": bool(ok), "detail": json.loads(json.dumps(detail, default=str))})
        if not quiet:
            print(f"{PREFIX} {'PASS' if ok else 'FAIL'} {num} {name}" + ("" if ok else f" -- {str(detail)[:300]}"))
    return res


# ------------------------------------------------------------------ corruption suite
def mirror(run: Path, vis: Path, tmp: Path) -> tuple[Path, Path]:
    def copy_tree(src, dst):
        for p in src.rglob("*"):
            q = dst / p.relative_to(src)
            if p.is_dir():
                q.mkdir(parents=True, exist_ok=True)
            elif p.suffix in (".json", ".jsonl"):
                q.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, q)
            else:
                q.parent.mkdir(parents=True, exist_ok=True)
                q.symlink_to(p.resolve())
    r, v = tmp / "r" / run.name, tmp / "v" / vis.name
    copy_tree(run, r)
    copy_tree(vis, v)
    return r, v


def edit_json(path: Path, fn) -> None:
    d = json.loads(path.read_text())
    fn(d)
    path.write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")


def load_npz(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]).copy() for k in z.files}


def save_npz(path: Path, d: dict) -> None:
    if path.exists() or path.is_symlink():
        path.unlink()
    np.savez_compressed(path, **d)


def edit_npz(path: Path, fn) -> None:
    d = load_npz(path)
    fn(d)
    save_npz(path, d)


def refreeze_sel(m: Path) -> None:
    edit_json(m / "selection/safe-forward-freeze.json", lambda d: d["files"].update({n: sha256(m / n) for n in d["files"]}))


def refreeze_geom(m: Path) -> None:
    edit_json(m / "freeze/geometry-freeze.json", lambda d: d["files"].update({n: sha256(m / n) for n in d["files"]}))
    h = sha256(m / "freeze/geometry-freeze.json")
    edit_json(m / "comparison/comparison-summary.json", lambda d: d.update(geometry_freeze_sha256=h))
    fz = json.loads((m / "freeze/geometry-freeze.json").read_text())

    def fn(d):
        d.update(geometry_freeze_sha256=h, frozen_geometry_sha256=fz["files"])
        d["comparison_sha256"] = {n: sha256(m / n) for n in d["comparison_sha256"]}
    edit_json(m / "evaluation/evaluation-summary.json", fn)


def refreeze_corr(m: Path) -> None:
    edit_json(m / "oracle/correspondence-freeze.json", lambda d: d["files"].update({n: sha256(m / n) for n in d["files"]}))
    refreeze_geom(m)


def regen_spherical(m: Path, ctx: Ctx, g: str, patches=()) -> None:
    BG = _generator("ab1b_geometry")
    c, prod = ctx.per("calib", g), load_npz(m / f"oracle/{g}/oracle-correspondences.npz")
    with patched(patches):
        res = BG.compute_epipolar(c, prod)
    save_npz(m / f"spherical/{g}/epipolar-result.npz", res)
    edit_json(m / f"spherical/{g}/spherical-summary.json", lambda d: d["inputs"]["correspondences"].update(
        sha256=sha256(m / f"oracle/{g}/oracle-correspondences.npz")))
    refreeze_geom(m)


def regen_planar(m: Path, ctx: Ctx, g: str, variant=None, rect=None) -> None:
    PL = _generator("ab1c_planar")
    c, prod = ctx.per("calib", g), load_npz(m / f"oracle/{g}/oracle-correspondences.npz")
    r = rect or PL.rectify(c)
    res = PL.triangulate(c, r, prod, variant)
    save_npz(m / f"planar/{g}/planar-result.npz", {**res, **{k: np.asarray(r[k]) for k in ("R1", "R2", "P1", "P2", "Q_full")},
                                                   "crop_xywh": np.asarray(r["crop_xywh"])})
    edit_json(m / f"planar/{g}/planar-summary.json", lambda d: d["inputs"]["correspondences"].update(
        sha256=sha256(m / f"oracle/{g}/oracle-correspondences.npz")))
    refreeze_geom(m)


def regen_oracle(m: Path, ctx: Ctx, g: str, patches) -> bool:
    BO = _generator("ab1b_oracle")
    with patched(patches):
        prod, summ = BO.compute_oracle(ctx.per("calib", g), ctx.per("ref", g))
    old = load_npz(m / f"oracle/{g}/oracle-correspondences.npz")
    if all(np.array_equal(old[k], prod[k]) for k in prod):
        return False
    save_npz(m / f"oracle/{g}/oracle-correspondences.npz", prod)
    edit_json(m / f"oracle/{g}/oracle-summary.json", lambda d: d.update(summ))
    edit_json(m / "oracle/correspondence-freeze.json", lambda d: d["files"].update({n: sha256(m / n) for n in d["files"]}))
    edit_json(m / "freeze/geometry-freeze.json", lambda d: d["files"].update(
        {f"oracle/{g}/oracle-correspondences.npz": sha256(m / f"oracle/{g}/oracle-correspondences.npz")}))
    regen_spherical(m, ctx, g)
    regen_planar(m, ctx, g)
    return True


@contextlib.contextmanager
def patched(patches):
    saved = []
    for mod, name, fn in patches:
        M = _generator(mod)
        saved.append((M, name, getattr(M, name)))
        setattr(M, name, fn(getattr(M, name)))
    try:
        yield
    finally:
        for M, name, orig in reversed(saved):
            setattr(M, name, orig)


def corruptions():
    G1, G2 = "gaze-1", "gaze-2"

    def kv(c, g, key="valid_epi", src="sph"):
        v = np.flatnonzero(c.per(src, g)[key])
        return int(v[len(v) // 2])

    def sel_edit(fn, freeze=True):
        def f(m, v, c):
            edit_json(m / "selection/selected-gazes.json", lambda d: fn(d, c))
            if freeze:
                refreeze_sel(m)
        return f

    def replace_gaze(pick):
        def fn(d, c):
            r, col = pick(c)
            yaw, pitch = -180.0 + 0.5 * (col + 0.5), 90.0 - 0.5 * (r + 0.5)
            d["gazes"][1].update(row=int(r), col=int(col), index=int(r * W_GRID + col), yaw_deg=yaw, pitch_deg=pitch,
                                 A=float(c.A[r, col]))
        return fn

    def other_eligible(c):
        e = own_mask()["eligible"]
        taken = {(g["row"], g["col"]) for g in c.sel}
        rr, cc = np.nonzero(e)
        k = next(i for i in range(len(rr)) if (rr[i], cc[i]) not in taken)
        return rr[k], cc[k]

    def outside_cone(c):
        return 180, 410    # yaw +25.25, pitch +0.25: outside the 20-degree cone

    def failing_leverage(c):
        m = own_mask()
        rr, cc = np.nonzero(m["cone"] & ~m["eligible"])
        return rr[0], cc[0]

    def regen_selection(d_min=D_MIN, tie=TIE, k=K_GAZES):
        def f(m, v, c):
            SEL = _generator("ab1c_select")
            mm = own_mask()
            picks, rounds = SEL.select_gazes(c.A, mm["dirs"], mm["eligible"], k, d_min, tie)
            gz = SEL.gaze_records(picks, rounds, c.A, {"alpha_forward_rad": mm["alpha"], "min_core_leverage_L": mm["lev_L"],
                                                       "min_core_leverage_R": mm["lev_R"]})
            edit_json(m / "selection/selected-gazes.json", lambda dd: dd.update(gazes=gz))
            edit_json(m / "selection/nms-rounds.json", lambda dd: dd.update(rounds=rounds))
            edit_json(m / "selection/selection-summary.json", lambda dd: dd.update(D_MIN_RAD=d_min, K=k))
            refreeze_sel(m)
        return f

    def altered_attention(m, v, c):
        a = c.A.copy()
        r, col = c.sel[0]["row"], c.sel[0]["col"]
        a[r, col] = a[r, col] - 10.0          # the frozen first pick loses its rank
        p = m.parent / "attention-altered.npz"
        np.savez_compressed(p, A=a)
        return {"attention_path": str(p)}

    def calib_edit(fn):
        def f(m, v, c):
            edit_json(m / f"observations/{G1}/acquisition/calibration.json", fn)
        return f

    def ipd(d):
        d["ipd_m"] = 0.064
        d["eyes"][0]["centre_h_m"] = [-0.032, 0.0, 0.0]
        d["eyes"][1]["centre_h_m"] = [0.032, 0.0, 0.0]

    def head_moved(d):
        d["head_origin_w_m"][0] = d["head_origin_w_m"][0] + 0.05

    def second_pair(m, v, c):
        src = m / f"observations/{G2}"
        dst = m / f"observations/{G2}-planar"
        shutil.copytree(src, dst, symlinks=True)
        with open(m / "process-log.jsonl", "a") as fh:
            fh.write(json.dumps({"command": "acquire", "status": "ok", "argv": ["x"], "code": {"dirty": False, "pushed": True},
                                 "blender": {"mode": "canonical", "argv": ["blender", "-b", "scenes/classroom/classroom_eye.blend"]}})
                     + "\n")

    def different_products(m, v, c):
        PL = _generator("ab1c_planar")
        prod = load_npz(m / f"oracle/{G1}/oracle-correspondences.npz")
        sub = {k: a[1:] for k, a in prod.items()}
        p = m / f"planar/{G1}/other-product.npz"
        np.savez_compressed(p, **sub)
        cc = c.per("calib", G1)
        r = PL.rectify(cc)
        res = PL.triangulate(cc, r, sub)
        save_npz(m / f"planar/{G1}/planar-result.npz", {**res, **{k: np.asarray(r[k]) for k in ("R1", "R2", "P1", "P2", "Q_full")},
                                                        "crop_xywh": np.asarray(r["crop_xywh"])})
        edit_json(m / f"planar/{G1}/planar-summary.json", lambda d: d["inputs"]["correspondences"].update(sha256=sha256(p)))
        refreeze_geom(m)

    def prod_edit(fn, regen=True):
        def f(m, v, c):
            edit_npz(m / f"oracle/{G1}/oracle-correspondences.npz", lambda z: fn(z, c))
            edit_json(m / "oracle/correspondence-freeze.json", lambda d: d["files"].update({n: sha256(m / n) for n in d["files"]}))
            edit_json(m / "freeze/geometry-freeze.json", lambda d: d["files"].update(
                {f"oracle/{G1}/oracle-correspondences.npz": sha256(m / f"oracle/{G1}/oracle-correspondences.npz")}))
            if regen:
                regen_spherical(m, c, G1)
                regen_planar(m, c, G1)
            else:
                for s in ("spherical", "planar"):
                    edit_json(m / f"{s}/{G1}/{s}-summary.json", lambda d: d["inputs"]["correspondences"].update(
                        sha256=sha256(m / f"oracle/{G1}/oracle-correspondences.npz")))
                refreeze_geom(m)
        return f

    def oracle_patch(name, fn):
        def f(m, v, c):
            if not any(regen_oracle(m, c, g, [("ab1b_oracle", name, fn)]) for g in GAZES):
                return {"not_applicable": f"the patched oracle rule {name} leaves every canonical product unchanged"}
        return f

    def planar_variant(variant):
        return lambda m, v, c: regen_planar(m, c, G1, variant)

    def planar_flags(m, v, c):
        import cv2
        PL = _generator("ab1c_planar")
        cc = c.per("calib", G1)
        r = dict(PL.rectify(cc))
        kl, kr = (np.asarray(e["K"], float) for e in cc["eyes"])
        rr, t = _generator("fsg_geometry").relative_pose(cc)
        r1, r2, p1, p2, q, _a, _b = cv2.stereoRectify(kl, np.zeros(5), kr, np.zeros(5), (RAW, RAW), rr, t, flags=0, alpha=0,
                                                       newImageSize=(RAW, RAW))
        r.update(R1=r1, R2=r2, P1=p1, P2=p2, Q_full=q)
        regen_planar(m, c, G1, None, r)

    def support_edit(m, v, c):
        edit_json(m / f"planar/{G1}/planar-support.json", lambda d: d["eyes"]["L"].update(
            rectified_core_pixels_from_nominal_raw_core=d["eyes"]["L"]["rectified_core_pixels_from_nominal_raw_core"] - 1000))
        refreeze_geom(m)

    def reads_reference(kind):
        def f(m, v, c):
            p = str((m / f"observations/{G1}/evaluation_only/reference-observation.npz").resolve())

            def fn(d):
                d["events"].append({"event": "open", "path": p, "kind": "data-read", "allowed": True})
                d["data_reads"].append(p)
            edit_json(m / f"{kind}/{G1}/{kind}-opened-files.json", fn)
            refreeze_geom(m)
        return f

    def truth_into(kind):
        def f(m, v, c):
            pt = c.ptruth(G1)
            key, vk, rel = (("P_epi", "valid_epi", f"spherical/{G1}/epipolar-result.npz") if kind == "spherical"
                            else ("P_planar", "valid_planar", f"planar/{G1}/planar-result.npz"))
            vv = c.per("sph" if kind == "spherical" else "pla", G1)[vk].astype(bool)
            edit_npz(m / rel, lambda z: z[key].__setitem__(vv, pt[vv]))
            reads_reference(kind)(m, v, c)
        return f

    def bad_phi(orig):
        def fn(d):
            t, p, s = orig(d)
            return t, -p, s
        return fn

    def bad_theta(orig):
        def fn(d):
            t, p, s = orig(d)
            d = np.asarray(d, np.float64)
            return np.arctan2(np.hypot(d[..., 0], d[..., 1]), -d[..., 2]), p, s
        return fn

    def flip_baseline(orig):
        def fn(cc):
            b, o_l, o_r = orig(cc)
            return -b, o_l, o_r
        return fn

    def geom_edit_unfrozen(m, v, c):
        k = kv(c, G1)
        edit_npz(m / f"spherical/{G1}/epipolar-result.npz", lambda z: z["P_epi"].__setitem__((k, 0), z["P_epi"][k, 0] + 1e-3))

    def early_ref(m, v, c):
        def fn(d):
            ev = d["ordered_data_events"]
            t = next(p for p in ev if str(p).endswith("reference-observation.npz"))
            ev.remove(t)
            ev.insert(0, t)
        edit_json(m / "evaluation/evaluation-opened-files.json", fn)

    def cmp_stat(m, v, c):
        edit_json(m / "comparison/comparison-summary.json", lambda d: d["per_gaze"][G1]["planar_minus_spherical_m"].update(
            median=d["per_gaze"][G1]["planar_minus_spherical_m"]["median"] * 1.5 + 1e-12))

    def pixel(m, v, c):
        from PIL import Image
        p = v / "overview.png"
        img = Image.open(p.resolve()).convert("RGB")
        img.putpixel((3, 3), (255, 0, 0))
        p.unlink()
        img.save(p)

    def badge(m, v, c):
        edit_json(v / "visuals-manifest.json", lambda d: d["figures"]["truth-error.png"].update(badges=[DER]))

    def log(entry):
        def f(m, v, c):
            with open(m / "process-log.jsonl", "a") as fh:
                fh.write(json.dumps(entry) + "\n")
        return f

    def changed(extra):
        return lambda m, v, c: {"changed_files": c.changed_files + [extra]}

    def evr_edit(key, delta):
        def f(m, v, c):
            k = kv(c, G1)
            edit_npz(m / f"evaluation/{G1}/evaluation-result.npz", lambda z: z[key].__setitem__(k, z[key][k] + delta))
        return f

    def exr_record(m, v, c):
        edit_json(m / f"observations/{G1}/acquisition/acquisition.json", lambda d: d["exr_channels_lr"]["L"].append(
            "interior.Depth.Z"))

    def plan_edit(m, v, c):
        edit_json(m / f"plan/{G1}/planned-calibration.json", lambda d: d["eyes"][1]["R_hc"][0].__setitem__(
            0, d["eyes"][1]["R_hc"][0][0] + 1e-6))

    def mask_edit(m, v, c):
        mm = c.smask
        r, col = np.argwhere(mm["cone"])[0]
        edit_npz(m / "selection/safe-forward-mask.npz", lambda z: z["min_core_leverage_L"].__setitem__((r, col), 0.5))
        refreeze_sel(m)

    def order(m, v, c):
        lines = (m / "process-log.jsonl").read_text().splitlines()
        i = next(k for k, ln in enumerate(lines) if json.loads(ln)["command"] == "compare")
        j_ = next(k for k, ln in enumerate(lines) if json.loads(ln)["command"] == "evaluate")
        lines[i], lines[j_] = lines[j_], lines[i]
        (m / "process-log.jsonl").write_text("\n".join(lines) + "\n")

    run_cmd = ["tools/active_bootstrap/ab1c_run.py"]
    return [
        # selection
        ("hand-picked gaze (another eligible cell substituted)", ("07", "08"), sel_edit(replace_gaze(other_eligible))),
        ("a gaze outside the forward cone", ("03", "07"), sel_edit(replace_gaze(outside_cone))),
        ("a gaze violating the min-core leverage", ("04", "07"), sel_edit(replace_gaze(failing_leverage))),
        ("K changed (one gaze dropped)", ("06",), sel_edit(lambda d, c: d["gazes"].pop())),
        ("D_MIN changed (halved; regenerated)", ("06", "07"), regen_selection(d_min=D_MIN / 2)),
        ("tie rule changed (tie window 0.5; regenerated)", ("07",), regen_selection(tie=0.5)),
        ("frozen RGB attention ordering altered", ("02", "07"), altered_attention),
        ("a leverage value altered in the mask", ("04",), mask_edit),
        ("selection opened the head-pose record", ("09",),
         lambda m, v, c: edit_json(m / "selection/selection-opened-files.json", lambda d: d["data_reads"].append(str(HEAD_POSE[0])))),
        # observation
        ("a selected gaze changed after the freeze", ("10",), sel_edit(replace_gaze(other_eligible), freeze=False)),
        ("a second pair rendered for one representation", ("12", "40"), second_pair),
        ("calibration / IPD altered in one observation", ("13",), calib_edit(ipd)),
        ("head moved in one observation (head origin shifted)", ("13", "39"), calib_edit(head_moved)),
        ("a planned calibration altered", ("11",), plan_edit),
        ("an EXR pass (Depth) recorded", ("14",), exr_record),
        # correspondence
        ("different products for planar and spherical", ("20",), different_products),
        ("uv_R rounded (regenerated)", ("15", "16"), prod_edit(lambda z, c: z.__setitem__("uv_R", np.rint(z["uv_R"])))),
        ("right match restricted to the nominal right core", ("15",),
         oracle_patch("inside_raster", lambda orig: lambda cc, uv: (uv[..., 0] >= ORIGIN) & (uv[..., 0] <= ORIGIN + CORE - 1)
                      & (uv[..., 1] >= ORIGIN) & (uv[..., 1] <= ORIGIN + CORE - 1))),
        ("same-instance visibility removed", ("15",),
         oracle_patch("same_instance", lambda orig: lambda ids, vi, ui, left: np.ones_like(left, bool))),
        ("Position added to the product", ("17",), prod_edit(lambda z, c: z.__setitem__("xyz_h", c.ptruth(G1)), regen=False)),
        ("instance id added to the product", ("17",),
         prod_edit(lambda z, c: z.__setitem__("instance_id", np.zeros(len(z["uv_L"]), np.int32)), regen=False)),
        ("depth added to the product", ("17",),
         prod_edit(lambda z, c: z.__setitem__("depth_m", np.ones(len(z["uv_L"]))), regen=False)),
        ("correspondence product modified after its freeze", ("18",),
         lambda m, v, c: edit_npz(m / f"oracle/{G1}/oracle-correspondences.npz",
                                  lambda z: z["uv_R"].__setitem__((0, 0), z["uv_R"][0, 0] + 1e-3))),
        # planar
        ("planar eye order altered (regenerated)", ("26",), planar_variant({"swap_eyes": True})),
        ("planar rectification convention altered (flags 0, alpha 0)", ("24",), planar_flags),
        ("planar R1 convention transposed (regenerated)", ("25", "26"), planar_variant({"r1_transposed": True})),
        ("fixed central support diagnostic changed", ("27",), support_edit),
        ("truth injected into the planar triangulation", ("19", "26"), truth_into("planar")),
        # spherical
        ("spherical phi sign flipped (regenerated)", ("21", "22"),
         lambda m, v, c: regen_spherical(m, c, G1, [("ab1b_geometry", "theta_phi", bad_phi)])),
        ("spherical theta from -Z instead of +X (regenerated)", ("21",),
         lambda m, v, c: regen_spherical(m, c, G1, [("ab1b_geometry", "theta_phi", bad_theta)])),
        ("spherical baseline direction flipped (regenerated)", ("22",),
         lambda m, v, c: regen_spherical(m, c, G1, [("ab1b_geometry", "baseline", flip_baseline)])),
        ("truth injected into the spherical triangulation", ("19", "22"), truth_into("spherical")),
        ("spherical stage opened Position", ("19",), reads_reference("spherical")),
        # freeze / evaluation
        ("geometry product edited after its freeze", ("30", "32"), geom_edit_unfrozen),
        ("Position opened before the geometry freeze", ("31",), early_ref),
        ("one direct-comparison statistic altered", ("29",), cmp_stat),
        ("P_truth altered in the evaluation", ("33",), evr_edit("P_truth", 1e-3)),
        ("a truth-error statistic altered", ("33",), lambda m, v, c: edit_json(
            m / "evaluation/evaluation-summary.json", lambda d: d["per_gaze"][G1]["planar_vs_truth"]["error_3d_m"].update(
                median=d["per_gaze"][G1]["planar_vs_truth"]["error_3d_m"]["median"] * 1.1))),
        ("a reprojection statistic altered", ("34",), lambda m, v, c: edit_json(
            m / "evaluation/evaluation-summary.json", lambda d: d["per_gaze"][G1]["spherical_reprojection_px"]["left"].update(
                median=d["per_gaze"][G1]["spherical_reprojection_px"]["left"]["median"] + 0.01))),
        ("a spherical summary distribution altered", ("35",), lambda m, v, c: (edit_json(
            m / f"spherical/{G1}/spherical-summary.json", lambda d: d["distributions"]["kappa"].update(
                median=d["distributions"]["kappa"]["median"] * 1.01)), refreeze_geom(m))[1]),
        ("kappa altered", ("23",), lambda m, v, c: (edit_npz(m / f"spherical/{G1}/epipolar-result.npz", lambda z: z["kappa"].__setitem__(
            kv(c, G1), z["kappa"][kv(c, G1)] * 1.01)), refreeze_geom(m))[1]),
        ("common mask altered", ("28",), lambda m, v, c: (edit_npz(m / f"comparison/{G1}/comparison-result.npz",
                                                                  lambda z: z["common"].__setitem__(kv(c, G1), False)), None)[1]),
        # visual
        ("a visual pixel altered", ("36",), pixel),
        ("a truth badge altered", ("37",), badge),
        # records, code, order
        ("SGBM / natural matcher in a generator", ("38",), lambda m, v, c: {"static_extra": {
            "ab1c_planar.py": "import cv2\n_m = cv2.StereoSGBM_create\n"}}),
        ("controller command in the process log", ("39",), log({"command": "controller02", "status": "ok", "argv": [
            "fov3d/experiments/classroom_oracle/controller02.py"], "code": {"dirty": False, "pushed": True}})),
        ("accepted FSG source modified", ("41",), changed("tools/fsg_stereo.py")),
        ("accepted AB1b source modified", ("41",), changed("tools/active_bootstrap/ab1b_geometry.py")),
        ("an undeclared tracked file changed", ("42",), changed("README.md")),
        ("a synthetic known-answer case failed", ("43",),
         lambda m, v, c: edit_json(m / "synthetic/synthetic-report.json", lambda d: d["cases"][0].update(ok=False))),
        ("oracle attrition altered", ("44",), lambda m, v, c: edit_json(
            m / f"oracle/{G1}/oracle-summary.json", lambda d: d["attrition"][1].update(remaining=d["attrition"][1]["remaining"] + 1))),
        ("run order altered (evaluate before compare)", ("45",), order),
        ("a canonical step run twice", ("45",), log({"command": "oracle", "status": "ok", "argv": run_cmd + ["oracle"],
                                                     "code": {"dirty": False, "pushed": True}})),
    ]


def corruption_suite(run: Path, vis: Path, base: Ctx) -> tuple[int, int, list]:
    caught = total = 0
    results = []
    with tempfile.TemporaryDirectory(prefix="ab1c-corrupt-") as td:   # null probe: an unmodified mirror must pass
        m, v = mirror(run, vis, Path(td))
        ctx = Ctx(m, v)
        ctx.__dict__["changed_files"] = base.changed_files
        with contextlib.redirect_stdout(io.StringIO()):
            null_failed = sorted(r["check"] for r in run_checks(ctx, quiet=True) if not r["ok"])
    print(f"{PREFIX} corruption null probe (unmodified mirror): failed {null_failed}")
    results.append({"name": "null probe (unmodified mirror)", "failed": null_failed})
    if null_failed:
        return 0, -1, results
    for name, targets, fn in corruptions():
        with tempfile.TemporaryDirectory(prefix="ab1c-corrupt-") as td:
            m, v = mirror(run, vis, Path(td))
            probe = Ctx(m, v)
            probe.__dict__["changed_files"] = base.changed_files
            with contextlib.redirect_stdout(io.StringIO()):
                overrides = fn(m, v, probe) or {}
            if "not_applicable" in overrides:
                print(f"{PREFIX} corruption N/A {list(targets)} {name}: {overrides['not_applicable']}")
                results.append({"name": name, "targets": list(targets), "not_applicable": overrides["not_applicable"]})
                continue
            total += 1
            ctx = Ctx(m, v)
            ctx.__dict__["changed_files"] = overrides.pop("changed_files", base.changed_files)
            patches = overrides.pop("patch", [])
            ctx.overrides = overrides
            with contextlib.redirect_stdout(io.StringIO()), patched(patches):
                res = run_checks(ctx, quiet=True)
            failed = sorted(r["check"] for r in res if not r["ok"])
            hit = any(t in failed for t in targets)
            caught += hit
            results.append({"name": name, "targets": list(targets), "caught": hit, "failed": failed})
            print(f"{PREFIX} corruption {'CAUGHT' if hit else 'MISSED'} {list(targets)} {name} (failed: {failed})")
    return caught, total, results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--visuals", required=True, type=Path)
    ap.add_argument("--stage", choices=("selection", "full"), default="full")
    ap.add_argument("--corruptions", action="store_true")
    ap.add_argument("--write-summary", action="store_true")
    a = ap.parse_args(argv)
    run, vis = a.run.resolve(), a.visuals.resolve()
    base = Ctx(run, vis)
    res = run_checks(base, stage=a.stage)
    npass = sum(r["ok"] for r in res)
    ok = npass == len(res)
    print(f"{PREFIX} SUMMARY stage={a.stage} checked={len(res)} failed={len(res) - npass}")
    if a.stage == "selection":
        if ok:
            print(f"{PREFIX} ACTIVE_BOOTSTRAP1C_SELECTION_CHECKS_PASS")
        if a.write_summary:
            (run / "selection/selection-check.json").write_text(json.dumps({
                "schema": "AB1c-selection-check-v1", "passed": ok, "checks": res, "code": git("rev-parse", "HEAD").strip(),
                "selection_freeze_sha256": sha256(run / "selection/safe-forward-freeze.json")}, indent=1, sort_keys=True) + "\n")
        return 0 if ok else 1
    if ok:
        print(f"{PREFIX} ACTIVE_BOOTSTRAP1C_CHECKS_PASS")
    out = {"schema": "AB1c-check-summary-v1", "checks": res, "passed": ok, "code": git("rev-parse", "HEAD").strip()}
    if a.corruptions:
        caught, total, results = corruption_suite(run, vis, base)
        out["corruptions"] = {"caught": caught, "total": total, "baseline_passing": ok, "results": results}
        print(f"{PREFIX} CORRUPTIONS caught={caught}/{total}" + ("" if ok else " (NOT PROBATIVE: baseline failing)"))
        if ok and caught == total:
            print(f"{PREFIX} ACTIVE_BOOTSTRAP1C_MUTATIONS_CAUGHT")
        ok = ok and caught == total
    if a.write_summary:
        (run / "check-summary.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
