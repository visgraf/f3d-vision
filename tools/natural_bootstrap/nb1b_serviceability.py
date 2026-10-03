"""Natural Bootstrap-1b: sensor-qualified serviceability of the frozen NB1a seeds (the selection core).

Contract: docs/natural-bootstrap/nb1b-foveal-serviceability-contract.md, sections 4-10.  The functions take
the frozen NB1a label raster and hypothesis records.  They read no RGB, no Object Index, no catalog and no
evaluation product; ``load_selection_inputs`` opens exactly the NB1a discovery products it needs.  No seed is
moved, no hypothesis is changed, and no score is computed.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

import nb1a_discovery as D   # accepted NB1a binning / quantile helpers, read-only
import nb1a_spec as A
import nb1b_spec as SP

SEED_FIELDS = ("row", "col", "yaw_deg", "pitch_deg", "range_m", "clearance_rad", "fallback", "tied_candidates")
STAT_KEYS = ("total_cells", "own_cells", "other_cells", "other_hypotheses", "invalid_cells", "containment_fraction",
             "boundary_tie_cells", "safe")


class PartitionInvariantError(RuntimeError):
    """The class rules would not partition the hypotheses (contract section 7): STOP for Luiz/Chat."""


def load_selection_inputs(disc: Path) -> dict:
    """The frozen NB1a label raster, hypothesis table, seeds and summary, cross-checked for consistency."""
    with np.load(disc / "hypothesis-raster.npz") as z:
        labels = np.asarray(z["labels"], np.int64)
    hyps = json.loads((disc / "hypotheses.json").read_text())["hypotheses"]
    seeds = json.loads((disc / "seeds.json").read_text())["seeds"]
    summ = json.loads((disc / "discovery-summary.json").read_text())
    if labels.shape != (A.HEIGHT, A.WIDTH):
        raise ValueError(f"label raster must be {A.HEIGHT} x {A.WIDTH}, got {labels.shape}")
    if not (len(hyps) == len(seeds) == summ["hypotheses"]):
        raise ValueError(f"hypothesis counts disagree: {len(hyps)}, {len(seeds)}, {summ['hypotheses']}")
    for k, (h, s) in enumerate(zip(hyps, seeds), start=1):
        if h["label"] != k or h["id"] != s["id"] or any(h["seed"][f] != s[f] for f in SEED_FIELDS):
            raise ValueError(f"seed / hypothesis records disagree at {h['id']}")
    return {"labels": labels, "hypotheses": hyps, "seeds": seeds, "summary": summ}


# ------------------------------------------------------------------ section 5: the footprint test
def angular_distance(d_s: np.ndarray, dirs: np.ndarray) -> np.ndarray:
    """alpha_i = atan2(||d_s x d_i||, d_s . d_i) for every row d_i of ``dirs``."""
    return np.arctan2(np.linalg.norm(np.cross(dirs, d_s), axis=1), dirs @ d_s)


def footprint(alpha: np.ndarray, radius: float, seed_col: int, seam_wrap: bool = True) -> np.ndarray:
    """Flat indices (ascending) of the cells with alpha <= radius + ANGLE_EPS_RAD (inclusive)."""
    inside = alpha <= radius + SP.ANGLE_EPS_RAD
    if not seam_wrap:   # mutation only: cells that are near only across the longitude seam are dropped
        inside &= np.abs(np.arange(alpha.size) % A.WIDTH - seed_col) <= A.WIDTH // 2
    return np.flatnonzero(inside)


def footprint_stats(cells: np.ndarray, alpha: np.ndarray, labels_flat: np.ndarray, label: int, radius: float,
                    invalid_unsafe: bool = True) -> dict:
    lab = labels_flat[cells]
    own = int((lab == label).sum())
    invalid = int((lab == 0).sum())
    other = len(cells) - own - invalid
    safe = own == len(cells) if invalid_unsafe else other == 0   # the second form exists for the mutation suite
    return {"total_cells": int(len(cells)), "own_cells": own, "other_cells": int(other),
            "other_hypotheses": len(set(lab[(lab != label) & (lab != 0)].tolist())), "invalid_cells": invalid,
            "containment_fraction": own / len(cells),
            "boundary_tie_cells": int((np.abs(alpha[cells] - radius) <= SP.ANGLE_EPS_RAD).sum()), "safe": bool(safe)}


# ------------------------------------------------------------------ sections 6-7: environment and classes
def classify(rec: dict) -> str:
    if rec["environment_candidate"]:
        return SP.ENVIRONMENT
    c = rec["clearance_rad"]
    if c is None:
        raise PartitionInvariantError(f"{rec['id']}: null clearance (NO_BOUNDARY_FALLBACK)")
    if c == 0.0 and rec["center"]["safe"]:
        raise PartitionInvariantError(f"{rec['id']}: zero clearance with a SAFE CENTER footprint")
    if rec["full"]["safe"]:
        return SP.PRIMARY
    if rec["center"]["safe"]:
        return SP.SECONDARY
    return SP.MARGINAL if c > 0.0 else SP.EDGE_ONLY


def serviceability(labels: np.ndarray, hyps: list[dict], *, r_center: float = SP.R_CENTER_RAD,
                   r_full: float = SP.R_FULL_RAD, env_support_sr: float = SP.ENV_SUPPORT_SR,
                   invalid_unsafe: bool = True, seam_wrap: bool = True) -> dict:
    """Footprints, containment and classes for every hypothesis, at its unchanged NB1a seed.

    ``r_center``, ``r_full``, ``env_support_sr``, ``invalid_unsafe`` and ``seam_wrap`` exist only so that the
    checker's mutation suite can build deliberately wrong variants."""
    dirs = A.cell_directions_h().reshape(-1, 3)
    lab = np.asarray(labels, np.int64).reshape(-1)
    records, center_cells, full_cells, full_alpha = [], [], [], []
    for h in hyps:
        s = h["seed"]
        flat = s["row"] * A.WIDTH + s["col"]
        d_s = dirs[flat]
        alpha = angular_distance(d_s, dirs)
        cen = footprint(alpha, r_center, s["col"], seam_wrap)
        ful = footprint(alpha, r_full, s["col"], seam_wrap)
        c = s["clearance_rad"]
        rec = {"id": h["id"], "label": h["label"], "cells": h["cells"], "support_sr": h["support_sr"],
               "fraction_of_4pi": h["fraction_of_4pi"], "range_m": h["range_m"],
               "clearance_rad": c, "clearance_deg": None if c is None else math.degrees(c),
               "seed": {f: s[f] for f in SEED_FIELDS}, "seed_direction_h": [float(x) for x in d_s],
               "environment_candidate": bool(h["support_sr"] > env_support_sr),
               "center": footprint_stats(cen, alpha, lab, h["label"], r_center, invalid_unsafe),
               "full": footprint_stats(ful, alpha, lab, h["label"], r_full, invalid_unsafe)}
        rec["class"] = classify(rec)
        records.append(rec)
        center_cells.append(cen)
        full_cells.append(ful)
        full_alpha.append(alpha[ful])
    queues = {name: queue(records, cls) for cls, name in SP.QUEUED.items()}
    for name, q in queues.items():
        rank = {e["id"]: e["rank"] for e in q}
        for r in records:
            if r["id"] in rank:
                r["queue"] = {"name": name, "rank": rank[r["id"]]}
    for r in records:
        r.setdefault("queue", None)
    return {"records": records, "queues": queues,
            "footprints": {"center_cells": center_cells, "full_cells": full_cells, "full_alpha": full_alpha},
            "radii": {"r_center": r_center, "r_full": r_full, "env_support_sr": env_support_sr}}


