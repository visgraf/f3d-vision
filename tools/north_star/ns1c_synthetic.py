"""North Star-1c: synthetic / known-answer tests (contract section 22), analytic data only, before NS1a / NS1b data.

Each test returns (passed, detail).  ``run_all`` returns the report written by the ``synthetic`` stage.
"""
from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "natural_bootstrap", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1b_chart as CH  # noqa: E402
import ns1b_core as B  # noqa: E402
import ns1c_core as CORE  # noqa: E402
import ns1c_spec as SP  # noqa: E402

RNG_SEED = 20261005


def _head():
    import fsg_geometry as FG
    return FG.HEAD_R_WH, FG.HEAD_ORIGIN_W


# ------------------------------------------------------------------ charts (section 7)
def t01_charts_every_nb1c_gaze():
    rows = {}
    for r, y, p in SP.NS1A_RANK_GAZES:
        ch = CORE.chart_record(100 + r, r, (y, p))
        rows[r] = {"ok": ch["checks"]["ok"], "b_perp": ch["projected_baseline_norm"],
                   "seed_local": ch["checks"]["seed_local_yaw_pitch_deg"]}
    singular = []
    for g in (np.array([1.0, 0.0, 0.0]), np.array([-1.0, 0.0, 0.0])):
        try:
            CH.chart_basis(g)
            singular.append(False)
        except CH.ChartSingular:
            singular.append(True)
    ok = all(v["ok"] and v["b_perp"] >= SP.CHART_SINGULAR_MIN for v in rows.values()) and all(singular)
    return ok, {"ranks": rows, "singular_refused": singular}


def t02_local_world_roundtrip():
    worst = 0.0
    for _r, y, p in SP.NS1A_RANK_GAZES:
        r = CH.chart_basis(CH.gaze_direction(y, p))["R_HC"]
        for yl in np.arange(-25.0, 25.1, 5.0):
            for pl in np.arange(-20.0, 20.1, 5.0):
                yw, pw, _ = CH.local_to_world_gaze(float(yl), float(pl), r)
                yb, pb = CH.world_to_local_gaze(yw, pw, r)
                worst = max(worst, abs(yb - yl), abs(pb - pl))
    return worst <= SP.GAZE_ROUNDTRIP_TOL_DEG, {"max_roundtrip_error_deg": worst}


# ------------------------------------------------------------------ eligibility (section 5)
def _ent(k, init, rank, patches, surfels):
    return {"temporary_entity_id": k, "initialized": init, "initialized_at_rank": rank if init else None,
            "contributing_patches": patches, "final_surfels": surfels}


def t03_eligibility_rule():
    ents = [_ent(5, True, 2, 1, 900), _ent(7, True, 6, 2, 9000), _ent(3, True, 1, 1, 400), _ent(9, True, 5, 3, 10 ** 5),
            _ent(11, False, None, 0, 0), _ent(4, True, 1, 1, 150)]
    a = CORE.derive_coherent_set({"entities": ents})
    rng = np.random.default_rng(RNG_SEED)
    perms = [CORE.derive_coherent_set({"entities": [ents[i] for i in rng.permutation(len(ents))]})["coherent_ids"]
             for _ in range(5)]
    ok = (a["coherent_ids"] == [3, 4, 5] and a["deferred_ids"] == [7, 9] and a["outside_ids"] == [11]
          and all(p == [3, 4, 5] for p in perms) and all(r["state"] == SP.DEFERRED_STATE for r in a["deferred"]))
    return ok, {"coherent": a["coherent_ids"], "deferred": a["deferred_ids"], "outside": a["outside_ids"]}


def t04_eligibility_name_refused():
    bad = {"entities": [{**_ent(5, True, 2, 1, 900), "object_name": "pipe"}]}
    try:
        CORE.derive_coherent_set(bad)
        refused = False
    except CORE.EligibilityRefused:
        refused = True
    cat = {"entities": [_ent(5, True, 2, 1, 900)], "catalog": {"5": "x"}}
    try:
        CORE.derive_coherent_set(cat)
        refused_cat = False
    except CORE.EligibilityRefused:
        refused_cat = True
    return refused and refused_cat, {"name_refused": refused, "catalog_refused": refused_cat}


