#!/usr/bin/env python3
"""Fail-capable checks for Integrated Foveal Controller 01.

    .venv/bin/python tools/controller/check_controller01.py              # unit + architecture
    .venv/bin/python tools/controller/check_controller01.py --run DIR    # + run-artifact validation
    .venv/bin/python tools/controller/check_controller01.py --terminal-reprobe DIR --object 210
                                                                         # Controller-01A read-only audit

Contract: docs/controller/controller-01-state-action-contract.md.  The unit checks are
Blender-free.  Every behavioral check is also run against a deliberate negative control (a
mutant scheduler, probe, loop configuration, memory view or firewall) that must be rejected,
so each check is shown to be able to fail.  ``--run`` validates a completed run directory
from controller-time artifacts only; it never opens evaluation truth.

``--terminal-reprobe`` (Controller-01A, docs/controller/controller-01a-terminal-audit-contract.md)
reconstructs a completed run's causal state from its saved artifacts, validates the
reconstruction against the saved watchdog-prefix probe, and asks the unchanged accepted local
policy again at the terminal state.  It renders, fuses and changes nothing, under the truth firewall.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
import dataclasses
import inspect
import itertools
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import numpy as np

import fov3d  # noqa: F401  (puts the sealed engine on sys.path for the facades)
from fov3d.control import integrated as ic
from fov3d.epistemic.head_memory import HeadEvidence, add_head_patch
from fov3d.epistemic.partition import build_epistemic_partition
from fov3d.experiments.classroom_oracle import controller01 as c01
from fov3d.geometry.core import make_calibration
from fov3d.reconstruction import surface_map
from fov3d.reconstruction.measurement_memory import InstanceMeasurementMemory, effective_target_geometry
from fov3d.scene.partition import joint_owner, support_depth_from_map
from fov3d.stereo.core import rectification

PREFIX = "[controller01-check]"
BASE = "c5f6be63d050d89026b3658a2d033e7c2439caf1"
INTEGRATED = REPO / "fov3d/control/integrated.py"
CONTROLLER = REPO / "fov3d/experiments/classroom_oracle/controller01.py"
LAYOUT = REPO / "docs/consolidation/consolidation-3-layout.json"
HISTORICAL_BARE = {
    "bl_common", "render_foveated", "warp", "exr_lite", "fsg_geometry", "fsg3_surface_map", "fsg_stereo",
    "fsg6f_frontier", "fsg6f_public", "multiobject2c_policy", "classroom_oracle1_public",
    "classroom_oracle1_matcher", "classroom_oracle1_epistemic", "classroom_oracle1_render",
    "classroom_oracle1_run", "classroom_oracle1_eval",
}
HISTORICAL_POLICY = ("candidate_policy", "run_context", "gaze_context")
# Historical interpretation fields that the intrinsic view must never carry.  Named here, not in
# fov3d: Core 14 requires that only gaze_context names the gaze field inside fov3d.
FORBIDDEN_VIEW_FIELDS = ("candidate", "candidate_region_count", "reconstruction_status",
                         "min_distance_to_historical_gaze_deg")

checked = 0
failed = 0
S = ic.ServiceState
REAL_SCHEDULE = ic.schedule  # mutants wrap this, so patching ic.schedule cannot recurse


def check(name: str, ok: bool, detail: str = "") -> None:
    global checked, failed
    checked += 1
    if not ok:
        failed += 1
    print(f"{PREFIX} {'PASS' if ok else 'FAIL'} {name}{'' if ok or not detail else ': ' + detail}")


def errors_of(fn, *a, **k) -> list[str]:
    """Run one check body; an unexpected exception counts as a failure of that body."""
    try:
        return list(fn(*a, **k))
    except Exception as exc:  # noqa: BLE001
        return [f"{type(exc).__name__}: {exc}"]


def verified(name: str, body, real: tuple, controls: dict[str, tuple]) -> None:
    """The body passes on the real objects and fails on every negative control."""
    errs = errors_of(body, *real)
    check(name, not errs, "; ".join(errs[:3]))
    for label, args in controls.items():
        caught = errors_of(body, *args)
        check(f"{name.split()[0]} control rejected: {label}", bool(caught), "the control mutant passed")


@contextmanager
def patched(obj, name: str, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


def O(i: int, state: S, reason: str | None = None) -> ic.ObjectSummary:  # noqa: E743
    return ic.ObjectSummary(i, state, reason)


def rows(spec: dict[int, str]) -> list[ic.ObjectSummary]:
    out = []
    for i, label in spec.items():
        if label.startswith("BLOCKED:"):
            out.append(O(i, S.BLOCKED, label.split(":", 1)[1]))
        else:
            out.append(O(i, S(label)))
    return out


# ---------------------------------------------------------------- mutant schedulers (controls)

def m_never_retain(current, summaries):
    s = list(summaries)
    d = REAL_SCHEDULE(current, s)
    if d.reason == "retain":
        others = [x for x in s if x.instance_id != current]
        alt = REAL_SCHEDULE(None, others)
        return alt if alt.kind == "attend" else d
    return d


def m_retain_anything(current, summaries):
    s = list(summaries)
    if current is not None:
        return ic.Decision("attend", current, "retain")
    return REAL_SCHEDULE(current, s)


def m_restart_scan(current, summaries):
    d = REAL_SCHEDULE(current, summaries)
    if d.reason == "switch":
        return ic.Decision("attend", REAL_SCHEDULE(None, summaries).target_id, "switch")
    return d


def m_input_order(current, summaries):
    s = list(summaries)
    serviceable = [x.instance_id for x in s if x.state in ic.SERVICEABLE]
    d = REAL_SCHEDULE(current, s)
    if d.kind == "attend" and d.reason != "retain" and serviceable:
        return ic.Decision("attend", serviceable[0], d.reason)
    return d


def m_seedable_ignored(current, summaries):
    return REAL_SCHEDULE(current, [O(x.instance_id, S.QUIET) if x.state is S.SEEDABLE else x for x in summaries])


def m_actionable_ignored(current, summaries):
    return REAL_SCHEDULE(current, [O(x.instance_id, S.QUIET) if x.state is S.ACTIONABLE else x for x in summaries])


def m_blocked_as_quiet(current, summaries):
    return REAL_SCHEDULE(current, [O(x.instance_id, S.QUIET) if x.state is S.BLOCKED else x for x in summaries])


def m_unlocated_as_quiet_seedable(current, summaries):
    return REAL_SCHEDULE(current, [O(x.instance_id, S.SEEDABLE) if x.state is S.UNLOCATED else x for x in summaries])


# ---------------------------------------------------------------- 1-10 scheduler

def t01_retain_actionable(sched):
    errs = []
    d = sched(2, rows({1: "QUIET", 2: "ACTIONABLE", 3: "ACTIONABLE"}))
    if (d.kind, d.target_id, d.reason) != ("attend", 2, "retain"):
        errs.append(f"current ACTIONABLE 2 not retained: {d}")
    d = sched(3, rows({1: "ACTIONABLE", 2: "SEEDABLE", 3: "ACTIONABLE"}))
    if (d.target_id, d.reason) != (3, "retain"):
        errs.append(f"current ACTIONABLE 3 (last id) not retained: {d}")
    return errs


def t02_retain_seedable(sched):
    d = sched(2, rows({1: "ACTIONABLE", 2: "SEEDABLE", 3: "SEEDABLE"}))
    return [] if (d.kind, d.target_id, d.reason) == ("attend", 2, "retain") else [f"current SEEDABLE not retained: {d}"]


def t03_cyclic_switch(sched):
    errs = []
    cases = [
        (3, {1: "ACTIONABLE", 2: "SEEDABLE", 3: "QUIET", 4: "QUIET", 5: "ACTIONABLE"}, 5),
        (5, {1: "QUIET", 2: "SEEDABLE", 3: "ACTIONABLE", 4: "QUIET", 5: "QUIET"}, 2),
        (3, {1: "SEEDABLE", 2: "QUIET", 3: "BLOCKED:watchdog", 4: "QUIET", 5: "ACTIONABLE", 9: "UNLOCATED"}, 5),
        (4, {1: "ACTIONABLE", 2: "QUIET", 4: "BLOCKED:seed_uninitializable", 7: "UNLOCATED"}, 1),
    ]
    for cur, spec, want in cases:
        d = sched(cur, rows(spec))
        if (d.kind, d.target_id, d.reason) != ("attend", want, "switch"):
            errs.append(f"current {cur} {spec[cur]} -> {d.target_id}/{d.reason}, expected {want}/switch")
    return errs


def t04_all_quiet_stop(sched):
    errs = []
    for cur, spec in ((2, {1: "QUIET", 2: "QUIET", 3: "QUIET"}), (1, {1: "QUIET", 5: "UNLOCATED", 8: "QUIET"})):
        d = sched(cur, rows(spec))
        if d.kind != "terminal" or not isinstance(d.terminal, ic.Stop) or d.terminal.reason != "global_quiescence":
            errs.append(f"all localized QUIET did not STOP(global_quiescence): {d}")
    return errs


def t05_seedable_prevents_stop(sched):
    d = sched(1, rows({1: "QUIET", 2: "QUIET", 3: "SEEDABLE"}))
    return [] if (d.kind, d.target_id) == ("attend", 3) else [f"SEEDABLE did not prevent STOP: {d}"]


def t06_actionable_prevents_stop(sched):
    d = sched(3, rows({1: "QUIET", 2: "ACTIONABLE", 3: "QUIET"}))
    return [] if (d.kind, d.target_id) == ("attend", 2) else [f"ACTIONABLE did not prevent STOP: {d}"]


def t07_blocked_prevents_quiescence(sched):
    errs = []
    for reason in ic.BLOCKED_REASONS:
        d = sched(1, rows({1: "QUIET", 2: f"BLOCKED:{reason}", 3: "QUIET"}))
        if d.kind != "terminal" or isinstance(d.terminal, ic.Stop):
            errs.append(f"BLOCKED:{reason} allowed a successful STOP: {d}")
        elif not isinstance(d.terminal, ic.Incomplete) or (2, reason) not in d.terminal.blocked:
            errs.append(f"BLOCKED:{reason} not reported as INCOMPLETE: {d}")
    try:
        ic.Stop("localized_objects_blocked")
        errs.append("STOP accepted a reason other than global_quiescence")
    except ValueError:
        pass
    return errs


def t08_unlocated_not_quiet(sched, classify):
    errs = []
    init = classify([1, 2, 3, 4], [2, 4])
    if init[1].state is not S.UNLOCATED or init[3].state is not S.UNLOCATED:
        errs.append(f"non-localized catalog objects not UNLOCATED: {init}")
    if any(init[i].state is S.QUIET for i in (1, 3)):
        errs.append("UNLOCATED silently converted to QUIET")
    if S.UNLOCATED == S.QUIET:
        errs.append("UNLOCATED equals QUIET")
    d = sched(2, [init[1], O(2, S.QUIET), init[3], O(4, S.QUIET)])
    if d.kind != "terminal" or not isinstance(d.terminal, ic.Stop):
        errs.append(f"UNLOCATED objects were attended or blocked STOP: {d}")
    d = sched(None, [init[1], init[3], O(4, S.ACTIONABLE)])
    if d.target_id != 4:
        errs.append(f"initial choice attended an UNLOCATED object: {d}")
    return errs


def m_classify_unlocated_quiet(catalog, localized):
    out = ic.catalog_summaries(catalog, localized)
    return {i: (O(i, S.QUIET) if s.state is S.UNLOCATED else s) for i, s in out.items()}


def t09_deterministic_order(sched):
    errs = []
    scenes = [
        (None, {7: "SEEDABLE", 3: "ACTIONABLE", 5: "SEEDABLE"}, 3),
        (5, {7: "SEEDABLE", 3: "ACTIONABLE", 5: "QUIET", 1: "UNLOCATED"}, 7),
        (7, {7: "QUIET", 3: "ACTIONABLE", 5: "SEEDABLE"}, 3),
    ]
    for cur, spec, want in scenes:
        base = rows(spec)
        for perm in itertools.permutations(base):
            d = sched(cur, list(perm))
            if d.target_id != want:
                errs.append(f"order-dependent choice {d.target_id} (expected {want}) for input order "
                            f"{[x.instance_id for x in perm]}")
                break
    return errs


def t10_state_identity_only(selector):
    errs = []
    fields = {f.name for f in dataclasses.fields(ic.ObjectSummary)}
    if fields != {"instance_id", "state", "blocked_reason"}:
        errs.append(f"ObjectSummary fields {sorted(fields)}")
    params = list(inspect.signature(ic.schedule).parameters)
    if params != ["current_id", "summaries"]:
        errs.append(f"schedule parameters {params}")
    rng = random.Random(20261003)
    for _ in range(200):
        n = rng.randint(2, 7)
        ids = rng.sample(range(1, 40), n)
        spec = {i: rng.choice(["SEEDABLE", "ACTIONABLE", "QUIET", "UNLOCATED"]) for i in ids}
        localized = [i for i, v in spec.items() if v != "UNLOCATED"]
        cur = rng.choice(localized + [None]) if localized else None
        side_a = {i: {"unknown_cells": rng.randint(0, 9999), "coverage": rng.random()} for i in ids}
        side_b = {i: {"unknown_cells": rng.randint(0, 9999), "coverage": rng.random()} for i in ids}
        try:
            da = selector(cur, rows(spec), side_a)
            db = selector(cur, rows(spec), side_b)
        except ValueError:
            continue
        if (da.kind, da.target_id, da.reason) != (db.kind, db.target_id, db.reason):
            errs.append(f"decision changed with epistemic side information: {da} vs {db}")
            break
    return errs


def m_ranking_selector(current, summaries, side):
    s = list(summaries)
    d = REAL_SCHEDULE(current, s)
    if d.kind == "attend" and d.reason != "retain":
        serviceable = [x.instance_id for x in s if x.state in ic.SERVICEABLE]
        best = max(serviceable, key=lambda i: side[i]["unknown_cells"])
        return ic.Decision("attend", best, d.reason)
    return d


# ---------------------------------------------------------------- 11 probe

def t11_probe_consistency(can, choose, probe):
    errs = []
    act = ic.Observe(3, (1.0, 2.0), c01.VERGENCE, c01.FOCUS, "fsg6f")
    for res in (ic.ProbeResult(None, {"quiet": True}), ic.ProbeResult(act, {"quiet": True})):
        if can(res) != (choose(res) is not None):
            errs.append(f"can_act={can(res)} while choose_action={choose(res)}")
        if res.state is not (S.ACTIONABLE if can(res) else S.QUIET):
            errs.append("ProbeResult.state disagrees with can_act")
    try:
        ic.ProbeResult(ic.Observe(3, (0.0, 0.0), c01.VERGENCE, c01.FOCUS, "oracle_seed"))
        errs.append("a probe result accepted a seed action")
    except ValueError:
        pass
    ctx = c01.LocalPolicyContext(3, gaze=(0.0, 0.0), calibration={}, state={
        "ids_left": np.zeros((2, 2), int), "raw_support_L": np.ones((2, 2), bool),
        "ids_right": np.zeros((2, 2), int), "raw_support_R": np.ones((2, 2), bool)})
    geo = np.zeros((5, 3))
    calls: list[str] = []

    def f_cont(**k):
        calls.append("fsg6f"); return {**_fsg_stub(False), "next_gaze_deg": [5.0, 0.0]}

    def f_stop(**k):
        calls.append("fsg6f"); return _fsg_stub(True)

    def c_sel(ev, g, visited):
        calls.append("cyc"); return _cyc_stub(False, [2.5, -1.0])

    def c_stop(ev, g, visited):
        calls.append("cyc"); return _cyc_stub(True, None)

    expect = [((f_cont, c_sel), ("fsg6f", (5.0, 0.0)), ["fsg6f"]),
              ((f_stop, c_sel), ("cyclopean_epistemic", (2.5, -1.0)), ["fsg6f", "cyc"]),
              ((f_stop, c_stop), None, ["fsg6f", "cyc"])]
    for (f, c), want, want_calls in expect:
        calls.clear()
        res, _dec = probe(ctx, geo, fsg6f=f, cyclopean=c)
        got = None if res.action is None else (res.action.source, res.action.gaze_yaw_pitch_deg)
        if got != want or calls != want_calls:
            errs.append(f"probe mapped to {got} with calls {calls}, expected {want} with {want_calls}")
        if can(res) != (choose(res) is not None):
            errs.append("probe result views disagree")
    return errs


def _fsg_stub(stop):
    return {"stop": stop, "reason": "no_frontier" if stop else "continue", "next_gaze_deg": None,
            "frontier_raw_count": 0, "frontier_open_count": 0, "frontier_map_resolved_count": 0,
            "frontier_boundary_resolved_count": 0, "candidates": [], "consensus_rejected_candidate_count": 0}


def _cyc_stub(stop, gaze):
    return {"stop": stop, "reason": "attention_complete" if stop else "epistemic_fixation", "next_gaze_deg": gaze,
            "audit": {"eligible_never_observed_exterior_shoreline_cells": 0 if stop else 3, "map_support_cells": 1,
                      "shoreline_cells": 1, "epistemic_state_counts": {"NEVER_OBSERVED": 1}}}


def m_can_act_flag(res):
    return bool(res.detail.get("quiet") is False)


def m_probe_skips_cyclopean(ctx, geo, *, fsg6f, cyclopean):
    res, dec = c01.probe_local_policy(ctx, geo, fsg6f=fsg6f, cyclopean=cyclopean)
    if res.action is not None and res.action.source == "cyclopean_epistemic":
        return ic.ProbeResult(None, res.detail), dec
    return res, dec


def _synthetic_context():
    """A small real calibration, a target patch and its binocular state, for the real policies."""
    c = make_calibration("small", 0.0, 0.0, 2.1, head_r_wh=np.eye(3), head_origin_w=np.zeros(3))
    _x, _y, w, h = map(int, rectification(c)["crop_xywh"])
    ids = np.zeros((h, w), np.int32)
    ids[:, : w // 2] = 11
    sup = np.ones((h, w), bool)
    st = {"ids_left": ids, "raw_support_L": sup, "ids_right": ids.copy(), "raw_support_R": sup.copy()}
    yaw, pitch = np.meshgrid(np.linspace(-5.5, 0.0, 60), np.linspace(-5.0, 5.0, 90))
    yr, pr = np.radians(yaw.ravel()), np.radians(pitch.ravel())
    geo = 2.1 * np.c_[np.sin(yr) * np.cos(pr), np.sin(pr), -np.cos(yr) * np.cos(pr)]
    ctx = c01.LocalPolicyContext(11, gaze=(0.0, 0.0), calibration=c, state=st, visited=[(0.0, 0.0)])
    ctx.history.append(c01.object_policy.history_entry(
        calibration=c, instance_L=ids, raw_support_L=sup, instance_R=ids, raw_support_R=sup, target_object_id=11))
    return ctx, geo


def _fingerprint(ctx, geo) -> list:
    out = [geo.tobytes(), json.dumps(ctx.calibration, sort_keys=True), list(ctx.visited), ctx.gaze]
    out += [a.tobytes() for a in ctx.state.values()]
    out += [ctx.evidence.seen_any.tobytes(), ctx.evidence.seen_target.tobytes()]
    for h in ctx.history:
        out += [h["instance_L"].tobytes(), h["raw_support_L"].tobytes()]
    return out


def t11b_probe_pure(probe):
    ctx, geo = _synthetic_context()
    before = _fingerprint(ctx, geo)
    r1, _ = probe(ctx, geo)
    r2, _ = probe(ctx, geo)
    errs = []
    if r1.action != r2.action or json.dumps(c01._jsonable(r1.detail), sort_keys=True) != \
            json.dumps(c01._jsonable(r2.detail), sort_keys=True):
        errs.append(f"repeated probe differs: {r1.action} vs {r2.action}")
    if _fingerprint(ctx, geo) != before:
        errs.append("the probe mutated its inputs")
    return errs


def m_probe_mutating(ctx, geo, **k):
    res = c01.probe_local_policy(ctx, geo, **k)
    ctx.visited.append((99.0, 99.0))
    return res


# ---------------------------------------------------------------- toy world for the control loop

class ToyWorld:
    """Point clusters on a line; a look at x measures every cluster within 1.0 of x."""

    def __init__(self, clusters: dict[int, list[float]], seeds: dict[int, float], *,
                 seed_fail: tuple[int, ...] = (), always_actionable: tuple[int, ...] = ()):
        self.clusters, self.seed_fail, self.always = clusters, seed_fail, always_actionable
        self.seeds = {i: (float(x), 0.0) for i, x in seeds.items()}
        self.memory = InstanceMeasurementMemory()
        self.counts: dict[int, int] = {}
        self.visited: dict[int, list[float]] = {i: [] for i in seeds}

    def observe(self, step, action, local):
        i, x0 = action.target_id, action.gaze_yaw_pitch_deg[0]
        pts, ids = [], []
        for j, xs in self.clusters.items():
            for x in xs:
                if abs(x - x0) <= 1.0:
                    pts.append([x, 0.0, -2.0]); ids.append(j)
        n = max(1, len(pts))
        xyz = np.full((1, n, 3), np.nan, np.float32)
        inst = np.zeros((1, n), np.int32)
        if pts:
            xyz[0, : len(pts)] = pts
            inst[0, : len(ids)] = ids
        added = self.memory.append_patch({"xyz_h": xyz, "instance_id": inst, "valid": inst > 0},
                                         source_global_index=step, source_active_target_id=i)
        for k, v in added.items():
            self.counts[k] = self.counts.get(k, 0) + v
        self.visited[i].append(x0)
        init = None if local else (i not in self.seed_fail)
        return ic.ObservationOutcome(init, {"additions": {str(k): v for k, v in added.items()}})

    def probe(self, i):
        if i in self.always:
            return ic.ProbeResult(ic.Observe(i, (100.0 + len(self.visited[i]), 0.0), c01.VERGENCE, c01.FOCUS, "fsg6f"),
                                  {"toy": "always"})
        xs = self.memory.snapshot(i).xyz_h[:, 0]
        far = [float(x) for x in xs if all(abs(float(x) - v) > 0.5 for v in self.visited[i])]
        if not far:
            return ic.ProbeResult(None, {"uncovered": 0})
        return ic.ProbeResult(ic.Observe(i, (round(float(np.mean(far)), 3), 0.0), c01.VERGENCE, c01.FOCUS,
                                         "cyclopean_epistemic"), {"uncovered": len(far)})

    def revision(self, i):
        return len(self.visited[i]), self.counts.get(i, 0)

    def run(self, *, revision=True, rev_fn=None, watchdog=24, cap=500):
        # The cap only turns a non-terminating mutant into a named failure (CapReached) instead of a hang.
        return ic.run_control_loop(
            self.seeds, observe=self.observe, probe=self.probe,
            revision=(rev_fn or self.revision) if revision else None,
            vergence=c01.VERGENCE, focus=c01.FOCUS, watchdog=watchdog, unlocated=[42], action_cap=cap)


def reactivation_world():
    # A (1) at x=0 and x=3; B (2) at x=2.2.  B's seed look measures A's far cluster.
    return ToyWorld({1: [0.0, 3.0], 2: [2.2]}, {1: 0.0, 2: 2.2})


def _strip(loop):
    return json.dumps(c01._jsonable({"a": loop.actions, "e": loop.events, "t": repr(loop.terminal)}), sort_keys=True)


def t12_natural_reactivation(make_world, run_kwargs):
    errs = []
    loop = make_world().run(**run_kwargs)
    seq = [(a["target_id"], a["action_source"], a["scheduler_decision"], a["scheduler_reason"]) for a in loop.actions]
    want = [(1, "oracle_seed", "initial", "initial"), (2, "oracle_seed", "switch", "switch"),
            (1, "cyclopean_epistemic", "switch", "natural_reactivation")]
    if seq != want:
        errs.append(f"action sequence {seq}, expected {want}")
    react = [e for e in loop.events if e["event"] == "natural_reactivation"]
    if len(react) != 1 or react[0]["object"] != 1 or react[0]["trigger_target"] != 2 or react[0]["global_step"] != 1:
        errs.append(f"natural reactivation events {react}")
    elif react[0]["state_after"] != "ACTIONABLE" or react[0]["probe_before"].get("uncovered") != 0:
        errs.append(f"reactivation not QUIET -> ACTIONABLE: {react[0]}")
    if len(loop.actions) > 1 and loop.actions[1]["service_states_after"].get("1") != "ACTIONABLE":
        errs.append("A was not recomputed ACTIONABLE after B's observation")
    if not isinstance(loop.terminal, ic.Stop):
        errs.append(f"terminal {loop.terminal}")
    return errs


def t12b_cache_exact(rev_fn):
    ref = reactivation_world().run(revision=False)
    got = reactivation_world()
    got_loop = got.run(rev_fn=(lambda i, w=got: rev_fn(w, i)))
    return [] if _strip(ref) == _strip(got_loop) else ["cached loop differs from the cache-free loop"]


def t12c_no_reactivation_api():
    errs = []
    names = set()
    for path in (INTEGRATED, CONTROLLER):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.arg):
                names.add(node.arg)
            elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
                names.add(node.attr)
    bad = sorted(n for n in names if any(w in n.lower() for w in
                                          ("reactivat", "recency", "stale", "inhibit", "salien", "rank", "score")))
    if bad:
        errs.append(f"reactivation/recency/ranking API names: {bad}")
    members = {m.name for m in ic.ServiceState}
    if members != {"UNLOCATED", "SEEDABLE", "ACTIONABLE", "QUIET", "BLOCKED"}:
        errs.append(f"service states {sorted(members)}")
    return errs


# ---------------------------------------------------------------- 13 effective geometry

def _dummy_run():
    seeds = {"controller_domain_deg": {"yaw": [-25.0, 25.0], "pitch": [-20.0, 20.0]},
             "instances": [{"instance_id": 7, "object_name": "a", "seed_gaze_deg": [0.0, 0.0]},
                           {"instance_id": 8, "object_name": "b", "seed_gaze_deg": [1.0, 0.0]}]}
    cat = {"instances": [{"instance_id": 7, "object_name": "a"}, {"instance_id": 8, "object_name": "b"},
                         {"instance_id": 9, "object_name": "c"}]}
    return c01.ClassroomController01(REPO, REPO / "nonexistent-run", REPO, argparse.Namespace(), seeds, cat)


def _patch(points: dict[int, np.ndarray]) -> dict[str, np.ndarray]:
    xyz = np.concatenate([p for p in points.values()]).astype(np.float32)
    inst = np.concatenate([np.full(len(p), k, np.int32) for k, p in points.items()])
    return {"xyz_h": xyz[None], "instance_id": inst[None], "valid": np.ones((1, len(inst)), bool)}


def t13_effective_geometry(geometry_fn):
    errs = []
    run = _dummy_run()
    rng = np.random.default_rng(13)
    own = rng.normal([0.0, 0.0, -2.0], 0.05, (150, 3))
    sm = surface_map.initialize(surface_map.Patch("fix_00", own, np.ones_like(own), np.full(150, 7)), 7)
    run.ctx[7].surface_map = sm
    snap_map = [np.asarray(getattr(sm, f)).copy() for f in ("xyz_h", "rgb", "instance_id", "support_count",
                                                          "provenance_mask")] + [list(sm.patch_ids)]
    cross = rng.normal([0.4, 0.1, -2.0], 0.05, (50, 3))
    run.memory.append_patch(_patch({7: cross, 8: rng.normal([1.0, 0, -2.0], 0.05, (30, 3))}),
                            source_global_index=4, source_active_target_id=8)
    geo = geometry_fn(run, 7)
    cross32 = cross.astype(np.float32).astype(np.float64)
    if len(geo) != 150 + 50:
        errs.append(f"effective geometry has {len(geo)} points, expected map 150 + cross 50")
    have = {tuple(r) for r in np.round(np.asarray(geo, np.float64), 9)}
    if not all(tuple(r) in have for r in np.round(cross32, 9)):
        errs.append("effective geometry misses causal cross-target XYZ")
    now = [np.asarray(getattr(sm, f)) for f in ("xyz_h", "rgb", "instance_id", "support_count",
                                                "provenance_mask")] + [list(sm.patch_ids)]
    if run.ctx[7].surface_map is not sm or not all(
            (a == b) if isinstance(a, list) else (a.shape == b.shape and np.array_equal(a, b))
            for a, b in zip(snap_map, now)):
        errs.append("the active-target SurfaceMap was mutated")
    prov = run.memory_provenance(7)
    if prov["cross_target_points"] != 50 or prov["by_source_target"] != {"8": 50}:
        errs.append(f"cross-target provenance {prov}")
    return errs


def t12c_revision_tracks_memory(revision_fn):
    """The real probe-cache key changes exactly when a probe input changes."""
    errs = []
    run = _dummy_run()
    rng = np.random.default_rng(12)
    r7, r8, r9 = (revision_fn(run, i) for i in (7, 8, 9))
    run.remember_measurements(_patch({7: rng.normal([0.4, 0.1, -2.0], 0.05, (20, 3))}), 0, 8)
    if revision_fn(run, 7) == r7:
        errs.append("revision of 7 unchanged after a look measured instance 7")
    if revision_fn(run, 9) != r9 or revision_fn(run, 8) != r8:
        errs.append("revision of an unmeasured, unobserved object changed")
    run.ctx[8].visited.append((1.0, 0.0))
    if revision_fn(run, 8) == r8:
        errs.append("revision of 8 unchanged after its own look")
    for i in (7, 8, 9):
        if run.revision(i)[1] != len(run.memory.snapshot(i).xyz_h):
            errs.append(f"measured point count of {i} disagrees with the memory snapshot")
    return errs


def m_geometry_map_only(run, i):
    return run.map_xyz(i)


def m_geometry_fuses(run, i):
    sm = run.ctx[i].surface_map
    extra = np.asarray(run.memory.snapshot(i).xyz_h, np.float64)
    sm.xyz_h = np.vstack((sm.xyz_h, extra))
    return run.map_xyz(i)


# ---------------------------------------------------------------- 14 intrinsic view

DOMAIN = {"yaw": [-2.0, 2.0], "pitch": [-1.5, 1.5]}


def _dir_points(yaw_deg, pitch_deg, r):
    y, p = np.radians(yaw_deg), np.radians(pitch_deg)
    return r * np.stack([np.sin(y) * np.cos(p), np.sin(p), -np.cos(y) * np.cos(p)], -1)


def _view_fixture():
    yy, pp = np.meshgrid(np.linspace(-0.6, 0.2, 12), np.linspace(-0.5, 0.5, 10))
    target = _dir_points(yy, pp, 2.0).reshape(-1, 3)
    yy2, pp2 = np.meshgrid(np.linspace(0.5, 1.2, 10), np.linspace(-0.3, 0.6, 9))
    other = _dir_points(yy2, pp2, 1.5).reshape(-1, 3)
    head = HeadEvidence.empty((31, 41))
    for tgt in (5, 6):
        pts = np.vstack([target, other])
        ids = np.r_[np.full(len(target), 5), np.full(len(other), 6)].astype(np.int32)
        add_head_patch(head, {"xyz_h": pts[None].astype(np.float32), "instance_id": ids[None],
                              "valid": np.ones((1, len(ids)), bool)}, tgt, DOMAIN, 0.10)
    seen = np.zeros((31, 41), bool)
    seen[5:26, 3:35] = True
    return {5: target, 6: other}, head, seen


def t14_intrinsic_view(head_view_fn, view_fn):
    errs = []
    geos, head, seen = _view_fixture()
    layers = ic.support_layers(geos, DOMAIN, 0.10)
    a, r, e, d = view_fn(target_id=5, target_name="t", layers=layers, head_view=head_view_fn(head),
                         seen_any=seen, domain=DOMAIN, grid_deg=0.10)
    kinds = {x["kind"] for x in r}
    if not {"TARGET_SUPPORT", "OTHER_SURFACE", "UNKNOWN"} <= kinds:
        errs.append(f"fixture kinds {sorted(kinds)}")
    leaked = sorted({k for x in r for k in x if k in FORBIDDEN_VIEW_FIELDS} | (set(d) & set(FORBIDDEN_VIEW_FIELDS)))
    if leaked:
        errs.append(f"non-intrinsic fields {leaked}")
    owner = joint_owner({k: support_depth_from_map(v, DOMAIN, 0.10, instance_id=k, object_name=str(k))
                         for k, v in geos.items()})[0]
    ref = build_epistemic_partition({
        "target_support": layers[5].support, "owner_instance": owner, "nearest_instance": head.nearest_instance,
        "ambiguous_instance": head.ambiguous_instance, "depth_seen": head.depth_seen, "seen_any": seen},
        target_id=5, target_name="t", domain=DOMAIN, grid_deg=0.10)
    if r != ref[1] or d != ref[3] or not all(np.array_equal(a[k], ref[0][k]) for k in ref[0]):
        errs.append("view differs from the intended support -> joint_owner -> Core-14 construction")
    rng = np.random.default_rng(14)
    head.target_depth_seen[:] = rng.random(head.target_depth_seen.shape) < 0.5
    head.other_depth_seen[:] = rng.random(head.other_depth_seen.shape) < 0.5
    a2, r2, _e2, d2 = view_fn(target_id=5, target_name="t", layers=layers, head_view=head_view_fn(head),
                              seen_any=seen, domain=DOMAIN, grid_deg=0.10)
    if r2 != r or d2 != d or not all(np.array_equal(a2[k], a[k]) for k in a):
        errs.append("view depends on the target-relative HeadEvidence fields")
    for field in FORBIDDEN_VIEW_FIELDS:
        try:
            ic.assert_intrinsic([{**r[0], field: None}], d) if field != "candidate_region_count" \
                else ic.assert_intrinsic(r, {**d, field: 0})
            errs.append(f"a view annotated with {field} was accepted")
        except AssertionError:
            pass
    try:
        ic.assert_intrinsic(r, d)
    except AssertionError as exc:
        errs.append(f"the real intrinsic view was refused: {exc}")
    return errs


def m_head_view_target_relative(head):
    v = ic.target_neutral_head_view(head)
    v["depth_seen"] = np.asarray(head.depth_seen, bool) & ~np.asarray(head.other_depth_seen, bool)
    return v


def m_view_with_candidates(**k):
    from fov3d.experiments.classroom_partition.candidate_policy import annotate_candidate_partition
    a, r, e, d = ic.target_epistemic_view(**k)
    r, d = annotate_candidate_partition(r, d)
    return a, r, e, d


# ---------------------------------------------------------------- 15-16 blocking

def t15_seed_failure(world_fn, sched):
    errs = []
    with patched(ic, "schedule", sched):
        w = world_fn()
        loop = w.run()
    if isinstance(loop.terminal, ic.Stop):
        errs.append("successful global STOP after a seed initialization failure")
    if loop.final[1].label != "BLOCKED:seed_uninitializable":
        errs.append(f"object 1 final state {loop.final[1].label}")
    if 2 not in {a["target_id"] for a in loop.actions}:
        errs.append("the blocked object stopped the service of the other object")
    if not isinstance(loop.terminal, ic.Incomplete):
        errs.append(f"terminal {loop.terminal}")
    return errs


def seed_fail_world():
    return ToyWorld({1: [0.0], 2: [5.0]}, {1: 0.0, 2: 5.0}, seed_fail=(1,))


def t16_watchdog(world_fn, probe_wrap):
    errs = []
    w = world_fn()
    if probe_wrap is not None:
        w.probe = probe_wrap(w.probe, w)
    loop = w.run(watchdog=24) if probe_wrap is None else w.run(watchdog=10 ** 9)
    labels = [a["service_states_after"].get("1") for a in loop.actions]
    if loop.final[1].label != "BLOCKED:watchdog":
        errs.append(f"always-actionable object final state {loop.final[1].label}")
    if "QUIET" in labels:
        errs.append("a watchdog-bound object was recorded QUIET")
    if loop.fixations[1] != 24:
        errs.append(f"fixations {loop.fixations[1]}")
    if isinstance(loop.terminal, ic.Stop):
        errs.append("successful STOP with a watchdog-blocked object")
    blocked = [e for e in loop.events if e["event"] == "blocked"]
    if [(e["object"], e["reason"]) for e in blocked] != [(1, "watchdog")]:
        errs.append(f"blocked events {blocked}")
    return errs


def watchdog_world():
    return ToyWorld({1: [0.0], 2: [9.0]}, {1: 0.0, 2: 9.0}, always_actionable=(1,))


def m_watchdog_as_quiet(probe, world):
    def wrapped(i):
        if i == 1 and len(world.visited[1]) >= 24:
            return ic.ProbeResult(None, {"toy": "forced quiet"})
        return probe(i)
    return wrapped


def t16b_quiet_at_watchdog_and_reactivation():
    """Quiet at 24 stays QUIET; a later reactivation at 24 fixations becomes BLOCKED:watchdog."""
    errs = []
    w = ToyWorld({1: [0.0, 30.0], 2: [29.5]}, {1: 0.0, 2: 29.5})
    base_probe = w.probe

    def probe(i):
        if i == 1 and len(w.visited[1]) < 24:
            return ic.ProbeResult(ic.Observe(1, (0.001 * len(w.visited[1]) + 0.0001, 0.0), c01.VERGENCE, c01.FOCUS,
                                             "fsg6f"), {"toy": "ramp"})
        return base_probe(i)

    w.probe = probe
    loop = w.run(watchdog=24)
    react = [e for e in loop.events if e["event"] == "natural_reactivation"]
    quiet1 = [e for e in loop.events if e["event"] == "quiet" and e["object"] == 1]
    if not quiet1 or quiet1[0]["fixations"] != 24:
        errs.append(f"object 1 did not go QUIET at 24 fixations: {quiet1}")
    if [(e["object"], e["state_after"]) for e in react] != [(1, "BLOCKED:watchdog")]:
        errs.append(f"reactivation at the watchdog: {react}")
    if loop.final[1].label != "BLOCKED:watchdog" or not isinstance(loop.terminal, ic.Incomplete):
        errs.append(f"final {loop.final[1].label} terminal {loop.terminal}")
    return errs


# ---------------------------------------------------------------- 17 truth firewall

def t17_firewall(predicate):
    errs = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "run"
        (root / "bootstrap" / "evaluation_only").mkdir(parents=True)
        np.savez(root / "bootstrap" / "evaluation_only" / "reachable_samples.npz", x=np.zeros(3))
        (root / "bootstrap" / "seeds.json").write_text("{}")
        (root / "evaluation.json").write_text("{}")
        fw = ic.TruthFirewall(root, predicate)
        with fw:
            json.loads((root / "bootstrap" / "seeds.json").read_text())
            for label, fn in (
                ("np.load evaluation_only", lambda: np.load(root / "bootstrap/evaluation_only/reachable_samples.npz")),
                ("open evaluation.json", lambda: open(root / "evaluation.json").read()),
                ("list evaluation_only", lambda: os.listdir(root / "bootstrap/evaluation_only")),
            ):
                try:
                    fn()
                    errs.append(f"firewall allowed: {label}")
                except PermissionError:
                    pass
        if "bootstrap/seeds.json" not in fw.opened:
            errs.append(f"allowed read not recorded: {sorted(fw.opened)}")
        if len(fw.violations) != 3 and not errs:
            errs.append(f"violations recorded {fw.violations}")
        open(root / "evaluation.json").read()  # after control the evaluator may open it
    for p, want in (("/r/bootstrap/evaluation_only/reachable_samples.npz", True), ("/r/evaluation.json", True),
                    ("/r/bootstrap/seeds.json", False), ("/r/objects/instance_0001/result.json", False)):
        if c01.is_evaluation_truth(p) != want:
            errs.append(f"is_evaluation_truth({p}) != {want}")
    return errs


# ---------------------------------------------------------------- architecture

def _imports(path: Path) -> set[str]:
    out = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            out.add(node.module or "")
            out |= {f"{node.module}.{a.name}" for a in node.names}
    return out


def architecture() -> None:
    imp = _imports(INTEGRATED)
    tops = {m.split(".")[0] for m in imp}
    bad = sorted(m for m in imp if m.split(".")[0] in HISTORICAL_BARE | {"tools", "bpy", "cv2"}
                 or any(h in m for h in HISTORICAL_POLICY) or ".eval" in m or "fov3d.experiments" in m
                 or m.startswith(("fov3d.control.frontier", "fov3d.control.object_policy")))
    check("A1 integrated.py imports no Blender, tools, historical module, policy, evaluator or experiment",
          not bad and tops <= {"__future__", "dataclasses", "enum", "os", "sys", "typing", "numpy", "fov3d"},
          str(bad or sorted(tops)))
    imp = _imports(CONTROLLER)
    bad = sorted(m for m in imp if m.split(".")[0] in HISTORICAL_BARE | {"tools", "bpy"}
                 or any(h in m for h in HISTORICAL_POLICY) or m.endswith(".eval")
                 or m.startswith("fov3d.experiments.classroom_oracle.run"))
    stdlib = {"__future__", "argparse", "dataclasses", "json", "os", "pathlib", "subprocess", "time", "typing"}
    tops = {m.split(".")[0] for m in imp}
    check("A2 controller01.py imports only fov3d namespaces, NumPy, OpenCV and the standard library",
          not bad and tops <= stdlib | {"cv2", "numpy", "fov3d"}, str(bad or sorted(tops - stdlib)))
    not_loaded = ["bpy", "bl_common", "render_foveated", "warp", "exr_lite", "classroom_oracle1_render",
                  "classroom_oracle1_run", "classroom_oracle1_eval"]
    code = ("import sys, fov3d.control.integrated, fov3d.experiments.classroom_oracle.controller01; "
            f"bad = {not_loaded!r}; pol = {list(HISTORICAL_POLICY)!r}; "
            "print(sorted(m for m in sys.modules if m.split('.')[-1] in bad or any(h in m for h in pol)))")
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True,
                         env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    check("A3 fresh import loads no Blender, renderer, evaluator, run module or historical partition policy",
          out.returncode == 0 and out.stdout.strip() == "[]", (out.stdout + out.stderr).strip()[-300:])
    code = "import sys, fov3d.control.integrated; print(sorted(m for m in sys.modules if m.startswith(('tools','fsg','classroom','multiobject','bl_','fov3d.experiments'))))"
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True,
                         env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    check("A4 fov3d.control.integrated alone loads no sealed engine or experiment module",
          out.returncode == 0 and out.stdout.strip() == "[]", (out.stdout + out.stderr).strip()[-300:])
    src = CONTROLLER.read_text()
    tree = ast.parse(src)
    hits = []
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for node in ast.walk(fn):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and \
                    ("evaluation_only" in node.value or "evaluation.json" in node.value):
                hits.append(fn.name)
    check("A5 controller01 names evaluation truth only inside is_evaluation_truth; never reachable_samples",
          set(hits) == {"is_evaluation_truth"} and "reachable_samples" not in src, str(sorted(set(hits))))
    plot = (REPO / "tools/controller/plot_controller01.py").read_text()
    check("A5b the visual tool never names evaluation truth",
          not any(w in plot for w in ("evaluation_only", "evaluation.json", "reachable_samples")))
    errs = errors_of(t12c_no_reactivation_api)
    check("A6 no reactivation/recency/inhibition/ranking API; exactly the five service states", not errs, "; ".join(errs))
    layout = json.loads(LAYOUT.read_text())
    sealed = ["tools/" + m["legacy"].split(".", 1)[1] + ".py" for m in layout["mappings"]]
    changed = []
    for rel in sealed:
        base = subprocess.run(["git", "show", f"{BASE}:{rel}"], cwd=REPO, capture_output=True).stdout
        if base != (REPO / rel).read_bytes():
            changed.append(rel)
    check(f"A7 the {len(sealed)} sealed tools-root modules are byte-identical to the base", len(sealed) == 16 and not changed,
          str(changed))
    diff = subprocess.run(["git", "diff", "--name-status", BASE, "--", "fov3d"], cwd=REPO, capture_output=True,
                          text=True).stdout.split("\n")
    diff = [x for x in diff if x.strip()]
    allowed = {"A\tfov3d/control/integrated.py", "A\tfov3d/experiments/classroom_oracle/controller01.py"}
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "fov3d"], cwd=REPO,
                               capture_output=True, text=True).stdout.split()
    extra = [x for x in diff if x not in allowed] + [u for u in untracked if "__pycache__" not in u and
                                                     u not in {"fov3d/control/integrated.py",
                                                               "fov3d/experiments/classroom_oracle/controller01.py"}]
    check("A8 every pre-existing fov3d file (including the Core-14 partition) is unchanged; only the two modules are new",
          not extra, str(extra[:4]))


# ---------------------------------------------------------------- unit suite

def unit() -> None:
    sched = ic.schedule
    verified("01 current ACTIONABLE object is retained", t01_retain_actionable, (sched,),
             {"never-retain scheduler": (m_never_retain,)})
    verified("02 current SEEDABLE object is retained", t02_retain_seedable, (sched,),
             {"never-retain scheduler": (m_never_retain,)})
    verified("03 current QUIET/BLOCKED object -> deterministic cyclic switch", t03_cyclic_switch, (sched,),
             {"retain-anything scheduler": (m_retain_anything,), "restart-scan scheduler": (m_restart_scan,)})
    verified("04 all localized initialized objects QUIET -> STOP(global_quiescence)", t04_all_quiet_stop, (sched,),
             {"unlocated-treated-as-seedable scheduler": (m_unlocated_as_quiet_seedable,),
              "retain-anything scheduler": (m_retain_anything,)})
    verified("05 a SEEDABLE object prevents STOP", t05_seedable_prevents_stop, (sched,),
             {"seedable-ignored scheduler": (m_seedable_ignored,)})
    verified("06 an ACTIONABLE object prevents STOP", t06_actionable_prevents_stop, (sched,),
             {"actionable-ignored scheduler": (m_actionable_ignored,)})
    verified("07 a localized BLOCKED object prevents global_quiescence", t07_blocked_prevents_quiescence, (sched,),
             {"blocked-as-quiet scheduler": (m_blocked_as_quiet,)})
    verified("08 UNLOCATED is not silently QUIET", t08_unlocated_not_quiet, (sched, ic.catalog_summaries),
             {"unlocated-as-quiet classification": (sched, m_classify_unlocated_quiet),
              "unlocated-serviceable scheduler": (m_unlocated_as_quiet_seedable, ic.catalog_summaries)})
    verified("09 ascending-id/cyclic order is deterministic", t09_deterministic_order, (sched,),
             {"input-order scheduler": (m_input_order,)})
    verified("10 selection uses only service state and identity", t10_state_identity_only,
             (lambda c, s, side: ic.schedule(c, s),), {"ranking selector": (m_ranking_selector,)})
    verified("11 can_act and choose_action are views of one probe result", t11_probe_consistency,
             (ic.can_act, ic.choose_action, c01.probe_local_policy),
             {"can_act from a separate flag": (m_can_act_flag, ic.choose_action, c01.probe_local_policy),
              "probe skipping the Cyclopean handoff": (ic.can_act, ic.choose_action, m_probe_skips_cyclopean)})
    verified("11b the real FSG6f/Cyclopean probe is pure (repeatable, inputs unmutated)", t11b_probe_pure,
             (c01.probe_local_policy,), {"input-mutating probe": (m_probe_mutating,)})
    verified("12 synthetic natural reactivation through the real control loop", t12_natural_reactivation,
             (reactivation_world, {}),
             {"stale-key cache (never re-probes a quiet object)":
              (reactivation_world, {"rev_fn": lambda i: 0})})
    verified("12b exact probe cache equals the cache-free loop", t12b_cache_exact,
             (lambda w, i: w.revision(i),), {"own-look-only revision key": (lambda w, i: len(w.visited[i]),)})
    verified("12c the real probe-cache key tracks own looks and measured points", t12c_revision_tracks_memory,
             (lambda run, i: run.revision(i),),
             {"own-look-only key": (lambda run, i: len(run.ctx[i].visited) if i in run.ctx else 0,)})
    verified("13 effective target geometry includes cross-target XYZ; SurfaceMap untouched", t13_effective_geometry,
             (lambda run, i: run.geometry(i),),
             {"map-only geometry": (m_geometry_map_only,), "geometry fusing into the map": (m_geometry_fuses,)})
    verified("14 the Core-14 target view is intrinsic and target-neutral in HeadEvidence", t14_intrinsic_view,
             (ic.target_neutral_head_view, ic.target_epistemic_view),
             {"target-relative head view": (m_head_view_target_relative, ic.target_epistemic_view),
              "candidate-annotated view": (ic.target_neutral_head_view, m_view_with_candidates)})
    verified("15 no successful global STOP after a seed initialization failure", t15_seed_failure,
             (seed_fail_world, ic.schedule), {"blocked-as-quiet scheduler": (seed_fail_world, m_blocked_as_quiet)})
    verified("16 watchdog-blocked is not QUIET", t16_watchdog, (watchdog_world, None),
             {"watchdog reported as quiet": (watchdog_world, m_watchdog_as_quiet)})
    errs = errors_of(t16b_quiet_at_watchdog_and_reactivation)
    check("16b quiet at 24 stays QUIET; a reactivation at 24 fixations is BLOCKED:watchdog", not errs, "; ".join(errs))
    verified("17 truth firewall rejects bootstrap/evaluation_only and evaluation.json", t17_firewall,
             (c01.is_evaluation_truth,), {"permissive firewall predicate": (lambda p: False,)})


# ---------------------------------------------------------------- run validation

def _summary_from_label(i: int, label: str) -> ic.ObjectSummary:
    if label.startswith("BLOCKED:"):
        return O(i, S.BLOCKED, label.split(":", 1)[1])
    return O(i, S(label))


def validate_run(root: Path) -> None:
    tag = f"R[{root.name}]"
    manifest = json.loads((root / "manifest.json").read_text())
    check(f"{tag} manifest schema and control_complete", manifest.get("schema") == c01.SCHEMA
          and manifest.get("control_complete") is True, str(manifest.get("terminal")))
    fw = manifest.get("truth_firewall", {})
    opened = list(fw.get("opened_run_files", []))
    check(f"{tag} truth firewall: no violation, no truth file opened, dense truth flag false",
          manifest.get("dense_evaluation_truth_opened_during_control") is False and fw.get("violations") == []
          and not any(c01.is_evaluation_truth(str(root / p)) for p in opened)
          and {"bootstrap/seeds.json", "bootstrap/instance_catalog.json"} <= set(opened),
          str([p for p in opened if c01.is_evaluation_truth(str(root / p))][:3]))
    seeds_doc = json.loads((root / "bootstrap/seeds.json").read_text())
    catalog_doc = json.loads((root / "bootstrap/instance_catalog.json").read_text())
    seeds = {int(s["instance_id"]): tuple(map(float, s["seed_gaze_deg"])) for s in seeds_doc["instances"]}
    catalog = {int(o["instance_id"]) for o in catalog_doc["instances"]}
    unlocated = sorted(catalog - set(seeds))
    doc = json.loads((root / "actions.json").read_text())
    acts, events = doc["actions"], doc["events"]
    check(f"{tag} catalog/localized/unlocated counts", manifest["known_catalog_objects"] == len(catalog)
          and manifest["localized_objects"] == len(seeds) and manifest["unlocated_objects"] == len(unlocated)
          and manifest["unlocated_object_ids"] == unlocated and set(seeds) <= catalog)
    check(f"{tag} contiguous global steps", [a["global_step"] for a in acts] == list(range(len(acts)))
          and manifest["total_actions"] == len(acts), f"{len(acts)} actions")

    per: dict[int, list[dict]] = {}
    for a in acts:
        per.setdefault(int(a["target_id"]), []).append(a)
    errs = []
    for i, rows_i in per.items():
        if i not in seeds:
            errs.append(f"{i} not localized")
            continue
        if rows_i[0]["action_source"] != "oracle_seed" or tuple(rows_i[0]["gaze_deg"]) != seeds[i]:
            errs.append(f"{i} first look is not its bootstrap seed")
        if any(r["action_source"] not in ic.PROBE_SOURCES for r in rows_i[1:]):
            errs.append(f"{i} post-seed look with source {[r['action_source'] for r in rows_i[1:]]}")
        if [r["object_local_step"] for r in rows_i] != list(range(len(rows_i))):
            errs.append(f"{i} local steps not sequential")
        g = [tuple(r["gaze_deg"]) for r in rows_i]
        if len(set(g)) != len(g):
            errs.append(f"{i} repeated own-target gaze")
        if len(rows_i) > c01.WATCHDOG:
            errs.append(f"{i} exceeded the watchdog")
    check(f"{tag} seed first and only first; post-seed sources; unique own gazes; <= 24 looks", not errs, "; ".join(errs[:3]))
    check(f"{tag} fixed vergence/focus recorded on every action",
          all(a["vergence"] == c01.VERGENCE and a["focus"] == c01.FOCUS
              and abs(a["prescribed_vergence_distance_m"] - c01.VERGENCE["distance_m"]) < 1e-12 for a in acts))

    errs = []
    prev_target = None
    bout = 0
    reactivated: set[int] = set()
    for t, a in enumerate(acts):
        summaries = [_summary_from_label(int(k), v) for k, v in a["service_states_before"].items()]
        summaries += [O(u, S.UNLOCATED) for u in unlocated]
        d = ic.schedule(prev_target, summaries)
        if (d.kind, d.target_id, d.reason) != ("attend", a["target_id"], a["scheduler_decision"]):
            errs.append(f"step {t}: replay {d.target_id}/{d.reason} vs logged {a['target_id']}/{a['scheduler_decision']}")
        if a["service_state_before"] != a["service_states_before"][str(a["target_id"])]:
            errs.append(f"step {t}: target state before inconsistent")
        if t and acts[t - 1]["service_states_after"] != a["service_states_before"]:
            errs.append(f"step {t}: states after step {t - 1} differ from states before step {t}")
        if a["scheduler_decision"] in ("initial", "switch"):
            bout += 1
        want_reason = "natural_reactivation" if (a["scheduler_decision"] == "switch" and a["target_id"] in reactivated) \
            else a["scheduler_decision"]
        if a["attention_bout"] != bout or a["scheduler_reason"] != want_reason:
            errs.append(f"step {t}: bout/reason {a['attention_bout']}/{a['scheduler_reason']} vs {bout}/{want_reason}")
        reactivated.discard(a["target_id"])
        reactivated |= {e["object"] for e in a["events"] if e["event"] == "natural_reactivation"}
        prev_target = a["target_id"]
    final_labels = acts[-1]["service_states_after"] if acts else {str(i): "SEEDABLE" for i in seeds}
    summaries = [_summary_from_label(int(k), v) for k, v in final_labels.items()] + [O(u, S.UNLOCATED) for u in unlocated]
    d = ic.schedule(prev_target, summaries)
    term = manifest["terminal"]
    if term["type"] == "CAP":
        ok_term = manifest["smoke"] and len(acts) == term["cap"] == c01.SMOKE_ACTION_CAP and d.kind == "attend"
    elif term["type"] == "STOP":
        ok_term = d.kind == "terminal" and isinstance(d.terminal, ic.Stop)
    else:
        ok_term = d.kind == "terminal" and isinstance(d.terminal, ic.Incomplete) and \
            [list(b) for b in d.terminal.blocked] == term["blocked"]
    check(f"{tag} the pure scheduler replayed over the logged states reproduces every decision", not errs,
          "; ".join(errs[:3]))
    check(f"{tag} terminal decision replays ({term['type']} {term['reason']})", ok_term, str(d))
    finals = manifest["final_service_states"]
    all_quiet = all(v["state"] == "QUIET" for v in finals.values())
    labels = {k: (v["state"] if v["blocked_reason"] is None else f"BLOCKED:{v['blocked_reason']}")
              for k, v in finals.items()}
    check(f"{tag} global_quiescence iff every localized object is initialized and QUIET",
          manifest["global_quiescence"] == (term["type"] == "STOP") == all_quiet and labels == final_labels,
          f"global_quiescence={manifest['global_quiescence']} all_quiet={all_quiet} terminal={term['type']}")
    switches = sum(a["scheduler_decision"] == "switch" for a in acts)
    kinds = {k: sum(e["event"] == k for e in events) for k in ("quiet", "natural_reactivation", "seed_initialized")}
    check(f"{tag} counts: switches, bouts, quiet episodes, reactivations, initialized",
          manifest["total_switches"] == switches and manifest["attention_bouts"] == bout
          and manifest["quiet_episodes"] == kinds["quiet"] and manifest["natural_reactivations"] == kinds["natural_reactivation"]
          and manifest["successfully_initialized_objects"] == kinds["seed_initialized"],
          f"switches={switches} bouts={bout} {kinds}")
    errs = []
    for e in events:
        if e["event"] != "natural_reactivation":
            continue
        a = acts[e["global_step"]]
        if a["service_states_before"].get(str(e["object"])) != "QUIET" or \
                a["service_states_after"].get(str(e["object"])) not in ("ACTIONABLE", "BLOCKED:watchdog") or \
                e["trigger_target"] == e["object"] or a["target_id"] != e["trigger_target"]:
            errs.append(f"reactivation event inconsistent: object {e['object']} step {e['global_step']}")
        if not (root / str(e.get("epistemic_view", {}).get("path", "missing"))).is_file():
            errs.append(f"reactivation view missing for object {e['object']}")
    for e in events:
        view = e.get("epistemic_view")
        if view is not None:
            s = view["summary"]
            if s.get("truth_used") is not False or set(s) & set(FORBIDDEN_VIEW_FIELDS) or \
                    not (root / view["path"]).is_file():
                errs.append(f"view {view['path']} invalid")
    check(f"{tag} events: reactivations QUIET -> ACTIONABLE by another target; saved views intrinsic", not errs,
          "; ".join(errs[:3]))

    memory = InstanceMeasurementMemory()
    errs = []
    for a in acts:
        i, k = int(a["target_id"]), int(a["object_local_step"])
        with np.load(root / f"objects/instance_{i:04d}/patches/fix_{k:02d}.npz", allow_pickle=False) as z:
            patch = {n: z[n] for n in z.files}
        added = memory.append_patch(patch, source_global_index=a["global_step"], source_active_target_id=i)
        if {str(x): int(v) for x, v in sorted(added.items())} != a["measurement_memory_additions"]:
            errs.append(f"step {a['global_step']}: memory additions differ")
    for i in sorted(per):
        odir = root / f"objects/instance_{i:04d}"
        res = json.loads((odir / "result.json").read_text())
        fm = odir / "final_map.npz"
        map_xyz = np.load(fm)["xyz_h"] if fm.exists() else np.empty((0, 3), np.float32)
        with np.load(odir / "final_effective_geometry.npz", allow_pickle=False) as z:
            eff = z["xyz_h"]
            n_map = int(z["active_map_points"])
            gsrc, tsrc = z["measured_source_global_index"], z["measured_source_active_target_id"]
        snap = memory.snapshot(i)
        want = effective_target_geometry(map_xyz.astype(np.float64), snap.xyz_h).astype(np.float32)
        if n_map != len(map_xyz) or eff.shape != want.shape or not np.array_equal(eff, want) or \
                not np.array_equal(gsrc, snap.source_global_index) or not np.array_equal(tsrc, snap.source_active_target_id):
            errs.append(f"{i}: final effective geometry differs from map + replayed memory")
        traj = res["trajectory"]
        if res["fixation_count"] != len(per[i]) or res["final_map_surfels"] != len(map_xyz) or \
                (traj and traj[-1]["map_size_after"] != len(map_xyz)):
            errs.append(f"{i}: final map / trajectory mismatch")
    check(f"{tag} measurement memory replayed from saved patches reproduces additions and effective geometry",
          not errs, "; ".join(errs[:3]))
    rows_m = {int(o["instance_id"]): o for o in manifest["objects"]}
    check(f"{tag} evaluator-compatible manifest rows for attempted objects",
          set(rows_m) == set(per) and all(
              rows_m[i]["fixation_count"] == len(per[i]) and len(rows_m[i]["trajectory"]) == len(per[i])
              and all("new_surfels" in r for r in rows_m[i]["trajectory"]) for i in per))


# ---------------------------------------------------------------- Controller-01A terminal re-probe audit

# The saved Controller-01 watchdog-prefix probe of object 210, restated from the Controller-01A contract
# (docs/controller/controller-01a-terminal-audit-contract.md).  The audit also compares against the saved
# probe record itself.
CONTROLLER01A_EXPECTED_PREFIX = {
    210: {"revision": [24, 1584958], "effective_points": 1748902, "state": "ACTIONABLE", "source": "fsg6f",
          "reason": "continue", "frontier_open_count": 58, "frontier_raw_count": 354,
          "frontier_map_resolved_count": 26, "frontier_boundary_resolved_count": 270, "candidates": 1,
          "consensus_rejected_candidates": 3, "next_gaze_deg": [7.6, 18.2]},
}


class AuditFailure(Exception):
    pass


def _audit_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def _same_summary(a, b, tol: float = 1e-9) -> bool:
    """Exact equality of probe summaries, with a gaze tolerance for floats."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_same_summary(a[k], b[k], tol) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_same_summary(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(float(a) - float(b)) <= tol
    return a == b


