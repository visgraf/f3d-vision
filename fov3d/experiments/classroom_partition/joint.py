"""Joint retrospective Classroom partition and local gap-corridor analysis.

Partition-Graph Phase 3 remains read-only and post-hoc. It combines the latest
saved map of every object reconstructed so far into one frontmost spherical
partition, replays the old controller's exact ``seen_any`` sampling geometry
from saved calibrations, derives cell-side scene boundaries, and measures a
local straight gap corridor between disconnected components of one object.

No dense evaluation truth, Blender scene, controller execution, fusion, or new
measurement is used here. Object identity is inherited from the Oracle-1 run.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable
import json
import math

import numpy as np

from fov3d.scene import (
    BoundaryKind,
    ObjectHypothesis,
    ObservationFootprint,
    ObservationOverlay,
    RegionKind,
    ScenePartitionGraph,
    SupportLayer,
    joint_owner,
    label_joint_regions,
    support_depth_from_map,
)
from fov3d.scene.boundaries import _interface_edges, _trace_edge_components, extract_boundaries
from fov3d.scene.corridors import _component_boundary, _line_cells, corridors_for_object, gap_corridor
from fov3d.scene.lineage import _lineage, _target_component_raster
from fov3d.geometry.head_chart import (
    chart_cells,
    chart_grid,
    head_angles_from_unit,
)
from fov3d.experiments.classroom_partition.lift import (
    ReadLog,
    _camera_polygon,
)


@dataclass(frozen=True)
class StereoOps:
    rectification: Callable[[dict[str, Any]], dict[str, Any]]
    support_mask: Callable[[dict[str, Any], dict[str, Any], str], np.ndarray]


def _default_stereo_ops() -> StereoOps:
    # Lazy on purpose: structural tests can inject a pure synthetic fixture, while
    # the real lift uses the consolidated public facade to replay the old evidence
    # geometry exactly. This imports no matcher or controller.
    from fov3d.stereo.core import rectification, support_mask
    return StereoOps(rectification=rectification, support_mask=support_mask)


def build_joint_graph(
    layers: dict[int, SupportLayer],
    object_names: dict[int, str],
    observations: ObservationOverlay,
    domain: dict[str, Any],
    grid_deg: float,
    *,
    global_index: int,
    current_target: int,
    current_local_step: int,
) -> tuple[ScenePartitionGraph, dict[str, np.ndarray], dict[str, int]]:
    owner, owner_depth, overlap = joint_owner(layers)
    regions, objects, region_code, code_to_rid, rid_to_code = label_joint_regions(owner, owner_depth, object_names)
    boundaries, boundary_diag = extract_boundaries(region_code, code_to_rid, regions, owner_depth, domain, grid_deg)
    graph = ScenePartitionGraph(
        regions=regions,
        objects=objects,
        boundaries=boundaries,
        observations=observations,
        attributes={
            "lift": "Classroom-Oracle-1 joint retrospective controller-time maps",
            "global_fixation_index": int(global_index),
            "current_target_instance_id": int(current_target),
            "current_target_local_step": int(current_local_step),
            "direction_frame": "legacy_head_H",
            "controller_domain_deg": domain,
            "grid_deg": float(grid_deg),
            "object_connectivity": 8,
            "base_connectivity": 4,
            "owner_rule": "nearest reconstructed 12mm-support range; deterministic instance-id tie break",
            "object_identity_source": "inherited_from_classroom_oracle1",
            "truth_used": False,
            "raw_footprints_are_display_only": True,
        },
    )
    graph.validate()
    state = {
        "owner_instance": owner,
        "owner_depth_m": owner_depth,
        "overlap_count": overlap,
        "region_code": region_code,
    }
    return graph, state, boundary_diag


def _rectified_core_directions_h(calibration: dict[str, Any], side: str, r: dict[str, Any]) -> np.ndarray:
    x0, y0, w, h = map(int, r["crop_xywh"])
    vv, uu = np.mgrid[:h, :w]
    uv = np.stack((uu + x0, vv + y0), axis=-1).astype(np.float64)
    k = np.asarray(r["P1" if side == "L" else "P2"], np.float64)[:, :3]
    rr = np.asarray(r["R1" if side == "L" else "R2"], np.float64)
    a = np.concatenate((uv, np.ones((h, w, 1))), axis=-1)
    d_rect = a @ np.linalg.inv(k).T
    d_c = d_rect @ rr
    eye = calibration["eyes"][0 if side == "L" else 1]
    d_h = d_c @ np.asarray(eye["R_hc"], np.float64).T
    d_h /= np.maximum(np.linalg.norm(d_h, axis=-1, keepdims=True), 1e-15)
    return d_h


def update_controller_seen_any(
    seen_any: np.ndarray,
    calibration: dict[str, Any],
    domain: dict[str, Any],
    grid_deg: float,
    *,
    stereo_ops: StereoOps | None = None,
) -> dict[str, int]:
    """Replay exactly the old controller's ``seen_any`` geometry.

    Only calibration and deterministic support masks are used. No image, instance
    id, local oracle observation, matcher output, or evaluation truth is opened.
    """
    ops = stereo_ops or _default_stereo_ops()
    r = ops.rectification(calibration)
    x0, y0, w, h = map(int, r["crop_xywh"])
    y_min, _ymax, p_min, _pmax, gh, gw = chart_grid(domain, grid_deg)
    before = int(seen_any.sum())
    marked_pixels = 0
    for side in ("L", "R"):
        full = np.asarray(ops.support_mask(calibration, r, side), bool)
        core = full[y0:y0 + h, x0:x0 + w]
        if core.shape != (h, w):
            raise ValueError(f"support-mask core shape mismatch for {side}: {core.shape} != {(h,w)}")
        directions = _rectified_core_directions_h(calibration, side, r)
        d = directions[core]
        marked_pixels += int(len(d))
        if len(d):
            yaw, pitch = head_angles_from_unit(d)
            yy, xx, ok = chart_cells(yaw, pitch, y_min, p_min, grid_deg, gh, gw)
            seen_any[yy[ok], xx[ok]] = True
    return {
        "supported_core_pixels_both_eyes": int(marked_pixels),
        "new_seen_cells": int(seen_any.sum()) - before,
        "seen_cells": int(seen_any.sum()),
        "unseen_cells": int(seen_any.size - seen_any.sum()),
    }


def _append_raw_footprints(
    observations: ObservationOverlay,
    calibration: dict[str, Any],
    global_index: int,
    target_id: int,
    local_step: int,
) -> None:
    from fov3d.scene import FootprintEye
    for eye_index, eye in ((0, FootprintEye.LEFT), (1, FootprintEye.RIGHT)):
        poly, gaze = _camera_polygon(calibration, eye_index)
        observations.append(
            ObservationFootprint(
                fixation_id=f"g{global_index:03d}:obj{target_id}:fix{local_step:02d}",
                eye=eye,
                polygon_sphere_xyz=poly,
                gaze_sphere_xyz=gaze,
                sequence_index=global_index,
                attributes={
                    "semantics": "rendered_tangent_footprint_display_only",
                    "controller_seen_any_source": "exact_core_support_is_saved_in_state_npz",
                },
            )
        )


def attach_state_region_codes(graph: ScenePartitionGraph, region_code: np.ndarray) -> ScenePartitionGraph:
    """Validate the construction-time raster code carried by every region."""
    codes = {int(c) for c in np.unique(region_code)}
    graph_codes = {int(r.attributes.get("state_region_code", -1)) for r in graph.regions.values()}
    if -1 in graph_codes or graph_codes != codes:
        raise RuntimeError(f"graph/raster region-code mismatch: graph={sorted(graph_codes)} raster={sorted(codes)}")
    graph.validate()
    return graph


def _controller_expected_never(row: dict[str, Any]) -> int | None:
    try:
        return int(row["cyclopean_decision"]["audit"]["epistemic_state_counts"]["NEVER_OBSERVED"])
    except (KeyError, TypeError, ValueError):
        return None


def lift_joint_run(
    run_dir: str | Path,
    out_dir: str | Path,
    *,
    grid_deg: float = 0.10,
    stereo_ops: StereoOps | None = None,
    strict_evidence: bool = True,
) -> dict[str, Any]:
    run = Path(run_dir).resolve()
    out = Path(out_dir).resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"lift output must be new or empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    log = ReadLog(run)
    manifest = log.json(run / "manifest.json")
    if not manifest.get("control_complete"):
        raise RuntimeError("source run is not control_complete")
    seeds = log.json(run / "bootstrap" / "seeds.json")
    domain = seeds["controller_domain_deg"]
    if abs(float(grid_deg) - 0.10) > 1e-12:
        raise ValueError("Phase 3 exact controller-evidence replay requires the frozen 0.10 degree chart")
    _y0, _y1, _p0, _p1, h, w = chart_grid(domain, grid_deg)

    object_names = {int(o["instance_id"]): str(o["object_name"]) for o in manifest["objects"]}
    layers: dict[int, SupportLayer] = {}
    evidence: dict[int, np.ndarray] = {}
    global_observations = ObservationOverlay([])
    state_summaries: list[dict[str, Any]] = []
    final_state_for_object: dict[int, int] = {}
    evidence_checks: list[dict[str, Any]] = []
    lineage_totals = Counter()
    previous_target_labels: dict[int, np.ndarray] = {}
    stereo = stereo_ops or _default_stereo_ops()
    global_index = 0

    for obj in manifest["objects"]:
        iid = int(obj["instance_id"])
        name = str(obj["object_name"])
        odir = run / "objects" / f"instance_{iid:04d}"
        seen = evidence.setdefault(iid, np.zeros((h, w), bool))
        trajectory = list(obj.get("trajectory", []))
        for local_step in range(int(obj["fixation_count"])):
            calib = log.json(odir / "acquisitions" / f"fix_{local_step:02d}" / "calibration.json")
            ev_delta = update_controller_seen_any(seen, calib, domain, grid_deg, stereo_ops=stereo)
            _append_raw_footprints(global_observations, calib, global_index, iid, local_step)

            row = trajectory[local_step] if local_step < len(trajectory) else {}
            expected_never = _controller_expected_never(row)
            if expected_never is not None:
                actual_never = int(seen.size - seen.sum())
                check = {
                    "instance_id": iid,
                    "local_step": local_step,
                    "expected_never_observed": expected_never,
                    "replayed_never_observed": actual_never,
                    "match": bool(expected_never == actual_never),
                }
                evidence_checks.append(check)
                if strict_evidence and not check["match"]:
                    raise RuntimeError(f"controller seen_any replay mismatch: {check}")

            map_path = odir / "maps" / f"fix_{local_step:02d}.npz"
            if not map_path.exists():
                # Full Oracle-1 has initialized maps, but retain explicit behavior.
                state_summaries.append({
                    "global_index": global_index,
                    "instance_id": iid,
                    "object_name": name,
                    "local_step": local_step,
                    "map_present": False,
                    "evidence": ev_delta,
                })
                global_index += 1
                continue
            snap = log.npz(map_path)
            layer = support_depth_from_map(
                snap["xyz_h"], domain, grid_deg,
                instance_id=iid, object_name=name,
            )
            layers[iid] = layer
            graph, state, bdiag = build_joint_graph(
                layers, object_names, global_observations, domain, grid_deg,
                global_index=global_index,
                current_target=iid,
                current_local_step=local_step,
            )
            graph = attach_state_region_codes(graph, state["region_code"])
            state["current_target_seen_any"] = seen.astype(bool)
            state["current_target_support"] = layer.support.astype(bool)
            state_dir = out / "states" / f"global_{global_index:03d}"
            graph.save(state_dir / "scene-model")
            np.savez_compressed(state_dir / "state.npz", **state)

            rels = corridors_for_object(graph, state, iid, seen, domain, grid_deg)
            (state_dir / "corridors.json").write_text(
                json.dumps(rels, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )

            current_target_labels = _target_component_raster(graph, state["region_code"], iid)
            lineage = _lineage(previous_target_labels.get(iid), current_target_labels)
            previous_target_labels[iid] = current_target_labels
            if not lineage["initial"]:
                for key in ("births", "merges", "splits", "deaths"):
                    lineage_totals[key] += int(lineage[key])

            n_obj_regions = sum(r.kind is RegionKind.OBJECT_COMPONENT for r in graph.regions.values())
            n_base = sum(r.kind is RegionKind.BASE for r in graph.regions.values())
            n_oo = sum(b.kind is BoundaryKind.OBJECT_OBJECT for b in graph.boundaries.values())
            n_ob = sum(b.kind is BoundaryKind.OBJECT_BASE for b in graph.boundaries.values())
            current_components = len(graph.objects[str(iid)].region_ids) if str(iid) in graph.objects else 0
            s = {
                "global_index": global_index,
                "instance_id": iid,
                "object_name": name,
                "local_step": local_step,
                "map_present": True,
                "objects_present": len(graph.objects),
                "object_regions": int(n_obj_regions),
                "base_regions": int(n_base),
                "object_object_boundaries": int(n_oo),
                "object_base_boundaries": int(n_ob),
                "current_target_components": int(current_components),
                "current_target_corridors": len(rels),
                "boundary_diagnostics": bdiag,
                "evidence": ev_delta,
                "lineage": lineage,
            }
            state_summaries.append(s)
            final_state_for_object[iid] = global_index
            global_index += 1

    if global_index != int(manifest.get("total_fixations", global_index)):
        raise RuntimeError(f"global fixation count mismatch: built {global_index}, manifest {manifest.get('total_fixations')}")

    # Scene-final relations use the final joint partition but each target's own
    # controller evidence accumulated only during that target's historical run.
    final_valid = next((s for s in reversed(state_summaries) if s.get("map_present")), None)
    final_relations: list[dict[str, Any]] = []
    final_graph_path = None
    if final_valid is not None:
        gi = int(final_valid["global_index"])
        state_dir = out / "states" / f"global_{gi:03d}"
        final_graph = ScenePartitionGraph.load(state_dir / "scene-model")
        with np.load(state_dir / "state.npz", allow_pickle=False) as z:
            final_state = {k: np.array(z[k]) for k in z.files}
        for iid in sorted(evidence):
            for r in corridors_for_object(final_graph, final_state, iid, evidence[iid], domain, grid_deg):
                r["context"] = "scene_final"
                final_relations.append(r)
        (out / "scene-final-corridors.json").write_text(
            json.dumps(final_relations, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        final_graph_path = f"states/global_{gi:03d}/scene-model"

    # Causal-final relations are the relations at the last state of each object's
    # own historical processing, before any future object maps exist.
    causal_final: list[dict[str, Any]] = []
    for iid, gi in sorted(final_state_for_object.items()):
        d = out / "states" / f"global_{gi:03d}"
        if (d / "corridors.json").exists():
            rels = json.loads((d / "corridors.json").read_text(encoding="utf-8"))
            for r in rels:
                r["context"] = "causal_object_final"
                r["global_index"] = int(gi)
                causal_final.append(r)
    (out / "causal-final-corridors.json").write_text(
        json.dumps(causal_final, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    bad_paths = [
        p for p in sorted(set(log.paths))
        if "evaluation_only" in p or Path(p).name in {"reachable_samples.npz", "evaluation.json"}
    ]
    if bad_paths:
        raise RuntimeError(f"truth isolation violation: {bad_paths}")
    evidence_mismatches = sum(not c["match"] for c in evidence_checks)
    summary = {
        "schema": "PartitionGraph3-joint-retrospective-v1",
        "source_run": str(run),
        "posthoc_only": True,
        "controller_executed": False,
        "blender_launched": False,
        "dense_truth_opened": False,
        "object_identity_inherited": True,
        "grid_deg": float(grid_deg),
        "global_states": state_summaries,
        "final_state_for_object": {str(k): int(v) for k, v in sorted(final_state_for_object.items())},
        "final_graph": final_graph_path,
        "controller_seen_any_validation": {
            "checks": len(evidence_checks),
            "mismatches": int(evidence_mismatches),
            "records": evidence_checks,
        },
        "lineage_totals_excluding_initial": {k: int(lineage_totals[k]) for k in ("births", "merges", "splits", "deaths")},
        "corridor_aggregate": {
            "causal_final_pairs": len(causal_final),
            "scene_final_pairs": len(final_relations),
            "scene_final_pairs_crossing_other_object": sum(int(r["other_object_cells"] > 0) for r in final_relations),
            "scene_final_pairs_with_unseen_cells": sum(int(r["unseen_cells"] > 0) for r in final_relations),
        },
        "read_paths": sorted(set(log.paths)),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