# ------------------------------------------------------------------ scheduler (sections 12-13)
def _scene(states: dict) -> dict:
    out = {}
    for k, lab in states.items():
        st, _, br = lab.partition(":")
        out[str(k)] = {"service": {"state": st, "blocked_reason": br or None, "label": lab}}
    return out


def _decide(current, states):
    ids = sorted(states)
    return CORE.schedule(current, CORE.summaries(_scene(states), ids))


def t05_scheduler_retain():
    d = _decide(172, {9: "ACTIONABLE", 172: "ACTIONABLE", 212: "ACTIONABLE"})
    return d["kind"] == "attend" and d["target_id"] == 172 and d["reason"] == "retain", d


def t06_scheduler_switch():
    fwd = _decide(172, {9: "ACTIONABLE", 172: "QUIET", 202: "QUIET", 212: "ACTIONABLE", 230: "ACTIONABLE"})
    wrap = _decide(172, {9: "QUIET", 12: "ACTIONABLE", 123: "ACTIONABLE", 172: "QUIET", 212: "QUIET"})
    blocked = _decide(172, {9: "QUIET", 172: "BLOCKED:watchdog", 204: "ACTIONABLE"})
    ok = ((fwd["target_id"], fwd["reason"]) == (212, "switch") and (wrap["target_id"], wrap["reason"]) == (12, "switch")
          and (blocked["target_id"], blocked["reason"]) == (204, "switch"))
    return ok, {"forward": fwd["target_id"], "wrap": wrap["target_id"], "after_watchdog": blocked["target_id"]}


def t07_scheduler_quiescence():
    d = _decide(172, {9: "QUIET", 172: "QUIET", 212: "QUIET"})
    ok = d["kind"] == "terminal" and d["terminal"]["type"] == "Stop" and \
        d["terminal"]["reason"] == "global_quiescence" and d["terminal"]["label"] == "COHERENT_SUBSET_QUIESCENT"
    return ok, d


def t08_scheduler_incomplete():
    d = _decide(172, {9: "QUIET", 172: "BLOCKED:watchdog", 212: "QUIET"})
    ok = d["kind"] == "terminal" and d["terminal"]["type"] == "Incomplete" and \
        d["terminal"]["blocked"] == [[172, "watchdog"]] and d["terminal"]["label"] == "COHERENT_SUBSET_INCOMPLETE"
    return ok, d


def t09_watchdog():
    act = {"proposal": {"source": "fsg6f"}, "gate": {"admissible": True}}
    rej = {"proposal": {"source": "fsg6f"}, "gate": {"admissible": False}}
    none = {"proposal": None, "gate": {"admissible": False}}
    wd = SP.WATCHDOG_EXPECTED
    rows = {"actionable_23": CORE.service(act, wd - 1, wd, None)["label"],
            "actionable_24": CORE.service(act, wd, wd, None)["label"],
            "rejected_24": CORE.service(rej, wd, wd, None)["label"],
            "no_proposal_2": CORE.service(none, 2, wd, None)["label"],
            "sticky": CORE.service(none, 3, wd, "watchdog")["label"]}
    ok = rows == {"actionable_23": "ACTIONABLE", "actionable_24": "BLOCKED:watchdog", "rejected_24": "QUIET",
                  "no_proposal_2": "QUIET", "sticky": "BLOCKED:watchdog"}
    return ok, rows


def t10_deferred_id_refused():
    states = {9: "QUIET", 172: "ACTIONABLE"}
    coherent = [9, 172]
    scene = _scene({**states, 110: "QUIET"})
    try:
        CORE.summaries(scene, coherent)
        inserted = False
    except CORE.SchedulerInputRefused:
        inserted = True
    try:
        CORE.summaries(_scene({172: "ACTIONABLE"}), coherent)
        dropped = False
    except CORE.SchedulerInputRefused:
        dropped = True
    return inserted and dropped, {"deferred_inserted_refused": inserted, "coherent_dropped_refused": dropped}


