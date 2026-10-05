"""Active Bootstrap-1d: synthetic known answers for the frozen matcher (contract sections 24 and 33).

Analytic scenes only (no Blender, no Classroom): a texture T defined on LEFT view directions, and a right image in
which every left direction (theta_L, phi_L) is seen at (theta_L + dtheta(phi_L), phi_L), a physical surface of known
binocular parallax.  The true line coordinate of every left pixel follows from the contract's own geometry.  The
tolerances are software / numerical; they are not scientific thresholds.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent / "natural_bootstrap"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ab1b_geometry as BG  # noqa: E402  (accepted, read-only)
import ab1d_match as M  # noqa: E402
import ab1d_spec as SP  # noqa: E402
import check_ab1d as CK  # noqa: E402  (the checker's independent matcher)
import fsg_geometry as FG  # noqa: E402  (accepted, read-only)
import fsg_stereo as FS  # noqa: E402  (accepted, read-only)
from nb1a_guard import OpenGuard  # noqa: E402  (accepted, read-only)

N_WAVES = 12


# ------------------------------------------------------------------ scenes
def calibration() -> dict:
    return FG.make_calibration("full", *SP.SYN_GAZE, SP.SYN_VERGENCE_M, SP.IPD_M, tangent_frame="baseline_projected")


class Texture:
    """128 + amp * sum of N_WAVES sinusoids of seeded wave-vectors on directions (angular wavelengths lo..hi px)."""

    def __init__(self, lo: float, hi: float, dlt: float, seed: int = SP.SYN_SEED, amp: float = 9.0) -> None:
        rng = np.random.default_rng(seed)
        lam = rng.uniform(lo, hi, N_WAVES)
        wv = rng.normal(size=(N_WAVES, 3))
        wv /= np.linalg.norm(wv, axis=1, keepdims=True)
        self.om = wv * (2 * np.pi / (lam * dlt))[:, None]
        self.ps = rng.uniform(0, 2 * np.pi, N_WAVES)
        self.amp = amp
        self.spec = {"wavelengths_px": [float(lo), float(hi)], "waves": N_WAVES, "seed": seed, "amplitude": amp}

    def __call__(self, d0, d1, d2):
        acc = np.zeros(np.shape(d0))
        for m in range(N_WAVES):
            acc = acc + np.sin(self.om[m, 0] * d0 + self.om[m, 1] * d1 + self.om[m, 2] * d2 + self.ps[m])
        return 128.0 + self.amp * acc


class Scene:
    """Analytic left / right gray images and the true right theta of every left pixel."""

    def __init__(self, c: dict, tex, dtheta, name: str) -> None:
        self.c, self.tex, self.dtheta, self.name = c, tex, dtheta, name
        self.cl, self.cr = M.make_cams(c)
        self.dlt = SP.delta(self.cl.f)
        v, u = np.mgrid[:SP.RAW_SIZE, :SP.RAW_SIZE].astype(np.float64)
        self.g_l = tex(*M.rays(self.cl, u, v))
        th, ph = M.theta_phi(*M.rays(self.cr, u, v))
        self.g_r = tex(*M.direction(th - dtheta(ph), ph))

    def truth(self, ctx: M.Context, idx) -> tuple[np.ndarray, np.ndarray]:
        """(s_true on the matcher's line, theta_R_true) of left core pixels ``idx``."""
        th_l, ph_l = ctx.th_l[idx], ctx.ph_l[idx]
        th_t = th_l + self.dtheta(ph_l)
        qu, qv, _ = M.project(ctx.cam_r, *M.direction(th_t, ph_l))
        q = np.stack([qu, qv], -1)
        return np.sum((q - ctx.line["q_inf"][idx]) * ctx.line["t"][idx], -1), th_t


def const(dt):
    return lambda phi: np.full(np.shape(phi), dt)


def gaze_phi() -> float:
    return float(M.theta_phi(*FG.gaze_direction(*SP.SYN_GAZE))[1])


def ramp(dlt):
    pg = gaze_phi()
    return lambda phi: dlt * (SP.SYN_DTHETA_SAMPLES + 10.0 * (np.asarray(phi) - pg) / 0.1)


def frac_bin(s, centre):
    f = s - np.floor(s)
    f = np.where(f > 1 - SP.SYN_BIN_HALF, f - 1.0, f)
    return np.abs(f - centre) <= SP.SYN_BIN_HALF


def q(a) -> dict | None:
    a = np.asarray(a, np.float64)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return None
    return {"median": float(np.median(a)), "p95": float(np.quantile(a, 0.95)), "max": float(a.max()), "n": int(a.size)}


# ------------------------------------------------------------------ cases
def run_synthetic(out_dir: Path) -> dict:
    t0 = time.time()
    out_dir.mkdir(parents=True, exist_ok=True)
    c = calibration()
    dlt = SP.delta(c["eyes"][0]["K"][0][0])
    tex = Texture(*SP.SYN_TEXTURE_PX, dlt)
    main = Scene(c, tex, const(SP.SYN_DTHETA_SAMPLES * dlt), "main")
    ctx = M.Context(c, main.g_l, main.g_r)
    idx = np.arange(0, SP.CORE_SIZE ** 2, SP.SYN_STRIDE)
    rec = M.match(ctx, idx)
    s_true, th_true = main.truth(ctx, idx)
    v = rec["valid_match"]
    e_ref = rec["s_est"] - s_true
    e_dis = rec["k_best"] - s_true
    cases = []

    def case(n, name, ok, **meas):
        cases.append({"case": n, "name": name, "passed": bool(ok), **meas})

    # 1 epipolar-line geometry
    sub = idx[::7]
    ln = ctx.line["l"][sub]
    lnorm = np.hypot(ln[:, 0], ln[:, 1])
    worst = 0.0
    s_mono = True
    for r in (0.3, 1.0, 4.5, 50.0):
        p = np.asarray(c["eyes"][0]["centre_h_m"]) + r * ctx.d_l[sub]
        uv, _ = FG.project_h(c["eyes"][1], p)
        dist = np.abs(ln[:, 0] * uv[:, 0] + ln[:, 1] * uv[:, 1] + ln[:, 2]) / lnorm
        worst = max(worst, float(dist.max()))
        s_r = np.sum((uv - ctx.line["q_inf"][sub]) * ctx.line["t"][sub], -1)
        s_mono &= bool((s_r > 0).all())
    qd = np.abs(np.sum(ln[:, :2] * ctx.line["q_inf"][sub], -1) + ln[:, 2]) / lnorm
    f = CK.fundamental(c)
    lf = (f @ np.stack([ctx.uv_l[sub, 0], ctx.uv_l[sub, 1], np.ones(sub.size)])).T
    ang = np.abs(np.arcsin(np.clip((ln[:, 0] * lf[:, 1] - ln[:, 1] * lf[:, 0]) / lnorm / np.hypot(lf[:, 0], lf[:, 1]),
                                   -1, 1)))
    case(1, "epipolar-line geometry", worst <= SP.SYN_LINE_PX and qd.max() <= SP.SYN_LINE_PX
         and ang.max() <= SP.SYN_LINE_PX and s_mono, max_point_line_px=worst, max_qinf_line_px=float(qd.max()),
         max_F_angle_rad=float(ang.max()), positive_s_for_finite_range=s_mono, pixels=int(sub.size))

    # 2 spherical equivalence of the candidates
    sub2 = idx[::50]
    cd = ctx.candidates(sub2)
    inr = cd["in_range"] & np.isfinite(cd["theta"])
    dphi = np.abs(BG.wrap_pi(cd["phi"] - ctx.ph_l[sub2][:, None]))[inr]
    mono = all(bool(np.all(np.diff(cd["theta"][i][inr[i]]) > 0)) for i in range(sub2.size))
    case(2, "spherical equivalence: candidates on the plane, theta increasing", float(dphi.max()) <= SP.SYN_PHI_RAD and mono,
         max_abs_phi_minus_phiL_rad=float(dphi.max()), theta_strictly_increasing=mono, pixels=int(sub2.size))

    # 3 exact textured match: integer bin; analytic-sampler exactness of the frozen score
    ib = v & frac_bin(s_true, 0.0)
    good = ib & (np.abs(e_dis) < 0.5)
    ana = analytic_exactness(c, tex, main, idx[ib][::4])
    ok3 = (good.sum() >= SP.SYN_CORRECT_INT * ib.sum() and q(np.abs(e_ref[good]))["median"] <= SP.SYN_REF_MEDIAN_PX
           and q(np.abs(e_ref[good]))["p95"] <= SP.SYN_REF_P95_PX and ana["passed"])
    case(3, "exact textured match (integer bin)", ok3, bin_pixels=int(ib.sum()),
         discrete_equals_round=float(good.sum() / max(ib.sum(), 1)), refined_abs_error_px=q(np.abs(e_ref[good])),
         discrete_abs_error_px=q(np.abs(e_dis[good])), analytic_sampler=ana)

    # 4 sub-pixel bins
    bins = {}
    ok4 = True
    for cen in (0.25, 0.50, 0.75):
        bb = v & frac_bin(s_true, cen)
        okk = bb & (np.abs(e_dis) < 1.0)
        er, ed = q(np.abs(e_ref[okk])), q(np.abs(e_dis[okk]))
        this = (okk.sum() >= SP.SYN_CORRECT_FRACTION * bb.sum() and er["median"] <= SP.SYN_REF_MEDIAN_PX
                and er["p95"] <= SP.SYN_REF_P95_PX and er["median"] < ed["median"])
        ok4 &= this
        bins[f"{cen:.2f}"] = {"pixels": int(bb.sum()), "correct_discrete": float(okk.sum() / max(bb.sum(), 1)),
                              "refined_abs_error_px": er, "discrete_abs_error_px": ed, "passed": bool(this)}
    case(4, "sub-pixel match (0.25 / 0.50 / 0.75 bins)", ok4, bins=bins)

    # 5 affine photometric gain / offset
    ctx5 = M.Context(c, main.g_l, 0.6 * main.g_r + 30.0)
    sub5 = idx[::5]
    r5, r0 = M.match(ctx5, sub5), M.match(ctx, sub5)
    same_k = bool(np.array_equal(r5["k_best"], r0["k_best"]))
    ds = float(np.nanmax(np.abs(r5["s_est"] - r0["s_est"])))
    dz = float(np.nanmax(np.abs(r5["best_zncc"] - r0["best_zncc"])))
    case(5, "affine photometric gain / offset", same_k and ds <= 1e-9 and dz <= 1e-12, same_k_best=same_k,
         max_s_diff_px=ds, max_zncc_diff=dz, pixels=int(sub5.size))

    # 6 flat patch
    gl6 = main.g_l.copy()
    gl6[300:348, 300:348] = 100.0
    ctx6 = M.Context(c, gl6, main.g_r)
    inner = np.array([(r - SP.CORE_ORIGIN) * SP.CORE_SIZE + (cc - SP.CORE_ORIGIN)
                      for r in range(304, 344) for cc in range(304, 344)])
    r6 = M.match(ctx6, inner)
    case(6, "flat patch -> LOW_TEXTURE", bool(np.all(r6["reason"] == 1) and not r6["valid_match"].any()),
         pixels=int(inner.size), max_left_std=float(r6["left_patch_std_u8"].max()))

    # 7 repeated texture
    rep = Scene(c, repeated_texture(dlt), const(SP.SYN_DTHETA_SAMPLES * dlt), "repeated")
    ctx7 = M.Context(c, rep.g_l, rep.g_r)
    sub7 = idx[::9]
    r7 = M.match(ctx7, sub7)
    v7 = r7["valid_match"]
    gap = np.abs(r7["peak_s"][:, 1] - r7["peak_s"][:, 0])
    near = np.abs(gap - SP.SYN_REPEAT_PERIOD_PX * np.rint(gap / SP.SYN_REPEAT_PERIOD_PX)) <= 1.5
    frac3 = float(np.mean(r7["peak_count"][v7] >= 3))
    mm = float(np.nanmedian(r7["peak_margin"][v7]))
    fnear = float(np.mean(near[v7 & np.isfinite(gap)]))
    case(7, "repeated texture exposes distinct near-equal peaks", frac3 >= 0.90 and mm <= 0.02 and fnear >= 0.90,
         fraction_three_or_more_peaks=frac3, median_margin=mm, fraction_gap_near_period_multiple=fnear,
         pixels=int(v7.sum()))

    # 8 search boundary
    bnd = Scene(c, tex, const(0.4 * dlt), "boundary")
    ctx8 = M.Context(c, bnd.g_l, bnd.g_r)
    sub8 = idx[::9]
    r8 = M.match(ctx8, sub8)
    atb = r8["valid_match"] & (r8["k_best"] == r8["k_first"])
    ok8 = (atb.sum() > 0 and not r8["refined"][atb].any()
           and bool(np.array_equal(r8["uv_R_est"][atb], r8["uv_R_discrete"][atb])))
    case(8, "search boundary -> no refinement", ok8, at_boundary=int(atb.sum()), pixels=int(sub8.size))

    # 9-11 structural mutations must fail the known answer
    rmp = Scene(c, tex, ramp(dlt), "phi-ramp")
    sub9 = idx[::9]
    for n, name, mut in ((9, "wrong epipolar-plane sign (phi = atan2(-d_y, -d_z))", "phi_sign"),
                         (10, "wrong right-camera transform (R_hc_R transposed)", "right_transposed"),
                         (11, "wrong baseline axis (+Y)", "baseline_y")):
        base_err = mutated_error(c, rmp, sub9, None)
        err, frac_valid = mutated_error(c, rmp, sub9, mut)
        fails = (not math.isfinite(err)) or err > SP.SYN_FAIL_PX or frac_valid < 0.5
        case(n, name + " -> known-answer failure", fails and base_err[0] < 1.0, mutated_median_abs_error_px=err,
             mutated_valid_fraction=frac_valid, frozen_median_abs_error_px=base_err[0])

    # 12-16 the checker's independent recomputation detects altered constants
    low = Scene(c, low_contrast(tex, c), const(SP.SYN_DTHETA_SAMPLES * dlt), "low-contrast")
    rough = Scene(c, Texture(*SP.SYN_ROUGH_PX, dlt, seed=SP.SYN_SEED + 1), const(SP.SYN_DTHETA_SAMPLES * dlt), "rough")
    pix_low = low_contrast_pixels(c, low)
    for n, name, kw, scene, pix in (
            (12, "altered patch size (7 x 7)", {"patch_half": 3}, main, idx[::97]),
            (13, "altered candidate spacing (0.5 px)", {"spacing": 0.5}, rough, idx[::97]),
            (14, "altered texture threshold (2.0)", {"min_std": 2.0}, low, pix_low),
            (15, "altered peak separation (2 px)", {"separation": 2.0}, rough, idx[::61]),
            (16, "altered sub-pixel bound (0.40)", {"bound": 0.40}, main, idx[v & frac_bin(s_true, 0.5)][:160])):
        res = checker_detects(c, scene, pix, kw)
        case(n, name + " -> the checker detects", res["frozen_mismatch"] == 0 and res["mutated_mismatch"] > 0, **res)

    # 17 truth-bearing matcher input
    try:
        M.validate_observation({"rgb_L": np.zeros((640, 640, 3)), "rgb_R": np.zeros((640, 640, 3)),
                                "position_w_L": np.zeros((640, 640, 3))}, (640, 640))
        rejected = False
    except ValueError:
        rejected = True
    case(17, "truth-bearing matcher input rejected", rejected)

    # 18 Position / oracle access during matching refused by the guarded stage
    gp = guard_probe(out_dir / "guard-probe", c, main)
    case(18, "Position / oracle access during matching refused", gp.pop("passed"), **gp)

    # 19 product schema
    prod = M.product(rec)
    bad = []
    for extra in ("depth_m", "xyz_h", "instance_id"):
        try:
            BG.validate_product({**prod, extra: np.zeros(prod["left_core_row"].shape)})
            bad.append(extra)
        except ValueError:
            pass
    case(19, "natural product rejects depth / XYZ / identity fields", not bad, accepted_forbidden=bad)

    # 20 spherical geometry consumes the natural product unchanged
    res = BG.compute_epipolar(c, prod)
    vv = rec["valid_match"]
    dth = float(np.max(np.abs(res["theta_R"] - rec["theta_R_est"][vv])))
    dph = float(np.max(np.abs(res["phi_residual"])))
    o_l = np.asarray(c["eyes"][0]["centre_h_m"])
    rel = res["P_epi"] - o_l
    off_ray = float(np.max(np.linalg.norm(rel - np.sum(rel * res["d_L"], -1)[:, None] * res["d_L"], axis=-1)))
    case(20, "spherical geometry consumes the natural product unchanged",
         dth <= 1e-12 and dph <= SP.SYN_PHI_RAD and off_ray <= 1e-9 and bool(res["valid_epi"].all()),
         max_theta_diff_rad=dth, max_abs_phi_residual_rad=dph, max_off_left_ray_m=off_ray,
         triangulated=int(res["valid_epi"].sum()), pairs=int(vv.sum()))

    # 21 photometric conversion
    rgb = np.array([[[0.0, 0.0, 0.0], [1.0, 1.0, 1.0], [0.5, 0.2, 0.1], [0.0031308, 0.04, 2.0]]])
    g_m, g_o = M.gray(rgb), CK.own_gray(rgb)
    u8_want = np.array([[[0, 0, 0], [255, 255, 255], [188, 124, 89], [10, 56, 255]]])
    want = np.array([[0.0, 255.0, 0.2126 * 188 + 0.7152 * 124 + 0.0722 * 89, 0.2126 * 10 + 0.7152 * 56 + 0.0722 * 255]])
    case(21, "photometric conversion = Rec.709 of linear_to_u8", bool(np.array_equal(g_m, g_o))
         and bool(np.array_equal(FS.linear_to_u8(rgb), u8_want)) and bool(np.allclose(g_m, want, rtol=0, atol=1e-9))
         and FS.MIN_LOCAL_STD_U8 == SP.MIN_LOCAL_STD_U8, values=g_m.ravel().tolist())

    # 22 ZNCC, tie rule, distinct peaks, parabola (pure functions)
    du = decision_units()
    case(22, "ZNCC, tie rule, distinct peaks and parabola", du.pop("passed"), **du)

    # 23 execution strategy
    sub23 = idx[::11]
    ra, rb = M.match(ctx, sub23, threads=1), M.match(ctx, sub23, threads=SP.THREADS, batch=37)
    same = all(np.array_equal(ra[k], rb[k], equal_nan=True) for k in ra)
    case(23, "1 thread and the declared threads give byte-identical records", same, pixels=int(sub23.size))

    # 24 end-to-end through linear RGB -> u8 -> gray
    ctx24 = M.Context(c, M.gray(to_linear_rgb(main.g_l)), M.gray(to_linear_rgb(main.g_r)))
    sub24 = idx[ib][::2]
    r24 = M.match(ctx24, sub24)
    s24, _ = main.truth(ctx24, sub24)
    fr = float(np.mean(r24["k_best"] == np.rint(s24)))
    case(24, "end-to-end linear RGB -> u8 -> gray", fr >= 0.95, fraction_k_equals_round=fr, pixels=int(sub24.size))

    passed = all(x["passed"] for x in cases)
    report = {"schema": "AB1d-synthetic-v1", "truth": SP.TRUTH_DERIVED,
              "statement": "synthetic known answers on analytic scenes only (no Blender, no Classroom); software "
                           "tolerances", "calibration_gaze": list(SP.SYN_GAZE), "texture": tex.spec,
              "main_scene": {"dtheta_samples": SP.SYN_DTHETA_SAMPLES, "pixels": int(idx.size),
                             "valid": int(v.sum()), "refined_abs_error_px": q(np.abs(e_ref[v])),
                             "gross_error_fraction_gt_1_5px": float(np.mean(np.abs(e_ref[v]) > 1.5)),
                             "median_peak_margin": float(np.nanmedian(rec["peak_margin"][v]))},
              "cases": cases, "passed": passed, "seconds": round(time.time() - t0, 2)}
    return report


# ------------------------------------------------------------------ helpers of the cases
def analytic_exactness(c, tex, scene: Scene, pix) -> dict:
    """With exact (analytic) sampling, the frozen score's continuous maximum lies at s_true (0.01-px grid)."""
    gl_id, gr_id = np.zeros((SP.RAW_SIZE, SP.RAW_SIZE)), np.ones((SP.RAW_SIZE, SP.RAW_SIZE))
    cl, cr = M.make_cams(c)

    def sampler(g, u, v):
        cam = cl if g is gl_id else cr
        d = M.rays(cam, u, v)
        if g is gl_id:
            val = tex(*d)
        else:
            t, p = M.theta_phi(*d)
            val = tex(*M.direction(t - scene.dtheta(p), p))
        with np.errstate(invalid="ignore"):
            inside = (u >= 0) & (u <= SP.RAW_SIZE - 1) & (v >= 0) & (v <= SP.RAW_SIZE - 1)
        return np.where(inside, val, np.nan), inside

    orig = M.bilinear
    M.bilinear = sampler
    try:
        ctx = M.Context(c, gl_id, gr_id)
        s_true, _ = scene.truth(ctx, pix)
        grid = np.round(np.arange(-0.30, 0.3001, 0.01), 10)
        S = np.stack([M.score_at(ctx, pix, M.line_theta(ctx, pix, s_true + o))[0] for o in grid], 1)
    finally:
        M.bilinear = orig
    peak = grid[np.nanargmax(S, axis=1)]
    at_truth = S[:, int(np.argmin(np.abs(grid)))]
    ok = bool(np.all(np.abs(peak) <= 0.0100001) and np.nanmin(at_truth) >= 0.9999)
    return {"passed": ok, "pixels": int(len(pix)), "max_abs_peak_offset_px": float(np.abs(peak).max()),
            "min_zncc_at_truth": float(np.nanmin(at_truth))}


def repeated_texture(dlt):
    p = SP.SYN_REPEAT_PERIOD_PX

    def tex(d0, d1, d2):
        th, ph = M.theta_phi(d0, d1, d2)
        return 128.0 + 60.0 * np.sin(2 * np.pi * th / (p * dlt)) + 25.0 * np.sin(2 * np.pi * ph * np.sin(th) / (19 * dlt) + 1.3)
    return tex


def low_contrast(tex, c):
    """The main texture with its contrast reduced to 6 % inside a disc (patch std inside (0.5, 2))."""
    d0 = FG.rays_h(c["eyes"][0], np.array([[250.0, 380.0]]))[0]

    def t2(a, b, cc):
        inside = (a * d0[0] + b * d0[1] + cc * d0[2]) >= math.cos(0.012)
        base = tex(a, b, cc)
        return np.where(inside, 128.0 + 0.06 * (base - 128.0), base)
    return t2


def low_contrast_pixels(c, scene: Scene) -> np.ndarray:
    ctx = M.Context(c, scene.g_l, scene.g_r)
    sd = ctx.lp_std
    return np.nonzero((sd >= 0.5) & (sd < 2.0))[0][:160]


def mutated_error(c, scene: Scene, pix, mut):
    saved = (M.theta_phi, M.make_cams, M.BASELINE)
    try:
        if mut == "phi_sign":
            M.theta_phi = lambda d0, d1, d2: (np.arctan2(np.hypot(d1, d2), d0), np.arctan2(-d1, -d2))
        elif mut == "right_transposed":
            M.make_cams = lambda cc: (M.Cam(cc["eyes"][0], cc["image_size_wh"]),
                                      M.Cam(cc["eyes"][1], cc["image_size_wh"], np.asarray(cc["eyes"][1]["R_hc"]).T))
        elif mut == "baseline_y":
            M.BASELINE = np.array([0.0, 1.0, 0.0])
        ctx = M.Context(c, scene.g_l, scene.g_r)
        rec = M.match(ctx, pix)
    finally:
        M.theta_phi, M.make_cams, M.BASELINE = saved
    ctx0 = M.Context(c, scene.g_l, scene.g_r)
    s_true, th_true = scene.truth(ctx0, pix)
    v = rec["valid_match"]
    if not v.any():
        return float("inf"), 0.0
    # the error is measured in the true geometry: true right theta vs the mutated estimate's own uv
    uv = rec["uv_R_est"][v]
    th_est = M.theta_phi(*M.rays(ctx0.cam_r, uv[:, 0], uv[:, 1]))[0]
    scale = M.line_theta(ctx0, pix[v], s_true[v] + 0.5) - M.line_theta(ctx0, pix[v], s_true[v] - 0.5)
    err = np.abs((th_est - th_true[v]) / scale)
    return float(np.median(err)), float(v.mean())


def checker_detects(c, scene: Scene, pix, kw: dict) -> dict:
    ctx_f = M.Context(c, scene.g_l, scene.g_r)
    rec_f = M.match(ctx_f, pix)
    ctx_m = M.Context(c, scene.g_l, scene.g_r, M.Params(**kw))
    rec_m = M.match(ctx_m, pix)
    own = CK.own_match(c, scene.g_l, scene.g_r, pix)
    sel = np.arange(len(pix))
    mf, mm = CK.compare_records(rec_f, own, sel), CK.compare_records(rec_m, own, sel)
    return {"pixels": int(len(pix)), "frozen_mismatch": int(sum(mf.values())), "mutated_mismatch": int(sum(mm.values())),
            "mutated_fields": sorted(k for k, n in mm.items() if n)}


def guard_probe(root: Path, c: dict, scene: Scene) -> dict:
    """Run the real guarded match stage on a synthetic gaze and try to read truth from inside it."""
    import ab1d_run as R
    (root / "inputs").mkdir(parents=True, exist_ok=True)
    (root / "forbidden").mkdir(parents=True, exist_ok=True)
    cal, rgbp = root / "inputs/calibration.json", root / "inputs/rgb-observation.npz"
    cal.write_text(json.dumps(c))
    np.savez_compressed(rgbp, rgb_L=to_linear_rgb(scene.g_l).astype(np.float32),
                        rgb_R=to_linear_rgb(scene.g_r).astype(np.float32))
    forb = [root / "forbidden/reference-observation.npz", root / "forbidden/oracle-correspondences.npz"]
    for p in forb:
        np.savez(p, x=np.zeros(1))
    out = root / "match"
    if out.exists():
        for p in sorted(out.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
    refused = []

    def probe():
        for p in forb:
            try:
                with open(p, "rb"):
                    pass
            except PermissionError:
                refused.append(p.name)
    try:
        R.run_match_gaze(cal, rgbp, out, idx=np.arange(0, SP.CORE_SIZE ** 2, 4093), probe=probe)
        stage_failed = False
    except PermissionError:
        stage_failed = True
    rec = json.loads((out / "match-opened-files.json").read_text())
    ok = (sorted(refused) == sorted(p.name for p in forb) and len(rec["violations"]) == len(forb)
          and rec["position_reads"] >= 1 and rec["oracle_reads"] >= 1 and not stage_failed)
    return {"passed": ok, "refused": sorted(refused), "violations": len(rec["violations"]),
            "position_reads_recorded": rec["position_reads"], "oracle_reads_recorded": rec["oracle_reads"]}


def decision_units() -> dict:
    rng = np.random.default_rng(7)
    a, b = rng.normal(size=(50, 25)) * 30 + 100, rng.normal(size=(50, 25)) * 20 + 80
    da, _ = M.moments(a)
    db, _ = M.moments(b)
    z = M.zncc(da, db)
    direct = np.array([np.corrcoef(a[i], b[i])[0, 1] for i in range(50)])
    zerr = float(np.abs(z - direct).max())
    S = np.array([[0.1, 0.5, 0.9, 0.5, 0.9, 0.2, np.nan, 0.3, 0.95, 0.94, 0.3]])
    d = M.decide(S)
    tie = M.decide(np.array([[0.2, 0.9, 0.9 + 5e-13, 0.1]]))
    peaks = [int(j) for j in d["peak_j"][0] if j >= 0]
    want_peaks = [8, 2]             # local peaks: 2 (0.9), 4 (0.9), 8 (0.95); 4 is suppressed by 2 (|4 - 2| < 3)
    xs = np.array([-1.0, 0.0, 1.0])
    quad = -0.3 * (xs - 0.2) ** 2 + 0.8
    dq = M.decide(np.array([[0.0, *quad, 0.0]]))
    ok = (zerr <= 1e-12 and int(d["j_best"][0]) == 8 and peaks == want_peaks and int(tie["j_best"][0]) == 1
          and abs(float(dq["offset"][0]) - 0.2) <= 1e-12 and bool(dq["refined"][0]))
    return {"passed": ok, "zncc_max_error": zerr, "best": int(d["j_best"][0]), "peaks": peaks,
            "tie_pick": int(tie["j_best"][0]), "parabola_offset": float(dq["offset"][0])}


def to_linear_rgb(g: np.ndarray) -> np.ndarray:
    """Equal-channel linear RGB whose linear_to_u8 is the nearest u8 of g (inverse sRGB curve)."""
    s = np.clip(np.asarray(g, np.float64), 0, 255) / 255.0
    lin = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
    return np.repeat(lin[..., None], 3, axis=-1)


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("synthetic-dev")
    rep = run_synthetic(out)
    for x in rep["cases"]:
        print(f"[ab1d-synthetic] {'PASS' if x['passed'] else 'FAIL'} {x['case']:2d} {x['name']}")
    print(f"[ab1d-synthetic] {'AB1D_SYNTHETIC_PASS' if rep['passed'] else 'FAILED'} "
          f"{sum(x['passed'] for x in rep['cases'])}/{len(rep['cases'])} in {rep['seconds']} s")
    return 0 if rep["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
