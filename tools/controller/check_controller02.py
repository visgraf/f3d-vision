#!/usr/bin/env python3
"""Fail-capable checks for Controller-02 residual closure.

    .venv/bin/python tools/controller/check_controller02.py                      # generic unit + gate + architecture
    .venv/bin/python tools/controller/check_controller02.py --run OUT --source SRC \
        [--audit01a A --c01b B --c01c C]                                         # + Classroom replay checks A-L

Contract: docs/controller/controller-02-residual-closure-contract.md.  The unit checks are
Blender-free and synthetic.  Every behavioral check is also run against negative controls --
source-level mutants of fov3d/control/controller02.py or of the Classroom gate functions -- that
must be rejected, so each check is shown to be able to fail.  ``--run`` validates a completed
replay from its compact output and controller-time source artifacts; the Controller-01A/01B/01C
artifacts, when given, are validation references only.  It never opens evaluation truth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import types

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import numpy as np

import fov3d  # noqa: F401
from fov3d.control import controller02 as c2
from fov3d.control import frontier, integrated as ic, object_policy
from fov3d.experiments.classroom_oracle import controller01 as c01
from fov3d.experiments.classroom_oracle import controller02 as x2
from fov3d.geometry import core as geom

PREFIX = "[controller02-check]"
MAIN = "6306458cf508712d4d1065b68708ca73f351c65d"
FROZEN = ("fov3d/control/integrated.py", "fov3d/experiments/classroom_oracle/controller01.py")
NEW_FOV3D = ("fov3d/control/controller02.py", "fov3d/experiments/classroom_oracle/controller02.py")
C2_SRC = (REPO / NEW_FOV3D[0]).read_text()
X2_SRC = (REPO / NEW_FOV3D[1]).read_text()
V, F = c01.VERGENCE, c01.FOCUS
S = ic.ServiceState
D = c2.Disposition
CAP = 400
checked = 0
failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global checked, failed
    checked += 1
    failed += not ok
    print(f"{PREFIX} {'PASS' if ok else 'FAIL'} {name}{'' if ok or not detail else ': ' + detail}")


def errors_of(fn, *a) -> list[str]:
    try:
        return list(fn(*a))
    except Exception as exc:  # noqa: BLE001
        return [f"{type(exc).__name__}: {exc}"]


def verified(name: str, body, real: tuple, controls: dict[str, tuple]) -> None:
    errs = errors_of(body, *real)
    check(name, not errs, "; ".join(errs[:3]))
    for label, args in controls.items():
        check(f"{name.split()[0]} control rejected: {label}", bool(errors_of(body, *args)), "the control mutant passed")


_mutant_count = 0


def mutant(src: str, old: str, new: str, base: str):
    """A throwaway module built from ``src`` with one exact replacement."""
    global _mutant_count
    if src.count(old) != 1:
        raise AssertionError(f"mutation site not unique ({src.count(old)}): {old[:60]!r}")
    _mutant_count += 1
    name = f"_{base}_mutant_{_mutant_count}"
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    exec(compile(src.replace(old, new), name, "exec"), mod.__dict__)
    return mod


def c2m(old: str, new: str):
    return mutant(C2_SRC, old, new, "c2")


def x2m(old: str, new: str):
    return mutant(X2_SRC, old, new, "x2")


# ---------------------------------------------------------------- synthetic scenes

class Scene:
    """A synthetic experiment: object i is ACTIONABLE until it has had need(i) own looks.

    ``bonus`` adds own-look requirements to an object when another object's look occurs, and
    ``relief`` removes an object's remaining need when another object has had enough looks:
    simple cross-object evidence for reactivation and deferred-QUIET cases.
    """

    def __init__(self, need, *, seed_fail=(), bonus=None, relief=None):
        self.need = dict(need)
        self.looks = {i: 0 for i in need}
        self.seed_fail = set(seed_fail)
        self.bonus = dict(bonus or {})     # (trigger object, trigger own-look number) -> (object, extra)
        self.relief = dict(relief or {})   # object -> (other object, looks needed of it)
        self.log: list[ic.Observe] = []
        self.gate_calls: list[tuple[int, ic.ProbeResult]] = []
        self.gate_current: list[ic.ProbeResult | None] = []
        self.last: dict[int, ic.ProbeResult] = {}

    def observe(self, step, action, local):
        i = int(action.target_id)
        self.log.append(action)
        self.looks[i] += 1
        key = (i, self.looks[i])
        if key in self.bonus:
            j, extra = self.bonus[key]
            self.need[j] += extra
        if action.source == ic.SEED_SOURCE:
            return ic.ObservationOutcome(initialized=i not in self.seed_fail)
        return ic.ObservationOutcome(initialized=None)

    def probe(self, i):
        rel = self.relief.get(i)
        quiet = self.looks[i] >= self.need[i] or (rel is not None and self.looks[rel[0]] >= rel[1])
        r = ic.ProbeResult(None if quiet else ic.Observe(i, (float(i), float(self.looks[i])), V, F, "fsg6f"),
                           {"looks": self.looks[i]})
        self.last[i] = r
        return r

    def gate(self, verdicts):
        def g(i, proposal):
            self.gate_calls.append((i, proposal))
            self.gate_current.append(self.last.get(i))
            ok = verdicts(i) if callable(verdicts) else bool(verdicts)
            return c2.FinalProbeDecision(ok, "admit" if ok else "reject")
        return g


def run(m, scene: Scene, verdicts=False, budget=24, unlocated=()):
    return m.run_controller02({i: (float(i), 0.5) for i in scene.need}, observe=scene.observe, probe=scene.probe,
                              final_gate=scene.gate(verdicts), vergence=V, focus=F, budget=budget,
                              unlocated=unlocated, action_cap=CAP)


def closed(res) -> list[str]:
    return [] if isinstance(res.terminal, c2.SceneClosed) else [f"terminal {res.terminal!r}"]


# ---------------------------------------------------------------- generic tests 1-12, 14, 18

def t01_below_budget_normal(m):
    sc = Scene({1: 5})
    res = run(m, sc, budget=24)
    errs = closed(res)
    ord1 = [a for a in res.actions if a["target_id"] == 1]
    if len(ord1) != 5 or any(a["phase"] != "NORMAL" for a in ord1):
        errs.append(f"expected seed + 4 ordinary looks (need 5 looks), got {[a['phase'] for a in ord1]}")
    if any("DEFERRED" in s for a in res.actions for s in a["service_states_after"].values()):
        errs.append("deferred below budget")
    if res.final[1].disposition is not D.NORMAL or res.final[1].local is not S.QUIET:
        errs.append(f"final {res.final[1].label}")
    return errs


def t02_budget_defers(m):
    sc = Scene({1: 30})
    res = run(m, sc, budget=3)
    errs = closed(res)
    ev = [e for e in res.events if e["event"] == "deferred"]
    if len(ev) != 1 or ev[0]["reason"] != "ordinary_budget" or ev[0]["fixations"] != 3 or ev[0]["local_state"] != "ACTIONABLE":
        errs.append(f"deferred events {ev}")
    labels = {s for a in res.actions for s in list(a["service_states_after"].values()) + [a["service_state_before"]]}
    if any("BLOCKED" in s for s in labels) or any(e["event"] == "blocked" for e in res.events):
        errs.append("BLOCKED used")
    if sum(1 for a in res.actions if a["phase"] == "NORMAL") != 3:
        errs.append("ordinary looks beyond the budget")
    return errs


def t03_deferred_not_serviced(m):
    sc = Scene({1: 30, 2: 6})
    res = run(m, sc, budget=3)
    errs = closed(res)
    n1 = sum(1 for a in res.actions if a["target_id"] == 1 and a["phase"] == "NORMAL")
    step_def = next(e["global_step"] for e in res.events if e["event"] == "deferred")
    after = [a["target_id"] for a in res.actions if a["global_step"] > step_def and a["phase"] == "NORMAL"]
    if n1 != 3 or 1 in after:
        errs.append(f"deferred object serviced: {n1} ordinary looks; after deferral {after}")
    return errs


def t04_deferred_quiet_finalizes(m):
    sc = Scene({1: 30, 2: 8}, relief={1: (2, 8)})  # 2's looks make the deferred object 1 quiet
    res = run(m, sc, verdicts=True, budget=10)
    errs = closed(res)
    fin = [e for e in res.events if e["event"] == "finalized" and e["object"] == 1]
    if [e["reason"] for e in fin] != ["quiet_before_final_probe"] or sc.gate_calls:
        errs.append(f"finalized {fin}; gate calls {len(sc.gate_calls)}")
    if any(a["phase"] == "RESIDUE" for a in res.actions) or 1 not in res.terminal.quiet:
        errs.append("a final look was taken or the object is not quiet at closure")
    return errs


def t05_rejected_no_look(m):
    sc = Scene({1: 30, 2: 3})
    res = run(m, sc, verdicts=False, budget=3)
    errs = closed(res)
    if any(a["phase"] == "RESIDUE" for a in res.actions):
        errs.append("a rejected proposal was executed")
    if not errs and (res.terminal.residual != ((1, "ACTIONABLE", "final_probe_rejected"),) or res.terminal.final_rejections != (1,)):
        errs.append(f"closure {res.terminal}")
    return errs


def t06_admitted_one_look(m):
    sc = Scene({1: 4, 2: 3})
    res = run(m, sc, verdicts=True, budget=3)
    errs = closed(res)
    fin = [a for a in res.actions if a["phase"] == "RESIDUE"]
    if len(fin) != 1 or fin[0]["target_id"] != 1 or fin[0]["scheduler_decision"] != c2.FINAL_RESIDUE_DECISION:
        errs.append(f"final looks {[(a['target_id'], a['scheduler_decision']) for a in fin]}")
    if not errs and (res.final[1].reason != "final_probe_executed" or 1 not in res.terminal.quiet
                     or res.terminal.final_observations != (1,)):
        errs.append(f"after the final look: {res.final[1].label}; {res.terminal}")
    return errs


def t07_still_actionable_residual(m):
    sc = Scene({1: 30, 2: 3})
    res = run(m, sc, verdicts=True, budget=3)
    errs = closed(res)
    fin = [a for a in res.actions if a["phase"] == "RESIDUE"]
    if len(fin) != 1 or len(sc.gate_calls) != 1:
        errs.append(f"{len(fin)} final looks, {len(sc.gate_calls)} gate calls")
    if not errs and res.terminal.residual != ((1, "ACTIONABLE", "final_probe_executed"),):
        errs.append(f"closure {res.terminal}")
    return errs


def t08_final_look_reactivates(m):
    sc = Scene({1: 30, 2: 2}, bonus={(1, 4): (2, 1)})  # 1's 4th own look (its final look) reactivates 2
    res = run(m, sc, verdicts=True, budget=3)
    errs = closed(res)
    phases = [p["phase"] for p in res.phases]
    fin = next((a["global_step"] for a in res.actions if a["phase"] == "RESIDUE"), None)
    later2 = [a for a in res.actions if a["target_id"] == 2 and fin is not None and a["global_step"] > fin]
    if phases[:4] != ["NORMAL", "RESIDUE", "NORMAL", "CLOSED"] or len(later2) != 1 or later2[0]["phase"] != "NORMAL":
        errs.append(f"phases {phases}; object 2 after the final look {[a['phase'] for a in later2]}")
    if not any(e["event"] == "natural_reactivation" and e["object"] == 2 for e in res.events):
        errs.append("no natural reactivation of object 2")
    return errs


def t09_residue_resumes(m):
    sc = Scene({1: 30, 2: 2, 3: 30}, bonus={(1, 4): (2, 1)})
    res = run(m, sc, verdicts=True, budget=3)
    errs = closed(res)
    phases = [p["phase"] for p in res.phases]
    order = [(a["target_id"], a["phase"]) for a in res.actions if a["global_step"] >= 8]
    if phases != ["NORMAL", "RESIDUE", "NORMAL", "RESIDUE", "CLOSED"]:
        errs.append(f"phases {phases}")
    if order != [(1, "RESIDUE"), (2, "NORMAL"), (3, "RESIDUE")]:
        errs.append(f"late actions {order}")
    return errs


def t10_seed_failure(m):
    sc = Scene({1: 3, 2: 2}, seed_fail={1})
    res = run(m, sc, budget=24)
    errs = closed(res)
    seeds1 = [a for a in res.actions if a["target_id"] == 1]
    if len(seeds1) != 1:
        errs.append(f"object 1 observed {len(seeds1)} times")
    if not errs and (res.terminal.seed_residues != (1,) or 1 in res.terminal.quiet or res.terminal.residual):
        errs.append(f"closure {res.terminal}")
    return errs


def t11_unlocated_separate(m):
    sc = Scene({1: 30, 2: 2})
    res = run(m, sc, verdicts=False, budget=3, unlocated=(50, 60))
    errs = closed(res)
    if not errs:
        t = res.terminal
        if t.unlocated != (50, 60) or any(r[0] in (50, 60) for r in t.residual) or {50, 60} & set(t.quiet):
            errs.append(f"closure {t}")
    return errs


def t12_close_with_actionable_residual(m):
    sc = Scene({1: 30, 2: 30, 3: 2})
    res = run(m, sc, verdicts=False, budget=3)
    errs = closed(res)
    if not errs and ({r[0] for r in res.terminal.residual} != {1, 2}
                     or any(r[1] != "ACTIONABLE" for r in res.terminal.residual) or res.terminal.quiet != (3,)):
        errs.append(f"closure {res.terminal}")
    return errs


def t14_exact_proposal(m):
    sc = Scene({1: 30, 2: 2})
    res = run(m, sc, verdicts=True, budget=3)
    errs = closed(res)
    if len(sc.gate_calls) != 1:
        return errs + [f"{len(sc.gate_calls)} gate calls"]
    i, proposal = sc.gate_calls[0]
    executed = [a for a in sc.log if a.target_id == 1][-1]
    if proposal is not sc.gate_current[0]:
        errs.append("the gate did not receive the object's current probe result")
    if executed is not proposal.action:
        errs.append(f"executed {executed} is not the proposal's own action {proposal.action}")
    return errs


def t18_no_second_residue_look(m):
    sc = Scene({1: 30, 2: 2}, bonus={(1, 4): (2, 1)})
    res = run(m, sc, verdicts=True, budget=3)
    errs = closed(res)
    n = sum(1 for a in res.actions if a["target_id"] == 1 and a["phase"] == "RESIDUE")
    calls = sum(1 for i, _ in sc.gate_calls if i == 1)
    if n != 1 or calls != 1:
        errs.append(f"object 1: {n} residue looks, {calls} gate calls")
    return errs


def e0_normal_equivalence(m, sched_mut=None):
    """Without budget hits, Controller-02 chooses Controller-01's actions and events."""
    rng = random.Random(20260929)
    errs = []
    for trial in range(60):
        ids = sorted(rng.sample(range(1, 40), rng.randint(2, 7)))
        need = {i: rng.randint(0, 6) for i in ids}
        bonus = {}
        for _ in range(rng.randint(0, 3)):
            a, b = rng.sample(ids, 2)
            bonus[(a, rng.randint(1, 3))] = (b, rng.randint(1, 2))
        s1, s2 = Scene(need, bonus=bonus), Scene(need, bonus=bonus)
        r1 = ic.run_control_loop({i: (float(i), 0.5) for i in ids}, observe=s1.observe, probe=s1.probe, vergence=V,
                                 focus=F, watchdog=24, action_cap=CAP)
        r2 = run(m, s2, budget=24)
        k = lambda a: (a["target_id"], tuple(a["gaze_deg"]), a["action_source"], a["scheduler_decision"],  # noqa: E731
                       a["scheduler_reason"], a["attention_bout"], a["object_local_step"])
        e = lambda ev: [(x["event"], x["object"], x["global_step"], x.get("trigger_target")) for x in ev  # noqa: E731
                        if x["event"] in ("seed_initialized", "quiet", "natural_reactivation")]
        if [k(a) for a in r1.actions] != [k(a) for a in r2.actions] or e(r1.events) != e(r2.events):
            errs.append(f"trial {trial} diverges")
            break
    return errs