# ------------------------------------------------------------------ physical sensor (section 4)
def t11_fixed_head_fake_local_refused():
    hr, ho = _head()
    out = {}
    for rank in (1, 6):
        _r, y, p = SP.NS1A_RANK_GAZES[rank - 1]
        r = CH.chart_basis(CH.gaze_direction(y, p))["R_HC"]
        local = (-5.0, -10.0)
        yw, pw, _ = CH.local_to_world_gaze(*local, r)
        real = CH.north_star_sensor("full", yw, pw, hr, ho)
        fake = CH.north_star_sensor("full", *local, hr, ho)
        reset = copy.deepcopy(real)
        for e, s in zip(reset["eyes"], (-1.0, 1.0)):
            e["centre_h_m"] = (s * SP.IPD_M / 2 * r[:, 0]).tolist()
        t_real = B.physical_calibration_test(real, local, r, hr, ho)
        t_fake = B.physical_calibration_test(fake, local, r, hr, ho)
        t_reset = B.physical_calibration_test(reset, local, r, hr, ho)
        out[rank] = {"real": t_real["ok"], "fake_refused": not t_fake["ok"], "reset_refused": not t_reset["ok"]}
    return all(all(v.values()) for v in out.values()), out


def t12_first_world_action():
    hr, ho = _head()
    out = {}
    for rank in (1, 6):
        _r, y, p = SP.NS1A_RANK_GAZES[rank - 1]
        ch = CORE.chart_record(1000 + rank, rank, (y, p))
        prop = {"local_gaze_deg": [-5.0, -10.0]}
        plan = CORE.plan_action(prop, ch, hr, ho)
        yw, pw, _ = CH.local_to_world_gaze(-5.0, -10.0, np.asarray(ch["R_HC"]))
        real = CH.north_star_sensor("full", yw, pw, hr, ho)
        out[rank] = {"world_equal": plan["world_gaze_deg"] == [yw, pw],
                     "calibration_is_real_world_sensor": B.calibration_matches(plan["planned_calibration"], real),
                     "physical_test": plan["physical_calibration_test"]["ok"],
                     "roundtrip": plan["roundtrip_error_deg"] <= SP.GAZE_ROUNDTRIP_TOL_DEG,
                     "fixed_head": B.fixed_head(plan["planned_calibration"], hr, ho)["ok"]}
    return all(all(v.values()) for v in out.values()), out


# ------------------------------------------------------------------ fusion (section 16)
def _plane(pid, lo, hi, k, z=-2.0, n=(50, 24)):
    rng = np.random.default_rng(12 + k)
    xy = np.stack(np.meshgrid(np.linspace(lo, hi, n[0]), np.linspace(-.10, .10, n[1])), axis=-1).reshape(-1, 2)
    xyz = np.c_[xy, z * np.ones(len(xy))] + rng.normal(scale=.0004, size=(len(xy), 3))
    return xyz


def t13_target_only_fusion():
    from fov3d.reconstruction import surface_map as SM
    maps = {}
    for k, (lo, hi, z) in {71: (-.28, -.02, -2.0), 72: (-.28, .28, -2.5), 73: (-.10, .10, -1.5)}.items():
        x = _plane("seed", lo, hi, k, z)
        maps[k] = SM.initialize(SM.Patch(f"seed_{k}", x, np.full((len(x), 3), .3), np.full(len(x), k, np.int32)), k)
    before = {k: B.map_arrays(m) for k, m in maps.items()}
    xa, xb, xc = _plane("A", -.12, .12, 71), _plane("B", -.2, .2, 72, -2.5), _plane("C", -.05, .05, 73, -1.5)
    xyz = np.vstack([xa, xb, xc])
    ids = np.r_[np.full(len(xa), 71), np.full(len(xb), 72), np.full(len(xc), 73)].astype(np.int32)
    valid = np.ones(len(xyz), bool)
    patch = CORE.target_patch(xyz, valid, ids, np.full((len(xyz), 3), .5), 71, 3)
    fused, rec = B.fuse_h0(maps[71], patch, 71)
    maps[71] = fused
    after = {k: B.map_arrays(m) for k, m in maps.items()}
    ok = (patch["points"] == len(xa) and np.all(patch["instance_id"] == 71) and patch["patch_id"] == "ns1c_step_03"
          and rec["action"] == "FUSED" and B.maps_equal(before[72], after[72]) and B.maps_equal(before[73], after[73])
          and not B.maps_equal(before[71], after[71]) and np.all(after[71]["instance_id"] == 71))
    return ok, {"target_points": patch["points"], "matched": rec["matched"], "new": rec["new"],
                "incidental_unchanged": [B.maps_equal(before[k], after[k]) for k in (72, 73)]}


