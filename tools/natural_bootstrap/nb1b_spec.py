"""Natural Bootstrap-1b: declared constants, pinned NB1a sources and the accepted sensor geometry.

Contract: docs/natural-bootstrap/nb1b-foveal-serviceability-contract.md, sections 2-9.  Plain Python +
NumPy.  The spherical grid and the canonical support are the accepted NB1a ones (``nb1a_spec``, read-only);
``CORE_FOV_DEG`` comes from the sealed sensor implementation ``tools/fsg_geometry.py``.  The checker keeps
its own literal copies.
"""
from __future__ import annotations

import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))   # tools/: the sealed fsg_geometry

import fsg_geometry  # noqa: E402  (sealed sensor geometry, read-only)
import nb1a_spec as A  # noqa: E402  (accepted NB1a grid geometry, read-only)

SHARED = A.SHARED
BASE_COMMIT = "9c01b8a62813d097940ad5e6e3e95c5d3e3ead83"           # main after NB1a acceptance
NB1A_ACCEPTED_COMMIT = "dcd294fc7dead16e9d492e8c0fd03a3e3df11e02"
NB1A_REPORT_COMMIT = "a0c98beb498fb0b869f53eb8ca97479106312f80"
NB1A_FROZEN_AT = "6b63cdcd9776fd28726db67dba487453f55383d3"
NB1A_BRANCH = "natural-bootstrap/nb1a-range-connectivity"
NB1A_RUN = SHARED / "previews/natural-bootstrap-1a-range-connectivity"
NB1A_HYPOTHESES = 453

# ---- selection inputs (contract section 2): exactly these five files, under NB1A_RUN/discovery
SELECTION_INPUTS = {
    "bootstrap-freeze.json": "c0236d0424a7724bfe57bf0a19bdf56899b7eadf5e059c9537e785f3a08b826a",
    "hypothesis-raster.npz": "513a15e0077fc1f5d84847ff020386687ce7ec28477b71ddc349378fb00bae88",
    "hypotheses.json": "eecf180faecd7765e15c162b76ae1427dc12212026f439d608f21b9c4357009b",
    "seeds.json": "c0362d9c898303869117bdd3bb303dadaf15c2d19b94733467fe2ade7c1fb556",
    "discovery-summary.json": "fac0adb39331d9ff2a3305791b2aff3f0edbd2a43503d3d3572437a74cf2e4ec",
}
# ---- evaluation-only inputs (contract section 2), under NB1A_RUN; opened only after the freeze verifies
EVALUATION_INPUTS = {
    "input/rgb-sensory.npz": "cd2600e678fe7f33471e50bee5443128dd5470cc2b380eb7b34a22d3e4ad2c3e",
    "evaluation/overlap-summary.json": "1ad980a4a84af7e0e63b6f81360c85c77e3863d7baa324bf45bcdedfe65691cb",
    "evaluation/overlap-matrix.npz": "e4f4bde03d2bfb82cc8a44ab6cbc3b74afec624677051da6fc882c96e502462d",
    "evaluation/reference-cells.npz": "54a58d28eab4ade81c7e945fefb379ce6d13f5a149797324bdbb23f1f84f9f76",
}

# ---- the accepted sensor geometry (contract section 3)
SENSOR_SOURCE = HERE.parent / "fsg_geometry.py"
SENSOR_SOURCE_SHA256 = "ae3779bc5cbe8f9702227ae9f123c6be1abe394a0a3c617627f38f171c556c54"
SENSOR_SOURCE_BLOB = "ad47c1eff6db2b9bd29340fdd633d9c09718d070"
CORE_FOV_DEG = fsg_geometry.CORE_FOV_DEG
R_CENTER_DEG = CORE_FOV_DEG / 2.0
R_CENTER_RAD = math.radians(R_CENTER_DEG)
R_FULL_RAD = math.atan(math.sqrt(2.0) * math.tan(R_CENTER_RAD))   # the square core's corner; never rounded
R_FULL_DEG = math.degrees(R_FULL_RAD)
ANGLE_EPS_RAD = 1e-12

# ---- environment role and classes (contract sections 6-7)
ENV_SUPPORT_SR = 2.0 * math.pi          # strictly more than one hemisphere of spherical support
ENVIRONMENT, PRIMARY, SECONDARY, MARGINAL, EDGE_ONLY = (
    "ENVIRONMENT_CANDIDATE", "PRIMARY_LOOK", "SECONDARY_LOOK", "MARGINAL", "EDGE_ONLY")
CLASSES = [ENVIRONMENT, PRIMARY, SECONDARY, MARGINAL, EDGE_ONLY]
QUEUED = {PRIMARY: "primary", SECONDARY: "secondary"}

TRUTH_ORACLE, TRUTH_DERIVED, TRUTH_REFERENCE = A.TRUTH_ORACLE, A.TRUTH_DERIVED, A.TRUTH_REFERENCE

SENSOR_CONSTANTS = {"CORE_FOV_DEG": CORE_FOV_DEG, "R_CENTER_DEG": R_CENTER_DEG, "R_CENTER_RAD": R_CENTER_RAD,
                    "R_FULL_RAD": R_FULL_RAD, "R_FULL_DEG": R_FULL_DEG, "ANGLE_EPS_RAD": ANGLE_EPS_RAD}
SELECTION_CONFIG = {
    **SENSOR_CONSTANTS, "ENV_SUPPORT_SR": ENV_SUPPORT_SR, "WIDTH": A.WIDTH, "HEIGHT": A.HEIGHT, "CELL_DEG": A.CELL_DEG,
    "sensor": "nominal square measurement core of CORE_FOV_DEG (tools/fsg_geometry.py); R_CENTER = CORE_FOV_DEG / 2 "
              "(inscribed disk); R_FULL = atan(sqrt(2) tan R_CENTER) (circumscribed disk)",
    "seed": "the frozen NB1a seed (row, col), unchanged; direction = NB1a cell-centre direction",
    "distance": "alpha_i = atan2(||d_s x d_i||, d_s . d_i) over all 259,200 cell centres (full sphere, no prefilter)",
    "footprint": "CENTER = {alpha_i <= R_CENTER + ANGLE_EPS_RAD}; FULL = {alpha_i <= R_FULL + ANGLE_EPS_RAD}",
    "safe": "every footprint cell has valid NB1a range (label > 0) and belongs to H; no-geometry counts as outside",
    "environment": "support_sr > 2 pi (NB1a canonical support); geometric, not semantic",
    "classes": "non-environment: PRIMARY_LOOK iff FULL safe; SECONDARY_LOOK iff !FULL and CENTER safe; "
               "MARGINAL iff !CENTER and clearance > 0; EDGE_ONLY iff clearance == 0",
    "invariants": "clearance == 0 implies CENTER unsafe; no null clearance; else STOP",
    "queue_order": "clearance desc, support_sr desc, id asc; PRIMARY_LOOK and SECONDARY_LOOK only",
}
