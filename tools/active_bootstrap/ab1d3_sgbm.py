"""Active Bootstrap-1d3: the frozen SGBM correspondence service and the raw-core correspondence adapter.

Contract: docs/active-bootstrap/ab1d3-sgbm-viability-contract.md, sections 6-8.

The matcher is the accepted AB1a natural RGB-only SGBM, ``ab1a_stereo.compute_natural``, called unchanged: the accepted
``fsg_stereo`` rectification (cv2.stereoRectify, CALIB_ZERO_DISPARITY, alpha = -1, 640 x 640), remap, linear_to_u8, gray,
full-raster SGBM_3WAY left -> right and right -> left, the bounded photometric refinement and the nine RGB-only validity
terms.  ``compute_natural`` computes every array on the full 640 x 640 rectified raster and, at return, crops them to
``rectification(c)["crop_xywh"]`` (the central 256 x 256).  ``full_raster_view`` sets that window to the full raster for
the duration of one call; nothing that is computed changes (section 6c; checked against the accepted crop).

``Recorder`` records every call of the watched OpenCV entry points, including the created SGBM objects' own getters and
the shape / dtype / hash of every array SGBM matches, and trips on any other matcher or disparity post-filter.

The adapter maps the full refined SGBM disparity back to ORIGINAL RAW coordinates and writes the accepted AB1b
truth-free correspondence product (left_core_row, left_core_col, uv_L, uv_R) for the 256 x 256 raw left core.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent / "natural_bootstrap"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ab1a_stereo as AS  # noqa: E402  (accepted AB1a natural RGB-only SGBM, read-only)
import ab1b_geometry as BG  # noqa: E402  (accepted product schema, read-only)
import ab1c_planar as CP  # noqa: E402  (accepted raw -> rectified geometry, read-only)
import ab1d3_spec as SP  # noqa: E402
import fsg_geometry as FG  # noqa: E402  (accepted sensor geometry, read-only)
import fsg_stereo as FS  # noqa: E402  (accepted stereo primitives, read-only)
from nb1a_guard import OpenGuard  # noqa: E402  (accepted allowlist file-open guard, read-only)


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def array_sha256(a) -> str:
    a = np.ascontiguousarray(a)
    return hashlib.sha256(str(a.dtype).encode() + str(a.shape).encode() + a.tobytes()).hexdigest()


def write_json(path: Path, data) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=1, sort_keys=True, allow_nan=False) + "\n")


# ------------------------------------------------------------------ section 6c: the full-raster output window
@contextlib.contextmanager
def full_raster_view():
    """The accepted compute_natural returns its arrays cropped to ``rectification(c)["crop_xywh"]``.  For one call,
    report that window as the full raster; R1, R2, P1, P2, Q, the maps, the ROI and the disparity range are untouched."""
    accepted = FS.rectification

    def view(c: dict) -> dict:
        r = accepted(c)
        w, h = c["image_size_wh"]
        return dict(r, crop_xywh=np.array([0, 0, w, h], np.int32))
    FS.rectification = view
    try:
        yield
    finally:
        FS.rectification = accepted


# ------------------------------------------------------------------ section 6d: the OpenCV call recorder
class _Matcher:
    """Wraps one created StereoSGBM object: records what it matches, then delegates."""

    def __init__(self, inner, entry: dict) -> None:
        self._inner, self._entry = inner, entry

    def compute(self, left, right, *a, **k):
        self._entry["compute"].append({"left_shape": list(np.shape(left)), "left_dtype": str(np.asarray(left).dtype),
                                       "right_shape": list(np.shape(right)), "right_dtype": str(np.asarray(right).dtype),
                                       "left_sha256": array_sha256(left), "right_sha256": array_sha256(right)})
        out = self._inner.compute(left, right, *a, **k)
        self._entry["compute"][-1].update({"out_shape": list(out.shape), "out_dtype": str(out.dtype),
                                           "out_sha256": array_sha256(out)})
        return out

    def __getattr__(self, name):
        return getattr(self._inner, name)


GETTERS = tuple(SP.SGBM_GETTERS) + ("getMinDisparity",)


class Recorder:
    def __init__(self) -> None:
        self.calls = {n: [] for n in SP.WATCHED}
        self.trips: dict[str, int] = {}
        self.saved: dict = {}

    def __enter__(self) -> "Recorder":
        for n in SP.WATCHED + SP.TRIPWIRES:
            if hasattr(cv2, n):
                self.saved[n] = getattr(cv2, n)
        orig = self.saved

        def sgbm_create(*a, **k):
            m = orig["StereoSGBM_create"](*a, **k)
            entry = {"kwargs": {kk: (int(vv) if isinstance(vv, (int, np.integer)) else vv) for kk, vv in k.items()},
                     "positional": len(a), "getters": {g: int(getattr(m, g)()) for g in GETTERS},
                     "type": type(m).__name__, "compute": []}
            self.calls["StereoSGBM_create"].append(entry)
            return _Matcher(m, entry)

        def stereo_rectify(*a, **k):
            self.calls["stereoRectify"].append({"image_size": [int(x) for x in a[4]] if len(a) > 4 else None,
                                                "flags": int(k.get("flags", -1)), "alpha": float(k.get("alpha", 0.0)),
                                                "newImageSize": [int(x) for x in k.get("newImageSize", (0, 0))],
                                                "positional": len(a)})
            return orig["stereoRectify"](*a, **k)

        def init_maps(*a, **k):
            self.calls["initUndistortRectifyMap"].append({"size": [int(x) for x in a[4]] if len(a) > 4 else None,
                                                          "m1type": int(a[5]) if len(a) > 5 else None})
            return orig["initUndistortRectifyMap"](*a, **k)

        def roi(*a, **k):
            out = orig["getValidDisparityROI"](*a, **k)
            self.calls["getValidDisparityROI"].append({"args": [list(map(int, a[0])), list(map(int, a[1])), int(a[2]),
                                                                int(a[3]), int(a[4])], "roi": [int(x) for x in out]})
            return out
        cv2.StereoSGBM_create = sgbm_create
        cv2.stereoRectify = stereo_rectify
        cv2.initUndistortRectifyMap = init_maps
        cv2.getValidDisparityROI = roi
        for n in SP.TRIPWIRES:
            if n in orig:
                def trip(*a, _n=n, **k):
                    self.trips[_n] = self.trips.get(_n, 0) + 1
                    raise RuntimeError(f"AB1d3 tripwire: cv2.{_n} called")
                setattr(cv2, n, trip)
        return self

    def __exit__(self, *exc) -> None:
        for n, fn in self.saved.items():
            setattr(cv2, n, fn)

    def log(self) -> dict:
        return {"calls": self.calls, "tripwire_calls": dict(self.trips), "opencv": cv2.__version__}


# ------------------------------------------------------------------ section 6: the frozen SGBM (accepted, unchanged)
def compute_sgbm(c: dict, obs: dict, variant: dict | None = None) -> tuple[dict, dict, dict]:
    """The accepted ab1a_stereo.compute_natural on the full rectified raster, under the recorder.  ``variant`` is the
    accepted compute_natural mutation hook; only the synthetic known answers and the checker pass one."""
    with Recorder() as rec, full_raster_view():
        record, summary = AS.compute_natural(c, obs, variant)
    return record, summary, rec.log()


def sgbm_summary(rec: dict, summ: dict, calls: dict, inputs: dict, seconds: float) -> dict:
    v = rec["valid"]
    sg = rec["term_sgbm_left"]
    raw = rec["disparity_sgbm_px"].astype(np.float64) * 16.0
    delta = rec["disparity_px"].astype(np.float64) - rec["disparity_sgbm_px"].astype(np.float64)
    q = BG.quantiles
    return {"schema": "AB1d3-sgbm-summary-v1", "truth": SP.TRUTH_DERIVED,
            "statement": "SGBM SPATIAL CORRESPONDENCE (planar, internal): the accepted AB1a natural RGB-only SGBM on the "
                         "calibration and the accepted 4096-spp RGB only, on the full 640 x 640 rectified raster; no "
                         "Position, Object Index, oracle, evaluation or truth",
            "sgbm": SP.SGBM, "sgbm_config_sha256": SP.config_sha256(SP.SGBM), "inputs": inputs,
            "seconds": round(seconds, 4), "accepted_summary": summ,
            "raster": {"pixels": int(v.size), "valid": int(v.sum()), "sgbm_left_valid": int(sg.sum())},
            "distributions_full_raster_valid": {
                "raw_fixed_point_disparity_x16": q(raw, v), "refined_disparity_px": q(rec["disparity_px"], v),
                "refinement_delta_px": q(delta, v), "lr_residual_px": q(rec["lr_error_px"], v),
                "z_rect_m": q(rec["z_rect_m"], v)},
            "refinement_delta_abs_max_sgbm_supported": float(np.nanmax(np.abs(delta[sg & rec["term_support_left"]])))
            if (sg & rec["term_support_left"]).any() else None,
            "opencv_calls": {k: len(x) for k, x in calls["calls"].items()}, "tripwire_calls": calls["tripwire_calls"]}


def run_sgbm_gaze(calib_path: Path, rgb_path: Path, out_dir: Path, probe=None) -> dict:
    """The frozen SGBM under the allowlist guard: exactly the calibration and the 4096-spp RGB observation."""
    out_dir.mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ab1d3-sgbm", [calib_path, rgb_path], [out_dir])
    summary = None
    try:
        with g:
            inputs = {"calibration": {"path": str(calib_path), "sha256": sha256(calib_path)},
                      "rgb_observation": {"path": str(rgb_path), "sha256": sha256(rgb_path)}}
            c = json.loads(Path(calib_path).read_text())
            FG.validate_calibration(c)
            obs = AS.load_observation(rgb_path)          # exactly rgb_L, rgb_R (accepted check)
            t0 = time.perf_counter()
            rec, summ, calls = compute_sgbm(c, obs)
            seconds = time.perf_counter() - t0
            if probe is not None:
                probe()
            np.savez_compressed(out_dir / "sgbm-record.npz", **rec)
            write_json(out_dir / "sgbm-calls.json", calls)
            summary = sgbm_summary(rec, summ, calls, inputs, seconds)
            write_json(out_dir / "sgbm-summary.json", summary)
    finally:
        r = g.record()
        r["modules_loaded"] = {m: m in sys.modules for m in ("ab1d_match", "ab1b_oracle", "ab1c_render", "bpy", "torch",
                                                             "tensorflow", "onnxruntime")}
        r.update(SP.truth_reads(r["events"]))
        r["truth_firewall_violations"] = len(r["violations"])
        write_json(out_dir / "sgbm-opened-files.json", r)
    return summary


# ------------------------------------------------------------------ section 8: the raw-core correspondence adapter
def core_grid() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = SP.CORE_SIZE
    rows, cols = np.divmod(np.arange(n * n, dtype=np.int64), n)
    uv = np.stack([cols + SP.CORE_ORIGIN, rows + SP.CORE_ORIGIN], -1).astype(np.float64)
    return rows, cols, uv


def inverse_rectified(k, r, k_rect, uvr) -> tuple[np.ndarray, np.ndarray]:
    """Rectified pixel -> raw pixel of the same camera.  Column form d_raw = R^T K_rect^-1 (u, v, 1)^T, uv = proj(K d_raw);
    row form below.  Returns the raw pixel and the raw-camera z of the ray."""
    uvr = np.asarray(uvr, np.float64)
    q = np.concatenate([uvr, np.ones((*uvr.shape[:-1], 1))], axis=-1)
    d_rect = q @ np.linalg.inv(np.asarray(k_rect, np.float64)).T
    d_raw = d_rect @ np.asarray(r, np.float64)
    hh = d_raw @ np.asarray(k, np.float64).T
    with np.errstate(divide="ignore", invalid="ignore"):
        uv = hh[..., :2] / hh[..., 2:3]
    return uv, d_raw[..., 2]


def footprint(uvr, w: int, h: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """The 2 x 2 bilinear footprint {x0, x0 + 1} x {y0, y0 + 1}; inside iff all four pixels are in the raster."""
    u, v = np.asarray(uvr[..., 0], np.float64), np.asarray(uvr[..., 1], np.float64)
    fin = np.isfinite(u) & np.isfinite(v)
    x0 = np.floor(np.where(fin, u, -10.0)).astype(np.int64)
    y0 = np.floor(np.where(fin, v, -10.0)).astype(np.int64)
    inside = fin & (x0 >= 0) & (x0 + 1 <= w - 1) & (y0 >= 0) & (y0 + 1 <= h - 1)
    fx = np.where(inside, u - x0, np.nan)
    fy = np.where(inside, v - y0, np.nan)
    return x0, y0, inside, fx, fy


def gather4(a, x0, y0, inside) -> np.ndarray:
    """Values at (y0, x0), (y0, x0 + 1), (y0 + 1, x0), (y0 + 1, x0 + 1); rows outside are read at (0, 0) (masked by the
    caller)."""
    xs, ys = np.where(inside, x0, 0), np.where(inside, y0, 0)
    a = np.asarray(a)
    return np.stack([a[ys, xs], a[ys, xs + 1], a[ys + 1, xs], a[ys + 1, xs + 1]], axis=-1)


def bilinear4(vals, fx, fy) -> np.ndarray:
    v = np.asarray(vals, np.float64)
    return ((1.0 - fx) * (1.0 - fy) * v[..., 0] + fx * (1.0 - fy) * v[..., 1]
            + (1.0 - fx) * fy * v[..., 2] + fx * fy * v[..., 3])


def adapt(c: dict, rec: dict, variant: dict | None = None) -> tuple[dict, dict]:
    """Section 8.  ``variant`` exists only for the known answers and the checker's mutations: ``r2_transposed``,
    ``disparity_sign`` (-1 flips it), ``k_right`` (a wrong right intrinsic), ``ignore_footprint_validity`` (bilinear
    sampling across invalid SGBM pixels)."""
    v = dict(variant or {})
    w, h = c["image_size_wh"]
    kl, kr = (np.asarray(e["K"], np.float64) for e in c["eyes"])
    r1, p1 = np.asarray(rec["R1"], np.float64), np.asarray(rec["P1"], np.float64)
    r2 = np.asarray(rec["R2"], np.float64)
    r2 = r2.T if v.get("r2_transposed") else r2
    k_rect = np.asarray(rec["P2"], np.float64)[:, :3]
    k_right = np.asarray(v["k_right"], np.float64) if v.get("k_right") is not None else kr
    rows, cols, uv_l = core_grid()
    n = uv_l.shape[0]
    uvr_l, w_l = CP.to_rectified(kl, r1, p1, uv_l)
    x0, y0, inside, fx, fy = footprint(uvr_l, w, h)
    rectifiable = inside & (w_l > SP.Z_EPS)
    stages = {"raw_core": np.ones(n, bool), "rectifiable": rectifiable}
    run = rectifiable.copy()
    alone = {}
    for t in SP.TERMS:
        ft = gather4(rec[t], x0, y0, rectifiable).all(axis=-1) & rectifiable
        alone[t] = ft
        run = run & ft
        stages["footprint_" + t] = run.copy()
    full = run if not v.get("ignore_footprint_validity") else rectifiable
    valid_mask_all = gather4(rec["valid"], x0, y0, rectifiable).all(axis=-1) & rectifiable
    d = np.where(full, bilinear4(gather4(rec["disparity_px"], x0, y0, rectifiable), fx, fy), np.nan)
    d_disc = np.where(full, bilinear4(gather4(rec["disparity_sgbm_px"], x0, y0, rectifiable), fx, fy), np.nan)
    lr = np.where(full, bilinear4(gather4(rec["lr_error_px"], x0, y0, rectifiable), fx, fy), np.nan)
    sign = float(v.get("disparity_sign", 1.0))
    uvr_r = np.stack([uvr_l[:, 0] - sign * d, uvr_l[:, 1]], axis=-1)
    uv_r, z_r = inverse_rectified(k_right, r2, k_rect, uvr_r)
    with np.errstate(invalid="ignore"):
        in_front = full & np.isfinite(uv_r).all(axis=-1) & (z_r > SP.Z_EPS)
        inside_raw = (in_front & (uv_r[:, 0] >= 0) & (uv_r[:, 0] <= w - 1) & (uv_r[:, 1] >= 0)
                      & (uv_r[:, 1] <= h - 1))
    stages["raw_in_front"], stages["raw_inside"] = in_front, inside_raw
    valid = inside_raw
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        x_rect = FG.reproject_q(np.asarray(rec["Q_full"], np.float64), uvr_l, d)
        p_planar = FG.rect_to_head(c, r1, np.where(np.isfinite(x_rect), x_rect, np.nan))
    prod = {"left_core_row": rows[valid].astype(np.int32), "left_core_col": cols[valid].astype(np.int32),
            "uv_L": np.ascontiguousarray(uv_l[valid]), "uv_R": np.ascontiguousarray(uv_r[valid])}
    out = {"left_core_row": rows.astype(np.int32), "left_core_col": cols.astype(np.int32), "uv_L": uv_l,
           "uvrect_L": uvr_l, "w_L": w_l, "footprint_x0": x0.astype(np.int32), "footprint_y0": y0.astype(np.int32),
           "footprint_inside": inside, "disparity_bilinear_px": d, "disparity_sgbm_bilinear_px": d_disc,
           "refinement_delta_bilinear_px": d - d_disc, "lr_residual_bilinear_px": lr, "uvrect_R": uvr_r,
           "uv_R": np.where(valid[:, None], uv_r, np.nan), "uv_R_unmasked": uv_r, "z_raw_R": z_r,
           "valid_adapter": valid, "footprint_full_valid": run, "footprint_valid_mask_all": valid_mask_all,
           "planar_q_point_secondary": np.where(valid[:, None], p_planar, np.nan),
           **{"stage_" + k: s for k, s in stages.items()}, **{"alone_" + t: a for t, a in alone.items()}}
    return out, prod


def adapter_summary(c: dict, rec: dict, out: dict, prod: dict, inputs: dict) -> dict:
    v = out["valid_adapter"]
    q = BG.quantiles
    stages = [{"stage": k, "remaining": int(out["stage_" + k].sum())} for k in SP.ADAPTER_STAGES]
    return {"schema": "AB1d3-adapter-summary-v1", "truth": SP.TRUTH_DERIVED,
            "statement": "RAW-CORE CORRESPONDENCE: the frozen SGBM disparity mapped back to ORIGINAL RAW coordinates "
                         "(section 8); the product is the accepted AB1b truth-free schema; no Position, Object Index, "
                         "oracle or truth",
            "adapter": SP.ADAPTER, "adapter_config_sha256": SP.config_sha256(SP.ADAPTER), "inputs": inputs,
            "counts": {"raw_core": int(v.size), "product_pairs": int(prod["left_core_row"].size)},
            "attrition": stages,
            "passes_alone_at_footprint": {t: int(out["alone_" + t].sum()) for t in SP.TERMS},
            "footprint_full_valid_equals_valid_mask": bool(np.array_equal(out["footprint_full_valid"],
                                                                          out["footprint_valid_mask_all"])),
            "distributions_product": {
                "disparity_bilinear_px": q(out["disparity_bilinear_px"], v),
                "refinement_delta_bilinear_px": q(out["refinement_delta_bilinear_px"], v),
                "lr_residual_bilinear_px": q(out["lr_residual_bilinear_px"], v),
                "row_of_left_rectified_px": q(out["uvrect_L"][:, 1], v)}}


def run_adapter_gaze(calib_path: Path, sgbm_path: Path, out_dir: Path, probe=None) -> dict:
    """The adapter under the allowlist guard: exactly the calibration and this run's SGBM record."""
    out_dir.mkdir(parents=True, exist_ok=True)
    g = OpenGuard("ab1d3-adapter", [calib_path, sgbm_path], [out_dir])
    summary = None
    try:
        with g:
            inputs = {"calibration": {"path": str(calib_path), "sha256": sha256(calib_path)},
                      "sgbm_record": {"path": str(sgbm_path), "sha256": sha256(sgbm_path)}}
            c = json.loads(Path(calib_path).read_text())
            FG.validate_calibration(c)
            with np.load(sgbm_path, allow_pickle=False) as z:
                rec = {k: np.asarray(z[k]) for k in z.files}
            r = FS.rectification(c)             # the accepted rectification, recomputed: must equal the record bitwise
            same = {k: bool(np.array_equal(np.asarray(r[k]), rec[k])) for k in ("R1", "R2", "P1", "P2", "Q_full",
                                                                                "roi_L", "roi_R", "num_disparities")}
            if not all(same.values()):
                raise RuntimeError(f"the recomputed rectification differs from the SGBM record: {same}")
            out, prod = adapt(c, rec)
            BG.validate_product(prod)
            if probe is not None:
                probe()
            np.savez_compressed(out_dir / "adapter-record.npz", **out)
            np.savez_compressed(out_dir / "sgbm-correspondences.npz", **prod)
            summary = adapter_summary(c, rec, out, prod, inputs)
            summary["rectification_recomputed_identical"] = same
            write_json(out_dir / "adapter-summary.json", summary)
    finally:
        r = g.record()
        r["modules_loaded"] = {m: m in sys.modules for m in ("ab1d_match", "ab1b_oracle", "ab1c_render", "bpy")}
        r.update(SP.truth_reads(r["events"]))
        r["truth_firewall_violations"] = len(r["violations"])
        write_json(out_dir / "adapter-opened-files.json", r)
    return summary
