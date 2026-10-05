"""Active Bootstrap-1d: declared constants, pinned sources and configurations (safe-forward natural RGB correspondence).

Contract: docs/active-bootstrap/ab1d-safe-forward-natural-correspondence-contract.md.  Standard library only.  The
checker keeps its own literal copies.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
REPO = TOOLS.parent
SHARED = Path("/home/lvelho/rd/f3d-vision")
BASE_COMMIT = "56840caab332bb203918c776acab20d9a6ef4c17"   # accepted main: AB1c accepted + post-AB1c roadmap
CONTRACT_COMMIT = "850724dd866352c7dd18b36fce5f4ee7400ed4cc"
CANONICAL_REMOTE = "visgraf/f3d-vision"
EXPERIMENT = "Active Bootstrap-1d: Safe-Forward Natural RGB Correspondence"
CONTRACT = "docs/active-bootstrap/ab1d-safe-forward-natural-correspondence-contract.md"
MARKER = "ACTIVE_BOOTSTRAP1D_SAFE_FORWARD_NATURAL_CORRESPONDENCE_COMPLETE"

TRUTH_ORACLE, TRUTH_DERIVED, TRUTH_REFERENCE = "ORACLE INPUT", "DERIVED", "REFERENCE / EVALUATION"

# ---- section 3a / 4: the accepted AB1c observations, reused exactly (never re-rendered)
A1C_RUN = SHARED / "previews/active-bootstrap/ab1c-safe-forward-planar-vs-spherical"
A1C_VIS = SHARED / "visuals/active-bootstrap/ab1c-safe-forward-planar-vs-spherical"
GAZES = ("gaze-1", "gaze-2", "gaze-3")
GAZE_TABLE = {"gaze-1": {"row": 191, "col": 322, "yaw_deg": -18.75, "pitch_deg": -5.75},
              "gaze-2": {"row": 166, "col": 373, "yaw_deg": 6.75, "pitch_deg": 6.75},
              "gaze-3": {"row": 190, "col": 397, "yaw_deg": 18.75, "pitch_deg": -5.25}}
OBS_TMPL = "observations/{g}/acquisition/{name}"
REF_TMPL = "observations/{g}/evaluation_only/reference-observation.npz"
ORACLE_TMPL = "oracle/{g}/oracle-correspondences.npz"
SPHERICAL_TMPL = "spherical/{g}/epipolar-result.npz"
EVAL_TMPL = "evaluation/{g}/evaluation-result.npz"
A1C_MANIFEST = ("manifest.json", "21640f6a56474f9ed171d37ceb13571a56499ac805b1b1bbec09c6808a0d378a")
A1C_VIS_MANIFEST = (A1C_VIS / "visuals-manifest.json",
                    "a533366986f6027114b694562d92f7c59bfc47fe486ff7bde0773f07f6b45311")
OBS_PINS = {
    "selection/safe-forward-freeze.json": "72d7e4b8497cabcc2f828a50b894c613790915205bbb8081ed4ce43d702c7ec6",
    "selection/selected-gazes.json": "85c94558119930e3bfbf247cf515361265ecc8fa12ca43d5eb98f9c7158b5b98",
    "observations/gaze-1/acquisition/calibration.json": "ae56ef338561a9d23d4208e36fb88862adb08e6bd8f773651ed3aa9e83224ebf",
    "observations/gaze-1/acquisition/rgb-observation.npz": "d6e2a532acf1534ed305ad63447b30b35645051a350922cbcec14dbb5388f47f",
    "observations/gaze-1/acquisition/acquisition.json": "d1ca822aa2ca49e32fd59466736d03408e7549cac1a452ded6bc19806d32c27b",
    "observations/gaze-2/acquisition/calibration.json": "ab348665b6c86443145cfa448ac488ec101eab41277d47b0d93c3eaabfd37ec7",
    "observations/gaze-2/acquisition/rgb-observation.npz": "297c5bd689cde4a5bf9b01b53e4b643719feff6f654a25a470a2e8b627bca43d",
    "observations/gaze-2/acquisition/acquisition.json": "59443c35284625fca1792b3bfe5cabb22e6635cb27c05bd274ab7501e93beeac",
    "observations/gaze-3/acquisition/calibration.json": "085ff33204b84c3d7b05a92c3099bef600dd698bf6e6ab209cb0e5bfe748accd",
    "observations/gaze-3/acquisition/rgb-observation.npz": "5924f94656b6bf3536ed986f2d47433331e201d7ea911c3df7f1ef52c57a170c",
    "observations/gaze-3/acquisition/acquisition.json": "68fd96d8d541095ff8623b98dd74e22a8161bf593611739e6ea5cad126a52abd",
}
# ---- section 3b: accepted AB1c products opened only after the geometry freeze (REFERENCE / EVALUATION)
BENCH_PINS = {
    "oracle/correspondence-freeze.json": "e7f06f53d13707c23fbd1dd3d638090043be7ea53662c41c1524143769bf8733",
    "oracle/gaze-1/oracle-correspondences.npz": "e83eaa7b537abaa4def50def64d0d36bf034d270baa3f4e7ce6cfb0a7512b4a6",
    "oracle/gaze-2/oracle-correspondences.npz": "fd4568d59f3b7a40aef6c11442961749e45a8c3b6c1b1fa53c8934dd636b8831",
    "oracle/gaze-3/oracle-correspondences.npz": "67d433311f1f940637573c9135d6947bad8363411cb45e52412f070874c20c73",
    "freeze/geometry-freeze.json": "1b7e2207af58a777f04b23903d1da25bca2a3cf39ccd454d8813491f2e4a4b9a",
    "spherical/gaze-1/epipolar-result.npz": "3e5024f3a75a34819f742c231b3b448ac6b8486a840f17c9c5f780798c52cd98",
    "spherical/gaze-2/epipolar-result.npz": "d2306f9c200a11e749bf59d71b535a2f4c8a32e08850618901b9402412fee4e2",
    "spherical/gaze-3/epipolar-result.npz": "f1de4f1d6be91880067446ad8a104f875dd7e4757c2c5176be2410ed92d0b561",
    "observations/gaze-1/evaluation_only/reference-observation.npz":
        "7c458254960befefbfef160e0904dc8ab9c34bb1d3791d8f59fd55403b323f2e",
    "observations/gaze-2/evaluation_only/reference-observation.npz":
        "c8b1833ef4df720a0252b89c6886ba6788be4d94f877cfd8ba0bc4781b9e47b6",
    "observations/gaze-3/evaluation_only/reference-observation.npz":
        "740d7ad78f9afc7eb867e20df186bf40b964e31a840a5ba2e85dd4bdcd81e5d0",
    "evaluation/gaze-1/evaluation-result.npz": "12270a99be04e3476eb367dad52327102224141f62f8191c1e256a3259863143",
    "evaluation/gaze-2/evaluation-result.npz": "bd937015ed30b8f92ccafeeaf62fd1830dc319adcac5ce0c96d38d0cab7e1484",
    "evaluation/gaze-3/evaluation-result.npz": "bfbf300c5cb741cb8cbda36b957eb21dee4a2bc7316f31f4144906d3452e3e99",
}

# ---- section 3c: accepted code reused read-only (sha256 at the base); a mismatch is a STOP
SOURCE_PINS = {
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

# ---- sections 6-13: the instrument and the frozen matcher
RAW_SIZE = 640
CORE_SIZE = 256
CORE_ORIGIN = (RAW_SIZE - CORE_SIZE) // 2          # 192: raw u, v = 192..447
FOCAL_PX = 1217.8386501404907
IPD_M = 0.063
BASELINE_AXIS = (1.0, 0.0, 0.0)
LUMA = (0.2126, 0.7152, 0.0722)                    # fsg_stereo.refine_disparity coefficients, on linear_to_u8
PATCH_HALF = 2                                     # 5 x 5 samples, offsets -2..+2
PATCH = 2 * PATCH_HALF + 1
MIN_LOCAL_STD_U8 = 0.5                             # = fsg_stereo.MIN_LOCAL_STD_U8 (verified by ``source``)
SPACING_PX = 1.0
TIE_EPS = 1e-12
TOP_K = 8
PEAK_SEPARATION_PX = 3.0
REFINE_BOUND_SAMPLES = 0.75                        # the accepted FSG maximum local refinement
Z_EPS = 1e-12                                      # projection in front: h_2 > Z_EPS
DEN_EPS = 1e-12                                    # = ab1b_spec.DEN_EPS (verified by ``source``)
REASONS = {0: "VALID", 1: "LOW_TEXTURE", 2: "NO_SEARCH_SUPPORT", 3: "NO_TEXTURED_CANDIDATE", 4: "LEFT_PATCH_OUTSIDE"}
MATCHER = {
    "name": "AB1d direct raw-image spherical epipolar search + 5 x 5 local angular patch + ZNCC + one 1-D parabola",
    "photometry": "G = 0.2126 U_R + 0.7152 U_G + 0.0722 U_B, U = fsg_stereo.linear_to_u8(rgb) (float64, not re-rounded)",
    "patch": "theta_c + i delta, phi_c + j delta / sin(theta_c), i, j in -2..2 (i-major), delta = atan(1 / K[0][0]); "
             "projected h = K R_hc^T d (h_2 > 1e-12); bilinear, inside 0 <= u <= W - 1, 0 <= v <= H - 1",
    "line": "n = (b x d_L) / |b x d_L|, b = +X; l = K_R^-T R_hc_R^T n; q(s) = q_inf + s t, q_inf = proj_R(d_L), "
            "t = (l_1, -l_0) / |.| oriented so theta_R increases",
    "candidates": "s_k = k * 1.0, k >= 1, centre in the raster; admissible: finite ray, cos(phi_k - phi_L) > 0, "
                  "theta_k > theta_L, cot theta_L - cot theta_k >= 1e-12, rho finite > 0, right patch exists",
    "score": "ZNCC (float64); texture = population std of 25 samples >= 0.5 (left: LOW_TEXTURE; right: candidate invalid)",
    "best": "max ZNCC; ties within 1e-12 -> smallest k",
    "peaks": "local peaks (>= valid neighbours - 1e-12); greedy TOP_K = 8, earliest within 1e-12 of remaining max, "
             "suppress |k - k_acc| < 3 px",
    "refinement": "3-point parabola at the best k if both neighbours valid and D = S- - 2 S0 + S+ < 0; "
                  "x = (S- - S+) / (2 D) clipped to +/-0.75 sample; no iteration",
    "thresholds": "texture only; no ZNCC, uniqueness, ratio or left-right threshold; no depth interval",
    "constants": {"PATCH": PATCH, "LUMA": list(LUMA), "MIN_LOCAL_STD_U8": MIN_LOCAL_STD_U8, "SPACING_PX": SPACING_PX,
                  "TIE_EPS": TIE_EPS, "TOP_K": TOP_K, "PEAK_SEPARATION_PX": PEAK_SEPARATION_PX,
                  "REFINE_BOUND_SAMPLES": REFINE_BOUND_SAMPLES, "Z_EPS": Z_EPS, "DEN_EPS": DEN_EPS},
    "not_used": ["Position", "Object Index", "AB1c oracle", "AB1c evaluation", "planar result", "truth", "depth",
                 "range interval", "instance catalog", "EXR", "controller state", "SGBM", "learned model"],
}
THREADS = 16
BATCH = 128

# ---- sections 17-22: evaluation (post-freeze, descriptive)
ORACLE_PEAK_RADIUS_PX = 1.5
LANDSCAPE_OFFSETS_PX = (-1.0, -0.5, 0.0, 0.5, 1.0)
AT_BEST_TOL = 1e-9
PX_BINS = (0.10, 0.25, 0.50, 1.00)
METRIC_FRACTIONS_M = (0.012, 0.025, 0.050)
TOPK_FRACTIONS = (1, 3, 5, 8)
QUANTILES = {"min": 0.0, "p05": 0.05, "median": 0.5, "p90": 0.90, "p95": 0.95, "p99": 0.99, "max": 1.0}
STRATA = ("peak_margin", "left_patch_std_u8", "best_zncc", "peak_curvature", "candidate_count")
CHECK_SUBSET = (32, 7)                             # core index % 32 == 7 (2,048 left pixels per gaze)
EXAMPLES = ("median-error", "high-confidence low-error", "smallest peak margin", "large-error percentile")

# ---- section 24: synthetic known answers (software tolerances; synthetic data only)
SYN_GAZE = (-8.0, 9.0)
SYN_VERGENCE_M = 2.10
SYN_DTHETA_SAMPLES = 40.0
SYN_SEED = 20261004
SYN_LINE_PX = 1e-9
SYN_PHI_RAD = 1e-12
SYN_TEXTURE_PX = (3.0, 8.0)       # contract section 33 (pre-canonical): structured at the 5 x 5 patch scale
SYN_ROUGH_PX = (2.2, 3.5)         # rough scene for the spacing / peak-separation detection cases
SYN_STRIDE = 3                     # main-scene left pixels: core index % 3 == 0
SYN_CORRECT_INT = 0.99            # integer bin: discrete k = round(s_true)
SYN_CORRECT_FRACTION = 0.80       # sub-pixel bins: discrete k within 1 px of s_true (sanity bound; the measured
                                   # half-sample phase penalty is recorded in contract section 33)
SYN_REF_MEDIAN_PX, SYN_REF_P95_PX = 0.12, 0.35    # refined |s_est - s_true| among correct discrete peaks
SYN_BIN_HALF = 0.02
SYN_FAIL_PX = 5.0
SYN_REPEAT_PERIOD_PX = 7.0

# ---- section 30: commands, run layout
RUN_DEFAULT = SHARED / "previews/active-bootstrap/ab1d-safe-forward-natural-correspondence"
VIS_DEFAULT = SHARED / "visuals/active-bootstrap/ab1d-safe-forward-natural-correspondence"
COMMANDS = ("source", "synthetic", "match", "freeze-correspondence", "spherical", "freeze-geometry", "evaluate",
            "visualize")
CANONICAL = ("source", "match", "freeze-correspondence", "spherical", "freeze-geometry", "evaluate")
MATCH_CODE = ("tools/active_bootstrap/ab1d_match.py", "tools/active_bootstrap/ab1d_spec.py",
              "tools/active_bootstrap/ab1d_run.py", "tools/fsg_geometry.py", "tools/fsg_stereo.py",
              "tools/active_bootstrap/ab1b_geometry.py", "tools/active_bootstrap/ab1b_spec.py",
              "tools/natural_bootstrap/nb1a_guard.py")
SPHERICAL_CODE = ("tools/active_bootstrap/ab1b_geometry.py", "tools/active_bootstrap/ab1b_spec.py",
                  "tools/active_bootstrap/ab1d_run.py", "tools/active_bootstrap/ab1d_spec.py", "tools/fsg_geometry.py",
                  "tools/natural_bootstrap/nb1a_guard.py")


def a1c(rel: str) -> Path:
    return A1C_RUN / rel


def obs_path(g: str, name: str) -> Path:
    return A1C_RUN / OBS_TMPL.format(g=g, name=name)


def calibration_path(g: str) -> Path:
    return obs_path(g, "calibration.json")


def rgb_path(g: str) -> Path:
    return obs_path(g, "rgb-observation.npz")


def reference_path(g: str) -> Path:
    return A1C_RUN / REF_TMPL.format(g=g)


def oracle_path(g: str) -> Path:
    return A1C_RUN / ORACLE_TMPL.format(g=g)


def perfect_path(g: str) -> Path:
    return A1C_RUN / SPHERICAL_TMPL.format(g=g)


def a1c_eval_path(g: str) -> Path:
    return A1C_RUN / EVAL_TMPL.format(g=g)


def config_sha256(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()


def delta(focal_px: float) -> float:
    return math.atan(1.0 / focal_px)
