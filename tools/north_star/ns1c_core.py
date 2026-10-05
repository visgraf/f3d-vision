"""North Star-1c: the pure functions of the first scene switch (host side; no Blender).

Contract: docs/north-star/ns1c-coherent-first-scene-switch-contract.md, sections 5-20.

- the COHERENT_SEED_SET rule (section 5) over the frozen NS1a seed set;
- one fixed policy chart per entity (section 7; the accepted NS1b construction);
- entity context records: the LocalPolicyContext rebuilt from saved looks, evidence and map (section 9);
- the service-state conversion with the accepted watchdog (section 12) and the summaries the scheduler may see;
- the accepted scheduler, called unchanged (section 13), with the accepted revision / cache semantics;
- the canonical stop, the global cap and the terminal labels (sections 18-19);
- the target-only patch of a step (section 16).

No object name and no catalog ever enters these functions.  The accepted policy, gate, adapter and fusion are reached
only through the accepted NS1b modules (``ns1b_chart``, ``ns1b_core``), unchanged.
"""
from __future__ import annotations

import hashlib
import json
import math
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
import ns1b_core as B  # noqa: E402  (accepted NS1b probe / context / fusion functions, read-only)
import ns1c_spec as SP  # noqa: E402


class EligibilityRefused(RuntimeError):
    """A name / catalog field reached the eligibility rule, or a required field is missing."""


class SchedulerInputRefused(RuntimeError):
    """The scheduler input is not exactly one summary per coherent entity (e.g. a deferred id was inserted)."""


class ProcessRefused(RuntimeError):
    """A process rule refuses the request (a second-target action after the stop, a step beyond the cap)."""


def jsonable(x: Any) -> Any:
    return B.jsonable(x)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ------------------------------------------------------------------ section 5: the coherent seed set
def derive_coherent_set(seed_set: dict) -> dict:
    """COHERENT_SEED_SET = initialized AND contributing_patches == 1; deferred = initialized AND > 1 patches.

    Reads only ``SP.ELIGIBILITY_FIELDS`` (+ ``SP.CONTEXT_FIELDS`` for the chart / map checks recorded with each row);
    any name / catalog field anywhere in the input is refused."""
    if B._has_name(seed_set):
        raise EligibilityRefused("a name or catalog field reached the eligibility rule")
    coherent, deferred, outside = [], [], []
    for e in seed_set["entities"]:
        missing = [f for f in SP.ELIGIBILITY_FIELDS + SP.CONTEXT_FIELDS if f not in e]
        if missing:
            raise EligibilityRefused(f"entity record lacks {missing}")
        k = int(e["temporary_entity_id"])
        row = {"temporary_entity_id": k, "initialized": bool(e["initialized"]),
               "contributing_patches": int(e["contributing_patches"])}
        if not bool(e["initialized"]):
            outside.append({**row, "state": SP.OUTSIDE_STATE})
        elif int(e["contributing_patches"]) == 1:
            coherent.append({**row, "initialized_at_rank": int(e["initialized_at_rank"]),
                             "final_surfels": int(e["final_surfels"])})
        else:
            deferred.append({**row, "initialized_at_rank": int(e["initialized_at_rank"]),
                             "final_surfels": int(e["final_surfels"]), "state": SP.DEFERRED_STATE})
    key = lambda r: r["temporary_entity_id"]  # noqa: E731
    return {"rule": "initialized == true AND contributing_patches == 1 (deferred: initialized AND > 1 patches)",
            "fields_read": list(SP.ELIGIBILITY_FIELDS + SP.CONTEXT_FIELDS),
            "coherent": sorted(coherent, key=key), "deferred": sorted(deferred, key=key),
            "outside": sorted(outside, key=key),
            "coherent_ids": sorted(r["temporary_entity_id"] for r in coherent),
            "deferred_ids": sorted(r["temporary_entity_id"] for r in deferred),
            "outside_ids": sorted(r["temporary_entity_id"] for r in outside)}


