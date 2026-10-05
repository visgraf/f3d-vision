"""Active Bootstrap-1d3: preflight known answers (contract sections 9 and 10), before any canonical SGBM.

Two families, never Classroom pixels:
- ADAPTER known answers on the three accepted calibrations (calibration-only data): raw -> rectified -> raw round trips,
  an analytic perfect correspondence (a tilted plane's rectified disparity is affine in (u, v), so bilinear sampling is
  exact), an OpenCV-map cross-check, and each wrong variant (R2 transposed, wrong intrinsic, disparity sign, sampling
  across an invalid pixel, non-raw uv_L) failing;
- SGBM known answers on analytic synthetic textured planes (the accepted ``ab1a_run.render_planes``): recovery, off-axis
  safe-forward calibrations, sub-pixel disparity with the bounded refinement, a periodic band (semi-global aggregation is
  active), wrong eye order, the full-raster window equal to the accepted crop, determinism, and the checker's audit
  detecting every configuration change; plus the truth firewall (refused truth-bearing input and refused reads).

Software tolerances are declared in ``ab1d3_spec``; nothing here is tuned on Classroom data.
"""
from __future__ import annotations

import contextlib
import json
from pathlib import Path
import shutil
import sys
import time

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent / "natural_bootstrap"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ab1a_run as AR  # noqa: E402  (accepted analytic plane renderer, read-only)
import ab1a_spec as ASP  # noqa: E402
import ab1a_stereo as AS  # noqa: E402
import ab1b_geometry as BG  # noqa: E402
import ab1c_planar as CP  # noqa: E402
import ab1d_run as AD  # noqa: E402
import ab1d3_sgbm as SG  # noqa: E402
import ab1d3_spec as SP  # noqa: E402
import check_ab1d3_core as K  # noqa: E402  (the checker's independent primitives)
import fsg_geometry as FG  # noqa: E402
import fsg_stereo as FS  # noqa: E402
from nb1a_guard import OpenGuard  # noqa: E402


def calibrations() -> dict:
    return {g: json.loads(SP.calibration_path(g).read_text()) for g in SP.GAZES}


def forward_calibration() -> dict:
    return FG.make_calibration(ASP.PROFILE, 0.0, 0.0, ASP.VERGENCE_M, tangent_frame=ASP.TANGENT_FRAME)


def jsonable(x):
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else float(x)
    return x


# ------------------------------------------------------------------ helpers: synthetic records and scenes
def fake_record(c: dict, disparity: np.ndarray, valid: np.ndarray | None = None) -> dict:
    """A calibration-only stand-in for the SGBM record: the accepted rectification + a given disparity field."""
    r = FS.rectification(c)
    w, h = c["image_size_wh"]
    v = np.ones((h, w), bool) if valid is None else valid
    rec = {k: np.asarray(r[k]) for k in ("R1", "R2", "P1", "P2", "Q_full")}
    rec.update({"disparity_px": disparity, "disparity_sgbm_px": disparity, "lr_error_px": np.zeros((h, w)),
                "valid": v})
    rec.update({t: v.copy() for t in SP.TERMS})
    return rec


def tilted_plane(c: dict, normal_rect=(0.18, -0.12, 1.0), dist=2.2) -> tuple[np.ndarray, callable]:
    """A plane n . X = dist in the rectified-left frame.  Returns its analytic disparity raster (affine in u, v) and a
    function mapping raw left pixels to their true 3-D head-frame point."""
    r = FS.rectification(c)
    w, h = c["image_size_wh"]
    p1 = np.asarray(r["P1"], float)
    f, cx, cy = p1[0, 0], p1[0, 2], p1[1, 2]
    b = -float(r["P2"][0, 3]) / f
    n = np.asarray(normal_rect, float) / np.linalg.norm(normal_rect)
    v, u = np.mgrid[:h, :w].astype(float)
    inv_z = (n[0] * (u - cx) / f + n[1] * (v - cy) / f + n[2]) / dist
    disp = f * b * inv_z
    r1 = np.asarray(r["R1"], float)
    o_l = np.asarray(c["eyes"][0]["centre_h_m"], float)

    def truth(uv_l):
        d = FG.rays_h(c["eyes"][0], uv_l)                         # head frame
        d_rect = (d @ np.asarray(c["eyes"][0]["R_hc"], float)) @ r1.T  # head -> raw camera -> rectified
        t = dist / (d_rect @ n)
        return o_l + d * t[:, None]
    return disp, truth


def plane_scene(c: dict, z=SP.SYN_PLANE_Z_M, seed=1, tex=None, spacing=0.004):
    r = FS.rectification(c)
    t = AR.noise_texture(seed) if tex is None else tex
    rgb, truth = AR.render_planes(c, [{"n": AR.rect_axis_h(c, r), "z": z, "tex": t, "spacing": spacing}])
    return r, rgb, truth


