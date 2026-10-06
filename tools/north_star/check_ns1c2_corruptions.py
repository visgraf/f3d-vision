"""North Star-1c2 corruption / mutation suite (contract section 25).

Run from ``check_ns1c2.py --corruptions`` after a passing baseline.  A temporary mirror of RUN and VIS is built (small
files copied; large arrays symlinked and unlinked before any write).  An unmodified-mirror null probe must pass every
check.  Each corruption then mutates a fresh mirror (an altered record, a regenerated wrong artifact, a figure) or the
code under check in-process (a source mutant of the phase adapter, a gated probe, a disabled guard), regenerates the
mirror's manifest and runs the checks it names; each named check must fail.  Corruptions that do not apply to the
executed trajectory are recorded NOT APPLICABLE, never counted as caught.  RUN and VIS are hashed before and after.
"""
from __future__ import annotations

import contextlib
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import textwrap

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_ns1c2 as C  # noqa: E402

BIG = 1 << 20


def tree_hashes(root: Path) -> dict:
    return {str(p.relative_to(root)): C.sha256(p) for p in sorted(root.rglob("*")) if p.is_file()}


def mirror(run: Path, vis: Path, td: Path) -> tuple[Path, Path]:
    m, mv = td / "run", td / "vis"
    for src, dst in ((run, m), (vis, mv)):
        for p in sorted(src.rglob("*")):
            q = dst / p.relative_to(src)
            if p.is_dir():
                q.mkdir(parents=True, exist_ok=True)
                continue
            q.parent.mkdir(parents=True, exist_ok=True)
            if p.stat().st_size > BIG and src == run:
                os.symlink(p.resolve(), q)
            else:
                shutil.copyfile(p, q)
    return m, mv


def unlinked(p: Path) -> Path:
    if p.is_symlink():
        p.unlink()
    return p


def jl(m: Path, rel: str):
    return json.loads((m / rel).read_text())


def js(m: Path, rel: str, d) -> None:
    unlinked(m / rel).write_text(json.dumps(d, indent=1, sort_keys=True, allow_nan=False) + "\n")


def nl(m: Path, rel: str) -> dict:
    with np.load(m / rel, allow_pickle=False) as z:
        return {k: np.asarray(z[k]) for k in z.files}


def ns(m: Path, rel: str, d: dict) -> None:
    (m / rel).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(unlinked(m / rel), **d)


def remanifest(m: Path) -> None:
    man = jl(m, "manifest.json")
    files = sorted(str(p.relative_to(m)) for p in m.rglob("*") if p.is_file()
                   and p.name not in ("manifest.json", "check-summary.json", "process-log.jsonl"))
    man["files"] = {f: C.sha256(m / f) for f in files}
    js(m, "manifest.json", man)


def edit(m: Path, rel: str, fn) -> None:
    d = jl(m, rel)
    fn(d)
    js(m, rel, d)


def log_entries(m: Path) -> list[dict]:
    return [json.loads(ln) for ln in (m / "process-log.jsonl").read_text().splitlines() if ln.strip()]


def log_append(m: Path, entries: list[dict]) -> None:
    unlinked(m / "process-log.jsonl")
    with open(m / "process-log.jsonl", "a") as f:
        for e in entries:
            f.write(json.dumps(e, sort_keys=True) + "\n")


# ------------------------------------------------------------------ trajectory helpers
def executed(m: Path) -> list[tuple[int, dict]]:
    out = []
    for p in sorted((m / "steps").glob("step-*/plan/decision.json")) if (m / "steps").exists() else []:
        k = int(p.parent.parent.name.split("-")[1])
        d = json.loads(p.read_text())
        if d["kind"] in ("attend", "final_residue") and (m / f"steps/step-{k:02d}/update/update.json").exists():
            out.append((k, d))
    return out


def new_steps(m: Path) -> list[tuple[int, dict]]:
    return [(k, d) for k, d in executed(m) if k >= C.PREFIX_STEPS]


def switch_step(m: Path) -> int | None:
    return next((k for k, d in new_steps(m) if int(d["action"]["target"]) != C.CONTINUING), None)


def state_before(k: int) -> str:
    return "scene/state-initial.json" if k == 0 else f"scene/state-after-step-{k - 1:02d}.json"


