"""North Star-1e: synthetic known answers (fail-capable; each test has a negative control).

Contract: docs/north-star/ns1e-coherent-full-loop-m2-memory-contract.md, section 29.

    .venv/bin/python tools/north_star/ns1e_synthetic.py

No Classroom data, no render.  The tests exercise the accepted components NS1e composes (the memory ledger, the
resumable Controller-02 machine, the gate guard) and NS1e's own functions (the M2 revision, the cap, the step
classification, the evaluation helpers, the PLY export).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "natural_bootstrap", HERE.parent / "classroom_oracle", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1c2_core as C2  # noqa: E402
import ns1c2_phase as PH  # noqa: E402
import ns1d_core as K  # noqa: E402
import ns1e_core as CORE  # noqa: E402
import ns1e_spec as SP  # noqa: E402
from fov3d.control import controller02 as c2  # noqa: E402
from fov3d.control import integrated as ic  # noqa: E402

S, D = ic.ServiceState, c2.Disposition


def _vf():
    return C2.vergence_focus()


def _probe(i, source, gaze=(1.0, 2.0), tag=None):
    v, f = _vf()
    return ic.ProbeResult(None if source is None else ic.Observe(int(i), gaze, v, f, source), {"src": source, "tag": tag})


def _patch(ids_xyz: list[tuple[int, tuple[float, float, float]]], size: int = 8) -> dict:
    xyz = np.full((size, size, 3), np.nan, np.float32)
    inst = np.zeros((size, size), np.int32)
    valid = np.zeros((size, size), bool)
    for n, (i, p) in enumerate(ids_xyz):
        r, c = divmod(n, size)
        xyz[r, c] = p
        inst[r, c] = i
        valid[r, c] = i > 0
    return {"xyz_h": xyz, "instance_id": inst, "valid": valid}


def _rec(i, own, surfels=3):
    return {"temporary_entity_id": i, "own_looks": own, "map": {"surfels": surfels}}


# ------------------------------------------------------------------ memory
def t01_append_once_and_order():
    led = K.MemoryLedger()
    led.append(0, "obs-a", _patch([(5, (0, 0, -1))]), 5)
    refused = {}
    for name, args in (("same observation twice", (1, "obs-a", _patch([(5, (0, 0, -1))]), 5)),
                       ("out of order", (2, "obs-b", _patch([(5, (0, 0, -1))]), 5)),
                       ("non-positive target", (1, "obs-c", _patch([(5, (0, 0, -1))]), 0))):
        try:
            led.append(*args)
            refused[name] = False
        except K.LedgerRefused:
            refused[name] = True
    ok_next = led.append(1, "obs-b", _patch([(5, (0, 0, -1))]), 5) == {5: 1}
    return all(refused.values()) and ok_next and len(led.events) == 2, {"refused": refused, "next_ok": ok_next}


def t02_routing_every_positive_id_no_zero():
    led = K.MemoryLedger()
    adds = led.append(0, "o", _patch([(0, (1, 1, 1)), (110, (0, 0, -2)), (202, (0, 1, -2)), (202, (0, 2, -2)),
                                      (7, (1, 0, -3))]), 202)
    ok = adds == {7: 1, 110: 1, 202: 2} and 0 not in led.memory.instance_ids()
    neg = adds != {202: 2}   # a router by active target would keep only the target
    snap = led.snapshot(110)
    prov = list(snap.source_active_target_id) == [202] and list(snap.source_global_index) == [0]
    return ok and neg and prov, {"additions": adds, "provenance_ok": prov}


def t03_m2_revision_cross_target():
    led = K.MemoryLedger()
    b = _rec(12, 1)
    before = CORE.revision_m2(b, led)
    led.append(0, "o1", _patch([(202, (0, 0, -2)), (12, (0, 1, -2)), (12, (0, 2, -2))]), 202)
    after = CORE.revision_m2(b, led)
    own_only = int((led.snapshot(12).source_active_target_id == 12).sum())
    map_rev = [b["own_looks"], b["map"]["surfels"]]          # the wrong (map-surfel) revision does not move
    ok = before == [1, 0] and after == [1, 2] and own_only == 0 and map_rev == [1, 3]
    return ok, {"before": before, "after": after, "own_only_points": own_only, "map_revision_static": map_rev}


def t04_effective_geometry_map_first_duplicates_kept():
    m = np.array([[0.0, 0.0, -1.0], [0.0, 0.1, -1.0]])
    mem = np.array([[0.0, 0.0, -1.0], [0.0, 0.0, -1.0]], np.float32)
    g = CORE.effective_target_geometry(m, mem)
    ok = g.shape == (4, 3) and np.array_equal(g[:2], m) and np.array_equal(g[2:], mem.astype(np.float64))
    neg = len(np.unique(g, axis=0)) != len(g)   # a deduplicating variant would differ
    return ok and neg, {"rows": int(len(g))}


# ------------------------------------------------------------------ the cap
def _always_actionable_machine(order, fixations, budget, current, step):
    v, f = _vf()
    m = PH.SceneMachine(order, budget=budget, vergence=v, focus=f)
    m.resume_initialized(fixations, current=current, bout=1, step=step,
                         probe=lambda i: _probe(i, "fsg6f"), revision=lambda i: (m.fixations[i],))
    return m


def t05_cap_formula_and_bound():
    order, budget = [1, 2, 3], 5
    fix = {1: 3, 2: 1, 3: 5 - 0}
    fix[3] = 4
    m = _always_actionable_machine(order, dict(fix), budget, 2, 10)
    cap = CORE.derive_cap(m)
    want = (5 - 3) + (5 - 1) + (5 - 4) + 3
    observed = {"n": 0}

    def observe(step, action, local_step):
        observed["n"] += 1
        return ic.ObservationOutcome(initialized=None, record={})

    def gate(i, proposal):
        return c2.FinalProbeDecision(True, "synthetic_admit")
    with PH.GateGuard(c2.ScenePhase.NORMAL.value, "t05") as gg:
        def guarded_gate(i, proposal):
            gg.phase = m.phase.value
            return gate(i, proposal)
        PH.run_machine(m, observe=observe, probe=lambda i: _probe(i, "fsg6f"), final_gate=guarded_gate,
                       revision=lambda i: (m.fixations[i],), action_cap=cap["absolute_action_cap"])
    closed = m.terminal is not None and m.terminal.get("type") == "closure"
    # negative control: one action less than the bound is reached as a cap, never a closure
    m2 = _always_actionable_machine(order, dict(fix), budget, 2, 10)
    with PH.GateGuard(c2.ScenePhase.NORMAL.value, "t05b") as gg2:
        def guarded_gate2(i, proposal):
            gg2.phase = m2.phase.value
            return gate(i, proposal)
        PH.run_machine(m2, observe=lambda s, a, l: ic.ObservationOutcome(initialized=None, record={}),
                       probe=lambda i: _probe(i, "fsg6f"), final_gate=guarded_gate2,
                       revision=lambda i: (m2.fixations[i],), action_cap=cap["absolute_action_cap"] - 1)
    capped = m2.terminal == {"type": "CapReached", "cap": cap["absolute_action_cap"] - 1}
    ok = (cap["max_new_physical_actions"] == want and cap["absolute_action_cap"] == 10 + want
          and observed["n"] == want and closed and capped and cap["assumptions_ok"]
          and all(m.fixations[i] == budget + 1 for i in order))
    return ok, {"cap": cap["max_new_physical_actions"], "want": want, "observed": observed["n"], "closed": closed,
                "cap_minus_one_is_cap": capped, "fixations": m.fixations}


def t06_cap_expected_handoff_numbers():
    order = list(SP.EXPECTED_COHERENT)
    fix = {int(k): v for k, v in SP.HANDOFF_EXPECTED["own_looks"].items()}
    m = _always_actionable_machine(order, fix, SP.BUDGET_EXPECTED, 202, 8)
    cap = CORE.derive_cap(m)
    ok = cap["max_new_physical_actions"] == SP.MAX_NEW_EXPECTED == 231 and cap["absolute_action_cap"] == 239
    m.disposition[9] = (D.DEFERRED, "ordinary_budget")
    neg = not CORE.derive_cap(m)["assumptions_ok"]
    return ok and neg, {"cap": cap["max_new_physical_actions"], "absolute": cap["absolute_action_cap"],
                        "deferred_breaks_assumption": neg}


# ------------------------------------------------------------------ resume, reactivation, gate, residue
def _scripted(order, script):
    """probe(i) -> a scripted ProbeResult keyed by the current revision."""
    def probe(i):
        return script(i)
    return probe


def t07_resume_equivalence():
    order = [1, 2, 3]
    state = {"rev": {1: 0, 2: 0, 3: 0}, "quiet": {2}}

    def probe(i):
        return _probe(i, None if i in state["quiet"] else "cyclopean_epistemic", (float(i), 1.0))
    v, f = _vf()
    a = PH.SceneMachine(order, budget=6, vergence=v, focus=f)
    a.resume_initialized({1: 1, 2: 2, 3: 1}, current=1, bout=1, step=0, probe=probe, revision=lambda i: (state["rev"][i],))
    for _ in range(3):
        plan = a.decide(lambda i, p: None)
        a.commit(plan, ic.ObservationOutcome(initialized=None, record={}), probe, lambda i: (state["rev"][i],))
    b = PH.SceneMachine(order, budget=6, vergence=v, focus=f)
    quiet = K.resume_scene(b, dict(a.fixations), current=a.current, bout=a.bout, step=a.step, probe=probe,
                           revision=lambda i: (state["rev"][i],), quiet_since=a.quiet_since.get(2))
    same = {fl: PH.status_to_json(a.statuses[i]) == PH.status_to_json(b.statuses[i]) for fl, i in
            (("s1", 1), ("s2", 2), ("s3", 3))}
    pa = PH.SceneMachine.from_json(a.to_json()).decide(lambda i, p: None)
    pb = PH.SceneMachine.from_json(b.to_json()).decide(lambda i, p: None)
    same_plan = (pa["target_id"], pa["decision"], tuple(pa["action"].gaze_yaw_pitch_deg)) == \
        (pb["target_id"], pb["decision"], tuple(pb["action"].gaze_yaw_pitch_deg))
    quiet_ok = quiet == [2] and 2 in b.quiet_probe and b.events == []
    # negative control: without the quiet bookkeeping a later reactivation of 2 would fail (KeyError on quiet_probe)
    c = PH.SceneMachine(order, budget=6, vergence=v, focus=f)
    c.resume_initialized(dict(a.fixations), current=a.current, bout=a.bout, step=a.step, probe=probe,
                         revision=lambda i: (state["rev"][i],))
    state["quiet"].discard(2)
    state["rev"][2] += 1
    try:
        c.refresh(c.step, 1, probe, lambda i: (state["rev"][i],))
        neg = False
    except KeyError:
        neg = True
    ok = all(same.values()) and same_plan and quiet_ok and neg
    return ok, {"statuses_equal": same, "plan_equal": same_plan, "quiet": quiet, "no_bookkeeping_fails": neg}


def t08_reactivation_only_through_revision():
    order = [1, 2]
    st = {"rev": {1: 0, 2: 0}, "quiet": {2}}

    def probe(i):
        return _probe(i, None if i in st["quiet"] else "fsg6f")
    v, f = _vf()
    m = PH.SceneMachine(order, budget=10, vergence=v, focus=f)
    K.resume_scene(m, {1: 1, 2: 1}, current=1, bout=1, step=0, probe=probe, revision=lambda i: (st["rev"][i],),
                   quiet_since=0)
    st["quiet"].discard(2)                       # the probe WOULD now act, but the revision is unchanged
    plan = m.decide(lambda i, p: None)
    m.commit(plan, ic.ObservationOutcome(initialized=None, record={}), probe, lambda i: (st["rev"][i],))
    no_event = not any(e["event"] == "natural_reactivation" for e in m.events) and m.statuses[2].local is S.QUIET
    st["rev"][2] += 1                            # a cross-target memory addition: the revision changes
    plan = m.decide(lambda i, p: None)
    m.commit(plan, ic.ObservationOutcome(initialized=None, record={}), probe, lambda i: (st["rev"][i],))
    ev = [e for e in m.events if e["event"] == "natural_reactivation"]
    ok = no_event and len(ev) == 1 and ev[0]["object"] == 2 and m.statuses[2].local is S.ACTIONABLE
    return ok, {"no_event_without_revision_change": no_event, "events": [e["event"] for e in m.events]}


def t09_gate_only_in_residue():
    from fov3d.experiments.classroom_oracle import controller02 as x2
    out = {}
    for phase in (c2.ScenePhase.NORMAL.value, c2.ScenePhase.RESIDUE.value):
        with PH.GateGuard(phase, f"t09 {phase}") as g:
            try:
                x2.final_look_gate_v1(proposal=_probe(4, "cyclopean_epistemic"), decision=None,
                                      geometry=np.zeros((0, 3)), gaze=(0.0, 0.0), calibration={}, state={}, history=[],
                                      visited=[], profile="full", head_r_wh=np.eye(3), head_origin_w=np.zeros(3),
                                      target_id=4)
                out[phase] = "called"
            except PH.GateOutsideResidue:
                out[phase] = "refused"
            except Exception as exc:  # noqa: BLE001  (the accepted gate ran and judged / failed on synthetic input)
                out[phase] = f"called ({type(exc).__name__})"
        out[phase + "_record"] = g.record()
    ok = out["NORMAL"] == "refused" and out["RESIDUE"].startswith("called") and \
        out["NORMAL_record"]["normal_calls"] == 1 and out["RESIDUE_record"]["residue_calls"] == 1
    return ok, {k: v for k, v in out.items() if not k.endswith("_record")}


def t10_residue_procedure():
    """Deferred QUIET -> finalized without a gate call; deferred ACTIONABLE -> the gate receives the UNCHANGED cached
    ProbeResult; an admitted proposal executes exactly one final observation; a rejected one is finalized."""
    order = [1, 2, 3]
    st = {"quiet": {1}}
    cached = {}

    def probe(i):
        r = _probe(i, None if i in st["quiet"] else "cyclopean_epistemic", (float(i), 0.0), tag=f"p{i}")
        cached[i] = r
        return r
    v, f = _vf()
    m = PH.SceneMachine(order, budget=2, vergence=v, focus=f)
    m.resume_initialized({1: 2, 2: 2, 3: 2}, current=3, bout=1, step=0, probe=probe, revision=lambda i: (0,))
    for i in order:
        m.disposition[i] = (D.DEFERRED, "ordinary_budget")
        m.statuses[i] = c2.ObjectStatus(i, m.statuses[i].local, D.DEFERRED, "ordinary_budget")
    seen = []

    def gate(i, proposal):
        seen.append((i, proposal is m.last_probe[i]))
        return c2.FinalProbeDecision(i == 2, "admit" if i == 2 else "reject")
    plan = m.decide(gate)
    ok1 = plan["kind"] == "final_residue" and plan["target_id"] == 2 and seen == [(2, True)] and \
        m.disposition[1] == (D.FINALIZED, "quiet_before_final_probe")
    m.commit(plan, ic.ObservationOutcome(initialized=None, record={}), probe, lambda i: (1,))
    plan2 = m.decide(gate)
    ok2 = plan2["kind"] == "closed" and seen == [(2, True), (3, True)] and \
        m.disposition[2] == (D.FINALIZED, "final_probe_executed") and m.disposition[3] == (D.FINALIZED,
                                                                                           "final_probe_rejected")
    once = m.final_observed == [2]
    # negative control: the closure is not global quiescence (residual ACTIONABLE entities remain)
    oc = CORE.control_outcome(m.terminal)
    return ok1 and ok2 and once and oc["outcome"] == "1R", {"gate_calls": seen, "final_observed": m.final_observed,
                                                           "outcome": oc["outcome"]}


# ------------------------------------------------------------------ checkpointing
def t11_step_classification():
    with tempfile.TemporaryDirectory() as td:
        sd = Path(td) / "steps/step-008"
        empty = CORE.classify_step(sd)
        for stage in SP.STEP[:4]:
            p = sd / SP.STAGE_OUTPUT[stage]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("{}")
        partial = CORE.classify_step(sd)
        (sd / SP.STAGE_OUTPUT[SP.STEP[6]]).parent.mkdir(parents=True, exist_ok=True)
        (sd / SP.STAGE_OUTPUT[SP.STEP[6]]).write_text("{}")
        try:
            CORE.classify_step(sd)
            ambiguous = False
        except CORE.StepAmbiguous:
            ambiguous = True
        sd2 = Path(td) / "steps/step-009"
        for stage in SP.STEP:
            p = sd2 / SP.STAGE_OUTPUT[stage]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("{}")
        complete = CORE.classify_step(sd2)
        sd3 = Path(td) / "steps/step-010"
        (sd3 / "plan").mkdir(parents=True)
        (sd3 / "plan/decision.json").write_text(json.dumps({"kind": "closed"}))
        term = CORE.classify_step(sd3)
    ok = (not empty["exists"] and partial["exists"] and not partial["complete"]
          and partial["next_stage"] == SP.STEP[4] and ambiguous and complete["complete"] and term["terminal"])
    return ok, {"partial_next": partial["next_stage"], "ambiguous_refused": ambiguous}


def t12_event_step_mapping():
    ok = SP.memory_event_of_step(8) == 9 and SP.memory_event_of_step(9) == 10 and SP.memory_event_of_step(8) != 8
    return ok, {"step8": SP.memory_event_of_step(8)}


# ------------------------------------------------------------------ evaluation helpers
def t13_coverage_inclusive_12mm():
    import classroom_oracle1_eval as EV
    surf = np.array([[0.0, 0.0, 0.0]])
    ref = np.array([[0.012, 0.0, 0.0], [0.0, 0.0119, 0.0], [0.0, 0.0, 0.0121], [0.006, 0.006, 0.006],
                    [0.008, 0.008, 0.008]])
    got = EV._covered(ref, surf, 0.012).tolist()
    want = [True, True, False, True, False]
    neg = EV._covered(ref, surf, 0.025).tolist() != want
    return got == want and neg, {"got": got}


def t14_solid_angle_weights():
    import breadth1_spec as B1S
    w = B1S.row_weights()
    total = float(w.sum() * SP.B1_WIDTH)
    ok = abs(total - 4 * math.pi) < 1e-12 and len(w) == SP.B1_HEIGHT
    mask = np.zeros((SP.B1_HEIGHT, SP.B1_WIDTH), bool)
    mask[180, :] = True
    ring = CORE.weighted(mask, w)
    ok2 = abs(ring - SP.B1_WIDTH * w[180]) < 1e-15
    neg = abs(CORE.weighted(mask, np.ones_like(w)) - ring) > 1e-3
    return ok and ok2 and neg, {"sphere": total}


def t15_world_to_head():
    import fsg_geometry as FG
    rng = np.random.default_rng(20261006)
    p_h = rng.normal(size=(20, 3))
    c = {"head_R_wh": FG.HEAD_R_WH.tolist(), "head_origin_w_m": FG.HEAD_ORIGIN_W.tolist()}
    p_w = FG.head_to_world(c, p_h)
    back = CORE.head_points(p_w, FG.HEAD_R_WH, FG.HEAD_ORIGIN_W)
    neg = np.abs(((p_w - FG.HEAD_ORIGIN_W) @ np.asarray(FG.HEAD_R_WH).T) - p_h).max() > 1e-6   # transposed is wrong
    return float(np.abs(back - p_h).max()) < 1e-12 and neg, {"max_err": float(np.abs(back - p_h).max())}


def t16_reference_mask():
    inst = np.array([[172, 172, 0], [202, 172, 172]])
    pos = np.array([[[1, 2, 3], [0, 0, 0], [1, 1, 1]], [[1, 1, 1], [np.nan, 0, 0], [2, 2, 2]]], np.float64)
    m = CORE.reference_mask(inst, pos, 172)
    want = np.array([[True, False, False], [False, False, True]])
    return bool(np.array_equal(m, want)), {"mask": m.tolist()}


def t17_ply_persistent_only():
    g1 = (172, np.array([[0, 0, -1.0], [0, 1, -1.0]]), np.array([[0.5, 0.5, 0.5], [1, 1, 1.0]]))
    g2 = (202, np.array([[1, 0, -2.0]]), None)
    b = CORE.ply_bytes([g1, g2], "NS1e synthetic\nPERSISTENT MAPS ONLY")
    r = CORE.ply_read(b)
    ok = len(r["xyz"]) == 3 and list(r["entity_id"]) == [172, 172, 202] and "PERSISTENT MAPS ONLY" in r["comments"]
    try:
        CORE.ply_read(b[:-1])
        neg = False
    except ValueError:
        neg = True
    return ok and neg, {"entities": r["entity_id"].tolist()}


def t18_outcome_labels():
    q = CORE.control_outcome({"kind": "closed", "closure": {"quiet": [1, 2], "residual": [], "seed_residues": []}})
    r = CORE.control_outcome({"kind": "closed", "closure": {"quiet": [1], "residual": [[2, "ACTIONABLE",
                                                                                         "final_probe_rejected"]],
                                                            "seed_residues": []}})
    cap = CORE.control_outcome({"kind": "cap", "cap": 239})
    bd = CORE.terminal_breakdown({}, {"1": {"local": "QUIET", "disposition": "NORMAL", "reason": None},
                                      "2": {"local": "ACTIONABLE", "disposition": "FINALIZED",
                                            "reason": "final_probe_rejected"},
                                      "3": {"local": "ACTIONABLE", "disposition": "FINALIZED",
                                            "reason": "final_probe_executed"}})
    ok = (q["outcome"] == "1Q" and r["outcome"] == "1R" and cap["outcome"] == "2" and q["scope"] == SP.SCOPE_CLOSED
          and cap["scope"] == SP.SCOPE_CAP and bd["finalized_final_probe_rejected"] == [2]
          and bd["finalized_final_probe_executed_still_actionable"] == [3] and not bd["global_quiescence_warranted"])
    return ok, {"q": q["outcome"], "r": r["outcome"], "cap": cap["outcome"]}


def t19_target_patch_only_target():
    xyz = np.arange(15, dtype=np.float64).reshape(5, 3)
    ids = np.array([202, 212, 202, -1, 0])
    valid = np.array([True, True, True, False, True])
    p = CORE.target_patch(xyz, valid, ids, np.ones((5, 3)), 202, 8)
    ok = p["points"] == 2 and np.all(p["instance_id"] == 202) and p["patch_id"] == "ns1e_step_008" and p["frame"] == "H0"
    return ok, {"points": p["points"]}


def t20_references_and_rescope():
    rec = {"looks": [{"calibration": "run:steps/step-07/x.json", "state": "ns1a:y.npz"}],
           "evidence": {"path": "run:contexts/e.npz"}, "map": {"path": "run:steps/step-07/m.npz"}}
    r2 = CORE.rescope(rec)
    ok = (r2["looks"][0]["calibration"] == "ns1c2:steps/step-07/x.json" and r2["looks"][0]["state"] == "ns1a:y.npz"
          and r2["map"]["path"].startswith("ns1c2:") and rec["map"]["path"].startswith("run:"))
    here = CORE.resolve("run:a/b", Path("/tmp/ns1e-run")) == Path("/tmp/ns1e-run/a/b")
    there = CORE.resolve("ns1c2:a", Path("/tmp/x")) == SP.NS1C2_RUN / "a"
    return ok and here and there, {"rescoped": r2["looks"][0]["calibration"]}


TESTS = {f.__name__: f for f in (t01_append_once_and_order, t02_routing_every_positive_id_no_zero,
                                 t03_m2_revision_cross_target, t04_effective_geometry_map_first_duplicates_kept,
                                 t05_cap_formula_and_bound, t06_cap_expected_handoff_numbers, t07_resume_equivalence,
                                 t08_reactivation_only_through_revision, t09_gate_only_in_residue,
                                 t10_residue_procedure, t11_step_classification, t12_event_step_mapping,
                                 t13_coverage_inclusive_12mm, t14_solid_angle_weights, t15_world_to_head,
                                 t16_reference_mask, t17_ply_persistent_only, t18_outcome_labels,
                                 t19_target_patch_only_target, t20_references_and_rescope)}


def run_all() -> dict:
    res = {}
    for k, fn in TESTS.items():
        try:
            ok, detail = fn()
        except Exception as exc:  # noqa: BLE001  (a crash is a failure of that test)
            ok, detail = False, {"error": repr(exc)}
        res[k] = {"pass": bool(ok), "detail": CORE.jsonable(detail)}
    failed = [k for k, v in res.items() if not v["pass"]]
    return {"schema": "NS1e-synthetic-v1", "truth": SP.TRUTH_DERIVED, "tests": res, "failed": failed,
            "count": len(res), "marker": "NS1E_SYNTHETIC_PASS" if not failed else "NS1E_SYNTHETIC_FAIL"}


if __name__ == "__main__":
    r = run_all()
    for k, v in r["tests"].items():
        print(f"[ns1e-synthetic] {'PASS' if v['pass'] else 'FAIL'} {k}")
    print(f"[ns1e-synthetic] {r['marker']} {r['count'] - len(r['failed'])}/{r['count']}")
    print(json.dumps({k: v["detail"] for k, v in r["tests"].items() if not v["pass"]}, default=str)[:4000])
