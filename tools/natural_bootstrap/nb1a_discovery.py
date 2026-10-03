"""Natural Bootstrap-1a: natural bootstrap discovery from the stripped range input only.

Contract: docs/natural-bootstrap/nb1a-range-connectivity-contract.md, sections 4-6.  The functions take
plain arrays: a range raster and its validity mask.  They read no RGB, no Object Index, no catalog and no
evaluation product; ``load_range_input`` opens exactly the stripped ``range-sensory.npz``.  No semantic
label, no confidence score, no filtering, no merging.
"""
from __future__ import annotations

import heapq
import math

import numpy as np

import nb1a_spec as SP


def load_range_input(path) -> tuple[np.ndarray, np.ndarray]:
    with np.load(path) as z:
        if sorted(z.files) != ["range_m", "valid_mask"]:
            raise ValueError(f"range sensory input must hold exactly range_m and valid_mask, got {z.files}")
        return np.asarray(z["range_m"], np.float64), np.asarray(z["valid_mask"], bool)


# ------------------------------------------------------------------ section 4: continuity edges
def continuity_edges(range_m: np.ndarray, valid: np.ndarray, *, c_max: float = SP.C_MAX,
                     wrap: bool = True, true_delta: bool = True) -> dict:
    """Candidate pairs (both valid) with delta, C and the retained flag.  ``wrap``/``true_delta`` exist only
    so that the checker's mutation suite can build deliberately wrong variants."""
    a, b = SP.neighbor_pairs()
    if not wrap:
        ca, cb = a % SP.WIDTH, b % SP.WIDTH
        keep = np.abs(ca - cb) <= 1
        a, b = a[keep], b[keep]
    v = valid.reshape(-1)
    cand = v[a] & v[b]
    a, b = a[cand], b[cand]
    d = SP.cell_directions_h().reshape(-1, 3)
    r = range_m.reshape(-1)
    di, dj = d[a], d[b]
    if true_delta:
        delta = np.arctan2(np.linalg.norm(np.cross(di, dj), axis=1), np.einsum("ij,ij->i", di, dj))
    else:
        delta = np.full(len(a), math.radians(SP.CELL_DEG))
    ri, rj = r[a], r[b]
    g = np.linalg.norm(ri[:, None] * di - rj[:, None] * dj, axis=1)
    s = 0.5 * (ri + rj) * delta
    c = g / s
    return {"a": a.astype(np.int32), "b": b.astype(np.int32), "delta": delta, "C": c, "retained": c <= c_max}


# ------------------------------------------------------------------ section 5: hypotheses
def components(valid: np.ndarray, a: np.ndarray, b: np.ndarray, retained: np.ndarray) -> np.ndarray:
    """Union-find over the retained edges; returns a raw root label per flat cell (-1 for invalid)."""
    n = valid.size
    parent = np.arange(n, dtype=np.int64).tolist()

    def find(x: int) -> int:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    for x, y in zip(a[retained].tolist(), b[retained].tolist()):
        rx, ry = find(x), find(y)
        if rx != ry:
            if rx < ry:
                parent[ry] = rx
            else:
                parent[rx] = ry
    raw = np.array([find(i) for i in range(n)], np.int64)
    raw[~valid.reshape(-1)] = -1
    return raw


def order_hypotheses(raw: np.ndarray) -> tuple[np.ndarray, list[dict]]:
    """Canonical ordering (support desc, cells desc, smallest (row, col) asc) -> labels 1..N."""
    cells = np.flatnonzero(raw >= 0)
    roots = raw[cells]
    order = np.argsort(roots, kind="stable")
    cells, roots = cells[order], roots[order]
    starts = np.flatnonzero(np.r_[True, roots[1:] != roots[:-1]])
    ends = np.r_[starts[1:], len(cells)]
    groups = []
    for s, e in zip(starts.tolist(), ends.tolist()):
        member = cells[s:e]                      # ascending flat index = row-major
        rows = member // SP.WIDTH
        groups.append({"cells_flat": member, "cells": int(len(member)),
                       "support_sr": SP.support_sr(np.bincount(rows, minlength=SP.HEIGHT)),
                       "min_flat": int(member[0])})
    groups.sort(key=lambda g: (-g["support_sr"], -g["cells"], g["min_flat"]))
    labels = np.zeros(raw.size, np.int32)
    for k, g in enumerate(groups, start=1):
        labels[g["cells_flat"]] = k
        g["label"] = k
    return labels.reshape(SP.HEIGHT, SP.WIDTH), groups