def generic() -> None:
    real = (c2,)
    defer_off = c2m('            disposition[i] = (Disposition.DEFERRED, "ordinary_budget")\n            disp, why = disposition[i]\n',
                    "            pass\n")
    budget_gt = c2m("local is S.ACTIONABLE and fixations[i] >= budget", "local is S.ACTIONABLE and fixations[i] > budget")
    serve_deferred = c2m("return self.disposition is Disposition.NORMAL and self.local in ic.SERVICEABLE",
                         "return self.disposition is not Disposition.FINALIZED and self.local in ic.SERVICEABLE")
    gate_quiet = c2m("        if now.local is S.QUIET:\n", "        if False:\n")
    ignore_gate = c2m("        if not verdict.admissible:\n", "        if False:\n")
    never_final = c2m("        if not verdict.admissible:\n", "        if True:\n")
    second_final = c2m('            finalize(i, "final_probe_executed", step)\n',
                       '            disposition[i] = (Disposition.DEFERRED, "ordinary_budget")\n')
    no_return = c2m("        decision = schedule_normal(current, statuses.values())\n",
                    "        decision = schedule_normal(current, statuses.values()) if phase is not ScenePhase.RESIDUE else None\n")
    no_resume = c2m("        pending = [i for i in order if disposition[i][0] is Disposition.DEFERRED]\n",
                    "        pending = [i for i in order if disposition[i][0] is Disposition.DEFERRED] if len(phases) < 3 else []\n")
    seed_block = c2m('                finalize(i, "seed_uninitializable", step)\n', "                pass\n")
    unlocated_residual = c2m("    return SceneClosed(tuple(quiet), tuple(residual), tuple(seed), unlocated,",
                             "    return SceneClosed(tuple(quiet), tuple(residual) + tuple((u, 'UNLOCATED', 'final_probe_rejected') for u in unlocated), tuple(seed), (),")
    close_quiet_only = c2m("            residual.append((i, st.local.value, str(st.reason)))\n",
                           "            raise AssertionError('residual object at closure')\n")
    copy_proposal = c2m("        after = execute(i, proposing.action, now,",
                        "        after = execute(i, ic.Observe(i, proposing.action.gaze_yaw_pitch_deg, proposing.action.vergence, proposing.action.focus, proposing.action.source), now,")
    stale_proposal = c2m("        proposing = last_probe[i]\n        verdict = final_gate(i, proposing)\n",
                         "        proposing = last_probe[i]\n        verdict = final_gate(i, ic.ProbeResult(ic.Observe(i, proposing.action.gaze_yaw_pitch_deg, proposing.action.vergence, proposing.action.focus, proposing.action.source), {}))\n")
    switch_back = c2m("            return ic.Decision(\"attend\", forward[0] if forward else serviceable[0], \"switch\")",
                      "            return ic.Decision(\"attend\", serviceable[0], \"switch\")")
    verified("01 ACTIONABLE below budget stays NORMAL and serviceable", t01_below_budget_normal, real,
             {"deferral at 1 fixation": (c2m("fixations[i] >= budget", "fixations[i] >= 1"),)})
    verified("02 ACTIONABLE at the budget becomes DEFERRED, not BLOCKED", t02_budget_defers, real,
             {"no deferral": (defer_off,), "budget off by one": (budget_gt,)})
    verified("03 a DEFERRED object receives no ordinary service", t03_deferred_not_serviced, real,
             {"deferred still serviceable": (serve_deferred,), "no deferral": (defer_off,)})
    verified("04 a deferred QUIET object finalizes without a look", t04_deferred_quiet_finalizes, real,
             {"QUIET sent to the gate": (gate_quiet,)})
    verified("05 an inadmissible final proposal executes 0 looks; residual", t05_rejected_no_look, real,
             {"gate ignored": (ignore_gate,)})
    verified("06 an admissible final proposal executes exactly 1 look, then finalizes", t06_admitted_one_look, real,
             {"admitted proposal never executed": (never_final,), "second final look": (second_final,)})
    verified("07 still ACTIONABLE after its final look stays residual; no second look", t07_still_actionable_residual, real,
             {"second final look": (second_final,)})
    verified("08 a final observation reactivates a NORMAL object; phase returns to NORMAL", t08_final_look_reactivates, real,
             {"no return to NORMAL": (no_return,)})
    verified("09 residue processing resumes after the reactivated normal work", t09_residue_resumes, real,
             {"second residue pass dropped": (no_resume,), "no return to NORMAL": (no_return,)})
    verified("10 a seed-initialization failure does not block closure", t10_seed_failure, real,
             {"seed failure left in service": (seed_block,)})
    verified("11 unlocated objects stay separate from residuals", t11_unlocated_separate, real,
             {"unlocated counted residual": (unlocated_residual,)})
    verified("12 the scene may close with ACTIONABLE residuals", t12_close_with_actionable_residual, real,
             {"closure requires quiet": (close_quiet_only,)})
    verified("14 the gate receives and the loop executes the exact unchanged local proposal", t14_exact_proposal, real,
             {"a copied proposal is executed": (copy_proposal,), "gate sees a rebuilt proposal": (stale_proposal,)})
    verified("18 no second residue observation for a finalized object", t18_no_second_residue_look, real,
             {"second final look": (second_final,)})
    verified("E0 NORMAL phase equals Controller-01's loop on 60 random synthetic scenes", e0_normal_equivalence, real,
             {"switch without the forward rule": (switch_back,)})
    # Types refuse BLOCKED and inconsistent dispositions; SceneClosed is not global quiescence.
    errs = []
    for bad in ((S.BLOCKED, D.NORMAL, None), (S.ACTIONABLE, D.DEFERRED, None), (S.QUIET, D.FINALIZED, "watchdog"),
                (S.ACTIONABLE, D.NORMAL, "ordinary_budget")):
        try:
            c2.ObjectStatus(1, *bad)
            errs.append(f"accepted {bad}")
        except (ValueError, TypeError):
            pass
    try:
        c2.SceneClosed((1,), ((1, "ACTIONABLE", "final_probe_rejected"),), (), (), (), (1,))
        errs.append("overlapping quiet/residual accepted")
    except ValueError:
        pass
    check("T  ObjectStatus refuses BLOCKED and inconsistent dispositions; SceneClosed groups are disjoint; "
          "SceneClosed != global quiescence", not errs and c2.SCENE_CLOSED != ic.GLOBAL_QUIESCENCE, "; ".join(errs))