def _probe_record(result: ic.ProbeResult, decisions: dict, geometry_points: int, revision: list[int]) -> dict:
    action = result.action
    selected = (decisions.get("fsg6f_decision") or {}).get("selected")
    return {
        "state": result.state.value,
        "source": None if action is None else action.source,
        "proposed_gaze_deg": None if action is None else list(action.gaze_yaw_pitch_deg),
        "revision": list(revision),
        "effective_points": int(geometry_points),
        "summary": c01._jsonable(dict(result.detail)),
        "fsg6f_selected": None if selected is None else c01._jsonable(
            {k: selected[k] for k in ("yaw_deg", "pitch_deg", "frontier_support_count", "raw_frontier_support_count",
                                      "map_resolved_support_count", "boundary_resolved_support_count",
                                      "predicted_new_angular_area_deg2", "frontier_score")}),
    }


def terminal_reprobe(root: Path, obj: int) -> dict:
    """Controller-01A: reconstruct the causal state of a completed run and re-probe one object.

    Read-only.  It replays the saved patches into a fresh InstanceMeasurementMemory, rebuilds the
    object's own local-policy context from its saved acquisitions with the accepted matcher, validates
    the reconstruction against the saved watchdog-prefix probe, and only then asks the unchanged
    accepted local probe again at the terminal state.  No render, fusion or policy change.
    """
    from fov3d.control import object_policy
    from fov3d.experiments.classroom_oracle import epistemic, matcher

    out: dict = {"run": str(root), "object": obj, "gates": [], "failure": None, "outcome": None}

    def gate(name: str, ok: bool, detail: str = "") -> None:
        out["gates"].append({"gate": name, "ok": bool(ok), "detail": detail})
        if not ok:
            raise AuditFailure(f"{name}: {detail}")

    fw = ic.TruthFirewall(root, c01.is_evaluation_truth)
    try:
        with fw:
            manifest = json.loads((root / "manifest.json").read_text())
            acts = json.loads((root / "actions.json").read_text())["actions"]
            odir = root / f"objects/instance_{obj:04d}"
            result = json.loads((odir / "result.json").read_text())

            # -- action order
            steps = [int(a["global_step"]) for a in acts]
            own = [a for a in acts if int(a["target_id"]) == obj]
            fixations = int(manifest["final_service_states"][str(obj)]["fixations"])
            gate("action order: contiguous ascending global steps; own looks at local steps 0..n-1 in global order; "
                 "count = manifest fixations",
                 steps == list(range(len(acts))) and [int(a["object_local_step"]) for a in own] == list(range(len(own)))
                 and len(own) == fixations and len(own) > 0,
                 f"steps ok={steps == list(range(len(acts)))}, own={len(own)}, fixations={fixations}")
            watchdog_step = int(own[-1]["global_step"])
            out["watchdog_step"] = watchdog_step

            # -- global measurement memory, replayed in global action order
            memory = InstanceMeasurementMemory()
            mismatched: list[int] = []

            def replay(a: dict) -> None:
                i, k = int(a["target_id"]), int(a["object_local_step"])
                patch = _audit_npz(root / f"objects/instance_{i:04d}/patches/fix_{k:02d}.npz")
                added = memory.append_patch(patch, source_global_index=int(a["global_step"]),
                                            source_active_target_id=int(a["target_id"]))
                if {str(x): int(v) for x, v in sorted(added.items())} != a["measurement_memory_additions"]:
                    mismatched.append(int(a["global_step"]))

            for a in acts[: watchdog_step + 1]:
                replay(a)
            gate("memory replay through the watchdog step reproduces every logged per-action addition", not mismatched,
                 f"mismatched steps {mismatched[:5]}")
            snap_w = memory.snapshot(obj)
            points_w = int(len(snap_w.xyz_h))

            # -- the object's own local-policy context, from its own saved acquisitions only
            ctx = c01.LocalPolicyContext(obj)
            gaze_bad, patch_bad = [], []
            for a in own:
                k = int(a["object_local_step"])
                adir = odir / "acquisitions" / f"fix_{k:02d}"
                c = json.loads((adir / "calibration.json").read_text())
                rec, _meta, st = matcher.compute(c, _audit_npz(adir / "oracle_observation.npz"))
                gaze = (float(a["gaze_deg"][0]), float(a["gaze_deg"][1]))
                if max(abs(float(c["gaze_yaw_pitch_deg"][j]) - gaze[j]) for j in (0, 1)) > 1e-9:
                    gaze_bad.append(k)
                saved = _audit_npz(odir / "patches" / f"fix_{k:02d}.npz")
                if not (np.array_equal(np.asarray(rec["xyz_h"], np.float32), saved["xyz_h"], equal_nan=True)
                        and np.array_equal(np.asarray(rec["valid"], bool), saved["valid"])
                        and np.array_equal(np.asarray(rec["instance_id"], np.int32), saved["instance_id"])):
                    patch_bad.append(k)
                epistemic.add_observation(ctx.evidence, c, st["ids_left"], st["raw_support_L"],
                                          st["ids_right"], st["raw_support_R"], rec["valid"], obj)
                ctx.history.append(object_policy.history_entry(
                    calibration=c, instance_L=st["ids_left"], raw_support_L=st["raw_support_L"],
                    instance_R=st["ids_right"], raw_support_R=st["raw_support_R"], target_object_id=obj))
                ctx.visited.append(gaze)
                ctx.gaze, ctx.calibration, ctx.state = gaze, c, st
            gate("own-look identity: each calibration gaze equals the logged gaze; each matcher-recreated patch equals "
                 "the saved patch", not gaze_bad and not patch_bad, f"gaze {gaze_bad}, patch {patch_bad}")
            logged_own = [(float(a["gaze_deg"][0]), float(a["gaze_deg"][1])) for a in own]
            gate("own context holds exactly the object's own looks (visited = logged own gazes in order; one history "
                 "entry per own look)", ctx.visited == logged_own and len(ctx.history) == len(own) == fixations,
                 f"visited {len(ctx.visited)}, history {len(ctx.history)}, own {len(own)}")

            # -- active map (saved geometry; no fusion)
            final_xyz = _audit_npz(odir / "final_map.npz")["xyz_h"]
            last_xyz = _audit_npz(odir / "maps" / f"fix_{len(own) - 1:02d}.npz")["xyz_h"]
            gate("active map: final_map equals the map after the last own look and its logged size",
                 np.array_equal(final_xyz, last_xyz) and len(final_xyz) == int(own[-1]["active_map_size_after"]),
                 f"{len(final_xyz)} vs {len(last_xyz)} / {own[-1]['active_map_size_after']}")
            map_xyz = np.asarray(final_xyz, np.float64)

            # -- watchdog-prefix reproduction (the stop gate)
            eff_w = effective_target_geometry(map_xyz, snap_w.xyz_h)
            res_w, dec_w = c01.probe_local_policy(ctx, eff_w)
            prefix = _probe_record(res_w, dec_w, len(eff_w), [len(own), points_w])
            out["watchdog_prefix_probe"] = prefix
            saved_w = [pr for pr in result["probes"] if int(pr["after_global_step"]) == watchdog_step]
            gate("the saved Controller-01 probe record after the watchdog step exists", len(saved_w) == 1,
                 f"{len(saved_w)} records")
            sw = saved_w[0]
            keys = ("fsg6f", "cyclopean", "effective_points")
            same_record = (sw["revision"] == prefix["revision"] and sw["state"] == prefix["state"]
                           and _same_summary({k: sw[k] for k in keys}, {k: prefix["summary"][k] for k in keys}))
            expected = CONTROLLER01A_EXPECTED_PREFIX.get(obj)
            same_contract = expected is None or (
                prefix["revision"] == expected["revision"] and prefix["effective_points"] == expected["effective_points"]
                and prefix["state"] == expected["state"] and prefix["source"] == expected["source"]
                and prefix["summary"]["fsg6f"]["reason"] == expected["reason"]
                and all(prefix["summary"]["fsg6f"][k] == expected[k] for k in (
                    "frontier_open_count", "frontier_raw_count", "frontier_map_resolved_count",
                    "frontier_boundary_resolved_count", "candidates", "consensus_rejected_candidates"))
                and _same_summary(prefix["proposed_gaze_deg"], expected["next_gaze_deg"]))
            gate("watchdog-prefix reproduction: the re-probe equals the saved Controller-01 probe record and the "
                 "contract's expected values", same_record and same_contract,
                 f"re-probe {prefix['state']} {prefix['source']} {prefix['summary'].get('fsg6f')} rev {prefix['revision']}")

            # -- terminal state: the remaining saved observations; own context unchanged
            for a in acts[watchdog_step + 1:]:
                replay(a)
            gate("memory replay of the remaining observations reproduces every logged per-action addition",
                 not mismatched, f"mismatched steps {mismatched[:5]}")
            snap_t = memory.snapshot(obj)
            eff_t = effective_target_geometry(map_xyz, snap_t.xyz_h)
            saved_eff = _audit_npz(odir / "final_effective_geometry.npz")
            gate("terminal effective geometry (XYZ and per-point provenance) equals the saved final_effective_geometry",
                 int(saved_eff["active_map_points"]) == len(final_xyz)
                 and np.array_equal(eff_t.astype(np.float32), saved_eff["xyz_h"])
                 and np.array_equal(snap_t.source_global_index, saved_eff["measured_source_global_index"])
                 and np.array_equal(snap_t.source_active_target_id, saved_eff["measured_source_active_target_id"]),
                 f"{len(eff_t)} vs {len(saved_eff['xyz_h'])}")
            after = snap_t.source_global_index > watchdog_step
            src = snap_t.source_active_target_id[after]
            out["measurements"] = {
                "measured_points_at_watchdog": points_w,
                "measured_points_at_terminal": int(len(snap_t.xyz_h)),
                "added_after_watchdog": int(after.sum()),
                "added_by_source_target": {str(int(t)): int((src == t).sum()) for t in np.unique(src)},
                "added_source_global_steps": sorted(int(g) for g in np.unique(snap_t.source_global_index[after])),
                "added_by_source_step": {str(int(g)): int((snap_t.source_global_index == g).sum())
                                         for g in np.unique(snap_t.source_global_index[after])},
                "active_map_points": int(len(final_xyz)),
                "effective_points_at_watchdog": int(len(eff_w)),
                "effective_points_at_terminal": int(len(eff_t)),
                "own_looks": len(own),
            }
            res_t, dec_t = c01.probe_local_policy(ctx, eff_t)
            out["terminal_probe"] = _probe_record(res_t, dec_t, len(eff_t), [len(own), int(len(snap_t.xyz_h))])
            out["outcome"] = "FINAL_REPROBE_ACTIONABLE" if ic.can_act(res_t) else "FINAL_REPROBE_QUIET"
    except AuditFailure as exc:
        out["failure"] = f"audit gate failed: {exc}"
    except Exception as exc:  # noqa: BLE001  (a reconstruction that cannot even be read is a failure)
        out["failure"] = f"{type(exc).__name__}: {exc}"
    out["firewall_violations"] = list(fw.violations)
    out["opened_run_files"] = sorted(fw.opened)
    if fw.violations:
        out["outcome"] = None
        out["failure"] = out["failure"] or f"truth firewall violations: {fw.violations}"
    return out