# ------------------------------------------------------------------ section 6: boundary, clearance, seed
def boundary_cells(labels: np.ndarray, valid: np.ndarray) -> np.ndarray:
    a, b = SP.neighbor_pairs()
    lab, v = labels.reshape(-1), valid.reshape(-1)
    differ = (~v[a]) | (~v[b]) | (lab[a] != lab[b])
    bnd = np.zeros(lab.size, bool)
    bnd[a[differ & v[a]]] = True
    bnd[b[differ & v[b]]] = True
    return bnd.reshape(labels.shape)


def interior_clearance(boundary: np.ndarray, valid: np.ndarray, a: np.ndarray, b: np.ndarray,
                       delta: np.ndarray, retained: np.ndarray) -> np.ndarray:
    """Multi-source Dijkstra from all boundary cells along retained edges (cost delta).  Cells of a component
    without boundary keep +inf; invalid cells are NaN."""
    n = boundary.size
    ea, eb, w = a[retained], b[retained], delta[retained]
    src = np.concatenate([ea, eb]); dst = np.concatenate([eb, ea]); ww = np.concatenate([w, w])
    order = np.argsort(src, kind="stable")
    src, dst, ww = src[order], dst[order], ww[order]
    ptr = np.searchsorted(src, np.arange(n + 1))
    dst_l, w_l, ptr_l = dst.tolist(), ww.tolist(), ptr.tolist()
    dist = [math.inf] * n
    heap = []
    for s in np.flatnonzero(boundary.reshape(-1)).tolist():
        dist[s] = 0.0
        heap.append((0.0, s))
    heapq.heapify(heap)
    while heap:
        du, u = heapq.heappop(heap)
        if du > dist[u]:
            continue
        for k in range(ptr_l[u], ptr_l[u + 1]):
            v, nd = dst_l[k], du + w_l[k]
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    out = np.array(dist, np.float64)
    out[~valid.reshape(-1)] = np.nan
    return out.reshape(boundary.shape)


def seed_of(member: np.ndarray, clearance_flat: np.ndarray) -> dict:
    """Max-clearance cell; ties within CLEARANCE_TIE_EPS_RAD -> smaller row, then column (= smaller flat)."""
    if len(member) == 1:
        return {"flat": int(member[0]), "clearance_rad": 0.0, "fallback": None, "tied_candidates": 1}
    d = clearance_flat[member]
    if np.all(np.isinf(d)):
        return {"flat": int(member.min()), "clearance_rad": None, "fallback": "NO_BOUNDARY_FALLBACK",
                "tied_candidates": None}
    mx = float(d.max())
    tied = member[mx - d <= SP.CLEARANCE_TIE_EPS_RAD]
    return {"flat": int(tied.min()), "clearance_rad": mx, "fallback": None, "tied_candidates": int(len(tied))}


