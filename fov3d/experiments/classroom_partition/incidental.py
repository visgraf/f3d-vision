"""Partition-Graph Phase 5: head-centred incidental 3-D evidence.

This module is retrospective and read-only. It asks what the accepted Oracle-1
controller *could have retained* from the already-produced local matcher record:
all binocular-valid 3-D points, including non-target instances.  Unlike the
Phase-4 left-eye evidence raster, valid points are projected from the head origin
using saved ``xyz_h``.  This places evidence and the spherical partition in the
same chart and removes the known eye-parallax bookkeeping offset.

No dense evaluation truth, oracle_observation, EXR, Blender scene, controller,
matcher, fusion or renderer is opened/executed here. Object/instance identity is
still inherited from the accepted Oracle-1 run and is reported as such.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

import numpy as np

from fov3d.scene import ScenePartitionGraph
from fov3d.experiments.classroom_partition.lift import ReadLog, _cells, _grid, _head_angles_from_unit
from fov3d.experiments.classroom_partition.joint import support_depth_from_map


HEAD_CLASS_NAMES = (
    "TARGET_SUPPORT",
    "MAPPED_OTHER",
    "INCIDENTAL_OTHER_DEPTH",
    "AMBIGUOUS_DEPTH_INSTANCE",
    "SEEN_NO_HEAD_DEPTH",
    "UNSEEN",
)
HEAD_CLASS_CODE = {name: i for i, name in enumerate(HEAD_CLASS_NAMES)}


@dataclass
class HeadEvidence:
    """Cumulative head-centred depth evidence available from saved local patches."""

    depth_seen: np.ndarray
    target_depth_seen: np.ndarray
    other_depth_seen: np.ndarray
    nearest_instance: np.ndarray
    nearest_range_m: np.ndarray
    ambiguous_instance: np.ndarray
    sample_count: np.ndarray

    @classmethod
    def empty(cls, shape: tuple[int, int]) -> "HeadEvidence":
        return cls(
            depth_seen=np.zeros(shape, bool),
            target_depth_seen=np.zeros(shape, bool),
            other_depth_seen=np.zeros(shape, bool),
            nearest_instance=np.zeros(shape, np.int32),
            nearest_range_m=np.full(shape, np.inf, np.float32),
            ambiguous_instance=np.zeros(shape, bool),
            sample_count=np.zeros(shape, np.uint16),
        )


def _valid_patch_samples(patch: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xyz = np.asarray(patch["xyz_h"], np.float64)
    ids = np.asarray(patch["instance_id"], np.int32)
    valid = np.asarray(patch["valid"], bool)
    if xyz.ndim != 3 or xyz.shape[2] != 3 or ids.shape != xyz.shape[:2] or valid.shape != ids.shape:
        raise ValueError(f"bad saved patch shapes xyz={xyz.shape} ids={ids.shape} valid={valid.shape}")
    m = valid & (ids > 0) & np.isfinite(xyz).all(axis=-1)
    return xyz[m], ids[m], m


def add_head_patch(
    ev: HeadEvidence,
    patch: dict[str, np.ndarray],
    target_id: int,
    domain: dict[str, Any],
    grid_deg: float,
) -> dict[str, int]:
    """Accumulate all valid patch geometry in the head-origin spherical chart.

    ``xyz_h`` is already expressed in the fixed head frame.  Therefore its
    direction is the correct partition-chart direction and no left-eye ray
    projection or parallax compensation is needed.
    """
    pts, ids, _m = _valid_patch_samples(patch)
    before = int(ev.depth_seen.sum())
    if len(pts) == 0:
        return {"valid_points": 0, "new_depth_cells": 0, "depth_cells": before}

    yaw, pitch = _head_angles_from_unit(pts)
    y0, _y1, p0, _p1, h, w = _grid(domain, grid_deg)
    yy, xx, ok = _cells(yaw, pitch, y0, p0, grid_deg, h, w)
    pts = pts[ok]
    ids = ids[ok]
    yy = yy[ok].astype(np.int64)
    xx = xx[ok].astype(np.int64)
    if len(pts) == 0:
        return {"valid_points": 0, "new_depth_cells": 0, "depth_cells": before}
    rng = np.linalg.norm(pts, axis=1).astype(np.float64)

    # Mark all semantic categories, independently of which sample is nearest.
    flat = yy * w + xx
    uniq, counts = np.unique(flat, return_counts=True)
    cy, cx = np.divmod(uniq, w)
    ev.depth_seen[cy, cx] = True
    tgt_flat = np.unique(flat[ids == int(target_id)])
    if len(tgt_flat):
        ty, tx = np.divmod(tgt_flat, w)
        ev.target_depth_seen[ty, tx] = True
    oth_flat = np.unique(flat[ids != int(target_id)])
    if len(oth_flat):
        oy, ox = np.divmod(oth_flat, w)
        ev.other_depth_seen[oy, ox] = True
    old = ev.sample_count[cy, cx].astype(np.uint32)
    ev.sample_count[cy, cx] = np.minimum(old + counts.astype(np.uint32), np.iinfo(np.uint16).max).astype(np.uint16)

    # Determine a deterministic nearest valid sample per chart cell for instance
    # attribution.  Ties prefer the smaller instance id only for determinism.
    order = np.lexsort((ids, rng, flat))
    f = flat[order]
    first = np.r_[True, f[1:] != f[:-1]]
    sel = order[first]
    sy, sx = yy[sel], xx[sel]
    sr, si = rng[sel], ids[sel]

    # Ambiguity means distinct valid instance identities have occupied the same
    # head-centred chart cell over the accumulated observation history.
    by_cell: dict[int, set[int]] = defaultdict(set)
    for ff, iid in zip(flat.tolist(), ids.tolist()):
        by_cell[int(ff)].add(int(iid))
    for ff, vals in by_cell.items():
        if len(vals) > 1:
            ay, ax = divmod(ff, w)
            ev.ambiguous_instance[ay, ax] = True

    for y, x, r, iid in zip(sy.tolist(), sx.tolist(), sr.tolist(), si.tolist()):
        old_i = int(ev.nearest_instance[y, x])
        if old_i not in (0, int(iid)):
            ev.ambiguous_instance[y, x] = True
        old_r = float(ev.nearest_range_m[y, x])
        if (r < old_r) or (r == old_r and (old_i == 0 or int(iid) < old_i)):
            ev.nearest_range_m[y, x] = np.float32(r)
            ev.nearest_instance[y, x] = int(iid)

    after = int(ev.depth_seen.sum())
    return {"valid_points": int(len(pts)), "new_depth_cells": after - before, "depth_cells": after}


def reconstruction_status(instance_id: int, graph: ScenePartitionGraph, all_target_ids: set[int]) -> str:
    iid = int(instance_id)
    if str(iid) in graph.objects:
        return "mapped_now"
    if iid in all_target_ids:
        return "targeted_later"
    return "never_targeted"


def _relation_true_gap_cells(relation: dict[str, Any], target_support: np.ndarray) -> np.ndarray:
    line = np.asarray(relation.get("corridor_yx", []), np.int32)
    interior = line[1:-1] if len(line) > 2 else np.empty((0, 2), np.int32)
    if not len(interior):
        return interior
    keep = ~np.asarray(target_support, bool)[interior[:, 0], interior[:, 1]]
    return interior[keep]


def annotate_head_relation(
    relation: dict[str, Any],
    graph: ScenePartitionGraph,
    owner_instance: np.ndarray,
    target_support: np.ndarray,
    seen_any: np.ndarray,
    ev: HeadEvidence,
    target_id: int,
    all_target_ids: set[int],
) -> dict[str, Any]:
    """Describe one Phase-4 relation in the unified head-centred chart.

    The exclusive true-gap classes are descriptive.  ``MAPPED_OTHER`` means the
    current causal joint graph already owns that cell with another reconstructed
    object. ``INCIDENTAL_OTHER_DEPTH`` means no mapped owner occupies the cell,
    but an already observed binocular-valid non-target 3-D sample projects there.
    Neither class is automatically an occlusion verdict.
    """
    out = dict(relation)
    cells = _relation_true_gap_cells(relation, target_support)
    counts = Counter({name: 0 for name in HEAD_CLASS_NAMES})
    observed_instances = Counter()
    status_counts: dict[str, Counter] = defaultdict(Counter)
    target_gap_violation = 0

    if len(cells):
        yy, xx = cells[:, 0], cells[:, 1]
        owner = np.asarray(owner_instance, np.int32)[yy, xx]
        seen = np.asarray(seen_any, bool)[yy, xx]
        target_seen = np.asarray(ev.target_depth_seen, bool)[yy, xx]
        nearest = np.asarray(ev.nearest_instance, np.int32)[yy, xx]
        ambiguous = np.asarray(ev.ambiguous_instance, bool)[yy, xx]
        target_gap_violation = int(target_seen.sum())

        for k in range(len(cells)):
            if int(owner[k]) > 0 and int(owner[k]) != int(target_id):
                cls = "MAPPED_OTHER"
            elif bool(ambiguous[k]) and int(nearest[k]) > 0 and int(nearest[k]) != int(target_id):
                cls = "AMBIGUOUS_DEPTH_INSTANCE"
            elif int(nearest[k]) > 0 and int(nearest[k]) != int(target_id):
                cls = "INCIDENTAL_OTHER_DEPTH"
            elif bool(seen[k]):
                cls = "SEEN_NO_HEAD_DEPTH"
            else:
                cls = "UNSEEN"
            counts[cls] += 1
            iid = int(nearest[k])
            if iid > 0 and iid != int(target_id):
                observed_instances[iid] += 1
                status_counts[reconstruction_status(iid, graph, all_target_ids)][iid] += 1

    unresolved = int(counts["AMBIGUOUS_DEPTH_INSTANCE"] + counts["SEEN_NO_HEAD_DEPTH"] + counts["UNSEEN"])
    explained = int(counts["MAPPED_OTHER"] + counts["INCIDENTAL_OTHER_DEPTH"])
    n = int(len(cells))
    out.update({
        "true_gap_cell_count": n,
        "true_gap_yx": cells.astype(int).tolist(),
        "head_evidence_class_counts": {k: int(counts[k]) for k in HEAD_CLASS_NAMES},
        "head_evidence_class_fractions": {k: (None if n == 0 else float(counts[k] / n)) for k in HEAD_CLASS_NAMES},
        "head_observed_instance_counts": {str(k): int(v) for k, v in sorted(observed_instances.items())},
        "head_observed_instance_status": {
            status: {str(k): int(v) for k, v in sorted(vals.items())}
            for status, vals in sorted(status_counts.items())
        },
        "head_target_depth_in_true_gap_cells": int(target_gap_violation),
        "explained_true_gap_cells": explained,
        "unresolved_true_gap_cells": unresolved,
        "has_unresolved_true_gap": bool(unresolved > 0),
        "phase5_semantics": (
            "head-centred controller-time incidental 3-D evidence; mapped/incidental other-object depth is descriptive only, "
            "not an occlusion or continuation verdict"
        ),
    })
    return out


def _forbidden_source_path(path: str) -> bool:
    p = Path(path)
    return (
        "evaluation_only" in p.parts
        or p.name in {"reachable_samples.npz", "evaluation.json", "oracle_observation.npz"}
        or p.suffix.lower() in {".exr", ".blend"}
        or "benchmark" in p.parts
    )


def analyze_phase5(
    source_run: str | Path,
    lift_dir: str | Path,
    phase4_dir: str | Path,
    out_dir: str | Path,
    *,
    grid_deg: float = 0.10,
    strict: bool = True,
) -> dict[str, Any]:
    source = Path(source_run).resolve()
    lift = Path(lift_dir).resolve()
    p4 = Path(phase4_dir).resolve()
    out = Path(out_dir).resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"Phase-5 output must be new or empty: {out}")
    out.mkdir(parents=True, exist_ok=True)

    log = ReadLog(source)
    manifest = log.json(source / "manifest.json")
    seeds = log.json(source / "bootstrap" / "seeds.json")
    domain = seeds["controller_domain_deg"]
    _y0, _y1, _p0, _p1, h, w = _grid(domain, grid_deg)
    all_target_ids = {int(o["instance_id"]) for o in manifest["objects"]}
    lift_summary = json.loads((lift / "summary.json").read_text(encoding="utf-8"))
    p4_summary = json.loads((p4 / "summary.json").read_text(encoding="utf-8"))
    if int(p4_summary["target_depth_valid_validation"]["mismatches"]) != 0:
        raise RuntimeError("Phase-4 target-depth replay is not clean")
    if int(lift_summary["controller_seen_any_validation"]["mismatches"]) != 0:
        raise RuntimeError("Phase-3/4 seen_any replay is not clean")

    memories: dict[int, HeadEvidence] = {}
    state_records: list[dict[str, Any]] = []
    challenge: list[dict[str, Any]] = []
    target_gap_violations = 0
    causal_final_state = {int(k): int(v) for k, v in lift_summary["final_state_for_object"].items()}
    global_index = 0

    for obj in manifest["objects"]:
        iid = int(obj["instance_id"])
        name = str(obj["object_name"])
        odir = source / "objects" / f"instance_{iid:04d}"
        mem = memories.setdefault(iid, HeadEvidence.empty((h, w)))
        for local_step in range(int(obj["fixation_count"])):
            patch = log.npz(odir / "patches" / f"fix_{local_step:02d}.npz")
            delta = add_head_patch(mem, patch, iid, domain, grid_deg)
            snap = log.npz(odir / "maps" / f"fix_{local_step:02d}.npz")
            layer = support_depth_from_map(snap["xyz_h"], domain, grid_deg, instance_id=iid, object_name=name)

            sd = lift / "states" / f"global_{global_index:03d}"
            graph = ScenePartitionGraph.load(sd / "scene-model")
            with np.load(sd / "state.npz", allow_pickle=False) as z:
                owner = np.array(z["owner_instance"], np.int32)
                seen_any = np.array(z["current_target_seen_any"], bool)

            p4_rel = json.loads((p4 / "states" / f"global_{global_index:03d}" / "relations.json").read_text(encoding="utf-8"))
            annotated = []
            for rel in p4_rel:
                rr = annotate_head_relation(rel, graph, owner, layer.support, seen_any, mem, iid, all_target_ids)
                annotated.append(rr)
                target_gap_violations += int(rr["head_target_depth_in_true_gap_cells"])
                if rr.get("relation_origin") == "own_support_gap" and rr["has_unresolved_true_gap"]:
                    challenge.append({
                        "global_index": int(global_index),
                        "instance_id": iid,
                        "object_name": name,
                        "local_step": int(local_step),
                        "is_causal_final": bool(global_index == causal_final_state.get(iid)),
                        "region_a": rr.get("region_a"),
                        "region_b": rr.get("region_b"),
                        "endpoint_gap_deg": rr.get("endpoint_gap_deg"),
                        "true_gap_cell_count": rr["true_gap_cell_count"],
                        "unresolved_true_gap_cells": rr["unresolved_true_gap_cells"],
                        "head_evidence_class_counts": rr["head_evidence_class_counts"],
                        "head_observed_instance_status": rr["head_observed_instance_status"],
                    })

            od = out / "states" / f"global_{global_index:03d}"
            od.mkdir(parents=True, exist_ok=True)
            (od / "relations.json").write_text(json.dumps(annotated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            np.savez_compressed(
                od / "head-evidence.npz",
                depth_seen=mem.depth_seen,
                target_depth_seen=mem.target_depth_seen,
                other_depth_seen=mem.other_depth_seen,
                nearest_instance=mem.nearest_instance,
                nearest_range_m=mem.nearest_range_m,
                ambiguous_instance=mem.ambiguous_instance,
                sample_count=mem.sample_count,
                target_support=layer.support,
                owner_instance=owner,
                seen_any=seen_any,
            )
            own = [r for r in annotated if r.get("relation_origin") == "own_support_gap"]
            state_records.append({
                "global_index": int(global_index),
                "instance_id": iid,
                "object_name": name,
                "local_step": int(local_step),
                "head_evidence_delta": delta,
                "relations": len(annotated),
                "own_support_gaps": len(own),
                "unresolved_own_support_gaps": int(sum(r["has_unresolved_true_gap"] for r in own)),
                "head_target_depth_in_true_gap_cells": int(sum(r["head_target_depth_in_true_gap_cells"] for r in own)),
            })
            global_index += 1

    if strict and target_gap_violations != 0:
        raise RuntimeError(f"head-origin target-depth evidence leaked into true gaps: {target_gap_violations} cells")

    # Deterministic challenge setting: every historical prefix own-support gap
    # with at least one true-gap cell that remains unseen, depth-unknown, or
    # instance-ambiguous after using all controller-time head-centred 3-D evidence.
    (out / "challenge-relations.json").write_text(json.dumps(challenge, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    earliest_by_target: dict[int, dict[str, Any]] = {}
    for row in challenge:
        iid = int(row["instance_id"])
        if iid not in earliest_by_target or int(row["global_index"]) < int(earliest_by_target[iid]["global_index"]):
            earliest_by_target[iid] = row
    compact = [earliest_by_target[k] for k in sorted(earliest_by_target)]
    (out / "challenge-states.json").write_text(json.dumps(compact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    bad = sorted(p for p in set(log.paths) if _forbidden_source_path(p))
    if bad:
        raise RuntimeError(f"Phase-5 truth-isolation violation: {bad}")

    def aggregate(rows: list[dict[str, Any]]) -> dict[str, int]:
        c = Counter()
        for st in rows:
            rp = out / "states" / f"global_{int(st['global_index']):03d}" / "relations.json"
            for r in json.loads(rp.read_text(encoding="utf-8")):
                if r.get("relation_origin") != "own_support_gap":
                    continue
                c["relations"] += 1
                for k, v in r["head_evidence_class_counts"].items():
                    c[k] += int(v)
                c["unresolved_relations"] += int(r["has_unresolved_true_gap"])
                c["true_gap_cells"] += int(r["true_gap_cell_count"])
        return {k: int(v) for k, v in sorted(c.items())}

    causal_rows = [s for s in state_records if int(s["global_index"]) in set(causal_final_state.values())]
    summary = {
        "schema": "PartitionGraph5-head-incidental-v1",
        "source_run": str(source),
        "lift_dir": str(lift),
        "phase4_dir": str(p4),
        "posthoc_only": True,
        "controller_executed": False,
        "matcher_executed": False,
        "fusion_executed": False,
        "blender_launched": False,
        "dense_truth_opened": False,
        "object_identity_inherited": True,
        "incidental_geometry_source": "saved controller-time patch xyz_h for all binocular-valid instance ids",
        "global_states": state_records,
        "head_target_depth_true_gap_violations": int(target_gap_violations),
        "all_prefix_own_support_gap": aggregate(state_records),
        "causal_final_own_support_gap": aggregate(causal_rows),
        "challenge_relation_count": len(challenge),
        "challenge_target_count": len({int(x["instance_id"]) for x in challenge}),
        "challenge_state_count": len({int(x["global_index"]) for x in challenge}),
        "compact_challenge_state_count": len(compact),
        "read_paths": sorted(set(log.paths)),
        "forbidden_read_paths": bad,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
