"""Integrated Foveal Controller: Controller-02 scene-level loop semantics (residual closure).

Contract: docs/controller/controller-02-residual-closure-contract.md.

Controller-02 separates an object's local perceptual/service state from its scene-level service
disposition:

- the local state keeps Controller-01's meanings (UNLOCATED, SEEDABLE, ACTIONABLE, QUIET) and is
  always recomputed from memory; BLOCKED is never used;
- the disposition says what the scene still spends on the object: NORMAL (ordinary service),
  DEFERRED (ordinary budget reached; awaiting its one residue decision) or FINALIZED (no further
  own-target observation);
- the scene phase is NORMAL, RESIDUE or CLOSED.

In the NORMAL phase the loop is Controller-01's (same retain/switch order, same probe cache by
revision, same quiet/natural-reactivation events) except that an ACTIONABLE object at the ordinary
budget is DEFERRED instead of blocked.  When no NORMAL object needs service, each DEFERRED object
receives exactly one residue decision: a QUIET one is finalized without a look; an ACTIONABLE one's
unchanged local proposal goes to an experiment-supplied final-look gate, and at most one admitted
final observation is executed.  A final observation may return the scene to NORMAL service.  The
scene closes honestly -- possibly with ACTIONABLE residual objects -- and SCENE_CLOSED is never
global quiescence.  There is no local fixation policy here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Hashable, Iterable, Mapping

from fov3d.control import integrated as ic

S = ic.ServiceState
LOCAL_STATES = frozenset({S.UNLOCATED, S.SEEDABLE, S.ACTIONABLE, S.QUIET})


class Disposition(str, Enum):
    NORMAL = "NORMAL"
    DEFERRED = "DEFERRED"
    FINALIZED = "FINALIZED"


class ScenePhase(str, Enum):
    NORMAL = "NORMAL"
    RESIDUE = "RESIDUE"
    CLOSED = "CLOSED"


DEFER_REASONS = ("ordinary_budget",)
FINALIZATION_REASONS = ("seed_uninitializable", "quiet_before_final_probe", "final_probe_rejected",
                        "final_probe_executed")
FINAL_RESIDUE_DECISION = "final_residue"
SCENE_CLOSED = "scene_closed"


@dataclass(frozen=True)
class ObjectStatus:
    """One object's local service state together with its scene-level disposition."""

    instance_id: int
    local: ic.ServiceState
    disposition: Disposition = Disposition.NORMAL
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.local not in LOCAL_STATES:
            raise ValueError(f"local state must be one of {sorted(s.value for s in LOCAL_STATES)}, got {self.local!r}")
        if not isinstance(self.disposition, Disposition):
            raise TypeError(f"disposition must be a Disposition, got {self.disposition!r}")
        allowed = {Disposition.NORMAL: (None,), Disposition.DEFERRED: DEFER_REASONS,
                   Disposition.FINALIZED: FINALIZATION_REASONS}[self.disposition]
        if self.reason not in allowed:
            raise ValueError(f"reason {self.reason!r} is not valid for {self.disposition.value}")

    @property
    def label(self) -> str:
        if self.disposition is Disposition.NORMAL:
            return self.local.value
        return f"{self.local.value}/{self.disposition.value}:{self.reason}"

    @property
    def serviceable(self) -> bool:
        """Ordinary service is spent only on NORMAL objects that are SEEDABLE or ACTIONABLE."""
        return self.disposition is Disposition.NORMAL and self.local in ic.SERVICEABLE


@dataclass(frozen=True)
class FinalProbeDecision:
    """The final-look gate's admissibility verdict over one unchanged local proposal."""

    admissible: bool
    reason: str
    detail: Mapping[str, Any] = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.admissible, bool) or not isinstance(self.reason, str) or not self.reason:
            raise ValueError("a final-probe decision needs a bool verdict and a non-empty reason")


@dataclass(frozen=True)
class SceneClosed:
    """The honest successful terminal: everything the scene will do has been done.

    It is not global quiescence: residual objects may still be locally ACTIONABLE.
    """

    quiet: tuple[int, ...]
    residual: tuple[tuple[int, str, str], ...]  # (instance id, local state, finalization reason)
    seed_residues: tuple[int, ...]
    unlocated: tuple[int, ...]
    final_observations: tuple[int, ...]
    final_rejections: tuple[int, ...]
    reason: str = SCENE_CLOSED

    def __post_init__(self) -> None:
        if self.reason != SCENE_CLOSED:
            raise ValueError("SceneClosed is reserved for scene_closed")
        groups = [set(self.quiet), {r[0] for r in self.residual}, set(self.seed_residues), set(self.unlocated)]
        if sum(len(g) for g in groups) != len(set().union(*groups)):
            raise ValueError("quiet, residual, seed-residue and unlocated objects must be disjoint")