# ---------------------------------------------------------------- the Classroom gate (tests 15-17)

def synthetic_gate_case():
    """A small synthetic FSG6f situation (the sealed self-test's map patch) with an FSG6f decision."""
    FR = frontier._legacy_impl
    cal = geom.make_calibration("small", 0.0, 0.0, 2.10)
    n = int(cal["core_size"])
    ids = np.full((n, n), 7, np.int32)
    sup = np.ones((n, n), bool)
    geometry = FR._xyz_patch((-11, 1), (-11, 1))
    d = object_policy.choose_next(0.0, 0.0, cal, ids, sup, ids, sup, geometry, [(0.0, 0.0)], [], target_object_id=7)
    state = {"ids_left": ids, "raw_support_L": sup, "ids_right": ids, "raw_support_R": sup}
    proposal = ic.ProbeResult(ic.Observe(7, tuple(d["next_gaze_deg"]), V, F, "fsg6f"), {})
    kw = dict(decision=d, geometry=geometry, gaze=(0.0, 0.0), calibration=cal, state=state, history=[],
              visited=[(0.0, 0.0)], profile="small", head_r_wh=geom.HEAD_R_WH, head_origin_w=geom.HEAD_ORIGIN_W, target_id=7)
    return proposal, kw, cal, ids, sup