# ------------------------------------------------------------------ section 7: charts
def chart_record(entity: int, rank: int, gaze_deg: tuple[float, float]) -> dict:
    """The accepted NS1b chart at the entity's NS1a initialization gaze (raises ``CH.ChartSingular``)."""
    g0 = CH.gaze_direction(*gaze_deg)
    basis = CH.chart_basis(g0)
    r = basis["R_HC"]
    rng = np.random.default_rng(int(entity))
    pts = g0[None] * rng.uniform(1.0, 5.0, (64, 1)) + rng.normal(scale=0.3, size=(64, 3))
    checks = CH.chart_checks(r, g0, pts)
    return {"temporary_entity_id": int(entity), "chart_id": f"C_{int(entity)}", "initialization_rank": int(rank),
            "seed_gaze_H0_deg": [float(gaze_deg[0]), float(gaze_deg[1])], "g0_H0": g0.tolist(), "R_HC": r.tolist(),
            "R_HC_sha256": chart_hash(r), "x_C_in_H0": basis["x_C_in_H0"].tolist(),
            "y_C_in_H0": basis["y_C_in_H0"].tolist(), "z_C_in_H0": basis["z_C_in_H0"].tolist(),
            "projected_baseline_norm": basis["projected_baseline_norm"], "b_dot_g0": basis["b_dot_g0"],
            "leverage": CH.leverage(g0), "chart_up_dot_world_up": float(basis["y_C_in_H0"][1]), "checks": checks,
            "domain_corners_in_H0_deg": [list(CH.local_to_world_gaze(a, b, r)[:2])
                                         for a, b in ((-25, -20), (25, -20), (25, 20), (-25, 20))]}


def chart_hash(r) -> str:
    return sha256_bytes(np.ascontiguousarray(np.asarray(r, np.float64)).tobytes())


# ------------------------------------------------------------------ paths of a context record
def resolve(ref: str, run: Path, ns1a: Path = SP.NS1A_RUN, ns1b: Path = SP.NS1B_RUN) -> Path:
    """'run:rel' / 'ns1a:rel' / 'ns1b:rel' -> a path (keeps records relocatable for corruption mirrors)."""
    scheme, rel = ref.split(":", 1)
    return {"run": Path(run), "ns1a": Path(ns1a), "ns1b": Path(ns1b)}[scheme] / rel