def cyclopean_entity(m: Path) -> str | None:
    s0 = jl(m, "scene/state-initial.json")
    for k, rec in sorted(s0["entities"].items(), key=lambda t: int(t[0])):
        pf = json.loads((m / rec["probe"]["path"].split(":", 1)[1]).read_text())
        if (pf["probe"]["proposal"] or {}).get("source") == "cyclopean_epistemic":
            return k
    return None


# ------------------------------------------------------------------ the corruptions: SEMANTICS
@contextlib.contextmanager
def gated_cyclopean():
    """NS1c's error: the v1 gate applied in NORMAL, which rejects every Cyclopean proposal (untraceable)."""
    import ns1c2_core as CORE
    orig = CORE.probe_normal_ctx

    def gated(*a, **k):
        out = orig(*a, **k)
        if out["proposal"] is not None and out["proposal"]["source"] == "cyclopean_epistemic":
            out = {**out, "proposal": None, "state": "QUIET",
                   "gate": {"admissible": False, "reason": "untraceable_final_support"}}
        return out
    CORE.probe_normal_ctx = gated
    try:
        yield
    finally:
        CORE.probe_normal_ctx = orig


def gate_fsg6f_record(m):
    rel = f"initial-probe/probes/e{C.CONTINUING:05d}.json"

    def g(d):
        d["gate_called"] = True
        d["probe"]["gate"] = {"admissible": True, "reason": "novel_support_in_predicted_cores"}
        d["probe"]["adapter"]["calls"]["P3"] = 1
    edit(m, rel, g)
    edit(m, "scene/state-initial.json", lambda s: s["entities"][str(C.CONTINUING)]["probe"].update(
        sha256=C.sha256(m / rel)))


def gate_call_in_normal(m):
    k, _d = executed(m)[-1]
    edit(m, f"steps/step-{k:02d}/plan/decision.json", lambda d: d["gate_guard"].update(
        calls=1, normal_calls=1, refused=1, calls_by_phase={"NORMAL": 1}))


@contextlib.contextmanager
def guard_disabled():
    import ns1c2_phase as PH
    orig = PH.GateGuard.__enter__

    def enter(self):
        self.phase = "RESIDUE"           # every call is treated as RESIDUE: the guard no longer refuses NORMAL calls
        return orig(self)
    PH.GateGuard.__enter__ = enter
    try:
        yield
    finally:
        PH.GateGuard.__enter__ = orig


def cyclopean_quiet(m):
    k = cyclopean_entity(m)

    def g(s):
        s["entities"][k]["status"].update(local="QUIET", label="QUIET", serviceable=False)
        s["machine"]["statuses"][k][1] = "QUIET"
    edit(m, "scene/state-initial.json", g)


def switch_while_actionable(m):
    k, d = new_steps(m)[0]
    prev = jl(m, state_before(k))
    other = next(int(kk) for kk, r in sorted(prev["entities"].items(), key=lambda t: int(t[0]))
                 if int(kk) != C.CONTINUING and r["status"]["serviceable"])

    def g(dd):
        dd["scheduler_decision"]["result"] = {"kind": "attend", "target_id": other, "reason": "switch"}
        dd["action"]["target"] = other
        dd["scheduler_reason"] = "switch"
    edit(m, f"steps/step-{k:02d}/plan/decision.json", g)


# ------------------------------------------------------------------ BUDGET
def budget_changed(m):
    edit(m, "source/source-manifest.json", lambda d: d["accepted_constants"].update(ORDINARY_BUDGET=30))
    for p in sorted((m / "scene").glob("state-*.json")):
        edit(m, f"scene/{p.name}", lambda d: (d.update(budget=30), d["machine"].update(budget=30)))


def called_blocked(m):
    last = sorted((m / "scene").glob("state-after-step-*.json"))[-1].name
    edit(m, f"scene/{last}", lambda s: s["entities"][str(C.CONTINUING)]["status"].update(
        disposition="BLOCKED", reason="watchdog", label="ACTIONABLE/BLOCKED:watchdog"))


def gated_at_budget(m):
    k, _d = new_steps(m)[0]
    edit(m, f"scene/state-after-step-{k:02d}.json", lambda s: s["machine"]["gate_log"].append(
        {"object": C.CONTINUING, "global_step": k, "phase": "RESIDUE"}))