def g_admits_genuine(gx):
    proposal, kw, *_ = synthetic_gate_case()
    v = gx.final_look_gate_v1(proposal=proposal, **kw)
    c = v.detail.get("counts", {})
    if not v.admissible or v.reason != "novel_support_in_predicted_cores" or c.get("novel_service_count", 0) <= 0:
        return [f"{v.admissible} {v.reason} {c}"]
    return []


def g_prior_interrogation_rejects(gx):
    proposal, kw, cal, ids, sup = synthetic_gate_case()
    look = geom.make_calibration("small", *proposal.action.gaze_yaw_pitch_deg, 2.10)
    hist = [object_policy.history_entry(calibration=look, instance_L=ids, raw_support_L=sup, instance_R=ids,
                                        raw_support_R=sup, target_object_id=7)]
    v = gx.final_look_gate_v1(proposal=proposal, **{**kw, "history": hist})
    c = v.detail.get("counts", {})
    if v.admissible or c.get("in_both_cores", 0) <= 0 or c.get("previously_interrogated_in_both_cores") != c.get("in_both_cores"):
        return [f"{v.admissible} {v.reason} {c}"]
    return []


def t15_untraceable(gx):
    proposal, kw, *_ = synthetic_gate_case()
    cyc = ic.ProbeResult(ic.Observe(7, proposal.action.gaze_yaw_pitch_deg, V, F, "cyclopean_epistemic"), {})
    v = gx.final_look_gate_v1(proposal=cyc, **kw)
    return [] if (not v.admissible and v.reason == "untraceable_final_support") else [f"{v.admissible} {v.reason}"]