def load_npz(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def load_state(path: Path) -> dict:
    z = load_npz(path)
    return {k: z[k] for k in ("ids_left", "ids_right", "raw_support_L", "raw_support_R")}


def load_map(path: Path):
    from fov3d.reconstruction import surface_map as SM
    m = load_npz(path)
    return SM.SurfaceMap(np.asarray(m["xyz_h"], np.float64).copy(), np.asarray(m["rgb"], np.float64).copy(),
                         m["instance_id"].copy(), m["support_count"].copy(), m["provenance_mask"].copy(),
                         [str(p) for p in m["patch_ids"]])


def context_from_record(rec: dict, run: Path, ns1a: Path = SP.NS1A_RUN, ns1b: Path = SP.NS1B_RUN):
    """The accepted LocalPolicyContext of one entity, rebuilt from its saved looks, evidence and visited gazes."""
    from fov3d.control import object_policy
    from fov3d.experiments.classroom_oracle import controller01 as c01
    k = int(rec["temporary_entity_id"])
    ctx = c01.LocalPolicyContext(k)
    ev = load_npz(resolve(rec["evidence"]["path"], run, ns1a, ns1b))
    for name, v in ev.items():
        arr = getattr(ctx.evidence, name)
        if arr.shape != v.shape:
            raise RuntimeError(f"entity {k}: the saved evidence chart shape differs")
        arr[...] = v
    cal = st = None
    for look in rec["looks"]:
        cal = json.loads(resolve(look["calibration"], run, ns1a, ns1b).read_text())
        st = load_state(resolve(look["state"], run, ns1a, ns1b))
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


def revision(rec: dict) -> list[int]:
    """The accepted revision semantics: (own looks, effective geometry size) -- NS1c's geometry is the H0 map."""
    return [int(rec["own_looks"]), int(rec["map"]["surfels"])]


# ------------------------------------------------------------------ section 11: the probe of one entity
def probe_entity(rec: dict, run: Path, chart: dict, head_r_wh, head_origin_w, label: str,
                 ns1a: Path = SP.NS1A_RUN, ns1b: Path = SP.NS1B_RUN) -> dict:
    """The accepted FSG6f -> Cyclopean probe and the v1 gate (``ns1b_core.probe``) for one entity, under its chart."""
    ctx = context_from_record(rec, run, ns1a, ns1b)
    r = np.asarray(chart["R_HC"], np.float64)
    m = load_npz(resolve(rec["map"]["path"], run, ns1a, ns1b))
    map_c = CH.to_chart(np.asarray(m["xyz_h"], np.float64), r)
    out = B.probe(ctx, map_c, r, CH.north_star_sensor, head_r_wh, head_origin_w, SP.PROFILE,
                  np.asarray(chart["g0_H0"], np.float64), label)
    return out


def rebuild_context(rec: dict, run: Path, r_hc, q=None, ns1a: Path = SP.NS1A_RUN, ns1b: Path = SP.NS1B_RUN):
    """The context recomputed from its looks alone (Controller-01 ``observe`` order; evidence through P2 under the
    chart), optionally for the scene rigidly rotated about the physical baseline by ``q`` (every camera R_hc -> q R_hc).
    It does not read the saved evidence: equality with the saved evidence is a recomputation, not a copy."""
    from fov3d.control import object_policy
    from fov3d.experiments.classroom_oracle import controller01 as c01, epistemic
    k = int(rec["temporary_entity_id"])
    ctx = c01.LocalPolicyContext(k)
    cal = st = None
    for look in rec["looks"]:
        cal = json.loads(resolve(look["calibration"], run, ns1a, ns1b).read_text())
        if q is not None:
            cal = CH.rotate_calibration(cal, q)
        z = load_npz(resolve(look["state"], run, ns1a, ns1b))
        st = {key: z[key] for key in ("ids_left", "ids_right", "raw_support_L", "raw_support_R")}
        with CH.PolicyChartAdapter(np.asarray(r_hc, np.float64), label=f"rebuild evidence of entity {k}"):
            epistemic.add_observation(ctx.evidence, cal, st["ids_left"], st["raw_support_L"], st["ids_right"],
                                      st["raw_support_R"], np.asarray(z["matcher_valid"], bool), k)
        ctx.history.append(object_policy.history_entry(
            calibration=cal, instance_L=st["ids_left"], raw_support_L=st["raw_support_L"], instance_R=st["ids_right"],
            raw_support_R=st["raw_support_R"], target_object_id=k))
    ctx.visited.extend((float(a), float(b)) for a, b in rec["visited"])
    ctx.gaze = (float(rec["current_local_gaze"][0]), float(rec["current_local_gaze"][1]))
    ctx.calibration, ctx.state = cal, st
    return ctx


def evidence_arrays(ctx) -> dict:
    return B.evidence_arrays(ctx)


def rotation_invariance(rec: dict, run: Path, chart: dict, out: dict, head_r_wh, head_origin_w,
                        betas=SP.PROBE_ROTATIONS_DEG, ns1a: Path = SP.NS1A_RUN, ns1b: Path = SP.NS1B_RUN) -> list[dict]:
    """The NS1b in-probe invariance for one entity: its context rigidly rotated about the physical baseline.

    Every look's calibration and the map are rotated (an exact fixed-head symmetry), the evidence is recomputed through
    P2 under the rotated chart (it must equal the saved one), the chart is rebuilt from the rotated seed; the local
    decision must be identical (the accepted comparison rules for float ties and exact 25-mm voxel boundaries)."""
    r = np.asarray(chart["R_HC"], np.float64)
    g0 = np.asarray(chart["g0_H0"], np.float64)
    m = load_npz(resolve(rec["map"]["path"], run, ns1a, ns1b))
    map_h0 = np.asarray(m["xyz_h"], np.float64)
    map_c = CH.to_chart(map_h0, r)
    saved = load_npz(resolve(rec["evidence"]["path"], run, ns1a, ns1b))
    rows = []
    for beta in betas:
        q = CH.rot_x(beta)
        rq = CH.chart_basis(q @ g0)["R_HC"]
        ctx = rebuild_context(rec, run, rq, q, ns1a, ns1b)
        ev = evidence_arrays(ctx)
        ev_equal = set(ev) == set(saved) and all(np.array_equal(ev[key], saved[key]) for key in ev)
        oq = B.probe(ctx, CH.to_chart(map_h0 @ q.T, rq), rq, CH.north_star_sensor, head_r_wh, head_origin_w,
                     SP.PROFILE, q @ g0, f"invariance {beta} entity {rec['temporary_entity_id']}")
        diffs, flip = B.explain_voxel_flip(B.probe_comparison(out, oq), map_c)
        row = {"beta_deg": beta, "chart_equals_Q_R_HC": float(np.abs(rq - q @ r).max()), "evidence_equal": ev_equal,
               "differences": diffs, "voxel_boundary_flip": flip,
               "tie_inversions": B.inversions((out["decisions"].get("fsg6f_decision") or {}).get("candidates", []),
                                              (oq["decisions"].get("fsg6f_decision") or {}).get("candidates", []))}
        if out["proposal"] is not None and oq["proposal"] is not None:
            row["world_proposal_error"] = float(np.abs(np.asarray(oq["proposal"]["d_H0"])
                                                       - q @ np.asarray(out["proposal"]["d_H0"])).max())
        row["pass"] = bool(not diffs and ev_equal and row["chart_equals_Q_R_HC"] <= 1e-12
                           and row.get("world_proposal_error", 0.0) <= 1e-12
                           and (out["proposal"] is None) == (oq["proposal"] is None))
        rows.append(row)
    return rows


# ------------------------------------------------------------------ section 12: service states
def gated_state(probe_out: dict) -> str:
    """ACTIONABLE iff the probe carries a proposal the v1 gate admits; QUIET otherwise."""
    p = probe_out.get("proposal")
    return SP.SERVICE_ACTIONABLE if (p is not None and bool(probe_out["gate"]["admissible"])) else SP.SERVICE_QUIET


def service(probe_out: dict, own_looks: int, watchdog: int, blocked_before: str | None) -> dict:
    """The accepted ``run_control_loop.service`` semantics over the gated probe: BLOCKED is sticky; an ACTIONABLE
    entity whose own looks reached the watchdog becomes BLOCKED:watchdog."""
    if blocked_before is not None:
        return {"state": SP.SERVICE_BLOCKED, "blocked_reason": blocked_before, "label": f"BLOCKED:{blocked_before}"}
    st = gated_state(probe_out)
    if st == SP.SERVICE_ACTIONABLE and int(own_looks) >= int(watchdog):
        return {"state": SP.SERVICE_BLOCKED, "blocked_reason": "watchdog", "label": "BLOCKED:watchdog"}
    return {"state": st, "blocked_reason": None, "label": st}


def summaries(entities: dict, coherent_ids: list[int]):
    """Exactly one accepted ObjectSummary per coherent entity (refuses any other id, e.g. a deferred one)."""
    from fov3d.control import integrated as ic
    ids = sorted(int(k) for k in entities)
    if ids != sorted(int(i) for i in coherent_ids):
        raise SchedulerInputRefused(f"scheduler input ids {ids} != COHERENT_SEED_SET {sorted(coherent_ids)}")
    out = []
    for k in ids:
        s = entities[str(k)]["service"] if str(k) in entities else entities[k]["service"]
        out.append(ic.ObjectSummary(int(k), ic.ServiceState(s["state"]), s["blocked_reason"]))
    return out


def schedule(current: int | None, rows) -> dict:
    """The accepted ``fov3d.control.integrated.schedule``, called unchanged; its decision as a record."""
    from fov3d.control import integrated as ic
    d = ic.schedule(current, rows)
    rec = {"kind": d.kind, "target_id": d.target_id, "reason": d.reason, "current_before": current,
           "summaries": [[int(s.instance_id), s.label] for s in rows]}
    if d.kind == "terminal":
        t = d.terminal
        name = type(t).__name__
        rec["terminal"] = {"type": name, "reason": getattr(t, "reason", None),
                           "blocked": [list(b) for b in getattr(t, "blocked", ())],
                           "label": SP.TERMINAL_LABELS[name]}
    return rec


# ------------------------------------------------------------------ section 18: stop and cap
def stop_event(target: int, fusion_action: str | None) -> bool:
    """The canonical stop: a successful physical action (through the fusion stage) on a target other than 172."""
    return int(target) != SP.CONTINUING and fusion_action in ("FUSED", "RETAINED_NOT_FUSED")


def require_not_stopped(scene: dict) -> None:
    if scene.get("stopped"):
        raise ProcessRefused(f"the canonical stop is reached (first cross-entity action at step "
                             f"{scene['stop']['global_step']}); no further action is scheduled")


def require_under_cap(executed: int, cap: int) -> None:
    if int(executed) >= int(cap):
        raise ProcessRefused(f"the global safety cap is reached: {executed} new physical actions >= cap {cap}")


def terminal_label(name: str) -> str:
    """The NS1c label of a terminal scheduler decision over the coherent subset (never the full-scene marker)."""
    lab = SP.TERMINAL_LABELS[name]
    if lab == SP.FORBIDDEN_MARKER:
        raise AssertionError("NS1c never closes the scene")
    return lab


# ------------------------------------------------------------------ section 14: the world gaze of a proposal
def plan_action(proposal: dict, chart: dict, head_r_wh, head_origin_w) -> dict:
    """Local C_i gaze -> H0 world gaze (round trip), the planned real-sensor calibration and its physical test."""
    import ns1a_core
    r = np.asarray(chart["R_HC"], np.float64)
    yc, pc = (float(v) for v in proposal["local_gaze_deg"])
    yw, pw, d = CH.local_to_world_gaze(yc, pc, r)
    back = CH.world_to_local_gaze(yw, pw, r)
    rt = max(abs(back[0] - yc), abs(back[1] - pc))
    planned = ns1a_core.planned_calibration(yw, pw, head_r_wh, head_origin_w)
    test = B.physical_calibration_test(planned, (yc, pc), r, head_r_wh, head_origin_w)
    g0 = np.asarray(chart["g0_H0"], np.float64)
    return {"local_gaze_deg": [yc, pc], "world_gaze_deg": [yw, pw], "d_H0": d.tolist(),
            "roundtrip_local_gaze_deg": list(back), "roundtrip_error_deg": rt, "leverage": CH.leverage(d),
            "angle_from_seed_deg": math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(g0, d)))))),
            "planned_calibration": planned, "planned_calibration_bytes": ns1a_core.calibration_bytes(planned),
            "physical_calibration_test": test}


