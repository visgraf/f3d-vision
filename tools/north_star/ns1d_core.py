"""North Star-1d: the pure functions of the controller-phase cross-target measurement memory (host side; no Blender).

Contract: docs/north-star/ns1d-cross-target-measurement-memory-contract.md, sections 5-17.

- the sparse 256 x 256 spherical memory patch of one physical observation, from frozen products only (section 7);
- ``MemoryLedger``: the accepted ``InstanceMeasurementMemory`` (unchanged) with Controller-01's ``measured_points``
  bookkeeping, and an append-once rule per physical observation (section 8);
- the three read-only geometry / revision modes M0, M1, M2 (section 11);
- the NORMAL probe of an entity under a mode (the accepted NS1c2 probe: no gate);
- the next action of a mode, its comparison with the accepted NS1c2 action (section 15);
- ``drive``: the causal replay driver that stops at the first divergence before consuming the next observation.

No object name and no catalog ever enters these functions.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Callable

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "active_bootstrap", HERE.parent / "natural_bootstrap", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1b_chart as CH  # noqa: E402  (accepted NS1b chart + frame adapter, read-only)
import ns1c2_core as C2  # noqa: E402  (accepted NS1c2 context / probe functions, read-only)
import ns1d_spec as SP  # noqa: E402
from fov3d.reconstruction.measurement_memory import (  # noqa: E402  (accepted, unchanged)
    InstanceMeasurementMemory, effective_target_geometry, valid_patch_measurements)


class PatchRefused(RuntimeError):
    """A product is misaligned, a cell repeats, or a count does not reproduce."""


class LedgerRefused(RuntimeError):
    """A physical observation would enter the memory twice, out of order, or with a non-positive target."""


def jsonable(x: Any) -> Any:
    return C2.jsonable(x)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def array_digest(a: np.ndarray) -> str:
    a = np.ascontiguousarray(a)
    return sha256_bytes(str(a.dtype).encode() + str(a.shape).encode() + a.tobytes())


# ------------------------------------------------------------------ section 7: the sparse spherical memory patch
def memory_patch(prod: dict, geom: dict, ident: dict, size: int = SP.CORE_SIZE) -> tuple[dict, dict]:
    """One raster patch (``xyz_h`` float32 NaN elsewhere, ``instance_id`` int32 0 elsewhere, ``valid``) from the frozen
    truth-stripped correspondence product, its accepted spherical H0 geometry and the identity attached after the
    geometry freeze.  No other input."""
    rows = np.asarray(prod["left_core_row"], np.int64)
    cols = np.asarray(prod["left_core_col"], np.int64)
    for name, d in (("geometry", geom), ("identity", ident)):
        if not (np.array_equal(np.asarray(d["left_core_row"], np.int64), rows)
                and np.array_equal(np.asarray(d["left_core_col"], np.int64), cols)):
            raise PatchRefused(f"the {name} product is not aligned with the correspondence product")
    if rows.size and (rows.min() < 0 or cols.min() < 0 or rows.max() >= size or cols.max() >= size):
        raise PatchRefused("a left-core cell lies outside the core raster")
    cell = rows * size + cols
    if np.unique(cell).size != cell.size:
        raise PatchRefused("a left-core cell carries two correspondences")
    valid_epi = np.asarray(geom["valid_epi"], bool)
    if not np.array_equal(np.asarray(ident["valid"], bool), valid_epi):
        raise PatchRefused("the identity attachment's valid mask differs from the frozen geometry")
    p = np.asarray(geom["P_epi"], np.float64)
    ids = np.asarray(ident["temporary_entity_id"], np.int64)
    if np.any(ids[~valid_epi] != -1) or np.any(ids[valid_epi] < 0):
        raise PatchRefused("the identity attachment is not -1 exactly where the geometry is invalid")
    finite = np.isfinite(p).all(axis=1)
    measured = valid_epi & finite
    keep = measured & (ids > 0)
    xyz = np.full((size, size, 3), np.nan, np.float32)
    xyz[rows[measured], cols[measured]] = p[measured].astype(np.float32)
    inst = np.zeros((size, size), np.int32)
    inst[rows[keep], cols[keep]] = ids[keep].astype(np.int32)
    valid = np.zeros((size, size), bool)
    valid[rows[keep], cols[keep]] = True
    patch = {"xyz_h": xyz, "valid": valid, "instance_id": inst}
    expected = int(keep.sum())
    got, got_ids, _mask = valid_patch_measurements(patch)
    if int(valid.sum()) != expected or len(got) != expected:
        raise PatchRefused(f"valid raster samples {int(valid.sum())} / measured {len(got)} != finite positive-id "
                           f"spherical measurements {expected}")
    u, n = np.unique(ids[keep], return_counts=True)
    info = {"correspondences": int(rows.size), "geometry_valid": int(valid_epi.sum()), "finite": int(measured.sum()),
            "instance_zero": int((measured & (ids == 0)).sum()), "invalid_minus_one": int((ids == -1).sum()),
            "valid_samples": expected, "by_observed_id": {str(int(k)): int(c) for k, c in zip(u, n)},
            "digest": {k: array_digest(v) for k, v in patch.items()}}
    return patch, info


def patch_counts(patch: dict) -> dict[int, int]:
    _xyz, ids, _m = valid_patch_measurements(patch)
    u, n = np.unique(ids, return_counts=True)
    return {int(k): int(c) for k, c in zip(u, n) if int(k) > 0}


def target_subset_equal(patch: dict, prod: dict, target_xyz: np.ndarray, target_ids, valid_epi, target: int) -> bool:
    """The accepted target-only fusion patch (float64, product order) equals the target cells of the memory patch."""
    keep = np.asarray(valid_epi, bool) & (np.asarray(target_ids) == int(target))
    r = np.asarray(prod["left_core_row"], np.int64)[keep]
    c = np.asarray(prod["left_core_col"], np.int64)[keep]
    t = np.asarray(target_xyz, np.float64)
    return bool(t.shape == (int(keep.sum()), 3)
                and np.array_equal(patch["xyz_h"][r, c], t.astype(np.float32))
                and np.all(patch["instance_id"][r, c] == int(target)) and np.all(patch["valid"][r, c]))


# ------------------------------------------------------------------ section 8: the memory with its event ledger
class MemoryLedger:
    """The accepted ``InstanceMeasurementMemory`` (unchanged), fed in Controller-01's ``remember_measurements`` way:
    one append per physical observation, ``source_global_index`` = the memory event index, ``source_active_target_id``
    = the active target, ``measured_points`` accumulated from the additions."""

    def __init__(self) -> None:
        self.memory = InstanceMeasurementMemory()
        self.measured_points: dict[int, int] = {}
        self.events: list[dict] = []

    def append(self, event: int, observation_key: str, patch: dict, target: int) -> dict[int, int]:
        event, target = int(event), int(target)
        if event != len(self.events):
            raise LedgerRefused(f"memory event {event} out of order (next is {len(self.events)})")
        if any(e["observation_key"] == observation_key for e in self.events):
            raise LedgerRefused(f"the physical observation {observation_key} is already in the memory")
        if target <= 0:
            raise LedgerRefused("the active target must be a positive id")
        additions = self.memory.append_patch(patch, source_global_index=event, source_active_target_id=target)
        for k, n in additions.items():
            self.measured_points[int(k)] = self.measured_points.get(int(k), 0) + int(n)
        self.events.append({"event": event, "observation_key": observation_key, "target": target,
                            "additions": {str(k): int(v) for k, v in sorted(additions.items())}})
        return additions

    def snapshot(self, i: int):
        return self.memory.snapshot(int(i))

    def own_xyz(self, i: int) -> np.ndarray:
        s = self.memory.snapshot(int(i))
        return s.xyz_h[s.source_active_target_id == int(i)]

    def own_points(self, i: int) -> int:
        s = self.memory.snapshot(int(i))
        return int((s.source_active_target_id == int(i)).sum())

    def provenance(self, i: int) -> dict:
        s = self.memory.snapshot(int(i))
        src, gi = s.source_active_target_id, s.source_global_index
        return {"points": int(len(s.xyz_h)), "own_target_points": int((src == int(i)).sum()),
                "cross_target_points": int((src != int(i)).sum()),
                "by_source_target": {str(int(k)): int((src == k).sum()) for k in np.unique(src)},
                "by_source_event": {str(int(k)): int((gi == k).sum()) for k in np.unique(gi)}}

    def summary(self) -> dict:
        ids = self.memory.instance_ids()
        snaps = {i: self.memory.snapshot(i) for i in ids}
        return {"events": len(self.events), "instance_ids": list(ids),
                "total_points": int(sum(len(s.xyz_h) for s in snaps.values())),
                "measured_points": {str(k): int(v) for k, v in sorted(self.measured_points.items())},
                "by_id": {str(i): self.provenance(i) for i in ids},
                "snapshot_digest": {str(i): {"xyz_h": array_digest(s.xyz_h),
                                             "source_global_index": array_digest(s.source_global_index),
                                             "source_active_target_id": array_digest(s.source_active_target_id)}
                                    for i, s in snaps.items()}}


# ------------------------------------------------------------------ section 11: the three read-only modes
def map_xyz(rec: dict, run: Path) -> np.ndarray:
    m = C2.load_npz(C2.resolve(rec["map"]["path"], run))
    return np.asarray(m["xyz_h"], np.float64)


def geometry(mode: str, rec: dict, run: Path, ledger: MemoryLedger) -> np.ndarray:
    """The H0 policy geometry of one entity under a mode."""
    i = int(rec["temporary_entity_id"])
    m = map_xyz(rec, run)
    if mode == "M0":
        return m                                                    # the accepted NS1c2 geometry, bit for bit
    if mode == "M1":
        return effective_target_geometry(m, ledger.own_xyz(i))
    if mode == "M2":
        return effective_target_geometry(m, ledger.snapshot(i).xyz_h)
    raise ValueError(f"unknown mode {mode!r}")


def revision(mode: str, rec: dict, ledger: MemoryLedger) -> list[int]:
    i, own = int(rec["temporary_entity_id"]), int(rec["own_looks"])
    if mode == "M0":
        return [own, int(rec["map"]["surfels"])]                     # the accepted NS1c2 revision
    if mode == "M1":
        return [own, ledger.own_points(i)]
    if mode == "M2":
        return [own, int(ledger.measured_points.get(i, 0))]
    raise ValueError(f"unknown mode {mode!r}")


def memory_counts(rec: dict, ledger: MemoryLedger) -> dict:
    i = int(rec["temporary_entity_id"])
    p = ledger.provenance(i)
    return {"map_surfels": int(rec["map"]["surfels"]), "memory_points": p["points"],
            "own_memory_points": p["own_target_points"], "cross_memory_points": p["cross_target_points"],
            "geometry_size": {"M0": int(rec["map"]["surfels"]), "M1": int(rec["map"]["surfels"]) + p["own_target_points"],
                              "M2": int(rec["map"]["surfels"]) + p["points"]}}


def probe(mode: str, rec: dict, chart: dict, run: Path, ledger: MemoryLedger, label: str) -> dict:
    """The accepted NORMAL probe (FSG6f -> Cyclopean under the frame adapter, NO gate) on the mode's geometry."""
    ctx = C2.context_from_record(rec, run)
    r = np.asarray(chart["R_HC"], np.float64)
    g = geometry(mode, rec, run, ledger)
    out = C2.probe_normal_ctx(ctx, CH.to_chart(g, r), r, np.asarray(chart["g0_H0"], np.float64), label)
    out["mode"] = mode
    out["geometry_h0_points"] = int(len(g))
    return out