def schedule_normal(current_id: int | None, statuses: Iterable[ObjectStatus]) -> ic.Decision | None:
    """Controller-01's deterministic retain/switch order over NORMAL-serviceable objects only.

    Returns None when no NORMAL object needs ordinary service (ordinary work exhausted).
    """
    rows = sorted(statuses, key=lambda s: int(s.instance_id))
    by_id = {int(s.instance_id): s for s in rows}
    if len(by_id) != len(rows):
        raise ValueError("duplicate instance ids in scheduler input")
    serviceable = [int(s.instance_id) for s in rows if s.serviceable]
    if current_id is not None:
        current = by_id.get(int(current_id))
        if current is None:
            raise ValueError(f"current object {current_id} is not a localized object")
        if current.serviceable:
            return ic.Decision("attend", int(current_id), "retain")
        if serviceable:
            forward = [i for i in serviceable if i > int(current_id)]
            return ic.Decision("attend", forward[0] if forward else serviceable[0], "switch")
    elif serviceable:
        return ic.Decision("attend", serviceable[0], "initial")
    return None


@dataclass
class Controller02Result:
    actions: list[dict[str, Any]]
    events: list[dict[str, Any]]
    final: dict[int, ObjectStatus]
    terminal: SceneClosed | ic.CapReached
    fixations: dict[int, int]
    initialized: list[int]
    probe_calls: int
    probe_cache_hits: int
    phases: list[dict[str, Any]]
    residue_decisions: list[dict[str, Any]]