# ------------------------------------------------------------------ the whole discovery
def discover(range_m: np.ndarray, valid: np.ndarray, *, c_max: float = SP.C_MAX, wrap: bool = True,
             true_delta: bool = True) -> dict:
    if range_m.shape != (SP.HEIGHT, SP.WIDTH) or valid.shape != range_m.shape:
        raise ValueError(f"range input must be {SP.HEIGHT} x {SP.WIDTH}")
    e = continuity_edges(range_m, valid, c_max=c_max, wrap=wrap, true_delta=true_delta)
    raw = components(valid, e["a"], e["b"], e["retained"])
    labels, groups = order_hypotheses(raw)
    bnd = boundary_cells(labels, valid)
    clr = interior_clearance(bnd, valid, e["a"], e["b"], e["delta"], e["retained"])
    yc, pc = SP.yaw_centers_deg(), SP.pitch_centers_deg()
    rflat, cflat, bflat = range_m.reshape(-1), clr.reshape(-1), bnd.reshape(-1)
    hyps = []
    for g in groups:
        member = g["cells_flat"]
        sd = seed_of(member, cflat)
        row, col = divmod(sd["flat"], SP.WIDTH)
        rr = rflat[member]
        c = sd["clearance_rad"]
        hyps.append({
            "id": f"H{g['label']:04d}", "label": g["label"], "cells": g["cells"], "support_sr": g["support_sr"],
            "fraction_of_4pi": g["support_sr"] / (4.0 * math.pi),
            "range_m": {"min": float(rr.min()), "median": float(np.median(rr)), "max": float(rr.max())},
            "boundary_cells": int(bflat[member].sum()),
            "max_interior_clearance_rad": c, "max_interior_clearance_deg": None if c is None else math.degrees(c),
            "seed": {"row": int(row), "col": int(col), "yaw_deg": float(yc[col]), "pitch_deg": float(pc[row]),
                     "range_m": float(rflat[sd["flat"]]), "clearance_rad": c, "fallback": sd["fallback"],
                     "tied_candidates": sd["tied_candidates"]},
            "ordering_keys": {"support_sr": g["support_sr"], "cells": g["cells"],
                              "min_cell": [int(g["min_flat"] // SP.WIDTH), int(g["min_flat"] % SP.WIDTH)]},
        })
    return {"edges": e, "labels": labels, "boundary": bnd, "clearance": clr, "hypotheses": hyps}


# ------------------------------------------------------------------ pure discovery summary (contract 8)
def binned(values, edges, zero_separate: bool = False) -> dict:
    v = np.asarray(values, np.float64)
    out = {"edges": [x if math.isfinite(x) else "inf" for x in edges]}
    if zero_separate:
        out["zero"] = int((v == 0).sum())
        v = v[v != 0]
    k = np.searchsorted(np.asarray(edges, np.float64), v, side="right") - 1
    under, over = k < 0, k >= len(edges) - 1
    counts = np.bincount(k[~under & ~over], minlength=len(edges) - 1)
    out.update(counts=[int(c) for c in counts], underflow=int(under.sum()), overflow=int(over.sum()))
    return out


def quantiles(values) -> list[float]:
    v = np.asarray(values, np.float64)
    return [float(x) for x in np.quantile(v, SP.QUANTILES, method="linear")] if len(v) else []


def summary(result: dict, valid: np.ndarray, n_pairs_total: int) -> dict:
    h = result["hypotheses"]
    e = result["edges"]
    sup = [x["support_sr"] for x in h]
    cells = [x["cells"] for x in h]
    clr = [x["seed"]["clearance_rad"] for x in h if x["seed"]["clearance_rad"] is not None]
    single = sum(1 for x in cells if x == 1)
    topk = {str(k): {"hypotheses": min(k, len(h)), "support_sr": float(math.fsum(sup[:k])),
                     "fraction_of_4pi": float(math.fsum(sup[:k])) / (4 * math.pi)} for k in SP.TOP_K}
    return {
        "schema": "NB1a-discovery-summary-v1", "truth": SP.TRUTH_DERIVED,
        "valid_cells": int(valid.sum()), "invalid_cells": int((~valid).sum()),
        "neighbor_pairs_total": int(n_pairs_total), "candidate_pairs": int(len(e["a"])),
        "retained_edges": int(e["retained"].sum()), "cut_edges": int((~e["retained"]).sum()),
        "C_MAX": SP.C_MAX, "MAX_SURFACE_SLANT_DEG": SP.MAX_SURFACE_SLANT_DEG,
        "hypotheses": len(h), "singletons": single, "singleton_fraction": single / len(h) if h else None,
        "multi_cell": len(h) - single, "multi_cell_fraction": (len(h) - single) / len(h) if h else None,
        "largest_support_sr": sup[0] if sup else None,
        "largest_fraction_of_4pi": sup[0] / (4 * math.pi) if sup else None,
        "top_k_support": topk,
        "support_distribution_sr": binned(sup, SP.SUPPORT_EDGES_SR),
        "cell_count_distribution": binned(cells, SP.CELL_COUNT_EDGES),
        "clearance_distribution_deg": binned([math.degrees(c) for c in clr], SP.CLEARANCE_EDGES_DEG, zero_separate=True),
        "clearance_quantiles_deg": quantiles([math.degrees(c) for c in clr]),
        "zero_clearance_seeds": sum(1 for c in clr if c == 0.0),
        "no_boundary_fallbacks": sum(1 for x in h if x["seed"]["fallback"] == "NO_BOUNDARY_FALLBACK"),
        "tied_seed_hypotheses": sum(1 for x in h if (x["seed"]["tied_candidates"] or 0) > 1),
        "range_by_hypothesis": {
            "median_range_distribution_m": binned([x["range_m"]["median"] for x in h], SP.RANGE_EDGES_M),
            "median_range_quantiles_m": quantiles([x["range_m"]["median"] for x in h]),
            "largest_25": [{"id": x["id"], "support_sr": x["support_sr"], "range_m": x["range_m"]} for x in h[:25]]},
        "quantiles": SP.QUANTILES,
    }
