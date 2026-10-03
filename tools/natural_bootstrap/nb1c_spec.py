"""Natural Bootstrap-1c: declared constants, the pinned RGB source and the accepted sensor geometry.

Contract: docs/natural-bootstrap/nb1c-rgb-candidate-gaze-contract.md, sections 2-11.  Plain Python +
NumPy.  Selection reads only these constants, this geometry and the coarse RGB proxy.  The spherical grid
convention is the accepted NB1a one (``nb1a_spec``, read-only); ``CORE_FOV_DEG`` comes from the sealed sensor
implementation ``tools/fsg_geometry.py``.  The checker keeps its own literal copies.
"""
from __future__ import annotations

import math
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))   # tools/: the sealed fsg_geometry

import fsg_geometry  # noqa: E402  (sealed sensor geometry, read-only)
import nb1a_spec as A  # noqa: E402  (accepted spherical grid convention, read-only)

SHARED = A.SHARED
BASE_COMMIT = "7d1c1b97e1e29be4bd5e45066507f9c12be006bc"   # main after the post-NB1b pivot

# ---- the RGB-only source (contract section 2)
RGB_SOURCE = SHARED / "previews/natural-bootstrap-1a-range-connectivity/input/rgb-sensory.npz"
RGB_SHA256 = "cd2600e678fe7f33471e50bee5443128dd5470cc2b380eb7b34a22d3e4ad2c3e"
RGB_ARRAYS = ("srgb8",)

# ---- the accepted sensor geometry (contract section 3)
SENSOR_SOURCE = HERE.parent / "fsg_geometry.py"
SENSOR_SOURCE_SHA256 = "ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54"
SENSOR_SOURCE_BLOB = "ad47c1eff6db2b9bd29340fdd633d9c09718d070"
CORE_FOV_DEG = fsg_geometry.CORE_FOV_DEG
R_CENTER_DEG = CORE_FOV_DEG / 2.0
R_CENTER_RAD = math.radians(R_CENTER_DEG)
R_SURROUND_DEG = CORE_FOV_DEG
R_SURROUND_RAD = math.radians(R_SURROUND_DEG)
R_FULL_RAD = math.atan(math.sqrt(2.0) * math.tan(R_CENTER_RAD))   # the square core's corner; never rounded
R_FULL_DEG = math.degrees(R_FULL_RAD)
D_MIN_RAD = 2.0 * R_FULL_RAD
D_MIN_DEG = math.degrees(D_MIN_RAD)
ANGLE_EPS_RAD = 1e-12
SCORE_TIE_REL = 1e-12
VAR_EPS = 1e-12            # squared linear-RGB units; a numerical denominator guard, not a fitted threshold

# ---- the declared attention budget (contract section 4)
K = 6

# ---- grid (contract section 5): the accepted NB1a / Breadth-1 convention
WIDTH, HEIGHT = A.WIDTH, A.HEIGHT
CELLS = WIDTH * HEIGHT
CELL_DEG = A.CELL_DEG
BAND_MARGIN_DEG = 1.0      # rows farther than R + 1 deg in latitude cannot hold a member (alpha >= |d pitch|)
QUANTILES = {"min": 0.0, "median": 0.5, "p90": 0.90, "p95": 0.95, "p99": 0.99, "max": 1.0}

TRUTH_ORACLE, TRUTH_DERIVED, TRUTH_REFERENCE = A.TRUTH_ORACLE, A.TRUTH_DERIVED, A.TRUTH_REFERENCE

SENSOR_CONSTANTS = {"CORE_FOV_DEG": CORE_FOV_DEG, "R_CENTER_DEG": R_CENTER_DEG, "R_CENTER_RAD": R_CENTER_RAD,
                    "R_SURROUND_DEG": R_SURROUND_DEG, "R_SURROUND_RAD": R_SURROUND_RAD, "R_FULL_RAD": R_FULL_RAD,
                    "R_FULL_DEG": R_FULL_DEG, "D_MIN_RAD": D_MIN_RAD, "D_MIN_DEG": D_MIN_DEG,
                    "ANGLE_EPS_RAD": ANGLE_EPS_RAD}
SELECTION_CONFIG = {
    **SENSOR_CONSTANTS, "SCORE_TIE_REL": SCORE_TIE_REL, "VAR_EPS": VAR_EPS, "K": K, "WIDTH": WIDTH, "HEIGHT": HEIGHT,
    "CELL_DEG": CELL_DEG,
    "source": "rgb-sensory.npz (srgb8 only); ORACLE INPUT controlled sensory proxy; nothing else is read",
    "candidates": "all 259,200 cell centres (NB1a convention); no validity mask",
    "distance": "alpha = atan2(||d_i x d_g||, d_i . d_g) on the head-frame cell-centre directions",
    "weights": "w_j = (2 pi / WIDTH) (sin(pi/2 - j pi/HEIGHT) - sin(pi/2 - (j+1) pi/HEIGHT))",
    "linear": "c = srgb8/255; c/12.92 if c <= 0.04045 else ((c + 0.055)/1.055)**2.4 (Python float64 per code)",
    "center": "alpha <= R_CENTER + ANGLE_EPS_RAD",
    "surround": "R_CENTER + ANGLE_EPS_RAD < alpha <= R_SURROUND + ANGLE_EPS_RAD",
    "statistics": "W_R = sum w; mu_R = sum w rgb / W_R; V_R = sum w ||rgb - mu_R||^2 / W_R (linear RGB)",
    "score": "A = ||mu_C - mu_S|| / sqrt(V_C + V_S + VAR_EPS)",
    "numerics": "row-interval membership at reference column 0 (STOP unless an exact circular interval); symmetric "
                "incremental row box sums; rows added in ascending order; SURROUND = 12-deg disk - CENTER; values "
                "shifted by the per-channel median m; V_R = sum w ||rgb - m||^2 / W_R - ||mu_R - m||^2, not clamped",
    "ties": "tie set = eligible with A_max - A <= SCORE_TIE_REL max(1, |A_max|); smaller row, then column",
    "nms": "greedy; suppress eligible q with alpha(q, g_k) + ANGLE_EPS_RAD < D_MIN (g_k included); exactly K; "
           "no score threshold; no clustering or movement",
}


def yaw_centers_deg() -> np.ndarray:
    return A.yaw_centers_deg()


def pitch_centers_deg() -> np.ndarray:
    return A.pitch_centers_deg()


def cell_directions_h() -> np.ndarray:
    """(HEIGHT, WIDTH, 3) head-frame unit directions of the cell centres (the accepted NB1a convention)."""
    return A.cell_directions_h()


def row_weights(weighted: bool = True) -> np.ndarray:
    """Solid angle of one cell of each row (contract section 5); ``weighted=False`` exists only for a mutant."""
    if not weighted:
        return np.ones(HEIGHT, np.float64)
    dl = 2.0 * math.pi / WIDTH
    return np.array([dl * (math.sin(math.pi / 2 - j * math.pi / HEIGHT) - math.sin(math.pi / 2 - (j + 1) * math.pi / HEIGHT))
                     for j in range(HEIGHT)], np.float64)


def srgb_to_linear(code: int) -> float:
    """Standard sRGB transfer inverse for one 8-bit code (contract section 6), in Python float64."""
    c = code / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_table(linear: bool = True) -> np.ndarray:
    """The 256-entry look-up table; ``linear=False`` (gamma-space values) exists only for a mutant."""
    return np.array([srgb_to_linear(k) if linear else k / 255.0 for k in range(256)], np.float64)