def t14_fusion_known_answer():
    from fov3d.reconstruction import surface_map as SM
    a, b = _plane("A", -.28, -.02, 71), _plane("B", -.12, .12, 71)
    m = SM.initialize(SM.Patch("A", a, np.full((len(a), 3), .4), np.full(len(a), 71, np.int32)), 71)
    pb = {"frame": "H0", "patch_id": "B", "xyz_h": b, "rgb": np.full((len(b), 3), .4),
          "instance_id": np.full(len(b), 71, np.int32), "points": int(len(b))}
    m2, rec = B.fuse_h0(m, pb, 71)
    direct, meta = SM.fuse(m, SM.Patch("B", b, pb["rgb"], pb["instance_id"]), 71, 0.012, 0.012)
    small = {**pb, "patch_id": "S", "xyz_h": b[:60], "rgb": pb["rgb"][:60], "instance_id": pb["instance_id"][:60],
             "points": 60}
    _m3, rec3 = B.fuse_h0(m2, small, 71)
    try:
        B.fuse_h0(m, {**pb, "frame": "C"}, 71)
        c_refused = False
    except B.FrameRefused:
        c_refused = True
    ok = (B.maps_equal(B.map_arrays(m2), B.map_arrays(direct)) and rec["matched"] == int(meta["matched"]) > 300
          and rec["new"] == int(meta["new"]) > 300 and rec["replay"]["exact"] and rec3["action"] == "RETAINED_NOT_FUSED"
          and c_refused and rec["radius_m"] == SP.ASSOCIATION_RADIUS_M and rec["hash_cell_m"] == SP.HASH_CELL_M)
    return ok, {"matched": rec["matched"], "new": rec["new"], "undersupported": rec3["action"],
                "chart_frame_refused": c_refused}


def t15_patch_ids_unique():
    from fov3d.reconstruction import surface_map as SM
    ids = [SP.patch_id(k) for k in range(30)]
    a = _plane("A", -.28, -.02, 71)
    m = SM.initialize(SM.Patch(SP.patch_id(0), a, np.full((len(a), 3), .4), np.full(len(a), 71, np.int32)), 71)
    _m2, meta = SM.fuse(m, SM.Patch(SP.patch_id(0), a, np.full((len(a), 3), .4), np.full(len(a), 71, np.int32)), 71,
                        0.012, 0.012)
    ok = len(set(ids)) == len(ids) and "ns1b_action_01" not in ids and meta["duplicate_patch"]
    return ok, {"duplicate_id_detected_by_accepted_fuse": bool(meta["duplicate_patch"])}


# ------------------------------------------------------------------ process (section 18)
def t16_second_target_stop():
    ok_rule = (not CORE.stop_event(172, "FUSED") and CORE.stop_event(212, "FUSED")
               and CORE.stop_event(212, "RETAINED_NOT_FUSED") and not CORE.stop_event(212, None))
    try:
        CORE.require_not_stopped({"stopped": True, "stop": {"global_step": 4}})
        refused = False
    except CORE.ProcessRefused:
        refused = True
    CORE.require_not_stopped({"stopped": False, "stop": None})
    return ok_rule and refused, {"rule": ok_rule, "after_stop_refused": refused}


def t17_global_cap():
    try:
        CORE.require_under_cap(SP.WATCHDOG_EXPECTED, SP.WATCHDOG_EXPECTED)
        capped = False
    except CORE.ProcessRefused:
        capped = True
    CORE.require_under_cap(SP.WATCHDOG_EXPECTED - 1, SP.WATCHDOG_EXPECTED)
    return capped, {"cap": SP.WATCHDOG_EXPECTED, "refused_at_cap": capped}


