"""Active Bootstrap-1c: declared constants, pinned sources and configurations (safe-forward planar vs spherical).

Contract: docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-contract.md.  Standard library only, so both
interpreters (Blender's and the host .venv) can import it.  The checker keeps its own literal copies.
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
BASE_COMMIT = "c2b8373b8ba7849ad4411e28c55c31257d15f2af"   # accepted main after the AB1b closure and roadmap
CANONICAL_REMOTE = "visgraf/f3d-vision"
EXPERIMENT = "Active Bootstrap-1c: Safe-Forward Planar vs Spherical Geometry"
CONTRACT = "docs/active-bootstrap/ab1c-safe-forward-planar-vs-spherical-contract.md"
MARKER = "ACTIVE_BOOTSTRAP1C_SAFE_FORWARD_PLANAR_SPHERICAL_COMPLETE"

TRUTH_ORACLE, TRUTH_DERIVED, TRUTH_REFERENCE = "ORACLE INPUT", "DERIVED", "REFERENCE / EVALUATION"
SELECTION_LABEL = "EXPERIMENT SELECTION"

# ---- section 2: the one selection input (the frozen accepted NB1c RGB attention raster)
NB1C_RUN = SHARED / "previews/natural-bootstrap-1c-rgb-candidate-gaze"
ATTENTION = (NB1C_RUN / "selection/attention-score.npz",
             "4bfee30e0a1a24007925c57d338627449484dffa2a9805fd13b72727c04ef552")
NB1C_FREEZE = (NB1C_RUN / "selection/rgb-gaze-freeze.json",
               "87a3bab01f55051316ac1eb45b48f394211f4c7a3a317fd0e61c0e52c36f9b37")
NB1C_MANIFEST = (NB1C_RUN / "manifest.json", "524f8fad71ccb8fd9359fa3221f4de6be3af40be8f3e5fa7cddeb482acedd87e")
GRID_DIRECTIONS_SHA256 = "d72076612515f1079ffce611e81a5b5e1675804c1f8d600cafc31a28829d0b73"
NB1C_RGB = (SHARED / "previews/natural-bootstrap-1a-range-connectivity/input/rgb-sensory.npz",
            "cd2600e678fe7f33471e50bee5443128dd5470cc2b380eb7b34a22d3e4ad2c3e")   # figures only (display)

# ---- section 2: accepted code reused read-only (sha256 at the base); a mismatch is a STOP
SOURCE_PINS = {
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
BLEND = "scenes/classroom/classroom_eye.blend"
BLEND_SHA256 = "dca66a3257b909aef00b0331652c55f62a93a8dff0665d070fba7efa436953cc"
BLENDER = "blender"
HEAD_POSE_SOURCE = (SHARED / "previews/controller-01-full/bootstrap/seeds.json",
                    "6ef833196de2462370ba4b2a2a8eed3fbde7f0a61e5aa6cbaf95f66947134c4f")

# accepted runs: unchanged, never re-executed (identity only)
ACCEPTED_PRODUCTS = {
    "AB1a manifest": (SHARED / "previews/active-bootstrap/ab1a-first-natural-stereo-look/manifest.json",
                      "74eba4d6112f2de69fd797f9f41ff987e128ce1ecbcb5d48f05f597e9a2731fe"),
    "AB1a visuals manifest": (SHARED / "visuals/active-bootstrap/ab1a-first-natural-stereo-look/visuals-manifest.json",
                              "d38bfdc2b9158739cc635f3cbc5ba4a764e6234c5397ba50ca99780987b22da0"),
    "AB1b geometry freeze": (SHARED / "previews/active-bootstrap/ab1b-spherical-epipolar-geometry/geometry/geometry-freeze.json",
                             "942707a858c8b76cb65db503183853d27c55000eb2e59c6de4dfbcf025d21c7a"),
    "AB1b visuals manifest": (SHARED / "visuals/active-bootstrap/ab1b-spherical-epipolar-geometry/visuals-manifest.json",
                              "a1216d2c22095f6353260efeb93b452a7b429f7a3d29b7d760db8d27a056f88c"),
    "NB1a freeze": (SHARED / "previews/natural-bootstrap-1a-range-connectivity/discovery/bootstrap-freeze.json",
                    "c0236d0424a7724bfe57bf0a19bdf56899b7eadf5e059c9537e785f3a08b826a"),
    "NB1b freeze": (SHARED / "previews/natural-bootstrap-1b-foveal-serviceability/selection/serviceability-freeze.json",
                    "f99b7cae02498feb21ae1d80978b57c877c44984067d55c7fd2bbe189efb6e9a"),
    "NB1c freeze": NB1C_FREEZE,
}
AB1A_CATALOG = (SHARED / "previews/active-bootstrap/ab1a-first-natural-stereo-look/evaluation_only/instance-catalog.json",
                "3924b5b4bde3e694d99e3c86b351be0b7f23d447ae6eda917619462b92732c1c")

# ---- section 3: the binocular instrument (unchanged; equal to ab1a_spec, verified by ``source``)
PROFILE = "full"
RAW_SIZE = 640
CORE_SIZE = 256
CORE_ORIGIN = (RAW_SIZE - CORE_SIZE) // 2          # 192: raw x, y = 192..447
FOCAL_PX = 1217.8386501404907
IPD_M = 0.063
VERGENCE_M = 2.10
TANGENT_FRAME = "baseline_projected"
DEVICE = "OPTIX"
SPP = 256
SEEDS = {"L": 2111, "R": 2112}
EYE_POSE_TOL = 1e-6
CALIBRATION_TOL = 1e-9
REQUIRED_PASSES = ("Combined", "Position", "Object Index")
FORBIDDEN_PASSES = ("Depth", "Normal")
INHERITED_PASSES = ("Ambient Occlusion", "Diffuse Color", "Diffuse Direct", "Diffuse Indirect", "Emission",
                    "Glossy Color", "Glossy Direct", "Glossy Indirect", "Transmission Color", "Transmission Direct",
                    "Transmission Indirect")   # AB1a contract section 23 (pinned; evaluation_only only)

# ---- section 4: the SAFE-FORWARD envelope (design eligibility)
BASELINE_AXIS = (1.0, 0.0, 0.0)
FORWARD_AXIS = (0.0, 0.0, -1.0)
FORWARD_CONE_DEG = 20.0
FORWARD_CONE_RAD = math.radians(FORWARD_CONE_DEG)
LEVERAGE_MIN = 0.90
ANGLE_EPS_RAD = 1e-12          # the accepted NB1c boundary convention

# ---- section 5: selection (accepted NB1c rules, restricted to the eligible set)
K = 3
SCORE_TIE_REL = 1e-12
R_CENTER_RAD = math.radians(12.0 / 2.0)
D_MIN_RAD = 2.0 * math.atan(math.sqrt(2.0) * math.tan(R_CENTER_RAD))   # 16.90906721486762 deg; never rounded
D_MIN_DEG = math.degrees(D_MIN_RAD)
WIDTH, HEIGHT = 720, 360
SELECTION = {
    "name": "AB1c SAFE-FORWARD RGB-attention gaze selection",
    "input": "the frozen accepted NB1c attention raster A (attention-score.npz), read as stored, never recomputed",
    "candidates": "the 259,200 NB1c cell centres: yaw = -180 + 0.5 (col + 0.5), pitch = 90 - 0.5 (row + 0.5)",
    "forward_cone": "alpha_forward = acos(clamp(d_g . (0, 0, -1))) <= 20 deg + ANGLE_EPS_RAD",
    "leverage": "min over both eyes and all 65,536 nominal raw-core pixel rays (fsg_geometry.rays_h of "
                "make_calibration('full', yaw, pitch, 2.10, ipd 0.063, baseline_projected)) of sqrt(1 - d_x^2) >= 0.90",
    "ties": "tie set = eligible with A_max - A <= 1e-12 max(1, |A_max|); smaller row, then column",
    "nms": "greedy inside the eligible set; suppress eligible q with alpha(q, g_k) + 1e-12 < D_MIN (g_k included)",
    "K": K, "D_MIN_RAD": D_MIN_RAD, "FORWARD_CONE_DEG": FORWARD_CONE_DEG, "LEVERAGE_MIN": LEVERAGE_MIN,
    "ANGLE_EPS_RAD": ANGLE_EPS_RAD, "SCORE_TIE_REL": SCORE_TIE_REL, "score_threshold": None,
    "not_used": ["depth", "range", "Position", "Object Index", "instance catalog", "segmentation", "stereo result",
                 "head-pose record", "any AB1c render"],
}

# ---- sections 7-9: oracle (accepted AB1b), spherical (accepted AB1b), planar (accepted AB1a rectification)
PRODUCT_KEYS = ("left_core_row", "left_core_col", "uv_L", "uv_R")
PLANAR_W_EPS = 1e-12           # the raw ray must lie in front of the rectified image plane (h[2] > eps)
PLANAR_D_EPS = 1e-12           # |disparity| below this: no planar triangulation (numerical only)
RECT_CORE_BOUNDS = (CORE_ORIGIN - 0.5, CORE_ORIGIN + CORE_SIZE - 0.5)   # the fixed central rectified core, continuous
PLANAR = {
    "name": "AB1c planar tangent / projective stereo geometry (accepted AB1a rectification; perfect correspondence)",
    "rectification": "fsg_stereo.rectification(c): cv2.stereoRectify(K_L, 0, K_R, 0, (640, 640), R, T, "
                     "flags=CALIB_ZERO_DISPARITY, alpha=-1, newImageSize=(640, 640)); eye order L, R; "
                     "R, T = fsg_geometry.relative_pose(c)",
    "to_rectified": "h_s = R_s K_s^-1 (u, v, 1); (u', v') = (P_s[:, :3] h_s)[:2] / h_s[2]",
    "disparity": "d = u'_L - u'_R",
    "triangulation": "X_rect = fsg_geometry.reproject_q(Q_full, (u'_L, v'_L), d); "
                     "P_planar = fsg_geometry.rect_to_head(c, R1, X_rect)",
    "validity": "h_L[2] > 1e-12 and h_R[2] > 1e-12, finite rectified coordinates, |d| >= 1e-12 px, finite P_planar",
    "w_eps": PLANAR_W_EPS, "d_eps": PLANAR_D_EPS,
    "descriptive_only": ["rectified row residual v'_R - v'_L", "range_per_disparity_px = range_L_planar / d",
                         "containment in the 640 x 640 rectified raster and the central 256 x 256 rectified core"],
    "thresholds": "none (no z_rect interval, no disparity sign, no containment or conditioning threshold)",
    "not_used": ["Position", "Object Index", "truth XYZ", "SGBM", "matcher", "image remap of scene data"],
}
SUPPORT = {
    "name": "AB1c planar support diagnostic (accepted ab1a_stereo.prelook_geometry; calibration only)",
    "added": "support_finite = every rectification-map coordinate of the central core finite; spans = raw source "
             "max - min in x and y; support_two_dimensional = both spans >= 1 raw pixel (definitional, descriptive)",
    "two_dimensional_min_span_px": 1.0,
}

# ---- section 11: statistics (descriptive)
QUANTILES = {"min": 0.0, "p05": 0.05, "median": 0.5, "p90": 0.90, "p95": 0.95, "p99": 0.99, "max": 1.0}
ERROR_FRACTIONS_M = (0.001, 0.005, 0.010, 0.025)
MIN_INSTANCE_PAIRS = 50

# ---- section 14: synthetic known-answer tolerances (software / numerical; synthetic data only)
SYN_EXACT_M = 1e-8
SYN_FAIL_M = 1e-3
SYN_E2E_MEDIAN_M = 1e-4
SYN_E2E_MAX_M = 5e-4
SYN_GAZES = {"forward": (0.0, 0.0), "right": (12.0, 0.0), "left-up": (-8.0, 9.0)}
REHEARSAL_SPP = 64
REHEARSAL_AGREE_M = 1e-5        # Blender Position data (oracle skew ~8e-4 px); pre-canonical clarification (contract section 23)
SYN_FLOAT32_AGREE_M = 1e-6      # float32 analytic Position (synthetic case 15)
REHEARSAL_MEDIAN_M = 1e-3
REHEARSAL_PROJECTION_PX = 1e-3

# ---- sections 18-19: commands, run layout
RUN_DEFAULT = SHARED / "previews/active-bootstrap/ab1c-safe-forward-planar-vs-spherical"
VIS_DEFAULT = SHARED / "visuals/active-bootstrap/ab1c-safe-forward-planar-vs-spherical"
GAZES = ("gaze-1", "gaze-2", "gaze-3")
COMMANDS = ("synthetic", "rehearse", "source", "select", "freeze-selection", "plan", "preflight", "acquire", "oracle",
            "freeze-correspondence", "spherical", "planar", "freeze-geometry", "compare", "evaluate", "visualize")
CANONICAL = ("source", "select", "freeze-selection", "plan", "preflight", "acquire", "oracle", "freeze-correspondence",
             "spherical", "planar", "freeze-geometry", "compare", "evaluate")
SELECTION_FILES = ("selection/safe-forward-mask.npz", "selection/selected-gazes.json", "selection/nms-rounds.json",
                   "selection/selection-summary.json", "selection/selection-opened-files.json")
SELECT_CODE = ("tools/active_bootstrap/ab1c_select.py", "tools/active_bootstrap/ab1c_spec.py", "tools/fsg_geometry.py",
               "tools/natural_bootstrap/nb1a_spec.py", "tools/natural_bootstrap/nb1c_spec.py",
               "tools/natural_bootstrap/nb1c_attention.py", "tools/natural_bootstrap/nb1a_guard.py")
ORACLE_CODE = ("tools/active_bootstrap/ab1b_oracle.py", "tools/active_bootstrap/ab1b_spec.py",
               "tools/active_bootstrap/ab1c_run.py", "tools/active_bootstrap/ab1c_spec.py", "tools/fsg_geometry.py",
               "tools/natural_bootstrap/nb1a_guard.py")
SPHERICAL_CODE = ("tools/active_bootstrap/ab1b_geometry.py", "tools/active_bootstrap/ab1b_spec.py",
                  "tools/active_bootstrap/ab1c_run.py", "tools/active_bootstrap/ab1c_spec.py", "tools/fsg_geometry.py",
                  "tools/natural_bootstrap/nb1a_guard.py")
PLANAR_CODE = ("tools/active_bootstrap/ab1c_planar.py", "tools/active_bootstrap/ab1c_spec.py", "tools/fsg_stereo.py",
               "tools/fsg_geometry.py", "tools/active_bootstrap/ab1a_stereo.py", "tools/active_bootstrap/ab1a_spec.py",
               "tools/active_bootstrap/ab1b_geometry.py", "tools/natural_bootstrap/nb1a_guard.py")


def gaze_cell_centre(row: int, col: int) -> tuple[float, float]:
    """The NB1c / NB1a cell-centre convention (0.5-degree cells)."""
    return -180.0 + 0.5 * (col + 0.5), 90.0 - 0.5 * (row + 0.5)


def config_sha256(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
