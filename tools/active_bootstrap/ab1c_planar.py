"""Active Bootstrap-1c: conventional planar tangent / projective stereo geometry with perfect correspondence.

Contract: docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-contract.md, sections 9, 9a and 13.  The input is
exactly the calibration and the frozen, truth-stripped correspondence product (the SAME product the spherical geometry
consumes).  The rectification is the accepted ``fsg_stereo.rectification`` (cv2.stereoRectify, CALIB_ZERO_DISPARITY,
alpha = -1, newImageSize = raster), read-only and never tuned per gaze; the reconstruction is the accepted Q reprojection
(``fsg_geometry.reproject_q``) and ``fsg_geometry.rect_to_head``.  The support diagnostic is the accepted AB1a pre-look
geometry (``ab1a_stereo.prelook_geometry``).  No SGBM, no matcher, no image remap of scene data, no truth.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent / "natural_bootstrap"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ab1a_stereo as AS  # noqa: E402  (accepted AB1a pre-look support diagnostic, read-only)
import ab1b_geometry as BG  # noqa: E402  (accepted product schema and quantiles, read-only)
import ab1c_spec as SP  # noqa: E402
import fsg_geometry as FG  # noqa: E402  (accepted sensor geometry, read-only)
import fsg_stereo as FS  # noqa: E402  (accepted planar rectification, read-only)
from nb1a_guard import OpenGuard  # noqa: E402  (accepted allowlist file-open guard, read-only)

RECT_KEYS = ("R1", "R2", "P1", "P2", "Q_full")


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, data) -> None:
    Path(path).write_text(json.dumps(data, indent=1, sort_keys=True, allow_nan=False) + "\n")


def rotation_deg(r) -> float:
    return float(np.degrees(np.arccos(np.clip((np.trace(np.asarray(r, np.float64)) - 1.0) / 2.0, -1.0, 1.0))))


# ------------------------------------------------------------------ the geometry (section 9)
def rectify(c: dict) -> dict:
    """The accepted planar rectification (fsg_stereo.rectification), unchanged."""
    return FS.rectification(c)


def to_rectified(k, r, p, uv) -> tuple[np.ndarray, np.ndarray]:
    """Raw pixel coordinates -> rectified coordinates; also the third coordinate of the rectified-frame ray."""
    uv = np.asarray(uv, np.float64)
    a = np.concatenate([uv, np.ones((*uv.shape[:-1], 1))], axis=-1)
    h = (a @ np.linalg.inv(np.asarray(k, np.float64)).T) @ np.asarray(r, np.float64).T
    x = h @ np.asarray(p, np.float64)[:, :3].T
    with np.errstate(divide="ignore", invalid="ignore"):
        uvr = x[..., :2] / h[..., 2:3]
    return uvr, h[..., 2]


def triangulate(c: dict, rect: dict, prod: dict, variant: dict | None = None) -> dict:
    """Planar projective triangulation of the shared correspondences.

    ``variant`` exists only so that the synthetic known answers and the checker's mutation suite can build
    deliberately wrong versions (``swap_eyes``, ``q_sign``, ``baseline_scale``, ``r1_transposed``, ``q``)."""
    v = dict(variant or {})
    BG.validate_product(prod)
    kl, kr = (np.asarray(e["K"], np.float64) for e in c["eyes"])
    r1 = np.asarray(rect["R1"], np.float64)
    r1 = r1.T if v.get("r1_transposed") else r1
    uvr_l, w_l = to_rectified(kl, r1, rect["P1"], prod["uv_L"])
    uvr_r, w_r = to_rectified(kr, rect["R2"], rect["P2"], prod["uv_R"])
    if v.get("swap_eyes"):
        uvr_l, uvr_r, w_l, w_r = uvr_r, uvr_l, w_r, w_l
    d = uvr_l[:, 0] - uvr_r[:, 0]
    qq = np.array(rect["Q_full"] if v.get("q") is None else v["q"], np.float64)
    qq[3, 2] *= float(v.get("q_sign", 1.0)) / float(v.get("baseline_scale", 1.0))
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        x_rect = FG.reproject_q(qq, uvr_l, d)
        p = FG.rect_to_head(c, r1, np.where(np.isfinite(x_rect), x_rect, np.nan))
    o_l = np.asarray(c["eyes"][0]["centre_h_m"], np.float64)
    valid = ((w_l > SP.PLANAR_W_EPS) & (w_r > SP.PLANAR_W_EPS) & np.isfinite(uvr_l).all(-1) & np.isfinite(uvr_r).all(-1)
             & np.isfinite(d) & (np.abs(d) >= SP.PLANAR_D_EPS) & np.isfinite(p).all(-1))
    p = np.where(valid[:, None], p, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        range_l = np.linalg.norm(p - o_l, axis=-1)
        per_disp = range_l / d
    w, h = c["image_size_wh"]
    lo, hi = SP.RECT_CORE_BOUNDS
    inside = lambda uv: (uv[:, 0] >= 0) & (uv[:, 0] <= w - 1) & (uv[:, 1] >= 0) & (uv[:, 1] <= h - 1)  # noqa: E731
    with np.errstate(invalid="ignore"):
        in_core = (uvr_l[:, 0] >= lo) & (uvr_l[:, 0] <= hi) & (uvr_l[:, 1] >= lo) & (uvr_l[:, 1] <= hi)
        raster_l, raster_r = inside(uvr_l), inside(uvr_r)
    return {"left_core_row": np.asarray(prod["left_core_row"], np.int32),
            "left_core_col": np.asarray(prod["left_core_col"], np.int32),
            "uvrect_L": uvr_l, "uvrect_R": uvr_r, "w_L": w_l, "w_R": w_r, "disparity": d,
            "row_residual": uvr_r[:, 1] - uvr_l[:, 1], "X_rect": x_rect, "z_rect": x_rect[:, 2], "P_planar": p,
            "valid_planar": valid, "range_L_planar": np.where(valid, range_l, np.nan),
            "range_per_disparity_px": np.where(valid, per_disp, np.nan),
            "rect_L_in_raster": raster_l, "rect_R_in_raster": raster_r, "rect_L_in_central_core": in_core}


# ------------------------------------------------------------------ the support diagnostic (section 9a)
def support_diagnostic(c: dict, rect: dict) -> dict:
    """The accepted AB1a pre-look diagnostic plus finiteness, raw-source spans and two-dimensionality."""
    pre = AS.prelook_geometry(c)
    x, y, cw, ch = map(int, rect["crop_xywh"])
    for side in ("L", "R"):
        mx, my = rect["map_" + side + "x"][y:y + ch, x:x + cw], rect["map_" + side + "y"][y:y + ch, x:x + cw]
        finite = bool(np.isfinite(mx).all() and np.isfinite(my).all())
        sx, sy = float(np.nanmax(mx) - np.nanmin(mx)), float(np.nanmax(my) - np.nanmin(my))
        e = pre["eyes"][side]
        e["support_finite"] = finite
        e["raw_source_span_px"] = {"x": sx, "y": sy}
        e["support_two_dimensional"] = bool(sx >= SP.SUPPORT["two_dimensional_min_span_px"]
                                            and sy >= SP.SUPPORT["two_dimensional_min_span_px"])
        e["rectified_core_fraction_from_nominal_raw_core"] = e["rectified_core_pixels_from_nominal_raw_core"] / (cw * ch)
    pre["schema"] = "AB1c-planar-support-v1"
    pre["statement"] = ("PLANAR SUPPORT DIAGNOSTIC (calibration only, descriptive): the fixed central 256 x 256 rectified "
                        "core of the accepted rectification, mapped back to each raw raster; no threshold")
    pre["support_rule"] = SP.SUPPORT
    return pre


# ------------------------------------------------------------------ summary
def summarize(c: dict, rect: dict, res: dict) -> dict:
    v = res["valid_planar"].astype(bool)
    d = res["disparity"]
    q = BG.quantiles
    return {
        "rectification": {"R1_rotation_deg": rotation_deg(rect["R1"]), "R2_rotation_deg": rotation_deg(rect["R2"]),
                          "rectified_focal_px": float(rect["P1"][0][0]),
                          "principal_point_L_px": [float(rect["P1"][0][2]), float(rect["P1"][1][2])],
                          "principal_point_R_px": [float(rect["P2"][0][2]), float(rect["P2"][1][2])],
                          "P2_0_3": float(rect["P2"][0][3]), "crop_xywh": [int(a) for a in rect["crop_xywh"]]},
        "counts": {"correspondences": int(v.size), "valid_planar": int(v.sum()),
                   "in_front_L": int((res["w_L"] > SP.PLANAR_W_EPS).sum()),
                   "in_front_R": int((res["w_R"] > SP.PLANAR_W_EPS).sum()),
                   "disparity_positive": int((d > 0).sum()), "disparity_zero": int((d == 0).sum()),
                   "disparity_negative": int((d < 0).sum()),
                   "rect_L_in_raster": int(res["rect_L_in_raster"].sum()),
                   "rect_R_in_raster": int(res["rect_R_in_raster"].sum()),
                   "rect_L_in_central_core": int(res["rect_L_in_central_core"].sum())},
        "distributions": {"disparity_px": q(d, v), "abs_row_residual_px": q(np.abs(res["row_residual"]), v),
                          "z_rect_m": q(res["z_rect"], v), "range_L_planar_m": q(res["range_L_planar"], v),
                          "range_per_disparity_px_m": q(res["range_per_disparity_px"], v)},
    }


# ------------------------------------------------------------------ the guarded stage
def truth_reads(events: list[dict]) -> dict:
    paths = [e["path"] for e in events if e.get("event") == "open"]
    ref = [p for p in paths if p.endswith("reference-observation.npz") or p.endswith(".exr") or "evaluation_only" in p]
    return {"position_reads": len(ref), "object_index_reads": len(ref)}


def run_planar(calib_path: Path, product_path: Path, out_dir: Path, freeze_path: Path) -> dict:
    """Read exactly the calibration and the frozen product; write the planar result, support and records."""
    if not Path(freeze_path).exists():
        raise RuntimeError("the correspondence product is not frozen")
    out_dir.mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ab1c-planar", [calib_path, product_path], [out_dir])
    try:
        with g:
            inputs = {"calibration": {"path": str(calib_path), "sha256": sha256(calib_path)},
                      "correspondences": {"path": str(product_path), "sha256": sha256(product_path)}}
            c = json.loads(Path(calib_path).read_text())
            FG.validate_calibration(c)
            prod = BG.load_product(product_path)
            rect = rectify(c)
            res = triangulate(c, rect, prod)
            sup = support_diagnostic(c, rect)
            np.savez_compressed(out_dir / "planar-result.npz", **res, **{k: np.asarray(rect[k]) for k in RECT_KEYS},
                                crop_xywh=np.asarray(rect["crop_xywh"]))
            write_json(out_dir / "planar-support.json", sup)
            summary = {"schema": "AB1c-planar-summary-v1", "truth": SP.TRUTH_DERIVED,
                       "statement": "TRUTH-FREE PLANAR RECONSTRUCTION: the accepted rectification and Q reprojection of "
                                    "the frozen shared correspondence product; no Position, Object Index or truth XYZ; "
                                    "no SGBM, no matcher",
                       "planar": SP.PLANAR, "planar_config_sha256": SP.config_sha256(SP.PLANAR), "inputs": inputs,
                       **summarize(c, rect, res)}
            write_json(out_dir / "planar-summary.json", summary)
    finally:
        rec = g.record()
        rec["modules_loaded"] = {m: m in sys.modules for m in ("cv2", "fsg_stereo", "ab1a_stereo")}
        rec.update(truth_reads(rec["events"]))
        rec["truth_firewall_violations"] = len(rec["violations"])
        write_json(out_dir / "planar-opened-files.json", rec)
    return summary
