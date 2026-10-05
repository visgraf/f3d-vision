"""North Star-1a: synthetic / known-answer tests of the NEW integration (analytic data only; no Classroom render).

Contract: docs/north-star/ns1a-perfect-bootstrap-round-contract.md, section 15.  The accepted AB1b oracle and geometry
are reused (their own known answers are accepted); these cases test what NS1a adds: the frozen-gaze reader, the
oracle adapter and core class map, the truth firewall of the stage allowlists, the local identity attachment and the
persistent entity seed construction with the accepted surface map.

The analytic scene is a set of bounded planes in the head frame with Blender-like rasters: Position in the world
frame as float32 ((0, 0, 0) where nothing is hit) and an int32 Object Index (0 where nothing is hit or for a
non-catalog plane).
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import traceback

import numpy as np

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent / "active_bootstrap", HERE.parent / "natural_bootstrap", HERE.parents[1]):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1a_core as CORE  # noqa: E402
import ns1a_spec as SP  # noqa: E402


# ------------------------------------------------------------------ the analytic scene
def plane(centre, normal, up, half_w, half_h, iid) -> dict:
    n = np.asarray(normal, float) / np.linalg.norm(normal)
    a = np.cross(np.asarray(up, float), n)
    a /= np.linalg.norm(a)
    b = np.cross(n, a)
    return {"c": np.asarray(centre, float), "n": n, "a": a, "b": b, "hw": float(half_w), "hh": float(half_h),
            "id": int(iid)}


def cast(o: np.ndarray, d: np.ndarray, planes: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """Nearest bounded-plane hit of rays o + t d (head frame): point (NaN where none) and id (-1 where none)."""
    best_t = np.full(d.shape[:-1], np.inf)
    ids = np.full(d.shape[:-1], -1, np.int32)
    for p in planes:
        nd = d @ p["n"]
        with np.errstate(divide="ignore", invalid="ignore"):
            t = ((p["c"] - o) @ p["n"]) / nd
        x = o + t[..., None] * d
        la, lb = (x - p["c"]) @ p["a"], (x - p["c"]) @ p["b"]
        ok = (np.abs(nd) > 1e-12) & (t > 1e-9) & (np.abs(la) <= p["hw"]) & (np.abs(lb) <= p["hh"]) & (t < best_t)
        best_t = np.where(ok, t, best_t)
        ids = np.where(ok, p["id"], ids)
    pts = np.where(np.isfinite(best_t)[..., None], o + best_t[..., None] * d, np.nan)
    return pts, ids


def render_reference(c: dict, planes: list[dict]) -> tuple[dict, dict]:
    """Blender-like truth rasters for both eyes, plus the exact (float64) left-eye hits for known answers."""
    import fsg_geometry as FG
    w, h = c["image_size_wh"]
    uv = FG.pixels(w, h)
    ref, exact = {}, {}
    for eye in c["eyes"]:
        s = eye["name"]
        d = FG.rays_h(eye, uv)
        pts, ids = cast(np.asarray(eye["centre_h_m"], float), d, planes)
        hit = ids >= 0
        pw = np.where(hit[..., None], FG.head_to_world(c, np.where(hit[..., None], pts, 0.0)), 0.0)
        ref[f"position_w_{s}"] = pw.astype(np.float32)
        ref[f"instance_{s}"] = np.where(hit, ids, 0).astype(np.int32)
        exact[s] = (pts, ids)
    return ref, exact


def calib(yaw: float, pitch: float, head=None) -> dict:
    import fsg_geometry as FG
    if head is None:
        return CORE.planned_calibration(yaw, pitch, FG.HEAD_R_WH, FG.HEAD_ORIGIN_W)
    return CORE.planned_calibration(yaw, pitch, head["head_R_wh"], head["head_origin_w_m"])


def scene_multi() -> list[dict]:
    """Forward scene (head frame): background id 5, two foreground ids 9 and 12, one non-catalog (id 0) patch."""
    up = (0.0, 1.0, 0.0)
    return [plane((0.0, 0.0, -3.0), (0, 0, 1), up, 1.5, 1.5, 5),
            plane((-0.135, 0.0, -2.0), (0, 0, 1), up, 0.115, 0.15, 9),
            plane((0.075, -0.06, -1.5), (0.2, 0, 1), up, 0.045, 0.045, 12),
            plane((0.02, 0.11, -1.8), (0, 0, 1), up, 0.04, 0.04, 0)]


def independent_oracle(c: dict, ref: dict) -> tuple[np.ndarray, np.ndarray]:
    """An own re-implementation of the oracle rule (rows / cols kept, uv_R), not the accepted function."""
    import fsg_geometry as FG
    o = SP.CORE_ORIGIN
    sl = slice(o, o + SP.CORE_SIZE)
    pw = ref["position_w_L"][sl, sl].reshape(-1, 3).astype(np.float64)
    il = ref["instance_L"][sl, sl].reshape(-1)
    hit = np.isfinite(pw).all(1) & (np.abs(pw).sum(1) > 0)
    ph = (pw - np.asarray(c["head_origin_w_m"])) @ np.asarray(c["head_R_wh"])
    e = c["eyes"][1]
    xc = (ph - np.asarray(e["centre_h_m"])) @ np.asarray(e["R_hc"])
    k = np.asarray(e["K"])
    with np.errstate(divide="ignore", invalid="ignore"):
        u = k[0, 0] * xc[:, 0] / xc[:, 2] + k[0, 2]
        v = k[1, 1] * xc[:, 1] / xc[:, 2] + k[1, 2]
    ok = hit & (il > 0) & np.isfinite(u) & np.isfinite(v) & (xc[:, 2] > 1e-9)
    ok &= (u >= 0) & (u <= SP.RAW_SIZE - 1) & (v >= 0) & (v <= SP.RAW_SIZE - 1)
    ui = np.rint(np.clip(np.nan_to_num(u), 0, SP.RAW_SIZE - 1)).astype(int)
    vi = np.rint(np.clip(np.nan_to_num(v), 0, SP.RAW_SIZE - 1)).astype(int)
    ok &= ref["instance_R"][vi, ui] == il
    return np.flatnonzero(ok), np.stack([u, v], -1)[ok]


# ------------------------------------------------------------------ cases
def case(name: str, fn, results: list) -> None:
    try:
        detail = fn()
        results.append({"case": name, "pass": bool(detail.pop("pass")), **detail})
    except Exception as e:  # a crash is a failure, recorded
        results.append({"case": name, "pass": False, "error": repr(e), "trace": traceback.format_exc()[-1500:]})


def _expect_raise(fn, exc=Exception) -> bool:
    try:
        fn()
    except exc:
        return True
    return False


def c01_reader() -> dict:
    fz = json.loads(Path(SP.NB1C_FREEZE[0]).read_text())
    cand = json.loads(Path(SP.NB1C_CANDIDATES[0]).read_text())
    import hashlib
    hz = hashlib.sha256(Path(SP.NB1C_FREEZE[0]).read_bytes()).hexdigest()
    g = CORE.parse_gaze_list(fz, cand)
    got = [(x["rank"], x["row"], x["col"], x["yaw_deg"], x["pitch_deg"]) for x in g]
    return {"pass": hz == SP.NB1C_FREEZE[1] and got == [tuple(x) for x in SP.GAZES], "freeze_sha256": hz,
            "gazes": got}


def c02_altered_order() -> dict:
    fz = json.loads(Path(SP.NB1C_FREEZE[0]).read_text())
    cand = json.loads(Path(SP.NB1C_CANDIDATES[0]).read_text())
    swapped = json.loads(json.dumps(fz))
    swapped["gazes"][1], swapped["gazes"][2] = swapped["gazes"][2], swapped["gazes"][1]
    relabel = json.loads(json.dumps(fz))
    for a, b in ((1, 2),):
        for key in ("row", "col"):
            relabel["gazes"][a][key], relabel["gazes"][b][key] = relabel["gazes"][b][key], relabel["gazes"][a][key]
    dropped = json.loads(json.dumps(fz))
    dropped["gazes"] = dropped["gazes"][:5]
    seventh = json.loads(json.dumps(fz))
    seventh["gazes"].append({"rank": 7, "row": 180, "col": 360})
    r = {n: _expect_raise(lambda d=d: CORE.parse_gaze_list(d, cand), ValueError)
         for n, d in (("swapped", swapped), ("relabelled", relabel), ("dropped", dropped), ("seventh", seventh))}
    return {"pass": all(r.values()), "refused": r}


def c03_altered_gaze() -> dict:
    fz = json.loads(Path(SP.NB1C_FREEZE[0]).read_text())
    cand = json.loads(Path(SP.NB1C_CANDIDATES[0]).read_text())
    moved = json.loads(json.dumps(fz))
    moved["gazes"][3]["col"] += 1
    cmoved = json.loads(json.dumps(cand))
    cmoved["gazes"][3]["yaw_deg"] += 0.5
    import hashlib
    b = json.dumps(moved).encode()
    r = {"freeze_gaze_moved": _expect_raise(lambda: CORE.parse_gaze_list(moved, cand), ValueError),
         "candidate_gaze_moved": _expect_raise(lambda: CORE.parse_gaze_list(fz, cmoved), ValueError),
         "hash_differs": hashlib.sha256(b).hexdigest() != SP.NB1C_FREEZE[1]}
    return {"pass": all(r.values()), "refused": r}


def _scene_products(yaw=0.0, pitch=0.0, planes=None, head=None):
    import ab1b_oracle as O
    import ab1b_geometry as BG
    c = calib(yaw, pitch, head)
    planes = planes if planes is not None else scene_multi()
    ref, exact = render_reference(c, planes)
    prod, summ = O.compute_oracle(c, ref)
    BG.validate_product(prod)
    res = BG.compute_epipolar(c, prod)
    return c, planes, ref, exact, prod, summ, res


def c04_oracle_adapter() -> dict:
    import fsg_geometry as FG
    c, planes, ref, exact, prod, summ, res = _scene_products()
    keep, uv_r = independent_oracle(c, ref)
    want = prod["left_core_row"].astype(np.int64) * SP.CORE_SIZE + prod["left_core_col"]
    same_set = np.array_equal(keep, want)
    pts, _ = exact["L"]
    o = SP.CORE_ORIGIN
    xs = pts[o:o + SP.CORE_SIZE, o:o + SP.CORE_SIZE].reshape(-1, 3)[want]
    uv_true, _z = FG.project_h(c["eyes"][1], xs)
    err = np.abs(uv_true - prod["uv_R"]).max() if len(xs) else np.inf
    own = float(np.abs(uv_r - prod["uv_R"]).max()) if same_set and len(xs) else np.inf
    cls = CORE.core_class_map(c, ref)
    cls_ok = (np.array_equal(np.flatnonzero(cls.ravel() == SP.CLASS_CORRESPONDENCE), want)
              and int((cls == SP.CLASS_INSTANCE0).sum()) == summ["excluded"]["hit_with_instance_0"])
    frac_nonint = float(np.mean(prod["uv_R"] != np.rint(prod["uv_R"])))
    return {"pass": bool(same_set and err <= SP.SYN_PROJECTION_PX and own <= 1e-6 and cls_ok and frac_nonint > 0.99),
            "correspondences": int(want.size), "independent_set_equal": bool(same_set),
            "max_uv_R_vs_analytic_px": float(err), "max_uv_R_vs_own_px": own, "class_map_consistent": bool(cls_ok),
            "uv_R_non_integer_fraction": frac_nonint, "attrition": summ["attrition"]}


def c09_multi_id() -> dict:
    c, planes, ref, exact, prod, summ, res = _scene_products()
    ids = CORE.attach_identity(prod, res["valid_epi"], ref["instance_L"])
    _pts, eid = exact["L"]
    o = SP.CORE_ORIGIN
    want = eid[o:o + SP.CORE_SIZE, o:o + SP.CORE_SIZE].reshape(-1)[
        prod["left_core_row"].astype(np.int64) * SP.CORE_SIZE + prod["left_core_col"]]
    s = CORE.identity_summary(ids)
    return {"pass": bool(np.array_equal(ids, want) and set(s["entities"]) == {"5", "9", "12"}
                         and s["zero_id_points"] == 0), "entities": s["entities"]}


def c06_identity_pixel() -> dict:
    c, planes, ref, exact, prod, summ, res = _scene_products()
    ids = CORE.attach_identity(prod, res["valid_epi"], ref["instance_L"])
    shifted_inst = np.roll(ref["instance_L"], 1, axis=1)
    ids_s = CORE.attach_identity(prod, res["valid_epi"], shifted_inst)
    bad = dict(prod)
    bad["uv_L"] = prod["uv_L"] + np.array([1.0, 0.0])
    frac = dict(prod)
    frac["uv_L"] = prod["uv_L"] + 0.25
    r = {"one_pixel_shift_changes_ids": int((ids_s != ids).sum()) > 0,
         "wrong_pixel_uv_L_refused": _expect_raise(lambda: CORE.attach_identity(bad, res["valid_epi"],
                                                                                 ref["instance_L"]), ValueError),
         "non_centre_uv_L_refused": _expect_raise(lambda: CORE.attach_identity(frac, res["valid_epi"],
                                                                                ref["instance_L"]), ValueError)}
    return {"pass": all(r.values()), **r, "ids_changed_by_shift": int((ids_s != ids).sum())}


def c18_end_to_end() -> dict:
    c, planes, ref, exact, prod, summ, res = _scene_products()
    pts, _ = exact["L"]
    o = SP.CORE_ORIGIN
    xs = pts[o:o + SP.CORE_SIZE, o:o + SP.CORE_SIZE].reshape(-1, 3)[
        prod["left_core_row"].astype(np.int64) * SP.CORE_SIZE + prod["left_core_col"]]
    v = res["valid_epi"]
    err = np.linalg.norm(res["P_epi"][v] - xs[v], axis=-1)
    return {"pass": bool(v.all() and np.median(err) <= SP.SYN_E2E_MEDIAN_M and err.max() <= SP.SYN_E2E_MAX_M),
            "triangulated": int(v.sum()), "of": int(v.size), "error_median_m": float(np.median(err)),
            "error_max_m": float(err.max())}


def c16_instance0() -> dict:
    import fov3d.reconstruction.surface_map as SM
    c, planes, ref, exact, prod, summ, res = _scene_products()
    _pts, eid = exact["L"]
    o = SP.CORE_ORIGIN
    core_ids = eid[o:o + SP.CORE_SIZE, o:o + SP.CORE_SIZE]
    n0 = int((core_ids == 0).sum())
    ids = CORE.attach_identity(prod, res["valid_epi"], ref["instance_L"])
    out = CORE.construct_seeds([{"rank": 1, "xyz": res["P_epi"], "valid": res["valid_epi"], "ids": ids,
                                 "rgb": np.full((len(ids), 3), 0.5)}], SM)
    bad = ids.copy()
    bad[0] = 0
    refused = _expect_raise(lambda: CORE.construct_seeds([{"rank": 1, "xyz": res["P_epi"], "valid": res["valid_epi"],
                                                           "ids": bad, "rgb": np.full((len(ids), 3), 0.5)}], SM),
                            ValueError)
    return {"pass": bool(n0 > 100 and summ["excluded"]["hit_with_instance_0"] == n0 and 0 not in out["maps"]
                         and refused), "id_0_core_pixels": n0,
            "oracle_hit_with_instance_0": summ["excluded"]["hit_with_instance_0"],
            "entities": sorted(out["maps"]), "id_0_point_refused_by_seed_construction": refused}


def _pts(n: int, x0: float, z: float = -2.0, step: float = 0.004, seed: int = 0) -> np.ndarray:
    side = int(np.ceil(np.sqrt(n)))
    g = np.stack(np.meshgrid(np.arange(side), np.arange(side)), -1).reshape(-1, 2)[:n] * step
    rng = np.random.default_rng(seed)
    return np.c_[g[:, 0] + x0, g[:, 1], np.full(n, z)] + rng.normal(scale=2e-4, size=(n, 3))


def _gaze(rank: int, parts: list[tuple[int, np.ndarray]]) -> dict:
    xyz = np.vstack([p for _k, p in parts])
    ids = np.concatenate([np.full(len(p), k, np.int32) for k, p in parts])
    return {"rank": rank, "xyz": xyz, "valid": np.ones(len(ids), bool), "ids": ids,
            "rgb": np.full((len(ids), 3), 0.25 + 0.01 * rank)}


def c10_c11_threshold() -> dict:
    import fov3d.reconstruction.surface_map as SM
    out = CORE.construct_seeds([_gaze(1, [(3, _pts(99, 0.0)), (4, _pts(100, 1.0))])], SM)
    ev = {e["entity"]: e["action"] for e in out["history"]}
    return {"pass": ev == {3: "SEEN_BUT_NOT_INITIALIZED", 4: "INITIALIZED"} and sorted(out["maps"]) == [4]
            and len(out["maps"][4]["xyz_h"]) == 100, "actions": {str(k): v for k, v in ev.items()}}


def c12_c14_fusion() -> dict:
    import fov3d.reconstruction.surface_map as SM
    a, b = _pts(900, 0.0, seed=1), _pts(900, 0.06, seed=2)       # 0.12 x 0.12 m patches overlapping by half
    out = CORE.construct_seeds([_gaze(1, [(7, a)]), _gaze(2, [(7, b)])], SM)
    fz = [e for e in out["history"] if e["action"] == "FUSED"]
    m = out["maps"][7]
    ok = (len(fz) == 1 and fz[0]["matched"] > 0 and fz[0]["new"] > 0 and fz[0]["matched_distance_m"]["max"] <= 0.012
          and list(m["patch_ids"]) == [SP.patch_id(1), SP.patch_id(2)] and sorted(out["maps"]) == [7]
          and int(m["support_count"].max()) == 2 and fz[0]["replay"]["exact"])
    return {"pass": bool(ok), "fusion": {k: v for k, v in fz[0].items() if k != "replay"} if fz else None,
            "entities": sorted(out["maps"])}


def c13_duplicate() -> dict:
    import fov3d.reconstruction.surface_map as SM
    p = SM.Patch(SP.patch_id(1), _pts(400, 0.0), np.full((400, 3), 0.5), np.full(400, 7, np.int32))
    q = SM.Patch(SP.patch_id(2), _pts(400, 0.03, seed=3), np.full((400, 3), 0.5), np.full(400, 7, np.int32))
    m = SM.initialize(p, 7)
    m2, _ = SM.fuse(m, q, 7, SP.ASSOCIATION_RADIUS_M, SP.HASH_CELL_M)
    m3, meta = SM.fuse(m2, q, 7, SP.ASSOCIATION_RADIUS_M, SP.HASH_CELL_M)
    m4, meta4 = SM.fuse(m3, p, 7, SP.ASSOCIATION_RADIUS_M, SP.HASH_CELL_M)
    same = CORE.maps_equal(CORE.map_arrays(m2), CORE.map_arrays(m3)) and CORE.maps_equal(CORE.map_arrays(m2),
                                                                                          CORE.map_arrays(m4))
    return {"pass": bool(meta["duplicate_patch"] and meta4["duplicate_patch"] and same), "exact": bool(same)}


def c15_no_cross_id() -> dict:
    import fov3d.reconstruction.surface_map as SM
    a = _pts(600, 0.0, seed=4)
    out = CORE.construct_seeds([_gaze(1, [(3, a)]), _gaze(2, [(4, a + 1e-4)])], SM)
    homogeneous = all(np.all(m["instance_id"] == k) for k, m in out["maps"].items())
    m3 = SM.initialize(SM.Patch("x", a, np.full((600, 3), .5), np.full(600, 3, np.int32)), 3)
    refused = _expect_raise(lambda: SM.fuse(m3, SM.Patch("y", a, np.full((600, 3), .5), np.full(600, 4, np.int32)),
                                            3, SP.ASSOCIATION_RADIUS_M, SP.HASH_CELL_M), ValueError)
    return {"pass": bool(sorted(out["maps"]) == [3, 4] and homogeneous and refused
                         and [e["action"] for e in out["history"]] == ["INITIALIZED", "INITIALIZED"]),
            "entities": sorted(out["maps"]), "cross_id_fuse_refused": refused}


def c19_undersupported() -> dict:
    import fov3d.reconstruction.surface_map as SM
    out = CORE.construct_seeds([_gaze(1, [(3, _pts(500, 0.0))]), _gaze(2, [(3, _pts(50, 0.01, seed=9))])], SM)
    ev = [e["action"] for e in out["history"]]
    unchanged = CORE.maps_equal(out["snapshots"][1][3], out["snapshots"][2][3])
    return {"pass": ev == ["INITIALIZED", "RETAINED_NOT_FUSED"] and unchanged
            and list(out["maps"][3]["patch_ids"]) == [SP.patch_id(1)], "actions": ev}


def c14_pipeline_two_gazes() -> dict:
    """The same id seen at two gazes through oracle -> geometry -> identity -> seeds is one persistent entity."""
    import fov3d.reconstruction.surface_map as SM
    up = (0.0, 1.0, 0.0)
    planes = [plane((0.1, 0.0, -2.0), (0, 0, 1), up, 0.6, 0.4, 7)]
    gz = []
    for rank, yaw in ((1, 0.0), (2, 6.0)):
        c, _pl, ref, _ex, prod, _s, res = _scene_products(yaw, 0.0, planes)
        sub = (prod["left_core_row"] % 6 == 0) & (prod["left_core_col"] % 6 == 0)
        p2 = {k: v[sub] for k, v in prod.items()}
        import ab1b_geometry as BG
        BG.validate_product(p2)
        res2 = BG.compute_epipolar(c, p2)
        ids = CORE.attach_identity(p2, res2["valid_epi"], ref["instance_L"])
        gz.append({"rank": rank, "xyz": res2["P_epi"], "valid": res2["valid_epi"], "ids": ids,
                   "rgb": np.full((len(ids), 3), 0.5)})
    out = CORE.construct_seeds(gz, SM)
    ev = [(e["rank"], e["action"], e.get("matched", 0), e.get("new", 0)) for e in out["history"]]
    ok = (sorted(out["maps"]) == [7] and [e[1] for e in ev] == ["INITIALIZED", "FUSED"] and ev[1][2] > 0
          and ev[1][3] > 0 and len(out["maps"][7]["patch_ids"]) == 2)
    return {"pass": bool(ok), "events": ev}


def c21_determinism() -> dict:
    import fov3d.reconstruction.surface_map as SM
    g = [_gaze(1, [(3, _pts(500, 0.0)), (5, _pts(300, 1.0))]), _gaze(2, [(3, _pts(500, 0.05, seed=2))])]
    a, b = CORE.construct_seeds(g, SM), CORE.construct_seeds(g, SM)
    same = all(CORE.maps_equal(a["maps"][k], b["maps"][k]) for k in a["maps"]) and a["history"] == b["history"]
    order = _expect_raise(lambda: CORE.construct_seeds(list(reversed(g)), SM), ValueError)
    return {"pass": bool(same and order), "deterministic": bool(same), "rank_order_enforced": order}


def c20_rank1_calibration() -> dict:
    import hashlib
    b = Path(SP.HEAD_POSE_SOURCE[0]).read_bytes()
    head = json.loads(b)
    c = calib(SP.GAZES[0][3], SP.GAZES[0][4], head)
    out = CORE.calibration_bytes(c)
    return {"pass": hashlib.sha256(b).hexdigest() == SP.HEAD_POSE_SOURCE[1] and out == b,
            "byte_identical_to_ab1a": out == b}


def c22_document() -> dict:
    import fov3d.reconstruction.surface_map as SM
    g = [_gaze(1, [(3, _pts(500, 0.0)), (5, _pts(60, 1.0))]), _gaze(2, [(3, _pts(500, 0.6, seed=2)),
                                                                        (5, _pts(200, 1.0, seed=5))])]
    out = CORE.construct_seeds(g, SM)
    doc = CORE.seed_set_document(g, out, {"per_rank": {}})
    e = {x["temporary_entity_id"]: x for x in doc["entities"]}
    text = json.dumps(doc)
    ok = (e[3]["initialized_at_rank"] == 1 and e[3]["gaze_ranks_seen"] == [1, 2] and e[3]["contributing_patches"] == 2
          and e[5]["first_seen_rank"] == 1 and e[5]["initialized_at_rank"] == 2 and e[5]["points_per_gaze"] == {
              "1": 60, "2": 200} and e[5]["total_raw_measured_points"] == 260 and doc["counts"]["initialized"] == 2
          and "object_name" not in text and e[3]["provenance_popcount_equals_support"])
    return {"pass": bool(ok), "counts": doc["counts"]}


# ------------------------------------------------------------------ the stage allowlists (truth firewall)
def guard_cases(work: Path) -> list[tuple[str, object]]:
    import ns1a_run as R
    from nb1a_guard import OpenGuard
    run = work / "guard-run"

    def build_geometry_run() -> tuple[Path, Path]:
        c, _pl, ref, _ex, prod, _s, _res = _scene_products()
        (run / "observations/rank-01/acquisition").mkdir(parents=True, exist_ok=True)
        (run / "observations/rank-01/oracle_aid").mkdir(parents=True, exist_ok=True)
        (run / "correspondence/rank-01").mkdir(parents=True, exist_ok=True)
        (run / SP.acq_rel(1, "calibration.json")).write_bytes(CORE.calibration_bytes(c))
        np.savez_compressed(run / SP.aid_rel(1, "reference-observation.npz"), **ref)
        np.savez_compressed(run / "correspondence/rank-01/oracle-correspondences.npz", **prod)
        return run / SP.aid_rel(1, "reference-observation.npz"), run / SP.CATALOG_REL

    def refused(reads, target) -> bool:
        """The stage allowlist with a write dir OUTSIDE the run (as in every stage): reading target must be refused."""
        g = OpenGuard("ns1a-synthetic-probe", reads, [work / "probe-out"])
        try:
            with g:
                open(target, "rb").close()
        except PermissionError:
            return len(g.violations) == 1
        except FileNotFoundError:
            return False
        return False

    def c05() -> dict:
        ref_p, _cat = build_geometry_run()
        ok_run = R.geometry_rank(run, 1)
        rec_ok = json.loads((run / "geometry/rank-01/geometry-opened-files.json").read_text())
        shutil.rmtree(run / "geometry")
        blocked = _expect_raise(lambda: R.geometry_rank(run, 1, probe=lambda: np.load(ref_p)), PermissionError)
        rec = json.loads((run / "geometry/rank-01/geometry-opened-files.json").read_text())
        shutil.rmtree(run / "geometry")
        return {"pass": bool(blocked and len(rec["violations"]) == 1 and rec["position_reads"] >= 1
                             and len(rec_ok["data_reads"]) == 2 and not rec_ok["violations"]
                             and ok_run["counts"]["triangulated_epipolar"] > 0),
                "position_read_refused": blocked, "positive_control_data_reads": len(rec_ok["data_reads"])}

    def c07() -> dict:
        reads = R.seed_reads(run) + R.segmentation_reads(run) + R.geometry_reads(run, 1) + R.oracle_reads(run, 1)
        bad = [str(p) for p in reads if any(t in str(p) for t in SP.FORBIDDEN_BEFORE_FREEZE)]
        r = {str(t): refused(R.seed_reads(run), t) for t in (SP.ACCEPTED_CATALOG[0], SP.C01_SEEDS[0],
                                                             SP.BREADTH1_OBJECTS[0])}
        return {"pass": not bad and all(r.values()), "refused": r, "forbidden_in_allowlists": bad}

    def c08() -> dict:
        _ref, cat = build_geometry_run()
        cat.parent.mkdir(parents=True, exist_ok=True)
        cat.write_text(json.dumps({"instances": [{"instance_id": 5, "object_name": "synthetic"}]}))
        r = {"segmentation": refused(R.segmentation_reads(run), cat), "seeds": refused(R.seed_reads(run), cat),
             "geometry": refused(R.geometry_reads(run, 1), cat), "oracle": refused(R.oracle_reads(run, 1), cat)}
        return {"pass": all(r.values()), "refused": r}

    def c17() -> dict:
        cat_in_eval = any(str(p).endswith(SP.CATALOG_REL) for p in R.evaluation_reads(run, []))
        empty = work / "eval-run"
        empty.mkdir(exist_ok=True)
        refuses = _expect_raise(lambda: R.evaluate(R.Ctx(empty, True)), SystemExit)
        return {"pass": bool(cat_in_eval and refuses), "catalog_in_evaluation_allowlist": cat_in_eval,
                "evaluate_refuses_without_seed_freeze": refuses}

    return [("05 truth-free geometry: a Position / Object Index read is refused", c05),
            ("07 global catalog / Controller-01 seeds / Breadth-1 before the seed freeze: refused", c07),
            ("08 object-name (sealed catalog) access before the freeze: refused", c08),
            ("17 the catalog opens only in the evaluation stage, after the seed freeze", c17)]


CASES = [("01 frozen gaze reader: exact NB1c hash and six-gaze order", c01_reader),
         ("02 altered order (swap, relabel, drop, seventh): refused", c02_altered_order),
         ("03 altered gaze: refused", c03_altered_gaze),
         ("04 perfect-correspondence adapter: accepted validator, analytic and independent oracle", c04_oracle_adapter),
         ("06 identity from the exact left raw-core pixels", c06_identity_pixel),
         ("09 known multi-id patch: correct local ids", c09_multi_id),
         ("10/11 initialization below 100 does not occur; at 100 it succeeds", c10_c11_threshold),
         ("12 overlapping second patch: 12-mm fusion gives matched and new support", c12_c14_fusion),
         ("13 duplicate patch replay: exactly idempotent", c13_duplicate),
         ("14 the same id at two gazes (oracle -> geometry -> identity -> seeds): one entity", c14_pipeline_two_gazes),
         ("15 different ids never fuse", c15_no_cross_id),
         ("16 instance 0 stays unassigned and never initializes", c16_instance0),
         ("18 end-to-end analytic geometry", c18_end_to_end),
         ("19 an undersupported later measurement is retained, not fused", c19_undersupported),
         ("20 rank-1 calibration byte-identical to AB1a (calibration-only)", c20_rank1_calibration),
         ("21 determinism and frozen rank order", c21_determinism),
         ("22 seed-set document fields; no names", c22_document)]


def run_all(out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for name, fn in CASES:
        case(name, fn, results)
    work = Path(tempfile.mkdtemp(prefix="guard-", dir=out_dir))
    try:
        for name, fn in guard_cases(work):
            case(name, fn, results)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    results.sort(key=lambda r: r["case"])
    passed = [r["case"] for r in results if r["pass"]]
    failed = [r["case"] for r in results if not r["pass"]]
    return {"schema": "NS1a-synthetic-v1", "truth": SP.TRUTH_DERIVED, "data": "analytic synthetic scenes only",
            "marker": "NS1A_SYNTHETIC_PASS" if not failed else "NS1A_SYNTHETIC_FAIL",
            "passed": passed, "failed": failed, "cases": results}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    rep = run_all(a.out)
    for r in rep["cases"]:
        print(("PASS " if r["pass"] else "FAIL ") + r["case"] + ("" if r["pass"] else f"  {r.get('error', '')}"))
    print(f"{rep['marker']} {len(rep['passed'])}/{len(rep['cases'])}")
    raise SystemExit(bool(rep["failed"]))
