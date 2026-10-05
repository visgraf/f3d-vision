"""North Star-1b: the pure functions of the handoff (host side; no file I/O, no Blender).

Contract: docs/north-star/ns1b-recentered-controller-handoff-contract.md, sections 5-15.

- the frozen target-selection rule (section 5);
- the controller context from the frozen NS1a initialization look (section 9);
- the read-only probe: the accepted ``controller01.probe_local_policy`` and ``controller02.final_look_gate_v1`` run
  unchanged under the frame adapter (section 10);
- rigid rotations of a context about the physical baseline (section 8b / the in-probe invariance);
- the H0-only fusion entry point over the accepted surface map (section 14);
- the fixed-head and fake-local-calibration tests;
- tolerance-aware decision comparison (exact where discrete; float tolerance only where unavoidable).

No object name and no catalog ever enters these functions.
"""
from __future__ import annotations

import copy
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "active_bootstrap", HERE.parent / "natural_bootstrap", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1b_chart as CH  # noqa: E402
import ns1b_spec as SP  # noqa: E402


class SelectionRefused(RuntimeError):
    """The selection input carries a name / catalog field, or a required field is missing."""


class FrameRefused(RuntimeError):
    """A persistent-map fusion was attempted in a frame other than canonical H0."""


def jsonable(x: Any) -> Any:
    from fov3d.experiments.classroom_oracle import controller01 as c01
    return c01._jsonable(x)


# ------------------------------------------------------------------ comparison (contract section 8a)
RANK_KEYS = ("predicted_new_angular_area_deg2", "frontier_score")
CANDIDATE_LISTS = ("candidates", "consensus_rejected_candidates")


def _rank_key(c: dict) -> tuple:
    return (-float(c["predicted_new_angular_area_deg2"]), -float(c["frontier_score"]),
            abs(float(c["delta_yaw_deg"])) + abs(float(c["delta_pitch_deg"])), float(c["yaw_deg"]),
            float(c["pitch_deg"]))


def _float_decided(first: dict, second: dict, tol: float) -> bool:
    """Whether the accepted sort placed ``first`` before ``second`` by a key difference within ``tol`` (a tie in exact
    arithmetic broken by floating-point noise), i.e. the first exactly-differing key differs by at most ``tol``."""
    for x, y in zip(_rank_key(first), _rank_key(second)):
        if x != y:
            return abs(x - y) <= tol * max(1.0, abs(x))
    return True


def compare(a: Any, b: Any, tol: float = SP.FLOAT_TOL, path: str = "", skip: tuple = ()) -> list[str]:
    """Differences between two JSON-like decisions: exact for discrete values, relative ``tol`` for floats.

    The candidate lists of an FSG6f decision are compared as the accepted sort defines them: the same candidates (by
    local gaze) with equal fields, in the same order except for inversions between candidates whose accepted ranking
    keys tie within ``tol`` (a floating-point tie-break, never a different candidate)."""
    if path.split("/")[-1] in skip:
        return []
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) - set(skip) != set(b) - set(skip):
            return [f"{path}: keys {sorted(set(a) ^ set(b))}"]
        out = []
        for k in sorted(a):
            if k in skip:
                continue
            if k in CANDIDATE_LISTS and isinstance(a[k], list):
                out += compare_candidates(a[k], b[k], tol, f"{path}/{k}")
            else:
                out += compare(a[k], b[k], tol, f"{path}/{k}", skip)
        return out
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in compare(x, y, tol, f"{path}[{i}]", skip)]
    if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None or isinstance(a, str):
        return [] if a == b and type(a) is type(b) else [f"{path}: {a!r} != {b!r}"]
    if isinstance(a, int) and isinstance(b, int):
        return [] if a == b else [f"{path}: {a} != {b}"]
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        fa, fb = float(a), float(b)
        if math.isnan(fa) and math.isnan(fb):
            return []
        return [] if abs(fa - fb) <= tol * max(1.0, abs(fa)) else [f"{path}: {fa!r} != {fb!r}"]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


