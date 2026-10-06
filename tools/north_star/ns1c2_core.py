"""North Star-1c2: the pure functions of the corrected first scene switch (host side; no Blender).

Contract: docs/north-star/ns1c2-controller02-phase-semantics-contract.md, sections 6-19.

- the COHERENT_SEED_SET rule and one fixed policy chart per entity (unchanged from NS1c);
- entity context records: the accepted LocalPolicyContext rebuilt from saved looks, evidence and map;
- the NORMAL probe: the accepted ``controller01.probe_local_policy`` under the accepted NS1b frame adapter, with NO gate
  (the accepted ``ns1b_core.probe`` gates every proposal and is never used here);
- the RESIDUE gate: the accepted ``controller02.final_look_gate_v1`` on the UNCHANGED cached proposal;
- the ProbeResult of a probe record, policy-part comparisons with NS1c's records, the world gaze of a proposal and the
  target-only patch of a step.

No object name and no catalog ever enters these functions.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _p in (HERE, HERE.parent, HERE.parent / "active_bootstrap", HERE.parent / "natural_bootstrap", REPO):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ns1b_chart as CH  # noqa: E402  (accepted NS1b chart + frame adapter, read-only)
import ns1b_core as B  # noqa: E402  (accepted NS1b context / comparison / fusion functions, read-only)
import ns1c2_spec as SP  # noqa: E402


class EligibilityRefused(RuntimeError):
    """A name / catalog field reached the eligibility rule, or a required field is missing."""


class ProcessRefused(RuntimeError):
    """A process rule refuses the request (an action after the stop, a step beyond the cap)."""


def jsonable(x: Any) -> Any:
    return B.jsonable(x)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def vergence_focus():
    from fov3d.experiments.classroom_oracle import controller01 as c01
    return c01.VERGENCE, c01.FOCUS


def budget_live() -> int:
    """The accepted ordinary-service budget (``classroom_oracle.controller02.BUDGET`` = ``controller01.WATCHDOG``)."""
    from fov3d.experiments.classroom_oracle import controller02 as x2
    return int(x2.BUDGET)


# ------------------------------------------------------------------ the coherent seed set (unchanged rule)
def derive_coherent_set(seed_set: dict) -> dict:
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


# ------------------------------------------------------------------ charts (the accepted NS1b construction)
def chart_hash(r) -> str:
    return sha256_bytes(np.ascontiguousarray(np.asarray(r, np.float64)).tobytes())


def chart_record(entity: int, rank: int, gaze_deg: tuple[float, float]) -> dict:
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


# ------------------------------------------------------------------ record paths and loads
def resolve(ref: str, run: Path, ns1a: Path = SP.NS1A_RUN, ns1b: Path = SP.NS1B_RUN, ns1c: Path = SP.NS1C_RUN) -> Path:
    """'run:rel' / 'ns1a:rel' / 'ns1b:rel' / 'ns1c:rel' -> a path (relocatable for corruption mirrors)."""
    scheme, rel = ref.split(":", 1)
    return {"run": Path(run), "ns1a": Path(ns1a), "ns1b": Path(ns1b), "ns1c": Path(ns1c)}[scheme] / rel


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


def context_from_record(rec: dict, run: Path):
    """The accepted LocalPolicyContext of one entity, rebuilt from its saved looks, evidence and visited gazes."""
    from fov3d.control import object_policy
    from fov3d.experiments.classroom_oracle import controller01 as c01
    k = int(rec["temporary_entity_id"])
    ctx = c01.LocalPolicyContext(k)
    ev = load_npz(resolve(rec["evidence"]["path"], run))
    for name, v in ev.items():
        arr = getattr(ctx.evidence, name)
        if arr.shape != v.shape:
            raise RuntimeError(f"entity {k}: the saved evidence chart shape differs")
        arr[...] = v
    cal = st = None
    for look in rec["looks"]:
        cal = json.loads(resolve(look["calibration"], run).read_text())
        st = load_state(resolve(look["state"], run))
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


def rebuild_context(rec: dict, run: Path, r_hc, q=None):
    """The context recomputed from its looks alone (evidence through P2 under the chart), optionally for the scene
    rigidly rotated about the physical baseline by ``q``; it does not read the saved evidence."""
    from fov3d.control import object_policy
    from fov3d.experiments.classroom_oracle import controller01 as c01, epistemic
    k = int(rec["temporary_entity_id"])
    ctx = c01.LocalPolicyContext(k)
    cal = st = None
    for look in rec["looks"]:
        cal = json.loads(resolve(look["calibration"], run).read_text())
        if q is not None:
            cal = CH.rotate_calibration(cal, q)
        z = load_npz(resolve(look["state"], run))
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


def revision(rec: dict) -> list[int]:
    """The accepted revision semantics: (own looks, effective geometry size); the geometry is the entity's H0 map."""
    return [int(rec["own_looks"]), int(rec["map"]["surfels"])]