# ------------------------------------------------------------------ RESIDUE (in-process source mutants of the adapter)
def machine_mutant(method: str, old: str, new: str):
    @contextlib.contextmanager
    def ctx():
        import ns1c2_phase as PH
        fn = getattr(PH.SceneMachine, method)
        src = textwrap.dedent(inspect.getsource(fn))
        if src.count(old) != 1:
            raise AssertionError(f"mutation site not unique in {method}: {old[:50]!r}")
        scope: dict = {}
        exec(compile(src.replace(old, new), f"<mutant {method}>", "exec"), PH.__dict__, scope)
        setattr(PH.SceneMachine, method, scope[method])
        try:
            yield
        finally:
            setattr(PH.SceneMachine, method, fn)
    return ctx


RESIDUE_EARLY = machine_mutant(
    "decide", "decision = c2.schedule_normal(self.current, self.statuses.values())",
    "decision = None if any(v[0] is D.DEFERRED for v in self.disposition.values()) else "
    "c2.schedule_normal(self.current, self.statuses.values())")
DEFERRED_ORDER = machine_mutant("decide", "i = pending[0]", "i = pending[-1]")
PROPOSAL_ALTERED = machine_mutant(
    "decide", "verdict = final_gate(i, proposing)",
    "verdict = final_gate(i, ic.ProbeResult(ic.Observe(i, (proposing.action.gaze_yaw_pitch_deg[0] + 1.0, "
    "proposing.action.gaze_yaw_pitch_deg[1]), self.vergence, self.focus, proposing.action.source), proposing.detail))")
TWO_FINAL_LOOKS = machine_mutant(
    "commit", 'self.finalize(i, "final_probe_executed", step)', "pass")


# ------------------------------------------------------------------ PREFIX
def prefix_action_altered(m):
    edit(m, "steps/step-01/plan/decision.json", lambda d: d["action"].update(local_gaze_deg=[-5.0, -10.0]))


def prefix_hash_altered(m):
    def g(d):
        f = sorted(d["verified_files"])[0]
        d["verified_files"][f] = "0" * 64
    edit(m, "steps/step-02/replay/replay.json", g)


def prefix_blender(m):
    e = [x for x in log_entries(m) if x["command"] == "replay" and x["step"] == 1][0]
    log_append(m, [{**e, "command": "acquire", "finished_utc": "later"}])


def prefix_three_steps(m):
    shutil.rmtree(m / "steps/step-03/replay")


def ns1c_wrong_quiet(m):
    rel = f"scene/state-after-step-{C.PREFIX_STEPS - 1:02d}.json"

    def g(s):
        s["entities"][str(C.CONTINUING)]["status"].update(local="QUIET", label="QUIET", serviceable=False)
        s["machine"]["statuses"][str(C.CONTINUING)][1] = "QUIET"
    edit(m, rel, g)


# ------------------------------------------------------------------ TARGET SET
def include(eid: int):
    def f(m):
        edit(m, "eligibility/coherent-seed-set.json", lambda d: d.update(
            coherent_ids=sorted(d["coherent_ids"] + [eid]), scene_ids=sorted(d["scene_ids"] + [eid])))
        edit(m, "steps/step-00/plan/decision.json", lambda d: d["scheduler_decision"].update(
            statuses=sorted(d["scheduler_decision"]["statuses"] + [[eid, "QUIET"]])))
    return f


def use_names(m):
    def g(d):
        p = str(m / "seeds/instance-catalog.json")
        d["events"].append({"event": "open", "path": p, "kind": "data-read", "allowed": True})
        d["data_reads"] = sorted(set(d["data_reads"]) | {p})
    edit(m, "eligibility/eligibility-opened-files.json", g)
    edit(m, "eligibility/coherent-seed-set.json", lambda d: d["fields_read"].append("object_name"))


# ------------------------------------------------------------------ CHART / SENSOR
def recenter(m):
    k, d = new_steps(m)[0]
    t = str(d["action"]["target"])
    r = C.own_chart(C.own_dir(*d["action"]["world_gaze_deg"]))
    h = hashlib.sha256(np.ascontiguousarray(r).tobytes()).hexdigest()
    edit(m, f"scene/state-after-step-{k:02d}.json", lambda s: s["entities"][t].update(chart_sha256=h))
    edit(m, f"steps/step-{k:02d}/update/probes/e{int(t):05d}.json", lambda p: p["probe"]["adapter"].update(
        R_HC=r.tolist()))


