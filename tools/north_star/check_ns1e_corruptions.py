#!/usr/bin/env python3
"""North Star-1e corruption suite: every corruption must be caught by its expected check(s).

    (run through check_ns1e.py --corruptions)

Contract: docs/north-star/ns1e-coherent-full-loop-m2-memory-contract.md, section 30.  From a passing baseline and after
an unmodified-mirror null probe.  A mirror copies every JSON / JSONL file of RUN and VIS and symlinks everything else; a
corruption unlinks a symlinked file before writing it.  RUN and VIS are hashed before and after the suite.  In-process
corruptions substitute an accepted function (or the scanned source) for the duration of their checks only.  A
corruption that cannot apply to the executed trace is NOT APPLICABLE (with its reason), never counted as caught.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_ns1e as C  # noqa: E402


def tree_hash(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob("*")):
        if p.is_file() and p.name not in ("check-summary.json",):
            h.update(str(p.relative_to(root)).encode())
            st = p.stat()
            h.update(f"{st.st_size}:{st.st_mtime_ns}".encode())
    return h.hexdigest()


def mirror(src: Path, dst: Path) -> None:
    for p in sorted(Path(src).rglob("*")):
        q = dst / p.relative_to(src)
        if p.is_dir():
            q.mkdir(parents=True, exist_ok=True)
        elif p.suffix in (".json", ".jsonl"):
            q.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, q)
        else:
            q.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(p.resolve(), q)


def rj(p: Path):
    return json.loads(Path(p).read_text())


def wj(p: Path, d) -> None:
    p = Path(p)
    if p.is_symlink():
        p.unlink()
    p.write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")


def edit(p: Path, fn) -> None:
    d = rj(p)
    fn(d)
    wj(p, d)


def wnpz(p: Path, arrays: dict) -> None:
    p = Path(p)
    if p.is_symlink() or p.exists():
        p.unlink()
    np.savez_compressed(p, **arrays)


def steps(run: Path) -> list[int]:
    return C.X(run, run).steps()


def first_step_where(run: Path, pred) -> int | None:
    x = C.X(run, run)
    for k in x.steps():
        if pred(x, k):
            return k
    return None


def last_state(run: Path) -> Path:
    st = steps(run)
    return run / (f"scene/state-after-step-{st[-1]:03d}.json" if st else "scene/state-initial.json")


# ------------------------------------------------------------------ the corruptions (mutate a mirror; return None or a
# context manager for in-process substitutions; raise NotApplicable)
class NotApplicable(Exception):
    pass


def cross_step(run):
    k = first_step_where(run, lambda x, k: bool(x.j(f"{x.sd(k)}/memory/event.json")["coherent_cross_target_additions"]
                                                 or x.j(f"{x.sd(k)}/memory/event.json")["non_scheduler_additions"]))
    if k is None:
        raise NotApplicable("no step observed an id other than its target")
    return k


def s_drop_event8(run, vis):
    edit(run / "scene/state-initial.json", lambda d: d["memory"]["events"].pop(8))


def s_change_current(run, vis):
    def f(d):
        d["current"] = 172
        d["machine"]["current"] = 172
    edit(run / "scene/state-initial.json", f)


def s_revert_202_map(run, vis):
    def f(d):
        d["entities"]["202"]["map"]["path"] = "ns1c2:contexts/entities/e00202/map-H0.npz"
    edit(run / "scene/state-initial.json", f)


def s_revert_172_looks(run, vis):
    def f(d):
        d["entities"]["172"]["own_looks"] = 8
    edit(run / "scene/state-initial.json", f)


def s_change_next(run, vis):
    def f(d):
        d["action"]["local_gaze_deg"] = [-5.9, 10.5]
    edit(run / "steps/step-008/plan/decision.json", f)


def _patch_mut(run, k, fn):
    p = run / f"steps/step-{k:03d}/memory/memory-patch.npz"
    a = C.load(p)
    fn(a, rj(run / f"steps/step-{k:03d}/plan/decision.json")["action"]["target"])
    wnpz(p, a)


def m_route_by_active(run, vis):
    k = cross_step(run)
    _patch_mut(run, k, lambda a, t: a["instance_id"].__setitem__(a["valid"], int(t)))


def m_discard_cross(run, vis):
    k = cross_step(run)

    def f(a, t):
        drop = a["valid"] & (a["instance_id"] != int(t))
        a["valid"][drop] = False
        a["instance_id"][drop] = 0
    _patch_mut(run, k, f)


def m_append_twice(run, vis):
    edit(last_state(run), lambda d: d["memory"]["events"].append(copy.deepcopy(d["memory"]["events"][-1])))


def m_include_id0(run, vis):
    k = steps(run)[0]

    def f(a, t):
        z = np.isfinite(a["xyz_h"]).all(-1) & ~a["valid"]
        if not z.any():
            raise NotApplicable("no measured instance-0 cell")
        a["valid"][z] = True
    _patch_mut(run, k, f)


def m_fuse_cross(run, vis):
    k = cross_step(run)
    p = run / f"steps/step-{k:03d}/fusion/fused-target-map.npz"
    a = C.load(p)
    mp = C.load(run / f"steps/step-{k:03d}/memory/memory-patch.npz")
    t = rj(run / f"steps/step-{k:03d}/plan/decision.json")["action"]["target"]
    sel = mp["valid"] & (mp["instance_id"] != t)
    extra = mp["xyz_h"][sel][:50].astype(np.float64)
    a["xyz_h"] = np.vstack([a["xyz_h"], extra])
    a["rgb"] = np.vstack([a["rgb"], np.zeros((len(extra), 3))])
    a["instance_id"] = np.concatenate([a["instance_id"], np.full(len(extra), t, a["instance_id"].dtype)])
    a["support_count"] = np.concatenate([a["support_count"], np.ones(len(extra), a["support_count"].dtype)])
    a["provenance_mask"] = np.concatenate([a["provenance_mask"], np.ones(len(extra), a["provenance_mask"].dtype)])
    wnpz(p, a)


def m_revision_semantics(run, vis):
    def f(d):
        for rec in d["entities"].values():
            rec["revision"] = [rec["own_looks"], rec["map"]["surfels"]]
    edit(last_state(run), f)


def x_incidental_gaze(run, vis):
    k = steps(run)[0]
    t = rj(run / f"steps/step-{k:03d}/plan/decision.json")["action"]["target"]
    o = next(i for i in C.COHERENT if i != t)
    edit(run / f"scene/state-after-step-{k:03d}.json", lambda d: d["entities"][str(o)]["visited"].append([1.0, 1.0]))


def x_other_evidence(run, vis):
    k = steps(run)[0]
    t = rj(run / f"steps/step-{k:03d}/plan/decision.json")["action"]["target"]
    o = next(i for i in C.COHERENT if i != t)

    def f(d):
        d["entities"][str(o)]["evidence"]["path"] = f"run:steps/step-{k:03d}/update/evidence.npz"
    edit(run / f"scene/state-after-step-{k:03d}.json", f)


def c_gate_cyc_normal(run, vis):
    k = first_step_where(run, lambda x, k: x.dec(k)["action"]["source"] == "cyclopean_epistemic")
    if k is None:
        raise NotApplicable("no Cyclopean action")

    def f(d):
        d["gate_guard"]["normal_calls"] = 1
        d["gate_guard"]["calls"] = 1
    edit(run / f"steps/step-{k:03d}/plan/decision.json", f)


def c_gate_fsg_normal(run, vis):
    k = first_step_where(run, lambda x, k: x.dec(k)["action"]["source"] == "fsg6f")
    if k is None:
        raise NotApplicable("no FSG6f action")

    def f(d):
        d["gate_guard"]["normal_calls"] = 1
        d["gate_guard"]["calls"] = 1
    edit(run / f"steps/step-{k:03d}/update/update.json", f)


@contextlib.contextmanager
def _subst(mod, name, fn):
    orig = getattr(mod, name)
    setattr(mod, name, fn)
    try:
        yield
    finally:
        setattr(mod, name, orig)


def c_scheduler_order(run, vis):
    from fov3d.control import controller02 as c2, integrated as ic
    orig = c2.schedule_normal
    x = C.X(run, run)
    if not any(x.dec(k)["action"]["decision"] == "switch" for k in x.steps()):
        raise NotApplicable("no switch in the trace")

    def reversed_order(current_id, statuses):
        rows = sorted(statuses, key=lambda s: int(s.instance_id))
        serviceable = [int(s.instance_id) for s in rows if s.serviceable]
        cur = {int(s.instance_id): s for s in rows}.get(current_id)
        if cur is not None and cur.serviceable:
            return ic.Decision("attend", int(current_id), "retain")
        if serviceable:
            back = [i for i in serviceable if i < int(current_id)]
            return ic.Decision("attend", back[-1] if back else serviceable[-1], "switch")
        return orig(current_id, statuses)
    return _subst(c2, "schedule_normal", reversed_order)


def c_change_budget(run, vis):
    def f(d):
        d["machine"]["budget"] = 25
    edit(run / "scene/state-initial.json", f)


def c_block_not_defer(run, vis):
    def f(d):
        k0 = next(iter(d["machine"]["statuses"]))
        d["machine"]["statuses"][k0][1] = "BLOCKED"
    edit(last_state(run), f)


def c_manual_reactivation(run, vis):
    src = (C.HERE / "ns1e_run.py").read_text() + "\n\ndef _corrupt(m):\n    m.reactivate(202)\n    m.quiet_since = {}\n"
    return _subst(C, "SOURCE_OVERRIDE", {"ns1e_run.py": src})


def ch_dynamic_recenter(run, vis):
    def f(d):
        st = C.X(run, run).final()
        m = C.load(C.X(run, run).ref(st["entities"]["202"]["map"]["path"]))["xyz_h"]
        g = np.median(m, axis=0)
        g = g / np.linalg.norm(g)
        yaw, pitch = math.degrees(math.atan2(g[0], -g[2])), math.degrees(math.atan2(g[1], math.hypot(g[0], g[2])))
        d["charts"]["202"]["R_HC"] = C.own_chart((yaw, pitch)).tolist()
    edit(run / "handoff/charts.json", f)


def ch_centroid_centre(run, vis):
    def f(d):
        st = C.X(run, run).initial()
        m = C.load(C.X(run, run).ref(st["entities"]["123"]["map"]["path"]))["xyz_h"]
        g = m.mean(axis=0)
        g = g / np.linalg.norm(g)
        yaw, pitch = math.degrees(math.atan2(g[0], -g[2])), math.degrees(math.atan2(g[1], math.hypot(g[0], g[2])))
        d["charts"]["123"]["R_HC"] = C.own_chart((yaw, pitch)).tolist()
    edit(run / "handoff/charts.json", f)


def ch_transpose(run, vis):
    edit(run / "handoff/charts.json",
         lambda d: d["charts"]["172"].__setitem__("R_HC", np.asarray(d["charts"]["172"]["R_HC"]).T.tolist()))


def _cal_edit(run, fn, k=None):
    k = steps(run)[0] if k is None else k
    edit(run / f"steps/step-{k:03d}/observation/acquisition/calibration.json", fn)


def p_move_head(run, vis):
    _cal_edit(run, lambda c: c.__setitem__("head_origin_w_m", [c["head_origin_w_m"][0] + 0.01] + c["head_origin_w_m"][1:]))


def p_rotate_baseline(run, vis):
    def f(c):
        a = math.radians(10)
        for e in c["eyes"]:
            x0, _y, z0 = e["centre_h_m"]
            e["centre_h_m"] = [x0 * math.cos(a), 0.0, -x0 * math.sin(a) + z0]
    _cal_edit(run, f)


def p_change_ipd(run, vis):
    _cal_edit(run, lambda c: c.__setitem__("ipd_m", 0.065))


def p_fake_local(run, vis):
    import ns1b_chart as CH
    k = steps(run)[0]
    d = rj(run / f"steps/step-{k:03d}/plan/decision.json")
    c0 = rj(C.NS1A / "observations/rank-01/acquisition/calibration.json")
    fake = CH.baseline_projected_sensor("full", *d["action"]["local_gaze_deg"], np.asarray(c0["head_R_wh"]),
                                        np.asarray(c0["head_origin_w_m"]))
    wj(run / f"steps/step-{k:03d}/observation/acquisition/calibration.json", C.json.loads(C.json.dumps(fake,
                                                                                                         default=float)))


def r_spp(run, vis):
    edit(run / f"steps/step-{steps(run)[0]:03d}/observation/acquisition-run.json", lambda d: d.__setitem__("spp", 2048))


def r_denoise(run, vis):
    edit(run / f"steps/step-{steps(run)[0]:03d}/observation/acquisition/acquisition.json",
         lambda d: d["settings"].__setitem__("denoising", True))


def r_rerender(run, vis):
    p = run / "process-log.jsonl"
    lines = p.read_text().splitlines()
    k = steps(run)[0]
    acq = [ln for ln in lines if json.loads(ln).get("command") == "acquire" and json.loads(ln).get("step") == k
           and json.loads(ln)["status"] == "ok"]
    p.write_text("\n".join(lines + acq) + "\n")


def e_sgbm(run, vis):
    edit(run / f"steps/step-{steps(run)[0]:03d}/correspondence/correspondence-opened-files.json",
         lambda d: d["modules_loaded"].__setitem__("ab1d3_sgbm", True))


def e_planar(run, vis):
    k = steps(run)[0]
    p = run / f"steps/step-{k:03d}/geometry/epipolar-result.npz"
    a = C.load(p)
    a["P_epi"] = a["P_epi"] * 1.001
    wnpz(p, a)


def e_position_leak(run, vis):
    k = steps(run)[0]

    def f(d):
        d["position_reads"] = 1
        d["events"].append({"event": "open", "path": str(run / f"steps/step-{k:03d}/observation/oracle_aid/"
                                                         "reference-observation.npz"), "kind": "data-read",
                            "allowed": True})
    edit(run / f"steps/step-{k:03d}/geometry/geometry-opened-files.json", f)


def f_radius(run, vis):
    k = first_step_where(run, lambda x, k: x.j(f"{x.sd(k)}/fusion/fusion.json")["action"] == "FUSED")
    if k is None:
        raise NotApplicable("no fused step")
    edit(run / f"steps/step-{k:03d}/fusion/fusion.json", lambda d: d.__setitem__("radius_m", 0.025))


def f_cross_id(run, vis):
    k = first_step_where(run, lambda x, k: x.j(f"{x.sd(k)}/fusion/fusion.json")["action"] == "FUSED")
    if k is None:
        raise NotApplicable("no fused step")
    p = run / f"steps/step-{k:03d}/fusion/fused-target-map.npz"
    a = C.load(p)
    a["instance_id"] = a["instance_id"].copy()
    a["instance_id"][:10] = 110
    wnpz(p, a)


def f_memory_points(run, vis):
    k = first_step_where(run, lambda x, k: x.j(f"{x.sd(k)}/fusion/fusion.json")["action"] == "FUSED")
    if k is None:
        raise NotApplicable("no fused step")
    p = run / f"steps/step-{k:03d}/fusion/fused-target-map.npz"
    a = C.load(p)
    a["support_count"] = a["support_count"] + 1
    wnpz(p, a)


def rs_while_normal(run, vis):
    k = steps(run)[0]

    def f(d):
        d["residue_gate_records"] = [{"object": d["action"]["target"], "phase": "RESIDUE", "admissible": True,
                                      "reason": "x", "proposal": {"local_gaze_deg": d["action"]["local_gaze_deg"],
                                                                  "source": d["action"]["source"],
                                                                  "world_gaze_deg": d["action"]["world_gaze_deg"]},
                                      "adapter": {"p3": [], "sensor": "north_star_sensor"}}]
    edit(run / f"steps/step-{k:03d}/plan/decision.json", f)


def rs_gate_outside(run, vis):
    rs_while_normal(run, vis)
    k = steps(run)[0]
    edit(run / f"steps/step-{k:03d}/plan/decision.json", lambda d: d["residue_gate_records"][0].__setitem__("phase",
                                                                                                         "NORMAL"))


def rs_modify_proposal(run, vis):
    x = C.X(run, run)
    k = next((k for k in x.steps() if x.dec(k).get("residue_gate_records")), None)
    if k is not None:
        edit(run / f"steps/step-{k:03d}/plan/decision.json",
             lambda d: d["residue_gate_records"][0]["proposal"].__setitem__("local_gaze_deg", [0.0, 0.0]))
        return
    t = x.terminal()
    if not (t and t.get("residue_gate_records")):
        raise NotApplicable("no residue gate call in the trace (exercised by synthetic test t10)")
    edit(run / "scene/terminal.json",
         lambda d: d["residue_gate_records"][0]["proposal"].__setitem__("local_gaze_deg", [0.0, 0.0]))


def rs_two_finals(run, vis):
    x = C.X(run, run)
    st = x.steps()
    if len(st) < 2:
        raise NotApplicable("fewer than two steps")
    t = x.dec(st[0])["action"]["target"]
    k2 = next((k for k in st[1:] if x.dec(k)["action"]["target"] == t), None)
    if k2 is None:
        raise NotApplicable("no second action on one entity")
    for k in (st[0], k2):
        edit(run / f"steps/step-{k:03d}/plan/decision.json", lambda d: (d.__setitem__("kind", "final_residue"),
                                                                        d["action"].__setitem__("phase", "RESIDUE")))


def k_increase_cap(run, vis):
    edit(run / "handoff/cap.json", lambda d: d.__setitem__("absolute_action_cap", 240))


def k_ignore_cap(run, vis):
    edit(run / f"steps/step-{steps(run)[-1]:03d}/plan/decision.json", lambda d: d.__setitem__("cap", None))


def q_duplicate_action(run, vis):
    p = run / "process-log.jsonl"
    lines = p.read_text().splitlines()
    k = steps(run)[0]
    up = [ln for ln in lines if json.loads(ln).get("command") == "update" and json.loads(ln).get("step") == k]
    p.write_text("\n".join(lines + up) + "\n")


def q_reuse_event(run, vis):
    st = steps(run)
    if len(st) < 2:
        raise NotApplicable("fewer than two steps")
    edit(run / f"steps/step-{st[1]:03d}/memory/event.json", lambda d: d.__setitem__("memory_event", st[0] + 1))


def q_partial(run, vis):
    k = steps(run)[-1] + 1
    t = C.X(run, run).terminal()
    if t is not None:
        k += 1
    d = run / f"steps/step-{k:03d}/plan"
    d.mkdir(parents=True, exist_ok=True)
    wj(d / "decision.json", {"kind": "attend"})


def v_truth_before_freeze(run, vis):
    k = steps(run)[0]
    edit(run / f"steps/step-{k:03d}/plan/plan-opened-files.json",
         lambda d: d["events"].append({"event": "open", "path": str(C.B1_EXR), "kind": "data-read", "allowed": True}))


def v_memory_in_primary(run, vis):
    def f(d):
        for r in d["per_entity"].values():
            if r.get("covered_cells") is not None and r["effective_covered_cells"] != r["covered_cells"]:
                r["covered_cells"] = r["effective_covered_cells"]
                return
        raise NotApplicable("effective and persistent coverage are equal for every entity")
    edit(run / "evaluation/evaluation.json", f)


def v_other_radius(run, vis):
    edit(run / "evaluation/evaluation.json", lambda d: d.__setitem__("radius_m", 0.025))


def v_comparable(run, vis):
    edit(run / "evaluation/evaluation.json", lambda d: d["historical_reference"].__setitem__("comparable", True))


def v_comparable_text(run, vis):
    edit(run / "evaluation/evaluation.json",
         lambda d: d.__setitem__("note", "persistent coverage is better than 98.34 % of Controller-01"))


def w_hide_labels(run, vis):
    edit(vis / "visuals-manifest.json", lambda d: d["figures"]["overview.png"]["labels"].remove("ORACLE CORRESPONDENCE"))


def w_memory_fused(run, vis):
    p = vis / "final-coherent-persistent-points.ply"
    b = p.read_bytes()
    import ns1e_core as CORE
    r = CORE.ply_read(b)
    extra = (172, np.zeros((5, 3)), None)
    groups = [(int(e), r["xyz"][r["entity_id"] == e], None) for e in sorted(set(r["entity_id"].tolist()))] + [extra]
    if p.is_symlink():
        p.unlink()
    p.write_bytes(CORE.ply_bytes(groups, "\n".join(r["comments"])))


def w_full_classroom(run, vis):
    if not (run / "scene/terminal.json").exists():
        raise NotApplicable("no terminal")
    edit(run / "scene/terminal.json", lambda d: d["outcome"].__setitem__("scope", "FULL_CLASSROOM_CLOSED"))


def w_pixel(run, vis):
    from PIL import Image
    p = vis / "overview.png"
    im = Image.open(p).convert("RGB")
    im.putpixel((5, 5), (255, 0, 0))
    p.unlink()
    im.save(p, format="PNG")


CORRUPTIONS = [
    ("START", "drop NS1d memory event 8", s_drop_event8, ["04", "16"]),
    ("START", "change the current target", s_change_current, ["04", "08"]),
    ("START", "revert 202's map", s_revert_202_map, ["15"]),
    ("START", "revert 172's own looks", s_revert_172_looks, ["04", "12"]),
    ("START", "change the next action", s_change_next, ["08", "07"]),
    ("MEMORY", "route by active id", m_route_by_active, ["16"]),
    ("MEMORY", "discard cross-target ids", m_discard_cross, ["16"]),
    ("MEMORY", "append twice", m_append_twice, ["16"]),
    ("MEMORY", "include id 0", m_include_id0, ["16"]),
    ("MEMORY", "fuse cross-target memory", m_fuse_cross, ["15"]),
    ("MEMORY", "alter revision semantics", m_revision_semantics, ["12"]),
    ("CONTEXT", "incidental gaze in another visited list", x_incidental_gaze, ["17"]),
    ("CONTEXT", "another entity's evidence altered", x_other_evidence, ["17"]),
    ("CONTROLLER", "gate Cyclopean in NORMAL", c_gate_cyc_normal, ["08"]),
    ("CONTROLLER", "gate FSG6f in NORMAL", c_gate_fsg_normal, ["08"]),
    ("CONTROLLER", "change scheduler order", c_scheduler_order, ["08"]),
    ("CONTROLLER", "change budget", c_change_budget, ["11", "21"]),
    ("CONTROLLER", "block instead of defer", c_block_not_defer, ["11"]),
    ("CONTROLLER", "manual reactivation", c_manual_reactivation, ["19"]),
    ("CHART", "dynamic recenter", ch_dynamic_recenter, ["06"]),
    ("CHART", "map-centroid centre", ch_centroid_centre, ["06"]),
    ("CHART", "transposed transform", ch_transpose, ["06"]),
    ("SENSOR", "move head", p_move_head, ["07"]),
    ("SENSOR", "rotate baseline", p_rotate_baseline, ["07"]),
    ("SENSOR", "change IPD", p_change_ipd, ["07"]),
    ("SENSOR", "fake local calibration", p_fake_local, ["07"]),
    ("RENDER", "change spp", r_spp, ["13"]),
    ("RENDER", "enable denoise", r_denoise, ["13"]),
    ("RENDER", "re-render a completed action", r_rerender, ["13", "22"]),
    ("MEASUREMENT", "SGBM", e_sgbm, ["14"]),
    ("MEASUREMENT", "planar persistent geometry", e_planar, ["14"]),
    ("MEASUREMENT", "Position read before the freeze", e_position_leak, ["14"]),
    ("FUSION", "change 12 mm", f_radius, ["15"]),
    ("FUSION", "cross-id fusion", f_cross_id, ["15"]),
    ("FUSION", "fuse memory points", f_memory_points, ["15"]),
    ("RESIDUE", "enter while NORMAL service exists", rs_while_normal, ["20"]),
    ("RESIDUE", "gate outside RESIDUE", rs_gate_outside, ["10"]),
    ("RESIDUE", "modify the proposal before the gate", rs_modify_proposal, ["08"]),
    ("RESIDUE", "two final residue observations for one entity", rs_two_finals, ["20"]),
    ("CAP", "increase the cap", k_increase_cap, ["21"]),
    ("CAP", "ignore the cap", k_ignore_cap, ["21"]),
    ("CHECKPOINT", "duplicate a completed action", q_duplicate_action, ["22"]),
    ("CHECKPOINT", "reuse a memory-event id", q_reuse_event, ["16"]),
    ("CHECKPOINT", "continue from a partial action", q_partial, ["22"]),
    ("EVALUATION", "reference truth opened before the control freeze", v_truth_before_freeze, ["23"]),
    ("EVALUATION", "memory in the primary coverage", v_memory_in_primary, ["24"]),
    ("EVALUATION", "another radius", v_other_radius, ["24"]),
    ("EVALUATION", "98.34 % called comparable", v_comparable, ["24"]),
    ("EVALUATION", "98.34 % compared in text", v_comparable_text, ["25"]),
    ("VISUAL", "oracle labels hidden", w_hide_labels, ["26"]),
    ("VISUAL", "memory exported as fused geometry", w_memory_fused, ["26"]),
    ("VISUAL", "full-Classroom closure claimed", w_full_classroom, ["25"]),
    ("VISUAL", "a pixel altered", w_pixel, ["26"]),
]


def run_suite(run: Path, vis: Path, baseline_failed=(), rehearsal: bool = False, names=None) -> dict:
    run, vis = Path(run), Path(vis)
    before = (tree_hash(run), tree_hash(vis))
    out = {"baseline_failed": list(baseline_failed), "results": [], "missed": [], "not_applicable": []}
    needed = sorted({c for _f, _n, _fn, cs in CORRUPTIONS for c in cs})
    with tempfile.TemporaryDirectory(prefix="ns1e-corr-") as td:
        m_run, m_vis = Path(td) / "run", Path(td) / "vis"
        mirror(run, m_run)
        mirror(vis, m_vis)
        null = C.run_checks(m_run, m_vis, only=set(needed), quiet=True, rehearsal=rehearsal)
        out["null_probe"] = {k: v["pass"] for k, v in null.items()}
        out["null_clean"] = all(v["pass"] for v in null.values())
        shutil.rmtree(m_run)
        shutil.rmtree(m_vis)
        for fam, name, fn, expect in CORRUPTIONS:
            if names is not None and name not in names:
                continue
            mirror(run, m_run)
            mirror(vis, m_vis)
            try:
                ctxm = fn(m_run, m_vis)
            except NotApplicable as e:
                out["not_applicable"].append({"family": fam, "corruption": name, "reason": str(e)})
                shutil.rmtree(m_run)
                shutil.rmtree(m_vis)
                continue
            with (ctxm if ctxm is not None else contextlib.nullcontext()):
                res = C.run_checks(m_run, m_vis, only=set(expect), quiet=True, rehearsal=rehearsal)
            caught = [k for k, v in res.items() if not v["pass"]]
            row = {"family": fam, "corruption": name, "expected": expect, "caught_by": caught, "caught": bool(caught)}
            out["results"].append(row)
            if not caught:
                out["missed"].append(name)
            print(f"[ns1e-corruptions] {'CAUGHT' if caught else 'MISSED'} {fam}: {name} {caught}", flush=True)
            shutil.rmtree(m_run)
            shutil.rmtree(m_vis)
    after = (tree_hash(run), tree_hash(vis))
    out["run_unchanged_by_suite"] = before == after
    n = len(out["results"])
    out["summary"] = {"applied": n, "caught": n - len(out["missed"]), "not_applicable": len(out["not_applicable"])}
    out["marker"] = "NORTH_STAR1E_MUTATIONS_CAUGHT" if not out["missed"] and out["null_clean"] else \
        "NORTH_STAR1E_MUTATIONS_FAIL"
    print(f"[ns1e-corruptions] {out['marker']} {out['summary']} null clean {out['null_clean']}", flush=True)
    return out