# ------------------------------------------------------------------ section 9: deterministic queues
def queue(records: list[dict], cls: str) -> list[dict]:
    members = sorted((r for r in records if r["class"] == cls),
                     key=lambda r: (-r["clearance_rad"], -r["support_sr"], r["id"]))
    return [{"rank": k, "id": r["id"], "clearance_rad": r["clearance_rad"], "clearance_deg": r["clearance_deg"],
             "support_sr": r["support_sr"], "cells": r["cells"],
             "seed": {f: r["seed"][f] for f in ("row", "col", "yaw_deg", "pitch_deg", "range_m")},
             "seed_direction_h": r["seed_direction_h"],
             "center_containment_fraction": r["center"]["containment_fraction"],
             "full_containment_fraction": r["full"]["containment_fraction"]} for k, r in enumerate(members, start=1)]


def pack_footprints(fp: dict) -> dict:
    """CSR-style arrays (hypothesis order = NB1a label order) for footprints.npz."""
    def csr(lists, dtype):
        ptr = np.zeros(len(lists) + 1, np.int64)
        ptr[1:] = np.cumsum([len(x) for x in lists])
        return ptr, (np.concatenate(lists).astype(dtype) if lists else np.zeros(0, dtype))
    cp, cc = csr(fp["center_cells"], np.int32)
    fpp, fc = csr(fp["full_cells"], np.int32)
    _p, fa = csr(fp["full_alpha"], np.float64)
    return {"center_ptr": cp, "center_cells": cc, "full_ptr": fpp, "full_cells": fc, "full_alpha": fa}


