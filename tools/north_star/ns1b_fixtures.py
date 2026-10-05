"""North Star-1b: coordinate-covariance known answers (contract section 8), established before NS1a data is touched.

- K1: the accepted FSG6f / Cyclopean self-test fixtures and the accepted gate function on an analytic state;
- K2, K3, K3q: accepted Controller-01 replay states of object 112 (FSG6f continue; FSG6f no_frontier -> Cyclopean
  fixation; QUIET), rebuilt from the accepted run's name-free saved files;
- K4: the accepted Controller-02 final-residue gate verdict of object 210;
- rigid rotations about the physical baseline axis (8b), projection invariance (8c) and the gate semantics (8d);
- chart-only covariance under general (off-axis) rotations.

The replay never opens the Controller-01 ``actions.json``, ``result.json``, ``manifest.json``, catalog, seeds or
evaluation files (they carry object names or evaluation truth); it reads each object's ``trajectory.partial.json``
(name-free; identical to the accepted trajectories), the saved acquisitions and patches, and the Controller-02
``final-residue.json``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1b_chart as CH  # noqa: E402
import ns1b_core as CORE  # noqa: E402
import ns1b_spec as SP  # noqa: E402

FILES_READ: dict[str, str] = {}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _read_json(path: Path):
    path = Path(path)
    FILES_READ[str(path)] = _sha(path)
    return json.loads(path.read_text())


def _npz(path: Path) -> dict:
    path = Path(path)
    FILES_READ[str(path)] = _sha(path)
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def files_digest(files: dict[str, str]) -> str:
    lines = "".join(f"{Path(p).relative_to(SP.SHARED) if Path(p).is_relative_to(SP.SHARED) else p} {h}\n"
                    for p, h in sorted(files.items()))
    return hashlib.sha256(lines.encode()).hexdigest()


def _modules():
    CH.ensure_policy_modules()
    import fsg6f_frontier as FR
    import fsg6f_public as PUB
    from fov3d.experiments.classroom_oracle import controller01 as c01, controller02 as c02x, epistemic
    return FR, PUB, c01, c02x, epistemic._legacy_impl     # the sealed module (private helpers included)


def _verdict(passed: bool, **kw) -> dict:
    return {"pass": bool(passed), **kw}


# ------------------------------------------------------------------ K1: analytic fixtures
def k1_fsg6f_cases() -> list[dict]:
    """The accepted ``fsg6f_frontier.self_test`` choose_next fixtures and their known answers."""
    FR, PUB, *_ = _modules()
    from fsg_geometry import make_calibration
    n = 128
    sup = np.ones((n, n), bool)
    cal = make_calibration("small", 0.0, 0.0, PUB.VERGENCE_DISTANCE_M)
    full = np.full((n, n), PUB.OBJECT_ID, np.int32)
    strip = FR._rolled_strip_mask(n, PUB.OBJECT_ID, PUB.BACKGROUND_ID)
    rstrip = strip.copy()
    rstrip[:, -12:] = PUB.BACKGROUND_ID
    inset = np.full((n, n), PUB.OBJECT_ID, np.int32)
    q = 12
    inset[:q, :] = PUB.BACKGROUND_ID
    inset[-q:, :] = PUB.BACKGROUND_ID
    inset[:, :q] = PUB.BACKGROUND_ID
    inset[:, -q:] = PUB.BACKGROUND_ID
    pa, pb = FR._xyz_patch((-11, 1), (-11, 1)), FR._xyz_patch((-1, 11), (-1, 11))
    down, small = FR._xyz_patch((-11, 1), (-1, 11)), FR._xyz_patch((-5, 5), (-5, 5))
    bg = np.full((n, n), PUB.BACKGROUND_ID, np.int32)
    hist_bg = [{"calibration": cal, "instance_L": bg, "raw_support_L": sup, "instance_R": bg, "raw_support_R": sup}]
    case = lambda name, l, r, m, hist, want: {"name": name, "calibration": cal, "L": l, "R": r, "map": m,  # noqa: E731
                                             "history": hist, "want": want}
    return [case("a_map_lower_left", full, full, pa, [], [5.0, 5.0]),
            case("b_map_upper_right", full, full, pb, [], [-5.0, -5.0]),
            case("c1_strip_eye_LR", strip, rstrip, pa, [], "eye_swap"),
            case("c2_strip_eye_RL", rstrip, strip, pa, [], "eye_swap"),
            case("c_symmetric_strip", strip, strip, pa, [], [5.0, 5.0]),
            case("d_down_right_regression", strip, strip, down, [], "not_[5,-5]"),
            case("z_inset_boundary_stop", inset, inset, small, [], "stop"),
            case("h_background_history", full, full, pa, hist_bg, None)]


def _choose(case: dict, cal: dict, m: np.ndarray, hist: list) -> dict:
    FR, *_ = _modules()
    return FR.choose_next(0.0, 0.0, cal, case["L"], np.ones(case["L"].shape, bool), case["R"],
                          np.ones(case["R"].shape, bool), m, [(0.0, 0.0)], hist)


def k1_fsg6f() -> dict:
    """Identity reproduction (exact) and the accepted known answers, then baseline rotations (8b)."""
    out = {"cases": [], "rotations": []}
    ok = True
    results = {}
    for case in k1_fsg6f_cases():
        direct = CORE.jsonable(_choose(case, case["calibration"], case["map"], case["history"]))
        with CH.PolicyChartAdapter(np.eye(3), label=f"K1 identity {case['name']}") as ad:
            adapted = CORE.jsonable(_choose(case, case["calibration"], case["map"], case["history"]))
        diffs = CORE.compare(direct, adapted, 0.0)
        results[case["name"]] = direct
        want = case["want"]
        if want == "stop":
            known = bool(direct["stop"]) and direct["reason"] == "no_frontier"
        elif want == "not_[5,-5]":
            known = direct["next_gaze_deg"] != [5.0, -5.0]
        elif isinstance(want, list):
            known = direct["next_gaze_deg"] == want
        else:
            known = True
        out["cases"].append({"name": case["name"], "identity_differences": diffs, "known_answer": known,
                             "next_gaze_deg": direct["next_gaze_deg"], "reason": direct["reason"],
                             "candidates": len(direct["candidates"]), "P1_calls": ad.calls["P1"]})
        ok &= (not diffs) and known and ad.calls["P1"] > 0
    eye = results["c1_strip_eye_LR"]["next_gaze_deg"] == results["c2_strip_eye_RL"]["next_gaze_deg"]
    out["eye_swap_invariant"] = eye
    ok &= eye
    for beta in SP.BASELINE_ROTATIONS_DEG:
        q = CH.rot_x(beta)
        ch = CH.chart_basis(q @ np.array([0.0, 0.0, -1.0]))
        r = ch["R_HC"]
        rec = {"beta_deg": beta, "chart_equals_Q": float(np.abs(r - q).max()), "cases": []}
        rok = rec["chart_equals_Q"] <= 1e-15
        for case in k1_fsg6f_cases():
            calq = CH.rotate_calibration(case["calibration"], q)
            hist = [{**h, "calibration": CH.rotate_calibration(h["calibration"], q)} for h in case["history"]]
            with CH.PolicyChartAdapter(r, label=f"K1 rotation {beta} {case['name']}"):
                local = CORE.jsonable(_choose(case, calq, CH.to_chart(case["map"] @ q.T, r), hist))
            base = results[case["name"]]
            diffs, flip = CORE.explain_voxel_flip(CORE.compare(base, local, SP.FLOAT_TOL),
                                                  CH.to_chart(case["map"] @ q.T, r))
            world = None
            if local["next_gaze_deg"] is not None:
                _y, _p, d = CH.local_to_world_gaze(*local["next_gaze_deg"], r)
                world = float(np.abs(d - q @ CH.gaze_direction(*base["next_gaze_deg"])).max())
            inv = CORE.inversions(base["candidates"], local["candidates"])
            rec["cases"].append({"name": case["name"], "differences": diffs, "tie_inversions": inv,
                                 "voxel_boundary_flip": flip, "world_proposal_error": world})
            rok &= (not diffs) and (world is None or world <= 1e-12)
        rec["pass"] = bool(rok)
        out["rotations"].append(rec)
        ok &= rok
    out["pass"] = bool(ok)
    return out


def k1_frontier_state_units() -> dict:
    """The accepted frontier-state unit controls (map resolution, boundary history, eye swap), identity + rotation."""
    FR, PUB, *_ = _modules()
    from fsg_geometry import make_calibration
    n = 128
    sup = np.ones((n, n), bool)
    cal = make_calibration("small", 0.0, 0.0, PUB.VERGENCE_DISTANCE_M)
    full = np.full((n, n), PUB.OBJECT_ID, np.int32)
    bg = np.full((n, n), PUB.BACKGROUND_ID, np.int32)
    target = np.array([[0.0, 0.0, -2.10]])
    source = np.array([[-PUB.SURFACE_FRONTIER["lookahead_m"], 0.0, -2.10]])
    mapped = np.vstack([source, target + np.array([[0.005, 0.0, 0.0]])])
    h = lambda l, r: [{"calibration": cal, "instance_L": l, "raw_support_L": sup, "instance_R": r,  # noqa: E731
                       "raw_support_R": sup}]
    units = [("background_resolves", source, h(bg, bg), "boundary"), ("object_stays_open", source, h(full, full), "open"),
             ("mapped_resolves", mapped, h(bg, bg), "map"), ("mix_LR", source, h(full, bg), "open"),
             ("mix_RL", source, h(bg, full), "open")]
    out, ok = [], True
    for name, m, hist, want in units:
        st = FR.classify_frontier_state({"target_xyz_h": target}, m, hist)
        with CH.PolicyChartAdapter(np.eye(3)):
            si = FR.classify_frontier_state({"target_xyz_h": target}, m, hist)
        got = "map" if st["map_resolved"][0] else "boundary" if st["boundary_resolved"][0] else "open"
        same = all(np.array_equal(st[k], si[k]) for k in ("map_resolved", "boundary_resolved", "open"))
        rot = []
        for beta in SP.BASELINE_ROTATIONS_DEG:
            q = CH.rot_x(beta)
            r = CH.chart_basis(q @ np.array([0.0, 0.0, -1.0]))["R_HC"]
            hq = [{**x, "calibration": CH.rotate_calibration(x["calibration"], q)} for x in hist]
            with CH.PolicyChartAdapter(r):
                sr = FR.classify_frontier_state({"target_xyz_h": CH.to_chart(target @ q.T, r)},
                                                CH.to_chart(m @ q.T, r), hq)
            rot.append(all(np.array_equal(st[k], sr[k]) for k in ("map_resolved", "boundary_resolved", "open")))
        out.append({"unit": name, "state": got, "known_answer": got == want, "identity_equal": same,
                    "rotations_equal": rot})
        ok &= got == want and same and all(rot)
    return _verdict(ok, units=out)


def k1_cyclopean() -> dict:
    """(a) the accepted Cyclopean self-test bay fixture; (b) an add_observation fixture exercising P2."""
    FR, PUB, c01, c02x, EP = _modules()
    from fsg_geometry import make_calibration
    ev = EP.make_evidence()
    yaw, pitch = np.linspace(-4.0, 4.0, 80), np.linspace(-3.0, 3.0, 60)
    Y, P = np.meshgrid(yaw, pitch)
    rr = 2.0
    xyz = np.c_[rr * np.cos(np.radians(P.ravel())) * np.sin(np.radians(Y.ravel())), rr * np.sin(np.radians(P.ravel())),
                -rr * np.cos(np.radians(P.ravel())) * np.cos(np.radians(Y.ravel()))]
    yy0, xx0, _ = EP._cells(ev, np.array([-8.0]), np.array([-7.0]))
    yy1, xx1, _ = EP._cells(ev, np.array([8.0]), np.array([7.0]))
    ev.seen_any[int(yy0[0]):int(yy1[0]) + 1, int(xx0[0]):int(xx1[0]) + 1] = True
    yc, xc, _ = EP._cells(ev, np.array([4.2]), np.array([0.0]))
    ev.seen_any[int(yc[0]) - 3:int(yc[0]) + 4, int(xc[0]):int(xc[0]) + 50] = False
    a_direct = CORE.jsonable(EP.choose_next(ev, xyz, []))
    with CH.PolicyChartAdapter(np.eye(3)):
        a_id = CORE.jsonable(EP.choose_next(ev, xyz, []))
    a_known = (not a_direct["stop"]) and a_direct["reason"] == "epistemic_fixation"
    a_rot = []
    for beta in SP.BASELINE_ROTATIONS_DEG:
        q = CH.rot_x(beta)
        r = CH.chart_basis(q @ np.array([0.0, 0.0, -1.0]))["R_HC"]
        with CH.PolicyChartAdapter(r):
            a_rot.append(CORE.compare(a_direct, CORE.jsonable(EP.choose_next(ev, CH.to_chart(xyz @ q.T, r), [])),
                                      SP.FLOAT_TOL))
    # (b) evidence from a completed binocular look through P2, then the handoff
    n = 128
    cal = make_calibration("small", 0.0, 0.0, PUB.VERGENCE_DISTANCE_M)
    sup = np.ones((n, n), bool)
    ids = np.full((n, n), PUB.BACKGROUND_ID, np.int32)
    ids[40:90, 30:80] = PUB.OBJECT_ID
    valid = ids == PUB.OBJECT_ID
    m = FR._xyz_patch((-3, 3), (-3, 3))

    def evidence_and_choice(calib, mm, r):
        e = EP.make_evidence()
        with CH.PolicyChartAdapter(r) as ad:
            EP.add_observation(e, calib, ids, sup, ids, sup, valid, PUB.OBJECT_ID)
            d = CORE.jsonable(EP.choose_next(e, mm, [(0.0, 0.0)]))
        return e, d, ad.calls["P2"]
    e0 = EP.make_evidence()
    EP.add_observation(e0, cal, ids, sup, ids, sup, valid, PUB.OBJECT_ID)
    b_direct = CORE.jsonable(EP.choose_next(e0, m, [(0.0, 0.0)]))
    e1, b_id, p2 = evidence_and_choice(cal, m, np.eye(3))
    arrays = ("seen_any", "seen_target", "seen_nontarget", "target_depth_valid")
    b_same = all(np.array_equal(getattr(e0, k), getattr(e1, k)) for k in arrays) and not CORE.compare(b_direct, b_id, 0.0)
    b_rot = []
    for beta in SP.BASELINE_ROTATIONS_DEG:
        q = CH.rot_x(beta)
        r = CH.chart_basis(q @ np.array([0.0, 0.0, -1.0]))["R_HC"]
        e2, d2, _ = evidence_and_choice(CH.rotate_calibration(cal, q), CH.to_chart(m @ q.T, r), r)
        b_rot.append({"evidence_equal": all(np.array_equal(getattr(e0, k), getattr(e2, k)) for k in arrays),
                      "differences": CORE.compare(b_direct, d2, SP.FLOAT_TOL)})
    ok = (not CORE.compare(a_direct, a_id, 0.0)) and a_known and not any(a_rot) and b_same and p2 > 0 and \
        all(x["evidence_equal"] and not x["differences"] for x in b_rot)
    return _verdict(ok, bay={"next_gaze_deg": a_direct["next_gaze_deg"], "reason": a_direct["reason"],
                             "known_answer": a_known, "identity_equal": not CORE.compare(a_direct, a_id, 0.0),
                             "rotation_differences": a_rot},
                    add_observation={"identity_equal": b_same, "P2_calls": p2, "reason": b_direct["reason"],
                                     "next_gaze_deg": b_direct["next_gaze_deg"], "rotations": b_rot,
                                     "seen_any_cells": int(e0.seen_any.sum())})


def k1_gate() -> dict:
    """The accepted gate function on an analytic FSG6f state: identity (accepted sensor) and a rotated chart with the
    real fixed-head sensor at the world gaze (8d), against the fake local-baseline calibration."""
    FR, PUB, c01, c02x, _EP = _modules()
    from fov3d.control import integrated as ic
    import fsg_geometry as FG
    case = k1_fsg6f_cases()[0]
    cal, m = case["calibration"], case["map"]
    n = case["L"].shape[0]
    state = {"ids_left": case["L"], "ids_right": case["R"], "raw_support_L": np.ones((n, n), bool),
             "raw_support_R": np.ones((n, n), bool)}
    head_r, head_o = FG.HEAD_R_WH, FG.HEAD_ORIGIN_W

    def gate(r, calib, mm, sensor):
        with CH.PolicyChartAdapter(r, sensor) as ad:
            d = FR.choose_next(0.0, 0.0, calib, state["ids_left"], state["raw_support_L"], state["ids_right"],
                               state["raw_support_R"], mm, [(0.0, 0.0)], [])
            prop = ic.ProbeResult(ic.Observe(PUB.OBJECT_ID, tuple(d["next_gaze_deg"]), c01.VERGENCE, c01.FOCUS, "fsg6f"))
            v = c02x.final_look_gate_v1(proposal=prop, decision=d, geometry=mm, gaze=(0.0, 0.0), calibration=calib,
                                        state=state, history=[], visited=[(0.0, 0.0)], profile="small",
                                        head_r_wh=head_r, head_origin_w=head_o, target_id=PUB.OBJECT_ID)
        return d, v, ad
    d0 = FR.choose_next(0.0, 0.0, cal, state["ids_left"], state["raw_support_L"], state["ids_right"],
                        state["raw_support_R"], m, [(0.0, 0.0)], [])
    prop0 = ic.ProbeResult(ic.Observe(PUB.OBJECT_ID, tuple(d0["next_gaze_deg"]), c01.VERGENCE, c01.FOCUS, "fsg6f"))
    v0 = c02x.final_look_gate_v1(proposal=prop0, decision=d0, geometry=m, gaze=(0.0, 0.0), calibration=cal,
                                 state=state, history=[], visited=[(0.0, 0.0)], profile="small", head_r_wh=head_r,
                                 head_origin_w=head_o, target_id=PUB.OBJECT_ID)
    _d, vi, adi = gate(np.eye(3), cal, m, CH.accepted_sensor)
    ident = CORE.compare({"a": v0.admissible, "r": v0.reason, "d": CORE.jsonable(dict(v0.detail))},
                         {"a": vi.admissible, "r": vi.reason, "d": CORE.jsonable(dict(vi.detail))}, SP.FLOAT_TOL)
    # rotated chart: the real baseline-projected sensor at the world gaze, both sides
    _d, vb, _ = gate(np.eye(3), cal, m, CH.baseline_projected_sensor)
    rots = []
    for beta in SP.BASELINE_ROTATIONS_DEG:
        q = CH.rot_x(beta)
        r = CH.chart_basis(q @ np.array([0.0, 0.0, -1.0]))["R_HC"]
        _dq, vq, adq = gate(r, CH.rotate_calibration(cal, q), CH.to_chart(m @ q.T, r), CH.baseline_projected_sensor)
        pc = dict(vq.detail)["predicted_calibration"]
        local = adq.p3_log[0]["local_gaze_deg"]
        real = CH.baseline_projected_sensor("small", *adq.p3_log[0]["world_gaze_deg"], head_r, head_o)
        fake = CH.baseline_projected_sensor("small", *local, head_r, head_o)
        rots.append({"beta_deg": beta,
                     "differences": CORE.compare({"a": vb.admissible, "r": vb.reason,
                                                  "d": CORE.jsonable(dict(vb.detail))},
                                                 {"a": vq.admissible, "r": vq.reason,
                                                  "d": CORE.jsonable(dict(vq.detail))}, SP.FLOAT_TOL,
                                                 skip=("predicted_calibration",)),
                     "p3_is_real_world_sensor": CORE.calibration_matches(pc, real),
                     "p3_is_fake_local": CORE.calibration_matches(pc, fake),
                     "fixed_head": CORE.fixed_head(pc, head_r, head_o)["ok"]})
    ok = (not ident) and adi.calls["P3"] == 1 and all(not x["differences"] and x["p3_is_real_world_sensor"]
                                                      and not x["p3_is_fake_local"] and x["fixed_head"] for x in rots)
    return _verdict(ok, identity_differences=ident, verdict=[v0.admissible, v0.reason],
                    counts=CORE.jsonable(dict(v0.detail).get("counts")), rotations=rots,
                    baseline_projected_verdict=[vb.admissible, vb.reason])


# ------------------------------------------------------------------ K2-K4: accepted replay states
def trajectory_files() -> list[Path]:
    """The 25 name-free per-object trajectories (listed outside any guard: a guard refuses directory listings)."""
    return sorted((SP.C01_RUN / "objects").glob("instance_*/trajectory.partial.json"))


def c01_rows(files: list[Path] | None = None) -> list[dict]:
    rows = []
    for f in (trajectory_files() if files is None else files):
        obj = int(f.parent.name.split("_")[1])
        for t in _read_json(f):
            rows.append({"target_id": obj, **t})
    rows.sort(key=lambda r: int(r["global_step"]))
    if [int(r["global_step"]) for r in rows] != list(range(len(rows))):
        raise RuntimeError("the accepted Controller-01 trajectories do not form one global action sequence")
    return rows


def rebuild(obj: int, after_step: int, rows: list[dict]) -> dict:
    """Controller-01's own-target context and effective geometry of ``obj`` after ``after_step`` (accepted code)."""
    from fov3d.control import object_policy
    from fov3d.experiments.classroom_oracle import config as public, controller01 as c01, epistemic, matcher
    from fov3d.reconstruction import surface_map
    from fov3d.reconstruction.measurement_memory import InstanceMeasurementMemory, effective_target_geometry
    ctx = c01.LocalPolicyContext(obj)
    memory = InstanceMeasurementMemory()
    measured = 0
    bad = []
    for a in rows:
        s = int(a["global_step"])
        if s > after_step:
            break
        i, k = int(a["target_id"]), int(a["step"])
        odir = SP.C01_RUN / f"objects/instance_{i:04d}"
        patch = _npz(odir / f"patches/fix_{k:02d}.npz")
        added = memory.append_patch(patch, source_global_index=s, source_active_target_id=i)
        measured += int(added.get(obj, 0))
        if i != obj:
            continue
        adir = odir / f"acquisitions/fix_{k:02d}"
        c = _read_json(adir / "calibration.json")
        rec, _meta, st = matcher.compute(c, _npz(adir / "oracle_observation.npz"))
        if not (np.array_equal(np.asarray(rec["xyz_h"], np.float32), patch["xyz_h"], equal_nan=True)
                and np.array_equal(np.asarray(rec["valid"], bool), patch["valid"])
                and np.array_equal(np.asarray(rec["instance_id"], np.int32), patch["instance_id"])):
            bad.append(s)
        tp = int((np.asarray(rec["valid"], bool) & (np.asarray(rec["instance_id"]) == obj)).sum())
        p = surface_map.Patch(patch_id=f"fix_{k:02d}", xyz_h=rec["xyz_h"], rgb=rec["rgb_left"],
                              instance_id=rec["instance_id"])
        if ctx.surface_map is None:
            if tp >= public.MIN_INITIAL_TARGET_POINTS:
                ctx.surface_map = surface_map.initialize(p, obj)
        elif tp >= public.MIN_INITIAL_TARGET_POINTS:
            ctx.surface_map, _m = surface_map.fuse(ctx.surface_map, p, obj, float(public.FUSION["association_radius_m"]),
                                                   float(public.FUSION["hash_cell_m"]))
        epistemic.add_observation(ctx.evidence, c, st["ids_left"], st["raw_support_L"], st["ids_right"],
                                  st["raw_support_R"], rec["valid"], obj)
        ctx.history.append(object_policy.history_entry(
            calibration=c, instance_L=st["ids_left"], raw_support_L=st["raw_support_L"], instance_R=st["ids_right"],
            raw_support_R=st["raw_support_R"], target_object_id=obj))
        gaze = (float(a["gaze_deg"][0]), float(a["gaze_deg"][1]))
        ctx.visited.append(gaze)
        ctx.gaze, ctx.calibration, ctx.state = gaze, c, st
    if bad:
        raise RuntimeError(f"replayed patches differ from the saved ones at steps {bad}")
    map_xyz = np.empty((0, 3)) if ctx.surface_map is None else np.asarray(ctx.surface_map.xyz_h, np.float64)
    geometry = effective_target_geometry(map_xyz, memory.snapshot(obj).xyz_h)
    return {"ctx": ctx, "geometry": geometry, "revision": [len(ctx.visited), measured]}


