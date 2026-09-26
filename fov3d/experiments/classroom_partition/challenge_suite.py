"""Partition-Graph Phase 8b: budgeted integrated-residual challenge suite.

Phase 8 established a truth-free integrated representation in which causally
measured target geometry is routed by instance identity.  The remaining problem
is benchmark quality, not a known memory-routing defect: residual misses are
concentrated in a few targets, early sparse-memory prefixes contain giant UNKNOWN
regions, and the raw region graph contains thousands of micro fragments.

Phase 8b remains benchmark construction only.  It introduces no score, ranking,
gaze policy, controller change, matcher, fusion, renderer, or scene change.

It creates five deterministic acquisition-budget scenarios over the *saved*
accepted trajectory.  In a scenario with budget B, every target contributes only
its first min(B, historical_fixations) completed looks to persistent cross-target
memory, and its benchmark state is the corresponding historical target prefix.
The FULL scenario retains all historical looks and must reproduce Phase 8 exactly.

Each truth-free integrated partition is then viewed through two benchmark
parameters declared before evaluation:

* UNKNOWN is subdivided into 5-degree chart-distance shells from target support,
  tied to the frozen FSG 5-degree movement lattice;
* raw candidates smaller than 25 chart cells (0.25 deg^2 at 0.1 degrees) remain
  represented but are marked ineligible in a separate benchmark view.

Dense truth enters only the separate evaluator.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import json

import cv2
import numpy as np

from fov3d.scene import ObservationOverlay
from fov3d.experiments.classroom_partition.benchmark import (
    FUSION_RADIUS_M,
    REGION_KIND,
    _cells,
    _covered,
    _grid,
    _region_interfaces,
    build_epistemic_partition,
)
from fov3d.experiments.classroom_partition.incidental import (
    HeadEvidence,
    _valid_patch_samples,
    add_head_patch,
)
from fov3d.experiments.classroom_partition.integration import effective_target_geometry
from fov3d.experiments.classroom_partition.joint import build_joint_graph, support_depth_from_map


BUDGETS: tuple[int | None, ...] = (1, 2, 4, 8, None)
UNKNOWN_SHELL_DEG = 5.0
MIN_ELIGIBLE_CELLS = 25
GRID_DEG = 0.10


def budget_name(budget: int | None) -> str:
    return "full" if budget is None else f"budget_{int(budget)}"


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.array(z[k]) for k in z.files}


def _guard_source(root: Path, path: Path, *, truth_allowed: bool) -> str:
    p = path.resolve()
    try:
        rel = p.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"source path escaped run root: {p}") from exc
    forbidden = (
        "evaluation_only" in rel.parts
        or p.name in {"reachable_samples.npz", "evaluation.json", "oracle_observation.npz"}
        or p.suffix.lower() in {".exr", ".blend"}
        or "benchmark" in rel.parts
    )
    if forbidden and not truth_allowed:
        raise RuntimeError(f"truth/renderer path forbidden to Phase-8b proposer: {rel.as_posix()}")
    return rel.as_posix()


def _concat_xyz(chunks: list[np.ndarray]) -> np.ndarray:
    if not chunks:
        return np.empty((0, 3), np.float32)
    return np.vstack([np.asarray(x, np.float32).reshape(-1, 3) for x in chunks])


def _route_patch(pool: dict[int, list[np.ndarray]], patch: dict[str, np.ndarray]) -> None:
    pts, ids, _ = _valid_patch_samples(patch)
    for observed in sorted(int(v) for v in np.unique(ids) if int(v) > 0):
        q = pts[ids == observed].astype(np.float32, copy=True)
        if len(q):
            pool[observed].append(q)


def _phase8_exact_parity(
    arrays: dict[str, np.ndarray],
    regions: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    phase8_state_dir: Path,
) -> None:
    old = _load_npz(phase8_state_dir / "partition.npz")
    if set(old) != set(arrays):
        raise RuntimeError("Phase-8b FULL array keys differ from Phase 8")
    for key in sorted(arrays):
        if not np.array_equal(np.asarray(arrays[key]), np.asarray(old[key])):
            raise RuntimeError(f"Phase-8b FULL partition differs from Phase 8: {key}")
    if regions != _json(phase8_state_dir / "regions.json"):
        raise RuntimeError("Phase-8b FULL regions differ from Phase 8")
    if edges != _json(phase8_state_dir / "edges.json"):
        raise RuntimeError("Phase-8b FULL edges differ from Phase 8")


def memory_stratum(depth_seen: np.ndarray) -> str:
    f = float(np.asarray(depth_seen, bool).mean())
    if f < 0.25:
        return "depth_00_25"
    if f < 0.50:
        return "depth_25_50"
    if f < 0.75:
        return "depth_50_75"
    return "depth_75_100"


def _component_rows(
    mask: np.ndarray,
    *,
    connectivity: int,
    kind: str,
    original_code: int | None,
    shell_index: int | None,
    next_code: int,
    refined_code: np.ndarray,
    original_row: dict[str, Any] | None,
) -> tuple[int, list[dict[str, Any]]]:
    n, labs = cv2.connectedComponents(np.asarray(mask, np.uint8), connectivity=connectivity)
    rows: list[dict[str, Any]] = []
    for lab in range(1, int(n)):
        m = labs == lab
        cells = int(m.sum())
        if cells <= 0:
            continue
        code = int(next_code); next_code += 1
        refined_code[m] = code
        candidate_raw = kind in {"UNKNOWN", "OTHER_SURFACE"}
        row: dict[str, Any] = {
            "region_code": code,
            "region_id": f"refined:{kind.lower()}:{code:05d}",
            "kind": kind,
            "cell_count": cells,
            "candidate_raw": bool(candidate_raw),
            "eligible_candidate": bool(candidate_raw and cells >= MIN_ELIGIBLE_CELLS),
            "minimum_eligible_cells": int(MIN_ELIGIBLE_CELLS),
            "origin_region_code": None if original_code is None else int(original_code),
            "unknown_shell_index": None if shell_index is None else int(shell_index),
            "unknown_shell_min_distance_deg": None if shell_index is None else float(shell_index * UNKNOWN_SHELL_DEG),
            "unknown_shell_max_distance_deg": None if shell_index is None else float((shell_index + 1) * UNKNOWN_SHELL_DEG),
        }
        if original_row is not None:
            for key in (
                "instance_id", "surface_source", "reconstruction_status",
                "mapped_cells", "incidental_cells", "touches_domain_edge",
                "seen_any_fraction", "head_depth_fraction",
            ):
                if key in original_row:
                    row[key] = original_row[key]
        rows.append(row)
    return next_code, rows


def refine_integrated_partition(
    arrays: dict[str, np.ndarray],
    regions: list[dict[str, Any]],
    *,
    grid_deg: float = GRID_DEG,
) -> tuple[dict[str, np.ndarray], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Subdivide UNKNOWN by fixed 5-degree shells; preserve everything else."""
    if abs(float(grid_deg) - GRID_DEG) > 1e-12:
        raise ValueError("Phase 8b uses the frozen 0.10-degree chart")
    rc = np.asarray(arrays["region_code"], np.int32)
    class_code = np.asarray(arrays["class_code"], np.uint8)
    target_support = np.asarray(arrays["target_support"], bool)
    depth_seen = np.asarray(arrays["depth_seen"], bool)
    if not (rc.shape == class_code.shape == target_support.shape == depth_seen.shape):
        raise ValueError("integrated partition arrays disagree in shape")
    by_code = {int(r["region_code"]): r for r in regions}
    unknown = class_code == int(REGION_KIND["UNKNOWN"])

    shell_index = np.full(rc.shape, -1, np.int16)
    if target_support.any():
        dist = cv2.distanceTransform((~target_support).astype(np.uint8), cv2.DIST_L2, 5) * float(grid_deg)
        shell_index[unknown] = np.floor(dist[unknown] / UNKNOWN_SHELL_DEG).astype(np.int16)
    else:
        shell_index[unknown] = 0

    refined = np.zeros(rc.shape, np.int32)
    out_rows: list[dict[str, Any]] = []
    next_code = 1

    for old_code in sorted(int(v) for v in np.unique(rc) if int(v) > 0):
        old = by_code.get(old_code)
        if old is None:
            raise RuntimeError(f"region table missing code {old_code}")
        kind = str(old["kind"])
        if kind == "UNKNOWN":
            continue
        next_code, rows = _component_rows(
            rc == old_code,
            connectivity=8 if kind in {"TARGET_SUPPORT", "OTHER_SURFACE", "TARGET_EVIDENCE_UNMAPPED"} else 4,
            kind=kind,
            original_code=old_code,
            shell_index=None,
            next_code=next_code,
            refined_code=refined,
            original_row=old,
        )
        if len(rows) != 1:
            raise RuntimeError(f"non-UNKNOWN region {old_code} unexpectedly split")
        out_rows.extend(rows)

    for sh in sorted(int(v) for v in np.unique(shell_index[unknown]) if int(v) >= 0):
        next_code, rows = _component_rows(
            unknown & (shell_index == sh),
            connectivity=4,
            kind="UNKNOWN",
            original_code=None,
            shell_index=sh,
            next_code=next_code,
            refined_code=refined,
            original_row=None,
        )
        out_rows.extend(rows)

    if np.any(refined == 0):
        raise RuntimeError("Phase-8b refinement left unlabelled cells")
    if sum(int(r["cell_count"]) for r in out_rows) != int(refined.size):
        raise RuntimeError("Phase-8b region sizes do not cover the chart")

    edges, adjacency = _region_interfaces(refined)
    by_new = {int(r["region_code"]): r for r in out_rows}
    for code, row in by_new.items():
        row["adjacent_regions"] = [
            {"region_code": int(n), "region_id": by_new[int(n)]["region_id"], "interface_edge_count": int(c)}
            for n, c in sorted(adjacency.get(code, {}).items())
        ]
        row["adjacent_to_target_support"] = any(
            by_new[int(n)]["kind"] == "TARGET_SUPPORT" for n in adjacency.get(code, {})
        )

    diag = {
        "region_count": len(out_rows),
        "raw_candidate_regions": int(sum(bool(r["candidate_raw"]) for r in out_rows)),
        "eligible_candidate_regions": int(sum(bool(r["eligible_candidate"]) for r in out_rows)),
        "micro_candidate_regions": int(sum(bool(r["candidate_raw"]) and not bool(r["eligible_candidate"]) for r in out_rows)),
        "unknown_regions": int(sum(r["kind"] == "UNKNOWN" for r in out_rows)),
        "unknown_shells_present": sorted(set(int(r["unknown_shell_index"]) for r in out_rows if r["unknown_shell_index"] is not None)),
        "memory_stratum": memory_stratum(depth_seen),
        "head_depth_fraction": float(depth_seen.mean()),
        "truth_used": False,
    }
    out_arrays = {
        "refined_region_code": refined,
        "original_region_code": rc,
        "class_code": class_code,
        "target_support": target_support,
        "depth_seen": depth_seen,
        "unknown_shell_index": shell_index,
    }
    return out_arrays, out_rows, edges, diag


