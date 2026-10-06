"""North Star-1c2: the accepted Controller-02 scene-loop semantics as a resumable state machine (Option A).

Contract: docs/north-star/ns1c2-controller02-phase-semantics-contract.md, section 6.

``SceneMachine`` mirrors ``fov3d.control.controller02.run_controller02`` statement by statement, with the loop body
split at the observation so that it can be driven one stage per process and resumed from a JSON record:

- ``decide(final_gate)``: everything ``run_controller02`` does between two observations -- the NORMAL decision of the
  accepted ``schedule_normal`` (phase return to NORMAL, cap, bout, the natural-reactivation reason), or the RESIDUE
  procedure (ascending deferred ids; QUIET -> finalized without a look; ACTIONABLE -> the unchanged current ProbeResult to
  the final-look gate; rejected -> finalized; admitted -> one final observation), or closure;
- ``commit(plan, outcome, probe, revision)``: everything ``execute`` does after ``observe`` (fixations, seed handling,
  finalization of an executed final look, the refresh with its deferral rule and events, the action record).

It uses the accepted types directly (``ObjectStatus``, ``Disposition``, ``ScenePhase``, ``schedule_normal``,
``FinalProbeDecision``, ``integrated.ProbeResult`` / ``Observe`` / ``can_act`` / ``choose_action``) and edits nothing in
``fov3d``.  ``GateGuard`` substitutes the accepted Classroom ``final_look_gate_v1`` by a wrapper that records every call
with the scene phase and refuses any call outside RESIDUE.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
from typing import Any, Callable, Hashable

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from fov3d.control import controller02 as c2  # noqa: E402  (accepted, unchanged)
from fov3d.control import integrated as ic  # noqa: E402  (accepted, unchanged)

S = ic.ServiceState
D = c2.Disposition
P = c2.ScenePhase
GATE_FILE = "fov3d/experiments/classroom_oracle/controller02.py"
GATE_NAME = "final_look_gate_v1"


class GateOutsideResidue(RuntimeError):
    """``final_look_gate_v1`` was called while the scene phase is not RESIDUE."""


# ------------------------------------------------------------------ the gate guard
class GateGuard:
    """Every loaded copy of the accepted Classroom ``final_look_gate_v1`` is replaced, while active, by a wrapper that
    records the call with ``self.phase`` and raises ``GateOutsideResidue`` unless the phase is RESIDUE."""

    _active: "GateGuard | None" = None

    def __init__(self, phase: str = P.NORMAL.value, label: str = "") -> None:
        self.phase = str(phase)
        self.label = label
        self.calls: list[dict[str, Any]] = []
        self.refused: list[dict[str, Any]] = []
        self.saved: list[tuple[Any, Any]] = []

    @staticmethod
    def copies() -> list[tuple[str, Any]]:
        want = (REPO / GATE_FILE).resolve()
        out = []
        for name, mod in list(sys.modules.items()):
            f = getattr(mod, "__file__", None)
            if f and Path(f).resolve() == want:
                out.append((name, mod))
        return sorted(out, key=lambda t: t[0])

    def __enter__(self) -> "GateGuard":
        from fov3d.experiments.classroom_oracle import controller02  # noqa: F401  (load before substituting)
        if GateGuard._active is not None:
            raise RuntimeError("a gate guard is already active (nesting refused)")
        for _name, mod in self.copies():
            original = getattr(mod, GATE_NAME)
            if getattr(original, "__ns1c2_guard__", False):
                raise RuntimeError("final_look_gate_v1 is already guarded")
            guard = self

            def guarded(*a, __original=original, **k):
                rec = {"phase": guard.phase, "label": guard.label, "call": len(guard.calls) + 1}
                guard.calls.append(rec)
                if guard.phase != P.RESIDUE.value:
                    guard.refused.append(rec)
                    raise GateOutsideResidue(f"final_look_gate_v1 called while the scene phase is {guard.phase}")
                return __original(*a, **k)
            guarded.__ns1c2_guard__ = True
            self.saved.append((mod, original))
            setattr(mod, GATE_NAME, guarded)
        if not self.saved:
            raise RuntimeError("no loaded copy of the accepted Classroom Controller-02 module")
        GateGuard._active = self
        return self

    def __exit__(self, *exc) -> None:
        for mod, original in reversed(self.saved):
            setattr(mod, GATE_NAME, original)
        GateGuard._active = None

    def record(self) -> dict[str, Any]:
        by = {}
        for c in self.calls:
            by[c["phase"]] = by.get(c["phase"], 0) + 1
        return {"label": self.label, "calls": len(self.calls), "calls_by_phase": by,
                "normal_calls": by.get(P.NORMAL.value, 0), "refused": len(self.refused),
                "residue_calls": by.get(P.RESIDUE.value, 0), "mechanism": f"{GATE_FILE}:{GATE_NAME} substituted in "
                "every loaded module copy; raises GateOutsideResidue unless the scene phase is RESIDUE"}


# ------------------------------------------------------------------ serialization of the accepted types
def probe_to_json(r: ic.ProbeResult) -> dict[str, Any]:
    a = r.action
    return {"action": None if a is None else {"target_id": int(a.target_id),
                                              "gaze_deg": [float(a.gaze_yaw_pitch_deg[0]), float(a.gaze_yaw_pitch_deg[1])],
                                              "source": a.source},
            "detail": copy.deepcopy(dict(r.detail))}


def probe_from_json(d: dict[str, Any], vergence, focus) -> ic.ProbeResult:
    a = d["action"]
    act = None if a is None else ic.Observe(int(a["target_id"]), tuple(a["gaze_deg"]), vergence, focus, a["source"])
    return ic.ProbeResult(act, copy.deepcopy(d.get("detail") or {}))


def status_to_json(s: c2.ObjectStatus) -> list:
    return [int(s.instance_id), s.local.value, s.disposition.value, s.reason]


def status_from_json(v: list) -> c2.ObjectStatus:
    return c2.ObjectStatus(int(v[0]), S(v[1]), D(v[2]), v[3])


def _key(x) -> Any:
    return list(x) if isinstance(x, tuple) else x


# ------------------------------------------------------------------ the machine
class SceneMachine:
    """The ``run_controller02`` state, resumable.  Callbacks are passed per call (``probe``, ``revision``,
    ``final_gate``), so a stage process can rebuild the machine from its record and drive one step."""

    def __init__(self, order, *, budget: int, vergence, focus, seeds=None, unlocated=()) -> None:
        self.order = sorted(int(i) for i in order)
        self.budget = int(budget)
        self.vergence, self.focus = dict(vergence), dict(focus)
        self.seeds = {int(k): (float(v[0]), float(v[1])) for k, v in (seeds or {}).items()}
        self.unlocated_ids = tuple(sorted({int(u) for u in unlocated} - set(self.order)))
        self.initialized: list[int] = []
        self.disposition: dict[int, tuple[D, str | None]] = {i: (D.NORMAL, None) for i in self.order}
        self.fixations = {i: 0 for i in self.order}
        self.cache: dict[int, tuple[Hashable, ic.ProbeResult]] = {}
        self.last_probe: dict[int, ic.ProbeResult] = {}
        self.quiet_probe: dict[int, ic.ProbeResult] = {}
        self.quiet_since: dict[int, int | None] = {}
        self.reactivated_since_attended: set[int] = set()
        self.events: list[dict[str, Any]] = []
        self.actions: list[dict[str, Any]] = []
        self.phases: list[dict[str, Any]] = [{"phase": P.NORMAL.value, "from_global_step": 0}]
        self.residue_decisions: list[dict[str, Any]] = []
        self.final_observed: list[int] = []
        self.final_rejected: list[int] = []
        self.gate_log: list[dict[str, Any]] = []
        self.calls = 0
        self.hits = 0
        self.recorded = {i: c2.ObjectStatus(i, S.SEEDABLE) for i in self.order}
        self.statuses = dict(self.recorded)
        self.phase = P.NORMAL
        self.current: int | None = None
        self.bout = 0
        self.step = 0
        self.terminal: dict[str, Any] | None = None
        self.on_event: Callable[[dict], None] | None = None

    # -- run_controller02 internals, verbatim semantics
    def emit(self, event: dict[str, Any]) -> None:
        self.events.append(event)
        if self.on_event is not None:
            self.on_event(event)

    def probe_now(self, i: int, probe, revision) -> ic.ProbeResult:
        key = _key(revision(i)) if revision is not None else None
        if revision is not None and i in self.cache and self.cache[i][0] == key:
            self.hits += 1
            return self.cache[i][1]
        result = probe(i)
        self.calls += 1
        if not isinstance(result, ic.ProbeResult):
            raise TypeError("the service probe must return a ProbeResult")
        if result.action is not None and int(result.action.target_id) != i:
            raise ValueError(f"probe of object {i} proposed an action for {result.action.target_id}")
        if revision is not None:
            self.cache[i] = (key, result)
        return result

    def status(self, i: int, probe, revision) -> c2.ObjectStatus:
        if i not in self.initialized:
            local = S.SEEDABLE
        else:
            result = self.probe_now(i, probe, revision)
            self.last_probe[i] = result
            local = S.ACTIONABLE if ic.can_act(result) else S.QUIET
        disp, why = self.disposition[i]
        if disp is D.NORMAL and local is S.ACTIONABLE and self.fixations[i] >= self.budget:
            self.disposition[i] = (D.DEFERRED, "ordinary_budget")
            disp, why = self.disposition[i]
        return c2.ObjectStatus(i, local, disp, why)

    def refresh(self, step: int, trigger: int, probe, revision) -> dict[int, c2.ObjectStatus]:
        now: dict[int, c2.ObjectStatus] = {}
        for i in self.order:
            prev, cur = self.recorded[i], self.status(i, probe, revision)
            now[i] = cur
            was_normal = prev.disposition is D.NORMAL
            if was_normal and prev.local is S.QUIET and cur.local is not S.QUIET:
                self.emit({
                    "event": "natural_reactivation", "object": i, "global_step": step,
                    "trigger_target": trigger, "quiet_since_step": self.quiet_since.pop(i, None),
                    "state_after": cur.label, "fixations": self.fixations[i],
                    "probe_before": dict(self.quiet_probe.pop(i).detail),
                    "probe_after": dict(self.last_probe[i].detail),
                })
                self.reactivated_since_attended.add(i)
            if cur.disposition is D.NORMAL and cur.local is S.QUIET and prev.local is not S.QUIET:
                self.quiet_since[i] = step
                self.quiet_probe[i] = self.last_probe[i]
                self.emit({"event": "quiet", "object": i, "global_step": step, "trigger_target": trigger,
                           "previous_state": prev.label, "fixations": self.fixations[i],
                           "probe": dict(self.last_probe[i].detail)})
            if cur.disposition is D.DEFERRED and was_normal:
                self.emit({"event": "deferred", "object": i, "global_step": step, "trigger_target": trigger,
                           "reason": cur.reason, "previous_state": prev.label, "local_state": cur.local.value,
                           "fixations": self.fixations[i], "probe": dict(self.last_probe[i].detail)})
            elif not was_normal and prev.local is not cur.local:
                self.emit({"event": "local_state_change", "object": i, "global_step": step,
                           "trigger_target": trigger, "disposition": cur.disposition.value,
                           "previous_local_state": prev.local.value, "local_state": cur.local.value,
                           "fixations": self.fixations[i]})
        self.recorded.update(now)
        return now

    def finalize(self, i: int, reason: str, step: int) -> None:
        self.disposition[i] = (D.FINALIZED, reason)
        st = c2.ObjectStatus(i, self.statuses[i].local, D.FINALIZED, reason)
        self.statuses[i] = self.recorded[i] = st
        self.emit({"event": "finalized", "object": i, "global_step": step, "reason": reason,
                   "local_state": st.local.value, "fixations": self.fixations[i]})

    # -- resume point: an already initialized scene (no history is replayed, no event is emitted)
    def resume_initialized(self, fixations: dict, *, current: int, bout: int, step: int, probe, revision) -> None:
        self.initialized = list(self.order)
        self.fixations = {i: int(fixations[i]) for i in self.order}
        self.current, self.bout, self.step = int(current), int(bout), int(step)
        for i in self.order:
            self.statuses[i] = self.status(i, probe, revision)
        self.recorded = dict(self.statuses)

    # -- the loop body up to the observation
    def decide(self, final_gate=None, action_cap: int | None = None) -> dict[str, Any]:
        """One pass of ``run_controller02``'s ``while`` loop up to ``execute``; non-observing residue decisions are
        consumed in place.  Returns an attend / final_residue plan, or closed / cap."""
        while True:
            decision = c2.schedule_normal(self.current, self.statuses.values())
            if decision is not None:
                if self.phase is P.RESIDUE:
                    self.phase = P.NORMAL
                    self.phases.append({"phase": self.phase.value, "from_global_step": self.step})
                if action_cap is not None and self.step >= int(action_cap):
                    self.terminal = {"type": "CapReached", "cap": int(action_cap)}
                    return {"kind": "cap", "cap": int(action_cap)}
                i = int(decision.target_id)
                before = self.statuses[i]
                if before.local is S.SEEDABLE:
                    action = ic.Observe(i, tuple(self.seeds[i]), self.vergence, self.focus, ic.SEED_SOURCE)
                    proposal = None
                else:
                    proposing = self.last_probe[i]
                    action = ic.choose_action(proposing)
                    if action is None:
                        raise AssertionError(f"scheduler selected object {i} without an action")
                    proposal = dict(proposing.detail)
                reason = decision.reason
                if reason == "switch" and i in self.reactivated_since_attended:
                    reason = "natural_reactivation"
                self.reactivated_since_attended.discard(i)
                if decision.reason in ("initial", "switch"):
                    self.bout += 1
                return self._plan(i, action, before, str(decision.reason), str(reason), proposal, "attend")

            pending = [i for i in self.order if self.disposition[i][0] is D.DEFERRED]
            if not pending:
                self.phase = P.CLOSED
                self.phases.append({"phase": self.phase.value, "from_global_step": self.step})
                self.terminal = self._closure()
                return {"kind": "closed", "closure": self.terminal}
            if self.phase is P.NORMAL:
                self.phase = P.RESIDUE
                self.phases.append({"phase": self.phase.value, "from_global_step": self.step, "deferred": list(pending)})
            i = pending[0]
            now = self.statuses[i]
            if now.local is S.QUIET:
                self.residue_decisions.append({"object": i, "global_step": self.step, "local_state": now.local.value,
                                               "outcome": "quiet_before_final_probe"})
                self.finalize(i, "quiet_before_final_probe", self.step)
                continue
            proposing = self.last_probe[i]
            self.gate_log.append({"object": i, "global_step": self.step, "phase": self.phase.value})
            verdict = final_gate(i, proposing)
            if not isinstance(verdict, c2.FinalProbeDecision):
                raise TypeError("the final-look gate must return a FinalProbeDecision")
            entry = {"object": i, "global_step": self.step, "local_state": now.local.value,
                     "proposal": {"gaze_deg": list(proposing.action.gaze_yaw_pitch_deg),
                                  "source": proposing.action.source, "summary": dict(proposing.detail)},
                     "admissible": verdict.admissible, "reason": verdict.reason, "detail": dict(verdict.detail)}
            self.emit({"event": "final_probe_decision", "object": i, "global_step": self.step,
                       "admissible": verdict.admissible, "reason": verdict.reason,
                       "proposal_gaze_deg": entry["proposal"]["gaze_deg"],
                       "proposal_source": entry["proposal"]["source"]})
            if not verdict.admissible:
                entry["outcome"] = "final_probe_rejected"
                self.residue_decisions.append(entry)
                self.final_rejected.append(i)
                self.finalize(i, "final_probe_rejected", self.step)
                continue
            if action_cap is not None and self.step >= int(action_cap):
                self.terminal = {"type": "CapReached", "cap": int(action_cap)}
                return {"kind": "cap", "cap": int(action_cap)}
            entry["outcome"] = "final_probe_executed"
            self.residue_decisions.append(entry)
            if self.current != i:
                self.bout += 1
            self.final_observed.append(i)
            return self._plan(i, proposing.action, now, c2.FINAL_RESIDUE_DECISION, c2.FINAL_RESIDUE_DECISION,
                              dict(proposing.detail), "final_residue", entry=len(self.residue_decisions) - 1)

    def _plan(self, i, action, before, decision, reason, proposal, kind, entry=None) -> dict[str, Any]:
        return {"kind": kind, "target_id": int(i), "action": action, "before": before, "decision": decision,
                "reason": reason, "proposal": proposal, "phase": self.phase.value, "global_step": self.step,
                "object_local_step": self.fixations[i], "previous_object": self.current, "attention_bout": self.bout,
                "states_before": {str(k): s.label for k, s in self.statuses.items()}, "residue_entry": entry}

    # -- the loop body after the observation
    def commit(self, plan: dict[str, Any], outcome: ic.ObservationOutcome, probe, revision) -> dict[str, Any]:
        i, action, before, decision = plan["target_id"], plan["action"], plan["before"], plan["decision"]
        step = self.step
        self.fixations[i] += 1
        first_event = len(self.events)
        if before.local is S.SEEDABLE:
            if outcome.initialized:
                self.initialized.append(i)
                self.emit({"event": "seed_initialized", "object": i, "global_step": step, "trigger_target": i})
            else:
                self.finalize(i, "seed_uninitializable", step)
        if decision == c2.FINAL_RESIDUE_DECISION:
            self.finalize(i, "final_probe_executed", step)
        self.statuses = self.refresh(step, i, probe, revision)
        record = {
            "global_step": step,
            "phase": self.phase.value,
            "target_id": i,
            "gaze_deg": list(action.gaze_yaw_pitch_deg),
            "action_source": action.source,
            "vergence": dict(action.vergence),
            "focus": dict(action.focus),
            "service_state_before": before.label,
            "scheduler_decision": decision,
            "scheduler_reason": plan["reason"],
            "previous_object": self.current,
            "current_object_transition": "retain" if self.current == i else f"{self.current}->{i}",
            "attention_bout": self.bout,
            "object_local_step": plan["object_local_step"],
            "target_fixations_after": self.fixations[i],
            "proposal": plan["proposal"],
            **outcome.record,
            "service_states_before": plan["states_before"],
            "service_states_after": {str(k): s.label for k, s in self.statuses.items()},
            "events": [{"event": e["event"], "object": e["object"]} for e in self.events[first_event:]],
        }
        if plan["kind"] == "final_residue" and plan.get("residue_entry") is not None:
            self.residue_decisions[plan["residue_entry"]]["local_state_after"] = self.statuses[i].local.value
        self.actions.append(record)
        self.current = i
        self.step += 1
        return record

    def _closure(self) -> dict[str, Any]:
        quiet, residual, seed = [], [], []
        for i in self.order:
            st = self.statuses[i]
            if st.serviceable or st.disposition is D.DEFERRED:
                raise AssertionError(f"scene closure with object {i} still in service ({st.label})")
            if st.disposition is D.FINALIZED and st.reason == "seed_uninitializable":
                seed.append(i)
            elif st.local is S.QUIET:
                quiet.append(i)
            else:
                residual.append([i, st.local.value, str(st.reason)])
        return {"type": "closure", "quiet": quiet, "residual": residual, "seed_residues": seed,
                "unlocated": list(self.unlocated_ids), "final_observations": list(self.final_observed),
                "final_rejections": list(self.final_rejected)}

    # -- persistence
    def to_json(self) -> dict[str, Any]:
        return {
            "order": self.order, "budget": self.budget, "vergence": self.vergence, "focus": self.focus,
            "seeds": {str(k): list(v) for k, v in self.seeds.items()}, "unlocated": list(self.unlocated_ids),
            "initialized": list(self.initialized),
            "disposition": {str(k): [v[0].value, v[1]] for k, v in self.disposition.items()},
            "fixations": {str(k): v for k, v in self.fixations.items()},
            "cache": {str(k): {"revision": v[0], "probe": probe_to_json(v[1])} for k, v in self.cache.items()},
            "last_probe": {str(k): probe_to_json(v) for k, v in self.last_probe.items()},
            "quiet_probe": {str(k): probe_to_json(v) for k, v in self.quiet_probe.items()},
            "quiet_since": {str(k): v for k, v in self.quiet_since.items()},
            "reactivated_since_attended": sorted(self.reactivated_since_attended),
            "phases": copy.deepcopy(self.phases), "residue_decisions": copy.deepcopy(self.residue_decisions),
            "final_observed": list(self.final_observed), "final_rejected": list(self.final_rejected),
            "gate_log": copy.deepcopy(self.gate_log), "calls": self.calls, "hits": self.hits,
            "recorded": {str(k): status_to_json(v) for k, v in self.recorded.items()},
            "statuses": {str(k): status_to_json(v) for k, v in self.statuses.items()},
            "phase": self.phase.value, "current": self.current, "bout": self.bout, "step": self.step,
            "terminal": copy.deepcopy(self.terminal), "events_emitted": len(self.events),
            "actions_committed": len(self.actions),
        }

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "SceneMachine":
        m = cls(d["order"], budget=d["budget"], vergence=d["vergence"], focus=d["focus"],
                seeds={int(k): v for k, v in d["seeds"].items()}, unlocated=d["unlocated"])
        pj = lambda x: probe_from_json(x, m.vergence, m.focus)  # noqa: E731
        m.initialized = [int(i) for i in d["initialized"]]
        m.disposition = {int(k): (D(v[0]), v[1]) for k, v in d["disposition"].items()}
        m.fixations = {int(k): int(v) for k, v in d["fixations"].items()}
        m.cache = {int(k): (v["revision"], pj(v["probe"])) for k, v in d["cache"].items()}
        m.last_probe = {int(k): pj(v) for k, v in d["last_probe"].items()}
        m.quiet_probe = {int(k): pj(v) for k, v in d["quiet_probe"].items()}
        m.quiet_since = {int(k): v for k, v in d["quiet_since"].items()}
        m.reactivated_since_attended = {int(i) for i in d["reactivated_since_attended"]}
        m.phases = copy.deepcopy(d["phases"])
        m.residue_decisions = copy.deepcopy(d["residue_decisions"])
        m.final_observed = [int(i) for i in d["final_observed"]]
        m.final_rejected = [int(i) for i in d["final_rejected"]]
        m.gate_log = copy.deepcopy(d["gate_log"])
        m.calls, m.hits = int(d["calls"]), int(d["hits"])
        m.recorded = {int(k): status_from_json(v) for k, v in d["recorded"].items()}
        m.statuses = {int(k): status_from_json(v) for k, v in d["statuses"].items()}
        m.phase = P(d["phase"])
        m.current = None if d["current"] is None else int(d["current"])
        m.bout, m.step = int(d["bout"]), int(d["step"])
        m.terminal = copy.deepcopy(d["terminal"])
        return m


# ------------------------------------------------------------------ an in-memory driver (known answers)
def run_machine(machine: SceneMachine, *, observe, probe, final_gate, revision=None, action_cap=None,
                max_steps: int | None = None) -> SceneMachine:
    """Drive the machine like ``run_controller02`` drives its loop (decide -> observe -> commit) to closure / cap."""
    n = 0
    while max_steps is None or n < max_steps:
        plan = machine.decide(final_gate, action_cap)
        if plan["kind"] in ("closed", "cap"):
            break
        outcome = observe(machine.step, plan["action"], plan["object_local_step"])
        machine.commit(plan, outcome, probe, revision)
        n += 1
    return machine


def normal_local_state(result: ic.ProbeResult) -> ic.ServiceState:
    """Accepted Controller-02 NORMAL classification: ACTIONABLE iff the ProbeResult carries an action (any source)."""
    return S.ACTIONABLE if ic.can_act(result) else S.QUIET