def compare_candidates(a: list, b: list, tol: float, path: str) -> list[str]:
    if len(a) != len(b):
        return [f"{path}: {len(a)} != {len(b)} candidates"]
    key = lambda c: (round(float(c["yaw_deg"]), 9), round(float(c["pitch_deg"]), 9))  # noqa: E731
    ia, ib = {key(c): i for i, c in enumerate(a)}, {key(c): i for i, c in enumerate(b)}
    if set(ia) != set(ib):
        return [f"{path}: candidate sets differ {sorted(set(ia) ^ set(ib))}"]
    out = []
    for k, i in ia.items():
        out += compare(a[i], b[ib[k]], tol, f"{path}{list(k)}")
    order_b = [ib[key(c)] for c in a]
    for i in range(len(a)):
        for j in range(i + 1, len(a)):
            if order_b[i] > order_b[j] and not (_float_decided(a[i], a[j], tol)
                                                or _float_decided(b[order_b[j]], b[order_b[i]], tol)):
                out.append(f"{path}: order of {list(key(a[i]))} and {list(key(a[j]))} differs without a ranking tie")
    return out


VOXEL_COUNT_PATH = "/frontier_voxel_count"


def voxel_boundary_points(xyz_c: np.ndarray, cell: float = 0.025, eps: float = 1e-12) -> int:
    """Map points whose chart coordinates lie within ``eps`` of a 25-mm voxel boundary of the accepted FSG6a grid."""
    p = np.asarray(xyz_c, np.float64).reshape(-1, 3) / cell
    return int((np.abs(p - np.rint(p)) <= eps / cell).any(axis=1).sum())


def explain_voxel_flip(diffs: list[str], xyz_c: np.ndarray) -> tuple[list[str], dict | None]:
    """A difference confined to the frontier voxel COUNT, with map points exactly on a voxel boundary, is the accepted
    voxelizer's discontinuity under round-off (recorded, not an adapter difference); anything else stays a difference."""
    if diffs and all(d.split(":")[0].endswith(VOXEL_COUNT_PATH) for d in diffs):
        n = voxel_boundary_points(xyz_c)
        if n > 0:
            return [], {"explained": diffs, "map_points_on_voxel_boundaries": n}
    return diffs, None


def inversions(a: list, b: list) -> list[list]:
    """The candidate pairs whose order differs (recorded when a tolerance tie allowed it)."""
    key = lambda c: (round(float(c["yaw_deg"]), 9), round(float(c["pitch_deg"]), 9))  # noqa: E731
    ib = {key(c): i for i, c in enumerate(b)}
    order_b = [ib.get(key(c), -1) for c in a]
    return [[list(key(a[i])), list(key(a[j]))] for i in range(len(a)) for j in range(i + 1, len(a))
            if order_b[i] > order_b[j]]


# ------------------------------------------------------------------ section 5: target selection
def _is_name_key(k: Any) -> bool:
    """A key that would carry an object name or a catalog (descriptive text such as 'non-catalog' is not one)."""
    k = str(k).lower()
    return (k in ("name", "names", "object_name", "object_names", "instance_catalog") or k.endswith(("_name", "_names"))
            or k.startswith("catalog"))


def _has_name(x: Any) -> bool:
    if isinstance(x, dict):
        return any(_is_name_key(k) or _has_name(v) for k, v in x.items())
    if isinstance(x, list):
        return any(_has_name(v) for v in x)
    return False


def rank_gazes(gaze_list: dict) -> dict[int, tuple[float, float]]:
    got = {int(g["rank"]): (float(g["yaw_deg"]), float(g["pitch_deg"])) for g in gaze_list["gazes"]}
    want = {r: (y, p) for r, y, p in SP.NS1A_RANK_GAZES}
    if got != want:
        raise SelectionRefused(f"the NS1a gaze provenance differs from the frozen six: {got}")
    return got