def plane_metrics(c: dict, r: dict, rec: dict, truth: dict, z: float, variant=None) -> dict:
    out, prod = SG.adapt(c, rec, variant)
    d_true = -float(r["P2"][0, 3]) / z
    v = out["valid_adapter"]
    e = out["disparity_bilinear_px"][v] - d_true
    m = {"valid_fraction_core": float(v.mean()), "d_true": d_true,
         "median_d_error": float(np.median(e)) if e.size else None,
         "p95_abs_d_error": float(np.quantile(np.abs(e), 0.95)) if e.size else None}
    if prod["left_core_row"].size:
        res = BG.compute_epipolar(c, prod)
        rows, cols = prod["left_core_row"].astype(int) + SP.CORE_ORIGIN, prod["left_core_col"].astype(int) + SP.CORE_ORIGIN
        pos = FG.world_to_head(c, truth["position_w_L"][rows, cols].astype(np.float64))
        e3 = np.linalg.norm(res["P_epi"] - pos, axis=1)
        m.update({"median_3d_m": float(np.nanmedian(e3)), "p95_3d_m": float(np.nanquantile(e3, 0.95)),
                  "phi_residual_max": float(np.nanmax(np.abs(res["phi_residual"])))})
    else:
        m.update({"median_3d_m": None, "p95_3d_m": None, "phi_residual_max": None})
    return m


def plane_ok(m: dict) -> bool:
    return bool(m["median_d_error"] is not None and m["valid_fraction_core"] >= SP.SYN_MIN_VALID
                and abs(m["median_d_error"]) <= SP.SYN_MAX_MEDIAN_DISPARITY_PX
                and m["p95_abs_d_error"] <= SP.SYN_MAX_P95_DISPARITY_PX
                and m["median_3d_m"] is not None and m["median_3d_m"] <= SP.SYN_MAX_MEDIAN_3D_M
                and m["phi_residual_max"] <= 1e-9)


@contextlib.contextmanager
def sgbm_override(**kw):
    """Mutation hook (known answers only): build every SGBM object with some parameters replaced."""
    orig = cv2.StereoSGBM_create

    def f(*a, **k):
        k = dict(k)
        k.update(kw)
        return orig(*a, **k)
    cv2.StereoSGBM_create = f
    try:
        yield
    finally:
        cv2.StereoSGBM_create = orig


@contextlib.contextmanager
def patched(module, name, value):
    saved = getattr(module, name)
    setattr(module, name, value)
    try:
        yield
    finally:
        setattr(module, name, saved)