# ------------------------------------------------------------------ section 15: actions and their comparison
def plan_action(plan: dict, probe_out: dict | None) -> dict:
    """The physical next action of a scene plan (an attend plan with the proposing probe), or the plan's kind."""
    if plan.get("kind") != "attend":
        return {"kind": plan.get("kind")}
    a = plan["action"]
    p = (probe_out or {}).get("proposal") or {}
    return {"kind": "attend", "target": int(a.target_id), "decision": str(plan["decision"]),
            "reason": str(plan["reason"]), "source": a.source,
            "local_gaze_deg": [float(a.gaze_yaw_pitch_deg[0]), float(a.gaze_yaw_pitch_deg[1])],
            "world_gaze_deg": p.get("world_gaze_deg")}


def accepted_action(decision: dict) -> dict:
    """The accepted NS1c2 step action from its recorded decision (``steps/step-KK/plan/decision.json``)."""
    a = decision["action"]
    return {"kind": decision["kind"], "target": int(a["target"]),
            "decision": str(decision["scheduler_decision"]["result"]["reason"]),
            "reason": str(decision["scheduler_reason"]), "source": a["source"],
            "local_gaze_deg": [float(v) for v in a["local_gaze_deg"]],
            "world_gaze_deg": [float(v) for v in a["world_gaze_deg"]]}