# ------------------------------------------------------------------ the NORMAL probe (no gate)
def probe_normal_ctx(ctx, geometry_c: np.ndarray, r_hc: np.ndarray, seed_dir_h0=None, label: str = "probe") -> dict:
    """The accepted FSG6f -> Cyclopean service probe under the frame adapter, read-only.  NO final-look gate."""
    from fov3d.experiments.classroom_oracle import controller01 as c01
    geometry_c = np.asarray(geometry_c, np.float64)
    with CH.PolicyChartAdapter(r_hc, CH.north_star_sensor, label) as ad:
        result, decisions = c01.probe_local_policy(ctx, geometry_c)
    act = result.action
    out = {"state": result.state.value, "summary": jsonable(dict(result.detail)), "decisions": jsonable(decisions),
           "proposal": None, "gate_called": False, "adapter": ad.record(), "effective_points": int(len(geometry_c))}
    if act is not None:
        yc, pc = map(float, act.gaze_yaw_pitch_deg)
        yw, pw, d = CH.local_to_world_gaze(yc, pc, r_hc)
        back = CH.world_to_local_gaze(yw, pw, r_hc)
        prop = {"source": act.source, "local_gaze_deg": [yc, pc], "world_gaze_deg": [yw, pw], "d_H0": d.tolist(),
                "roundtrip_local_gaze_deg": list(back),
                "roundtrip_error_deg": max(abs(back[0] - yc), abs(back[1] - pc)), "leverage": CH.leverage(d)}
        if seed_dir_h0 is not None:
            s = np.asarray(seed_dir_h0, np.float64)
            prop["angle_from_seed_deg"] = math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(s, d) /
                                                                              np.linalg.norm(s))))))
        out["proposal"] = prop
    return out


def probe_entity(rec: dict, run: Path, chart: dict, label: str) -> dict:
    """The NORMAL probe of one entity under its fixed chart, from its record."""
    ctx = context_from_record(rec, run)
    r = np.asarray(chart["R_HC"], np.float64)
    m = load_npz(resolve(rec["map"]["path"], run))
    return probe_normal_ctx(ctx, CH.to_chart(np.asarray(m["xyz_h"], np.float64), r), r,
                            np.asarray(chart["g0_H0"], np.float64), label)


def probe_result(probe_out: dict, entity: int, extra: dict | None = None):
    """The accepted ProbeResult of a probe record: an Observe with the proposal's LOCAL chart gaze, or no action."""
    from fov3d.control import integrated as ic
    v, f = vergence_focus()
    p = probe_out.get("proposal")
    act = None if p is None else ic.Observe(int(entity), tuple(p["local_gaze_deg"]), v, f, p["source"])
    return ic.ProbeResult(act, {**dict(probe_out["summary"]), **(extra or {})})


def policy_comparison(a: dict, b: dict, tol: float = 0.0) -> list[str]:
    """The policy part of two probes (decisions, summary, state, proposal): what NORMAL service depends on."""
    d = (B.compare(a["decisions"], b["decisions"], tol, "decisions")
         + B.compare(a["summary"], b["summary"], tol, "summary")
         + B.compare(a["state"], b["state"], tol, "state"))
    pa, pb = a.get("proposal"), b.get("proposal")
    if (pa is None) != (pb is None):
        d.append("proposal presence")
    elif pa is not None:
        keys = ("source", "local_gaze_deg", "world_gaze_deg", "d_H0", "leverage")
        d += B.compare({k: pa[k] for k in keys}, {k: pb[k] for k in keys}, tol, "proposal")
    return d


def rotation_invariance(rec: dict, run: Path, chart: dict, out: dict, betas=SP.PROBE_ROTATIONS_DEG) -> list[dict]:
    """The NS1b / NS1c in-probe invariance for one entity under rigid rotations about the physical baseline."""
    r = np.asarray(chart["R_HC"], np.float64)
    g0 = np.asarray(chart["g0_H0"], np.float64)
    m = load_npz(resolve(rec["map"]["path"], run))
    map_h0 = np.asarray(m["xyz_h"], np.float64)
    map_c = CH.to_chart(map_h0, r)
    saved = load_npz(resolve(rec["evidence"]["path"], run))
    rows = []
    for beta in betas:
        q = CH.rot_x(beta)
        rq = CH.chart_basis(q @ g0)["R_HC"]
        ctx = rebuild_context(rec, run, rq, q)
        ev = evidence_arrays(ctx)
        ev_equal = set(ev) == set(saved) and all(np.array_equal(ev[key], saved[key]) for key in ev)
        oq = probe_normal_ctx(ctx, CH.to_chart(map_h0 @ q.T, rq), rq, q @ g0,
                              f"invariance {beta} entity {rec['temporary_entity_id']}")
        tol = B.SP.FLOAT_TOL     # the accepted NS1b comparison tolerance (discrete fields exact)
        diffs = (B.compare(out["decisions"], oq["decisions"], tol, "decisions")
                 + B.compare(out["summary"], oq["summary"], tol, "summary")
                 + B.compare(out["state"], oq["state"], 0.0, "state"))
        diffs, flip = B.explain_voxel_flip(diffs, map_c)
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


