"""North Star-1a: the pure functions of the bootstrap round (host side; no file I/O, no Blender, no cv2).

Contract: docs/north-star/ns1a-perfect-bootstrap-round-contract.md, sections 4, 8, 10-12.

- the frozen NB1c gaze reader (exact six, exact order);
- the oracle-aid core class map (the accepted AB1b oracle steps, per raw-core pixel);
- the local oracle segmentation aid (the left raw-core Object Index at the exact uv_L centre);
- the persistent entity seed construction with the accepted ``fov3d.reconstruction.surface_map`` (initialize / fuse)
  and the accepted precondition, radius and hash cell, in frozen gaze order;
- the machine-facing seed-set document.

No object name and no catalog ever enters these functions.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent / "active_bootstrap", HERE.parent / "natural_bootstrap", HERE.parents[1]):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1a_spec as SP  # noqa: E402


# ------------------------------------------------------------------ the frozen NB1c action
def parse_gaze_list(freeze: dict, candidates: dict) -> list[dict]:
    """The six frozen gazes, in frozen order, verified against the literal table and the NB1c candidate record."""
    got = [(int(g["rank"]), int(g["row"]), int(g["col"])) for g in freeze.get("gazes", [])]
    want = [(r, row, col) for r, row, col, _y, _p in SP.GAZES]
    if got != want:
        raise ValueError(f"NB1c frozen gaze list {got} != the accepted six in frozen order {want}")
    if freeze.get("grid", {}).get("convention") != SP.GRID_CONVENTION:
        raise ValueError("NB1c grid convention changed")
    cand = [(int(g["rank"]), int(g["row"]), int(g["col"]), float(g["yaw_deg"]), float(g["pitch_deg"]))
            for g in candidates.get("gazes", [])]
    out = []
    for (r, row, col, yaw, pitch), c in zip(SP.GAZES, cand):
        y2, p2 = SP.gaze_yaw_pitch(row, col)
        if (y2, p2) != (yaw, pitch) or c != (r, row, col, yaw, pitch):
            raise ValueError(f"rank {r}: yaw / pitch {(y2, p2)} / candidate {c} != frozen {(yaw, pitch)}")
        out.append({"rank": r, "row": row, "col": col, "yaw_deg": yaw, "pitch_deg": pitch,
                    "patch_id": SP.patch_id(r), "action_source": SP.ACTION_SOURCE.format(rank=r)})
    if len(cand) != len(SP.GAZES) or len(out) != 6:
        raise ValueError("exactly six frozen gazes are required")
    return out


def planned_calibration(yaw: float, pitch: float, head_r_wh, head_origin_w) -> dict:
    import fsg_geometry as FG
    return FG.make_calibration(SP.PROFILE, float(yaw), float(pitch), SP.VERGENCE_M, ipd=SP.IPD_M,
                               head_r_wh=np.asarray(head_r_wh, np.float64),
                               head_origin_w=np.asarray(head_origin_w, np.float64), tangent_frame=SP.TANGENT_FRAME)


def calibration_bytes(c: dict) -> bytes:
    """The accepted ``write_json`` serialization (indent 1, sorted keys)."""
    return (json.dumps(c, indent=1, sort_keys=True, allow_nan=False) + "\n").encode()


# ------------------------------------------------------------------ section 8: the oracle-aid core class map
def core_class_map(c: dict, ref: dict) -> np.ndarray:
    """Per raw-core pixel (row-major 256 x 256): no hit / instance 0 / positive not visible / correspondence.

    Uses the accepted AB1b oracle step functions; the correspondence class equals the accepted product's pixel set.
    """
    import ab1b_oracle as O
    import fsg_geometry as FG
    rows, cols = O.core_grid()
    v_raw, u_raw = rows + SP.CORE_ORIGIN, cols + SP.CORE_ORIGIN
    pos = np.asarray(ref["position_w_L"])[v_raw, u_raw].astype(np.float64)
    ids_l = np.asarray(ref["instance_L"])[v_raw, u_raw].astype(np.int64)
    hit = O.left_hit(pos)
    cat = hit & O.left_catalog(ids_l)
    p_h = FG.world_to_head(c, np.where(hit[:, None], pos, 0.0))
    uv_r, z_r = O.right_projection(c, p_h)
    proj = cat & O.right_projectable(uv_r, z_r)
    inside = proj & O.inside_raster(c, uv_r)
    vi, ui = O.nearest_pixel(c, uv_r)
    visible = inside & O.same_instance(ref["instance_R"], vi, ui, ids_l)
    cls = np.full(rows.size, SP.CLASS_NO_HIT, np.int8)
    cls[hit & ~cat] = SP.CLASS_INSTANCE0
    cls[cat & ~visible] = SP.CLASS_NOT_VISIBLE
    cls[visible] = SP.CLASS_CORRESPONDENCE
    return cls.reshape(SP.CORE_SIZE, SP.CORE_SIZE)


# ------------------------------------------------------------------ section 10: the local oracle segmentation aid
def attach_identity(prod: dict, valid: np.ndarray, instance_l: np.ndarray) -> np.ndarray:
    """temporary_entity_id = instance_L[v_L, u_L] at the exact integer uv_L centre; -1 where the geometry is invalid."""
    uv = np.asarray(prod["uv_L"], np.float64)
    if uv.ndim != 2 or uv.shape[1] != 2 or not np.array_equal(uv, np.rint(uv)):
        raise ValueError("uv_L must be exact integer raw pixel centres")
    u, v = uv[:, 0].astype(np.int64), uv[:, 1].astype(np.int64)
    want_u = np.asarray(prod["left_core_col"], np.int64) + SP.CORE_ORIGIN
    want_v = np.asarray(prod["left_core_row"], np.int64) + SP.CORE_ORIGIN
    if not (np.array_equal(u, want_u) and np.array_equal(v, want_v)):
        raise ValueError("uv_L is not the raw-core pixel centre of (left_core_row, left_core_col)")
    ids = np.asarray(instance_l)[v, u].astype(np.int32)
    valid = np.asarray(valid, bool)
    if valid.shape != ids.shape:
        raise ValueError("valid mask does not align with the product")
    return np.where(valid, ids, -1).astype(np.int32)


def identity_summary(ids: np.ndarray) -> dict:
    ids = np.asarray(ids)
    pos = ids[ids > 0]
    u, n = np.unique(pos, return_counts=True)
    return {"valid_correspondences": int((ids >= 0).sum()), "positive_id_points": int(pos.size),
            "zero_id_points": int((ids == 0).sum()),
            "entities": {str(int(k)): int(c) for k, c in zip(u, n)}}


# ------------------------------------------------------------------ section 11: persistent entity seed maps
def build_patch(sm, rank: int, xyz: np.ndarray, valid: np.ndarray, ids: np.ndarray, rgb: np.ndarray):
    """One accepted surface-map Patch per gaze: its valid correspondences with a positive local id."""
    keep = np.asarray(valid, bool) & (np.asarray(ids) > 0)
    return sm.Patch(patch_id=SP.patch_id(rank), xyz_h=np.asarray(xyz, np.float64)[keep],
                    rgb=np.asarray(rgb, np.float64)[keep], instance_id=np.asarray(ids, np.int32)[keep])


def map_arrays(m) -> dict:
    """The full-precision arrays of an accepted SurfaceMap (patch ids as a fixed-width string array)."""
    return {"xyz_h": np.asarray(m.xyz_h, np.float64), "rgb": np.asarray(m.rgb, np.float64),
            "instance_id": np.asarray(m.instance_id), "support_count": np.asarray(m.support_count),
            "provenance_mask": np.asarray(m.provenance_mask), "patch_ids": np.array(list(m.patch_ids), dtype="U64")}


def maps_equal(a: dict, b: dict) -> bool:
    return set(a) == set(b) and all(np.asarray(a[k]).dtype == np.asarray(b[k]).dtype
                                    and np.array_equal(np.asarray(a[k]), np.asarray(b[k])) for k in a)


def _dist(meta: dict) -> dict | None:
    d = np.asarray(meta.get("distances_m", np.empty(0)), float)
    if not d.size:
        return None
    return {"median": float(np.median(d)), "p95": float(np.quantile(d, 0.95)), "max": float(d.max())}


def construct_seeds(gazes: list[dict], sm, min_points: int = SP.MIN_INITIAL_TARGET_POINTS,
                    radius: float = SP.ASSOCIATION_RADIUS_M, cell: float = SP.HASH_CELL_M) -> dict:
    """The persistent entity seed set from the six gaze measurements, in frozen rank order.

    ``gazes``: [{"rank", "xyz", "valid", "ids", "rgb"}] in rank order (frozen geometry, oracle ids, raw RGB).
    Returns the final maps, per-rank snapshots, the event history and the per-gaze measurement records.
    """
    ranks = [int(g["rank"]) for g in gazes]
    if ranks != sorted(ranks) or len(set(ranks)) != len(ranks):
        raise ValueError(f"gazes must be processed in frozen rank order, got {ranks}")
    maps: dict[int, object] = {}
    history, per_gaze, snapshots = [], {}, {}
    for g in gazes:
        r = int(g["rank"])
        ids = np.asarray(g["ids"])
        valid = np.asarray(g["valid"], bool)
        if np.any(ids[valid] == 0):
            raise ValueError(f"rank {r}: an instance-0 correspondence reached the seed construction")
        patch = build_patch(sm, r, g["xyz"], valid, ids, g["rgb"])
        observed = sorted(int(k) for k in np.unique(ids[valid & (ids > 0)]))
        per_gaze[r] = {}
        for k in observed:
            if k <= 0:
                raise ValueError("instance 0 is never an ordinary entity")
            n = int((valid & (ids == k)).sum())
            ev = {"rank": r, "entity": k, "patch_id": patch.patch_id, "points": n}
            if k not in maps:
                if n >= min_points:
                    maps[k] = sm.initialize(patch, k)
                    ev.update(action="INITIALIZED", map_before=0, map_after=int(len(maps[k].xyz_h)))
                else:
                    ev.update(action="SEEN_BUT_NOT_INITIALIZED", map_before=0, map_after=0)
            else:
                before = int(len(maps[k].xyz_h))
                if n >= min_points:
                    m2, meta = sm.fuse(maps[k], patch, k, radius, cell)
                    replay, rmeta = sm.fuse(m2, patch, k, radius, cell)
                    a, b = map_arrays(m2), map_arrays(replay)
                    exact = maps_equal(a, b)
                    close = bool(a["xyz_h"].shape == b["xyz_h"].shape
                                 and np.allclose(a["xyz_h"], b["xyz_h"], rtol=0.0, atol=SP.IDEMPOTENCE_ATOL,
                                                 equal_nan=True))
                    if not (exact and close and rmeta.get("duplicate_patch")):
                        raise RuntimeError(f"12 mm fusion lost idempotence at entity {k}, rank {r}")
                    maps[k] = m2
                    ev.update(action="FUSED", map_before=before, map_after=int(len(m2.xyz_h)),
                              matched=int(meta["matched"]), new=int(meta["new"]),
                              affected_surfels=int(meta["affected_surfels"]), matched_distance_m=_dist(meta),
                              replay={"duplicate_patch": bool(rmeta["duplicate_patch"]), "exact": exact,
                                      "allclose_1e-10": close})
                else:
                    ev.update(action="RETAINED_NOT_FUSED", map_before=before, map_after=before)
            history.append(ev)
            per_gaze[r][k] = ev
        snapshots[r] = {k: map_arrays(m) for k, m in sorted(maps.items())}
    final = {k: map_arrays(m) for k, m in sorted(maps.items())}
    for k, a in final.items():
        if not np.all(a["instance_id"] == k):
            raise RuntimeError(f"entity {k}: map holds another instance id")
    return {"maps": final, "snapshots": snapshots, "history": history, "per_gaze": per_gaze}


def _popcount(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, np.uint64)
    c = np.zeros(x.shape, np.int64)
    for b in range(64):
        c += ((x >> np.uint64(b)) & np.uint64(1)).astype(np.int64)
    return c


def seed_set_document(gazes: list[dict], result: dict, unassigned: dict) -> dict:
    """The machine-facing seed set (section 12): one record per locally observed positive entity id; no names."""
    ranks = [int(g["rank"]) for g in gazes]
    hist: dict[int, list[dict]] = {}
    for ev in result["history"]:
        hist.setdefault(int(ev["entity"]), []).append(ev)
    entities = []
    for k in sorted(hist):
        evs = hist[k]
        init = [e for e in evs if e["action"] == "INITIALIZED"]
        contributing = [e for e in evs if e["action"] in ("INITIALIZED", "FUSED")]
        rec = {"temporary_entity_id": k, "identity": SP.LABEL_SEGMENTATION,
               "first_seen_rank": int(evs[0]["rank"]), "gaze_ranks_seen": [int(e["rank"]) for e in evs],
               "points_per_gaze": {str(r): int(next((e["points"] for e in evs if e["rank"] == r), 0)) for r in ranks},
               "actions_per_gaze": {str(int(e["rank"])): e["action"] for e in evs},
               "initialized": bool(init), "initialized_at_rank": int(init[0]["rank"]) if init else None,
               "initial_point_count": int(init[0]["points"]) if init else None,
               "map_size_after_contributing_gaze": {str(int(e["rank"])): int(e["map_after"]) for e in contributing},
               "total_raw_measured_points": int(sum(e["points"] for e in evs))}
        if k in result["maps"]:
            m = result["maps"][k]
            sc = np.asarray(m["support_count"], np.int64)
            pc = _popcount(m["provenance_mask"])
            rec.update(final_surfels=int(len(sc)), contributing_patches=int(len(m["patch_ids"])),
                       patch_ids=[str(p) for p in m["patch_ids"]],
                       support_count={"min": int(sc.min()), "median": float(np.median(sc)), "max": int(sc.max()),
                                      "histogram": {str(int(v)): int(c) for v, c in zip(*np.unique(sc,
                                                                                                return_counts=True))}},
                       provenance_popcount_equals_support=bool(np.array_equal(pc, sc)))
        else:
            rec.update(final_surfels=0, contributing_patches=0, patch_ids=[], support_count=None,
                       provenance_popcount_equals_support=None)
        entities.append(rec)
    initialized = [e["temporary_entity_id"] for e in entities if e["initialized"]]
    return {
        "schema": "NS1a-seed-set-v1", "truth": SP.TRUTH_DERIVED, "experiment": SP.EXPERIMENT,
        "statement": "persistent entity seeds from one six-gaze RGB bootstrap round: PERFECT / ORACLE correspondence, "
                     "DERIVED spherical geometry, ORACLE SEGMENTATION AID identity; no catalog, no names, no "
                     "controller",
        "persistence": SP.PERSISTENCE, "persistence_config_sha256": SP.config_sha256(SP.PERSISTENCE),
        "ranks_processed": ranks,
        "counts": {"observed_positive_entities": len(entities), "initialized": len(initialized),
                   "seen_but_not_initialized": len(entities) - len(initialized),
                   "gazes_with_an_initialized_entity": sorted({e["initialized_at_rank"] for e in entities
                                                               if e["initialized"]})},
        "initialized_entities": initialized,
        "entities": entities,
        "unassigned_instance_0": unassigned,
    }
