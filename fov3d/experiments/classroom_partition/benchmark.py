"""Partition-Graph Phase 6: causal epistemic-region proposals and truth-only benchmark.

The module deliberately separates two stages:

* ``propose_phase6`` is controller-time / truth-free.  It turns the causal-final
  Phase-5 head-centred evidence state for each target into an epistemic region
  partition and emits *all* candidate regions without ranking them.
* ``evaluate_phase6`` is offline evaluation.  It is the only Phase-6 function
  allowed to open dense reachable-surface truth, and it writes to a separate
  output tree.

No gaze, controller, matcher, fusion, renderer, or scene process is executed.
Object identity remains inherited from Classroom-Oracle-1.
"""
from __future__ import annotations

from collections import Counter, deque
from pathlib import Path
from typing import Any
import json

import numpy as np

from fov3d.epistemic.partition import (
    CANDIDATE_KINDS,
    REGION_KIND,
    REGION_KIND_BY_CODE,
    _angular_distance_deg,
    _centroid_angles,
    _component_labels,
    _distance_to_target,
    _region_interfaces,
    _touches_edge,
    build_epistemic_partition,
)
from fov3d.geometry.head_chart import chart_cells, chart_grid
from fov3d.reconstruction.association import SURFACE_ASSOCIATION_RADIUS_M


# Backward-compatible aliases for historical checks/tools. Production code imports
# the conceptual modules directly.
FUSION_RADIUS_M = SURFACE_ASSOCIATION_RADIUS_M
_cells = chart_cells
_grid = chart_grid


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _guard_source_path(root: Path, path: Path, *, truth_allowed: bool) -> str:
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
        raise RuntimeError(f"truth/renderer path forbidden to Phase-6 proposer: {rel.as_posix()}")
    return rel.as_posix()


def propose_phase6(
    source_run: str | Path,
    lift_dir: str | Path,
    phase5_dir: str | Path,
    out_dir: str | Path,
    *,
    grid_deg: float = 0.10,
) -> dict[str, Any]:
    """Emit causal-final epistemic region proposals without opening dense truth."""
    source = Path(source_run).resolve()
    lift = Path(lift_dir).resolve()
    p5 = Path(phase5_dir).resolve()
    out = Path(out_dir).resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"Phase-6 proposal output must be new or empty: {out}")
    out.mkdir(parents=True, exist_ok=True)

    reads: list[str] = []
    mp = source / "manifest.json"
    reads.append(_guard_source_path(source, mp, truth_allowed=False))
    manifest = _json(mp)
    sp = source / "bootstrap" / "seeds.json"
    reads.append(_guard_source_path(source, sp, truth_allowed=False))
    seeds = _json(sp)
    if not manifest.get("control_complete"):
        raise RuntimeError("source run is not control_complete")
    domain = seeds["controller_domain_deg"]
    if abs(float(grid_deg) - 0.10) > 1e-12:
        raise ValueError("Phase 6 uses the frozen 0.10-degree chart")

    lift_summary = _json(lift / "summary.json")
    p5_summary = _json(p5 / "summary.json")
    if int(p5_summary.get("head_target_depth_true_gap_violations", -1)) != 0:
        raise RuntimeError("Phase-5 head-centred invariant is not clean")
    final_state = {int(k): int(v) for k, v in lift_summary["final_state_for_object"].items()}
    all_target_ids = {int(o["instance_id"]) for o in manifest["objects"]}
    by_id = {int(o["instance_id"]): o for o in manifest["objects"]}

    candidate_rows: list[dict[str, Any]] = []
    target_rows: list[dict[str, Any]] = []
    for iid in sorted(final_state):
        obj = by_id[iid]
        gi = int(final_state[iid])
        st_path = p5 / "states" / f"global_{gi:03d}" / "head-evidence.npz"
        with np.load(st_path, allow_pickle=False) as z:
            state = {k: np.array(z[k]) for k in z.files}
        gazes = [tuple(map(float, r["gaze_deg"])) for r in obj.get("trajectory", []) if "gaze_deg" in r]
        arrays, regions, edges, diag = build_epistemic_partition(
            state,
            target_id=iid,
            target_name=str(obj["object_name"]),
            all_target_ids=all_target_ids,
            domain=domain,
            grid_deg=grid_deg,
            gazes_deg=gazes,
        )
        td = out / "targets" / f"instance_{iid:04d}"
        td.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(td / "partition.npz", **arrays)
        _write_json(td / "regions.json", regions)
        _write_json(td / "edges.json", edges)
        diag.update({
            "global_index": gi,
            "local_final_step": int(obj["fixation_count"]) - 1,
            "fixation_count": int(obj["fixation_count"]),
            "termination": str(obj["termination"]),
        })
        _write_json(td / "summary.json", diag)
        target_rows.append(diag)
        for r in regions:
            if r["candidate"]:
                rr = dict(r)
                rr.update({
                    "instance_id_target": iid,
                    "object_name_target": str(obj["object_name"]),
                    "global_index": gi,
                })
                candidate_rows.append(rr)

    _write_json(out / "candidate-regions.json", candidate_rows)
    summary = {
        "schema": "PartitionGraph6-causal-epistemic-regions-v1",
        "source_run": str(source),
        "lift_dir": str(lift),
        "phase5_dir": str(p5),
        "posthoc_representation_only": True,
        "truth_used": False,
        "controller_executed": False,
        "gaze_policy_defined": False,
        "object_identity_inherited": True,
        "grid_deg": float(grid_deg),
        "targets": target_rows,
        "target_count": len(target_rows),
        "candidate_region_count": len(candidate_rows),
        "candidate_kind_counts": dict(sorted(Counter(r["kind"] for r in candidate_rows).items())),
        "source_read_paths": sorted(set(reads)),
        "forbidden_read_paths": [],
    }
    _write_json(out / "summary.json", summary)
    return summary


