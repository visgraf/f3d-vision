"""North Star-1e: the pure functions of the full coherent multi-entity loop with M2 memory (host side; no Blender).

Contract: docs/north-star/ns1e-coherent-full-loop-m2-memory-contract.md, sections 5-27.

- record references and the entity context: the accepted ``ns1c2_core.context_from_record`` with a resolver that also
  knows the ``ns1c2:`` / ``ns1d:`` schemes (section 6.3);
- M2, the live controller geometry: ``effective_target_geometry(map, memory.snapshot(i).xyz_h)`` and the revision
  (own looks, measured points of observed id i) (section 8);
- the NORMAL probe (the accepted ``ns1c2_core.probe_normal_ctx``; no gate) and the RESIDUE gate adapter (the accepted
  ``final_look_gate_v1`` on the unchanged proposal, M2 geometry, the real fixed-head sensor) (sections 10, 12);
- the memory ledger rebuild from frozen patches, the map / memory digests, the derived hard cap (section 20);
- step-directory classification for checkpointing (section 21), the control outcome (section 24);
- the post-freeze evaluation helpers (section 26) and the PLY export (section 28).

No object name and no catalog ever enters these functions.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "active_bootstrap", HERE.parent / "natural_bootstrap",
           HERE.parent / "classroom_oracle", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1b_chart as CH  # noqa: E402  (accepted NS1b chart + frame adapter, read-only)
import ns1b_core as B  # noqa: E402  (accepted NS1b comparison / fusion functions, read-only)
import ns1c2_core as C2  # noqa: E402  (accepted NS1c2 context / probe functions, read-only)
import ns1d_core as K  # noqa: E402  (accepted NS1d memory patch / ledger / resume, read-only)
import ns1e_spec as SP  # noqa: E402
from fov3d.reconstruction.measurement_memory import effective_target_geometry  # noqa: E402  (accepted, unchanged)


class ProcessGuard:
    """The accepted ``NoProcessGuard`` mechanism (the same audit events; every process launch refused while active),
    defined here so that the measurement stages need not import the controller stack the accepted guard's module
    loads (their module records must show no cv2 / fsg_stereo / controller module).  The checker requires
    ``EVENTS`` to equal the accepted ``NoProcessGuard.EVENTS``."""

    EVENTS = ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork", "os.forkpty")
    _installed = False
    _active: "ProcessGuard | None" = None

    def __init__(self) -> None:
        self.attempts: list[str] = []

    def __enter__(self) -> "ProcessGuard":
        if not ProcessGuard._installed:
            sys.addaudithook(ProcessGuard._hook)
            ProcessGuard._installed = True
        if ProcessGuard._active is not None:
            raise RuntimeError("a process guard is already active")
        ProcessGuard._active = self
        return self

    def __exit__(self, *exc) -> None:
        ProcessGuard._active = None

    @staticmethod
    def _hook(event: str, args: tuple) -> None:
        guard = ProcessGuard._active
        if guard is None or event not in ProcessGuard.EVENTS:
            return
        guard.attempts.append(f"{event}: {args[0] if args else ''}")
        raise PermissionError(f"process launch refused during an NS1e measurement stage: {event}")


class StepAmbiguous(RuntimeError):
    """A step directory is partial or its stage outputs are not a prefix of the declared stage order."""


class LedgerMismatch(RuntimeError):
    """A frozen memory patch does not reproduce its recorded additions, digest or order."""


def jsonable(x: Any) -> Any:
    return C2.jsonable(x)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def canonical_digest(d: Any) -> str:
    return sha256_bytes(json.dumps(jsonable(d), sort_keys=True, allow_nan=False).encode())


# ------------------------------------------------------------------ references (section 6.1)
ROOTS = {"ns1a": SP.NS1A_RUN, "ns1b": SP.NS1B_RUN, "ns1c": SP.NS1C_RUN, "ns1c2": SP.NS1C2_RUN, "ns1d": SP.NS1D_RUN}


def resolve(ref: str, run: Path, roots: dict | None = None) -> Path:
    """'run:rel' (this NS1e run) / 'ns1a:' / 'ns1b:' / 'ns1c:' / 'ns1c2:' / 'ns1d:' -> a path."""
    scheme, rel = ref.split(":", 1)
    if scheme == "run":
        return Path(run) / rel
    return Path((roots or ROOTS)[scheme]) / rel


REF_FIELDS = (("looks", "calibration"), ("looks", "state"), ("evidence", "path"), ("map", "path"), ("probe", "path"))


def rescope(rec: dict, scheme: str = "ns1c2") -> dict:
    """An imported NS1c2 entity record with its run-relative references re-scoped to the NS1c2 run."""
    out = copy.deepcopy(rec)

    def fix(ref: str) -> str:
        return f"{scheme}:{ref.split(':', 1)[1]}" if ref.startswith("run:") else ref
    for look in out["looks"]:
        look["calibration"], look["state"] = fix(look["calibration"]), fix(look["state"])
    for key in ("evidence", "map", "probe"):
        if out.get(key) and out[key].get("path"):
            out[key]["path"] = fix(out[key]["path"])
    return out


def record_refs(rec: dict) -> list[str]:
    refs = [x for look in rec["looks"] for x in (look["calibration"], look["state"])]
    refs += [rec["evidence"]["path"], rec["map"]["path"]]
    if rec.get("probe"):
        refs.append(rec["probe"]["path"])
    return refs


# ------------------------------------------------------------------ the entity context (accepted, with the NS1e resolver)
def context_from_record(rec: dict, run: Path):
    """``ns1c2_core.context_from_record`` statement by statement, with the NS1e reference resolver."""
    from fov3d.control import object_policy
    from fov3d.experiments.classroom_oracle import controller01 as c01
    k = int(rec["temporary_entity_id"])
    ctx = c01.LocalPolicyContext(k)
    ev = C2.load_npz(resolve(rec["evidence"]["path"], run))
    for name, v in ev.items():
        arr = getattr(ctx.evidence, name)
        if arr.shape != v.shape:
            raise RuntimeError(f"entity {k}: the saved evidence chart shape differs")
        arr[...] = v
    cal = st = None
    for look in rec["looks"]:
        cal = json.loads(resolve(look["calibration"], run).read_text())
        st = C2.load_state(resolve(look["state"], run))
        ctx.history.append(object_policy.history_entry(
            calibration=cal, instance_L=st["ids_left"], raw_support_L=st["raw_support_L"], instance_R=st["ids_right"],
            raw_support_R=st["raw_support_R"], target_object_id=k))
    ctx.visited.extend((float(a), float(b)) for a, b in rec["visited"])
    ctx.gaze = (float(rec["current_local_gaze"][0]), float(rec["current_local_gaze"][1]))
    ctx.calibration, ctx.state = cal, st
    if len(ctx.history) != int(rec["own_looks"]) or len(ctx.visited) != int(rec["own_looks"]):
        raise RuntimeError(f"entity {k}: own looks {rec['own_looks']} != history {len(ctx.history)} / visited "
                           f"{len(ctx.visited)}")
    return ctx


def contexts_equal(a, b) -> list[str]:
    """Exact equality of two LocalPolicyContexts (evidence arrays, history entries, visited, gaze, calibration, state)."""
    probs = []
    ea, eb = B.evidence_arrays(a), B.evidence_arrays(b)
    if set(ea) != set(eb) or any(not np.array_equal(ea[k], eb[k]) for k in ea):
        probs.append("evidence")
    if len(a.history) != len(b.history):
        probs.append("history length")
    else:
        for i, (ha, hb) in enumerate(zip(a.history, b.history)):
            if set(ha) != set(hb):
                probs.append(f"history[{i}] keys")
                continue
            for key in ha:
                va, vb = ha[key], hb[key]
                if isinstance(va, np.ndarray) or isinstance(vb, np.ndarray):
                    if not np.array_equal(np.asarray(va), np.asarray(vb)):
                        probs.append(f"history[{i}].{key}")
                elif jsonable(va) != jsonable(vb):
                    probs.append(f"history[{i}].{key}")
    if list(a.visited) != list(b.visited) or tuple(a.gaze) != tuple(b.gaze):
        probs.append("visited / gaze")
    if jsonable(a.calibration) != jsonable(b.calibration):
        probs.append("calibration")
    if set(a.state) != set(b.state) or any(not np.array_equal(a.state[k], b.state[k]) for k in a.state):
        probs.append("state")
    if int(a.target_id) != int(b.target_id):
        probs.append("target id")
    return probs


# ------------------------------------------------------------------ M2: the live controller geometry (section 8)
def map_xyz(rec: dict, run: Path) -> np.ndarray:
    m = C2.load_npz(resolve(rec["map"]["path"], run))
    return np.asarray(m["xyz_h"], np.float64)


def geometry_m2(rec: dict, run: Path, ledger) -> np.ndarray:
    i = int(rec["temporary_entity_id"])
    return effective_target_geometry(map_xyz(rec, run), ledger.snapshot(i).xyz_h)


def revision_m2(rec: dict, ledger) -> list[int]:
    i = int(rec["temporary_entity_id"])
    return [int(rec["own_looks"]), int(ledger.measured_points.get(i, 0))]


def memory_counts(rec: dict, ledger) -> dict:
    i = int(rec["temporary_entity_id"])
    p = ledger.provenance(i)
    surf = int(rec["map"]["surfels"])
    return {"map_surfels": surf, "memory_points": p["points"], "own_memory_points": p["own_target_points"],
            "cross_memory_points": p["cross_target_points"], "effective_points": surf + p["points"],
            "by_source_target": p["by_source_target"]}


def probe_m2(rec: dict, chart: dict, run: Path, ledger, label: str) -> dict:
    """The accepted NORMAL probe (FSG6f -> Cyclopean under the frame adapter, NO gate) on the M2 effective geometry."""
    ctx = context_from_record(rec, run)
    r = np.asarray(chart["R_HC"], np.float64)
    g = geometry_m2(rec, run, ledger)
    out = C2.probe_normal_ctx(ctx, CH.to_chart(g, r), r, np.asarray(chart["g0_H0"], np.float64), label)
    out["mode"] = "M2"
    out["geometry_h0_points"] = int(len(g))
    return out


def probe_policy_part(out: dict) -> dict:
    """What NORMAL service depends on: the ProbeResult's action (local gaze, source) and its detail summary."""
    p = out.get("proposal")
    return {"action": None if p is None else {"gaze_deg": [float(v) for v in p["local_gaze_deg"]], "source": p["source"]},
            "detail": jsonable(dict(out["summary"]))}