# ------------------------------------------------------------------ section 16: the target-only patch
def target_patch(xyz_epi, valid, ids, rgb, target: int, step: int) -> dict:
    keep = np.asarray(valid, bool) & (np.asarray(ids) == int(target))
    return {"frame": SP.FUSION_FRAME, "patch_id": SP.patch_id(step),
            "xyz_h": np.asarray(xyz_epi, np.float64)[keep], "rgb": np.asarray(rgb, np.float64)[keep],
            "instance_id": np.asarray(ids, np.int32)[keep], "points": int(keep.sum())}


def map_arrays(m) -> dict:
    return B.map_arrays(m)


def maps_equal(a: dict, b: dict) -> bool:
    return B.maps_equal(a, b)


# ------------------------------------------------------------------ the scene state
def proposal_summary(probe_out: dict) -> dict | None:
    p = probe_out.get("proposal")
    if p is None:
        return None
    return {k: p[k] for k in ("source", "local_gaze_deg", "world_gaze_deg", "leverage", "angle_from_seed_deg")
            if k in p}


def gate_summary(probe_out: dict) -> dict:
    g = probe_out["gate"]
    c = (g.get("detail") or {}).get("counts") or {}
    return {"admissible": bool(g["admissible"]), "reason": g["reason"],
            "novel_service_count": c.get("novel_service_count"), "support": c.get("support"),
            "in_both_cores": c.get("in_both_cores")}


