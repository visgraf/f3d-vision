"""Active Bootstrap-1d3: the checker's independent primitives (contract sections 9, 10 and 21).

Used by ``check_ab1d3.py`` on the canonical run and by the preflight known answers on synthetic data ("the checker
detects").  Everything here keeps its own literal constants and its own assembly of the pipeline:

- ``own_sgbm``: its own relative pose, its own cv2.stereoRectify / initUndistortRectifyMap / remap calls with literal
  flags, its own linear -> u8 transfer, its own StereoSGBM objects built from literal parameters, its own bounded
  photometric refinement (written out), its own LR / texture / z / ROI / support terms;
- ``own_adapt``: its own raw -> rectified map (column form), footprint, bilinear weights and rectified -> raw inverse
  (a linear solve, not an inverse matrix);
- ``audit_calls`` / ``audit_summary`` / ``audit_record``: the frozen configuration against what was recorded and what
  the record contains.

It never imports the AB1d3 run, SGBM or adapter modules.
"""
from __future__ import annotations

import math

import cv2
import numpy as np

# ------------------------------------------------------------------ literals (contract sections 5, 6, 8)
RAW, CORE, ORIGIN = 640, 256, 192
LIT_SGBM = {"minDisparity": 0, "numDisparities": 112, "blockSize": 5, "P1": 200, "P2": 800, "disp12MaxDiff": -1,
            "preFilterCap": 31, "uniquenessRatio": 10, "speckleWindowSize": 0, "speckleRange": 1, "mode": 2}
LIT_GETTERS = {"getMode": 2, "getBlockSize": 5, "getP1": 200, "getP2": 800, "getPreFilterCap": 31,
               "getUniquenessRatio": 10, "getDisp12MaxDiff": -1, "getSpeckleWindowSize": 0, "getSpeckleRange": 1,
               "getNumDisparities": 112}
LIT_MIN_DISP = (0, -111)
LIT_Z = (0.75, 4.5)
LIT_LR = 1.0
LIT_STD = 0.5
LIT_REFINE = (3, 0.5, 0.75)
LIT_ZERO_DISPARITY = 1024
LIT_TERMS = ("term_sgbm_left", "term_right_valid", "term_support_left", "term_inside_raster", "term_lr", "term_texture",
             "term_finite", "term_z_range", "term_roi")
LIT_LUMA = (0.2126, 0.7152, 0.0722)
Z_EPS = 1e-12


def own_u8(rgb) -> np.ndarray:
    a = np.clip(np.asarray(rgb, float), 0.0, 1.0)
    a = np.where(a <= 0.0031308, 12.92 * a, 1.055 * np.power(a, 1 / 2.4) - 0.055)
    return np.rint(255 * a).astype(np.uint8)


def own_rectify(c: dict) -> dict:
    w, h = c["image_size_wh"]
    el, er = c["eyes"]
    kl, kr = np.asarray(el["K"], float), np.asarray(er["K"], float)
    rl, rr = np.asarray(el["R_hc"], float), np.asarray(er["R_hc"], float)
    r = rr.T @ rl
    t = rr.T @ (np.asarray(el["centre_h_m"], float) - np.asarray(er["centre_h_m"], float))
    r1, r2, p1, p2, q, roi1, roi2 = cv2.stereoRectify(kl, np.zeros(5), kr, np.zeros(5), (w, h), r, t,
                                                      flags=LIT_ZERO_DISPARITY, alpha=-1, newImageSize=(w, h))
    maps = {}
    for side, k, rr_, pp in (("L", kl, r1, p1), ("R", kr, r2, p2)):
        mx, my = cv2.initUndistortRectifyMap(k, np.zeros(5), rr_, pp[:, :3], (w, h), cv2.CV_32FC1)
        maps[side] = (mx, my)
    z_min = LIT_Z[0]
    nd = int(math.ceil((int(math.ceil(abs(p2[0, 3]) / z_min)) + 4) / 16) * 16)
    roi = cv2.getValidDisparityROI(tuple(roi1), tuple(roi2), 0, nd, LIT_SGBM["blockSize"])
    return {"R1": r1, "R2": r2, "P1": p1, "P2": p2, "Q": q, "maps": maps, "nd": nd, "roi": tuple(int(a) for a in roi),
            "roi1": roi1, "roi2": roi2}


def own_support(mx, my, w, h) -> np.ndarray:
    a = (mx >= 1) & (mx < w - 2) & (my >= 1) & (my < h - 2)
    return cv2.erode(a.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)