def fake_local(m):
    k, d = new_steps(m)[0]
    loc = d["action"]["local_gaze_deg"]
    b = C.cal_bytes(C.own_calibration(*loc))
    unlinked(m / f"steps/step-{k:02d}/plan/planned-calibration.json").write_bytes(b)
    edit(m, f"steps/step-{k:02d}/plan/decision.json", lambda dd: dd["action"].update(
        world_gaze_deg=list(loc), planned_calibration_sha256=hashlib.sha256(b).hexdigest()))


def head_moved(m):
    k, _d = new_steps(m)[0]

    def g(c):
        cc, s = np.cos(np.radians(5.0)), np.sin(np.radians(5.0))
        c["head_R_wh"] = (np.asarray(c["head_R_wh"]) @ np.array([[cc, 0, s], [0, 1, 0], [-s, 0, cc]])).tolist()
    edit(m, f"steps/step-{k:02d}/observation/acquisition/calibration.json", g)


# ------------------------------------------------------------------ MEASUREMENT
def sgbm(m):
    k, _d = new_steps(m)[0]
    rel = f"steps/step-{k:02d}/correspondence/oracle-correspondences.npz"
    a = nl(m, rel)
    a["uv_R"] = a["uv_R"] + np.random.default_rng(1).normal(scale=0.3, size=a["uv_R"].shape)
    ns(m, rel, a)


def planar(m):
    k, _d = new_steps(m)[0]
    rel = f"steps/step-{k:02d}/geometry/epipolar-result.npz"
    a = nl(m, rel)
    a["P_epi"] = a["P_epi"] * 1.002
    ns(m, rel, a)


def position_leak(m):
    k, _d = new_steps(m)[0]

    def g(d):
        p = str(m / f"steps/step-{k:02d}/observation/oracle_aid/reference-observation.npz")
        d["events"].append({"event": "open", "path": p, "kind": "data-read", "allowed": True})
        d["data_reads"] = sorted(set(d["data_reads"]) | {p})
        d["position_reads"] = 1
    edit(m, f"steps/step-{k:02d}/geometry/geometry-opened-files.json", g)


def has_corr(m):
    if not new_steps(m):
        return False
    return len(nl(m, f"steps/step-{new_steps(m)[0][0]:02d}/correspondence/oracle-correspondences.npz")["uv_R"]) > 0


# ------------------------------------------------------------------ FUSION
def fused_step(m) -> int | None:
    return next((k for k, _d in executed(m) if jl(m, f"steps/step-{k:02d}/fusion/fusion.json")["action"] == "FUSED"),
                None)


def cross_target(m):
    k = fused_step(m)
    rel = f"steps/step-{k:02d}/fusion/fused-target-map.npz"
    a = nl(m, rel)
    a["instance_id"] = a["instance_id"].copy()
    a["instance_id"][:5] = 110
    ns(m, rel, a)


def radius(m):
    import ns1b_core as B
    import ns1c2_core as CORE
    k = fused_step(m)
    s = f"steps/step-{k:02d}"
    d = jl(m, f"{s}/plan/decision.json")
    t = int(d["action"]["target"])
    mrec = jl(m, state_before(k))["entities"][str(t)]["map"]
    sm = CORE.load_map(m / mrec["path"].split(":", 1)[1])
    p = nl(m, f"{s}/fusion/target-patch.npz")
    pid = jl(m, f"{s}/fusion/fusion.json")["patch_id"]
    fused, rec = B.fuse_h0(sm, {"frame": "H0", "patch_id": pid, "xyz_h": p["xyz_h"], "rgb": p["rgb"],
                                "instance_id": p["instance_id"], "points": int(len(p["xyz_h"]))}, t, 0.024, 0.024)
    ns(m, f"{s}/fusion/fused-target-map.npz", B.map_arrays(fused))
    edit(m, f"{s}/fusion/fusion.json", lambda dd: dd.update({kk: rec[kk] for kk in ("matched", "new",
                                                                                   "affected_surfels", "map_after")},
                                                            radius_m=0.024))