def fsg6f_summary(probe_out: dict) -> dict:
    s = probe_out["summary"]
    return {"fsg6f": s.get("fsg6f"), "cyclopean": s.get("cyclopean")}


def scene_digest(scene: dict) -> str:
    return sha256_bytes(json.dumps(scene, sort_keys=True, allow_nan=False).encode())


def entity_row(rec: dict) -> dict:
    """One row of the scene service-state table (section 20)."""
    return {"temporary_entity_id": rec["temporary_entity_id"], "initialization_rank": rec["initialization_rank"],
            "chart_id": rec["chart_id"], "chart_sha256": rec["chart_sha256"],
            "current_local_gaze": rec["current_local_gaze"], "own_looks": rec["own_looks"],
            "map_surfels": rec["map"]["surfels"], "service_state": rec["service"]["label"],
            "proposal": rec.get("proposal"), "gate": rec.get("gate"), "revision": rec["revision"],
            "probe_provenance": rec["probe"].get("provenance")}


def reproduce_ns1b_post(mine: dict, accepted_probe: dict) -> list[str]:
    """The exact reproduction of the accepted NS1b post-action probe (tolerance 0)."""
    diffs = B.probe_comparison(accepted_probe, jsonable(mine), 0.0)
    extra = ("planned_calibration_test", "gate_predicted_equals_planned")
    if accepted_probe.get("proposal") is None or mine.get("proposal") is None:
        if (accepted_probe.get("proposal") is None) != (mine.get("proposal") is None):
            diffs.append("proposal presence")
    else:
        diffs += B.compare(accepted_probe["proposal"], jsonable(mine["proposal"]), 0.0, "proposal", skip=extra)
    pa = accepted_probe["gate"]["detail"].get("predicted_calibration")
    pb = jsonable(mine["gate"]["detail"].get("predicted_calibration"))
    if (pa is None) != (pb is None) or (pa is not None and B.compare(pa, pb, 0.0, "predicted_calibration")):
        diffs.append("gate predicted calibration")
    return diffs