def k_replay(name: str, rows: list[dict], rotate: bool = True) -> dict:
    """Identity reproduction of the saved accepted decision (exact), then baseline rotations (R_HC = Q)."""
    _FR, _PUB, c01, _c02x, _EP = _modules()
    spec = SP.K_FIXTURES[name]
    obj = int(spec["object"])
    st = rebuild(obj, int(spec["after_global_step"]), rows)
    ctx, geo = st["ctx"], st["geometry"]
    rev_ok = st["revision"] == list(spec["revision"])
    res_d, dec_d = c01.probe_local_policy(ctx, geo)
    with CH.PolicyChartAdapter(np.eye(3), label=f"{name} identity") as ad:
        res_a, dec_a = c01.probe_local_policy(ctx, geo)
    direct, adapted = CORE.jsonable(dec_d), CORE.jsonable(dec_a)
    ident = CORE.compare(direct, adapted, 0.0) + CORE.compare(CORE.jsonable(dict(res_d.detail)),
                                                               CORE.jsonable(dict(res_a.detail)), 0.0)
    if spec["kind"] == "quiet":
        accepted = SP.K3Q_SUMMARY
        against = CORE.compare(accepted, {"state": res_d.state.value, **CORE.jsonable(dict(res_d.detail))}, 0.0)
    else:
        saved = next(t for t in rows if int(t["target_id"]) == obj and int(t["step"]) == int(spec["trajectory_step"]))
        against = CORE.compare(saved["proposal_decisions"], direct, 0.0)
    out = {"name": name, "object": obj, "after_global_step": spec["after_global_step"], "kind": spec["kind"],
           "revision": st["revision"], "revision_matches": rev_ok, "effective_points": int(len(geo)),
           "state": res_d.state.value, "summary": CORE.jsonable(dict(res_d.detail)),
           "identity_differences": ident, "differences_from_accepted_record": against,
           "adapter_calls": ad.calls, "rotations": []}
    ok = rev_ok and not ident and not against
    if rotate:
        for beta in SP.BASELINE_ROTATIONS_DEG:
            q = CH.rot_x(beta)
            ctx_q = CORE.copy_ctx(ctx)
            ctx_q.calibration = CH.rotate_calibration(ctx.calibration, q)
            ctx_q.history = [{**h, "calibration": CH.rotate_calibration(h["calibration"], q)} for h in ctx.history]
            with CH.PolicyChartAdapter(q, label=f"{name} rotation {beta}"):
                res_q, dec_q = c01.probe_local_policy(ctx_q, CH.to_chart(geo @ q.T, q))
            dq = CORE.jsonable(dec_q)
            diffs = CORE.compare(direct, dq, SP.FLOAT_TOL)
            world = None
            if res_d.action is not None and res_q.action is not None:
                _y, _p, d = CH.local_to_world_gaze(*res_q.action.gaze_yaw_pitch_deg, q)
                world = float(np.abs(d - q @ CH.gaze_direction(*res_d.action.gaze_yaw_pitch_deg)).max())
            out["rotations"].append({"beta_deg": beta, "differences": diffs, "world_proposal_error": world})
            ok &= (not diffs) and (world is None or world <= 1e-12)
    out["pass"] = bool(ok)
    return out


