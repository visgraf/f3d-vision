"""Partition-Graph Phase 7: prefix benchmark and cross-target causal 3-D memory.

Phase 7 stays benchmark/representation-only.  The truth-free proposer emits two
region partitions at every one of the 104 accepted Oracle-1 prefixes:

* ``local``  -- the Phase-5 per-target head-centred memory;
* ``global`` -- one causal head-centred memory accumulated from *all* completed
  local patches up to the current global fixation.

The offline evaluator is the only function in this module allowed to open dense
reachable-surface truth.  No attention score, candidate ranking, gaze policy,
controller, matcher, fusion, renderer, or Blender process is executed.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import json

import numpy as np

from fov3d.experiments.classroom_partition.benchmark import (
    CANDIDATE_KINDS,
    FUSION_RADIUS_M,
    REGION_KIND,
    REGION_KIND_BY_CODE,
    _cells,
    _covered,
    _grid,
    build_epistemic_partition,
)
from fov3d.experiments.classroom_partition.incidental import HeadEvidence, add_head_patch


ARMS = ("local", "global")
AREA_BINS = (
    ("le_05", 0.05),
    ("05_15", 0.15),
    ("15_50", 0.50),
)


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
        raise RuntimeError(f"truth/renderer path forbidden to Phase-7 proposer: {rel.as_posix()}")
    return rel.as_posix()


def _load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.array(z[k]) for k in z.files}


def _memory_state(local_state: dict[str, np.ndarray], mem: HeadEvidence) -> dict[str, np.ndarray]:
    """Return the Phase-6 partition inputs with global head memory substituted.

    ``target_support``, ``owner_instance`` and target-specific historical
    ``seen_any`` remain exactly the current accepted-prefix state.  Only the
    head-origin measured-depth memory becomes cross-target.
    """
    out = dict(local_state)
    out["depth_seen"] = np.asarray(mem.depth_seen, bool).copy()
    out["nearest_instance"] = np.asarray(mem.nearest_instance, np.int32).copy()
    out["nearest_range_m"] = np.asarray(mem.nearest_range_m, np.float32).copy()
    out["ambiguous_instance"] = np.asarray(mem.ambiguous_instance, bool).copy()
    out["sample_count"] = np.asarray(mem.sample_count, np.uint16).copy()
    return out


def _candidate_cells(regions: list[dict[str, Any]]) -> int:
    return int(sum(int(r["cell_count"]) for r in regions if bool(r.get("candidate"))))


def _largest_kind_cells(regions: list[dict[str, Any]], kind: str) -> int:
    vals = [int(r["cell_count"]) for r in regions if str(r["kind"]) == kind]
    return max(vals) if vals else 0


def _partition_signature(arrays: dict[str, np.ndarray], regions: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    """Small deterministic structure summary used by unit/integration checks."""
    return {
        "shape": list(np.asarray(arrays["region_code"]).shape),
        "region_count": len(regions),
        "edge_count": len(edges),
        "candidate_count": int(sum(bool(r.get("candidate")) for r in regions)),
        "candidate_cells": _candidate_cells(regions),
        "unknown_regions": int(sum(str(r["kind"]) == "UNKNOWN" for r in regions)),
        "other_surface_regions": int(sum(str(r["kind"]) == "OTHER_SURFACE" for r in regions)),
        "target_evidence_unmapped_regions": int(sum(str(r["kind"]) == "TARGET_EVIDENCE_UNMAPPED" for r in regions)),
        "largest_unknown_cells": _largest_kind_cells(regions, "UNKNOWN"),
    }


def _assert_phase6_final_parity(
    arrays: dict[str, np.ndarray],
    regions: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    phase6_dir: Path,
    target_id: int,
) -> None:
    """The local arm at target-final states must exactly reproduce Phase 6."""
    td = phase6_dir / "targets" / f"instance_{int(target_id):04d}"
    if not td.exists():
        raise FileNotFoundError(f"missing Phase-6 target proposal for parity check: {td}")
    old_arrays = _load_npz(td / "partition.npz")
    if set(old_arrays) != set(arrays):
        raise RuntimeError(f"Phase-6/local array-key mismatch for target {target_id}")
    for k in sorted(arrays):
        if not np.array_equal(np.asarray(arrays[k]), np.asarray(old_arrays[k])):
            raise RuntimeError(f"Phase-7 local final partition differs from Phase 6: target={target_id} array={k}")
    if regions != _json(td / "regions.json"):
        raise RuntimeError(f"Phase-7 local final regions differ from Phase 6: target={target_id}")
    if edges != _json(td / "edges.json"):
        raise RuntimeError(f"Phase-7 local final edges differ from Phase 6: target={target_id}")


def propose_phase7(
    source_run: str | Path,
    phase5_dir: str | Path,
    phase6_proposal_dir: str | Path,
    out_dir: str | Path,
    *,
    grid_deg: float = 0.10,
) -> dict[str, Any]:
    """Emit local-vs-global causal region partitions at every historical prefix."""
    source = Path(source_run).resolve()
    p5 = Path(phase5_dir).resolve()
    p6 = Path(phase6_proposal_dir).resolve()
    out = Path(out_dir).resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"Phase-7 proposal output must be new or empty: {out}")
    out.mkdir(parents=True, exist_ok=True)

    reads: list[str] = []
    mp = source / "manifest.json"
    reads.append(_guard_source(source, mp, truth_allowed=False))
    manifest = _json(mp)
    sp = source / "bootstrap" / "seeds.json"
    reads.append(_guard_source(source, sp, truth_allowed=False))
    seeds = _json(sp)
    if not manifest.get("control_complete"):
        raise RuntimeError("source run is not control_complete")
    if abs(float(grid_deg) - 0.10) > 1e-12:
        raise ValueError("Phase 7 uses the frozen 0.10-degree chart")
    domain = seeds["controller_domain_deg"]
    _y0, _y1, _p0, _p1, h, w = _grid(domain, grid_deg)
    chart_cells = int(h * w)
    all_target_ids = {int(o["instance_id"]) for o in manifest["objects"]}
    p5_summary = _json(p5 / "summary.json")
    if int(p5_summary.get("head_target_depth_true_gap_violations", -1)) != 0:
        raise RuntimeError("Phase-5 head-centred invariant is not clean")
    p6_summary = _json(p6 / "summary.json")
    if p6_summary.get("truth_used") is not False:
        raise RuntimeError("Phase-6 proposal tree is not truth-free")

    global_mem = HeadEvidence.empty((h, w))
    global_gazes: list[tuple[float, float]] = []
    state_rows: list[dict[str, Any]] = []
    candidate_rows: dict[str, list[dict[str, Any]]] = {a: [] for a in ARMS}
    final_local_parity = 0
    depth_monotonic = True
    local_subset_checks = 0
    previous_global_depth = 0
    global_index = 0

    for obj in manifest["objects"]:
        iid = int(obj["instance_id"])
        name = str(obj["object_name"])
        trajectory = list(obj.get("trajectory", []))
        odir = source / "objects" / f"instance_{iid:04d}"
        nfix = int(obj["fixation_count"])
        for local_step in range(nfix):
            pp = odir / "patches" / f"fix_{local_step:02d}.npz"
            reads.append(_guard_source(source, pp, truth_allowed=False))
            patch = _load_npz(pp)
            delta = add_head_patch(global_mem, patch, iid, domain, grid_deg)
            depth_now = int(global_mem.depth_seen.sum())
            depth_monotonic &= depth_now >= previous_global_depth
            previous_global_depth = depth_now

            row = trajectory[local_step] if local_step < len(trajectory) else {}
            if "gaze_deg" in row:
                global_gazes.append(tuple(map(float, row["gaze_deg"])))
            current_target_gazes = [
                tuple(map(float, r["gaze_deg"]))
                for r in trajectory[: local_step + 1]
                if "gaze_deg" in r
            ]

            p5_state_path = p5 / "states" / f"global_{global_index:03d}" / "head-evidence.npz"
            local_state = _load_npz(p5_state_path)
            if np.any(np.asarray(local_state["depth_seen"], bool) & ~np.asarray(global_mem.depth_seen, bool)):
                raise RuntimeError(f"local head memory is not a subset of global memory at state {global_index}")
            local_subset_checks += 1
            global_state = _memory_state(local_state, global_mem)

            arm_results: dict[str, tuple[dict[str, np.ndarray], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]] = {}
            for arm, state in (("local", local_state), ("global", global_state)):
                arrays, regions, edges, diag = build_epistemic_partition(
                    state,
                    target_id=iid,
                    target_name=name,
                    all_target_ids=all_target_ids,
                    domain=domain,
                    grid_deg=grid_deg,
                    # Keep Phase-6 semantics for exact final-state parity. Global
                    # gaze history is recorded separately in the state summary.
                    gazes_deg=current_target_gazes,
                )
                arm_results[arm] = (arrays, regions, edges, diag)
                ad = out / "states" / f"global_{global_index:03d}" / arm
                ad.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(ad / "partition.npz", **arrays)
                _write_json(ad / "regions.json", regions)
                _write_json(ad / "edges.json", edges)
                ddiag = dict(diag)
                ddiag.update({
                    "arm": arm,
                    "global_index": int(global_index),
                    "instance_id": iid,
                    "object_name": name,
                    "local_step": int(local_step),
                    "is_target_final": bool(local_step + 1 == nfix),
                    "candidate_cell_count": _candidate_cells(regions),
                    "candidate_chart_fraction": float(_candidate_cells(regions) / chart_cells),
                    "largest_unknown_cell_count": _largest_kind_cells(regions, "UNKNOWN"),
                    "largest_unknown_chart_fraction": float(_largest_kind_cells(regions, "UNKNOWN") / chart_cells),
                })
                _write_json(ad / "summary.json", ddiag)
                for r in regions:
                    if bool(r.get("candidate")):
                        rr = dict(r)
                        rr.update({
                            "arm": arm,
                            "global_index": int(global_index),
                            "instance_id_target": iid,
                            "object_name_target": name,
                            "local_step": int(local_step),
                        })
                        candidate_rows[arm].append(rr)

            if local_step + 1 == nfix:
                la, lr, le, _ld = arm_results["local"]
                _assert_phase6_final_parity(la, lr, le, p6, iid)
                final_local_parity += 1

            local_sig = _partition_signature(*arm_results["local"][:3])
            global_sig = _partition_signature(*arm_results["global"][:3])
            state_rows.append({
                "global_index": int(global_index),
                "instance_id": iid,
                "object_name": name,
                "local_step": int(local_step),
                "is_target_final": bool(local_step + 1 == nfix),
                "action_source": row.get("action_source"),
                "gaze_deg": row.get("gaze_deg"),
                "global_completed_gaze_count": len(global_gazes),
                "global_head_memory_delta": delta,
                "local_depth_cells": int(np.asarray(local_state["depth_seen"], bool).sum()),
                "global_depth_cells": int(global_mem.depth_seen.sum()),
                "local": local_sig,
                "global": global_sig,
                "unknown_cells_reduced_by_global_memory": int(
                    sum(int(r["cell_count"]) for r in arm_results["local"][1] if r["kind"] == "UNKNOWN")
                    - sum(int(r["cell_count"]) for r in arm_results["global"][1] if r["kind"] == "UNKNOWN")
                ),
                "target_evidence_unmapped_cells_global": int(arm_results["global"][3]["target_evidence_unmapped_cells"]),
            })
            global_index += 1

    expected_states = int(manifest.get("total_fixations", -1))
    if global_index != expected_states:
        raise RuntimeError(f"prefix count mismatch: built {global_index}, manifest {expected_states}")
    if not depth_monotonic:
        raise RuntimeError("global head-depth memory is not monotonic")
    if final_local_parity != len(manifest["objects"]):
        raise RuntimeError(f"Phase-6 final parity incomplete: {final_local_parity}/{len(manifest['objects'])}")

    for arm in ARMS:
        _write_json(out / f"candidate-regions-{arm}.json", candidate_rows[arm])
    summary = {
        "schema": "PartitionGraph7-prefix-cross-target-proposals-v1",
        "source_run": str(source),
        "phase5_dir": str(p5),
        "phase6_proposal_dir": str(p6),
        "posthoc_representation_only": True,
        "truth_used": False,
        "controller_executed": False,
        "gaze_policy_defined": False,
        "candidate_ranking_defined": False,
        "object_identity_inherited": True,
        "grid_deg": float(grid_deg),
        "chart_shape_hw": [h, w],
        "chart_cells": chart_cells,
        "arms": list(ARMS),
        "state_count": global_index,
        "target_count": len(manifest["objects"]),
        "phase6_final_local_parity": final_local_parity,
        "local_memory_subset_checks": local_subset_checks,
        "global_head_depth_monotonic": bool(depth_monotonic),
        "candidate_region_counts": {a: len(candidate_rows[a]) for a in ARMS},
        "candidate_kind_counts": {
            a: dict(sorted(Counter(str(r["kind"]) for r in candidate_rows[a]).items())) for a in ARMS
        },
        "global_final_depth_cells": int(global_mem.depth_seen.sum()),
        "states": state_rows,
        "source_read_paths": sorted(set(reads)),
        "forbidden_read_paths": [],
    }
    _write_json(out / "summary.json", summary)
    return summary


def _region_lookup(regions: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(r["region_code"]): r for r in regions}


def _angles_to_codes(
    angles: np.ndarray,
    region_code: np.ndarray,
    domain: dict[str, Any],
    grid_deg: float,
) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(angles, np.float64).reshape(-1, 2)
    y0, _y1, p0, _p1, h, w = _grid(domain, grid_deg)
    yy, xx, ok = _cells(a[:, 0] if len(a) else np.empty(0), a[:, 1] if len(a) else np.empty(0), y0, p0, grid_deg, h, w)
    codes = np.zeros(len(a), np.int32)
    codes[ok] = np.asarray(region_code, np.int32)[yy[ok], xx[ok]]
    return codes, ok


def _candidate_capture_metrics(
    missed_codes: np.ndarray,
    regions: list[dict[str, Any]],
    chart_cells: int,
) -> tuple[dict[str, Any], dict[int, int]]:
    by = _region_lookup(regions)
    miss_by_code = Counter(int(c) for c in np.asarray(missed_codes).tolist() if int(c) > 0)
    candidate_codes = {c for c, r in by.items() if bool(r.get("candidate"))}
    captured = int(sum(n for c, n in miss_by_code.items() if c in candidate_codes))
    positive_codes = sorted(c for c in candidate_codes if miss_by_code.get(c, 0) > 0)
    neg_candidates = int(len(candidate_codes) - len(positive_codes))
    area_fracs = [float(by[c]["cell_count"] / chart_cells) for c in positive_codes]
    captured_bins = Counter()
    for c, n in miss_by_code.items():
        if c not in candidate_codes:
            continue
        f = float(by[c]["cell_count"] / chart_cells)
        placed = False
        for name, threshold in AREA_BINS:
            if f <= threshold:
                captured_bins[name] += int(n)
                placed = True
                break
        if not placed:
            captured_bins["gt_50"] += int(n)
    metrics = {
        "candidate_captured_missed_samples": captured,
        "truth_positive_candidate_regions": len(positive_codes),
        "truth_negative_candidate_regions": neg_candidates,
        "positive_candidate_region_fraction_min": None if not area_fracs else float(min(area_fracs)),
        "positive_candidate_region_fraction_median": None if not area_fracs else float(np.median(area_fracs)),
        "positive_candidate_region_fraction_max": None if not area_fracs else float(max(area_fracs)),
        "captured_misses_by_positive_region_area": {
            k: int(captured_bins.get(k, 0)) for k in ("le_05", "05_15", "15_50", "gt_50")
        },
    }
    return metrics, dict(miss_by_code)


def _code_row(code: int, by: dict[int, dict[str, Any]]) -> dict[str, Any] | None:
    return by.get(int(code)) if int(code) > 0 else None


def _state_arm_evaluation(
    *,
    arm: str,
    proposal_state_dir: Path,
    missed_angles: np.ndarray,
    newly_covered_angles: np.ndarray,
    all_truth_angles: np.ndarray,
    all_truth_ids: np.ndarray,
    target_id: int,
    next_gaze: tuple[float, float] | None,
    domain: dict[str, Any],
    grid_deg: float,
    chart_cells: int,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, list[dict[str, Any]]]:
    ad = proposal_state_dir / arm
    regions = _json(ad / "regions.json")
    by = _region_lookup(regions)
    with np.load(ad / "partition.npz", allow_pickle=False) as z:
        region_code = np.asarray(z["region_code"], np.int32)
        class_code = np.asarray(z["class_code"], np.uint8)
    missed_codes, _ = _angles_to_codes(missed_angles, region_code, domain, grid_deg)
    new_codes, _ = _angles_to_codes(newly_covered_angles, region_code, domain, grid_deg)
    capture, miss_by_code = _candidate_capture_metrics(missed_codes, regions, chart_cells)
    miss_kind = Counter()
    for code, n in miss_by_code.items():
        r = by.get(code)
        if r is not None:
            miss_kind[str(r["kind"])] += int(n)

    all_codes, all_ok = _angles_to_codes(all_truth_angles, region_code, domain, grid_deg)
    dense_by_code = Counter(int(v) for v in all_codes[all_ok].tolist() if int(v) > 0)
    target_mask = np.asarray(all_truth_ids, np.int32) == int(target_id)
    target_truth_by_code = Counter(int(v) for v in all_codes[target_mask & all_ok].tolist() if int(v) > 0)
    region_rows: list[dict[str, Any]] = []
    for r in regions:
        c = int(r["region_code"])
        nm = int(miss_by_code.get(c, 0))
        region_rows.append({
            "arm": arm,
            "region_code": c,
            "region_id": r["region_id"],
            "kind": r["kind"],
            "candidate": bool(r.get("candidate")),
            "region_cell_count": int(r["cell_count"]),
            "region_chart_fraction": float(int(r["cell_count"]) / chart_cells),
            "dense_first_hit_samples_in_region": int(dense_by_code.get(c, 0)),
            "target_truth_samples_in_region": int(target_truth_by_code.get(c, 0)),
            "missed_target_samples_in_region": nm,
            "truth_positive": bool(nm > 0),
        })

    next_info = None
    if next_gaze is not None:
        c, ok = _angles_to_codes(np.asarray([next_gaze], np.float64), region_code, domain, grid_deg)
        code = int(c[0]) if bool(ok[0]) else 0
        rr = _code_row(code, by)
        newly_by_code = Counter(int(v) for v in new_codes.tolist() if int(v) > 0)
        next_info = {
            "gaze_deg": [float(next_gaze[0]), float(next_gaze[1])],
            "inside_chart": bool(ok[0]),
            "region_code": code,
            "region_id": None if rr is None else rr["region_id"],
            "region_kind": None if rr is None else rr["kind"],
            "region_candidate": False if rr is None else bool(rr.get("candidate")),
            "current_missed_samples_in_region": int(miss_by_code.get(code, 0)),
            "newly_covered_samples_in_region": int(newly_by_code.get(code, 0)),
            "current_region_truth_positive": bool(miss_by_code.get(code, 0) > 0),
            "next_gain_region_positive": bool(newly_by_code.get(code, 0) > 0),
        }

    metrics = dict(capture)
    metrics.update({
        "arm": arm,
        "missed_by_region_kind": dict(sorted((k, int(v)) for k, v in miss_kind.items())),
        "candidate_recall": None if len(missed_angles) == 0 else float(capture["candidate_captured_missed_samples"] / len(missed_angles)),
        "target_evidence_unmapped_misses": int(miss_kind.get("TARGET_EVIDENCE_UNMAPPED", 0)),
        "target_support_misses": int(miss_kind.get("TARGET_SUPPORT", 0)),
        "next_gaze_center": next_info,
    })
    return metrics, missed_codes, class_code, region_rows


def evaluate_phase7(
    source_run: str | Path,
    proposal_dir: str | Path,
    phase6_evaluation_dir: str | Path,
    out_dir: str | Path,
    *,
    grid_deg: float = 0.10,
    strict_golden: bool = True,
) -> dict[str, Any]:
    """Offline truth evaluation of both prefix proposal arms.

    The Phase-7 proposal tree is read-only here. Dense truth and prefix maps are
    evaluator-only inputs and are never copied into the proposal tree.
    """
    source = Path(source_run).resolve()
    prop = Path(proposal_dir).resolve()
    p6eval = Path(phase6_evaluation_dir).resolve()
    out = Path(out_dir).resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"Phase-7 evaluation output must be new or empty: {out}")
    out.mkdir(parents=True, exist_ok=True)

    truth_reads: list[str] = []
    mp = source / "manifest.json"
    truth_reads.append(_guard_source(source, mp, truth_allowed=True))
    manifest = _json(mp)
    sp = source / "bootstrap" / "seeds.json"
    truth_reads.append(_guard_source(source, sp, truth_allowed=True))
    seeds = _json(sp)
    domain = seeds["controller_domain_deg"]
    tp = source / "bootstrap" / "evaluation_only" / "reachable_samples.npz"
    truth_reads.append(_guard_source(source, tp, truth_allowed=True))
    with np.load(tp, allow_pickle=False) as z:
        truth_ids = np.asarray(z["instance_id"], np.int32)
        truth_xyz = np.asarray(z["xyz_h"], np.float64)
        truth_angles = np.asarray(z["yaw_pitch_deg"], np.float64)
    prop_summary = _json(prop / "summary.json")
    if prop_summary.get("truth_used") is not False or int(prop_summary.get("state_count", -1)) != int(manifest.get("total_fixations", -2)):
        raise RuntimeError("Phase-7 proposal tree is not the expected truth-free 104-state tree")
    chart_cells = int(prop_summary["chart_cells"])
    y0, _y1, p0, _p1, h, w = _grid(domain, grid_deg)

    by_id = {int(o["instance_id"]): o for o in manifest["objects"]}
    state_eval: list[dict[str, Any]] = []
    region_eval: list[dict[str, Any]] = []
    final_totals = Counter()
    final_candidate_capture = Counter()
    final_positive_regions = Counter()
    prefix_totals = Counter()
    transition_counts: Counter[str] = Counter()
    next_ref = {a: Counter() for a in ARMS}
    global_index = 0

    for obj in manifest["objects"]:
        iid = int(obj["instance_id"])
        name = str(obj["object_name"])
        trajectory = list(obj.get("trajectory", []))
        ref_mask = truth_ids == iid
        ref = truth_xyz[ref_mask]
        ang = truth_angles[ref_mask]
        odir = source / "objects" / f"instance_{iid:04d}"
        nfix = int(obj["fixation_count"])
        for local_step in range(nfix):
            map_path = odir / "maps" / f"fix_{local_step:02d}.npz"
            truth_reads.append(_guard_source(source, map_path, truth_allowed=True))
            with np.load(map_path, allow_pickle=False) as z:
                sm = np.asarray(z["xyz_h"], np.float64)
            sm = sm[np.isfinite(sm).all(axis=1)]
            cov = _covered(ref, sm, FUSION_RADIUS_M)
            miss = ~cov
            missed_ang = ang[miss]
            newly_ang = np.empty((0, 2), np.float64)
            next_gaze = None
            if local_step + 1 < nfix:
                next_path = odir / "maps" / f"fix_{local_step + 1:02d}.npz"
                truth_reads.append(_guard_source(source, next_path, truth_allowed=True))
                with np.load(next_path, allow_pickle=False) as z:
                    sm2 = np.asarray(z["xyz_h"], np.float64)
                sm2 = sm2[np.isfinite(sm2).all(axis=1)]
                cov2 = _covered(ref, sm2, FUSION_RADIUS_M)
                newly_ang = ang[(~cov) & cov2]
                if local_step + 1 < len(trajectory) and "gaze_deg" in trajectory[local_step + 1]:
                    next_gaze = tuple(map(float, trajectory[local_step + 1]["gaze_deg"]))

            prefix_totals["reachable_state_samples"] += len(ref)
            prefix_totals["covered_state_samples"] += int(cov.sum())
            prefix_totals["missed_state_samples"] += int(miss.sum())
            prefix_totals["newly_covered_next_state_samples"] += len(newly_ang)

            sd = prop / "states" / f"global_{global_index:03d}"
            arm_metrics: dict[str, dict[str, Any]] = {}
            arm_miss_codes: dict[str, np.ndarray] = {}
            for arm in ARMS:
                met, miss_codes, _class_code, rr = _state_arm_evaluation(
                    arm=arm,
                    proposal_state_dir=sd,
                    missed_angles=missed_ang,
                    newly_covered_angles=newly_ang,
                    all_truth_angles=truth_angles,
                    all_truth_ids=truth_ids,
                    target_id=iid,
                    next_gaze=next_gaze,
                    domain=domain,
                    grid_deg=grid_deg,
                    chart_cells=chart_cells,
                )
                arm_metrics[arm] = met
                arm_miss_codes[arm] = miss_codes
                for row in rr:
                    row.update({
                        "global_index": int(global_index),
                        "instance_id_target": iid,
                        "object_name_target": name,
                        "local_step": int(local_step),
                    })
                    region_eval.append(row)
                if met["next_gaze_center"] is not None:
                    ni = met["next_gaze_center"]
                    next_ref[arm]["states"] += 1
                    next_ref[arm]["center_on_candidate"] += int(bool(ni["region_candidate"]))
                    next_ref[arm]["center_on_truth_positive"] += int(bool(ni["current_region_truth_positive"]))
                    next_ref[arm]["center_on_next_gain_positive"] += int(bool(ni["next_gain_region_positive"]))

            # Per-miss local/global transitions and containing-region area change.
            local_by = _region_lookup(_json(sd / "local" / "regions.json"))
            global_by = _region_lookup(_json(sd / "global" / "regions.json"))
            area_delta: list[float] = []
            smaller = equal = larger = 0
            for lc, gc in zip(arm_miss_codes["local"].tolist(), arm_miss_codes["global"].tolist()):
                lr = local_by.get(int(lc)); gr = global_by.get(int(gc))
                lk = "OUTSIDE" if lr is None else str(lr["kind"])
                gk = "OUTSIDE" if gr is None else str(gr["kind"])
                transition_counts[f"{lk}->{gk}"] += 1
                if lr is not None and gr is not None:
                    lf = float(lr["cell_count"] / chart_cells)
                    gf = float(gr["cell_count"] / chart_cells)
                    area_delta.append(gf - lf)
                    if gf < lf - 1e-15: smaller += 1
                    elif gf > lf + 1e-15: larger += 1
                    else: equal += 1

            # Evaluation-only truth raster for the demo.
            miss_count = np.zeros((h, w), np.uint16)
            yy, xx, ok = _cells(missed_ang[:, 0] if len(missed_ang) else np.empty(0), missed_ang[:, 1] if len(missed_ang) else np.empty(0), y0, p0, grid_deg, h, w)
            if len(yy):
                np.add.at(miss_count, (yy[ok], xx[ok]), 1)
            gain_count = np.zeros((h, w), np.uint16)
            gy, gx, gok = _cells(newly_ang[:, 0] if len(newly_ang) else np.empty(0), newly_ang[:, 1] if len(newly_ang) else np.empty(0), y0, p0, grid_deg, h, w)
            if len(gy):
                np.add.at(gain_count, (gy[gok], gx[gok]), 1)
            ed = out / "states" / f"global_{global_index:03d}"
            ed.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(ed / "truth-evaluation.npz", missed_count=miss_count, next_gain_count=gain_count)

            state_row = {
                "global_index": int(global_index),
                "instance_id": iid,
                "object_name": name,
                "local_step": int(local_step),
                "is_target_final": bool(local_step + 1 == nfix),
                "reachable_samples": int(len(ref)),
                "covered_samples": int(cov.sum()),
                "missed_samples": int(miss.sum()),
                "newly_covered_at_next_prefix": int(len(newly_ang)),
                "local": arm_metrics["local"],
                "global": arm_metrics["global"],
                "global_vs_local_miss_containing_region": {
                    "smaller": int(smaller),
                    "equal": int(equal),
                    "larger": int(larger),
                    "median_chart_fraction_delta": None if not area_delta else float(np.median(area_delta)),
                },
            }
            state_eval.append(state_row)

            if local_step + 1 == nfix:
                final_totals["reachable"] += len(ref)
                final_totals["covered"] += int(cov.sum())
                final_totals["missed"] += int(miss.sum())
                for arm in ARMS:
                    final_candidate_capture[arm] += int(arm_metrics[arm]["candidate_captured_missed_samples"])
                    final_positive_regions[arm] += int(arm_metrics[arm]["truth_positive_candidate_regions"])
            global_index += 1

    p6_summary = _json(p6eval / "summary.json")
    expected_final = (
        int(p6_summary["reachable_samples_total"]),
        int(p6_summary["covered_samples_total"]),
        int(p6_summary["missed_samples_total"]),
    )
    actual_final = (int(final_totals["reachable"]), int(final_totals["covered"]), int(final_totals["missed"]))
    if strict_golden and expected_final != (29288, 25618, 3670):
        raise RuntimeError(f"Phase-6 evaluator no longer carries golden totals: {expected_final}")
    if strict_golden and actual_final != expected_final:
        raise RuntimeError(f"Phase-7 final-prefix totals differ from Phase 6: {actual_final} != {expected_final}")
    if strict_golden and int(final_candidate_capture["local"]) != int(p6_summary["candidate_captured_missed_samples"]):
        raise RuntimeError("Phase-7 local final candidate capture differs from Phase 6")
    if strict_golden and int(final_positive_regions["local"]) != int(p6_summary["truth_positive_candidate_region_count"]):
        raise RuntimeError("Phase-7 local final positive-region count differs from Phase 6")

    _write_json(out / "state-evaluation.json", state_eval)
    _write_json(out / "region-evaluation.json", region_eval)

    def aggregate_arm(arm: str) -> dict[str, Any]:
        rows = [s[arm] for s in state_eval]
        total_miss = int(sum(int(s["missed_samples"]) for s in state_eval))
        captured = int(sum(int(r["candidate_captured_missed_samples"]) for r in rows))
        positives = [int(r["truth_positive_candidate_regions"]) for r in rows]
        area = Counter()
        for r in rows:
            for k, v in r["captured_misses_by_positive_region_area"].items():
                area[k] += int(v)
        return {
            "state_count": len(rows),
            "candidate_captured_state_misses": captured,
            "candidate_recall_over_state_misses": None if total_miss == 0 else float(captured / total_miss),
            "truth_positive_candidate_regions_total": int(sum(positives)),
            "states_with_0_positive_candidates": int(sum(v == 0 for v in positives)),
            "states_with_1_positive_candidate": int(sum(v == 1 for v in positives)),
            "states_with_2plus_positive_candidates": int(sum(v >= 2 for v in positives)),
            "captured_misses_by_positive_region_area": {k: int(area[k]) for k in ("le_05", "05_15", "15_50", "gt_50")},
            "target_evidence_unmapped_state_misses": int(sum(int(r["target_evidence_unmapped_misses"]) for r in rows)),
            "target_support_state_misses": int(sum(int(r["target_support_misses"]) for r in rows)),
            "historical_next_gaze_center": {k: int(v) for k, v in sorted(next_ref[arm].items())},
        }

    summary = {
        "schema": "PartitionGraph7-prefix-truth-evaluation-v1",
        "source_run": str(source),
        "proposal_dir": str(prop),
        "phase6_evaluation_dir": str(p6eval),
        "offline_truth_evaluation_only": True,
        "proposal_tree_truth_free": True,
        "gaze_policy_defined": False,
        "candidate_ranking_defined": False,
        "state_count": len(state_eval),
        "target_count": len(manifest["objects"]),
        "prefix_totals": {k: int(v) for k, v in sorted(prefix_totals.items())},
        "final_prefix_totals": {k: int(v) for k, v in sorted(final_totals.items())},
        "phase6_final_parity": {
            "expected": list(expected_final),
            "actual": list(actual_final),
            "local_candidate_capture_expected": int(p6_summary["candidate_captured_missed_samples"]),
            "local_candidate_capture_actual": int(final_candidate_capture["local"]),
            "local_positive_regions_expected": int(p6_summary["truth_positive_candidate_region_count"]),
            "local_positive_regions_actual": int(final_positive_regions["local"]),
        },
        "local": aggregate_arm("local"),
        "global": aggregate_arm("global"),
        "miss_region_kind_transitions_local_to_global": dict(sorted((k, int(v)) for k, v in transition_counts.items())),
        "truth_read_paths": sorted(set(truth_reads)),
        "interpretation": (
            "offline comparison of two truth-free prefix region representations; truth-positive labels, recall and historical-next gains are not controller features"
        ),
    }
    _write_json(out / "summary.json", summary)
    return summary