def fuse_in_chart(m):
    k = fused_step(m)
    d = jl(m, f"steps/step-{k:02d}/plan/decision.json")
    r = np.asarray(jl(m, "charts/policy-charts.json")["charts"][str(d["action"]["target"])]["R_HC"], float)
    rel = f"steps/step-{k:02d}/fusion/fused-target-map.npz"
    a = nl(m, rel)
    a["xyz_h"] = a["xyz_h"] @ r
    ns(m, rel, a)


# ------------------------------------------------------------------ STOP
def has_final(m):
    return (m / "scene/final-scene-state.json").exists()


def extra_step(third: bool):
    def f(m):
        k = switch_step(m)
        src, dst = m / f"steps/step-{k:02d}", m / f"steps/step-{k + 1:02d}"
        for p in ("plan/decision.json", "update/update.json"):
            (dst / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / p, dst / p)
        d = jl(m, f"steps/step-{k + 1:02d}/plan/decision.json")
        d["global_step"] = k + 1
        if third:
            used = {C.CONTINUING, int(d["action"]["target"])}
            d["action"]["target"] = next(i for i in C.COHERENT if i not in used)
        js(m, f"steps/step-{k + 1:02d}/plan/decision.json", d)
        e = [x for x in log_entries(m) if x["command"] == "schedule" and x["step"] == k][0]
        log_append(m, [{**e, "step": k + 1, "finished_utc": "later"}])
    return f


def claim_closed(m):
    edit(m, "scene/final-scene-state.json" if has_final(m) else "scene/state-initial.json",
         lambda d: d.update(marker="SCENE" + "_CLOSED"))


# ------------------------------------------------------------------ PROBE
def ns1b_post_altered(m):
    edit(m, f"initial-probe/probes/e{C.CONTINUING:05d}.json",
         lambda d: d["probe"]["proposal"].update(local_gaze_deg=[0.0, -10.0]))


def untouched_changed(m):
    k, _d = new_steps(m)[0]
    targets = {str(dd["action"]["target"]) for _kk, dd in executed(m)}
    st = jl(m, f"scene/state-after-step-{k:02d}.json")
    other = next(kk for kk in sorted(st["entities"], key=int) if kk not in targets)

    def g(s):
        lab = s["entities"][other]["status"]["label"]
        new = "QUIET" if lab == "ACTIONABLE" else "ACTIONABLE"
        s["entities"][other]["status"].update(local=new, label=new)
    edit(m, f"scene/state-after-step-{k:02d}.json", g)


def truth_in_probe(m):
    def g(d):
        p = str(C.NS1A / "observations/rank-06/oracle_aid/reference-observation.npz")
        d["events"].append({"event": "open", "path": p, "kind": "data-read", "allowed": True})
        d["data_reads"] = sorted(set(d["data_reads"]) | {p})
    edit(m, "initial-probe/initial-probe-opened-files.json", g)


# ------------------------------------------------------------------ VISUAL
def man_edit(fn):
    def f(m, mv):
        d = json.loads((mv / "visuals-manifest.json").read_text())
        fn(d)
        (mv / "visuals-manifest.json").write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")
    return f


def gate_in_normal_marker(d):
    k = d["figures"]["overview.png"]["phases_shown"]
    d["figures"]["overview.png"].update(gate_markers=[len(k) - 2], gate_marker_phases=["NORMAL"])
    d["figures"]["controller-phase-timeline.png"].update(gate_markers=[len(k) - 2])


def pixel(m, mv):
    p = mv / "overview.png"
    im = Image.open(p).convert("RGB")
    v = im.getpixel((100, 100))
    im.putpixel((100, 100), (255 - v[0], v[1], v[2]))
    im.save(p, format="PNG", optimize=False)


ANY = lambda m: True  # noqa: E731
NEW = lambda m: bool(new_steps(m))  # noqa: E731
CYC = lambda m: cyclopean_entity(m) is not None  # noqa: E731
FUSED = lambda m: fused_step(m) is not None  # noqa: E731
SWITCH_ALT = lambda m: bool(new_steps(m)) and any(  # noqa: E731
    int(kk) != C.CONTINUING and r["status"]["serviceable"]
    for kk, r in jl(m, state_before(new_steps(m)[0][0]))["entities"].items())