def k4_gate(rows: list[dict]) -> dict:
    """The accepted Controller-02 final-residue verdict of object 210, reproduced through the identity adapter."""
    _FR, _PUB, c01, c02x, _EP = _modules()
    spec = SP.K_FIXTURES["K4"]
    obj = int(spec["object"])
    t0 = time.perf_counter()
    st = rebuild(obj, int(spec["after_global_step"]), rows)
    ctx, geo = st["ctx"], st["geometry"]
    t1 = time.perf_counter()
    with CH.PolicyChartAdapter(np.eye(3), CH.accepted_sensor, label="K4 identity") as ad:
        res, dec = c01.probe_local_policy(ctx, geo)
        v = c02x.final_look_gate_v1(proposal=res, decision=dec.get("fsg6f_decision"), geometry=geo, gaze=ctx.gaze,
                                    calibration=ctx.calibration, state=ctx.state, history=ctx.history,
                                    visited=list(ctx.visited), profile="full",
                                    head_r_wh=ctx.calibration["head_R_wh"],
                                    head_origin_w=ctx.calibration["head_origin_w_m"], target_id=obj)
    residue = _read_json(SP.C02_RUN / SP.C02_FINAL_RESIDUE)["residue_decisions"]
    acc = next(r for r in residue if int(r["object"]) == obj)
    mine = {"admissible": bool(v.admissible), "reason": v.reason, "detail": CORE.jsonable(dict(v.detail))}
    acc_detail = {k: val for k, val in acc["detail"].items() if k not in ("revision", "probe_summary")}
    diffs = CORE.compare({"admissible": acc["admissible"], "reason": acc["reason"], "detail": acc_detail}, mine,
                         SP.FLOAT_TOL)
    gaze_ok = res.action is not None and list(res.action.gaze_yaw_pitch_deg) == list(spec["gaze"])
    ok = (st["revision"] == list(spec["revision"]) and not diffs and gaze_ok and v.reason == spec["verdict"]
          and ad.calls["P3"] == 1)
    return _verdict(ok, object=obj, revision=st["revision"], revision_matches=st["revision"] == list(spec["revision"]),
                    effective_points=int(len(geo)), proposal_gaze_deg=None if res.action is None else
                    list(res.action.gaze_yaw_pitch_deg), verdict=[bool(v.admissible), v.reason],
                    counts=mine["detail"].get("counts"), differences_from_accepted_record=diffs,
                    accepted_residue_global_step=acc["global_step"], adapter_calls=ad.calls,
                    seconds={"rebuild": round(t1 - t0, 2), "probe_and_gate": round(time.perf_counter() - t1, 2)})