def t16_visited(gx):
    proposal, kw, *_ = synthetic_gate_case()
    v = gx.final_look_gate_v1(proposal=proposal, **{**kw, "visited": [(0.0, 0.0), tuple(proposal.action.gaze_yaw_pitch_deg)]})
    return [] if (not v.admissible and v.reason == "visited_final_gaze") else [f"{v.admissible} {v.reason}"]


def t17_resolved_not_counted(gx):
    t = np.array([[0.0, 0.0, -2.0], [0.3, 0.0, -2.0]])
    geometry = np.vstack([np.array([[0.005, 0.0, -2.0]]), np.random.default_rng(0).normal(0, 0.01, (150, 3)) + [3.0, 3.0, -5.0]])
    s = gx.serviceable_support(t, np.array([True, True]), np.array([True, True]), np.array([False, False]), geometry)
    errs = []
    if s["mapped_12mm"].tolist() != [True, False] or s["novel"].tolist() != [False, True]:
        errs.append(f"mapped {s['mapped_12mm'].tolist()} novel {s['novel'].tolist()}")
    return errs


def gate() -> None:
    real = (x2,)
    source_blind = x2m('    if act.source != "fsg6f":\n', "    if False:\n")
    visited_blind = x2m("    if any(_same_gaze(act.gaze_yaw_pitch_deg, v) for v in visited):\n", "    if False:\n")
    radius_blind = x2m("    mapped = FR._target_mapped_mask(t, geometry) if len(t) else np.zeros(0, bool)\n",
                       "    mapped = np.zeros(len(t), bool)\n")
    prior_blind = x2m("    novel = serviceable & ~np.asarray(prior, bool)\n", "    novel = serviceable\n")
    always_reject = x2m("    if novel > 0:\n", "    if False:\n")
    one_eye = x2m('    out["both"] = out["L"]["observable"] & out["R"]["observable"]\n',
                  '    out["both"] = out["L"]["observable"] | ~out["L"]["observable"]\n')
    verified("G1 the gate admits a genuinely serviceable, never-interrogated synthetic proposal", g_admits_genuine, real,
             {"gate that always rejects": (always_reject,)})
    verified("G2 support already binocularly interrogated by a prior own look is not novel", g_prior_interrogation_rejects,
             real, {"prior interrogation ignored": (prior_blind,)})
    verified("15 an unsupported/untraceable final-support source is rejected, not guessed", t15_untraceable, real,
             {"source not checked": (source_blind,)})
    verified("16 a duplicate visited final gaze is rejected", t16_visited, real, {"visited not checked": (visited_blind,)})
    verified("17 support already resolved within 12 mm is not counted", t17_resolved_not_counted, real,
             {"12 mm rule ignored": (radius_blind,)})

    def g3_core_known_answer(gx):
        # A point on the gaze ray is in both cores; a point 10 deg off-axis is in neither (core 12 deg).
        cal = geom.make_calibration("small", 3.0, 2.0, 2.10)
        on = geom.gaze_direction(3.0, 2.0) * 2.1
        off = geom.gaze_direction(13.0, 2.0) * 2.1
        c = gx.core_observability(cal, np.vstack([on, off]))
        return [] if c["both"].tolist() == [True, False] else [f"both {c['both'].tolist()}"]
    verified("G3 predicted-core known answer: on-axis point in both cores, 10 deg off-axis point in neither",
             g3_core_known_answer, real, {"one-eye/any test": (one_eye,)})


