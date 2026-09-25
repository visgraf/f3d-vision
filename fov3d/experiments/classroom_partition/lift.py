"""Retrospectively lift a saved Classroom-Oracle-1 run into partition graphs.

This module is deliberately post-hoc and read-only.  It consumes only the saved
controller-time trajectory, calibration and metric-map snapshots.  It never
opens dense evaluation truth or re-runs the controller.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any
import json
import math

import cv2
import numpy as np

from fov3d.scene import (
    BoundaryChain, BoundaryKind, EyeVisibility, FootprintEye, ObjectHypothesis,
    ObservationFootprint, ObservationOverlay, PartitionRegion, RegionKind,
    ScenePartitionGraph,
)

TRUTH_BASENAMES = {"reachable_samples.npz", "evaluation.json"}
FUSION_RADIUS_M = 0.012


class ReadLog:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.paths: list[str] = []

    def _record(self, path: Path) -> Path:
        p = path.resolve()
        try:
            rel = p.relative_to(self.root)
        except ValueError:
            raise ValueError(f"input escaped run root: {p}")
        if "evaluation_only" in rel.parts or p.name in TRUTH_BASENAMES:
            raise RuntimeError(f"dense/evaluation truth is forbidden to the lift: {rel}")
        self.paths.append(rel.as_posix())
        return p

    def json(self, path: Path) -> Any:
        p = self._record(path)
        return json.loads(p.read_text(encoding="utf-8"))

    def npz(self, path: Path) -> dict[str, np.ndarray]:
        p = self._record(path)
        with np.load(p, allow_pickle=False) as z:
            return {k: np.array(z[k]) for k in z.files}


def _head_angles_from_unit(d: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    u = np.asarray(d, dtype=np.float64).reshape(-1, 3)
    n = np.linalg.norm(u, axis=1, keepdims=True)
    u = u / np.maximum(n, 1e-15)
    yaw = np.degrees(np.arctan2(u[:, 0], -u[:, 2]))
    pitch = np.degrees(np.arctan2(u[:, 1], np.hypot(u[:, 0], u[:, 2])))
    return yaw, pitch


def _head_unit_from_angles(yaw_deg: np.ndarray, pitch_deg: np.ndarray) -> np.ndarray:
    y = np.deg2rad(np.asarray(yaw_deg, dtype=np.float64))
    p = np.deg2rad(np.asarray(pitch_deg, dtype=np.float64))
    y, p = np.broadcast_arrays(y, p)
    out = np.stack((np.sin(y) * np.cos(p), np.sin(p), -np.cos(y) * np.cos(p)), axis=-1)
    return out.reshape(-1, 3)


def _grid(domain: dict[str, Any], grid_deg: float):
    y0, y1 = map(float, domain["yaw"])
    p0, p1 = map(float, domain["pitch"])
    w = int(round((y1 - y0) / grid_deg)) + 1
    h = int(round((p1 - p0) / grid_deg)) + 1
    return y0, y1, p0, p1, h, w


def _cells(yaw: np.ndarray, pitch: np.ndarray, y0: float, p0: float, grid_deg: float, h: int, w: int):
    x = np.rint((np.asarray(yaw) - y0) / grid_deg).astype(np.int64)
    y = np.rint((np.asarray(pitch) - p0) / grid_deg).astype(np.int64)
    ok = np.isfinite(yaw) & np.isfinite(pitch) & (x >= 0) & (x < w) & (y >= 0) & (y < h)
    return y, x, ok


def _disk(radius: int) -> np.ndarray:
    yy, xx = np.mgrid[-radius:radius + 1, -radius:radius + 1]
    return ((xx * xx + yy * yy) <= radius * radius).astype(np.uint8)


def _support_from_map(xyz_h: np.ndarray, domain: dict[str, Any], grid_deg: float):
    y0, y1, p0, p1, h, w = _grid(domain, grid_deg)
    p = np.asarray(xyz_h, dtype=np.float64).reshape(-1, 3)
    finite = np.isfinite(p).all(axis=1)
    ids = np.flatnonzero(finite)
    p = p[finite]
    mask = np.zeros((h, w), np.uint8)
    point_yx = np.full((len(xyz_h), 2), -1, np.int32)
    if len(p) == 0:
        return mask.astype(bool), point_yx
    yaw, pitch = _head_angles_from_unit(p)
    yy, xx, ok = _cells(yaw, pitch, y0, p0, grid_deg, h, w)
    ranges = np.linalg.norm(p, axis=1)
    rad_deg = np.degrees(np.arctan(FUSION_RADIUS_M / np.maximum(ranges, 1e-12)))
    rad_cells = np.maximum(1, np.ceil(rad_deg / grid_deg).astype(np.int32))
    point_yx[ids[ok], 0] = yy[ok]
    point_yx[ids[ok], 1] = xx[ok]
    for r in sorted(set(int(v) for v in rad_cells[ok])):
        sel = ok & (rad_cells == r)
        raw = np.zeros_like(mask)
        raw[yy[sel], xx[sel]] = 1
        mask |= cv2.dilate(raw, _disk(r))
    return mask.astype(bool), point_yx


def _camera_polygon(calibration: dict, eye_index: int) -> tuple[np.ndarray, np.ndarray]:
    w, h = map(int, calibration["image_size_wh"])
    eye = calibration["eyes"][eye_index]
    K = np.asarray(eye["K"], dtype=np.float64)
    R_hc = np.asarray(eye["R_hc"], dtype=np.float64)
    uv = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float64)
    a = np.c_[uv, np.ones(4)]
    d_c = a @ np.linalg.inv(K).T
    d_h = d_c @ R_hc.T
    d_h /= np.linalg.norm(d_h, axis=1, keepdims=True)
    # Gaze is optical-axis direction for this eye.
    g_h = np.array([[0.0, 0.0, 1.0]]) @ R_hc.T
    g_h /= np.linalg.norm(g_h, axis=1, keepdims=True)
    return d_h, g_h[0]


def _overlay_until(log: ReadLog, odir: Path, step: int) -> ObservationOverlay:
    fps: list[ObservationFootprint] = []
    for i in range(step + 1):
        c = log.json(odir / "acquisitions" / f"fix_{i:02d}" / "calibration.json")
        for eye_index, eye in ((0, FootprintEye.LEFT), (1, FootprintEye.RIGHT)):
            poly, gaze = _camera_polygon(c, eye_index)
            fps.append(ObservationFootprint(
                fixation_id=f"fix_{i:02d}", eye=eye,
                polygon_sphere_xyz=poly, gaze_sphere_xyz=gaze,
                sequence_index=i,
                attributes={"semantics": "rendered_tangent_footprint", "source": "saved_calibration"},
            ))
    return ObservationOverlay(fps)


def _fill_polygon(mask: np.ndarray, polygon: np.ndarray, domain: dict[str, Any], grid_deg: float) -> None:
    y0, y1, p0, p1, h, w = _grid(domain, grid_deg)
    yaw, pitch = _head_angles_from_unit(polygon)
    x = np.rint((yaw - y0) / grid_deg).astype(np.int32)
    y = np.rint((pitch - p0) / grid_deg).astype(np.int32)
    pts = np.stack((x, y), axis=1).reshape(-1, 1, 2)
    cv2.fillPoly(mask, [pts], 1)


def _visibility_raster(overlay: ObservationOverlay, domain: dict[str, Any], grid_deg: float) -> np.ndarray:
    *_, h, w = _grid(domain, grid_deg)
    left = np.zeros((h, w), np.uint8)
    right = np.zeros((h, w), np.uint8)
    for fp in overlay.footprints:
        if fp.eye in (FootprintEye.LEFT, FootprintEye.BINOCULAR):
            _fill_polygon(left, fp.polygon_sphere_xyz, domain, grid_deg)
        if fp.eye in (FootprintEye.RIGHT, FootprintEye.BINOCULAR):
            _fill_polygon(right, fp.polygon_sphere_xyz, domain, grid_deg)
    # 0 unobserved, 1 left, 2 right, 3 binocular.
    return left + 2 * right


def _component_attributes(label_mask: np.ndarray, label: int, visibility: np.ndarray) -> dict[str, Any]:
    m = label_mask == label
    ys, xs = np.nonzero(m)
    counts = Counter(int(v) for v in visibility[m].tolist())
    return {
        "cell_count": int(m.sum()),
        "touches_domain_edge": bool(
            np.any(ys == 0) or np.any(xs == 0) or np.any(ys == label_mask.shape[0] - 1) or np.any(xs == label_mask.shape[1] - 1)
        ),
        "visibility_counts": {
            EyeVisibility.UNOBSERVED.value: int(counts.get(0, 0)),
            EyeVisibility.LEFT_ONLY.value: int(counts.get(1, 0)),
            EyeVisibility.RIGHT_ONLY.value: int(counts.get(2, 0)),
            EyeVisibility.BINOCULAR.value: int(counts.get(3, 0)),
        },
    }


def _build_graph(
    target_id: int,
    object_name: str,
    xyz_h: np.ndarray,
    overlay: ObservationOverlay,
    domain: dict[str, Any],
    grid_deg: float,
    head_origin_w: np.ndarray,
    head_R_wh: np.ndarray,
    source_step: int,
):
    support, point_yx = _support_from_map(xyz_h, domain, grid_deg)
    visibility = _visibility_raster(overlay, domain, grid_deg)
    n_obj, obj_labels = cv2.connectedComponents(support.astype(np.uint8), connectivity=8)
    n_base, base_labels = cv2.connectedComponents((~support).astype(np.uint8), connectivity=8)

    regions: dict[str, PartitionRegion] = {}
    object_region_ids: list[str] = []
    for lab in range(1, n_obj):
        rid = f"obj:{target_id}:c{lab:03d}"
        pids = tuple(int(i) for i in np.flatnonzero(
            (point_yx[:, 0] >= 0) & (obj_labels[np.maximum(point_yx[:, 0], 0), np.maximum(point_yx[:, 1], 0)] == lab)
        ))
        attrs = _component_attributes(obj_labels, lab, visibility)
        regions[rid] = PartitionRegion(rid, RegionKind.OBJECT_COMPONENT, object_id=str(target_id), point_ids=pids, attributes=attrs)
        object_region_ids.append(rid)
    for lab in range(1, n_base):
        rid = f"base:c{lab:03d}"
        regions[rid] = PartitionRegion(rid, RegionKind.BASE, attributes=_component_attributes(base_labels, lab, visibility))

    objects: dict[str, ObjectHypothesis] = {}
    if object_region_ids:
        objects[str(target_id)] = ObjectHypothesis(
            str(target_id), tuple(object_region_ids), {"object_name": object_name, "source": "saved_target_map"}
        )

    # Map labels to region ids for contour adjacency.
    obj_rid = {lab: f"obj:{target_id}:c{lab:03d}" for lab in range(1, n_obj)}
    base_rid = {lab: f"base:c{lab:03d}" for lab in range(1, n_base)}
    boundaries: dict[str, BoundaryChain] = {}
    y0, y1, p0, p1, h, w = _grid(domain, grid_deg)
    bid_counter = 0
    for lab in range(1, n_obj):
        cmask = (obj_labels == lab).astype(np.uint8)
        contours, _ = cv2.findContours(cmask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        for contour in contours:
            xy = contour.reshape(-1, 2)
            if len(xy) < 2:
                continue
            neighbor_counts: Counter[int] = Counter()
            for x, y in xy:
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        yy, xx = int(y + dy), int(x + dx)
                        if 0 <= yy < h and 0 <= xx < w:
                            b = int(base_labels[yy, xx])
                            if b > 0:
                                neighbor_counts[b] += 1
            if not neighbor_counts:
                continue
            base_lab = neighbor_counts.most_common(1)[0][0]
            # Subsample long raster contours deterministically.
            stride = max(1, int(math.ceil(len(xy) / 512)))
            xy = xy[::stride]
            yaw = y0 + xy[:, 0].astype(np.float64) * grid_deg
            pitch = p0 + xy[:, 1].astype(np.float64) * grid_deg
            sphere = _head_unit_from_angles(yaw, pitch)
            bid = f"b{bid_counter:04d}"
            bid_counter += 1
            boundaries[bid] = BoundaryChain(
                bid, obj_rid[lab], base_rid[base_lab], sphere,
                closed=True, kind=BoundaryKind.OBJECT_BASE,
                attributes={
                    "source": "rasterized_current_map",
                    "contour_samples_before_subsample": int(len(contour)),
                    "base_neighbor_votes": int(neighbor_counts[base_lab]),
                },
            )

    g = ScenePartitionGraph(
        regions=regions, objects=objects, boundaries=boundaries, observations=overlay,
        attributes={
            "lift": "Classroom-Oracle-1 saved controller-time state",
            "target_instance_id": int(target_id),
            "object_name": object_name,
            "source_step": int(source_step),
            "direction_frame": "legacy_head_H",
            "metric_map_frame": "legacy_head_H",
            "controller_domain_deg": domain,
            "grid_deg": float(grid_deg),
            "support_rule": "12mm association radius projected per surfel",
            "truth_used": False,
        },
    )
    g.validate()

    state = {
        "object_labels": obj_labels.astype(np.int32),
        "base_labels": base_labels.astype(np.int32),
        "visibility": visibility.astype(np.uint8),
        "support": support.astype(bool),
    }
    return g, state


def _relations(g: ScenePartitionGraph) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for oid, obj in g.objects.items():
        rids = list(obj.region_ids)
        base_neighbors: dict[str, set[str]] = {rid: set() for rid in rids}
        for e in g.dual_edges():
            a, b = e["region_a"], e["region_b"]
            if a in base_neighbors and g.regions[b].kind is RegionKind.BASE:
                base_neighbors[a].add(b)
            if b in base_neighbors and g.regions[a].kind is RegionKind.BASE:
                base_neighbors[b].add(a)
        for i in range(len(rids)):
            for j in range(i + 1, len(rids)):
                shared = sorted(base_neighbors[rids[i]] & base_neighbors[rids[j]])
                out.append({
                    "object_id": oid,
                    "region_a": rids[i],
                    "region_b": rids[j],
                    "shared_base_regions": shared,
                    "shared_base_visibility": {
                        bid: dict(g.regions[bid].attributes.get("visibility_counts", {})) for bid in shared
                    },
                })
    return out


def lift_run(run_dir: str | Path, out_dir: str | Path, *, grid_deg: float = 0.10) -> dict[str, Any]:
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
    head_origin_w = np.asarray(seeds["head_origin_w_m"], dtype=np.float64)
    head_R_wh = np.asarray(seeds["head_R_wh"], dtype=np.float64)

    objects_summary: list[dict[str, Any]] = []
    total_graphs = 0
    total_merges = total_splits = 0
    for obj in manifest["objects"]:
        iid = int(obj["instance_id"])
        name = str(obj["object_name"])
        odir = run / "objects" / f"instance_{iid:04d}"
        oout = out / "objects" / f"instance_{iid:04d}"
        oout.mkdir(parents=True, exist_ok=True)
        fix_summaries: list[dict[str, Any]] = []
        prev_components: int | None = None
        for step in range(int(obj["fixation_count"])):
            map_path = odir / "maps" / f"fix_{step:02d}.npz"
            overlay = _overlay_until(log, odir, step)
            if not map_path.exists():
                # Seed-uninitializable cases have no metric map yet; record the absence
                # rather than manufacturing an object region.
                fix_summaries.append({
                    "step": step, "map_present": False, "observation_footprints": len(overlay.footprints)
                })
                continue
            snap = log.npz(map_path)
            if "xyz_h" not in snap:
                raise KeyError(f"{map_path} lacks xyz_h")
            g, state = _build_graph(
                iid, name, snap["xyz_h"], overlay, domain, grid_deg,
                head_origin_w, head_R_wh, step,
            )
            gout = oout / f"fix_{step:02d}"
            g.save(gout / "scene-model")
            np.savez_compressed(gout / "state.npz", **state)
            rels = _relations(g)
            (gout / "relations.json").write_text(json.dumps(rels, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            ncomp = len(next(iter(g.objects.values())).region_ids) if g.objects else 0
            event = "initial"
            if prev_components is not None:
                event = "merge" if ncomp < prev_components else "split" if ncomp > prev_components else "stable"
                total_merges += int(event == "merge")
                total_splits += int(event == "split")
            prev_components = ncomp
            shared_pairs = sum(bool(r["shared_base_regions"]) for r in rels)
            s = {
                "step": step, "map_present": True, "object_components": ncomp,
                "base_components": sum(r.kind is RegionKind.BASE for r in g.regions.values()),
                "dual_edges": len(g.boundaries), "observation_footprints": len(g.observations.footprints),
                "same_object_component_pairs": len(rels), "pairs_with_shared_base_neighbor": shared_pairs,
                "topology_event": event,
            }
            fix_summaries.append(s)
            total_graphs += 1
        final = next((x for x in reversed(fix_summaries) if x.get("map_present")), None)
        objects_summary.append({
            "instance_id": iid, "object_name": name, "fixation_count": int(obj["fixation_count"]),
            "termination": obj["termination"], "fixations": fix_summaries, "final": final,
        })

    summary = {
        "schema": "PartitionGraph2-retrospective-lift-v1",
        "source_run": str(run),
        "source_control_complete": True,
        "posthoc_only": True,
        "controller_executed": False,
        "blender_launched": False,
        "dense_truth_opened": False,
        "grid_deg": float(grid_deg),
        "objects": objects_summary,
        "aggregate": {
            "objects": len(objects_summary),
            "graphs_written": total_graphs,
            "topology_merges": total_merges,
            "topology_splits": total_splits,
            "final_multi_component_objects": sum(
                bool(o["final"] and o["final"]["object_components"] > 1) for o in objects_summary
            ),
            "final_pairs_with_shared_base_neighbor": sum(
                int(o["final"]["pairs_with_shared_base_neighbor"]) for o in objects_summary if o["final"]
            ),
        },
        "read_paths": sorted(set(log.paths)),
    }
    bad = [p for p in summary["read_paths"] if "evaluation_only" in p or Path(p).name in TRUTH_BASENAMES]
    if bad:
        raise RuntimeError(f"truth isolation violation: {bad}")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