# ------------------------------------------------------------------ 8c: projection invariance; chart-only off-axis tests
def projection_invariance(calibrations: list[dict], r_hc: np.ndarray, points_h0: np.ndarray) -> dict:
    FR, *_ = _modules()
    import tools.classroom_oracle1_epistemic as EPL
    pts = np.asarray(points_h0, np.float64)
    pc = CH.to_chart(pts, r_hc)
    rows, ok = [], True
    for c in calibrations:
        for side in ("L", "R"):
            uv0, z0 = FR._project_rectified_core(c, pts, side)
            with CH.PolicyChartAdapter(r_hc):
                uv1, z1 = FR._project_rectified_core(c, pc, side)
                d1 = EPL._rectified_core_directions_h(c, side)
            d0 = EPL._rectified_core_directions_h(c, side)
            uvn, _zn = FR._project_rectified_core(c, pc, side)     # negative control: C points as if H0
            du = float(np.nanmax(np.abs(uv1 - uv0)))
            dz = float(np.nanmax(np.abs(z1 - z0)))
            neg = float(np.nanmax(np.abs(uvn - uv0)))
            dd = float(np.abs(d1 - CH.to_chart(d0.reshape(-1, 3), r_hc).reshape(d0.shape)).max())
            rows.append({"gaze_deg": list(c["gaze_yaw_pitch_deg"]), "side": side, "uv_difference_px": du,
                         "depth_difference_m": dz, "negative_control_px": neg, "P2_direction_difference": dd})
            ok &= du <= SP.FLOAT_TOL and dz <= SP.FLOAT_TOL and dd <= 1e-12 and neg > 1.0
    return _verdict(ok, rows=rows)