LOAD_BEARING = ("kind", "target", "decision", "source", "local_gaze_deg", "world_gaze_deg")


def action_differences(mine: dict, accepted: dict) -> list[str]:
    """Load-bearing differences (exact equality: proposals are the accepted policy's grid values)."""
    out = []
    for f in LOAD_BEARING:
        a, b = mine.get(f), accepted.get(f)
        if f.endswith("gaze_deg") and a is not None and b is not None:
            if [float(v) for v in a] != [float(v) for v in b]:
                out.append(f)
        elif a != b:
            out.append(f)
    return out


def stateless_decision(current: int, ids, probes: dict, fixations: dict, budget: int) -> tuple[dict, list]:
    """A diagnostic mode's decision: the accepted NORMAL classification and deferral rule, then ``schedule_normal``."""
    from fov3d.control import controller02 as c2, integrated as ic
    S, D = ic.ServiceState, c2.Disposition
    statuses = []
    for i in sorted(int(k) for k in ids):
        local = S.ACTIONABLE if probes[i].get("proposal") is not None else S.QUIET
        if local is S.ACTIONABLE and int(fixations[i]) >= int(budget):
            statuses.append(c2.ObjectStatus(i, local, D.DEFERRED, "ordinary_budget"))
        else:
            statuses.append(c2.ObjectStatus(i, local))
    d = c2.schedule_normal(int(current), statuses)
    labels = [[int(s.instance_id), s.label] for s in statuses]
    if d is None:
        return {"kind": "none"}, labels
    p = probes[int(d.target_id)]["proposal"]
    return {"kind": "attend", "target": int(d.target_id), "decision": str(d.reason), "reason": str(d.reason),
            "source": p["source"], "local_gaze_deg": [float(v) for v in p["local_gaze_deg"]],
            "world_gaze_deg": [float(v) for v in p["world_gaze_deg"]]}, labels