# ------------------------------------------------------------------ the RESIDUE gate (accepted gate, unchanged proposal)
def residue_gate(rec: dict, run: Path, chart: dict, cached_probe: dict, proposal, head_r_wh, head_origin_w,
                 label: str = "residue gate") -> tuple[Any, dict]:
    """The accepted ``final_look_gate_v1`` on the UNCHANGED cached proposal of a DEFERRED ACTIONABLE entity.

    The context is rebuilt from the record; the probe is recomputed (same revision -> same decision) and must equal the
    cached probe exactly; the gate then receives the cached ProbeResult and the recomputed FSG6f decision, under the
    frame adapter with the North-Star sensor for P3.  Must be called with the gate guard in phase RESIDUE."""
    from fov3d.experiments.classroom_oracle import controller01 as c01, controller02 as x2
    from fov3d.control import controller02 as c2
    ctx = context_from_record(rec, run)
    r = np.asarray(chart["R_HC"], np.float64)
    m = load_npz(resolve(rec["map"]["path"], run))
    geometry_c = CH.to_chart(np.asarray(m["xyz_h"], np.float64), r)
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
    detail = {"admissible": bool(verdict.admissible), "reason": verdict.reason, "detail": jsonable(dict(verdict.detail)),
              "adapter": ad.record(), "recomputed_probe_equal": True}
    return c2.FinalProbeDecision(bool(verdict.admissible), verdict.reason, {"record": detail}), detail


# ------------------------------------------------------------------ the world gaze of a proposal
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


# ------------------------------------------------------------------ the target-only patch
def target_patch(xyz_epi, valid, ids, rgb, target: int, step: int) -> dict:
    keep = np.asarray(valid, bool) & (np.asarray(ids) == int(target))
    return {"frame": SP.FUSION_FRAME, "patch_id": SP.patch_id(step),
            "xyz_h": np.asarray(xyz_epi, np.float64)[keep], "rgb": np.asarray(rgb, np.float64)[keep],
            "instance_id": np.asarray(ids, np.int32)[keep], "points": int(keep.sum())}


def map_arrays(m) -> dict:
    return B.map_arrays(m)


def maps_equal(a: dict, b: dict) -> bool:
    return B.maps_equal(a, b)


def stop_event(target: int, fusion_action: str | None) -> bool:
    """The canonical stop: a successful physical action (through the fusion stage) on a target other than 172."""
    return int(target) != SP.CONTINUING and fusion_action in ("FUSED", "RETAINED_NOT_FUSED")


def require_not_stopped(scene: dict) -> None:
    if scene.get("stopped"):
        raise ProcessRefused(f"the canonical stop is reached (first cross-entity action at step "
                             f"{scene['stop']['global_step']}); no further action is scheduled")


def require_under_cap(new_actions: int, cap: int | None) -> None:
    if cap is not None and int(new_actions) >= int(cap):
        raise ProcessRefused(f"the post-divergence safety cap is reached: {new_actions} new actions >= cap {cap}")


def derived_cap(budget: int, own_looks_172: int) -> int:
    return (int(budget) - int(own_looks_172)) + 1


# ------------------------------------------------------------------ scene records
def proposal_summary(probe_out: dict) -> dict | None:
    p = probe_out.get("proposal")
    if p is None:
        return None
    return {k: p[k] for k in ("source", "local_gaze_deg", "world_gaze_deg", "leverage", "angle_from_seed_deg")
            if k in p}


def policy_summary(probe_out: dict) -> dict:
    s = probe_out["summary"]
    return {"fsg6f": s.get("fsg6f"), "cyclopean": s.get("cyclopean")}


def entity_row(rec: dict) -> dict:
    return {"temporary_entity_id": rec["temporary_entity_id"], "initialization_rank": rec["initialization_rank"],
            "chart_id": rec["chart_id"], "chart_sha256": rec["chart_sha256"],
            "current_local_gaze": rec["current_local_gaze"], "own_looks": rec["own_looks"],
            "map_surfels": rec["map"]["surfels"], "local_state": rec["status"]["local"],
            "disposition": rec["status"]["disposition"], "reason": rec["status"]["reason"],
            "label": rec["status"]["label"], "proposal": rec.get("proposal"),
            "fsg6f": ((rec.get("policy") or {}).get("fsg6f") or {}).get("reason"),
            "cyclopean": ((rec.get("policy") or {}).get("cyclopean") or {}).get("reason"),
            "revision": rec["revision"], "probe_provenance": rec["probe"].get("provenance")}


def status_record(st) -> dict:
    return {"local": st.local.value, "disposition": st.disposition.value, "reason": st.reason, "label": st.label,
            "serviceable": bool(st.serviceable)}


def deferred_rows(elig: dict) -> list[dict]:
    return [{"temporary_entity_id": r["temporary_entity_id"], "contributing_patches": r["contributing_patches"],
             "initialized_at_rank": r["initialized_at_rank"], "final_surfels": r["final_surfels"],
             "state": SP.DEFERRED_STATE, "in_scheduler": False} for r in elig["deferred"]]


def probe_record_file(probe_out: dict) -> bytes:
    return (json.dumps(jsonable(probe_out), indent=1, sort_keys=True, allow_nan=False) + "\n").encode()