def expected_ns1b_post(probe_out: dict) -> dict:
    p = probe_out.get("proposal") or {}
    c = (probe_out["gate"].get("detail") or {}).get("counts") or {}
    got = {"state": gated_state(probe_out), "source": p.get("source"), "local_gaze_deg": p.get("local_gaze_deg"),
           "admissible": bool(probe_out["gate"]["admissible"]), "reason": probe_out["gate"]["reason"],
           "novel_service_count": c.get("novel_service_count")}
    return {"got": got, "expected": dict(SP.NS1B_POST_EXPECTED), "equal": got == dict(SP.NS1B_POST_EXPECTED)}


def own_look_counts(entities: dict) -> dict:
    return {str(k): int(v["own_looks"]) for k, v in entities.items()}


def deferred_rows(elig: dict) -> list[dict]:
    return [{"temporary_entity_id": r["temporary_entity_id"], "contributing_patches": r["contributing_patches"],
             "initialized_at_rank": r["initialized_at_rank"], "final_surfels": r["final_surfels"],
             "state": SP.DEFERRED_STATE, "in_scheduler": False} for r in elig["deferred"]]


def refresh_events(prev: dict, now: dict, step: int, trigger: int) -> list[dict]:
    """The accepted ``run_control_loop.refresh`` events: quiet / natural_reactivation / blocked transitions."""
    ev = []
    for k in sorted(now, key=int):
        a, b = prev[k]["service"], now[k]["service"]
        if a["state"] == SP.SERVICE_QUIET and b["state"] != SP.SERVICE_QUIET:
            ev.append({"event": "natural_reactivation", "object": int(k), "global_step": step, "trigger_target": trigger,
                       "state_after": b["label"]})
        if b["state"] == SP.SERVICE_QUIET and a["state"] != SP.SERVICE_QUIET:
            ev.append({"event": "quiet", "object": int(k), "global_step": step, "trigger_target": trigger,
                       "previous_state": a["label"]})
        if b["state"] == SP.SERVICE_BLOCKED and a["state"] != SP.SERVICE_BLOCKED:
            ev.append({"event": "blocked", "object": int(k), "global_step": step, "trigger_target": trigger,
                       "reason": b["blocked_reason"], "previous_state": a["label"]})
    return ev


def probe_record_file(probe_out: dict) -> bytes:
    return (json.dumps(jsonable(probe_out), indent=1, sort_keys=True, allow_nan=False) + "\n").encode()


def call_counter() -> Callable[[], int]:
    n = [0]

    def inc() -> int:
        n[0] += 1
        return n[0]
    return inc