def t18_scene_closed_forbidden():
    labels = list(SP.TERMINAL_LABELS.values())
    literal = SP.FORBIDDEN_MARKER
    hits = []
    for name in ("ns1c_spec.py", "ns1c_core.py", "ns1c_run.py", "ns1c_render.py", "ns1c_visuals.py"):
        p = HERE / name
        if p.exists():
            tree = ast.parse(p.read_text())
            hits += [f"{name}: {n.value}" for n in ast.walk(tree) if isinstance(n, ast.Constant)
                     and isinstance(n.value, str) and literal in n.value]
    try:
        CORE.terminal_label("Stop")
        stop_ok = CORE.terminal_label("Stop") == "COHERENT_SUBSET_QUIESCENT"
    except AssertionError:
        stop_ok = False
    ok = literal not in labels and not hits and stop_ok
    return ok, {"labels": labels, "literal_hits": hits}


def t19_revision_and_events():
    rec = {"own_looks": 2, "map": {"surfels": 21243}}
    r0 = CORE.revision(rec)
    r1 = CORE.revision({"own_looks": 3, "map": {"surfels": 21243}})
    prev = _scene({9: "QUIET", 172: "ACTIONABLE", 212: "ACTIONABLE"})
    now = _scene({9: "ACTIONABLE", 172: "QUIET", 212: "BLOCKED:watchdog"})
    ev = CORE.refresh_events(prev, now, 3, 172)
    got = sorted((e["event"], e["object"]) for e in ev)
    ok = r0 == [2, 21243] and r0 != r1 and got == [("blocked", 212), ("natural_reactivation", 9), ("quiet", 172)]
    return ok, {"events": got}


def tx_adapter_restores():
    before = CH.original_functions()
    with CH.PolicyChartAdapter(CH.rot_x(30.0)):
        during = CH.original_functions()
    after = CH.original_functions()
    swapped = all(a is not d for sid in before for (_n, a), (_m, d) in zip(before[sid], during[sid]))
    restored = all(a is b for sid in before for (_n, a), (_m, b) in zip(before[sid], after[sid]))
    return swapped and restored, {"swapped": swapped, "restored": restored}


def run_all() -> dict:
    tests = {"01_charts_every_nb1c_gaze": t01_charts_every_nb1c_gaze(), "02_local_world_roundtrip": t02_local_world_roundtrip(),
             "03_eligibility_rule": t03_eligibility_rule(), "04_eligibility_name_refused": t04_eligibility_name_refused(),
             "05_scheduler_retain": t05_scheduler_retain(), "06_scheduler_switch": t06_scheduler_switch(),
             "07_scheduler_quiescence": t07_scheduler_quiescence(), "08_scheduler_incomplete": t08_scheduler_incomplete(),
             "09_watchdog": t09_watchdog(), "10_deferred_id_refused": t10_deferred_id_refused(),
             "11_fixed_head_fake_local_refused": t11_fixed_head_fake_local_refused(),
             "12_first_world_action_real_sensor": t12_first_world_action(),
             "13_target_only_fusion": t13_target_only_fusion(), "14_h0_fusion_known_answer": t14_fusion_known_answer(),
             "15_patch_ids_unique": t15_patch_ids_unique(), "16_second_target_stop": t16_second_target_stop(),
             "17_global_cap": t17_global_cap(), "18_scene_closed_forbidden": t18_scene_closed_forbidden(),
             "19_revision_and_events": t19_revision_and_events(), "x1_adapter_restores": tx_adapter_restores()}
    res = {k: {"pass": bool(v[0]), "detail": CORE.jsonable(v[1])} for k, v in tests.items()}
    failed = [k for k, v in res.items() if not v["pass"]]
    return {"schema": "NS1c-synthetic-v1", "truth": SP.TRUTH_DERIVED, "tests": res, "failed": failed,
            "count": len(res), "marker": "NS1C_SYNTHETIC_PASS" if not failed else "NS1C_SYNTHETIC_FAIL"}


if __name__ == "__main__":
    r = run_all()
    for k, v in r["tests"].items():
        print(f"[ns1c-synthetic] {'PASS' if v['pass'] else 'FAIL'} {k}")
    print(f"[ns1c-synthetic] {r['marker']} {r['count'] - len(r['failed'])}/{r['count']}")
    print(json.dumps({k: v["detail"] for k, v in r["tests"].items() if not v["pass"]}, default=str)[:3000])