def _scenario_look_count(nfix: int, budget: int | None) -> int:
    return int(nfix if budget is None else min(int(budget), int(nfix)))


def propose_phase8b(
    source_run: str | Path,
    phase5_dir: str | Path,
    phase8_proposal_dir: str | Path,
    out_dir: str | Path,
    *,
    grid_deg: float = GRID_DEG,
) -> dict[str, Any]:
    """Build truth-free budget-limited integrated residual benchmark scenarios."""
    source = Path(source_run).resolve()
    p5 = Path(phase5_dir).resolve()
    p8 = Path(phase8_proposal_dir).resolve()
    out = Path(out_dir).resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"Phase-8b proposal output must be new or empty: {out}")
    out.mkdir(parents=True, exist_ok=True)

    reads: list[str] = []
    mp = source / "manifest.json"; reads.append(_guard_source(source, mp, truth_allowed=False)); manifest = _json(mp)
    sp = source / "bootstrap" / "seeds.json"; reads.append(_guard_source(source, sp, truth_allowed=False)); seeds = _json(sp)
    domain = seeds["controller_domain_deg"]
    if abs(float(grid_deg) - GRID_DEG) > 1e-12:
        raise ValueError("Phase 8b uses the frozen 0.10-degree chart")
    _y0, _y1, _p0, _p1, h, w = _grid(domain, grid_deg)
    all_target_ids = {int(o["instance_id"]) for o in manifest["objects"]}
    p8s = _json(p8 / "summary.json")
    if p8s.get("truth_used") is not False or int(p8s.get("integrated_target_evidence_unmapped_cells_total", -1)) != 0:
        raise RuntimeError("Phase-8 proposal tree is not a clean truth-free integrated reference")

    # Original global index of each target/local prefix, used only to retrieve the
    # target-specific seen_any raster and FULL Phase-8 parity state.
    target_start: dict[int, int] = {}
    g = 0
    for obj in manifest["objects"]:
        target_start[int(obj["instance_id"])] = g
        g += int(obj["fixation_count"])

    state_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    full_parity = 0

    for budget in BUDGETS:
        sname = budget_name(budget)
        global_mem = HeadEvidence.empty((h, w))
        pool: dict[int, list[np.ndarray]] = defaultdict(list)
        mapped_layers: dict[int, Any] = {}
        object_names: dict[int, str] = {}

        for obj in manifest["objects"]:
            iid = int(obj["instance_id"]); name = str(obj["object_name"]); nfix = int(obj["fixation_count"])
            keep = _scenario_look_count(nfix, budget)
            odir = source / "objects" / f"instance_{iid:04d}"

            # Retain only looks allowed by this scenario. This changes memory available
            # to all later targets while preserving each retained acquisition exactly.
            for local_step in range(keep):
                pp = odir / "patches" / f"fix_{local_step:02d}.npz"
                reads.append(_guard_source(source, pp, truth_allowed=False))
                patch = _load_npz(pp)
                add_head_patch(global_mem, patch, iid, domain, grid_deg)
                _route_patch(pool, patch)

            local_step = keep - 1
            original_gi = int(target_start[iid] + local_step)
            map_path = odir / "maps" / f"fix_{local_step:02d}.npz"
            reads.append(_guard_source(source, map_path, truth_allowed=False))
            snap = _load_npz(map_path)
            hist_xyz = np.asarray(snap["xyz_h"], np.float64).reshape(-1, 3)
            hist_xyz = hist_xyz[np.isfinite(hist_xyz).all(axis=1)]
            hist_layer = support_depth_from_map(hist_xyz, domain, grid_deg, instance_id=iid, object_name=name)

            # Capped historical mapped scene: earlier targets are represented only by
            # their own retained-budget map, not by discarded later looks.
            layers = dict(mapped_layers); layers[iid] = hist_layer
            names = dict(object_names); names[iid] = name
            _graph, joint_state, _diag = build_joint_graph(
                layers, names, ObservationOverlay([]), domain, grid_deg,
                global_index=original_gi, current_target=iid, current_local_step=local_step,
            )

            measured_xyz = _concat_xyz(pool.get(iid, []))
            effective_xyz = effective_target_geometry(hist_xyz, measured_xyz)
            integrated_layer = support_depth_from_map(effective_xyz, domain, grid_deg, instance_id=iid, object_name=name)

            # seen_any depends only on this target's retained looks and is therefore
            # exactly recoverable from its corresponding accepted historical prefix.
            p5state = _load_npz(p5 / "states" / f"global_{original_gi:03d}" / "head-evidence.npz")
            state = {
                "target_support": integrated_layer.support.astype(bool),
                "owner_instance": np.asarray(joint_state["owner_instance"], np.int32),
                "nearest_instance": np.asarray(global_mem.nearest_instance, np.int32),
                "ambiguous_instance": np.asarray(global_mem.ambiguous_instance, bool),
                "depth_seen": np.asarray(global_mem.depth_seen, bool),
                "seen_any": np.asarray(p5state["seen_any"], bool),
            }
            current_gazes = [
                tuple(map(float, r["gaze_deg"]))
                for r in list(obj.get("trajectory", []))[:keep]
                if "gaze_deg" in r
            ]
            arrays8b_base, regions8b_base, edges8b_base, diag8b_base = build_epistemic_partition(
                state,
                target_id=iid,
                target_name=name,
                all_target_ids=all_target_ids,
                domain=domain,
                grid_deg=grid_deg,
                gazes_deg=current_gazes,
            )
            if int(diag8b_base["target_evidence_unmapped_cells"]) != 0:
                raise RuntimeError(f"budget scenario {sname} left TARGET_EVIDENCE_UNMAPPED for target {iid}")

            if budget is None:
                p8state = p8 / "states" / f"global_{original_gi:03d}" / "integrated"
                _phase8_exact_parity(arrays8b_base, regions8b_base, edges8b_base, p8state)
                full_parity += 1

            arrays, regions, edges, refine_diag = refine_integrated_partition(arrays8b_base, regions8b_base, grid_deg=grid_deg)
            sd = out / "scenarios" / sname / "targets" / f"instance_{iid:04d}"
            sd.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(sd / "partition.npz", **arrays)
            _write_json(sd / "regions.json", regions)
            _write_json(sd / "edges.json", edges)

            row = {
                "scenario": sname,
                "look_budget": None if budget is None else int(budget),
                "instance_id": iid,
                "object_name": name,
                "historical_fixation_count": nfix,
                "retained_fixation_count": keep,
                "original_global_index": original_gi,
                "historical_map_points": int(len(hist_xyz)),
                "causal_measured_target_points": int(len(measured_xyz)),
                "integrated_target_support_cells": int(integrated_layer.support.sum()),
                "global_head_depth_cells": int(global_mem.depth_seen.sum()),
                "global_head_depth_fraction": float(global_mem.depth_seen.mean()),
                "target_evidence_unmapped_cells": int(diag8b_base["target_evidence_unmapped_cells"]),
                **refine_diag,
            }
            _write_json(sd / "summary.json", row)
            state_rows.append(row)
            for r in regions:
                if r["candidate_raw"]:
                    rr = dict(r); rr.update({
                        "scenario": sname,
                        "look_budget": None if budget is None else int(budget),
                        "instance_id_target": iid,
                        "object_name_target": name,
                        "retained_fixation_count": keep,
                        "memory_stratum": str(refine_diag["memory_stratum"]),
                    })
                    candidate_rows.append(rr)

            # Only the retained historical map persists as mapped scene geometry for
            # later targets in this budget scenario. Integration is object memory, not
            # a rewrite of the historical frontmost joint map.
            mapped_layers[iid] = hist_layer
            object_names[iid] = name

    expected_full = len(manifest["objects"])
    if full_parity != expected_full:
        raise RuntimeError(f"FULL Phase-8 parity incomplete: {full_parity}/{expected_full}")

    _write_json(out / "benchmark-states.json", state_rows)
    _write_json(out / "candidate-regions.json", candidate_rows)
    summary = {
        "schema": "PartitionGraph8b-budgeted-integrated-residual-suite-v1",
        "source_run": str(source),
        "phase5_dir": str(p5),
        "phase8_proposal_dir": str(p8),
        "truth_used": False,
        "controller_executed": False,
        "gaze_policy_defined": False,
        "candidate_ranking_defined": False,
        "object_identity_inherited": True,
        "scenario_semantics": "each budget retains only the first min(B,historical fixation count) saved looks for every target; FULL retains all; no acquisition is re-rendered",
        "parameters": {
            "grid_deg": float(grid_deg),
            "budgets": [None if b is None else int(b) for b in BUDGETS],
            "unknown_shell_deg": float(UNKNOWN_SHELL_DEG),
            "minimum_eligible_cells": int(MIN_ELIGIBLE_CELLS),
            "minimum_eligible_area_deg2": float(MIN_ELIGIBLE_CELLS * grid_deg * grid_deg),
        },
        "scenario_count": len(BUDGETS),
        "state_count": len(state_rows),
        "target_count": len(manifest["objects"]),
        "full_phase8_parity_checks": full_parity,
        "raw_candidate_region_count": int(sum(bool(r["candidate_raw"]) for r in candidate_rows)),
        "eligible_candidate_region_count": int(sum(bool(r["eligible_candidate"]) for r in candidate_rows)),
        "scenario_state_counts": dict(sorted(Counter(str(r["scenario"]) for r in state_rows).items())),
        "memory_stratum_counts": dict(sorted(Counter(str(r["memory_stratum"]) for r in state_rows).items())),
        "states": state_rows,
        "source_read_paths": sorted(set(reads)),
        "forbidden_read_paths": [],
    }
    _write_json(out / "summary.json", summary)
    return summary