# ------------------------------------------------------------------ section 10: primary measurements
def _dist(values, edges, zero_separate: bool = False) -> dict:
    return {"binned": D.binned(values, edges, zero_separate=zero_separate), "quantiles": D.quantiles(values)}


def failure_accounting(recs: list[dict]) -> dict:
    out = {}
    for fpn in ("center", "full"):
        bad = [r[fpn] for r in recs if not r[fpn]["safe"]]
        inv = [s for s in bad if s["invalid_cells"] > 0]
        oth = [s for s in bad if s["other_cells"] > 0]
        out[fpn] = {"hypotheses": len(recs), "not_safe": len(bad),
                    "containing_invalid": sum(1 for r in recs if r[fpn]["invalid_cells"] > 0),
                    "containing_other_hypothesis": sum(1 for r in recs if r[fpn]["other_cells"] > 0),
                    "failing_only_no_geometry": sum(1 for s in inv if s["other_cells"] == 0),
                    "failing_only_other_hypothesis": sum(1 for s in oth if s["invalid_cells"] == 0),
                    "failing_both": sum(1 for s in inv if s["other_cells"] > 0)}
    return out


def summary(res: dict, n_nb1a: int) -> dict:
    recs = res["records"]
    by = {c: [r for r in recs if r["class"] == c] for c in SP.CLASSES}
    per_class = {}
    for c, rs in by.items():
        clr = [r["clearance_deg"] for r in rs if r["clearance_deg"] is not None]
        per_class[c] = {
            "hypotheses": len(rs), "cells": int(sum(r["cells"] for r in rs)),
            "support_sr": float(math.fsum(r["support_sr"] for r in rs)),
            "fraction_of_4pi": float(math.fsum(r["support_sr"] for r in rs)) / (4 * math.pi),
            "clearance_deg": _dist(clr, A.CLEARANCE_EDGES_DEG, zero_separate=True),
            "median_range_m": _dist([r["range_m"]["median"] for r in rs], A.RANGE_EDGES_M),
            "seed_range_m": _dist([r["seed"]["range_m"] for r in rs], A.RANGE_EDGES_M)}
    fg = [r for r in recs if not r["environment_candidate"]]
    env = by[SP.ENVIRONMENT]
    return {
        "schema": "NB1b-selection-summary-v1", "truth": SP.TRUTH_DERIVED,
        "statement": "primary serviceability measurements, recorded before any reference evaluation; a sampled "
                     "spherical test of the nominal measurement core, not stereo success or objectness",
        "sensor": SP.SENSOR_CONSTANTS, "radii_used": res["radii"],
        "total_hypotheses": len(recs), "nb1a_hypotheses": n_nb1a,
        "counts": {c: len(by[c]) for c in SP.CLASSES},
        "per_class": per_class,
        "queues": {name: [{k: e[k] for k in ("rank", "id", "clearance_deg", "support_sr", "seed", "seed_direction_h",
                                             "center_containment_fraction", "full_containment_fraction")} for e in q]
                   for name, q in res["queues"].items()},
        "failure_accounting_non_environment": failure_accounting(fg),
        "environment_candidates": [{"id": r["id"], "support_sr": r["support_sr"], "fraction_of_4pi": r["fraction_of_4pi"],
                                    "clearance_deg": r["clearance_deg"], "center": r["center"], "full": r["full"]}
                                   for r in env],
        "quantiles": A.QUANTILES,
    }
