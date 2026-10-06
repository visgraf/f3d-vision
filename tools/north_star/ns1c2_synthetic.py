"""North Star-1c2: synthetic / known-answer tests (contract section 7, stage `synthetic`), analytic data only.

B4a NORMAL classification (with gating mutants refused by the guard), B4b the accepted scheduler, B4c the ordinary
budget, B4d RESIDUE only, the differential equivalence of the resumable adapter with the accepted ``run_controller02``
(driven from the seeds and resumed from JSON), and the inherited NS1c analytic tests (charts, world gazes, eligibility,
fixed head, fusion, process rules).  Each test returns (passed, detail).
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
import ns1c2_core as CORE  # noqa: E402
import ns1c2_phase as PH  # noqa: E402
import ns1c2_spec as SP  # noqa: E402
from fov3d.control import controller02 as c2  # noqa: E402
from fov3d.control import integrated as ic  # noqa: E402

S, D = ic.ServiceState, c2.Disposition
RNG_SEED = 20261005


def _vf():
    return CORE.vergence_focus()


def _head():
    import fsg_geometry as FG
    return FG.HEAD_R_WH, FG.HEAD_ORIGIN_W


def _probe(i, source, gaze=(1.0, 2.0)):
    v, f = _vf()
    return ic.ProbeResult(None if source is None else ic.Observe(i, gaze, v, f, source), {"src": source})


def _accepted_gate_call(pr: ic.ProbeResult):
    """The real accepted Classroom gate on a synthetic proposal: FSG6f without a decision and Cyclopean proposals are
    judged before any geometry is needed."""
    from fov3d.experiments.classroom_oracle import controller02 as x2
    hr, ho = _head()
    return x2.final_look_gate_v1(proposal=pr, decision=None, geometry=np.zeros((0, 3)), gaze=(0.0, 0.0), calibration={},
                                 state={}, history=[], visited=[], profile="full", head_r_wh=hr, head_origin_w=ho,
                                 target_id=int(pr.action.target_id) if pr.action else 0)


# ------------------------------------------------------------------ B4a NORMAL classification
def t01_normal_classification():
    probes = {"fsg6f": _probe(1, "fsg6f"), "cyclopean": _probe(2, "cyclopean_epistemic"), "none": _probe(3, None)}
    with PH.GateGuard(c2.ScenePhase.NORMAL.value, "B4a") as g:
        got = {k: PH.normal_local_state(v).value for k, v in probes.items()}
    rec = g.record()
    ok = got == {"fsg6f": "ACTIONABLE", "cyclopean": "ACTIONABLE", "none": "QUIET"} and rec["calls"] == 0
    return ok, {"states": got, "gate_calls": rec["calls"]}


def t02_gating_mutants_refused():
    """A mutant that gates a Cyclopean (or FSG6f) NORMAL proposal: refused by the guard in NORMAL, and -- were the gate
    allowed -- it would classify the proposal QUIET (the NS1c error)."""
    out = {}
    for name, pr in (("cyclopean", _probe(2, "cyclopean_epistemic")), ("fsg6f", _probe(1, "fsg6f"))):
        with PH.GateGuard(c2.ScenePhase.NORMAL.value, f"mutant {name}") as g:
            try:
                _accepted_gate_call(pr)
                refused = False
            except PH.GateOutsideResidue:
                refused = True
        with PH.GateGuard(c2.ScenePhase.RESIDUE.value, f"mutant {name} (residue harness)"):
            v = _accepted_gate_call(pr)
        gated = "ACTIONABLE" if v.admissible else "QUIET"
        out[name] = {"refused_in_normal": refused, "normal_refusals_recorded": g.record()["refused"],
                     "gated_classification": gated, "gate_reason": v.reason,
                     "accepted_classification": PH.normal_local_state(pr).value}
    ok = all(r["refused_in_normal"] and r["normal_refusals_recorded"] == 1 and r["gated_classification"] == "QUIET"
             and r["accepted_classification"] == "ACTIONABLE" for r in out.values())
    return ok, out


# ------------------------------------------------------------------ B4b the accepted scheduler
def _st(i, local, disp="NORMAL", reason=None):
    return c2.ObjectStatus(i, S(local), D(disp), reason)


def t03_schedule_normal():
    sn = c2.schedule_normal
    retain = sn(172, [_st(9, "ACTIONABLE"), _st(172, "ACTIONABLE"), _st(212, "ACTIONABLE")])
    fwd = sn(172, [_st(9, "ACTIONABLE"), _st(172, "QUIET"), _st(202, "QUIET"), _st(212, "ACTIONABLE")])
    wrap = sn(172, [_st(9, "QUIET"), _st(12, "ACTIONABLE"), _st(123, "ACTIONABLE"), _st(172, "QUIET")])
    deferred = sn(172, [_st(9, "QUIET"), _st(172, "ACTIONABLE", "DEFERRED", "ordinary_budget"), _st(204, "ACTIONABLE")])
    finalized_only = sn(172, [_st(9, "QUIET"), _st(172, "ACTIONABLE", "FINALIZED", "final_probe_rejected")])
    none = sn(172, [_st(9, "QUIET"), _st(172, "ACTIONABLE", "DEFERRED", "ordinary_budget")])
    got = {"retain": (retain.target_id, retain.reason), "forward": (fwd.target_id, fwd.reason),
           "wrap": (wrap.target_id, wrap.reason), "after_deferral": (deferred.target_id, deferred.reason),
           "finalized_only": finalized_only, "no_normal_work": none}
    ok = (got["retain"] == (172, "retain") and got["forward"] == (212, "switch") and got["wrap"] == (12, "switch")
          and got["after_deferral"] == (204, "switch") and finalized_only is None and none is None)
    return ok, {k: (list(v) if isinstance(v, tuple) else v) for k, v in got.items()}


# ------------------------------------------------------------------ B4c the ordinary budget
def t04_budget_defers():
    v, f = _vf()
    budget = CORE.budget_live()
    rows = {}
    for fix, src in ((budget - 1, "fsg6f"), (budget, "fsg6f"), (budget, "cyclopean_epistemic"), (budget, None)):
        m = PH.SceneMachine([7], budget=budget, vergence=v, focus=f)
        m.initialized = [7]
        m.fixations[7] = fix
        st = m.status(7, lambda i, s=src: _probe(i, s), None)
        rows[f"{fix}_{src}"] = st.label
    want = {f"{budget - 1}_fsg6f": "ACTIONABLE", f"{budget}_fsg6f": "ACTIONABLE/DEFERRED:ordinary_budget",
            f"{budget}_cyclopean_epistemic": "ACTIONABLE/DEFERRED:ordinary_budget", f"{budget}_None": "QUIET"}
    ok = budget == SP.BUDGET_EXPECTED and rows == want and not any("BLOCKED" in r or "FINALIZED" in r
                                                                     for r in rows.values())
    return ok, {"budget": budget, "labels": rows}


# ------------------------------------------------------------------ synthetic scenes for B4d and the differential
class Scene:
    """Object i is ACTIONABLE until it has had need(i) own looks; ``cyclopean`` objects alternate FSG6f / Cyclopean
    proposals; ``bonus`` (trigger, look number) -> (object, extra need) and ``relief`` object -> (other, looks) give
    cross-object evidence (natural reactivation, deferred-QUIET)."""

    def __init__(self, need, *, cyclopean=(), seed_fail=(), bonus=None, relief=None, admit=()):
        self.need = dict(need)
        self.looks = {i: 0 for i in need}
        self.cyclopean = set(cyclopean)
        self.seed_fail = set(seed_fail)
        self.bonus = dict(bonus or {})
        self.relief = dict(relief or {})
        self.admit = set(admit)
        self.gate_calls: list[dict] = []
        self.machine = None

    def observe(self, step, action, local):
        i = int(action.target_id)
        self.looks[i] += 1
        key = (i, self.looks[i])
        if key in self.bonus:
            j, extra = self.bonus[key]
            self.need[j] += extra
        if action.source == ic.SEED_SOURCE:
            return ic.ObservationOutcome(initialized=i not in self.seed_fail, record={"looks": self.looks[i]})
        return ic.ObservationOutcome(initialized=None, record={"looks": self.looks[i]})

    def probe(self, i):
        v, f = _vf()
        rel = self.relief.get(i)
        quiet = self.looks[i] >= self.need[i] or (rel is not None and self.looks[rel[0]] >= rel[1])
        src = "cyclopean_epistemic" if (i in self.cyclopean and self.looks[i] % 2 == 0) else "fsg6f"
        return ic.ProbeResult(None if quiet else ic.Observe(i, (float(i), float(self.looks[i])), v, f, src),
                              {"looks": self.looks[i], "source": None if quiet else src})

    def revision(self, i):
        rel = self.relief.get(i)
        return (self.looks[i], self.need[i], None if rel is None else self.looks[rel[0]])

    def gate(self, i, proposal):
        phase = None if self.machine is None else self.machine.phase.value
        self.gate_calls.append({"object": i, "gaze": list(proposal.action.gaze_yaw_pitch_deg),
                                "source": proposal.action.source, "phase": phase})
        return c2.FinalProbeDecision(i in self.admit, "admit" if i in self.admit else "reject")


SCENES = {
    "normal_mixed_sources_reactivation": dict(need={1: 3, 2: 2, 3: 1, 5: 2}, cyclopean={1, 2, 5},
                                              bonus={(3, 1): (2, 2)}, budget=24),
    "defer_then_reject": dict(need={1: 6, 2: 2}, cyclopean={1}, budget=4),
    "defer_admit_final_look_reactivates": dict(need={1: 6, 2: 1, 3: 1}, cyclopean={2}, bonus={(1, 4): (2, 1)},
                                               admit={1}, budget=3),
    "deferred_quiet_finalized": dict(need={1: 9, 2: 3, 3: 2}, relief={1: (3, 2)}, cyclopean={2}, budget=3),
    "second_residue_pass": dict(need={1: 5, 2: 5, 3: 1}, bonus={(1, 3): (3, 1)}, admit={1}, cyclopean={1, 3},
                                budget=2),
    "seed_failure_and_unlocated": dict(need={1: 2, 4: 1, 6: 2}, seed_fail={4}, cyclopean={6}, budget=24,
                                       unlocated=(8, 9)),
}


def _scene(name):
    kw = dict(SCENES[name])
    budget = kw.pop("budget")
    unlocated = kw.pop("unlocated", ())
    return Scene(**kw), budget, unlocated


def _seeds(sc):
    return {i: (float(i), 0.0) for i in sc.need}


def _jsn(x):
    return json.loads(json.dumps(CORE.jsonable(x), sort_keys=True))


def generic_result(name):
    sc, budget, unl = _scene(name)
    v, f = _vf()
    r = c2.run_controller02(_seeds(sc), observe=sc.observe, probe=sc.probe, final_gate=sc.gate, vergence=v, focus=f,
                            budget=budget, revision=sc.revision, unlocated=unl, action_cap=400)
    t = r.terminal
    term = {"type": "closure", "quiet": list(t.quiet), "residual": [list(x) for x in t.residual],
            "seed_residues": list(t.seed_residues), "unlocated": list(t.unlocated),
            "final_observations": list(t.final_observations), "final_rejections": list(t.final_rejections)} \
        if isinstance(t, c2.SceneClosed) else {"type": "CapReached", "cap": t.cap}
    return _jsn({"actions": r.actions, "events": r.events, "final": {str(k): s.label for k, s in r.final.items()},
                 "terminal": term, "fixations": r.fixations, "initialized": r.initialized, "calls": r.probe_calls,
                 "hits": r.probe_cache_hits, "phases": r.phases, "residue": r.residue_decisions,
                 "gate_calls": len(sc.gate_calls)})


def machine_result(name, resume_at: int | None = None):
    sc, budget, unl = _scene(name)
    v, f = _vf()
    m = PH.SceneMachine(list(sc.need), budget=budget, vergence=v, focus=f, seeds=_seeds(sc), unlocated=unl)
    sc.machine = m
    events, actions = [], []
    if resume_at is not None:
        PH.run_machine(m, observe=sc.observe, probe=sc.probe, final_gate=sc.gate, revision=sc.revision,
                       action_cap=400, max_steps=resume_at)
        events, actions = list(m.events), list(m.actions)
        m = PH.SceneMachine.from_json(json.loads(json.dumps(m.to_json(), sort_keys=True)))
        sc.machine = m
    PH.run_machine(m, observe=sc.observe, probe=sc.probe, final_gate=sc.gate, revision=sc.revision, action_cap=400)
    return _jsn({"actions": actions + m.actions, "events": events + m.events,
                 "final": {str(k): s.label for k, s in m.statuses.items()}, "terminal": m.terminal,
                 "fixations": m.fixations, "initialized": m.initialized, "calls": m.calls, "hits": m.hits,
                 "phases": m.phases, "residue": m.residue_decisions, "gate_calls": len(sc.gate_calls)}), sc


def differential(names=tuple(SCENES)) -> dict:
    """The adapter vs the accepted run_controller02 on every synthetic scene, from the seeds and resumed from JSON."""
    rows = {}
    for name in names:
        g = generic_result(name)
        mine, sc = machine_result(name)
        n = len(g["actions"])
        resumes = {}
        for k in sorted({1, max(1, n // 3), max(1, n // 2), max(1, n - 2)}):
            rk, _ = machine_result(name, resume_at=k)
            resumes[str(k)] = rk == g
        normal_gate = [c for c in sc.gate_calls if c["phase"] != c2.ScenePhase.RESIDUE.value]
        rows[name] = {"equal": mine == g, "resumed_equal": resumes, "actions": n,
                      "differing_keys": sorted(k for k in g if g[k] != mine.get(k)),
                      "gate_calls": len(sc.gate_calls), "gate_calls_outside_residue": len(normal_gate),
                      "phases": [p["phase"] for p in g["phases"]],
                      "sources": sorted({a["action_source"] for a in g["actions"]}),
                      "events": sorted({e["event"] for e in g["events"]}),
                      "residue_outcomes": [r["outcome"] for r in g["residue"]]}
    return rows


def t05_differential():
    rows = differential()
    cover = set().union(*(set(r["events"]) for r in rows.values()))
    ok = (all(r["equal"] and all(r["resumed_equal"].values()) and r["gate_calls_outside_residue"] == 0
              for r in rows.values())
          and {"natural_reactivation", "quiet", "deferred", "finalized", "final_probe_decision",
               "local_state_change", "seed_initialized"} <= cover
          and rows["normal_mixed_sources_reactivation"]["gate_calls"] == 0
          and "cyclopean_epistemic" in rows["normal_mixed_sources_reactivation"]["sources"]
          and rows["defer_then_reject"]["gate_calls"] == 1
          and rows["deferred_quiet_finalized"]["gate_calls"] == 0
          and "quiet_before_final_probe" in rows["deferred_quiet_finalized"]["residue_outcomes"]
          and rows["second_residue_pass"]["phases"].count("RESIDUE") == 2)
    return ok, {"scenes": rows, "events_covered": sorted(cover)}


# ------------------------------------------------------------------ B4d RESIDUE only
def t06_residue_only():
    v, f = _vf()
    with PH.GateGuard(c2.ScenePhase.NORMAL.value, "B4d direct") as g:
        try:
            _accepted_gate_call(_probe(5, "fsg6f"))
            direct_refused = False
        except PH.GateOutsideResidue:
            direct_refused = True
    mine, sc = machine_result("defer_then_reject")
    normal, sc_n = machine_result("normal_mixed_sources_reactivation")
    gate_steps = [r["global_step"] for r in mine["residue"]]
    residue_from = [p["from_global_step"] for p in mine["phases"] if p["phase"] == "RESIDUE"]
    normal_after_residue = [a for a in mine["actions"] if a["phase"] == "NORMAL" and residue_from
                            and a["global_step"] >= residue_from[0]]
    ok = (direct_refused and g.record()["refused"] == 1 and len(sc.gate_calls) == 1
          and sc.gate_calls[0]["phase"] == "RESIDUE" and len(sc_n.gate_calls) == 0 and gate_steps == residue_from
          and not normal_after_residue and mine["final"]["1"] == "ACTIONABLE/FINALIZED:final_probe_rejected")
    return ok, {"direct_call_refused": direct_refused, "gate_calls": sc.gate_calls, "residue_from": residue_from,
                "final_1": mine["final"]["1"], "normal_scene_gate_calls": len(sc_n.gate_calls)}


def t07_guard_restores():
    from fov3d.experiments.classroom_oracle import controller02 as x2
    before = [getattr(m, PH.GATE_NAME) for _n, m in PH.GateGuard.copies()]
    with PH.GateGuard(c2.ScenePhase.NORMAL.value):
        during = [getattr(m, PH.GATE_NAME) for _n, m in PH.GateGuard.copies()]
    after = [getattr(m, PH.GATE_NAME) for _n, m in PH.GateGuard.copies()]
    ok = all(a is not d for a, d in zip(before, during)) and all(a is b for a, b in zip(before, after)) \
        and x2.final_look_gate_v1 is before[0]
    return ok, {"copies": len(before)}


# ------------------------------------------------------------------ inherited NS1c analytic tests
def t08_charts_every_nb1c_gaze():
    rows = {}
    for r, y, p in SP.NS1A_RANK_GAZES:
        ch = CORE.chart_record(100 + r, r, (y, p))
        rows[r] = {"ok": ch["checks"]["ok"], "b_perp": ch["projected_baseline_norm"]}
    singular = []
    for g in (np.array([1.0, 0.0, 0.0]), np.array([-1.0, 0.0, 0.0])):
        try:
            CH.chart_basis(g)
            singular.append(False)
        except CH.ChartSingular:
            singular.append(True)
    ok = all(v["ok"] and v["b_perp"] >= SP.CHART_SINGULAR_MIN for v in rows.values()) and all(singular)
    return ok, {"ranks": rows, "singular_refused": singular}


def t09_local_world_roundtrip():
    worst = 0.0
    for _r, y, p in SP.NS1A_RANK_GAZES:
        r = CH.chart_basis(CH.gaze_direction(y, p))["R_HC"]
        for yl in np.arange(-25.0, 25.1, 5.0):
            for pl in np.arange(-20.0, 20.1, 5.0):
                yw, pw, _ = CH.local_to_world_gaze(float(yl), float(pl), r)
                yb, pb = CH.world_to_local_gaze(yw, pw, r)
                worst = max(worst, abs(yb - yl), abs(pb - pl))
    return worst <= SP.GAZE_ROUNDTRIP_TOL_DEG, {"max_roundtrip_error_deg": worst}


def _ent(k, init, rank, patches, surfels):
    return {"temporary_entity_id": k, "initialized": init, "initialized_at_rank": rank if init else None,
            "contributing_patches": patches, "final_surfels": surfels}


def t10_eligibility_rule_and_names():
    ents = [_ent(5, True, 2, 1, 900), _ent(7, True, 6, 2, 9000), _ent(3, True, 1, 1, 400), _ent(9, True, 5, 3, 10 ** 5),
            _ent(11, False, None, 0, 0), _ent(4, True, 1, 1, 150)]
    a = CORE.derive_coherent_set({"entities": ents})
    refused = []
    for bad in ({"entities": [{**_ent(5, True, 2, 1, 900), "object_name": "x"}]},
                {"entities": [_ent(5, True, 2, 1, 900)], "catalog": {"5": "x"}}):
        try:
            CORE.derive_coherent_set(bad)
            refused.append(False)
        except CORE.EligibilityRefused:
            refused.append(True)
    ok = a["coherent_ids"] == [3, 4, 5] and a["deferred_ids"] == [7, 9] and a["outside_ids"] == [11] and all(refused)
    return ok, {"coherent": a["coherent_ids"], "deferred": a["deferred_ids"], "names_refused": refused}


def t11_fixed_head_fake_local_refused():
    hr, ho = _head()
    out = {}
    for rank in (1, 6):
        _r, y, p = SP.NS1A_RANK_GAZES[rank - 1]
        r = CH.chart_basis(CH.gaze_direction(y, p))["R_HC"]
        local = (6.2, -1.2)
        yw, pw, _ = CH.local_to_world_gaze(*local, r)
        real = CH.north_star_sensor("full", yw, pw, hr, ho)
        fake = CH.north_star_sensor("full", *local, hr, ho)
        reset = copy.deepcopy(real)
        for e, s in zip(reset["eyes"], (-1.0, 1.0)):
            e["centre_h_m"] = (s * SP.IPD_M / 2 * r[:, 0]).tolist()
        out[rank] = {"real": B.physical_calibration_test(real, local, r, hr, ho)["ok"],
                     "fake_refused": not B.physical_calibration_test(fake, local, r, hr, ho)["ok"],
                     "reset_refused": not B.physical_calibration_test(reset, local, r, hr, ho)["ok"]}
    return all(all(v.values()) for v in out.values()), out


def t12_first_world_action_real_sensor():
    hr, ho = _head()
    out = {}
    for rank in (1, 6):
        _r, y, p = SP.NS1A_RANK_GAZES[rank - 1]
        ch = CORE.chart_record(1000 + rank, rank, (y, p))
        plan = CORE.plan_action({"local_gaze_deg": [6.2, -1.2]}, ch, hr, ho)
        yw, pw, _ = CH.local_to_world_gaze(6.2, -1.2, np.asarray(ch["R_HC"]))
        real = CH.north_star_sensor("full", yw, pw, hr, ho)
        out[rank] = {"world_equal": plan["world_gaze_deg"] == [yw, pw],
                     "calibration_is_real_world_sensor": B.calibration_matches(plan["planned_calibration"], real),
                     "physical_test": plan["physical_calibration_test"]["ok"],
                     "fixed_head": B.fixed_head(plan["planned_calibration"], hr, ho)["ok"]}
    return all(all(v.values()) for v in out.values()), out


def _plane(lo, hi, k, z=-2.0, n=(50, 24)):
    rng = np.random.default_rng(12 + k)
    xy = np.stack(np.meshgrid(np.linspace(lo, hi, n[0]), np.linspace(-.10, .10, n[1])), axis=-1).reshape(-1, 2)
    return np.c_[xy, z * np.ones(len(xy))] + rng.normal(scale=.0004, size=(len(xy), 3))


def t13_target_only_fusion_known_answer():
    from fov3d.reconstruction import surface_map as SM
    maps = {}
    for k, (lo, hi, z) in {71: (-.28, -.02, -2.0), 72: (-.28, .28, -2.5)}.items():
        x = _plane(lo, hi, k, z)
        maps[k] = SM.initialize(SM.Patch(f"seed_{k}", x, np.full((len(x), 3), .3), np.full(len(x), k, np.int32)), k)
    before = {k: B.map_arrays(m) for k, m in maps.items()}
    xa, xb = _plane(-.12, .12, 71), _plane(-.2, .2, 72, -2.5)
    xyz = np.vstack([xa, xb])
    ids = np.r_[np.full(len(xa), 71), np.full(len(xb), 72)].astype(np.int32)
    patch = CORE.target_patch(xyz, np.ones(len(xyz), bool), ids, np.full((len(xyz), 3), .5), 71, 7)
    fused, rec = B.fuse_h0(maps[71], patch, 71)
    direct, meta = SM.fuse(maps[71], SM.Patch(patch["patch_id"], patch["xyz_h"], patch["rgb"], patch["instance_id"]),
                           71, 0.012, 0.012)
    try:
        B.fuse_h0(maps[71], {**patch, "frame": "C"}, 71)
        c_refused = False
    except B.FrameRefused:
        c_refused = True
    ok = (patch["points"] == len(xa) and np.all(patch["instance_id"] == 71) and patch["patch_id"] == "ns1c2_step_07"
          and rec["action"] == "FUSED" and B.maps_equal(B.map_arrays(fused), B.map_arrays(direct))
          and B.maps_equal(before[72], B.map_arrays(maps[72])) and rec["replay"]["exact"] and c_refused
          and rec["radius_m"] == SP.ASSOCIATION_RADIUS_M and rec["hash_cell_m"] == SP.HASH_CELL_M)
    return ok, {"matched": rec["matched"], "new": rec["new"], "chart_frame_refused": c_refused}


def t14_patch_ids_and_prefix():
    ids = [SP.patch_id(k) for k in range(24)]
    ok = (ids[:4] == ["ns1c_step_00", "ns1c_step_01", "ns1c_step_02", "ns1c_step_03"] and ids[4] == "ns1c2_step_04"
          and len(set(ids)) == len(ids) and "ns1b_action_01" not in ids
          and [SP.is_prefix(k) for k in (0, 3, 4)] == [True, True, False])
    return ok, {"first": ids[:6]}


def t15_stop_cap_rules():
    rule = (not CORE.stop_event(172, "FUSED") and CORE.stop_event(202, "FUSED")
            and CORE.stop_event(202, "RETAINED_NOT_FUSED") and not CORE.stop_event(202, None))
    try:
        CORE.require_not_stopped({"stopped": True, "stop": {"global_step": 9}})
        refused = False
    except CORE.ProcessRefused:
        refused = True
    try:
        CORE.require_under_cap(19, 19)
        capped = False
    except CORE.ProcessRefused:
        capped = True
    CORE.require_under_cap(18, 19)
    cap = CORE.derived_cap(SP.BUDGET_EXPECTED, 6)
    return rule and refused and capped and cap == SP.CAP_EXPECTED, {"cap": cap, "after_stop_refused": refused}


def t16_scene_closure_literal_absent():
    hits = []
    for name in ("ns1c2_spec.py", "ns1c2_phase.py", "ns1c2_core.py", "ns1c2_run.py", "ns1c2_render.py",
                 "ns1c2_visuals.py"):
        p = HERE / name
        if p.exists():
            tree = ast.parse(p.read_text())
            hits += [f"{name}: {n.value}" for n in ast.walk(tree) if isinstance(n, ast.Constant)
                     and isinstance(n.value, str) and SP.FORBIDDEN_MARKER in n.value]
    return not hits, {"literal_hits": hits}


def t17_adapter_restores():
    before = CH.original_functions()
    with CH.PolicyChartAdapter(CH.rot_x(30.0)):
        during = CH.original_functions()
    after = CH.original_functions()
    swapped = all(a is not d for sid in before for (_n, a), (_m, d) in zip(before[sid], during[sid]))
    restored = all(a is b for sid in before for (_n, a), (_m, b) in zip(before[sid], after[sid]))
    return swapped and restored, {"swapped": swapped, "restored": restored}


# ------------------------------------------------------------------ B4e: the accepted Controller-02 history (known-answer)
def historical_trace(trajectories: dict, events: list[dict], final_residue: dict, budget: int) -> dict:
    """Drive the adapter over the accepted Controller-02 history (name-free inputs only).

    ``trajectories``: object id -> its accepted Controller-01 trajectory rows (global_step, step, action_source,
    gaze_deg); ``events``: Controller-02 ``events.json``; ``final_residue``: Controller-02 ``final-residue.json``.  The
    probe stub returns QUIET or ACTIONABLE by the recorded quiet / natural-reactivation events, ACTIONABLE carrying the
    object's next executed action (or, after its last ordinary look, the recorded final-probe proposal); the gate stub
    returns the recorded verdict.  The adapter's own scheduling, fixation counting, deferral, phases and gate placement
    are then compared with the accepted record."""
    v, f = _vf()
    order = sorted(int(k) for k in trajectories)
    rows = {int(k): sorted(r, key=lambda x: int(x["global_step"])) for k, r in trajectories.items()}
    by_step = {int(r["global_step"]): (k, r) for k, rs in rows.items() for r in rs}
    timeline: dict[int, list[tuple[int, str]]] = {k: [] for k in order}
    for e in events:
        if e["event"] in ("quiet", "natural_reactivation"):
            timeline[int(e["object"])].append((int(e["global_step"]), e["event"]))
    fpd = [e for e in events if e["event"] == "final_probe_decision"]
    final_prop = {int(e["object"]): (tuple(e["proposal_gaze_deg"]), e["proposal_source"]) for e in fpd}
    verdicts = {int(r["object"]): r for r in final_residue["residue_decisions"]}
    seeds = {k: tuple(rs[0]["gaze_deg"]) for k, rs in rows.items()}
    m = PH.SceneMachine(order, budget=budget, vergence=v, focus=f, seeds=seeds)
    mismatches, gate_calls = [], []

    def label_after(i, s):
        lab = "ACTIONABLE"
        for st, ev in timeline[i]:
            if st <= s:
                lab = "QUIET" if ev == "quiet" else "ACTIONABLE"
        return lab

    def probe(i):
        s = m.step
        if label_after(i, s) == "QUIET":
            return ic.ProbeResult(None, {"stub": "quiet"})
        nxt = [r for r in rows[i] if int(r["global_step"]) > s]
        if nxt:
            gaze, src = tuple(nxt[0]["gaze_deg"]), nxt[0]["action_source"]
        elif i in final_prop:
            gaze, src = final_prop[i]
        else:
            raise AssertionError(f"object {i} is ACTIONABLE after step {s} with no recorded next action")
        return ic.ProbeResult(ic.Observe(i, gaze, v, f, src), {"stub": "actionable"})

    def observe(step, action, local):
        k, r = by_step.get(int(step), (None, None))
        got = (int(action.target_id), action.source, int(local))
        want = None if r is None else (k, r["action_source"], int(r["step"]))
        dev = None if r is None else max(abs(float(a) - float(b)) for a, b in zip(action.gaze_yaw_pitch_deg,
                                                                                  r["gaze_deg"]))
        if got != want or dev is None or dev > 1e-9:
            mismatches.append({"global_step": step, "machine": list(got), "accepted": want, "gaze_deviation": dev})
        return ic.ObservationOutcome(initialized=True if action.source == ic.SEED_SOURCE else None)

    def gate(i, proposal):
        gate_calls.append({"object": i, "phase": m.phase.value, "global_step": m.step,
                           "gaze_deg": list(proposal.action.gaze_yaw_pitch_deg), "source": proposal.action.source})
        r = verdicts[i]
        return c2.FinalProbeDecision(bool(r["admissible"]), str(r["reason"]))

    PH.run_machine(m, observe=observe, probe=probe, final_gate=gate, revision=None, action_cap=400)
    key = lambda e: [e["event"], int(e["object"]), int(e["global_step"]), e.get("trigger_target")]  # noqa: E731
    ours, theirs = [key(e) for e in m.events], [key(e) for e in events]
    dec = [a["scheduler_reason"] for a in m.actions]
    normal = [a for a in m.actions if a["phase"] == "NORMAL"]
    deferred = [e for e in m.events if e["event"] == "deferred"]
    return {"actions": len(m.actions), "ordinary_actions": len(normal), "action_mismatches": mismatches[:5],
            "action_mismatch_count": len(mismatches),
            "sources": {s_: sum(1 for a in m.actions if a["action_source"] == s_) for s_ in
                        ("oracle_seed", "fsg6f", "cyclopean_epistemic")},
            "events_equal": ours == theirs, "events": len(ours), "accepted_events": len(theirs),
            "first_event_difference": next(([a, b] for a, b in zip(ours, theirs) if a != b), None),
            "switches": sum(1 for a in m.actions if a["scheduler_decision"] == "switch"),
            "natural_reactivation_switches": dec.count("natural_reactivation"),
            "bouts": max((int(a["attention_bout"]) for a in m.actions), default=0),
            "phases": m.phases, "phases_equal": m.phases == final_residue["phases"],
            "deferred": [{"object": e["object"], "global_step": e["global_step"], "fixations": e["fixations"],
                          "reason": e["reason"]} for e in deferred],
            "gate_calls": gate_calls, "gate_calls_in_normal": sum(1 for g in gate_calls if g["phase"] != "RESIDUE"),
            "residue_decisions": [{k_: r[k_] for k_ in ("object", "global_step", "outcome", "admissible", "reason")
                                   if k_ in r} for r in m.residue_decisions],
            "final": {str(k): s.label for k, s in m.statuses.items()},
            "action_sequence": [[int(a["global_step"]), int(a["target_id"]), a["action_source"], a["phase"],
                                 a["scheduler_reason"]] for a in m.actions],
            "terminal": m.terminal}


def historical_ok(h: dict) -> tuple[bool, dict]:
    want = SP.HISTORICAL
    c1, c02 = want["controller01"], want["controller02"]
    finals = list(h["final"].values())
    checks = {
        "141_actions_equal": h["actions"] == c1["observations"] and h["action_mismatch_count"] == 0,
        "sources": h["sources"] == c1["observations_by_source"],
        "events_equal": h["events_equal"] and h["events"] == c02["events"],
        "switches": h["switches"] == c1["switches"] and h["natural_reactivation_switches"] == 2
        and h["bouts"] == c1["bouts"],
        "phases_equal": h["phases_equal"] and [p["phase"] for p in h["phases"]] == ["NORMAL", "RESIDUE", "CLOSED"],
        "deferred_210_at_101": h["deferred"] == [{"object": 210, "global_step": 101, "fixations": 24,
                                                  "reason": "ordinary_budget"}],
        "one_gate_call_in_residue": len(h["gate_calls"]) == 1 and h["gate_calls_in_normal"] == 0
        and h["gate_calls"][0]["object"] == 210 and h["gate_calls"][0]["phase"] == "RESIDUE"
        and h["gate_calls"][0]["source"] == "fsg6f"
        and max(abs(a - b) for a, b in zip(h["gate_calls"][0]["gaze_deg"], [7.6, 18.2])) <= 1e-9,
        "rejected_finalized": h["final"].get("210") == "ACTIONABLE/FINALIZED:final_probe_rejected"
        and finals.count("QUIET") == 24 and [r["outcome"] for r in h["residue_decisions"]] == ["final_probe_rejected"],
        "no_final_residue_observation": h["ordinary_actions"] == h["actions"],
    }
    return all(checks.values()), checks


TESTS = {"01_b4a_normal_classification": t01_normal_classification,
         "02_b4a_gating_mutants_refused": t02_gating_mutants_refused,
         "03_b4b_schedule_normal": t03_schedule_normal, "04_b4c_budget_defers": t04_budget_defers,
         "05_differential_run_controller02": t05_differential, "06_b4d_residue_only": t06_residue_only,
         "07_gate_guard_restores": t07_guard_restores, "08_charts_every_nb1c_gaze": t08_charts_every_nb1c_gaze,
         "09_local_world_roundtrip": t09_local_world_roundtrip,
         "10_eligibility_rule_and_names": t10_eligibility_rule_and_names,
         "11_fixed_head_fake_local_refused": t11_fixed_head_fake_local_refused,
         "12_first_world_action_real_sensor": t12_first_world_action_real_sensor,
         "13_target_only_fusion_known_answer": t13_target_only_fusion_known_answer,
         "14_patch_ids_and_prefix": t14_patch_ids_and_prefix, "15_stop_cap_rules": t15_stop_cap_rules,
         "16_scene_closure_literal_absent": t16_scene_closure_literal_absent,
         "17_frame_adapter_restores": t17_adapter_restores}


def run_all() -> dict:
    res = {}
    for k, fn in TESTS.items():
        try:
            ok, detail = fn()
        except Exception as exc:  # noqa: BLE001  (a crash is a failure of that test)
            ok, detail = False, {"error": repr(exc)}
        res[k] = {"pass": bool(ok), "detail": CORE.jsonable(detail)}
    failed = [k for k, v in res.items() if not v["pass"]]
    return {"schema": "NS1c2-synthetic-v1", "truth": SP.TRUTH_DERIVED, "tests": res, "failed": failed,
            "count": len(res), "marker": "NS1C2_SYNTHETIC_PASS" if not failed else "NS1C2_SYNTHETIC_FAIL"}


if __name__ == "__main__":
    r = run_all()
    for k, v in r["tests"].items():
        print(f"[ns1c2-synthetic] {'PASS' if v['pass'] else 'FAIL'} {k}")
    print(f"[ns1c2-synthetic] {r['marker']} {r['count'] - len(r['failed'])}/{r['count']}")
    print(json.dumps({k: v["detail"] for k, v in r["tests"].items() if not v["pass"]}, default=str)[:4000])
