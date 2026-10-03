"""Active Bootstrap-1a: the natural RGB-only local stereo matcher and the calibration-only pre-look geometry.

Contract: docs/active-bootstrap/ab1a-first-natural-stereo-look-contract.md, sections 5, 7 and 8.

The input is exactly the calibration and one binocular RGB observation holding ``rgb_L`` and ``rgb_R``.  The
mechanics are the accepted FSG ones, reused read-only from ``tools/fsg_stereo.py`` (rectification, remap,
calibration support, SGBM 3WAY, bounded photometric refinement, linear-to-u8): left-right consistency, calibration
support, the texture gate, the fixed z_rect interval and the disparity ROI.  The accepted truth-assisted path of
``fsg_stereo`` is never called, and support is calibration-derived only: there is no identity boundary guard.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "natural_bootstrap"))

import ab1a_spec as SP  # noqa: E402
import fsg_geometry as FG  # noqa: E402  (accepted sensor geometry, read-only)
import fsg_stereo as FS  # noqa: E402  (accepted stereo primitives, read-only)
from nb1a_guard import OpenGuard  # noqa: E402  (accepted allowlist file-open guard, read-only)

RECT_KEYS = ("R1", "R2", "P1", "P2", "Q_full", "Q_core", "crop_xywh", "roi_L", "roi_R", "min_disparity",
             "num_disparities")


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, data) -> None:
    Path(path).write_text(json.dumps(data, indent=1, sort_keys=True, allow_nan=False) + "\n")


def config_sha256() -> str:
    return hashlib.sha256(json.dumps(SP.MATCHER, sort_keys=True).encode()).hexdigest()


def verify_inherited() -> dict:
    """STOP unless the reused accepted sources and constants are exactly the frozen instrument."""
    bad = {p: sha256(SP.REPO / p) for p in ("tools/fsg_geometry.py", "tools/fsg_stereo.py")
           if sha256(SP.REPO / p) != SP.SOURCE_PINS[p]}
    got = {"block_size": FS.BLOCK_SIZE, "lr_tolerance_px": FS.LR_TOLERANCE_PX,
           "uniqueness_ratio": FS.UNIQUENESS_RATIO, "minimum_local_std_u8": FS.MIN_LOCAL_STD_U8,
           "CORE_FOV_DEG": FG.CORE_FOV_DEG, "core_size": FG.CORE_SIZE[SP.PROFILE], "ipd_m": FG.DEFAULT_IPD}
    want = {"block_size": SP.MATCHER["block_size"], "lr_tolerance_px": SP.MATCHER["lr_tolerance_px"],
            "uniqueness_ratio": SP.MATCHER["uniqueness_ratio"],
            "minimum_local_std_u8": SP.MATCHER["minimum_local_std_u8"], "CORE_FOV_DEG": SP.CORE_FOV_DEG,
            "core_size": SP.CORE_SIZE, "ipd_m": SP.IPD_M}
    if bad or got != want:
        raise SystemExit(f"[ab1a] STOP inherited instrument differs: sources {bad}; constants {got} != {want}")
    return got


@contextlib.contextmanager
def _instrument(variant: dict):
    """The accepted SGBM factory reads its block size and uniqueness from ``fsg_stereo``; a mutation variant
    (the corruption suite only) swaps them for the duration of one computation."""
    saved = (FS.BLOCK_SIZE, FS.UNIQUENESS_RATIO)
    FS.BLOCK_SIZE = int(variant.get("block_size", saved[0]))
    FS.UNIQUENESS_RATIO = int(variant.get("uniqueness_ratio", saved[1]))
    try:
        yield
    finally:
        FS.BLOCK_SIZE, FS.UNIQUENESS_RATIO = saved


def validate_rgb(c: dict, obs: dict) -> None:
    if set(obs) != set(SP.RGB_KEYS):
        raise ValueError(f"the natural observation must hold exactly {list(SP.RGB_KEYS)}, not {sorted(obs)}")
    w, h = c["image_size_wh"]
    for side in ("L", "R"):
        a = np.asarray(obs["rgb_" + side])
        if a.shape != (h, w, 3) or not np.isfinite(a).all():
            raise ValueError(f"rgb_{side}: shape {a.shape} or non-finite values")


def compute_natural(c: dict, obs: dict, variant: dict | None = None) -> tuple[dict, dict]:
    """Natural RGB-only local stereo for one binocular tangent observation.  ``variant`` exists only for the
    corruption suite (block_size, uniqueness_ratio, use_lr, use_texture)."""
    v = dict(variant or {})
    t0 = time.perf_counter()
    FG.validate_calibration(c)
    validate_rgb(c, obs)
    w, h = c["image_size_wh"]
    with _instrument(v):
        r = FS.rectification(c)
        colours, gray, support = {}, {}, {}
        for side in ("L", "R"):
            colours[side] = FS.remap(np.asarray(obs["rgb_" + side], np.float32), r, side, cv2.INTER_LINEAR)
            gray[side] = cv2.cvtColor(FS.linear_to_u8(colours[side]), cv2.COLOR_RGB2GRAY)
            support[side] = FS.support_mask(c, r, side)
        nd, minimum = int(r["num_disparities"]), int(r["min_disparity"])
        # OpenCV returns 1/16-pixel fixed point; its invalid value is (minDisparity - 1) * 16.
        dl_raw = FS.matcher(minimum, nd).compute(gray["L"], gray["R"])
        min_right = -(minimum + nd - 1)
        dr_raw = FS.matcher(min_right, nd).compute(gray["R"], gray["L"])
        dl, dr = dl_raw.astype(np.float32) / 16., dr_raw.astype(np.float32) / 16.
        vl, vr = dl_raw > (minimum - 1) * 16, dr_raw > (min_right - 1) * 16
        dl_discrete = dl.copy()
        dl = FS.refine_disparity(colours["L"], colours["R"], dl, vl & support["L"])
        dr = FS.refine_disparity(colours["R"], colours["L"], dr, vr & support["R"])
        uv = FG.pixels(w, h)
        ur = uv[..., 0] - dl
        vv = uv[..., 1].astype(np.float32)
        xr = ur.astype(np.float32)
        dr_at = cv2.remap(dr, xr, vv, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        vr_at = cv2.remap((vr & support["R"]).astype(np.float32), xr, vv, cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=0) > .999
        lr = np.abs(dl + dr_at)
        m = gray["L"].astype(np.float32)
        std = np.sqrt(np.maximum(cv2.boxFilter(m * m, -1, (5, 5)) - cv2.boxFilter(m, -1, (5, 5)) ** 2, 0.))
        rect_xyz = FG.reproject_q(r["Q_full"], uv, dl)
        z = rect_xyz[..., 2]
        lo, hi = c["depth_search_z_rect_m"]
        roi = cv2.getValidDisparityROI(tuple(r["roi_L"]), tuple(r["roi_R"]), minimum, nd, FS.BLOCK_SIZE)
        gx, gy, gw, gh = roi
        roi_mask = np.zeros((h, w), bool)
        roi_mask[gy:gy + gh, gx:gx + gw] = True
        with np.errstate(invalid="ignore"):
            terms = {
                "term_sgbm_left": vl,
                "term_right_valid": vr_at,
                "term_support_left": support["L"],
                "term_inside_raster": (ur >= 0) & (ur < w - 1),
                "term_lr": (lr <= FS.LR_TOLERANCE_PX) if v.get("use_lr", True) else np.ones((h, w), bool),
                "term_texture": (std >= FS.MIN_LOCAL_STD_U8) if v.get("use_texture", True) else np.ones((h, w), bool),
                "term_finite": np.isfinite(rect_xyz).all(axis=-1),
                "term_z_range": (z >= lo) & (z <= hi),
                "term_roi": roi_mask,
            }
        valid = np.ones((h, w), bool)
        for name in SP.TERMS:
            valid &= terms[name]
        xyz_h = FG.rect_to_head(c, r["R1"], np.where(np.isfinite(rect_xyz), rect_xyz, np.nan))
        eye_range = np.linalg.norm(xyz_h - np.asarray(c["eyes"][0]["centre_h_m"]), axis=-1)
        x, y, cw, ch = map(int, r["crop_xywh"])
        sl = np.s_[y:y + ch, x:x + cw]
        keep = valid[sl]
        point = xyz_h[sl].astype(np.float32)
        point[~keep] = np.nan
        record = {k: np.asarray(r[k]) for k in RECT_KEYS}
        record.update({
            "valid_disparity_roi": np.asarray(roi, np.int32),
            "disparity_px": dl[sl], "disparity_sgbm_px": dl_discrete[sl], "valid": keep, "xyz_h": point,
            "range_left_m": np.where(keep, eye_range[sl], np.nan).astype(np.float32),
            "z_rect_m": np.where(keep, z[sl], np.nan).astype(np.float32),
            "lr_error_px": lr[sl], "left_gray_std": std[sl],
            "rgb_left": colours["L"][sl], "rgb_right": colours["R"][sl],
            "raw_support_L": support["L"][sl],
        })
        record.update({k: terms[k][sl] for k in SP.TERMS})
        config = {**SP.MATCHER, "variant": v, "min_disparity": minimum, "num_disparities": nd,
                  "block_size_used": FS.BLOCK_SIZE, "uniqueness_ratio_used": FS.UNIQUENESS_RATIO,
                  "rectified_focal_px": float(r["P1"][0, 0]), "crop_xywh": [int(a) for a in r["crop_xywh"]],
                  "valid_disparity_roi": [int(a) for a in roi]}
    summary = summarize(record, config, time.perf_counter() - t0)
    return record, summary


def _dist(a) -> dict | None:
    a = np.asarray(a, np.float64).ravel()
    a = a[np.isfinite(a)]
    if a.size == 0:
        return None
    return {k: float(np.quantile(a, q)) for k, q in SP.SUMMARY_QUANTILES.items()} | {"count": int(a.size)}


def summarize(rec: dict, config: dict, seconds: float) -> dict:
    keep = rec["valid"]
    n = int(keep.size)
    attrition, run = [], np.ones_like(keep)
    for name in SP.TERMS:
        run = run & rec[name]
        attrition.append({"term": name, "passes_alone": int(rec[name].sum()), "remaining_after": int(run.sum())})
    xyz = rec["xyz_h"][keep].astype(np.float64)
    bbox = None if not len(xyz) else {"min": xyz.min(0).tolist(), "max": xyz.max(0).tolist(),
                                       "extent": (xyz.max(0) - xyz.min(0)).tolist()}
    sgbm = rec["term_sgbm_left"]
    return {
        "schema": "AB1a-stereo-summary-v1", "truth": SP.TRUTH_DERIVED,
        "statement": "natural RGB-only local stereo at frozen NB1c RGB gaze #1; descriptive pre-evaluation "
                     "measurement; calibration-derived support only; no identity guard",
        "valid_count": int(keep.sum()), "core_pixels": n, "valid_fraction_core": float(keep.mean()),
        "sgbm_valid_core": int(sgbm.sum()),
        "finite_refined_disparity_core": int((np.isfinite(rec["disparity_px"]) & sgbm).sum()),
        "term_attrition": attrition,
        "disparity_px_valid": _dist(rec["disparity_px"][keep]),
        "range_left_m_valid": _dist(rec["range_left_m"][keep]),
        "z_rect_m_valid": _dist(rec["z_rect_m"][keep]),
        "lr_error_px_sgbm_valid": _dist(rec["lr_error_px"][sgbm]),
        "lr_error_px_valid": _dist(rec["lr_error_px"][keep]),
        "left_gray_std_core": _dist(rec["left_gray_std"]),
        "left_gray_std_valid": _dist(rec["left_gray_std"][keep]),
        "xyz_h_bbox_valid_m": bbox,
        "seconds": round(float(seconds), 4),
        "matcher": config, "matcher_config_sha256": config_sha256(),
        "opencv": cv2.__version__, "numpy": np.__version__,
        "point_frame": "H: fixed head; +X right, +Y up, -Z forward; metres",
        "quality_note": "LR residual and texture are diagnostics, not calibrated uncertainty",
    }


# ------------------------------------------------------------------ pre-look geometry (section 5)
def leverage(yaw: float, pitch: float) -> dict:
    d = FG.gaze_direction(yaw, pitch)
    b = np.asarray(SP.BASELINE_H, float)
    bd = float(b @ d)
    lev = math.sqrt(max(0.0, 1.0 - bd * bd))
    return {"gaze_direction_h": d.tolist(), "b_dot_d": bd, "angle_to_baseline_deg": math.degrees(math.acos(abs(bd))),
            "L": lev, "B_perp_m": SP.IPD_M * lev,
            "formula": "L = sqrt(1 - (b . d)^2), b = (1, 0, 0); B_perp = IPD * L"}


def prelook_geometry(c: dict) -> dict:
    """Calibration-only diagnostics of the accepted instrument at this gaze; no scene data."""
    yaw, pitch = c["gaze_yaw_pitch_deg"]
    out = leverage(yaw, pitch)
    d = np.asarray(out["gaze_direction_h"])
    r = FS.rectification(c)
    w, h = c["image_size_wh"]
    x, y, cw, ch = map(int, r["crop_xywh"])
    core = c["core_size"]
    nominal = ((w - core) // 2, (h - core) // 2)
    eyes = {}
    for i, side in enumerate(("L", "R")):
        eye = c["eyes"][i]
        rr, pp = np.asarray(r["R1" if side == "L" else "R2"]), np.asarray(r["P1" if side == "L" else "P2"])
        r_hc = np.asarray(eye["R_hc"], float)
        z_cam = FG.unit(d * c["prescribed_vergence_distance_m"] - np.asarray(eye["centre_h_m"], float))
        b = np.asarray(SP.BASELINE_H, float)
        x_expected = FG.unit(b - (b @ z_cam) * z_cam)
        u0 = np.array([x + (cw - 1) / 2, y + (ch - 1) / 2])
        ray_rect = np.array([(u0[0] - pp[0, 2]) / pp[0, 0], (u0[1] - pp[1, 2]) / pp[1, 1], 1.0])
        u_z = float(1.0 / np.linalg.norm(ray_rect))
        ray_h = FG.unit((ray_rect @ rr) @ r_hc.T)
        mx, my = r["map_" + side + "x"][y:y + ch, x:x + cw], r["map_" + side + "y"][y:y + ch, x:x + cw]
        in_nominal = ((mx >= nominal[0] - 0.5) & (mx <= nominal[0] + core - 0.5)
                      & (my >= nominal[1] - 0.5) & (my <= nominal[1] + core - 0.5))
        lo, hi = c["depth_search_z_rect_m"]
        eyes[side] = {
            "camera_x_axis_h": r_hc[:, 0].tolist(), "expected_baseline_projected_x_h": x_expected.tolist(),
            "rectification_rotation_deg": math.degrees(math.acos(float(np.clip((np.trace(rr) - 1) / 2, -1, 1)))),
            "rectified_principal_point_px": [float(pp[0, 2]), float(pp[1, 2])],
            "rectified_core_centre_direction_h": ray_h.tolist(),
            "rectified_core_centre_from_gaze_deg": math.degrees(math.acos(float(np.clip(ray_h @ d, -1, 1)))),
            "rectified_core_centre_from_baseline_deg": math.degrees(math.acos(float(min(1.0, abs(ray_h[0]))))),
            "rectified_core_centre_u_z": u_z,
            "range_admitted_at_core_centre_m": [lo / u_z, hi / u_z],
            "raw_source_of_rectified_core_px": {"x": [float(mx.min()), float(mx.max())],
                                                "y": [float(my.min()), float(my.max())]},
            "rectified_core_pixels_from_nominal_raw_core": int(in_nominal.sum()),
            "calibration_support_in_core": int(FS.support_mask(c, r, side)[y:y + ch, x:x + cw].sum()),
        }
    out.update({
        "schema": "AB1a-prelook-geometry-v1", "truth": SP.TRUTH_DERIVED,
        "statement": "PRE-LOOK GEOMETRY: calibration-only diagnostics, recorded before acquisition; they do not veto, "
                     "move or replace the gaze and do not modify vergence or any matcher parameter",
        "gaze_yaw_pitch_deg": [yaw, pitch], "tangent_frame": c.get("tangent_frame", "legacy_upright"),
        "ipd_m": c["ipd_m"], "rectified_focal_px": float(r["P1"][0, 0]), "P2_0_3": float(r["P2"][0, 3]),
        "rectified_baseline_m": float(np.linalg.norm(np.subtract(c["eyes"][1]["centre_h_m"], c["eyes"][0]["centre_h_m"]))),
        "num_disparities": int(r["num_disparities"]), "crop_xywh": [int(a) for a in r["crop_xywh"]],
        "core_pixels": int(cw * ch), "eyes": eyes,
        "max_disparity_for_z_rect_min_px": float(-r["P2"][0, 3] / c["depth_search_z_rect_m"][0]),
    })
    return out


# ------------------------------------------------------------------ the guarded measurement (sections 7-8)
def load_observation(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        names = set(z.files)
        if names != set(SP.RGB_KEYS):
            raise ValueError(f"the natural observation must hold exactly {list(SP.RGB_KEYS)}, not {sorted(names)}")
        return {k: np.asarray(z[k]) for k in SP.RGB_KEYS}


def measure_dir(acq: Path, out: Path, variant: dict | None = None, probe: Path | None = None) -> tuple[dict, dict]:
    """Run the natural matcher on ``acq/calibration.json`` + ``acq/rgb-observation.npz`` under the allowlist guard.
    ``probe`` exists only for the synthetic truth-guard test: it is opened inside the guard and must be refused."""
    calib, rgbp = acq / "calibration.json", acq / "rgb-observation.npz"
    out.mkdir(parents=True, exist_ok=True)
    summary: dict = {}
    g = OpenGuard("measurement", [calib, rgbp], [out])
    try:
        with g:
            c = json.loads(calib.read_text())
            obs = load_observation(rgbp)
            if probe is not None:
                with open(probe, "rb") as f:
                    f.read(1)
            rec, summary = compute_natural(c, obs, variant)
            summary["inputs_sha256"] = {"calibration.json": sha256(calib), "rgb-observation.npz": sha256(rgbp)}
            np.savez_compressed(out / "stereo-result.npz", **rec)
            write_json(out / "stereo-summary.json", summary)
    finally:
        record = g.record()
        record["truth_firewall_violations"] = len(record["violations"])
        write_json(out / "measurement-opened-files.json", record)
    return summary, record
