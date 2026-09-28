"""Integrated Foveal Controller: reusable scene-level control concepts (Controller 01).

Contract: docs/controller/controller-01-state-action-contract.md.

The controller state is ``S_t = (M_t, H_t, C_t)``: persistent causal memory, the global
executed action history and a small attentional context (the current object).  This module
owns only the reusable concepts over that state:

- the object service states and the small object summary the scheduler may see;
- the OBSERVE / STOP / INCOMPLETE decision types and the service-probe result;
- the deterministic retain/switch/stop scheduler;
- the generic closed control loop, which recomputes every object's service state from the
  current memory after each observation (a quiet object is only "quiet now");
- the target-relative intrinsic epistemic view ``E_t(i)`` derived from supplied causal memory;
- a process-wide truth firewall for controller-time file access.

It contains no Blender, no evaluator, no historical candidate/run/gaze policy and no local
fixation policy.  An experiment adapter supplies the observation, the service probe and the
memory revision.  There is deliberately no reactivation operation: a previously quiet object
becomes actionable again only because its recomputed probe says so.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import os
import sys
from typing import Any, Callable, Hashable, Iterable, Mapping

import numpy as np

from fov3d.epistemic.partition import REGION_KIND, build_epistemic_partition
from fov3d.scene.partition import SupportLayer, joint_owner, support_depth_from_map


class ServiceState(str, Enum):
    UNLOCATED = "UNLOCATED"
    SEEDABLE = "SEEDABLE"
    ACTIONABLE = "ACTIONABLE"
    QUIET = "QUIET"
    BLOCKED = "BLOCKED"


BLOCKED_REASONS = ("seed_uninitializable", "watchdog")
SERVICEABLE = frozenset({ServiceState.SEEDABLE, ServiceState.ACTIONABLE})
SEED_SOURCE = "oracle_seed"
PROBE_SOURCES = ("fsg6f", "cyclopean_epistemic")
GLOBAL_QUIESCENCE = "global_quiescence"


@dataclass(frozen=True)
class ObjectSummary:
    """Everything the scheduler may know about one object: identity and service state."""

    instance_id: int
    state: ServiceState
    blocked_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.state, ServiceState):
            raise TypeError(f"state must be a ServiceState, got {self.state!r}")
        if (self.state is ServiceState.BLOCKED) != (self.blocked_reason is not None):
            raise ValueError("blocked_reason is required for BLOCKED and forbidden otherwise")
        if self.blocked_reason is not None and self.blocked_reason not in BLOCKED_REASONS:
            raise ValueError(f"unknown blocked_reason {self.blocked_reason!r}")

    @property
    def label(self) -> str:
        return self.state.value if self.blocked_reason is None else f"BLOCKED:{self.blocked_reason}"


@dataclass(frozen=True)
class Observe:
    """One executed sensory action: OBSERVE(target, gaze, vergence, focus)."""

    target_id: int
    gaze_yaw_pitch_deg: tuple[float, float]
    vergence: Mapping[str, Any]
    focus: Mapping[str, Any]
    source: str

    def __post_init__(self) -> None:
        if self.source not in (SEED_SOURCE, *PROBE_SOURCES):
            raise ValueError(f"unknown action source {self.source!r}")
        y, p = (float(v) for v in self.gaze_yaw_pitch_deg)
        object.__setattr__(self, "gaze_yaw_pitch_deg", (y, p))


@dataclass(frozen=True)
class Stop:
    """The only successful terminal controller action."""

    reason: str = GLOBAL_QUIESCENCE

    def __post_init__(self) -> None:
        if self.reason != GLOBAL_QUIESCENCE:
            raise ValueError("STOP is reserved for global_quiescence")


@dataclass(frozen=True)
class Incomplete:
    """A non-success ending: some localized object is blocked."""

    reason: str
    blocked: tuple[tuple[int, str], ...]


@dataclass(frozen=True)
class CapReached:
    """A non-success, non-scientific ending at an explicit cost cap (smoke only)."""

    cap: int
    reason: str = "smoke_cap_reached"


@dataclass(frozen=True)
class Decision:
    kind: str  # "attend" or "terminal"
    target_id: int | None = None
    reason: str | None = None  # "initial", "retain" or "switch"
    terminal: Stop | Incomplete | None = None


@dataclass(frozen=True)
class ProbeResult:
    """One service-probe result.  ACTIONABLE iff it carries an action; QUIET otherwise."""

    action: Observe | None
    detail: Mapping[str, Any] = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        if self.action is not None and self.action.source not in PROBE_SOURCES:
            raise ValueError("a service probe proposes only post-seed actions")

    @property
    def state(self) -> ServiceState:
        return ServiceState.ACTIONABLE if self.action is not None else ServiceState.QUIET


def can_act(result: ProbeResult) -> bool:
    return result.action is not None


def choose_action(result: ProbeResult) -> Observe | None:
    return result.action


def catalog_summaries(catalog_ids: Iterable[int], localized_ids: Iterable[int]) -> dict[int, ObjectSummary]:
    """Initial summaries: SEEDABLE for bootstrap-localized objects, UNLOCATED for the rest."""
    catalog = sorted({int(i) for i in catalog_ids})
    localized = {int(i) for i in localized_ids}
    unknown = sorted(localized - set(catalog))
    if unknown:
        raise ValueError(f"localized ids missing from the catalog: {unknown}")
    return {
        i: ObjectSummary(i, ServiceState.SEEDABLE if i in localized else ServiceState.UNLOCATED)
        for i in catalog
    }


def schedule(current_id: int | None, summaries: Iterable[ObjectSummary]) -> Decision:
    """Deterministic retain/switch/stop over identity and service state only."""
    rows = sorted(summaries, key=lambda s: int(s.instance_id))
    by_id = {int(s.instance_id): s for s in rows}
    if len(by_id) != len(rows):
        raise ValueError("duplicate instance ids in scheduler input")
    localized = [s for s in rows if s.state is not ServiceState.UNLOCATED]
    serviceable = [int(s.instance_id) for s in localized if s.state in SERVICEABLE]

    if current_id is not None:
        current = by_id.get(int(current_id))
        if current is None or current.state is ServiceState.UNLOCATED:
            raise ValueError(f"current object {current_id} is not a localized object")
        if current.state in SERVICEABLE:
            return Decision("attend", int(current_id), "retain")
        if serviceable:
            forward = [i for i in serviceable if i > int(current_id)]
            return Decision("attend", forward[0] if forward else serviceable[0], "switch")
    elif serviceable:
        return Decision("attend", serviceable[0], "initial")

    blocked = tuple((int(s.instance_id), str(s.blocked_reason)) for s in localized
                    if s.state is ServiceState.BLOCKED)
    if blocked:
        return Decision("terminal", terminal=Incomplete("localized_objects_blocked", blocked))
    if any(s.state is not ServiceState.QUIET for s in localized):
        raise AssertionError("no serviceable or blocked object, yet a localized object is not QUIET")
    return Decision("terminal", terminal=Stop())


@dataclass
class ObservationOutcome:
    """What the experiment reports after executing one OBSERVE."""

    initialized: bool | None  # seed look: map initialized or not; later look: None
    record: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoopResult:
    actions: list[dict[str, Any]]
    events: list[dict[str, Any]]
    final: dict[int, ObjectSummary]
    terminal: Stop | Incomplete | CapReached
    fixations: dict[int, int]
    initialized: list[int]
    probe_calls: int
    probe_cache_hits: int


def run_control_loop(
    seeds: Mapping[int, tuple[float, float]],
    *,
    observe: Callable[[int, Observe, int], ObservationOutcome],
    probe: Callable[[int], ProbeResult],
    vergence: Mapping[str, Any],
    focus: Mapping[str, Any],
    watchdog: int,
    revision: Callable[[int], Hashable] | None = None,
    unlocated: Iterable[int] = (),
    action_cap: int | None = None,
    on_event: Callable[[dict[str, Any]], None] | None = None,
    on_action: Callable[[dict[str, Any]], None] | None = None,
) -> LoopResult:
    """Run the closed scene-level loop until STOP, INCOMPLETE or the explicit cap.

    ``observe(global_step, action, object_local_step)`` executes one action and updates the
    experiment's causal memory.  ``probe(i)`` is the pure service probe of an initialized
    object over the current memory.  ``revision(i)``, if given, must change whenever any
    input of ``probe(i)`` changes; the last probe result is then reused exactly while the
    revision is unchanged.
    """
    order = sorted(int(i) for i in seeds)
    unlocated_rows = [ObjectSummary(int(u), ServiceState.UNLOCATED)
                      for u in sorted({int(u) for u in unlocated} - set(order))]
    initialized: list[int] = []
    blocked: dict[int, str] = {}
    fixations = {i: 0 for i in order}
    cache: dict[int, tuple[Hashable, ProbeResult]] = {}
    last_probe: dict[int, ProbeResult] = {}
    quiet_probe: dict[int, ProbeResult] = {}
    quiet_since: dict[int, int | None] = {}
    reactivated_since_attended: set[int] = set()
    events: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    calls = 0
    hits = 0

    def emit(event: dict[str, Any]) -> None:
        events.append(event)
        if on_event is not None:
            on_event(event)

    def probe_now(i: int) -> ProbeResult:
        nonlocal calls, hits
        key = revision(i) if revision is not None else None
        if revision is not None and i in cache and cache[i][0] == key:
            hits += 1
            return cache[i][1]
        result = probe(i)
        calls += 1
        if not isinstance(result, ProbeResult):
            raise TypeError("the service probe must return a ProbeResult")
        if result.action is not None and int(result.action.target_id) != i:
            raise ValueError(f"probe of object {i} proposed an action for {result.action.target_id}")
        if revision is not None:
            cache[i] = (key, result)
        return result

    def service(i: int) -> ObjectSummary:
        if i in blocked:
            return ObjectSummary(i, ServiceState.BLOCKED, blocked[i])
        if i not in initialized:
            return ObjectSummary(i, ServiceState.SEEDABLE)
        result = probe_now(i)
        last_probe[i] = result
        if can_act(result):
            if fixations[i] >= watchdog:
                blocked[i] = "watchdog"
                return ObjectSummary(i, ServiceState.BLOCKED, "watchdog")
            return ObjectSummary(i, ServiceState.ACTIONABLE)
        return ObjectSummary(i, ServiceState.QUIET)

    recorded = {i: ObjectSummary(i, ServiceState.SEEDABLE) for i in order}

    def refresh(step: int, trigger: int) -> dict[int, ObjectSummary]:
        now: dict[int, ObjectSummary] = {}
        for i in order:
            prev, cur = recorded[i], service(i)
            now[i] = cur
            if prev.state is ServiceState.QUIET and cur.state is not ServiceState.QUIET:
                emit({
                    "event": "natural_reactivation", "object": i, "global_step": step,
                    "trigger_target": trigger, "quiet_since_step": quiet_since.pop(i, None),
                    "state_after": cur.label, "fixations": fixations[i],
                    "probe_before": dict(quiet_probe.pop(i).detail),
                    "probe_after": dict(last_probe[i].detail),
                })
                reactivated_since_attended.add(i)
            if cur.state is ServiceState.QUIET and prev.state is not ServiceState.QUIET:
                quiet_since[i] = step
                quiet_probe[i] = last_probe[i]
                emit({"event": "quiet", "object": i, "global_step": step, "trigger_target": trigger,
                      "previous_state": prev.label, "fixations": fixations[i],
                      "probe": dict(last_probe[i].detail)})
            if cur.state is ServiceState.BLOCKED and prev.state is not ServiceState.BLOCKED:
                emit({"event": "blocked", "object": i, "global_step": step, "trigger_target": trigger,
                      "reason": cur.blocked_reason, "previous_state": prev.label,
                      "fixations": fixations[i]})
        recorded.update(now)
        return now

    summaries = dict(recorded)
    current: int | None = None
    bout = 0
    step = 0
    while True:
        decision = schedule(current, [*summaries.values(), *unlocated_rows])
        if decision.kind == "terminal":
            terminal: Stop | Incomplete | CapReached = decision.terminal  # type: ignore[assignment]
            break
        if action_cap is not None and step >= int(action_cap):
            terminal = CapReached(int(action_cap))
            break
        i = int(decision.target_id)  # type: ignore[arg-type]
        before = summaries[i]
        if before.state is ServiceState.SEEDABLE:
            action = Observe(i, tuple(seeds[i]), vergence, focus, SEED_SOURCE)
            proposal = None
        else:
            proposing = last_probe[i]
            action = choose_action(proposing)
            if action is None:
                raise AssertionError(f"scheduler selected object {i} without an action")
            proposal = dict(proposing.detail)
        reason = decision.reason
        if reason == "switch" and i in reactivated_since_attended:
            reason = "natural_reactivation"
        reactivated_since_attended.discard(i)
        if decision.reason in ("initial", "switch"):
            bout += 1
        states_before = {str(k): s.label for k, s in summaries.items()}
        local_step = fixations[i]

        outcome = observe(step, action, local_step)
        fixations[i] += 1
        first_event = len(events)
        if before.state is ServiceState.SEEDABLE:
            if outcome.initialized:
                initialized.append(i)
                emit({"event": "seed_initialized", "object": i, "global_step": step, "trigger_target": i})
            else:
                blocked[i] = "seed_uninitializable"
        summaries = refresh(step, i)

        record = {
            "global_step": step,
            "target_id": i,
            "gaze_deg": list(action.gaze_yaw_pitch_deg),
            "action_source": action.source,
            "vergence": dict(action.vergence),
            "focus": dict(action.focus),
            "service_state_before": before.label,
            "scheduler_decision": decision.reason,
            "scheduler_reason": reason,
            "previous_object": current,
            "current_object_transition": "retain" if current == i else f"{current}->{i}",
            "attention_bout": bout,
            "object_local_step": local_step,
            "target_fixations_after": fixations[i],
            "proposal": proposal,
            **outcome.record,
            "service_states_before": states_before,
            "service_states_after": {str(k): s.label for k, s in summaries.items()},
            "events": [{"event": e["event"], "object": e["object"]} for e in events[first_event:]],
        }
        actions.append(record)
        if on_action is not None:
            on_action(record)
        current = i
        step += 1

    final = dict(summaries)
    final.update({s.instance_id: s for s in unlocated_rows})
    return LoopResult(actions, events, final, terminal, fixations, initialized, calls, hits)


# ---------------------------------------------------------------- target-relative view

TARGET_NEUTRAL_HEAD_FIELDS = ("depth_seen", "nearest_instance", "nearest_range_m",
                              "ambiguous_instance", "sample_count")
FORBIDDEN_VIEW_FIELDS = ("candidate", "candidate_region_count", "reconstruction_status",
                         "min_distance_to_historical_gaze_deg")


def target_neutral_head_view(head: Any) -> dict[str, np.ndarray]:
    """The global HeadEvidence fields that mean the same whatever target was active."""
    return {name: np.asarray(getattr(head, name)) for name in TARGET_NEUTRAL_HEAD_FIELDS}


def support_layers(
    geometries: Mapping[int, np.ndarray],
    domain: Mapping[str, Any],
    grid_deg: float,
    *,
    cache: dict[int, tuple[Hashable, SupportLayer]] | None = None,
    revisions: Mapping[int, Hashable] | None = None,
) -> dict[int, SupportLayer]:
    """One support layer per instance with finite geometry, optionally cached by revision."""
    layers: dict[int, SupportLayer] = {}
    for iid in sorted(int(k) for k in geometries):
        xyz = np.asarray(geometries[iid], np.float64).reshape(-1, 3)
        if not np.isfinite(xyz).all(axis=1).any():
            continue
        key = None if revisions is None else revisions[iid]
        if cache is not None and revisions is not None and iid in cache and cache[iid][0] == key:
            layers[iid] = cache[iid][1]
            continue
        layer = support_depth_from_map(xyz, dict(domain), grid_deg, instance_id=iid, object_name=str(iid))
        layers[iid] = layer
        if cache is not None and revisions is not None:
            cache[iid] = (key, layer)
    return layers


def target_epistemic_view(
    *,
    target_id: int,
    target_name: str,
    layers: Mapping[int, SupportLayer],
    head_view: Mapping[str, np.ndarray],
    seen_any: np.ndarray,
    domain: Mapping[str, Any],
    grid_deg: float,
) -> tuple[dict[str, np.ndarray], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """E_t(i): the intrinsic Core-14 partition for target ``i`` from current causal memory.

    ``layers`` are the support layers of every currently measured instance (the target
    included when it has geometry); ``head_view`` holds only target-neutral HeadEvidence
    fields; ``seen_any`` is the global completed-observation footprint.
    """
    seen = np.asarray(seen_any, bool)
    shape = seen.shape
    target = layers.get(int(target_id))
    target_support = np.zeros(shape, bool) if target is None else np.asarray(target.support, bool)
    nonempty = {k: v for k, v in layers.items() if np.asarray(v.support).any()}
    owner = joint_owner(nonempty)[0] if nonempty else np.zeros(shape, np.int32)
    state = {
        "target_support": target_support,
        "owner_instance": owner,
        "nearest_instance": np.asarray(head_view["nearest_instance"], np.int32),
        "ambiguous_instance": np.asarray(head_view["ambiguous_instance"], bool),
        "depth_seen": np.asarray(head_view["depth_seen"], bool),
        "seen_any": seen,
    }
    arrays, rows, edges, diag = build_epistemic_partition(
        state, target_id=int(target_id), target_name=str(target_name),
        domain=dict(domain), grid_deg=float(grid_deg),
    )
    assert_intrinsic(rows, diag)
    return arrays, rows, edges, diag


def assert_intrinsic(rows: list[dict[str, Any]], diag: Mapping[str, Any]) -> None:
    """Refuse a view carrying candidate, run-context or action-history annotations."""
    leaked = sorted({k for r in rows for k in r if k in FORBIDDEN_VIEW_FIELDS}
                    | {k for k in diag if k in FORBIDDEN_VIEW_FIELDS})
    if leaked:
        raise AssertionError(f"target view is not intrinsic: {leaked}")


def view_summary(rows: list[dict[str, Any]], edges: list[dict[str, Any]], diag: Mapping[str, Any]) -> dict[str, Any]:
    """Kind counts plus a small topology summary of one target view."""
    unknown = [r for r in rows if r["kind"] == "UNKNOWN"]
    return {
        "kind_cell_counts": {k: int(diag["kind_cell_counts"].get(k, 0)) for k in REGION_KIND},
        "kind_region_counts": {k: int(diag["kind_region_counts"].get(k, 0)) for k in REGION_KIND},
        "region_count": int(diag["region_count"]),
        "edge_count": len(edges),
        "target_evidence_unmapped_cells": int(diag["target_evidence_unmapped_cells"]),
        "ambiguous_boundary_cells": int(diag["ambiguous_boundary_cells"]),
        "head_depth_cells": int(diag["head_depth_cells"]),
        "eye_ray_seen_cells": int(diag["eye_ray_seen_cells"]),
        "unknown_regions_adjacent_to_target_support": sum(bool(r["adjacent_to_target_support"]) for r in unknown),
        "unknown_cells_adjacent_to_target_support": sum(int(r["cell_count"]) for r in unknown
                                                        if r["adjacent_to_target_support"]),
        "unknown_regions_touching_domain_edge": sum(bool(r["touches_domain_edge"]) for r in unknown),
        "largest_unknown_region_cells": max((int(r["cell_count"]) for r in unknown), default=0),
        "other_surface_instances_adjacent_to_target_support": sorted({
            int(r["instance_id"]) for r in rows
            if r["kind"] == "OTHER_SURFACE" and r["adjacent_to_target_support"]
        }),
        "truth_used": bool(diag["truth_used"]),
    }


# ---------------------------------------------------------------- truth firewall

class TruthFirewall:
    """Process-wide guard against controller-time access to evaluation truth.

    While active, an audit hook sees every ``open`` and directory listing in this process
    and raises ``PermissionError`` for any path the predicate forbids.  It also records the
    files under ``root`` opened for reading.  Audit hooks cannot be removed, so the hook is
    installed once and consults the active firewall.
    """

    _installed = False
    _active: "TruthFirewall | None" = None

    def __init__(self, root: str | os.PathLike, forbidden: Callable[[str], bool]) -> None:
        self.root = os.path.abspath(os.fspath(root))
        self.forbidden = forbidden
        self.violations: list[str] = []
        self.opened: set[str] = set()

    def __enter__(self) -> "TruthFirewall":
        if not TruthFirewall._installed:
            sys.addaudithook(TruthFirewall._hook)
            TruthFirewall._installed = True
        if TruthFirewall._active is not None:
            raise RuntimeError("a truth firewall is already active")
        TruthFirewall._active = self
        return self

    def __exit__(self, *exc: Any) -> None:
        TruthFirewall._active = None

    @staticmethod
    def _hook(event: str, args: tuple) -> None:
        fw = TruthFirewall._active
        if fw is None or event not in ("open", "os.listdir", "os.scandir"):
            return
        path = args[0] if args else None
        if path is None or isinstance(path, int):
            return
        full = os.path.abspath(os.fsdecode(path))
        if fw.forbidden(full):
            fw.violations.append(full)
            raise PermissionError(f"truth firewall: controller access to evaluation truth: {full}")
        if event != "open" or not (full == fw.root or full.startswith(fw.root + os.sep)):
            return
        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 else 0
        reading = (not any(c in mode for c in "wax+")) if isinstance(mode, str) \
            else not (int(flags or 0) & (os.O_WRONLY | os.O_RDWR))
        if reading:
            fw.opened.add(os.path.relpath(full, fw.root))