def _region_metrics(
    residual_angles: np.ndarray,
    region_code: np.ndarray,
    regions: list[dict[str, Any]],
    domain: dict[str, Any],
    grid_deg: float,
    *,
    candidate_field: str,
) -> tuple[dict[str, Any], np.ndarray]:
    y0, _y1, p0, _p1, h, w = _grid(domain, grid_deg)
    a = np.asarray(residual_angles, np.float64).reshape(-1, 2)
    yy, xx, ok = _cells(a[:,0] if len(a) else np.empty(0), a[:,1] if len(a) else np.empty(0), y0, p0, grid_deg, h, w)
    codes = np.zeros(len(a), np.int32); codes[ok] = np.asarray(region_code, np.int32)[yy[ok], xx[ok]]
    by = {int(r["region_code"]): r for r in regions}
    miss_by = Counter(int(c) for c in codes.tolist() if int(c) > 0)
    eligible = {c for c, r in by.items() if bool(r.get(candidate_field))}
    positive = sorted(c for c in eligible if miss_by.get(c,0) > 0)
    captured = int(sum(n for c,n in miss_by.items() if c in eligible))
    area = Counter(); fracs = []
    chart_cells = int(h*w)
    for c in positive:
        f = float(by[c]["cell_count"] / chart_cells); fracs.append(f)
        if f <= .05: area["le_05"] += int(miss_by[c])
        elif f <= .15: area["05_15"] += int(miss_by[c])
        elif f <= .50: area["15_50"] += int(miss_by[c])
        else: area["gt_50"] += int(miss_by[c])
    return {
        "residual_misses": int(len(a)),
        "captured_residual_misses": captured,
        "candidate_recall": None if not len(a) else float(captured / len(a)),
        "candidate_regions": int(len(eligible)),
        "truth_positive_candidate_regions": int(len(positive)),
        "truth_negative_candidate_regions": int(len(eligible)-len(positive)),
        "largest_positive_region_chart_fraction": None if not fracs else float(max(fracs)),
        "captured_misses_by_positive_region_area": {k:int(area[k]) for k in ("le_05","05_15","15_50","gt_50")},
    }, codes