def cached_policy_part(probe_json: dict) -> dict:
    """The same part of a serialized ProbeResult (``ns1c2_phase.probe_to_json``), without NS1d/NS1e bookkeeping keys."""
    a = probe_json["action"]
    det = {k: v for k, v in (probe_json.get("detail") or {}).items() if k not in ("probe_path", "revision")}
    return {"action": None if a is None else {"gaze_deg": [float(v) for v in a["gaze_deg"]], "source": a["source"]},
            "detail": jsonable(det)}


# ------------------------------------------------------------------ the RESIDUE gate adapter (section 12)
def residue_gate_m2(rec: dict, run: Path, chart: dict, cached_probe: dict, proposal, head_r_wh, head_origin_w, ledger,
                    label: str = "residue gate") -> tuple[Any, dict]:
    """``ns1c2_core.residue_gate`` with the M2 effective geometry in chart C_i in place of the map: the context is rebuilt,
    the probe recomputed (same revision -> same decision) and required equal to the cached probe; the accepted
    ``final_look_gate_v1`` then receives the UNCHANGED cached ProbeResult and the recomputed FSG6f decision, under the
    accepted frame adapter with the real fixed-head North-Star sensor for P3.  Call only with the gate guard in RESIDUE."""
    from fov3d.control import controller02 as c2
    from fov3d.experiments.classroom_oracle import controller01 as c01, controller02 as x2
    ctx = context_from_record(rec, run)
    r = np.asarray(chart["R_HC"], np.float64)
    geometry_c = CH.to_chart(geometry_m2(rec, run, ledger), r)
    with CH.PolicyChartAdapter(r, CH.north_star_sensor, label) as ad:
        result, decisions = c01.probe_local_policy(ctx, geometry_c)
        again = {"state": result.state.value, "summary": jsonable(dict(result.detail)), "decisions": jsonable(decisions)}
        diffs = (B.compare(cached_probe["decisions"], again["decisions"], 0.0, "decisions")
                 + B.compare(cached_probe["summary"], again["summary"], 0.0, "summary")
                 + B.compare(cached_probe["state"], again["state"], 0.0, "state"))
        same_action = (result.action is not None and proposal.action is not None
                       and tuple(result.action.gaze_yaw_pitch_deg) == tuple(proposal.action.gaze_yaw_pitch_deg)
                       and result.action.source == proposal.action.source)
        if diffs or not same_action:
            raise RuntimeError(f"the residue proposal is not the unchanged cached proposal: {diffs[:3]}")
        verdict = x2.final_look_gate_v1(
            proposal=proposal, decision=decisions.get("fsg6f_decision"), geometry=geometry_c, gaze=ctx.gaze,
            calibration=ctx.calibration, state=ctx.state, history=ctx.history, visited=list(ctx.visited),
            profile=SP.PROFILE, head_r_wh=head_r_wh, head_origin_w=head_origin_w, target_id=int(ctx.target_id))
    yw, pw, _d = CH.local_to_world_gaze(*map(float, proposal.action.gaze_yaw_pitch_deg), r)
    detail = {"admissible": bool(verdict.admissible), "reason": verdict.reason, "detail": jsonable(dict(verdict.detail)),
              "adapter": ad.record(), "recomputed_probe_equal": True, "geometry": "M2 effective geometry in chart C_i",
              "effective_points": int(len(geometry_c)), "proposal": {
                  "local_gaze_deg": [float(v) for v in proposal.action.gaze_yaw_pitch_deg],
                  "source": proposal.action.source, "world_gaze_deg": [yw, pw]},
              "sensor": "ns1b_chart.north_star_sensor (real fixed-head H0 sensor at the mapped world gaze)"}
    return c2.FinalProbeDecision(bool(verdict.admissible), verdict.reason, {"record": detail}), detail