# ---------------------------------------------------------------- architecture

def architecture() -> None:
    def frozen_same(read):
        bad = [p for p in FROZEN if subprocess.run(["git", "show", f"{MAIN}:{p}"], cwd=REPO, capture_output=True,
                                                   check=True).stdout != read(p)]
        return [f"changed: {bad}"] if bad else []
    real_read = lambda p: (REPO / p).read_bytes()  # noqa: E731
    tampered = lambda p: (REPO / p).read_bytes() + (b"# edit\n" if p.endswith("controller01.py") else b"")  # noqa: E731
    verified("13 the frozen Controller-01 modules are byte-identical to main", frozen_same, (real_read,),
             {"one frozen file edited": (tampered,)})
    import ast
    bad = []
    for p in NEW_FOV3D:
        tree = ast.parse((REPO / p).read_text())
        for node in ast.walk(tree):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            bad += [f"{p}: {n}" for n in names if n == "tools" or n.startswith("tools.") or n in (
                "fsg6f_frontier", "fsg6f_public", "fsg_geometry", "fsg_stereo", "multiobject2c_policy",
                "classroom_oracle1_matcher", "fsg3_surface_map")]
    check("A  the new fov3d modules import accepted functionality only through fov3d.*", not bad, str(bad))
    src = C2_SRC
    check("A  the generic Controller-02 module has no Blender, subprocess, file I/O or local fixation policy",
          not any(w in src for w in ("subprocess", "blender", "open(", "choose_next", "extract_frontier")))

    def guard_blocks(guard_cls):
        g = guard_cls()
        with g:
            try:
                subprocess.run(["true"], check=False)
                return ["a process was launched under the guard"]
            except PermissionError:
                pass
        return [] if g.attempts else ["no attempt recorded"]

    class NoGuard:
        attempts: list = []

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None
    verified("C  the no-process guard refuses a process launch and records it", guard_blocks, (x2.NoProcessGuard,),
             {"no guard": (NoGuard,)})

    def forbidden_ok(pred):
        yes = ["/x/previews/controller-01-full/evaluation.json", "/x/previews/controller-01-full/bootstrap/evaluation_only/a.npz",
               "/x/previews/controller-01b-single-continuation/objects/instance_0210/acquisitions/fix_24/calibration.json",
               "/x/previews/controller-01c-frontier-action-correspondence/audit.json",
               "/x/previews/controller-01a-terminal-audit/audit.json"]
        no = ["/x/previews/controller-01-full/actions.json", "/x/previews/controller-01-full/bootstrap/seeds.json"]
        errs = [f"allowed {p}" for p in yes if not pred(p)] + [f"refused {p}" for p in no if pred(p)]
        return errs
    verified("D  the replay firewall refuses evaluation truth and the later 01A/01B/01C artifacts only",
             forbidden_ok, (x2.is_forbidden_during_replay,), {"evaluation-only predicate": (c01.is_evaluation_truth,)})


# ---------------------------------------------------------------- Classroom replay checks (--run)