def chart_only_off_axis(m_h0: np.ndarray, calibration: dict) -> dict:
    """Frontier extraction, 12-mm map resolution and Cyclopean map support under general rotations Q, R_HC = Q."""
    FR, _PUB, _c01, _c02x, EP = _modules()
    out, ok = [], True
    f0 = FR.extract_frontier(m_h0, 0.0, 0.0, calibration)
    t0 = f0["target_xyz_h"]
    m0 = FR._target_mapped_mask(t0, m_h0)
    s0 = EP._map_support(EP.make_evidence(), m_h0)[0]
    for ax0, ax1, ax2, ang in SP.OFF_AXIS_ROTATIONS:
        q = CH.rot_axis((ax0, ax1, ax2), ang)
        mq = m_h0 @ q.T
        f1 = FR.extract_frontier(CH.to_chart(mq, q), 0.0, 0.0, calibration)
        same_count = len(f1["strength"]) == len(f0["strength"])
        geo = float(np.abs(f1["target_xyz_h"] - t0).max()) if same_count and len(t0) else 0.0
        m_c = FR._target_mapped_mask(CH.to_chart(t0 @ q.T, q), CH.to_chart(mq, q))
        m_h = FR._target_mapped_mask(t0 @ q.T, mq)
        s1 = EP._map_support(EP.make_evidence(), CH.to_chart(mq, q))[0]
        rec = {"axis": [ax0, ax1, ax2], "angle_rad": ang, "frontier_count_equal": same_count,
               "frontier_target_difference_m": geo, "map_resolution_equal_C": bool(np.array_equal(m0, m_c)),
               "map_resolution_frame_invariant": bool(np.array_equal(m_c, m_h)),
               "cyclopean_support_equal": bool(np.array_equal(s0, s1))}
        out.append(rec)
        ok &= same_count and geo <= SP.FLOAT_TOL and rec["map_resolution_equal_C"] and \
            rec["map_resolution_frame_invariant"] and rec["cyclopean_support_equal"]
    return _verdict(ok, rotations=out, frontier_count=int(len(f0["strength"])))


