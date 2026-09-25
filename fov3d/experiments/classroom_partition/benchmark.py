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

from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any
import json
import math

import cv2
import numpy as np

from fov3d.experiments.classroom_partition.lift import _cells, _grid


REGION_KIND = {
    "TARGET_SUPPORT": 1,
    "OTHER_SURFACE": 2,
    "UNKNOWN": 3,
    "AMBIGUOUS_BOUNDARY": 4,
    "TARGET_EVIDENCE_UNMAPPED": 5,
}
REGION_KIND_BY_CODE = {v: k for k, v in REGION_KIND.items()}
CANDIDATE_KINDS = {"OTHER_SURFACE", "UNKNOWN"}
FUSION_RADIUS_M = 0.012


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


def _component_labels(mask: np.ndarray, connectivity: int) -> tuple[int, np.ndarray]:
    m = np.asarray(mask, np.uint8)
    n, labs = cv2.connectedComponents(m, connectivity=connectivity)
    return int(n), labs.astype(np.int32)


def _distance_to_target(target_support: np.ndarray, grid_deg: float) -> np.ndarray:
    target = np.asarray(target_support, bool)
    if not target.any():
        return np.full(target.shape, np.inf, np.float32)
    # cv2.distanceTransform measures non-zero pixels to the nearest zero pixel.
    d = cv2.distanceTransform((~target).astype(np.uint8), cv2.DIST_L2, 5)
    return (d * float(grid_deg)).astype(np.float32)


def _touches_edge(mask: np.ndarray) -> bool:
    m = np.asarray(mask, bool)
    if not m.any():
        return False
    return bool(m[0].any() or m[-1].any() or m[:, 0].any() or m[:, -1].any())


def _centroid_angles(mask: np.ndarray, domain: dict[str, Any], grid_deg: float) -> tuple[float, float]:
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return float("nan"), float("nan")
    y0, _y1, p0, _p1, _h, _w = _grid(domain, grid_deg)
    return float(y0 + xs.mean() * grid_deg), float(p0 + ys.mean() * grid_deg)


def _angular_distance_deg(a: tuple[float, float], b: tuple[float, float]) -> float:
    ay, ap = map(math.radians, a)
    by, bp = map(math.radians, b)
    ua = np.array([math.sin(ay) * math.cos(ap), math.sin(ap), -math.cos(ay) * math.cos(ap)])
    ub = np.array([math.sin(by) * math.cos(bp), math.sin(bp), -math.cos(by) * math.cos(bp)])
    return float(math.degrees(math.acos(float(np.clip(np.dot(ua, ub), -1.0, 1.0)))))


def _region_interfaces(region_code: np.ndarray) -> tuple[list[dict[str, Any]], dict[int, dict[int, int]]]:
    rc = np.asarray(region_code, np.int32)
    pairs: Counter[tuple[int, int]] = Counter()
    left = rc[:, :-1]
    right = rc[:, 1:]
    ys, xs = np.nonzero(left != right)
    for y, x in zip(ys.tolist(), xs.tolist()):
        a, b = int(left[y, x]), int(right[y, x])
        if a and b:
            pairs[tuple(sorted((a, b)))] += 1
    top = rc[:-1, :]
    bottom = rc[1:, :]
    ys, xs = np.nonzero(top != bottom)
    for y, x in zip(ys.tolist(), xs.tolist()):
        a, b = int(top[y, x]), int(bottom[y, x])
        if a and b:
            pairs[tuple(sorted((a, b)))] += 1
    edges = [
        {"region_code_a": int(a), "region_code_b": int(b), "interface_edge_count": int(n)}
        for (a, b), n in sorted(pairs.items())
    ]
    adjacency: dict[int, dict[int, int]] = defaultdict(dict)
    for (a, b), n in pairs.items():
        adjacency[a][b] = int(n)
        adjacency[b][a] = int(n)
    return edges, adjacency