def _covered(reference: np.ndarray, surfels: np.ndarray, radius: float) -> np.ndarray:
    """Exact 12-mm coverage, intentionally matching the sealed offline evaluator."""
    ref = np.asarray(reference, np.float64)
    pts = np.asarray(surfels, np.float64)
    out = np.zeros(len(ref), bool)
    if not len(ref) or not len(pts):
        return out
    cell = float(radius)
    q = np.floor(pts / cell).astype(np.int64)
    table: dict[tuple[int, int, int], list[int]] = {}
    for i, c in enumerate(q):
        table.setdefault(tuple(map(int, c)), []).append(i)
    qr = np.floor(ref / cell).astype(np.int64)
    r2 = radius * radius
    for i, c in enumerate(qr):
        ids: list[int] = []
        cx, cy, cz = map(int, c)
        for dz in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ids.extend(table.get((cx + dx, cy + dy, cz + dz), ()))
        if ids:
            d = pts[np.asarray(ids)] - ref[i]
            out[i] = bool(np.any(np.einsum("ij,ij->i", d, d) <= r2))
    return out


def _miss_components(yaw_pitch_deg: np.ndarray, step_deg: float = 0.25) -> list[list[int]]:
    a = np.asarray(yaw_pitch_deg, np.float64).reshape(-1, 2)
    if not len(a):
        return []
    keys = np.rint(a / float(step_deg)).astype(np.int64)
    lookup = {tuple(map(int, k)): i for i, k in enumerate(keys)}
    unseen = set(range(len(a)))
    comps: list[list[int]] = []
    nbr = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)]
    while unseen:
        seed = min(unseen)
        unseen.remove(seed)
        q = deque([seed])
        comp = [seed]
        while q:
            i = q.popleft()
            y, x = map(int, keys[i])
            for dy, dx in nbr:
                j = lookup.get((y + dy, x + dx))
                if j is not None and j in unseen:
                    unseen.remove(j)
                    q.append(j)
                    comp.append(j)
        comps.append(sorted(comp))
    return comps