def run_controller02(
    seeds: Mapping[int, tuple[float, float]],
    *,
    observe: Callable[[int, ic.Observe, int], ic.ObservationOutcome],
    probe: Callable[[int], ic.ProbeResult],
    final_gate: Callable[[int, ic.ProbeResult], FinalProbeDecision],
    vergence: Mapping[str, Any],
    focus: Mapping[str, Any],
    budget: int,
    revision: Callable[[int], Hashable] | None = None,
    unlocated: Iterable[int] = (),
    action_cap: int | None = None,
    on_event: Callable[[dict[str, Any]], None] | None = None,
    on_action: Callable[[dict[str, Any]], None] | None = None,
) -> Controller02Result:
    """Run the Controller-02 scene loop until SCENE_CLOSED or the explicit cap.

    ``observe``, ``probe`` and ``revision`` have Controller-01's meanings.  ``budget`` is the
    ordinary-service budget (fixations) at which an ACTIONABLE object is deferred.
    ``final_gate(i, proposal)`` receives the object's current, unchanged ``ProbeResult``; an
    admitted proposal's own ``action`` is executed exactly once.
    """
    order = sorted(int(i) for i in seeds)
    unlocated_ids = tuple(sorted({int(u) for u in unlocated} - set(order)))
    initialized: list[int] = []
    disposition: dict[int, tuple[Disposition, str | None]] = {i: (Disposition.NORMAL, None) for i in order}
    fixations = {i: 0 for i in order}
    cache: dict[int, tuple[Hashable, ic.ProbeResult]] = {}
    last_probe: dict[int, ic.ProbeResult] = {}
    quiet_probe: dict[int, ic.ProbeResult] = {}
    quiet_since: dict[int, int | None] = {}
    reactivated_since_attended: set[int] = set()
    events: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    phases: list[dict[str, Any]] = [{"phase": ScenePhase.NORMAL.value, "from_global_step": 0}]
    residue_decisions: list[dict[str, Any]] = []
    final_observed: list[int] = []
    final_rejected: list[int] = []
    calls = 0
    hits = 0

    def emit(event: dict[str, Any]) -> None:
        events.append(event)
        if on_event is not None:
            on_event(event)

    def probe_now(i: int) -> ic.ProbeResult:
        nonlocal calls, hits
        key = revision(i) if revision is not None else None
        if revision is not None and i in cache and cache[i][0] == key:
            hits += 1
            return cache[i][1]
        result = probe(i)
        calls += 1
        if not isinstance(result, ic.ProbeResult):
            raise TypeError("the service probe must return a ProbeResult")
        if result.action is not None and int(result.action.target_id) != i:
            raise ValueError(f"probe of object {i} proposed an action for {result.action.target_id}")
        if revision is not None:
            cache[i] = (key, result)
        return result

    def status(i: int) -> ObjectStatus:
        if i not in initialized:
            local = S.SEEDABLE
        else:
            result = probe_now(i)
            last_probe[i] = result
            local = S.ACTIONABLE if ic.can_act(result) else S.QUIET
        disp, why = disposition[i]
        if disp is Disposition.NORMAL and local is S.ACTIONABLE and fixations[i] >= budget:
            disposition[i] = (Disposition.DEFERRED, "ordinary_budget")
            disp, why = disposition[i]
        return ObjectStatus(i, local, disp, why)

    recorded = {i: ObjectStatus(i, S.SEEDABLE) for i in order}

    def refresh(step: int, trigger: int) -> dict[int, ObjectStatus]:
        now: dict[int, ObjectStatus] = {}
        for i in order:
            prev, cur = recorded[i], status(i)
            now[i] = cur
            was_normal = prev.disposition is Disposition.NORMAL
            if was_normal and prev.local is S.QUIET and cur.local is not S.QUIET:
                emit({
                    "event": "natural_reactivation", "object": i, "global_step": step,
                    "trigger_target": trigger, "quiet_since_step": quiet_since.pop(i, None),
                    "state_after": cur.label, "fixations": fixations[i],
                    "probe_before": dict(quiet_probe.pop(i).detail),
                    "probe_after": dict(last_probe[i].detail),
                })
                reactivated_since_attended.add(i)
            if cur.disposition is Disposition.NORMAL and cur.local is S.QUIET and prev.local is not S.QUIET:
                quiet_since[i] = step
                quiet_probe[i] = last_probe[i]
                emit({"event": "quiet", "object": i, "global_step": step, "trigger_target": trigger,
                      "previous_state": prev.label, "fixations": fixations[i],
                      "probe": dict(last_probe[i].detail)})
            if cur.disposition is Disposition.DEFERRED and was_normal:
                emit({"event": "deferred", "object": i, "global_step": step, "trigger_target": trigger,
                      "reason": cur.reason, "previous_state": prev.label, "local_state": cur.local.value,
                      "fixations": fixations[i], "probe": dict(last_probe[i].detail)})
            elif not was_normal and prev.local is not cur.local:
                emit({"event": "local_state_change", "object": i, "global_step": step,
                      "trigger_target": trigger, "disposition": cur.disposition.value,
                      "previous_local_state": prev.local.value, "local_state": cur.local.value,
                      "fixations": fixations[i]})
        recorded.update(now)
        return now

    def finalize(i: int, reason: str, step: int) -> None:
        disposition[i] = (Disposition.FINALIZED, reason)
        st = ObjectStatus(i, statuses[i].local, Disposition.FINALIZED, reason)
        statuses[i] = recorded[i] = st
        emit({"event": "finalized", "object": i, "global_step": step, "reason": reason,
              "local_state": st.local.value, "fixations": fixations[i]})

    statuses = dict(recorded)
    phase = ScenePhase.NORMAL
    current: int | None = None
    bout = 0
    step = 0

    def execute(i: int, action: ic.Observe, before: ObjectStatus, decision: str, reason: str,
                proposal: dict[str, Any] | None) -> ObjectStatus:
        nonlocal statuses, bout
        states_before = {str(k): s.label for k, s in statuses.items()}
        local_step = fixations[i]
        outcome = observe(step, action, local_step)
        fixations[i] += 1
        first_event = len(events)
        if before.local is S.SEEDABLE:
            if outcome.initialized:
                initialized.append(i)
                emit({"event": "seed_initialized", "object": i, "global_step": step, "trigger_target": i})
            else:
                finalize(i, "seed_uninitializable", step)
        if decision == FINAL_RESIDUE_DECISION:
            finalize(i, "final_probe_executed", step)
        statuses = refresh(step, i)
        record = {
            "global_step": step,
            "phase": phase.value,
            "target_id": i,
            "gaze_deg": list(action.gaze_yaw_pitch_deg),
            "action_source": action.source,
            "vergence": dict(action.vergence),
            "focus": dict(action.focus),
            "service_state_before": before.label,
            "scheduler_decision": decision,
            "scheduler_reason": reason,
            "previous_object": current,
            "current_object_transition": "retain" if current == i else f"{current}->{i}",
            "attention_bout": bout,
            "object_local_step": local_step,
            "target_fixations_after": fixations[i],
            "proposal": proposal,
            **outcome.record,
            "service_states_before": states_before,
            "service_states_after": {str(k): s.label for k, s in statuses.items()},
            "events": [{"event": e["event"], "object": e["object"]} for e in events[first_event:]],
        }
        actions.append(record)
        if on_action is not None:
            on_action(record)
        return statuses[i]

    terminal: SceneClosed | ic.CapReached
    while True:
        decision = schedule_normal(current, statuses.values())
        if decision is not None:
            if phase is ScenePhase.RESIDUE:
                phase = ScenePhase.NORMAL
                phases.append({"phase": phase.value, "from_global_step": step})
            if action_cap is not None and step >= int(action_cap):
                terminal = ic.CapReached(int(action_cap))
                break
            i = int(decision.target_id)  # type: ignore[arg-type]
            before = statuses[i]
            if before.local is S.SEEDABLE:
                action = ic.Observe(i, tuple(seeds[i]), vergence, focus, ic.SEED_SOURCE)
                proposal = None
            else:
                proposing = last_probe[i]
                action = ic.choose_action(proposing)
                if action is None:
                    raise AssertionError(f"scheduler selected object {i} without an action")
                proposal = dict(proposing.detail)
            reason = decision.reason
            if reason == "switch" and i in reactivated_since_attended:
                reason = "natural_reactivation"
            reactivated_since_attended.discard(i)
            if decision.reason in ("initial", "switch"):
                bout += 1
            execute(i, action, before, str(decision.reason), str(reason), proposal)
            current = i
            step += 1
            continue

        # ---- ordinary work is exhausted: one residue decision per DEFERRED object, ascending id
        pending = [i for i in order if disposition[i][0] is Disposition.DEFERRED]
        if not pending:
            phase = ScenePhase.CLOSED
            phases.append({"phase": phase.value, "from_global_step": step})
            terminal = _closure(statuses, order, unlocated_ids, final_observed, final_rejected)
            break
        if phase is ScenePhase.NORMAL:
            phase = ScenePhase.RESIDUE
            phases.append({"phase": phase.value, "from_global_step": step, "deferred": list(pending)})
        i = pending[0]
        now = statuses[i]
        if now.local is S.QUIET:
            residue_decisions.append({"object": i, "global_step": step, "local_state": now.local.value,
                                      "outcome": "quiet_before_final_probe"})
            finalize(i, "quiet_before_final_probe", step)
            continue
        proposing = last_probe[i]
        verdict = final_gate(i, proposing)
        if not isinstance(verdict, FinalProbeDecision):
            raise TypeError("the final-look gate must return a FinalProbeDecision")
        entry = {"object": i, "global_step": step, "local_state": now.local.value,
                 "proposal": {"gaze_deg": list(proposing.action.gaze_yaw_pitch_deg), "source": proposing.action.source,
                              "summary": dict(proposing.detail)},
                 "admissible": verdict.admissible, "reason": verdict.reason, "detail": dict(verdict.detail)}
        emit({"event": "final_probe_decision", "object": i, "global_step": step,
              "admissible": verdict.admissible, "reason": verdict.reason,
              "proposal_gaze_deg": entry["proposal"]["gaze_deg"], "proposal_source": entry["proposal"]["source"]})
        if not verdict.admissible:
            entry["outcome"] = "final_probe_rejected"
            residue_decisions.append(entry)
            final_rejected.append(i)
            finalize(i, "final_probe_rejected", step)
            continue
        if action_cap is not None and step >= int(action_cap):
            terminal = ic.CapReached(int(action_cap))
            break
        entry["outcome"] = "final_probe_executed"
        residue_decisions.append(entry)
        if current != i:
            bout += 1
        final_observed.append(i)
        after = execute(i, proposing.action, now, FINAL_RESIDUE_DECISION, FINAL_RESIDUE_DECISION, dict(proposing.detail))
        entry["local_state_after"] = after.local.value
        current = i
        step += 1

    return Controller02Result(actions, events, dict(statuses), terminal, fixations, initialized, calls, hits,
                              phases, residue_decisions)


def _closure(statuses: Mapping[int, ObjectStatus], order: list[int], unlocated: tuple[int, ...],
             final_observed: list[int], final_rejected: list[int]) -> SceneClosed:
    quiet, residual, seed = [], [], []
    for i in order:
        st = statuses[i]
        if st.serviceable or st.disposition is Disposition.DEFERRED:
            raise AssertionError(f"scene closure with object {i} still in service ({st.label})")
        if st.disposition is Disposition.FINALIZED and st.reason == "seed_uninitializable":
            seed.append(i)
        elif st.local is S.QUIET:
            quiet.append(i)
        else:
            residual.append((i, st.local.value, str(st.reason)))
    return SceneClosed(tuple(quiet), tuple(residual), tuple(seed), unlocated, tuple(final_observed),
                       tuple(final_rejected))