def refine_changed(left, right, initial, supported):
    """A changed refinement (mutation): the accepted update with a 2.0 px total bound and 5 iterations."""
    luma = np.array([.2126, .7152, .0722], np.float32)
    lg, rg = np.asarray(left, np.float32) @ luma, np.asarray(right, np.float32) @ luma
    grad = cv2.Sobel(rg, cv2.CV_32F, 1, 0, ksize=3, scale=1 / 8)
    h, w = lg.shape
    vv, uu = np.mgrid[:h, :w].astype(np.float32)
    d = initial.copy()
    mean = lambda a: cv2.boxFilter(a, -1, (5, 5), normalize=True, borderType=cv2.BORDER_REFLECT)  # noqa: E731
    for _ in range(5):
        x = uu - d
        rw = cv2.remap(rg, x, vv, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        gw = cv2.remap(grad, x, vv, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        res = rw - lg
        gm, rm = mean(gw), mean(res)
        num = mean(gw * res) - gm * rm
        den = np.maximum(mean(gw * gw) - gm * gm, 0.)
        step = np.divide(num, den + 1e-9, out=np.zeros_like(d), where=den > 1e-8)
        d = np.where(supported, np.clip(d + np.clip(step, -.5, .5), initial - 2.0, initial + 2.0), initial).astype(np.float32)
    return d


def band_texture() -> tuple[np.ndarray, tuple[int, int]]:
    p = SP.SYN_REPEAT
    n = p["texture_n"]
    rng = np.random.default_rng(p["seed"])
    nz = cv2.GaussianBlur(rng.random((n, n)).astype(np.float32), (0, 0), 1.2)
    nz = (nz - nz.min()) / (nz.max() - nz.min())
    t = 0.05 + 0.9 * nz
    x = np.arange(n)[None, :]
    stripes = 0.5 + p["contrast"] * np.sin(2 * np.pi * x / p["period_texels"]) * np.ones((n, 1))
    lo, hi = n // 2 - p["band_texels"] // 2, n // 2 + p["band_texels"] // 2
    t[lo:hi] = np.clip(stripes[lo:hi] + p["noise"] * (nz[lo:hi] - 0.5), 0, 1)
    return np.repeat(t[..., None].astype(np.float32), 3, -1), (lo, hi)


# ------------------------------------------------------------------ cases
def run_preflight(out_dir: Path) -> dict:
    t0 = time.time()
    out_dir.mkdir(parents=True, exist_ok=True)
    cals = calibrations()
    fwd = forward_calibration()
    cases = []

    def case(name, fn):
        try:
            ok, det = fn()
        except Exception as exc:          # a known answer that cannot run fails
            ok, det = False, {"error": f"{type(exc).__name__}: {exc}"}
        cases.append({"case": len(cases) + 1, "name": name, "passed": bool(ok), "detail": jsonable(det)})

    # ---- adapter known answers (calibration-only)
    def roundtrip():
        det = {}
        for g, c in cals.items():
            r = FS.rectification(c)
            v, u = np.mgrid[100:540:7, 100:540:7]
            uv = np.stack([u.ravel(), v.ravel()], -1).astype(float)
            errs = []
            for side, k, rr, pp in (("L", 0, "R1", "P1"), ("R", 1, "R2", "P2")):
                kk = np.asarray(c["eyes"][k]["K"], float)
                uvr, _ = CP.to_rectified(kk, r[rr], r[pp], uv)
                back, z = SG.inverse_rectified(kk, r[rr], np.asarray(r[pp])[:, :3], uvr)
                errs.append(float(np.max(np.abs(back - uv))))
            det[g] = {"max_err_L_px": errs[0], "max_err_R_px": errs[1]}
        return all(max(d.values()) <= SP.KA_ROUNDTRIP_PX for d in det.values()), det
    case("adapter: raw -> rectified -> raw round trip (both eyes, 3 accepted calibrations)", roundtrip)

    def perfect(variant=None):
        det = {}
        for g, c in cals.items():
            disp, truth = tilted_plane(c)
            out, prod = SG.adapt(c, fake_record(c, disp), variant)
            v = out["valid_adapter"]
            rows, cols, uv_l = SG.core_grid()
            x = truth(uv_l)
            uv_true, _ = FG.project_h(c["eyes"][1], x)
            err = np.abs(out["uv_R_unmasked"] - uv_true)
            det[g] = {"valid": int(v.sum()), "max_err_px": float(np.nanmax(err[v])) if v.any() else None,
                      "median_err_px": float(np.nanmedian(err[v])) if v.any() else None}
        return det

    def perfect_case():
        det = perfect()
        return all(d["valid"] == SP.CORE_SIZE ** 2 and d["max_err_px"] <= SP.KA_PERFECT_PX for d in det.values()), det
    case("adapter: analytic perfect correspondence (tilted plane, full raw core, 3 calibrations) recovers uv_R",
         perfect_case)

    def opencv_maps():
        det = {}
        for g, c in cals.items():
            r = FS.rectification(c)
            v, u = np.mgrid[0:640:3, 0:640:3]
            uvr = np.stack([u.ravel(), v.ravel()], -1).astype(float)
            out = {}
            for side, k, rr, pp in (("L", 0, "R1", "P1"), ("R", 1, "R2", "P2")):
                uv, z = SG.inverse_rectified(np.asarray(c["eyes"][k]["K"], float), r[rr], np.asarray(r[pp])[:, :3], uvr)
                mx, my = r["map_" + side + "x"][v.ravel(), u.ravel()], r["map_" + side + "y"][v.ravel(), u.ravel()]
                m = (z > 0) & np.isfinite(uv).all(-1)
                out[side] = float(np.max(np.hypot(uv[m, 0] - mx[m], uv[m, 1] - my[m])))
            det[g] = out
        return all(max(d.values()) <= SP.KA_OPENCV_MAP_PX for d in det.values()), det
    case("adapter: rectified -> raw inverse equals OpenCV's own initUndistortRectifyMap (float32) at every 3rd pixel",
         opencv_maps)

    def must_fail(variant, label):
        def fn():
            det = perfect(variant)
            worst = min((d["max_err_px"] or np.inf) if d["valid"] else np.inf for d in det.values())
            return worst > 1.0, {"variant": label, "per_gaze": det, "smallest_max_error_px": worst}
        return fn
    case("adapter mutation: R2 transposed must fail", must_fail({"r2_transposed": True}, "R2^T"))

    def k_rect_confusion():
        det = {}
        for g, c in cals.items():
            k_rect = np.asarray(FS.rectification(c)["P2"])[:, :3]
            det[g] = perfect({"k_right": k_rect.tolist()})[g]
        worst = min((d["max_err_px"] or np.inf) if d["valid"] else np.inf for d in det.values())
        return worst > 1.0, {"per_gaze": det, "smallest_max_error_px": worst}
    case("adapter mutation: the rectified intrinsic K_rect used as the raw right intrinsic must fail", k_rect_confusion)

    def focal_scaled():
        det = {}
        for g, c in cals.items():
            k = np.asarray(c["eyes"][1]["K"], float).copy()
            k[0, 0] *= 1.001
            k[1, 1] *= 1.001
            d = perfect({"k_right": k.tolist()})[g]
            det[g] = d
        worst = min(d["max_err_px"] for d in det.values())
        return worst > 1e-3, {"per_gaze": det, "smallest_max_error_px": worst,
                              "note": "the two eyes share K in these calibrations, so a swapped eye intrinsic is a "
                                      "no-op; the mutation is a 0.1 % focal error"}
    case("adapter mutation: right intrinsic focal scaled by 1.001 must fail (above 1e-3 px)", focal_scaled)
    case("adapter mutation: disparity sign flipped must fail", must_fail({"disparity_sign": -1.0}, "u_R = u_L + d"))

    def one_invalid():
        c = cals["gaze-2"]
        disp, _ = tilted_plane(c)
        base_out, _ = SG.adapt(c, fake_record(c, disp))
        uvr = base_out["uvrect_L"]
        k = SP.CORE_SIZE * 128 + 128
        px, py = int(np.floor(uvr[k, 0])) + 1, int(np.floor(uvr[k, 1])) + 1
        valid = np.ones((640, 640), bool)
        valid[py, px] = False
        rec = fake_record(c, disp, valid)
        out, prod = SG.adapt(c, rec)
        x0, y0 = base_out["footprint_x0"].astype(int), base_out["footprint_y0"].astype(int)
        contains = (x0 <= px) & (px <= x0 + 1) & (y0 <= py) & (py <= y0 + 1)
        rejected = ~out["valid_adapter"]
        out_ignore, _ = SG.adapt(c, rec, {"ignore_footprint_validity": True})
        ok = (contains.sum() >= 1 and np.array_equal(rejected, contains) and out_ignore["valid_adapter"][contains].all())
        return ok, {"invalid_pixel": [px, py], "samples_containing_it": int(contains.sum()),
                    "rejected": int(rejected.sum()), "accepted_by_the_ignore_mutation": int(out_ignore["valid_adapter"][contains].sum())}
    case("adapter: one invalid SGBM source pixel rejects exactly the raw-core samples whose bilinear footprint holds it",
         one_invalid)

    def non_raw_uv_l():
        c = cals["gaze-1"]
        disp, _ = tilted_plane(c)
        _, prod = SG.adapt(c, fake_record(c, disp))
        det = {}
        for off in (1e-9, 0.5):
            p = {k: v.copy() for k, v in prod.items()}
            p["uv_L"][10, 0] += off
            try:
                BG.validate_product(p)
                det[str(off)] = "accepted"
            except ValueError as e:
                det[str(off)] = f"rejected: {e}"
        BG.validate_product(prod)
        return all(v.startswith("rejected") for v in det.values()), det
    case("product: uv_L moved off the exact raw pixel centre (1e-9 px, 0.5 px) is rejected by the accepted AB1b "
         "validator", non_raw_uv_l)

    def checker_adapter():
        det = {}
        for g, c in cals.items():
            disp, _ = tilted_plane(c)
            rec = fake_record(c, disp)
            out, _ = SG.adapt(c, rec)
            own = K.own_adapt(c, rec["R1"], rec["R2"], rec["P1"], rec["P2"], rec["disparity_px"], rec["valid"])
            same = np.array_equal(own["valid"], out["valid_adapter"])
            diff = float(np.max(np.abs(own["uv_R"][own["valid"]] - out["uv_R_unmasked"][own["valid"]])))
            mut = {}
            for name, v in (("r2_transposed", {"r2_transposed": True}), ("sign", {"disparity_sign": -1.0})):
                o2, _ = SG.adapt(c, rec, v)
                m = own["valid"] & o2["valid_adapter"]
                mut[name] = float(np.max(np.abs(own["uv_R"][m] - o2["uv_R_unmasked"][m]))) if m.any() else np.inf
            det[g] = {"valid_equal": same, "max_uv_R_diff_px": diff, "mutation_diff_px": mut}
        ok = all(d["valid_equal"] and d["max_uv_R_diff_px"] <= 1e-9 and min(d["mutation_diff_px"].values()) > 1.0
                 for d in det.values())
        return ok, det
    case("checker: the independent adapter agrees with the run adapter (<= 1e-9 px) and detects R2^T and sign mutations",
         checker_adapter)

    # ---- SGBM known answers (analytic synthetic planes)
    def fronto():
        r, rgb, truth = plane_scene(fwd)
        rec, summ, calls = SG.compute_sgbm(fwd, rgb)
        m = plane_metrics(fwd, r, rec, truth, SP.SYN_PLANE_Z_M)
        return plane_ok(m), m
    case("SGBM: textured fronto-parallel plane at z_rect 2 m (forward calibration): disparity and spherical geometry "
         "recovered", fronto)

    def off_axis():
        det = {}
        for g, c in cals.items():
            r, rgb, truth = plane_scene(c, seed=2)
            rec, summ, calls = SG.compute_sgbm(c, rgb)
            det[g] = plane_metrics(c, r, rec, truth, SP.SYN_PLANE_Z_M)
        return all(plane_ok(m) for m in det.values()), det
    case("SGBM: safe-forward off-axis (the 3 accepted calibrations, synthetic plane): disparity and geometry recovered",
         off_axis)

    base_c = cals["gaze-1"]
    base_r, base_rgb, base_truth = plane_scene(base_c, seed=3)
    base_rec, base_summ, base_calls = SG.compute_sgbm(base_c, base_rgb)

    def crop_equal():
        acc, _ = AS.compute_natural(base_c, base_rgb)
        x, y, cw, ch = map(int, acc["crop_xywh"])
        sl = np.s_[y:y + ch, x:x + cw]
        keys = [k for k in acc if np.ndim(acc[k]) >= 2 and np.shape(acc[k])[:2] == (cw, ch)]
        bad = [k for k in keys if not np.array_equal(acc[k], base_rec[k][sl], equal_nan=np.asarray(acc[k]).dtype.kind == "f")]
        same_rect = all(np.array_equal(acc[k], base_rec[k]) for k in ("R1", "R2", "P1", "P2", "Q_full", "Q_core",
                                                                      "num_disparities", "valid_disparity_roi"))
        return not bad and same_rect and len(keys) >= 15, {"compared_arrays": keys, "mismatches": bad,
                                                           "rectification_identical": same_rect,
                                                           "full_window": [int(a) for a in base_rec["crop_xywh"]]}
    case("SGBM: the full-raster window's central crop equals the accepted compute_natural output bitwise", crop_equal)

    def determinism():
        rec2, _, _ = SG.compute_sgbm(base_c, base_rgb)
        diff = [k for k in base_rec if not np.array_equal(base_rec[k], rec2[k], equal_nan=np.asarray(rec2[k]).dtype.kind == "f")]
        return not diff, {"differing_arrays": diff}
    case("SGBM: two computations of the same input are bitwise identical", determinism)

    def recorder():
        import ab1d3_run as RUN
        ok, p = RUN.calls_ok(base_calls)
        return ok and not K.audit_calls(base_calls), {"run_check": p, "checker_audit": K.audit_calls(base_calls),
                                                      "getters": [e["getters"] for e in base_calls["calls"]["StereoSGBM_create"]]}
    case("SGBM: the recorder observes exactly the frozen configuration (2 objects, getters, 640 x 640 uint8, rectify)",
         recorder)

    def audit_null():
        bad, det = K.audit_record(base_c, base_rgb, base_rec)
        return not bad and not K.audit_summary(base_summ), {"record": bad, "summary": K.audit_summary(base_summ), **det}
    case("checker: null probe -- the audit raises nothing on the unmutated synthetic run", audit_null)

    def band():
        det = {}
        tex, (lo, hi) = band_texture()
        p = SP.SYN_REPEAT
        for g, c in cals.items():
            r, rgb, truth = plane_scene(c, tex=tex, spacing=p["spacing_m"])
            d_true = -float(r["P2"][0, 3]) / SP.SYN_PLANE_Z_M
            n = AR.rect_axis_h(c, r)
            foot = np.asarray(c["eyes"][0]["centre_h_m"]) + n * SP.SYN_PLANE_Z_M
            a = FG.unit(np.cross(n, [0.0, 1.0, 0.0]))
            b = np.cross(n, a)
            rows, cols, _ = SG.core_grid()
            pos = FG.world_to_head(c, truth["position_w_L"][rows + SP.CORE_ORIGIN, cols + SP.CORE_ORIGIN].astype(float))
            sy = (pos - foot) @ b / p["spacing_m"] + p["texture_n"] / 2
            inb = (sy >= lo + p["margin_texels"]) & (sy < hi - p["margin_texels"])
            outb = (sy < lo - p["margin_texels"]) | (sy >= hi + p["margin_texels"])
            res = {}
            for name, kw in (("frozen", {}), ("P1=P2=0 control", {"P1": 0, "P2": 0})):
                with sgbm_override(**kw):
                    rec, _, _ = SG.compute_sgbm(c, rgb)
                out, _ = SG.adapt(c, rec)
                v = out["valid_adapter"]
                e = np.abs(out["disparity_bilinear_px"] - d_true)
                res[name] = {"disc": rec["disparity_sgbm_px"],
                             "in_band_valid": float((v & inb).sum() / inb.sum()),
                             "in_band_correct": float((v & inb & (e <= 1)).sum() / inb.sum()),
                             "in_band_wrong": float((v & inb & (e > 1)).sum() / inb.sum()),
                             "outside_correct": float((v & outb & (e <= 1)).sum() / outb.sum())}
            f, k = res["frozen"], res["P1=P2=0 control"]
            det[g] = {"band_pixels": int(inb.sum()), "outside_pixels": int(outb.sum()),
                      "aggregation_changes_output": not np.array_equal(f["disc"], k["disc"]),
                      **{f"{nm}_{kk}": vv for nm, rr in (("frozen", f), ("control", k)) for kk, vv in rr.items()
                         if kk != "disc"}}
        ok = all(d["aggregation_changes_output"] and d["frozen_outside_correct"] - d["control_outside_correct"]
                 >= SP.SYN_REPEAT_OUTSIDE_GAIN and d["frozen_in_band_wrong"] <= SP.SYN_REPEAT_BAND_WRONG_MAX
                 and d["frozen_in_band_wrong"] <= d["control_in_band_wrong"] for d in det.values())
        return ok, {"per_gaze": det, "texture": SP.SYN_REPEAT,
                    "descriptive": "semi-global aggregation is active: it changes the output, adds correct matches on "
                                   "unique texture and suppresses false matches in the periodic band; it does NOT "
                                   "recover the periodic band itself (in-band correct is recorded, not required)"}
    case("SGBM: periodic band in unique texture -- semi-global aggregation acts (vs a P1 = P2 = 0 control)", band)

    def subpixel():
        c = cals["gaze-2"]
        r = FS.rectification(c)
        z = -float(r["P2"][0, 3]) / SP.SYN_SUBPIXEL_D_PX
        r, rgb, truth = plane_scene(c, z=z, seed=4)
        rec, _, _ = SG.compute_sgbm(c, rgb)
        out, _ = SG.adapt(c, rec)
        v = out["valid_adapter"]
        e = out["disparity_bilinear_px"][v] - SP.SYN_SUBPIXEL_D_PX
        sup = rec["term_sgbm_left"] & rec["term_support_left"]
        delta = rec["disparity_px"].astype(float) - rec["disparity_sgbm_px"].astype(float)
        e_disc = out["disparity_sgbm_bilinear_px"][v] - SP.SYN_SUBPIXEL_D_PX
        det = {"z_m": z, "valid_fraction_core": float(v.mean()), "median_refined_error_px": float(np.median(e)),
               "median_abs_refined_error_px": float(np.median(np.abs(e))),
               "median_abs_discrete_error_px": float(np.median(np.abs(e_disc))),
               "refinement_max_abs_px": float(np.max(np.abs(delta[sup]))),
               "refinement_median_abs_px": float(np.median(np.abs(delta[sup]))),
               "unsupported_unchanged": bool(np.all(delta[~sup] == 0))}
        ok = (det["valid_fraction_core"] >= SP.SYN_MIN_VALID and abs(det["median_refined_error_px"])
              <= SP.SYN_MAX_MEDIAN_DISPARITY_PX and det["refinement_max_abs_px"] <= SP.SYN_REFINE_MAX_PX
              and det["refinement_median_abs_px"] > 0 and det["unsupported_unchanged"])
        return ok, det
    case("SGBM: known sub-pixel disparity 40.3 px recovered; refinement active and bounded (<= 0.75 px)", subpixel)

    def swapped():
        r, rgb, truth = plane_scene(fwd, seed=5)
        sw = {"rgb_L": rgb["rgb_R"], "rgb_R": rgb["rgb_L"]}
        rec, _, _ = SG.compute_sgbm(fwd, sw)
        m = plane_metrics(fwd, r, rec, truth, SP.SYN_PLANE_Z_M)
        return not plane_ok(m), m
    case("SGBM mutation: wrong eye order (L and R swapped) must fail the plane known answer", swapped)

    def adapter_mut(variant, label):
        def fn():
            m = plane_metrics(base_c, base_r, base_rec, base_truth, SP.SYN_PLANE_Z_M, variant)
            return not plane_ok(m), {"variant": label, **m}
        return fn
    case("adapter mutation on the SGBM scene: disparity sign flipped must fail", adapter_mut({"disparity_sign": -1.0},
                                                                                            "sign"))
    case("adapter mutation on the SGBM scene: wrong R2 (transposed) must fail", adapter_mut({"r2_transposed": True}, "R2^T"))

    def detects(label, ctx_fn, variant=None, calib=None):
        def fn():
            c = calib if calib is not None else base_c
            with ctx_fn():
                rec, summ, calls = SG.compute_sgbm(c, base_rgb, variant)
            bad_rec, det = K.audit_record(base_c, base_rgb, rec)
            bad = {"calls": K.audit_calls(calls), "summary": K.audit_summary(summ), "record": bad_rec}
            return any(bad.values()), {"mutation": label, "detected_by": bad}
        return fn
    null = contextlib.nullcontext
    case("checker detects: changed block size (7)", detects("blockSize 7", null, {"block_size": 7}))
    case("checker detects: changed uniquenessRatio (15)", detects("uniquenessRatio 15", null, {"uniqueness_ratio": 15}))
    case("checker detects: changed P1 / P2 (400 / 1600)", detects("P1 400, P2 1600",
                                                                  lambda: sgbm_override(P1=400, P2=1600)))
    case("checker detects: changed SGBM mode (MODE_SGBM)", detects("mode SGBM", lambda: sgbm_override(mode=0)))
    case("checker detects: changed disparity range (numDisparities 128)",
         detects("numDisparities 128", lambda: sgbm_override(numDisparities=128)))
    zc = json.loads(json.dumps(base_c))
    zc["depth_search_z_rect_m"] = [0.5, 6.0]
    case("checker detects: changed z interval (0.5 .. 6 m)", detects("z 0.5..6", null, None, zc))
    case("checker detects: disabled LR consistency", detects("use_lr False", null, {"use_lr": False}))
    case("checker detects: changed texture threshold (2.0 u8)",
         detects("MIN_LOCAL_STD_U8 2.0", lambda: patched(FS, "MIN_LOCAL_STD_U8", 2.0)))
    case("checker detects: enabled speckle filtering (window 100, range 2)",
         detects("speckle 100/2", lambda: sgbm_override(speckleWindowSize=100, speckleRange=2)))
    case("checker detects: changed refinement (5 iterations, 2.0 px bound)",
         detects("refinement 5 / 2.0", lambda: patched(FS, "refine_disparity", refine_changed)))

    # ---- the evaluation code on a synthetic scene with a synthetic oracle (fail-capable)
    def evaluation_known_answer():
        import ab1d_match as M
        import ab1d3_run as RUN
        det = {}
        for k, g in enumerate(SP.GAZES):
            c = cals[g]
            r = FS.rectification(c)
            gz = FG.gaze_direction(*c["gaze_yaw_pitch_deg"])
            planes = [{"n": AR.rect_axis_h(c, r), "z": 6.0, "tex": AR.noise_texture(11 + k), "spacing": 0.006},
                      {"n": gz, "z": 2.0 + 0.3 * k, "tex": AR.noise_texture(21 + k), "half": (0.14, 1.0)}]
            rgb, truth = AR.render_planes(c, planes)
            rec, _, _ = SG.compute_sgbm(c, rgb)
            out, prod = SG.adapt(c, rec)
            rows, cols, uv_l = SG.core_grid()
            x = FG.world_to_head(c, truth["position_w_L"][rows + SP.CORE_ORIGIN, cols + SP.CORE_ORIGIN].astype(float))
            uv_r, zc = FG.project_h(c["eyes"][1], x)
            ri = np.clip(np.rint(uv_r).astype(int), 0, SP.RAW_SIZE - 1)
            xr = FG.world_to_head(c, truth["position_w_R"][ri[:, 1], ri[:, 0]].astype(float))
            seen = ((truth["instance_L"][rows + SP.CORE_ORIGIN, cols + SP.CORE_ORIGIN] > 0) & (zc > 0)
                    & (uv_r >= 0).all(1) & (uv_r <= SP.RAW_SIZE - 1).all(1) & (np.linalg.norm(xr - x, axis=1) < 0.01))
            ora = {"left_core_row": rows[seen].astype(np.int32), "left_core_col": cols[seen].astype(np.int32),
                   "uv_L": uv_l[seen], "uv_R": uv_r[seen]}
            perf = BG.compute_epipolar(c, ora)
            oi = rows[seen] * SP.CORE_SIZE + cols[seen]
            cls = np.full(SP.CORE_SIZE ** 2, 3, np.int8)
            cls[oi] = 0
            pe = np.where(oi % 3 == 0, 0.3, np.where(oi % 3 == 1, 4.0, 80.0))
            prim = {"core_index": oi.astype(np.int32), "e_px": pe, "error_3d_vs_perfect_m": pe * 0.03, "class_map": cls}
            far = np.zeros(SP.CORE_SIZE ** 2, bool)
            far[rows * SP.CORE_SIZE + cols] = truth["instance_L"][rows + SP.CORE_ORIGIN, cols + SP.CORE_ORIGIN] == 1
            res = {}
            for name, shift in (("frozen", 0.0), ("uv_R shifted +2 px (must show)", 2.0)):
                o2 = dict(out)
                p2 = {kk: vv.copy() for kk, vv in prod.items()}
                p2["uv_R"][:, 0] += shift
                geo = BG.compute_epipolar(c, p2)
                summ, arr = RUN.evaluation_core(c, rec, o2, geo, ora, perf, truth["position_w_L"], prim, M)
                cats = summ["comparison_ab1d2"]["categories_on_full_oracle"]
                res[name] = {"median_abs_px": summ["primary"]["px_equivalent_abs"]["median"],
                             "serviceable": int(arr["serviceable_mask"].sum()),
                             "serviceable_on_far_plane": int((arr["serviceable_mask"] & far).sum()),
                             "far_plane_oracle": int((arr["oracle_mask"] & far).sum()),
                             "valid_on_far_plane": int((arr["sgbm_valid_mask"] & far).sum()),
                             "focal_ratio_median": float(np.median(np.abs(arr["e_focal_px"]) / np.abs(arr["e_px"]))),
                             "categories_partition": sum(v["count"] for v in cats.values()) == int(arr["oracle_mask"].sum()),
                             "primitive_correct_fraction": summ["comparison_ab1d2"]["primitive_ab1d2"]["within_px_precision"]["1"],
                             "precision_12mm": summ["metric"]["vs_perfect"]["within_m"]["0.012"]["precision"],
                             "effective_12mm": summ["metric"]["vs_perfect"]["within_m"]["0.012"]["effective_oracle_coverage"],
                             "secondary_max_m": summ["secondary"]["planar_q_vs_spherical_m"]["max"]}
            det[g] = res
        ok = True
        for g, res in det.items():
            f, s = res["frozen"], res["uv_R shifted +2 px (must show)"]
            ok &= (f["serviceable_on_far_plane"] == 0 and f["far_plane_oracle"] > 1000
                   and f["valid_on_far_plane"] <= 0.01 * f["far_plane_oracle"] and f["median_abs_px"] <= 0.2
                   and 0.95 <= f["focal_ratio_median"] <= 1.05 and f["categories_partition"]
                   and abs(f["primitive_correct_fraction"] - 1 / 3) < 0.01 and f["effective_12mm"] <= f["precision_12mm"]
                   and f["secondary_max_m"] <= 1e-9 and 1.8 <= s["median_abs_px"] <= 2.2)
        return bool(ok), {"per_gaze": det, "scene": "a gaze-normal textured plane at 2.0 / 2.3 / 2.6 m (half-width 0.14 m) "
                                                    "in front of a plane at z_rect 6 m (beyond the frozen 4.5 m)"}
    case("evaluation: synthetic two-plane scene with a synthetic oracle -- serviceable set, errors, categories, metric; "
         "a +2 px shift shows as ~2 px", evaluation_known_answer)

    # ---- the truth firewall
    probe_dir = out_dir / "guard-probe"
    if probe_dir.exists():
        shutil.rmtree(probe_dir)
    (probe_dir / "acq").mkdir(parents=True)
    (probe_dir / "evaluation_only").mkdir()
    cal_p = probe_dir / "acq/calibration.json"
    cal_p.write_text(json.dumps(base_c))
    rgb_p = probe_dir / "acq/rgb-observation.npz"
    np.savez_compressed(rgb_p, **base_rgb)
    pos_p = probe_dir / "evaluation_only/reference-observation.npz"
    np.savez_compressed(pos_p, position_w_L=np.zeros((2, 2, 3), np.float32))
    ora_p = probe_dir / "oracle-correspondences.npz"
    np.savez_compressed(ora_p, left_core_row=np.zeros(1, np.int32))

    def truth_input():
        det = {}
        bad = probe_dir / "acq-truth.npz"
        np.savez_compressed(bad, **base_rgb, position_w_L=np.zeros((640, 640, 3), np.float32))
        try:
            AS.load_observation(bad)
            det["npz_with_position"] = "accepted"
        except ValueError as e:
            det["npz_with_position"] = f"refused: {e}"
        try:
            SG.compute_sgbm(base_c, {**base_rgb, "instance_L": np.zeros((640, 640), np.int32)})
            det["dict_with_instance"] = "accepted"
        except ValueError as e:
            det["dict_with_instance"] = f"refused: {e}"
        bad.unlink()
        return all(v.startswith("refused") for v in det.values()), det
    case("firewall: a truth-bearing matcher input (Position / Object Index keys) is refused", truth_input)

    def guarded_positive():
        out = probe_dir / "sgbm-ok"
        summ = SG.run_sgbm_gaze(cal_p, rgb_p, out)
        rec = json.loads((out / "sgbm-opened-files.json").read_text())
        want = {str(cal_p.resolve()), str(rgb_p.resolve())}
        calls = json.loads((out / "sgbm-calls.json").read_text())
        ok = set(rec["data_reads"]) == want and not rec["violations"] and not K.audit_calls(calls) and summ is not None
        return ok, {"data_reads": rec["data_reads"], "violations": rec["violations"]}
    case("firewall positive control: the guarded SGBM stage reads exactly the calibration and the RGB", guarded_positive)

    def guarded_probe(kind):
        def fn():
            path = pos_p if kind == "position" else ora_p
            out = probe_dir / f"sgbm-probe-{kind}"

            def probe():
                with open(path, "rb") as f:
                    f.read(1)
            refused = False
            try:
                SG.run_sgbm_gaze(cal_p, rgb_p, out, probe=probe)
            except PermissionError:
                refused = True
            rec = json.loads((out / "sgbm-opened-files.json").read_text())
            n = rec["position_reads"] if kind == "position" else rec["oracle_reads"]
            return refused and len(rec["violations"]) == 1 and n == 1 and not (out / "sgbm-record.npz").exists(), {
                "refused": refused, "violations": rec["violations"], "counted_reads": n}
        return fn
    case("firewall: a Position read inside the SGBM stage is refused and counted", guarded_probe("position"))
    case("firewall: an oracle read inside the SGBM stage is refused and counted", guarded_probe("oracle"))

    def adapter_probe():
        out = probe_dir / "adapter-probe"
        sgbm_rec = probe_dir / "sgbm-ok/sgbm-record.npz"

        def probe():
            with open(ora_p, "rb") as f:
                f.read(1)
        refused = False
        try:
            SG.run_adapter_gaze(cal_p, sgbm_rec, out, probe=probe)
        except PermissionError:
            refused = True
        rec = json.loads((out / "adapter-opened-files.json").read_text())
        return refused and rec["oracle_reads"] == 1 and not (out / "sgbm-correspondences.npz").exists(), {
            "refused": refused, "violations": rec["violations"]}
    case("firewall: an oracle read inside the adapter stage is refused and counted", adapter_probe)

    def unfrozen():
        out = probe_dir / "spherical-unfrozen"
        sgbm_rec = probe_dir / "sgbm-ok/sgbm-record.npz"
        SG.run_adapter_gaze(cal_p, sgbm_rec, probe_dir / "adapter-ok")
        try:
            AD.run_spherical_gaze(cal_p, probe_dir / "adapter-ok/sgbm-correspondences.npz", out,
                                  probe_dir / "adapter-ok/correspondence-freeze.json")
            return False, {"refused": False}
        except RuntimeError as e:
            return True, {"refused": str(e)}
    case("firewall: the spherical geometry refuses an unfrozen correspondence product", unfrozen)

    rep = {"schema": "AB1d3-preflight-v1", "truth": SP.TRUTH_DERIVED,
           "statement": "PREFLIGHT KNOWN ANSWERS: calibration-only adapter tests on the three accepted calibrations and "
                        "SGBM tests on analytic synthetic planes; no Classroom pixel, no Position, no oracle",
           "cases": cases, "passed": all(x["passed"] for x in cases), "seconds": round(time.time() - t0, 1),
           "tolerances": {k: getattr(SP, k) for k in dir(SP) if k.startswith(("KA_", "SYN_"))}}
    return rep
