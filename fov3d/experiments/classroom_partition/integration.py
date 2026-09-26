"""Partition-Graph Phase 8: causal target-evidence integration benchmark.

Phase 7 showed that causal cross-target head memory localizes the residual visual
field, but also turns a majority of current target misses into
``TARGET_EVIDENCE_UNMAPPED``: valid target geometry had already been measured by
some earlier look and simply was not routed into the target's persistent map.

Phase 8 remains retrospective and does not modify the historical SurfaceMap.  It
constructs a *shadow integrated target geometry* at each accepted prefix:

    historical target map XYZ
        UNION
    every causally measured valid target-labelled XYZ up to that prefix

The extra geometry is controller-time evidence from saved patches.  It is not
evaluation truth.  The union is deliberately representation-level: no new
surfel averaging, colour update, support-count update, gaze, controller, matcher,
fusion or renderer execution is introduced.

The proposer is truth-free.  The separate evaluator is the only stage allowed to
open dense reachable-surface truth.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import json

import numpy as np

from fov3d.experiments.classroom_partition.benchmark import (
    FUSION_RADIUS_M,
    _cells,
    _covered,
    _grid,
    build_epistemic_partition,
)
from fov3d.experiments.classroom_partition.incidental import (
    HeadEvidence,
    _valid_patch_samples,
    add_head_patch,
)
from fov3d.experiments.classroom_partition.joint import support_depth_from_map
from fov3d.experiments.classroom_partition.prefix_benchmark import (
    AREA_BINS,
    _angles_to_codes,
    _candidate_capture_metrics,
    _memory_state,
    _partition_signature,
    _region_lookup,
)


ARMS = ("historical_global", "integrated")


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
        raise RuntimeError(f"truth/renderer path forbidden to Phase-8 proposer: {rel.as_posix()}")
    return rel.as_posix()


def _finite_xyz(x: np.ndarray) -> np.ndarray:
    a = np.asarray(x, np.float64).reshape(-1, 3)
    return a[np.isfinite(a).all(axis=1)]


def effective_target_geometry(map_xyz_h: np.ndarray, cross_target_xyz_h: np.ndarray) -> np.ndarray:
    """Return the shadow integrated geometry without mutating either input.

    Duplicates are intentionally retained.  Coverage/support queries are set-like
    under the frozen 12-mm rule, while retaining raw measurements preserves a
    clean no-new-fusion interpretation and exact provenance.
    """
    a = _finite_xyz(map_xyz_h)
    b = _finite_xyz(cross_target_xyz_h)
    if not len(a):
        return b.copy()
    if not len(b):
        return a.copy()
    return np.vstack((a, b))


def cross_target_novelty(map_xyz_h: np.ndarray, cross_target_xyz_h: np.ndarray) -> dict[str, Any]:
    """Describe how much deferred target evidence is outside the historical map.

    This is truth-free: the reference points are saved controller-time target
    measurements, not dense scene truth.
    """
    base = _finite_xyz(map_xyz_h)
    cross = _finite_xyz(cross_target_xyz_h)
    if not len(cross):
        return {
            "cross_target_points": 0,
            "represented_within_12mm": 0,
            "novel_beyond_12mm": 0,
            "novel_fraction": None,
        }
    represented = _covered(cross, base, FUSION_RADIUS_M)
    nrep = int(represented.sum())
    return {
        "cross_target_points": int(len(cross)),
        "represented_within_12mm": nrep,
        "novel_beyond_12mm": int(len(cross) - nrep),
        "novel_fraction": float((len(cross) - nrep) / len(cross)),
    }


def _partition_exact_parity(
    arrays: dict[str, np.ndarray],
    regions: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    phase7_state_dir: Path,
) -> None:
    """Require our reconstructed pre-integration global arm to equal Phase 7."""
    old_arrays = _load_npz(phase7_state_dir / "global" / "partition.npz")
    if set(old_arrays) != set(arrays):
        raise RuntimeError("Phase-8 historical-global array keys differ from Phase 7")
    for k in sorted(arrays):
        if not np.array_equal(np.asarray(arrays[k]), np.asarray(old_arrays[k])):
            raise RuntimeError(f"Phase-8 historical-global array differs from Phase 7: {k}")
    if regions != _json(phase7_state_dir / "global" / "regions.json"):
        raise RuntimeError("Phase-8 historical-global regions differ from Phase 7")
    if edges != _json(phase7_state_dir / "global" / "edges.json"):
        raise RuntimeError("Phase-8 historical-global edges differ from Phase 7")


def _concat_chunks(chunks: list[np.ndarray]) -> np.ndarray:
    if not chunks:
        return np.empty((0, 3), np.float32)
    return np.vstack([np.asarray(x, np.float32).reshape(-1, 3) for x in chunks])


def _concat_int_chunks(chunks: list[np.ndarray]) -> np.ndarray:
    if not chunks:
        return np.empty((0,), np.int32)
    return np.concatenate([np.asarray(x, np.int32).reshape(-1) for x in chunks])


def propose_phase8(
    source_run: str | Path,
    phase5_dir: str | Path,
    phase7_proposal_dir: str | Path,
    out_dir: str | Path,
    *,
    grid_deg: float = 0.10,
) -> dict[str, Any]:
    """Build a truth-free shadow-integrated target representation for 104 prefixes.

    Target evidence for object ``i`` means valid saved patch samples labelled
    ``i`` from every completed look up to the current prefix. Source-target
    provenance keeps the cross-target subset explicit. Because the accepted run
    processes objects sequentially, cross-target evidence available when a target
    begins comes only from earlier target runs; own-target evidence then grows
    causally during that target's trajectory.
    """
    source = Path(source_run).resolve()
    p5 = Path(phase5_dir).resolve()
    p7 = Path(phase7_proposal_dir).resolve()
    out = Path(out_dir).resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"Phase-8 proposal output must be new or empty: {out}")
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
        raise ValueError("Phase 8 uses the frozen 0.10-degree chart")
    domain = seeds["controller_domain_deg"]
    _y0, _y1, _p0, _p1, h, w = _grid(domain, grid_deg)
    chart_cells = int(h * w)
    all_target_ids = {int(o["instance_id"]) for o in manifest["objects"]}

    p5_summary = _json(p5 / "summary.json")
    if int(p5_summary.get("head_target_depth_true_gap_violations", -1)) != 0:
        raise RuntimeError("Phase-5 head-centred invariant is not clean")
    p7_summary = _json(p7 / "summary.json")
    if p7_summary.get("truth_used") is not False or int(p7_summary.get("state_count", -1)) != int(manifest.get("total_fixations", -2)):
        raise RuntimeError("Phase-7 proposal tree is not the expected truth-free prefix tree")

    global_mem = HeadEvidence.empty((h, w))
    # Per instance, retain every valid controller-time XYZ measurement, with
    # source-target provenance so cross-target and own-target contributions remain separable.
    pool_xyz: dict[int, list[np.ndarray]] = defaultdict(list)
    pool_global: dict[int, list[np.ndarray]] = defaultdict(list)
    pool_source_target: dict[int, list[np.ndarray]] = defaultdict(list)

    state_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    phase7_parity = 0
    target_evidence_unmapped_total = 0
    target_evidence_unmapped_states = 0
    global_index = 0

    for obj in manifest["objects"]:
        iid = int(obj["instance_id"])
        name = str(obj["object_name"])
        trajectory = list(obj.get("trajectory", []))
        odir = source / "objects" / f"instance_{iid:04d}"
        nfix = int(obj["fixation_count"])
        target_start_global = int(global_index)

        # The reservoir already contains measurements from all earlier targets.
        # Own-target measurements are added causally as each current look completes.
        td = out / "targets" / f"instance_{iid:04d}"
        td.mkdir(parents=True, exist_ok=True)

        for local_step in range(nfix):
            pp = odir / "patches" / f"fix_{local_step:02d}.npz"
            reads.append(_guard_source(source, pp, truth_allowed=False))
            patch = _load_npz(pp)
            # Global memory includes the current completed look, matching Phase 7.
            add_head_patch(global_mem, patch, iid, domain, grid_deg)

            # Route every valid measured instance into a causal per-instance
            # geometry reservoir.  This is the architecture under test: measured
            # target geometry is retained regardless of which target was active.
            pts, ids, _valid = _valid_patch_samples(patch)
            for observed in sorted(int(v) for v in np.unique(ids) if int(v) > 0):
                q = pts[ids == observed].astype(np.float32, copy=True)
                if not len(q):
                    continue
                pool_xyz[observed].append(q)
                pool_global[observed].append(np.full(len(q), global_index, np.int32))
                pool_source_target[observed].append(np.full(len(q), iid, np.int32))

            measured_xyz = _concat_chunks(pool_xyz.get(iid, []))
            measured_global = _concat_int_chunks(pool_global.get(iid, []))
            measured_source_target = _concat_int_chunks(pool_source_target.get(iid, []))
            if not (len(measured_xyz) == len(measured_global) == len(measured_source_target)):
                raise RuntimeError(f"target-evidence provenance length mismatch for {iid}")
            if len(measured_global) and int(measured_global.max()) > global_index:
                raise RuntimeError(f"future target evidence reached state {global_index}")
            cross_mask = measured_source_target != iid
            cross_xyz = measured_xyz[cross_mask]
            cross_source_ids = sorted(set(int(x) for x in measured_source_target[cross_mask].tolist()))

            p5_state = _load_npz(p5 / "states" / f"global_{global_index:03d}" / "head-evidence.npz")
            historical_global_state = _memory_state(p5_state, global_mem)
            current_gazes = [
                tuple(map(float, r["gaze_deg"]))
                for r in trajectory[: local_step + 1]
                if "gaze_deg" in r
            ]

            # Reconstruct Phase-7 global exactly before changing target support.
            ha, hr, he, hd = build_epistemic_partition(
                historical_global_state,
                target_id=iid,
                target_name=name,
                all_target_ids=all_target_ids,
                domain=domain,
                grid_deg=grid_deg,
                gazes_deg=current_gazes,
            )
            _partition_exact_parity(ha, hr, he, p7 / "states" / f"global_{global_index:03d}")
            phase7_parity += 1

            map_path = odir / "maps" / f"fix_{local_step:02d}.npz"
            reads.append(_guard_source(source, map_path, truth_allowed=False))
            snap = _load_npz(map_path)
            map_xyz = _finite_xyz(snap["xyz_h"])
            effective_xyz = effective_target_geometry(map_xyz, measured_xyz)
            layer = support_depth_from_map(
                effective_xyz,
                domain,
                grid_deg,
                instance_id=iid,
                object_name=name,
            )
            integrated_state = dict(historical_global_state)
            integrated_state["target_support"] = layer.support.astype(bool)
            ia, ir, ie, idiag = build_epistemic_partition(
                integrated_state,
                target_id=iid,
                target_name=name,
                all_target_ids=all_target_ids,
                domain=domain,
                grid_deg=grid_deg,
                gazes_deg=current_gazes,
            )

            unmapped = int(idiag["target_evidence_unmapped_cells"])
            target_evidence_unmapped_total += unmapped
            target_evidence_unmapped_states += int(unmapped > 0)
            if unmapped:
                raise RuntimeError(
                    f"integrated target geometry left TARGET_EVIDENCE_UNMAPPED cells at state {global_index}: {unmapped}"
                )

            sd = out / "states" / f"global_{global_index:03d}" / "integrated"
            sd.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(sd / "partition.npz", **ia)
            _write_json(sd / "regions.json", ir)
            _write_json(sd / "edges.json", ie)

            novelty = cross_target_novelty(map_xyz, measured_xyz)
            cross_novelty = cross_target_novelty(map_xyz, cross_xyz)
            hist_support = np.asarray(p5_state["target_support"], bool)
            added_support = int((layer.support & ~hist_support).sum())
            sig_h = _partition_signature(ha, hr, he)
            sig_i = _partition_signature(ia, ir, ie)
            row = {
                "global_index": int(global_index),
                "instance_id": iid,
                "object_name": name,
                "local_step": int(local_step),
                "is_target_final": bool(local_step + 1 == nfix),
                "historical_map_points": int(len(map_xyz)),
                "effective_geometry_points": int(len(effective_xyz)),
                "causal_target_evidence": novelty,
                "cross_target_evidence": cross_novelty,
                "measured_target_points": int(len(measured_xyz)),
                "measured_cross_target_points": int(len(cross_xyz)),
                "measured_own_target_points": int(len(measured_xyz) - len(cross_xyz)),
                "historical_target_support_cells": int(hist_support.sum()),
                "integrated_target_support_cells": int(layer.support.sum()),
                "added_target_support_cells": added_support,
                "historical_global": sig_h,
                "integrated": sig_i,
                "integrated_target_evidence_unmapped_cells": unmapped,
                "cross_target_source_ids": cross_source_ids,
            }
            state_rows.append(row)
            ddiag = dict(idiag)
            ddiag.update(row)
            _write_json(sd / "summary.json", ddiag)
            for r in ir:
                if bool(r.get("candidate")):
                    rr = dict(r)
                    rr.update({
                        "global_index": int(global_index),
                        "instance_id_target": iid,
                        "object_name_target": name,
                        "local_step": int(local_step),
                    })
                    candidate_rows.append(rr)

            global_index += 1

        # Persist all causal target measurements available through this target's
        # final prefix.  The evaluator filters by source_global_index for earlier
        # prefixes, so no future measurement is credited retroactively.
        all_xyz = _concat_chunks(pool_xyz.get(iid, []))
        all_global = _concat_int_chunks(pool_global.get(iid, []))
        all_source_target = _concat_int_chunks(pool_source_target.get(iid, []))
        if len(all_global) and int(all_global.max()) >= global_index:
            raise RuntimeError(f"target evidence extends beyond target-final prefix for {iid}")
        np.savez_compressed(
            td / "causal-target-evidence.npz",
            xyz_h=all_xyz.astype(np.float32),
            source_global_index=all_global.astype(np.int32),
            source_active_target_id=all_source_target.astype(np.int32),
        )
        cross = all_source_target != iid
        target_meta = {
            "instance_id": iid,
            "object_name": name,
            "target_start_global_index": target_start_global,
            "target_final_global_index": global_index - 1,
            "causal_target_point_count": int(len(all_xyz)),
            "cross_target_point_count": int(cross.sum()),
            "own_target_point_count": int((~cross).sum()),
            "source_fixation_count": int(len(set(all_global.tolist())) if len(all_global) else 0),
            "cross_target_source_ids": sorted(set(int(x) for x in all_source_target[cross].tolist())),
            "all_sources_causal": bool(not len(all_global) or int(all_global.max()) < global_index),
        }
        _write_json(td / "summary.json", target_meta)

    expected_states = int(manifest.get("total_fixations", -1))
    if global_index != expected_states:
        raise RuntimeError(f"Phase-8 prefix count mismatch: {global_index} != {expected_states}")
    if phase7_parity != expected_states:
        raise RuntimeError(f"Phase-7 global parity incomplete: {phase7_parity}/{expected_states}")

    _write_json(out / "candidate-regions-integrated.json", candidate_rows)
    summary = {
        "schema": "PartitionGraph8-causal-target-integration-v1",
        "source_run": str(source),
        "phase5_dir": str(p5),
        "phase7_proposal_dir": str(p7),
        "posthoc_representation_only": True,
        "truth_used": False,
        "controller_executed": False,
        "gaze_policy_defined": False,
        "candidate_ranking_defined": False,
        "historical_map_modified": False,
        "object_identity_inherited": True,
        "integration_semantics": "shadow union of historical target-map XYZ with all causally measured valid target XYZ retained by instance identity; cross-target provenance reported separately; no new surfel fusion/averaging",
        "grid_deg": float(grid_deg),
        "chart_shape_hw": [h, w],
        "chart_cells": chart_cells,
        "state_count": global_index,
        "target_count": len(manifest["objects"]),
        "phase7_global_parity_checks": phase7_parity,
        "integrated_target_evidence_unmapped_cells_total": int(target_evidence_unmapped_total),
        "states_with_integrated_target_evidence_unmapped": int(target_evidence_unmapped_states),
        "candidate_region_count": len(candidate_rows),
        "candidate_kind_counts": dict(sorted(Counter(str(r["kind"]) for r in candidate_rows).items())),
        "states": state_rows,
        "source_read_paths": sorted(set(reads)),
        "forbidden_read_paths": [],
    }
    _write_json(out / "summary.json", summary)
    return summary


def _state_integrated_evaluation(
    *,
    proposal_state_dir: Path,
    missed_angles: np.ndarray,
    next_gain_angles: np.ndarray,
    all_truth_angles: np.ndarray,
    all_truth_ids: np.ndarray,
    target_id: int,
    next_gaze: tuple[float, float] | None,
    domain: dict[str, Any],
    grid_deg: float,
    chart_cells: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    regions = _json(proposal_state_dir / "regions.json")
    by = _region_lookup(regions)
    with np.load(proposal_state_dir / "partition.npz", allow_pickle=False) as z:
        region_code = np.asarray(z["region_code"], np.int32)
    missed_codes, _ = _angles_to_codes(missed_angles, region_code, domain, grid_deg)
    next_codes, _ = _angles_to_codes(next_gain_angles, region_code, domain, grid_deg)
    capture, miss_by_code = _candidate_capture_metrics(missed_codes, regions, chart_cells)

    miss_kind = Counter()
    for code, n in miss_by_code.items():
        row = by.get(int(code))
        if row is not None:
            miss_kind[str(row["kind"])] += int(n)

    all_codes, all_ok = _angles_to_codes(all_truth_angles, region_code, domain, grid_deg)
    dense_by_code = Counter(int(v) for v in all_codes[all_ok].tolist() if int(v) > 0)
    tmask = np.asarray(all_truth_ids, np.int32) == int(target_id)
    target_by_code = Counter(int(v) for v in all_codes[tmask & all_ok].tolist() if int(v) > 0)
    region_rows: list[dict[str, Any]] = []
    for r in regions:
        c = int(r["region_code"])
        nm = int(miss_by_code.get(c, 0))
        region_rows.append({
            "region_code": c,
            "region_id": r["region_id"],
            "kind": r["kind"],
            "candidate": bool(r.get("candidate")),
            "region_cell_count": int(r["cell_count"]),
            "region_chart_fraction": float(int(r["cell_count"]) / chart_cells),
            "dense_first_hit_samples_in_region": int(dense_by_code.get(c, 0)),
            "target_truth_samples_in_region": int(target_by_code.get(c, 0)),
            "residual_missed_target_samples_in_region": nm,
            "truth_positive_residual": bool(nm > 0),
        })

    next_info = None
    if next_gaze is not None:
        c, ok = _angles_to_codes(np.asarray([next_gaze], np.float64), region_code, domain, grid_deg)
        code = int(c[0]) if bool(ok[0]) else 0
        rr = by.get(code)
        next_by = Counter(int(v) for v in next_codes.tolist() if int(v) > 0)
        next_info = {
            "gaze_deg": [float(next_gaze[0]), float(next_gaze[1])],
            "inside_chart": bool(ok[0]),
            "region_code": code,
            "region_id": None if rr is None else rr["region_id"],
            "region_kind": None if rr is None else rr["kind"],
            "region_candidate": False if rr is None else bool(rr.get("candidate")),
            "current_residual_misses_in_region": int(miss_by_code.get(code, 0)),
            "next_integrated_gain_in_region": int(next_by.get(code, 0)),
            "current_region_truth_positive_residual": bool(miss_by_code.get(code, 0) > 0),
            "next_gain_region_positive": bool(next_by.get(code, 0) > 0),
        }

    metrics = dict(capture)
    metrics.update({
        "residual_missed_by_region_kind": dict(sorted((k, int(v)) for k, v in miss_kind.items())),
        "candidate_recall_on_residual": None if len(missed_angles) == 0 else float(capture["candidate_captured_missed_samples"] / len(missed_angles)),
        "target_evidence_unmapped_residual_misses": int(miss_kind.get("TARGET_EVIDENCE_UNMAPPED", 0)),
        "target_support_residual_misses": int(miss_kind.get("TARGET_SUPPORT", 0)),
        "historical_next_gaze_center": next_info,
    })
    return metrics, region_rows


def evaluate_phase8(
    source_run: str | Path,
    proposal_dir: str | Path,
    phase7_evaluation_dir: str | Path,
    out_dir: str | Path,
    *,
    grid_deg: float = 0.10,
    strict_golden: bool = True,
) -> dict[str, Any]:
    """Offline dense-truth evaluation of the truth-free shadow integration."""
    source = Path(source_run).resolve()
    prop = Path(proposal_dir).resolve()
    p7e = Path(phase7_evaluation_dir).resolve()
    out = Path(out_dir).resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"Phase-8 evaluation output must be new or empty: {out}")
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
        raise RuntimeError("Phase-8 proposal tree is not the expected truth-free 104-state tree")
    if int(prop_summary.get("integrated_target_evidence_unmapped_cells_total", -1)) != 0:
        raise RuntimeError("Phase-8 proposer did not eliminate TARGET_EVIDENCE_UNMAPPED")
    chart_cells = int(prop_summary["chart_cells"])
    y0, _y1, p0, _p1, h, w = _grid(domain, grid_deg)

    p7_summary = _json(p7e / "summary.json")
    p7_states = _json(p7e / "state-evaluation.json")
    if len(p7_states) != int(prop_summary["state_count"]):
        raise RuntimeError("Phase-7/8 state-count mismatch")

    state_eval: list[dict[str, Any]] = []
    region_eval: list[dict[str, Any]] = []
    prefix = Counter()
    final = Counter()
    positive_counts: list[int] = []
    area = Counter()
    next_ref = Counter()
    historical_parity = 0
    global_index = 0

    for obj in manifest["objects"]:
        iid = int(obj["instance_id"])
        name = str(obj["object_name"])
        trajectory = list(obj.get("trajectory", []))
        ref_mask = truth_ids == iid
        ref = truth_xyz[ref_mask]
        ang = truth_angles[ref_mask]
        odir = source / "objects" / f"instance_{iid:04d}"
        evidence = _load_npz(prop / "targets" / f"instance_{iid:04d}" / "causal-target-evidence.npz")
        all_evidence_xyz = _finite_xyz(evidence["xyz_h"])
        evidence_global = np.asarray(evidence["source_global_index"], np.int32).reshape(-1)
        evidence_source_target = np.asarray(evidence["source_active_target_id"], np.int32).reshape(-1)
        if not (len(all_evidence_xyz) == len(evidence_global) == len(evidence_source_target)):
            raise RuntimeError(f"Phase-8 evidence/provenance mismatch for target {iid}")
        nfix = int(obj["fixation_count"])

        for local_step in range(nfix):
            map_path = odir / "maps" / f"fix_{local_step:02d}.npz"
            truth_reads.append(_guard_source(source, map_path, truth_allowed=True))
            snap = _load_npz(map_path)
            hist_xyz = _finite_xyz(snap["xyz_h"])
            causal_mask = evidence_global <= global_index
            causal_evidence = all_evidence_xyz[causal_mask]
            cross_evidence = all_evidence_xyz[causal_mask & (evidence_source_target != iid)]
            cross_xyz = effective_target_geometry(hist_xyz, cross_evidence)
            integrated_xyz = effective_target_geometry(hist_xyz, causal_evidence)

            hist_cov = _covered(ref, hist_xyz, FUSION_RADIUS_M)
            cross_cov = _covered(ref, cross_xyz, FUSION_RADIUS_M)
            int_cov = _covered(ref, integrated_xyz, FUSION_RADIUS_M)
            if np.any(hist_cov & ~cross_cov) or np.any(cross_cov & ~int_cov):
                raise RuntimeError(f"integration coverage is not monotone at state {global_index}")
            hist_miss = ~hist_cov
            residual = ~int_cov
            cross_gain = hist_miss & cross_cov
            integration_gain = hist_miss & int_cov
            own_retention_gain = integration_gain & ~cross_cov
            residual_ang = ang[residual]
            gain_ang = ang[integration_gain]

            old = p7_states[global_index]
            if int(old["global_index"]) != global_index or int(old["instance_id"]) != iid or int(old["local_step"]) != local_step:
                raise RuntimeError("Phase-7 state ordering differs from Phase 8")
            if int(old["covered_samples"]) != int(hist_cov.sum()) or int(old["missed_samples"]) != int(hist_miss.sum()):
                raise RuntimeError(f"Phase-8 historical coverage differs from Phase 7 at state {global_index}")
            historical_parity += 1

            next_gain_ang = np.empty((0, 2), np.float64)
            next_gaze = None
            if local_step + 1 < nfix:
                npth = odir / "maps" / f"fix_{local_step + 1:02d}.npz"
                truth_reads.append(_guard_source(source, npth, truth_allowed=True))
                ns = _load_npz(npth)
                next_evidence = all_evidence_xyz[evidence_global <= (global_index + 1)]
                next_xyz = effective_target_geometry(_finite_xyz(ns["xyz_h"]), next_evidence)
                next_cov = _covered(ref, next_xyz, FUSION_RADIUS_M)
                next_gain_ang = ang[(~int_cov) & next_cov]
                if local_step + 1 < len(trajectory) and "gaze_deg" in trajectory[local_step + 1]:
                    next_gaze = tuple(map(float, trajectory[local_step + 1]["gaze_deg"]))

            met, rr = _state_integrated_evaluation(
                proposal_state_dir=prop / "states" / f"global_{global_index:03d}" / "integrated",
                missed_angles=residual_ang,
                next_gain_angles=next_gain_ang,
                all_truth_angles=truth_angles,
                all_truth_ids=truth_ids,
                target_id=iid,
                next_gaze=next_gaze,
                domain=domain,
                grid_deg=grid_deg,
                chart_cells=chart_cells,
            )
            for row in rr:
                row.update({
                    "global_index": global_index,
                    "instance_id_target": iid,
                    "object_name_target": name,
                    "local_step": local_step,
                })
                region_eval.append(row)

            prefix["reachable_state_samples"] += len(ref)
            prefix["historical_covered_state_samples"] += int(hist_cov.sum())
            prefix["historical_missed_state_samples"] += int(hist_miss.sum())
            prefix["cross_target_integration_gain_state_samples"] += int(cross_gain.sum())
            prefix["own_target_retention_gain_state_samples"] += int(own_retention_gain.sum())
            prefix["integration_gain_state_samples"] += int(integration_gain.sum())
            prefix["integrated_covered_state_samples"] += int(int_cov.sum())
            prefix["integrated_residual_state_misses"] += int(residual.sum())
            prefix["next_integrated_gain_state_samples"] += len(next_gain_ang)
            positive_counts.append(int(met["truth_positive_candidate_regions"]))
            for k, v in met["captured_misses_by_positive_region_area"].items():
                area[k] += int(v)
            ni = met["historical_next_gaze_center"]
            if ni is not None:
                next_ref["states"] += 1
                next_ref["center_on_candidate"] += int(bool(ni["region_candidate"]))
                next_ref["center_on_truth_positive_residual"] += int(bool(ni["current_region_truth_positive_residual"]))
                next_ref["center_on_next_integrated_gain"] += int(bool(ni["next_gain_region_positive"]))

            # Demo rasters are evaluator-only.
            hist_miss_count = np.zeros((h, w), np.uint16)
            residual_count = np.zeros((h, w), np.uint16)
            integration_gain_count = np.zeros((h, w), np.uint16)
            next_gain_count = np.zeros((h, w), np.uint16)
            for arr, dst in ((ang[hist_miss], hist_miss_count), (residual_ang, residual_count), (gain_ang, integration_gain_count), (next_gain_ang, next_gain_count)):
                a = np.asarray(arr, np.float64).reshape(-1, 2)
                if not len(a):
                    continue
                yy, xx, ok = _cells(a[:, 0], a[:, 1], y0, p0, grid_deg, h, w)
                if np.any(ok):
                    np.add.at(dst, (yy[ok], xx[ok]), 1)
            ed = out / "states" / f"global_{global_index:03d}"
            ed.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(
                ed / "truth-evaluation.npz",
                historical_miss_count=hist_miss_count,
                integration_gain_count=integration_gain_count,
                residual_miss_count=residual_count,
                next_integrated_gain_count=next_gain_count,
            )

            state_eval.append({
                "global_index": global_index,
                "instance_id": iid,
                "object_name": name,
                "local_step": local_step,
                "is_target_final": bool(local_step + 1 == nfix),
                "reachable_samples": int(len(ref)),
                "historical_covered_samples": int(hist_cov.sum()),
                "historical_missed_samples": int(hist_miss.sum()),
                "cross_target_integration_gain_samples": int(cross_gain.sum()),
                "own_target_retention_gain_samples": int(own_retention_gain.sum()),
                "integration_gain_samples": int(integration_gain.sum()),
                "integrated_covered_samples": int(int_cov.sum()),
                "integrated_residual_misses": int(residual.sum()),
                "next_integrated_gain_samples": int(len(next_gain_ang)),
                "integrated": met,
            })

            if local_step + 1 == nfix:
                final["reachable"] += len(ref)
                final["historical_covered"] += int(hist_cov.sum())
                final["historical_missed"] += int(hist_miss.sum())
                final["cross_target_integration_gain"] += int(cross_gain.sum())
                final["own_target_retention_gain"] += int(own_retention_gain.sum())
                final["integration_gain"] += int(integration_gain.sum())
                final["integrated_covered"] += int(int_cov.sum())
                final["integrated_residual"] += int(residual.sum())
            global_index += 1

    if historical_parity != len(p7_states):
        raise RuntimeError(f"Phase-7 state parity incomplete: {historical_parity}/{len(p7_states)}")
    p7_prefix = p7_summary["prefix_totals"]
    if int(prefix["historical_missed_state_samples"]) != int(p7_prefix["missed_state_samples"]):
        raise RuntimeError("Phase-8 historical prefix miss total differs from Phase 7")
    if int(prefix["historical_covered_state_samples"]) != int(p7_prefix["covered_state_samples"]):
        raise RuntimeError("Phase-8 historical prefix covered total differs from Phase 7")
    if strict_golden:
        hist_final = (int(final["reachable"]), int(final["historical_covered"]), int(final["historical_missed"]))
        if hist_final != (29288, 25618, 3670):
            raise RuntimeError(f"accepted golden final totals changed: {hist_final}")

    total_residual = int(prefix["integrated_residual_state_misses"])
    captured = int(sum(int(s["integrated"]["candidate_captured_missed_samples"]) for s in state_eval))
    integrated_summary = {
        "candidate_captured_residual_state_misses": captured,
        "candidate_recall_on_residual_state_misses": None if total_residual == 0 else float(captured / total_residual),
        "truth_positive_candidate_regions_total": int(sum(positive_counts)),
        "states_with_0_positive_candidates": int(sum(v == 0 for v in positive_counts)),
        "states_with_1_positive_candidate": int(sum(v == 1 for v in positive_counts)),
        "states_with_2plus_positive_candidates": int(sum(v >= 2 for v in positive_counts)),
        "captured_residual_misses_by_positive_region_area": {k: int(area[k]) for k in ("le_05", "05_15", "15_50", "gt_50")},
        "target_evidence_unmapped_residual_misses": int(sum(int(s["integrated"]["target_evidence_unmapped_residual_misses"]) for s in state_eval)),
        "target_support_residual_misses": int(sum(int(s["integrated"]["target_support_residual_misses"]) for s in state_eval)),
        "historical_next_gaze_center": {k: int(v) for k, v in sorted(next_ref.items())},
    }

    _write_json(out / "state-evaluation.json", state_eval)
    _write_json(out / "region-evaluation.json", region_eval)
    summary = {
        "schema": "PartitionGraph8-target-integration-evaluation-v1",
        "source_run": str(source),
        "proposal_dir": str(prop),
        "phase7_evaluation_dir": str(p7e),
        "offline_truth_evaluation_only": True,
        "proposal_tree_truth_free": True,
        "gaze_policy_defined": False,
        "candidate_ranking_defined": False,
        "state_count": len(state_eval),
        "target_count": len(manifest["objects"]),
        "phase7_historical_state_parity": historical_parity,
        "prefix_totals": {k: int(v) for k, v in sorted(prefix.items())},
        "final_prefix_totals": {k: int(v) for k, v in sorted(final.items())},
        "integrated": integrated_summary,
        "truth_read_paths": sorted(set(truth_reads)),
        "interpretation": (
            "offline evaluation of a truth-free shadow integration of already measured target geometry; "
            "integration gain is not a gaze-policy result"
        ),
    }
    _write_json(out / "summary.json", summary)
    return summary