# ------------------------------------------------------------------ the derived hard cap (section 20)
def derive_cap(machine) -> dict:
    from fov3d.control import controller02 as c2
    order = list(machine.order)
    budget = int(machine.budget)
    fix = {int(i): int(machine.fixations[i]) for i in order}
    normal = all(machine.disposition[i][0] is c2.Disposition.NORMAL for i in order)
    initialized = sorted(machine.initialized) == sorted(order)
    within = all(0 <= f <= budget for f in fix.values())
    remaining = {str(i): budget - fix[i] for i in order}
    max_new = sum(budget - fix[i] for i in order) + len(order)
    return {"budget": budget, "fixations": {str(i): fix[i] for i in order}, "normal_remaining": remaining,
            "normal_remaining_total": sum(remaining.values()), "final_residue_max": len(order),
            "max_new_physical_actions": max_new, "start_global_step": int(machine.step),
            "absolute_action_cap": int(machine.step) + max_new,
            "formula": "MAX_NEW = sum_i (budget - f_i) + |coherent|; ABSOLUTE = start global step + MAX_NEW",
            "assumptions": {"all_normal": normal, "all_initialized": initialized, "fixations_within_budget": within},
            "assumptions_ok": bool(normal and initialized and within)}


# ------------------------------------------------------------------ the target-only patch (section 15)
def target_patch(xyz_epi, valid, ids, rgb, target: int, step: int) -> dict:
    keep = np.asarray(valid, bool) & (np.asarray(ids) == int(target))
    return {"frame": SP.FUSION_FRAME, "patch_id": SP.patch_id(step),
            "xyz_h": np.asarray(xyz_epi, np.float64)[keep], "rgb": np.asarray(rgb, np.float64)[keep],
            "instance_id": np.asarray(ids, np.int32)[keep], "points": int(keep.sum())}