def analytic_suite() -> dict:
    """Everything analytic (cheap): used by `synthetic`, `covariance` and the checker."""
    FR, PUB, *_ = _modules()
    from fsg_geometry import make_calibration
    cal = make_calibration("small", 0.0, 0.0, PUB.VERGENCE_DISTANCE_M)
    m = FR._xyz_patch((-11, 1), (-11, 1))
    q = CH.rot_x(23.0)
    pts = np.array([[0.05, -0.02, -2.0], [-0.1, 0.08, -2.4], [0.0, 0.0, -1.6], [0.12, 0.1, -3.0]])
    calp = [make_calibration("small", 0.0, 0.0, 2.1), make_calibration("small", 4.0, -3.0, 2.1,
                                                                       tangent_frame="baseline_projected")]
    return {"K1_fsg6f": k1_fsg6f(), "K1_frontier_state": k1_frontier_state_units(), "K1_cyclopean": k1_cyclopean(),
            "K1_gate": k1_gate(), "projection_invariance": projection_invariance(calp, q, pts),
            "chart_only_off_axis": chart_only_off_axis(m, cal)}


def replay_suite(include_k4: bool = True, traj_files: list[Path] | None = None) -> dict:
    FILES_READ.clear()
    rows = c01_rows(traj_files)
    out = {"K2": k_replay("K2", rows), "K3": k_replay("K3", rows), "K3q": k_replay("K3q", rows, rotate=True)}
    if include_k4:
        out["K4"] = k4_gate(rows)
    out["files_read"] = len(FILES_READ)
    out["files_digest"] = files_digest(FILES_READ)
    return out
