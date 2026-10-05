"""North Star-1b: synthetic / known-answer tests (contract section 18), analytic data only, before NS1a data is touched.

Each test returns (passed, detail).  ``run_all`` returns the report written by the ``synthetic`` stage.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "natural_bootstrap", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1b_chart as CH  # noqa: E402
import ns1b_core as CORE  # noqa: E402
import ns1b_fixtures as FX  # noqa: E402
import ns1b_spec as SP  # noqa: E402

RNG_SEED = 20261005
NB1C_GAZES = [(y, p) for _r, y, p in SP.NS1A_RANK_GAZES]


def _dirs(n: int = 24) -> np.ndarray:
    rng = np.random.default_rng(RNG_SEED)
    d = rng.normal(size=(n, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    d = d[np.abs(d[:, 0]) < 0.99]
    return np.vstack([d] + [CH.gaze_direction(y, p)[None] for y, p in NB1C_GAZES])


def _points(n: int = 50) -> np.ndarray:
    rng = np.random.default_rng(RNG_SEED + 1)
    return rng.normal(size=(n, 3)) * 2.0


# ------------------------------------------------------------------ 1-5: the chart
def t01_basis():
    worst = {"ortho": 0.0, "det": 0.0}
    for g in _dirs():
        r = CH.chart_basis(g)["R_HC"]
        worst["ortho"] = max(worst["ortho"], float(np.abs(r.T @ r - np.eye(3)).max()))
        worst["det"] = max(worst["det"], abs(float(np.linalg.det(r)) - 1.0))
    return worst["ortho"] <= SP.ORTHO_TOL and worst["det"] <= SP.ORTHO_TOL, worst


def t02_centre():
    worst = max(max(abs(v) for v in CH.yaw_pitch(CH.to_chart(g, CH.chart_basis(g)["R_HC"]))) for g in _dirs())
    return worst <= SP.CENTRE_TOL_DEG, {"max_seed_local_deg": worst}


def t03_direction_roundtrip():
    worst = 0.0
    for g in _dirs():
        r = CH.chart_basis(g)["R_HC"]
        d = _dirs()
        worst = max(worst, float(np.abs(CH.to_h0(CH.to_chart(d, r), r) - d).max()))
    return worst <= SP.ROUNDTRIP_TOL, {"max_error": worst}


def t04_point_roundtrip():
    p = _points()
    worst = max(float(np.abs(CH.to_h0(CH.to_chart(p, CH.chart_basis(g)["R_HC"]), CH.chart_basis(g)["R_HC"]) - p).max())
                for g in _dirs())
    return worst <= SP.ROUNDTRIP_TOL, {"max_error_m": worst}


def t05_distance():
    p = _points()
    d0 = np.linalg.norm(p[:, None] - p[None], axis=-1)
    worst = 0.0
    for g in _dirs():
        q = CH.to_chart(p, CH.chart_basis(g)["R_HC"])
        worst = max(worst, float(np.abs(np.linalg.norm(q[:, None] - q[None], axis=-1) - d0).max()))
    return worst <= SP.ROUNDTRIP_TOL, {"max_distance_change_m": worst}


# ------------------------------------------------------------------ 6-10, 14-15: covariance (fixtures module)
def covariance_tests(suite: dict) -> dict:
    k1 = suite["K1_fsg6f"]
    cyc = suite["K1_cyclopean"]
    gate = suite["K1_gate"]
    return {
        "06_identity_fsg6f": (all(not c["identity_differences"] and c["known_answer"] for c in k1["cases"])
                              and k1["eye_swap_invariant"] and suite["K1_frontier_state"]["pass"],
                              {"cases": [[c["name"], c["next_gaze_deg"], c["reason"]] for c in k1["cases"]]}),
        "07_rotation_fsg6f": (all(r["pass"] for r in k1["rotations"]),
                              {"rotations_deg": [r["beta_deg"] for r in k1["rotations"]],
                               "tie_inversions": [[r["beta_deg"], c["name"], c["tie_inversions"]] for r in k1["rotations"]
                                                  for c in r["cases"] if c["tie_inversions"]],
                               "voxel_boundary_flips": [[r["beta_deg"], c["name"], c["voxel_boundary_flip"]]
                                                        for r in k1["rotations"] for c in r["cases"]
                                                        if c["voxel_boundary_flip"]]}),
        "08_identity_cyclopean": (cyc["bay"]["identity_equal"] and cyc["bay"]["known_answer"]
                                  and cyc["add_observation"]["identity_equal"] and cyc["add_observation"]["P2_calls"] > 0,
                                  {"bay_fixation": cyc["bay"]["next_gaze_deg"]}),
        "09_rotation_cyclopean": (not any(cyc["bay"]["rotation_differences"])
                                  and all(x["evidence_equal"] and not x["differences"]
                                          for x in cyc["add_observation"]["rotations"]), {}),
        "10_projection": (suite["projection_invariance"]["pass"],
                          {"max_uv_px": max(r["uv_difference_px"] for r in suite["projection_invariance"]["rows"]),
                           "min_negative_control_px": min(r["negative_control_px"]
                                                          for r in suite["projection_invariance"]["rows"])}),
        "14_identity_gate": (not gate["identity_differences"], {"verdict": gate["verdict"], "counts": gate["counts"]}),
        "15_rotated_gate_real_sensor": (all(not x["differences"] and x["p3_is_real_world_sensor"]
                                            and not x["p3_is_fake_local"] and x["fixed_head"] for x in gate["rotations"]),
                                        {"rotations": gate["rotations"]}),
    }


# ------------------------------------------------------------------ 11-13: physical sensor
def _head():
    import fsg_geometry as FG
    return FG.HEAD_R_WH, FG.HEAD_ORIGIN_W


def t11_fake_local_refused():
    hr, ho = _head()
    r = CH.chart_basis(CH.gaze_direction(*NB1C_GAZES[5]))["R_HC"]
    local = (5.0, 5.0)
    yw, pw, _ = CH.local_to_world_gaze(*local, r)
    real = CH.north_star_sensor("full", yw, pw, hr, ho)
    fake = CH.north_star_sensor("full", *local, hr, ho)            # make_calibration as though C were the head frame
    t_real = CORE.physical_calibration_test(real, local, r, hr, ho)
    t_fake = CORE.physical_calibration_test(fake, local, r, hr, ho)
    # the other fake: eye centres reset to +/- IPD/2 along the chart's x axis (a secretly rotated baseline)
    reset = copy.deepcopy(real)
    for e, s in zip(reset["eyes"], (-1.0, 1.0)):
        e["centre_h_m"] = (s * SP.IPD_M / 2 * r[:, 0]).tolist()
    t_reset = CORE.physical_calibration_test(reset, local, r, hr, ho)
    ok = t_real["ok"] and not t_fake["ok"] and t_fake["matches_fake_local"] and not t_reset["ok"] \
        and not t_reset["fixed_head"]["ok"]
    return ok, {"real": t_real["ok"], "fake_local_refused": not t_fake["ok"],
                "reset_centres_refused": not t_reset["ok"], "reset_validate": t_reset["fixed_head"]["validate_calibration"]}


def t12_known_directions():
    r_fwd = CH.chart_basis(np.array([0.0, 0.0, -1.0]))["R_HC"]
    r_back = CH.chart_basis(np.array([0.0, 0.0, 1.0]))["R_HC"]
    yb, pb, _ = CH.local_to_world_gaze(0.0, 10.0, r_back)
    checks = {
        "forward_seed_chart_is_identity": float(np.abs(r_fwd - np.eye(3)).max()) <= 1e-15,
        "backward_seed_chart_rows": np.allclose(r_back, np.diag([1.0, -1.0, -1.0]), atol=1e-15),
        "backward_local_up_is_world_down": abs(abs(yb) - 180.0) <= 1e-9 and abs(pb + 10.0) <= 1e-9,
    }
    worst = 0.0
    for g in _dirs():
        r = CH.chart_basis(g)["R_HC"]
        y0, p0 = CH.yaw_pitch(g)
        yw, pw, _ = CH.local_to_world_gaze(0.0, 0.0, r)
        worst = max(worst, abs(((yw - y0 + 180) % 360) - 180), abs(pw - p0))
        for yl, pl in ((5.0, 5.0), (-5.0, 0.0), (0.0, -5.0), (25.0, -20.0)):
            yw, pw, _ = CH.local_to_world_gaze(yl, pl, r)
            yb2, pb2 = CH.world_to_local_gaze(yw, pw, r)
            worst = max(worst, abs(yb2 - yl), abs(pb2 - pl))
        x_dir = CH.to_h0(CH.gaze_direction(90.0, 0.0), r)
        worst = max(worst, float(np.abs(x_dir - r[:, 0]).max()))
    checks["seed_and_candidate_roundtrips"] = worst <= SP.GAZE_ROUNDTRIP_TOL_DEG
    return all(checks.values()), {**checks, "worst": worst}


def t13_world_calibration_fixed_head():
    hr, ho = _head()
    out = []
    for g in _dirs()[-6:]:
        r = CH.chart_basis(g)["R_HC"]
        for local in ((5.0, 5.0), (-5.0, -5.0)):
            yw, pw, _ = CH.local_to_world_gaze(*local, r)
            fh = CORE.fixed_head(CH.north_star_sensor("full", yw, pw, hr, ho), hr, ho)
            out.append(fh["ok"] and fh["tangent_frame"] == SP.TANGENT_FRAME)
    return all(out), {"calibrations": len(out)}


# ------------------------------------------------------------------ 16-17: selection
def _seed_doc(entities):
    return {"entities": entities}


def _ent(k, init, rank, patches, surfels):
    return {"temporary_entity_id": k, "initialized": init, "initialized_at_rank": rank if init else None,
            "contributing_patches": patches, "final_surfels": surfels}


def _gaze_doc():
    return {"gazes": [{"rank": r, "yaw_deg": y, "pitch_deg": p} for r, y, p in SP.NS1A_RANK_GAZES]}


def t16_selection_rule():
    ents = [_ent(5, True, 2, 1, 900), _ent(7, True, 2, 1, 900), _ent(3, True, 2, 1, 400), _ent(9, True, 5, 2, 10 ** 6),
            _ent(11, False, None, 0, 0), _ent(4, True, 1, 1, 10 ** 6)]
    a = CORE.select_target(_seed_doc(ents), _gaze_doc())
    rng = np.random.default_rng(RNG_SEED)
    perms = [CORE.select_target(_seed_doc([ents[i] for i in rng.permutation(len(ents))]), _gaze_doc())["selected"]
             for _ in range(6)]
    lev = {r: CH.leverage(CH.gaze_direction(y, p)) for r, y, p in SP.NS1A_RANK_GAZES}
    # rank 2 (L 0.99993) beats rank 1 (L 0.264); 9 (rank 5) is excluded as multi-patch; 5 and 7 tie in L and surfels
    ok = (a["selected"] == 5 and a["decided_by"] == "temporary_entity_id" and set(perms) == {5}
          and sorted(e["temporary_entity_id"] for e in a["excluded"]) == [9, 11] and lev[2] > lev[1])
    b = CORE.select_target(_seed_doc([_ent(5, True, 2, 1, 900), _ent(3, True, 2, 1, 1400)]), _gaze_doc())
    ok &= b["selected"] == 3 and b["decided_by"] == "final_surfels"
    c = CORE.select_target(_seed_doc([_ent(5, True, 1, 1, 10 ** 6), _ent(3, True, 6, 1, 1)]), _gaze_doc())
    ok &= c["selected"] == 3 and c["decided_by"] == "leverage"
    return ok, {"tie_by_id": a["selected"], "tie_by_surfels": b["selected"], "by_leverage": c["selected"],
                "permutations": perms}


def t17_name_refused():
    ents = [_ent(5, True, 2, 1, 900)]
    bad = copy.deepcopy(ents)
    bad[0]["object_name"] = "pipe"
    try:
        CORE.select_target(_seed_doc(bad), _gaze_doc())
        refused_field = False
    except CORE.SelectionRefused:
        refused_field = True
    from nb1a_guard import OpenGuard
    with tempfile.TemporaryDirectory() as td:
        ok_file, cat = Path(td) / "seed-set.json", Path(td) / "instance-catalog.json"
        ok_file.write_text("{}")
        cat.write_text("{}")
        g = OpenGuard("ns1b-synthetic-selection", [ok_file], [Path(td) / "out"])
        refused_read = False
        with g:
            ok_file.read_text()
            try:
                cat.read_text()
            except PermissionError:
                refused_read = True
    return refused_field and refused_read, {"name_field_refused": refused_field, "catalog_read_refused": refused_read}


# ------------------------------------------------------------------ 18-20: fusion and process
def _plane(pid, lo, hi, z=-2.0, k=71):
    rng = np.random.default_rng(12)
    xy = np.stack(np.meshgrid(np.linspace(lo, hi, 50), np.linspace(-.10, .10, 24)), axis=-1).reshape(-1, 2)
    xyz = np.c_[xy, z * np.ones(len(xy))] + rng.normal(scale=.0004, size=(len(xy), 3))
    return {"frame": "H0", "patch_id": pid, "xyz_h": xyz, "rgb": np.full((len(xyz), 3), 0.4),
            "instance_id": np.full(len(xyz), k, np.int32), "points": int(len(xyz))}


def t18_fusion():
    from fov3d.reconstruction import surface_map as SM
    a, b = _plane("A", -.28, -.02), _plane("B", -.12, .12)
    m = SM.initialize(SM.Patch(a["patch_id"], a["xyz_h"], a["rgb"], a["instance_id"]), 71)
    m2, rec = CORE.fuse_h0(m, b, 71)
    direct, meta = SM.fuse(m, SM.Patch(b["patch_id"], b["xyz_h"], b["rgb"], b["instance_id"]), 71, 0.012, 0.012)
    same = CORE.maps_equal(CORE.map_arrays(m2), CORE.map_arrays(direct))
    small = _plane("S", -.01, .01)
    small = {**small, "xyz_h": small["xyz_h"][:60], "rgb": small["rgb"][:60], "instance_id": small["instance_id"][:60],
             "points": 60}
    m3, rec3 = CORE.fuse_h0(m2, small, 71)
    ok = (same and rec["matched"] == int(meta["matched"]) > 300 and rec["new"] == int(meta["new"]) > 300
          and rec["replay"]["exact"] and rec3["action"] == "RETAINED_NOT_FUSED" and m3 is m2)
    return ok, {"matched": rec["matched"], "new": rec["new"], "undersupported": rec3["action"]}


def t19_local_frame_refused():
    from fov3d.reconstruction import surface_map as SM
    a = _plane("A", -.28, -.02)
    m = SM.initialize(SM.Patch(a["patch_id"], a["xyz_h"], a["rgb"], a["instance_id"]), 71)
    b = {**_plane("B", -.12, .12), "frame": "C"}
    try:
        CORE.fuse_h0(m, b, 71)
        return False, {"refused": False}
    except CORE.FrameRefused:
        return True, {"refused": True}


def t20_second_action_refused():
    import ns1b_run as RUN
    with tempfile.TemporaryDirectory() as td:
        obs = Path(td) / "observation"
        obs.mkdir()
        (obs / "acquisition").mkdir()
        try:
            RUN.once(obs / "acquisition", "the one physical observation")
            again = False
        except RUN.Refused:
            again = True
    try:
        RUN.single_action({"case": "B", "actions": [{"local_gaze_deg": [5, 5]}, {"local_gaze_deg": [0, 5]}]})
        two = False
    except RUN.Refused:
        two = True
    try:
        RUN.single_action({"case": "A", "actions": [{"local_gaze_deg": [5, 5]}]})
        quiet = False
    except RUN.Refused:
        quiet = True
    return again and two and quiet, {"rerender_refused": again, "two_actions_refused": two,
                                     "action_without_case_B_refused": quiet}


# ------------------------------------------------------------------ extras: adapter mechanics, singularity
def tx_adapter_mechanics():
    before = CH.original_functions()
    with CH.PolicyChartAdapter(CH.rot_x(30.0)) as ad:
        during = CH.original_functions()
        try:
            with CH.PolicyChartAdapter(np.eye(3)):
                pass
            nested = False
        except RuntimeError:
            nested = True
    after = CH.original_functions()
    swapped = all(a is not d for sid in before for (_n, a), (_m, d) in zip(before[sid], during[sid]))
    restored = all(a is b for sid in before for (_n, a), (_m, b) in zip(before[sid], after[sid]))
    copies = {sid: [n for n, _ in v] for sid, v in before.items()}
    ok = swapped and restored and nested and len(copies["P1"]) >= 2 and ad.restored
    try:
        CH.PolicyChartAdapter(np.diag([1.0, 1.0, -1.0]))
        improper = False
    except ValueError:
        improper = True
    return ok and improper, {"module_copies": copies, "nesting_refused": nested, "restored": restored,
                             "improper_chart_refused": improper}


def tx_singular():
    out = []
    for g in (np.array([1.0, 0.0, 0.0]), np.array([-1.0, 0.0, 0.0]), np.array([1.0, 1e-8, 0.0])):
        try:
            CH.chart_basis(g)
            out.append(False)
        except CH.ChartSingular:
            out.append(True)
    ok_near = CH.chart_basis(np.array([1.0, 1e-3, 0.0]))["projected_baseline_norm"] > SP.CHART_SINGULAR_MIN
    return all(out) and ok_near, {"singular_refused": out}


def run_all() -> dict:
    suite = FX.analytic_suite()
    tests = {"01_chart_basis": t01_basis(), "02_centre_gaze": t02_centre(), "03_direction_roundtrip": t03_direction_roundtrip(),
             "04_point_roundtrip": t04_point_roundtrip(), "05_distance_invariant": t05_distance(),
             **covariance_tests(suite),
             "11_fake_local_baseline_refused": t11_fake_local_refused(),
             "12_world_local_known_directions": t12_known_directions(),
             "13_world_calibration_fixed_head": t13_world_calibration_fixed_head(),
             "16_selection_deterministic": t16_selection_rule(), "17_selection_name_catalog_refused": t17_name_refused(),
             "18_h0_fusion_accepted": t18_fusion(), "19_local_frame_fusion_refused": t19_local_frame_refused(),
             "20_second_action_refused": t20_second_action_refused(),
             "x1_adapter_mechanics": tx_adapter_mechanics(), "x2_chart_singularity_stop": tx_singular(),
             "x3_euclidean_frame_invariance": (suite["chart_only_off_axis"]["pass"], suite["chart_only_off_axis"])}
    res = {k: {"pass": bool(v[0]), "detail": CORE.jsonable(v[1])} for k, v in tests.items()}
    failed = [k for k, v in res.items() if not v["pass"]]
    return {"schema": "NS1b-synthetic-v1", "truth": SP.TRUTH_DERIVED, "tests": res, "failed": failed,
            "count": len(res), "analytic_suite": CORE.jsonable(suite),
            "marker": "NS1B_SYNTHETIC_PASS" if not failed else "NS1B_SYNTHETIC_FAIL"}


if __name__ == "__main__":
    r = run_all()
    for k, v in r["tests"].items():
        print(f"[ns1b-synthetic] {'PASS' if v['pass'] else 'FAIL'} {k}")
    print(f"[ns1b-synthetic] {r['marker']} {r['count'] - len(r['failed'])}/{r['count']}")
    print(json.dumps({k: v["detail"] for k, v in r["tests"].items() if not v["pass"]}, default=str)[:3000])