# ------------------------------------------------------------------ the memory ledger (section 16)
def ledger_digest(summary: dict) -> str:
    return canonical_digest(summary)


def rebuild_ledger(events: list[dict], run: Path, load=None) -> Any:
    """The accepted ledger rebuilt from the frozen patches in event order; each patch must equal its recorded hash and
    reproduce its recorded additions (the read-only replay of every completed memory event)."""
    load = load or C2.load_npz
    ledger = K.MemoryLedger()
    for i, ev in enumerate(events):
        if int(ev["event"]) != i:
            raise LedgerMismatch(f"memory event list out of order at position {i}: {ev['event']}")
        path = resolve(ev["patch"], run)
        if sha256_file(path) != ev["patch_sha256"]:
            raise LedgerMismatch(f"memory event {i}: the patch is not the frozen one")
        adds = ledger.append(int(ev["event"]), ev["observation_key"], load(path), int(ev["target"]))
        if {str(k): int(v) for k, v in sorted(adds.items())} != {str(k): int(v) for k, v in ev["additions"].items()}:
            raise LedgerMismatch(f"memory event {i}: additions differ from the record")
    return ledger


def map_digest(entities: dict) -> str:
    lines = "".join(f"{int(k)} {entities[k]['map']['sha256']}\n" for k in sorted(entities, key=int))
    return sha256_bytes(lines.encode())