def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run_checks(out: Path, source: Path, a01: Path | None, c01b: Path | None, c01c: Path | None) -> None:
    man = json.loads((out / "manifest.json").read_text())
    res = json.loads((out / "result.json").read_text())
    acts = json.loads((out / "actions.json").read_text())["actions"]
    evs = json.loads((out / "events.json").read_text())["events"]
    residue = json.loads((out / "final-residue.json").read_text())["residue_decisions"]
    acc = json.loads((source / "actions.json").read_text())
    acc_a, acc_e = acc["actions"], acc["events"]
    seeds = json.loads((source / "bootstrap/seeds.json").read_text())
    hashes = {n: sha(source / n) for n in x2.ACCEPTED_SOURCE}
    check("A  source Controller-01 hashes are the accepted ones (live and recorded)",
          hashes == x2.ACCEPTED_SOURCE == man["source_hashes"], str(hashes))
    check("C  no process was launched (guard active; 0 attempts)", man["process_guard"]["attempts"] == []
          and "subprocess.Popen" in man["process_guard"]["events"])
    opened = man["truth_firewall"]["opened_source_files"]
    check("D  truth firewall: 0 violations; no evaluation file and no 01A/01B/01C artifact opened",
          man["truth_firewall"]["violations"] == [] and not any(x2.is_forbidden_during_replay(str(source / p)) for p in opened)
          and all("controller-01" not in p for p in opened), f"{len(opened)} opened")
    normal = [a for a in acts if a["phase"] == "NORMAL"]
    key = lambda a: (int(a["target_id"]), tuple(a["gaze_deg"]), a["action_source"], a["scheduler_decision"],  # noqa: E731
                     a["scheduler_reason"], int(a["object_local_step"]), int(a["attention_bout"]))
    check("E  all 141 ordinary actions equal Controller-01's (target, gaze, source, scheduler decision/reason, local step, bout)",
          len(normal) == len(acc_a) == 141 and [key(a) for a in normal] == [key(a) for a in acc_a]
          and [a["global_step"] for a in normal] == list(range(141)) and man["replay"]["steps_verified"] == 141,
          f"{len(normal)} ordinary, verified {man['replay']['steps_verified']}")
    meas = ("target_valid_points", "measurement_memory_additions", "new_surfels", "active_map_size_after", "head_evidence")
    check("E  every ordinary action's measurement record and proposal summary equal Controller-01's",
          all(all(a[k] == b[k] for k in meas) and a["proposal"] == b["proposal"] for a, b in zip(normal, acc_a)))
    ek = lambda e: (e["event"], e["object"], e["global_step"], e.get("trigger_target"), e.get("quiet_since_step"),  # noqa: E731
                    e.get("fixations"))
    kinds = ("seed_initialized", "quiet", "natural_reactivation")
    mine = [ek(e) for e in evs if e["event"] in kinds]
    theirs = [ek(e) for e in acc_e if e["event"] in kinds]
    react = [(e["object"], e["global_step"], e["trigger_target"]) for e in evs if e["event"] == "natural_reactivation"]
    probes_ok = all(a.get("probe_before") == b.get("probe_before") and a.get("probe_after") == b.get("probe_after")
                    for a, b in zip([e for e in evs if e["event"] == "natural_reactivation"],
                                    [e for e in acc_e if e["event"] == "natural_reactivation"]))
    check("F  every NORMAL-object event equals Controller-01's; natural reactivations 109@7 (by 110) and 178@114 (by 224)",
          mine == theirs and react == [(109, 7, 110), (178, 114, 224)] and probes_ok, f"reactivations {react}")
    deferred = [e for e in evs if e["event"] == "deferred"]
    blocked_c01 = [e for e in acc_e if e["event"] == "blocked"]
    labels = {s for a in acts for s in list(a["service_states_after"].values()) + [a["service_state_before"]]}
    check("G  210 becomes DEFERRED (ordinary_budget, 24 fixations, ACTIONABLE) exactly where Controller-01 blocked it; "
          "nothing is BLOCKED",
          [(e["object"], e["global_step"], e["reason"], e["fixations"], e["local_state"]) for e in deferred]
          == [(210, 101, "ordinary_budget", 24, "ACTIONABLE")]
          and [(e["object"], e["global_step"]) for e in blocked_c01] == [(210, 101)]
          and not any("BLOCKED" in s for s in labels) and not any(e["event"] == "blocked" for e in evs))
    r210 = [r for r in residue if r["object"] == 210]
    d = r210[0]["detail"] if r210 else {}
    if a01 is not None:
        term = json.loads(a01.read_text())["terminal_probe"]
        check("H  210's final local probe reproduces the accepted final Controller-01 state (01A terminal probe; validation)",
              len(r210) == 1 and d.get("probe_summary") == term["summary"] and d.get("revision") == term["revision"]
              and r210[0]["proposal"]["gaze_deg"] == term["proposed_gaze_deg"] and r210[0]["proposal"]["source"] == term["source"],
              f"{d.get('revision')} {r210[0]['proposal'] if r210 else None}")
    pred = d.get("predicted_calibration")
    model = json.loads(json.dumps(x2.predicted_calibration(seeds["profile"], r210[0]["proposal"]["gaze_deg"], seeds["head_R_wh"],
                                                           seeds["head_origin_w_m"]))) if r210 else None
    exact = 0
    for a in acc_a:
        saved = json.loads((source / f"objects/instance_{a['target_id']:04d}/acquisitions/fix_{a['object_local_step']:02d}"
                                     "/calibration.json").read_text())
        exact += json.loads(json.dumps(x2.predicted_calibration(seeds["profile"], a["gaze_deg"], seeds["head_R_wh"],
                                                                seeds["head_origin_w_m"]))) == saved
    check("I  the predicted [7.6, 18.2] calibration is the sensor model's (make_calibration from the bootstrap head pose); "
          "known answer: the model reproduces all 141 saved calibrations exactly",
          pred is not None and pred == model and pred["gaze_yaw_pitch_deg"] == r210[0]["proposal"]["gaze_deg"]
          and exact == len(acc_a) == 141, f"exact {exact}/141")
    if c01b is not None:
        cal01b = json.loads((c01b / "objects/instance_0210/acquisitions/fix_24/calibration.json").read_text())
        check("I  validation only (not a decision input): the prediction equals Controller-01B's executed calibration",
              pred == cal01b)
    counts = d.get("counts", {})
    els = d.get("elements", [])
    check("J  the final-support reconstruction reproduces the selected candidate (30 OPEN of 43 raw; identity checks)",
          d.get("support_counts_open_raw_map_boundary") == [30, 43, 3, 10] and counts.get("support") == 30 == len(els)
          and all(d.get("identity", {}).values()) and len(d.get("identity", {})) == 4)
    if els:
        t = np.array([e["t_e"] for e in els])
        core = x2.core_observability(pred, t)
        recompute = [bool(v) for v in core["both"]] == [e["in_both_cores"] for e in els] \
            and [bool(v) for v in core["L"]["observable"]] == [e["in_left_core"] for e in els]
    else:
        recompute = False
    check("K  the final core-service computation is recomputed from the recorded t_e and calibration",
          recompute and counts.get("in_both_cores") == sum(e["in_both_cores"] for e in els)
          and counts.get("novel_service_count") == sum(e["novel"] for e in els), str(counts))
    if c01c is not None and els:
        audit = json.loads(c01c.read_text())
        sup = [e for e in audit["elements"] if e["open_support"]]
        same_ids = [e["frontier_index"] for e in sup] == [e["frontier_index"] for e in els] \
            and all(np.allclose(e["t_e"], f["t_e"], rtol=0, atol=1e-12) for e, f in zip(sup, els))
        same_core = all((e["look25_t"]["L"]["inside_core"] and e["look25_t"]["R"]["inside_core"]) == f["in_both_cores"]
                        for e, f in zip(sup, els))
        check("K  validation only (01C is not a decision input): same 30 support elements and t_e as the 01C audit, "
              "and the predicted in-both-cores flags equal 01C's measured ones for the executed look", same_ids and same_core)
    t = res.get("terminal", {})
    quiet, residual, unloc = res.get("quiet", []), res.get("residual", []), res.get("unlocated", [])
    consistent = (t.get("type") == "SCENE_CLOSED" and res.get("marker") == x2.SCENE_CLOSED_MARKER == man["marker"]
                  and len(quiet) + len(residual) + len(res.get("seed_residues", [])) == res["localized_objects"] == 25
                  and len(unloc) == res["unlocated_objects"] == 209 and not man["global_quiescence_claimed"]
                  and res["ordinary_observations"] == 141 and res["final_residue_observations"] == len(res["final_observations"])
                  and all(res["final_states"][str(q)]["local_state"] == "QUIET" for q in quiet)
                  and all(res["final_states"][str(r[0])]["local_state"] == r[1] != "QUIET"
                          and res["final_states"][str(r[0])]["disposition"] == "FINALIZED" for r in residual)
                  and all(s["disposition"] != "DEFERRED" for s in res["final_states"].values())
                  and [p["phase"] for p in res["phases"]][-1] == "CLOSED"
                  and set(res["final_rejections"]) == {r["object"] for r in residue if r["outcome"] == "final_probe_rejected"}
                  and "GLOBAL_QUIESCENCE" not in json.dumps(res).upper().replace("GLOBAL_QUIESCENCE_CLAIMED", ""))
    check("L  the scene terminal record is internally consistent (SCENE_CLOSED; groups partition the 25 localized objects; "
          "residuals FINALIZED and not QUIET; no deferred object left; no global quiescence)", consistent)