def run_terminal_audit(root: Path, obj: int, out_path: Path | None) -> None:
    res = terminal_reprobe(root, obj)
    for g in res["gates"]:
        check(f"01A {g['gate']}", g["ok"], g["detail"])
    check("01A truth firewall: no violation; no opened file is evaluation truth",
          not res["firewall_violations"] and not any(c01.is_evaluation_truth(str(root / p)) for p in res["opened_run_files"]),
          str(res["firewall_violations"]))
    check("01A audit reached a result (no reconstruction failure)", res["failure"] is None and res["outcome"] is not None,
          str(res["failure"]))
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    m = res.get("measurements", {})
    for label in ("watchdog_prefix_probe", "terminal_probe"):
        if label in res:
            pr = res[label]
            print(f"{PREFIX} 01A {label}: {pr['state']} source={pr['source']} gaze={pr['proposed_gaze_deg']} "
                  f"rev={pr['revision']} effective={pr['effective_points']} fsg6f={pr['summary']['fsg6f']} "
                  f"cyclopean={pr['summary']['cyclopean']}")
    if m:
        print(f"{PREFIX} 01A measurements: {json.dumps(m, sort_keys=True)}")
    print(f"{PREFIX} 01A opened run files: {len(res['opened_run_files'])}")
    if res["failure"] is None and res["outcome"] is not None:
        print(f"{PREFIX} 01A RESULT CONTROLLER01A_{res['outcome']}")
    else:
        print(f"{PREFIX} 01A AUDIT RECONSTRUCTION FAILURE: {res['failure']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, action="append", default=[], help="completed run directory to validate")
    ap.add_argument("--skip-unit", action="store_true", help="validate runs only")
    ap.add_argument("--terminal-reprobe", type=Path, default=None,
                    help="Controller-01A: read-only terminal re-probe audit of a completed run (implies --skip-unit)")
    ap.add_argument("--object", type=int, default=210, help="object id for --terminal-reprobe")
    ap.add_argument("--audit-out", type=Path, default=None, help="write the audit record as JSON here")
    args = ap.parse_args()
    if args.terminal_reprobe is not None:
        run_terminal_audit(args.terminal_reprobe.resolve(), args.object, args.audit_out)
        args.skip_unit = True
    if not args.skip_unit:
        unit()
        architecture()
    for run in args.run:
        validate_run(run.resolve())
    print(f"{PREFIX} SUMMARY checked={checked} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