# ------------------------------------------------------------------ checkpointing (section 21)
def classify_step(sd: Path) -> dict:
    """Which stages of a step directory are complete; a terminal decision is its own class; anything else that is not a
    complete prefix of the declared order is ambiguous."""
    sd = Path(sd)
    if not sd.exists():
        return {"exists": False, "complete": False, "terminal": False, "stages_done": [], "next_stage": SP.STEP[0]}
    dec = sd / "plan/decision.json"
    if dec.is_file():
        try:
            kind = json.loads(dec.read_text()).get("kind")
        except ValueError:
            kind = None
        if kind in ("closed", "cap"):
            return {"exists": True, "complete": False, "terminal": True, "kind": kind, "stages_done": ["schedule"],
                    "next_stage": None}
    done = [s for s in SP.STEP if (sd / SP.STAGE_OUTPUT[s]).is_file()]
    prefix = list(SP.STEP[:len(done)])
    if done != prefix:
        raise StepAmbiguous(f"{sd}: completed stages {done} are not a prefix of the declared order")
    complete = len(done) == len(SP.STEP)
    return {"exists": True, "complete": complete, "terminal": False, "stages_done": done,
            "next_stage": None if complete else SP.STEP[len(done)]}


# ------------------------------------------------------------------ terminal semantics (sections 23, 24)
def control_outcome(terminal: dict) -> dict:
    """Outcome 1Q / 1R (honest closure), 2 (cap)."""
    if terminal.get("kind") == "cap" or terminal.get("type") == "CapReached":
        return {"outcome": "2", "scope": SP.SCOPE_CAP, "statement": "the derived hard cap was reached before closure: "
                "an incomplete coherent loop"}
    clo = terminal["closure"] if "closure" in terminal else terminal
    residual = list(clo.get("residual") or [])
    seed = list(clo.get("seed_residues") or [])
    q = "1Q" if not residual and not seed else "1R"
    return {"outcome": q, "scope": SP.SCOPE_CLOSED, "generic_terminal": "scene_closed",
            "statement": ("honest coherent-subset closure; all ten entities locally QUIET" if q == "1Q" else
                          "honest coherent-subset closure with finalized residual ACTIONABLE entities")}


def terminal_breakdown(closure: dict, statuses: dict) -> dict:
    """The closure split as the contract requires (section 23)."""
    rows = {"quiet_normal": [], "finalized_quiet_before_final_probe": [], "finalized_final_probe_rejected": [],
            "finalized_final_probe_executed_still_actionable": [], "finalized_final_probe_executed_quiet": [],
            "other_residual": []}
    for i, st in sorted(statuses.items(), key=lambda t: int(t[0])):
        local, disp, why = st["local"], st["disposition"], st["reason"]
        if disp == "NORMAL" and local == "QUIET":
            rows["quiet_normal"].append(int(i))
        elif disp == "FINALIZED" and why == "quiet_before_final_probe":
            rows["finalized_quiet_before_final_probe"].append(int(i))
        elif disp == "FINALIZED" and why == "final_probe_rejected":
            rows["finalized_final_probe_rejected"].append(int(i))
        elif disp == "FINALIZED" and why == "final_probe_executed":
            key = "finalized_final_probe_executed_quiet" if local == "QUIET" else \
                "finalized_final_probe_executed_still_actionable"
            rows[key].append(int(i))
        else:
            rows["other_residual"].append(int(i))
    rows["global_quiescence_warranted"] = all(st["local"] == "QUIET" for st in statuses.values())
    return rows