def replay_guards(source: Path, c01b: Path | None) -> None:
    """The replay refuses divergent or unevidenced actions and detects tampered source artifacts."""
    acc = json.loads((source / "actions.json").read_text())["actions"]
    a0 = acc[0]
    right = ic.Observe(int(a0["target_id"]), tuple(a0["gaze_deg"]), V, F, a0["action_source"])
    wrong = ic.Observe(int(a0["target_id"]), (a0["gaze_deg"][0], a0["gaze_deg"][1] + 0.05), V, F, a0["action_source"])

    def step0(src: Path, action: ic.Observe, step: int = 0) -> list[str]:
        with tempfile.TemporaryDirectory() as w:
            rp = x2.AcceptedReplay(REPO, src, Path(w))
            rp.observe(step, action, 0)
            return [] if rp.verified_steps == 1 else ["step not verified"]

    def refused(fn, exc) -> list[str]:
        try:
            fn()
            return ["accepted"]
        except exc:
            return []
    verified("R1 the replay accepts the accepted action and refuses a divergent gaze", lambda act: step0(source, act),
             (right,), {"gaze +0.05 deg": (wrong,)})
    check("R2 an action beyond the accepted 141 has no evidence and is refused (rendering not authorized)",
          not refused(lambda: step0(source, right, 141), x2.NoAcceptedEvidence))

    def fake_source(tamper: bool) -> Path:
        root = Path(tempfile.mkdtemp(prefix="c02-fake-source-"))
        rel = [f"objects/instance_{right.target_id:04d}/acquisitions/fix_00/{n}" for n in ("calibration.json", "oracle_observation.npz")]
        rel += ["manifest.json", "actions.json", "bootstrap/seeds.json", "bootstrap/instance_catalog.json",
                f"objects/instance_{right.target_id:04d}/maps/fix_00.npz"]
        for r in rel:
            (root / r).parent.mkdir(parents=True, exist_ok=True)
            os.symlink(source / r, root / r)
        pr = f"objects/instance_{right.target_id:04d}/patches/fix_00.npz"
        (root / pr).parent.mkdir(parents=True, exist_ok=True)
        z = c01._load_npz(source / pr)
        if tamper:
            v = np.argwhere(z["valid"])[0]
            z["xyz_h"] = z["xyz_h"].copy()
            z["xyz_h"][v[0], v[1], 2] += np.float32(0.001)
        np.savez_compressed(root / pr, **z)
        return root
    def on_fake(tamper: bool) -> list[str]:
        root = fake_source(tamper)
        try:
            return step0(root, right)
        finally:
            import shutil
            shutil.rmtree(root, ignore_errors=True)
    verified("R3 per-step verification detects a saved patch that differs by 1 mm in one point",
             on_fake, (False,), {"tampered patch": (True,)})
    if c01b is not None:
        target = c01b / "objects/instance_0210/acquisitions/fix_24/calibration.json"

        def read_under(pred) -> list[str]:
            with ic.TruthFirewall(source, pred):
                try:
                    target.read_bytes()
                    return ["read allowed"]
                except PermissionError:
                    return []
        verified("R4 the replay firewall refuses reading the Controller-01B look", read_under,
                 (x2.is_forbidden_during_replay,), {"evaluation-only firewall": (c01.is_evaluation_truth,)})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path)
    ap.add_argument("--source", type=Path)
    ap.add_argument("--audit01a", type=Path)
    ap.add_argument("--c01b", type=Path)
    ap.add_argument("--c01c", type=Path)
    a = ap.parse_args()
    generic()
    gate()
    architecture()
    if a.run is not None:
        if a.source is None:
            ap.error("--run needs --source")
        try:
            run_checks(a.run.resolve(), a.source.resolve(), a.audit01a, a.c01b, a.c01c)
            replay_guards(a.source.resolve(), a.c01b)
        except Exception as exc:  # noqa: BLE001
            check("run checks completed without error", False, f"{type(exc).__name__}: {exc}")
    print(f"{PREFIX} SUMMARY checked={checked} failed={failed}")
    if failed == 0:
        print(f"{PREFIX} CONTROLLER02_IMPLEMENTATION_CHECKS_PASS")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
