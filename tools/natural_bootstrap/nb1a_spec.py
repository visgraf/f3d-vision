"""Natural Bootstrap-1a: declared constants and the deterministic spherical grid geometry.

Contract: docs/natural-bootstrap/nb1a-range-connectivity-contract.md, sections 2-8.  Plain Python +
NumPy.  Discovery reads only these constants, this geometry and the stripped range input.  The checker
keeps its own literal copies.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

SHARED = Path("/home/lvelho/rd/f3d-vision")
BASE_COMMIT = "0fe83af8c28c99b6e533972c7b2ec72a8a93b489"

# ---- the accepted observation and its sources (contract section 2)
SOURCES = {
    "exr": (SHARED / "previews/breadth-1-classroom-234-spherical-glance/render/canonical.exr",
            "4ea036fc74eab3b3ab06a0c4470c2b01740c9322de0eea522f957ddfffa172f8"),
    "seeds": (SHARED / "previews/controller-01-full/bootstrap/seeds.json",  # head pose only
              "6ef833196de2462370ba4b2a2a8eed3fbde7f0a61e5aa6cbaf95f66947134c4f"),
    "catalog": (SHARED / "previews/controller-01-full/bootstrap/instance_catalog.json",  # evaluation only
                "be26594254b03fbda7216ac1a942a5c800cf4bdd8f79751a2b8c22d6bfb4c7ae"),
    "breadth1_summary": (SHARED / "previews/breadth-1-classroom-234-spherical-glance/summary.json",  # evaluation only
                         "b0744571be530599446e48ec0379c429d3e21acc08fdf153930fd82d4842be04"),
}

# ---- grid (contract section 4)
WIDTH, HEIGHT = 720, 360
CELLS = WIDTH * HEIGHT
CELL_DEG = 0.5
FORWARD_OFFSETS = ((0, 1), (1, -1), (1, 0), (1, 1))   # each unordered 8-neighbour pair once; columns wrap

# ---- the single scientific parameter (declared before any Classroom discovery)
MAX_SURFACE_SLANT_DEG = 75.0
C_MAX = 1.0 / math.cos(math.radians(MAX_SURFACE_SLANT_DEG))   # sec 75 deg, computed, never rounded
CLEARANCE_TIE_EPS_RAD = 1e-12

# ---- declared distributions (contract section 8)
SUPPORT_EDGES_SR = [10.0 ** (k / 2.0) for k in range(-14, 3)]
CELL_COUNT_EDGES = [2 ** k for k in range(0, 19)]
CLEARANCE_EDGES_DEG = [2.0 ** (k / 2.0) for k in range(-6, 15)]
RANGE_EDGES_M = [0.0] + [2.0 ** (k / 2.0) for k in range(-6, 13)] + [math.inf]
RGB_CONTRAST_EDGES = [10.0 ** (k / 4.0) for k in range(-24, 2)]
QUANTILES = [0.0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1.0]
TOP_K = [1, 5, 10, 25]

TRUTH_ORACLE = "ORACLE INPUT"
TRUTH_DERIVED = "DERIVED"
TRUTH_REFERENCE = "REFERENCE / EVALUATION"

DISCOVERY_CONFIG = {
    "WIDTH": WIDTH, "HEIGHT": HEIGHT, "CELL_DEG": CELL_DEG, "FORWARD_OFFSETS": [list(o) for o in FORWARD_OFFSETS],
    "MAX_SURFACE_SLANT_DEG": MAX_SURFACE_SLANT_DEG, "C_MAX": C_MAX, "CLEARANCE_TIE_EPS_RAD": CLEARANCE_TIE_EPS_RAD,
    "continuity": "C_ij = ||p_i - p_j|| / (((r_i + r_j) / 2) * atan2(||d_i x d_j||, d_i . d_j)); retain iff C_ij <= C_MAX",
    "hypotheses": "connected components of the valid-cell graph under retained edges; every component kept",
    "ordering": "support desc (folded-row math.fsum), cells desc, smallest (row, col) cell asc",
    "boundary": "an existing 8-neighbour (longitude wraps) is invalid or in another component",
    "clearance": "multi-source Dijkstra from boundary cells along retained edges, cost = delta_ij",
    "seed": "max clearance; ties within 1e-12 rad -> smaller row, then column; singleton -> itself (0); "
            "no boundary -> NO_BOUNDARY_FALLBACK smallest cell (clearance null)",
}


def yaw_centers_deg() -> np.ndarray:
    return -180.0 + CELL_DEG * (np.arange(WIDTH, dtype=np.float64) + 0.5)


def pitch_centers_deg() -> np.ndarray:
    return 90.0 - CELL_DEG * (np.arange(HEIGHT, dtype=np.float64) + 0.5)


def cell_directions_h() -> np.ndarray:
    """(HEIGHT, WIDTH, 3) head-frame unit directions of the cell centres (as Breadth-1)."""
    yaw, pitch = np.meshgrid(np.radians(yaw_centers_deg()), np.radians(pitch_centers_deg()))
    return np.stack([np.sin(yaw) * np.cos(pitch), np.sin(pitch), -np.cos(yaw) * np.cos(pitch)], axis=-1)


def folded_row_deltas() -> list[float]:
    """Delta s_k = sin(pi/2 - k pi/360) - sin(pi/2 - (k+1) pi/360), k = 0..179 (Python math.sin)."""
    return [math.sin(math.pi / 2 - k * math.pi / HEIGHT) - math.sin(math.pi / 2 - (k + 1) * math.pi / HEIGHT)
            for k in range(HEIGHT // 2)]


_DS = folded_row_deltas()


def support_sr(row_counts) -> float:
    """Canonical spherical support (contract 5): (2 pi / 720) * fsum_k (n_k + n_(359-k)) * Delta s_k."""
    n = np.asarray(row_counts, np.int64)
    m = n[: HEIGHT // 2] + n[::-1][: HEIGHT // 2]
    return (2.0 * math.pi / WIDTH) * math.fsum(int(mk) * dk for mk, dk in zip(m.tolist(), _DS) if mk)


def neighbor_pairs() -> tuple[np.ndarray, np.ndarray]:
    """All seam-aware 8-neighbour pairs, each unordered pair once, as flat indices (row-major)."""
    rows, cols = np.meshgrid(np.arange(HEIGHT), np.arange(WIDTH), indexing="ij")
    a_list, b_list = [], []
    for dr, dc in FORWARD_OFFSETS:
        r2 = rows + dr
        ok = r2 < HEIGHT
        c2 = (cols + dc) % WIDTH
        a_list.append((rows * WIDTH + cols)[ok])
        b_list.append((r2 * WIDTH + c2)[ok])
    return np.concatenate(a_list).astype(np.int64), np.concatenate(b_list).astype(np.int64)