CORRUPTIONS = [
    # (family, name, applies, mutation, kind, expected catching checks)
    ("SEMANTICS", "gate a Cyclopean NORMAL proposal (NS1c's rule, in-process)", CYC, gated_cyclopean, "live",
     ["09", "17", "26"]),
    ("SEMANTICS", "gate an FSG6f NORMAL proposal (probe record)", ANY, gate_fsg6f_record, "run", ["09", "14"]),
    ("SEMANTICS", "a final-gate call while the phase is NORMAL", NEW, gate_call_in_normal, "run", ["14"]),
    ("SEMANTICS", "the gate guard no longer refuses NORMAL calls (in-process)", ANY, guard_disabled, "live", ["10"]),
    ("SEMANTICS", "a Cyclopean proposal classified QUIET", CYC, cyclopean_quiet, "run", ["11"]),
    ("SEMANTICS", "a switch while the current entity is NORMAL ACTIONABLE", SWITCH_ALT, switch_while_actionable, "run",
     ["12", "13"]),
    ("BUDGET", "ordinary budget changed (24 -> 30)", ANY, budget_changed, "run", ["06"]),
    ("BUDGET", "BLOCKED instead of DEFERRED", NEW, called_blocked, "run", ["11", "15"]),
    ("BUDGET", "gated at the budget while NORMAL work remains", NEW, gated_at_budget, "run", ["15"]),
    ("RESIDUE", "RESIDUE entered while a NORMAL-serviceable object exists (adapter mutant)", ANY, RESIDUE_EARLY, "live",
     ["10"]),
    ("RESIDUE", "deferred order changed (adapter mutant)", ANY, DEFERRED_ORDER, "live", ["10"]),
    ("RESIDUE", "the final proposal altered before the gate (adapter mutant)", ANY, PROPOSAL_ALTERED, "live", ["10"]),
    ("RESIDUE", "two final residue looks for one object (adapter mutant)", ANY, TWO_FINAL_LOOKS, "live", ["10"]),
    ("PREFIX", "one saved NS1c action altered", ANY, prefix_action_altered, "run", ["12", "16"]),
    ("PREFIX", "one observation hash altered", ANY, prefix_hash_altered, "run", ["16"]),
    ("PREFIX", "Blender during the prefix replay", ANY, prefix_blender, "run", ["16", "28"]),
    ("PREFIX", "only three prefix steps replayed", ANY, prefix_three_steps, "run", ["16"]),
    ("PREFIX", "NS1c's wrong QUIET state imported for 172", ANY, ns1c_wrong_quiet, "run", ["11", "13"]),
    ("TARGET SET", "include 10", ANY, include(10), "run", ["04"]),
    ("TARGET SET", "include 110", ANY, include(110), "run", ["04"]),
    ("TARGET SET", "include 178", ANY, include(178), "run", ["04"]),
    ("TARGET SET", "names / catalog used in the eligibility", ANY, use_names, "run", ["04", "29"]),
    ("CHART / SENSOR", "dynamic recenter after an action", NEW, recenter, "run", ["05"]),
    ("CHART / SENSOR", "fake local baseline (local gaze as the H0 gaze)", NEW, fake_local, "run", ["07", "18"]),
    ("CHART / SENSOR", "physical head moved", NEW, head_moved, "run", ["07", "18"]),
    ("MEASUREMENT", "SGBM-like correspondence", has_corr, sgbm, "run", ["21"]),
    ("MEASUREMENT", "planar / other persistent geometry", has_corr, planar, "run", ["22"]),
    ("MEASUREMENT", "Position leak into the spherical stage", NEW, position_leak, "run", ["22", "29"]),
    ("FUSION", "cross-target fusion", FUSED, cross_target, "run", ["24"]),
    ("FUSION", "radius changed (regenerated)", FUSED, radius, "run", ["24"]),
    ("FUSION", "fused in chart coordinates", FUSED, fuse_in_chart, "run", ["24"]),
    ("STOP", "a second action on the new target", has_final, extra_step(False), "run", ["27"]),
    ("STOP", "a third entity", has_final, extra_step(True), "run", ["27"]),
    ("STOP", "a scene-closure claim", ANY, claim_closed, "run", ["30"]),
    ("PROBE", "the NS1b reproduction altered", ANY, ns1b_post_altered, "run", ["09"]),
    ("PROBE", "an untouched entity's state changed silently", NEW, untouched_changed, "run", ["11", "26"]),
    ("PROBE", "truth read by the initial probe", ANY, truth_in_probe, "run", ["09", "29"]),
    ("VISUAL", "phase hidden", ANY, man_edit(lambda d: d["figures"]["overview.png"].update(phases_shown=[])), "vis",
     ["31"]),
    ("VISUAL", "a final-gate marker shown in NORMAL", ANY, man_edit(gate_in_normal_marker), "vis", ["31"]),
    ("VISUAL", "oracle label removed", ANY, man_edit(lambda d: d["figures"]["overview.png"]["labels"].remove(
        "ORACLE CORRESPONDENCE")), "vis", ["31"]),
    ("VISUAL", "a canonical pixel altered", ANY, pixel, "vis", ["31"]),
]