def evaluate_phase8b(
    source_run: str | Path,
    proposal_dir: str | Path,
    phase8_evaluation_dir: str | Path,
    out_dir: str | Path,
    *,
    grid_deg: float = GRID_DEG,
) -> dict[str, Any]:
    """Offline dense-truth evaluation of the five budget scenarios."""
    source = Path(source_run).resolve(); prop = Path(proposal_dir).resolve(); p8e = Path(phase8_evaluation_dir).resolve(); out = Path(out_dir).resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"Phase-8b evaluation output must be new or empty: {out}")
    out.mkdir(parents=True, exist_ok=True)

    mp = source / "manifest.json"; manifest = _json(mp)
    sp = source / "bootstrap" / "seeds.json"; seeds = _json(sp); domain = seeds["controller_domain_deg"]
    tp = source / "bootstrap" / "evaluation_only" / "reachable_samples.npz"
    with np.load(tp, allow_pickle=False) as z:
        truth_ids = np.asarray(z["instance_id"], np.int32)
        truth_xyz = np.asarray(z["xyz_h"], np.float64)
        truth_angles = np.asarray(z["yaw_pitch_deg"], np.float64)
    ps = _json(prop / "summary.json")
    if ps.get("truth_used") is not False or int(ps.get("full_phase8_parity_checks", -1)) != len(manifest["objects"]):
        raise RuntimeError("Phase-8b proposal tree is not the expected truth-free benchmark")
    p8sum = _json(p8e / "summary.json")

    scenario_rows: list[dict[str, Any]] = []
    state_rows: list[dict[str, Any]] = []
    total_by_target: dict[str, Counter] = defaultdict(Counter)
    stratum_stats: dict[str, Counter] = defaultdict(Counter)

    for budget in BUDGETS:
        sname = budget_name(budget)
        pool: dict[int, list[np.ndarray]] = defaultdict(list)
        agg_raw = Counter(); agg_eligible = Counter(); scenario_total = Counter()

        for obj in manifest["objects"]:
            iid = int(obj["instance_id"]); name = str(obj["object_name"]); nfix = int(obj["fixation_count"]); keep = _scenario_look_count(nfix, budget)
            odir = source / "objects" / f"instance_{iid:04d}"
            for local_step in range(keep):
                patch = _load_npz(odir / "patches" / f"fix_{local_step:02d}.npz")
                _route_patch(pool, patch)
            snap = _load_npz(odir / "maps" / f"fix_{keep-1:02d}.npz")
            hist_xyz = np.asarray(snap["xyz_h"], np.float64).reshape(-1,3); hist_xyz = hist_xyz[np.isfinite(hist_xyz).all(axis=1)]
            effective_xyz = effective_target_geometry(hist_xyz, _concat_xyz(pool.get(iid, [])))
            mask = truth_ids == iid; ref = truth_xyz[mask]; ang = truth_angles[mask]
            cov = _covered(ref, effective_xyz, FUSION_RADIUS_M); residual_ang = ang[~cov]

            pd = prop / "scenarios" / sname / "targets" / f"instance_{iid:04d}"
            pa = _load_npz(pd / "partition.npz"); regions = _json(pd / "regions.json"); ss = _json(pd / "summary.json")
            raw, _ = _region_metrics(residual_ang, pa["refined_region_code"], regions, domain, grid_deg, candidate_field="candidate_raw")
            eligible, _ = _region_metrics(residual_ang, pa["refined_region_code"], regions, domain, grid_deg, candidate_field="eligible_candidate")

            row = {
                "scenario": sname,
                "look_budget": None if budget is None else int(budget),
                "instance_id": iid,
                "object_name": name,
                "historical_fixation_count": nfix,
                "retained_fixation_count": keep,
                "reachable_samples": int(len(ref)),
                "integrated_covered_samples": int(cov.sum()),
                "integrated_residual_misses": int((~cov).sum()),
                "memory_stratum": str(ss["memory_stratum"]),
                "raw": raw,
                "eligible": eligible,
            }
            state_rows.append(row)
            scenario_total["reachable"] += len(ref); scenario_total["covered"] += int(cov.sum()); scenario_total["residual"] += int((~cov).sum())
            for label, met, agg in (("raw",raw,agg_raw),("eligible",eligible,agg_eligible)):
                agg["residual"] += int(met["residual_misses"]); agg["captured"] += int(met["captured_residual_misses"])
                agg["candidates"] += int(met["candidate_regions"]); agg["positive"] += int(met["truth_positive_candidate_regions"]); agg["negative"] += int(met["truth_negative_candidate_regions"])
                agg["states0"] += int(met["truth_positive_candidate_regions"]==0); agg["states1"] += int(met["truth_positive_candidate_regions"]==1); agg["states2p"] += int(met["truth_positive_candidate_regions"]>=2)
                agg["giant"] += int(met["largest_positive_region_chart_fraction"] is not None and float(met["largest_positive_region_chart_fraction"])>.50)
                for k,v in met["captured_misses_by_positive_region_area"].items(): agg[f"area_{k}"] += int(v)
            t = total_by_target[str(iid)]; t["states"] += 1; t["residual"] += int((~cov).sum()); t["eligible_positive"] += int(eligible["truth_positive_candidate_regions"]); t["states2p"] += int(eligible["truth_positive_candidate_regions"]>=2)
            st = str(ss["memory_stratum"]); stc = stratum_stats[st]; stc["states"] += 1; stc["residual"] += int((~cov).sum()); stc["eligible_captured"] += int(eligible["captured_residual_misses"]); stc["eligible_positive"] += int(eligible["truth_positive_candidate_regions"])

        def finish(c: Counter) -> dict[str, Any]:
            res=int(c["residual"]); cap=int(c["captured"])
            return {
                "residual_misses":res,"captured_residual_misses":cap,"candidate_recall":None if res==0 else float(cap/res),
                "candidate_regions":int(c["candidates"]),"truth_positive_candidate_regions":int(c["positive"]),"truth_negative_candidate_regions":int(c["negative"]),
                "states_with_0_positive_candidates":int(c["states0"]),"states_with_1_positive_candidate":int(c["states1"]),"states_with_2plus_positive_candidates":int(c["states2p"]),
                "states_with_giant_positive_region_gt50pct":int(c["giant"]),
                "captured_misses_by_positive_region_area":{k:int(c[f"area_{k}"]) for k in ("le_05","05_15","15_50","gt_50")},
            }
        scenario_rows.append({
            "scenario":sname,"look_budget":None if budget is None else int(budget),
            "reachable_samples":int(scenario_total["reachable"]),"integrated_covered_samples":int(scenario_total["covered"]),"integrated_residual_misses":int(scenario_total["residual"]),
            "raw":finish(agg_raw),"eligible":finish(agg_eligible),
        })

    full = next(r for r in scenario_rows if r["scenario"]=="full")
    exp_cov=int(p8sum["final_prefix_totals"]["integrated_covered"]); exp_res=int(p8sum["final_prefix_totals"]["integrated_residual"])
    if int(full["integrated_covered_samples"]) != exp_cov or int(full["integrated_residual_misses"]) != exp_res:
        raise RuntimeError(f"FULL scenario does not reproduce Phase 8: {full['integrated_covered_samples']}/{full['integrated_residual_misses']} != {exp_cov}/{exp_res}")

    _write_json(out / "state-evaluation.json", state_rows)
    _write_json(out / "scenario-evaluation.json", scenario_rows)
    by_target = {k:{kk:int(vv) for kk,vv in sorted(v.items())} for k,v in sorted(total_by_target.items(), key=lambda kv:int(kv[0]))}
    by_stratum = {k:{**{kk:int(vv) for kk,vv in sorted(v.items())},"eligible_recall":None if int(v["residual"])==0 else float(v["eligible_captured"]/v["residual"])} for k,v in sorted(stratum_stats.items())}
    summary = {
        "schema":"PartitionGraph8b-budgeted-integrated-residual-evaluation-v1",
        "source_run":str(source),"proposal_dir":str(prop),"phase8_evaluation_dir":str(p8e),
        "offline_truth_evaluation_only":True,"proposal_tree_truth_free":True,"gaze_policy_defined":False,"candidate_ranking_defined":False,
        "parameters":ps["parameters"],"scenario_count":len(scenario_rows),"state_count":len(state_rows),"target_count":len(manifest["objects"]),
        "full_phase8_parity":{"expected_integrated_covered":exp_cov,"actual_integrated_covered":int(full["integrated_covered_samples"]),"expected_integrated_residual":exp_res,"actual_integrated_residual":int(full["integrated_residual_misses"])},
        "scenarios":scenario_rows,"by_target_across_scenarios":by_target,"by_memory_stratum":by_stratum,
        "interpretation":"offline evaluation of predeclared truth-free budget scenarios and candidate granularity; no score or ranking is defined",
    }
    _write_json(out / "summary.json", summary)
    return summary