def own_refine(left, right, initial, supported, params=LIT_REFINE) -> np.ndarray:
    """The bounded photometric refinement, written out with literal constants (3 updates, |step| <= 0.5, total 0.75).
    ``params`` is changed only by the corruption suite (a mutated refinement)."""
    iters, step_max, total = params
    luma = np.array(LIT_LUMA, np.float32)
    lg = np.asarray(left, np.float32) @ luma
    rg = np.asarray(right, np.float32) @ luma
    grad = cv2.Sobel(rg, cv2.CV_32F, 1, 0, ksize=3, scale=1 / 8)
    hh, ww = lg.shape
    vv, uu = np.mgrid[:hh, :ww].astype(np.float32)
    d = initial.copy()

    def box(a):
        return cv2.boxFilter(a, -1, (5, 5), normalize=True, borderType=cv2.BORDER_REFLECT)
    for _ in range(iters):
        x = uu - d
        rw = cv2.remap(rg, x, vv, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        gw = cv2.remap(grad, x, vv, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        res = rw - lg
        gm, rm = box(gw), box(res)
        num = box(gw * res) - gm * rm
        den = np.maximum(box(gw * gw) - gm * gm, 0.0)
        step = np.divide(num, den + 1e-9, out=np.zeros_like(d), where=den > 1e-8)
        d = np.where(supported, np.clip(d + np.clip(step, -step_max, step_max), initial - total, initial + total),
                     initial).astype(np.float32)
    return d


def own_sgbm(c: dict, obs: dict) -> dict:
    """The whole frozen matcher re-assembled from literals; full 640 x 640 arrays."""
    w, h = c["image_size_wh"]
    r = own_rectify(c)
    col, gray, sup = {}, {}, {}
    for side in ("L", "R"):
        mx, my = r["maps"][side]
        col[side] = cv2.remap(np.asarray(obs["rgb_" + side], np.float32), mx, my, cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        gray[side] = cv2.cvtColor(own_u8(col[side]), cv2.COLOR_RGB2GRAY)
        sup[side] = own_support(mx, my, w, h)
    nd = r["nd"]
    p = dict(LIT_SGBM, numDisparities=nd)
    dl_raw = cv2.StereoSGBM_create(**p).compute(gray["L"], gray["R"])
    pr = dict(p, minDisparity=-(nd - 1))
    dr_raw = cv2.StereoSGBM_create(**pr).compute(gray["R"], gray["L"])
    vl, vr = dl_raw > -16, dr_raw > (-(nd - 1) - 1) * 16
    disc = dl_raw.astype(np.float32) / 16.0
    dl = own_refine(col["L"], col["R"], disc, vl & sup["L"])
    dr = own_refine(col["R"], col["L"], dr_raw.astype(np.float32) / 16.0, vr & sup["R"])
    vgrid, ugrid = np.mgrid[:h, :w].astype(float)
    ur = ugrid - dl
    xr = ur.astype(np.float32)
    v32 = vgrid.astype(np.float32)
    dr_at = cv2.remap(dr, xr, v32, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    vr_at = cv2.remap((vr & sup["R"]).astype(np.float32), xr, v32, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                      borderValue=0) > .999
    lr = np.abs(dl + dr_at)
    m = gray["L"].astype(np.float32)
    std = np.sqrt(np.maximum(cv2.boxFilter(m * m, -1, (5, 5)) - cv2.boxFilter(m, -1, (5, 5)) ** 2, 0.0))
    q = np.asarray(r["Q"], float)
    hom = np.stack([ugrid, vgrid, dl, np.ones_like(ugrid)], -1) @ q.T
    with np.errstate(divide="ignore", invalid="ignore"):
        xyz = hom[..., :3] / hom[..., 3:4]
    z = xyz[..., 2]
    gx, gy, gw, gh = r["roi"]
    roi = np.zeros((h, w), bool)
    roi[gy:gy + gh, gx:gx + gw] = True
    with np.errstate(invalid="ignore"):
        terms = {"term_sgbm_left": vl, "term_right_valid": vr_at, "term_support_left": sup["L"],
                 "term_inside_raster": (ur >= 0) & (ur < w - 1), "term_lr": lr <= LIT_LR, "term_texture": std >= LIT_STD,
                 "term_finite": np.isfinite(xyz).all(-1), "term_z_range": (z >= LIT_Z[0]) & (z <= LIT_Z[1]),
                 "term_roi": roi}
    valid = np.ones((h, w), bool)
    for t in LIT_TERMS:
        valid &= terms[t]
    return {"rect": r, "disc": disc, "dl": dl, "dl_raw": dl_raw, "dr_raw": dr_raw, "lr": lr, "std": std, "z": z,
            "valid": valid, "gray": gray, **terms}


# ------------------------------------------------------------------ the raw-core adapter, independently
def own_raw_to_rect(k, r, p, uv) -> tuple[np.ndarray, np.ndarray]:
    uv = np.asarray(uv, float)
    hom = np.vstack([uv[:, 0], uv[:, 1], np.ones(len(uv))])            # 3 x n columns
    x = np.asarray(r, float) @ np.linalg.solve(np.asarray(k, float), hom)
    y = np.asarray(p, float)[:, :3] @ x
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.stack([y[0] / x[2], y[1] / x[2]], -1), x[2]


def own_rect_to_raw(k, r, k_rect, uvr) -> tuple[np.ndarray, np.ndarray]:
    uvr = np.asarray(uvr, float)
    hom = np.vstack([uvr[:, 0], uvr[:, 1], np.ones(len(uvr))])
    x = np.asarray(r, float).T @ np.linalg.solve(np.asarray(k_rect, float), hom)
    y = np.asarray(k, float) @ x
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.stack([y[0] / y[2], y[1] / y[2]], -1), x[2]


def own_adapt(c: dict, r1, r2, p1, p2, disparity, valid) -> dict:
    w, h = c["image_size_wh"]
    kl, kr = (np.asarray(e["K"], float) for e in c["eyes"])
    idx = np.arange(CORE * CORE)
    rows, cols = idx // CORE, idx % CORE
    uv_l = np.stack([cols + ORIGIN, rows + ORIGIN], -1).astype(float)
    uvr, wl = own_raw_to_rect(kl, r1, p1, uv_l)
    fin = np.isfinite(uvr).all(-1)
    x0 = np.floor(np.where(fin, uvr[:, 0], -5)).astype(int)
    y0 = np.floor(np.where(fin, uvr[:, 1], -5)).astype(int)
    ok = fin & (wl > Z_EPS) & (x0 >= 0) & (x0 <= w - 2) & (y0 >= 0) & (y0 <= h - 2)
    xs, ys = np.where(ok, x0, 0), np.where(ok, y0, 0)
    vmask = np.asarray(valid, bool)
    allv = ok & vmask[ys, xs] & vmask[ys, xs + 1] & vmask[ys + 1, xs] & vmask[ys + 1, xs + 1]
    a, b = uvr[:, 0] - xs, uvr[:, 1] - ys
    D = np.asarray(disparity, float)
    d = (D[ys, xs] * (1 - a) * (1 - b) + D[ys, xs + 1] * a * (1 - b) + D[ys + 1, xs] * (1 - a) * b
         + D[ys + 1, xs + 1] * a * b)
    d = np.where(allv, d, np.nan)
    uvr_r = np.stack([uvr[:, 0] - d, uvr[:, 1]], -1)
    uv_r, zr = own_rect_to_raw(kr, r2, np.asarray(p2, float)[:, :3], uvr_r)
    with np.errstate(invalid="ignore"):
        good = allv & np.isfinite(uv_r).all(-1) & (zr > Z_EPS) & (uv_r[:, 0] >= 0) & (uv_r[:, 0] <= w - 1) \
            & (uv_r[:, 1] >= 0) & (uv_r[:, 1] <= h - 1)
    return {"valid": good, "uv_R": uv_r, "uvrect_L": uvr, "d": d, "footprint_valid": allv, "rectifiable": ok}


# ------------------------------------------------------------------ audits (the frozen configuration)
def audit_calls(calls: dict) -> list[str]:
    bad = []
    c = calls.get("calls", {})
    sg = c.get("StereoSGBM_create", [])
    if len(sg) != 2:
        bad.append(f"SGBM objects created: {len(sg)} != 2")
    for k, e in enumerate(sg):
        g = e["getters"]
        for name, want in LIT_GETTERS.items():
            if g.get(name) != want:
                bad.append(f"SGBM[{k}] {name} = {g.get(name)} != {want}")
        if k < 2 and g.get("getMinDisparity") != LIT_MIN_DISP[k]:
            bad.append(f"SGBM[{k}] minDisparity = {g.get('getMinDisparity')} != {LIT_MIN_DISP[k]}")
        cp = e.get("compute", [])
        if len(cp) != 1 or cp[0]["left_shape"] != [RAW, RAW] or cp[0]["right_shape"] != [RAW, RAW] \
                or cp[0]["left_dtype"] != "uint8":
            bad.append(f"SGBM[{k}] did not match exactly one full 640 x 640 uint8 pair: {cp}")
    if len(sg) == 2 and sg[0]["compute"] and sg[1]["compute"] and (
            sg[0]["compute"][0]["left_sha256"] != sg[1]["compute"][0]["right_sha256"]
            or sg[0]["compute"][0]["right_sha256"] != sg[1]["compute"][0]["left_sha256"]):
        bad.append("the right -> left SGBM did not match the same pair, swapped")
    rect = c.get("stereoRectify", [])
    if len(rect) != 1 or rect[0]["flags"] != LIT_ZERO_DISPARITY or rect[0]["alpha"] != -1.0 \
            or rect[0]["newImageSize"] != [RAW, RAW]:
        bad.append(f"rectification call: {rect}")
    if calls.get("tripwire_calls"):
        bad.append(f"tripwires: {calls['tripwire_calls']}")
    return bad


def audit_summary(summ: dict) -> list[str]:
    m = summ.get("matcher", {})
    bad = []
    if m.get("variant"):
        bad.append(f"compute_natural variant {m.get('variant')}")
    for k, want in (("block_size_used", 5), ("uniqueness_ratio_used", 10), ("num_disparities", 112), ("min_disparity", 0),
                    ("lr_tolerance_px", LIT_LR), ("minimum_local_std_u8", LIT_STD)):
        if m.get(k) != want:
            bad.append(f"summary {k} = {m.get(k)} != {want}")
    if m.get("z_rect_m") != list(LIT_Z):
        bad.append(f"summary z_rect_m = {m.get('z_rect_m')}")
    if m.get("identity_guard") is not None:
        bad.append("identity guard present")
    return bad


def audit_record(c: dict, obs: dict, rec: dict, own: dict | None = None) -> tuple[list[str], dict]:
    """Recompute the whole frozen matcher independently and compare with the record (full raster)."""
    own = own or own_sgbm(c, obs)
    bad, det = [], {}
    if list(c["depth_search_z_rect_m"]) != list(LIT_Z):
        bad.append(f"calibration z interval {c['depth_search_z_rect_m']}")
    if own["rect"]["nd"] != LIT_SGBM["numDisparities"]:
        bad.append(f"own numDisparities {own['rect']['nd']}")
    if int(rec["num_disparities"]) != own["rect"]["nd"] or int(rec["min_disparity"]) != 0:
        bad.append(f"record disparity range {int(rec['min_disparity'])} + {int(rec['num_disparities'])}")
    for k, kk in (("R1", "R1"), ("R2", "R2"), ("P1", "P1"), ("P2", "P2"), ("Q_full", "Q")):
        if not np.allclose(np.asarray(rec[k], float), own["rect"][kk], rtol=0, atol=1e-12):
            bad.append(f"rectification {k} differs")
    if [int(a) for a in rec["valid_disparity_roi"]] != list(own["rect"]["roi"]):
        bad.append("valid-disparity ROI differs")
    det["discrete_equal"] = bool(np.array_equal(rec["disparity_sgbm_px"], own["disc"]))
    det["refined_max_abs_diff"] = float(np.max(np.abs(rec["disparity_px"].astype(float) - own["dl"].astype(float))))
    if not det["discrete_equal"]:
        bad.append("SGBM discrete disparity differs from the literal-configuration recomputation")
    if det["refined_max_abs_diff"] > 1e-5:
        bad.append(f"refined disparity differs: {det['refined_max_abs_diff']:.3g} px")
    det["term_mismatch"] = {t: int((np.asarray(rec[t], bool) != own[t]).sum()) for t in LIT_TERMS}
    for t, n in det["term_mismatch"].items():
        if n:
            bad.append(f"{t}: {n} pixels differ")
    det["valid_mismatch"] = int((np.asarray(rec["valid"], bool) != own["valid"]).sum())
    if det["valid_mismatch"]:
        bad.append(f"valid: {det['valid_mismatch']} pixels differ")
    andv = np.ones_like(own["valid"])
    for t in LIT_TERMS:
        andv &= np.asarray(rec[t], bool)
    if not np.array_equal(andv, np.asarray(rec["valid"], bool)):
        bad.append("record valid != AND of its own terms")
    sup = np.asarray(rec["term_sgbm_left"], bool) & np.asarray(rec["term_support_left"], bool)
    delta = rec["disparity_px"].astype(float) - rec["disparity_sgbm_px"].astype(float)
    det["refinement_max_abs"] = float(np.max(np.abs(delta[sup]))) if sup.any() else 0.0
    if det["refinement_max_abs"] > LIT_REFINE[2] + 1e-5 or np.any(delta[~sup] != 0):
        bad.append(f"refinement bound violated: {det['refinement_max_abs']}")
    det["lr_max_abs_diff_valid"] = float(np.max(np.abs(rec["lr_error_px"] - own["lr"])[own["valid"]])) \
        if own["valid"].any() else 0.0
    det["std_max_abs_diff"] = float(np.max(np.abs(rec["left_gray_std"] - own["std"])))
    if det["std_max_abs_diff"] > 1e-3:
        bad.append(f"texture std differs: {det['std_max_abs_diff']}")
    return bad, det