def run_suite(run: Path, vis: Path, baseline_failed: list, ignore_baseline: tuple = ()) -> dict:
    """``ignore_baseline`` is a development aid only (rehearsal runs); the canonical suite uses an empty tuple."""
    run, vis = Path(run), Path(vis)
    before = {"run": tree_hashes(run), "vis": tree_hashes(vis)}
    out = {"baseline_failed": list(baseline_failed), "results": [], "missed": [], "not_applicable": [],
           "baseline_failing": []}
    if set(baseline_failed) - set(ignore_baseline):
        out.update(error="the suite runs only from a passing baseline", run_unchanged_by_suite=True,
                   marker="NORTH_STAR1C2_MUTATIONS_INCOMPLETE")
        return out
    with tempfile.TemporaryDirectory(prefix="ns1c2-corrupt-") as td:
        m, mv = mirror(run, vis, Path(td) / "null")
        null = C.run_checks(m, mv, quiet=True)
        out["null_probe"] = {"failed": [k for k, v in null.items() if not v["pass"] and k not in ignore_baseline],
                             "checked": len(null)}
        shutil.rmtree(Path(td) / "null")
        for family, name, applies, mutate, kind, expect in CORRUPTIONS:
            d = Path(td) / f"c{len(out['results']):02d}"
            m, mv = mirror(run, vis, d)
            if set(expect) & set(ignore_baseline):
                out["baseline_failing"].append(name)
                out["results"].append({"family": family, "corruption": name, "status": "BASELINE FAILING (dev)"})
                shutil.rmtree(d)
                continue
            if not applies(m):
                out["not_applicable"].append(name)
                out["results"].append({"family": family, "corruption": name, "status": "NOT APPLICABLE",
                                       "reason": "the mutated product does not exist in the executed trajectory"})
                shutil.rmtree(d)
                continue
            if kind == "live":
                with mutate():
                    res = C.run_checks(m, mv, only=set(expect), quiet=True)
            else:
                if kind == "vis":
                    mutate(m, mv)
                else:
                    mutate(m)
                remanifest(m)
                res = C.run_checks(m, mv, only=set(expect), quiet=True)
            caught = [k for k in expect if not res[k]["pass"]]
            rec = {"family": family, "corruption": name, "expected": expect, "caught_by": caught,
                   "status": "CAUGHT" if caught == expect else "MISSED"}
            if caught != expect:
                out["missed"].append(name)
                rec["details"] = {k: res[k]["detail"] for k in expect if res[k]["pass"]}
            out["results"].append(rec)
            print(f"{C.PREFIX} corruption {rec['status']:<14} {family}: {name} -> {caught}", flush=True)
            shutil.rmtree(d)
    after = {"run": tree_hashes(run), "vis": tree_hashes(vis)}
    out["run_unchanged_by_suite"] = after == before
    applicable = [r for r in out["results"] if r["status"] in ("CAUGHT", "MISSED")]
    out["caught"] = sum(1 for r in applicable if r["status"] == "CAUGHT")
    out["applicable"] = len(applicable)
    out["marker"] = "NORTH_STAR1C2_MUTATIONS_CAUGHT" if not out["missed"] and not out["null_probe"]["failed"] \
        and out["run_unchanged_by_suite"] and not out["baseline_failing"] else "NORTH_STAR1C2_MUTATIONS_INCOMPLETE"
    print(f"{C.PREFIX} corruptions caught {out['caught']}/{out['applicable']} (not applicable "
          f"{len(out['not_applicable'])}; baseline-failing {len(out['baseline_failing'])}); null probe failed "
          f"{out['null_probe']['failed']}; run unchanged {out['run_unchanged_by_suite']}; {out['marker']}", flush=True)
    return out
