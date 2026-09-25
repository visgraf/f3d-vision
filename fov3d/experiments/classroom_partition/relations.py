"""Partition-Graph Phase 4: typed gap relations and local epistemic replay.

This module is retrospective and read-only. It operates on accepted Phase-3/4
joint-partition outputs plus controller-time Classroom-Oracle-1 artifacts. It
never opens dense evaluation truth, raw oracle observations, EXRs, Blender data,
or executes the controller/matcher/fusion/renderer.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

import cv2
import numpy as np

from fov3d.scene import BoundaryKind, RegionKind, ScenePartitionGraph
from fov3d.experiments.classroom_partition.lift import FUSION_RADIUS_M, ReadLog, _cells, _grid, _head_angles_from_unit
from fov3d.experiments.classroom_partition.joint import (
    StereoOps,
    _default_stereo_ops,
    _rectified_core_directions_h,
    support_depth_from_map,
)


EVIDENCE_CLASS_NAMES = (
    "UNSEEN",
    "SEEN_NO_LEFT_ID_EVIDENCE",
    "LEFT_NONTARGET_ONLY",
    "LEFT_TARGET_NO_DEPTH",
    "LEFT_MIXED_NO_DEPTH",
    "TARGET_DEPTH_VALID",
)
EVIDENCE_CLASS_CODE = {name: i for i, name in enumerate(EVIDENCE_CLASS_NAMES)}


@dataclass
class FineEvidence:
    """Cumulative per-target controller-time evidence recoverable from saved patches."""

    left_target_seen: np.ndarray
    left_nontarget_seen: np.ndarray
    target_depth_valid: np.ndarray

    @classmethod
    def empty(cls, shape: tuple[int, int]) -> "FineEvidence":
        z = np.zeros(shape, bool)
        return cls(z.copy(), z.copy(), z.copy())


def _mark(mask: np.ndarray, directions_h: np.ndarray, dst: np.ndarray,
          domain: dict[str, Any], grid_deg: float) -> None:
    m = np.asarray(mask, bool)
    if m.shape != directions_h.shape[:2]:
        raise ValueError(f"evidence mask/direction shape mismatch: {m.shape} != {directions_h.shape[:2]}")
    d = directions_h[m]
    if len(d) == 0:
        return
    yaw, pitch = _head_angles_from_unit(d)
    y0, _y1, p0, _p1, h, w = _grid(domain, grid_deg)
    yy, xx, ok = _cells(yaw, pitch, y0, p0, grid_deg, h, w)
    dst[yy[ok], xx[ok]] = True


def add_patch_observation(
    ev: FineEvidence,
    calibration: dict[str, Any],
    patch: dict[str, np.ndarray],
    target_id: int,
    domain: dict[str, Any],
    grid_deg: float,
    *,
    stereo_ops: StereoOps | None = None,
) -> dict[str, int]:
    """Replay left-core target/nontarget/depth evidence from a saved Oracle-1 patch.

    The patch is a controller-time product written immediately after the local
    perfect matcher. The exact two-eye ``seen_any`` replay remains Phase 3's
    responsibility; this function only reconstructs the finer left-derived masks
    and the exact historical ``target_depth_valid`` mask.
    """
    ops = stereo_ops or _default_stereo_ops()
    r = ops.rectification(calibration)
    x0, y0, w, h = map(int, r["crop_xywh"])
    full_support_l = np.asarray(ops.support_mask(calibration, r, "L"), bool)
    support_l = full_support_l[y0:y0 + h, x0:x0 + w]
    ids = np.asarray(patch["instance_id"], np.int32)
    valid = np.asarray(patch["valid"], bool)
    if ids.shape != (h, w) or valid.shape != (h, w) or support_l.shape != (h, w):
        raise ValueError(
            f"saved patch/core shape mismatch ids={ids.shape} valid={valid.shape} support={support_l.shape} expected={(h,w)}"
        )
    directions = _rectified_core_directions_h(calibration, "L", r)

    before = (int(ev.left_target_seen.sum()), int(ev.left_nontarget_seen.sum()), int(ev.target_depth_valid.sum()))
    target = support_l & (ids == int(target_id))
    nontarget = support_l & (ids != int(target_id))
    depth_valid = target & valid
    _mark(target, directions, ev.left_target_seen, domain, grid_deg)
    _mark(nontarget, directions, ev.left_nontarget_seen, domain, grid_deg)
    _mark(depth_valid, directions, ev.target_depth_valid, domain, grid_deg)
    after = (int(ev.left_target_seen.sum()), int(ev.left_nontarget_seen.sum()), int(ev.target_depth_valid.sum()))
    return {
        "new_left_target_cells": after[0] - before[0],
        "new_left_nontarget_cells": after[1] - before[1],
        "new_target_depth_valid_cells": after[2] - before[2],
        "left_target_cells": after[0],
        "left_nontarget_cells": after[1],
        "target_depth_valid_cells": after[2],
    }


def evidence_class_raster(seen_any: np.ndarray, ev: FineEvidence) -> np.ndarray:
    """Return one readable diagnostic class per chart cell.

    The underlying boolean masks remain authoritative. The precedence is solely
    for mutually-exclusive display/accounting and is documented in the Phase-4
    contract.
    """
    seen = np.asarray(seen_any, bool)
    for a in (ev.left_target_seen, ev.left_nontarget_seen, ev.target_depth_valid):
        if np.asarray(a).shape != seen.shape:
            raise ValueError("fine-evidence shape mismatch")
    out = np.full(seen.shape, EVIDENCE_CLASS_CODE["UNSEEN"], np.uint8)
    out[seen] = EVIDENCE_CLASS_CODE["SEEN_NO_LEFT_ID_EVIDENCE"]

    lt = np.asarray(ev.left_target_seen, bool)
    ln = np.asarray(ev.left_nontarget_seen, bool)
    dv = np.asarray(ev.target_depth_valid, bool)
    out[seen & ln & ~lt] = EVIDENCE_CLASS_CODE["LEFT_NONTARGET_ONLY"]
    out[seen & lt & ~ln & ~dv] = EVIDENCE_CLASS_CODE["LEFT_TARGET_NO_DEPTH"]
    out[seen & lt & ln & ~dv] = EVIDENCE_CLASS_CODE["LEFT_MIXED_NO_DEPTH"]
    out[dv] = EVIDENCE_CLASS_CODE["TARGET_DEPTH_VALID"]
    return out


def evidence_class_counts(raster: np.ndarray, mask: np.ndarray | None = None) -> dict[str, int]:
    a = np.asarray(raster)
    if mask is not None:
        a = a[np.asarray(mask, bool)]
    c = Counter(int(v) for v in a.reshape(-1).tolist())
    return {name: int(c.get(code, 0)) for name, code in EVIDENCE_CLASS_CODE.items()}


def _region_code(graph: ScenePartitionGraph, rid: str) -> int:
    return int(graph.regions[rid].attributes["state_region_code"])


def _own_labels(layer_support: np.ndarray) -> np.ndarray:
    _n, labs = cv2.connectedComponents(np.asarray(layer_support, np.uint8), connectivity=8)
    return labs.astype(np.int32)


def _joint_region_own_component(graph: ScenePartitionGraph, state: dict[str, np.ndarray], rid: str,
                                own_labels: np.ndarray) -> int:
    code = _region_code(graph, rid)
    m = np.asarray(state["region_code"], np.int32) == code
    vals = np.unique(own_labels[m])
    vals = vals[vals > 0]
    if len(vals) != 1:
        raise RuntimeError(f"joint region {rid} does not map to exactly one own-support component: {vals.tolist()}")
    return int(vals[0])


def relation_origin(graph: ScenePartitionGraph, state: dict[str, np.ndarray], corridor: dict[str, Any],
                    own_support: np.ndarray) -> tuple[str, int, int]:
    labs = _own_labels(own_support)
    a = _joint_region_own_component(graph, state, corridor["region_a"], labs)
    b = _joint_region_own_component(graph, state, corridor["region_b"], labs)
    return ("ownership_cut" if a == b else "own_support_gap", a, b)


def _stats(values: np.ndarray) -> dict[str, Any]:
    x = np.asarray(values, np.float64)
    x = x[np.isfinite(x)]
    if not len(x):
        return {"count": 0, "min": None, "median": None, "p90": None}
    return {
        "count": int(len(x)),
        "min": float(np.min(x)),
        "median": float(np.median(x)),
        "p90": float(np.percentile(x, 90.0)),
    }


def ownership_margin_descriptor(state: dict[str, np.ndarray], target_layer, target_id: int,
                                corridor_yx: list[list[int]]) -> dict[str, Any]:
    line = np.asarray(corridor_yx, np.int32)
    interior = line[1:-1] if len(line) > 2 else np.empty((0, 2), np.int32)
    if not len(interior):
        return {
            "count": 0, "min_m": None, "median_m": None, "p90_m": None,
            "median_over_fusion_radius": None, "fraction_gt_fusion_radius": None,
        }
    yy, xx = interior[:, 0], interior[:, 1]
    owner = np.asarray(state["owner_instance"], np.int32)[yy, xx]
    winner_depth = np.asarray(state["owner_depth_m"], np.float64)[yy, xx]
    target_depth = np.asarray(target_layer.depth_m, np.float64)[yy, xx]
    m = (owner > 0) & (owner != int(target_id)) & np.isfinite(winner_depth) & np.isfinite(target_depth)
    margins = target_depth[m] - winner_depth[m]
    s = _stats(margins)
    if not s["count"]:
        return {
            "count": 0, "min_m": None, "median_m": None, "p90_m": None,
            "median_over_fusion_radius": None, "fraction_gt_fusion_radius": None,
        }
    return {
        "count": s["count"],
        "min_m": s["min"],
        "median_m": s["median"],
        "p90_m": s["p90"],
        "median_over_fusion_radius": float(s["median"] / FUSION_RADIUS_M),
        "fraction_gt_fusion_radius": float(np.mean(margins > FUSION_RADIUS_M)),
    }


def _region_object(graph: ScenePartitionGraph, rid: str) -> int | None:
    r = graph.regions[rid]
    if r.kind is not RegionKind.OBJECT_COMPONENT or r.object_id is None:
        return None
    return int(r.object_id)


def _weighted_quantile(values: list[float], weights: list[int], q: float) -> float | None:
    if not values:
        return None
    v = np.asarray(values, np.float64)
    w = np.asarray(weights, np.float64)
    order = np.argsort(v)
    v, w = v[order], w[order]
    c = np.cumsum(w)
    if c[-1] <= 0:
        return None
    return float(v[np.searchsorted(c, q * c[-1], side="left")])


def boundary_depth_order(graph: ScenePartitionGraph, target_id: int,
                         interveners: set[int]) -> dict[str, Any]:
    by: dict[int, dict[str, Any]] = {}
    for other in sorted(int(v) for v in interveners if int(v) != int(target_id)):
        tv = ov = edges = 0
        jumps: list[float] = []
        weights: list[int] = []
        chains = 0
        for b in graph.boundaries.values():
            if b.kind is not BoundaryKind.OBJECT_OBJECT:
                continue
            oa, ob = _region_object(graph, b.region_a), _region_object(graph, b.region_b)
            if {oa, ob} != {int(target_id), int(other)}:
                continue
            a_votes = int(b.attributes.get("nearer_region_a_votes", 0))
            b_votes = int(b.attributes.get("nearer_region_b_votes", 0))
            if oa == int(target_id):
                tv += a_votes; ov += b_votes
            else:
                tv += b_votes; ov += a_votes
            nedge = int(b.attributes.get("interface_edge_count", 0))
            edges += nedge
            if "depth_jump_median_m" in b.attributes and nedge > 0:
                jumps.append(float(b.attributes["depth_jump_median_m"]))
                weights.append(nedge)
            chains += 1
        den = tv + ov
        by[str(other)] = {
            "boundary_chain_count": int(chains),
            "interface_edge_count": int(edges),
            "target_nearer_votes": int(tv),
            "intervener_nearer_votes": int(ov),
            "intervener_nearer_vote_fraction": None if den == 0 else float(ov / den),
            "depth_order_confidence_abs_vote_balance": None if den == 0 else float(abs(ov - tv) / den),
            "depth_jump_interface_weighted_median_m": _weighted_quantile(jumps, weights, 0.5),
            "depth_jump_interface_weighted_p90_m": _weighted_quantile(jumps, weights, 0.9),
        }
    return by


def annotate_corridor(
    graph: ScenePartitionGraph,
    state: dict[str, np.ndarray],
    corridor: dict[str, Any],
    target_layer,
    target_id: int,
    seen_any: np.ndarray,
    fine: FineEvidence,
) -> dict[str, Any]:
    """Return a Phase-4 relation record derived from one Phase-3 corridor."""
    origin, own_a, own_b = relation_origin(graph, state, corridor, target_layer.support)
    cls = evidence_class_raster(seen_any, fine)
    line = np.asarray(corridor["corridor_yx"], np.int32)
    interior = line[1:-1] if len(line) > 2 else np.empty((0, 2), np.int32)
    if len(interior):
        mask = np.zeros(cls.shape, bool)
        mask[interior[:, 0], interior[:, 1]] = True
        counts = evidence_class_counts(cls, mask)
    else:
        counts = {name: 0 for name in EVIDENCE_CLASS_NAMES}
    n = int(sum(counts.values()))
    fracs = {k: (None if n == 0 else float(v / n)) for k, v in counts.items()}
    interveners = {int(k) for k in corridor.get("other_object_counts", {}).keys()}
    out = dict(corridor)
    out.update({
        "relation_origin": origin,
        "own_support_component_a": int(own_a),
        "own_support_component_b": int(own_b),
        "evidence_class_counts": counts,
        "evidence_class_fractions": fracs,
        "ownership_margin": ownership_margin_descriptor(state, target_layer, target_id, corridor["corridor_yx"]),
        "boundary_depth_order": boundary_depth_order(graph, target_id, interveners),
        "phase4_semantics": "descriptive relation evidence only; no attention priority, continuation, or occlusion verdict",
    })
    return out


def component_lineage(prev_labels: np.ndarray | None, curr_labels: np.ndarray) -> dict[str, int | bool]:
    """Lineage in one component-label code space; labels 0 are background."""
    curr = np.asarray(curr_labels, np.int32)
    curr_codes = sorted(int(v) for v in np.unique(curr) if int(v) > 0)
    if prev_labels is None:
        return {"initial": True, "births": len(curr_codes), "merges": 0, "splits": 0, "deaths": 0, "persistent_links": 0}
    prev = np.asarray(prev_labels, np.int32)
    if prev.shape != curr.shape:
        raise ValueError("lineage raster shape mismatch")
    prev_codes = sorted(int(v) for v in np.unique(prev) if int(v) > 0)
    parents = {c: set() for c in curr_codes}
    children = {c: set() for c in prev_codes}
    for pc in prev_codes:
        pm = prev == pc
        for cc in curr_codes:
            if np.any(pm & (curr == cc)):
                parents[cc].add(pc)
                children[pc].add(cc)
    return {
        "initial": False,
        "births": int(sum(len(parents[c]) == 0 for c in curr_codes)),
        "merges": int(sum(len(parents[c]) > 1 for c in curr_codes)),
        "splits": int(sum(len(children[c]) > 1 for c in prev_codes)),
        "deaths": int(sum(len(children[c]) == 0 for c in prev_codes)),
        "persistent_links": int(sum(len(parents[c]) == 1 for c in curr_codes)),
    }


def own_support_labels(support: np.ndarray) -> np.ndarray:
    _n, labs = cv2.connectedComponents(np.asarray(support, np.uint8), connectivity=8)
    return labs.astype(np.int32)


def _expected_depth_valid(row: dict[str, Any]) -> int | None:
    try:
        return int(row["cyclopean_decision"]["audit"]["epistemic_state_counts"]["OBSERVED_TARGET_WITH_DEPTH"])
    except (KeyError, TypeError, ValueError):
        return None


def _forbidden_source_path(path: str) -> bool:
    p = Path(path)
    return (
        "evaluation_only" in p.parts
        or p.name in {"reachable_samples.npz", "evaluation.json", "oracle_observation.npz"}
        or p.suffix.lower() == ".exr"
        or "benchmark" in p.parts
        or p.suffix.lower() == ".blend"
    )


def analyze_phase4(
    source_run: str | Path,
    lift_dir: str | Path,
    out_dir: str | Path,
    *,
    grid_deg: float = 0.10,
    stereo_ops: StereoOps | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """Annotate all Phase-3/4 corridors with typed relation and finer evidence.

    ``lift_dir`` must be a fresh lift generated by the fixed Phase-4 version of
    ``lift_joint_run`` from the same accepted source run.
    """
    source = Path(source_run).resolve()
    lift = Path(lift_dir).resolve()
    out = Path(out_dir).resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"Phase-4 output must be new or empty: {out}")
    out.mkdir(parents=True, exist_ok=True)

    log = ReadLog(source)
    manifest = log.json(source / "manifest.json")
    seeds = log.json(source / "bootstrap" / "seeds.json")
    domain = seeds["controller_domain_deg"]
    _y0, _y1, _p0, _p1, h, w = _grid(domain, grid_deg)
    ops = stereo_ops or _default_stereo_ops()
    lift_summary = json.loads((lift / "summary.json").read_text(encoding="utf-8"))
    if len(lift_summary.get("global_states", [])) != int(manifest.get("total_fixations", -1)):
        raise RuntimeError("lift/source fixation-count mismatch")

    joint_lineage = lift_summary.get("lineage_totals_excluding_initial", {})
    expected_joint = {"births": 10, "merges": 3, "splits": 0, "deaths": 1}
    if strict and {k: int(joint_lineage.get(k, -1)) for k in expected_joint} != expected_joint:
        raise RuntimeError(f"corrected joint lineage regression: {joint_lineage} != {expected_joint}")

    fine_by_target: dict[int, FineEvidence] = {}
    final_layer: dict[int, Any] = {}
    final_fine: dict[int, FineEvidence] = {}
    final_seen: dict[int, np.ndarray] = {}
    causal_final_state: dict[int, int] = {int(k): int(v) for k, v in lift_summary["final_state_for_object"].items()}
    state_records: list[dict[str, Any]] = []
    depth_checks: list[dict[str, Any]] = []
    own_lineage_totals = Counter()
    previous_own: dict[int, np.ndarray] = {}
    global_index = 0

    for obj in manifest["objects"]:
        iid = int(obj["instance_id"])
        name = str(obj["object_name"])
        odir = source / "objects" / f"instance_{iid:04d}"
        fine = fine_by_target.setdefault(iid, FineEvidence.empty((h, w)))
        trajectory = list(obj.get("trajectory", []))
        for local_step in range(int(obj["fixation_count"])):
            calib = log.json(odir / "acquisitions" / f"fix_{local_step:02d}" / "calibration.json")
            patch = log.npz(odir / "patches" / f"fix_{local_step:02d}.npz")
            delta = add_patch_observation(fine, calib, patch, iid, domain, grid_deg, stereo_ops=ops)

            sd = lift / "states" / f"global_{global_index:03d}"
            graph = ScenePartitionGraph.load(sd / "scene-model")
            with np.load(sd / "state.npz", allow_pickle=False) as z:
                state = {k: np.array(z[k]) for k in z.files}
            seen_any = np.asarray(state["current_target_seen_any"], bool)
            if seen_any.shape != (h, w):
                raise RuntimeError("seen_any shape mismatch")

            row = trajectory[local_step] if local_step < len(trajectory) else {}
            expected = _expected_depth_valid(row)
            if expected is not None:
                actual = int(fine.target_depth_valid.sum())
                rec = {
                    "instance_id": iid,
                    "local_step": local_step,
                    "expected_observed_target_with_depth": expected,
                    "replayed_target_depth_valid": actual,
                    "match": bool(expected == actual),
                }
                depth_checks.append(rec)
                if strict and not rec["match"]:
                    raise RuntimeError(f"target-depth-valid replay mismatch: {rec}")

            snap = log.npz(odir / "maps" / f"fix_{local_step:02d}.npz")
            layer = support_depth_from_map(snap["xyz_h"], domain, grid_deg, instance_id=iid, object_name=name)
            final_layer[iid] = layer
            curr_own = own_support_labels(layer.support)
            lin = component_lineage(previous_own.get(iid), curr_own)
            previous_own[iid] = curr_own
            if not lin["initial"]:
                for key in ("births", "merges", "splits", "deaths"):
                    own_lineage_totals[key] += int(lin[key])

            rels = json.loads((sd / "corridors.json").read_text(encoding="utf-8"))
            annotated = [annotate_corridor(graph, state, r, layer, iid, seen_any, fine) for r in rels]
            out_state = out / "states" / f"global_{global_index:03d}"
            out_state.mkdir(parents=True, exist_ok=True)
            (out_state / "relations.json").write_text(json.dumps(annotated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            cls = evidence_class_raster(seen_any, fine)
            np.savez_compressed(
                out_state / "evidence.npz",
                evidence_class=cls,
                left_target_seen=fine.left_target_seen,
                left_nontarget_seen=fine.left_nontarget_seen,
                target_depth_valid=fine.target_depth_valid,
                seen_any=seen_any,
            )
            state_records.append({
                "global_index": global_index,
                "instance_id": iid,
                "object_name": name,
                "local_step": local_step,
                "relations": len(annotated),
                "ownership_cut": int(sum(r["relation_origin"] == "ownership_cut" for r in annotated)),
                "own_support_gap": int(sum(r["relation_origin"] == "own_support_gap" for r in annotated)),
                "evidence_delta": delta,
                "own_support_lineage": lin,
            })
            if global_index == causal_final_state.get(iid):
                final_fine[iid] = FineEvidence(
                    fine.left_target_seen.copy(), fine.left_nontarget_seen.copy(), fine.target_depth_valid.copy()
                )
                final_seen[iid] = seen_any.copy()
            global_index += 1

    expected_own = {"births": 7, "merges": 2, "splits": 0, "deaths": 0}
    own_totals = {k: int(own_lineage_totals[k]) for k in expected_own}
    if strict and own_totals != expected_own:
        raise RuntimeError(f"own-support lineage regression: {own_totals} != {expected_own}")

    # Causal-final relation set from per-state outputs.
    causal: list[dict[str, Any]] = []
    for iid, gi in sorted(causal_final_state.items()):
        p = out / "states" / f"global_{gi:03d}" / "relations.json"
        for r in json.loads(p.read_text(encoding="utf-8")):
            rr = dict(r); rr["context"] = "causal_object_final"; rr["global_index"] = gi
            causal.append(rr)
    (out / "causal-final-relations.json").write_text(json.dumps(causal, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Scene-final corridors are Phase-3 relations recomputed in the final graph.
    final_state_row = next(s for s in reversed(lift_summary["global_states"]) if s.get("map_present"))
    final_gi = int(final_state_row["global_index"])
    final_sd = lift / "states" / f"global_{final_gi:03d}"
    final_graph = ScenePartitionGraph.load(final_sd / "scene-model")
    with np.load(final_sd / "state.npz", allow_pickle=False) as z:
        final_state = {k: np.array(z[k]) for k in z.files}
    scene_src = json.loads((lift / "scene-final-corridors.json").read_text(encoding="utf-8"))
    scene: list[dict[str, Any]] = []
    for r in scene_src:
        iid = int(r["object_id"])
        if iid not in final_layer or iid not in final_fine or iid not in final_seen:
            continue
        rr = annotate_corridor(final_graph, final_state, r, final_layer[iid], iid, final_seen[iid], final_fine[iid])
        rr["context"] = "scene_final"
        scene.append(rr)
    (out / "scene-final-relations.json").write_text(json.dumps(scene, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    bad_paths = sorted(p for p in set(log.paths) if _forbidden_source_path(p))
    if bad_paths:
        raise RuntimeError(f"Phase-4 truth-isolation violation: {bad_paths}")

    def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
        own = [r for r in rows if r["relation_origin"] == "own_support_gap"]
        cuts = [r for r in rows if r["relation_origin"] == "ownership_cut"]
        def occupancy(r):
            b, o = int(r.get("base_cells", 0)), int(r.get("other_object_cells", 0))
            if b > 0 and o == 0: return "pure_base"
            if o > 0 and b == 0: return "pure_other_object"
            if b > 0 and o > 0: return "mixed"
            return "neither"
        occ = Counter(occupancy(r) for r in own)
        depth_any = sum(r["evidence_class_counts"].get("TARGET_DEPTH_VALID", 0) > 0 for r in own)
        unseen_any = sum(r["evidence_class_counts"].get("UNSEEN", 0) > 0 for r in own)
        fully_seen_no_depth = sum(
            r["evidence_class_counts"].get("UNSEEN", 0) == 0
            and r["evidence_class_counts"].get("TARGET_DEPTH_VALID", 0) == 0
            for r in own
        )
        return {
            "relations": len(rows),
            "ownership_cut": len(cuts),
            "own_support_gap": len(own),
            "own_support_gap_occupancy": dict(sorted(occ.items())),
            "own_support_gap_with_target_depth_valid": int(depth_any),
            "own_support_gap_with_unseen": int(unseen_any),
            "own_support_gap_fully_seen_no_target_depth_valid": int(fully_seen_no_depth),
        }

    depth_mismatches = int(sum(not x["match"] for x in depth_checks))
    seen_validation = lift_summary.get("controller_seen_any_validation", {})
    summary = {
        "schema": "PartitionGraph4-typed-relations-v1",
        "source_run": str(source),
        "lift_dir": str(lift),
        "posthoc_only": True,
        "controller_executed": False,
        "matcher_executed": False,
        "fusion_executed": False,
        "blender_launched": False,
        "dense_truth_opened": False,
        "object_identity_inherited": True,
        "global_states": state_records,
        "joint_lineage_totals_excluding_initial": {k: int(joint_lineage[k]) for k in expected_joint},
        "own_support_lineage_totals_excluding_initial": own_totals,
        "controller_seen_any_validation": seen_validation,
        "target_depth_valid_validation": {
            "checks": len(depth_checks),
            "mismatches": depth_mismatches,
            "records": depth_checks,
        },
        "causal_final": aggregate(causal),
        "scene_final": aggregate(scene),
        "read_paths": sorted(set(log.paths)),
        "forbidden_read_paths": bad_paths,
    }
    if strict and int(seen_validation.get("mismatches", -1)) != 0:
        raise RuntimeError("Phase-3 seen_any invariant did not survive Phase 4")
    if strict and depth_mismatches:
        raise RuntimeError(f"target-depth-valid replay has {depth_mismatches} mismatches")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