def select_target(seed_set: dict, gaze_list: dict) -> dict:
    """The frozen rule: initialized AND contributing_patches == 1; max L at the initialization gaze; then surfels; then id.

    Reads only ``SP.SELECTION_FIELDS`` of each entity record; any name / catalog field anywhere in the input is
    refused (no name or catalog may reach the selection)."""
    if _has_name(seed_set) or _has_name(gaze_list):
        raise SelectionRefused("a name or catalog field reached the target selection")
    gazes = rank_gazes(gaze_list)
    rows, excluded = [], []
    for e in seed_set["entities"]:
        missing = [f for f in SP.SELECTION_FIELDS if f not in e]
        if missing:
            raise SelectionRefused(f"entity record lacks {missing}")
        k = int(e["temporary_entity_id"])
        if not bool(e["initialized"]):
            excluded.append({"temporary_entity_id": k, "reason": "not initialized"})
            continue
        if int(e["contributing_patches"]) != 1:
            excluded.append({"temporary_entity_id": k, "reason": f"{int(e['contributing_patches'])} contributing patches"})
            continue
        r = int(e["initialized_at_rank"])
        y, p = gazes[r]
        g = CH.gaze_direction(y, p)
        bg = float(np.dot(CH.B_H0, g))
        rows.append({"temporary_entity_id": k, "initialized_at_rank": r, "initialization_gaze_deg": [y, p],
                     "g_H0": g.tolist(), "b_dot_g": bg, "leverage": math.sqrt(max(0.0, 1.0 - bg * bg)),
                     "final_surfels": int(e["final_surfels"]), "contributing_patches": int(e["contributing_patches"])})
    if not rows:
        raise SelectionRefused("no initialized single-patch entity")
    order = sorted(rows, key=lambda r: (-r["leverage"], -r["final_surfels"], r["temporary_entity_id"]))
    best, second = order[0], (order[1] if len(order) > 1 else None)
    if second is None or best["leverage"] != second["leverage"]:
        decided_by = "leverage"
    elif best["final_surfels"] != second["final_surfels"]:
        decided_by = "final_surfels"
    else:
        decided_by = "temporary_entity_id"
    return {"rule": "initialized AND contributing_patches == 1; max L = sqrt(1 - (b.g)^2) at the initialization gaze "
                    "(b = +X in H0); then max final_surfels; then lowest temporary_entity_id",
            "fields_read": list(SP.SELECTION_FIELDS), "candidates": order, "excluded": excluded,
            "selected": best["temporary_entity_id"], "selected_rank": best["initialized_at_rank"],
            "selected_gaze_deg": best["initialization_gaze_deg"], "selected_leverage": best["leverage"],
            "decided_by": decided_by,
            "leverage_tied_with": [r["temporary_entity_id"] for r in order[1:] if r["leverage"] == best["leverage"]]}


# ------------------------------------------------------------------ maps
def load_surface_map(maps: dict, entity: int):
    """The accepted SurfaceMap of one entity from the NS1a ``entity-maps.npz`` arrays (exact values)."""
    from fov3d.reconstruction import surface_map as SM
    f = {k: np.asarray(maps[SP.map_key(entity, k)]) for k in SP.MAP_FIELDS}
    return SM.SurfaceMap(np.asarray(f["xyz_h"], np.float64).copy(), np.asarray(f["rgb"], np.float64).copy(),
                         f["instance_id"].copy(), f["support_count"].copy(), f["provenance_mask"].copy(),
                         [str(p) for p in f["patch_ids"]])


def map_arrays(m) -> dict:
    return {"xyz_h": np.asarray(m.xyz_h, np.float64), "rgb": np.asarray(m.rgb, np.float64),
            "instance_id": np.asarray(m.instance_id), "support_count": np.asarray(m.support_count),
            "provenance_mask": np.asarray(m.provenance_mask), "patch_ids": np.array(list(m.patch_ids), dtype="U64")}


def maps_equal(a: dict, b: dict) -> bool:
    return set(a) == set(b) and all(np.asarray(a[k]).dtype == np.asarray(b[k]).dtype
                                    and np.array_equal(np.asarray(a[k]), np.asarray(b[k])) for k in a)


# ------------------------------------------------------------------ section 9: the controller context
def matcher_state(calibration: dict, rgb: dict, reference: dict):
    """The accepted Classroom perfect local matcher on one saved look (controller observation state only)."""
    from fov3d.experiments.classroom_oracle import matcher
    obs = {"rgb_L": rgb["rgb_L"], "rgb_R": rgb["rgb_R"], "instance_L": reference["instance_L"],
           "instance_R": reference["instance_R"], "position_w_L": reference["position_w_L"],
           "position_w_R": reference["position_w_R"]}
    rec, meta, st = matcher.compute(calibration, obs)
    return rec, meta, st