def build_epistemic_partition(
    state: dict[str, np.ndarray],
    *,
    target_id: int,
    target_name: str,
    all_target_ids: set[int],
    domain: dict[str, Any],
    grid_deg: float,
    gazes_deg: list[tuple[float, float]],
) -> tuple[dict[str, np.ndarray], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Build a truth-free causal evidence partition for one target-final state.

    Precedence is intentionally representation-first:
      target own support > ambiguous instance boundary > mapped/incidental other
      surface > unmapped target evidence > no head-centred depth.

    Unknown territory is therefore defined in the same head-origin chart as the
    persistent object support.  Historical eye-ray ``seen_any`` is retained only
    as an attribute; it does not define region identity.
    """
    target_support = np.asarray(state["target_support"], bool)
    owner = np.asarray(state["owner_instance"], np.int32)
    nearest = np.asarray(state["nearest_instance"], np.int32)
    ambiguous = np.asarray(state["ambiguous_instance"], bool)
    depth_seen = np.asarray(state["depth_seen"], bool)
    seen_any = np.asarray(state["seen_any"], bool)
    if not (target_support.shape == owner.shape == nearest.shape == ambiguous.shape == depth_seen.shape == seen_any.shape):
        raise ValueError("Phase-5 state rasters do not share one chart shape")

    mapped_other = (~target_support) & (owner > 0) & (owner != int(target_id))
    incidental_other = (~target_support) & (~mapped_other) & (nearest > 0) & (nearest != int(target_id))
    target_unmapped = (~target_support) & (nearest == int(target_id))
    ambiguous_boundary = (~target_support) & ambiguous
    other_surface = (~ambiguous_boundary) & (mapped_other | incidental_other)
    target_unmapped &= ~ambiguous_boundary & ~other_surface
    unknown = ~(target_support | ambiguous_boundary | other_surface | target_unmapped)

    class_code = np.zeros(target_support.shape, np.uint8)
    class_code[target_support] = REGION_KIND["TARGET_SUPPORT"]
    class_code[other_surface] = REGION_KIND["OTHER_SURFACE"]
    class_code[unknown] = REGION_KIND["UNKNOWN"]
    class_code[ambiguous_boundary] = REGION_KIND["AMBIGUOUS_BOUNDARY"]
    class_code[target_unmapped] = REGION_KIND["TARGET_EVIDENCE_UNMAPPED"]
    if np.any(class_code == 0):
        raise RuntimeError("epistemic partition left unclassified cells")

    surface_instance = np.zeros(owner.shape, np.int32)
    surface_instance[mapped_other] = owner[mapped_other]
    take_inc = incidental_other & ~mapped_other
    surface_instance[take_inc] = nearest[take_inc]

    region_code = np.zeros(owner.shape, np.int32)
    region_rows: list[dict[str, Any]] = []
    next_code = 1
    distance_deg = _distance_to_target(target_support, grid_deg)

    def add_components(kind: str, mask: np.ndarray, connectivity: int, instance_id: int | None = None) -> None:
        nonlocal next_code
        n, labs = _component_labels(mask, connectivity)
        for lab in range(1, n):
            m = labs == lab
            if not m.any():
                continue
            code = next_code
            next_code += 1
            region_code[m] = code
            cyaw, cpitch = _centroid_angles(m, domain, grid_deg)
            dvals = distance_deg[m]
            finite_d = dvals[np.isfinite(dvals)]
            gaze_dist = [
                _angular_distance_deg((cyaw, cpitch), (float(y), float(p)))
                for y, p in gazes_deg
            ] if gazes_deg and np.isfinite(cyaw) and np.isfinite(cpitch) else []
            mapped_n = int((mapped_other & m).sum())
            incidental_n = int((incidental_other & m).sum())
            row: dict[str, Any] = {
                "region_code": int(code),
                "region_id": f"{kind.lower()}:{code:04d}",
                "kind": kind,
                "candidate": bool(kind in CANDIDATE_KINDS),
                "instance_id": None if instance_id is None else int(instance_id),
                "cell_count": int(m.sum()),
                "touches_domain_edge": _touches_edge(m),
                "centroid_yaw_deg": cyaw,
                "centroid_pitch_deg": cpitch,
                "min_distance_to_target_deg": None if not len(finite_d) else float(np.min(finite_d)),
                "median_distance_to_target_deg": None if not len(finite_d) else float(np.median(finite_d)),
                "min_distance_to_historical_gaze_deg": None if not gaze_dist else float(min(gaze_dist)),
                "seen_any_fraction": float(seen_any[m].mean()),
                "head_depth_fraction": float(depth_seen[m].mean()),
                "mapped_cells": mapped_n,
                "incidental_cells": incidental_n,
            }
            if kind == "OTHER_SURFACE" and instance_id is not None:
                if mapped_n and incidental_n:
                    source = "mapped_and_incidental"
                elif mapped_n:
                    source = "mapped"
                elif incidental_n:
                    source = "incidental"
                else:
                    source = "unknown"
                row["surface_source"] = source
                row["reconstruction_status"] = (
                    "mapped_now" if mapped_n
                    else "targeted_later" if int(instance_id) in all_target_ids
                    else "never_targeted"
                )
            region_rows.append(row)

    # Target support remains its own-support topology (8-connected).
    add_components("TARGET_SUPPORT", target_support, 8, int(target_id))

    # Keep distinct non-target identities separate, including incidental-only ones.
    for iid in sorted(int(v) for v in np.unique(surface_instance) if int(v) > 0):
        add_components("OTHER_SURFACE", other_surface & (surface_instance == iid), 8, iid)

    # Complement-like classes use 4-connectivity as digital duals to 8-connected surfaces.
    add_components("UNKNOWN", unknown, 4, None)
    add_components("AMBIGUOUS_BOUNDARY", ambiguous_boundary, 4, None)
    add_components("TARGET_EVIDENCE_UNMAPPED", target_unmapped, 8, int(target_id))

    if np.any(region_code == 0):
        raise RuntimeError("epistemic region labelling left cells without region codes")

    edge_rows, adjacency = _region_interfaces(region_code)
    by_code = {int(r["region_code"]): r for r in region_rows}
    for code, row in by_code.items():
        row["adjacent_regions"] = [
            {"region_code": int(n), "region_id": by_code[n]["region_id"], "interface_edge_count": int(c)}
            for n, c in sorted(adjacency.get(code, {}).items())
        ]
        row["adjacent_to_target_support"] = any(
            by_code[n]["kind"] == "TARGET_SUPPORT" for n in adjacency.get(code, {})
        )

    diag = {
        "target_id": int(target_id),
        "target_name": str(target_name),
        "chart_shape_hw": [int(v) for v in target_support.shape],
        "region_count": len(region_rows),
        "candidate_region_count": sum(bool(r["candidate"]) for r in region_rows),
        "kind_region_counts": dict(sorted(Counter(r["kind"] for r in region_rows).items())),
        "kind_cell_counts": {
            name: int((class_code == code).sum()) for name, code in REGION_KIND.items()
        },
        "target_evidence_unmapped_cells": int(target_unmapped.sum()),
        "ambiguous_boundary_cells": int(ambiguous_boundary.sum()),
        "head_depth_cells": int(depth_seen.sum()),
        "eye_ray_seen_cells": int(seen_any.sum()),
        "truth_used": False,
    }
    arrays = {
        "class_code": class_code,
        "region_code": region_code,
        "surface_instance": surface_instance,
        "target_support": target_support,
        "depth_seen": depth_seen,
        "seen_any": seen_any,
        "mapped_other": mapped_other,
        "incidental_other": incidental_other,
        "ambiguous_boundary": ambiguous_boundary,
    }
    return arrays, region_rows, edge_rows, diag


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

    y0, _y1, p0, _p1, h, w = _grid(domain, grid_deg)
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
        cov = _covered(ref, sm, FUSION_RADIUS_M)
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
        yy, xx, ok = _cells(missed_ang[:, 0] if len(missed_ang) else np.empty(0),
                            missed_ang[:, 1] if len(missed_ang) else np.empty(0),
                            y0, p0, grid_deg, h, w)
        miss_codes = np.zeros(len(missed_ang), np.int32)
        miss_codes[ok] = region_code[yy[ok], xx[ok]]
        miss_by_code = Counter(int(v) for v in miss_codes.tolist() if int(v) > 0)

        # All dense first-hit samples provide a denominator for evaluator-only
        # region purity/precision diagnostics.
        ayy, axx, aok = _cells(truth_angles[:, 0], truth_angles[:, 1], y0, p0, grid_deg, h, w)
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