def evaluate_phase6(
    source_run: str | Path,
    proposal_dir: str | Path,
    out_dir: str | Path,
    *,
    grid_deg: float = 0.10,
    strict_golden: bool = True,
) -> dict[str, Any]:
    """Evaluate truth-free Phase-6 proposals against dense truth offline.

    This function is intentionally separate from proposal construction.  Truth is
    never copied into the proposal tree and no candidate is ranked by evaluation.
    """
    source = Path(source_run).resolve()
    prop = Path(proposal_dir).resolve()
    out = Path(out_dir).resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"Phase-6 evaluation output must be new or empty: {out}")
    out.mkdir(parents=True, exist_ok=True)

    truth_reads: list[str] = []
    mp = source / "manifest.json"
    truth_reads.append(_guard_source_path(source, mp, truth_allowed=True))
    manifest = _json(mp)
    sp = source / "bootstrap" / "seeds.json"
    truth_reads.append(_guard_source_path(source, sp, truth_allowed=True))
    seeds = _json(sp)
    domain = seeds["controller_domain_deg"]
    tp = source / "bootstrap" / "evaluation_only" / "reachable_samples.npz"
    truth_reads.append(_guard_source_path(source, tp, truth_allowed=True))
    with np.load(tp, allow_pickle=False) as z:
        truth_ids = np.asarray(z["instance_id"], np.int32)
        truth_xyz = np.asarray(z["xyz_h"], np.float64)
        truth_angles = np.asarray(z["yaw_pitch_deg"], np.float64)
    if len(truth_ids) != len(truth_xyz) or len(truth_ids) != len(truth_angles):
        raise ValueError("dense truth arrays disagree")

    prop_summary = _json(prop / "summary.json")
    if prop_summary.get("truth_used") is not False:
        raise RuntimeError("proposal tree is not marked truth-free")
    if int(prop_summary.get("target_count", -1)) != len(manifest["objects"]):
        raise RuntimeError("proposal/source target-count mismatch")

    y0, _y1, p0, _p1, h, w = chart_grid(domain, grid_deg)
    run_by_id = {int(o["instance_id"]): o for o in manifest["objects"]}
    region_eval_rows: list[dict[str, Any]] = []
    target_rows: list[dict[str, Any]] = []
    component_rows: list[dict[str, Any]] = []
    total_ref = total_cov = total_miss = 0
    total_candidate_capture = 0

    for iid in sorted(int(v) for v in np.unique(truth_ids) if int(v) > 0):
        if iid not in run_by_id:
            continue
        obj = run_by_id[iid]
        ref_mask = truth_ids == iid
        ref = truth_xyz[ref_mask]
        ang = truth_angles[ref_mask]
        map_path = source / "objects" / f"instance_{iid:04d}" / "final_map.npz"
        truth_reads.append(_guard_source_path(source, map_path, truth_allowed=True))
        with np.load(map_path, allow_pickle=False) as z:
            sm = np.asarray(z["xyz_h"], np.float64)
        sm = sm[np.isfinite(sm).all(axis=1)]
        cov = _covered(ref, sm, SURFACE_ASSOCIATION_RADIUS_M)
        missed_ang = ang[~cov]
        nref, ncov, nmiss = int(len(ref)), int(cov.sum()), int((~cov).sum())
        total_ref += nref
        total_cov += ncov
        total_miss += nmiss

        td = prop / "targets" / f"instance_{iid:04d}"
        regions = _json(td / "regions.json")
        by_code = {int(r["region_code"]): r for r in regions}
        with np.load(td / "partition.npz", allow_pickle=False) as z:
            region_code = np.asarray(z["region_code"], np.int32)
        yy, xx, ok = chart_cells(missed_ang[:, 0] if len(missed_ang) else np.empty(0),
                            missed_ang[:, 1] if len(missed_ang) else np.empty(0),
                            y0, p0, grid_deg, h, w)
        miss_codes = np.zeros(len(missed_ang), np.int32)
        miss_codes[ok] = region_code[yy[ok], xx[ok]]
        miss_by_code = Counter(int(v) for v in miss_codes.tolist() if int(v) > 0)

        # All dense first-hit samples provide a denominator for evaluator-only
        # region purity/precision diagnostics.
        ayy, axx, aok = chart_cells(truth_angles[:, 0], truth_angles[:, 1], y0, p0, grid_deg, h, w)
        all_codes = np.zeros(len(truth_angles), np.int32)
        all_codes[aok] = region_code[ayy[aok], axx[aok]]
        all_by_code = Counter(int(v) for v in all_codes.tolist() if int(v) > 0)
        target_truth_by_code = Counter(int(v) for v in all_codes[truth_ids == iid].tolist() if int(v) > 0)

        kind_misses: Counter[str] = Counter()
        candidate_captured = 0
        positive_candidate_regions = 0
        for r in regions:
            code = int(r["region_code"])
            nm = int(miss_by_code.get(code, 0))
            nt = int(all_by_code.get(code, 0))
            ntt = int(target_truth_by_code.get(code, 0))
            kind = str(r["kind"])
            kind_misses[kind] += nm
            if r.get("candidate"):
                candidate_captured += nm
                positive_candidate_regions += int(nm > 0)
            region_eval_rows.append({
                "instance_id_target": iid,
                "object_name_target": str(obj["object_name"]),
                "region_code": code,
                "region_id": r["region_id"],
                "kind": kind,
                "candidate": bool(r.get("candidate")),
                "region_cell_count": int(r["cell_count"]),
                "dense_first_hit_samples_in_region": nt,
                "target_truth_samples_in_region": ntt,
                "missed_target_samples_in_region": nm,
                "truth_positive": bool(nm > 0),
                "target_miss_fraction_of_dense_samples": None if nt == 0 else float(nm / nt),
            })
        total_candidate_capture += candidate_captured

        comps = _miss_components(missed_ang, 0.25)
        for ci, ids in enumerate(comps):
            codes = Counter(int(miss_codes[j]) for j in ids if int(miss_codes[j]) > 0)
            kinds = Counter(by_code[c]["kind"] for c in codes if c in by_code)
            component_rows.append({
                "instance_id_target": iid,
                "object_name_target": str(obj["object_name"]),
                "component_index": ci,
                "missed_sample_count": len(ids),
                "yaw_span_deg": [float(np.min(missed_ang[ids, 0])), float(np.max(missed_ang[ids, 0]))],
                "pitch_span_deg": [float(np.min(missed_ang[ids, 1])), float(np.max(missed_ang[ids, 1]))],
                "proposal_region_codes": {str(k): int(v) for k, v in sorted(codes.items())},
                "proposal_kind_counts": dict(sorted((str(k), int(v)) for k, v in kinds.items())),
            })

        target_rows.append({
            "instance_id": iid,
            "object_name": str(obj["object_name"]),
            "reachable_samples": nref,
            "covered_samples": ncov,
            "missed_samples": nmiss,
            "coverage_fraction": None if nref == 0 else float(ncov / nref),
            "missed_by_region_kind": dict(sorted((k, int(v)) for k, v in kind_misses.items())),
            "candidate_captured_missed_samples": int(candidate_captured),
            "candidate_recall": None if nmiss == 0 else float(candidate_captured / nmiss),
            "truth_positive_candidate_regions": int(positive_candidate_regions),
            "miss_component_count_025deg": len(comps),
        })

    if strict_golden:
        expected = (29288, 25618, 3670)
        actual = (total_ref, total_cov, total_miss)
        if actual != expected:
            raise RuntimeError(f"accepted golden dense totals changed: {actual} != {expected}")

    _write_json(out / "region-evaluation.json", region_eval_rows)
    _write_json(out / "miss-components.json", component_rows)
    summary = {
        "schema": "PartitionGraph6-truth-evaluation-v1",
        "source_run": str(source),
        "proposal_dir": str(prop),
        "offline_truth_evaluation_only": True,
        "proposal_tree_truth_free": True,
        "gaze_policy_defined": False,
        "reachable_samples_total": int(total_ref),
        "covered_samples_total": int(total_cov),
        "missed_samples_total": int(total_miss),
        "coverage_fraction_micro": None if total_ref == 0 else float(total_cov / total_ref),
        "candidate_captured_missed_samples": int(total_candidate_capture),
        "candidate_recall_micro": None if total_miss == 0 else float(total_candidate_capture / total_miss),
        "target_count": len(target_rows),
        "truth_positive_candidate_region_count": int(sum(r["truth_positive"] and r["candidate"] for r in region_eval_rows)),
        "miss_component_count_025deg": len(component_rows),
        "targets": target_rows,
        "truth_read_paths": sorted(set(truth_reads)),
        "interpretation": (
            "evaluation of truth-free causal region proposals only; truth-positive labels and recall are not available to a controller"
        ),
    }
    _write_json(out / "summary.json", summary)
    return summary