def build_context(entity: int, calibration: dict, state: dict, valid: np.ndarray, r_hc: np.ndarray,
                  local_gaze: tuple[float, float] = (0.0, 0.0)):
    """The accepted LocalPolicyContext with one completed own look, in Controller-01's ``observe`` order."""
    from fov3d.control import object_policy
    from fov3d.experiments.classroom_oracle import controller01 as c01, epistemic
    ctx = c01.LocalPolicyContext(int(entity))
    with CH.PolicyChartAdapter(r_hc, label="context: evidence of the completed own look") as ad:
        epistemic.add_observation(ctx.evidence, calibration, state["ids_left"], state["raw_support_L"],
                                  state["ids_right"], state["raw_support_R"], valid, int(entity))
    ctx.history.append(object_policy.history_entry(
        calibration=calibration, instance_L=state["ids_left"], raw_support_L=state["raw_support_L"],
        instance_R=state["ids_right"], raw_support_R=state["raw_support_R"], target_object_id=int(entity)))
    gaze = (float(local_gaze[0]), float(local_gaze[1]))
    ctx.visited.append(gaze)
    ctx.gaze, ctx.calibration, ctx.state = gaze, calibration, state
    return ctx, ad.record()


def add_look(ctx, calibration: dict, state: dict, valid: np.ndarray, r_hc: np.ndarray, local_gaze) -> dict:
    """Controller-01 ``observe``'s own-target context update for one completed look (evidence under the adapter)."""
    from fov3d.control import object_policy
    from fov3d.experiments.classroom_oracle import epistemic
    with CH.PolicyChartAdapter(r_hc, label="post-action: evidence of the executed look") as ad:
        epistemic.add_observation(ctx.evidence, calibration, state["ids_left"], state["raw_support_L"],
                                  state["ids_right"], state["raw_support_R"], valid, int(ctx.target_id))
    ctx.history.append(object_policy.history_entry(
        calibration=calibration, instance_L=state["ids_left"], raw_support_L=state["raw_support_L"],
        instance_R=state["ids_right"], raw_support_R=state["raw_support_R"], target_object_id=int(ctx.target_id)))
    gaze = (float(local_gaze[0]), float(local_gaze[1]))
    ctx.visited.append(gaze)
    ctx.gaze, ctx.calibration, ctx.state = gaze, calibration, state
    return ad.record()


def evidence_arrays(ctx) -> dict:
    ev = ctx.evidence
    return {k: np.asarray(getattr(ev, k)) for k in ("seen_any", "seen_target", "seen_nontarget", "target_depth_valid")}


# ------------------------------------------------------------------ section 10: the probe
def probe(ctx, geometry_c: np.ndarray, r_hc: np.ndarray, sensor, head_r_wh, head_origin_w, profile: str,
          seed_dir_h0: np.ndarray | None = None, label: str = "probe") -> dict:
    """The accepted FSG6f -> Cyclopean service probe and the accepted strict final-look gate v1, read-only."""
    from fov3d.experiments.classroom_oracle import controller01 as c01, controller02 as c02x
    geometry_c = np.asarray(geometry_c, np.float64)
    with CH.PolicyChartAdapter(r_hc, sensor, label) as ad:
        result, decisions = c01.probe_local_policy(ctx, geometry_c)
        verdict = c02x.final_look_gate_v1(
            proposal=result, decision=decisions.get("fsg6f_decision"), geometry=geometry_c, gaze=ctx.gaze,
            calibration=ctx.calibration, state=ctx.state, history=ctx.history, visited=list(ctx.visited),
            profile=profile, head_r_wh=head_r_wh, head_origin_w=head_origin_w, target_id=int(ctx.target_id))
    act = result.action
    out = {"state": result.state.value, "summary": jsonable(dict(result.detail)), "decisions": jsonable(decisions),
           "proposal": None, "gate": {"admissible": bool(verdict.admissible), "reason": verdict.reason,
                                      "detail": jsonable(dict(verdict.detail))},
           "adapter": ad.record(), "effective_points": int(len(geometry_c))}
    if act is not None:
        yc, pc = map(float, act.gaze_yaw_pitch_deg)
        yw, pw, d = CH.local_to_world_gaze(yc, pc, r_hc)
        back = CH.world_to_local_gaze(yw, pw, r_hc)
        prop = {"source": act.source, "local_gaze_deg": [yc, pc], "world_gaze_deg": [yw, pw], "d_H0": d.tolist(),
                "roundtrip_local_gaze_deg": list(back),
                "roundtrip_error_deg": max(abs(back[0] - yc), abs(back[1] - pc)),
                "leverage": CH.leverage(d)}
        if seed_dir_h0 is not None:
            s = np.asarray(seed_dir_h0, np.float64)
            prop["angle_from_seed_deg"] = math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(s, d) /
                                                                              np.linalg.norm(s))))))
        out["proposal"] = prop
    return out