# ------------------------------------------------------------------ resuming the accepted adapter
def resume_scene(machine, fixations: dict, *, current: int, bout: int, step: int, probe, revision,
                 quiet_since: int | None = None) -> list[int]:
    """``SceneMachine.resume_initialized`` (accepted, unchanged), then the quiet bookkeeping that ``run_controller02``
    records when an object enters QUIET (``quiet_probe``, ``quiet_since``) for every entity already QUIET at the resume
    point, so that a later natural reactivation is reported with its quiet probe.  Returns the QUIET ids (no event)."""
    from fov3d.control import integrated as ic
    machine.resume_initialized(fixations, current=current, bout=bout, step=step, probe=probe, revision=revision)
    quiet = [i for i in machine.order if machine.statuses[i].local is ic.ServiceState.QUIET]
    for i in quiet:
        machine.quiet_probe[i] = machine.last_probe[i]
        machine.quiet_since[i] = quiet_since
    return quiet


def refuse_gate(i, proposal):
    raise RuntimeError(f"final_look_gate_v1 requested for {i} during the NS1d NORMAL replay")


# ------------------------------------------------------------------ the causal replay driver
def drive(n_steps: int, decide: Callable[[int], dict], accepted: Callable[[int], dict],
          consume: Callable[[int], None], final: Callable[[], None] | None = None) -> dict:
    """For k = 0..n_steps-1: compare the decided next action with the accepted one; at the first load-bearing difference
    STOP before consuming observation k (a counterfactual); otherwise consume it (replay, memory, commit).  After the
    last step ``final`` runs once (the descriptive post-trace state)."""
    consumed = []
    for k in range(int(n_steps)):
        mine, acc = decide(k), accepted(k)
        diffs = action_differences(mine, acc)
        if diffs:
            return {"divergence": True, "step": k, "differences": diffs, "mine": mine, "accepted": acc,
                    "consumed_steps": consumed}
        consume(k)
        consumed.append(k)
    if final is not None:
        final()
    return {"divergence": False, "step": None, "differences": [], "consumed_steps": consumed}


def attribution(m1: dict | None, m2: dict, accepted: dict) -> dict:
    """Outcome 1 vs 3 at the first M2 divergence (contract section 17)."""
    m1_diff = action_differences(m1 or {}, accepted) if m1 is not None else None
    m1_eq_m2 = m1 is not None and not action_differences(m1, m2)
    if m1_diff:
        reading = "Outcome 3 - own-memory effect dominates" if m1_eq_m2 else \
            "Outcome 3 element - M1 already diverges, M2 diverges differently"
    else:
        reading = "Outcome 1 - the divergence needs cross-target evidence (M1 = accepted)"
    return {"m1_differs_from_accepted": bool(m1_diff), "m1_differences": m1_diff, "m1_equals_m2": bool(m1_eq_m2),
            "reading": reading}


def entity_row(rec: dict, mode: str, rev, status, probe_out: dict, provenance: str, counts: dict) -> dict:
    p = probe_out.get("proposal")
    s = probe_out["summary"]
    return {"temporary_entity_id": int(rec["temporary_entity_id"]), "mode": mode, "own_looks": int(rec["own_looks"]),
            "revision": list(rev), "label": status, "probe": provenance,
            "geometry_points": int(probe_out.get("geometry_h0_points", probe_out.get("effective_points", 0))),
            "fsg6f": (s.get("fsg6f") or {}).get("reason"), "cyclopean": (s.get("cyclopean") or {}).get("reason"),
            "cyclopean_eligible": (s.get("cyclopean") or {}).get("eligible_cells"),
            "fsg6f_candidates": (s.get("fsg6f") or {}).get("candidates"),
            "frontier_open": (s.get("fsg6f") or {}).get("frontier_open_count"),
            "source": None if p is None else p["source"],
            "local_gaze_deg": None if p is None else p["local_gaze_deg"],
            "world_gaze_deg": None if p is None else p["world_gaze_deg"], **counts}


def record_bytes(d: dict) -> bytes:
    return (json.dumps(jsonable(d), indent=1, sort_keys=True, allow_nan=False) + "\n").encode()
