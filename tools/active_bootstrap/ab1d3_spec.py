"""Active Bootstrap-1d3: declared constants, pinned sources and the frozen SGBM configuration (one-shot SGBM viability).

Contract: docs/active-bootstrap/ab1d3-sgbm-viability-contract.md.  Standard library only.  The checker keeps its own
literal copies.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
REPO = TOOLS.parent
SHARED = Path("/home/lvelho/rd/f3d-vision")
BASE_COMMIT = "56606b8d4a51361f4fb729306ed73bf23b8ffaf3"        # accepted main: AB1d2 accepted + post-AB1d2 roadmap
AB1D2_ACCEPTANCE = "f65c6ac8344bfcfb0491888bf8608471d2452f61"
AB1D2_ACCEPTED_MARKER = "ACTIVE_BOOTSTRAP1D2_4096SPP_OBSERVATION_QUALITY_ACCEPTED"
AB1D2_REPORT = "docs/active-bootstrap/ab1d2-4096spp-observation-quality-report.md"
CONTRACT_COMMIT = "492232e810b75099708b466a1f3b603f4f1dbba9"
CANONICAL_REMOTE = "visgraf/f3d-vision"
BRANCH = "active-bootstrap/ab1d3-sgbm-viability"
EXPERIMENT = "Active Bootstrap-1d3: One-Shot SGBM Viability"
CONTRACT = "docs/active-bootstrap/ab1d3-sgbm-viability-contract.md"
MARKER = "ACTIVE_BOOTSTRAP1D3_SGBM_VIABILITY_COMPLETE"

TRUTH_ORACLE, TRUTH_DERIVED, TRUTH_REFERENCE = "ORACLE INPUT", "DERIVED", "REFERENCE / EVALUATION"

# ---- section 4: the accepted AB1d2 4096-spp observations (no render; read in place)
A1D2_RUN = SHARED / "previews/active-bootstrap/ab1d2-4096spp-observation-quality"
A1D2_VIS = SHARED / "visuals/active-bootstrap/ab1d2-4096spp-observation-quality"
GAZES = ("gaze-1", "gaze-2", "gaze-3")
GAZE_TABLE = {"gaze-1": {"row": 191, "col": 322, "yaw_deg": -18.75, "pitch_deg": -5.75},
              "gaze-2": {"row": 166, "col": 373, "yaw_deg": 6.75, "pitch_deg": 6.75},
              "gaze-3": {"row": 190, "col": 397, "yaw_deg": 18.75, "pitch_deg": -5.25}}
SPP = 4096
OBS_PINS = {
    "observations/gaze-1/acquisition/calibration.json": "ae56ef338561a9d23d4208e36fb88862adb08e6bd8f773651ed3aa9e83224ebf",
    "observations/gaze-1/acquisition/rgb-observation.npz": "9d653bd1fa1bb2d1d59847b0a55c1b43603b5628beb3bc70f29975d4e57bf02c",
    "observations/gaze-1/acquisition/acquisition.json": "7c023b1f382514716893ca1a4d3009a6ae1102e327b3de00312206e3d9f37eff",
    "observations/gaze-2/acquisition/calibration.json": "ab348665b6c86443145cfa448ac488ec101eab41277d47b0d93c3eaabfd37ec7",
    "observations/gaze-2/acquisition/rgb-observation.npz": "3046cc66f67494b5f639380c46f25672c2259684f28511ba5366f872986e4bba",
    "observations/gaze-2/acquisition/acquisition.json": "bba22357919a2398feeb96896fda131f8c9f866d0cfe4006ecad7e44fc434fe8",
    "observations/gaze-3/acquisition/calibration.json": "085ff33204b84c3d7b05a92c3099bef600dd698bf6e6ab209cb0e5bfe748accd",
    "observations/gaze-3/acquisition/rgb-observation.npz": "fd9ecd4ed94b8c6fdc91a1dd7501840da2934b335387515b10098dc69497ce75",
    "observations/gaze-3/acquisition/acquisition.json": "657c7b7bd7ab80dd91b1cf68b4bc293846a9332408bb1309dd2ecfb56b0f6544",
}
A1D2_PINS = {      # the accepted AB1d2 run records (hashed at source; the evaluation files are opened only post-freeze)
    "manifest.json": "5ace0ab7764e40e9ab673271c829cb77363d7787fcc794a79aa63d5c580c6cbd",
    "freeze/observation-freeze.json": "7c8ed0a3a65189fd8057c980ef9a3c1968e83ade9955dc1625503a6d6df47290",
    "observations/render-control.json": "9b982634395c2f9c99e5964f874a98a620848e80c69b05d0c179bdb6f08e993c",
    "match/correspondence-freeze.json": "ae98de446c88bc6df8b0ff623b41d26928b6dfdb2854a0015b3697e38834e162",
    "freeze/geometry-freeze.json": "9447019debd00fe10599de3dbe7774058f072a3236e2a115ad0b31ca74435831",
    "evaluation/evaluation-summary.json": "e62cf56def51c23b7d431bf25bb1b688a6e00b7b96ae4501cca85d614960cea2",
    "evaluation/gaze-1/evaluation-result.npz": "ee844c5a2f7666a6be3851a505321b12c04cb147146b49610abfdf5c0038daa0",
    "evaluation/gaze-2/evaluation-result.npz": "8ac6781a053550a5803632c3a37d8a5f0dde829e071d01bf06d5889340e2e25b",
    "evaluation/gaze-3/evaluation-result.npz": "995fc07ee8e76cf00cbfa7f7f7769634e6bf9fd04680f9d00912cc3ae0286eb4",
}
A1D2_VIS_MANIFEST = (A1D2_VIS / "visuals-manifest.json",
                     "3041febc5fb1727d385d4e4ad063477fc9100cad1859bd8a1d778a97836363be")

# ---- section 4b: the accepted AB1c benchmark (the AB1d / AB1d2 BENCH_PINS), opened only after the geometry freeze
A1C_RUN = SHARED / "previews/active-bootstrap/ab1c-safe-forward-planar-vs-spherical"
A1C_MANIFEST = ("manifest.json", "21640f6a56474f9ed171d37ceb13571a56499ac805b1b1bbec09c6808a0d378a")

# ---- section 4c: accepted code reused read-only (sha256 at the base); a mismatch is a STOP
SOURCE_PINS = {
    "tools/fsg_stereo.py": "faebf0f1b3acbfde60b08830a57213bf29c708c3aa274e493ade0042eb0545e9",
    "tools/fsg_geometry.py": "ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54",
    "tools/active_bootstrap/ab1a_stereo.py": "c0238a7318c4a9c034c4a679104ae46cfd7504bf204935e2af15707b10f07f65",
    "tools/active_bootstrap/ab1a_spec.py": "24ab5df947b6aaabc46737d3fd015d43802405f94ff1b01595c650bf5ab24a62",
    "tools/active_bootstrap/ab1a_run.py": "348fdee41b98f52d7b184b97a608a9b9da8b779794f0d8c9d1d198dd13095b0f",
    "tools/active_bootstrap/ab1b_geometry.py": "a125dd9cc666120219e0421a09a380353d2304ed0f09681a1655962444572538",
    "tools/active_bootstrap/ab1b_spec.py": "1634e455a61879934545a1fa634a72cbb2b8ca74fd83a6ba3a977412be0e497d",
    "tools/active_bootstrap/ab1c_planar.py": "1528ee92af48c5a13b621d300fe0a78dedc57f27181959d40505f2f9b19e6227",
    "tools/active_bootstrap/ab1c_spec.py": "53d1b7228b30883db715f3fc33a65893aa7708656c2881f2a31eef1a3ac77b1a",
    "tools/active_bootstrap/ab1d_match.py": "dd1ac243d1da09635e12edb87d0d402f169d49e016ac3f35ed5d1572ec255ffd",
    "tools/active_bootstrap/ab1d_spec.py": "fc50a7306ed5e384878c61574c250b3534e1ac4b3a2e6936c153f805aba7b346",
    "tools/active_bootstrap/ab1d_run.py": "9df2981ba55041e7cebdb34061b5cb565d65734b78962318931b4dcb482a7292",
    "tools/active_bootstrap/ab1d2_spec.py": "116a9063939e90132d3f911dbd5119f4a2137ecf07dacedbd294d60bbe480e6c",
    "tools/active_bootstrap/ab1b_visuals.py": "6dd4a203b1847e9d5f0f984c2a1727859aa035ad00adead79849bd484ca833ee",
    "tools/active_bootstrap/ab1c_visuals.py": "28054811eca774883753c2499d135cdabae37b32f6f014432bf1057dcab71a30",
    "tools/natural_bootstrap/nb1a_guard.py": "29ebca57be9e977def7a94ea45a7b0cff0f22a8b1d86b40f740f132491ebe99d",
    "tools/visual_language/style.py": "c379a2a31c9112d22bbe8989324d2ff74608c669fe84d58905509b4d62264053",
    "tools/classroom_oracle/breadth1_visuals.py": "61683aea17993da09bfddce4ed13d48da47d710d1630e40c6bdcc7a6f6d2144c",
}

# ---- section 5: the instrument
RAW_SIZE = 640
CORE_SIZE = 256
CORE_ORIGIN = (RAW_SIZE - CORE_SIZE) // 2          # 192: raw u, v = 192..447
IPD_M = 0.063
FOCAL_PX = 1217.8386501404907

# ---- section 6: the ONE frozen SGBM configuration (the accepted FSG / AB1a RGB-only matcher; fsg_stereo + ab1a_stereo)
SGBM = {
    "name": "accepted FSG / AB1a natural RGB-only SGBM_3WAY + bounded photometric refinement (ab1a_stereo.compute_natural)",
    "mode": "STEREO_SGBM_MODE_SGBM_3WAY", "mode_value": 2, "blockSize": 5, "P1": 200, "P2": 800,
    "P1_rule": "8 * blockSize^2", "P2_rule": "32 * blockSize^2", "preFilterCap": 31, "uniquenessRatio": 10,
    "disp12MaxDiff": -1, "speckleWindowSize": 0, "speckleRange": 1, "minDisparity_left": 0,
    "numDisparities_rule": "ceil((ceil(|P2[0,3]| / z_rect_min) + 4) / 16) * 16",
    "minDisparity_right_rule": "-(minDisparity + numDisparities - 1)",
    "z_rect_m": [0.75, 4.5], "lr_tolerance_px": 1.0, "min_local_std_u8": 0.5,
    "refinement": {"iterations": 3, "max_step_px": 0.5, "max_total_px": 0.75},
    "rectification": "fsg_stereo.rectification: cv2.stereoRectify(CALIB_ZERO_DISPARITY, alpha = -1, newImageSize = "
                     "640 x 640), cv2.initUndistortRectifyMap CV_32FC1, cv2.remap INTER_LINEAR",
    "photometry": "fsg_stereo.linear_to_u8, cv2.cvtColor(COLOR_RGB2GRAY)",
    "matched_raster": "the full 640 x 640 rectified raster (no crop before SGBM)",
    "roi": "cv2.getValidDisparityROI(roi_L, roi_R, minDisparity, numDisparities, blockSize)",
    "support": "fsg_stereo.support_mask (calibration-derived)", "identity_guard": None,
    "validity": ["term_sgbm_left", "term_right_valid", "term_support_left", "term_inside_raster", "term_lr",
                 "term_texture", "term_finite", "term_z_range", "term_roi"],
    "output_window": "full 640 x 640 rectified raster (section 6c): the accepted computation is unchanged; only the "
                     "window of the returned arrays is the full raster instead of the central 256 x 256 crop",
}
TERMS = tuple(SGBM["validity"])
NUM_DISPARITIES = 112                              # the formula at the three accepted calibrations (verified by source)
SGBM_GETTERS = {"getMode": 2, "getBlockSize": 5, "getP1": 200, "getP2": 800, "getPreFilterCap": 31,
                "getUniquenessRatio": 10, "getDisp12MaxDiff": -1, "getSpeckleWindowSize": 0, "getSpeckleRange": 1,
                "getNumDisparities": NUM_DISPARITIES}
SGBM_MIN_DISPARITY = {"L": 0, "R": -(NUM_DISPARITIES - 1)}
RECTIFY = {"flags": 1024, "alpha": -1.0, "newImageSize": [RAW_SIZE, RAW_SIZE]}   # cv2.CALIB_ZERO_DISPARITY == 1024
WATCHED = ("StereoSGBM_create", "stereoRectify", "initUndistortRectifyMap", "getValidDisparityROI")
TRIPWIRES = ("StereoBM_create", "filterSpeckles", "validateDisparity", "reprojectImageTo3D")
RGB_KEYS = ("rgb_L", "rgb_R")

# ---- section 8: the raw-core correspondence adapter (frozen)
ADAPTER = {
    "left": "ab1c_planar.to_rectified(K_L, R1, P1, uv_L): exact continuous left rectified coordinate of the raw "
            "left-core pixel centre",
    "rectifiable": "finite, w_L > Z_EPS, and the 2 x 2 bilinear footprint {x0, x0 + 1} x {y0, y0 + 1} (x0 = floor(u), "
                   "y0 = floor(v)) inside the 640 x 640 rectified raster",
    "sampling": "bilinear refined disparity; valid only if all FOUR footprint pixels satisfy the full SGBM validity "
                "(every term), whatever their weights; no interpolation across invalid SGBM pixels",
    "right_rectified": "u_R = u_L - d, v_R = v_L",
    "inverse": "d_raw_R = R2^T K_rect^-1 (u_R, v_R, 1)^T with K_rect = P2[:, :3]; uv_R = project(K_R d_raw_R); "
               "row-vector form d_raw_row = (q K_rect^-T) @ R2",
    "raw_valid": "finite, raw camera z > Z_EPS, 0 <= u_R <= W - 1 and 0 <= v_R <= H - 1",
    "product": "accepted AB1b schema (left_core_row, left_core_col, uv_L exact raw centre, uv_R), core order, valid only",
}
Z_EPS = 1e-12
ADAPTER_STAGES = ("raw_core", "rectifiable") + tuple(f"footprint_{t}" for t in TERMS) + ("raw_in_front", "raw_inside")

# ---- section 9: known-answer software tolerances (synthetic / calibration-only data only)
KA_ROUNDTRIP_PX = 1e-9
KA_PERFECT_PX = 1e-6
KA_OPENCV_MAP_PX = 2e-3
KA_PLANE_SEED = 20261005
SYN_PLANE_Z_M = 2.0                  # = ab1a_spec.SYN_PLANE_Z_M (verified)
SYN_MIN_VALID = 0.90                 # = ab1a_spec (accepted AB1a SGBM known answer)
SYN_MAX_MEDIAN_DISPARITY_PX = 0.05
SYN_MAX_P95_DISPARITY_PX = 0.50
SYN_MAX_MEDIAN_3D_M = 0.005          # spherical reconstruction of the adapted product vs synthetic Position
SYN_SUBPIXEL_D_PX = 40.3
SYN_REFINE_MAX_PX = 0.75 + 1e-6
SYN_REPEAT = {"period_texels": 10, "spacing_m": 0.001, "contrast": 0.35, "noise": 0.04, "band_texels": 120,
              "texture_n": 2400, "seed": 7, "margin_texels": 8}
SYN_REPEAT_OUTSIDE_GAIN = 0.02       # frozen minus the P1 = P2 = 0 control: correct-and-valid fraction outside the band
SYN_REPEAT_BAND_WRONG_MAX = 0.05     # frozen: wrong-and-valid fraction inside the periodic band

# ---- sections 12-15: evaluation (post-freeze, descriptive; no acceptance threshold)
GOOD_PX = 1.0
PX_BINS = (0.10, 0.25, 0.50, 1.00)
CATASTROPHIC_PX = (10.0, 100.0)
METRIC_FRACTIONS_M = (0.012, 0.025, 0.050, 0.100)
QUANTILES = {"min": 0.0, "p05": 0.05, "p10": 0.10, "p25": 0.25, "median": 0.5, "p75": 0.75, "p90": 0.90, "p95": 0.95,
             "p99": 0.99, "max": 1.0}
SERVICEABLE = {
    "statement": "an oracle pair (accepted AB1c perfect correspondence) is SGBM-serviceable iff, through the accepted "
                 "planar geometry, it lies inside the frozen SGBM operating domain; computed post-freeze, evaluation only",
    "left": "the bilinear footprint of to_rectified(uv_L) inside the raster, all four pixels with calibration support "
            "(fsg_stereo.support_mask L) and inside the accepted valid-disparity ROI",
    "right": "the bilinear footprint of to_rectified(uv_R_oracle) inside the raster and all four pixels with "
             "calibration support (fsg_stereo.support_mask R)",
    "disparity": "0 <= d = u_rect_L - u_rect_R <= numDisparities - 1 (the declared SGBM search)",
    "z_rect": "Q reprojection of (u_rect_L, v_rect_L, d) finite with z_rect in [0.75, 4.5] m",
}
CATEGORIES = ("both_correct", "primitive_only", "sgbm_only", "neither")
COMPONENT_MIN_PX = 50

# ---- section 18: commands, run layout
RUN_DEFAULT = SHARED / "previews/active-bootstrap/ab1d3-sgbm-viability"
VIS_DEFAULT = SHARED / "visuals/active-bootstrap/ab1d3-sgbm-viability"
COMMANDS = ("source", "preflight", "sgbm", "raw-core-adapter", "freeze-correspondence", "spherical", "freeze-geometry",
            "evaluate", "visualize")
CANONICAL = ("source", "sgbm", "raw-core-adapter", "freeze-correspondence", "spherical", "freeze-geometry", "evaluate")
ORDER = COMMANDS
FIGURES = ("overview.png", "sgbm-vs-primitive.png", "disparity-validity.png", "metric-error.png", "attrition.png")
SGBM_CODE = ("tools/active_bootstrap/ab1d3_sgbm.py", "tools/active_bootstrap/ab1d3_spec.py",
             "tools/active_bootstrap/ab1d3_run.py", "tools/active_bootstrap/ab1a_stereo.py",
             "tools/active_bootstrap/ab1a_spec.py", "tools/fsg_stereo.py", "tools/fsg_geometry.py",
             "tools/natural_bootstrap/nb1a_guard.py")
ADAPTER_CODE = SGBM_CODE + ("tools/active_bootstrap/ab1c_planar.py", "tools/active_bootstrap/ab1b_geometry.py",
                            "tools/active_bootstrap/ab1b_spec.py")
SPHERICAL_CODE = ("tools/active_bootstrap/ab1b_geometry.py", "tools/active_bootstrap/ab1b_spec.py",
                  "tools/active_bootstrap/ab1d_run.py", "tools/active_bootstrap/ab1d_spec.py",
                  "tools/active_bootstrap/ab1d3_run.py", "tools/active_bootstrap/ab1d3_spec.py", "tools/fsg_geometry.py",
                  "tools/natural_bootstrap/nb1a_guard.py")


def a1d2(rel: str) -> Path:
    return A1D2_RUN / rel


def a1c(rel: str) -> Path:
    return A1C_RUN / rel


def obs_rel(g: str, name: str) -> str:
    return f"observations/{g}/acquisition/{name}"


def calibration_path(g: str) -> Path:
    return A1D2_RUN / obs_rel(g, "calibration.json")


def rgb_path(g: str) -> Path:
    return A1D2_RUN / obs_rel(g, "rgb-observation.npz")


def config_sha256(cfg) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()


def truth_reads(events: list[dict]) -> dict:
    """Reads the inference stages must never make, counted from every open event (allowed or refused)."""
    paths = [e["path"] for e in events if e.get("event") == "open"]
    a1c, a1d2 = str(A1C_RUN.resolve()), str(A1D2_RUN.resolve())
    pos = [p for p in paths if "/evaluation_only/" in p or p.endswith(".exr") or p.endswith("reference-observation.npz")]
    ora = [p for p in paths if "oracle" in p.rsplit("/", 1)[-1] or p.startswith(a1c + "/oracle/")]
    ev = [p for p in paths if p.startswith(a1c + "/") or any(p.startswith(a1d2 + "/" + s + "/") for s in
                                                            ("evaluation", "match", "spherical", "freeze"))
          or "evaluation-result" in p or "instance-catalog" in p]
    return {"position_reads": len(pos), "object_index_reads": len(pos), "oracle_reads": len(ora),
            "evaluation_or_matcher_product_reads": len(ev)}