def case_of(probe_out: dict) -> str:
    """A: no proposal (QUIET); 3: proposal rejected by the gate; B: one admissible proposal."""
    if probe_out["proposal"] is None:
        return "A"
    return "B" if probe_out["gate"]["admissible"] else "3"


# ------------------------------------------------------------------ section 8b: rigidly rotated contexts
def rotate_world(q: np.ndarray, calibration: dict, map_h0: np.ndarray, g0: np.ndarray) -> dict:
    """The same fixed head looking at the scene rigidly rotated about the baseline axis by Q."""
    c2 = CH.rotate_calibration(calibration, q)
    return {"calibration": c2, "map_h0": np.asarray(map_h0, np.float64) @ np.asarray(q).T,
            "g0": np.asarray(q) @ np.asarray(g0, np.float64)}


def probe_comparison(a: dict, b: dict, tol: float = SP.FLOAT_TOL) -> list[str]:
    """Local decisions of two probes (chart C), excluding the physical predicted calibration and adapter records."""
    return (compare(a["decisions"], b["decisions"], tol, "decisions")
            + compare(a["summary"], b["summary"], tol, "summary")
            + compare({k: a["gate"][k] for k in ("admissible", "reason")},
                      {k: b["gate"][k] for k in ("admissible", "reason")}, tol, "gate")
            + compare(a["gate"]["detail"], b["gate"]["detail"], tol, "gate/detail", skip=("predicted_calibration",))
            + compare(a["state"], b["state"], tol, "state"))


# ------------------------------------------------------------------ section 14: H0-only fusion
def target_patch(xyz_epi: np.ndarray, valid: np.ndarray, ids: np.ndarray, rgb: np.ndarray, target: int) -> dict:
    """The target's points of the frozen spherical measurement (canonical H0), tagged with their frame."""
    keep = np.asarray(valid, bool) & (np.asarray(ids) == int(target))
    return {"frame": SP.FUSION_FRAME, "patch_id": SP.ACTION_PATCH_ID,
            "xyz_h": np.asarray(xyz_epi, np.float64)[keep], "rgb": np.asarray(rgb, np.float64)[keep],
            "instance_id": np.asarray(ids, np.int32)[keep], "points": int(keep.sum())}


def fuse_h0(sm_map, patch: dict, target: int, radius: float = SP.ASSOCIATION_RADIUS_M,
            cell: float = SP.HASH_CELL_M) -> tuple[Any, dict]:
    """The accepted 12-mm fusion, in canonical H0 only, with one exact replay (idempotence)."""
    from fov3d.reconstruction import surface_map as SM
    if patch.get("frame") != SP.FUSION_FRAME:
        raise FrameRefused(f"persistent fusion happens in canonical H0 only, not in {patch.get('frame')!r}")
    before = int(len(sm_map.xyz_h))
    p = SM.Patch(patch_id=patch["patch_id"], xyz_h=patch["xyz_h"], rgb=patch["rgb"], instance_id=patch["instance_id"])
    n = int(patch["points"])
    if n < SP.MIN_POINTS:
        return sm_map, {"action": "RETAINED_NOT_FUSED", "reason": f"{n} < {SP.MIN_POINTS} target points (accepted "
                        "fusion precondition)", "map_before": before, "map_after": before, "measured_points": n,
                        "matched": 0, "new": 0, "affected_surfels": 0, "matched_distance_m": None}
    m2, meta = SM.fuse(sm_map, p, int(target), float(radius), float(cell))
    replay, rmeta = SM.fuse(m2, p, int(target), float(radius), float(cell))
    a, b = map_arrays(m2), map_arrays(replay)
    exact = maps_equal(a, b)
    close = bool(a["xyz_h"].shape == b["xyz_h"].shape and np.allclose(a["xyz_h"], b["xyz_h"], rtol=0.0,
                                                                      atol=SP.IDEMPOTENCE_ATOL, equal_nan=True))
    if not (exact and close and rmeta.get("duplicate_patch")):
        raise RuntimeError("12 mm fusion lost idempotence")
    d = np.asarray(meta.get("distances_m", np.empty(0)), float)
    return m2, {"action": "FUSED", "map_before": before, "map_after": int(len(m2.xyz_h)), "measured_points": n,
                "matched": int(meta["matched"]), "new": int(meta["new"]),
                "affected_surfels": int(meta["affected_surfels"]), "input_points": int(meta["input_points"]),
                "matched_distance_m": None if not d.size else {
                    "median": float(np.median(d)), "p95": float(np.quantile(d, 0.95)), "max": float(d.max())},
                "replay": {"duplicate_patch": bool(rmeta["duplicate_patch"]), "exact": exact,
                           "allclose_1e-10": close},
                "radius_m": float(radius), "hash_cell_m": float(cell), "frame": SP.FUSION_FRAME}