# ------------------------------------------------------------------ evaluation helpers (section 26)
def head_points(position_w: np.ndarray, r_wh, o_w) -> np.ndarray:
    """World -> canonical H0: p_H0 = (p_w - o_w) R_wh (fsg_geometry.world_to_head)."""
    return (np.asarray(position_w, np.float64) - np.asarray(o_w, np.float64)) @ np.asarray(r_wh, np.float64)


def reference_mask(instance: np.ndarray, position_w: np.ndarray, i: int) -> np.ndarray:
    p = np.asarray(position_w, np.float64)
    return (np.asarray(instance) == int(i)) & np.isfinite(p).all(axis=-1) & ~np.all(p == 0.0, axis=-1)


def weighted(mask: np.ndarray, weights_row: np.ndarray) -> float:
    rows = np.nonzero(mask)[0]
    return float(np.bincount(rows, minlength=len(weights_row)).astype(np.float64) @ np.asarray(weights_row, np.float64))


# ------------------------------------------------------------------ PLY export (section 28)
def ply_bytes(groups: list[tuple[int, np.ndarray, np.ndarray | None]], comment: str) -> bytes:
    """Binary little-endian PLY: x y z (float32), red green blue (uchar), entity_id (int32); groups in the given order."""
    rows = []
    for eid, xyz, rgb in groups:
        xyz = np.asarray(xyz, np.float32).reshape(-1, 3)
        if rgb is None or len(rgb) != len(xyz):
            col = np.zeros((len(xyz), 3), np.uint8)
        else:
            c = np.asarray(rgb, np.float64).reshape(-1, 3)
            c = c * 255.0 if c.size and np.nanmax(c) <= 1.5 else c
            col = np.clip(np.rint(np.nan_to_num(c)), 0, 255).astype(np.uint8)
        rows.append((int(eid), xyz, col))
    n = sum(len(x) for _e, x, _c in rows)
    head = ("ply\nformat binary_little_endian 1.0\n" + "".join(f"comment {line}\n" for line in comment.split("\n"))
            + f"element vertex {n}\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\n"
              "property uchar green\nproperty uchar blue\nproperty int entity_id\nend_header\n").encode("ascii")
    dt = np.dtype([("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("r", "u1"), ("g", "u1"), ("b", "u1"), ("e", "<i4")])
    parts = [head]
    for eid, xyz, col in rows:
        a = np.zeros(len(xyz), dt)
        a["x"], a["y"], a["z"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
        a["r"], a["g"], a["b"] = col[:, 0], col[:, 1], col[:, 2]
        a["e"] = eid
        parts.append(a.tobytes())
    return b"".join(parts)


def ply_read(b: bytes) -> dict:
    """The vertices of a PLY written by ``ply_bytes`` (checker / synthetic use)."""
    end = b.index(b"end_header\n") + len(b"end_header\n")
    head = b[:end].decode("ascii").split("\n")
    n = int(next(line for line in head if line.startswith("element vertex")).split()[-1])
    dt = np.dtype([("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("r", "u1"), ("g", "u1"), ("b", "u1"), ("e", "<i4")])
    a = np.frombuffer(b[end:], dt, count=n)
    if len(b) - end != n * dt.itemsize:
        raise ValueError("PLY body size mismatch")
    return {"xyz": np.stack([a["x"], a["y"], a["z"]], 1), "entity_id": a["e"].copy(), "comments":
            [line[8:] for line in head if line.startswith("comment ")]}


def record_bytes(d: dict) -> bytes:
    return (json.dumps(jsonable(d), indent=1, sort_keys=True, allow_nan=False) + "\n").encode()