# ------------------------------------------------------------------ the fixed head and the fake local calibration
def fixed_head(c: dict, head_r_wh, head_origin_w) -> dict:
    """A physical calibration of the fixed head: AB1a head pose, eyes at (-/+0.0315, 0, 0), IPD 0.063, proper."""
    import fsg_geometry as FG
    out = {"validate_calibration": True}
    try:
        FG.validate_calibration(c)
    except ValueError as exc:
        out["validate_calibration"] = f"refused: {exc}"
    centres = np.array([e["centre_h_m"] for e in c["eyes"]], np.float64)
    out["eye_centre_error_m"] = float(np.abs(centres - np.array(SP.EYE_CENTRES_H0)).max())
    out["ipd_m"] = float(c["ipd_m"])
    out["head_R_error"] = float(np.abs(np.asarray(c["head_R_wh"], np.float64) - np.asarray(head_r_wh)).max())
    out["head_origin_error_m"] = float(np.abs(np.asarray(c["head_origin_w_m"], np.float64)
                                              - np.asarray(head_origin_w)).max())
    out["tangent_frame"] = c.get("tangent_frame", "legacy_upright")
    out["ok"] = bool(out["validate_calibration"] is True and out["eye_centre_error_m"] <= SP.HEAD_TOL
                     and abs(out["ipd_m"] - SP.IPD_M) <= SP.HEAD_TOL and out["head_R_error"] <= SP.HEAD_TOL
                     and out["head_origin_error_m"] <= SP.HEAD_TOL)
    return out


def calibration_matches(c: dict, ref: dict, tol: float = 1e-12) -> bool:
    if [list(map(float, c["gaze_yaw_pitch_deg"]))] != [list(map(float, ref["gaze_yaw_pitch_deg"]))]:
        if max(abs(float(x) - float(y)) for x, y in zip(c["gaze_yaw_pitch_deg"], ref["gaze_yaw_pitch_deg"])) > tol:
            return False
    return all(np.abs(np.asarray(e["R_hc"], float) - np.asarray(f["R_hc"], float)).max() <= tol
               and np.abs(np.asarray(e["centre_h_m"], float) - np.asarray(f["centre_h_m"], float)).max() <= tol
               for e, f in zip(c["eyes"], ref["eyes"]))


def physical_calibration_test(c: dict, local_gaze, r_hc, head_r_wh, head_origin_w, profile: str = SP.PROFILE) -> dict:
    """The checker's calibration test: a physical look's calibration must be the REAL fixed-head sensor at the WORLD
    gaze of the local proposal; the fake local-baseline calibration (``make_calibration`` at the LOCAL gaze, as though
    C were the physical head frame) is refused."""
    yw, pw, _d = CH.local_to_world_gaze(float(local_gaze[0]), float(local_gaze[1]), r_hc)
    real = CH.north_star_sensor(profile, yw, pw, head_r_wh, head_origin_w) if profile == SP.PROFILE else \
        CH.baseline_projected_sensor(profile, yw, pw, head_r_wh, head_origin_w)
    fake = CH.baseline_projected_sensor(profile, float(local_gaze[0]), float(local_gaze[1]), head_r_wh, head_origin_w)
    is_real, is_fake = calibration_matches(c, real), calibration_matches(c, fake)
    head = fixed_head(c, head_r_wh, head_origin_w)
    return {"world_gaze_deg": [yw, pw], "matches_real_world_sensor": is_real, "matches_fake_local": is_fake,
            "fixed_head": head, "ok": bool(is_real and not is_fake and head["ok"])}


def copy_ctx(ctx):
    return copy.deepcopy(ctx)
